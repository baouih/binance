"""
File cấu hình để khởi động ứng dụng trong môi trường Replit
"""
import os
import sys
import subprocess
import time
import signal
import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('app_config')

def start_direct_app():
    """Khởi động ứng dụng direct_app.py"""
    logger.info("Đang khởi động ứng dụng direct_app.py")
    try:
        # Chạy ứng dụng
        process = subprocess.Popen([sys.executable, 'direct_app.py'])
        logger.info(f"Ứng dụng đã khởi động với PID {process.pid}")
        return process
    except Exception as e:
        logger.error(f"Lỗi khi khởi động ứng dụng: {str(e)}")
        return None

def stop_process(process):
    """Dừng tiến trình"""
    if process and process.poll() is None:
        logger.info(f"Đang dừng tiến trình PID {process.pid}")
        process.terminate()
        time.sleep(2)
        if process.poll() is None:
            process.kill()
        logger.info("Tiến trình đã dừng")

def handle_signal(signum, frame):
    """Xử lý tín hiệu"""
    logger.info(f"Nhận tín hiệu {signum}, đang thoát...")
    if 'app_process' in globals():
        stop_process(app_process)
    sys.exit(0)

if __name__ == "__main__":
    # Đăng ký xử lý tín hiệu
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    
    # Khởi động ứng dụng
    app_process = start_direct_app()
    
    try:
        # Giữ tiến trình cha chạy
        while app_process and app_process.poll() is None:
            time.sleep(1)
        
        # Nếu tiến trình con kết thúc
        exit_code = app_process.returncode if app_process else 1
        logger.info(f"Ứng dụng kết thúc với mã thoát {exit_code}")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Nhận lệnh ngắt từ bàn phím, đang thoát...")
        stop_process(app_process)