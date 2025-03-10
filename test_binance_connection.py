#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kiểm tra kết nối với Binance API
"""

import os
import json
import logging
import sys
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("api_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("api_test")

def load_config():
    """Tải cấu hình từ file account_config.json"""
    try:
        if os.path.exists("account_config.json"):
            with open("account_config.json", "r") as f:
                config = json.load(f)
            logger.info("Đã tải cấu hình từ account_config.json")
            return config
        else:
            logger.error("Không tìm thấy file account_config.json")
            return None
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình: {e}")
        return None

def test_binance_connection():
    """Kiểm tra kết nối với Binance API"""
    config = load_config()
    if not config:
        print("Không thể tải cấu hình. Vui lòng kiểm tra file account_config.json")
        return False
    
    # Kiểm tra API key và secret
    api_key = config.get("api_key", "")
    api_secret = config.get("api_secret", "")
    
    if not api_key or not api_secret:
        print("API key hoặc API secret chưa được cấu hình")
        return False
    
    # Kiểm tra chế độ testnet
    testnet = config.get("testnet", True)
    print(f"Chế độ API: {'Testnet' if testnet else 'Thực'}")
    
    # Thử kết nối với Binance API
    try:
        from binance.client import Client
        
        # Khởi tạo client
        print("Đang kết nối với Binance API...")
        if testnet:
            client = Client(api_key, api_secret, testnet=True)
        else:
            client = Client(api_key, api_secret)
        
        # Kiểm tra kết nối bằng cách lấy thông tin thị trường
        print("Kiểm tra kết nối bằng cách lấy thông tin thị trường...")
        ticker = client.get_ticker(symbol='BTCUSDT')
        
        print(f"Kết nối thành công! Giá BTC hiện tại: {ticker['lastPrice']}")
        
        # Thử lấy thông tin tài khoản
        print("Kiểm tra thông tin tài khoản...")
        if testnet:
            account = client.futures_account()
        else:
            account = client.futures_account()
        
        print("Thông tin tài khoản:")
        print(f"- Tổng số dư: {account['totalWalletBalance']} USDT")
        print(f"- Số dư khả dụng: {account['availableBalance']} USDT")
        
        # Kiểm tra lấy danh sách vị thế
        positions = [p for p in account['positions'] if float(p['positionAmt']) != 0]
        print(f"Số vị thế đang mở: {len(positions)}")
        for pos in positions:
            symbol = pos['symbol']
            amount = float(pos['positionAmt'])
            entry_price = float(pos['entryPrice'])
            unrealized_pnl = float(pos['unrealizedProfit'])
            leverage = pos['leverage']
            
            direction = "LONG" if amount > 0 else "SHORT"
            print(f"- {symbol}: {direction}, Số lượng: {abs(amount)}, Giá vào: {entry_price}, P/L: {unrealized_pnl}, Đòn bẩy: {leverage}x")
        
        return True
        
    except Exception as e:
        print(f"Lỗi khi kết nối với Binance API: {e}")
        logger.error(f"Lỗi khi kết nối với Binance API: {e}")
        return False

def main():
    print("=" * 50)
    print("KIỂM TRA KẾT NỐI BINANCE API")
    print("=" * 50)
    
    result = test_binance_connection()
    
    print("\nKết quả:")
    if result:
        print("✅ Kết nối API thành công!")
    else:
        print("❌ Kết nối API thất bại!")
    
    print("\nHướng dẫn:")
    print("1. Nếu kết nối thất bại, kiểm tra lại API key và API secret trong file account_config.json")
    print("2. Đảm bảo tài khoản Binance của bạn đã được kích hoạt Futures")
    print("3. Nếu sử dụng testnet, đảm bảo bạn đã đăng ký tài khoản Binance Futures Testnet")
    
    print("\nThời gian kiểm tra:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 50)

if __name__ == "__main__":
    main()