#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module Trailing Stop nâng cao (AdvancedTrailingStop)

Module này cung cấp các chiến lược trailing stop đa dạng và nâng cao
như % callback, giá trị tuyệt đối, ATR-based, và Parabolic SAR,
tự động điều chỉnh theo biến động thị trường.
"""

import os
import json
import time
import logging
import datetime
import math
from typing import Dict, List, Tuple, Optional, Union, Any

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('advanced_trailing_stop')

class TrailingStopStrategy:
    """
    Lớp cơ sở cho các chiến lược trailing stop
    """
    
    def __init__(self, name: str):
        """
        Khởi tạo chiến lược
        
        Args:
            name (str): Tên chiến lược
        """
        self.name = name
    
    def initialize(self, position: Dict) -> Dict:
        """
        Khởi tạo tham số cho chiến lược
        
        Args:
            position (Dict): Thông tin vị thế
            
        Returns:
            Dict: Thông tin vị thế đã cập nhật
        """
        raise NotImplementedError("Phương thức initialize() phải được ghi đè")
    
    def update(self, position: Dict, current_price: float) -> Dict:
        """
        Cập nhật trailing stop dựa trên giá hiện tại
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            
        Returns:
            Dict: Thông tin vị thế đã cập nhật
        """
        raise NotImplementedError("Phương thức update() phải được ghi đè")
    
    def should_close(self, position: Dict, current_price: float) -> Tuple[bool, str]:
        """
        Kiểm tra xem có nên đóng vị thế không
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            
        Returns:
            Tuple[bool, str]: (Có nên đóng hay không, Lý do)
        """
        raise NotImplementedError("Phương thức should_close() phải được ghi đè")


class PercentageTrailingStop(TrailingStopStrategy):
    """
    Chiến lược trailing stop dựa trên phần trăm callback
    """
    
    def __init__(self, activation_percent: float = 1.0, callback_percent: float = 0.5):
        """
        Khởi tạo chiến lược
        
        Args:
            activation_percent (float): Phần trăm lợi nhuận để kích hoạt trailing stop
            callback_percent (float): Phần trăm callback từ mức cao/thấp nhất
        """
        super().__init__("percentage")
        self.activation_percent = activation_percent
        self.callback_percent = callback_percent
    
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
        position['trailing_activation_percent'] = self.activation_percent
        position['trailing_callback_percent'] = self.callback_percent
        position['trailing_activated'] = False
        position['trailing_stop'] = None
        
        # Lưu giá cao/thấp nhất
        if position['side'] == 'LONG':
            position['highest_price'] = position['entry_price']
            position['lowest_price'] = None
        else:  # SHORT
            position['highest_price'] = None
            position['lowest_price'] = position['entry_price']
        
        return position
    
    def update(self, position: Dict, current_price: float) -> Dict:
        """
        Cập nhật trailing stop dựa trên giá hiện tại
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            
        Returns:
            Dict: Thông tin vị thế đã cập nhật
        """
        entry_price = position['entry_price']
        side = position['side']
        activation_percent = position.get('trailing_activation_percent', self.activation_percent)
        callback_percent = position.get('trailing_callback_percent', self.callback_percent)
        
        # Tính phần trăm lợi nhuận
        if side == 'LONG':
            profit_percent = (current_price - entry_price) / entry_price * 100
            
            # Cập nhật giá cao nhất
            if position.get('highest_price') is None or current_price > position['highest_price']:
                position['highest_price'] = current_price
            
            # Kiểm tra kích hoạt trailing stop
            if not position.get('trailing_activated', False):
                if profit_percent >= activation_percent:
                    position['trailing_activated'] = True
                    # Tính giá trailing stop
                    callback_amount = position['highest_price'] * callback_percent / 100
                    position['trailing_stop'] = position['highest_price'] - callback_amount
                    logger.info(f"Đã kích hoạt trailing stop cho {position['symbol']} ở mức {position['trailing_stop']:.2f}")
            else:
                # Nếu đã kích hoạt, cập nhật trailing stop nếu giá tăng
                if current_price > position['highest_price']:
                    position['highest_price'] = current_price
                    # Cập nhật giá trailing stop
                    callback_amount = position['highest_price'] * callback_percent / 100
                    position['trailing_stop'] = position['highest_price'] - callback_amount
                    logger.info(f"Đã cập nhật trailing stop cho {position['symbol']} lên {position['trailing_stop']:.2f}")
        else:  # SHORT
            profit_percent = (entry_price - current_price) / entry_price * 100
            
            # Cập nhật giá thấp nhất
            if position.get('lowest_price') is None or current_price < position['lowest_price']:
                position['lowest_price'] = current_price
            
            # Kiểm tra kích hoạt trailing stop
            if not position.get('trailing_activated', False):
                if profit_percent >= activation_percent:
                    position['trailing_activated'] = True
                    # Tính giá trailing stop
                    callback_amount = position['lowest_price'] * callback_percent / 100
                    position['trailing_stop'] = position['lowest_price'] + callback_amount
                    logger.info(f"Đã kích hoạt trailing stop cho {position['symbol']} ở mức {position['trailing_stop']:.2f}")
            else:
                # Nếu đã kích hoạt, cập nhật trailing stop nếu giá giảm
                if current_price < position['lowest_price']:
                    position['lowest_price'] = current_price
                    # Cập nhật giá trailing stop
                    callback_amount = position['lowest_price'] * callback_percent / 100
                    position['trailing_stop'] = position['lowest_price'] + callback_amount
                    logger.info(f"Đã cập nhật trailing stop cho {position['symbol']} xuống {position['trailing_stop']:.2f}")
        
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
            return False, "Trailing stop chưa kích hoạt"
        
        side = position['side']
        trailing_stop = position['trailing_stop']
        
        # Kiểm tra điều kiện đóng vị thế
        if side == 'LONG' and current_price <= trailing_stop:
            return True, f"Giá ({current_price:.2f}) đã chạm trailing stop ({trailing_stop:.2f})"
        elif side == 'SHORT' and current_price >= trailing_stop:
            return True, f"Giá ({current_price:.2f}) đã chạm trailing stop ({trailing_stop:.2f})"
        
        return False, "Giá chưa chạm trailing stop"


class AbsoluteTrailingStop(TrailingStopStrategy):
    """
    Chiến lược trailing stop dựa trên giá trị tuyệt đối
    """
    
    def __init__(self, activation_amount: float = 100.0, callback_amount: float = 50.0):
        """
        Khởi tạo chiến lược
        
        Args:
            activation_amount (float): Giá trị lợi nhuận để kích hoạt trailing stop
            callback_amount (float): Giá trị callback từ mức cao/thấp nhất
        """
        super().__init__("absolute")
        self.activation_amount = activation_amount
        self.callback_amount = callback_amount
    
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
        position['trailing_activation_amount'] = self.activation_amount
        position['trailing_callback_amount'] = self.callback_amount
        position['trailing_activated'] = False
        position['trailing_stop'] = None
        
        # Lưu giá cao/thấp nhất
        if position['side'] == 'LONG':
            position['highest_price'] = position['entry_price']
            position['lowest_price'] = None
        else:  # SHORT
            position['highest_price'] = None
            position['lowest_price'] = position['entry_price']
        
        return position
    
    def update(self, position: Dict, current_price: float) -> Dict:
        """
        Cập nhật trailing stop dựa trên giá hiện tại
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            
        Returns:
            Dict: Thông tin vị thế đã cập nhật
        """
        entry_price = position['entry_price']
        quantity = position['quantity']
        leverage = position.get('leverage', 1)
        side = position['side']
        activation_amount = position.get('trailing_activation_amount', self.activation_amount)
        callback_amount = position.get('trailing_callback_amount', self.callback_amount)
        
        # Tính lợi nhuận
        if side == 'LONG':
            profit_amount = (current_price - entry_price) * quantity * leverage
            
            # Cập nhật giá cao nhất
            if position.get('highest_price') is None or current_price > position['highest_price']:
                position['highest_price'] = current_price
            
            # Kiểm tra kích hoạt trailing stop
            if not position.get('trailing_activated', False):
                if profit_amount >= activation_amount:
                    position['trailing_activated'] = True
                    # Tính giá trailing stop
                    position['trailing_stop'] = position['highest_price'] - (callback_amount / (quantity * leverage))
                    logger.info(f"Đã kích hoạt trailing stop cho {position['symbol']} ở mức {position['trailing_stop']:.2f}")
            else:
                # Nếu đã kích hoạt, cập nhật trailing stop nếu giá tăng
                if current_price > position['highest_price']:
                    position['highest_price'] = current_price
                    # Cập nhật giá trailing stop
                    position['trailing_stop'] = position['highest_price'] - (callback_amount / (quantity * leverage))
                    logger.info(f"Đã cập nhật trailing stop cho {position['symbol']} lên {position['trailing_stop']:.2f}")
        else:  # SHORT
            profit_amount = (entry_price - current_price) * quantity * leverage
            
            # Cập nhật giá thấp nhất
            if position.get('lowest_price') is None or current_price < position['lowest_price']:
                position['lowest_price'] = current_price
            
            # Kiểm tra kích hoạt trailing stop
            if not position.get('trailing_activated', False):
                if profit_amount >= activation_amount:
                    position['trailing_activated'] = True
                    # Tính giá trailing stop
                    position['trailing_stop'] = position['lowest_price'] + (callback_amount / (quantity * leverage))
                    logger.info(f"Đã kích hoạt trailing stop cho {position['symbol']} ở mức {position['trailing_stop']:.2f}")
            else:
                # Nếu đã kích hoạt, cập nhật trailing stop nếu giá giảm
                if current_price < position['lowest_price']:
                    position['lowest_price'] = current_price
                    # Cập nhật giá trailing stop
                    position['trailing_stop'] = position['lowest_price'] + (callback_amount / (quantity * leverage))
                    logger.info(f"Đã cập nhật trailing stop cho {position['symbol']} xuống {position['trailing_stop']:.2f}")
        
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
            return False, "Trailing stop chưa kích hoạt"
        
        side = position['side']
        trailing_stop = position['trailing_stop']
        
        # Kiểm tra điều kiện đóng vị thế
        if side == 'LONG' and current_price <= trailing_stop:
            return True, f"Giá ({current_price:.2f}) đã chạm trailing stop ({trailing_stop:.2f})"
        elif side == 'SHORT' and current_price >= trailing_stop:
            return True, f"Giá ({current_price:.2f}) đã chạm trailing stop ({trailing_stop:.2f})"
        
        return False, "Giá chưa chạm trailing stop"


class ATRTrailingStop(TrailingStopStrategy):
    """
    Chiến lược trailing stop dựa trên ATR (Average True Range)
    """
    
    def __init__(self, atr_multiplier: float = 3.0, atr_period: int = 14, data_cache = None):
        """
        Khởi tạo chiến lược
        
        Args:
            atr_multiplier (float): Hệ số nhân ATR
            atr_period (int): Số chu kỳ để tính ATR
            data_cache (DataCache, optional): Cache dữ liệu
        """
        super().__init__("atr")
        self.atr_multiplier = atr_multiplier
        self.atr_period = atr_period
        self.data_cache = data_cache
    
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
        position['trailing_atr_multiplier'] = self.atr_multiplier
        position['trailing_atr_period'] = self.atr_period
        position['trailing_activated'] = False
        position['trailing_stop'] = None
        
        # Lưu giá cao/thấp nhất
        if position['side'] == 'LONG':
            position['highest_price'] = position['entry_price']
            position['lowest_price'] = None
        else:  # SHORT
            position['highest_price'] = None
            position['lowest_price'] = position['entry_price']
        
        # Nếu có giá trị ATR sẵn, tính trailing stop
        symbol = position['symbol']
        atr_value = self._get_atr_value(symbol)
        if atr_value:
            position['atr_value'] = atr_value
        
        return position
    
    def _get_atr_value(self, symbol: str, timeframe: str = "1h") -> Optional[float]:
        """
        Lấy giá trị ATR hiện tại
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            
        Returns:
            Optional[float]: Giá trị ATR hoặc None nếu không có dữ liệu
        """
        if self.data_cache is None:
            return None
        
        try:
            # Thử lấy ATR từ cache
            atr_key = f"{symbol}_{timeframe}_atr_{self.atr_period}"
            atr_data = self.data_cache.get('indicators', atr_key)
            
            if atr_data:
                # Kiểm tra xem có cấu trúc dữ liệu chuẩn không
                if isinstance(atr_data, dict) and 'value' in atr_data:
                    return atr_data['value']
                elif isinstance(atr_data, (int, float)):
                    return float(atr_data)
                elif isinstance(atr_data, list) and len(atr_data) > 0:
                    return float(atr_data[-1])
            
            # Nếu không có trong cache và không có chức năng tính ATR
            # thì trả về giá trị mặc định dựa trên giá hiện tại
            # (đây chỉ là approximation, không chính xác)
            symbol_price = self.data_cache.get('market_data', f"{symbol}_price")
            if symbol_price and isinstance(symbol_price, (int, float)):
                # Lấy ~2% của giá hiện tại
                return symbol_price * 0.02
            
            return None
        except Exception as e:
            logger.error(f"Lỗi khi lấy giá trị ATR cho {symbol}: {str(e)}")
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
        entry_price = position['entry_price']
        side = position['side']
        atr_multiplier = position.get('trailing_atr_multiplier', self.atr_multiplier)
        
        # Lấy giá trị ATR
        symbol = position['symbol']
        atr_value = position.get('atr_value')
        if not atr_value:
            atr_value = self._get_atr_value(symbol)
            if atr_value:
                position['atr_value'] = atr_value
            else:
                # Nếu không có ATR, sử dụng 2% giá hiện tại
                atr_value = current_price * 0.02
                position['atr_value'] = atr_value
        
        # Tính trailing stop
        atr_distance = atr_value * atr_multiplier
        
        if side == 'LONG':
            # Cập nhật giá cao nhất
            if position.get('highest_price') is None or current_price > position['highest_price']:
                position['highest_price'] = current_price
            
            # Tính trailing stop
            trailing_stop = position['highest_price'] - atr_distance
            
            # Kiểm tra kích hoạt trailing stop
            if not position.get('trailing_activated', False):
                # Kích hoạt nếu giá đủ cao so với giá vào
                if current_price > entry_price + atr_distance:
                    position['trailing_activated'] = True
                    position['trailing_stop'] = trailing_stop
                    logger.info(f"Đã kích hoạt ATR trailing stop cho {position['symbol']} ở mức {trailing_stop:.2f}")
            else:
                # Chỉ cập nhật trailing stop nếu nó cao hơn giá trị cũ
                if position.get('trailing_stop') is None or trailing_stop > position['trailing_stop']:
                    position['trailing_stop'] = trailing_stop
                    logger.info(f"Đã cập nhật ATR trailing stop cho {position['symbol']} lên {trailing_stop:.2f}")
        else:  # SHORT
            # Cập nhật giá thấp nhất
            if position.get('lowest_price') is None or current_price < position['lowest_price']:
                position['lowest_price'] = current_price
            
            # Tính trailing stop
            trailing_stop = position['lowest_price'] + atr_distance
            
            # Kiểm tra kích hoạt trailing stop
            if not position.get('trailing_activated', False):
                # Kích hoạt nếu giá đủ thấp so với giá vào
                if current_price < entry_price - atr_distance:
                    position['trailing_activated'] = True
                    position['trailing_stop'] = trailing_stop
                    logger.info(f"Đã kích hoạt ATR trailing stop cho {position['symbol']} ở mức {trailing_stop:.2f}")
            else:
                # Chỉ cập nhật trailing stop nếu nó thấp hơn giá trị cũ
                if position.get('trailing_stop') is None or trailing_stop < position['trailing_stop']:
                    position['trailing_stop'] = trailing_stop
                    logger.info(f"Đã cập nhật ATR trailing stop cho {position['symbol']} xuống {trailing_stop:.2f}")
        
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
            return False, "Trailing stop chưa kích hoạt"
        
        side = position['side']
        trailing_stop = position['trailing_stop']
        
        # Kiểm tra điều kiện đóng vị thế
        if side == 'LONG' and current_price <= trailing_stop:
            return True, f"Giá ({current_price:.2f}) đã chạm ATR trailing stop ({trailing_stop:.2f})"
        elif side == 'SHORT' and current_price >= trailing_stop:
            return True, f"Giá ({current_price:.2f}) đã chạm ATR trailing stop ({trailing_stop:.2f})"
        
        return False, "Giá chưa chạm trailing stop"


class ParabolicSARTrailingStop(TrailingStopStrategy):
    """
    Chiến lược trailing stop dựa trên Parabolic SAR
    """
    
    def __init__(self, acceleration_factor: float = 0.02, acceleration_max: float = 0.2, data_cache = None):
        """
        Khởi tạo chiến lược
        
        Args:
            acceleration_factor (float): Hệ số tăng tốc ban đầu (thường 0.02)
            acceleration_max (float): Hệ số tăng tốc tối đa (thường 0.2)
            data_cache (DataCache, optional): Cache dữ liệu
        """
        super().__init__("psar")
        self.acceleration_factor = acceleration_factor
        self.acceleration_max = acceleration_max
        self.data_cache = data_cache
    
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
        position['trailing_af'] = self.acceleration_factor
        position['trailing_af_max'] = self.acceleration_max
        position['trailing_activated'] = False
        position['trailing_stop'] = None
        
        # Lưu giá cao/thấp nhất
        if position['side'] == 'LONG':
            position['highest_price'] = position['entry_price']
            position['lowest_price'] = None
            # Giá trị SAR ban đầu (dưới mức giá vào)
            position['psar_value'] = position['entry_price'] * 0.99
        else:  # SHORT
            position['highest_price'] = None
            position['lowest_price'] = position['entry_price']
            # Giá trị SAR ban đầu (trên mức giá vào)
            position['psar_value'] = position['entry_price'] * 1.01
        
        # Lưu các giá trị Parabolic SAR
        position['psar_af'] = self.acceleration_factor
        position['psar_ep'] = position['entry_price']  # Extreme Point
        position['psar_history'] = []
        
        return position
    
    def update(self, position: Dict, current_price: float) -> Dict:
        """
        Cập nhật trailing stop dựa trên giá hiện tại
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            
        Returns:
            Dict: Thông tin vị thế đã cập nhật
        """
        entry_price = position['entry_price']
        side = position['side']
        
        # Lấy các giá trị PSAR từ position
        psar_value = position.get('psar_value')
        psar_af = position.get('psar_af', self.acceleration_factor)
        psar_ep = position.get('psar_ep', entry_price)
        af_max = position.get('trailing_af_max', self.acceleration_max)
        
        # Xử lý trường hợp psar_value là None
        if psar_value is None:
            if side == 'LONG':
                psar_value = position['entry_price'] * 0.99
            else:
                psar_value = position['entry_price'] * 1.01
        
        # Cập nhật giá cao/thấp nhất
        if side == 'LONG':
            if position.get('highest_price') is None or current_price > position['highest_price']:
                position['highest_price'] = current_price
                
                # Cập nhật EP nếu có giá cao hơn
                if current_price > psar_ep:
                    psar_ep = current_price
                    # Tăng AF nếu có EP mới
                    psar_af = min(psar_af + self.acceleration_factor, af_max)
            
            # Tính giá trị PSAR mới
            psar_value = psar_value + psar_af * (psar_ep - psar_value)
            
            # Đảm bảo PSAR không vượt quá giá thấp nhất gần đây
            # (thường là 2 nến gần nhất, nhưng ở đây đơn giản hóa)
            lowest_price = position.get('lowest_price')
            if lowest_price is not None:
                psar_value = min(psar_value, lowest_price)
        else:  # SHORT
            if position.get('lowest_price') is None or current_price < position['lowest_price']:
                position['lowest_price'] = current_price
                
                # Cập nhật EP nếu có giá thấp hơn
                if current_price < psar_ep:
                    psar_ep = current_price
                    # Tăng AF nếu có EP mới
                    psar_af = min(psar_af + self.acceleration_factor, af_max)
            
            # Tính giá trị PSAR mới
            psar_value = psar_value + psar_af * (psar_ep - psar_value)
            
            # Đảm bảo PSAR không vượt quá giá cao nhất gần đây
            highest_price = position.get('highest_price')
            if highest_price is not None:
                psar_value = max(psar_value, highest_price)
        
        # Lưu lại các giá trị
        position['psar_value'] = psar_value
        position['psar_af'] = psar_af
        position['psar_ep'] = psar_ep
        
        # Lưu lịch sử PSAR (giới hạn 10 giá trị gần nhất)
        psar_history = position.get('psar_history', [])
        psar_history.append(psar_value)
        if len(psar_history) > 10:
            psar_history = psar_history[-10:]
        position['psar_history'] = psar_history
        
        # Kiểm tra kích hoạt trailing stop
        if not position.get('trailing_activated', False):
            # Kích hoạt nếu đã có lợi nhuận tối thiểu
            min_profit_pct = 1.0  # 1%
            if side == 'LONG':
                profit_pct = (current_price - entry_price) / entry_price * 100
                if profit_pct >= min_profit_pct:
                    position['trailing_activated'] = True
                    position['trailing_stop'] = psar_value
                    logger.info(f"Đã kích hoạt PSAR trailing stop cho {position['symbol']} ở mức {psar_value:.2f}")
            else:  # SHORT
                profit_pct = (entry_price - current_price) / entry_price * 100
                if profit_pct >= min_profit_pct:
                    position['trailing_activated'] = True
                    position['trailing_stop'] = psar_value
                    logger.info(f"Đã kích hoạt PSAR trailing stop cho {position['symbol']} ở mức {psar_value:.2f}")
        else:
            # Cập nhật trailing stop theo PSAR
            position['trailing_stop'] = psar_value
            logger.debug(f"Đã cập nhật PSAR trailing stop cho {position['symbol']} thành {psar_value:.2f}")
        
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
            return False, "Trailing stop chưa kích hoạt"
        
        side = position['side']
        trailing_stop = position['trailing_stop']
        
        # Kiểm tra điều kiện đóng vị thế
        if side == 'LONG' and current_price <= trailing_stop:
            return True, f"Giá ({current_price:.2f}) đã chạm PSAR trailing stop ({trailing_stop:.2f})"
        elif side == 'SHORT' and current_price >= trailing_stop:
            return True, f"Giá ({current_price:.2f}) đã chạm PSAR trailing stop ({trailing_stop:.2f})"
        
        return False, "Giá chưa chạm trailing stop"


class StepTrailingStop(TrailingStopStrategy):
    """
    Chiến lược trailing stop bậc thang (step)
    """
    
    def __init__(self, profit_steps: List[float] = None, callback_steps: List[float] = None):
        """
        Khởi tạo chiến lược
        
        Args:
            profit_steps (List[float]): Danh sách các mức lợi nhuận (%)
            callback_steps (List[float]): Danh sách các mức callback tương ứng (%)
        """
        super().__init__("step")
        self.profit_steps = profit_steps or [1.0, 2.0, 3.0, 5.0, 8.0]
        self.callback_steps = callback_steps or [0.5, 0.8, 1.0, 1.5, 2.0]
    
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
        position['trailing_profit_steps'] = self.profit_steps
        position['trailing_callback_steps'] = self.callback_steps
        position['trailing_activated'] = False
        position['trailing_stop'] = None
        position['trailing_current_step'] = 0
        
        # Lưu giá cao/thấp nhất
        if position['side'] == 'LONG':
            position['highest_price'] = position['entry_price']
            position['lowest_price'] = None
        else:  # SHORT
            position['highest_price'] = None
            position['lowest_price'] = position['entry_price']
        
        return position
    
    def update(self, position: Dict, current_price: float) -> Dict:
        """
        Cập nhật trailing stop dựa trên giá hiện tại
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            
        Returns:
            Dict: Thông tin vị thế đã cập nhật
        """
        entry_price = position['entry_price']
        side = position['side']
        leverage = position.get('leverage', 1)
        profit_steps = position.get('trailing_profit_steps', self.profit_steps)
        callback_steps = position.get('trailing_callback_steps', self.callback_steps)
        current_step = position.get('trailing_current_step', 0)
        
        # Tính phần trăm lợi nhuận
        if side == 'LONG':
            profit_percent = (current_price - entry_price) / entry_price * 100 * leverage
            
            # Cập nhật giá cao nhất
            if position.get('highest_price') is None or current_price > position['highest_price']:
                position['highest_price'] = current_price
            
            # Kiểm tra xem đã đạt bước tiếp theo chưa
            next_step = min(current_step + 1, len(profit_steps) - 1)
            if next_step > current_step and profit_percent >= profit_steps[next_step]:
                # Đã đạt mức lợi nhuận tiếp theo, cập nhật bước
                position['trailing_current_step'] = next_step
                
                # Tính giá trailing stop mới
                callback_percent = callback_steps[next_step]
                callback_amount = position['highest_price'] * callback_percent / 100
                position['trailing_stop'] = position['highest_price'] - callback_amount
                position['trailing_activated'] = True
                
                logger.info(f"Đã cập nhật step trailing stop cho {position['symbol']} lên bước {next_step}, "
                          f"stop = {position['trailing_stop']:.2f} (callback {callback_percent}%)")
            elif position.get('trailing_activated', False):
                # Nếu đã kích hoạt, cập nhật trailing stop khi giá tăng
                if current_price > position['highest_price']:
                    position['highest_price'] = current_price
                    
                    # Cập nhật giá trailing stop
                    callback_percent = callback_steps[current_step]
                    callback_amount = position['highest_price'] * callback_percent / 100
                    position['trailing_stop'] = position['highest_price'] - callback_amount
                    
                    logger.info(f"Đã cập nhật step trailing stop cho {position['symbol']} theo giá mới, "
                              f"stop = {position['trailing_stop']:.2f}")
            elif profit_percent >= profit_steps[0] and not position.get('trailing_activated', False):
                # Kích hoạt trailing stop ở bước đầu tiên
                position['trailing_current_step'] = 0
                position['trailing_activated'] = True
                
                # Tính giá trailing stop
                callback_percent = callback_steps[0]
                callback_amount = position['highest_price'] * callback_percent / 100
                position['trailing_stop'] = position['highest_price'] - callback_amount
                
                logger.info(f"Đã kích hoạt step trailing stop cho {position['symbol']} ở mức {position['trailing_stop']:.2f}")
        else:  # SHORT
            profit_percent = (entry_price - current_price) / entry_price * 100 * leverage
            
            # Cập nhật giá thấp nhất
            if position.get('lowest_price') is None or current_price < position['lowest_price']:
                position['lowest_price'] = current_price
            
            # Kiểm tra xem đã đạt bước tiếp theo chưa
            next_step = min(current_step + 1, len(profit_steps) - 1)
            if next_step > current_step and profit_percent >= profit_steps[next_step]:
                # Đã đạt mức lợi nhuận tiếp theo, cập nhật bước
                position['trailing_current_step'] = next_step
                
                # Tính giá trailing stop mới
                callback_percent = callback_steps[next_step]
                callback_amount = position['lowest_price'] * callback_percent / 100
                position['trailing_stop'] = position['lowest_price'] + callback_amount
                position['trailing_activated'] = True
                
                logger.info(f"Đã cập nhật step trailing stop cho {position['symbol']} lên bước {next_step}, "
                          f"stop = {position['trailing_stop']:.2f} (callback {callback_percent}%)")
            elif position.get('trailing_activated', False):
                # Nếu đã kích hoạt, cập nhật trailing stop khi giá giảm
                if current_price < position['lowest_price']:
                    position['lowest_price'] = current_price
                    
                    # Cập nhật giá trailing stop
                    callback_percent = callback_steps[current_step]
                    callback_amount = position['lowest_price'] * callback_percent / 100
                    position['trailing_stop'] = position['lowest_price'] + callback_amount
                    
                    logger.info(f"Đã cập nhật step trailing stop cho {position['symbol']} theo giá mới, "
                              f"stop = {position['trailing_stop']:.2f}")
            elif profit_percent >= profit_steps[0] and not position.get('trailing_activated', False):
                # Kích hoạt trailing stop ở bước đầu tiên
                position['trailing_current_step'] = 0
                position['trailing_activated'] = True
                
                # Tính giá trailing stop
                callback_percent = callback_steps[0]
                callback_amount = position['lowest_price'] * callback_percent / 100
                position['trailing_stop'] = position['lowest_price'] + callback_amount
                
                logger.info(f"Đã kích hoạt step trailing stop cho {position['symbol']} ở mức {position['trailing_stop']:.2f}")
        
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
            return False, "Trailing stop chưa kích hoạt"
        
        side = position['side']
        trailing_stop = position['trailing_stop']
        current_step = position.get('trailing_current_step', 0)
        
        # Kiểm tra điều kiện đóng vị thế
        if side == 'LONG' and current_price <= trailing_stop:
            return True, f"Giá ({current_price:.2f}) đã chạm step trailing stop ({trailing_stop:.2f}) ở bước {current_step}"
        elif side == 'SHORT' and current_price >= trailing_stop:
            return True, f"Giá ({current_price:.2f}) đã chạm step trailing stop ({trailing_stop:.2f}) ở bước {current_step}"
        
        return False, "Giá chưa chạm trailing stop"


class AdvancedTrailingStop:
    """
    Lớp quản lý trailing stop nâng cao
    """
    
    def __init__(self, strategy_type: str = "percentage", data_cache = None, config: Dict = None):
        """
        Khởi tạo quản lý trailing stop
        
        Args:
            strategy_type (str): Loại chiến lược ('percentage', 'absolute', 'atr', 'psar', 'step')
            data_cache (DataCache, optional): Cache dữ liệu
            config (Dict, optional): Cấu hình cho chiến lược
        """
        self.data_cache = data_cache
        self.config = config or {}
        
        # Tạo chiến lược theo loại
        self.strategy_type = strategy_type
        self.strategy = self._create_strategy(strategy_type)
    
    def _create_strategy(self, strategy_type: str) -> TrailingStopStrategy:
        """
        Tạo đối tượng chiến lược theo loại
        
        Args:
            strategy_type (str): Loại chiến lược
            
        Returns:
            TrailingStopStrategy: Đối tượng chiến lược
        """
        if strategy_type == "percentage":
            activation_percent = self.config.get('activation_percent', 1.0)
            callback_percent = self.config.get('callback_percent', 0.5)
            return PercentageTrailingStop(activation_percent, callback_percent)
        
        elif strategy_type == "absolute":
            activation_amount = self.config.get('activation_amount', 100.0)
            callback_amount = self.config.get('callback_amount', 50.0)
            return AbsoluteTrailingStop(activation_amount, callback_amount)
        
        elif strategy_type == "atr":
            atr_multiplier = self.config.get('atr_multiplier', 3.0)
            atr_period = self.config.get('atr_period', 14)
            return ATRTrailingStop(atr_multiplier, atr_period, self.data_cache)
        
        elif strategy_type == "psar":
            acceleration_factor = self.config.get('acceleration_factor', 0.02)
            acceleration_max = self.config.get('acceleration_max', 0.2)
            return ParabolicSARTrailingStop(acceleration_factor, acceleration_max, self.data_cache)
        
        elif strategy_type == "step":
            profit_steps = self.config.get('profit_steps')
            callback_steps = self.config.get('callback_steps')
            return StepTrailingStop(profit_steps, callback_steps)
        
        else:
            logger.warning(f"Không hỗ trợ loại chiến lược '{strategy_type}', sử dụng mặc định 'percentage'")
            return PercentageTrailingStop()
    
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
        # Kiểm tra xem vị thế đã được khởi tạo chưa
        if 'trailing_type' not in position:
            position = self.initialize_position(position)
        
        # Kiểm tra xem loại trailing stop có khớp với chiến lược hiện tại không
        if position.get('trailing_type') != self.strategy.name:
            # Nếu không khớp, chuyển đổi sang chiến lược hiện tại
            logger.info(f"Chuyển đổi vị thế từ chiến lược {position.get('trailing_type')} sang {self.strategy.name}")
            position = self.initialize_position(position)
        
        # Cập nhật trailing stop
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
        # Kiểm tra xem vị thế đã được khởi tạo chưa
        if 'trailing_type' not in position:
            return False, "Vị thế chưa được khởi tạo trailing stop"
        
        # Kiểm tra xem loại trailing stop có khớp với chiến lược hiện tại không
        if position.get('trailing_type') != self.strategy.name:
            logger.warning(f"Loại trailing stop không khớp: {position.get('trailing_type')} vs {self.strategy.name}")
            return False, "Loại trailing stop không phù hợp"
        
        # Kiểm tra điều kiện đóng vị thế
        return self.strategy.should_close(position, current_price)
    
    def get_strategy_name(self) -> str:
        """
        Lấy tên chiến lược hiện tại
        
        Returns:
            str: Tên chiến lược
        """
        return self.strategy.name
    
    def change_strategy(self, new_strategy_type: str, config: Dict = None) -> bool:
        """
        Đổi chiến lược trailing stop
        
        Args:
            new_strategy_type (str): Loại chiến lược mới
            config (Dict, optional): Cấu hình cho chiến lược mới
            
        Returns:
            bool: True nếu thay đổi thành công, False nếu không
        """
        try:
            # Cập nhật cấu hình nếu có
            if config:
                self.config.update(config)
            
            # Tạo chiến lược mới
            self.strategy = self._create_strategy(new_strategy_type)
            self.strategy_type = new_strategy_type
            
            logger.info(f"Đã chuyển đổi sang chiến lược {new_strategy_type}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi chuyển đổi chiến lược: {str(e)}")
            return False


def main():
    """Hàm chính để test AdvancedTrailingStop"""
    
    print("=== Test AdvancedTrailingStop ===\n")
    
    # Tạo vị thế giả lập
    position_long = {
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry_price': 60000,
        'quantity': 0.1,
        'leverage': 10,
        'entry_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    position_short = {
        'symbol': 'ETHUSDT',
        'side': 'SHORT',
        'entry_price': 3000,
        'quantity': 1.0,
        'leverage': 5,
        'entry_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Test PercentageTrailingStop
    print("--- Test PercentageTrailingStop ---")
    ts_percentage = AdvancedTrailingStop("percentage", None, {
        "activation_percent": 1.0,
        "callback_percent": 0.5
    })
    
    # Khởi tạo vị thế
    position_long = ts_percentage.initialize_position(position_long)
    print(f"Đã khởi tạo vị thế LONG với chiến lược {position_long['trailing_type']}")
    
    # Mô phỏng tăng giá
    print("\nMô phỏng tăng giá:")
    prices = [60200, 60500, 60800, 61000, 60800, 60500]
    for price in prices:
        position_long = ts_percentage.update_trailing_stop(position_long, price)
        should_close, reason = ts_percentage.check_stop_condition(position_long, price)
        
        print(f"Giá: {price}, Trailing kích hoạt: {position_long['trailing_activated']}, "
            f"Stop: {position_long.get('trailing_stop')}, Đóng: {should_close}")
    
    # Test ATRTrailingStop
    print("\n--- Test ATRTrailingStop ---")
    
    # Tạo mock DataCache
    class MockDataCache:
        def get(self, category, key):
            if key == "ETHUSDT_1h_atr_14":
                return 150  # ~5% của giá entry
            return None
    
    ts_atr = AdvancedTrailingStop("atr", MockDataCache(), {
        "atr_multiplier": 2.0
    })
    
    # Khởi tạo vị thế
    position_short = ts_atr.initialize_position(position_short)
    print(f"Đã khởi tạo vị thế SHORT với chiến lược {position_short['trailing_type']}")
    
    # Mô phỏng giảm giá
    print("\nMô phỏng giảm giá:")
    prices = [2950, 2900, 2850, 2800, 2850, 2900]
    for price in prices:
        position_short = ts_atr.update_trailing_stop(position_short, price)
        should_close, reason = ts_atr.check_stop_condition(position_short, price)
        
        print(f"Giá: {price}, Trailing kích hoạt: {position_short['trailing_activated']}, "
            f"Stop: {position_short.get('trailing_stop')}, Đóng: {should_close}")
    
    # Test thay đổi chiến lược
    print("\n--- Test đổi chiến lược ---")
    print(f"Chiến lược hiện tại: {ts_percentage.get_strategy_name()}")
    
    result = ts_percentage.change_strategy("step", {
        "profit_steps": [1.0, 2.0, 3.0],
        "callback_steps": [0.5, 0.8, 1.0]
    })
    
    print(f"Đổi chiến lược thành 'step': {'Thành công' if result else 'Thất bại'}")
    print(f"Chiến lược mới: {ts_percentage.get_strategy_name()}")


if __name__ == "__main__":
    main()