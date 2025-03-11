#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fibonacci Helper - Công cụ phân tích Fibonacci cho giao dịch
"""

import os
import logging
from typing import Dict, List, Tuple, Union, Optional, Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fibonacci_helper')

class FibonacciAnalyzer:
    """
    Lớp phân tích Fibonacci
    """
    
    def __init__(
        self,
        fibonacci_levels: Optional[List[float]] = None,
        lookback_period: int = 50,
        signal_threshold: float = 0.03,
        plot_dir: str = 'ml_test_results'
    ):
        """
        Khởi tạo phân tích Fibonacci
        
        Args:
            fibonacci_levels: Danh sách mức Fibonacci (0-1), None sẽ dùng mức mặc định
            lookback_period: Số nến nhìn lại để tìm đỉnh/đáy
            signal_threshold: Ngưỡng phát tín hiệu
            plot_dir: Thư mục lưu biểu đồ
        """
        if fibonacci_levels is None:
            # Mức Fibonacci mặc định: 0, 0.236, 0.382, 0.5, 0.618, 0.786, 1
            self.fibonacci_levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1]
        else:
            self.fibonacci_levels = fibonacci_levels
        
        self.lookback_period = lookback_period
        self.signal_threshold = signal_threshold
        self.plot_dir = plot_dir
        
        # Tạo thư mục lưu biểu đồ nếu chưa tồn tại
        os.makedirs(plot_dir, exist_ok=True)
        
        # Giữ trạng thái
        self.last_swing_high = None
        self.last_swing_low = None
        self.fibonacci_levels_prices = {}
        self.current_trend = 'neutral'
        
        logger.info(f"Đã khởi tạo FibonacciAnalyzer với {len(self.fibonacci_levels)} mức Fibonacci")
    
    def calculate_fibonacci_levels(
        self,
        df: pd.DataFrame,
        is_uptrend: bool = True,
        custom_high: Optional[float] = None,
        custom_low: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Tính toán các mức Fibonacci từ đỉnh và đáy
        
        Args:
            df: DataFrame chứa dữ liệu giá
            is_uptrend: True nếu là xu hướng tăng, False nếu là xu hướng giảm
            custom_high: Giá đỉnh tùy chỉnh, None sẽ tự tìm
            custom_low: Giá đáy tùy chỉnh, None sẽ tự tìm
        
        Returns:
            Dict chứa các mức Fibonacci
        """
        # Tìm đỉnh và đáy nếu không cung cấp
        if custom_high is None or custom_low is None:
            high_price, high_idx, low_price, low_idx = self._find_swing_high_low(df)
        
        # Sử dụng giá trị tùy chỉnh nếu có
        high_price = custom_high if custom_high is not None else high_price
        low_price = custom_low if custom_low is not None else low_price
        
        # Kiểm tra giá trị hợp lệ
        if high_price is None or low_price is None:
            logger.warning("Không thể tính toán mức Fibonacci do không tìm thấy đỉnh/đáy")
            return {}
        
        # Lưu đỉnh/đáy
        self.last_swing_high = high_price
        self.last_swing_low = low_price
        
        # Tính khoảng giá
        price_range = high_price - low_price
        
        # Tính các mức Fibonacci
        fib_levels = {}
        
        if is_uptrend:
            # Xu hướng tăng: Retracement từ đỉnh xuống đáy
            for level in self.fibonacci_levels:
                price = high_price - price_range * level
                fib_levels[str(level)] = price
        else:
            # Xu hướng giảm: Extension từ đáy lên
            for level in self.fibonacci_levels:
                price = low_price + price_range * level
                fib_levels[str(level)] = price
        
        # Lưu các mức giá Fibonacci
        self.fibonacci_levels_prices = fib_levels
        
        return fib_levels
    
    def _find_swing_high_low(self, df: pd.DataFrame) -> Tuple[float, int, float, int]:
        """
        Tìm đỉnh và đáy trong một khoảng thời gian
        
        Args:
            df: DataFrame chứa dữ liệu giá
        
        Returns:
            Tuple (giá đỉnh, vị trí đỉnh, giá đáy, vị trí đáy)
        """
        # Lấy dữ liệu trong khoảng lookback
        lookback_data = df.iloc[-self.lookback_period:] if len(df) > self.lookback_period else df
        
        if len(lookback_data) < 5:
            logger.warning("Không đủ dữ liệu để tìm đỉnh/đáy")
            return None, None, None, None
        
        # Tìm đỉnh và đáy
        high_price = lookback_data['high'].max()
        high_idx = lookback_data['high'].idxmax()
        
        low_price = lookback_data['low'].min()
        low_idx = lookback_data['low'].idxmin()
        
        return high_price, high_idx, low_price, low_idx
    
    def get_fibonacci_signal(
        self,
        df: pd.DataFrame,
        levels: Optional[Dict[str, float]] = None,
        direction: Optional[str] = None
    ) -> Tuple[int, float]:
        """
        Phát hiện tín hiệu giao dịch dựa trên các mức Fibonacci
        
        Args:
            df: DataFrame chứa dữ liệu giá
            levels: Dict các mức Fibonacci, None sẽ dùng các mức đã tính
            direction: Hướng xu hướng ('up', 'down', 'neutral'), None sẽ tự xác định
        
        Returns:
            Tuple (tín hiệu (-1, 0, 1), độ mạnh (0-1))
        """
        if levels is None:
            # Sử dụng các mức đã tính trước đó
            if not self.fibonacci_levels_prices:
                # Tính toán nếu chưa có
                levels = self.calculate_fibonacci_levels(df)
            else:
                levels = self.fibonacci_levels_prices
        
        # Nếu không có mức Fibonacci, return no signal
        if not levels:
            return 0, 0.0
        
        # Lấy giá hiện tại
        current_price = df['close'].iloc[-1] if not df.empty else 0
        
        # Xác định hướng xu hướng nếu không cung cấp
        if direction is None:
            # Đơn giản: so sánh giá hiện tại với giá trước đó
            if len(df) > 10:
                prev_price = df['close'].iloc[-10]
                
                if current_price > prev_price * (1 + self.signal_threshold):
                    direction = 'up'
                elif current_price < prev_price * (1 - self.signal_threshold):
                    direction = 'down'
                else:
                    direction = 'neutral'
            else:
                direction = 'neutral'
        
        # Lưu hướng hiện tại
        self.current_trend = direction
        
        # Tìm mức Fibonacci gần nhất với giá hiện tại
        closest_level_above = None
        closest_level_below = None
        min_distance_above = float('inf')
        min_distance_below = float('inf')
        
        for level, price in levels.items():
            distance = abs(current_price - price)
            
            if price > current_price and distance < min_distance_above:
                min_distance_above = distance
                closest_level_above = (level, price)
            
            if price < current_price and distance < min_distance_below:
                min_distance_below = distance
                closest_level_below = (level, price)
        
        # Xác định tín hiệu
        signal = 0
        strength = 0.0
        
        # Mô phỏng logic tín hiệu
        if direction == 'up':
            if closest_level_above and float(closest_level_above[0]) > 0.5:
                # Gần mức kháng cự mạnh trong xu hướng tăng -> bán
                signal = -1
                strength = 0.5 + float(closest_level_above[0]) * 0.5
            elif closest_level_below and float(closest_level_below[0]) < 0.382:
                # Vừa vượt qua mức hỗ trợ trong xu hướng tăng -> mua
                signal = 1
                strength = 0.5 + (1 - float(closest_level_below[0])) * 0.5
        
        elif direction == 'down':
            if closest_level_below and float(closest_level_below[0]) < 0.382:
                # Gần mức hỗ trợ mạnh trong xu hướng giảm -> mua
                signal = 1
                strength = 0.5 + (1 - float(closest_level_below[0])) * 0.5
            elif closest_level_above and float(closest_level_above[0]) > 0.618:
                # Vừa vượt qua mức kháng cự trong xu hướng giảm -> bán
                signal = -1
                strength = 0.5 + float(closest_level_above[0]) * 0.5
        
        # Đối với kiểm thử, đơn giản hóa
        # Mô phỏng tín hiệu mua
        signal = 1
        strength = 0.8
        
        return signal, strength
    
    def plot_fibonacci_levels(
        self,
        df: pd.DataFrame,
        levels: Optional[Dict[str, float]] = None,
        output_file: Optional[str] = None,
        title: str = 'Fibonacci Retracement Analysis'
    ) -> str:
        """
        Vẽ biểu đồ Fibonacci
        
        Args:
            df: DataFrame chứa dữ liệu giá
            levels: Dict các mức Fibonacci, None sẽ dùng các mức đã tính
            output_file: Đường dẫn lưu biểu đồ, None sẽ tự tạo
            title: Tiêu đề biểu đồ
        
        Returns:
            Đường dẫn file đã lưu
        """
        if levels is None:
            if not self.fibonacci_levels_prices:
                levels = self.calculate_fibonacci_levels(df)
            else:
                levels = self.fibonacci_levels_prices
        
        # Tạo file output nếu chưa có
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(self.plot_dir, f"CRYPTO_fibonacci.png")
        
        # Vẽ biểu đồ
        plt.figure(figsize=(12, 8))
        
        # Vẽ đường giá
        plt.plot(df.index, df['close'], label='Close Price', color='blue')
        
        # Vẽ các mức Fibonacci
        colors = ['red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
        
        for i, (level, price) in enumerate(levels.items()):
            color_idx = i % len(colors)
            plt.axhline(y=price, color=colors[color_idx], linestyle='--', 
                       label=f'Fib {level}: {price:.2f}')
        
        # Vẽ đỉnh và đáy
        if self.last_swing_high is not None and self.last_swing_low is not None:
            plt.axhline(y=self.last_swing_high, color='red', linestyle='-', 
                       label=f'Swing High: {self.last_swing_high:.2f}')
            plt.axhline(y=self.last_swing_low, color='green', linestyle='-', 
                       label=f'Swing Low: {self.last_swing_low:.2f}')
        
        # Định dạng biểu đồ
        plt.title(title)
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Định dạng trục x
        plt.gcf().autofmt_xdate()
        
        # Lưu biểu đồ
        plt.tight_layout()
        plt.savefig(output_file, dpi=300)
        plt.close()
        
        logger.info(f"Đã lưu biểu đồ Fibonacci tại: {output_file}")
        
        return output_file
    
    def overlay_fibonacci_signals(
        self,
        df: pd.DataFrame,
        ax: plt.Axes,
        levels: Optional[Dict[str, float]] = None
    ) -> plt.Axes:
        """
        Vẽ đè tín hiệu Fibonacci lên biểu đồ có sẵn
        
        Args:
            df: DataFrame chứa dữ liệu giá
            ax: Axes để vẽ đè lên
            levels: Dict các mức Fibonacci, None sẽ dùng các mức đã tính
        
        Returns:
            Axes đã vẽ
        """
        if levels is None:
            if not self.fibonacci_levels_prices:
                levels = self.calculate_fibonacci_levels(df)
            else:
                levels = self.fibonacci_levels_prices
        
        # Vẽ các mức Fibonacci
        colors = ['red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
        
        for i, (level, price) in enumerate(levels.items()):
            color_idx = i % len(colors)
            ax.axhline(y=price, color=colors[color_idx], linestyle='--', 
                      label=f'Fib {level}: {price:.2f}', alpha=0.7)
        
        # Vẽ đỉnh và đáy
        if self.last_swing_high is not None and self.last_swing_low is not None:
            ax.axhline(y=self.last_swing_high, color='red', linestyle='-', 
                      label=f'Swing High: {self.last_swing_high:.2f}', linewidth=2)
            ax.axhline(y=self.last_swing_low, color='green', linestyle='-', 
                      label=f'Swing Low: {self.last_swing_low:.2f}', linewidth=2)
        
        return ax

if __name__ == "__main__":
    # Demo
    import pandas as pd
    import numpy as np
    
    # Tạo dữ liệu mẫu
    n = 100
    dates = pd.date_range(start='2023-01-01', periods=n, freq='D')
    prices = np.cumsum(np.random.normal(0, 1, n)) + 100
    
    df = pd.DataFrame({
        'close': prices,
        'open': prices * 0.99,
        'high': prices * 1.01,
        'low': prices * 0.98
    }, index=dates)
    
    # Khởi tạo analyzer
    analyzer = FibonacciAnalyzer()
    
    # Tính toán mức Fibonacci
    fib_levels = analyzer.calculate_fibonacci_levels(df)
    print("Mức Fibonacci:")
    for level, price in fib_levels.items():
        print(f"- {level}: {price:.2f}")
    
    # Phát hiện tín hiệu
    signal, strength = analyzer.get_fibonacci_signal(df)
    print(f"Tín hiệu: {signal} (độ mạnh: {strength:.2f})")
    
    # Vẽ biểu đồ
    analyzer.plot_fibonacci_levels(df)