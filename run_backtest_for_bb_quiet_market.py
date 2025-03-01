#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script chạy backtest tập trung vào chiến lược BBands trong thị trường yên tĩnh

Script này thực hiện:
1. Tạo dữ liệu mô phỏng thị trường yên tĩnh 
2. Thực hiện backtest chiến lược BBands với các tham số đã tối ưu
3. Phân tích hiệu quả của chiến lược và tạo báo cáo
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bb_quiet_market_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import các module cần thiết
try:
    from market_regime_ml_optimized import BollingerBandsStrategy, MarketRegimeDetector
except ImportError:
    logger.error("Không thể import module từ market_regime_ml_optimized.py")
    sys.exit(1)

class SimulatedMarketData:
    """Lớp tạo dữ liệu mô phỏng thị trường yên tĩnh"""
    
    @staticmethod
    def generate_quiet_market_data(days=20, base_price=60000, volatility=0.005):
        """
        Tạo dữ liệu mô phỏng thị trường yên tĩnh
        
        Args:
            days (int): Số ngày dữ liệu
            base_price (float): Giá cơ sở
            volatility (float): Mức độ biến động
            
        Returns:
            pd.DataFrame: DataFrame dữ liệu giá
        """
        # Số nến (1 ngày = 24 nến giờ)
        periods = days * 24
        
        # Khởi tạo dữ liệu thời gian
        start_date = datetime.now() - timedelta(days=days)
        date_range = pd.date_range(start=start_date, periods=periods, freq='H')
        
        # Khởi tạo chuỗi giá với random walk hẹp
        np.random.seed(42)  # Để kết quả reproducible
        returns = np.random.normal(0, volatility, periods)
        
        # Thêm xu hướng nhỏ
        trend = np.linspace(-0.002, 0.002, periods)
        returns = returns + trend
        
        # Tính giá
        prices = base_price * (1 + np.cumsum(returns))
        
        # Tạo DataFrame
        df = pd.DataFrame({
            'timestamp': date_range,
            'open': prices,
            'high': prices * (1 + np.random.uniform(0, volatility, periods)),
            'low': prices * (1 - np.random.uniform(0, volatility, periods)),
            'close': prices,
            'volume': np.random.exponential(1000, periods)
        })
        
        # Đảm bảo high >= open, close và low <= open, close
        df['high'] = df[['high', 'open', 'close']].max(axis=1)
        df['low'] = df[['low', 'open', 'close']].min(axis=1)
        
        # Thêm biến động đột ngột nhỏ (spike) để test phản ứng của chiến lược
        spike_points = np.random.choice(range(periods), size=5, replace=False)
        for point in spike_points:
            spike_direction = np.random.choice([-1, 1])
            df.loc[point, 'high'] = df.loc[point, 'high'] * (1 + spike_direction * volatility * 5)
            df.loc[point, 'low'] = df.loc[point, 'low'] * (1 - spike_direction * volatility * 5)
            df.loc[point, 'close'] = df.loc[point, 'close'] * (1 + spike_direction * volatility * 3)
        
        df.set_index('timestamp', inplace=True)
        
        logger.info(f"Đã tạo dữ liệu mô phỏng thị trường yên tĩnh với {len(df)} nến")
        
        return df

def add_indicators(df):
    """
    Thêm các chỉ báo kỹ thuật vào DataFrame
    
    Args:
        df (pd.DataFrame): DataFrame dữ liệu giá
        
    Returns:
        pd.DataFrame: DataFrame với các chỉ báo đã thêm
    """
    # Sao chép DataFrame để không thay đổi bản gốc
    df = df.copy()
    
    # Thêm Bollinger Bands
    # Sử dụng tham số tối ưu: period=30, std=0.8
    bb_period = 30
    bb_std = 0.8
    
    df['bb_middle'] = df['close'].rolling(window=bb_period).mean()
    rolling_std = df['close'].rolling(window=bb_period).std()
    df['bb_upper'] = df['bb_middle'] + (rolling_std * bb_std)
    df['bb_lower'] = df['bb_middle'] - (rolling_std * bb_std)
    
    # Thêm RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Thêm MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # Thêm Stochastic
    low_min = df['low'].rolling(window=14).min()
    high_max = df['high'].rolling(window=14).max()
    df['stoch_k'] = 100 * ((df['close'] - low_min) / (high_max - low_min))
    df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
    
    # Thêm EMA
    for period in [9, 21, 50, 200]:
        df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
    
    # Thêm ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = true_range.rolling(window=14).mean()
    
    # Thêm ADX
    plus_dm = df['high'].diff()
    minus_dm = df['low'].diff()
    plus_dm = plus_dm.where((plus_dm > 0) & (plus_dm > minus_dm * -1), 0)
    minus_dm = minus_dm.where((minus_dm < 0) & (minus_dm * -1 > plus_dm), 0)
    tr = true_range
    
    plus_di = 100 * (plus_dm.ewm(alpha=1/14, adjust=False).mean() / tr.ewm(alpha=1/14, adjust=False).mean())
    minus_di = abs(100 * (minus_dm.ewm(alpha=1/14, adjust=False).mean() / tr.ewm(alpha=1/14, adjust=False).mean()))
    dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
    df['adx'] = dx.ewm(alpha=1/14, adjust=False).mean()
    df['plus_di'] = plus_di
    df['minus_di'] = minus_di
    
    # Tính BB width
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    
    return df

class BBQuietMarketTester:
    """Lớp test chiến lược BBands trong thị trường yên tĩnh"""
    
    def __init__(self, data_df=None, initial_balance=10000):
        """
        Khởi tạo tester
        
        Args:
            data_df (pd.DataFrame, optional): DataFrame dữ liệu giá
            initial_balance (float): Số dư ban đầu
        """
        self.data_df = data_df
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity_curve = [initial_balance]
        self.trades = []
        
        # Khởi tạo chiến lược
        self.bb_strategy = BollingerBandsStrategy(params={
            'bb_period': 30,
            'bb_std': 0.8,
            'use_bb_squeeze': True
        })
        
        # Khởi tạo bộ phát hiện chế độ thị trường
        self.regime_detector = MarketRegimeDetector()
    
    def run_backtest(self):
        """Chạy backtest chiến lược BBands"""
        if self.data_df is None or self.data_df.empty:
            logger.error("Không có dữ liệu để chạy backtest")
            return False
        
        # Thêm chỉ báo vào dữ liệu nếu chưa có
        df = add_indicators(self.data_df) if 'bb_upper' not in self.data_df.columns else self.data_df
        
        # Số dư hiện tại
        current_balance = self.initial_balance
        
        # Vị thế hiện tại (None = không có vị thế)
        current_position = None
        
        # Ghi nhận tổng quát
        total_trades = 0
        winning_trades = 0
        total_profit = 0
        total_loss = 0
        max_drawdown = 0
        max_balance = self.initial_balance
        
        # Danh sách lưu kết quả
        results = []
        
        # Vòng lặp qua từng nến
        for i in range(50, len(df)-1):  # Bỏ qua 50 nến đầu để có đủ dữ liệu cho các chỉ báo
            # Chuẩn bị dữ liệu
            current_data = df.iloc[:i+1]
            
            # Phát hiện chế độ thị trường
            regime = self.regime_detector.detect_regime(current_data)
            
            # Lấy tín hiệu từ chiến lược BBands
            signal = self.bb_strategy.generate_signal(current_data)
            
            # Thực hiện giao dịch nếu có tín hiệu
            current_price = current_data['close'].iloc[-1]
            current_timestamp = current_data.index[-1]
            
            # Ghi nhận kết quả
            result = {
                'timestamp': current_timestamp,
                'price': current_price,
                'regime': regime,
                'signal': signal,
                'balance': current_balance,
                'position': 'NONE' if current_position is None else current_position['side']
            }
            
            # Nếu đang có vị thế, kiểm tra điều kiện đóng vị thế
            if current_position is not None:
                # Tính lãi/lỗ hiện tại
                if current_position['side'] == 'BUY':
                    profit_pct = (current_price - current_position['entry_price']) / current_position['entry_price']
                else:  # SELL
                    profit_pct = (current_position['entry_price'] - current_price) / current_position['entry_price']
                
                profit_amount = current_position['amount'] * profit_pct
                result['unrealized_profit'] = profit_amount
                
                # Kiểm tra điều kiện Take Profit
                take_profit_reached = profit_pct >= current_position['take_profit_pct']
                
                # Kiểm tra điều kiện Stop Loss
                stop_loss_reached = profit_pct <= -current_position['stop_loss_pct']
                
                # Kiểm tra tín hiệu ngược
                reverse_signal = (current_position['side'] == 'BUY' and signal == -1) or \
                                (current_position['side'] == 'SELL' and signal == 1)
                
                # Đóng vị thế nếu đạt điều kiện
                if take_profit_reached or stop_loss_reached or reverse_signal:
                    # Tính lãi/lỗ
                    if current_position['side'] == 'BUY':
                        profit = current_position['amount'] * (current_price - current_position['entry_price']) / current_position['entry_price']
                    else:  # SELL
                        profit = current_position['amount'] * (current_position['entry_price'] - current_price) / current_position['entry_price']
                    
                    # Cập nhật số dư
                    current_balance += profit
                    
                    # Ghi nhận thông tin giao dịch
                    trade_info = {
                        'entry_time': current_position['entry_time'],
                        'exit_time': current_timestamp,
                        'side': current_position['side'],
                        'entry_price': current_position['entry_price'],
                        'exit_price': current_price,
                        'amount': current_position['amount'],
                        'profit': profit,
                        'profit_pct': profit_pct * 100,
                        'exit_reason': 'Take Profit' if take_profit_reached else 'Stop Loss' if stop_loss_reached else 'Reverse Signal'
                    }
                    
                    self.trades.append(trade_info)
                    
                    # Cập nhật tổng quát
                    total_trades += 1
                    if profit > 0:
                        winning_trades += 1
                        total_profit += profit
                    else:
                        total_loss -= profit  # Chuyển thành số dương
                    
                    # Cập nhật max_balance và max_drawdown
                    max_balance = max(max_balance, current_balance)
                    drawdown = (max_balance - current_balance) / max_balance
                    max_drawdown = max(max_drawdown, drawdown)
                    
                    # Đặt lại vị thế
                    current_position = None
                    
                    # Ghi nhận kết quả
                    result['trade_closed'] = True
                    result['trade_info'] = trade_info
                    result['balance'] = current_balance
                    result['position'] = 'NONE'
            
            # Mở vị thế mới nếu có tín hiệu và không có vị thế hiện tại
            if current_position is None and signal != 0 and regime == 'quiet':
                # Tham số quản lý rủi ro
                risk_percentage = 0.5  # 0.5% của số dư trên mỗi giao dịch
                take_profit_pct = 1.0  # 1.0% lợi nhuận
                stop_loss_pct = 0.5    # 0.5% cắt lỗ
                
                # Tính toán kích thước vị thế
                amount = current_balance * risk_percentage / 100
                
                # Mở vị thế
                current_position = {
                    'side': 'BUY' if signal == 1 else 'SELL',
                    'entry_price': current_price,
                    'amount': amount,
                    'entry_time': current_timestamp,
                    'take_profit_pct': take_profit_pct / 100,
                    'stop_loss_pct': stop_loss_pct / 100
                }
                
                # Ghi nhận kết quả
                result['trade_opened'] = True
                result['position'] = current_position['side']
            
            # Cập nhật equity curve
            self.equity_curve.append(current_balance)
            
            # Lưu kết quả
            results.append(result)
        
        # Tính hiệu suất cuối cùng
        if total_trades > 0:
            win_rate = winning_trades / total_trades * 100
            profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
            avg_profit = total_profit / winning_trades if winning_trades > 0 else 0
            avg_loss = total_loss / (total_trades - winning_trades) if (total_trades - winning_trades) > 0 else 0
            roi = (current_balance - self.initial_balance) / self.initial_balance * 100
        else:
            win_rate = 0
            profit_factor = 0
            avg_profit = 0
            avg_loss = 0
            roi = 0
        
        # Lưu kết quả tổng quát
        self.performance = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'max_drawdown': max_drawdown * 100,
            'roi': roi,
            'final_balance': current_balance
        }
        
        self.results = results
        
        logger.info(f"Đã hoàn thành backtest với {total_trades} giao dịch")
        logger.info(f"Win rate: {win_rate:.2f}%, ROI: {roi:.2f}%, Drawdown: {max_drawdown*100:.2f}%")
        
        return True
    
    def create_charts(self, output_dir='backtest_charts'):
        """
        Tạo biểu đồ kết quả backtest
        
        Args:
            output_dir (str): Thư mục lưu biểu đồ
        """
        if not hasattr(self, 'results') or not self.results:
            logger.error("Chưa có kết quả backtest để tạo biểu đồ")
            return
        
        # Đảm bảo thư mục tồn tại
        os.makedirs(output_dir, exist_ok=True)
        
        # Chuyển đổi kết quả thành DataFrame
        results_df = pd.DataFrame(self.results)
        
        # Biểu đồ giá và Bollinger Bands
        plt.figure(figsize=(12, 8))
        plt.plot(self.data_df.index, self.data_df['close'], label='Close Price')
        plt.plot(self.data_df.index, self.data_df['bb_upper'], 'r--', label='Upper BB')
        plt.plot(self.data_df.index, self.data_df['bb_middle'], 'g--', label='Middle BB')
        plt.plot(self.data_df.index, self.data_df['bb_lower'], 'b--', label='Lower BB')
        
        # Vẽ điểm mua/bán
        buy_signals = results_df[results_df['trade_opened'] == True][results_df['position'] == 'BUY']
        sell_signals = results_df[results_df['trade_opened'] == True][results_df['position'] == 'SELL']
        
        plt.scatter(buy_signals['timestamp'], buy_signals['price'], color='green', marker='^', s=100, label='Buy Signal')
        plt.scatter(sell_signals['timestamp'], sell_signals['price'], color='red', marker='v', s=100, label='Sell Signal')
        
        plt.title('BBands Strategy in Quiet Market - Price and Signals')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()
        plt.grid(True)
        
        # Lưu biểu đồ
        price_chart_path = os.path.join(output_dir, 'bb_quiet_price_chart.png')
        plt.savefig(price_chart_path)
        plt.close()
        
        # Biểu đồ equity curve
        plt.figure(figsize=(12, 6))
        plt.plot(self.equity_curve)
        plt.title('Equity Curve')
        plt.xlabel('Candles')
        plt.ylabel('Balance')
        plt.grid(True)
        
        # Lưu biểu đồ
        equity_chart_path = os.path.join(output_dir, 'bb_quiet_equity_curve.png')
        plt.savefig(equity_chart_path)
        plt.close()
        
        # Biểu đồ BB Width
        plt.figure(figsize=(12, 6))
        plt.plot(self.data_df.index, self.data_df['bb_width'])
        plt.axhline(y=0.03, color='r', linestyle='--', label='Quiet Market Threshold (3%)')
        plt.title('Bollinger Bands Width')
        plt.xlabel('Date')
        plt.ylabel('BB Width')
        plt.legend()
        plt.grid(True)
        
        # Lưu biểu đồ
        bb_width_chart_path = os.path.join(output_dir, 'bb_quiet_width_chart.png')
        plt.savefig(bb_width_chart_path)
        plt.close()
        
        # Biểu đồ phân bố lợi nhuận
        if self.trades:
            profits = [trade['profit'] for trade in self.trades]
            plt.figure(figsize=(10, 6))
            plt.hist(profits, bins=20)
            plt.axvline(x=0, color='r', linestyle='--')
            plt.title('Profit Distribution')
            plt.xlabel('Profit')
            plt.ylabel('Frequency')
            plt.grid(True)
            
            # Lưu biểu đồ
            profit_dist_path = os.path.join(output_dir, 'bb_quiet_profit_distribution.png')
            plt.savefig(profit_dist_path)
            plt.close()
        
        logger.info(f"Đã tạo biểu đồ kết quả backtest trong thư mục: {output_dir}")
    
    def create_report(self, output_dir='reports'):
        """
        Tạo báo cáo kết quả backtest
        
        Args:
            output_dir (str): Thư mục lưu báo cáo
        """
        if not hasattr(self, 'performance') or not self.performance:
            logger.error("Chưa có kết quả backtest để tạo báo cáo")
            return
        
        # Đảm bảo thư mục tồn tại
        os.makedirs(output_dir, exist_ok=True)
        
        # Tạo báo cáo JSON
        report_data = {
            'test_time': datetime.now().isoformat(),
            'data_info': {
                'periods': len(self.data_df),
                'start_date': self.data_df.index[0].isoformat(),
                'end_date': self.data_df.index[-1].isoformat(),
                'average_bb_width': float(self.data_df['bb_width'].mean())
            },
            'strategy_params': {
                'bb_period': 30,
                'bb_std': 0.8,
                'use_bb_squeeze': True,
                'risk_percentage': 0.5,
                'take_profit_pct': 1.0,
                'stop_loss_pct': 0.5
            },
            'performance': self.performance,
            'trades': self.trades
        }
        
        # Lưu báo cáo JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_report_path = os.path.join(output_dir, f'bb_quiet_market_report_{timestamp}.json')
        
        with open(json_report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=4, default=str)
        
        # Tạo báo cáo văn bản
        text_report = []
        text_report.append("="*80)
        text_report.append(f"BÁO CÁO BACKTEST CHIẾN LƯỢC BBANDS TRONG THỊ TRƯỜNG YÊN TĨNH")
        text_report.append("="*80)
        text_report.append(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        text_report.append("")
        
        text_report.append("THÔNG TIN DỮ LIỆU:")
        text_report.append(f"- Số nến: {len(self.data_df)}")
        text_report.append(f"- Bắt đầu: {self.data_df.index[0].strftime('%Y-%m-%d %H:%M:%S')}")
        text_report.append(f"- Kết thúc: {self.data_df.index[-1].strftime('%Y-%m-%d %H:%M:%S')}")
        text_report.append(f"- BB Width trung bình: {self.data_df['bb_width'].mean():.4f}")
        text_report.append("")
        
        text_report.append("THAM SỐ CHIẾN LƯỢC:")
        text_report.append("- BBands period: 30")
        text_report.append("- BBands std: 0.8")
        text_report.append("- Sử dụng BB squeeze: True")
        text_report.append("- Risk percentage: 0.5%")
        text_report.append("- Take profit: 1.0%")
        text_report.append("- Stop loss: 0.5%")
        text_report.append("")
        
        text_report.append("KẾT QUẢ HIỆU SUẤT:")
        text_report.append(f"- Số lượng giao dịch: {self.performance['total_trades']}")
        text_report.append(f"- Số giao dịch thắng: {self.performance['winning_trades']}")
        text_report.append(f"- Tỷ lệ thắng: {self.performance['win_rate']:.2f}%")
        text_report.append(f"- Profit factor: {self.performance['profit_factor']:.2f}")
        text_report.append(f"- Lợi nhuận trung bình: {self.performance['avg_profit']:.2f}")
        text_report.append(f"- Lỗ trung bình: {self.performance['avg_loss']:.2f}")
        text_report.append(f"- Drawdown tối đa: {self.performance['max_drawdown']:.2f}%")
        text_report.append(f"- ROI: {self.performance['roi']:.2f}%")
        text_report.append(f"- Số dư cuối: {self.performance['final_balance']:.2f}")
        text_report.append("")
        
        if self.trades:
            text_report.append("GIAO DỊCH GẦN ĐÂY:")
            for i, trade in enumerate(self.trades[-5:], 1):
                text_report.append(f"Giao dịch {i}:")
                text_report.append(f"- Vào: {trade['entry_time'].strftime('%Y-%m-%d %H:%M:%S')} @ {trade['entry_price']:.2f}")
                text_report.append(f"- Ra: {trade['exit_time'].strftime('%Y-%m-%d %H:%M:%S')} @ {trade['exit_price']:.2f}")
                text_report.append(f"- Hướng: {trade['side']}")
                text_report.append(f"- Lợi nhuận: {trade['profit']:.2f} ({trade['profit_pct']:.2f}%)")
                text_report.append(f"- Lý do thoát: {trade['exit_reason']}")
                text_report.append("")
            
        text_report.append("ĐÁNH GIÁ:")
        win_rate = self.performance['win_rate']
        roi = self.performance['roi']
        
        if win_rate >= 60 and roi > 0:
            text_report.append("✓ Chiến lược BBands hoạt động HIỆU QUẢ trong thị trường yên tĩnh")
        elif win_rate >= 50 and roi > 0:
            text_report.append("✓ Chiến lược BBands hoạt động KHÁ HIỆU QUẢ trong thị trường yên tĩnh")
        elif roi > 0:
            text_report.append("⚠ Chiến lược BBands hoạt động CÓ LỢI NHUẬN nhưng tỷ lệ thắng thấp")
        else:
            text_report.append("✗ Chiến lược BBands hoạt động KHÔNG HIỆU QUẢ trong thị trường yên tĩnh")
        
        text_report.append("")
        text_report.append("KIẾN NGHỊ:")
        
        if win_rate < 50:
            text_report.append("- Cần tăng ngưỡng xác nhận khi phát hiện tín hiệu để giảm số lượng giao dịch false positive")
        
        if self.performance['avg_profit'] < self.performance['avg_loss']:
            text_report.append("- Cần điều chỉnh tỷ lệ take profit/stop loss để cải thiện Reward:Risk ratio")
        
        if self.performance['max_drawdown'] > 5:
            text_report.append("- Cần giảm kích thước vị thế để kiểm soát drawdown tốt hơn")
        
        if roi < 0:
            text_report.append("- Xem xét việc kết hợp với các chỉ báo khác để cải thiện hiệu suất")
        
        text_report.append("="*80)
        
        # Lưu báo cáo văn bản
        text_report_path = os.path.join(output_dir, f'bb_quiet_market_report_{timestamp}.txt')
        
        with open(text_report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(text_report))
        
        logger.info(f"Đã tạo báo cáo JSON: {json_report_path}")
        logger.info(f"Đã tạo báo cáo văn bản: {text_report_path}")
        
        return {
            'json_report': json_report_path,
            'text_report': text_report_path
        }

def main():
    # Tạo dữ liệu thị trường yên tĩnh
    market_data = SimulatedMarketData.generate_quiet_market_data(days=20, base_price=60000, volatility=0.005)
    
    # Thêm các chỉ báo kỹ thuật
    data_with_indicators = add_indicators(market_data)
    
    # Khởi tạo tester
    tester = BBQuietMarketTester(data_df=data_with_indicators, initial_balance=10000)
    
    # Chạy backtest
    tester.run_backtest()
    
    # Tạo biểu đồ
    tester.create_charts()
    
    # Tạo báo cáo
    tester.create_report()

if __name__ == "__main__":
    main()