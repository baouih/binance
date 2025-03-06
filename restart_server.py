"""
Script hỗ trợ khởi động lại server với cấu hình eventlet
"""
import os
import logging
import subprocess
import signal
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('server_restarter')

def kill_existing_gunicorn():
    """Tìm và kết thúc tiến trình gunicorn hiện tại"""
    try:
        # Tìm PID của các tiến trình gunicorn
        result = subprocess.run(['pgrep', '-f', 'gunicorn'], capture_output=True, text=True)
        pids = result.stdout.strip().split('\n')
        
        for pid in pids:
            if pid:
                logger.info(f"Tìm thấy tiến trình gunicorn với PID {pid}, đang kết thúc...")
                try:
                    os.kill(int(pid), signal.SIGTERM)
                    logger.info(f"Đã gửi tín hiệu SIGTERM tới PID {pid}")
                except ProcessLookupError:
                    logger.info(f"Tiến trình {pid} không tồn tại")
        
        # Chờ một chút để đảm bảo các tiến trình đã dừng
        time.sleep(2)
    except Exception as e:
        logger.error(f"Lỗi khi kết thúc gunicorn: {str(e)}")

def start_server():
    """Khởi động server với cấu hình mới"""
    try:
        logger.info("Khởi động server với cấu hình eventlet...")
        subprocess.Popen(['./start_server.sh'], shell=True)
        logger.info("Server khởi động thành công với cấu hình eventlet!")
    except Exception as e:
        logger.error(f"Lỗi khi khởi động server: {str(e)}")

if __name__ == "__main__":
    kill_existing_gunicorn()
    start_server()