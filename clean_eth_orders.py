#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Script xóa các lệnh ETH đang treo"""

import os
import sys
import logging
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('clean_eth_orders')

# Thêm thư mục gốc vào sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from binance_api import BinanceAPI

def clean_eth_orders(testnet=True):
    """Xóa các lệnh ETH đang treo"""
    
    binance_api = BinanceAPI(testnet=testnet)
    
    print(f"===== XÓA LỆNH ETH ĐANG TREO =====")
    print(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    # Kiểm tra các vị thế ETH
    positions = binance_api.futures_get_position()
    eth_positions = [p for p in positions if p.get('symbol') == 'ETHUSDT' and abs(float(p.get('positionAmt', 0))) > 0]
    
    if eth_positions:
        print(f"Tìm thấy {len(eth_positions)} vị thế ETH đang mở")
        for pos in eth_positions:
            side = 'LONG' if float(pos.get('positionAmt', 0)) > 0 else 'SHORT'
            entry_price = float(pos.get('entryPrice', 0))
            position_amt = abs(float(pos.get('positionAmt', 0)))
            print(f"Vị thế: ETHUSDT {side}, Entry: {entry_price}, Số lượng: {position_amt}")
    else:
        print("Không tìm thấy vị thế ETH nào đang mở")
    
    # Lấy các lệnh ETH đang chờ
    eth_orders = binance_api.get_open_orders('ETHUSDT')
    
    if eth_orders:
        print(f"\nTìm thấy {len(eth_orders)} lệnh ETH đang chờ")
        for order in eth_orders:
            order_id = order.get('orderId')
            order_type = order.get('type')
            side = order.get('side')
            stop_price = float(order.get('stopPrice', 0))
            print(f"Lệnh: ID={order_id}, {order_type} {side}, Stop price: {stop_price}")
            
            # Xóa lệnh
            try:
                result = binance_api.cancel_order('ETHUSDT', order_id)
                print(f"Đã xóa lệnh {order_id}: {result}")
            except Exception as e:
                print(f"Lỗi khi xóa lệnh {order_id}: {str(e)}")
    else:
        print("Không tìm thấy lệnh ETH nào đang chờ")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Xóa các lệnh ETH đang treo')
    parser.add_argument('--testnet', action='store_true', help='Sử dụng testnet')
    
    args = parser.parse_args()
    clean_eth_orders(testnet=args.testnet)