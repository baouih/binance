#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module Trailing Stop thích ứng cải tiến (Enhanced Adaptive Trailing Stop)

Module này mở rộng từ Advanced Trailing Stop, cung cấp các cải tiến như:
- Bảo vệ lợi nhuận tự động khi đạt ngưỡng
- Điều chỉnh theo chế độ thị trường
- Căn chỉnh với các mức hỗ trợ/kháng cự
- Tự động phân đoạn thoát vị thế theo giai đoạn
"""

import os
import sys
import json
import time
import math
import logging
import datetime
import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
from pathlib import Path

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('enhanced_trailing_stop.log')
    ]
)
logger = logging.getLogger('enhanced_trailing_stop')

# Thêm thư mục gốc vào sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import module cơ sở
try:
    from advanced_trailing_stop import TrailingStopStrategy, AdvancedTrailingStop
except ImportError:
    logger.error("Không thể import module advanced_trailing_stop. Hãy đảm bảo bạn đang chạy từ thư mục gốc.")
    # Định nghĩa lớp giả lập nếu không import được
    class TrailingStopStrategy:
        def __init__(self, name: str):
            self.name = name
    
    class AdvancedTrailingStop:
        def __init__(self, strategy_type: str = "percentage", data_cache = None, config: Dict = None):
            self.strategy_type = strategy_type
            self.data_cache = data_cache
            self.config = config or {}


class AdaptiveTrailingStop(TrailingStopStrategy):
    """
    Chiến lược trailing stop thích ứng với nhiều yếu tố
    """
    
    def __init__(self, config: Dict = None, data_provider = None):
        """
        Khởi tạo chiến lược
        
        Args:
            config (Dict): Cấu hình cho chiến lược
            data_provider: Nguồn cung cấp dữ liệu thị trường
        """
        super().__init__("adaptive")
        self.config = config or {}
        self.data_provider = data_provider
        
        # Tham số mặc định
        self.default_config = {
            'base_callback': 0.02,  # 2% callback cơ sở
            'regime_multipliers': {
                'trending': 0.7,  # Callback nhỏ hơn cho xu hướng
                'ranging': 1.5,   # Callback lớn hơn cho thị trường sideway
                'volatile': 1.2,  # Callback vừa phải cho thị trường biến động
                'quiet': 1.0,     # Callback tiêu chuẩn cho thị trường ít biến động
                'neutral': 1.0    # Mặc định
            },
            'profit_protection': {
                'enabled': True,
                'min_profit': 0.05,  # 5% lợi nhuận tối thiểu
                'margin_factor': 0.01  # Đảm bảo lãi ít nhất 1% sau khi kích hoạt
            },
            'profit_phases': {
                'initial': {'threshold': 0.02, 'multiplier': 1.0},       # 0-2%
                'growing': {'threshold': 0.05, 'multiplier': 0.8},       # 2-5%
                'substantial': {'threshold': 0.1, 'multiplier': 0.7},    # 5-10%
                'significant': {'threshold': 0.2, 'multiplier': 0.6},    # 10-20%
                'major': {'threshold': float('inf'), 'multiplier': 0.5}  # >20%
            },
            'sr_alignment': {
                'enabled': True,
                'max_distance': 0.02  # Khoảng cách tối đa để căn chỉnh (2%)
            },
            'time_factor': {
                'enabled': True,
                'reduction_per_day': 0.05  # Giảm 5% callback mỗi ngày
            },
            'weights': {
                'regime': 0.35,
                'profit': 0.30,
                'volatility': 0.25,
                'time': 0.10
            },
            'partial_exit': {
                'enabled': False,
                'thresholds': [0.05, 0.1, 0.2],  # Các mức lợi nhuận để thoát một phần
                'percentages': [0.25, 0.25, 0.25]  # Phần trăm vị thế thoát ở mỗi mức
            }
        }
        
        # Merge cấu hình
        for key, value in self.default_config.items():
            if key not in self.config:
                self.config[key] = value
            elif isinstance(value, dict) and isinstance(self.config[key], dict):
                for subkey, subvalue in value.items():
                    if subkey not in self.config[key]:
                        self.config[key][subkey] = subvalue
    
    def initialize(self, position: Dict) -> Dict:
        """
        Khởi tạo tham số cho chiến lược
        
        Args:
            position (Dict): Thông tin vị thế
            
        Returns:
            Dict: Thông tin vị thế đã cập nhật
        """
        # Lưu chiến lược
        position['trailing_type'] = self.name
        position['trailing_config'] = self.config
        position['trailing_activated'] = False
        position['trailing_stop'] = None
        position['trailing_status'] = "waiting"  # waiting, tracking, active
        position['trailing_partial_exits'] = []
        
        # Lưu giá cao/thấp nhất
        if position['side'] == 'LONG':
            position['highest_price'] = position['entry_price']
            position['lowest_price'] = None
        else:  # SHORT
            position['highest_price'] = None
            position['lowest_price'] = position['entry_price']
        
        # Lưu thời gian vào lệnh
        if 'entry_time' not in position:
            position['entry_time'] = int(time.time())
        
        # Lưu thông tin thị trường
        if self.data_provider:
            position['market_regime'] = self._get_market_regime(position['symbol'])
            position['entry_volatility'] = self._get_volatility(position['symbol'])
            position['support_resistance_levels'] = self._get_support_resistance_levels(position['symbol'])
        else:
            position['market_regime'] = 'neutral'
            position['entry_volatility'] = 0.02
            position['support_resistance_levels'] = []
        
        return position
    
    def _get_market_regime(self, symbol: str) -> str:
        """
        Lấy chế độ thị trường hiện tại
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            str: Chế độ thị trường ('trending', 'ranging', 'volatile', 'quiet', 'neutral')
        """
        if not self.data_provider:
            return 'neutral'
            
        try:
            return self.data_provider.get_market_regime(symbol)
        except:
            return 'neutral'
    
    def _get_volatility(self, symbol: str) -> float:
        """
        Lấy biến động thị trường hiện tại
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            float: Giá trị biến động (ATR/Price)
        """
        if not self.data_provider:
            return 0.02
            
        try:
            return self.data_provider.get_volatility(symbol)
        except:
            return 0.02
    
    def _get_support_resistance_levels(self, symbol: str) -> List[float]:
        """
        Lấy các mức hỗ trợ/kháng cự gần đó
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            List[float]: Danh sách các mức giá
        """
        if not self.data_provider:
            return []
            
        try:
            return self.data_provider.get_support_resistance_levels(symbol)
        except:
            return []
    
    def _update_market_info(self, position: Dict) -> Dict:
        """
        Cập nhật thông tin thị trường cho vị thế
        
        Args:
            position (Dict): Thông tin vị thế
            
        Returns:
            Dict: Thông tin vị thế đã cập nhật
        """
        if not self.data_provider:
            return position
            
        symbol = position['symbol']
        
        try:
            position['market_regime'] = self._get_market_regime(symbol)
            position['current_volatility'] = self._get_volatility(symbol)
            position['support_resistance_levels'] = self._get_support_resistance_levels(symbol)
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật thông tin thị trường: {str(e)}")
        
        return position
    
    def _calculate_highest_profit(self, position: Dict, current_price: float) -> float:
        """
        Tính lợi nhuận cao nhất đã đạt được
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            
        Returns:
            float: Phần trăm lợi nhuận cao nhất
        """
        entry_price = position['entry_price']
        side = position['side']
        
        if side == 'LONG':
            highest_price = position.get('highest_price', entry_price)
            highest_profit = (highest_price - entry_price) / entry_price
        else:  # SHORT
            lowest_price = position.get('lowest_price', entry_price)
            highest_profit = (entry_price - lowest_price) / entry_price
            
        return highest_profit
    
    def _calculate_current_profit(self, position: Dict, current_price: float) -> float:
        """
        Tính lợi nhuận hiện tại
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            
        Returns:
            float: Phần trăm lợi nhuận hiện tại
        """
        entry_price = position['entry_price']
        side = position['side']
        
        if side == 'LONG':
            current_profit = (current_price - entry_price) / entry_price
        else:  # SHORT
            current_profit = (entry_price - current_price) / entry_price
            
        return current_profit
    
    def _get_time_in_trade_days(self, position: Dict) -> float:
        """
        Tính thời gian trong giao dịch (ngày)
        
        Args:
            position (Dict): Thông tin vị thế
            
        Returns:
            float: Thời gian giao dịch (ngày)
        """
        entry_time = position.get('entry_time', int(time.time()))
        now = int(time.time())
        
        days = (now - entry_time) / (24 * 3600)
        return max(0, days)
    
    def _get_profit_phase_multiplier(self, highest_profit: float) -> float:
        """
        Lấy hệ số nhân theo giai đoạn lợi nhuận
        
        Args:
            highest_profit (float): Lợi nhuận cao nhất
            
        Returns:
            float: Hệ số nhân
        """
        profit_phases = self.config.get('profit_phases', {})
        
        for phase, config in profit_phases.items():
            if highest_profit <= config.get('threshold', 0):
                return config.get('multiplier', 1.0)
        
        # Mặc định cho lợi nhuận rất cao
        return 0.5
    
    def _get_regime_multiplier(self, market_regime: str) -> float:
        """
        Lấy hệ số nhân theo chế độ thị trường
        
        Args:
            market_regime (str): Chế độ thị trường
            
        Returns:
            float: Hệ số nhân
        """
        regime_multipliers = self.config.get('regime_multipliers', {})
        return regime_multipliers.get(market_regime, 1.0)
    
    def _get_volatility_multiplier(self, current_volatility: float, base_volatility: float) -> float:
        """
        Lấy hệ số nhân theo biến động
        
        Args:
            current_volatility (float): Biến động hiện tại
            base_volatility (float): Biến động cơ sở
            
        Returns:
            float: Hệ số nhân
        """
        if base_volatility <= 0:
            base_volatility = 0.02  # Giá trị mặc định
            
        volatility_ratio = current_volatility / base_volatility
        
        # Điều chỉnh theo tỷ lệ biến động
        return min(1.5, max(0.7, volatility_ratio))
    
    def _get_time_multiplier(self, days_in_trade: float) -> float:
        """
        Lấy hệ số nhân theo thời gian
        
        Args:
            days_in_trade (float): Số ngày trong giao dịch
            
        Returns:
            float: Hệ số nhân
        """
        if not self.config.get('time_factor', {}).get('enabled', True):
            return 1.0
            
        reduction_per_day = self.config.get('time_factor', {}).get('reduction_per_day', 0.05)
        
        # Giảm dần callback theo thời gian
        multiplier = max(0.7, 1.0 - (days_in_trade * reduction_per_day))
        return multiplier
    
    def _align_with_support_resistance(self, price: float, side: str, levels: List[float]) -> float:
        """
        Căn chỉnh giá với mức hỗ trợ/kháng cự gần nhất
        
        Args:
            price (float): Giá ban đầu
            side (str): Hướng vị thế ('LONG' hoặc 'SHORT')
            levels (List[float]): Danh sách các mức hỗ trợ/kháng cự
            
        Returns:
            float: Giá đã căn chỉnh
        """
        if not levels or not self.config.get('sr_alignment', {}).get('enabled', True):
            return price
            
        max_distance = self.config.get('sr_alignment', {}).get('max_distance', 0.02)
        max_distance_abs = price * max_distance
        
        # Sắp xếp mức giá theo thứ tự phù hợp
        if side == 'LONG':
            # Tìm mức hỗ trợ gần nhất dưới giá
            suitable_levels = [level for level in levels if level < price]
            if not suitable_levels:
                return price
                
            # Tìm mức gần nhất
            best_level = max(suitable_levels)
            
            # Kiểm tra khoảng cách
            if price - best_level <= max_distance_abs:
                return best_level
        else:  # SHORT
            # Tìm mức kháng cự gần nhất trên giá
            suitable_levels = [level for level in levels if level > price]
            if not suitable_levels:
                return price
                
            # Tìm mức gần nhất
            best_level = min(suitable_levels)
            
            # Kiểm tra khoảng cách
            if best_level - price <= max_distance_abs:
                return best_level
        
        return price
    
    def _protect_profit(self, trailing_stop: float, entry_price: float, highest_profit: float, side: str) -> float:
        """
        Bảo vệ lợi nhuận khi đạt ngưỡng
        
        Args:
            trailing_stop (float): Giá trailing stop ban đầu
            entry_price (float): Giá vào lệnh
            highest_profit (float): Lợi nhuận cao nhất
            side (str): Hướng vị thế ('LONG' hoặc 'SHORT')
            
        Returns:
            float: Giá trailing stop đã điều chỉnh
        """
        if not self.config.get('profit_protection', {}).get('enabled', True):
            return trailing_stop
            
        min_profit = self.config.get('profit_protection', {}).get('min_profit', 0.05)
        margin_factor = self.config.get('profit_protection', {}).get('margin_factor', 0.01)
        
        # Chỉ bảo vệ khi lợi nhuận đủ lớn
        if highest_profit < min_profit:
            return trailing_stop
            
        if side == 'LONG':
            # Nếu trailing_stop dưới giá vào, điều chỉnh lên
            # Đảm bảo ít nhất lãi margin_factor
            min_stop = entry_price * (1 + margin_factor)
            if trailing_stop < min_stop:
                return min_stop
        else:  # SHORT
            # Nếu trailing_stop trên giá vào, điều chỉnh xuống
            max_stop = entry_price * (1 - margin_factor)
            if trailing_stop > max_stop:
                return max_stop
        
        return trailing_stop
    
    def _check_partial_exit(self, position: Dict, current_price: float) -> Dict:
        """
        Kiểm tra điều kiện thoát một phần vị thế
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            
        Returns:
            Dict: Thông tin thoát một phần hoặc None nếu không thoát
        """
        if not self.config.get('partial_exit', {}).get('enabled', False):
            return None
            
        thresholds = self.config.get('partial_exit', {}).get('thresholds', [])
        percentages = self.config.get('partial_exit', {}).get('percentages', [])
        
        if not thresholds or not percentages or len(thresholds) != len(percentages):
            return None
            
        # Kiểm tra đã thoát ở ngưỡng nào chưa
        exit_thresholds = [exit_info.get('threshold') for exit_info in position.get('trailing_partial_exits', [])]
        
        # Tính lợi nhuận hiện tại
        current_profit = self._calculate_current_profit(position, current_price)
        
        # Kiểm tra các ngưỡng chưa thoát
        for i, threshold in enumerate(thresholds):
            if threshold not in exit_thresholds and current_profit >= threshold:
                # Tính số lượng thoát
                original_quantity = position.get('original_quantity', position.get('quantity', 0))
                exit_percentage = percentages[i]
                exit_quantity = original_quantity * exit_percentage
                
                # Kiểm tra số lượng còn lại
                remaining_quantity = position.get('quantity', 0) - exit_quantity
                if remaining_quantity <= 0:
                    return None  # Không đủ số lượng để thoát
                
                return {
                    'threshold': threshold,
                    'percentage': exit_percentage,
                    'quantity': exit_quantity,
                    'price': current_price
                }
        
        return None
    
    def update(self, position: Dict, current_price: float) -> Dict:
        """
        Cập nhật trailing stop dựa trên giá hiện tại
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            
        Returns:
            Dict: Thông tin vị thế đã cập nhật
        """
        # Cập nhật thông tin thị trường
        position = self._update_market_info(position)
        
        # Lấy các thông tin cần thiết
        entry_price = position['entry_price']
        side = position['side']
        market_regime = position.get('market_regime', 'neutral')
        base_volatility = position.get('entry_volatility', 0.02)
        current_volatility = position.get('current_volatility', base_volatility)
        support_resistance_levels = position.get('support_resistance_levels', [])
        
        # Đảm bảo quantity và original_quantity
        if 'original_quantity' not in position:
            position['original_quantity'] = position.get('quantity', 0)
        
        # Cập nhật giá cao/thấp nhất
        if side == 'LONG':
            if position.get('highest_price') is None or current_price > position['highest_price']:
                position['highest_price'] = current_price
        else:  # SHORT
            if position.get('lowest_price') is None or current_price < position['lowest_price']:
                position['lowest_price'] = current_price
        
        # Tính lợi nhuận cao nhất và hiện tại
        highest_profit = self._calculate_highest_profit(position, current_price)
        current_profit = self._calculate_current_profit(position, current_price)
        
        # Kiểm tra thoát một phần
        partial_exit = self._check_partial_exit(position, current_price)
        if partial_exit:
            # Thêm vào danh sách thoát một phần
            if 'trailing_partial_exits' not in position:
                position['trailing_partial_exits'] = []
            position['trailing_partial_exits'].append(partial_exit)
            
            # Cập nhật số lượng
            position['quantity'] -= partial_exit['quantity']
            
            logger.info(f"Thoát một phần {partial_exit['percentage']*100:.0f}% vị thế {position['symbol']} "
                       f"ở mức lợi nhuận {partial_exit['threshold']*100:.1f}%, "
                       f"giá: {partial_exit['price']:.2f}")
        
        # Tính các hệ số điều chỉnh
        days_in_trade = self._get_time_in_trade_days(position)
        profit_multiplier = self._get_profit_phase_multiplier(highest_profit)
        regime_multiplier = self._get_regime_multiplier(market_regime)
        volatility_multiplier = self._get_volatility_multiplier(current_volatility, base_volatility)
        time_multiplier = self._get_time_multiplier(days_in_trade)
        
        # Lấy trọng số
        weights = self.config.get('weights', {
            'regime': 0.35,
            'profit': 0.30,
            'volatility': 0.25,
            'time': 0.10
        })
        
        # Tính callback tối ưu
        base_callback = self.config.get('base_callback', 0.02)
        callback_pct = (
            base_callback * regime_multiplier * weights.get('regime', 0.35) +
            base_callback * profit_multiplier * weights.get('profit', 0.30) +
            base_callback * volatility_multiplier * weights.get('volatility', 0.25) +
            base_callback * time_multiplier * weights.get('time', 0.10)
        )
        
        # Tính trailing stop
        if side == 'LONG':
            # Tính giá trailing stop ban đầu
            highest_price = position['highest_price']
            callback_amount = highest_price * callback_pct
            trailing_stop = highest_price - callback_amount
            
            # Bảo vệ lợi nhuận
            trailing_stop = self._protect_profit(trailing_stop, entry_price, highest_profit, side)
            
            # Căn chỉnh với mức hỗ trợ/kháng cự
            trailing_stop = self._align_with_support_resistance(trailing_stop, side, support_resistance_levels)
        else:  # SHORT
            # Tính giá trailing stop ban đầu
            lowest_price = position['lowest_price']
            callback_amount = lowest_price * callback_pct
            trailing_stop = lowest_price + callback_amount
            
            # Bảo vệ lợi nhuận
            trailing_stop = self._protect_profit(trailing_stop, entry_price, highest_profit, side)
            
            # Căn chỉnh với mức hỗ trợ/kháng cự
            trailing_stop = self._align_with_support_resistance(trailing_stop, side, support_resistance_levels)
        
        # Cập nhật trạng thái trailing stop
        old_trailing_stop = position.get('trailing_stop')
        
        if current_profit >= 0.01:  # Lãi ít nhất 1%
            if not position.get('trailing_activated', False):
                position['trailing_activated'] = True
                position['trailing_status'] = "active"
                logger.info(f"Đã kích hoạt trailing stop cho {position['symbol']} ở mức {trailing_stop:.2f}")
            elif side == 'LONG' and (old_trailing_stop is None or trailing_stop > old_trailing_stop):
                logger.info(f"Đã cập nhật trailing stop cho {position['symbol']} lên {trailing_stop:.2f}")
            elif side == 'SHORT' and (old_trailing_stop is None or trailing_stop < old_trailing_stop):
                logger.info(f"Đã cập nhật trailing stop cho {position['symbol']} xuống {trailing_stop:.2f}")
        elif current_profit > 0:  # Lãi nhưng chưa đủ kích hoạt
            position['trailing_status'] = "tracking"
        
        # Lưu trailing stop
        position['trailing_stop'] = trailing_stop
        
        # Lưu thông tin phụ
        position['trailing_factors'] = {
            'highest_profit': highest_profit,
            'current_profit': current_profit,
            'days_in_trade': days_in_trade,
            'callback_pct': callback_pct,
            'profit_multiplier': profit_multiplier,
            'regime_multiplier': regime_multiplier,
            'volatility_multiplier': volatility_multiplier,
            'time_multiplier': time_multiplier
        }
        
        return position
    
    def should_close(self, position: Dict, current_price: float) -> Tuple[bool, str]:
        """
        Kiểm tra xem có nên đóng vị thế không
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            
        Returns:
            Tuple[bool, str]: (Có nên đóng hay không, Lý do)
        """
        # Kiểm tra xem trailing stop đã được kích hoạt chưa
        if not position.get('trailing_activated', False) or position.get('trailing_stop') is None:
            # Kiểm tra nếu đang lỗ quá lớn - hỗ trợ stop loss chung
            entry_price = position['entry_price']
            side = position['side']
            
            if side == 'LONG' and current_price < entry_price * 0.95:
                return True, f"Giá ({current_price:.2f}) đã giảm quá 5% từ giá vào lệnh ({entry_price:.2f})"
            elif side == 'SHORT' and current_price > entry_price * 1.05:
                return True, f"Giá ({current_price:.2f}) đã tăng quá 5% từ giá vào lệnh ({entry_price:.2f})"
                
            return False, "Trailing stop chưa kích hoạt"
        
        side = position['side']
        trailing_stop = position['trailing_stop']
        
        # Kiểm tra điều kiện đóng vị thế
        if side == 'LONG' and current_price <= trailing_stop:
            return True, f"Giá ({current_price:.2f}) đã chạm trailing stop ({trailing_stop:.2f})"
        elif side == 'SHORT' and current_price >= trailing_stop:
            return True, f"Giá ({current_price:.2f}) đã chạm trailing stop ({trailing_stop:.2f})"
        
        return False, "Giá chưa chạm trailing stop"


class EnhancedAdaptiveTrailingStop:
    """
    Lớp quản lý trailing stop thích ứng cải tiến
    """
    
    def __init__(self, config_path: str = 'configs/enhanced_trailing_stop_config.json', data_provider = None):
        """
        Khởi tạo quản lý trailing stop
        
        Args:
            config_path (str): Đường dẫn file cấu hình
            data_provider: Nguồn cung cấp dữ liệu thị trường
        """
        self.config_path = config_path
        self.data_provider = data_provider
        self.config = self._load_config()
        self.strategy = AdaptiveTrailingStop(self.config, data_provider)
    
    def _load_config(self) -> Dict:
        """
        Tải cấu hình từ file
        
        Returns:
            Dict: Cấu hình đã tải
        """
        # Cấu hình mặc định
        default_config = {
            'base_callback': 0.02,  # 2% callback cơ sở
            'regime_multipliers': {
                'trending': 0.7,  # Callback nhỏ hơn cho xu hướng
                'ranging': 1.5,   # Callback lớn hơn cho thị trường sideway
                'volatile': 1.2,  # Callback vừa phải cho thị trường biến động
                'quiet': 1.0,     # Callback tiêu chuẩn cho thị trường ít biến động
                'neutral': 1.0    # Mặc định
            },
            'profit_protection': {
                'enabled': True,
                'min_profit': 0.05,  # 5% lợi nhuận tối thiểu
                'margin_factor': 0.01  # Đảm bảo lãi ít nhất 1% sau khi kích hoạt
            },
            'sr_alignment': {
                'enabled': True,
                'max_distance': 0.02  # Khoảng cách tối đa để căn chỉnh (2%)
            },
            'partial_exit': {
                'enabled': True,
                'thresholds': [0.05, 0.1, 0.2],  # Các mức lợi nhuận để thoát một phần
                'percentages': [0.25, 0.25, 0.25]  # Phần trăm vị thế thoát ở mỗi mức
            }
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
                
                # Merge với default config
                for key, value in loaded_config.items():
                    default_config[key] = value
                    
                return default_config
            else:
                # Lưu default config
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                with open(self.config_path, 'w') as f:
                    json.dump(default_config, f, indent=4)
                logger.info(f"Đã tạo file cấu hình mặc định tại {self.config_path}")
                return default_config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
            return default_config
    
    def save_config(self) -> bool:
        """
        Lưu cấu hình vào file
        
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Đã lưu cấu hình vào {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {str(e)}")
            return False
    
    def update_config(self, new_config: Dict) -> bool:
        """
        Cập nhật cấu hình
        
        Args:
            new_config (Dict): Cấu hình mới
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không
        """
        try:
            # Cập nhật từng phần của config
            for key, value in new_config.items():
                if key in self.config:
                    if isinstance(value, dict) and isinstance(self.config[key], dict):
                        # Merge nested dict
                        self.config[key].update(value)
                    else:
                        self.config[key] = value
                else:
                    self.config[key] = value
                    
            # Cập nhật chiến lược
            self.strategy = AdaptiveTrailingStop(self.config, self.data_provider)
                    
            # Lưu config mới
            return self.save_config()
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật cấu hình: {str(e)}")
            return False
    
    def initialize_position(self, position: Dict) -> Dict:
        """
        Khởi tạo vị thế với chiến lược trailing stop
        
        Args:
            position (Dict): Thông tin vị thế
            
        Returns:
            Dict: Thông tin vị thế đã cập nhật
        """
        return self.strategy.initialize(position)
    
    def update_trailing_stop(self, position: Dict, current_price: float) -> Dict:
        """
        Cập nhật trailing stop cho vị thế
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            
        Returns:
            Dict: Thông tin vị thế đã cập nhật
        """
        return self.strategy.update(position, current_price)
    
    def check_stop_condition(self, position: Dict, current_price: float) -> Tuple[bool, str]:
        """
        Kiểm tra điều kiện đóng vị thế
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            
        Returns:
            Tuple[bool, str]: (Có nên đóng hay không, Lý do)
        """
        return self.strategy.should_close(position, current_price)
    
    def get_partial_exits(self, position: Dict) -> List[Dict]:
        """
        Lấy danh sách các lần thoát một phần
        
        Args:
            position (Dict): Thông tin vị thế
            
        Returns:
            List[Dict]: Danh sách thông tin thoát một phần
        """
        return position.get('trailing_partial_exits', [])
    
    def check_partial_exit(self, position: Dict, current_price: float) -> Optional[Dict]:
        """
        Kiểm tra vị thế có cần thoát một phần không
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            
        Returns:
            Optional[Dict]: Thông tin thoát một phần hoặc None nếu không thoát
        """
        return self.strategy._check_partial_exit(position, current_price)
    
    def get_trailing_status(self, position: Dict) -> Dict:
        """
        Lấy trạng thái chi tiết của trailing stop
        
        Args:
            position (Dict): Thông tin vị thế
            
        Returns:
            Dict: Trạng thái chi tiết
        """
        return {
            'status': position.get('trailing_status', 'waiting'),
            'activated': position.get('trailing_activated', False),
            'stop_price': position.get('trailing_stop'),
            'factors': position.get('trailing_factors', {}),
            'partial_exits': position.get('trailing_partial_exits', [])
        }
    
    def backtest_trailing_stop(self, entry_price: float, price_data: List[float], side: str = 'LONG', 
                              position_size: float = 1.0, entry_index: int = 0) -> Dict:
        """
        Backtesting trailing stop trên dữ liệu giá
        
        Args:
            entry_price (float): Giá vào lệnh
            price_data (List[float]): Danh sách giá đóng cửa
            side (str): Hướng vị thế ('LONG' hoặc 'SHORT')
            position_size (float): Kích thước vị thế
            entry_index (int): Chỉ số của giá vào lệnh trong danh sách
            
        Returns:
            Dict: Kết quả backtest
        """
        # Tạo vị thế mẫu
        position = {
            'symbol': 'BACKTEST',
            'side': side,
            'entry_price': entry_price,
            'quantity': position_size,
            'original_quantity': position_size,
            'entry_time': int(time.time()) - (len(price_data) - entry_index) * 3600  # Giả định dữ liệu 1h
        }
        
        # Khởi tạo vị thế
        position = self.initialize_position(position)
        
        # Chạy backtest
        exit_index = None
        exit_price = None
        exit_reason = None
        partial_exits = []
        trailing_history = []
        
        for i in range(entry_index + 1, len(price_data)):
            current_price = price_data[i]
            
            # Kiểm tra thoát một phần
            partial_exit = self.check_partial_exit(position, current_price)
            if partial_exit:
                # Lưu thoát một phần
                partial_exit['index'] = i
                partial_exits.append(partial_exit)
                
                # Cập nhật vị thế
                position['quantity'] -= partial_exit['quantity']
                if 'trailing_partial_exits' not in position:
                    position['trailing_partial_exits'] = []
                position['trailing_partial_exits'].append(partial_exit)
            
            # Cập nhật trailing stop
            position = self.update_trailing_stop(position, current_price)
            
            # Lưu lịch sử
            trailing_history.append({
                'index': i,
                'price': current_price,
                'trailing_stop': position.get('trailing_stop'),
                'status': position.get('trailing_status')
            })
            
            # Kiểm tra đóng vị thế
            should_close, reason = self.check_stop_condition(position, current_price)
            if should_close:
                exit_index = i
                exit_price = current_price
                exit_reason = reason
                break
        
        # Tính kết quả
        pnl = 0
        if exit_price:
            if side == 'LONG':
                # Tính lợi nhuận phần còn lại
                remaining_pnl = (exit_price - entry_price) * position['quantity']
                
                # Tính lợi nhuận các phần đã thoát
                partial_pnl = sum((exit['price'] - entry_price) * exit['quantity'] for exit in partial_exits)
                
                pnl = remaining_pnl + partial_pnl
            else:  # SHORT
                # Tính lợi nhuận phần còn lại
                remaining_pnl = (entry_price - exit_price) * position['quantity']
                
                # Tính lợi nhuận các phần đã thoát
                partial_pnl = sum((entry_price - exit['price']) * exit['quantity'] for exit in partial_exits)
                
                pnl = remaining_pnl + partial_pnl
        
        return {
            'entry_price': entry_price,
            'exit_price': exit_price,
            'exit_index': exit_index,
            'exit_reason': exit_reason,
            'pnl': pnl,
            'partial_exits': partial_exits,
            'trailing_history': trailing_history,
            'final_position': position
        }


# Mock data provider cho testing
class MockDataProvider:
    def __init__(self):
        self.market_regime = 'trending'
        self.volatility = 0.02
        self.support_resistance_levels = [10000, 10500, 11000, 11500, 12000]
    
    def get_market_regime(self, symbol: str) -> str:
        return self.market_regime
    
    def get_volatility(self, symbol: str) -> float:
        return self.volatility
    
    def get_support_resistance_levels(self, symbol: str) -> List[float]:
        return self.support_resistance_levels


def main():
    """Hàm chính để test EnhancedAdaptiveTrailingStop"""
    print("=== Test EnhancedAdaptiveTrailingStop ===\n")
    
    # Khởi tạo mock data provider
    mock_provider = MockDataProvider()
    
    # Khởi tạo trailing stop
    trailing_stop = EnhancedAdaptiveTrailingStop(data_provider=mock_provider)
    
    # Tạo vị thế mẫu
    position = {
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry_price': 50000,
        'quantity': 0.1,
        'leverage': 5
    }
    
    # Khởi tạo vị thế
    position = trailing_stop.initialize_position(position)
    print(f"Vị thế ban đầu: {json.dumps(position, indent=2)}")
    
    # Cập nhật trailing stop với các mức giá khác nhau
    print("\nCập nhật trailing stop với các mức giá tăng dần:")
    prices = [50500, 51000, 51500, 52000, 51500, 51000, 50500, 50000]
    
    for price in prices:
        position = trailing_stop.update_trailing_stop(position, price)
        should_close, reason = trailing_stop.check_stop_condition(position, price)
        
        status = trailing_stop.get_trailing_status(position)
        print(f"Giá: {price}, Stop: {status['stop_price']:.2f if status['stop_price'] else None}, "
              f"Trạng thái: {status['status']}, Kích hoạt: {status['activated']}")
        
        if should_close:
            print(f"Đóng vị thế tại giá {price}: {reason}")
            break
    
    # Backtest
    print("\nBacktest trailing stop:")
    price_data = [49500, 50000, 50500, 51000, 51500, 52000, 51500, 51000, 50500, 50000, 49000]
    
    result = trailing_stop.backtest_trailing_stop(
        entry_price=50000,
        price_data=price_data,
        side='LONG',
        position_size=0.1,
        entry_index=1  # Vào ở index 1 (giá 50000)
    )
    
    print(f"Kết quả backtest:")
    print(f"Giá vào: {result['entry_price']}, Giá ra: {result['exit_price']}")
    print(f"Lý do thoát: {result['exit_reason']}")
    print(f"PnL: {result['pnl']:.2f}")
    
    if result['partial_exits']:
        print(f"Thoát một phần:")
        for exit in result['partial_exits']:
            print(f"  Ngưỡng: {exit['threshold']*100:.1f}%, Giá: {exit['price']}, "
                 f"Số lượng: {exit['quantity']}")


if __name__ == "__main__":
    main()