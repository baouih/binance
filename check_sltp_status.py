#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script kiểm tra trạng thái Stop Loss và Take Profit cho các vị thế hiện tại

Script này kiểm tra và hiển thị:
1. Các vị thế đang mở
2. Các lệnh Stop Loss / Take Profit đang có
3. Kiểm tra xem SL/TP có hiển thị trên giao diện Binance hay không
4. Xác nhận các lệnh có sử dụng tham số closePosition=true không
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('check_sltp_status')

# Thêm thư mục gốc vào sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Import các module cần thiết
from binance_api import BinanceAPI

def get_open_orders(api, symbol=None):
    """Lấy danh sách các lệnh đang mở"""
    try:
        if symbol:
            orders = api.get_open_orders(symbol)
        else:
            # Nếu không chỉ định symbol, lấy tất cả các lệnh
            orders = api.get_open_orders()
        
        return orders
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách lệnh: {str(e)}")
        return []

def get_positions(api):
    """Lấy danh sách các vị thế đang mở"""
    try:
        positions = api.get_futures_position_risk()
        # Lọc các vị thế có số lượng != 0
        active_positions = [p for p in positions if float(p.get('positionAmt', 0)) != 0]
        return active_positions
    except Exception as e:
        logger.error(f"Lỗi khi lấy vị thế: {str(e)}")
        return []

def classify_orders(orders):
    """Phân loại các loại lệnh SL/TP"""
    sl_orders = [o for o in orders if o.get('type') in ['STOP_MARKET', 'STOP']]
    tp_orders = [o for o in orders if o.get('type') in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT']]
    
    return sl_orders, tp_orders

def check_order_close_position(order):
    """Kiểm tra xem lệnh có sử dụng tham số closePosition không"""
    return 'closePosition' in order and order['closePosition'] == True

def main():
    """Hàm chính"""
    try:
        # Khởi tạo Binance API
        api = BinanceAPI()
        
        # Lấy các vị thế đang mở
        positions = get_positions(api)
        logger.info(f"Đã tìm thấy {len(positions)} vị thế đang mở")
        
        if not positions:
            logger.info("Không có vị thế nào đang mở.")
            return
        
        # Lấy tất cả các lệnh đang mở
        all_orders = get_open_orders(api)
        
        # Hiển thị thông tin chi tiết cho từng vị thế
        for position in positions:
            symbol = position['symbol']
            position_amt = float(position['positionAmt'])
            entry_price = float(position['entryPrice'])
            side = 'LONG' if position_amt > 0 else 'SHORT'
            
            logger.info(f"\n==== Vị thế {symbol} ====")
            logger.info(f"Side: {side}")
            logger.info(f"Entry Price: {entry_price}")
            logger.info(f"Position Amount: {abs(position_amt)}")
            
            # Lọc các lệnh của symbol này
            symbol_orders = [o for o in all_orders if o['symbol'] == symbol]
            sl_orders, tp_orders = classify_orders(symbol_orders)
            
            # Kiểm tra và hiển thị SL
            logger.info(f"\nStop Loss orders ({len(sl_orders)}):")
            if sl_orders:
                for i, order in enumerate(sl_orders):
                    order_id = order.get('orderId')
                    stop_price = float(order.get('stopPrice', 0))
                    uses_close_position = check_order_close_position(order)
                    
                    logger.info(f"SL #{i+1} - ID: {order_id}")
                    logger.info(f"  Price: {stop_price}")
                    logger.info(f"  Uses closePosition: {uses_close_position}")
                    logger.info(f"  Visible on Binance UI: {uses_close_position}")
            else:
                logger.warning("  Không có lệnh Stop Loss nào!")
            
            # Kiểm tra và hiển thị TP
            logger.info(f"\nTake Profit orders ({len(tp_orders)}):")
            if tp_orders:
                for i, order in enumerate(tp_orders):
                    order_id = order.get('orderId')
                    stop_price = float(order.get('stopPrice', 0))
                    uses_close_position = check_order_close_position(order)
                    
                    logger.info(f"TP #{i+1} - ID: {order_id}")
                    logger.info(f"  Price: {stop_price}")
                    logger.info(f"  Uses closePosition: {uses_close_position}")
                    logger.info(f"  Visible on Binance UI: {uses_close_position}")
            else:
                logger.warning("  Không có lệnh Take Profit nào!")
        
        # Kiểm tra nếu có vị thế không có SL/TP
        for position in positions:
            symbol = position['symbol']
            symbol_orders = [o for o in all_orders if o['symbol'] == symbol]
            sl_orders, tp_orders = classify_orders(symbol_orders)
            
            if not sl_orders:
                logger.warning(f"\n⚠️ CẢNH BÁO: {symbol} không có Stop Loss!")
            if not tp_orders:
                logger.warning(f"\n⚠️ CẢNH BÁO: {symbol} không có Take Profit!")
        
    except Exception as e:
        logger.error(f"Lỗi: {str(e)}")

if __name__ == "__main__":
    main()