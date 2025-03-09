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

logger = logging.getLogger('test_order_creator')

# API Testnet endpoints
BASE_TESTNET_URL = "https://testnet.binancefuture.com"

# Lấy API key và secret từ biến môi trường
API_KEY = os.environ.get('BINANCE_TESTNET_API_KEY', '')
API_SECRET = os.environ.get('BINANCE_TESTNET_API_SECRET', '')

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

def futures_ticker_price(symbol):
    """Lấy giá hiện tại của một symbol"""
    url = f"{BASE_TESTNET_URL}/fapi/v1/ticker/price"
    
    params = {
        'symbol': symbol
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return float(response.json()['price'])
    else:
        logger.error(f"Lỗi khi lấy giá ticker: {response.status_code} - {response.text}")
        return None

def futures_create_order(symbol, side, order_type, quantity=None, price=None, 
                      stop_price=None, close_position=None, reduce_only=None, 
                      time_in_force=None, activation_price=None, callback_rate=None,
                      test=False):
    """Tạo lệnh giao dịch futures với hỗ trợ trailing stop"""
    endpoint = "/fapi/v1/order/test" if test else "/fapi/v1/order"
    url = f"{BASE_TESTNET_URL}{endpoint}"
    
    timestamp = get_server_time()
    params = {
        'symbol': symbol,
        'side': side,
        'type': order_type,
        'timestamp': timestamp,
        'positionSide': 'LONG'  # Tài khoản đang sử dụng LONG positions
    }
    
    # Thêm các tham số tùy chọn
    if quantity is not None:
        params['quantity'] = quantity
    if price is not None:
        params['price'] = price
    if stop_price is not None:
        params['stopPrice'] = stop_price
    if close_position is not None:
        params['closePosition'] = close_position
    if reduce_only is not None and order_type != 'TRAILING_STOP_MARKET':
        params['reduceOnly'] = reduce_only
    if time_in_force is not None:
        params['timeInForce'] = time_in_force
    # Thêm tham số cho trailing stop
    if activation_price is not None:
        params['activationPrice'] = activation_price
    if callback_rate is not None:
        params['callbackRate'] = callback_rate
    
    # Tạo query string và signature
    query_string = '&'.join([f"{key}={params[key]}" for key in params])
    signature = generate_signature(query_string)
    
    headers = {'X-MBX-APIKEY': API_KEY}
    final_url = f"{url}?{query_string}&signature={signature}"
    
    # Log URL và tham số để debug
    logger.info(f"Gửi request đến: {url}")
    logger.info(f"Tham số: {params}")
    
    response = requests.post(final_url, headers=headers)
    if response.status_code == 200:
        logger.info(f"Đã đặt lệnh thành công")
        return response.json()
    else:
        logger.error(f"Lỗi khi đặt lệnh: {response.status_code} - {response.text}")
        return None

def create_test_order_with_trailing_stop(symbol='BTCUSDT', quantity='0.001'):
    """Tạo lệnh test với TP và Trailing Stop"""
    # 1. Lấy giá hiện tại
    current_price = futures_ticker_price(symbol)
    if not current_price:
        logger.error(f"Không thể lấy giá hiện tại cho {symbol}, không thể tạo lệnh")
        return False
    
    logger.info(f"Giá hiện tại của {symbol}: {current_price}")
    
    # 2. Đặt lệnh MARKET
    market_order = futures_create_order(
        symbol=symbol,
        side="BUY",
        order_type="MARKET",
        quantity=quantity
    )
    
    if not market_order:
        logger.error(f"Không thể tạo lệnh MARKET, dừng quá trình")
        return False
    
    logger.info(f"Đã tạo lệnh MARKET thành công: {market_order}")
    logger.info("Chờ 3 giây để lệnh được thực hiện...")
    time.sleep(3)
    
    # 3. Tính giá kích hoạt cho trailing stop (+2%)
    activation_price = round(current_price * 1.02, 2)
    logger.info(f"Giá kích hoạt cho Trailing Stop: {activation_price} (+2% từ giá hiện tại)")
    
    # 4. Đặt Trailing Stop với callback 1%
    trailing_stop = futures_create_order(
        symbol=symbol,
        side="SELL",
        order_type="TRAILING_STOP_MARKET",
        quantity=quantity,
        activation_price=str(activation_price),
        callback_rate="1.0"
    )
    
    if trailing_stop:
        logger.info(f"Đã đặt Trailing Stop thành công: {trailing_stop}")
    else:
        logger.error(f"Không thể đặt Trailing Stop")
    
    # 5. Tính giá TP 3%
    tp_price = round(current_price * 1.03, 2)
    logger.info(f"Giá Take Profit: {tp_price} (+3% từ giá hiện tại)")
    
    # 6. Đặt lệnh Take Profit
    take_profit = futures_create_order(
        symbol=symbol,
        side="SELL",
        order_type="TAKE_PROFIT_MARKET",
        quantity=quantity,
        stop_price=str(tp_price)
    )
    
    if take_profit:
        logger.info(f"Đã đặt Take Profit thành công: {take_profit}")
    else:
        logger.error(f"Không thể đặt Take Profit")
    
    logger.info("Quá trình tạo lệnh test đã hoàn tất")
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Tạo lệnh test với TP và Trailing Stop")
    parser.add_argument("--symbol", type=str, default="BTCUSDT", help="Symbol để tạo lệnh (mặc định: BTCUSDT)")
    parser.add_argument("--quantity", type=str, default="0.001", help="Số lượng BTC (mặc định: 0.001)")
    
    args = parser.parse_args()
    
    logger.info(f"=== Tạo lệnh test cho {args.symbol} với số lượng {args.quantity} ===")
    create_test_order_with_trailing_stop(args.symbol, args.quantity)