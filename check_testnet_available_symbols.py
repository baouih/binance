#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script để kiểm tra các cặp tiền có sẵn trên Binance Futures Testnet
và lưu kết quả để tham khảo trong tương lai
"""

import os
import sys
import json
import time
import logging
import requests
from typing import List, Dict, Any

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("testnet_symbols.log")
    ]
)
logger = logging.getLogger("check_testnet_symbols")

# Các symbols mục tiêu của hệ thống
TARGET_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT",
    "DOGEUSDT", "MATICUSDT", "LTCUSDT", "DOTUSDT", "XRPUSDT",
    "AVAXUSDT", "LINKUSDT", "ATOMUSDT"
]

def get_server_time() -> int:
    """Lấy thời gian server Binance"""
    try:
        url = "https://testnet.binancefuture.com/fapi/v1/time"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get('serverTime', int(time.time() * 1000))
    except Exception as e:
        logger.error(f"Lỗi khi lấy thời gian server: {str(e)}")
    
    return int(time.time() * 1000)

def get_exchange_info() -> Dict:
    """Lấy thông tin tất cả các cặp giao dịch trên Binance Futures Testnet"""
    url = "https://testnet.binancefuture.com/fapi/v1/exchangeInfo"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Lỗi khi lấy exchange info: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Lỗi không mong đợi: {str(e)}")
    
    return {}

def get_ticker_prices() -> List[Dict]:
    """Lấy giá hiện tại của tất cả các cặp giao dịch"""
    url = "https://testnet.binancefuture.com/fapi/v1/ticker/price"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Lỗi khi lấy ticker prices: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Lỗi không mong đợi: {str(e)}")
    
    return []

def check_single_ticker(symbol: str) -> Dict:
    """Kiểm tra giá của một cặp cụ thể"""
    url = f"https://testnet.binancefuture.com/fapi/v1/ticker/price?symbol={symbol}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Lỗi khi lấy ticker {symbol}: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Lỗi không mong đợi: {str(e)}")
    
    return {}

def main():
    """Hàm chính để kiểm tra các symbols có sẵn trên Testnet"""
    logger.info("Bắt đầu kiểm tra các symbols trên Binance Futures Testnet")
    
    # Lấy thông tin exchange
    exchange_info = get_exchange_info()
    
    if not exchange_info or 'symbols' not in exchange_info:
        logger.error("Không lấy được thông tin exchange")
        return
    
    # Lọc các symbols đang giao dịch
    trading_symbols = []
    for symbol_info in exchange_info['symbols']:
        symbol = symbol_info.get('symbol')
        status = symbol_info.get('status')
        
        if status == 'TRADING':
            trading_symbols.append(symbol)
    
    logger.info(f"Có {len(trading_symbols)} cặp đang giao dịch trên Testnet")
    
    # Lấy giá của tất cả các cặp
    ticker_prices = get_ticker_prices()
    price_data = {}
    
    if ticker_prices:
        for ticker in ticker_prices:
            symbol = ticker.get('symbol')
            price = ticker.get('price')
            if symbol and price:
                price_data[symbol] = float(price)
        
        logger.info(f"Đã lấy giá của {len(price_data)} cặp")
    else:
        logger.error("Không lấy được giá của các cặp")
    
    # Kiểm tra các symbols mục tiêu
    available_symbols = []
    unavailable_symbols = []
    
    for symbol in TARGET_SYMBOLS:
        if symbol in trading_symbols and symbol in price_data:
            available_symbols.append({
                'symbol': symbol,
                'price': price_data[symbol],
                'status': 'available'
            })
        else:
            # Thử kiểm tra trực tiếp
            ticker = check_single_ticker(symbol)
            if ticker and 'price' in ticker:
                available_symbols.append({
                    'symbol': symbol,
                    'price': float(ticker['price']),
                    'status': 'available'
                })
            else:
                unavailable_symbols.append({
                    'symbol': symbol,
                    'status': 'unavailable',
                    'reason': 'Not found or not trading'
                })
    
    # Hiển thị kết quả
    logger.info(f"=== KIỂM TRA {len(TARGET_SYMBOLS)} SYMBOLS MỤC TIÊU ===")
    logger.info(f"Có sẵn: {len(available_symbols)}")
    for s in available_symbols:
        logger.info(f"✅ {s['symbol']}: {s['price']}")
    
    logger.info(f"Không có sẵn: {len(unavailable_symbols)}")
    for s in unavailable_symbols:
        logger.info(f"❌ {s['symbol']}: {s['reason']}")
    
    # Lưu kết quả ra file
    result = {
        'timestamp': get_server_time(),
        'available_symbols': available_symbols,
        'unavailable_symbols': unavailable_symbols
    }
    
    with open('testnet_available_symbols.json', 'w') as f:
        json.dump(result, f, indent=2)
        logger.info("Đã lưu kết quả vào testnet_available_symbols.json")

if __name__ == "__main__":
    main()