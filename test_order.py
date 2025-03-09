#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import logging
import json
from binance_api import BinanceAPI
from binance_api_fixes import apply_fixes_to_api

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_order_without_position_side():
    """Test đặt lệnh mà không có position_side"""
    api = BinanceAPI()
    api = apply_fixes_to_api(api)
    
    print('Kiểm tra lệnh không có position_side...')
    try:
        params = {
            'symbol': 'BTCUSDT', 
            'side': 'BUY', 
            'type': 'MARKET', 
            'quantity': 0.001,
            'newOrderRespType': 'RESULT'
        }
        
        timestamp = api._get_timestamp()
        params['timestamp'] = timestamp
        signature = api._generate_signature(params)
        params['signature'] = signature
        
        response = requests.post(
            f'{api.base_url}fapi/v1/order', 
            params=params, 
            headers=api._get_headers()
        )
        
        print(f'Mã phản hồi: {response.status_code}')
        print(f'Nội dung phản hồi: {response.text}')
        
        if response.status_code == 200:
            return True
        return False
    except Exception as e:
        print(f'Lỗi: {str(e)}')
        return False

def test_order_with_api_method():
    """Test đặt lệnh sử dụng phương thức API trực tiếp"""
    api = BinanceAPI()
    api = apply_fixes_to_api(api)
    
    print('\nKiểm tra lệnh sử dụng phương thức API...')
    try:
        # Lấy chi tiết lỗi nếu có
        import requests
        import time
        from urllib.parse import urlencode
        import hmac
        import hashlib
        
        params = {
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'type': 'MARKET',
            'quantity': 0.001
        }
        
        # Thêm timestamp
        timestamp = int(time.time() * 1000)
        params['timestamp'] = timestamp
        
        # Tạo signature thủ công
        query_string = urlencode(params)
        signature = hmac.new(
            api.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        params['signature'] = signature
        
        # Tạo URL đầy đủ
        url = f"{api.base_url}/fapi/v1/order"
        print(f"URL: {url}")
        print(f"Params: {params}")
        
        # Tạo headers thủ công
        headers = {
            'X-MBX-APIKEY': api.api_key
        }
        print(f"Headers: {headers}")
        
        # Gửi request
        response = requests.post(url, params=params, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            return True
        return False
    except Exception as e:
        print(f'Lỗi: {str(e)}')
        return False

def test_binance_api_fixes():
    """Test đặt lệnh sử dụng binance_api_fixes"""
    api = BinanceAPI()
    api = apply_fixes_to_api(api)
    
    print('\nKiểm tra lệnh sử dụng binance_api_fixes...')
    try:
        result = api.create_order_with_position_side(
            symbol='BTCUSDT',
            side='BUY',
            order_type='MARKET',
            quantity=0.001
        )
        
        print(f'Kết quả đặt lệnh: {json.dumps(result, indent=2)}')
        return True
    except Exception as e:
        print(f'Lỗi: {str(e)}')
        return False

def show_account_positions():
    """Hiển thị các vị thế trong tài khoản"""
    api = BinanceAPI()
    api = apply_fixes_to_api(api)
    
    print('\nVị thế hiện tại trong tài khoản:')
    try:
        positions = api.get_futures_position_risk()
        active_positions = [p for p in positions if abs(float(p['positionAmt'])) > 0]
        
        for pos in active_positions:
            symbol = pos['symbol']
            position_amt = float(pos['positionAmt'])
            entry_price = float(pos['entryPrice'])
            unrealized_pnl = float(pos['unRealizedProfit'])
            leverage = float(pos['leverage'])
            
            side = 'LONG' if position_amt > 0 else 'SHORT'
            print(f"Symbol: {symbol}, Side: {side}, Amount: {position_amt}, Entry: {entry_price}, PnL: {unrealized_pnl}, Leverage: {leverage}x")
        
        if not active_positions:
            print("Không có vị thế nào.")
    except Exception as e:
        print(f'Lỗi: {str(e)}')

if __name__ == "__main__":
    print("===== KIỂM TRA ĐẶT LỆNH VỚI BINANCE FUTURES TESTNET =====")
    
    # Kiểm tra vị thế hiện tại
    show_account_positions()
    
    # Các phương pháp khác nhau để đặt lệnh
    success1 = test_order_without_position_side()
    success2 = test_order_with_api_method() 
    success3 = test_binance_api_fixes()
    
    # Kiểm tra lại vị thế sau khi đặt lệnh
    if success1 or success2 or success3:
        print("\nKiểm tra lại vị thế sau khi đặt lệnh:")
        show_account_positions()
    else:
        print("\nTất cả các phương pháp đặt lệnh đều thất bại.")