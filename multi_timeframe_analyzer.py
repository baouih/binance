"""
Module phân tích đa khung thời gian (Multi-timeframe Analysis)

Module này cung cấp các công cụ để phân tích thị trường trên nhiều khung thời gian
khác nhau và tổng hợp kết quả để có tín hiệu giao dịch chính xác hơn.
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional
from app.binance_api import BinanceAPI
from app.data_processor import DataProcessor

# Thiết lập logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('multi_timeframe')

class MultiTimeframeAnalyzer:
    """
    Lớp phân tích đa khung thời gian, kết hợp tín hiệu từ nhiều khung 
    thời gian khác nhau để tăng độ tin cậy của tín hiệu giao dịch.
    """
    
    # Các khung thời gian mặc định để phân tích
    DEFAULT_TIMEFRAMES = ['15m', '1h', '4h', '1d']
    
    # Trọng số mặc định cho mỗi khung thời gian (càng dài càng quan trọng)
    DEFAULT_WEIGHTS = {
        '1m': 0.05,
        '5m': 0.10,
        '15m': 0.15,
        '30m': 0.20,
        '1h': 0.25,
        '4h': 0.30,
        '1d': 0.40,
        '1w': 0.50
    }
    
    def __init__(self, binance_api: BinanceAPI = None, data_processor: DataProcessor = None,
                 timeframes: List[str] = None, use_dynamic_weights: bool = True):
        """
        Khởi tạo bộ phân tích đa khung thời gian.
        
        Args:
            binance_api (BinanceAPI): Đối tượng API Binance để lấy dữ liệu
            data_processor (DataProcessor): Bộ xử lý dữ liệu
            timeframes (List[str]): Danh sách các khung thời gian cần phân tích
            use_dynamic_weights (bool): Sử dụng trọng số động dựa trên hiệu suất gần đây
        """
        self.binance_api = binance_api
        self.data_processor = data_processor
        self.timeframes = timeframes or self.DEFAULT_TIMEFRAMES
        self.use_dynamic_weights = use_dynamic_weights
        self.weights = self.DEFAULT_WEIGHTS.copy()
        
        # Lưu trữ hiệu suất gần đây của mỗi khung thời gian
        self.recent_performance = {tf: 1.0 for tf in self.timeframes}
        
        # Khởi tạo bộ nhớ cache cho dữ liệu
        self.data_cache = {}
        
        logger.info(f"Khởi tạo Bộ phân tích đa khung thời gian với các khung: {self.timeframes}")
    
    def get_data(self, symbol: str, timeframe: str, lookback_days: int = 30) -> pd.DataFrame:
        """
        Lấy và xử lý dữ liệu cho một khung thời gian cụ thể.
        
        Args:
            symbol (str): Mã cặp giao dịch (vd: BTCUSDT)
            timeframe (str): Khung thời gian (vd: 1h, 4h, 1d)
            lookback_days (int): Số ngày dữ liệu lịch sử cần lấy
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu giá và chỉ báo
        """
        # Kiểm tra cache
        cache_key = f"{symbol}_{timeframe}_{lookback_days}"
        if cache_key in self.data_cache:
            # Kiểm tra xem dữ liệu có cần cập nhật không
            last_update = self.data_cache[cache_key]['last_update']
            current_time = pd.Timestamp.now()
            # Nếu dữ liệu được cập nhật trong vòng 5 phút qua
            if (current_time - last_update).total_seconds() < 300:
                return self.data_cache[cache_key]['data']
        
        # Nếu không có trong cache hoặc cần cập nhật, lấy dữ liệu mới
        if self.data_processor and self.binance_api:
            df = self.data_processor.get_historical_data(symbol, timeframe, lookback_days=lookback_days)
            
            # Lưu vào cache
            self.data_cache[cache_key] = {
                'data': df,
                'last_update': pd.Timestamp.now()
            }
            
            return df
        else:
            logger.error(f"Không thể lấy dữ liệu vì thiếu data_processor hoặc binance_api")
            return None
    
    def analyze_rsi(self, symbol: str, lookback_days: int = 30, 
                   overbought: int = 70, oversold: int = 30) -> Dict[str, Dict]:
        """
        Phân tích RSI trên nhiều khung thời gian.
        
        Args:
            symbol (str): Mã cặp giao dịch
            lookback_days (int): Số ngày dữ liệu lịch sử
            overbought (int): Ngưỡng quá mua
            oversold (int): Ngưỡng quá bán
            
        Returns:
            Dict[str, Dict]: Kết quả phân tích RSI theo từng khung thời gian
        """
        results = {}
        
        for timeframe in self.timeframes:
            df = self.get_data(symbol, timeframe, lookback_days)
            if df is not None and not df.empty and 'rsi' in df.columns:
                current_rsi = df['rsi'].iloc[-1]
                signal = 0
                
                if current_rsi <= oversold:
                    signal = 1  # Tín hiệu mua
                elif current_rsi >= overbought:
                    signal = -1  # Tín hiệu bán
                
                results[timeframe] = {
                    'rsi': current_rsi,
                    'signal': signal,
                    'weight': self.weights.get(timeframe, 0.2)
                }
                
                logger.info(f"RSI trên khung {timeframe}: {current_rsi:.2f}, Tín hiệu: {signal}")
            else:
                logger.warning(f"Không thể phân tích RSI cho khung {timeframe}")
        
        return results
    
    def analyze_trend(self, symbol: str, lookback_days: int = 30) -> Dict[str, Dict]:
        """
        Phân tích xu hướng trên nhiều khung thời gian sử dụng EMA.
        
        Args:
            symbol (str): Mã cặp giao dịch
            lookback_days (int): Số ngày dữ liệu lịch sử
            
        Returns:
            Dict[str, Dict]: Kết quả phân tích xu hướng theo từng khung thời gian
        """
        results = {}
        
        for timeframe in self.timeframes:
            df = self.get_data(symbol, timeframe, lookback_days)
            if df is not None and not df.empty:
                # Đảm bảo có các chỉ báo EMA
                if 'ema20' not in df.columns:
                    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
                if 'ema50' not in df.columns:
                    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
                if 'ema200' not in df.columns:
                    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
                
                current_price = df['close'].iloc[-1]
                ema20 = df['ema20'].iloc[-1]
                ema50 = df['ema50'].iloc[-1]
                ema200 = df['ema200'].iloc[-1]
                
                # Xác định xu hướng
                if current_price > ema20 > ema50 > ema200:
                    trend = 2  # Xu hướng tăng mạnh
                elif current_price > ema20 > ema50:
                    trend = 1  # Xu hướng tăng
                elif current_price < ema20 < ema50 < ema200:
                    trend = -2  # Xu hướng giảm mạnh
                elif current_price < ema20 < ema50:
                    trend = -1  # Xu hướng giảm
                else:
                    trend = 0  # Đi ngang
                
                results[timeframe] = {
                    'trend': trend,
                    'ema20': ema20,
                    'ema50': ema50,
                    'ema200': ema200,
                    'close': current_price,
                    'weight': self.weights.get(timeframe, 0.2)
                }
                
                logger.info(f"Xu hướng trên khung {timeframe}: {trend} (Giá: {current_price:.2f}, EMA20: {ema20:.2f}, EMA50: {ema50:.2f})")
            else:
                logger.warning(f"Không thể phân tích xu hướng cho khung {timeframe}")
        
        return results
    
    def consolidate_signals(self, symbol: str, lookback_days: int = 30,
                           rsi_overbought: int = 70, rsi_oversold: int = 30) -> Dict:
        """
        Tổng hợp tín hiệu từ nhiều khung thời gian.
        
        Args:
            symbol (str): Mã cặp giao dịch
            lookback_days (int): Số ngày dữ liệu lịch sử
            rsi_overbought (int): Ngưỡng RSI quá mua
            rsi_oversold (int): Ngưỡng RSI quá bán
            
        Returns:
            Dict: Tổng hợp tín hiệu giao dịch
        """
        # Phân tích RSI và xu hướng
        rsi_analysis = self.analyze_rsi(symbol, lookback_days, rsi_overbought, rsi_oversold)
        trend_analysis = self.analyze_trend(symbol, lookback_days)
        
        # Tổng hợp tín hiệu
        rsi_signal_weighted = 0
        trend_signal_weighted = 0
        total_rsi_weight = 0
        total_trend_weight = 0
        
        # Tính tổng tín hiệu có trọng số cho RSI
        for timeframe, data in rsi_analysis.items():
            weight = data['weight']
            rsi_signal_weighted += data['signal'] * weight
            total_rsi_weight += weight
        
        # Tính tổng tín hiệu có trọng số cho xu hướng
        for timeframe, data in trend_analysis.items():
            weight = data['weight']
            # Chuyển đổi xu hướng thành tín hiệu
            trend_signal = 1 if data['trend'] > 0 else (-1 if data['trend'] < 0 else 0)
            trend_signal_weighted += trend_signal * weight
            total_trend_weight += weight
        
        # Tính trung bình có trọng số
        avg_rsi_signal = rsi_signal_weighted / total_rsi_weight if total_rsi_weight > 0 else 0
        avg_trend_signal = trend_signal_weighted / total_trend_weight if total_trend_weight > 0 else 0
        
        # Tính tổng hợp cuối cùng (70% xu hướng, 30% RSI)
        combined_signal_raw = (avg_trend_signal * 0.7) + (avg_rsi_signal * 0.3)
        
        # Chuyển đổi thành tín hiệu rõ ràng
        if combined_signal_raw > 0.5:
            combined_signal = 1  # Tín hiệu mua mạnh
        elif combined_signal_raw > 0.15:
            combined_signal = 0.5  # Tín hiệu mua nhẹ
        elif combined_signal_raw < -0.5:
            combined_signal = -1  # Tín hiệu bán mạnh
        elif combined_signal_raw < -0.15:
            combined_signal = -0.5  # Tín hiệu bán nhẹ
        else:
            combined_signal = 0  # Không có tín hiệu rõ ràng
        
        # Tính điểm tin cậy (0-100%)
        confidence = min(abs(combined_signal_raw) * 100, 100)
        
        # Quyết định kích thước vị thế dựa trên độ tin cậy
        position_size_factor = confidence / 100
        
        # Tạo kết quả tổng hợp
        result = {
            'signal': combined_signal,
            'confidence': confidence,
            'position_size_factor': position_size_factor,
            'rsi_analysis': rsi_analysis,
            'trend_analysis': trend_analysis,
            'raw_signal': combined_signal_raw
        }
        
        # Tạo mô tả tín hiệu
        signal_description = ""
        if combined_signal == 1:
            signal_description = "Tín hiệu MUA mạnh"
        elif combined_signal == 0.5:
            signal_description = "Tín hiệu MUA nhẹ"
        elif combined_signal == -1:
            signal_description = "Tín hiệu BÁN mạnh"
        elif combined_signal == -0.5:
            signal_description = "Tín hiệu BÁN nhẹ"
        else:
            signal_description = "Không có tín hiệu rõ ràng"
        
        result['signal_description'] = signal_description
        result['summary'] = f"{signal_description} với độ tin cậy {confidence:.1f}% (Hệ số vị thế: {position_size_factor:.2f})"
        
        logger.info(f"Tín hiệu tổng hợp cho {symbol}: {result['summary']}")
        return result
    
    def update_weights_based_on_performance(self, performance_by_timeframe: Dict[str, float]):
        """
        Cập nhật trọng số của các khung thời gian dựa trên hiệu suất gần đây.
        
        Args:
            performance_by_timeframe (Dict[str, float]): Hiệu suất của mỗi khung thời gian
        """
        if not self.use_dynamic_weights:
            return
        
        # Cập nhật hiệu suất gần đây
        for timeframe, performance in performance_by_timeframe.items():
            if timeframe in self.recent_performance:
                # Sử dụng trung bình động để cập nhật hiệu suất
                self.recent_performance[timeframe] = (
                    0.7 * self.recent_performance[timeframe] + 0.3 * performance
                )
        
        # Tính tổng hiệu suất
        total_performance = sum(self.recent_performance.values())
        
        # Cập nhật trọng số
        if total_performance > 0:
            for timeframe in self.recent_performance:
                # Đảm bảo trọng số tối thiểu 0.05 cho mỗi khung thời gian
                self.weights[timeframe] = max(
                    0.05, 
                    (self.recent_performance[timeframe] / total_performance) * len(self.recent_performance)
                )
        
        logger.info(f"Đã cập nhật trọng số cho các khung thời gian: {self.weights}")
    
    def get_optimal_entry_points(self, symbol: str, lookback_days: int = 30) -> Dict:
        """
        Xác định các điểm vào lệnh tối ưu dựa trên phân tích đa khung thời gian.
        
        Args:
            symbol (str): Mã cặp giao dịch
            lookback_days (int): Số ngày dữ liệu lịch sử
            
        Returns:
            Dict: Thông tin về các điểm vào lệnh tối ưu
        """
        # Lấy phân tích xu hướng
        trend_analysis = self.analyze_trend(symbol, lookback_days)
        
        # Tìm khung thời gian dài nhất
        longest_timeframe = self.timeframes[-1]
        timeframe_data = trend_analysis.get(longest_timeframe, {})
        
        # Khởi tạo kết quả
        result = {
            'entry_points': [],
            'avoid_zones': [],
            'current_price': None
        }
        
        # Lấy dữ liệu cho khung thời gian dài nhất
        df_long = self.get_data(symbol, longest_timeframe, lookback_days)
        if df_long is not None and not df_long.empty:
            current_price = df_long['close'].iloc[-1]
            result['current_price'] = current_price
            
            # Xác định các mức hỗ trợ/kháng cự chính
            pivots = self._find_pivot_points(df_long)
            
            # Thêm các mức này vào điểm vào lệnh tiềm năng
            for level, level_type in pivots:
                if level_type == 'support' and level < current_price:
                    # Mức hỗ trợ dưới giá hiện tại (tiềm năng điểm mua)
                    distance_pct = (current_price - level) / current_price * 100
                    if distance_pct <= 10:  # Trong phạm vi 10% của giá hiện tại
                        entry_point = {
                            'price': level,
                            'type': 'buy',
                            'strength': self._calculate_level_strength(level, df_long, 'support'),
                            'distance_pct': distance_pct
                        }
                        result['entry_points'].append(entry_point)
                elif level_type == 'resistance' and level > current_price:
                    # Mức kháng cự trên giá hiện tại (tiềm năng điểm bán)
                    distance_pct = (level - current_price) / current_price * 100
                    if distance_pct <= 10:  # Trong phạm vi 10% của giá hiện tại
                        entry_point = {
                            'price': level,
                            'type': 'sell',
                            'strength': self._calculate_level_strength(level, df_long, 'resistance'),
                            'distance_pct': distance_pct
                        }
                        result['entry_points'].append(entry_point)
        
        # Sắp xếp điểm vào lệnh theo độ mạnh
        result['entry_points'] = sorted(result['entry_points'], key=lambda x: x['strength'], reverse=True)
        
        # Lấy 3 điểm mạnh nhất
        result['best_entry_points'] = result['entry_points'][:3] if result['entry_points'] else []
        
        return result
    
    def _find_pivot_points(self, df: pd.DataFrame, window: int = 10) -> List[Tuple[float, str]]:
        """
        Tìm các điểm pivot (hỗ trợ/kháng cự) trong dữ liệu.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            window (int): Kích thước cửa sổ cho việc xác định pivot
            
        Returns:
            List[Tuple[float, str]]: Danh sách các điểm pivot và loại (hỗ trợ/kháng cự)
        """
        pivot_points = []
        
        # Tìm các đỉnh cục bộ
        for i in range(window, len(df) - window):
            # Kiểm tra xem đây có phải là đỉnh cục bộ không
            if all(df['high'].iloc[i] > df['high'].iloc[i-j] for j in range(1, window+1)) and \
               all(df['high'].iloc[i] > df['high'].iloc[i+j] for j in range(1, window+1)):
                pivot_points.append((df['high'].iloc[i], 'resistance'))
            
            # Kiểm tra xem đây có phải là đáy cục bộ không
            if all(df['low'].iloc[i] < df['low'].iloc[i-j] for j in range(1, window+1)) and \
               all(df['low'].iloc[i] < df['low'].iloc[i+j] for j in range(1, window+1)):
                pivot_points.append((df['low'].iloc[i], 'support'))
        
        return pivot_points
    
    def _calculate_level_strength(self, level: float, df: pd.DataFrame, level_type: str) -> float:
        """
        Tính toán độ mạnh của một mức hỗ trợ/kháng cự.
        
        Args:
            level (float): Giá trị của mức
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            level_type (str): 'support' hoặc 'resistance'
            
        Returns:
            float: Độ mạnh từ 0-100
        """
        # Xác định độ rộng của dải biến động
        price_range = df['high'].max() - df['low'].min()
        tolerance = price_range * 0.005  # 0.5% của dải giá
        
        # Đếm số lần giá chạm/phá vỡ mức này
        touch_count = 0
        break_count = 0
        
        for i in range(len(df)):
            if level_type == 'support':
                # Nếu giá chạm xuống mức hỗ trợ nhưng không phá
                if abs(df['low'].iloc[i] - level) <= tolerance and df['close'].iloc[i] > level:
                    touch_count += 1
                # Nếu giá phá vỡ mức hỗ trợ
                elif df['close'].iloc[i] < level - tolerance:
                    break_count += 1
            else:  # resistance
                # Nếu giá chạm lên mức kháng cự nhưng không phá
                if abs(df['high'].iloc[i] - level) <= tolerance and df['close'].iloc[i] < level:
                    touch_count += 1
                # Nếu giá phá vỡ mức kháng cự
                elif df['close'].iloc[i] > level + tolerance:
                    break_count += 1
        
        # Tính độ mạnh
        strength = min(100, (touch_count * 10) / (break_count + 1))
        
        return strength