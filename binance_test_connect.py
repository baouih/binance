#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import hmac
import hashlib
import requests
import logging
from urllib.parse import urlencode

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('binance_test')

# API keys từ biến môi trường
API_KEY = os.environ.get('BINANCE_TESTNET_API_KEY', '')
API_SECRET = os.environ.get('BINANCE_TESTNET_API_SECRET', '')

def test_futures_endpoints():
    """Kiểm tra các endpoint Binance Futures Testnet khác nhau để tìm ra cái hoạt động"""
    
    # Các URL cơ sở cần kiểm tra
    base_urls = [
        "https://testnet.binancefuture.com",
        "https://testnet.binancefutures.com", 
        "https://testnet.futures.binance.com",
        "https://testnet-fapi.binance.com"
    ]
    
    # Các endpoint cần kiểm tra
    endpoints = [
        "/fapi/v1/time",
        "/fapi/v1/exchangeInfo",
        "/fapi/v1/ticker/price?symbol=BTCUSDT"
    ]
    
    logger.info("Bắt đầu kiểm tra các endpoints không cần xác thực...")
    
    # Kiểm tra endpoints không cần xác thực
    for base_url in base_urls:
        for endpoint in endpoints:
            url = f"{base_url}{endpoint}"
            try:
                response = requests.get(url, timeout=5)
                status = response.status_code
                
                if status == 200:
                    logger.info(f"✅ {url} - Hoạt động! Status: {status}")
                    try:
                        # Hiển thị một phần response để kiểm tra
                        data = response.json()
                        sample = str(data)[:100] + "..." if len(str(data)) > 100 else str(data)
                        logger.info(f"   Sample response: {sample}")
                    except:
                        logger.info(f"   Không thể hiển thị response")
                else:
                    logger.warning(f"❌ {url} - Không hoạt động. Status: {status}")
                
            except Exception as e:
                logger.error(f"❌ {url} - Lỗi: {str(e)}")
    
    # Nếu không có API key, dừng lại
    if not API_KEY or not API_SECRET:
        logger.error("Không tìm thấy API_KEY hoặc API_SECRET. Bỏ qua kiểm tra các endpoint cần xác thực.")
        return

    logger.info("\nBắt đầu kiểm tra các endpoints cần xác thực...")
    
    # Các endpoints cần xác thực
    auth_endpoints = [
        "/fapi/v1/account",
        "/fapi/v2/account",
        "/fapi/v1/balance", 
        "/fapi/v2/balance"
    ]
    
    # Kiểm tra endpoints cần xác thực
    for base_url in base_urls:
        for endpoint in auth_endpoints:
            timestamp = int(time.time() * 1000)
            params = {'timestamp': timestamp}
            
            query_string = urlencode(params)
            signature = hmac.new(
                API_SECRET.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            url = f"{base_url}{endpoint}?{query_string}&signature={signature}"
            
            try:
                headers = {'X-MBX-APIKEY': API_KEY}
                response = requests.get(url, headers=headers, timeout=5)
                status = response.status_code
                
                if status == 200:
                    logger.info(f"✅ {base_url}{endpoint} - Hoạt động! Status: {status}")
                    try:
                        # Hiển thị một phần response để kiểm tra
                        data = response.json()
                        sample = str(data)[:100] + "..." if len(str(data)) > 100 else str(data)
                        logger.info(f"   Sample response: {sample}")
                    except:
                        logger.info(f"   Không thể hiển thị response")
                else:
                    logger.warning(f"❌ {base_url}{endpoint} - Không hoạt động. Status: {status}, Error: {response.text}")
                    
            except Exception as e:
                logger.error(f"❌ {base_url}{endpoint} - Lỗi: {str(e)}")

if __name__ == "__main__":
    logger.info("Bắt đầu kiểm tra kết nối Binance Futures Testnet")
    test_futures_endpoints()
    logger.info("Hoàn thành kiểm tra kết nối")