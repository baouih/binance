#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test SL/TP Integration - Kiểm tra tích hợp Stop Loss và Take Profit với API Binance

Script này kiểm tra việc tích hợp và hoạt động của các lệnh SL/TP trên Binance API
"""

import os
import json
import time
import logging
from typing import Dict, List, Optional

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_sltp_integration')

from binance_api import BinanceAPI
from binance_api_fixes import apply_fixes_to_api

def setup_api() -> BinanceAPI:
    """Khởi tạo API với bản sửa lỗi áp dụng"""
    api = BinanceAPI(None, None, testnet=True)
    # Tải api từ account_config.json sẽ tự động thiết lập account_type là futures
    apply_fixes_to_api(api)
    return api

def test_get_positions(api: BinanceAPI) -> List[Dict]:
    """Kiểm tra lấy vị thế hiện tại"""
    logger.info("Đang lấy vị thế hiện tại...")
    positions = api.get_futures_position_risk()
    active_positions = [p for p in positions if abs(float(p.get('positionAmt', 0))) > 0]
    
    logger.info(f"Tìm thấy {len(active_positions)} vị thế đang mở")
    for pos in active_positions:
        symbol = pos.get('symbol')
        amount = float(pos.get('positionAmt', 0))
        entry_price = float(pos.get('entryPrice', 0))
        mark_price = float(pos.get('markPrice', 0))
        unrealized_pnl = float(pos.get('unRealizedProfit', 0))
        
        logger.info(f"Vị thế: {symbol}, Số lượng: {amount}, Entry Price: {entry_price}, "
                   f"Mark Price: {mark_price}, Unrealized PnL: {unrealized_pnl}")
    
    return active_positions

def test_get_open_orders(api: BinanceAPI, symbol: str) -> Dict[str, List[Dict]]:
    """Kiểm tra lấy lệnh đang mở"""
    logger.info(f"Đang lấy lệnh đang mở cho {symbol}...")
    orders = api.get_open_orders(symbol)
    
    # Phân loại lệnh
    sl_orders = [o for o in orders if o.get('type') in ['STOP_MARKET', 'STOP'] and o.get('reduceOnly', False)]
    tp_orders = [o for o in orders if o.get('type') in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT'] and o.get('reduceOnly', False)]
    other_orders = [o for o in orders if o not in sl_orders and o not in tp_orders]
    
    logger.info(f"Tìm thấy {len(sl_orders)} lệnh SL, {len(tp_orders)} lệnh TP, {len(other_orders)} lệnh khác")
    
    # In chi tiết
    for sl in sl_orders:
        logger.info(f"SL: ID={sl.get('orderId')}, Price={sl.get('stopPrice')}, Type={sl.get('type')}")
    for tp in tp_orders:
        logger.info(f"TP: ID={tp.get('orderId')}, Price={tp.get('stopPrice')}, Type={tp.get('type')}")
    
    return {
        'sl': sl_orders,
        'tp': tp_orders,
        'other': other_orders
    }

def cancel_all_sl_tp(api: BinanceAPI, symbol: str) -> bool:
    """Hủy tất cả lệnh SL/TP cho một symbol"""
    logger.info(f"Hủy tất cả lệnh SL/TP cho {symbol}...")
    orders = test_get_open_orders(api, symbol)
    sl_tp_orders = orders['sl'] + orders['tp']
    
    for order in sl_tp_orders:
        order_id = order.get('orderId')
        order_type = order.get('type')
        
        try:
            api.cancel_order(symbol=symbol, order_id=order_id)
            logger.info(f"Đã hủy lệnh {order_type} #{order_id}")
        except Exception as e:
            logger.error(f"Lỗi khi hủy lệnh #{order_id}: {str(e)}")
    
    return True

def set_sl_tp_for_position(api: BinanceAPI, symbol: str, position: Dict) -> bool:
    """Thiết lập SL/TP cho một vị thế"""
    # Lấy thông tin vị thế
    position_amt = float(position.get('positionAmt', 0))
    entry_price = float(position.get('entryPrice', 0))
    side = 'LONG' if position_amt > 0 else 'SHORT'
    qty = abs(position_amt)
    
    # Tính toán giá SL/TP
    sl_percent = 2.0  # 2% cho SL
    tp_percent = 3.0  # 3% cho TP
    
    if side == 'LONG':
        sl_price = entry_price * (1 - sl_percent / 100)
        tp_price = entry_price * (1 + tp_percent / 100)
    else:
        sl_price = entry_price * (1 + sl_percent / 100)
        tp_price = entry_price * (1 - tp_percent / 100)
    
    # Làm tròn giá
    sl_price = round(sl_price, 2)
    tp_price = round(tp_price, 2)
    
    logger.info(f"Thiết lập SL/TP cho {symbol} {side}:")
    logger.info(f"Entry Price: {entry_price}, SL: {sl_price}, TP: {tp_price}")
    
    # Đặt SL
    try:
        close_side = 'SELL' if side == 'LONG' else 'BUY'
        
        # Đặt lệnh Stop Loss
        sl_result = api.futures_create_order(
            symbol=symbol,
            side=close_side,
            type='STOP_MARKET',
            stopPrice=sl_price,
            quantity=qty,
            reduceOnly='true',
            workingType="MARK_PRICE"
        )
        
        logger.info(f"Đã đặt lệnh SL: {sl_result}")
        
        # Đặt lệnh Take Profit
        tp_result = api.futures_create_order(
            symbol=symbol,
            side=close_side,
            type='TAKE_PROFIT_MARKET',
            stopPrice=tp_price,
            quantity=qty,
            reduceOnly='true',
            workingType="MARK_PRICE"
        )
        
        logger.info(f"Đã đặt lệnh TP: {tp_result}")
        
        return True
    except Exception as e:
        logger.error(f"Lỗi khi đặt lệnh SL/TP: {str(e)}")
        return False

def main():
    # Khởi tạo API
    api = setup_api()
    
    # Test kết nối
    logger.info("Kiểm tra kết nối API...")
    try:
        account_info = api.futures_account_balance()
        logger.info("Kết nối API thành công!")
        if account_info:
            logger.info(f"Số dư tài khoản: {account_info[0].get('balance')} USDT")
    except Exception as e:
        logger.error(f"Lỗi kết nối API: {str(e)}")
        return
    
    # Lấy vị thế hiện tại
    positions = test_get_positions(api)
    if not positions:
        logger.info("Không có vị thế đang mở. Thoát.")
        return
    
    # Chọn vị thế đầu tiên để test
    test_position = positions[0]
    symbol = test_position.get('symbol')
    
    # Hủy lệnh SL/TP hiện tại
    cancel_all_sl_tp(api, symbol)
    
    # Đặt lệnh SL/TP mới
    success = set_sl_tp_for_position(api, symbol, test_position)
    if success:
        logger.info(f"Đã thiết lập SL/TP cho {symbol} thành công!")
    else:
        logger.error(f"Không thể thiết lập SL/TP cho {symbol}")
    
    # Kiểm tra lại lệnh đang mở
    time.sleep(2)  # Chờ một chút để đảm bảo lệnh đã được xử lý
    final_orders = test_get_open_orders(api, symbol)
    
    # Hiển thị kết quả
    logger.info(f"Kết quả test SL/TP integration cho {symbol}:")
    logger.info(f"- Số lệnh SL: {len(final_orders['sl'])}")
    logger.info(f"- Số lệnh TP: {len(final_orders['tp'])}")
    
    if len(final_orders['sl']) > 0 and len(final_orders['tp']) > 0:
        logger.info("✅ TEST PASSED: Đã thiết lập thành công cả SL và TP")
    else:
        logger.error("❌ TEST FAILED: Không đặt được đủ cả SL và TP")

if __name__ == "__main__":
    main()