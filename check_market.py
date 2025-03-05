#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
from datetime import datetime
from binance_api import BinanceAPI

def format_price(price):
    if float(price) < 0.1:
        return f"{float(price):.8f}"
    elif float(price) < 1:
        return f"{float(price):.6f}"
    elif float(price) < 10:
        return f"{float(price):.4f}"
    elif float(price) < 1000:
        return f"{float(price):.2f}"
    else:
        return f"{float(price):.2f}"

def format_change(pct):
    pct = float(pct)
    if pct > 0:
        return f"\033[32m+{pct:.2f}%\033[0m"  # Green
    elif pct < 0:
        return f"\033[31m{pct:.2f}%\033[0m"   # Red
    else:
        return f"{pct:.2f}%"

def main():
    print("===== THÔNG TIN THỊ TRƯỜNG CRYPTO =====")
    print(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        client = BinanceAPI()
        
        # Lấy thông tin 24h ticker
        tickers = {}
        ticker_data = client.get_24h_ticker()
        
        # Lọc những cặp tiền USDT
        usdt_tickers = []
        for ticker in ticker_data:
            if isinstance(ticker, dict) and ticker.get('symbol', '').endswith('USDT'):
                usdt_tickers.append(ticker)
        
        # Sắp xếp theo khối lượng
        sorted_tickers = sorted(usdt_tickers, key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
        
        # Hiển thị top 10 cặp tiền theo khối lượng
        print("\nTOP 10 CẶP TIỀN THEO KHỐI LƯỢNG GIAO DỊCH:")
        print("{:<10} {:<12} {:<12} {:<15} {:<15}".format(
            "SYMBOL", "GIÁ", "THAY ĐỔI 24H", "KHỐI LƯỢNG (USDT)", "CAO/THẤP 24H"
        ))
        print("-" * 80)
        
        for i, ticker in enumerate(sorted_tickers[:10]):
            symbol = ticker.get('symbol', '')
            price = format_price(ticker.get('lastPrice', 0))
            change_pct = format_change(ticker.get('priceChangePercent', 0))
            volume = float(ticker.get('quoteVolume', 0))
            volume_fmt = f"{volume/1000000:.2f}M" if volume >= 1000000 else f"{volume/1000:.2f}K"
            high = format_price(ticker.get('highPrice', 0))
            low = format_price(ticker.get('lowPrice', 0))
            
            print("{:<10} {:<12} {:<20} {:<15} {}/{}".format(
                symbol, price, change_pct, volume_fmt, high, low
            ))
        
        # Lấy thông tin order book cho BTC và ETH
        print("\nORDER BOOK CÁC CẶP TIỀN CHÍNH:")
        for symbol in ['BTCUSDT', 'ETHUSDT']:
            try:
                order_book = client.get_order_book(symbol=symbol, limit=5)
                
                print(f"\n{symbol} ORDER BOOK:")
                
                # Hiển thị asks (bán)
                print("BIDS (MUA):")
                for bid in order_book.get('bids', [])[:5]:
                    price, qty = bid
                    print(f"  Giá: {format_price(price)}, SL: {float(qty):.6f}, Giá trị: {float(price) * float(qty):.2f} USDT")
                
                # Hiển thị bids (mua)
                print("ASKS (BÁN):")
                for ask in order_book.get('asks', [])[:5]:
                    price, qty = ask
                    print(f"  Giá: {format_price(price)}, SL: {float(qty):.6f}, Giá trị: {float(price) * float(qty):.2f} USDT")
            except Exception as e:
                print(f"Lỗi khi lấy order book cho {symbol}: {str(e)}")
        
        return 0
    
    except Exception as e:
        print(f"Lỗi: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
