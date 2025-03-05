#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from binance_api import BinanceAPI
from datetime import datetime, timedelta

def main():
    api = BinanceAPI()
    
    # Lấy tài khoản
    account = api.get_futures_account()
    balance = float(account.get('totalWalletBalance', 0))
    available = float(account.get('availableBalance', 0))
    
    print(f'Số dư tài khoản: {balance:.2f} USDT')
    print(f'Số dư khả dụng: {available:.2f} USDT')
    print(f'P/L tổng: {float(account.get("totalUnrealizedProfit", 0)):.2f} USDT')
    print('-' * 70)
    
    # Lấy lịch sử giao dịch (7 ngày gần nhất)
    start_time = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
    end_time = int(datetime.now().timestamp() * 1000)
    
    try:
        symbols = ["BTCUSDT", "ETHUSDT"]
        all_trades = []
        
        for symbol in symbols:
            print(f"Đang lấy lịch sử giao dịch cho {symbol}...")
            trades = api.get_all_orders(symbol=symbol, start_time=start_time, end_time=end_time) or []
            filled_trades = [t for t in trades if t.get('status') == 'FILLED']
            all_trades.extend(filled_trades)
        
        if not all_trades:
            print("Không có giao dịch nào trong 7 ngày gần đây")
            return
        
        print(f"\nĐã tìm thấy {len(all_trades)} giao dịch đã hoàn thành:")
        
        # Sắp xếp giao dịch theo thời gian gần nhất
        all_trades.sort(key=lambda x: x.get('time', 0), reverse=True)
        
        for i, trade in enumerate(all_trades[:10]):  # Hiển thị 10 giao dịch gần nhất
            symbol = trade.get('symbol')
            side = trade.get('side')
            price = float(trade.get('price', 0))
            qty = float(trade.get('executedQty', 0))
            trade_time = datetime.fromtimestamp(trade.get('time', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"{i+1}. {symbol} {side} - Giá: {price:.2f} - Số lượng: {qty} - Thời gian: {trade_time}")
        
    except Exception as e:
        print(f"Lỗi khi lấy lịch sử giao dịch: {e}")

if __name__ == '__main__':
    main()
