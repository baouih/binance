#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script kiểm tra tính hiển thị của lệnh SL/TP trên giao diện Binance
"""

import sys
import logging
import json
import argparse
from binance_api import BinanceAPI

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("check_visible_sltp")

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

def check_visible_sltp(symbol=None, api=None):
    """
    Kiểm tra các lệnh SL/TP có hiển thị đúng hay không
    
    Args:
        symbol: Symbol cần kiểm tra, nếu None sẽ kiểm tra tất cả
        api: Đối tượng BinanceAPI đã khởi tạo
    """
    # Khởi tạo API nếu chưa được cung cấp
    if api is None:
        config = load_account_config()
        api_key = config.get('api_key', '')
        api_secret = config.get('api_secret', '')
        testnet = config.get('testnet', True)
        
        api = BinanceAPI(api_key, api_secret, testnet=testnet)
    
    # Lấy danh sách vị thế
    positions = api.futures_get_position(symbol)
    
    # Lọc các vị thế đang mở
    active_positions = [p for p in positions if float(p.get('positionAmt', 0)) != 0]
    
    if not active_positions:
        logger.info("Không có vị thế đang mở")
        return
    
    logger.info(f"Tìm thấy {len(active_positions)} vị thế đang mở")
    
    # Kiểm tra từng vị thế
    for position in active_positions:
        pos_symbol = position.get('symbol')
        pos_amount = float(position.get('positionAmt', 0))
        entry_price = float(position.get('entryPrice', 0))
        side = 'LONG' if pos_amount > 0 else 'SHORT'
        quantity = abs(pos_amount)
        
        logger.info(f"Vị thế {pos_symbol} {side}: Entry={entry_price}, Quantity={quantity}")
        
        # Lấy các lệnh đang mở cho symbol
        open_orders = api.get_open_orders(pos_symbol)
        
        # Phân loại các lệnh SL và TP
        sl_orders = [o for o in open_orders if o.get('type') in ['STOP_MARKET', 'STOP']]
        tp_orders = [o for o in open_orders if o.get('type') in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT']]
        
        # Kiểm tra lệnh SL
        if sl_orders:
            logger.info(f"  SL: {len(sl_orders)} lệnh")
            for order in sl_orders:
                order_id = order.get('orderId')
                order_type = order.get('type')
                stop_price = float(order.get('stopPrice', 0))
                reduce_only = order.get('reduceOnly', False)
                order_quantity = float(order.get('origQty', 0))
                
                status = "✅ Đúng" if reduce_only and order_quantity == quantity else "❌ Cần sửa"
                
                logger.info(f"  - {order_id}: {order_type}, stopPrice={stop_price}, reduceOnly={reduce_only}, qty={order_quantity} {status}")
        else:
            logger.warning(f"  ❌ Không tìm thấy lệnh SL cho {pos_symbol} {side}")
        
        # Kiểm tra lệnh TP
        if tp_orders:
            logger.info(f"  TP: {len(tp_orders)} lệnh")
            for order in tp_orders:
                order_id = order.get('orderId')
                order_type = order.get('type')
                stop_price = float(order.get('stopPrice', 0))
                reduce_only = order.get('reduceOnly', False)
                order_quantity = float(order.get('origQty', 0))
                
                status = "✅ Đúng" if reduce_only and order_quantity == quantity else "❌ Cần sửa"
                
                logger.info(f"  - {order_id}: {order_type}, stopPrice={stop_price}, reduceOnly={reduce_only}, qty={order_quantity} {status}")
        else:
            logger.warning(f"  ❌ Không tìm thấy lệnh TP cho {pos_symbol} {side}")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description="Kiểm tra tính hiển thị của lệnh SL/TP")
    parser.add_argument("--symbol", help="Symbol cần kiểm tra")
    args = parser.parse_args()
    
    check_visible_sltp(args.symbol)

if __name__ == "__main__":
    main()