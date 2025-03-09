#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Auto SL/TP Manager - Hệ thống tự động quản lý Stop Loss và Take Profit

Script này tự động quản lý và điều chỉnh Stop Loss và Take Profit cho các vị thế đang mở,
bao gồm:
- Thiết lập SL/TP ban đầu cho vị thế mới
- Điều chỉnh SL theo trailing stop
- Điều chỉnh TP theo profit manager
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('auto_sltp_manager')

# Thêm thư mục gốc vào sys.path để import các module
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from binance_api import BinanceAPI
from binance_api_fixes import apply_fixes_to_api

class AutoSLTPManager:
    """
    Quản lý tự động Stop Loss và Take Profit
    """
    
    def __init__(self, api_key: str = None, api_secret: str = None, testnet: bool = True):
        """
        Khởi tạo manager
        
        Args:
            api_key (str, optional): API key Binance
            api_secret (str, optional): API secret Binance
            testnet (bool): Sử dụng testnet hay không
        """
        # Khởi tạo API
        self.api = BinanceAPI(api_key=api_key, api_secret=api_secret, testnet=testnet)
        self.api = apply_fixes_to_api(self.api)
        
        # Tham số mặc định
        self.default_sl_percent = 2.0  # 2% từ giá entry
        self.default_tp_percent = 3.0  # 3% từ giá entry
        self.min_profit_percent = 1.0  # 1% là mức lợi nhuận tối thiểu để trailing stop
        self.trailing_percent = 1.0    # 1% là khoảng cách trailing stop
        self.activation_percent = 2.0  # 2% là mức kích hoạt trailing stop
        
        # Trạng thái
        self.active_positions = {}     # Lưu trữ vị thế đang quản lý
        self.position_data = {}        # Dữ liệu bổ sung cho vị thế (highest_price, trailing_active, etc.)
        
        # Tải cấu hình từ file nếu có
        self._load_config()
        
        logger.info(f"Khởi tạo Auto SL/TP Manager: SL={self.default_sl_percent}%, TP={self.default_tp_percent}%")
        
    def _load_config(self):
        """Tải cấu hình từ file"""
        try:
            config_file = 'configs/sltp_config.json'
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                # Áp dụng cấu hình
                self.default_sl_percent = config.get('default_sl_percent', self.default_sl_percent)
                self.default_tp_percent = config.get('default_tp_percent', self.default_tp_percent)
                self.min_profit_percent = config.get('min_profit_percent', self.min_profit_percent)
                self.trailing_percent = config.get('trailing_percent', self.trailing_percent)
                self.activation_percent = config.get('activation_percent', self.activation_percent)
                
                logger.info(f"Đã tải cấu hình từ {config_file}")
        except Exception as e:
            logger.warning(f"Không thể tải cấu hình: {str(e)}")
    
    def _save_position_data(self):
        """Lưu trạng thái vị thế vào file"""
        try:
            with open('position_data.json', 'w') as f:
                json.dump(self.position_data, f, indent=2)
            logger.debug("Đã lưu dữ liệu vị thế")
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu vị thế: {str(e)}")
    
    def _load_position_data(self):
        """Tải trạng thái vị thế từ file"""
        try:
            if os.path.exists('position_data.json'):
                with open('position_data.json', 'r') as f:
                    self.position_data = json.load(f)
                logger.debug("Đã tải dữ liệu vị thế")
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu vị thế: {str(e)}")
    
    def update_positions(self):
        """Cập nhật danh sách vị thế đang mở"""
        try:
            positions = self.api.get_futures_position_risk()
            active_positions = [p for p in positions if abs(float(p.get('positionAmt', 0))) > 0]
            
            # Cập nhật active_positions
            self.active_positions = {p.get('symbol'): p for p in active_positions}
            
            logger.info(f"Đã cập nhật {len(active_positions)} vị thế đang mở")
            return active_positions
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật vị thế: {str(e)}")
            return []
    
    def get_open_orders(self, symbol: str) -> Tuple[List[Dict], List[Dict]]:
        """Lấy các lệnh SL/TP đang mở cho một symbol
        
        Args:
            symbol (str): Symbol cần kiểm tra
            
        Returns:
            Tuple[List[Dict], List[Dict]]: (sl_orders, tp_orders)
        """
        try:
            orders = self.api.get_open_orders(symbol)
            
            # Phân loại lệnh - sửa phần này để phân loại chính xác hơn
            # Kiểm tra cả type và tên hiển thị đầy đủ
            sl_orders = [o for o in orders if (
                o.get('type') in ['STOP_MARKET', 'STOP'] and
                # Cũng kiểm tra các thuộc tính khác để xác nhận đây là lệnh SL
                o.get('origType', '') in ['STOP_MARKET', 'STOP'] and
                # Thêm kiểm tra workingType nếu có
                o.get('workingType', '') in ['MARK_PRICE', 'CONTRACT_PRICE']
            )]
            
            tp_orders = [o for o in orders if (
                o.get('type') in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT'] and
                # Cũng kiểm tra các thuộc tính khác để xác nhận đây là lệnh TP
                o.get('origType', '') in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT'] and
                # Thêm kiểm tra workingType nếu có
                o.get('workingType', '') in ['MARK_PRICE', 'CONTRACT_PRICE']
            )]
            
            # Log chi tiết để debug
            logger.info(f"Tìm thấy {len(sl_orders)} lệnh SL và {len(tp_orders)} lệnh TP cho {symbol}")
            
            return sl_orders, tp_orders
        except Exception as e:
            logger.error(f"Lỗi khi lấy lệnh đang mở cho {symbol}: {str(e)}")
            return [], []
    
    def set_stop_loss(self, symbol: str, side: str, price: float, quantity: float) -> bool:
        """Thiết lập Stop Loss
        
        Args:
            symbol (str): Symbol
            side (str): 'LONG' hoặc 'SHORT'
            price (float): Giá stop loss
            quantity (float): Số lượng
            
        Returns:
            bool: True nếu thành công
        """
        try:
            # Xác định phía đóng lệnh
            close_side = 'SELL' if side == 'LONG' else 'BUY'
            
            # Xác định positionSide cho hedge mode
            position_side = 'LONG' if side == 'LONG' else 'SHORT'
            
            # Đặt lệnh Stop Loss với quantity và reduceOnly=True để hiển thị trên giao diện
            result = self.api.futures_create_order(
                symbol=symbol,
                side=close_side,
                type='STOP_MARKET',
                stopPrice=price,
                quantity=abs(quantity),
                reduceOnly=True,
                workingType="MARK_PRICE"
            )
            
            logger.info(f"Đã đặt SL cho {symbol} {side} tại giá {price}, số lượng {quantity}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi đặt SL cho {symbol}: {str(e)}")
            return False
    
    def set_take_profit(self, symbol: str, side: str, price: float, quantity: float) -> bool:
        """Thiết lập Take Profit
        
        Args:
            symbol (str): Symbol
            side (str): 'LONG' hoặc 'SHORT'
            price (float): Giá take profit
            quantity (float): Số lượng
            
        Returns:
            bool: True nếu thành công
        """
        try:
            # Xác định phía đóng lệnh
            close_side = 'SELL' if side == 'LONG' else 'BUY'
            
            # Xác định positionSide cho hedge mode
            position_side = 'LONG' if side == 'LONG' else 'SHORT'
            
            # Đặt lệnh Take Profit với quantity và reduceOnly=True để hiển thị trên giao diện
            result = self.api.futures_create_order(
                symbol=symbol,
                side=close_side,
                type='TAKE_PROFIT_MARKET',
                stopPrice=price,
                quantity=abs(quantity),
                reduceOnly=True,
                workingType="MARK_PRICE"
            )
            
            logger.info(f"Đã đặt TP cho {symbol} {side} tại giá {price}, số lượng {quantity}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi đặt TP cho {symbol}: {str(e)}")
            return False
    
    def cancel_sl_tp_orders(self, symbol: str) -> bool:
        """Hủy tất cả lệnh SL/TP cho một symbol
        
        Args:
            symbol (str): Symbol cần hủy lệnh
            
        Returns:
            bool: True nếu thành công
        """
        try:
            sl_orders, tp_orders = self.get_open_orders(symbol)
            all_orders = sl_orders + tp_orders
            
            for order in all_orders:
                order_id = order.get('orderId')
                order_type = order.get('type')
                
                try:
                    self.api.cancel_order(symbol=symbol, order_id=order_id)
                    logger.info(f"Đã hủy lệnh {order_type} #{order_id} cho {symbol}")
                except Exception as e:
                    logger.error(f"Lỗi khi hủy lệnh #{order_id}: {str(e)}")
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi hủy lệnh SL/TP cho {symbol}: {str(e)}")
            return False
    
    def setup_initial_sltp(self, symbol: str, force: bool = False) -> bool:
        """Thiết lập SL/TP ban đầu cho một symbol
        
        Args:
            symbol (str): Symbol cần thiết lập
            force (bool): Buộc thiết lập lại nếu đã có
            
        Returns:
            bool: True nếu thành công
        """
        try:
            # Kiểm tra vị thế
            if symbol not in self.active_positions:
                logger.warning(f"Không tìm thấy vị thế {symbol} đang mở")
                return False
            
            position = self.active_positions[symbol]
            
            # Lấy thông tin vị thế
            position_amt = float(position.get('positionAmt', 0))
            entry_price = float(position.get('entryPrice', 0))
            side = 'LONG' if position_amt > 0 else 'SHORT'
            qty = abs(position_amt)
            
            # Kiểm tra lệnh đang mở
            sl_orders, tp_orders = self.get_open_orders(symbol)
            
            # Nếu đã có lệnh và không force thì bỏ qua - nhưng chỉ khi thực sự xác định được đúng lệnh
            if not force and len(sl_orders) > 0 and len(tp_orders) > 0:
                # Tạo thêm log chi tiết
                logger.info(f"{symbol} đã có cả SL ({len(sl_orders)} lệnh) và TP ({len(tp_orders)} lệnh), bỏ qua")
                # Nếu chỉ có 1 lệnh SL và 1 lệnh TP, ghi log thêm chi tiết về các lệnh
                if len(sl_orders) == 1 and len(tp_orders) == 1:
                    sl_order = sl_orders[0]
                    tp_order = tp_orders[0]
                    logger.info(f"Chi tiết lệnh SL: ID={sl_order.get('orderId')}, stopPrice={sl_order.get('stopPrice')}")
                    logger.info(f"Chi tiết lệnh TP: ID={tp_order.get('orderId')}, stopPrice={tp_order.get('stopPrice')}")
                return True
            
            # Nếu force hoặc chưa có lệnh thì hủy lệnh cũ và đặt lại
            if force or len(sl_orders) == 0 or len(tp_orders) == 0:
                # Hủy lệnh cũ
                self.cancel_sl_tp_orders(symbol)
                
                # Tính giá SL/TP
                if side == 'LONG':
                    sl_price = entry_price * (1 - self.default_sl_percent / 100)
                    tp_price = entry_price * (1 + self.default_tp_percent / 100)
                else:
                    sl_price = entry_price * (1 + self.default_sl_percent / 100)
                    tp_price = entry_price * (1 - self.default_tp_percent / 100)
                
                # Làm tròn giá
                sl_price = round(sl_price, 2)
                tp_price = round(tp_price, 2)
                
                # Đặt lệnh mới
                sl_success = self.set_stop_loss(symbol, side, sl_price, qty)
                tp_success = self.set_take_profit(symbol, side, tp_price, qty)
                
                # Thêm thông tin vào position_data
                if symbol not in self.position_data:
                    self.position_data[symbol] = {}
                    
                self.position_data[symbol].update({
                    'entry_price': entry_price,
                    'side': side,
                    'qty': qty,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'highest_price': entry_price if side == 'LONG' else 0,
                    'lowest_price': entry_price if side == 'SHORT' else float('inf'),
                    'trailing_active': False,
                    'last_updated': datetime.now().isoformat()
                })
                
                self._save_position_data()
                
                return sl_success and tp_success
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập SL/TP ban đầu cho {symbol}: {str(e)}")
            return False
    
    def update_trailing_stop(self, symbol: str) -> bool:
        """Cập nhật trailing stop
        
        Args:
            symbol (str): Symbol cần cập nhật
            
        Returns:
            bool: True nếu có cập nhật
        """
        try:
            # Kiểm tra vị thế
            if symbol not in self.active_positions or symbol not in self.position_data:
                return False
            
            position = self.active_positions[symbol]
            position_data = self.position_data[symbol]
            
            # Lấy thông tin vị thế
            entry_price = float(position.get('entryPrice', 0))
            current_price = float(self.api.get_symbol_ticker(symbol).get('price', 0))
            side = position_data.get('side')
            qty = position_data.get('qty')
            
            # Kiểm tra điều kiện kích hoạt trailing stop
            if side == 'LONG':
                # Tính toán lợi nhuận hiện tại
                profit_percent = (current_price - entry_price) / entry_price * 100
                
                # Lưu giá cao nhất
                if current_price > position_data.get('highest_price', 0):
                    position_data['highest_price'] = current_price
                    self._save_position_data()
                
                # Kiểm tra nếu đủ điều kiện kích hoạt trailing stop
                if profit_percent >= self.activation_percent and not position_data.get('trailing_active', False):
                    logger.info(f"Kích hoạt trailing stop cho {symbol}: Profit={profit_percent:.2f}%")
                    position_data['trailing_active'] = True
                    self._save_position_data()
                
                # Nếu trailing stop đã kích hoạt, cập nhật SL
                if position_data.get('trailing_active', False):
                    highest_price = position_data.get('highest_price', current_price)
                    
                    # Tính trailing stop price mới
                    new_sl_price = highest_price * (1 - self.trailing_percent / 100)
                    current_sl_price = position_data.get('sl_price', 0)
                    
                    # Chỉ cập nhật nếu SL mới cao hơn SL hiện tại
                    if new_sl_price > current_sl_price:
                        # Hủy lệnh SL cũ
                        sl_orders, _ = self.get_open_orders(symbol)
                        for order in sl_orders:
                            self.api.cancel_order(symbol=symbol, order_id=order.get('orderId'))
                        
                        # Đặt lệnh SL mới
                        new_sl_price = round(new_sl_price, 2)
                        self.set_stop_loss(symbol, side, new_sl_price, qty)
                        
                        # Cập nhật dữ liệu
                        position_data['sl_price'] = new_sl_price
                        position_data['last_updated'] = datetime.now().isoformat()
                        self._save_position_data()
                        
                        logger.info(f"Đã cập nhật trailing stop cho {symbol}: {current_sl_price:.2f} -> {new_sl_price:.2f}")
                        return True
                        
            elif side == 'SHORT':
                # Tính toán lợi nhuận hiện tại
                profit_percent = (entry_price - current_price) / entry_price * 100
                
                # Lưu giá thấp nhất
                if current_price < position_data.get('lowest_price', float('inf')):
                    position_data['lowest_price'] = current_price
                    self._save_position_data()
                
                # Kiểm tra nếu đủ điều kiện kích hoạt trailing stop
                if profit_percent >= self.activation_percent and not position_data.get('trailing_active', False):
                    logger.info(f"Kích hoạt trailing stop cho {symbol}: Profit={profit_percent:.2f}%")
                    position_data['trailing_active'] = True
                    self._save_position_data()
                
                # Nếu trailing stop đã kích hoạt, cập nhật SL
                if position_data.get('trailing_active', False):
                    lowest_price = position_data.get('lowest_price', current_price)
                    
                    # Tính trailing stop price mới
                    new_sl_price = lowest_price * (1 + self.trailing_percent / 100)
                    current_sl_price = position_data.get('sl_price', float('inf'))
                    
                    # Chỉ cập nhật nếu SL mới thấp hơn SL hiện tại
                    if new_sl_price < current_sl_price:
                        # Hủy lệnh SL cũ
                        sl_orders, _ = self.get_open_orders(symbol)
                        for order in sl_orders:
                            self.api.cancel_order(symbol=symbol, order_id=order.get('orderId'))
                        
                        # Đặt lệnh SL mới
                        new_sl_price = round(new_sl_price, 2)
                        self.set_stop_loss(symbol, side, new_sl_price, qty)
                        
                        # Cập nhật dữ liệu
                        position_data['sl_price'] = new_sl_price
                        position_data['last_updated'] = datetime.now().isoformat()
                        self._save_position_data()
                        
                        logger.info(f"Đã cập nhật trailing stop cho {symbol}: {current_sl_price:.2f} -> {new_sl_price:.2f}")
                        return True
            
            return False
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật trailing stop cho {symbol}: {str(e)}")
            return False
    
    def run_once(self, force_setup: bool = False) -> bool:
        """Chạy một lần kiểm tra và cập nhật SL/TP
        
        Args:
            force_setup (bool): Buộc thiết lập lại SL/TP
            
        Returns:
            bool: True nếu hoàn thành
        """
        try:
            # Tải dữ liệu vị thế
            self._load_position_data()
            
            # Cập nhật danh sách vị thế
            self.update_positions()
            
            # Kiểm tra từng vị thế
            for symbol in self.active_positions:
                # Thiết lập SL/TP ban đầu
                self.setup_initial_sltp(symbol, force=force_setup)
                
                # Cập nhật trailing stop
                self.update_trailing_stop(symbol)
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi chạy Auto SL/TP Manager: {str(e)}")
            return False
    
    def run(self, interval: int = 60, force_setup: bool = False):
        """Chạy liên tục
        
        Args:
            interval (int): Thời gian giữa các lần kiểm tra (giây)
            force_setup (bool): Buộc thiết lập lại SL/TP
        """
        import traceback
        logger.info(f"Bắt đầu chạy Auto SL/TP Manager với interval={interval}s")
        
        # Theo dõi lỗi để có thể phục hồi
        consecutive_errors = 0
        max_consecutive_errors = 3
        last_heartbeat = time.time()
        heartbeat_interval = 300  # 5 phút
        
        # Lưu trữ thông tin API
        api_testnet = self.testnet if hasattr(self, 'testnet') else False
        
        # Đảm bảo rằng chúng ta lặp mãi mãi với nhiều lớp xử lý lỗi
        while True:
            try:
                # Vòng lặp chính
                while True:
                    try:
                        # Chạy một chu kỳ cập nhật SL/TP
                        success = self.run_once(force_setup=force_setup)
                        
                        # Reset biến force sau lần đầu tiên
                        force_setup = False
                        
                        # Reset số lỗi liên tiếp nếu thành công
                        if success:
                            consecutive_errors = 0
                        
                        # Ghi log heartbeat định kỳ
                        current_time = time.time()
                        if current_time - last_heartbeat > heartbeat_interval:
                            logger.info(f"Heartbeat: Auto SL/TP Manager đang chạy bình thường, đã xử lý {consecutive_errors} lỗi")
                            last_heartbeat = current_time
                        
                        # Tạm nghỉ trước chu kỳ tiếp theo
                        time.sleep(interval)
                        
                    except Exception as inner_e:
                        # Tăng số lỗi liên tiếp
                        consecutive_errors += 1
                        
                        # Ghi log lỗi chi tiết
                        error_details = traceback.format_exc()
                        logger.error(f"Lỗi trong chu kỳ cập nhật SL/TP lần thứ {consecutive_errors}: {str(inner_e)}")
                        logger.error(f"Chi tiết lỗi: {error_details}")
                        
                        # Kiểm tra số lỗi liên tiếp
                        if consecutive_errors >= max_consecutive_errors:
                            logger.critical(f"Đã xảy ra {consecutive_errors} lỗi liên tiếp, khởi động lại kết nối API")
                            # Thử khởi động lại API
                            try:
                                del self.api
                                self.api = BinanceAPI("", "", testnet=api_testnet)
                                apply_fixes_to_api(self.api)
                                # Khởi tạo lại các biến dữ liệu
                                self.position_data = {}
                                self.active_positions = {}
                                # Thông báo khởi động lại thành công
                                logger.info("Đã khởi động lại kết nối API thành công")
                                # Reset số lỗi
                                consecutive_errors = 0
                            except Exception as restart_e:
                                logger.critical(f"Không thể khởi động lại API: {str(restart_e)}")
                        
                        # Tạm nghỉ ngắn sau lỗi trước khi thử lại
                        recovery_interval = min(interval, 30)  # Tối đa 30 giây
                        logger.info(f"Đợi {recovery_interval}s trước khi thử lại")
                        time.sleep(recovery_interval)
                        
            except KeyboardInterrupt:
                logger.info("Dừng Auto SL/TP Manager theo yêu cầu người dùng")
                break  # Thoát khỏi vòng lặp ngoài cùng
            except Exception as e:
                # Xử lý lỗi nghiêm trọng
                import traceback
                logger.critical(f"Lỗi nghiêm trọng trong vòng lặp chính: {str(e)}")
                logger.critical(f"Chi tiết lỗi: {traceback.format_exc()}")
                
                # Đợi một thời gian trước khi khởi động lại toàn bộ
                logger.info("Đợi 60 giây trước khi khởi động lại toàn bộ quy trình")
                time.sleep(60)
                
                # Reset trạng thái
                consecutive_errors = 0
                
                # Tiếp tục vòng lặp ngoài để thử lại từ đầu
                logger.info("Khởi động lại toàn bộ quy trình sau lỗi nghiêm trọng")

def main():
    parser = argparse.ArgumentParser(description='Auto SL/TP Manager')
    parser.add_argument('--interval', type=int, default=60, help='Thời gian giữa các lần kiểm tra (giây)')
    parser.add_argument('--force', action='store_true', help='Buộc thiết lập lại SL/TP')
    parser.add_argument('--once', action='store_true', help='Chỉ chạy một lần')
    parser.add_argument('--testnet', action='store_true', help='Sử dụng Binance Testnet')
    args = parser.parse_args()
    
    # Khởi tạo manager
    manager = AutoSLTPManager(testnet=args.testnet)
    
    # Chạy
    if args.once:
        manager.run_once(force_setup=args.force)
    else:
        manager.run(interval=args.interval, force_setup=args.force)

if __name__ == "__main__":
    main()