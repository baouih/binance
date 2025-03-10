#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import ccxt
from binance.client import Client

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("APIDataValidator")

def validate_api_credentials(api_key, api_secret, testnet=True):
    """
    Kiểm tra xem API key và API secret có hợp lệ không
    
    Args:
        api_key (str): API key
        api_secret (str): API secret
        testnet (bool): Sử dụng testnet hay không
    
    Returns:
        bool: True nếu API hợp lệ, False nếu không
    """
    try:
        # Khởi tạo client
        if testnet:
            client = Client(api_key, api_secret, testnet=True)
        else:
            client = Client(api_key, api_secret)
        
        # Thử lấy thông tin tài khoản
        account_info = client.get_account()
        
        # Kiểm tra xem có lỗi không
        if account_info and 'balances' in account_info:
            logger.info("API credentials hợp lệ")
            return True
        else:
            logger.warning("API credentials không hợp lệ")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra API credentials: {str(e)}")
        return False

def validate_api_credentials_ccxt(api_key, api_secret, testnet=True):
    """
    Kiểm tra xem API key và API secret có hợp lệ không sử dụng ccxt
    
    Args:
        api_key (str): API key
        api_secret (str): API secret
        testnet (bool): Sử dụng testnet hay không
    
    Returns:
        bool: True nếu API hợp lệ, False nếu không
    """
    try:
        # Khởi tạo exchange
        options = {}
        if testnet:
            options['defaultType'] = 'future'
            options['test'] = True
        
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': options
        })
        
        # Thử lấy thông tin tài khoản
        balance = exchange.fetch_balance()
        
        # Kiểm tra xem có lỗi không
        if balance and 'total' in balance:
            logger.info("API credentials hợp lệ (ccxt)")
            return True
        else:
            logger.warning("API credentials không hợp lệ (ccxt)")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra API credentials (ccxt): {str(e)}")
        return False

def get_account_balance(api_key, api_secret, testnet=True):
    """
    Lấy số dư tài khoản
    
    Args:
        api_key (str): API key
        api_secret (str): API secret
        testnet (bool): Sử dụng testnet hay không
    
    Returns:
        float: Số dư tài khoản (USDT), None nếu có lỗi
    """
    try:
        if testnet:
            client = Client(api_key, api_secret, testnet=True)
        else:
            client = Client(api_key, api_secret)
        
        # Lấy số dư futures
        futures_account = client.futures_account_balance()
        
        # Tìm USDT balance
        for asset in futures_account:
            if asset['asset'] == 'USDT':
                return float(asset['balance'])
        
        return None
    except Exception as e:
        logger.error(f"Lỗi khi lấy số dư tài khoản: {str(e)}")
        return None

def main():
    """Hàm chính để kiểm tra API credentials"""
    api_key = os.environ.get("BINANCE_TESTNET_API_KEY")
    api_secret = os.environ.get("BINANCE_TESTNET_API_SECRET")
    
    if not api_key or not api_secret:
        logger.error("Thiếu API key hoặc API secret")
        return
    
    is_valid = validate_api_credentials(api_key, api_secret, testnet=True)
    
    if is_valid:
        print("API credentials hợp lệ")
        
        # Lấy số dư tài khoản
        balance = get_account_balance(api_key, api_secret, testnet=True)
        if balance is not None:
            print(f"Số dư tài khoản: {balance} USDT")
        else:
            print("Không lấy được số dư tài khoản")
    else:
        print("API credentials không hợp lệ")

if __name__ == "__main__":
    main()