#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Auto SL/TP Manager
Kiểm tra và xác minh tính năng quản lý Stop Loss và Take Profit tự động
"""

import logging
import json
import time
import os
from binance_api import BinanceAPI
from binance_api_fixes import apply_fixes_to_api
from auto_sltp_manager import AutoSLTPManager

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_auto_sltp')

def verify_sltp_orders(api, symbol):
    """Xác minh các lệnh SL/TP đang mở"""
    try:
        # Lấy thông tin vị thế
        positions = api.get_futures_position_risk()
        pos = None
        
        for p in positions:
            if p.get('symbol') == symbol and float(p.get('positionAmt', 0)) != 0:
                pos = p
                break
                
        if not pos:
            logger.warning(f"Không tìm thấy vị thế active cho {symbol}")
            return False, "Không tìm thấy vị thế"
            
        # Lấy các lệnh đang mở
        orders = api.get_open_orders(symbol)
        
        sl_orders = [o for o in orders if o.get('type') in ['STOP_MARKET', 'STOP'] and o.get('side') != 'NONE']
        tp_orders = [o for o in orders if o.get('type') in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT'] and o.get('side') != 'NONE']
        
        # Kiểm tra xem có cả SL và TP không
        has_sl = len(sl_orders) > 0
        has_tp = len(tp_orders) > 0
        
        # Hiển thị thông tin chi tiết
        logger.info(f"Vị thế {symbol}: {pos.get('positionSide')} - {pos.get('positionAmt')}")
        logger.info(f"Lệnh SL ({len(sl_orders)}): {[o.get('orderId') for o in sl_orders]}")
        logger.info(f"Lệnh TP ({len(tp_orders)}): {[o.get('orderId') for o in tp_orders]}")
        
        # Kiểm tra chi tiết về lệnh
        if has_sl and has_tp:
            sl_order = sl_orders[0]
            tp_order = tp_orders[0]
            
            # Kiểm tra thuộc tính positionSide nếu tài khoản ở chế độ hedge mode
            if hasattr(api, 'hedge_mode') and api.hedge_mode:
                sl_has_position_side = sl_order.get('positionSide') == pos.get('positionSide')
                tp_has_position_side = tp_order.get('positionSide') == pos.get('positionSide')
                
                if not sl_has_position_side or not tp_has_position_side:
                    logger.error(f"Lỗi: positionSide không đúng! SL: {sl_order.get('positionSide')}, TP: {tp_order.get('positionSide')}, Vị thế: {pos.get('positionSide')}")
                    return False, "positionSide không đúng"
                
            # Kiểm tra các thông số khác
            if sl_order.get('type') != 'STOP_MARKET' or tp_order.get('type') != 'TAKE_PROFIT_MARKET':
                logger.error(f"Lỗi: Loại lệnh không đúng! SL: {sl_order.get('type')}, TP: {tp_order.get('type')}")
                return False, "Loại lệnh không đúng"
                
            return True, "Các lệnh SL/TP hợp lệ"
        else:
            return False, f"Thiếu lệnh (SL: {has_sl}, TP: {has_tp})"
            
    except Exception as e:
        logger.error(f"Lỗi khi xác minh lệnh SL/TP: {str(e)}")
        return False, str(e)

def main():
    """Hàm chính để kiểm tra Auto SL/TP Manager"""
    try:
        # Khởi tạo API
        api = BinanceAPI(None, None, testnet=True)
        apply_fixes_to_api(api)
        
        # Khởi tạo Auto SL/TP Manager
        manager = AutoSLTPManager(testnet=True)
        
        # Kiểm tra các vị thế hiện tại
        positions = api.get_futures_position_risk()
        active_positions = [p for p in positions if abs(float(p.get('positionAmt', 0))) > 0]
        
        if not active_positions:
            logger.warning("Không tìm thấy vị thế đang mở để kiểm tra")
            return
            
        logger.info(f"Tìm thấy {len(active_positions)} vị thế đang mở")
        symbols = [p.get('symbol') for p in active_positions]
        
        # Thực hiện kiểm tra từng bước
        test_steps = [
            {"name": "Cập nhật vị thế", "fn": lambda: manager.update_positions()},
            {"name": "Hủy lệnh SL/TP", "fn": lambda: all(manager.cancel_sl_tp_orders(s) for s in symbols)},
            {"name": "Thiết lập ban đầu", "fn": lambda: all(manager.setup_initial_sltp(s, force=True) for s in symbols)},
            {"name": "Xác minh lệnh", "fn": lambda: all(verify_sltp_orders(api, s)[0] for s in symbols)}
        ]
        
        # Thực hiện từng bước
        for i, step in enumerate(test_steps):
            logger.info(f"\nBước {i+1}/{len(test_steps)}: {step['name']}...")
            success = step['fn']()
            
            if success:
                logger.info(f"✅ {step['name']} thành công!")
            else:
                logger.error(f"❌ {step['name']} thất bại!")
                return
                
            # Chờ giữa các bước
            time.sleep(2)
            
        # Kiểm tra chi tiết SL/TP cuối cùng
        logger.info("\nKết quả cuối cùng:")
        for symbol in symbols:
            success, message = verify_sltp_orders(api, symbol)
            status = "✅ Thành công" if success else "❌ Thất bại"
            logger.info(f"{symbol}: {status} - {message}")
            
        logger.info("\nTất cả các kiểm tra đã hoàn tất!")
        
    except Exception as e:
        logger.error(f"Lỗi trong quá trình kiểm tra: {str(e)}")

if __name__ == "__main__":
    main()