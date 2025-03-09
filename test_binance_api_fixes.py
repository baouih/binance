#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module kiểm tra các bản vá API Binance trong binance_api_fixes.py

Kiểm tra:
1. Xác định đúng chế độ tài khoản hedge/one-way
2. Xử lý đúng tham số positionSide cho hedge mode
3. Xử lý đúng tham số reduceOnly cho one-way mode
4. Đặt lệnh SL/TP chính xác cho cả hai chế độ tài khoản
"""

import sys
import logging
import json
import os
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('test_binance_api_fixes')

# Import các module cần thiết
from binance_api import BinanceAPI
from binance_api_fixes import apply_fixes_to_api, APIFixer


def test_hedge_mode_detection():
    """Kiểm tra nhận dạng chế độ hedge mode của tài khoản"""
    api = BinanceAPI()
    api = apply_fixes_to_api(api)
    
    # Kiểm tra hedge mode
    hedge_status = api.hedge_mode
    logger.info(f"Chế độ hedge mode: {hedge_status}")
    
    return hedge_status


def test_create_order(api, symbol="BTCUSDT", side="BUY", position_side="LONG", 
                      order_type="LIMIT", price=None, quantity=None, is_sl_tp=False):
    """Kiểm tra tạo lệnh với các tham số khác nhau"""
    
    # Lấy giá hiện tại nếu cần
    if price is None:
        ticker = api.futures_ticker_price(symbol)
        if isinstance(ticker, dict) and 'price' in ticker:
            current_price = float(ticker['price'])
            # Điều chỉnh giá mua/bán cho lệnh LIMIT
            if order_type == "LIMIT":
                if side == "BUY":
                    price = round(current_price * 0.97, 2)  # Giá thấp hơn 3%
                else:
                    price = round(current_price * 1.03, 2)  # Giá cao hơn 3%
            logger.info(f"Lấy giá hiện tại của {symbol}: {current_price}")
        else:
            logger.error(f"Không lấy được giá hiện tại cho {symbol}")
            return False
    
    # Tính số lượng nếu không được chỉ định
    if quantity is None:
        quantity = api.calculate_min_quantity(symbol, 10)  # Lệnh 10 USD
        logger.info(f"Tính số lượng tối thiểu: {quantity}")
    
    # Chuẩn bị tham số
    order_params = {
        'symbol': symbol,
        'side': side,
        'order_type': order_type,
        'quantity': quantity
    }
    
    # Thêm tham số tùy chọn
    if price and order_type != 'MARKET':
        order_params['price'] = price
    
    # Thêm tham số cho hedge mode nếu cần
    if api.hedge_mode:
        order_params['position_side'] = position_side
    
    # Thêm reduce_only cho lệnh TP/SL trong one-way mode
    if is_sl_tp and not api.hedge_mode:
        order_params['reduce_only'] = True
    
    # Tạo lệnh
    logger.info(f"Tạo lệnh {order_type} cho {symbol} với tham số: {json.dumps(order_params, default=str)}")
    
    try:
        if order_type in ['MARKET', 'LIMIT']:
            # Lệnh thông thường
            result = api.create_order_with_position_side(**order_params)
        else:
            # Lệnh có điều kiện
            result = api.create_order_with_position_side(**order_params)
        
        if 'orderId' in result:
            logger.info(f"✅ Tạo lệnh thành công, orderId: {result['orderId']}")
            return True
        else:
            logger.error(f"❌ Lỗi khi tạo lệnh: {result}")
            return False
    except Exception as e:
        logger.error(f"❌ Ngoại lệ khi tạo lệnh: {str(e)}")
        return False


def test_set_sl_tp_orders(api, symbol="BTCUSDT", position_side=None):
    """Kiểm tra tạo lệnh SL/TP tự động"""
    
    # Lấy thông tin vị thế
    positions = api.get_futures_position_risk()
    target_position = None
    
    # Tìm vị thế mục tiêu
    for pos in positions:
        if pos['symbol'] == symbol:
            if api.hedge_mode and position_side:
                # Trong hedge mode, tìm theo position_side
                if pos['positionSide'] == position_side:
                    target_position = pos
                    break
            else:
                # Trong one-way mode, chỉ cần khớp symbol
                target_position = pos
                break
    
    if not target_position:
        logger.error(f"Không tìm thấy vị thế {symbol} {'với positionSide=' + position_side if position_side else ''}")
        return False
    
    # Lấy thông tin vị thế
    entry_price = float(target_position['entryPrice'])
    position_amt = float(target_position['positionAmt'])
    
    logger.info(f"Đã tìm thấy vị thế {symbol}: entryPrice={entry_price}, positionAmt={position_amt}")
    
    # Xác định SL/TP dựa vào vị thế
    if position_amt > 0:  # Vị thế LONG
        sl_price = round(entry_price * 0.98, 2)  # -2%
        tp_price = round(entry_price * 1.03, 2)  # +3%
    else:  # Vị thế SHORT
        sl_price = round(entry_price * 1.02, 2)  # +2%
        tp_price = round(entry_price * 0.97, 2)  # -3%
    
    # Gọi API để đặt SL/TP
    try:
        logger.info(f"Đặt SL={sl_price}, TP={tp_price} cho {symbol}")
        
        result = api.set_stop_loss_take_profit(
            symbol=symbol,
            position_side=position_side,
            entry_price=entry_price,
            stop_loss_price=sl_price,
            take_profit_price=tp_price
        )
        
        # Kiểm tra kết quả
        sl_success = 'stop_loss' in result and 'orderId' in result['stop_loss']
        tp_success = 'take_profit' in result and 'orderId' in result['take_profit']
        
        if sl_success and tp_success:
            logger.info(f"✅ Đặt SL/TP thành công cho {symbol}")
            logger.info(f"SL orderId: {result['stop_loss']['orderId']}")
            logger.info(f"TP orderId: {result['take_profit']['orderId']}")
            return True
        else:
            logger.error(f"❌ Đặt SL/TP thất bại: {result}")
            return False
    except Exception as e:
        logger.error(f"❌ Ngoại lệ khi đặt SL/TP: {str(e)}")
        return False


def verify_sl_tp_orders(api, symbol="BTCUSDT", position_side=None):
    """Xác minh các lệnh SL/TP đã được đặt chính xác"""
    
    try:
        # Lấy danh sách lệnh mở
        open_orders = api.get_futures_open_orders(symbol=symbol)
        
        if not open_orders:
            logger.error(f"Không tìm thấy lệnh mở nào cho {symbol}")
            return False
        
        # Đếm lệnh SL/TP
        sl_orders = []
        tp_orders = []
        
        for order in open_orders:
            if order['symbol'] == symbol:
                if api.hedge_mode and position_side:
                    # Trong hedge mode, lọc theo position_side
                    if order.get('positionSide') != position_side:
                        continue
                
                # Phân loại lệnh
                if order['type'] == 'STOP_MARKET':
                    sl_orders.append(order)
                elif order['type'] == 'TAKE_PROFIT_MARKET':
                    tp_orders.append(order)
        
        # Kiểm tra kết quả
        logger.info(f"Tìm thấy {len(sl_orders)} lệnh SL và {len(tp_orders)} lệnh TP cho {symbol}")
        
        # Hiển thị thông tin chi tiết
        for sl in sl_orders:
            logger.info(f"SL #{sl['orderId']}: Giá={sl['stopPrice']}, Side={sl['side']}, " + 
                       (f"PositionSide={sl['positionSide']}" if 'positionSide' in sl else "One-way mode"))
        
        for tp in tp_orders:
            logger.info(f"TP #{tp['orderId']}: Giá={tp['stopPrice']}, Side={tp['side']}, " +
                       (f"PositionSide={tp['positionSide']}" if 'positionSide' in tp else "One-way mode"))
        
        return len(sl_orders) > 0 and len(tp_orders) > 0
    except Exception as e:
        logger.error(f"❌ Ngoại lệ khi xác minh lệnh SL/TP: {str(e)}")
        return False


def run_tests():
    """Chạy các bài kiểm tra"""
    
    logger.info("=== Bắt đầu kiểm tra module binance_api_fixes ===")
    
    # Tạo API instance
    api = BinanceAPI()
    api = apply_fixes_to_api(api)
    
    # Kiểm tra 1: Xác định chế độ tài khoản
    hedge_mode = test_hedge_mode_detection()
    logger.info(f"Chế độ tài khoản: {'hedge mode' if hedge_mode else 'one-way mode'}")
    
    # Kiểm tra 2: Đặt và xác minh SL/TP
    if hedge_mode:
        # Đối với tài khoản hedge mode, cần chỉ định positionSide
        for position_side in ['LONG', 'SHORT']:
            logger.info(f"\n=== Kiểm tra với positionSide={position_side} ===")
            
            # Đặt SL/TP
            if test_set_sl_tp_orders(api, "BTCUSDT", position_side):
                # Xác minh kết quả
                verify_sl_tp_orders(api, "BTCUSDT", position_side)
    else:
        # Đối với tài khoản one-way, không cần positionSide
        logger.info("\n=== Kiểm tra trong chế độ one-way ===")
        
        # Đặt SL/TP
        if test_set_sl_tp_orders(api, "BTCUSDT"):
            # Xác minh kết quả
            verify_sl_tp_orders(api, "BTCUSDT")
    
    logger.info("\n=== Hoàn thành tất cả các bài kiểm tra ===")


if __name__ == "__main__":
    run_tests()