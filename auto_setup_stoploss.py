#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script thiết lập tự động Stop Loss/Take Profit cho các lệnh mới
Giải quyết vấn đề lệnh ETH được đặt mà không có SL/TP rõ ràng
"""

import logging
import time
import json
from datetime import datetime
import os

from binance_api import BinanceAPI

# Thiết lập logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('auto_setup_stoploss')

def load_risk_config(config_path='configs/risk_config.json'):
    """
    Tải cấu hình quản lý rủi ro
    
    Args:
        config_path (str): Đường dẫn đến file cấu hình
        
    Returns:
        dict: Cấu hình đã tải
    """
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình quản lý rủi ro: {str(e)}")
        return {
            'risk_level': 'medium',
            'default_stop_loss_percent': 5,
            'default_take_profit_percent': 10
        }

def setup_sl_tp_for_position(binance_api, position):
    """
    Thiết lập SL/TP cho một vị thế
    
    Args:
        binance_api (BinanceAPI): Đối tượng BinanceAPI
        position (dict): Thông tin vị thế
        
    Returns:
        tuple: (bool, str) - (Thành công hay không, Thông báo)
    """
    try:
        # Kiểm tra xem vị thế có tồn tại không
        if not position:
            return False, "Vị thế không tồn tại"
            
        # Lấy thông tin cần thiết
        symbol = position.get('symbol')
        side = 'LONG' if float(position.get('positionAmt', 0)) > 0 else 'SHORT'
        entry_price = float(position.get('entryPrice', 0))
        quantity = abs(float(position.get('positionAmt', 0)))
        
        if quantity <= 0 or entry_price <= 0:
            return False, f"Thông tin vị thế không hợp lệ: quantity={quantity}, entry_price={entry_price}"
            
        # Tải cấu hình rủi ro
        risk_config = load_risk_config()
        
        # Lấy % SL/TP theo cấu hình
        sl_percent = risk_config.get('default_stop_loss_percent', 5)
        tp_percent = risk_config.get('default_take_profit_percent', 10)
        
        # Tính giá SL/TP
        if side == 'LONG':
            sl_price = entry_price * (1 - sl_percent / 100)
            tp_price = entry_price * (1 + tp_percent / 100)
        else:  # SHORT
            sl_price = entry_price * (1 + sl_percent / 100)
            tp_price = entry_price * (1 - tp_percent / 100)
            
        # Kiểm tra xem đã có lệnh SL/TP cho vị thế này chưa
        orders = binance_api.get_open_orders(symbol)
        
        # Lọc các lệnh SL/TP
        sl_orders = [order for order in orders if order.get('type') in ['STOP', 'STOP_MARKET'] and order.get('symbol') == symbol]
        tp_orders = [order for order in orders if order.get('type') in ['TAKE_PROFIT', 'TAKE_PROFIT_MARKET'] and order.get('symbol') == symbol]
        
        logger.info(f"Vị thế {symbol}: Entry price={entry_price}, Side={side}")
        logger.info(f"  - Đã có {len(sl_orders)} lệnh SL và {len(tp_orders)} lệnh TP")
        
        # Tạo lệnh SL nếu chưa có
        if not sl_orders:
            logger.info(f"Thiết lập Stop Loss cho {symbol} tại giá {sl_price}")
            
            # Xác định side cho lệnh đóng
            close_side = 'SELL' if side == 'LONG' else 'BUY'
            
            # Tạo lệnh STOP_MARKET
            try:
                sl_order = binance_api.futures_create_order(
                    symbol=symbol,
                    side=close_side,
                    type='STOP_MARKET',
                    stopPrice=sl_price,
                    closePosition=True
                )
                logger.info(f"Đã đặt lệnh Stop Loss thành công: {sl_order.get('orderId')}")
            except Exception as e:
                logger.error(f"Lỗi khi đặt lệnh Stop Loss: {str(e)}")
        
        # Tạo lệnh TP nếu chưa có
        if not tp_orders:
            logger.info(f"Thiết lập Take Profit cho {symbol} tại giá {tp_price}")
            
            # Xác định side cho lệnh đóng
            close_side = 'SELL' if side == 'LONG' else 'BUY'
            
            # Tạo lệnh TAKE_PROFIT_MARKET
            try:
                tp_order = binance_api.futures_create_order(
                    symbol=symbol,
                    side=close_side,
                    type='TAKE_PROFIT_MARKET',
                    stopPrice=tp_price,
                    closePosition=True
                )
                logger.info(f"Đã đặt lệnh Take Profit thành công: {tp_order.get('orderId')}")
            except Exception as e:
                logger.error(f"Lỗi khi đặt lệnh Take Profit: {str(e)}")
                
        return True, "Đã thiết lập SL/TP cho vị thế"
    except Exception as e:
        logger.error(f"Lỗi khi thiết lập SL/TP: {str(e)}")
        return False, f"Lỗi: {str(e)}"

def check_and_setup_positions():
    """
    Kiểm tra và thiết lập SL/TP cho tất cả các vị thế đang mở
    """
    try:
        # Khởi tạo BinanceAPI
        binance_api = BinanceAPI()
        
        # Lấy vị thế đang mở
        positions = binance_api.get_open_positions()
        
        if not positions:
            logger.info("Không có vị thế nào đang mở")
            return
            
        # Đếm số vị thế đã được thiết lập SL/TP
        setup_count = 0
        
        # Kiểm tra từng vị thế và thiết lập SL/TP nếu cần
        for position in positions:
            symbol = position.get('symbol')
            position_size = float(position.get('positionAmt', 0))
            
            # Bỏ qua vị thế không có số lượng
            if position_size == 0:
                continue
                
            logger.info(f"Kiểm tra vị thế {symbol} với số lượng {position_size}")
            
            # Thiết lập SL/TP
            success, message = setup_sl_tp_for_position(binance_api, position)
            
            if success:
                setup_count += 1
                logger.info(f"Đã thiết lập SL/TP cho {symbol}: {message}")
            else:
                logger.warning(f"Không thể thiết lập SL/TP cho {symbol}: {message}")
                
        logger.info(f"Đã thiết lập SL/TP cho {setup_count}/{len(positions)} vị thế")
            
    except Exception as e:
        logger.error(f"Lỗi trong quá trình kiểm tra và thiết lập SL/TP: {str(e)}")

if __name__ == "__main__":
    logger.info("Bắt đầu kiểm tra và thiết lập SL/TP cho các vị thế")
    check_and_setup_positions()