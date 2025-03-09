#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import time
import logging
import json
from binance_api import BinanceAPI

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('test_orders')

def test_trailing_stop_order():
    """Kiểm tra khả năng tạo trailing stop order"""
    try:
        # Khởi tạo client API
        client = BinanceAPI()
        
        # 1. Lấy vị thế hiện tại
        positions = client.get_futures_position_risk()
        active_positions = [p for p in positions if float(p.get('positionAmt', 0)) > 0]
        
        if not active_positions:
            logger.warning("Không có vị thế LONG nào đang hoạt động để thử nghiệm")
            return False
            
        # Lấy vị thế đầu tiên để kiểm tra
        test_position = active_positions[0]
        symbol = test_position['symbol']
        position_amt = float(test_position['positionAmt'])
        entry_price = float(test_position['entryPrice'])
        
        logger.info(f"Đang thử tạo trailing stop cho vị thế {symbol}")
        logger.info(f"Số lượng: {position_amt}")
        logger.info(f"Giá vào: {entry_price}")
        
        # 2. Tính toán giá kích hoạt (activation price) - 5% trên giá vào
        activation_price = round(entry_price * 1.05, 2)
        callback_rate = 1.0  # 1% callback
        
        logger.info(f"Giá kích hoạt: {activation_price}")
        logger.info(f"Callback rate: {callback_rate}%")
        
        # 3. Thử tạo lệnh trailing stop
        logger.info("Đang gửi lệnh TRAILING_STOP_MARKET...")
        
        # Kiểm tra phương thức create_order trong API
        order_result = client.create_order(
            symbol=symbol,
            side="SELL",
            type="TRAILING_STOP_MARKET",
            quantity=position_amt,
            activation_price=activation_price,
            callback_rate=callback_rate,
            reduce_only=True
        )
        
        # Kiểm tra kết quả
        if order_result:
            # Kiểm tra nếu có lỗi trong kết quả
            if isinstance(order_result, dict) and order_result.get('error'):
                logger.error(f"Lỗi khi tạo lệnh TRAILING_STOP_MARKET: {order_result.get('error')}")
                return False
            else:    
                logger.info(f"Đã tạo lệnh TRAILING_STOP_MARKET thành công: {json.dumps(order_result, indent=2)}")
                return True
        else:
            logger.error("Thất bại khi tạo lệnh TRAILING_STOP_MARKET")
            return False
            
    except Exception as e:
        logger.error(f"Lỗi khi thử tạo lệnh: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("=== BẮT ĐẦU KIỂM TRA TẠO LỆNH ===")
    result = test_trailing_stop_order()
    if result:
        logger.info("=== KIỂM TRA THÀNH CÔNG ===")
    else:
        logger.error("=== KIỂM TRA THẤT BẠI ===")
        sys.exit(1)