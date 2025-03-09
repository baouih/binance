#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Script kiểm tra các vị thế hiện tại và lệnh đang chờ"""

import os
import sys
import json
from datetime import datetime

# Thêm thư mục gốc vào sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from binance_api import BinanceAPI

def check_positions(testnet=True):
    """Kiểm tra các vị thế hiện tại và lệnh đang chờ"""
    
    binance_api = BinanceAPI(testnet=testnet)
    
    print("===== KIỂM TRA VỊ THẾ HIỆN TẠI =====")
    print(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    # Lấy tất cả vị thế
    positions = binance_api.futures_get_position()
    active_positions = [p for p in positions if abs(float(p.get('positionAmt', 0))) > 0]
    
    print(f"Số vị thế đang mở: {len(active_positions)}")
    
    # Hiển thị thông tin về các vị thế đang mở
    for pos in active_positions:
        symbol = pos.get('symbol')
        side = 'LONG' if float(pos.get('positionAmt', 0)) > 0 else 'SHORT'
        entry_price = float(pos.get('entryPrice', 0))
        position_amt = abs(float(pos.get('positionAmt', 0)))
        unrealized_profit = float(pos.get('unrealizedProfit', 0))
        
        print(f"\nVị thế: {symbol} {side}")
        print(f"Entry price: {entry_price}")
        print(f"Số lượng: {position_amt}")
        print(f"Lợi nhuận chưa thực hiện: {unrealized_profit:.2f} USDT")
        
        # Lấy các lệnh liên quan
        orders = binance_api.get_open_orders(symbol)
        sl_orders = [o for o in orders if o.get('type') == 'STOP_MARKET']
        tp_orders = [o for o in orders if o.get('type') == 'TAKE_PROFIT_MARKET']
        
        print(f"SL orders: {len(sl_orders)}")
        for order in sl_orders:
            order_price = float(order.get('stopPrice', 0))
            order_side = order.get('side')
            print(f"- SL: {order_price} ({order_side})")
        
        print(f"TP orders: {len(tp_orders)}")
        for order in tp_orders:
            order_price = float(order.get('stopPrice', 0))
            order_side = order.get('side')
            print(f"- TP: {order_price} ({order_side})")
        
        # Tính toán % SL và TP so với giá entry
        if sl_orders and entry_price > 0:
            sl_price = float(sl_orders[0].get('stopPrice', 0))
            if side == 'LONG':
                sl_percent = (entry_price - sl_price) / entry_price * 100
                print(f"SL %: {sl_percent:.2f}% từ entry")
            else:
                sl_percent = (sl_price - entry_price) / entry_price * 100
                print(f"SL %: {sl_percent:.2f}% từ entry")
                
        if tp_orders and entry_price > 0:
            tp_price = float(tp_orders[0].get('stopPrice', 0))
            if side == 'LONG':
                tp_percent = (tp_price - entry_price) / entry_price * 100
                print(f"TP %: {tp_percent:.2f}% từ entry")
            else:
                tp_percent = (entry_price - tp_price) / entry_price * 100
                print(f"TP %: {tp_percent:.2f}% từ entry")
    
    print("\n===== KIỂM TRA LỆNH ĐANG CHỜ =====")
    # Lấy tất cả lệnh đang chờ
    all_orders = binance_api.get_open_orders()
    print(f"Số lệnh đang chờ: {len(all_orders)}")
    
    for order in all_orders:
        symbol = order.get('symbol')
        order_type = order.get('type')
        side = order.get('side')
        price = float(order.get('price', 0))
        stop_price = float(order.get('stopPrice', 0))
        
        print(f"\nLệnh: {symbol} {order_type} {side}")
        if price > 0:
            print(f"Price: {price}")
        if stop_price > 0:
            print(f"Stop price: {stop_price}")
            
    # Kiểm tra các lệnh ETH đặc biệt
    eth_orders = [o for o in all_orders if o.get('symbol') == 'ETHUSDT']
    if eth_orders:
        print("\n===== LỆNH ETH ĐANG CHỜ =====")
        print(f"Số lệnh ETH đang chờ: {len(eth_orders)}")
        
        for order in eth_orders:
            order_type = order.get('type')
            side = order.get('side')
            price = float(order.get('price', 0))
            stop_price = float(order.get('stopPrice', 0))
            
            print(f"\nLệnh ETH {order_type} {side}")
            if price > 0:
                print(f"Price: {price}")
            if stop_price > 0:
                print(f"Stop price: {stop_price}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Kiểm tra vị thế hiện tại và lệnh đang chờ')
    parser.add_argument('--testnet', action='store_true', help='Sử dụng testnet')
    
    args = parser.parse_args()
    check_positions(testnet=args.testnet)