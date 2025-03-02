#!/usr/bin/env python3
"""
Module báo cáo hiệu suất giao dịch

Module này tạo báo cáo chi tiết về hiệu suất giao dịch của bot, bao gồm
phân tích lãi lỗ, thống kê giao dịch, biểu đồ hiệu suất và các chỉ số quan trọng.
"""

import os
import logging
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import matplotlib.dates as mdates
from tabulate import tabulate

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("performance_reporter")

# Thư mục lưu báo cáo và biểu đồ
REPORTS_DIR = "reports"
CHARTS_DIR = "charts"

# Đảm bảo thư mục tồn tại
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)

class PerformanceReporter:
    """Lớp tạo báo cáo hiệu suất giao dịch"""
    
    def __init__(self, 
                 trades_data: pd.DataFrame = None, 
                 trades_file: str = None,
                 account_history_file: str = None,
                 initial_balance: float = 100.0,
                 strategy_name: str = None,
                 risk_profile: str = None,
                 symbol: str = "BTCUSDT",
                 timeframe: str = "1h"):
        """
        Khởi tạo trình tạo báo cáo hiệu suất
        
        Args:
            trades_data (pd.DataFrame, optional): DataFrame chứa dữ liệu giao dịch
            trades_file (str, optional): Đường dẫn đến file CSV chứa dữ liệu giao dịch
            account_history_file (str, optional): Đường dẫn đến file CSV chứa lịch sử tài khoản
            initial_balance (float, optional): Số dư ban đầu
            strategy_name (str, optional): Tên chiến lược
            risk_profile (str, optional): Tên hồ sơ rủi ro
            symbol (str, optional): Biểu tượng giao dịch
            timeframe (str, optional): Khung thời gian
        """
        self.initial_balance = initial_balance
        self.strategy_name = strategy_name
        self.risk_profile = risk_profile
        self.symbol = symbol
        self.timeframe = timeframe
        
        # Tải dữ liệu giao dịch
        if trades_data is not None:
            self.trades_df = trades_data
        elif trades_file is not None:
            self.trades_df = self._load_trades_data(trades_file)
        else:
            self.trades_df = None
            
        # Tải lịch sử tài khoản
        if account_history_file is not None:
            self.account_df = self._load_account_history(account_history_file)
        else:
            self.account_df = None
            
        # Chuyển đổi dữ liệu nếu cần
        if self.trades_df is not None:
            self._preprocess_trades_data()
            
        if self.account_df is not None:
            self._preprocess_account_data()
            
        logger.info("Đã khởi tạo PerformanceReporter")
    
    def _load_trades_data(self, file_path: str) -> pd.DataFrame:
        """
        Tải dữ liệu giao dịch từ file
        
        Args:
            file_path (str): Đường dẫn đến file giao dịch
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu giao dịch
        """
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith('.json'):
                df = pd.read_json(file_path)
            else:
                raise ValueError(f"Định dạng file không được hỗ trợ: {file_path}")
                
            logger.info(f"Đã tải dữ liệu giao dịch từ {file_path}")
            
            return df
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu giao dịch: {e}")
            return pd.DataFrame()
    
    def _load_account_history(self, file_path: str) -> pd.DataFrame:
        """
        Tải lịch sử tài khoản từ file
        
        Args:
            file_path (str): Đường dẫn đến file lịch sử tài khoản
            
        Returns:
            pd.DataFrame: DataFrame chứa lịch sử tài khoản
        """
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith('.json'):
                df = pd.read_json(file_path)
            else:
                raise ValueError(f"Định dạng file không được hỗ trợ: {file_path}")
                
            logger.info(f"Đã tải lịch sử tài khoản từ {file_path}")
            
            return df
        except Exception as e:
            logger.error(f"Lỗi khi tải lịch sử tài khoản: {e}")
            return pd.DataFrame()
    
    def _preprocess_trades_data(self) -> None:
        """Tiền xử lý dữ liệu giao dịch"""
        # Kiểm tra dữ liệu
        if self.trades_df is None or self.trades_df.empty:
            logger.warning("Không có dữ liệu giao dịch để xử lý")
            return
            
        # Chuyển đổi cột thời gian thành datetime
        date_columns = ['entry_time', 'exit_time', 'timestamp', 'time', 'date']
        for col in date_columns:
            if col in self.trades_df.columns:
                self.trades_df[col] = pd.to_datetime(self.trades_df[col])
                
        # Sắp xếp theo thời gian
        for col in date_columns:
            if col in self.trades_df.columns:
                self.trades_df = self.trades_df.sort_values(by=col)
                break
                
        # Tính toán P&L % nếu chưa có
        if 'profit_percent' not in self.trades_df.columns and 'profit' in self.trades_df.columns:
            # Ước tính P&L % từ P&L giá trị
            if 'entry_price' in self.trades_df.columns and 'exit_price' in self.trades_df.columns:
                for idx, row in self.trades_df.iterrows():
                    side = row.get('side', 'buy').lower()
                    entry = row['entry_price']
                    exit = row['exit_price']
                    
                    if side in ['buy', 'long']:
                        self.trades_df.at[idx, 'profit_percent'] = (exit - entry) / entry * 100
                    else:  # sell, short
                        self.trades_df.at[idx, 'profit_percent'] = (entry - exit) / entry * 100
    
    def _preprocess_account_data(self) -> None:
        """Tiền xử lý dữ liệu tài khoản"""
        # Kiểm tra dữ liệu
        if self.account_df is None or self.account_df.empty:
            logger.warning("Không có dữ liệu tài khoản để xử lý")
            return
            
        # Chuyển đổi cột thời gian thành datetime
        date_columns = ['timestamp', 'time', 'date']
        for col in date_columns:
            if col in self.account_df.columns:
                self.account_df[col] = pd.to_datetime(self.account_df[col])
                
        # Sắp xếp theo thời gian
        for col in date_columns:
            if col in self.account_df.columns:
                self.account_df = self.account_df.sort_values(by=col)
                break
    
    def generate_summary_metrics(self) -> Dict:
        """
        Tạo các chỉ số tổng hợp
        
        Returns:
            Dict: Các chỉ số tổng hợp
        """
        if self.trades_df is None or self.trades_df.empty:
            logger.warning("Không có dữ liệu giao dịch để tính chỉ số")
            return {}
            
        # Thống kê cơ bản
        total_trades = len(self.trades_df)
        
        # Tính số lượng giao dịch winning/losing
        if 'profit' in self.trades_df.columns:
            winning_trades = len(self.trades_df[self.trades_df['profit'] > 0])
            losing_trades = len(self.trades_df[self.trades_df['profit'] <= 0])
        elif 'profit_percent' in self.trades_df.columns:
            winning_trades = len(self.trades_df[self.trades_df['profit_percent'] > 0])
            losing_trades = len(self.trades_df[self.trades_df['profit_percent'] <= 0])
        else:
            winning_trades = 0
            losing_trades = 0
            
        # Tính tỷ lệ thắng
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Tính P&L tổng
        if 'profit' in self.trades_df.columns:
            total_profit = self.trades_df['profit'].sum()
            avg_profit = self.trades_df['profit'].mean()
            avg_win = self.trades_df[self.trades_df['profit'] > 0]['profit'].mean() if winning_trades > 0 else 0
            avg_loss = self.trades_df[self.trades_df['profit'] <= 0]['profit'].mean() if losing_trades > 0 else 0
        else:
            total_profit = 0
            avg_profit = 0
            avg_win = 0
            avg_loss = 0
            
        # Tính profit factor
        profit_factor = abs(self.trades_df[self.trades_df['profit'] > 0]['profit'].sum() / self.trades_df[self.trades_df['profit'] < 0]['profit'].sum()) if self.trades_df[self.trades_df['profit'] < 0]['profit'].sum() != 0 else float('inf')
        
        # Tính drawdown
        cumulative_pnl = self.calculate_cumulative_pnl()
        max_drawdown_pct, max_drawdown_duration, max_drawdown_start, max_drawdown_end = self.calculate_drawdown()
        
        # Tính thời gian trung bình nắm giữ
        avg_hold_time = None
        if 'entry_time' in self.trades_df.columns and 'exit_time' in self.trades_df.columns:
            hold_times = (self.trades_df['exit_time'] - self.trades_df['entry_time']).dt.total_seconds() / 3600  # giờ
            avg_hold_time = hold_times.mean()
            
        # Tính hiệu suất hàng tháng nếu có đủ dữ liệu
        monthly_returns = None
        sharpe_ratio = None
        if 'entry_time' in self.trades_df.columns and 'profit' in self.trades_df.columns:
            # Nhóm theo tháng và tính tổng profit
            self.trades_df['month'] = self.trades_df['entry_time'].dt.to_period('M')
            monthly_returns = self.trades_df.groupby('month')['profit'].sum()
            
            # Tính Sharpe ratio (Risk-free rate = 0)
            if len(monthly_returns) > 1:
                mean_return = monthly_returns.mean()
                std_return = monthly_returns.std()
                sharpe_ratio = mean_return / std_return if std_return > 0 else 0
        
        # Tổng hợp kết quả
        metrics = {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "total_profit": total_profit,
            "avg_profit": avg_profit,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "max_drawdown_pct": max_drawdown_pct,
            "max_drawdown_duration": max_drawdown_duration,
            "max_drawdown_start": max_drawdown_start,
            "max_drawdown_end": max_drawdown_end,
            "avg_hold_time": avg_hold_time,
            "sharpe_ratio": sharpe_ratio,
            "final_balance": self.initial_balance + total_profit,
            "roi_percent": (total_profit / self.initial_balance) * 100 if self.initial_balance > 0 else 0,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "strategy": self.strategy_name,
            "risk_profile": self.risk_profile,
            "report_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        logger.info("Đã tạo các chỉ số tổng hợp")
        
        return metrics
    
    def calculate_cumulative_pnl(self) -> pd.Series:
        """
        Tính toán P&L tích lũy
        
        Returns:
            pd.Series: P&L tích lũy theo thời gian
        """
        if self.trades_df is None or self.trades_df.empty:
            logger.warning("Không có dữ liệu giao dịch để tính P&L tích lũy")
            return pd.Series()
            
        if 'profit' not in self.trades_df.columns:
            logger.warning("Không có cột 'profit' trong dữ liệu giao dịch")
            return pd.Series()
            
        # Sắp xếp theo thời gian
        date_column = None
        for col in ['exit_time', 'entry_time', 'timestamp', 'time', 'date']:
            if col in self.trades_df.columns:
                date_column = col
                break
                
        if date_column is None:
            logger.warning("Không tìm thấy cột thời gian trong dữ liệu giao dịch")
            return pd.Series()
            
        # Sắp xếp và tính P&L tích lũy
        sorted_trades = self.trades_df.sort_values(by=date_column)
        cumulative_pnl = sorted_trades['profit'].cumsum()
        cumulative_pnl.index = sorted_trades[date_column]
        
        # Thêm điểm đầu (balance ban đầu)
        if date_column in sorted_trades.columns and not sorted_trades.empty:
            start_date = sorted_trades[date_column].min() - timedelta(days=1)
            cumulative_pnl = pd.concat([pd.Series([0], index=[start_date]), cumulative_pnl])
            
        # Chuyển về balance
        cumulative_balance = cumulative_pnl + self.initial_balance
        
        return cumulative_balance
    
    def calculate_drawdown(self) -> Tuple[float, float, datetime, datetime]:
        """
        Tính toán drawdown tối đa
        
        Returns:
            Tuple[float, float, datetime, datetime]: (Drawdown tối đa (%), Thời gian drawdown (ngày), Thời điểm bắt đầu, Thời điểm kết thúc)
        """
        cumulative_balance = self.calculate_cumulative_pnl()
        
        if cumulative_balance.empty:
            return 0, 0, None, None
            
        # Tính drawdown
        running_max = cumulative_balance.cummax()
        drawdown = (cumulative_balance - running_max) / running_max * 100
        
        # Tìm drawdown tối đa
        max_drawdown_idx = drawdown.idxmin()
        max_drawdown_pct = drawdown.min()
        
        # Tìm thời điểm bắt đầu drawdown
        peak_idx = running_max.loc[:max_drawdown_idx].idxmax()
        
        # Tìm thời điểm kết thúc drawdown (khi balance trở lại peak)
        recovery_idx = None
        after_trough = cumulative_balance.loc[max_drawdown_idx:] >= running_max[peak_idx]
        if any(after_trough):
            recovery_idx = after_trough[after_trough].index[0]
            
        # Tính thời gian drawdown
        if recovery_idx is not None:
            drawdown_duration = (recovery_idx - peak_idx).total_seconds() / (24 * 3600)  # ngày
        else:
            drawdown_duration = (cumulative_balance.index[-1] - peak_idx).total_seconds() / (24 * 3600)
            
        return max_drawdown_pct, drawdown_duration, peak_idx, max_drawdown_idx
    
    def calculate_periodic_returns(self, period: str = 'M') -> pd.Series:
        """
        Tính toán lợi nhuận theo kỳ
        
        Args:
            period (str): Kỳ ('D' = ngày, 'W' = tuần, 'M' = tháng, 'Y' = năm)
            
        Returns:
            pd.Series: Lợi nhuận theo kỳ
        """
        if self.trades_df is None or self.trades_df.empty:
            logger.warning("Không có dữ liệu giao dịch để tính lợi nhuận theo kỳ")
            return pd.Series()
            
        if 'profit' not in self.trades_df.columns:
            logger.warning("Không có cột 'profit' trong dữ liệu giao dịch")
            return pd.Series()
            
        # Tìm cột thời gian
        date_column = None
        for col in ['exit_time', 'entry_time', 'timestamp', 'time', 'date']:
            if col in self.trades_df.columns:
                date_column = col
                break
                
        if date_column is None:
            logger.warning("Không tìm thấy cột thời gian trong dữ liệu giao dịch")
            return pd.Series()
            
        # Tính lợi nhuận theo kỳ
        try:
            self.trades_df['period'] = self.trades_df[date_column].dt.to_period(period)
            periodic_returns = self.trades_df.groupby('period')['profit'].sum()
            return periodic_returns
        except Exception as e:
            logger.error(f"Lỗi khi tính lợi nhuận theo kỳ: {e}")
            return pd.Series()
    
    def generate_equity_curve_chart(self, file_path: str = None) -> str:
        """
        Tạo biểu đồ đường vốn (equity curve)
        
        Args:
            file_path (str, optional): Đường dẫn lưu biểu đồ
            
        Returns:
            str: Đường dẫn đến biểu đồ đã lưu
        """
        cumulative_balance = self.calculate_cumulative_pnl()
        
        if cumulative_balance.empty:
            logger.warning("Không có dữ liệu để tạo biểu đồ đường vốn")
            return None
            
        # Tạo biểu đồ
        plt.figure(figsize=(12, 6))
        plt.plot(cumulative_balance.index, cumulative_balance.values, label='Equity Curve', color='#2196F3', linewidth=2)
        
        # Thêm đường tham chiếu
        plt.axhline(y=self.initial_balance, color='#616161', linestyle='--', alpha=0.5, label='Initial Balance')
        
        # Tìm drawdown tối đa
        _, _, drawdown_start, drawdown_end = self.calculate_drawdown()
        
        # Highlight drawdown tối đa
        if drawdown_start is not None and drawdown_end is not None:
            plt.axvspan(drawdown_start, drawdown_end, alpha=0.2, color='red', label='Max Drawdown')
            
        # Thêm nhãn
        strategy_label = f"Strategy: {self.strategy_name}" if self.strategy_name else ""
        risk_label = f"Risk Profile: {self.risk_profile}" if self.risk_profile else ""
        symbol_label = f"Symbol: {self.symbol}" if self.symbol else ""
        timeframe_label = f"Timeframe: {self.timeframe}" if self.timeframe else ""
        
        info_text = "\n".join(filter(None, [strategy_label, risk_label, symbol_label, timeframe_label]))
        
        # Đặt tiêu đề và nhãn
        plt.title('Equity Curve', fontsize=14, fontweight='bold')
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Balance (USD)', fontsize=12)
        plt.grid(True, alpha=0.3)
        
        # Định dạng trục x
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.gcf().autofmt_xdate()
        
        # Thêm text box với thông tin
        plt.figtext(0.01, 0.01, info_text, fontsize=10, ha='left')
        
        # Thêm legend
        plt.legend()
        
        # Lưu biểu đồ
        if file_path is None:
            file_path = os.path.join(CHARTS_DIR, f"equity_curve_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
        plt.tight_layout()
        plt.savefig(file_path, dpi=300)
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ đường vốn và lưu tại {file_path}")
        
        return file_path
    
    def generate_monthly_returns_chart(self, file_path: str = None) -> str:
        """
        Tạo biểu đồ lợi nhuận hàng tháng
        
        Args:
            file_path (str, optional): Đường dẫn lưu biểu đồ
            
        Returns:
            str: Đường dẫn đến biểu đồ đã lưu
        """
        monthly_returns = self.calculate_periodic_returns('M')
        
        if monthly_returns.empty:
            logger.warning("Không có dữ liệu để tạo biểu đồ lợi nhuận hàng tháng")
            return None
            
        # Tạo biểu đồ
        plt.figure(figsize=(12, 6))
        
        # Tạo màu cho từng cột
        colors = ['#4CAF50' if x >= 0 else '#F44336' for x in monthly_returns.values]
        
        # Vẽ biểu đồ cột
        monthly_returns.plot(kind='bar', color=colors, alpha=0.7)
        
        # Thêm đường ngang tại 0
        plt.axhline(y=0, color='#616161', linestyle='-', alpha=0.3)
        
        # Thêm nhãn giá trị trên mỗi cột
        for i, v in enumerate(monthly_returns.values):
            plt.text(i, v + (1 if v >= 0 else -1), f'{v:.2f}', ha='center', fontsize=9)
            
        # Thêm nhãn
        strategy_label = f"Strategy: {self.strategy_name}" if self.strategy_name else ""
        risk_label = f"Risk Profile: {self.risk_profile}" if self.risk_profile else ""
        symbol_label = f"Symbol: {self.symbol}" if self.symbol else ""
        
        info_text = "\n".join(filter(None, [strategy_label, risk_label, symbol_label]))
        
        # Đặt tiêu đề và nhãn
        plt.title('Monthly Returns', fontsize=14, fontweight='bold')
        plt.xlabel('Month', fontsize=12)
        plt.ylabel('Profit/Loss (USD)', fontsize=12)
        plt.grid(True, axis='y', alpha=0.3)
        
        # Thêm text box với thông tin
        plt.figtext(0.01, 0.01, info_text, fontsize=10, ha='left')
        
        # Lưu biểu đồ
        if file_path is None:
            file_path = os.path.join(CHARTS_DIR, f"monthly_returns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
        plt.tight_layout()
        plt.savefig(file_path, dpi=300)
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ lợi nhuận hàng tháng và lưu tại {file_path}")
        
        return file_path
    
    def generate_win_loss_chart(self, file_path: str = None) -> str:
        """
        Tạo biểu đồ thống kê thắng thua
        
        Args:
            file_path (str, optional): Đường dẫn lưu biểu đồ
            
        Returns:
            str: Đường dẫn đến biểu đồ đã lưu
        """
        if self.trades_df is None or self.trades_df.empty:
            logger.warning("Không có dữ liệu giao dịch để tạo biểu đồ thắng thua")
            return None
            
        # Tính số lượng giao dịch winning/losing
        if 'profit' in self.trades_df.columns:
            winning_trades = len(self.trades_df[self.trades_df['profit'] > 0])
            losing_trades = len(self.trades_df[self.trades_df['profit'] <= 0])
        elif 'profit_percent' in self.trades_df.columns:
            winning_trades = len(self.trades_df[self.trades_df['profit_percent'] > 0])
            losing_trades = len(self.trades_df[self.trades_df['profit_percent'] <= 0])
        else:
            logger.warning("Không có cột 'profit' hoặc 'profit_percent' trong dữ liệu giao dịch")
            return None
            
        # Tạo biểu đồ
        plt.figure(figsize=(10, 6))
        
        # Dữ liệu cho biểu đồ
        categories = ['Winning Trades', 'Losing Trades']
        values = [winning_trades, losing_trades]
        colors = ['#4CAF50', '#F44336']
        
        # Vẽ biểu đồ cột
        plt.bar(categories, values, color=colors, alpha=0.7)
        
        # Thêm nhãn giá trị trên mỗi cột
        for i, v in enumerate(values):
            plt.text(i, v + 0.5, str(v), ha='center', fontsize=12, fontweight='bold')
            
        # Tính tỷ lệ thắng
        win_rate = winning_trades / (winning_trades + losing_trades) * 100 if (winning_trades + losing_trades) > 0 else 0
        
        # Thêm nhãn
        strategy_label = f"Strategy: {self.strategy_name}" if self.strategy_name else ""
        risk_label = f"Risk Profile: {self.risk_profile}" if self.risk_profile else ""
        win_rate_label = f"Win Rate: {win_rate:.2f}%"
        
        info_text = "\n".join(filter(None, [strategy_label, risk_label, win_rate_label]))
        
        # Đặt tiêu đề và nhãn
        plt.title('Win/Loss Distribution', fontsize=14, fontweight='bold')
        plt.ylabel('Number of Trades', fontsize=12)
        plt.grid(True, axis='y', alpha=0.3)
        
        # Thêm text box với thông tin
        plt.figtext(0.01, 0.01, info_text, fontsize=10, ha='left')
        
        # Lưu biểu đồ
        if file_path is None:
            file_path = os.path.join(CHARTS_DIR, f"win_loss_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
        plt.tight_layout()
        plt.savefig(file_path, dpi=300)
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ thắng thua và lưu tại {file_path}")
        
        return file_path
    
    def generate_trade_distribution_chart(self, file_path: str = None) -> str:
        """
        Tạo biểu đồ phân phối lợi nhuận giao dịch
        
        Args:
            file_path (str, optional): Đường dẫn lưu biểu đồ
            
        Returns:
            str: Đường dẫn đến biểu đồ đã lưu
        """
        if self.trades_df is None or self.trades_df.empty:
            logger.warning("Không có dữ liệu giao dịch để tạo biểu đồ phân phối")
            return None
            
        # Tìm cột lợi nhuận
        profit_column = None
        for col in ['profit_percent', 'profit']:
            if col in self.trades_df.columns:
                profit_column = col
                break
                
        if profit_column is None:
            logger.warning("Không tìm thấy cột lợi nhuận trong dữ liệu giao dịch")
            return None
            
        # Tạo biểu đồ
        plt.figure(figsize=(12, 6))
        
        # Vẽ histogram
        n, bins, patches = plt.hist(self.trades_df[profit_column], bins=20, alpha=0.7, color='#2196F3')
        
        # Thay đổi màu cho các khoảng giá trị âm/dương
        for i, patch in enumerate(patches):
            if bins[i] < 0:
                patch.set_facecolor('#F44336')
            else:
                patch.set_facecolor('#4CAF50')
                
        # Thêm đường mật độ xác suất
        try:
            kde_x = np.linspace(min(self.trades_df[profit_column]), max(self.trades_df[profit_column]), 100)
            kde = stats.gaussian_kde(self.trades_df[profit_column])
            plt.plot(kde_x, kde(kde_x) * len(self.trades_df[profit_column]) * (bins[1] - bins[0]), 'k-', linewidth=2)
        except:
            pass
            
        # Thêm đường dọc tại 0
        plt.axvline(x=0, color='#616161', linestyle='-', alpha=0.5)
        
        # Thêm nhãn thống kê
        mean_profit = self.trades_df[profit_column].mean()
        median_profit = self.trades_df[profit_column].median()
        std_profit = self.trades_df[profit_column].std()
        
        stats_text = f"Mean: {mean_profit:.2f}\nMedian: {median_profit:.2f}\nStd Dev: {std_profit:.2f}"
        
        # Thêm nhãn
        plt.title('Trade Profit Distribution', fontsize=14, fontweight='bold')
        plt.xlabel('Profit/Loss' + (' (%)' if profit_column == 'profit_percent' else ' (USD)'), fontsize=12)
        plt.ylabel('Number of Trades', fontsize=12)
        plt.grid(True, alpha=0.3)
        
        # Thêm text box với thông tin thống kê
        plt.figtext(0.01, 0.01, stats_text, fontsize=10, ha='left')
        
        # Lưu biểu đồ
        if file_path is None:
            file_path = os.path.join(CHARTS_DIR, f"profit_distribution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
        plt.tight_layout()
        plt.savefig(file_path, dpi=300)
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ phân phối lợi nhuận và lưu tại {file_path}")
        
        return file_path
    
    def generate_html_report(self, output_path: str = None) -> str:
        """
        Tạo báo cáo HTML tổng hợp
        
        Args:
            output_path (str, optional): Đường dẫn lưu báo cáo
            
        Returns:
            str: Đường dẫn đến báo cáo HTML
        """
        # Tạo các biểu đồ
        equity_chart = self.generate_equity_curve_chart()
        monthly_chart = self.generate_monthly_returns_chart()
        win_loss_chart = self.generate_win_loss_chart()
        distribution_chart = self.generate_trade_distribution_chart()
        
        # Tính toán các chỉ số
        metrics = self.generate_summary_metrics()
        
        # Tạo bảng giao dịch gần đây
        recent_trades_table = ""
        if self.trades_df is not None and not self.trades_df.empty:
            # Sắp xếp theo thời gian
            date_column = None
            for col in ['exit_time', 'entry_time', 'timestamp', 'time', 'date']:
                if col in self.trades_df.columns:
                    date_column = col
                    break
                    
            if date_column is not None:
                # Lấy 10 giao dịch gần nhất
                recent_trades = self.trades_df.sort_values(by=date_column, ascending=False).head(10)
                
                # Tạo bảng HTML
                recent_trades_table = recent_trades.to_html(
                    index=False, 
                    columns=[col for col in ['entry_time', 'exit_time', 'symbol', 'side', 'entry_price', 'exit_price', 'quantity', 'profit', 'profit_percent', 'exit_reason'] if col in recent_trades.columns],
                    float_format='%.4f'
                )
                
        # Tạo nội dung HTML
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Trading Performance Report</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1, h2, h3 {{
                    color: #2196F3;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                    border-bottom: 2px solid #eee;
                    padding-bottom: 20px;
                }}
                .metrics-container {{
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: space-between;
                    margin-bottom: 30px;
                }}
                .metric-box {{
                    background-color: #f9f9f9;
                    border-radius: 5px;
                    padding: 15px;
                    width: calc(25% - 20px);
                    box-sizing: border-box;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }}
                .metric-title {{
                    font-size: 0.9em;
                    color: #666;
                    margin-bottom: 5px;
                }}
                .metric-value {{
                    font-size: 1.4em;
                    font-weight: bold;
                }}
                .metric-value.positive {{
                    color: #4CAF50;
                }}
                .metric-value.negative {{
                    color: #F44336;
                }}
                .charts-container {{
                    margin-bottom: 30px;
                }}
                .chart {{
                    margin-bottom: 30px;
                }}
                .chart img {{
                    max-width: 100%;
                    height: auto;
                    border-radius: 5px;
                    box-shadow: 0 3px 10px rgba(0,0,0,0.1);
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 30px;
                }}
                th, td {{
                    padding: 10px;
                    border: 1px solid #ddd;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                    font-weight: bold;
                }}
                tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
                .positive {{
                    color: #4CAF50;
                }}
                .negative {{
                    color: #F44336;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 50px;
                    color: #777;
                    font-size: 0.9em;
                    border-top: 1px solid #eee;
                    padding-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Trading Performance Report</h1>
                <p><strong>Strategy:</strong> {metrics.get('strategy', 'N/A')} | <strong>Symbol:</strong> {metrics.get('symbol', 'N/A')} | <strong>Timeframe:</strong> {metrics.get('timeframe', 'N/A')} | <strong>Risk Profile:</strong> {metrics.get('risk_profile', 'N/A')}</p>
                <p><strong>Report Date:</strong> {metrics.get('report_date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}</p>
            </div>
            
            <div class="metrics-container">
                <div class="metric-box">
                    <div class="metric-title">Total Trades</div>
                    <div class="metric-value">{metrics.get('total_trades', 0)}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">Win Rate</div>
                    <div class="metric-value">{metrics.get('win_rate', 0):.2%}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">Total Profit</div>
                    <div class="metric-value {'' if not metrics.get('total_profit') else 'positive' if metrics.get('total_profit', 0) > 0 else 'negative'}">${metrics.get('total_profit', 0):.2f}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">ROI</div>
                    <div class="metric-value {'' if not metrics.get('roi_percent') else 'positive' if metrics.get('roi_percent', 0) > 0 else 'negative'}">{metrics.get('roi_percent', 0):.2f}%</div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">Profit Factor</div>
                    <div class="metric-value">{metrics.get('profit_factor', 0):.2f}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">Max Drawdown</div>
                    <div class="metric-value negative">{metrics.get('max_drawdown_pct', 0):.2f}%</div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">Avg Hold Time</div>
                    <div class="metric-value">{metrics.get('avg_hold_time', 0):.2f} hours</div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">Sharpe Ratio</div>
                    <div class="metric-value">{metrics.get('sharpe_ratio', 0):.2f}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">Initial Balance</div>
                    <div class="metric-value">${self.initial_balance:.2f}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">Final Balance</div>
                    <div class="metric-value {'' if not metrics.get('final_balance') else 'positive' if metrics.get('final_balance', 0) > self.initial_balance else 'negative'}">${metrics.get('final_balance', 0):.2f}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">Winning Trades</div>
                    <div class="metric-value positive">{metrics.get('winning_trades', 0)}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">Losing Trades</div>
                    <div class="metric-value negative">{metrics.get('losing_trades', 0)}</div>
                </div>
            </div>
            
            <div class="charts-container">
                <h2>Performance Charts</h2>
                
                <div class="chart">
                    <h3>Equity Curve</h3>
                    <img src="{equity_chart}" alt="Equity Curve">
                </div>
                
                <div class="chart">
                    <h3>Monthly Returns</h3>
                    <img src="{monthly_chart}" alt="Monthly Returns">
                </div>
                
                <div class="chart">
                    <h3>Win/Loss Distribution</h3>
                    <img src="{win_loss_chart}" alt="Win/Loss Distribution">
                </div>
                
                <div class="chart">
                    <h3>Trade Profit Distribution</h3>
                    <img src="{distribution_chart}" alt="Trade Profit Distribution">
                </div>
            </div>
            
            <div class="recent-trades">
                <h2>Recent Trades</h2>
                {recent_trades_table}
            </div>
            
            <div class="footer">
                <p>This report was generated automatically by Trading Bot Performance Reporter</p>
                <p>© {datetime.now().year} Trading Bot System</p>
            </div>
        </body>
        </html>
        """
        
        # Lưu báo cáo HTML
        if output_path is None:
            output_path = os.path.join(REPORTS_DIR, f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
            
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            logger.info(f"Đã tạo báo cáo HTML và lưu tại {output_path}")
            
            return output_path
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo HTML: {e}")
            return None
    
    def generate_txt_report(self, output_path: str = None) -> str:
        """
        Tạo báo cáo text đơn giản
        
        Args:
            output_path (str, optional): Đường dẫn lưu báo cáo
            
        Returns:
            str: Đường dẫn đến báo cáo text
        """
        # Tính toán các chỉ số
        metrics = self.generate_summary_metrics()
        
        # Tạo nội dung báo cáo
        report_content = f"""
========================================================
TRADING PERFORMANCE REPORT
========================================================

GENERAL INFORMATION
------------------
Strategy: {metrics.get('strategy', 'N/A')}
Symbol: {metrics.get('symbol', 'N/A')}
Timeframe: {metrics.get('timeframe', 'N/A')}
Risk Profile: {metrics.get('risk_profile', 'N/A')}
Report Date: {metrics.get('report_date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}

PERFORMANCE METRICS
------------------
Total Trades: {metrics.get('total_trades', 0)}
Winning Trades: {metrics.get('winning_trades', 0)}
Losing Trades: {metrics.get('losing_trades', 0)}
Win Rate: {metrics.get('win_rate', 0):.2%}

Total Profit: ${metrics.get('total_profit', 0):.2f}
ROI: {metrics.get('roi_percent', 0):.2f}%
Initial Balance: ${self.initial_balance:.2f}
Final Balance: ${metrics.get('final_balance', 0):.2f}

Average Profit per Trade: ${metrics.get('avg_profit', 0):.2f}
Average Win: ${metrics.get('avg_win', 0):.2f}
Average Loss: ${metrics.get('avg_loss', 0):.2f}
Profit Factor: {metrics.get('profit_factor', 0):.2f}

Max Drawdown: {metrics.get('max_drawdown_pct', 0):.2f}%
Drawdown Duration: {metrics.get('max_drawdown_duration', 0):.2f} days
Average Hold Time: {metrics.get('avg_hold_time', 0):.2f} hours
Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}

RECENT TRADES
------------------
"""
        
        # Thêm bảng giao dịch gần đây
        if self.trades_df is not None and not self.trades_df.empty:
            # Sắp xếp theo thời gian
            date_column = None
            for col in ['exit_time', 'entry_time', 'timestamp', 'time', 'date']:
                if col in self.trades_df.columns:
                    date_column = col
                    break
                    
            if date_column is not None:
                # Lấy 10 giao dịch gần nhất
                recent_trades = self.trades_df.sort_values(by=date_column, ascending=False).head(10)
                
                # Chọn các cột để hiển thị
                display_columns = [col for col in ['entry_time', 'exit_time', 'symbol', 'side', 'entry_price', 'exit_price', 'profit', 'profit_percent', 'exit_reason'] if col in recent_trades.columns]
                
                # Tạo bảng text
                recent_trades_table = tabulate(
                    recent_trades[display_columns].values,
                    headers=display_columns,
                    tablefmt="grid",
                    numalign="right",
                    floatfmt=".4f"
                )
                
                report_content += recent_trades_table
                
        report_content += """
========================================================
                Generated by Trading Bot Performance Reporter
========================================================
"""
        
        # Lưu báo cáo text
        if output_path is None:
            output_path = os.path.join(REPORTS_DIR, f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
                
            logger.info(f"Đã tạo báo cáo text và lưu tại {output_path}")
            
            return output_path
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo text: {e}")
            return None
    
    def save_metrics_to_json(self, output_path: str = None) -> str:
        """
        Lưu các chỉ số vào file JSON
        
        Args:
            output_path (str, optional): Đường dẫn lưu file JSON
            
        Returns:
            str: Đường dẫn đến file JSON
        """
        # Tính toán các chỉ số
        metrics = self.generate_summary_metrics()
        
        # Chuyển đổi datetime thành chuỗi
        for key, value in metrics.items():
            if isinstance(value, (datetime, pd.Timestamp)):
                metrics[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                
        # Lưu vào file JSON
        if output_path is None:
            output_path = os.path.join(REPORTS_DIR, f"performance_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(metrics, f, indent=4)
                
            logger.info(f"Đã lưu các chỉ số vào file JSON tại {output_path}")
            
            return output_path
        except Exception as e:
            logger.error(f"Lỗi khi lưu các chỉ số vào file JSON: {e}")
            return None

def main():
    """Hàm chính để test PerformanceReporter"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate trading performance report')
    parser.add_argument('--trades-file', type=str, help='Path to trades data file (CSV or JSON)')
    parser.add_argument('--account-file', type=str, help='Path to account history file (CSV or JSON)')
    parser.add_argument('--initial-balance', type=float, default=100.0, help='Initial account balance')
    parser.add_argument('--strategy', type=str, help='Strategy name')
    parser.add_argument('--risk-profile', type=str, help='Risk profile name')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Trading symbol')
    parser.add_argument('--timeframe', type=str, default='1h', help='Trading timeframe')
    parser.add_argument('--output-dir', type=str, help='Output directory for reports')
    parser.add_argument('--format', type=str, choices=['html', 'txt', 'json', 'all'], default='all', help='Report format')
    
    args = parser.parse_args()
    
    # Cập nhật thư mục đầu ra nếu được chỉ định
    if args.output_dir:
        global REPORTS_DIR, CHARTS_DIR
        REPORTS_DIR = os.path.join(args.output_dir, 'reports')
        CHARTS_DIR = os.path.join(args.output_dir, 'charts')
        os.makedirs(REPORTS_DIR, exist_ok=True)
        os.makedirs(CHARTS_DIR, exist_ok=True)
    
    # Khởi tạo trình tạo báo cáo
    reporter = PerformanceReporter(
        trades_file=args.trades_file,
        account_history_file=args.account_file,
        initial_balance=args.initial_balance,
        strategy_name=args.strategy,
        risk_profile=args.risk_profile,
        symbol=args.symbol,
        timeframe=args.timeframe
    )
    
    # Tạo các báo cáo theo định dạng đã chọn
    if args.format == 'html' or args.format == 'all':
        html_report = reporter.generate_html_report()
        if html_report:
            print(f"HTML report generated: {html_report}")
    
    if args.format == 'txt' or args.format == 'all':
        txt_report = reporter.generate_txt_report()
        if txt_report:
            print(f"Text report generated: {txt_report}")
    
    if args.format == 'json' or args.format == 'all':
        json_report = reporter.save_metrics_to_json()
        if json_report:
            print(f"JSON metrics saved: {json_report}")
    
    # Tạo các biểu đồ bổ sung
    equity_chart = reporter.generate_equity_curve_chart()
    monthly_chart = reporter.generate_monthly_returns_chart()
    win_loss_chart = reporter.generate_win_loss_chart()
    distribution_chart = reporter.generate_trade_distribution_chart()
    
    if equity_chart:
        print(f"Equity curve chart generated: {equity_chart}")
    if monthly_chart:
        print(f"Monthly returns chart generated: {monthly_chart}")
    if win_loss_chart:
        print(f"Win/loss distribution chart generated: {win_loss_chart}")
    if distribution_chart:
        print(f"Trade profit distribution chart generated: {distribution_chart}")

if __name__ == "__main__":
    # Kiểm tra xem module được chạy trực tiếp hay được import
    if hasattr(sys, 'ps1'):
        # Chế độ tương tác
        pass
    else:
        # Chạy qua command-line
        main()