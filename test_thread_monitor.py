#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Kiểm tra module theo dõi thread
"""

import time
import logging
import threading
from thread_monitor import register_thread, monitor_threads, get_thread_stats

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_thread_monitor")

def test_worker_normal(duration=5):
    """Thread làm việc bình thường"""
    logger.info(f"Thread bình thường bắt đầu, sẽ chạy trong {duration} giây")
    for i in range(duration):
        logger.info(f"Thread bình thường: Đang xử lý... {i+1}/{duration}")
        time.sleep(1)
    logger.info("Thread bình thường hoàn thành công việc")
    return True

def test_worker_error(duration=3):
    """Thread sẽ gặp lỗi sau một thời gian"""
    logger.info(f"Thread lỗi bắt đầu, sẽ gặp lỗi sau {duration} giây")
    for i in range(duration):
        logger.info(f"Thread lỗi: Đang xử lý... {i+1}/{duration}")
        time.sleep(1)
    logger.info("Thread lỗi chuẩn bị ném ngoại lệ")
    raise ValueError("Lỗi giả lập cho mục đích test!")

def test_worker_infinite():
    """Thread chạy vô hạn"""
    logger.info("Thread vô hạn bắt đầu")
    count = 0
    try:
        while True:
            count += 1
            logger.info(f"Thread vô hạn: nhịp thứ {count}")
            time.sleep(2)
    except KeyboardInterrupt:
        logger.info("Thread vô hạn bị dừng bởi người dùng")

def main():
    """Hàm chính để kiểm tra module thread_monitor"""
    logger.info("=== BẮT ĐẦU KIỂM TRA THREAD MONITOR ===")
    
    # Khởi động thread monitor
    monitor_threads()
    
    # Đăng ký và khởi động các threads test
    register_thread("thread_normal", test_worker_normal, (5,))
    
    # Chờ một chút
    time.sleep(1)
    
    # Đăng ký thread vô hạn
    infinite_thread = register_thread("thread_infinite", test_worker_infinite)
    
    # Chờ một chút
    time.sleep(1)
    
    # Đăng ký thread lỗi
    error_thread = register_thread("thread_error", test_worker_error, (3,))
    
    # Theo dõi trạng thái các thread trong 20 giây
    for i in range(20):
        # Hiển thị thống kê mỗi 2 giây
        time.sleep(2)
        stats = get_thread_stats()
        logger.info(f"--- THỐNG KÊ THREADS ({i+1}/10) ---")
        for stat in stats:
            name = stat['name']
            status = stat['status']
            is_alive = stat['is_alive']
            restarts = stat['restart_count']
            errors = stat['error_count']
            
            status_indicator = "✅" if is_alive else "❌"
            logger.info(f"{status_indicator} {name}: {status}, Restarts: {restarts}, Errors: {errors}")
    
    # Kết thúc thread vô hạn
    if infinite_thread and infinite_thread.is_alive():
        logger.info("Dừng thread vô hạn...")
        infinite_thread._stop()
    
    logger.info("=== HOÀN THÀNH KIỂM TRA THREAD MONITOR ===")

if __name__ == "__main__":
    main()