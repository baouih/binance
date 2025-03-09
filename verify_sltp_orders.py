#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Xác minh lệnh SL/TP đang mở trên Binance Futures
"""

import logging
import json
from binance_api import BinanceAPI
from binance_api_fixes import apply_fixes_to_api

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("verify_sltp")

def main():
    # Khởi tạo API
    api = BinanceAPI(None, None, testnet=True)
    api = apply_fixes_to_api(api)
    
    # Lấy vị thế đang mở
    positions = api.get_futures_position_risk()
    active_positions = [p for p in positions if abs(float(p.get('positionAmt', 0))) > 0]
    
    # Hiển thị số lượng vị thế
    logger.info(f"Có {len(active_positions)} vị thế đang mở")
    
    # Kiểm tra từng vị thế
    for pos in active_positions:
        symbol = pos.get('symbol')
        position_side = pos.get('positionSide')
        position_amt = float(pos.get('positionAmt', 0))
        entry_price = float(pos.get('entryPrice', 0))
        leverage = pos.get('leverage')
        
        logger.info(f"\n--- Vị thế {symbol} ---")
        logger.info(f"Side: {position_side}, Số lượng: {position_amt}, Entry: {entry_price}, Đòn bẩy: {leverage}")
        
        # Lấy lệnh đang mở
        orders = api.get_open_orders(symbol)
        
        # Phân loại lệnh
        sl_orders = [o for o in orders if o.get('type') in ['STOP_MARKET', 'STOP'] and o.get('side') != 'NONE']
        tp_orders = [o for o in orders if o.get('type') in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT'] and o.get('side') != 'NONE']
        
        logger.info(f"SL orders: {len(sl_orders)}, TP orders: {len(tp_orders)}")
        
        # Hiển thị chi tiết lệnh
        for sl in sl_orders:
            order_id = sl.get('orderId')
            stop_price = sl.get('stopPrice')
            order_side = sl.get('side')
            order_position_side = sl.get('positionSide')
            
            # Tính % SL dựa trên entry price
            sl_percent = abs((float(stop_price) - entry_price) / entry_price * 100)
            
            logger.info(f"SL #{order_id}: Giá={stop_price}, Side={order_side}, PositionSide={order_position_side}, %={sl_percent:.2f}%")
            
            # Kiểm tra các vấn đề
            if position_side != order_position_side and order_position_side is not None:
                logger.warning(f"⚠️ PositionSide không khớp: {position_side} vs {order_position_side}")
        
        for tp in tp_orders:
            order_id = tp.get('orderId')
            stop_price = tp.get('stopPrice')
            order_side = tp.get('side')
            order_position_side = tp.get('positionSide')
            
            # Tính % TP dựa trên entry price
            tp_percent = abs((float(stop_price) - entry_price) / entry_price * 100)
            
            logger.info(f"TP #{order_id}: Giá={stop_price}, Side={order_side}, PositionSide={order_position_side}, %={tp_percent:.2f}%")
            
            # Kiểm tra các vấn đề
            if position_side != order_position_side and order_position_side is not None:
                logger.warning(f"⚠️ PositionSide không khớp: {position_side} vs {order_position_side}")
        
        # Hiển thị trạng thái
        if len(sl_orders) == 0:
            logger.warning(f"❌ Thiếu lệnh SL cho {symbol}")
        
        if len(tp_orders) == 0:
            logger.warning(f"❌ Thiếu lệnh TP cho {symbol}")
            
        if len(sl_orders) > 0 and len(tp_orders) > 0:
            logger.info(f"✅ {symbol} có đầy đủ SL và TP")

if __name__ == "__main__":
    main()