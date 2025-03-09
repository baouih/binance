#!/usr/bin/env python3
"""
Script khởi động lại dịch vụ trailing stop
"""

import os
import sys
import time
import signal
import logging
import subprocess
from pathlib import Path

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("restart_trailing_stop")

# File PID
TRAILING_STOP_PID_FILE = "trailing_stop.pid"

def is_process_running(pid):
    """
    Kiểm tra xem một tiến trình có đang chạy không
    
    Args:
        pid (int): Process ID cần kiểm tra
        
    Returns:
        bool: True nếu tiến trình đang chạy, False nếu không
    """
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def stop_trailing_stop():
    """
    Dừng dịch vụ trailing stop nếu đang chạy
    
    Returns:
        bool: True nếu dừng thành công hoặc không có dịch vụ đang chạy, False nếu thất bại
    """
    try:
        if os.path.exists(TRAILING_STOP_PID_FILE):
            with open(TRAILING_STOP_PID_FILE, 'r') as f:
                pid = int(f.read().strip())
                
            if is_process_running(pid):
                logger.info(f"Đang dừng dịch vụ trailing stop với PID {pid}...")
                try:
                    os.kill(pid, signal.SIGTERM)
                    
                    # Đợi tối đa 5 giây để tiến trình dừng
                    for _ in range(10):
                        if not is_process_running(pid):
                            break
                        time.sleep(0.5)
                    
                    if is_process_running(pid):
                        logger.warning(f"Tiến trình {pid} không dừng sau 5 giây, đang buộc dừng...")
                        os.kill(pid, signal.SIGKILL)
                    
                    logger.info(f"Đã dừng dịch vụ trailing stop với PID {pid}")
                except OSError as e:
                    logger.error(f"Lỗi khi dừng tiến trình {pid}: {str(e)}")
                    return False
            else:
                logger.info(f"Không tìm thấy tiến trình với PID {pid}")
                
            # Xóa file PID
            os.remove(TRAILING_STOP_PID_FILE)
                
        return True
    except Exception as e:
        logger.error(f"Lỗi khi dừng dịch vụ trailing stop: {str(e)}")
        return False

def start_trailing_stop():
    """
    Khởi động dịch vụ trailing stop
    
    Returns:
        bool: True nếu khởi động thành công, False nếu thất bại
    """
    try:
        # Tạo lệnh chạy dịch vụ
        command = [sys.executable, "position_trailing_stop.py", "--interval", "30"]
        
        # Chạy dịch vụ trong nền
        with open("trailing_stop.log", "a") as log_file:
            process = subprocess.Popen(
                command,
                stdout=log_file,
                stderr=log_file,
                start_new_session=True
            )
        
        # Lưu PID vào file
        with open(TRAILING_STOP_PID_FILE, "w") as f:
            f.write(str(process.pid))
            
        logger.info(f"Đã khởi động dịch vụ trailing stop với PID {process.pid}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi khởi động dịch vụ trailing stop: {str(e)}")
        return False

def restart_trailing_stop():
    """
    Khởi động lại dịch vụ trailing stop
    
    Returns:
        bool: True nếu khởi động lại thành công, False nếu thất bại
    """
    # Dừng dịch vụ nếu đang chạy
    if not stop_trailing_stop():
        logger.warning("Có lỗi khi dừng dịch vụ trailing stop, tiếp tục khởi động lại...")
    
    # Xóa file active_positions.json nếu có (để đảm bảo đồng bộ với dữ liệu từ API)
    if os.path.exists("active_positions.json"):
        try:
            os.rename("active_positions.json", f"active_positions_backup_{int(time.time())}.json")
            logger.info("Đã tạo bản sao lưu của file active_positions.json và xóa file gốc")
        except Exception as e:
            logger.error(f"Lỗi khi tạo bản sao lưu active_positions.json: {str(e)}")
    
    # Tạo file active_positions.json trống
    with open("active_positions.json", "w") as f:
        f.write("{}")
    
    # Khởi động lại dịch vụ
    success = start_trailing_stop()
    if success:
        logger.info("Đã khởi động lại dịch vụ trailing stop thành công")
    else:
        logger.error("Không thể khởi động lại dịch vụ trailing stop")
        
    return success

if __name__ == "__main__":
    print("Đang khởi động lại dịch vụ trailing stop...")
    restart_trailing_stop()