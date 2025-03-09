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
from math import floor
import logging

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('correct_order')

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

def futures_exchange_info():
    """Lấy thông tin exchange"""
    url = f"{BASE_TESTNET_URL}/fapi/v1/exchangeInfo"
    
    response = requests.get(url)
    if response.status_code == 200:
        logger.info("Đã lấy thông tin exchange thành công")
        return response.json()
    else:
        logger.error(f"Lỗi khi lấy thông tin exchange: {response.status_code} - {response.text}")
        return None

def futures_change_leverage(symbol, leverage):
    """Thay đổi đòn bẩy"""
    endpoint = "/fapi/v1/leverage"
    url = f"{BASE_TESTNET_URL}{endpoint}"
    
    timestamp = get_server_time()
    params = {
        'symbol': symbol,
        'leverage': leverage,
        'timestamp': timestamp
    }
    
    # Tạo query string và signature
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
        usdt_balance = 13000.0  # Giá trị mặc định từ log thực tế
    
    logger.info(f"Số dư tài khoản hiện tại: {usdt_balance} USDT")
    
    # Cấu hình giao dịch
    symbol = input("Nhập cặp tiền cần giao dịch (ví dụ: BTCUSDT): ").strip().upper()
    leverage = 5  # 5x leverage mặc định
    risk_percent = 2.0  # % số dư để giao dịch
    target_risk_percent = 5.0  # % rủi ro mục tiêu sau khi tính đòn bẩy
    target_reward_percent = 7.5  # % lợi nhuận mục tiêu sau khi tính đòn bẩy
    
    # Lấy giá hiện tại
    ticker = futures_ticker_price(symbol)
    if ticker:
        current_price = float(ticker['price'])
        logger.info(f"Giá hiện tại của {symbol}: {current_price} USDT")
    else:
        logger.error(f"Không thể lấy giá hiện tại cho {symbol}")
        return
    
    # Thiết lập đòn bẩy
    try:
        leverage_input = input(f"Nhập đòn bẩy (mặc định {leverage}x): ").strip()
        if leverage_input:
            leverage = int(leverage_input)
        
        leverage_response = futures_change_leverage(symbol, leverage)
        if leverage_response:
            logger.info(f"Đã thiết lập đòn bẩy {leverage}x cho {symbol}")
        else:
            logger.warning(f"Không thể thiết lập đòn bẩy, sử dụng giá trị mặc định")
    except Exception as e:
        logger.error(f"Lỗi khi thiết lập đòn bẩy: {str(e)}")
    
    # Điều chỉnh các mức SL/TP dựa trên đòn bẩy
    adjusted_levels = calculate_adjusted_levels(
        current_price=current_price,
        leverage=leverage,
        risk_percent=target_risk_percent,
        reward_percent=target_reward_percent
    )
    
    # Tính toán kích thước vị thế dựa trên risk_percent
    position_value = usdt_balance * (risk_percent / 100)
    position_size = position_value / current_price
    
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
    logger.info(f"- Stop Loss: {adjusted_levels['stop_loss']} USDT (-{adjusted_levels['sl_percent']:.2f}%, tương đương -{target_risk_percent}% sau đòn bẩy)")
    logger.info(f"- Take Profit: {adjusted_levels['take_profit']} USDT (+{adjusted_levels['tp_percent']:.2f}%, tương đương +{target_reward_percent}% sau đòn bẩy)")
    
    # Xác nhận giao dịch
    confirm = input("Xác nhận đặt lệnh? (y/n): ").strip().lower()
    if confirm != 'y':
        logger.info("Hủy đặt lệnh.")
        return
    
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
                    stop_price=str(adjusted_levels['stop_loss']),
                    close_position="true"
                )
                
                if stop_order:
                    logger.info(f"Đã đặt lệnh Stop Loss thành công: {json.dumps(stop_order, indent=2)}")
                
                # Đặt Take Profit
                take_profit_order = futures_create_order(
                    symbol=symbol,
                    side="SELL",
                    order_type="TAKE_PROFIT_MARKET",
                    stop_price=str(adjusted_levels['take_profit']),
                    close_position="true"
                )
                
                if take_profit_order:
                    logger.info(f"Đã đặt lệnh Take Profit thành công: {json.dumps(take_profit_order, indent=2)}")
                
                # Có muốn đặt thêm Trailing Stop không?
                trailing_stop = input("Bạn có muốn đặt thêm Trailing Stop không? (y/n): ").strip().lower()
                
                if trailing_stop == 'y':
                    # Tính toán mức kích hoạt trailing stop (mặc định kích hoạt ở 2% lợi nhuận)
                    activation_percent = 2.0  # % lợi nhuận để kích hoạt trailing stop
                    callback_rate = 1.0  # % callback rate cho trailing stop
                    
                    activation_price = round(current_price * (1 + activation_percent / 100), 2)
                    
                    # Đặt Trailing Stop
                    trailing_stop_order = futures_create_order(
                        symbol=symbol,
                        side="SELL",
                        order_type="TRAILING_STOP_MARKET",
                        quantity=position_size_str,
                        activation_price=str(activation_price),
                        callback_rate=str(callback_rate),
                        reduce_only="true"
                    )
                    
                    if trailing_stop_order:
                        logger.info(f"Đã đặt lệnh Trailing Stop thành công: {json.dumps(trailing_stop_order, indent=2)}")
                
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
                    "stop_loss": adjusted_levels['stop_loss'],
                    "take_profit": adjusted_levels['take_profit'],
                    "entry_time": timestamp,
                    "order_id": order.get("orderId", "Unknown"),
                    "sl_order_id": stop_order.get("orderId", "Unknown") if stop_order else "Unknown",
                    "tp_order_id": take_profit_order.get("orderId", "Unknown") if take_profit_order else "Unknown",
                    "status": "ACTIVE",
                    "leverage": leverage,
                    "adjusted_levels": {
                        "sl_percent": adjusted_levels['sl_percent'],
                        "tp_percent": adjusted_levels['tp_percent'],
                        "actual_risk_percent": target_risk_percent,
                        "actual_reward_percent": target_reward_percent
                    }
                }
                
                # Thêm thông tin trailing stop nếu có
                if trailing_stop == 'y' and trailing_stop_order:
                    active_positions[symbol]["trailing_activation"] = activation_price
                    active_positions[symbol]["trailing_callback"] = callback_rate
                    active_positions[symbol]["trailing_order_id"] = trailing_stop_order.get("orderId", "Unknown")
                
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