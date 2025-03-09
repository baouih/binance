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

logger = logging.getLogger('trailing_stop_adder')

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
        return response.json()
    else:
        logger.error(f"Lỗi khi lấy giá ticker: {response.status_code} - {response.text}")
        return None

def get_active_positions():
    """Lấy thông tin các vị thế đang hoạt động"""
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
        positions = [p for p in response.json() if float(p['positionAmt']) != 0]
        logger.info(f"Đã lấy {len(positions)} vị thế đang hoạt động")
        return positions
    else:
        logger.error(f"Lỗi khi lấy thông tin vị thế: {response.status_code} - {response.text}")
        return None

def get_open_orders():
    """Lấy danh sách các lệnh đang mở"""
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
        orders = response.json()
        logger.info(f"Đã lấy {len(orders)} lệnh đang mở")
        return orders
    else:
        logger.error(f"Lỗi khi lấy thông tin lệnh đang mở: {response.status_code} - {response.text}")
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

def add_trailing_stop_to_positions():
    """Thêm trailing stop cho các vị thế hiện có"""
    # Lấy danh sách vị thế đang hoạt động
    positions = get_active_positions()
    if not positions:
        logger.info("Không có vị thế nào đang hoạt động.")
        return
    
    # Lấy danh sách lệnh đang mở
    open_orders = get_open_orders()
    if open_orders is None:
        logger.error("Không thể lấy danh sách lệnh đang mở.")
        return
    
    # Tải các vị thế đã ghi nhận từ file
    try:
        with open('active_positions.json', 'r') as f:
            tracked_positions = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        tracked_positions = {}
    
    # Thiết lập tham số trailing stop
    activation_percent = 2.0  # Kích hoạt ở mức +2% từ giá vào
    callback_rate = 1.0  # Callback rate 1%
    
    # Xử lý từng vị thế đang mở
    for position in positions:
        symbol = position['symbol']
        position_amt = float(position['positionAmt'])
        entry_price = float(position['entryPrice'])
        leverage = float(position['leverage'])
        position_side = position['positionSide']
        
        # Bỏ qua vị thế rỗng hoặc SHORT
        if position_amt <= 0:
            continue
        
        logger.info(f"Xử lý vị thế {symbol}:")
        logger.info(f"  - Số lượng: {position_amt}")
        logger.info(f"  - Giá vào: {entry_price}")
        logger.info(f"  - Đòn bẩy: {leverage}x")
        logger.info(f"  - Position Side: {position_side}")
        
        # Tính giá kích hoạt trailing stop
        activation_price = round(entry_price * (1 + activation_percent / 100), 2)
        
        # Kiểm tra xem đã có trailing stop chưa
        has_trailing_stop = False
        for order in open_orders:
            if order['symbol'] == symbol and order['type'] == 'TRAILING_STOP_MARKET':
                has_trailing_stop = True
                logger.info(f"  - Đã có lệnh Trailing Stop cho {symbol}, không cần tạo thêm")
                break
        
        if not has_trailing_stop:
            logger.info(f"  - Chưa có Trailing Stop cho {symbol}, tạo mới")
            logger.info(f"  - Giá kích hoạt: {activation_price} (+{activation_percent}% từ giá vào)")
            logger.info(f"  - Callback Rate: {callback_rate}%")
            
            # Tạo trailing stop
            trailing_stop_order = futures_create_order(
                symbol=symbol,
                side="SELL",
                order_type="TRAILING_STOP_MARKET",
                quantity=str(position_amt),
                activation_price=str(activation_price),
                callback_rate=str(callback_rate)
            )
            
            if trailing_stop_order:
                logger.info(f"  - Đã tạo Trailing Stop thành công cho {symbol}")
                
                # Cập nhật thông tin vào file tracking
                if symbol in tracked_positions:
                    tracked_positions[symbol]['trailing_activation'] = activation_price
                    tracked_positions[symbol]['trailing_callback'] = callback_rate
                    tracked_positions[symbol]['trailing_order_id'] = trailing_stop_order.get('orderId', 'Unknown')
                else:
                    logger.warning(f"  - {symbol} không có trong file tracking, không thể cập nhật")
            else:
                logger.error(f"  - Không thể tạo Trailing Stop cho {symbol}")
    
    # Lưu lại thông tin vị thế đã cập nhật
    with open('active_positions.json', 'w') as f:
        json.dump(tracked_positions, f, indent=4)
    
    logger.info("Đã hoàn thành kiểm tra và thêm Trailing Stop cho các vị thế.")

def add_3pct_tp_for_positions():
    """Thêm lệnh TP +3% song song với TP hiện có"""
    # Lấy danh sách vị thế đang hoạt động
    positions = get_active_positions()
    if not positions:
        logger.info("Không có vị thế nào đang hoạt động.")
        return
    
    # Lấy danh sách lệnh đang mở
    open_orders = get_open_orders()
    if open_orders is None:
        logger.error("Không thể lấy danh sách lệnh đang mở.")
        return
    
    # Tải các vị thế đã ghi nhận từ file
    try:
        with open('active_positions.json', 'r') as f:
            tracked_positions = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        tracked_positions = {}
    
    # Thiết lập tham số take profit
    tp_percent = 3.0  # TP ở mức +3% từ giá vào
    
    # Xử lý từng vị thế đang mở
    for position in positions:
        symbol = position['symbol']
        position_amt = float(position['positionAmt'])
        entry_price = float(position['entryPrice'])
        leverage = float(position['leverage'])
        position_side = position['positionSide']
        
        # Bỏ qua vị thế rỗng hoặc SHORT
        if position_amt <= 0:
            continue
        
        logger.info(f"Xử lý vị thế {symbol}:")
        logger.info(f"  - Số lượng: {position_amt}")
        logger.info(f"  - Giá vào: {entry_price}")
        logger.info(f"  - Đòn bẩy: {leverage}x")
        logger.info(f"  - Position Side: {position_side}")
        
        # Tính giá take profit 3%
        tp_price = round(entry_price * (1 + tp_percent / 100), 2)
        
        # Kiểm tra xem đã có TP 3% chưa
        has_3pct_tp = False
        for order in open_orders:
            if (order['symbol'] == symbol and 
                order['type'] == 'TAKE_PROFIT_MARKET' and 
                abs(float(order['stopPrice']) - tp_price) < 0.1):
                has_3pct_tp = True
                logger.info(f"  - Đã có lệnh TP {tp_percent}% cho {symbol}, không cần tạo thêm")
                break
        
        if not has_3pct_tp:
            logger.info(f"  - Thêm TP {tp_percent}% cho {symbol} tại giá {tp_price}")
            
            # Tạo lệnh TP 3%
            tp_order = futures_create_order(
                symbol=symbol,
                side="SELL",
                order_type="TAKE_PROFIT_MARKET",
                quantity=str(position_amt/2),  # Chỉ đặt TP cho 50% vị thế
                stop_price=str(tp_price)
            )
            
            if tp_order:
                logger.info(f"  - Đã tạo TP {tp_percent}% thành công cho {symbol}")
                
                # Cập nhật thông tin vào file tracking
                if symbol in tracked_positions:
                    if not 'partial_tp' in tracked_positions[symbol]:
                        tracked_positions[symbol]['partial_tp'] = []
                    
                    tracked_positions[symbol]['partial_tp'].append({
                        'percent': tp_percent,
                        'price': tp_price,
                        'quantity': str(position_amt/2),
                        'order_id': tp_order.get('orderId', 'Unknown')
                    })
                else:
                    logger.warning(f"  - {symbol} không có trong file tracking, không thể cập nhật")
            else:
                logger.error(f"  - Không thể tạo TP {tp_percent}% cho {symbol}")
    
    # Lưu lại thông tin vị thế đã cập nhật
    with open('active_positions.json', 'w') as f:
        json.dump(tracked_positions, f, indent=4)
    
    logger.info(f"Đã hoàn thành kiểm tra và thêm TP {tp_percent}% cho các vị thế.")

if __name__ == "__main__":
    import argparse
    
    # Thiết lập command line arguments
    parser = argparse.ArgumentParser(description='Thêm Trailing Stop và Take Profit cho các vị thế hiện có')
    parser.add_argument('--force-update-all', action='store_true', help='Cập nhật cả những vị thế đã có Trailing Stop')
    args = parser.parse_args()
    
    if args.force_update_all:
        logger.info("=== Thêm/Cập nhật Trailing Stop cho TẤT CẢ vị thế hiện có (chế độ force) ===")
        # Buộc xóa file theo dõi vị thế để đảm bảo mọi vị thế đều được cập nhật
        if os.path.exists('active_positions.json'):
            os.remove('active_positions.json')
            logger.info("Đã xóa danh sách vị thế được theo dõi để buộc cập nhật lại toàn bộ")
    else:
        logger.info("=== Thêm Trailing Stop cho các vị thế hiện có ===")
    
    add_trailing_stop_to_positions()
    
    logger.info("\n=== Thêm TP 3% cho các vị thế hiện có ===")
    add_3pct_tp_for_positions()