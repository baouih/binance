import os
import sys
import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from pathlib import Path

# Thêm thư mục gốc vào đường dẫn
sys.path.append('.')

# Import các module cần thiết
from adaptive_risk_allocation import AdaptiveRiskAllocator
from sideways_market_strategy import SidewaysMarketStrategy
from optimized_risk_manager import OptimizedRiskManager
from multi_risk_strategy import MultiRiskStrategy
from market_analyzer import MarketAnalyzer
from utils.data_loader import DataLoader
from utils.performance_analyzer import PerformanceAnalyzer

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('3month_comprehensive_test.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('comprehensive_test')

class ComprehensiveTestRunner:
    """
    Lớp thực hiện kiểm tra tổng thể hiệu suất của bot với dữ liệu 3 tháng
    """
    
    def __init__(self):
        # Thư mục lưu kết quả
        self.results_dir = Path('./comprehensive_test_results')
        if not self.results_dir.exists():
            os.makedirs(self.results_dir)
        
        # Cấu hình test
        self.test_config = {
            'start_date': (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),  # 3 tháng trước
            'end_date': datetime.now().strftime('%Y-%m-%d'),
            'timeframes': ['15m', '1h', '4h', '1d'],
            'symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT'],
            'risk_levels': [0.10, 0.15, 0.20, 0.25],  # 10%, 15%, 20%, 25%
            'initial_balance': 10000,  # 10,000 USDT
            'leverage': 5,  # Đòn bẩy 5x
        }
        
        # Khởi tạo các thành phần
        self.data_loader = DataLoader()
        self.performance_analyzer = PerformanceAnalyzer()
        
        # Kết quả test
        self.results = {
            'by_symbol': {},
            'by_timeframe': {},
            'by_risk_level': {},
            'by_market_condition': {},
            'overall': {},
            'sideways_performance': {},
        }
    
    def load_data(self, symbol, timeframe, start_date, end_date):
        """
        Tải dữ liệu thị trường
        """
        logger.info(f"Đang tải dữ liệu {symbol} - {timeframe} từ {start_date} đến {end_date}")
        
        try:
            # Sử dụng data loader để tải dữ liệu
            data = self.data_loader.load_historical_data(
                symbol=symbol,
                interval=timeframe,
                start_str=start_date,
                end_str=end_date,
                testnet=True
            )
            
            if data is None or len(data) < 100:
                logger.warning(f"Không đủ dữ liệu cho {symbol} - {timeframe}")
                return None
            
            # Tiền xử lý dữ liệu
            # Đảm bảo dữ liệu có các cột cần thiết
            data = data.rename(columns={
                'open': 'Open', 
                'high': 'High', 
                'low': 'Low', 
                'close': 'Close', 
                'volume': 'Volume'
            })
            
            return data
        
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu {symbol} - {timeframe}: {str(e)}")
            return None
    
    def apply_strategies(self, data, symbol, timeframe, risk_level):
        """
        Áp dụng các chiến lược vào dữ liệu
        """
        logger.info(f"Áp dụng chiến lược cho {symbol} - {timeframe} với mức rủi ro {risk_level*100:.0f}%")
        
        try:
            # 1. Phân tích thị trường để xác định điều kiện
            market_analyzer = MarketAnalyzer(data)
            market_condition = market_analyzer.detect_market_condition()
            data['market_condition'] = market_condition
            
            # 2. Quản lý rủi ro tối ưu
            risk_manager = OptimizedRiskManager(risk_level=risk_level)
            
            # 3. Chiến lược thị trường đi ngang
            sideways_strategy = SidewaysMarketStrategy(data, risk_level=risk_level)
            sideways_signals = sideways_strategy.generate_signals()
            
            # 4. Chiến lược đa mức rủi ro
            multi_risk_strategy = MultiRiskStrategy(risk_level=risk_level)
            multi_risk_signals = multi_risk_strategy.apply_strategy(data)
            
            # 5. Phân bổ rủi ro thích ứng
            adaptive_risk = AdaptiveRiskAllocator(risk_level=risk_level)
            
            # Kết hợp tín hiệu từ các chiến lược 
            # Ưu tiên tín hiệu từ chiến lược chuyên biệt cho thị trường đi ngang nếu là thị trường đi ngang
            signals = []
            
            # Đếm số lượng các loại thị trường
            market_types = data['market_condition'].value_counts().to_dict()
            
            for i in range(len(data)):
                current_condition = data['market_condition'].iloc[i]
                
                # Nếu là thị trường đi ngang và có tín hiệu từ chiến lược chuyên biệt
                if current_condition == 'SIDEWAYS' and i in sideways_signals:
                    signal = sideways_signals[i].copy()
                    signal['strategy'] = 'sideways'
                    signal['risk_adjusted'] = risk_manager.adjust_risk(signal, current_condition)
                    signals.append(signal)
                
                # Sử dụng tín hiệu từ chiến lược đa mức rủi ro
                elif i in multi_risk_signals:
                    signal = multi_risk_signals[i].copy()
                    signal['strategy'] = 'multi_risk'
                    signal['risk_adjusted'] = risk_manager.adjust_risk(signal, current_condition)
                    signals.append(signal)
            
            return {
                'data': data,
                'signals': signals,
                'market_types': market_types
            }
        
        except Exception as e:
            logger.error(f"Lỗi khi áp dụng chiến lược {symbol} - {timeframe}: {str(e)}")
            return None
    
    def run_backtest(self, data, signals, risk_level, symbol, timeframe):
        """
        Chạy backtest với dữ liệu và tín hiệu đã xử lý
        """
        logger.info(f"Chạy backtest cho {symbol} - {timeframe} với mức rủi ro {risk_level*100:.0f}%")
        
        try:
            # Cấu hình backtest
            initial_balance = self.test_config['initial_balance']
            leverage = self.test_config['leverage']
            
            # Biến theo dõi trạng thái giao dịch
            balance = initial_balance
            position = None
            trades = []
            equity_curve = [initial_balance]
            max_drawdown = 0
            max_balance = initial_balance
            
            # Danh sách để theo dõi giao dịch theo loại thị trường
            trades_by_market = {
                'BULL': [],
                'BEAR': [],
                'SIDEWAYS': [],
                'VOLATILE': []
            }
            
            # Các biến thống kê
            trade_count = 0
            win_count = 0
            loss_count = 0
            
            # Duyệt qua từng điểm dữ liệu
            for i in range(1, len(data)):
                current_price = data['Close'].iloc[i]
                current_condition = data['market_condition'].iloc[i]
                
                # Xử lý vị thế đang mở
                if position is not None:
                    # Kiểm tra điều kiện chốt lời
                    if (position['type'] == 'LONG' and current_price >= position['take_profit']) or \
                       (position['type'] == 'SHORT' and current_price <= position['take_profit']):
                        # Tính lợi nhuận
                        if position['type'] == 'LONG':
                            profit = position['quantity'] * (current_price - position['entry_price']) * leverage
                        else:
                            profit = position['quantity'] * (position['entry_price'] - current_price) * leverage
                        
                        # Cập nhật số dư
                        balance += profit
                        
                        # Lưu thông tin giao dịch
                        trade = {
                            'entry_time': position['entry_time'],
                            'exit_time': data.index[i],
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'type': position['type'],
                            'entry_price': position['entry_price'],
                            'exit_price': current_price,
                            'quantity': position['quantity'],
                            'profit': profit,
                            'profit_pct': (profit / position['cost']) * 100,
                            'market_condition': position['market_condition'],
                            'strategy': position['strategy']
                        }
                        
                        trades.append(trade)
                        trades_by_market[position['market_condition']].append(trade)
                        
                        # Cập nhật thống kê
                        trade_count += 1
                        if profit > 0:
                            win_count += 1
                        else:
                            loss_count += 1
                        
                        # Đóng vị thế
                        position = None
                    
                    # Kiểm tra điều kiện cắt lỗ
                    elif (position['type'] == 'LONG' and current_price <= position['stop_loss']) or \
                         (position['type'] == 'SHORT' and current_price >= position['stop_loss']):
                        # Tính lỗ
                        if position['type'] == 'LONG':
                            loss = position['quantity'] * (current_price - position['entry_price']) * leverage
                        else:
                            loss = position['quantity'] * (position['entry_price'] - current_price) * leverage
                        
                        # Cập nhật số dư
                        balance += loss
                        
                        # Lưu thông tin giao dịch
                        trade = {
                            'entry_time': position['entry_time'],
                            'exit_time': data.index[i],
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'type': position['type'],
                            'entry_price': position['entry_price'],
                            'exit_price': current_price,
                            'quantity': position['quantity'],
                            'profit': loss,
                            'profit_pct': (loss / position['cost']) * 100,
                            'market_condition': position['market_condition'],
                            'strategy': position['strategy']
                        }
                        
                        trades.append(trade)
                        trades_by_market[position['market_condition']].append(trade)
                        
                        # Cập nhật thống kê
                        trade_count += 1
                        loss_count += 1
                        
                        # Đóng vị thế
                        position = None
                
                # Mở vị thế mới nếu có tín hiệu và không có vị thế đang mở
                signal_at_i = None
                for signal in signals:
                    if signal.get('index', -1) == i:
                        signal_at_i = signal
                        break
                
                if position is None and signal_at_i is not None:
                    signal = signal_at_i
                    
                    # Tính kích thước vị thế dựa vào mức rủi ro
                    risk_amount = balance * risk_level
                    
                    if signal['type'] == 'LONG':
                        # Stop loss là giá hiện tại trừ đi một tỷ lệ
                        stop_distance = current_price - signal['stop_loss']
                        position_size = (risk_amount / stop_distance) / leverage
                    else:
                        # Stop loss là giá hiện tại cộng thêm một tỷ lệ
                        stop_distance = signal['stop_loss'] - current_price
                        position_size = (risk_amount / stop_distance) / leverage
                    
                    # Đảm bảo không vượt quá số dư
                    max_position = balance * 0.95 / current_price  # Giữ 5% margin
                    position_size = min(position_size, max_position)
                    
                    # Mở vị thế
                    position = {
                        'entry_time': data.index[i],
                        'type': signal['type'],
                        'entry_price': current_price,
                        'quantity': position_size,
                        'stop_loss': signal['stop_loss'],
                        'take_profit': signal['take_profit'],
                        'cost': position_size * current_price,
                        'market_condition': current_condition,
                        'strategy': signal['strategy']
                    }
                
                # Cập nhật equity curve và drawdown
                equity_curve.append(balance)
                
                if balance > max_balance:
                    max_balance = balance
                
                current_drawdown = (max_balance - balance) / max_balance * 100
                max_drawdown = max(max_drawdown, current_drawdown)
            
            # Đóng vị thế cuối cùng nếu còn
            if position is not None:
                final_price = data['Close'].iloc[-1]
                
                if position['type'] == 'LONG':
                    profit = position['quantity'] * (final_price - position['entry_price']) * leverage
                else:
                    profit = position['quantity'] * (position['entry_price'] - final_price) * leverage
                
                balance += profit
                
                trade = {
                    'entry_time': position['entry_time'],
                    'exit_time': data.index[-1],
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'type': position['type'],
                    'entry_price': position['entry_price'],
                    'exit_price': final_price,
                    'quantity': position['quantity'],
                    'profit': profit,
                    'profit_pct': (profit / position['cost']) * 100,
                    'market_condition': position['market_condition'],
                    'strategy': position['strategy']
                }
                
                trades.append(trade)
                trades_by_market[position['market_condition']].append(trade)
                
                trade_count += 1
                if profit > 0:
                    win_count += 1
                else:
                    loss_count += 1
            
            # Phân tích riêng cho chiến lược thị trường đi ngang
            sideways_trades = [t for t in trades if t['strategy'] == 'sideways']
            sideways_win_count = len([t for t in sideways_trades if t['profit'] > 0])
            
            # Tính các thống kê
            final_balance = balance
            profit_loss = final_balance - initial_balance
            profit_pct = (profit_loss / initial_balance) * 100
            win_rate = win_count / trade_count * 100 if trade_count > 0 else 0
            
            # Tính profit factor
            total_profit = sum([t['profit'] for t in trades if t['profit'] > 0])
            total_loss = sum([abs(t['profit']) for t in trades if t['profit'] < 0])
            profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
            
            # Kết quả backtest
            backtest_result = {
                'symbol': symbol,
                'timeframe': timeframe,
                'risk_level': risk_level,
                'initial_balance': initial_balance,
                'final_balance': final_balance,
                'profit_loss': profit_loss,
                'profit_pct': profit_pct,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'trades_count': trade_count,
                'trades': trades,
                'equity_curve': equity_curve,
                'trades_by_market': trades_by_market,
                'sideways_performance': {
                    'trades_count': len(sideways_trades),
                    'win_count': sideways_win_count,
                    'win_rate': (sideways_win_count / len(sideways_trades) * 100) if len(sideways_trades) > 0 else 0
                }
            }
            
            return backtest_result
        
        except Exception as e:
            logger.error(f"Lỗi khi chạy backtest {symbol} - {timeframe}: {str(e)}")
            raise
    
    def run_comprehensive_test(self):
        """
        Chạy kiểm tra tổng thể cho tất cả các cặp tiền, khung thời gian và mức rủi ro
        """
        logger.info("Bắt đầu chạy kiểm tra tổng thể...")
        
        symbols = self.test_config['symbols']
        timeframes = self.test_config['timeframes']
        risk_levels = self.test_config['risk_levels']
        start_date = self.test_config['start_date']
        end_date = self.test_config['end_date']
        
        all_results = []
        risk_level_results = {r: [] for r in risk_levels}
        
        # Chạy test cho mỗi kết hợp
        for symbol in symbols:
            self.results['by_symbol'][symbol] = {}
            
            for timeframe in timeframes:
                logger.info(f"Kiểm thử {symbol} - {timeframe}")
                
                # Tải dữ liệu
                data = self.load_data(symbol, timeframe, start_date, end_date)
                if data is None:
                    continue
                
                self.results['by_symbol'][symbol][timeframe] = {}
                if timeframe not in self.results['by_timeframe']:
                    self.results['by_timeframe'][timeframe] = {}
                
                for risk_level in risk_levels:
                    logger.info(f"Kiểm thử với mức rủi ro {risk_level*100:.0f}%")
                    
                    # Áp dụng chiến lược
                    strategy_result = self.apply_strategies(data, symbol, timeframe, risk_level)
                    if strategy_result is None:
                        continue
                    
                    # Chạy backtest
                    backtest_result = self.run_backtest(
                        strategy_result['data'], 
                        strategy_result['signals'], 
                        risk_level, 
                        symbol, 
                        timeframe
                    )
                    
                    # Lưu kết quả
                    self.results['by_symbol'][symbol][timeframe][f"{risk_level:.2f}"] = backtest_result
                    
                    if symbol not in self.results['by_timeframe'][timeframe]:
                        self.results['by_timeframe'][timeframe][symbol] = {}
                    
                    self.results['by_timeframe'][timeframe][symbol][f"{risk_level:.2f}"] = backtest_result
                    
                    # Lưu kết quả theo mức rủi ro
                    if f"{risk_level:.2f}" not in self.results['by_risk_level']:
                        self.results['by_risk_level'][f"{risk_level:.2f}"] = {}
                    
                    if symbol not in self.results['by_risk_level'][f"{risk_level:.2f}"]:
                        self.results['by_risk_level'][f"{risk_level:.2f}"][symbol] = {}
                    
                    self.results['by_risk_level'][f"{risk_level:.2f}"][symbol][timeframe] = backtest_result
                    
                    # Lưu thông tin hiệu suất cho thị trường đi ngang
                    if 'sideways_performance' not in self.results:
                        self.results['sideways_performance'] = {}
                    
                    if f"{risk_level:.2f}" not in self.results['sideways_performance']:
                        self.results['sideways_performance'][f"{risk_level:.2f}"] = []
                    
                    self.results['sideways_performance'][f"{risk_level:.2f}"].append(
                        backtest_result['sideways_performance']
                    )
                    
                    # Thêm vào danh sách tất cả kết quả
                    all_results.append(backtest_result)
                    risk_level_results[risk_level].append(backtest_result)
        
        # Phân tích kết quả tổng thể
        self.analyze_results(all_results, risk_level_results)
        
        # Lưu kết quả
        self.save_results()
        
        # Vẽ biểu đồ
        self.create_charts()
        
        return self.results
    
    def analyze_results(self, all_results, risk_level_results):
        """
        Phân tích tổng hợp kết quả test
        """
        logger.info("Phân tích kết quả test...")
        
        try:
            # Phân tích theo mức rủi ro
            for risk_level, results in risk_level_results.items():
                if not results:
                    continue
                
                avg_profit = np.mean([r['profit_pct'] for r in results])
                avg_drawdown = np.mean([r['max_drawdown'] for r in results])
                avg_win_rate = np.mean([r['win_rate'] for r in results])
                avg_profit_factor = np.mean([min(r['profit_factor'], 10) for r in results])  # Giới hạn max 10 để tránh outlier
                
                self.results['by_risk_level_summary'] = self.results.get('by_risk_level_summary', {})
                self.results['by_risk_level_summary'][f"{risk_level:.2f}"] = {
                    'avg_profit_pct': avg_profit,
                    'avg_drawdown_pct': avg_drawdown,
                    'avg_win_rate': avg_win_rate,
                    'avg_profit_factor': avg_profit_factor,
                    'sample_size': len(results)
                }
            
            # Phân tích hiệu suất thị trường đi ngang
            for risk_level, perfs in self.results.get('sideways_performance', {}).items():
                if not perfs:
                    continue
                
                valid_perfs = [p for p in perfs if p['trades_count'] > 0]
                if not valid_perfs:
                    continue
                
                avg_win_rate = np.mean([p['win_rate'] for p in valid_perfs])
                total_trades = sum([p['trades_count'] for p in valid_perfs])
                total_wins = sum([p['win_count'] for p in valid_perfs])
                
                self.results['sideways_summary'] = self.results.get('sideways_summary', {})
                self.results['sideways_summary'][risk_level] = {
                    'avg_win_rate': avg_win_rate,
                    'total_trades': total_trades,
                    'total_wins': total_wins,
                    'overall_win_rate': (total_wins / total_trades * 100) if total_trades > 0 else 0
                }
            
            # Phân tích tổng thể
            if all_results:
                avg_profit = np.mean([r['profit_pct'] for r in all_results])
                avg_drawdown = np.mean([r['max_drawdown'] for r in all_results])
                avg_win_rate = np.mean([r['win_rate'] for r in all_results])
                avg_profit_factor = np.mean([min(r['profit_factor'], 10) for r in all_results])
                
                self.results['overall_summary'] = {
                    'avg_profit_pct': avg_profit,
                    'avg_drawdown_pct': avg_drawdown,
                    'avg_win_rate': avg_win_rate,
                    'avg_profit_factor': avg_profit_factor,
                    'sample_size': len(all_results),
                    'test_period': f"{self.test_config['start_date']} to {self.test_config['end_date']}"
                }
        
        except Exception as e:
            logger.error(f"Lỗi khi phân tích kết quả: {str(e)}")
    
    def save_results(self):
        """
        Lưu kết quả vào file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = self.results_dir / f"comprehensive_test_{timestamp}.json"
        summary_file = self.results_dir / f"comprehensive_test_summary_{timestamp}.json"
        
        # Lưu toàn bộ kết quả chi tiết
        with open(results_file, 'w') as f:
            # Loại bỏ các dữ liệu quá lớn trước khi lưu
            results_to_save = self.results.copy()
            
            # Chỉ giữ lại thông tin tóm tắt cho mỗi giao dịch
            for symbol in results_to_save.get('by_symbol', {}):
                for timeframe in results_to_save['by_symbol'].get(symbol, {}):
                    for risk_level in results_to_save['by_symbol'][symbol].get(timeframe, {}):
                        if 'trades' in results_to_save['by_symbol'][symbol][timeframe][risk_level]:
                            # Chỉ lưu 5 giao dịch đầu tiên
                            results_to_save['by_symbol'][symbol][timeframe][risk_level]['trades'] = \
                                results_to_save['by_symbol'][symbol][timeframe][risk_level]['trades'][:5]
                        
                        if 'equity_curve' in results_to_save['by_symbol'][symbol][timeframe][risk_level]:
                            # Không lưu equity curve
                            del results_to_save['by_symbol'][symbol][timeframe][risk_level]['equity_curve']
            
            json.dump(results_to_save, f, indent=4, default=str)
        
        # Lưu tóm tắt kết quả
        summary = {
            'test_period': f"{self.test_config['start_date']} to {self.test_config['end_date']}",
            'symbols_tested': self.test_config['symbols'],
            'timeframes_tested': self.test_config['timeframes'],
            'risk_levels_tested': self.test_config['risk_levels'],
            'overall_summary': self.results.get('overall_summary', {}),
            'by_risk_level_summary': self.results.get('by_risk_level_summary', {}),
            'sideways_summary': self.results.get('sideways_summary', {})
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=4, default=str)
        
        logger.info(f"Đã lưu kết quả vào {results_file}")
        logger.info(f"Đã lưu tóm tắt vào {summary_file}")
    
    def create_charts(self):
        """
        Tạo các biểu đồ phân tích
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        charts_dir = self.results_dir / 'charts'
        if not charts_dir.exists():
            os.makedirs(charts_dir)
        
        try:
            # 1. Biểu đồ lợi nhuận theo mức rủi ro
            if 'by_risk_level_summary' in self.results:
                risk_levels = sorted(self.results['by_risk_level_summary'].keys(), key=lambda x: float(x))
                risk_profits = [self.results['by_risk_level_summary'][r]['avg_profit_pct'] for r in risk_levels]
                risk_drawdowns = [self.results['by_risk_level_summary'][r]['avg_drawdown_pct'] for r in risk_levels]
                risk_win_rates = [self.results['by_risk_level_summary'][r]['avg_win_rate'] for r in risk_levels]
                
                plt.figure(figsize=(12, 8))
                plt.subplot(3, 1, 1)
                plt.bar(risk_levels, risk_profits, color='green', alpha=0.7)
                plt.title('Lợi nhuận trung bình (%) theo mức rủi ro')
                plt.xlabel('Mức rủi ro')
                plt.ylabel('Lợi nhuận (%)')
                plt.grid(True)
                
                plt.subplot(3, 1, 2)
                plt.bar(risk_levels, risk_drawdowns, color='red', alpha=0.7)
                plt.title('Drawdown trung bình (%) theo mức rủi ro')
                plt.xlabel('Mức rủi ro')
                plt.ylabel('Drawdown (%)')
                plt.grid(True)
                
                plt.subplot(3, 1, 3)
                plt.bar(risk_levels, risk_win_rates, color='blue', alpha=0.7)
                plt.title('Tỷ lệ thắng (%) theo mức rủi ro')
                plt.xlabel('Mức rủi ro')
                plt.ylabel('Tỷ lệ thắng (%)')
                plt.grid(True)
                
                plt.tight_layout()
                plt.savefig(charts_dir / f"risk_level_performance_{timestamp}.png")
                plt.close()
            
            # 2. Biểu đồ hiệu suất chiến lược thị trường đi ngang
            if 'sideways_summary' in self.results:
                risk_levels = sorted(self.results['sideways_summary'].keys(), key=lambda x: float(x))
                win_rates = [self.results['sideways_summary'][r]['avg_win_rate'] for r in risk_levels]
                total_trades = [self.results['sideways_summary'][r]['total_trades'] for r in risk_levels]
                
                plt.figure(figsize=(12, 6))
                plt.subplot(1, 2, 1)
                plt.bar(risk_levels, win_rates, color='purple', alpha=0.7)
                plt.title('Tỷ lệ thắng chiến lược thị trường đi ngang')
                plt.xlabel('Mức rủi ro')
                plt.ylabel('Tỷ lệ thắng (%)')
                plt.grid(True)
                
                plt.subplot(1, 2, 2)
                plt.bar(risk_levels, total_trades, color='orange', alpha=0.7)
                plt.title('Số lượng giao dịch thị trường đi ngang')
                plt.xlabel('Mức rủi ro')
                plt.ylabel('Số lượng giao dịch')
                plt.grid(True)
                
                plt.tight_layout()
                plt.savefig(charts_dir / f"sideways_performance_{timestamp}.png")
                plt.close()
            
            # 3. Biểu đồ so sánh hiệu suất theo symbol
            by_symbol_profits = {}
            for symbol in self.results.get('by_symbol', {}):
                symbol_profits = []
                for timeframe in self.results['by_symbol'].get(symbol, {}):
                    for risk_level in self.results['by_symbol'][symbol].get(timeframe, {}):
                        if 'profit_pct' in self.results['by_symbol'][symbol][timeframe][risk_level]:
                            symbol_profits.append(
                                self.results['by_symbol'][symbol][timeframe][risk_level]['profit_pct']
                            )
                
                if symbol_profits:
                    by_symbol_profits[symbol] = np.mean(symbol_profits)
            
            if by_symbol_profits:
                symbols = list(by_symbol_profits.keys())
                profits = [by_symbol_profits[s] for s in symbols]
                
                plt.figure(figsize=(10, 6))
                plt.bar(symbols, profits, color=['green' if p > 0 else 'red' for p in profits], alpha=0.7)
                plt.title('Lợi nhuận trung bình (%) theo cặp tiền')
                plt.xlabel('Cặp tiền')
                plt.ylabel('Lợi nhuận (%)')
                plt.grid(True)
                plt.savefig(charts_dir / f"symbol_performance_{timestamp}.png")
                plt.close()
            
            logger.info(f"Đã tạo các biểu đồ phân tích trong thư mục {charts_dir}")
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ: {str(e)}")
    
    def create_report(self):
        """
        Tạo báo cáo tổng hợp dạng Markdown
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = self.results_dir / f"comprehensive_test_report_{timestamp}.md"
        
        with open(report_path, 'w') as f:
            f.write("# Báo Cáo Kiểm Thử Tổng Thể - Hệ Thống Giao Dịch Tiền Mã Hóa\n\n")
            
            f.write(f"## Thông Tin Kiểm Thử\n\n")
            f.write(f"- **Thời gian kiểm thử:** {self.test_config['start_date']} đến {self.test_config['end_date']}\n")
            f.write(f"- **Cặp tiền được kiểm thử:** {', '.join(self.test_config['symbols'])}\n")
            f.write(f"- **Khung thời gian:** {', '.join(self.test_config['timeframes'])}\n")
            f.write(f"- **Mức rủi ro được kiểm thử:** {', '.join([f'{r*100:.0f}%' for r in self.test_config['risk_levels']])}\n")
            f.write(f"- **Số dư ban đầu:** {self.test_config['initial_balance']} USDT\n")
            f.write(f"- **Đòn bẩy:** {self.test_config['leverage']}x\n\n")
            
            if 'overall_summary' in self.results:
                summary = self.results['overall_summary']
                f.write(f"## Kết Quả Tổng Thể\n\n")
                f.write(f"- **Lợi nhuận trung bình:** {summary['avg_profit_pct']:.2f}%\n")
                f.write(f"- **Drawdown trung bình:** {summary['avg_drawdown_pct']:.2f}%\n")
                f.write(f"- **Tỷ lệ thắng trung bình:** {summary['avg_win_rate']:.2f}%\n")
                f.write(f"- **Profit factor trung bình:** {summary['avg_profit_factor']:.2f}\n")
                f.write(f"- **Số lượng kiểm thử:** {summary['sample_size']}\n\n")
            
            if 'by_risk_level_summary' in self.results:
                f.write(f"## Kết Quả Theo Mức Rủi Ro\n\n")
                f.write(f"| Mức rủi ro | Lợi nhuận (%) | Drawdown (%) | Tỷ lệ thắng (%) | Profit Factor |\n")
                f.write(f"|------------|---------------|--------------|-----------------|---------------|\n")
                
                for risk_level in sorted(self.results['by_risk_level_summary'].keys(), key=lambda x: float(x)):
                    stats = self.results['by_risk_level_summary'][risk_level]
                    f.write(f"| {float(risk_level)*100:.0f}% | {stats['avg_profit_pct']:.2f}% | "
                           f"{stats['avg_drawdown_pct']:.2f}% | {stats['avg_win_rate']:.2f}% | "
                           f"{stats['avg_profit_factor']:.2f} |\n")
                
                f.write("\n")
            
            if 'sideways_summary' in self.results:
                f.write(f"## Hiệu Suất Chiến Lược Thị Trường Đi Ngang\n\n")
                f.write(f"| Mức rủi ro | Tỷ lệ thắng (%) | Số giao dịch |\n")
                f.write(f"|------------|-----------------|---------------|\n")
                
                for risk_level in sorted(self.results['sideways_summary'].keys(), key=lambda x: float(x)):
                    stats = self.results['sideways_summary'][risk_level]
                    f.write(f"| {float(risk_level)*100:.0f}% | {stats['avg_win_rate']:.2f}% | {stats['total_trades']} |\n")
                
                f.write("\n")
            
            f.write(f"## Nhận Xét và Đánh Giá\n\n")
            
            if 'by_risk_level_summary' in self.results:
                # Xác định mức rủi ro tốt nhất
                best_profit_risk = max(self.results['by_risk_level_summary'].items(), 
                                     key=lambda x: x[1]['avg_profit_pct'])
                best_win_rate_risk = max(self.results['by_risk_level_summary'].items(), 
                                       key=lambda x: x[1]['avg_win_rate'])
                best_pf_risk = max(self.results['by_risk_level_summary'].items(), 
                                 key=lambda x: x[1]['avg_profit_factor'])
                
                f.write(f"### Mức rủi ro tối ưu:\n\n")
                f.write(f"- **Lợi nhuận cao nhất:** {float(best_profit_risk[0])*100:.0f}% "
                       f"với lợi nhuận trung bình {best_profit_risk[1]['avg_profit_pct']:.2f}%\n")
                f.write(f"- **Tỷ lệ thắng cao nhất:** {float(best_win_rate_risk[0])*100:.0f}% "
                       f"với tỷ lệ thắng {best_win_rate_risk[1]['avg_win_rate']:.2f}%\n")
                f.write(f"- **Profit factor tốt nhất:** {float(best_pf_risk[0])*100:.0f}% "
                       f"với profit factor {best_pf_risk[1]['avg_profit_factor']:.2f}\n\n")
            
            if 'sideways_summary' in self.results:
                # Đánh giá hiệu suất chiến lược thị trường đi ngang
                best_sideways_risk = max(self.results['sideways_summary'].items(),
                                      key=lambda x: x[1]['avg_win_rate'])
                
                f.write(f"### Hiệu suất chiến lược thị trường đi ngang:\n\n")
                f.write(f"- Mức rủi ro tốt nhất cho thị trường đi ngang: {float(best_sideways_risk[0])*100:.0f}% "
                       f"với tỷ lệ thắng {best_sideways_risk[1]['avg_win_rate']:.2f}%\n")
                
                # So sánh với hiệu suất trước khi tối ưu
                f.write(f"- So với mục tiêu tối ưu hóa (trên 45% win rate), ")
                
                if best_sideways_risk[1]['avg_win_rate'] > 45:
                    f.write(f"chiến lược đã đạt được mục tiêu với tỷ lệ thắng "
                           f"{best_sideways_risk[1]['avg_win_rate']:.2f}% (cao hơn 45%).\n\n")
                else:
                    f.write(f"chiến lược chưa đạt được mục tiêu với tỷ lệ thắng "
                           f"{best_sideways_risk[1]['avg_win_rate']:.2f}% (thấp hơn 45%).\n\n")
            
            # Kết luận tổng thể
            if 'overall_summary' in self.results:
                f.write(f"### Kết luận tổng thể:\n\n")
                
                if self.results['overall_summary']['avg_profit_pct'] > 0:
                    f.write(f"- Hệ thống giao dịch có lợi nhuận tổng thể dương ({self.results['overall_summary']['avg_profit_pct']:.2f}%), ")
                    f.write(f"cho thấy chiến lược hoạt động hiệu quả trong giai đoạn 3 tháng kiểm thử.\n")
                else:
                    f.write(f"- Hệ thống giao dịch có lợi nhuận tổng thể âm ({self.results['overall_summary']['avg_profit_pct']:.2f}%), ")
                    f.write(f"cần xem xét điều chỉnh chiến lược.\n")
                
                if self.results['overall_summary']['avg_win_rate'] > 50:
                    f.write(f"- Tỷ lệ thắng trung bình ({self.results['overall_summary']['avg_win_rate']:.2f}%) trên 50%, ")
                    f.write(f"cho thấy chiến lược có độ ổn định tốt.\n")
                else:
                    f.write(f"- Tỷ lệ thắng trung bình ({self.results['overall_summary']['avg_win_rate']:.2f}%) dưới 50%, ")
                    f.write(f"cần cải thiện khả năng dự đoán xu hướng thị trường.\n")
                
                if self.results['overall_summary']['avg_profit_factor'] > 1:
                    f.write(f"- Profit factor trung bình ({self.results['overall_summary']['avg_profit_factor']:.2f}) lớn hơn 1, ")
                    f.write(f"cho thấy chiến lược có lợi nhuận ổn định dài hạn.\n")
                else:
                    f.write(f"- Profit factor trung bình ({self.results['overall_summary']['avg_profit_factor']:.2f}) nhỏ hơn 1, ")
                    f.write(f"cần cải thiện tỷ lệ lợi nhuận/rủi ro của chiến lược.\n")
            
            f.write("\n## Biểu Đồ Phân Tích\n\n")
            f.write("Các biểu đồ phân tích chi tiết được lưu trong thư mục `comprehensive_test_results/charts/`.\n")
        
        logger.info(f"Đã tạo báo cáo tổng hợp: {report_path}")
        return report_path


def run_3month_comprehensive_test():
    """
    Chạy kiểm tra tổng thể 3 tháng
    """
    print("=== BẮT ĐẦU KIỂM TRA TỔNG THỂ 3 THÁNG ===")
    
    test_runner = ComprehensiveTestRunner()
    test_runner.run_comprehensive_test()
    report_path = test_runner.create_report()
    
    print(f"Đã hoàn thành kiểm tra và tạo báo cáo tại: {report_path}")
    print("=== HOÀN THÀNH KIỂM TRA ===")


if __name__ == "__main__":
    run_3month_comprehensive_test()