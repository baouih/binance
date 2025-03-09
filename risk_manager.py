"""
Module quản lý rủi ro (Risk Manager)

Module này cung cấp các công cụ quản lý rủi ro để bảo vệ vốn và tối ưu hóa hiệu suất giao dịch,
bao gồm các chiến lược stop loss, take profit, trailing stop động và quản lý rủi ro tổng thể.
"""

import logging
import math
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional, Union
from datetime import datetime

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("risk_manager")

class RiskManager:
    """Lớp quản lý rủi ro cho giao dịch"""
    
    def __init__(self, account_balance: float = 10000.0, 
               stop_loss_pct: float = 5.0, take_profit_pct: float = 15.0,
               trailing_stop: bool = True, max_open_trades: int = 5,
               max_daily_trades: int = 10, max_trades_per_symbol: int = 3,
               max_drawdown_pct: float = 20.0, daily_loss_limit_pct: float = 5.0,
               risk_method: str = 'fixed', max_trades: int = 10):
        """
        Khởi tạo Risk Manager
        
        Args:
            account_balance (float): Số dư tài khoản
            stop_loss_pct (float): Phần trăm stop loss mặc định
            take_profit_pct (float): Phần trăm take profit mặc định
            trailing_stop (bool): Sử dụng trailing stop hay không
            max_open_trades (int): Số lượng giao dịch mở tối đa cùng lúc
            max_daily_trades (int): Số lượng giao dịch tối đa trong ngày
            max_trades_per_symbol (int): Số lượng giao dịch tối đa cho mỗi symbol
            max_drawdown_pct (float): Phần trăm drawdown tối đa cho phép
            daily_loss_limit_pct (float): Giới hạn thua lỗ hàng ngày (phần trăm)
            risk_method (str): Phương pháp quản lý rủi ro ('fixed', 'adaptive', 'volatility_based')
        """
        self.account_balance = account_balance
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.trailing_stop = trailing_stop
        self.max_open_trades = max_open_trades
        self.max_daily_trades = max_daily_trades
        self.max_trades_per_symbol = max_trades_per_symbol
        self.max_drawdown_pct = max_drawdown_pct
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.risk_method = risk_method
        
        self.open_trades = []
        self.closed_trades = []
        self.trade_count_today = 0
        self.trade_counts_by_symbol = {}
        self.peak_balance = account_balance
        self.daily_starting_balance = account_balance
        self.risk_adjustment_factor = 1.0  # Hệ số điều chỉnh rủi ro động
        
    def calculate_stop_levels(self, entry_price: float, side: str, 
                           market_data: pd.DataFrame = None, position_size: float = None,
                           balance: float = None) -> Tuple[float, float]:
        """
        Tính toán mức stop loss và take profit
        
        Args:
            entry_price (float): Giá vào lệnh
            side (str): Hướng vị thế ('BUY' hoặc 'SELL')
            market_data (pd.DataFrame, optional): Dữ liệu thị trường
            position_size (float, optional): Kích thước vị thế
            balance (float, optional): Số dư tài khoản
            
        Returns:
            Tuple[float, float]: (stop_loss_price, take_profit_price)
        """
        # Phương pháp fixed (cố định phần trăm)
        if self.risk_method == 'fixed':
            if side == 'BUY':
                stop_loss = entry_price * (1 - self.stop_loss_pct / 100)
                take_profit = entry_price * (1 + self.take_profit_pct / 100)
            else:  # SELL
                stop_loss = entry_price * (1 + self.stop_loss_pct / 100)
                take_profit = entry_price * (1 - self.take_profit_pct / 100)
                
        # Phương pháp adaptive (thích ứng với hiệu suất)
        elif self.risk_method == 'adaptive':
            # Điều chỉnh % stop loss dựa trên hiệu suất gần đây
            adjusted_sl_pct = self.stop_loss_pct * self.risk_adjustment_factor
            adjusted_tp_pct = self.take_profit_pct * self.risk_adjustment_factor
            
            if side == 'BUY':
                stop_loss = entry_price * (1 - adjusted_sl_pct / 100)
                take_profit = entry_price * (1 + adjusted_tp_pct / 100)
            else:  # SELL
                stop_loss = entry_price * (1 + adjusted_sl_pct / 100)
                take_profit = entry_price * (1 - adjusted_tp_pct / 100)
                
        # Phương pháp volatility_based (dựa trên biến động, thường là ATR)
        elif self.risk_method == 'volatility_based':
            # Sử dụng ATR nếu có
            if market_data is not None and 'atr' in market_data.columns:
                atr = market_data['atr'].iloc[-1]
                sl_multiplier = 2.0  # Khoảng cách 2 ATR
                tp_multiplier = 3.0  # Khoảng cách 3 ATR
                
                if side == 'BUY':
                    stop_loss = entry_price - (atr * sl_multiplier)
                    take_profit = entry_price + (atr * tp_multiplier)
                else:  # SELL
                    stop_loss = entry_price + (atr * sl_multiplier)
                    take_profit = entry_price - (atr * tp_multiplier)
            else:
                # Nếu không có ATR, sử dụng phương pháp cố định
                if side == 'BUY':
                    stop_loss = entry_price * (1 - self.stop_loss_pct / 100)
                    take_profit = entry_price * (1 + self.take_profit_pct / 100)
                else:  # SELL
                    stop_loss = entry_price * (1 + self.stop_loss_pct / 100)
                    take_profit = entry_price * (1 - self.take_profit_pct / 100)
        else:
            # Phương pháp mặc định nếu không nhận dạng được
            if side == 'BUY':
                stop_loss = entry_price * (1 - self.stop_loss_pct / 100)
                take_profit = entry_price * (1 + self.take_profit_pct / 100)
            else:  # SELL
                stop_loss = entry_price * (1 + self.stop_loss_pct / 100)
                take_profit = entry_price * (1 - self.take_profit_pct / 100)
                
        return (stop_loss, take_profit)
        
    def should_execute_trade(self, symbol: str, side: str, current_balance: Optional[float] = None) -> bool:
        """
        Kiểm tra xem có nên thực hiện giao dịch hay không
        
        Args:
            symbol (str): Symbol giao dịch
            side (str): Hướng giao dịch ('BUY' hoặc 'SELL')
            current_balance (float, optional): Số dư hiện tại
            
        Returns:
            bool: True nếu nên thực hiện, False nếu không
        """
        # Cập nhật số dư
        if current_balance is not None:
            self.account_balance = current_balance
            
        # Kiểm tra số lượng vị thế mở tối đa
        if len(self.open_trades) >= self.max_open_trades:
            logger.info(f"Đã đạt số lượng vị thế mở tối đa ({self.max_open_trades})")
            return False
            
        # Kiểm tra số lượng giao dịch trong ngày
        if self.trade_count_today >= self.max_daily_trades:
            logger.info(f"Đã đạt số lượng giao dịch tối đa trong ngày ({self.max_daily_trades})")
            return False
            
        # Kiểm tra số lượng giao dịch cho mỗi symbol
        symbol_count = self.trade_counts_by_symbol.get(symbol, 0)
        if symbol_count >= self.max_trades_per_symbol:
            logger.info(f"Đã đạt số lượng giao dịch tối đa cho {symbol} ({self.max_trades_per_symbol})")
            return False
            
        # Kiểm tra drawdown
        if self.account_balance < self.peak_balance * (1 - self.max_drawdown_pct / 100):
            logger.info(f"Đã đạt drawdown tối đa ({self.max_drawdown_pct}%)")
            return False
            
        # Kiểm tra giới hạn thua lỗ hàng ngày
        if self.account_balance < self.daily_starting_balance * (1 - self.daily_loss_limit_pct / 100):
            logger.info(f"Đã đạt giới hạn thua lỗ hàng ngày ({self.daily_loss_limit_pct}%)")
            return False
            
        # Kiểm tra nếu đã có vị thế ngược chiều cho cùng symbol
        for trade in self.open_trades:
            if trade['symbol'] == symbol and trade['side'] != side:
                logger.info(f"Đã có vị thế ngược chiều cho {symbol}")
                return False
                
        return True
        
    def open_trade(self, symbol: str, side: str, entry_price: float, quantity: float,
                stop_loss: float = None, take_profit: float = None,
                entry_time: datetime = None, leverage: int = 1) -> Dict:
        """
        Mở một giao dịch mới
        
        Args:
            symbol (str): Symbol giao dịch
            side (str): Hướng giao dịch ('BUY' hoặc 'SELL')
            entry_price (float): Giá vào lệnh
            quantity (float): Số lượng
            stop_loss (float, optional): Giá stop loss
            take_profit (float, optional): Giá take profit
            entry_time (datetime, optional): Thời gian vào lệnh
            leverage (int): Đòn bẩy
            
        Returns:
            Dict: Thông tin giao dịch
        """
        # Kiểm tra xem có nên mở giao dịch không
        if not self.should_execute_trade(symbol, side):
            logger.warning(f"Không thể mở giao dịch {symbol} {side}")
            return None
            
        # Tính toán stop loss và take profit nếu chưa có
        if stop_loss is None or take_profit is None:
            sl, tp = self.calculate_stop_levels(entry_price, side)
            stop_loss = stop_loss or sl
            take_profit = take_profit or tp
            
        # Tạo thông tin giao dịch
        trade_id = len(self.open_trades) + len(self.closed_trades) + 1
        entry_time = entry_time or datetime.now()
        
        trade = {
            'id': trade_id,
            'symbol': symbol,
            'side': side,
            'entry_price': entry_price,
            'quantity': quantity,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'entry_time': entry_time,
            'exit_time': None,
            'exit_price': None,
            'profit': None,
            'exit_reason': None,
            'leverage': leverage,
            'trailing_stop_activated': False,
            'trailing_stop_level': None,
            'position_value': entry_price * quantity
        }
        
        # Thêm vào danh sách giao dịch mở
        self.open_trades.append(trade)
        
        # Cập nhật các số liệu
        self.trade_count_today += 1
        self.trade_counts_by_symbol[symbol] = self.trade_counts_by_symbol.get(symbol, 0) + 1
        
        logger.info(f"Mở giao dịch #{trade_id}: {symbol} {side} tại {entry_price}, SL: {stop_loss}, TP: {take_profit}")
        
        return trade
        
    def close_trade(self, trade_id: int, exit_price: float, exit_time: datetime = None, 
                 exit_reason: str = None) -> Dict:
        """
        Đóng một giao dịch
        
        Args:
            trade_id (int): ID của giao dịch cần đóng
            exit_price (float): Giá thoát
            exit_time (datetime, optional): Thời gian thoát
            exit_reason (str, optional): Lý do thoát
            
        Returns:
            Dict: Thông tin giao dịch đã đóng
        """
        # Tìm giao dịch cần đóng
        trade = None
        trade_index = -1
        for i, t in enumerate(self.open_trades):
            if t['id'] == trade_id:
                trade = t
                trade_index = i
                break
                
        if trade is None:
            logger.warning(f"Không tìm thấy giao dịch ID {trade_id}")
            return None
            
        # Cập nhật thông tin đóng
        trade['exit_price'] = exit_price
        trade['exit_time'] = exit_time or datetime.now()
        trade['exit_reason'] = exit_reason or 'manual'
        
        # Tính lợi nhuận (đã tính đến đòn bẩy)
        if trade['side'] == 'BUY':
            profit_pct = (exit_price - trade['entry_price']) / trade['entry_price'] * 100 * trade['leverage']
        else:  # SELL
            profit_pct = (trade['entry_price'] - exit_price) / trade['entry_price'] * 100 * trade['leverage']
            
        profit_amount = trade['position_value'] * profit_pct / 100
        trade['profit'] = profit_amount
        trade['profit_pct'] = profit_pct
        
        # Cập nhật số dư
        self.account_balance += profit_amount
        
        # Cập nhật peak balance nếu cần
        if self.account_balance > self.peak_balance:
            self.peak_balance = self.account_balance
            
        # Xóa khỏi danh sách giao dịch mở và thêm vào danh sách đã đóng
        closed_trade = self.open_trades.pop(trade_index)
        self.closed_trades.append(closed_trade)
        
        # Cập nhật risk_adjustment_factor dựa trên kết quả
        self._update_risk_adjustment_factor(profit_pct)
        
        logger.info(f"Đóng giao dịch #{trade_id}: {trade['symbol']} {trade['side']} tại {exit_price}, "
                 f"Lợi nhuận: ${profit_amount:.2f} ({profit_pct:.2f}%), Lý do: {exit_reason}")
        
        return closed_trade
        
    def update_trailing_stop(self, trade_id: int, current_price: float) -> Tuple[bool, float]:
        """
        Cập nhật trailing stop cho một giao dịch
        
        Args:
            trade_id (int): ID của giao dịch
            current_price (float): Giá hiện tại
            
        Returns:
            Tuple[bool, float]: (Đã cập nhật hay không, Mức trailing stop mới)
        """
        # Tìm giao dịch
        trade = None
        for t in self.open_trades:
            if t['id'] == trade_id:
                trade = t
                break
                
        if trade is None:
            logger.warning(f"Không tìm thấy giao dịch ID {trade_id}")
            return (False, None)
            
        # Nếu trailing stop chưa được kích hoạt, kiểm tra điều kiện để kích hoạt
        if not trade['trailing_stop_activated']:
            # Kích hoạt trailing stop khi đạt 50% mức take profit
            if trade['side'] == 'BUY':
                target_price = trade['entry_price'] + (trade['take_profit'] - trade['entry_price']) * 0.5
                if current_price >= target_price:
                    trade['trailing_stop_activated'] = True
                    trade['trailing_stop_level'] = max(trade['stop_loss'], current_price * (1 - self.stop_loss_pct / 100))
                    logger.info(f"Kích hoạt trailing stop cho #{trade_id} tại {current_price}, "
                             f"Mức: {trade['trailing_stop_level']}")
                    return (True, trade['trailing_stop_level'])
            else:  # SELL
                target_price = trade['entry_price'] - (trade['entry_price'] - trade['take_profit']) * 0.5
                if current_price <= target_price:
                    trade['trailing_stop_activated'] = True
                    trade['trailing_stop_level'] = min(trade['stop_loss'], current_price * (1 + self.stop_loss_pct / 100))
                    logger.info(f"Kích hoạt trailing stop cho #{trade_id} tại {current_price}, "
                             f"Mức: {trade['trailing_stop_level']}")
                    return (True, trade['trailing_stop_level'])
        
        # Nếu trailing stop đã được kích hoạt, cập nhật nếu cần
        elif trade['trailing_stop_activated']:
            if trade['side'] == 'BUY' and current_price > trade['trailing_stop_level'] * (1 + self.stop_loss_pct / 200):
                # Cập nhật trailing stop lên
                new_stop = current_price * (1 - self.stop_loss_pct / 100)
                if new_stop > trade['trailing_stop_level']:
                    trade['trailing_stop_level'] = new_stop
                    logger.info(f"Cập nhật trailing stop cho #{trade_id} lên {new_stop}")
                    return (True, new_stop)
            
            elif trade['side'] == 'SELL' and current_price < trade['trailing_stop_level'] * (1 - self.stop_loss_pct / 200):
                # Cập nhật trailing stop xuống
                new_stop = current_price * (1 + self.stop_loss_pct / 100)
                if new_stop < trade['trailing_stop_level']:
                    trade['trailing_stop_level'] = new_stop
                    logger.info(f"Cập nhật trailing stop cho #{trade_id} xuống {new_stop}")
                    return (True, new_stop)
        
        return (False, trade.get('trailing_stop_level'))
        
    def check_trade_exit(self, trade_id: int, current_price: float, current_time: datetime = None) -> Tuple[bool, str]:
        """
        Kiểm tra xem một giao dịch có nên được đóng không
        
        Args:
            trade_id (int): ID của giao dịch
            current_price (float): Giá hiện tại
            current_time (datetime, optional): Thời gian hiện tại
            
        Returns:
            Tuple[bool, str]: (Nên đóng hay không, Lý do)
        """
        # Tìm giao dịch
        trade = None
        for t in self.open_trades:
            if t['id'] == trade_id:
                trade = t
                break
                
        if trade is None:
            logger.warning(f"Không tìm thấy giao dịch ID {trade_id}")
            return (False, None)
            
        # Cập nhật trailing stop nếu được bật
        if self.trailing_stop and not trade.get('trailing_stop_activated', False):
            self.update_trailing_stop(trade_id, current_price)
            
        # Kiểm tra điều kiện đóng lệnh
        
        # Take profit
        if (trade['side'] == 'BUY' and current_price >= trade['take_profit']) or \
           (trade['side'] == 'SELL' and current_price <= trade['take_profit']):
            return (True, 'take_profit')
            
        # Stop loss
        if (trade['side'] == 'BUY' and current_price <= trade['stop_loss']) or \
           (trade['side'] == 'SELL' and current_price >= trade['stop_loss']):
            return (True, 'stop_loss')
            
        # Trailing stop
        if trade.get('trailing_stop_activated', False) and trade.get('trailing_stop_level') is not None:
            if (trade['side'] == 'BUY' and current_price <= trade['trailing_stop_level']) or \
               (trade['side'] == 'SELL' and current_price >= trade['trailing_stop_level']):
                return (True, 'trailing_stop')
                
        return (False, None)
        
    def update_trades(self, current_prices: Dict[str, float], current_time: datetime = None) -> List[Dict]:
        """
        Cập nhật tất cả các giao dịch đang mở với giá hiện tại
        
        Args:
            current_prices (Dict[str, float]): Giá hiện tại cho mỗi symbol
            current_time (datetime, optional): Thời gian hiện tại
            
        Returns:
            List[Dict]: Danh sách các giao dịch đã được đóng
        """
        closed_trades = []
        current_time = current_time or datetime.now()
        
        # Cập nhật các giao dịch đang mở
        for trade in self.open_trades[:]:  # Tạo một bản sao để lặp
            symbol = trade['symbol']
            
            # Bỏ qua nếu không có thông tin giá
            if symbol not in current_prices:
                continue
                
            current_price = current_prices[symbol]
            
            # Kiểm tra điều kiện đóng
            should_exit, exit_reason = self.check_trade_exit(trade['id'], current_price, current_time)
            
            if should_exit:
                closed_trade = self.close_trade(trade['id'], current_price, current_time, exit_reason)
                closed_trades.append(closed_trade)
                
        return closed_trades
                
    def get_open_trades(self) -> List[Dict]:
        """
        Lấy danh sách các giao dịch đang mở
        
        Returns:
            List[Dict]: Danh sách các giao dịch đang mở
        """
        return self.open_trades
        
    def get_closed_trades(self, limit: int = None) -> List[Dict]:
        """
        Lấy danh sách các giao dịch đã đóng
        
        Args:
            limit (int, optional): Số lượng giao dịch tối đa
            
        Returns:
            List[Dict]: Danh sách các giao dịch đã đóng
        """
        if limit is not None:
            return self.closed_trades[-limit:]
        return self.closed_trades
        
    def get_trade_by_id(self, trade_id: int) -> Dict:
        """
        Lấy thông tin giao dịch theo ID
        
        Args:
            trade_id (int): ID của giao dịch
            
        Returns:
            Dict: Thông tin giao dịch nếu tìm thấy, None nếu không
        """
        # Tìm trong danh sách giao dịch mở
        for trade in self.open_trades:
            if trade['id'] == trade_id:
                return trade
                
        # Tìm trong danh sách giao dịch đã đóng
        for trade in self.closed_trades:
            if trade['id'] == trade_id:
                return trade
                
        return None
        
    def get_performance_metrics(self) -> Dict:
        """
        Tính toán các chỉ số hiệu suất
        
        Returns:
            Dict: Các chỉ số hiệu suất
        """
        # Nếu chưa có giao dịch nào, trả về metrics rỗng
        if not self.closed_trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'average_profit': 0,
                'average_loss': 0,
                'expectancy': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'total_profit': 0,
                'total_profit_pct': 0
            }
            
        # Tổng số giao dịch
        total_trades = len(self.closed_trades)
        
        # Số giao dịch thắng/thua
        winning_trades = [trade for trade in self.closed_trades if trade['profit'] > 0]
        losing_trades = [trade for trade in self.closed_trades if trade['profit'] <= 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        
        # Tỷ lệ thắng
        win_rate = win_count / total_trades if total_trades > 0 else 0
        
        # Tổng lợi nhuận/thua lỗ
        total_profit = sum(trade['profit'] for trade in winning_trades)
        total_loss = abs(sum(trade['profit'] for trade in losing_trades))
        
        # Profit factor
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Lợi nhuận/thua lỗ trung bình
        average_profit = total_profit / win_count if win_count > 0 else 0
        average_loss = total_loss / loss_count if loss_count > 0 else 0
        
        # Expectancy
        expectancy = (win_rate * average_profit) - ((1 - win_rate) * average_loss)
        
        # Tổng lợi nhuận
        net_profit = total_profit - total_loss
        
        # Tính drawdown
        balance_curve = [self.daily_starting_balance]
        for trade in self.closed_trades:
            balance_curve.append(balance_curve[-1] + trade['profit'])
            
        peak = balance_curve[0]
        max_drawdown = 0
        for balance in balance_curve[1:]:
            if balance > peak:
                peak = balance
            drawdown = (peak - balance) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)
            
        # Sharpe ratio
        if len(self.closed_trades) > 1:
            profits = [trade['profit'] for trade in self.closed_trades]
            profit_mean = np.mean(profits)
            profit_std = np.std(profits)
            sharpe_ratio = profit_mean / profit_std if profit_std > 0 else 0
        else:
            sharpe_ratio = 0
            
        # Tổng lợi nhuận tính theo phần trăm
        initial_balance = self.daily_starting_balance
        total_profit_pct = (self.account_balance - initial_balance) / initial_balance * 100
        
        return {
            'total_trades': total_trades,
            'win_count': win_count,
            'loss_count': loss_count,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'average_profit': average_profit,
            'average_loss': average_loss,
            'expectancy': expectancy,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'total_profit': net_profit,
            'total_profit_pct': total_profit_pct,
            'current_balance': self.account_balance
        }
        
    def reset_daily_metrics(self) -> None:
        """
        Đặt lại các chỉ số hàng ngày
        """
        self.trade_count_today = 0
        self.daily_starting_balance = self.account_balance
        
    def _update_risk_adjustment_factor(self, last_profit_pct: float) -> None:
        """
        Cập nhật hệ số điều chỉnh rủi ro dựa trên kết quả giao dịch gần đây
        
        Args:
            last_profit_pct (float): Phần trăm lợi nhuận của giao dịch gần nhất
        """
        # Nếu giao dịch gần nhất thắng, tăng nhẹ hệ số
        if last_profit_pct > 0:
            self.risk_adjustment_factor = min(1.2, self.risk_adjustment_factor * 1.05)
        # Nếu giao dịch gần nhất thua, giảm mạnh hệ số
        else:
            self.risk_adjustment_factor = max(0.5, self.risk_adjustment_factor * 0.9)
            
    def update_account_balance(self, new_balance: float) -> None:
        """
        Cập nhật số dư tài khoản
        
        Args:
            new_balance (float): Số dư mới
        """
        self.account_balance = new_balance
        
        # Cập nhật peak balance nếu cần
        if new_balance > self.peak_balance:
            self.peak_balance = new_balance
            
    def get_active_risk_exposure(self) -> float:
        """
        Tính tổng rủi ro đang mở
        
        Returns:
            float: Phần trăm vốn đang chịu rủi ro
        """
        total_risk = 0
        
        for trade in self.open_trades:
            entry_price = trade['entry_price']
            stop_loss = trade['stop_loss']
            position_value = trade['position_value']
            
            if trade['side'] == 'BUY':
                risk_pct = (entry_price - stop_loss) / entry_price * 100
            else:  # SELL
                risk_pct = (stop_loss - entry_price) / entry_price * 100
                
            trade_risk = position_value * risk_pct / 100
            total_risk += trade_risk
            
        # Tính phần trăm so với số dư
        risk_exposure_pct = total_risk / self.account_balance * 100
        
        return risk_exposure_pct