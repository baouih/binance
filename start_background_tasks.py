#!/usr/bin/env python
"""
Tiện ích khởi động tác vụ nền qua API.
Script này giúp khởi động các tác vụ nền thông qua API của hệ thống.
"""

import os
import sys
import json
import logging
import requests
import time
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('start_background_tasks.log')
    ]
)
logger = logging.getLogger('start_background_tasks')

# Cấu hình API
API_BASE_URL = "http://localhost:5000/api"
SERVICES = {
    "bot": "/bot/control/all",  # API điều khiển bot
    "unified": "/services/unified/start"  # API khởi động dịch vụ hợp nhất
}

def send_api_request(endpoint, action="start"):
    """
    Gửi yêu cầu API
    
    Args:
        endpoint (str): Endpoint API
        action (str): Hành động (mặc định: start)
    
    Returns:
        dict: Kết quả từ API
    """
    url = f"{API_BASE_URL}{endpoint}"
    logger.info(f"Gửi yêu cầu khởi động đến {url}")
    
    try:
        response = requests.post(
            url,
            json={"action": action},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Kết quả API: {result}")
            return result
        else:
            logger.error(f"Lỗi HTTP {response.status_code}: {response.text}")
            return {"success": False, "message": f"Lỗi HTTP {response.status_code}"}
            
    except requests.RequestException as e:
        logger.error(f"Lỗi kết nối API: {str(e)}")
        return {"success": False, "message": f"Lỗi kết nối: {str(e)}"}

def start_all_services():
    """
    Khởi động tất cả các dịch vụ
    """
    logger.info("=== BẮT ĐẦU KHỞI ĐỘNG CÁC DỊCH VỤ ===")
    
    # 1. Khởi động dịch vụ hợp nhất
    logger.info("1. Khởi động dịch vụ hợp nhất...")
    unified_result = send_api_request(SERVICES["unified"])
    
    if unified_result.get("success"):
        logger.info("✓ Dịch vụ hợp nhất đã được khởi động thành công")
    else:
        logger.warning(f"✗ Không thể khởi động dịch vụ hợp nhất: {unified_result.get('message')}")
    
    # Đợi dịch vụ hợp nhất khởi động
    time.sleep(2)
    
    # 2. Khởi động bot
    logger.info("2. Khởi động bot giao dịch...")
    bot_result = send_api_request(SERVICES["bot"], "start")
    
    if bot_result.get("success"):
        logger.info("✓ Bot giao dịch đã được khởi động thành công")
    else:
        logger.warning(f"✗ Không thể khởi động bot giao dịch: {bot_result.get('message')}")
    
    logger.info("=== HOÀN TẤT KHỞI ĐỘNG DỊCH VỤ ===")
    return {"unified": unified_result, "bot": bot_result}

if __name__ == "__main__":
    try:
        # Ghi timestamp bắt đầu
        start_time = datetime.now()
        logger.info(f"Bắt đầu khởi động dịch vụ lúc: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Khởi động các dịch vụ
        results = start_all_services()
        
        # Ghi kết quả vào file
        with open('startup_results.json', 'w') as f:
            json.dump({
                "timestamp": start_time.isoformat(),
                "results": results
            }, f, indent=2)
        
        # Kiểm tra kết quả tổng hợp
        if all(r.get("success", False) for r in results.values()):
            logger.info("Tất cả dịch vụ đã được khởi động thành công!")
            sys.exit(0)
        else:
            logger.warning("Một số dịch vụ không khởi động thành công, xem log để biết chi tiết.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Lỗi không mong đợi: {str(e)}")
        sys.exit(1)