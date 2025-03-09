#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import json
from binance_api import BinanceAPI

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("min_notional_checker")

def check_min_notional():
    """Kiểm tra min_notional cho các cặp tiền tệ trên Binance Futures."""
    try:
        # Khởi tạo API
        api = BinanceAPI(testnet=True)
        
        # Lấy thông tin exchange
        exchange_info = api.get_exchange_info()
        
        if not exchange_info or 'symbols' not in exchange_info:
            logger.error("Không thể lấy thông tin exchange")
            return False
        
        # Danh sách các loại bộ lọc cần kiểm tra
        filter_types = ['LOT_SIZE', 'MARKET_LOT_SIZE', 'MIN_NOTIONAL']
        
        # Danh sách các cặp tiền tệ chính
        main_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT", "DOGEUSDT", "XRPUSDT"]
        
        # Duyệt qua các cặp tiền tệ
        for symbol_info in exchange_info['symbols']:
            symbol = symbol_info['symbol']
            
            # Chỉ kiểm tra các cặp tiền tệ chính
            if symbol in main_symbols:
                logger.info(f"\n{'=' * 40}")
                logger.info(f"Thông tin cho {symbol}:")
                logger.info(f"{'=' * 40}")
                
                # Kiểm tra giá hiện tại
                ticker = api.get_symbol_ticker(symbol)
                current_price = float(ticker['price']) if ticker and 'price' in ticker else 0
                logger.info(f"Giá hiện tại: {current_price}")
                
                # Kiểm tra các bộ lọc
                for filter_type in filter_types:
                    for filter_item in symbol_info['filters']:
                        if filter_item['filterType'] == filter_type:
                            logger.info(f"\n{filter_type}:")
                            for key, value in filter_item.items():
                                if key != 'filterType':
                                    logger.info(f"  {key}: {value}")
                                    
                                    # Tính toán giá trị thực tế nếu là MIN_NOTIONAL
                                    if filter_type == 'MIN_NOTIONAL' and key == 'notional':
                                        min_notional = float(value)
                                        min_qty_by_notional = min_notional / current_price
                                        logger.info(f"  Số lượng tối thiểu tính theo min_notional: {min_qty_by_notional}")
                
                # Tìm min_qty từ LOT_SIZE
                min_qty = 0
                for filter_item in symbol_info['filters']:
                    if filter_item['filterType'] == 'LOT_SIZE':
                        min_qty = float(filter_item['minQty'])
                        break
                
                # Tính notional value với min_qty
                min_notional_value = min_qty * current_price
                logger.info(f"\nGiá trị notional tối thiểu với min_qty ({min_qty}): {min_notional_value}")
                
                # Tính lượng USD cần có khi sử dụng đòn bẩy 5x với rủi ro 2.5%
                leverage = 5
                risk_percent = 2.5
                balance_needed = (min_qty * current_price) / (leverage * (risk_percent / 100))
                logger.info(f"Số dư tài khoản cần thiết với đòn bẩy {leverage}x và rủi ro {risk_percent}%: {balance_needed} USDT")
                
                # Kiểm tra các mức đòn bẩy khác
                logger.info(f"\nYêu cầu số dư tối thiểu theo đòn bẩy (với rủi ro {risk_percent}%):")
                for lev in [1, 2, 5, 10, 20]:
                    balance = (min_qty * current_price) / (lev * (risk_percent / 100))
                    logger.info(f"  Đòn bẩy {lev}x: {balance} USDT")
        
        # Kiểm tra số dư tài khoản hiện tại
        account_balance = api.futures_account_balance()
        available_balance = 0
        
        for balance in account_balance:
            if balance.get('asset') == 'USDT':
                available_balance = float(balance.get('availableBalance', 0))
                break
        
        logger.info(f"\n{'=' * 40}")
        logger.info(f"Số dư khả dụng: {available_balance} USDT")
        logger.info(f"{'=' * 40}")
        
        return True

    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra min_notional: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Bắt đầu kiểm tra min_notional cho các cặp tiền tệ...")
    check_min_notional()