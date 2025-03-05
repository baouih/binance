#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
from datetime import datetime
from binance_api import BinanceAPI

def main():
    print("===== THÔNG TIN TÀI KHOẢN BINANCE FUTURES TESTNET =====")
    
    try:
        client = BinanceAPI()
        
        # Lấy thông tin tài khoản
        account = client.get_futures_account()
        
        print(f"Số dư tài khoản: {account.get('totalWalletBalance', 0)} USDT")
        print(f"Số dư khả dụng: {account.get('availableBalance', 0)} USDT")
        
        # Lấy thông tin vị thế
        positions = client.get_futures_position_risk()
        
        # Lọc các vị thế đang mở
        open_positions = [p for p in positions if float(p.get('positionAmt', 0)) != 0]
        
        print(f"Số vị thế đang mở: {len(open_positions)}")
        
        if open_positions:
            print("\nCHI TIẾT VỊ THẾ ĐANG MỞ:")
            for pos in open_positions:
                symbol = pos.get('symbol', 'UNKNOWN')
                side = 'LONG' if float(pos.get('positionAmt', 0)) > 0 else 'SHORT'
                entry_price = float(pos.get('entryPrice', 0))
                amount = abs(float(pos.get('positionAmt', 0)))
                leverage = pos.get('leverage', '1')
                mark_price = float(pos.get('markPrice', 0))
                unrealized_profit = pos.get('unrealizedProfit', 0)
                
                print(f"\nSymbol: {symbol}")
                print(f"Hướng: {side}")
                print(f"Giá vào lệnh: {entry_price}")
                print(f"Giá hiện tại: {mark_price}")
                print(f"Số lượng: {amount}")
                print(f"Đòn bẩy: {leverage}x")
                
                if 'liquidationPrice' in pos and float(pos['liquidationPrice']) > 0:
                    print(f"Giá thanh lý: {pos['liquidationPrice']}")
                
                if unrealized_profit:
                    print(f"Lãi/lỗ: {unrealized_profit}")
        else:
            print("Không có vị thế đang mở.")
        
        return 0
    
    except Exception as e:
        print(f"Lỗi: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
