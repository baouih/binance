#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module Giám Sát Hiệu Suất (Performance Monitor)

Module này cung cấp các công cụ giám sát và phân tích hiệu suất giao dịch,
tạo báo cáo, cảnh báo, và đề xuất điều chỉnh chiến lược dựa trên kết quả.
"""

import logging
import json
import time
import datetime
import os
import math
import copy
import re
from typing import Dict, List, Tuple, Any, Optional, Union
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('performance_monitor')


class PerformanceMonitor:
    """Lớp giám sát và phân tích hiệu suất giao dịch"""
    
    def __init__(self, config_path: str = 'configs/performance_monitor_config.json',
                binance_api = None, pnl_calculator = None):
        """
        Khởi tạo Performance Monitor
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
            binance_api: Đối tượng BinanceAPI để lấy dữ liệu
            pnl_calculator: Đối tượng PnLCalculator để tính toán lợi nhuận
        """
        self.config = self._load_config(config_path)
        self.binance_api = binance_api
        self.pnl_calculator = pnl_calculator
        
        # Tạo các thư mục cần thiết
        os.makedirs('reports', exist_ok=True)
        os.makedirs('reports/daily', exist_ok=True)
        os.makedirs('reports/weekly', exist_ok=True)
        os.makedirs('reports/monthly', exist_ok=True)
        os.makedirs('reports/strategy', exist_ok=True)
        
        # Khởi tạo cache dữ liệu
        self.position_cache = {}
        self.trade_history = []
        self.metrics_history = {}
        self.alerts = []
        
        # Tải dữ liệu nếu có
        self._load_data()
        
        logger.info("Đã khởi tạo Performance Monitor")
    
    def _load_config(self, config_path: str) -> Dict:
        """
        Tải cấu hình từ file hoặc sử dụng cấu hình mặc định
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
            
        Returns:
            Dict: Cấu hình đã tải
        """
        default_config = {
            'tracking': {
                'track_trades': True,
                'track_pnl': True,
                'track_balance': True,
                'track_drawdown': True,
                'track_win_rate': True,
                'track_strategies': True,
                'track_symbols': True
            },
            'reporting': {
                'daily_reports': True,
                'weekly_reports': True,
                'monthly_reports': True,
                'strategy_reports': True,
                'symbol_reports': True,
                'include_charts': True,
                'email_reports': False,
                'telegram_reports': False
            },
            'alerts': {
                'drawdown_threshold': 10,  # %
                'losing_streak_threshold': 5,  # số lượng thua liên tiếp
                'profit_target_alert': 5,  # % lợi nhuận mục tiêu hằng ngày
                'low_win_rate_threshold': 40,  # % tỷ lệ thắng thấp cần cảnh báo
                'balance_drop_threshold': 5,  # % giảm số dư cần cảnh báo
                'high_exposure_threshold': 50  # % tài khoản trong vị thế
            },
            'metrics': {
                'rr_ratio_min': 1.5,  # Tỷ lệ R/R tối thiểu mong muốn
                'win_rate_min': 45,  # % tỷ lệ thắng tối thiểu mong muốn
                'profit_factor_min': 1.2,  # Hệ số lợi nhuận tối thiểu
                'max_drawdown_acceptable': 20,  # % drawdown tối đa chấp nhận được
                'target_monthly_return': 10,  # % lợi nhuận hàng tháng mục tiêu
                'expected_trades_per_day': 3  # Số giao dịch dự kiến mỗi ngày
            },
            'strategies': {
                'track_individual_performance': True,
                'auto_adjust_weights': True,
                'min_trades_for_evaluation': 20
            },
            'data_retention': {
                'trade_history_max_days': 365,  # Số ngày lưu trữ lịch sử giao dịch
                'metrics_history_max_days': 730  # Số ngày lưu trữ chỉ số hiệu suất
            },
            'visualization': {
                'chart_style': 'seaborn',
                'chart_colors': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'],
                'equity_chart_interval': 'daily'  # 'hourly', 'daily', 'weekly'
            }
        }
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {config_path}")
                return config
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning(f"Không thể tải cấu hình từ {config_path}, sử dụng cấu hình mặc định")
            # Lưu cấu hình mặc định
            try:
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=4)
                logger.info(f"Đã lưu cấu hình mặc định vào {config_path}")
            except Exception as e:
                logger.error(f"Không thể lưu cấu hình mặc định: {str(e)}")
            
            return default_config
    
    def _load_data(self) -> None:
        """Tải dữ liệu từ các file lưu trữ"""
        # Tải lịch sử giao dịch
        try:
            with open('data/trade_history.json', 'r') as f:
                self.trade_history = json.load(f)
            logger.info(f"Đã tải lịch sử giao dịch: {len(self.trade_history)} giao dịch")
        except (FileNotFoundError, json.JSONDecodeError):
            logger.info("Không tìm thấy hoặc không thể tải lịch sử giao dịch")
        
        # Tải lịch sử chỉ số
        try:
            with open('data/metrics_history.json', 'r') as f:
                self.metrics_history = json.load(f)
            logger.info(f"Đã tải lịch sử chỉ số hiệu suất")
        except (FileNotFoundError, json.JSONDecodeError):
            logger.info("Không tìm thấy hoặc không thể tải lịch sử chỉ số hiệu suất")
        
        # Tải lịch sử cảnh báo
        try:
            with open('data/performance_alerts.json', 'r') as f:
                self.alerts = json.load(f)
            logger.info(f"Đã tải lịch sử cảnh báo: {len(self.alerts)} cảnh báo")
        except (FileNotFoundError, json.JSONDecodeError):
            logger.info("Không tìm thấy hoặc không thể tải lịch sử cảnh báo")
    
    def _save_data(self) -> None:
        """Lưu dữ liệu vào các file lưu trữ"""
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs('data', exist_ok=True)
        
        # Lưu lịch sử giao dịch
        try:
            with open('data/trade_history.json', 'w') as f:
                json.dump(self.trade_history, f, indent=4)
            logger.debug("Đã lưu lịch sử giao dịch")
        except Exception as e:
            logger.error(f"Không thể lưu lịch sử giao dịch: {str(e)}")
        
        # Lưu lịch sử chỉ số
        try:
            with open('data/metrics_history.json', 'w') as f:
                json.dump(self.metrics_history, f, indent=4)
            logger.debug("Đã lưu lịch sử chỉ số hiệu suất")
        except Exception as e:
            logger.error(f"Không thể lưu lịch sử chỉ số hiệu suất: {str(e)}")
        
        # Lưu lịch sử cảnh báo
        try:
            with open('data/performance_alerts.json', 'w') as f:
                json.dump(self.alerts, f, indent=4)
            logger.debug("Đã lưu lịch sử cảnh báo")
        except Exception as e:
            logger.error(f"Không thể lưu lịch sử cảnh báo: {str(e)}")
    
    def record_trade(self, trade_data: Dict) -> str:
        """
        Ghi nhận giao dịch mới
        
        Args:
            trade_data (Dict): Dữ liệu giao dịch
                {
                    'symbol': str,
                    'side': str,
                    'entry_time': int,
                    'exit_time': int,
                    'entry_price': float,
                    'exit_price': float,
                    'position_size': float,
                    'pnl': float,
                    'roi': float,
                    'strategy': str,
                    'leverage': float,
                    'fees': float,
                    'stop_loss': float,
                    'take_profit': float,
                    'reason': str,
                    'tags': List[str],
                    'notes': str
                }
            
        Returns:
            str: ID của giao dịch
        """
        # Kiểm tra dữ liệu đầu vào tối thiểu
        required_fields = ['symbol', 'side', 'entry_price', 'exit_price']
        for field in required_fields:
            if field not in trade_data:
                logger.error(f"Thiếu trường dữ liệu {field} khi ghi nhận giao dịch")
                return ""
        
        # Tạo ID giao dịch
        trade_id = f"trade_{int(time.time())}_{trade_data['symbol']}_{len(self.trade_history)}"
        
        # Thêm các trường bổ sung
        trade_data['trade_id'] = trade_id
        trade_data['record_time'] = int(time.time())
        
        if 'entry_time' not in trade_data:
            trade_data['entry_time'] = int(time.time()) - 3600  # Mặc định 1 giờ trước
        
        if 'exit_time' not in trade_data:
            trade_data['exit_time'] = int(time.time())
        
        # Tính PnL nếu chưa có
        if 'pnl' not in trade_data and self.pnl_calculator:
            try:
                result = self.pnl_calculator.calculate_pnl_with_full_details(
                    entry_price=trade_data['entry_price'],
                    exit_price=trade_data['exit_price'],
                    position_size=trade_data.get('position_size', 1.0),
                    leverage=trade_data.get('leverage', 1.0),
                    position_side=trade_data['side'],
                    symbol=trade_data['symbol'],
                    entry_time=trade_data['entry_time'],
                    exit_time=trade_data['exit_time']
                )
                
                trade_data['pnl'] = result['net_pnl']
                trade_data['roi'] = result['roi_percent']
                trade_data['fees'] = result['total_fee']
                
                if 'funding_pnl' in result:
                    trade_data['funding_pnl'] = result['funding_pnl']
                
            except Exception as e:
                logger.error(f"Lỗi khi tính PnL cho giao dịch: {str(e)}")
                # Tính toán đơn giản nếu không dùng được PnL Calculator
                if trade_data['side'].upper() == 'LONG':
                    trade_data['pnl'] = (trade_data['exit_price'] - trade_data['entry_price']) * trade_data.get('position_size', 1.0)
                else:
                    trade_data['pnl'] = (trade_data['entry_price'] - trade_data['exit_price']) * trade_data.get('position_size', 1.0)
                
                # Tính ROI
                trade_data['roi'] = (trade_data['pnl'] / (trade_data['entry_price'] * trade_data.get('position_size', 1.0))) * 100
        
        # Thêm giao dịch vào lịch sử
        self.trade_history.append(trade_data)
        
        # Lưu dữ liệu
        self._save_data()
        
        # Cập nhật chỉ số và kiểm tra cảnh báo
        self.update_metrics()
        self.check_alerts()
        
        logger.info(f"Đã ghi nhận giao dịch mới: {trade_id}, PnL: {trade_data.get('pnl', 0):.2f}, ROI: {trade_data.get('roi', 0):.2f}%")
        
        return trade_id
    
    def record_position_update(self, position_data: Dict) -> str:
        """
        Ghi nhận cập nhật vị thế (theo dõi vị thế đang mở)
        
        Args:
            position_data (Dict): Dữ liệu vị thế
                {
                    'symbol': str,
                    'side': str,
                    'entry_time': int,
                    'entry_price': float,
                    'current_price': float,
                    'position_size': float,
                    'leverage': float,
                    'unrealized_pnl': float,
                    'unrealized_roi': float,
                    'strategy': str,
                    'stop_loss': float,
                    'take_profit': float
                }
            
        Returns:
            str: ID của vị thế
        """
        # Kiểm tra dữ liệu đầu vào tối thiểu
        required_fields = ['symbol', 'side', 'entry_price', 'current_price']
        for field in required_fields:
            if field not in position_data:
                logger.error(f"Thiếu trường dữ liệu {field} khi ghi nhận vị thế")
                return ""
        
        # Tạo ID vị thế
        position_id = f"{position_data['symbol']}_{position_data['side']}"
        
        # Thêm các trường bổ sung
        position_data['position_id'] = position_id
        position_data['update_time'] = int(time.time())
        
        if 'entry_time' not in position_data:
            position_data['entry_time'] = int(time.time()) - 3600  # Mặc định 1 giờ trước
        
        # Tính unrealized PnL nếu chưa có
        if 'unrealized_pnl' not in position_data:
            side = position_data['side'].upper()
            entry_price = position_data['entry_price']
            current_price = position_data['current_price']
            position_size = position_data.get('position_size', 1.0)
            leverage = position_data.get('leverage', 1.0)
            
            if side == 'LONG':
                unrealized_pnl = (current_price - entry_price) * position_size * leverage
            else:
                unrealized_pnl = (entry_price - current_price) * position_size * leverage
            
            position_data['unrealized_pnl'] = unrealized_pnl
            
            # Tính unrealized ROI
            margin = (entry_price * position_size) / leverage
            position_data['unrealized_roi'] = (unrealized_pnl / margin) * 100
        
        # Cập nhật vị thế trong cache
        self.position_cache[position_id] = position_data
        
        logger.debug(f"Đã cập nhật vị thế: {position_id}, Unrealized PnL: {position_data.get('unrealized_pnl', 0):.2f}")
        
        return position_id
    
    def update_metrics(self) -> Dict:
        """
        Cập nhật và tính toán các chỉ số hiệu suất
        
        Returns:
            Dict: Các chỉ số hiệu suất hiện tại
        """
        # Nếu không có giao dịch, trả về chỉ số mặc định
        if not self.trade_history:
            metrics = self._get_default_metrics()
            self.metrics_history[str(int(time.time()))] = metrics
            return metrics
        
        # Lấy giao dịch trong 24 giờ qua
        now = int(time.time())
        one_day_ago = now - 86400
        one_week_ago = now - 604800
        one_month_ago = now - 2592000
        
        daily_trades = [t for t in self.trade_history if t.get('exit_time', 0) > one_day_ago]
        weekly_trades = [t for t in self.trade_history if t.get('exit_time', 0) > one_week_ago]
        monthly_trades = [t for t in self.trade_history if t.get('exit_time', 0) > one_month_ago]
        
        # Tính toán chỉ số tổng thể
        all_trades = self.trade_history
        all_metrics = self._calculate_metrics(all_trades)
        
        # Tính toán chỉ số theo thời gian
        daily_metrics = self._calculate_metrics(daily_trades)
        weekly_metrics = self._calculate_metrics(weekly_trades)
        monthly_metrics = self._calculate_metrics(monthly_trades)
        
        # Tính toán chỉ số theo chiến lược
        strategy_metrics = self._calculate_strategy_metrics(all_trades)
        
        # Tính toán chỉ số theo cặp tiền
        symbol_metrics = self._calculate_symbol_metrics(all_trades)
        
        # Tổng hợp tất cả chỉ số
        metrics = {
            'timestamp': now,
            'overall': all_metrics,
            'daily': daily_metrics,
            'weekly': weekly_metrics,
            'monthly': monthly_metrics,
            'strategies': strategy_metrics,
            'symbols': symbol_metrics
        }
        
        # Lưu vào lịch sử
        self.metrics_history[str(now)] = metrics
        
        # Lưu dữ liệu
        self._save_data()
        
        return metrics
    
    def _get_default_metrics(self) -> Dict:
        """
        Tạo chỉ số mặc định khi chưa có giao dịch
        
        Returns:
            Dict: Chỉ số mặc định
        """
        default_metrics = {
            'total_trades': 0,
            'win_trades': 0,
            'loss_trades': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'total_pnl': 0,
            'avg_pnl': 0,
            'largest_win': 0,
            'largest_loss': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'avg_trade': 0,
            'max_drawdown': 0,
            'max_drawdown_percent': 0,
            'avg_trade_duration': 0,
            'trading_expectancy': 0,
            'sharpe_ratio': 0,
            'trades_per_day': 0,
            'consecutive_wins': 0,
            'consecutive_losses': 0,
            'win_loss_ratio': 0,
            'rr_ratio': 0
        }
        
        return default_metrics
    
    def _calculate_metrics(self, trades: List[Dict]) -> Dict:
        """
        Tính toán các chỉ số hiệu suất từ danh sách giao dịch
        
        Args:
            trades (List[Dict]): Danh sách giao dịch
            
        Returns:
            Dict: Các chỉ số hiệu suất
        """
        # Nếu không có giao dịch, trả về chỉ số mặc định
        if not trades:
            return self._get_default_metrics()
        
        # Tính toán các chỉ số cơ bản
        total_trades = len(trades)
        winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in trades if t.get('pnl', 0) <= 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        
        win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0
        
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
        
        # Tính các chỉ số thắng/thua
        largest_win = max([t.get('pnl', 0) for t in winning_trades]) if winning_trades else 0
        largest_loss = min([t.get('pnl', 0) for t in losing_trades]) if losing_trades else 0
        
        avg_win = sum(t.get('pnl', 0) for t in winning_trades) / win_count if win_count > 0 else 0
        avg_loss = sum(t.get('pnl', 0) for t in losing_trades) / loss_count if loss_count > 0 else 0
        
        # Tính Profit Factor
        gross_profit = sum(t.get('pnl', 0) for t in winning_trades)
        gross_loss = abs(sum(t.get('pnl', 0) for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0 if gross_profit == 0 else float('inf')
        
        # Tính thời gian giao dịch trung bình
        durations = []
        for trade in trades:
            entry_time = trade.get('entry_time', 0)
            exit_time = trade.get('exit_time', 0)
            if entry_time > 0 and exit_time > entry_time:
                durations.append(exit_time - entry_time)
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Tính Drawdown
        max_drawdown, max_dd_percent = self._calculate_drawdown(trades)
        
        # Tính số giao dịch trung bình mỗi ngày
        if durations:
            total_trading_seconds = sum(durations)
            total_trading_days = total_trading_seconds / 86400  # seconds in a day
            trades_per_day = total_trades / total_trading_days if total_trading_days > 0 else 0
        else:
            # Nếu không có thông tin thời gian, giả định mỗi giao dịch là 1 ngày
            trades_per_day = total_trades / total_trades if total_trades > 0 else 0
        
        # Tính Trading Expectancy
        expectancy = (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss)
        
        # Tính Sharpe Ratio (đơn giản hóa)
        pnl_values = [t.get('pnl', 0) for t in trades]
        avg_return = sum(pnl_values) / len(pnl_values) if pnl_values else 0
        std_dev = np.std(pnl_values) if len(pnl_values) > 1 else 1
        sharpe_ratio = avg_return / std_dev if std_dev > 0 else 0
        
        # Tính số lần thắng/thua liên tiếp
        consecutive_wins, consecutive_losses = self._calculate_streaks(trades)
        
        # Tính tỷ lệ thắng/thua
        win_loss_ratio = win_count / loss_count if loss_count > 0 else float('inf') if win_count > 0 else 0
        
        # Tính tỷ lệ R/R
        rr_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf') if avg_win > 0 else 0
        
        # Tổng hợp các chỉ số
        metrics = {
            'total_trades': total_trades,
            'win_trades': win_count,
            'loss_trades': loss_count,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_trade': avg_pnl,
            'max_drawdown': max_drawdown,
            'max_drawdown_percent': max_dd_percent,
            'avg_trade_duration': avg_duration,
            'avg_trade_duration_hours': avg_duration / 3600 if avg_duration > 0 else 0,
            'trading_expectancy': expectancy,
            'sharpe_ratio': sharpe_ratio,
            'trades_per_day': trades_per_day,
            'consecutive_wins': consecutive_wins,
            'consecutive_losses': consecutive_losses,
            'win_loss_ratio': win_loss_ratio,
            'rr_ratio': rr_ratio
        }
        
        return metrics
    
    def _calculate_drawdown(self, trades: List[Dict]) -> Tuple[float, float]:
        """
        Tính toán drawdown tối đa
        
        Args:
            trades (List[Dict]): Danh sách giao dịch
            
        Returns:
            Tuple[float, float]: (max_drawdown, max_drawdown_percent)
        """
        # Tạo chuỗi thời gian của equity
        # Sắp xếp giao dịch theo thời gian
        sorted_trades = sorted(trades, key=lambda x: x.get('exit_time', 0))
        
        # Giả sử ban đầu có 10000 (hoặc dùng số dư ban đầu nếu có)
        initial_balance = 10000
        current_balance = initial_balance
        peak_balance = initial_balance
        max_drawdown = 0
        max_dd_percent = 0
        
        for trade in sorted_trades:
            pnl = trade.get('pnl', 0)
            current_balance += pnl
            
            # Cập nhật peak balance
            if current_balance > peak_balance:
                peak_balance = current_balance
            
            # Tính drawdown hiện tại
            current_drawdown = peak_balance - current_balance
            current_dd_percent = (current_drawdown / peak_balance) * 100 if peak_balance > 0 else 0
            
            # Cập nhật max drawdown
            if current_drawdown > max_drawdown:
                max_drawdown = current_drawdown
                max_dd_percent = current_dd_percent
        
        return max_drawdown, max_dd_percent
    
    def _calculate_streaks(self, trades: List[Dict]) -> Tuple[int, int]:
        """
        Tính toán số lần thắng/thua liên tiếp
        
        Args:
            trades (List[Dict]): Danh sách giao dịch
            
        Returns:
            Tuple[int, int]: (max_win_streak, max_loss_streak)
        """
        # Sắp xếp giao dịch theo thời gian
        sorted_trades = sorted(trades, key=lambda x: x.get('exit_time', 0))
        
        current_win_streak = 0
        current_loss_streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        
        for trade in sorted_trades:
            pnl = trade.get('pnl', 0)
            
            if pnl > 0:
                # Thắng
                current_win_streak += 1
                current_loss_streak = 0
                if current_win_streak > max_win_streak:
                    max_win_streak = current_win_streak
            else:
                # Thua
                current_loss_streak += 1
                current_win_streak = 0
                if current_loss_streak > max_loss_streak:
                    max_loss_streak = current_loss_streak
        
        return max_win_streak, max_loss_streak
    
    def _calculate_strategy_metrics(self, trades: List[Dict]) -> Dict:
        """
        Tính toán chỉ số hiệu suất theo chiến lược
        
        Args:
            trades (List[Dict]): Danh sách giao dịch
            
        Returns:
            Dict: Chỉ số hiệu suất theo chiến lược
        """
        # Nhóm các giao dịch theo chiến lược
        strategies = {}
        
        for trade in trades:
            strategy = trade.get('strategy', 'unknown')
            if strategy not in strategies:
                strategies[strategy] = []
            
            strategies[strategy].append(trade)
        
        # Tính toán chỉ số cho từng chiến lược
        strategy_metrics = {}
        
        for strategy, strategy_trades in strategies.items():
            strategy_metrics[strategy] = self._calculate_metrics(strategy_trades)
            strategy_metrics[strategy]['trade_count'] = len(strategy_trades)
            strategy_metrics[strategy]['percentage_of_total'] = (len(strategy_trades) / len(trades)) * 100 if trades else 0
        
        return strategy_metrics
    
    def _calculate_symbol_metrics(self, trades: List[Dict]) -> Dict:
        """
        Tính toán chỉ số hiệu suất theo cặp tiền
        
        Args:
            trades (List[Dict]): Danh sách giao dịch
            
        Returns:
            Dict: Chỉ số hiệu suất theo cặp tiền
        """
        # Nhóm các giao dịch theo cặp tiền
        symbols = {}
        
        for trade in trades:
            symbol = trade.get('symbol', 'unknown')
            if symbol not in symbols:
                symbols[symbol] = []
            
            symbols[symbol].append(trade)
        
        # Tính toán chỉ số cho từng cặp tiền
        symbol_metrics = {}
        
        for symbol, symbol_trades in symbols.items():
            symbol_metrics[symbol] = self._calculate_metrics(symbol_trades)
            symbol_metrics[symbol]['trade_count'] = len(symbol_trades)
            symbol_metrics[symbol]['percentage_of_total'] = (len(symbol_trades) / len(trades)) * 100 if trades else 0
        
        return symbol_metrics
    
    def check_alerts(self) -> List[Dict]:
        """
        Kiểm tra và tạo cảnh báo dựa trên các ngưỡng đã cấu hình
        
        Returns:
            List[Dict]: Danh sách cảnh báo mới
        """
        # Lấy chỉ số hiệu suất mới nhất
        metrics = self.get_latest_metrics()
        
        if not metrics:
            return []
        
        # Lấy cấu hình cảnh báo
        alert_config = self.config.get('alerts', {})
        
        # Danh sách cảnh báo mới
        new_alerts = []
        
        # Kiểm tra drawdown
        drawdown_threshold = alert_config.get('drawdown_threshold', 10)
        max_drawdown_percent = metrics.get('overall', {}).get('max_drawdown_percent', 0)
        
        if max_drawdown_percent >= drawdown_threshold:
            alert = {
                'type': 'drawdown',
                'level': 'warning',
                'message': f'Drawdown đạt {max_drawdown_percent:.2f}%, vượt ngưỡng {drawdown_threshold}%',
                'value': max_drawdown_percent,
                'threshold': drawdown_threshold,
                'timestamp': int(time.time())
            }
            new_alerts.append(alert)
        
        # Kiểm tra chuỗi thua liên tiếp
        losing_streak_threshold = alert_config.get('losing_streak_threshold', 5)
        consecutive_losses = metrics.get('overall', {}).get('consecutive_losses', 0)
        
        if consecutive_losses >= losing_streak_threshold:
            alert = {
                'type': 'losing_streak',
                'level': 'warning',
                'message': f'Chuỗi thua liên tiếp đạt {consecutive_losses}, vượt ngưỡng {losing_streak_threshold}',
                'value': consecutive_losses,
                'threshold': losing_streak_threshold,
                'timestamp': int(time.time())
            }
            new_alerts.append(alert)
        
        # Kiểm tra tỷ lệ thắng thấp
        low_win_rate_threshold = alert_config.get('low_win_rate_threshold', 40)
        win_rate = metrics.get('overall', {}).get('win_rate', 0)
        
        if win_rate < low_win_rate_threshold and metrics.get('overall', {}).get('total_trades', 0) >= 10:
            alert = {
                'type': 'low_win_rate',
                'level': 'warning',
                'message': f'Tỷ lệ thắng {win_rate:.2f}%, dưới ngưỡng {low_win_rate_threshold}%',
                'value': win_rate,
                'threshold': low_win_rate_threshold,
                'timestamp': int(time.time())
            }
            new_alerts.append(alert)
        
        # Lưu cảnh báo mới
        if new_alerts:
            self.alerts.extend(new_alerts)
            self._save_data()
        
        return new_alerts
    
    def get_latest_metrics(self) -> Dict:
        """
        Lấy chỉ số hiệu suất mới nhất
        
        Returns:
            Dict: Chỉ số hiệu suất mới nhất
        """
        if not self.metrics_history:
            return {}
        
        latest_timestamp = max(int(ts) for ts in self.metrics_history.keys())
        return self.metrics_history[str(latest_timestamp)]
    
    def create_daily_report(self, date: datetime.date = None) -> str:
        """
        Tạo báo cáo hằng ngày
        
        Args:
            date (datetime.date, optional): Ngày cần tạo báo cáo, mặc định là hôm nay
            
        Returns:
            str: Đường dẫn đến file báo cáo
        """
        # Xác định ngày tạo báo cáo
        if date is None:
            date = datetime.date.today()
        
        date_str = date.strftime('%Y-%m-%d')
        
        # Lấy giao dịch trong ngày
        start_timestamp = int(datetime.datetime.combine(date, datetime.time.min).timestamp())
        end_timestamp = int(datetime.datetime.combine(date, datetime.time.max).timestamp())
        
        daily_trades = [t for t in self.trade_history if start_timestamp <= t.get('exit_time', 0) <= end_timestamp]
        
        # Tính toán chỉ số cho ngày này
        daily_metrics = self._calculate_metrics(daily_trades)
        
        # Tạo báo cáo
        report = {
            'date': date_str,
            'trades': daily_trades,
            'metrics': daily_metrics,
            'strategy_metrics': self._calculate_strategy_metrics(daily_trades),
            'symbol_metrics': self._calculate_symbol_metrics(daily_trades),
            'alerts': [a for a in self.alerts if start_timestamp <= a.get('timestamp', 0) <= end_timestamp]
        }
        
        # Lưu báo cáo
        report_path = f'reports/daily/report_{date_str}.json'
        try:
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=4)
            logger.info(f"Đã tạo báo cáo hằng ngày: {report_path}")
        except Exception as e:
            logger.error(f"Không thể lưu báo cáo hằng ngày: {str(e)}")
            return ""
        
        # Tạo báo cáo HTML nếu cần
        if self.config.get('reporting', {}).get('include_charts', True):
            html_report_path = self._create_html_report(report, 'daily', date_str)
            logger.info(f"Đã tạo báo cáo HTML hằng ngày: {html_report_path}")
        
        return report_path
    
    def create_weekly_report(self, end_date: datetime.date = None) -> str:
        """
        Tạo báo cáo hằng tuần
        
        Args:
            end_date (datetime.date, optional): Ngày cuối tuần, mặc định là hôm nay
            
        Returns:
            str: Đường dẫn đến file báo cáo
        """
        # Xác định tuần cần tạo báo cáo
        if end_date is None:
            end_date = datetime.date.today()
        
        # Tính ngày đầu tuần (thứ Hai)
        start_date = end_date - datetime.timedelta(days=end_date.weekday())
        
        week_str = f"{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}"
        
        # Lấy giao dịch trong tuần
        start_timestamp = int(datetime.datetime.combine(start_date, datetime.time.min).timestamp())
        end_timestamp = int(datetime.datetime.combine(end_date, datetime.time.max).timestamp())
        
        weekly_trades = [t for t in self.trade_history if start_timestamp <= t.get('exit_time', 0) <= end_timestamp]
        
        # Tính toán chỉ số cho tuần này
        weekly_metrics = self._calculate_metrics(weekly_trades)
        
        # Tạo báo cáo
        report = {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'trades': weekly_trades,
            'metrics': weekly_metrics,
            'strategy_metrics': self._calculate_strategy_metrics(weekly_trades),
            'symbol_metrics': self._calculate_symbol_metrics(weekly_trades),
            'alerts': [a for a in self.alerts if start_timestamp <= a.get('timestamp', 0) <= end_timestamp]
        }
        
        # Lưu báo cáo
        report_path = f'reports/weekly/report_week_{week_str}.json'
        try:
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=4)
            logger.info(f"Đã tạo báo cáo hằng tuần: {report_path}")
        except Exception as e:
            logger.error(f"Không thể lưu báo cáo hằng tuần: {str(e)}")
            return ""
        
        # Tạo báo cáo HTML nếu cần
        if self.config.get('reporting', {}).get('include_charts', True):
            html_report_path = self._create_html_report(report, 'weekly', week_str)
            logger.info(f"Đã tạo báo cáo HTML hằng tuần: {html_report_path}")
        
        return report_path
    
    def create_monthly_report(self, year: int = None, month: int = None) -> str:
        """
        Tạo báo cáo hằng tháng
        
        Args:
            year (int, optional): Năm, mặc định là năm hiện tại
            month (int, optional): Tháng, mặc định là tháng hiện tại
            
        Returns:
            str: Đường dẫn đến file báo cáo
        """
        # Xác định tháng cần tạo báo cáo
        today = datetime.date.today()
        if year is None:
            year = today.year
        if month is None:
            month = today.month
        
        # Tính ngày đầu và cuối tháng
        start_date = datetime.date(year, month, 1)
        if month == 12:
            end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
        
        month_str = f"{year}-{month:02d}"
        
        # Lấy giao dịch trong tháng
        start_timestamp = int(datetime.datetime.combine(start_date, datetime.time.min).timestamp())
        end_timestamp = int(datetime.datetime.combine(end_date, datetime.time.max).timestamp())
        
        monthly_trades = [t for t in self.trade_history if start_timestamp <= t.get('exit_time', 0) <= end_timestamp]
        
        # Tính toán chỉ số cho tháng này
        monthly_metrics = self._calculate_metrics(monthly_trades)
        
        # Tạo báo cáo
        report = {
            'year': year,
            'month': month,
            'month_str': month_str,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'trades': monthly_trades,
            'metrics': monthly_metrics,
            'strategy_metrics': self._calculate_strategy_metrics(monthly_trades),
            'symbol_metrics': self._calculate_symbol_metrics(monthly_trades),
            'alerts': [a for a in self.alerts if start_timestamp <= a.get('timestamp', 0) <= end_timestamp]
        }
        
        # Lưu báo cáo
        report_path = f'reports/monthly/report_month_{month_str}.json'
        try:
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=4)
            logger.info(f"Đã tạo báo cáo hằng tháng: {report_path}")
        except Exception as e:
            logger.error(f"Không thể lưu báo cáo hằng tháng: {str(e)}")
            return ""
        
        # Tạo báo cáo HTML nếu cần
        if self.config.get('reporting', {}).get('include_charts', True):
            html_report_path = self._create_html_report(report, 'monthly', month_str)
            logger.info(f"Đã tạo báo cáo HTML hằng tháng: {html_report_path}")
        
        return report_path
    
    def create_strategy_report(self, strategy: str, period: str = 'all') -> str:
        """
        Tạo báo cáo theo chiến lược
        
        Args:
            strategy (str): Tên chiến lược
            period (str): Khoảng thời gian ('all', 'daily', 'weekly', 'monthly')
            
        Returns:
            str: Đường dẫn đến file báo cáo
        """
        # Xác định khoảng thời gian
        now = int(time.time())
        
        if period == 'daily':
            start_timestamp = now - 86400
            period_str = 'daily'
        elif period == 'weekly':
            start_timestamp = now - 604800
            period_str = 'weekly'
        elif period == 'monthly':
            start_timestamp = now - 2592000
            period_str = 'monthly'
        else:
            start_timestamp = 0
            period_str = 'all'
        
        # Lấy giao dịch của chiến lược trong khoảng thời gian
        strategy_trades = [t for t in self.trade_history if t.get('strategy', 'unknown') == strategy and t.get('exit_time', 0) >= start_timestamp]
        
        # Tính toán chỉ số cho chiến lược
        strategy_metrics = self._calculate_metrics(strategy_trades)
        
        # Tính chỉ số theo cặp tiền
        symbol_metrics = self._calculate_symbol_metrics(strategy_trades)
        
        # Tạo báo cáo
        report = {
            'strategy': strategy,
            'period': period_str,
            'trades': strategy_trades,
            'metrics': strategy_metrics,
            'symbol_metrics': symbol_metrics,
            'timestamp': now
        }
        
        # Lưu báo cáo
        report_path = f'reports/strategy/report_{strategy}_{period_str}.json'
        try:
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=4)
            logger.info(f"Đã tạo báo cáo chiến lược: {report_path}")
        except Exception as e:
            logger.error(f"Không thể lưu báo cáo chiến lược: {str(e)}")
            return ""
        
        # Tạo báo cáo HTML nếu cần
        if self.config.get('reporting', {}).get('include_charts', True):
            html_report_path = self._create_html_report(report, 'strategy', f"{strategy}_{period_str}")
            logger.info(f"Đã tạo báo cáo HTML chiến lược: {html_report_path}")
        
        return report_path
    
    def _create_html_report(self, report_data: Dict, report_type: str, report_id: str) -> str:
        """
        Tạo báo cáo HTML từ dữ liệu báo cáo
        
        Args:
            report_data (Dict): Dữ liệu báo cáo
            report_type (str): Loại báo cáo ('daily', 'weekly', 'monthly', 'strategy')
            report_id (str): Định danh báo cáo
            
        Returns:
            str: Đường dẫn đến file báo cáo HTML
        """
        # Tạo thư mục nếu chưa tồn tại
        report_dir = f'reports/{report_type}'
        os.makedirs(report_dir, exist_ok=True)
        
        html_path = f'{report_dir}/report_{report_id}.html'
        
        # Tạo nội dung HTML
        html_content = self._generate_html_report(report_data, report_type)
        
        # Lưu file HTML
        try:
            with open(html_path, 'w') as f:
                f.write(html_content)
            return html_path
        except Exception as e:
            logger.error(f"Không thể lưu báo cáo HTML: {str(e)}")
            return ""
    
    def _generate_html_report(self, report_data: Dict, report_type: str) -> str:
        """
        Tạo nội dung HTML cho báo cáo
        
        Args:
            report_data (Dict): Dữ liệu báo cáo
            report_type (str): Loại báo cáo
            
        Returns:
            str: Nội dung HTML
        """
        # Tạo tiêu đề báo cáo
        if report_type == 'daily':
            title = f"Báo Cáo Giao Dịch Ngày {report_data.get('date', '')}"
            period_desc = f"Ngày {report_data.get('date', '')}"
        elif report_type == 'weekly':
            title = f"Báo Cáo Giao Dịch Tuần {report_data.get('start_date', '')} đến {report_data.get('end_date', '')}"
            period_desc = f"Tuần từ {report_data.get('start_date', '')} đến {report_data.get('end_date', '')}"
        elif report_type == 'monthly':
            title = f"Báo Cáo Giao Dịch Tháng {report_data.get('month_str', '')}"
            period_desc = f"Tháng {report_data.get('month_str', '')}"
        elif report_type == 'strategy':
            title = f"Báo Cáo Chiến Lược {report_data.get('strategy', '')}"
            period_desc = f"Giai đoạn: {report_data.get('period', 'all')}"
        else:
            title = "Báo Cáo Giao Dịch"
            period_desc = "Tất cả giai đoạn"
        
        # Lấy dữ liệu chỉ số
        metrics = report_data.get('metrics', {})
        
        # Tạo bảng tóm tắt
        summary_table = self._generate_metrics_table(metrics)
        
        # Tạo bảng chiến lược
        strategy_metrics = report_data.get('strategy_metrics', {})
        strategy_table = self._generate_strategy_table(strategy_metrics)
        
        # Tạo bảng cặp tiền
        symbol_metrics = report_data.get('symbol_metrics', {})
        symbol_table = self._generate_symbol_table(symbol_metrics)
        
        # Tạo bảng giao dịch
        trades = report_data.get('trades', [])
        trades_table = self._generate_trades_table(trades)
        
        # Tạo bảng cảnh báo
        alerts = report_data.get('alerts', [])
        alerts_table = self._generate_alerts_table(alerts)
        
        # Tạo đồ thị (nếu có dữ liệu)
        # Tạm thời để trống, sẽ cập nhật sau khi có thể tạo đồ thị
        
        # Tạo nội dung HTML
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 20px;
                    color: #333;
                }}
                h1, h2, h3 {{
                    color: #2c3e50;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                    padding-bottom: 20px;
                    border-bottom: 1px solid #eee;
                }}
                .section {{
                    margin-bottom: 30px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 20px;
                }}
                th, td {{
                    padding: 12px 15px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background-color: #f8f9fa;
                    font-weight: bold;
                }}
                tr:hover {{
                    background-color: #f5f5f5;
                }}
                .positive {{
                    color: green;
                }}
                .negative {{
                    color: red;
                }}
                .summary-box {{
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: space-between;
                    margin-bottom: 20px;
                }}
                .metric-card {{
                    background: #f8f9fa;
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 15px;
                    width: calc(33.333% - 20px);
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }}
                .metric-title {{
                    font-size: 14px;
                    color: #666;
                    margin-bottom: 5px;
                }}
                .metric-value {{
                    font-size: 24px;
                    font-weight: bold;
                }}
                .metric-unit {{
                    font-size: 14px;
                    color: #666;
                }}
                .alert {{
                    background-color: #fff3cd;
                    color: #856404;
                    padding: 10px;
                    margin-bottom: 10px;
                    border-radius: 4px;
                }}
                @media (max-width: 768px) {{
                    .metric-card {{
                        width: calc(50% - 15px);
                    }}
                }}
                @media (max-width: 576px) {{
                    .metric-card {{
                        width: 100%;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{title}</h1>
                    <p>Thời gian: {period_desc}</p>
                </div>
                
                <div class="section">
                    <h2>Tóm Tắt Hiệu Suất</h2>
                    <div class="summary-box">
                        <div class="metric-card">
                            <div class="metric-title">Tổng số giao dịch</div>
                            <div class="metric-value">{metrics.get('total_trades', 0)}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-title">Tỷ lệ thắng</div>
                            <div class="metric-value">{metrics.get('win_rate', 0):.2f}<span class="metric-unit">%</span></div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-title">Lợi nhuận</div>
                            <div class="metric-value {'positive' if metrics.get('total_pnl', 0) >= 0 else 'negative'}">{metrics.get('total_pnl', 0):.2f}<span class="metric-unit"> USDT</span></div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-title">Hệ số lợi nhuận (Profit Factor)</div>
                            <div class="metric-value">{metrics.get('profit_factor', 0):.2f}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-title">Tỷ lệ R/R</div>
                            <div class="metric-value">{metrics.get('rr_ratio', 0):.2f}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-title">Drawdown tối đa</div>
                            <div class="metric-value">{metrics.get('max_drawdown_percent', 0):.2f}<span class="metric-unit">%</span></div>
                        </div>
                    </div>
                    
                    {summary_table}
                </div>
                
                <div class="section">
                    <h2>Hiệu Suất Theo Chiến Lược</h2>
                    {strategy_table}
                </div>
                
                <div class="section">
                    <h2>Hiệu Suất Theo Cặp Tiền</h2>
                    {symbol_table}
                </div>
                
                <div class="section">
                    <h2>Danh Sách Giao Dịch</h2>
                    {trades_table}
                </div>
                
                {f'<div class="section"><h2>Cảnh Báo</h2>{alerts_table}</div>' if alerts else ''}
                
                <div class="footer">
                    <p>Báo cáo tạo lúc: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def _generate_metrics_table(self, metrics: Dict) -> str:
        """
        Tạo bảng HTML cho chỉ số hiệu suất
        
        Args:
            metrics (Dict): Chỉ số hiệu suất
            
        Returns:
            str: Bảng HTML
        """
        table_html = """
        <table>
            <tr>
                <th>Chỉ số</th>
                <th>Giá trị</th>
            </tr>
            <tr>
                <td>Tổng số giao dịch</td>
                <td>{}</td>
            </tr>
            <tr>
                <td>Số giao dịch thắng</td>
                <td>{}</td>
            </tr>
            <tr>
                <td>Số giao dịch thua</td>
                <td>{}</td>
            </tr>
            <tr>
                <td>Tỷ lệ thắng</td>
                <td>{:.2f}%</td>
            </tr>
            <tr>
                <td>Tổng lợi nhuận</td>
                <td class="{}">$ {:.2f}</td>
            </tr>
            <tr>
                <td>Lợi nhuận trung bình mỗi giao dịch</td>
                <td class="{}">$ {:.2f}</td>
            </tr>
            <tr>
                <td>Giao dịch thắng lớn nhất</td>
                <td class="positive">$ {:.2f}</td>
            </tr>
            <tr>
                <td>Giao dịch thua lớn nhất</td>
                <td class="negative">$ {:.2f}</td>
            </tr>
            <tr>
                <td>Lợi nhuận trung bình (thắng)</td>
                <td class="positive">$ {:.2f}</td>
            </tr>
            <tr>
                <td>Lỗ trung bình (thua)</td>
                <td class="negative">$ {:.2f}</td>
            </tr>
            <tr>
                <td>Hệ số lợi nhuận (Profit Factor)</td>
                <td>{:.2f}</td>
            </tr>
            <tr>
                <td>Drawdown tối đa</td>
                <td>$ {:.2f} ({:.2f}%)</td>
            </tr>
            <tr>
                <td>Thời gian giao dịch trung bình</td>
                <td>{:.2f} giờ</td>
            </tr>
            <tr>
                <td>Số giao dịch mỗi ngày</td>
                <td>{:.2f}</td>
            </tr>
            <tr>
                <td>Chuỗi thắng liên tiếp lớn nhất</td>
                <td>{}</td>
            </tr>
            <tr>
                <td>Chuỗi thua liên tiếp lớn nhất</td>
                <td>{}</td>
            </tr>
            <tr>
                <td>Tỷ lệ thắng/thua</td>
                <td>{:.2f}</td>
            </tr>
            <tr>
                <td>Tỷ lệ R/R</td>
                <td>{:.2f}</td>
            </tr>
        </table>
        """.format(
            metrics.get('total_trades', 0),
            metrics.get('win_trades', 0),
            metrics.get('loss_trades', 0),
            metrics.get('win_rate', 0),
            'positive' if metrics.get('total_pnl', 0) >= 0 else 'negative',
            metrics.get('total_pnl', 0),
            'positive' if metrics.get('avg_pnl', 0) >= 0 else 'negative',
            metrics.get('avg_pnl', 0),
            metrics.get('largest_win', 0),
            metrics.get('largest_loss', 0),
            metrics.get('avg_win', 0),
            metrics.get('avg_loss', 0),
            metrics.get('profit_factor', 0),
            metrics.get('max_drawdown', 0), metrics.get('max_drawdown_percent', 0),
            metrics.get('avg_trade_duration_hours', 0),
            metrics.get('trades_per_day', 0),
            metrics.get('consecutive_wins', 0),
            metrics.get('consecutive_losses', 0),
            metrics.get('win_loss_ratio', 0),
            metrics.get('rr_ratio', 0)
        )
        
        return table_html
    
    def _generate_strategy_table(self, strategy_metrics: Dict) -> str:
        """
        Tạo bảng HTML cho hiệu suất theo chiến lược
        
        Args:
            strategy_metrics (Dict): Hiệu suất theo chiến lược
            
        Returns:
            str: Bảng HTML
        """
        if not strategy_metrics:
            return "<p>Không có dữ liệu chiến lược</p>"
        
        rows = ""
        for strategy, metrics in strategy_metrics.items():
            rows += f"""
            <tr>
                <td>{strategy}</td>
                <td>{metrics.get('trade_count', 0)}</td>
                <td>{metrics.get('win_rate', 0):.2f}%</td>
                <td class="{'positive' if metrics.get('total_pnl', 0) >= 0 else 'negative'}">$ {metrics.get('total_pnl', 0):.2f}</td>
                <td>{metrics.get('profit_factor', 0):.2f}</td>
                <td>{metrics.get('percentage_of_total', 0):.2f}%</td>
            </tr>
            """
        
        table_html = f"""
        <table>
            <tr>
                <th>Chiến lược</th>
                <th>Số giao dịch</th>
                <th>Tỷ lệ thắng</th>
                <th>Lợi nhuận</th>
                <th>Profit Factor</th>
                <th>% tổng giao dịch</th>
            </tr>
            {rows}
        </table>
        """
        
        return table_html
    
    def _generate_symbol_table(self, symbol_metrics: Dict) -> str:
        """
        Tạo bảng HTML cho hiệu suất theo cặp tiền
        
        Args:
            symbol_metrics (Dict): Hiệu suất theo cặp tiền
            
        Returns:
            str: Bảng HTML
        """
        if not symbol_metrics:
            return "<p>Không có dữ liệu cặp tiền</p>"
        
        rows = ""
        for symbol, metrics in symbol_metrics.items():
            rows += f"""
            <tr>
                <td>{symbol}</td>
                <td>{metrics.get('trade_count', 0)}</td>
                <td>{metrics.get('win_rate', 0):.2f}%</td>
                <td class="{'positive' if metrics.get('total_pnl', 0) >= 0 else 'negative'}">$ {metrics.get('total_pnl', 0):.2f}</td>
                <td>{metrics.get('profit_factor', 0):.2f}</td>
                <td>{metrics.get('percentage_of_total', 0):.2f}%</td>
            </tr>
            """
        
        table_html = f"""
        <table>
            <tr>
                <th>Cặp tiền</th>
                <th>Số giao dịch</th>
                <th>Tỷ lệ thắng</th>
                <th>Lợi nhuận</th>
                <th>Profit Factor</th>
                <th>% tổng giao dịch</th>
            </tr>
            {rows}
        </table>
        """
        
        return table_html
    
    def _generate_trades_table(self, trades: List[Dict]) -> str:
        """
        Tạo bảng HTML cho danh sách giao dịch
        
        Args:
            trades (List[Dict]): Danh sách giao dịch
            
        Returns:
            str: Bảng HTML
        """
        if not trades:
            return "<p>Không có giao dịch nào</p>"
        
        # Sắp xếp giao dịch theo thời gian
        sorted_trades = sorted(trades, key=lambda x: x.get('exit_time', 0), reverse=True)
        
        rows = ""
        for trade in sorted_trades:
            entry_time = datetime.datetime.fromtimestamp(trade.get('entry_time', 0)).strftime('%Y-%m-%d %H:%M')
            exit_time = datetime.datetime.fromtimestamp(trade.get('exit_time', 0)).strftime('%Y-%m-%d %H:%M')
            
            rows += f"""
            <tr>
                <td>{trade.get('symbol', '')}</td>
                <td>{trade.get('side', '')}</td>
                <td>{entry_time}</td>
                <td>{exit_time}</td>
                <td>$ {trade.get('entry_price', 0):.4f}</td>
                <td>$ {trade.get('exit_price', 0):.4f}</td>
                <td>{trade.get('position_size', 0):.4f}</td>
                <td class="{'positive' if trade.get('pnl', 0) >= 0 else 'negative'}">$ {trade.get('pnl', 0):.2f}</td>
                <td class="{'positive' if trade.get('roi', 0) >= 0 else 'negative'}">{trade.get('roi', 0):.2f}%</td>
                <td>{trade.get('strategy', 'Unknown')}</td>
            </tr>
            """
        
        table_html = f"""
        <table>
            <tr>
                <th>Cặp tiền</th>
                <th>Hướng</th>
                <th>Thời gian vào</th>
                <th>Thời gian ra</th>
                <th>Giá vào</th>
                <th>Giá ra</th>
                <th>Kích thước</th>
                <th>Lợi nhuận</th>
                <th>ROI</th>
                <th>Chiến lược</th>
            </tr>
            {rows}
        </table>
        """
        
        return table_html
    
    def _generate_alerts_table(self, alerts: List[Dict]) -> str:
        """
        Tạo bảng HTML cho danh sách cảnh báo
        
        Args:
            alerts (List[Dict]): Danh sách cảnh báo
            
        Returns:
            str: Bảng HTML
        """
        if not alerts:
            return "<p>Không có cảnh báo nào</p>"
        
        # Sắp xếp cảnh báo theo thời gian
        sorted_alerts = sorted(alerts, key=lambda x: x.get('timestamp', 0), reverse=True)
        
        rows = ""
        for alert in sorted_alerts:
            timestamp = datetime.datetime.fromtimestamp(alert.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M')
            
            rows += f"""
            <tr>
                <td>{alert.get('type', '')}</td>
                <td>{alert.get('level', '')}</td>
                <td>{alert.get('message', '')}</td>
                <td>{timestamp}</td>
            </tr>
            """
        
        table_html = f"""
        <table>
            <tr>
                <th>Loại</th>
                <th>Cấp độ</th>
                <th>Thông báo</th>
                <th>Thời gian</th>
            </tr>
            {rows}
        </table>
        """
        
        return table_html
    
    def generate_strategy_recommendations(self) -> Dict:
        """
        Tạo đề xuất điều chỉnh chiến lược dựa trên hiệu suất
        
        Returns:
            Dict: Các đề xuất điều chỉnh chiến lược
        """
        # Lấy chỉ số hiệu suất mới nhất
        metrics = self.get_latest_metrics()
        
        if not metrics:
            return {
                'status': 'no_data',
                'message': 'Không có dữ liệu hiệu suất',
                'recommendations': []
            }
        
        # Lấy chỉ số hiệu suất theo chiến lược
        strategy_metrics = metrics.get('strategies', {})
        
        # Tạo đề xuất dựa trên hiệu suất
        recommendations = []
        
        # Kiểm tra các ngưỡng mong muốn
        metrics_thresholds = self.config.get('metrics', {})
        win_rate_min = metrics_thresholds.get('win_rate_min', 45)
        profit_factor_min = metrics_thresholds.get('profit_factor_min', 1.2)
        rr_ratio_min = metrics_thresholds.get('rr_ratio_min', 1.5)
        
        for strategy, strategy_data in strategy_metrics.items():
            # Bỏ qua chiến lược có quá ít giao dịch
            min_trades = self.config.get('strategies', {}).get('min_trades_for_evaluation', 20)
            if strategy_data.get('total_trades', 0) < min_trades:
                continue
            
            strategy_recs = []
            
            # Kiểm tra tỷ lệ thắng
            win_rate = strategy_data.get('win_rate', 0)
            if win_rate < win_rate_min:
                strategy_recs.append({
                    'type': 'win_rate',
                    'message': f'Tỷ lệ thắng ({win_rate:.2f}%) dưới ngưỡng mong muốn ({win_rate_min}%)',
                    'suggestion': 'Xem xét tinh chỉnh bộ lọc tín hiệu để giảm số lượng giao dịch thua'
                })
            
            # Kiểm tra Profit Factor
            profit_factor = strategy_data.get('profit_factor', 0)
            if profit_factor < profit_factor_min:
                strategy_recs.append({
                    'type': 'profit_factor',
                    'message': f'Profit Factor ({profit_factor:.2f}) dưới ngưỡng mong muốn ({profit_factor_min})',
                    'suggestion': 'Xem xét điều chỉnh take profit và stop loss để cải thiện Profit Factor'
                })
            
            # Kiểm tra tỷ lệ R/R
            rr_ratio = strategy_data.get('rr_ratio', 0)
            if rr_ratio < rr_ratio_min:
                strategy_recs.append({
                    'type': 'rr_ratio',
                    'message': f'Tỷ lệ R/R ({rr_ratio:.2f}) dưới ngưỡng mong muốn ({rr_ratio_min})',
                    'suggestion': 'Xem xét điều chỉnh take profit xa hơn hoặc stop loss gần hơn để cải thiện tỷ lệ R/R'
                })
            
            # Kiểm tra chuỗi thua liên tiếp
            consecutive_losses = strategy_data.get('consecutive_losses', 0)
            if consecutive_losses >= 5:
                strategy_recs.append({
                    'type': 'consecutive_losses',
                    'message': f'Chuỗi thua liên tiếp cao ({consecutive_losses})',
                    'suggestion': 'Xem xét thêm bộ lọc để tránh giao dịch trong điều kiện thị trường bất lợi'
                })
            
            # Thêm đề xuất cho chiến lược này
            if strategy_recs:
                recommendations.append({
                    'strategy': strategy,
                    'issues': strategy_recs,
                    'overall_score': self._calculate_strategy_health_score(strategy_data)
                })
        
        # Xếp hạng các chiến lược theo hiệu suất
        strategy_ranking = []
        
        for strategy, strategy_data in strategy_metrics.items():
            # Bỏ qua chiến lược có quá ít giao dịch
            if strategy_data.get('total_trades', 0) < 5:
                continue
            
            # Tính điểm tổng hợp
            score = self._calculate_strategy_health_score(strategy_data)
            
            strategy_ranking.append({
                'strategy': strategy,
                'score': score,
                'win_rate': strategy_data.get('win_rate', 0),
                'profit_factor': strategy_data.get('profit_factor', 0),
                'total_pnl': strategy_data.get('total_pnl', 0)
            })
        
        # Sắp xếp theo điểm
        strategy_ranking.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            'status': 'success',
            'message': 'Đã tạo đề xuất điều chỉnh chiến lược',
            'recommendations': recommendations,
            'strategy_ranking': strategy_ranking
        }
    
    def _calculate_strategy_health_score(self, strategy_data: Dict) -> float:
        """
        Tính điểm sức khỏe của chiến lược
        
        Args:
            strategy_data (Dict): Dữ liệu hiệu suất của chiến lược
            
        Returns:
            float: Điểm sức khỏe (0-100)
        """
        # Lấy các chỉ số quan trọng
        win_rate = strategy_data.get('win_rate', 0)
        profit_factor = strategy_data.get('profit_factor', 0)
        rr_ratio = strategy_data.get('rr_ratio', 0)
        trades_count = strategy_data.get('total_trades', 0)
        
        # Tính điểm từng thành phần
        win_rate_score = min(win_rate / 50 * 100, 100)  # Tỷ lệ thắng 50% -> 100 điểm
        
        profit_factor_score = min(profit_factor / 1.5 * 100, 100)  # Profit Factor 1.5 -> 100 điểm
        
        rr_ratio_score = min(rr_ratio / 2 * 100, 100)  # R/R 2.0 -> 100 điểm
        
        # Điểm cho số lượng giao dịch (càng nhiều càng đáng tin)
        trade_count_score = min(trades_count / 50 * 100, 100)  # 50 giao dịch -> 100 điểm
        
        # Tính điểm tổng hợp
        total_score = (
            win_rate_score * 0.35 +
            profit_factor_score * 0.3 +
            rr_ratio_score * 0.25 +
            trade_count_score * 0.1
        )
        
        return total_score
    
    def create_equity_chart(self, period: str = 'all', output_path: str = None) -> str:
        """
        Tạo biểu đồ equity curve
        
        Args:
            period (str): Khoảng thời gian ('all', 'daily', 'weekly', 'monthly')
            output_path (str, optional): Đường dẫn lưu biểu đồ
            
        Returns:
            str: Đường dẫn đến file biểu đồ
        """
        # Nếu không có giao dịch, trả về lỗi
        if not self.trade_history:
            logger.warning("Không có dữ liệu giao dịch để tạo biểu đồ equity")
            return ""
        
        # Xác định khoảng thời gian
        now = int(time.time())
        
        if period == 'daily':
            start_timestamp = now - 86400
            period_str = 'daily'
        elif period == 'weekly':
            start_timestamp = now - 604800
            period_str = 'weekly'
        elif period == 'monthly':
            start_timestamp = now - 2592000
            period_str = 'monthly'
        else:
            start_timestamp = 0
            period_str = 'all'
        
        # Lọc giao dịch trong khoảng thời gian
        filtered_trades = [t for t in self.trade_history if t.get('exit_time', 0) >= start_timestamp]
        
        # Sắp xếp giao dịch theo thời gian
        sorted_trades = sorted(filtered_trades, key=lambda x: x.get('exit_time', 0))
        
        # Tạo dữ liệu cho biểu đồ
        timestamps = []
        equity_values = []
        
        initial_balance = 10000  # Giả sử ban đầu có 10000
        current_equity = initial_balance
        
        # Thêm điểm đầu tiên
        if sorted_trades:
            first_trade_time = sorted_trades[0].get('exit_time', 0)
            timestamps.append(datetime.datetime.fromtimestamp(first_trade_time - 86400))  # Ngày trước giao dịch đầu tiên
            equity_values.append(current_equity)
        
        # Thêm các điểm giao dịch
        for trade in sorted_trades:
            current_equity += trade.get('pnl', 0)
            timestamps.append(datetime.datetime.fromtimestamp(trade.get('exit_time', 0)))
            equity_values.append(current_equity)
        
        # Tạo figure
        plt.figure(figsize=(12, 6))
        
        # Thiết lập style
        plt.style.use(self.config.get('visualization', {}).get('chart_style', 'seaborn'))
        
        # Vẽ đường equity
        plt.plot(timestamps, equity_values, label='Equity', color='#1f77b4', linewidth=2)
        
        # Vẽ đường peak equity
        peak_equity = [equity_values[0]]
        for eq in equity_values[1:]:
            peak_equity.append(max(peak_equity[-1], eq))
        
        plt.plot(timestamps, peak_equity, label='Peak Equity', color='#2ca02c', linestyle='--', linewidth=1)
        
        # Đường drawdown
        drawdown = [(peak - eq) / peak * 100 for peak, eq in zip(peak_equity, equity_values)]
        
        # Vẽ drawdown trên biểu đồ phụ
        ax1 = plt.gca()
        ax2 = ax1.twinx()
        ax2.fill_between(timestamps, drawdown, alpha=0.3, color='#d62728')
        ax2.set_ylabel('Drawdown (%)', color='#d62728')
        ax2.tick_params(axis='y', labelcolor='#d62728')
        
        # Thiết lập tiêu đề và nhãn
        plt.title(f'Equity Curve ({period_str.capitalize()})')
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Equity')
        
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Xác định đường dẫn lưu file
        if output_path is None:
            os.makedirs('reports/charts', exist_ok=True)
            output_path = f'reports/charts/equity_curve_{period_str}.png'
        
        # Lưu biểu đồ
        plt.savefig(output_path, dpi=100, bbox_inches='tight')
        plt.close()
        
        return output_path
    
    def create_win_loss_chart(self, period: str = 'all', output_path: str = None) -> str:
        """
        Tạo biểu đồ thống kê thắng/thua
        
        Args:
            period (str): Khoảng thời gian ('all', 'daily', 'weekly', 'monthly')
            output_path (str, optional): Đường dẫn lưu biểu đồ
            
        Returns:
            str: Đường dẫn đến file biểu đồ
        """
        # Nếu không có giao dịch, trả về lỗi
        if not self.trade_history:
            logger.warning("Không có dữ liệu giao dịch để tạo biểu đồ win/loss")
            return ""
        
        # Xác định khoảng thời gian
        now = int(time.time())
        
        if period == 'daily':
            start_timestamp = now - 86400
            period_str = 'daily'
        elif period == 'weekly':
            start_timestamp = now - 604800
            period_str = 'weekly'
        elif period == 'monthly':
            start_timestamp = now - 2592000
            period_str = 'monthly'
        else:
            start_timestamp = 0
            period_str = 'all'
        
        # Lọc giao dịch trong khoảng thời gian
        filtered_trades = [t for t in self.trade_history if t.get('exit_time', 0) >= start_timestamp]
        
        # Tách thành giao dịch thắng và thua
        winning_trades = [t for t in filtered_trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in filtered_trades if t.get('pnl', 0) <= 0]
        
        # Tạo dữ liệu cho biểu đồ
        win_pnls = [t.get('pnl', 0) for t in winning_trades]
        loss_pnls = [abs(t.get('pnl', 0)) for t in losing_trades]  # Lấy giá trị tuyệt đối
        
        # Tạo figure
        plt.figure(figsize=(12, 6))
        
        # Thiết lập style
        plt.style.use(self.config.get('visualization', {}).get('chart_style', 'seaborn'))
        
        # Vẽ biểu đồ
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Biểu đồ phân phối lợi nhuận
        if win_pnls:
            ax1.hist(win_pnls, bins=20, alpha=0.7, color='green', label='Wins')
        if loss_pnls:
            ax1.hist(loss_pnls, bins=20, alpha=0.7, color='red', label='Losses')
        
        ax1.set_title('Phân phối lợi nhuận/lỗ')
        ax1.set_xlabel('PnL (USDT)')
        ax1.set_ylabel('Số lượng giao dịch')
        ax1.legend()
        
        # Biểu đồ thống kê
        labels = ['Wins', 'Losses']
        sizes = [len(winning_trades), len(losing_trades)]
        colors = ['green', 'red']
        
        ax2.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        ax2.axis('equal')
        ax2.set_title('Tỷ lệ thắng/thua')
        
        plt.suptitle(f'Thống kê thắng/thua ({period_str.capitalize()})')
        plt.tight_layout()
        
        # Xác định đường dẫn lưu file
        if output_path is None:
            os.makedirs('reports/charts', exist_ok=True)
            output_path = f'reports/charts/win_loss_{period_str}.png'
        
        # Lưu biểu đồ
        plt.savefig(output_path, dpi=100, bbox_inches='tight')
        plt.close()
        
        return output_path
    
    def analyze_trade_distribution(self) -> Dict:
        """
        Phân tích phân phối giao dịch theo giờ và ngày trong tuần
        
        Returns:
            Dict: Kết quả phân tích
        """
        # Nếu không có giao dịch, trả về kết quả trống
        if not self.trade_history:
            return {
                'hour_distribution': {},
                'day_distribution': {},
                'hour_win_rate': {},
                'day_win_rate': {}
            }
        
        # Khởi tạo dữ liệu
        hour_dist = defaultdict(int)
        day_dist = defaultdict(int)
        hour_wins = defaultdict(int)
        day_wins = defaultdict(int)
        hour_total = defaultdict(int)
        day_total = defaultdict(int)
        
        # Phân tích từng giao dịch
        for trade in self.trade_history:
            exit_time = trade.get('exit_time', 0)
            if exit_time:
                dt = datetime.datetime.fromtimestamp(exit_time)
                hour = dt.hour
                day = dt.strftime('%A')  # Tên ngày trong tuần
                
                # Cập nhật phân phối
                hour_dist[hour] += 1
                day_dist[day] += 1
                
                # Cập nhật tỷ lệ thắng
                is_win = trade.get('pnl', 0) > 0
                hour_total[hour] += 1
                day_total[day] += 1
                
                if is_win:
                    hour_wins[hour] += 1
                    day_wins[day] += 1
        
        # Tính tỷ lệ thắng
        hour_win_rate = {h: hour_wins[h] / hour_total[h] * 100 if hour_total[h] > 0 else 0 for h in hour_total}
        day_win_rate = {d: day_wins[d] / day_total[d] * 100 if day_total[d] > 0 else 0 for d in day_total}
        
        # Sắp xếp dữ liệu
        hour_dist_sorted = {h: hour_dist[h] for h in sorted(hour_dist.keys())}
        day_dist_sorted = {}
        
        # Sắp xếp theo thứ trong tuần
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day in days_order:
            if day in day_dist:
                day_dist_sorted[day] = day_dist[day]
        
        return {
            'hour_distribution': hour_dist_sorted,
            'day_distribution': day_dist_sorted,
            'hour_win_rate': {h: hour_win_rate[h] for h in sorted(hour_win_rate.keys())},
            'day_win_rate': {d: day_win_rate[d] for d in days_order if d in day_win_rate}
        }
    
    def create_trade_distribution_chart(self, output_path: str = None) -> str:
        """
        Tạo biểu đồ phân phối giao dịch
        
        Args:
            output_path (str, optional): Đường dẫn lưu biểu đồ
            
        Returns:
            str: Đường dẫn đến file biểu đồ
        """
        # Phân tích phân phối giao dịch
        distribution_data = self.analyze_trade_distribution()
        
        if not distribution_data.get('hour_distribution') and not distribution_data.get('day_distribution'):
            logger.warning("Không có dữ liệu giao dịch để tạo biểu đồ phân phối")
            return ""
        
        # Tạo figure
        plt.figure(figsize=(14, 10))
        
        # Thiết lập style
        plt.style.use(self.config.get('visualization', {}).get('chart_style', 'seaborn'))
        
        # Tạo 4 biểu đồ con
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
        
        # Biểu đồ phân phối theo giờ
        hours = list(distribution_data['hour_distribution'].keys())
        hour_counts = list(distribution_data['hour_distribution'].values())
        
        ax1.bar(hours, hour_counts, color='skyblue')
        ax1.set_title('Phân phối giao dịch theo giờ')
        ax1.set_xlabel('Giờ trong ngày')
        ax1.set_ylabel('Số lượng giao dịch')
        ax1.set_xticks(range(0, 24))
        
        # Biểu đồ phân phối theo ngày
        days = list(distribution_data['day_distribution'].keys())
        day_counts = list(distribution_data['day_distribution'].values())
        
        ax2.bar(days, day_counts, color='lightgreen')
        ax2.set_title('Phân phối giao dịch theo ngày')
        ax2.set_xlabel('Ngày trong tuần')
        ax2.set_ylabel('Số lượng giao dịch')
        ax2.tick_params(axis='x', rotation=45)
        
        # Biểu đồ tỷ lệ thắng theo giờ
        hour_win_rates = list(distribution_data['hour_win_rate'].values())
        
        ax3.bar(hours, hour_win_rates, color='orange')
        ax3.set_title('Tỷ lệ thắng theo giờ')
        ax3.set_xlabel('Giờ trong ngày')
        ax3.set_ylabel('Tỷ lệ thắng (%)')
        ax3.set_xticks(range(0, 24))
        ax3.set_ylim(0, 100)
        
        # Biểu đồ tỷ lệ thắng theo ngày
        day_win_rates = list(distribution_data['day_win_rate'].values())
        
        ax4.bar(days, day_win_rates, color='salmon')
        ax4.set_title('Tỷ lệ thắng theo ngày')
        ax4.set_xlabel('Ngày trong tuần')
        ax4.set_ylabel('Tỷ lệ thắng (%)')
        ax4.tick_params(axis='x', rotation=45)
        ax4.set_ylim(0, 100)
        
        plt.suptitle('Phân tích phân phối giao dịch')
        plt.tight_layout()
        
        # Xác định đường dẫn lưu file
        if output_path is None:
            os.makedirs('reports/charts', exist_ok=True)
            output_path = 'reports/charts/trade_distribution.png'
        
        # Lưu biểu đồ
        plt.savefig(output_path, dpi=100, bbox_inches='tight')
        plt.close()
        
        return output_path


def main():
    """Hàm chính để test PerformanceMonitor"""
    monitor = PerformanceMonitor()
    
    # Thêm một số giao dịch mẫu
    for i in range(20):
        win = i % 3 != 0  # 2/3 win rate
        
        trade_data = {
            'symbol': f"{'BTC' if i % 2 == 0 else 'ETH'}USDT",
            'side': 'LONG' if i % 4 < 2 else 'SHORT',
            'entry_price': 50000 if i % 2 == 0 else 2000,
            'exit_price': (50000 * (1.03 if win else 0.98)) if i % 2 == 0 else (2000 * (1.04 if win else 0.97)),
            'position_size': 0.1,
            'leverage': 5,
            'strategy': f"Strategy{i % 3 + 1}",
            'entry_time': int(time.time()) - (86400 * (20 - i)),  # Từ 20 ngày trước đến hiện tại
            'exit_time': int(time.time()) - (86400 * (20 - i)) + 7200  # +2 giờ
        }
        
        monitor.record_trade(trade_data)
    
    # Cập nhật chỉ số
    metrics = monitor.update_metrics()
    print("Chỉ số hiệu suất tổng thể:")
    print(f"Tổng số giao dịch: {metrics['overall']['total_trades']}")
    print(f"Tỷ lệ thắng: {metrics['overall']['win_rate']:.2f}%")
    print(f"Tổng lợi nhuận: {metrics['overall']['total_pnl']:.2f}")
    print(f"Profit Factor: {metrics['overall']['profit_factor']:.2f}")
    
    # Tạo báo cáo hằng ngày
    daily_report = monitor.create_daily_report()
    print(f"Đã tạo báo cáo hằng ngày: {daily_report}")
    
    # Tạo đề xuất chiến lược
    recommendations = monitor.generate_strategy_recommendations()
    print("Đề xuất chiến lược:")
    for rec in recommendations.get('recommendations', []):
        print(f"Chiến lược: {rec['strategy']}")
        for issue in rec['issues']:
            print(f"  - {issue['message']}")
            print(f"    Đề xuất: {issue['suggestion']}")
    
    # Tạo biểu đồ
    equity_chart = monitor.create_equity_chart()
    print(f"Đã tạo biểu đồ equity: {equity_chart}")
    
    win_loss_chart = monitor.create_win_loss_chart()
    print(f"Đã tạo biểu đồ win/loss: {win_loss_chart}")
    
    distribution_chart = monitor.create_trade_distribution_chart()
    print(f"Đã tạo biểu đồ phân phối giao dịch: {distribution_chart}")


if __name__ == "__main__":
    main()