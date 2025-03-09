#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module theo dõi và quản lý threads cho ứng dụng giao dịch crypto

Module này cung cấp các chức năng để:
1. Theo dõi trạng thái của tất cả các threads
2. Tự động khởi động lại threads khi chúng dừng bất ngờ
3. Hiển thị thống kê về thời gian hoạt động và hiệu suất
4. Gửi thông báo về trạng thái threads qua Telegram
"""

import os
import sys
import time
import threading
import logging
import traceback
import json
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Any, Optional, Tuple, Union
import inspect
import gc

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("thread_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("thread_monitor")

class ThreadStats:
    """Lưu trữ thống kê về một thread"""
    
    def __init__(self, name: str, thread: threading.Thread = None):
        self.name = name
        self.thread = thread
        self.start_time = datetime.now()
        self.last_alive_check = self.start_time
        self.restart_count = 0
        self.error_count = 0
        self.last_error = None
        self.status = "initialized"  # initialized, running, stopped, error, completed
        self.runtime = timedelta(seconds=0)
        self.load_average = 0.0
        
    def update(self, thread: threading.Thread = None):
        """Cập nhật thông tin thread"""
        now = datetime.now()
        
        if thread:
            self.thread = thread
            
        if self.thread:
            was_alive = self.status == "running"
            is_alive = self.thread.is_alive()
            
            if is_alive:
                self.status = "running"
                self.runtime = now - self.start_time
            elif was_alive and not is_alive:
                self.status = "stopped"
                
        self.last_alive_check = now
        return self
        
    def mark_error(self, error: Exception):
        """Đánh dấu lỗi xảy ra trong thread"""
        self.error_count += 1
        self.last_error = str(error)
        self.status = "error"
        return self
        
    def mark_restarted(self, thread: threading.Thread):
        """Đánh dấu thread đã được khởi động lại"""
        self.thread = thread
        self.restart_count += 1
        self.start_time = datetime.now()
        self.status = "running"
        return self
        
    def to_dict(self) -> Dict:
        """Chuyển đổi thành dictionary để lưu trữ hoặc hiển thị"""
        return {
            "name": self.name,
            "status": self.status,
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "runtime": str(self.runtime),
            "restart_count": self.restart_count,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "thread_id": self.thread.ident if self.thread else None,
            "is_alive": self.thread.is_alive() if self.thread else False
        }
        
    def __str__(self) -> str:
        """Hiển thị thông tin thread dưới dạng chuỗi"""
        return (f"Thread '{self.name}': {self.status}, "
                f"Runtime: {self.runtime}, "
                f"Restarts: {self.restart_count}, "
                f"Errors: {self.error_count}")

class ThreadMonitor:
    """Quản lý và theo dõi các threads trong ứng dụng"""
    
    def __init__(self, check_interval: int = 60):
        """
        Khởi tạo Thread Monitor
        
        Args:
            check_interval (int): Khoảng thời gian kiểm tra threads (giây)
        """
        self.threads: Dict[str, ThreadStats] = {}
        self.check_interval = check_interval
        self.monitor_thread = None
        self.running = False
        self.telegram_notify = None  # Sẽ được gán nếu cần gửi thông báo qua Telegram
        self._lock = threading.Lock()
        
    def register_thread(self, name: str, thread_func: Callable, args: Tuple = (), daemon: bool = True) -> threading.Thread:
        """
        Đăng ký và khởi động một thread mới
        
        Args:
            name (str): Tên định danh của thread
            thread_func (Callable): Hàm sẽ chạy trong thread
            args (Tuple): Các tham số cho thread_func
            daemon (bool): Có đặt thread là daemon không
            
        Returns:
            threading.Thread: Thread đã tạo
        """
        with self._lock:
            # Tạo thread mới
            thread = threading.Thread(target=self._wrapped_thread_func, 
                                     args=(name, thread_func, args),
                                     daemon=daemon)
            thread.name = name
            
            # Lưu thông tin
            self.threads[name] = ThreadStats(name, thread)
            
            # Khởi động thread
            thread.start()
            logger.info(f"Đã đăng ký và khởi động thread '{name}'")
            
            return thread
            
    def _wrapped_thread_func(self, name: str, thread_func: Callable, args: Tuple):
        """
        Bọc hàm thread gốc để theo dõi lỗi và cập nhật trạng thái
        
        Args:
            name (str): Tên thread
            thread_func (Callable): Hàm gốc của thread
            args (Tuple): Tham số cho hàm gốc
        """
        try:
            logger.info(f"Thread '{name}' bắt đầu chạy")
            
            with self._lock:
                if name in self.threads:
                    self.threads[name].status = "running"
            
            # Gọi hàm gốc với các tham số
            result = thread_func(*args)
            
            with self._lock:
                if name in self.threads:
                    self.threads[name].status = "completed"
                    
            logger.info(f"Thread '{name}' đã hoàn thành với kết quả: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Lỗi trong thread '{name}': {str(e)}")
            logger.error(traceback.format_exc())
            
            with self._lock:
                if name in self.threads:
                    self.threads[name].mark_error(e)
                    
            # Gửi thông báo về lỗi nếu cần
            if self.telegram_notify:
                try:
                    self.telegram_notify(f"🔴 Lỗi thread '{name}': {str(e)}")
                except:
                    pass
                    
            raise e
            
    def restart_thread(self, name: str, thread_func: Callable, args: Tuple = (), daemon: bool = True) -> threading.Thread:
        """
        Khởi động lại một thread đã dừng hoặc gặp lỗi
        
        Args:
            name (str): Tên thread cần khởi động lại
            thread_func (Callable): Hàm sẽ chạy trong thread mới
            args (Tuple): Các tham số cho thread_func
            daemon (bool): Có đặt thread là daemon không
            
        Returns:
            threading.Thread: Thread mới đã tạo
        """
        with self._lock:
            # Khởi tạo thread mới
            thread = threading.Thread(target=self._wrapped_thread_func, 
                                     args=(name, thread_func, args),
                                     daemon=daemon)
            thread.name = name
            
            # Cập nhật thông tin
            if name in self.threads:
                self.threads[name].mark_restarted(thread)
            else:
                self.threads[name] = ThreadStats(name, thread)
                self.threads[name].restart_count = 1
            
            # Khởi động thread
            thread.start()
            logger.info(f"Đã khởi động lại thread '{name}'")
            
            # Gửi thông báo về việc khởi động lại
            if self.telegram_notify:
                try:
                    self.telegram_notify(f"🟠 Đã khởi động lại thread '{name}'")
                except:
                    pass
            
            return thread
            
    def update_all_threads(self):
        """Cập nhật thông tin tất cả các threads đã đăng ký"""
        with self._lock:
            for name, stats in list(self.threads.items()):
                stats.update()
                
                # Xóa các threads đã hoàn thành quá lâu
                if stats.status == "completed" and (datetime.now() - stats.last_alive_check) > timedelta(hours=1):
                    logger.info(f"Xóa thread '{name}' khỏi danh sách theo dõi (đã hoàn thành)")
                    del self.threads[name]
                    
    def get_thread_stats(self, name: str = None) -> Union[Dict, List[Dict]]:
        """
        Lấy thông tin thống kê về các threads
        
        Args:
            name (str, optional): Tên thread cụ thể, hoặc None để lấy tất cả
            
        Returns:
            Union[Dict, List[Dict]]: Thông tin thống kê dưới dạng dict hoặc list of dict
        """
        with self._lock:
            if name:
                if name in self.threads:
                    return self.threads[name].to_dict()
                return None
            
            # Trả về thông tin tất cả các threads
            return [stats.to_dict() for stats in self.threads.values()]
            
    def get_dead_threads(self) -> List[str]:
        """
        Lấy danh sách các threads đã dừng hoặc gặp lỗi
        
        Returns:
            List[str]: Danh sách tên các threads đã dừng/lỗi
        """
        dead_threads = []
        
        with self._lock:
            for name, stats in self.threads.items():
                if stats.thread and not stats.thread.is_alive() and stats.status not in ["completed", "initialized"]:
                    dead_threads.append(name)
                    
        return dead_threads
        
    def _monitoring_thread(self):
        """Thread giám sát chính"""
        logger.info("Thread monitor bắt đầu chạy")
        
        last_full_log_time = datetime.now()
        
        while self.running:
            try:
                # Cập nhật thông tin tất cả các threads
                self.update_all_threads()
                
                # Tìm các threads đã chết
                dead_threads = self.get_dead_threads()
                if dead_threads:
                    logger.warning(f"Phát hiện {len(dead_threads)} threads đã dừng: {', '.join(dead_threads)}")
                    
                    # Có thể triển khai chức năng tự khởi động lại các threads
                    # (yêu cầu lưu trữ các hàm và tham số ban đầu)
                
                # Ghi log chi tiết theo định kỳ
                now = datetime.now()
                if now - last_full_log_time > timedelta(minutes=15):
                    self._log_all_thread_stats()
                    last_full_log_time = now
                    
                    # Dọn dẹp bộ nhớ
                    gc.collect()
                
                # Chờ đến lần kiểm tra tiếp theo
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Lỗi trong thread monitor: {str(e)}")
                logger.error(traceback.format_exc())
                time.sleep(10)  # Chờ một chút trước khi thử lại
                
        logger.info("Thread monitor đã dừng")
                
    def _log_all_thread_stats(self):
        """Ghi log thông tin tất cả các threads"""
        with self._lock:
            thread_count = len(self.threads)
            running_count = sum(1 for stats in self.threads.values() 
                              if stats.thread and stats.thread.is_alive())
            
            logger.info(f"=== THỐNG KÊ THREADS ({running_count}/{thread_count} đang chạy) ===")
            
            for name, stats in sorted(self.threads.items()):
                status_indicator = "✅" if stats.thread and stats.thread.is_alive() else "❌"
                logger.info(f"{status_indicator} {stats}")
                
            logger.info("=== KẾT THÚC THỐNG KÊ ===")
            
    def start_monitoring(self):
        """Bắt đầu thread giám sát"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            logger.warning("Thread monitor đã đang chạy")
            return
            
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_thread,
            daemon=True,
            name="thread_monitor"
        )
        self.monitor_thread.start()
        logger.info("Đã bắt đầu thread giám sát")
        
    def stop_monitoring(self):
        """Dừng thread giám sát"""
        self.running = False
        logger.info("Đã gửi tín hiệu dừng cho thread giám sát")
        
    def set_telegram_notifier(self, notify_func: Callable[[str], None]):
        """
        Đặt hàm gửi thông báo qua Telegram
        
        Args:
            notify_func (Callable): Hàm có một tham số là chuỗi tin nhắn
        """
        self.telegram_notify = notify_func
        logger.info("Đã cài đặt chức năng thông báo qua Telegram")

# Tạo instance toàn cục để sử dụng trong toàn bộ ứng dụng
thread_monitor = ThreadMonitor()

def register_thread(name: str, thread_func: Callable, args: Tuple = (), daemon: bool = True) -> threading.Thread:
    """
    Hàm tiện ích để đăng ký thread với monitor
    
    Args:
        name (str): Tên định danh của thread
        thread_func (Callable): Hàm sẽ chạy trong thread
        args (Tuple): Các tham số cho thread_func
        daemon (bool): Có đặt thread là daemon không
        
    Returns:
        threading.Thread: Thread đã tạo
    """
    return thread_monitor.register_thread(name, thread_func, args, daemon)

def restart_thread(name: str, thread_func: Callable, args: Tuple = (), daemon: bool = True) -> threading.Thread:
    """
    Hàm tiện ích để khởi động lại thread
    
    Args:
        name (str): Tên thread cần khởi động lại
        thread_func (Callable): Hàm sẽ chạy trong thread mới
        args (Tuple): Các tham số cho thread_func
        daemon (bool): Có đặt thread là daemon không
        
    Returns:
        threading.Thread: Thread mới đã tạo
    """
    return thread_monitor.restart_thread(name, thread_func, args, daemon)

def monitor_threads():
    """Bắt đầu theo dõi các threads"""
    thread_monitor.start_monitoring()

def get_thread_stats(name: str = None) -> Union[Dict, List[Dict]]:
    """
    Lấy thông tin thống kê về các threads
    
    Args:
        name (str, optional): Tên thread cụ thể, hoặc None để lấy tất cả
        
    Returns:
        Union[Dict, List[Dict]]: Thông tin thống kê dưới dạng dict hoặc list of dict
    """
    return thread_monitor.get_thread_stats(name)

# Các hàm test để demo chức năng
def test_normal_thread(sleep_time=20):
    """Thread chạy bình thường và kết thúc"""
    logger.info(f"Thread bình thường bắt đầu, sẽ chạy trong {sleep_time}s")
    for i in range(sleep_time):
        logger.info(f"Thread bình thường: đang xử lý {i+1}/{sleep_time}")
        time.sleep(1)
    logger.info("Thread bình thường kết thúc")
    return "Thành công"

def test_error_thread(sleep_time=5):
    """Thread sẽ gặp lỗi sau một thời gian"""
    logger.info(f"Thread lỗi bắt đầu, sẽ gặp lỗi sau {sleep_time}s")
    for i in range(sleep_time):
        logger.info(f"Thread lỗi: đang xử lý {i+1}/{sleep_time}")
        time.sleep(1)
    logger.info("Thread lỗi chuẩn bị ném ngoại lệ")
    raise ValueError("Lỗi giả lập cho mục đích test!")

def test_infinite_thread():
    """Thread chạy vô hạn"""
    logger.info("Thread vô hạn bắt đầu")
    count = 0
    while True:
        count += 1
        logger.info(f"Thread vô hạn: nhịp thứ {count}")
        time.sleep(2)

# Phần thực thi khi chạy trực tiếp module này
if __name__ == "__main__":
    # Khởi động thread monitor
    monitor_threads()
    
    # Đăng ký các threads test
    register_thread("normal_thread", test_normal_thread, (10,))
    register_thread("infinite_thread", test_infinite_thread)
    
    # Chờ một chút
    time.sleep(3)
    
    # Đăng ký thread lỗi
    error_thread = register_thread("error_thread", test_error_thread, (5,))
    
    # Cho chương trình chạy một thời gian
    try:
        while True:
            # Hiển thị thống kê mỗi 5 giây
            time.sleep(5)
            stats = get_thread_stats()
            print(f"Số threads được theo dõi: {len(stats)}")
            for stat in stats:
                print(f"- {stat['name']}: {stat['status']}, Alive: {stat['is_alive']}")
    except KeyboardInterrupt:
        print("Đã nhấn Ctrl+C, thoát chương trình...")
        thread_monitor.stop_monitoring()