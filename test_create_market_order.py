#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import logging
from binance_api import BinanceAPI

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('test_create_order')

def test_create_market_order():
    """Thử nghiệm tạo một lệnh market đơn giản"""
    try:
        # Khởi tạo client API
        client = BinanceAPI()
        
        # Lấy vị thế hiện tại
        positions = client.get_futures_position_risk()
        active_positions = [p for p in positions if float(p.get('positionAmt', 0)) != 0]
        
        if not active_positions:
            logger.warning("Không có vị thế nào đang hoạt động để thử nghiệm")
            # Thử tạo một lệnh market mới
            logger.info("Thử tạo lệnh MARKET mua mới...")
            
            order = client.create_order(
                symbol="BTCUSDT",
                side="BUY",
                type="MARKET",
                quantity=0.001
            )
            
            if isinstance(order, dict) and order.get('error'):
                logger.error(f"Lỗi khi tạo lệnh MARKET: {order.get('error')}")
                return False
            else:
                logger.info(f"Đã tạo lệnh MARKET thành công: {json.dumps(order, indent=2)}")
                return True
        else:
            # Lấy vị thế đầu tiên để kiểm tra
            test_position = active_positions[0]
            symbol = test_position['symbol']
            position_amt = float(test_position['positionAmt'])
            entry_price = float(test_position['entryPrice'])
            
            logger.info(f"Vị thế hiện tại: {symbol}")
            logger.info(f"Số lượng: {position_amt}")
            logger.info(f"Giá vào: {entry_price}")
            
            # Thử đóng một phần của vị thế bằng lệnh MARKET
            close_amt = round(abs(position_amt) * 0.1, 3)  # Đóng 10% vị thế
            
            logger.info(f"Thử đóng {close_amt} {symbol} bằng lệnh MARKET...")
            
            side = "SELL" if position_amt > 0 else "BUY"
            
            order = client.create_order(
                symbol=symbol,
                side=side,
                type="MARKET",
                quantity=close_amt,
                reduceOnly=True
            )
            
            if isinstance(order, dict) and order.get('error'):
                logger.error(f"Lỗi khi tạo lệnh MARKET đóng vị thế: {order.get('error')}")
                return False
            else:
                logger.info(f"Đã tạo lệnh MARKET đóng vị thế thành công: {json.dumps(order, indent=2)}")
                return True
    except Exception as e:
        logger.error(f"Lỗi khi thử tạo lệnh MARKET: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("=== BẮT ĐẦU KIỂM TRA TẠO LỆNH MARKET ===")
    result = test_create_market_order()
    if result:
        logger.info("=== KIỂM TRA THÀNH CÔNG ===")
    else:
        logger.error("=== KIỂM TRA THẤT BẠI ===")
        sys.exit(1)