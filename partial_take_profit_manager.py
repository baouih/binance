"""
Partial Take Profit Manager - Quản lý chốt lời từng phần

Module này cung cấp các công cụ để quản lý và thực hiện chốt lời từng phần
theo các mức cấu hình khác nhau dựa trên lợi nhuận, thời gian và chế độ thị trường.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import json
from typing import Dict, List, Tuple, Optional, Union, Any
import matplotlib.pyplot as plt
from collections import defaultdict
import math

# Thêm các module tự tạo nếu cần
from enhanced_market_regime_detector import EnhancedMarketRegimeDetector

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('partial_take_profit_manager')

class PartialTakeProfitManager:
    """
    Quản lý chiến lược chốt lời từng phần và thiết lập các mức chốt lời
    dựa trên các tham số và chế độ thị trường.
    """
    
    # Cấu hình mức chốt lời mặc định cho từng chế độ thị trường
    DEFAULT_TP_LEVELS = {
        'trending_bullish': [
            {'percent': 2.0, 'quantity': 0.25, 'adjust_stop': True},
            {'percent': 4.0, 'quantity': 0.25, 'adjust_stop': True},
            {'percent': 7.0, 'quantity': 0.25, 'adjust_stop': True},
            {'percent': 12.0, 'quantity': 0.25, 'adjust_stop': True}
        ],
        'trending_bearish': [
            {'percent': 2.0, 'quantity': 0.25, 'adjust_stop': True},
            {'percent': 4.0, 'quantity': 0.25, 'adjust_stop': True},
            {'percent': 7.0, 'quantity': 0.25, 'adjust_stop': True},
            {'percent': 12.0, 'quantity': 0.25, 'adjust_stop': True}
        ],
        'ranging_narrow': [
            {'percent': 1.0, 'quantity': 0.3, 'adjust_stop': True},
            {'percent': 2.0, 'quantity': 0.3, 'adjust_stop': True},
            {'percent': 3.0, 'quantity': 0.4, 'adjust_stop': True}
        ],
        'ranging_wide': [
            {'percent': 1.5, 'quantity': 0.3, 'adjust_stop': True},
            {'percent': 3.0, 'quantity': 0.3, 'adjust_stop': True},
            {'percent': 5.0, 'quantity': 0.4, 'adjust_stop': True}
        ],
        'volatile_breakout': [
            {'percent': 2.0, 'quantity': 0.2, 'adjust_stop': True},
            {'percent': 4.0, 'quantity': 0.2, 'adjust_stop': True},
            {'percent': 6.0, 'quantity': 0.2, 'adjust_stop': True},
            {'percent': 10.0, 'quantity': 0.2, 'adjust_stop': True},
            {'percent': 15.0, 'quantity': 0.2, 'adjust_stop': True}
        ],
        'quiet_accumulation': [
            {'percent': 0.8, 'quantity': 0.5, 'adjust_stop': True},
            {'percent': 1.5, 'quantity': 0.5, 'adjust_stop': True}
        ],
        'neutral': [
            {'percent': 1.5, 'quantity': 0.3, 'adjust_stop': True},
            {'percent': 3.0, 'quantity': 0.3, 'adjust_stop': True},
            {'percent': 5.0, 'quantity': 0.4, 'adjust_stop': True}
        ]
    }
    
    # Cấu hình stop loss adjustment cho từng mức chốt lời
    DEFAULT_STOP_ADJUSTMENTS = {
        'after_first': {'type': 'breakeven', 'value': 0},
        'after_second': {'type': 'lock_profit', 'value': 0.3},  # Lock in 30% of profit
        'after_third': {'type': 'lock_profit', 'value': 0.5},   # Lock in 50% of profit
        'after_fourth': {'type': 'lock_profit', 'value': 0.7},  # Lock in 70% of profit
        'after_fifth': {'type': 'lock_profit', 'value': 0.8}    # Lock in 80% of profit
    }
    
    def __init__(self, data_storage_path: str = 'data/partial_take_profit'):
        """
        Khởi tạo Partial Take Profit Manager.
        
        Args:
            data_storage_path (str): Đường dẫn lưu trữ dữ liệu và cấu hình
        """
        self.data_storage_path = data_storage_path
        
        # Tạo thư mục lưu trữ nếu chưa tồn tại
        os.makedirs(data_storage_path, exist_ok=True)
        
        # Khởi tạo detector chế độ thị trường
        self.regime_detector = EnhancedMarketRegimeDetector()
        
        # Cấu hình cho các chế độ thị trường
        self.tp_levels_config = self.DEFAULT_TP_LEVELS.copy()
        self.stop_adjustments_config = self.DEFAULT_STOP_ADJUSTMENTS.copy()
        
        # Lưu trữ trạng thái chốt lời
        self.active_tp_levels = {}  # {symbol: {position_id: [tp_levels]}}
        self.stop_levels = {}  # {symbol: {position_id: stop_level}}
        self.executed_tps = {}  # {symbol: {position_id: [executed_tps]}}
        
        # Tải cấu hình nếu có
        self._load_config()
    
    def set_tp_levels(self, market_data: pd.DataFrame, position_data: Dict, 
                    override_regime: str = None) -> Dict:
        """
        Thiết lập các mức chốt lời từng phần cho một vị thế.
        
        Args:
            market_data (pd.DataFrame): DataFrame chứa dữ liệu thị trường
            position_data (Dict): Thông tin về vị thế hiện tại
            override_regime (str, optional): Ghi đè chế độ thị trường
            
        Returns:
            Dict: Thông tin về các mức chốt lời
        """
        try:
            # Lấy thông tin vị thế
            symbol = position_data.get('symbol', 'UNKNOWN')
            position_id = position_data.get('position_id', 'pos_1')
            position_type = position_data.get('position_type', 'long')
            entry_price = position_data.get('entry_price', 0)
            current_price = position_data.get('current_price', market_data['close'].iloc[-1])
            position_size = position_data.get('position_size', 1.0)
            
            # Xác định chế độ thị trường
            if override_regime:
                regime = override_regime
            else:
                # Phát hiện chế độ thị trường từ dữ liệu
                regime_result = self.regime_detector.detect_regime(market_data)
                regime = regime_result['regime']
            
            # Lấy cấu hình chốt lời cho chế độ thị trường
            tp_levels = self.tp_levels_config.get(regime, self.tp_levels_config['neutral'])
            
            # Tính toán giá chốt lời cho từng mức
            calculated_levels = []
            remaining_size = position_size
            
            for i, level in enumerate(tp_levels):
                # Tính giá chốt lời
                if position_type == 'long':
                    tp_price = entry_price * (1 + level['percent'] / 100)
                else:
                    tp_price = entry_price * (1 - level['percent'] / 100)
                
                # Tính số lượng chốt
                tp_quantity = level['quantity'] * position_size
                
                # Đảm bảo không chốt quá số lượng còn lại
                tp_quantity = min(tp_quantity, remaining_size)
                remaining_size -= tp_quantity
                
                # Tính điều chỉnh stop loss
                adjust_key = f'after_{self._ordinal(i+1)}'
                stop_adjustment = self.stop_adjustments_config.get(adjust_key, {'type': 'no_change', 'value': 0})
                
                # Thêm vào danh sách
                calculated_levels.append({
                    'level': i + 1,
                    'price': tp_price,
                    'percent': level['percent'],
                    'quantity': tp_quantity,
                    'quantity_percent': level['quantity'] * 100,
                    'adjust_stop': level.get('adjust_stop', True),
                    'stop_adjustment': stop_adjustment,
                    'executed': False
                })
            
            # Lưu trữ các mức chốt lời
            if symbol not in self.active_tp_levels:
                self.active_tp_levels[symbol] = {}
            
            self.active_tp_levels[symbol][position_id] = calculated_levels
            
            # Khởi tạo danh sách chốt lời đã thực hiện
            if symbol not in self.executed_tps:
                self.executed_tps[symbol] = {}
            
            if position_id not in self.executed_tps[symbol]:
                self.executed_tps[symbol][position_id] = []
            
            # Tạo kết quả
            result = {
                'symbol': symbol,
                'position_id': position_id,
                'position_type': position_type,
                'entry_price': entry_price,
                'current_price': current_price,
                'position_size': position_size,
                'regime': regime,
                'tp_levels': calculated_levels,
                'timestamp': datetime.now().isoformat()
            }
            
            # Lưu cấu hình
            self._save_position_tp_config(symbol, position_id, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập mức chốt lời: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Trả về mặc định nếu có lỗi
            return {
                'symbol': position_data.get('symbol', 'UNKNOWN'),
                'position_id': position_data.get('position_id', 'pos_1'),
                'position_type': position_data.get('position_type', 'long'),
                'entry_price': position_data.get('entry_price', 0),
                'current_price': position_data.get('current_price', 0),
                'position_size': position_data.get('position_size', 1.0),
                'regime': 'unknown',
                'tp_levels': [],
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def check_tp_signals(self, symbol: str, position_id: str, current_price: float) -> Dict:
        """
        Kiểm tra các tín hiệu chốt lời từng phần dựa trên giá hiện tại.
        
        Args:
            symbol (str): Mã cặp tiền giao dịch
            position_id (str): ID của vị thế
            current_price (float): Giá hiện tại
            
        Returns:
            Dict: Thông tin tín hiệu chốt lời
        """
        try:
            # Kiểm tra xem có cấu hình chốt lời cho vị thế này không
            if symbol not in self.active_tp_levels or position_id not in self.active_tp_levels[symbol]:
                logger.warning(f"Không tìm thấy cấu hình chốt lời cho {symbol} - {position_id}")
                return {'tp_signal': False}
            
            # Lấy thông tin TP đã thiết lập
            position_tp_config = self._load_position_tp_config(symbol, position_id)
            if not position_tp_config:
                logger.warning(f"Không tìm thấy cấu hình chốt lời đã lưu cho {symbol} - {position_id}")
                return {'tp_signal': False}
            
            position_type = position_tp_config['position_type']
            tp_levels = position_tp_config['tp_levels']
            
            # Kiểm tra xem đã chốt lời hết chưa
            not_executed_levels = [level for level in tp_levels if not level['executed']]
            if not not_executed_levels:
                logger.info(f"Đã thực hiện tất cả các mức chốt lời cho {symbol} - {position_id}")
                return {'tp_signal': False, 'reason': 'All levels executed'}
            
            # Kiểm tra từng mức chốt lời chưa thực hiện
            for level in not_executed_levels:
                tp_price = level['price']
                
                # Kiểm tra điều kiện chốt lời
                if position_type == 'long' and current_price >= tp_price:
                    # Chốt lời long position
                    return {
                        'tp_signal': True,
                        'level': level['level'],
                        'price': tp_price,
                        'quantity': level['quantity'],
                        'quantity_percent': level['quantity_percent'],
                        'adjust_stop': level['adjust_stop'],
                        'stop_adjustment': level['stop_adjustment'],
                        'position_type': position_type
                    }
                elif position_type == 'short' and current_price <= tp_price:
                    # Chốt lời short position
                    return {
                        'tp_signal': True,
                        'level': level['level'],
                        'price': tp_price,
                        'quantity': level['quantity'],
                        'quantity_percent': level['quantity_percent'],
                        'adjust_stop': level['adjust_stop'],
                        'stop_adjustment': level['stop_adjustment'],
                        'position_type': position_type
                    }
            
            # Không có tín hiệu chốt lời
            return {'tp_signal': False, 'position_type': position_type}
            
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra tín hiệu chốt lời: {str(e)}")
            return {'tp_signal': False, 'error': str(e)}
    
    def execute_partial_tp(self, symbol: str, position_id: str, execution_data: Dict) -> Dict:
        """
        Thực hiện chốt lời từng phần.
        
        Args:
            symbol (str): Mã cặp tiền giao dịch
            position_id (str): ID của vị thế
            execution_data (Dict): Thông tin thực hiện (giá, số lượng)
            
        Returns:
            Dict: Kết quả thực hiện
        """
        try:
            # Kiểm tra xem có cấu hình chốt lời cho vị thế này không
            if symbol not in self.active_tp_levels or position_id not in self.active_tp_levels[symbol]:
                logger.warning(f"Không tìm thấy cấu hình chốt lời cho {symbol} - {position_id}")
                return {'success': False, 'error': 'No TP configuration found'}
            
            # Lấy thông tin TP đã thiết lập
            position_tp_config = self._load_position_tp_config(symbol, position_id)
            if not position_tp_config:
                logger.warning(f"Không tìm thấy cấu hình chốt lời đã lưu cho {symbol} - {position_id}")
                return {'success': False, 'error': 'No TP configuration found'}
            
            # Thông tin thực hiện
            level = execution_data.get('level')
            execution_price = execution_data.get('price')
            execution_quantity = execution_data.get('quantity')
            
            # Tìm mức TP tương ứng
            tp_levels = position_tp_config['tp_levels']
            target_level = None
            
            for tp_level in tp_levels:
                if tp_level['level'] == level and not tp_level['executed']:
                    target_level = tp_level
                    break
            
            if not target_level:
                logger.warning(f"Không tìm thấy mức TP {level} chưa thực hiện cho {symbol} - {position_id}")
                return {'success': False, 'error': f'TP level {level} not found or already executed'}
            
            # Cập nhật trạng thái executed
            target_level['executed'] = True
            target_level['execution_price'] = execution_price
            target_level['execution_quantity'] = execution_quantity
            target_level['execution_time'] = datetime.now().isoformat()
            
            # Cập nhật danh sách đã thực hiện
            if symbol not in self.executed_tps:
                self.executed_tps[symbol] = {}
            
            if position_id not in self.executed_tps[symbol]:
                self.executed_tps[symbol][position_id] = []
            
            self.executed_tps[symbol][position_id].append(target_level)
            
            # Điều chỉnh stop loss nếu cần
            new_stop = None
            if target_level['adjust_stop']:
                # Lấy thông tin điều chỉnh stop
                stop_adjustment = target_level['stop_adjustment']
                adjustment_type = stop_adjustment['type']
                adjustment_value = stop_adjustment['value']
                
                # Thông tin vị thế
                entry_price = position_tp_config['entry_price']
                position_type = position_tp_config['position_type']
                
                # Tính stop loss mới
                if adjustment_type == 'breakeven':
                    # Đưa stop về mức hòa vốn
                    new_stop = entry_price
                elif adjustment_type == 'lock_profit':
                    # Khóa một phần lợi nhuận
                    if position_type == 'long':
                        profit = execution_price - entry_price
                        new_stop = entry_price + profit * adjustment_value
                    else:
                        profit = entry_price - execution_price
                        new_stop = entry_price - profit * adjustment_value
                
                # Lưu trữ stop mới
                if symbol not in self.stop_levels:
                    self.stop_levels[symbol] = {}
                
                self.stop_levels[symbol][position_id] = new_stop
            
            # Cập nhật cấu hình
            position_tp_config['tp_levels'] = tp_levels
            if new_stop:
                position_tp_config['adjusted_stop'] = new_stop
            
            # Lưu cấu hình
            self._save_position_tp_config(symbol, position_id, position_tp_config)
            
            # Tạo kết quả
            result = {
                'success': True,
                'symbol': symbol,
                'position_id': position_id,
                'level': level,
                'execution_price': execution_price,
                'execution_quantity': execution_quantity,
                'execution_time': datetime.now().isoformat(),
                'remaining_levels': len([tp for tp in tp_levels if not tp['executed']]),
                'adjusted_stop': new_stop,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Đã thực hiện chốt lời mức {level} cho {symbol} - {position_id} với giá {execution_price}")
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi thực hiện chốt lời: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def reset_position_tp(self, symbol: str, position_id: str) -> Dict:
        """
        Reset cấu hình chốt lời cho một vị thế.
        
        Args:
            symbol (str): Mã cặp tiền giao dịch
            position_id (str): ID của vị thế
            
        Returns:
            Dict: Kết quả reset
        """
        try:
            # Xóa cấu hình chốt lời
            if symbol in self.active_tp_levels and position_id in self.active_tp_levels[symbol]:
                del self.active_tp_levels[symbol][position_id]
            
            # Xóa danh sách đã thực hiện
            if symbol in self.executed_tps and position_id in self.executed_tps[symbol]:
                del self.executed_tps[symbol][position_id]
            
            # Xóa stop level
            if symbol in self.stop_levels and position_id in self.stop_levels[symbol]:
                del self.stop_levels[symbol][position_id]
            
            # Xóa file cấu hình
            config_file = os.path.join(self.data_storage_path, f'{symbol}_{position_id}_tp_config.json')
            if os.path.exists(config_file):
                os.remove(config_file)
            
            logger.info(f"Đã reset cấu hình chốt lời cho {symbol} - {position_id}")
            
            return {'success': True, 'message': f'Reset TP configuration for {symbol} - {position_id}'}
            
        except Exception as e:
            logger.error(f"Lỗi khi reset cấu hình chốt lời: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_position_tp_status(self, symbol: str, position_id: str) -> Dict:
        """
        Lấy trạng thái chốt lời của một vị thế.
        
        Args:
            symbol (str): Mã cặp tiền giao dịch
            position_id (str): ID của vị thế
            
        Returns:
            Dict: Trạng thái chốt lời
        """
        try:
            # Kiểm tra xem có cấu hình chốt lời cho vị thế này không
            if symbol not in self.active_tp_levels or position_id not in self.active_tp_levels[symbol]:
                logger.warning(f"Không tìm thấy cấu hình chốt lời cho {symbol} - {position_id}")
                return {'success': False, 'error': 'No TP configuration found'}
            
            # Lấy thông tin TP đã thiết lập
            position_tp_config = self._load_position_tp_config(symbol, position_id)
            if not position_tp_config:
                logger.warning(f"Không tìm thấy cấu hình chốt lời đã lưu cho {symbol} - {position_id}")
                return {'success': False, 'error': 'No TP configuration found'}
            
            # Lấy danh sách TP đã thực hiện
            executed_tps = self.executed_tps.get(symbol, {}).get(position_id, [])
            
            # Tính toán số lượng đã thực hiện
            executed_quantity = sum(tp.get('execution_quantity', 0) for tp in executed_tps)
            
            # Tính toán tổng số lượng
            total_quantity = position_tp_config.get('position_size', 0)
            
            # Tính toán số lượng còn lại
            remaining_quantity = total_quantity - executed_quantity
            
            # Tính toán tỷ lệ đã thực hiện
            executed_percent = executed_quantity / total_quantity * 100 if total_quantity > 0 else 0
            
            # Lấy stop level hiện tại
            current_stop = self.stop_levels.get(symbol, {}).get(position_id)
            
            # Tạo kết quả
            result = {
                'success': True,
                'symbol': symbol,
                'position_id': position_id,
                'position_type': position_tp_config['position_type'],
                'entry_price': position_tp_config['entry_price'],
                'total_quantity': total_quantity,
                'executed_quantity': executed_quantity,
                'remaining_quantity': remaining_quantity,
                'executed_percent': executed_percent,
                'tp_levels': position_tp_config['tp_levels'],
                'executed_tps': executed_tps,
                'current_stop': current_stop,
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy trạng thái chốt lời: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def update_tp_config(self, regime: str, tp_levels: List[Dict]) -> None:
        """
        Cập nhật cấu hình chốt lời cho một chế độ thị trường.
        
        Args:
            regime (str): Tên chế độ thị trường
            tp_levels (List[Dict]): Danh sách các mức chốt lời
        """
        # Kiểm tra cấu trúc dữ liệu
        required_fields = ['percent', 'quantity']
        for level in tp_levels:
            missing = [field for field in required_fields if field not in level]
            if missing:
                logger.warning(f"Thiếu các trường bắt buộc {missing} trong cấu hình chốt lời")
                return
        
        # Cập nhật cấu hình
        self.tp_levels_config[regime] = tp_levels
        logger.info(f"Đã cập nhật cấu hình chốt lời cho chế độ {regime}")
        
        # Lưu cấu hình
        self._save_config()
    
    def update_stop_adjustment_config(self, adjustment_config: Dict) -> None:
        """
        Cập nhật cấu hình điều chỉnh stop loss.
        
        Args:
            adjustment_config (Dict): Cấu hình điều chỉnh stop loss
        """
        # Cập nhật cấu hình
        self.stop_adjustments_config.update(adjustment_config)
        logger.info("Đã cập nhật cấu hình điều chỉnh stop loss")
        
        # Lưu cấu hình
        self._save_config()
    
    def custom_tp_levels_for_position(self, symbol: str, position_id: str, 
                                   position_data: Dict, custom_levels: List[Dict]) -> Dict:
        """
        Thiết lập cấu hình chốt lời tùy chỉnh cho một vị thế cụ thể.
        
        Args:
            symbol (str): Mã cặp tiền giao dịch
            position_id (str): ID của vị thế
            position_data (Dict): Thông tin về vị thế
            custom_levels (List[Dict]): Danh sách các mức chốt lời tùy chỉnh
            
        Returns:
            Dict: Kết quả thiết lập
        """
        try:
            # Kiểm tra cấu trúc dữ liệu
            required_fields = ['percent', 'quantity']
            for level in custom_levels:
                missing = [field for field in required_fields if field not in level]
                if missing:
                    logger.warning(f"Thiếu các trường bắt buộc {missing} trong cấu hình chốt lời tùy chỉnh")
                    return {'success': False, 'error': f'Missing required fields: {missing}'}
            
            # Lấy thông tin vị thế
            position_type = position_data.get('position_type', 'long')
            entry_price = position_data.get('entry_price', 0)
            position_size = position_data.get('position_size', 1.0)
            
            # Tính toán giá chốt lời cho từng mức
            calculated_levels = []
            remaining_size = position_size
            
            for i, level in enumerate(custom_levels):
                # Tính giá chốt lời
                if position_type == 'long':
                    tp_price = entry_price * (1 + level['percent'] / 100)
                else:
                    tp_price = entry_price * (1 - level['percent'] / 100)
                
                # Tính số lượng chốt
                tp_quantity = level['quantity'] * position_size
                
                # Đảm bảo không chốt quá số lượng còn lại
                tp_quantity = min(tp_quantity, remaining_size)
                remaining_size -= tp_quantity
                
                # Tính điều chỉnh stop loss
                adjust_key = f'after_{self._ordinal(i+1)}'
                stop_adjustment = self.stop_adjustments_config.get(adjust_key, {'type': 'no_change', 'value': 0})
                
                # Thêm vào danh sách
                calculated_levels.append({
                    'level': i + 1,
                    'price': tp_price,
                    'percent': level['percent'],
                    'quantity': tp_quantity,
                    'quantity_percent': level['quantity'] * 100,
                    'adjust_stop': level.get('adjust_stop', True),
                    'stop_adjustment': stop_adjustment,
                    'executed': False
                })
            
            # Lưu trữ các mức chốt lời
            if symbol not in self.active_tp_levels:
                self.active_tp_levels[symbol] = {}
            
            self.active_tp_levels[symbol][position_id] = calculated_levels
            
            # Khởi tạo danh sách chốt lời đã thực hiện
            if symbol not in self.executed_tps:
                self.executed_tps[symbol] = {}
            
            if position_id not in self.executed_tps[symbol]:
                self.executed_tps[symbol][position_id] = []
            
            # Tạo kết quả
            result = {
                'success': True,
                'symbol': symbol,
                'position_id': position_id,
                'position_type': position_type,
                'entry_price': entry_price,
                'position_size': position_size,
                'tp_levels': calculated_levels,
                'custom': True,
                'timestamp': datetime.now().isoformat()
            }
            
            # Lưu cấu hình
            self._save_position_tp_config(symbol, position_id, result)
            
            logger.info(f"Đã thiết lập cấu hình chốt lời tùy chỉnh cho {symbol} - {position_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập cấu hình chốt lời tùy chỉnh: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def visualize_tp_levels(self, symbol: str, position_id: str, 
                          market_data: Optional[pd.DataFrame] = None,
                          output_path: Optional[str] = None) -> str:
        """
        Tạo biểu đồ các mức chốt lời.
        
        Args:
            symbol (str): Mã cặp tiền giao dịch
            position_id (str): ID của vị thế
            market_data (pd.DataFrame, optional): Dữ liệu thị trường để vẽ biểu đồ
            output_path (str, optional): Đường dẫn lưu biểu đồ
            
        Returns:
            str: Đường dẫn đến biểu đồ
        """
        try:
            # Lấy thông tin TP đã thiết lập
            position_tp_config = self._load_position_tp_config(symbol, position_id)
            if not position_tp_config:
                logger.warning(f"Không tìm thấy cấu hình chốt lời cho {symbol} - {position_id}")
                return "Error: TP configuration not found"
            
            # Tạo biểu đồ
            plt.figure(figsize=(12, 8))
            
            # Vẽ biểu đồ giá nếu có dữ liệu thị trường
            if market_data is not None and not market_data.empty:
                plt.subplot(2, 1, 1)
                plt.plot(market_data.index, market_data['close'], color='black', linewidth=1.5)
                plt.title(f'Price Chart with Take Profit Levels - {symbol}')
                plt.ylabel('Price')
                plt.grid(True, alpha=0.3)
                
                # Giới hạn trục x
                if len(market_data) > 50:
                    plt.xlim(market_data.index[-50], market_data.index[-1])
            
            # Lấy thông tin vị thế
            entry_price = position_tp_config['entry_price']
            tp_levels = position_tp_config['tp_levels']
            position_type = position_tp_config['position_type']
            current_stop = position_tp_config.get('adjusted_stop')
            
            # Vẽ entry price
            if market_data is not None and not market_data.empty:
                plt.axhline(y=entry_price, color='blue', linestyle='--', linewidth=1.5, label=f'Entry: {entry_price:.2f}')
                
                # Vẽ stop loss nếu có
                if current_stop:
                    plt.axhline(y=current_stop, color='red', linestyle='--', linewidth=1.5, label=f'Stop Loss: {current_stop:.2f}')
                
                # Vẽ các mức take profit
                for tp in tp_levels:
                    color = 'green' if not tp['executed'] else 'lightgreen'
                    style = '-' if not tp['executed'] else '--'
                    label = f"TP {tp['level']}: {tp['price']:.2f} ({tp['quantity_percent']:.0f}%) - {'Executed' if tp['executed'] else 'Active'}"
                    plt.axhline(y=tp['price'], color=color, linestyle=style, linewidth=1.5, label=label)
                
                plt.legend()
            
            # Vẽ biểu đồ phân phối chốt lời
            plt.subplot(2, 1, 2 if market_data is not None and not market_data.empty else 1, 1)
            
            # Chuẩn bị dữ liệu
            levels = [tp['level'] for tp in tp_levels]
            quantities = [tp['quantity_percent'] for tp in tp_levels]
            prices = [tp['price'] for tp in tp_levels]
            executed = [tp['executed'] for tp in tp_levels]
            
            # Tạo màu cho các cột
            colors = ['green' if not exe else 'lightgreen' for exe in executed]
            
            # Vẽ biểu đồ cột
            bars = plt.bar(levels, quantities, color=colors, alpha=0.7)
            
            # Thêm giá chốt lời lên mỗi cột
            for i, bar in enumerate(bars):
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2, height + 1,
                        f"{prices[i]:.2f}", ha='center', va='bottom')
            
            plt.title('Take Profit Distribution')
            plt.xlabel('Take Profit Level')
            plt.ylabel('Quantity (%)')
            plt.xticks(levels)
            plt.grid(True, alpha=0.3)
            
            # Thêm chú thích
            plt.figtext(0.5, 0.01, f"Position: {position_type.upper()}, Entry Price: {entry_price:.2f}, Stop Loss: {current_stop if current_stop else 'N/A'}", 
                     ha='center', fontsize=10)
            
            plt.tight_layout(rect=[0, 0.03, 1, 0.97])
            
            # Lưu biểu đồ
            if output_path is None:
                output_path = os.path.join(self.data_storage_path, f'{symbol}_{position_id}_tp_chart.png')
            
            plt.savefig(output_path)
            plt.close()
            
            logger.info(f"Đã tạo biểu đồ các mức chốt lời tại: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ các mức chốt lời: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return "Error creating chart"
    
    def _save_position_tp_config(self, symbol: str, position_id: str, config: Dict) -> None:
        """Lưu cấu hình chốt lời cho một vị thế."""
        try:
            # Tạo thư mục lưu trữ
            os.makedirs(self.data_storage_path, exist_ok=True)
            
            # Lưu vào file
            config_file = os.path.join(self.data_storage_path, f'{symbol}_{position_id}_tp_config.json')
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình chốt lời: {str(e)}")
    
    def _load_position_tp_config(self, symbol: str, position_id: str) -> Optional[Dict]:
        """Tải cấu hình chốt lời cho một vị thế."""
        try:
            # Tìm file cấu hình
            config_file = os.path.join(self.data_storage_path, f'{symbol}_{position_id}_tp_config.json')
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    return json.load(f)
            
            return None
            
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình chốt lời: {str(e)}")
            return None
    
    def _save_config(self) -> None:
        """Lưu cấu hình tổng thể."""
        try:
            # Tạo thư mục lưu trữ
            os.makedirs(self.data_storage_path, exist_ok=True)
            
            # Lưu cấu hình TP levels
            tp_config_file = os.path.join(self.data_storage_path, 'tp_levels_config.json')
            with open(tp_config_file, 'w') as f:
                json.dump(self.tp_levels_config, f, indent=2)
            
            # Lưu cấu hình stop adjustments
            stop_config_file = os.path.join(self.data_storage_path, 'stop_adjustments_config.json')
            with open(stop_config_file, 'w') as f:
                json.dump(self.stop_adjustments_config, f, indent=2)
                
            logger.info(f"Đã lưu cấu hình tại: {self.data_storage_path}")
                
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {str(e)}")
    
    def _load_config(self) -> None:
        """Tải cấu hình tổng thể."""
        try:
            # Tải cấu hình TP levels
            tp_config_file = os.path.join(self.data_storage_path, 'tp_levels_config.json')
            if os.path.exists(tp_config_file):
                with open(tp_config_file, 'r') as f:
                    self.tp_levels_config = json.load(f)
            
            # Tải cấu hình stop adjustments
            stop_config_file = os.path.join(self.data_storage_path, 'stop_adjustments_config.json')
            if os.path.exists(stop_config_file):
                with open(stop_config_file, 'r') as f:
                    self.stop_adjustments_config = json.load(f)
                    
            logger.info(f"Đã tải cấu hình từ: {self.data_storage_path}")
                    
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
    
    def _ordinal(self, n: int) -> str:
        """Chuyển đổi số thành dạng thứ tự."""
        if 10 <= n % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return f"{n}{suffix}"


if __name__ == "__main__":
    # Ví dụ sử dụng
    tp_manager = PartialTakeProfitManager()
    
    # Tạo dữ liệu mẫu
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    # Dữ liệu mẫu cho thị trường
    dates = [datetime.now() - timedelta(hours=i) for i in range(100, 0, -1)]
    close_prices = [50000 + i * 10 for i in range(100)]
    
    # Tạo DataFrame
    market_data = pd.DataFrame({
        'open': [p - 50 for p in close_prices],
        'high': [p + 100 for p in close_prices],
        'low': [p - 100 for p in close_prices],
        'close': close_prices,
        'volume': [1000 * (1 + 0.1 * (i % 5)) for i in range(100)]
    }, index=dates)
    
    # Thông tin vị thế
    position_data = {
        'symbol': 'BTCUSDT',
        'position_id': 'test_pos_1',
        'position_type': 'long',
        'entry_price': 50500,
        'current_price': 51000,
        'position_size': 0.1
    }
    
    # Thiết lập các mức chốt lời
    tp_result = tp_manager.set_tp_levels(market_data, position_data, 'trending_bullish')
    
    print("Đã thiết lập các mức chốt lời:")
    for level in tp_result['tp_levels']:
        print(f"Mức {level['level']}: {level['price']:.2f} ({level['quantity_percent']:.0f}%)")
    
    # Kiểm tra tín hiệu chốt lời
    current_price = 51500  # Giả sử giá tăng
    tp_signal = tp_manager.check_tp_signals(position_data['symbol'], position_data['position_id'], current_price)
    
    if tp_signal['tp_signal']:
        print(f"\nCó tín hiệu chốt lời:")
        print(f"Mức TP: {tp_signal['level']}")
        print(f"Giá TP: {tp_signal['price']:.2f}")
        print(f"Số lượng: {tp_signal['quantity']:.4f} ({tp_signal['quantity_percent']:.0f}%)")
        
        # Thực hiện chốt lời
        execution_data = {
            'level': tp_signal['level'],
            'price': tp_signal['price'],
            'quantity': tp_signal['quantity']
        }
        
        execute_result = tp_manager.execute_partial_tp(position_data['symbol'], position_data['position_id'], execution_data)
        
        if execute_result['success']:
            print(f"\nĐã thực hiện chốt lời thành công")
            print(f"Stop loss mới: {execute_result.get('adjusted_stop')}")
            print(f"Số mức còn lại: {execute_result['remaining_levels']}")
    else:
        print("\nChưa có tín hiệu chốt lời")
    
    # Tạo biểu đồ
    chart_path = tp_manager.visualize_tp_levels(position_data['symbol'], position_data['position_id'], market_data)
    print(f"\nBiểu đồ các mức chốt lời: {chart_path}")
    
    # Lấy trạng thái
    status = tp_manager.get_position_tp_status(position_data['symbol'], position_data['position_id'])
    
    print("\nTrạng thái chốt lời:")
    print(f"Đã thực hiện: {status['executed_percent']:.1f}%")
    print(f"Còn lại: {status['remaining_quantity']:.4f} ({status['position_size'] - status['executed_quantity']:.4f} BTC)")
    
    # Thiết lập cấu hình tùy chỉnh
    custom_levels = [
        {'percent': 1.0, 'quantity': 0.2, 'adjust_stop': True},
        {'percent': 2.0, 'quantity': 0.3, 'adjust_stop': True},
        {'percent': 3.0, 'quantity': 0.5, 'adjust_stop': True}
    ]
    
    custom_result = tp_manager.custom_tp_levels_for_position(
        'ETHUSDT', 'test_pos_2', 
        {
            'position_type': 'long',
            'entry_price': 3000,
            'position_size': 1.0
        },
        custom_levels
    )
    
    print("\nĐã thiết lập cấu hình tùy chỉnh cho ETHUSDT:")
    for level in custom_result['tp_levels']:
        print(f"Mức {level['level']}: {level['price']:.2f} ({level['quantity_percent']:.0f}%)")