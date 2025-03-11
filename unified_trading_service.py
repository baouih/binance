#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified Trading Service - Dịch vụ giao dịch hợp nhất
====================================================

Script này kết hợp nhiều dịch vụ riêng lẻ thành một dịch vụ duy nhất:
1. Auto SLTP Manager (Quản lý Stop Loss/Take Profit tự động)
2. Trailing Stop Service (Quản lý Trailing Stop)
3. Market Monitor (Giám sát thị trường)

Lợi ích:
- Giảm số lượng process cần chạy
- Tối ưu tài nguyên hệ thống
- Quản lý tập trung tất cả dịch vụ
- Dễ dàng khởi động/dừng toàn bộ hệ thống

Cách sử dụng:
    python unified_trading_service.py [--no-sltp] [--no-trailing] [--no-market] [--interval 60]

Tham số:
    --no-sltp: Không chạy Auto SLTP Manager
    --no-trailing: Không chạy Trailing Stop Service
    --no-market: Không chạy Market Monitor
    --interval: Đặt khoảng thời gian kiểm tra (giây), mặc định 60s
"""

import os
import sys
import time
import signal
import argparse
import threading
import logging
import importlib
import json
from datetime import datetime

# Thiết lập logging
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('unified_service')
logger.setLevel(logging.INFO)

# File handler
log_file = 'unified_trading_service.log'
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

# Module imports động
def import_module_safely(module_name):
    """Import module an toàn, nếu import lỗi sẽ trả về None."""
    try:
        if os.path.exists(f"{module_name}.py"):
            spec = importlib.util.spec_from_file_location(module_name, f"{module_name}.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            logger.info(f"Đã import thành công module {module_name}")
            return module
        else:
            logger.error(f"Không tìm thấy file {module_name}.py")
            return None
    except Exception as e:
        logger.error(f"Lỗi khi import module {module_name}: {e}")
        return None

class UnifiedTradingService:
    def __init__(self, run_sltp=True, run_trailing=True, run_market=True, interval=60):
        """Khởi tạo dịch vụ giao dịch hợp nhất."""
        self.run_sltp = run_sltp
        self.run_trailing = run_trailing
        self.run_market = run_market
        self.interval = interval
        self.running = False
        self.threads = []
        self.pid = os.getpid()
        
        # Ghi PID để theo dõi
        with open('unified_trading_service.pid', 'w') as f:
            f.write(str(self.pid))
        
        # Cài đặt xử lý tín hiệu
        signal.signal(signal.SIGTERM, self.handle_exit)
        signal.signal(signal.SIGINT, self.handle_exit)
        
        # Import các module cần thiết
        if self.run_sltp:
            self.sltp_config = self.load_sltp_config()
        
        logger.info(f"Khởi tạo Unified Trading Service với PID {self.pid}")
        logger.info(f"Các dịch vụ được bật: "
                    f"SLTP={'Có' if run_sltp else 'Không'}, "
                    f"Trailing Stop={'Có' if run_trailing else 'Không'}, "
                    f"Market Monitor={'Có' if run_market else 'Không'}")
    
    def load_sltp_config(self):
        """Load cấu hình SLTP từ file."""
        config_path = "configs/sltp_config.json"
        if not os.path.exists(config_path):
            config_path = "sltp_config.json"
            if not os.path.exists(config_path):
                logger.warning("Không tìm thấy file cấu hình SLTP, sử dụng giá trị mặc định")
                return {"stop_loss_percent": 2.0, "take_profit_percent": 3.0}
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Đã tải cấu hình SLTP từ {config_path}")
            return config
        except Exception as e:
            logger.error(f"Lỗi khi đọc file cấu hình SLTP: {e}")
            return {"stop_loss_percent": 2.0, "take_profit_percent": 3.0}
    
    def handle_exit(self, signum, frame):
        """Xử lý khi nhận tín hiệu thoát."""
        logger.info("Nhận được tín hiệu thoát, đang dừng dịch vụ...")
        self.running = False
        
        # Xóa file PID
        try:
            os.remove('unified_trading_service.pid')
        except:
            pass
        
        # Đợi tất cả threads kết thúc
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=5)
        
        logger.info("Unified Trading Service đã dừng")
        sys.exit(0)
    
    def send_notification(self, message, category="system"):
        """Gửi thông báo về trạng thái dịch vụ."""
        try:
            # Kiểm tra telegram_notifier có tồn tại không
            if os.path.exists('telegram_notifier.py'):
                import telegram_notifier
                telegram_notifier.send_message(message, category)
                logger.info(f"Đã gửi thông báo: {message}")
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo: {e}")
    
    def auto_sltp_service(self):
        """Dịch vụ Auto SLTP."""
        logger.info("Bắt đầu dịch vụ Auto SLTP")
        
        # Import BinanceAPI một lần
        try:
            from binance_api import BinanceAPI
            api = BinanceAPI()
            logger.info("Đã khởi tạo kết nối Binance API")
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo Binance API: {e}")
            return
        
        sl_percent = self.sltp_config.get('stop_loss_percent', 2.0)
        tp_percent = self.sltp_config.get('take_profit_percent', 3.0)
        logger.info(f"Auto SLTP được cấu hình với SL={sl_percent}%, TP={tp_percent}%")
        
        last_notification_time = 0
        
        while self.running:
            try:
                # Lấy tất cả các vị thế đang mở
                positions = api.get_positions()
                
                if positions:
                    logger.info(f"Đang kiểm tra {len(positions)} vị thế để cập nhật SL/TP")
                    
                    for position in positions:
                        symbol = position['symbol']
                        side = position['side']
                        size = float(position['positionAmt'])
                        entry_price = float(position['entryPrice'])
                        
                        # Bỏ qua vị thế zero
                        if size == 0:
                            continue
                        
                        # Tính toán giá SL/TP
                        if side == 'LONG':
                            sl_price = entry_price * (1 - sl_percent/100)
                            tp_price = entry_price * (1 + tp_percent/100)
                        else:  # SHORT
                            sl_price = entry_price * (1 + sl_percent/100)
                            tp_price = entry_price * (1 - tp_percent/100)
                        
                        # Làm tròn giá theo quy tắc của sàn
                        # (Phần này có thể cần cải thiện để lấy thông tin precision từ API)
                        sl_price = round(sl_price, 2)
                        tp_price = round(tp_price, 2)
                        
                        # Đặt SL/TP
                        try:
                            api.set_stop_loss_take_profit(symbol, side, sl_price, tp_price)
                            logger.info(f"Đã đặt SL/TP cho {symbol} {side}: SL={sl_price}, TP={tp_price}")
                        except Exception as e:
                            logger.error(f"Lỗi khi đặt SL/TP cho {symbol}: {e}")
                else:
                    # Gửi thông báo không quá thường xuyên (mỗi 30 phút)
                    current_time = time.time()
                    if current_time - last_notification_time > 1800:  # 30 phút
                        logger.info("Không có vị thế nào đang mở, chờ đến lần kiểm tra tiếp theo")
                        last_notification_time = current_time
            
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp Auto SLTP: {e}")
            
            # Chờ đến lần kiểm tra tiếp theo
            time.sleep(self.interval)
    
    def trailing_stop_service(self):
        """Dịch vụ Trailing Stop."""
        logger.info("Bắt đầu dịch vụ Trailing Stop")
        
        # Import BinanceAPI một lần
        try:
            from binance_api import BinanceAPI
            api = BinanceAPI()
            logger.info("Đã khởi tạo kết nối Binance API")
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo Binance API: {e}")
            return
        
        # Tải cấu hình trailing stop
        trailing_config = {}
        if os.path.exists("configs/trailing_config.json"):
            try:
                with open("configs/trailing_config.json", 'r') as f:
                    trailing_config = json.load(f)
            except:
                pass
        
        # Sử dụng giá trị mặc định nếu không có cấu hình
        activation_percent = trailing_config.get('activation_percent', 1.0)
        callback_rate = trailing_config.get('callback_rate', 0.5)
        
        logger.info(f"Trailing Stop cấu hình với Activation={activation_percent}%, Callback={callback_rate}%")
        
        # Lưu trữ thông tin vị thế và trailing stop
        position_highs = {}  # Lưu giá cao nhất/thấp nhất của mỗi vị thế
        trailing_active = {}  # Trạng thái trailing stop cho mỗi vị thế
        
        while self.running:
            try:
                # Lấy tất cả các vị thế đang mở
                positions = api.get_positions()
                
                if positions:
                    logger.info(f"Đang kiểm tra {len(positions)} vị thế để cập nhật Trailing Stop")
                    
                    current_prices = {}  # Lưu giá hiện tại của các cặp giao dịch
                    
                    # Lấy giá hiện tại của tất cả các symbol trong vị thế
                    symbols = set(p['symbol'] for p in positions if float(p['positionAmt']) != 0)
                    for symbol in symbols:
                        try:
                            price_data = api.get_symbol_price(symbol)
                            current_prices[symbol] = float(price_data['price'])
                        except Exception as e:
                            logger.error(f"Lỗi khi lấy giá của {symbol}: {e}")
                    
                    # Kiểm tra và cập nhật trailing stop cho mỗi vị thế
                    for position in positions:
                        symbol = position['symbol']
                        side = position['side']
                        size = float(position['positionAmt'])
                        entry_price = float(position['entryPrice'])
                        
                        # Bỏ qua vị thế zero
                        if size == 0:
                            continue
                        
                        # Bỏ qua nếu không có giá hiện tại
                        if symbol not in current_prices:
                            continue
                        
                        current_price = current_prices[symbol]
                        
                        # Khởi tạo nếu chưa có trong dict
                        if symbol not in position_highs:
                            position_highs[symbol] = {}
                        if side not in position_highs[symbol]:
                            position_highs[symbol][side] = entry_price
                        
                        # Thiết lập key cho trailing_active
                        pos_key = f"{symbol}_{side}"
                        if pos_key not in trailing_active:
                            trailing_active[pos_key] = False
                        
                        # Cập nhật giá cao nhất/thấp nhất
                        if side == 'LONG':
                            # Với vị thế Long, theo dõi giá cao nhất
                            if current_price > position_highs[symbol][side]:
                                position_highs[symbol][side] = current_price
                            
                            # Kiểm tra điều kiện kích hoạt trailing stop
                            profit_percent = (current_price - entry_price) / entry_price * 100
                            
                            if not trailing_active[pos_key] and profit_percent >= activation_percent:
                                trailing_active[pos_key] = True
                                logger.info(f"Đã kích hoạt Trailing Stop cho {symbol} LONG tại mức lợi nhuận {profit_percent:.2f}%")
                            
                            # Nếu trailing stop đã kích hoạt, kiểm tra điều kiện đóng vị thế
                            if trailing_active[pos_key]:
                                high_price = position_highs[symbol][side]
                                drawdown = (high_price - current_price) / high_price * 100
                                
                                if drawdown >= callback_rate:
                                    # Đóng vị thế
                                    try:
                                        logger.info(f"Trailing Stop được kích hoạt cho {symbol} LONG: Drawdown {drawdown:.2f}% từ đỉnh {high_price}")
                                        api.close_position(symbol, 'LONG')
                                        self.send_notification(
                                            f"🔄 Trailing Stop: Đã đóng vị thế {symbol} LONG\n"
                                            f"Giá đỉnh: {high_price}\n"
                                            f"Giá hiện tại: {current_price}\n"
                                            f"Drawdown: {drawdown:.2f}%"
                                        )
                                        # Xóa khỏi danh sách theo dõi
                                        trailing_active.pop(pos_key, None)
                                    except Exception as e:
                                        logger.error(f"Lỗi khi đóng vị thế {symbol} LONG: {e}")
                        
                        else:  # SHORT
                            # Với vị thế Short, theo dõi giá thấp nhất
                            if current_price < position_highs[symbol][side] or position_highs[symbol][side] == entry_price:
                                position_highs[symbol][side] = current_price
                            
                            # Kiểm tra điều kiện kích hoạt trailing stop
                            profit_percent = (entry_price - current_price) / entry_price * 100
                            
                            if not trailing_active[pos_key] and profit_percent >= activation_percent:
                                trailing_active[pos_key] = True
                                logger.info(f"Đã kích hoạt Trailing Stop cho {symbol} SHORT tại mức lợi nhuận {profit_percent:.2f}%")
                            
                            # Nếu trailing stop đã kích hoạt, kiểm tra điều kiện đóng vị thế
                            if trailing_active[pos_key]:
                                low_price = position_highs[symbol][side]
                                drawdown = (current_price - low_price) / low_price * 100
                                
                                if drawdown >= callback_rate:
                                    # Đóng vị thế
                                    try:
                                        logger.info(f"Trailing Stop được kích hoạt cho {symbol} SHORT: Drawdown {drawdown:.2f}% từ đáy {low_price}")
                                        api.close_position(symbol, 'SHORT')
                                        self.send_notification(
                                            f"🔄 Trailing Stop: Đã đóng vị thế {symbol} SHORT\n"
                                            f"Giá đáy: {low_price}\n"
                                            f"Giá hiện tại: {current_price}\n"
                                            f"Drawdown: {drawdown:.2f}%"
                                        )
                                        # Xóa khỏi danh sách theo dõi
                                        trailing_active.pop(pos_key, None)
                                    except Exception as e:
                                        logger.error(f"Lỗi khi đóng vị thế {symbol} SHORT: {e}")
                
                else:
                    logger.info("Không có vị thế nào đang mở để áp dụng Trailing Stop")
                    # Xóa dữ liệu vị thế cũ
                    position_highs.clear()
                    trailing_active.clear()
            
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp Trailing Stop: {e}")
            
            # Chờ đến lần kiểm tra tiếp theo
            time.sleep(self.interval)
    
    def market_monitor_service(self):
        """Dịch vụ giám sát thị trường."""
        logger.info("Bắt đầu dịch vụ Market Monitor")
        
        # Import BinanceAPI một lần
        try:
            from binance_api import BinanceAPI
            api = BinanceAPI()
            logger.info("Đã khởi tạo kết nối Binance API")
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo Binance API: {e}")
            return
        
        # Danh sách các cặp tiền cần theo dõi
        watch_symbols = ["BTCUSDT", "ETHUSDT"]
        
        # Cập nhật danh sách từ cấu hình nếu có
        if os.path.exists("configs/market_monitor_config.json"):
            try:
                with open("configs/market_monitor_config.json", 'r') as f:
                    config = json.load(f)
                    if 'watch_symbols' in config and isinstance(config['watch_symbols'], list):
                        watch_symbols = config['watch_symbols']
            except Exception as e:
                logger.error(f"Lỗi khi đọc cấu hình Market Monitor: {e}")
        
        logger.info(f"Market Monitor theo dõi các cặp: {', '.join(watch_symbols)}")
        
        # Lưu trữ giá trước đó để phát hiện biến động
        previous_prices = {}
        
        # Ngưỡng thay đổi giá để thông báo (%)
        price_alert_threshold = 1.0
        
        while self.running:
            try:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                market_update = f"📊 Cập nhật thị trường ({current_time}):\n"
                
                price_alerts = []
                
                for symbol in watch_symbols:
                    try:
                        # Lấy giá hiện tại
                        price_data = api.get_symbol_price(symbol)
                        current_price = float(price_data['price'])
                        
                        # Thêm vào cập nhật thị trường
                        market_update += f"{symbol}: ${current_price:.2f}"
                        
                        # Kiểm tra biến động giá
                        if symbol in previous_prices:
                            prev_price = previous_prices[symbol]
                            change_percent = (current_price - prev_price) / prev_price * 100
                            
                            # Thêm % thay đổi vào cập nhật
                            if change_percent > 0:
                                market_update += f" (🟢 +{change_percent:.2f}%)"
                            elif change_percent < 0:
                                market_update += f" (🔴 {change_percent:.2f}%)"
                            else:
                                market_update += f" (⚪ 0.00%)"
                            
                            # Tạo cảnh báo nếu biến động lớn
                            if abs(change_percent) >= price_alert_threshold:
                                direction = "tăng" if change_percent > 0 else "giảm"
                                alert = f"⚠️ {symbol} đã {direction} {abs(change_percent):.2f}% trong {self.interval} giây qua"
                                price_alerts.append(alert)
                        
                        # Cập nhật giá trước đó
                        previous_prices[symbol] = current_price
                        
                        market_update += "\n"
                    
                    except Exception as e:
                        logger.error(f"Lỗi khi lấy giá của {symbol}: {e}")
                        market_update += f"{symbol}: Lỗi khi lấy giá\n"
                
                # Gửi cập nhật thị trường (mỗi 5 phút)
                if time.time() % 300 < self.interval:
                    self.send_notification(market_update.strip(), "market")
                
                # Gửi cảnh báo biến động giá (ngay lập tức)
                if price_alerts:
                    alerts_message = "\n".join(price_alerts)
                    self.send_notification(alerts_message, "alert")
            
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp Market Monitor: {e}")
            
            # Chờ đến lần kiểm tra tiếp theo
            time.sleep(self.interval)
    
    def start(self):
        """Khởi động tất cả các dịch vụ."""
        logger.info("Khởi động Unified Trading Service")
        self.running = True
        
        # Gửi thông báo khởi động
        self.send_notification("🚀 Unified Trading Service đã khởi động")
        
        # Khởi động Auto SLTP Service
        if self.run_sltp:
            sltp_thread = threading.Thread(target=self.auto_sltp_service)
            sltp_thread.daemon = True
            self.threads.append(sltp_thread)
            sltp_thread.start()
            logger.info("Đã khởi động thread Auto SLTP Service")
        
        # Khởi động Trailing Stop Service
        if self.run_trailing:
            trailing_thread = threading.Thread(target=self.trailing_stop_service)
            trailing_thread.daemon = True
            self.threads.append(trailing_thread)
            trailing_thread.start()
            logger.info("Đã khởi động thread Trailing Stop Service")
        
        # Khởi động Market Monitor Service
        if self.run_market:
            market_thread = threading.Thread(target=self.market_monitor_service)
            market_thread.daemon = True
            self.threads.append(market_thread)
            market_thread.start()
            logger.info("Đã khởi động thread Market Monitor Service")
        
        try:
            # Vòng lặp chính để giữ cho process chạy
            while self.running:
                # Kiểm tra trạng thái các thread
                all_alive = all(t.is_alive() for t in self.threads)
                if not all_alive and self.running:
                    dead_threads = [i for i, t in enumerate(self.threads) if not t.is_alive()]
                    logger.error(f"Phát hiện thread đã dừng: {dead_threads}")
                    self.send_notification("⚠️ Một số dịch vụ đã ngừng hoạt động, đang thử khởi động lại...")
                    
                    # Thử khởi động lại các thread đã chết
                    for i in dead_threads:
                        if i == 0 and self.run_sltp:
                            logger.info("Khởi động lại Auto SLTP Service")
                            self.threads[i] = threading.Thread(target=self.auto_sltp_service)
                            self.threads[i].daemon = True
                            self.threads[i].start()
                        elif i == 1 and self.run_trailing:
                            logger.info("Khởi động lại Trailing Stop Service")
                            self.threads[i] = threading.Thread(target=self.trailing_stop_service)
                            self.threads[i].daemon = True
                            self.threads[i].start()
                        elif i == 2 and self.run_market:
                            logger.info("Khởi động lại Market Monitor Service")
                            self.threads[i] = threading.Thread(target=self.market_monitor_service)
                            self.threads[i].daemon = True
                            self.threads[i].start()
                
                # In trạng thái hoạt động
                if time.time() % 300 < 1:  # Mỗi 5 phút
                    logger.info("Unified Trading Service đang hoạt động bình thường")
                
                time.sleep(5)  # Kiểm tra mỗi 5 giây
        
        except KeyboardInterrupt:
            logger.info("Nhận được KeyboardInterrupt, dừng dịch vụ...")
            self.running = False
        
        finally:
            # Đảm bảo tất cả threads được dừng sạch sẽ
            self.running = False
            for thread in self.threads:
                if thread.is_alive():
                    thread.join(timeout=5)
            
            logger.info("Tất cả các dịch vụ đã dừng")
            self.send_notification("🛑 Unified Trading Service đã dừng")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unified Trading Service")
    parser.add_argument("--no-sltp", action="store_true", help="Không chạy Auto SLTP Manager")
    parser.add_argument("--no-trailing", action="store_true", help="Không chạy Trailing Stop Service")
    parser.add_argument("--no-market", action="store_true", help="Không chạy Market Monitor")
    parser.add_argument("--interval", type=int, default=60, help="Khoảng thời gian kiểm tra (giây)")
    args = parser.parse_args()
    
    service = UnifiedTradingService(
        run_sltp=not args.no_sltp,
        run_trailing=not args.no_trailing,
        run_market=not args.no_market,
        interval=args.interval
    )
    
    service.start()