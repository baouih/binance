#!/usr/bin/env python3
"""
Module quản lý Trailing Stop và khởi chạy dịch vụ tự động khi Replit khởi động

Module này đảm bảo dịch vụ trailing stop được chạy liên tục và tự khởi động lại
khi Replit khởi động lại, bảo vệ vị thế và lợi nhuận.
"""

import os
import sys
import time
import signal
import logging
import datetime
import subprocess
import threading
from threading import Thread
from flask import Flask, jsonify

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("auto_trade_scheduler")

# Đường dẫn đến file pid để theo dõi tiến trình
KEEP_ALIVE_PID_FILE = "keep_alive.pid"
TRAILING_STOP_PID_FILE = "trailing_stop.pid"

# Flask app cho keep-alive
app = Flask(__name__)

@app.route('/')
def home():
    return "Binance Trader Bot Service đang hoạt động!"

@app.route('/status')
def status():
    return jsonify({
        "status": "running",
        "version": "1.0.0",
        "services": {
            "keep_alive": is_process_running(KEEP_ALIVE_PID_FILE),
            "trailing_stop": is_process_running(TRAILING_STOP_PID_FILE)
        },
        "uptime": "active",
        "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

def is_process_running(pid_file: str) -> bool:
    """
    Kiểm tra xem tiến trình có đang chạy không
    
    Args:
        pid_file (str): Đường dẫn đến file PID
        
    Returns:
        bool: True nếu tiến trình đang chạy, False nếu không
    """
    try:
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Kiểm tra tiến trình có tồn tại không
            os.kill(pid, 0)
            return True
        return False
    except (ProcessLookupError, FileNotFoundError, ValueError, PermissionError):
        return False

def save_pid(pid_file: str, pid: int) -> None:
    """
    Lưu PID vào file
    
    Args:
        pid_file (str): Đường dẫn đến file PID
        pid (int): Process ID cần lưu
    """
    try:
        with open(pid_file, 'w') as f:
            f.write(str(pid))
        logger.info(f"Đã lưu PID {pid} vào file {pid_file}")
    except Exception as e:
        logger.error(f"Lỗi khi lưu PID vào file: {str(e)}")

def run_keep_alive_server():
    """Chạy máy chủ keep-alive"""
    try:
        port = int(os.environ.get('PORT', 8080))
        logger.info(f"Khởi động dịch vụ keep-alive trên cổng {port}")
        
        # Lưu PID của tiến trình hiện tại
        save_pid(KEEP_ALIVE_PID_FILE, os.getpid())
        
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"Lỗi khi khởi động dịch vụ keep-alive: {str(e)}")

def start_trailing_stop_service(interval: int = 60) -> subprocess.Popen:
    """
    Khởi động dịch vụ trailing stop
    
    Args:
        interval (int): Khoảng thời gian giữa các lần cập nhật (giây)
        
    Returns:
        subprocess.Popen: Đối tượng tiến trình
    """
    try:
        logger.info(f"Khởi động dịch vụ trailing stop với chu kỳ {interval} giây")
        
        # Khởi động tiến trình con cho dịch vụ trailing stop
        process = subprocess.Popen(
            [sys.executable, "position_trailing_stop.py", "--mode", "service", "--interval", str(interval)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Lưu PID của tiến trình
        save_pid(TRAILING_STOP_PID_FILE, process.pid)
        
        logger.info(f"Dịch vụ trailing stop đã khởi động với PID {process.pid}")
        return process
    except Exception as e:
        logger.error(f"Lỗi khi khởi động dịch vụ trailing stop: {str(e)}")
        return None

def monitor_trailing_stop_service(interval: int = 60):
    """
    Giám sát và đảm bảo dịch vụ trailing stop luôn chạy
    
    Args:
        interval (int): Khoảng thời gian giữa các lần kiểm tra (giây)
    """
    process = None
    
    try:
        while True:
            # Kiểm tra xem dịch vụ trailing stop có đang chạy không
            if not is_process_running(TRAILING_STOP_PID_FILE):
                logger.warning("Dịch vụ trailing stop không hoạt động, khởi động lại...")
                process = start_trailing_stop_service(interval)
            else:
                logger.info("Dịch vụ trailing stop đang hoạt động bình thường")
            
            # Đợi một khoảng thời gian trước khi kiểm tra lại
            time.sleep(300)  # Kiểm tra mỗi 5 phút
    except KeyboardInterrupt:
        logger.info("Dịch vụ giám sát đã dừng theo yêu cầu người dùng")
        if process and process.poll() is None:
            process.terminate()
    except Exception as e:
        logger.error(f"Lỗi trong dịch vụ giám sát: {str(e)}")
        if process and process.poll() is None:
            process.terminate()

def cleanup_handler(signum, frame):
    """
    Xử lý sự kiện khi tiến trình bị kết thúc
    
    Args:
        signum: Số hiệu tín hiệu
        frame: Stack frame
    """
    logger.info(f"Nhận tín hiệu {signum}, dọn dẹp trước khi thoát...")
    
    # Xóa các file PID
    for pid_file in [KEEP_ALIVE_PID_FILE, TRAILING_STOP_PID_FILE]:
        if os.path.exists(pid_file):
            try:
                os.remove(pid_file)
                logger.info(f"Đã xóa file {pid_file}")
            except Exception as e:
                logger.error(f"Lỗi khi xóa file {pid_file}: {str(e)}")
    
    sys.exit(0)

def main():
    """Hàm chính"""
    
    # Đăng ký handler cho các tín hiệu
    signal.signal(signal.SIGTERM, cleanup_handler)
    signal.signal(signal.SIGINT, cleanup_handler)
    
    try:
        logger.info("Khởi động Auto Trade Scheduler")
        
        # Khởi động dịch vụ trailing stop trong một thread riêng
        trailing_stop_service = start_trailing_stop_service()
        
        # Khởi động thread giám sát dịch vụ trailing stop
        monitor_thread = Thread(target=monitor_trailing_stop_service)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Khởi động dịch vụ keep-alive trong thread chính
        run_keep_alive_server()
    except Exception as e:
        logger.error(f"Lỗi trong Auto Trade Scheduler: {str(e)}")

if __name__ == "__main__":
    main()