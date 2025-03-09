#!/usr/bin/env python3
"""
Demo bot giao dịch với cấu hình rủi ro cao cho tài khoản nhỏ (100 USD)

Script này mô phỏng hiệu suất bot giao dịch với cấu hình chấp nhận
mức rủi ro cao (30-50% vốn) để đánh giá khả năng sinh lời và rủi ro.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional

# Import cấu hình rủi ro cao
from config_high_risk import (
    INITIAL_BALANCE, MAX_ACCOUNT_RISK, RISK_PER_TRADE, 
    MAX_LEVERAGE, OPTIMAL_LEVERAGE, MIN_DISTANCE_TO_LIQUIDATION,
    VOLATILITY_THRESHOLD, RSI_LOWER, RSI_UPPER, MIN_RISK_REWARD,
    SCALPING_STOP_LOSS, SCALPING_TAKE_PROFIT, TREND_STOP_LOSS, TREND_TAKE_PROFIT,
    USE_TRAILING_STOP, TRAILING_ACTIVATION, TRAILING_CALLBACK, MAX_MARGIN_USAGE
)

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("high_risk_demo")

# Tạo thư mục kết quả nếu chưa tồn tại
os.makedirs("high_risk_results", exist_ok=True)

class HighRiskTrader:
    """Demo bot giao dịch với cấu hình rủi ro cao"""
    
    def __init__(self, 
                initial_balance=INITIAL_BALANCE, 
                max_leverage=MAX_LEVERAGE,
                risk_per_trade=RISK_PER_TRADE,
                max_account_risk=MAX_ACCOUNT_RISK):
        """
        Khởi tạo bot với cấu hình rủi ro cao
        
        Args:
            initial_balance (float): Số dư ban đầu (USD)
            max_leverage (int): Đòn bẩy tối đa
            risk_per_trade (float): Rủi ro mỗi giao dịch (%)
            max_account_risk (float): Rủi ro tối đa cho tài khoản (%)
        """
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.max_leverage = max_leverage
        self.risk_per_trade = risk_per_trade
        self.max_account_risk = max_account_risk
        
        self.total_risk_amount = 0  # Tổng số tiền đang có rủi ro
        
        # Lịch sử số dư và giao dịch
        self.balance_history = []
        self.equity_history = []
        self.trades = []
        
        # Trạng thái hiện tại
        self.open_positions = {}  # ID -> position_info
        self.next_position_id = 0
        
        logger.info(f"Khởi tạo HighRiskTrader: Balance=${initial_balance}, "
                   f"MaxLeverage=x{max_leverage}, Risk={risk_per_trade}%, "
                   f"MaxAccountRisk={max_account_risk}%")
    
    def create_price_series(self, days=30, price_points_per_day=24) -> pd.DataFrame:
        """
        Tạo chuỗi giá mẫu
        
        Args:
            days (int): Số ngày dữ liệu
            price_points_per_day (int): Số điểm giá mỗi ngày
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu giá mẫu
        """
        total_points = days * price_points_per_day
        
        # Thời gian bắt đầu
        start_time = datetime.now() - timedelta(days=days)
        
        # Tạo dữ liệu thời gian
        time_interval = timedelta(days=days) / total_points
        timestamps = [start_time + i * time_interval for i in range(total_points)]
        
        # Tạo giá mẫu với các xu hướng và biến động khác nhau
        initial_price = 35000.0
        
        # Các giai đoạn thị trường, điều chỉnh để tạo thêm biến động
        # 1. Giai đoạn đi ngang (20%)
        # 2. Giai đoạn tăng (25%)
        # 3. Giai đoạn biến động cao (30%) 
        # 4. Giai đoạn giảm (25%)
        
        segment_sizes = [
            int(total_points * 0.2),  # Đi ngang
            int(total_points * 0.25),  # Tăng
            int(total_points * 0.3),  # Biến động cao (tăng tỷ lệ này cho high risk)
            int(total_points * 0.25)   # Giảm
        ]
        
        # Đảm bảo tổng đúng bằng total_points
        extra_points = total_points - sum(segment_sizes)
        segment_sizes[0] += extra_points
        
        # Volatility và trend cho từng giai đoạn - tăng biến động lên cho high risk
        segment_params = [
            {'volatility': 0.003, 'trend': 0.0001},  # Đi ngang
            {'volatility': 0.004, 'trend': 0.0025},  # Tăng
            {'volatility': 0.009, 'trend': 0.0000},  # Biến động cao
            {'volatility': 0.005, 'trend': -0.0025}  # Giảm
        ]
        
        # Tạo giá cho từng giai đoạn
        current_price = initial_price
        all_prices = []
        
        for i, segment_size in enumerate(segment_sizes):
            volatility = segment_params[i]['volatility']
            trend = segment_params[i]['trend']
            
            segment_prices = [current_price]
            for j in range(1, segment_size):
                # Tạo giá với xu hướng và biến động ngẫu nhiên
                rnd = np.random.randn()
                change = trend + volatility * rnd
                price = segment_prices[-1] * (1 + change)
                segment_prices.append(price)
            
            all_prices.extend(segment_prices)
            current_price = segment_prices[-1]
        
        # Tạo dữ liệu OHLCV
        df = pd.DataFrame()
        df['timestamp'] = timestamps
        df['close'] = all_prices
        
        # Tạo open, high, low từ close
        df['open'] = df['close'].shift(1).fillna(df['close'])
        df['high'] = df.apply(lambda row: max(row['open'], row['close']) * (1 + np.random.uniform(0, 0.003)), axis=1)
        df['low'] = df.apply(lambda row: min(row['open'], row['close']) * (1 - np.random.uniform(0, 0.003)), axis=1)
        
        # Tạo volume
        df['volume'] = np.random.uniform(10, 100, total_points) * np.abs(df['close'] - df['open']) / df['open'] * 1000
        
        # Reset index
        df = df.reset_index(drop=True)
        
        logger.info(f"Đã tạo chuỗi giá mẫu với {total_points} điểm giá")
        
        return df
    
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các chỉ báo kỹ thuật cần thiết
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            
        Returns:
            pd.DataFrame: DataFrame với các chỉ báo đã thêm
        """
        # RSI
        window_length = 14
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=window_length).mean()
        avg_loss = loss.rolling(window=window_length).mean()
        
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=14).mean()
        
        # Bollinger Bands
        df['sma20'] = df['close'].rolling(window=20).mean()
        std20 = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['sma20'] + 2 * std20
        df['bb_lower'] = df['sma20'] - 2 * std20
        
        # EMA
        df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # Stochastic
        low_14 = df['low'].rolling(window=14).min()
        high_14 = df['high'].rolling(window=14).max()
        df['stoch_k'] = 100 * ((df['close'] - low_14) / (high_14 - low_14))
        df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
        
        # Loại bỏ hàng NaN
        df.dropna(inplace=True)
        
        return df
    
    def calculate_position_size(self, entry_price: float, stop_loss: float, leverage: int) -> Tuple[float, Dict]:
        """
        Tính toán kích thước vị thế tối ưu với cấu hình rủi ro cao
        
        Args:
            entry_price (float): Giá dự kiến vào lệnh
            stop_loss (float): Giá dự kiến stop loss
            leverage (int): Đòn bẩy dự kiến sử dụng
            
        Returns:
            Tuple[float, Dict]: (Kích thước vị thế, Chi tiết)
        """
        # Tính khoảng cách % từ entry đến stop loss
        if entry_price > stop_loss:  # Long position
            stop_distance_percent = (entry_price - stop_loss) / entry_price * 100
            side = "buy"
        else:  # Short position
            stop_distance_percent = (stop_loss - entry_price) / entry_price * 100
            side = "sell"
        
        # Tính số tiền rủi ro
        risk_amount = self.current_balance * (self.risk_per_trade / 100)
        
        # Kiểm tra tổng rủi ro tài khoản
        if self.total_risk_amount + risk_amount > self.current_balance * (self.max_account_risk / 100):
            # Vượt quá rủi ro tài khoản, điều chỉnh lại
            available_risk = max(0, self.current_balance * (self.max_account_risk / 100) - self.total_risk_amount)
            if available_risk <= 0:
                # Không còn rủi ro khả dụng
                return 0, {'error': 'Đã đạt rủi ro tài khoản tối đa'}
            risk_amount = available_risk
        
        # Tính kích thước vị thế (USD)
        position_size_usd = (risk_amount / stop_distance_percent) * 100 * leverage
        
        # Số lượng Bitcoin
        quantity = position_size_usd / entry_price
        
        # Kiểm tra điểm thanh lý (liquidation)
        if side == "buy":
            liquidation_price = entry_price * (1 - (1 / leverage) + 0.004)  # 0.4% duy trì margin
            liquidation_distance = (entry_price - liquidation_price) / entry_price * 100
        else:  # sell
            liquidation_price = entry_price * (1 + (1 / leverage) - 0.004)
            liquidation_distance = (liquidation_price - entry_price) / entry_price * 100
            
        # Kiểm tra xem stop loss có quá gần điểm thanh lý - sử dụng giá trị từ cấu hình high risk
        if liquidation_distance * (1 - MIN_DISTANCE_TO_LIQUIDATION/100) > stop_distance_percent:
            # Stop loss quá gần điểm thanh lý, điều chỉnh lại kích thước vị thế
            adjustment_factor = stop_distance_percent / (liquidation_distance * (1 - MIN_DISTANCE_TO_LIQUIDATION/100))
            position_size_usd *= adjustment_factor
            quantity = position_size_usd / entry_price
            
            logger.info(f"Điều chỉnh kích thước vị thế do stop loss quá gần điểm thanh lý: "
                      f"${position_size_usd:.2f}, quantity={quantity:.8f}")
        
        # Giới hạn kích thước vị thế tối đa theo % margin
        max_size = self.current_balance * (MAX_MARGIN_USAGE/100) * leverage
        if position_size_usd > max_size:
            position_size_usd = max_size
            quantity = position_size_usd / entry_price
            
            logger.info(f"Giới hạn kích thước vị thế tối đa ({MAX_MARGIN_USAGE}% margin): "
                      f"${position_size_usd:.2f}, quantity={quantity:.8f}")
        
        details = {
            'side': side,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'leverage': leverage,
            'risk_amount': risk_amount,
            'risk_percent': risk_amount / self.current_balance * 100,
            'position_size_usd': position_size_usd,
            'quantity': quantity,
            'margin_used': position_size_usd / leverage,
            'stop_distance_percent': stop_distance_percent,
            'liquidation_price': liquidation_price,
            'liquidation_distance_percent': liquidation_distance
        }
        
        return position_size_usd, details
    
    def generate_signals(self, df: pd.DataFrame, idx: int, strategy: str) -> Dict:
        """
        Tạo tín hiệu giao dịch theo chiến lược đã chọn
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            idx (int): Chỉ số hàng hiện tại
            strategy (str): Chiến lược giao dịch ('scalping', 'trend', 'combined')
            
        Returns:
            Dict: Tín hiệu giao dịch
        """
        if strategy == 'scalping':
            return self._generate_scalping_signal(df, idx)
        elif strategy == 'trend':
            return self._generate_trend_signal(df, idx)
        elif strategy == 'combined':
            # Kết hợp cả hai chiến lược khi rủi ro cao
            scalping_signal = self._generate_scalping_signal(df, idx)
            if scalping_signal['signal'] != 'neutral':
                return scalping_signal
                
            return self._generate_trend_signal(df, idx)
        else:
            return {'signal': 'neutral'}
    
    def _generate_scalping_signal(self, df: pd.DataFrame, idx: int) -> Dict:
        """
        Tạo tín hiệu scalping với cấu hình rủi ro cao
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            idx (int): Chỉ số hàng hiện tại
            
        Returns:
            Dict: Tín hiệu giao dịch
        """
        signal = {'signal': 'neutral'}
        
        # Lấy giá và chỉ báo hiện tại
        current_price = df['close'].iloc[idx]
        current_rsi = df['rsi'].iloc[idx]
        prev_rsi = df['rsi'].iloc[idx-1] if idx > 0 else 50
        
        current_macd = df['macd'].iloc[idx]
        current_macd_signal = df['macd_signal'].iloc[idx]
        
        # Tính biến động
        atr = df['atr'].iloc[idx]
        volatility = (atr / current_price) * 100
        
        # Sử dụng ngưỡng biến động từ cấu hình rủi ro cao
        if volatility < VOLATILITY_THRESHOLD:
            return signal
        
        # Tính leverage dựa trên biến động - sử dụng nhiều đòn bẩy hơn cho rủi ro cao
        if volatility < 2.0:
            leverage = min(MAX_LEVERAGE, OPTIMAL_LEVERAGE)
        elif volatility < 4.0:
            leverage = min(14, OPTIMAL_LEVERAGE)
        elif volatility < 6.0:
            leverage = min(10, OPTIMAL_LEVERAGE)
        else:
            leverage = min(8, OPTIMAL_LEVERAGE)
        
        # Tín hiệu mua - sử dụng ngưỡng RSI từ cấu hình rủi ro cao
        if current_rsi < RSI_LOWER and prev_rsi < current_rsi and current_macd > current_macd_signal:
            signal['signal'] = 'buy'
            signal['entry_price'] = current_price
            signal['stop_loss'] = current_price * (1 - SCALPING_STOP_LOSS/100)  # Stop loss từ cấu hình
            signal['take_profit'] = current_price * (1 + SCALPING_TAKE_PROFIT/100)  # Take profit từ cấu hình
            signal['leverage'] = leverage
            signal['strategy'] = 'scalping'
            
        # Tín hiệu bán - sử dụng ngưỡng RSI từ cấu hình rủi ro cao
        elif current_rsi > RSI_UPPER and prev_rsi > current_rsi and current_macd < current_macd_signal:
            signal['signal'] = 'sell'
            signal['entry_price'] = current_price
            signal['stop_loss'] = current_price * (1 + SCALPING_STOP_LOSS/100)  # Stop loss từ cấu hình
            signal['take_profit'] = current_price * (1 - SCALPING_TAKE_PROFIT/100)  # Take profit từ cấu hình
            signal['leverage'] = leverage
            signal['strategy'] = 'scalping'
        
        # Tính kích thước vị thế nếu có tín hiệu
        if signal['signal'] != 'neutral':
            position_size, details = self.calculate_position_size(
                entry_price=signal['entry_price'],
                stop_loss=signal['stop_loss'],
                leverage=signal['leverage']
            )
            
            # Nếu không thể tính kích thước vị thế
            if position_size <= 0:
                return {'signal': 'neutral'}
                
            signal.update(details)
            
            # Kiểm tra tỷ lệ risk-reward
            if signal['side'] == 'buy':
                risk = signal['entry_price'] - signal['stop_loss']
                reward = signal['take_profit'] - signal['entry_price']
            else:  # 'sell'
                risk = signal['stop_loss'] - signal['entry_price']
                reward = signal['entry_price'] - signal['take_profit']
                
            risk_reward_ratio = reward / risk if risk > 0 else 0
            
            # Nếu risk-reward không đạt ngưỡng tối thiểu
            if risk_reward_ratio < MIN_RISK_REWARD:
                return {'signal': 'neutral'}
        
        return signal
    
    def _generate_trend_signal(self, df: pd.DataFrame, idx: int) -> Dict:
        """
        Tạo tín hiệu theo xu hướng với cấu hình rủi ro cao
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            idx (int): Chỉ số hàng hiện tại
            
        Returns:
            Dict: Tín hiệu giao dịch
        """
        signal = {'signal': 'neutral'}
        
        # Lấy giá và chỉ báo hiện tại
        current_price = df['close'].iloc[idx]
        
        # MACD
        current_macd = df['macd'].iloc[idx]
        current_macd_signal = df['macd_signal'].iloc[idx]
        prev_macd = df['macd'].iloc[idx-1] if idx > 0 else 0
        prev_macd_signal = df['macd_signal'].iloc[idx-1] if idx > 0 else 0
        
        # EMA
        ema9 = df['ema9'].iloc[idx]
        ema21 = df['ema21'].iloc[idx]
        prev_ema9 = df['ema9'].iloc[idx-1] if idx > 0 else 0
        prev_ema21 = df['ema21'].iloc[idx-1] if idx > 0 else 0
        
        # Tính biến động
        atr = df['atr'].iloc[idx]
        volatility = (atr / current_price) * 100
        
        # Tính leverage dựa trên biến động - sử dụng nhiều đòn bẩy hơn cho rủi ro cao
        if volatility < 2.0:
            leverage = min(MAX_LEVERAGE, OPTIMAL_LEVERAGE)
        elif volatility < 4.0:
            leverage = min(14, OPTIMAL_LEVERAGE)
        elif volatility < 6.0:
            leverage = min(10, OPTIMAL_LEVERAGE)
        else:
            leverage = min(8, OPTIMAL_LEVERAGE)
        
        # Tín hiệu mua
        buy_condition1 = prev_macd < prev_macd_signal and current_macd > current_macd_signal  # MACD cắt lên
        buy_condition2 = prev_ema9 < prev_ema21 and ema9 > ema21  # EMA cắt lên
        buy_condition3 = current_macd > current_macd_signal and current_macd > prev_macd and ema9 > ema21  # Xác nhận xu hướng
        
        if buy_condition1 or buy_condition2 or buy_condition3:
            signal['signal'] = 'buy'
            signal['entry_price'] = current_price
            signal['stop_loss'] = current_price * (1 - TREND_STOP_LOSS/100)  # Stop loss từ cấu hình
            signal['take_profit'] = current_price * (1 + TREND_TAKE_PROFIT/100)  # Take profit từ cấu hình
            signal['leverage'] = leverage
            signal['strategy'] = 'trend'
            
        # Tín hiệu bán
        sell_condition1 = prev_macd > prev_macd_signal and current_macd < current_macd_signal  # MACD cắt xuống
        sell_condition2 = prev_ema9 > prev_ema21 and ema9 < ema21  # EMA cắt xuống
        sell_condition3 = current_macd < current_macd_signal and current_macd < prev_macd and ema9 < ema21  # Xác nhận xu hướng
        
        if sell_condition1 or sell_condition2 or sell_condition3:
            signal['signal'] = 'sell'
            signal['entry_price'] = current_price
            signal['stop_loss'] = current_price * (1 + TREND_STOP_LOSS/100)  # Stop loss từ cấu hình
            signal['take_profit'] = current_price * (1 - TREND_TAKE_PROFIT/100)  # Take profit từ cấu hình
            signal['leverage'] = leverage
            signal['strategy'] = 'trend'
        
        # Tính kích thước vị thế nếu có tín hiệu
        if signal['signal'] != 'neutral':
            position_size, details = self.calculate_position_size(
                entry_price=signal['entry_price'],
                stop_loss=signal['stop_loss'],
                leverage=signal['leverage']
            )
            
            # Nếu không thể tính kích thước vị thế
            if position_size <= 0:
                return {'signal': 'neutral'}
                
            signal.update(details)
            
            # Kiểm tra tỷ lệ risk-reward
            if signal['side'] == 'buy':
                risk = signal['entry_price'] - signal['stop_loss']
                reward = signal['take_profit'] - signal['entry_price']
            else:  # 'sell'
                risk = signal['stop_loss'] - signal['entry_price']
                reward = signal['entry_price'] - signal['take_profit']
                
            risk_reward_ratio = reward / risk if risk > 0 else 0
            
            # Nếu risk-reward không đạt ngưỡng tối thiểu
            if risk_reward_ratio < MIN_RISK_REWARD:
                return {'signal': 'neutral'}
        
        return signal
    
    def open_position(self, signal: Dict, current_time) -> int:
        """
        Mở vị thế mới
        
        Args:
            signal (Dict): Tín hiệu giao dịch
            current_time: Thời gian hiện tại
            
        Returns:
            int: ID của vị thế đã mở, -1 nếu không thể mở
        """
        if signal['signal'] == 'neutral':
            return -1
            
        # Thêm thông tin thời gian
        position_info = signal.copy()
        position_info['entry_time'] = current_time
        position_info['position_id'] = self.next_position_id
        position_info['unrealized_pnl'] = 0
        
        # Thiết lập trailing stop nếu được cấu hình
        if USE_TRAILING_STOP:
            position_info['use_trailing_stop'] = True
            position_info['trailing_activation'] = TRAILING_ACTIVATION
            position_info['trailing_callback'] = TRAILING_CALLBACK
            position_info['trailing_stop_price'] = None
            position_info['trailing_activated'] = False
            
            # Tính giá kích hoạt trailing
            if position_info['side'] == 'buy':
                position_info['trailing_activation_price'] = position_info['entry_price'] * (1 + position_info['trailing_activation']/100)
            else:  # 'sell'
                position_info['trailing_activation_price'] = position_info['entry_price'] * (1 - position_info['trailing_activation']/100)
        
        # Ghi nhận vị thế mới
        self.open_positions[self.next_position_id] = position_info
        
        # Cập nhật tổng rủi ro
        self.total_risk_amount += position_info['risk_amount']
        
        # Tăng ID cho vị thế tiếp theo
        position_id = self.next_position_id
        self.next_position_id += 1
        
        logger.info(f"Giao dịch #{position_id} đã mở: {position_info['side'].upper()}, "
                  f"Strategy={position_info['strategy']}, "
                  f"Entry=${position_info['entry_price']:.2f}, Stop=${position_info['stop_loss']:.2f}, "
                  f"TP=${position_info['take_profit']:.2f}, Leverage=x{position_info['leverage']}, "
                  f"Size=${position_info['position_size_usd']:.2f}, Quantity={position_info['quantity']:.8f}")
                  
        return position_id
    
    def update_positions(self, current_price: float, current_time) -> List[Dict]:
        """
        Cập nhật tất cả các vị thế mở với giá hiện tại
        
        Args:
            current_price (float): Giá hiện tại
            current_time: Thời gian hiện tại
            
        Returns:
            List[Dict]: Danh sách các vị thế đã đóng
        """
        closed_positions = []
        positions_to_close = []
        
        # Tính equity hiện tại
        current_equity = self.current_balance
        
        # Kiểm tra từng vị thế
        for position_id, position in self.open_positions.items():
            # Tính P&L hiện tại
            if position['side'] == 'buy':
                unrealized_pnl = (current_price - position['entry_price']) * position['quantity']
                pnl_percent = (current_price - position['entry_price']) / position['entry_price'] * 100 * position['leverage']
            else:  # 'sell'
                unrealized_pnl = (position['entry_price'] - current_price) * position['quantity']
                pnl_percent = (position['entry_price'] - current_price) / position['entry_price'] * 100 * position['leverage']
            
            # Cập nhật unrealized P&L
            position['unrealized_pnl'] = unrealized_pnl
            
            # Cập nhật equity
            current_equity += unrealized_pnl
            
            # Flag để kiểm tra đóng vị thế
            close_position = False
            close_reason = ""
            
            # Kiểm tra điều kiện đóng vị thế
            if position['side'] == 'buy':
                # Kiểm tra stop loss
                if current_price <= position['stop_loss']:
                    close_position = True
                    close_reason = "stop_loss"
                # Kiểm tra take profit
                elif current_price >= position['take_profit']:
                    close_position = True
                    close_reason = "take_profit"
                # Kiểm tra trailing stop
                elif position.get('use_trailing_stop', False) and position.get('trailing_activated', False) and position.get('trailing_stop_price') is not None:
                    if current_price <= position['trailing_stop_price']:
                        close_position = True
                        close_reason = "trailing_stop"
                        
                # Cập nhật trailing stop nếu cần
                if position.get('use_trailing_stop', False):
                    # Nếu chưa kích hoạt, kiểm tra điều kiện kích hoạt
                    if not position['trailing_activated'] and current_price >= position['trailing_activation_price']:
                        position['trailing_activated'] = True
                        position['trailing_stop_price'] = current_price * (1 - position['trailing_callback']/100)
                        logger.info(f"Trailing stop kích hoạt cho vị thế #{position_id} tại ${current_price:.2f}")
                    
                    # Nếu đã kích hoạt, cập nhật giá trailing stop
                    elif position['trailing_activated']:
                        new_trailing_stop = current_price * (1 - position['trailing_callback']/100)
                        if new_trailing_stop > position['trailing_stop_price']:
                            position['trailing_stop_price'] = new_trailing_stop
            else:  # 'sell'
                # Kiểm tra stop loss
                if current_price >= position['stop_loss']:
                    close_position = True
                    close_reason = "stop_loss"
                # Kiểm tra take profit
                elif current_price <= position['take_profit']:
                    close_position = True
                    close_reason = "take_profit"
                # Kiểm tra trailing stop
                elif position.get('use_trailing_stop', False) and position.get('trailing_activated', False) and position.get('trailing_stop_price') is not None:
                    if current_price >= position['trailing_stop_price']:
                        close_position = True
                        close_reason = "trailing_stop"
                        
                # Cập nhật trailing stop nếu cần
                if position.get('use_trailing_stop', False):
                    # Nếu chưa kích hoạt, kiểm tra điều kiện kích hoạt
                    if not position['trailing_activated'] and current_price <= position['trailing_activation_price']:
                        position['trailing_activated'] = True
                        position['trailing_stop_price'] = current_price * (1 + position['trailing_callback']/100)
                        logger.info(f"Trailing stop kích hoạt cho vị thế #{position_id} tại ${current_price:.2f}")
                    
                    # Nếu đã kích hoạt, cập nhật giá trailing stop
                    elif position['trailing_activated']:
                        new_trailing_stop = current_price * (1 + position['trailing_callback']/100)
                        if new_trailing_stop < position['trailing_stop_price']:
                            position['trailing_stop_price'] = new_trailing_stop
            
            # Nếu cần đóng vị thế
            if close_position:
                positions_to_close.append((position_id, close_reason))
        
        # Lưu equity hiện tại
        self.equity_history.append({
            'timestamp': current_time,
            'equity': current_equity
        })
        
        # Đóng các vị thế đã đánh dấu
        for position_id, reason in positions_to_close:
            closed_position = self.close_position(position_id, current_price, current_time, reason)
            closed_positions.append(closed_position)
            
        return closed_positions
    
    def close_position(self, position_id: int, exit_price: float, exit_time, exit_reason: str) -> Dict:
        """
        Đóng vị thế
        
        Args:
            position_id (int): ID vị thế cần đóng
            exit_price (float): Giá đóng vị thế
            exit_time: Thời gian đóng vị thế
            exit_reason (str): Lý do đóng vị thế
            
        Returns:
            Dict: Thông tin vị thế đã đóng
        """
        if position_id not in self.open_positions:
            logger.error(f"Không tìm thấy vị thế #{position_id}")
            return {}
            
        position = self.open_positions[position_id]
        
        # Tính P&L thực tế
        if position['side'] == 'buy':
            pnl = (exit_price - position['entry_price']) * position['quantity']
            pnl_percent = (exit_price - position['entry_price']) / position['entry_price'] * 100 * position['leverage']
        else:  # 'sell'
            pnl = (position['entry_price'] - exit_price) * position['quantity']
            pnl_percent = (position['entry_price'] - exit_price) / position['entry_price'] * 100 * position['leverage']
        
        # Cập nhật thông tin vị thế
        position['exit_price'] = exit_price
        position['exit_time'] = exit_time
        position['exit_reason'] = exit_reason
        position['pnl'] = pnl
        position['pnl_percent'] = pnl_percent
        
        # Cập nhật số dư
        self.current_balance += pnl
        
        # Giảm rủi ro tổng
        self.total_risk_amount -= position['risk_amount']
        
        # Lưu vị thế vào lịch sử giao dịch
        self.trades.append(position.copy())
        
        # Lưu số dư mới vào lịch sử
        self.balance_history.append({
            'timestamp': exit_time,
            'balance': self.current_balance
        })
        
        # Xóa khỏi danh sách vị thế mở
        del self.open_positions[position_id]
        
        logger.info(f"Giao dịch #{position_id} đã đóng: {position['side'].upper()}, "
                  f"Strategy={position['strategy']}, "
                  f"Entry=${position['entry_price']:.2f}, Exit=${exit_price:.2f}, "
                  f"P&L=${pnl:.2f} ({pnl_percent:+.2f}%), Balance=${self.current_balance:.2f}, "
                  f"Lý do: {exit_reason}")
                  
        return position
    
    def run_backtest(self, strategy: str = 'combined', days: int = 30) -> Dict:
        """
        Chạy backtest với cấu hình rủi ro cao
        
        Args:
            strategy (str): Chiến lược giao dịch ('scalping', 'trend', 'combined')
            days (int): Số ngày mô phỏng
            
        Returns:
            Dict: Kết quả backtest
        """
        logger.info(f"Bắt đầu backtest với chiến lược {strategy}, vốn ${self.initial_balance}, "
                   f"MaxRisk={self.max_account_risk}%")
        
        # Tạo dữ liệu giá mẫu
        df = self.create_price_series(days=days)
        
        # Thêm các chỉ báo
        df = self.add_indicators(df)
        
        # Lưu số dư ban đầu
        self.balance_history.append({
            'timestamp': df['timestamp'].iloc[0],
            'balance': self.current_balance
        })
        
        self.equity_history.append({
            'timestamp': df['timestamp'].iloc[0],
            'equity': self.current_balance
        })
        
        # Chạy mô phỏng
        for idx in range(len(df)):
            current_time = df['timestamp'].iloc[idx]
            current_price = df['close'].iloc[idx]
            
            # Cập nhật các vị thế mở
            closed_positions = self.update_positions(current_price, current_time)
            
            # Tạo tín hiệu mới
            signal = self.generate_signals(df, idx, strategy)
            
            # Mở vị thế mới nếu có tín hiệu và chưa đạt số vị thế tối đa
            if signal['signal'] != 'neutral' and len(self.open_positions) < 3:
                self.open_position(signal, current_time)
        
        # Đóng tất cả vị thế còn lại
        final_price = df['close'].iloc[-1]
        final_time = df['timestamp'].iloc[-1]
        
        for position_id in list(self.open_positions.keys()):
            self.close_position(position_id, final_price, final_time, "end_of_test")
        
        # Tính toán kết quả
        results = self._calculate_results()
        
        # Vẽ biểu đồ
        self._plot_results(df, strategy, results)
        
        return results
    
    def _calculate_results(self) -> Dict:
        """
        Tính toán kết quả backtest
        
        Returns:
            Dict: Kết quả backtest
        """
        if not self.trades:
            return {
                'status': 'No trades executed',
                'initial_balance': self.initial_balance,
                'final_balance': self.current_balance
            }
        
        # Tổng quan
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t['pnl'] > 0)
        losing_trades = total_trades - winning_trades
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Phân tích P&L
        total_profit = sum(t['pnl'] for t in self.trades if t['pnl'] > 0)
        total_loss = abs(sum(t['pnl'] for t in self.trades if t['pnl'] <= 0))
        net_profit = total_profit - total_loss
        
        # Profit factor
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # P&L trung bình
        avg_profit = total_profit / winning_trades if winning_trades > 0 else 0
        avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
        
        # P&L theo chiến lược
        strategy_performance = {}
        for strategy in set(t.get('strategy', 'unknown') for t in self.trades):
            strategy_trades = [t for t in self.trades if t.get('strategy', 'unknown') == strategy]
            strategy_wins = sum(1 for t in strategy_trades if t['pnl'] > 0)
            
            strategy_performance[strategy] = {
                'trades': len(strategy_trades),
                'wins': strategy_wins,
                'losses': len(strategy_trades) - strategy_wins,
                'win_rate': strategy_wins / len(strategy_trades) if len(strategy_trades) > 0 else 0,
                'profit': sum(t['pnl'] for t in strategy_trades),
                'avg_leverage': sum(t['leverage'] for t in strategy_trades) / len(strategy_trades)
            }
        
        # Phân tích drawdown
        equity_values = [entry['equity'] for entry in self.equity_history]
        peak = equity_values[0]
        drawdowns = []
        
        for equity in equity_values:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak * 100 if peak > 0 else 0
            drawdowns.append(drawdown)
            
        max_drawdown = max(drawdowns) if drawdowns else 0
        
        # ROI
        roi = (self.current_balance - self.initial_balance) / self.initial_balance * 100
        
        # Thống kê vị thế
        avg_position_size = sum(t['position_size_usd'] for t in self.trades) / total_trades if total_trades > 0 else 0
        avg_leverage = sum(t['leverage'] for t in self.trades) / total_trades if total_trades > 0 else 0
        
        # Phân tích theo lý do thoát
        exit_reasons = {}
        for reason in set(t['exit_reason'] for t in self.trades):
            reason_trades = [t for t in self.trades if t['exit_reason'] == reason]
            reason_wins = sum(1 for t in reason_trades if t['pnl'] > 0)
            
            exit_reasons[reason] = {
                'count': len(reason_trades),
                'wins': reason_wins,
                'win_rate': reason_wins / len(reason_trades) if len(reason_trades) > 0 else 0,
                'profit': sum(t['pnl'] for t in reason_trades)
            }
        
        return {
            'initial_balance': self.initial_balance,
            'final_balance': self.current_balance,
            'net_profit': net_profit,
            'roi': roi,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'max_drawdown': max_drawdown,
            'strategy_performance': strategy_performance,
            'avg_position_size': avg_position_size,
            'avg_leverage': avg_leverage,
            'exit_reasons': exit_reasons,
            'risk_settings': {
                'risk_per_trade': self.risk_per_trade,
                'max_account_risk': self.max_account_risk,
                'max_leverage': self.max_leverage
            }
        }
    
    def _plot_results(self, df: pd.DataFrame, strategy: str, results: Dict):
        """
        Vẽ biểu đồ kết quả backtest
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            strategy (str): Chiến lược giao dịch
            results (Dict): Kết quả backtest
        """
        # Vẽ biểu đồ chính
        plt.figure(figsize=(15, 12))
        
        # Subplot 1: Giá và các giao dịch
        plt.subplot(3, 1, 1)
        plt.plot(df['timestamp'], df['close'], label='Close Price')
        
        # Vẽ các điểm entry/exit
        for trade in self.trades:
            entry_time = trade['entry_time']
            exit_time = trade['exit_time']
            entry_price = trade['entry_price']
            exit_price = trade['exit_price']
            
            # Màu dựa trên chiến lược
            if trade['strategy'] == 'scalping':
                color_base = 'blue'
            elif trade['strategy'] == 'trend':
                color_base = 'green'
            else:
                color_base = 'purple'
            
            if trade['side'] == 'buy':
                plt.scatter(entry_time, entry_price, marker='^', color=color_base, s=100)
                if trade['pnl'] > 0:
                    plt.scatter(exit_time, exit_price, marker='o', color='g', s=100)
                else:
                    plt.scatter(exit_time, exit_price, marker='o', color='r', s=100)
            else:  # 'sell'
                plt.scatter(entry_time, entry_price, marker='v', color=color_base, s=100)
                if trade['pnl'] > 0:
                    plt.scatter(exit_time, exit_price, marker='o', color='g', s=100)
                else:
                    plt.scatter(exit_time, exit_price, marker='o', color='r', s=100)
        
        plt.title(f'Price Chart with Trades - {strategy.capitalize()} Strategy')
        plt.ylabel('Price ($)')
        plt.grid(True, alpha=0.3)
        
        # Subplot 2: Equity curve
        plt.subplot(3, 1, 2)
        
        # Balance history
        balance_times = [entry['timestamp'] for entry in self.balance_history]
        balances = [entry['balance'] for entry in self.balance_history]
        plt.plot(balance_times, balances, label='Account Balance', color='blue')
        
        # Equity history
        equity_times = [entry['timestamp'] for entry in self.equity_history]
        equities = [entry['equity'] for entry in self.equity_history]
        plt.plot(equity_times, equities, label='Equity', color='green', alpha=0.7)
        
        # Initial balance
        plt.axhline(y=self.initial_balance, color='r', linestyle='--', label=f'Initial Balance (${self.initial_balance})')
        
        # Target risk level
        risk_level = self.initial_balance * (1 - self.max_account_risk/100)
        plt.axhline(y=risk_level, color='orange', linestyle='--', label=f'Max Risk Level (${risk_level:.2f})')
        
        plt.title('Equity and Balance Curves')
        plt.ylabel('Value ($)')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Subplot 3: Drawdown
        plt.subplot(3, 1, 3)
        
        # Tính drawdown từ equity
        equity_values = [entry['equity'] for entry in self.equity_history]
        equity_times = [entry['timestamp'] for entry in self.equity_history]
        
        peak = equity_values[0]
        drawdowns = []
        
        for equity in equity_values:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak * 100 if peak > 0 else 0
            drawdowns.append(drawdown)
        
        plt.fill_between(equity_times, drawdowns, color='red', alpha=0.3)
        plt.axhline(y=self.max_account_risk, color='orange', linestyle='--', label=f'Max Risk ({self.max_account_risk}%)')
        
        plt.title('Drawdown (%)')
        plt.ylabel('Drawdown (%)')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Tạo tiêu đề chung
        title = f'High Risk Trading Results: ${self.initial_balance} Initial Balance'
        subtitle = f'Strategy: {strategy.capitalize()}, Final Balance: ${results["final_balance"]:.2f} (ROI: {results["roi"]:+.2f}%)'
        info = f'Win Rate: {results["win_rate"]:.2%}, Profit Factor: {results["profit_factor"]:.2f}, Max Drawdown: {results["max_drawdown"]:.2f}%'
        
        plt.suptitle(f'{title}\n{subtitle}\n{info}', fontsize=16)
        
        # Chỉnh định dạng và lưu
        plt.tight_layout(rect=[0, 0, 1, 0.90])
        plt.savefig(f"high_risk_results/high_risk_{strategy}.png")
        
        logger.info(f"Đã lưu biểu đồ kết quả vào high_risk_results/high_risk_{strategy}.png")

def run_high_risk_test():
    """Chạy kiểm thử với cấu hình rủi ro cao"""
    strategies = ['scalping', 'trend', 'combined']
    results = {}
    
    for strategy in strategies:
        # Khởi tạo trader với cấu hình rủi ro cao
        trader = HighRiskTrader(
            initial_balance=INITIAL_BALANCE,
            max_leverage=MAX_LEVERAGE,
            risk_per_trade=RISK_PER_TRADE,
            max_account_risk=MAX_ACCOUNT_RISK
        )
        
        # Chạy backtest
        result = trader.run_backtest(strategy=strategy, days=30)
        
        # Lưu kết quả
        results[strategy] = result
    
    # So sánh kết quả
    print("\n===== KẾT QUẢ GIAO DỊCH RỦI RO CAO (30-50% VỐN) =====")
    print(f"Vốn ban đầu: ${INITIAL_BALANCE:.2f}")
    print(f"Rủi ro tối đa tài khoản: {MAX_ACCOUNT_RISK:.1f}%")
    print(f"Rủi ro mỗi giao dịch: {RISK_PER_TRADE:.1f}%")
    print(f"Đòn bẩy tối đa: x{MAX_LEVERAGE}")
    
    print("\nHiệu suất các chiến lược:")
    for strategy, result in results.items():
        print(f"\n  {strategy.upper()}:")
        print(f"    Số dư cuối: ${result['final_balance']:.2f}")
        print(f"    ROI: {result['roi']:+.2f}%")
        print(f"    Số giao dịch: {result['total_trades']}")
        print(f"    Win rate: {result['win_rate']:.2%}")
        print(f"    Profit factor: {result['profit_factor']:.2f}")
        print(f"    Drawdown tối đa: {result['max_drawdown']:.2f}%")
        
        # Phân tích theo chiến lược (cho combined)
        if strategy == 'combined' and 'strategy_performance' in result:
            print("\n    Phân tích theo chiến lược:")
            for substrat, perf in result['strategy_performance'].items():
                print(f"      - {substrat}: {perf['trades']} giao dịch, "
                     f"Win rate {perf['win_rate']:.2%}, "
                     f"P&L ${perf['profit']:.2f}, "
                     f"Leverage x{perf['avg_leverage']:.1f}")
    
    # Khuyến nghị
    best_strategy = max(results.keys(), key=lambda s: results[s]['roi'])
    worst_drawdown = max(results.keys(), key=lambda s: results[s]['max_drawdown'])
    
    print(f"\nChiến lược tốt nhất: {best_strategy.upper()}")
    print(f"  ROI: {results[best_strategy]['roi']:+.2f}%")
    print(f"  Drawdown tối đa: {results[best_strategy]['max_drawdown']:.2f}%")
    
    # So sánh với mức rủi ro đã chấp nhận
    met_risk_target = any(results[s]['max_drawdown'] >= 30 for s in results)
    exceeded_risk_target = any(results[s]['max_drawdown'] >= 50 for s in results)
    
    print("\nPhân tích rủi ro:")
    if exceeded_risk_target:
        print(f"  ⚠️ Cảnh báo: Drawdown của chiến lược {worst_drawdown} đã vượt quá 50%")
        print(f"     Nên giảm rủi ro hoặc sử dụng chiến lược an toàn hơn")
    elif met_risk_target:
        print(f"  ⚠️ Lưu ý: Drawdown đã đạt mức 30-50% như dự kiến")
        print(f"     Mức rủi ro phù hợp với yêu cầu")
    else:
        print(f"  ✅ Tốt: Drawdown thấp hơn mức chấp nhận (30-50%)")
        print(f"     Có thể tăng rủi ro để đạt hiệu suất cao hơn")
    
    print("\nKhuyến nghị dựa trên kết quả:")
    
    if results[best_strategy]['roi'] > 100:
        print(f"  ✅ Nên sử dụng chiến lược {best_strategy} với cấu hình rủi ro cao")
        
        if 'combined' == best_strategy:
            best_substrat = max(results['combined']['strategy_performance'].keys(), 
                              key=lambda s: results['combined']['strategy_performance'][s]['profit'])
            print(f"  ✅ Trong chiến lược kết hợp, {best_substrat} cho hiệu quả tốt nhất")
    else:
        print(f"  ⚠️ Hiệu suất với rủi ro cao chưa thực sự ấn tượng")
        print(f"  ⚠️ Nên cân nhắc điều chỉnh tham số hoặc sử dụng chiến lược rủi ro thấp hơn")
    
    print("\nĐã lưu biểu đồ kết quả vào thư mục: high_risk_results")

if __name__ == "__main__":
    run_high_risk_test()