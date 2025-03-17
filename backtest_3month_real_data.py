#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Backtest 3 tháng trên dữ liệu thật

Script này thực hiện backtest hệ thống giao dịch tích hợp trên dữ liệu thật 3 tháng gần nhất.
"""

import os
import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union
import argparse

# Import các module đã phát triển
from integrated_sideways_trading_system import IntegratedSidewaysTrader
from sideways_market_optimizer import SidewaysMarketOptimizer

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/backtest_3month.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('backtest_3month')

class BacktestEngine:
    """
    Engine backtest cho hệ thống giao dịch tích hợp
    """
    
    def __init__(self, config_path: str = 'configs/sideways_config.json'):
        """
        Khởi tạo engine backtesting
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
        """
        # Tạo thư mục đầu ra
        os.makedirs('backtest_results', exist_ok=True)
        os.makedirs('backtest_charts', exist_ok=True)
        
        # Khởi tạo hệ thống giao dịch
        self.trader = IntegratedSidewaysTrader(config_path)
        
        logger.info("Đã khởi tạo Backtest Engine")
    
    def run_backtest(self, symbol: str, period: str = '3mo', timeframe: str = '1d',
                    initial_balance: float = 10000.0) -> Dict:
        """
        Chạy backtest
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            period (str): Khoảng thời gian
            timeframe (str): Khung thời gian
            initial_balance (float): Số dư ban đầu
            
        Returns:
            Dict: Kết quả backtest
        """
        # Tải dữ liệu
        df = self.trader.load_data(symbol, timeframe, period)
        
        if df.empty:
            logger.error(f"Không thể tải dữ liệu cho {symbol}")
            return {"error": "Không thể tải dữ liệu"}
        
        # Chuẩn bị kết quả
        trades = []
        equity_curve = []
        
        # Trạng thái backtest
        balance = initial_balance
        position = None
        
        # Thêm chỉ báo
        df_indicators = self.trader.sideways_optimizer.calculate_indicators(df)
        
        # Trường hợp đặc biệt: với timeframe 1d, chúng ta mô phỏng giao dịch EOD
        if timeframe == '1d':
            # Lặp qua từng ngày giao dịch
            for i in range(30, len(df_indicators) - 1):  # Bắt đầu sau 30 ngày để có đủ dữ liệu
                # Lấy dữ liệu cho đến thời điểm hiện tại
                current_data = df_indicators.iloc[:i+1].copy()
                
                # Lấy giá hiện tại và giá tiếp theo (cho mục đích kiểm tra TP/SL)
                current_price = current_data['close'].iloc[-1]
                next_day_open = df_indicators['open'].iloc[i+1]
                next_day_high = df_indicators['high'].iloc[i+1]
                next_day_low = df_indicators['low'].iloc[i+1]
                next_day_close = df_indicators['close'].iloc[i+1]
                
                # Lưu trữ giá trị vốn
                equity_curve.append({
                    'date': current_data.index[-1],
                    'equity': balance if position is None else balance + position['size'] * (current_price - position['entry_price']),
                    'position': 'long' if position is not None and position['direction'] == 'buy' else 'short' if position is not None and position['direction'] == 'sell' else 'none'
                })
                
                # Kiểm tra nếu đang có vị thế mở
                if position is not None:
                    # Kiểm tra xem TP/SL có được kích hoạt không
                    if position['direction'] == 'buy':
                        # Vị thế mua
                        if next_day_high >= position['take_profit']:
                            # TP được kích hoạt
                            profit = position['size'] * (position['take_profit'] - position['entry_price'])
                            balance += profit
                            
                            trades.append({
                                'entry_date': position['entry_date'],
                                'exit_date': current_data.index[-1],
                                'direction': position['direction'],
                                'entry_price': position['entry_price'],
                                'exit_price': position['take_profit'],
                                'size': position['size'],
                                'profit': profit,
                                'profit_pct': (profit / (position['size'] * position['entry_price'])) * 100,
                                'exit_type': 'take_profit'
                            })
                            
                            logger.info(f"TP đạt: {position['direction']} từ {position['entry_price']:.2f} đến {position['take_profit']:.2f}, lợi nhuận: ${profit:.2f}")
                            
                            position = None
                            
                        elif next_day_low <= position['stop_loss']:
                            # SL được kích hoạt
                            loss = position['size'] * (position['stop_loss'] - position['entry_price'])
                            balance += loss
                            
                            trades.append({
                                'entry_date': position['entry_date'],
                                'exit_date': current_data.index[-1],
                                'direction': position['direction'],
                                'entry_price': position['entry_price'],
                                'exit_price': position['stop_loss'],
                                'size': position['size'],
                                'profit': loss,
                                'profit_pct': (loss / (position['size'] * position['entry_price'])) * 100,
                                'exit_type': 'stop_loss'
                            })
                            
                            logger.info(f"SL đạt: {position['direction']} từ {position['entry_price']:.2f} đến {position['stop_loss']:.2f}, lỗ: ${loss:.2f}")
                            
                            position = None
                    
                    else:
                        # Vị thế bán
                        if next_day_low <= position['take_profit']:
                            # TP được kích hoạt
                            profit = position['size'] * (position['entry_price'] - position['take_profit'])
                            balance += profit
                            
                            trades.append({
                                'entry_date': position['entry_date'],
                                'exit_date': current_data.index[-1],
                                'direction': position['direction'],
                                'entry_price': position['entry_price'],
                                'exit_price': position['take_profit'],
                                'size': position['size'],
                                'profit': profit,
                                'profit_pct': (profit / (position['size'] * position['entry_price'])) * 100,
                                'exit_type': 'take_profit'
                            })
                            
                            logger.info(f"TP đạt: {position['direction']} từ {position['entry_price']:.2f} đến {position['take_profit']:.2f}, lợi nhuận: ${profit:.2f}")
                            
                            position = None
                            
                        elif next_day_high >= position['stop_loss']:
                            # SL được kích hoạt
                            loss = position['size'] * (position['entry_price'] - position['stop_loss'])
                            balance += loss
                            
                            trades.append({
                                'entry_date': position['entry_date'],
                                'exit_date': current_data.index[-1],
                                'direction': position['direction'],
                                'entry_price': position['entry_price'],
                                'exit_price': position['stop_loss'],
                                'size': position['size'],
                                'profit': loss,
                                'profit_pct': (loss / (position['size'] * position['entry_price'])) * 100,
                                'exit_type': 'stop_loss'
                            })
                            
                            logger.info(f"SL đạt: {position['direction']} từ {position['entry_price']:.2f} đến {position['stop_loss']:.2f}, lỗ: ${loss:.2f}")
                            
                            position = None
                
                # Nếu không có vị thế, kiểm tra tín hiệu mới
                if position is None:
                    # Phân tích thị trường
                    market_analysis = self.trader.sideways_optimizer.analyze_market_with_divergence(current_data, symbol)
                    
                    # Lấy tín hiệu
                    signal = self.trader.get_trading_signals(symbol, timeframe, period)
                    
                    # Kiểm tra xem có nên vào lệnh không
                    if signal['signal'] in ['buy', 'sell'] and signal['confidence'] > 0.5:
                        # Lấy thông số giao dịch
                        trade_params = self.trader.get_trade_parameters(symbol, timeframe, period)
                        
                        # Tính toán kích thước vị thế (ở đây giả sử 1x là 100% số dư)
                        position_size_multiplier = trade_params['position_size']
                        position_size = balance * position_size_multiplier  # Đơn vị USD
                        
                        # Mở vị thế mới
                        position = {
                            'direction': signal['signal'],
                            'entry_date': current_data.index[-1],
                            'entry_price': current_price,
                            'take_profit': trade_params['take_profit'],
                            'stop_loss': trade_params['stop_loss'],
                            'size': position_size / current_price,  # Chuyển đổi từ USD sang số lượng coin
                            'tp_pct': trade_params['tp_distance_pct'],
                            'sl_pct': trade_params['sl_distance_pct']
                        }
                        
                        logger.info(f"Mở vị thế: {signal['signal']} tại {current_price:.2f}, TP: {trade_params['take_profit']:.2f}, SL: {trade_params['stop_loss']:.2f}")
        
        # Đóng vị thế cuối cùng nếu còn
        if position is not None:
            final_price = df_indicators['close'].iloc[-1]
            
            if position['direction'] == 'buy':
                profit = position['size'] * (final_price - position['entry_price'])
            else:
                profit = position['size'] * (position['entry_price'] - final_price)
                
            balance += profit
            
            trades.append({
                'entry_date': position['entry_date'],
                'exit_date': df_indicators.index[-1],
                'direction': position['direction'],
                'entry_price': position['entry_price'],
                'exit_price': final_price,
                'size': position['size'],
                'profit': profit,
                'profit_pct': (profit / (position['size'] * position['entry_price'])) * 100,
                'exit_type': 'end_of_test'
            })
            
            logger.info(f"Đóng vị thế cuối cùng: {position['direction']} từ {position['entry_price']:.2f} đến {final_price:.2f}, lợi nhuận: ${profit:.2f}")
        
        # Thêm mục cuối vào equity curve
        equity_curve.append({
            'date': df_indicators.index[-1],
            'equity': balance,
            'position': 'none'
        })
        
        # Tính toán số liệu thống kê
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t['profit'] > 0)
        losing_trades = sum(1 for t in trades if t['profit'] <= 0)
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_profit = sum(t['profit'] for t in trades)
        avg_profit = total_profit / total_trades if total_trades > 0 else 0
        
        # Tính toán các thông số khác
        if winning_trades > 0:
            avg_win = sum(t['profit'] for t in trades if t['profit'] > 0) / winning_trades
        else:
            avg_win = 0
            
        if losing_trades > 0:
            avg_loss = sum(t['profit'] for t in trades if t['profit'] <= 0) / losing_trades
        else:
            avg_loss = 0
        
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        
        # Tính toán drawdown
        equity_values = [e['equity'] for e in equity_curve]
        max_drawdown, max_drawdown_pct = self.calculate_max_drawdown(equity_values, initial_balance)
        
        # Tạo báo cáo
        result = {
            'symbol': symbol,
            'period': period,
            'timeframe': timeframe,
            'initial_balance': initial_balance,
            'final_balance': balance,
            'profit_loss': balance - initial_balance,
            'profit_loss_pct': ((balance - initial_balance) / initial_balance) * 100,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown_pct,
            'trades': trades,
            'equity_curve': equity_curve,
            'test_start_date': df.index[0].strftime('%Y-%m-%d'),
            'test_end_date': df.index[-1].strftime('%Y-%m-%d')
        }
        
        # Lưu kết quả dưới dạng JSON
        results_path = f'backtest_results/backtest_{symbol}_{period}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        # Chuyển đổi datetime thành string trong danh sách trades
        trades_serializable = []
        for trade in trades:
            trade_copy = trade.copy()
            trade_copy['entry_date'] = trade_copy['entry_date'].strftime('%Y-%m-%d')
            trade_copy['exit_date'] = trade_copy['exit_date'].strftime('%Y-%m-%d')
            trades_serializable.append(trade_copy)
        
        equity_serializable = []
        for point in equity_curve:
            point_copy = point.copy()
            point_copy['date'] = point_copy['date'].strftime('%Y-%m-%d')
            equity_serializable.append(point_copy)
        
        # Tạo bản sao có thể serialize
        result_serializable = result.copy()
        result_serializable['trades'] = trades_serializable
        result_serializable['equity_curve'] = equity_serializable
        
        with open(results_path, 'w') as f:
            json.dump(result_serializable, f, indent=4)
        
        logger.info(f"Đã lưu kết quả backtest tại {results_path}")
        
        # Vẽ biểu đồ
        self.plot_backtest_results(result, symbol, period)
        
        return result
    
    def calculate_max_drawdown(self, equity_values: List[float], initial_balance: float) -> Tuple[float, float]:
        """
        Tính toán drawdown tối đa
        
        Args:
            equity_values (List[float]): Danh sách giá trị vốn
            initial_balance (float): Số dư ban đầu
            
        Returns:
            Tuple[float, float]: Drawdown tối đa (số tiền, phần trăm)
        """
        max_equity = initial_balance
        max_drawdown = 0
        
        for equity in equity_values:
            if equity > max_equity:
                max_equity = equity
            
            drawdown = max_equity - equity
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        max_drawdown_pct = (max_drawdown / max_equity) * 100 if max_equity > 0 else 0
        
        return max_drawdown, max_drawdown_pct
    
    def plot_backtest_results(self, result: Dict, symbol: str, period: str) -> None:
        """
        Vẽ biểu đồ kết quả backtest
        
        Args:
            result (Dict): Kết quả backtest
            symbol (str): Ký hiệu tiền tệ
            period (str): Khoảng thời gian
        """
        # Tạo biểu đồ
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})
        
        # Chuẩn bị dữ liệu
        dates = [datetime.strptime(e['date'], '%Y-%m-%d') if isinstance(e['date'], str) else e['date'] for e in result['equity_curve']]
        equity = [e['equity'] for e in result['equity_curve']]
        
        # Vẽ đường equity
        ax1.plot(dates, equity, label='Equity Curve')
        
        # Thêm các giao dịch vào biểu đồ
        for trade in result['trades']:
            entry_date = datetime.strptime(trade['entry_date'], '%Y-%m-%d') if isinstance(trade['entry_date'], str) else trade['entry_date']
            exit_date = datetime.strptime(trade['exit_date'], '%Y-%m-%d') if isinstance(trade['exit_date'], str) else trade['exit_date']
            
            if trade['profit'] > 0:
                color = 'green'
            else:
                color = 'red'
            
            # Vẽ dải giao dịch
            ax1.axvspan(entry_date, exit_date, color=color, alpha=0.3)
            
            # Thêm chú thích
            if exit_date == dates[-1]:  # Nếu là giao dịch cuối cùng
                ax1.annotate(f"{trade['direction'].upper()} {trade['profit']:.2f}",
                           xy=(entry_date, max(equity)),
                           xytext=(entry_date, max(equity) * 1.05),
                           arrowprops=dict(facecolor=color, shrink=0.05),
                           ha='center')
        
        # Tính toán return theo từng giao dịch
        trade_returns = []
        for trade in result['trades']:
            trade_returns.append({
                'exit_date': datetime.strptime(trade['exit_date'], '%Y-%m-%d') if isinstance(trade['exit_date'], str) else trade['exit_date'],
                'profit_pct': trade['profit_pct']
            })
        
        # Sắp xếp theo ngày
        trade_returns.sort(key=lambda x: x['exit_date'])
        
        # Vẽ chart lợi nhuận mỗi giao dịch
        if trade_returns:
            ret_dates = [t['exit_date'] for t in trade_returns]
            ret_values = [t['profit_pct'] for t in trade_returns]
            
            ax2.bar(ret_dates, ret_values, color=['green' if r > 0 else 'red' for r in ret_values])
            ax2.axhline(y=0, color='black', linestyle='-')
            ax2.set_ylabel('Lợi nhuận %')
        
        # Thêm tiêu đề và nhãn
        ax1.set_title(f'Backtest {symbol} ({period}) - P/L: ${result["profit_loss"]:.2f} ({result["profit_loss_pct"]:.2f}%)', fontsize=14)
        ax1.set_ylabel('Equity ($)')
        ax1.grid(True)
        
        # Thêm thông tin thống kê
        stats_text = f"""
        Win Rate: {result['win_rate']:.2f}
        Profit Factor: {result['profit_factor']:.2f}
        Trades: {result['total_trades']}
        Max Drawdown: ${result['max_drawdown']:.2f} ({result['max_drawdown_pct']:.2f}%)
        """
        
        # Thêm text box với thông tin thống kê
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax1.text(0.02, 0.97, stats_text, transform=ax1.transAxes, fontsize=10,
               verticalalignment='top', bbox=props)
        
        # Định dạng ngày tháng
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        
        # Lưu biểu đồ
        chart_path = f'backtest_charts/backtest_{symbol}_{period}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        plt.savefig(chart_path)
        plt.close()
        
        logger.info(f"Đã lưu biểu đồ backtest tại {chart_path}")
    
    def create_summary_report(self, results: List[Dict]) -> None:
        """
        Tạo báo cáo tổng hợp từ nhiều kết quả backtest
        
        Args:
            results (List[Dict]): Danh sách kết quả backtest
        """
        if not results:
            logger.warning("Không có kết quả backtest để tạo báo cáo tổng hợp")
            return
        
        # Tổng hợp kết quả
        symbols = [r['symbol'] for r in results]
        total_profit = sum(r['profit_loss'] for r in results)
        avg_profit_pct = sum(r['profit_loss_pct'] for r in results) / len(results)
        avg_win_rate = sum(r['win_rate'] for r in results) / len(results)
        
        # Thống kê số giao dịch
        total_trades = sum(r['total_trades'] for r in results)
        winning_trades = sum(r['winning_trades'] for r in results)
        losing_trades = sum(r['losing_trades'] for r in results)
        
        if total_trades > 0:
            overall_win_rate = winning_trades / total_trades
        else:
            overall_win_rate = 0
        
        # Báo cáo
        summary = {
            'symbols': symbols,
            'total_symbols': len(symbols),
            'test_period': results[0]['period'],
            'test_timeframe': results[0]['timeframe'],
            'total_profit_loss': total_profit,
            'avg_profit_loss_pct': avg_profit_pct,
            'avg_win_rate': avg_win_rate,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'overall_win_rate': overall_win_rate,
            'test_start_date': min(r['test_start_date'] for r in results),
            'test_end_date': max(r['test_end_date'] for r in results),
            'results_by_symbol': []
        }
        
        # Thêm thông tin chi tiết cho từng symbol
        for result in results:
            summary['results_by_symbol'].append({
                'symbol': result['symbol'],
                'profit_loss': result['profit_loss'],
                'profit_loss_pct': result['profit_loss_pct'],
                'win_rate': result['win_rate'],
                'total_trades': result['total_trades']
            })
        
        # Lưu báo cáo
        summary_path = f'backtest_results/summary_{results[0]["period"]}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=4)
        
        logger.info(f"Đã lưu báo cáo tổng hợp tại {summary_path}")
        
        # Vẽ biểu đồ tổng hợp
        self.plot_summary_results(summary)
    
    def plot_summary_results(self, summary: Dict) -> None:
        """
        Vẽ biểu đồ tổng hợp từ nhiều kết quả backtest
        
        Args:
            summary (Dict): Báo cáo tổng hợp
        """
        # Chuẩn bị dữ liệu
        symbols = [r['symbol'] for r in summary['results_by_symbol']]
        profits = [r['profit_loss_pct'] for r in summary['results_by_symbol']]
        win_rates = [r['win_rate'] * 100 for r in summary['results_by_symbol']]
        trades = [r['total_trades'] for r in summary['results_by_symbol']]
        
        # Tạo biểu đồ
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        
        # Vẽ biểu đồ lợi nhuận theo symbol
        bars = ax1.bar(symbols, profits, color=['green' if p > 0 else 'red' for p in profits])
        ax1.set_title(f'Kết quả Backtest {summary["test_period"]}', fontsize=14)
        ax1.set_ylabel('Lợi nhuận (%)')
        ax1.axhline(y=0, color='black', linestyle='-')
        
        # Thêm giá trị lên các cột
        for bar in bars:
            height = bar.get_height()
            ax1.annotate(f'{height:.1f}%',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),  # 3 points vertical offset
                       textcoords="offset points",
                       ha='center', va='bottom')
        
        # Vẽ biểu đồ tỷ lệ thắng và số lượng giao dịch
        ax2.bar(symbols, win_rates, alpha=0.7, label='Win Rate (%)')
        
        # Tạo trục thứ hai cho số lượng giao dịch
        ax3 = ax2.twinx()
        ax3.plot(symbols, trades, 'ro-', label='Số lượng giao dịch')
        
        # Thêm legend cho cả hai trục
        lines1, labels1 = ax2.get_legend_handles_labels()
        lines2, labels2 = ax3.get_legend_handles_labels()
        ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
        
        ax2.set_ylabel('Win Rate (%)')
        ax3.set_ylabel('Số lượng giao dịch')
        
        # Thêm thông tin tổng hợp
        summary_text = f"""
        Tổng lợi nhuận: ${summary['total_profit_loss']:.2f}
        Lợi nhuận trung bình: {summary['avg_profit_loss_pct']:.2f}%
        Win Rate tổng thể: {summary['overall_win_rate']*100:.1f}%
        Tổng số giao dịch: {summary['total_trades']}
        """
        
        props = dict(boxstyle='round', facecolor='lightblue', alpha=0.5)
        ax1.text(0.02, 0.98, summary_text, transform=ax1.transAxes, fontsize=10,
               verticalalignment='top', bbox=props)
        
        plt.tight_layout()
        
        # Lưu biểu đồ
        chart_path = f'backtest_charts/summary_{summary["test_period"]}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        plt.savefig(chart_path)
        plt.close()
        
        logger.info(f"Đã lưu biểu đồ tổng hợp tại {chart_path}")

def main():
    """
    Hàm main cho script
    """
    parser = argparse.ArgumentParser(description='Backtest 3 tháng trên dữ liệu thật')
    parser.add_argument('--symbols', type=str, nargs='+', default=['BTC-USD'],
                       help='Danh sách các symbols cần test (e.g., BTC-USD ETH-USD)')
    parser.add_argument('--period', type=str, default='3mo',
                       help='Khoảng thời gian (e.g., 1mo, 3mo, 6mo)')
    parser.add_argument('--timeframe', type=str, default='1d',
                       help='Khung thời gian (e.g., 1d, 4h, 1h)')
    parser.add_argument('--balance', type=float, default=10000.0,
                       help='Số dư ban đầu')
    
    args = parser.parse_args()
    
    # Khởi tạo backtest engine
    engine = BacktestEngine()
    
    # Lưu kết quả từng symbol
    results = []
    
    # Chạy backtest cho từng symbol
    for symbol in args.symbols:
        try:
            logger.info(f"Bắt đầu backtest {symbol} ({args.period}, {args.timeframe})")
            
            result = engine.run_backtest(symbol, args.period, args.timeframe, args.balance)
            
            if 'error' not in result:
                results.append(result)
                
                logger.info(f"Kết quả {symbol}: P/L=${result['profit_loss']:.2f} ({result['profit_loss_pct']:.2f}%), "
                          f"Win Rate={result['win_rate']*100:.1f}%, Trades={result['total_trades']}")
            
        except Exception as e:
            logger.error(f"Lỗi khi backtest {symbol}: {str(e)}")
    
    # Tạo báo cáo tổng hợp
    if results:
        engine.create_summary_report(results)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Lỗi trong main: {str(e)}")
        print(f"Lỗi: {str(e)}")