#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module đồng bộ hóa với Binance (BinanceSynchronizer)

Module này cung cấp các phương thức để đồng bộ hóa dữ liệu giữa hệ thống giao dịch
local và Binance, đảm bảo thông tin vị thế, stop loss, và take profit luôn được
cập nhật đồng bộ theo cả hai chiều.
"""

import os
import json
import time
import logging
import datetime
import traceback
from typing import Dict, List, Tuple, Optional, Union, Any
from binance_api import BinanceAPI

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('binance_synchronizer')

class BinanceSynchronizer:
    """Lớp đồng bộ hóa dữ liệu với Binance"""
    
    def __init__(self, binance_api: BinanceAPI, positions_file: str = 'active_positions.json',
                max_retries: int = 3, retry_delay: int = 2):
        """
        Khởi tạo đồng bộ hóa với Binance
        
        Args:
            binance_api (BinanceAPI): Đối tượng BinanceAPI đã được khởi tạo
            positions_file (str): Đường dẫn file lưu vị thế active
            max_retries (int): Số lần thử lại tối đa khi gặp lỗi
            retry_delay (int): Thời gian chờ giữa các lần thử lại (giây)
        """
        self.api = binance_api
        self.positions_file = positions_file
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Vị thế đang active trên local
        self.active_positions = {}
        
        # Thông tin đồng bộ
        self.sync_info = {
            'last_sync_time': None,
            'sync_count': 0,
            'positions_synced': 0,
            'sl_synced': 0,
            'tp_synced': 0,
            'errors': []
        }
        
        # Tải vị thế từ file nếu tồn tại
        self.load_local_positions()
    
    def load_local_positions(self) -> Dict:
        """
        Tải dữ liệu vị thế từ file local
        
        Returns:
            Dict: Dữ liệu vị thế đã tải
        """
        if os.path.exists(self.positions_file):
            try:
                with open(self.positions_file, 'r') as f:
                    data = json.load(f)
                
                # Kiểm tra cấu trúc dữ liệu
                if isinstance(data, dict):
                    self.active_positions = data
                    logger.info(f"Đã tải {len(data)} vị thế từ {self.positions_file}")
                else:
                    logger.warning(f"Dữ liệu không đúng định dạng từ {self.positions_file}, sử dụng mặc định")
                    self.active_positions = {}
            except Exception as e:
                logger.error(f"Lỗi khi tải dữ liệu vị thế từ {self.positions_file}: {str(e)}")
                self.active_positions = {}
        else:
            logger.info(f"Không tìm thấy file vị thế {self.positions_file}, sử dụng mặc định")
            self.active_positions = {}
        
        return self.active_positions
    
    def save_local_positions(self) -> bool:
        """
        Lưu dữ liệu vị thế vào file local
        
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        try:
            # Tạo bản sao dữ liệu để tránh thay đổi trong quá trình lưu
            data_to_save = self.active_positions.copy()
            
            # Tạo backup nếu file đã tồn tại
            if os.path.exists(self.positions_file):
                backup_file = f"{self.positions_file}.bak"
                try:
                    import shutil
                    shutil.copy2(self.positions_file, backup_file)
                except Exception as e:
                    logger.warning(f"Không thể tạo backup file: {str(e)}")
            
            # Lưu dữ liệu
            with open(self.positions_file, 'w') as f:
                json.dump(data_to_save, f, indent=2)
            
            logger.info(f"Đã lưu {len(data_to_save)} vị thế vào {self.positions_file}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu vị thế vào {self.positions_file}: {str(e)}")
            return False
    
    def check_local_positions_integrity(self) -> Dict:
        """
        Kiểm tra tính toàn vẹn của dữ liệu vị thế local
        
        Returns:
            Dict: Kết quả kiểm tra
        """
        result = {
            'valid_positions': 0,
            'invalid_positions': 0,
            'issues': []
        }
        
        if not self.active_positions:
            result['issues'].append("Không có vị thế nào")
            return result
        
        # Danh sách trường bắt buộc
        required_fields = {
            'symbol': str,
            'side': str,
            'entry_price': float,
            'quantity': float,
            'leverage': int,
            'entry_time': str
        }
        
        # Kiểm tra từng vị thế
        for symbol, position in list(self.active_positions.items()):
            is_valid = True
            issues = []
            
            # Kiểm tra các trường bắt buộc
            for field, field_type in required_fields.items():
                if field not in position:
                    is_valid = False
                    issues.append(f"Thiếu trường {field}")
                elif not isinstance(position[field], field_type):
                    is_valid = False
                    issues.append(f"Trường {field} không đúng kiểu dữ liệu, mong đợi {field_type.__name__}")
            
            # Kiểm tra giá trị hợp lệ
            if is_valid:
                # Kiểm tra side
                if position['side'] not in ['LONG', 'SHORT']:
                    is_valid = False
                    issues.append(f"Side không hợp lệ: {position['side']}")
                
                # Kiểm tra giá trị số
                for field in ['entry_price', 'quantity']:
                    if position[field] <= 0:
                        is_valid = False
                        issues.append(f"{field} phải là số dương")
                
                # Kiểm tra leverage
                if position['leverage'] <= 0:
                    is_valid = False
                    issues.append(f"Leverage phải là số dương")
            
            # Cập nhật kết quả
            if is_valid:
                result['valid_positions'] += 1
            else:
                result['invalid_positions'] += 1
                result['issues'].append(f"Vị thế {symbol} không hợp lệ: {', '.join(issues)}")
                
                # Ghi log
                logger.warning(f"Vị thế {symbol} không hợp lệ: {', '.join(issues)}")
                
                # Xóa vị thế không hợp lệ
                del self.active_positions[symbol]
        
        # Lưu lại nếu đã sửa
        if result['invalid_positions'] > 0:
            self.save_local_positions()
        
        return result
    
    def _with_retry(self, func, *args, **kwargs) -> Tuple[bool, Any, Optional[Exception]]:
        """
        Thực thi một hàm với cơ chế thử lại
        
        Args:
            func: Hàm cần thực thi
            *args: Tham số vị trí cho hàm
            **kwargs: Tham số từ khóa cho hàm
            
        Returns:
            Tuple[bool, Any, Optional[Exception]]: (Thành công hay không, Kết quả, Lỗi nếu có)
        """
        for attempt in range(self.max_retries):
            try:
                result = func(*args, **kwargs)
                return True, result, None
            except Exception as e:
                logger.warning(f"Lỗi khi thực thi {func.__name__} (lần thử {attempt+1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    return False, None, e
    
    def get_binance_positions(self) -> Dict[str, Any]:
        """
        Lấy danh sách vị thế đang mở trên Binance
        
        Returns:
            Dict[str, Any]: Danh sách vị thế theo symbol
        """
        # Lấy thông tin vị thế từ Binance
        success, positions_info, error = self._with_retry(self.api.get_position_information)
        
        if not success:
            logger.error(f"Không thể lấy thông tin vị thế từ Binance: {str(error)}")
            return {}
        
        # Chuyển đổi sang dict theo symbol
        binance_positions = {}
        for position in positions_info:
            symbol = position['symbol']
            position_amt = float(position['positionAmt'])
            
            # Chỉ lấy các vị thế có số lượng != 0
            if position_amt != 0:
                side = 'LONG' if position_amt > 0 else 'SHORT'
                entry_price = float(position['entryPrice'])
                leverage = int(position['leverage'])
                mark_price = float(position['markPrice'])
                
                # Tính unrealized PnL
                unrealized_pnl = float(position['unRealizedProfit'])
                
                # Chuẩn bị dữ liệu vị thế
                binance_positions[symbol] = {
                    'symbol': symbol,
                    'side': side,
                    'entry_price': entry_price,
                    'quantity': abs(position_amt),
                    'leverage': leverage,
                    'mark_price': mark_price,
                    'unrealized_pnl': unrealized_pnl,
                    'last_updated': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        
        logger.info(f"Đã lấy {len(binance_positions)} vị thế từ Binance")
        return binance_positions
    
    def get_binance_open_orders(self) -> Dict[str, List[Dict]]:
        """
        Lấy danh sách lệnh đang mở trên Binance
        
        Returns:
            Dict[str, List[Dict]]: Danh sách lệnh theo symbol
        """
        # Lấy danh sách lệnh đang mở
        success, open_orders, error = self._with_retry(self.api.get_open_orders)
        
        if not success:
            logger.error(f"Không thể lấy danh sách lệnh đang mở từ Binance: {str(error)}")
            return {}
        
        # Chuyển đổi sang dict theo symbol
        orders_by_symbol = {}
        for order in open_orders:
            symbol = order['symbol']
            
            if symbol not in orders_by_symbol:
                orders_by_symbol[symbol] = []
            
            orders_by_symbol[symbol].append(order)
        
        logger.info(f"Đã lấy {len(open_orders)} lệnh đang mở từ Binance cho {len(orders_by_symbol)} symbol")
        return orders_by_symbol
    
    def _extract_stop_loss_take_profit(self, symbol: str, open_orders: List[Dict]) -> Dict:
        """
        Trích xuất thông tin stop loss và take profit từ danh sách lệnh
        
        Args:
            symbol (str): Symbol cần trích xuất
            open_orders (List[Dict]): Danh sách lệnh đang mở
            
        Returns:
            Dict: Thông tin stop loss và take profit
        """
        result = {
            'has_stop_loss': False,
            'has_take_profit': False,
            'stop_loss_price': None,
            'take_profit_price': None,
            'stop_loss_order_id': None,
            'take_profit_order_id': None
        }
        
        if not open_orders:
            return result
        
        # Lọc các lệnh của symbol
        symbol_orders = [order for order in open_orders if order['symbol'] == symbol]
        
        # Tìm lệnh stop loss và take profit
        for order in symbol_orders:
            order_type = order['type']
            if order_type == 'STOP_MARKET' or order_type == 'STOP':
                result['has_stop_loss'] = True
                result['stop_loss_price'] = float(order['stopPrice'])
                result['stop_loss_order_id'] = order['orderId']
            elif order_type == 'TAKE_PROFIT_MARKET' or order_type == 'TAKE_PROFIT':
                result['has_take_profit'] = True
                result['take_profit_price'] = float(order['stopPrice'])
                result['take_profit_order_id'] = order['orderId']
        
        return result
    
    def sync_binance_to_local(self) -> Dict:
        """
        Đồng bộ dữ liệu từ Binance xuống local
        
        Returns:
            Dict: Kết quả đồng bộ
        """
        result = {
            'success': True,
            'positions_found': 0,
            'positions_added': 0,
            'positions_updated': 0,
            'positions_removed': 0,
            'errors': []
        }
        
        try:
            # Lấy vị thế từ Binance
            binance_positions = self.get_binance_positions()
            result['positions_found'] = len(binance_positions)
            
            if not binance_positions:
                logger.warning("Không tìm thấy vị thế nào trên Binance")
                return result
            
            # Lấy lệnh đang mở từ Binance
            binance_orders = self.get_binance_open_orders()
            
            # Đồng bộ dữ liệu
            local_symbols = set(self.active_positions.keys())
            binance_symbols = set(binance_positions.keys())
            
            # Tìm các vị thế cần thêm (có trên Binance nhưng không có local)
            symbols_to_add = binance_symbols - local_symbols
            for symbol in symbols_to_add:
                # Lấy thông tin vị thế từ Binance
                binance_position = binance_positions[symbol]
                
                # Trích xuất thông tin stop loss và take profit
                sl_tp_info = self._extract_stop_loss_take_profit(
                    symbol, 
                    binance_orders.get(symbol, [])
                )
                
                # Tạo dữ liệu vị thế local
                local_position = {
                    'symbol': symbol,
                    'side': binance_position['side'],
                    'entry_price': binance_position['entry_price'],
                    'quantity': binance_position['quantity'],
                    'leverage': binance_position['leverage'],
                    'mark_price': binance_position.get('mark_price'),
                    'stop_loss': sl_tp_info['stop_loss_price'],
                    'take_profit': sl_tp_info['take_profit_price'],
                    'unrealized_pnl': binance_position.get('unrealized_pnl'),
                    'entry_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'last_updated': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'source': 'binance',
                    'binance_sl_updated': sl_tp_info['has_stop_loss'],
                    'binance_tp_updated': sl_tp_info['has_take_profit']
                }
                
                # Thêm vào danh sách vị thế local
                self.active_positions[symbol] = local_position
                result['positions_added'] += 1
                
                logger.info(f"Đã thêm vị thế mới từ Binance: {symbol} {binance_position['side']}")
            
            # Tìm các vị thế cần cập nhật (có ở cả Binance và local)
            symbols_to_update = binance_symbols.intersection(local_symbols)
            for symbol in symbols_to_update:
                # Lấy thông tin vị thế
                binance_position = binance_positions[symbol]
                local_position = self.active_positions[symbol]
                
                # Trích xuất thông tin stop loss và take profit
                sl_tp_info = self._extract_stop_loss_take_profit(
                    symbol, 
                    binance_orders.get(symbol, [])
                )
                
                # Cập nhật thông tin cơ bản
                local_position['mark_price'] = binance_position.get('mark_price')
                local_position['unrealized_pnl'] = binance_position.get('unrealized_pnl')
                local_position['last_updated'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Cập nhật thông tin từ Binance
                if binance_position['side'] != local_position['side']:
                    local_position['side'] = binance_position['side']
                if binance_position['entry_price'] != local_position['entry_price']:
                    local_position['entry_price'] = binance_position['entry_price']
                if binance_position['quantity'] != local_position['quantity']:
                    local_position['quantity'] = binance_position['quantity']
                if binance_position['leverage'] != local_position['leverage']:
                    local_position['leverage'] = binance_position['leverage']
                
                # Cập nhật stop loss và take profit từ Binance nếu có
                if sl_tp_info['has_stop_loss']:
                    local_position['stop_loss'] = sl_tp_info['stop_loss_price']
                    local_position['binance_sl_updated'] = True
                if sl_tp_info['has_take_profit']:
                    local_position['take_profit'] = sl_tp_info['take_profit_price']
                    local_position['binance_tp_updated'] = True
                
                result['positions_updated'] += 1
                logger.info(f"Đã cập nhật vị thế từ Binance: {symbol} {binance_position['side']}")
            
            # Tìm các vị thế cần xóa (có ở local nhưng không có ở Binance)
            symbols_to_remove = local_symbols - binance_symbols
            for symbol in symbols_to_remove:
                # Nếu vị thế được đánh dấu là đã đóng, không cần cảnh báo
                if self.active_positions[symbol].get('closed', False):
                    pass
                else:
                    logger.warning(f"Vị thế {symbol} có ở local nhưng không tìm thấy trên Binance")
                
                # Xóa khỏi danh sách vị thế local
                del self.active_positions[symbol]
                result['positions_removed'] += 1
            
            # Lưu dữ liệu
            self.save_local_positions()
            
            return result
        except Exception as e:
            logger.error(f"Lỗi khi đồng bộ dữ liệu từ Binance xuống local: {str(e)}")
            logger.error(traceback.format_exc())
            result['success'] = False
            result['errors'].append(str(e))
            return result
    
    def sync_local_to_binance(self) -> Dict:
        """
        Đồng bộ dữ liệu từ local lên Binance
        
        Returns:
            Dict: Kết quả đồng bộ
        """
        result = {
            'success': True,
            'stop_loss_synced': 0,
            'take_profit_synced': 0,
            'errors': []
        }
        
        if not self.active_positions:
            logger.info("Không có vị thế local nào để đồng bộ lên Binance")
            return result
        
        try:
            # Lấy lệnh đang mở từ Binance
            binance_orders = self.get_binance_open_orders()
            
            # Duyệt qua từng vị thế local
            for symbol, position in self.active_positions.items():
                # Trích xuất thông tin về SL/TP
                sl_tp_info = self._extract_stop_loss_take_profit(
                    symbol, 
                    binance_orders.get(symbol, [])
                )
                
                # Cập nhật thông tin đồng bộ
                position['binance_sl_updated'] = sl_tp_info['has_stop_loss']
                position['binance_tp_updated'] = sl_tp_info['has_take_profit']
                
                # Kiểm tra và đồng bộ stop loss
                if position.get('stop_loss') and not sl_tp_info['has_stop_loss']:
                    try:
                        # Tạo lệnh stop loss
                        side = 'SELL' if position['side'] == 'LONG' else 'BUY'
                        success, response, error = self._with_retry(
                            self.api.create_order,
                            symbol=symbol,
                            side=side,
                            type='STOP_MARKET',
                            quantity=position['quantity'],
                            stopPrice=position['stop_loss'],
                            reduceOnly='true',
                            closePosition='true'
                        )
                        
                        if success:
                            position['binance_sl_updated'] = True
                            result['stop_loss_synced'] += 1
                            logger.info(f"Đã tạo stop loss cho {symbol} ở giá {position['stop_loss']}")
                        else:
                            result['errors'].append(f"Không thể tạo stop loss cho {symbol}: {str(error)}")
                    except Exception as e:
                        logger.error(f"Lỗi khi tạo stop loss cho {symbol}: {str(e)}")
                        result['errors'].append(f"Lỗi khi tạo stop loss cho {symbol}: {str(e)}")
                
                # Kiểm tra và đồng bộ take profit
                if position.get('take_profit') and not sl_tp_info['has_take_profit']:
                    try:
                        # Tạo lệnh take profit
                        side = 'SELL' if position['side'] == 'LONG' else 'BUY'
                        success, response, error = self._with_retry(
                            self.api.create_order,
                            symbol=symbol,
                            side=side,
                            type='TAKE_PROFIT_MARKET',
                            quantity=position['quantity'],
                            stopPrice=position['take_profit'],
                            reduceOnly='true',
                            closePosition='true'
                        )
                        
                        if success:
                            position['binance_tp_updated'] = True
                            result['take_profit_synced'] += 1
                            logger.info(f"Đã tạo take profit cho {symbol} ở giá {position['take_profit']}")
                        else:
                            result['errors'].append(f"Không thể tạo take profit cho {symbol}: {str(error)}")
                    except Exception as e:
                        logger.error(f"Lỗi khi tạo take profit cho {symbol}: {str(e)}")
                        result['errors'].append(f"Lỗi khi tạo take profit cho {symbol}: {str(e)}")
            
            # Lưu dữ liệu
            self.save_local_positions()
            
            # Cập nhật thông tin đồng bộ
            self.sync_info['sl_synced'] += result['stop_loss_synced']
            self.sync_info['tp_synced'] += result['take_profit_synced']
            
            return result
        except Exception as e:
            logger.error(f"Lỗi khi đồng bộ dữ liệu từ local lên Binance: {str(e)}")
            logger.error(traceback.format_exc())
            result['success'] = False
            result['errors'].append(str(e))
            return result
    
    def full_sync_with_binance(self) -> Dict:
        """
        Thực hiện đồng bộ hóa đầy đủ hai chiều với Binance
        
        Returns:
            Dict: Kết quả đồng bộ
        """
        result = {
            'success': True,
            'positions_synced': 0,
            'stop_loss_synced': 0,
            'take_profit_synced': 0,
            'errors': []
        }
        
        # Đồng bộ từ Binance xuống local
        binance_to_local = self.sync_binance_to_local()
        if not binance_to_local['success']:
            result['success'] = False
            result['errors'].extend(binance_to_local['errors'])
        
        # Cập nhật thông tin đồng bộ
        result['positions_synced'] = binance_to_local['positions_added'] + binance_to_local['positions_updated']
        
        # Đồng bộ từ local lên Binance
        local_to_binance = self.sync_local_to_binance()
        if not local_to_binance['success']:
            result['success'] = False
            result['errors'].extend(local_to_binance['errors'])
        
        # Cập nhật thông tin đồng bộ
        result['stop_loss_synced'] = local_to_binance['stop_loss_synced']
        result['take_profit_synced'] = local_to_binance['take_profit_synced']
        
        # Cập nhật thông tin đồng bộ
        self.sync_info['last_sync_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.sync_info['sync_count'] += 1
        self.sync_info['positions_synced'] += result['positions_synced']
        
        return result
    
    def get_sync_status(self) -> Dict:
        """
        Lấy trạng thái đồng bộ hiện tại
        
        Returns:
            Dict: Trạng thái đồng bộ
        """
        # Bổ sung thông tin hiện tại
        status = self.sync_info.copy()
        status['positions_count'] = len(self.active_positions)
        status['active_symbols'] = list(self.active_positions.keys())
        
        # Xác định trạng thái đồng bộ
        sl_synced = all(p.get('binance_sl_updated', False) for p in self.active_positions.values())
        tp_synced = all(p.get('binance_tp_updated', False) for p in self.active_positions.values())
        
        status['sl_synced'] = sl_synced
        status['tp_synced'] = tp_synced
        status['fully_synced'] = sl_synced and tp_synced
        
        return status
    
    def close_position(self, symbol: str, reason: str = None) -> Dict:
        """
        Đóng một vị thế trên Binance
        
        Args:
            symbol (str): Symbol của vị thế cần đóng
            reason (str, optional): Lý do đóng vị thế
            
        Returns:
            Dict: Kết quả đóng vị thế
        """
        result = {
            'success': False,
            'message': '',
            'order_id': None
        }
        
        # Kiểm tra xem có vị thế không
        if symbol not in self.active_positions:
            result['message'] = f"Không tìm thấy vị thế {symbol}"
            return result
        
        position = self.active_positions[symbol]
        
        try:
            # Hủy tất cả các lệnh đang mở của symbol
            success, cancel_response, error = self._with_retry(
                self.api.cancel_all_open_orders,
                symbol=symbol
            )
            
            if not success:
                logger.warning(f"Không thể hủy các lệnh đang mở của {symbol}: {str(error)}")
            
            # Tạo lệnh đóng vị thế
            side = 'SELL' if position['side'] == 'LONG' else 'BUY'
            quantity = position['quantity']
            
            success, response, error = self._with_retry(
                self.api.create_order,
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity,
                reduceOnly='true'
            )
            
            if success:
                # Cập nhật thông tin vị thế
                position['closed'] = True
                position['exit_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                position['exit_reason'] = reason or "Manual close"
                
                # Lưu thông tin order
                if 'orderId' in response:
                    position['exit_order_id'] = response['orderId']
                    result['order_id'] = response['orderId']
                
                # Lưu dữ liệu
                self.save_local_positions()
                
                # Cập nhật kết quả
                result['success'] = True
                result['message'] = f"Đã đóng vị thế {symbol} thành công"
                
                logger.info(f"Đã đóng vị thế {symbol} thành công, lý do: {reason or 'Manual close'}")
            else:
                result['message'] = f"Không thể đóng vị thế {symbol}: {str(error)}"
                logger.error(result['message'])
        except Exception as e:
            result['message'] = f"Lỗi khi đóng vị thế {symbol}: {str(e)}"
            logger.error(result['message'])
            logger.error(traceback.format_exc())
        
        return result
    
    def update_stop_loss(self, symbol: str, new_stop_loss: float) -> Dict:
        """
        Cập nhật stop loss cho một vị thế
        
        Args:
            symbol (str): Symbol của vị thế
            new_stop_loss (float): Giá stop loss mới
            
        Returns:
            Dict: Kết quả cập nhật
        """
        result = {
            'success': False,
            'message': '',
            'order_id': None
        }
        
        # Kiểm tra xem có vị thế không
        if symbol not in self.active_positions:
            result['message'] = f"Không tìm thấy vị thế {symbol}"
            return result
        
        position = self.active_positions[symbol]
        
        try:
            # Lấy danh sách lệnh đang mở
            success, open_orders, error = self._with_retry(
                self.api.get_open_orders,
                symbol=symbol
            )
            
            if not success:
                result['message'] = f"Không thể lấy danh sách lệnh đang mở của {symbol}: {str(error)}"
                return result
            
            # Tìm và hủy lệnh stop loss cũ
            stop_loss_order_id = None
            for order in open_orders:
                if order['type'] == 'STOP_MARKET' or order['type'] == 'STOP':
                    stop_loss_order_id = order['orderId']
                    break
            
            if stop_loss_order_id:
                success, cancel_response, error = self._with_retry(
                    self.api.cancel_order,
                    symbol=symbol,
                    order_id=stop_loss_order_id
                )
                
                if not success:
                    logger.warning(f"Không thể hủy lệnh stop loss cũ của {symbol}: {str(error)}")
            
            # Tạo lệnh stop loss mới
            side = 'SELL' if position['side'] == 'LONG' else 'BUY'
            quantity = position['quantity']
            
            success, response, error = self._with_retry(
                self.api.create_order,
                symbol=symbol,
                side=side,
                type='STOP_MARKET',
                quantity=quantity,
                stopPrice=new_stop_loss,
                reduceOnly='true',
                closePosition='true'
            )
            
            if success:
                # Cập nhật thông tin vị thế
                position['stop_loss'] = new_stop_loss
                position['binance_sl_updated'] = True
                
                # Lưu thông tin order
                if 'orderId' in response:
                    position['stop_loss_order_id'] = response['orderId']
                    result['order_id'] = response['orderId']
                
                # Lưu dữ liệu
                self.save_local_positions()
                
                # Cập nhật kết quả
                result['success'] = True
                result['message'] = f"Đã cập nhật stop loss cho {symbol} thành {new_stop_loss}"
                
                logger.info(f"Đã cập nhật stop loss cho {symbol} thành {new_stop_loss}")
            else:
                result['message'] = f"Không thể tạo stop loss mới cho {symbol}: {str(error)}"
                logger.error(result['message'])
        except Exception as e:
            result['message'] = f"Lỗi khi cập nhật stop loss cho {symbol}: {str(e)}"
            logger.error(result['message'])
            logger.error(traceback.format_exc())
        
        return result
    
    def update_take_profit(self, symbol: str, new_take_profit: float) -> Dict:
        """
        Cập nhật take profit cho một vị thế
        
        Args:
            symbol (str): Symbol của vị thế
            new_take_profit (float): Giá take profit mới
            
        Returns:
            Dict: Kết quả cập nhật
        """
        result = {
            'success': False,
            'message': '',
            'order_id': None
        }
        
        # Kiểm tra xem có vị thế không
        if symbol not in self.active_positions:
            result['message'] = f"Không tìm thấy vị thế {symbol}"
            return result
        
        position = self.active_positions[symbol]
        
        try:
            # Lấy danh sách lệnh đang mở
            success, open_orders, error = self._with_retry(
                self.api.get_open_orders,
                symbol=symbol
            )
            
            if not success:
                result['message'] = f"Không thể lấy danh sách lệnh đang mở của {symbol}: {str(error)}"
                return result
            
            # Tìm và hủy lệnh take profit cũ
            take_profit_order_id = None
            for order in open_orders:
                if order['type'] == 'TAKE_PROFIT_MARKET' or order['type'] == 'TAKE_PROFIT':
                    take_profit_order_id = order['orderId']
                    break
            
            if take_profit_order_id:
                success, cancel_response, error = self._with_retry(
                    self.api.cancel_order,
                    symbol=symbol,
                    order_id=take_profit_order_id
                )
                
                if not success:
                    logger.warning(f"Không thể hủy lệnh take profit cũ của {symbol}: {str(error)}")
            
            # Tạo lệnh take profit mới
            side = 'SELL' if position['side'] == 'LONG' else 'BUY'
            quantity = position['quantity']
            
            success, response, error = self._with_retry(
                self.api.create_order,
                symbol=symbol,
                side=side,
                type='TAKE_PROFIT_MARKET',
                quantity=quantity,
                stopPrice=new_take_profit,
                reduceOnly='true',
                closePosition='true'
            )
            
            if success:
                # Cập nhật thông tin vị thế
                position['take_profit'] = new_take_profit
                position['binance_tp_updated'] = True
                
                # Lưu thông tin order
                if 'orderId' in response:
                    position['take_profit_order_id'] = response['orderId']
                    result['order_id'] = response['orderId']
                
                # Lưu dữ liệu
                self.save_local_positions()
                
                # Cập nhật kết quả
                result['success'] = True
                result['message'] = f"Đã cập nhật take profit cho {symbol} thành {new_take_profit}"
                
                logger.info(f"Đã cập nhật take profit cho {symbol} thành {new_take_profit}")
            else:
                result['message'] = f"Không thể tạo take profit mới cho {symbol}: {str(error)}"
                logger.error(result['message'])
        except Exception as e:
            result['message'] = f"Lỗi khi cập nhật take profit cho {symbol}: {str(e)}"
            logger.error(result['message'])
            logger.error(traceback.format_exc())
        
        return result
    
    def archive_closed_positions(self) -> Dict:
        """
        Lưu trữ các vị thế đã đóng vào file lịch sử
        
        Returns:
            Dict: Kết quả lưu trữ
        """
        result = {
            'success': True,
            'archived_positions': 0,
            'message': ''
        }
        
        try:
            # Tìm các vị thế đã đóng
            closed_positions = {}
            for symbol, position in list(self.active_positions.items()):
                if position.get('closed', False):
                    closed_positions[symbol] = position
                    del self.active_positions[symbol]
            
            # Nếu không có vị thế đã đóng
            if not closed_positions:
                result['message'] = "Không có vị thế đã đóng để lưu trữ"
                return result
            
            # Đường dẫn file lịch sử
            history_file = 'trading_history.json'
            
            # Tải lịch sử cũ nếu có
            history = []
            if os.path.exists(history_file):
                try:
                    with open(history_file, 'r') as f:
                        history = json.load(f)
                except Exception as e:
                    logger.warning(f"Không thể tải lịch sử từ {history_file}, tạo mới: {str(e)}")
                    history = []
            
            # Thêm vị thế đã đóng vào lịch sử
            for symbol, position in closed_positions.items():
                position['archive_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                history.append(position)
            
            # Lưu lịch sử
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
            
            # Lưu lại vị thế active
            self.save_local_positions()
            
            # Cập nhật kết quả
            result['archived_positions'] = len(closed_positions)
            result['message'] = f"Đã lưu trữ {len(closed_positions)} vị thế đã đóng"
            
            logger.info(f"Đã lưu trữ {len(closed_positions)} vị thế đã đóng vào {history_file}")
            return result
        except Exception as e:
            logger.error(f"Lỗi khi lưu trữ vị thế đã đóng: {str(e)}")
            logger.error(traceback.format_exc())
            result['success'] = False
            result['message'] = f"Lỗi khi lưu trữ vị thế đã đóng: {str(e)}"
            return result


def main():
    """Hàm chính để test BinanceSynchronizer"""
    
    print("=== Testing BinanceSynchronizer ===\n")
    
    # Khởi tạo BinanceAPI
    api = BinanceAPI()
    
    # Khởi tạo BinanceSynchronizer
    sync = BinanceSynchronizer(api)
    
    # Kiểm tra tính toàn vẹn
    print("Kiểm tra tính toàn vẹn của dữ liệu vị thế local...")
    integrity_result = sync.check_local_positions_integrity()
    print(f"Kết quả: {integrity_result['valid_positions']} vị thế hợp lệ, "
         f"{integrity_result['invalid_positions']} vị thế không hợp lệ")
    if integrity_result['issues']:
        print(f"Vấn đề: {'; '.join(integrity_result['issues'])}")
    
    # Đồng bộ đầy đủ
    print("\nĐồng bộ đầy đủ với Binance...")
    sync_result = sync.full_sync_with_binance()
    print(f"Kết quả đồng bộ: {'Thành công' if sync_result['success'] else 'Thất bại'}")
    print(f"- Vị thế đã đồng bộ: {sync_result['positions_synced']}")
    print(f"- Stop loss đã đồng bộ: {sync_result['stop_loss_synced']}")
    print(f"- Take profit đã đồng bộ: {sync_result['take_profit_synced']}")
    if sync_result['errors']:
        print(f"- Lỗi: {'; '.join(sync_result['errors'])}")
    
    # Trạng thái đồng bộ
    print("\nTrạng thái đồng bộ hiện tại:")
    sync_status = sync.get_sync_status()
    print(f"- Số lượng vị thế: {sync_status['positions_count']}")
    print(f"- Các symbol: {', '.join(sync_status['active_symbols'])}")
    print(f"- Stop loss đã đồng bộ: {sync_status['sl_synced']}")
    print(f"- Take profit đã đồng bộ: {sync_status['tp_synced']}")
    print(f"- Đồng bộ đầy đủ: {sync_status['fully_synced']}")


if __name__ == "__main__":
    main()