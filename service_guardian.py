#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service Guardian - Giám sát và khởi động lại các dịch vụ khi cần thiết

Chức năng chính:
1. Giám sát các dịch vụ quan trọng
2. Khởi động lại các dịch vụ đã dừng
3. Gửi thông báo về trạng thái dịch vụ

Tác giả: BinanceTrader Bot
"""

import os
import sys
import time
import signal
import logging
import subprocess
import threading
from typing import Dict, List, Any
from datetime import datetime

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("service_guardian.log"),
        logging.StreamHandler()
    ]
)

# Tạo logger riêng cho dịch vụ guardian
logger = logging.getLogger("service_guardian")

# Danh sách các dịch vụ cần giám sát
SERVICES = [
    {
        "name": "Unified Trading Service",
        "process_name": "unified_trading_service.py",
        "start_command": "python3 unified_trading_service.py",
        "pid_file": "unified_trading_service.pid",
        "essential": True,
        "auto_restart": True
    }
]

# Biến toàn cục để theo dõi trạng thái dịch vụ
running = True


def check_process_running(service: Dict[str, Any]) -> bool:
    """
    Kiểm tra xem một tiến trình có đang chạy không
    
    :param service: Dict chứa thông tin dịch vụ
    :return: True nếu tiến trình đang chạy, False nếu không
    """
    # 1. Kiểm tra thông qua file PID (nếu có)
    if 'pid_file' in service and os.path.exists(service['pid_file']):
        try:
            with open(service['pid_file'], 'r') as f:
                pid = int(f.read().strip())
                
            # Kiểm tra xem PID có tồn tại không
            try:
                os.kill(pid, 0)  # Gửi signal 0 để kiểm tra tiến trình
                return True
            except OSError:
                # PID không tồn tại hoặc không có quyền truy cập
                logger.warning(f"Process với PID {pid} không tồn tại, mặc dù có file PID cho {service['name']}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi đọc file PID của {service['name']}: {e}")
    
    # 2. Kiểm tra thông qua tên tiến trình
    if 'process_name' in service:
        try:
            # Sử dụng ps để tìm các tiến trình có chứa tên tiến trình
            cmd = f"ps aux | grep '{service['process_name']}' | grep -v grep | awk '{{print $2}}'"
            result = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
            
            if result:
                # Tìm thấy ít nhất một tiến trình
                return True
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra tiến trình của {service['name']}: {e}")
    
    return False


def start_service(service: Dict[str, Any]) -> bool:
    """
    Khởi động một dịch vụ
    
    :param service: Dict chứa thông tin dịch vụ
    :return: True nếu khởi động thành công, False nếu không
    """
    if not service.get('start_command'):
        logger.error(f"Không thể khởi động {service['name']}: Thiếu lệnh khởi động")
        return False
    
    try:
        # Chạy dịch vụ trong nền
        cmd = f"{service['start_command']} &"
        subprocess.Popen(cmd, shell=True)
        
        logger.info(f"Đã khởi động {service['name']}")
        
        # Đợi một chút để dịch vụ có thể khởi động
        time.sleep(5)
        
        # Kiểm tra xem dịch vụ đã chạy chưa
        if check_process_running(service):
            logger.info(f"{service['name']} đã được khởi động thành công")
            return True
        else:
            logger.error(f"{service['name']} không khởi động được sau 5 giây")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi khởi động {service['name']}: {e}")
        return False


def check_and_restart_services() -> None:
    """
    Kiểm tra và khởi động lại các dịch vụ nếu cần
    """
    for service in SERVICES:
        try:
            if not check_process_running(service):
                logger.warning(f"{service['name']} không chạy")
                
                if service.get('auto_restart', False):
                    logger.info(f"Đang khởi động lại {service['name']}...")
                    start_service(service)
                    
                    # Gửi thông báo
                    try:
                        # Thử import telegram_notifier
                        from telegram_notifier import TelegramNotifier
                        notifier = TelegramNotifier()
                        
                        message = f"🛠️ *Thông báo từ Service Guardian*\n\n"
                        message += f"Dịch vụ *{service['name']}* đã được khởi động lại tự động."
                        
                        notifier.send_message(message)
                    except Exception as e:
                        logger.error(f"Lỗi khi gửi thông báo Telegram: {e}")
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra dịch vụ {service['name']}: {e}")


def monitor_services() -> None:
    """
    Chạy vòng lặp chính để giám sát các dịch vụ
    """
    global running
    
    logger.info("===== Bắt đầu giám sát dịch vụ =====")
    
    try:
        while running:
            # Kiểm tra và khởi động lại các dịch vụ
            check_and_restart_services()
            
            # Đợi 60 giây trước khi kiểm tra lại
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Nhận được tín hiệu thoát từ bàn phím")
        running = False
    finally:
        logger.info("===== Đã dừng giám sát dịch vụ =====")


def signal_handler(sig, frame) -> None:
    """
    Xử lý tín hiệu khi nhận SIGTERM hoặc SIGINT
    """
    global running
    logger.info(f"Đã nhận tín hiệu {sig}, dừng dịch vụ...")
    running = False


def main() -> None:
    """
    Hàm chính để chạy dịch vụ guardian
    """
    global running
    running = True
    
    # Đăng ký handler xử lý tín hiệu
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Bắt đầu giám sát các dịch vụ
    monitor_services()


if __name__ == "__main__":
    main()