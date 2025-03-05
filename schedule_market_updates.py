#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script lập lịch cập nhật dữ liệu thị trường 

Script này tự động lập lịch cập nhật dữ liệu thị trường cho tất cả các cặp tiền,
với các khung thời gian khác nhau cho từng cặp dựa trên mức độ ưu tiên và biến động.
"""

import os
import sys
import time
import json
import signal
import logging
import schedule
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Thêm thư mục gốc vào đường dẫn tìm kiếm
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import các module cần thiết
try:
    from market_data_updater import MarketDataUpdater
except ImportError as e:
    print(f"Lỗi khi import modules: {e}")
    sys.exit(1)

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("market_updates_scheduler.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("market_scheduler")

# Các cặp tiền được hỗ trợ và mức độ ưu tiên của chúng (1-10, 10 là cao nhất)
DEFAULT_PAIRS_PRIORITY = {
    "BTCUSDT": 10,
    "ETHUSDT": 9,
    "ADAUSDT": 7,
    "BNBUSDT": 8,
    "DOGEUSDT": 7,
    "SOLUSDT": 8,
    "XRPUSDT": 7,
    "DOTUSDT": 6,
    "LTCUSDT": 6,
    "AVAXUSDT": 7,
    "MATICUSDT": 6,
    "LINKUSDT": 7,
    "ATOMUSDT": 5,
    "TRXUSDT": 5
}

# Các khung thời gian cập nhật và tần suất (giây)
DEFAULT_UPDATE_INTERVALS = {
    "high_priority": 180,  # 3 phút
    "medium_priority": 300,  # 5 phút
    "low_priority": 600    # 10 phút
}

class MarketUpdateScheduler:
    """Lớp lập lịch cập nhật dữ liệu thị trường"""
    
    def __init__(self, config_path: str = 'schedule_config.json'):
        """
        Khởi tạo lập lịch cập nhật
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình lập lịch
        """
        self.config_path = config_path
        self.updater = MarketDataUpdater()
        self.running = False
        self.update_threads = {}
        self.last_update_time = {}
        self.update_stats = {}
        self.load_or_create_config()
        
        # Thiết lập bắt tín hiệu từ hệ điều hành
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        
        logger.info("Đã khởi tạo MarketUpdateScheduler")
        
    def load_or_create_config(self) -> None:
        """Tải hoặc tạo mới cấu hình lập lịch"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                
                self.pairs_priority = config.get('pairs_priority', DEFAULT_PAIRS_PRIORITY)
                self.update_intervals = config.get('update_intervals', DEFAULT_UPDATE_INTERVALS)
                logger.info(f"Đã tải cấu hình lập lịch từ {self.config_path}")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Lỗi khi tải cấu hình: {e}, sử dụng cấu hình mặc định")
                self.pairs_priority = DEFAULT_PAIRS_PRIORITY
                self.update_intervals = DEFAULT_UPDATE_INTERVALS
        else:
            self.pairs_priority = DEFAULT_PAIRS_PRIORITY
            self.update_intervals = DEFAULT_UPDATE_INTERVALS
            self.save_config()
            logger.info(f"Đã tạo mới cấu hình lập lịch tại {self.config_path}")
    
    def save_config(self) -> None:
        """Lưu cấu hình lập lịch"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump({
                    'pairs_priority': self.pairs_priority,
                    'update_intervals': self.update_intervals,
                    'last_modified': datetime.now().isoformat()
                }, f, indent=2)
            logger.info(f"Đã lưu cấu hình lập lịch vào {self.config_path}")
        except IOError as e:
            logger.error(f"Lỗi khi lưu cấu hình: {e}")
    
    def get_update_interval(self, symbol: str) -> int:
        """
        Lấy khoảng thời gian cập nhật cho một cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            int: Khoảng thời gian cập nhật (giây)
        """
        priority = self.pairs_priority.get(symbol, 5)
        
        if priority >= 9:  # BTC, ETH
            return self.update_intervals["high_priority"]
        elif priority >= 7:  # BNB, SOL, ADA, XRP, AVAX, LINK, DOGE
            return self.update_intervals["medium_priority"]
        else:  # DOT, LTC, MATIC, ATOM, TRX
            return self.update_intervals["low_priority"]
    
    def setup_schedules(self) -> None:
        """Thiết lập lịch cập nhật cho tất cả các cặp tiền"""
        logger.info("Thiết lập lịch cập nhật thị trường")
        
        # Xóa tất cả lịch đã thiết lập trước đó
        schedule.clear()
        
        # Thiết lập lịch cập nhật cho từng cặp tiền
        for symbol in self.pairs_priority.keys():
            interval = self.get_update_interval(symbol)
            
            # Lập lịch cập nhật không đồng bộ để tránh các cập nhật xảy ra cùng lúc
            offset = list(self.pairs_priority.keys()).index(symbol) * 15  # Mỗi cặp tiền cách nhau 15 giây
            
            # Lập lịch cập nhật đầu tiên
            first_run = datetime.now() + timedelta(seconds=offset)
            schedule.every().day.at(first_run.strftime("%H:%M:%S")).do(self.update_market_data, symbol)
            
            # Sau đó cứ sau mỗi interval giây
            schedule.every(interval).seconds.do(self.update_market_data, symbol)
            
            logger.info(f"Đã lập lịch cập nhật {symbol} mỗi {interval} giây (độ ưu tiên: {self.pairs_priority[symbol]})")
        
        # Lập lịch lưu cấu hình và thống kê
        schedule.every(30).minutes.do(self.save_config)
        schedule.every(10).minutes.do(self.save_statistics)
        schedule.every().day.at("00:00").do(self.reset_daily_statistics)
        
        logger.info("Đã hoàn tất thiết lập lịch cập nhật thị trường")
    
    def update_market_data(self, symbol: str) -> bool:
        """
        Cập nhật dữ liệu thị trường cho một cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không
        """
        if symbol in self.update_threads and self.update_threads[symbol].is_alive():
            logger.warning(f"Bỏ qua cập nhật {symbol} vì cập nhật trước đó vẫn đang chạy")
            return False
        
        thread = threading.Thread(target=self._update_symbol_thread, args=(symbol,))
        thread.daemon = True
        thread.start()
        self.update_threads[symbol] = thread
        
        return True
    
    def _update_symbol_thread(self, symbol: str) -> None:
        """
        Luồng cập nhật dữ liệu thị trường cho một cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền
        """
        start_time = time.time()
        try:
            logger.info(f"Bắt đầu cập nhật {symbol}")
            success = self.updater.update_symbol(symbol)
            
            duration = time.time() - start_time
            self.last_update_time[symbol] = datetime.now()
            
            # Cập nhật thống kê
            if symbol not in self.update_stats:
                self.update_stats[symbol] = {
                    "total_updates": 0,
                    "successful_updates": 0,
                    "failed_updates": 0,
                    "total_duration": 0,
                    "max_duration": 0,
                    "min_duration": float('inf'),
                    "last_update": None,
                    "last_status": None,
                    "last_duration": None,
                    "today_updates": 0,
                    "today_successful": 0
                }
            
            self.update_stats[symbol]["total_updates"] += 1
            self.update_stats[symbol]["today_updates"] += 1
            self.update_stats[symbol]["total_duration"] += duration
            self.update_stats[symbol]["last_update"] = datetime.now().isoformat()
            self.update_stats[symbol]["last_duration"] = duration
            self.update_stats[symbol]["last_status"] = "success" if success else "failed"
            
            if success:
                self.update_stats[symbol]["successful_updates"] += 1
                self.update_stats[symbol]["today_successful"] += 1
                logger.info(f"Cập nhật {symbol} thành công ({duration:.2f}s)")
            else:
                self.update_stats[symbol]["failed_updates"] += 1
                logger.error(f"Cập nhật {symbol} thất bại ({duration:.2f}s)")
            
            self.update_stats[symbol]["max_duration"] = max(self.update_stats[symbol]["max_duration"], duration)
            self.update_stats[symbol]["min_duration"] = min(self.update_stats[symbol]["min_duration"], duration)
        
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Lỗi khi cập nhật {symbol}: {e} ({duration:.2f}s)")
            
            if symbol not in self.update_stats:
                self.update_stats[symbol] = {
                    "total_updates": 1,
                    "successful_updates": 0,
                    "failed_updates": 1,
                    "total_duration": duration,
                    "max_duration": duration,
                    "min_duration": duration,
                    "last_update": datetime.now().isoformat(),
                    "last_status": "error",
                    "last_duration": duration,
                    "today_updates": 1,
                    "today_successful": 0
                }
            else:
                self.update_stats[symbol]["total_updates"] += 1
                self.update_stats[symbol]["today_updates"] += 1
                self.update_stats[symbol]["failed_updates"] += 1
                self.update_stats[symbol]["total_duration"] += duration
                self.update_stats[symbol]["last_update"] = datetime.now().isoformat()
                self.update_stats[symbol]["last_status"] = "error"
                self.update_stats[symbol]["last_duration"] = duration
                self.update_stats[symbol]["max_duration"] = max(self.update_stats[symbol]["max_duration"], duration)
    
    def save_statistics(self) -> None:
        """Lưu thống kê cập nhật"""
        try:
            with open('market_update_stats.json', 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'stats': self.update_stats,
                    'summary': {
                        'total_updates': sum(s["total_updates"] for s in self.update_stats.values()),
                        'successful_updates': sum(s["successful_updates"] for s in self.update_stats.values()),
                        'failed_updates': sum(s["failed_updates"] for s in self.update_stats.values()),
                        'success_rate': sum(s["successful_updates"] for s in self.update_stats.values()) / 
                                      max(1, sum(s["total_updates"] for s in self.update_stats.values())) * 100,
                        'average_duration': sum(s["total_duration"] for s in self.update_stats.values()) / 
                                         max(1, sum(s["total_updates"] for s in self.update_stats.values())),
                        'today_updates': sum(s["today_updates"] for s in self.update_stats.values()),
                        'today_successful': sum(s["today_successful"] for s in self.update_stats.values())
                    }
                }, f, indent=2)
            logger.info("Đã lưu thống kê cập nhật vào market_update_stats.json")
        except IOError as e:
            logger.error(f"Lỗi khi lưu thống kê: {e}")
    
    def reset_daily_statistics(self) -> None:
        """Reset thống kê hàng ngày"""
        for symbol in self.update_stats:
            self.update_stats[symbol]["today_updates"] = 0
            self.update_stats[symbol]["today_successful"] = 0
        logger.info("Đã reset thống kê hàng ngày")
    
    def check_symbol_update(self, symbol: str) -> Dict:
        """
        Kiểm tra trạng thái cập nhật gần đây nhất của một cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền
        
        Returns:
            Dict: Thông tin trạng thái cập nhật
        """
        if symbol not in self.update_stats:
            return {"status": "unknown", "message": f"Chưa có cập nhật nào cho {symbol}"}
        
        last_update = self.update_stats[symbol]["last_update"]
        last_status = self.update_stats[symbol]["last_status"]
        last_duration = self.update_stats[symbol]["last_duration"]
        
        if last_update is None:
            return {"status": "unknown", "message": f"Chưa có cập nhật nào cho {symbol}"}
        
        time_since_update = datetime.now() - datetime.fromisoformat(last_update)
        
        if time_since_update.total_seconds() > self.get_update_interval(symbol) * 1.5:
            return {
                "status": "delayed",
                "message": f"Cập nhật {symbol} bị trễ ({time_since_update.total_seconds():.0f}s)",
                "last_update": last_update,
                "last_status": last_status,
                "last_duration": last_duration
            }
        
        return {
            "status": "ok",
            "message": f"Cập nhật {symbol} gần đây ({time_since_update.total_seconds():.0f}s trước)",
            "last_update": last_update,
            "last_status": last_status,
            "last_duration": last_duration
        }
    
    def get_all_status(self) -> Dict:
        """
        Lấy trạng thái cập nhật của tất cả các cặp tiền
        
        Returns:
            Dict: Trạng thái cập nhật của tất cả các cặp tiền
        """
        return {symbol: self.check_symbol_update(symbol) for symbol in self.pairs_priority}
    
    def run(self) -> None:
        """Chạy lập lịch cập nhật thị trường"""
        logger.info("Bắt đầu chạy lập lịch cập nhật thị trường")
        self.running = True
        self.setup_schedules()
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        except Exception as e:
            logger.error(f"Lỗi khi chạy lập lịch: {e}")
            self.running = False
        
        logger.info("Kết thúc lập lịch cập nhật thị trường")
    
    def handle_shutdown(self, signum, frame) -> None:
        """Xử lý khi nhận tín hiệu tắt từ hệ điều hành"""
        logger.info(f"Nhận tín hiệu {signum}, đang tắt lập lịch cập nhật...")
        self.running = False
        self.save_statistics()
        self.save_config()
        sys.exit(0)

def main():
    """Hàm chính"""
    scheduler = MarketUpdateScheduler()
    
    # Chạy cập nhật một lần cho tất cả các cặp tiền để khởi động
    logger.info("Chạy cập nhật ban đầu cho tất cả các cặp tiền")
    for symbol in scheduler.pairs_priority.keys():
        scheduler.update_market_data(symbol)
        time.sleep(2)  # Đợi 2 giây giữa các cập nhật ban đầu
    
    # Bắt đầu lập lịch
    scheduler.run()

if __name__ == "__main__":
    main()