#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Reinforcement Learning Agent for Optimizing Trading Decisions
"""

import os
import json
import time
import random
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Union, Optional, Any
from collections import deque
from datetime import datetime

# Deep Learning
import tensorflow as tf
from tensorflow.keras.models import Sequential, Model, load_model
from tensorflow.keras.layers import Dense, Input, Conv1D, LSTM, Flatten, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.losses import Huber
from tensorflow.keras.initializers import HeUniform
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('reinforcement_agent')

class TradingEnvironment:
    """
    Môi trường giao dịch cho RL agent
    """
    
    def __init__(
        self, 
        df: pd.DataFrame, 
        initial_balance: float = 10000.0,
        transaction_fee_percent: float = 0.04,
        reward_scaling: float = 0.01,
        window_size: int = 60,
        max_position_size: float = 1.0,
        use_risk_adjustment: bool = True,
        risk_weight: float = 0.4
    ):
        """
        Khởi tạo môi trường giao dịch
        
        Args:
            df: DataFrame chứa dữ liệu giao dịch (OHLCV)
            initial_balance: Số dư ban đầu
            transaction_fee_percent: Phần trăm phí giao dịch
            reward_scaling: Hệ số scale reward
            window_size: Kích thước cửa sổ observation
            max_position_size: Kích thước vị thế tối đa
            use_risk_adjustment: Điều chỉnh reward dựa trên rủi ro
            risk_weight: Trọng số của rủi ro trong reward
        """
        self.df = df.copy()
        self.initial_balance = initial_balance
        self.transaction_fee_percent = transaction_fee_percent / 100  # Chuyển thành tỷ lệ
        self.reward_scaling = reward_scaling
        self.window_size = window_size
        self.max_position_size = max_position_size
        self.use_risk_adjustment = use_risk_adjustment
        self.risk_weight = risk_weight
        
        # Kiểm tra cột cần thiết
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in self.df.columns]
        
        if missing_columns:
            raise ValueError(f"Thiếu các cột: {missing_columns} trong dữ liệu")
        
        # Thêm các đặc trưng kỹ thuật nếu chưa có
        self._add_technical_features()
        
        # Các thuộc tính để theo dõi trạng thái
        self.current_step = 0
        self.balance = initial_balance
        self.portfolio_value = initial_balance
        self.position = 0.0  # [-1.0, 1.0], âm là short, dương là long
        self.entry_price = 0.0
        self.current_price = 0.0
        self.trade_history = []
        self.profits = []
        self.drawdowns = []
        self.unrealized_pnl = 0.0
        self.episode_reward = 0.0
        
        # Các đặc trưng được chuẩn hóa
        self.normalized_features = None
        self._normalize_features()
        
        logger.info(f"Khởi tạo môi trường giao dịch với {len(self.df)} điểm dữ liệu")
    
    def _add_technical_features(self) -> None:
        """Thêm các đặc trưng kỹ thuật"""
        # Chỉ thêm nếu chưa có
        if 'returns' not in self.df.columns:
            # Log returns
            self.df['returns'] = np.log(self.df['close'] / self.df['close'].shift(1)).fillna(0)
        
        if 'volatility' not in self.df.columns:
            # Biến động (volatility)
            self.df['volatility'] = self.df['returns'].rolling(20).std().fillna(0)
        
        if 'rsi_14' not in self.df.columns:
            # RSI
            delta = self.df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(14).mean()
            avg_loss = loss.rolling(14).mean()
            
            rs = avg_gain / avg_loss.replace(0, np.nan)
            self.df['rsi_14'] = (100 - (100 / (1 + rs))).fillna(50)
        
        if 'sma_20' not in self.df.columns:
            # Simple Moving Average
            self.df['sma_20'] = self.df['close'].rolling(20).mean().fillna(method='bfill')
        
        if 'ema_12' not in self.df.columns:
            # Exponential Moving Average
            self.df['ema_12'] = self.df['close'].ewm(span=12, adjust=False).mean().fillna(method='bfill')
        
        if 'ema_26' not in self.df.columns:
            self.df['ema_26'] = self.df['close'].ewm(span=26, adjust=False).mean().fillna(method='bfill')
        
        if 'macd' not in self.df.columns:
            # MACD
            self.df['macd'] = self.df['ema_12'] - self.df['ema_26']
            self.df['macd_signal'] = self.df['macd'].ewm(span=9, adjust=False).mean().fillna(method='bfill')
            self.df['macd_hist'] = self.df['macd'] - self.df['macd_signal']
        
        if 'bb_upper' not in self.df.columns:
            # Bollinger Bands
            self.df['bb_middle'] = self.df['close'].rolling(20).mean()
            self.df['bb_std'] = self.df['close'].rolling(20).std()
            self.df['bb_upper'] = self.df['bb_middle'] + 2 * self.df['bb_std']
            self.df['bb_lower'] = self.df['bb_middle'] - 2 * self.df['bb_std']
            self.df['bb_width'] = (self.df['bb_upper'] - self.df['bb_lower']) / self.df['bb_middle']
            
            # Điền giá trị NaN
            for col in ['bb_middle', 'bb_std', 'bb_upper', 'bb_lower', 'bb_width']:
                self.df[col] = self.df[col].fillna(method='bfill')
    
    def _normalize_features(self) -> None:
        """Chuẩn hóa các đặc trưng để sử dụng cho state"""
        # Các đặc trưng để normalize
        price_cols = ['open', 'high', 'low', 'close']
        tech_cols = [
            'rsi_14', 'macd', 'macd_signal', 'macd_hist', 
            'volatility', 'bb_width', 'returns',
            'sma_20', 'ema_12', 'ema_26'
        ]
        
        # Kiểm tra xem tất cả các cột có sẵn không
        available_cols = [col for col in price_cols + tech_cols if col in self.df.columns]
        
        if not available_cols:
            raise ValueError("Không có đặc trưng nào để chuẩn hóa")
        
        # Chỉ chuẩn hóa các đặc trưng cần thiết
        normalized_df = pd.DataFrame(index=self.df.index)
        
        # Chuẩn hóa giá
        for col in [c for c in price_cols if c in self.df.columns]:
            # Min-max scaling trên cửa sổ trượt
            roll_max = self.df[col].rolling(self.window_size).max()
            roll_min = self.df[col].rolling(self.window_size).min()
            normalized_df[f'{col}_norm'] = (self.df[col] - roll_min) / (roll_max - roll_min + 1e-8)
        
        # Chuẩn hóa các đặc trưng kỹ thuật theo cách phù hợp
        if 'rsi_14' in self.df.columns:
            # RSI đã ở trong khoảng [0, 100]
            normalized_df['rsi_14_norm'] = self.df['rsi_14'] / 100.0
        
        if 'macd' in self.df.columns:
            # MACD, chuẩn hóa dựa trên biên độ lịch sử
            macd_max = self.df['macd'].rolling(self.window_size).max()
            macd_min = self.df['macd'].rolling(self.window_size).min()
            normalized_df['macd_norm'] = (self.df['macd'] - macd_min) / (macd_max - macd_min + 1e-8)
            
            # Tương tự cho macd_signal và macd_hist nếu có
            if 'macd_signal' in self.df.columns:
                normalized_df['macd_signal_norm'] = (self.df['macd_signal'] - macd_min) / (macd_max - macd_min + 1e-8)
            if 'macd_hist' in self.df.columns:
                hist_max = self.df['macd_hist'].rolling(self.window_size).max()
                hist_min = self.df['macd_hist'].rolling(self.window_size).min()
                normalized_df['macd_hist_norm'] = (self.df['macd_hist'] - hist_min) / (hist_max - hist_min + 1e-8)
        
        if 'volatility' in self.df.columns:
            # Biến động, chuẩn hóa dựa trên max lịch sử
            vol_max = self.df['volatility'].rolling(self.window_size).max()
            normalized_df['volatility_norm'] = self.df['volatility'] / (vol_max + 1e-8)
        
        if 'bb_width' in self.df.columns:
            # Bollinger Bands width
            bbw_max = self.df['bb_width'].rolling(self.window_size).max()
            normalized_df['bb_width_norm'] = self.df['bb_width'] / (bbw_max + 1e-8)
        
        if 'returns' in self.df.columns:
            # Returns, chuẩn hóa dựa trên biên độ lịch sử
            ret_max = self.df['returns'].rolling(self.window_size).max()
            ret_min = self.df['returns'].rolling(self.window_size).min()
            normalized_df['returns_norm'] = (self.df['returns'] - ret_min) / (ret_max - ret_min + 1e-8)
        
        # Các EMA/SMA
        for col in ['sma_20', 'ema_12', 'ema_26']:
            if col in self.df.columns:
                # Chuẩn hóa tương đối so với giá hiện tại
                normalized_df[f'{col}_norm'] = self.df[col] / self.df['close']
        
        # Điền giá trị NaN
        normalized_df = normalized_df.fillna(0.5)  # Giá trị trung tính
        
        self.normalized_features = normalized_df
        
        logger.info(f"Đã chuẩn hóa {len(normalized_df.columns)} đặc trưng")
    
    def reset(self) -> np.ndarray:
        """
        Thiết lập lại môi trường cho một episode mới
        
        Returns:
            Trạng thái ban đầu
        """
        self.current_step = self.window_size
        self.balance = self.initial_balance
        self.position = 0.0
        self.entry_price = 0.0
        self.portfolio_value = self.initial_balance
        self.trade_history = []
        self.profits = []
        self.drawdowns = []
        self.unrealized_pnl = 0.0
        self.episode_reward = 0.0
        
        # Trạng thái ban đầu
        return self._get_observation()
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Thực hiện một bước trong môi trường
        
        Args:
            action: Hành động thực hiện
                0 = không làm gì
                1 = mua (long)
                2 = bán (short)
                3 = đóng vị thế
        
        Returns:
            observation: trạng thái mới
            reward: phần thưởng nhận được
            done: episode đã kết thúc chưa
            info: thông tin bổ sung
        """
        if self.current_step >= len(self.df) - 1:
            # Hết dữ liệu, kết thúc episode
            return self._get_observation(), 0, True, {
                'portfolio_value': self.portfolio_value,
                'balance': self.balance,
                'position': self.position,
                'unrealized_pnl': self.unrealized_pnl,
                'total_trades': len(self.trade_history),
                'total_profit': sum(self.profits),
                'max_drawdown': min(self.drawdowns) if self.drawdowns else 0
            }
        
        # Giá hiện tại
        self.current_price = self.df['close'].iloc[self.current_step]
        
        # Thực hiện hành động
        reward = self._take_action(action)
        
        # Cập nhật reward tổng
        self.episode_reward += reward
        
        # Chuyển sang bước tiếp theo
        self.current_step += 1
        
        # Kiểm tra xem episode đã kết thúc chưa
        done = self.current_step >= len(self.df) - 1
        
        # Nếu kết thúc, đóng hết vị thế
        if done and self.position != 0:
            self._close_position()
        
        return self._get_observation(), reward, done, {
            'portfolio_value': self.portfolio_value,
            'balance': self.balance,
            'position': self.position,
            'unrealized_pnl': self.unrealized_pnl,
            'current_price': self.current_price
        }
    
    def _get_observation(self) -> np.ndarray:
        """
        Lấy observation hiện tại
        
        Returns:
            Array chứa các đặc trưng đã chuẩn hóa
        """
        # Lấy cửa sổ đặc trưng đã chuẩn hóa
        features = self.normalized_features.iloc[self.current_step - self.window_size:self.current_step]
        
        # Ghép các đặc trưng lại thành một mảng 2D
        features_array = features.values
        
        # Thêm thông tin vị thế hiện tại
        position_info = np.array([
            self.position,  # -1 to 1
            self.unrealized_pnl / self.initial_balance,  # scale by initial balance
            self.entry_price / self.current_price - 1 if self.entry_price > 0 else 0  # relative entry price
        ])
        
        # Ghép toàn bộ thông tin thành state
        state = {
            'market_features': features_array,
            'account_state': position_info
        }
        
        return state
    
    def _take_action(self, action: int) -> float:
        """
        Thực hiện hành động và tính reward
        
        Args:
            action: Hành động (0: không làm gì, 1: mua, 2: bán, 3: đóng vị thế)
        
        Returns:
            reward: phần thưởng nhận được
        """
        # Lưu trữ giá trị danh mục trước hành động
        prev_portfolio_value = self.portfolio_value
        
        # Tính unrealized PnL trước khi thực hiện hành động
        if self.position != 0:
            price_diff = self.current_price - self.entry_price
            self.unrealized_pnl = self.position * price_diff * self.initial_balance / self.entry_price
        else:
            self.unrealized_pnl = 0
        
        # Cập nhật giá trị danh mục
        self.portfolio_value = self.balance + self.unrealized_pnl
        
        # Thực hiện hành động
        if action == 0:  # Không làm gì
            pass
        elif action == 1:  # Mua (long)
            if self.position <= 0:  # Nếu đang short hoặc không có vị thế
                if self.position < 0:  # Đang short, đóng vị thế trước
                    self._close_position()
                # Mở vị thế long
                self._open_position(1.0)
        elif action == 2:  # Bán (short)
            if self.position >= 0:  # Nếu đang long hoặc không có vị thế
                if self.position > 0:  # Đang long, đóng vị thế trước
                    self._close_position()
                # Mở vị thế short
                self._open_position(-1.0)
        elif action == 3:  # Đóng vị thế
            if self.position != 0:
                self._close_position()
        
        # Tính lại giá trị danh mục sau hành động
        if self.position != 0:
            price_diff = self.current_price - self.entry_price
            self.unrealized_pnl = self.position * price_diff * self.initial_balance / self.entry_price
        else:
            self.unrealized_pnl = 0
        
        self.portfolio_value = self.balance + self.unrealized_pnl
        
        # Tính drawdown
        drawdown = (self.portfolio_value / self.initial_balance - 1) * 100
        if drawdown < 0:
            self.drawdowns.append(drawdown)
        
        # Tính reward
        reward = self._calculate_reward(prev_portfolio_value)
        
        return reward
    
    def _open_position(self, direction: float) -> None:
        """
        Mở vị thế
        
        Args:
            direction: Hướng vị thế (1.0 = long, -1.0 = short)
        """
        if self.position != 0:
            logger.warning("Đã có vị thế, hãy đóng vị thế trước khi mở vị thế mới")
            return
        
        # Giá mở vị thế
        self.entry_price = self.current_price
        
        # Kích thước vị thế
        position_size = self._calculate_position_size()
        
        # Hướng vị thế
        self.position = direction * position_size
        
        # Phí giao dịch
        fee = self.initial_balance * position_size * self.transaction_fee_percent
        self.balance -= fee
        
        # Lưu lịch sử giao dịch
        self.trade_history.append({
            'timestamp': self.df.index[self.current_step],
            'action': 'buy' if direction > 0 else 'sell',
            'price': self.entry_price,
            'position_size': position_size,
            'fee': fee
        })
        
        logger.debug(f"Mở vị thế {direction} tại giá {self.entry_price} với kích thước {position_size}")
    
    def _close_position(self) -> None:
        """Đóng vị thế hiện tại"""
        if self.position == 0:
            return
        
        # Giá đóng vị thế
        exit_price = self.current_price
        
        # Tính lợi nhuận/lỗ
        price_diff = exit_price - self.entry_price
        pnl = self.position * price_diff * self.initial_balance / self.entry_price
        
        # Phí giao dịch
        fee = abs(self.position) * self.initial_balance * self.transaction_fee_percent
        
        # Cập nhật số dư
        self.balance += pnl - fee
        
        # Lưu lịch sử giao dịch
        self.trade_history.append({
            'timestamp': self.df.index[self.current_step],
            'action': 'sell' if self.position > 0 else 'buy',
            'price': exit_price,
            'position_size': abs(self.position),
            'fee': fee,
            'pnl': pnl
        })
        
        # Lưu lợi nhuận
        self.profits.append(pnl)
        
        # Reset vị thế
        self.position = 0.0
        self.entry_price = 0.0
        self.unrealized_pnl = 0.0
        
        logger.debug(f"Đóng vị thế tại giá {exit_price} với PnL {pnl:.2f}")
    
    def _calculate_position_size(self) -> float:
        """
        Tính toán kích thước vị thế dựa trên biến động
        
        Returns:
            Kích thước vị thế (0-1)
        """
        if not self.use_risk_adjustment:
            return self.max_position_size
        
        # Lấy biến động hiện tại
        if 'volatility' in self.df.columns:
            volatility = self.df['volatility'].iloc[self.current_step]
            
            # Điều chỉnh kích thước vị thế ngược với biến động
            vol_percentile = self.df['volatility'].quantile(0.95)
            vol_ratio = min(1.0, volatility / vol_percentile if vol_percentile > 0 else 1.0)
            
            # Công thức: Higher volatility = smaller position
            position_size = self.max_position_size * (1 - vol_ratio * 0.5)  # Minimum 50% of max size
            
            return max(0.1, position_size)  # Always at least 10% of max size
        
        return self.max_position_size
    
    def _calculate_reward(self, prev_portfolio_value: float) -> float:
        """
        Tính toán phần thưởng cho hành động
        
        Args:
            prev_portfolio_value: Giá trị danh mục trước hành động
        
        Returns:
            reward: phần thưởng
        """
        # Tính thay đổi về giá trị danh mục
        portfolio_change = (self.portfolio_value - prev_portfolio_value) / self.initial_balance
        
        # Reward cơ bản dựa trên thay đổi giá trị
        reward = portfolio_change / self.reward_scaling
        
        # Reward rủi ro-điều chỉnh nếu được kích hoạt
        if self.use_risk_adjustment:
            # Tính biến động
            if 'volatility' in self.df.columns:
                volatility = self.df['volatility'].iloc[self.current_step]
                
                # Phần thưởng/phạt cho rủi ro quá mức
                # Reward tích cực nếu: profit tốt với rủi ro thấp
                # Phạt nếu: rủi ro cao với profit ít hoặc lỗ
                risk_reward = (
                    -1 * self.risk_weight * volatility if portfolio_change < 0 else
                    self.risk_weight * (portfolio_change / (volatility + 1e-8))
                )
                
                reward += risk_reward
            
            # Phạt cho drawdown lớn
            if self.drawdowns and min(self.drawdowns) < -10:  # Drawdown > 10%
                max_dd = min(self.drawdowns)
                dd_penalty = 0.1 * max_dd  # Phạt 10% của drawdown
                reward += dd_penalty
        
        return reward
    
    def render(self, mode: str = 'human') -> None:
        """
        Hiển thị trạng thái hiện tại của môi trường
        
        Args:
            mode: Chế độ hiển thị
        """
        if mode == 'human':
            print(f"\nStep: {self.current_step}")
            print(f"Price: {self.current_price:.2f}")
            print(f"Balance: {self.balance:.2f}")
            print(f"Position: {self.position:.2f}")
            print(f"Entry Price: {self.entry_price:.2f}")
            print(f"Unrealized PnL: {self.unrealized_pnl:.2f}")
            print(f"Portfolio Value: {self.portfolio_value:.2f}")
            print(f"Reward so far: {self.episode_reward:.2f}")
            print(f"Trades: {len(self.trade_history)}")
            print(f"Profit/Loss: {sum(self.profits):.2f}")
            print(f"Max Drawdown: {min(self.drawdowns) if self.drawdowns else 0:.2f}%")
    
    def get_portfolio_history(self) -> pd.DataFrame:
        """
        Lấy lịch sử danh mục
        
        Returns:
            DataFrame chứa lịch sử danh mục
        """
        if not self.trade_history:
            return pd.DataFrame()
        
        return pd.DataFrame(self.trade_history)

class ReplayBuffer:
    """
    Bộ nhớ trải nghiệm để lưu trữ và lấy mẫu từ trải nghiệm cho DQN
    """
    
    def __init__(self, capacity: int = 10000):
        """
        Khởi tạo Replay Buffer
        
        Args:
            capacity: Dung lượng tối đa của buffer
        """
        self.buffer = deque(maxlen=capacity)
    
    def add(
        self, 
        state: Dict, 
        action: int, 
        reward: float, 
        next_state: Dict, 
        done: bool
    ) -> None:
        """
        Thêm một trải nghiệm vào buffer
        
        Args:
            state: Trạng thái
            action: Hành động
            reward: Phần thưởng
            next_state: Trạng thái tiếp theo
            done: Episode đã kết thúc chưa
        """
        # Làm phẳng state và next_state để lưu trữ
        self.buffer.append((state, action, reward, next_state, done))
    
    def sample(self, batch_size: int) -> Tuple:
        """
        Lấy mẫu ngẫu nhiên các trải nghiệm
        
        Args:
            batch_size: Kích thước batch
        
        Returns:
            Tuple (states, actions, rewards, next_states, dones)
        """
        batch = random.sample(self.buffer, min(batch_size, len(self.buffer)))
        
        # Tách batch
        states, actions, rewards, next_states, dones = zip(*batch)
        
        return states, actions, rewards, next_states, dones
    
    def __len__(self) -> int:
        """Số lượng trải nghiệm trong buffer"""
        return len(self.buffer)

class DQNAgent:
    """
    Agent DQN cho giao dịch tiền điện tử
    """
    
    def __init__(
        self, 
        state_size: Tuple[int, int],
        action_size: int,
        learning_rate: float = 0.001,
        gamma: float = 0.95,
        epsilon: float = 1.0,
        epsilon_min: float = 0.01,
        epsilon_decay: float = 0.995,
        batch_size: int = 32,
        tau: float = 0.01,
        update_frequency: int = 5,
        double_dqn: bool = True,
        model_dir: str = 'ml_models'
    ):
        """
        Khởi tạo DQN Agent
        
        Args:
            state_size: Kích thước trạng thái (window_size, n_features)
            action_size: Số lượng hành động có thể
            learning_rate: Tốc độ học
            gamma: Hệ số giảm reward
            epsilon: Epsilon ban đầu cho epsilon-greedy
            epsilon_min: Epsilon tối thiểu
            epsilon_decay: Tốc độ giảm epsilon
            batch_size: Kích thước batch cho training
            tau: Hệ số cập nhật từ từ cho target network
            update_frequency: Tần suất cập nhật target network
            double_dqn: Sử dụng Double DQN nếu True
            model_dir: Thư mục để lưu mô hình
        """
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.tau = tau
        self.update_frequency = update_frequency
        self.double_dqn = double_dqn
        self.model_dir = model_dir
        
        # Tạo thư mục mô hình nếu chưa tồn tại
        os.makedirs(model_dir, exist_ok=True)
        
        # Replay buffer
        self.memory = ReplayBuffer(capacity=50000)
        
        # Training metrics
        self.train_loss_history = []
        self.episode_reward_history = []
        self.q_value_history = []
        self.epsilon_history = []
        
        # State và action counters
        self.training_steps = 0
        self.update_counter = 0
        
        # Xây dựng model
        self.model = self._build_model()
        self.target_model = self._build_model()
        
        # Khởi tạo target model giống với main model
        self._update_target_model(tau=1.0)
        
        logger.info(f"Đã khởi tạo DQN Agent với {action_size} hành động và epsilon={epsilon}")
    
    def _build_model(self) -> Model:
        """
        Xây dựng mô hình DQN
        
        Returns:
            Tensorflow/Keras model
        """
        # Input layers cho đặc trưng thị trường
        market_input = Input(shape=self.state_size, name='market_features')
        
        # Input layer cho trạng thái tài khoản
        account_input = Input(shape=(3,), name='account_state')
        
        # Xử lý đặc trưng thị trường
        # 1. Convolutional layers để trích xuất mẫu ngắn hạn
        conv1 = Conv1D(64, 3, activation='relu')(market_input)
        conv2 = Conv1D(64, 5, activation='relu')(market_input)
        
        # 2. LSTM để bắt mẫu dài hạn
        lstm = LSTM(64, return_sequences=False)(market_input)
        
        # Kết hợp đặc trưng
        conv1_flat = Flatten()(conv1)
        conv2_flat = Flatten()(conv2)
        
        # Ghép các đặc trưng
        merged = tf.keras.layers.concatenate([conv1_flat, conv2_flat, lstm, account_input])
        
        # Fully connected layers
        dense1 = Dense(128, activation='relu')(merged)
        dense1 = BatchNormalization()(dense1)
        dense1 = Dropout(0.2)(dense1)
        
        dense2 = Dense(64, activation='relu')(dense1)
        dense2 = BatchNormalization()(dense2)
        dense2 = Dropout(0.1)(dense2)
        
        # Output layer
        output = Dense(self.action_size, activation='linear')(dense2)
        
        # Tạo model
        model = Model(inputs=[market_input, account_input], outputs=output)
        
        # Compile model
        model.compile(
            loss=Huber(), 
            optimizer=Adam(learning_rate=self.learning_rate)
        )
        
        return model
    
    def _update_target_model(self, tau: float = None) -> None:
        """
        Cập nhật target model từ model chính
        
        Args:
            tau: Hệ số cho soft update, None sẽ sử dụng giá trị mặc định
        """
        if tau is None:
            tau = self.tau
        
        # Soft update
        for target_weights, main_weights in zip(
            self.target_model.get_weights(), self.model.get_weights()
        ):
            target_weights = tau * main_weights + (1 - tau) * target_weights
        
        # Hard update nếu tau=1
        if tau == 1.0:
            self.target_model.set_weights(self.model.get_weights())
    
    def remember(
        self, 
        state: Dict, 
        action: int, 
        reward: float, 
        next_state: Dict, 
        done: bool
    ) -> None:
        """
        Lưu trữ trải nghiệm vào replay buffer
        
        Args:
            state: Trạng thái
            action: Hành động
            reward: Phần thưởng
            next_state: Trạng thái tiếp theo
            done: Episode đã kết thúc chưa
        """
        self.memory.add(state, action, reward, next_state, done)
    
    def act(self, state: Dict, training: bool = True) -> int:
        """
        Chọn hành động dựa trên trạng thái
        
        Args:
            state: Trạng thái hiện tại
            training: Có đang trong quá trình training hay không
        
        Returns:
            action: Hành động được chọn
        """
        if training and np.random.rand() <= self.epsilon:
            # Chọn ngẫu nhiên trong quá trình training
            return random.randrange(self.action_size)
        
        # Format state cho input model
        market_features = np.expand_dims(state['market_features'], axis=0)
        account_state = np.expand_dims(state['account_state'], axis=0)
        
        # Dự đoán Q-values
        q_values = self.model.predict(
            [market_features, account_state], verbose=0
        )
        
        # Lưu Q-values cho theo dõi
        self.q_value_history.append(np.mean(q_values))
        
        # Chọn hành động tốt nhất dựa trên Q-values
        return np.argmax(q_values[0])
    
    def replay(self, batch_size: int = None) -> float:
        """
        Training model từ replay buffer
        
        Args:
            batch_size: Kích thước batch, None sẽ sử dụng giá trị mặc định
        
        Returns:
            loss: Giá trị loss sau khi train
        """
        if batch_size is None:
            batch_size = self.batch_size
        
        # Kiểm tra xem có đủ dữ liệu trong buffer không
        if len(self.memory) < batch_size:
            return 0.0
        
        # Lấy mẫu batch từ replay buffer
        states, actions, rewards, next_states, dones = self.memory.sample(batch_size)
        
        # Format states và next_states cho batch
        market_features_batch = np.array([s['market_features'] for s in states])
        account_state_batch = np.array([s['account_state'] for s in states])
        
        next_market_features_batch = np.array([ns['market_features'] for ns in next_states])
        next_account_state_batch = np.array([ns['account_state'] for ns in next_states])
        
        # Convert to numpy arrays
        actions = np.array(actions)
        rewards = np.array(rewards)
        dones = np.array(dones, dtype=np.float32)
        
        # Batch predictions
        # Predict Q-values cho trạng thái hiện tại
        current_q_batch = self.model.predict(
            [market_features_batch, account_state_batch], verbose=0
        )
        
        if self.double_dqn:
            # Double DQN: Chọn hành động từ main model
            next_actions = np.argmax(
                self.model.predict(
                    [next_market_features_batch, next_account_state_batch], verbose=0
                ), axis=1
            )
            
            # Lấy Q-values từ target model
            next_q_batch = self.target_model.predict(
                [next_market_features_batch, next_account_state_batch], verbose=0
            )
            
            # Get Q-values for the selected actions
            max_next_q = next_q_batch[np.arange(batch_size), next_actions]
        else:
            # Standard DQN: Trực tiếp lấy max Q-value từ target model
            next_q_batch = self.target_model.predict(
                [next_market_features_batch, next_account_state_batch], verbose=0
            )
            max_next_q = np.max(next_q_batch, axis=1)
        
        # Tính expected Q values
        expected_q = rewards + (1 - dones) * self.gamma * max_next_q
        
        # Cập nhật Q-values cho hành động đã thực hiện
        target_q = current_q_batch.copy()
        for i, action in enumerate(actions):
            target_q[i, action] = expected_q[i]
        
        # Train model
        history = self.model.fit(
            [market_features_batch, account_state_batch], 
            target_q, 
            epochs=1, 
            verbose=0,
            batch_size=batch_size
        )
        
        # Lưu loss
        loss = history.history['loss'][0]
        self.train_loss_history.append(loss)
        
        # Cập nhật counter
        self.training_steps += 1
        self.update_counter += 1
        
        # Kiểm tra xem có cần cập nhật target model không
        if self.update_counter >= self.update_frequency:
            self._update_target_model()
            self.update_counter = 0
        
        # Giảm epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
            self.epsilon_history.append(self.epsilon)
        
        return loss
    
    def save(self, filepath: str = None) -> None:
        """
        Lưu mô hình
        
        Args:
            filepath: Đường dẫn để lưu mô hình, None sẽ sử dụng đường dẫn mặc định
        """
        if filepath is None:
            filepath = os.path.join(self.model_dir, 'dqn_model.h5')
        
        self.model.save(filepath)
        
        # Lưu thông số và lịch sử training
        params = {
            'state_size': self.state_size,
            'action_size': self.action_size,
            'learning_rate': self.learning_rate,
            'gamma': self.gamma,
            'epsilon': self.epsilon,
            'epsilon_min': self.epsilon_min,
            'epsilon_decay': self.epsilon_decay,
            'batch_size': self.batch_size,
            'tau': self.tau,
            'update_frequency': self.update_frequency,
            'double_dqn': self.double_dqn,
            'training_steps': self.training_steps
        }
        
        # Lưu các thông số và lịch sử training
        with open(os.path.join(self.model_dir, 'dqn_params.json'), 'w') as f:
            json.dump(params, f, indent=4)
        
        # Lưu lịch sử training
        history = {
            'loss': self.train_loss_history,
            'rewards': self.episode_reward_history,
            'q_values': self.q_value_history,
            'epsilon': self.epsilon_history
        }
        
        np.save(os.path.join(self.model_dir, 'dqn_history.npy'), history)
        
        logger.info(f"Đã lưu mô hình DQN tại: {filepath}")
    
    def load(self, filepath: str = None) -> None:
        """
        Tải mô hình
        
        Args:
            filepath: Đường dẫn để tải mô hình, None sẽ sử dụng đường dẫn mặc định
        """
        if filepath is None:
            filepath = os.path.join(self.model_dir, 'dqn_model.h5')
        
        self.model = load_model(filepath)
        self.target_model = load_model(filepath)
        
        # Tải thông số
        params_path = os.path.join(self.model_dir, 'dqn_params.json')
        if os.path.exists(params_path):
            with open(params_path, 'r') as f:
                params = json.load(f)
            
            # Cập nhật thông số
            self.learning_rate = params.get('learning_rate', self.learning_rate)
            self.gamma = params.get('gamma', self.gamma)
            self.epsilon = params.get('epsilon', self.epsilon)
            self.epsilon_min = params.get('epsilon_min', self.epsilon_min)
            self.epsilon_decay = params.get('epsilon_decay', self.epsilon_decay)
            self.batch_size = params.get('batch_size', self.batch_size)
            self.tau = params.get('tau', self.tau)
            self.update_frequency = params.get('update_frequency', self.update_frequency)
            self.double_dqn = params.get('double_dqn', self.double_dqn)
            self.training_steps = params.get('training_steps', 0)
        
        # Tải lịch sử training
        history_path = os.path.join(self.model_dir, 'dqn_history.npy')
        if os.path.exists(history_path):
            history = np.load(history_path, allow_pickle=True).item()
            
            self.train_loss_history = history.get('loss', [])
            self.episode_reward_history = history.get('rewards', [])
            self.q_value_history = history.get('q_values', [])
            self.epsilon_history = history.get('epsilon', [])
        
        logger.info(f"Đã tải mô hình DQN từ: {filepath}")
    
    def plot_training_history(self, filepath: str = None) -> None:
        """
        Vẽ biểu đồ lịch sử training
        
        Args:
            filepath: Đường dẫn để lưu biểu đồ, None sẽ sử dụng đường dẫn mặc định
        """
        import matplotlib.pyplot as plt
        
        if not self.train_loss_history:
            logger.warning("Không có lịch sử training để vẽ")
            return
        
        if filepath is None:
            filepath = os.path.join(self.model_dir, 'dqn_training_history.png')
        
        # Tạo hình
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Plot loss
        axes[0, 0].plot(self.train_loss_history)
        axes[0, 0].set_title('Training Loss')
        axes[0, 0].set_xlabel('Training Step')
        axes[0, 0].set_ylabel('Loss')
        
        # Plot rewards
        if self.episode_reward_history:
            axes[0, 1].plot(self.episode_reward_history)
            axes[0, 1].set_title('Episode Reward')
            axes[0, 1].set_xlabel('Episode')
            axes[0, 1].set_ylabel('Total Reward')
        
        # Plot Q-values
        if self.q_value_history:
            axes[1, 0].plot(self.q_value_history)
            axes[1, 0].set_title('Average Q-Value')
            axes[1, 0].set_xlabel('Step')
            axes[1, 0].set_ylabel('Q-Value')
        
        # Plot epsilon
        if self.epsilon_history:
            axes[1, 1].plot(self.epsilon_history)
            axes[1, 1].set_title('Epsilon')
            axes[1, 1].set_xlabel('Training Step')
            axes[1, 1].set_ylabel('Epsilon')
        
        plt.tight_layout()
        plt.savefig(filepath)
        plt.close()
        
        logger.info(f"Đã lưu biểu đồ lịch sử training tại: {filepath}")

class ReinforcementTrader:
    """
    Hệ thống giao dịch sử dụng Reinforcement Learning
    """
    
    def __init__(
        self, 
        model_dir: str = 'ml_models',
        use_double_dqn: bool = True,
        window_size: int = 60,
        batch_size: int = 32,
        epsilon: float = 0.5,
        mode: str = 'train'
    ):
        """
        Khởi tạo ReinforcementTrader
        
        Args:
            model_dir: Thư mục chứa mô hình
            use_double_dqn: Sử dụng Double DQN nếu True
            window_size: Kích thước cửa sổ dữ liệu
            batch_size: Kích thước batch cho training
            epsilon: Epsilon ban đầu cho epsilon-greedy
            mode: Chế độ hoạt động ('train' hoặc 'test')
        """
        self.model_dir = model_dir
        self.use_double_dqn = use_double_dqn
        self.window_size = window_size
        self.batch_size = batch_size
        self.epsilon = epsilon
        self.mode = mode
        
        # Tạo thư mục mô hình nếu chưa tồn tại
        os.makedirs(model_dir, exist_ok=True)
        
        # Khởi tạo agent và môi trường
        self.agent = None
        self.env = None
        
        # Trạng thái training
        self.episode = 0
        self.best_reward = -np.inf
        
        logger.info(f"Đã khởi tạo ReinforcementTrader trong chế độ {mode}")
    
    def prepare_environment(
        self, 
        df: pd.DataFrame, 
        initial_balance: float = 10000.0,
        transaction_fee_percent: float = 0.04,
        reward_scaling: float = 0.01,
        max_position_size: float = 1.0,
        use_risk_adjustment: bool = True
    ) -> None:
        """
        Chuẩn bị môi trường giao dịch
        
        Args:
            df: DataFrame chứa dữ liệu giao dịch
            initial_balance: Số dư ban đầu
            transaction_fee_percent: Phần trăm phí giao dịch
            reward_scaling: Hệ số scale reward
            max_position_size: Kích thước vị thế tối đa
            use_risk_adjustment: Điều chỉnh reward dựa trên rủi ro
        """
        # Tạo môi trường
        self.env = TradingEnvironment(
            df=df,
            initial_balance=initial_balance,
            transaction_fee_percent=transaction_fee_percent,
            reward_scaling=reward_scaling,
            window_size=self.window_size,
            max_position_size=max_position_size,
            use_risk_adjustment=use_risk_adjustment
        )
        
        # Lấy kích thước state và action
        state = self.env.reset()
        market_features_shape = state['market_features'].shape
        action_size = 4  # Không làm gì, mua (long), bán (short), đóng vị thế
        
        # Khởi tạo agent nếu chưa có
        if self.agent is None:
            self.agent = DQNAgent(
                state_size=market_features_shape,
                action_size=action_size,
                learning_rate=0.0005,
                gamma=0.95,
                epsilon=self.epsilon,
                epsilon_min=0.01,
                epsilon_decay=0.995,
                batch_size=self.batch_size,
                tau=0.01,
                update_frequency=5,
                double_dqn=self.use_double_dqn,
                model_dir=self.model_dir
            )
            
            # Tải mô hình nếu có
            model_path = os.path.join(self.model_dir, 'dqn_model.h5')
            if os.path.exists(model_path):
                logger.info(f"Tải mô hình từ {model_path}")
                self.agent.load(model_path)
        
        logger.info(f"Đã chuẩn bị môi trường giao dịch với dữ liệu {len(df)} điểm")
    
    def train(
        self, 
        episodes: int = 100,
        batch_size: int = None,
        print_interval: int = 10,
        save_best: bool = True,
        plot_results: bool = True
    ) -> Dict:
        """
        Training RL agent
        
        Args:
            episodes: Số lượng episodes
            batch_size: Kích thước batch, None sẽ sử dụng giá trị mặc định
            print_interval: Khoảng in thông tin
            save_best: Lưu mô hình tốt nhất nếu True
            plot_results: Vẽ biểu đồ kết quả nếu True
        
        Returns:
            Dict chứa kết quả training
        """
        if self.env is None or self.agent is None:
            raise ValueError("Môi trường hoặc agent chưa được khởi tạo. Gọi prepare_environment trước.")
        
        if batch_size is None:
            batch_size = self.batch_size
        
        # Kết quả
        results = {
            'rewards': [],
            'portfolio_values': [],
            'balances': [],
            'trades': [],
            'win_rates': []
        }
        
        # Tổng thời gian
        start_time = time.time()
        
        # Start training
        for e in range(episodes):
            self.episode += 1
            
            # Reset môi trường
            state = self.env.reset()
            done = False
            episode_reward = 0
            
            while not done:
                # Chọn hành động
                action = self.agent.act(state, training=True)
                
                # Thực hiện hành động
                next_state, reward, done, info = self.env.step(action)
                
                # Lưu trữ trải nghiệm
                self.agent.remember(state, action, reward, next_state, done)
                
                # Cập nhật state và reward
                state = next_state
                episode_reward += reward
                
                # Training agent
                if len(self.agent.memory) > batch_size:
                    loss = self.agent.replay(batch_size)
            
            # Lưu kết quả episode
            rewards = self.env.profits
            n_trades = len(self.env.trade_history)
            win_rate = (np.array(rewards) > 0).sum() / max(1, len(rewards)) * 100
            
            results['rewards'].append(episode_reward)
            results['portfolio_values'].append(self.env.portfolio_value)
            results['balances'].append(self.env.balance)
            results['trades'].append(n_trades)
            results['win_rates'].append(win_rate)
            
            # Lưu mô hình tốt nhất
            if save_best and episode_reward > self.best_reward:
                self.best_reward = episode_reward
                self.agent.save(os.path.join(self.model_dir, 'dqn_model_best.h5'))
                
                # Lưu trạng thái training
                self._save_training_state({
                    'episode': self.episode,
                    'best_reward': self.best_reward
                })
            
            # In thông tin
            if (e + 1) % print_interval == 0:
                avg_reward = np.mean(results['rewards'][-print_interval:])
                avg_portfolio = np.mean(results['portfolio_values'][-print_interval:])
                avg_trades = np.mean(results['trades'][-print_interval:])
                avg_win_rate = np.mean(results['win_rates'][-print_interval:])
                
                logger.info(f"Episode: {self.episode}/{episodes+self.episode-1}, "
                          f"Reward: {episode_reward:.2f}, "
                          f"Avg Reward: {avg_reward:.2f}, "
                          f"Portfolio: {self.env.portfolio_value:.2f}, "
                          f"Trades: {n_trades}, "
                          f"Win Rate: {win_rate:.2f}%, "
                          f"Epsilon: {self.agent.epsilon:.4f}")
        
        # Lưu mô hình cuối cùng
        self.agent.save(os.path.join(self.model_dir, 'dqn_model.h5'))
        
        # Vẽ biểu đồ kết quả
        if plot_results:
            self.agent.plot_training_history()
            self._plot_training_results(results)
        
        # Tính toán metrics
        mean_reward = np.mean(results['rewards'])
        mean_portfolio = np.mean(results['portfolio_values'])
        mean_trades = np.mean(results['trades'])
        mean_win_rate = np.mean(results['win_rates'])
        
        logger.info(f"Training completed in {time.time() - start_time:.2f}s")
        logger.info(f"Mean Reward: {mean_reward:.2f}")
        logger.info(f"Mean Portfolio Value: {mean_portfolio:.2f}")
        logger.info(f"Mean Trades: {mean_trades:.2f}")
        logger.info(f"Mean Win Rate: {mean_win_rate:.2f}%")
        
        return results
    
    def test(
        self, 
        df: pd.DataFrame = None, 
        plot_results: bool = True,
        verbose: bool = True
    ) -> Dict:
        """
        Kiểm thử RL agent
        
        Args:
            df: DataFrame chứa dữ liệu kiểm thử, None sẽ sử dụng dữ liệu đã chuẩn bị
            plot_results: Vẽ biểu đồ kết quả nếu True
            verbose: In thông tin chi tiết nếu True
        
        Returns:
            Dict chứa kết quả kiểm thử
        """
        if df is not None:
            # Chuẩn bị môi trường mới
            self.prepare_environment(df)
        
        if self.env is None or self.agent is None:
            raise ValueError("Môi trường hoặc agent chưa được khởi tạo. Gọi prepare_environment trước.")
        
        # Reset môi trường
        state = self.env.reset()
        done = False
        test_reward = 0
        
        # Thực hiện kiểm thử
        while not done:
            # Chọn hành động
            action = self.agent.act(state, training=False)
            
            # Thực hiện hành động
            next_state, reward, done, info = self.env.step(action)
            
            # Cập nhật state và reward
            state = next_state
            test_reward += reward
            
            # In thông tin
            if verbose:
                self.env.render()
        
        # Kết quả
        profits = self.env.profits
        n_trades = len(self.env.trade_history)
        win_rate = (np.array(profits) > 0).sum() / max(1, len(profits)) * 100
        
        results = {
            'reward': test_reward,
            'portfolio_value': self.env.portfolio_value,
            'balance': self.env.balance,
            'trades': n_trades,
            'win_rate': win_rate,
            'profits': profits,
            'drawdowns': self.env.drawdowns,
            'trade_history': self.env.trade_history
        }
        
        # In kết quả
        logger.info(f"Test Results:")
        logger.info(f"Reward: {test_reward:.2f}")
        logger.info(f"Portfolio Value: {self.env.portfolio_value:.2f}")
        logger.info(f"Final Balance: {self.env.balance:.2f}")
        logger.info(f"Total Trades: {n_trades}")
        logger.info(f"Win Rate: {win_rate:.2f}%")
        logger.info(f"Total Profit: {sum(profits):.2f}")
        logger.info(f"Max Drawdown: {min(self.env.drawdowns) if self.env.drawdowns else 0:.2f}%")
        
        # Vẽ biểu đồ kết quả
        if plot_results:
            self._plot_test_results(results)
        
        return results
    
    def _save_training_state(self, state: Dict) -> None:
        """
        Lưu trạng thái training
        
        Args:
            state: Trạng thái cần lưu
        """
        state_path = os.path.join(self.model_dir, 'training_state.json')
        with open(state_path, 'w') as f:
            json.dump(state, f, indent=4)
    
    def _load_training_state(self) -> Dict:
        """
        Tải trạng thái training
        
        Returns:
            Dict chứa trạng thái training
        """
        state_path = os.path.join(self.model_dir, 'training_state.json')
        if os.path.exists(state_path):
            with open(state_path, 'r') as f:
                state = json.load(f)
            
            # Cập nhật trạng thái
            self.episode = state.get('episode', 0)
            self.best_reward = state.get('best_reward', -np.inf)
            
            return state
        
        return {}
    
    def _plot_training_results(self, results: Dict) -> None:
        """
        Vẽ biểu đồ kết quả training
        
        Args:
            results: Dict chứa kết quả training
        """
        import matplotlib.pyplot as plt
        
        # Tạo hình
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Plot rewards
        axes[0, 0].plot(results['rewards'])
        axes[0, 0].set_title('Episode Rewards')
        axes[0, 0].set_xlabel('Episode')
        axes[0, 0].set_ylabel('Total Reward')
        
        # Plot portfolio values
        axes[0, 1].plot(results['portfolio_values'])
        axes[0, 1].set_title('Portfolio Values')
        axes[0, 1].set_xlabel('Episode')
        axes[0, 1].set_ylabel('Portfolio Value')
        
        # Plot trades
        axes[1, 0].plot(results['trades'])
        axes[1, 0].set_title('Number of Trades')
        axes[1, 0].set_xlabel('Episode')
        axes[1, 0].set_ylabel('Trades')
        
        # Plot win rates
        axes[1, 1].plot(results['win_rates'])
        axes[1, 1].set_title('Win Rates')
        axes[1, 1].set_xlabel('Episode')
        axes[1, 1].set_ylabel('Win Rate (%)')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.model_dir, 'training_results.png'))
        plt.close()
        
        logger.info(f"Đã lưu biểu đồ kết quả training")
    
    def _plot_test_results(self, results: Dict) -> None:
        """
        Vẽ biểu đồ kết quả kiểm thử
        
        Args:
            results: Dict chứa kết quả kiểm thử
        """
        import matplotlib.pyplot as plt
        
        # Tạo hình
        fig, axes = plt.subplots(2, 1, figsize=(15, 10))
        
        # Plot trade history
        if results['trade_history']:
            # Extract trade data
            trades_df = pd.DataFrame(results['trade_history'])
            
            # Ensure 'timestamp' is in the correct format
            if 'timestamp' in trades_df.columns:
                trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
            
            # Plot prices and trades
            if 'price' in trades_df.columns and 'timestamp' in trades_df.columns:
                axes[0].plot(trades_df['timestamp'], trades_df['price'], label='Price')
                
                # Plot buy points
                buy_trades = trades_df[trades_df['action'] == 'buy']
                if not buy_trades.empty:
                    axes[0].scatter(buy_trades['timestamp'], buy_trades['price'], 
                                  color='green', marker='^', label='Buy')
                
                # Plot sell points
                sell_trades = trades_df[trades_df['action'] == 'sell']
                if not sell_trades.empty:
                    axes[0].scatter(sell_trades['timestamp'], sell_trades['price'], 
                                   color='red', marker='v', label='Sell')
                
                axes[0].set_title('Price and Trades')
                axes[0].set_xlabel('Time')
                axes[0].set_ylabel('Price')
                axes[0].legend()
            
            # Plot cumulative profit
            if 'pnl' in trades_df.columns:
                # Fill NaN with 0
                trades_df['pnl'] = trades_df['pnl'].fillna(0)
                
                # Compute cumulative profit
                cumulative_profit = np.cumsum(trades_df['pnl'])
                
                axes[1].plot(cumulative_profit)
                axes[1].set_title('Cumulative Profit/Loss')
                axes[1].set_xlabel('Trade')
                axes[1].set_ylabel('Cumulative P/L')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.model_dir, 'test_results.png'))
        plt.close()
        
        logger.info(f"Đã lưu biểu đồ kết quả kiểm thử")
    
    def predict(self, state: Dict) -> int:
        """
        Dự đoán hành động dựa trên trạng thái
        
        Args:
            state: Trạng thái hiện tại
        
        Returns:
            action: Hành động dự đoán
        """
        if self.agent is None:
            raise ValueError("Agent chưa được khởi tạo. Gọi prepare_environment trước.")
        
        # Dự đoán hành động
        return self.agent.act(state, training=False)
    
    def get_action_description(self, action: int) -> str:
        """
        Lấy mô tả hành động
        
        Args:
            action: Hành động
        
        Returns:
            str: Mô tả hành động
        """
        action_mapping = {
            0: "Không làm gì",
            1: "Mua (Long)",
            2: "Bán (Short)",
            3: "Đóng vị thế"
        }
        
        return action_mapping.get(action, "Không xác định")

# Hàm demo
def test_reinforcement_agent():
    """Demo sử dụng Reinforcement Agent"""
    from data_processor import DataProcessor
    from binance_api import BinanceAPI
    
    # Lấy dữ liệu
    binance_api = BinanceAPI()
    data_processor = DataProcessor(api=binance_api)
    
    # Tải dữ liệu
    symbol = 'BTCUSDT'
    interval = '1h'
    limit = 1000  # Lấy 1000 nến gần nhất
    
    df = data_processor.get_historical_data(symbol, interval, limit)
    
    # Chia thành tập training và test
    train_ratio = 0.8
    train_size = int(len(df) * train_ratio)
    
    train_df = df.iloc[:train_size]
    test_df = df.iloc[train_size:]
    
    # Khởi tạo ReinforcementTrader
    trader = ReinforcementTrader(
        model_dir='ml_models/reinforcement',
        use_double_dqn=True,
        window_size=60,
        batch_size=32,
        epsilon=0.5,
        mode='train'
    )
    
    # Chuẩn bị môi trường với dữ liệu training
    trader.prepare_environment(
        df=train_df,
        initial_balance=10000.0,
        transaction_fee_percent=0.04,
        reward_scaling=0.01,
        max_position_size=1.0,
        use_risk_adjustment=True
    )
    
    # Training agent
    train_results = trader.train(
        episodes=10,  # Số lượng episodes nhỏ cho demo
        batch_size=32,
        print_interval=1,
        save_best=True,
        plot_results=True
    )
    
    # Kiểm thử agent với dữ liệu test
    test_results = trader.test(
        df=test_df,
        plot_results=True,
        verbose=True
    )
    
    return trader, train_results, test_results

if __name__ == "__main__":
    # Demo và test
    trader, train_results, test_results = test_reinforcement_agent()