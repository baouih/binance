import sys
import os
import json
import logging
import datetime
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from binance_api import BinanceAPI
from adaptive_strategy_selector import AdaptiveStrategySelector

class SimpleBTCBacktester:
    def __init__(self):
        self.logger = logging.getLogger('simple_backtest')
        self.logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # Khởi tạo API
        self.api = BinanceAPI()
        
        # Thông số
        self.initial_balance = 10000.0  # Số dư ban đầu (USDT)
        self.risk_per_trade = 10.0      # Phần trăm rủi ro mỗi lệnh
        self.leverage = 20              # Đòn bẩy
        self.backtest_days = 30         # Số ngày backtest
        self.timeframe = '1h'           # Khung thời gian
        
        # Tạo thư mục lưu kết quả nếu chưa tồn tại
        self.results_dir = 'backtest_results/'
        self.charts_dir = 'backtest_charts/'
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.charts_dir, exist_ok=True)
        
        self.logger.info(f"Đã khởi tạo SimpleBTCBacktester, rủi ro: {self.risk_per_trade}%, đòn bẩy: {self.leverage}x")
    
    def download_historical_data(self, symbol, days=30, timeframe='1h'):
        """Tải dữ liệu lịch sử từ Binance"""
        try:
            self.logger.info(f"Đang tải dữ liệu lịch sử cho {symbol}, khung thời gian {timeframe}, {days} ngày")
            
            # Tính thời gian bắt đầu và kết thúc
            end_time = datetime.datetime.now()
            start_time = end_time - datetime.timedelta(days=days)
            
            # Convert to milliseconds timestamp
            start_ms = int(start_time.timestamp() * 1000)
            end_ms = int(end_time.timestamp() * 1000)
            
            # Lấy dữ liệu từ API
            klines = self.api.get_historical_klines(symbol, timeframe, start_ms, end_ms)
            
            if not klines:
                self.logger.error(f"Không lấy được dữ liệu cho {symbol}")
                return None
            
            # Chuyển đổi dữ liệu thành DataFrame
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 
                                               'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 
                                               'taker_buy_quote_asset_volume', 'ignore'])
            
            # Chuyển đổi kiểu dữ liệu
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume', 
                               'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
            
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Chuyển timestamp thành datetime index
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            self.logger.info(f"Đã tải {len(df)} dòng dữ liệu cho {symbol}")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Lỗi khi tải dữ liệu lịch sử cho {symbol}: {str(e)}")
            return None
    
    def apply_technical_indicators(self, df):
        """Thêm các chỉ báo kỹ thuật vào DataFrame"""
        try:
            # SMA
            df['sma'] = df['close'].rolling(window=20).mean()
            
            # Bollinger Bands
            df['std'] = df['close'].rolling(window=20).std()
            df['upper_band'] = df['sma'] + (df['std'] * 2)
            df['lower_band'] = df['sma'] - (df['std'] * 2)
            
            # RSI
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            
            rs = avg_gain / avg_loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Volume change
            df['volume_change'] = df['volume'].pct_change()
            
            # MACD
            ema12 = df['close'].ewm(span=12, adjust=False).mean()
            ema26 = df['close'].ewm(span=26, adjust=False).mean()
            df['macd'] = ema12 - ema26
            df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            
            # Đảm bảo không có giá trị NaN
            df.dropna(inplace=True)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Lỗi khi thêm chỉ báo kỹ thuật: {str(e)}")
            return df
    
    def apply_strategy(self, df):
        """Áp dụng chiến lược đơn giản"""
        try:
            # Tạo cột tín hiệu và stop loss/take profit
            df['trade_signal'] = 0
            df['stop_loss'] = 0.0
            df['take_profit'] = 0.0
            
            # Chiến lược đơn giản: Bollinger Bands và RSI
            # Mua khi giá chạm dải dưới và RSI < 30
            buy_condition = (df['close'] < df['lower_band']) & (df['rsi'] < 30)
            
            # Bán khi giá chạm dải trên và RSI > 70
            sell_condition = (df['close'] > df['upper_band']) & (df['rsi'] > 70)
            
            # Đặt tín hiệu
            df.loc[buy_condition, 'trade_signal'] = 1
            df.loc[sell_condition, 'trade_signal'] = -1
            
            # Tính Stop Loss và Take Profit
            stop_percentage = 0.025  # 2.5%
            take_percentage = 0.05   # 5%
            
            for i in range(len(df)):
                if df.iloc[i]['trade_signal'] == 1:  # Tín hiệu mua
                    entry_price = float(df.iloc[i]['close'])
                    df.at[df.index[i], 'stop_loss'] = float(entry_price * (1 - stop_percentage))
                    df.at[df.index[i], 'take_profit'] = float(entry_price * (1 + take_percentage))
                    
                elif df.iloc[i]['trade_signal'] == -1:  # Tín hiệu bán
                    entry_price = float(df.iloc[i]['close'])
                    df.at[df.index[i], 'stop_loss'] = float(entry_price * (1 + stop_percentage))
                    df.at[df.index[i], 'take_profit'] = float(entry_price * (1 - take_percentage))
            
            return df
            
        except Exception as e:
            self.logger.error(f"Lỗi khi áp dụng chiến lược: {str(e)}")
            return df
    
    def run_backtest(self, df):
        """Chạy backtest trên dữ liệu"""
        try:
            # Khởi tạo các biến
            balance = float(self.initial_balance)
            position = 0.0
            entry_price = 0.0
            stop_loss = 0.0
            take_profit = 0.0
            position_start_index = 0
            
            trades = []
            balance_history = [balance]
            
            # Điều chỉnh thông số rủi ro
            risk_per_trade = float(self.risk_per_trade) / 100.0
            position_size_pct = risk_per_trade * float(self.leverage)
            
            # Vòng lặp qua từng nến
            for i in range(1, len(df)):
                current_price = float(df.iloc[i]['close'])
                signal = df.iloc[i]['trade_signal']
                
                # Nếu đang có vị thế
                if position != 0:
                    # Kiểm tra take profit
                    if position > 0 and current_price >= take_profit:
                        profit = position * (current_price - entry_price)
                        balance += profit
                        
                        trades.append({
                            'type': 'LONG',
                            'entry_date': df.index[position_start_index].strftime('%Y-%m-%d %H:%M:%S'),
                            'exit_date': df.index[i].strftime('%Y-%m-%d %H:%M:%S'),
                            'entry_price': float(entry_price),
                            'exit_price': float(current_price),
                            'profit_pct': float((current_price / entry_price - 1) * 100),
                            'balance': float(balance)
                        })
                        
                        self.logger.info(f"TAKE PROFIT LONG BTC tại {current_price}, lợi nhuận: {profit:.2f} USDT, số dư: {balance:.2f} USDT")
                        position = 0
                        
                    # Kiểm tra stop loss
                    elif position > 0 and current_price <= stop_loss:
                        loss = position * (current_price - entry_price)
                        balance += loss
                        
                        trades.append({
                            'type': 'LONG',
                            'entry_date': df.index[position_start_index].strftime('%Y-%m-%d %H:%M:%S'),
                            'exit_date': df.index[i].strftime('%Y-%m-%d %H:%M:%S'),
                            'entry_price': float(entry_price),
                            'exit_price': float(current_price),
                            'profit_pct': float((current_price / entry_price - 1) * 100),
                            'balance': float(balance)
                        })
                        
                        self.logger.info(f"STOP LOSS LONG BTC tại {current_price}, lỗ: {loss:.2f} USDT, số dư: {balance:.2f} USDT")
                        position = 0
                    
                    # Kiểm tra tín hiệu đảo chiều
                    elif position > 0 and signal == -1:
                        profit = position * (current_price - entry_price)
                        balance += profit
                        
                        trades.append({
                            'type': 'LONG',
                            'entry_date': df.index[position_start_index].strftime('%Y-%m-%d %H:%M:%S'),
                            'exit_date': df.index[i].strftime('%Y-%m-%d %H:%M:%S'),
                            'entry_price': float(entry_price),
                            'exit_price': float(current_price),
                            'profit_pct': float((current_price / entry_price - 1) * 100),
                            'balance': float(balance)
                        })
                        
                        # Mở vị thế mới theo tín hiệu đảo chiều
                        position_start_index = i
                        position = -1 * (balance * position_size_pct / current_price)
                        entry_price = current_price
                        stop_loss = df.iloc[i]['stop_loss']
                        take_profit = df.iloc[i]['take_profit']
                        
                        self.logger.info(f"LONG -> SHORT BTC tại {current_price}, lợi nhuận: {profit:.2f} USDT, số dư: {balance:.2f} USDT")
                
                # Nếu không có vị thế
                elif position == 0:
                    if signal == 1:  # Tín hiệu mua
                        position_start_index = i
                        position = balance * position_size_pct / current_price
                        entry_price = current_price
                        stop_loss = df.iloc[i]['stop_loss']
                        take_profit = df.iloc[i]['take_profit']
                        
                        self.logger.info(f"OPEN LONG BTC tại {current_price}, kích thước: {position:.4f}, SL: {stop_loss:.2f}, TP: {take_profit:.2f}")
                        
                    elif signal == -1:  # Tín hiệu bán
                        position_start_index = i
                        position = -1 * (balance * position_size_pct / current_price)
                        entry_price = current_price
                        stop_loss = df.iloc[i]['stop_loss']
                        take_profit = df.iloc[i]['take_profit']
                        
                        self.logger.info(f"OPEN SHORT BTC tại {current_price}, kích thước: {abs(position):.4f}, SL: {stop_loss:.2f}, TP: {take_profit:.2f}")
                
                # Ghi lại số dư
                balance_history.append(balance)
            
            # Đóng vị thế cuối cùng nếu còn
            if position != 0:
                current_price = float(df.iloc[-1]['close'])
                
                if position > 0:
                    profit = position * (current_price - entry_price)
                    balance += profit
                    
                    trades.append({
                        'type': 'LONG',
                        'entry_date': df.index[position_start_index].strftime('%Y-%m-%d %H:%M:%S'),
                        'exit_date': df.index[-1].strftime('%Y-%m-%d %H:%M:%S'),
                        'entry_price': float(entry_price),
                        'exit_price': float(current_price),
                        'profit_pct': float((current_price / entry_price - 1) * 100),
                        'balance': float(balance)
                    })
                    
                    self.logger.info(f"CLOSE LONG BTC tại {current_price}, lợi nhuận: {profit:.2f} USDT, số dư cuối: {balance:.2f} USDT")
                
                else:
                    profit = -position * (entry_price - current_price)
                    balance += profit
                    
                    trades.append({
                        'type': 'SHORT',
                        'entry_date': df.index[position_start_index].strftime('%Y-%m-%d %H:%M:%S'),
                        'exit_date': df.index[-1].strftime('%Y-%m-%d %H:%M:%S'),
                        'entry_price': float(entry_price),
                        'exit_price': float(current_price),
                        'profit_pct': float((entry_price / current_price - 1) * 100),
                        'balance': float(balance)
                    })
                    
                    self.logger.info(f"CLOSE SHORT BTC tại {current_price}, lợi nhuận: {profit:.2f} USDT, số dư cuối: {balance:.2f} USDT")
            
            # Tính toán các chỉ số hiệu suất
            final_balance = balance
            profit_loss = final_balance - self.initial_balance
            profit_pct = (final_balance / self.initial_balance - 1) * 100
            
            # Tính drawdown
            peak = self.initial_balance
            drawdown = 0
            max_drawdown = 0
            
            for bal in balance_history:
                if bal > peak:
                    peak = bal
                
                dd = (peak - bal) / peak * 100
                drawdown = dd
                
                if dd > max_drawdown:
                    max_drawdown = dd
            
            # Tính các chỉ số khác
            if len(trades) > 0:
                win_trades = [t for t in trades if (t['type'] == 'LONG' and t['exit_price'] > t['entry_price']) or 
                             (t['type'] == 'SHORT' and t['exit_price'] < t['entry_price'])]
                
                win_rate = len(win_trades) / len(trades) * 100
                
                # Tính trung bình lợi nhuận và lỗ
                avg_profit = np.mean([t['profit_pct'] for t in win_trades]) if win_trades else 0
                
                lose_trades = [t for t in trades if t not in win_trades]
                avg_loss = np.mean([t['profit_pct'] for t in lose_trades]) if lose_trades else 0
                
                # Tính Profit Factor
                win_sum = sum([t['profit_pct'] for t in win_trades]) if win_trades else 0
                lose_sum = sum([abs(t['profit_pct']) for t in lose_trades]) if lose_trades else 0
                profit_factor = (win_sum / lose_sum) if lose_sum != 0 else float('inf')
            else:
                win_rate = 0
                avg_profit = 0
                avg_loss = 0
                profit_factor = 0
            
            # Kết quả backtest
            backtest_result = {
                'symbol': 'BTCUSDT',
                'initial_balance': float(self.initial_balance),
                'final_balance': float(final_balance),
                'profit_loss': float(profit_loss),
                'profit_pct': float(profit_pct),
                'max_drawdown': float(max_drawdown),
                'trades_count': len(trades),
                'win_rate': float(win_rate),
                'avg_profit': float(avg_profit),
                'avg_loss': float(avg_loss),
                'profit_factor': float(profit_factor),
                'risk_per_trade': float(self.risk_per_trade),
                'leverage': float(self.leverage),
                'trades': trades
            }
            
            return backtest_result
            
        except Exception as e:
            self.logger.error(f"Lỗi khi chạy backtest: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def plot_backtest_results(self, df, backtest_result):
        """Vẽ đồ thị kết quả backtest"""
        try:
            if backtest_result is None:
                return
                
            # Tạo figure với 3 subplot
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 12), gridspec_kw={'height_ratios': [2, 1]})
            
            # Plot 1: Giá và tín hiệu
            ax1.plot(df.index, df['close'], label='Giá đóng cửa')
            ax1.plot(df.index, df['upper_band'], 'r--', alpha=0.3, label='Upper Band')
            ax1.plot(df.index, df['lower_band'], 'g--', alpha=0.3, label='Lower Band')
            ax1.plot(df.index, df['sma'], 'y-', alpha=0.5, label='SMA')
            
            # Vẽ các tín hiệu mua
            buy_signals = df[df['trade_signal'] == 1]
            ax1.scatter(buy_signals.index, buy_signals['close'], marker='^', color='lime', s=100, label='Mua')
            
            # Vẽ các tín hiệu bán
            sell_signals = df[df['trade_signal'] == -1]
            ax1.scatter(sell_signals.index, sell_signals['close'], marker='v', color='red', s=100, label='Bán')
            
            # Vẽ các giao dịch
            for trade in backtest_result['trades']:
                entry_date = datetime.datetime.strptime(trade['entry_date'], '%Y-%m-%d %H:%M:%S')
                exit_date = datetime.datetime.strptime(trade['exit_date'], '%Y-%m-%d %H:%M:%S')
                
                if trade['type'] == 'LONG':
                    color = 'green' if trade['exit_price'] > trade['entry_price'] else 'red'
                    ax1.plot([entry_date, exit_date], 
                           [trade['entry_price'], trade['exit_price']], 
                           color=color, linewidth=2, alpha=0.7)
                else:
                    color = 'green' if trade['exit_price'] < trade['entry_price'] else 'red'
                    ax1.plot([entry_date, exit_date], 
                           [trade['entry_price'], trade['exit_price']], 
                           color=color, linewidth=2, alpha=0.7)
            
            ax1.set_title('Backtest BTC - Chiến lược Rủi ro cao')
            ax1.set_ylabel('Giá')
            ax1.grid(True)
            ax1.legend()
            
            # Plot 2: RSI
            ax2.plot(df.index, df['rsi'], label='RSI')
            ax2.axhline(y=70, color='r', linestyle='--', alpha=0.3)
            ax2.axhline(y=30, color='g', linestyle='--', alpha=0.3)
            ax2.set_ylabel('RSI')
            ax2.grid(True)
            
            plt.tight_layout()
            
            # Thêm thông tin hiệu suất
            performance_text = (
                f"Số dư ban đầu: {backtest_result['initial_balance']} USDT\n"
                f"Số dư cuối: {backtest_result['final_balance']:.2f} USDT\n"
                f"Lợi nhuận: {backtest_result['profit_loss']:.2f} USDT ({backtest_result['profit_pct']:.2f}%)\n"
                f"Drawdown tối đa: {backtest_result['max_drawdown']:.2f}%\n"
                f"Số lệnh: {backtest_result['trades_count']}\n"
                f"Tỷ lệ thắng: {backtest_result['win_rate']:.2f}%\n"
                f"Profit Factor: {backtest_result['profit_factor']:.2f}\n"
                f"Rủi ro/lệnh: {backtest_result['risk_per_trade']}%\n"
                f"Đòn bẩy: {backtest_result['leverage']}x"
            )
            
            plt.figtext(0.01, 0.01, performance_text, ha='left', fontsize=10, bbox=dict(facecolor='white', alpha=0.8))
            
            # Lưu đồ thị
            filename = f"{self.charts_dir}BTCUSDT_high_risk_backtest.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"Đã lưu đồ thị backtest tại {filename}")
            
        except Exception as e:
            self.logger.error(f"Lỗi khi vẽ đồ thị kết quả backtest: {str(e)}")
    
    def save_backtest_results(self, backtest_result):
        """Lưu kết quả backtest vào file"""
        try:
            if backtest_result is None:
                return
                
            # Lưu kết quả chi tiết
            filename = f"{self.results_dir}BTCUSDT_high_risk_backtest.json"
            
            # Tạo bản sao để lưu (loại bỏ danh sách giao dịch để giảm kích thước)
            result_to_save = backtest_result.copy()
            result_to_save.pop('trades', None)
            
            with open(filename, 'w') as f:
                json.dump(result_to_save, f, indent=4)
            
            self.logger.info(f"Đã lưu kết quả backtest tại {filename}")
            
            # Tạo báo cáo text
            text_report = "===== BÁO CÁO BACKTEST CHIẾN LƯỢC RỦI RO CAO =====\n\n"
            text_report += f"Ngày thực hiện: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            text_report += f"Symbol: BTCUSDT\n"
            text_report += f"Số ngày backtest: {self.backtest_days}\n"
            text_report += f"Khung thời gian: {self.timeframe}\n"
            text_report += f"Rủi ro mỗi lệnh: {self.risk_per_trade}%\n"
            text_report += f"Đòn bẩy: {self.leverage}x\n\n"
            
            text_report += f"Số dư ban đầu: {backtest_result['initial_balance']} USDT\n"
            text_report += f"Số dư cuối: {backtest_result['final_balance']:.2f} USDT\n"
            text_report += f"Lợi nhuận: {backtest_result['profit_loss']:.2f} USDT ({backtest_result['profit_pct']:.2f}%)\n"
            text_report += f"Drawdown tối đa: {backtest_result['max_drawdown']:.2f}%\n"
            text_report += f"Số lệnh: {backtest_result['trades_count']}\n"
            text_report += f"Tỷ lệ thắng: {backtest_result['win_rate']:.2f}%\n"
            text_report += f"Trung bình lãi mỗi lệnh thắng: {backtest_result['avg_profit']:.2f}%\n"
            text_report += f"Trung bình lỗ mỗi lệnh thua: {backtest_result['avg_loss']:.2f}%\n"
            text_report += f"Profit Factor: {backtest_result['profit_factor']:.2f}\n\n"
            
            text_report += "DANH SÁCH GIAO DỊCH:\n"
            for i, trade in enumerate(backtest_result['trades']):
                profit = trade['exit_price'] - trade['entry_price'] if trade['type'] == 'LONG' else trade['entry_price'] - trade['exit_price']
                result = "THẮNG" if ((trade['type'] == 'LONG' and profit > 0) or (trade['type'] == 'SHORT' and profit < 0)) else "THUA"
                
                text_report += f"{i+1}. {trade['type']} {trade['entry_date']} -> {trade['exit_date']}, "
                text_report += f"Giá vào: {trade['entry_price']:.2f}, Giá ra: {trade['exit_price']:.2f}, "
                text_report += f"P/L: {trade['profit_pct']:.2f}%, Kết quả: {result}\n"
            
            # Lưu báo cáo text
            report_filename = f"{self.results_dir}BTCUSDT_high_risk_backtest_report.txt"
            with open(report_filename, 'w') as f:
                f.write(text_report)
            
            self.logger.info(f"Đã lưu báo cáo backtest chi tiết tại {report_filename}")
            
        except Exception as e:
            self.logger.error(f"Lỗi khi lưu kết quả backtest: {str(e)}")
    
    def run(self):
        """Hàm chính để thực hiện backtest"""
        # Tải dữ liệu lịch sử
        df = self.download_historical_data('BTCUSDT', days=self.backtest_days, timeframe=self.timeframe)
        
        if df is None or len(df) < 20:
            self.logger.error("Không đủ dữ liệu cho BTCUSDT, dừng backtest.")
            return
        
        # Thêm chỉ báo kỹ thuật
        df = self.apply_technical_indicators(df)
        
        # Áp dụng chiến lược
        df = self.apply_strategy(df)
        
        # Chạy backtest
        backtest_result = self.run_backtest(df)
        
        # Vẽ đồ thị kết quả
        self.plot_backtest_results(df, backtest_result)
        
        # Lưu kết quả
        self.save_backtest_results(backtest_result)
        
        # In kết quả
        if backtest_result is not None:
            print("\n===== KẾT QUẢ BACKTEST BTC =====")
            print(f"Lợi nhuận: {backtest_result['profit_pct']:.2f}%")
            print(f"Số lệnh: {backtest_result['trades_count']}")
            print(f"Tỷ lệ thắng: {backtest_result['win_rate']:.2f}%")
            print(f"Profit Factor: {backtest_result['profit_factor']:.2f}")
            print(f"Max Drawdown: {backtest_result['max_drawdown']:.2f}%")
            print(f"Xem báo cáo chi tiết tại {self.results_dir}BTCUSDT_high_risk_backtest_report.txt")
        
        return backtest_result

if __name__ == "__main__":
    backtester = SimpleBTCBacktester()
    backtester.run()