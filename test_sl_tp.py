#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test thiết lập thủ công SL/TP 
Phiên bản đơn giản để kiểm tra vấn đề lỗi 400 Bad Request
"""

import json
import time
import logging
from binance_api import BinanceAPI

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_sl_tp')

def main():
    # Khởi tạo API
    api = BinanceAPI()
    logger.info("Khởi tạo BinanceAPI thành công")
    
    # Lấy giá hiện tại của ETH
    symbol = 'ETHUSDT'
    try:
        ticker = api.get_symbol_ticker(symbol)
        current_price = float(ticker['price'])
        logger.info(f"Giá {symbol} hiện tại: {current_price}")
    except Exception as e:
        logger.error(f"Lỗi khi lấy giá: {str(e)}")
        return
    
    # Lấy vị thế hiện tại
    try:
        logger.info("Lấy thông tin vị thế...")
        positions = api.get_futures_position_risk()
        active_positions = [p for p in positions if abs(float(p.get('positionAmt', 0))) > 0]
        logger.info(f"Số vị thế đang mở: {len(active_positions)}")
        
        for pos in active_positions:
            pos_symbol = pos.get('symbol')
            side = 'LONG' if float(pos.get('positionAmt', 0)) > 0 else 'SHORT'
            entry_price = float(pos.get('entryPrice', 0))
            pos_amt = float(pos.get('positionAmt', 0))
            logger.info(f"Vị thế: {pos_symbol} {side}, Entry: {entry_price}, Qty: {pos_amt}")
            
            if pos_symbol == symbol:
                notional = pos_amt * current_price
                logger.info(f"Giá trị giao dịch {symbol}: {notional} USDT")
        
    except Exception as e:
        logger.error(f"Lỗi khi lấy thông tin vị thế: {str(e)}")
        return
    
    # Lấy các lệnh đang mở
    try:
        logger.info(f"Lấy các lệnh đang mở cho {symbol}...")
        orders = api.get_open_orders(symbol)
        
        logger.info(f"Số lệnh đang mở: {len(orders)}")
        for order in orders:
            order_type = order.get('type')
            order_side = order.get('side')
            order_price = order.get('price', 0)
            stop_price = order.get('stopPrice', 0)
            
            logger.info(f"Lệnh: {order_type} {order_side}, Giá: {order_price}, Stop: {stop_price}")
            
    except Exception as e:
        logger.error(f"Lỗi khi lấy các lệnh đang mở: {str(e)}")
    
    # Thử đặt lệnh Stop Loss
    try:
        logger.info("Thử đặt lệnh Stop Loss...")
        
        # Chọn vị thế ETH
        eth_pos = next((p for p in active_positions if p.get('symbol') == symbol), None)
        
        if not eth_pos:
            logger.error(f"Không tìm thấy vị thế {symbol} đang mở")
            return
            
        side = 'LONG' if float(eth_pos.get('positionAmt', 0)) > 0 else 'SHORT'
        close_side = 'SELL' if side == 'LONG' else 'BUY'
        entry_price = float(eth_pos.get('entryPrice', 0))
        
        # Tính SL 5% từ giá entry
        sl_percent = 5.0 
        if side == 'LONG':
            sl_price = entry_price * (1 - sl_percent / 100)
        else:
            sl_price = entry_price * (1 + sl_percent / 100)
        
        sl_price = round(sl_price, 2)  # Làm tròn 2 chữ số
        
        logger.info(f"Thử đặt SL cho {symbol} {side} tại giá {sl_price}")
        
        # Đặt lệnh SL
        try:
            result = api.futures_create_order(
                symbol=symbol,
                side=close_side,
                type='STOP_MARKET',
                stopPrice=sl_price,
                closePosition=True
            )
            
            logger.info(f"Đặt lệnh SL thành công: {json.dumps(result, indent=2)}")
            
        except Exception as e:
            logger.error(f"Lỗi khi đặt lệnh SL: {str(e)}")
            
        # Thử lại với việc chỉ định quantity thay vì closePosition
        try:
            logger.info("Thử đặt SL với quantity thay vì closePosition...")
            
            quantity = abs(float(eth_pos.get('positionAmt', 0)))
            
            result = api.futures_create_order(
                symbol=symbol,
                side=close_side,
                type='STOP_MARKET',
                stopPrice=sl_price,
                quantity=quantity
            )
            
            logger.info(f"Đặt lệnh SL với quantity thành công: {json.dumps(result, indent=2)}")
            
        except Exception as e:
            logger.error(f"Lỗi khi đặt lệnh SL với quantity: {str(e)}")
            
    except Exception as e:
        logger.error(f"Lỗi khi thực hiện thiết lập SL: {str(e)}")
    
    # Thử đặt lệnh Take Profit
    try:
        logger.info("Thử đặt lệnh Take Profit...")
        
        # Chọn vị thế ETH
        eth_pos = next((p for p in active_positions if p.get('symbol') == symbol), None)
        
        if not eth_pos:
            logger.error(f"Không tìm thấy vị thế {symbol} đang mở")
            return
            
        side = 'LONG' if float(eth_pos.get('positionAmt', 0)) > 0 else 'SHORT'
        close_side = 'SELL' if side == 'LONG' else 'BUY'
        entry_price = float(eth_pos.get('entryPrice', 0))
        
        # Tính TP 10% từ giá entry
        tp_percent = 10.0
        if side == 'LONG':
            tp_price = entry_price * (1 + tp_percent / 100)
        else:
            tp_price = entry_price * (1 - tp_percent / 100)
        
        tp_price = round(tp_price, 2)  # Làm tròn 2 chữ số
        
        logger.info(f"Thử đặt TP cho {symbol} {side} tại giá {tp_price}")
        
        # Đặt lệnh TP
        try:
            result = api.futures_create_order(
                symbol=symbol,
                side=close_side,
                type='TAKE_PROFIT_MARKET',
                stopPrice=tp_price,
                closePosition=True
            )
            
            logger.info(f"Đặt lệnh TP thành công: {json.dumps(result, indent=2)}")
            
        except Exception as e:
            logger.error(f"Lỗi khi đặt lệnh TP: {str(e)}")
            
        # Thử lại với việc chỉ định quantity thay vì closePosition
        try:
            logger.info("Thử đặt TP với quantity thay vì closePosition...")
            
            quantity = abs(float(eth_pos.get('positionAmt', 0)))
            
            result = api.futures_create_order(
                symbol=symbol,
                side=close_side,
                type='TAKE_PROFIT_MARKET',
                stopPrice=tp_price,
                quantity=quantity
            )
            
            logger.info(f"Đặt lệnh TP với quantity thành công: {json.dumps(result, indent=2)}")
            
        except Exception as e:
            logger.error(f"Lỗi khi đặt lệnh TP với quantity: {str(e)}")
            
    except Exception as e:
        logger.error(f"Lỗi khi thực hiện thiết lập TP: {str(e)}")
        
    logger.info("Kết thúc kiểm tra SL/TP")

if __name__ == "__main__":
    main()