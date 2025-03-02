"""
Module quản lý vị thế cho tài khoản nhỏ (Micro Position Sizing)

Module này cung cấp các công cụ để quản lý vị thế giao dịch cho tài khoản có vốn nhỏ
(100-200 USD) khi sử dụng đòn bẩy cao (x10-x20) trên thị trường Futures.
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("micro_position_sizing")

class MicroPositionSizer:
    """Quản lý kích thước vị thế cho tài khoản nhỏ với đòn bẩy cao"""
    
    def __init__(self, 
                initial_balance: float = 100.0, 
                max_leverage: int = 20,
                max_risk_per_trade_percent: float = 2.0,
                max_account_risk_percent: float = 15.0,
                adaptive_sizing: bool = True,
                trade_history: List[Dict] = None):
        """
        Khởi tạo bộ quản lý vị thế cho tài khoản nhỏ
        
        Args:
            initial_balance (float): Số dư ban đầu (USD)
            max_leverage (int): Đòn bẩy tối đa (10-20)
            max_risk_per_trade_percent (float): Rủi ro tối đa cho mỗi giao dịch (%)
            max_account_risk_percent (float): Rủi ro tối đa cho tài khoản (%)
            adaptive_sizing (bool): Sử dụng điều chỉnh vị thế thích ứng
            trade_history (List[Dict]): Lịch sử giao dịch
        """
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.max_leverage = max_leverage
        self.max_risk_per_trade_percent = max_risk_per_trade_percent
        self.max_account_risk_percent = max_account_risk_percent
        self.adaptive_sizing = adaptive_sizing
        self.trade_history = trade_history or []
        
        # Thông số thêm cho giao dịch tài khoản nhỏ
        self.min_position_size_usd = 5.0  # Vị thế tối thiểu trong USD 
        self.min_distance_to_liquidation_percent = 20.0  # Khoảng cách tối thiểu đến điểm thanh lý
        
        # Theo dõi vị thế hiện tại
        self.open_positions = []
        
        logger.info(f"Khởi tạo MicroPositionSizer: Balance=${initial_balance}, Leverage=x{max_leverage}, "
                   f"Max Risk/Trade={max_risk_per_trade_percent}%, Max Account Risk={max_account_risk_percent}%")
    
    def calculate_position_size(self, 
                              entry_price: float, 
                              stop_loss_price: float, 
                              leverage: int = None,
                              market_volatility: float = None) -> Tuple[float, Dict]:
        """
        Tính toán kích thước vị thế tối ưu cho tài khoản nhỏ
        
        Args:
            entry_price (float): Giá dự kiến vào lệnh
            stop_loss_price (float): Giá dự kiến stop loss
            leverage (int, optional): Đòn bẩy cụ thể, nếu không cung cấp sẽ sử dụng max_leverage
            market_volatility (float, optional): Độ biến động của thị trường (%)
            
        Returns:
            Tuple[float, Dict]: (Kích thước vị thế, Thông tin chi tiết)
        """
        # Sử dụng đòn bẩy tối đa nếu không được chỉ định
        if leverage is None:
            leverage = self.max_leverage
        else:
            # Đảm bảo đòn bẩy không vượt quá giới hạn
            leverage = min(leverage, self.max_leverage)
        
        # Tính khoảng cách % giữa entry và stop loss
        if entry_price > stop_loss_price:  # Vị thế Long
            side = "BUY"
            stop_distance_percent = (entry_price - stop_loss_price) / entry_price * 100
        else:  # Vị thế Short
            side = "SELL"
            stop_distance_percent = (stop_loss_price - entry_price) / entry_price * 100
        
        # Điều chỉnh rủi ro dựa trên độ biến động thị trường nếu có
        risk_percent = self.max_risk_per_trade_percent
        if market_volatility is not None and self.adaptive_sizing:
            # Giảm rủi ro khi biến động tăng, tăng rủi ro khi biến động giảm
            volatility_factor = 1.0 - (market_volatility / 10.0)  # Ví dụ: biến động 5% -> factor = 0.5
            risk_percent = risk_percent * max(0.3, min(volatility_factor, 1.5))
            logger.info(f"Điều chỉnh rủi ro theo biến động: {self.max_risk_per_trade_percent}% -> {risk_percent:.2f}%")
        
        # Tính toán số tiền rủi ro dựa trên số dư hiện tại
        risk_amount = self.current_balance * (risk_percent / 100)
        
        # Tính toán kích thước vị thế (USD)
        # Formula: position_size = (risk_amount / stop_distance_percent) * 100 * leverage
        position_size_usd = (risk_amount / stop_distance_percent) * 100 * leverage
        
        # Kiểm tra kích thước vị thế tối thiểu
        if position_size_usd < self.min_position_size_usd:
            position_size_usd = max(self.min_position_size_usd, position_size_usd)
            logger.info(f"Điều chỉnh kích thước vị thế lên mức tối thiểu: ${position_size_usd:.2f}")
        
        # Tính margin sử dụng
        margin_used = position_size_usd / leverage
        
        # Kiểm tra khoảng cách đến điểm thanh lý (liquidation)
        liquidation_distance = 100 / leverage  # % thay đổi giá gây thanh lý
        
        if stop_distance_percent > liquidation_distance * (1 - self.min_distance_to_liquidation_percent/100):
            # Stop loss quá gần điểm thanh lý, điều chỉnh lại
            old_position_size = position_size_usd
            position_size_usd = position_size_usd * (liquidation_distance * (1 - self.min_distance_to_liquidation_percent/100) / stop_distance_percent)
            logger.warning(f"Stop loss ({stop_distance_percent:.2f}%) quá gần điểm thanh lý ({liquidation_distance:.2f}%). "
                          f"Điều chỉnh kích thước vị thế: ${old_position_size:.2f} -> ${position_size_usd:.2f}")
        
        # Số lượng Bitcoin để giao dịch
        quantity = position_size_usd / entry_price
        
        # Tính toán rủi ro thực tế
        actual_risk_percent = (risk_amount / self.current_balance) * 100
        
        # Tạo thông tin chi tiết
        details = {
            'side': side,
            'entry_price': entry_price,
            'stop_loss_price': stop_loss_price,
            'stop_distance_percent': stop_distance_percent,
            'leverage': leverage,
            'position_size_usd': position_size_usd,
            'margin_used': margin_used,
            'quantity': quantity,
            'risk_amount': risk_amount,
            'risk_percent': actual_risk_percent,
            'liquidation_distance_percent': liquidation_distance,
            'liquidation_price_estimate': self._calculate_liquidation_price(entry_price, leverage, side)
        }
        
        logger.info(f"Vị thế được tính: {side}, Size=${position_size_usd:.2f}, "
                   f"Quantity={quantity:.6f}, Leverage=x{leverage}, "
                   f"Risk=${risk_amount:.2f} ({actual_risk_percent:.2f}%)")
        
        return position_size_usd, details
    
    def _calculate_liquidation_price(self, entry_price: float, leverage: int, side: str) -> float:
        """
        Tính toán giá thanh lý dự kiến
        
        Args:
            entry_price (float): Giá vào lệnh
            leverage (int): Đòn bẩy
            side (str): Hướng vị thế ("BUY" hoặc "SELL")
            
        Returns:
            float: Giá thanh lý dự kiến
        """
        # Công thức đơn giản: Liq Price = Entry Price +/- Entry Price / Leverage
        # (công thức thực tế phức tạp hơn do phí, tài sản ký quỹ, v.v.)
        maintenance_margin = 0.5  # % margin duy trì (giả định)
        
        if side == "BUY":
            # Long position: Liquidation price goes down
            liq_price = entry_price * (1 - (1 / leverage) + maintenance_margin / 100)
        else:
            # Short position: Liquidation price goes up
            liq_price = entry_price * (1 + (1 / leverage) - maintenance_margin / 100)
            
        return liq_price
    
    def update_balance(self, new_balance: float) -> None:
        """
        Cập nhật số dư tài khoản
        
        Args:
            new_balance (float): Số dư mới
        """
        old_balance = self.current_balance
        self.current_balance = new_balance
        
        change_percent = ((new_balance - old_balance) / old_balance) * 100 if old_balance > 0 else 0
        logger.info(f"Cập nhật số dư: ${old_balance:.2f} -> ${new_balance:.2f} ({change_percent:+.2f}%)")
    
    def check_account_risk(self) -> Tuple[bool, float]:
        """
        Kiểm tra tổng rủi ro hiện tại của tài khoản
        
        Returns:
            Tuple[bool, float]: (Có vượt quá giới hạn không, Tổng % rủi ro)
        """
        # Tính tổng rủi ro từ tất cả vị thế mở
        total_risk_amount = sum(position.get('risk_amount', 0) for position in self.open_positions)
        total_risk_percent = (total_risk_amount / self.current_balance) * 100 if self.current_balance > 0 else 0
        
        exceeds_limit = total_risk_percent > self.max_account_risk_percent
        
        if exceeds_limit:
            logger.warning(f"Tổng rủi ro tài khoản ({total_risk_percent:.2f}%) vượt quá giới hạn ({self.max_account_risk_percent}%)")
        
        return exceeds_limit, total_risk_percent
    
    def add_position(self, position_details: Dict) -> int:
        """
        Thêm vị thế mới vào danh sách theo dõi
        
        Args:
            position_details (Dict): Thông tin chi tiết vị thế
            
        Returns:
            int: ID của vị thế
        """
        position_id = len(self.open_positions)
        position_details['position_id'] = position_id
        position_details['open_time'] = datetime.now()
        
        self.open_positions.append(position_details)
        
        # Kiểm tra tổng rủi ro
        self.check_account_risk()
        
        return position_id
    
    def close_position(self, position_id: int, exit_price: float, pnl: float) -> Dict:
        """
        Đóng vị thế và cập nhật số dư
        
        Args:
            position_id (int): ID của vị thế
            exit_price (float): Giá thoát
            pnl (float): Lợi nhuận/thua lỗ
            
        Returns:
            Dict: Thông tin vị thế đã đóng
        """
        # Tìm vị thế trong danh sách
        position = None
        for pos in self.open_positions:
            if pos.get('position_id') == position_id:
                position = pos
                break
                
        if not position:
            logger.error(f"Không tìm thấy vị thế với ID {position_id}")
            return {}
        
        # Cập nhật thông tin vị thế
        position['exit_price'] = exit_price
        position['exit_time'] = datetime.now()
        position['pnl'] = pnl
        
        # Tính % lợi nhuận
        if 'position_size_usd' in position and position['position_size_usd'] > 0:
            position['pnl_percent'] = (pnl / position['position_size_usd']) * 100
        else:
            position['pnl_percent'] = 0
        
        # Cập nhật số dư
        self.update_balance(self.current_balance + pnl)
        
        # Ghi lại lịch sử giao dịch
        self.trade_history.append(position.copy())
        
        # Xóa khỏi danh sách vị thế mở
        self.open_positions = [pos for pos in self.open_positions if pos.get('position_id') != position_id]
        
        logger.info(f"Đóng vị thế #{position_id}: {position['side']}, P&L=${pnl:.2f} ({position.get('pnl_percent', 0):.2f}%)")
        
        return position
    
    def get_optimal_leverage(self, 
                           market_volatility: float = None, 
                           market_regime: str = None) -> int:
        """
        Tính toán đòn bẩy tối ưu dựa trên điều kiện thị trường
        
        Args:
            market_volatility (float, optional): Độ biến động thị trường (%)
            market_regime (str, optional): Chế độ thị trường ('trending', 'ranging', 'volatile', 'quiet')
            
        Returns:
            int: Đòn bẩy tối ưu
        """
        # Đòn bẩy mặc định
        optimal_leverage = self.max_leverage
        
        # Điều chỉnh theo độ biến động
        if market_volatility is not None:
            # Giảm đòn bẩy khi biến động tăng
            if market_volatility < 1.0:  # Biến động thấp
                volatility_factor = 1.0
            elif market_volatility < 2.0:  # Biến động trung bình
                volatility_factor = 0.8
            elif market_volatility < 4.0:  # Biến động cao
                volatility_factor = 0.6
            else:  # Biến động rất cao
                volatility_factor = 0.4
                
            optimal_leverage = int(self.max_leverage * volatility_factor)
        
        # Điều chỉnh theo chế độ thị trường
        if market_regime is not None:
            regime_factor = 1.0
            
            if market_regime == 'trending':
                regime_factor = 1.0  # Không thay đổi trong xu hướng
            elif market_regime == 'ranging':
                regime_factor = 0.7  # Giảm đòn bẩy trong thị trường đi ngang
            elif market_regime == 'volatile':
                regime_factor = 0.5  # Giảm mạnh đòn bẩy trong thị trường biến động
            elif market_regime == 'quiet':
                regime_factor = 0.8  # Giảm nhẹ đòn bẩy trong thị trường yên tĩnh
                
            # Áp dụng điều chỉnh nếu chưa có điều chỉnh từ độ biến động
            if market_volatility is None:
                optimal_leverage = int(self.max_leverage * regime_factor)
            else:
                # Kết hợp cả hai yếu tố
                optimal_leverage = min(optimal_leverage, int(self.max_leverage * regime_factor))
        
        # Đảm bảo đòn bẩy tối thiểu là 1
        optimal_leverage = max(1, optimal_leverage)
        
        logger.info(f"Đòn bẩy tối ưu được tính: x{optimal_leverage} "
                   f"(Volatility: {market_volatility}, Regime: {market_regime})")
        
        return optimal_leverage
    
    def calculate_risk_reward_ratio(self, entry_price: float, stop_loss: float, take_profit: float) -> float:
        """
        Tính tỷ lệ risk/reward
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss (float): Giá stop loss
            take_profit (float): Giá take profit
            
        Returns:
            float: Tỷ lệ risk/reward
        """
        if entry_price > stop_loss:  # Long position
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
        else:  # Short position
            risk = stop_loss - entry_price
            reward = entry_price - take_profit
            
        if risk <= 0 or reward <= 0:
            return 0
            
        return reward / risk
    
    def adjust_position_for_small_account(self, position_size_usd: float, entry_price: float) -> float:
        """
        Điều chỉnh kích thước vị thế cho tài khoản nhỏ
        
        Args:
            position_size_usd (float): Kích thước vị thế theo USD
            entry_price (float): Giá vào lệnh
            
        Returns:
            float: Kích thước vị thế điều chỉnh
        """
        # Đối với tài khoản nhỏ, chúng ta nên đảm bảo margin sử dụng không quá 50% số dư
        # để tránh bị thanh lý và có đệm cho những biến động bất ngờ
        max_margin_usage = self.current_balance * 0.5
        margin_usage = position_size_usd / self.max_leverage
        
        if margin_usage > max_margin_usage:
            old_size = position_size_usd
            # Điều chỉnh position size để margin không vượt quá 50% số dư
            position_size_usd = max_margin_usage * self.max_leverage
            logger.warning(f"Kích thước vị thế quá lớn, điều chỉnh: ${old_size:.2f} -> ${position_size_usd:.2f}")
        
        # Đảm bảo kích thước vị thế là bội số của giá trị contract tối thiểu (ví dụ 0.001 BTC)
        contract_size = 0.001  # Kích thước tối thiểu của contract (ví dụ: 0.001 BTC)
        quantity = position_size_usd / entry_price
        
        # Làm tròn xuống bội số của contract_size
        adjusted_quantity = int(quantity / contract_size) * contract_size
        adjusted_position_size = adjusted_quantity * entry_price
        
        if adjusted_position_size != position_size_usd:
            logger.info(f"Điều chỉnh kích thước vị thế để phù hợp với kích thước contract: "
                       f"${position_size_usd:.2f} -> ${adjusted_position_size:.2f}")
        
        return adjusted_position_size