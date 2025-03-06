#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script để đóng vị thế BTC một cách chủ động
Dùng để giải quyết vấn đề vị thế BTC không chốt lời sau thời gian dài
"""

import logging
import time
import json
from datetime import datetime
import os

from binance_api import BinanceAPI
from position_manager import PositionManager
from profit_manager import ProfitManager
from advanced_trailing_stop import AdvancedTrailingStop

# Thiết lập logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('force_close_btc')

def load_profit_config(config_path='configs/profit_manager_config.json'):
    """
    Tải cấu hình profit manager
    
    Args:
        config_path (str): Đường dẫn đến file cấu hình
        
    Returns:
        dict: Cấu hình đã tải
    """
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình profit manager: {str(e)}")
        return {}

def load_trailing_config(config_path='configs/trailing_stop_config.json'):
    """
    Tải cấu hình trailing stop
    
    Args:
        config_path (str): Đường dẫn đến file cấu hình
        
    Returns:
        dict: Cấu hình đã tải
    """
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình trailing stop: {str(e)}")
        # Cấu hình mặc định
        return {
            'strategy_type': 'percentage',
            'config': {
                'activation_percent': 0.8,
                'callback_percent': 0.3
            }
        }

def close_position(binance_api, position_id):
    """
    Đóng vị thế theo ID
    
    Args:
        binance_api (BinanceAPI): Đối tượng BinanceAPI
        position_id (str): ID vị thế cần đóng
        
    Returns:
        bool: True nếu đóng thành công, False nếu không
    """
    try:
        # Lấy thông tin vị thế
        positions = binance_api.get_open_positions()
        
        if not positions:
            logger.warning("Không có vị thế nào đang mở")
            return False
            
        # Tìm vị thế cần đóng
        position = None
        for pos in positions:
            if pos.get('symbol') == 'BTCUSDT':
                position = pos
                break
                
        if not position:
            logger.warning("Không tìm thấy vị thế BTC nào")
            return False
            
        # Lấy thông tin cần thiết
        symbol = position.get('symbol')
        side = 'SELL' if position.get('positionSide', 'BOTH') == 'LONG' or float(position.get('positionAmt', 0)) > 0 else 'BUY'
        quantity = abs(float(position.get('positionAmt', 0)))
        
        if quantity <= 0:
            logger.warning(f"Số lượng không hợp lệ: {quantity}")
            return False
            
        # Tạo lệnh đóng vị thế
        logger.info(f"Đóng vị thế {symbol} với side={side}, quantity={quantity}")
        
        # Đóng bằng lệnh MARKET
        order = binance_api.futures_create_order(
            symbol=symbol,
            side=side,
            type='MARKET',
            quantity=quantity,
            reduceOnly=True
        )
        
        logger.info(f"Đã đóng vị thế thành công: {order}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi đóng vị thế: {str(e)}")
        return False

def check_position_and_close_if_needed():
    """
    Kiểm tra vị thế BTC và đóng nếu cần thiết
    """
    try:
        # Khởi tạo BinanceAPI
        binance_api = BinanceAPI()
        
        # Lấy vị thế đang mở
        positions = binance_api.get_open_positions()
        
        if not positions:
            logger.info("Không có vị thế nào đang mở")
            return
            
        # Lọc ra vị thế BTC
        btc_positions = [pos for pos in positions if pos.get('symbol') == 'BTCUSDT']
        
        if not btc_positions:
            logger.info("Không có vị thế BTC nào đang mở")
            return
            
        btc_position = btc_positions[0]
        
        # Chuyển đổi định dạng dữ liệu
        position = {
            'id': 'btc_position',
            'symbol': btc_position.get('symbol'),
            'side': 'LONG' if float(btc_position.get('positionAmt', 0)) > 0 else 'SHORT',
            'entry_price': float(btc_position.get('entryPrice', 0)),
            'quantity': abs(float(btc_position.get('positionAmt', 0))),
            'leverage': int(btc_position.get('leverage', 1))
        }
        
        # Kiểm tra thời gian vào lệnh
        if 'entryTime' in btc_position:
            entry_time = datetime.fromtimestamp(int(btc_position.get('entryTime', 0)) / 1000)
            position['entry_time'] = entry_time
        else:
            # Nếu không có entryTime, sử dụng thời gian hiện tại - 24 giờ
            entry_time = datetime.now()
            position['entry_time'] = entry_time
            
        # Thêm thông tin price
        current_price = float(binance_api.get_symbol_ticker('BTCUSDT').get('price', 0))
        position['current_price'] = current_price
        
        # Tính toán lợi nhuận
        if position['side'] == 'LONG':
            profit_pct = (current_price - position['entry_price']) / position['entry_price'] * 100 * position['leverage']
        else:
            profit_pct = (position['entry_price'] - current_price) / position['entry_price'] * 100 * position['leverage']
            
        position['profit_percentage'] = profit_pct
        
        # Log thông tin vị thế
        logger.info(f"Thông tin vị thế BTC: Entry price={position['entry_price']}, Current price={current_price}, "
                   f"P/L={profit_pct:.2f}%, Side={position['side']}")
        
        # Kiểm tra điều kiện đóng vị thế
        should_close = False
        reason = ""
        
        # 1. Lợi nhuận > 1%
        if profit_pct >= 1.0:
            should_close = True
            reason = f"Lợi nhuận đạt {profit_pct:.2f}% > 1%, đóng vị thế"
            
        # 2. Đã giữ vị thế quá lâu (>12 giờ)
        current_time = datetime.now()
        hold_duration = (current_time - position['entry_time']).total_seconds() / 3600  # giờ
        
        if hold_duration >= 12:
            should_close = True
            reason = f"Đã giữ vị thế {hold_duration:.2f} giờ > 12 giờ, đóng vị thế"
            
        # 3. Lỗ quá 2%
        if profit_pct <= -2.0:
            should_close = True
            reason = f"Lỗ {profit_pct:.2f}% < -2%, đóng vị thế để cắt lỗ"
            
        # Kiểm tra và đóng vị thế nếu cần
        if should_close:
            logger.info(f"Cần đóng vị thế BTC: {reason}")
            if close_position(binance_api, 'btc_position'):
                logger.info("Đã đóng vị thế BTC thành công")
            else:
                logger.error("Không thể đóng vị thế BTC")
        else:
            logger.info("Chưa cần đóng vị thế BTC")
            
    except Exception as e:
        logger.error(f"Lỗi trong quá trình kiểm tra và đóng vị thế: {str(e)}")

if __name__ == "__main__":
    logger.info("Bắt đầu kiểm tra và đóng vị thế BTC nếu cần")
    check_position_and_close_if_needed()