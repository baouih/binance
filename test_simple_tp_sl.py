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

def test_take_profit_and_stop_loss():
    """Kiểm tra khả năng tạo take profit và stop loss thay cho trailing stop"""
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
        
        logger.info(f"Đang thử tạo TP/SL cho vị thế {symbol}")
        logger.info(f"Số lượng: {position_amt}")
        logger.info(f"Giá vào: {entry_price}")
        
        # 2. Tính toán giá TP/SL
        tp_price = round(entry_price * 1.05, 2)  # +5% từ giá vào
        sl_price = round(entry_price * 0.97, 2)  # -3% từ giá vào
        
        logger.info(f"Giá take profit: {tp_price}")
        logger.info(f"Giá stop loss: {sl_price}")
        
        # 3. Thử tạo lệnh take profit
        logger.info("Đang gửi lệnh TAKE_PROFIT_MARKET...")
        
        # Sử dụng 50% vị thế cho TP
        tp_quantity = round(position_amt / 2, 3)
        
        # Binance Futures yêu cầu thêm tham số working_type và price cho TAKE_PROFIT orders
        tp_order = client.create_order(
            symbol=symbol,
            side="SELL",
            type="TAKE_PROFIT", # Sử dụng TAKE_PROFIT thay vì TAKE_PROFIT_MARKET
            quantity=tp_quantity,
            stop_price=tp_price,
            price=tp_price*0.99, # Cần thêm giá limit thấp hơn stop price
            time_in_force="GTC",
            working_type="MARK_PRICE",
            reduce_only=True
        )
        
        # Kiểm tra kết quả TP
        if isinstance(tp_order, dict) and tp_order.get('error'):
            logger.error(f"Lỗi khi tạo lệnh TAKE_PROFIT: {tp_order.get('error')}")
            success_tp = False
        else:
            logger.info(f"Đã tạo lệnh TAKE_PROFIT thành công: {json.dumps(tp_order, indent=2)}")
            success_tp = True
            
        # 4. Thử tạo lệnh stop loss
        logger.info("Đang gửi lệnh STOP...")
        
        # Sử dụng toàn bộ vị thế còn lại cho SL
        sl_quantity = position_amt - tp_quantity if success_tp else position_amt
        
        # Binance Futures yêu cầu thêm tham số working_type cho STOP orders
        sl_order = client.create_order(
            symbol=symbol,
            side="SELL",
            type="STOP",
            quantity=sl_quantity,
            stop_price=sl_price,
            price=sl_price*1.01, # Cần thêm giá limit cao hơn stop price
            time_in_force="GTC",
            working_type="MARK_PRICE",
            reduce_only=True
        )
        
        # Kiểm tra kết quả SL
        if isinstance(sl_order, dict) and sl_order.get('error'):
            logger.error(f"Lỗi khi tạo lệnh STOP: {sl_order.get('error')}")
            success_sl = False
        else:
            logger.info(f"Đã tạo lệnh STOP thành công: {json.dumps(sl_order, indent=2)}")
            success_sl = True
            
        return success_tp or success_sl
            
    except Exception as e:
        logger.error(f"Lỗi khi thử tạo lệnh TP/SL: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("=== BẮT ĐẦU KIỂM TRA TẠO LỆNH TP/SL ===")
    result = test_take_profit_and_stop_loss()
    if result:
        logger.info("=== KIỂM TRA THÀNH CÔNG ===")
    else:
        logger.error("=== KIỂM TRA THẤT BẠI ===")
        sys.exit(1)