#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified Trading Service
-----------------------
Dịch vụ hợp nhất quản lý các chức năng giao dịch để tối ưu tài nguyên.
Kết hợp các dịch vụ:
1. Auto SLTP Manager (Quản lý Stop Loss và Take Profit tự động)
2. Trailing Stop Manager (Quản lý Trailing Stop)
3. Market Monitor (Theo dõi thị trường và cảnh báo)

Tác giả: Trading Bot Team
Phát triển: 2025
"""

import os
import sys
import time
import json
import signal
import logging
import threading
import schedule
from datetime import datetime, timedelta
import importlib

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("unified_service.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("unified_service")

# Thông tin phiên bản
VERSION = "1.0.0"

# Đường dẫn file cấu hình
CONFIG_FILE = 'account_config.json'
PID_FILE = 'unified_trading_service.pid'
ACTIVE_POSITIONS_FILE = 'active_positions.json'

# Biến điều khiển
running = True
services = {}
scheduler = None
api_client = None

def load_config():
    """Tải cấu hình từ file"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error(f"Không thể tải cấu hình: {str(e)}")
        return {}

def save_pid():
    """Lưu PID của process hiện tại"""
    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        logger.info(f"Đã lưu PID: {os.getpid()}")
    except Exception as e:
        logger.error(f"Không thể lưu PID: {str(e)}")

def signal_handler(sig, frame):
    """Xử lý tín hiệu thoát"""
    global running
    logger.info(f"Đã nhận tín hiệu {sig}, đang dừng dịch vụ...")
    running = False

def import_module_dynamically(module_name):
    """Import mô-đun một cách động"""
    try:
        if module_name in sys.modules:
            # Nếu module đã được import trước đó, reload để cập nhật
            module = importlib.import_module(module_name)
            module = importlib.reload(module)
        else:
            # Import module mới
            module = importlib.import_module(module_name)
        logger.info(f"Đã import mô-đun: {module_name}")
        return module
    except Exception as e:
        logger.error(f"Không thể import mô-đun {module_name}: {str(e)}")
        return None

def initialize_api_client():
    """Khởi tạo API client"""
    global api_client
    
    try:
        # Import mô-đun BinanceAPI
        binance_api_module = import_module_dynamically('binance_api')
        if not binance_api_module:
            logger.error("Không thể import binance_api module")
            return False
        
        # Lấy API key và secret từ biến môi trường
        api_key = os.environ.get("BINANCE_TESTNET_API_KEY", "")
        api_secret = os.environ.get("BINANCE_TESTNET_API_SECRET", "")
        
        # Khởi tạo đối tượng BinanceAPI
        BinanceAPI = getattr(binance_api_module, 'BinanceAPI')
        api_client = BinanceAPI(api_key=api_key, api_secret=api_secret, testnet=True)
        
        # Kiểm tra kết nối
        if api_client.test_connection():
            logger.info("Kết nối API thành công")
            return True
        else:
            logger.error("Kết nối API thất bại")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo API client: {str(e)}")
        return False

def initialize_telegram():
    """Khởi tạo Telegram notifier"""
    try:
        telegram_module = import_module_dynamically('telegram_notifier')
        if telegram_module:
            # Gửi thông báo khởi động
            telegram_module.send_message(
                message=f"<b>🤖 Dịch vụ hợp nhất đã khởi động</b>\n\n"
                f"<i>Phiên bản:</i> {VERSION}\n"
                f"<i>Thời gian:</i> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"<i>PID:</i> {os.getpid()}"
            )
            logger.info("Đã khởi tạo Telegram notifier")
            return True
        return False
    except Exception as e:
        logger.error(f"Không thể khởi tạo Telegram notifier: {str(e)}")
        return False

def start_sltp_manager():
    """Khởi động và quản lý dịch vụ Auto SLTP Manager"""
    try:
        # Tải cấu hình
        config = load_config()
        sltp_config = config.get('auto_sltp_settings', {})
        enabled = sltp_config.get('enabled', False)
        check_interval = sltp_config.get('check_interval', 30)
        
        if not enabled:
            logger.info("Auto SLTP Manager đã bị tắt trong cấu hình")
            return False
        
        # Thiết lập lên lịch kiểm tra
        def check_and_update_sltp():
            """Kiểm tra và cập nhật SL/TP cho các vị thế"""
            try:
                # Lấy danh sách vị thế đang mở
                positions = api_client.get_positions()
                active_positions = [p for p in positions if abs(float(p.get('positionAmt', 0))) > 0]
                
                if not active_positions:
                    logger.info("Không có vị thế đang mở để cập nhật SL/TP")
                    return
                
                # Lưu vị thế active
                try:
                    with open(ACTIVE_POSITIONS_FILE, 'w') as f:
                        json.dump(active_positions, f, indent=2)
                except Exception as e:
                    logger.error(f"Không thể lưu active positions: {str(e)}")
                
                # Xử lý từng vị thế
                for position in active_positions:
                    symbol = position.get('symbol', '')
                    position_amt = float(position.get('positionAmt', 0))
                    entry_price = float(position.get('entryPrice', 0))
                    
                    if position_amt == 0 or entry_price == 0:
                        continue
                    
                    # Xác định hướng vị thế
                    position_side = 'LONG' if position_amt > 0 else 'SHORT'
                    
                    # Tính Stop Loss và Take Profit dựa trên cấu hình
                    risk_reward_ratio = sltp_config.get('risk_reward_ratio', 2.0)
                    stop_loss_percent = sltp_config.get('stop_loss_percent', 1.0)
                    
                    # Tính giá SL và TP
                    if position_side == 'LONG':
                        stop_loss = entry_price * (1 - stop_loss_percent / 100)
                        take_profit = entry_price * (1 + (stop_loss_percent * risk_reward_ratio) / 100)
                    else:  # SHORT
                        stop_loss = entry_price * (1 + stop_loss_percent / 100)
                        take_profit = entry_price * (1 - (stop_loss_percent * risk_reward_ratio) / 100)
                    
                    # Đặt SL và TP
                    result = api_client.set_stop_loss_take_profit(
                        symbol=symbol,
                        position_side=position_side,
                        stop_loss_price=stop_loss,
                        take_profit_price=take_profit
                    )
                    
                    if result:
                        logger.info(f"Đã cập nhật SL/TP cho {symbol} {position_side}: SL={stop_loss}, TP={take_profit}")
                    else:
                        logger.warning(f"Không thể cập nhật SL/TP cho {symbol} {position_side}")
            
            except Exception as e:
                logger.error(f"Lỗi khi kiểm tra và cập nhật SL/TP: {str(e)}")
        
        # Thực hiện ngay lập tức một lần
        check_and_update_sltp()
        
        # Lên lịch thực hiện định kỳ
        schedule.every(check_interval).seconds.do(check_and_update_sltp)
        logger.info(f"Auto SLTP được cấu hình với khoảng thời gian kiểm tra {check_interval} giây")
        
        return True
    
    except Exception as e:
        logger.error(f"Không thể khởi động Auto SLTP Manager: {str(e)}")
        return False

def start_trailing_stop_manager():
    """Khởi động và quản lý dịch vụ Trailing Stop Manager"""
    try:
        # Tải cấu hình
        config = load_config()
        trailing_config = config.get('trailing_stop_settings', {})
        enabled = trailing_config.get('enabled', False)
        check_interval = trailing_config.get('check_interval', 15)
        activation_percent = trailing_config.get('activation_percent', 0.5)
        trailing_percent = trailing_config.get('trailing_percent', 0.2)
        
        if not enabled:
            logger.info("Trailing Stop Manager đã bị tắt trong cấu hình")
            return False
        
        # Lưu trữ trailing stops cho mỗi vị thế
        trailing_stops = {}
        
        # Thiết lập lên lịch kiểm tra
        def check_and_update_trailing_stop():
            """Kiểm tra và cập nhật trailing stop cho các vị thế"""
            try:
                # Lấy danh sách vị thế đang mở
                positions = api_client.get_positions()
                active_positions = [p for p in positions if abs(float(p.get('positionAmt', 0))) > 0]
                
                if not active_positions:
                    logger.debug("Không có vị thế đang mở để cập nhật trailing stop")
                    return
                
                # Xử lý từng vị thế
                for position in active_positions:
                    symbol = position.get('symbol', '')
                    position_amt = float(position.get('positionAmt', 0))
                    entry_price = float(position.get('entryPrice', 0))
                    mark_price = float(position.get('markPrice', 0))
                    
                    if position_amt == 0 or entry_price == 0:
                        continue
                    
                    # Xác định hướng vị thế
                    position_side = 'LONG' if position_amt > 0 else 'SHORT'
                    
                    # Lấy giá thị trường hiện tại
                    current_price = api_client.get_symbol_price(symbol)
                    if not current_price:
                        logger.warning(f"Không thể lấy giá hiện tại cho {symbol}")
                        continue
                    
                    # Kiểm tra xem vị thế có trong trailing_stops chưa
                    position_key = f"{symbol}_{position_side}"
                    if position_key not in trailing_stops:
                        trailing_stops[position_key] = {
                            'activated': False,
                            'trailing_stop': None
                        }
                    
                    # Kiểm tra nếu đã đạt ngưỡng kích hoạt
                    is_activated = trailing_stops[position_key]['activated']
                    current_trailing_stop = trailing_stops[position_key]['trailing_stop']
                    
                    # Tính toán mức lợi nhuận hiện tại
                    profit_percent = 0
                    if position_side == 'LONG':
                        profit_percent = (current_price - entry_price) / entry_price * 100
                    else:  # SHORT
                        profit_percent = (entry_price - current_price) / entry_price * 100
                    
                    # Nếu chưa kích hoạt, kiểm tra xem đã đạt ngưỡng chưa
                    if not is_activated:
                        if profit_percent >= activation_percent:
                            trailing_stops[position_key]['activated'] = True
                            # Đặt trailing stop ban đầu
                            if position_side == 'LONG':
                                trailing_stop = current_price * (1 - trailing_percent / 100)
                            else:  # SHORT
                                trailing_stop = current_price * (1 + trailing_percent / 100)
                            
                            trailing_stops[position_key]['trailing_stop'] = trailing_stop
                            logger.info(f"Đã kích hoạt trailing stop cho {symbol} {position_side} tại {trailing_stop}")
                    
                    # Nếu đã kích hoạt, cập nhật trailing stop theo giá thị trường
                    elif is_activated and current_trailing_stop is not None:
                        # Cập nhật trailing stop theo giá mới
                        if position_side == 'LONG':
                            # Nếu giá tăng, cập nhật trailing stop
                            new_trailing_stop = current_price * (1 - trailing_percent / 100)
                            if new_trailing_stop > current_trailing_stop:
                                trailing_stops[position_key]['trailing_stop'] = new_trailing_stop
                                logger.info(f"Đã cập nhật trailing stop cho {symbol} {position_side} lên {new_trailing_stop}")
                            
                            # Kiểm tra nếu giá giảm xuống dưới trailing stop, đóng vị thế
                            if current_price <= current_trailing_stop:
                                # Đóng vị thế
                                result = api_client.close_position(symbol=symbol, position_side=position_side)
                                if result:
                                    logger.info(f"Đã đóng vị thế {symbol} {position_side} theo trailing stop tại {current_price}")
                                    # Xóa khỏi danh sách theo dõi
                                    trailing_stops.pop(position_key, None)
                                else:
                                    logger.warning(f"Không thể đóng vị thế {symbol} {position_side} theo trailing stop")
                        
                        else:  # SHORT
                            # Nếu giá giảm, cập nhật trailing stop
                            new_trailing_stop = current_price * (1 + trailing_percent / 100)
                            if new_trailing_stop < current_trailing_stop:
                                trailing_stops[position_key]['trailing_stop'] = new_trailing_stop
                                logger.info(f"Đã cập nhật trailing stop cho {symbol} {position_side} xuống {new_trailing_stop}")
                            
                            # Kiểm tra nếu giá tăng lên trên trailing stop, đóng vị thế
                            if current_price >= current_trailing_stop:
                                # Đóng vị thế
                                result = api_client.close_position(symbol=symbol, position_side=position_side)
                                if result:
                                    logger.info(f"Đã đóng vị thế {symbol} {position_side} theo trailing stop tại {current_price}")
                                    # Xóa khỏi danh sách theo dõi
                                    trailing_stops.pop(position_key, None)
                                else:
                                    logger.warning(f"Không thể đóng vị thế {symbol} {position_side} theo trailing stop")
            
            except Exception as e:
                logger.error(f"Lỗi khi kiểm tra và cập nhật trailing stop: {str(e)}")
        
        # Thực hiện ngay lập tức một lần
        check_and_update_trailing_stop()
        
        # Lên lịch thực hiện định kỳ
        schedule.every(check_interval).seconds.do(check_and_update_trailing_stop)
        logger.info(f"Trailing Stop cấu hình với kích hoạt {activation_percent}%, duy trì {trailing_percent}%, kiểm tra mỗi {check_interval}s")
        
        return True
    
    except Exception as e:
        logger.error(f"Không thể khởi động Trailing Stop Manager: {str(e)}")
        return False

def start_market_monitor():
    """Khởi động và quản lý dịch vụ Market Monitor"""
    try:
        # Tải cấu hình
        config = load_config()
        market_monitor_config = config.get('market_monitor_settings', {})
        enabled = market_monitor_config.get('enabled', False)
        check_interval = market_monitor_config.get('check_interval', 60)
        symbols = market_monitor_config.get('symbols', ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'])
        volatility_threshold = market_monitor_config.get('volatility_threshold', 3.0)
        
        if not enabled:
            logger.info("Market Monitor đã bị tắt trong cấu hình")
            return False
        
        # Lưu trữ giá trước đó
        previous_prices = {}
        
        # Thiết lập lên lịch kiểm tra
        def check_market_conditions():
            """Kiểm tra điều kiện thị trường và gửi cảnh báo"""
            try:
                nonlocal previous_prices
                
                for symbol in symbols:
                    # Lấy giá hiện tại
                    current_price = api_client.get_symbol_price(symbol)
                    if not current_price:
                        logger.warning(f"Không thể lấy giá hiện tại cho {symbol}")
                        continue
                    
                    # Nếu không có giá trước đó, lưu lại và tiếp tục
                    if symbol not in previous_prices:
                        previous_prices[symbol] = current_price
                        continue
                    
                    # Tính toán % thay đổi
                    previous_price = previous_prices[symbol]
                    price_change_percent = ((current_price - previous_price) / previous_price) * 100
                    
                    # Kiểm tra ngưỡng biến động
                    if abs(price_change_percent) >= volatility_threshold:
                        # Xác định hướng
                        direction = "TĂNG" if price_change_percent > 0 else "GIẢM"
                        
                        # Gửi cảnh báo
                        message = (
                            f"<b>⚠️ Cảnh báo biến động {symbol}</b>\n\n"
                            f"Giá {direction} mạnh: <b>{abs(price_change_percent):.2f}%</b>\n"
                            f"Giá trước: {previous_price:.2f}\n"
                            f"Giá hiện tại: {current_price:.2f}\n\n"
                            f"<i>Thời gian: {datetime.now().strftime('%H:%M:%S')}</i>"
                        )
                        
                        # Import mô-đun Telegram và gửi thông báo
                        try:
                            telegram_module = import_module_dynamically('telegram_notifier')
                            if telegram_module:
                                telegram_module.send_message(message=message)
                                logger.info(f"Đã gửi cảnh báo biến động cho {symbol}: {price_change_percent:.2f}%")
                        except Exception as e:
                            logger.error(f"Không thể gửi cảnh báo Telegram: {str(e)}")
                    
                    # Cập nhật giá trước đó
                    previous_prices[symbol] = current_price
            
            except Exception as e:
                logger.error(f"Lỗi khi kiểm tra điều kiện thị trường: {str(e)}")
        
        # Thực hiện ngay lập tức một lần
        check_market_conditions()
        
        # Lên lịch thực hiện định kỳ
        schedule.every(check_interval).seconds.do(check_market_conditions)
        logger.info(f"Market Monitor theo dõi các cặp {', '.join(symbols)} với ngưỡng biến động {volatility_threshold}%")
        
        return True
    
    except Exception as e:
        logger.error(f"Không thể khởi động Market Monitor: {str(e)}")
        return False

def scheduler_thread():
    """Thread quản lý lên lịch thực hiện"""
    global running
    logger.info("Đã khởi động thread lên lịch thực hiện")
    
    while running:
        schedule.run_pending()
        time.sleep(1)
    
    logger.info("Thread lên lịch thực hiện đã dừng")

def start_services():
    """Khởi động tất cả các dịch vụ"""
    global services
    
    try:
        # Khởi động Auto SLTP Manager
        sltp_manager_started = start_sltp_manager()
        services['sltp_manager'] = {
            'active': sltp_manager_started,
            'started_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S') if sltp_manager_started else None
        }
        
        # Khởi động Trailing Stop Manager
        trailing_stop_manager_started = start_trailing_stop_manager()
        services['trailing_stop_manager'] = {
            'active': trailing_stop_manager_started,
            'started_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S') if trailing_stop_manager_started else None
        }
        
        # Khởi động Market Monitor
        market_monitor_started = start_market_monitor()
        services['market_monitor'] = {
            'active': market_monitor_started,
            'started_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S') if market_monitor_started else None
        }
        
        # Gửi thông báo trạng thái dịch vụ
        active_services = [name for name, info in services.items() if info['active']]
        inactive_services = [name for name, info in services.items() if not info['active']]
        
        logger.info(f"Dịch vụ đang hoạt động: {', '.join(active_services) if active_services else 'Không có'}")
        logger.info(f"Dịch vụ không hoạt động: {', '.join(inactive_services) if inactive_services else 'Không có'}")
        
        return len(active_services) > 0
    
    except Exception as e:
        logger.error(f"Lỗi khi khởi động dịch vụ: {str(e)}")
        return False

def check_services_status():
    """Kiểm tra trạng thái các dịch vụ và khởi động lại nếu cần"""
    global services
    
    try:
        # Kiểm tra từng dịch vụ
        for service_name, service_info in services.items():
            if not service_info['active']:
                logger.warning(f"Dịch vụ {service_name} không hoạt động, thử khởi động lại...")
                
                # Thử khởi động lại dịch vụ
                if service_name == 'sltp_manager':
                    started = start_sltp_manager()
                elif service_name == 'trailing_stop_manager':
                    started = start_trailing_stop_manager()
                elif service_name == 'market_monitor':
                    started = start_market_monitor()
                else:
                    started = False
                
                # Cập nhật trạng thái
                services[service_name]['active'] = started
                if started:
                    services[service_name]['started_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(f"Đã khởi động lại dịch vụ {service_name}")
                else:
                    logger.error(f"Không thể khởi động lại dịch vụ {service_name}")
    
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra trạng thái dịch vụ: {str(e)}")

def main():
    """Hàm chính của dịch vụ hợp nhất"""
    global running, scheduler
    
    try:
        # Đăng ký bộ xử lý tín hiệu
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Lưu PID
        save_pid()
        
        logger.info(f"Khởi động Dịch vụ hợp nhất v{VERSION}")
        
        # Khởi tạo API client
        if not initialize_api_client():
            logger.error("Không thể khởi tạo API client, dừng dịch vụ")
            return 1
        
        # Khởi tạo Telegram
        initialize_telegram()
        
        # Khởi động các dịch vụ
        if not start_services():
            logger.warning("Không có dịch vụ nào được khởi động thành công")
        
        # Lên lịch kiểm tra trạng thái dịch vụ
        schedule.every(5).minutes.do(check_services_status)
        
        # Khởi động thread lên lịch
        scheduler = threading.Thread(target=scheduler_thread)
        scheduler.daemon = True
        scheduler.start()
        
        # Vòng lặp chính
        while running:
            # Đơn giản chỉ chờ thread lên lịch thực hiện công việc
            time.sleep(1)
        
        logger.info("Dịch vụ hợp nhất đang thoát...")
        return 0
    
    except KeyboardInterrupt:
        logger.info("Đã nhận KeyboardInterrupt, đang thoát...")
        running = False
        return 0
    
    except Exception as e:
        logger.error(f"Lỗi không xử lý được trong dịch vụ hợp nhất: {str(e)}")
        return 1
    
    finally:
        # Đảm bảo xóa file PID khi thoát
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
                logger.info(f"Đã xóa file PID")
        except:
            pass

if __name__ == "__main__":
    sys.exit(main())