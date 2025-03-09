"""
Module định kích thước vị thế (Position Sizing)

Module này cung cấp các phương pháp khác nhau để tính toán kích thước vị thế
dựa trên quản lý vốn và quản lý rủi ro, giúp tối ưu hóa hiệu suất giao dịch.
"""

import logging
import math
import numpy as np
from typing import Dict, List, Any, Optional, Union, Callable

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("position_sizing")

class BasePositionSizer:
    """Lớp cơ sở cho tất cả các position sizer"""
    
    def __init__(self, account_balance: float, risk_percentage: float = 1.0):
        """
        Khởi tạo position sizer cơ bản
        
        Args:
            account_balance (float): Số dư tài khoản
            risk_percentage (float): Phần trăm rủi ro trên mỗi giao dịch
        """
        self.account_balance = account_balance
        self.risk_percentage = risk_percentage
        self.name = "Base Position Sizer"
        self.trade_history = []
        
    def calculate_position_size(self, current_price: float, account_balance: float = None, 
                             leverage: int = 1, volatility: float = None, market_data: Dict = None,
                             entry_price: float = None, stop_loss_price: float = None) -> float:
        """
        Tính toán kích thước vị thế
        
        Args:
            current_price (float): Giá hiện tại
            account_balance (float, optional): Số dư tài khoản (nếu None, sử dụng số dư của đối tượng)
            leverage (int): Đòn bẩy
            volatility (float, optional): Độ biến động (thường là giá trị ATR)
            market_data (Dict, optional): Dữ liệu thị trường bổ sung
            entry_price (float, optional): Giá vào lệnh
            stop_loss_price (float, optional): Giá stop loss
            
        Returns:
            float: Kích thước vị thế (tính bằng base currency)
        """
        # Sử dụng số dư tài khoản đã cho hoặc số dư mặc định
        balance = account_balance if account_balance is not None else self.account_balance
        
        # Tính số tiền rủi ro
        risk_amount = balance * (self.risk_percentage / 100)
        
        # Tính kích thước vị thế cơ bản
        position_size = risk_amount
        
        return position_size
    
    def update_balance(self, new_balance: float) -> None:
        """
        Cập nhật số dư tài khoản
        
        Args:
            new_balance (float): Số dư mới
        """
        self.account_balance = new_balance
        
    def update_risk_percentage(self, new_percentage: float) -> None:
        """
        Cập nhật phần trăm rủi ro
        
        Args:
            new_percentage (float): Phần trăm rủi ro mới
        """
        self.risk_percentage = new_percentage
        
    def update_trade_result(self, trade_result: Dict) -> None:
        """
        Cập nhật kết quả giao dịch vào lịch sử
        
        Args:
            trade_result (Dict): Kết quả giao dịch
        """
        self.trade_history.append(trade_result)
        
    def get_trade_history(self) -> List[Dict]:
        """
        Lấy lịch sử giao dịch
        
        Returns:
            List[Dict]: Lịch sử giao dịch
        """
        return self.trade_history

class FixedPositionSizer(BasePositionSizer):
    """Position sizer sử dụng số tiền cố định cho mỗi giao dịch"""
    
    def __init__(self, account_balance: float, fixed_amount: float = None, 
              risk_percentage: float = 1.0):
        """
        Khởi tạo Fixed Position Sizer
        
        Args:
            account_balance (float): Số dư tài khoản
            fixed_amount (float, optional): Số tiền cố định cho mỗi giao dịch
            risk_percentage (float): Phần trăm số dư sử dụng nếu fixed_amount không được cung cấp
        """
        super().__init__(account_balance, risk_percentage)
        self.fixed_amount = fixed_amount
        self.name = "Fixed Position Sizer"
        
    def calculate_position_size(self, current_price: float, account_balance: float = None, 
                             leverage: int = 1, volatility: float = None, market_data: Dict = None,
                             entry_price: float = None, stop_loss_price: float = None) -> float:
        """
        Tính toán kích thước vị thế
        
        Args:
            current_price (float): Giá hiện tại
            account_balance (float, optional): Số dư tài khoản
            leverage (int): Đòn bẩy
            volatility (float, optional): Độ biến động
            market_data (Dict, optional): Dữ liệu thị trường bổ sung
            entry_price (float, optional): Giá vào lệnh
            stop_loss_price (float, optional): Giá stop loss
            
        Returns:
            float: Kích thước vị thế (tính bằng quote currency)
        """
        # Sử dụng số dư tài khoản đã cho hoặc số dư mặc định
        balance = account_balance if account_balance is not None else self.account_balance
        
        # Tính số tiền rủi ro
        if self.fixed_amount is not None:
            risk_amount = min(self.fixed_amount, balance)
        else:
            risk_amount = balance * (self.risk_percentage / 100)
        
        # Tính kích thước vị thế (áp dụng đòn bẩy)
        position_size = risk_amount * leverage
        
        return position_size

class DynamicPositionSizer(BasePositionSizer):
    """Position sizer điều chỉnh kích thước vị thế dựa trên biến động thị trường"""
    
    def __init__(self, account_balance: float, risk_percentage: float = 1.0, 
              atr_multiplier: float = 2.0):
        """
        Khởi tạo Dynamic Position Sizer
        
        Args:
            account_balance (float): Số dư tài khoản
            risk_percentage (float): Phần trăm rủi ro trên mỗi giao dịch
            atr_multiplier (float): Hệ số nhân với ATR để tính khoảng cách stop loss
        """
        super().__init__(account_balance, risk_percentage)
        self.atr_multiplier = atr_multiplier
        self.name = "Dynamic Position Sizer"
        
    def calculate_position_size(self, current_price: float, account_balance: float = None, 
                             leverage: int = 1, volatility: float = None, market_data: Dict = None,
                             entry_price: float = None, stop_loss_price: float = None) -> float:
        """
        Tính toán kích thước vị thế dựa trên biến động
        
        Args:
            current_price (float): Giá hiện tại
            account_balance (float, optional): Số dư tài khoản
            leverage (int): Đòn bẩy
            volatility (float, optional): Độ biến động (giá trị ATR)
            market_data (Dict, optional): Dữ liệu thị trường bổ sung
            entry_price (float, optional): Giá vào lệnh
            stop_loss_price (float, optional): Giá stop loss
            
        Returns:
            float: Kích thước vị thế (tính bằng quote currency)
        """
        # Sử dụng số dư tài khoản đã cho hoặc số dư mặc định
        balance = account_balance if account_balance is not None else self.account_balance
        
        # Tính số tiền rủi ro
        risk_amount = balance * (self.risk_percentage / 100)
        
        # Nếu có stop loss hoặc SL tự tính dựa trên ATR
        if stop_loss_price is not None and entry_price is not None:
            # Tính khoảng cách stop loss
            stop_distance = abs(entry_price - stop_loss_price)
            
            # Tránh chia cho 0
            if stop_distance > 0:
                # Kích thước vị thế = Số tiền rủi ro / Khoảng cách stop loss
                position_size = risk_amount / (stop_distance / entry_price)
            else:
                position_size = risk_amount
            
        elif volatility is not None and volatility > 0:
            # Tính khoảng cách stop loss dựa trên ATR
            stop_distance = volatility * self.atr_multiplier
            
            # Tránh chia cho 0
            if stop_distance > 0:
                # Kích thước vị thế = Số tiền rủi ro / Khoảng cách stop loss
                position_size = risk_amount / (stop_distance / current_price)
            else:
                position_size = risk_amount
                
        else:
            # Mặc định nếu không có thông tin về volatility
            position_size = risk_amount
        
        # Áp dụng đòn bẩy
        position_size = position_size * leverage
        
        return position_size
    
    def update_atr_multiplier(self, new_multiplier: float) -> None:
        """
        Cập nhật hệ số nhân ATR
        
        Args:
            new_multiplier (float): Hệ số nhân mới
        """
        self.atr_multiplier = new_multiplier

class KellyCriterionSizer(BasePositionSizer):
    """Position sizer sử dụng công thức Kelly Criterion"""
    
    def __init__(self, account_balance: float, win_rate: float = 0.5, 
              win_loss_ratio: float = 2.0, max_risk_percentage: float = 5.0,
              kelly_fraction: float = 0.5):
        """
        Khởi tạo Kelly Criterion Sizer
        
        Args:
            account_balance (float): Số dư tài khoản
            win_rate (float): Tỷ lệ thắng (0-1)
            win_loss_ratio (float): Tỷ lệ lợi nhuận trung bình / thua lỗ trung bình
            max_risk_percentage (float): Phần trăm rủi ro tối đa
            kelly_fraction (float): Phần của Kelly formula (0-1)
        """
        super().__init__(account_balance, 0)  # Risk percentage sẽ được tính bởi Kelly
        self.win_rate = win_rate
        self.win_loss_ratio = win_loss_ratio
        self.max_risk_percentage = max_risk_percentage
        self.kelly_fraction = kelly_fraction
        self.name = "Kelly Criterion Sizer"
        
    def calculate_position_size(self, current_price: float, account_balance: float = None, 
                             leverage: int = 1, volatility: float = None, market_data: Dict = None,
                             entry_price: float = None, stop_loss_price: float = None) -> float:
        """
        Tính toán kích thước vị thế sử dụng Kelly Criterion
        
        Args:
            current_price (float): Giá hiện tại
            account_balance (float, optional): Số dư tài khoản
            leverage (int): Đòn bẩy
            volatility (float, optional): Độ biến động
            market_data (Dict, optional): Dữ liệu thị trường bổ sung
            entry_price (float, optional): Giá vào lệnh
            stop_loss_price (float, optional): Giá stop loss
            
        Returns:
            float: Kích thước vị thế (tính bằng quote currency)
        """
        # Sử dụng số dư tài khoản đã cho hoặc số dư mặc định
        balance = account_balance if account_balance is not None else self.account_balance
        
        # Cập nhật win_rate và win_loss_ratio từ lịch sử nếu có đủ dữ liệu
        if len(self.trade_history) >= 10:
            self._update_metrics_from_history()
        
        # Tính Kelly percentage
        kelly_pct = (self.win_rate * self.win_loss_ratio - (1 - self.win_rate)) / self.win_loss_ratio
        
        # Áp dụng fraction và giới hạn tối đa
        kelly_pct = kelly_pct * self.kelly_fraction
        kelly_pct = min(kelly_pct, self.max_risk_percentage / 100)
        
        # Nếu Kelly âm, sử dụng giá trị nhỏ nhất
        kelly_pct = max(kelly_pct, 0.001)  # Tối thiểu 0.1%
        
        # Tính số tiền rủi ro
        risk_amount = balance * kelly_pct
        
        # Nếu có stop loss
        if stop_loss_price is not None and entry_price is not None:
            stop_distance = abs(entry_price - stop_loss_price)
            if stop_distance > 0:
                position_size = risk_amount / (stop_distance / entry_price)
            else:
                position_size = risk_amount
                
        else:
            position_size = risk_amount
        
        # Áp dụng đòn bẩy
        position_size = position_size * leverage
        
        return position_size
    
    def _update_metrics_from_history(self) -> None:
        """Cập nhật tỷ lệ thắng và tỷ lệ lợi nhuận/thua lỗ từ lịch sử"""
        if not self.trade_history:
            return
            
        wins = [trade for trade in self.trade_history if trade.get('profit', 0) > 0]
        losses = [trade for trade in self.trade_history if trade.get('profit', 0) <= 0]
        
        # Cập nhật tỷ lệ thắng
        if len(self.trade_history) > 0:
            self.win_rate = len(wins) / len(self.trade_history)
            
        # Cập nhật tỷ lệ lợi nhuận/thua lỗ
        if len(wins) > 0 and len(losses) > 0:
            avg_win = sum(trade.get('profit', 0) for trade in wins) / len(wins)
            avg_loss = sum(abs(trade.get('profit', 0)) for trade in losses) / len(losses)
            
            if avg_loss > 0:
                self.win_loss_ratio = avg_win / avg_loss
            else:
                self.win_loss_ratio = 2.0  # Giá trị mặc định nếu chưa có lỗ

class AntiMartingaleSizer(BasePositionSizer):
    """Position sizer tăng kích thước vị thế sau khi thắng, giảm sau khi thua"""
    
    def __init__(self, account_balance: float, base_risk_percentage: float = 1.0,
              increase_factor: float = 1.5, decrease_factor: float = 0.5,
              max_risk_percentage: float = 5.0, min_risk_percentage: float = 0.5):
        """
        Khởi tạo Anti-Martingale Sizer
        
        Args:
            account_balance (float): Số dư tài khoản
            base_risk_percentage (float): Phần trăm rủi ro cơ bản
            increase_factor (float): Hệ số tăng sau khi thắng
            decrease_factor (float): Hệ số giảm sau khi thua
            max_risk_percentage (float): Phần trăm rủi ro tối đa
            min_risk_percentage (float): Phần trăm rủi ro tối thiểu
        """
        super().__init__(account_balance, base_risk_percentage)
        self.base_risk_percentage = base_risk_percentage
        self.current_risk_percentage = base_risk_percentage
        self.increase_factor = increase_factor
        self.decrease_factor = decrease_factor
        self.max_risk_percentage = max_risk_percentage
        self.min_risk_percentage = min_risk_percentage
        self.last_trade_profit = None
        self.name = "Anti-Martingale Sizer"
        
    def calculate_position_size(self, current_price: float, account_balance: float = None, 
                             leverage: int = 1, volatility: float = None, market_data: Dict = None,
                             entry_price: float = None, stop_loss_price: float = None) -> float:
        """
        Tính toán kích thước vị thế theo phương pháp anti-martingale
        
        Args:
            current_price (float): Giá hiện tại
            account_balance (float, optional): Số dư tài khoản
            leverage (int): Đòn bẩy
            volatility (float, optional): Độ biến động
            market_data (Dict, optional): Dữ liệu thị trường bổ sung
            entry_price (float, optional): Giá vào lệnh
            stop_loss_price (float, optional): Giá stop loss
            
        Returns:
            float: Kích thước vị thế (tính bằng quote currency)
        """
        # Sử dụng số dư tài khoản đã cho hoặc số dư mặc định
        balance = account_balance if account_balance is not None else self.account_balance
        
        # Điều chỉnh tỷ lệ rủi ro dựa trên kết quả giao dịch gần nhất
        if len(self.trade_history) > 0:
            last_trade = self.trade_history[-1]
            
            if last_trade.get('profit', 0) > 0:
                # Tăng tỷ lệ rủi ro sau khi thắng
                self.current_risk_percentage = min(
                    self.current_risk_percentage * self.increase_factor,
                    self.max_risk_percentage
                )
            else:
                # Giảm tỷ lệ rủi ro sau khi thua
                self.current_risk_percentage = max(
                    self.current_risk_percentage * self.decrease_factor,
                    self.min_risk_percentage
                )
        
        # Tính số tiền rủi ro
        risk_amount = balance * (self.current_risk_percentage / 100)
        
        # Nếu có stop loss
        if stop_loss_price is not None and entry_price is not None:
            stop_distance = abs(entry_price - stop_loss_price)
            if stop_distance > 0:
                position_size = risk_amount / (stop_distance / entry_price)
            else:
                position_size = risk_amount
                
        else:
            position_size = risk_amount
        
        # Áp dụng đòn bẩy
        position_size = position_size * leverage
        
        return position_size
    
    def reset_to_base_risk(self) -> None:
        """Đặt lại tỷ lệ rủi ro về mức cơ bản"""
        self.current_risk_percentage = self.base_risk_percentage

class PortfolioSizer(BasePositionSizer):
    """Position sizer quản lý kích thước vị thế theo danh mục đầu tư"""
    
    def __init__(self, account_balance: float, max_open_positions: int = 5, 
              equal_weight: bool = True, asset_weights: Dict[str, float] = None,
              base_risk_percentage: float = 1.0):
        """
        Khởi tạo Portfolio Sizer
        
        Args:
            account_balance (float): Số dư tài khoản
            max_open_positions (int): Số lượng vị thế mở tối đa
            equal_weight (bool): Phân bổ vốn đều cho tất cả vị thế
            asset_weights (Dict[str, float], optional): Trọng số cho từng tài sản
            base_risk_percentage (float): Phần trăm rủi ro cơ bản
        """
        super().__init__(account_balance, base_risk_percentage)
        self.max_open_positions = max_open_positions
        self.equal_weight = equal_weight
        self.asset_weights = asset_weights or {}
        self.open_positions = []
        self.name = "Portfolio Sizer"
        
    def calculate_position_size(self, current_price: float, account_balance: float = None, 
                             leverage: int = 1, volatility: float = None, market_data: Dict = None,
                             entry_price: float = None, stop_loss_price: float = None) -> float:
        """
        Tính toán kích thước vị thế theo danh mục
        
        Args:
            current_price (float): Giá hiện tại
            account_balance (float, optional): Số dư tài khoản
            leverage (int): Đòn bẩy
            volatility (float, optional): Độ biến động
            market_data (Dict, optional): Dữ liệu thị trường bổ sung
            entry_price (float, optional): Giá vào lệnh
            stop_loss_price (float, optional): Giá stop loss
            
        Returns:
            float: Kích thước vị thế (tính bằng quote currency)
        """
        # Sử dụng số dư tài khoản đã cho hoặc số dư mặc định
        balance = account_balance if account_balance is not None else self.account_balance
        
        # Lấy thông tin symbol nếu có
        symbol = market_data.get('symbol', '') if market_data else ''
        
        # Tính phần vốn khả dụng cho vị thế mới
        if len(self.open_positions) >= self.max_open_positions:
            logger.warning(f"Đã đạt số lượng vị thế tối đa ({self.max_open_positions})")
            return 0
        
        # Nếu phân bổ đều
        if self.equal_weight:
            position_allocation = balance / self.max_open_positions
        else:
            # Phân bổ theo trọng số
            weight = self.asset_weights.get(symbol, 1.0 / self.max_open_positions)
            position_allocation = balance * weight
        
        # Tính số tiền rủi ro
        risk_amount = position_allocation * (self.risk_percentage / 100)
        
        # Nếu có stop loss
        if stop_loss_price is not None and entry_price is not None:
            stop_distance = abs(entry_price - stop_loss_price)
            if stop_distance > 0:
                position_size = risk_amount / (stop_distance / entry_price)
            else:
                position_size = risk_amount
                
        elif volatility is not None and volatility > 0:
            # Sử dụng ATR nếu không có stop loss cụ thể
            stop_distance = volatility * 2  # Giả định stop loss là 2 ATR
            position_size = risk_amount / (stop_distance / current_price)
            
        else:
            position_size = risk_amount
        
        # Áp dụng đòn bẩy
        position_size = position_size * leverage
        
        return position_size
    
    def add_open_position(self, position_info: Dict) -> None:
        """
        Thêm vị thế mở vào danh sách
        
        Args:
            position_info (Dict): Thông tin vị thế
        """
        self.open_positions.append(position_info)
        
    def remove_open_position(self, position_id: str) -> bool:
        """
        Xóa vị thế khỏi danh sách
        
        Args:
            position_id (str): ID của vị thế
            
        Returns:
            bool: True nếu xóa thành công, False nếu không
        """
        for i, position in enumerate(self.open_positions):
            if position.get('id') == position_id:
                self.open_positions.pop(i)
                return True
        return False
    
    def set_asset_weights(self, weights: Dict[str, float]) -> None:
        """
        Thiết lập trọng số mới cho các tài sản
        
        Args:
            weights (Dict[str, float]): Trọng số mới
        """
        self.asset_weights = weights
        self.equal_weight = False

def create_position_sizer(sizer_type: str, account_balance: float, **kwargs) -> BasePositionSizer:
    """
    Tạo position sizer dựa trên loại
    
    Args:
        sizer_type (str): Loại position sizer
        account_balance (float): Số dư tài khoản
        **kwargs: Các tham số bổ sung
        
    Returns:
        BasePositionSizer: Đối tượng position sizer
    """
    if sizer_type.lower() == 'fixed':
        return FixedPositionSizer(account_balance, **kwargs)
        
    elif sizer_type.lower() == 'dynamic':
        return DynamicPositionSizer(account_balance, **kwargs)
        
    elif sizer_type.lower() == 'kelly':
        return KellyCriterionSizer(account_balance, **kwargs)
        
    elif sizer_type.lower() == 'anti_martingale':
        return AntiMartingaleSizer(account_balance, **kwargs)
        
    elif sizer_type.lower() == 'portfolio':
        return PortfolioSizer(account_balance, **kwargs)
        
    else:
        # Mặc định sử dụng dynamic
        logger.warning(f"Loại position sizer không được hỗ trợ: {sizer_type}. Sử dụng dynamic thay thế.")
        return DynamicPositionSizer(account_balance, **kwargs)

def main():
    """Hàm chính để demo"""
    account_balance = 10000.0
    
    # Tạo các position sizer
    fixed_sizer = create_position_sizer('fixed', account_balance, fixed_amount=100.0)
    dynamic_sizer = create_position_sizer('dynamic', account_balance, risk_percentage=1.0)
    kelly_sizer = create_position_sizer('kelly', account_balance, win_rate=0.6, win_loss_ratio=2.0)
    anti_martingale = create_position_sizer('anti_martingale', account_balance)
    portfolio_sizer = create_position_sizer('portfolio', account_balance, max_open_positions=5)
    
    # Tính kích thước vị thế
    current_price = 50000.0
    entry_price = 50000.0
    stop_loss = 49000.0
    
    fixed_size = fixed_sizer.calculate_position_size(current_price)
    dynamic_size = dynamic_sizer.calculate_position_size(
        current_price, 
        entry_price=entry_price, 
        stop_loss_price=stop_loss
    )
    kelly_size = kelly_sizer.calculate_position_size(
        current_price, 
        entry_price=entry_price, 
        stop_loss_price=stop_loss
    )
    anti_martingale_size = anti_martingale.calculate_position_size(
        current_price, 
        entry_price=entry_price, 
        stop_loss_price=stop_loss
    )
    portfolio_size = portfolio_sizer.calculate_position_size(
        current_price, 
        entry_price=entry_price, 
        stop_loss_price=stop_loss
    )
    
    print(f"Fixed Size: {fixed_size}")
    print(f"Dynamic Size: {dynamic_size}")
    print(f"Kelly Criterion Size: {kelly_size}")
    print(f"Anti-Martingale Size: {anti_martingale_size}")
    print(f"Portfolio Size: {portfolio_size}")
    
if __name__ == "__main__":
    main()