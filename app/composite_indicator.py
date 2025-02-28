"""
Module Chỉ báo tổng hợp (Composite Indicator) cho thư mục app

Module này cung cấp các công cụ để tạo và sử dụng chỉ báo tổng hợp từ nhiều chỉ báo kỹ thuật
khác nhau, mang lại tín hiệu giao dịch có độ tin cậy cao hơn so với các chỉ báo đơn lẻ.
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Union

logger = logging.getLogger(__name__)

class CompositeIndicator:
    """
    Lớp Chỉ báo tổng hợp kết hợp nhiều chỉ báo kỹ thuật thành một
    hệ thống chấm điểm thống nhất để tạo tín hiệu giao dịch.
    """

    SUPPORTED_INDICATORS = {
        'rsi': 'RSI (0-100), dưới 30 -> +1, trên 70 -> -1',
        'macd': 'MACD, historgram dương -> +1, âm -> -1',
        'ema_cross': 'EMA cross, EMA ngắn cắt lên EMA dài -> +1, cắt xuống -> -1',
        'bbands': 'Bollinger Bands, giá dưới hạ band -> +0.5, trên thượng band -> -0.5',
        'volume_trend': 'Volume trend, khối lượng tăng với giá tăng -> +0.5, khối lượng tăng với giá giảm -> -0.5',
        'adx': 'ADX (0-100), ADX > 25 xác nhận xu hướng -> +/-0.5 (dấu phụ thuộc vào DI+/DI-)',
        'stochastic': 'Stochastic (0-100), dưới 20 -> +0.5, trên 80 -> -0.5, kèm %K cắt %D',
        'obv': 'On-Balance Volume, OBV tăng -> +0.5, OBV giảm -> -0.5',
        'atr': 'ATR, được sử dụng để xác định mức biến động, không tạo tín hiệu trực tiếp'
    }

    def __init__(self, indicators: List[str] = None, weights: Dict[str, float] = None, 
                dynamic_weights: bool = True, lookback_period: int = 20):
        """
        Khởi tạo chỉ báo tổng hợp.
        
        Args:
            indicators (List[str]): Danh sách các chỉ báo sẽ được sử dụng
            weights (Dict[str, float]): Trọng số cho mỗi chỉ báo (0.0-1.0)
            dynamic_weights (bool): Có sử dụng trọng số động dựa trên hiệu suất không
            lookback_period (int): Số chu kỳ để phân tích hiệu suất
        """
        self.indicators = indicators or list(self.SUPPORTED_INDICATORS.keys())
        self.weights = weights or {ind: 1.0/len(self.indicators) for ind in self.indicators}
        self.dynamic_weights = dynamic_weights
        self.lookback_period = lookback_period
        self.performance_history = {ind: [] for ind in self.indicators}
        
        logger.info(f"Khởi tạo CompositeIndicator với {len(self.indicators)} chỉ báo: {self.indicators}")

    def calculate_individual_scores(self, dataframe: pd.DataFrame) -> Dict[str, float]:
        """
        Tính toán điểm số cho từng chỉ báo riêng lẻ.
        
        Args:
            dataframe (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            
        Returns:
            Dict[str, float]: Điểm số cho từng chỉ báo (-1.0 đến 1.0)
        """
        if dataframe.empty:
            logger.warning("DataFrame trống, không thể tính điểm chỉ báo")
            return {ind: 0.0 for ind in self.indicators}
        
        scores = {}
        row = dataframe.iloc[-1]  # Lấy dòng cuối cùng
        prev_row = dataframe.iloc[-2] if len(dataframe) > 1 else None
        
        # Tính điểm cho từng chỉ báo
        for indicator in self.indicators:
            if indicator == 'rsi' and 'rsi' in row:
                scores[indicator] = self._calculate_rsi_score(row['rsi'])
            
            elif indicator == 'macd' and 'macd_hist' in row:
                prev_macd_hist = prev_row['macd_hist'] if prev_row is not None else None
                scores[indicator] = self._calculate_macd_score(row['macd_hist'], prev_macd_hist)
            
            elif indicator == 'ema_cross' and 'ema_short' in row and 'ema_long' in row:
                prev_ema_short = prev_row['ema_short'] if prev_row is not None else None
                prev_ema_long = prev_row['ema_long'] if prev_row is not None else None
                scores[indicator] = self._calculate_ema_cross_score(
                    row['ema_short'], row['ema_long'], prev_ema_short, prev_ema_long
                )
            
            elif indicator == 'bbands' and 'bb_upper' in row and 'bb_lower' in row:
                scores[indicator] = self._calculate_bbands_score(row['close'], row['bb_upper'], row['bb_lower'])
            
            elif indicator == 'volume_trend' and 'volume' in row:
                prev_volume = prev_row['volume'] if prev_row is not None else None
                prev_close = prev_row['close'] if prev_row is not None else None
                scores[indicator] = self._calculate_volume_trend_score(
                    row['volume'], row['close'], prev_volume, prev_close
                )
            
            elif indicator == 'adx' and 'adx' in row and 'di_plus' in row and 'di_minus' in row:
                scores[indicator] = self._calculate_adx_score(row['adx'], row['di_plus'], row['di_minus'])
            
            elif indicator == 'stochastic' and 'stoch_k' in row and 'stoch_d' in row:
                prev_stoch_k = prev_row['stoch_k'] if prev_row is not None else None
                prev_stoch_d = prev_row['stoch_d'] if prev_row is not None else None
                scores[indicator] = self._calculate_stochastic_score(
                    row['stoch_k'], row['stoch_d'], prev_stoch_k, prev_stoch_d
                )
            
            elif indicator == 'obv' and 'obv' in row:
                prev_obv = prev_row['obv'] if prev_row is not None else None
                scores[indicator] = self._calculate_obv_score(row['obv'], prev_obv)
            
            else:
                scores[indicator] = 0.0  # Nếu không có dữ liệu cho chỉ báo này
        
        return scores

    def _calculate_rsi_score(self, rsi: float) -> float:
        """
        Tính điểm cho RSI.
        
        Args:
            rsi (float): Giá trị RSI hiện tại
            
        Returns:
            float: Điểm số (-1.0 đến 1.0)
        """
        if rsi < 30:
            return 1.0
        elif rsi > 70:
            return -1.0
        elif rsi < 45:
            return 0.5
        elif rsi > 55:
            return -0.5
        else:
            return 0.0

    def _calculate_macd_score(self, macd_hist: float, prev_macd_hist: Optional[float]) -> float:
        """
        Tính điểm cho MACD.
        
        Args:
            macd_hist (float): MACD histogram hiện tại
            prev_macd_hist (float, optional): MACD histogram trước đó
            
        Returns:
            float: Điểm số (-1.0 đến 1.0)
        """
        score = 0.0
        
        # Điểm cơ bản dựa trên giá trị histogram
        if macd_hist > 0:
            score += 0.5
        elif macd_hist < 0:
            score -= 0.5
        
        # Điểm bổ sung dựa trên sự thay đổi
        if prev_macd_hist is not None:
            if macd_hist > prev_macd_hist:
                score += 0.5
            elif macd_hist < prev_macd_hist:
                score -= 0.5
        
        # Giới hạn trong phạm vi [-1, 1]
        return max(-1.0, min(1.0, score))

    def _calculate_ema_cross_score(self, ema_short: float, ema_long: float, 
                                  prev_ema_short: Optional[float], prev_ema_long: Optional[float]) -> float:
        """
        Tính điểm cho EMA Cross.
        
        Args:
            ema_short (float): EMA ngắn hạn hiện tại
            ema_long (float): EMA dài hạn hiện tại
            prev_ema_short (float, optional): EMA ngắn hạn trước đó
            prev_ema_long (float, optional): EMA dài hạn trước đó
            
        Returns:
            float: Điểm số (-1.0 đến 1.0)
        """
        score = 0.0
        
        # Điểm cơ bản dựa trên vị trí hiện tại
        if ema_short > ema_long:
            score += 0.5
        elif ema_short < ema_long:
            score -= 0.5
        
        # Điểm bổ sung dựa trên việc có cắt nhau hay không
        if prev_ema_short is not None and prev_ema_long is not None:
            if ema_short > ema_long and prev_ema_short < prev_ema_long:
                score += 0.5  # Cắt lên
            elif ema_short < ema_long and prev_ema_short > prev_ema_long:
                score -= 0.5  # Cắt xuống
        
        return score

    def _calculate_bbands_score(self, close: float, bb_upper: float, bb_lower: float) -> float:
        """
        Tính điểm cho Bollinger Bands.
        
        Args:
            close (float): Giá đóng cửa hiện tại
            bb_upper (float): Dải trên Bollinger
            bb_lower (float): Dải dưới Bollinger
            
        Returns:
            float: Điểm số (-1.0 đến 1.0)
        """
        bb_width = (bb_upper - bb_lower) / ((bb_upper + bb_lower) / 2)
        middle = (bb_upper + bb_lower) / 2
        
        if close <= bb_lower:
            return 0.5 + min(0.5, (bb_lower - close) / (bb_lower * 0.01))  # Tăng điểm nếu giá càng thấp dưới dải dưới
        elif close >= bb_upper:
            return -0.5 - min(0.5, (close - bb_upper) / (bb_upper * 0.01))  # Giảm điểm nếu giá càng cao trên dải trên
        else:
            # Điểm tỷ lệ với vị trí giá so với dải giữa
            relative_pos = (close - middle) / ((bb_upper - bb_lower) / 2)
            return -relative_pos * 0.4  # -0.4 đến 0.4 tùy thuộc vị trí

    def _calculate_volume_trend_score(self, volume: float, close: float, 
                                    prev_volume: Optional[float], prev_close: Optional[float]) -> float:
        """
        Tính điểm cho Volume Trend.
        
        Args:
            volume (float): Khối lượng hiện tại
            close (float): Giá đóng cửa hiện tại
            prev_volume (float, optional): Khối lượng trước đó
            prev_close (float, optional): Giá đóng cửa trước đó
            
        Returns:
            float: Điểm số (-1.0 đến 1.0)
        """
        if prev_volume is None or prev_close is None:
            return 0.0
        
        volume_change = volume / prev_volume if prev_volume > 0 else 1.0
        price_change = close - prev_close
        
        if volume_change > 1.5:  # Khối lượng tăng đáng kể
            if price_change > 0:
                return 0.5  # Khối lượng tăng + giá tăng = tín hiệu tích cực
            elif price_change < 0:
                return -0.5  # Khối lượng tăng + giá giảm = tín hiệu tiêu cực
        
        return 0.0

    def _calculate_adx_score(self, adx: float, di_plus: float, di_minus: float) -> float:
        """
        Tính điểm cho ADX.
        
        Args:
            adx (float): Giá trị ADX
            di_plus (float): Giá trị DI+
            di_minus (float): Giá trị DI-
            
        Returns:
            float: Điểm số (-1.0 đến 1.0)
        """
        if adx < 25:
            return 0.0  # Không có xu hướng rõ ràng
        
        if di_plus > di_minus:
            return 0.5  # Xu hướng tăng
        else:
            return -0.5  # Xu hướng giảm

    def _calculate_stochastic_score(self, stoch_k: float, stoch_d: float, 
                                  prev_stoch_k: Optional[float], prev_stoch_d: Optional[float]) -> float:
        """
        Tính điểm cho Stochastic.
        
        Args:
            stoch_k (float): Giá trị %K hiện tại
            stoch_d (float): Giá trị %D hiện tại
            prev_stoch_k (float, optional): Giá trị %K trước đó
            prev_stoch_d (float, optional): Giá trị %D trước đó
            
        Returns:
            float: Điểm số (-1.0 đến 1.0)
        """
        score = 0.0
        
        # Điểm cơ bản dựa trên giá trị
        if stoch_k < 20:
            score += 0.5
        elif stoch_k > 80:
            score -= 0.5
        
        # Điểm bổ sung dựa trên cắt nhau
        if prev_stoch_k is not None and prev_stoch_d is not None:
            if stoch_k > stoch_d and prev_stoch_k < prev_stoch_d:
                score += 0.5  # %K cắt lên %D
            elif stoch_k < stoch_d and prev_stoch_k > prev_stoch_d:
                score -= 0.5  # %K cắt xuống %D
        
        return max(-1.0, min(1.0, score))

    def _calculate_obv_score(self, obv: float, prev_obv: Optional[float]) -> float:
        """
        Tính điểm cho On-Balance Volume.
        
        Args:
            obv (float): Giá trị OBV hiện tại
            prev_obv (float, optional): Giá trị OBV trước đó
            
        Returns:
            float: Điểm số (-1.0 đến 1.0)
        """
        if prev_obv is None:
            return 0.0
        
        change = (obv - prev_obv) / abs(prev_obv) if prev_obv != 0 else 0
        
        if change > 0.01:  # OBV tăng đáng kể
            return 0.5
        elif change < -0.01:  # OBV giảm đáng kể
            return -0.5
        
        return 0.0

    def calculate_composite_score(self, dataframe: pd.DataFrame) -> Dict:
        """
        Tính toán điểm tổng hợp từ tất cả các chỉ báo.
        
        Args:
            dataframe (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            
        Returns:
            Dict: Thông tin về điểm tổng hợp
        """
        if dataframe.empty:
            logger.warning("DataFrame trống, không thể tính điểm tổng hợp")
            return {"score": 0.0, "individual_scores": {}, "weighted_scores": {}}
        
        individual_scores = self.calculate_individual_scores(dataframe)
        self._add_to_performance_history(individual_scores)
        
        if self.dynamic_weights:
            self._update_weights_based_on_performance()
        
        weighted_scores = {ind: individual_scores[ind] * self.weights[ind] 
                          for ind in individual_scores if ind in self.weights}
        
        composite_score = sum(weighted_scores.values())
        
        return {
            "score": composite_score,
            "individual_scores": individual_scores,
            "weighted_scores": weighted_scores
        }

    def _add_to_performance_history(self, scores: Dict[str, float]):
        """
        Thêm điểm hiện tại vào lịch sử hiệu suất.
        
        Args:
            scores (Dict[str, float]): Điểm cho từng chỉ báo
        """
        for indicator, score in scores.items():
            if indicator in self.performance_history:
                self.performance_history[indicator].append(score)
                # Giới hạn kích thước lịch sử
                if len(self.performance_history[indicator]) > self.lookback_period:
                    self.performance_history[indicator].pop(0)

    def _update_weights_based_on_performance(self):
        """
        Cập nhật trọng số dựa trên hiệu suất gần đây của các chỉ báo.
        """
        # Chỉ cập nhật nếu có đủ dữ liệu lịch sử
        if any(len(hist) < 5 for hist in self.performance_history.values()):
            return
        
        # Tính điểm hiệu suất cho mỗi chỉ báo
        performance_scores = {}
        for indicator, history in self.performance_history.items():
            if not history:
                performance_scores[indicator] = 0.0
                continue
            
            # Tính hiệu suất dựa trên độ nhất quán của tín hiệu
            consistency = np.std(history)
            if consistency == 0:
                performance_scores[indicator] = 0.5  # Tín hiệu nhất quán nhưng không thay đổi
            else:
                recent_trend = np.mean(history[-3:])  # Xu hướng gần đây
                performance_scores[indicator] = abs(recent_trend) / consistency
        
        # Chuẩn hóa
        total_score = sum(performance_scores.values())
        if total_score > 0:
            for indicator in performance_scores:
                self.weights[indicator] = performance_scores[indicator] / total_score
        else:
            # Nếu tổng điểm bằng 0, đặt trọng số bằng nhau
            for indicator in performance_scores:
                self.weights[indicator] = 1.0 / len(performance_scores)

    def get_trading_recommendation(self, dataframe: pd.DataFrame, lookback: int = 5) -> Dict:
        """
        Đưa ra khuyến nghị giao dịch dựa trên phân tích chỉ báo tổng hợp.
        
        Args:
            dataframe (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            lookback (int): Số chu kỳ phân tích ngược lại
            
        Returns:
            Dict: Khuyến nghị giao dịch chi tiết
        """
        if dataframe.empty or len(dataframe) < lookback:
            logger.warning(f"Không đủ dữ liệu cho khuyến nghị giao dịch, cần ít nhất {lookback} dòng")
            return {
                "signal": "neutral",
                "strength": 0.0,
                "reasoning": "Không đủ dữ liệu"
            }
        
        # Tính điểm tổng hợp cho các dòng gần đây
        recent_scores = []
        for i in range(min(lookback, len(dataframe))):
            if i < len(dataframe):
                score = self.calculate_composite_score(dataframe.iloc[-(i+1):])
                recent_scores.append(score['score'])
        
        # Đảo ngược để có thứ tự thời gian đúng
        recent_scores.reverse()
        
        # Tính điểm trung bình và xu hướng
        avg_score = np.mean(recent_scores)
        trend = np.polyfit(range(len(recent_scores)), recent_scores, 1)[0]
        
        # Xác định tín hiệu
        signal = "neutral"
        strength = abs(avg_score)
        reasoning = []
        
        if avg_score > 0.3:
            signal = "buy"
            reasoning.append(f"Điểm tổng hợp dương mạnh ({avg_score:.2f})")
        elif avg_score < -0.3:
            signal = "sell"
            reasoning.append(f"Điểm tổng hợp âm mạnh ({avg_score:.2f})")
        
        # Xem xét xu hướng
        if trend > 0.05:
            reasoning.append(f"Xu hướng điểm tăng ({trend:.2f})")
            if signal == "neutral":
                signal = "buy"
                strength = abs(trend) * 2
        elif trend < -0.05:
            reasoning.append(f"Xu hướng điểm giảm ({trend:.2f})")
            if signal == "neutral":
                signal = "sell"
                strength = abs(trend) * 2
        
        # Giới hạn strength trong khoảng [0, 1]
        strength = max(0.0, min(1.0, strength))
        
        # Tính toán thêm các yếu tố khác
        latest_scores = self.calculate_individual_scores(dataframe.iloc[-1:])
        
        # Thêm lý do chi tiết
        for indicator, score in latest_scores.items():
            if abs(score) >= 0.5:
                indicator_name = indicator.replace('_', ' ').upper()
                direction = "tích cực" if score > 0 else "tiêu cực"
                reasoning.append(f"{indicator_name} đưa ra tín hiệu {direction} ({score:.1f})")
        
        return {
            "signal": signal,
            "strength": strength,
            "reasoning": reasoning,
            "scores": {
                "latest": recent_scores[-1] if recent_scores else 0,
                "average": avg_score,
                "trend": trend
            },
            "individual_scores": latest_scores
        }