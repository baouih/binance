#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced Market Regime Detector - Bộ phát hiện chế độ thị trường nâng cao
"""

import os
import json
import logging
import random
from enum import Enum
from typing import Dict, List, Tuple, Union, Optional, Any

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('enhanced_market_regime')

# Định nghĩa các loại chế độ thị trường
class MarketRegimeType(str, Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    NEUTRAL = "neutral"

class EnhancedMarketRegimeDetector:
    """
    Bộ phát hiện chế độ thị trường nâng cao sử dụng nhiều phương pháp
    """
    
    def __init__(
        self,
        method: str = 'ensemble',
        lookback_period: int = 20,
        regime_change_threshold: float = 0.6,
        use_volatility_scaling: bool = True,
        models_dir: str = 'ml_models'
    ):
        """
        Khởi tạo bộ phát hiện chế độ thị trường nâng cao
        
        Args:
            method: Phương pháp phát hiện: 'ensemble', 'hmm', 'clustering', 'ml'
            lookback_period: Số nến nhìn lại để phân tích
            regime_change_threshold: Ngưỡng thay đổi chế độ
            use_volatility_scaling: Sử dụng điều chỉnh biến động
            models_dir: Thư mục lưu mô hình
        """
        self.method = method
        self.lookback_period = lookback_period
        self.regime_change_threshold = regime_change_threshold
        self.use_volatility_scaling = use_volatility_scaling
        self.models_dir = models_dir
        
        # Tạo thư mục lưu mô hình nếu chưa tồn tại
        os.makedirs(models_dir, exist_ok=True)
        
        # Trạng thái
        self.current_regime = MarketRegimeType.NEUTRAL
        self.regime_history = []
        self.confidence = 0.0
        
        logger.info(f"Đã khởi tạo EnhancedMarketRegimeDetector với phương pháp: {method}")
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Chuẩn bị đặc trưng từ dữ liệu giá
        
        Args:
            df: DataFrame chứa dữ liệu giá
        
        Returns:
            DataFrame chứa đặc trưng
        """
        # Giả lập tính toán đặc trưng
        features = df.copy()
        
        # Thêm đặc trưng chỉ báo xu hướng
        if 'close' in features.columns and len(features) > 5:
            # RSI
            if 'rsi_14' not in features.columns:
                features['rsi_14'] = self._mock_rsi(features['close'])
            
            # Stochastic
            if 'stochastic_k' not in features.columns:
                features['stochastic_k'] = self._mock_stochastic(features['close'])
            
            # Volatility
            if 'volatility' not in features.columns:
                features['volatility'] = self._calculate_volatility(features['close'])
            
            # Trend strength
            if 'trend_strength' not in features.columns:
                features['trend_strength'] = self._calculate_trend_strength(features)
            
            # Price momentum
            if 'price_momentum' not in features.columns:
                features['price_momentum'] = self._calculate_momentum(features['close'])
            
            # Volume trend
            if 'volume' in features.columns and 'volume_trend' not in features.columns:
                features['volume_trend'] = self._calculate_volume_trend(features['volume'])
        
        return features
    
    def _mock_rsi(self, price_series: pd.Series, period: int = 14) -> pd.Series:
        """
        Mô phỏng RSI 
        
        Args:
            price_series: Dữ liệu giá
            period: Chu kỳ
        
        Returns:
            Giá trị RSI
        """
        return pd.Series(np.random.uniform(30, 70, len(price_series)), index=price_series.index)
    
    def _mock_stochastic(self, price_series: pd.Series, period: int = 14) -> pd.Series:
        """
        Mô phỏng Stochastic
        
        Args:
            price_series: Dữ liệu giá
            period: Chu kỳ
        
        Returns:
            Giá trị Stochastic
        """
        return pd.Series(np.random.uniform(20, 80, len(price_series)), index=price_series.index)
    
    def _calculate_volatility(self, price_series: pd.Series, window: int = 20) -> pd.Series:
        """
        Tính biến động giá
        
        Args:
            price_series: Dữ liệu giá
            window: Cửa sổ tính toán
        
        Returns:
            Biến động
        """
        # Tính logarithmic returns
        returns = np.log(price_series / price_series.shift(1))
        # Standard deviation of returns
        volatility = returns.rolling(window=window).std() * np.sqrt(window)
        return volatility
    
    def _calculate_trend_strength(self, df: pd.DataFrame, window: int = 20) -> pd.Series:
        """
        Tính độ mạnh xu hướng
        
        Args:
            df: DataFrame chứa dữ liệu
            window: Cửa sổ tính toán
        
        Returns:
            Độ mạnh xu hướng
        """
        close = df['close']
        # Linear regression slope
        x = np.arange(window)
        
        def rolling_slope(y):
            if len(y) < window:
                return 0
            x_full = np.arange(len(y))
            slope = np.polyfit(x_full, y, 1)[0]
            return slope * window
        
        # Áp dụng hàm tính slope
        trend_strength = close.rolling(window=window).apply(rolling_slope, raw=True)
        
        # Chuẩn hóa
        if not trend_strength.isna().all():
            max_abs = trend_strength.abs().max()
            if max_abs > 0:
                trend_strength = trend_strength / max_abs
        
        return trend_strength
    
    def _calculate_momentum(self, price_series: pd.Series, period: int = 10) -> pd.Series:
        """
        Tính momentum
        
        Args:
            price_series: Dữ liệu giá
            period: Chu kỳ
        
        Returns:
            Momentum
        """
        return price_series.pct_change(period)
    
    def _calculate_volume_trend(self, volume_series: pd.Series, period: int = 10) -> pd.Series:
        """
        Tính xu hướng khối lượng
        
        Args:
            volume_series: Dữ liệu khối lượng
            period: Chu kỳ
        
        Returns:
            Xu hướng khối lượng
        """
        volume_sma = volume_series.rolling(window=period).mean()
        volume_trend = volume_series / volume_sma - 1
        return volume_trend
    
    def analyze_current_market(self, features_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Phân tích chế độ thị trường hiện tại
        
        Args:
            features_df: DataFrame chứa đặc trưng
        
        Returns:
            Dict chứa chế độ thị trường hiện tại và thông tin liên quan
        """
        result = {}
        
        # Lấy dữ liệu gần đây nhất
        recent_data = features_df.iloc[-self.lookback_period:].copy()
        
        # Phân tích dựa trên phương pháp được chọn
        if self.method == 'ensemble':
            result = self._analyze_ensemble(recent_data)
        elif self.method == 'hmm':
            result = self._analyze_hmm(recent_data)
        elif self.method == 'clustering':
            result = self._analyze_clustering(recent_data)
        elif self.method == 'ml':
            result = self._analyze_ml(recent_data)
        else:
            # Mặc định: ensemble
            result = self._analyze_ensemble(recent_data)
        
        # Cập nhật trạng thái hiện tại
        self.current_regime = result.get('regime', MarketRegimeType.NEUTRAL)
        self.confidence = result.get('confidence', 0.0)
        
        return result
    
    def _analyze_ensemble(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Phân tích sử dụng phương pháp tổng hợp
        
        Args:
            df: DataFrame chứa đặc trưng
        
        Returns:
            Dict chứa kết quả phân tích
        """
        # Mô phỏng phân tích tổng hợp
        # Tính điểm cho từng chế độ
        regime_scores = {
            MarketRegimeType.TRENDING_UP: 0,
            MarketRegimeType.TRENDING_DOWN: 0,
            MarketRegimeType.RANGING: 0,
            MarketRegimeType.VOLATILE: 0,
            MarketRegimeType.NEUTRAL: 0
        }
        
        try:
            # Phân tích xu hướng
            if 'trend_strength' in df.columns and not df['trend_strength'].isna().all():
                trend_strength = df['trend_strength'].iloc[-1]
                if trend_strength > 0.3:
                    regime_scores[MarketRegimeType.TRENDING_UP] += 1
                elif trend_strength < -0.3:
                    regime_scores[MarketRegimeType.TRENDING_DOWN] += 1
                else:
                    regime_scores[MarketRegimeType.RANGING] += 1
            
            # Phân tích biến động
            if 'volatility' in df.columns and not df['volatility'].isna().all():
                volatility = df['volatility'].iloc[-1]
                vol_avg = df['volatility'].mean()
                if volatility > vol_avg * 1.5:
                    regime_scores[MarketRegimeType.VOLATILE] += 1
                elif volatility < vol_avg * 0.5:
                    regime_scores[MarketRegimeType.RANGING] += 0.5
            
            # Phân tích RSI
            if 'rsi_14' in df.columns and not df['rsi_14'].isna().all():
                rsi = df['rsi_14'].iloc[-1]
                if rsi > 70:
                    regime_scores[MarketRegimeType.TRENDING_UP] += 0.5
                elif rsi < 30:
                    regime_scores[MarketRegimeType.TRENDING_DOWN] += 0.5
            
            # Phân tích momentum
            if 'price_momentum' in df.columns and not df['price_momentum'].isna().all():
                momentum = df['price_momentum'].iloc[-1]
                if momentum > 0.05:
                    regime_scores[MarketRegimeType.TRENDING_UP] += 0.5
                elif momentum < -0.05:
                    regime_scores[MarketRegimeType.TRENDING_DOWN] += 0.5
                else:
                    regime_scores[MarketRegimeType.RANGING] += 0.5
            
            # Phân tích khối lượng
            if 'volume_trend' in df.columns and not df['volume_trend'].isna().all():
                volume_trend = df['volume_trend'].iloc[-1]
                if volume_trend > 0.2:
                    regime_scores[MarketRegimeType.VOLATILE] += 0.5
            
            # Tính tổng điểm
            total_score = sum(regime_scores.values())
            if total_score == 0:
                # Mặc định neutral
                regime_probs = {regime: 0.2 for regime in regime_scores}
            else:
                # Chuẩn hóa thành xác suất
                regime_probs = {regime: score / total_score for regime, score in regime_scores.items()}
            
            # Chọn chế độ có điểm cao nhất
            max_regime = max(regime_scores.items(), key=lambda x: x[1])
            if max_regime[1] == 0:
                current_regime = MarketRegimeType.NEUTRAL
                confidence = 0.2
            else:
                current_regime = max_regime[0]
                confidence = max_regime[1] / total_score
            
            result = {
                'regime': current_regime,
                'confidence': confidence,
                'probabilities': regime_probs,
                'scores': regime_scores
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích ensemble: {str(e)}")
            return {
                'regime': MarketRegimeType.NEUTRAL,
                'confidence': 0.2,
                'probabilities': {regime: 0.2 for regime in regime_scores},
                'scores': regime_scores
            }
    
    def _analyze_hmm(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Phân tích sử dụng Hidden Markov Model
        
        Args:
            df: DataFrame chứa đặc trưng
        
        Returns:
            Dict chứa kết quả phân tích
        """
        # Mô phỏng phân tích HMM
        regimes = list(MarketRegimeType)
        probs = np.random.dirichlet(np.ones(len(regimes)))
        regime_probs = {regime: prob for regime, prob in zip(regimes, probs)}
        
        # Chọn chế độ có xác suất cao nhất
        max_regime = max(regime_probs.items(), key=lambda x: x[1])
        current_regime = max_regime[0]
        confidence = max_regime[1]
        
        return {
            'regime': current_regime,
            'confidence': confidence,
            'probabilities': regime_probs,
            'method': 'hmm'
        }
    
    def _analyze_clustering(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Phân tích sử dụng phương pháp clustering
        
        Args:
            df: DataFrame chứa đặc trưng
        
        Returns:
            Dict chứa kết quả phân tích
        """
        # Mô phỏng phân tích clustering
        regimes = list(MarketRegimeType)
        probs = np.random.dirichlet(np.ones(len(regimes)))
        regime_probs = {regime: prob for regime, prob in zip(regimes, probs)}
        
        # Chọn chế độ có xác suất cao nhất
        max_regime = max(regime_probs.items(), key=lambda x: x[1])
        current_regime = max_regime[0]
        confidence = max_regime[1]
        
        return {
            'regime': current_regime,
            'confidence': confidence,
            'probabilities': regime_probs,
            'method': 'clustering'
        }
    
    def _analyze_ml(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Phân tích sử dụng Machine Learning
        
        Args:
            df: DataFrame chứa đặc trưng
        
        Returns:
            Dict chứa kết quả phân tích
        """
        # Mô phỏng phân tích ML
        regimes = list(MarketRegimeType)
        probs = np.random.dirichlet(np.ones(len(regimes)))
        regime_probs = {regime: prob for regime, prob in zip(regimes, probs)}
        
        # Chọn chế độ có xác suất cao nhất
        max_regime = max(regime_probs.items(), key=lambda x: x[1])
        current_regime = max_regime[0]
        confidence = max_regime[1]
        
        return {
            'regime': current_regime,
            'confidence': confidence,
            'probabilities': regime_probs,
            'method': 'ml'
        }
    
    def detect_regime_changes(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Phát hiện thay đổi chế độ thị trường
        
        Args:
            df: DataFrame chứa dữ liệu
        
        Returns:
            Dict chứa các thời điểm thay đổi và thông tin liên quan
        """
        # Mô phỏng phát hiện thay đổi
        regimes = []
        changes = {}
        confidence_values = []
        
        # Phân tích từng khung thời gian
        for i in range(self.lookback_period, len(df)):
            window = df.iloc[i-self.lookback_period:i]
            analysis = self._analyze_ensemble(window)
            regime = analysis['regime']
            confidence = analysis['confidence']
            
            regimes.append(regime)
            confidence_values.append(confidence)
            
            # Phát hiện thay đổi
            if i > self.lookback_period and regimes[-1] != regimes[-2]:
                # Thay đổi chế độ
                changes[df.index[i]] = {
                    'from': regimes[-2],
                    'to': regimes[-1],
                    'confidence': confidence
                }
        
        return {
            'regimes': regimes,
            'changes': changes,
            'confidence': confidence_values
        }
    
    def save(self, filepath: Optional[str] = None) -> str:
        """
        Lưu trạng thái
        
        Args:
            filepath: Đường dẫn file lưu, None sẽ tạo tự động
        
        Returns:
            Đường dẫn đã lưu
        """
        # Tạo đường dẫn tự động nếu không chỉ định
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(self.models_dir, f"enhanced_regime_detector_{timestamp}.json")
        
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Dữ liệu detector
        detector_data = {
            'method': self.method,
            'lookback_period': self.lookback_period,
            'regime_change_threshold': self.regime_change_threshold,
            'use_volatility_scaling': self.use_volatility_scaling,
            'current_regime': self.current_regime,
            'confidence': self.confidence,
            'timestamp': datetime.now().isoformat()
        }
        
        # Lưu dữ liệu
        try:
            with open(filepath, 'w') as f:
                json.dump(detector_data, f, indent=2)
            logger.info(f"Đã lưu EnhancedMarketRegimeDetector tại: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Lỗi khi lưu EnhancedMarketRegimeDetector: {str(e)}")
            return ""
    
    def load(self, filepath: str) -> bool:
        """
        Tải trạng thái
        
        Args:
            filepath: Đường dẫn file
        
        Returns:
            True nếu tải thành công, False nếu thất bại
        """
        try:
            with open(filepath, 'r') as f:
                detector_data = json.load(f)
            
            # Khôi phục trạng thái
            self.method = detector_data['method']
            self.lookback_period = detector_data['lookback_period']
            self.regime_change_threshold = detector_data['regime_change_threshold']
            self.use_volatility_scaling = detector_data['use_volatility_scaling']
            self.current_regime = detector_data['current_regime']
            self.confidence = detector_data['confidence']
            
            logger.info(f"Đã tải EnhancedMarketRegimeDetector từ: {filepath}")
            return True
        
        except Exception as e:
            logger.error(f"Lỗi khi tải EnhancedMarketRegimeDetector: {str(e)}")
            return False

if __name__ == "__main__":
    # Demo
    import pandas as pd
    import numpy as np
    
    # Tạo dữ liệu mẫu
    n = 100
    dates = pd.date_range(start='2023-01-01', periods=n, freq='D')
    prices = np.cumsum(np.random.normal(0, 1, n)) + 100
    volumes = np.random.randint(100, 1000, n)
    
    df = pd.DataFrame({
        'close': prices,
        'open': prices * 0.99,
        'high': prices * 1.01,
        'low': prices * 0.98,
        'volume': volumes
    }, index=dates)
    
    # Khởi tạo detector
    detector = EnhancedMarketRegimeDetector()
    
    # Chuẩn bị đặc trưng
    features = detector.prepare_features(df)
    
    # Phân tích chế độ thị trường hiện tại
    current_regime = detector.analyze_current_market(features)
    print(f"Chế độ thị trường hiện tại: {current_regime['regime']}")
    print(f"Độ tin cậy: {current_regime['confidence']:.2f}")
    print(f"Xác suất: {current_regime['probabilities']}")
    
    # Phát hiện thay đổi chế độ
    changes = detector.detect_regime_changes(features)
    print(f"Số lượng thay đổi chế độ: {len(changes['changes'])}")
    
    # Lưu detector
    detector.save()