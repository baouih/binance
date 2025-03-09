"""
Module quản lý vị thế nâng cao (Position Sizing)

Module này cung cấp các phương thức nâng cao để tính toán kích thước vị thế
phù hợp với chiến lược đầu tư và quản lý rủi ro. Bao gồm chiến lược mới
như Pythagorean Position Sizer kết hợp tỷ lệ thắng và hệ số lợi nhuận.
"""

import math
import random
import logging
from typing import Dict, List, Optional, Tuple, Union, Any
import numpy as np
import pandas as pd

from position_sizing import BasePositionSizer

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('position_sizing_enhanced')

class PythagoreanPositionSizer(BasePositionSizer):
    """
    Sử dụng công thức Pythagoras để cân bằng giữa lợi nhuận và rủi ro.
    
    Công thức Pythagoras ở đây ám chỉ việc sử dụng căn bậc hai của tích của win_rate 
    và profit_factor để điều chỉnh kích thước vị thế. Cách tiếp cận này giúp cân bằng 
    giữa tần suất thắng và mức lợi nhuận trung bình.
    """
    
    def __init__(self, trade_history: List[Dict] = None, account_balance: float = 10000.0, risk_percentage: float = 1.0,
                lookback_trades: int = 30):
        """
        Khởi tạo Pythagorean Position Sizer.
        
        Args:
            trade_history (List[Dict], optional): Lịch sử giao dịch
            account_balance (float): Số dư tài khoản
            risk_percentage (float): Phần trăm rủi ro tối đa trên mỗi giao dịch
            lookback_trades (int): Số giao dịch gần nhất để phân tích
        """
        super().__init__(account_balance=account_balance, risk_percentage=risk_percentage)
        self.trade_history = trade_history or []
        self.lookback_trades = lookback_trades
        self.max_risk_percentage = risk_percentage  # Lưu lại để sử dụng sau này
        
    def calculate_position_size(self, current_price: float, account_balance: float = None, 
                              leverage: int = 1, volatility: float = None, market_data: Dict = None,
                              entry_price: float = None, stop_loss_price: float = None) -> float:
        """
        Tính toán kích thước vị thế sử dụng công thức Pythagoras
        
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
        # Tính win_rate và profit_factor từ lịch sử giao dịch
        win_rate = self.calculate_win_rate()
        profit_factor = self.calculate_profit_factor()
        
        # Thông báo các thông số đầu vào
        logger.info(f"Pythagorean sizer: win_rate={win_rate:.2f}, profit_factor={profit_factor:.2f}")
        
        # Tính toán vị thế cơ bản
        base_size = super().calculate_position_size(
            current_price, account_balance, leverage, volatility, 
            market_data, entry_price, stop_loss_price
        )
        
        # Điều chỉnh theo "công thức Pythagoras"
        pythagoras_factor = math.sqrt(win_rate * profit_factor)
        adjusted_size = base_size * pythagoras_factor
        
        # Giới hạn kích thước tối đa
        max_size = account_balance * (self.max_risk_percentage / 100) * leverage
        
        logger.info(f"Base size: {base_size:.2f}, Pythagoras factor: {pythagoras_factor:.2f}, " 
                  f"Adjusted size: {adjusted_size:.2f}")
        
        return min(adjusted_size, max_size)
    
    def calculate_win_rate(self) -> float:
        """
        Tính tỷ lệ thắng từ lịch sử giao dịch
        
        Returns:
            float: Tỷ lệ thắng (0-1)
        """
        if len(self.trade_history) < 10:
            return 0.5  # Giá trị mặc định nếu không đủ dữ liệu
        
        # Chỉ xem xét N giao dịch gần nhất
        recent_trades = self.trade_history[-self.lookback_trades:]
        
        winning_trades = sum(1 for trade in recent_trades if trade.get('pnl', 0) > 0)
        return winning_trades / len(recent_trades)
    
    def calculate_profit_factor(self) -> float:
        """
        Tính hệ số lợi nhuận (tổng lợi nhuận / tổng thua lỗ)
        
        Returns:
            float: Hệ số lợi nhuận
        """
        if len(self.trade_history) < 10:
            return 1.5  # Giá trị mặc định nếu không đủ dữ liệu
        
        # Chỉ xem xét N giao dịch gần nhất
        recent_trades = self.trade_history[-self.lookback_trades:]
        
        total_profit = sum(trade.get('pnl', 0) for trade in recent_trades if trade.get('pnl', 0) > 0)
        total_loss = abs(sum(trade.get('pnl', 0) for trade in recent_trades if trade.get('pnl', 0) < 0))
        
        return total_profit / total_loss if total_loss > 0 else 1.5
    
    def update_trade_history(self, new_trade: Dict) -> None:
        """
        Cập nhật lịch sử giao dịch với một giao dịch mới
        
        Args:
            new_trade (Dict): Thông tin giao dịch mới
        """
        self.trade_history.append(new_trade)
        logger.info(f"Đã thêm giao dịch mới vào lịch sử, tổng số: {len(self.trade_history)}")
    
    def set_trade_history(self, trade_history: List[Dict]) -> None:
        """
        Thiết lập lịch sử giao dịch mới
        
        Args:
            trade_history (List[Dict]): Lịch sử giao dịch mới
        """
        self.trade_history = trade_history
        logger.info(f"Đã thiết lập lịch sử giao dịch, tổng số: {len(self.trade_history)}")
    
    def get_statistics(self) -> Dict:
        """
        Lấy thống kê từ lịch sử giao dịch
        
        Returns:
            Dict: Các thống kê về hiệu suất giao dịch
        """
        if len(self.trade_history) < 5:
            return {
                "win_rate": 0.5,
                "profit_factor": 1.5,
                "average_win": 0,
                "average_loss": 0,
                "expectancy": 0,
                "total_trades": len(self.trade_history)
            }
            
        # Chỉ xem xét N giao dịch gần nhất
        recent_trades = self.trade_history[-self.lookback_trades:] if len(self.trade_history) > self.lookback_trades else self.trade_history
        
        win_rate = self.calculate_win_rate()
        profit_factor = self.calculate_profit_factor()
        
        winning_trades = [trade.get('pnl', 0) for trade in recent_trades if trade.get('pnl', 0) > 0]
        losing_trades = [trade.get('pnl', 0) for trade in recent_trades if trade.get('pnl', 0) < 0]
        
        average_win = sum(winning_trades) / len(winning_trades) if winning_trades else 0
        average_loss = sum(losing_trades) / len(losing_trades) if losing_trades else 0
        
        # Tính toán expectancy
        expectancy = 0
        if average_loss < 0:  # Tránh chia cho 0
            expectancy = (win_rate * average_win + (1 - win_rate) * average_loss) / abs(average_loss)
            
        return {
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "average_win": average_win,
            "average_loss": average_loss,
            "expectancy": expectancy,
            "total_trades": len(recent_trades)
        }

class MonteCarloRiskAnalyzer:
    """Phân tích rủi ro sử dụng mô phỏng Monte Carlo"""
    
    def __init__(self, trade_history: List[Dict], default_risk: float = 1.0):
        """
        Khởi tạo Monte Carlo Risk Analyzer
        
        Args:
            trade_history (List[Dict]): Lịch sử giao dịch
            default_risk (float): % rủi ro mặc định
        """
        self.trade_history = trade_history
        self.default_risk = default_risk
        
    def analyze(self, confidence_level: float = 0.95, simulations: int = 1000, 
              sequence_length: int = 20, max_risk_limit: float = 2.0) -> float:
        """
        Thực hiện phân tích Monte Carlo và đề xuất % rủi ro
        
        Args:
            confidence_level (float): Mức độ tin cậy (0-1)
            simulations (int): Số lần mô phỏng
            sequence_length (int): Độ dài chuỗi giao dịch để mô phỏng
            max_risk_limit (float): Giới hạn % rủi ro tối đa
            
        Returns:
            float: % rủi ro đề xuất
        """
        if len(self.trade_history) < 30:
            logger.warning(f"Không đủ dữ liệu giao dịch ({len(self.trade_history)}/30) cho phân tích Monte Carlo")
            return self.default_risk
        
        logger.info(f"Bắt đầu phân tích Monte Carlo với {simulations} mô phỏng...")
        
        # Tính toán phân phối lợi nhuận/thua lỗ
        pnl_distribution = [trade.get('pnl_pct', 0) for trade in self.trade_history]
        
        # Mô phỏng Monte Carlo
        drawdowns = []
        for i in range(simulations):
            # Lấy mẫu ngẫu nhiên từ phân phối lợi nhuận
            sample = random.choices(pnl_distribution, k=sequence_length)
            # Tính toán đường cong vốn
            equity_curve = [100]  # Bắt đầu với 100 đơn vị
            for pnl in sample:
                equity_curve.append(equity_curve[-1] * (1 + pnl/100))
            
            # Tính drawdown tối đa
            max_dd = self._calculate_max_drawdown(equity_curve)
            drawdowns.append(max_dd)
            
            if i % 200 == 0:
                logger.debug(f"Đã hoàn thành {i}/{simulations} mô phỏng...")
        
        # Tính toán VaR (Value at Risk) tại mức độ tin cậy
        var = sorted(drawdowns)[int(simulations * confidence_level)]
        
        # Điều chỉnh % rủi ro để drawdown kỳ vọng <= max_acceptable_drawdown
        max_acceptable_drawdown = 20  # 20% drawdown tối đa có thể chấp nhận
        suggested_risk = self.default_risk * (max_acceptable_drawdown / var)
        
        logger.info(f"Kết quả Monte Carlo: VaR={var:.2f}%, Đề xuất % rủi ro={suggested_risk:.2f}%")
        
        # Giới hạn % rủi ro
        return max(0.1, min(suggested_risk, max_risk_limit))
    
    def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """
        Tính drawdown tối đa từ đường cong vốn
        
        Args:
            equity_curve (List[float]): Đường cong vốn
            
        Returns:
            float: Drawdown tối đa (%)
        """
        max_dd = 0
        peak = equity_curve[0]
        
        for value in equity_curve:
            if value > peak:
                peak = value
            
            dd = 100 * (peak - value) / peak
            max_dd = max(max_dd, dd)
        
        return max_dd
    
    def get_drawdown_distribution(self, simulations: int = 1000, sequence_length: int = 20) -> Dict:
        """
        Lấy phân phối drawdown từ các mô phỏng
        
        Args:
            simulations (int): Số lần mô phỏng
            sequence_length (int): Độ dài chuỗi giao dịch để mô phỏng
            
        Returns:
            Dict: Phân phối drawdown
        """
        if len(self.trade_history) < 30:
            logger.warning(f"Không đủ dữ liệu giao dịch ({len(self.trade_history)}/30) cho phân tích phân phối")
            return {"percentiles": {}, "drawdowns": []}
        
        # Tính toán phân phối lợi nhuận/thua lỗ
        pnl_distribution = [trade.get('pnl_pct', 0) for trade in self.trade_history]
        
        # Mô phỏng Monte Carlo
        drawdowns = []
        for _ in range(simulations):
            # Lấy mẫu ngẫu nhiên từ phân phối lợi nhuận
            sample = random.choices(pnl_distribution, k=sequence_length)
            # Tính toán đường cong vốn
            equity_curve = [100]
            for pnl in sample:
                equity_curve.append(equity_curve[-1] * (1 + pnl/100))
            
            # Tính drawdown tối đa
            max_dd = self._calculate_max_drawdown(equity_curve)
            drawdowns.append(max_dd)
        
        # Tính percentiles cho phân phối
        percentiles = {
            "50%": np.percentile(drawdowns, 50),
            "75%": np.percentile(drawdowns, 75),
            "90%": np.percentile(drawdowns, 90),
            "95%": np.percentile(drawdowns, 95),
            "99%": np.percentile(drawdowns, 99)
        }
        
        return {
            "percentiles": percentiles,
            "drawdowns": drawdowns
        }
    
    def get_risk_levels(self, max_acceptable_drawdown: float = 20.0, 
                        confidence_levels: List[float] = [0.90, 0.95, 0.99]) -> Dict:
        """
        Lấy các mức rủi ro tương ứng với các mức tin cậy khác nhau
        
        Args:
            max_acceptable_drawdown (float): Drawdown tối đa chấp nhận được (%)
            confidence_levels (List[float]): Các mức độ tin cậy cần kiểm tra
            
        Returns:
            Dict: Các mức rủi ro tương ứng
        """
        risk_levels = {}
        
        for conf_level in confidence_levels:
            risk = self.analyze(confidence_level=conf_level, 
                               simulations=1000, 
                               max_risk_limit=5.0)
            risk_levels[f"{int(conf_level*100)}%"] = risk
        
        return risk_levels

def create_enhanced_position_sizer(sizer_type: str, account_balance: float, **kwargs) -> Union[BasePositionSizer, PythagoreanPositionSizer]:
    """
    Factory function để tạo position sizer
    
    Args:
        sizer_type (str): Loại position sizer
        account_balance (float): Số dư tài khoản
        **kwargs: Các tham số khác
        
    Returns:
        Union[BasePositionSizer, PythagoreanPositionSizer]: Đối tượng position sizer
    """
    if sizer_type.lower() == 'pythagorean':
        return PythagoreanPositionSizer(
            trade_history=kwargs.get('trade_history', []),
            account_balance=account_balance,
            risk_percentage=kwargs.get('risk_percentage', 1.0),
            lookback_trades=kwargs.get('lookback_trades', 30)
        )
    else:
        # Import và sử dụng factory function từ module position_sizing
        from position_sizing import create_position_sizer
        return create_position_sizer(sizer_type, account_balance, **kwargs)

# Hàm test cho module
def test_position_sizing():
    """Kiểm tra các chức năng của module"""
    # Tạo dữ liệu test
    test_trade_history = [
        {'pnl': 100, 'pnl_pct': 2.5},
        {'pnl': -50, 'pnl_pct': -1.2},
        {'pnl': 80, 'pnl_pct': 1.8},
        {'pnl': 120, 'pnl_pct': 2.2},
        {'pnl': -40, 'pnl_pct': -0.9},
        {'pnl': 60, 'pnl_pct': 1.3},
        {'pnl': 90, 'pnl_pct': 2.0},
        {'pnl': -60, 'pnl_pct': -1.5},
        {'pnl': 70, 'pnl_pct': 1.6},
        {'pnl': 110, 'pnl_pct': 2.3},
    ]
    
    # Kiểm tra PythagoreanPositionSizer
    print("=== Kiểm tra PythagoreanPositionSizer ===")
    pythag_sizer = PythagoreanPositionSizer(
        trade_history=test_trade_history,
        account_balance=10000,
        risk_percentage=1.0
    )
    
    # Tính toán kích thước vị thế
    account_balance = 10000
    current_price = 50000
    entry_price = 50000
    stop_loss_price = 49000
    
    position_size = pythag_sizer.calculate_position_size(
        current_price=current_price,
        account_balance=account_balance,
        entry_price=entry_price,
        stop_loss_price=stop_loss_price
    )
    
    print(f"Kích thước vị thế: {position_size:.2f}")
    print(f"Win rate: {pythag_sizer.calculate_win_rate():.2f}")
    print(f"Profit factor: {pythag_sizer.calculate_profit_factor():.2f}")
    
    # Kiểm tra Monte Carlo Risk Analyzer
    print("\n=== Kiểm tra MonteCarloRiskAnalyzer ===")
    
    # Tạo 100 giao dịch mẫu
    extended_trade_history = []
    for i in range(10):
        for trade in test_trade_history:
            # Thêm nhiễu ngẫu nhiên
            noise = random.uniform(-0.5, 0.5)
            extended_trade_history.append({
                'pnl': trade['pnl'] * (1 + noise),
                'pnl_pct': trade['pnl_pct'] * (1 + noise)
            })
    
    mc_analyzer = MonteCarloRiskAnalyzer(
        trade_history=extended_trade_history,
        default_risk=1.0
    )
    
    risk_level = mc_analyzer.analyze(
        confidence_level=0.95,
        simulations=1000,
        sequence_length=20
    )
    
    print(f"Đề xuất mức rủi ro: {risk_level:.2f}%")
    
    # Kiểm tra các mức rủi ro khác nhau
    risk_levels = mc_analyzer.get_risk_levels()
    for level, risk in risk_levels.items():
        print(f"Mức tin cậy {level}: {risk:.2f}%")

if __name__ == "__main__":
    test_position_sizing()