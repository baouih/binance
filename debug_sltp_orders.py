#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import argparse
from binance_api import BinanceAPI

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('debug_sltp_orders')

def load_account_config():
    """Tải cấu hình tài khoản từ file"""
    try:
        with open('account_config.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình tài khoản: {str(e)}")
        return {}

def debug_create_orders(symbol, testnet=True, reduce_only=True):
    """
    Debug việc tạo lệnh SL/TP với nhiều tham số khác nhau
    """
    # Khởi tạo API
    config = load_account_config()
    api_key = config.get('api_key', '')
    api_secret = config.get('api_secret', '')
    
    api = BinanceAPI(api_key, api_secret, testnet=testnet)
    
    # Lấy thông tin vị thế
    positions = api.futures_get_position(symbol)
    active_positions = [p for p in positions if float(p.get('positionAmt', 0)) != 0]
    
    if not active_positions:
        logger.info(f"Không có vị thế đang mở cho {symbol}")
        return
    
    for position in active_positions:
        symbol = position.get('symbol')
        pos_amount = float(position.get('positionAmt', 0))
        entry_price = float(position.get('entryPrice', 0))
        
        # Xác định side của vị thế
        side = 'LONG' if pos_amount > 0 else 'SHORT'
        close_side = 'SELL' if side == 'LONG' else 'BUY'
        
        # Tính toán SL/TP
        sl_percent = 2.0
        tp_percent = 3.0
        
        if side == 'LONG':
            sl_price = round(entry_price * (1 - sl_percent / 100), 2)
            tp_price = round(entry_price * (1 + tp_percent / 100), 2)
        else:
            sl_price = round(entry_price * (1 + sl_percent / 100), 2)
            tp_price = round(entry_price * (1 - tp_percent / 100), 2)
        
        quantity = abs(pos_amount)
        
        logger.info(f"Vị thế: {symbol} {side} - Entry price: {entry_price}, Quantity: {quantity}")
        logger.info(f"  → SL price: {sl_price}, TP price: {tp_price}")
        
        # Debug các tham số khác nhau - SL
        try:
            logger.info(f"Thử đặt lệnh SL với reduceOnly={reduce_only}")
            # Thử sử dụng cấu trúc mới, bỏ timeInForce
            result = api.futures_create_order(
                symbol=symbol,
                side=close_side,
                type='STOP_MARKET',
                stopPrice=sl_price,
                quantity=quantity,
                reduceOnly=reduce_only
            )
            logger.info(f"Kết quả đặt SL: {json.dumps(result, indent=2)}")
        except Exception as e:
            error_details = getattr(e, 'response', None)
            if error_details and hasattr(error_details, 'text'):
                error_text = error_details.text
                logger.error(f"Lỗi khi đặt SL: {str(e)}")
                logger.error(f"Chi tiết lỗi: {error_text}")
            else:
                logger.error(f"Lỗi khi đặt SL: {str(e)}")
        
        try:
            logger.info(f"Thử đặt lệnh TP với reduceOnly={reduce_only}")
            result = api.futures_create_order(
                symbol=symbol,
                side=close_side,
                type='TAKE_PROFIT_MARKET',
                stopPrice=tp_price,
                quantity=quantity,
                reduceOnly=reduce_only,
                timeInForce="GTC"
            )
            logger.info(f"Kết quả đặt TP: {json.dumps(result, indent=2)}")
        except Exception as e:
            error_details = getattr(e, 'response', None)
            if error_details and hasattr(error_details, 'text'):
                error_text = error_details.text
                logger.error(f"Lỗi khi đặt TP: {str(e)}")
                logger.error(f"Chi tiết lỗi: {error_text}")
            else:
                logger.error(f"Lỗi khi đặt TP: {str(e)}")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description="Debug việc tạo lệnh SL/TP với tham số khác nhau")
    parser.add_argument("--symbol", help="Symbol cần debug", default="BTCUSDT")
    parser.add_argument("--testnet", help="Sử dụng testnet", action="store_true", default=True)
    parser.add_argument("--no-reduce-only", help="Không dùng tham số reduceOnly", action="store_true")
    args = parser.parse_args()
    
    reduce_only = not args.no_reduce_only
    
    debug_create_orders(args.symbol, args.testnet, reduce_only)

if __name__ == "__main__":
    main()