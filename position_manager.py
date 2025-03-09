#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module quản lý vị thế giao dịch (Position Manager)

Module này kết hợp AdvancedTrailingStop và ProfitManager để quản lý toàn diện
vị thế giao dịch, bao gồm trailing stop, chốt lời, và quản lý rủi ro.
"""

import time
import logging
from typing import Dict, Tuple, List, Optional, Any
from datetime import datetime

from advanced_trailing_stop import AdvancedTrailingStop
from profit_manager import ProfitManager

# Thiết lập logging
logger = logging.getLogger(__name__)

class PositionManager:
    """
    Lớp quản lý vị thế giao dịch tổng hợp
    """
    
    def __init__(self, 
                 trailing_stop_config: Dict = None, 
                 profit_manager_config: Dict = None,
                 data_cache = None):
        """
        Khởi tạo quản lý vị thế
        
        Args:
            trailing_stop_config (Dict, optional): Cấu hình cho trailing stop
            profit_manager_config (Dict, optional): Cấu hình cho profit manager
            data_cache (DataCache, optional): Cache dữ liệu
        """
        self.data_cache = data_cache
        
        # Khởi tạo các thành phần
        self.trailing_stop = AdvancedTrailingStop(
            strategy_type=trailing_stop_config.get('strategy_type', 'percentage') if trailing_stop_config else 'percentage',
            config=trailing_stop_config.get('config', {}) if trailing_stop_config else {},
            data_cache=data_cache
        )
        
        self.profit_manager = ProfitManager(
            config=profit_manager_config,
            data_cache=data_cache
        )
    
    def initialize_position(self, position: Dict) -> Dict:
        """
        Khởi tạo vị thế với tất cả các tham số quản lý
        
        Args:
            position (Dict): Thông tin vị thế
            
        Returns:
            Dict: Thông tin vị thế đã cập nhật
        """
        # Khởi tạo trailing stop
        position = self.trailing_stop.initialize_position(position)
        
        # Khởi tạo profit manager
        position = self.profit_manager.initialize_position(position)
        
        # Đảm bảo có entry_time
        if 'entry_time' not in position:
            position['entry_time'] = datetime.now()
        
        return position
    
    def update_position(self, position: Dict, current_price: float, current_time: datetime = None) -> Dict:
        """
        Cập nhật trạng thái vị thế
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            current_time (datetime, optional): Thời gian hiện tại
            
        Returns:
            Dict: Thông tin vị thế đã cập nhật
        """
        # Cập nhật trailing stop
        position = self.trailing_stop.update_trailing_stop(position, current_price)
        
        return position
    
    def check_exit_conditions(self, position: Dict, current_price: float, 
                             current_time: datetime = None) -> Tuple[bool, str]:
        """
        Kiểm tra các điều kiện đóng vị thế
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            current_time (datetime, optional): Thời gian hiện tại
            
        Returns:
            Tuple[bool, str]: (Có nên đóng hay không, Lý do)
        """
        if not current_time:
            current_time = datetime.now()
        
        # Kiểm tra trailing stop
        should_close, reason = self.trailing_stop.check_stop_condition(position, current_price)
        
        if should_close:
            return True, reason
        
        # Kiểm tra profit manager
        should_close, reason = self.profit_manager.check_profit_conditions(
            position, current_price, current_time
        )
        
        if should_close:
            return True, reason
        
        return False, None
    
    def get_trailing_stop_status(self, position: Dict) -> Dict:
        """
        Lấy trạng thái trailing stop
        
        Args:
            position (Dict): Thông tin vị thế
            
        Returns:
            Dict: Trạng thái trailing stop
        """
        return {
            'strategy': self.trailing_stop.get_strategy_name(),
            'activated': position.get('trailing_activated', False),
            'stop_price': position.get('trailing_stop')
        }
    
    def get_profit_strategies(self) -> List[str]:
        """
        Lấy danh sách chiến lược chốt lời đang hoạt động
        
        Returns:
            List[str]: Danh sách tên chiến lược
        """
        return self.profit_manager.get_active_strategies()
    
    def change_trailing_strategy(self, new_strategy_type: str, config: Dict = None) -> bool:
        """
        Thay đổi chiến lược trailing stop
        
        Args:
            new_strategy_type (str): Loại chiến lược mới
            config (Dict, optional): Cấu hình mới
            
        Returns:
            bool: True nếu thành công, False nếu không
        """
        return self.trailing_stop.change_strategy(new_strategy_type, config)
    
    def toggle_profit_strategy(self, strategy_name: str, enabled: bool) -> bool:
        """
        Bật/tắt một chiến lược chốt lời
        
        Args:
            strategy_name (str): Tên chiến lược
            enabled (bool): Trạng thái
            
        Returns:
            bool: True nếu thành công, False nếu không
        """
        return self.profit_manager.toggle_strategy(strategy_name, enabled)
    
    def update_profit_strategy(self, strategy_name: str, params: Dict) -> bool:
        """
        Cập nhật tham số cho một chiến lược chốt lời
        
        Args:
            strategy_name (str): Tên chiến lược
            params (Dict): Tham số mới
            
        Returns:
            bool: True nếu thành công, False nếu không
        """
        return self.profit_manager.update_strategy_params(strategy_name, params)
    
    def generate_position_summary(self, position: Dict, current_price: float) -> Dict:
        """
        Tạo tóm tắt vị thế
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            
        Returns:
            Dict: Tóm tắt vị thế
        """
        entry_price = position.get('entry_price')
        side = position.get('side')
        quantity = position.get('quantity')
        entry_time = position.get('entry_time')
        
        # Tính lợi nhuận hiện tại
        current_profit = 0
        current_profit_pct = 0
        
        if entry_price and side and current_price:
            if side == 'LONG':
                current_profit = (current_price - entry_price) * quantity
                current_profit_pct = (current_price - entry_price) / entry_price * 100
            else:  # SHORT
                current_profit = (entry_price - current_price) * quantity
                current_profit_pct = (entry_price - current_price) / entry_price * 100
        
        # Thời gian giữ vị thế
        hold_duration = None
        if entry_time:
            if isinstance(entry_time, str):
                try:
                    entry_time = datetime.strptime(entry_time, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        entry_time = datetime.fromisoformat(entry_time)
                    except ValueError:
                        entry_time = None
            
            if entry_time:
                hold_duration = (datetime.now() - entry_time).total_seconds() / 3600  # giờ
        
        # Tóm tắt
        summary = {
            'id': position.get('id'),
            'symbol': position.get('symbol'),
            'side': side,
            'entry_price': entry_price,
            'current_price': current_price,
            'quantity': quantity,
            'current_profit': current_profit,
            'current_profit_pct': current_profit_pct,
            'entry_time': entry_time,
            'hold_duration_hours': hold_duration,
            'trailing_stop': self.get_trailing_stop_status(position),
            'profit_strategies': position.get('profit_strategies', [])
        }
        
        return summary


def main():
    """Hàm chính để test PositionManager"""
    # Thiết lập logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Tạo cấu hình
    trailing_config = {
        'strategy_type': 'percentage',
        'config': {
            'activation_percent': 1.0,
            'callback_percent': 0.5
        }
    }
    
    profit_config = {
        'time_based': {
            'enabled': True,
            'max_hold_time': 48
        },
        'target_profit': {
            'enabled': True,
            'profit_target': 5.0
        }
    }
    
    # Tạo position manager
    position_manager = PositionManager(trailing_config, profit_config)
    
    # Tạo vị thế
    position = {
        'id': 'test_position',
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry_price': 50000,
        'quantity': 0.1,
        'entry_time': datetime.now()
    }
    
    # Khởi tạo vị thế
    position = position_manager.initialize_position(position)
    
    # Mô phỏng cập nhật giá
    prices = [
        50100,  # +0.2%
        50300,  # +0.6%
        50500,  # +1.0% (kích hoạt trailing stop)
        50700,  # +1.4%
        50900,  # +1.8%
        50700,  # +1.4%
        50500,  # +1.0%
        50300   # +0.6%
    ]
    
    for price in prices:
        # Cập nhật vị thế
        position = position_manager.update_position(position, price)
        
        # Kiểm tra điều kiện đóng
        should_close, reason = position_manager.check_exit_conditions(position, price)
        
        # Hiển thị trạng thái
        summary = position_manager.generate_position_summary(position, price)
        logger.info(f"Giá: {price}, Lợi nhuận: {summary['current_profit_pct']:.2f}%, "
                   f"Trailing: {summary['trailing_stop']['stop_price']}")
        
        if should_close:
            logger.info(f"Đóng vị thế: {reason}")
            break


if __name__ == "__main__":
    main()