#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script chạy tất cả chiến lược và đánh giá hiệu quả trong 3 tháng
Đánh giá toàn diện từng chiến lược và kết hợp
"""

import os
import sys
import logging
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('3month_all_strategies_test.log')
    ]
)

logger = logging.getLogger('three_month_test')

# Import các module chiến lược
try:
    from multi_risk_strategy import MultiRiskStrategy
    from sideways_market_strategy import SidewaysMarketStrategy
    from adaptive_risk_allocation import AdaptiveRiskAllocator
    from adaptive_risk_manager import AdaptiveRiskManager
    from utils.data_loader import DataLoader
    from utils.performance_analyzer import PerformanceAnalyzer
except ImportError as e:
    logger.error(f"Lỗi import module: {e}")
    sys.exit(1)

class AllStrategiesBacktest:
    """
    Class thực hiện backtest tất cả chiến lược và tổng hợp kết quả
    """
    
    def __init__(self, timeframe='1h', test_period=90, symbols=None):
        """
        Khởi tạo backtest cho tất cả chiến lược
        
        Args:
            timeframe (str): Khung thời gian ('1h', '4h', '1d')
            test_period (int): Số ngày backtest
            symbols (list): Danh sách cặp tiền, mặc định là ['BTCUSDT']
        """
        self.timeframe = timeframe
        self.test_period = test_period
        self.symbols = symbols or ['BTCUSDT']
        self.result_dir = Path('3month_test_results')
        
        # Tạo thư mục kết quả nếu chưa tồn tại
        if not self.result_dir.exists():
            os.makedirs(self.result_dir)
        
        # Lưu timestamp bắt đầu backtest
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Khởi tạo DataLoader
        self.data_loader = DataLoader()
        
        # Khởi tạo PerformanceAnalyzer
        self.performance_analyzer = PerformanceAnalyzer()
        
        logger.info(f"Khởi tạo backtest cho {len(self.symbols)} cặp tiền, khung thời gian {timeframe}, thời gian {test_period} ngày")
    
    def load_market_data(self, symbol):
        """
        Tải dữ liệu thị trường cho cặp tiền
        
        Args:
            symbol (str): Cặp tiền
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu thị trường
        """
        # Tính toán ngày bắt đầu và kết thúc
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.test_period)
        
        # Định dạng ngày
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        logger.info(f"Tải dữ liệu {symbol} từ {start_str} đến {end_str}")
        
        # Dữ liệu 1h từ file
        file_path = f"data/{symbol}_{self.timeframe}_data.csv"
        
        if os.path.exists(file_path):
            logger.info(f"Đang tải dữ liệu từ {file_path}")
            df = pd.read_csv(file_path)
            
            # Xử lý timestamp
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            
            # Đảm bảo tên cột chuẩn
            if 'open' in df.columns and 'Open' not in df.columns:
                df = df.rename(columns={
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                })
            
            # Lấy subset của dữ liệu trong khoảng thời gian
            if isinstance(df.index, pd.DatetimeIndex):
                df = df.loc[start_date:end_date]
            
            logger.info(f"Đã tải {len(df)} nến cho {symbol}")
            return df
        else:
            logger.error(f"Không tìm thấy file dữ liệu {file_path}")
            return None
    
    def run_multi_risk_strategy(self, data, risk_level):
        """
        Chạy backtest chiến lược đa rủi ro
        
        Args:
            data (pd.DataFrame): DataFrame chứa dữ liệu thị trường
            risk_level (float): Mức rủi ro
            
        Returns:
            dict: Kết quả backtest
        """
        logger.info(f"Bắt đầu backtest chiến lược multi_risk với risk_level={risk_level}")
        
        # Khởi tạo chiến lược
        strategy = MultiRiskStrategy(risk_level=risk_level)
        
        # Tính toán các chỉ báo
        df_with_indicators = strategy.calculate_indicators(data)
        
        # Tạo tín hiệu giao dịch
        signals = strategy.generate_signals(df_with_indicators)
        
        # Mô phỏng giao dịch
        trades, equity_curve, stats = self._simulate_trades(data, signals, risk_level)
        
        logger.info(f"Kết quả backtest chiến lược multi_risk (risk={risk_level}): P/L: {stats['profit_pct']:.2f}%, Win Rate: {stats['win_rate']:.2f}%, Trades: {stats['total_trades']}, Max DD: {stats['max_drawdown_pct']:.2f}%")
        
        return {
            'strategy': f'multi_risk_{int(risk_level*100)}',
            'trades': trades,
            'equity_curve': equity_curve,
            'stats': stats,
            'signals': signals
        }
    
    def run_sideways_strategy(self, data, risk_level):
        """
        Chạy backtest chiến lược cho thị trường đi ngang
        
        Args:
            data (pd.DataFrame): DataFrame chứa dữ liệu thị trường
            risk_level (float): Mức rủi ro
            
        Returns:
            dict: Kết quả backtest
        """
        logger.info(f"Bắt đầu backtest chiến lược sideways với risk_level={risk_level}")
        
        # Khởi tạo chiến lược
        strategy = SidewaysMarketStrategy(data=data, risk_level=risk_level)
        
        # Tạo tín hiệu giao dịch
        signals = strategy.generate_signals()
        
        # Mô phỏng giao dịch
        trades, equity_curve, stats = self._simulate_trades(data, signals, risk_level)
        
        logger.info(f"Kết quả backtest chiến lược sideways (risk={risk_level}): P/L: {stats['profit_pct']:.2f}%, Win Rate: {stats['win_rate']:.2f}%, Trades: {stats['total_trades']}, Max DD: {stats['max_drawdown_pct']:.2f}%")
        
        return {
            'strategy': f'sideways_{int(risk_level*100)}',
            'trades': trades,
            'equity_curve': equity_curve,
            'stats': stats,
            'signals': signals
        }
    
    def run_adaptive_strategy(self, data):
        """
        Chạy backtest chiến lược thích ứng đa rủi ro
        
        Args:
            data (pd.DataFrame): DataFrame chứa dữ liệu thị trường
            
        Returns:
            dict: Kết quả backtest
        """
        logger.info(f"Bắt đầu backtest chiến lược thích ứng đa rủi ro")
        
        # Khởi tạo risk allocator
        risk_allocator = AdaptiveRiskAllocator()
        
        # Khởi tạo bộ quản lý rủi ro thích ứng
        risk_manager = AdaptiveRiskManager()
        
        # Lưu tín hiệu giao dịch
        all_signals = {}
        current_index = 0
        
        # Phân bổ vốn cho từng chiến lược
        capital_allocation = {
            0.10: 0.20,  # 20% vốn cho chiến lược rủi ro 10%
            0.15: 0.20,  # 20% vốn cho chiến lược rủi ro 15%
            0.20: 0.20,  # 20% vốn cho chiến lược rủi ro 20%
            0.25: 0.10,  # 10% vốn cho chiến lược rủi ro 25%
        }
        
        # Khởi tạo danh sách vị thế mở
        open_positions = []
        equity_curve = [1.0]  # Bắt đầu với 100% vốn
        trades = []
        
        # Mô phỏng giao dịch theo thời gian
        for i in range(1, len(data)):
            current_date = data.index[i]
            current_price = data['Close'].iloc[i]
            
            # Xác định điều kiện thị trường
            if i % 24 == 0:  # Cập nhật điều kiện thị trường mỗi 24 giờ
                market_condition = self._detect_market_condition(data.iloc[max(0, i-50):i])
                optimal_risk = risk_manager.get_optimal_risk(market_condition)
                logger.debug(f"Ngày {current_date}: Thị trường {market_condition}, rủi ro tối ưu {optimal_risk}")
            
            # Mở vị thế mới dựa trên tín hiệu
            for risk_level in [0.10, 0.15, 0.20, 0.25]:
                # Chỉ xem xét mức rủi ro gần với rủi ro tối ưu
                if abs(risk_level - optimal_risk) <= 0.05:
                    # Tạo tín hiệu từ chiến lược phù hợp
                    if market_condition == 'SIDEWAYS':
                        strategy = SidewaysMarketStrategy(data=data.iloc[:i+1], risk_level=risk_level)
                        signals = strategy.generate_signals()
                    else:
                        strategy = MultiRiskStrategy(risk_level=risk_level)
                        with_indicators = strategy.calculate_indicators(data.iloc[:i+1])
                        signals = strategy.generate_signals(with_indicators)
                    
                    # Kiểm tra tín hiệu tại thời điểm hiện tại
                    if i in signals:
                        signal = signals[i]
                        position_size = capital_allocation[risk_level] * risk_level  # Kích thước vị thế dựa trên phân bổ vốn
                        
                        # Mở vị thế mới
                        open_positions.append({
                            'entry_index': i,
                            'entry_date': current_date,
                            'entry_price': current_price,
                            'type': signal['type'],
                            'stop_loss': signal['stop_loss'],
                            'take_profit': signal['take_profit'],
                            'risk_level': risk_level,
                            'position_size': position_size,
                            'market_condition': market_condition
                        })
                        logger.debug(f"Mở {signal['type']} tại {current_price} (risk={risk_level}, condition={market_condition})")
            
            # Kiểm tra và đóng các vị thế
            j = 0
            while j < len(open_positions):
                position = open_positions[j]
                
                # Tính P/L
                if position['type'] == 'LONG':
                    pnl_pct = (current_price - position['entry_price']) / position['entry_price']
                else:  # SHORT
                    pnl_pct = (position['entry_price'] - current_price) / position['entry_price']
                
                # Kiểm tra điều kiện đóng vị thế
                close_position = False
                reason = ''
                
                # Stop loss
                if position['type'] == 'LONG' and current_price <= position['stop_loss']:
                    close_position = True
                    reason = 'Stop Loss'
                elif position['type'] == 'SHORT' and current_price >= position['stop_loss']:
                    close_position = True
                    reason = 'Stop Loss'
                
                # Take profit
                elif position['type'] == 'LONG' and current_price >= position['take_profit']:
                    close_position = True
                    reason = 'Take Profit'
                elif position['type'] == 'SHORT' and current_price <= position['take_profit']:
                    close_position = True
                    reason = 'Take Profit'
                
                # Đóng vị thế nếu có điều kiện
                if close_position:
                    # Lưu thông tin giao dịch
                    trade = {
                        'entry_date': position['entry_date'],
                        'entry_price': position['entry_price'],
                        'exit_date': current_date,
                        'exit_price': current_price,
                        'type': position['type'],
                        'pnl_pct': pnl_pct * 100,  # Chuyển sang phần trăm
                        'risk_level': position['risk_level'],
                        'reason': reason,
                        'market_condition': position['market_condition']
                    }
                    trades.append(trade)
                    
                    # Cập nhật equity curve
                    equity_change = pnl_pct * position['position_size']
                    equity_curve.append(equity_curve[-1] * (1 + equity_change))
                    
                    logger.debug(f"Đóng {position['type']} tại {current_price}, P/L: {pnl_pct*100:.2f}%, Lý do: {reason}")
                    
                    # Xóa vị thế
                    open_positions.pop(j)
                else:
                    j += 1
            
            # Cập nhật equity curve nếu không có giao dịch nào đóng
            if len(equity_curve) <= i:
                equity_curve.append(equity_curve[-1])
        
        # Tính toán thống kê
        stats = self._calculate_stats(trades, equity_curve)
        
        logger.info(f"Kết quả backtest chiến lược thích ứng đa rủi ro: P/L: {stats['profit_pct']:.2f}%, Win Rate: {stats['win_rate']:.2f}%, Trades: {stats['total_trades']}, Max DD: {stats['max_drawdown_pct']:.2f}%")
        
        return {
            'strategy': 'adaptive_multi_risk',
            'trades': trades,
            'equity_curve': equity_curve,
            'stats': stats
        }
    
    def _simulate_trades(self, data, signals, risk_level):
        """
        Mô phỏng giao dịch dựa trên tín hiệu
        
        Args:
            data (pd.DataFrame): DataFrame chứa dữ liệu thị trường
            signals (dict): Dictionary chứa tín hiệu giao dịch
            risk_level (float): Mức rủi ro
            
        Returns:
            tuple: (trades, equity_curve, stats)
        """
        # Khởi tạo danh sách giao dịch và equity curve
        trades = []
        equity_curve = [1.0]  # Bắt đầu với 100% vốn
        
        # Khởi tạo danh sách vị thế mở
        open_positions = []
        
        # Mô phỏng giao dịch
        for i in range(1, len(data)):
            current_price = data['Close'].iloc[i]
            current_date = data.index[i]
            
            # Mở vị thế mới nếu có tín hiệu
            if i in signals:
                signal = signals[i]
                
                # Thêm vị thế mới vào danh sách vị thế mở
                open_positions.append({
                    'entry_index': i,
                    'entry_date': current_date,
                    'entry_price': current_price,
                    'type': signal['type'],
                    'stop_loss': signal['stop_loss'],
                    'take_profit': signal['take_profit']
                })
            
            # Kiểm tra và đóng các vị thế
            j = 0
            while j < len(open_positions):
                position = open_positions[j]
                
                # Tính P/L
                if position['type'] == 'LONG':
                    pnl_pct = (current_price - position['entry_price']) / position['entry_price']
                else:  # SHORT
                    pnl_pct = (position['entry_price'] - current_price) / position['entry_price']
                
                # Kiểm tra điều kiện đóng vị thế
                close_position = False
                reason = ''
                
                # Stop loss
                if position['type'] == 'LONG' and current_price <= position['stop_loss']:
                    close_position = True
                    reason = 'Stop Loss'
                elif position['type'] == 'SHORT' and current_price >= position['stop_loss']:
                    close_position = True
                    reason = 'Stop Loss'
                
                # Take profit
                elif position['type'] == 'LONG' and current_price >= position['take_profit']:
                    close_position = True
                    reason = 'Take Profit'
                elif position['type'] == 'SHORT' and current_price <= position['take_profit']:
                    close_position = True
                    reason = 'Take Profit'
                
                # Đóng vị thế nếu có điều kiện
                if close_position:
                    # Lưu thông tin giao dịch
                    trade = {
                        'entry_date': position['entry_date'],
                        'entry_price': position['entry_price'],
                        'exit_date': current_date,
                        'exit_price': current_price,
                        'type': position['type'],
                        'pnl_pct': pnl_pct * 100,  # Chuyển sang phần trăm
                        'reason': reason
                    }
                    trades.append(trade)
                    
                    # Cập nhật equity curve
                    equity_change = pnl_pct * risk_level
                    equity_curve.append(equity_curve[-1] * (1 + equity_change))
                    
                    # Xóa vị thế
                    open_positions.pop(j)
                else:
                    j += 1
            
            # Cập nhật equity curve nếu không có giao dịch nào đóng
            if len(equity_curve) <= i:
                equity_curve.append(equity_curve[-1])
        
        # Tính toán thống kê
        stats = self._calculate_stats(trades, equity_curve)
        
        return trades, equity_curve, stats
    
    def _calculate_stats(self, trades, equity_curve):
        """
        Tính toán thống kê từ danh sách giao dịch và equity curve
        
        Args:
            trades (list): Danh sách giao dịch
            equity_curve (list): Đường vốn
            
        Returns:
            dict: Thống kê giao dịch
        """
        # Số lượng giao dịch
        total_trades = len(trades)
        
        if total_trades == 0:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'profit_pct': 0,
                'max_drawdown_pct': 0,
                'average_win_pct': 0,
                'average_loss_pct': 0,
                'profit_factor': 0,
                'recovery_factor': 0
            }
        
        # Số lượng giao dịch thắng và thua
        winning_trades = [t for t in trades if t['pnl_pct'] > 0]
        losing_trades = [t for t in trades if t['pnl_pct'] <= 0]
        
        # Tỷ lệ thắng
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        # Lợi nhuận
        profit_pct = 100 * (equity_curve[-1] - equity_curve[0]) / equity_curve[0]
        
        # Drawdown tối đa
        drawdowns = []
        peak = equity_curve[0]
        for value in equity_curve:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100
            drawdowns.append(drawdown)
        max_drawdown_pct = max(drawdowns)
        
        # Trung bình lợi nhuận của giao dịch thắng và thua
        average_win_pct = sum([t['pnl_pct'] for t in winning_trades]) / len(winning_trades) if winning_trades else 0
        average_loss_pct = sum([t['pnl_pct'] for t in losing_trades]) / len(losing_trades) if losing_trades else 0
        
        # Profit factor
        gross_profit = sum([t['pnl_pct'] for t in winning_trades]) if winning_trades else 0
        gross_loss = abs(sum([t['pnl_pct'] for t in losing_trades])) if losing_trades else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Recovery factor
        recovery_factor = profit_pct / max_drawdown_pct if max_drawdown_pct > 0 else float('inf')
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_pct': profit_pct,
            'max_drawdown_pct': max_drawdown_pct,
            'average_win_pct': average_win_pct,
            'average_loss_pct': average_loss_pct,
            'profit_factor': profit_factor,
            'recovery_factor': recovery_factor
        }
    
    def _detect_market_condition(self, data):
        """
        Phát hiện điều kiện thị trường dựa trên dữ liệu giá
        
        Args:
            data (pd.DataFrame): DataFrame chứa dữ liệu thị trường
            
        Returns:
            str: Điều kiện thị trường ('BULL', 'BEAR', 'SIDEWAYS', 'VOLATILE')
        """
        if len(data) < 20:
            return 'NEUTRAL'
        
        # Tính toán biến động giá
        price_change = (data['Close'].iloc[-1] - data['Close'].iloc[0]) / data['Close'].iloc[0] * 100
        
        # Tính toán volatility
        returns = data['Close'].pct_change().dropna()
        volatility = returns.std() * 100
        
        # Xác định điều kiện thị trường
        if price_change > 5:  # Tăng > 5%
            if volatility > 3:
                return 'VOLATILE'
            else:
                return 'BULL'
        elif price_change < -5:  # Giảm > 5%
            if volatility > 3:
                return 'VOLATILE'
            else:
                return 'BEAR'
        else:  # Đi ngang
            if volatility > 2:
                return 'VOLATILE'
            else:
                return 'SIDEWAYS'
    
    def plot_results(self, symbol, results):
        """
        Vẽ biểu đồ kết quả
        
        Args:
            symbol (str): Cặp tiền
            results (list): Danh sách kết quả backtest
        """
        plt.figure(figsize=(14, 8))
        
        # Vẽ equity curve cho từng chiến lược
        for result in results:
            label = f"{result['strategy']} (P/L: {result['stats']['profit_pct']:.2f}%, Win: {result['stats']['win_rate']:.2f}%)"
            plt.plot(result['equity_curve'], label=label)
        
        plt.title(f'So sánh hiệu suất các chiến lược - {symbol} {self.timeframe} ({self.test_period} ngày)')
        plt.xlabel('Candle Index')
        plt.ylabel('Equity (starting at 1.0)')
        plt.legend()
        plt.grid(True)
        
        # Lưu biểu đồ
        plt.savefig(self.result_dir / f"{symbol}_{self.timeframe}_all_strategies_comparison.png")
        logger.info(f"Đã lưu biểu đồ so sánh tại {self.result_dir / f'{symbol}_{self.timeframe}_all_strategies_comparison.png'}")
        
        # Vẽ biểu đồ từng chiến lược riêng
        for result in results:
            plt.figure(figsize=(14, 6))
            plt.plot(result['equity_curve'])
            plt.title(f"{result['strategy']} - {symbol} {self.timeframe} (P/L: {result['stats']['profit_pct']:.2f}%, Win: {result['stats']['win_rate']:.2f}%)")
            plt.xlabel('Candle Index')
            plt.ylabel('Equity (starting at 1.0)')
            plt.grid(True)
            plt.savefig(self.result_dir / f"{symbol}_{self.timeframe}_{result['strategy']}_equity.png")
            logger.info(f"Đã lưu biểu đồ {result['strategy']} tại {self.result_dir / f'{symbol}_{self.timeframe}_{result['strategy']}_equity.png'}")
    
    def save_results(self, symbol, results):
        """
        Lưu kết quả backtest
        
        Args:
            symbol (str): Cặp tiền
            results (list): Danh sách kết quả backtest
        """
        # Tạo summary
        summary = {
            'symbol': symbol,
            'timeframe': self.timeframe,
            'test_period': self.test_period,
            'timestamp': self.timestamp,
            'strategies': []
        }
        
        # Thêm kết quả cho từng chiến lược
        for result in results:
            strategy_summary = {
                'name': result['strategy'],
                'stats': result['stats'],
                'trades_count': len(result['trades'])
            }
            summary['strategies'].append(strategy_summary)
            
            # Lưu danh sách giao dịch
            trades_df = pd.DataFrame(result['trades'])
            trades_df.to_csv(self.result_dir / f"{symbol}_{self.timeframe}_{result['strategy']}_trades.csv", index=False)
            logger.info(f"Đã lưu danh sách giao dịch tại {self.result_dir / f'{symbol}_{self.timeframe}_{result['strategy']}_trades.csv'}")
        
        # Lưu summary
        with open(self.result_dir / f"{symbol}_{self.timeframe}_summary.json", 'w') as f:
            json.dump(summary, f, indent=4)
        logger.info(f"Đã lưu tóm tắt kết quả tại {self.result_dir / f'{symbol}_{self.timeframe}_summary.json'}")
    
    def run_backtest(self):
        """
        Chạy backtest cho tất cả cặp tiền và chiến lược
        """
        all_results = {}
        
        for symbol in self.symbols:
            logger.info(f"Bắt đầu backtest cho {symbol}")
            
            # Tải dữ liệu
            data = self.load_market_data(symbol)
            if data is None or len(data) == 0:
                logger.error(f"Không thể tải dữ liệu cho {symbol}")
                continue
            
            # Kết quả cho từng chiến lược
            results = []
            
            # Chạy chiến lược đa rủi ro với các mức rủi ro khác nhau
            for risk_level in [0.10, 0.15, 0.20, 0.25]:
                result = self.run_multi_risk_strategy(data, risk_level)
                results.append(result)
            
            # Chạy chiến lược cho thị trường đi ngang với các mức rủi ro khác nhau
            for risk_level in [0.10, 0.15, 0.20, 0.25]:
                result = self.run_sideways_strategy(data, risk_level)
                results.append(result)
            
            # Chạy chiến lược thích ứng đa rủi ro
            adaptive_result = self.run_adaptive_strategy(data)
            results.append(adaptive_result)
            
            # Vẽ biểu đồ kết quả
            self.plot_results(symbol, results)
            
            # Lưu kết quả
            self.save_results(symbol, results)
            
            all_results[symbol] = results
        
        return all_results

if __name__ == "__main__":
    # Danh sách cặp tiền tệ
    symbols = ['BTCUSDT']
    
    # Khởi tạo và chạy backtest
    backtest = AllStrategiesBacktest(timeframe='1h', test_period=90, symbols=symbols)
    results = backtest.run_backtest()
    
    logger.info("Hoàn thành backtest cho tất cả chiến lược!")