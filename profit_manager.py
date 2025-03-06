#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module quản lý chốt lời (Profit Manager)

Module này cung cấp các chiến lược chốt lời đa dạng và nâng cao như:
- Chốt lời theo thời gian
- Chốt lời theo mức lãi mục tiêu
- Chốt lời theo chỉ báo kỹ thuật
- Chốt lời theo đảo chiều giá
- Quản lý chốt lời động theo biến động

Mỗi chiến lược có thể được kích hoạt/tắt và cấu hình độc lập.
"""

import time
import logging
from typing import Dict, Tuple, List, Optional, Any
from datetime import datetime, timedelta

# Thiết lập logging
logger = logging.getLogger(__name__)

class ProfitStrategy:
    """
    Lớp cơ sở cho các chiến lược chốt lời
    """
    
    def __init__(self, name: str):
        """
        Khởi tạo chiến lược
        
        Args:
            name (str): Tên chiến lược
        """
        self.name = name
        self.enabled = True
    
    def initialize(self, position: Dict) -> Dict:
        """
        Khởi tạo tham số cho chiến lược
        
        Args:
            position (Dict): Thông tin vị thế
            
        Returns:
            Dict: Thông tin vị thế đã cập nhật
        """
        return position
    
    def should_close(self, position: Dict, current_price: float, 
                    current_time: datetime = None, market_data: Dict = None) -> Tuple[bool, str]:
        """
        Kiểm tra xem có nên đóng vị thế không
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            current_time (datetime, optional): Thời gian hiện tại
            market_data (Dict, optional): Dữ liệu thị trường bổ sung
            
        Returns:
            Tuple[bool, str]: (Có nên đóng hay không, Lý do)
        """
        return False, None


class TimeBasedProfit(ProfitStrategy):
    """
    Chiến lược chốt lời dựa trên thời gian giữ vị thế
    """
    
    def __init__(self, max_hold_time: int = 48):
        """
        Khởi tạo chiến lược
        
        Args:
            max_hold_time (int): Thời gian tối đa giữ vị thế (giờ)
        """
        super().__init__("time_based")
        self.max_hold_time = max_hold_time
    
    def initialize(self, position: Dict) -> Dict:
        """
        Khởi tạo tham số cho chiến lược
        
        Args:
            position (Dict): Thông tin vị thế
            
        Returns:
            Dict: Thông tin vị thế đã cập nhật
        """
        position['max_hold_time'] = self.max_hold_time
        
        # Đảm bảo có entry_time
        if 'entry_time' not in position:
            position['entry_time'] = datetime.now()
            
        return position
    
    def should_close(self, position: Dict, current_price: float, 
                   current_time: datetime = None, market_data: Dict = None) -> Tuple[bool, str]:
        """
        Kiểm tra xem có nên đóng vị thế không dựa trên thời gian
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            current_time (datetime, optional): Thời gian hiện tại, mặc định là now()
            market_data (Dict, optional): Dữ liệu thị trường bổ sung
            
        Returns:
            Tuple[bool, str]: (Có nên đóng hay không, Lý do)
        """
        if not self.enabled:
            return False, None
            
        max_hold_time = position.get('max_hold_time', self.max_hold_time)
        entry_time = position.get('entry_time')
        
        if not entry_time:
            return False, None
            
        if not current_time:
            current_time = datetime.now()
            
        # Tính thời gian đã giữ vị thế
        if isinstance(entry_time, str):
            try:
                entry_time = datetime.strptime(entry_time, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    entry_time = datetime.fromisoformat(entry_time)
                except ValueError:
                    logger.error(f"Không thể chuyển đổi entry_time: {entry_time}")
                    return False, None
        
        hold_duration = (current_time - entry_time).total_seconds() / 3600
        
        if hold_duration >= max_hold_time:
            return True, f"Chốt lời theo thời gian sau {max_hold_time} giờ"
        
        return False, None


class TargetProfitStrategy(ProfitStrategy):
    """
    Chiến lược chốt lời khi đạt mức lãi mục tiêu
    """
    
    def __init__(self, profit_target: float = 5.0):
        """
        Khởi tạo chiến lược
        
        Args:
            profit_target (float): Mức lãi mục tiêu (%)
        """
        super().__init__("target_profit")
        self.profit_target = profit_target
    
    def initialize(self, position: Dict) -> Dict:
        """
        Khởi tạo tham số cho chiến lược
        
        Args:
            position (Dict): Thông tin vị thế
            
        Returns:
            Dict: Thông tin vị thế đã cập nhật
        """
        position['profit_target'] = self.profit_target
        return position
    
    def should_close(self, position: Dict, current_price: float, 
                   current_time: datetime = None, market_data: Dict = None) -> Tuple[bool, str]:
        """
        Kiểm tra xem có nên đóng vị thế khi đạt mức lãi mục tiêu
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            current_time (datetime, optional): Thời gian hiện tại
            market_data (Dict, optional): Dữ liệu thị trường bổ sung
            
        Returns:
            Tuple[bool, str]: (Có nên đóng hay không, Lý do)
        """
        if not self.enabled:
            return False, None
            
        profit_target = position.get('profit_target', self.profit_target)
        entry_price = position.get('entry_price')
        side = position.get('side')
        
        if not entry_price or not side:
            return False, None
            
        # Tính lợi nhuận hiện tại theo phần trăm
        if side == 'LONG':
            current_profit_pct = (current_price - entry_price) / entry_price * 100
        else:  # SHORT
            current_profit_pct = (entry_price - current_price) / entry_price * 100
            
        if current_profit_pct >= profit_target:
            return True, f"Chốt lời khi đạt {profit_target:.2f}% lợi nhuận"
        
        return False, None


class IndicatorBasedProfit(ProfitStrategy):
    """
    Chiến lược chốt lời dựa trên chỉ báo kỹ thuật
    """
    
    def __init__(self, rsi_overbought: float = 70.0, rsi_oversold: float = 30.0):
        """
        Khởi tạo chiến lược
        
        Args:
            rsi_overbought (float): Ngưỡng quá mua RSI
            rsi_oversold (float): Ngưỡng quá bán RSI
        """
        super().__init__("indicator_based")
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
    
    def initialize(self, position: Dict) -> Dict:
        """
        Khởi tạo tham số cho chiến lược
        
        Args:
            position (Dict): Thông tin vị thế
            
        Returns:
            Dict: Thông tin vị thế đã cập nhật
        """
        position['rsi_overbought'] = self.rsi_overbought
        position['rsi_oversold'] = self.rsi_oversold
        return position
    
    def should_close(self, position: Dict, current_price: float, 
                   current_time: datetime = None, market_data: Dict = None) -> Tuple[bool, str]:
        """
        Kiểm tra xem có nên đóng vị thế dựa trên chỉ báo kỹ thuật
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            current_time (datetime, optional): Thời gian hiện tại
            market_data (Dict, optional): Dữ liệu thị trường bổ sung
            
        Returns:
            Tuple[bool, str]: (Có nên đóng hay không, Lý do)
        """
        if not self.enabled or not market_data:
            return False, None
            
        rsi_overbought = position.get('rsi_overbought', self.rsi_overbought)
        rsi_oversold = position.get('rsi_oversold', self.rsi_oversold)
        side = position.get('side')
        
        if not side:
            return False, None
            
        # Lấy giá trị RSI từ dữ liệu thị trường
        rsi = market_data.get('rsi')
        
        if rsi is None:
            return False, None
            
        if side == 'LONG' and rsi > rsi_overbought:
            return True, f"Chốt lời khi RSI vượt ngưỡng quá mua (RSI = {rsi:.2f})"
        elif side == 'SHORT' and rsi < rsi_oversold:
            return True, f"Chốt lời khi RSI vượt ngưỡng quá bán (RSI = {rsi:.2f})"
        
        return False, None


class PriceReversalProfit(ProfitStrategy):
    """
    Chiến lược chốt lời khi phát hiện đảo chiều giá
    """
    
    def __init__(self, candle_count: int = 3):
        """
        Khởi tạo chiến lược
        
        Args:
            candle_count (int): Số lượng nến liên tiếp để xác định đảo chiều
        """
        super().__init__("price_reversal")
        self.candle_count = candle_count
    
    def initialize(self, position: Dict) -> Dict:
        """
        Khởi tạo tham số cho chiến lược
        
        Args:
            position (Dict): Thông tin vị thế
            
        Returns:
            Dict: Thông tin vị thế đã cập nhật
        """
        position['candle_count'] = self.candle_count
        return position
    
    def should_close(self, position: Dict, current_price: float, 
                   current_time: datetime = None, market_data: Dict = None) -> Tuple[bool, str]:
        """
        Kiểm tra xem có nên đóng vị thế khi phát hiện đảo chiều giá
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            current_time (datetime, optional): Thời gian hiện tại
            market_data (Dict, optional): Dữ liệu thị trường bổ sung
            
        Returns:
            Tuple[bool, str]: (Có nên đóng hay không, Lý do)
        """
        if not self.enabled or not market_data:
            return False, None
            
        candle_count = position.get('candle_count', self.candle_count)
        side = position.get('side')
        
        if not side:
            return False, None
            
        # Lấy dữ liệu giá từ market_data
        price_history = market_data.get('price_history', [])
        
        if len(price_history) < candle_count:
            return False, None
            
        # Lấy n nến gần nhất
        recent_candles = price_history[:candle_count]
        
        if side == 'LONG':
            # Phát hiện đảo chiều giảm: n nến đỏ liên tiếp
            if all(candle['close'] < candle['open'] for candle in recent_candles):
                return True, f"Chốt lời khi phát hiện đảo chiều giảm ({candle_count} nến đỏ liên tiếp)"
        else:  # SHORT
            # Phát hiện đảo chiều tăng: n nến xanh liên tiếp
            if all(candle['close'] > candle['open'] for candle in recent_candles):
                return True, f"Chốt lời khi phát hiện đảo chiều tăng ({candle_count} nến xanh liên tiếp)"
        
        return False, None


class DynamicVolatilityProfit(ProfitStrategy):
    """
    Chiến lược quản lý chốt lời động theo biến động thị trường
    """
    
    def __init__(self, low_vol_target: float = 1.5, 
               medium_vol_target: float = 3.0, 
               high_vol_target: float = 5.0):
        """
        Khởi tạo chiến lược
        
        Args:
            low_vol_target (float): Mức lãi mục tiêu khi biến động thấp (%)
            medium_vol_target (float): Mức lãi mục tiêu khi biến động vừa (%)
            high_vol_target (float): Mức lãi mục tiêu khi biến động cao (%)
        """
        super().__init__("dynamic_volatility")
        self.low_vol_target = low_vol_target
        self.medium_vol_target = medium_vol_target
        self.high_vol_target = high_vol_target
    
    def initialize(self, position: Dict) -> Dict:
        """
        Khởi tạo tham số cho chiến lược
        
        Args:
            position (Dict): Thông tin vị thế
            
        Returns:
            Dict: Thông tin vị thế đã cập nhật
        """
        position['low_vol_target'] = self.low_vol_target
        position['medium_vol_target'] = self.medium_vol_target
        position['high_vol_target'] = self.high_vol_target
        return position
    
    def should_close(self, position: Dict, current_price: float, 
                   current_time: datetime = None, market_data: Dict = None) -> Tuple[bool, str]:
        """
        Kiểm tra xem có nên đóng vị thế dựa trên biến động
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            current_time (datetime, optional): Thời gian hiện tại
            market_data (Dict, optional): Dữ liệu thị trường bổ sung
            
        Returns:
            Tuple[bool, str]: (Có nên đóng hay không, Lý do)
        """
        if not self.enabled or not market_data:
            return False, None
            
        low_vol_target = position.get('low_vol_target', self.low_vol_target)
        medium_vol_target = position.get('medium_vol_target', self.medium_vol_target)
        high_vol_target = position.get('high_vol_target', self.high_vol_target)
        
        entry_price = position.get('entry_price')
        side = position.get('side')
        
        if not entry_price or not side:
            return False, None
            
        # Lấy biến động từ market_data
        volatility = market_data.get('volatility')
        
        if volatility is None:
            return False, None
            
        # Tính toán mức lãi mục tiêu dựa trên biến động
        if volatility <= 0.01:  # Biến động thấp
            target_profit = low_vol_target
        elif volatility <= 0.03:  # Biến động vừa
            target_profit = medium_vol_target
        else:  # Biến động cao
            target_profit = high_vol_target
        
        # Tính lợi nhuận hiện tại
        if side == 'LONG':
            current_profit_pct = (current_price - entry_price) / entry_price * 100
        else:  # SHORT
            current_profit_pct = (entry_price - current_price) / entry_price * 100
        
        if current_profit_pct >= target_profit:
            return True, f"Chốt lời động theo biến động thị trường ({target_profit:.2f}%)"
        
        return False, None


class ProfitManager:
    """
    Lớp quản lý chốt lời tổng hợp
    """
    
    def __init__(self, config: Dict = None, data_cache = None):
        """
        Khởi tạo quản lý chốt lời
        
        Args:
            config (Dict, optional): Cấu hình cho các chiến lược
            data_cache (DataCache, optional): Cache dữ liệu
        """
        self.data_cache = data_cache
        self.strategies = {}
        
        # Khởi tạo các chiến lược mặc định
        self._create_default_strategies()
        
        # Cập nhật cấu hình nếu có
        if config:
            self._update_strategies_config(config)
    
    def _create_default_strategies(self):
        """Tạo các chiến lược mặc định"""
        self.strategies = {
            'time_based': TimeBasedProfit(),
            'target_profit': TargetProfitStrategy(),
            'indicator_based': IndicatorBasedProfit(),
            'price_reversal': PriceReversalProfit(),
            'dynamic_volatility': DynamicVolatilityProfit()
        }
    
    def _update_strategies_config(self, config: Dict):
        """
        Cập nhật cấu hình cho các chiến lược
        
        Args:
            config (Dict): Cấu hình mới
        """
        for strategy_name, strategy_config in config.items():
            if strategy_name in self.strategies:
                # Bật/tắt chiến lược
                if 'enabled' in strategy_config:
                    self.strategies[strategy_name].enabled = strategy_config['enabled']
                
                # Cập nhật các tham số
                for param_name, param_value in strategy_config.items():
                    if param_name != 'enabled' and hasattr(self.strategies[strategy_name], param_name):
                        setattr(self.strategies[strategy_name], param_name, param_value)
    
    def initialize_position(self, position: Dict) -> Dict:
        """
        Khởi tạo vị thế với các tham số chốt lời
        
        Args:
            position (Dict): Thông tin vị thế
            
        Returns:
            Dict: Thông tin vị thế đã cập nhật
        """
        # Thêm tham số mặc định
        if 'profit_strategies' not in position:
            position['profit_strategies'] = []
        
        # Khởi tạo tham số cho từng chiến lược
        for strategy_name, strategy in self.strategies.items():
            if strategy.enabled:
                position = strategy.initialize(position)
                if strategy_name not in position['profit_strategies']:
                    position['profit_strategies'].append(strategy_name)
        
        return position
    
    def check_profit_conditions(self, position: Dict, current_price: float, 
                               current_time: datetime = None) -> Tuple[bool, str]:
        """
        Kiểm tra các điều kiện chốt lời
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            current_time (datetime, optional): Thời gian hiện tại
            
        Returns:
            Tuple[bool, str]: (Có nên đóng hay không, Lý do)
        """
        if not current_time:
            current_time = datetime.now()
        
        symbol = position.get('symbol')
        
        # Lấy dữ liệu thị trường từ cache nếu có
        market_data = {}
        if self.data_cache and symbol:
            # Lấy các chỉ báo cần thiết
            timeframe = '1h'  # Mặc định
            market_data = {
                'rsi': self.data_cache.get('indicators', f"{symbol}_{timeframe}_rsi"),
                'volatility': self.data_cache.get('market_analysis', f"{symbol}_{timeframe}_volatility"),
                'price_history': self.data_cache.get('market_data', f"{symbol}_{timeframe}_candles", [])
            }
        
        # Kiểm tra từng chiến lược
        active_strategies = position.get('profit_strategies', [])
        
        for strategy_name, strategy in self.strategies.items():
            if strategy.enabled and (not active_strategies or strategy_name in active_strategies):
                should_close, reason = strategy.should_close(
                    position, current_price, current_time, market_data
                )
                
                if should_close:
                    return True, reason
        
        return False, None
    
    def add_strategy(self, strategy: ProfitStrategy) -> bool:
        """
        Thêm một chiến lược mới
        
        Args:
            strategy (ProfitStrategy): Chiến lược cần thêm
            
        Returns:
            bool: True nếu thêm thành công, False nếu không
        """
        if strategy.name in self.strategies:
            logger.warning(f"Chiến lược {strategy.name} đã tồn tại, sẽ bị ghi đè")
        
        self.strategies[strategy.name] = strategy
        return True
    
    def remove_strategy(self, strategy_name: str) -> bool:
        """
        Xóa một chiến lược
        
        Args:
            strategy_name (str): Tên chiến lược cần xóa
            
        Returns:
            bool: True nếu xóa thành công, False nếu không
        """
        if strategy_name in self.strategies:
            del self.strategies[strategy_name]
            return True
        
        return False
    
    def toggle_strategy(self, strategy_name: str, enabled: bool) -> bool:
        """
        Bật/tắt một chiến lược
        
        Args:
            strategy_name (str): Tên chiến lược
            enabled (bool): Trạng thái
            
        Returns:
            bool: True nếu thành công, False nếu không
        """
        if strategy_name in self.strategies:
            self.strategies[strategy_name].enabled = enabled
            return True
        
        return False
    
    def update_strategy_params(self, strategy_name: str, params: Dict) -> bool:
        """
        Cập nhật tham số cho một chiến lược
        
        Args:
            strategy_name (str): Tên chiến lược
            params (Dict): Tham số mới
            
        Returns:
            bool: True nếu thành công, False nếu không
        """
        if strategy_name not in self.strategies:
            return False
        
        for param_name, param_value in params.items():
            if hasattr(self.strategies[strategy_name], param_name):
                setattr(self.strategies[strategy_name], param_name, param_value)
        
        return True
    
    def get_active_strategies(self) -> List[str]:
        """
        Lấy danh sách chiến lược đang hoạt động
        
        Returns:
            List[str]: Danh sách tên chiến lược
        """
        return [name for name, strategy in self.strategies.items() if strategy.enabled]


def main():
    """Hàm chính để test ProfitManager"""
    # Thiết lập logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Tạo vị thế mẫu
    position = {
        'id': 'test_position',
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry_price': 50000,
        'quantity': 0.1,
        'entry_time': datetime.now() - timedelta(hours=24)  # 24 giờ trước
    }
    
    # Tạo dữ liệu thị trường mẫu
    class MockDataCache:
        def get(self, category, key, default=None):
            if key == 'BTCUSDT_1h_rsi':
                return 75  # RSI cao
            elif key == 'BTCUSDT_1h_volatility':
                return 0.02  # Biến động vừa
            elif key == 'BTCUSDT_1h_candles':
                # 3 nến đỏ liên tiếp
                return [
                    {'open': 52000, 'close': 51800, 'high': 52100, 'low': 51700},
                    {'open': 51800, 'close': 51600, 'high': 51900, 'low': 51500},
                    {'open': 51600, 'close': 51400, 'high': 51700, 'low': 51300}
                ]
            return default
    
    # Tạo profit manager
    profit_manager = ProfitManager(data_cache=MockDataCache())
    
    # Khởi tạo vị thế
    position = profit_manager.initialize_position(position)
    
    # Kiểm tra điều kiện chốt lời với giá hiện tại
    current_price = 52500  # Lãi 5%
    
    should_close, reason = profit_manager.check_profit_conditions(position, current_price)
    
    if should_close:
        logger.info(f"Nên đóng vị thế: {reason}")
    else:
        logger.info("Chưa đóng vị thế")
    
    # Kiểm tra theo thời gian
    position['entry_time'] = datetime.now() - timedelta(hours=50)  # 50 giờ trước
    should_close, reason = profit_manager.check_profit_conditions(position, current_price)
    
    if should_close:
        logger.info(f"Nên đóng vị thế: {reason}")
    else:
        logger.info("Chưa đóng vị thế")


if __name__ == "__main__":
    main()