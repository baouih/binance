#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script khắc phục các lệnh SL/TP không hiển thị trên giao diện Binance
"""

import sys
import logging
import json
import argparse
import time
from binance_api import BinanceAPI

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("fix_visible_sltp")

def load_account_config():
    """
    Tải cấu hình tài khoản từ file config
    """
    try:
        with open('account_config.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Lỗi khi tải file cấu hình: {str(e)}")
        return {}

def load_sltp_config():
    """
    Tải cấu hình SL/TP từ file
    """
    try:
        with open('configs/sltp_config.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Lỗi khi tải file cấu hình SL/TP: {str(e)}")
        # Sử dụng giá trị mặc định nếu không tìm thấy file
        return {"default_sl_percent": 2.0, "default_tp_percent": 3.0}

def get_price_precision(symbol, api):
    """
    Lấy độ chính xác giá của một symbol
    
    Args:
        symbol: Symbol cần lấy thông tin
        api: Đối tượng BinanceAPI
        
    Returns:
        int: Số chữ số sau dấu phẩy
    """
    try:
        # Lấy thông tin symbol
        exchange_info = api.futures_exchange_info()
        
        # Tìm symbol trong danh sách
        for info in exchange_info.get('symbols', []):
            if info.get('symbol') == symbol:
                return len(info.get('pricePrecision', '1'))
        
        return 2  # Mặc định là 2
    except Exception as e:
        logger.error(f"Lỗi khi lấy độ chính xác giá: {str(e)}")
        return 2  # Mặc định là 2

def fix_sltp_for_position(position, api, sl_percent, tp_percent, force=False):
    """
    Khắc phục SL/TP cho một vị thế
    
    Args:
        position: Dict chứa thông tin vị thế
        api: Đối tượng BinanceAPI
        sl_percent: Phần trăm stop loss
        tp_percent: Phần trăm take profit
        force: Buộc thực hiện ngay cả khi đã có lệnh
        
    Returns:
        bool: True nếu thành công
    """
    symbol = position.get('symbol')
    pos_amount = float(position.get('positionAmt', 0))
    entry_price = float(position.get('entryPrice', 0))
    side = 'LONG' if pos_amount > 0 else 'SHORT'
    quantity = abs(pos_amount)
    
    logger.info(f"Chuẩn bị khắc phục SL/TP cho {symbol} {side}: Entry={entry_price}, Quantity={quantity}")
    
    # Lấy các lệnh đang mở cho symbol
    open_orders = api.get_open_orders(symbol)
    
    # Phân loại các lệnh SL và TP
    sl_orders = [o for o in open_orders if o.get('type') in ['STOP_MARKET', 'STOP']]
    tp_orders = [o for o in open_orders if o.get('type') in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT']]
    
    # Kiểm tra xem có cần khắc phục không
    need_fix_sl = force or not sl_orders
    need_fix_tp = force or not tp_orders
    
    # Nếu không cần khắc phục, kiểm tra các lệnh SL/TP có đúng không
    if not need_fix_sl and sl_orders:
        for order in sl_orders:
            order_qty = float(order.get('origQty', 0))
            reduce_only = order.get('reduceOnly', False)
            
            if not reduce_only or order_qty != quantity:
                need_fix_sl = True
                logger.info(f"Cần khắc phục lệnh SL: reduceOnly={reduce_only}, qty={order_qty} != {quantity}")
                break
    
    if not need_fix_tp and tp_orders:
        for order in tp_orders:
            order_qty = float(order.get('origQty', 0))
            reduce_only = order.get('reduceOnly', False)
            
            if not reduce_only or order_qty != quantity:
                need_fix_tp = True
                logger.info(f"Cần khắc phục lệnh TP: reduceOnly={reduce_only}, qty={order_qty} != {quantity}")
                break
    
    # Nếu không cần khắc phục gì
    if not need_fix_sl and not need_fix_tp:
        logger.info(f"Không cần khắc phục SL/TP cho {symbol} {side}")
        return True
    
    # Hủy tất cả lệnh SL/TP hiện có
    for order in sl_orders + tp_orders:
        order_id = order.get('orderId')
        api.cancel_order(symbol=symbol, order_id=order_id)
        logger.info(f"Đã hủy lệnh #{order_id} cho {symbol}")
    
    # Chờ một chút để đảm bảo lệnh đã được hủy
    time.sleep(1)
    
    # Tính toán giá SL/TP
    price_precision = get_price_precision(symbol, api)
    
    if side == 'LONG':
        sl_price = round(entry_price * (1 - sl_percent / 100), price_precision)
        tp_price = round(entry_price * (1 + tp_percent / 100), price_precision)
        close_side = 'SELL'
    else:  # SHORT
        sl_price = round(entry_price * (1 + sl_percent / 100), price_precision)
        tp_price = round(entry_price * (1 - tp_percent / 100), price_precision)
        close_side = 'BUY'
    
    # Đặt lệnh mới
    success = True
    
    if need_fix_sl:
        try:
            # Đặt lệnh SL với reduceOnly=True và quantity=pos_amount
            result = api.futures_create_order(
                symbol=symbol,
                side=close_side,
                type='STOP_MARKET',
                stopPrice=sl_price,
                quantity=quantity,
                reduceOnly=True,
                workingType="MARK_PRICE",
                timeInForce="GTC"
            )
            
            logger.info(f"Đã đặt SL cho {symbol} {side} tại giá {sl_price}, số lượng {quantity}")
        except Exception as e:
            logger.error(f"Lỗi khi đặt lệnh SL: {str(e)}")
            success = False
    
    if need_fix_tp:
        try:
            # Đặt lệnh TP với reduceOnly=True và quantity=pos_amount
            result = api.futures_create_order(
                symbol=symbol,
                side=close_side,
                type='TAKE_PROFIT_MARKET',
                stopPrice=tp_price,
                quantity=quantity,
                reduceOnly=True,
                workingType="MARK_PRICE",
                timeInForce="GTC"
            )
            
            logger.info(f"Đã đặt TP cho {symbol} {side} tại giá {tp_price}, số lượng {quantity}")
        except Exception as e:
            logger.error(f"Lỗi khi đặt lệnh TP: {str(e)}")
            success = False
    
    return success

def fix_visible_sltp(symbol=None, force=False, api=None):
    """
    Khắc phục tất cả các lệnh SL/TP không hiển thị
    
    Args:
        symbol: Symbol cần khắc phục, nếu None sẽ khắc phục tất cả
        force: Buộc khắc phục ngay cả khi đã có lệnh
        api: Đối tượng BinanceAPI đã khởi tạo
    """
    # Khởi tạo API nếu chưa được cung cấp
    if api is None:
        config = load_account_config()
        api_key = config.get('api_key', '')
        api_secret = config.get('api_secret', '')
        testnet = config.get('testnet', True)
        
        api = BinanceAPI(api_key, api_secret, testnet=testnet)
    
    # Tải cấu hình SL/TP
    sltp_config = load_sltp_config()
    sl_percent = float(sltp_config.get('default_sl_percent', 2.0))
    tp_percent = float(sltp_config.get('default_tp_percent', 3.0))
    
    # Lấy danh sách vị thế
    positions = api.futures_get_position(symbol)
    
    # Lọc các vị thế đang mở
    active_positions = [p for p in positions if float(p.get('positionAmt', 0)) != 0]
    
    if not active_positions:
        logger.info("Không có vị thế đang mở")
        return
    
    logger.info(f"Tìm thấy {len(active_positions)} vị thế đang mở")
    
    # Khắc phục từng vị thế
    for position in active_positions:
        fix_sltp_for_position(position, api, sl_percent, tp_percent, force)

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description="Khắc phục các lệnh SL/TP không hiển thị")
    parser.add_argument("--symbol", help="Symbol cần khắc phục")
    parser.add_argument("--force", action="store_true", help="Buộc khắc phục tất cả các lệnh")
    args = parser.parse_args()
    
    fix_visible_sltp(args.symbol, args.force)

if __name__ == "__main__":
    main()