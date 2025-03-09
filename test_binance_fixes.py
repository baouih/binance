#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script để kiểm tra các bản vá lỗi cho Binance API
"""

import os
import sys
import json
import time
import logging
import traceback
from binance_api import BinanceAPI
from binance_api_fixes import apply_fixes_to_api

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_binance_fixes")

def test_position_mode():
    """Kiểm tra và hiển thị chế độ position mode"""
    logger.info("=== KIỂM TRA CHẾ ĐỘ POSITION MODE ===")
    
    api = BinanceAPI()
    api = apply_fixes_to_api(api)
    
    logger.info(f"Tài khoản ở chế độ hedge mode: {api.hedge_mode}")
    
    # Lấy vị thế hiện tại
    positions = api.get_futures_position_risk()
    active_positions = [p for p in positions if float(p.get('positionAmt', 0)) != 0]
    
    logger.info(f"Số vị thế active: {len(active_positions)}")
    for pos in active_positions:
        symbol = pos['symbol']
        pos_side = pos['positionSide']
        pos_amt = float(pos['positionAmt'])
        entry_price = float(pos['entryPrice'])
        mark_price = float(pos['markPrice'])
        unreal_pnl = float(pos['unRealizedProfit'])
        
        logger.info(f"Vị thế {symbol} ({pos_side}): {pos_amt} @ {entry_price} (Mark: {mark_price}, PnL: {unreal_pnl})")

def test_market_order():
    """Kiểm tra tạo lệnh market với các bản vá đã áp dụng"""
    logger.info("=== KIỂM TRA TẠO LỆNH MARKET ===")
    
    api = BinanceAPI()
    api = apply_fixes_to_api(api)
    
    # Symbol và giá trị lệnh
    symbol = "BTCUSDT"
    usd_value = 200  # 200 USD
    
    # Tạo lệnh
    side = "BUY"
    position_side = "LONG" if api.hedge_mode else None
    
    logger.info(f"Tạo lệnh {side} {symbol} với giá trị {usd_value} USD")
    order = api.create_order_with_position_side(
        symbol=symbol,
        side=side,
        order_type="MARKET",
        usd_value=usd_value,
        position_side=position_side
    )
    
    if order.get('error'):
        logger.error(f"Lỗi tạo lệnh: {order.get('error')}")
        return False
    
    logger.info(f"Lệnh thành công: {json.dumps(order, indent=2)}")
    return True

def test_tp_sl_orders():
    """Kiểm tra tạo lệnh TP/SL với các bản vá đã áp dụng"""
    logger.info("=== KIỂM TRA TẠO LỆNH TP/SL ===")
    
    api = BinanceAPI()
    api = apply_fixes_to_api(api)
    
    # Symbol và các thông số
    symbol = "BTCUSDT"
    usd_value = 100  # 100 USD
    
    # Lấy vị thế hiện tại
    positions = api.get_position_risk()
    active_pos = None
    
    for pos in positions:
        if pos['symbol'] == symbol and float(pos.get('positionAmt', 0)) != 0:
            active_pos = pos
            break
    
    if not active_pos:
        logger.warning(f"Không tìm thấy vị thế active nào cho {symbol}")
        return False
    
    position_side = active_pos['positionSide']
    entry_price = float(active_pos['entryPrice'])
    
    # Tính giá TP/SL
    tp_price = round(entry_price * 1.05, 1)  # +5%
    sl_price = round(entry_price * 0.97, 1)  # -3%
    
    logger.info(f"Đặt TP/SL cho {symbol} ({position_side})")
    logger.info(f"Entry: {entry_price}, TP: {tp_price}, SL: {sl_price}")
    
    # Đặt TP/SL
    tp_sl = api.set_stop_loss_take_profit(
        symbol=symbol,
        position_side=position_side,
        entry_price=entry_price,
        stop_loss_price=sl_price,
        take_profit_price=tp_price,
        usd_value=usd_value
    )
    
    if tp_sl.get('error') or (tp_sl.get('take_profit') and tp_sl['take_profit'].get('error')) or (tp_sl.get('stop_loss') and tp_sl['stop_loss'].get('error')):
        logger.error(f"Lỗi đặt TP/SL: {json.dumps(tp_sl, indent=2)}")
        return False
    
    logger.info(f"TP/SL thành công: {json.dumps(tp_sl, indent=2)}")
    return True

def test_thread_monitor():
    """Giả lập một hàm theo dõi thread"""
    logger.info("=== KIỂM TRA THEO DÕI THREAD ===")
    
    import threading
    import time
    
    def worker(name, duration):
        """Hàm worker giả lập"""
        logger.info(f"Thread {name} bắt đầu làm việc")
        for i in range(duration):
            logger.info(f"Thread {name}: Đang xử lý... {i+1}/{duration}")
            time.sleep(1)
        logger.info(f"Thread {name} hoàn thành")
    
    # Tạo các threads
    threads = []
    for i in range(3):
        t = threading.Thread(target=worker, args=(f"Worker-{i}", 3))
        t.daemon = True  # Làm thread chạy nền
        threads.append(t)
        t.start()
    
    # Theo dõi threads
    while True:
        active_threads = [t for t in threads if t.is_alive()]
        if not active_threads:
            logger.info("Tất cả threads đã hoàn thành")
            break
            
        logger.info(f"Đang có {len(active_threads)} threads đang chạy")
        for i, t in enumerate(active_threads):
            logger.info(f"Thread {i}: {t.name}, Trạng thái: {'Alive' if t.is_alive() else 'Dead'}")
        
        time.sleep(1)
    
    return True

def main():
    """Hàm main để chạy tất cả các bài test"""
    logger.info("======= BẮT ĐẦU KIỂM TRA BINANCE API FIXES =======")
    
    try:
        # Kiểm tra chế độ position mode
        test_position_mode()
        
        # Thử tạo lệnh market
        market_result = test_market_order()
        
        # Nếu thành công, thử tạo TP/SL
        if market_result:
            tp_sl_result = test_tp_sl_orders()
        
        # Kiểm tra monitor thread
        # test_thread_monitor()
        
        logger.info("======= HOÀN THÀNH KIỂM TRA =======")
    except Exception as e:
        logger.error(f"Lỗi không mong đợi: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()