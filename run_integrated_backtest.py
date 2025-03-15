#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chạy backtest tích hợp cho chiến lược thích ứng tự động 
với dữ liệu thị trường thực tế 3 tháng

Script này mô phỏng đúng cách bot thực tế hoạt động:
- Tự động phát hiện trạng thái thị trường
- Tự động chuyển đổi giữa các chiến lược
- Tự động điều chỉnh mức rủi ro dựa trên hiệu suất và điều kiện thị trường
- Phân bổ vốn động giữa các mức rủi ro khác nhau
"""

import os
import logging
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from pathlib import Path

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('integrated_backtest.log')
    ]
)

logger = logging.getLogger('integrated_backtest')

class IntegratedBacktest:
    """
    Thực hiện backtest tích hợp với khả năng thích ứng tự động
    
    Mô phỏng chính xác cách hệ thống hoạt động trong thực tế:
    - Tự động chuyển đổi giữa các chiến lược dựa trên trạng thái thị trường
    - Phân bổ vốn động giữa các mức rủi ro
    - Quản lý rủi ro tổng thể của danh mục đầu tư
    """
    
    def __init__(self, symbol='BTCUSDT', timeframe='1h', test_period=90):
        """
        Khởi tạo backtest
        
        Args:
            symbol (str): Cặp tiền tệ
            timeframe (str): Khung thời gian
            test_period (int): Số ngày dữ liệu quá khứ
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.test_period = test_period
        self.result_dir = Path('integrated_test_results')
        
        # Tạo thư mục kết quả nếu chưa tồn tại
        if not self.result_dir.exists():
            os.makedirs(self.result_dir)
        
        # Danh sách các mức rủi ro hỗ trợ
        self.risk_levels = {
            'ultra_conservative': 0.03,  # 3%
            'conservative': 0.05,        # 5%
            'moderate': 0.10,            # 10%
            'aggressive': 0.15,          # 15%
            'high_risk': 0.20,           # 20%
            'extreme_risk': 0.25,        # 25%
        }
        
        # Phân bổ vốn ban đầu cho từng mức rủi ro
        self.capital_allocation = {
            'ultra_conservative': 0.20,  # 20% 
            'conservative': 0.20,        # 20%
            'moderate': 0.20,            # 20%
            'aggressive': 0.20,          # 20%
            'high_risk': 0.15,           # 15%
            'extreme_risk': 0.05,        # 5%
        }
        
        # Trạng thái tài khoản
        self.initial_capital = 10000  # USD
        self.equity = self.initial_capital
        self.equity_curve = [self.initial_capital]
        
        # Lưu vị thế mở
        self.open_positions = []
        
        # Lưu lịch sử giao dịch
        self.trade_history = []
        
        # Theo dõi hiệu suất mỗi mức rủi ro
        self.risk_performance = {level: {'trades': 0, 'wins': 0, 'profit': 0.0} for level in self.risk_levels}
        
        logger.info(f"Đã khởi tạo backtest cho {symbol} {timeframe} với dữ liệu {test_period} ngày")
    
    def load_market_data(self):
        """
        Tải dữ liệu thị trường
        
        Returns:
            pd.DataFrame: Dữ liệu thị trường
        """
        # Tính ngày bắt đầu và kết thúc
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.test_period)
        
        logger.info(f"Tải dữ liệu {self.symbol} từ {start_date.strftime('%Y-%m-%d')} đến {end_date.strftime('%Y-%m-%d')}")
        
        # Tải dữ liệu từ file
        file_path = f"data/{self.symbol}_{self.timeframe}_data.csv"
        
        if os.path.exists(file_path):
            logger.info(f"Đang tải dữ liệu từ {file_path}")
            df = pd.read_csv(file_path)
            
            # Xử lý timestamp
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            
            # Đảm bảo tên cột chuẩn (viết hoa để phù hợp với hệ thống)
            if 'open' in df.columns and 'Open' not in df.columns:
                df = df.rename(columns={
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                })
            
            # Lấy subset data trong khoảng thời gian
            if isinstance(df.index, pd.DatetimeIndex):
                df = df.loc[start_date:end_date]
            
            logger.info(f"Đã tải {len(df)} nến cho {self.symbol}")
            return df
        else:
            logger.error(f"Không tìm thấy file dữ liệu {file_path}")
            return None
    
    def detect_market_condition(self, data_window):
        """
        Phát hiện điều kiện thị trường dựa trên cửa sổ dữ liệu
        
        Args:
            data_window (pd.DataFrame): Cửa sổ dữ liệu gần đây
            
        Returns:
            str: Điều kiện thị trường ('SIDEWAYS', 'BULL', 'BEAR', 'VOLATILE')
        """
        # Tính % thay đổi
        price_change = (data_window['Close'].iloc[-1] - data_window['Close'].iloc[0]) / data_window['Close'].iloc[0] * 100
        
        # Tính volatility
        returns = data_window['Close'].pct_change().dropna()
        volatility = returns.std() * 100  # Đổi thành phần trăm
        
        # Phân loại thị trường
        if abs(price_change) < 5:  # Biến động giá nhỏ
            if volatility < 2:
                return 'SIDEWAYS'  # Đi ngang, ít biến động
            else:
                return 'VOLATILE'  # Biến động cao nhưng không có xu hướng rõ ràng
        elif price_change > 5:  # Xu hướng tăng
            if volatility > 3:
                return 'VOLATILE'  # Tăng với biến động cao
            else:
                return 'BULL'  # Xu hướng tăng ổn định
        else:  # Xu hướng giảm
            if volatility > 3:
                return 'VOLATILE'  # Giảm với biến động cao
            else:
                return 'BEAR'  # Xu hướng giảm ổn định
    
    def get_optimal_risk_level(self, market_condition):
        """
        Chọn mức rủi ro tối ưu dựa trên điều kiện thị trường
        
        Args:
            market_condition (str): Điều kiện thị trường
            
        Returns:
            str: Mức rủi ro tối ưu (key từ self.risk_levels)
        """
        # Hiệu suất gần đây
        recent_performance = {}
        for level, perf in self.risk_performance.items():
            if perf['trades'] > 0:
                win_rate = perf['wins'] / perf['trades'] * 100
                profit_per_trade = perf['profit'] / perf['trades']
                # Điểm hiệu suất: kết hợp tỷ lệ thắng và lợi nhuận
                recent_performance[level] = win_rate * 0.6 + profit_per_trade * 40
            else:
                recent_performance[level] = 0
        
        # Chọn mức rủi ro dựa trên điều kiện thị trường và hiệu suất
        if market_condition == 'SIDEWAYS':
            # Đi ngang thường có hiệu quả tốt với rủi ro thấp
            candidates = ['ultra_conservative', 'conservative', 'moderate']
        elif market_condition == 'BULL':
            # Thị trường tăng có thể dùng rủi ro trung bình đến cao
            candidates = ['moderate', 'aggressive', 'high_risk']
        elif market_condition == 'BEAR':
            # Thị trường giảm - cẩn trọng với rủi ro trung bình
            candidates = ['conservative', 'moderate', 'aggressive']
        else:  # VOLATILE
            # Thị trường biến động mạnh - nên dùng rủi ro thấp
            candidates = ['ultra_conservative', 'conservative']
        
        # Tìm mức có hiệu suất tốt nhất trong các ứng viên
        best_level = candidates[0]
        best_score = recent_performance.get(candidates[0], 0)
        
        for level in candidates:
            if recent_performance.get(level, 0) > best_score:
                best_level = level
                best_score = recent_performance.get(level, 0)
        
        return best_level
    
    def calculate_position_size(self, entry_price, stop_loss, risk_level):
        """
        Tính kích thước vị thế dựa trên mức rủi ro
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss (float): Giá stop loss
            risk_level (float): Mức rủi ro
            
        Returns:
            float: Kích thước vị thế (số lượng)
        """
        risk_amount = self.equity * risk_level  # Số tiền chấp nhận rủi ro
        risk_per_unit = abs(entry_price - stop_loss)  # Rủi ro trên mỗi đơn vị
        
        if risk_per_unit > 0:
            position_size = risk_amount / risk_per_unit
        else:
            position_size = 0
            
        return position_size
    
    def calculate_indicators(self, data):
        """
        Tính toán các chỉ báo kỹ thuật
        
        Args:
            data (pd.DataFrame): Dữ liệu giá
            
        Returns:
            pd.DataFrame: Dữ liệu với các chỉ báo đã tính
        """
        df = data.copy()
        
        # 1. Tính RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 2. Tính MACD
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema12 - ema26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        
        # 3. Tính Bollinger Bands
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        df['STD20'] = df['Close'].rolling(window=20).std()
        df['Upper_Band'] = df['SMA20'] + (df['STD20'] * 2)
        df['Lower_Band'] = df['SMA20'] - (df['STD20'] * 2)
        
        # 4. Tính ATR (Average True Range)
        tr1 = df['High'] - df['Low']
        tr2 = abs(df['High'] - df['Close'].shift())
        tr3 = abs(df['Low'] - df['Close'].shift())
        df['TR'] = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        df['ATR'] = df['TR'].rolling(window=14).mean()
        
        # 5. Tính Stochastic Oscillator
        df['Lowest_14'] = df['Low'].rolling(window=14).min()
        df['Highest_14'] = df['High'].rolling(window=14).max()
        df['%K'] = (df['Close'] - df['Lowest_14']) / (df['Highest_14'] - df['Lowest_14']) * 100
        df['%D'] = df['%K'].rolling(window=3).mean()
        
        return df.dropna()
    
    def generate_sideways_signals(self, data, day_index, market_condition):
        """
        Tạo tín hiệu giao dịch cho thị trường đi ngang
        
        Args:
            data (pd.DataFrame): Dữ liệu với các chỉ báo
            day_index (int): Chỉ số của ngày hiện tại
            market_condition (str): Trạng thái thị trường
            
        Returns:
            list: Danh sách tín hiệu giao dịch
        """
        signals = []
        
        # Chỉ tạo tín hiệu nếu đủ dữ liệu
        if day_index < 20:
            return signals
        
        current_price = data['Close'].iloc[day_index]
        
        # Các điều kiện cụ thể cho thị trường đi ngang
        # 1. Giao dịch dựa trên Bollinger Bands trong thị trường đi ngang
        upper_band = data['Upper_Band'].iloc[day_index]
        lower_band = data['Lower_Band'].iloc[day_index]
        sma20 = data['SMA20'].iloc[day_index]
        
        # Giá tiếp cận band dưới -> tín hiệu MUA
        if current_price <= lower_band * 1.01:
            # Tính stop loss và take profit
            atr = data['ATR'].iloc[day_index]
            stop_loss = current_price - (atr * 1.5)  # Mức stop loss cách 1.5 ATR
            take_profit = current_price + (atr * 2.0)  # Mức take profit cách 2.0 ATR
            
            signals.append({
                'type': 'LONG',
                'entry_price': current_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'reason': 'Sideways - Giá chạm Bollinger Band dưới',
                'market_condition': market_condition
            })
        
        # Giá tiếp cận band trên -> tín hiệu BÁN
        elif current_price >= upper_band * 0.99:
            # Tính stop loss và take profit
            atr = data['ATR'].iloc[day_index]
            stop_loss = current_price + (atr * 1.5)  # Mức stop loss cách 1.5 ATR
            take_profit = current_price - (atr * 2.0)  # Mức take profit cách 2.0 ATR
            
            signals.append({
                'type': 'SHORT',
                'entry_price': current_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'reason': 'Sideways - Giá chạm Bollinger Band trên',
                'market_condition': market_condition
            })
        
        return signals
    
    def generate_trend_signals(self, data, day_index, market_condition):
        """
        Tạo tín hiệu giao dịch cho thị trường xu hướng (tăng/giảm)
        
        Args:
            data (pd.DataFrame): Dữ liệu với các chỉ báo
            day_index (int): Chỉ số của ngày hiện tại
            market_condition (str): Trạng thái thị trường
            
        Returns:
            list: Danh sách tín hiệu giao dịch
        """
        signals = []
        
        # Chỉ tạo tín hiệu nếu đủ dữ liệu
        if day_index < 26:
            return signals
        
        current_price = data['Close'].iloc[day_index]
        
        # Tín hiệu MACD
        macd = data['MACD'].iloc[day_index]
        macd_signal = data['MACD_Signal'].iloc[day_index]
        prev_macd = data['MACD'].iloc[day_index-1]
        prev_macd_signal = data['MACD_Signal'].iloc[day_index-1]
        
        # Tín hiệu RSI
        rsi = data['RSI'].iloc[day_index]
        prev_rsi = data['RSI'].iloc[day_index-1]
        
        # 1. Tín hiệu trong thị trường tăng
        if market_condition == 'BULL':
            # MACD cắt lên signal line trong khi MACD < 0
            if prev_macd < prev_macd_signal and macd >= macd_signal and macd < 0:
                atr = data['ATR'].iloc[day_index]
                stop_loss = current_price - (atr * 2.0)  # Stop loss rộng hơn
                take_profit = current_price + (atr * 3.0)  # Take profit xa hơn
                
                signals.append({
                    'type': 'LONG',
                    'entry_price': current_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'reason': 'Bull - MACD cắt lên signal line',
                    'market_condition': market_condition
                })
            
            # RSI thoát khỏi vùng quá bán
            elif prev_rsi < 30 and rsi >= 30:
                atr = data['ATR'].iloc[day_index]
                stop_loss = current_price - (atr * 1.5)
                take_profit = current_price + (atr * 2.5)
                
                signals.append({
                    'type': 'LONG',
                    'entry_price': current_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'reason': 'Bull - RSI thoát khỏi vùng quá bán',
                    'market_condition': market_condition
                })
        
        # 2. Tín hiệu trong thị trường giảm
        elif market_condition == 'BEAR':
            # MACD cắt xuống signal line trong khi MACD > 0
            if prev_macd > prev_macd_signal and macd <= macd_signal and macd > 0:
                atr = data['ATR'].iloc[day_index]
                stop_loss = current_price + (atr * 2.0)
                take_profit = current_price - (atr * 3.0)
                
                signals.append({
                    'type': 'SHORT',
                    'entry_price': current_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'reason': 'Bear - MACD cắt xuống signal line',
                    'market_condition': market_condition
                })
            
            # RSI thoát khỏi vùng quá mua
            elif prev_rsi > 70 and rsi <= 70:
                atr = data['ATR'].iloc[day_index]
                stop_loss = current_price + (atr * 1.5)
                take_profit = current_price - (atr * 2.5)
                
                signals.append({
                    'type': 'SHORT',
                    'entry_price': current_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'reason': 'Bear - RSI thoát khỏi vùng quá mua',
                    'market_condition': market_condition
                })
        
        return signals
    
    def run_backtest(self):
        """
        Chạy backtest tích hợp
        
        Returns:
            dict: Kết quả backtest
        """
        # Tải dữ liệu
        data = self.load_market_data()
        if data is None or len(data) == 0:
            logger.error(f"Không thể tải dữ liệu cho {self.symbol}")
            return None
        
        # Tính toán các chỉ báo
        data_with_indicators = self.calculate_indicators(data)
        
        # Đặt lại equity và equity curve
        self.equity = self.initial_capital
        self.equity_curve = [self.initial_capital]
        self.open_positions = []
        self.trade_history = []
        
        # Biến lưu thông tin hiện tại
        current_market_condition = 'NEUTRAL'
        optimal_risk_level = 'moderate'  # Mức rủi ro mặc định
        reallocation_counter = 0  # Đếm ngày từ lần phân bổ lại gần nhất
        
        # Thông tin theo dõi trạng thái
        market_conditions = []
        optimal_risk_levels = []
        
        # Chạy mô phỏng
        logger.info(f"Bắt đầu backtest tích hợp cho {self.symbol} với {len(data_with_indicators)} nến")
        
        for i in range(50, len(data_with_indicators)):
            current_date = data_with_indicators.index[i]
            current_price = data_with_indicators['Close'].iloc[i]
            
            # Cập nhật trạng thái thị trường mỗi 24 giờ (hoặc mỗi ngày với dữ liệu 1h)
            if i % 24 == 0:
                # Sử dụng cửa sổ 20 nến để xác định trạng thái thị trường
                lookback_window = data_with_indicators.iloc[i-50:i]
                current_market_condition = self.detect_market_condition(lookback_window)
                
                # Cập nhật mức rủi ro tối ưu
                optimal_risk_level = self.get_optimal_risk_level(current_market_condition)
                risk_pct = self.risk_levels[optimal_risk_level]
                
                logger.info(f"Ngày {current_date}: Thị trường {current_market_condition}, chọn mức rủi ro {optimal_risk_level} ({risk_pct*100:.1f}%)")
                
                # Tăng bộ đếm tái phân bổ
                reallocation_counter += 1
                
                # Tái phân bổ vốn mỗi 7 ngày
                if reallocation_counter >= 7:
                    reallocation_counter = 0
                    self.reallocate_capital()
            
            # Lưu trạng thái thị trường và mức rủi ro
            market_conditions.append(current_market_condition)
            optimal_risk_levels.append(optimal_risk_level)
            
            # Tạo tín hiệu giao dịch dựa trên trạng thái thị trường
            signals = []
            
            if current_market_condition == 'SIDEWAYS':
                signals = self.generate_sideways_signals(data_with_indicators, i, current_market_condition)
            elif current_market_condition in ['BULL', 'BEAR']:
                signals = self.generate_trend_signals(data_with_indicators, i, current_market_condition)
            
            # Xử lý các tín hiệu mới
            for signal in signals:
                risk_level_name = optimal_risk_level
                risk_pct = self.risk_levels[risk_level_name]
                
                # Tính toán kích thước vị thế
                position_size = self.calculate_position_size(
                    signal['entry_price'], 
                    signal['stop_loss'], 
                    risk_pct * self.capital_allocation[risk_level_name]
                )
                
                # Mở vị thế mới
                if position_size > 0:
                    position = {
                        'type': signal['type'],
                        'entry_date': current_date,
                        'entry_price': signal['entry_price'],
                        'stop_loss': signal['stop_loss'],
                        'take_profit': signal['take_profit'],
                        'size': position_size,
                        'risk_level': risk_level_name,
                        'market_condition': signal['market_condition'],
                        'reason': signal['reason']
                    }
                    
                    self.open_positions.append(position)
                    logger.debug(f"Mở {signal['type']} tại {signal['entry_price']} (SL: {signal['stop_loss']}, TP: {signal['take_profit']})")
            
            # Kiểm tra và đóng các vị thế
            j = 0
            while j < len(self.open_positions):
                position = self.open_positions[j]
                
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
                    # Tính toán P/L
                    position_risk = self.risk_levels[position['risk_level']]
                    pnl_amount = pnl_pct * position['size'] * position['entry_price']
                    
                    # Cập nhật equity
                    self.equity += pnl_amount
                    
                    # Lưu thông tin giao dịch
                    trade = {
                        'entry_date': position['entry_date'],
                        'entry_price': position['entry_price'],
                        'exit_date': current_date,
                        'exit_price': current_price,
                        'type': position['type'],
                        'pnl_pct': pnl_pct * 100,
                        'pnl_amount': pnl_amount,
                        'risk_level': position['risk_level'],
                        'market_condition': position['market_condition'],
                        'reason': position['reason'],
                        'close_reason': reason
                    }
                    self.trade_history.append(trade)
                    
                    # Cập nhật hiệu suất rủi ro
                    risk_level = position['risk_level']
                    self.risk_performance[risk_level]['trades'] += 1
                    if pnl_amount > 0:
                        self.risk_performance[risk_level]['wins'] += 1
                    self.risk_performance[risk_level]['profit'] += pnl_amount
                    
                    logger.debug(f"Đóng {position['type']} tại {current_price}, P/L: {pnl_pct*100:.2f}%, Lý do: {reason}")
                    
                    # Xóa vị thế
                    self.open_positions.pop(j)
                else:
                    j += 1
            
            # Cập nhật equity curve
            self.equity_curve.append(self.equity)
        
        # Tính thống kê backtest
        stats = self.calculate_stats()
        
        # Vẽ biểu đồ kết quả
        self.plot_results(data_with_indicators, market_conditions, optimal_risk_levels)
        
        # Lưu kết quả giao dịch
        self.save_results()
        
        logger.info(f"Kết quả backtest: P/L: {stats['profit_pct']:.2f}%, Win Rate: {stats['win_rate']:.2f}%, Trades: {stats['total_trades']}, Max DD: {stats['max_drawdown_pct']:.2f}%")
        
        return {
            'equity_curve': self.equity_curve,
            'trade_history': self.trade_history,
            'stats': stats,
            'risk_performance': self.risk_performance,
            'market_conditions': market_conditions,
            'optimal_risk_levels': optimal_risk_levels
        }
    
    def reallocate_capital(self):
        """
        Tái phân bổ vốn giữa các mức rủi ro dựa trên hiệu suất
        """
        # Tính hiệu suất của từng mức rủi ro
        performance = {}
        for level, stats in self.risk_performance.items():
            if stats['trades'] > 0:
                win_rate = stats['wins'] / stats['trades'] * 100
                avg_profit = stats['profit'] / stats['trades']
                # Điểm hiệu suất
                performance[level] = (win_rate * 0.7) + (avg_profit * 30)
            else:
                performance[level] = 0
        
        # Chỉ tiếp tục nếu có ít nhất một mức rủi ro có giao dịch
        if not performance:
            return
        
        # Tính tổng điểm hiệu suất
        total_performance = sum(performance.values())
        
        if total_performance > 0:
            # Tính tỷ lệ mới dựa trên hiệu suất
            new_allocation = {}
            for level in self.capital_allocation:
                # 50% dựa trên hiệu suất, 50% giữ nguyên phân bổ hiện tại
                new_ratio = 0.5 * (performance.get(level, 0) / total_performance) + 0.5 * self.capital_allocation[level]
                new_allocation[level] = new_ratio
            
            # Chuẩn hóa tỷ lệ để tổng = 1
            total = sum(new_allocation.values())
            self.capital_allocation = {k: v/total for k, v in new_allocation.items()}
            
            logger.info(f"Đã tái phân bổ vốn: {', '.join([f'{k}: {v*100:.1f}%' for k, v in self.capital_allocation.items()])}")
    
    def calculate_stats(self):
        """
        Tính thống kê từ kết quả backtest
        
        Returns:
            dict: Thống kê
        """
        # Số lượng giao dịch
        total_trades = len(self.trade_history)
        
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
        winning_trades = [t for t in self.trade_history if t['pnl_pct'] > 0]
        losing_trades = [t for t in self.trade_history if t['pnl_pct'] <= 0]
        
        # Tỷ lệ thắng
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        # Lợi nhuận
        profit_pct = (self.equity_curve[-1] - self.equity_curve[0]) / self.equity_curve[0] * 100
        
        # Drawdown tối đa
        drawdowns = []
        peak = self.equity_curve[0]
        for value in self.equity_curve:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100
            drawdowns.append(drawdown)
        max_drawdown_pct = max(drawdowns)
        
        # Trung bình lợi nhuận của giao dịch thắng và thua
        average_win_pct = sum([t['pnl_pct'] for t in winning_trades]) / len(winning_trades) if winning_trades else 0
        average_loss_pct = sum([t['pnl_pct'] for t in losing_trades]) / len(losing_trades) if losing_trades else 0
        
        # Profit factor
        gross_profit = sum([t['pnl_amount'] for t in winning_trades]) if winning_trades else 0
        gross_loss = abs(sum([t['pnl_amount'] for t in losing_trades])) if losing_trades else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Recovery factor
        recovery_factor = profit_pct / max_drawdown_pct if max_drawdown_pct > 0 else float('inf')
        
        # Chi tiết theo trạng thái thị trường
        market_stats = {}
        for condition in ['SIDEWAYS', 'BULL', 'BEAR', 'VOLATILE']:
            condition_trades = [t for t in self.trade_history if t['market_condition'] == condition]
            if condition_trades:
                wins = len([t for t in condition_trades if t['pnl_pct'] > 0])
                market_stats[condition] = {
                    'trades': len(condition_trades),
                    'win_rate': wins / len(condition_trades) * 100,
                    'profit': sum([t['pnl_amount'] for t in condition_trades])
                }
        
        # Chi tiết theo mức rủi ro
        risk_stats = {}
        for level in self.risk_levels:
            level_trades = [t for t in self.trade_history if t['risk_level'] == level]
            if level_trades:
                wins = len([t for t in level_trades if t['pnl_pct'] > 0])
                risk_stats[level] = {
                    'trades': len(level_trades),
                    'win_rate': wins / len(level_trades) * 100,
                    'profit': sum([t['pnl_amount'] for t in level_trades])
                }
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_pct': profit_pct,
            'max_drawdown_pct': max_drawdown_pct,
            'average_win_pct': average_win_pct,
            'average_loss_pct': average_loss_pct,
            'profit_factor': profit_factor,
            'recovery_factor': recovery_factor,
            'market_stats': market_stats,
            'risk_stats': risk_stats
        }
    
    def plot_results(self, data, market_conditions, optimal_risk_levels):
        """
        Vẽ biểu đồ kết quả backtest
        
        Args:
            data (pd.DataFrame): Dữ liệu thị trường
            market_conditions (list): Trạng thái thị trường tại mỗi điểm dữ liệu
            optimal_risk_levels (list): Mức rủi ro tối ưu tại mỗi điểm dữ liệu
        """
        # Tạo biểu đồ
        fig, axs = plt.subplots(4, 1, figsize=(14, 20), gridspec_kw={'height_ratios': [3, 1, 1, 2]})
        
        # 1. Biểu đồ giá và vị thế
        axs[0].plot(data.index[50:], data['Close'].iloc[50:], color='blue', alpha=0.6)
        axs[0].set_title(f'{self.symbol} Price Chart')
        axs[0].set_ylabel('Price')
        axs[0].grid(True)
        
        # Vẽ các điểm vào lệnh và thoát lệnh
        for trade in self.trade_history:
            if trade['type'] == 'LONG':
                # Điểm vào lệnh
                axs[0].scatter(trade['entry_date'], trade['entry_price'], color='green', marker='^', s=100)
                # Điểm thoát lệnh
                if trade['pnl_pct'] > 0:
                    axs[0].scatter(trade['exit_date'], trade['exit_price'], color='green', marker='x', s=100)
                else:
                    axs[0].scatter(trade['exit_date'], trade['exit_price'], color='red', marker='x', s=100)
            else:  # SHORT
                # Điểm vào lệnh
                axs[0].scatter(trade['entry_date'], trade['entry_price'], color='red', marker='v', s=100)
                # Điểm thoát lệnh
                if trade['pnl_pct'] > 0:
                    axs[0].scatter(trade['exit_date'], trade['exit_price'], color='green', marker='x', s=100)
                else:
                    axs[0].scatter(trade['exit_date'], trade['exit_price'], color='red', marker='x', s=100)
        
        # 2. Biểu đồ trạng thái thị trường
        market_colors = {
            'SIDEWAYS': 'blue',
            'BULL': 'green',
            'BEAR': 'red',
            'VOLATILE': 'orange',
            'NEUTRAL': 'gray'
        }
        
        # Mã hóa trạng thái thị trường thành số
        market_codes = {
            'NEUTRAL': 0,
            'SIDEWAYS': 1,
            'BULL': 2,
            'BEAR': 3,
            'VOLATILE': 4
        }
        
        market_values = [market_codes[condition] for condition in market_conditions]
        cmap = plt.cm.get_cmap('viridis', 5)
        
        axs[1].scatter(data.index[50:], market_values, c=market_values, cmap=cmap, s=10)
        axs[1].set_yticks(list(market_codes.values()))
        axs[1].set_yticklabels(list(market_codes.keys()))
        axs[1].set_title('Market Conditions')
        axs[1].grid(True)
        
        # 3. Biểu đồ mức rủi ro tối ưu
        risk_codes = {level: i for i, level in enumerate(self.risk_levels.keys())}
        risk_values = [risk_codes[level] for level in optimal_risk_levels]
        
        axs[2].scatter(data.index[50:], risk_values, c=risk_values, cmap='plasma', s=10)
        axs[2].set_yticks(list(risk_codes.values()))
        axs[2].set_yticklabels(list(risk_codes.keys()))
        axs[2].set_title('Optimal Risk Levels')
        axs[2].grid(True)
        
        # 4. Biểu đồ equity curve
        axs[3].plot(data.index[50:], self.equity_curve, color='blue')
        axs[3].set_title('Equity Curve')
        axs[3].set_ylabel('Equity (USD)')
        axs[3].grid(True)
        
        # Vẽ các vạch đánh dấu thiệt hại tối đa
        peak = self.equity_curve[0]
        max_drawdown = 0
        max_drawdown_idx = 0
        
        for i, value in enumerate(self.equity_curve):
            if value > peak:
                peak = value
            
            drawdown = (peak - value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_idx = i
        
        # Vẽ vùng drawdown lớn nhất
        if max_drawdown_idx > 0:
            # Tìm peak trước drawdown
            peak_idx = 0
            for i in range(max_drawdown_idx, 0, -1):
                if self.equity_curve[i] == peak:
                    peak_idx = i
                    break
            
            # Vẽ vùng drawdown
            axs[3].axvspan(data.index[50 + peak_idx], data.index[50 + max_drawdown_idx], alpha=0.2, color='red')
            axs[3].text(data.index[50 + peak_idx], self.equity_curve[peak_idx], f'Max DD: {max_drawdown*100:.2f}%', 
                      color='red', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.result_dir / f"{self.symbol}_{self.timeframe}_integrated_backtest.png")
        logger.info(f"Đã lưu biểu đồ tại {self.result_dir / f'{self.symbol}_{self.timeframe}_integrated_backtest.png'}")
        
        # Vẽ biểu đồ phân tích hiệu suất theo trạng thái thị trường và mức rủi ro
        self.plot_performance_analysis()
    
    def plot_performance_analysis(self):
        """
        Vẽ biểu đồ phân tích hiệu suất
        """
        # Tính thống kê
        stats = self.calculate_stats()
        
        # Phân tích theo trạng thái thị trường
        if 'market_stats' in stats and stats['market_stats']:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
            
            # Trích xuất dữ liệu
            conditions = list(stats['market_stats'].keys())
            win_rates = [stats['market_stats'][c]['win_rate'] for c in conditions]
            profits = [stats['market_stats'][c]['profit'] for c in conditions]
            trades = [stats['market_stats'][c]['trades'] for c in conditions]
            
            # Biểu đồ Win Rate theo trạng thái thị trường
            bars1 = ax1.bar(conditions, win_rates, color=['blue', 'green', 'red', 'orange'])
            ax1.set_title('Win Rate by Market Condition')
            ax1.set_ylabel('Win Rate (%)')
            ax1.set_ylim(0, 100)
            ax1.grid(True, axis='y')
            
            # Thêm nhãn số lượng giao dịch
            for i, bar in enumerate(bars1):
                ax1.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 5, f'{trades[i]} trades', 
                        ha='center', va='bottom')
            
            # Biểu đồ lợi nhuận theo trạng thái thị trường
            bars2 = ax2.bar(conditions, profits, color=['blue', 'green', 'red', 'orange'])
            ax2.set_title('Profit by Market Condition')
            ax2.set_ylabel('Profit (USD)')
            ax2.grid(True, axis='y')
            
            # Thêm nhãn
            for i, bar in enumerate(bars2):
                color = 'green' if profits[i] > 0 else 'red'
                ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + (5 if profits[i] > 0 else -15), 
                        f'${profits[i]:.2f}', ha='center', va='bottom', color=color)
            
            plt.tight_layout()
            plt.savefig(self.result_dir / f"{self.symbol}_{self.timeframe}_market_performance.png")
            logger.info(f"Đã lưu biểu đồ phân tích thị trường tại {self.result_dir / f'{self.symbol}_{self.timeframe}_market_performance.png'}")
        
        # Phân tích theo mức rủi ro
        if 'risk_stats' in stats and stats['risk_stats']:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
            
            # Trích xuất dữ liệu
            risk_levels = list(stats['risk_stats'].keys())
            win_rates = [stats['risk_stats'][r]['win_rate'] for r in risk_levels]
            profits = [stats['risk_stats'][r]['profit'] for r in risk_levels]
            trades = [stats['risk_stats'][r]['trades'] for r in risk_levels]
            
            # Biểu đồ Win Rate theo mức rủi ro
            risk_colors = ['green', 'blue', 'purple', 'orange', 'red', 'darkred']
            bars1 = ax1.bar(risk_levels, win_rates, color=risk_colors[:len(risk_levels)])
            ax1.set_title('Win Rate by Risk Level')
            ax1.set_ylabel('Win Rate (%)')
            ax1.set_ylim(0, 100)
            ax1.grid(True, axis='y')
            
            # Thêm nhãn số lượng giao dịch
            for i, bar in enumerate(bars1):
                ax1.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 5, f'{trades[i]} trades', 
                        ha='center', va='bottom')
            
            # Biểu đồ lợi nhuận theo mức rủi ro
            bars2 = ax2.bar(risk_levels, profits, color=risk_colors[:len(risk_levels)])
            ax2.set_title('Profit by Risk Level')
            ax2.set_ylabel('Profit (USD)')
            ax2.grid(True, axis='y')
            
            # Thêm nhãn
            for i, bar in enumerate(bars2):
                color = 'green' if profits[i] > 0 else 'red'
                ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + (5 if profits[i] > 0 else -15), 
                        f'${profits[i]:.2f}', ha='center', va='bottom', color=color)
            
            plt.tight_layout()
            plt.savefig(self.result_dir / f"{self.symbol}_{self.timeframe}_risk_performance.png")
            logger.info(f"Đã lưu biểu đồ phân tích rủi ro tại {self.result_dir / f'{self.symbol}_{self.timeframe}_risk_performance.png'}")
    
    def save_results(self):
        """
        Lưu kết quả backtest
        """
        # Tạo DataFrame từ lịch sử giao dịch
        if self.trade_history:
            trades_df = pd.DataFrame(self.trade_history)
            trades_file = self.result_dir / f"{self.symbol}_{self.timeframe}_trades.csv"
            trades_df.to_csv(trades_file, index=False)
            logger.info(f"Đã lưu lịch sử giao dịch tại {trades_file}")
        
        # Lưu thống kê
        stats = self.calculate_stats()
        stats_file = self.result_dir / f"{self.symbol}_{self.timeframe}_stats.json"
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=4, default=str)
        logger.info(f"Đã lưu thống kê tại {stats_file}")
        
        # Lưu equity curve
        equity_df = pd.DataFrame({'equity': self.equity_curve})
        equity_file = self.result_dir / f"{self.symbol}_{self.timeframe}_equity.csv"
        equity_df.to_csv(equity_file, index=False)
        logger.info(f"Đã lưu equity curve tại {equity_file}")

def main():
    """
    Hàm chính
    """
    # Tạo và chạy backtest
    backtest = IntegratedBacktest(symbol='BTCUSDT', timeframe='1h', test_period=90)
    results = backtest.run_backtest()
    
    if results:
        # Hiển thị kết quả
        stats = results['stats']
        print("\n=== KẾT QUẢ BACKTEST TÍCH HỢP ===")
        print(f"Tổng số giao dịch: {stats['total_trades']}")
        print(f"Tỷ lệ thắng: {stats['win_rate']:.2f}%")
        print(f"Lợi nhuận: {stats['profit_pct']:.2f}%")
        print(f"Drawdown tối đa: {stats['max_drawdown_pct']:.2f}%")
        print(f"Profit factor: {stats['profit_factor']:.2f}")
        
        # Hiển thị chi tiết theo trạng thái thị trường
        if 'market_stats' in stats:
            print("\nHiệu suất theo trạng thái thị trường:")
            for condition, cstats in stats['market_stats'].items():
                print(f"  {condition}: {cstats['trades']} giao dịch, Win Rate: {cstats['win_rate']:.2f}%, Lợi nhuận: ${cstats['profit']:.2f}")
        
        # Hiển thị chi tiết theo mức rủi ro
        if 'risk_stats' in stats:
            print("\nHiệu suất theo mức rủi ro:")
            for level, rstats in stats['risk_stats'].items():
                print(f"  {level}: {rstats['trades']} giao dịch, Win Rate: {rstats['win_rate']:.2f}%, Lợi nhuận: ${rstats['profit']:.2f}")
    
if __name__ == "__main__":
    main()