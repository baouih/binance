#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script kích hoạt giao dịch cho tất cả các cặp tiền đã cấu hình
Giải quyết vấn đề chỉ BTC và ETH được giao dịch
"""

import logging
import time
import json
from datetime import datetime
import os

from binance_api import BinanceAPI
from account_type_selector import AccountTypeSelector

# Thiết lập logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('activate_all_symbols')

def load_bot_config(config_path='bot_config.json'):
    """
    Tải cấu hình bot
    
    Args:
        config_path (str): Đường dẫn đến file cấu hình
        
    Returns:
        dict: Cấu hình đã tải
    """
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình bot: {str(e)}")
        return {}

def update_account_config(enabled_symbols):
    """
    Cập nhật danh sách các cặp tiền được giao dịch
    
    Args:
        enabled_symbols (list): Danh sách các cặp tiền được kích hoạt
        
    Returns:
        bool: True nếu cập nhật thành công, False nếu không
    """
    try:
        # Sử dụng AccountTypeSelector để cập nhật cấu hình
        selector = AccountTypeSelector()
        
        # Cập nhật danh sách symbols
        result = selector.set_symbols(enabled_symbols)
        
        if result:
            logger.info(f"Đã cập nhật danh sách symbols: {enabled_symbols}")
        else:
            logger.error("Không thể cập nhật danh sách symbols")
            
        return result
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật account config: {str(e)}")
        return False

def get_tradable_symbols(binance_api):
    """
    Lấy danh sách các cặp tiền có thể giao dịch trên Binance
    
    Args:
        binance_api (BinanceAPI): Đối tượng BinanceAPI
        
    Returns:
        list: Danh sách các cặp tiền
    """
    try:
        # Lấy thông tin thị trường (sử dụng phương thức phù hợp)
        exchange_info = binance_api.get_exchange_info()
        
        # Lọc các cặp tiền kết thúc bằng USDT và đang hoạt động
        symbols = [
            symbol['symbol'] for symbol in exchange_info.get('symbols', [])
            if symbol['symbol'].endswith('USDT') and symbol['status'] == 'TRADING'
        ]
        
        return symbols
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách symbols: {str(e)}")
        return []

def get_recommended_symbols():
    """
    Lấy danh sách các cặp tiền được đề xuất giao dịch
    
    Returns:
        list: Danh sách các cặp tiền đề xuất
    """
    # Danh sách cố định các cặp tiền phổ biến
    return [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT', 
        'DOGEUSDT', 'DOTUSDT', 'AVAXUSDT', 'MATICUSDT', 'XRPUSDT',
        'LINKUSDT', 'ATOMUSDT', 'NEARUSDT'
    ]

def check_and_enable_all_symbols():
    """
    Kiểm tra và kích hoạt tất cả các cặp tiền đã cấu hình
    """
    try:
        # Khởi tạo BinanceAPI
        binance_api = BinanceAPI()
        
        # Lấy cấu hình hiện tại
        selector = AccountTypeSelector()
        current_config = selector.get_current_config()
        current_symbols = current_config.get('symbols', [])
        
        logger.info(f"Danh sách symbols hiện tại: {current_symbols}")
        
        # Lấy danh sách các cặp tiền đề xuất
        recommended_symbols = get_recommended_symbols()
        
        # Lấy danh sách các cặp tiền có thể giao dịch trên Binance
        tradable_symbols = get_tradable_symbols(binance_api)
        
        # Kết hợp và lọc các cặp tiền
        enabled_symbols = list(set(current_symbols + recommended_symbols))
        
        # Đảm bảo tất cả đều có thể giao dịch được
        enabled_symbols = [symbol for symbol in enabled_symbols if symbol in tradable_symbols]
        
        # Cập nhật cấu hình
        if update_account_config(enabled_symbols):
            logger.info(f"Đã kích hoạt {len(enabled_symbols)} cặp tiền: {enabled_symbols}")
        else:
            logger.error("Không thể kích hoạt các cặp tiền")
            
    except Exception as e:
        logger.error(f"Lỗi trong quá trình kích hoạt các cặp tiền: {str(e)}")

if __name__ == "__main__":
    logger.info("Bắt đầu kích hoạt tất cả các cặp tiền đã cấu hình")
    check_and_enable_all_symbols()