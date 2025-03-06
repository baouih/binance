#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script xóa và đặt lại SL/TP cho các vị thế hiện tại
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Optional

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('reset_sltp')

# Thêm thư mục gốc vào sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from binance_api import BinanceAPI

def reset_sltp_for_all_positions(testnet=True):
    """
    Xóa và đặt lại SL/TP cho tất cả các vị thế
    
    Args:
        testnet (bool): Sử dụng testnet hay không
    """
    binance_api = BinanceAPI(testnet=testnet)
    
    # Lấy vị thế đang mở
    positions = binance_api.futures_get_position()
    active_positions = [p for p in positions if abs(float(p.get('positionAmt', 0))) > 0]
    
    if not active_positions:
        logger.info("Không có vị thế nào đang mở")
        return
    
    logger.info(f"Tìm thấy {len(active_positions)} vị thế đang mở")
    
    # Tải cấu hình
    try:
        with open('configs/profit_manager_config.json', 'r') as f:
            profit_config = json.load(f)
    except Exception as e:
        logger.warning(f"Không thể tải cấu hình profit manager: {str(e)}")
        profit_config = {}
    
    for position in active_positions:
        symbol = position.get('symbol')
        position_amt = float(position.get('positionAmt', 0))
        side = 'LONG' if position_amt > 0 else 'SHORT'
        entry_price = float(position.get('entryPrice', 0))
        leverage = int(position.get('leverage', 1))
        
        # Bỏ qua các vị thế có lượng = 0
        if abs(position_amt) <= 0:
            continue
            
        logger.info(f"Xử lý vị thế {symbol} {side}: Entry price={entry_price}")
        
        # Lấy giá hiện tại
        current_price = float(binance_api.get_symbol_ticker(symbol).get('price', 0))
        logger.info(f"Giá hiện tại của {symbol}: {current_price}")
        
        # Xóa tất cả lệnh cũ
        try:
            cancel_result = binance_api.futures_cancel_all_orders(symbol)
            logger.info(f"Đã xóa tất cả lệnh cho {symbol}: {cancel_result}")
        except Exception as e:
            logger.error(f"Lỗi khi xóa lệnh cho {symbol}: {str(e)}")
            continue
        
        # Đợi 1s để đảm bảo các lệnh đã được xóa hoàn toàn
        time.sleep(1)
        
        # Tính toán SL mới
        max_sl_percent = 5.0  # Tối đa 5% từ giá entry
        sl_percent = 2.0  # Mặc định 2%
        sl_percent_adjusted = min(sl_percent, max_sl_percent)
        
        if side == 'LONG':
            sl_price = entry_price * (1 - sl_percent_adjusted / 100)
            min_sl_price = current_price * 0.9  # Không thấp hơn 90% giá hiện tại
            sl_price = max(sl_price, min_sl_price)
        else:
            sl_price = entry_price * (1 + sl_percent_adjusted / 100)
            max_sl_price = current_price * 1.1  # Không cao hơn 110% giá hiện tại
            sl_price = min(sl_price, max_sl_price)
        
        # Làm tròn giá
        sl_price = round(sl_price, 1)
        
        # Tính toán TP mới
        max_tp_percent = 10.0  # Tối đa 10% từ giá entry
        
        # Lấy target profit từ cấu hình
        target_profit = profit_config.get('target_profit', {}).get('profit_target', 2.0)
        small_account_settings = profit_config.get('small_account_settings', {})
        if small_account_settings.get('enabled', False):
            if symbol == 'BTCUSDT':
                target_profit = small_account_settings.get('btc_profit_target', 1.5)
            elif symbol == 'ETHUSDT':
                target_profit = small_account_settings.get('eth_profit_target', 2.0)
            else:
                target_profit = small_account_settings.get('altcoin_profit_target', 3.0)
        
        # Điều chỉnh target dựa trên đòn bẩy
        effective_target = target_profit / leverage if leverage > 1 else target_profit
        tp_percent = effective_target  # Từ cấu hình
        tp_percent_adjusted = min(tp_percent, max_tp_percent)
        
        if side == 'LONG':
            tp_price = entry_price * (1 + tp_percent_adjusted / 100)
            # Đảm bảo TP LONG cao hơn giá hiện tại và không quá cao
            min_tp_price = current_price * 1.01  # Ít nhất 1% cao hơn giá hiện tại
            max_tp_price = current_price * 1.15  # Không cao hơn 115% giá hiện tại
            tp_price = max(min_tp_price, min(tp_price, max_tp_price))
        else:
            tp_price = entry_price * (1 - tp_percent_adjusted / 100)
            # Đảm bảo TP SHORT thấp hơn giá hiện tại và không quá thấp
            max_tp_price = current_price * 0.99  # Ít nhất 1% thấp hơn giá hiện tại
            min_tp_price = current_price * 0.85  # Không thấp hơn 85% giá hiện tại
            tp_price = min(max_tp_price, max(tp_price, min_tp_price))
        
        # Làm tròn giá
        tp_price = round(tp_price, 1)
        
        # Đặt SL mới
        try:
            sl_result = binance_api.futures_set_stop_loss(symbol, side, sl_price)
            logger.info(f"Đã đặt SL mới cho {symbol} {side} tại giá {sl_price}")
        except Exception as e:
            logger.error(f"Lỗi khi đặt SL cho {symbol}: {str(e)}")
        
        # Đặt TP mới
        try:
            tp_result = binance_api.futures_set_take_profit(symbol, side, tp_price)
            logger.info(f"Đã đặt TP mới cho {symbol} {side} tại giá {tp_price}")
        except Exception as e:
            logger.error(f"Lỗi khi đặt TP cho {symbol}: {str(e)}")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Xóa và đặt lại SL/TP cho các vị thế đang mở')
    parser.add_argument('--testnet', action='store_true', help='Sử dụng testnet')
    args = parser.parse_args()
    
    reset_sltp_for_all_positions(testnet=args.testnet)

if __name__ == "__main__":
    main()