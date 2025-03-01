"""
Module quản lý vốn nâng cao (Advanced Position Sizing)

Module này cung cấp các công cụ tiên tiến để tính toán và quản lý kích thước vị thế:
- Kelly Criterion cho tối ưu hóa kỳ vọng
- Anti-Martingale position sizing thông minh
- Quản lý vốn động theo điều kiện thị trường
- Phân bổ danh mục đầu tư với model tương quan

Mục tiêu là tối ưu hóa kích thước lệnh dựa trên đặc điểm thị trường,
tỷ lệ thắng kỳ vọng, và bảo vệ tài khoản khi thị trường bất lợi.
"""

import numpy as np
import logging
from typing import Dict, List, Tuple, Union, Optional

# Cấu hình logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("position_sizing")

class BasePositionSizer:
    """Lớp cơ sở để tính toán kích thước vị thế theo phần trăm rủi ro"""
    
    def __init__(self, account_balance: float, max_risk_pct: float = 2.0, 
                leverage: int = 1, min_position_size: float = 0.0):
        """
        Khởi tạo Position Sizer cơ bản.
        
        Args:
            account_balance (float): Số dư tài khoản
            max_risk_pct (float): Phần trăm rủi ro tối đa trên mỗi giao dịch (%)
            leverage (int): Đòn bẩy
            min_position_size (float): Kích thước vị thế tối thiểu
        """
        self.account_balance = max(0.0, account_balance)
        self.max_risk_pct = max(0.1, min(max_risk_pct, 10.0))  # Giới hạn 0.1% đến 10%
        self.leverage = max(1, leverage)
        self.min_position_size = max(0.0, min_position_size)
        
    def calculate_position_size(self, entry_price: float, stop_loss_price: float, 
                              **kwargs) -> Tuple[float, float]:
        """
        Tính toán kích thước vị thế dựa trên mức rủi ro.
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss_price (float): Giá dừng lỗ
            **kwargs: Tham số bổ sung
            
        Returns:
            Tuple[float, float]: (kích thước vị thế, phần trăm rủi ro thực tế)
        """
        # Validate input
        if entry_price <= 0:
            logger.warning(f"Invalid entry price: {entry_price}")
            return 0.0, 0.0
            
        if stop_loss_price <= 0:
            logger.warning(f"Invalid stop loss price: {stop_loss_price}")
            return 0.0, 0.0
            
        # Tính phần trăm rủi ro trên mỗi đơn vị
        if entry_price == stop_loss_price:
            logger.warning("Entry price equals stop loss price")
            return 0.0, 0.0
            
        # Tính kích thước vị thế
        if entry_price > stop_loss_price:  # Long position
            risk_per_unit = (entry_price - stop_loss_price) / entry_price
        else:  # Short position
            risk_per_unit = (stop_loss_price - entry_price) / entry_price
            
        # Nếu rủi ro trên đơn vị quá nhỏ hoặc bằng 0, đặt một giá trị tối thiểu an toàn
        risk_per_unit = max(risk_per_unit, 0.001)  # Tối thiểu 0.1%
        
        # Tính số tiền rủi ro
        risk_amount = self.account_balance * (self.max_risk_pct / 100)
        
        # Tính kích thước vị thế (số lượng)
        position_size = risk_amount / (entry_price * risk_per_unit)
        
        # Điều chỉnh cho đòn bẩy
        position_size = position_size * self.leverage
        
        # Đảm bảo kích thước tối thiểu
        position_size = max(self.min_position_size, position_size)
        
        # Tính phần trăm rủi ro thực tế
        actual_risk_pct = (position_size * entry_price * risk_per_unit) / self.account_balance * 100
        actual_risk_pct = min(actual_risk_pct, self.max_risk_pct)  # Giới hạn theo max_risk_pct
        
        logger.debug(f"Calculated position size: {position_size:.6f}, risk: {actual_risk_pct:.2f}%")
        return position_size, actual_risk_pct
        
    def update_account_balance(self, new_balance: float) -> None:
        """
        Cập nhật số dư tài khoản.
        
        Args:
            new_balance (float): Số dư tài khoản mới
        """
        self.account_balance = max(0.0, new_balance)
        logger.debug(f"Updated account balance: {self.account_balance}")


class DynamicPositionSizer(BasePositionSizer):
    """Lớp tính toán kích thước vị thế động theo biến động thị trường"""
    
    def __init__(self, account_balance: float, max_risk_pct: float = 2.0, 
                leverage: int = 1, volatility_factor: float = 1.0, 
                confidence_factor: float = 1.0, min_position_size: float = 0.0):
        """
        Khởi tạo Dynamic Position Sizer.
        
        Args:
            account_balance (float): Số dư tài khoản
            max_risk_pct (float): Phần trăm rủi ro tối đa trên mỗi giao dịch (%)
            leverage (int): Đòn bẩy
            volatility_factor (float): Hệ số điều chỉnh theo biến động (>1 giảm size khi volatility cao)
            confidence_factor (float): Hệ số điều chỉnh theo độ tin cậy tín hiệu
            min_position_size (float): Kích thước vị thế tối thiểu
        """
        super().__init__(account_balance, max_risk_pct, leverage, min_position_size)
        self.volatility_factor = max(0.1, volatility_factor)
        self.confidence_factor = max(0.1, confidence_factor)
        
    def calculate_position_size(self, entry_price: float, stop_loss_price: float, 
                              volatility: float = None, signal_confidence: float = None, 
                              **kwargs) -> Tuple[float, float]:
        """
        Tính toán kích thước vị thế dựa trên mức rủi ro, điều chỉnh theo biến động và độ tin cậy.
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss_price (float): Giá dừng lỗ
            volatility (float, optional): Chỉ số biến động thị trường (0-1)
            signal_confidence (float, optional): Độ tin cậy của tín hiệu giao dịch (0-1)
            **kwargs: Tham số bổ sung
            
        Returns:
            Tuple[float, float]: (kích thước vị thế, phần trăm rủi ro thực tế)
        """
        # Tính kích thước vị thế cơ bản
        base_size, base_risk = super().calculate_position_size(entry_price, stop_loss_price)
        
        # Điều chỉnh theo biến động
        if volatility is not None:
            volatility = max(0.0, min(1.0, volatility))  # Đảm bảo trong khoảng 0-1
            volatility_multiplier = 1.0 / (1.0 + volatility * self.volatility_factor)
        else:
            volatility_multiplier = 1.0
            
        # Điều chỉnh theo độ tin cậy của tín hiệu
        if signal_confidence is not None:
            signal_confidence = max(0.0, min(1.0, signal_confidence))  # Đảm bảo trong khoảng 0-1
            confidence_multiplier = signal_confidence * self.confidence_factor
        else:
            confidence_multiplier = 1.0
            
        # Tính kích thước vị thế điều chỉnh
        adjusted_size = base_size * volatility_multiplier * confidence_multiplier
        
        # Đảm bảo kích thước tối thiểu
        adjusted_size = max(self.min_position_size, adjusted_size)
        
        # Tính phần trăm rủi ro điều chỉnh
        if entry_price > stop_loss_price:  # Long position
            risk_per_unit = (entry_price - stop_loss_price) / entry_price
        else:  # Short position
            risk_per_unit = (stop_loss_price - entry_price) / entry_price
            
        risk_per_unit = max(risk_per_unit, 0.001)  # Tối thiểu 0.1%
        actual_risk_pct = (adjusted_size * entry_price * risk_per_unit) / self.account_balance * 100
        actual_risk_pct = min(actual_risk_pct, self.max_risk_pct)  # Giới hạn theo max_risk_pct
        
        logger.debug(f"Dynamic position size: {adjusted_size:.6f}, risk: {actual_risk_pct:.2f}%")
        return adjusted_size, actual_risk_pct


class KellyCriterionSizer(BasePositionSizer):
    """Lớp tính toán kích thước vị thế dựa trên công thức Kelly Criterion"""
    
    def __init__(self, account_balance: float, win_rate: float = 0.5, 
                avg_win_loss_ratio: float = 1.0, max_risk_pct: float = 5.0,
                kelly_fraction: float = 1.0, leverage: int = 1, 
                min_position_size: float = 0.0):
        """
        Khởi tạo Kelly Criterion Position Sizer.
        
        Args:
            account_balance (float): Số dư tài khoản
            win_rate (float): Tỷ lệ thắng kỳ vọng (0-1)
            avg_win_loss_ratio (float): Tỷ lệ lợi nhuận trung bình / thua lỗ trung bình
            max_risk_pct (float): Phần trăm rủi ro tối đa trên mỗi giao dịch (%)
            kelly_fraction (float): Phần công thức Kelly sử dụng (0-1) - 0.5 = "Half Kelly"
            leverage (int): Đòn bẩy
            min_position_size (float): Kích thước vị thế tối thiểu
        """
        super().__init__(account_balance, max_risk_pct, leverage, min_position_size)
        self.win_rate = max(0.01, min(0.99, win_rate))  # Giới hạn 1%-99%
        self.avg_win_loss_ratio = max(0.1, avg_win_loss_ratio)
        self.kelly_fraction = max(0.1, min(1.0, kelly_fraction))  # Giới hạn 10%-100%
        
    def calculate_position_size(self, entry_price: float, stop_loss_price: float, 
                              take_profit_price: float = None, **kwargs) -> Tuple[float, float]:
        """
        Tính toán kích thước vị thế dựa trên công thức Kelly Criterion.
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss_price (float): Giá dừng lỗ
            take_profit_price (float, optional): Giá chốt lời
            **kwargs: Tham số bổ sung
            
        Returns:
            Tuple[float, float]: (kích thước vị thế, phần trăm rủi ro thực tế)
        """
        # Validate input
        if entry_price <= 0 or stop_loss_price <= 0:
            logger.warning(f"Invalid prices: entry={entry_price}, stop_loss={stop_loss_price}")
            return 0.0, 0.0
            
        # Tính tỷ lệ R (risk/reward) dựa trên giá chốt lời và dừng lỗ
        if take_profit_price is not None and take_profit_price > 0:
            if entry_price > stop_loss_price:  # Long position
                win_amount = take_profit_price - entry_price
                loss_amount = entry_price - stop_loss_price
            else:  # Short position
                win_amount = entry_price - take_profit_price
                loss_amount = stop_loss_price - entry_price
                
            if loss_amount <= 0:
                logger.warning("Invalid stop loss (no risk)")
                return 0.0, 0.0
                
            current_rr_ratio = win_amount / loss_amount
        else:
            # Sử dụng tỷ lệ trung bình nếu không có take_profit
            current_rr_ratio = self.avg_win_loss_ratio
            
        # Tính Kelly percentage
        kelly_pct = (self.win_rate * (current_rr_ratio + 1) - 1) / current_rr_ratio
        
        # Nếu Kelly âm, có nghĩa là kỳ vọng âm, không nên giao dịch
        if kelly_pct <= 0:
            logger.info("Kelly Criterion suggests not to trade (negative expectancy)")
            return 0.0, 0.0
            
        # Áp dụng Kelly fraction
        kelly_pct = kelly_pct * self.kelly_fraction
        
        # Giới hạn theo max_risk_pct
        kelly_pct = min(kelly_pct, self.max_risk_pct / 100)
        
        # Tính kích thước vị thế
        # Tính risk per unit (phần trăm)
        if entry_price > stop_loss_price:  # Long position
            risk_per_unit = (entry_price - stop_loss_price) / entry_price
        else:  # Short position
            risk_per_unit = (stop_loss_price - entry_price) / entry_price
            
        risk_per_unit = max(risk_per_unit, 0.001)  # Tối thiểu 0.1%
        
        # Tính position size
        position_value = self.account_balance * kelly_pct
        position_size = position_value / entry_price
        
        # Điều chỉnh theo risk per unit thực tế
        max_position_size = (self.account_balance * self.max_risk_pct / 100) / (entry_price * risk_per_unit)
        position_size = min(position_size, max_position_size)
        
        # Điều chỉnh cho đòn bẩy
        position_size = position_size * self.leverage
        
        # Đảm bảo kích thước tối thiểu
        position_size = max(self.min_position_size, position_size)
        
        # Tính phần trăm rủi ro thực tế
        actual_risk_pct = (position_size * entry_price * risk_per_unit) / self.account_balance * 100
        
        logger.debug(f"Kelly position size: {position_size:.6f}, risk: {actual_risk_pct:.2f}%, " +
                   f"Kelly: {kelly_pct*100:.2f}%")
        return position_size, actual_risk_pct


class AntiMartingaleSizer(BasePositionSizer):
    """
    Lớp tính toán kích thước vị thế theo Anti-Martingale
    Tăng kích thước vị thế sau mỗi lần thắng, reset sau khi thua
    """
    
    def __init__(self, account_balance: float, max_risk_pct: float = 2.0, 
                base_unit_pct: float = 1.0, increase_factor: float = 1.5,
                max_units: int = 4, leverage: int = 1, min_position_size: float = 0.0):
        """
        Khởi tạo Anti-Martingale Position Sizer.
        
        Args:
            account_balance (float): Số dư tài khoản
            max_risk_pct (float): Phần trăm rủi ro tối đa trên mỗi giao dịch (%)
            base_unit_pct (float): Phần trăm rủi ro của đơn vị cơ bản (%)
            increase_factor (float): Hệ số tăng kích thước sau mỗi lần thắng
            max_units (int): Số đơn vị tối đa cho phép
            leverage (int): Đòn bẩy
            min_position_size (float): Kích thước vị thế tối thiểu
        """
        super().__init__(account_balance, max_risk_pct, leverage, min_position_size)
        self.base_unit_pct = max(0.1, min(base_unit_pct, max_risk_pct))
        self.increase_factor = max(1.0, increase_factor)
        self.max_units = max(1, max_units)
        self.current_units = 1  # Bắt đầu với 1 đơn vị
        self.consecutive_wins = 0
        
    def calculate_position_size(self, entry_price: float, stop_loss_price: float, 
                              **kwargs) -> Tuple[float, float]:
        """
        Tính toán kích thước vị thế dựa trên Anti-Martingale.
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss_price (float): Giá dừng lỗ
            **kwargs: Tham số bổ sung
            
        Returns:
            Tuple[float, float]: (kích thước vị thế, phần trăm rủi ro thực tế)
        """
        # Tính kích thước đơn vị cơ bản
        base_position_sizer = BasePositionSizer(
            self.account_balance, self.base_unit_pct, self.leverage, self.min_position_size
        )
        base_size, base_risk = base_position_sizer.calculate_position_size(entry_price, stop_loss_price)
        
        # Tính số đơn vị hiện tại dựa trên chuỗi thắng
        current_units = min(self.current_units, self.max_units)
        
        # Tính kích thước vị thế theo Anti-Martingale
        position_size = base_size * current_units
        
        # Tính phần trăm rủi ro thực tế
        if entry_price > stop_loss_price:  # Long position
            risk_per_unit = (entry_price - stop_loss_price) / entry_price
        else:  # Short position
            risk_per_unit = (stop_loss_price - entry_price) / entry_price
            
        risk_per_unit = max(risk_per_unit, 0.001)  # Tối thiểu 0.1%
        actual_risk_pct = (position_size * entry_price * risk_per_unit) / self.account_balance * 100
        
        # Đảm bảo không vượt quá max_risk_pct
        if actual_risk_pct > self.max_risk_pct:
            position_size = (self.account_balance * self.max_risk_pct / 100) / (entry_price * risk_per_unit)
            actual_risk_pct = self.max_risk_pct
            
        logger.debug(f"Anti-Martingale position size: {position_size:.6f}, units: {current_units}, " +
                   f"risk: {actual_risk_pct:.2f}%")
        return position_size, actual_risk_pct
        
    def update_after_trade(self, is_win: bool) -> None:
        """
        Cập nhật trạng thái sau một giao dịch.
        
        Args:
            is_win (bool): Giao dịch thắng hay thua
        """
        if is_win:
            # Tăng chuỗi thắng và số đơn vị
            self.consecutive_wins += 1
            self.current_units = self.current_units * self.increase_factor
        else:
            # Reset về đơn vị cơ bản sau khi thua
            self.consecutive_wins = 0
            self.current_units = 1
            
        logger.debug(f"Anti-Martingale update: is_win={is_win}, consecutive_wins={self.consecutive_wins}, " +
                   f"current_units={self.current_units}")


class PortfolioSizer:
    """Lớp quản lý phân bổ vốn trong danh mục đầu tư với phân tích tương quan"""
    
    def __init__(self, account_balance: float, max_portfolio_risk: float = 5.0, 
                max_symbol_risk: float = 2.0, max_correlated_exposure: float = 3.0,
                correlation_threshold: float = 0.7):
        """
        Khởi tạo Portfolio Sizer.
        
        Args:
            account_balance (float): Số dư tài khoản
            max_portfolio_risk (float): Phần trăm rủi ro tối đa cho toàn bộ danh mục (%)
            max_symbol_risk (float): Phần trăm rủi ro tối đa cho mỗi cặp tiền (%)
            max_correlated_exposure (float): Mức phơi nhiễm tương quan tối đa
            correlation_threshold (float): Ngưỡng tương quan để tính phơi nhiễm
        """
        self.account_balance = max(0.0, account_balance)
        self.max_portfolio_risk = max(1.0, min(max_portfolio_risk, 20.0))  # Giới hạn 1-20%
        self.max_symbol_risk = max(0.5, min(max_symbol_risk, 5.0))  # Giới hạn 0.5-5%
        self.max_correlated_exposure = max(1.0, max_correlated_exposure)
        self.correlation_threshold = max(0.5, min(correlation_threshold, 1.0))  # Giới hạn 0.5-1.0
        
        # Theo dõi các vị thế hiện tại
        self.current_positions = {}
        
    def calculate_position_allocations(self, symbols: List[str], 
                                     signals: Dict[str, Dict], 
                                     correlation_matrix: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        Tính toán phân bổ kích thước vị thế tối ưu cho danh mục đầu tư.
        
        Args:
            symbols (List[str]): Danh sách các cặp tiền
            signals (Dict[str, Dict]): Thông tin tín hiệu cho mỗi cặp
                {symbol: {'signal': 'buy'/'sell'/'neutral', 'strength': 0-1, 
                        'entry_price': float, 'stop_loss': float, ...}}
            correlation_matrix (Dict[str, Dict]): Ma trận tương quan giữa các cặp tiền
                {symbol1: {symbol1: 1.0, symbol2: 0.7, ...}, ...}
                
        Returns:
            Dict[str, Dict]: Thông tin phân bổ cho mỗi cặp tiền
                {symbol: {'position_size': float, 'position_value': float, 'risk_pct': float, ...}}
        """
        # Lọc các cặp có tín hiệu giao dịch (không phải neutral)
        tradable_symbols = [s for s in symbols if s in signals and 
                          signals[s].get('signal') in ['buy', 'sell']]
        
        if not tradable_symbols:
            logger.info("No tradable symbols with valid signals")
            return {}
            
        # Tính initial allocations không tính đến tương quan
        initial_allocations = {}
        total_risk = 0.0
        
        for symbol in tradable_symbols:
            signal = signals[symbol]
            
            # Lấy thông tin cần thiết
            entry_price = signal.get('entry_price', 0)
            stop_loss = signal.get('stop_loss', 0)
            signal_strength = signal.get('strength', 0.5)
            
            # Kiểm tra dữ liệu hợp lệ
            if entry_price <= 0 or stop_loss <= 0:
                logger.warning(f"Invalid prices for {symbol}: entry={entry_price}, stop={stop_loss}")
                continue
                
            # Tính risk_per_unit
            if signal['signal'] == 'buy':  # Long position
                risk_per_unit = (entry_price - stop_loss) / entry_price
            else:  # Short position
                risk_per_unit = (stop_loss - entry_price) / entry_price
                
            risk_per_unit = max(risk_per_unit, 0.001)  # Tối thiểu 0.1%
            
            # Phân bổ rủi ro dựa trên strength
            symbol_risk_pct = self.max_symbol_risk * signal_strength
            
            # Tính kích thước vị thế
            risk_amount = self.account_balance * (symbol_risk_pct / 100)
            position_size = risk_amount / (entry_price * risk_per_unit)
            
            # Lưu thông tin phân bổ
            initial_allocations[symbol] = {
                'position_size': position_size,
                'position_value': position_size * entry_price,
                'risk_amount': risk_amount,
                'risk_pct': symbol_risk_pct,
                'side': signal['signal'],
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'signal_strength': signal_strength
            }
            
            total_risk += symbol_risk_pct
            
        # Nếu tổng rủi ro vượt quá giới hạn danh mục, điều chỉnh tỷ lệ
        if total_risk > self.max_portfolio_risk:
            scaling_factor = self.max_portfolio_risk / total_risk
            
            for symbol in initial_allocations:
                initial_allocations[symbol]['position_size'] *= scaling_factor
                initial_allocations[symbol]['position_value'] *= scaling_factor
                initial_allocations[symbol]['risk_amount'] *= scaling_factor
                initial_allocations[symbol]['risk_pct'] *= scaling_factor
                
            logger.info(f"Scaled all positions by {scaling_factor:.2f} to meet portfolio risk limit")
            
        # Tiếp theo, kiểm tra và điều chỉnh phơi nhiễm tương quan
        final_allocations = self._adjust_for_correlation(initial_allocations, correlation_matrix)
        
        return final_allocations
        
    def _adjust_for_correlation(self, allocations: Dict[str, Dict], 
                              correlation_matrix: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        Điều chỉnh phân bổ dựa trên tương quan giữa các cặp tiền.
        
        Args:
            allocations (Dict[str, Dict]): Phân bổ ban đầu
            correlation_matrix (Dict[str, Dict]): Ma trận tương quan
            
        Returns:
            Dict[str, Dict]: Phân bổ sau khi điều chỉnh
        """
        if not allocations:
            return {}
            
        # Kiểm tra ma trận tương quan
        if not correlation_matrix:
            logger.warning("No correlation matrix provided, skipping correlation adjustment")
            return allocations
            
        # Tính exposure scores cho mỗi cặp và tìm các cặp có tương quan cao
        exposure_scores = {}
        correlations = {}
        
        for symbol1, alloc1 in allocations.items():
            exposure_scores[symbol1] = 1.0  # Bắt đầu với 1.0 (tự tương quan)
            correlations[symbol1] = {}
            
            for symbol2, alloc2 in allocations.items():
                if symbol1 == symbol2:
                    continue
                    
                # Tính correlation factor
                try:
                    if symbol1 in correlation_matrix and symbol2 in correlation_matrix[symbol1]:
                        corr = correlation_matrix[symbol1][symbol2]
                    elif symbol2 in correlation_matrix and symbol1 in correlation_matrix[symbol2]:
                        corr = correlation_matrix[symbol2][symbol1]
                    else:
                        logger.warning(f"No correlation data for {symbol1}-{symbol2}, assuming 0")
                        corr = 0.0
                except Exception as e:
                    logger.warning(f"Error getting correlation for {symbol1}-{symbol2}: {e}")
                    corr = 0.0
                    
                # Chỉ xét các correlation vượt ngưỡng
                if abs(corr) >= self.correlation_threshold:
                    # Kiểm tra xem các vị thế có cùng chiều không
                    same_direction = (alloc1['side'] == alloc2['side'])
                    
                    # Nếu tương quan dương và cùng chiều, hoặc tương quan âm và ngược chiều
                    # thì tăng exposure; ngược lại giảm exposure (vì sẽ hedged)
                    if (corr > 0 and same_direction) or (corr < 0 and not same_direction):
                        exposure_factor = abs(corr)
                    else:
                        exposure_factor = -abs(corr)  # Âm để thể hiện hedging
                        
                    correlations[symbol1][symbol2] = {
                        'correlation': corr,
                        'exposure_factor': exposure_factor,
                        'side1': alloc1['side'],
                        'side2': alloc2['side']
                    }
                    
                    # Cập nhật exposure score
                    exposure_scores[symbol1] += exposure_factor * alloc2['risk_pct'] / alloc1['risk_pct']
        
        # Điều chỉnh các vị thế có exposure_score vượt ngưỡng
        adjusted_allocations = allocations.copy()
        
        for symbol, score in exposure_scores.items():
            if score > self.max_correlated_exposure:
                # Tính tỷ lệ scale down
                scale_factor = self.max_correlated_exposure / score
                
                # Điều chỉnh phân bổ
                adjusted_allocations[symbol]['position_size'] *= scale_factor
                adjusted_allocations[symbol]['position_value'] *= scale_factor
                adjusted_allocations[symbol]['risk_amount'] *= scale_factor
                adjusted_allocations[symbol]['risk_pct'] *= scale_factor
                
                # Thêm thông tin correlation
                adjusted_allocations[symbol]['correlation_info'] = {
                    'exposure_score': score,
                    'scale_factor': scale_factor,
                    'correlations': correlations[symbol]
                }
                
                logger.info(f"Scaled {symbol} position by {scale_factor:.2f} due to high correlation exposure")
                
        return adjusted_allocations
        
    def update_account_balance(self, new_balance: float) -> None:
        """
        Cập nhật số dư tài khoản.
        
        Args:
            new_balance (float): Số dư tài khoản mới
        """
        self.account_balance = max(0.0, new_balance)
        logger.debug(f"Updated account balance: {self.account_balance}")


def create_position_sizer(sizer_type: str, account_balance: float, **kwargs) -> BasePositionSizer:
    """
    Factory function để tạo position sizer phù hợp.
    
    Args:
        sizer_type (str): Loại position sizer ('basic', 'dynamic', 'kelly', 'antimartingale', 'portfolio')
        account_balance (float): Số dư tài khoản
        **kwargs: Tham số bổ sung cho từng loại sizer
        
    Returns:
        BasePositionSizer: Đối tượng position sizer
    """
    if sizer_type.lower() == 'basic':
        return BasePositionSizer(account_balance, **kwargs)
    elif sizer_type.lower() == 'dynamic':
        return DynamicPositionSizer(account_balance, **kwargs)
    elif sizer_type.lower() == 'kelly':
        return KellyCriterionSizer(account_balance, **kwargs)
    elif sizer_type.lower() == 'antimartingale':
        return AntiMartingaleSizer(account_balance, **kwargs)
    elif sizer_type.lower() == 'portfolio':
        return PortfolioSizer(account_balance, **kwargs)
    else:
        logger.warning(f"Unknown position sizer type: {sizer_type}, falling back to basic")
        return BasePositionSizer(account_balance, **kwargs)


def main():
    """Hàm demo"""
    # Khởi tạo các position sizer
    account_balance = 10000
    
    # Basic position sizer
    basic_sizer = BasePositionSizer(account_balance)
    size, risk = basic_sizer.calculate_position_size(40000, 39000)
    print(f"Basic position sizer: size={size:.6f}, risk={risk:.2f}%")
    
    # Dynamic position sizer
    dynamic_sizer = DynamicPositionSizer(account_balance)
    size, risk = dynamic_sizer.calculate_position_size(40000, 39000, volatility=0.2, signal_confidence=0.8)
    print(f"Dynamic position sizer: size={size:.6f}, risk={risk:.2f}%")
    
    # Kelly Criterion sizer
    kelly_sizer = KellyCriterionSizer(account_balance, win_rate=0.6, avg_win_loss_ratio=2.0)
    size, risk = kelly_sizer.calculate_position_size(40000, 39000, take_profit_price=42000)
    print(f"Kelly position sizer: size={size:.6f}, risk={risk:.2f}%")
    
    # Anti-Martingale sizer
    anti_sizer = AntiMartingaleSizer(account_balance)
    for i in range(3):
        size, risk = anti_sizer.calculate_position_size(40000, 39000)
        print(f"Anti-Martingale (wins={i}): size={size:.6f}, risk={risk:.2f}%")
        anti_sizer.update_after_trade(True)  # Simulate win
    
    # After a loss
    anti_sizer.update_after_trade(False)  # Simulate loss
    size, risk = anti_sizer.calculate_position_size(40000, 39000)
    print(f"Anti-Martingale (after loss): size={size:.6f}, risk={risk:.2f}%")
    
    # Portfolio Sizer
    portfolio_sizer = PortfolioSizer(account_balance)
    correlation_matrix = {
        'BTCUSDT': {'BTCUSDT': 1.0, 'ETHUSDT': 0.8, 'SOLUSDT': 0.6},
        'ETHUSDT': {'BTCUSDT': 0.8, 'ETHUSDT': 1.0, 'SOLUSDT': 0.7},
        'SOLUSDT': {'BTCUSDT': 0.6, 'ETHUSDT': 0.7, 'SOLUSDT': 1.0}
    }
    
    signals = {
        'BTCUSDT': {'signal': 'buy', 'strength': 0.8, 'entry_price': 40000, 'stop_loss': 39000},
        'ETHUSDT': {'signal': 'buy', 'strength': 0.7, 'entry_price': 2500, 'stop_loss': 2400},
        'SOLUSDT': {'signal': 'sell', 'strength': 0.6, 'entry_price': 100, 'stop_loss': 105}
    }
    
    allocations = portfolio_sizer.calculate_position_allocations(
        ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'], signals, correlation_matrix
    )
    
    print("\nPortfolio allocations:")
    for symbol, allocation in allocations.items():
        print(f"{symbol}: size={allocation['position_size']:.6f}, " + 
            f"value=${allocation['position_value']:.2f}, risk={allocation['risk_pct']:.2f}%")

if __name__ == "__main__":
    main()