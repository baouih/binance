#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Chương trình backtest chiến lược giao dịch hai chiều (hedge mode)
Kiểm tra hiệu suất của việc đánh cả hai hướng LONG và SHORT cùng lúc
"""

import os
import json
import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('hedge_mode_backtest.log')
    ]
)

logger = logging.getLogger('hedge_backtest')

class HedgeModeBacktester:
    """
    Lớp thực hiện backtest chiến lược đánh hai chiều (hedge mode)
    """
    
    def __init__(self, symbols, days=30, risk_level='medium', timeframe='1h', 
                 initial_balance=10000, leverage=20):
        """
        Khởi tạo backtester
        
        Args:
            symbols (list): Danh sách các cặp tiền cần test
            days (int): Số ngày test
            risk_level (str): Mức độ rủi ro (low, medium, high)
            timeframe (str): Khung thời gian (1h, 4h, 1d)
            initial_balance (float): Số dư ban đầu
            leverage (int): Đòn bẩy
        """
        self.symbols = symbols
        self.days = days
        self.risk_level = risk_level
        self.timeframe = timeframe
        self.initial_balance = initial_balance
        self.leverage = leverage
        
        # Thiết lập thông số chiến lược theo mức độ rủi ro
        self.risk_settings = {
            'low': {
                'risk_per_trade': 0.01,  # 1% mỗi lệnh
                'long_sl_percent': 0.02,  # 2% stop loss
                'long_tp_percent': 0.04,  # 4% take profit
                'short_sl_percent': 0.02,
                'short_tp_percent': 0.04,
                'max_positions': 5
            },
            'medium': {
                'risk_per_trade': 0.02,  # 2% mỗi lệnh
                'long_sl_percent': 0.05,  # 5% stop loss
                'long_tp_percent': 0.1,   # 10% take profit
                'short_sl_percent': 0.05,
                'short_tp_percent': 0.1,
                'max_positions': 7
            },
            'high': {
                'risk_per_trade': 0.03,  # 3% mỗi lệnh
                'long_sl_percent': 0.07,  # 7% stop loss
                'long_tp_percent': 0.21,  # 21% take profit
                'short_sl_percent': 0.07,
                'short_tp_percent': 0.21,
                'max_positions': 10
            }
        }
        
        # Phiên giao dịch tối ưu dựa trên báo cáo test
        self.optimal_sessions = {
            'London Open': {
                'start_time': '15:00',
                'end_time': '17:00',
                'direction': 'short',
                'win_rate': 95.0
            },
            'New York Open': {
                'start_time': '20:30',
                'end_time': '22:30',
                'direction': 'short',
                'win_rate': 90.0
            },
            'Major News Events': {
                'start_time': '21:30',
                'end_time': '22:00',
                'direction': 'short',
                'win_rate': 80.0
            },
            'Daily Candle Close': {
                'start_time': '06:30',
                'end_time': '07:30',
                'direction': 'long',
                'win_rate': 75.0
            },
            'London/NY Close': {
                'start_time': '03:00',
                'end_time': '05:00',
                'direction': 'both',
                'win_rate': 70.0
            }
        }
        
        # Kết quả backtest
        self.results = {
            'summary': {},
            'trades': [],
            'individual_symbols': {},
            'hedge_vs_single': {},
            'equity_curve': []
        }
    
    def load_historical_data(self, symbol):
        """
        Tải dữ liệu lịch sử
        
        Args:
            symbol (str): Cặp giao dịch (ví dụ BTCUSDT)
            
        Returns:
            pd.DataFrame: Dữ liệu lịch sử
        """
        try:
            # Thử tải dữ liệu từ thư mục dữ liệu
            data_dir = 'data'
            # Kiểm tra tên file thông thường và tên file có thể có trong dự án
            filenames = [
                f"{symbol}_{self.timeframe}_data.csv",
                f"{symbol}_{self.timeframe}.csv"
            ]
            
            for filename in filenames:
                filepath = os.path.join(data_dir, filename)
                if os.path.exists(filepath):
                    df = pd.read_csv(filepath)
                    
                    # Xử lý định dạng cột thời gian
                    time_columns = [col for col in df.columns if 'time' in col.lower() or 'date' in col.lower() or col == 'timestamp']
                    if time_columns:
                        time_col = time_columns[0]
                        df['timestamp'] = pd.to_datetime(df[time_col])
                    else:
                        # Nếu không có cột thời gian rõ ràng, giả định cột đầu tiên là thời gian
                        # hoặc tạo cột timestamp mới
                        if 'open_time' in df.columns:
                            df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
                        else:
                            df['timestamp'] = pd.date_range(
                                end=datetime.now(), 
                                periods=len(df), 
                                freq=self.timeframe.replace('h', 'H').replace('d', 'D')
                            )
                    
                    # Đảm bảo có các cột OHLCV
                    required_cols = ['open', 'high', 'low', 'close', 'volume']
                    rename_map = {}
                    
                    for required_col in required_cols:
                        if required_col not in df.columns:
                            # Tìm cột tương ứng (ví dụ: Open, High, Low, Close)
                            potential_cols = [col for col in df.columns if col.lower() == required_col.lower()]
                            if potential_cols:
                                rename_map[potential_cols[0]] = required_col
                    
                    if rename_map:
                        df = df.rename(columns=rename_map)
                    
                    # Lọc theo số ngày cần test
                    start_date = datetime.now() - timedelta(days=self.days)
                    df = df[df['timestamp'] >= start_date]
                    
                    logger.info(f"Đã tải dữ liệu {symbol} từ file {filename}: {len(df)} candlesticks")
                    return df
            
            logger.error(f"Không tìm thấy file dữ liệu cho {symbol} trong {data_dir}")
            return self._generate_sample_data(symbol)
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu {symbol}: {str(e)}")
            return self._generate_sample_data(symbol)
    
    def _generate_sample_data(self, symbol):
        """
        Tạo dữ liệu mẫu cho việc kiểm thử code
        
        Args:
            symbol (str): Cặp giao dịch
            
        Returns:
            pd.DataFrame: Dữ liệu mẫu
        """
        # Tạo dữ liệu mẫu dựa trên biến động thực tế của thị trường
        # Data sẽ mô phỏng một xu hướng với sóng sideway và pullback
        
        logger.warning(f"Sử dụng dữ liệu mẫu cho {symbol}. Chỉ nên dùng để kiểm thử.")
        
        # Lấy giá khởi điểm dựa trên symbol
        base_price = 0
        if symbol == 'BTCUSDT':
            base_price = 80000
        elif symbol == 'ETHUSDT':
            base_price = 1900
        elif symbol == 'BNBUSDT':
            base_price = 600
        elif symbol == 'SOLUSDT':
            base_price = 135
        else:
            base_price = 100
        
        # Tạo các mốc thời gian
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.days)
        
        # Tạo thời gian theo khung timeframe
        if self.timeframe == '1h':
            timestamps = pd.date_range(start=start_date, end=end_date, freq='H')
        elif self.timeframe == '4h':
            timestamps = pd.date_range(start=start_date, end=end_date, freq='4H')
        else:  # 1d
            timestamps = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Tạo giá theo mô hình xu hướng kết hợp sóng sideway
        n = len(timestamps)
        
        # Tạo component xu hướng (trend)
        trend = np.linspace(0, 0.2, n)  # Xu hướng tăng 20%
        
        # Tạo component sóng (waves)
        waves = 0.05 * np.sin(np.linspace(0, 10 * np.pi, n))
        
        # Tạo component nhiễu (noise)
        noise = 0.01 * np.random.randn(n)
        
        # Tạo component sideway
        sideway_mask = (np.arange(n) % (n // 3)) > (n // 4)
        sideway = np.zeros(n)
        sideway[sideway_mask] = 0.02 * np.sin(np.linspace(0, 20 * np.pi, sum(sideway_mask)))
        
        # Kết hợp tất cả components
        price_changes = trend + waves + noise + sideway
        
        # Tính giá
        multiplier = np.cumprod(1 + price_changes)
        prices = base_price * multiplier
        
        # Tạo dữ liệu OHLC
        data = []
        for i, timestamp in enumerate(timestamps):
            if i > 0:
                open_price = prices[i-1]
            else:
                open_price = base_price
            
            close_price = prices[i]
            high_price = close_price * (1 + 0.005 * np.random.random())
            low_price = open_price * (1 - 0.005 * np.random.random())
            
            # Đảm bảo high >= max(open, close) và low <= min(open, close)
            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)
            
            volume = base_price * 10 * (1 + 0.5 * np.random.random())
            
            data.append({
                'timestamp': timestamp,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def run_backtest(self):
        """
        Thực hiện backtest cho tất cả symbols
        
        Returns:
            dict: Kết quả backtest
        """
        # Lấy chiến lược theo mức độ rủi ro
        strategy_params = self.risk_settings[self.risk_level]
        
        # Khởi tạo tracking biến số
        account_balance = self.initial_balance
        equity_curve = [account_balance]
        total_trades = 0
        winning_trades = 0
        losing_trades = 0
        total_profit = 0
        total_loss = 0
        max_drawdown = 0
        highest_balance = account_balance
        trades_data = []
        single_direction_results = {}  # Lưu kết quả cho chiến lược một chiều
        hedge_results = {}  # Lưu kết quả cho chiến lược hai chiều
        
        # Chạy cho từng symbol
        for symbol in self.symbols:
            logger.info(f"Bắt đầu backtest {symbol} trong chế độ hedge mode")
            
            # Tải dữ liệu lịch sử
            df = self.load_historical_data(symbol)
            
            if df is None or len(df) == 0:
                logger.error(f"Không có dữ liệu cho {symbol}, bỏ qua")
                continue
            
            # Báo cáo số lượng dữ liệu
            logger.info(f"Backtest {symbol} với {len(df)} candlesticks, từ {df['timestamp'].min()} đến {df['timestamp'].max()}")
            
            # Theo dõi vị thế cho chiến lược một chiều và hai chiều
            long_position = None
            short_position = None
            single_direction_position = None  # chỉ LONG hoặc SHORT tại một thời điểm
            
            # Reset kết quả cho symbol này
            symbol_trades = []
            symbol_winning_trades = 0
            symbol_losing_trades = 0
            symbol_total_profit = 0
            symbol_total_loss = 0
            
            # Khởi tạo tracking cho single và hedge riêng
            single_balance = self.initial_balance
            single_equity = [single_balance]
            hedge_balance = self.initial_balance
            hedge_equity = [hedge_balance]
            
            # Lặp qua từng candlestick
            for i in range(1, len(df)):
                current_candle = df.iloc[i]
                previous_candle = df.iloc[i-1]
                
                # Lấy thời gian hiện tại từ dữ liệu
                current_time = current_candle['timestamp']
                hour = current_time.hour
                minute = current_time.minute
                current_time_str = f"{hour:02d}:{minute:02d}"
                
                # Kiểm tra xem có phải thời điểm tối ưu không
                optimal_session = None
                for session_name, session_info in self.optimal_sessions.items():
                    start_time = session_info['start_time']
                    end_time = session_info['end_time']
                    
                    # So sánh thời gian hiện tại với thời gian của phiên
                    if self._is_time_in_range(current_time_str, start_time, end_time):
                        optimal_session = session_info
                        logger.info(f"Phát hiện phiên giao dịch tối ưu: {session_name} ({start_time}-{end_time})")
                        break
                
                # Kiểm tra và đóng vị thế nếu hit SL/TP
                if long_position:
                    entry_price = long_position['entry_price']
                    stop_loss = long_position['stop_loss']
                    take_profit = long_position['take_profit']
                    
                    # Kiểm tra SL
                    if current_candle['low'] <= stop_loss:
                        # Hit stop loss
                        pnl_percent = -strategy_params['long_sl_percent']
                        position_size = long_position['position_size']
                        pnl_amount = position_size * pnl_percent
                        
                        # Cập nhật account
                        account_balance += pnl_amount
                        hedge_balance += pnl_amount
                        
                        # Thêm vào danh sách giao dịch
                        trade_data = {
                            'symbol': symbol,
                            'direction': 'LONG',
                            'entry_time': long_position['entry_time'],
                            'exit_time': current_time,
                            'entry_price': entry_price,
                            'exit_price': stop_loss,
                            'position_size': position_size,
                            'pnl_percent': pnl_percent,
                            'pnl_amount': pnl_amount,
                            'exit_reason': 'SL',
                            'strategy': 'hedge'
                        }
                        trades_data.append(trade_data)
                        symbol_trades.append(trade_data)
                        
                        # Cập nhật thống kê
                        total_trades += 1
                        losing_trades += 1
                        total_loss += abs(pnl_amount)
                        symbol_losing_trades += 1
                        symbol_total_loss += abs(pnl_amount)
                        
                        logger.info(f"LONG hit SL: {symbol} giá {stop_loss}, PNL: {pnl_percent:.2%}, Số dư: {account_balance}")
                        
                        # Reset vị thế
                        long_position = None
                    
                    # Kiểm tra TP
                    elif current_candle['high'] >= take_profit:
                        # Hit take profit
                        pnl_percent = strategy_params['long_tp_percent']
                        position_size = long_position['position_size']
                        pnl_amount = position_size * pnl_percent
                        
                        # Cập nhật account
                        account_balance += pnl_amount
                        hedge_balance += pnl_amount
                        
                        # Thêm vào danh sách giao dịch
                        trade_data = {
                            'symbol': symbol,
                            'direction': 'LONG',
                            'entry_time': long_position['entry_time'],
                            'exit_time': current_time,
                            'entry_price': entry_price,
                            'exit_price': take_profit,
                            'position_size': position_size,
                            'pnl_percent': pnl_percent,
                            'pnl_amount': pnl_amount,
                            'exit_reason': 'TP',
                            'strategy': 'hedge'
                        }
                        trades_data.append(trade_data)
                        symbol_trades.append(trade_data)
                        
                        # Cập nhật thống kê
                        total_trades += 1
                        winning_trades += 1
                        total_profit += pnl_amount
                        symbol_winning_trades += 1
                        symbol_total_profit += pnl_amount
                        
                        logger.info(f"LONG hit TP: {symbol} giá {take_profit}, PNL: {pnl_percent:.2%}, Số dư: {account_balance}")
                        
                        # Reset vị thế
                        long_position = None
                
                # Kiểm tra và đóng vị thế SHORT nếu hit SL/TP
                if short_position:
                    entry_price = short_position['entry_price']
                    stop_loss = short_position['stop_loss']
                    take_profit = short_position['take_profit']
                    
                    # Kiểm tra SL (giá lên cao hơn SL)
                    if current_candle['high'] >= stop_loss:
                        # Hit stop loss
                        pnl_percent = -strategy_params['short_sl_percent']
                        position_size = short_position['position_size']
                        pnl_amount = position_size * pnl_percent
                        
                        # Cập nhật account
                        account_balance += pnl_amount
                        hedge_balance += pnl_amount
                        
                        # Thêm vào danh sách giao dịch
                        trade_data = {
                            'symbol': symbol,
                            'direction': 'SHORT',
                            'entry_time': short_position['entry_time'],
                            'exit_time': current_time,
                            'entry_price': entry_price,
                            'exit_price': stop_loss,
                            'position_size': position_size,
                            'pnl_percent': pnl_percent,
                            'pnl_amount': pnl_amount,
                            'exit_reason': 'SL',
                            'strategy': 'hedge'
                        }
                        trades_data.append(trade_data)
                        symbol_trades.append(trade_data)
                        
                        # Cập nhật thống kê
                        total_trades += 1
                        losing_trades += 1
                        total_loss += abs(pnl_amount)
                        symbol_losing_trades += 1
                        symbol_total_loss += abs(pnl_amount)
                        
                        logger.info(f"SHORT hit SL: {symbol} giá {stop_loss}, PNL: {pnl_percent:.2%}, Số dư: {account_balance}")
                        
                        # Reset vị thế
                        short_position = None
                    
                    # Kiểm tra TP (giá xuống thấp hơn TP)
                    elif current_candle['low'] <= take_profit:
                        # Hit take profit
                        pnl_percent = strategy_params['short_tp_percent']
                        position_size = short_position['position_size']
                        pnl_amount = position_size * pnl_percent
                        
                        # Cập nhật account
                        account_balance += pnl_amount
                        hedge_balance += pnl_amount
                        
                        # Thêm vào danh sách giao dịch
                        trade_data = {
                            'symbol': symbol,
                            'direction': 'SHORT',
                            'entry_time': short_position['entry_time'],
                            'exit_time': current_time,
                            'entry_price': entry_price,
                            'exit_price': take_profit,
                            'position_size': position_size,
                            'pnl_percent': pnl_percent,
                            'pnl_amount': pnl_amount,
                            'exit_reason': 'TP',
                            'strategy': 'hedge'
                        }
                        trades_data.append(trade_data)
                        symbol_trades.append(trade_data)
                        
                        # Cập nhật thống kê
                        total_trades += 1
                        winning_trades += 1
                        total_profit += pnl_amount
                        symbol_winning_trades += 1
                        symbol_total_profit += pnl_amount
                        
                        logger.info(f"SHORT hit TP: {symbol} giá {take_profit}, PNL: {pnl_percent:.2%}, Số dư: {account_balance}")
                        
                        # Reset vị thế
                        short_position = None
                
                # Kiểm tra và đóng vị thế single direction nếu hit SL/TP
                if single_direction_position:
                    direction = single_direction_position['direction']
                    entry_price = single_direction_position['entry_price']
                    stop_loss = single_direction_position['stop_loss']
                    take_profit = single_direction_position['take_profit']
                    
                    if direction == 'LONG':
                        # Kiểm tra SL
                        if current_candle['low'] <= stop_loss:
                            # Hit stop loss
                            pnl_percent = -strategy_params['long_sl_percent']
                            position_size = single_direction_position['position_size']
                            pnl_amount = position_size * pnl_percent
                            
                            # Cập nhật account single direction
                            single_balance += pnl_amount
                            
                            # Reset vị thế
                            logger.info(f"SINGLE LONG hit SL: {symbol} giá {stop_loss}, PNL: {pnl_percent:.2%}, Số dư: {single_balance}")
                            single_direction_position = None
                        
                        # Kiểm tra TP
                        elif current_candle['high'] >= take_profit:
                            # Hit take profit
                            pnl_percent = strategy_params['long_tp_percent']
                            position_size = single_direction_position['position_size']
                            pnl_amount = position_size * pnl_percent
                            
                            # Cập nhật account single direction
                            single_balance += pnl_amount
                            
                            # Reset vị thế
                            logger.info(f"SINGLE LONG hit TP: {symbol} giá {take_profit}, PNL: {pnl_percent:.2%}, Số dư: {single_balance}")
                            single_direction_position = None
                    else:  # SHORT
                        # Kiểm tra SL (giá lên cao hơn SL)
                        if current_candle['high'] >= stop_loss:
                            # Hit stop loss
                            pnl_percent = -strategy_params['short_sl_percent']
                            position_size = single_direction_position['position_size']
                            pnl_amount = position_size * pnl_percent
                            
                            # Cập nhật account single direction
                            single_balance += pnl_amount
                            
                            # Reset vị thế
                            logger.info(f"SINGLE SHORT hit SL: {symbol} giá {stop_loss}, PNL: {pnl_percent:.2%}, Số dư: {single_balance}")
                            single_direction_position = None
                        
                        # Kiểm tra TP (giá xuống thấp hơn TP)
                        elif current_candle['low'] <= take_profit:
                            # Hit take profit
                            pnl_percent = strategy_params['short_tp_percent']
                            position_size = single_direction_position['position_size']
                            pnl_amount = position_size * pnl_percent
                            
                            # Cập nhật account single direction
                            single_balance += pnl_amount
                            
                            # Reset vị thế
                            logger.info(f"SINGLE SHORT hit TP: {symbol} giá {take_profit}, PNL: {pnl_percent:.2%}, Số dư: {single_balance}")
                            single_direction_position = None
                
                # Kiểm tra xem có mở vị thế mới không
                if optimal_session:
                    direction = optimal_session['direction']
                    
                    # HEDGE MODE: Mở đồng thời vị thế LONG và SHORT nếu chưa có
                    if direction == 'both' or direction == 'long':
                        if not long_position:
                            # Tính size vị thế dựa trên mức rủi ro
                            position_size = account_balance * strategy_params['risk_per_trade']
                            entry_price = current_candle['close']
                            stop_loss = entry_price * (1 - strategy_params['long_sl_percent'])
                            take_profit = entry_price * (1 + strategy_params['long_tp_percent'])
                            
                            # Tạo vị thế mới
                            long_position = {
                                'symbol': symbol,
                                'direction': 'LONG',
                                'entry_time': current_time,
                                'entry_price': entry_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit,
                                'position_size': position_size
                            }
                            
                            logger.info(f"Mở vị thế LONG mới: {symbol} giá {entry_price}, SL: {stop_loss}, TP: {take_profit}")
                    
                    if direction == 'both' or direction == 'short':
                        if not short_position:
                            # Tính size vị thế dựa trên mức rủi ro
                            position_size = account_balance * strategy_params['risk_per_trade']
                            entry_price = current_candle['close']
                            stop_loss = entry_price * (1 + strategy_params['short_sl_percent'])
                            take_profit = entry_price * (1 - strategy_params['short_tp_percent'])
                            
                            # Tạo vị thế mới
                            short_position = {
                                'symbol': symbol,
                                'direction': 'SHORT',
                                'entry_time': current_time,
                                'entry_price': entry_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit,
                                'position_size': position_size
                            }
                            
                            logger.info(f"Mở vị thế SHORT mới: {symbol} giá {entry_price}, SL: {stop_loss}, TP: {take_profit}")
                    
                    # SINGLE DIRECTION MODE: Chỉ mở một hướng nếu chưa có vị thế
                    if not single_direction_position:
                        # Ưu tiên hướng được chỉ định trong phiên tối ưu
                        if direction == 'both':
                            # Nếu là both, lựa chọn hướng dựa vào xu hướng gần nhất
                            if current_candle['close'] > previous_candle['close']:
                                single_direction = 'LONG'
                            else:
                                single_direction = 'SHORT'
                        else:
                            single_direction = direction.upper()
                        
                        # Tính size vị thế dựa trên mức rủi ro
                        position_size = single_balance * strategy_params['risk_per_trade']
                        entry_price = current_candle['close']
                        
                        if single_direction == 'LONG':
                            stop_loss = entry_price * (1 - strategy_params['long_sl_percent'])
                            take_profit = entry_price * (1 + strategy_params['long_tp_percent'])
                        else:  # SHORT
                            stop_loss = entry_price * (1 + strategy_params['short_sl_percent'])
                            take_profit = entry_price * (1 - strategy_params['short_tp_percent'])
                        
                        # Tạo vị thế mới
                        single_direction_position = {
                            'symbol': symbol,
                            'direction': single_direction,
                            'entry_time': current_time,
                            'entry_price': entry_price,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'position_size': position_size
                        }
                        
                        logger.info(f"Mở vị thế SINGLE {single_direction}: {symbol} giá {entry_price}, SL: {stop_loss}, TP: {take_profit}")
                
                # Cập nhật equity curve
                equity_curve.append(account_balance)
                single_equity.append(single_balance)
                hedge_equity.append(hedge_balance)
                
                # Tính drawdown
                if account_balance > highest_balance:
                    highest_balance = account_balance
                
                current_drawdown = (highest_balance - account_balance) / highest_balance
                if current_drawdown > max_drawdown:
                    max_drawdown = current_drawdown
            
            # Kết thúc backtest cho symbol này
            logger.info(f"Kết thúc backtest {symbol}")
            
            # Tính lợi nhuận và thống kê
            win_rate = 0 if (symbol_winning_trades + symbol_losing_trades) == 0 else symbol_winning_trades / (symbol_winning_trades + symbol_losing_trades)
            profit_factor = 1 if symbol_total_loss == 0 else symbol_total_profit / max(0.01, symbol_total_loss)
            
            # Lưu kết quả cho symbol này
            symbol_result = {
                'total_trades': symbol_winning_trades + symbol_losing_trades,
                'winning_trades': symbol_winning_trades,
                'losing_trades': symbol_losing_trades,
                'win_rate': win_rate,
                'total_profit': symbol_total_profit,
                'total_loss': symbol_total_loss,
                'profit_factor': profit_factor,
                'trades': symbol_trades
            }
            
            self.results['individual_symbols'][symbol] = symbol_result
            
            # So sánh kết quả hedge và single
            hedge_vs_single = {
                'hedge_balance': hedge_balance,
                'hedge_return': (hedge_balance - self.initial_balance) / self.initial_balance,
                'single_balance': single_balance,
                'single_return': (single_balance - self.initial_balance) / self.initial_balance,
                'equity_curve': {
                    'hedge': hedge_equity,
                    'single': single_equity
                }
            }
            
            self.results['hedge_vs_single'][symbol] = hedge_vs_single
        
        # Tổng kết kết quả
        win_rate = 0 if total_trades == 0 else winning_trades / total_trades
        profit_factor = 1 if total_loss == 0 else total_profit / max(0.01, total_loss)
        total_return = (account_balance - self.initial_balance) / self.initial_balance
        
        summary = {
            'initial_balance': self.initial_balance,
            'final_balance': account_balance,
            'total_return': total_return,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'test_duration_days': self.days,
            'risk_level': self.risk_level,
            'leverage': self.leverage,
            'symbols_tested': self.symbols,
            'test_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.results['summary'] = summary
        self.results['trades'] = trades_data
        self.results['equity_curve'] = equity_curve
        
        return self.results
    
    def _is_time_in_range(self, current_time, start_time, end_time):
        """
        Kiểm tra xem thời gian hiện tại có nằm trong khoảng start-end không
        
        Args:
            current_time (str): Thời gian hiện tại format 'HH:MM'
            start_time (str): Thời gian bắt đầu format 'HH:MM'
            end_time (str): Thời gian kết thúc format 'HH:MM'
            
        Returns:
            bool: True nếu thời gian nằm trong khoảng
        """
        # Chuyển đổi string thành giờ phút
        def parse_time(time_str):
            hour, minute = map(int, time_str.split(':'))
            return hour * 60 + minute
        
        current_minutes = parse_time(current_time)
        start_minutes = parse_time(start_time)
        end_minutes = parse_time(end_time)
        
        # So sánh
        if start_minutes <= end_minutes:
            # Trường hợp thông thường: start < end
            return start_minutes <= current_minutes <= end_minutes
        else:
            # Trường hợp qua ngày: start > end
            return current_minutes >= start_minutes or current_minutes <= end_minutes
    
    def save_results(self, output_dir='backtest_results'):
        """
        Lưu kết quả backtest
        
        Args:
            output_dir (str): Thư mục lưu kết quả
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Tạo tên file dựa trên thời gian và tham số
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        symbols_str = '_'.join([s.replace('USDT', '') for s in self.symbols])
        filename = f"hedge_backtest_{symbols_str}_{self.risk_level}_{self.days}days_{timestamp}"
        
        # Lưu kết quả dạng JSON
        json_path = os.path.join(output_dir, f"{filename}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        # Lưu báo cáo chi tiết dạng text
        report_path = os.path.join(output_dir, f"{filename}_report.txt")
        self._generate_text_report(report_path)
        
        # Vẽ biểu đồ equity curve
        chart_path = os.path.join(output_dir, f"{filename}_equity.png")
        self._generate_equity_chart(chart_path)
        
        logger.info(f"Đã lưu kết quả backtest vào {output_dir}")
        
        return {
            'json_path': json_path,
            'report_path': report_path,
            'chart_path': chart_path
        }
    
    def _generate_text_report(self, report_path):
        """
        Tạo báo cáo chi tiết dạng text
        
        Args:
            report_path (str): Đường dẫn file báo cáo
        """
        summary = self.results['summary']
        hedge_vs_single = self.results['hedge_vs_single']
        strategy_params = self.risk_settings[self.risk_level]
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"===== BÁO CÁO BACKTEST CHẾ ĐỘ HEDGE MODE =====\n\n")
            f.write(f"Ngày thực hiện: {summary['test_time']}\n")
            f.write(f"Số tiền ban đầu: {summary['initial_balance']} USDT\n")
            f.write(f"Số tiền cuối: {summary['final_balance']:.2f} USDT\n")
            f.write(f"Lợi nhuận: {(summary['final_balance'] - summary['initial_balance']):.2f} USDT ({summary['total_return']:.2%})\n")
            f.write(f"Drawdown tối đa: {summary['max_drawdown']:.2%}\n")
            f.write(f"Số lệnh: {summary['total_trades']}\n")
            f.write(f"Tỷ lệ thắng: {summary['win_rate']:.2%}\n")
            f.write(f"Profit Factor: {summary['profit_factor']:.2f}\n\n")
            
            f.write("SO SÁNH HEDGE MODE VỚI SINGLE DIRECTION:\n")
            f.write("-----------------------------------\n\n")
            
            for symbol, comparison in hedge_vs_single.items():
                f.write(f"Symbol: {symbol}\n")
                f.write(f"- Hedge Mode: {comparison['hedge_balance']:.2f} USDT ({comparison['hedge_return']:.2%})\n")
                f.write(f"- Single Direction: {comparison['single_balance']:.2f} USDT ({comparison['single_return']:.2%})\n")
                f.write(f"- Chênh lệch: {(comparison['hedge_balance'] - comparison['single_balance']):.2f} USDT ")
                
                if comparison['hedge_balance'] > comparison['single_balance']:
                    f.write("(HEDGE MODE TỐT HƠN)\n\n")
                else:
                    f.write("(SINGLE DIRECTION TỐT HƠN)\n\n")
            
            f.write("\nCÁC KHUNG THỜI GIAN GIAO DỊCH TỐI ƯU:\n")
            f.write("--------------------------------\n\n")
            
            for session_name, session_info in self.optimal_sessions.items():
                f.write(f"- {session_name}: {session_info['start_time']} - {session_info['end_time']}, ")
                f.write(f"Hướng: {session_info['direction'].upper()}, ")
                f.write(f"Tỷ lệ thắng: {session_info['win_rate']:.1f}%\n")
            
            f.write("\nKẾT LUẬN:\n")
            f.write("----------\n\n")
            
            # Tạo kết luận dựa trên kết quả
            hedge_better_count = sum(1 for comp in hedge_vs_single.values() if comp['hedge_balance'] > comp['single_balance'])
            total_symbols = len(hedge_vs_single)
            
            if hedge_better_count > total_symbols / 2:
                f.write(f"Chiến lược HEDGE MODE (đánh hai đầu) hiệu quả hơn cho {hedge_better_count}/{total_symbols} cặp tiền.\n")
                f.write("Nên sử dụng chiến lược HEDGE MODE trong các thời điểm biến động mạnh hoặc sideway không rõ xu hướng.\n")
                f.write("Đặc biệt hiệu quả trong phiên giao dịch London/NY Close (03:00-05:00).\n")
            else:
                f.write(f"Chiến lược SINGLE DIRECTION (đánh một đầu) hiệu quả hơn cho {total_symbols - hedge_better_count}/{total_symbols} cặp tiền.\n")
                f.write("Nên sử dụng chiến lược SINGLE DIRECTION khi thị trường có xu hướng rõ ràng.\n")
                f.write("Ưu tiên LONG trong phiên Daily Candle Close (06:30-07:30).\n")
                f.write("Ưu tiên SHORT trong phiên London Open (15:00-17:00) và New York Open (20:30-22:30).\n")
            
            # Thêm khuyến nghị về risk management
            f.write("\nKHUYẾN NGHỊ QUẢN LÝ RỦI RO:\n")
            f.write("--------------------------\n\n")
            f.write(f"1. Mỗi lệnh chỉ nên risk tối đa {strategy_params['risk_per_trade'] * 100:.1f}% tài khoản\n")
            f.write(f"2. Đòn bẩy nên giữ ở mức {self.leverage}x\n")
            f.write(f"3. Stop Loss: {strategy_params['long_sl_percent'] * 100:.1f}% cho LONG, {strategy_params['short_sl_percent'] * 100:.1f}% cho SHORT\n")
            f.write(f"4. Take Profit: {strategy_params['long_tp_percent'] * 100:.1f}% cho LONG, {strategy_params['short_tp_percent'] * 100:.1f}% cho SHORT\n")
            f.write(f"5. Số lệnh tối đa cùng lúc: {strategy_params['max_positions']}\n")
    
    def _generate_equity_chart(self, chart_path):
        """
        Vẽ biểu đồ equity curve
        
        Args:
            chart_path (str): Đường dẫn file chart
        """
        plt.figure(figsize=(12, 8))
        
        # Plot equity curve chung
        equity_curve = self.results['equity_curve']
        plt.plot(equity_curve, label='Combined Strategy', linewidth=2)
        
        # Plot equity curve cho từng symbol (hedge vs single)
        for symbol, comparison in self.results['hedge_vs_single'].items():
            hedge_equity = comparison['equity_curve']['hedge']
            single_equity = comparison['equity_curve']['single']
            
            plt.plot(hedge_equity, label=f'{symbol} Hedge', linestyle='--', alpha=0.7)
            plt.plot(single_equity, label=f'{symbol} Single', linestyle=':', alpha=0.7)
        
        plt.title('Hedge Mode vs Single Direction Backtest Results')
        plt.xlabel('Trade Number')
        plt.ylabel('Account Balance (USDT)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Thêm thông tin backtest
        summary = self.results['summary']
        info_text = (
            f"Initial Balance: {summary['initial_balance']} USDT\n"
            f"Final Balance: {summary['final_balance']:.2f} USDT\n"
            f"Return: {summary['total_return']:.2%}\n"
            f"Win Rate: {summary['win_rate']:.2%}\n"
            f"Max Drawdown: {summary['max_drawdown']:.2%}"
        )
        plt.figtext(0.02, 0.02, info_text, fontsize=10, bbox=dict(facecolor='white', alpha=0.7))
        
        plt.tight_layout()
        plt.savefig(chart_path, dpi=300)
        plt.close()


def run_backtest(symbols, risk_level='medium', days=30):
    """
    Chạy backtest và hiển thị kết quả
    
    Args:
        symbols (list): Danh sách cặp tiền cần test
        risk_level (str): Mức độ rủi ro (low, medium, high)
        days (int): Số ngày test
        
    Returns:
        dict: Kết quả backtest
    """
    logger.info(f"Bắt đầu backtest với {len(symbols)} cặp tiền, mức rủi ro {risk_level}, {days} ngày")
    
    # Khởi tạo backtester
    backtester = HedgeModeBacktester(
        symbols=symbols,
        days=days,
        risk_level=risk_level,
        timeframe='1h',
        initial_balance=10000,
        leverage=20
    )
    
    # Chạy backtest
    results = backtester.run_backtest()
    
    # Lưu kết quả
    output_files = backtester.save_results()
    
    # Hiển thị kết quả tóm tắt
    summary = results['summary']
    logger.info(f"Kết quả backtest:")
    logger.info(f"- Số dư ban đầu: {summary['initial_balance']} USDT")
    logger.info(f"- Số dư cuối: {summary['final_balance']:.2f} USDT")
    logger.info(f"- Lợi nhuận: {(summary['final_balance'] - summary['initial_balance']):.2f} USDT ({summary['total_return']:.2%})")
    logger.info(f"- Drawdown tối đa: {summary['max_drawdown']:.2%}")
    logger.info(f"- Số lệnh: {summary['total_trades']}")
    logger.info(f"- Tỷ lệ thắng: {summary['win_rate']:.2%}")
    logger.info(f"- Profit Factor: {summary['profit_factor']:.2f}")
    
    # Hiển thị so sánh hedge vs single
    logger.info("So sánh Hedge Mode với Single Direction:")
    for symbol, comparison in results['hedge_vs_single'].items():
        logger.info(f"- {symbol}: Hedge {comparison['hedge_return']:.2%} vs Single {comparison['single_return']:.2%}")
    
    logger.info(f"Đã lưu báo cáo chi tiết vào {output_files['report_path']}")
    logger.info(f"Đã lưu biểu đồ vào {output_files['chart_path']}")
    
    return results

if __name__ == "__main__":
    # Chạy backtest cho các cặp tiền phổ biến
    symbols_to_test = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT']
    results = run_backtest(symbols_to_test, risk_level='high', days=30)