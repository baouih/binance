"""
Module Chỉ báo tổng hợp (Composite Indicator)

Module này cung cấp các công cụ để tạo và sử dụng chỉ báo tổng hợp từ nhiều chỉ báo kỹ thuật
khác nhau, mang lại tín hiệu giao dịch có độ tin cậy cao hơn so với các chỉ báo đơn lẻ.
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional, Callable, Union

# Thiết lập logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('composite_indicator')

class CompositeIndicator:
    """
    Lớp Chỉ báo tổng hợp kết hợp nhiều chỉ báo kỹ thuật thành một
    hệ thống chấm điểm thống nhất để tạo tín hiệu giao dịch.
    """
    
    # Danh sách các chỉ báo được hỗ trợ và mô tả về cách tính điểm
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
        # Danh sách các chỉ báo được sử dụng
        self.indicators = indicators or ['rsi', 'macd', 'ema_cross', 'bbands']
        
        # Kiểm tra xem các chỉ báo có được hỗ trợ không
        for ind in self.indicators:
            if ind not in self.SUPPORTED_INDICATORS:
                logger.warning(f"Chỉ báo '{ind}' không được hỗ trợ hoặc chưa được thêm vào hệ thống")
        
        # Trọng số các chỉ báo
        if weights is None:
            # Thiết lập trọng số mặc định bằng nhau
            self.weights = {ind: 1.0 / len(self.indicators) for ind in self.indicators}
        else:
            # Chuẩn hóa trọng số
            total = sum(weights.values())
            self.weights = {k: v / total for k, v in weights.items()}
        
        # Cài đặt khác
        self.dynamic_weights = dynamic_weights
        self.lookback_period = lookback_period
        
        # Lưu trữ hiệu suất
        self.performance_history = {ind: [] for ind in self.indicators}
        
        logger.info(f"Khởi tạo Chỉ báo tổng hợp với các chỉ báo: {self.indicators}")
        logger.info(f"Trọng số ban đầu: {self.weights}")
    
    def calculate_individual_scores(self, dataframe: pd.DataFrame) -> Dict[str, float]:
        """
        Tính toán điểm số cho từng chỉ báo riêng lẻ.
        
        Args:
            dataframe (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            
        Returns:
            Dict[str, float]: Điểm số cho từng chỉ báo (-1.0 đến 1.0)
        """
        scores = {}
        
        # Kiểm tra dữ liệu
        if dataframe is None or dataframe.empty:
            logger.error("DataFrame trống hoặc None")
            return scores
        
        # Lấy dòng cuối cùng cho tính toán
        latest = dataframe.iloc[-1]
        prev = dataframe.iloc[-2] if len(dataframe) > 1 else None
        
        # Tính điểm cho RSI
        if 'rsi' in self.indicators and 'rsi' in dataframe.columns:
            rsi = latest['rsi']
            scores['rsi'] = self._calculate_rsi_score(rsi)
        
        # Tính điểm cho MACD
        if 'macd' in self.indicators and all(col in dataframe.columns for col in ['macd', 'macd_signal']):
            macd = latest['macd']
            macd_signal = latest['macd_signal']
            macd_hist = macd - macd_signal
            prev_macd_hist = None
            if prev is not None:
                prev_macd_hist = prev['macd'] - prev['macd_signal']
            scores['macd'] = self._calculate_macd_score(macd_hist, prev_macd_hist)
        
        # Tính điểm cho EMA Cross
        if 'ema_cross' in self.indicators and all(col in dataframe.columns for col in ['ema9', 'ema21']):
            ema_short = latest['ema9']
            ema_long = latest['ema21']
            prev_ema_short = prev['ema9'] if prev is not None else None
            prev_ema_long = prev['ema21'] if prev is not None else None
            scores['ema_cross'] = self._calculate_ema_cross_score(ema_short, ema_long, prev_ema_short, prev_ema_long)
        
        # Tính điểm cho Bollinger Bands
        if 'bbands' in self.indicators and all(col in dataframe.columns for col in ['bb_upper', 'bb_lower']):
            close = latest['close']
            bb_upper = latest['bb_upper']
            bb_lower = latest['bb_lower']
            scores['bbands'] = self._calculate_bbands_score(close, bb_upper, bb_lower)
        
        # Tính điểm cho Volume Trend
        if 'volume_trend' in self.indicators and all(col in dataframe.columns for col in ['volume']):
            volume = latest['volume']
            close = latest['close']
            prev_volume = prev['volume'] if prev is not None else None
            prev_close = prev['close'] if prev is not None else None
            scores['volume_trend'] = self._calculate_volume_trend_score(volume, close, prev_volume, prev_close)
        
        # Tính điểm cho ADX
        if 'adx' in self.indicators and all(col in dataframe.columns for col in ['adx', 'di_plus', 'di_minus']):
            adx = latest['adx']
            di_plus = latest['di_plus']
            di_minus = latest['di_minus']
            scores['adx'] = self._calculate_adx_score(adx, di_plus, di_minus)
        
        # Tính điểm cho Stochastic
        if 'stochastic' in self.indicators and all(col in dataframe.columns for col in ['stoch_k', 'stoch_d']):
            stoch_k = latest['stoch_k']
            stoch_d = latest['stoch_d']
            prev_stoch_k = prev['stoch_k'] if prev is not None else None
            prev_stoch_d = prev['stoch_d'] if prev is not None else None
            scores['stochastic'] = self._calculate_stochastic_score(stoch_k, stoch_d, prev_stoch_k, prev_stoch_d)
        
        # Tính điểm cho On-Balance Volume
        if 'obv' in self.indicators and 'obv' in dataframe.columns:
            obv = latest['obv']
            prev_obv = prev['obv'] if prev is not None else None
            scores['obv'] = self._calculate_obv_score(obv, prev_obv)
        
        # Ghi log điểm số
        for ind, score in scores.items():
            logger.info(f"Điểm {ind}: {score:.2f}")
        
        return scores
    
    def _calculate_rsi_score(self, rsi: float) -> float:
        """
        Tính điểm cho RSI.
        
        Args:
            rsi (float): Giá trị RSI hiện tại
            
        Returns:
            float: Điểm số (-1.0 đến 1.0)
        """
        if rsi <= 30:
            # Quá bán, tín hiệu mua
            return min(1.0, (30 - rsi) / 10 + 0.5)
        elif rsi >= 70:
            # Quá mua, tín hiệu bán
            return max(-1.0, -((rsi - 70) / 10 + 0.5))
        else:
            # Vùng trung tính
            # Chuẩn hóa về thang -0.4 đến 0.4
            return ((50 - rsi) / 20) * 0.4
    
    def _calculate_macd_score(self, macd_hist: float, prev_macd_hist: Optional[float]) -> float:
        """
        Tính điểm cho MACD.
        
        Args:
            macd_hist (float): MACD histogram hiện tại
            prev_macd_hist (float, optional): MACD histogram trước đó
            
        Returns:
            float: Điểm số (-1.0 đến 1.0)
        """
        # Tính điểm cơ bản dựa trên dấu của histogram
        base_score = 0.5 if macd_hist > 0 else -0.5
        
        # Nếu có dữ liệu trước đó, kiểm tra xem có xảy ra cắt không
        if prev_macd_hist is not None:
            if macd_hist > 0 and prev_macd_hist < 0:
                # MACD cắt lên, tín hiệu mua mạnh
                base_score = 1.0
            elif macd_hist < 0 and prev_macd_hist > 0:
                # MACD cắt xuống, tín hiệu bán mạnh
                base_score = -1.0
            else:
                # Điều chỉnh điểm theo độ dốc của histogram
                # Nếu histogram đang tăng (giảm giá trị âm hoặc tăng giá trị dương)
                if macd_hist > prev_macd_hist:
                    base_score += 0.2  # Tăng điểm
                # Nếu histogram đang giảm (tăng giá trị âm hoặc giảm giá trị dương)
                else:
                    base_score -= 0.2  # Giảm điểm
        
        # Đảm bảo điểm nằm trong khoảng -1.0 đến 1.0
        return max(-1.0, min(1.0, base_score))
    
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
        # Tính điểm cơ bản dựa trên vị trí tương đối
        base_score = 0.5 if ema_short > ema_long else -0.5
        
        # Nếu có dữ liệu trước đó, kiểm tra xem có xảy ra cắt không
        if prev_ema_short is not None and prev_ema_long is not None:
            if ema_short > ema_long and prev_ema_short < prev_ema_long:
                # EMA ngắn cắt lên EMA dài, tín hiệu mua mạnh
                base_score = 1.0
            elif ema_short < ema_long and prev_ema_short > prev_ema_long:
                # EMA ngắn cắt xuống EMA dài, tín hiệu bán mạnh
                base_score = -1.0
            else:
                # Điều chỉnh điểm theo khoảng cách giữa hai EMA
                # Tính khoảng cách tương đối
                distance = (ema_short - ema_long) / ema_long
                if distance > 0:
                    # EMA ngắn trên EMA dài
                    base_score = min(1.0, 0.5 + distance * 10)  # Giới hạn ở 1.0
                else:
                    # EMA ngắn dưới EMA dài
                    base_score = max(-1.0, -0.5 + distance * 10)  # Giới hạn ở -1.0
        
        # Đảm bảo điểm nằm trong khoảng -1.0 đến 1.0
        return max(-1.0, min(1.0, base_score))
    
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
        # Tính vị trí tương đối trong dải Bollinger (0 = dải dưới, 1 = dải trên)
        bb_range = bb_upper - bb_lower
        if bb_range == 0:  # Tránh chia cho 0
            return 0.0
        
        relative_position = (close - bb_lower) / bb_range
        
        # Ánh xạ vị trí tương đối vào thang điểm
        if relative_position <= 0.2:
            # Gần/dưới dải dưới, tín hiệu mua
            return 0.8  # Mua vừa phải
        elif relative_position >= 0.8:
            # Gần/trên dải trên, tín hiệu bán
            return -0.8  # Bán vừa phải
        else:
            # Trong dải, ánh xạ tuyến tính từ 0.5 (trung tâm) ra hai bên
            return 0.4 - (relative_position - 0.5) * 1.6
    
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
        
        # Tính thay đổi khối lượng và giá
        volume_change = volume / prev_volume - 1
        price_change = close / prev_close - 1
        
        # Tính điểm dựa trên mối quan hệ giữa khối lượng và giá
        if abs(volume_change) < 0.05:
            # Khối lượng ổn định, điểm thấp
            return 0.0
        
        if price_change > 0 and volume_change > 0:
            # Giá tăng với khối lượng tăng, tín hiệu mua
            return min(1.0, volume_change)
        elif price_change < 0 and volume_change > 0:
            # Giá giảm với khối lượng tăng, tín hiệu bán
            return max(-1.0, -volume_change)
        elif price_change > 0 and volume_change < 0:
            # Giá tăng với khối lượng giảm, tín hiệu yếu
            return 0.2
        else:
            # Giá giảm với khối lượng giảm, tín hiệu yếu
            return -0.2
    
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
        # ADX < 20: thị trường không có xu hướng rõ ràng
        if adx < 20:
            return 0.0
        
        # ADX > 20: thị trường có xu hướng, 
        # hướng phụ thuộc vào DI+ và DI-
        if di_plus > di_minus:
            # DI+ > DI-: xu hướng tăng
            strength = min(1.0, adx / 50)  # Chuẩn hóa về thang 0-1
            return strength * 0.8  # Giới hạn ở 0.8 vì ADX không xác định hướng chính xác
        else:
            # DI+ < DI-: xu hướng giảm
            strength = min(1.0, adx / 50)  # Chuẩn hóa về thang 0-1
            return -strength * 0.8  # Giới hạn ở -0.8
    
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
        # Tính điểm cơ bản dựa trên vùng quá mua/quá bán
        if stoch_k < 20:
            # Vùng quá bán, tín hiệu mua
            base_score = 0.6
        elif stoch_k > 80:
            # Vùng quá mua, tín hiệu bán
            base_score = -0.6
        else:
            # Vùng trung tính
            base_score = 0.0
        
        # Nếu có dữ liệu trước đó, kiểm tra xem có xảy ra cắt không
        if prev_stoch_k is not None and prev_stoch_d is not None:
            if stoch_k > stoch_d and prev_stoch_k < prev_stoch_d:
                # %K cắt lên %D, tăng điểm
                base_score += 0.4
            elif stoch_k < stoch_d and prev_stoch_k > prev_stoch_d:
                # %K cắt xuống %D, giảm điểm
                base_score -= 0.4
        
        # Đảm bảo điểm nằm trong khoảng -1.0 đến 1.0
        return max(-1.0, min(1.0, base_score))
    
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
        
        # Tính thay đổi OBV
        obv_change = obv - prev_obv
        
        # Tính điểm dựa trên thay đổi
        if obv_change > 0:
            # OBV tăng, tín hiệu mua
            return min(0.5, obv_change / prev_obv * 10)  # Giới hạn ở 0.5
        else:
            # OBV giảm, tín hiệu bán
            return max(-0.5, obv_change / prev_obv * 10)  # Giới hạn ở -0.5
    
    def calculate_composite_score(self, dataframe: pd.DataFrame) -> Dict:
        """
        Tính toán điểm tổng hợp từ tất cả các chỉ báo.
        
        Args:
            dataframe (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            
        Returns:
            Dict: Thông tin về điểm tổng hợp
        """
        # Tính điểm cho từng chỉ báo
        individual_scores = self.calculate_individual_scores(dataframe)
        
        # Tính điểm tổng hợp có trọng số
        weighted_sum = 0
        total_weight = 0
        weighted_scores = {}
        
        for indicator, score in individual_scores.items():
            weight = self.weights.get(indicator, 0)
            weighted_score = score * weight
            weighted_scores[indicator] = weighted_score
            weighted_sum += weighted_score
            total_weight += weight
        
        # Nếu không có chỉ báo hoặc trọng số là 0, trả về 0
        if total_weight == 0:
            composite_score = 0
        else:
            composite_score = weighted_sum / total_weight
        
        # Xác định tín hiệu dựa trên điểm tổng hợp
        if composite_score >= 0.5:
            signal = 1  # MUA mạnh
        elif 0.2 <= composite_score < 0.5:
            signal = 0.5  # MUA nhẹ
        elif -0.2 <= composite_score < 0.2:
            signal = 0  # KHÔNG HÀNH ĐỘNG
        elif -0.5 <= composite_score < -0.2:
            signal = -0.5  # BÁN nhẹ
        else:
            signal = -1  # BÁN mạnh
        
        # Tính điểm tin cậy (0-100%)
        confidence = min(abs(composite_score) * 100, 100)
        
        # Tạo mô tả tín hiệu
        signal_description = ""
        if signal == 1:
            signal_description = "MUA mạnh"
        elif signal == 0.5:
            signal_description = "MUA nhẹ"
        elif signal == 0:
            signal_description = "KHÔNG HÀNH ĐỘNG"
        elif signal == -0.5:
            signal_description = "BÁN nhẹ"
        else:
            signal_description = "BÁN mạnh"
        
        # Tạo kết quả
        result = {
            'composite_score': composite_score,
            'signal': signal,
            'confidence': confidence,
            'individual_scores': individual_scores,
            'weighted_scores': weighted_scores,
            'signal_description': signal_description,
            'summary': f"{signal_description} với độ tin cậy {confidence:.1f}%"
        }
        
        logger.info(f"Điểm tổng hợp: {composite_score:.2f} -> {result['summary']}")
        
        # Cập nhật hiệu suất để điều chỉnh trọng số nếu cần
        if self.dynamic_weights:
            self._add_to_performance_history(individual_scores)
            self._update_weights_based_on_performance()
        
        return result
    
    def _add_to_performance_history(self, scores: Dict[str, float]):
        """
        Thêm điểm hiện tại vào lịch sử hiệu suất.
        
        Args:
            scores (Dict[str, float]): Điểm cho từng chỉ báo
        """
        for indicator, score in scores.items():
            if indicator in self.performance_history:
                # Chỉ giữ số lượng bản ghi theo lookback_period
                if len(self.performance_history[indicator]) >= self.lookback_period:
                    self.performance_history[indicator].pop(0)
                self.performance_history[indicator].append(score)
    
    def _update_weights_based_on_performance(self):
        """
        Cập nhật trọng số dựa trên hiệu suất gần đây của các chỉ báo.
        """
        # Tính chỉ số hiệu suất cho mỗi chỉ báo
        # Đo dựa trên độ nhất quán của tín hiệu (ít thay đổi chiều hướng)
        performance_scores = {}
        
        for indicator, history in self.performance_history.items():
            if len(history) < 2:
                performance_scores[indicator] = 1.0  # Mặc định
                continue
                
            # Đếm số lần thay đổi dấu
            sign_changes = 0
            for i in range(1, len(history)):
                if (history[i] > 0 and history[i-1] < 0) or (history[i] < 0 and history[i-1] > 0):
                    sign_changes += 1
            
            # Tính hiệu suất dựa trên độ ổn định
            if len(history) > 1:
                stability = 1 - (sign_changes / (len(history) - 1))
            else:
                stability = 1.0
                
            # Tính hiệu suất dựa trên độ mạnh của tín hiệu
            avg_strength = sum(abs(s) for s in history) / len(history)
            
            # Tính điểm hiệu suất tổng hợp
            # 70% độ ổn định + 30% độ mạnh
            performance_scores[indicator] = stability * 0.7 + avg_strength * 0.3
        
        # Chuẩn hóa điểm hiệu suất
        total_performance = sum(performance_scores.values())
        if total_performance > 0:
            for indicator in performance_scores:
                # Đảm bảo mỗi chỉ báo có trọng số tối thiểu 0.1
                self.weights[indicator] = max(0.1, performance_scores[indicator] / total_performance)
            
            # Chuẩn hóa lại để tổng = 1.0
            total_weight = sum(self.weights.values())
            self.weights = {k: v / total_weight for k, v in self.weights.items()}
            
            logger.info(f"Đã cập nhật trọng số dựa trên hiệu suất: {self.weights}")
    
    def get_trading_recommendation(self, dataframe: pd.DataFrame, lookback: int = 5) -> Dict:
        """
        Đưa ra khuyến nghị giao dịch dựa trên phân tích chỉ báo tổng hợp.
        
        Args:
            dataframe (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            lookback (int): Số chu kỳ phân tích ngược lại
            
        Returns:
            Dict: Khuyến nghị giao dịch chi tiết
        """
        # Kiểm tra dữ liệu
        if dataframe is None or len(dataframe) < lookback + 1:
            logger.error(f"Không đủ dữ liệu để phân tích (cần ít nhất {lookback + 1} dòng)")
            return {"error": "Không đủ dữ liệu"}
        
        # Tính điểm hiện tại
        current_result = self.calculate_composite_score(dataframe)
        
        # Tính các điểm trước đó để xác định xu hướng của chỉ báo
        historical_scores = []
        for i in range(1, min(lookback + 1, len(dataframe))):
            historical_df = dataframe.iloc[:-i]
            if len(historical_df) > 0:
                historical_result = self.calculate_composite_score(historical_df)
                historical_scores.append(historical_result['composite_score'])
        
        # Xác định xu hướng của điểm tổng hợp
        score_trend = "đi ngang"
        if len(historical_scores) > 0:
            avg_hist_score = sum(historical_scores) / len(historical_scores)
            if current_result['composite_score'] > avg_hist_score + 0.2:
                score_trend = "tăng"
            elif current_result['composite_score'] < avg_hist_score - 0.2:
                score_trend = "giảm"
        
        # Dịch tóm tắt
        signal_dict = {
            1: "MUA mạnh",
            0.5: "MUA nhẹ",
            0: "KHÔNG HÀNH ĐỘNG",
            -0.5: "BÁN nhẹ",
            -1: "BÁN mạnh"
        }
        
        # Tạo khuyến nghị chi tiết
        current_price = dataframe['close'].iloc[-1] if 'close' in dataframe.columns else None
        
        recommendation = {
            'signal': current_result['signal'],
            'signal_text': signal_dict.get(current_result['signal'], "KHÔNG HÀNH ĐỘNG"),
            'confidence': current_result['confidence'],
            'composite_score': current_result['composite_score'],
            'score_trend': score_trend,
            'price': current_price,
            'individual_signals': {
                ind: {'score': score, 'weighted_score': current_result['weighted_scores'].get(ind, 0)}
                for ind, score in current_result['individual_scores'].items()
            },
            'description': f"{current_result['signal_description']} với độ tin cậy {current_result['confidence']:.1f}%. "
                        f"Điểm tổng hợp {current_result['composite_score']:.2f} đang có xu hướng {score_trend}."
        }
        
        # Tạo chi tiết khuyến nghị:
        if current_result['signal'] >= 0.5:
            recommendation['action'] = "MUA"
            if current_price is not None:
                # Tính toán điểm mục tiêu lợi nhuận và dừng lỗ
                take_profit = current_price * (1 + 0.02 * current_result['confidence'] / 100)
                stop_loss = current_price * (1 - 0.01 * current_result['confidence'] / 100)
                recommendation['take_profit'] = take_profit
                recommendation['stop_loss'] = stop_loss
                recommendation['action_details'] = (
                    f"MUA tại {current_price:.2f}, Mục tiêu: {take_profit:.2f}, "
                    f"Dừng lỗ: {stop_loss:.2f}, Tỷ lệ RR: "
                    f"{(take_profit - current_price) / (current_price - stop_loss):.2f}"
                )
        elif current_result['signal'] <= -0.5:
            recommendation['action'] = "BÁN"
            if current_price is not None:
                # Tính toán điểm mục tiêu lợi nhuận và dừng lỗ
                take_profit = current_price * (1 - 0.02 * current_result['confidence'] / 100)
                stop_loss = current_price * (1 + 0.01 * current_result['confidence'] / 100)
                recommendation['take_profit'] = take_profit
                recommendation['stop_loss'] = stop_loss
                recommendation['action_details'] = (
                    f"BÁN tại {current_price:.2f}, Mục tiêu: {take_profit:.2f}, "
                    f"Dừng lỗ: {stop_loss:.2f}, Tỷ lệ RR: "
                    f"{(current_price - take_profit) / (stop_loss - current_price):.2f}"
                )
        else:
            recommendation['action'] = "CHỜ ĐỢI"
            recommendation['action_details'] = "Không có tín hiệu rõ ràng, tiếp tục theo dõi thị trường."
        
        logger.info(f"Khuyến nghị: {recommendation['action']} - {recommendation['action_details']}")
        
        return recommendation