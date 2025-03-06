#!/usr/bin/env python
"""
Script khởi động lại hoàn toàn server, sử dụng ứng dụng đơn giản
"""
import os
import sys
import time
import logging
import signal
import subprocess

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('server_restarter')

def find_gunicorn_process():
    """Tìm PID của process gunicorn"""
    try:
        # Sử dụng ps để tìm PID của gunicorn
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        pids = []
        for line in lines:
            if 'gunicorn' in line and 'python' in line:
                parts = line.split()
                if len(parts) > 1:
                    pids.append(int(parts[1]))
        
        return pids
    except Exception as e:
        logger.error(f"Lỗi khi tìm process gunicorn: {str(e)}")
        return []

def stop_gunicorn_processes():
    """Dừng các process gunicorn đang chạy"""
    pids = find_gunicorn_process()
    
    if not pids:
        logger.info("Không tìm thấy process gunicorn nào đang chạy")
        return
    
    for pid in pids:
        try:
            logger.info(f"Tìm thấy tiến trình gunicorn với PID {pid}, đang kết thúc...")
            os.kill(pid, signal.SIGTERM)
            logger.info(f"Đã gửi tín hiệu SIGTERM tới PID {pid}")
        except Exception as e:
            logger.error(f"Lỗi khi kết thúc process {pid}: {str(e)}")
    
    # Đợi tất cả các process kết thúc
    time.sleep(2)

def start_simple_app():
    """Khởi động ứng dụng đơn giản"""
    try:
        logger.info("Khởi động server với ứng dụng đơn giản...")
        
        # Sử dụng gunicorn để khởi động ứng dụng đơn giản
        cmd = [
            'gunicorn',
            '--bind', '0.0.0.0:5000',
            '--workers', '1',
            '--timeout', '120',
            'simple_app:app'
        ]
        
        # Khởi động server trong background
        subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        logger.info("Server khởi động thành công!")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi khởi động server: {str(e)}")
        return False

if __name__ == "__main__":
    # Dừng tất cả các process gunicorn đang chạy
    stop_gunicorn_processes()
    
    # Khởi động ứng dụng đơn giản
    success = start_simple_app()
    
    if success:
        logger.info("Khởi động lại server thành công")
        sys.exit(0)
    else:
        logger.error("Không thể khởi động lại server")
        sys.exit(1)