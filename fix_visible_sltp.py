#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script sửa lỗi SL/TP không hiển thị trên giao diện Binance

Script này:
1. Kiểm tra tất cả các vị thế đang mở
2. Xác định xem lệnh SL/TP có sử dụng closePosition=True hay không
3. Hủy các lệnh cũ và tạo lệnh mới với closePosition=True
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
        logging.StreamHandler(),
        logging.FileHandler("fix_sltp_visibility.log")
    ]
)

logger = logging.getLogger('fix_visible_sltp')

# Thêm thư mục gốc vào sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Import các module cần thiết
from binance_api import BinanceAPI

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

def classify_orders(orders):
    """Phân loại các loại lệnh SL/TP"""
    sl_orders = [o for o in orders if o.get('type') in ['STOP_MARKET', 'STOP']]
    tp_orders = [o for o in orders if o.get('type') in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT']]
    
    return sl_orders, tp_orders

def check_order_close_position(order):
    """Kiểm tra xem lệnh có sử dụng tham số closePosition không"""
    return 'closePosition' in order and order['closePosition'] == True

def fix_symbol_orders(api, symbol, side, position_amt):
    """Sửa các lệnh SL/TP cho một symbol
    
    Args:
        api: Đối tượng BinanceAPI
        symbol: Symbol cần sửa
        side: Phía vị thế (LONG/SHORT)
        position_amt: Lượng vị thế
    
    Returns:
        bool: True nếu sửa thành công
    """
    try:
        # Lấy danh sách lệnh của symbol
        orders = get_open_orders(api, symbol)
        sl_orders, tp_orders = classify_orders(orders)
        
        # Kiểm tra xem có lệnh SL/TP không
        if not sl_orders and not tp_orders:
            logger.warning(f"{symbol} không có lệnh SL/TP nào, tạo mới!")
            # Tính SL/TP dựa trên giá hiện tại thay vì hủy/tạo lại
            try:
                # Lấy thông tin vị thế để biết entry price
                positions = get_positions(api)
                position = next((p for p in positions if p['symbol'] == symbol), None)
                if not position:
                    logger.warning(f"Không tìm thấy thông tin vị thế {symbol}")
                    return False
                
                entry_price = float(position['entryPrice'])
                
                # Tính toán mức SL/TP mặc định (2% SL, 3% TP)
                sl_percent = 2.0
                tp_percent = 3.0
                
                if side == 'LONG':
                    sl_price = round(entry_price * (1 - sl_percent/100), 2)
                    tp_price = round(entry_price * (1 + tp_percent/100), 2)
                else:  # SHORT
                    sl_price = round(entry_price * (1 + sl_percent/100), 2)
                    tp_price = round(entry_price * (1 - tp_percent/100), 2)
                
                # Tạo lệnh mới
                close_side = 'SELL' if side == 'LONG' else 'BUY'
                
                # Tạo lệnh SL
                try:
                    new_sl = api.futures_create_order(
                        symbol=symbol,
                        side=close_side,
                        type='STOP_MARKET',
                        stopPrice=sl_price,
                        closePosition='true'  # Sử dụng chuỗi thay vì boolean
                    )
                    logger.info(f"Đã tạo lệnh SL mới cho {symbol} tại giá {sl_price} với closePosition=True")
                    time.sleep(0.5)
                except Exception as e:
                    logger.error(f"Lỗi khi tạo lệnh SL mới cho {symbol}: {str(e)}")
                
                # Tạo lệnh TP
                try:
                    new_tp = api.futures_create_order(
                        symbol=symbol,
                        side=close_side,
                        type='TAKE_PROFIT_MARKET',
                        stopPrice=tp_price,
                        closePosition='true'  # Sử dụng chuỗi thay vì boolean
                    )
                    logger.info(f"Đã tạo lệnh TP mới cho {symbol} tại giá {tp_price} với closePosition=True")
                    time.sleep(0.5)
                except Exception as e:
                    logger.error(f"Lỗi khi tạo lệnh TP mới cho {symbol}: {str(e)}")
                
                return True
            except Exception as e:
                logger.error(f"Lỗi khi tạo SL/TP mới cho {symbol}: {str(e)}")
                return False
        
        # Kiểm tra xem các lệnh có sử dụng closePosition không
        all_use_close_position = True
        for order in sl_orders + tp_orders:
            if not check_order_close_position(order):
                all_use_close_position = False
                break
        
        # Nếu tất cả các lệnh đã sử dụng closePosition, không cần sửa
        if all_use_close_position:
            logger.info(f"{symbol} đã sử dụng closePosition cho tất cả các lệnh, không cần sửa")
            return True
        
        # Lưu thông tin lệnh cũ
        sl_prices = set()
        tp_prices = set()
        
        for order in sl_orders:
            sl_prices.add(float(order.get('stopPrice', 0)))
        
        for order in tp_orders:
            tp_prices.add(float(order.get('stopPrice', 0)))
        
        # Hủy tất cả lệnh cũ qua API cancel_all_open_orders
        try:
            logger.info(f"Hủy tất cả lệnh đang mở cho {symbol}")
            api.futures_cancel_all_orders(symbol=symbol)
            logger.info(f"Đã hủy tất cả lệnh cho {symbol}")
            time.sleep(1.0)  # Chờ lâu hơn để đảm bảo lệnh được hủy
        except Exception as e:
            logger.error(f"Lỗi khi hủy lệnh cho {symbol}: {str(e)}")
        
        # Tạo lệnh mới với closePosition=True
        close_side = 'SELL' if side == 'LONG' else 'BUY'
        
        # Tạo lại các lệnh SL
        for sl_price in sl_prices:
            try:
                new_sl = api.futures_create_order(
                    symbol=symbol,
                    side=close_side,
                    type='STOP_MARKET',
                    stopPrice=sl_price,
                    closePosition='true'  # Sử dụng chuỗi thay vì boolean
                )
                logger.info(f"Đã tạo lại lệnh SL cho {symbol} tại giá {sl_price} với closePosition=True")
                time.sleep(0.5)  # Chờ để đảm bảo lệnh được tạo
            except Exception as e:
                logger.error(f"Lỗi khi tạo lại lệnh SL cho {symbol}: {str(e)}")
        
        # Tạo lại các lệnh TP
        for tp_price in tp_prices:
            try:
                new_tp = api.futures_create_order(
                    symbol=symbol,
                    side=close_side,
                    type='TAKE_PROFIT_MARKET',
                    stopPrice=tp_price,
                    closePosition=True
                )
                logger.info(f"Đã tạo lại lệnh TP cho {symbol} tại giá {tp_price} với closePosition=True")
                time.sleep(0.5)  # Chờ để đảm bảo lệnh được tạo
            except Exception as e:
                logger.error(f"Lỗi khi tạo lại lệnh TP cho {symbol}: {str(e)}")
        
        return True
    except Exception as e:
        logger.error(f"Lỗi khi sửa lệnh cho {symbol}: {str(e)}")
        return False

def main():
    """Hàm chính"""
    try:
        logger.info("===== BẮT ĐẦU SỬA LỆNH SL/TP KHÔNG HIỂN THỊ =====")
        
        # Khởi tạo Binance API
        api = BinanceAPI()
        
        # Lấy các vị thế đang mở
        positions = get_positions(api)
        logger.info(f"Đã tìm thấy {len(positions)} vị thế đang mở")
        
        if not positions:
            logger.info("Không có vị thế nào đang mở.")
            return
        
        # Sửa lệnh cho từng vị thế
        fixed_count = 0
        for position in positions:
            symbol = position['symbol']
            position_amt = float(position['positionAmt'])
            side = 'LONG' if position_amt > 0 else 'SHORT'
            
            logger.info(f"\n==== Đang sửa lệnh cho vị thế {symbol} {side} ====")
            
            if fix_symbol_orders(api, symbol, side, abs(position_amt)):
                fixed_count += 1
        
        logger.info(f"\n===== KẾT THÚC: Đã sửa {fixed_count}/{len(positions)} vị thế =====")
        
    except Exception as e:
        logger.error(f"Lỗi: {str(e)}")

if __name__ == "__main__":
    main()