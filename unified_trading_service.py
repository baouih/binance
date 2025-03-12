#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dịch vụ hợp nhất - Quản lý nhiều dịch vụ nhỏ trong một tiến trình chính
để tối ưu hóa tài nguyên và đơn giản hóa quản lý

Các dịch vụ bao gồm:
1. Auto SLTP: Tự động đặt Stop Loss và Take Profit
2. Trailing Stop: Theo dõi và điều chỉnh Stop Loss theo giá
3. Market Monitor: Theo dõi thị trường và gửi thông báo khi có biến động

Tác giả: BinanceTrader Bot
"""

import os
import sys
import time
import json
import signal
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta

try:
    import schedule
except ImportError:
    print("Thư viện schedule chưa được cài đặt. Đang cài đặt...")
    os.system("pip install schedule")
    import schedule

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("unified_service.log"),
        logging.StreamHandler()
    ]
)

# Tạo logger riêng cho dịch vụ hợp nhất
logger = logging.getLogger("unified_service")

# Đường dẫn tới file cấu hình tài khoản
ACCOUNT_CONFIG_PATH = 'account_config.json'
PID_FILE = 'unified_trading_service.pid'

# Biến toàn cục để theo dõi trạng thái dịch vụ
running = True
services = {
    'auto_sltp': {'active': False, 'thread': None, 'last_run': None},
    'trailing_stop': {'active': False, 'thread': None, 'last_run': None},
    'market_monitor': {'active': False, 'thread': None, 'last_run': None}
}


def load_config() -> Dict[str, Any]:
    """Tải cấu hình từ file account_config.json"""
    try:
        with open(ACCOUNT_CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình: {e}")
        return {}


def save_pid() -> None:
    """Lưu PID của tiến trình hiện tại vào file"""
    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        logger.info(f"Đã lưu PID {os.getpid()} vào {PID_FILE}")
    except Exception as e:
        logger.error(f"Lỗi khi lưu PID: {e}")


def remove_pid() -> None:
    """Xóa file PID khi thoát"""
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
            logger.info(f"Đã xóa file PID {PID_FILE}")
    except Exception as e:
        logger.error(f"Lỗi khi xóa file PID: {e}")


def signal_handler(sig, frame) -> None:
    """Xử lý tín hiệu khi nhận SIGTERM hoặc SIGINT"""
    global running
    logger.info(f"Đã nhận tín hiệu {sig}, dừng dịch vụ...")
    running = False
    
    # Dừng tất cả các dịch vụ con
    stop_all_services()
    
    # Xóa file PID
    remove_pid()
    
    # Xóa tất cả các công việc định kỳ
    schedule.clear()
    
    # Thoát khỏi tiến trình sau 2 giây
    logger.info("Đang thoát dịch vụ hợp nhất...")
    time.sleep(2)
    sys.exit(0)


def initialize_binance_client():
    """Khởi tạo Binance API client"""
    try:
        from binance_api import BinanceAPI
        
        # Tải cấu hình từ file
        config = load_config()
        api_mode = config.get('api_mode', 'testnet')
        
        # Đọc keys từ biến môi trường hoặc từ file cấu hình
        api_keys = config.get('api_keys', {})
        keys_for_mode = api_keys.get(api_mode, {})
        
        api_key = os.environ.get("BINANCE_TESTNET_API_KEY", keys_for_mode.get('api_key', ''))
        api_secret = os.environ.get("BINANCE_TESTNET_API_SECRET", keys_for_mode.get('api_secret', ''))
        
        # Khởi tạo client với chế độ phù hợp
        use_testnet = api_mode != 'live'
        client = BinanceAPI(api_key=api_key, api_secret=api_secret, testnet=use_testnet)
        
        logger.info(f"Đã khởi tạo Binance API client với chế độ: {api_mode}")
        return client
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo Binance API client: {e}")
        return None


def initialize_position_manager():
    """Khởi tạo Position Manager"""
    try:
        from position_manager import PositionManager
        client = initialize_binance_client()
        if client:
            position_manager = PositionManager(client)
            logger.info("Đã khởi tạo Position Manager")
            return position_manager
        return None
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo Position Manager: {e}")
        return None


def check_positions(position_manager=None):
    """Kiểm tra các vị thế hiện có"""
    if position_manager is None:
        position_manager = initialize_position_manager()
    
    if position_manager:
        try:
            positions = position_manager.get_all_positions()
            active_positions = [p for p in positions if float(p.get('positionAmt', 0)) != 0]
            
            if active_positions:
                logger.info(f"Đang có {len(active_positions)} vị thế hoạt động:")
                for pos in active_positions:
                    symbol = pos.get('symbol', '')
                    side = 'LONG' if float(pos.get('positionAmt', 0)) > 0 else 'SHORT'
                    amt = abs(float(pos.get('positionAmt', 0)))
                    entry = float(pos.get('entryPrice', 0))
                    pnl = float(pos.get('unRealizedProfit', 0))
                    logger.info(f"  - {symbol}: {side}, Số lượng: {amt}, Giá vào: {entry}, PnL: {pnl} USDT")
            else:
                logger.info("Không có vị thế nào đang hoạt động")
            
            return active_positions
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra vị thế: {e}")
    
    return []


def set_stop_loss_take_profit_for_positions(position_manager=None):
    """Đặt Stop Loss và Take Profit cho các vị thế hiện có"""
    if position_manager is None:
        position_manager = initialize_position_manager()
    
    if not position_manager:
        logger.error("Không thể thiết lập SLTP: Position Manager không được khởi tạo")
        return
    
    # Tải cấu hình
    config = load_config()
    auto_sltp_settings = config.get('auto_sltp_settings', {})
    
    # Lấy các thiết lập
    risk_reward_ratio = auto_sltp_settings.get('risk_reward_ratio', 2.0)
    stop_loss_percent = auto_sltp_settings.get('stop_loss_percent', 2.0)
    take_profit_percent = auto_sltp_settings.get('take_profit_percent', stop_loss_percent * risk_reward_ratio)
    
    logger.info(f"Auto SLTP được cấu hình với: SL={stop_loss_percent}%, TP={take_profit_percent}%, R:R={risk_reward_ratio}")
    
    # Lấy danh sách vị thế
    try:
        positions = position_manager.get_all_positions()
        active_positions = [p for p in positions if float(p.get('positionAmt', 0)) != 0]
        
        if not active_positions:
            logger.info("Không có vị thế nào cần thiết lập SLTP")
            return
        
        # Xử lý từng vị thế
        for pos in active_positions:
            symbol = pos.get('symbol', '')
            position_amt = float(pos.get('positionAmt', 0))
            
            if position_amt == 0:
                continue
                
            entry_price = float(pos.get('entryPrice', 0))
            is_long = position_amt > 0
            
            # Tính SL và TP
            if is_long:
                sl_price = entry_price * (1 - stop_loss_percent / 100)
                tp_price = entry_price * (1 + take_profit_percent / 100)
            else:
                sl_price = entry_price * (1 + stop_loss_percent / 100)
                tp_price = entry_price * (1 - take_profit_percent / 100)
            
            # Làm tròn giá
            sl_price = round(sl_price, 2)
            tp_price = round(tp_price, 2)
            
            logger.info(f"Thiết lập SLTP cho {symbol}: Entry={entry_price}, SL={sl_price}, TP={tp_price}")
            
            # Gọi API để đặt SL và TP
            try:
                position_manager.set_stop_loss_take_profit(
                    symbol=symbol,
                    stop_loss=sl_price,
                    take_profit=tp_price,
                    position_side="LONG" if is_long else "SHORT"
                )
                logger.info(f"Đã đặt SLTP thành công cho {symbol}")
            except Exception as e:
                logger.error(f"Lỗi khi đặt SLTP cho {symbol}: {e}")
    
    except Exception as e:
        logger.error(f"Lỗi khi thiết lập SLTP: {e}")


def auto_sltp_service():
    """Dịch vụ tự động đặt Stop Loss và Take Profit"""
    if not services['auto_sltp']['active']:
        return
    
    logger.info("Đang chạy dịch vụ Auto SLTP...")
    position_manager = initialize_position_manager()
    
    try:
        # Kiểm tra vị thế
        active_positions = check_positions(position_manager)
        
        # Đặt SLTP cho các vị thế
        if active_positions:
            set_stop_loss_take_profit_for_positions(position_manager)
        
        # Cập nhật thời gian chạy cuối cùng
        services['auto_sltp']['last_run'] = datetime.now()
    except Exception as e:
        logger.error(f"Lỗi khi chạy dịch vụ Auto SLTP: {e}")


def check_and_update_trailing_stops(position_manager=None):
    """Kiểm tra và cập nhật Trailing Stop cho các vị thế"""
    if position_manager is None:
        position_manager = initialize_position_manager()
    
    if not position_manager:
        logger.error("Không thể cập nhật Trailing Stop: Position Manager không được khởi tạo")
        return
    
    # Tải cấu hình
    config = load_config()
    trailing_stop_settings = config.get('trailing_stop_settings', {})
    
    # Lấy các thiết lập
    activation_percent = trailing_stop_settings.get('activation_percent', 1.0)
    trailing_percent = trailing_stop_settings.get('trailing_percent', 0.5)
    
    logger.info(f"Trailing Stop cấu hình với: Kích hoạt={activation_percent}%, Theo sau={trailing_percent}%")
    
    # Lấy danh sách vị thế
    try:
        positions = position_manager.get_all_positions()
        active_positions = [p for p in positions if float(p.get('positionAmt', 0)) != 0]
        
        if not active_positions:
            logger.info("Không có vị thế nào cần cập nhật Trailing Stop")
            return
        
        # Xử lý từng vị thế
        for pos in active_positions:
            symbol = pos.get('symbol', '')
            position_amt = float(pos.get('positionAmt', 0))
            
            if position_amt == 0:
                continue
                
            entry_price = float(pos.get('entryPrice', 0))
            is_long = position_amt > 0
            
            # Lấy giá hiện tại
            current_price = get_symbol_price(symbol, position_manager)
            
            if not current_price:
                logger.warning(f"Không thể lấy giá hiện tại cho {symbol}, bỏ qua cập nhật Trailing Stop")
                continue
            
            # Tính lợi nhuận hiện tại (%)
            if is_long:
                profit_percent = ((current_price / entry_price) - 1) * 100
            else:
                profit_percent = ((entry_price / current_price) - 1) * 100
            
            # Kiểm tra điều kiện kích hoạt Trailing Stop
            if profit_percent >= activation_percent:
                # Tính toán giá Stop Loss mới
                if is_long:
                    new_sl_price = current_price * (1 - trailing_percent / 100)
                    
                    # Lấy Stop Loss hiện tại
                    current_sl = get_current_stop_loss(symbol, "LONG", position_manager)
                    
                    # Nếu Stop Loss mới cao hơn Stop Loss hiện tại
                    if not current_sl or new_sl_price > current_sl:
                        logger.info(f"{symbol} (LONG): Cập nhật Trailing Stop từ {current_sl} lên {new_sl_price}, lợi nhuận: {profit_percent:.2f}%")
                        
                        try:
                            # Hủy Stop Loss cũ nếu có
                            if current_sl:
                                position_manager.close_position(
                                    symbol=symbol,
                                    side="BUY",  # Đối với vị thế LONG, đóng = BUY
                                    quantity=0,  # Chỉ hủy đơn hàng SL, không đóng vị thế
                                    close_type="STOP_MARKET",
                                    cancel_orders=True
                                )
                            
                            # Đặt Stop Loss mới
                            position_manager.set_stop_loss_take_profit(
                                symbol=symbol,
                                stop_loss=new_sl_price,
                                position_side="LONG"
                            )
                            logger.info(f"Đã cập nhật Trailing Stop cho {symbol} (LONG)")
                        except Exception as e:
                            logger.error(f"Lỗi khi cập nhật Trailing Stop cho {symbol} (LONG): {e}")
                else:
                    new_sl_price = current_price * (1 + trailing_percent / 100)
                    
                    # Lấy Stop Loss hiện tại
                    current_sl = get_current_stop_loss(symbol, "SHORT", position_manager)
                    
                    # Nếu Stop Loss mới thấp hơn Stop Loss hiện tại
                    if not current_sl or new_sl_price < current_sl:
                        logger.info(f"{symbol} (SHORT): Cập nhật Trailing Stop từ {current_sl} xuống {new_sl_price}, lợi nhuận: {profit_percent:.2f}%")
                        
                        try:
                            # Hủy Stop Loss cũ nếu có
                            if current_sl:
                                position_manager.close_position(
                                    symbol=symbol,
                                    side="SELL",  # Đối với vị thế SHORT, đóng = SELL
                                    quantity=0,  # Chỉ hủy đơn hàng SL, không đóng vị thế
                                    close_type="STOP_MARKET",
                                    cancel_orders=True
                                )
                            
                            # Đặt Stop Loss mới
                            position_manager.set_stop_loss_take_profit(
                                symbol=symbol,
                                stop_loss=new_sl_price,
                                position_side="SHORT"
                            )
                            logger.info(f"Đã cập nhật Trailing Stop cho {symbol} (SHORT)")
                        except Exception as e:
                            logger.error(f"Lỗi khi cập nhật Trailing Stop cho {symbol} (SHORT): {e}")
            else:
                logger.debug(f"{symbol}: Lợi nhuận {profit_percent:.2f}% chưa đạt ngưỡng kích hoạt Trailing Stop ({activation_percent}%)")
    
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật Trailing Stop: {e}")


def get_current_stop_loss(symbol, position_side, position_manager):
    """Lấy giá Stop Loss hiện tại từ các đơn hàng đang mở"""
    try:
        # TODO: Implement logic to get current stop loss orders
        # This is a placeholder, actual implementation would depend on Binance API
        return None
    except Exception as e:
        logger.error(f"Lỗi khi lấy Stop Loss hiện tại cho {symbol}: {e}")
        return None


def get_symbol_price(symbol, position_manager=None):
    """Lấy giá hiện tại của một cặp tiền tệ"""
    if position_manager is None:
        position_manager = initialize_position_manager()
    
    if not position_manager:
        logger.error("Position Manager không được khởi tạo")
        return None
    
    try:
        # Sử dụng client của position_manager để lấy giá
        price_info = position_manager.client.futures_symbol_ticker(symbol=symbol)
        if price_info and 'price' in price_info:
            return float(price_info['price'])
        
        logger.warning(f"Không thể lấy giá cho {symbol}: Dữ liệu không đúng định dạng")
        return None
    except Exception as e:
        logger.error(f"Lỗi khi lấy giá {symbol}: {e}")
        return None


def trailing_stop_service():
    """Dịch vụ Trailing Stop"""
    if not services['trailing_stop']['active']:
        return
    
    logger.info("Đang chạy dịch vụ Trailing Stop...")
    position_manager = initialize_position_manager()
    
    try:
        # Kiểm tra vị thế
        active_positions = check_positions(position_manager)
        
        # Cập nhật Trailing Stop cho các vị thế
        if active_positions:
            check_and_update_trailing_stops(position_manager)
        
        # Cập nhật thời gian chạy cuối cùng
        services['trailing_stop']['last_run'] = datetime.now()
    except Exception as e:
        logger.error(f"Lỗi khi chạy dịch vụ Trailing Stop: {e}")


def monitor_market_volatility():
    """Theo dõi biến động thị trường và gửi thông báo khi vượt ngưỡng"""
    # Tải cấu hình
    config = load_config()
    market_settings = config.get('market_monitor_settings', {})
    
    # Lấy các thiết lập
    symbols = market_settings.get('symbols', ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
    volatility_threshold = market_settings.get('volatility_threshold', 3.0)
    
    logger.info(f"Market Monitor theo dõi các cặp: {', '.join(symbols)}")
    
    # Khởi tạo client
    client = initialize_binance_client()
    if not client:
        logger.error("Không thể kết nối đến Binance API")
        return
    
    try:
        # Lấy dữ liệu thị trường
        tickers = client.futures_ticker()
        
        if not tickers:
            logger.warning("Không thể lấy dữ liệu thị trường")
            return
        
        # Lọc các cặp tiền quan tâm
        for ticker in tickers:
            symbol = ticker.get('symbol', '')
            
            if symbol not in symbols:
                continue
            
            price_change = float(ticker.get('priceChangePercent', 0))
            current_price = float(ticker.get('lastPrice', 0))
            
            # Kiểm tra biến động
            if abs(price_change) >= volatility_threshold:
                direction = "tăng" if price_change > 0 else "giảm"
                message = f"⚠️ {symbol} đang {direction} mạnh {abs(price_change):.2f}%, giá hiện tại: {current_price} USDT"
                logger.warning(message)
                
                # Gửi thông báo
                try:
                    from telegram_notifier import TelegramNotifier
                    notifier = TelegramNotifier()
                    notifier.send_message(message)
                except Exception as e:
                    logger.error(f"Lỗi khi gửi thông báo Telegram: {e}")
    
    except Exception as e:
        logger.error(f"Lỗi khi theo dõi biến động thị trường: {e}")


def market_monitor_service():
    """Dịch vụ giám sát thị trường"""
    if not services['market_monitor']['active']:
        return
    
    logger.info("Đang chạy dịch vụ Market Monitor...")
    
    try:
        # Theo dõi biến động thị trường
        monitor_market_volatility()
        
        # Cập nhật thời gian chạy cuối cùng
        services['market_monitor']['last_run'] = datetime.now()
    except Exception as e:
        logger.error(f"Lỗi khi chạy dịch vụ Market Monitor: {e}")


def setup_services():
    """Thiết lập các dịch vụ theo cấu hình"""
    # Tải cấu hình
    config = load_config()
    
    # Thiết lập Auto SLTP service
    auto_sltp_settings = config.get('auto_sltp_settings', {})
    if auto_sltp_settings.get('enabled', True):
        services['auto_sltp']['active'] = True
        interval = auto_sltp_settings.get('check_interval', 30)
        schedule.every(interval).seconds.do(auto_sltp_service)
        logger.info(f"Đã kích hoạt dịch vụ Auto SLTP với chu kỳ {interval} giây")
    
    # Thiết lập Trailing Stop service
    trailing_stop_settings = config.get('trailing_stop_settings', {})
    if trailing_stop_settings.get('enabled', True):
        services['trailing_stop']['active'] = True
        interval = trailing_stop_settings.get('check_interval', 15)
        schedule.every(interval).seconds.do(trailing_stop_service)
        logger.info(f"Đã kích hoạt dịch vụ Trailing Stop với chu kỳ {interval} giây")
    
    # Thiết lập Market Monitor service
    market_monitor_settings = config.get('market_monitor_settings', {})
    if market_monitor_settings.get('enabled', True):
        services['market_monitor']['active'] = True
        interval = market_monitor_settings.get('check_interval', 60)
        schedule.every(interval).seconds.do(market_monitor_service)
        logger.info(f"Đã kích hoạt dịch vụ Market Monitor với chu kỳ {interval} giây")


def stop_all_services():
    """Dừng tất cả các dịch vụ"""
    logger.info("Đang dừng tất cả các dịch vụ...")
    
    for service_name, service_info in services.items():
        service_info['active'] = False
        logger.info(f"Đã dừng dịch vụ {service_name}")


def run_scheduler():
    """Chạy bộ lập lịch để thực hiện các công việc định kỳ"""
    global running
    
    logger.info("Bắt đầu chạy bộ lập lịch...")
    
    while running:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logger.error(f"Lỗi khi chạy bộ lập lịch: {e}")
            time.sleep(5)  # Đợi 5 giây trước khi thử lại


def main():
    """Hàm chính để chạy dịch vụ hợp nhất"""
    global running
    running = True
    
    logger.info("===== Khởi động dịch vụ hợp nhất =====")
    
    # Đăng ký handler xử lý tín hiệu
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Lưu PID
    save_pid()
    
    # Kiểm tra kết nối đến Binance API
    client = initialize_binance_client()
    if not client:
        logger.error("Không thể kết nối đến Binance API, dừng dịch vụ")
        return
    
    # Thiết lập các dịch vụ
    setup_services()
    
    # Kiểm tra vị thế ban đầu
    position_manager = initialize_position_manager()
    if position_manager:
        check_positions(position_manager)
    
    # Chạy bộ lập lịch trong một thread riêng
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    # Kiểm tra trạng thái các dịch vụ định kỳ
    try:
        while running:
            # Kiểm tra trạng thái các dịch vụ
            for service_name, service_info in services.items():
                if service_info['active']:
                    last_run = service_info['last_run']
                    if last_run:
                        elapsed = datetime.now() - last_run
                        status = f"Hoạt động (Lần chạy cuối: {elapsed.seconds} giây trước)"
                    else:
                        status = "Đang khởi động..."
                else:
                    status = "Không hoạt động"
                
                logger.debug(f"Dịch vụ {service_name}: {status}")
            
            # Đợi 30 giây trước khi kiểm tra lại
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Nhận được tín hiệu thoát từ bàn phím")
        running = False
    finally:
        # Dừng tất cả các dịch vụ
        stop_all_services()
        
        # Xóa file PID
        remove_pid()
        
        logger.info("===== Đã dừng dịch vụ hợp nhất =====")


if __name__ == "__main__":
    main()