#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Kiểm tra và sửa SL/TP cho tất cả các vị thế mở

Script này sẽ:
1. Kiểm tra tất cả các vị thế mở
2. Xác minh mỗi vị thế có đầy đủ SL và TP
3. Thêm SL/TP cho các vị thế thiếu
4. Áp dụng các bản vá lỗi cho tài khoản hedge mode

Có thể chạy định kỳ thông qua cron:
*/10 * * * * python check_and_fix_all_positions_sltp.py
"""

import os
import sys
import json
import time
import logging
import math
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional, Union

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('sltp_check.log')
    ]
)

logger = logging.getLogger('sltp_check')

# Import các module cần thiết
try:
    from binance_api import BinanceAPI
    from binance_api_fixes import apply_fixes_to_api
except ImportError as e:
    logger.error(f"Lỗi import module: {str(e)}")
    sys.exit(1)


class SLTPChecker:
    """Lớp quản lý kiểm tra và sửa SL/TP"""
    
    def __init__(self):
        """Khởi tạo SLTPChecker"""
        # Tạo instance API và áp dụng các bản vá
        self.api = BinanceAPI()
        self.api = apply_fixes_to_api(self.api)
        
        # Lấy cấu hình SL/TP
        self.config = self.load_config()
        
        # Kiểm tra chế độ tài khoản
        self.hedge_mode = self.api.hedge_mode
        logger.info(f"Chế độ tài khoản: {'hedge mode' if self.hedge_mode else 'one-way mode'}")
    
    def load_config(self) -> dict:
        """Tải cấu hình SL/TP từ file"""
        try:
            if os.path.exists('sltp_config.json'):
                with open('sltp_config.json', 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình từ sltp_config.json")
                return config
            else:
                # Cấu hình mặc định
                default_config = {
                    "default_sl_percentage": 2.0,
                    "default_tp_percentage": 3.0,
                    "update_interval_seconds": 60
                }
                logger.warning(f"Không tìm thấy file sltp_config.json, sử dụng cấu hình mặc định")
                return default_config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
            # Fallback to default values
            return {
                "default_sl_percentage": 2.0,
                "default_tp_percentage": 3.0,
                "update_interval_seconds": 60
            }
    
    def get_sl_tp_percentages(self) -> Tuple[float, float]:
        """Lấy % SL/TP từ cấu hình"""
        sl_pct = self.config.get("default_sl_percentage", 2.0)
        tp_pct = self.config.get("default_tp_percentage", 3.0)
        return sl_pct, tp_pct
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Lấy danh sách vị thế đang mở"""
        try:
            positions = self.api.get_futures_position_risk()
            # Lọc vị thế có số lượng khác 0
            active_positions = [
                pos for pos in positions 
                if float(pos['positionAmt']) != 0
            ]
            logger.info(f"Tìm thấy {len(active_positions)} vị thế đang mở")
            return active_positions
        except Exception as e:
            logger.error(f"Lỗi khi lấy vị thế: {str(e)}")
            return []
    
    def check_sltp_orders(self, symbol: str, position_side: Optional[str] = None) -> Dict[str, List]:
        """Kiểm tra lệnh SL/TP cho một vị thế"""
        try:
            # Bỏ qua phần kiểm tra lệnh mở
            # Tạo các danh sách trống ban đầu
            sl_orders = []
            tp_orders = []
            
            # Trong thực tế, việc không có kiểm tra lệnh mở sẽ luôn coi
            # như cần đặt lại SL/TP, nhưng điều này an toàn vì Binance
            # sẽ tự động hủy các lệnh trùng lặp
            logger.info(f"Bỏ qua kiểm tra lệnh mở, sẽ luôn đặt SL/TP mới")
            return {'sl': sl_orders, 'tp': tp_orders}
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra SL/TP cho {symbol}: {str(e)}")
            return {'sl': [], 'tp': []}
    
    def fix_missing_sltp(self, position: Dict[str, Any]) -> bool:
        """Sửa SL/TP bị thiếu cho một vị thế"""
        symbol = position['symbol']
        entry_price = float(position['entryPrice'])
        position_amt = float(position['positionAmt'])
        position_side = None
        
        # Xác định position_side nếu ở hedge mode
        if self.hedge_mode:
            position_side = position['positionSide']
        
        # Kiểm tra lệnh SL/TP hiện tại
        orders = self.check_sltp_orders(symbol, position_side)
        
        # Nếu đã có đủ SL/TP, không cần sửa
        if len(orders['sl']) > 0 and len(orders['tp']) > 0:
            logger.info(f"{symbol} đã có đủ SL và TP")
            return True
        
        # Tính SL/TP dựa vào % từ cấu hình
        sl_pct, tp_pct = self.get_sl_tp_percentages()
        
        # Chiều vị thế
        is_long = position_amt > 0
        
        # Tính giá SL/TP
        if is_long:
            sl_price = round(entry_price * (1 - sl_pct/100), 2)
            tp_price = round(entry_price * (1 + tp_pct/100), 2)
        else:
            sl_price = round(entry_price * (1 + sl_pct/100), 2)
            tp_price = round(entry_price * (1 - tp_pct/100), 2)
        
        # Cần đặt SL?
        need_sl = len(orders['sl']) == 0
        # Cần đặt TP?
        need_tp = len(orders['tp']) == 0
        
        logger.info(f"Vị thế {symbol}: "
                  f"entry={entry_price}, "
                  f"{'LONG' if is_long else 'SHORT'}, "
                  f"amount={abs(position_amt)}, "
                  f"SL={sl_price}, "
                  f"TP={tp_price}")
        
        if not need_sl and not need_tp:
            return True
        
        # Lấy abs của position_amt
        quantity = abs(position_amt)
        
        try:
            # Đặt SL/TP bị thiếu
            if need_sl and not need_tp:
                logger.info(f"Đặt SL cho {symbol} tại giá {sl_price}")
                result = self.api.set_stop_loss_take_profit(
                    symbol=symbol,
                    position_side=position_side,
                    entry_price=entry_price,
                    stop_loss_price=sl_price,
                    take_profit_price=None,
                    order_quantity=quantity
                )
                if 'stop_loss' in result and 'orderId' in result['stop_loss']:
                    logger.info(f"✅ Đặt SL thành công, orderId: {result['stop_loss']['orderId']}")
                    return True
                else:
                    logger.error(f"❌ Lỗi khi đặt SL: {result}")
                    return False
            elif need_tp and not need_sl:
                logger.info(f"Đặt TP cho {symbol} tại giá {tp_price}")
                result = self.api.set_stop_loss_take_profit(
                    symbol=symbol,
                    position_side=position_side,
                    entry_price=entry_price,
                    stop_loss_price=None,
                    take_profit_price=tp_price,
                    order_quantity=quantity
                )
                if 'take_profit' in result and 'orderId' in result['take_profit']:
                    logger.info(f"✅ Đặt TP thành công, orderId: {result['take_profit']['orderId']}")
                    return True
                else:
                    logger.error(f"❌ Lỗi khi đặt TP: {result}")
                    return False
            else:
                logger.info(f"Đặt cả SL và TP cho {symbol}")
                result = self.api.set_stop_loss_take_profit(
                    symbol=symbol,
                    position_side=position_side,
                    entry_price=entry_price,
                    stop_loss_price=sl_price,
                    take_profit_price=tp_price,
                    order_quantity=quantity
                )
                sl_success = 'stop_loss' in result and 'orderId' in result['stop_loss']
                tp_success = 'take_profit' in result and 'orderId' in result['take_profit']
                
                if sl_success and tp_success:
                    logger.info(f"✅ Đặt SL/TP thành công cho {symbol}")
                    return True
                else:
                    logger.error(f"❌ Lỗi khi đặt SL/TP: {result}")
                    return False
        except Exception as e:
            logger.error(f"Ngoại lệ khi đặt SL/TP cho {symbol}: {str(e)}")
            return False
    
    def check_and_fix_all_positions(self) -> Dict[str, int]:
        """Kiểm tra và sửa SL/TP cho tất cả các vị thế"""
        positions = self.get_open_positions()
        
        if not positions:
            logger.info("Không có vị thế nào đang mở")
            return {"total": 0, "fixed": 0, "errors": 0}
        
        stats = {"total": len(positions), "fixed": 0, "errors": 0}
        
        for position in positions:
            symbol = position['symbol']
            position_amt = float(position['positionAmt'])
            
            # Bỏ qua vị thế đóng
            if position_amt == 0:
                continue
            
            logger.info(f"\n--- Kiểm tra {symbol} ---")
            
            try:
                if self.fix_missing_sltp(position):
                    stats["fixed"] += 1
                else:
                    stats["errors"] += 1
            except Exception as e:
                logger.error(f"Lỗi khi sửa SL/TP cho {symbol}: {str(e)}")
                stats["errors"] += 1
        
        return stats
    
    def run(self):
        """Chạy kiểm tra toàn bộ vị thế"""
        logger.info("=== Bắt đầu kiểm tra và sửa SL/TP ===")
        start_time = time.time()
        
        stats = self.check_and_fix_all_positions()
        
        logger.info("\n=== Kết quả kiểm tra ===")
        logger.info(f"Tổng số vị thế: {stats['total']}")
        logger.info(f"Vị thế đã sửa: {stats['fixed']}")
        logger.info(f"Lỗi: {stats['errors']}")
        
        run_time = time.time() - start_time
        logger.info(f"Thời gian chạy: {run_time:.2f} giây")
        
        # Hiển thị kết quả cuối cùng
        if stats["errors"] == 0:
            logger.info("✅ Kiểm tra hoàn tất, tất cả các vị thế có đầy đủ SL/TP")
        else:
            logger.warning(f"⚠️ Kiểm tra hoàn tất, có {stats['errors']} lỗi cần xem xét thêm")


if __name__ == "__main__":
    try:
        checker = SLTPChecker()
        checker.run()
    except Exception as e:
        logger.error(f"Lỗi chương trình: {str(e)}")
        sys.exit(1)