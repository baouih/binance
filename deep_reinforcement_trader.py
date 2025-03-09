#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Mô-đun Học Sâu & Học Tăng Cường cho Bot Giao Dịch Tiền Điện Tử

Module này cung cấp các khả năng học máy nâng cao để cải thiện tỷ lệ thắng và ROI của bot
thông qua học tăng cường (Reinforcement Learning), mạng nơ-ron học sâu, và phân tích
thị trường tự thích ứng dựa trên lịch sử hiệu suất.
"""

import os
import json
import logging
import time
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime, timedelta
import random
from collections import deque
import joblib
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score

# Định nghĩa logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("deep_reinforcement_trader")

# Constants
FEATURES_DIR = 'ml_models/features'
MODELS_DIR = 'ml_models/trained'
HISTORY_DIR = 'ml_results'

class DeepReinforcementTrader:
    """
    Lớp triển khai học tăng cường và học sâu cho giao dịch tiền điện tử,
    cải thiện hiệu suất bot thông qua học tập từ kinh nghiệm và tự thích ứng.
    """
    
    def __init__(self, 
                 data_processor=None,
                 market_regime_detector=None,
                 training_window: int = 100,
                 memory_size: int = 10000,
                 batch_size: int = 64,
                 gamma: float = 0.95,
                 epsilon: float = 1.0,
                 epsilon_min: float = 0.01,
                 epsilon_decay: float = 0.995,
                 learning_rate: float = 0.001,
                 model_update_frequency: int = 100):
        """
        Khởi tạo DeepReinforcementTrader
        
        Args:
            data_processor: Bộ xử lý dữ liệu thị trường
            market_regime_detector: Bộ phát hiện chế độ thị trường
            training_window (int): Số lượng mẫu dữ liệu để huấn luyện mô hình
            memory_size (int): Kích thước bộ nhớ kinh nghiệm
            batch_size (int): Kích thước batch để huấn luyện
            gamma (float): Hệ số chiết khấu cho phần thưởng tương lai (0-1)
            epsilon (float): Tỷ lệ khám phá ban đầu (0-1)
            epsilon_min (float): Tỷ lệ khám phá tối thiểu
            epsilon_decay (float): Tốc độ giảm tỷ lệ khám phá
            learning_rate (float): Tốc độ học của mô hình
            model_update_frequency (int): Tần suất cập nhật mô hình
        """
        self.data_processor = data_processor
        self.market_regime_detector = market_regime_detector
        
        # Tham số học tăng cường
        self.training_window = training_window
        self.memory_size = memory_size
        self.batch_size = batch_size
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.learning_rate = learning_rate
        self.model_update_frequency = model_update_frequency
        
        # Bộ nhớ trải nghiệm
        self.memory = deque(maxlen=memory_size)
        
        # Mô hình ML
        self.models = {}
        self.regime_models = {}
        self.action_models = {}
        self.state_scalers = {}
        
        # Lịch sử hiệu suất
        self.performance_history = []
        self.trading_results = []
        
        # Khởi tạo thư mục lưu trữ
        os.makedirs(FEATURES_DIR, exist_ok=True)
        os.makedirs(MODELS_DIR, exist_ok=True)
        os.makedirs(HISTORY_DIR, exist_ok=True)
        
        # Trạng thái huấn luyện
        self.train_step_counter = 0
        
        # Tải cấu hình AI nâng cao
        self.ai_config = self._load_advanced_ai_config()
        
        # Áp dụng cấu hình nâng cao
        if self.ai_config:
            # Cập nhật các tham số từ cấu hình
            ai_settings = self.ai_config.get('ai_settings', {})
            if ai_settings:
                self.epsilon = ai_settings.get('initial_exploration_rate', self.epsilon)
                self.epsilon_min = ai_settings.get('min_exploration_rate', self.epsilon_min)
                self.epsilon_decay = ai_settings.get('exploration_decay', self.epsilon_decay)
                self.batch_size = ai_settings.get('batch_size', self.batch_size)
                self.memory_size = ai_settings.get('memory_size', self.memory_size)
                self.model_update_frequency = ai_settings.get('model_update_frequency', self.model_update_frequency)
            
            logger.info(f"Đã áp dụng cấu hình nâng cao: epsilon={self.epsilon}, batch_size={self.batch_size}")
        
        # Tải mô hình nếu có
        self._load_models()
        
        logger.info("Đã khởi tạo Deep Reinforcement Trader")
    
    def extract_features(self, market_data: pd.DataFrame, timeframe: str) -> np.ndarray:
        """
        Trích xuất đặc trưng từ dữ liệu thị trường
        
        Args:
            market_data (pd.DataFrame): Dữ liệu thị trường
            timeframe (str): Khung thời gian
            
        Returns:
            np.ndarray: Mảng đặc trưng
        """
        if market_data.empty or len(market_data) < 50:
            logger.warning(f"Không đủ dữ liệu để trích xuất đặc trưng cho {timeframe}")
            return np.array([])
        
        try:
            # Chuẩn hóa giá
            closes = market_data['close'].values
            highs = market_data['high'].values
            lows = market_data['low'].values
            volumes = market_data['volume'].values if 'volume' in market_data.columns else np.zeros_like(closes)
            
            # Đặc trưng kỹ thuật
            features = []
            
            # Thay đổi giá
            price_change = np.diff(closes) / closes[:-1]
            price_change = np.append(0, price_change)
            features.append(price_change[-1])  # Thay đổi giá gần nhất
            
            # Thay đổi giá trung bình
            features.append(np.mean(price_change[-10:]))  # Thay đổi giá tb 10 chu kỳ
            features.append(np.mean(price_change[-20:]))  # Thay đổi giá tb 20 chu kỳ
            
            # Biến động
            volatility_10 = np.std(price_change[-10:])
            volatility_20 = np.std(price_change[-20:])
            features.append(volatility_10)
            features.append(volatility_20)
            
            # Chỉ số kỹ thuật
            if 'rsi' in market_data.columns:
                features.append(market_data['rsi'].iloc[-1] / 100.0)  # Chuẩn hóa RSI
            else:
                features.append(0.5)  # Giá trị mặc định nếu không có RSI
                
            if 'macd' in market_data.columns and 'macd_signal' in market_data.columns:
                macd_diff = market_data['macd'].iloc[-1] - market_data['macd_signal'].iloc[-1]
                features.append(np.tanh(macd_diff))  # Chuẩn hóa MACD
            else:
                features.append(0.0)  # Giá trị mặc định
                
            # Biến động Bollinger Bands
            if all(col in market_data.columns for col in ['bb_upper', 'bb_lower', 'sma']):
                bb_width = (market_data['bb_upper'].iloc[-1] - market_data['bb_lower'].iloc[-1]) / market_data['sma'].iloc[-1]
                bb_position = (closes[-1] - market_data['bb_lower'].iloc[-1]) / (market_data['bb_upper'].iloc[-1] - market_data['bb_lower'].iloc[-1])
                features.append(bb_width)
                features.append(bb_position)
            else:
                features.extend([0.2, 0.5])  # Giá trị mặc định
                
            # Mẫu hình giá
            if len(closes) >= 5:
                price_pattern = (closes[-1] - closes[-5]) / closes[-5]
                features.append(price_pattern)
            else:
                features.append(0.0)
                
            # Khối lượng giao dịch
            if len(volumes) >= 5:
                volume_change = (volumes[-1] - np.mean(volumes[-5:])) / np.mean(volumes[-5:]) if np.mean(volumes[-5:]) > 0 else 0
                features.append(volume_change)
            else:
                features.append(0.0)
                
            # Tỷ lệ High-Low
            if len(highs) >= 5 and len(lows) >= 5:
                hl_ratio = (highs[-1] - lows[-1]) / closes[-1]
                features.append(hl_ratio)
            else:
                features.append(0.02)  # Giá trị mặc định
                
            # Chế độ thị trường (nếu có)
            if self.market_regime_detector:
                regime = self.market_regime_detector.detect_regime(market_data)
                regime_encoding = {
                    'trending': 1.0,
                    'ranging': 0.5,
                    'volatile': 0.25,
                    'quiet': 0.0,
                    'neutral': 0.5
                }
                features.append(regime_encoding.get(regime, 0.5))
            else:
                features.append(0.5)  # Giá trị mặc định
            
            # Các đặc trưng ADX
            if all(col in market_data.columns for col in ['adx', 'di_plus', 'di_minus']):
                features.append(market_data['adx'].iloc[-1] / 100.0)
                features.append((market_data['di_plus'].iloc[-1] - market_data['di_minus'].iloc[-1]) / 100.0)
            else:
                features.extend([0.2, 0.0])
            
            # Diễn biến khối lượng giao dịch
            if 'volume' in market_data.columns and len(market_data) >= 10:
                vol_avg = np.mean(market_data['volume'][-10:])
                vol_current = market_data['volume'].iloc[-1]
                features.append(vol_current / vol_avg if vol_avg > 0 else 1.0)
            else:
                features.append(1.0)
                
            # Chuyển đổi thành mảng numpy
            feature_array = np.array(features, dtype=np.float32)
            
            # Xử lý giá trị NaN hoặc inf
            feature_array = np.nan_to_num(feature_array, nan=0.0, posinf=1.0, neginf=-1.0)
            
            return feature_array
            
        except Exception as e:
            logger.error(f"Lỗi khi trích xuất đặc trưng: {str(e)}")
            return np.zeros(15)  # Trả về vector 0 với số lượng đặc trưng đã định nghĩa
    
    def create_state(self, symbol: str, timeframe: str) -> np.ndarray:
        """
        Tạo vector trạng thái từ dữ liệu thị trường hiện tại
        
        Args:
            symbol (str): Mã cặp giao dịch
            timeframe (str): Khung thời gian
            
        Returns:
            np.ndarray: Vector trạng thái
        """
        try:
            # Lấy dữ liệu thị trường
            if self.data_processor:
                market_data = self.data_processor.get_market_data(symbol, timeframe, limit=100)
            else:
                logger.error("Không có data_processor để lấy dữ liệu thị trường")
                return np.zeros(15)
            
            # Trích xuất đặc trưng
            features = self.extract_features(market_data, timeframe)
            
            # Chuẩn hóa đặc trưng
            if f"{symbol}_{timeframe}" not in self.state_scalers:
                self.state_scalers[f"{symbol}_{timeframe}"] = MinMaxScaler(feature_range=(-1, 1))
                # Khởi tạo với dữ liệu mẫu để tránh lỗi reshape
                sample_data = np.random.random((10, len(features)))
                self.state_scalers[f"{symbol}_{timeframe}"].fit(sample_data)
            
            # Reshape và chuẩn hóa
            if len(features) > 0:
                features = features.reshape(1, -1)
                features = self.state_scalers[f"{symbol}_{timeframe}"].transform(features).flatten()
            
            return features
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo trạng thái: {str(e)}")
            return np.zeros(15)
    
    def predict_action(self, state: np.ndarray, symbol: str, timeframe: str, 
                      market_regime: str = 'neutral') -> Tuple[int, float, Dict]:
        """
        Dự đoán hành động (mua/bán/giữ) dựa trên trạng thái hiện tại
        
        Args:
            state (np.ndarray): Vector trạng thái
            symbol (str): Mã cặp giao dịch
            timeframe (str): Khung thời gian
            market_regime (str): Chế độ thị trường
            
        Returns:
            Tuple[int, float, Dict]: (Hành động, Độ tin cậy, Chi tiết)
            Hành động: 0 = HOLD, 1 = BUY, 2 = SELL
        """
        if len(state) == 0:
            logger.warning(f"Không có dữ liệu trạng thái cho {symbol}_{timeframe}")
            return 0, 0.0, {'reason': 'Không có dữ liệu', 'scores': {0: 0.34, 1: 0.33, 2: 0.33}}
        
        # Exploration: lựa chọn ngẫu nhiên với xác suất epsilon
        if random.random() < self.epsilon:
            action = random.choice([0, 1, 2])
            return action, 0.33, {'reason': 'Exploration', 'scores': {0: 0.33, 1: 0.33, 2: 0.34}}
        
        # Exploitation: sử dụng mô hình để dự đoán
        model_key = f"{symbol}_{timeframe}"
        regime_model_key = f"{market_regime}"
        
        scores = {0: 0.33, 1: 0.33, 2: 0.34}  # Mặc định cân bằng
        
        # Dự đoán từ mô hình cặp giao dịch cụ thể
        if model_key in self.models:
            try:
                # Dự đoán xác suất cho mỗi lớp
                proba = self.models[model_key].predict_proba(state.reshape(1, -1))[0]
                for i, p in enumerate(proba):
                    scores[i] = p
            except Exception as e:
                logger.error(f"Lỗi khi dự đoán từ mô hình {model_key}: {str(e)}")
        
        # Dự đoán từ mô hình chế độ thị trường
        if regime_model_key in self.regime_models:
            try:
                regime_proba = self.regime_models[regime_model_key].predict_proba(state.reshape(1, -1))[0]
                
                # Kết hợp xác suất (mô hình cụ thể được ưu tiên hơn)
                if model_key in self.models:
                    for i, p in enumerate(regime_proba):
                        scores[i] = 0.7 * scores[i] + 0.3 * p  # Kết hợp theo trọng số
                else:
                    for i, p in enumerate(regime_proba):
                        scores[i] = p
            except Exception as e:
                logger.error(f"Lỗi khi dự đoán từ mô hình chế độ {regime_model_key}: {str(e)}")
        
        # Xác định hành động với điểm cao nhất
        action = max(scores, key=scores.get)
        confidence = scores[action]
        
        # Tạo lý do cho quyết định
        reasons = {
            0: "Giữ - Không có tín hiệu rõ ràng",
            1: "Mua - Tín hiệu tăng giá mạnh",
            2: "Bán - Tín hiệu giảm giá mạnh"
        }
        
        return action, confidence, {
            'reason': reasons[action],
            'scores': scores,
            'model_used': model_key if model_key in self.models else regime_model_key
        }
    
    def remember(self, state: np.ndarray, action: int, reward: float, 
                next_state: np.ndarray, done: bool, metadata: Dict) -> None:
        """
        Lưu trải nghiệm vào bộ nhớ
        
        Args:
            state (np.ndarray): Trạng thái hiện tại
            action (int): Hành động đã thực hiện (0=HOLD, 1=BUY, 2=SELL)
            reward (float): Phần thưởng nhận được
            next_state (np.ndarray): Trạng thái tiếp theo
            done (bool): Đã hoàn thành giao dịch chưa
            metadata (Dict): Thông tin bổ sung (symbol, timeframe, etc.)
        """
        if len(state) == 0 or len(next_state) == 0:
            return
            
        self.memory.append((state, action, reward, next_state, done, metadata))
        
        # Giảm epsilon theo thời gian (khám phá giảm dần)
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
    
    def replay(self, batch_size: int = None) -> float:
        """
        Huấn luyện mô hình từ bộ nhớ trải nghiệm
        
        Args:
            batch_size (int, optional): Kích thước batch
            
        Returns:
            float: Giá trị hàm mất mát
        """
        batch_size = batch_size or self.batch_size
        
        if len(self.memory) < batch_size:
            return 0.0
        
        # Tăng biến đếm huấn luyện
        self.train_step_counter += 1
        
        # Lấy batch dữ liệu từ bộ nhớ
        minibatch = random.sample(self.memory, batch_size)
        
        # Nhóm dữ liệu theo symbol và timeframe
        grouped_samples = {}
        for state, action, reward, next_state, done, metadata in minibatch:
            key = f"{metadata['symbol']}_{metadata['timeframe']}"
            if key not in grouped_samples:
                grouped_samples[key] = []
            grouped_samples[key].append((state, action, reward, next_state, done, metadata))
        
        loss_sum = 0.0
        
        # Huấn luyện mô hình cho từng nhóm
        for key, samples in grouped_samples.items():
            if len(samples) < 5:  # Cần ít nhất 5 mẫu để huấn luyện
                continue
                
            # Chuẩn bị dữ liệu huấn luyện
            X = np.array([s[0] for s in samples])
            y = np.array([s[1] for s in samples])
            
            # Kiểm tra xem đã tồn tại mô hình chưa
            if key not in self.models:
                self.models[key] = RandomForestClassifier(n_estimators=100)
                
            # Huấn luyện mô hình
            try:
                self.models[key].fit(X, y)
                
                # Tính loss (dùng accuracy như là một proxy)
                y_pred = self.models[key].predict(X)
                acc = accuracy_score(y, y_pred)
                loss_sum += (1.0 - acc)  # Convert accuracy thành loss
                
                logger.info(f"Huấn luyện mô hình {key}: Accuracy = {acc:.4f}")
                
                # Lưu mô hình định kỳ
                if self.train_step_counter % self.model_update_frequency == 0:
                    self._save_model(key, self.models[key])
                    
            except Exception as e:
                logger.error(f"Lỗi khi huấn luyện mô hình {key}: {str(e)}")
        
        # Huấn luyện mô hình theo chế độ thị trường
        regime_samples = {}
        for state, action, reward, next_state, done, metadata in minibatch:
            regime = metadata.get('market_regime', 'neutral')
            if regime not in regime_samples:
                regime_samples[regime] = []
            regime_samples[regime].append((state, action, reward, next_state, done, metadata))
        
        for regime, samples in regime_samples.items():
            if len(samples) < 10:  # Cần nhiều mẫu hơn cho mô hình chế độ thị trường
                continue
                
            # Chuẩn bị dữ liệu huấn luyện
            X = np.array([s[0] for s in samples])
            y = np.array([s[1] for s in samples])
            
            # Kiểm tra xem đã tồn tại mô hình chưa
            if regime not in self.regime_models:
                self.regime_models[regime] = GradientBoostingClassifier(n_estimators=100)
                
            # Huấn luyện mô hình
            try:
                self.regime_models[regime].fit(X, y)
                
                # Tính loss
                y_pred = self.regime_models[regime].predict(X)
                acc = accuracy_score(y, y_pred)
                
                logger.info(f"Huấn luyện mô hình chế độ {regime}: Accuracy = {acc:.4f}")
                
                # Lưu mô hình định kỳ
                if self.train_step_counter % self.model_update_frequency == 0:
                    self._save_model(f"regime_{regime}", self.regime_models[regime])
                    
            except Exception as e:
                logger.error(f"Lỗi khi huấn luyện mô hình chế độ {regime}: {str(e)}")
        
        return loss_sum / len(grouped_samples) if grouped_samples else 0.0
    
    def calculate_reward(self, action: int, pnl: float, market_change: float, 
                        position_duration: int, confidence: float) -> float:
        """
        Tính toán phần thưởng cho một hành động
        
        Args:
            action (int): Hành động đã thực hiện (0=HOLD, 1=BUY, 2=SELL)
            pnl (float): Lợi nhuận/lỗ từ giao dịch (%)
            market_change (float): Thay đổi giá thị trường (%)
            position_duration (int): Thời gian giữ vị thế (phút)
            confidence (float): Độ tin cậy của dự đoán
            
        Returns:
            float: Giá trị phần thưởng
        """
        # Phần thưởng cơ bản từ P/L
        base_reward = pnl
        
        # Điều chỉnh phần thưởng theo hành động và diễn biến thị trường
        if action == 1:  # BUY
            # Thưởng cao nếu mua đúng thị trường tăng
            if market_change > 0:
                action_reward = 1.0 + market_change
            else:
                action_reward = -0.5  # Phạt nhẹ nếu mua trong thị trường giảm
                
        elif action == 2:  # SELL
            # Thưởng cao nếu bán đúng thị trường giảm
            if market_change < 0:
                action_reward = 1.0 - market_change
            else:
                action_reward = -0.5  # Phạt nhẹ nếu bán trong thị trường tăng
                
        else:  # HOLD
            # Thưởng nhẹ nếu giữ đúng trong thị trường đi ngang
            if abs(market_change) < 0.5:
                action_reward = 0.2
            else:
                action_reward = -0.1  # Phạt nhẹ nếu giữ trong thị trường có xu hướng rõ ràng
        
        # Điều chỉnh theo thời gian giữ vị thế (ưu tiên các vị thế ngắn hạn có lãi)
        if pnl > 0:
            duration_factor = max(0, 1.0 - (position_duration / (24*60*3)))  # Giảm dần trong 3 ngày
        else:
            duration_factor = min(0, -0.5 * (position_duration / (24*60*1)))  # Phạt nặng dần cho vị thế lỗ kéo dài
        
        # Điều chỉnh theo độ tin cậy
        confidence_reward = (confidence - 0.33) * 2.0  # Thưởng cho độ tin cậy cao hơn ngẫu nhiên
        
        # Tổng hợp phần thưởng
        total_reward = (0.6 * base_reward) + (0.25 * action_reward) + (0.1 * duration_factor) + (0.05 * confidence_reward)
        
        return total_reward
    
    def update_trading_results(self, trade_result: Dict) -> None:
        """
        Cập nhật kết quả giao dịch để sử dụng trong huấn luyện
        
        Args:
            trade_result (Dict): Kết quả của một giao dịch đã đóng
        """
        self.trading_results.append(trade_result)
        
        # Giới hạn kích thước
        if len(self.trading_results) > 1000:
            self.trading_results.pop(0)
            
        # Lưu định kỳ
        if len(self.trading_results) % 10 == 0:
            self._save_trading_results()
    
    def get_action_for_signal(self, symbol: str, timeframe: str, 
                            market_regime: str = 'neutral') -> Dict:
        """
        Lấy hành động giao dịch cho một cặp tiền tệ
        
        Args:
            symbol (str): Mã cặp giao dịch
            timeframe (str): Khung thời gian
            market_regime (str): Chế độ thị trường
            
        Returns:
            Dict: Tín hiệu giao dịch
        """
        try:
            # Tạo trạng thái từ dữ liệu thị trường
            state = self.create_state(symbol, timeframe)
            
            # Dự đoán hành động
            action, confidence, details = self.predict_action(state, symbol, timeframe, market_regime)
            
            # Chuyển đổi hành động sang tín hiệu
            action_mapping = {
                0: "HOLD",
                1: "BUY",
                2: "SELL"
            }
            
            signal = {
                'symbol': symbol,
                'timeframe': timeframe,
                'action': action_mapping[action],
                'confidence': confidence * 100,  # Chuyển về phần trăm
                'signal': 0.0,  # Mặc định
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'details': details,
                'source': 'deep_reinforcement',
                'market_regime': market_regime
            }
            
            # Điều chỉnh giá trị tín hiệu (-1.0 đến 1.0) theo hành động
            if action == 1:  # BUY
                signal['signal'] = confidence
            elif action == 2:  # SELL
                signal['signal'] = -confidence
            
            return signal
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy hành động cho {symbol}_{timeframe}: {str(e)}")
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'action': "HOLD",
                'confidence': 33.0,
                'signal': 0.0,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'details': {'reason': 'Lỗi khi xử lý', 'error': str(e)},
                'source': 'deep_reinforcement_error',
                'market_regime': market_regime
            }
    
    def learn_from_trade(self, trade: Dict) -> None:
        """
        Học từ một giao dịch đã hoàn thành
        
        Args:
            trade (Dict): Thông tin giao dịch
        """
        try:
            symbol = trade.get('symbol', '')
            timeframe = trade.get('timeframe', '1h')  # Mặc định 1h nếu không có
            
            # Bỏ qua nếu không có symbol
            if not symbol:
                return
                
            # Ánh xạ hành động
            action_mapping = {
                'BUY': 1,
                'SELL': 2,
                'HOLD': 0
            }
            action = action_mapping.get(trade.get('side', 'HOLD'), 0)
            
            # Tính phần thưởng
            pnl_percent = trade.get('profit_loss_percent', 0.0)
            
            # Lấy thay đổi thị trường tổng thể
            market_change = 0.0
            if self.data_processor:
                try:
                    current_data = self.data_processor.get_market_data(symbol, timeframe, limit=2)
                    if not current_data.empty and len(current_data) > 1:
                        market_change = (current_data['close'].iloc[-1] - current_data['close'].iloc[-2]) / current_data['close'].iloc[-2] * 100
                except Exception as e:
                    logger.warning(f"Không thể lấy thay đổi thị trường: {str(e)}")
            
            # Tính thời gian giữ vị thế
            entry_time = datetime.strptime(trade.get('entry_time', ''), '%Y-%m-%d %H:%M:%S')
            exit_time = datetime.strptime(trade.get('exit_time', ''), '%Y-%m-%d %H:%M:%S')
            position_duration = int((exit_time - entry_time).total_seconds() / 60)  # Phút
            
            # Lấy thông tin thị trường tại thời điểm vào lệnh
            if self.data_processor:
                try:
                    # Tạo trạng thái trước khi vào lệnh
                    entry_data = self.data_processor.get_market_data(symbol, timeframe, limit=100)
                    entry_state = self.extract_features(entry_data, timeframe)
                    
                    # Tạo trạng thái sau khi đóng lệnh
                    exit_data = self.data_processor.get_market_data(symbol, timeframe, limit=100)
                    exit_state = self.extract_features(exit_data, timeframe)
                    
                    # Xác định chế độ thị trường
                    market_regime = self.market_regime_detector.detect_regime(entry_data) if self.market_regime_detector else 'neutral'
                    
                    # Tính phần thưởng
                    confidence = trade.get('confidence', 50.0) / 100.0
                    reward = self.calculate_reward(action, pnl_percent, market_change, position_duration, confidence)
                    
                    # Lưu trải nghiệm
                    metadata = {
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'market_regime': market_regime,
                        'entry_time': trade.get('entry_time', ''),
                        'exit_time': trade.get('exit_time', ''),
                        'pnl': pnl_percent,
                        'market_change': market_change
                    }
                    
                    self.remember(entry_state, action, reward, exit_state, True, metadata)
                    
                    # Cập nhật dữ liệu kết quả giao dịch
                    trade['reward'] = reward
                    trade['market_regime'] = market_regime
                    trade['market_change'] = market_change
                    self.update_trading_results(trade)
                    
                    # Huấn luyện nếu có đủ dữ liệu
                    if len(self.memory) >= self.batch_size:
                        loss = self.replay()
                        logger.info(f"Học từ giao dịch {symbol} {trade.get('side')}: " +
                                  f"Reward={reward:.4f}, Loss={loss:.4f}")
                    
                except Exception as e:
                    logger.error(f"Lỗi khi học từ giao dịch: {str(e)}")
            
        except Exception as e:
            logger.error(f"Lỗi khi xử lý trade trong học tăng cường: {str(e)}")
    
    def _save_model(self, model_name: str, model) -> bool:
        """
        Lưu mô hình ML
        
        Args:
            model_name (str): Tên mô hình
            model: Mô hình cần lưu
            
        Returns:
            bool: True nếu lưu thành công, False nếu thất bại
        """
        try:
            filename = os.path.join(MODELS_DIR, f"{model_name}.joblib")
            joblib.dump(model, filename)
            logger.info(f"Đã lưu mô hình {model_name}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu mô hình {model_name}: {str(e)}")
            return False
    
    def _load_advanced_ai_config(self) -> Dict:
        """
        Tải cấu hình AI nâng cao từ file JSON
        
        Returns:
            Dict: Cấu hình AI nâng cao
        """
        config_path = "configs/advanced_ai_config.json"
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình AI nâng cao từ {config_path}")
                return config
            else:
                logger.warning(f"Không tìm thấy file cấu hình AI nâng cao: {config_path}")
                return {}
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình AI nâng cao: {str(e)}")
            return {}

    def _load_models(self) -> bool:
        """
        Tải tất cả các mô hình ML đã lưu
        
        Returns:
            bool: True nếu tải thành công ít nhất một mô hình, False nếu không
        """
        try:
            if not os.path.exists(MODELS_DIR):
                logger.info("Chưa có thư mục mô hình, sẽ tạo mô hình mới")
                return False
                
            # Tải các mô hình
            model_count = 0
            for filename in os.listdir(MODELS_DIR):
                if filename.endswith('.joblib'):
                    try:
                        model_path = os.path.join(MODELS_DIR, filename)
                        model_name = filename.replace('.joblib', '')
                        
                        # Tải mô hình
                        model = joblib.load(model_path)
                        
                        # Phân loại mô hình
                        if model_name.startswith('regime_'):
                            regime = model_name.replace('regime_', '')
                            self.regime_models[regime] = model
                        else:
                            self.models[model_name] = model
                            
                        model_count += 1
                        
                    except Exception as e:
                        logger.error(f"Lỗi khi tải mô hình {filename}: {str(e)}")
            
            logger.info(f"Đã tải {model_count} mô hình")
            
            # Tải kết quả giao dịch
            self._load_trading_results()
            
            return model_count > 0
            
        except Exception as e:
            logger.error(f"Lỗi khi tải mô hình: {str(e)}")
            return False
    
    def _save_trading_results(self) -> bool:
        """
        Lưu kết quả giao dịch
        
        Returns:
            bool: True nếu lưu thành công, False nếu thất bại
        """
        try:
            filename = os.path.join(HISTORY_DIR, "trading_results.json")
            with open(filename, 'w') as f:
                json.dump(self.trading_results, f)
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu kết quả giao dịch: {str(e)}")
            return False
    
    def _load_trading_results(self) -> bool:
        """
        Tải kết quả giao dịch
        
        Returns:
            bool: True nếu tải thành công, False nếu thất bại
        """
        try:
            filename = os.path.join(HISTORY_DIR, "trading_results.json")
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    self.trading_results = json.load(f)
                logger.info(f"Đã tải {len(self.trading_results)} kết quả giao dịch")
                return True
            return False
        except Exception as e:
            logger.error(f"Lỗi khi tải kết quả giao dịch: {str(e)}")
            return False
    
    def get_performance_summary(self) -> Dict:
        """
        Lấy tóm tắt hiệu suất của mô hình
        
        Returns:
            Dict: Tóm tắt hiệu suất
        """
        # Tính toán hiệu suất từ kết quả giao dịch
        results = {
            'total_trades': len(self.trading_results),
            'models': len(self.models),
            'regime_models': len(self.regime_models),
            'memory_size': len(self.memory),
            'exploration_rate': self.epsilon
        }
        
        # Tính hiệu suất nếu có đủ giao dịch
        if self.trading_results:
            profit_trades = [t for t in self.trading_results if t.get('pnl', 0) > 0]
            loss_trades = [t for t in self.trading_results if t.get('pnl', 0) <= 0]
            
            results['profitable_trades'] = len(profit_trades)
            results['losing_trades'] = len(loss_trades)
            results['win_rate'] = (len(profit_trades) / len(self.trading_results)) * 100 if self.trading_results else 0
            
            # Tính ROI
            total_profit = sum(t.get('pnl', 0) for t in profit_trades)
            total_loss = sum(t.get('pnl', 0) for t in loss_trades)
            results['total_profit'] = total_profit
            results['total_loss'] = total_loss
            results['net_profit'] = total_profit + total_loss
            
            # Phân tích theo chế độ thị trường
            regime_performance = {}
            for trade in self.trading_results:
                regime = trade.get('market_regime', 'unknown')
                if regime not in regime_performance:
                    regime_performance[regime] = {
                        'count': 0,
                        'profit': 0,
                        'win': 0
                    }
                
                regime_performance[regime]['count'] += 1
                regime_performance[regime]['profit'] += trade.get('pnl', 0)
                if trade.get('pnl', 0) > 0:
                    regime_performance[regime]['win'] += 1
            
            # Tính tỷ lệ thắng cho mỗi chế độ
            for regime, data in regime_performance.items():
                if data['count'] > 0:
                    data['win_rate'] = (data['win'] / data['count']) * 100
            
            results['regime_performance'] = regime_performance
        
        return results

def main():
    """Hàm chính để test DeepReinforcementTrader"""
    # Khởi tạo các thành phần cần thiết
    from data_processor import DataProcessor
    from market_regime_detector import MarketRegimeDetector
    
    data_processor = DataProcessor()
    market_regime_detector = MarketRegimeDetector()
    
    # Khởi tạo DeepReinforcementTrader
    trader = DeepReinforcementTrader(
        data_processor=data_processor,
        market_regime_detector=market_regime_detector
    )
    
    # Lấy dữ liệu để test
    symbol = 'BTCUSDT'
    timeframe = '1h'
    
    # Lấy dữ liệu thị trường
    market_data = data_processor.get_market_data(symbol, timeframe, limit=100)
    
    # Tạo trạng thái
    state = trader.create_state(symbol, timeframe)
    print(f"State shape: {state.shape}")
    
    # Dự đoán hành động
    action, confidence, details = trader.predict_action(state, symbol, timeframe)
    print(f"Predicted action: {action}, Confidence: {confidence:.4f}")
    print(f"Details: {details}")
    
    # Tạo tín hiệu giao dịch
    signal = trader.get_action_for_signal(symbol, timeframe)
    print(f"Trading signal: {signal}")
    
    # Hiển thị tóm tắt hiệu suất
    print("\nPerformance Summary:")
    performance = trader.get_performance_summary()
    for key, value in performance.items():
        if key != 'regime_performance':
            print(f"{key}: {value}")
    
    print("\nRegime Performance:")
    for regime, data in performance.get('regime_performance', {}).items():
        print(f"{regime}: Win Rate={data.get('win_rate', 0):.2f}%, Count={data.get('count', 0)}, Profit={data.get('profit', 0):.2f}")

if __name__ == "__main__":
    main()