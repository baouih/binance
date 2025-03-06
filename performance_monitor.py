#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module theo dõi hiệu suất (Performance Monitor)

Module này cung cấp các công cụ để theo dõi và phân tích hiệu suất giao dịch,
bao gồm theo dõi hiệu suất theo chiến lược, cặp giao dịch, và chế độ thị trường,
cũng như tính toán các chỉ số như Sharpe Ratio, Profit Factor, Win Rate.
"""

import os
import sys
import json
import time
import math
import logging
import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional, Union, Any
from pathlib import Path

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('performance_monitor.log')
    ]
)
logger = logging.getLogger('performance_monitor')

# Thêm thư mục gốc vào sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import calculate_pnl_with_full_details nếu có
try:
    from calculate_pnl_with_full_details import PnLCalculator
    pnl_calculator_available = True
except ImportError:
    logger.warning("Không thể import module calculate_pnl_with_full_details")
    pnl_calculator_available = False


class PerformanceMetrics:
    """Lớp tính toán chỉ số hiệu suất"""
    
    @staticmethod
    def calculate_win_rate(trades: List[Dict]) -> float:
        """
        Tính tỷ lệ thắng
        
        Args:
            trades (List[Dict]): Danh sách giao dịch
            
        Returns:
            float: Tỷ lệ thắng (0-1)
        """
        if not trades:
            return 0.0
        
        winning_trades = [t for t in trades if t.get('net_pnl', 0) > 0]
        return len(winning_trades) / len(trades)
    
    @staticmethod
    def calculate_profit_factor(trades: List[Dict]) -> float:
        """
        Tính profit factor (tổng lãi / tổng lỗ)
        
        Args:
            trades (List[Dict]): Danh sách giao dịch
            
        Returns:
            float: Profit factor
        """
        total_profit = sum(t.get('net_pnl', 0) for t in trades if t.get('net_pnl', 0) > 0)
        total_loss = sum(abs(t.get('net_pnl', 0)) for t in trades if t.get('net_pnl', 0) < 0)
        
        if total_loss == 0:
            return float('inf') if total_profit > 0 else 0.0
        
        return total_profit / total_loss
    
    @staticmethod
    def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
        """
        Tính Sharpe ratio
        
        Args:
            returns (List[float]): Danh sách lợi nhuận theo kỳ (%)
            risk_free_rate (float): Lãi suất phi rủi ro
            
        Returns:
            float: Sharpe ratio
        """
        if not returns:
            return 0.0
        
        returns_array = np.array(returns)
        excess_returns = returns_array - risk_free_rate
        
        if len(returns) <= 1:
            return 0.0
        
        return (np.mean(excess_returns) / np.std(excess_returns, ddof=1)) * np.sqrt(252)  # Annualized
    
    @staticmethod
    def calculate_sortino_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
        """
        Tính Sortino ratio
        
        Args:
            returns (List[float]): Danh sách lợi nhuận theo kỳ (%)
            risk_free_rate (float): Lãi suất phi rủi ro
            
        Returns:
            float: Sortino ratio
        """
        if not returns:
            return 0.0
        
        returns_array = np.array(returns)
        excess_returns = returns_array - risk_free_rate
        
        # Chỉ tính downside deviation (chỉ lấy các giá trị âm)
        negative_returns = excess_returns[excess_returns < 0]
        
        if len(negative_returns) == 0:
            return float('inf') if np.mean(excess_returns) > 0 else 0.0
        
        downside_deviation = np.std(negative_returns, ddof=1)
        if downside_deviation == 0:
            return 0.0
        
        return (np.mean(excess_returns) / downside_deviation) * np.sqrt(252)  # Annualized
    
    @staticmethod
    def calculate_max_drawdown(equity_curve: List[float]) -> Tuple[float, int, int]:
        """
        Tính drawdown tối đa
        
        Args:
            equity_curve (List[float]): Đường cong vốn
            
        Returns:
            Tuple[float, int, int]: (drawdown tối đa (%), chỉ số bắt đầu, chỉ số kết thúc)
        """
        if not equity_curve:
            return 0.0, 0, 0
        
        equity_array = np.array(equity_curve)
        max_dd = 0.0
        max_dd_start = 0
        max_dd_end = 0
        
        highest = equity_array[0]
        highest_idx = 0
        
        for i in range(1, len(equity_array)):
            if equity_array[i] > highest:
                highest = equity_array[i]
                highest_idx = i
            else:
                drawdown = (highest - equity_array[i]) / highest * 100
                if drawdown > max_dd:
                    max_dd = drawdown
                    max_dd_start = highest_idx
                    max_dd_end = i
        
        return max_dd, max_dd_start, max_dd_end
    
    @staticmethod
    def calculate_average_profit_loss(trades: List[Dict]) -> Tuple[float, float]:
        """
        Tính lợi nhuận/lỗ trung bình
        
        Args:
            trades (List[Dict]): Danh sách giao dịch
            
        Returns:
            Tuple[float, float]: (lợi nhuận trung bình, lỗ trung bình)
        """
        profit_trades = [t.get('net_pnl', 0) for t in trades if t.get('net_pnl', 0) > 0]
        loss_trades = [t.get('net_pnl', 0) for t in trades if t.get('net_pnl', 0) < 0]
        
        avg_profit = np.mean(profit_trades) if profit_trades else 0.0
        avg_loss = np.mean(loss_trades) if loss_trades else 0.0
        
        return avg_profit, avg_loss
    
    @staticmethod
    def calculate_expectancy(trades: List[Dict]) -> float:
        """
        Tính kỳ vọng lợi nhuận trên mỗi giao dịch
        
        Args:
            trades (List[Dict]): Danh sách giao dịch
            
        Returns:
            float: Kỳ vọng lợi nhuận
        """
        if not trades:
            return 0.0
        
        win_rate = PerformanceMetrics.calculate_win_rate(trades)
        avg_profit, avg_loss = PerformanceMetrics.calculate_average_profit_loss(trades)
        
        # Tính R-multiple (Lợi nhuận trung bình / Lỗ trung bình)
        r_multiple = abs(avg_profit / avg_loss) if avg_loss != 0 else 0.0
        
        # Expectancy = (Win Rate * R) - (Loss Rate * 1)
        expectancy = (win_rate * r_multiple) - ((1 - win_rate) * 1)
        
        return expectancy


class PerformanceMonitor:
    """Lớp theo dõi và phân tích hiệu suất giao dịch"""
    
    def __init__(self, data_dir: str = 'performance_data', reports_dir: str = 'reports'):
        """
        Khởi tạo Performance Monitor
        
        Args:
            data_dir (str): Thư mục lưu dữ liệu
            reports_dir (str): Thư mục lưu báo cáo
        """
        self.data_dir = data_dir
        self.reports_dir = reports_dir
        self.trades = []
        self.equity_curve = []
        self.daily_returns = []
        self.strategy_performance = {}
        self.symbol_performance = {}
        self.regime_performance = {}
        
        # Tạo thư mục lưu dữ liệu nếu chưa có
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(reports_dir, exist_ok=True)
        
        # Khởi tạo PnLCalculator nếu có
        self.pnl_calculator = PnLCalculator() if pnl_calculator_available else None
    
    def load_trades(self, file_path: str = None) -> bool:
        """
        Tải dữ liệu giao dịch từ file
        
        Args:
            file_path (str): Đường dẫn file
            
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        if file_path is None:
            file_path = os.path.join(self.data_dir, 'trades.json')
        
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    self.trades = json.load(f)
                logger.info(f"Đã tải {len(self.trades)} giao dịch từ {file_path}")
                return True
            else:
                logger.warning(f"File {file_path} không tồn tại")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi tải giao dịch: {str(e)}")
            return False
    
    def save_trades(self, file_path: str = None) -> bool:
        """
        Lưu dữ liệu giao dịch vào file
        
        Args:
            file_path (str): Đường dẫn file
            
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        if file_path is None:
            file_path = os.path.join(self.data_dir, 'trades.json')
        
        try:
            with open(file_path, 'w') as f:
                json.dump(self.trades, f, indent=4)
            logger.info(f"Đã lưu {len(self.trades)} giao dịch vào {file_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu giao dịch: {str(e)}")
            return False
    
    def add_trade(self, trade: Dict) -> bool:
        """
        Thêm giao dịch mới
        
        Args:
            trade (Dict): Thông tin giao dịch
            
        Returns:
            bool: True nếu thêm thành công, False nếu không
        """
        required_fields = ['symbol', 'side', 'entry_price', 'exit_price', 'quantity']
        if not all(field in trade for field in required_fields):
            logger.error(f"Giao dịch thiếu thông tin: {trade}")
            return False
        
        # Tính PnL chi tiết nếu có PnLCalculator
        if self.pnl_calculator:
            try:
                # Tính toán PnL chi tiết
                pnl_details = self.pnl_calculator.calculate_pnl_with_full_details(
                    entry_price=trade['entry_price'],
                    exit_price=trade['exit_price'],
                    position_size=trade['quantity'],
                    leverage=trade.get('leverage', 1),
                    position_side=trade['side'],
                    entry_time=trade.get('entry_time'),
                    exit_time=trade.get('exit_time'),
                    symbol=trade['symbol'],
                    partial_exits=trade.get('partial_exits')
                )
                
                # Cập nhật thông tin giao dịch với PnL chi tiết
                trade.update(pnl_details)
            except Exception as e:
                logger.error(f"Lỗi khi tính PnL chi tiết: {str(e)}")
                
                # Tính toán PnL đơn giản nếu không tính được chi tiết
                if 'side' in trade and 'entry_price' in trade and 'exit_price' in trade:
                    if trade['side'] == 'LONG':
                        trade['net_pnl'] = (trade['exit_price'] - trade['entry_price']) * trade['quantity']
                    else:  # SHORT
                        trade['net_pnl'] = (trade['entry_price'] - trade['exit_price']) * trade['quantity']
        else:
            # Tính toán PnL đơn giản
            if 'side' in trade and 'entry_price' in trade and 'exit_price' in trade:
                if trade['side'] == 'LONG':
                    trade['net_pnl'] = (trade['exit_price'] - trade['entry_price']) * trade['quantity']
                else:  # SHORT
                    trade['net_pnl'] = (trade['entry_price'] - trade['exit_price']) * trade['quantity']
        
        # Thêm ID nếu chưa có
        if 'trade_id' not in trade:
            trade['trade_id'] = f"trade_{int(time.time())}_{len(self.trades)}"
        
        # Thêm timestamp nếu chưa có
        if 'timestamp' not in trade:
            trade['timestamp'] = int(time.time())
        
        # Thêm vào danh sách
        self.trades.append(trade)
        logger.info(f"Đã thêm giao dịch {trade['trade_id']} ({trade['symbol']})")
        
        return True
    
    def calculate_equity_curve(self, initial_balance: float = 10000.0) -> List[float]:
        """
        Tính đường cong vốn
        
        Args:
            initial_balance (float): Số dư ban đầu
            
        Returns:
            List[float]: Đường cong vốn
        """
        if not self.trades:
            return [initial_balance]
        
        # Sắp xếp giao dịch theo thời gian
        sorted_trades = sorted(self.trades, key=lambda t: t.get('timestamp', 0))
        
        # Tính đường cong vốn
        equity = [initial_balance]
        current_balance = initial_balance
        
        for trade in sorted_trades:
            if 'net_pnl' in trade:
                current_balance += trade['net_pnl']
                equity.append(current_balance)
        
        self.equity_curve = equity
        return equity
    
    def calculate_daily_returns(self) -> List[float]:
        """
        Tính lợi nhuận hàng ngày
        
        Returns:
            List[float]: Lợi nhuận hàng ngày (%)
        """
        if not self.equity_curve or len(self.equity_curve) < 2:
            return []
        
        # Tính lợi nhuận tương đối (%)
        returns = [(self.equity_curve[i] / self.equity_curve[i-1] - 1) * 100 
                  for i in range(1, len(self.equity_curve))]
        
        self.daily_returns = returns
        return returns
    
    def get_trade_statistics(self) -> Dict:
        """
        Tính toán các thống kê giao dịch
        
        Returns:
            Dict: Các thống kê giao dịch
        """
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'expectancy': 0.0,
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'max_drawdown': 0.0,
                'avg_profit': 0.0,
                'avg_loss': 0.0,
                'total_profit': 0.0,
                'total_loss': 0.0,
                'net_profit': 0.0,
                'biggest_winner': 0.0,
                'biggest_loser': 0.0,
                'average_trade': 0.0,
                'average_bars_winners': 0,
                'average_bars_losers': 0,
                'trades_per_day': 0.0
            }
        
        # Đảm bảo đã tính equity curve và daily returns
        if not self.equity_curve:
            self.calculate_equity_curve()
        
        if not self.daily_returns:
            self.calculate_daily_returns()
        
        # Chuẩn bị dữ liệu
        winning_trades = [t for t in self.trades if t.get('net_pnl', 0) > 0]
        losing_trades = [t for t in self.trades if t.get('net_pnl', 0) < 0]
        
        total_profit = sum(t.get('net_pnl', 0) for t in winning_trades)
        total_loss = sum(t.get('net_pnl', 0) for t in losing_trades)
        net_profit = total_profit + total_loss
        
        # Tính các chỉ số
        win_rate = PerformanceMetrics.calculate_win_rate(self.trades)
        profit_factor = PerformanceMetrics.calculate_profit_factor(self.trades)
        expectancy = PerformanceMetrics.calculate_expectancy(self.trades)
        avg_profit, avg_loss = PerformanceMetrics.calculate_average_profit_loss(self.trades)
        
        sharpe_ratio = PerformanceMetrics.calculate_sharpe_ratio(self.daily_returns)
        sortino_ratio = PerformanceMetrics.calculate_sortino_ratio(self.daily_returns)
        max_drawdown, _, _ = PerformanceMetrics.calculate_max_drawdown(self.equity_curve)
        
        # Tìm giao dịch lời/lỗ nhất
        biggest_winner = max(self.trades, key=lambda t: t.get('net_pnl', 0)).get('net_pnl', 0) if self.trades else 0.0
        biggest_loser = min(self.trades, key=lambda t: t.get('net_pnl', 0)).get('net_pnl', 0) if self.trades else 0.0
        
        # Tính thời gian trung bình giữ vị thế
        bars_winners = []
        bars_losers = []
        
        for trade in self.trades:
            entry_time = trade.get('entry_time')
            exit_time = trade.get('exit_time')
            
            if entry_time and exit_time:
                bars = (exit_time - entry_time) / 3600  # Giờ
                
                if trade.get('net_pnl', 0) > 0:
                    bars_winners.append(bars)
                else:
                    bars_losers.append(bars)
        
        avg_bars_winners = np.mean(bars_winners) if bars_winners else 0
        avg_bars_losers = np.mean(bars_losers) if bars_losers else 0
        
        # Tính số giao dịch trung bình mỗi ngày
        if len(self.trades) >= 2:
            earliest_trade = min(self.trades, key=lambda t: t.get('timestamp', 0))
            latest_trade = max(self.trades, key=lambda t: t.get('timestamp', 0))
            
            earliest_time = earliest_trade.get('timestamp', 0)
            latest_time = latest_trade.get('timestamp', 0)
            
            days_trading = (latest_time - earliest_time) / (24 * 3600) + 1
            trades_per_day = len(self.trades) / days_trading if days_trading > 0 else 0
        else:
            trades_per_day = 0
        
        return {
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'total_profit': total_profit,
            'total_loss': total_loss,
            'net_profit': net_profit,
            'biggest_winner': biggest_winner,
            'biggest_loser': biggest_loser,
            'average_trade': net_profit / len(self.trades) if self.trades else 0.0,
            'average_bars_winners': avg_bars_winners,
            'average_bars_losers': avg_bars_losers,
            'trades_per_day': trades_per_day
        }
    
    def analyze_by_strategy(self) -> Dict:
        """
        Phân tích hiệu suất theo chiến lược
        
        Returns:
            Dict: Hiệu suất theo chiến lược
        """
        result = {}
        
        # Phân loại giao dịch theo chiến lược
        strategy_trades = {}
        
        for trade in self.trades:
            strategy = trade.get('strategy', 'unknown')
            
            if strategy not in strategy_trades:
                strategy_trades[strategy] = []
                
            strategy_trades[strategy].append(trade)
        
        # Tính hiệu suất cho mỗi chiến lược
        for strategy, trades in strategy_trades.items():
            if not trades:
                continue
                
            # Tính các chỉ số cơ bản
            total_trades = len(trades)
            winning_trades = [t for t in trades if t.get('net_pnl', 0) > 0]
            win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
            
            total_profit = sum(t.get('net_pnl', 0) for t in winning_trades)
            total_loss = sum(t.get('net_pnl', 0) for t in trades if t.get('net_pnl', 0) < 0)
            net_profit = total_profit + total_loss
            
            profit_factor = PerformanceMetrics.calculate_profit_factor(trades)
            expectancy = PerformanceMetrics.calculate_expectancy(trades)
            
            result[strategy] = {
                'total_trades': total_trades,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'expectancy': expectancy,
                'net_profit': net_profit,
                'average_trade': net_profit / total_trades if total_trades > 0 else 0.0
            }
        
        self.strategy_performance = result
        return result
    
    def analyze_by_symbol(self) -> Dict:
        """
        Phân tích hiệu suất theo cặp giao dịch
        
        Returns:
            Dict: Hiệu suất theo cặp giao dịch
        """
        result = {}
        
        # Phân loại giao dịch theo cặp
        symbol_trades = {}
        
        for trade in self.trades:
            symbol = trade.get('symbol', 'unknown')
            
            if symbol not in symbol_trades:
                symbol_trades[symbol] = []
                
            symbol_trades[symbol].append(trade)
        
        # Tính hiệu suất cho mỗi cặp
        for symbol, trades in symbol_trades.items():
            if not trades:
                continue
                
            # Tính các chỉ số cơ bản
            total_trades = len(trades)
            winning_trades = [t for t in trades if t.get('net_pnl', 0) > 0]
            win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
            
            total_profit = sum(t.get('net_pnl', 0) for t in winning_trades)
            total_loss = sum(t.get('net_pnl', 0) for t in trades if t.get('net_pnl', 0) < 0)
            net_profit = total_profit + total_loss
            
            profit_factor = PerformanceMetrics.calculate_profit_factor(trades)
            expectancy = PerformanceMetrics.calculate_expectancy(trades)
            
            result[symbol] = {
                'total_trades': total_trades,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'expectancy': expectancy,
                'net_profit': net_profit,
                'average_trade': net_profit / total_trades if total_trades > 0 else 0.0
            }
        
        self.symbol_performance = result
        return result
    
    def analyze_by_market_regime(self) -> Dict:
        """
        Phân tích hiệu suất theo chế độ thị trường
        
        Returns:
            Dict: Hiệu suất theo chế độ thị trường
        """
        result = {}
        
        # Phân loại giao dịch theo chế độ thị trường
        regime_trades = {}
        
        for trade in self.trades:
            regime = trade.get('market_regime', 'unknown')
            
            if regime not in regime_trades:
                regime_trades[regime] = []
                
            regime_trades[regime].append(trade)
        
        # Tính hiệu suất cho mỗi chế độ
        for regime, trades in regime_trades.items():
            if not trades:
                continue
                
            # Tính các chỉ số cơ bản
            total_trades = len(trades)
            winning_trades = [t for t in trades if t.get('net_pnl', 0) > 0]
            win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
            
            total_profit = sum(t.get('net_pnl', 0) for t in winning_trades)
            total_loss = sum(t.get('net_pnl', 0) for t in trades if t.get('net_pnl', 0) < 0)
            net_profit = total_profit + total_loss
            
            profit_factor = PerformanceMetrics.calculate_profit_factor(trades)
            expectancy = PerformanceMetrics.calculate_expectancy(trades)
            
            result[regime] = {
                'total_trades': total_trades,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'expectancy': expectancy,
                'net_profit': net_profit,
                'average_trade': net_profit / total_trades if total_trades > 0 else 0.0
            }
        
        self.regime_performance = result
        return result
    
    def analyze_performance_by_time(self) -> Dict:
        """
        Phân tích hiệu suất theo thời gian
        
        Returns:
            Dict: Hiệu suất theo thời gian
        """
        if not self.trades:
            return {
                'daily': {},
                'weekly': {},
                'monthly': {}
            }
        
        # Sắp xếp giao dịch theo thời gian
        sorted_trades = sorted(self.trades, key=lambda t: t.get('timestamp', 0))
        
        # Phân loại giao dịch theo ngày, tuần, tháng
        daily_trades = {}
        weekly_trades = {}
        monthly_trades = {}
        
        for trade in sorted_trades:
            timestamp = trade.get('timestamp', 0)
            if timestamp == 0:
                continue
                
            dt = datetime.datetime.fromtimestamp(timestamp)
            
            # Ngày
            day_key = dt.strftime('%Y-%m-%d')
            if day_key not in daily_trades:
                daily_trades[day_key] = []
            daily_trades[day_key].append(trade)
            
            # Tuần
            week_key = f"{dt.year}-W{dt.isocalendar()[1]}"
            if week_key not in weekly_trades:
                weekly_trades[week_key] = []
            weekly_trades[week_key].append(trade)
            
            # Tháng
            month_key = dt.strftime('%Y-%m')
            if month_key not in monthly_trades:
                monthly_trades[month_key] = []
            monthly_trades[month_key].append(trade)
        
        # Tính hiệu suất
        daily_performance = {}
        weekly_performance = {}
        monthly_performance = {}
        
        # Hàm hỗ trợ tính hiệu suất
        def calculate_period_performance(trades):
            total_trades = len(trades)
            winning_trades = [t for t in trades if t.get('net_pnl', 0) > 0]
            win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
            
            total_profit = sum(t.get('net_pnl', 0) for t in winning_trades)
            total_loss = sum(t.get('net_pnl', 0) for t in trades if t.get('net_pnl', 0) < 0)
            net_profit = total_profit + total_loss
            
            return {
                'total_trades': total_trades,
                'win_rate': win_rate,
                'net_profit': net_profit,
                'average_trade': net_profit / total_trades if total_trades > 0 else 0.0
            }
        
        # Tính hiệu suất theo ngày
        for day, trades in daily_trades.items():
            daily_performance[day] = calculate_period_performance(trades)
            
        # Tính hiệu suất theo tuần
        for week, trades in weekly_trades.items():
            weekly_performance[week] = calculate_period_performance(trades)
            
        # Tính hiệu suất theo tháng
        for month, trades in monthly_trades.items():
            monthly_performance[month] = calculate_period_performance(trades)
        
        return {
            'daily': daily_performance,
            'weekly': weekly_performance,
            'monthly': monthly_performance
        }
    
    def analyze_position_sizing(self) -> Dict:
        """
        Phân tích sizing vị thế
        
        Returns:
            Dict: Phân tích sizing
        """
        if not self.trades:
            return {
                'average_position_size': 0.0,
                'average_leverage': 0.0,
                'average_risk_percentage': 0.0,
                'size_vs_performance': {}
            }
        
        # Tính kích thước vị thế và đòn bẩy trung bình
        position_sizes = [t.get('quantity', 0) * t.get('entry_price', 0) for t in self.trades]
        leverages = [t.get('leverage', 1) for t in self.trades]
        
        avg_position_size = np.mean(position_sizes) if position_sizes else 0.0
        avg_leverage = np.mean(leverages) if leverages else 0.0
        
        # Phân nhóm kích thước vị thế
        size_groups = {
            'small': [],
            'medium': [],
            'large': []
        }
        
        # Phân loại vị thế
        if position_sizes:
            min_size = min(position_sizes)
            max_size = max(position_sizes)
            range_size = max_size - min_size
            
            if range_size > 0:
                for trade in self.trades:
                    position_size = trade.get('quantity', 0) * trade.get('entry_price', 0)
                    
                    if position_size < min_size + range_size / 3:
                        size_groups['small'].append(trade)
                    elif position_size < min_size + 2 * range_size / 3:
                        size_groups['medium'].append(trade)
                    else:
                        size_groups['large'].append(trade)
            else:
                size_groups['medium'] = self.trades
        
        # Tính hiệu suất cho mỗi nhóm
        size_performance = {}
        
        for size, trades in size_groups.items():
            if not trades:
                continue
                
            # Tính các chỉ số
            total_trades = len(trades)
            winning_trades = [t for t in trades if t.get('net_pnl', 0) > 0]
            win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
            
            total_profit = sum(t.get('net_pnl', 0) for t in winning_trades)
            total_loss = sum(t.get('net_pnl', 0) for t in trades if t.get('net_pnl', 0) < 0)
            net_profit = total_profit + total_loss
            
            avg_position = np.mean([t.get('quantity', 0) * t.get('entry_price', 0) for t in trades])
            
            size_performance[size] = {
                'total_trades': total_trades,
                'win_rate': win_rate,
                'net_profit': net_profit,
                'average_trade': net_profit / total_trades if total_trades > 0 else 0.0,
                'average_position_size': avg_position
            }
        
        # Tính ước lượng % rủi ro trung bình
        risk_percentages = []
        
        for trade in self.trades:
            entry_price = trade.get('entry_price', 0)
            stop_loss = trade.get('stop_loss', 0)
            
            if entry_price > 0 and stop_loss > 0:
                if trade.get('side', '') == 'LONG':
                    risk_pct = (entry_price - stop_loss) / entry_price * 100
                else:  # SHORT
                    risk_pct = (stop_loss - entry_price) / entry_price * 100
                    
                risk_percentages.append(risk_pct)
        
        avg_risk_percentage = np.mean(risk_percentages) if risk_percentages else 0.0
        
        return {
            'average_position_size': avg_position_size,
            'average_leverage': avg_leverage,
            'average_risk_percentage': avg_risk_percentage,
            'size_vs_performance': size_performance
        }
    
    def generate_full_report(self, output_path: str = None) -> str:
        """
        Tạo báo cáo tổng hợp
        
        Args:
            output_path (str): Đường dẫn file báo cáo
            
        Returns:
            str: Nội dung báo cáo
        """
        if output_path is None:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(self.reports_dir, f'performance_report_{timestamp}.html')
        
        # Kiểm tra đường dẫn
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Phân tích dữ liệu
        trade_stats = self.get_trade_statistics()
        self.analyze_by_strategy()
        self.analyze_by_symbol()
        self.analyze_by_market_regime()
        time_analysis = self.analyze_performance_by_time()
        sizing_analysis = self.analyze_position_sizing()
        
        # Tạo báo cáo HTML
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Trading Performance Report</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    line-height: 1.6;
                    color: #333;
                }
                h1, h2, h3 {
                    color: #2c3e50;
                }
                .section {
                    margin-bottom: 30px;
                    border: 1px solid #ddd;
                    padding: 20px;
                    border-radius: 5px;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 20px;
                }
                th, td {
                    padding: 10px;
                    border: 1px solid #ddd;
                    text-align: left;
                }
                th {
                    background-color: #f2f2f2;
                }
                .positive {
                    color: green;
                }
                .negative {
                    color: red;
                }
                .metrics-container {
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: space-between;
                }
                .metric-box {
                    flex: 0 0 30%;
                    margin-bottom: 20px;
                    padding: 15px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    background-color: #f9f9f9;
                }
                .metric-name {
                    font-weight: bold;
                    margin-bottom: 5px;
                }
                .metric-value {
                    font-size: 1.4em;
                    font-weight: bold;
                }
            </style>
        </head>
        <body>
            <h1>Trading Performance Report</h1>
            <p>Generated on: """ + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
            
            <div class="section">
                <h2>Overall Performance</h2>
                <div class="metrics-container">
                    <div class="metric-box">
                        <div class="metric-name">Total Trades</div>
                        <div class="metric-value">""" + str(trade_stats['total_trades']) + """</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-name">Win Rate</div>
                        <div class="metric-value">""" + f"{trade_stats['win_rate']*100:.2f}%" + """</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-name">Profit Factor</div>
                        <div class="metric-value">""" + f"{trade_stats['profit_factor']:.2f}" + """</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-name">Net Profit</div>
                        <div class="metric-value """ + ("positive" if trade_stats['net_profit'] > 0 else "negative") + """">""" + f"{trade_stats['net_profit']:.2f}" + """</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-name">Sharpe Ratio</div>
                        <div class="metric-value">""" + f"{trade_stats['sharpe_ratio']:.2f}" + """</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-name">Max Drawdown</div>
                        <div class="metric-value negative">""" + f"{trade_stats['max_drawdown']:.2f}%" + """</div>
                    </div>
                </div>
                
                <h3>Detailed Statistics</h3>
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
                    <tr>
                        <td>Total Trades</td>
                        <td>""" + str(trade_stats['total_trades']) + """</td>
                    </tr>
                    <tr>
                        <td>Winning Trades</td>
                        <td>""" + str(trade_stats['winning_trades']) + """</td>
                    </tr>
                    <tr>
                        <td>Losing Trades</td>
                        <td>""" + str(trade_stats['losing_trades']) + """</td>
                    </tr>
                    <tr>
                        <td>Win Rate</td>
                        <td>""" + f"{trade_stats['win_rate']*100:.2f}%" + """</td>
                    </tr>
                    <tr>
                        <td>Profit Factor</td>
                        <td>""" + f"{trade_stats['profit_factor']:.2f}" + """</td>
                    </tr>
                    <tr>
                        <td>Expectancy</td>
                        <td>""" + f"{trade_stats['expectancy']:.2f}" + """</td>
                    </tr>
                    <tr>
                        <td>Sharpe Ratio</td>
                        <td>""" + f"{trade_stats['sharpe_ratio']:.2f}" + """</td>
                    </tr>
                    <tr>
                        <td>Sortino Ratio</td>
                        <td>""" + f"{trade_stats['sortino_ratio']:.2f}" + """</td>
                    </tr>
                    <tr>
                        <td>Max Drawdown</td>
                        <td class="negative">""" + f"{trade_stats['max_drawdown']:.2f}%" + """</td>
                    </tr>
                    <tr>
                        <td>Average Profit</td>
                        <td class="positive">""" + f"{trade_stats['avg_profit']:.2f}" + """</td>
                    </tr>
                    <tr>
                        <td>Average Loss</td>
                        <td class="negative">""" + f"{trade_stats['avg_loss']:.2f}" + """</td>
                    </tr>
                    <tr>
                        <td>Total Profit</td>
                        <td class="positive">""" + f"{trade_stats['total_profit']:.2f}" + """</td>
                    </tr>
                    <tr>
                        <td>Total Loss</td>
                        <td class="negative">""" + f"{trade_stats['total_loss']:.2f}" + """</td>
                    </tr>
                    <tr>
                        <td>Net Profit</td>
                        <td class="positive">""" + f"{trade_stats['net_profit']:.2f}" + """</td>
                    </tr>
                    <tr>
                        <td>Biggest Winner</td>
                        <td class="positive">""" + f"{trade_stats['biggest_winner']:.2f}" + """</td>
                    </tr>
                    <tr>
                        <td>Biggest Loser</td>
                        <td class="negative">""" + f"{trade_stats['biggest_loser']:.2f}" + """</td>
                    </tr>
                    <tr>
                        <td>Average Trade</td>
                        <td>""" + f"{trade_stats['average_trade']:.2f}" + """</td>
                    </tr>
                    <tr>
                        <td>Average Hold Time (Winners)</td>
                        <td>""" + f"{trade_stats['average_bars_winners']:.2f} hours" + """</td>
                    </tr>
                    <tr>
                        <td>Average Hold Time (Losers)</td>
                        <td>""" + f"{trade_stats['average_bars_losers']:.2f} hours" + """</td>
                    </tr>
                    <tr>
                        <td>Trades Per Day</td>
                        <td>""" + f"{trade_stats['trades_per_day']:.2f}" + """</td>
                    </tr>
                </table>
            </div>
            
            <div class="section">
                <h2>Performance by Strategy</h2>
                <table>
                    <tr>
                        <th>Strategy</th>
                        <th>Trades</th>
                        <th>Win Rate</th>
                        <th>Profit Factor</th>
                        <th>Net Profit</th>
                        <th>Avg Profit</th>
                    </tr>
        """
        
        # Thêm dữ liệu hiệu suất theo chiến lược
        for strategy, stats in self.strategy_performance.items():
            html += f"""
                    <tr>
                        <td>{strategy}</td>
                        <td>{stats['total_trades']}</td>
                        <td>{stats['win_rate']*100:.2f}%</td>
                        <td>{stats['profit_factor']:.2f}</td>
                        <td class="{'positive' if stats['net_profit'] > 0 else 'negative'}">{stats['net_profit']:.2f}</td>
                        <td class="{'positive' if stats['average_trade'] > 0 else 'negative'}">{stats['average_trade']:.2f}</td>
                    </tr>
            """
            
        html += """
                </table>
            </div>
            
            <div class="section">
                <h2>Performance by Symbol</h2>
                <table>
                    <tr>
                        <th>Symbol</th>
                        <th>Trades</th>
                        <th>Win Rate</th>
                        <th>Profit Factor</th>
                        <th>Net Profit</th>
                        <th>Avg Profit</th>
                    </tr>
        """
        
        # Thêm dữ liệu hiệu suất theo cặp giao dịch
        for symbol, stats in self.symbol_performance.items():
            html += f"""
                    <tr>
                        <td>{symbol}</td>
                        <td>{stats['total_trades']}</td>
                        <td>{stats['win_rate']*100:.2f}%</td>
                        <td>{stats['profit_factor']:.2f}</td>
                        <td class="{'positive' if stats['net_profit'] > 0 else 'negative'}">{stats['net_profit']:.2f}</td>
                        <td class="{'positive' if stats['average_trade'] > 0 else 'negative'}">{stats['average_trade']:.2f}</td>
                    </tr>
            """
            
        html += """
                </table>
            </div>
            
            <div class="section">
                <h2>Performance by Market Regime</h2>
                <table>
                    <tr>
                        <th>Market Regime</th>
                        <th>Trades</th>
                        <th>Win Rate</th>
                        <th>Profit Factor</th>
                        <th>Net Profit</th>
                        <th>Avg Profit</th>
                    </tr>
        """
        
        # Thêm dữ liệu hiệu suất theo chế độ thị trường
        for regime, stats in self.regime_performance.items():
            html += f"""
                    <tr>
                        <td>{regime}</td>
                        <td>{stats['total_trades']}</td>
                        <td>{stats['win_rate']*100:.2f}%</td>
                        <td>{stats['profit_factor']:.2f}</td>
                        <td class="{'positive' if stats['net_profit'] > 0 else 'negative'}">{stats['net_profit']:.2f}</td>
                        <td class="{'positive' if stats['average_trade'] > 0 else 'negative'}">{stats['average_trade']:.2f}</td>
                    </tr>
            """
            
        html += """
                </table>
            </div>
            
            <div class="section">
                <h2>Position Sizing Analysis</h2>
                <h3>Position Size Metrics</h3>
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
                    <tr>
                        <td>Average Position Size</td>
                        <td>""" + f"{sizing_analysis['average_position_size']:.2f}" + """</td>
                    </tr>
                    <tr>
                        <td>Average Leverage</td>
                        <td>""" + f"{sizing_analysis['average_leverage']:.2f}x" + """</td>
                    </tr>
                    <tr>
                        <td>Average Risk Percentage</td>
                        <td>""" + f"{sizing_analysis['average_risk_percentage']:.2f}%" + """</td>
                    </tr>
                </table>
                
                <h3>Performance by Position Size</h3>
                <table>
                    <tr>
                        <th>Size Category</th>
                        <th>Trades</th>
                        <th>Win Rate</th>
                        <th>Net Profit</th>
                        <th>Avg Position Size</th>
                    </tr>
        """
        
        # Thêm dữ liệu hiệu suất theo kích thước vị thế
        for size, stats in sizing_analysis['size_vs_performance'].items():
            html += f"""
                    <tr>
                        <td>{size}</td>
                        <td>{stats['total_trades']}</td>
                        <td>{stats['win_rate']*100:.2f}%</td>
                        <td class="{'positive' if stats['net_profit'] > 0 else 'negative'}">{stats['net_profit']:.2f}</td>
                        <td>{stats['average_position_size']:.2f}</td>
                    </tr>
            """
            
        html += """
                </table>
            </div>
            
            <div class="section">
                <h2>Monthly Performance</h2>
                <table>
                    <tr>
                        <th>Month</th>
                        <th>Trades</th>
                        <th>Win Rate</th>
                        <th>Net Profit</th>
                        <th>Avg Profit</th>
                    </tr>
        """
        
        # Thêm dữ liệu hiệu suất theo tháng
        sorted_months = sorted(time_analysis['monthly'].keys())
        for month in sorted_months:
            stats = time_analysis['monthly'][month]
            html += f"""
                    <tr>
                        <td>{month}</td>
                        <td>{stats['total_trades']}</td>
                        <td>{stats['win_rate']*100:.2f}%</td>
                        <td class="{'positive' if stats['net_profit'] > 0 else 'negative'}">{stats['net_profit']:.2f}</td>
                        <td class="{'positive' if stats['average_trade'] > 0 else 'negative'}">{stats['average_trade']:.2f}</td>
                    </tr>
            """
            
        html += """
                </table>
            </div>
            
            <div class="footer">
                <p>Generated by Performance Monitor v1.0</p>
            </div>
        </body>
        </html>
        """
        
        # Lưu file
        with open(output_path, 'w') as f:
            f.write(html)
        
        logger.info(f"Đã tạo báo cáo tại {output_path}")
        
        return html
    
    def plot_equity_curve(self, output_path: str = None) -> str:
        """
        Vẽ đường cong vốn
        
        Args:
            output_path (str): Đường dẫn lưu biểu đồ
            
        Returns:
            str: Đường dẫn đến biểu đồ
        """
        if not self.equity_curve:
            self.calculate_equity_curve()
            
        if len(self.equity_curve) < 2:
            logger.warning("Không đủ dữ liệu để vẽ đường cong vốn")
            return ""
            
        if output_path is None:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(self.reports_dir, f'equity_curve_{timestamp}.png')
            
        # Đảm bảo thư mục tồn tại
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Vẽ biểu đồ
        plt.figure(figsize=(12, 6))
        plt.plot(self.equity_curve, label='Equity Curve')
        plt.title('Equity Curve')
        plt.xlabel('Trades')
        plt.ylabel('Equity')
        plt.grid(True)
        plt.legend()
        
        # Tính và vẽ drawdown
        equity_array = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (running_max - equity_array) / running_max * 100
        
        plt.twinx()
        plt.plot(drawdown, 'r--', alpha=0.5, label='Drawdown (%)')
        plt.ylabel('Drawdown (%)')
        plt.legend(loc='lower right')
        
        # Lưu biểu đồ
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        
        logger.info(f"Đã lưu biểu đồ đường cong vốn tại {output_path}")
        
        return output_path
    
    def plot_win_loss_distribution(self, output_path: str = None) -> str:
        """
        Vẽ biểu đồ phân phối lợi nhuận/lỗ
        
        Args:
            output_path (str): Đường dẫn lưu biểu đồ
            
        Returns:
            str: Đường dẫn đến biểu đồ
        """
        if not self.trades:
            logger.warning("Không có giao dịch để vẽ biểu đồ phân phối")
            return ""
            
        if output_path is None:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(self.reports_dir, f'pnl_distribution_{timestamp}.png')
            
        # Đảm bảo thư mục tồn tại
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Lấy dữ liệu PnL
        pnl_values = [t.get('net_pnl', 0) for t in self.trades]
        
        # Vẽ biểu đồ
        plt.figure(figsize=(12, 6))
        
        # Histogram
        plt.hist(pnl_values, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
        
        # Thêm đường mean và median
        plt.axvline(np.mean(pnl_values), color='red', linestyle='dashed', linewidth=1, label=f'Mean: {np.mean(pnl_values):.2f}')
        plt.axvline(np.median(pnl_values), color='green', linestyle='dashed', linewidth=1, label=f'Median: {np.median(pnl_values):.2f}')
        
        # Zero line
        plt.axvline(0, color='black', linestyle='-', linewidth=1)
        
        plt.title('P&L Distribution')
        plt.xlabel('P&L Value')
        plt.ylabel('Frequency')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Lưu biểu đồ
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        
        logger.info(f"Đã lưu biểu đồ phân phối P&L tại {output_path}")
        
        return output_path
    
    def plot_monthly_performance(self, output_path: str = None) -> str:
        """
        Vẽ biểu đồ hiệu suất theo tháng
        
        Args:
            output_path (str): Đường dẫn lưu biểu đồ
            
        Returns:
            str: Đường dẫn đến biểu đồ
        """
        # Phân tích theo thời gian nếu chưa
        time_analysis = self.analyze_performance_by_time()
        monthly_data = time_analysis['monthly']
        
        if not monthly_data:
            logger.warning("Không có dữ liệu tháng để vẽ biểu đồ")
            return ""
            
        if output_path is None:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(self.reports_dir, f'monthly_performance_{timestamp}.png')
            
        # Đảm bảo thư mục tồn tại
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Chuẩn bị dữ liệu
        months = sorted(monthly_data.keys())
        profits = [monthly_data[m]['net_profit'] for m in months]
        win_rates = [monthly_data[m]['win_rate'] * 100 for m in months]
        trade_counts = [monthly_data[m]['total_trades'] for m in months]
        
        # Vẽ biểu đồ
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
        
        # Profit by month
        bars = ax1.bar(months, profits, color=['green' if p > 0 else 'red' for p in profits])
        ax1.set_title('Monthly Net Profit')
        ax1.set_ylabel('Net Profit')
        ax1.grid(True, alpha=0.3)
        
        # Add values on bars
        for bar, value in zip(bars, profits):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., 
                    height + (5 if height > 0 else -15),
                    f'{value:.2f}',
                    ha='center', va='bottom' if height > 0 else 'top',
                    rotation=0)
        
        # Win rate and trade count
        ax2.bar(months, trade_counts, alpha=0.3, label='Trade Count')
        ax2.set_xlabel('Month')
        ax2.set_ylabel('Trade Count')
        
        ax2b = ax2.twinx()
        ax2b.plot(months, win_rates, 'ro-', label='Win Rate')
        ax2b.set_ylabel('Win Rate (%)')
        ax2b.set_ylim(0, 100)
        
        # Combine legends
        lines1, labels1 = ax2.get_legend_handles_labels()
        lines2, labels2 = ax2b.get_legend_handles_labels()
        ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        
        logger.info(f"Đã lưu biểu đồ hiệu suất theo tháng tại {output_path}")
        
        return output_path


def main():
    """Hàm chính để test Performance Monitor"""
    print("=== Test Performance Monitor ===\n")
    
    # Khởi tạo monitor
    monitor = PerformanceMonitor()
    
    # Tạo một số giao dịch mẫu
    trades = [
        {
            'trade_id': 'trade_1',
            'symbol': 'BTCUSDT',
            'side': 'LONG',
            'entry_price': 50000,
            'exit_price': 52000,
            'quantity': 0.1,
            'leverage': 5,
            'entry_time': int(time.time()) - 7 * 24 * 3600,  # 7 ngày trước
            'exit_time': int(time.time()) - 6 * 24 * 3600,   # 6 ngày trước
            'strategy': 'trend_following',
            'market_regime': 'trending',
            'net_pnl': 1000  # (52000 - 50000) * 0.1 * 5
        },
        {
            'trade_id': 'trade_2',
            'symbol': 'ETHUSDT',
            'side': 'SHORT',
            'entry_price': 3000,
            'exit_price': 3100,
            'quantity': 0.5,
            'leverage': 3,
            'entry_time': int(time.time()) - 5 * 24 * 3600,  # 5 ngày trước
            'exit_time': int(time.time()) - 4 * 24 * 3600,   # 4 ngày trước
            'strategy': 'mean_reversion',
            'market_regime': 'ranging',
            'net_pnl': -150  # (3000 - 3100) * 0.5 * 3
        },
        {
            'trade_id': 'trade_3',
            'symbol': 'BTCUSDT',
            'side': 'LONG',
            'entry_price': 51000,
            'exit_price': 51500,
            'quantity': 0.2,
            'leverage': 3,
            'entry_time': int(time.time()) - 3 * 24 * 3600,  # 3 ngày trước
            'exit_time': int(time.time()) - 2 * 24 * 3600,   # 2 ngày trước
            'strategy': 'breakout',
            'market_regime': 'volatile',
            'net_pnl': 300  # (51500 - 51000) * 0.2 * 3
        },
        {
            'trade_id': 'trade_4',
            'symbol': 'SOLUSDT',
            'side': 'SHORT',
            'entry_price': 100,
            'exit_price': 90,
            'quantity': 2,
            'leverage': 2,
            'entry_time': int(time.time()) - 1 * 24 * 3600,  # 1 ngày trước
            'exit_time': int(time.time()) - 12 * 3600,       # 12 giờ trước
            'strategy': 'trend_following',
            'market_regime': 'trending',
            'net_pnl': 40  # (100 - 90) * 2 * 2
        }
    ]
    
    # Thêm các giao dịch
    for trade in trades:
        monitor.add_trade(trade)
    
    # Tính các chỉ số hiệu suất
    monitor.calculate_equity_curve()
    monitor.calculate_daily_returns()
    
    # Lấy thống kê
    stats = monitor.get_trade_statistics()
    print("Thống kê giao dịch:")
    print(f"Tổng số giao dịch: {stats['total_trades']}")
    print(f"Tỷ lệ thắng: {stats['win_rate']*100:.2f}%")
    print(f"Profit Factor: {stats['profit_factor']:.2f}")
    print(f"Lợi nhuận ròng: {stats['net_profit']:.2f}")
    print(f"Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
    print(f"Drawdown tối đa: {stats['max_drawdown']:.2f}%")
    
    # Phân tích theo chiến lược
    strategy_perf = monitor.analyze_by_strategy()
    print("\nHiệu suất theo chiến lược:")
    for strategy, perf in strategy_perf.items():
        print(f"{strategy}: Win Rate={perf['win_rate']*100:.2f}%, Profit={perf['net_profit']:.2f}")
    
    # Tạo báo cáo
    report_path = "example_report.html"
    monitor.generate_full_report(report_path)
    print(f"\nĐã tạo báo cáo tại: {report_path}")
    
    # Vẽ đường cong vốn
    equity_chart = monitor.plot_equity_curve("example_equity.png")
    print(f"Đã vẽ đường cong vốn tại: {equity_chart}")
    
    # Vẽ phân phối lợi nhuận
    pnl_chart = monitor.plot_win_loss_distribution("example_pnl.png")
    print(f"Đã vẽ phân phối lợi nhuận tại: {pnl_chart}")


if __name__ == "__main__":
    main()