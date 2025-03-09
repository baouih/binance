#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import requests
from binance_api import BinanceAPI

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('check_api_rate_limit')

def load_account_config():
    """Tải cấu hình tài khoản từ file"""
    try:
        with open('account_config.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình tài khoản: {str(e)}")
        return {}

def check_api_endpoints(testnet=True):
    """
    Kiểm tra tình trạng API Binance và giới hạn rate limit
    """
    # Khởi tạo API
    config = load_account_config()
    api_key = config.get('api_key', '')
    api_secret = config.get('api_secret', '')
    
    api = BinanceAPI(api_key, api_secret, testnet=testnet)
    
    # Kiểm tra các API endpoint cơ bản và in ra headers
    try:
        # Kiểm tra API server time
        logger.info("Kiểm tra API server time...")
        response = api._request('GET', 'time')
        logger.info(f"Kết quả: {response}")
        
        # Kiểm tra thông tin hệ thống
        logger.info("\nKiểm tra thông tin hệ thống...")
        response = api._request('GET', 'exchangeInfo')
        logger.info(f"exchangeInfo headers: {response.get('headers', 'Không có thông tin headers')}")
        
        # Kiểm tra tài khoản
        logger.info("\nKiểm tra thông tin tài khoản...")
        account_info = api._request('GET', 'account', signed=True)
        logger.info(f"account headers: {account_info.get('headers', 'Không có thông tin headers')}")
        
        # Kiểm tra giới hạn lệnh
        logger.info("\nKiểm tra giới hạn lệnh...")
        
        # Thử test order với SL
        logger.info("\nThử test order STOP_MARKET...")
        try:
            test_result = api.futures_create_order(
                symbol="BTCUSDT",
                side="SELL",
                type="STOP_MARKET",
                stopPrice=60000,
                quantity=0.001,
                reduceOnly=True,
                timeInForce="GTC",
                test=True
            )
            logger.info(f"Test order thành công: {test_result}")
        except Exception as e:
            error_details = getattr(e, 'response', None)
            if error_details and hasattr(error_details, 'text'):
                error_text = error_details.text
                logger.error(f"Test order không thành công: {str(e)}")
                logger.error(f"Chi tiết lỗi: {error_text}")
            else:
                logger.error(f"Test order không thành công: {str(e)}")
        
        # Thử test order với TP
        logger.info("\nThử test order TAKE_PROFIT_MARKET...")
        try:
            test_result = api.futures_create_order(
                symbol="BTCUSDT",
                side="SELL",
                type="TAKE_PROFIT_MARKET",
                stopPrice=90000,
                quantity=0.001,
                reduceOnly=True,
                timeInForce="GTC",
                test=True
            )
            logger.info(f"Test order thành công: {test_result}")
        except Exception as e:
            error_details = getattr(e, 'response', None)
            if error_details and hasattr(error_details, 'text'):
                error_text = error_details.text
                logger.error(f"Test order không thành công: {str(e)}")
                logger.error(f"Chi tiết lỗi: {error_text}")
            else:
                logger.error(f"Test order không thành công: {str(e)}")
        
        # Kiểm tra exchange info chi tiết
        logger.info("\nKiểm tra exchange info chi tiết ETHUSDT...")
        exchange_info = api._request('GET', 'exchangeInfo')
        symbols_info = exchange_info.get('symbols', [])
        
        for symbol_info in symbols_info:
            if symbol_info.get('symbol') == 'ETHUSDT':
                logger.info(f"Thông tin chi tiết ETHUSDT: {json.dumps(symbol_info, indent=2)}")
                break
        
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra API: {str(e)}")

if __name__ == "__main__":
    check_api_endpoints(testnet=True)