"""
Module quản lý rủi ro nâng cao (Advanced Risk Management)

Module này cung cấp các tính năng quản lý rủi ro tiên tiến:
- Quản lý rủi ro dựa trên tương quan giữa các cặp tiền
- Điều chỉnh stop loss theo biến động thị trường
- Circuit breakers tự động dừng giao dịch khi thị trường biến động quá mức
- Kiểm soát drawdown bằng cách giảm kích thước giao dịch
- Mô phỏng kịch bản căng thẳng thị trường

Mục tiêu là bảo vệ vốn và tối ưu hóa hiệu suất dài hạn của hệ thống giao dịch.
"""

import logging
import numpy as np
import pandas as pd
import time
import threading
import json
from typing import Dict, List, Optional, Tuple, Union, Callable
from datetime import datetime, timedelta

# Cấu hình logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("risk_manager")

class RiskManager:
    """Lớp quản lý rủi ro tổng thể cho hệ thống giao dịch"""
    
    def __init__(self, account_balance: float, max_risk_per_trade: float = 2.0,
                max_daily_risk: float = 5.0, max_weekly_risk: float = 10.0,
                max_drawdown_allowed: float = 20.0, 
                risk_reduction_factor: float = 0.5):
        """
        Khởi tạo Risk Manager.
        
        Args:
            account_balance (float): Số dư tài khoản hiện tại
            max_risk_per_trade (float): % rủi ro tối đa cho mỗi giao dịch
            max_daily_risk (float): % rủi ro tối đa cho mỗi ngày
            max_weekly_risk (float): % rủi ro tối đa cho mỗi tuần
            max_drawdown_allowed (float): % drawdown tối đa được phép
            risk_reduction_factor (float): Hệ số giảm rủi ro khi gần ngưỡng
        """
        self.account_balance = account_balance
        self.max_risk_per_trade = max_risk_per_trade
        self.max_daily_risk = max_daily_risk
        self.max_weekly_risk = max_weekly_risk
        self.max_drawdown_allowed = max_drawdown_allowed
        self.risk_reduction_factor = risk_reduction_factor
        
        # Dữ liệu theo dõi
        self.peak_balance = account_balance
        self.current_drawdown = 0.0
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        self.daily_risk_used = 0.0
        self.weekly_risk_used = 0.0
        self.circuit_breakers_triggered = {}
        
        # Lịch sử giao dịch và drawdown
        self.trade_history = []
        self.drawdown_history = []
        
        # Ngày bắt đầu theo dõi
        self.current_day = datetime.now().date()
        self.current_week = self._get_week_number(datetime.now())
        
        # Trạng thái
        self.is_active = True
        self.current_status = 'normal'  # 'normal', 'caution', 'restricted', 'halted'
        
        # Thread giám sát
        self.monitoring_thread = None
        self.monitoring_active = False
    
    def update_account_balance(self, new_balance: float) -> None:
        """
        Cập nhật số dư tài khoản và tính toán drawdown.
        
        Args:
            new_balance (float): Số dư tài khoản mới
        """
        old_balance = self.account_balance
        self.account_balance = new_balance
        
        # Tính toán drawdown
        if new_balance > self.peak_balance:
            self.peak_balance = new_balance
            self.current_drawdown = 0.0
        else:
            self.current_drawdown = (self.peak_balance - new_balance) / self.peak_balance * 100
            
        # Lưu lịch sử drawdown
        self.drawdown_history.append({
            'timestamp': datetime.now(),
            'balance': new_balance,
            'peak_balance': self.peak_balance,
            'drawdown_pct': self.current_drawdown
        })
        
        # Cập nhật P&L
        pnl_change = new_balance - old_balance
        self.daily_pnl += pnl_change
        self.weekly_pnl += pnl_change
        
        # Kiểm tra ngày/tuần mới
        self._check_new_day()
        
        # Cập nhật trạng thái
        self._update_status()
        
        logger.info(f"Account balance updated: ${new_balance:.2f}, " +
                   f"Drawdown: {self.current_drawdown:.2f}%, " +
                   f"Daily P&L: ${self.daily_pnl:.2f}, " +
                   f"Weekly P&L: ${self.weekly_pnl:.2f}")
    
    def check_trade_risk(self, symbol: str, risk_amount: float, 
                       entry_price: float, stop_loss_price: float) -> Dict:
        """
        Kiểm tra rủi ro của một giao dịch và quyết định có cho phép hay không.
        
        Args:
            symbol (str): Mã cặp giao dịch
            risk_amount (float): Số tiền rủi ro dự kiến
            entry_price (float): Giá dự kiến vào lệnh
            stop_loss_price (float): Giá dự kiến stop loss
            
        Returns:
            Dict: Kết quả kiểm tra
                {
                    'allowed': bool,
                    'adjusted_risk_amount': float,
                    'reason': str,
                    'risk_percentage': float,
                    'risk_level': str
                }
        """
        # Tính % rủi ro
        risk_percentage = (risk_amount / self.account_balance) * 100
        
        # Kiểm tra rủi ro tối đa cho một giao dịch
        if risk_percentage > self.max_risk_per_trade:
            adjusted_risk = self.max_risk_per_trade * self.account_balance / 100
            return {
                'allowed': True,
                'adjusted_risk_amount': adjusted_risk,
                'risk_amount': risk_amount,
                'reason': f"Risk exceeds max_risk_per_trade ({self.max_risk_per_trade}%). Adjusted to {self.max_risk_per_trade}%.",
                'risk_percentage': self.max_risk_per_trade,
                'risk_level': 'adjusted'
            }
        
        # Kiểm tra rủi ro tích lũy trong ngày
        daily_risk_projected = self.daily_risk_used + risk_percentage
        if daily_risk_projected > self.max_daily_risk:
            if self.daily_risk_used >= self.max_daily_risk:
                return {
                    'allowed': False,
                    'adjusted_risk_amount': 0,
                    'risk_amount': risk_amount,
                    'reason': f"Daily risk limit reached ({self.daily_risk_used:.2f}% >= {self.max_daily_risk}%).",
                    'risk_percentage': 0,
                    'risk_level': 'denied'
                }
            else:
                remaining_risk = self.max_daily_risk - self.daily_risk_used
                adjusted_risk = remaining_risk * self.account_balance / 100
                return {
                    'allowed': True,
                    'adjusted_risk_amount': adjusted_risk,
                    'risk_amount': risk_amount,
                    'reason': f"Limited by remaining daily risk ({remaining_risk:.2f}%).",
                    'risk_percentage': remaining_risk,
                    'risk_level': 'adjusted'
                }
        
        # Kiểm tra rủi ro tích lũy trong tuần
        weekly_risk_projected = self.weekly_risk_used + risk_percentage
        if weekly_risk_projected > self.max_weekly_risk:
            if self.weekly_risk_used >= self.max_weekly_risk:
                return {
                    'allowed': False,
                    'adjusted_risk_amount': 0,
                    'risk_amount': risk_amount,
                    'reason': f"Weekly risk limit reached ({self.weekly_risk_used:.2f}% >= {self.max_weekly_risk}%).",
                    'risk_percentage': 0,
                    'risk_level': 'denied'
                }
            else:
                remaining_risk = self.max_weekly_risk - self.weekly_risk_used
                adjusted_risk = remaining_risk * self.account_balance / 100
                return {
                    'allowed': True,
                    'adjusted_risk_amount': adjusted_risk,
                    'risk_amount': risk_amount,
                    'reason': f"Limited by remaining weekly risk ({remaining_risk:.2f}%).",
                    'risk_percentage': remaining_risk,
                    'risk_level': 'adjusted'
                }
        
        # Kiểm tra drawdown
        if self.current_drawdown > self.max_drawdown_allowed:
            return {
                'allowed': False,
                'adjusted_risk_amount': 0,
                'risk_amount': risk_amount,
                'reason': f"Max drawdown exceeded ({self.current_drawdown:.2f}% > {self.max_drawdown_allowed}%).",
                'risk_percentage': 0,
                'risk_level': 'denied'
            }
        
        # Điều chỉnh rủi ro dựa trên drawdown
        if self.current_drawdown > self.max_drawdown_allowed * 0.7:  # Đang tiến gần ngưỡng
            reduction_ratio = 1 - (self.current_drawdown / self.max_drawdown_allowed) * self.risk_reduction_factor
            adjusted_risk = risk_amount * max(0.1, reduction_ratio)  # Ít nhất giảm 10%
            adjusted_percentage = (adjusted_risk / self.account_balance) * 100
            
            return {
                'allowed': True,
                'adjusted_risk_amount': adjusted_risk,
                'risk_amount': risk_amount,
                'reason': f"Risk reduced due to high drawdown ({self.current_drawdown:.2f}%).",
                'risk_percentage': adjusted_percentage,
                'risk_level': 'reduced'
            }
        
        # Kiểm tra xem symbol có bị circuit breaker không
        if symbol in self.circuit_breakers_triggered:
            cb_info = self.circuit_breakers_triggered[symbol]
            if cb_info['active'] and datetime.now() < cb_info['expiry']:
                return {
                    'allowed': False,
                    'adjusted_risk_amount': 0,
                    'risk_amount': risk_amount,
                    'reason': f"Circuit breaker active for {symbol} until {cb_info['expiry'].strftime('%H:%M:%S')}.",
                    'risk_percentage': 0,
                    'risk_level': 'denied'
                }
        
        # Kiểm tra trạng thái tổng thể
        if self.current_status == 'halted':
            return {
                'allowed': False,
                'adjusted_risk_amount': 0,
                'risk_amount': risk_amount,
                'reason': f"All trading halted. Status: {self.current_status}",
                'risk_percentage': 0,
                'risk_level': 'denied'
            }
        elif self.current_status == 'restricted' or self.current_status == 'caution':
            adjusted_ratio = 0.25 if self.current_status == 'restricted' else 0.5
            adjusted_risk = risk_amount * adjusted_ratio
            adjusted_percentage = (adjusted_risk / self.account_balance) * 100
            
            return {
                'allowed': True,
                'adjusted_risk_amount': adjusted_risk,
                'risk_amount': risk_amount,
                'reason': f"Risk reduced due to {self.current_status} status.",
                'risk_percentage': adjusted_percentage,
                'risk_level': 'reduced'
            }
        
        # Nếu không có vấn đề gì, cho phép giao dịch với rủi ro đầy đủ
        return {
            'allowed': True,
            'adjusted_risk_amount': risk_amount,
            'risk_amount': risk_amount,
            'reason': "Trade allowed with full risk.",
            'risk_percentage': risk_percentage,
            'risk_level': 'normal'
        }
    
    def register_trade(self, trade: Dict) -> None:
        """
        Đăng ký một giao dịch mới trong hệ thống quản lý rủi ro.
        
        Args:
            trade (Dict): Thông tin giao dịch
                {
                    'symbol': str,
                    'side': str,
                    'entry_price': float,
                    'stop_loss_price': float,
                    'take_profit_price': float,
                    'quantity': float,
                    'risk_amount': float,
                    'risk_percentage': float,
                    'timestamp': datetime
                }
        """
        # Thêm vào lịch sử
        self.trade_history.append(trade)
        
        # Cập nhật rủi ro đã sử dụng
        self.daily_risk_used += trade.get('risk_percentage', 0)
        self.weekly_risk_used += trade.get('risk_percentage', 0)
        
        logger.info(f"Trade registered: {trade['symbol']} {trade['side']} " +
                   f"Risk: {trade['risk_percentage']:.2f}% (${trade['risk_amount']:.2f}), " +
                   f"Daily risk used: {self.daily_risk_used:.2f}%, " +
                   f"Weekly risk used: {self.weekly_risk_used:.2f}%")
    
    def update_trade_result(self, trade_id: str, result: Dict) -> None:
        """
        Cập nhật kết quả của một giao dịch.
        
        Args:
            trade_id (str): ID của giao dịch
            result (Dict): Kết quả giao dịch
                {
                    'exit_price': float,
                    'exit_time': datetime,
                    'profit_loss': float,
                    'profit_loss_pct': float,
                    'status': str  # 'win', 'loss', 'breakeven'
                }
        """
        # Tìm giao dịch trong lịch sử
        for trade in self.trade_history:
            if trade.get('id') == trade_id:
                # Cập nhật thông tin
                trade.update(result)
                
                # Nếu giao dịch thắng, giảm rủi ro đã sử dụng
                if result.get('status') == 'win':
                    # Không thay đổi daily_risk_used và weekly_risk_used
                    # vì đó là rủi ro tiềm ẩn ban đầu, không phải rủi ro thực tế
                    pass
                
                logger.info(f"Trade result updated: {trade_id} {result['status']} " +
                           f"P&L: ${result['profit_loss']:.2f} ({result['profit_loss_pct']:.2f}%)")
                break
    
    def calculate_dynamic_stop_loss(self, symbol: str, side: str, entry_price: float,
                                 initial_stop_price: float, volatility: float = None,
                                 atr_value: float = None, bars_passed: int = 0) -> float:
        """
        Tính toán giá stop loss động dựa trên biến động thị trường.
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng vị thế ('LONG' hoặc 'SHORT')
            entry_price (float): Giá vào lệnh
            initial_stop_price (float): Giá stop loss ban đầu
            volatility (float, optional): Chỉ số biến động (% thay đổi)
            atr_value (float, optional): Giá trị ATR (Average True Range)
            bars_passed (int): Số nến đã trôi qua từ khi vào lệnh
            
        Returns:
            float: Giá stop loss điều chỉnh
        """
        # Tính khoảng cách ban đầu từ entry đến stop
        initial_stop_distance = abs(entry_price - initial_stop_price)
        
        # Nếu không cung cấp biến động, sử dụng khoảng cách ban đầu
        if volatility is None and atr_value is None:
            adjusted_stop_distance = initial_stop_distance
        else:
            # Ưu tiên sử dụng ATR nếu có
            if atr_value is not None:
                volatility_factor = atr_value
            else:
                # Chuẩn hóa biến động từ % sang đơn vị giá
                volatility_factor = entry_price * (volatility / 100)
                
            # Điều chỉnh khoảng cách stop loss dựa trên biến động
            adjusted_stop_distance = max(initial_stop_distance, volatility_factor * 1.5)
        
        # Điều chỉnh stop loss theo thời gian (trailing stop)
        if bars_passed > 0:
            # Tính trailing factor dựa trên số nến đã trôi qua
            trailing_factor = min(0.5, bars_passed * 0.05)  # Tối đa giảm 50% khoảng cách
            adjusted_stop_distance *= (1 - trailing_factor)
        
        # Tính giá stop loss mới
        if side.upper() == 'LONG':
            new_stop = max(initial_stop_price, entry_price - adjusted_stop_distance)
        else:  # SHORT
            new_stop = min(initial_stop_price, entry_price + adjusted_stop_distance)
        
        logger.info(f"Dynamic stop loss calculated for {symbol} {side}: " +
                   f"Initial: {initial_stop_price:.2f}, New: {new_stop:.2f}, " +
                   f"Volatility factor: {volatility_factor if 'volatility_factor' in locals() else 'N/A'}, " +
                   f"Bars passed: {bars_passed}")
        
        return new_stop
    
    def check_and_trigger_circuit_breaker(self, symbol: str, price_change_pct: float,
                                       volume_surge_factor: float = None,
                                       duration_minutes: int = 30) -> bool:
        """
        Kiểm tra và kích hoạt circuit breaker nếu biến động quá mức.
        
        Args:
            symbol (str): Mã cặp giao dịch
            price_change_pct (float): % thay đổi giá trong một khoảng thời gian ngắn
            volume_surge_factor (float, optional): Hệ số tăng đột biến của khối lượng
            duration_minutes (int): Thời gian hiệu lực của circuit breaker (phút)
            
        Returns:
            bool: True nếu circuit breaker được kích hoạt, False nếu không
        """
        # Ngưỡng mặc định
        price_change_threshold = 5.0  # 5% trong thời gian ngắn
        volume_surge_threshold = 3.0  # Khối lượng tăng gấp 3 lần TB
        
        # Kiểm tra điều kiện kích hoạt
        price_condition = abs(price_change_pct) > price_change_threshold
        volume_condition = volume_surge_factor is None or volume_surge_factor > volume_surge_threshold
        
        if price_condition and volume_condition:
            # Tính thời gian hết hạn
            expiry_time = datetime.now() + timedelta(minutes=duration_minutes)
            
            # Kích hoạt circuit breaker
            self.circuit_breakers_triggered[symbol] = {
                'active': True,
                'trigger_time': datetime.now(),
                'expiry': expiry_time,
                'price_change_pct': price_change_pct,
                'volume_surge_factor': volume_surge_factor
            }
            
            logger.warning(f"Circuit breaker triggered for {symbol}! " +
                          f"Price change: {price_change_pct:.2f}%, " +
                          f"Volume surge: {volume_surge_factor if volume_surge_factor else 'N/A'}, " +
                          f"Active until: {expiry_time.strftime('%H:%M:%S')}")
            
            return True
        
        return False
    
    def _start_monitoring(self, check_interval: int = 60) -> None:
        """
        Bắt đầu thread giám sát.
        
        Args:
            check_interval (int): Thời gian giữa các lần kiểm tra (giây)
        """
        if self.monitoring_thread is not None and self.monitoring_thread.is_alive():
            logger.warning("Monitoring thread is already running")
            return
            
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(check_interval,)
        )
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        logger.info(f"Risk monitoring started with interval: {check_interval} seconds")
    
    def _stop_monitoring(self) -> None:
        """Dừng thread giám sát"""
        self.monitoring_active = False
        if self.monitoring_thread is not None:
            # Thread sẽ tự kết thúc ở lần kiểm tra tiếp theo
            logger.info("Risk monitoring stopping...")
    
    def _monitoring_loop(self, check_interval: int) -> None:
        """
        Vòng lặp giám sát.
        
        Args:
            check_interval (int): Thời gian giữa các lần kiểm tra (giây)
        """
        while self.monitoring_active:
            try:
                # Kiểm tra các circuit breaker hết hạn
                self._check_circuit_breakers()
                
                # Kiểm tra ngày/tuần mới
                self._check_new_day()
                
                # Cập nhật trạng thái
                self._update_status()
                
                # Lưu dữ liệu định kỳ
                self._save_state()
                
            except Exception as e:
                logger.error(f"Error in risk monitoring loop: {e}")
                
            # Chờ đến lần kiểm tra tiếp theo
            time.sleep(check_interval)
        
        logger.info("Risk monitoring stopped")
    
    def _check_circuit_breakers(self) -> None:
        """Kiểm tra và cập nhật trạng thái các circuit breaker"""
        now = datetime.now()
        
        for symbol in list(self.circuit_breakers_triggered.keys()):
            cb_info = self.circuit_breakers_triggered[symbol]
            
            if cb_info['active'] and now >= cb_info['expiry']:
                # Hết thời gian hiệu lực, tắt circuit breaker
                cb_info['active'] = False
                logger.info(f"Circuit breaker for {symbol} has expired")
    
    def _check_new_day(self) -> None:
        """Kiểm tra và xử lý nếu là ngày/tuần mới"""
        today = datetime.now().date()
        this_week = self._get_week_number(datetime.now())
        
        if today != self.current_day:
            # Ngày mới, reset rủi ro hàng ngày
            logger.info(f"New day detected: {today}. Resetting daily risk counters.")
            self.daily_risk_used = 0.0
            self.daily_pnl = 0.0
            self.current_day = today
            
        if this_week != self.current_week:
            # Tuần mới, reset rủi ro hàng tuần
            logger.info(f"New week detected: {this_week}. Resetting weekly risk counters.")
            self.weekly_risk_used = 0.0
            self.weekly_pnl = 0.0
            self.current_week = this_week
    
    def _update_status(self) -> None:
        """Cập nhật trạng thái tổng thể dựa trên các chỉ số rủi ro"""
        old_status = self.current_status
        
        # Kiểm tra drawdown
        if self.current_drawdown >= self.max_drawdown_allowed:
            new_status = 'halted'
        elif self.current_drawdown >= self.max_drawdown_allowed * 0.8:
            new_status = 'restricted'
        elif self.current_drawdown >= self.max_drawdown_allowed * 0.5:
            new_status = 'caution'
        else:
            new_status = 'normal'
            
        # Kiểm tra rủi ro hàng ngày
        if self.daily_risk_used >= self.max_daily_risk:
            new_status = min('halted', new_status) if new_status == 'halted' else 'restricted'
        elif self.daily_risk_used >= self.max_daily_risk * 0.8:
            new_status = min('restricted', new_status) if new_status in ['halted', 'restricted'] else 'caution'
            
        # Kiểm tra rủi ro hàng tuần
        if self.weekly_risk_used >= self.max_weekly_risk:
            new_status = min('halted', new_status) if new_status == 'halted' else 'restricted'
        elif self.weekly_risk_used >= self.max_weekly_risk * 0.8:
            new_status = min('restricted', new_status) if new_status in ['halted', 'restricted'] else 'caution'
            
        # Cập nhật nếu thay đổi
        if new_status != old_status:
            self.current_status = new_status
            logger.warning(f"Risk status changed: {old_status} -> {new_status}")
            
            # Thực hiện xử lý đặc biệt khi trạng thái thay đổi
            if new_status == 'halted' and old_status != 'halted':
                logger.critical("TRADING HALTED! Maximum risk thresholds exceeded.")
                # Ở đây có thể thêm code để đóng tất cả các vị thế nếu cần
                
            elif new_status == 'restricted' and old_status not in ['restricted', 'halted']:
                logger.warning("Trading restricted! Risk thresholds approaching limits.")
                # Ở đây có thể thêm code để giảm kích thước vị thế mặc định
    
    def _save_state(self) -> None:
        """Lưu trạng thái của risk manager"""
        state = {
            'timestamp': datetime.now().isoformat(),
            'account_balance': self.account_balance,
            'peak_balance': self.peak_balance,
            'current_drawdown': self.current_drawdown,
            'daily_pnl': self.daily_pnl,
            'weekly_pnl': self.weekly_pnl,
            'daily_risk_used': self.daily_risk_used,
            'weekly_risk_used': self.weekly_risk_used,
            'current_status': self.current_status,
            'circuit_breakers': {
                k: {
                    'active': v['active'],
                    'trigger_time': v['trigger_time'].isoformat(),
                    'expiry': v['expiry'].isoformat(),
                    'price_change_pct': v['price_change_pct'],
                    'volume_surge_factor': v['volume_surge_factor']
                } for k, v in self.circuit_breakers_triggered.items()
            }
        }
        
        # Ở đây có thể lưu state vào file nếu cần
        # with open('risk_manager_state.json', 'w') as f:
        #     json.dump(state, f, indent=2)
    
    def _get_week_number(self, dt: datetime) -> int:
        """
        Lấy số tuần trong năm.
        
        Args:
            dt (datetime): Đối tượng datetime
            
        Returns:
            int: Số tuần trong năm (1-53)
        """
        return dt.isocalendar()[1]


class CorrelationRiskManager:
    """Quản lý rủi ro dựa trên tương quan giữa các cặp tiền"""
    
    def __init__(self, max_correlation_exposure: float = 2.0,
                correlation_data: Dict[str, Dict[str, float]] = None, 
                correlation_threshold: float = 0.7):
        """
        Khởi tạo Correlation Risk Manager.
        
        Args:
            max_correlation_exposure (float): Hệ số giới hạn tổng phơi nhiễm
            correlation_data (Dict[str, Dict[str, float]], optional): Ma trận tương quan
            correlation_threshold (float): Ngưỡng tương quan cần xem xét (0-1)
        """
        self.max_correlation_exposure = max_correlation_exposure
        self.correlation_threshold = correlation_threshold
        self.correlation_data = correlation_data or {}
        
        # Dữ liệu theo dõi vị thế
        self.active_positions = {}  # {symbol: {'side': str, 'size': float, 'value': float}}
    
    def update_correlation_data(self, correlation_data: Dict[str, Dict[str, float]]) -> None:
        """
        Cập nhật ma trận tương quan.
        
        Args:
            correlation_data (Dict[str, Dict[str, float]]): Ma trận tương quan
        """
        self.correlation_data = correlation_data
        logger.info("Correlation matrix updated")
    
    def update_position(self, symbol: str, side: str, position_size: float, 
                      position_value: float, is_active: bool = True) -> None:
        """
        Cập nhật thông tin vị thế.
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng vị thế ('LONG' hoặc 'SHORT')
            position_size (float): Kích thước vị thế
            position_value (float): Giá trị vị thế (USD)
            is_active (bool): True nếu vị thế đang mở, False nếu đã đóng
        """
        if is_active:
            self.active_positions[symbol] = {
                'side': side.upper(),
                'size': position_size,
                'value': position_value
            }
        elif symbol in self.active_positions:
            del self.active_positions[symbol]
    
    def calculate_correlation_exposure(self, symbol: str, side: str, 
                                    position_value: float) -> Dict:
        """
        Tính toán tổng phơi nhiễm tương quan nếu thêm vị thế mới.
        
        Args:
            symbol (str): Mã cặp giao dịch mới
            side (str): Hướng vị thế mới ('LONG' hoặc 'SHORT')
            position_value (float): Giá trị vị thế mới (USD)
            
        Returns:
            Dict: Phân tích phơi nhiễm tương quan
                {
                    'total_exposure': float,
                    'max_allowed': float,
                    'is_acceptable': bool,
                    'exposure_ratio': float,
                    'correlated_positions': list,
                    'correlation_factors': dict
                }
        """
        side = side.upper()
        
        # Nếu không có ma trận tương quan hoặc không có vị thế khác, không có vấn đề gì
        if not self.correlation_data or not self.active_positions:
            return {
                'total_exposure': position_value,
                'max_allowed': position_value * self.max_correlation_exposure,
                'is_acceptable': True,
                'exposure_ratio': 1.0,
                'correlated_positions': [],
                'correlation_factors': {}
            }
        
        # Tính toán phơi nhiễm
        total_exposure = position_value
        effective_exposure = position_value
        correlated_positions = []
        correlation_factors = {}
        
        # Duyệt qua các vị thế hiện có
        for existing_symbol, pos_info in self.active_positions.items():
            # Bỏ qua symbol trùng
            if existing_symbol == symbol:
                continue
                
            # Lấy tương quan giữa hai cặp
            correlation = self.correlation_data.get(symbol, {}).get(existing_symbol, 0)
            
            # Nếu tương quan đủ cao, tính phơi nhiễm
            if abs(correlation) >= self.correlation_threshold:
                existing_side = pos_info['side']
                existing_value = pos_info['value']
                
                # Điều chỉnh dấu tương quan nếu các vị thế theo hướng ngược nhau
                sign = 1 if (side == existing_side and correlation > 0) or (side != existing_side and correlation < 0) else -1
                
                # Tương quan dương, cùng hướng -> tăng phơi nhiễm
                # Tương quan dương, ngược hướng -> giảm phơi nhiễm
                # Tương quan âm, cùng hướng -> giảm phơi nhiễm
                # Tương quan âm, ngược hướng -> tăng phơi nhiễm
                
                # Tính hệ số tương quan hiệu quả
                effective_correlation = sign * abs(correlation)
                
                # Thêm vào phơi nhiễm hiệu quả
                # Giá trị âm nghĩa là giảm phơi nhiễm (đòn bẩy âm)
                exposure_contribution = existing_value * effective_correlation
                effective_exposure += exposure_contribution
                
                # Cộng dồn tổng phơi nhiễm (giá trị tuyệt đối)
                total_exposure += existing_value
                
                # Lưu thông tin
                correlated_positions.append({
                    'symbol': existing_symbol,
                    'side': existing_side,
                    'value': existing_value,
                    'correlation': correlation,
                    'effective_correlation': effective_correlation,
                    'exposure_contribution': exposure_contribution
                })
                
                correlation_factors[existing_symbol] = effective_correlation
        
        # Tính tỷ lệ phơi nhiễm
        max_allowed_exposure = total_exposure * self.max_correlation_exposure
        exposure_ratio = abs(effective_exposure) / max_allowed_exposure if max_allowed_exposure > 0 else 1.0
        
        # Kết quả
        result = {
            'total_exposure': total_exposure,
            'effective_exposure': effective_exposure,
            'max_allowed': max_allowed_exposure,
            'is_acceptable': exposure_ratio <= 1.0,
            'exposure_ratio': exposure_ratio,
            'correlated_positions': correlated_positions,
            'correlation_factors': correlation_factors
        }
        
        logger.info(f"Correlation exposure for {symbol} {side}: " +
                   f"Effective: ${effective_exposure:.2f}, Total: ${total_exposure:.2f}, " +
                   f"Ratio: {exposure_ratio:.2f}, Acceptable: {result['is_acceptable']}")
        
        return result
    
    def suggest_position_adjustments(self, max_exposure_ratio: float = 0.8) -> Dict:
        """
        Đề xuất điều chỉnh vị thế để giảm phơi nhiễm tương quan.
        
        Args:
            max_exposure_ratio (float): Tỷ lệ phơi nhiễm tối đa mong muốn
            
        Returns:
            Dict: Đề xuất điều chỉnh vị thế
        """
        if not self.active_positions or len(self.active_positions) < 2:
            return {
                'adjustments_needed': False,
                'current_exposure_ratio': 0,
                'target_exposure_ratio': max_exposure_ratio,
                'position_adjustments': {}
            }
        
        # Tính toán ma trận phơi nhiễm
        exposure_matrix = {}
        total_position_value = sum(pos['value'] for pos in self.active_positions.values())
        
        for symbol1, pos1 in self.active_positions.items():
            exposure_matrix[symbol1] = {}
            
            for symbol2, pos2 in self.active_positions.items():
                if symbol1 == symbol2:
                    continue
                    
                correlation = self.correlation_data.get(symbol1, {}).get(symbol2, 0)
                side1, side2 = pos1['side'], pos2['side']
                
                # Điều chỉnh dấu
                sign = 1 if (side1 == side2 and correlation > 0) or (side1 != side2 and correlation < 0) else -1
                effective_correlation = sign * abs(correlation)
                
                exposure_matrix[symbol1][symbol2] = {
                    'correlation': correlation,
                    'effective_correlation': effective_correlation,
                    'exposure': pos2['value'] * effective_correlation
                }
        
        # Tính tổng phơi nhiễm cho mỗi symbol
        total_exposures = {}
        for symbol, pos in self.active_positions.items():
            symbol_exposure = pos['value']  # Phơi nhiễm ban đầu là giá trị vị thế
            
            for other_symbol, corr_data in exposure_matrix.get(symbol, {}).items():
                symbol_exposure += corr_data['exposure']
                
            total_exposures[symbol] = symbol_exposure
        
        # Tính tổng phơi nhiễm hiệu quả
        effective_total_exposure = sum(abs(exp) for exp in total_exposures.values())
        current_exposure_ratio = effective_total_exposure / (total_position_value * self.max_correlation_exposure)
        
        # Nếu đã dưới ngưỡng, không cần điều chỉnh
        if current_exposure_ratio <= max_exposure_ratio:
            return {
                'adjustments_needed': False,
                'current_exposure_ratio': current_exposure_ratio,
                'target_exposure_ratio': max_exposure_ratio,
                'position_values': {s: p['value'] for s, p in self.active_positions.items()},
                'position_exposures': total_exposures
            }
        
        # Tìm các vị thế cần điều chỉnh
        adjustments = {}
        target_exposure = total_position_value * self.max_correlation_exposure * max_exposure_ratio
        
        # Mục tiêu là giảm effective_total_exposure xuống target_exposure
        reduction_needed = effective_total_exposure - target_exposure
        
        # Sắp xếp các vị thế theo mức độ đóng góp vào phơi nhiễm (giảm dần)
        exposure_contributions = []
        for symbol, exposure in total_exposures.items():
            exposure_contributions.append({
                'symbol': symbol,
                'exposure': abs(exposure),
                'sign': 1 if exposure >= 0 else -1
            })
            
        exposure_contributions.sort(key=lambda x: x['exposure'], reverse=True)
        
        # Bắt đầu từ vị thế có phơi nhiễm cao nhất, giảm dần
        remaining_reduction = reduction_needed
        for contribution in exposure_contributions:
            symbol = contribution['symbol']
            pos_info = self.active_positions[symbol]
            
            # Nếu còn cần giảm và vị thế này có đóng góp đáng kể
            if remaining_reduction > 0 and contribution['exposure'] > 0:
                # Tính phần trăm điều chỉnh cần thiết (tối đa là đóng toàn bộ)
                adjustment_pct = min(1.0, remaining_reduction / contribution['exposure'])
                
                # Điều chỉnh giá trị vị thế
                adjusted_value = pos_info['value'] * (1 - adjustment_pct)
                adjustment_amount = pos_info['value'] - adjusted_value
                
                # Cập nhật lượng cần giảm còn lại
                remaining_reduction -= contribution['exposure'] * adjustment_pct
                
                # Lưu đề xuất điều chỉnh
                adjustments[symbol] = {
                    'current_value': pos_info['value'],
                    'adjusted_value': adjusted_value,
                    'adjustment_amount': adjustment_amount,
                    'adjustment_percentage': adjustment_pct * 100,
                    'exposure_contribution': contribution['exposure']
                }
        
        return {
            'adjustments_needed': True,
            'current_exposure_ratio': current_exposure_ratio,
            'target_exposure_ratio': max_exposure_ratio,
            'total_reduction_needed': reduction_needed,
            'position_adjustments': adjustments,
            'position_values': {s: p['value'] for s, p in self.active_positions.items()},
            'position_exposures': total_exposures
        }


class DrawdownManager:
    """Quản lý và kiểm soát drawdown"""
    
    def __init__(self, initial_balance: float, max_drawdown_pct: float = 20.0,
                recovery_factor: float = 0.5, scaling_levels: List[Dict] = None):
        """
        Khởi tạo Drawdown Manager.
        
        Args:
            initial_balance (float): Số dư ban đầu
            max_drawdown_pct (float): % drawdown tối đa được phép
            recovery_factor (float): Hệ số phục hồi (càng nhỏ càng dè dặt)
            scaling_levels (List[Dict], optional): Các mức điều chỉnh kích thước
                [{'drawdown': 5, 'scale': 0.9}, {'drawdown': 10, 'scale': 0.7}, ...]
        """
        self.initial_balance = initial_balance
        self.max_drawdown_pct = max_drawdown_pct
        self.recovery_factor = recovery_factor
        
        # Mặc định các mức điều chỉnh
        self.scaling_levels = scaling_levels or [
            {'drawdown': 5, 'scale': 0.9},
            {'drawdown': 10, 'scale': 0.7},
            {'drawdown': 15, 'scale': 0.5},
            {'drawdown': 20, 'scale': 0.25},
            {'drawdown': 25, 'scale': 0}  # Dừng giao dịch khi drawdown > 25%
        ]
        
        # Dữ liệu theo dõi
        self.peak_balance = initial_balance
        self.current_balance = initial_balance
        self.current_drawdown_pct = 0.0
        self.drawdown_history = []
        self.recovery_mode = False
        self.recovery_target = initial_balance
        self.recovery_plan = {}
    
    def update_balance(self, new_balance: float) -> Dict:
        """
        Cập nhật số dư và tính toán drawdown.
        
        Args:
            new_balance (float): Số dư mới
            
        Returns:
            Dict: Thông tin về drawdown hiện tại
        """
        old_balance = self.current_balance
        self.current_balance = new_balance
        
        # Cập nhật peak balance
        if new_balance > self.peak_balance:
            self.peak_balance = new_balance
        
        # Tính drawdown
        if self.peak_balance > 0:
            self.current_drawdown_pct = (self.peak_balance - new_balance) / self.peak_balance * 100
        else:
            self.current_drawdown_pct = 0
        
        # Lưu lịch sử
        self.drawdown_history.append({
            'timestamp': datetime.now(),
            'balance': new_balance,
            'peak_balance': self.peak_balance,
            'drawdown_pct': self.current_drawdown_pct,
            'change': new_balance - old_balance
        })
        
        # Kiểm tra và cập nhật chế độ phục hồi
        self._check_recovery_mode()
        
        logger.info(f"Balance updated: ${new_balance:.2f}, Peak: ${self.peak_balance:.2f}, " +
                   f"Drawdown: {self.current_drawdown_pct:.2f}%, Recovery mode: {self.recovery_mode}")
        
        return {
            'current_balance': new_balance,
            'peak_balance': self.peak_balance,
            'drawdown_pct': self.current_drawdown_pct,
            'recovery_mode': self.recovery_mode,
            'scaling_factor': self.get_position_scaling()
        }
    
    def get_position_scaling(self) -> float:
        """
        Lấy hệ số điều chỉnh kích thước vị thế dựa trên drawdown hiện tại.
        
        Returns:
            float: Hệ số điều chỉnh (0-1)
        """
        # Sắp xếp các mức theo thứ tự drawdown giảm dần
        sorted_levels = sorted(self.scaling_levels, key=lambda x: x['drawdown'], reverse=True)
        
        # Tìm mức phù hợp
        for level in sorted_levels:
            if self.current_drawdown_pct >= level['drawdown']:
                return level['scale']
        
        # Mặc định nếu không có mức nào phù hợp
        return 1.0
    
    def calculate_recovery_plan(self) -> Dict:
        """
        Tính toán kế hoạch phục hồi từ drawdown.
        
        Returns:
            Dict: Kế hoạch phục hồi
        """
        if not self.recovery_mode:
            return {
                'recovery_needed': False,
                'message': "No recovery needed"
            }
        
        # Tính số lượng giao dịch thắng cần thiết để phục hồi
        deficit = self.peak_balance - self.current_balance
        
        # Giả định: mỗi giao dịch thắng mang lại lợi nhuận 1% số dư hiện tại
        win_profit_pct = 1.0
        win_profit = self.current_balance * (win_profit_pct / 100)
        
        # Tính số giao dịch cần thiết
        trades_needed = np.ceil(deficit / win_profit)
        
        # Tính thời gian phục hồi dự kiến
        # Giả định: trung bình 5 giao dịch mỗi tuần, tỷ lệ thắng 60%
        win_rate = 0.6
        trades_per_week = 5
        wins_per_week = trades_per_week * win_rate
        weeks_to_recover = trades_needed / wins_per_week
        
        # Tạo kế hoạch phục hồi
        recovery_plan = {
            'recovery_needed': True,
            'current_balance': self.current_balance,
            'peak_balance': self.peak_balance,
            'deficit': deficit,
            'deficit_percentage': self.current_drawdown_pct,
            'win_profit_pct': win_profit_pct,
            'win_profit': win_profit,
            'trades_needed': trades_needed,
            'estimated_weeks': weeks_to_recover,
            'position_sizing': {
                'current_scaling': self.get_position_scaling(),
                'suggested_strategy': "Kelly Criterion với half-Kelly",
                'max_risk_per_trade': min(1.0, 2.0 * self.get_position_scaling())  # % tài khoản
            },
            'psychological_tips': [
                "Tập trung vào việc thực hiện đúng quy trình, không phải kết quả ngắn hạn",
                "Không cố gắng phục hồi nhanh bằng cách tăng kích thước vị thế",
                "Theo sát kế hoạch giao dịch và chiến lược quản lý vốn",
                "Theo dõi và ghi chú lại mỗi giao dịch để học hỏi và cải thiện"
            ]
        }
        
        # Lưu kế hoạch
        self.recovery_plan = recovery_plan
        
        logger.info(f"Recovery plan calculated: Deficit: ${deficit:.2f}, " +
                   f"Trades needed: {trades_needed:.0f}, Weeks: {weeks_to_recover:.1f}")
        
        return recovery_plan
    
    def should_take_trade(self, expected_win_rate: float, risk_reward_ratio: float) -> Dict:
        """
        Quyết định có nên thực hiện giao dịch dựa trên drawdown và kỳ vọng.
        
        Args:
            expected_win_rate (float): Tỷ lệ thắng kỳ vọng (0-1)
            risk_reward_ratio (float): Tỷ lệ reward/risk
            
        Returns:
            Dict: Quyết định và lý do
        """
        # Tính toán kỳ vọng (Expectancy)
        expectancy = (expected_win_rate * risk_reward_ratio) - (1 - expected_win_rate)
        
        # Lấy hệ số điều chỉnh
        scaling = self.get_position_scaling()
        
        # Nếu hệ số scaling là 0, không giao dịch
        if scaling == 0:
            return {
                'should_trade': False,
                'reason': f"Trading halted due to high drawdown ({self.current_drawdown_pct:.1f}% > threshold)",
                'expectancy': expectancy,
                'scaling': scaling
            }
        
        # Nếu đang ở chế độ phục hồi, yêu cầu kỳ vọng cao hơn
        min_expectancy = 0.2 if not self.recovery_mode else 0.3
        
        if expectancy < min_expectancy:
            return {
                'should_trade': False,
                'reason': f"Expectancy too low ({expectancy:.2f} < {min_expectancy})",
                'expectancy': expectancy,
                'scaling': scaling
            }
        
        # Nếu tất cả điều kiện đều tốt
        return {
            'should_trade': True,
            'reason': f"Trade acceptable, expectancy: {expectancy:.2f}",
            'expectancy': expectancy,
            'scaling': scaling,
            'position_scale_factor': scaling,
            'risk_adjustment': "normal" if not self.recovery_mode else "recovery"
        }
    
    def _check_recovery_mode(self) -> None:
        """Kiểm tra và cập nhật chế độ phục hồi"""
        # Ngưỡng để vào chế độ phục hồi
        recovery_threshold = 0.5 * self.max_drawdown_pct
        
        # Kiểm tra xem có nên vào chế độ phục hồi không
        if not self.recovery_mode and self.current_drawdown_pct >= recovery_threshold:
            self.recovery_mode = True
            self.recovery_target = self.peak_balance
            logger.warning(f"Entering recovery mode: Drawdown {self.current_drawdown_pct:.2f}% > {recovery_threshold:.2f}%")
        
        # Kiểm tra xem đã phục hồi chưa
        elif self.recovery_mode and self.current_balance >= self.recovery_target * self.recovery_factor:
            # Thoát chế độ phục hồi nếu đã phục hồi đủ lượng (recovery_factor = 1 nghĩa là phục hồi hoàn toàn)
            self.recovery_mode = False
            logger.info(f"Exiting recovery mode: Balance ${self.current_balance:.2f} >= " +
                      f"${self.recovery_target * self.recovery_factor:.2f}")


class StressTestManager:
    """Thực hiện các kịch bản kiểm tra sức chịu đựng (stress test)"""
    
    def __init__(self, risk_manager: RiskManager = None):
        """
        Khởi tạo Stress Test Manager.
        
        Args:
            risk_manager (RiskManager, optional): Đối tượng risk manager để kiểm tra
        """
        self.risk_manager = risk_manager
        
        # Các kịch bản stress test mặc định
        self.default_scenarios = [
            {
                'name': "Market Crash",
                'description': "Mô phỏng sự kiện thị trường giảm đột ngột 20%",
                'price_movements': [
                    {'percentage': -20, 'duration_minutes': 60, 'affected_symbols': 'all'}
                ],
                'liquidation_risks': True
            },
            {
                'name': "Volatility Surge",
                'description': "Mô phỏng sự kiện tăng đột biến biến động thị trường",
                'price_movements': [
                    {'percentage': 10, 'duration_minutes': 30, 'affected_symbols': 'all'},
                    {'percentage': -15, 'duration_minutes': 45, 'affected_symbols': 'all'},
                    {'percentage': 8, 'duration_minutes': 30, 'affected_symbols': 'all'}
                ],
                'liquidation_risks': True
            },
            {
                'name': "Correlated Downturn",
                'description': "Mô phỏng đợt sụt giảm đồng thời của các tài sản có tương quan",
                'price_movements': [
                    {'percentage': -12, 'duration_minutes': 120, 'affected_symbols': 'correlated'}
                ],
                'liquidation_risks': True
            },
            {
                'name': "Extended Drawdown",
                'description': "Mô phỏng giai đoạn suy giảm kéo dài",
                'price_movements': [
                    {'percentage': -5, 'duration_minutes': 60, 'affected_symbols': 'all'},
                    {'percentage': -2, 'duration_minutes': 120, 'affected_symbols': 'all'},
                    {'percentage': -3, 'duration_minutes': 180, 'affected_symbols': 'all'},
                    {'percentage': -3, 'duration_minutes': 240, 'affected_symbols': 'all'}
                ],
                'liquidation_risks': True
            },
            {
                'name': "Liquidity Crisis",
                'description': "Mô phỏng sự kiện thiếu thanh khoản và giá spread rộng",
                'price_movements': [
                    {'percentage': -8, 'duration_minutes': 30, 'affected_symbols': 'all'},
                    {'percentage': 4, 'duration_minutes': 15, 'affected_symbols': 'all'},
                    {'percentage': -10, 'duration_minutes': 45, 'affected_symbols': 'all'}
                ],
                'liquidity_reduction': 0.8,
                'spread_increase': 5,
                'liquidation_risks': True
            }
        ]
    
    def run_stress_test(self, positions: Dict[str, Dict], scenario: Dict = None,
                      correlation_matrix: Dict[str, Dict] = None) -> Dict:
        """
        Chạy kiểm tra sức chịu đựng trên các vị thế hiện tại.
        
        Args:
            positions (Dict[str, Dict]): Các vị thế hiện tại
                {symbol: {'side': str, 'quantity': float, 'entry_price': float, 'stop_loss': float}}
            scenario (Dict, optional): Kịch bản kiểm tra
            correlation_matrix (Dict[str, Dict], optional): Ma trận tương quan
            
        Returns:
            Dict: Kết quả kiểm tra
        """
        # Sử dụng kịch bản mặc định nếu không cung cấp
        if scenario is None:
            # Chọn ngẫu nhiên một kịch bản từ danh sách mặc định
            scenario = self.default_scenarios[np.random.randint(0, len(self.default_scenarios))]
        
        logger.info(f"Running stress test: {scenario['name']} - {scenario['description']}")
        
        # Tính toán giá trị ban đầu của danh mục
        initial_portfolio_value = self._calculate_portfolio_value(positions)
        
        # Mô phỏng các biến động giá
        stress_results = self._simulate_price_movements(
            positions, 
            scenario['price_movements'],
            correlation_matrix
        )
        
        # Tính toán giá trị cuối cùng của danh mục
        final_portfolio_value = stress_results['final_portfolio_value']
        
        # Tính drawdown
        drawdown_amount = initial_portfolio_value - final_portfolio_value
        drawdown_percentage = (drawdown_amount / initial_portfolio_value) * 100 if initial_portfolio_value > 0 else 0
        
        # Kiểm tra các vị thế bị dừng lỗ
        stopped_positions = stress_results['stopped_positions']
        
        # Tạo báo cáo
        report = {
            'scenario_name': scenario['name'],
            'scenario_description': scenario['description'],
            'initial_portfolio_value': initial_portfolio_value,
            'final_portfolio_value': final_portfolio_value,
            'drawdown_amount': drawdown_amount,
            'drawdown_percentage': drawdown_percentage,
            'stopped_positions': stopped_positions,
            'liquidated_positions': stress_results['liquidated_positions'],
            'price_movements': stress_results['price_movements'],
            'risk_metrics': {
                'var_95': stress_results['var_95'],
                'cvar_95': stress_results['cvar_95'],
                'max_drawdown': stress_results['max_drawdown'],
                'recovery_time_estimate': stress_results['recovery_time_estimate']
            },
            'recommendations': self._generate_recommendations(stress_results)
        }
        
        logger.info(f"Stress test completed: Drawdown ${drawdown_amount:.2f} ({drawdown_percentage:.2f}%), " +
                   f"Stopped positions: {len(stopped_positions)}/{len(positions)}")
        
        return report
    
    def _calculate_portfolio_value(self, positions: Dict[str, Dict]) -> float:
        """
        Tính toán giá trị danh mục dựa trên các vị thế.
        
        Args:
            positions (Dict[str, Dict]): Các vị thế
            
        Returns:
            float: Giá trị danh mục
        """
        total_value = 0
        
        for symbol, position in positions.items():
            entry_price = position['entry_price']
            quantity = position['quantity']
            position_value = entry_price * quantity
            total_value += position_value
            
        return total_value
    
    def _simulate_price_movements(self, positions: Dict[str, Dict], 
                              price_movements: List[Dict],
                              correlation_matrix: Dict[str, Dict] = None) -> Dict:
        """
        Mô phỏng biến động giá theo kịch bản.
        
        Args:
            positions (Dict[str, Dict]): Các vị thế
            price_movements (List[Dict]): Các biến động giá
            correlation_matrix (Dict[str, Dict], optional): Ma trận tương quan
            
        Returns:
            Dict: Kết quả mô phỏng
        """
        # Sao chép vị thế để không ảnh hưởng đến dữ liệu gốc
        current_positions = {s: p.copy() for s, p in positions.items()}
        
        # Mảng theo dõi giá trị danh mục
        portfolio_values = []
        current_value = self._calculate_portfolio_value(current_positions)
        portfolio_values.append(current_value)
        
        # Theo dõi các vị thế bị dừng lỗ hoặc thanh lý
        stopped_positions = {}
        liquidated_positions = {}
        
        # Lưu vết biến động giá
        price_movement_data = []
        
        # Mô phỏng từng biến động giá
        for movement in price_movements:
            percentage = movement['percentage']
            affected_symbols = movement['affected_symbols']
            
            # Xác định các symbol bị ảnh hưởng
            symbols_to_adjust = []
            if affected_symbols == 'all':
                symbols_to_adjust = list(current_positions.keys())
            elif affected_symbols == 'correlated' and correlation_matrix:
                # Chọn các symbol có tương quan cao với nhau
                # Logic này có thể cần phức tạp hơn trong triển khai thực tế
                symbols_to_adjust = list(current_positions.keys())
            else:
                # Giả sử affected_symbols là danh sách các symbol
                symbols_to_adjust = [s for s in affected_symbols if s in current_positions]
            
            # Điều chỉnh giá cho từng symbol
            for symbol in symbols_to_adjust:
                if symbol in stopped_positions or symbol in liquidated_positions:
                    continue  # Bỏ qua các vị thế đã bị dừng lỗ hoặc thanh lý
                
                position = current_positions[symbol]
                side = position['side']
                current_price = position.get('current_price', position['entry_price'])
                stop_loss = position.get('stop_loss', 0)
                
                # Tính giá mới
                new_price = current_price * (1 + percentage / 100)
                price_change_pct = (new_price - current_price) / current_price * 100
                
                # Lưu vết biến động
                price_movement_data.append({
                    'symbol': symbol,
                    'from_price': current_price,
                    'to_price': new_price,
                    'change_pct': price_change_pct,
                    'position_side': side
                })
                
                # Kiểm tra stop loss
                if stop_loss > 0:
                    if (side.upper() == 'LONG' and new_price <= stop_loss) or \
                       (side.upper() == 'SHORT' and new_price >= stop_loss):
                        # Vị thế bị dừng lỗ
                        stopped_positions[symbol] = {
                            'position': position,
                            'stop_price': stop_loss,
                            'market_price': new_price,
                            'pnl': self._calculate_pnl(position, stop_loss)
                        }
                        continue
                
                # Tính P&L tạm thời
                unrealized_pnl = self._calculate_pnl(position, new_price)
                
                # Cập nhật giá hiện tại
                position['current_price'] = new_price
                position['unrealized_pnl'] = unrealized_pnl
                
                # Kiểm tra thanh lý (tùy thuộc vào loại tài khoản)
                # Giả sử ngưỡng thanh lý là -80% giá trị vị thế
                if unrealized_pnl < -0.8 * position['entry_price'] * position['quantity']:
                    liquidated_positions[symbol] = {
                        'position': position,
                        'liquidation_price': new_price,
                        'pnl': unrealized_pnl
                    }
            
            # Tính giá trị danh mục sau biến động
            current_value = self._calculate_adjusted_portfolio_value(
                current_positions, stopped_positions, liquidated_positions
            )
            portfolio_values.append(current_value)
        
        # Tính các chỉ số rủi ro
        returns = np.diff(portfolio_values) / portfolio_values[:-1]
        var_95 = np.percentile(returns, 5) * current_value  # Value at Risk 95%
        cvar_95 = returns[returns <= np.percentile(returns, 5)].mean() * current_value  # Conditional VaR
        max_drawdown = (max(portfolio_values) - min(portfolio_values)) / max(portfolio_values) * 100
        
        # Ước tính thời gian phục hồi
        recovery_estimate = self._estimate_recovery_time(
            portfolio_values[0], portfolio_values[-1], returns
        )
        
        return {
            'final_portfolio_value': portfolio_values[-1],
            'portfolio_value_timeseries': portfolio_values,
            'stopped_positions': stopped_positions,
            'liquidated_positions': liquidated_positions,
            'price_movements': price_movement_data,
            'var_95': var_95,
            'cvar_95': cvar_95,
            'max_drawdown': max_drawdown,
            'recovery_time_estimate': recovery_estimate
        }
    
    def _calculate_pnl(self, position: Dict, current_price: float) -> float:
        """
        Tính lợi nhuận/lỗ (P&L) cho một vị thế.
        
        Args:
            position (Dict): Thông tin vị thế
            current_price (float): Giá hiện tại
            
        Returns:
            float: Giá trị P&L
        """
        entry_price = position['entry_price']
        quantity = position['quantity']
        side = position['side']
        
        if side.upper() == 'LONG':
            return (current_price - entry_price) * quantity
        else:  # SHORT
            return (entry_price - current_price) * quantity
    
    def _calculate_adjusted_portfolio_value(self, positions: Dict[str, Dict],
                                        stopped_positions: Dict[str, Dict],
                                        liquidated_positions: Dict[str, Dict]) -> float:
        """
        Tính giá trị danh mục điều chỉnh sau khi xem xét các vị thế bị dừng lỗ và thanh lý.
        
        Args:
            positions (Dict[str, Dict]): Các vị thế hiện tại
            stopped_positions (Dict[str, Dict]): Các vị thế bị dừng lỗ
            liquidated_positions (Dict[str, Dict]): Các vị thế bị thanh lý
            
        Returns:
            float: Giá trị danh mục điều chỉnh
        """
        total_value = 0
        
        # Tính giá trị các vị thế còn lại
        for symbol, position in positions.items():
            if symbol in stopped_positions or symbol in liquidated_positions:
                continue
                
            current_price = position.get('current_price', position['entry_price'])
            quantity = position['quantity']
            position_value = current_price * quantity
            total_value += position_value
        
        # Cộng thêm P&L từ các vị thế bị dừng lỗ
        for symbol, stopped in stopped_positions.items():
            total_value += stopped['pnl']
        
        # Cộng thêm P&L từ các vị thế bị thanh lý
        for symbol, liquidated in liquidated_positions.items():
            total_value += liquidated['pnl']
            
        return total_value
    
    def _estimate_recovery_time(self, initial_value: float, final_value: float, 
                             returns: np.ndarray) -> Dict:
        """
        Ước tính thời gian cần thiết để phục hồi từ drawdown.
        
        Args:
            initial_value (float): Giá trị ban đầu
            final_value (float): Giá trị cuối cùng
            returns (np.ndarray): Mảng các giá trị lợi nhuận
            
        Returns:
            Dict: Thông tin ước tính thời gian phục hồi
        """
        if final_value >= initial_value:
            return {'days': 0, 'weeks': 0, 'months': 0, 'description': "No recovery needed"}
        
        # Tính lợi nhuận trung bình (chỉ từ các ngày dương)
        positive_returns = returns[returns > 0]
        if len(positive_returns) == 0:
            avg_daily_return = 0.005  # Mặc định 0.5% mỗi ngày
        else:
            avg_daily_return = positive_returns.mean()
        
        # Tính drawdown
        drawdown = (initial_value - final_value) / initial_value
        
        # Công thức ước tính: log(1/(1-drawdown)) / log(1+avg_daily_return)
        if avg_daily_return <= 0:
            recovery_days = float('inf')
        else:
            recovery_days = np.log(1 / (1 - drawdown)) / np.log(1 + avg_daily_return)
        
        recovery_weeks = recovery_days / 5  # Giả sử 5 ngày giao dịch mỗi tuần
        recovery_months = recovery_weeks / 4.33  # Ước tính
        
        return {
            'days': int(recovery_days),
            'weeks': round(recovery_weeks, 1),
            'months': round(recovery_months, 1),
            'description': self._format_recovery_time(recovery_days)
        }
    
    def _format_recovery_time(self, days: float) -> str:
        """
        Định dạng thời gian phục hồi thành chuỗi dễ đọc.
        
        Args:
            days (float): Số ngày để phục hồi
            
        Returns:
            str: Chuỗi mô tả thời gian
        """
        if days == float('inf'):
            return "Cannot recover with current strategy"
            
        if days <= 5:
            return f"Quick recovery: {int(days)} trading days"
        elif days <= 20:
            return f"Short term: {round(days/5, 1)} weeks ({int(days)} days)"
        elif days <= 60:
            return f"Medium term: {round(days/20, 1)} months ({int(days)} days)"
        else:
            return f"Long term: {round(days/252, 1)} years ({int(days)} days)"
    
    def _generate_recommendations(self, stress_results: Dict) -> List[str]:
        """
        Tạo các khuyến nghị dựa trên kết quả stress test.
        
        Args:
            stress_results (Dict): Kết quả stress test
            
        Returns:
            List[str]: Danh sách các khuyến nghị
        """
        recommendations = []
        
        # Phân tích mức độ nghiêm trọng
        drawdown = stress_results['max_drawdown']
        stopped = len(stress_results['stopped_positions'])
        liquidated = len(stress_results['liquidated_positions'])
        
        # Về drawdown
        if drawdown > 30:
            recommendations.append("NGHIÊM TRỌNG: Drawdown vượt quá 30% trong kịch bản này. Cần giảm đáng kể kích thước vị thế và xem xét lại chiến lược.")
        elif drawdown > 20:
            recommendations.append("CẢNH BÁO: Drawdown vượt quá 20%. Nên giảm kích thước vị thế và tăng cường quản lý rủi ro.")
        elif drawdown > 10:
            recommendations.append("CHÚ Ý: Drawdown vượt quá 10%. Hãy xem xét điều chỉnh các tham số stop loss để bảo vệ tài khoản tốt hơn.")
        
        # Về vị thế bị dừng lỗ
        if stopped > 0:
            recommendations.append(f"{stopped} vị thế đã kích hoạt stop loss trong kịch bản này. Xem xét đa dạng hóa danh mục đầu tư hơn nữa.")
        
        # Về vị thế bị thanh lý
        if liquidated > 0:
            recommendations.append(f"CẢNH BÁO: {liquidated} vị thế đã bị thanh lý do margin call. Đòn bẩy hiện tại có thể quá cao!")
        
        # Về thời gian phục hồi
        recovery = stress_results['recovery_time_estimate']
        if recovery['days'] > 120:
            recommendations.append(f"Thời gian phục hồi ước tính: {recovery['description']}. Quá dài, cần xem xét lại chiến lược giao dịch.")
        elif recovery['days'] > 60:
            recommendations.append(f"Thời gian phục hồi ước tính: {recovery['description']}. Hãy xem xét tăng cường quản lý rủi ro.")
        else:
            recommendations.append(f"Thời gian phục hồi ước tính: {recovery['description']}.")
        
        # Các khuyến nghị chung
        recommendations.append("Sử dụng Kelly Criterion với half-Kelly để xác định kích thước vị thế tối ưu.")
        recommendations.append("Cân nhắc tăng cường đa dạng hóa danh mục qua việc thêm các tài sản có tương quan âm.")
        recommendations.append("Tính toán và theo dõi biến động thị trường để điều chỉnh động các mức stop loss.")
        
        return recommendations


def create_risk_manager(manager_type: str, **kwargs) -> Union[RiskManager, 
                                                          CorrelationRiskManager, 
                                                          DrawdownManager, 
                                                          StressTestManager]:
    """
    Tạo risk manager theo loại.
    
    Args:
        manager_type (str): Loại manager ('risk', 'correlation', 'drawdown', 'stress')
        **kwargs: Các tham số bổ sung
        
    Returns:
        Union[RiskManager, CorrelationRiskManager, DrawdownManager, StressTestManager]:
            Đối tượng risk manager
    """
    if manager_type.lower() == 'correlation':
        return CorrelationRiskManager(**kwargs)
    elif manager_type.lower() == 'drawdown':
        return DrawdownManager(**kwargs)
    elif manager_type.lower() == 'stress':
        return StressTestManager(**kwargs)
    else:  # 'risk' hoặc mặc định
        return RiskManager(**kwargs)


def main():
    """Hàm chính để test module"""
    # Test RiskManager
    print("\n=== Testing RiskManager ===")
    risk_manager = RiskManager(
        account_balance=10000.0,
        max_risk_per_trade=2.0,
        max_daily_risk=5.0,
        max_weekly_risk=10.0,
        max_drawdown_allowed=20.0
    )
    
    # Kiểm tra rủi ro một giao dịch
    check_result = risk_manager.check_trade_risk(
        symbol="BTCUSDT",
        risk_amount=300.0,  # $300 rủi ro
        entry_price=40000.0,
        stop_loss_price=39000.0
    )
    print(f"Trade risk check: {check_result['allowed']}, Reason: {check_result['reason']}")
    
    # Đăng ký giao dịch
    risk_manager.register_trade({
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry_price': 40000.0,
        'stop_loss_price': 39000.0,
        'take_profit_price': 42000.0,
        'quantity': 0.1,
        'risk_amount': 100.0,
        'risk_percentage': 1.0,
        'timestamp': datetime.now()
    })
    
    # Cập nhật số dư
    risk_manager.update_account_balance(9900.0)  # Giảm $100
    
    # Test CorrelationRiskManager
    print("\n=== Testing CorrelationRiskManager ===")
    correlation_manager = CorrelationRiskManager(
        max_correlation_exposure=2.0,
        correlation_threshold=0.7
    )
    
    # Ma trận tương quan
    correlation_data = {
        'BTCUSDT': {'BTCUSDT': 1.0, 'ETHUSDT': 0.8, 'SOLUSDT': 0.6},
        'ETHUSDT': {'BTCUSDT': 0.8, 'ETHUSDT': 1.0, 'SOLUSDT': 0.7},
        'SOLUSDT': {'BTCUSDT': 0.6, 'ETHUSDT': 0.7, 'SOLUSDT': 1.0}
    }
    correlation_manager.update_correlation_data(correlation_data)
    
    # Cập nhật vị thế
    correlation_manager.update_position(
        symbol='BTCUSDT',
        side='LONG',
        position_size=0.1,
        position_value=4000.0
    )
    
    # Kiểm tra phơi nhiễm tương quan
    exposure = correlation_manager.calculate_correlation_exposure(
        symbol='ETHUSDT',
        side='LONG',
        position_value=3000.0
    )
    print(f"Correlation exposure: {exposure['exposure_ratio']:.2f}, Acceptable: {exposure['is_acceptable']}")
    
    # Test DrawdownManager
    print("\n=== Testing DrawdownManager ===")
    drawdown_manager = DrawdownManager(
        initial_balance=10000.0,
        max_drawdown_pct=20.0
    )
    
    # Cập nhật số dư
    drawdown_result = drawdown_manager.update_balance(9500.0)  # -5% drawdown
    print(f"Drawdown: {drawdown_result['drawdown_pct']:.2f}%, Scaling: {drawdown_result['scaling']}")
    
    # Kiểm tra có nên giao dịch
    trade_decision = drawdown_manager.should_take_trade(
        expected_win_rate=0.6,
        risk_reward_ratio=2.0
    )
    print(f"Should trade: {trade_decision['should_trade']}, Reason: {trade_decision['reason']}")
    
    # Test StressTestManager
    print("\n=== Testing StressTestManager ===")
    stress_manager = StressTestManager()
    
    # Mô phỏng các vị thế
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
        }
    }
    
    # Chạy stress test
    stress_report = stress_manager.run_stress_test(
        positions=positions,
        correlation_matrix=correlation_data
    )
    
    print(f"Stress test: {stress_report['scenario_name']}")
    print(f"Drawdown: ${stress_report['drawdown_amount']:.2f} ({stress_report['drawdown_percentage']:.2f}%)")
    print(f"Recovery time: {stress_report['risk_metrics']['recovery_time_estimate']['description']}")
    print("\nRecommendations:")
    for rec in stress_report['recommendations']:
        print(f"- {rec}")
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    main()