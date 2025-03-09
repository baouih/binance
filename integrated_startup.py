#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Integrated Startup Script - Khởi động tất cả các dịch vụ cần thiết trong một lần chạy duy nhất
"""

import os
import sys
import time
import json
import logging
import subprocess
import argparse
import signal
from datetime import datetime
import threading

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("integrated_system.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("integrated_system")

# Đường dẫn tới các script
SCRIPTS = {
    "main_trading_bot": "python main.py",
    "auto_sltp_manager": "python auto_sltp_manager.py",
    "trailing_stop": "bash start_trailing_stop.sh",
    "market_analyzer": "python market_analysis_service.py --mode service",
    "telegram_notifier": "python telegram_notification_service.py"
}

# Đường dẫn tới các file pid
PID_FILES = {
    "main_trading_bot": "main.pid",
    "auto_sltp_manager": "auto_sltp_manager.pid",
    "trailing_stop": "trailing_stop.pid",
    "market_analyzer": "market_analyzer.pid",
    "telegram_notifier": "telegram_notifier.pid"
}

# Class quản lý các tiến trình
class ServiceManager:
    def __init__(self):
        self.processes = {}
        self.statuses = {}
        self.lock = threading.Lock()
        self.load_status()
        
    def load_status(self):
        """Tải trạng thái từ file nếu có"""
        try:
            if os.path.exists('service_status.json'):
                with open('service_status.json', 'r') as f:
                    self.statuses = json.load(f)
            else:
                self.statuses = {name: "stopped" for name in SCRIPTS.keys()}
        except Exception as e:
            logger.error(f"Không thể tải trạng thái dịch vụ: {e}")
            self.statuses = {name: "stopped" for name in SCRIPTS.keys()}
    
    def save_status(self):
        """Lưu trạng thái ra file"""
        with self.lock:
            try:
                with open('service_status.json', 'w') as f:
                    json.dump(self.statuses, f, indent=4)
            except Exception as e:
                logger.error(f"Không thể lưu trạng thái dịch vụ: {e}")
    
    def start_service(self, name):
        """Khởi động một dịch vụ"""
        if name not in SCRIPTS:
            logger.error(f"Dịch vụ không tồn tại: {name}")
            return False
        
        if name in self.processes and self.processes[name].poll() is None:
            logger.info(f"Dịch vụ {name} đã đang chạy")
            return True
        
        cmd = SCRIPTS[name]
        try:
            logger.info(f"Đang khởi động dịch vụ {name} với lệnh: {cmd}")
            process = subprocess.Popen(
                cmd, 
                shell=True, 
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            self.processes[name] = process
            
            # Chờ một chút để kiểm tra xem tiến trình có khởi động thành công không
            time.sleep(2)
            if process.poll() is None:
                logger.info(f"Dịch vụ {name} đã được khởi động thành công với PID {process.pid}")
                with self.lock:
                    self.statuses[name] = "running"
                self.save_status()
                return True
            else:
                stdout, _ = process.communicate()
                logger.error(f"Không thể khởi động dịch vụ {name}. Lỗi: {stdout}")
                with self.lock:
                    self.statuses[name] = "failed"
                self.save_status()
                return False
        except Exception as e:
            logger.error(f"Lỗi khi khởi động dịch vụ {name}: {e}")
            with self.lock:
                self.statuses[name] = "failed"
            self.save_status()
            return False
    
    def stop_service(self, name):
        """Dừng một dịch vụ"""
        if name not in self.processes:
            logger.info(f"Dịch vụ {name} không đang chạy")
            return True
        
        process = self.processes[name]
        pid_file = PID_FILES.get(name)
        
        try:
            # Nếu có file PID, đọc PID từ file đó
            if pid_file and os.path.exists(pid_file):
                with open(pid_file, 'r') as f:
                    try:
                        pid = int(f.read().strip())
                        logger.info(f"Đang dừng dịch vụ {name} với PID {pid} từ file PID")
                        os.kill(pid, signal.SIGTERM)
                    except Exception as e:
                        logger.error(f"Không thể đọc hoặc sử dụng PID từ file {pid_file}: {e}")
            
            # Nếu process vẫn đang chạy, dừng nó
            if process.poll() is None:
                logger.info(f"Đang dừng dịch vụ {name} với PID {process.pid}")
                process.terminate()
                process.wait(timeout=5)
            
            # Kiểm tra xem đã dừng chưa, nếu chưa thì kill
            if process.poll() is None:
                logger.warning(f"Dịch vụ {name} chưa dừng, thực hiện kill")
                process.kill()
                process.wait(timeout=2)
            
            logger.info(f"Đã dừng dịch vụ {name}")
            with self.lock:
                self.statuses[name] = "stopped"
            self.save_status()
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi dừng dịch vụ {name}: {e}")
            with self.lock:
                self.statuses[name] = "unknown"
            self.save_status()
            return False
    
    def restart_service(self, name):
        """Khởi động lại một dịch vụ"""
        logger.info(f"Đang khởi động lại dịch vụ {name}")
        self.stop_service(name)
        time.sleep(2)  # Chờ một chút để đảm bảo dịch vụ đã dừng hoàn toàn
        return self.start_service(name)
    
    def start_all(self):
        """Khởi động tất cả các dịch vụ"""
        success = True
        for name in SCRIPTS.keys():
            if not self.start_service(name):
                success = False
        return success
    
    def stop_all(self):
        """Dừng tất cả các dịch vụ"""
        success = True
        for name in list(self.processes.keys()):
            if not self.stop_service(name):
                success = False
        return success
    
    def restart_all(self):
        """Khởi động lại tất cả các dịch vụ"""
        self.stop_all()
        time.sleep(3)  # Chờ một chút để đảm bảo tất cả dịch vụ đã dừng
        return self.start_all()
    
    def check_status(self, name=None):
        """Kiểm tra trạng thái của một dịch vụ hoặc tất cả dịch vụ"""
        if name:
            if name not in self.processes:
                status = "stopped"
            elif self.processes[name].poll() is None:
                status = "running"
            else:
                status = "stopped"
            
            with self.lock:
                self.statuses[name] = status
            
            return {name: status}
        else:
            statuses = {}
            for name in SCRIPTS.keys():
                if name not in self.processes:
                    status = "stopped"
                elif self.processes[name].poll() is None:
                    status = "running"
                else:
                    status = "stopped"
                
                statuses[name] = status
                
                with self.lock:
                    self.statuses[name] = status
            
            self.save_status()
            return statuses
    
    def get_status_report(self):
        """Tạo báo cáo trạng thái của tất cả dịch vụ"""
        self.check_status()
        
        report = "\n=== BÁO CÁO TRẠNG THÁI DỊCH VỤ ===\n"
        report += f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for name, status in self.statuses.items():
            status_str = {
                "running": "🟢 Đang chạy",
                "stopped": "🔴 Đã dừng",
                "failed": "🔴 Khởi động thất bại",
                "unknown": "🟠 Không xác định"
            }.get(status, f"⚪ {status}")
            
            report += f"{name}: {status_str}\n"
        
        return report

def main():
    parser = argparse.ArgumentParser(description="Quản lý tích hợp các dịch vụ trading")
    parser.add_argument("--action", choices=["start", "stop", "restart", "status"], default="start",
                        help="Hành động: start, stop, restart hoặc status")
    parser.add_argument("--service", help="Tên dịch vụ cụ thể, để trống để áp dụng cho tất cả")
    
    args = parser.parse_args()
    
    logger.info(f"=== KHỞI ĐỘNG HỆ THỐNG QUẢN LÝ DỊCH VỤ ===")
    service_manager = ServiceManager()
    
    try:
        if args.action == "start":
            if args.service:
                service_manager.start_service(args.service)
            else:
                service_manager.start_all()
                logger.info("Đã khởi động tất cả các dịch vụ")
        
        elif args.action == "stop":
            if args.service:
                service_manager.stop_service(args.service)
            else:
                service_manager.stop_all()
                logger.info("Đã dừng tất cả các dịch vụ")
        
        elif args.action == "restart":
            if args.service:
                service_manager.restart_service(args.service)
            else:
                service_manager.restart_all()
                logger.info("Đã khởi động lại tất cả các dịch vụ")
        
        elif args.action == "status":
            report = service_manager.get_status_report()
            print(report)
            logger.info(report)
        
        # Sau khi thực hiện các lệnh, luôn hiển thị trạng thái
        if args.action != "status":
            time.sleep(2)  # Chờ một chút để các dịch vụ có thời gian cập nhật trạng thái
            report = service_manager.get_status_report()
            print(report)
    
    except KeyboardInterrupt:
        logger.info("Nhận được tín hiệu ngắt (Ctrl+C)")
        service_manager.stop_all()
        logger.info("Đã dừng tất cả các dịch vụ")
    
    except Exception as e:
        logger.error(f"Lỗi không xác định: {e}")
        service_manager.stop_all()
        logger.info("Đã dừng tất cả các dịch vụ do lỗi")

if __name__ == "__main__":
    main()