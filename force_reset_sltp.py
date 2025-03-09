#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Force Reset SL/TP

Script này buộc thiết lập lại Stop Loss và Take Profit 
cho tất cả các vị thế đang mở
"""

import os
import sys
import logging
import traceback
from sltp_telegram_integration import EnhancedAutoSLTPManager

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("force_reset_sltp")

def main():
    """Hàm chính"""
    try:
        logger.info("Bắt đầu buộc thiết lập lại SL/TP...")
        
        # Tạo đối tượng EnhancedAutoSLTPManager với testnet=True
        manager = EnhancedAutoSLTPManager(testnet=True)
        
        # Cập nhật danh sách vị thế đang mở
        positions = manager.update_positions()
        
        # Nếu không có vị thế nào
        if not positions:
            logger.info("Không có vị thế nào đang mở.")
            return
        
        # Buộc thiết lập lại SL/TP cho từng vị thế
        for position in positions:
            symbol = position.get('symbol')
            
            try:
                # Buộc thiết lập lại với force=True
                logger.info(f"Đang reset SL/TP cho {symbol}...")
                success = manager.setup_initial_sltp(symbol, force=True)
                
                if success:
                    logger.info(f"Đã thiết lập lại SL/TP thành công cho {symbol}")
                else:
                    logger.error(f"Không thể thiết lập lại SL/TP cho {symbol}")
            except Exception as e:
                logger.error(f"Lỗi khi thiết lập lại SL/TP cho {symbol}: {str(e)}")
                traceback.print_exc()
        
        logger.info("Hoàn thành quá trình thiết lập lại SL/TP.")
    except Exception as e:
        logger.error(f"Lỗi khi chạy script: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()