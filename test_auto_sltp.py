#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kiểm tra hoạt động của hệ thống tự động cập nhật Stop Loss và Take Profit
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_auto_sltp')

# Thêm thư mục gốc vào sys.path để import các module
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from binance_api import BinanceAPI
from binance_api_fixes import apply_fixes_to_api

def test_get_active_positions(api):
    """Kiểm tra lấy các vị thế đang hoạt động trên tài khoản testnet"""
    try:
        logger.info("Đang lấy vị thế hiện tại...")
        positions = api.get_futures_position_risk()
        active_positions = [p for p in positions if abs(float(p.get('positionAmt', 0))) > 0]
        
        logger.info(f"Đã tìm thấy {len(active_positions)} vị thế đang mở")
        
        for pos in active_positions:
            symbol = pos.get('symbol')
            pos_amt = float(pos.get('positionAmt', 0))
            entry_price = float(pos.get('entryPrice', 0))
            mark_price = float(pos.get('markPrice', 0))
            unrealized_profit = float(pos.get('unRealizedProfit', 0))
            side = 'LONG' if pos_amt > 0 else 'SHORT'
            
            logger.info(f"Vị thế: {symbol} {side}, Entry: {entry_price}, Mark: {mark_price}, PnL: {unrealized_profit}")
        
        return active_positions
    except Exception as e:
        logger.error(f"Lỗi khi lấy vị thế: {str(e)}")
        return []

def test_get_stop_loss_orders(api, symbol):
    """Kiểm tra lấy các lệnh stop loss của một cặp giao dịch"""
    try:
        logger.info(f"Đang lấy các lệnh SL/TP cho {symbol}...")
        orders = api.get_open_orders(symbol)
        
        # Phân loại các loại lệnh
        sl_orders = [o for o in orders if o.get('type') in ['STOP_MARKET', 'STOP']]
        tp_orders = [o for o in orders if o.get('type') in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT']]
        
        logger.info(f"Đã tìm thấy {len(sl_orders)} lệnh SL và {len(tp_orders)} lệnh TP cho {symbol}")
        
        for sl in sl_orders:
            order_id = sl.get('orderId')
            stop_price = float(sl.get('stopPrice', 0))
            side = sl.get('side')
            
            logger.info(f"Lệnh SL #{order_id}: Giá kích hoạt = {stop_price}, Side = {side}")
        
        for tp in tp_orders:
            order_id = tp.get('orderId')
            stop_price = float(tp.get('stopPrice', 0))
            side = tp.get('side')
            
            logger.info(f"Lệnh TP #{order_id}: Giá kích hoạt = {stop_price}, Side = {side}")
            
        return sl_orders, tp_orders
    except Exception as e:
        logger.error(f"Lỗi khi lấy lệnh SL/TP: {str(e)}")
        return [], []

def test_auto_setup_stoploss(api):
    """Kiểm tra chức năng tự động thiết lập Stop Loss"""
    try:
        # Thực hiện quét tất cả vị thế và cập nhật SL/TP
        logger.info("Chạy auto_setup_stoploss.py...")
        
        from auto_setup_stoploss import check_and_setup_positions
        check_and_setup_positions()
        
        return True
    except Exception as e:
        logger.error(f"Lỗi khi chạy auto_setup_stoploss: {str(e)}")
        return False

def test_auto_setup_sltp(api):
    """Kiểm tra chức năng tự động thiết lập SL/TP"""
    try:
        logger.info("Chạy auto_setup_sltp.py...")
        
        # Import và chạy hàm từ module
        import importlib.util
        spec = importlib.util.spec_from_file_location("auto_setup_sltp", "auto_setup_sltp.py")
        sltp_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sltp_module)
        
        # Chạy hàm setup_sltp_for_positions từ module đã import
        sltp_module.setup_sltp_for_positions(testnet=True, force_check=True)
        
        return True
    except Exception as e:
        logger.error(f"Lỗi khi chạy auto_setup_sltp: {str(e)}")
        return False

def test_cancel_sl_tp_orders(api, symbol):
    """Kiểm tra hủy các lệnh SL/TP để có thể tạo mới"""
    try:
        logger.info(f"Đang hủy tất cả lệnh SL/TP cho {symbol}...")
        orders = api.get_open_orders(symbol)
        
        # Lọc lệnh SL/TP
        sl_tp_orders = [o for o in orders if o.get('type') in ['STOP_MARKET', 'STOP', 'TAKE_PROFIT_MARKET', 'TAKE_PROFIT']]
        
        for order in sl_tp_orders:
            order_id = order.get('orderId')
            order_type = order.get('type')
            
            try:
                result = api.cancel_order(symbol=symbol, order_id=order_id)
                logger.info(f"Đã hủy lệnh {order_type} #{order_id} cho {symbol}")
            except Exception as e:
                logger.error(f"Lỗi khi hủy lệnh #{order_id}: {str(e)}")
                
        # Kiểm tra lại sau khi hủy
        remaining_orders = api.get_open_orders(symbol)
        sl_tp_remaining = [o for o in remaining_orders if o.get('type') in ['STOP_MARKET', 'STOP', 'TAKE_PROFIT_MARKET', 'TAKE_PROFIT']]
        
        if len(sl_tp_remaining) == 0:
            logger.info(f"Đã hủy thành công tất cả lệnh SL/TP cho {symbol}")
            return True
        else:
            logger.warning(f"Vẫn còn {len(sl_tp_remaining)} lệnh SL/TP cho {symbol}")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi hủy lệnh SL/TP: {str(e)}")
        return False

def test_set_manual_sl_tp(api, symbol, side, entry_price, current_price):
    """Thiết lập thủ công SL/TP để kiểm tra"""
    try:
        logger.info(f"Đang thiết lập thủ công SL/TP cho {symbol}...")
        
        # Tính toán giá SL/TP đơn giản
        sl_percent = 2.0  # 2%
        tp_percent = 3.0  # 3%
        
        if side == 'LONG':
            sl_price = entry_price * (1 - sl_percent / 100)
            tp_price = entry_price * (1 + tp_percent / 100)
            close_side = 'SELL'
        else:  # SHORT
            sl_price = entry_price * (1 + sl_percent / 100)
            tp_price = entry_price * (1 - tp_percent / 100)
            close_side = 'BUY'
            
        # Đặt lệnh SL
        try:
            sl_order = api.futures_create_order(
                symbol=symbol,
                side=close_side,
                type='STOP_MARKET',
                stopPrice=sl_price,
                closePosition=True
            )
            logger.info(f"Đã đặt lệnh SL cho {symbol} tại giá {sl_price}")
        except Exception as e:
            logger.error(f"Lỗi khi đặt SL: {str(e)}")
            
        # Đặt lệnh TP
        try:
            tp_order = api.futures_create_order(
                symbol=symbol,
                side=close_side,
                type='TAKE_PROFIT_MARKET',
                stopPrice=tp_price,
                closePosition=True
            )
            logger.info(f"Đã đặt lệnh TP cho {symbol} tại giá {tp_price}")
        except Exception as e:
            logger.error(f"Lỗi khi đặt TP: {str(e)}")
            
        return True
    except Exception as e:
        logger.error(f"Lỗi khi thiết lập thủ công SL/TP: {str(e)}")
        return False

def main():
    """Hàm chính cho quá trình kiểm tra"""
    logger.info("=== BẮT ĐẦU KIỂM TRA TỰ ĐỘNG ĐIỀU CHỈNH SL/TP ===")
    
    # Khởi tạo API Binance
    api = BinanceAPI()
    api = apply_fixes_to_api(api)
    
    # 1. Kiểm tra vị thế hiện tại
    active_positions = test_get_active_positions(api)
    
    if not active_positions:
        logger.warning("Không có vị thế nào đang mở, không thể tiếp tục kiểm tra!")
        return
        
    # 2. Chọn vị thế đầu tiên để kiểm tra
    test_position = active_positions[0]
    symbol = test_position.get('symbol')
    pos_amt = float(test_position.get('positionAmt', 0))
    entry_price = float(test_position.get('entryPrice', 0))
    mark_price = float(test_position.get('markPrice', 0))
    side = 'LONG' if pos_amt > 0 else 'SHORT'
    
    logger.info(f"Chọn vị thế {symbol} {side} để kiểm tra: Entry={entry_price}, Mark={mark_price}")
    
    # 3. Kiểm tra các lệnh SL/TP hiện tại
    sl_orders, tp_orders = test_get_stop_loss_orders(api, symbol)
    
    # 4. Hủy các lệnh SL/TP để có thể tạo mới nếu cần
    if len(sl_orders) > 0 or len(tp_orders) > 0:
        logger.info(f"Hủy lệnh SL/TP hiện có cho {symbol} để kiểm tra tạo mới...")
        test_cancel_sl_tp_orders(api, symbol)
        time.sleep(2)  # Chờ lệnh hủy được xử lý
    
    # 5. Thiết lập thủ công SL/TP
    test_set_manual_sl_tp(api, symbol, side, entry_price, mark_price)
    time.sleep(2)  # Chờ lệnh được tạo
    
    # 6. Kiểm tra lại các lệnh SL/TP sau khi tạo
    logger.info("Kiểm tra các lệnh SL/TP sau khi tạo thủ công:")
    sl_orders, tp_orders = test_get_stop_loss_orders(api, symbol)
    
    # 7. Chạy các script tự động
    logger.info("Thực hiện kiểm tra auto_setup_stoploss.py...")
    test_auto_setup_stoploss(api)
    
    logger.info("Thực hiện kiểm tra auto_setup_sltp.py...")
    test_auto_setup_sltp(api)
    
    # 8. Kiểm tra lại sau khi chạy script tự động
    logger.info("Kiểm tra lại các lệnh SL/TP sau khi chạy script tự động:")
    sl_orders_after, tp_orders_after = test_get_stop_loss_orders(api, symbol)
    
    logger.info("=== KẾT THÚC KIỂM TRA TỰ ĐỘNG ĐIỀU CHỈNH SL/TP ===")

if __name__ == "__main__":
    main()