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

logger = logging.getLogger('fix_sl_tp')

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

def futures_account_balance():
    """Lấy số dư tài khoản futures"""
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
    
    response = requests.get(final_url, headers=headers)
    if response.status_code == 200:
        logger.info("Đã lấy số dư tài khoản thành công")
        return response.json()
    else:
        logger.error(f"Lỗi khi lấy số dư tài khoản: {response.status_code} - {response.text}")
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

def cancel_order(order_id, symbol):
    """Hủy một lệnh đang mở"""
    endpoint = "/fapi/v1/order"
    url = f"{BASE_TESTNET_URL}{endpoint}"
    
    timestamp = get_server_time()
    params = {
        'symbol': symbol,
        'orderId': order_id,
        'timestamp': timestamp
    }
    
    # Tạo query string và signature
    query_string = '&'.join([f"{key}={params[key]}" for key in params])
    signature = generate_signature(query_string)
    
    headers = {'X-MBX-APIKEY': API_KEY}
    final_url = f"{url}?{query_string}&signature={signature}"
    
    logger.info(f"Gửi request hủy lệnh đến: {url}")
    
    response = requests.delete(final_url, headers=headers)
    if response.status_code == 200:
        logger.info(f"Đã hủy lệnh {order_id} cho {symbol} thành công")
        return response.json()
    else:
        logger.error(f"Lỗi khi hủy lệnh: {response.status_code} - {response.text}")
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
        'positionSide': 'LONG'  # Sử dụng LONG mode
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
    if reduce_only is not None:
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

def calculate_adjusted_levels(current_price, leverage, risk_percent=5, reward_percent=7.5):
    """Tính toán các mức SL/TP đã điều chỉnh theo đòn bẩy
    
    Args:
        current_price: Giá hiện tại
        leverage: Đòn bẩy
        risk_percent: Phần trăm rủi ro mục tiêu (5% sau khi tính đòn bẩy)
        reward_percent: Phần trăm lợi nhuận mục tiêu (7.5% sau khi tính đòn bẩy)
        
    Returns:
        Dictionary chứa các mức SL/TP
    """
    # Điều chỉnh % để tính vào đòn bẩy
    adjusted_sl_percent = risk_percent / leverage
    adjusted_tp_percent = reward_percent / leverage
    
    # Tính giá SL/TP dựa trên % đã điều chỉnh
    sl_price = current_price * (1 - adjusted_sl_percent / 100)
    tp_price = current_price * (1 + adjusted_tp_percent / 100)
    
    # Làm tròn giá
    sl_price = round(sl_price, 2)
    tp_price = round(tp_price, 2)
    
    logger.info(f"Giá hiện tại: {current_price}")
    logger.info(f"Stop Loss: {sl_price} (-{adjusted_sl_percent:.2f}% từ giá hiện tại, tương đương -{risk_percent}% sau đòn bẩy)")
    logger.info(f"Take Profit: {tp_price} (+{adjusted_tp_percent:.2f}% từ giá hiện tại, tương đương +{reward_percent}% sau đòn bẩy)")
    
    return {
        'stop_loss': sl_price,
        'take_profit': tp_price,
        'sl_percent': adjusted_sl_percent,
        'tp_percent': adjusted_tp_percent
    }

def fix_positions_sltp():
    """Kiểm tra và sửa SL/TP cho các vị thế hiện tại"""
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
    
    leverage = 5  # Đòn bẩy mặc định
    
    # Xử lý từng vị thế đang mở
    for position in positions:
        symbol = position['symbol']
        position_amt = float(position['positionAmt'])
        entry_price = float(position['entryPrice'])
        mark_price = float(position['markPrice'])
        leverage = float(position['leverage'])
        
        # Bỏ qua vị thế rỗng
        if position_amt == 0:
            continue
        
        logger.info(f"Xử lý vị thế {symbol}:")
        logger.info(f"  - Số lượng: {position_amt}")
        logger.info(f"  - Giá vào: {entry_price}")
        logger.info(f"  - Giá hiện tại: {mark_price}")
        logger.info(f"  - Đòn bẩy: {leverage}x")
        
        # Tính toán SL/TP mới đã điều chỉnh theo đòn bẩy
        adjusted_levels = calculate_adjusted_levels(
            current_price=entry_price,
            leverage=leverage,
            risk_percent=5.0,   # Rủi ro 5% sau khi tính đòn bẩy
            reward_percent=7.5  # Lợi nhuận 7.5% sau khi tính đòn bẩy
        )
        
        # Lọc các lệnh SL/TP hiện tại của vị thế
        symbol_orders = [order for order in open_orders if order['symbol'] == symbol]
        sl_orders = [order for order in symbol_orders if order['type'] == 'STOP_MARKET']
        tp_orders = [order for order in symbol_orders if order['type'] == 'TAKE_PROFIT_MARKET']
        
        # Có cần sửa stop loss không?
        if sl_orders:
            for order in sl_orders:
                current_sl_price = float(order['stopPrice'])
                order_id = order['orderId']
                
                # Nếu SL hiện tại khác với SL mới đã điều chỉnh
                if abs(current_sl_price - adjusted_levels['stop_loss']) > 0.01:
                    logger.info(f"  - Stop Loss cũ: {current_sl_price}")
                    logger.info(f"  - Stop Loss mới (đã điều chỉnh theo đòn bẩy): {adjusted_levels['stop_loss']}")
                    
                    # Hỏi người dùng trước khi sửa
                    response = input(f"Bạn có muốn sửa Stop Loss từ {current_sl_price} thành {adjusted_levels['stop_loss']} cho {symbol}? (y/n): ")
                    
                    if response.lower() == 'y':
                        # Hủy lệnh SL cũ
                        cancel_result = cancel_order(order_id, symbol)
                        
                        if cancel_result:
                            # Đặt lệnh SL mới
                            new_sl_order = futures_create_order(
                                symbol=symbol,
                                side="SELL",
                                order_type="STOP_MARKET",
                                stop_price=str(adjusted_levels['stop_loss']),
                                close_position="true"
                            )
                            
                            if new_sl_order:
                                logger.info(f"  - Đã cập nhật Stop Loss thành công cho {symbol}")
                                
                                # Cập nhật file vị thế
                                if symbol in tracked_positions:
                                    tracked_positions[symbol]['stop_loss'] = adjusted_levels['stop_loss']
                                    tracked_positions[symbol]['sl_order_id'] = new_sl_order.get('orderId', 'Unknown')
                else:
                    logger.info(f"  - Stop Loss hiện tại ({current_sl_price}) đã đúng, không cần sửa.")
        else:
            logger.info(f"  - Không tìm thấy lệnh Stop Loss cho {symbol}, tạo mới...")
            response = input(f"Bạn có muốn tạo Stop Loss mới ở mức {adjusted_levels['stop_loss']} cho {symbol}? (y/n): ")
            
            if response.lower() == 'y':
                new_sl_order = futures_create_order(
                    symbol=symbol,
                    side="SELL",
                    order_type="STOP_MARKET",
                    stop_price=str(adjusted_levels['stop_loss']),
                    close_position="true"
                )
                
                if new_sl_order:
                    logger.info(f"  - Đã tạo Stop Loss mới thành công cho {symbol}")
                    
                    # Cập nhật file vị thế
                    if symbol in tracked_positions:
                        tracked_positions[symbol]['stop_loss'] = adjusted_levels['stop_loss']
                        tracked_positions[symbol]['sl_order_id'] = new_sl_order.get('orderId', 'Unknown')
        
        # Có cần sửa take profit không?
        if tp_orders:
            for order in tp_orders:
                current_tp_price = float(order['stopPrice'])
                order_id = order['orderId']
                
                # Nếu TP hiện tại khác với TP mới đã điều chỉnh
                if abs(current_tp_price - adjusted_levels['take_profit']) > 0.01:
                    logger.info(f"  - Take Profit cũ: {current_tp_price}")
                    logger.info(f"  - Take Profit mới (đã điều chỉnh theo đòn bẩy): {adjusted_levels['take_profit']}")
                    
                    # Hỏi người dùng trước khi sửa
                    response = input(f"Bạn có muốn sửa Take Profit từ {current_tp_price} thành {adjusted_levels['take_profit']} cho {symbol}? (y/n): ")
                    
                    if response.lower() == 'y':
                        # Hủy lệnh TP cũ
                        cancel_result = cancel_order(order_id, symbol)
                        
                        if cancel_result:
                            # Đặt lệnh TP mới
                            new_tp_order = futures_create_order(
                                symbol=symbol,
                                side="SELL",
                                order_type="TAKE_PROFIT_MARKET",
                                stop_price=str(adjusted_levels['take_profit']),
                                close_position="true"
                            )
                            
                            if new_tp_order:
                                logger.info(f"  - Đã cập nhật Take Profit thành công cho {symbol}")
                                
                                # Cập nhật file vị thế
                                if symbol in tracked_positions:
                                    tracked_positions[symbol]['take_profit'] = adjusted_levels['take_profit']
                                    tracked_positions[symbol]['tp_order_id'] = new_tp_order.get('orderId', 'Unknown')
                else:
                    logger.info(f"  - Take Profit hiện tại ({current_tp_price}) đã đúng, không cần sửa.")
        else:
            logger.info(f"  - Không tìm thấy lệnh Take Profit cho {symbol}, tạo mới...")
            response = input(f"Bạn có muốn tạo Take Profit mới ở mức {adjusted_levels['take_profit']} cho {symbol}? (y/n): ")
            
            if response.lower() == 'y':
                new_tp_order = futures_create_order(
                    symbol=symbol,
                    side="SELL",
                    order_type="TAKE_PROFIT_MARKET",
                    stop_price=str(adjusted_levels['take_profit']),
                    close_position="true"
                )
                
                if new_tp_order:
                    logger.info(f"  - Đã tạo Take Profit mới thành công cho {symbol}")
                    
                    # Cập nhật file vị thế
                    if symbol in tracked_positions:
                        tracked_positions[symbol]['take_profit'] = adjusted_levels['take_profit']
                        tracked_positions[symbol]['tp_order_id'] = new_tp_order.get('orderId', 'Unknown')
    
    # Lưu lại thông tin vị thế đã cập nhật
    with open('active_positions.json', 'w') as f:
        json.dump(tracked_positions, f, indent=4)
    
    logger.info("Đã hoàn thành kiểm tra và sửa SL/TP cho các vị thế.")

if __name__ == "__main__":
    fix_positions_sltp()