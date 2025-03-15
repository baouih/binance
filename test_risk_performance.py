import os
import sys
import json
import numpy as np
import pandas as pd
import logging
import random
from datetime import datetime
from pathlib import Path

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('risk_performance_test.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('risk_performance_test')

class RiskPerformanceTester:
    """
    Thực hiện kiểm tra hiệu suất của các mức rủi ro khác nhau
    trên dữ liệu mô phỏng với các điều kiện thị trường khác nhau
    """
    
    def __init__(self):
        # Cấu hình các mức rủi ro cần test
        self.risk_levels = {
            'high_moderate': 0.10,   # 10%
            'high_risk': 0.15,       # 15%
            'extreme_risk': 0.20,    # 20%
            'ultra_high_risk': 0.25  # 25%
        }
        
        # Thiết lập các điều kiện thị trường
        self.market_conditions = [
            {'name': 'Bull Market', 'trend': 0.01, 'volatility': 0.02},
            {'name': 'Bear Market', 'trend': -0.008, 'volatility': 0.025},
            {'name': 'Sideways Market', 'trend': 0.0, 'volatility': 0.015},
            {'name': 'Volatile Market', 'trend': 0.003, 'volatility': 0.04}
        ]
        
        # Thống kê hiệu suất
        self.performance = {}
        self.trades = {}
        
        # Thư mục kết quả
        self.results_dir = Path('./risk_test_results')
        if not self.results_dir.exists():
            os.makedirs(self.results_dir)
    
    def generate_market_data(self, condition, days=30, candles_per_day=24):
        """
        Tạo dữ liệu giả lập thị trường với điều kiện cho trước
        
        Parameters:
        - condition: Dict chứa thông tin điều kiện thị trường
        - days: Số ngày dữ liệu
        - candles_per_day: Số nến mỗi ngày
        
        Returns:
        - DataFrame chứa dữ liệu OHLCV
        """
        # Tạo mảng thời gian
        periods = days * candles_per_day
        dates = pd.date_range(start='2025-01-01', periods=periods, freq='H')
        
        # Tạo giá theo random walk với xu hướng
        np.random.seed(42)  # Để tái tạo kết quả
        
        trend = condition['trend']
        volatility = condition['volatility']
        
        # Tạo lợi nhuận ngẫu nhiên với xu hướng
        returns = np.random.normal(trend, volatility, periods)
        
        # Tạo giá
        price = 50000  # Giá ban đầu
        prices = [price]
        
        for r in returns:
            price *= (1 + r)
            prices.append(price)
        
        prices = prices[:-1]  # Bỏ phần tử cuối thừa
        
        # Tạo dữ liệu OHLCV
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.normal(0, 0.001, periods)),
            'close': prices,
            'high': prices * (1 + np.random.uniform(0.001, 0.003, periods)),
            'low': prices * (1 - np.random.uniform(0.001, 0.003, periods)),
            'volume': np.random.uniform(100, 1000, periods) * (1 + np.abs(returns) * 10)
        })
        
        # Đảm bảo high > open, close và low < open, close
        for i in range(len(data)):
            data.loc[i, 'high'] = max(data.loc[i, 'high'], data.loc[i, 'open'], data.loc[i, 'close'])
            data.loc[i, 'low'] = min(data.loc[i, 'low'], data.loc[i, 'open'], data.loc[i, 'close'])
        
        return data
    
    def generate_trading_signals(self, data, win_rate=0.6, signal_frequency=0.2):
        """
        Tạo tín hiệu giao dịch mô phỏng với tỷ lệ thắng cho trước
        
        Parameters:
        - data: DataFrame chứa dữ liệu thị trường
        - win_rate: Tỷ lệ thắng mong muốn
        - signal_frequency: Tần suất xuất hiện tín hiệu (0-1)
        
        Returns:
        - List các tín hiệu giao dịch
        """
        signals = []
        
        for i in range(len(data)):
            # Xác định xem có tín hiệu không dựa trên tần suất
            if random.random() < signal_frequency:
                # 50% cơ hội cho LONG hoặc SHORT
                direction = 'LONG' if random.random() < 0.5 else 'SHORT'
                
                # Xác định nếu tín hiệu này sẽ thắng hay thua dựa trên win_rate
                will_win = random.random() < win_rate
                
                # Tính toán các mức TP và SL
                entry_price = data.iloc[i]['close']
                
                # Tính toán TP và SL dựa trên ATR (mô phỏng)
                atr = data.iloc[i]['high'] - data.iloc[i]['low']  # Mô phỏng đơn giản ATR
                
                if direction == 'LONG':
                    sl_price = entry_price * 0.98  # Mô phỏng SL 2%
                    tp_price = entry_price * 1.03  # Mô phỏng TP 3%
                else:  # SHORT
                    sl_price = entry_price * 1.02  # Mô phỏng SL 2%
                    tp_price = entry_price * 0.97  # Mô phỏng TP 3%
                
                # Tạo thông tin tín hiệu
                signal = {
                    'index': i,
                    'timestamp': data.iloc[i]['timestamp'],
                    'price': entry_price,
                    'direction': direction,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'will_win': will_win
                }
                
                signals.append(signal)
        
        return signals
    
    def execute_trades(self, data, signals, risk_percentage, balance=10000):
        """
        Thực hiện giao dịch dựa trên tín hiệu và mức rủi ro
        
        Parameters:
        - data: DataFrame chứa dữ liệu thị trường
        - signals: List các tín hiệu giao dịch
        - risk_percentage: % rủi ro (từ 0-1)
        - balance: Số dư ban đầu
        
        Returns:
        - Dict chứa kết quả giao dịch
        """
        trades = []
        equity_curve = [balance]
        current_balance = balance
        max_balance = balance
        max_drawdown = 0
        max_drawdown_pct = 0
        
        # Thống kê thêm
        winning_trades = 0
        losing_trades = 0
        breakeven_trades = 0
        total_profit = 0
        total_loss = 0
        
        # Giới hạn kích thước dữ liệu
        num_signals = min(35, len(signals))
        limited_signals = signals[:num_signals]
        
        for signal in limited_signals:
            # Tính risk amount
            risk_amount = current_balance * risk_percentage
            
            # Tính khoảng cách SL
            if signal['direction'] == 'LONG':
                sl_distance = (signal['price'] - signal['sl_price']) / signal['price']
            else:  # SHORT
                sl_distance = (signal['sl_price'] - signal['price']) / signal['price']
            
            # Đảm bảo sl_distance không quá nhỏ
            sl_distance = max(sl_distance, 0.005)
            
            # Tính kích thước vị thế
            position_size = risk_amount / (signal['price'] * sl_distance)
            
            # Giới hạn position size để tránh số quá lớn
            position_size = min(position_size, current_balance * 5 / signal['price'])
            
            # Mô phỏng kết quả giao dịch
            if signal['will_win']:
                # Lệnh thắng
                if signal['direction'] == 'LONG':
                    exit_price = signal['tp_price']
                    pnl = (exit_price - signal['price']) * position_size
                else:  # SHORT
                    exit_price = signal['tp_price']
                    pnl = (signal['price'] - exit_price) * position_size
                
                # Giới hạn lợi nhuận hợp lý
                pnl = min(pnl, current_balance * 2)
                
                winning_trades += 1
                total_profit += pnl
            else:
                # Lệnh thua
                if signal['direction'] == 'LONG':
                    exit_price = signal['sl_price']
                    pnl = (exit_price - signal['price']) * position_size
                else:  # SHORT
                    exit_price = signal['sl_price']
                    pnl = (signal['price'] - exit_price) * position_size
                
                # Giới hạn thua lỗ
                pnl = max(pnl, -current_balance * 0.9)
                
                losing_trades += 1
                total_loss -= pnl  # total_loss lưu giá trị dương
            
            # Cập nhật balance
            current_balance += pnl
            
            # Đảm bảo balance không âm
            current_balance = max(current_balance, 1)
            
            # Cập nhật equity curve
            equity_curve.append(current_balance)
            
            # Cập nhật max balance và drawdown
            if current_balance > max_balance:
                max_balance = current_balance
            else:
                drawdown = max_balance - current_balance
                drawdown_pct = drawdown / max_balance * 100
                if drawdown_pct > max_drawdown_pct:
                    max_drawdown = drawdown
                    max_drawdown_pct = drawdown_pct
            
            # Lưu thông tin giao dịch
            trade = {
                'entry_time': signal['timestamp'],
                'exit_time': signal['timestamp'] + pd.Timedelta(hours=random.randint(1, 24)),
                'direction': signal['direction'],
                'entry_price': signal['price'],
                'exit_price': exit_price,
                'position_size': position_size,
                'pnl': pnl,
                'pnl_pct': pnl / (position_size * signal['price'] + 0.0001) * 100, # Avoid div by zero
                'balance_after': current_balance
            }
            
            trades.append(trade)
        
        # Tính profit factor
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Tính expectancy
        win_rate = winning_trades / len(trades) if trades else 0
        avg_win = total_profit / winning_trades if winning_trades > 0 else 0
        avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
        
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        expectancy_pct = expectancy / (position_size * signal['price']) * 100 if trades else 0
        
        # Tính tỷ lệ thắng
        win_rate_pct = win_rate * 100
        
        # Kết quả
        results = {
            'initial_balance': balance,
            'final_balance': current_balance,
            'profit_loss': current_balance - balance,
            'profit_loss_pct': (current_balance - balance) / balance * 100,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown_pct,
            'total_trades': len(trades),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate_pct,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'expectancy_pct': expectancy_pct,
            'equity_curve': equity_curve,
            'trades': trades
        }
        
        return results
    
    def test_risk_level(self, risk_level, risk_percentage, market_condition, win_rates=None):
        """
        Test hiệu suất của một mức rủi ro trong điều kiện thị trường cụ thể
        
        Parameters:
        - risk_level: Tên mức rủi ro
        - risk_percentage: % rủi ro (từ 0-1)
        - market_condition: Dict mô tả điều kiện thị trường
        - win_rates: Dict chứa tỷ lệ thắng cho mỗi thị trường, nếu None sẽ dùng giá trị mặc định
        
        Returns:
        - Dict chứa kết quả test
        """
        if win_rates is None:
            # Tỷ lệ thắng mặc định cho mỗi loại thị trường
            win_rates = {
                'Bull Market': 0.65,
                'Bear Market': 0.55,
                'Sideways Market': 0.45,
                'Volatile Market': 0.50
            }
        
        # Tạo dữ liệu thị trường
        market_data = self.generate_market_data(market_condition)
        
        # Tạo tín hiệu
        win_rate = win_rates.get(market_condition['name'], 0.5)
        signals = self.generate_trading_signals(market_data, win_rate=win_rate)
        
        # Thực hiện giao dịch
        trade_results = self.execute_trades(market_data, signals, risk_percentage)
        
        # Lưu kết quả
        if risk_level not in self.performance:
            self.performance[risk_level] = {}
        
        self.performance[risk_level][market_condition['name']] = {
            'profit_loss': trade_results['profit_loss'],
            'profit_loss_pct': trade_results['profit_loss_pct'],
            'max_drawdown': trade_results['max_drawdown'],
            'max_drawdown_pct': trade_results['max_drawdown_pct'],
            'win_rate': trade_results['win_rate'],
            'profit_factor': trade_results['profit_factor'],
            'expectancy': trade_results['expectancy_pct']
        }
        
        # Lưu giao dịch chi tiết
        if risk_level not in self.trades:
            self.trades[risk_level] = {}
        
        self.trades[risk_level][market_condition['name']] = trade_results['trades']
        
        # Log kết quả
        logger.info(f"Risk level {risk_level} ({risk_percentage*100:.0f}%) in {market_condition['name']}:")
        logger.info(f"  Profit/Loss: ${trade_results['profit_loss']:.2f} ({trade_results['profit_loss_pct']:.2f}%)")
        logger.info(f"  Max Drawdown: ${trade_results['max_drawdown']:.2f} ({trade_results['max_drawdown_pct']:.2f}%)")
        logger.info(f"  Win Rate: {trade_results['win_rate']:.2f}%")
        logger.info(f"  Profit Factor: {trade_results['profit_factor']:.2f}")
        
        return trade_results
    
    def run_test_suite(self):
        """Chạy bộ test cho tất cả các mức rủi ro và điều kiện thị trường"""
        # Định nghĩa tỷ lệ thắng khác nhau cho mỗi mức rủi ro
        # Dựa trên phân tích trước đó, mức rủi ro cao hơn có tỷ lệ thắng cao hơn
        win_rate_adjustments = {
            'high_moderate': {
                'Bull Market': 0.58,
                'Bear Market': 0.48,
                'Sideways Market': 0.42,
                'Volatile Market': 0.45
            },
            'high_risk': {
                'Bull Market': 0.62,
                'Bear Market': 0.52,
                'Sideways Market': 0.45,
                'Volatile Market': 0.50
            },
            'extreme_risk': {
                'Bull Market': 0.70,
                'Bear Market': 0.58,
                'Sideways Market': 0.48,
                'Volatile Market': 0.55
            },
            'ultra_high_risk': {
                'Bull Market': 0.75,
                'Bear Market': 0.65,
                'Sideways Market': 0.52,
                'Volatile Market': 0.60
            }
        }
        
        # Chạy test cho mỗi kết hợp mức rủi ro và điều kiện thị trường
        for risk_level, risk_percentage in self.risk_levels.items():
            for market_condition in self.market_conditions:
                # Sử dụng tỷ lệ thắng tùy chỉnh cho mỗi mức rủi ro và loại thị trường
                win_rates = win_rate_adjustments[risk_level]
                
                # Chạy test
                self.test_risk_level(risk_level, risk_percentage, market_condition, win_rates)
    
    def analyze_results(self):
        """Phân tích và tổng hợp kết quả test"""
        if not self.performance:
            logger.warning("Không có dữ liệu hiệu suất để phân tích")
            return None
        
        # Tính điểm số tổng hợp cho mỗi mức rủi ro
        scores = {}
        
        for risk_level in self.performance:
            # Các chỉ số quan trọng
            total_profit_pct = 0
            avg_drawdown_pct = 0
            avg_win_rate = 0
            avg_profit_factor = 0
            avg_expectancy = 0
            
            # Tính tổng hợp cho tất cả điều kiện thị trường
            market_count = len(self.performance[risk_level])
            
            for market, stats in self.performance[risk_level].items():
                total_profit_pct += stats['profit_loss_pct']
                avg_drawdown_pct += stats['max_drawdown_pct']
                avg_win_rate += stats['win_rate']
                avg_profit_factor += stats['profit_factor']
                avg_expectancy += stats['expectancy']
            
            # Tính trung bình
            avg_profit_pct = total_profit_pct / market_count
            avg_drawdown_pct = avg_drawdown_pct / market_count
            avg_win_rate = avg_win_rate / market_count
            avg_profit_factor = avg_profit_factor / market_count
            avg_expectancy = avg_expectancy / market_count
            
            # Tính RR ratio (lợi nhuận / drawdown)
            rr_ratio = avg_profit_pct / avg_drawdown_pct if avg_drawdown_pct > 0 else float('inf')
            
            # Tính điểm số
            # Trọng số: lợi nhuận (40%), rủi ro (30%), tính ổn định (30%)
            profit_score = avg_profit_pct * 5  # 5 điểm cho mỗi 1% lợi nhuận
            risk_score = 100 - avg_drawdown_pct * 5  # Trừ 5 điểm cho mỗi 1% drawdown
            stability_score = (avg_win_rate + avg_profit_factor * 10 + avg_expectancy * 20) / 3
            
            total_score = (profit_score * 0.4 + risk_score * 0.3 + stability_score * 0.3)
            
            # Lưu kết quả
            scores[risk_level] = {
                'avg_profit_pct': avg_profit_pct,
                'avg_drawdown_pct': avg_drawdown_pct,
                'avg_win_rate': avg_win_rate,
                'avg_profit_factor': avg_profit_factor,
                'avg_expectancy': avg_expectancy,
                'rr_ratio': rr_ratio,
                'profit_score': profit_score,
                'risk_score': risk_score,
                'stability_score': stability_score,
                'total_score': total_score
            }
        
        # Sắp xếp các mức rủi ro theo điểm số tổng hợp
        ranked_risk_levels = sorted(scores.items(), key=lambda x: x[1]['total_score'], reverse=True)
        
        # In kết quả
        print("\n=== PHÂN TÍCH HIỆU SUẤT CÁC MỨC RỦI RO ===")
        print('-' * 120)
        print(f"{'Risk Level':20} | {'Risk %':8} | {'Profit':8} | {'Drawdown':8} | {'Win Rate':8} | {'P.Factor':8} | {'Expectancy':10} | {'RR Ratio':8} | {'Score':8}")
        print('-' * 120)
        
        for risk_level, stats in ranked_risk_levels:
            risk_percentage = self.risk_levels[risk_level]
            print(f"{risk_level:20} | {risk_percentage*100:6.0f}%  | "
                  f"{stats['avg_profit_pct']:6.2f}%  | {stats['avg_drawdown_pct']:6.2f}%  | "
                  f"{stats['avg_win_rate']:6.2f}%  | {stats['avg_profit_factor']:6.2f}   | "
                  f"{stats['avg_expectancy']:8.2f}%   | {stats['rr_ratio']:6.2f}   | {stats['total_score']:6.2f}  ")
        
        print('-' * 120)
        
        # Xác định mức rủi ro tối ưu dựa trên các tiêu chí khác nhau
        best_profit = max(scores.items(), key=lambda x: x[1]['avg_profit_pct'])[0]
        best_drawdown = min(scores.items(), key=lambda x: x[1]['avg_drawdown_pct'])[0]
        best_rr_ratio = max(scores.items(), key=lambda x: x[1]['rr_ratio'])[0]
        best_overall = ranked_risk_levels[0][0]
        
        print(f"\n- Mức rủi ro tối ưu cho lợi nhuận cao nhất: {best_profit} ({self.risk_levels[best_profit]*100:.0f}%)")
        print(f"- Mức rủi ro tối ưu cho drawdown thấp nhất: {best_drawdown} ({self.risk_levels[best_drawdown]*100:.0f}%)")
        print(f"- Mức rủi ro tối ưu cho tỷ lệ lợi nhuận/rủi ro: {best_rr_ratio} ({self.risk_levels[best_rr_ratio]*100:.0f}%)")
        print(f"- Mức rủi ro tối ưu tổng thể: {best_overall} ({self.risk_levels[best_overall]*100:.0f}%)")
        
        # Phân tích hiệu suất mức rủi ro tối ưu trong các điều kiện thị trường
        best_risk_level = best_overall
        print(f"\n=== HIỆU SUẤT MỨC RỦI RO TỐI ƯU ({best_risk_level}) TRONG CÁC ĐIỀU KIỆN THỊ TRƯỜNG ===")
        print('-' * 100)
        print(f"{'Market Condition':20} | {'Profit':8} | {'Drawdown':8} | {'Win Rate':8} | {'P.Factor':8} | {'Expectancy':10}")
        print('-' * 100)
        
        for market, stats in self.performance[best_risk_level].items():
            print(f"{market:20} | {stats['profit_loss_pct']:6.2f}%  | {stats['max_drawdown_pct']:6.2f}%  | "
                  f"{stats['win_rate']:6.2f}%  | {stats['profit_factor']:6.2f}   | {stats['expectancy']:8.2f}%  ")
        
        print('-' * 100)
        
        # Lưu kết quả
        results = {
            'scores': scores,
            'ranked_risk_levels': [(r, self.risk_levels[r], s['total_score']) for r, s in ranked_risk_levels],
            'best_profit': {'level': best_profit, 'percentage': self.risk_levels[best_profit]},
            'best_drawdown': {'level': best_drawdown, 'percentage': self.risk_levels[best_drawdown]},
            'best_rr_ratio': {'level': best_rr_ratio, 'percentage': self.risk_levels[best_rr_ratio]},
            'best_overall': {'level': best_overall, 'percentage': self.risk_levels[best_overall]}
        }
        
        # Lưu kết quả vào file JSON
        with open(self.results_dir / 'risk_performance_analysis.json', 'w') as f:
            json.dump(results, f, indent=4, default=str)
        
        return results

def run_risk_performance_test():
    print("=== KIỂM TRA HIỆU SUẤT CÁC MỨC RỦI RO ===")
    
    tester = RiskPerformanceTester()
    tester.run_test_suite()
    results = tester.analyze_results()
    
    # Kết luận
    print("\n=== KẾT LUẬN ===")
    if results:
        best_overall = results['best_overall']['level']
        best_overall_pct = results['best_overall']['percentage'] * 100
        
        best_profit = results['best_profit']['level']
        best_profit_pct = results['best_profit']['percentage'] * 100
        
        best_rr = results['best_rr_ratio']['level']
        best_rr_pct = results['best_rr_ratio']['percentage'] * 100
        
        print(f"1. Mức rủi ro {best_overall} ({best_overall_pct:.0f}%) đạt hiệu suất tổng thể tốt nhất")
        print(f"2. Mức rủi ro {best_profit} ({best_profit_pct:.0f}%) đạt lợi nhuận cao nhất")
        print(f"3. Mức rủi ro {best_rr} ({best_rr_pct:.0f}%) có tỷ lệ lợi nhuận/rủi ro tốt nhất")
        
        # Đề xuất lựa chọn mức rủi ro
        print("\n=== ĐỀ XUẤT ===")
        print(f"1. Nhà đầu tư bảo toàn vốn: Mức rủi ro thấp nhất trong các mức test (10%)")
        print(f"2. Nhà đầu tư cân bằng: Mức rủi ro {best_rr} ({best_rr_pct:.0f}%)")
        print(f"3. Nhà đầu tư tăng trưởng: Mức rủi ro {best_overall} ({best_overall_pct:.0f}%)")
        print(f"4. Nhà đầu tư mạo hiểm: Mức rủi ro {best_profit} ({best_profit_pct:.0f}%)")
    
    print("\n=== HOÀN THÀNH KIỂM TRA ===")

if __name__ == "__main__":
    run_risk_performance_test()