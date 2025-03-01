"""
Bộ lọc tín hiệu giao dịch nâng cao để phát hiện và loại bỏ tín hiệu giả

Module này cung cấp bộ lọc tín hiệu thông minh, kết hợp nhiều kỹ thuật phân tích để
xác định tín hiệu giao dịch đáng tin cậy và loại bỏ tín hiệu giả, đặc biệt hiệu quả
trong thị trường biến động.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Union, Optional, Any
from datetime import datetime

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedSignalFilter:
    """
    Bộ lọc tín hiệu nâng cao để xác định và loại bỏ tín hiệu giả.
    Áp dụng nhiều bộ lọc để xác nhận tín hiệu và cải thiện win rate.
    """
    
    def __init__(self, config: Dict = None):
        """
        Khởi tạo bộ lọc tín hiệu nâng cao.
        
        Args:
            config (Dict, optional): Cấu hình bộ lọc
        """
        # Cấu hình mặc định
        default_config = {
            "volume_filter": {
                "enabled": True,
                "min_volume_surge": 1.5,  # Khối lượng tối thiểu phải vượt quá trung bình
                "volume_trend_confirmation": True  # Khối lượng phải phù hợp với xu hướng giá
            },
            "divergence_filter": {
                "enabled": True,
                "indicators": ["rsi", "macd"],  # Các chỉ báo để phát hiện phân kỳ
                "lookback_periods": 10  # Số kỳ để tìm phân kỳ
            },
            "support_resistance_filter": {
                "enabled": True,
                "levels_lookback": 100,  # Số kỳ để xác định các mức S/R
                "breakout_confirmation_periods": 2,  # Số kỳ để xác nhận đột phá
                "distance_threshold": 0.005  # % khoảng cách tối thiểu so với mức S/R
            },
            "trend_filter": {
                "enabled": True,
                "ema_periods": [8, 21, 55],  # Các chu kỳ EMA để xác định xu hướng
                "price_action_confirmation": True  # Yêu cầu xác nhận từ price action
            },
            "volatility_filter": {
                "enabled": True,
                "atr_period": 14,
                "max_volatility_percentile": 80,  # Phần trăm tối đa cho thị trường biến động
                "min_volatility_percentile": 20   # Phần trăm tối thiểu cho thị trường ít biến động
            },
            "liquidity_filter": {
                "enabled": True,
                "min_distance_to_liquidity": 0.5,  # % khoảng cách tối thiểu đến vùng thanh khoản
                "check_liquidity_clusters": True  # Kiểm tra các cụm thanh khoản
            },
            "false_breakout_filter": {
                "enabled": True,
                "min_retracement": 0.3,  # % tối thiểu để xác định false breakout
                "lookback_periods": 5  # Số kỳ để tìm false breakout
            },
            "oscillator_alignment": {
                "enabled": True,
                "oscillators": ["rsi", "stochastic", "cci"],  # Các dao động chỉ báo
                "min_oscillators_aligned": 2  # Số tối thiểu dao động chỉ báo phải đồng thuận
            },
            "market_regime_specific": {
                "trending": {
                    "min_signal_quality": 0.6,  # Chất lượng tín hiệu tối thiểu (0-1) 
                    "required_filters": ["trend_filter", "volume_filter"]  # Các bộ lọc bắt buộc
                },
                "ranging": {
                    "min_signal_quality": 0.8,
                    "required_filters": ["support_resistance_filter", "false_breakout_filter"]
                },
                "volatile": {
                    "min_signal_quality": 0.9,
                    "required_filters": ["volatility_filter", "divergence_filter", "liquidity_filter"]
                }
            }
        }
        
        # Sử dụng cấu hình mặc định nếu không có cấu hình được cung cấp
        self.config = default_config if config is None else config
        
        logger.info("Khởi tạo bộ lọc tín hiệu giao dịch nâng cao")
    
    def apply_filters(self, df: pd.DataFrame, signal: Dict, market_regime: str = "ranging") -> Dict:
        """
        Áp dụng các bộ lọc cho tín hiệu giao dịch.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            signal (Dict): Tín hiệu giao dịch ban đầu
            market_regime (str): Chế độ thị trường hiện tại
            
        Returns:
            Dict: Tín hiệu đã được lọc với các thông tin bổ sung
        """
        if df.empty or not signal:
            logger.warning("Không có dữ liệu hoặc tín hiệu ban đầu")
            return {"signal": "NEUTRAL", "strength": 0, "filtered": True}
        
        # Kiểm tra xem có phải là tín hiệu NEUTRAL không
        if signal.get("signal", "NEUTRAL") == "NEUTRAL":
            return signal
        
        # Kết quả lọc ban đầu
        filtered_signal = signal.copy()
        filtered_signal["filter_results"] = {}
        filtered_signal["filter_summary"] = {}
        
        # Danh sách các bộ lọc đã áp dụng
        applied_filters = []
        
        # Danh sách các bộ lọc đã vượt qua
        passed_filters = []
        
        # Số lượng bộ lọc tối thiểu dựa trên chế độ thị trường
        regime_config = self.config["market_regime_specific"].get(market_regime, self.config["market_regime_specific"]["ranging"])
        min_signal_quality = regime_config["min_signal_quality"]
        required_filters = regime_config["required_filters"]
        
        # 1. Áp dụng bộ lọc khối lượng
        if self.config["volume_filter"]["enabled"]:
            volume_result = self._apply_volume_filter(df, signal)
            filtered_signal["filter_results"]["volume_filter"] = volume_result
            applied_filters.append("volume_filter")
            if volume_result["passed"]:
                passed_filters.append("volume_filter")
        
        # 2. Áp dụng bộ lọc phân kỳ
        if self.config["divergence_filter"]["enabled"]:
            divergence_result = self._apply_divergence_filter(df, signal)
            filtered_signal["filter_results"]["divergence_filter"] = divergence_result
            applied_filters.append("divergence_filter")
            if divergence_result["passed"]:
                passed_filters.append("divergence_filter")
        
        # 3. Áp dụng bộ lọc vùng hỗ trợ/kháng cự
        if self.config["support_resistance_filter"]["enabled"]:
            sr_result = self._apply_support_resistance_filter(df, signal)
            filtered_signal["filter_results"]["support_resistance_filter"] = sr_result
            applied_filters.append("support_resistance_filter")
            if sr_result["passed"]:
                passed_filters.append("support_resistance_filter")
        
        # 4. Áp dụng bộ lọc xu hướng
        if self.config["trend_filter"]["enabled"]:
            trend_result = self._apply_trend_filter(df, signal)
            filtered_signal["filter_results"]["trend_filter"] = trend_result
            applied_filters.append("trend_filter")
            if trend_result["passed"]:
                passed_filters.append("trend_filter")
        
        # 5. Áp dụng bộ lọc biến động
        if self.config["volatility_filter"]["enabled"]:
            volatility_result = self._apply_volatility_filter(df, signal)
            filtered_signal["filter_results"]["volatility_filter"] = volatility_result
            applied_filters.append("volatility_filter")
            if volatility_result["passed"]:
                passed_filters.append("volatility_filter")
        
        # 6. Áp dụng bộ lọc thanh khoản
        if self.config["liquidity_filter"]["enabled"]:
            liquidity_result = self._apply_liquidity_filter(df, signal)
            filtered_signal["filter_results"]["liquidity_filter"] = liquidity_result
            applied_filters.append("liquidity_filter")
            if liquidity_result["passed"]:
                passed_filters.append("liquidity_filter")
        
        # 7. Áp dụng bộ lọc đột phá giả
        if self.config["false_breakout_filter"]["enabled"]:
            false_breakout_result = self._apply_false_breakout_filter(df, signal)
            filtered_signal["filter_results"]["false_breakout_filter"] = false_breakout_result
            applied_filters.append("false_breakout_filter")
            if false_breakout_result["passed"]:
                passed_filters.append("false_breakout_filter")
        
        # 8. Áp dụng bộ lọc đồng thuận dao động chỉ báo
        if self.config["oscillator_alignment"]["enabled"]:
            oscillator_result = self._apply_oscillator_alignment_filter(df, signal)
            filtered_signal["filter_results"]["oscillator_alignment"] = oscillator_result
            applied_filters.append("oscillator_alignment")
            if oscillator_result["passed"]:
                passed_filters.append("oscillator_alignment")
        
        # Tính tỷ lệ vượt qua các bộ lọc
        filter_pass_rate = len(passed_filters) / len(applied_filters) if applied_filters else 0
        
        # Kiểm tra các bộ lọc bắt buộc
        required_filters_passed = all(rf in passed_filters for rf in required_filters)
        
        # Chất lượng tín hiệu dựa trên tỷ lệ vượt qua các bộ lọc
        signal_quality = filter_pass_rate
        
        # Thông tin tóm tắt
        filtered_signal["filter_summary"] = {
            "applied_filters": applied_filters,
            "passed_filters": passed_filters,
            "filter_pass_rate": filter_pass_rate,
            "required_filters_passed": required_filters_passed,
            "signal_quality": signal_quality,
            "min_signal_quality": min_signal_quality
        }
        
        # Quyết định cuối cùng
        if required_filters_passed and signal_quality >= min_signal_quality:
            # Giữ nguyên tín hiệu
            filtered_signal["filtered"] = False
        else:
            # Loại bỏ tín hiệu
            filtered_signal["signal"] = "NEUTRAL"
            filtered_signal["strength"] = 0
            filtered_signal["filtered"] = True
            filtered_signal["reason"] = "Không đạt yêu cầu lọc tín hiệu"
        
        return filtered_signal
    
    def _apply_volume_filter(self, df: pd.DataFrame, signal: Dict) -> Dict:
        """
        Áp dụng bộ lọc khối lượng giao dịch.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            signal (Dict): Tín hiệu giao dịch ban đầu
            
        Returns:
            Dict: Kết quả lọc tín hiệu dựa trên khối lượng
        """
        # Kiểm tra điều kiện
        if 'volume' not in df.columns:
            return {"passed": False, "reason": "Không có dữ liệu khối lượng"}
        
        # Lấy cấu hình
        min_volume_surge = self.config["volume_filter"]["min_volume_surge"]
        volume_trend_confirmation = self.config["volume_filter"]["volume_trend_confirmation"]
        
        # Tính khối lượng trung bình
        avg_volume = df['volume'].rolling(window=20).mean()
        
        # Khối lượng hiện tại
        current_volume = df['volume'].iloc[-1]
        
        # Biến đổi giá
        price_change = df['close'].pct_change().iloc[-1]
        
        # Kiểm tra khối lượng tăng
        volume_surge = current_volume / avg_volume.iloc[-1] if not pd.isna(avg_volume.iloc[-1]) and avg_volume.iloc[-1] > 0 else 0
        volume_condition = volume_surge >= min_volume_surge
        
        # Kiểm tra khối lượng phù hợp với xu hướng giá
        trend_confirmation = True
        if volume_trend_confirmation:
            if signal.get("signal") == "BUY" and price_change > 0:
                # Khi mua, giá tăng và khối lượng tăng là tốt
                trend_confirmation = volume_surge >= min_volume_surge
            elif signal.get("signal") == "SELL" and price_change < 0:
                # Khi bán, giá giảm và khối lượng tăng là tốt
                trend_confirmation = volume_surge >= min_volume_surge
            else:
                trend_confirmation = False
        
        # Kết quả
        passed = volume_condition and trend_confirmation
        
        return {
            "passed": passed,
            "volume_surge": volume_surge,
            "min_volume_surge": min_volume_surge,
            "trend_confirmation": trend_confirmation,
            "reason": "Khối lượng không đủ lớn" if not volume_condition else 
                     "Khối lượng không phù hợp với xu hướng giá" if not trend_confirmation else 
                     "Vượt qua bộ lọc khối lượng"
        }
    
    def _apply_divergence_filter(self, df: pd.DataFrame, signal: Dict) -> Dict:
        """
        Áp dụng bộ lọc phân kỳ (divergence).
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            signal (Dict): Tín hiệu giao dịch ban đầu
            
        Returns:
            Dict: Kết quả lọc tín hiệu dựa trên phân kỳ
        """
        # Lấy cấu hình
        indicators = self.config["divergence_filter"]["indicators"]
        lookback_periods = self.config["divergence_filter"]["lookback_periods"]
        
        # Kiểm tra phân kỳ
        divergences = []
        
        # Phân kỳ RSI
        if "rsi" in indicators and "rsi" in df.columns:
            # Phân kỳ dương (bullish divergence)
            bullish_divergence = self._check_bullish_divergence(df, "rsi", lookback_periods)
            
            # Phân kỳ âm (bearish divergence)
            bearish_divergence = self._check_bearish_divergence(df, "rsi", lookback_periods)
            
            if signal.get("signal") == "BUY" and bullish_divergence:
                divergences.append("RSI bullish divergence")
            elif signal.get("signal") == "SELL" and bearish_divergence:
                divergences.append("RSI bearish divergence")
        
        # Phân kỳ MACD
        if "macd" in indicators and "macd" in df.columns and "macd_signal" in df.columns:
            # Phân kỳ dương (bullish divergence)
            bullish_divergence = self._check_bullish_divergence(df, "macd", lookback_periods)
            
            # Phân kỳ âm (bearish divergence)
            bearish_divergence = self._check_bearish_divergence(df, "macd", lookback_periods)
            
            if signal.get("signal") == "BUY" and bullish_divergence:
                divergences.append("MACD bullish divergence")
            elif signal.get("signal") == "SELL" and bearish_divergence:
                divergences.append("MACD bearish divergence")
        
        # Kết quả
        passed = len(divergences) > 0
        
        return {
            "passed": passed,
            "divergences": divergences,
            "reason": "Không tìm thấy phân kỳ phù hợp" if not passed else "Phát hiện phân kỳ phù hợp"
        }
    
    def _check_bullish_divergence(self, df: pd.DataFrame, indicator: str, lookback_periods: int) -> bool:
        """
        Kiểm tra phân kỳ dương (bullish divergence).
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            indicator (str): Tên chỉ báo
            lookback_periods (int): Số kỳ để tìm phân kỳ
            
        Returns:
            bool: True nếu có phân kỳ dương, False nếu không
        """
        if indicator not in df.columns or len(df) < lookback_periods:
            return False
        
        # Lấy dữ liệu trong khoảng lookback
        data = df.iloc[-lookback_periods:].copy()
        
        # Tìm các đáy giá
        price_lows = []
        for i in range(1, len(data) - 1):
            if data['low'].iloc[i] < data['low'].iloc[i-1] and data['low'].iloc[i] < data['low'].iloc[i+1]:
                price_lows.append((i, data['low'].iloc[i]))
        
        # Tìm các đáy chỉ báo
        indicator_lows = []
        for i in range(1, len(data) - 1):
            if data[indicator].iloc[i] < data[indicator].iloc[i-1] and data[indicator].iloc[i] < data[indicator].iloc[i+1]:
                indicator_lows.append((i, data[indicator].iloc[i]))
        
        # Kiểm tra phân kỳ
        if len(price_lows) >= 2 and len(indicator_lows) >= 2:
            # Hai đáy giá gần nhất
            last_price_low, second_last_price_low = sorted(price_lows, key=lambda x: x[0], reverse=True)[:2]
            
            # Hai đáy chỉ báo gần nhất
            last_indicator_low, second_last_indicator_low = sorted(indicator_lows, key=lambda x: x[0], reverse=True)[:2]
            
            # Kiểm tra phân kỳ: giá làm đáy thấp hơn, chỉ báo làm đáy cao hơn
            if (last_price_low[1] < second_last_price_low[1] and 
                last_indicator_low[1] > second_last_indicator_low[1]):
                return True
        
        return False
    
    def _check_bearish_divergence(self, df: pd.DataFrame, indicator: str, lookback_periods: int) -> bool:
        """
        Kiểm tra phân kỳ âm (bearish divergence).
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            indicator (str): Tên chỉ báo
            lookback_periods (int): Số kỳ để tìm phân kỳ
            
        Returns:
            bool: True nếu có phân kỳ âm, False nếu không
        """
        if indicator not in df.columns or len(df) < lookback_periods:
            return False
        
        # Lấy dữ liệu trong khoảng lookback
        data = df.iloc[-lookback_periods:].copy()
        
        # Tìm các đỉnh giá
        price_highs = []
        for i in range(1, len(data) - 1):
            if data['high'].iloc[i] > data['high'].iloc[i-1] and data['high'].iloc[i] > data['high'].iloc[i+1]:
                price_highs.append((i, data['high'].iloc[i]))
        
        # Tìm các đỉnh chỉ báo
        indicator_highs = []
        for i in range(1, len(data) - 1):
            if data[indicator].iloc[i] > data[indicator].iloc[i-1] and data[indicator].iloc[i] > data[indicator].iloc[i+1]:
                indicator_highs.append((i, data[indicator].iloc[i]))
        
        # Kiểm tra phân kỳ
        if len(price_highs) >= 2 and len(indicator_highs) >= 2:
            # Hai đỉnh giá gần nhất
            last_price_high, second_last_price_high = sorted(price_highs, key=lambda x: x[0], reverse=True)[:2]
            
            # Hai đỉnh chỉ báo gần nhất
            last_indicator_high, second_last_indicator_high = sorted(indicator_highs, key=lambda x: x[0], reverse=True)[:2]
            
            # Kiểm tra phân kỳ: giá làm đỉnh cao hơn, chỉ báo làm đỉnh thấp hơn
            if (last_price_high[1] > second_last_price_high[1] and 
                last_indicator_high[1] < second_last_indicator_high[1]):
                return True
        
        return False
    
    def _apply_support_resistance_filter(self, df: pd.DataFrame, signal: Dict) -> Dict:
        """
        Áp dụng bộ lọc vùng hỗ trợ/kháng cự.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            signal (Dict): Tín hiệu giao dịch ban đầu
            
        Returns:
            Dict: Kết quả lọc tín hiệu dựa trên vùng hỗ trợ/kháng cự
        """
        # Lấy cấu hình
        levels_lookback = self.config["support_resistance_filter"]["levels_lookback"]
        breakout_confirmation_periods = self.config["support_resistance_filter"]["breakout_confirmation_periods"]
        distance_threshold = self.config["support_resistance_filter"]["distance_threshold"]
        
        # Kiểm tra dữ liệu
        if len(df) < levels_lookback:
            return {"passed": False, "reason": "Không đủ dữ liệu để xác định vùng hỗ trợ/kháng cự"}
        
        # Tính toán các mức hỗ trợ/kháng cự
        data = df.iloc[-levels_lookback:].copy()
        
        # Tìm các đỉnh (peaks)
        peaks = []
        for i in range(2, len(data) - 2):
            if (data['high'].iloc[i] > data['high'].iloc[i-1] and 
                data['high'].iloc[i] > data['high'].iloc[i-2] and
                data['high'].iloc[i] > data['high'].iloc[i+1] and
                data['high'].iloc[i] > data['high'].iloc[i+2]):
                peaks.append(data['high'].iloc[i])
        
        # Tìm các đáy (troughs)
        troughs = []
        for i in range(2, len(data) - 2):
            if (data['low'].iloc[i] < data['low'].iloc[i-1] and 
                data['low'].iloc[i] < data['low'].iloc[i-2] and
                data['low'].iloc[i] < data['low'].iloc[i+1] and
                data['low'].iloc[i] < data['low'].iloc[i+2]):
                troughs.append(data['low'].iloc[i])
        
        # Gom nhóm các mức giá gần nhau
        def cluster_levels(levels, threshold=0.01):
            if not levels:
                return []
            
            clusters = []
            current_cluster = [levels[0]]
            
            for level in levels[1:]:
                # So sánh với giá trị trung bình của cụm hiện tại
                avg_cluster = sum(current_cluster) / len(current_cluster)
                
                if abs(level - avg_cluster) / avg_cluster < threshold:
                    # Thêm vào cụm hiện tại
                    current_cluster.append(level)
                else:
                    # Tạo cụm mới
                    clusters.append(sum(current_cluster) / len(current_cluster))
                    current_cluster = [level]
            
            # Thêm cụm cuối cùng
            clusters.append(sum(current_cluster) / len(current_cluster))
            
            return clusters
        
        # Gom nhóm các mức
        resistance_levels = cluster_levels(peaks)
        support_levels = cluster_levels(troughs)
        
        # Giá hiện tại
        current_price = df['close'].iloc[-1]
        
        # Tìm mức hỗ trợ/kháng cự gần nhất
        nearest_resistance = min(resistance_levels, key=lambda x: abs(x - current_price)) if resistance_levels else None
        nearest_support = min(support_levels, key=lambda x: abs(x - current_price)) if support_levels else None
        
        # Tính khoảng cách tương đối
        resistance_distance = (nearest_resistance - current_price) / current_price if nearest_resistance else 1
        support_distance = (current_price - nearest_support) / current_price if nearest_support else 1
        
        # Kiểm tra breakout
        confirmed_breakout = False
        
        if signal.get("signal") == "BUY":
            # Kiểm tra breakout kháng cự cho tín hiệu mua
            if nearest_resistance and resistance_distance < distance_threshold and resistance_distance > 0:
                # Kiểm tra xem giá đã vượt qua mức kháng cự trong vài kỳ gần đây
                breakout_confirmed = 0
                for i in range(1, min(breakout_confirmation_periods + 1, len(df))):
                    if df['close'].iloc[-i] > nearest_resistance:
                        breakout_confirmed += 1
                
                confirmed_breakout = breakout_confirmed >= breakout_confirmation_periods
        
        elif signal.get("signal") == "SELL":
            # Kiểm tra breakdown hỗ trợ cho tín hiệu bán
            if nearest_support and support_distance < distance_threshold and support_distance > 0:
                # Kiểm tra xem giá đã phá vỡ mức hỗ trợ trong vài kỳ gần đây
                breakout_confirmed = 0
                for i in range(1, min(breakout_confirmation_periods + 1, len(df))):
                    if df['close'].iloc[-i] < nearest_support:
                        breakout_confirmed += 1
                
                confirmed_breakout = breakout_confirmed >= breakout_confirmation_periods
        
        # Kiểm tra vùng hỗ trợ/kháng cự
        sr_condition = False
        
        if signal.get("signal") == "BUY":
            # Cho tín hiệu mua: giá gần mức hỗ trợ hoặc đã vượt qua mức kháng cự
            sr_condition = (nearest_support and support_distance < distance_threshold) or confirmed_breakout
        
        elif signal.get("signal") == "SELL":
            # Cho tín hiệu bán: giá gần mức kháng cự hoặc đã phá vỡ mức hỗ trợ
            sr_condition = (nearest_resistance and resistance_distance < distance_threshold) or confirmed_breakout
        
        # Kết quả
        passed = sr_condition
        
        return {
            "passed": passed,
            "resistance_levels": resistance_levels,
            "support_levels": support_levels,
            "nearest_resistance": nearest_resistance,
            "nearest_support": nearest_support,
            "confirmed_breakout": confirmed_breakout,
            "reason": "Không thỏa mãn điều kiện hỗ trợ/kháng cự" if not passed else "Thỏa mãn điều kiện hỗ trợ/kháng cự"
        }
    
    def _apply_trend_filter(self, df: pd.DataFrame, signal: Dict) -> Dict:
        """
        Áp dụng bộ lọc xu hướng.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            signal (Dict): Tín hiệu giao dịch ban đầu
            
        Returns:
            Dict: Kết quả lọc tín hiệu dựa trên xu hướng
        """
        # Lấy cấu hình
        ema_periods = self.config["trend_filter"]["ema_periods"]
        price_action_confirmation = self.config["trend_filter"]["price_action_confirmation"]
        
        # Tính toán các EMA nếu chưa có
        for period in ema_periods:
            col_name = f'ema_{period}'
            if col_name not in df.columns:
                df[col_name] = df['close'].ewm(span=period, adjust=False).mean()
        
        # Xác định xu hướng dựa trên EMA
        short_ema = df[f'ema_{ema_periods[0]}'].iloc[-1]
        medium_ema = df[f'ema_{ema_periods[1]}'].iloc[-1]
        long_ema = df[f'ema_{ema_periods[2]}'].iloc[-1]
        
        uptrend = short_ema > medium_ema > long_ema
        downtrend = short_ema < medium_ema < long_ema
        
        # Xác định xu hướng dựa trên price action
        price_action_uptrend = False
        price_action_downtrend = False
        
        if price_action_confirmation:
            # Kiểm tra 10 kỳ gần nhất
            highs = df['high'].iloc[-10:].values
            lows = df['low'].iloc[-10:].values
            
            # Kiểm tra higher highs và higher lows cho uptrend
            higher_highs = all(highs[i] >= highs[i-1] for i in range(1, len(highs), 2))
            higher_lows = all(lows[i] >= lows[i-1] for i in range(1, len(lows), 2))
            price_action_uptrend = higher_highs and higher_lows
            
            # Kiểm tra lower highs và lower lows cho downtrend
            lower_highs = all(highs[i] <= highs[i-1] for i in range(1, len(highs), 2))
            lower_lows = all(lows[i] <= lows[i-1] for i in range(1, len(lows), 2))
            price_action_downtrend = lower_highs and lower_lows
        
        # Kết hợp xu hướng EMA và price action
        if price_action_confirmation:
            final_uptrend = uptrend and price_action_uptrend
            final_downtrend = downtrend and price_action_downtrend
        else:
            final_uptrend = uptrend
            final_downtrend = downtrend
        
        # Kiểm tra tín hiệu phù hợp với xu hướng
        trend_condition = False
        
        if signal.get("signal") == "BUY" and final_uptrend:
            trend_condition = True
        elif signal.get("signal") == "SELL" and final_downtrend:
            trend_condition = True
        
        # Kết quả
        passed = trend_condition
        
        return {
            "passed": passed,
            "uptrend": final_uptrend,
            "downtrend": final_downtrend,
            "price_action_uptrend": price_action_uptrend if price_action_confirmation else None,
            "price_action_downtrend": price_action_downtrend if price_action_confirmation else None,
            "reason": "Tín hiệu không phù hợp với xu hướng" if not passed else "Tín hiệu phù hợp với xu hướng"
        }
    
    def _apply_volatility_filter(self, df: pd.DataFrame, signal: Dict) -> Dict:
        """
        Áp dụng bộ lọc biến động.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            signal (Dict): Tín hiệu giao dịch ban đầu
            
        Returns:
            Dict: Kết quả lọc tín hiệu dựa trên biến động
        """
        # Lấy cấu hình
        atr_period = self.config["volatility_filter"]["atr_period"]
        max_volatility_percentile = self.config["volatility_filter"]["max_volatility_percentile"]
        min_volatility_percentile = self.config["volatility_filter"]["min_volatility_percentile"]
        
        # Tính ATR nếu chưa có
        if 'atr' not in df.columns:
            tr1 = df['high'] - df['low']
            tr2 = (df['high'] - df['close'].shift()).abs()
            tr3 = (df['low'] - df['close'].shift()).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            df['atr'] = tr.rolling(window=atr_period).mean()
        
        # Tính phần trăm ATR so với giá
        current_price = df['close'].iloc[-1]
        current_atr = df['atr'].iloc[-1]
        atr_percentage = (current_atr / current_price) * 100
        
        # Tính phân vị ATR trong lịch sử
        all_atr_percentages = (df['atr'] / df['close']) * 100
        volatility_percentile = pd.Series(all_atr_percentages).rank(pct=True).iloc[-1] * 100
        
        # Kiểm tra điều kiện biến động
        too_volatile = volatility_percentile > max_volatility_percentile
        too_calm = volatility_percentile < min_volatility_percentile
        
        # Điều kiện lọc
        volatility_condition = not too_volatile
        
        # Đối với thị trường quá trầm lắng, chỉ tín hiệu mạnh mới được chấp nhận
        if too_calm and signal.get("strength", 0) < 0.8:
            volatility_condition = False
        
        # Kết quả
        passed = volatility_condition
        
        return {
            "passed": passed,
            "atr_percentage": atr_percentage,
            "volatility_percentile": volatility_percentile,
            "too_volatile": too_volatile,
            "too_calm": too_calm,
            "reason": "Biến động quá cao" if too_volatile else 
                     "Biến động quá thấp và tín hiệu không đủ mạnh" if too_calm and signal.get("strength", 0) < 0.8 else
                     "Biến động phù hợp"
        }
    
    def _apply_liquidity_filter(self, df: pd.DataFrame, signal: Dict) -> Dict:
        """
        Áp dụng bộ lọc thanh khoản.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            signal (Dict): Tín hiệu giao dịch ban đầu
            
        Returns:
            Dict: Kết quả lọc tín hiệu dựa trên thanh khoản
        """
        # Lấy cấu hình
        min_distance_to_liquidity = self.config["liquidity_filter"]["min_distance_to_liquidity"]
        check_liquidity_clusters = self.config["liquidity_filter"]["check_liquidity_clusters"]
        
        # Đơn giản hóa: sử dụng biến volume như là proxy cho liquidity
        if 'volume' not in df.columns:
            return {"passed": False, "reason": "Không có dữ liệu khối lượng"}
        
        # Tìm các cụm khối lượng cao
        high_volume_threshold = df['volume'].quantile(0.8)
        high_volume_bars = df[df['volume'] > high_volume_threshold]
        
        if high_volume_bars.empty:
            return {"passed": True, "reason": "Không tìm thấy vùng thanh khoản đặc biệt"}
        
        # Xác định các vùng giá có thanh khoản cao
        high_liquidity_zones = []
        
        if check_liquidity_clusters:
            # Tính histogram của giá với khối lượng cao
            price_bins = pd.cut(high_volume_bars['close'], bins=10)
            liquidity_zones = high_volume_bars.groupby(price_bins)['volume'].sum()
            
            # Tìm các vùng giá có thanh khoản cao nhất
            top_zones = liquidity_zones.nlargest(3)
            
            for zone_idx in top_zones.index:
                high_liquidity_zones.append((zone_idx.left, zone_idx.right))
        else:
            # Sử dụng các mức giá từ các thanh khối lượng cao gần đây
            recent_high_volume = high_volume_bars.iloc[-10:]
            for _, row in recent_high_volume.iterrows():
                high_liquidity_zones.append((row['low'], row['high']))
        
        # Giá hiện tại
        current_price = df['close'].iloc[-1]
        
        # Tính khoảng cách đến vùng thanh khoản gần nhất
        min_distance = float('inf')
        nearest_zone = None
        
        for zone in high_liquidity_zones:
            if zone[0] <= current_price <= zone[1]:
                # Giá nằm trong vùng thanh khoản
                min_distance = 0
                nearest_zone = zone
                break
            else:
                # Tính khoảng cách đến vùng thanh khoản
                distance_to_zone = min(abs(current_price - zone[0]) / current_price,
                                     abs(current_price - zone[1]) / current_price)
                if distance_to_zone < min_distance:
                    min_distance = distance_to_zone
                    nearest_zone = zone
        
        # Điều kiện lọc dựa trên khoảng cách đến vùng thanh khoản
        liquidity_condition = True
        
        # Nếu giá nằm trong vùng thanh khoản cao, kiểm tra hướng
        if min_distance == 0:
            # Trong vùng thanh khoản, cần xem xét kỹ hơn
            if signal.get("signal") == "BUY" and current_price > (nearest_zone[0] + nearest_zone[1]) / 2:
                # Mua khi giá trên nửa trên của vùng thanh khoản (có thể đang break out)
                liquidity_condition = True
            elif signal.get("signal") == "SELL" and current_price < (nearest_zone[0] + nearest_zone[1]) / 2:
                # Bán khi giá dưới nửa dưới của vùng thanh khoản (có thể đang break down)
                liquidity_condition = True
            else:
                # Giá đang đi vào vùng thanh khoản - có thể bị kẹt
                liquidity_condition = False
        else:
            # Không trong vùng thanh khoản, cần đủ xa
            liquidity_condition = min_distance >= min_distance_to_liquidity
        
        # Kết quả
        passed = liquidity_condition
        
        return {
            "passed": passed,
            "min_distance": min_distance,
            "min_distance_threshold": min_distance_to_liquidity,
            "in_liquidity_zone": min_distance == 0,
            "reason": "Quá gần vùng thanh khoản" if not passed and min_distance < min_distance_to_liquidity else
                     "Trong vùng thanh khoản không thuận lợi" if not passed and min_distance == 0 else
                     "Khoảng cách đến vùng thanh khoản phù hợp"
        }
    
    def _apply_false_breakout_filter(self, df: pd.DataFrame, signal: Dict) -> Dict:
        """
        Áp dụng bộ lọc đột phá giả.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            signal (Dict): Tín hiệu giao dịch ban đầu
            
        Returns:
            Dict: Kết quả lọc tín hiệu dựa trên đột phá giả
        """
        # Lấy cấu hình
        min_retracement = self.config["false_breakout_filter"]["min_retracement"]
        lookback_periods = self.config["false_breakout_filter"]["lookback_periods"]
        
        # Kiểm tra dữ liệu
        if len(df) < lookback_periods + 5:
            return {"passed": False, "reason": "Không đủ dữ liệu để kiểm tra đột phá giả"}
        
        # Dữ liệu gần đây
        recent_data = df.iloc[-(lookback_periods + 5):].copy()
        
        # Kiểm tra false breakout khi BUY
        false_breakout_buy = False
        false_breakout_sell = False
        
        if signal.get("signal") == "BUY":
            # Tìm các kháng cự gần đây
            resistance_levels = []
            
            for i in range(2, len(recent_data) - 2):
                if (recent_data['high'].iloc[i] > recent_data['high'].iloc[i-1] and 
                    recent_data['high'].iloc[i] > recent_data['high'].iloc[i-2] and
                    recent_data['high'].iloc[i] > recent_data['high'].iloc[i+1] and
                    recent_data['high'].iloc[i] > recent_data['high'].iloc[i+2]):
                    resistance_levels.append((i, recent_data['high'].iloc[i]))
            
            # Kiểm tra false breakout
            if resistance_levels:
                for level_idx, level_price in resistance_levels:
                    # Tìm các nến sau mức kháng cự
                    after_level = recent_data.iloc[level_idx+1:].copy()
                    
                    # Tìm nến vượt lên trên mức kháng cự
                    breakout_idx = None
                    for j in range(len(after_level)):
                        if after_level['close'].iloc[j] > level_price:
                            breakout_idx = j
                            break
                    
                    # Nếu có breakout, kiểm tra retracement
                    if breakout_idx is not None and breakout_idx + 1 < len(after_level):
                        # Giá cao nhất sau breakout
                        high_after_breakout = after_level['high'].iloc[breakout_idx]
                        
                        # Tìm mức giảm sâu nhất sau đó
                        lowest_after_breakout = after_level['low'].iloc[breakout_idx+1:].min()
                        
                        # Tính retracement
                        retracement = (high_after_breakout - lowest_after_breakout) / (high_after_breakout - level_price)
                        
                        # Nếu retracement > 50%, đây là false breakout
                        if retracement > min_retracement:
                            false_breakout_buy = True
                            break
        
        elif signal.get("signal") == "SELL":
            # Tìm các hỗ trợ gần đây
            support_levels = []
            
            for i in range(2, len(recent_data) - 2):
                if (recent_data['low'].iloc[i] < recent_data['low'].iloc[i-1] and 
                    recent_data['low'].iloc[i] < recent_data['low'].iloc[i-2] and
                    recent_data['low'].iloc[i] < recent_data['low'].iloc[i+1] and
                    recent_data['low'].iloc[i] < recent_data['low'].iloc[i+2]):
                    support_levels.append((i, recent_data['low'].iloc[i]))
            
            # Kiểm tra false breakdown
            if support_levels:
                for level_idx, level_price in support_levels:
                    # Tìm các nến sau mức hỗ trợ
                    after_level = recent_data.iloc[level_idx+1:].copy()
                    
                    # Tìm nến phá xuống dưới mức hỗ trợ
                    breakdown_idx = None
                    for j in range(len(after_level)):
                        if after_level['close'].iloc[j] < level_price:
                            breakdown_idx = j
                            break
                    
                    # Nếu có breakdown, kiểm tra retracement
                    if breakdown_idx is not None and breakdown_idx + 1 < len(after_level):
                        # Giá thấp nhất sau breakdown
                        low_after_breakdown = after_level['low'].iloc[breakdown_idx]
                        
                        # Tìm mức tăng cao nhất sau đó
                        highest_after_breakdown = after_level['high'].iloc[breakdown_idx+1:].max()
                        
                        # Tính retracement
                        retracement = (highest_after_breakdown - low_after_breakdown) / (level_price - low_after_breakdown)
                        
                        # Nếu retracement > 50%, đây là false breakdown
                        if retracement > min_retracement:
                            false_breakout_sell = True
                            break
        
        # Kết quả - vượt qua nếu không phát hiện false breakout
        passed = not ((signal.get("signal") == "BUY" and false_breakout_buy) or 
                      (signal.get("signal") == "SELL" and false_breakout_sell))
        
        return {
            "passed": passed,
            "false_breakout_detected": false_breakout_buy or false_breakout_sell,
            "reason": "Phát hiện đột phá giả gần đây" if not passed else "Không phát hiện đột phá giả"
        }
    
    def _apply_oscillator_alignment_filter(self, df: pd.DataFrame, signal: Dict) -> Dict:
        """
        Áp dụng bộ lọc đồng thuận dao động chỉ báo.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            signal (Dict): Tín hiệu giao dịch ban đầu
            
        Returns:
            Dict: Kết quả lọc tín hiệu dựa trên đồng thuận dao động chỉ báo
        """
        # Lấy cấu hình
        oscillators = self.config["oscillator_alignment"]["oscillators"]
        min_oscillators_aligned = self.config["oscillator_alignment"]["min_oscillators_aligned"]
        
        # Kiểm tra các dao động chỉ báo có sẵn
        available_oscillators = []
        
        # Kiểm tra RSI
        if "rsi" in oscillators and "rsi" in df.columns:
            available_oscillators.append("rsi")
        
        # Kiểm tra stochastic
        stoch_available = all(col in df.columns for col in ["stoch_k", "stoch_d"])
        if "stochastic" in oscillators and stoch_available:
            available_oscillators.append("stochastic")
        elif "stochastic" in oscillators:
            # Tính stochastic nếu chưa có
            stoch_k_period = 14
            stoch_d_period = 3
            
            # %K = (Current Close - Lowest Low)/(Highest High - Lowest Low) * 100
            lowest_low = df['low'].rolling(window=stoch_k_period).min()
            highest_high = df['high'].rolling(window=stoch_k_period).max()
            
            df['stoch_k'] = 100 * ((df['close'] - lowest_low) / (highest_high - lowest_low))
            # %D = 3-day SMA of %K
            df['stoch_d'] = df['stoch_k'].rolling(window=stoch_d_period).mean()
            
            available_oscillators.append("stochastic")
        
        # Kiểm tra CCI
        if "cci" in oscillators and "cci" in df.columns:
            available_oscillators.append("cci")
        elif "cci" in oscillators:
            # Tính CCI nếu chưa có
            cci_period = 20
            TP = (df['high'] + df['low'] + df['close']) / 3
            ma_tp = TP.rolling(window=cci_period).mean()
            mean_deviation = abs(TP - ma_tp).rolling(window=cci_period).mean()
            
            df['cci'] = (TP - ma_tp) / (0.015 * mean_deviation)
            
            available_oscillators.append("cci")
        
        # Không đủ dao động chỉ báo
        if len(available_oscillators) < min_oscillators_aligned:
            return {"passed": False, "reason": f"Không đủ dao động chỉ báo (cần {min_oscillators_aligned}, có {len(available_oscillators)})"}
        
        # Đếm số dao động chỉ báo đồng thuận
        aligned_oscillators = 0
        oscillator_signals = {}
        
        # Kiểm tra tín hiệu từ RSI
        if "rsi" in available_oscillators:
            rsi = df['rsi'].iloc[-1]
            
            if signal.get("signal") == "BUY" and rsi < 50:
                aligned_oscillators += 1
                oscillator_signals["rsi"] = "BUY"
            elif signal.get("signal") == "SELL" and rsi > 50:
                aligned_oscillators += 1
                oscillator_signals["rsi"] = "SELL"
            else:
                oscillator_signals["rsi"] = "NEUTRAL"
        
        # Kiểm tra tín hiệu từ Stochastic
        if "stochastic" in available_oscillators:
            stoch_k = df['stoch_k'].iloc[-1]
            stoch_d = df['stoch_d'].iloc[-1]
            
            if signal.get("signal") == "BUY" and stoch_k < 50 and stoch_k > stoch_d:
                aligned_oscillators += 1
                oscillator_signals["stochastic"] = "BUY"
            elif signal.get("signal") == "SELL" and stoch_k > 50 and stoch_k < stoch_d:
                aligned_oscillators += 1
                oscillator_signals["stochastic"] = "SELL"
            else:
                oscillator_signals["stochastic"] = "NEUTRAL"
        
        # Kiểm tra tín hiệu từ CCI
        if "cci" in available_oscillators:
            cci = df['cci'].iloc[-1]
            
            if signal.get("signal") == "BUY" and cci < 0:
                aligned_oscillators += 1
                oscillator_signals["cci"] = "BUY"
            elif signal.get("signal") == "SELL" and cci > 0:
                aligned_oscillators += 1
                oscillator_signals["cci"] = "SELL"
            else:
                oscillator_signals["cci"] = "NEUTRAL"
        
        # Kết quả
        passed = aligned_oscillators >= min_oscillators_aligned
        
        return {
            "passed": passed,
            "aligned_oscillators": aligned_oscillators,
            "min_required": min_oscillators_aligned,
            "oscillator_signals": oscillator_signals,
            "reason": f"Không đủ dao động chỉ báo đồng thuận (cần {min_oscillators_aligned}, có {aligned_oscillators})" if not passed else "Đủ dao động chỉ báo đồng thuận"
        }

# Hàm test
def test_filter(data_file="test_data/BTCUSDT_1h.csv"):
    """
    Kiểm tra bộ lọc tín hiệu nâng cao với dữ liệu lịch sử.
    
    Args:
        data_file (str): Đường dẫn đến file CSV chứa dữ liệu OHLCV
    """
    import pandas as pd
    import matplotlib.pyplot as plt
    from datetime import datetime
    
    # Tải dữ liệu
    try:
        df = pd.read_csv(data_file)
        df['datetime'] = pd.to_datetime(df['timestamp'])
        df.set_index('datetime', inplace=True)
    except Exception as e:
        print(f"Lỗi khi tải dữ liệu: {e}")
        return
    
    # Tính các chỉ báo
    # RSI
    rsi_period = 14
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=rsi_period).mean()
    avg_loss = loss.rolling(window=rsi_period).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    fast_period, slow_period, signal_period = 12, 26, 9
    ema_fast = df['close'].ewm(span=fast_period, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow_period, adjust=False).mean()
    df['macd'] = ema_fast - ema_slow
    df['macd_signal'] = df['macd'].ewm(span=signal_period, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # Bollinger Bands
    bb_period, std_dev = 20, 2.0
    df['bb_middle'] = df['close'].rolling(window=bb_period).mean()
    df['bb_std'] = df['close'].rolling(window=bb_period).std()
    df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * std_dev)
    df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * std_dev)
    
    # EMA
    for period in [8, 21, 55]:
        df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
    
    # Stochastic
    stoch_k_period, stoch_d_period = 14, 3
    lowest_low = df['low'].rolling(window=stoch_k_period).min()
    highest_high = df['high'].rolling(window=stoch_k_period).max()
    df['stoch_k'] = 100 * ((df['close'] - lowest_low) / (highest_high - lowest_low))
    df['stoch_d'] = df['stoch_k'].rolling(window=stoch_d_period).mean()
    
    # CCI
    cci_period = 20
    tp = (df['high'] + df['low'] + df['close']) / 3
    ma_tp = tp.rolling(window=cci_period).mean()
    mean_dev = abs(tp - ma_tp).rolling(window=cci_period).mean()
    df['cci'] = (tp - ma_tp) / (0.015 * mean_dev)
    
    # ATR
    atr_period = 14
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift()).abs()
    tr3 = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=atr_period).mean()
    
    # Khởi tạo bộ lọc
    signal_filter = EnhancedSignalFilter()
    
    # Tạo tín hiệu mẫu dựa trên các quy tắc đơn giản
    signals = []
    
    for i in range(100, len(df)):
        # Window data
        window = df.iloc[i-100:i+1]
        
        # Tín hiệu đơn giản dựa trên RSI
        rsi = window['rsi'].iloc[-1]
        macd = window['macd'].iloc[-1]
        macd_signal = window['macd_signal'].iloc[-1]
        
        signal = "NEUTRAL"
        strength = 0
        
        if rsi < 30 and macd > macd_signal:
            signal = "BUY"
            strength = 0.7
        elif rsi > 70 and macd < macd_signal:
            signal = "SELL"
            strength = 0.7
        
        # Phát hiện chế độ thị trường
        # Đơn giản hóa:
        adx = window['cci'].abs().mean()  # Sử dụng CCI thay cho ADX
        if adx > 100:
            regime = "trending"
        elif window['atr'].iloc[-1] / window['close'].iloc[-1] > 0.015:
            regime = "volatile"
        else:
            regime = "ranging"
        
        # Áp dụng bộ lọc nếu có tín hiệu
        filtered_signal = None
        if signal != "NEUTRAL":
            # Tạo tín hiệu ban đầu
            original_signal = {
                "signal": signal,
                "strength": strength,
                "timestamp": window.index[-1].strftime("%Y-%m-%d %H:%M:%S"),
                "price": window['close'].iloc[-1]
            }
            
            # Áp dụng bộ lọc
            filtered_signal = signal_filter.apply_filters(window, original_signal, regime)
        
        signals.append({
            "timestamp": window.index[-1],
            "original_signal": signal,
            "filtered_signal": filtered_signal['signal'] if filtered_signal else "NEUTRAL",
            "price": window['close'].iloc[-1],
            "regime": regime,
            "filtered": filtered_signal['filtered'] if filtered_signal else False,
            "filter_summary": filtered_signal['filter_summary'] if filtered_signal else None
        })
    
    # Tính số lượng tín hiệu bị lọc ra
    original_buy_signals = [s for s in signals if s['original_signal'] == "BUY"]
    original_sell_signals = [s for s in signals if s['original_signal'] == "SELL"]
    
    filtered_buy_signals = [s for s in signals if s['filtered_signal'] == "BUY"]
    filtered_sell_signals = [s for s in signals if s['filtered_signal'] == "SELL"]
    
    print(f"Tín hiệu ban đầu: {len(original_buy_signals)} mua, {len(original_sell_signals)} bán")
    print(f"Tín hiệu sau khi lọc: {len(filtered_buy_signals)} mua, {len(filtered_sell_signals)} bán")
    print(f"Tỷ lệ loại bỏ: {(len(original_buy_signals) + len(original_sell_signals) - len(filtered_buy_signals) - len(filtered_sell_signals)) / (len(original_buy_signals) + len(original_sell_signals)) * 100:.2f}%")
    
    # Vẽ biểu đồ
    plt.figure(figsize=(14, 10))
    
    # Vẽ giá
    plt.subplot(3, 1, 1)
    plt.plot(df.index[100:], df['close'].iloc[100:], label='Price')
    
    # Vẽ các tín hiệu ban đầu
    original_buy_x = [s["timestamp"] for s in signals if s["original_signal"] == "BUY"]
    original_buy_y = [s["price"] for s in signals if s["original_signal"] == "BUY"]
    
    original_sell_x = [s["timestamp"] for s in signals if s["original_signal"] == "SELL"]
    original_sell_y = [s["price"] for s in signals if s["original_signal"] == "SELL"]
    
    plt.scatter(original_buy_x, original_buy_y, color='green', marker='^', alpha=0.4, s=80, label='Original BUY')
    plt.scatter(original_sell_x, original_sell_y, color='red', marker='v', alpha=0.4, s=80, label='Original SELL')
    
    # Vẽ các tín hiệu đã lọc
    filtered_buy_x = [s["timestamp"] for s in signals if s["filtered_signal"] == "BUY"]
    filtered_buy_y = [s["price"] for s in signals if s["filtered_signal"] == "BUY"]
    
    filtered_sell_x = [s["timestamp"] for s in signals if s["filtered_signal"] == "SELL"]
    filtered_sell_y = [s["price"] for s in signals if s["filtered_signal"] == "SELL"]
    
    plt.scatter(filtered_buy_x, filtered_buy_y, color='green', marker='^', alpha=1.0, s=120, edgecolors='black', label='Filtered BUY')
    plt.scatter(filtered_sell_x, filtered_sell_y, color='red', marker='v', alpha=1.0, s=120, edgecolors='black', label='Filtered SELL')
    
    plt.title('Bitcoin Price and Trading Signals (Enhanced Signal Filter)')
    plt.ylabel('Price (USD)')
    plt.grid(True)
    plt.legend()
    
    # Vẽ chế độ thị trường
    plt.subplot(3, 1, 2)
    
    regimes = [s["regime"] for s in signals]
    regime_values = [1 if r == "trending" else 0.5 if r == "ranging" else 0 for r in regimes]
    
    plt.plot(df.index[100:], regime_values, color='blue', label='Market Regime')
    plt.yticks([0, 0.5, 1], ['Volatile', 'Ranging', 'Trending'])
    plt.title('Market Regime Detection')
    plt.grid(True)
    
    # Vẽ tỷ lệ lọc tín hiệu
    plt.subplot(3, 1, 3)
    
    # Tạo dữ liệu tỷ lệ vượt qua các bộ lọc
    filter_rates = []
    timestamps = []
    
    for s in signals:
        if s['filter_summary']:
            filter_rate = s['filter_summary'].get('filter_pass_rate', 0)
            filter_rates.append(filter_rate)
            timestamps.append(s['timestamp'])
    
    if filter_rates:
        plt.plot(timestamps, filter_rates, 'o-', color='purple', label='Filter Pass Rate')
        plt.axhline(y=0.6, color='r', linestyle='--', label='Min Quality Threshold')
        plt.title('Signal Filter Pass Rate')
        plt.ylabel('Pass Rate (0-1)')
        plt.ylim(0, 1.1)
        plt.grid(True)
        plt.legend()
    
    plt.tight_layout()
    plt.savefig("results/enhanced_signal_filter_test.png")
    plt.show()

if __name__ == "__main__":
    test_filter()