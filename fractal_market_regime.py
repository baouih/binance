"""
Module phát hiện chế độ thị trường sử dụng phân tích fractal

Module này cung cấp công cụ phân tích thị trường tiên tiến dựa trên lý thuyết fractal
để phát hiện chế độ thị trường như trending, ranging, volatile, quiet, và choppy.
Điều này giúp hệ thống giao dịch thích nghi với điều kiện thị trường hiện tại.
"""

import math
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Any
from scipy import stats

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('fractal_market_regime')

class FractalMarketRegimeDetector:
    """Phát hiện chế độ thị trường sử dụng phân tích fractal"""
    
    def __init__(self, lookback_periods: int = 100):
        """
        Khởi tạo bộ phát hiện
        
        Args:
            lookback_periods (int): Số chu kỳ nhìn lại
        """
        self.lookback_periods = lookback_periods
        self.regimes = ["trending", "ranging", "volatile", "quiet", "choppy"]
        self.current_regime = "unknown"
        self.current_confidence = 0.0
        self.regime_history = []
        logger.info(f"Đã khởi tạo FractalMarketRegimeDetector với {lookback_periods} chu kỳ")
    
    def detect_regime(self, price_data: pd.DataFrame) -> Dict:
        """
        Phát hiện chế độ thị trường dựa trên phân tích fractal
        
        Args:
            price_data (pd.DataFrame): Dữ liệu giá (OHLCV)
            
        Returns:
            Dict: Kết quả phát hiện với chế độ và độ tin cậy
        """
        if len(price_data) < self.lookback_periods:
            logger.warning(f"Không đủ dữ liệu ({len(price_data)}/{self.lookback_periods}) cho phân tích fractal")
            return {"regime": "unknown", "confidence": 0.0, "details": {}}
        
        logger.info(f"Bắt đầu phát hiện chế độ thị trường với {len(price_data)} candlesticks")
        
        # Trích xuất đặc trưng fractal và thống kê
        features = self._extract_features(price_data)
        
        # Tính điểm cho từng chế độ
        regime_scores = self._calculate_regime_scores(features)
        
        # Chọn chế độ có điểm cao nhất
        top_regime = max(regime_scores.items(), key=lambda x: x[1])
        total_score = sum(regime_scores.values())
        
        # Cập nhật chế độ hiện tại
        self.current_regime = top_regime[0]
        self.current_confidence = top_regime[1] / total_score if total_score > 0 else 0
        
        # Lưu vào lịch sử
        self.regime_history.append({
            "timestamp": price_data.index[-1] if hasattr(price_data, 'index') else None,
            "regime": self.current_regime,
            "confidence": self.current_confidence,
            "scores": regime_scores
        })
        
        # Giới hạn kích thước lịch sử
        if len(self.regime_history) > 100:
            self.regime_history.pop(0)
        
        logger.info(f"Chế độ thị trường: {self.current_regime}, độ tin cậy: {self.current_confidence:.2f}")
        
        return {
            "regime": self.current_regime,
            "confidence": self.current_confidence,
            "details": {
                "regime_scores": regime_scores,
                "features": features
            }
        }
    
    def _extract_features(self, price_data: pd.DataFrame) -> Dict:
        """
        Trích xuất các đặc trưng fractal và thống kê từ dữ liệu giá
        
        Args:
            price_data (pd.DataFrame): Dữ liệu giá
            
        Returns:
            Dict: Các đặc trưng
        """
        # Lấy dữ liệu đóng cửa
        close_prices = price_data['close'].values[-self.lookback_periods:]
        
        # Tính Hurst Exponent (chỉ số fractal)
        hurst = self._calculate_hurst_exponent(close_prices)
        
        # Tính chỉ số khác
        atr = self._calculate_atr(price_data)
        atr_ratio = atr / np.mean(close_prices[-20:]) * 100
        
        # Tính chỉ số xu hướng (ADX)
        adx = self._calculate_adx(price_data)
        
        # Độ dịch chuyển biến động
        volatility_shift = self._calculate_volatility_shift(price_data)
        
        # Tính logarithmic return distribution
        log_returns = np.diff(np.log(close_prices))
        skewness = stats.skew(log_returns)
        kurtosis = stats.kurtosis(log_returns)
        
        # Fractal Dimension
        fractal_dimension = self._calculate_fractal_dimension(close_prices)
        
        return {
            "hurst_exponent": hurst,
            "atr_ratio": atr_ratio,
            "adx": adx,
            "volatility_shift": volatility_shift,
            "return_skewness": skewness,
            "return_kurtosis": kurtosis,
            "fractal_dimension": fractal_dimension
        }
    
    def _calculate_regime_scores(self, features: Dict) -> Dict:
        """
        Tính điểm cho từng chế độ thị trường dựa trên đặc trưng
        
        Args:
            features (Dict): Các đặc trưng thị trường
            
        Returns:
            Dict: Điểm cho từng chế độ
        """
        scores = {regime: 0.0 for regime in self.regimes}
        
        # ===== Trending =====
        # Trending thường có Hurst > 0.6 và ADX > 25
        if features["hurst_exponent"] > 0.6:
            scores["trending"] += (features["hurst_exponent"] - 0.6) * 10
        
        if features["adx"] > 25:
            scores["trending"] += (features["adx"] - 25) / 25
            
        # Phân phối lợi nhuận lệch (skewed)
        if abs(features["return_skewness"]) > 0.5:
            scores["trending"] += abs(features["return_skewness"]) - 0.5
        
        # Fractal Dimension thấp hơn trong trending markets
        if features["fractal_dimension"] < 1.4:
            scores["trending"] += (1.4 - features["fractal_dimension"]) * 5
        
        # ===== Ranging =====
        # Ranging thường có Hurst ~ 0.5 và ADX thấp
        if 0.45 <= features["hurst_exponent"] <= 0.55:
            scores["ranging"] += 1 - abs(features["hurst_exponent"] - 0.5) * 10
            
        if features["adx"] < 25:
            scores["ranging"] += (25 - features["adx"]) / 25
            
        # Fractal Dimension cao hơn trong ranging markets
        if 1.4 <= features["fractal_dimension"] <= 1.6:
            scores["ranging"] += 1 - abs(features["fractal_dimension"] - 1.5) * 5
        
        # ===== Volatile =====
        # Volatile có ATR cao và volatility shift lớn
        if features["atr_ratio"] > 2:
            scores["volatile"] += features["atr_ratio"] / 2
            
        if features["volatility_shift"] > 1.5:
            scores["volatile"] += features["volatility_shift"] - 1
            
        # Kurtosis cao (fat tails)
        if features["return_kurtosis"] > 3:
            scores["volatile"] += (features["return_kurtosis"] - 3) / 3
        
        # ===== Quiet =====
        # Quiet có ATR thấp
        if features["atr_ratio"] < 1:
            scores["quiet"] += 1 - features["atr_ratio"]
            
        # Ít biến động
        if features["volatility_shift"] < 0.5:
            scores["quiet"] += 1 - features["volatility_shift"]
            
        # Kurtosis thấp
        if features["return_kurtosis"] < 1:
            scores["quiet"] += 1 - features["return_kurtosis"]
        
        # ===== Choppy =====
        # Choppy có Hurst < 0.4 (anti-persistent)
        if features["hurst_exponent"] < 0.4:
            scores["choppy"] += (0.4 - features["hurst_exponent"]) * 10
            
        # Kurtosis thấp
        if features["return_kurtosis"] < 0:
            scores["choppy"] += abs(features["return_kurtosis"])
            
        # Fractal Dimension rất cao trong choppy markets
        if features["fractal_dimension"] > 1.6:
            scores["choppy"] += (features["fractal_dimension"] - 1.6) * 5
        
        return scores
    
    def _calculate_hurst_exponent(self, prices: np.ndarray) -> float:
        """
        Tính Hurst Exponent (chỉ số fractal tự tương quan)
        
        Hurst Exponent là một số đo độ liên tục (persistence) của chuỗi thời gian:
        - H > 0.5: thị trường trending
        - H = 0.5: thị trường random walk
        - H < 0.5: thị trường mean reverting
        
        Args:
            prices (np.ndarray): Mảng giá
            
        Returns:
            float: Hurst Exponent
        """
        # Chuyển đổi giá thành lợi nhuận
        returns = np.diff(np.log(prices))
        
        # Các độ dài tối đa cho R/S Analysis
        max_lag = min(len(returns) // 2, 20)
        lags = range(2, max_lag)
        
        # Vector bắt đầu tính R/S
        tau = []
        # Vector giữ các giá trị R/S
        rs = []
        
        for lag in lags:
            # Phân tích R/S cho mỗi độ trễ
            # Chia chuỗi thành các khối có độ dài lag
            n_blocks = len(returns) // lag
            
            if n_blocks < 1:
                continue
                
            # Tính R/S cho mỗi khối và lấy trung bình
            rs_values = []
            
            for i in range(n_blocks):
                block = returns[i * lag:(i + 1) * lag]
                
                # Kích thước mẫu không đủ
                if len(block) < 2:
                    continue
                    
                # Tính giá trị trung bình của khối
                mean_block = np.mean(block)
                
                # Tính độ lệch chuẩn
                std_block = np.std(block)
                
                if std_block == 0:
                    continue
                
                # Tính chuỗi tích lũy
                cumsum = np.cumsum(block - mean_block)
                
                # Tính Range: max(cumsum) - min(cumsum)
                r = max(cumsum) - min(cumsum)
                
                # Tính R/S
                rs_current = r / std_block
                rs_values.append(rs_current)
            
            if len(rs_values) > 0:
                # Lấy trung bình R/S qua các khối
                rs.append(np.mean(rs_values))
                tau.append(lag)
        
        # Kiểm tra có đủ dữ liệu không
        if len(tau) < 2:
            logger.warning("Không đủ dữ liệu để tính Hurst Exponent")
            return 0.5
            
        # Tính Hurst Exponent từ linear regression
        log_tau = np.log10(tau)
        log_rs = np.log10(rs)
        
        # Thực hiện hồi quy tuyến tính
        slope, _, _, _, _ = stats.linregress(log_tau, log_rs)
        
        # Hurst Exponent là hệ số góc của đường hồi quy
        hurst = slope
        
        # Giới hạn giá trị
        hurst = max(0.1, min(0.9, hurst))
        
        return hurst
    
    def _calculate_fractal_dimension(self, prices: np.ndarray) -> float:
        """
        Tính Fractal Dimension sử dụng phương pháp Higuchi
        
        Args:
            prices (np.ndarray): Mảng giá
            
        Returns:
            float: Fractal Dimension
        """
        # Chuyển đổi giá thành logarithm
        log_prices = np.log(prices)
        
        # Số k max
        kmax = 10
        
        # Vector lưu trữ độ dài cho mỗi k
        length = np.zeros(kmax)
        
        # Tính toán độ dài cho mỗi k
        for k in range(1, kmax + 1):
            # Tính độ dài đường cong cho k
            lk = 0
            
            # Tính toán path length cho điểm bắt đầu khác nhau
            for m in range(1, k + 1):
                # Số phân đoạn
                idx = np.arange(m - 1, len(log_prices) - 1, k)
                idx_shift = np.arange(m, len(log_prices), k)
                
                if len(idx) == 0 or len(idx_shift) == 0:
                    continue
                
                # Tính tổng độ dài đoạn
                segment_lengths = np.abs(log_prices[idx_shift] - log_prices[idx])
                
                # Normalization
                lm = np.sum(segment_lengths) * (len(log_prices) - 1) / (((len(log_prices) - m) // k) * k)
                
                lk += lm
            
            # Trung bình trên m
            lk /= k
            length[k - 1] = lk
        
        # Thực hiện linear regression trên log(length) vs log(1/k)
        x = np.log(1.0 / np.arange(1, kmax + 1))
        y = np.log(length)
        
        # Kiểm tra NaN
        valid_indices = ~np.isnan(y)
        if np.sum(valid_indices) < 2:
            logger.warning("Không đủ dữ liệu hợp lệ để tính Fractal Dimension")
            return 1.5
            
        slope, _, _, _, _ = stats.linregress(x[valid_indices], y[valid_indices])
        
        # Fractal dimension là hệ số góc
        fractal_dim = slope
        
        # Giới hạn giá trị
        fractal_dim = max(1.1, min(1.9, fractal_dim))
        
        return fractal_dim
    
    def _calculate_atr(self, price_data: pd.DataFrame, period: int = 14) -> float:
        """
        Tính Average True Range
        
        Args:
            price_data (pd.DataFrame): Dữ liệu giá
            period (int): Số chu kỳ
            
        Returns:
            float: ATR
        """
        high = price_data['high'].values[-period-1:]
        low = price_data['low'].values[-period-1:]
        close = price_data['close'].values[-period-1:]
        
        # Tính True Range
        tr1 = np.abs(high[1:] - low[1:])
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        
        # True Range là giá trị lớn nhất của 3 độ chênh lệch
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        
        # Tính ATR
        atr = np.mean(tr)
        
        return atr
    
    def _calculate_adx(self, price_data: pd.DataFrame, period: int = 14) -> float:
        """
        Tính Average Directional Index
        
        Args:
            price_data (pd.DataFrame): Dữ liệu giá
            period (int): Số chu kỳ
            
        Returns:
            float: ADX
        """
        # Các mảng cần thiết, với thêm 1 period để tính DM
        high = price_data['high'].values[-(period*2+1):]
        low = price_data['low'].values[-(period*2+1):]
        close = price_data['close'].values[-(period*2+1):]
        
        # Kiểm tra đủ dữ liệu
        if len(high) < period*2:
            return 25.0  # Giá trị mặc định
        
        # Tính +DM và -DM
        up_move = high[1:] - high[:-1]
        down_move = low[:-1] - low[1:]
        
        # Tính +DM
        plus_dm = np.where(
            (up_move > down_move) & (up_move > 0),
            up_move,
            0
        )
        
        # Tính -DM
        minus_dm = np.where(
            (down_move > up_move) & (down_move > 0),
            down_move,
            0
        )
        
        # Tính True Range
        tr1 = np.abs(high[1:] - low[1:])
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        
        # Tính ATR (Average True Range)
        atr = self._calculate_ema(tr, period)
        
        # Tính +DI và -DI
        plus_di = 100 * self._calculate_ema(plus_dm, period) / atr
        minus_di = 100 * self._calculate_ema(minus_dm, period) / atr
        
        # Tính Directional Index
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        
        # Tính ADX
        adx = self._calculate_ema(dx, period)
        
        return float(adx[-1]) if len(adx) > 0 else 25.0
    
    def _calculate_ema(self, data, period):
        """Helper để tính EMA"""
        alpha = 2 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
            
        return ema
    
    def _calculate_volatility_shift(self, price_data: pd.DataFrame) -> float:
        """
        Tính sự thay đổi biến động gần đây so với quá khứ
        
        Args:
            price_data (pd.DataFrame): Dữ liệu giá
            
        Returns:
            float: Tỷ lệ thay đổi biến động
        """
        close = price_data['close'].values[-self.lookback_periods:]
        
        if len(close) < self.lookback_periods:
            return 1.0
        
        # Chuyển đổi giá thành log returns
        log_returns = np.diff(np.log(close))
        
        # Chia thành 2 nửa: gần đây và xa hơn
        recent_vol = np.std(log_returns[len(log_returns)//2:])
        past_vol = np.std(log_returns[:len(log_returns)//2])
        
        # Tính tỷ lệ thay đổi
        if past_vol > 0:
            vol_shift = recent_vol / past_vol
        else:
            vol_shift = 1.0
            
        return vol_shift
    
    def get_regime_statistics(self) -> Dict:
        """
        Lấy thống kê của các chế độ thị trường
        
        Returns:
            Dict: Thống kê về các chế độ thị trường
        """
        if not self.regime_history:
            return {
                "current_regime": "unknown",
                "regime_counts": {},
                "average_confidence": 0.0,
                "regime_duration": {},
                "transition_matrix": {}
            }
            
        # Đếm số lần xuất hiện của mỗi chế độ
        regime_counts = {}
        for regime in self.regimes:
            count = sum(1 for entry in self.regime_history if entry["regime"] == regime)
            regime_counts[regime] = count
            
        # Tính độ tin cậy trung bình
        avg_confidence = sum(entry["confidence"] for entry in self.regime_history) / len(self.regime_history)
        
        # Tính ma trận chuyển đổi
        transition_matrix = {regime: {r: 0 for r in self.regimes} for regime in self.regimes}
        
        for i in range(1, len(self.regime_history)):
            prev_regime = self.regime_history[i-1]["regime"]
            curr_regime = self.regime_history[i]["regime"]
            
            if prev_regime in self.regimes and curr_regime in self.regimes:
                transition_matrix[prev_regime][curr_regime] += 1
                
        # Chuẩn hóa ma trận chuyển đổi
        for regime in self.regimes:
            total = sum(transition_matrix[regime].values())
            if total > 0:
                for r in self.regimes:
                    transition_matrix[regime][r] /= total
        
        # Tính thời lượng trung bình của mỗi chế độ
        regime_duration = {regime: 0 for regime in self.regimes}
        current_regime = None
        current_count = 0
        
        # Biến để đếm tổng số đợt của mỗi chế độ
        regime_episodes = {regime: 0 for regime in self.regimes}
        
        for entry in self.regime_history:
            if entry["regime"] != current_regime:
                if current_regime is not None and current_regime in self.regimes:
                    regime_duration[current_regime] += current_count
                    regime_episodes[current_regime] += 1
                current_regime = entry["regime"]
                current_count = 1
            else:
                current_count += 1
                
        # Thêm đợt cuối cùng
        if current_regime is not None and current_regime in self.regimes:
            regime_duration[current_regime] += current_count
            regime_episodes[current_regime] += 1
            
        # Tính thời lượng trung bình
        for regime in self.regimes:
            if regime_episodes[regime] > 0:
                regime_duration[regime] /= regime_episodes[regime]
                
        return {
            "current_regime": self.current_regime,
            "regime_counts": regime_counts,
            "average_confidence": avg_confidence,
            "regime_duration": regime_duration,
            "transition_matrix": transition_matrix
        }
    
    def get_suitable_strategies(self) -> Dict[str, float]:
        """
        Đề xuất các chiến lược phù hợp với chế độ thị trường hiện tại
        
        Returns:
            Dict[str, float]: Ánh xạ chiến lược -> trọng số
        """
        if self.current_regime == "trending":
            return {
                "ema_cross": 0.5,
                "macd": 0.3,
                "adx": 0.2
            }
        elif self.current_regime == "ranging":
            return {
                "rsi": 0.4,
                "bbands": 0.4,
                "stochastic": 0.2
            }
        elif self.current_regime == "volatile":
            return {
                "bbands": 0.3,
                "atr": 0.4,
                "adx": 0.3
            }
        elif self.current_regime == "quiet":
            return {
                "bbands": 0.5,
                "rsi": 0.3,
                "stochastic": 0.2
            }
        elif self.current_regime == "choppy":
            return {
                "rsi": 0.4,
                "bbands": 0.3,
                "stochastic": 0.3
            }
        else:
            return {
                "rsi": 0.33,
                "macd": 0.33,
                "bbands": 0.34
            }
    
    def get_risk_adjustment(self) -> float:
        """
        Đề xuất điều chỉnh rủi ro dựa trên chế độ thị trường hiện tại
        
        Returns:
            float: Hệ số điều chỉnh rủi ro (0-1)
        """
        if self.current_regime == "trending":
            return 1.0  # 100% mức rủi ro cơ bản
        elif self.current_regime == "ranging":
            return 0.8  # 80% mức rủi ro cơ bản
        elif self.current_regime == "volatile":
            return 0.6  # 60% mức rủi ro cơ bản
        elif self.current_regime == "quiet":
            return 0.9  # 90% mức rủi ro cơ bản
        elif self.current_regime == "choppy":
            return 0.7  # 70% mức rủi ro cơ bản
        else:
            return 0.5  # 50% mức rủi ro cơ bản khi không chắc chắn
            
    def get_position_sizing_adjustment(self) -> Dict:
        """
        Đề xuất điều chỉnh position sizing dựa trên chế độ thị trường
        
        Returns:
            Dict: Các tham số điều chỉnh
        """
        base = self.get_risk_adjustment()
        
        if self.current_regime == "trending":
            return {
                "risk_factor": base,
                "take_profit_ratio": 2.5,  # Tỷ lệ TP/SL cao hơn trong trending
                "use_trailing_stop": True,
                "trailing_activation": 0.7,  # % của TP để kích hoạt trailing
                "breakeven_activation": 0.4,  # % của TP để move SL to breakeven
            }
        elif self.current_regime == "ranging":
            return {
                "risk_factor": base,
                "take_profit_ratio": 1.5,  # Tỷ lệ TP/SL thấp hơn
                "use_trailing_stop": False,
                "trailing_activation": 0.0,
                "breakeven_activation": 0.6,
            }
        elif self.current_regime == "volatile":
            return {
                "risk_factor": base,
                "take_profit_ratio": 3.0,  # Tỷ lệ TP/SL cao hơn do biến động lớn
                "use_trailing_stop": True,
                "trailing_activation": 0.5,  # Kích hoạt sớm hơn
                "breakeven_activation": 0.3,
            }
        elif self.current_regime == "quiet":
            return {
                "risk_factor": base,
                "take_profit_ratio": 2.0,
                "use_trailing_stop": True,
                "trailing_activation": 0.8,  # Kích hoạt muộn hơn trong thị trường yên tĩnh
                "breakeven_activation": 0.5,
            }
        elif self.current_regime == "choppy":
            return {
                "risk_factor": base,
                "take_profit_ratio": 1.2,  # Tỷ lệ TP/SL thấp trong thị trường không xu hướng
                "use_trailing_stop": False,
                "trailing_activation": 0.0,
                "breakeven_activation": 0.7,
            }
        else:
            return {
                "risk_factor": base,
                "take_profit_ratio": 2.0,  # Giá trị mặc định
                "use_trailing_stop": True,
                "trailing_activation": 0.6,
                "breakeven_activation": 0.4,
            }

def test_fractal_market_regime():
    """
    Hàm test cho module FractalMarketRegime
    """
    try:
        import matplotlib.pyplot as plt
        
        # Tạo dữ liệu mẫu
        np.random.seed(42)
        
        # Tạo séries thời gian
        n = 200
        t = np.linspace(0, 10, n)
        
        # Tạo các chế độ thị trường khác nhau
        
        # 1. Trending market (Hurst > 0.5)
        trending_prices = 1000 + np.cumsum(np.random.normal(0.1, 1, n))
        
        # 2. Ranging market (Hurst ~ 0.5)
        ranging_mean = 1000
        ranging_prices = ranging_mean + 100 * np.sin(t/2) + np.random.normal(0, 20, n)
        
        # 3. Volatile market
        volatile_prices = 1000 + np.cumsum(np.random.normal(0, 3, n))
        
        # 4. Quiet market
        quiet_prices = 1000 + np.cumsum(np.random.normal(0, 0.5, n))
        
        # 5. Choppy market (Hurst < 0.5)
        choppy_prices = np.zeros(n)
        choppy_prices[0] = 1000
        for i in range(1, n):
            # Mean-reverting process
            choppy_prices[i] = choppy_prices[i-1] + 0.3 * (1000 - choppy_prices[i-1]) + np.random.normal(0, 10)
        
        # Tạo DataFrame cho mỗi loại thị trường
        def create_ohlc(prices):
            df = pd.DataFrame()
            df['close'] = prices
            df['open'] = df['close'].shift(1)
            df['open'].iloc[0] = df['close'].iloc[0] * 0.99
            
            # Tạo high/low từ open-close
            rng = np.random.RandomState(42)
            high_offset = rng.uniform(0, 0.01, n) * prices
            low_offset = rng.uniform(0, 0.01, n) * prices
            
            df['high'] = df[['open', 'close']].max(axis=1) + high_offset
            df['low'] = df[['open', 'close']].min(axis=1) - low_offset
            
            # Tạo volume
            df['volume'] = rng.uniform(100, 1000, n)
            
            return df
        
        # Tạo dữ liệu OHLCV cho mỗi chế độ
        trending_df = create_ohlc(trending_prices)
        ranging_df = create_ohlc(ranging_prices)
        volatile_df = create_ohlc(volatile_prices)
        quiet_df = create_ohlc(quiet_prices)
        choppy_df = create_ohlc(choppy_prices)
        
        # Khởi tạo bộ phát hiện
        detector = FractalMarketRegimeDetector(lookback_periods=50)
        
        # Phát hiện chế độ thị trường cho mỗi loại
        trending_result = detector.detect_regime(trending_df)
        ranging_result = detector.detect_regime(ranging_df)
        volatile_result = detector.detect_regime(volatile_df)
        quiet_result = detector.detect_regime(quiet_df)
        choppy_result = detector.detect_regime(choppy_df)
        
        # In kết quả
        print("=== Kết quả phát hiện chế độ thị trường ===")
        print(f"Trending market: {trending_result['regime']} (confidence: {trending_result['confidence']:.2f})")
        print(f"Ranging market: {ranging_result['regime']} (confidence: {ranging_result['confidence']:.2f})")
        print(f"Volatile market: {volatile_result['regime']} (confidence: {volatile_result['confidence']:.2f})")
        print(f"Quiet market: {quiet_result['regime']} (confidence: {quiet_result['confidence']:.2f})")
        print(f"Choppy market: {choppy_result['regime']} (confidence: {choppy_result['confidence']:.2f})")
        
        # Hiển thị các đặc trưng được tính toán
        print("\n=== Các đặc trưng quan trọng (Features) ===")
        print(f"Trending Hurst: {trending_result['details']['features']['hurst_exponent']:.2f}, "
              f"ADX: {trending_result['details']['features']['adx']:.2f}")
        print(f"Ranging Hurst: {ranging_result['details']['features']['hurst_exponent']:.2f}, "
              f"ADX: {ranging_result['details']['features']['adx']:.2f}")
        print(f"Volatile ATR Ratio: {volatile_result['details']['features']['atr_ratio']:.2f}, "
              f"Volatility Shift: {volatile_result['details']['features']['volatility_shift']:.2f}")
        print(f"Quiet ATR Ratio: {quiet_result['details']['features']['atr_ratio']:.2f}, "
              f"Volatility Shift: {quiet_result['details']['features']['volatility_shift']:.2f}")
        print(f"Choppy Hurst: {choppy_result['details']['features']['hurst_exponent']:.2f}, "
              f"Fractal Dimension: {choppy_result['details']['features']['fractal_dimension']:.2f}")
        
        # Hiển thị các điều chỉnh
        print("\n=== Điều chỉnh quản lý rủi ro ===")
        print(f"Trending Risk: {detector.get_risk_adjustment():.2f}")
        
        # Reset detector
        detector.current_regime = "ranging"
        print(f"Ranging Risk: {detector.get_risk_adjustment():.2f}")
        
        # Reset detector
        detector.current_regime = "volatile"
        print(f"Volatile Risk: {detector.get_risk_adjustment():.2f}")
        
        # Vẽ biểu đồ
        plt.figure(figsize=(15, 10))
        
        plt.subplot(5, 1, 1)
        plt.plot(trending_prices)
        plt.title(f"Trending Market (Detected: {trending_result['regime']})")
        
        plt.subplot(5, 1, 2)
        plt.plot(ranging_prices)
        plt.title(f"Ranging Market (Detected: {ranging_result['regime']})")
        
        plt.subplot(5, 1, 3)
        plt.plot(volatile_prices)
        plt.title(f"Volatile Market (Detected: {volatile_result['regime']})")
        
        plt.subplot(5, 1, 4)
        plt.plot(quiet_prices)
        plt.title(f"Quiet Market (Detected: {quiet_result['regime']})")
        
        plt.subplot(5, 1, 5)
        plt.plot(choppy_prices)
        plt.title(f"Choppy Market (Detected: {choppy_result['regime']})")
        
        plt.tight_layout()
        plt.savefig('fractal_market_regime_test.png')
        print("\nĐã lưu biểu đồ tại 'fractal_market_regime_test.png'")
        
    except ImportError:
        print("Matplotlib không được cài đặt. Vui lòng cài đặt để hiển thị biểu đồ.")
        # Vẫn in kết quả text
        detector = FractalMarketRegimeDetector(lookback_periods=50)

if __name__ == "__main__":
    test_fractal_market_regime()