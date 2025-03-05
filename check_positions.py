#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
from datetime import datetime
from binance_api import BinanceAPI

def format_money(amount):
    return f"{float(amount):,.2f}"

def format_pct(pct):
    return f"{float(pct):+.2f}%"

def calculate_pnl_pct(entry_price, current_price, side, leverage=1):
    if side == 'LONG':
        return ((current_price - entry_price) / entry_price) * 100 * leverage
    else:
        return ((entry_price - current_price) / entry_price) * 100 * leverage

def main():
    print("===== KIỂM TRA VỊ THẾ ĐẦU TƯ BINANCE FUTURES =====")
    print(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    try:
        client = BinanceAPI()
        
        # Lấy thông tin tài khoản
        account = client.get_futures_account()
        
        # Lấy thông tin vị thế
        positions = client.get_futures_position_risk()
        
        # Lấy giá hiện tại
        tickers = {}
        ticker_data = client.get_price_ticker()
        if isinstance(ticker_data, list):
            for ticker in ticker_data:
                tickers[ticker['symbol']] = float(ticker['price'])
        
        # Lọc các vị thế đang mở
        open_positions = [p for p in positions if float(p['positionAmt']) != 0]
        
        # Hiển thị thông tin tài khoản
        print(f"Số dư tài khoản: {format_money(account['totalWalletBalance'])} USDT")
        print(f"Số dư khả dụng: {format_money(account['availableBalance'])} USDT")
        total_unrealized_pnl = sum(float(p['unRealizedProfit']) for p in positions)
        print(f"Tổng lãi/lỗ chưa thực hiện: {format_money(total_unrealized_pnl)} USDT")
        
        total_margin = sum(float(p['isolatedWallet']) for p in positions if p['isolated'] == 'true')
        print(f"Tổng margin đã sử dụng: {format_money(total_margin)} USDT")
        
        print("-" * 60)
        print(f"Số vị thế đang mở: {len(open_positions)}")
        
        if open_positions:
            print("\nCHI TIẾT VỊ THẾ:")
            
            for pos in open_positions:
                symbol = pos['symbol']
                side = 'LONG' if float(pos['positionAmt']) > 0 else 'SHORT'
                entry_price = float(pos['entryPrice'])
                current_price = tickers.get(symbol, entry_price)
                amount = abs(float(pos['positionAmt']))
                notional = amount * current_price
                leverage = int(float(pos['leverage']))
                margin = notional / leverage
                unrealized_pnl = float(pos['unRealizedProfit'])
                pnl_percent = calculate_pnl_pct(entry_price, current_price, side, leverage)
                liq_price = float(pos['liquidationPrice']) if float(pos['liquidationPrice']) > 0 else None
                
                # Tính khoảng cách đến giá thanh lý
                liq_distance = None
                if liq_price:
                    if side == 'LONG':
                        liq_distance = ((entry_price - liq_price) / entry_price) * 100
                    else:
                        liq_distance = ((liq_price - entry_price) / entry_price) * 100
                
                print(f"\033[1m{symbol}\033[0m ({side})")
                print(f"  Giá vào lệnh: {format_money(entry_price)} USDT")
                print(f"  Giá hiện tại: {format_money(current_price)} USDT")
                print(f"  Số lượng: {amount} ({format_money(notional)} USDT)")
                print(f"  Đòn bẩy: {leverage}x (Margin: {format_money(margin)} USDT)")
                
                # Hiển thị P/L với màu sắc
                if unrealized_pnl > 0:
                    print(f"  \033[32mLợi nhuận: +{format_money(unrealized_pnl)} USDT ({format_pct(pnl_percent)})\033[0m")
                else:
                    print(f"  \033[31mLợi nhuận: {format_money(unrealized_pnl)} USDT ({format_pct(pnl_percent)})\033[0m")
                
                # Hiển thị giá thanh lý nếu có
                if liq_price:
                    print(f"  Giá thanh lý: {format_money(liq_price)} USDT (cách {format_pct(liq_distance)})")
                
                # Hiển thị thông tin thêm từ vị thế
                if 'updateTime' in pos:
                    update_time = datetime.fromtimestamp(int(pos['updateTime'])/1000)
                    print(f"  Cập nhật cuối: {update_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                print("")
        else:
            print("\nKhông có vị thế đang mở.")
        
        return 0
    
    except Exception as e:
        print(f"Lỗi: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
