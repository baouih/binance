#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Service Guardian - Giám sát và khởi động lại dịch vụ
====================================================

Script này giám sát và tự động khởi động lại các dịch vụ nếu chúng bị dừng.
Được thiết kế để chạy liên tục như một dịch vụ hệ thống, đảm bảo các dịch vụ
quan trọng của hệ thống giao dịch luôn hoạt động.

Mode sử dụng:
1. Chạy như một dịch vụ độc lập: python service_guardian.py
2. Kiểm tra và khởi động một lần: python service_guardian.py --check-only

Tính năng:
- Giám sát trạng thái các dịch vụ thường xuyên
- Ghi nhật ký chi tiết về hoạt động giám sát
- Tự động khởi động lại dịch vụ nếu không còn hoạt động
- Gửi thông báo về trạng thái dịch vụ
"""

import os
import sys
import time
import signal
import logging
import argparse
import subprocess
import json
from datetime import datetime
import psutil

# Thiết lập logging
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('service_guardian')
logger.setLevel(logging.INFO)

# File handler
log_file = 'service_guardian.log'
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

# Danh sách dịch vụ cần giám sát và các thông tin cần thiết
# Format: name, check_command, start_script, pid_file
SERVICES = [
    {
        'name': 'Auto SLTP Manager',
        'check_command': 'pgrep -f "python auto_sltp_manager.py"',
        'start_script': './headless_start_sltp_manager.sh',
        'pid_file': 'auto_sltp_manager.pid',
        'direct_command': 'nohup python auto_sltp_manager.py > auto_sltp_manager.log 2>&1 &'
    },
    {
        'name': 'Trailing Stop Service',
        'check_command': 'pgrep -f "python position_trailing_stop.py"',
        'start_script': './headless_trailing_stop.sh',
        'pid_file': 'trailing_stop_service.pid',
        'direct_command': 'nohup python position_trailing_stop.py --mode service --interval 60 > trailing_stop_service.log 2>&1 &'
    },
    # Thêm các dịch vụ khác nếu cần
]

class ServiceGuardian:
    def __init__(self, check_only=False):
        """Khởi tạo Guardian Service."""
        self.check_only = check_only
        self.pid = os.getpid()
        self.write_pid_file()
        logger.info(f"Service Guardian khởi động với PID {self.pid}")
        
        # Xử lý tín hiệu để thoát sạch sẽ
        signal.signal(signal.SIGTERM, self.handle_sigterm)
        signal.signal(signal.SIGINT, self.handle_sigterm)
    
    def write_pid_file(self):
        """Ghi PID ra file để có thể kiểm tra sau này."""
        try:
            with open('service_guardian.pid', 'w') as f:
                f.write(str(self.pid))
        except Exception as e:
            logger.error(f"Không thể ghi file PID: {e}")
    
    def handle_sigterm(self, signum, frame):
        """Xử lý khi nhận tín hiệu thoát."""
        logger.info("Nhận được tín hiệu thoát, đang dừng dịch vụ...")
        try:
            os.remove('service_guardian.pid')
        except:
            pass
        sys.exit(0)
    
    def check_service(self, service):
        """Kiểm tra xem dịch vụ có đang chạy không."""
        try:
            # Sử dụng cả hai phương pháp để kiểm tra dịch vụ
            # 1. Kiểm tra thông qua lệnh check_command
            process = subprocess.run(service['check_command'], shell=True, stdout=subprocess.PIPE)
            running_by_command = process.returncode == 0
            
            # 2. Kiểm tra thông qua file PID
            running_by_pid = False
            if os.path.exists(service['pid_file']):
                with open(service['pid_file'], 'r') as f:
                    pid = f.read().strip()
                    running_by_pid = psutil.pid_exists(int(pid)) if pid.isdigit() else False
            
            # Dịch vụ được coi là đang chạy nếu một trong hai phương pháp xác nhận
            return running_by_command or running_by_pid
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra dịch vụ {service['name']}: {e}")
            return False
    
    def start_service(self, service):
        """Khởi động dịch vụ."""
        logger.info(f"Đang khởi động {service['name']}...")
        try:
            # Thử khởi động bằng script
            if os.path.exists(service['start_script']):
                subprocess.run(f"chmod +x {service['start_script']}", shell=True)
                result = subprocess.run(service['start_script'], shell=True)
                if result.returncode == 0:
                    logger.info(f"Đã khởi động {service['name']} thành công qua script")
                    return True
                else:
                    logger.warning(f"Khởi động {service['name']} qua script thất bại, thử lệnh trực tiếp")
            
            # Nếu script thất bại hoặc không tồn tại, thử lệnh trực tiếp
            subprocess.run(service['direct_command'], shell=True)
            
            # Chờ một chút để dịch vụ khởi động
            time.sleep(3)
            
            # Kiểm tra xem dịch vụ đã khởi động thành công chưa
            if self.check_service(service):
                logger.info(f"Đã khởi động {service['name']} thành công qua lệnh trực tiếp")
                return True
            else:
                logger.error(f"Không thể khởi động {service['name']}")
                return False
                
        except Exception as e:
            logger.error(f"Lỗi khi khởi động {service['name']}: {e}")
            return False
    
    def send_notification(self, message):
        """Gửi thông báo về trạng thái dịch vụ."""
        try:
            # Kiểm tra xem telegram_notifier có tồn tại không
            if os.path.exists('telegram_notifier.py'):
                cmd = f'python telegram_notifier.py "{message}" "system"'
                subprocess.run(cmd, shell=True)
                logger.info(f"Đã gửi thông báo: {message}")
            else:
                logger.warning("Không tìm thấy telegram_notifier.py. Bỏ qua thông báo.")
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo: {e}")
    
    def run(self):
        """Chạy vòng lặp chính của Guardian."""
        logger.info("Service Guardian bắt đầu giám sát các dịch vụ")
        
        # Gửi thông báo khởi động
        self.send_notification("🛡️ Service Guardian đã bắt đầu giám sát hệ thống")
        
        # Kiểm tra và khởi động các dịch vụ
        while True:
            service_status = []
            
            for service in SERVICES:
                is_running = self.check_service(service)
                status = "✅ Đang chạy" if is_running else "❌ Không chạy"
                logger.info(f"{service['name']}: {status}")
                service_status.append(f"{service['name']}: {status}")
                
                if not is_running:
                    if not self.check_only:
                        if self.start_service(service):
                            service_status[-1] = f"{service['name']}: ✅ Đã khởi động lại"
                            self.send_notification(f"🔄 Dịch vụ {service['name']} đã được khởi động lại tự động")
                        else:
                            self.send_notification(f"⚠️ Không thể khởi động lại dịch vụ {service['name']}")
            
            # Gửi báo cáo trạng thái các dịch vụ
            if not all("✅" in status for status in service_status):
                status_message = "📊 Trạng thái dịch vụ:\n" + "\n".join(service_status)
                self.send_notification(status_message)
            
            # Nếu chỉ kiểm tra một lần thì thoát
            if self.check_only:
                break
            
            # Chờ đến lần kiểm tra tiếp theo
            time.sleep(60)  # Kiểm tra mỗi 60 giây
        
        logger.info("Service Guardian kết thúc giám sát")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Service Guardian - Giám sát và khởi động lại dịch vụ")
    parser.add_argument("--check-only", action="store_true", 
                        help="Chỉ kiểm tra và khởi động các dịch vụ một lần")
    args = parser.parse_args()
    
    guardian = ServiceGuardian(check_only=args.check_only)
    guardian.run()