#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script để gỡ lỗi API Binance cụ thể
"""

import logging
import json
import sys
import time
from binance_api import BinanceAPI
from binance_api_fixes import apply_fixes_to_api

# Thiết lập logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("debug_api")

def setup_api():
    """Khởi tạo API với debug mode"""
    api = BinanceAPI(None, None, testnet=True)
    # Áp dụng bản vá
    apply_fixes_to_api(api)
    return api

def get_api_error_details(api, symbol="ETHUSDT"):
    """Lấy thông tin chi tiết về lỗi API"""
    try:
        # 1. Kiểm tra thông tin symbol
        logger.info(f"Kiểm tra thông tin chi tiết về {symbol}...")
        exchange_info = api._request('GET', 'exchangeInfo', {}, version='v1')
        
        symbol_info = None
        for s in exchange_info.get('symbols', []):
            if s.get('symbol') == symbol:
                symbol_info = s
                break
                
        if symbol_info:
            logger.info(f"Chi tiết {symbol}: {json.dumps(symbol_info, indent=2)}")
            
            # Lấy thông tin quan trọng
            price_precision = symbol_info.get('pricePrecision', 2)
            qty_precision = symbol_info.get('quantityPrecision', 3)
            
            logger.info(f"Precision - Giá: {price_precision}, Số lượng: {qty_precision}")
        else:
            logger.error(f"Không tìm thấy thông tin của {symbol}")
            
        # 2. Kiểm tra vị thế hiện tại
        positions = api.get_futures_position_risk()
        pos = None
        
        for p in positions:
            if p.get('symbol') == symbol:
                pos = p
                break
                
        if pos:
            logger.info(f"Vị thế hiện tại: {json.dumps(pos, indent=2)}")
        else:
            logger.error(f"Không tìm thấy vị thế cho {symbol}")
            
        # 3. Kiểm tra lệnh đang mở
        open_orders = api.get_open_orders(symbol)
        logger.info(f"Lệnh đang mở: {json.dumps(open_orders, indent=2)}")
        
        # 4. Kiểm tra hedge mode
        try:
            hedge_setting = api._request('GET', 'positionSide/dual', {}, signed=True, version='v1')
            logger.info(f"Cài đặt hedge mode: {hedge_setting}")
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra hedge mode: {str(e)}")
            
        # 5. Thử đặt lệnh SL với các tham số khác nhau
        # CẢNH BÁO: Đoạn code này chỉ dành cho debug, không sử dụng trong sản phẩm
        pos_amt = float(pos.get('positionAmt', 0)) if pos else 0.01
        entry_price = float(pos.get('entryPrice', 0)) if pos else 0
        
        if abs(pos_amt) > 0:
            side = 'SELL' if pos_amt > 0 else 'BUY'
            
            # 5.1 Thử với positionSide
            try:
                logger.info("Thử đặt SL với positionSide...")
                sl_price = entry_price * 0.97 if pos_amt > 0 else entry_price * 1.03
                sl_price = round(sl_price, 2)
                
                sl_result = api.futures_create_order(
                    symbol=symbol,
                    side=side, 
                    type='STOP_MARKET',
                    stopPrice=sl_price,
                    quantity=abs(pos_amt),
                    positionSide='LONG' if pos_amt > 0 else 'SHORT',
                    workingType='MARK_PRICE'
                )
                
                logger.info(f"Kết quả SL với positionSide: {sl_result}")
            except Exception as e:
                logger.error(f"Lỗi khi đặt SL với positionSide: {str(e)}")
                
            # 5.2 Thử với reduceOnly
            try:
                logger.info("Thử đặt SL với reduceOnly...")
                sl_price = entry_price * 0.96 if pos_amt > 0 else entry_price * 1.04
                sl_price = round(sl_price, 2)
                
                sl_result = api.futures_create_order(
                    symbol=symbol,
                    side=side, 
                    type='STOP_MARKET',
                    stopPrice=sl_price,
                    quantity=abs(pos_amt),
                    reduceOnly='true',
                    workingType='MARK_PRICE'
                )
                
                logger.info(f"Kết quả SL với reduceOnly: {sl_result}")
            except Exception as e:
                logger.error(f"Lỗi khi đặt SL với reduceOnly: {str(e)}")
                
            # 5.3 Thử với closePosition
            try:
                logger.info("Thử đặt SL với closePosition...")
                sl_price = entry_price * 0.95 if pos_amt > 0 else entry_price * 1.05
                sl_price = round(sl_price, 2)
                
                sl_result = api.futures_create_order(
                    symbol=symbol,
                    side=side, 
                    type='STOP_MARKET',
                    stopPrice=sl_price,
                    closePosition='true',
                    workingType='MARK_PRICE'
                )
                
                logger.info(f"Kết quả SL với closePosition: {sl_result}")
            except Exception as e:
                logger.error(f"Lỗi khi đặt SL với closePosition: {str(e)}")
        else:
            logger.warning(f"Không có vị thế đang mở cho {symbol}, không thể test đặt SL/TP")
        
    except Exception as e:
        logger.error(f"Lỗi trong quá trình debug: {str(e)}")

def main():
    api = setup_api()
    
    # Kiểm tra kết nối
    try:
        account_info = api.futures_account_balance()
        logger.info(f"Kết nối API thành công! Balance: {account_info[0].get('balance')} USDT")
    except Exception as e:
        logger.error(f"Lỗi kết nối API: {str(e)}")
        return
        
    # Debug lỗi cho ETHUSDT
    symbol = "ETHUSDT"
    get_api_error_details(api, symbol)
    
if __name__ == "__main__":
    main()