#!/usr/bin/env python3
"""
Test script để kiểm tra kết nối đến Binance Testnet API

Script này kiểm tra kết nối đến Binance Testnet API với các API keys
đã được cấu hình trong account_config.json, thông qua lớp BinanceAPI.
"""

import os
import sys
import json
import logging
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_api_connection")

# Thêm thư mục gốc vào sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Import binance_api
from binance_api import BinanceAPI

def test_connection():
    """Kiểm tra kết nối với Binance API và báo cáo kết quả"""
    logger.info("===== BẮT ĐẦU KIỂM TRA KẾT NỐI BINANCE API =====")
    
    # Tải cấu hình
    try:
        with open('account_config.json', 'r') as f:
            config = json.load(f)
            
        api_key = config.get('api_key', '')
        api_secret = config.get('api_secret', '')
        testnet = config.get('api_mode', '') == 'testnet'
        account_type = config.get('account_type', 'spot')
        
        logger.info(f"Đã tải cấu hình tài khoản: mode={config.get('api_mode')}, type={account_type}")
        logger.info(f"API Key (đã che giấu): {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}")
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
        return False
    
    # Khởi tạo API
    try:
        api = BinanceAPI(api_key, api_secret, testnet)
        logger.info(f"Đã khởi tạo BinanceAPI: testnet={testnet}, account_type={api.account_type}")
        logger.info(f"Base URL: {api.base_url}")
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo BinanceAPI: {str(e)}")
        return False
    
    # Kiểm tra kết nối cơ bản (không yêu cầu xác thực)
    try:
        logger.info("Kiểm tra 1: Lấy thông tin sàn giao dịch (không yêu cầu xác thực)")
        # Sửa API call trực tiếp để đảm bảo đúng phiên bản
        if api.account_type == 'futures':
            exchange_info = api._request('GET', 'exchangeInfo', version='v1')
        else:
            exchange_info = api.get_exchange_info()
        
        if exchange_info and 'symbols' in exchange_info:
            symbol_count = len(exchange_info['symbols'])
            logger.info(f"✅ Thành công: Lấy được {symbol_count} symbols")
        else:
            logger.error(f"❌ Lỗi: Không lấy được thông tin sàn giao dịch: {exchange_info}")
            return False
    except Exception as e:
        logger.error(f"❌ Lỗi khi gọi get_exchange_info: {str(e)}")
        return False
    
    # Kiểm tra thông tin giá
    try:
        logger.info("Kiểm tra 2: Lấy thông tin giá BTCUSDT (không yêu cầu xác thực)")
        # Sửa API call trực tiếp để đảm bảo đúng phiên bản
        if api.account_type == 'futures':
            params = {'symbol': 'BTCUSDT'}
            price_info = api._request('GET', 'ticker/price', params, version='v1')
        else:
            price_info = api.get_symbol_ticker('BTCUSDT')
            
        if price_info and 'price' in price_info:
            logger.info(f"✅ Thành công: Giá BTC hiện tại = {price_info['price']} USDT")
        else:
            logger.error(f"❌ Lỗi: Không lấy được thông tin giá: {price_info}")
            return False
    except Exception as e:
        logger.error(f"❌ Lỗi khi gọi get_symbol_ticker: {str(e)}")
        return False
    
    # Kiểm tra kết nối yêu cầu xác thực
    try:
        logger.info("Kiểm tra 3: Lấy thông tin tài khoản (yêu cầu xác thực)")
        if account_type == 'futures':
            account_info = api.get_futures_account()
        else:
            account_info = api.get_account()
            
        if account_info:
            if account_type == 'futures':
                balance = account_info.get('totalWalletBalance', 'N/A')
                logger.info(f"✅ Thành công: Số dư ví futures = {balance} USDT")
            else:
                balances = account_info.get('balances', [])
                usdt_balance = next((b['free'] for b in balances if b['asset'] == 'USDT'), 'N/A')
                logger.info(f"✅ Thành công: Số dư ví spot USDT = {usdt_balance}")
        else:
            logger.error(f"❌ Lỗi: Không lấy được thông tin tài khoản: {account_info}")
            return False
    except Exception as e:
        logger.error(f"❌ Lỗi khi gọi get_account/get_futures_account: {str(e)}")
        return False
    
    # Kiểm tra vị thế futures (chỉ áp dụng cho futures)
    if account_type == 'futures':
        try:
            logger.info("Kiểm tra 4: Lấy thông tin vị thế futures (yêu cầu xác thực)")
            positions = api.get_futures_position_risk()
            
            if isinstance(positions, list):
                open_positions = [p for p in positions if float(p.get('positionAmt', 0)) != 0]
                logger.info(f"✅ Thành công: Đã lấy {len(positions)} vị thế, có {len(open_positions)} vị thế mở")
                
                # Hiển thị chi tiết vị thế mở
                for pos in open_positions:
                    symbol = pos.get('symbol', 'N/A')
                    amount = pos.get('positionAmt', '0')
                    entry_price = pos.get('entryPrice', '0')
                    mark_price = pos.get('markPrice', '0')
                    pnl = pos.get('unRealizedProfit', '0')
                    logger.info(f"  - Vị thế: {symbol}, Lượng: {amount}, Giá vào: {entry_price}, " 
                               f"Giá hiện tại: {mark_price}, PnL: {pnl}")
            else:
                logger.error(f"❌ Lỗi: Không lấy được thông tin vị thế: {positions}")
                return False
        except Exception as e:
            logger.error(f"❌ Lỗi khi gọi get_futures_position_risk: {str(e)}")
            return False
    
    logger.info("===== KẾT THÚC KIỂM TRA KẾT NỐI BINANCE API =====")
    logger.info("✅ TẤT CẢ CÁC KIỂM TRA ĐỀU THÀNH CÔNG!")
    
    return True

if __name__ == "__main__":
    result = test_connection()
    print(f"\nKết quả kiểm tra: {'THÀNH CÔNG' if result else 'THẤT BẠI'}")
    sys.exit(0 if result else 1)