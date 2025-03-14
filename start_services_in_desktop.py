#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script khởi động dịch vụ từ giao diện desktop
"""

import os
import sys
import time
import subprocess
import logging
import json
from datetime import datetime

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("desktop_services_start.log")
    ]
)

logger = logging.getLogger(__name__)

# Danh sách các dịch vụ cần khởi động
SERVICES = {
    "watchdog": {
        "script": "service_watchdog.py",
        "description": "Watchdog Service - Giám sát toàn hệ thống"
    },
    "service_manager": {
        "script": "enhanced_service_manager.py",
        "description": "Service Manager - Quản lý các dịch vụ khác"
    },
    "unified_trading_service": {
        "script": "unified_trading_service.py",
        "description": "Unified Trading Service - Dịch vụ giao dịch"
    },
    "market_notifier": {
        "script": "auto_market_notifier.py",
        "description": "Market Notifier - Phân tích thị trường"
    }
}

def start_service(service_name):
    """
    Khởi động một dịch vụ
    
    :param service_name: Tên dịch vụ cần khởi động
    :return: True nếu thành công, False nếu thất bại
    """
    try:
        service_info = SERVICES.get(service_name)
        if not service_info:
            logger.error(f"Không tìm thấy thông tin cho dịch vụ: {service_name}")
            return False
        
        script = service_info["script"]
        description = service_info["description"]
        
        # Kiểm tra script có tồn tại không
        if not os.path.exists(script):
            logger.error(f"Không tìm thấy file script: {script}")
            return False
        
        logger.info(f"Đang khởi động {description} ({script})...")
        
        # File để lưu PID
        pid_file = f"{service_name}.pid"
        # File nhật ký
        log_file = f"{service_name}.log"
        
        # Khởi động dịch vụ trong nền và lưu PID
        cmd = f"python {script} > {log_file} 2>&1 & echo $! > {pid_file}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Đã khởi động thành công {description}")
            time.sleep(1)  # Chờ một chút để dịch vụ khởi động
            return True
        else:
            logger.error(f"Lỗi khi khởi động {description}: {result.stderr}")
            return False
    
    except Exception as e:
        logger.exception(f"Lỗi không xác định khi khởi động {service_name}: {str(e)}")
        return False

def check_service_status(service_name):
    """
    Kiểm tra trạng thái dịch vụ
    
    :param service_name: Tên dịch vụ cần kiểm tra
    :return: True nếu đang chạy, False nếu không
    """
    try:
        pid_file = f"{service_name}.pid"
        
        # Kiểm tra file PID có tồn tại không
        if not os.path.exists(pid_file):
            return False
        
        # Đọc PID từ file
        with open(pid_file, "r") as f:
            pid = f.read().strip()
        
        if not pid:
            return False
        
        # Kiểm tra process có đang chạy không
        try:
            os.kill(int(pid), 0)
            return True
        except (OSError, ProcessLookupError):
            return False
    
    except Exception as e:
        logger.exception(f"Lỗi khi kiểm tra trạng thái {service_name}: {str(e)}")
        return False

def start_all_services():
    """
    Khởi động tất cả dịch vụ
    
    :return: Dictionary kết quả
    """
    results = {}
    services_started = []
    services_failed = []
    
    # Bắt đầu với Watchdog, sau đó Service Manager, cuối cùng là các dịch vụ khác
    priority_order = ["watchdog", "service_manager", "unified_trading_service", "market_notifier"]
    
    for service_name in priority_order:
        # Kiểm tra xem dịch vụ đã chạy chưa
        if check_service_status(service_name):
            logger.info(f"{service_name} đã đang chạy.")
            services_started.append(service_name)
            continue
        
        # Khởi động dịch vụ
        success = start_service(service_name)
        
        if success:
            services_started.append(service_name)
        else:
            services_failed.append(service_name)
    
    results["started"] = services_started
    results["failed"] = services_failed
    results["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Lưu kết quả vào file
    with open("services_start_results.json", "w") as f:
        json.dump(results, f, indent=4)
    
    return results

if __name__ == "__main__":
    print("Khởi động dịch vụ từ giao diện desktop...")
    results = start_all_services()
    
    if results["failed"]:
        print(f"❌ Các dịch vụ khởi động thất bại: {', '.join(results['failed'])}")
    
    if results["started"]:
        print(f"✅ Các dịch vụ đã khởi động: {', '.join(results['started'])}")
    
    print(f"Thời gian: {results['timestamp']}")
    print("Xem chi tiết trong file nhật ký desktop_services_start.log")