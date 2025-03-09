#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import logging
import requests
import hmac
import hashlib
import time
import urllib.parse
import os

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('check_position_side')

def get_binance_signed_params(api_secret, params=None):
    """Tạo tham số đã ký cho Binance API"""
    if params is None:
        params = {}
        
    # Thêm timestamp
    params['timestamp'] = int(time.time() * 1000)
    
    # Tạo query string và signature
    query_string = urllib.parse.urlencode(params)
    signature = hmac.new(
        api_secret.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Thêm signature vào params
    params['signature'] = signature
    return params

def check_position_side_dual():
    """Kiểm tra cài đặt position side của tài khoản"""
    api_key = os.environ.get('BINANCE_TESTNET_API_KEY')
    api_secret = os.environ.get('BINANCE_TESTNET_API_SECRET')
    
    if not api_key or not api_secret:
        logger.error("Không tìm thấy BINANCE_TESTNET_API_KEY hoặc BINANCE_TESTNET_API_SECRET trong môi trường")
        return None
        
    # Endpoint và header
    endpoint = 'https://testnet.binancefuture.com/fapi/v1/positionSide/dual'
    headers = {'X-MBX-APIKEY': api_key}
    
    # Tạo tham số đã ký
    params = get_binance_signed_params(api_secret)
    
    # Gửi yêu cầu
    response = requests.get(endpoint, params=params, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Lỗi API: {response.status_code} - {response.text}")
        return None

def toggle_position_side_dual(enable_dual=False):
    """Bật/tắt chế độ position side dual (hedge mode)"""
    api_key = os.environ.get('BINANCE_TESTNET_API_KEY')
    api_secret = os.environ.get('BINANCE_TESTNET_API_SECRET')
    
    if not api_key or not api_secret:
        logger.error("Không tìm thấy BINANCE_TESTNET_API_KEY hoặc BINANCE_TESTNET_API_SECRET trong môi trường")
        return False
        
    # Endpoint và header
    endpoint = 'https://testnet.binancefuture.com/fapi/v1/positionSide/dual'
    headers = {'X-MBX-APIKEY': api_key}
    
    # Tham số
    params = {
        'dualSidePosition': 'true' if enable_dual else 'false'
    }
    
    # Tạo tham số đã ký
    params = get_binance_signed_params(api_secret, params)
    
    # Gửi yêu cầu POST
    response = requests.post(endpoint, params=params, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        logger.info(f"Đã thay đổi position side dual: {json.dumps(result, indent=2)}")
        return True
    else:
        logger.error(f"Lỗi API khi thay đổi position side dual: {response.status_code} - {response.text}")
        return False

def create_market_order_with_position_side(symbol, side, quantity, position_side, reduce_only=False):
    """Tạo lệnh market với position side xác định"""
    api_key = os.environ.get('BINANCE_TESTNET_API_KEY')
    api_secret = os.environ.get('BINANCE_TESTNET_API_SECRET')
    
    if not api_key or not api_secret:
        logger.error("Không tìm thấy BINANCE_TESTNET_API_KEY hoặc BINANCE_TESTNET_API_SECRET trong môi trường")
        return None
        
    # Endpoint và header
    endpoint = 'https://testnet.binancefuture.com/fapi/v1/order'
    headers = {'X-MBX-APIKEY': api_key}
    
    # Tham số lệnh
    params = {
        'symbol': symbol,
        'side': side,
        'type': 'MARKET',
        'quantity': quantity,
    }
    
    # Thêm position side nếu ở chế độ hedge mode
    if position_side in ['LONG', 'SHORT', 'BOTH']:
        params['positionSide'] = position_side
        
    # Thêm reduceOnly nếu cần
    if reduce_only:
        params['reduceOnly'] = 'true'
    
    # Tạo tham số đã ký
    params = get_binance_signed_params(api_secret, params)
    
    # Gửi yêu cầu POST
    logger.info(f"Tham số lệnh: {json.dumps(params, indent=2)}")
    response = requests.post(endpoint, params=params, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        logger.info(f"Lệnh thành công: {json.dumps(result, indent=2)}")
        return result
    else:
        logger.error(f"Lỗi API khi tạo lệnh: {response.status_code} - {response.text}")
        return {'error': response.text}

if __name__ == "__main__":
    logger.info("=== KIỂM TRA VÀ CẤU HÌNH POSITION SIDE DUAL ===")
    
    # Kiểm tra cài đặt hiện tại
    current_setting = check_position_side_dual()
    
    if current_setting is not None:
        logger.info(f"Cài đặt position side hiện tại: {json.dumps(current_setting, indent=2)}")
        
        # Lấy giá trị dualSidePosition
        is_dual_side = current_setting.get('dualSidePosition', False)
        
        if is_dual_side:
            logger.info("Tài khoản đang ở chế độ hedge mode (dual position side)")
            
            # Thử tạo lệnh với position side
            logger.info("Thử tạo lệnh MARKET với position side LONG")
            create_market_order_with_position_side(
                symbol="BTCUSDT",
                side="BUY",
                quantity=0.001,
                position_side="LONG"
            )
        else:
            logger.info("Tài khoản đang ở chế độ one-way (single position side)")
            
            # Thử tạo lệnh thông thường
            logger.info("Thử tạo lệnh MARKET thông thường")
            create_market_order_with_position_side(
                symbol="BTCUSDT",
                side="BUY",
                quantity=0.001,
                position_side=None
            )
            
            # Chuyển sang chế độ hedge mode (dual position side)
            logger.info("Chuyển sang chế độ hedge mode (dual position side)")
            if toggle_position_side_dual(enable_dual=True):
                logger.info("Đã chuyển sang chế độ hedge mode thành công")
                
                # Kiểm tra lại cài đặt
                new_setting = check_position_side_dual()
                logger.info(f"Cài đặt mới: {json.dumps(new_setting, indent=2)}")
                
                # Thử tạo lệnh với position side
                logger.info("Thử tạo lệnh MARKET với position side LONG")
                create_market_order_with_position_side(
                    symbol="BTCUSDT",
                    side="BUY",
                    quantity=0.001,
                    position_side="LONG"
                )
            else:
                logger.error("Không thể chuyển sang chế độ hedge mode")
    else:
        logger.error("Không thể kiểm tra cài đặt position side")