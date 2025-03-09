"""
Module báo cáo nâng cao (Enhanced Reporting)

Module này cung cấp các công cụ báo cáo nâng cao cho hệ thống giao dịch:
- Phân tích hiệu suất theo điều kiện thị trường
- Tính toán Expectancy Score (chỉ số kỳ vọng lợi nhuận trên mỗi giao dịch)
- Phân tích rủi ro chi tiết (VaR, CVaR, Maximum Drawdown Duration)
- Thống kê edge giao dịch
- Hiển thị vùng giá xung đột (Order Book Heat Map)

Mục tiêu là cung cấp thông tin chi tiết hơn để đưa ra quyết định giao dịch hiệu quả.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from typing import Dict, List, Optional, Tuple, Union, Callable
from datetime import datetime, timedelta
import logging
import json
import os
from io import BytesIO
import base64
from collections import defaultdict

# Cấu hình logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("enhanced_reporting")

class PerformanceAnalyzer:
    """Phân tích hiệu suất giao dịch theo nhiều khía cạnh"""
    
    def __init__(self, trade_history: List[Dict] = None):
        """
        Khởi tạo Performance Analyzer.
        
        Args:
            trade_history (List[Dict], optional): Lịch sử giao dịch
        """
        self.trade_history = trade_history or []
        
        # Khởi tạo các thuộc tính phân tích
        self.metrics = {}
        self.market_regime_performance = {}
        self.symbol_performance = {}
        self.timeframe_performance = {}
        self.session_performance = {}
        self.drawdown_periods = []
        
        # Tính toán metrics nếu có dữ liệu
        if trade_history:
            self.calculate_all_metrics()
    
    def load_trade_history(self, trade_history: List[Dict]) -> None:
        """
        Tải lịch sử giao dịch mới.
        
        Args:
            trade_history (List[Dict]): Lịch sử giao dịch
        """
        self.trade_history = trade_history
        self.calculate_all_metrics()
        logger.info(f"Loaded trade history with {len(trade_history)} trades")
    
    def add_trade(self, trade: Dict) -> None:
        """
        Thêm một giao dịch vào lịch sử và cập nhật metrics.
        
        Args:
            trade (Dict): Thông tin giao dịch
        """
        self.trade_history.append(trade)
        self.calculate_all_metrics()
        logger.info(f"Added new trade. Total trades: {len(self.trade_history)}")
    
    def calculate_all_metrics(self) -> None:
        """Tính toán tất cả các metrics"""
        if not self.trade_history:
            logger.warning("No trade history to analyze")
            return
            
        # Tính toán metrics tổng thể
        self._calculate_overall_metrics()
        
        # Phân tích theo chế độ thị trường
        self._analyze_by_market_regime()
        
        # Phân tích theo symbol
        self._analyze_by_symbol()
        
        # Phân tích theo khung thời gian
        self._analyze_by_timeframe()
        
        # Phân tích theo phiên giao dịch
        self._analyze_by_session()
        
        # Tính toán các khoảng drawdown
        self._calculate_drawdown_periods()
        
        logger.info("All metrics calculated successfully")
    
    def _calculate_overall_metrics(self) -> None:
        """Tính toán các metrics tổng thể"""
        # Chuyển đổi thành DataFrame để dễ xử lý
        trades_df = pd.DataFrame(self.trade_history)
        
        # Đảm bảo các trường cần thiết
        required_fields = ['profit_loss', 'profit_loss_pct', 'status', 'entry_time', 'exit_time', 'symbol', 'initial_risk']
        for field in required_fields:
            if field not in trades_df.columns:
                if field in ['profit_loss', 'profit_loss_pct', 'initial_risk']:
                    trades_df[field] = 0.0
                elif field in ['entry_time', 'exit_time']:
                    trades_df[field] = pd.NaT
                else:
                    trades_df[field] = None
        
        # Chuyển đổi kiểu dữ liệu
        for time_field in ['entry_time', 'exit_time']:
            if time_field in trades_df.columns:
                trades_df[time_field] = pd.to_datetime(trades_df[time_field])
        
        # Tính số lượng giao dịch
        total_trades = len(trades_df)
        
        # Tính tỷ lệ thắng/thua
        winning_trades = trades_df[trades_df['profit_loss'] > 0]
        win_count = len(winning_trades)
        loss_count = total_trades - win_count
        win_rate = win_count / total_trades if total_trades > 0 else 0
        
        # Tính P&L
        total_profit = winning_trades['profit_loss'].sum() if not winning_trades.empty else 0
        total_loss = trades_df[trades_df['profit_loss'] <= 0]['profit_loss'].sum() if not trades_df[trades_df['profit_loss'] <= 0].empty else 0
        net_profit = total_profit + total_loss
        
        # Tính trung bình P&L
        avg_profit = winning_trades['profit_loss'].mean() if not winning_trades.empty else 0
        avg_loss = trades_df[trades_df['profit_loss'] < 0]['profit_loss'].mean() if not trades_df[trades_df['profit_loss'] < 0].empty else 0
        avg_trade = trades_df['profit_loss'].mean()
        
        # Tính Payoff Ratio
        payoff_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else float('inf')
        
        # Tính Expectancy (kỳ vọng lợi nhuận trên mỗi giao dịch)
        expectancy = (win_rate * avg_profit) + ((1 - win_rate) * avg_loss) if avg_loss != 0 else 0
        expectancy_r = (win_rate * payoff_ratio) - (1 - win_rate) if avg_loss != 0 else 0
        
        # Tính Risk-Adjusted Return
        if 'initial_risk' in trades_df.columns and (trades_df['initial_risk'] > 0).any():
            risk_adjusted_return = net_profit / trades_df['initial_risk'].sum()
        else:
            risk_adjusted_return = 0
        
        # Tính Profit Factor
        profit_factor = abs(total_profit / total_loss) if total_loss != 0 else float('inf')
        
        # Tính Recovery Factor
        max_drawdown = self._calculate_max_drawdown(trades_df)
        recovery_factor = net_profit / abs(max_drawdown) if max_drawdown != 0 else float('inf')
        
        # Tính Sharpe Ratio (giả định)
        if len(trades_df) > 1:
            returns = trades_df['profit_loss_pct'].values
            sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Tính các chỉ số thời gian
        if 'entry_time' in trades_df.columns and 'exit_time' in trades_df.columns:
            trades_df['duration'] = (trades_df['exit_time'] - trades_df['entry_time']).dt.total_seconds() / 3600  # hours
            avg_trade_duration = trades_df['duration'].mean()
            avg_win_duration = winning_trades['duration'].mean() if not winning_trades.empty else 0
            avg_loss_duration = trades_df[trades_df['profit_loss'] <= 0]['duration'].mean() if not trades_df[trades_df['profit_loss'] <= 0].empty else 0
        else:
            avg_trade_duration = avg_win_duration = avg_loss_duration = 0
        
        # Lưu tất cả metrics
        self.metrics = {
            'total_trades': total_trades,
            'win_count': win_count,
            'loss_count': loss_count,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'total_loss': total_loss,
            'net_profit': net_profit,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'avg_trade': avg_trade,
            'payoff_ratio': payoff_ratio,
            'expectancy': expectancy,
            'expectancy_r': expectancy_r,
            'risk_adjusted_return': risk_adjusted_return,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'recovery_factor': recovery_factor,
            'sharpe_ratio': sharpe_ratio,
            'avg_trade_duration': avg_trade_duration,
            'avg_win_duration': avg_win_duration,
            'avg_loss_duration': avg_loss_duration
        }
    
    def _analyze_by_market_regime(self) -> None:
        """Phân tích hiệu suất theo chế độ thị trường"""
        trades_df = pd.DataFrame(self.trade_history)
        
        # Kiểm tra xem có thông tin về chế độ thị trường không
        if 'market_regime' not in trades_df.columns:
            self.market_regime_performance = {}
            return
            
        # Nhóm theo chế độ thị trường và tính toán metrics
        grouped = trades_df.groupby('market_regime')
        
        market_regimes = {}
        for regime, group in grouped:
            # Bỏ qua nếu không có tên chế độ hợp lệ
            if pd.isna(regime) or regime == "":
                continue
                
            # Tính các metrics cho chế độ này
            win_count = len(group[group['profit_loss'] > 0])
            total_count = len(group)
            win_rate = win_count / total_count if total_count > 0 else 0
            
            total_profit = group[group['profit_loss'] > 0]['profit_loss'].sum() if not group[group['profit_loss'] > 0].empty else 0
            total_loss = group[group['profit_loss'] <= 0]['profit_loss'].sum() if not group[group['profit_loss'] <= 0].empty else 0
            net_profit = total_profit + total_loss
            
            avg_profit = group[group['profit_loss'] > 0]['profit_loss'].mean() if not group[group['profit_loss'] > 0].empty else 0
            avg_loss = group[group['profit_loss'] < 0]['profit_loss'].mean() if not group[group['profit_loss'] < 0].empty else 0
            
            payoff_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else float('inf')
            expectancy = (win_rate * avg_profit) + ((1 - win_rate) * avg_loss)
            
            # Lưu metrics cho chế độ này
            market_regimes[regime] = {
                'total_trades': total_count,
                'win_count': win_count,
                'loss_count': total_count - win_count,
                'win_rate': win_rate,
                'total_profit': total_profit,
                'total_loss': total_loss,
                'net_profit': net_profit,
                'avg_profit': avg_profit,
                'avg_loss': avg_loss,
                'payoff_ratio': payoff_ratio,
                'expectancy': expectancy
            }
        
        self.market_regime_performance = market_regimes
    
    def _analyze_by_symbol(self) -> None:
        """Phân tích hiệu suất theo symbol"""
        trades_df = pd.DataFrame(self.trade_history)
        
        # Kiểm tra xem có thông tin về symbol không
        if 'symbol' not in trades_df.columns:
            self.symbol_performance = {}
            return
            
        # Nhóm theo symbol và tính toán metrics
        grouped = trades_df.groupby('symbol')
        
        symbols = {}
        for symbol, group in grouped:
            # Bỏ qua nếu không có symbol hợp lệ
            if pd.isna(symbol) or symbol == "":
                continue
                
            # Tính các metrics cho symbol này
            win_count = len(group[group['profit_loss'] > 0])
            total_count = len(group)
            win_rate = win_count / total_count if total_count > 0 else 0
            
            total_profit = group[group['profit_loss'] > 0]['profit_loss'].sum() if not group[group['profit_loss'] > 0].empty else 0
            total_loss = group[group['profit_loss'] <= 0]['profit_loss'].sum() if not group[group['profit_loss'] <= 0].empty else 0
            net_profit = total_profit + total_loss
            
            avg_profit = group[group['profit_loss'] > 0]['profit_loss'].mean() if not group[group['profit_loss'] > 0].empty else 0
            avg_loss = group[group['profit_loss'] < 0]['profit_loss'].mean() if not group[group['profit_loss'] < 0].empty else 0
            
            payoff_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else float('inf')
            expectancy = (win_rate * avg_profit) + ((1 - win_rate) * avg_loss)
            
            # Lưu metrics cho symbol này
            symbols[symbol] = {
                'total_trades': total_count,
                'win_count': win_count,
                'loss_count': total_count - win_count,
                'win_rate': win_rate,
                'total_profit': total_profit,
                'total_loss': total_loss,
                'net_profit': net_profit,
                'avg_profit': avg_profit,
                'avg_loss': avg_loss,
                'payoff_ratio': payoff_ratio,
                'expectancy': expectancy
            }
        
        self.symbol_performance = symbols
    
    def _analyze_by_timeframe(self) -> None:
        """Phân tích hiệu suất theo khung thời gian"""
        trades_df = pd.DataFrame(self.trade_history)
        
        # Kiểm tra xem có thông tin về timeframe không
        if 'timeframe' not in trades_df.columns:
            self.timeframe_performance = {}
            return
            
        # Nhóm theo timeframe và tính toán metrics
        grouped = trades_df.groupby('timeframe')
        
        timeframes = {}
        for timeframe, group in grouped:
            # Bỏ qua nếu không có timeframe hợp lệ
            if pd.isna(timeframe) or timeframe == "":
                continue
                
            # Tính các metrics cho timeframe này
            win_count = len(group[group['profit_loss'] > 0])
            total_count = len(group)
            win_rate = win_count / total_count if total_count > 0 else 0
            
            total_profit = group[group['profit_loss'] > 0]['profit_loss'].sum() if not group[group['profit_loss'] > 0].empty else 0
            total_loss = group[group['profit_loss'] <= 0]['profit_loss'].sum() if not group[group['profit_loss'] <= 0].empty else 0
            net_profit = total_profit + total_loss
            
            avg_profit = group[group['profit_loss'] > 0]['profit_loss'].mean() if not group[group['profit_loss'] > 0].empty else 0
            avg_loss = group[group['profit_loss'] < 0]['profit_loss'].mean() if not group[group['profit_loss'] < 0].empty else 0
            
            payoff_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else float('inf')
            expectancy = (win_rate * avg_profit) + ((1 - win_rate) * avg_loss)
            
            # Lưu metrics cho timeframe này
            timeframes[timeframe] = {
                'total_trades': total_count,
                'win_count': win_count,
                'loss_count': total_count - win_count,
                'win_rate': win_rate,
                'total_profit': total_profit,
                'total_loss': total_loss,
                'net_profit': net_profit,
                'avg_profit': avg_profit,
                'avg_loss': avg_loss,
                'payoff_ratio': payoff_ratio,
                'expectancy': expectancy
            }
        
        self.timeframe_performance = timeframes
    
    def _analyze_by_session(self) -> None:
        """Phân tích hiệu suất theo phiên giao dịch"""
        trades_df = pd.DataFrame(self.trade_history)
        
        # Kiểm tra xem có thông tin về thời gian vào lệnh không
        if 'entry_time' not in trades_df.columns:
            self.session_performance = {}
            return
            
        # Chuyển entry_time thành datetime nếu chưa
        trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
        
        # Tạo một cột mới cho phiên giao dịch
        def get_session(hour):
            if 0 <= hour < 8:
                return 'Asian'
            elif 8 <= hour < 16:
                return 'European'
            else:
                return 'American'
                
        trades_df['session'] = trades_df['entry_time'].dt.hour.apply(get_session)
        
        # Nhóm theo phiên và tính toán metrics
        grouped = trades_df.groupby('session')
        
        sessions = {}
        for session, group in grouped:
            # Tính các metrics cho phiên này
            win_count = len(group[group['profit_loss'] > 0])
            total_count = len(group)
            win_rate = win_count / total_count if total_count > 0 else 0
            
            total_profit = group[group['profit_loss'] > 0]['profit_loss'].sum() if not group[group['profit_loss'] > 0].empty else 0
            total_loss = group[group['profit_loss'] <= 0]['profit_loss'].sum() if not group[group['profit_loss'] <= 0].empty else 0
            net_profit = total_profit + total_loss
            
            avg_profit = group[group['profit_loss'] > 0]['profit_loss'].mean() if not group[group['profit_loss'] > 0].empty else 0
            avg_loss = group[group['profit_loss'] < 0]['profit_loss'].mean() if not group[group['profit_loss'] < 0].empty else 0
            
            payoff_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else float('inf')
            expectancy = (win_rate * avg_profit) + ((1 - win_rate) * avg_loss)
            
            # Lưu metrics cho phiên này
            sessions[session] = {
                'total_trades': total_count,
                'win_count': win_count,
                'loss_count': total_count - win_count,
                'win_rate': win_rate,
                'total_profit': total_profit,
                'total_loss': total_loss,
                'net_profit': net_profit,
                'avg_profit': avg_profit,
                'avg_loss': avg_loss,
                'payoff_ratio': payoff_ratio,
                'expectancy': expectancy
            }
        
        self.session_performance = sessions
    
    def _calculate_drawdown_periods(self) -> None:
        """Tính toán các khoảng drawdown"""
        trades_df = pd.DataFrame(self.trade_history)
        
        # Kiểm tra xem có đủ dữ liệu không
        if 'profit_loss' not in trades_df.columns or 'exit_time' not in trades_df.columns:
            self.drawdown_periods = []
            return
            
        # Sắp xếp theo thời gian
        trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])
        trades_df = trades_df.sort_values('exit_time')
        
        # Tính toán equity curve
        trades_df['cumulative_pnl'] = trades_df['profit_loss'].cumsum()
        
        # Tìm các khoảng drawdown
        drawdown_periods = []
        peak = 0
        drawdown_start = None
        max_drawdown = 0
        current_drawdown = 0
        
        for i, row in trades_df.iterrows():
            if row['cumulative_pnl'] > peak:
                # Nếu có drawdown trước đó, lưu lại
                if drawdown_start is not None and current_drawdown > 0:
                    drawdown_periods.append({
                        'start_time': drawdown_start,
                        'end_time': row['exit_time'],
                        'duration': (row['exit_time'] - drawdown_start).total_seconds() / 86400,  # days
                        'drawdown_amount': current_drawdown,
                        'drawdown_pct': current_drawdown / (peak + current_drawdown) * 100 if peak + current_drawdown > 0 else 0
                    })
                    
                # Cập nhật peak mới
                peak = row['cumulative_pnl']
                drawdown_start = None
                current_drawdown = 0
            else:
                # Bắt đầu drawdown mới hoặc tiếp tục drawdown hiện tại
                if drawdown_start is None:
                    drawdown_start = row['exit_time']
                
                # Cập nhật drawdown
                drawdown = peak - row['cumulative_pnl']
                if drawdown > current_drawdown:
                    current_drawdown = drawdown
                    
                # Cập nhật max drawdown
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        
        # Nếu còn drawdown đang diễn ra
        if drawdown_start is not None and current_drawdown > 0:
            last_time = trades_df['exit_time'].max()
            drawdown_periods.append({
                'start_time': drawdown_start,
                'end_time': last_time,
                'duration': (last_time - drawdown_start).total_seconds() / 86400,  # days
                'drawdown_amount': current_drawdown,
                'drawdown_pct': current_drawdown / (peak + current_drawdown) * 100 if peak + current_drawdown > 0 else 0
            })
        
        self.drawdown_periods = drawdown_periods
    
    def _calculate_max_drawdown(self, trades_df: pd.DataFrame) -> float:
        """
        Tính max drawdown từ DataFrame giao dịch.
        
        Args:
            trades_df (pd.DataFrame): DataFrame chứa thông tin giao dịch
            
        Returns:
            float: Giá trị max drawdown
        """
        if 'profit_loss' not in trades_df.columns:
            return 0
            
        # Sắp xếp theo thời gian nếu có thông tin thời gian
        if 'exit_time' in trades_df.columns:
            trades_df = trades_df.sort_values('exit_time')
            
        # Tính toán equity curve
        cumulative = trades_df['profit_loss'].cumsum()
        
        # Tính max drawdown
        peak = 0
        max_drawdown = 0
        
        for value in cumulative:
            if value > peak:
                peak = value
            else:
                drawdown = peak - value
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                    
        return max_drawdown
    
    def calculate_var_cvar(self, confidence_level: float = 0.95) -> Dict:
        """
        Tính Value at Risk (VaR) và Conditional Value at Risk (CVaR).
        
        Args:
            confidence_level (float): Mức độ tin cậy (0-1)
            
        Returns:
            Dict: Kết quả VaR và CVaR
        """
        trades_df = pd.DataFrame(self.trade_history)
        
        if 'profit_loss_pct' not in trades_df.columns or trades_df.empty:
            return {'var': 0, 'cvar': 0, 'confidence_level': confidence_level}
            
        # Sắp xếp lợi nhuận
        returns = trades_df['profit_loss_pct'].values
        returns.sort()
        
        # Tính VaR
        var_percentile = 1 - confidence_level
        var_index = int(var_percentile * len(returns))
        var = abs(returns[var_index]) if var_index < len(returns) else 0
        
        # Tính CVaR
        cvar_values = returns[:var_index+1]
        cvar = abs(np.mean(cvar_values)) if len(cvar_values) > 0 else 0
        
        return {
            'var': var,
            'cvar': cvar,
            'confidence_level': confidence_level
        }
    
    def calculate_expectancy_by_setup(self, setup_field: str = 'setup_type') -> Dict:
        """
        Tính Expectancy theo loại setup giao dịch.
        
        Args:
            setup_field (str): Tên trường chứa thông tin setup
            
        Returns:
            Dict: Kết quả Expectancy theo setup
        """
        trades_df = pd.DataFrame(self.trade_history)
        
        if setup_field not in trades_df.columns or trades_df.empty:
            return {}
            
        # Nhóm theo setup
        grouped = trades_df.groupby(setup_field)
        
        setups = {}
        for setup, group in grouped:
            # Bỏ qua nếu không có setup hợp lệ
            if pd.isna(setup) or setup == "":
                continue
                
            # Tính các metrics cho setup này
            win_count = len(group[group['profit_loss'] > 0])
            total_count = len(group)
            win_rate = win_count / total_count if total_count > 0 else 0
            
            avg_profit = group[group['profit_loss'] > 0]['profit_loss'].mean() if not group[group['profit_loss'] > 0].empty else 0
            avg_loss = group[group['profit_loss'] < 0]['profit_loss'].mean() if not group[group['profit_loss'] < 0].empty else 0
            
            payoff_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else float('inf')
            expectancy = (win_rate * avg_profit) + ((1 - win_rate) * avg_loss)
            expectancy_r = (win_rate * payoff_ratio) - (1 - win_rate) if avg_loss != 0 else 0
            
            # Lưu metrics cho setup này
            setups[setup] = {
                'total_trades': total_count,
                'win_count': win_count,
                'loss_count': total_count - win_count,
                'win_rate': win_rate,
                'avg_profit': avg_profit,
                'avg_loss': avg_loss,
                'payoff_ratio': payoff_ratio,
                'expectancy': expectancy,
                'expectancy_r': expectancy_r
            }
        
        return setups
    
    def get_edge_statistics(self) -> Dict:
        """
        Lấy thống kê edge của chiến lược giao dịch.
        
        Returns:
            Dict: Thống kê edge
        """
        # Edge được định nghĩa là lợi thế thống kê của chiến lược
        # Bao gồm: win rate, payoff ratio, và expectancy
        
        if not self.metrics:
            return {}
            
        edge_stats = {
            'win_rate': self.metrics['win_rate'],
            'payoff_ratio': self.metrics['payoff_ratio'],
            'expectancy': self.metrics['expectancy'],
            'expectancy_r': self.metrics['expectancy_r'],
            'profit_factor': self.metrics['profit_factor'],
            'sharpe_ratio': self.metrics['sharpe_ratio'],
            'market_regime_edge': self._calculate_market_regime_edge(),
            'symbol_edge': self._calculate_symbol_edge(),
            'timeframe_edge': self._calculate_timeframe_edge(),
            'session_edge': self._calculate_session_edge()
        }
        
        return edge_stats
    
    def _calculate_market_regime_edge(self) -> Dict:
        """
        Tính edge theo chế độ thị trường.
        
        Returns:
            Dict: Edge theo chế độ thị trường
        """
        result = {}
        
        for regime, metrics in self.market_regime_performance.items():
            if metrics['total_trades'] >= 10:  # Chỉ xét các chế độ có đủ dữ liệu
                edge = metrics['win_rate'] * metrics['payoff_ratio'] - (1 - metrics['win_rate'])
                result[regime] = {
                    'edge': edge,
                    'win_rate': metrics['win_rate'],
                    'payoff_ratio': metrics['payoff_ratio'],
                    'total_trades': metrics['total_trades']
                }
                
        return result
    
    def _calculate_symbol_edge(self) -> Dict:
        """
        Tính edge theo symbol.
        
        Returns:
            Dict: Edge theo symbol
        """
        result = {}
        
        for symbol, metrics in self.symbol_performance.items():
            if metrics['total_trades'] >= 10:  # Chỉ xét các symbol có đủ dữ liệu
                edge = metrics['win_rate'] * metrics['payoff_ratio'] - (1 - metrics['win_rate'])
                result[symbol] = {
                    'edge': edge,
                    'win_rate': metrics['win_rate'],
                    'payoff_ratio': metrics['payoff_ratio'],
                    'total_trades': metrics['total_trades']
                }
                
        return result
    
    def _calculate_timeframe_edge(self) -> Dict:
        """
        Tính edge theo khung thời gian.
        
        Returns:
            Dict: Edge theo khung thời gian
        """
        result = {}
        
        for timeframe, metrics in self.timeframe_performance.items():
            if metrics['total_trades'] >= 10:  # Chỉ xét các timeframe có đủ dữ liệu
                edge = metrics['win_rate'] * metrics['payoff_ratio'] - (1 - metrics['win_rate'])
                result[timeframe] = {
                    'edge': edge,
                    'win_rate': metrics['win_rate'],
                    'payoff_ratio': metrics['payoff_ratio'],
                    'total_trades': metrics['total_trades']
                }
                
        return result
    
    def _calculate_session_edge(self) -> Dict:
        """
        Tính edge theo phiên giao dịch.
        
        Returns:
            Dict: Edge theo phiên giao dịch
        """
        result = {}
        
        for session, metrics in self.session_performance.items():
            if metrics['total_trades'] >= 10:  # Chỉ xét các phiên có đủ dữ liệu
                edge = metrics['win_rate'] * metrics['payoff_ratio'] - (1 - metrics['win_rate'])
                result[session] = {
                    'edge': edge,
                    'win_rate': metrics['win_rate'],
                    'payoff_ratio': metrics['payoff_ratio'],
                    'total_trades': metrics['total_trades']
                }
                
        return result
    
    def get_performance_summary(self) -> Dict:
        """
        Lấy tóm tắt hiệu suất giao dịch.
        
        Returns:
            Dict: Tóm tắt hiệu suất
        """
        # Sử dụng các metrics đã tính toán
        if not self.metrics:
            return {}
            
        # Thêm thống kê edge
        edge_stats = self.get_edge_statistics()
        
        # Thêm thống kê VaR và CVaR
        risk_stats = self.calculate_var_cvar()
        
        # Tạo tóm tắt
        summary = {
            'overall_metrics': self.metrics,
            'edge_statistics': edge_stats,
            'risk_statistics': risk_stats,
            'market_regime_performance': self.market_regime_performance,
            'symbol_performance': self.symbol_performance,
            'timeframe_performance': self.timeframe_performance,
            'session_performance': self.session_performance,
            'drawdown_periods': self.drawdown_periods
        }
        
        return summary
    
    def generate_equity_curve_chart(self, cumulative_only: bool = False) -> str:
        """
        Tạo biểu đồ equity curve.
        
        Args:
            cumulative_only (bool): Chỉ hiển thị đồ thị tích lũy
            
        Returns:
            str: Biểu đồ dạng base64
        """
        trades_df = pd.DataFrame(self.trade_history)
        
        if 'profit_loss' not in trades_df.columns or 'exit_time' not in trades_df.columns:
            return ""
            
        # Chuyển exit_time thành datetime
        trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])
        
        # Sắp xếp theo thời gian
        trades_df = trades_df.sort_values('exit_time')
        
        # Tính toán equity curve
        trades_df['cumulative_pnl'] = trades_df['profit_loss'].cumsum()
        
        # Tạo biểu đồ
        plt.figure(figsize=(10, 6))
        
        # Vẽ đường equity curve
        plt.plot(trades_df['exit_time'], trades_df['cumulative_pnl'], 'b-', label='Equity Curve')
        
        # Vẽ biểu đồ individual trade nếu được yêu cầu
        if not cumulative_only:
            # Tìm trades dương và âm
            positive_trades = trades_df[trades_df['profit_loss'] > 0]
            negative_trades = trades_df[trades_df['profit_loss'] <= 0]
            
            # Vẽ các điểm thắng/thua
            plt.scatter(positive_trades['exit_time'], positive_trades['cumulative_pnl'], 
                      color='green', alpha=0.7, label='Winning Trades')
            plt.scatter(negative_trades['exit_time'], negative_trades['cumulative_pnl'], 
                      color='red', alpha=0.7, label='Losing Trades')
        
        # Tùy chỉnh biểu đồ
        plt.title('Equity Curve')
        plt.xlabel('Time')
        plt.ylabel('Cumulative P&L')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Định dạng trục thời gian
        plt.gcf().autofmt_xdate()
        date_format = mdates.DateFormatter('%Y-%m-%d')
        plt.gca().xaxis.set_major_formatter(date_format)
        
        # Chuyển đổi thành base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        plt.close()
        buffer.seek(0)
        img_str = base64.b64encode(buffer.read()).decode('utf-8')
        
        return f"data:image/png;base64,{img_str}"
    
    def generate_drawdown_chart(self) -> str:
        """
        Tạo biểu đồ drawdown theo thời gian.
        
        Returns:
            str: Biểu đồ dạng base64
        """
        trades_df = pd.DataFrame(self.trade_history)
        
        if 'profit_loss' not in trades_df.columns or 'exit_time' not in trades_df.columns:
            return ""
            
        # Chuyển exit_time thành datetime
        trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])
        
        # Sắp xếp theo thời gian
        trades_df = trades_df.sort_values('exit_time')
        
        # Tính toán equity curve và drawdown
        trades_df['cumulative_pnl'] = trades_df['profit_loss'].cumsum()
        trades_df['peak'] = trades_df['cumulative_pnl'].cummax()
        trades_df['drawdown'] = trades_df['peak'] - trades_df['cumulative_pnl']
        trades_df['drawdown_pct'] = trades_df['drawdown'] / trades_df['peak'].replace(0, 1) * 100
        
        # Tạo biểu đồ
        plt.figure(figsize=(10, 6))
        
        # Vẽ đường drawdown
        plt.fill_between(trades_df['exit_time'], 0, -trades_df['drawdown_pct'], color='red', alpha=0.3)
        plt.plot(trades_df['exit_time'], -trades_df['drawdown_pct'], 'r-', label='Drawdown %')
        
        # Tùy chỉnh biểu đồ
        plt.title('Drawdown Over Time')
        plt.xlabel('Time')
        plt.ylabel('Drawdown (%)')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Định dạng trục thời gian
        plt.gcf().autofmt_xdate()
        date_format = mdates.DateFormatter('%Y-%m-%d')
        plt.gca().xaxis.set_major_formatter(date_format)
        
        # Chuyển đổi thành base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        plt.close()
        buffer.seek(0)
        img_str = base64.b64encode(buffer.read()).decode('utf-8')
        
        return f"data:image/png;base64,{img_str}"
    
    def generate_market_regime_performance_chart(self) -> str:
        """
        Tạo biểu đồ hiệu suất theo chế độ thị trường.
        
        Returns:
            str: Biểu đồ dạng base64
        """
        if not self.market_regime_performance:
            return ""
            
        # Chuẩn bị dữ liệu
        regimes = list(self.market_regime_performance.keys())
        win_rates = [self.market_regime_performance[r]['win_rate'] * 100 for r in regimes]
        expectancies = [self.market_regime_performance[r]['expectancy'] for r in regimes]
        trade_counts = [self.market_regime_performance[r]['total_trades'] for r in regimes]
        
        # Tạo biểu đồ
        fig, ax1 = plt.subplots(figsize=(10, 6))
        
        # Vẽ cột win rate
        bar_width = 0.35
        x = np.arange(len(regimes))
        bars1 = ax1.bar(x - bar_width/2, win_rates, bar_width, color='skyblue', label='Win Rate (%)')
        ax1.set_ylabel('Win Rate (%)')
        ax1.set_ylim(0, 100)
        
        # Tạo trục thứ hai cho expectancy
        ax2 = ax1.twinx()
        bars2 = ax2.bar(x + bar_width/2, expectancies, bar_width, color='lightgreen', label='Expectancy ($)')
        ax2.set_ylabel('Expectancy ($)')
        
        # Thêm số lượng giao dịch
        for i, count in enumerate(trade_counts):
            plt.annotate(f"n={count}", xy=(x[i], 5), ha='center')
        
        # Tùy chỉnh biểu đồ
        ax1.set_title('Performance by Market Regime')
        ax1.set_xticks(x)
        ax1.set_xticklabels(regimes, rotation=45, ha='right')
        ax1.grid(True, alpha=0.3, axis='y')
        
        # Kết hợp legends
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.tight_layout()
        
        # Chuyển đổi thành base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        plt.close()
        buffer.seek(0)
        img_str = base64.b64encode(buffer.read()).decode('utf-8')
        
        return f"data:image/png;base64,{img_str}"
    
    def save_performance_report(self, file_path: str = 'performance_report.json') -> bool:
        """
        Lưu báo cáo hiệu suất vào file.
        
        Args:
            file_path (str): Đường dẫn đến file
            
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        try:
            # Lấy tóm tắt hiệu suất
            report = self.get_performance_summary()
            
            # Chuyển đổi datetime thành string
            report_serializable = self._make_json_serializable(report)
            
            # Lưu vào file
            with open(file_path, 'w') as f:
                json.dump(report_serializable, f, indent=2)
                
            logger.info(f"Performance report saved to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving performance report: {e}")
            return False
    
    def _make_json_serializable(self, obj):
        """Chuyển đổi object để có thể serialize thành JSON"""
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(v) for v in obj]
        elif isinstance(obj, (datetime, pd.Timestamp)):
            return obj.isoformat()
        elif isinstance(obj, (np.int64, np.float64)):
            return float(obj)
        elif np.isnan(obj) if isinstance(obj, float) else False:
            return None
        elif np.isinf(obj) if isinstance(obj, float) else False:
            return "Infinity" if obj > 0 else "-Infinity"
        else:
            return obj


class OrderBookHeatmapGenerator:
    """Lớp tạo biểu đồ Order Book Heat Map"""
    
    def __init__(self, levels: int = 100):
        """
        Khởi tạo Order Book Heat Map Generator.
        
        Args:
            levels (int): Số lượng level giá để hiển thị
        """
        self.levels = levels
        self.data_history = []
        self.data_max_size = 100  # Số lượng snapshot tối đa để lưu
    
    def add_orderbook_snapshot(self, bids: List[List[float]], asks: List[List[float]], 
                           timestamp: datetime = None) -> None:
        """
        Thêm một snapshot của order book.
        
        Args:
            bids (List[List[float]]): Danh sách các bid [price, quantity]
            asks (List[List[float]]): Danh sách các ask [price, quantity]
            timestamp (datetime, optional): Thời gian snapshot
        """
        # Sử dụng thời gian hiện tại nếu không cung cấp
        if timestamp is None:
            timestamp = datetime.now()
            
        # Chuyển đổi thành DataFrame
        bid_df = pd.DataFrame(bids, columns=['price', 'quantity']).sort_values('price', ascending=False)
        ask_df = pd.DataFrame(asks, columns=['price', 'quantity']).sort_values('price')
        
        # Giới hạn số lượng level
        bid_df = bid_df.head(self.levels)
        ask_df = ask_df.head(self.levels)
        
        # Lưu snapshot
        self.data_history.append({
            'timestamp': timestamp,
            'bids': bid_df,
            'asks': ask_df
        })
        
        # Giới hạn kích thước lịch sử
        if len(self.data_history) > self.data_max_size:
            self.data_history = self.data_history[-self.data_max_size:]
            
        logger.info(f"Added orderbook snapshot at {timestamp}")
    
    def generate_heatmap(self, time_window: int = None, 
                      normalize: bool = True, log_scale: bool = True) -> str:
        """
        Tạo biểu đồ heat map từ dữ liệu order book.
        
        Args:
            time_window (int, optional): Số snapshot gần nhất để sử dụng
            normalize (bool): Chuẩn hóa dữ liệu
            log_scale (bool): Sử dụng thang logarit
            
        Returns:
            str: Biểu đồ dạng base64
        """
        if not self.data_history:
            return ""
            
        # Xác định cửa sổ thời gian
        if time_window is None or time_window > len(self.data_history):
            time_window = len(self.data_history)
            
        # Lấy các snapshot trong cửa sổ thời gian
        recent_data = self.data_history[-time_window:]
        
        # Tổng hợp dữ liệu
        price_levels = set()
        for data in recent_data:
            price_levels.update(data['bids']['price'])
            price_levels.update(data['asks']['price'])
            
        price_levels = sorted(price_levels)
        
        # Tạo ma trận dữ liệu
        num_levels = len(price_levels)
        num_snapshots = len(recent_data)
        
        # Tạo từ điển ánh xạ giá -> index
        price_to_index = {price: i for i, price in enumerate(price_levels)}
        
        # Khởi tạo ma trận
        matrix = np.zeros((num_levels, num_snapshots))
        
        # Điền dữ liệu vào ma trận
        for j, data in enumerate(recent_data):
            # Điền dữ liệu bid
            for _, row in data['bids'].iterrows():
                price, quantity = row['price'], row['quantity']
                if price in price_to_index:
                    matrix[price_to_index[price], j] = quantity
                    
            # Điền dữ liệu ask (dùng giá trị âm để phân biệt)
            for _, row in data['asks'].iterrows():
                price, quantity = row['price'], row['quantity']
                if price in price_to_index:
                    matrix[price_to_index[price], j] = -quantity
        
        # Chuẩn hóa dữ liệu nếu cần
        if normalize:
            max_abs = np.max(np.abs(matrix))
            if max_abs > 0:
                matrix = matrix / max_abs
                
        # Sử dụng thang logarit nếu cần
        if log_scale:
            # Tạo ma trận dấu
            sign_matrix = np.sign(matrix)
            # Lấy logarit của giá trị tuyệt đối, xử lý giá trị 0
            log_matrix = np.log1p(np.abs(matrix))
            # Áp dụng dấu trở lại
            matrix = sign_matrix * log_matrix
        
        # Tạo biểu đồ
        plt.figure(figsize=(12, 8))
        
        # Tạo một colormap tùy chỉnh với đỏ cho ask, xanh lá cho bid, trắng cho không có dữ liệu
        cmap = plt.cm.RdYlGn
        
        # Vẽ heatmap
        plt.imshow(matrix, aspect='auto', cmap=cmap, interpolation='none')
        
        # Thêm colorbar
        plt.colorbar(label='Volume' + (' (normalized, log scale)' if normalize and log_scale else 
                                       ' (normalized)' if normalize else
                                       ' (log scale)' if log_scale else ''))
        
        # Tùy chỉnh trục
        step = max(1, num_levels // 10)  # Hiển thị tối đa 10 mức giá
        plt.yticks(np.arange(0, num_levels, step), [f"{price_levels[i]:.2f}" for i in range(0, num_levels, step)])
        plt.ylabel('Price Levels')
        
        # Tùy chỉnh trục thời gian
        step_t = max(1, num_snapshots // 8)  # Hiển thị tối đa 8 mốc thời gian
        timestamps = [data['timestamp'] for data in recent_data]
        plt.xticks(np.arange(0, num_snapshots, step_t), 
                 [t.strftime('%H:%M:%S') for t in timestamps[::step_t]], rotation=45)
        plt.xlabel('Time')
        
        plt.title('Order Book Heatmap (Green: Bids, Red: Asks)')
        plt.tight_layout()
        
        # Chuyển đổi thành base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        plt.close()
        buffer.seek(0)
        img_str = base64.b64encode(buffer.read()).decode('utf-8')
        
        return f"data:image/png;base64,{img_str}"
    
    def generate_volume_profile(self) -> str:
        """
        Tạo biểu đồ volume profile từ dữ liệu order book.
        
        Returns:
            str: Biểu đồ dạng base64
        """
        if not self.data_history:
            return ""
            
        # Lấy snapshot mới nhất
        latest_data = self.data_history[-1]
        
        # Tạo biểu đồ
        plt.figure(figsize=(10, 8))
        
        # Vẽ bid volume (bên phải)
        bid_prices = latest_data['bids']['price'].values
        bid_quantities = latest_data['bids']['quantity'].values
        plt.barh(bid_prices, bid_quantities, height=bid_prices.min() * 0.001, color='green', alpha=0.5, label='Bids')
        
        # Vẽ ask volume (bên trái)
        ask_prices = latest_data['asks']['price'].values
        ask_quantities = latest_data['asks']['quantity'].values
        plt.barh(ask_prices, -ask_quantities, height=ask_prices.min() * 0.001, color='red', alpha=0.5, label='Asks')
        
        # Tính giá trung bình và đánh dấu
        mid_price = (bid_prices.max() + ask_prices.min()) / 2
        plt.axhline(y=mid_price, color='blue', linestyle='-', alpha=0.3, label='Mid Price')
        
        # Tùy chỉnh biểu đồ
        plt.title('Order Book Volume Profile')
        plt.xlabel('Volume')
        plt.ylabel('Price')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Đảo ngược trục y để giá cao ở trên
        plt.gca().invert_yaxis()
        
        # Chuyển đổi thành base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        plt.close()
        buffer.seek(0)
        img_str = base64.b64encode(buffer.read()).decode('utf-8')
        
        return f"data:image/png;base64,{img_str}"


class EnhancedReportGenerator:
    """Lớp tạo báo cáo nâng cao tổng hợp"""
    
    def __init__(self, performance_analyzer: PerformanceAnalyzer = None,
              orderbook_generator: OrderBookHeatmapGenerator = None):
        """
        Khởi tạo Enhanced Report Generator.
        
        Args:
            performance_analyzer (PerformanceAnalyzer, optional): Đối tượng phân tích hiệu suất
            orderbook_generator (OrderBookHeatmapGenerator, optional): Đối tượng tạo heat map
        """
        self.performance_analyzer = performance_analyzer or PerformanceAnalyzer()
        self.orderbook_generator = orderbook_generator or OrderBookHeatmapGenerator()
        
        # Thư mục lưu báo cáo
        self.reports_dir = 'reports'
        self.charts_dir = os.path.join(self.reports_dir, 'charts')
        
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(self.charts_dir, exist_ok=True)
    
    def generate_html_report(self, include_charts: bool = True) -> str:
        """
        Tạo báo cáo HTML đầy đủ.
        
        Args:
            include_charts (bool): Có bao gồm các biểu đồ không
            
        Returns:
            str: Nội dung HTML
        """
        # Lấy dữ liệu hiệu suất
        performance_data = self.performance_analyzer.get_performance_summary()
        
        # Tạo biểu đồ nếu cần
        charts = {}
        if include_charts:
            charts['equity_curve'] = self.performance_analyzer.generate_equity_curve_chart()
            charts['drawdown'] = self.performance_analyzer.generate_drawdown_chart()
            charts['market_regime'] = self.performance_analyzer.generate_market_regime_performance_chart()
            
            if self.orderbook_generator.data_history:
                charts['orderbook_heatmap'] = self.orderbook_generator.generate_heatmap()
                charts['volume_profile'] = self.orderbook_generator.generate_volume_profile()
        
        # Tạo HTML
        html = self._create_html_report(performance_data, charts)
        
        return html
    
    def _create_html_report(self, data: Dict, charts: Dict) -> str:
        """
        Tạo nội dung HTML từ dữ liệu.
        
        Args:
            data (Dict): Dữ liệu hiệu suất
            charts (Dict): Các biểu đồ
            
        Returns:
            str: Nội dung HTML
        """
        # Đảm bảo có dữ liệu
        if not data:
            return "<html><body><h1>No data available</h1></body></html>"
            
        # Định dạng số
        def fmt(value):
            if isinstance(value, float):
                return f"{value:.2f}"
            return str(value)
            
        # Định dạng phần trăm
        def fmt_pct(value):
            if isinstance(value, float):
                return f"{value*100:.2f}%"
            return str(value)
        
        # Tạo HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Enhanced Trading Performance Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ background-color: #343a40; color: white; padding: 20px; margin-bottom: 20px; }}
                .section {{ margin-bottom: 30px; border: 1px solid #ddd; padding: 20px; border-radius: 5px; }}
                .flex-container {{ display: flex; flex-wrap: wrap; }}
                .flex-item {{ flex: 1; min-width: 300px; margin: 10px; }}
                .metric-card {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 10px; }}
                .metric-value {{ font-size: 24px; font-weight: bold; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
                .neutral {{ color: gray; }}
                table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                .chart {{ width: 100%; margin: 20px 0; }}
                .chart img {{ max-width: 100%; height: auto; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Enhanced Trading Performance Report</h1>
                    <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
        """
        
        # 1. Metrics tổng thể
        if 'overall_metrics' in data:
            metrics = data['overall_metrics']
            html += f"""
                <div class="section">
                    <h2>Overall Performance</h2>
                    <div class="flex-container">
                        <div class="flex-item">
                            <div class="metric-card">
                                <h3>Win Rate</h3>
                                <div class="metric-value">{fmt_pct(metrics.get('win_rate', 0))}</div>
                                <p>{metrics.get('win_count', 0)} wins out of {metrics.get('total_trades', 0)} trades</p>
                            </div>
                        </div>
                        <div class="flex-item">
                            <div class="metric-card">
                                <h3>Net Profit</h3>
                                <div class="metric-value {('positive' if metrics.get('net_profit', 0) > 0 else 'negative')}">
                                    ${fmt(metrics.get('net_profit', 0))}
                                </div>
                                <p>Profit: ${fmt(metrics.get('total_profit', 0))}, Loss: ${fmt(metrics.get('total_loss', 0))}</p>
                            </div>
                        </div>
                        <div class="flex-item">
                            <div class="metric-card">
                                <h3>Expectancy</h3>
                                <div class="metric-value {('positive' if metrics.get('expectancy', 0) > 0 else 'negative')}">
                                    ${fmt(metrics.get('expectancy', 0))}
                                </div>
                                <p>Expected profit per trade</p>
                            </div>
                        </div>
                    </div>
                    <div class="flex-container">
                        <div class="flex-item">
                            <div class="metric-card">
                                <h3>Payoff Ratio</h3>
                                <div class="metric-value">{fmt(metrics.get('payoff_ratio', 0))}</div>
                                <p>Avg Win: ${fmt(metrics.get('avg_profit', 0))}, Avg Loss: ${fmt(abs(metrics.get('avg_loss', 0)))}</p>
                            </div>
                        </div>
                        <div class="flex-item">
                            <div class="metric-card">
                                <h3>Profit Factor</h3>
                                <div class="metric-value">{fmt(metrics.get('profit_factor', 0))}</div>
                                <p>Gross Profit / Gross Loss</p>
                            </div>
                        </div>
                        <div class="flex-item">
                            <div class="metric-card">
                                <h3>Max Drawdown</h3>
                                <div class="metric-value negative">${fmt(metrics.get('max_drawdown', 0))}</div>
                                <p>Recovery Factor: {fmt(metrics.get('recovery_factor', 0))}</p>
                            </div>
                        </div>
                    </div>
            """
            
            # Biểu đồ Equity Curve
            if 'equity_curve' in charts:
                html += f"""
                    <div class="chart">
                        <h3>Equity Curve</h3>
                        <img src="{charts['equity_curve']}" alt="Equity Curve" />
                    </div>
                """
                
            # Biểu đồ Drawdown
            if 'drawdown' in charts:
                html += f"""
                    <div class="chart">
                        <h3>Drawdown</h3>
                        <img src="{charts['drawdown']}" alt="Drawdown" />
                    </div>
                """
                
            html += "</div>"  # End of Overall Performance section
        
        # 2. Phân tích theo chế độ thị trường
        if 'market_regime_performance' in data and data['market_regime_performance']:
            html += f"""
                <div class="section">
                    <h2>Performance by Market Regime</h2>
            """
            
            if 'market_regime' in charts:
                html += f"""
                    <div class="chart">
                        <img src="{charts['market_regime']}" alt="Market Regime Performance" />
                    </div>
                """
                
            html += f"""
                    <table>
                        <tr>
                            <th>Market Regime</th>
                            <th>Trades</th>
                            <th>Win Rate</th>
                            <th>Net Profit</th>
                            <th>Expectancy</th>
                            <th>Payoff Ratio</th>
                        </tr>
            """
            
            for regime, metrics in data['market_regime_performance'].items():
                html += f"""
                        <tr>
                            <td>{regime}</td>
                            <td>{metrics.get('total_trades', 0)}</td>
                            <td>{fmt_pct(metrics.get('win_rate', 0))}</td>
                            <td class="{('positive' if metrics.get('net_profit', 0) > 0 else 'negative')}">${fmt(metrics.get('net_profit', 0))}</td>
                            <td class="{('positive' if metrics.get('expectancy', 0) > 0 else 'negative')}">${fmt(metrics.get('expectancy', 0))}</td>
                            <td>{fmt(metrics.get('payoff_ratio', 0))}</td>
                        </tr>
                """
                
            html += """
                    </table>
                </div>
            """
        
        # 3. Thống kê Edge
        if 'edge_statistics' in data and data['edge_statistics']:
            edge_stats = data['edge_statistics']
            html += f"""
                <div class="section">
                    <h2>Edge Statistics</h2>
                    <div class="flex-container">
                        <div class="flex-item">
                            <div class="metric-card">
                                <h3>Overall Edge</h3>
                                <div class="metric-value {('positive' if edge_stats.get('expectancy_r', 0) > 0 else 'negative')}">
                                    {fmt(edge_stats.get('expectancy_r', 0))}
                                </div>
                                <p>Win Rate: {fmt_pct(edge_stats.get('win_rate', 0))}, Payoff Ratio: {fmt(edge_stats.get('payoff_ratio', 0))}</p>
                            </div>
                        </div>
                        <div class="flex-item">
                            <div class="metric-card">
                                <h3>Sharpe Ratio</h3>
                                <div class="metric-value">
                                    {fmt(edge_stats.get('sharpe_ratio', 0))}
                                </div>
                                <p>Higher is better, > 1 is good</p>
                            </div>
                        </div>
                        <div class="flex-item">
                            <div class="metric-card">
                                <h3>Profit Factor</h3>
                                <div class="metric-value">
                                    {fmt(edge_stats.get('profit_factor', 0))}
                                </div>
                                <p>Higher is better, > 1.5 is good</p>
                            </div>
                        </div>
                    </div>
            """
            
            # Market Regime Edge
            if 'market_regime_edge' in edge_stats and edge_stats['market_regime_edge']:
                html += f"""
                    <h3>Edge by Market Regime</h3>
                    <table>
                        <tr>
                            <th>Market Regime</th>
                            <th>Edge</th>
                            <th>Win Rate</th>
                            <th>Payoff Ratio</th>
                            <th>Trades</th>
                        </tr>
                """
                
                for regime, metrics in edge_stats['market_regime_edge'].items():
                    html += f"""
                        <tr>
                            <td>{regime}</td>
                            <td class="{('positive' if metrics.get('edge', 0) > 0 else 'negative')}">{fmt(metrics.get('edge', 0))}</td>
                            <td>{fmt_pct(metrics.get('win_rate', 0))}</td>
                            <td>{fmt(metrics.get('payoff_ratio', 0))}</td>
                            <td>{metrics.get('total_trades', 0)}</td>
                        </tr>
                    """
                    
                html += "</table>"
            
            html += "</div>"  # End of Edge Statistics section
        
        # 4. Thống kê rủi ro
        if 'risk_statistics' in data and data['risk_statistics']:
            risk_stats = data['risk_statistics']
            html += f"""
                <div class="section">
                    <h2>Risk Analysis</h2>
                    <div class="flex-container">
                        <div class="flex-item">
                            <div class="metric-card">
                                <h3>Value at Risk (VaR)</h3>
                                <div class="metric-value negative">
                                    {fmt_pct(risk_stats.get('var', 0))}
                                </div>
                                <p>Maximum expected loss at {int(risk_stats.get('confidence_level', 0.95)*100)}% confidence</p>
                            </div>
                        </div>
                        <div class="flex-item">
                            <div class="metric-card">
                                <h3>Conditional VaR (CVaR)</h3>
                                <div class="metric-value negative">
                                    {fmt_pct(risk_stats.get('cvar', 0))}
                                </div>
                                <p>Expected loss when exceeding VaR</p>
                            </div>
                        </div>
                    </div>
            """
            
            # Drawdown periods
            if 'drawdown_periods' in data and data['drawdown_periods']:
                html += f"""
                    <h3>Significant Drawdown Periods</h3>
                    <table>
                        <tr>
                            <th>Start Date</th>
                            <th>End Date</th>
                            <th>Duration (days)</th>
                            <th>Drawdown Amount</th>
                            <th>Drawdown %</th>
                        </tr>
                """
                
                for period in data['drawdown_periods']:
                    if period['drawdown_pct'] > 5:  # Only show significant drawdowns
                        html += f"""
                            <tr>
                                <td>{period['start_time'].strftime('%Y-%m-%d') if isinstance(period['start_time'], datetime) else period['start_time']}</td>
                                <td>{period['end_time'].strftime('%Y-%m-%d') if isinstance(period['end_time'], datetime) else period['end_time']}</td>
                                <td>{fmt(period['duration'])}</td>
                                <td class="negative">${fmt(period['drawdown_amount'])}</td>
                                <td class="negative">{fmt_pct(period['drawdown_pct']/100)}</td>
                            </tr>
                        """
                        
                html += "</table>"
            
            html += "</div>"  # End of Risk Analysis section
        
        # 5. Order Book Analysis
        if 'orderbook_heatmap' in charts or 'volume_profile' in charts:
            html += f"""
                <div class="section">
                    <h2>Order Book Analysis</h2>
            """
            
            if 'orderbook_heatmap' in charts:
                html += f"""
                    <div class="chart">
                        <h3>Order Book Heatmap</h3>
                        <img src="{charts['orderbook_heatmap']}" alt="Order Book Heatmap" />
                    </div>
                """
                
            if 'volume_profile' in charts:
                html += f"""
                    <div class="chart">
                        <h3>Volume Profile</h3>
                        <img src="{charts['volume_profile']}" alt="Volume Profile" />
                    </div>
                """
                
            html += "</div>"  # End of Order Book Analysis section
        
        # Kết thúc HTML
        html += """
            </div>
        </body>
        </html>
        """
        
        return html
    
    def save_html_report(self, file_path: str = None) -> str:
        """
        Tạo và lưu báo cáo HTML.
        
        Args:
            file_path (str, optional): Đường dẫn đến file
            
        Returns:
            str: Đường dẫn đến file đã lưu
        """
        # Tạo báo cáo
        html = self.generate_html_report()
        
        # Xác định đường dẫn file
        if file_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = os.path.join(self.reports_dir, f'performance_report_{timestamp}.html')
            
        # Lưu báo cáo
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html)
            
        logger.info(f"HTML report saved to {file_path}")
        return file_path
    
    def generate_pdf_report(self, file_path: str = None) -> str:
        """
        Tạo và lưu báo cáo PDF.
        
        Args:
            file_path (str, optional): Đường dẫn đến file
            
        Returns:
            str: Đường dẫn đến file đã lưu
        """
        # Xác định đường dẫn file
        if file_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = os.path.join(self.reports_dir, f'performance_report_{timestamp}.pdf')
            
        # Đầu tiên tạo và lưu báo cáo HTML
        html_path = file_path.replace('.pdf', '.html')
        self.save_html_report(html_path)
        
        # Convert HTML to PDF (cần thư viện weasyprint hoặc pdfkit)
        try:
            # Thử sử dụng pdfkit trước
            import pdfkit
            pdfkit.from_file(html_path, file_path)
            logger.info(f"PDF report saved to {file_path}")
            return file_path
        except ImportError:
            try:
                # Thử sử dụng weasyprint
                from weasyprint import HTML
                HTML(html_path).write_pdf(file_path)
                logger.info(f"PDF report saved to {file_path}")
                return file_path
            except ImportError:
                logger.warning("Could not convert to PDF. Install pdfkit or weasyprint.")
                return html_path
    
    def generate_json_report(self, file_path: str = None) -> str:
        """
        Tạo và lưu báo cáo JSON.
        
        Args:
            file_path (str, optional): Đường dẫn đến file
            
        Returns:
            str: Đường dẫn đến file đã lưu
        """
        # Xác định đường dẫn file
        if file_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = os.path.join(self.reports_dir, f'performance_report_{timestamp}.json')
            
        # Lưu báo cáo
        if self.performance_analyzer:
            self.performance_analyzer.save_performance_report(file_path)
            
        return file_path
    
    def send_report_email(self, to_email: str, subject: str = None, 
                        report_type: str = 'html') -> bool:
        """
        Gửi báo cáo qua email.
        
        Args:
            to_email (str): Địa chỉ email nhận
            subject (str, optional): Tiêu đề email
            report_type (str): Loại báo cáo ('html', 'pdf', 'json')
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        # Kiểm tra xem đã cài đặt thư viện email chưa
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            from email.mime.application import MIMEApplication
        except ImportError:
            logger.error("Could not import email libraries")
            return False
            
        # Lấy cấu hình SMTP từ biến môi trường
        smtp_server = os.environ.get('SMTP_SERVER')
        smtp_port = os.environ.get('SMTP_PORT')
        smtp_user = os.environ.get('SMTP_USER')
        smtp_password = os.environ.get('SMTP_PASSWORD')
        from_email = os.environ.get('FROM_EMAIL', smtp_user)
        
        if not all([smtp_server, smtp_port, smtp_user, smtp_password]):
            logger.error("Missing SMTP configuration")
            return False
            
        # Tạo báo cáo
        if report_type == 'html':
            report_path = self.save_html_report()
            report_content = open(report_path, 'r', encoding='utf-8').read()
            mime_type = 'html'
        elif report_type == 'pdf':
            report_path = self.generate_pdf_report()
            mime_type = 'application/pdf'
        elif report_type == 'json':
            report_path = self.generate_json_report()
            mime_type = 'application/json'
        else:
            logger.error(f"Unsupported report type: {report_type}")
            return False
            
        # Tạo email
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject or f"Trading Performance Report - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Thêm nội dung
        if report_type == 'html':
            msg.attach(MIMEText(report_content, mime_type))
        else:
            # Thêm text mặc định
            msg.attach(MIMEText(f"Please find attached your trading performance report. Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 'plain'))
            
            # Thêm file đính kèm
            with open(report_path, 'rb') as f:
                attachment = MIMEApplication(f.read(), _subtype=mime_type.split('/')[-1])
                attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(report_path))
                msg.attach(attachment)
        
        # Gửi email
        try:
            server = smtplib.SMTP(smtp_server, int(smtp_port))
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Report sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False


def main():
    """Hàm chính để demo"""
    # Tạo dữ liệu mẫu
    trade_history = []
    seed = 42
    np.random.seed(seed)
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    market_regimes = ['Bullish', 'Bearish', 'Sideways']
    timeframes = ['1h', '4h', '1d']
    
    # Thời gian bắt đầu (3 tháng trước)
    start_time = datetime.now() - timedelta(days=90)
    
    # Tạo 100 giao dịch mẫu
    for i in range(100):
        # Thời gian
        entry_time = start_time + timedelta(hours=i*8)
        holding_hours = np.random.randint(4, 48)
        exit_time = entry_time + timedelta(hours=holding_hours)
        
        # Symbol
        symbol = np.random.choice(symbols)
        
        # Chế độ thị trường
        market_regime = np.random.choice(market_regimes)
        
        # Timeframe
        timeframe = np.random.choice(timeframes)
        
        # Giá và số lượng
        base_price = 40000 if symbol == 'BTCUSDT' else 2500 if symbol == 'ETHUSDT' else 100
        price_noise = np.random.normal(0, base_price * 0.02)
        entry_price = base_price + price_noise
        
        # Số lượng
        quantity = np.random.uniform(0.1, 1.0) if symbol == 'BTCUSDT' else \
                 np.random.uniform(1.0, 5.0) if symbol == 'ETHUSDT' else \
                 np.random.uniform(10.0, 50.0)
        
        # Thắng/thua và P&L
        # Tăng tỷ lệ thắng cho chế độ Bullish, giảm cho Bearish
        win_prob = 0.6
        if market_regime == 'Bullish':
            win_prob = 0.7
        elif market_regime == 'Bearish':
            win_prob = 0.4
            
        is_win = np.random.random() < win_prob
        
        # P&L (phần trăm)
        if is_win:
            pnl_pct = np.random.uniform(1.0, 5.0) / 100
        else:
            pnl_pct = -np.random.uniform(1.0, 3.0) / 100
            
        # P&L (giá trị)
        pnl = entry_price * quantity * pnl_pct
        
        # Tạo giao dịch
        trade = {
            'id': f"trade_{i+1}",
            'symbol': symbol,
            'entry_time': entry_time,
            'exit_time': exit_time,
            'entry_price': entry_price,
            'exit_price': entry_price * (1 + pnl_pct),
            'quantity': quantity,
            'side': 'LONG' if np.random.random() < 0.7 else 'SHORT',
            'profit_loss': pnl,
            'profit_loss_pct': pnl_pct,
            'status': 'win' if is_win else 'loss',
            'market_regime': market_regime,
            'timeframe': timeframe,
            'setup_type': np.random.choice(['Breakout', 'Pullback', 'Reversal']),
            'initial_risk': entry_price * quantity * 0.02  # Giả định rủi ro 2%
        }
        
        trade_history.append(trade)
    
    # Tạo dữ liệu order book mẫu
    bids = []
    asks = []
    
    base_price = 40000  # Giả sử BTC
    
    # Tạo 50 mức giá cho bid
    for i in range(50):
        price = base_price * (1 - (i+1) * 0.001)
        quantity = np.random.uniform(0.5, 5.0) * (1 + (50-i)/50)
        bids.append([price, quantity])
    
    # Tạo 50 mức giá cho ask
    for i in range(50):
        price = base_price * (1 + (i+1) * 0.001)
        quantity = np.random.uniform(0.5, 5.0) * (1 + (50-i)/50)
        asks.append([price, quantity])
    
    # 1. Khởi tạo Performance Analyzer
    performance_analyzer = PerformanceAnalyzer(trade_history)
    
    # 2. Khởi tạo OrderBook Heatmap Generator
    orderbook_generator = OrderBookHeatmapGenerator()
    
    # Thêm 10 snapshot order book
    for i in range(10):
        # Tạo một chút biến động cho mỗi snapshot
        noise_factor = 1 + np.random.normal(0, 0.05)
        
        # Thêm noise cho bid/ask
        noisy_bids = [[price, quantity * noise_factor] for price, quantity in bids]
        noisy_asks = [[price, quantity * noise_factor] for price, quantity in asks]
        
        # Thêm snapshot
        orderbook_generator.add_orderbook_snapshot(
            noisy_bids, 
            noisy_asks, 
            timestamp=datetime.now() - timedelta(minutes=10*(9-i))
        )
    
    # 3. Khởi tạo Report Generator
    report_generator = EnhancedReportGenerator(performance_analyzer, orderbook_generator)
    
    # 4. Tạo báo cáo HTML
    html_path = report_generator.save_html_report('enhanced_report_demo.html')
    print(f"HTML report saved to {html_path}")
    
    # 5. Tạo báo cáo JSON
    json_path = report_generator.generate_json_report('enhanced_report_demo.json')
    print(f"JSON report saved to {json_path}")
    
    # 6. Những metrics hữu ích khác
    print("\nOverall Metrics:")
    print(f"Win Rate: {performance_analyzer.metrics['win_rate']*100:.2f}%")
    print(f"Expectancy: ${performance_analyzer.metrics['expectancy']:.2f}")
    print(f"Profit Factor: {performance_analyzer.metrics['profit_factor']:.2f}")
    
    print("\nMarket Regime Performance:")
    for regime, data in performance_analyzer.market_regime_performance.items():
        print(f"{regime}: Win Rate: {data['win_rate']*100:.2f}%, Net Profit: ${data['net_profit']:.2f}")
    
    print("\nEdge Statistics:")
    edge_stats = performance_analyzer.get_edge_statistics()
    print(f"Overall Edge: {edge_stats['expectancy_r']:.2f}")
    
    # Hiển thị kết quả VaR/CVaR
    var_cvar = performance_analyzer.calculate_var_cvar()
    print(f"\nRisk Analysis:")
    print(f"Value at Risk (95%): {var_cvar['var']*100:.2f}%")
    print(f"Conditional VaR (95%): {var_cvar['cvar']*100:.2f}%")

if __name__ == "__main__":
    main()