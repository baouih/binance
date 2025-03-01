"""
Module quản lý vốn (Position Sizing)

Module này cung cấp các phương pháp tính toán kích thước vị thế giao dịch dựa trên
nguyên tắc quản lý vốn khác nhau, với mục tiêu bảo vệ tài khoản và tối ưu hóa hiệu suất.
"""

import logging
import time
from typing import Dict, Tuple, List, Any, Optional, Union, Callable

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("position_sizing")

class BasePositionSizer:
    """Lớp cơ sở cho position sizing"""
    
    def __init__(self, account_balance, max_risk_pct=2.0, leverage=1, min_position_size=0.0):
        """
        Khởi tạo position sizer cơ bản
        
        Args:
            account_balance (float): Số dư tài khoản
            max_risk_pct (float): Phần trăm rủi ro tối đa trên mỗi giao dịch
            leverage (int): Đòn bẩy
            min_position_size (float): Kích thước vị thế tối thiểu
        """
        self.account_balance = account_balance
        self.max_risk_pct = max_risk_pct
        self.leverage = leverage
        self.min_position_size = min_position_size
        self.name = "Base Position Sizer"
        
    def calculate_position_size(self, entry_price, stop_loss_price, **kwargs):
        """
        Tính toán kích thước vị thế dựa trên quản lý rủi ro
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss_price (float): Giá dừng lỗ
            **kwargs: Tham số bổ sung
            
        Returns:
            Tuple[float, float]: (Kích thước vị thế, phần trăm rủi ro)
        """
        if entry_price <= 0:
            raise ValueError("Giá vào lệnh phải lớn hơn 0")
            
        if stop_loss_price <= 0:
            raise ValueError("Giá dừng lỗ phải lớn hơn 0")
            
        if entry_price == stop_loss_price:
            raise ValueError("Giá vào lệnh và giá dừng lỗ không được bằng nhau")
            
        # Tính toán phần trăm rủi ro trên mỗi đơn vị
        risk_per_unit = abs(entry_price - stop_loss_price) / entry_price
        
        # Số tiền rủi ro tối đa
        risk_amount = self.account_balance * (self.max_risk_pct / 100)
        
        # Kích thước vị thế
        position_size = risk_amount / (entry_price * risk_per_unit)
        position_size *= self.leverage
        
        return max(self.min_position_size, position_size), self.max_risk_pct
        
    def update_account_balance(self, new_balance):
        """
        Cập nhật số dư tài khoản
        
        Args:
            new_balance (float): Số dư tài khoản mới
        """
        self.account_balance = max(0.0, new_balance)
        
class DynamicPositionSizer(BasePositionSizer):
    """Lớp position sizing động dựa trên biến động và độ tin cậy"""
    
    def __init__(self, account_balance, max_risk_pct=2.0, leverage=1,
               volatility_factor=1.0, confidence_factor=1.0, min_position_size=0.0):
        """
        Khởi tạo position sizer động
        
        Args:
            account_balance (float): Số dư tài khoản
            max_risk_pct (float): Phần trăm rủi ro tối đa trên mỗi giao dịch
            leverage (int): Đòn bẩy
            volatility_factor (float): Hệ số biến động (càng cao thì giảm size càng nhiều khi biến động lớn)
            confidence_factor (float): Hệ số tin cậy (càng cao thì tăng size càng nhiều khi độ tin cậy cao)
            min_position_size (float): Kích thước vị thế tối thiểu
        """
        super().__init__(account_balance, max_risk_pct, leverage, min_position_size)
        self.volatility_factor = volatility_factor
        self.confidence_factor = confidence_factor
        self.name = "Dynamic Position Sizer"
        
    def calculate_position_size(self, entry_price, stop_loss_price, 
                              volatility=None, signal_confidence=None, **kwargs):
        """
        Tính toán kích thước vị thế có điều chỉnh theo biến động và độ tin cậy
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss_price (float): Giá dừng lỗ
            volatility (float, optional): Độ biến động thị trường (0-1)
            signal_confidence (float, optional): Độ tin cậy của tín hiệu (0-1)
            **kwargs: Tham số bổ sung
            
        Returns:
            Tuple[float, float]: (Kích thước vị thế, phần trăm rủi ro)
        """
        base_size, base_risk = super().calculate_position_size(entry_price, stop_loss_price)
        
        # Điều chỉnh dựa trên biến động và độ tin cậy
        volatility_multiplier = 1.0
        confidence_multiplier = 1.0
        
        if volatility is not None:
            volatility = max(0.0, min(1.0, volatility))  # Đảm bảo giá trị trong [0,1]
            volatility_multiplier = 1.0 / (1.0 + volatility * self.volatility_factor)
            
        if signal_confidence is not None:
            signal_confidence = max(0.0, min(1.0, signal_confidence))  # Đảm bảo giá trị trong [0,1]
            confidence_multiplier = signal_confidence * self.confidence_factor
            
        # Tính kích thước cuối cùng
        adjusted_size = base_size * volatility_multiplier * confidence_multiplier
        
        return max(self.min_position_size, adjusted_size), base_risk
        
class KellyCriterionSizer(BasePositionSizer):
    """Lớp position sizing dựa trên công thức Kelly Criterion"""
    
    def __init__(self, account_balance, win_rate=0.5, avg_win_loss_ratio=1.0, 
               max_risk_pct=5.0, kelly_fraction=1.0, leverage=1, min_position_size=0.0):
        """
        Khởi tạo position sizer dựa trên Kelly Criterion
        
        Args:
            account_balance (float): Số dư tài khoản
            win_rate (float): Tỷ lệ thắng (0-1)
            avg_win_loss_ratio (float): Tỷ lệ thắng/thua trung bình
            max_risk_pct (float): Phần trăm rủi ro tối đa trên mỗi giao dịch
            kelly_fraction (float): Phần Kelly sử dụng (0-1, thường 0.5 hoặc 0.25)
            leverage (int): Đòn bẩy
            min_position_size (float): Kích thước vị thế tối thiểu
        """
        super().__init__(account_balance, max_risk_pct, leverage, min_position_size)
        self.win_rate = win_rate
        self.avg_win_loss_ratio = avg_win_loss_ratio
        self.kelly_fraction = kelly_fraction
        self.name = "Kelly Criterion Sizer"
        
    def calculate_position_size(self, entry_price, stop_loss_price, take_profit_price=None, **kwargs):
        """
        Tính toán kích thước vị thế dựa trên công thức Kelly
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss_price (float): Giá dừng lỗ
            take_profit_price (float, optional): Giá chốt lời
            **kwargs: Tham số bổ sung
            
        Returns:
            Tuple[float, float]: (Kích thước vị thế, phần trăm rủi ro)
        """
        if entry_price <= 0:
            raise ValueError("Giá vào lệnh phải lớn hơn 0")
            
        if stop_loss_price <= 0:
            raise ValueError("Giá dừng lỗ phải lớn hơn 0")
            
        if entry_price == stop_loss_price:
            raise ValueError("Giá vào lệnh và giá dừng lỗ không được bằng nhau")
            
        # Tính toán tỷ lệ thắng/thua dựa trên giá nếu có
        if take_profit_price is not None:
            if entry_price > stop_loss_price:  # Long
                win_amount = take_profit_price - entry_price
                loss_amount = entry_price - stop_loss_price
            else:  # Short
                win_amount = entry_price - take_profit_price
                loss_amount = stop_loss_price - entry_price
                
            current_rr_ratio = win_amount / loss_amount if loss_amount > 0 else self.avg_win_loss_ratio
        else:
            current_rr_ratio = self.avg_win_loss_ratio
            
        # Áp dụng công thức Kelly
        # f* = (p*r - q)/r where p = win rate, q = 1-p, r = win/loss ratio
        kelly_pct = (self.win_rate * current_rr_ratio - (1 - self.win_rate)) / current_rr_ratio
        
        # Giới hạn kết quả âm
        kelly_pct = max(0, kelly_pct)
        
        # Áp dụng hệ số Kelly (thường là 0.5 hoặc 0.25 của Kelly đầy đủ)
        kelly_pct = kelly_pct * self.kelly_fraction
        
        # Giới hạn theo max_risk_pct
        kelly_pct = min(kelly_pct, self.max_risk_pct / 100)
        
        # Tính kích thước vị thế
        position_value = self.account_balance * kelly_pct
        position_size = position_value / entry_price * self.leverage
        
        return max(self.min_position_size, position_size), kelly_pct * 100
        
class AntiMartingaleSizer(BasePositionSizer):
    """Lớp position sizing tăng kích thước sau khi thắng"""
    
    def __init__(self, account_balance, max_risk_pct=2.0, base_unit_pct=1.0, 
               increase_factor=1.5, max_units=4, leverage=1, min_position_size=0.0):
        """
        Khởi tạo Anti-Martingale Position Sizer
        
        Args:
            account_balance (float): Số dư tài khoản
            max_risk_pct (float): Phần trăm rủi ro tối đa trên mỗi giao dịch
            base_unit_pct (float): Phần trăm rủi ro cho đơn vị cơ bản
            increase_factor (float): Hệ số tăng sau mỗi lần thắng
            max_units (int): Số đơn vị tối đa
            leverage (int): Đòn bẩy
            min_position_size (float): Kích thước vị thế tối thiểu
        """
        super().__init__(account_balance, max_risk_pct, leverage, min_position_size)
        self.base_unit_pct = base_unit_pct
        self.increase_factor = increase_factor
        self.max_units = max_units
        self.current_units = 1
        self.consecutive_wins = 0
        self.name = "Anti-Martingale Sizer"
        
    def calculate_position_size(self, entry_price, stop_loss_price, **kwargs):
        """
        Tính toán kích thước vị thế tăng dần sau mỗi lần thắng
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss_price (float): Giá dừng lỗ
            **kwargs: Tham số bổ sung
            
        Returns:
            Tuple[float, float]: (Kích thước vị thế, phần trăm rủi ro)
        """
        # Sử dụng base sizer với base_unit_pct
        base_sizer = BasePositionSizer(
            self.account_balance, self.base_unit_pct, self.leverage, self.min_position_size
        )
        base_size, base_risk = base_sizer.calculate_position_size(entry_price, stop_loss_price)
        
        # Giới hạn số đơn vị
        current_units = min(self.current_units, self.max_units)
        position_size = base_size * current_units
        
        # Tính toán rủi ro thực tế
        actual_risk = base_risk * current_units
        
        # Giới hạn rủi ro tối đa
        if actual_risk > self.max_risk_pct:
            scaling_factor = self.max_risk_pct / actual_risk
            position_size *= scaling_factor
            actual_risk = self.max_risk_pct
        
        return max(self.min_position_size, position_size), actual_risk
        
    def update_after_trade(self, is_win):
        """
        Cập nhật số đơn vị sau một giao dịch
        
        Args:
            is_win (bool): True nếu giao dịch thắng, False nếu thua
        """
        if is_win:
            self.consecutive_wins += 1
            self.current_units = self.current_units * self.increase_factor
        else:
            self.consecutive_wins = 0
            self.current_units = 1
            
class PortfolioSizer:
    """Lớp quản lý vốn dựa trên danh mục đầu tư"""
    
    def __init__(self, account_balance, max_portfolio_risk=5.0, max_symbol_risk=2.0,
               max_correlated_exposure=3.0, correlation_threshold=0.7):
        """
        Khởi tạo Portfolio Sizer
        
        Args:
            account_balance (float): Số dư tài khoản
            max_portfolio_risk (float): Rủi ro tối đa cho toàn bộ danh mục
            max_symbol_risk (float): Rủi ro tối đa cho một mã
            max_correlated_exposure (float): Mức độ phơi nhiễm tương quan tối đa
            correlation_threshold (float): Ngưỡng tương quan đáng kể
        """
        self.account_balance = account_balance
        self.max_portfolio_risk = max_portfolio_risk
        self.max_symbol_risk = max_symbol_risk
        self.max_correlated_exposure = max_correlated_exposure
        self.correlation_threshold = correlation_threshold
        self.current_positions = {}
        self.name = "Portfolio Sizer"
        
    def calculate_position_allocations(self, symbols, signals, correlation_matrix):
        """
        Tính toán phân bổ vốn cho danh mục đầu tư
        
        Args:
            symbols (List[str]): Danh sách các mã
            signals (Dict): Tín hiệu giao dịch cho mỗi mã
            correlation_matrix (Dict): Ma trận tương quan giữa các mã
            
        Returns:
            Dict: Phân bổ vốn cho mỗi mã
        """
        allocations = {}
        
        for symbol in symbols:
            if symbol not in signals or signals[symbol].get('signal') not in ['buy', 'sell']:
                continue
                
            signal = signals[symbol]
            entry_price = signal.get('entry_price', 0)
            stop_loss = signal.get('stop_loss', 0)
            signal_strength = signal.get('strength', 0.5)
            
            if entry_price <= 0 or stop_loss <= 0:
                continue
                
            # Tính toán rủi ro cho mã này
            symbol_risk_pct = self.max_symbol_risk * signal_strength
            risk_amount = self.account_balance * (symbol_risk_pct / 100)
            
            # Tính toán kích thước vị thế
            if signal['signal'] == 'buy':  # Long
                risk_per_unit = (entry_price - stop_loss) / entry_price
            else:  # Short
                risk_per_unit = (stop_loss - entry_price) / entry_price
                
            # Đảm bảo không chia cho 0
            risk_per_unit = max(risk_per_unit, 0.001)
            position_size = risk_amount / (entry_price * risk_per_unit)
            
            # Tính toán phơi nhiễm tương quan
            exposure_info = self._calculate_correlation_exposure(
                symbol, 
                signal['signal'], 
                position_size * entry_price,
                correlation_matrix
            )
            
            # Điều chỉnh kích thước nếu phơi nhiễm quá lớn
            scale_factor = 1.0
            if exposure_info['exposure_ratio'] > self.max_correlated_exposure:
                scale_factor = self.max_correlated_exposure / exposure_info['exposure_ratio']
                
            # Cập nhật phân bổ
            allocations[symbol] = {
                'position_size': position_size * scale_factor,
                'position_value': position_size * entry_price * scale_factor,
                'risk_amount': risk_amount * scale_factor,
                'risk_pct': symbol_risk_pct * scale_factor,
                'side': signal['signal'],
                'correlation_info': {
                    'exposure_ratio': exposure_info['exposure_ratio'],
                    'scale_factor': scale_factor,
                    'correlated_with': exposure_info.get('correlated_with', [])
                }
            }
            
        # Kiểm tra và điều chỉnh rủi ro tổng thể của danh mục
        total_risk = sum(alloc['risk_pct'] for alloc in allocations.values())
        if total_risk > self.max_portfolio_risk:
            scaling_factor = self.max_portfolio_risk / total_risk
            for symbol in allocations:
                allocations[symbol]['position_size'] *= scaling_factor
                allocations[symbol]['position_value'] *= scaling_factor
                allocations[symbol]['risk_amount'] *= scaling_factor
                allocations[symbol]['risk_pct'] *= scaling_factor
                
        return allocations
        
    def _calculate_correlation_exposure(self, symbol, side, position_value, correlation_matrix):
        """
        Tính toán mức độ phơi nhiễm do tương quan
        
        Args:
            symbol (str): Mã cần kiểm tra
            side (str): Hướng giao dịch
            position_value (float): Giá trị vị thế
            correlation_matrix (Dict): Ma trận tương quan
            
        Returns:
            Dict: Thông tin về mức độ phơi nhiễm
        """
        exposure_ratio = 1.0  # Mức cơ bản
        correlated_with = []
        
        # Kiểm tra tương quan với các vị thế đang có
        for other_symbol, pos in self.current_positions.items():
            if other_symbol == symbol:
                continue
                
            # Lấy độ tương quan giữa hai mã
            correlation = self._get_correlation(symbol, other_symbol, correlation_matrix)
            
            # Chỉ xét các mã có tương quan đáng kể
            if abs(correlation) >= self.correlation_threshold:
                # Kiểm tra hướng giao dịch
                same_direction = (side == pos['side'])
                
                # Tính mức phơi nhiễm
                # Nếu tương quan dương và cùng hướng, phơi nhiễm tăng
                # Nếu tương quan âm và ngược hướng, phơi nhiễm tăng
                if (correlation > 0 and same_direction) or (correlation < 0 and not same_direction):
                    exposure_ratio += abs(correlation) * 0.5
                    correlated_with.append({
                        'symbol': other_symbol,
                        'correlation': correlation,
                        'side': pos['side'],
                        'impact': abs(correlation) * 0.5
                    })
                    
        return {
            'exposure_ratio': exposure_ratio,
            'is_acceptable': exposure_ratio <= self.max_correlated_exposure,
            'correlated_with': correlated_with
        }
        
    def _get_correlation(self, symbol1, symbol2, correlation_matrix):
        """
        Lấy độ tương quan giữa hai mã
        
        Args:
            symbol1 (str): Mã thứ nhất
            symbol2 (str): Mã thứ hai
            correlation_matrix (Dict): Ma trận tương quan
            
        Returns:
            float: Độ tương quan (-1 đến 1)
        """
        if symbol1 == symbol2:
            return 1.0
            
        if symbol1 in correlation_matrix and symbol2 in correlation_matrix[symbol1]:
            return correlation_matrix[symbol1][symbol2]
            
        if symbol2 in correlation_matrix and symbol1 in correlation_matrix[symbol2]:
            return correlation_matrix[symbol2][symbol1]
            
        return 0.0
        
    def update_account_balance(self, new_balance):
        """
        Cập nhật số dư tài khoản
        
        Args:
            new_balance (float): Số dư tài khoản mới
        """
        self.account_balance = max(0.0, new_balance)
        
    def update_position(self, symbol, side, position_size, position_value):
        """
        Cập nhật thông tin vị thế hiện tại
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng giao dịch
            position_size (float): Kích thước vị thế
            position_value (float): Giá trị vị thế
        """
        self.current_positions[symbol] = {
            'side': side,
            'position_size': position_size,
            'position_value': position_value
        }
        
    def remove_position(self, symbol):
        """
        Xóa vị thế
        
        Args:
            symbol (str): Mã cần xóa vị thế
            
        Returns:
            bool: True nếu xóa thành công, False nếu không tìm thấy
        """
        if symbol in self.current_positions:
            del self.current_positions[symbol]
            return True
        return False
        
def create_position_sizer(sizer_type, account_balance, **kwargs):
    """
    Factory function tạo position sizer theo loại
    
    Args:
        sizer_type (str): Loại position sizer
        account_balance (float): Số dư tài khoản
        **kwargs: Tham số bổ sung
        
    Returns:
        Any: Đối tượng position sizer
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
        logger.warning(f"Không tìm thấy position sizer: {sizer_type}, sử dụng basic")
        return BasePositionSizer(account_balance, **kwargs)

# Demo nếu chạy trực tiếp
if __name__ == "__main__":
    # Ví dụ sử dụng
    account_balance = 10000
    entry_price = 40000
    stop_loss = 39000
    take_profit = 42000
    
    # Test base sizer
    base_sizer = BasePositionSizer(account_balance)
    size, risk = base_sizer.calculate_position_size(entry_price, stop_loss)
    print(f"Base Sizer: size={size:.6f}, risk={risk:.2f}%")
    
    # Test Kelly sizer
    kelly_sizer = KellyCriterionSizer(account_balance, win_rate=0.6, avg_win_loss_ratio=2.0)
    size, risk = kelly_sizer.calculate_position_size(entry_price, stop_loss, take_profit_price=take_profit)
    print(f"Kelly Sizer: size={size:.6f}, risk={risk:.2f}%")
    
    # Test Dynamic sizer
    dynamic_sizer = DynamicPositionSizer(account_balance)
    size, risk = dynamic_sizer.calculate_position_size(entry_price, stop_loss, volatility=0.5, signal_confidence=0.8)
    print(f"Dynamic Sizer: size={size:.6f}, risk={risk:.2f}%")