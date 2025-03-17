#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module phát hiện divergence RSI (Relative Strength Index)

Module này cung cấp các chức năng để phát hiện divergence (phân kỳ) giữa 
giá và chỉ báo RSI. Divergence thường là tín hiệu đảo chiều mạnh, đặc biệt
hữu ích trong thị trường đi ngang.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import logging
import os
from typing import Dict, List, Tuple, Optional, Union

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/divergence_detector.log')
    ]
)

logger = logging.getLogger('divergence_detector')

class RSIDivergenceDetector:
    """Lớp cung cấp các phương pháp phát hiện divergence RSI"""
    
    def __init__(self, rsi_period: int = 14, divergence_window: int = 30, 
                 min_pivot_distance: int = 5, peak_threshold: float = 0.8):
        """
        Khởi tạo detector với các tham số
        
        Args:
            rsi_period (int): Chu kỳ tính RSI
            divergence_window (int): Số thanh nến để tìm kiếm divergence
            min_pivot_distance (int): Khoảng cách tối thiểu giữa các điểm pivot
            peak_threshold (float): Ngưỡng để xác định đỉnh/đáy (0-1)
        """
        self.rsi_period = rsi_period
        self.divergence_window = divergence_window
        self.min_pivot_distance = min_pivot_distance
        self.peak_threshold = peak_threshold
        
        # Đảm bảo thư mục charts tồn tại
        os.makedirs('charts/divergence', exist_ok=True)
        
        logger.info(f"Khởi tạo RSIDivergenceDetector với period={rsi_period}, "
                   f"window={divergence_window}, min_distance={min_pivot_distance}")
    
    def calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """
        Tính RSI cho chuỗi giá
        
        Args:
            prices (pd.Series): Chuỗi giá đóng cửa
            
        Returns:
            pd.Series: Chuỗi giá trị RSI
        """
        delta = prices.diff()
        gain = delta.copy()
        loss = delta.copy()
        
        gain[gain < 0] = 0
        loss[loss > 0] = 0
        loss = abs(loss)
        
        avg_gain = gain.rolling(window=self.rsi_period).mean()
        avg_loss = loss.rolling(window=self.rsi_period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def find_pivots(self, data: pd.Series, is_high: bool = True) -> List[int]:
        """
        Tìm các điểm pivot (đỉnh/đáy cục bộ) trong chuỗi dữ liệu
        
        Args:
            data (pd.Series): Chuỗi dữ liệu (giá hoặc RSI)
            is_high (bool): True nếu tìm đỉnh, False nếu tìm đáy
            
        Returns:
            List[int]: Danh sách các chỉ số của điểm pivot
        """
        if len(data) < 2 * self.min_pivot_distance + 1:
            return []
        
        pivots = []
        
        for i in range(self.min_pivot_distance, len(data) - self.min_pivot_distance):
            window = data.iloc[i - self.min_pivot_distance:i + self.min_pivot_distance + 1]
            
            if is_high and data.iloc[i] == window.max():
                pivots.append(i)
            
            if not is_high and data.iloc[i] == window.min():
                pivots.append(i)
        
        # Lọc các pivot quá gần nhau
        filtered_pivots = []
        for pivot in pivots:
            if not filtered_pivots or pivot - filtered_pivots[-1] >= self.min_pivot_distance:
                filtered_pivots.append(pivot)
        
        return filtered_pivots
    
    def detect_divergence(self, df: pd.DataFrame, is_bullish: bool = True) -> Dict:
        """
        Phát hiện divergence giữa giá và RSI
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLC
            is_bullish (bool): True để tìm bullish divergence, False cho bearish
            
        Returns:
            Dict: Kết quả phát hiện, bao gồm các điểm divergence và mức độ tin cậy
        """
        # Tính RSI
        if 'rsi' not in df.columns:
            df['rsi'] = self.calculate_rsi(df['close'])
        
        # Chuẩn bị dữ liệu cho việc phát hiện
        recent_data = df.iloc[-self.divergence_window:].copy()
        
        # Tìm đỉnh/đáy
        if is_bullish:
            # Bullish divergence: giá tạo đáy thấp hơn, RSI tạo đáy cao hơn
            price_pivots = self.find_pivots(recent_data['close'], is_high=False)
            rsi_pivots = self.find_pivots(recent_data['rsi'], is_high=False)
        else:
            # Bearish divergence: giá tạo đỉnh cao hơn, RSI tạo đỉnh thấp hơn
            price_pivots = self.find_pivots(recent_data['close'], is_high=True)
            rsi_pivots = self.find_pivots(recent_data['rsi'], is_high=True)
        
        if len(price_pivots) < 2 or len(rsi_pivots) < 2:
            return {
                "detected": False,
                "confidence": 0,
                "price_pivots": [],
                "rsi_pivots": [],
                "divergence_type": "bullish" if is_bullish else "bearish"
            }
        
        # Lấy 2 pivot gần nhất
        price_pivot1, price_pivot2 = price_pivots[-2], price_pivots[-1]
        rsi_pivot1, rsi_pivot2 = rsi_pivots[-2], rsi_pivots[-1]
        
        # Kiểm tra divergence
        if is_bullish:
            price_divergence = recent_data['close'].iloc[price_pivot2] < recent_data['close'].iloc[price_pivot1]
            rsi_divergence = recent_data['rsi'].iloc[rsi_pivot2] > recent_data['rsi'].iloc[rsi_pivot1]
        else:
            price_divergence = recent_data['close'].iloc[price_pivot2] > recent_data['close'].iloc[price_pivot1]
            rsi_divergence = recent_data['rsi'].iloc[rsi_pivot2] < recent_data['rsi'].iloc[rsi_pivot1]
        
        # Tính độ tin cậy
        confidence = 0
        
        if price_divergence and rsi_divergence:
            # Tăng độ tin cậy dựa trên mức độ phân kỳ
            if is_bullish:
                price_diff = (recent_data['close'].iloc[price_pivot1] - recent_data['close'].iloc[price_pivot2]) / recent_data['close'].iloc[price_pivot1]
                rsi_diff = (recent_data['rsi'].iloc[rsi_pivot2] - recent_data['rsi'].iloc[rsi_pivot1]) / recent_data['rsi'].iloc[rsi_pivot1]
            else:
                price_diff = (recent_data['close'].iloc[price_pivot2] - recent_data['close'].iloc[price_pivot1]) / recent_data['close'].iloc[price_pivot1]
                rsi_diff = (recent_data['rsi'].iloc[rsi_pivot1] - recent_data['rsi'].iloc[rsi_pivot2]) / recent_data['rsi'].iloc[rsi_pivot1]
            
            # Chuẩn hóa về 0-1
            confidence = min(1.0, (price_diff + rsi_diff) / 0.1)  # 0.1 là ngưỡng điển hình
            
            # Thêm yếu tố thời gian
            time_factor = 1.0 - (price_pivot2 - price_pivot1) / self.divergence_window
            confidence *= (0.5 + 0.5 * time_factor)  # Time weight: 50%
            
            # Kiểm tra oversold/overbought để tăng độ tin cậy
            if is_bullish and recent_data['rsi'].iloc[rsi_pivot2] < 30:
                confidence *= 1.2  # Tăng 20% nếu RSI oversold
            elif not is_bullish and recent_data['rsi'].iloc[rsi_pivot2] > 70:
                confidence *= 1.2  # Tăng 20% nếu RSI overbought
        
        # Tạo kết quả
        result = {
            "detected": price_divergence and rsi_divergence,
            "confidence": confidence,
            "price_pivots": [price_pivot1, price_pivot2],
            "rsi_pivots": [rsi_pivot1, rsi_pivot2],
            "divergence_type": "bullish" if is_bullish else "bearish",
            "last_price": recent_data['close'].iloc[-1],
            "last_rsi": recent_data['rsi'].iloc[-1]
        }
        
        if result["detected"]:
            logger.info(f"Phát hiện {'bullish' if is_bullish else 'bearish'} "
                       f"divergence với độ tin cậy {confidence:.2f}")
        
        return result
    
    def visualize_divergence(self, df: pd.DataFrame, result: Dict, symbol: str, 
                            save_path: Optional[str] = None) -> str:
        """
        Tạo biểu đồ minh họa divergence
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLC
            result (Dict): Kết quả từ hàm detect_divergence
            symbol (str): Ký hiệu của coin
            save_path (str, optional): Đường dẫn lưu biểu đồ, tự tạo nếu None
            
        Returns:
            str: Đường dẫn đến biểu đồ đã lưu
        """
        if not result["detected"]:
            return ""
        
        # Chuẩn bị dữ liệu
        recent_data = df.iloc[-self.divergence_window:].copy()
        
        # Tạo biểu đồ
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), 
                                       gridspec_kw={'height_ratios': [2, 1]}, 
                                       sharex=True)
        
        # Biểu đồ giá
        ax1.plot(recent_data.index, recent_data['close'], color='blue', label='Price')
        
        # Đánh dấu các điểm pivot trên biểu đồ giá
        price_pivots = result["price_pivots"]
        price_pivot1, price_pivot2 = recent_data.index[price_pivots[0]], recent_data.index[price_pivots[1]]
        
        ax1.scatter([price_pivot1, price_pivot2], 
                   [recent_data['close'].iloc[price_pivots[0]], recent_data['close'].iloc[price_pivots[1]]],
                   color='red', s=100, marker='^' if result["divergence_type"] == "bearish" else 'v')
        
        ax1.plot([price_pivot1, price_pivot2], 
                [recent_data['close'].iloc[price_pivots[0]], recent_data['close'].iloc[price_pivots[1]]],
                'r--', lw=1)
        
        # Biểu đồ RSI
        ax2.plot(recent_data.index, recent_data['rsi'], color='purple', label='RSI')
        
        # Thêm các đường oversold/overbought
        ax2.axhline(y=30, color='green', linestyle='-', alpha=0.3)
        ax2.axhline(y=70, color='red', linestyle='-', alpha=0.3)
        
        # Đánh dấu các điểm pivot trên biểu đồ RSI
        rsi_pivots = result["rsi_pivots"]
        rsi_pivot1, rsi_pivot2 = recent_data.index[rsi_pivots[0]], recent_data.index[rsi_pivots[1]]
        
        ax2.scatter([rsi_pivot1, rsi_pivot2], 
                   [recent_data['rsi'].iloc[rsi_pivots[0]], recent_data['rsi'].iloc[rsi_pivots[1]]],
                   color='red', s=100, marker='^' if result["divergence_type"] == "bearish" else 'v')
        
        ax2.plot([rsi_pivot1, rsi_pivot2], 
                [recent_data['rsi'].iloc[rsi_pivots[0]], recent_data['rsi'].iloc[rsi_pivots[1]]],
                'r--', lw=1)
        
        # Hiển thị thông tin divergence
        title = f"{symbol} - {'Bullish' if result['divergence_type'] == 'bullish' else 'Bearish'} Divergence"
        subtitle = f"Confidence: {result['confidence']:.2f}, RSI: {result['last_rsi']:.1f}"
        ax1.set_title(f"{title}\n{subtitle}")
        
        ax1.set_ylabel("Price")
        ax2.set_ylabel("RSI")
        
        ax1.legend()
        ax2.legend()
        
        ax1.grid(True, alpha=0.3)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Lưu biểu đồ
        if save_path is None:
            save_path = f"charts/divergence/{symbol}_divergence_{result['divergence_type']}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        plt.savefig(save_path)
        plt.close()
        
        logger.info(f"Đã lưu biểu đồ divergence tại {save_path}")
        return save_path
    
    def get_trading_signal(self, df: pd.DataFrame) -> Dict:
        """
        Tạo tín hiệu giao dịch dựa trên phát hiện divergence
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLC
            
        Returns:
            Dict: Tín hiệu giao dịch với loại, độ tin cậy và hướng
        """
        # Phát hiện cả hai loại divergence
        bullish_result = self.detect_divergence(df, is_bullish=True)
        bearish_result = self.detect_divergence(df, is_bullish=False)
        
        # Xác định tín hiệu dựa trên độ tin cậy cao hơn
        if bullish_result["detected"] and not bearish_result["detected"]:
            signal_type = "buy"
            confidence = bullish_result["confidence"]
            divergence_data = bullish_result
        elif bearish_result["detected"] and not bullish_result["detected"]:
            signal_type = "sell"
            confidence = bearish_result["confidence"]
            divergence_data = bearish_result
        elif bullish_result["detected"] and bearish_result["detected"]:
            if bullish_result["confidence"] > bearish_result["confidence"]:
                signal_type = "buy"
                confidence = bullish_result["confidence"]
                divergence_data = bullish_result
            else:
                signal_type = "sell"
                confidence = bearish_result["confidence"]
                divergence_data = bearish_result
        else:
            signal_type = "neutral"
            confidence = 0
            divergence_data = {}
        
        return {
            "signal": signal_type,
            "confidence": confidence,
            "price": df['close'].iloc[-1] if len(df) > 0 else None,
            "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "divergence_data": divergence_data
        }

# Hàm demo
if __name__ == "__main__":
    import yfinance as yf
    
    try:
        # Tải dữ liệu BTC
        btc = yf.download("BTC-USD", period="3mo", interval="1d")
        
        # Đổi tên cột
        btc.columns = [c.lower() for c in btc.columns]
        
        # Khởi tạo detector
        detector = RSIDivergenceDetector()
        
        # Phát hiện divergence
        print("\n--- Phát hiện Bullish Divergence ---")
        bullish_result = detector.detect_divergence(btc, is_bullish=True)
        print(f"Phát hiện: {bullish_result['detected']}")
        print(f"Độ tin cậy: {bullish_result['confidence']:.2f}")
        
        if bullish_result["detected"]:
            chart_path = detector.visualize_divergence(btc, bullish_result, "BTC-USD")
            print(f"Đã lưu biểu đồ tại: {chart_path}")
        
        print("\n--- Phát hiện Bearish Divergence ---")
        bearish_result = detector.detect_divergence(btc, is_bullish=False)
        print(f"Phát hiện: {bearish_result['detected']}")
        print(f"Độ tin cậy: {bearish_result['confidence']:.2f}")
        
        if bearish_result["detected"]:
            chart_path = detector.visualize_divergence(btc, bearish_result, "BTC-USD")
            print(f"Đã lưu biểu đồ tại: {chart_path}")
        
        # Tạo tín hiệu giao dịch
        signal = detector.get_trading_signal(btc)
        print("\n--- Tín Hiệu Giao Dịch ---")
        print(f"Tín hiệu: {signal['signal']}")
        print(f"Độ tin cậy: {signal['confidence']:.2f}")
        print(f"Giá hiện tại: ${signal['price']:.2f}")
        
    except Exception as e:
        print(f"Lỗi khi chạy demo: {str(e)}")
        print("Bạn có thể cần cài đặt yfinance: pip install yfinance")