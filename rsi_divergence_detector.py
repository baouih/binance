#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RSI Divergence Detector

Module này giúp phát hiện sự phân kỳ (divergence) giữa giá và chỉ báo RSI,
đặc biệt hữu ích trong thị trường đi ngang.
"""

import os
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Union
from ta_lib_easy import ta

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/rsi_divergence.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('rsi_divergence')

class RSIDivergenceDetector:
    """
    Lớp phát hiện sự phân kỳ RSI
    """
    
    def __init__(self, rsi_period: int = 14, window_size: int = 30,
                min_pivot_distance: int = 5, peak_threshold: float = 0.8,
                confidence_threshold: float = 0.5):
        """
        Khởi tạo detector với các tham số
        
        Args:
            rsi_period (int): Chu kỳ RSI
            window_size (int): Cửa sổ dữ liệu để tìm kiếm phân kỳ
            min_pivot_distance (int): Khoảng cách tối thiểu giữa các điểm pivot
            peak_threshold (float): Ngưỡng để xác định các đỉnh/đáy của RSI (0-1)
            confidence_threshold (float): Ngưỡng độ tin cậy tối thiểu
        """
        self.rsi_period = rsi_period
        self.window_size = window_size
        self.min_pivot_distance = min_pivot_distance
        self.peak_threshold = peak_threshold
        self.confidence_threshold = confidence_threshold
        
        # Tạo thư mục đầu ra
        os.makedirs('charts', exist_ok=True)
        
        logger.info(f"Đã khởi tạo RSI Divergence Detector (RSI period: {rsi_period}, window: {window_size})")
    
    def find_pivots(self, data: np.ndarray, is_high: bool = True) -> List[int]:
        """
        Tìm các điểm pivot (đỉnh/đáy) trong dữ liệu
        
        Args:
            data (np.ndarray): Mảng dữ liệu
            is_high (bool): True cho đỉnh, False cho đáy
            
        Returns:
            List[int]: Danh sách các chỉ số của điểm pivot
        """
        # Tạo một mảng trống để lưu kết quả
        pivots = []
        
        # Lấy kích thước dữ liệu
        n = len(data)
        
        # Một khoảng cách tối thiểu giữa các điểm pivot
        min_distance = self.min_pivot_distance
        
        # Thuật toán tìm điểm pivot đơn giản
        for i in range(min_distance, n - min_distance):
            # Lấy cửa sổ dữ liệu xung quanh điểm
            window = data[i - min_distance:i + min_distance + 1]
            
            # Kiểm tra xem đây có phải là đỉnh/đáy không
            is_pivot = False
            
            if is_high:
                # Đây là đỉnh nếu điểm giữa cao hơn tất cả các điểm khác trong cửa sổ
                is_pivot = data[i] == np.max(window)
            else:
                # Đây là đáy nếu điểm giữa thấp hơn tất cả các điểm khác trong cửa sổ
                is_pivot = data[i] == np.min(window)
            
            # Thêm vào danh sách nếu là pivot
            if is_pivot:
                pivots.append(i)
        
        # Đảm bảo các điểm pivot đủ xa nhau
        filtered_pivots = []
        last_pivot = -min_distance * 2
        
        for pivot in pivots:
            if pivot - last_pivot >= min_distance:
                filtered_pivots.append(pivot)
                last_pivot = pivot
        
        return filtered_pivots
    
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Chuẩn bị dữ liệu cho phát hiện divergence
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLC
            
        Returns:
            pd.DataFrame: DataFrame đã được chuẩn bị
        """
        # Đảm bảo cột là chữ thường
        df.columns = [c.lower() for c in df.columns]
        
        # Sao chép DataFrame
        df_copy = df.copy()
        
        # Tính RSI nếu chưa có
        if 'rsi' not in df_copy.columns:
            df_copy['rsi'] = ta.RSI(df_copy['close'], timeperiod=self.rsi_period)
        
        return df_copy
    
    def detect_divergence(self, df: pd.DataFrame, is_bullish: bool = True) -> Dict:
        """
        Phát hiện phân kỳ RSI
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLC và RSI
            is_bullish (bool): True cho phân kỳ tăng, False cho phân kỳ giảm
            
        Returns:
            Dict: Kết quả phát hiện phân kỳ
        """
        # Chuẩn bị dữ liệu
        df = self.prepare_data(df)
        
        # Lấy dữ liệu gần đây theo cửa sổ
        window_df = df.iloc[-self.window_size:].copy()
        
        # Lấy dữ liệu giá và RSI
        prices = window_df['close'].values
        rsi_values = window_df['rsi'].values
        
        # Tìm các điểm pivot (đỉnh/đáy)
        if is_bullish:
            # Bullish divergence: tìm các đáy (đáy giá và đáy RSI)
            price_pivots = self.find_pivots(prices, is_high=False)
            rsi_pivots = self.find_pivots(rsi_values, is_high=False)
        else:
            # Bearish divergence: tìm các đỉnh (đỉnh giá và đỉnh RSI)
            price_pivots = self.find_pivots(prices, is_high=True)
            rsi_pivots = self.find_pivots(rsi_values, is_high=True)
        
        # Nếu không tìm thấy đủ pivot, trả về không phát hiện
        if len(price_pivots) < 2 or len(rsi_pivots) < 2:
            return {
                "detected": False,
                "type": "bullish" if is_bullish else "bearish",
                "confidence": 0,
                "price_pivots": [],
                "rsi_pivots": [],
                "divergence_start": None,
                "divergence_end": None
            }
        
        # Kiểm tra phân kỳ bằng cách so sánh 2 pivot gần nhất
        # Lấy 2 pivot gần nhất cho cả giá và RSI
        price_pivot1, price_pivot2 = price_pivots[-2], price_pivots[-1]
        rsi_pivot1, rsi_pivot2 = rsi_pivots[-2], rsi_pivots[-1]
        
        price_pivot1_value = prices[price_pivot1]
        price_pivot2_value = prices[price_pivot2]
        rsi_pivot1_value = rsi_values[rsi_pivot1]
        rsi_pivot2_value = rsi_values[rsi_pivot2]
        
        # Kiểm tra phân kỳ
        is_divergence = False
        confidence = 0
        
        if is_bullish:
            # Bullish divergence: Giá tạo đáy thấp hơn (giảm) nhưng RSI tạo đáy cao hơn (tăng)
            # Điều này là dấu hiệu sắp có xu hướng tăng
            price_lower = price_pivot2_value < price_pivot1_value
            rsi_higher = rsi_pivot2_value > rsi_pivot1_value
            
            if price_lower and rsi_higher:
                is_divergence = True
                
                # Tính độ tin cậy dựa trên mức độ phân kỳ
                price_diff = (price_pivot1_value - price_pivot2_value) / price_pivot1_value
                rsi_diff = (rsi_pivot2_value - rsi_pivot1_value) / rsi_pivot1_value
                
                # Kết hợp các yếu tố, chuẩn hóa để có giá trị từ 0-1
                confidence = min(1.0, (price_diff + rsi_diff) / 0.1)
                
                # Tăng độ tin cậy nếu RSI trong vùng oversold (<30)
                if rsi_pivot2_value < 30:
                    confidence *= 1.2
                    confidence = min(1.0, confidence)
                
        else:
            # Bearish divergence: Giá tạo đỉnh cao hơn (tăng) nhưng RSI tạo đỉnh thấp hơn (giảm)
            # Điều này là dấu hiệu sắp có xu hướng giảm
            price_higher = price_pivot2_value > price_pivot1_value
            rsi_lower = rsi_pivot2_value < rsi_pivot1_value
            
            if price_higher and rsi_lower:
                is_divergence = True
                
                # Tính độ tin cậy dựa trên mức độ phân kỳ
                price_diff = (price_pivot2_value - price_pivot1_value) / price_pivot1_value
                rsi_diff = (rsi_pivot1_value - rsi_pivot2_value) / rsi_pivot1_value
                
                # Kết hợp các yếu tố, chuẩn hóa để có giá trị từ 0-1
                confidence = min(1.0, (price_diff + rsi_diff) / 0.1)
                
                # Tăng độ tin cậy nếu RSI trong vùng overbought (>70)
                if rsi_pivot2_value > 70:
                    confidence *= 1.2
                    confidence = min(1.0, confidence)
        
        # Kiểm tra xem độ tin cậy có vượt ngưỡng không
        is_significant = confidence >= self.confidence_threshold
        
        # Kết quả
        result = {
            "detected": is_divergence and is_significant,
            "type": "bullish" if is_bullish else "bearish",
            "confidence": confidence,
            "price_pivots": [price_pivot1, price_pivot2],
            "rsi_pivots": [rsi_pivot1, rsi_pivot2],
            "price_pivot_values": [price_pivot1_value, price_pivot2_value],
            "rsi_pivot_values": [rsi_pivot1_value, rsi_pivot2_value],
            "divergence_start": window_df.index[min(price_pivot1, rsi_pivot1)],
            "divergence_end": window_df.index[max(price_pivot2, rsi_pivot2)]
        }
        
        if is_divergence and is_significant:
            logger.info(f"Đã phát hiện phân kỳ {'tăng' if is_bullish else 'giảm'} với độ tin cậy {confidence:.2f}")
        
        return result
    
    def get_trading_signal(self, df: pd.DataFrame) -> Dict:
        """
        Lấy tín hiệu giao dịch dựa trên phân kỳ RSI
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLC và RSI
            
        Returns:
            Dict: Tín hiệu giao dịch
        """
        # Phát hiện cả phân kỳ tăng và giảm
        bullish_result = self.detect_divergence(df, is_bullish=True)
        bearish_result = self.detect_divergence(df, is_bullish=False)
        
        # Kiểm tra phân kỳ nào mạnh hơn
        if bullish_result["detected"] and not bearish_result["detected"]:
            signal = "buy"
            confidence = bullish_result["confidence"]
        elif bearish_result["detected"] and not bullish_result["detected"]:
            signal = "sell"
            confidence = bearish_result["confidence"]
        elif bullish_result["detected"] and bearish_result["detected"]:
            # Cả hai phân kỳ cùng được phát hiện, chọn phân kỳ có độ tin cậy cao hơn
            if bullish_result["confidence"] > bearish_result["confidence"]:
                signal = "buy"
                confidence = bullish_result["confidence"]
            else:
                signal = "sell"
                confidence = bearish_result["confidence"]
        else:
            # Không phát hiện phân kỳ nào
            signal = "neutral"
            confidence = 0
        
        return {
            "signal": signal,
            "confidence": confidence,
            "bullish_detected": bullish_result["detected"],
            "bearish_detected": bearish_result["detected"],
            "bullish_confidence": bullish_result["confidence"],
            "bearish_confidence": bearish_result["confidence"]
        }
    
    def visualize_divergence(self, df: pd.DataFrame, divergence_result: Dict, symbol: str = '') -> str:
        """
        Trực quan hóa phân kỳ RSI
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLC và RSI
            divergence_result (Dict): Kết quả phát hiện phân kỳ
            symbol (str): Ký hiệu tiền tệ
            
        Returns:
            str: Đường dẫn đến biểu đồ đã lưu
        """
        # Kiểm tra xem có phát hiện phân kỳ không
        if not divergence_result["detected"]:
            logger.warning("Không có phân kỳ để trực quan hóa")
            return ""
        
        # Chuẩn bị dữ liệu
        df = self.prepare_data(df)
        
        # Lấy dữ liệu trong khoảng thời gian phân kỳ, mở rộng thêm
        start_idx = df.index.get_loc(divergence_result["divergence_start"]) - 5
        end_idx = df.index.get_loc(divergence_result["divergence_end"]) + 5
        
        start_idx = max(0, start_idx)
        end_idx = min(len(df), end_idx)
        
        plot_df = df.iloc[start_idx:end_idx].copy()
        
        # Tạo biểu đồ
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})
        
        # Biểu đồ 1: Giá
        ax1.plot(plot_df.index, plot_df['close'], label='Giá đóng cửa')
        
        # Biểu đồ 2: RSI
        ax2.plot(plot_df.index, plot_df['rsi'], label='RSI', color='purple')
        ax2.axhline(y=70, color='r', linestyle='--', alpha=0.3)
        ax2.axhline(y=30, color='g', linestyle='--', alpha=0.3)
        ax2.set_ylim(0, 100)
        
        # Lấy các điểm pivot từ kết quả phân kỳ
        price_pivots = divergence_result["price_pivots"]
        rsi_pivots = divergence_result["rsi_pivots"]
        
        # Lấy giá trị cụ thể của các pivot
        price_pivot_values = divergence_result["price_pivot_values"]
        rsi_pivot_values = divergence_result["rsi_pivot_values"]
        
        # Tính toán vị trí trên biểu đồ
        local_price_pivots = [df.index.get_loc(divergence_result["divergence_start"]) - start_idx,
                            df.index.get_loc(divergence_result["divergence_end"]) - start_idx]
        
        local_rsi_pivots = local_price_pivots  # Giả sử cùng vị trí trên trục x
        
        # Vẽ các điểm pivot trên biểu đồ giá
        ax1.scatter(plot_df.index[local_price_pivots], price_pivot_values, color='red', s=100)
        
        # Vẽ các điểm pivot trên biểu đồ RSI
        ax2.scatter(plot_df.index[local_rsi_pivots], rsi_pivot_values, color='red', s=100)
        
        # Vẽ đường nối các điểm pivot trên biểu đồ giá
        ax1.plot(plot_df.index[local_price_pivots], price_pivot_values, 'r--', alpha=0.7)
        
        # Vẽ đường nối các điểm pivot trên biểu đồ RSI
        ax2.plot(plot_df.index[local_rsi_pivots], rsi_pivot_values, 'r--', alpha=0.7)
        
        # Loại phân kỳ
        divergence_type = divergence_result["type"].capitalize()
        
        # Thêm tiêu đề
        ax1.set_title(f'{symbol} - {divergence_type} RSI Divergence (Conf: {divergence_result["confidence"]:.2f})', 
                    fontsize=14)
        
        ax1.set_ylabel('Giá')
        ax2.set_ylabel('RSI')
        
        # Thêm chú thích
        ax1.text(plot_df.index[0], min(plot_df['close']), 
                f"{divergence_type} Divergence\nConfidence: {divergence_result['confidence']:.2f}", 
                fontsize=12, color='red', 
                bbox=dict(facecolor='white', alpha=0.7))
        
        # Định dạng ngày tháng trên trục x
        for ax in [ax1, ax2]:
            ax.grid(True)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        
        # Lưu biểu đồ
        chart_path = f'charts/rsi_divergence_{divergence_type.lower()}_{symbol}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        plt.savefig(chart_path)
        plt.close()
        
        logger.info(f"Đã lưu biểu đồ phân kỳ: {chart_path}")
        
        return chart_path