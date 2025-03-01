"""
Module quản lý rủi ro nâng cao (Advanced Risk Management)

Module này cung cấp các công cụ tiên tiến để quản lý rủi ro giao dịch:
- Tính toán VaR (Value at Risk) và CVaR (Conditional Value at Risk)
- Phát hiện phơi nhiễm tương quan (correlation exposure) giữa các vị thế
- Stress testing cho các kịch bản thị trường khác nhau
- Quản lý drawdown và kế hoạch phục hồi
- Circuit breakers tự động khi phát hiện biến động bất thường

Mục tiêu là bảo vệ tài khoản khỏi rủi ro hệ thống và không hệ thống,
đồng thời tối ưu hóa quản lý vốn trong các điều kiện thị trường khác nhau.
"""

import time
import threading
import logging
import json
import os
from typing import Dict, List, Tuple, Union, Optional
from datetime import datetime, timedelta
import numpy as np

# Cấu hình logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("risk_manager")

class RiskManager:
    """Lớp quản lý rủi ro tổng thể cho hệ thống giao dịch"""
    
    def __init__(self, account_balance: float, max_risk_per_trade: float = 2.0,
                max_daily_risk: float = 5.0, max_weekly_risk: float = 10.0,
                max_drawdown_allowed: float = 20.0, risk_free_rate: float = 0.0,
                circuit_breaker_threshold: float = 7.0):
        """
        Khởi tạo Risk Manager.
        
        Args:
            account_balance (float): Số dư tài khoản
            max_risk_per_trade (float): Phần trăm rủi ro tối đa cho mỗi giao dịch (%)
            max_daily_risk (float): Phần trăm rủi ro tối đa cho một ngày (%)
            max_weekly_risk (float): Phần trăm rủi ro tối đa cho một tuần (%)
            max_drawdown_allowed (float): Phần trăm drawdown tối đa cho phép (%)
            risk_free_rate (float): Lãi suất phi rủi ro hàng năm (%)
            circuit_breaker_threshold (float): Ngưỡng biến động giá để kích hoạt circuit breaker (%)
        """
        self.account_balance = max(0.01, account_balance)
        self.initial_balance = self.account_balance
        self.max_risk_per_trade = max(0.1, min(max_risk_per_trade, 10.0))  # Giới hạn 0.1-10%
        self.max_daily_risk = max(0.1, min(max_daily_risk, 20.0))  # Giới hạn 0.1-20%
        self.max_weekly_risk = max(0.1, min(max_weekly_risk, 50.0))  # Giới hạn 0.1-50%
        self.max_drawdown_allowed = max(1.0, min(max_drawdown_allowed, 50.0))  # Giới hạn 1-50%
        self.risk_free_rate = max(0.0, min(risk_free_rate, 10.0))  # Giới hạn 0-10%
        self.circuit_breaker_threshold = max(1.0, circuit_breaker_threshold)
        
        # Theo dõi rủi ro theo thời gian
        self.daily_risk_used = 0.0
        self.weekly_risk_used = 0.0
        self.daily_trades = []
        self.weekly_trades = []
        self.active_trades = {}  # {trade_id: trade_info}
        self.closed_trades = []
        
        # Thông tin drawdown
        self.max_balance = self.account_balance
        self.current_drawdown_pct = 0.0
        self.max_drawdown_pct = 0.0
        self.drawdown_start_date = None
        
        # Circuit breaker
        self.circuit_breaker_active = False
        self.circuit_breaker_end_time = None
        self.circuit_breaker_duration_minutes = 30  # Thời gian mặc định khi kích hoạt
        
        # Thời gian theo dõi
        self.current_day = datetime.now().date()
        self.current_week_start = self._get_week_start(datetime.now())
        
        # Khởi tạo lịch sử tài khoản
        self.balance_history = [{
            'timestamp': datetime.now(),
            'balance': self.account_balance,
            'equity': self.account_balance,
            'drawdown_pct': 0.0
        }]
    
    def check_trade_risk(self, symbol: str, risk_amount: float, entry_price: float, 
                        stop_loss_price: float, **kwargs) -> Dict:
        """
        Kiểm tra xem một giao dịch có tuân thủ các quy tắc rủi ro không.
        
        Args:
            symbol (str): Mã cặp giao dịch
            risk_amount (float): Số tiền rủi ro (USD)
            entry_price (float): Giá vào lệnh
            stop_loss_price (float): Giá dừng lỗ
            **kwargs: Các tham số bổ sung
            
        Returns:
            Dict: Kết quả kiểm tra rủi ro
        """
        # Kiểm tra dữ liệu đầu vào
        if risk_amount <= 0 or entry_price <= 0 or stop_loss_price <= 0:
            return {
                'allowed': False,
                'reason': 'Invalid parameters',
                'details': {
                    'risk_amount': risk_amount,
                    'entry_price': entry_price,
                    'stop_loss_price': stop_loss_price
                }
            }
            
        # Kiểm tra circuit breaker
        if self.circuit_breaker_active:
            now = datetime.now()
            if self.circuit_breaker_end_time and now < self.circuit_breaker_end_time:
                minutes_left = (self.circuit_breaker_end_time - now).total_seconds() / 60
                return {
                    'allowed': False,
                    'reason': f'Circuit breaker active, trading paused for {minutes_left:.1f} more minutes',
                    'details': {
                        'circuit_breaker_end_time': self.circuit_breaker_end_time
                    }
                }
            else:
                # Reset circuit breaker nếu đã hết thời gian
                self.circuit_breaker_active = False
                self.circuit_breaker_end_time = None
        
        # Tính phần trăm rủi ro
        risk_percentage = (risk_amount / self.account_balance) * 100
        
        # Kiểm tra rủi ro từng giao dịch
        if risk_percentage > self.max_risk_per_trade:
            return {
                'allowed': False,
                'reason': f'Exceeds maximum risk per trade ({risk_percentage:.2f}% > {self.max_risk_per_trade:.2f}%)',
                'details': {
                    'risk_percentage': risk_percentage,
                    'max_risk_per_trade': self.max_risk_per_trade
                }
            }
            
        # Kiểm tra rủi ro ngày
        self._check_new_day()
        daily_risk_projection = self.daily_risk_used + risk_percentage
        if daily_risk_projection > self.max_daily_risk:
            return {
                'allowed': False,
                'reason': f'Exceeds maximum daily risk ({daily_risk_projection:.2f}% > {self.max_daily_risk:.2f}%)',
                'details': {
                    'daily_risk_used': self.daily_risk_used,
                    'daily_risk_projection': daily_risk_projection,
                    'max_daily_risk': self.max_daily_risk
                }
            }
            
        # Kiểm tra rủi ro tuần
        self._check_new_week()
        weekly_risk_projection = self.weekly_risk_used + risk_percentage
        if weekly_risk_projection > self.max_weekly_risk:
            return {
                'allowed': False,
                'reason': f'Exceeds maximum weekly risk ({weekly_risk_projection:.2f}% > {self.max_weekly_risk:.2f}%)',
                'details': {
                    'weekly_risk_used': self.weekly_risk_used,
                    'weekly_risk_projection': weekly_risk_projection,
                    'max_weekly_risk': self.max_weekly_risk
                }
            }
            
        # Kiểm tra drawdown
        if self.current_drawdown_pct > self.max_drawdown_allowed:
            return {
                'allowed': False,
                'reason': f'Account in excessive drawdown ({self.current_drawdown_pct:.2f}% > {self.max_drawdown_allowed:.2f}%)',
                'details': {
                    'current_drawdown_pct': self.current_drawdown_pct,
                    'max_drawdown_allowed': self.max_drawdown_allowed
                }
            }
            
        # Nếu mọi kiểm tra đều pass
        return {
            'allowed': True,
            'reason': 'Trade meets risk requirements',
            'details': {
                'risk_percentage': risk_percentage,
                'daily_risk_used': self.daily_risk_used,
                'weekly_risk_used': self.weekly_risk_used,
                'daily_risk_projection': daily_risk_projection,
                'weekly_risk_projection': weekly_risk_projection,
                'current_drawdown_pct': self.current_drawdown_pct
            }
        }
    
    def register_trade(self, trade_info: Dict) -> str:
        """
        Đăng ký một giao dịch mới và cập nhật rủi ro.
        
        Args:
            trade_info (Dict): Thông tin giao dịch
            
        Returns:
            str: Trade ID
        """
        # Validate and set defaults
        if 'timestamp' not in trade_info or trade_info['timestamp'] is None:
            trade_info['timestamp'] = datetime.now()
            
        if 'risk_percentage' not in trade_info or trade_info['risk_percentage'] is None:
            # Tính risk percentage nếu không được cung cấp
            if 'risk_amount' in trade_info and trade_info['risk_amount'] > 0:
                trade_info['risk_percentage'] = (trade_info['risk_amount'] / self.account_balance) * 100
            else:
                trade_info['risk_percentage'] = 0.0
                
        if 'trade_id' not in trade_info or not trade_info['trade_id']:
            trade_info['trade_id'] = f"trade_{int(time.time())}_{len(self.active_trades) + len(self.closed_trades)}"
            
        # Add to active trades
        trade_id = trade_info['trade_id']
        self.active_trades[trade_id] = trade_info
        
        # Update risk usage
        self._check_new_day()
        self._check_new_week()
        
        risk_percentage = trade_info.get('risk_percentage', 0.0)
        self.daily_risk_used += risk_percentage
        self.weekly_risk_used += risk_percentage
        
        self.daily_trades.append(trade_id)
        self.weekly_trades.append(trade_id)
        
        logger.info(f"Registered trade {trade_id} with risk {risk_percentage:.2f}%")
        return trade_id
    
    def close_trade(self, trade_id: str, exit_price: float, pnl: float, 
                  timestamp: datetime = None) -> bool:
        """
        Đóng một giao dịch và cập nhật thông tin tài khoản.
        
        Args:
            trade_id (str): ID của giao dịch
            exit_price (float): Giá thoát
            pnl (float): Lãi/lỗ
            timestamp (datetime, optional): Thời gian
            
        Returns:
            bool: True nếu đóng thành công, False nếu không
        """
        if trade_id not in self.active_trades:
            logger.warning(f"Trade {trade_id} not found in active trades")
            return False
            
        # Get trade info
        trade_info = self.active_trades[trade_id]
        
        # Update trade info
        trade_info['exit_price'] = exit_price
        trade_info['pnl'] = pnl
        trade_info['exit_time'] = timestamp or datetime.now()
        trade_info['status'] = 'win' if pnl > 0 else 'loss'
        
        # Move to closed trades
        self.closed_trades.append(trade_info)
        del self.active_trades[trade_id]
        
        # Update account balance
        self.update_account_balance(self.account_balance + pnl)
        
        logger.info(f"Closed trade {trade_id} with P&L: {pnl}")
        return True
    
    def update_account_balance(self, new_balance: float) -> None:
        """
        Cập nhật số dư tài khoản và tính toán drawdown.
        
        Args:
            new_balance (float): Số dư tài khoản mới
        """
        # Prevent negative balance
        new_balance = max(0.01, new_balance)
        
        # Update balance
        self.account_balance = new_balance
        
        # Update max balance
        if new_balance > self.max_balance:
            self.max_balance = new_balance
            self.drawdown_start_date = None
        
        # Calculate drawdown
        if self.max_balance > 0:
            self.current_drawdown_pct = (1 - (new_balance / self.max_balance)) * 100
            
            # Update max drawdown
            if self.current_drawdown_pct > self.max_drawdown_pct:
                self.max_drawdown_pct = self.current_drawdown_pct
                
            # Record drawdown start date if entering drawdown
            if self.current_drawdown_pct > 0 and self.drawdown_start_date is None:
                self.drawdown_start_date = datetime.now()
        else:
            self.current_drawdown_pct = 0.0
            
        # Add to balance history
        self.balance_history.append({
            'timestamp': datetime.now(),
            'balance': self.account_balance,
            'equity': self._calculate_equity(),
            'drawdown_pct': self.current_drawdown_pct
        })
        
        logger.info(f"Updated account balance: {self.account_balance:.2f}, " +
                  f"Drawdown: {self.current_drawdown_pct:.2f}%")
    
    def check_and_trigger_circuit_breaker(self, symbol: str, price_change_pct: float,
                                       volume_surge_factor: float = None,
                                       duration_minutes: float = None) -> bool:
        """
        Kiểm tra và kích hoạt circuit breaker nếu phát hiện biến động bất thường.
        
        Args:
            symbol (str): Mã cặp giao dịch
            price_change_pct (float): Phần trăm thay đổi giá (dương hoặc âm)
            volume_surge_factor (float, optional): Tỷ lệ khối lượng so với trung bình
            duration_minutes (float, optional): Thời lượng circuit breaker (phút)
            
        Returns:
            bool: True nếu circuit breaker được kích hoạt, False nếu không
        """
        # Check if already active
        if self.circuit_breaker_active:
            return True
            
        # Các điều kiện kích hoạt circuit breaker
        should_trigger = False
        
        # 1. Biến động giá vượt ngưỡng
        if abs(price_change_pct) >= self.circuit_breaker_threshold:
            should_trigger = True
            
        # 2. Kết hợp với volume bất thường
        if volume_surge_factor is not None and volume_surge_factor > 3.0 and abs(price_change_pct) >= self.circuit_breaker_threshold * 0.7:
            should_trigger = True
            
        # Kích hoạt nếu thỏa mãn điều kiện
        if should_trigger:
            # Set duration
            if duration_minutes is None:
                duration_minutes = self.circuit_breaker_duration_minutes
                
            # Activate circuit breaker
            self.circuit_breaker_active = True
            self.circuit_breaker_end_time = datetime.now() + timedelta(minutes=duration_minutes)
            
            logger.warning(f"Circuit breaker activated for {symbol} due to {price_change_pct:.2f}% price change " +
                         f"and {volume_surge_factor or 0:.1f}x volume surge. Trading paused for {duration_minutes} minutes.")
            return True
            
        return False
    
    def get_account_status(self) -> Dict:
        """
        Lấy trạng thái tài khoản hiện tại.
        
        Returns:
            Dict: Trạng thái tài khoản
        """
        return {
            'balance': self.account_balance,
            'equity': self._calculate_equity(),
            'initial_balance': self.initial_balance,
            'max_balance': self.max_balance,
            'current_drawdown_pct': self.current_drawdown_pct,
            'max_drawdown_pct': self.max_drawdown_pct,
            'drawdown_start_date': self.drawdown_start_date,
            'daily_risk_used': self.daily_risk_used,
            'weekly_risk_used': self.weekly_risk_used,
            'active_trades_count': len(self.active_trades),
            'closed_trades_count': len(self.closed_trades),
            'circuit_breaker_active': self.circuit_breaker_active,
            'circuit_breaker_end_time': self.circuit_breaker_end_time
        }
    
    def get_risk_metrics(self) -> Dict:
        """
        Tính toán các chỉ số rủi ro từ lịch sử giao dịch.
        
        Returns:
            Dict: Các chỉ số rủi ro
        """
        # Check if we have enough data
        if len(self.closed_trades) < 5:
            return {
                'var_95': 0.0,
                'cvar_95': 0.0,
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'expectancy': 0.0,
                'max_drawdown_pct': self.max_drawdown_pct,
                'drawdown_duration_days': self._calculate_drawdown_duration()
            }
            
        # Extract returns
        returns = []
        for trade in self.closed_trades:
            # Convert PnL to percentage return
            if 'pnl' in trade and 'entry_price' in trade and 'quantity' in trade:
                pnl = trade['pnl']
                entry_value = trade['entry_price'] * trade['quantity']
                if entry_value > 0:
                    returns.append(pnl / entry_value * 100)  # Percentage
                    
        if not returns:
            return {
                'var_95': 0.0,
                'cvar_95': 0.0,
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'expectancy': 0.0,
                'max_drawdown_pct': self.max_drawdown_pct,
                'drawdown_duration_days': self._calculate_drawdown_duration()
            }
            
        # Convert to numpy array for calculations
        returns_array = np.array(returns)
        
        # Calculate metrics
        
        # VaR and CVaR (95%)
        returns_sorted = np.sort(returns_array)
        var_95_index = int(0.05 * len(returns_sorted))
        var_95 = abs(returns_sorted[var_95_index])
        cvar_95 = abs(np.mean(returns_sorted[:var_95_index+1]))
        
        # Sharpe and Sortino
        daily_rf = (1 + self.risk_free_rate/100) ** (1/365) - 1  # Daily risk-free rate
        avg_return = np.mean(returns_array)
        std_return = np.std(returns_array)
        
        sharpe_ratio = (avg_return - daily_rf) / std_return if std_return > 0 else 0
        
        # For Sortino, we only consider negative returns
        negative_returns = returns_array[returns_array < 0]
        downside_std = np.std(negative_returns) if len(negative_returns) > 0 else 1e-10
        sortino_ratio = (avg_return - daily_rf) / downside_std
        
        # Win rate and profit factor
        wins = sum(1 for r in returns_array if r > 0)
        losses = sum(1 for r in returns_array if r < 0)
        
        win_rate = wins / len(returns_array) if len(returns_array) > 0 else 0
        
        total_profit = sum(r for r in returns_array if r > 0)
        total_loss = abs(sum(r for r in returns_array if r < 0))
        
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        
        # Expectancy
        expectancy = np.mean(returns_array) if returns_array.size > 0 else 0
        
        return {
            'var_95': var_95,
            'cvar_95': cvar_95,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'max_drawdown_pct': self.max_drawdown_pct,
            'drawdown_duration_days': self._calculate_drawdown_duration()
        }
    
    def save_state(self, file_path: str = 'risk_manager_state.json') -> bool:
        """
        Lưu trạng thái của Risk Manager.
        
        Args:
            file_path (str): Đường dẫn file
            
        Returns:
            bool: True nếu lưu thành công, False nếu thất bại
        """
        try:
            state = {
                'account_balance': self.account_balance,
                'initial_balance': self.initial_balance,
                'max_balance': self.max_balance,
                'max_risk_per_trade': self.max_risk_per_trade,
                'max_daily_risk': self.max_daily_risk,
                'max_weekly_risk': self.max_weekly_risk,
                'max_drawdown_allowed': self.max_drawdown_allowed,
                'risk_free_rate': self.risk_free_rate,
                'circuit_breaker_threshold': self.circuit_breaker_threshold,
                'daily_risk_used': self.daily_risk_used,
                'weekly_risk_used': self.weekly_risk_used,
                'current_drawdown_pct': self.current_drawdown_pct,
                'max_drawdown_pct': self.max_drawdown_pct,
                'circuit_breaker_active': self.circuit_breaker_active,
                'circuit_breaker_duration_minutes': self.circuit_breaker_duration_minutes,
                'current_day': self.current_day.isoformat(),
                'current_week_start': self.current_week_start.isoformat()
            }
            
            # Convert datetime objects to string
            if self.drawdown_start_date:
                state['drawdown_start_date'] = self.drawdown_start_date.isoformat()
            
            if self.circuit_breaker_end_time:
                state['circuit_breaker_end_time'] = self.circuit_breaker_end_time.isoformat()
                
            # Save active and closed trades
            state['active_trades'] = []
            for trade_id, trade in self.active_trades.items():
                trade_copy = trade.copy()
                if 'timestamp' in trade_copy:
                    trade_copy['timestamp'] = trade_copy['timestamp'].isoformat()
                state['active_trades'].append(trade_copy)
                
            state['closed_trades'] = []
            for trade in self.closed_trades:
                trade_copy = trade.copy()
                if 'timestamp' in trade_copy:
                    trade_copy['timestamp'] = trade_copy['timestamp'].isoformat()
                if 'exit_time' in trade_copy:
                    trade_copy['exit_time'] = trade_copy['exit_time'].isoformat()
                state['closed_trades'].append(trade_copy)
                
            # Save balance history
            state['balance_history'] = []
            for record in self.balance_history:
                record_copy = record.copy()
                record_copy['timestamp'] = record_copy['timestamp'].isoformat()
                state['balance_history'].append(record_copy)
                
            # Save to file
            with open(file_path, 'w') as f:
                json.dump(state, f, indent=2)
                
            logger.info(f"Saved risk manager state to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving risk manager state: {e}")
            return False
    
    def load_state(self, file_path: str = 'risk_manager_state.json') -> bool:
        """
        Tải trạng thái của Risk Manager.
        
        Args:
            file_path (str): Đường dẫn file
            
        Returns:
            bool: True nếu tải thành công, False nếu thất bại
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"State file {file_path} not found")
                return False
                
            with open(file_path, 'r') as f:
                state = json.load(f)
                
            # Load basic settings
            self.account_balance = state.get('account_balance', self.account_balance)
            self.initial_balance = state.get('initial_balance', self.initial_balance)
            self.max_balance = state.get('max_balance', self.max_balance)
            self.max_risk_per_trade = state.get('max_risk_per_trade', self.max_risk_per_trade)
            self.max_daily_risk = state.get('max_daily_risk', self.max_daily_risk)
            self.max_weekly_risk = state.get('max_weekly_risk', self.max_weekly_risk)
            self.max_drawdown_allowed = state.get('max_drawdown_allowed', self.max_drawdown_allowed)
            self.risk_free_rate = state.get('risk_free_rate', self.risk_free_rate)
            self.circuit_breaker_threshold = state.get('circuit_breaker_threshold', self.circuit_breaker_threshold)
            self.daily_risk_used = state.get('daily_risk_used', self.daily_risk_used)
            self.weekly_risk_used = state.get('weekly_risk_used', self.weekly_risk_used)
            self.current_drawdown_pct = state.get('current_drawdown_pct', self.current_drawdown_pct)
            self.max_drawdown_pct = state.get('max_drawdown_pct', self.max_drawdown_pct)
            self.circuit_breaker_active = state.get('circuit_breaker_active', self.circuit_breaker_active)
            self.circuit_breaker_duration_minutes = state.get('circuit_breaker_duration_minutes', self.circuit_breaker_duration_minutes)
            
            # Load datetime objects
            if 'drawdown_start_date' in state and state['drawdown_start_date']:
                self.drawdown_start_date = datetime.fromisoformat(state['drawdown_start_date'])
            
            if 'circuit_breaker_end_time' in state and state['circuit_breaker_end_time']:
                self.circuit_breaker_end_time = datetime.fromisoformat(state['circuit_breaker_end_time'])
                
            if 'current_day' in state:
                self.current_day = datetime.fromisoformat(state['current_day']).date()
                
            if 'current_week_start' in state:
                self.current_week_start = datetime.fromisoformat(state['current_week_start']).date()
                
            # Load active and closed trades
            self.active_trades = {}
            for trade in state.get('active_trades', []):
                if 'timestamp' in trade and trade['timestamp']:
                    trade['timestamp'] = datetime.fromisoformat(trade['timestamp'])
                if 'trade_id' in trade:
                    self.active_trades[trade['trade_id']] = trade
                    
            self.closed_trades = []
            for trade in state.get('closed_trades', []):
                if 'timestamp' in trade and trade['timestamp']:
                    trade['timestamp'] = datetime.fromisoformat(trade['timestamp'])
                if 'exit_time' in trade and trade['exit_time']:
                    trade['exit_time'] = datetime.fromisoformat(trade['exit_time'])
                self.closed_trades.append(trade)
                
            # Load balance history
            self.balance_history = []
            for record in state.get('balance_history', []):
                if 'timestamp' in record:
                    record['timestamp'] = datetime.fromisoformat(record['timestamp'])
                self.balance_history.append(record)
                
            # Rebuild daily and weekly trades lists
            self._rebuild_risk_lists()
            
            logger.info(f"Loaded risk manager state from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading risk manager state: {e}")
            return False
    
    def _check_new_day(self) -> None:
        """Kiểm tra và reset rủi ro ngày nếu sang ngày mới"""
        today = datetime.now().date()
        if today != self.current_day:
            # Reset daily risk
            self.daily_risk_used = 0.0
            self.daily_trades = []
            self.current_day = today
            logger.info(f"New day detected, reset daily risk: {today}")
    
    def _check_new_week(self) -> None:
        """Kiểm tra và reset rủi ro tuần nếu sang tuần mới"""
        week_start = self._get_week_start(datetime.now())
        if week_start != self.current_week_start:
            # Reset weekly risk
            self.weekly_risk_used = 0.0
            self.weekly_trades = []
            self.current_week_start = week_start
            logger.info(f"New week detected, reset weekly risk: Week starting {week_start}")
    
    def _get_week_start(self, dt: datetime) -> datetime.date:
        """Lấy ngày đầu tuần (thứ 2) của một ngày"""
        # Adjust day of week (0 is Monday in Python's datetime)
        return (dt - timedelta(days=dt.weekday())).date()
    
    def _calculate_equity(self) -> float:
        """Tính toán equity (balance + unrealized PnL)"""
        # For now, we're just using balance as equity
        # In a real system, you'd calculate unrealized PnL from active trades
        return self.account_balance
    
    def _calculate_drawdown_duration(self) -> int:
        """Tính toán thời gian drawdown (ngày)"""
        if not self.drawdown_start_date or self.current_drawdown_pct == 0:
            return 0
            
        # Calculate days in drawdown
        days = (datetime.now() - self.drawdown_start_date).days
        return max(0, days)
    
    def _rebuild_risk_lists(self) -> None:
        """Xây dựng lại danh sách giao dịch ngày/tuần từ active_trades"""
        today = datetime.now().date()
        week_start = self._get_week_start(datetime.now())
        
        self.daily_trades = []
        self.weekly_trades = []
        
        for trade_id, trade in self.active_trades.items():
            if 'timestamp' in trade:
                trade_date = trade['timestamp'].date()
                
                # Add to daily trades if from today
                if trade_date == today:
                    self.daily_trades.append(trade_id)
                    
                # Add to weekly trades if from this week
                trade_week_start = self._get_week_start(trade['timestamp'])
                if trade_week_start == week_start:
                    self.weekly_trades.append(trade_id)


class CorrelationRiskManager:
    """Lớp quản lý rủi ro tương quan giữa các vị thế"""
    
    def __init__(self, max_correlation_exposure: float = 2.0, 
                correlation_threshold: float = 0.7):
        """
        Khởi tạo Correlation Risk Manager.
        
        Args:
            max_correlation_exposure (float): Mức phơi nhiễm tương quan tối đa
            correlation_threshold (float): Ngưỡng tương quan để tính phơi nhiễm
        """
        self.max_correlation_exposure = max(1.0, max_correlation_exposure)
        self.correlation_threshold = max(0.5, min(correlation_threshold, 1.0))
        
        # Lưu trữ dữ liệu tương quan
        self.correlation_matrix = {}
        
        # Lưu trữ các vị thế hiện tại
        self.current_positions = {}  # {symbol: {'side': str, 'position_size': float, 'position_value': float}}
    
    def update_correlation_data(self, correlation_matrix: Dict[str, Dict[str, float]]) -> None:
        """
        Cập nhật ma trận tương quan.
        
        Args:
            correlation_matrix (Dict[str, Dict[str, float]]): Ma trận tương quan
                {symbol1: {symbol1: 1.0, symbol2: 0.7, ...}, ...}
        """
        self.correlation_matrix = correlation_matrix
        logger.info(f"Updated correlation data for {len(correlation_matrix)} symbols")
    
    def update_position(self, symbol: str, side: str, position_size: float,
                      position_value: float) -> None:
        """
        Cập nhật một vị thế.
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng vị thế ('LONG' hoặc 'SHORT')
            position_size (float): Kích thước vị thế (số lượng)
            position_value (float): Giá trị vị thế (USD)
        """
        # Update or add position
        self.current_positions[symbol] = {
            'side': side.upper(),
            'position_size': position_size,
            'position_value': position_value
        }
        
        logger.info(f"Updated position for {symbol}: {side} {position_size} (${position_value:.2f})")
    
    def remove_position(self, symbol: str) -> bool:
        """
        Xóa một vị thế.
        
        Args:
            symbol (str): Mã cặp giao dịch
            
        Returns:
            bool: True nếu xóa thành công, False nếu không
        """
        if symbol in self.current_positions:
            del self.current_positions[symbol]
            logger.info(f"Removed position for {symbol}")
            return True
        else:
            logger.warning(f"Position {symbol} not found")
            return False
    
    def calculate_correlation_exposure(self, symbol: str, side: str, 
                                     position_value: float) -> Dict:
        """
        Tính toán mức phơi nhiễm tương quan nếu thêm một vị thế mới.
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng vị thế ('LONG' hoặc 'SHORT')
            position_value (float): Giá trị vị thế (USD)
            
        Returns:
            Dict: Thông tin phơi nhiễm
                {
                    'exposure_ratio': float,
                    'is_acceptable': bool,
                    'correlated_symbols': List[Dict],
                    'total_correlated_value': float,
                    'direction_adjusted_exposure': float
                }
        """
        # Validate input
        if not self.correlation_matrix:
            logger.warning("No correlation data available")
            return {
                'exposure_ratio': 0.0,
                'is_acceptable': True,
                'correlated_symbols': [],
                'total_correlated_value': 0.0,
                'direction_adjusted_exposure': 0.0
            }
            
        side = side.upper()
        
        # Calculate correlation exposure
        correlated_symbols = []
        total_correlated_value = 0.0
        direction_adjusted_exposure = 0.0
        
        for existing_symbol, position in self.current_positions.items():
            # Skip if same symbol (will be replaced if exists)
            if existing_symbol == symbol:
                continue
                
            # Get correlation coefficient
            correlation = self._get_correlation(symbol, existing_symbol)
            
            # Only consider significant correlations
            if abs(correlation) >= self.correlation_threshold:
                existing_side = position['side']
                existing_value = position['position_value']
                
                # Calculate direction factor
                # If correlation is positive and sides are same, or correlation is negative and sides are opposite,
                # then positions amplify each other (positive factor)
                # Otherwise, they hedge each other (negative factor)
                same_direction = (side == existing_side)
                direction_factor = 1 if (correlation > 0 and same_direction) or (correlation < 0 and not same_direction) else -1
                
                # Calculate exposure
                exposure = abs(correlation) * direction_factor * existing_value
                
                # Add to total
                direction_adjusted_exposure += exposure
                
                # Track correlated symbols for reporting
                correlated_symbols.append({
                    'symbol': existing_symbol,
                    'correlation': correlation,
                    'side': existing_side,
                    'position_value': existing_value,
                    'direction_factor': direction_factor,
                    'exposure': exposure
                })
                
                # Add to total correlated value
                total_correlated_value += existing_value
        
        # Calculate exposure ratio
        if position_value > 0:
            # Ratio of correlated exposure to position value
            exposure_ratio = (direction_adjusted_exposure + position_value) / position_value
        else:
            exposure_ratio = 0.0
            
        # Determine if acceptable
        is_acceptable = exposure_ratio <= self.max_correlation_exposure
        
        return {
            'exposure_ratio': exposure_ratio,
            'is_acceptable': is_acceptable,
            'correlated_symbols': correlated_symbols,
            'total_correlated_value': total_correlated_value,
            'direction_adjusted_exposure': direction_adjusted_exposure
        }
    
    def suggest_position_adjustments(self, max_exposure_ratio: float = None) -> Dict:
        """
        Đề xuất điều chỉnh vị thế để giảm rủi ro tương quan.
        
        Args:
            max_exposure_ratio (float, optional): Mức phơi nhiễm tối đa, mặc định là max_correlation_exposure
            
        Returns:
            Dict: Đề xuất điều chỉnh
                {
                    'adjustments_needed': bool,
                    'overall_exposure': float,
                    'position_adjustments': Dict[str, Dict],
                    'high_exposure_positions': List[str]
                }
        """
        if not self.current_positions or not self.correlation_matrix:
            return {
                'adjustments_needed': False,
                'overall_exposure': 0.0,
                'position_adjustments': {},
                'high_exposure_positions': []
            }
            
        if max_exposure_ratio is None:
            max_exposure_ratio = self.max_correlation_exposure
            
        # Calculate current exposure for each position
        position_exposures = {}
        high_exposure_positions = []
        overall_exposure = 0.0
        
        for symbol, position in self.current_positions.items():
            side = position['side']
            value = position['position_value']
            
            # Skip if value is too small
            if value < 1.0:
                continue
                
            # Calculate exposure
            exposure_info = self.calculate_correlation_exposure(symbol, side, value)
            position_exposures[symbol] = exposure_info
            
            # Track high exposure positions
            if exposure_info['exposure_ratio'] > max_exposure_ratio:
                high_exposure_positions.append(symbol)
                
            # Add to overall exposure
            overall_exposure += exposure_info['exposure_ratio'] * value
            
        # Calculate overall exposure ratio
        total_value = sum(p['position_value'] for p in self.current_positions.values())
        if total_value > 0:
            overall_exposure_ratio = overall_exposure / total_value
        else:
            overall_exposure_ratio = 0.0
            
        # Determine if adjustments needed
        adjustments_needed = len(high_exposure_positions) > 0
        
        # Calculate suggested adjustments
        position_adjustments = {}
        
        for symbol in high_exposure_positions:
            position = self.current_positions[symbol]
            exposure_info = position_exposures[symbol]
            
            # Calculate how much to reduce
            current_ratio = exposure_info['exposure_ratio']
            target_ratio = max_exposure_ratio
            
            if current_ratio > 0:
                reduction_percentage = (current_ratio - target_ratio) / current_ratio * 100
                reduction_amount = position['position_value'] * reduction_percentage / 100
                
                position_adjustments[symbol] = {
                    'current_exposure': current_ratio,
                    'target_exposure': target_ratio,
                    'adjustment_percentage': reduction_percentage,
                    'adjustment_amount': reduction_amount,
                    'new_position_value': position['position_value'] - reduction_amount
                }
        
        return {
            'adjustments_needed': adjustments_needed,
            'overall_exposure': overall_exposure_ratio,
            'position_adjustments': position_adjustments,
            'high_exposure_positions': high_exposure_positions
        }
    
    def get_portfolio_correlation_heatmap(self) -> Dict:
        """
        Tạo dữ liệu heatmap tương quan danh mục.
        
        Returns:
            Dict: Dữ liệu heatmap
                {
                    'symbols': List[str],
                    'matrix': List[List[float]],
                    'exposures': Dict[str, float]
                }
        """
        if not self.current_positions:
            return {
                'symbols': [],
                'matrix': [],
                'exposures': {}
            }
            
        # Get all symbols in portfolio
        symbols = list(self.current_positions.keys())
        
        # Create correlation matrix
        matrix = []
        for symbol1 in symbols:
            row = []
            for symbol2 in symbols:
                # Get correlation
                correlation = self._get_correlation(symbol1, symbol2)
                row.append(correlation)
            matrix.append(row)
            
        # Calculate exposures
        exposures = {}
        for symbol, position in self.current_positions.items():
            side = position['side']
            value = position['position_value']
            
            exposure_info = self.calculate_correlation_exposure(symbol, side, value)
            exposures[symbol] = exposure_info['exposure_ratio']
            
        return {
            'symbols': symbols,
            'matrix': matrix,
            'exposures': exposures
        }
    
    def _get_correlation(self, symbol1: str, symbol2: str) -> float:
        """
        Lấy hệ số tương quan giữa hai symbol.
        
        Args:
            symbol1 (str): Symbol thứ nhất
            symbol2 (str): Symbol thứ hai
            
        Returns:
            float: Hệ số tương quan (-1 đến 1)
        """
        # If same symbol, correlation is 1
        if symbol1 == symbol2:
            return 1.0
            
        # Check if we have correlation data
        if symbol1 in self.correlation_matrix and symbol2 in self.correlation_matrix[symbol1]:
            return self.correlation_matrix[symbol1][symbol2]
        elif symbol2 in self.correlation_matrix and symbol1 in self.correlation_matrix[symbol2]:
            return self.correlation_matrix[symbol2][symbol1]
            
        # Default to 0 if not found
        return 0.0


class DrawdownManager:
    """Lớp quản lý drawdown và đề xuất kế hoạch phục hồi"""
    
    def __init__(self, initial_balance: float, max_drawdown_pct: float = 20.0,
                recovery_factor: float = 1.5, reduce_size_threshold: float = 5.0):
        """
        Khởi tạo Drawdown Manager.
        
        Args:
            initial_balance (float): Số dư ban đầu
            max_drawdown_pct (float): Phần trăm drawdown tối đa cho phép
            recovery_factor (float): Hệ số tính toán kế hoạch phục hồi
            reduce_size_threshold (float): Ngưỡng drawdown để bắt đầu giảm kích thước giao dịch
        """
        self.initial_balance = max(0.01, initial_balance)
        self.max_drawdown_pct = max(1.0, min(max_drawdown_pct, 50.0))
        self.recovery_factor = max(1.0, recovery_factor)
        self.reduce_size_threshold = max(1.0, min(reduce_size_threshold, max_drawdown_pct))
        
        # Tracking
        self.peak_balance = self.initial_balance
        self.current_balance = self.initial_balance
        self.drawdown_amount = 0.0
        self.drawdown_pct = 0.0
        
        # Drawdown history
        self.drawdown_history = []
        self.drawdown_start_date = None
    
    def update_balance(self, new_balance: float) -> Dict:
        """
        Cập nhật số dư và tính toán drawdown.
        
        Args:
            new_balance (float): Số dư mới
            
        Returns:
            Dict: Thông tin drawdown
                {
                    'balance': float,
                    'peak_balance': float,
                    'drawdown_amount': float,
                    'drawdown_pct': float,
                    'scaling': float
                }
        """
        # Prevent negative balance
        new_balance = max(0.01, new_balance)
        
        # Update current balance
        self.current_balance = new_balance
        
        # Update peak balance if new balance is higher
        if new_balance > self.peak_balance:
            self.peak_balance = new_balance
            self.drawdown_start_date = None
        
        # Calculate drawdown
        self.drawdown_amount = self.peak_balance - self.current_balance
        if self.peak_balance > 0:
            self.drawdown_pct = (self.drawdown_amount / self.peak_balance) * 100
        else:
            self.drawdown_pct = 0.0
            
        # Record drawdown start date if entering drawdown
        if self.drawdown_pct > 0 and self.drawdown_start_date is None:
            self.drawdown_start_date = datetime.now()
            
        # Add to history
        self.drawdown_history.append({
            'timestamp': datetime.now(),
            'balance': new_balance,
            'peak_balance': self.peak_balance,
            'drawdown_amount': self.drawdown_amount,
            'drawdown_pct': self.drawdown_pct
        })
        
        # Calculate position size scaling based on drawdown
        scaling = self._calculate_scaling()
        
        logger.info(f"Updated balance: {new_balance:.2f}, " +
                  f"Drawdown: {self.drawdown_pct:.2f}%, Scaling: {scaling:.2f}")
        
        return {
            'balance': self.current_balance,
            'peak_balance': self.peak_balance,
            'drawdown_amount': self.drawdown_amount,
            'drawdown_pct': self.drawdown_pct,
            'scaling': scaling
        }
    
    def should_take_trade(self, expected_win_rate: float = 0.5, 
                        risk_reward_ratio: float = 1.0) -> Dict:
        """
        Đánh giá xem có nên tiếp tục giao dịch dựa trên drawdown hiện tại.
        
        Args:
            expected_win_rate (float): Tỷ lệ thắng kỳ vọng (0-1)
            risk_reward_ratio (float): Tỷ lệ rủi ro/lợi nhuận
            
        Returns:
            Dict: Đánh giá
                {
                    'should_trade': bool,
                    'reason': str,
                    'scaling': float,
                    'drawdown_pct': float
                }
        """
        # Calculate expectancy
        expectancy = (expected_win_rate * risk_reward_ratio) - (1 - expected_win_rate)
        
        # Calculate scaling
        scaling = self._calculate_scaling()
        
        # If drawdown is too high, stop trading
        if self.drawdown_pct >= self.max_drawdown_pct:
            return {
                'should_trade': False,
                'reason': f"Excessive drawdown ({self.drawdown_pct:.2f}% >= {self.max_drawdown_pct:.2f}%)",
                'scaling': scaling,
                'drawdown_pct': self.drawdown_pct,
                'expectancy': expectancy
            }
            
        # If expectancy is negative, don't trade
        if expectancy <= 0:
            return {
                'should_trade': False,
                'reason': f"Negative expectancy ({expectancy:.2f})",
                'scaling': scaling,
                'drawdown_pct': self.drawdown_pct,
                'expectancy': expectancy
            }
            
        # For moderate drawdown, apply scaling
        if self.drawdown_pct > self.reduce_size_threshold:
            return {
                'should_trade': True,
                'reason': f"Trading with reduced size (scaling: {scaling:.2f})",
                'scaling': scaling,
                'drawdown_pct': self.drawdown_pct,
                'expectancy': expectancy
            }
            
        # Otherwise, trade normally
        return {
            'should_trade': True,
            'reason': "Normal trading conditions",
            'scaling': scaling,
            'drawdown_pct': self.drawdown_pct,
            'expectancy': expectancy
        }
    
    def calculate_recovery_plan(self, target_balance: float = None) -> Dict:
        """
        Tính toán kế hoạch phục hồi từ drawdown.
        
        Args:
            target_balance (float, optional): Số dư mục tiêu, mặc định là peak_balance
            
        Returns:
            Dict: Kế hoạch phục hồi
                {
                    'recovery_needed': bool,
                    'current_balance': float,
                    'target_balance': float,
                    'drawdown_pct': float,
                    'percentage_gain_needed': float,
                    'trades_needed': int,
                    'recommendations': List[str]
                }
        """
        if target_balance is None:
            target_balance = self.peak_balance
            
        # If no drawdown, no recovery needed
        if self.drawdown_pct < 1.0 or self.current_balance >= target_balance:
            return {
                'recovery_needed': False,
                'current_balance': self.current_balance,
                'target_balance': target_balance,
                'drawdown_pct': self.drawdown_pct,
                'percentage_gain_needed': 0.0,
                'trades_needed': 0,
                'recommendations': ["No recovery needed, account at or near peak balance."]
            }
            
        # Calculate percentage gain needed to recover
        percentage_gain_needed = ((target_balance / self.current_balance) - 1) * 100
        
        # Calculate trades needed (rough estimate with 1% gain per trade)
        trades_needed = int(percentage_gain_needed / (1.0 * self.recovery_factor))
        
        # Generate recommendations
        recommendations = []
        
        if percentage_gain_needed > 50:
            recommendations.append(f"Severe drawdown ({self.drawdown_pct:.1f}%). Consider pausing trading to reassess strategy.")
            recommendations.append(f"Recovery requires {percentage_gain_needed:.1f}% gain, approximately {trades_needed} successful trades.")
            recommendations.append("Focus on capital preservation until strategy proves effective again.")
        elif percentage_gain_needed > 20:
            recommendations.append(f"Significant drawdown ({self.drawdown_pct:.1f}%). Reduce position size by {self._calculate_scaling():.2f}x.")
            recommendations.append(f"Recovery requires {percentage_gain_needed:.1f}% gain, approximately {trades_needed} successful trades.")
            recommendations.append("Consider higher probability setups with better risk/reward.")
        else:
            recommendations.append(f"Moderate drawdown ({self.drawdown_pct:.1f}%). Maintain discipline and follow trading plan.")
            recommendations.append(f"Recovery requires {percentage_gain_needed:.1f}% gain, approximately {trades_needed} successful trades.")
            
        return {
            'recovery_needed': True,
            'current_balance': self.current_balance,
            'target_balance': target_balance,
            'drawdown_pct': self.drawdown_pct,
            'percentage_gain_needed': percentage_gain_needed,
            'trades_needed': trades_needed,
            'recommendations': recommendations
        }
    
    def get_drawdown_stats(self) -> Dict:
        """
        Lấy thống kê drawdown.
        
        Returns:
            Dict: Thống kê drawdown
        """
        # Calculate max drawdown
        max_drawdown_pct = max([record['drawdown_pct'] for record in self.drawdown_history]) if self.drawdown_history else 0.0
        
        # Calculate drawdown duration
        drawdown_duration = 0
        if self.drawdown_start_date:
            drawdown_duration = (datetime.now() - self.drawdown_start_date).days
            
        return {
            'current_drawdown_pct': self.drawdown_pct,
            'max_drawdown_pct': max_drawdown_pct,
            'drawdown_duration_days': drawdown_duration,
            'peak_balance': self.peak_balance,
            'current_balance': self.current_balance,
            'initial_balance': self.initial_balance,
            'scaling': self._calculate_scaling()
        }
    
    def _calculate_scaling(self) -> float:
        """
        Tính toán hệ số điều chỉnh kích thước vị thế dựa trên drawdown.
        
        Returns:
            float: Hệ số điều chỉnh (0-1)
        """
        # If no drawdown or below threshold, keep full size
        if self.drawdown_pct < self.reduce_size_threshold:
            return 1.0
            
        # If above max drawdown, stop trading (scaling = 0)
        if self.drawdown_pct >= self.max_drawdown_pct:
            return 0.0
            
        # Linear scaling between threshold and max
        range_pct = self.max_drawdown_pct - self.reduce_size_threshold
        excess_pct = self.drawdown_pct - self.reduce_size_threshold
        
        if range_pct > 0:
            scaling = 1.0 - (excess_pct / range_pct)
            return max(0.0, min(1.0, scaling))
        else:
            return 1.0  # Fallback


class StressTestManager:
    """Lớp thực hiện stress test cho các kịch bản thị trường khác nhau"""
    
    def __init__(self):
        """Khởi tạo Stress Test Manager."""
        # Định nghĩa các kịch bản stress test
        self.scenarios = {
            'market_crash': {
                'description': 'Market crash scenario with high correlation',
                'price_changes': {
                    'default': -0.15,  # -15% by default
                    'BTCUSDT': -0.20,  # -20% for BTC
                    'ETHUSDT': -0.25,  # -25% for ETH
                },
                'correlation_factor': 1.2,  # Correlations increase during crashes
                'volatility_increase': 2.5,  # Volatility increases
                'liquidity_decrease': 0.5,  # Liquidity decreases
                'slippage_factor': 3.0  # Slippage increases
            },
            'sector_rotation': {
                'description': 'Sector rotation with mixed performance',
                'price_changes': {
                    'default': -0.05,
                    'BTCUSDT': 0.05,
                    'ETHUSDT': 0.03,
                    'SOLUSDT': -0.10,
                    'AVAXUSDT': -0.08
                },
                'correlation_factor': 0.8,
                'volatility_increase': 1.5,
                'liquidity_decrease': 0.8,
                'slippage_factor': 1.5
            },
            'high_volatility': {
                'description': 'High volatility with no clear direction',
                'price_changes': {
                    'default': 0.0
                },
                'price_volatility': 0.15,  # Random changes up to ±15%
                'correlation_factor': 0.5,  # Correlations break down
                'volatility_increase': 3.0,
                'liquidity_decrease': 0.7,
                'slippage_factor': 2.0
            },
            'liquidity_crisis': {
                'description': 'Liquidity crisis with high slippage',
                'price_changes': {
                    'default': -0.10
                },
                'correlation_factor': 1.0,
                'volatility_increase': 2.0,
                'liquidity_decrease': 0.3,  # Severe liquidity reduction
                'slippage_factor': 5.0  # Extreme slippage
            },
            'bullish_momentum': {
                'description': 'Strong bullish momentum across the market',
                'price_changes': {
                    'default': 0.10,
                    'BTCUSDT': 0.15,
                    'ETHUSDT': 0.18
                },
                'correlation_factor': 1.1,
                'volatility_increase': 1.2,
                'liquidity_decrease': 1.0,  # No liquidity decrease
                'slippage_factor': 0.8  # Better than normal slippage
            }
        }
    
    def run_stress_test(self, positions: Dict, 
                      initial_portfolio_value: float = None,
                      correlation_matrix: Dict[str, Dict[str, float]] = None,
                      scenario_name: str = None) -> Dict:
        """
        Thực hiện stress test cho danh mục vị thế.
        
        Args:
            positions (Dict): Danh mục vị thế
                {symbol: {'side': str, 'quantity': float, 'entry_price': float, 'stop_loss': float, ...}}
            initial_portfolio_value (float, optional): Giá trị danh mục ban đầu
            correlation_matrix (Dict, optional): Ma trận tương quan
            scenario_name (str, optional): Tên kịch bản, None để chọn ngẫu nhiên
            
        Returns:
            Dict: Kết quả stress test
        """
        # Validate positions
        if not positions:
            return {
                'scenario_name': 'none',
                'description': 'No positions to test',
                'drawdown_amount': 0.0,
                'drawdown_percentage': 0.0,
                'portfolio_impact': [],
                'risk_metrics': {},
                'recommendations': ['No positions to test']
            }
            
        # Select scenario
        if scenario_name is None or scenario_name not in self.scenarios:
            # Choose random scenario
            scenario_name = np.random.choice(list(self.scenarios.keys()))
            
        scenario = self.scenarios[scenario_name]
        
        # Calculate initial portfolio value
        if initial_portfolio_value is None:
            initial_portfolio_value = sum(
                positions[symbol]['quantity'] * positions[symbol]['entry_price']
                for symbol in positions
            )
            
        # Apply scenario to positions
        position_results = {}
        portfolio_value_after = 0.0
        
        for symbol, position in positions.items():
            # Get position details
            side = position['side'].upper()
            quantity = position['quantity']
            entry_price = position['entry_price']
            
            # Calculate position value
            position_value = quantity * entry_price
            position_percentage = position_value / initial_portfolio_value if initial_portfolio_value > 0 else 0
            
            # Apply price change
            if scenario_name == 'high_volatility':
                # Random price change in high volatility scenario
                volatility = scenario['price_volatility']
                price_change = np.random.uniform(-volatility, volatility)
            else:
                # Get specified price change or default
                price_change = scenario['price_changes'].get(symbol, scenario['price_changes']['default'])
                
            # Apply direction-specific impact
            if side == 'LONG':
                # For long positions, price decrease is negative, increase is positive
                impact_pct = price_change
            else:  # 'SHORT'
                # For short positions, price decrease is positive, increase is negative
                impact_pct = -price_change
                
            # Calculate impact amount
            impact_amount = position_value * impact_pct
            
            # Apply slippage if has stop loss
            stop_loss_triggered = False
            slippage_impact = 0.0
            
            if 'stop_loss' in position:
                stop_loss = position['stop_loss']
                
                # Check if stop loss would be triggered
                if (side == 'LONG' and entry_price * (1 + price_change) < stop_loss) or \
                   (side == 'SHORT' and entry_price * (1 + price_change) > stop_loss):
                    
                    stop_loss_triggered = True
                    
                    # Calculate slippage on stop loss
                    slippage_pct = (scenario['slippage_factor'] - 1) * 0.01  # Base slippage 1%
                    
                    if side == 'LONG':
                        # For long, slippage makes stop loss execution worse (lower)
                        slippage_impact = position_value * slippage_pct * -1
                    else:  # 'SHORT'
                        # For short, slippage makes stop loss execution worse (higher)
                        slippage_impact = position_value * slippage_pct * -1
                        
            # Store result for this position
            position_results[symbol] = {
                'side': side,
                'position_value': position_value,
                'position_percentage': position_percentage,
                'price_change': price_change,
                'impact_pct': impact_pct,
                'impact_amount': impact_amount,
                'stop_loss_triggered': stop_loss_triggered,
                'slippage_impact': slippage_impact,
                'total_impact': impact_amount + slippage_impact,
                'position_value_after': position_value + impact_amount + slippage_impact
            }
            
            # Add to portfolio value after
            portfolio_value_after += position_value + impact_amount + slippage_impact
            
        # Calculate drawdown
        drawdown_amount = initial_portfolio_value - portfolio_value_after
        drawdown_percentage = (drawdown_amount / initial_portfolio_value) * 100 if initial_portfolio_value > 0 else 0
        
        # Calculate correlation-related impacts
        correlation_impacts = []
        
        if correlation_matrix and len(positions) > 1:
            # Apply correlation factor to exaggerate correlations during stress
            corr_factor = scenario.get('correlation_factor', 1.0)
            
            # For each pair of positions
            symbols = list(positions.keys())
            for i in range(len(symbols)):
                for j in range(i+1, len(symbols)):
                    symbol1 = symbols[i]
                    symbol2 = symbols[j]
                    
                    # Get correlation
                    correlation = self._get_correlation(symbol1, symbol2, correlation_matrix)
                    
                    # Apply correlation factor
                    adjusted_correlation = min(1.0, correlation * corr_factor) if correlation > 0 else max(-1.0, correlation * corr_factor)
                    
                    # Calculate combined impact
                    side1 = positions[symbol1]['side'].upper()
                    side2 = positions[symbol2]['side'].upper()
                    same_direction = (side1 == side2)
                    
                    # If correlation is positive and same direction, or negative and opposite direction,
                    # the combined effect is amplified
                    amplify = (adjusted_correlation > 0 and same_direction) or (adjusted_correlation < 0 and not same_direction)
                    
                    if abs(adjusted_correlation) > 0.5:  # Only report significant correlations
                        correlation_impacts.append({
                            'symbol1': symbol1,
                            'symbol2': symbol2,
                            'correlation': correlation,
                            'adjusted_correlation': adjusted_correlation,
                            'same_direction': same_direction,
                            'amplification': amplify
                        })
        
        # Calculate risk metrics
        var_95 = drawdown_amount * 1.2  # Simplified VaR calculation
        cvar_95 = drawdown_amount * 1.5  # Simplified CVaR calculation
        
        # Calculate recovery time estimate (rough)
        recovery_time_days = 0
        recovery_description = ""
        
        if drawdown_percentage > 0:
            # Assuming 0.5% daily growth
            daily_growth = 0.005
            recovery_time_days = int(np.log(initial_portfolio_value / portfolio_value_after) / np.log(1 + daily_growth))
            
            if recovery_time_days < 7:
                recovery_description = f"Quick recovery possible ({recovery_time_days} days)"
            elif recovery_time_days < 30:
                recovery_description = f"Moderate recovery time ({recovery_time_days} days)"
            else:
                recovery_description = f"Long recovery period ({recovery_time_days} days / {recovery_time_days/30:.1f} months)"
        else:
            recovery_description = "No recovery needed (no drawdown)"
            
        # Generate recommendations
        recommendations = []
        
        if drawdown_percentage > 20:
            recommendations.append(f"CRITICAL: Consider reducing position sizes immediately")
            recommendations.append(f"Set tighter stop losses to limit potential drawdown")
        elif drawdown_percentage > 10:
            recommendations.append(f"MODERATE RISK: Review position sizing and correlations")
            
        # Position-specific recommendations
        for symbol, result in position_results.items():
            if result['total_impact'] < -result['position_value'] * 0.1:  # > 10% loss
                recommendations.append(f"High impact on {symbol}: Consider hedging or reducing position size")
                
        # Correlation-specific recommendations
        high_corr_symbols = []
        for impact in correlation_impacts:
            if impact['amplification'] and abs(impact['adjusted_correlation']) > 0.7:
                high_corr_symbols.append((impact['symbol1'], impact['symbol2']))
                
        if high_corr_symbols:
            recommendations.append(f"High correlation risks between: {', '.join([f'{s1}-{s2}' for s1, s2 in high_corr_symbols])}")
            
        # General recommendations
        if scenario_name == 'market_crash':
            recommendations.append("Consider adding uncorrelated assets or inverse ETFs as hedges")
        elif scenario_name == 'liquidity_crisis':
            recommendations.append("Use limit orders and reduce position sizes in less liquid markets")
            
        # Sort portfolio impact by total impact (biggest loss first)
        portfolio_impact = []
        for symbol, result in position_results.items():
            portfolio_impact.append({
                'symbol': symbol,
                'side': result['side'],
                'position_value': result['position_value'],
                'portfolio_percentage': result['position_percentage'] * 100,
                'price_change_percentage': result['price_change'] * 100,
                'impact_amount': result['total_impact'],
                'impact_percentage': (result['total_impact'] / result['position_value']) * 100 if result['position_value'] > 0 else 0,
                'stop_loss_triggered': result['stop_loss_triggered']
            })
            
        portfolio_impact.sort(key=lambda x: x['impact_amount'])
        
        # Final result
        result = {
            'scenario_name': scenario_name,
            'description': scenario['description'],
            'drawdown_amount': drawdown_amount,
            'drawdown_percentage': drawdown_percentage,
            'initial_portfolio_value': initial_portfolio_value,
            'portfolio_value_after': portfolio_value_after,
            'portfolio_impact': portfolio_impact,
            'correlation_impacts': correlation_impacts,
            'risk_metrics': {
                'var_95': var_95,
                'cvar_95': cvar_95,
                'recovery_time_estimate': {
                    'days': recovery_time_days,
                    'description': recovery_description
                }
            },
            'recommendations': recommendations
        }
        
        return result
    
    def run_comprehensive_stress_test(self, positions: Dict,
                                    initial_portfolio_value: float = None,
                                    correlation_matrix: Dict[str, Dict[str, float]] = None) -> Dict:
        """
        Thực hiện stress test toàn diện với tất cả các kịch bản.
        
        Args:
            positions (Dict): Danh mục vị thế
            initial_portfolio_value (float, optional): Giá trị danh mục ban đầu
            correlation_matrix (Dict, optional): Ma trận tương quan
            
        Returns:
            Dict: Kết quả stress test toàn diện
        """
        # Run all scenarios
        results = {}
        worst_scenario = None
        worst_drawdown = 0
        
        for scenario_name in self.scenarios.keys():
            result = self.run_stress_test(
                positions=positions,
                initial_portfolio_value=initial_portfolio_value,
                correlation_matrix=correlation_matrix,
                scenario_name=scenario_name
            )
            
            results[scenario_name] = result
            
            # Track worst scenario
            if result['drawdown_percentage'] > worst_drawdown:
                worst_drawdown = result['drawdown_percentage']
                worst_scenario = scenario_name
                
        # Compile overall recommendations
        all_recommendations = []
        
        # Add worst scenario recommendations first
        if worst_scenario:
            worst_result = results[worst_scenario]
            all_recommendations.append(f"Worst scenario: {worst_scenario} ({worst_result['description']})")
            all_recommendations.append(f"Maximum drawdown: {worst_result['drawdown_percentage']:.1f}%")
            all_recommendations.extend(worst_result['recommendations'])
            
        # General recommendations
        if worst_drawdown > 25:
            all_recommendations.append("CRITICAL: Portfolio highly vulnerable to market shocks")
            all_recommendations.append("Consider diversification across uncorrelated assets")
        elif worst_drawdown > 15:
            all_recommendations.append("MODERATE RISK: Portfolio sensitive to certain market scenarios")
            all_recommendations.append("Review position sizing and stop loss levels")
        else:
            all_recommendations.append("LOW RISK: Portfolio relatively resilient to tested scenarios")
            
        # Compile summary
        summary = {
            'worst_scenario': worst_scenario,
            'worst_drawdown_percentage': worst_drawdown,
            'scenario_results': results,
            'comprehensive_recommendations': all_recommendations
        }
        
        return summary
    
    def _get_correlation(self, symbol1: str, symbol2: str, 
                       correlation_matrix: Dict[str, Dict[str, float]]) -> float:
        """
        Lấy hệ số tương quan giữa hai symbol.
        
        Args:
            symbol1 (str): Symbol thứ nhất
            symbol2 (str): Symbol thứ hai
            correlation_matrix (Dict): Ma trận tương quan
            
        Returns:
            float: Hệ số tương quan (-1 đến 1)
        """
        # If same symbol, correlation is 1
        if symbol1 == symbol2:
            return 1.0
            
        # Check if we have correlation data
        if correlation_matrix:
            if symbol1 in correlation_matrix and symbol2 in correlation_matrix[symbol1]:
                return correlation_matrix[symbol1][symbol2]
            elif symbol2 in correlation_matrix and symbol1 in correlation_matrix[symbol2]:
                return correlation_matrix[symbol2][symbol1]
                
        # Default to 0 if not found
        return 0.0


def create_risk_manager(manager_type: str, account_balance: float = 10000.0, **kwargs) -> Union[RiskManager, CorrelationRiskManager, DrawdownManager, StressTestManager]:
    """
    Factory function để tạo đối tượng quản lý rủi ro phù hợp.
    
    Args:
        manager_type (str): Loại quản lý rủi ro ('risk', 'correlation', 'drawdown', 'stress')
        account_balance (float): Số dư tài khoản ban đầu
        **kwargs: Các tham số bổ sung
        
    Returns:
        Union[RiskManager, CorrelationRiskManager, DrawdownManager, StressTestManager]: 
            Đối tượng quản lý rủi ro
    """
    manager_type = manager_type.lower()
    
    if manager_type == 'risk':
        return RiskManager(account_balance, **kwargs)
    elif manager_type == 'correlation':
        return CorrelationRiskManager(**kwargs)
    elif manager_type == 'drawdown':
        return DrawdownManager(account_balance, **kwargs)
    elif manager_type == 'stress':
        return StressTestManager()
    else:
        logger.warning(f"Unknown manager type: {manager_type}, falling back to RiskManager")
        return RiskManager(account_balance, **kwargs)


def main():
    """Hàm demo"""
    # Demo RiskManager
    print("=== Testing RiskManager ===")
    
    risk_manager = RiskManager(
        account_balance=10000.0,
        max_risk_per_trade=2.0,
        max_daily_risk=5.0,
        max_weekly_risk=10.0,
        max_drawdown_allowed=20.0
    )
    
    # Check trade risk
    trade_check = risk_manager.check_trade_risk(
        symbol="BTCUSDT",
        risk_amount=150.0,  # $150 risk
        entry_price=40000.0,
        stop_loss_price=39000.0
    )
    
    print(f"Trade check: {trade_check['allowed']}, Reason: {trade_check['reason']}")
    
    # Register trade
    trade_id = risk_manager.register_trade({
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry_price': 40000.0,
        'stop_loss_price': 39000.0,
        'risk_amount': 150.0,
        'quantity': 0.1,
        'risk_percentage': 1.5
    })
    
    print(f"Registered trade: {trade_id}")
    
    # Simulate profit
    risk_manager.close_trade(trade_id, 41000.0, 100.0)
    print(f"New balance: {risk_manager.account_balance}")
    
    # Demo CorrelationRiskManager
    print("\n=== Testing CorrelationRiskManager ===")
    
    correlation_manager = CorrelationRiskManager(
        max_correlation_exposure=2.0,
        correlation_threshold=0.7
    )
    
    # Set up correlation matrix
    correlation_matrix = {
        'BTCUSDT': {'BTCUSDT': 1.0, 'ETHUSDT': 0.8, 'SOLUSDT': 0.6},
        'ETHUSDT': {'BTCUSDT': 0.8, 'ETHUSDT': 1.0, 'SOLUSDT': 0.7},
        'SOLUSDT': {'BTCUSDT': 0.6, 'ETHUSDT': 0.7, 'SOLUSDT': 1.0}
    }
    
    correlation_manager.update_correlation_data(correlation_matrix)
    
    # Add position
    correlation_manager.update_position(
        symbol='BTCUSDT',
        side='LONG',
        position_size=0.1,
        position_value=4000.0
    )
    
    # Check exposure
    exposure = correlation_manager.calculate_correlation_exposure(
        symbol='ETHUSDT',
        side='LONG',
        position_value=3000.0
    )
    
    print(f"ETH exposure: {exposure['exposure_ratio']:.2f} (acceptable: {exposure['is_acceptable']})")
    
    # Demo DrawdownManager
    print("\n=== Testing DrawdownManager ===")
    
    drawdown_manager = DrawdownManager(
        initial_balance=10000.0,
        max_drawdown_pct=20.0
    )
    
    # Update with drawdown
    result = drawdown_manager.update_balance(9000.0)  # 10% drawdown
    print(f"Drawdown: {result['drawdown_pct']:.2f}%, Scaling: {result['scaling']}")
    
    # Check if should trade
    trade_decision = drawdown_manager.should_take_trade(
        expected_win_rate=0.6,
        risk_reward_ratio=2.0
    )
    
    print(f"Should trade: {trade_decision['should_trade']}, Reason: {trade_decision['reason']}")
    
    # Calculate recovery plan
    recovery_plan = drawdown_manager.calculate_recovery_plan()
    print(f"Recovery plan: {recovery_plan['percentage_gain_needed']:.2f}% needed, {recovery_plan['trades_needed']} trades")
    
    # Demo StressTestManager
    print("\n=== Testing StressTestManager ===")
    
    stress_manager = StressTestManager()
    
    # Define test portfolio
    positions = {
        'BTCUSDT': {
            'side': 'LONG',
            'quantity': 0.1,
            'entry_price': 40000.0,
            'stop_loss': 38000.0
        },
        'ETHUSDT': {
            'side': 'LONG',
            'quantity': 1.0,
            'entry_price': 2500.0,
            'stop_loss': 2300.0
        },
        'SOLUSDT': {
            'side': 'SHORT',
            'quantity': 10.0,
            'entry_price': 100.0,
            'stop_loss': 110.0
        }
    }
    
    # Run stress test
    result = stress_manager.run_stress_test(
        positions=positions,
        correlation_matrix=correlation_matrix,
        scenario_name='market_crash'
    )
    
    print(f"Stress test ({result['scenario_name']}): {result['drawdown_percentage']:.2f}% drawdown")
    print("Recommendations:")
    for rec in result['recommendations']:
        print(f"- {rec}")

if __name__ == "__main__":
    main()