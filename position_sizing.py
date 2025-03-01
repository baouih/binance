"""
Module quản lý vốn và tính toán kích thước vị thế nâng cao

Module này cung cấp các thuật toán quản lý vốn tiên tiến như:
- Position Sizing động dựa trên biến động thị trường
- Kelly Criterion để tối ưu hóa kích thước vị thế
- Anti-Martingale thông minh thay đổi kích thước dựa trên chuỗi thắng/thua
- Phân bổ tài sản đa cặp tiền với tính toán tương quan

Các thuật toán này giúp tối ưu hóa hiệu suất dài hạn và quản lý rủi ro tốt hơn.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("position_sizing")

class BasePositionSizer:
    """Lớp cơ sở cho tất cả các chiến lược tính toán kích thước vị thế"""
    
    def __init__(self, account_balance: float, max_risk_pct: float = 2.0, 
                max_position_pct: float = 20.0):
        """
        Khởi tạo position sizer.
        
        Args:
            account_balance (float): Số dư tài khoản hiện tại
            max_risk_pct (float): Phần trăm rủi ro tối đa trên mỗi giao dịch
            max_position_pct (float): Phần trăm tối đa của tài khoản cho một vị thế
        """
        self.account_balance = account_balance
        self.max_risk_pct = max_risk_pct
        self.max_position_pct = max_position_pct
    
    def calculate_position_size(self, entry_price: float, stop_loss_price: float, 
                               **kwargs) -> Tuple[float, float]:
        """
        Tính toán kích thước vị thế cơ bản.
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss_price (float): Giá stop loss
            
        Returns:
            Tuple[float, float]: (Số lượng hợp đồng/coin, Phần trăm tài khoản)
        """
        # Tính toán rủi ro theo số tiền
        risk_amount = self.account_balance * (self.max_risk_pct / 100)
        
        # Tính khoảng cách từ entry đến stop loss theo phần trăm
        if stop_loss_price > 0:
            risk_per_unit = abs(entry_price - stop_loss_price)
        else:
            # Nếu không có stop loss cụ thể, sử dụng giá trị mặc định 2%
            risk_per_unit = entry_price * 0.02
            
        # Tính số lượng hợp đồng/coin
        if risk_per_unit > 0:
            position_size = risk_amount / risk_per_unit
        else:
            position_size = 0
            
        # Tính giá trị vị thế
        position_value = position_size * entry_price
        
        # Giới hạn kích thước vị thế theo phần trăm tài khoản tối đa
        max_position_value = self.account_balance * (self.max_position_pct / 100)
        if position_value > max_position_value:
            position_size = max_position_value / entry_price
            position_value = position_size * entry_price
            
        position_pct = (position_value / self.account_balance) * 100
        
        return position_size, position_pct
        
    def update_balance(self, new_balance: float) -> None:
        """
        Cập nhật số dư tài khoản.
        
        Args:
            new_balance (float): Số dư tài khoản mới
        """
        self.account_balance = new_balance
        
    def set_risk_parameters(self, max_risk_pct: float = None, 
                          max_position_pct: float = None) -> None:
        """
        Cập nhật tham số rủi ro.
        
        Args:
            max_risk_pct (float, optional): Phần trăm rủi ro tối đa mới
            max_position_pct (float, optional): Phần trăm tối đa của tài khoản cho một vị thế
        """
        if max_risk_pct is not None:
            self.max_risk_pct = max_risk_pct
        if max_position_pct is not None:
            self.max_position_pct = max_position_pct


class DynamicPositionSizer(BasePositionSizer):
    """Chiến lược tính toán kích thước vị thế dựa trên biến động thị trường"""
    
    def __init__(self, account_balance: float, max_risk_pct: float = 2.0, 
                max_position_pct: float = 20.0, volatility_factor: float = 1.0,
                confidence_factor: float = 1.0):
        """
        Khởi tạo position sizer động.
        
        Args:
            account_balance (float): Số dư tài khoản hiện tại
            max_risk_pct (float): Phần trăm rủi ro tối đa trên mỗi giao dịch
            max_position_pct (float): Phần trăm tối đa của tài khoản cho một vị thế
            volatility_factor (float): Hệ số điều chỉnh theo biến động (1.0 = không điều chỉnh)
            confidence_factor (float): Hệ số điều chỉnh theo độ tin cậy tín hiệu (1.0 = không điều chỉnh)
        """
        super().__init__(account_balance, max_risk_pct, max_position_pct)
        self.volatility_factor = volatility_factor
        self.confidence_factor = confidence_factor
        
    def calculate_position_size(self, entry_price: float, stop_loss_price: float,
                               volatility: float = None, signal_confidence: float = None,
                               **kwargs) -> Tuple[float, float]:
        """
        Tính toán kích thước vị thế dựa trên biến động và độ tin cậy.
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss_price (float): Giá stop loss
            volatility (float, optional): Chỉ số biến động (ATR hoặc biến động chuẩn)
            signal_confidence (float, optional): Độ tin cậy của tín hiệu (0-1)
            
        Returns:
            Tuple[float, float]: (Số lượng hợp đồng/coin, Phần trăm tài khoản)
        """
        # Tính kích thước vị thế cơ bản
        base_size, base_pct = super().calculate_position_size(entry_price, stop_loss_price)
        
        # Điều chỉnh theo biến động
        volatility_multiplier = 1.0
        if volatility is not None:
            # Điều chỉnh kích thước vị thế ngược với biến động
            # Biến động cao -> kích thước nhỏ, biến động thấp -> kích thước lớn
            normalized_volatility = min(max(volatility, 0.5), 2.0)  # Giới hạn trong khoảng 0.5-2.0
            volatility_multiplier = 1.0 / (normalized_volatility ** self.volatility_factor)
            
        # Điều chỉnh theo độ tin cậy
        confidence_multiplier = 1.0
        if signal_confidence is not None:
            # Độ tin cậy cao -> kích thước lớn, độ tin cậy thấp -> kích thước nhỏ
            confidence_multiplier = signal_confidence ** self.confidence_factor
            
        # Áp dụng điều chỉnh
        adjusted_size = base_size * volatility_multiplier * confidence_multiplier
        adjusted_value = adjusted_size * entry_price
        adjusted_pct = (adjusted_value / self.account_balance) * 100
        
        # Đảm bảo không vượt quá giới hạn
        max_position_value = self.account_balance * (self.max_position_pct / 100)
        if adjusted_value > max_position_value:
            adjusted_size = max_position_value / entry_price
            adjusted_value = adjusted_size * entry_price
            adjusted_pct = (adjusted_value / self.account_balance) * 100
            
        logger.info(f"Dynamic position sizing: Base size={base_size:.4f}, " + 
                   f"Adjusted size={adjusted_size:.4f} " +
                   f"(Volatility={volatility}, Confidence={signal_confidence})")
            
        return adjusted_size, adjusted_pct
        
    def set_adjustment_factors(self, volatility_factor: float = None, 
                             confidence_factor: float = None) -> None:
        """
        Cập nhật các hệ số điều chỉnh.
        
        Args:
            volatility_factor (float, optional): Hệ số điều chỉnh biến động mới
            confidence_factor (float, optional): Hệ số điều chỉnh độ tin cậy mới
        """
        if volatility_factor is not None:
            self.volatility_factor = volatility_factor
        if confidence_factor is not None:
            self.confidence_factor = confidence_factor


class KellyCriterionSizer(BasePositionSizer):
    """Chiến lược tính toán kích thước vị thế dựa trên công thức Kelly Criterion"""
    
    def __init__(self, account_balance: float, max_risk_pct: float = 2.0,
                max_position_pct: float = 20.0, kelly_fraction: float = 0.5,
                win_rate: float = 0.5, avg_win_loss_ratio: float = 1.0):
        """
        Khởi tạo Kelly position sizer.
        
        Args:
            account_balance (float): Số dư tài khoản hiện tại
            max_risk_pct (float): Phần trăm rủi ro tối đa trên mỗi giao dịch
            max_position_pct (float): Phần trăm tối đa của tài khoản cho một vị thế
            kelly_fraction (float): Phần Kelly sử dụng (1.0 = Full Kelly, 0.5 = Half Kelly)
            win_rate (float): Tỷ lệ thắng lịch sử (0-1)
            avg_win_loss_ratio (float): Tỷ lệ lời trung bình / lỗ trung bình
        """
        super().__init__(account_balance, max_risk_pct, max_position_pct)
        self.kelly_fraction = kelly_fraction
        self.win_rate = win_rate
        self.avg_win_loss_ratio = avg_win_loss_ratio
        # Lịch sử giao dịch để tự động tính toán tỷ lệ thắng và tỷ lệ lời/lỗ
        self.trade_history = []
        
    def calculate_position_size(self, entry_price: float, stop_loss_price: float,
                               take_profit_price: float = None, win_rate: float = None,
                               win_loss_ratio: float = None, **kwargs) -> Tuple[float, float]:
        """
        Tính toán kích thước vị thế dựa trên công thức Kelly Criterion.
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss_price (float): Giá stop loss
            take_profit_price (float, optional): Giá take profit
            win_rate (float, optional): Tỷ lệ thắng ước tính cho giao dịch này
            win_loss_ratio (float, optional): Tỷ lệ lời/lỗ ước tính cho giao dịch này
            
        Returns:
            Tuple[float, float]: (Số lượng hợp đồng/coin, Phần trăm tài khoản)
        """
        # Sử dụng giá trị được cung cấp hoặc giá trị mặc định
        win_probability = win_rate if win_rate is not None else self.win_rate
        
        # Tính tỷ lệ lời/lỗ nếu chưa cung cấp
        if win_loss_ratio is None:
            if take_profit_price is not None and stop_loss_price is not None:
                # Tính từ mức take profit và stop loss
                potential_profit = abs(take_profit_price - entry_price)
                potential_loss = abs(entry_price - stop_loss_price)
                
                if potential_loss > 0:
                    calculated_ratio = potential_profit / potential_loss
                else:
                    calculated_ratio = 1.0  # Giá trị mặc định nếu không có stop loss
            else:
                # Sử dụng giá trị lịch sử
                calculated_ratio = self.avg_win_loss_ratio
        else:
            calculated_ratio = win_loss_ratio
            
        # Tính Kelly percentage
        # formula: f* = (p * b - q) / b = (p * b - (1-p)) / b
        # where p = win probability, q = 1-p = loss probability, b = win/loss ratio
        q = 1 - win_probability
        kelly_pct = (win_probability * calculated_ratio - q) / calculated_ratio
        
        # Kelly có thể âm (nghĩa là không nên giao dịch)
        # hoặc lớn hơn 1 (nghĩa là đòn bẩy)
        kelly_pct = max(0, min(1, kelly_pct))
        
        # Áp dụng phân số Kelly để giảm biến động
        kelly_pct *= self.kelly_fraction
        
        # Đảm bảo không vượt quá mức rủi ro tối đa
        risk_pct = min(kelly_pct * 100, self.max_risk_pct)
        
        # Tính số tiền rủi ro
        risk_amount = self.account_balance * (risk_pct / 100)
        
        # Tính khoảng cách từ entry đến stop loss
        if stop_loss_price > 0:
            risk_per_unit = abs(entry_price - stop_loss_price)
        else:
            # Nếu không có stop loss cụ thể, sử dụng giá trị mặc định 2%
            risk_per_unit = entry_price * 0.02
            
        # Tính số lượng hợp đồng/coin
        if risk_per_unit > 0:
            position_size = risk_amount / risk_per_unit
        else:
            position_size = 0
            
        # Tính giá trị vị thế
        position_value = position_size * entry_price
        
        # Giới hạn kích thước vị thế theo phần trăm tài khoản tối đa
        max_position_value = self.account_balance * (self.max_position_pct / 100)
        if position_value > max_position_value:
            position_size = max_position_value / entry_price
            position_value = position_size * entry_price
            
        position_pct = (position_value / self.account_balance) * 100
        
        logger.info(f"Kelly position sizing: Kelly%={kelly_pct:.4f}, " + 
                   f"Position%={position_pct:.2f}%, Size={position_size:.4f} " +
                   f"(Win rate={win_probability:.2f}, Win/Loss ratio={calculated_ratio:.2f})")
            
        return position_size, position_pct
    
    def update_statistics_from_trade(self, trade_result: Dict) -> None:
        """
        Cập nhật thống kê từ kết quả giao dịch.
        
        Args:
            trade_result (Dict): Kết quả giao dịch với các thông tin như lợi nhuận, thắng/thua
        """
        # Thêm vào lịch sử
        self.trade_history.append(trade_result)
        
        # Giới hạn kích thước lịch sử
        if len(self.trade_history) > 100:
            self.trade_history = self.trade_history[-100:]
            
        # Tính toán lại thống kê
        wins = sum(1 for trade in self.trade_history if trade.get('profit', 0) > 0)
        self.win_rate = wins / len(self.trade_history) if self.trade_history else 0.5
        
        # Tính tỷ lệ lời/lỗ
        winning_trades = [trade for trade in self.trade_history if trade.get('profit', 0) > 0]
        losing_trades = [trade for trade in self.trade_history if trade.get('profit', 0) <= 0]
        
        avg_win = np.mean([trade.get('profit', 0) for trade in winning_trades]) if winning_trades else 0
        avg_loss = abs(np.mean([trade.get('profit', 0) for trade in losing_trades])) if losing_trades else 1
        
        if avg_loss > 0:
            self.avg_win_loss_ratio = avg_win / avg_loss
        else:
            self.avg_win_loss_ratio = 1.0
            
        logger.info(f"Updated Kelly statistics: Win rate={self.win_rate:.2f}, " +
                   f"Win/Loss ratio={self.avg_win_loss_ratio:.2f}")
    
    def set_kelly_parameters(self, kelly_fraction: float = None, 
                           win_rate: float = None, 
                           avg_win_loss_ratio: float = None) -> None:
        """
        Cập nhật tham số Kelly.
        
        Args:
            kelly_fraction (float, optional): Phần Kelly sử dụng
            win_rate (float, optional): Tỷ lệ thắng
            avg_win_loss_ratio (float, optional): Tỷ lệ lời/lỗ trung bình
        """
        if kelly_fraction is not None:
            self.kelly_fraction = kelly_fraction
        if win_rate is not None:
            self.win_rate = win_rate
        if avg_win_loss_ratio is not None:
            self.avg_win_loss_ratio = avg_win_loss_ratio


class AntiMartingaleSizer(BasePositionSizer):
    """Chiến lược Anti-Martingale thông minh điều chỉnh kích thước vị thế dựa trên chuỗi thắng/thua"""
    
    def __init__(self, account_balance: float, max_risk_pct: float = 2.0,
                max_position_pct: float = 20.0, base_unit_pct: float = 1.0,
                increase_factor: float = 1.5, decrease_factor: float = 0.7,
                max_consecutive_increases: int = 3):
        """
        Khởi tạo Anti-Martingale position sizer.
        
        Args:
            account_balance (float): Số dư tài khoản hiện tại
            max_risk_pct (float): Phần trăm rủi ro tối đa trên mỗi giao dịch
            max_position_pct (float): Phần trăm tối đa của tài khoản cho một vị thế
            base_unit_pct (float): Phần trăm rủi ro cơ bản cho đơn vị đầu tiên
            increase_factor (float): Hệ số tăng kích thước sau thắng
            decrease_factor (float): Hệ số giảm kích thước sau thua
            max_consecutive_increases (int): Số lần tăng kích thước tối đa liên tiếp
        """
        super().__init__(account_balance, max_risk_pct, max_position_pct)
        self.base_unit_pct = base_unit_pct
        self.increase_factor = increase_factor
        self.decrease_factor = decrease_factor
        self.max_consecutive_increases = max_consecutive_increases
        
        # Trạng thái hiện tại
        self.current_unit_pct = base_unit_pct
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        self.last_trade_result = None  # 'win', 'loss', or None
        
    def calculate_position_size(self, entry_price: float, stop_loss_price: float,
                               **kwargs) -> Tuple[float, float]:
        """
        Tính toán kích thước vị thế dựa trên chiến lược Anti-Martingale.
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss_price (float): Giá stop loss
            
        Returns:
            Tuple[float, float]: (Số lượng hợp đồng/coin, Phần trăm tài khoản)
        """
        # Đảm bảo không vượt quá mức rủi ro tối đa
        risk_pct = min(self.current_unit_pct, self.max_risk_pct)
        
        # Tính số tiền rủi ro
        risk_amount = self.account_balance * (risk_pct / 100)
        
        # Tính khoảng cách từ entry đến stop loss
        if stop_loss_price > 0:
            risk_per_unit = abs(entry_price - stop_loss_price)
        else:
            # Nếu không có stop loss cụ thể, sử dụng giá trị mặc định 2%
            risk_per_unit = entry_price * 0.02
            
        # Tính số lượng hợp đồng/coin
        if risk_per_unit > 0:
            position_size = risk_amount / risk_per_unit
        else:
            position_size = 0
            
        # Tính giá trị vị thế
        position_value = position_size * entry_price
        
        # Giới hạn kích thước vị thế theo phần trăm tài khoản tối đa
        max_position_value = self.account_balance * (self.max_position_pct / 100)
        if position_value > max_position_value:
            position_size = max_position_value / entry_price
            position_value = position_size * entry_price
            
        position_pct = (position_value / self.account_balance) * 100
        
        logger.info(f"Anti-Martingale position sizing: Current unit%={self.current_unit_pct:.2f}%, " + 
                   f"Position%={position_pct:.2f}%, Size={position_size:.4f} " +
                   f"(Consecutive wins={self.consecutive_wins}, losses={self.consecutive_losses})")
            
        return position_size, position_pct
    
    def update_after_trade(self, is_win: bool) -> None:
        """
        Cập nhật trạng thái sau giao dịch.
        
        Args:
            is_win (bool): True nếu giao dịch thắng, False nếu thua
        """
        if is_win:
            # Sau khi thắng, tăng kích thước vị thế
            self.consecutive_wins += 1
            self.consecutive_losses = 0
            self.last_trade_result = 'win'
            
            # Chỉ tăng nếu chưa đạt số lần tăng tối đa
            if self.consecutive_wins <= self.max_consecutive_increases:
                self.current_unit_pct *= self.increase_factor
                # Đảm bảo không vượt quá max_risk_pct
                self.current_unit_pct = min(self.current_unit_pct, self.max_risk_pct)
        else:
            # Sau khi thua, giảm kích thước vị thế
            self.consecutive_losses += 1
            self.consecutive_wins = 0
            self.last_trade_result = 'loss'
            
            # Giảm kích thước
            self.current_unit_pct *= self.decrease_factor
            # Đảm bảo không dưới base_unit_pct
            self.current_unit_pct = max(self.current_unit_pct, self.base_unit_pct)
            
        logger.info(f"Updated Anti-Martingale state: current_unit%={self.current_unit_pct:.2f}%, " +
                   f"after {'win' if is_win else 'loss'}")
    
    def reset(self) -> None:
        """Đặt lại về trạng thái ban đầu"""
        self.current_unit_pct = self.base_unit_pct
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        self.last_trade_result = None
        logger.info("Reset Anti-Martingale position sizer to initial state")
    
    def set_antimartingale_parameters(self, base_unit_pct: float = None, 
                                   increase_factor: float = None,
                                   decrease_factor: float = None,
                                   max_consecutive_increases: int = None) -> None:
        """
        Cập nhật tham số Anti-Martingale.
        
        Args:
            base_unit_pct (float, optional): Phần trăm rủi ro cơ bản mới
            increase_factor (float, optional): Hệ số tăng mới
            decrease_factor (float, optional): Hệ số giảm mới
            max_consecutive_increases (int, optional): Số lần tăng tối đa mới
        """
        if base_unit_pct is not None:
            self.base_unit_pct = base_unit_pct
        if increase_factor is not None:
            self.increase_factor = increase_factor
        if decrease_factor is not None:
            self.decrease_factor = decrease_factor
        if max_consecutive_increases is not None:
            self.max_consecutive_increases = max_consecutive_increases


class PortfolioSizer:
    """Phân bổ tài sản cho nhiều cặp tiền dựa trên tính toán tương quan"""
    
    def __init__(self, account_balance: float, max_portfolio_risk: float = 5.0,
                max_per_symbol_risk: float = 2.0, correlation_impact: float = 0.5):
        """
        Khởi tạo Portfolio Sizer.
        
        Args:
            account_balance (float): Số dư tài khoản tổng
            max_portfolio_risk (float): Phần trăm rủi ro tối đa cho cả danh mục đầu tư
            max_per_symbol_risk (float): Phần trăm rủi ro tối đa cho mỗi cặp tiền
            correlation_impact (float): Mức độ ảnh hưởng của tương quan (0-1)
        """
        self.account_balance = account_balance
        self.max_portfolio_risk = max_portfolio_risk
        self.max_per_symbol_risk = max_per_symbol_risk
        self.correlation_impact = correlation_impact
        
        # Lưu trữ dữ liệu
        self.positions = {}  # Các vị thế hiện tại
        self.correlations = {}  # Ma trận tương quan giữa các cặp tiền
        
    def calculate_position_allocations(self, symbols: List[str],
                                    signals: Dict[str, Dict],
                                    correlations: Dict[str, Dict] = None) -> Dict[str, Dict]:
        """
        Tính toán phân bổ vốn cho nhiều cặp tiền.
        
        Args:
            symbols (List[str]): Danh sách các cặp tiền cần phân bổ
            signals (Dict[str, Dict]): Tín hiệu giao dịch cho mỗi cặp tiền
                Định dạng: {symbol: {'signal': 'buy'/'sell'/'neutral', 'strength': 0-1, 'entry_price': float, 'stop_loss': float}}
            correlations (Dict[str, Dict], optional): Ma trận tương quan giữa các cặp tiền
                Định dạng: {symbol1: {symbol2: correlation_value}}
                
        Returns:
            Dict[str, Dict]: Phân bổ vốn cho mỗi cặp tiền
                Định dạng: {symbol: {'position_size': float, 'position_pct': float, 'risk_pct': float, 'risk_amount': float}}
        """
        # Cập nhật ma trận tương quan nếu được cung cấp
        if correlations:
            self.correlations = correlations
            
        # Lọc các cặp tiền có tín hiệu không phải neutral
        active_symbols = [s for s in symbols if signals.get(s, {}).get('signal', 'neutral') != 'neutral']
        
        if not active_symbols:
            logger.info("No active trading signals, skipping portfolio allocation")
            return {}
            
        # Tính toán điểm số ban đầu cho mỗi cặp tiền dựa trên độ mạnh tín hiệu
        initial_scores = {}
        for symbol in active_symbols:
            signal_strength = signals.get(symbol, {}).get('strength', 0.5)
            initial_scores[symbol] = signal_strength
            
        # Tính toán điều chỉnh dựa trên tương quan
        if self.correlations and len(active_symbols) > 1:
            adjusted_scores = initial_scores.copy()
            
            # Duyệt qua từng cặp tiền và điều chỉnh dựa trên tương quan với các cặp khác
            for symbol in active_symbols:
                correlation_adjustment = 0
                
                for other_symbol in active_symbols:
                    if symbol != other_symbol:
                        # Lấy tương quan, mặc định là 0 nếu không có dữ liệu
                        corr = self.correlations.get(symbol, {}).get(other_symbol, 0)
                        
                        # Cùng hướng tín hiệu -> điều chỉnh giảm để tránh quá tập trung
                        # Ngược hướng tín hiệu -> điều chỉnh tăng để đa dạng hóa
                        other_signal = signals.get(other_symbol, {}).get('signal', 'neutral')
                        current_signal = signals.get(symbol, {}).get('signal', 'neutral')
                        
                        if current_signal != 'neutral' and other_signal != 'neutral':
                            # Nếu cùng hướng, tương quan cao -> giảm
                            if (current_signal == other_signal) and corr > 0.5:
                                correlation_adjustment -= corr * 0.1
                            # Nếu ngược hướng, tương quan âm -> tăng
                            elif (current_signal != other_signal) and corr < -0.3:
                                correlation_adjustment += abs(corr) * 0.1
                
                # Áp dụng điều chỉnh với hệ số ảnh hưởng
                adjusted_scores[symbol] += correlation_adjustment * self.correlation_impact
                # Đảm bảo điểm số trong khoảng hợp lý
                adjusted_scores[symbol] = max(0.1, min(1.0, adjusted_scores[symbol]))
        else:
            adjusted_scores = initial_scores
                
        # Tính tổng điểm số để chuẩn hóa
        total_score = sum(adjusted_scores.values())
        
        # Phân bổ rủi ro dựa trên điểm đã điều chỉnh
        risk_allocations = {}
        total_allocated_risk = 0
        
        for symbol in active_symbols:
            # Tính phần trăm rủi ro cho cặp này
            normalized_score = adjusted_scores[symbol] / total_score if total_score > 0 else 0
            symbol_risk_pct = normalized_score * self.max_portfolio_risk
            
            # Đảm bảo không vượt quá rủi ro tối đa cho mỗi cặp
            symbol_risk_pct = min(symbol_risk_pct, self.max_per_symbol_risk)
            
            risk_amount = self.account_balance * (symbol_risk_pct / 100)
            total_allocated_risk += symbol_risk_pct
            
            risk_allocations[symbol] = {
                'risk_pct': symbol_risk_pct,
                'risk_amount': risk_amount,
                'adjusted_score': adjusted_scores[symbol],
                'initial_score': initial_scores[symbol]
            }
            
        # Tính kích thước vị thế cho mỗi cặp tiền
        position_allocations = {}
        
        for symbol in active_symbols:
            signal_data = signals.get(symbol, {})
            entry_price = signal_data.get('entry_price', 0)
            stop_loss = signal_data.get('stop_loss', 0)
            
            # Tính risk_per_unit
            if stop_loss > 0 and entry_price > 0:
                risk_per_unit = abs(entry_price - stop_loss)
            else:
                # Nếu không có stop loss cụ thể, sử dụng giá trị mặc định 2%
                risk_per_unit = entry_price * 0.02
                
            risk_amount = risk_allocations[symbol]['risk_amount']
            
            # Tính size
            if risk_per_unit > 0 and entry_price > 0:
                position_size = risk_amount / risk_per_unit
                position_value = position_size * entry_price
                position_pct = (position_value / self.account_balance) * 100
            else:
                position_size = 0
                position_value = 0
                position_pct = 0
                
            position_allocations[symbol] = {
                'position_size': position_size,
                'position_value': position_value,
                'position_pct': position_pct,
                'risk_pct': risk_allocations[symbol]['risk_pct'],
                'risk_amount': risk_allocations[symbol]['risk_amount'],
                'adjusted_score': risk_allocations[symbol]['adjusted_score'],
                'initial_score': risk_allocations[symbol]['initial_score']
            }
            
        # Log thông tin phân bổ
        logger.info(f"Portfolio allocation for {len(active_symbols)} symbols:")
        for symbol, alloc in position_allocations.items():
            logger.info(f"  {symbol}: Size={alloc['position_size']:.4f}, " +
                       f"Value=${alloc['position_value']:.2f} ({alloc['position_pct']:.2f}%), " +
                       f"Risk={alloc['risk_pct']:.2f}%")
            
        return position_allocations
    
    def update_portfolio_state(self, active_positions: Dict[str, Dict]) -> None:
        """
        Cập nhật trạng thái danh mục đầu tư.
        
        Args:
            active_positions (Dict[str, Dict]): Các vị thế đang mở
                Định dạng: {symbol: position_data}
        """
        self.positions = active_positions
        
    def update_balance(self, new_balance: float) -> None:
        """
        Cập nhật số dư tài khoản.
        
        Args:
            new_balance (float): Số dư tài khoản mới
        """
        self.account_balance = new_balance
        
    def set_portfolio_parameters(self, max_portfolio_risk: float = None,
                               max_per_symbol_risk: float = None,
                               correlation_impact: float = None) -> None:
        """
        Cập nhật tham số danh mục đầu tư.
        
        Args:
            max_portfolio_risk (float, optional): Phần trăm rủi ro tối đa cho cả danh mục
            max_per_symbol_risk (float, optional): Phần trăm rủi ro tối đa cho mỗi cặp tiền
            correlation_impact (float, optional): Mức độ ảnh hưởng của tương quan
        """
        if max_portfolio_risk is not None:
            self.max_portfolio_risk = max_portfolio_risk
        if max_per_symbol_risk is not None:
            self.max_per_symbol_risk = max_per_symbol_risk
        if correlation_impact is not None:
            self.correlation_impact = correlation_impact
            
            
def create_position_sizer(sizer_type: str, account_balance: float, **kwargs) -> BasePositionSizer:
    """
    Tạo position sizer theo loại.
    
    Args:
        sizer_type (str): Loại position sizer ('dynamic', 'kelly', 'antimartingale', 'basic')
        account_balance (float): Số dư tài khoản
        **kwargs: Các tham số bổ sung
        
    Returns:
        BasePositionSizer: Đối tượng position sizer
    """
    if sizer_type.lower() == 'dynamic':
        return DynamicPositionSizer(account_balance, **kwargs)
    elif sizer_type.lower() == 'kelly':
        return KellyCriterionSizer(account_balance, **kwargs)
    elif sizer_type.lower() == 'antimartingale':
        return AntiMartingaleSizer(account_balance, **kwargs)
    else:  # basic
        return BasePositionSizer(account_balance, **kwargs)


def main():
    """Hàm chính để test module"""
    # Ví dụ cơ bản
    account_balance = 10000.0
    
    # Test position sizer cơ bản
    basic_sizer = BasePositionSizer(account_balance, max_risk_pct=2.0)
    size, pct = basic_sizer.calculate_position_size(40000.0, 39000.0)
    print(f"Basic sizer: size={size}, pct={pct}%")
    
    # Test dynamic position sizer
    dynamic_sizer = DynamicPositionSizer(account_balance, volatility_factor=0.8, confidence_factor=1.2)
    size, pct = dynamic_sizer.calculate_position_size(40000.0, 39000.0, volatility=1.5, signal_confidence=0.8)
    print(f"Dynamic sizer: size={size}, pct={pct}%")
    
    # Test Kelly sizer
    kelly_sizer = KellyCriterionSizer(account_balance, kelly_fraction=0.5, win_rate=0.6, avg_win_loss_ratio=2.0)
    size, pct = kelly_sizer.calculate_position_size(40000.0, 39000.0, take_profit_price=42000.0)
    print(f"Kelly sizer: size={size}, pct={pct}%")
    
    # Test Anti-Martingale sizer
    anti_sizer = AntiMartingaleSizer(account_balance, base_unit_pct=1.0, increase_factor=1.5)
    size, pct = anti_sizer.calculate_position_size(40000.0, 39000.0)
    print(f"Anti-Martingale initial: size={size}, pct={pct}%")
    
    # Cập nhật sau khi thắng
    anti_sizer.update_after_trade(True)
    size, pct = anti_sizer.calculate_position_size(40000.0, 39000.0)
    print(f"Anti-Martingale after win: size={size}, pct={pct}%")
    
    # Cập nhật sau khi thua
    anti_sizer.update_after_trade(False)
    size, pct = anti_sizer.calculate_position_size(40000.0, 39000.0)
    print(f"Anti-Martingale after loss: size={size}, pct={pct}%")
    
    # Test portfolio sizer
    portfolio_sizer = PortfolioSizer(account_balance, max_portfolio_risk=5.0, correlation_impact=0.5)
    
    # Ví dụ ma trận tương quan
    correlations = {
        'BTCUSDT': {'BTCUSDT': 1.0, 'ETHUSDT': 0.8, 'SOLUSDT': 0.6},
        'ETHUSDT': {'BTCUSDT': 0.8, 'ETHUSDT': 1.0, 'SOLUSDT': 0.7},
        'SOLUSDT': {'BTCUSDT': 0.6, 'ETHUSDT': 0.7, 'SOLUSDT': 1.0}
    }
    
    # Ví dụ tín hiệu
    signals = {
        'BTCUSDT': {'signal': 'buy', 'strength': 0.8, 'entry_price': 40000.0, 'stop_loss': 39000.0},
        'ETHUSDT': {'signal': 'buy', 'strength': 0.7, 'entry_price': 2500.0, 'stop_loss': 2400.0},
        'SOLUSDT': {'signal': 'sell', 'strength': 0.6, 'entry_price': 100.0, 'stop_loss': 105.0}
    }
    
    # Tính toán phân bổ
    allocations = portfolio_sizer.calculate_position_allocations(
        ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'], signals, correlations
    )
    
    print("\nPortfolio allocations:")
    for symbol, data in allocations.items():
        print(f"{symbol}: Size={data['position_size']:.4f}, Value=${data['position_value']:.2f} " +
              f"({data['position_pct']:.2f}%), Risk={data['risk_pct']:.2f}%")
    
if __name__ == "__main__":
    main()