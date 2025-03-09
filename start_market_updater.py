#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script khởi động dịch vụ cập nhật dữ liệu thị trường theo lịch

Script này đảm bảo dịch vụ cập nhật dữ liệu thị trường được chạy như một tiến trình
background (daemon), theo dõi và tự động khởi động lại nếu cần thiết.
"""

import os
import sys
import time
import json
import signal
import logging
import subprocess
from datetime import datetime

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("market_updater_service.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("market_updater_service")

# Đường dẫn đến file PID
PID_FILE = 'market_updater.pid'

def is_process_running(pid_file: str) -> bool:
    """
    Kiểm tra xem tiến trình có đang chạy không
    
    Args:
        pid_file (str): Đường dẫn đến file PID
        
    Returns:
        bool: True nếu tiến trình đang chạy, False nếu không
    """
    if not os.path.exists(pid_file):
        return False
        
    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
            
        # Kiểm tra tiến trình trên Linux
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        # Tiến trình không tồn tại hoặc không thể đọc PID
        return False
        
def save_pid(pid_file: str, pid: int) -> None:
    """
    Lưu PID vào file
    
    Args:
        pid_file (str): Đường dẫn đến file PID
        pid (int): Process ID cần lưu
    """
    with open(pid_file, 'w') as f:
        f.write(str(pid))
    logger.info(f"Đã lưu PID {pid} vào {pid_file}")

def start_market_updater_service() -> subprocess.Popen:
    """
    Khởi động dịch vụ cập nhật dữ liệu thị trường
    
    Returns:
        subprocess.Popen: Đối tượng tiến trình
    """
    logger.info("Đang khởi động dịch vụ cập nhật dữ liệu thị trường...")
    
    # Chạy script trong nền
    process = subprocess.Popen(
        ['python', 'schedule_market_updates.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True  # Tạo session mới để tránh bị kill khi terminal đóng
    )
    
    # Lưu PID vào file
    save_pid(PID_FILE, process.pid)
    
    logger.info(f"Đã khởi động dịch vụ cập nhật dữ liệu thị trường với PID {process.pid}")
    return process

def run_single_update() -> bool:
    """
    Chạy một lần cập nhật dữ liệu thị trường
    
    Returns:
        bool: True nếu thành công, False nếu không
    """
    logger.info("Đang chạy cập nhật dữ liệu thị trường...")
    
    start_time = time.time()
    try:
        # Import và chạy updater
        from market_data_updater import MarketDataUpdater
        updater = MarketDataUpdater()
        results = updater.update_all_symbols()
        
        # Thống kê kết quả
        success_count = sum(1 for v in results.values() if v)
        duration = time.time() - start_time
        
        logger.info(f"Cập nhật thành công {success_count}/{len(results)} cặp giao dịch ({duration:.2f}s)")
        
        # Lưu kết quả
        with open('market_updater_last_run.json', 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
                "results": {k: "success" if v else "failed" for k, v in results.items()},
                "success_count": success_count,
                "total_count": len(results)
            }, f, indent=2)
        
        return success_count > 0
    
    except Exception as e:
        logger.error(f"Lỗi khi chạy cập nhật dữ liệu thị trường: {e}")
        return False

def main():
    """Hàm chính"""
    logger.info("Bắt đầu dịch vụ cập nhật dữ liệu thị trường")
    
    # Kiểm tra xem dịch vụ đã chạy chưa
    if is_process_running(PID_FILE):
        logger.info("Dịch vụ cập nhật dữ liệu thị trường đã đang chạy")
        return 0
    
    # Parse tham số
    if len(sys.argv) > 1 and sys.argv[1] == "--single":
        # Chạy một lần cập nhật
        success = run_single_update()
        return 0 if success else 1
    else:
        # Khởi động dịch vụ
        process = start_market_updater_service()
        
        # Kiểm tra xem tiến trình có khởi động thành công không
        time.sleep(2)
        if process.poll() is not None:
            # Tiến trình đã kết thúc
            stdout, stderr = process.communicate()
            logger.error(f"Dịch vụ cập nhật dữ liệu thị trường không thể khởi động")
            logger.error(f"STDOUT: {stdout.decode('utf-8')}")
            logger.error(f"STDERR: {stderr.decode('utf-8')}")
            return 1
        
        logger.info("Dịch vụ cập nhật dữ liệu thị trường đã khởi động thành công")
        
        # Chạy một lần cập nhật ngay
        run_single_update()
        
        return 0

if __name__ == "__main__":
    sys.exit(main())