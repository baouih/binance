#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import logging
import json
import requests
import hmac
import hashlib
import time
import urllib.parse

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('binance_api_test')

class BinanceTestClient:
    """Client đơn giản để thử nghiệm yêu cầu trực tiếp đến Binance API"""
    
    def __init__(self):
        # Đọc thông tin từ môi trường
        import os
        self.api_key = os.environ.get('BINANCE_TESTNET_API_KEY')
        self.api_secret = os.environ.get('BINANCE_TESTNET_API_SECRET')
        self.base_url = 'https://testnet.binancefuture.com'
        
        if not self.api_key or not self.api_secret:
            logger.error("Không tìm thấy API key hoặc API secret trong môi trường")
            sys.exit(1)
    
    def _generate_signature(self, params):
        """Tạo signature cho yêu cầu API"""
        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def get_positions(self):
        """Lấy thông tin vị thế"""
        endpoint = '/fapi/v2/positionRisk'
        params = {'timestamp': int(time.time() * 1000)}
        params['signature'] = self._generate_signature(params)
        
        headers = {'X-MBX-APIKEY': self.api_key}
        response = requests.get(f"{self.base_url}{endpoint}", params=params, headers=headers)
        
        if response.status_code == 200:
            positions = response.json()
            active_positions = [p for p in positions if float(p.get('positionAmt', 0)) != 0]
            return active_positions
        else:
            logger.error(f"Lỗi khi lấy vị thế: {response.status_code} - {response.text}")
            return []
    
    def create_market_order(self, symbol, side, quantity, reduce_only=False):
        """Tạo lệnh market"""
        endpoint = '/fapi/v1/order'
        params = {
            'symbol': symbol,
            'side': side,
            'type': 'MARKET',
            'quantity': quantity,
            'timestamp': int(time.time() * 1000)
        }
        
        if reduce_only:
            params['reduceOnly'] = 'true'  # Kiểu chuỗi thay vì boolean
            
        params['signature'] = self._generate_signature(params)
        
        headers = {'X-MBX-APIKEY': self.api_key}
        
        logger.info(f"Lệnh gửi đi: {json.dumps(params, indent=2)}")
        response = requests.post(f"{self.base_url}{endpoint}", params=params, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Lỗi tạo lệnh: {response.status_code} - {response.text}")
            return {'error': response.text}
    
    def create_tp_sl_order(self, symbol, side, order_type, quantity, stop_price, reduce_only=False):
        """Tạo lệnh take profit hoặc stop loss"""
        endpoint = '/fapi/v1/order'
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,  # 'TAKE_PROFIT_MARKET' hoặc 'STOP_MARKET'
            'quantity': quantity,
            'stopPrice': stop_price,
            'timestamp': int(time.time() * 1000)
        }
        
        if reduce_only:
            params['reduceOnly'] = 'true'  # Kiểu chuỗi thay vì boolean
            
        params['signature'] = self._generate_signature(params)
        
        headers = {'X-MBX-APIKEY': self.api_key}
        
        logger.info(f"Lệnh {order_type} gửi đi: {json.dumps(params, indent=2)}")
        response = requests.post(f"{self.base_url}{endpoint}", params=params, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Lỗi tạo lệnh {order_type}: {response.status_code} - {response.text}")
            return {'error': response.text}

def test_direct_market_order():
    """Thử nghiệm trực tiếp lệnh market với Binance API"""
    client = BinanceTestClient()
    
    # Lấy vị thế hiện tại
    positions = client.get_positions()
    
    if not positions:
        logger.warning("Không tìm thấy vị thế nào")
        return False
    
    logger.info(f"Tìm thấy {len(positions)} vị thế active")
    
    # Chọn vị thế đầu tiên để đóng một phần
    position = positions[0]
    symbol = position['symbol']
    position_amt = float(position['positionAmt'])
    
    # Tính toán lượng đóng (10% vị thế)
    close_amt = round(abs(position_amt) * 0.1, 3)
    side = "SELL" if position_amt > 0 else "BUY"
    
    # Kiểm tra xem số lượng đóng có đáp ứng yêu cầu tối thiểu không
    if close_amt < 0.001:
        logger.warning(f"Số lượng đóng {close_amt} quá nhỏ, điều chỉnh lên mức tối thiểu 0.001")
        close_amt = 0.001
    
    # Tạo lệnh market
    logger.info(f"Thử đóng {close_amt} {symbol} bằng lệnh {side}")
    result = client.create_market_order(symbol, side, close_amt, reduce_only=True)
    
    if result.get('error'):
        logger.error(f"Thất bại: {result.get('error')}")
        return False
    else:
        logger.info(f"Thành công: {json.dumps(result, indent=2)}")
        return True

def test_tp_sl_orders():
    """Thử nghiệm trực tiếp lệnh TP/SL với Binance API"""
    client = BinanceTestClient()
    
    # Lấy vị thế hiện tại
    positions = client.get_positions()
    long_positions = [p for p in positions if float(p.get('positionAmt', 0)) > 0]
    
    if not long_positions:
        logger.warning("Không tìm thấy vị thế LONG nào để đặt TP/SL")
        return False
    
    # Chọn vị thế LONG đầu tiên
    position = long_positions[0]
    symbol = position['symbol']
    position_amt = float(position['positionAmt'])
    entry_price = float(position['entryPrice'])
    
    # Tính giá TP/SL
    tp_price = round(entry_price * 1.05, 2)  # +5%
    sl_price = round(entry_price * 0.97, 2)  # -3%
    
    # Tính lượng order (mỗi lệnh 25% vị thế)
    order_qty = round(position_amt * 0.25, 3)
    
    if order_qty < 0.001:
        logger.warning(f"Số lượng order {order_qty} quá nhỏ, điều chỉnh lên mức tối thiểu 0.001")
        order_qty = 0.001
    
    # 1. Tạo lệnh take profit
    tp_result = client.create_tp_sl_order(
        symbol=symbol,
        side="SELL",
        order_type="TAKE_PROFIT_MARKET",
        quantity=order_qty,
        stop_price=tp_price,
        reduce_only=True
    )
    
    tp_success = not tp_result.get('error')
    
    # 2. Tạo lệnh stop loss
    sl_result = client.create_tp_sl_order(
        symbol=symbol,
        side="SELL",
        order_type="STOP_MARKET",
        quantity=order_qty,
        stop_price=sl_price,
        reduce_only=True
    )
    
    sl_success = not sl_result.get('error')
    
    return tp_success or sl_success

if __name__ == "__main__":
    logger.info("=== KIỂM TRA TRỰC TIẾP API BINANCE FUTURES ===")
    
    # Thử tạo lệnh market
    logger.info("--- Kiểm tra lệnh MARKET ---")
    market_result = test_direct_market_order()
    
    if market_result:
        # Nếu lệnh market thành công, thử TP/SL
        logger.info("--- Kiểm tra lệnh TP/SL ---")
        tp_sl_result = test_tp_sl_orders()
        
        if tp_sl_result:
            logger.info("=== KIỂM TRA TP/SL THÀNH CÔNG ===")
        else:
            logger.error("=== KIỂM TRA TP/SL THẤT BẠI ===")
    else:
        logger.error("=== KIỂM TRA MARKET THẤT BẠI ===")