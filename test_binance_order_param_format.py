#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import logging
import time
from binance_api import BinanceAPI
from reference_order_format import (
    MARKET_ORDER, 
    STOP_MARKET_ORDER, 
    TAKE_PROFIT_MARKET_ORDER
)

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('test_order_format')

def test_market_order():
    """Kiểm tra lệnh MARKET với định dạng tham chiếu"""
    client = BinanceAPI()
    
    # Lấy vị thế hiện tại
    positions = client.get_futures_position_risk()
    active_positions = [p for p in positions if float(p.get('positionAmt', 0)) != 0]
    
    if not active_positions:
        logger.warning("Không có vị thế hiện tại để đóng. Thử tạo lệnh mới...")
        # Tạo một lệnh market BUY nhỏ
        params = MARKET_ORDER.copy()
        params["quantity"] = 0.001  # Số lượng rất nhỏ
    else:
        # Lấy vị thế đầu tiên để đóng một phần
        position = active_positions[0]
        symbol = position['symbol']
        position_amt = float(position['positionAmt'])
        
        # Tính toán lệnh đóng một phần vị thế (10%)
        close_amt = round(abs(position_amt) * 0.1, 3)
        side = "SELL" if position_amt > 0 else "BUY"
        
        params = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": close_amt,
            "reduceOnly": "true"  # Chú ý: sử dụng chuỗi "true" thay vì boolean True
        }
    
    # Log định dạng lệnh cuối cùng
    logger.info(f"Định dạng lệnh: {json.dumps(params, indent=2)}")
    
    # Gửi lệnh
    try:
        result = client._request('POST', 'order', params, signed=True, version='v1')
        if result.get('error'):
            logger.error(f"Lỗi: {result.get('error')}")
            return False
        else:
            logger.info(f"Kết quả: {json.dumps(result, indent=2)}")
            return True
    except Exception as e:
        logger.error(f"Lỗi: {str(e)}")
        return False

def test_tp_sl_format():
    """Kiểm tra định dạng lệnh TP/SL với định dạng tham chiếu"""
    client = BinanceAPI()
    
    # Lấy vị thế hiện tại
    positions = client.get_futures_position_risk()
    active_positions = [p for p in positions if float(p.get('positionAmt', 0)) > 0]
    
    if not active_positions:
        logger.warning("Không có vị thế LONG hiện tại để đặt TP/SL")
        return False
    
    # Lấy vị thế đầu tiên
    position = active_positions[0]
    symbol = position['symbol']
    position_amt = float(position['positionAmt'])
    entry_price = float(position['entryPrice'])
    
    # Tính TP/SL
    tp_price = round(entry_price * 1.05, 2)  # +5%
    sl_price = round(entry_price * 0.97, 2)  # -3%
    
    # 1. Thử lệnh Take Profit (sử dụng 50% vị thế)
    tp_qty = round(position_amt / 2, 3)
    
    tp_params = {
        "symbol": symbol,
        "side": "SELL",
        "type": "TAKE_PROFIT_MARKET",
        "stopPrice": tp_price,
        "quantity": tp_qty,
        "reduceOnly": "true",  # Chuỗi "true", không phải boolean
        "workingType": "MARK_PRICE"
    }
    
    # 2. Thử lệnh Stop Loss (sử dụng 50% vị thế còn lại)
    sl_params = {
        "symbol": symbol,
        "side": "SELL",
        "type": "STOP_MARKET",
        "stopPrice": sl_price,
        "quantity": tp_qty,
        "reduceOnly": "true",  # Chuỗi "true", không phải boolean
        "workingType": "MARK_PRICE"
    }
    
    # Log định dạng lệnh
    logger.info(f"Định dạng Take Profit: {json.dumps(tp_params, indent=2)}")
    logger.info(f"Định dạng Stop Loss: {json.dumps(sl_params, indent=2)}")
    
    # Gửi lệnh TP
    try:
        logger.info("Đang gửi lệnh Take Profit...")
        tp_result = client._request('POST', 'order', tp_params, signed=True, version='v1')
        if tp_result.get('error'):
            logger.error(f"Lỗi TP: {tp_result.get('error')}")
            tp_success = False
        else:
            logger.info(f"Kết quả TP: {json.dumps(tp_result, indent=2)}")
            tp_success = True
            
        # Đợi một chút trước khi gửi lệnh tiếp theo
        time.sleep(1)
        
        # Gửi lệnh SL
        logger.info("Đang gửi lệnh Stop Loss...")
        sl_result = client._request('POST', 'order', sl_params, signed=True, version='v1')
        if sl_result.get('error'):
            logger.error(f"Lỗi SL: {sl_result.get('error')}")
            sl_success = False
        else:
            logger.info(f"Kết quả SL: {json.dumps(sl_result, indent=2)}")
            sl_success = True
            
        return tp_success or sl_success
    except Exception as e:
        logger.error(f"Lỗi: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("=== KIỂM TRA ĐỊNH DẠNG THAM SỐ LỆNH BINANCE FUTURES ===")
    
    # 1. Thử nghiệm lệnh MARKET
    logger.info("--- Kiểm tra lệnh MARKET ---")
    market_result = test_market_order()
    
    # 2. Thử nghiệm lệnh TP/SL
    logger.info("--- Kiểm tra lệnh TP/SL ---")
    tp_sl_result = test_tp_sl_format()
    
    if market_result or tp_sl_result:
        logger.info("=== KIỂM TRA THÀNH CÔNG ===")
    else:
        logger.error("=== KIỂM TRA THẤT BẠI ===")
        sys.exit(1)