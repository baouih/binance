#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import hmac
import hashlib
import requests
from datetime import datetime
import logging

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('position_mode_checker')

# API Testnet endpoints
BASE_TESTNET_URL = "https://testnet.binancefuture.com"

# Lấy API key và secret từ biến môi trường
API_KEY = os.environ.get('BINANCE_TESTNET_API_KEY')
API_SECRET = os.environ.get('BINANCE_TESTNET_API_SECRET')

def get_server_time():
    """Lấy thời gian từ server Binance"""
    try:
        response = requests.get(f"{BASE_TESTNET_URL}/fapi/v1/time")
        if response.status_code == 200:
            return response.json()['serverTime']
        else:
            logger.error(f"Không thể lấy thời gian từ server: {response.status_code} - {response.text}")
            return int(time.time() * 1000)
    except Exception as e:
        logger.error(f"Lỗi khi lấy thời gian từ server: {str(e)}")
        return int(time.time() * 1000)

def generate_signature(query_string):
    """Tạo chữ ký cho API request"""
    return hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def get_position_mode():
    """Kiểm tra chế độ position (Hedge Mode hoặc One-way Mode)"""
    endpoint = "/fapi/v1/positionSide/dual"
    url = f"{BASE_TESTNET_URL}{endpoint}"
    
    timestamp = get_server_time()
    params = {
        'timestamp': timestamp
    }
    
    # Tạo query string và signature
    query_string = '&'.join([f"{key}={params[key]}" for key in params])
    signature = generate_signature(query_string)
    
    headers = {'X-MBX-APIKEY': API_KEY}
    final_url = f"{url}?{query_string}&signature={signature}"
    
    # Log URL để debug
    logger.info(f"Gửi request đến: {url}")
    logger.info(f"Tham số: {params}")
    
    response = requests.get(final_url, headers=headers)
    if response.status_code == 200:
        result = response.json()
        logger.info(f"Chế độ position hiện tại: {json.dumps(result, indent=2)}")
        dual_side_position = result.get('dualSidePosition', False)
        if dual_side_position:
            logger.info("Tài khoản đang sử dụng Hedge Mode (đồng thời Long và Short)")
        else:
            logger.info("Tài khoản đang sử dụng One-way Mode (chỉ Long hoặc Short)")
        return result
    else:
        logger.error(f"Lỗi khi kiểm tra chế độ position: {response.status_code} - {response.text}")
        return None

def change_position_mode(dual_side_position):
    """Thay đổi chế độ position (True = Hedge Mode, False = One-way Mode)"""
    endpoint = "/fapi/v1/positionSide/dual"
    url = f"{BASE_TESTNET_URL}{endpoint}"
    
    timestamp = get_server_time()
    params = {
        'dualSidePosition': str(dual_side_position).lower(),
        'timestamp': timestamp
    }
    
    # Tạo query string và signature
    query_string = '&'.join([f"{key}={params[key]}" for key in params])
    signature = generate_signature(query_string)
    
    headers = {'X-MBX-APIKEY': API_KEY}
    final_url = f"{url}?{query_string}&signature={signature}"
    
    # Log URL để debug
    logger.info(f"Gửi request đến: {url}")
    logger.info(f"Tham số: {params}")
    
    response = requests.post(final_url, headers=headers)
    if response.status_code == 200:
        result = response.json()
        logger.info(f"Đã thay đổi chế độ position: {json.dumps(result, indent=2)}")
        return result
    else:
        logger.error(f"Lỗi khi thay đổi chế độ position: {response.status_code} - {response.text}")
        return None

if __name__ == "__main__":
    # Kiểm tra chế độ position hiện tại
    current_mode = get_position_mode()
    
    # Nếu cần thay đổi, bạn có thể uncomment dòng dưới đây và chọn chế độ
    # Đặt 'False' cho One-way Mode (chỉ Long hoặc Short)
    # Đặt 'True' cho Hedge Mode (đồng thời Long và Short)
    # change_position_mode(False)