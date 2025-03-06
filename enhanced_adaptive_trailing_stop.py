#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module Enhanced Adaptive Trailing Stop (EATS)

Module này cung cấp các chiến lược trailing stop nâng cao với khả năng tự động
thích nghi với điều kiện thị trường, bao gồm:

1. Percentage Trailing Stop: Dựa trên % callback, tự động điều chỉnh theo
   biến động thị trường
2. Step Trailing Stop: Sử dụng nhiều mức trailing stop tăng dần theo lợi nhuận
3. ATR-based Trailing Stop: Dựa trên chỉ báo ATR để thích nghi với biến động

Mỗi chiến lược đều hỗ trợ thoát lệnh một phần (partial exit) ở các ngưỡng
lợi nhuận khác nhau để tối ưu hóa kết quả giao dịch.
"""

import json
import logging
import os
from typing import Dict, List, Tuple, Optional, Union, Any
from datetime import datetime
import time
import numpy as np

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('trailing_stop')

class EnhancedAdaptiveTrailingStop:
    """
    Lớp quản lý trailing stop thích ứng nâng cao với đa dạng chiến lược
    và khả năng thích nghi với điều kiện thị trường
    """
    
    def __init__(self, config_path: str = 'configs/trailing_stop_config.json'):
        """
        Khởi tạo Enhanced Adaptive Trailing Stop
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.history = self._load_history()
        self.current_volatility = 1.0  # Hệ số biến động mặc định
        self.current_volatility_multiplier = 1.0  # Hệ số nhân biến động mặc định
        
        logger.info(f"Đã tải cấu hình từ {config_path}")
        logger.info("Đã khởi tạo Enhanced Adaptive Trailing Stop")
    
    def _load_config(self) -> Dict:
        """
        Tải cấu hình từ file
        
        Returns:
            Dict: Cấu hình đã tải
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
            # Trả về cấu hình mặc định nếu có lỗi
            return {
                "strategies": {
                    "percentage": {
                        "trending": {
                            "activation_percent": 1.0,
                            "callback_percent": 0.5,
                            "use_dynamic_callback": True,
                            "min_callback": 0.3,
                            "max_callback": 2.0,
                            "partial_exits": []
                        },
                        "ranging": {
                            "activation_percent": 0.8,
                            "callback_percent": 0.8,
                            "use_dynamic_callback": True,
                            "min_callback": 0.5,
                            "max_callback": 1.5,
                            "partial_exits": []
                        },
                        "volatile": {
                            "activation_percent": 1.5,
                            "callback_percent": 1.0,
                            "use_dynamic_callback": True,
                            "min_callback": 0.8,
                            "max_callback": 3.0,
                            "partial_exits": []
                        },
                        "quiet": {
                            "activation_percent": 0.5,
                            "callback_percent": 0.3,
                            "use_dynamic_callback": False,
                            "partial_exits": []
                        }
                    }
                },
                "general": {
                    "default_strategy": "percentage",
                    "default_market_regime": "trending",
                    "log_level": "INFO"
                }
            }
    
    def _load_history(self) -> List[Dict]:
        """
        Tải lịch sử trailing stop từ file
        
        Returns:
            List[Dict]: Lịch sử đã tải hoặc danh sách rỗng
        """
        history_file = self.config.get('general', {}).get('history_file', 'trailing_stop_history.json')
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.info("Không tìm thấy hoặc không thể tải lịch sử trailing stop")
            return []
    
    def _convert_datetime_to_iso(self, obj):
        """
        Chuyển đổi các đối tượng datetime thành chuỗi ISO format
        
        Args:
            obj: Đối tượng cần chuyển đổi
            
        Returns:
            Đối tượng đã chuyển đổi
        """
        if isinstance(obj, dict):
            return {key: self._convert_datetime_to_iso(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_datetime_to_iso(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj
            
    def _save_history(self) -> bool:
        """
        Lưu lịch sử trailing stop vào file
        
        Returns:
            bool: True nếu lưu thành công, False nếu thất bại
        """
        if not self.config.get('general', {}).get('save_history', True):
            return False
            
        history_file = self.config.get('general', {}).get('history_file', 'trailing_stop_history.json')
        max_entries = self.config.get('general', {}).get('max_history_entries', 1000)
        
        # Giới hạn số lượng mục lịch sử
        if len(self.history) > max_entries:
            self.history = self.history[-max_entries:]
            
        try:
            # Chuyển đổi tất cả các đối tượng datetime trước khi serialize
            serializable_history = self._convert_datetime_to_iso(self.history)
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_history, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu lịch sử: {str(e)}")
            return False
    
    def _add_to_history(self, position_info: Dict) -> None:
        """
        Thêm thông tin vị thế vào lịch sử
        
        Args:
            position_info (Dict): Thông tin vị thế đã đóng
        """
        if not self.config.get('general', {}).get('save_history', True):
            return
            
        entry_time = position_info.get('entry_time')
        if isinstance(entry_time, datetime):
            position_info['entry_time'] = entry_time.isoformat()
            
        exit_time = position_info.get('exit_time')
        if isinstance(exit_time, datetime):
            position_info['exit_time'] = exit_time.isoformat()
            
        self.history.append(position_info)
        self._save_history()
    
    def update_volatility(self, volatility: float = None) -> None:
        """
        Cập nhật hệ số biến động thị trường
        
        Args:
            volatility (float, optional): Hệ số biến động mới
        """
        if volatility is None:
            return
            
        self.current_volatility = volatility
        self.current_volatility_multiplier = 1.0  # Đặt giá trị mặc định
        
        # Áp dụng giới hạn cho hệ số biến động
        volatility_settings = self.config.get('market_volatility_adjustment', {})
        if volatility_settings.get('enable', False):
            low_threshold = volatility_settings.get('low_volatility_threshold', 0.5)
            high_threshold = volatility_settings.get('high_volatility_threshold', 2.0)
            
            if volatility < low_threshold:
                self.current_volatility_multiplier = volatility_settings.get('low_volatility_multiplier', 0.7)
            elif volatility > high_threshold:
                self.current_volatility_multiplier = volatility_settings.get('high_volatility_multiplier', 1.5)
            else:
                # Tuyến tính nội suy giữa giá trị thấp và cao
                range_size = high_threshold - low_threshold
                position = (volatility - low_threshold) / range_size
                low_mult = volatility_settings.get('low_volatility_multiplier', 0.7)
                high_mult = volatility_settings.get('high_volatility_multiplier', 1.5)
                self.current_volatility_multiplier = low_mult + position * (high_mult - low_mult)
        else:
            self.current_volatility_multiplier = 1.0
    
    def _get_strategy_config(self, strategy_type: str, market_regime: str) -> Dict:
        """
        Lấy cấu hình cho chiến lược và chế độ thị trường cụ thể
        
        Args:
            strategy_type (str): Loại chiến lược
            market_regime (str): Chế độ thị trường
            
        Returns:
            Dict: Cấu hình chiến lược
        """
        default_strategy = self.config.get('general', {}).get('default_strategy', 'percentage')
        default_regime = self.config.get('general', {}).get('default_market_regime', 'trending')
        
        if not strategy_type:
            strategy_type = default_strategy
        if not market_regime:
            market_regime = default_regime
            
        # Lấy cấu hình cho chiến lược và chế độ thị trường
        try:
            strategy_config = self.config.get('strategies', {}).get(strategy_type, {}).get(market_regime, {})
            
            # Nếu không tìm thấy cấu hình cụ thể, sử dụng cấu hình mặc định
            if not strategy_config:
                strategy_config = self.config.get('strategies', {}).get(default_strategy, {}).get(default_regime, {})
                logger.warning(f"Không tìm thấy cấu hình cho {strategy_type}/{market_regime}, sử dụng mặc định")
            
            return strategy_config
        except Exception as e:
            logger.error(f"Lỗi khi lấy cấu hình chiến lược: {str(e)}")
            return {}
    
    def initialize_trailing_stop(self, entry_price: float, side: str, 
                               strategy_type: str = None, market_regime: str = None) -> Dict:
        """
        Khởi tạo trailing stop cho một vị thế mới
        
        Args:
            entry_price (float): Giá vào lệnh
            side (str): Hướng vị thế ('LONG' hoặc 'SHORT')
            strategy_type (str, optional): Loại chiến lược
            market_regime (str, optional): Chế độ thị trường
            
        Returns:
            Dict: Thông tin trailing stop đã khởi tạo
        """
        if not strategy_type:
            strategy_type = self.config.get('general', {}).get('default_strategy', 'percentage')
        if not market_regime:
            market_regime = self.config.get('general', {}).get('default_market_regime', 'trending')
            
        strategy_config = self._get_strategy_config(strategy_type, market_regime)
        
        # Khởi tạo thông tin vị thế cơ bản
        position_info = {
            'entry_price': entry_price,
            'side': side,
            'strategy_type': strategy_type,
            'market_regime': market_regime,
            'entry_time': datetime.now(),
            'last_update_time': datetime.now(),
            'highest_price': entry_price,
            'lowest_price': entry_price,
            'stop_price': None,
            'current_price': entry_price,
            'status': 'ACTIVE',
            'trailing_activated': False,
            'partial_exits': [],
            'partial_exit_levels': strategy_config.get('partial_exits', []),
            'profit_pct': 0.0,
            'max_profit_pct': 0.0,
            'config': strategy_config
        }
        
        # Thêm thông tin đặc thù cho từng loại chiến lược
        if strategy_type == 'percentage':
            position_info['activation_percent'] = strategy_config.get('activation_percent', 1.0)
            position_info['callback_percent'] = strategy_config.get('callback_percent', 0.5)
            position_info['use_dynamic_callback'] = strategy_config.get('use_dynamic_callback', False)
            position_info['min_callback'] = strategy_config.get('min_callback', 0.3)
            position_info['max_callback'] = strategy_config.get('max_callback', 2.0)
            
            # Tính stop price ban đầu (chưa kích hoạt)
            if side == 'LONG':
                stop_pct = 1 - position_info['callback_percent'] / 100
                position_info['stop_price'] = entry_price * stop_pct
            else:  # SHORT
                stop_pct = 1 + position_info['callback_percent'] / 100
                position_info['stop_price'] = entry_price * stop_pct
                
        elif strategy_type == 'step':
            position_info['profit_steps'] = strategy_config.get('profit_steps', [1.0, 2.0, 5.0, 10.0])
            position_info['callback_steps'] = strategy_config.get('callback_steps', [0.2, 0.5, 1.0, 2.0])
            position_info['current_step'] = 0
            
            # Tính stop price ban đầu (dựa trên step đầu tiên)
            if side == 'LONG':
                stop_pct = 1 - position_info['callback_steps'][0] / 100
                position_info['stop_price'] = entry_price * stop_pct
            else:  # SHORT
                stop_pct = 1 + position_info['callback_steps'][0] / 100
                position_info['stop_price'] = entry_price * stop_pct
                
        elif strategy_type == 'atr_based':
            position_info['atr_multiplier'] = strategy_config.get('atr_multiplier', 2.0)
            position_info['atr_value'] = strategy_config.get('atr_value', None)  # Sẽ được cập nhật khi có dữ liệu
            position_info['min_profit_activation'] = strategy_config.get('min_profit_activation', 0.5)
            
            # Nếu không có giá trị ATR, sử dụng % callback mặc định
            if not position_info['atr_value']:
                atr_default = 0.01 * entry_price  # Giả định ATR là 1% giá
                position_info['atr_value'] = atr_default
            
            # Tính stop price ban đầu
            atr_distance = position_info['atr_value'] * position_info['atr_multiplier']
            if side == 'LONG':
                position_info['stop_price'] = entry_price - atr_distance
            else:  # SHORT
                position_info['stop_price'] = entry_price + atr_distance
        
        logger.info(f"Đã khởi tạo trailing stop cho vị thế {side}: chiến lược {strategy_type}, chế độ {market_regime}")
        return position_info
    
    def update_trailing_stop(self, position_info: Dict, current_price: float, 
                           atr_value: float = None) -> Dict:
        """
        Cập nhật trailing stop dựa trên giá hiện tại
        
        Args:
            position_info (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            atr_value (float, optional): Giá trị ATR hiện tại
            
        Returns:
            Dict: Thông tin vị thế đã cập nhật
        """
        if position_info['status'] != 'ACTIVE':
            return position_info
            
        side = position_info['side']
        strategy_type = position_info['strategy_type']
        entry_price = position_info['entry_price']
        
        # Cập nhật giá cao nhất/thấp nhất
        if current_price > position_info['highest_price']:
            position_info['highest_price'] = current_price
        if current_price < position_info['lowest_price']:
            position_info['lowest_price'] = current_price
            
        # Cập nhật giá hiện tại và thời gian
        position_info['current_price'] = current_price
        position_info['last_update_time'] = datetime.now()
        
        # Tính toán phần trăm lợi nhuận hiện tại
        if side == 'LONG':
            profit_pct = (current_price - entry_price) / entry_price * 100
            max_profit_pct = (position_info['highest_price'] - entry_price) / entry_price * 100
        else:  # SHORT
            profit_pct = (entry_price - current_price) / entry_price * 100
            max_profit_pct = (entry_price - position_info['lowest_price']) / entry_price * 100
            
        position_info['profit_pct'] = profit_pct
        position_info['max_profit_pct'] = max_profit_pct
        
        # Cập nhật tùy theo chiến lược
        if strategy_type == 'percentage':
            self._update_percentage_trailing_stop(position_info, current_price)
        elif strategy_type == 'step':
            self._update_step_trailing_stop(position_info, current_price)
        elif strategy_type == 'atr_based':
            if atr_value:
                position_info['atr_value'] = atr_value
            self._update_atr_trailing_stop(position_info, current_price)
            
        # Kiểm tra điều kiện thoát một phần
        if position_info['partial_exit_levels']:
            self._check_partial_exits(position_info)
            
        return position_info
    
    def _update_percentage_trailing_stop(self, position_info: Dict, current_price: float) -> None:
        """
        Cập nhật trailing stop dựa trên phần trăm
        
        Args:
            position_info (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
        """
        side = position_info['side']
        entry_price = position_info['entry_price']
        activation_percent = position_info['activation_percent']
        callback_percent = position_info['callback_percent']
        use_dynamic_callback = position_info['use_dynamic_callback']
        min_callback = position_info.get('min_callback', 0.3)
        max_callback = position_info.get('max_callback', 2.0)
        
        # Tính profit %
        if side == 'LONG':
            profit_pct = (current_price - entry_price) / entry_price * 100
            # Kiểm tra và cập nhật trailing stop
            if not position_info['trailing_activated']:
                # Kiểm tra xem đã đạt ngưỡng kích hoạt chưa
                if profit_pct >= activation_percent:
                    position_info['trailing_activated'] = True
                    
                    # Tính callback tự động nếu được bật
                    if use_dynamic_callback:
                        # Điều chỉnh callback theo profit và volatility
                        # Công thức: min_callback + (profit/10) * (max-min)
                        profit_factor = min(1.0, profit_pct / 10)
                        dynamic_callback = min_callback + profit_factor * (max_callback - min_callback)
                        # Áp dụng hệ số biến động thị trường
                        dynamic_callback *= self.current_volatility_multiplier
                        # Giới hạn trong khoảng min-max
                        callback_percent = max(min_callback, min(max_callback, dynamic_callback))
                        position_info['callback_percent'] = callback_percent
                    
                    # Tính giá stop mới
                    position_info['stop_price'] = current_price * (1 - callback_percent/100)
                    logger.info(f"Kích hoạt percentage trailing stop cho vị thế {side}: giá hiện tại={current_price}, callback={callback_percent}%, stop_price={position_info['stop_price']}")
            else:
                # Đã kích hoạt, cập nhật stop nếu giá tăng
                new_stop_price = current_price * (1 - callback_percent/100)
                if new_stop_price > position_info['stop_price']:
                    position_info['stop_price'] = new_stop_price
        else:  # SHORT
            profit_pct = (entry_price - current_price) / entry_price * 100
            # Kiểm tra và cập nhật trailing stop
            if not position_info['trailing_activated']:
                # Kiểm tra xem đã đạt ngưỡng kích hoạt chưa
                if profit_pct >= activation_percent:
                    position_info['trailing_activated'] = True
                    
                    # Tính callback tự động nếu được bật
                    if use_dynamic_callback:
                        # Điều chỉnh callback theo profit và volatility
                        profit_factor = min(1.0, profit_pct / 10)
                        dynamic_callback = min_callback + profit_factor * (max_callback - min_callback)
                        # Áp dụng hệ số biến động thị trường
                        dynamic_callback *= self.current_volatility_multiplier
                        # Giới hạn trong khoảng min-max
                        callback_percent = max(min_callback, min(max_callback, dynamic_callback))
                        position_info['callback_percent'] = callback_percent
                    
                    # Tính giá stop mới
                    position_info['stop_price'] = current_price * (1 + callback_percent/100)
                    logger.info(f"Kích hoạt percentage trailing stop cho vị thế {side}: giá hiện tại={current_price}, callback={callback_percent}%, stop_price={position_info['stop_price']}")
            else:
                # Đã kích hoạt, cập nhật stop nếu giá giảm
                new_stop_price = current_price * (1 + callback_percent/100)
                if new_stop_price < position_info['stop_price']:
                    position_info['stop_price'] = new_stop_price
    
    def _update_step_trailing_stop(self, position_info: Dict, current_price: float) -> None:
        """
        Cập nhật trailing stop theo bậc thang (step)
        
        Args:
            position_info (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
        """
        side = position_info['side']
        entry_price = position_info['entry_price']
        profit_steps = position_info['profit_steps']
        callback_steps = position_info['callback_steps']
        current_step = position_info['current_step']
        
        # Tính profit %
        if side == 'LONG':
            profit_pct = (current_price - entry_price) / entry_price * 100
            
            # Xác định step hiện tại dựa trên profit
            next_step = current_step
            for i, step_level in enumerate(profit_steps):
                if profit_pct >= step_level and i > current_step:
                    next_step = i
            
            # Nếu đã chuyển sang step mới, cập nhật lại stop
            if next_step > current_step:
                position_info['current_step'] = next_step
                position_info['trailing_activated'] = True
                callback_pct = callback_steps[next_step]
                position_info['stop_price'] = current_price * (1 - callback_pct/100)
                logger.info(f"Chuyển sang step {next_step} cho vị thế LONG: profit={profit_pct:.2f}%, callback={callback_pct}%, stop_price={position_info['stop_price']:.2f}")
            elif position_info['trailing_activated']:
                # Đã kích hoạt, cập nhật stop nếu giá tăng
                callback_pct = callback_steps[current_step]
                new_stop_price = current_price * (1 - callback_pct/100)
                if new_stop_price > position_info['stop_price']:
                    position_info['stop_price'] = new_stop_price
        else:  # SHORT
            profit_pct = (entry_price - current_price) / entry_price * 100
            
            # Xác định step hiện tại dựa trên profit
            next_step = current_step
            for i, step_level in enumerate(profit_steps):
                if profit_pct >= step_level and i > current_step:
                    next_step = i
            
            # Nếu đã chuyển sang step mới, cập nhật lại stop
            if next_step > current_step:
                position_info['current_step'] = next_step
                position_info['trailing_activated'] = True
                callback_pct = callback_steps[next_step]
                position_info['stop_price'] = current_price * (1 + callback_pct/100)
                logger.info(f"Chuyển sang step {next_step} cho vị thế SHORT: profit={profit_pct:.2f}%, callback={callback_pct}%, stop_price={position_info['stop_price']:.2f}")
            elif position_info['trailing_activated']:
                # Đã kích hoạt, cập nhật stop nếu giá giảm
                callback_pct = callback_steps[current_step]
                new_stop_price = current_price * (1 + callback_pct/100)
                if new_stop_price < position_info['stop_price']:
                    position_info['stop_price'] = new_stop_price
    
    def _update_atr_trailing_stop(self, position_info: Dict, current_price: float) -> None:
        """
        Cập nhật trailing stop dựa trên ATR
        
        Args:
            position_info (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
        """
        side = position_info['side']
        entry_price = position_info['entry_price']
        atr_value = position_info['atr_value']
        atr_multiplier = position_info['atr_multiplier']
        min_profit_activation = position_info['min_profit_activation']
        
        # Tính profit %
        if side == 'LONG':
            profit_pct = (current_price - entry_price) / entry_price * 100
            
            # Kiểm tra xem đã đạt ngưỡng kích hoạt chưa
            if not position_info['trailing_activated']:
                if profit_pct >= min_profit_activation:
                    position_info['trailing_activated'] = True
                    atr_distance = atr_value * atr_multiplier
                    position_info['stop_price'] = current_price - atr_distance
                    logger.info(f"Kích hoạt ATR trailing stop cho vị thế LONG: ATR={atr_value:.2f}, multiplier={atr_multiplier}, stop_price={position_info['stop_price']:.2f}")
            else:
                # Đã kích hoạt, cập nhật stop nếu giá tăng
                atr_distance = atr_value * atr_multiplier
                new_stop_price = current_price - atr_distance
                if new_stop_price > position_info['stop_price']:
                    position_info['stop_price'] = new_stop_price
        else:  # SHORT
            profit_pct = (entry_price - current_price) / entry_price * 100
            
            # Kiểm tra xem đã đạt ngưỡng kích hoạt chưa
            if not position_info['trailing_activated']:
                if profit_pct >= min_profit_activation:
                    position_info['trailing_activated'] = True
                    atr_distance = atr_value * atr_multiplier
                    position_info['stop_price'] = current_price + atr_distance
                    logger.info(f"Kích hoạt ATR trailing stop cho vị thế SHORT: ATR={atr_value:.2f}, multiplier={atr_multiplier}, stop_price={position_info['stop_price']:.2f}")
            else:
                # Đã kích hoạt, cập nhật stop nếu giá giảm
                atr_distance = atr_value * atr_multiplier
                new_stop_price = current_price + atr_distance
                if new_stop_price < position_info['stop_price']:
                    position_info['stop_price'] = new_stop_price
    
    def _check_partial_exits(self, position_info: Dict) -> None:
        """
        Kiểm tra và xử lý thoát một phần
        
        Args:
            position_info (Dict): Thông tin vị thế
        """
        side = position_info['side']
        entry_price = position_info['entry_price']
        current_price = position_info['current_price']
        partial_exits = position_info['partial_exits']
        partial_exit_levels = position_info['partial_exit_levels']
        
        # Tính profit %
        if side == 'LONG':
            profit_pct = (current_price - entry_price) / entry_price * 100
        else:  # SHORT
            profit_pct = (entry_price - current_price) / entry_price * 100
            
        # Kiểm tra từng mức thoát một phần
        for level in partial_exit_levels:
            threshold = level.get('threshold', 0)
            percentage = level.get('percentage', 0)
            
            # Kiểm tra xem đã thực hiện thoát ở mức này chưa
            level_already_executed = False
            for exit_info in partial_exits:
                if abs(exit_info.get('threshold', 0) - threshold) < 0.001:
                    level_already_executed = True
                    break
                    
            # Nếu chưa thực hiện và đã đạt ngưỡng
            if not level_already_executed and profit_pct >= threshold:
                # Thêm thông tin thoát một phần vào danh sách
                partial_exit_info = {
                    'time': datetime.now(),
                    'price': current_price,
                    'threshold': threshold,
                    'percentage': percentage,
                    'profit_pct': profit_pct
                }
                position_info['partial_exits'].append(partial_exit_info)
                logger.info(f"Thoát một phần ({percentage*100:.0f}%) tại mức lợi nhuận {threshold}% với giá {current_price}")
    
    def check_stop_condition(self, position_info: Dict, current_price: float) -> Tuple[bool, str]:
        """
        Kiểm tra điều kiện đóng vị thế
        
        Args:
            position_info (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            
        Returns:
            Tuple[bool, str]: (Có đóng vị thế không, Lý do đóng)
        """
        if position_info['status'] != 'ACTIVE':
            return False, "Vị thế không còn hoạt động"
            
        side = position_info['side']
        stop_price = position_info['stop_price']
        
        # Kiểm tra điều kiện dừng lỗ/chốt lời
        if side == 'LONG':
            if current_price <= stop_price and position_info['trailing_activated']:
                return True, f"Giá ({current_price}) dưới mức trailing stop ({stop_price})"
        else:  # SHORT
            if current_price >= stop_price and position_info['trailing_activated']:
                return True, f"Giá ({current_price}) trên mức trailing stop ({stop_price})"
                
        return False, None
    
    def close_position(self, position_info: Dict, current_price: float, exit_reason: str = None) -> Dict:
        """
        Đóng vị thế
        
        Args:
            position_info (Dict): Thông tin vị thế
            current_price (float): Giá thoát
            exit_reason (str, optional): Lý do thoát
            
        Returns:
            Dict: Thông tin vị thế đã đóng
        """
        if position_info['status'] != 'ACTIVE':
            return position_info
            
        side = position_info['side']
        entry_price = position_info['entry_price']
        
        # Cập nhật trạng thái và giá thoát
        position_info['status'] = 'CLOSED'
        position_info['exit_price'] = current_price
        position_info['exit_time'] = datetime.now()
        position_info['exit_reason'] = exit_reason or "Đóng vị thế thủ công"
        
        # Tính toán kết quả giao dịch
        if side == 'LONG':
            position_info['profit_pct'] = (current_price - entry_price) / entry_price * 100
            position_info['max_profit_pct'] = (position_info['highest_price'] - entry_price) / entry_price * 100
        else:  # SHORT
            position_info['profit_pct'] = (entry_price - current_price) / entry_price * 100
            position_info['max_profit_pct'] = (entry_price - position_info['lowest_price']) / entry_price * 100
            
        # Tính hiệu quả trailing stop
        if position_info['max_profit_pct'] > 0:
            position_info['efficiency'] = position_info['profit_pct'] / position_info['max_profit_pct'] * 100
        else:
            position_info['efficiency'] = 0
            
        # Thêm vào lịch sử
        self._add_to_history(position_info.copy())
        
        logger.info(f"Đóng vị thế {side}: P/L={position_info['profit_pct']:.2f}%, Hiệu quả={position_info['efficiency']:.2f}%, Lý do: {position_info['exit_reason']}")
        return position_info
    
    def get_position_summary(self, position_info: Dict) -> str:
        """
        Tạo bản tóm tắt vị thế
        
        Args:
            position_info (Dict): Thông tin vị thế
            
        Returns:
            str: Bản tóm tắt
        """
        if not position_info:
            return "Không có thông tin vị thế"
            
        side = position_info.get('side', 'UNKNOWN')
        strategy_type = position_info.get('strategy_type', 'UNKNOWN')
        market_regime = position_info.get('market_regime', 'UNKNOWN')
        status = position_info.get('status', 'UNKNOWN')
        entry_price = position_info.get('entry_price', 0)
        current_price = position_info.get('current_price', 0)
        profit_pct = position_info.get('profit_pct', 0)
        max_profit_pct = position_info.get('max_profit_pct', 0)
        efficiency = position_info.get('efficiency', 0) if status == 'CLOSED' else 0
        stop_price = position_info.get('stop_price', 0)
        trailing_activated = position_info.get('trailing_activated', False)
        partial_exits = position_info.get('partial_exits', [])
        
        summary = []
        summary.append(f"Vị thế {side} - {strategy_type.capitalize()}/{market_regime} - {status}")
        summary.append(f"Giá vào: {entry_price:.2f}, Giá hiện tại: {current_price:.2f}")
        summary.append(f"Lợi nhuận: {profit_pct:.2f}%, Tối đa: {max_profit_pct:.2f}%")
        
        if status == 'CLOSED':
            summary.append(f"Hiệu quả: {efficiency:.2f}%")
            summary.append(f"Lý do thoát: {position_info.get('exit_reason', 'Không rõ')}")
        else:
            summary.append(f"Trailing stop: {'Đã kích hoạt' if trailing_activated else 'Chưa kích hoạt'}")
            if trailing_activated:
                summary.append(f"Stop price: {stop_price:.2f}")
                
        if partial_exits:
            for i, exit_info in enumerate(partial_exits):
                summary.append(f"Thoát phần {i+1}: {exit_info.get('percentage', 0)*100:.0f}% tại {exit_info.get('threshold', 0)}% lợi nhuận (giá {exit_info.get('price', 0):.2f})")
                
        return "\n".join(summary)
    
    def get_strategy_types(self) -> List[str]:
        """
        Lấy danh sách các loại chiến lược có sẵn
        
        Returns:
            List[str]: Danh sách các loại chiến lược
        """
        return list(self.config.get('strategies', {}).keys())
    
    def get_market_regimes(self) -> List[str]:
        """
        Lấy danh sách các chế độ thị trường có sẵn
        
        Returns:
            List[str]: Danh sách các chế độ thị trường
        """
        # Lấy danh sách chế độ từ chiến lược đầu tiên
        first_strategy = next(iter(self.config.get('strategies', {}).values()), {})
        return list(first_strategy.keys())
    
    def get_performance_stats(self) -> Dict:
        """
        Lấy thống kê hiệu suất từ lịch sử
        
        Returns:
            Dict: Thống kê hiệu suất
        """
        if not self.history:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'expectancy': 0,
                'efficiency': 0,
                'strategy_stats': {},
                'regime_stats': {}
            }
            
        total_trades = len(self.history)
        profitable_trades = [trade for trade in self.history if trade.get('profit_pct', 0) > 0]
        win_rate = len(profitable_trades) / total_trades * 100 if total_trades > 0 else 0
        
        # Tính trung bình lợi nhuận và thua lỗ
        profits = [trade.get('profit_pct', 0) for trade in profitable_trades]
        losses = [trade.get('profit_pct', 0) for trade in self.history if trade.get('profit_pct', 0) <= 0]
        
        avg_profit = sum(profits) / len(profits) if profits else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        # Tính expectancy (kỳ vọng lợi nhuận trên mỗi giao dịch)
        expectancy = (win_rate/100 * avg_profit) - ((100-win_rate)/100 * abs(avg_loss)) if total_trades > 0 else 0
        
        # Tính hiệu quả trung bình (% của max profit đạt được)
        efficiencies = [trade.get('efficiency', 0) for trade in self.history]
        avg_efficiency = sum(efficiencies) / len(efficiencies) if efficiencies else 0
        
        # Thống kê theo chiến lược
        strategy_stats = {}
        for trade in self.history:
            strategy = trade.get('strategy_type', 'unknown')
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {'total': 0, 'wins': 0, 'profit_pct': 0}
            
            strategy_stats[strategy]['total'] += 1
            if trade.get('profit_pct', 0) > 0:
                strategy_stats[strategy]['wins'] += 1
            strategy_stats[strategy]['profit_pct'] += trade.get('profit_pct', 0)
            
        # Tính win rate và avg profit cho mỗi chiến lược
        for strategy, stats in strategy_stats.items():
            stats['win_rate'] = stats['wins'] / stats['total'] * 100 if stats['total'] > 0 else 0
            stats['avg_profit'] = stats['profit_pct'] / stats['total'] if stats['total'] > 0 else 0
            
        # Thống kê theo chế độ thị trường
        regime_stats = {}
        for trade in self.history:
            regime = trade.get('market_regime', 'unknown')
            if regime not in regime_stats:
                regime_stats[regime] = {'total': 0, 'wins': 0, 'profit_pct': 0}
            
            regime_stats[regime]['total'] += 1
            if trade.get('profit_pct', 0) > 0:
                regime_stats[regime]['wins'] += 1
            regime_stats[regime]['profit_pct'] += trade.get('profit_pct', 0)
            
        # Tính win rate và avg profit cho mỗi chế độ
        for regime, stats in regime_stats.items():
            stats['win_rate'] = stats['wins'] / stats['total'] * 100 if stats['total'] > 0 else 0
            stats['avg_profit'] = stats['profit_pct'] / stats['total'] if stats['total'] > 0 else 0
            
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'expectancy': expectancy,
            'efficiency': avg_efficiency,
            'strategy_stats': strategy_stats,
            'regime_stats': regime_stats
        }
    
    def backtest_trailing_stop(self, entry_price: float, side: str, price_data: List[float], 
                             strategy_type: str = None, market_regime: str = None,
                             atr_value: float = None, entry_index: int = 0) -> Dict:
        """
        Thực hiện backtest trailing stop với dữ liệu giá
        
        Args:
            entry_price (float): Giá vào lệnh
            side (str): Hướng vị thế ('LONG' hoặc 'SHORT')
            price_data (List[float]): Dữ liệu giá
            strategy_type (str, optional): Loại chiến lược
            market_regime (str, optional): Chế độ thị trường
            atr_value (float, optional): Giá trị ATR ban đầu
            entry_index (int): Chỉ số vào lệnh trong dữ liệu giá
            
        Returns:
            Dict: Kết quả backtest
        """
        # Khởi tạo vị thế
        position_info = self.initialize_trailing_stop(entry_price, side, strategy_type, market_regime)
        position_info['entry_index'] = entry_index
        
        # Thêm giá trị ATR nếu có
        if atr_value and strategy_type == 'atr_based':
            position_info['atr_value'] = atr_value
            
        # Lặp qua dữ liệu giá
        for i, price in enumerate(price_data[entry_index + 1:], start=entry_index + 1):
            # Cập nhật vị thế với giá mới
            position_info = self.update_trailing_stop(position_info, price)
            
            # Kiểm tra điều kiện dừng
            should_close, reason = self.check_stop_condition(position_info, price)
            if should_close:
                position_info = self.close_position(position_info, price, reason)
                position_info['exit_index'] = i
                break
                
        # Nếu vị thế vẫn còn mở khi kết thúc dữ liệu, đóng tại giá cuối cùng
        if position_info['status'] == 'ACTIVE':
            last_price = price_data[-1]
            position_info = self.close_position(position_info, last_price, "Kết thúc dữ liệu")
            position_info['exit_index'] = len(price_data) - 1
            
        return position_info
    
    def optimize_parameters(self, price_data: List[float], side: str = 'LONG', 
                          strategy_type: str = None, market_regime: str = None,
                          param_ranges: Dict = None) -> Dict:
        """
        Tối ưu hóa tham số cho chiến lược
        
        Args:
            price_data (List[float]): Dữ liệu giá
            side (str): Hướng vị thế ('LONG' hoặc 'SHORT')
            strategy_type (str, optional): Loại chiến lược
            market_regime (str, optional): Chế độ thị trường
            param_ranges (Dict, optional): Phạm vi các tham số cần tối ưu
            
        Returns:
            Dict: Tham số tối ưu và kết quả
        """
        if not strategy_type:
            strategy_type = self.config.get('general', {}).get('default_strategy', 'percentage')
        if not market_regime:
            market_regime = self.config.get('general', {}).get('default_market_regime', 'trending')
            
        entry_price = price_data[0]
        best_result = None
        best_params = None
        best_score = float('-inf')
        
        # Mặc định param_ranges nếu không được cung cấp
        if not param_ranges:
            if strategy_type == 'percentage':
                param_ranges = {
                    'activation_percent': [0.5, 1.0, 1.5, 2.0],
                    'callback_percent': [0.3, 0.5, 0.8, 1.0, 1.5, 2.0],
                    'use_dynamic_callback': [True, False]
                }
            elif strategy_type == 'step':
                param_ranges = {
                    'profit_steps': [[0.5, 1.0, 3.0, 5.0], [1.0, 2.0, 5.0, 10.0], [2.0, 4.0, 8.0, 15.0]],
                    'callback_steps': [[0.2, 0.4, 0.8, 1.5], [0.3, 0.6, 1.2, 2.5], [0.5, 1.0, 2.0, 4.0]]
                }
            elif strategy_type == 'atr_based':
                param_ranges = {
                    'atr_multiplier': [1.0, 1.5, 2.0, 2.5, 3.0],
                    'min_profit_activation': [0.5, 1.0, 1.5, 2.0]
                }
        
        # Grid search qua tất cả tổ hợp tham số
        def grid_search(param_ranges, current_params=None, param_names=None, index=0):
            nonlocal best_result, best_params, best_score
            
            if current_params is None:
                current_params = {}
            if param_names is None:
                param_names = list(param_ranges.keys())
                
            # Nếu đã thử tất cả các tham số, chạy backtest
            if index >= len(param_names):
                # Sao chép cấu hình hiện tại và áp dụng tham số mới
                config_copy = self.config.copy()
                config_copy['strategies'] = {strategy_type: {market_regime: current_params}}
                
                # Tạm thời thay đổi cấu hình
                old_config = self.config
                self.config = config_copy
                
                # Chạy backtest
                result = self.backtest_trailing_stop(entry_price, side, price_data, strategy_type, market_regime)
                
                # Khôi phục cấu hình
                self.config = old_config
                
                # Tính điểm (kết hợp lợi nhuận và hiệu quả)
                profit_pct = result.get('profit_pct', 0)
                efficiency = result.get('efficiency', 0)
                score = profit_pct * 0.7 + efficiency * 0.3  # 70% lợi nhuận, 30% hiệu quả
                
                # Cập nhật nếu tốt hơn
                if score > best_score:
                    best_score = score
                    best_params = current_params.copy()
                    best_result = result
                return
                
            # Thử tất cả giá trị của tham số hiện tại
            param_name = param_names[index]
            param_values = param_ranges[param_name]
            
            for value in param_values:
                current_params[param_name] = value
                grid_search(param_ranges, current_params, param_names, index + 1)
        
        # Bắt đầu grid search
        grid_search(param_ranges)
        
        return {
            'best_params': best_params,
            'best_result': best_result,
            'best_score': best_score
        }

    def __str__(self) -> str:
        """Trả về thông tin tóm tắt"""
        stats = self.get_performance_stats()
        strategies = self.get_strategy_types()
        
        return (f"Enhanced Adaptive Trailing Stop\n"
                f"Số giao dịch: {stats['total_trades']}\n"
                f"Tỷ lệ thắng: {stats['win_rate']:.2f}%\n"
                f"Chiến lược có sẵn: {', '.join(strategies)}")
        
def main():
    """Chức năng chính để demo"""
    # Tạo ví dụ dữ liệu giá
    np.random.seed(42)
    initial_price = 50000.0
    price_data = [initial_price]
    
    # Tạo dữ liệu giá xu hướng tăng
    for i in range(100):
        drift = 0.001 + 0.0005 * i/100  # Xu hướng tăng nhẹ
        volatility = 0.005  # Độ biến động
        price_change = price_data[-1] * (drift + volatility * np.random.normal())
        price_data.append(max(price_data[-1] + price_change, price_data[-1] * 0.99))  # Không cho giảm quá 1%
    
    # Khởi tạo trailing stop
    ts = EnhancedAdaptiveTrailingStop()
    
    # Thực hiện backtest
    result_pct = ts.backtest_trailing_stop(price_data[0], 'LONG', price_data, 'percentage', 'trending')
    result_step = ts.backtest_trailing_stop(price_data[0], 'LONG', price_data, 'step', 'trending')
    
    # In kết quả
    print("Percentage Trailing Stop:")
    print(f"P/L: {result_pct['profit_pct']:.2f}%")
    print(f"Hiệu quả: {result_pct['efficiency']:.2f}%")
    print(f"Số lần thoát một phần: {len(result_pct['partial_exits'])}")
    
    print("\nStep Trailing Stop:")
    print(f"P/L: {result_step['profit_pct']:.2f}%")
    print(f"Hiệu quả: {result_step['efficiency']:.2f}%")
    print(f"Số lần thoát một phần: {len(result_step['partial_exits'])}")

if __name__ == "__main__":
    main()