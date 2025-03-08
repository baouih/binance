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

logger = logging.getLogger('position_checker')

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

def get_account_balance():
    """Lấy số dư tài khoản"""
    endpoint = "/fapi/v2/balance"
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
    
    logger.info(f"Gửi request đến: {url}")
    
    response = requests.get(final_url, headers=headers)
    if response.status_code == 200:
        result = response.json()
        # Lọc và hiển thị USDT balance
        usdt_balance = next((asset for asset in result if asset['asset'] == 'USDT'), None)
        if usdt_balance:
            logger.info(f"Số dư USDT: {usdt_balance['balance']} (Khả dụng: {usdt_balance['availableBalance']})")
        else:
            logger.info("Không tìm thấy USDT trong tài khoản")
        return result
    else:
        logger.error(f"Lỗi khi lấy số dư tài khoản: {response.status_code} - {response.text}")
        return None

def get_position_risk():
    """Lấy thông tin rủi ro vị thế hiện tại"""
    endpoint = "/fapi/v2/positionRisk"
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
    
    logger.info(f"Gửi request đến: {url}")
    
    response = requests.get(final_url, headers=headers)
    if response.status_code == 200:
        result = response.json()
        
        # Lọc vị thế có positionAmt != 0 (vị thế đang active)
        active_positions = [pos for pos in result if float(pos['positionAmt']) != 0]
        
        if active_positions:
            logger.info(f"Có {len(active_positions)} vị thế đang hoạt động:")
            for pos in active_positions:
                entry_price = float(pos['entryPrice'])
                mark_price = float(pos['markPrice'])
                position_amt = float(pos['positionAmt'])
                leverage = float(pos['leverage'])
                
                # Tính toán PnL
                pnl = position_amt * (mark_price - entry_price)
                pnl_percent = (mark_price - entry_price) / entry_price * 100 * leverage
                
                direction = "LONG" if position_amt > 0 else "SHORT"
                
                logger.info(f"Symbol: {pos['symbol']}")
                logger.info(f"Direction: {direction} (positionSide: {pos['positionSide']})")
                logger.info(f"Quantity: {abs(position_amt)}")
                logger.info(f"Entry Price: {entry_price}")
                logger.info(f"Current Price: {mark_price}")
                logger.info(f"Leverage: {leverage}x")
                logger.info(f"Unrealized PnL: {pnl:.4f} USD ({pnl_percent:.2f}%)")
                logger.info(f"Liquidation Price: {pos['liquidationPrice']}")
                logger.info("-------------------------")
        else:
            logger.info("Không có vị thế nào đang hoạt động")
            
        return result
    else:
        logger.error(f"Lỗi khi lấy thông tin vị thế: {response.status_code} - {response.text}")
        return None

def get_open_orders():
    """Lấy danh sách lệnh đang mở"""
    endpoint = "/fapi/v1/openOrders"
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
    
    logger.info(f"Gửi request đến: {url}")
    
    response = requests.get(final_url, headers=headers)
    if response.status_code == 200:
        result = response.json()
        
        if result:
            logger.info(f"Có {len(result)} lệnh đang mở:")
            for order in result:
                logger.info(f"Order ID: {order['orderId']}")
                logger.info(f"Symbol: {order['symbol']}")
                logger.info(f"Type: {order['type']}")
                logger.info(f"Side: {order['side']}")
                if 'stopPrice' in order and float(order['stopPrice']) > 0:
                    logger.info(f"Stop Price: {order['stopPrice']}")
                logger.info(f"Position Side: {order['positionSide']}")
                logger.info(f"Status: {order['status']}")
                logger.info("-------------------------")
        else:
            logger.info("Không có lệnh nào đang mở")
            
        return result
    else:
        logger.error(f"Lỗi khi lấy danh sách lệnh: {response.status_code} - {response.text}")
        return None

if __name__ == "__main__":
    logger.info("===== KIỂM TRA SỐ DƯ TÀI KHOẢN =====")
    get_account_balance()
    
    logger.info("\n===== KIỂM TRA VỊ THẾ ĐANG HOẠT ĐỘNG =====")
    get_position_risk()
    
    logger.info("\n===== KIỂM TRA LỆNH ĐANG MỞ =====")
    get_open_orders()