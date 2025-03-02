"""
Module quản lý rủi ro cho giao dịch đòn bẩy cao (Leverage Risk Manager)

Module này cung cấp các công cụ để quản lý rủi ro khi giao dịch với đòn bẩy cao (x10-x20)
trên thị trường Futures, đặc biệt cho các tài khoản có vốn nhỏ (100-200 USD).
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("leverage_risk_manager")

class LeverageRiskManager:
    """Quản lý rủi ro cho giao dịch đòn bẩy cao"""
    
    def __init__(self, 
                initial_balance: float = 100.0,
                max_leverage: int = 20,
                max_positions: int = 3,
                max_risk_per_trade: float = 2.0,
                max_account_risk: float = 15.0,
                min_distance_to_liquidation: float = 20.0):
        """
        Khởi tạo quản lý rủi ro cho đòn bẩy cao
        
        Args:
            initial_balance (float): Số dư ban đầu (USD)
            max_leverage (int): Đòn bẩy tối đa
            max_positions (int): Số vị thế đồng thời tối đa
            max_risk_per_trade (float): Rủi ro tối đa cho mỗi giao dịch (%)
            max_account_risk (float): Rủi ro tối đa cho tài khoản (%)
            min_distance_to_liquidation (float): Khoảng cách tối thiểu đến điểm thanh lý (%)
        """
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.max_leverage = max_leverage
        self.max_positions = max_positions
        self.max_risk_per_trade = max_risk_per_trade
        self.max_account_risk = max_account_risk
        self.min_distance_to_liquidation = min_distance_to_liquidation
        
        # Theo dõi các vị thế hiện tại
        self.open_positions = []
        
        # Lịch sử rủi ro
        self.risk_history = []
        
        logger.info(f"Khởi tạo LeverageRiskManager: Balance=${initial_balance}, "
                   f"MaxLeverage=x{max_leverage}, MaxPositions={max_positions}, "
                   f"MaxRisk/Trade={max_risk_per_trade}%, MaxAccountRisk={max_account_risk}%")
    
    def calculate_optimal_leverage(self, 
                                entry_price: float, 
                                stop_loss: float, 
                                market_volatility: float,
                                market_regime: str) -> Tuple[int, Dict]:
        """
        Tính toán đòn bẩy tối ưu dựa trên các điều kiện thị trường
        
        Args:
            entry_price (float): Giá dự kiến vào lệnh
            stop_loss (float): Giá dự kiến stop loss
            market_volatility (float): Độ biến động thị trường (%)
            market_regime (str): Chế độ thị trường ('trending', 'ranging', 'volatile', 'quiet')
            
        Returns:
            Tuple[int, Dict]: (Đòn bẩy tối ưu, Chi tiết điều chỉnh)
        """
        # Tính % chênh lệch từ entry đến stop loss
        if entry_price > stop_loss:  # Long position
            stop_distance_percent = (entry_price - stop_loss) / entry_price * 100
        else:  # Short position
            stop_distance_percent = (stop_loss - entry_price) / entry_price * 100
        
        # Đòn bẩy tối đa ban đầu
        max_lev = self.max_leverage
        
        # Điều chỉnh 1: Đảm bảo khoảng cách an toàn đến điểm thanh lý
        # Liquidation xảy ra khi giá thay đổi ~ 100% / leverage
        safe_lev_for_liquidation = int(100 / (stop_distance_percent / (1 - self.min_distance_to_liquidation/100)))
        
        # Điều chỉnh 2: Dựa trên biến động thị trường
        volatility_factor = 1.0
        if market_volatility < 1.0:  # Biến động rất thấp
            volatility_factor = 1.0
        elif market_volatility < 2.0:  # Biến động thấp
            volatility_factor = 0.8
        elif market_volatility < 4.0:  # Biến động trung bình
            volatility_factor = 0.6
        elif market_volatility < 6.0:  # Biến động cao
            volatility_factor = 0.4
        else:  # Biến động rất cao
            volatility_factor = 0.3
            
        volatility_adjusted_lev = int(max_lev * volatility_factor)
        
        # Điều chỉnh 3: Dựa trên chế độ thị trường
        regime_factor = 1.0
        if market_regime == 'trending':
            regime_factor = 0.8  # Giảm nhẹ trong xu hướng để đảm bảo an toàn
        elif market_regime == 'ranging':
            regime_factor = 0.6  # Giảm đáng kể trong thị trường đi ngang
        elif market_regime == 'volatile':
            regime_factor = 0.4  # Giảm mạnh trong thị trường biến động
        elif market_regime == 'quiet':
            regime_factor = 0.9  # Giảm ít trong thị trường yên tĩnh
            
        regime_adjusted_lev = int(max_lev * regime_factor)
        
        # Điều chỉnh 4: Dựa trên số lượng vị thế mở
        position_count = len(self.open_positions)
        position_factor = 1.0 - (position_count * 0.2)  # Mỗi vị thế mở giảm 20% đòn bẩy
        position_factor = max(0.4, position_factor)  # Giới hạn giảm tối đa 60%
        
        position_adjusted_lev = int(max_lev * position_factor)
        
        # Kết hợp tất cả các điều chỉnh (lấy giá trị thấp nhất)
        optimal_leverage = min(
            max_lev,
            safe_lev_for_liquidation,
            volatility_adjusted_lev,
            regime_adjusted_lev,
            position_adjusted_lev
        )
        
        # Đảm bảo leverage tối thiểu
        optimal_leverage = max(1, optimal_leverage)
        
        # Chi tiết điều chỉnh
        details = {
            'max_leverage': max_lev,
            'stop_distance_percent': stop_distance_percent,
            'safe_leverage_for_liquidation': safe_lev_for_liquidation,
            'volatility_adjustment': {
                'factor': volatility_factor,
                'adjusted_leverage': volatility_adjusted_lev
            },
            'regime_adjustment': {
                'factor': regime_factor,
                'adjusted_leverage': regime_adjusted_lev
            },
            'position_adjustment': {
                'factor': position_factor,
                'adjusted_leverage': position_adjusted_lev
            },
            'final_optimal_leverage': optimal_leverage
        }
        
        logger.info(f"Đòn bẩy tối ưu: x{optimal_leverage} (Max: x{max_lev}, "
                   f"StopDistance: {stop_distance_percent:.2f}%, "
                   f"Volatility: {market_volatility:.2f}%, Regime: {market_regime})")
        
        return optimal_leverage, details
    
    def calculate_position_size(self, 
                              entry_price: float, 
                              stop_loss: float, 
                              leverage: int) -> Tuple[float, Dict]:
        """
        Tính toán kích thước vị thế tối ưu
        
        Args:
            entry_price (float): Giá dự kiến vào lệnh
            stop_loss (float): Giá dự kiến stop loss
            leverage (int): Đòn bẩy sử dụng
            
        Returns:
            Tuple[float, Dict]: (Kích thước vị thế, Thông tin chi tiết)
        """
        # Tính % chênh lệch từ entry đến stop loss
        if entry_price > stop_loss:  # Long position
            stop_distance_percent = (entry_price - stop_loss) / entry_price * 100
            side = "BUY"
        else:  # Short position
            stop_distance_percent = (stop_loss - entry_price) / entry_price * 100
            side = "SELL"
        
        # Tính toán số tiền rủi ro
        risk_amount = self.current_balance * (self.max_risk_per_trade / 100)
        
        # Tính toán kích thước vị thế (USD)
        position_size_usd = (risk_amount / stop_distance_percent) * 100 * leverage
        
        # Kiểm tra xem có đủ số dư không
        required_margin = position_size_usd / leverage
        if required_margin > self.current_balance:
            # Điều chỉnh kích thước vị thế dựa trên số dư khả dụng
            position_size_usd = self.current_balance * leverage * 0.95  # Sử dụng 95% số dư
        
        # Tính số lượng Bitcoin
        quantity = position_size_usd / entry_price
        
        # Thông tin chi tiết
        details = {
            'side': side,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'stop_distance_percent': stop_distance_percent,
            'risk_amount': risk_amount,
            'risk_percent': self.max_risk_per_trade,
            'position_size_usd': position_size_usd,
            'quantity': quantity,
            'margin_used': position_size_usd / leverage,
            'leverage': leverage
        }
        
        # Tính điểm thanh lý dự kiến
        if side == "BUY":
            liquidation_price = entry_price * (1 - (1 / leverage) + 0.004)  # 0.4% duy trì margin
            details['liquidation_price'] = liquidation_price
            
            # Kiểm tra khoảng cách đến điểm thanh lý
            liquidation_distance = (entry_price - liquidation_price) / entry_price * 100
            details['liquidation_distance_percent'] = liquidation_distance
            
        else:  # SELL
            liquidation_price = entry_price * (1 + (1 / leverage) - 0.004)  # 0.4% duy trì margin
            details['liquidation_price'] = liquidation_price
            
            # Kiểm tra khoảng cách đến điểm thanh lý
            liquidation_distance = (liquidation_price - entry_price) / entry_price * 100
            details['liquidation_distance_percent'] = liquidation_distance
        
        # Kiểm tra xem stop loss có quá gần điểm thanh lý không
        if details['liquidation_distance_percent'] < self.min_distance_to_liquidation * 1.1:
            logger.warning(f"Stop loss quá gần điểm thanh lý: {details['liquidation_distance_percent']:.2f}% < "
                         f"{self.min_distance_to_liquidation * 1.1:.2f}%")
            
            # Điều chỉnh kích thước vị thế
            adjustment_factor = (details['liquidation_distance_percent'] / (self.min_distance_to_liquidation * 1.1))
            position_size_usd *= adjustment_factor
            
            # Cập nhật lại thông tin
            details['position_size_usd'] = position_size_usd
            details['quantity'] = position_size_usd / entry_price
            details['margin_used'] = position_size_usd / leverage
            
            logger.info(f"Điều chỉnh kích thước vị thế: ${position_size_usd:.2f}, "
                       f"Quantity={details['quantity']:.8f}")
        
        return position_size_usd, details
    
    def validate_trade(self, 
                     entry_price: float, 
                     stop_loss: float, 
                     take_profit: float, 
                     leverage: int, 
                     side: str) -> Tuple[bool, Dict]:
        """
        Xác thực giao dịch dựa trên các tiêu chí rủi ro
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss (float): Giá stop loss
            take_profit (float): Giá take profit
            leverage (int): Đòn bẩy sử dụng
            side (str): Hướng giao dịch ("BUY" hoặc "SELL")
            
        Returns:
            Tuple[bool, Dict]: (Hợp lệ hay không, Thông tin xác thực)
        """
        validation = {'is_valid': True, 'messages': []}
        
        # Kiểm tra số vị thế đã mở
        if len(self.open_positions) >= self.max_positions:
            validation['is_valid'] = False
            validation['messages'].append(f"Đã đạt số vị thế tối đa ({self.max_positions})")
        
        # Tính Risk/Reward ratio
        if side == "BUY":
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
        else:  # SELL
            risk = stop_loss - entry_price
            reward = entry_price - take_profit
            
        if risk <= 0:
            validation['is_valid'] = False
            validation['messages'].append("Stop loss không hợp lệ")
        
        if reward <= 0:
            validation['is_valid'] = False
            validation['messages'].append("Take profit không hợp lệ")
            
        # Tỷ lệ Risk/Reward tối thiểu là 1:1.5
        if risk > 0 and reward > 0:
            rr_ratio = reward / risk
            validation['risk_reward_ratio'] = rr_ratio
            
            if rr_ratio < 1.5:
                validation['is_valid'] = False
                validation['messages'].append(f"Tỷ lệ Risk/Reward ({rr_ratio:.2f}) dưới mức tối thiểu (1.5)")
                
        # Tính toán rủi ro của vị thế
        _, position_details = self.calculate_position_size(entry_price, stop_loss, leverage)
        position_risk = position_details['risk_amount']
        
        # Tính tổng rủi ro tài khoản hiện tại
        total_risk = sum(pos.get('risk_amount', 0) for pos in self.open_positions)
        
        # Thêm rủi ro của vị thế mới
        new_total_risk = total_risk + position_risk
        new_total_risk_percent = (new_total_risk / self.current_balance) * 100
        
        validation['account_risk_percent'] = new_total_risk_percent
        
        # Kiểm tra rủi ro tài khoản
        if new_total_risk_percent > self.max_account_risk:
            validation['is_valid'] = False
            validation['messages'].append(
                f"Tổng rủi ro tài khoản ({new_total_risk_percent:.2f}%) vượt quá giới hạn ({self.max_account_risk}%)")
        
        # Kiểm tra khoảng cách đến điểm thanh lý
        if side == "BUY":
            liquidation_price = entry_price * (1 - (1 / leverage) + 0.004)
            liquidation_distance = (entry_price - liquidation_price) / entry_price * 100
        else:  # SELL
            liquidation_price = entry_price * (1 + (1 / leverage) - 0.004)
            liquidation_distance = (liquidation_price - entry_price) / entry_price * 100
            
        validation['liquidation_price'] = liquidation_price
        validation['liquidation_distance_percent'] = liquidation_distance
        
        # Stop loss không được quá gần điểm thanh lý
        stop_to_liquidation_buffer = 5.0  # %
        
        if side == "BUY":
            stop_to_liquidation = (stop_loss - liquidation_price) / liquidation_price * 100
        else:  # SELL
            stop_to_liquidation = (liquidation_price - stop_loss) / stop_loss * 100
            
        validation['stop_to_liquidation_percent'] = stop_to_liquidation
        
        if stop_to_liquidation < stop_to_liquidation_buffer:
            validation['is_valid'] = False
            validation['messages'].append(
                f"Stop loss quá gần điểm thanh lý ({stop_to_liquidation:.2f}% < {stop_to_liquidation_buffer}%)")
                
        return validation['is_valid'], validation
    
    def add_position(self, 
                    entry_price: float, 
                    stop_loss: float, 
                    take_profit: float, 
                    leverage: int, 
                    side: str, 
                    position_size: float = None) -> Tuple[bool, Dict]:
        """
        Thêm vị thế mới vào danh sách theo dõi
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss (float): Giá stop loss
            take_profit (float): Giá take profit
            leverage (int): Đòn bẩy sử dụng
            side (str): Hướng giao dịch ("BUY" hoặc "SELL")
            position_size (float, optional): Kích thước vị thế
            
        Returns:
            Tuple[bool, Dict]: (Thành công hay không, Thông tin vị thế)
        """
        # Xác thực giao dịch
        is_valid, validation = self.validate_trade(entry_price, stop_loss, take_profit, leverage, side)
        
        if not is_valid:
            logger.warning(f"Không thể mở vị thế: {validation['messages']}")
            return False, validation
        
        # Tính kích thước vị thế nếu chưa được cung cấp
        if position_size is None:
            position_size, position_details = self.calculate_position_size(entry_price, stop_loss, leverage)
        else:
            # Tính toán các thông số khác
            if entry_price > stop_loss:  # Long position
                stop_distance_percent = (entry_price - stop_loss) / entry_price * 100
            else:  # Short position
                stop_distance_percent = (stop_loss - entry_price) / entry_price * 100
                
            risk_amount = (position_size / leverage) * (stop_distance_percent / 100)
            
            position_details = {
                'side': side,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'leverage': leverage,
                'position_size_usd': position_size,
                'quantity': position_size / entry_price,
                'margin_used': position_size / leverage,
                'risk_amount': risk_amount,
                'risk_percent': (risk_amount / self.current_balance) * 100,
                'stop_distance_percent': stop_distance_percent
            }
            
            if side == "BUY":
                liquidation_price = entry_price * (1 - (1 / leverage) + 0.004)
                position_details['liquidation_price'] = liquidation_price
                position_details['liquidation_distance_percent'] = (entry_price - liquidation_price) / entry_price * 100
            else:  # SELL
                liquidation_price = entry_price * (1 + (1 / leverage) - 0.004)
                position_details['liquidation_price'] = liquidation_price
                position_details['liquidation_distance_percent'] = (liquidation_price - entry_price) / entry_price * 100
        
        # Thêm các thông tin khác
        position_details['open_time'] = datetime.now()
        position_details['position_id'] = len(self.open_positions)
        position_details['take_profit'] = take_profit
        
        # Lưu vị thế
        self.open_positions.append(position_details)
        
        # Cập nhật lịch sử rủi ro
        self.risk_history.append({
            'timestamp': datetime.now(),
            'account_balance': self.current_balance,
            'risk_amount': position_details['risk_amount'],
            'risk_percent': position_details['risk_percent'],
            'position_size': position_size,
            'leverage': leverage
        })
        
        logger.info(f"Đã mở vị thế {side} #{position_details['position_id']}: "
                   f"Size=${position_size:.2f}, Leverage=x{leverage}, "
                   f"Risk=${position_details['risk_amount']:.2f} ({position_details['risk_percent']:.2f}%)")
        
        return True, position_details
    
    def update_position(self, 
                       position_id: int, 
                       current_price: float, 
                       trailing_stop_percent: float = None) -> Dict:
        """
        Cập nhật vị thế với giá hiện tại và kiểm tra các điều kiện đóng vị thế
        
        Args:
            position_id (int): ID của vị thế
            current_price (float): Giá hiện tại
            trailing_stop_percent (float, optional): Phần trăm trailing stop
            
        Returns:
            Dict: Trạng thái vị thế
        """
        # Tìm vị thế
        position = None
        for pos in self.open_positions:
            if pos['position_id'] == position_id:
                position = pos
                break
                
        if not position:
            logger.error(f"Không tìm thấy vị thế với ID {position_id}")
            return {'status': 'error', 'message': f"Không tìm thấy vị thế với ID {position_id}"}
        
        # Tính P&L hiện tại
        if position['side'] == "BUY":
            pnl = (current_price - position['entry_price']) * position['quantity']
            pnl_percent = (current_price - position['entry_price']) / position['entry_price'] * 100 * position['leverage']
        else:  # SELL
            pnl = (position['entry_price'] - current_price) * position['quantity']
            pnl_percent = (position['entry_price'] - current_price) / position['entry_price'] * 100 * position['leverage']
            
        # Cập nhật trạng thái
        status = {
            'position_id': position_id,
            'side': position['side'],
            'entry_price': position['entry_price'],
            'current_price': current_price,
            'stop_loss': position['stop_loss'],
            'take_profit': position['take_profit'],
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'status': 'open'
        }
        
        # Kiểm tra nếu đã đạt take profit
        if (position['side'] == "BUY" and current_price >= position['take_profit']) or \
           (position['side'] == "SELL" and current_price <= position['take_profit']):
            status['status'] = 'close'
            status['close_reason'] = 'take_profit'
            
        # Kiểm tra nếu đã chạm stop loss
        elif (position['side'] == "BUY" and current_price <= position['stop_loss']) or \
             (position['side'] == "SELL" and current_price >= position['stop_loss']):
            status['status'] = 'close'
            status['close_reason'] = 'stop_loss'
            
        # Kiểm tra và cập nhật trailing stop nếu cần
        if trailing_stop_percent and status['status'] == 'open':
            # Chỉ áp dụng trailing stop khi đã có lợi nhuận
            if pnl > 0:
                if 'trailing_active' not in position:
                    position['trailing_active'] = False
                    position['trailing_price'] = None
                
                # Tính giá kích hoạt trailing stop
                if not position['trailing_active']:
                    if position['side'] == "BUY":
                        activation_price = position['entry_price'] * (1 + trailing_stop_percent / 100)
                        if current_price >= activation_price:
                            position['trailing_active'] = True
                            position['trailing_price'] = current_price * (1 - trailing_stop_percent / 100)
                    else:  # SELL
                        activation_price = position['entry_price'] * (1 - trailing_stop_percent / 100)
                        if current_price <= activation_price:
                            position['trailing_active'] = True
                            position['trailing_price'] = current_price * (1 + trailing_stop_percent / 100)
                
                # Cập nhật trailing stop nếu đã kích hoạt
                if position['trailing_active']:
                    if position['side'] == "BUY":
                        # Cập nhật trailing stop nếu giá tăng
                        new_trailing_price = current_price * (1 - trailing_stop_percent / 100)
                        if new_trailing_price > position['trailing_price']:
                            position['trailing_price'] = new_trailing_price
                            
                        # Kiểm tra nếu giá chạm trailing stop
                        if current_price <= position['trailing_price']:
                            status['status'] = 'close'
                            status['close_reason'] = 'trailing_stop'
                            status['trailing_price'] = position['trailing_price']
                    else:  # SELL
                        # Cập nhật trailing stop nếu giá giảm
                        new_trailing_price = current_price * (1 + trailing_stop_percent / 100)
                        if new_trailing_price < position['trailing_price']:
                            position['trailing_price'] = new_trailing_price
                            
                        # Kiểm tra nếu giá chạm trailing stop
                        if current_price >= position['trailing_price']:
                            status['status'] = 'close'
                            status['close_reason'] = 'trailing_stop'
                            status['trailing_price'] = position['trailing_price']
                            
                status['trailing_active'] = position['trailing_active']
                status['trailing_price'] = position['trailing_price']
        
        return status
    
    def close_position(self, position_id: int, exit_price: float, exit_reason: str = 'manual') -> Tuple[bool, Dict]:
        """
        Đóng vị thế
        
        Args:
            position_id (int): ID của vị thế
            exit_price (float): Giá thoát
            exit_reason (str): Lý do thoát ('take_profit', 'stop_loss', 'trailing_stop', 'manual')
            
        Returns:
            Tuple[bool, Dict]: (Thành công hay không, Thông tin vị thế đã đóng)
        """
        # Tìm vị thế
        position = None
        position_index = -1
        
        for i, pos in enumerate(self.open_positions):
            if pos['position_id'] == position_id:
                position = pos
                position_index = i
                break
                
        if not position:
            logger.error(f"Không tìm thấy vị thế với ID {position_id}")
            return False, {'status': 'error', 'message': f"Không tìm thấy vị thế với ID {position_id}"}
        
        # Tính P&L
        if position['side'] == "BUY":
            pnl = (exit_price - position['entry_price']) * position['quantity']
            pnl_percent = (exit_price - position['entry_price']) / position['entry_price'] * 100 * position['leverage']
        else:  # SELL
            pnl = (position['entry_price'] - exit_price) * position['quantity']
            pnl_percent = (position['entry_price'] - exit_price) / position['entry_price'] * 100 * position['leverage']
            
        # Cập nhật thông tin vị thế
        position['exit_price'] = exit_price
        position['exit_time'] = datetime.now()
        position['pnl'] = pnl
        position['pnl_percent'] = pnl_percent
        position['duration'] = (position['exit_time'] - position['open_time']).total_seconds() / 3600  # giờ
        position['exit_reason'] = exit_reason
        
        # Cập nhật số dư
        old_balance = self.current_balance
        self.current_balance += pnl
        
        # Tạo bản sao để trả về
        closed_position = position.copy()
        
        # Xóa khỏi danh sách vị thế mở
        self.open_positions.pop(position_index)
        
        logger.info(f"Đã đóng vị thế {position['side']} #{position_id}: "
                   f"Entry={position['entry_price']:.2f}, Exit={exit_price:.2f}, "
                   f"P&L=${pnl:.2f} ({pnl_percent:+.2f}%), Lý do: {exit_reason}")
                   
        logger.info(f"Số dư: ${old_balance:.2f} -> ${self.current_balance:.2f} ({(pnl/old_balance)*100:+.2f}%)")
        
        return True, closed_position
    
    def update_balance(self, new_balance: float) -> None:
        """
        Cập nhật số dư tài khoản
        
        Args:
            new_balance (float): Số dư mới
        """
        old_balance = self.current_balance
        self.current_balance = new_balance
        
        logger.info(f"Cập nhật số dư: ${old_balance:.2f} -> ${new_balance:.2f} "
                   f"({(new_balance-old_balance)/old_balance*100:+.2f}%)")
    
    def get_account_status(self) -> Dict:
        """
        Lấy trạng thái tài khoản hiện tại
        
        Returns:
            Dict: Trạng thái tài khoản
        """
        total_margin_used = sum(pos['margin_used'] for pos in self.open_positions)
        margin_usage_percent = total_margin_used / self.current_balance * 100 if self.current_balance > 0 else 0
        
        total_risk_amount = sum(pos['risk_amount'] for pos in self.open_positions)
        risk_percent = total_risk_amount / self.current_balance * 100 if self.current_balance > 0 else 0
        
        status = {
            'current_balance': self.current_balance,
            'open_positions': len(self.open_positions),
            'total_margin_used': total_margin_used,
            'margin_usage_percent': margin_usage_percent,
            'total_risk_amount': total_risk_amount,
            'risk_percent': risk_percent,
            'available_balance': self.current_balance - total_margin_used,
            'max_positions': self.max_positions,
            'positions_available': max(0, self.max_positions - len(self.open_positions))
        }
        
        # Tính P&L unrealized
        if self.open_positions:
            unrealized_pnl = sum(pos.get('pnl', 0) for pos in self.open_positions)
            status['unrealized_pnl'] = unrealized_pnl
            status['unrealized_pnl_percent'] = unrealized_pnl / self.current_balance * 100
        else:
            status['unrealized_pnl'] = 0
            status['unrealized_pnl_percent'] = 0
            
        return status
    
    def get_risk_allocation_recommendations(self) -> Dict:
        """
        Đưa ra các khuyến nghị phân bổ rủi ro cho vị thế tiếp theo
        
        Returns:
            Dict: Các khuyến nghị phân bổ rủi ro
        """
        account_status = self.get_account_status()
        
        # Số vị thế còn lại có thể mở
        positions_left = account_status['positions_available']
        
        # Rủi ro còn lại có thể phân bổ
        risk_left_percent = max(0, self.max_account_risk - account_status['risk_percent'])
        
        # Phân bổ rủi ro đều cho các vị thế còn lại
        if positions_left > 0:
            recommended_risk_per_trade = min(self.max_risk_per_trade, risk_left_percent / positions_left)
        else:
            recommended_risk_per_trade = 0
            
        # Margin còn lại
        margin_left = account_status['available_balance']
        
        # Ước tính kích thước vị thế tối đa
        max_position_size = margin_left * self.max_leverage * 0.95  # Sử dụng 95% margin khả dụng
        
        # Ước tính kích thước vị thế theo rủi ro
        risk_amount = self.current_balance * (recommended_risk_per_trade / 100)
        # Giả định stop loss khoảng 2% giá, leverage = 10
        estimated_position_size = (risk_amount / 2) * 100 * 10
        
        # Lấy giá trị nhỏ hơn
        recommended_position_size = min(max_position_size, estimated_position_size)
        
        return {
            'positions_available': positions_left,
            'risk_left_percent': risk_left_percent,
            'recommended_risk_per_trade': recommended_risk_per_trade,
            'margin_available': margin_left,
            'max_position_size': max_position_size,
            'recommended_position_size': recommended_position_size
        }
    
    def get_risk_metrics(self) -> Dict:
        """
        Tính toán các chỉ số rủi ro dựa trên lịch sử
        
        Returns:
            Dict: Các chỉ số rủi ro
        """
        if not self.risk_history:
            return {
                'status': 'No risk history available'
            }
            
        # Số giao dịch đã thực hiện
        trade_count = len(self.risk_history)
        
        # Rủi ro trung bình trên mỗi giao dịch
        avg_risk_percent = sum(entry['risk_percent'] for entry in self.risk_history) / trade_count
        
        # Đòn bẩy trung bình
        avg_leverage = sum(entry['leverage'] for entry in self.risk_history) / trade_count
        
        # Kích thước vị thế trung bình
        avg_position_size = sum(entry['position_size'] for entry in self.risk_history) / trade_count
        
        # Xu hướng rủi ro theo thời gian
        risk_trend = "stable"
        if len(self.risk_history) >= 5:
            recent_risk = sum(entry['risk_percent'] for entry in self.risk_history[-5:]) / 5
            earlier_risk = sum(entry['risk_percent'] for entry in self.risk_history[:-5]) / max(1, len(self.risk_history) - 5)
            
            if recent_risk > earlier_risk * 1.2:
                risk_trend = "increasing"
            elif recent_risk < earlier_risk * 0.8:
                risk_trend = "decreasing"
                
        return {
            'trade_count': trade_count,
            'avg_risk_percent': avg_risk_percent,
            'avg_leverage': avg_leverage,
            'avg_position_size': avg_position_size,
            'risk_trend': risk_trend,
            'latest_risk_percent': self.risk_history[-1]['risk_percent'] if self.risk_history else 0
        }
        
# Chức năng demo
def main():
    """Demo chức năng của LeverageRiskManager"""
    # Khởi tạo với tài khoản nhỏ
    risk_manager = LeverageRiskManager(
        initial_balance=100.0,
        max_leverage=20,
        max_positions=3,
        max_risk_per_trade=2.0,
        max_account_risk=15.0
    )
    
    # Tính đòn bẩy tối ưu
    entry_price = 35000.0
    stop_loss = 34650.0  # 1% dưới giá vào
    
    leverage, details = risk_manager.calculate_optimal_leverage(
        entry_price=entry_price,
        stop_loss=stop_loss,
        market_volatility=2.5,
        market_regime='trending'
    )
    
    print(f"Đòn bẩy tối ưu: x{leverage}")
    
    # Tính kích thước vị thế
    position_size, pos_details = risk_manager.calculate_position_size(
        entry_price=entry_price,
        stop_loss=stop_loss,
        leverage=leverage
    )
    
    print(f"Kích thước vị thế: ${position_size:.2f}")
    print(f"Số lượng Bitcoin: {pos_details['quantity']:.8f}")
    print(f"Rủi ro: ${pos_details['risk_amount']:.2f} ({pos_details['risk_percent']:.2f}%)")
    print(f"Điểm thanh lý: ${pos_details['liquidation_price']:.2f}")
    print(f"Khoảng cách đến thanh lý: {pos_details['liquidation_distance_percent']:.2f}%")
    
    # Thêm vị thế
    success, position = risk_manager.add_position(
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=entry_price * 1.03,  # 3% trên giá vào
        leverage=leverage,
        side="BUY",
        position_size=position_size
    )
    
    if success:
        print(f"Đã mở vị thế: {position['side']}, ID={position['position_id']}")
    else:
        print(f"Không thể mở vị thế: {position}")
        
    # Cập nhật vị thế với giá hiện tại
    status = risk_manager.update_position(
        position_id=0,
        current_price=entry_price * 1.02,  # Giả sử giá tăng 2%
        trailing_stop_percent=1.0  # Trailing stop 1%
    )
    
    print(f"Trạng thái vị thế: {status['status']}")
    print(f"P&L: ${status['pnl']:.2f} ({status['pnl_percent']:+.2f}%)")
    
    # Đóng vị thế
    closed, closed_position = risk_manager.close_position(
        position_id=0,
        exit_price=entry_price * 1.02,
        exit_reason='manual'
    )
    
    if closed:
        print(f"Đã đóng vị thế: P&L=${closed_position['pnl']:.2f} ({closed_position['pnl_percent']:+.2f}%)")
    
    # Lấy trạng thái tài khoản
    account_status = risk_manager.get_account_status()
    print(f"Số dư hiện tại: ${account_status['current_balance']:.2f}")
    
    # Lấy khuyến nghị phân bổ rủi ro
    recommendations = risk_manager.get_risk_allocation_recommendations()
    print(f"Có thể mở thêm {recommendations['positions_available']} vị thế")
    print(f"Rủi ro đề xuất cho vị thế tiếp theo: {recommendations['recommended_risk_per_trade']:.2f}%")
    print(f"Kích thước vị thế đề xuất: ${recommendations['recommended_position_size']:.2f}")

if __name__ == "__main__":
    main()