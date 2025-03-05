#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from binance_api import BinanceAPI

def main():
    api = BinanceAPI()
    positions = api.get_futures_position_risk()
    active_positions = [pos for pos in positions if abs(float(pos.get('positionAmt', 0))) > 0]
    
    print(f'Số vị thế đang mở: {len(active_positions)}')
    print('-' * 70)
    
    for pos in active_positions:
        symbol = pos.get('symbol')
        position_amt = float(pos.get('positionAmt', 0))
        side = 'LONG' if position_amt > 0 else 'SHORT'
        unrealized_profit = float(pos.get('unrealizedProfit', 0))
        entry_price = float(pos.get('entryPrice', 0))
        leverage = pos.get('leverage')
        
        print(f'Cặp giao dịch: {symbol}')
        print(f'Loại vị thế: {side}')
        print(f'Số lượng: {abs(position_amt)}')
        print(f'Giá vào: {entry_price}')
        print(f'Lợi nhuận: {unrealized_profit:.4f} USDT')
        print(f'Đòn bẩy: {leverage}x')
        print('-' * 70)

if __name__ == '__main__':
    main()
