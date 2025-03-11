#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Binance Connection
----------------------
Script kiểm tra kết nối với Binance API và lấy giá BTCUSDT
"""

import os
import sys
import time
import logging
import argparse
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("test_binance_connection")

def test_connection():
    """Kiểm tra kết nối với Binance API và lấy giá BTCUSDT"""
    try:
        # Nhập các module cần thiết
        logger.info("Nhập module EnhancedBinanceAPI...")
        from enhanced_binance_api import EnhancedBinanceAPI
        
        # Kiểm tra các biến môi trường
        api_key = os.environ.get('BINANCE_TESTNET_API_KEY')
        api_secret = os.environ.get('BINANCE_TESTNET_API_SECRET')
        
        if not api_key or not api_secret:
            logger.warning("Không tìm thấy API key và secret trong biến môi trường")
            logger.info("Sử dụng cấu hình từ file account_config.json")
        else:
            logger.info("Đã tìm thấy API key và secret trong biến môi trường")
        
        # Khởi tạo API
        logger.info("Khởi tạo kết nối Binance API...")
        api = EnhancedBinanceAPI(testnet=True)
        
        # Kiểm tra kết nối
        logger.info("Kiểm tra kết nối...")
        if not api.test_connection():
            logger.error("Không thể kết nối tới Binance API")
            return False
        
        # Lấy số dư tài khoản
        logger.info("Lấy số dư tài khoản...")
        account_balance = api.get_account_balance()
        logger.info(f"Số dư tài khoản: {account_balance}")
        
        # Lấy giá BTCUSDT
        logger.info("Lấy giá BTCUSDT...")
        btc_price = api.get_symbol_price("BTCUSDT")
        
        if btc_price:
            logger.info(f"Giá BTC/USDT: ${btc_price:,.2f}")
        else:
            logger.error("Không thể lấy giá BTC/USDT")
            return False
        
        # Lấy thông tin thị trường tổng thể
        logger.info("Lấy thông tin thị trường tổng thể...")
        market_overview = api.get_market_overview()
        
        if market_overview:
            # Hiển thị top 5 coin
            logger.info("Top 5 coin theo volume:")
            for i, coin in enumerate(market_overview[:5], 1):
                symbol = coin.get('symbol', '')
                price = coin.get('price', 0)
                change = coin.get('price_change_24h', 0)
                volume = coin.get('volume_24h', 0)
                logger.info(f"{i}. {symbol}: ${price:,.2f} ({change:+.2f}%) - Volume: ${volume:,.2f}")
        else:
            logger.warning("Không thể lấy thông tin thị trường tổng thể")
        
        # Thử lấy dữ liệu K-lines
        logger.info("Lấy dữ liệu K-lines cho BTCUSDT (1h, 10 candles)...")
        klines = api.get_klines("BTCUSDT", "1h", limit=10)
        
        if klines:
            logger.info(f"Đã lấy {len(klines)} candles")
            
            # Hiển thị candle mới nhất
            latest_candle = klines[-1]
            open_time = datetime.fromtimestamp(latest_candle[0] / 1000)
            open_price = float(latest_candle[1])
            high_price = float(latest_candle[2])
            low_price = float(latest_candle[3])
            close_price = float(latest_candle[4])
            volume = float(latest_candle[5])
            
            logger.info(f"Candle mới nhất ({open_time}):")
            logger.info(f"  Open: ${open_price:,.2f}")
            logger.info(f"  High: ${high_price:,.2f}")
            logger.info(f"  Low: ${low_price:,.2f}")
            logger.info(f"  Close: ${close_price:,.2f}")
            logger.info(f"  Volume: {volume:,.2f}")
        else:
            logger.warning("Không thể lấy dữ liệu K-lines")
        
        logger.info("Kết nối thành công tới Binance API!")
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra kết nối: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Kiểm tra kết nối với Binance API')
    args = parser.parse_args()
    
    success = test_connection()
    
    if success:
        logger.info("Kiểm tra kết nối thành công")
        sys.exit(0)
    else:
        logger.error("Kiểm tra kết nối thất bại")
        sys.exit(1)

if __name__ == "__main__":
    main()