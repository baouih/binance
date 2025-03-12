#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Khởi động tất cả các dịch vụ trong hệ thống trading
"""

import os
import sys
import time
import logging
import subprocess
from datetime import datetime

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("start_all_services.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("start_all_services")

# Danh sách các dịch vụ cần khởi động
SERVICES = [
    {
        "name": "Market Notifier",
        "script": "auto_market_notifier.py",
        "pid_file": "market_notifier.pid",
        "log_file": "market_notifier.log"
    },
    {
        "name": "Unified Trading Service",
        "script": "unified_trading_service.py",
        "pid_file": "unified_trading_service.pid",
        "log_file": "unified_trading_service.log"
    }
]

def start_service(service):
    """Khởi động một dịch vụ cụ thể"""
    logger.info(f"Đang khởi động {service['name']}...")
    
    script_path = service['script']
    pid_file = service['pid_file']
    log_file = service['log_file']
    
    # Kiểm tra xem script có tồn tại không
    if not os.path.exists(script_path):
        logger.error(f"Không tìm thấy script {script_path}")
        return False
    
    # Khởi động dịch vụ với nohup
    cmd = f"python {script_path} > {log_file} 2>&1 & echo $! > {pid_file}"
    
    try:
        subprocess.run(cmd, shell=True, check=True)
        logger.info(f"Đã khởi động {service['name']}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Lỗi khi khởi động {service['name']}: {e}")
        return False

def start_all_services():
    """Khởi động tất cả các dịch vụ"""
    logger.info("===== BẮT ĐẦU KHỞI ĐỘNG TẤT CẢ DỊCH VỤ =====")
    logger.info(f"Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")
    
    # Khởi động từng dịch vụ
    for service in SERVICES:
        success = start_service(service)
        if success:
            logger.info(f"✅ {service['name']} đã được khởi động thành công")
        else:
            logger.error(f"❌ Không thể khởi động {service['name']}")
        
        # Đợi một chút giữa các lần khởi động
        time.sleep(2)
    
    logger.info("===== KẾT THÚC KHỞI ĐỘNG DỊCH VỤ =====")

if __name__ == "__main__":
    start_all_services()