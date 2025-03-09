#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import logging
import time
import os
import requests
import hmac
import hashlib
import urllib.parse

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('fix_order_creation')

class BinanceOrderCreator:
    """Class để tạo lệnh đúng định dạng cho Binance Futures API"""
    
    def __init__(self):
        # Đọc thông tin từ môi trường
        self.api_key = os.environ.get('BINANCE_TESTNET_API_KEY')
        self.api_secret = os.environ.get('BINANCE_TESTNET_API_SECRET')
        self.base_url = 'https://testnet.binancefuture.com'
        
        if not self.api_key or not self.api_secret:
            logger.error("Không tìm thấy API key hoặc API secret trong môi trường")
            sys.exit(1)
        
        # Kiểm tra chế độ position side
        self.hedge_mode = self._check_hedge_mode()
        logger.info(f"Tài khoản đang ở chế độ hedge mode: {self.hedge_mode}")
        
        # Lấy thông tin tỷ giá hiện tại
        self.current_prices = self._get_current_prices()
    
    def _generate_signature(self, params):
        """Tạo signature cho yêu cầu API"""
        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _check_hedge_mode(self):
        """Kiểm tra xem tài khoản có đang ở chế độ hedge mode không"""
        endpoint = '/fapi/v1/positionSide/dual'
        params = {'timestamp': int(time.time() * 1000)}
        params['signature'] = self._generate_signature(params)
        
        headers = {'X-MBX-APIKEY': self.api_key}
        response = requests.get(f"{self.base_url}{endpoint}", params=params, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            return result.get('dualSidePosition', False)
        else:
            logger.error(f"Lỗi khi kiểm tra hedge mode: {response.status_code} - {response.text}")
            return False
    
    def _get_current_prices(self):
        """Lấy giá hiện tại của các cặp giao dịch"""
        endpoint = '/fapi/v1/ticker/price'
        response = requests.get(f"{self.base_url}{endpoint}")
        
        if response.status_code == 200:
            prices = {item['symbol']: float(item['price']) for item in response.json()}
            logger.info(f"Đã lấy giá của {len(prices)} cặp giao dịch")
            return prices
        else:
            logger.error(f"Lỗi khi lấy giá: {response.status_code} - {response.text}")
            return {}
    
    def _calculate_quantity(self, symbol, usd_amount=100):
        """Tính toán số lượng dựa trên giá trị USD và giá hiện tại"""
        if symbol not in self.current_prices:
            logger.error(f"Không tìm thấy giá của {symbol}")
            return None
        
        price = self.current_prices[symbol]
        
        # Lấy thông tin precision của symbol
        symbol_info = self._get_symbol_info(symbol)
        if not symbol_info:
            logger.error(f"Không lấy được thông tin của {symbol}")
            return None
        
        quantity_precision = symbol_info.get('quantityPrecision', 3)
        
        # Đảm bảo giá trị lệnh ít nhất là 100 USDT
        if usd_amount < 100:
            usd_amount = 100
            logger.info(f"Đã điều chỉnh giá trị lệnh lên {usd_amount} USDT để đáp ứng yêu cầu tối thiểu")
        
        # Tính toán số lượng với precision đúng
        quantity = usd_amount / price
        quantity = round(quantity, quantity_precision)
        
        # Kiểm tra lại giá trị lệnh
        order_value = quantity * price
        if order_value < 100:
            # Điều chỉnh số lượng lên để đạt giá trị tối thiểu
            old_quantity = quantity
            quantity = 100 / price
            quantity = round(quantity, quantity_precision)
            logger.info(f"Đã điều chỉnh số lượng từ {old_quantity} lên {quantity} để đạt giá trị tối thiểu 100 USDT")
        
        logger.info(f"Đã tính toán số lượng cho {symbol}: {quantity} (giá: {price}, USD: {usd_amount}, giá trị: {quantity * price})")
        return quantity
    
    def _get_symbol_info(self, symbol):
        """Lấy thông tin chi tiết của symbol"""
        endpoint = '/fapi/v1/exchangeInfo'
        response = requests.get(f"{self.base_url}{endpoint}")
        
        if response.status_code == 200:
            exchange_info = response.json()
            for sym_info in exchange_info.get('symbols', []):
                if sym_info.get('symbol') == symbol:
                    return sym_info
        
        logger.error(f"Không tìm thấy thông tin của {symbol}")
        return None
    
    def create_market_order(self, symbol, side, usd_amount=100, position_side=None, reduce_only=False):
        """Tạo lệnh market với số lượng dựa trên giá trị USD"""
        # Tính toán số lượng
        quantity = self._calculate_quantity(symbol, usd_amount)
        if not quantity:
            return {'error': f"Không thể tính toán số lượng cho {symbol}"}
        
        # Chuẩn bị tham số lệnh
        endpoint = '/fapi/v1/order'
        params = {
            'symbol': symbol,
            'side': side,
            'type': 'MARKET',
            'quantity': quantity,
            'timestamp': int(time.time() * 1000)
        }
        
        # Thêm positionSide nếu ở chế độ hedge mode và được chỉ định
        if self.hedge_mode and position_side:
            if position_side in ['LONG', 'SHORT']:
                params['positionSide'] = position_side
        
        # Thêm reduceOnly nếu cần
        if reduce_only:
            params['reduceOnly'] = 'true'
        
        # Tạo signature
        params['signature'] = self._generate_signature(params)
        
        # Gửi yêu cầu
        headers = {'X-MBX-APIKEY': self.api_key}
        logger.info(f"Tham số lệnh: {json.dumps(params, indent=2)}")
        
        response = requests.post(f"{self.base_url}{endpoint}", params=params, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Lệnh thành công: {json.dumps(result, indent=2)}")
            return result
        else:
            error_text = response.text
            logger.error(f"Lỗi tạo lệnh: {response.status_code} - {error_text}")
            
            # Phân tích lỗi
            try:
                error_json = json.loads(error_text)
                error_code = error_json.get('code')
                error_msg = error_json.get('msg')
                
                if error_code == -4061:  # Order's position side does not match user's setting
                    logger.error("Lỗi position side không khớp với cài đặt")
                    if self.hedge_mode:
                        logger.info("Thử lại với position side LONG")
                        params['positionSide'] = 'LONG'
                        params['timestamp'] = int(time.time() * 1000)
                        params['signature'] = self._generate_signature(params)
                        
                        response = requests.post(f"{self.base_url}{endpoint}", params=params, headers=headers)
                        if response.status_code == 200:
                            result = response.json()
                            logger.info(f"Lệnh thành công với position side LONG: {json.dumps(result, indent=2)}")
                            return result
            except:
                pass
            
            return {'error': error_text}
    
    def create_tp_sl_order(self, symbol, position_side, order_type, usd_amount, stop_price, reduce_only=True):
        """Tạo lệnh take profit hoặc stop loss"""
        # Tính toán số lượng
        quantity = self._calculate_quantity(symbol, usd_amount)
        if not quantity:
            return {'error': f"Không thể tính toán số lượng cho {symbol}"}
        
        # Xác định side dựa vào position_side
        side = "SELL" if position_side == "LONG" else "BUY"
        
        # Chuẩn bị tham số lệnh
        endpoint = '/fapi/v1/order'
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,  # 'TAKE_PROFIT_MARKET' hoặc 'STOP_MARKET'
            'quantity': quantity,
            'stopPrice': stop_price,
            'timestamp': int(time.time() * 1000)
        }
        
        # Thêm positionSide nếu ở chế độ hedge mode
        if self.hedge_mode:
            params['positionSide'] = position_side
            # Không thêm reduceOnly khi đã chỉ định positionSide trong hedge mode
        else:
            # Chỉ thêm reduceOnly khi ở chế độ one-way và cần thiết
            if reduce_only:
                params['reduceOnly'] = 'true'
            
        # Thêm workingType
        params['workingType'] = 'MARK_PRICE'
        
        # Tạo signature
        params['signature'] = self._generate_signature(params)
        
        # Gửi yêu cầu
        headers = {'X-MBX-APIKEY': self.api_key}
        logger.info(f"Tham số lệnh {order_type}: {json.dumps(params, indent=2)}")
        
        response = requests.post(f"{self.base_url}{endpoint}", params=params, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Lệnh {order_type} thành công: {json.dumps(result, indent=2)}")
            return result
        else:
            logger.error(f"Lỗi tạo lệnh {order_type}: {response.status_code} - {response.text}")
            return {'error': response.text}

def test_order_creation():
    """Thử nghiệm tạo các loại lệnh"""
    creator = BinanceOrderCreator()
    
    # 1. Tạo lệnh MARKET mua BTC
    logger.info("Thử tạo lệnh MARKET mua BTC (200 USDT)")
    if creator.hedge_mode:
        btc_result = creator.create_market_order(
            symbol="BTCUSDT",
            side="BUY",
            usd_amount=200,
            position_side="LONG"
        )
    else:
        btc_result = creator.create_market_order(
            symbol="BTCUSDT",
            side="BUY",
            usd_amount=200
        )
    
    btc_success = not btc_result.get('error')
    
    # 2. Nếu thành công, thử tạo lệnh TP/SL
    if btc_success:
        logger.info("Thử tạo lệnh Take Profit và Stop Loss")
        
        # Lấy giá hiện tại của BTC
        btc_price = creator.current_prices.get('BTCUSDT', 0)
        
        if btc_price > 0:
            # Tính giá TP/SL
            tp_price = round(btc_price * 1.05, 2)  # +5%
            sl_price = round(btc_price * 0.97, 2)  # -3%
            
            # Tạo lệnh Take Profit
            if creator.hedge_mode:
                tp_result = creator.create_tp_sl_order(
                    symbol="BTCUSDT",
                    position_side="LONG",
                    order_type="TAKE_PROFIT_MARKET",
                    usd_amount=50,  # 50% vị thế
                    stop_price=tp_price
                )
            else:
                tp_result = creator.create_tp_sl_order(
                    symbol="BTCUSDT",
                    position_side=None,
                    order_type="TAKE_PROFIT_MARKET",
                    usd_amount=50,
                    stop_price=tp_price
                )
            
            time.sleep(1)  # Đợi 1s giữa các lệnh
            
            # Tạo lệnh Stop Loss
            if creator.hedge_mode:
                sl_result = creator.create_tp_sl_order(
                    symbol="BTCUSDT",
                    position_side="LONG",
                    order_type="STOP_MARKET",
                    usd_amount=50,  # 50% vị thế còn lại
                    stop_price=sl_price
                )
            else:
                sl_result = creator.create_tp_sl_order(
                    symbol="BTCUSDT",
                    position_side=None,
                    order_type="STOP_MARKET",
                    usd_amount=50,
                    stop_price=sl_price
                )
            
            tp_success = not tp_result.get('error')
            sl_success = not sl_result.get('error')
            
            return tp_success or sl_success
    
    return btc_success

if __name__ == "__main__":
    logger.info("=== KIỂM TRA TẠO LỆNH CHO BINANCE FUTURES ===")
    
    # Thử nghiệm tạo lệnh
    result = test_order_creation()
    
    if result:
        logger.info("=== KIỂM TRA THÀNH CÔNG ===")
    else:
        logger.error("=== KIỂM TRA THẤT BẠI ===")