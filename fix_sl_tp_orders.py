#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Sửa lỗi đặt lệnh SL/TP trên Binance Futures API
"""

import logging
import json
import time
from binance_api import BinanceAPI
from binance_api_fixes import apply_fixes_to_api

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fix_sl_tp")

class SLTPFixer:
    def __init__(self, api):
        self.api = api
        
    def check_position(self, symbol):
        """Kiểm tra vị thế hiện tại"""
        positions = self.api.get_futures_position_risk()
        pos = None
        
        for p in positions:
            if p.get('symbol') == symbol:
                if float(p.get('positionAmt', 0)) != 0:
                    pos = p
                    break
                    
        if pos:
            logger.info(f"Vị thế hiện tại: {json.dumps(pos, indent=2)}")
            return pos
        
        logger.error(f"Không tìm thấy vị thế active cho {symbol}")
        return None
        
    def cancel_all_sl_tp(self, symbol):
        """Hủy tất cả lệnh SL/TP hiện tại"""
        try:
            orders = self.api.get_open_orders(symbol)
            
            logger.info(f"Có {len(orders)} lệnh đang mở cho {symbol}")
            
            for order in orders:
                order_id = order.get('orderId')
                order_type = order.get('type')
                
                if order_type in ['STOP_MARKET', 'TAKE_PROFIT_MARKET', 'STOP', 'TAKE_PROFIT']:
                    try:
                        self.api.cancel_order(symbol=symbol, order_id=order_id)
                        logger.info(f"Đã hủy lệnh {order_type} #{order_id}")
                    except Exception as e:
                        logger.error(f"Lỗi khi hủy lệnh #{order_id}: {str(e)}")
                        
            return True
        except Exception as e:
            logger.error(f"Lỗi khi hủy lệnh SL/TP: {str(e)}")
            return False
            
    def set_sl_tp_with_close_position(self, symbol, pos):
        """Thiết lập SL/TP sử dụng closePosition"""
        try:
            # Lấy thông tin vị thế
            pos_amt = float(pos.get('positionAmt', 0))
            entry_price = float(pos.get('entryPrice', 0))
            pos_side = pos.get('positionSide', 'BOTH')
            
            # Xác định side và giá
            is_long = pos_amt > 0
            side = 'SELL' if is_long else 'BUY'
            
            # Thiết lập SL/TP theo phần trăm
            sl_percent = 2.0  # 2% cho SL
            tp_percent = 3.0  # 3% cho TP
            
            # Tính giá SL/TP
            if is_long:
                sl_price = round(entry_price * (1 - sl_percent / 100), 2)
                tp_price = round(entry_price * (1 + tp_percent / 100), 2)
            else:
                sl_price = round(entry_price * (1 + sl_percent / 100), 2)
                tp_price = round(entry_price * (1 - tp_percent / 100), 2)
                
            logger.info(f"Vị thế: {symbol} {'LONG' if is_long else 'SHORT'}")
            logger.info(f"Entry: {entry_price}, SL: {sl_price}, TP: {tp_price}")
            
            # Đặt SL
            sl_params = {
                'symbol': symbol,
                'side': side,
                'type': 'STOP_MARKET',
                'stopPrice': sl_price,
                'closePosition': 'true',
                'workingType': 'MARK_PRICE'
            }
            
            # Thêm positionSide nếu tài khoản đang ở hedge mode
            if hasattr(self.api, 'hedge_mode') and self.api.hedge_mode and pos_side != 'BOTH':
                sl_params['positionSide'] = pos_side
                # Khi có positionSide, không có closePosition
                sl_params.pop('closePosition')
                sl_params['quantity'] = abs(pos_amt)
                
            logger.info(f"Tham số lệnh SL: {json.dumps(sl_params, indent=2)}")
            sl_order = self.api._request('POST', 'order', sl_params, signed=True, version='v1')
            
            logger.info(f"Kết quả đặt lệnh SL: {json.dumps(sl_order, indent=2)}")
            
            # Đặt TP
            tp_params = {
                'symbol': symbol,
                'side': side,
                'type': 'TAKE_PROFIT_MARKET',
                'stopPrice': tp_price,
                'closePosition': 'true',
                'workingType': 'MARK_PRICE'
            }
            
            # Thêm positionSide nếu tài khoản đang ở hedge mode
            if hasattr(self.api, 'hedge_mode') and self.api.hedge_mode and pos_side != 'BOTH':
                tp_params['positionSide'] = pos_side
                # Khi có positionSide, không có closePosition
                tp_params.pop('closePosition')
                tp_params['quantity'] = abs(pos_amt)
                
            logger.info(f"Tham số lệnh TP: {json.dumps(tp_params, indent=2)}")
            tp_order = self.api._request('POST', 'order', tp_params, signed=True, version='v1')
            
            logger.info(f"Kết quả đặt lệnh TP: {json.dumps(tp_order, indent=2)}")
            
            return {
                'sl': sl_order,
                'tp': tp_order
            }
        except Exception as e:
            logger.error(f"Lỗi khi đặt SL/TP: {str(e)}")
            return None
            
    def verify_sl_tp(self, symbol):
        """Xác minh lệnh SL/TP đã được đặt thành công"""
        try:
            orders = self.api.get_open_orders(symbol)
            
            sl_orders = [o for o in orders if o.get('type') in ['STOP_MARKET', 'STOP'] and o.get('side') != 'NONE']
            tp_orders = [o for o in orders if o.get('type') in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT'] and o.get('side') != 'NONE']
            
            logger.info(f"Tìm thấy {len(sl_orders)} lệnh SL và {len(tp_orders)} lệnh TP cho {symbol}")
            
            for sl in sl_orders:
                logger.info(f"SL: #{sl.get('orderId')} - Giá: {sl.get('stopPrice')}")
                
            for tp in tp_orders:
                logger.info(f"TP: #{tp.get('orderId')} - Giá: {tp.get('stopPrice')}")
                
            return {
                'has_sl': len(sl_orders) > 0,
                'has_tp': len(tp_orders) > 0,
                'sl_orders': sl_orders,
                'tp_orders': tp_orders
            }
        except Exception as e:
            logger.error(f"Lỗi khi xác minh SL/TP: {str(e)}")
            return None
            
    def process_symbol(self, symbol):
        """Xử lý đặt SL/TP cho một symbol"""
        logger.info(f"Đang xử lý {symbol}...")
        
        # Kiểm tra vị thế
        pos = self.check_position(symbol)
        if not pos:
            return False
            
        # Hủy các lệnh SL/TP hiện tại
        if not self.cancel_all_sl_tp(symbol):
            logger.warning(f"Không thể hủy lệnh SL/TP hiện tại cho {symbol}")
            
        # Thiết lập SL/TP mới
        result = self.set_sl_tp_with_close_position(symbol, pos)
        if not result:
            logger.error(f"Không thể thiết lập SL/TP cho {symbol}")
            return False
            
        # Xác minh SL/TP
        time.sleep(2)  # Chờ để đảm bảo lệnh đã được xử lý
        verify = self.verify_sl_tp(symbol)
        
        if verify and verify.get('has_sl') and verify.get('has_tp'):
            logger.info(f"✅ Đã thiết lập thành công SL/TP cho {symbol}")
            return True
        else:
            logger.error(f"❌ Không thể xác minh SL/TP cho {symbol}")
            return False
        
def main():
    # Khởi tạo API
    api = BinanceAPI(None, None, testnet=True)
    apply_fixes_to_api(api)
    
    # Khởi tạo fixer
    fixer = SLTPFixer(api)
    
    # Lấy danh sách vị thế
    positions = api.get_futures_position_risk()
    active_positions = [p for p in positions if abs(float(p.get('positionAmt', 0))) > 0]
    
    logger.info(f"Tìm thấy {len(active_positions)} vị thế đang mở")
    
    results = {}
    
    # Xử lý từng symbol
    for pos in active_positions:
        symbol = pos.get('symbol')
        success = fixer.process_symbol(symbol)
        results[symbol] = success
        
    # Hiển thị kết quả
    logger.info("\n--- KẾT QUẢ THIẾT LẬP SL/TP ---")
    for symbol, success in results.items():
        status = "✅ Thành công" if success else "❌ Thất bại"
        logger.info(f"{symbol}: {status}")
        
if __name__ == "__main__":
    main()