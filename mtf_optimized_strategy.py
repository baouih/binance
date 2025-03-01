"""
Chiến lược giao dịch Bitcoin đa khung thời gian tối ưu hóa

Module này cung cấp chiến lược giao dịch thích ứng đa khung thời gian (MTF), kết hợp phân tích
từ nhiều khung thời gian khác nhau để tạo ra tín hiệu giao dịch chính xác hơn và giảm thiểu
tín hiệu giả.
"""

import pandas as pd
import numpy as np
import logging
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union, Any

# Thiết lập logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class MTFOptimizedStrategy:
    """
    Chiến lược giao dịch đa khung thời gian được tối ưu hóa.
    Kết hợp các khung thời gian khác nhau để tăng độ chính xác của tín hiệu.
    """
    
    def __init__(self, config: Dict = None):
        """
        Khởi tạo chiến lược giao dịch đa khung thời gian.
        
        Args:
            config (Dict, optional): Cấu hình chiến lược
        """
        # Cấu hình mặc định
        default_config = {
            "timeframes": {
                "primary": "1h",
                "secondary": ["4h", "1d"],
                "weights": {"1h": 0.5, "4h": 0.3, "1d": 0.2}
            },
            "indicators": {
                "rsi": {
                    "period": 14,
                    "overbought": 70,
                    "oversold": 30,
                    "weight": 1.0
                },
                "macd": {
                    "fast_period": 12,
                    "slow_period": 26,
                    "signal_period": 9,
                    "weight": 1.0
                },
                "ema": {
                    "short_period": 8,
                    "medium_period": 21,
                    "long_period": 55,
                    "weight": 1.0
                },
                "bb": {
                    "period": 20,
                    "std_dev": 2.0,
                    "weight": 0.8
                },
                "volume": {
                    "period": 20,
                    "weight": 0.7
                },
                "adx": {
                    "period": 14,
                    "threshold": 25,
                    "weight": 0.9
                }
            },
            "regime_configs": {
                "trending": {
                    "active": True,
                    "min_signal_strength": 0.6,
                    "take_profit_pct": 3.0,
                    "stop_loss_pct": 1.5,
                    "risk_per_trade_pct": 2.0,
                    "timeframe_alignment": 0.6  # Mức độ đồng thuận cần thiết giữa các khung thời gian
                },
                "ranging": {
                    "active": True,
                    "min_signal_strength": 0.8,
                    "take_profit_pct": 1.5,
                    "stop_loss_pct": 1.0,
                    "risk_per_trade_pct": 1.0,
                    "timeframe_alignment": 0.7
                },
                "volatile": {
                    "active": False,
                    "min_signal_strength": 0.9,
                    "take_profit_pct": 5.0,
                    "stop_loss_pct": 2.5,
                    "risk_per_trade_pct": 0.5,
                    "timeframe_alignment": 0.8
                }
            },
            "use_volume_filter": True,
            "volume_threshold": 1.5,
            "use_atr_for_stops": True,
            "atr_multiplier_tp": 2.5,
            "atr_multiplier_sl": 1.2,
            "consecutive_losses_limit": 3,
            "max_open_positions": 3,
            "enable_trailing_stop": True,
            "trailing_stop_activation_pct": 1.0,
            "trailing_stop_callback_pct": 0.5,
            "confirmation_filter": {
                "min_tf_agreement": 2,  # Số khung thời gian tối thiểu phải đồng thuận
                "primary_tf_weight": 2,  # Trọng số cho khung thời gian chính
                "trend_continuation": True  # Yêu cầu xác nhận xu hướng
            }
        }
        
        # Sử dụng cấu hình mặc định nếu không có cấu hình được cung cấp
        self.config = default_config if config is None else config
        
        # Trạng thái hiện tại của chiến lược
        self.current_regime = "ranging"  # Mặc định là ranging
        self.last_indicators = {}
        self.last_multi_tf_indicators = {}
        self.last_signal = None
        self.trading_history = []
        self.consecutive_losses = 0
        self.performance_metrics = {
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "expectancy": 0.0,
            "avg_win_pct": 0.0,
            "avg_loss_pct": 0.0,
            "regime_performance": {
                "trending": {"wins": 0, "losses": 0, "win_rate": 0.0},
                "ranging": {"wins": 0, "losses": 0, "win_rate": 0.0},
                "volatile": {"wins": 0, "losses": 0, "win_rate": 0.0}
            },
            "timeframe_performance": {
                "1h": {"accuracy": 0.0, "count": 0},
                "4h": {"accuracy": 0.0, "count": 0},
                "1d": {"accuracy": 0.0, "count": 0}
            }
        }
        
        # Tạo thư mục lưu trữ nếu chưa tồn tại
        os.makedirs("results", exist_ok=True)
        
        logger.info("Khởi tạo chiến lược giao dịch đa khung thời gian")
    
    def calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """
        Tính toán các chỉ báo kỹ thuật từ DataFrame.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            
        Returns:
            Dict: Từ điển chứa các chỉ báo đã tính
        """
        # Đảm bảo DataFrame có các cột cần thiết
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume']):
            logger.error("DataFrame thiếu các cột cần thiết")
            return {}
        
        indicators = {}
        
        # RSI
        rsi_period = self.config["indicators"]["rsi"]["period"]
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=rsi_period).mean()
        avg_loss = loss.rolling(window=rsi_period).mean()
        rs = avg_gain / avg_loss
        indicators['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        fast_period = self.config["indicators"]["macd"]["fast_period"]
        slow_period = self.config["indicators"]["macd"]["slow_period"]
        signal_period = self.config["indicators"]["macd"]["signal_period"]
        
        ema_fast = df['close'].ewm(span=fast_period, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow_period, adjust=False).mean()
        indicators['macd'] = ema_fast - ema_slow
        indicators['macd_signal'] = indicators['macd'].ewm(span=signal_period, adjust=False).mean()
        indicators['macd_hist'] = indicators['macd'] - indicators['macd_signal']
        
        # Bollinger Bands
        bb_period = self.config["indicators"]["bb"]["period"]
        std_dev = self.config["indicators"]["bb"]["std_dev"]
        
        indicators['bb_middle'] = df['close'].rolling(window=bb_period).mean()
        indicators['bb_std'] = df['close'].rolling(window=bb_period).std()
        indicators['bb_upper'] = indicators['bb_middle'] + (indicators['bb_std'] * std_dev)
        indicators['bb_lower'] = indicators['bb_middle'] - (indicators['bb_std'] * std_dev)
        indicators['bb_width'] = (indicators['bb_upper'] - indicators['bb_lower']) / indicators['bb_middle']
        
        # Exponential Moving Averages
        short_period = self.config["indicators"]["ema"]["short_period"]
        medium_period = self.config["indicators"]["ema"]["medium_period"]
        long_period = self.config["indicators"]["ema"]["long_period"]
        
        indicators['ema_short'] = df['close'].ewm(span=short_period, adjust=False).mean()
        indicators['ema_medium'] = df['close'].ewm(span=medium_period, adjust=False).mean()
        indicators['ema_long'] = df['close'].ewm(span=long_period, adjust=False).mean()
        
        # Volume Indicators
        vol_period = self.config["indicators"]["volume"]["period"]
        indicators['volume_sma'] = df['volume'].rolling(window=vol_period).mean()
        indicators['volume_ratio'] = df['volume'] / indicators['volume_sma']
        
        # ATR - Average True Range
        atr_period = 14
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - df['close'].shift()).abs()
        tr3 = (df['low'] - df['close'].shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        indicators['atr'] = tr.rolling(window=atr_period).mean()
        
        # ADX - Average Directional Index
        adx_period = self.config["indicators"]["adx"]["period"]
        
        # Plus Directional Movement (+DM)
        plus_dm = df['high'].diff()
        plus_dm = plus_dm.where((plus_dm > 0) & (plus_dm > -df['low'].diff()), 0)
        
        # Minus Directional Movement (-DM)
        minus_dm = -df['low'].diff()
        minus_dm = minus_dm.where((minus_dm > 0) & (minus_dm > df['high'].diff()), 0)
        
        # Smoothed +DM and -DM
        smoothed_plus_dm = plus_dm.rolling(window=adx_period).sum()
        smoothed_minus_dm = minus_dm.rolling(window=adx_period).sum()
        
        # Directional Indicators
        plus_di = 100 * (smoothed_plus_dm / tr.rolling(window=adx_period).sum())
        minus_di = 100 * (smoothed_minus_dm / tr.rolling(window=adx_period).sum())
        
        # Directional Index
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
        
        # Average Directional Index (ADX)
        indicators['adx'] = dx.rolling(window=adx_period).mean()
        indicators['plus_di'] = plus_di
        indicators['minus_di'] = minus_di
        
        # Thêm các chỉ báo xu hướng bổ sung cho phân tích đa khung thời gian
        
        # SuperTrend (đơn giản hóa)
        atr_multiplier = 3.0
        indicators['supertrend_upper'] = ((df['high'] + df['low']) / 2) + (atr_multiplier * indicators['atr'])
        indicators['supertrend_lower'] = ((df['high'] + df['low']) / 2) - (atr_multiplier * indicators['atr'])
        
        # Ichimoku Cloud (đơn giản hóa)
        tenkan_period = 9
        kijun_period = 26
        senkou_span_b_period = 52
        
        # Tenkan-sen (Conversion Line): (9-period high + 9-period low)/2
        indicators['tenkan_sen'] = (
            df['high'].rolling(window=tenkan_period).max() + 
            df['low'].rolling(window=tenkan_period).min()
        ) / 2
        
        # Kijun-sen (Base Line): (26-period high + 26-period low)/2
        indicators['kijun_sen'] = (
            df['high'].rolling(window=kijun_period).max() + 
            df['low'].rolling(window=kijun_period).min()
        ) / 2
        
        # Chỉ báo xác định xu hướng
        indicators['trend_direction'] = np.where(
            (indicators['ema_short'] > indicators['ema_medium']) & 
            (indicators['ema_medium'] > indicators['ema_long']) &
            (df['close'] > indicators['kijun_sen']),
            1,  # Xu hướng tăng
            np.where(
                (indicators['ema_short'] < indicators['ema_medium']) & 
                (indicators['ema_medium'] < indicators['ema_long']) &
                (df['close'] < indicators['kijun_sen']),
                -1,  # Xu hướng giảm
                0  # Không có xu hướng rõ ràng
            )
        )
        
        # Lưu các chỉ báo cuối cùng
        self.last_indicators = {k: v.iloc[-1] for k, v in indicators.items() if isinstance(v, pd.Series)}
        
        return indicators
    
    def detect_market_regime(self, df: pd.DataFrame, indicators: Dict = None) -> str:
        """
        Phát hiện chế độ thị trường hiện tại.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            indicators (Dict, optional): Từ điển chứa các chỉ báo đã tính
            
        Returns:
            str: Chế độ thị trường ("trending", "ranging", "volatile")
        """
        if indicators is None:
            indicators = self.calculate_indicators(df)
        
        if not indicators:
            return "ranging"  # Mặc định là ranging nếu không thể tính toán
        
        # Lấy các chỉ báo cuối cùng
        bb_width = indicators['bb_width'].iloc[-1]
        adx = indicators['adx'].iloc[-1]
        atr = indicators['atr'].iloc[-1]
        volume_ratio = indicators['volume_ratio'].iloc[-1]
        
        # Tính toán biến động giá
        price_volatility = df['close'].pct_change().abs().rolling(window=14).std().iloc[-1] * 100
        
        # Điểm số cho mỗi loại chế độ thị trường
        trending_score = 0
        ranging_score = 0
        volatile_score = 0
        
        # ADX > 25 thường chỉ ra xu hướng mạnh
        if adx > 25:
            trending_score += 2
        elif adx > 20:
            trending_score += 1
        else:
            ranging_score += 1
        
        # Bollinger Bands hẹp thường chỉ ra sideways market
        if bb_width < 0.03:
            ranging_score += 2
        elif bb_width < 0.05:
            ranging_score += 1
        
        # Bollinger Bands rộng thường chỉ ra thị trường biến động
        if bb_width > 0.08:
            volatile_score += 2
        elif bb_width > 0.06:
            volatile_score += 1
        
        # Biến động giá cao thường chỉ ra thị trường volatility
        if price_volatility > 5:
            volatile_score += 2
        elif price_volatility > 3:
            volatile_score += 1
        
        # Khối lượng giao dịch cao thường xuất hiện trong thị trường trending hoặc volatile
        if volume_ratio > 1.5:
            trending_score += 1
            volatile_score += 1
        
        # Thêm phân tích xu hướng từ các chỉ báo xu hướng
        trend_direction = indicators['trend_direction'].iloc[-10:].value_counts()
        if 1 in trend_direction and trend_direction[1] >= 7:  # Hầu hết các kỳ là xu hướng tăng
            trending_score += 2
        elif -1 in trend_direction and trend_direction[-1] >= 7:  # Hầu hết các kỳ là xu hướng giảm
            trending_score += 2
        elif 0 in trend_direction and trend_direction[0] >= 7:  # Hầu hết các kỳ không có xu hướng
            ranging_score += 2
        
        # Xác định chế độ thị trường dựa trên điểm số cao nhất
        scores = {
            "trending": trending_score,
            "ranging": ranging_score,
            "volatile": volatile_score
        }
        
        regime = max(scores, key=scores.get)
        
        # Nếu các điểm số quá gần nhau, mặc định là ranging
        max_score = scores[regime]
        second_highest = sorted(scores.values(), reverse=True)[1]
        if max_score - second_highest < 1:
            regime = "ranging"
        
        return regime
    
    def analyze_multi_timeframe(self, data_frames: Dict[str, pd.DataFrame]) -> Dict:
        """
        Phân tích dữ liệu từ nhiều khung thời gian khác nhau.
        
        Args:
            data_frames (Dict[str, pd.DataFrame]): Dictionary chứa DataFrame của các khung thời gian khác nhau
            
        Returns:
            Dict: Kết quả phân tích đa khung thời gian
        """
        mtf_indicators = {}
        mtf_signals = {}
        mtf_regimes = {}
        
        # Phân tích từng khung thời gian
        for tf, df in data_frames.items():
            if df.empty or len(df) < 60:  # Cần ít nhất 60 kỳ dữ liệu để phân tích
                logger.warning(f"Không đủ dữ liệu cho khung thời gian {tf}")
                continue
            
            # Tính toán chỉ báo
            indicators = self.calculate_indicators(df)
            
            # Phát hiện chế độ thị trường
            regime = self.detect_market_regime(df, indicators)
            
            # Lưu trữ kết quả
            mtf_indicators[tf] = {k: v.iloc[-1] for k, v in indicators.items() if isinstance(v, pd.Series)}
            mtf_regimes[tf] = regime
            
            # Tạo tín hiệu cho khung thời gian này
            signal_strength = self.calculate_signal_strength(mtf_indicators[tf], regime)
            
            min_signal_strength = self.config["regime_configs"][regime]["min_signal_strength"]
            
            if signal_strength >= min_signal_strength:
                mtf_signals[tf] = "BUY"
            elif signal_strength <= -min_signal_strength:
                mtf_signals[tf] = "SELL"
            else:
                mtf_signals[tf] = "NEUTRAL"
        
        # Tổng hợp dữ liệu từ các khung thời gian
        primary_tf = self.config["timeframes"]["primary"]
        
        mtf_weights = self.config["timeframes"]["weights"]
        
        # Phát hiện xung đột giữa các khung thời gian
        signal_conflicts = len(set(mtf_signals.values())) > 1
        
        # Tính toán mức độ đồng thuận
        signal_counts = {"BUY": 0, "SELL": 0, "NEUTRAL": 0}
        for tf, signal in mtf_signals.items():
            signal_counts[signal] += mtf_weights.get(tf, 1.0)
        
        # Tổng trọng số
        total_weight = sum(mtf_weights.values())
        
        # Tính phần trăm đồng thuận
        buy_alignment = signal_counts["BUY"] / total_weight if total_weight > 0 else 0
        sell_alignment = signal_counts["SELL"] / total_weight if total_weight > 0 else 0
        
        # Xác định tín hiệu tổng thể
        if buy_alignment > sell_alignment and buy_alignment >= self.config["regime_configs"][mtf_regimes.get(primary_tf, "ranging")]["timeframe_alignment"]:
            composite_signal = "BUY"
            alignment = buy_alignment
        elif sell_alignment > buy_alignment and sell_alignment >= self.config["regime_configs"][mtf_regimes.get(primary_tf, "ranging")]["timeframe_alignment"]:
            composite_signal = "SELL"
            alignment = sell_alignment
        else:
            composite_signal = "NEUTRAL"
            alignment = max(buy_alignment, sell_alignment)
        
        # Kiểm tra bộ lọc xác nhận
        confirmation_passed = False
        
        if self.config["confirmation_filter"]["min_tf_agreement"] <= sum(1 for s in mtf_signals.values() if s == composite_signal):
            # Đủ số khung thời gian đồng thuận
            if not self.config["confirmation_filter"]["trend_continuation"] or mtf_indicators.get(primary_tf, {}).get('trend_direction', 0) != 0:
                # Nếu không yêu cầu xác nhận xu hướng hoặc có xu hướng rõ ràng
                confirmation_passed = True
        
        # Lưu lại kết quả phân tích đa khung thời gian
        self.last_multi_tf_indicators = {
            "indicators": mtf_indicators,
            "signals": mtf_signals,
            "regimes": mtf_regimes,
            "composite_signal": composite_signal,
            "signal_alignment": alignment,
            "confirmation_passed": confirmation_passed
        }
        
        return {
            "indicators": mtf_indicators,
            "signals": mtf_signals,
            "regimes": mtf_regimes,
            "composite_signal": composite_signal,
            "signal_alignment": alignment,
            "confirmation_passed": confirmation_passed
        }
    
    def calculate_signal_strength(self, indicators: Dict, regime: str) -> float:
        """
        Tính toán độ mạnh của tín hiệu dựa trên các chỉ báo và chế độ thị trường.
        
        Args:
            indicators (Dict): Từ điển chứa các chỉ báo
            regime (str): Chế độ thị trường
            
        Returns:
            float: Độ mạnh của tín hiệu (-1.0 đến 1.0)
        """
        if not indicators:
            return 0.0
        
        # Trọng số cho mỗi chỉ báo
        weights = {}
        for indicator, config in self.config["indicators"].items():
            weights[indicator] = config["weight"]
        
        # Điều chỉnh trọng số dựa trên chế độ thị trường
        if regime == "trending":
            weights["ema"] *= 1.5
            weights["adx"] *= 1.5
            weights["macd"] *= 1.2
            weights["rsi"] *= 0.8
        elif regime == "ranging":
            weights["bb"] *= 1.5
            weights["rsi"] *= 1.3
            weights["adx"] *= 0.7
        elif regime == "volatile":
            weights["volume"] *= 1.5
            weights["atr"] *= 1.3
            weights["bb"] *= 1.2
        
        # Chuẩn hóa trọng số
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}
        
        # Tính toán điểm cho mỗi chỉ báo
        scores = {}
        
        # RSI Score
        rsi = indicators.get('rsi', 50)
        if rsi <= 30:
            scores["rsi"] = 1.0  # Oversold - Buy signal
        elif rsi >= 70:
            scores["rsi"] = -1.0  # Overbought - Sell signal
        else:
            # Scale between 30-70
            scores["rsi"] = -2 * (rsi - 30) / 40 + 1  # Linear scale from 1.0 at 30 to -1.0 at 70
        
        # MACD Score
        macd = indicators.get('macd', 0)
        macd_signal = indicators.get('macd_signal', 0)
        macd_hist = indicators.get('macd_hist', 0)
        prev_macd_hist = indicators.get('macd_hist_prev', 0)
        
        if macd_hist > 0 and macd > 0:
            macd_score = 0.5
        elif macd_hist > 0 and macd < 0:
            macd_score = 0.2  # MACD đang tăng nhưng vẫn âm
        elif macd_hist < 0 and macd < 0:
            macd_score = -0.5
        else:
            macd_score = -0.2  # MACD đang giảm nhưng vẫn dương
        
        # MACD histogram đang tăng/giảm
        if prev_macd_hist is not None:
            if macd_hist > prev_macd_hist:
                macd_score += 0.3
            elif macd_hist < prev_macd_hist:
                macd_score -= 0.3
        
        scores["macd"] = max(-1.0, min(1.0, macd_score))
        
        # EMA Score
        ema_short = indicators.get('ema_short', 0)
        ema_medium = indicators.get('ema_medium', 0)
        ema_long = indicators.get('ema_long', 0)
        close = indicators.get('close', 0)
        
        ema_score = 0
        
        # EMA crossovers và xu hướng
        if ema_short > ema_medium > ema_long:
            ema_score += 0.6  # Strong uptrend
        elif ema_short > ema_medium and ema_medium < ema_long:
            ema_score += 0.3  # Potential trend reversal to upside
        elif ema_short < ema_medium < ema_long:
            ema_score -= 0.6  # Strong downtrend
        elif ema_short < ema_medium and ema_medium > ema_long:
            ema_score -= 0.3  # Potential trend reversal to downside
        
        # Giá so với các EMA
        if close > ema_short:
            ema_score += 0.1
        if close > ema_medium:
            ema_score += 0.2
        if close > ema_long:
            ema_score += 0.2
        if close < ema_short:
            ema_score -= 0.1
        if close < ema_medium:
            ema_score -= 0.2
        if close < ema_long:
            ema_score -= 0.2
        
        scores["ema"] = max(-1.0, min(1.0, ema_score))
        
        # Bollinger Bands Score
        bb_upper = indicators.get('bb_upper', float('inf'))
        bb_lower = indicators.get('bb_lower', 0)
        bb_width = indicators.get('bb_width', 0)
        
        bb_score = 0
        if close <= bb_lower:
            bb_score = 1.0  # Strong buy signal
        elif close >= bb_upper:
            bb_score = -1.0  # Strong sell signal
        else:
            # Normalize position within the bands
            bb_pos = (close - bb_lower) / (bb_upper - bb_lower)
            bb_score = -2 * bb_pos + 1  # 1.0 at lower band, -1.0 at upper band
        
        # Điều chỉnh dựa trên chiều rộng của dải
        if regime == "ranging" and bb_width < 0.05:
            bb_score *= 1.5  # Khuếch đại tín hiệu trong thị trường sideways với dải hẹp
        
        scores["bb"] = max(-1.0, min(1.0, bb_score))
        
        # Volume Score
        volume_ratio = indicators.get('volume_ratio', 1.0)
        volume_score = 0
        
        if volume_ratio > 1.5:
            volume_score = 0.5  # Khối lượng lớn, tín hiệu mạnh hơn
        elif volume_ratio < 0.7:
            volume_score = -0.3  # Khối lượng nhỏ, tín hiệu yếu
        
        scores["volume"] = volume_score
        
        # ADX Score
        adx = indicators.get('adx', 0)
        plus_di = indicators.get('plus_di', 0)
        minus_di = indicators.get('minus_di', 0)
        
        adx_score = 0
        if adx > 25:  # Strong trend
            if plus_di > minus_di:
                adx_score = 0.7  # Strong uptrend
            else:
                adx_score = -0.7  # Strong downtrend
        elif adx > 20:  # Moderate trend
            if plus_di > minus_di:
                adx_score = 0.4
            else:
                adx_score = -0.4
        else:  # Weak trend
            adx_score = 0
        
        scores["adx"] = adx_score
        
        # Trend Direction Score (from SuperTrend and Ichimoku)
        trend_direction = indicators.get('trend_direction', 0)
        trend_score = 0.5 * trend_direction  # -0.5, 0, or 0.5
        
        # Thêm điểm với Ichimoku
        tenkan = indicators.get('tenkan_sen', 0)
        kijun = indicators.get('kijun_sen', 0)
        
        if close > kijun and tenkan > kijun:
            trend_score += 0.3  # Bullish
        elif close < kijun and tenkan < kijun:
            trend_score -= 0.3  # Bearish
        
        scores["trend"] = max(-1.0, min(1.0, trend_score))
        
        # Tính toán tín hiệu tổng hợp
        signal_strength = sum(scores[k] * weights.get(k, 0) for k in scores)
        
        # Điều chỉnh tín hiệu dựa trên số lần thua liên tiếp
        if self.consecutive_losses >= self.config["consecutive_losses_limit"]:
            signal_strength *= 0.5  # Giảm cường độ tín hiệu sau nhiều lần thua liên tiếp
        
        return max(-1.0, min(1.0, signal_strength))
    
    def generate_signal(self, data_frames: Dict[str, pd.DataFrame]) -> Dict:
        """
        Tạo tín hiệu giao dịch dựa trên phân tích đa khung thời gian.
        
        Args:
            data_frames (Dict[str, pd.DataFrame]): Dictionary chứa DataFrame của các khung thời gian khác nhau
            
        Returns:
            Dict: Tín hiệu giao dịch và các thông tin liên quan
        """
        # Kiểm tra dữ liệu
        primary_tf = self.config["timeframes"]["primary"]
        if primary_tf not in data_frames or data_frames[primary_tf].empty:
            logger.warning(f"Không có dữ liệu cho khung thời gian chính {primary_tf}")
            return {"signal": "NEUTRAL", "strength": 0, "regime": self.current_regime}
        
        # Phân tích đa khung thời gian
        mtf_analysis = self.analyze_multi_timeframe(data_frames)
        
        # Lấy regime từ khung thời gian chính
        self.current_regime = mtf_analysis["regimes"].get(primary_tf, "ranging")
        
        # Kiểm tra xem chế độ thị trường có được kích hoạt không
        if not self.config["regime_configs"][self.current_regime]["active"]:
            logger.info(f"Chế độ thị trường {self.current_regime} không được kích hoạt")
            return {"signal": "NEUTRAL", "strength": 0, "regime": self.current_regime}
        
        # Phân tích chỉ báo từ khung thời gian chính
        primary_indicators = mtf_analysis["indicators"].get(primary_tf, {})
        
        # Thêm giá đóng cửa gần nhất vào indicators
        if 'close' not in primary_indicators:
            primary_indicators['close'] = data_frames[primary_tf]['close'].iloc[-1]
        
        # Thêm giá trị MACD histogram trước đó
        indicators = self.calculate_indicators(data_frames[primary_tf])
        if 'macd_hist' in primary_indicators and len(indicators['macd_hist']) > 1:
            primary_indicators['macd_hist_prev'] = indicators['macd_hist'].iloc[-2]
        
        # Tín hiệu từ phân tích đa khung thời gian
        composite_signal = mtf_analysis["composite_signal"]
        signal_alignment = mtf_analysis["signal_alignment"]
        confirmation_passed = mtf_analysis["confirmation_passed"]
        
        # Thêm kiểm tra lọc khối lượng
        volume_filter_passed = True
        if self.config["use_volume_filter"]:
            volume_ratio = primary_indicators.get('volume_ratio', 1.0)
            volume_filter_passed = volume_ratio >= self.config["volume_threshold"]
        
        # Xác định tín hiệu cuối cùng
        final_signal = "NEUTRAL"
        if composite_signal != "NEUTRAL" and confirmation_passed and volume_filter_passed:
            final_signal = composite_signal
        
        # Tính toán các mức stop loss và take profit
        current_price = data_frames[primary_tf]['close'].iloc[-1]
        atr = primary_indicators.get('atr', current_price * 0.02)  # Mặc định là 2% nếu không có ATR
        
        stop_loss_pct = self.config["regime_configs"][self.current_regime]["stop_loss_pct"]
        take_profit_pct = self.config["regime_configs"][self.current_regime]["take_profit_pct"]
        
        # Sử dụng ATR để tính SL/TP nếu được cấu hình
        if self.config["use_atr_for_stops"]:
            stop_loss = atr * self.config["atr_multiplier_sl"]
            take_profit = atr * self.config["atr_multiplier_tp"]
            
            # Chuyển đổi thành phần trăm
            stop_loss_pct = (stop_loss / current_price) * 100
            take_profit_pct = (take_profit / current_price) * 100
        
        # Đảm bảo mức SL/TP không quá lớn hoặc quá nhỏ
        stop_loss_pct = min(10.0, max(0.5, stop_loss_pct))
        take_profit_pct = min(50.0, max(1.0, take_profit_pct))
        
        # Tính risk-reward ratio
        risk_reward_ratio = take_profit_pct / stop_loss_pct if stop_loss_pct > 0 else 0
        
        # Tạo tín hiệu
        signal_data = {
            "signal": final_signal,
            "strength": signal_alignment,
            "regime": self.current_regime,
            "mtf_signals": mtf_analysis["signals"],
            "mtf_regimes": mtf_analysis["regimes"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "price": current_price,
            "stop_loss_pct": stop_loss_pct,
            "take_profit_pct": take_profit_pct,
            "risk_reward_ratio": risk_reward_ratio,
            "volume_filter_passed": volume_filter_passed,
            "confirmation_passed": confirmation_passed,
            "primary_indicators": {k: float(v) if isinstance(v, (int, float, np.number)) else v 
                           for k, v in primary_indicators.items()},
            "risk_per_trade_pct": self.config["regime_configs"][self.current_regime]["risk_per_trade_pct"],
            "enable_trailing_stop": self.config["enable_trailing_stop"],
            "trailing_stop_activation_pct": self.config["trailing_stop_activation_pct"],
            "trailing_stop_callback_pct": self.config["trailing_stop_callback_pct"]
        }
        
        self.last_signal = signal_data
        return signal_data
    
    def update_performance(self, trade_result: Dict) -> None:
        """
        Cập nhật các chỉ số hiệu suất dựa trên kết quả giao dịch.
        
        Args:
            trade_result (Dict): Kết quả giao dịch
                {
                    "entry_price": float,
                    "exit_price": float,
                    "pnl_pct": float,
                    "direction": str ("LONG" or "SHORT"),
                    "exit_reason": str,
                    "regime": str,
                    "timestamp": str,
                    "mtf_signals": Dict[str, str]
                }
        """
        if not trade_result:
            return
        
        self.trading_history.append(trade_result)
        
        # Cập nhật số lần thắng/thua
        is_win = trade_result["pnl_pct"] > 0
        regime = trade_result.get("regime", "ranging")
        
        if is_win:
            self.performance_metrics["wins"] += 1
            self.performance_metrics["regime_performance"][regime]["wins"] += 1
            self.consecutive_losses = 0
        else:
            self.performance_metrics["losses"] += 1
            self.performance_metrics["regime_performance"][regime]["losses"] += 1
            self.consecutive_losses += 1
        
        # Cập nhật win rate
        total_trades = self.performance_metrics["wins"] + self.performance_metrics["losses"]
        self.performance_metrics["win_rate"] = (self.performance_metrics["wins"] / total_trades) * 100 if total_trades > 0 else 0
        
        # Cập nhật win rate theo chế độ
        for r in self.performance_metrics["regime_performance"]:
            regime_trades = self.performance_metrics["regime_performance"][r]["wins"] + self.performance_metrics["regime_performance"][r]["losses"]
            if regime_trades > 0:
                self.performance_metrics["regime_performance"][r]["win_rate"] = (
                    self.performance_metrics["regime_performance"][r]["wins"] / regime_trades
                ) * 100
        
        # Cập nhật hiệu suất theo khung thời gian
        if "mtf_signals" in trade_result:
            for tf, signal in trade_result["mtf_signals"].items():
                if tf not in self.performance_metrics["timeframe_performance"]:
                    self.performance_metrics["timeframe_performance"][tf] = {"accuracy": 0.0, "count": 0}
                
                # Kiểm tra tín hiệu có đúng không
                is_correct = (signal == "BUY" and trade_result["pnl_pct"] > 0) or (signal == "SELL" and trade_result["pnl_pct"] < 0)
                
                self.performance_metrics["timeframe_performance"][tf]["count"] += 1
                count = self.performance_metrics["timeframe_performance"][tf]["count"]
                
                # Cập nhật độ chính xác
                current_accuracy = self.performance_metrics["timeframe_performance"][tf]["accuracy"]
                new_accuracy = ((count - 1) * current_accuracy + (1 if is_correct else 0)) / count
                self.performance_metrics["timeframe_performance"][tf]["accuracy"] = new_accuracy
        
        # Tính average win/loss
        win_trades = [t["pnl_pct"] for t in self.trading_history if t["pnl_pct"] > 0]
        loss_trades = [t["pnl_pct"] for t in self.trading_history if t["pnl_pct"] <= 0]
        
        self.performance_metrics["avg_win_pct"] = sum(win_trades) / len(win_trades) if win_trades else 0
        self.performance_metrics["avg_loss_pct"] = sum(loss_trades) / len(loss_trades) if loss_trades else 0
        
        # Tính expectancy
        if self.performance_metrics["avg_loss_pct"] != 0:
            win_loss_ratio = abs(self.performance_metrics["avg_win_pct"] / self.performance_metrics["avg_loss_pct"])
            win_rate = self.performance_metrics["win_rate"] / 100
            self.performance_metrics["expectancy"] = (win_rate * win_loss_ratio) - (1 - win_rate)
        
        # Lưu dữ liệu hiệu suất
        self._save_performance()
    
    def _save_performance(self) -> None:
        """Lưu dữ liệu hiệu suất vào file JSON."""
        try:
            performance_data = {
                "metrics": self.performance_metrics,
                "trading_history": self.trading_history,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open("results/mtf_strategy_performance.json", "w") as f:
                json.dump(performance_data, f, indent=4)
            
            logger.info("Đã lưu dữ liệu hiệu suất thành công")
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu hiệu suất: {e}")
    
    def load_performance(self) -> bool:
        """
        Tải dữ liệu hiệu suất từ file.
        
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        try:
            if os.path.exists("results/mtf_strategy_performance.json"):
                with open("results/mtf_strategy_performance.json", "r") as f:
                    data = json.load(f)
                
                self.performance_metrics = data.get("metrics", self.performance_metrics)
                self.trading_history = data.get("trading_history", [])
                
                logger.info("Đã tải dữ liệu hiệu suất thành công")
                return True
            else:
                logger.warning("Không tìm thấy file dữ liệu hiệu suất")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu hiệu suất: {e}")
            return False
    
    def adapt_to_market_conditions(self) -> None:
        """
        Điều chỉnh các tham số chiến lược dựa trên điều kiện thị trường và hiệu suất gần đây.
        """
        # Kiểm tra số lượng giao dịch vừa đủ để điều chỉnh
        if len(self.trading_history) < 5:
            logger.info("Chưa đủ dữ liệu giao dịch để điều chỉnh")
            return
        
        # Lấy hiệu suất gần đây (10 giao dịch gần nhất)
        recent_trades = self.trading_history[-10:]
        regime_counts = {"trending": 0, "ranging": 0, "volatile": 0}
        regime_wins = {"trending": 0, "ranging": 0, "volatile": 0}
        
        for trade in recent_trades:
            regime = trade.get("regime", "ranging")
            regime_counts[regime] += 1
            if trade["pnl_pct"] > 0:
                regime_wins[regime] += 1
        
        # Tính win rate gần đây cho mỗi chế độ
        regime_win_rates = {}
        for regime, count in regime_counts.items():
            if count > 0:
                regime_win_rates[regime] = (regime_wins[regime] / count) * 100
            else:
                regime_win_rates[regime] = 0
        
        # Điều chỉnh cấu hình dựa trên hiệu suất
        for regime, win_rate in regime_win_rates.items():
            if count < 3:  # Bỏ qua nếu không đủ dữ liệu
                continue
            
            # Thêm trọng số cho các chỉ báo hiệu quả
            if win_rate < 40:  # Hiệu suất kém
                # Tăng ngưỡng tín hiệu
                self.config["regime_configs"][regime]["min_signal_strength"] = min(
                    0.9, self.config["regime_configs"][regime]["min_signal_strength"] + 0.05
                )
                
                # Tăng yêu cầu đồng thuận giữa các khung thời gian
                self.config["regime_configs"][regime]["timeframe_alignment"] = min(
                    0.9, self.config["regime_configs"][regime]["timeframe_alignment"] + 0.05
                )
                
                # Điều chỉnh risk reward ratio
                self.config["regime_configs"][regime]["take_profit_pct"] = min(
                    20.0, self.config["regime_configs"][regime]["take_profit_pct"] * 1.1
                )
                
                # Giảm risk per trade
                self.config["regime_configs"][regime]["risk_per_trade_pct"] = max(
                    0.5, self.config["regime_configs"][regime]["risk_per_trade_pct"] * 0.9
                )
                
                logger.info(f"Điều chỉnh cấu hình cho chế độ {regime} do hiệu suất kém (win rate: {win_rate:.1f}%)")
            
            elif win_rate > 60:  # Hiệu suất tốt
                # Giảm ngưỡng tín hiệu
                self.config["regime_configs"][regime]["min_signal_strength"] = max(
                    0.5, self.config["regime_configs"][regime]["min_signal_strength"] - 0.02
                )
                
                # Giảm yêu cầu đồng thuận
                self.config["regime_configs"][regime]["timeframe_alignment"] = max(
                    0.5, self.config["regime_configs"][regime]["timeframe_alignment"] - 0.02
                )
                
                # Tăng risk per trade
                self.config["regime_configs"][regime]["risk_per_trade_pct"] = min(
                    3.0, self.config["regime_configs"][regime]["risk_per_trade_pct"] * 1.05
                )
                
                logger.info(f"Điều chỉnh cấu hình cho chế độ {regime} do hiệu suất tốt (win rate: {win_rate:.1f}%)")
        
        # Điều chỉnh trọng số khung thời gian dựa trên độ chính xác
        tf_weights = self.config["timeframes"]["weights"]
        total_accuracy = 0
        
        # Tính tổng độ chính xác có trọng số
        for tf, stats in self.performance_metrics["timeframe_performance"].items():
            if stats["count"] > 5:  # Chỉ xem xét nếu có đủ dữ liệu
                total_accuracy += stats["accuracy"]
        
        # Cập nhật trọng số
        if total_accuracy > 0:
            for tf, stats in self.performance_metrics["timeframe_performance"].items():
                if stats["count"] > 5:
                    tf_weights[tf] = max(0.1, min(0.7, stats["accuracy"] / total_accuracy))
            
            # Chuẩn hóa trọng số
            total_weight = sum(tf_weights.values())
            if total_weight > 0:
                self.config["timeframes"]["weights"] = {tf: w / total_weight for tf, w in tf_weights.items()}
    
    def get_performance_summary(self) -> Dict:
        """
        Lấy tóm tắt hiệu suất của chiến lược.
        
        Returns:
            Dict: Tóm tắt hiệu suất
        """
        return {
            "total_trades": len(self.trading_history),
            "win_rate": self.performance_metrics["win_rate"],
            "expectancy": self.performance_metrics["expectancy"],
            "avg_win_pct": self.performance_metrics["avg_win_pct"],
            "avg_loss_pct": self.performance_metrics["avg_loss_pct"],
            "regime_performance": self.performance_metrics["regime_performance"],
            "timeframe_performance": self.performance_metrics["timeframe_performance"],
            "consecutive_losses": self.consecutive_losses
        }
    
    def get_strategy_details(self) -> Dict:
        """
        Lấy chi tiết cấu hình hiện tại của chiến lược.
        
        Returns:
            Dict: Chi tiết chiến lược
        """
        return {
            "current_regime": self.current_regime,
            "regime_configs": self.config["regime_configs"],
            "indicators": self.config["indicators"],
            "timeframes": self.config["timeframes"],
            "confirmation_filter": self.config["confirmation_filter"],
            "last_signal": self.last_signal,
            "performance": self.get_performance_summary()
        }

# Hàm test
def test_strategy():
    """
    Kiểm tra chiến lược giao dịch đa khung thời gian với dữ liệu lịch sử.
    """
    import pandas as pd
    import matplotlib.pyplot as plt
    from datetime import datetime
    
    # Tải dữ liệu
    try:
        data_frames = {}
        for tf in ["1h", "4h", "1d"]:
            file_path = f"test_data/BTCUSDT_{tf}.csv"
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                df['datetime'] = pd.to_datetime(df['timestamp'])
                df.set_index('datetime', inplace=True)
                data_frames[tf] = df
            else:
                print(f"File {file_path} không tồn tại")
    except Exception as e:
        print(f"Lỗi khi tải dữ liệu: {e}")
        return
    
    # Kiểm tra dữ liệu
    if not data_frames or "1h" not in data_frames:
        print("Không đủ dữ liệu để test chiến lược")
        return
    
    # Khởi tạo chiến lược
    strategy = MTFOptimizedStrategy()
    
    # Mô phỏng giao dịch
    signals = []
    balance = 10000.0
    position = None
    trades = []
    
    primary_tf = "1h"
    window_size = 200  # Số lượng kỳ dữ liệu để phân tích
    
    # Cắt dữ liệu để đảm bảo các khung thời gian có cùng khoảng thời gian
    start_date = max([df.index[0] for df in data_frames.values()])
    end_date = min([df.index[-1] for df in data_frames.values()])
    
    for tf in data_frames:
        data_frames[tf] = data_frames[tf].loc[(data_frames[tf].index >= start_date) & (data_frames[tf].index <= end_date)]
    
    # Tạo các mốc thời gian để phân tích
    time_points = data_frames[primary_tf].index[window_size:]
    
    for i, time_point in enumerate(time_points):
        # Lấy dữ liệu cho mỗi khung thời gian
        current_data = {}
        for tf, df in data_frames.items():
            # Lấy tất cả dữ liệu đến thời điểm hiện tại
            mask = df.index <= time_point
            current_data[tf] = df.loc[mask].iloc[-window_size:] if sum(mask) >= window_size else df.loc[mask]
        
        # Tạo tín hiệu
        signal = strategy.generate_signal(current_data)
        current_price = data_frames[primary_tf].loc[time_point, 'close']
        
        signals.append({
            "timestamp": time_point, 
            "signal": signal["signal"], 
            "price": current_price, 
            "regime": signal["regime"],
            "mtf_signals": signal.get("mtf_signals", {})
        })
        
        # Xử lý vị thế hiện tại
        if position:
            # Kiểm tra stop loss
            if (position["direction"] == "LONG" and current_price <= position["stop_loss"]) or \
               (position["direction"] == "SHORT" and current_price >= position["stop_loss"]):
                # Đóng vị thế do stop loss
                pnl = (current_price / position["entry_price"] - 1) * 100 * (1 if position["direction"] == "LONG" else -1)
                trade_result = {
                    "entry_price": position["entry_price"],
                    "exit_price": current_price,
                    "pnl_pct": pnl,
                    "direction": position["direction"],
                    "exit_reason": "STOP_LOSS",
                    "regime": position["regime"],
                    "timestamp": time_point.strftime("%Y-%m-%d %H:%M:%S"),
                    "mtf_signals": position.get("mtf_signals", {})
                }
                trades.append(trade_result)
                
                # Cập nhật balance
                balance = balance * (1 + pnl / 100)
                position = None
                
                # Cập nhật hiệu suất
                strategy.update_performance(trade_result)
            
            # Kiểm tra take profit
            elif (position["direction"] == "LONG" and current_price >= position["take_profit"]) or \
                 (position["direction"] == "SHORT" and current_price <= position["take_profit"]):
                # Đóng vị thế do take profit
                pnl = (current_price / position["entry_price"] - 1) * 100 * (1 if position["direction"] == "LONG" else -1)
                trade_result = {
                    "entry_price": position["entry_price"],
                    "exit_price": current_price,
                    "pnl_pct": pnl,
                    "direction": position["direction"],
                    "exit_reason": "TAKE_PROFIT",
                    "regime": position["regime"],
                    "timestamp": time_point.strftime("%Y-%m-%d %H:%M:%S"),
                    "mtf_signals": position.get("mtf_signals", {})
                }
                trades.append(trade_result)
                
                # Cập nhật balance
                balance = balance * (1 + pnl / 100)
                position = None
                
                # Cập nhật hiệu suất
                strategy.update_performance(trade_result)
            
            # Kiểm tra tín hiệu đóng vị thế
            elif (position["direction"] == "LONG" and signal["signal"] == "SELL") or \
                 (position["direction"] == "SHORT" and signal["signal"] == "BUY"):
                # Đóng vị thế do tín hiệu đảo chiều
                pnl = (current_price / position["entry_price"] - 1) * 100 * (1 if position["direction"] == "LONG" else -1)
                trade_result = {
                    "entry_price": position["entry_price"],
                    "exit_price": current_price,
                    "pnl_pct": pnl,
                    "direction": position["direction"],
                    "exit_reason": "SIGNAL_REVERSE",
                    "regime": position["regime"],
                    "timestamp": time_point.strftime("%Y-%m-%d %H:%M:%S"),
                    "mtf_signals": position.get("mtf_signals", {})
                }
                trades.append(trade_result)
                
                # Cập nhật balance
                balance = balance * (1 + pnl / 100)
                position = None
                
                # Cập nhật hiệu suất
                strategy.update_performance(trade_result)
        
        # Mở vị thế mới nếu không có vị thế hiện tại
        if position is None:
            if signal["signal"] == "BUY":
                # Mở vị thế LONG
                stop_loss = current_price * (1 - signal["stop_loss_pct"] / 100)
                take_profit = current_price * (1 + signal["take_profit_pct"] / 100)
                
                position = {
                    "direction": "LONG",
                    "entry_price": current_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "regime": signal["regime"],
                    "entry_time": time_point,
                    "mtf_signals": signal.get("mtf_signals", {})
                }
            
            elif signal["signal"] == "SELL":
                # Mở vị thế SHORT
                stop_loss = current_price * (1 + signal["stop_loss_pct"] / 100)
                take_profit = current_price * (1 - signal["take_profit_pct"] / 100)
                
                position = {
                    "direction": "SHORT",
                    "entry_price": current_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "regime": signal["regime"],
                    "entry_time": time_point,
                    "mtf_signals": signal.get("mtf_signals", {})
                }
        
        # Điều chỉnh chiến lược sau mỗi 20 giao dịch
        if len(trades) > 0 and len(trades) % 20 == 0:
            strategy.adapt_to_market_conditions()
    
    # Đóng vị thế cuối cùng nếu còn
    if position:
        last_price = data_frames[primary_tf]['close'].iloc[-1]
        pnl = (last_price / position["entry_price"] - 1) * 100 * (1 if position["direction"] == "LONG" else -1)
        trade_result = {
            "entry_price": position["entry_price"],
            "exit_price": last_price,
            "pnl_pct": pnl,
            "direction": position["direction"],
            "exit_reason": "END_OF_TEST",
            "regime": position["regime"],
            "timestamp": data_frames[primary_tf].index[-1].strftime("%Y-%m-%d %H:%M:%S"),
            "mtf_signals": position.get("mtf_signals", {})
        }
        trades.append(trade_result)
        
        # Cập nhật balance
        balance = balance * (1 + pnl / 100)
        
        # Cập nhật hiệu suất
        strategy.update_performance(trade_result)
    
    # Tính toán các chỉ số
    win_trades = [t for t in trades if t["pnl_pct"] > 0]
    loss_trades = [t for t in trades if t["pnl_pct"] <= 0]
    
    win_rate = len(win_trades) / len(trades) * 100 if trades else 0
    avg_win = sum(t["pnl_pct"] for t in win_trades) / len(win_trades) if win_trades else 0
    avg_loss = sum(t["pnl_pct"] for t in loss_trades) / len(loss_trades) if loss_trades else 0
    
    # In kết quả
    print(f"===== Kết quả backtest chiến lược đa khung thời gian =====")
    print(f"Số lượng giao dịch: {len(trades)}")
    print(f"Win rate: {win_rate:.2f}%")
    print(f"Lợi nhuận trung bình khi thắng: {avg_win:.2f}%")
    print(f"Lỗ trung bình khi thua: {avg_loss:.2f}%")
    print(f"Balance cuối: ${balance:.2f} (Lợi nhuận: {(balance/10000-1)*100:.2f}%)")
    print(f"Số giao dịch theo chế độ thị trường:")
    
    regime_stats = {"trending": {"count": 0, "wins": 0}, "ranging": {"count": 0, "wins": 0}, "volatile": {"count": 0, "wins": 0}}
    for trade in trades:
        regime = trade.get("regime", "ranging")
        regime_stats[regime]["count"] += 1
        if trade["pnl_pct"] > 0:
            regime_stats[regime]["wins"] += 1
    
    for regime, stats in regime_stats.items():
        if stats["count"] > 0:
            win_rate = stats["wins"] / stats["count"] * 100
            print(f"  {regime}: {stats['count']} giao dịch, win rate: {win_rate:.2f}%")
    
    # Hiệu suất theo khung thời gian
    print("\nHiệu suất theo khung thời gian:")
    for tf, stats in strategy.performance_metrics["timeframe_performance"].items():
        if stats["count"] > 0:
            print(f"  {tf}: {stats['count']} giao dịch, độ chính xác: {stats['accuracy']*100:.2f}%")
    
    print("===========================")
    
    # Vẽ biểu đồ
    plt.figure(figsize=(14, 8))
    
    # Vẽ giá
    plt.subplot(2, 1, 1)
    plt.plot(time_points, data_frames[primary_tf].loc[time_points, 'close'], label='Price')
    
    # Vẽ các tín hiệu
    buy_signals = [s for s in signals if s["signal"] == "BUY"]
    sell_signals = [s for s in signals if s["signal"] == "SELL"]
    
    buy_x = [s["timestamp"] for s in buy_signals]
    buy_y = [s["price"] for s in buy_signals]
    
    sell_x = [s["timestamp"] for s in sell_signals]
    sell_y = [s["price"] for s in sell_signals]
    
    plt.scatter(buy_x, buy_y, color='green', marker='^', alpha=0.7, s=100, label='BUY')
    plt.scatter(sell_x, sell_y, color='red', marker='v', alpha=0.7, s=100, label='SELL')
    
    # Vẽ các giao dịch
    for trade in trades:
        entry_time = datetime.strptime(trade["timestamp"], "%Y-%m-%d %H:%M:%S")
        color = 'green' if trade["pnl_pct"] > 0 else 'red'
        plt.annotate(f"{trade['pnl_pct']:.1f}%", 
                    xy=(entry_time, trade["entry_price"]), 
                    xytext=(0, 10), 
                    textcoords='offset points',
                    color=color,
                    fontweight='bold')
    
    plt.title('Bitcoin Price and Trading Signals (Multi-Timeframe Strategy)')
    plt.ylabel('Price (USD)')
    plt.grid(True)
    plt.legend()
    
    # Vẽ chế độ thị trường
    plt.subplot(2, 1, 2)
    
    regimes = [s["regime"] for s in signals]
    regime_values = [1 if r == "trending" else 0.5 if r == "ranging" else 0 for r in regimes]
    
    plt.plot(time_points, regime_values, color='blue', label='Market Regime')
    plt.yticks([0, 0.5, 1], ['Volatile', 'Ranging', 'Trending'])
    plt.title('Market Regime Detection')
    plt.xlabel('Date')
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig("results/mtf_backtest_results.png")
    plt.show()

if __name__ == "__main__":
    test_strategy()