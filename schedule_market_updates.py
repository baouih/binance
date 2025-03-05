#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Lên lịch cập nhật dữ liệu thị trường tự động

Script này lên lịch cập nhật dữ liệu thị trường định kỳ sử dụng thư viện schedule.
Thiết kế để chạy như một daemon trong nền.
"""

import os
import sys
import time
import logging
import signal
import schedule
from datetime import datetime

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("market_scheduler.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("market_scheduler")

# Biến trạng thái
running = True

def run_market_updater():
    """Chạy script cập nhật dữ liệu thị trường"""
    try:
        logger.info("Đang chạy cập nhật dữ liệu thị trường...")
        start_time = time.time()
        
        # Chạy script cập nhật
        exit_code = os.system('python market_data_updater.py')
        
        duration = time.time() - start_time
        if exit_code == 0:
            logger.info(f"Cập nhật dữ liệu thị trường thành công ({duration:.2f}s)")
        else:
            logger.error(f"Cập nhật dữ liệu thị trường thất bại với mã lỗi {exit_code} ({duration:.2f}s)")
        
        return exit_code == 0
    except Exception as e:
        logger.error(f"Lỗi khi chạy cập nhật dữ liệu thị trường: {e}")
        return False

def schedule_updates():
    """Lên lịch các cập nhật định kỳ"""
    # Cập nhật mỗi 15 phút
    schedule.every(15).minutes.do(run_market_updater)
    
    # Cập nhật vào các thời điểm quan trọng (cố định)
    schedule.every().day.at("00:05").do(run_market_updater)  # Đầu ngày
    schedule.every().day.at("08:05").do(run_market_updater)  # Thị trường châu Á
    schedule.every().day.at("14:05").do(run_market_updater)  # Thị trường châu Âu
    schedule.every().day.at("20:05").do(run_market_updater)  # Thị trường Mỹ
    
    logger.info("Đã lên lịch cập nhật dữ liệu thị trường")

def signal_handler(sig, frame):
    """Xử lý tín hiệu để thoát một cách an toàn"""
    global running
    logger.info("Đã nhận tín hiệu thoát, đang dừng...")
    running = False

def main():
    """Hàm chính"""
    try:
        # Đặt signal handler
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("Bắt đầu lịch cập nhật dữ liệu thị trường")
        
        # Chạy cập nhật ngay khi khởi động
        run_market_updater()
        
        # Lên lịch các cập nhật tiếp theo
        schedule_updates()
        
        # Vòng lặp chính
        while running:
            schedule.run_pending()
            time.sleep(1)
        
        logger.info("Dừng lịch cập nhật dữ liệu thị trường")
        return 0
    
    except Exception as e:
        logger.error(f"Lỗi khi chạy lịch cập nhật: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())