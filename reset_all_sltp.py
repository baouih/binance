#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Reset All SL/TP Orders

Script này buộc thiết lập lại Stop Loss và Take Profit 
cho tất cả các vị thế đang mở, bất kể trạng thái hiện tại của chúng.
"""

import os
import sys
import time
import logging
import argparse
import traceback
from typing import Dict, Any, List

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('reset_sltp.log')
    ]
)
logger = logging.getLogger('reset_sltp')

# Đặt đường dẫn hiện tại vào sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Import các module cần thiết
from binance_api import BinanceAPI
from sltp_telegram_integration import EnhancedAutoSLTPManager

def get_all_positions(api: BinanceAPI) -> List[Dict[str, Any]]:
    """Lấy danh sách tất cả các vị thế đang mở
    
    Args:
        api: Đối tượng BinanceAPI
        
    Returns:
        List[Dict[str, Any]]: Danh sách các vị thế
    """
    try:
        positions = api.get_futures_position_risk()
        active_positions = [p for p in positions if abs(float(p.get('positionAmt', 0))) > 0]
        logger.info(f"Đã tìm thấy {len(active_positions)} vị thế đang mở")
        return active_positions
    except Exception as e:
        logger.error(f"Lỗi khi lấy thông tin vị thế: {str(e)}")
        return []

def reset_sltp_for_position(manager: EnhancedAutoSLTPManager, position: Dict[str, Any]) -> bool:
    """Thiết lập lại SL/TP cho một vị thế
    
    Args:
        manager: Đối tượng EnhancedAutoSLTPManager
        position: Thông tin vị thế
        
    Returns:
        bool: True nếu thành công
    """
    try:
        symbol = position.get('symbol')
        amt = float(position.get('positionAmt', 0))
        
        if abs(amt) == 0:
            logger.info(f"Bỏ qua {symbol}, không có vị thế mở")
            return False
        
        logger.info(f"Đang reset SL/TP cho {symbol} với số lượng {abs(amt)}")
        
        # Thêm vị thế vào active_positions để setup_initial_sltp có thể tìm thấy
        manager.active_positions[symbol] = position
        
        # Buộc thiết lập lại SL/TP với force=True
        result = manager.setup_initial_sltp(symbol, force=True)
        
        if result:
            logger.info(f"Đã thiết lập lại SL/TP cho {symbol} thành công")
        else:
            logger.error(f"Không thể thiết lập lại SL/TP cho {symbol}")
        
        return result
    except Exception as e:
        logger.error(f"Lỗi khi thiết lập lại SL/TP cho {position.get('symbol')}: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Reset all SL/TP orders')
    parser.add_argument('--testnet', action='store_true', help='Sử dụng Binance Testnet')
    args = parser.parse_args()
    
    try:
        logger.info("Bắt đầu reset SL/TP cho tất cả các vị thế...")
        
        # Khởi tạo manager
        manager = EnhancedAutoSLTPManager(testnet=True if args.testnet else False)
        
        # Lấy danh sách vị thế
        positions = get_all_positions(manager.api)
        
        if not positions:
            logger.info("Không có vị thế nào, kết thúc")
            return
        
        # Thiết lập lại SL/TP cho từng vị thế
        success_count = 0
        for position in positions:
            if reset_sltp_for_position(manager, position):
                success_count += 1
            
            # Tạm nghỉ để tránh rate limit
            time.sleep(1)
        
        logger.info(f"Hoàn thành: đã reset {success_count}/{len(positions)} vị thế")
        
    except Exception as e:
        logger.error(f"Lỗi không mong muốn: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()