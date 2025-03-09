#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script giám sát giá liên tục và thông báo khi phát hiện vấn đề với giá.
"""

import time
import logging
import schedule
import threading
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# Import các module cần thiết
from price_validator import price_validator, get_verified_price
from prices_cache import update_prices, get_all_prices

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("price_monitor.log")
    ]
)
logger = logging.getLogger(__name__)

# Danh sách symbols cần giám sát
TARGET_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT",
    "DOGEUSDT", "LTCUSDT", "DOTUSDT", "XRPUSDT",
    "AVAXUSDT", "LINKUSDT", "ATOMUSDT"
]

class PriceMonitor:
    """
    Lớp giám sát giá của các cặp tiền và thông báo khi có vấn đề.
    """
    
    def __init__(self, symbols: List[str], api=None, check_interval: int = 60):
        """
        Khởi tạo PriceMonitor.
        
        Args:
            symbols (List[str]): Danh sách các symbols cần giám sát
            api: Instance của BinanceAPI nếu có
            check_interval (int): Khoảng thời gian (giây) giữa các lần kiểm tra
        """
        self.symbols = symbols
        self.api = api
        self.check_interval = check_interval
        self.running = False
        self.monitor_thread = None
        self.price_history = {}  # Lưu lịch sử giá để phát hiện biến động bất thường
        self.status = {
            'last_update': None,
            'reliable_symbols': [],
            'unreliable_symbols': [],
            'price_errors': {},
            'trading_enabled': True
        }
        
    def check_prices(self) -> Dict[str, Any]:
        """
        Kiểm tra giá của tất cả các symbols đang giám sát.
        
        Returns:
            Dict[str, Any]: Trạng thái hiện tại
        """
        reliable_symbols = []
        unreliable_symbols = []
        price_errors = {}
        prices = {}
        
        for symbol in self.symbols:
            try:
                price, is_reliable = get_verified_price(symbol, self.api)
                
                if price:
                    prices[symbol] = price
                    # Cập nhật lịch sử giá
                    if symbol not in self.price_history:
                        self.price_history[symbol] = []
                    
                    self.price_history[symbol].append({
                        'timestamp': int(time.time()),
                        'price': price,
                        'is_reliable': is_reliable
                    })
                    
                    # Giữ lịch sử giá trong 24 giờ
                    current_time = int(time.time())
                    self.price_history[symbol] = [
                        entry for entry in self.price_history[symbol]
                        if current_time - entry['timestamp'] <= 86400
                    ]
                    
                    if is_reliable:
                        reliable_symbols.append(symbol)
                    else:
                        unreliable_symbols.append(symbol)
                else:
                    price_errors[symbol] = "Không lấy được giá"
                    unreliable_symbols.append(symbol)
                    
            except Exception as e:
                logger.error(f"Lỗi khi kiểm tra giá {symbol}: {str(e)}")
                price_errors[symbol] = str(e)
                unreliable_symbols.append(symbol)
        
        # Cập nhật trạng thái
        self.status = {
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'reliable_symbols': reliable_symbols,
            'unreliable_symbols': unreliable_symbols,
            'price_errors': price_errors,
            'trading_enabled': price_validator.trading_enabled
        }
        
        # Thông báo nếu có nhiều symbols không đáng tin cậy
        if len(unreliable_symbols) > 0:
            logger.warning(f"Có {len(unreliable_symbols)} symbols không đáng tin cậy: {', '.join(unreliable_symbols)}")
            
            # Gửi thông báo nếu số symbols không đáng tin cậy vượt ngưỡng
            if len(unreliable_symbols) >= 3:
                self.send_alert(
                    f"⚠️ CẢNH BÁO: {len(unreliable_symbols)}/{len(self.symbols)} symbols không đáng tin cậy",
                    f"Các symbols không đáng tin cậy: {', '.join(unreliable_symbols)}\n"
                    f"Giao dịch tự động đã {'' if price_validator.trading_enabled else 'bị tạm dừng'}."
                )
                
        return self.status
    
    def detect_price_anomalies(self) -> List[Dict[str, Any]]:
        """
        Phát hiện những biến động giá bất thường.
        
        Returns:
            List[Dict[str, Any]]: Danh sách các anomaly phát hiện được
        """
        anomalies = []
        
        for symbol, history in self.price_history.items():
            if len(history) < 3:  # Cần ít nhất 3 điểm dữ liệu
                continue
                
            # Lấy 3 giá gần nhất
            recent_prices = sorted(history, key=lambda x: x['timestamp'], reverse=True)[:3]
            
            # Tính phần trăm thay đổi giữa giá mới nhất và giá cũ nhất trong 3 điểm
            if recent_prices[0]['price'] and recent_prices[2]['price']:
                price_change = abs(recent_prices[0]['price'] - recent_prices[2]['price']) / recent_prices[2]['price']
                
                # Nếu thay đổi lớn hơn 3% trong thời gian ngắn, coi là bất thường
                if price_change > 0.03:
                    anomalies.append({
                        'symbol': symbol,
                        'timestamp': recent_prices[0]['timestamp'],
                        'current_price': recent_prices[0]['price'],
                        'previous_price': recent_prices[2]['price'],
                        'change_percent': price_change * 100,
                        'is_reliable': recent_prices[0]['is_reliable']
                    })
        
        # Thông báo nếu phát hiện anomaly
        if anomalies:
            logger.warning(f"Phát hiện {len(anomalies)} biến động giá bất thường")
            
            # Gửi thông báo
            message = "🔔 Phát hiện biến động giá bất thường:\n\n"
            for anomaly in anomalies:
                message += f"• {anomaly['symbol']}: {anomaly['change_percent']:.2f}% "
                message += f"({'tăng' if anomaly['current_price'] > anomaly['previous_price'] else 'giảm'})\n"
                message += f"  {anomaly['previous_price']} → {anomaly['current_price']}\n"
                
            self.send_alert("Biến động giá bất thường", message)
            
        return anomalies
    
    def send_alert(self, title: str, message: str) -> None:
        """
        Gửi cảnh báo.
        
        Args:
            title (str): Tiêu đề thông báo
            message (str): Nội dung thông báo
        """
        logger.critical(f"{title}: {message}")
        
        # TODO: Tích hợp với Telegram hoặc Email để gửi thông báo
        try:
            # Ghi ra file alerts.log
            with open("price_alerts.log", "a") as f:
                f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {title}\n")
                f.write(f"{message}\n")
                f.write("-" * 50 + "\n")
        except Exception as e:
            logger.error(f"Lỗi khi ghi alert: {str(e)}")
    
    def save_status(self) -> None:
        """Lưu trạng thái hiện tại vào file."""
        try:
            with open("price_monitor_status.json", "w") as f:
                json.dump(self.status, f, indent=2)
        except Exception as e:
            logger.error(f"Lỗi khi lưu trạng thái: {str(e)}")
    
    def monitor_job(self) -> None:
        """Hàm chạy định kỳ để giám sát giá."""
        self.check_prices()
        self.detect_price_anomalies()
        self.save_status()
    
    def start(self) -> None:
        """Bắt đầu giám sát giá."""
        if self.running:
            logger.warning("Price monitor đã đang chạy")
            return
            
        self.running = True
        logger.info(f"Bắt đầu giám sát giá cho {len(self.symbols)} symbols")
        
        # Chạy ngay một lần
        self.monitor_job()
        
        # Thiết lập lịch trình
        schedule.every(self.check_interval).seconds.do(self.monitor_job)
        
        # Tạo thread để chạy lịch trình
        def run_scheduler():
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        
        self.monitor_thread = threading.Thread(target=run_scheduler)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop(self) -> None:
        """Dừng giám sát giá."""
        if not self.running:
            logger.warning("Price monitor không chạy")
            return
            
        self.running = False
        logger.info("Đã dừng giám sát giá")
        
        # Lưu trạng thái lần cuối
        self.save_status()
        
        # Hủy tất cả công việc đã lên lịch
        schedule.clear()
        
        # Đợi thread kết thúc
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
            self.monitor_thread = None

def start_price_monitor(api=None):
    """
    Khởi động monitor giám sát giá.
    
    Args:
        api: Instance của BinanceAPI nếu có
        
    Returns:
        PriceMonitor: Instance của PriceMonitor
    """
    monitor = PriceMonitor(TARGET_SYMBOLS, api)
    monitor.start()
    return monitor

if __name__ == "__main__":
    logger.info("Khởi động price_monitor.py")
    
    # Có thể import BinanceAPI nếu cần
    try:
        from binance_api import BinanceAPI
        from binance_api_fixes import apply_fixes_to_api
        
        api = BinanceAPI()
        api = apply_fixes_to_api(api)
        
        logger.info("Đã khởi tạo API Binance")
        
        monitor = start_price_monitor(api)
        
        # Giữ script chạy
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            logger.info("Đã nhận tín hiệu thoát")
            monitor.stop()
            
    except ImportError:
        logger.info("Chạy mà không có BinanceAPI")
        monitor = start_price_monitor()
        
        # Giữ script chạy
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            logger.info("Đã nhận tín hiệu thoát")
            monitor.stop()