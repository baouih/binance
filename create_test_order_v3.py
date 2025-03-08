#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
import requests
import time
from datetime import datetime
from math import floor

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('testnet_order')

# URL gốc cho Testnet Binance Futures
BASE_TESTNET_URL = "https://testnet.binancefuture.com"
API_KEY = os.environ.get('BINANCE_TESTNET_API_KEY', '')
API_SECRET = os.environ.get('BINANCE_TESTNET_API_SECRET', '')

if not API_KEY or not API_SECRET:
    logger.error("Vui lòng cung cấp BINANCE_TESTNET_API_KEY và BINANCE_TESTNET_API_SECRET trong biến môi trường")
    sys.exit(1)

def get_server_time():
    """Lấy thời gian máy chủ từ Binance để đồng bộ timestamp"""
    url = f"{BASE_TESTNET_URL}/fapi/v1/time"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['serverTime']
    else:
        # Nếu không lấy được, sử dụng thời gian hiện tại
        return int(time.time() * 1000)

def generate_signature(query_string):
    """Tạo chữ ký HMAC-SHA256 cho API request"""
    import hmac
    import hashlib
    
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature

def futures_ticker_price(symbol):
    """Lấy giá hiện tại của một symbol"""
    url = f"{BASE_TESTNET_URL}/fapi/v1/ticker/price"
    params = {'symbol': symbol}
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Lỗi khi lấy giá: {response.status_code} - {response.text}")
        return None

def futures_account_balance():
    """Lấy số dư tài khoản futures"""
    url = f"{BASE_TESTNET_URL}/fapi/v2/balance"
    
    timestamp = get_server_time()
    params = {'timestamp': timestamp}
    query_string = '&'.join([f"{key}={params[key]}" for key in params])
    signature = generate_signature(query_string)
    
    headers = {'X-MBX-APIKEY': API_KEY}
    final_url = f"{url}?{query_string}&signature={signature}"
    
    response = requests.get(final_url, headers=headers)
    if response.status_code == 200:
        logger.info("Đã lấy số dư tài khoản thành công")
        return response.json()
    else:
        logger.error(f"Lỗi khi lấy số dư: {response.status_code} - {response.text}")
        return []

def futures_change_leverage(symbol, leverage):
    """Thay đổi đòn bẩy cho một symbol"""
    url = f"{BASE_TESTNET_URL}/fapi/v1/leverage"
    
    timestamp = get_server_time()
    params = {
        'symbol': symbol,
        'leverage': leverage,
        'timestamp': timestamp
    }
    
    query_string = '&'.join([f"{key}={params[key]}" for key in params])
    signature = generate_signature(query_string)
    
    headers = {'X-MBX-APIKEY': API_KEY}
    final_url = f"{url}?{query_string}&signature={signature}"
    
    response = requests.post(final_url, headers=headers)
    if response.status_code == 200:
        logger.info(f"Đã thay đổi đòn bẩy cho {symbol} thành {leverage}x")
        return response.json()
    else:
        logger.error(f"Lỗi khi thay đổi đòn bẩy: {response.status_code} - {response.text}")
        return None

def futures_exchange_info():
    """Lấy thông tin chi tiết về quy tắc giao dịch"""
    url = f"{BASE_TESTNET_URL}/fapi/v1/exchangeInfo"
    
    response = requests.get(url)
    if response.status_code == 200:
        logger.info("Đã lấy thông tin exchange thành công")
        return response.json()
    else:
        logger.error(f"Lỗi khi lấy thông tin exchange: {response.status_code} - {response.text}")
        return None

def futures_create_order(symbol, side, order_type, quantity=None, price=None, 
                       stop_price=None, close_position=None, reduce_only=None, 
                       time_in_force=None, test=False):
    """Tạo lệnh giao dịch futures"""
    endpoint = "/fapi/v1/order/test" if test else "/fapi/v1/order"
    url = f"{BASE_TESTNET_URL}{endpoint}"
    
    timestamp = get_server_time()
    params = {
        'symbol': symbol,
        'side': side,
        'type': order_type,
        'timestamp': timestamp,
        'positionSide': 'LONG'  # Tài khoản đang sử dụng Hedge Mode (cần chỉ rõ LONG hoặc SHORT)
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

def main():
    # Lấy balance tài khoản
    balances = futures_account_balance()
    usdt_balance = None
    
    # Tìm balance của USDT
    if balances:
        for asset in balances:
            if asset['asset'] == 'USDT':
                usdt_balance = float(asset['balance'])
                break
    
    if usdt_balance is None:
        logger.error("Không tìm thấy balance USDT trong tài khoản!")
        usdt_balance = 13000.0  # Giá trị mặc định từ log thực tế khi không lấy được balance
    
    logger.info(f"Số dư tài khoản hiện tại: {usdt_balance} USDT")
    
    # Cấu hình giao dịch
    symbol = "ETHUSDT"  # Thử với ETH
    leverage = 5  # 5x leverage
    risk_percent = 2.0  # % số dư để giao dịch - giảm xuống để an toàn hơn
    stop_loss_percent = 5.0  # % giảm giá để dừng lỗ 
    take_profit_percent = 7.5  # % tăng giá để chốt lời
    
    # Lấy giá hiện tại
    ticker = futures_ticker_price(symbol)
    if ticker:
        current_price = float(ticker['price'])
        logger.info(f"Giá hiện tại của {symbol}: {current_price} USDT")
    else:
        logger.error(f"Không thể lấy giá hiện tại cho {symbol}")
        current_price = 170.0  # Giả định giá mặc định khi không lấy được giá hiện tại
    
    # Thiết lập đòn bẩy
    try:
        leverage_response = futures_change_leverage(symbol, leverage)
        if leverage_response:
            logger.info(f"Đã thiết lập đòn bẩy {leverage}x cho {symbol}")
        else:
            logger.warning(f"Không thể thiết lập đòn bẩy, sử dụng giá trị mặc định")
    except Exception as e:
        logger.error(f"Lỗi khi thiết lập đòn bẩy: {str(e)}")
    
    # Tính toán kích thước vị thế dựa trên risk_percent
    position_value = usdt_balance * (risk_percent / 100)
    position_size = position_value / current_price
    
    # Tính toán stop loss và take profit
    stop_loss_price = round(current_price * (1 - stop_loss_percent / 100), 2)
    take_profit_price = round(current_price * (1 + take_profit_percent / 100), 2)
    
    # Làm tròn số lượng theo precision
    exchange_info = futures_exchange_info()
    if exchange_info:
        symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
        if symbol_info:
            qty_precision = int(symbol_info.get('quantityPrecision', 3))
            # Làm tròn chính xác theo precision
            position_size = floor(position_size * 10**qty_precision) / 10**qty_precision
    else:
        # Mặc định làm tròn xuống 3 chữ số thập phân
        position_size = floor(position_size * 1000) / 1000
    
    # Chuyển đổi sang chuỗi với định dạng chính xác
    position_size_str = f"{position_size}"
    
    # Hiển thị thông tin giao dịch
    logger.info("Thông số giao dịch:")
    logger.info(f"- Symbol: {symbol}")
    logger.info(f"- Đòn bẩy: {leverage}x")
    logger.info(f"- Kích thước vị thế: {position_size} {symbol.replace('USDT', '')} (≈ {position_value:.3f} USDT)")
    logger.info(f"- Giá hiện tại: {current_price} USDT")
    logger.info(f"- Stop Loss: {stop_loss_price} USDT ({stop_loss_percent}%)")
    logger.info(f"- Take Profit: {take_profit_price} USDT ({take_profit_percent}%)")
    
    # Trong môi trường thử nghiệm, tự động đặt lệnh không cần xác nhận thủ công
    # để dễ kiểm thử từ command line
    logger.info("Bot đang chạy ở chế độ tự động, tiến hành đặt lệnh...")
    
    # Đặt lệnh MARKET
    try:
        # Thử test order trước
        test_result = futures_create_order(
            symbol=symbol,
            side="BUY",
            order_type="MARKET",
            quantity=position_size_str,
            test=True
        )
        
        if test_result is not None:
            logger.info(f"Test order thành công: {test_result}")
            
            # Đặt lệnh thực tế
            order = futures_create_order(
                symbol=symbol,
                side="BUY",
                order_type="MARKET",
                quantity=position_size_str
            )
            
            if order:
                logger.info(f"Đã đặt lệnh MARKET BUY thành công: {json.dumps(order, indent=2)}")
                
                # Đặt Stop Loss
                stop_order = futures_create_order(
                    symbol=symbol,
                    side="SELL",
                    order_type="STOP_MARKET",
                    stop_price=str(stop_loss_price),
                    close_position="true"
                )
                
                if stop_order:
                    logger.info(f"Đã đặt lệnh Stop Loss thành công: {json.dumps(stop_order, indent=2)}")
                
                # Đặt Take Profit
                take_profit_order = futures_create_order(
                    symbol=symbol,
                    side="SELL",
                    order_type="TAKE_PROFIT_MARKET",
                    stop_price=str(take_profit_price),
                    close_position="true"
                )
                
                if take_profit_order:
                    logger.info(f"Đã đặt lệnh Take Profit thành công: {json.dumps(take_profit_order, indent=2)}")
                
                # Cập nhật file active_positions.json
                try:
                    with open('active_positions.json', 'r') as f:
                        active_positions = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    active_positions = {}
                
                # Thêm vị thế mới
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                active_positions[symbol] = {
                    "entry_price": current_price,
                    "position_size": position_size,
                    "stop_loss": stop_loss_price,
                    "take_profit": take_profit_price,
                    "entry_time": timestamp,
                    "order_id": order.get("orderId", "Unknown"),
                    "sl_order_id": stop_order.get("orderId", "Unknown") if stop_order else "Unknown",
                    "tp_order_id": take_profit_order.get("orderId", "Unknown") if take_profit_order else "Unknown",
                    "status": "ACTIVE"
                }
                
                # Lưu lại thông tin
                with open('active_positions.json', 'w') as f:
                    json.dump(active_positions, f, indent=4)
                
                logger.info(f"Đã cập nhật vị thế vào active_positions.json: {symbol}")
        else:
            logger.error("Test order không thành công, không đặt lệnh thực tế")
            
    except Exception as e:
        logger.error(f"Lỗi khi đặt lệnh: {str(e)}")
        # In ra traceback đầy đủ để debug
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()