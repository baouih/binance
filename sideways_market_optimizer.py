#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module tối ưu hóa chiến lược cho thị trường sideway

Mô-đun này cung cấp các chức năng phát hiện và tối ưu hóa giao dịch trong
môi trường thị trường sideway. Nó sử dụng các chỉ báo đặc biệt cho thị trường
không có xu hướng rõ ràng và điều chỉnh chiến lược phù hợp.
"""

import os
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional, Union
import json
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/sideways_optimizer.log')
    ]
)

logger = logging.getLogger('sideways_optimizer')

class SidewaysMarketOptimizer:
    """
    Lớp cung cấp các phương pháp để phát hiện và tối ưu hóa giao dịch trong thị trường sideway
    """
    
    def __init__(self, config_path: str = 'configs/sideways_config.json'):
        """
        Khởi tạo optimizer với cấu hình
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
        """
        self.config = self._load_config(config_path)
        self.is_sideways = False
        self.sideways_score = 0
        self.volatility_threshold = self.config.get('volatility_threshold', 0.5)
        self.bollinger_squeeze_threshold = self.config.get('bollinger_squeeze_threshold', 0.1)
        self.keltner_factor = self.config.get('keltner_factor', 1.5)
        self.adx_threshold = self.config.get('adx_threshold', 25)
        self.position_size_reduction = self.config.get('position_size_reduction', 0.5)
        
        # Đảm bảo thư mục đầu ra tồn tại
        os.makedirs('charts/sideways_analysis', exist_ok=True)
        logger.info("Đã khởi tạo SidewaysMarketOptimizer")
        
    def _load_config(self, config_path: str) -> Dict:
        """
        Tải cấu hình từ file JSON
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
            
        Returns:
            Dict: Cấu hình đã tải
        """
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
            else:
                # Cấu hình mặc định nếu không tìm thấy file
                default_config = {
                    "volatility_threshold": 0.5,
                    "bollinger_squeeze_threshold": 0.1,
                    "keltner_factor": 1.5,
                    "adx_threshold": 25,
                    "position_size_reduction": 0.5,
                    "mean_reversion_enabled": True,
                    "squeeze_detection_enabled": True,
                    "volatility_filter_enabled": True
                }
                
                # Tạo thư mục configs nếu chưa tồn tại
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                
                # Lưu cấu hình mặc định
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=4)
                
                logger.info(f"Đã tạo file cấu hình mặc định tại {config_path}")
                return default_config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
            return {}
    
    def detect_sideways_market(self, df: pd.DataFrame, window: int = 20) -> bool:
        """
        Phát hiện thị trường sideway dựa trên nhiều chỉ báo
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            window (int): Cửa sổ thời gian cho tính toán
            
        Returns:
            bool: True nếu phát hiện thị trường sideway
        """
        if len(df) < window * 2:
            logger.warning("Không đủ dữ liệu để phát hiện thị trường sideway")
            return False
        
        scores = []
        
        # 1. Kiểm tra biên độ dao động thấp
        if self.config.get('volatility_filter_enabled', True):
            atr = self._calculate_atr(df, window)
            avg_price = df['close'].iloc[-window:].mean()
            volatility_ratio = atr / avg_price
            
            volatility_score = 1 - min(volatility_ratio / self.volatility_threshold, 1)
            scores.append(volatility_score)
            
            logger.debug(f"Volatility score: {volatility_score:.2f} (ATR/AvgPrice: {volatility_ratio:.4f})")
        
        # 2. Kiểm tra Bollinger Squeeze
        if self.config.get('squeeze_detection_enabled', True):
            bb_squeeze = self._detect_bollinger_squeeze(df, window)
            scores.append(bb_squeeze)
            
            logger.debug(f"Bollinger squeeze score: {bb_squeeze:.2f}")
        
        # 3. Kiểm tra ADX thấp (không có xu hướng)
        adx = self._calculate_adx(df, window)
        adx_score = 1 - min(adx / self.adx_threshold, 1)
        scores.append(adx_score)
        
        logger.debug(f"ADX score: {adx_score:.2f} (ADX: {adx:.2f})")
        
        # Tính điểm trung bình
        self.sideways_score = sum(scores) / len(scores)
        self.is_sideways = self.sideways_score > 0.6
        
        logger.info(f"Sideways market score: {self.sideways_score:.2f}, Is sideways: {self.is_sideways}")
        return self.is_sideways
    
    def _calculate_atr(self, df: pd.DataFrame, window: int = 14) -> float:
        """
        Tính chỉ số Average True Range (ATR)
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLC
            window (int): Cửa sổ tính toán
            
        Returns:
            float: Giá trị ATR
        """
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        tr1 = np.abs(high[1:] - low[1:])
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        
        tr = np.vstack([tr1, tr2, tr3]).max(axis=0)
        atr = np.mean(tr[-window:])
        
        return atr
    
    def _detect_bollinger_squeeze(self, df: pd.DataFrame, window: int = 20) -> float:
        """
        Phát hiện Bollinger Squeeze (khi Bollinger Bands co lại hẹp hơn Keltner Channels)
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLC
            window (int): Cửa sổ tính toán
            
        Returns:
            float: Điểm squeeze (0-1), 1 là squeeze mạnh nhất
        """
        # Tính Bollinger Bands
        rolling_mean = df['close'].rolling(window=window).mean()
        rolling_std = df['close'].rolling(window=window).std()
        
        # Tính ATR cho Keltner Channels
        atr = self._calculate_atr(df, window)
        
        # Tính độ rộng của Bollinger Bands và Keltner Channels
        bb_width = 2 * rolling_std.iloc[-1]
        kc_width = 2 * self.keltner_factor * atr
        
        # Tính tỷ lệ
        ratio = bb_width / kc_width if kc_width > 0 else 1
        
        # Điểm squeeze (giá trị càng gần 0, squeeze càng mạnh)
        squeeze_score = max(0, 1 - (ratio / self.bollinger_squeeze_threshold))
        
        return squeeze_score
    
    def _calculate_adx(self, df: pd.DataFrame, window: int = 14) -> float:
        """
        Tính chỉ số Average Directional Index (ADX)
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLC
            window (int): Cửa sổ tính toán
            
        Returns:
            float: Giá trị ADX
        """
        # Tính +DM và -DM
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        up_move = high[1:] - high[:-1]
        down_move = low[:-1] - low[1:]
        
        pos_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        neg_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # Tính TR (True Range)
        tr1 = np.abs(high[1:] - low[1:])
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.vstack([tr1, tr2, tr3]).max(axis=0)
        
        # Tính chỉ số đầu tiên
        tr_period = tr[-window:]
        pos_dm_period = pos_dm[-window:]
        neg_dm_period = neg_dm[-window:]
        
        # Tính chỉ số
        tr_sum = np.sum(tr_period)
        pos_di = 100 * np.sum(pos_dm_period) / tr_sum if tr_sum > 0 else 0
        neg_di = 100 * np.sum(neg_dm_period) / tr_sum if tr_sum > 0 else 0
        
        dx = 100 * np.abs(pos_di - neg_di) / (pos_di + neg_di) if (pos_di + neg_di) > 0 else 0
        adx = dx  # Đơn giản hóa, thực tế ADX là trung bình 14 ngày của DX
        
        return adx
    
    def adjust_strategy_for_sideways(self, original_position_size: float) -> Dict:
        """
        Điều chỉnh chiến lược giao dịch cho thị trường sideway
        
        Args:
            original_position_size (float): Kích thước vị thế theo chiến lược gốc
            
        Returns:
            Dict: Các tham số chiến lược đã điều chỉnh
        """
        if not self.is_sideways:
            return {
                "position_size": original_position_size,
                "use_mean_reversion": False,
                "adjust_stop_loss": False,
                "sideways_score": self.sideways_score
            }
        
        # Giảm kích thước vị thế
        adjusted_position_size = original_position_size * (1 - self.position_size_reduction * self.sideways_score)
        
        # Trả về chiến lược điều chỉnh
        return {
            "position_size": adjusted_position_size,
            "use_mean_reversion": self.config.get('mean_reversion_enabled', True),
            "adjust_stop_loss": True,
            "sideways_score": self.sideways_score
        }
    
    def generate_mean_reversion_signals(self, df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        """
        Tạo tín hiệu theo chiến lược mean reversion cho thị trường sideway
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLC
            window (int): Cửa sổ tính toán
            
        Returns:
            pd.DataFrame: DataFrame với tín hiệu giao dịch
        """
        if not self.is_sideways:
            logger.info("Không phải thị trường sideway, không tạo tín hiệu mean reversion")
            return df
        
        # Sao chép để không làm thay đổi dữ liệu gốc
        result_df = df.copy()
        
        # Tính Bollinger Bands
        result_df['middle_band'] = result_df['close'].rolling(window=window).mean()
        rolling_std = result_df['close'].rolling(window=window).std()
        result_df['upper_band'] = result_df['middle_band'] + 2 * rolling_std
        result_df['lower_band'] = result_df['middle_band'] - 2 * rolling_std
        
        # Tính %B (vị trí tương đối trong Bollinger Bands)
        result_df['pct_b'] = (result_df['close'] - result_df['lower_band']) / (result_df['upper_band'] - result_df['lower_band'])
        
        # Tín hiệu mua: Giá gần băng dưới (%B < 0.2)
        # Tín hiệu bán: Giá gần băng trên (%B > 0.8)
        result_df['buy_signal'] = (result_df['pct_b'] < 0.2).astype(int)
        result_df['sell_signal'] = (result_df['pct_b'] > 0.8).astype(int)
        
        # RSI để xác nhận tín hiệu
        result_df['rsi'] = self._calculate_rsi(result_df, window)
        
        # Lọc tín hiệu với RSI
        result_df['buy_signal'] = ((result_df['buy_signal'] == 1) & (result_df['rsi'] < 30)).astype(int)
        result_df['sell_signal'] = ((result_df['sell_signal'] == 1) & (result_df['rsi'] > 70)).astype(int)
        
        logger.info(f"Đã tạo tín hiệu mean reversion cho thị trường sideway với {result_df['buy_signal'].sum()} tín hiệu mua và {result_df['sell_signal'].sum()} tín hiệu bán")
        
        return result_df
    
    def _calculate_rsi(self, df: pd.DataFrame, window: int = 14) -> pd.Series:
        """
        Tính chỉ số Relative Strength Index (RSI)
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu giá
            window (int): Cửa sổ tính toán
            
        Returns:
            pd.Series: Chuỗi giá trị RSI
        """
        delta = df['close'].diff()
        up, down = delta.copy(), delta.copy()
        up[up < 0] = 0
        down[down > 0] = 0
        down = -down
        
        roll_up = up.rolling(window).mean()
        roll_down = down.rolling(window).mean()
        
        rs = roll_up / roll_down
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def visualize_sideways_detection(self, df: pd.DataFrame, symbol: str, window: int = 20, custom_path: Optional[str] = None) -> str:
        """
        Tạo biểu đồ phân tích thị trường sideway
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLC
            symbol (str): Ký hiệu tiền tệ
            window (int): Cửa sổ tính toán
            custom_path (str, optional): Đường dẫn tùy chỉnh để lưu biểu đồ
            
        Returns:
            str: Đường dẫn tới biểu đồ đã tạo
        """
        if len(df) < window * 2:
            logger.warning("Không đủ dữ liệu để tạo biểu đồ phân tích")
            return ""
        
        # Sao chép để không làm thay đổi dữ liệu gốc
        plot_df = df.copy()
        
        # Tính Bollinger Bands
        plot_df['middle_band'] = plot_df['close'].rolling(window=window).mean()
        rolling_std = plot_df['close'].rolling(window=window).std()
        plot_df['upper_band'] = plot_df['middle_band'] + 2 * rolling_std
        plot_df['lower_band'] = plot_df['middle_band'] - 2 * rolling_std
        
        # Tính Keltner Channels
        atr = self._calculate_atr(plot_df, window)
        plot_df['keltner_middle'] = plot_df['close'].rolling(window=window).mean()
        plot_df['keltner_upper'] = plot_df['keltner_middle'] + self.keltner_factor * atr
        plot_df['keltner_lower'] = plot_df['keltner_middle'] - self.keltner_factor * atr
        
        # Tính RSI
        plot_df['rsi'] = self._calculate_rsi(plot_df, window)
        
        # Tính ADX
        adx_values = []
        for i in range(window, len(plot_df)):
            adx = self._calculate_adx(plot_df.iloc[:i+1], window)
            adx_values.append(adx)
        
        # Pad values
        adx_values = [np.nan] * window + adx_values
        plot_df['adx'] = adx_values
        
        # Tạo biểu đồ
        fig, axs = plt.subplots(3, 1, figsize=(14, 12), gridspec_kw={'height_ratios': [3, 1, 1]})
        
        # Biểu đồ giá và băng
        axs[0].plot(plot_df.index, plot_df['close'], label='Close Price', color='blue')
        axs[0].plot(plot_df.index, plot_df['middle_band'], label='BB Middle', color='gray', linestyle='--')
        axs[0].plot(plot_df.index, plot_df['upper_band'], label='BB Upper', color='red', linestyle='-')
        axs[0].plot(plot_df.index, plot_df['lower_band'], label='BB Lower', color='green', linestyle='-')
        axs[0].plot(plot_df.index, plot_df['keltner_upper'], label='KC Upper', color='purple', linestyle=':')
        axs[0].plot(plot_df.index, plot_df['keltner_lower'], label='KC Lower', color='purple', linestyle=':')
        
        # Tô màu vùng squeeze
        squeeze_region = (plot_df['upper_band'] <= plot_df['keltner_upper']) & (plot_df['lower_band'] >= plot_df['keltner_lower'])
        squeeze_starts = []
        squeeze_ends = []
        in_squeeze = False
        
        for i, is_squeeze in enumerate(squeeze_region):
            if is_squeeze and not in_squeeze:
                squeeze_starts.append(i)
                in_squeeze = True
            elif not is_squeeze and in_squeeze:
                squeeze_ends.append(i)
                in_squeeze = False
        
        if in_squeeze:
            squeeze_ends.append(len(squeeze_region) - 1)
        
        for start, end in zip(squeeze_starts, squeeze_ends):
            axs[0].axvspan(plot_df.index[start], plot_df.index[end], alpha=0.2, color='yellow')
        
        axs[0].set_title(f'Sideways Market Analysis - {symbol} (Score: {self.sideways_score:.2f})')
        axs[0].set_ylabel('Price')
        axs[0].legend(loc='upper left')
        axs[0].grid(True)
        
        # Biểu đồ RSI
        axs[1].plot(plot_df.index, plot_df['rsi'], label='RSI', color='blue')
        axs[1].axhline(y=70, color='red', linestyle='--')
        axs[1].axhline(y=30, color='green', linestyle='--')
        axs[1].set_ylabel('RSI')
        axs[1].set_ylim(0, 100)
        axs[1].grid(True)
        
        # Biểu đồ ADX
        axs[2].plot(plot_df.index, plot_df['adx'], label='ADX', color='purple')
        axs[2].axhline(y=self.adx_threshold, color='red', linestyle='--')
        axs[2].set_ylabel('ADX')
        axs[2].set_xlabel('Date')
        axs[2].grid(True)
        
        plt.tight_layout()
        
        # Tạo đường dẫn lưu biểu đồ
        if custom_path:
            os.makedirs(custom_path, exist_ok=True)
            chart_path = os.path.join(custom_path, f'sideways_analysis_{symbol}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
        else:
            chart_path = os.path.join('charts/sideways_analysis', f'sideways_analysis_{symbol}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
        
        plt.savefig(chart_path)
        plt.close()
        
        logger.info(f"Đã lưu biểu đồ phân tích thị trường sideway tại {chart_path}")
        return chart_path

    def calculate_squeeze_duration(self, df: pd.DataFrame, window: int = 20) -> int:
        """
        Tính thời gian kéo dài của squeeze hiện tại
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLC
            window (int): Cửa sổ tính toán
            
        Returns:
            int: Số nến mà squeeze đã kéo dài
        """
        if len(df) < window * 2:
            return 0
        
        # Tính Bollinger Bands
        rolling_mean = df['close'].rolling(window=window).mean()
        rolling_std = df['close'].rolling(window=window).std()
        upper_band = rolling_mean + 2 * rolling_std
        lower_band = rolling_mean - 2 * rolling_std
        
        # Tính Keltner Channels
        atr = self._calculate_atr(df, window)
        keltner_middle = df['close'].rolling(window=window).mean()
        keltner_upper = keltner_middle + self.keltner_factor * atr
        keltner_lower = keltner_middle - self.keltner_factor * atr
        
        # Phát hiện squeeze
        is_squeeze = (upper_band <= keltner_upper) & (lower_band >= keltner_lower)
        
        # Tính thời gian squeeze hiện tại
        if not is_squeeze.iloc[-1]:
            return 0
        
        current_squeeze_duration = 0
        for i in range(len(is_squeeze) - 1, -1, -1):
            if is_squeeze.iloc[i]:
                current_squeeze_duration += 1
            else:
                break
        
        return current_squeeze_duration
    
    def predict_breakout_direction(self, df: pd.DataFrame, window: int = 20) -> str:
        """
        Dự đoán hướng breakout từ sideways market
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLC
            window (int): Cửa sổ tính toán
            
        Returns:
            str: Hướng dự đoán ('up', 'down', hoặc 'unknown')
        """
        if not self.is_sideways or len(df) < window * 2:
            return "unknown"
        
        # Tính momentum indicators
        momentum_score = 0
        
        # 1. Xu hướng giá ngắn hạn
        short_ma = df['close'].rolling(window=5).mean().iloc[-1]
        long_ma = df['close'].rolling(window=window).mean().iloc[-1]
        if short_ma > long_ma:
            momentum_score += 1
        elif short_ma < long_ma:
            momentum_score -= 1
        
        # 2. Khối lượng giao dịch trung bình
        avg_volume = df['volume'].rolling(window=window).mean().iloc[-1]
        recent_volume = df['volume'].iloc[-5:].mean()
        if recent_volume > avg_volume * 1.2:  # Volume tăng 20%
            if df['close'].iloc[-1] > df['close'].iloc[-2]:
                momentum_score += 1
            else:
                momentum_score -= 1
        
        # 3. Chỉ số RSI
        rsi = self._calculate_rsi(df).iloc[-1]
        if rsi > 50:
            momentum_score += 1
        else:
            momentum_score -= 1
        
        # 4. Phân tích cung cầu dựa trên khối lượng
        obv = self._calculate_obv(df)
        obv_slope = (obv.iloc[-1] - obv.iloc[-window]) / window
        if obv_slope > 0:
            momentum_score += 1
        else:
            momentum_score -= 1
        
        # Dự đoán dựa trên tổng điểm
        if momentum_score >= 2:
            return "up"
        elif momentum_score <= -2:
            return "down"
        else:
            return "unknown"
    
    def _calculate_obv(self, df: pd.DataFrame) -> pd.Series:
        """
        Tính chỉ số On-Balance Volume (OBV)
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLC và volume
            
        Returns:
            pd.Series: Chuỗi giá trị OBV
        """
        close_diff = df['close'].diff()
        obv = pd.Series(index=df.index)
        obv.iloc[0] = 0
        
        for i in range(1, len(df)):
            if close_diff.iloc[i] > 0:
                obv.iloc[i] = obv.iloc[i-1] + df['volume'].iloc[i]
            elif close_diff.iloc[i] < 0:
                obv.iloc[i] = obv.iloc[i-1] - df['volume'].iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        return obv
    
    def optimize_takeprofit_stoploss(self, df: pd.DataFrame, window: int = 20) -> Dict:
        """
        Tối ưu hóa mức take profit và stop loss cho thị trường sideway
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLC
            window (int): Cửa sổ tính toán
            
        Returns:
            Dict: Các mức take profit và stop loss đã tối ưu hóa
        """
        if not self.is_sideways:
            return {
                "tp_adjustment": 1.0,
                "sl_adjustment": 1.0
            }
        
        # Tính Bollinger Bands
        rolling_mean = df['close'].rolling(window=window).mean().iloc[-1]
        rolling_std = df['close'].rolling(window=window).std().iloc[-1]
        
        # Tính chiều rộng của BB tương đối với giá trung bình
        bb_width_percent = (2 * rolling_std) / rolling_mean
        
        # Điều chỉnh TP và SL dựa trên độ rộng BB
        tp_adjustment = min(1.0, max(0.5, bb_width_percent / 0.02))  # Giả sử BB width bình thường là 2%
        sl_adjustment = max(1.0, min(1.5, 0.02 / bb_width_percent))
        
        # Đối với thị trường sideway mạnh, giảm TP và tăng SL
        if self.sideways_score > 0.8:
            tp_adjustment *= 0.8
            sl_adjustment *= 1.2
        
        return {
            "tp_adjustment": tp_adjustment,
            "sl_adjustment": sl_adjustment
        }
    
    def generate_market_report(self, df: pd.DataFrame, symbol: str, window: int = 20) -> Dict:
        """
        Tạo báo cáo phân tích thị trường đầy đủ
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLC
            symbol (str): Ký hiệu tiền tệ
            window (int): Cửa sổ tính toán
            
        Returns:
            Dict: Báo cáo phân tích thị trường
        """
        # Phát hiện thị trường sideway
        is_sideways = self.detect_sideways_market(df, window)
        
        # Dự đoán hướng breakout
        breakout_direction = self.predict_breakout_direction(df, window)
        
        # Tính thời gian squeeze
        squeeze_duration = self.calculate_squeeze_duration(df, window)
        
        # Tối ưu hóa TP/SL
        tp_sl_adjustments = self.optimize_takeprofit_stoploss(df, window)
        
        # Tạo biểu đồ nếu là thị trường sideway
        chart_path = ""
        if is_sideways:
            chart_path = self.visualize_sideways_detection(df, symbol, window)
        
        # Tạo báo cáo
        report = {
            "symbol": symbol,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "is_sideways_market": is_sideways,
            "sideways_score": self.sideways_score,
            "breakout_prediction": breakout_direction,
            "squeeze_duration": squeeze_duration,
            "tp_adjustment_factor": tp_sl_adjustments["tp_adjustment"],
            "sl_adjustment_factor": tp_sl_adjustments["sl_adjustment"],
            "chart_path": chart_path,
            "recommendations": []
        }
        
        # Thêm các khuyến nghị
        if is_sideways:
            report["recommendations"].append("Giảm kích thước vị thế xuống {:.1f}% so với bình thường".format(
                (1 - self.position_size_reduction * self.sideways_score) * 100
            ))
            
            report["recommendations"].append("Sử dụng chiến lược mean reversion thay vì trend following")
            
            if breakout_direction != "unknown":
                report["recommendations"].append("Chuẩn bị cho breakout hướng {} với tín hiệu xác nhận".format(
                    "tăng" if breakout_direction == "up" else "giảm"
                ))
            
            report["recommendations"].append("Điều chỉnh take profit xuống {:.1f}% so với bình thường".format(
                tp_sl_adjustments["tp_adjustment"] * 100
            ))
            
            report["recommendations"].append("Điều chỉnh stop loss lên {:.1f}% so với bình thường".format(
                tp_sl_adjustments["sl_adjustment"] * 100
            ))
        else:
            report["recommendations"].append("Thị trường không ở trạng thái sideway, sử dụng chiến lược thông thường")
        
        # Lưu báo cáo vào file
        report_path = os.path.join(
            'reports', 
            f'sideways_report_{symbol}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )
        os.makedirs('reports', exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=4)
        
        logger.info(f"Đã lưu báo cáo phân tích thị trường tại {report_path}")
        
        return report

# Hàm chạy demo nếu chạy trực tiếp
if __name__ == "__main__":
    # Tạo dữ liệu mẫu
    import yfinance as yf
    
    # Tải dữ liệu
    try:
        btc = yf.download("BTC-USD", period="3mo", interval="1d")
        eth = yf.download("ETH-USD", period="3mo", interval="1d")
        
        # Đổi tên cột cho phù hợp
        for df in [btc, eth]:
            df.columns = [c.lower() for c in df.columns]
        
        # Khởi tạo optimizer
        optimizer = SidewaysMarketOptimizer()
        
        # Phân tích BTC
        print("\n=== Phân tích Bitcoin ===")
        btc_sideways = optimizer.detect_sideways_market(btc)
        print(f"Bitcoin thị trường sideway: {btc_sideways} (Score: {optimizer.sideways_score:.2f})")
        
        if btc_sideways:
            chart_path = optimizer.visualize_sideways_detection(btc, "BTC-USD")
            print(f"Đã lưu biểu đồ tại: {chart_path}")
            
            # Lấy các điều chỉnh chiến lược
            strategy_adjustments = optimizer.adjust_strategy_for_sideways(1.0)
            print(f"Kích thước vị thế điều chỉnh: {strategy_adjustments['position_size']:.2f}")
            print(f"Sử dụng mean reversion: {strategy_adjustments['use_mean_reversion']}")
            
            # Dự đoán hướng breakout
            breakout = optimizer.predict_breakout_direction(btc)
            print(f"Dự đoán hướng breakout: {breakout}")
            
            # Điều chỉnh TP/SL
            tp_sl = optimizer.optimize_takeprofit_stoploss(btc)
            print(f"Điều chỉnh Take Profit: {tp_sl['tp_adjustment']:.2f}x")
            print(f"Điều chỉnh Stop Loss: {tp_sl['sl_adjustment']:.2f}x")
        
        # Phân tích ETH
        print("\n=== Phân tích Ethereum ===")
        eth_sideways = optimizer.detect_sideways_market(eth)
        print(f"Ethereum thị trường sideway: {eth_sideways} (Score: {optimizer.sideways_score:.2f})")
        
        if eth_sideways:
            chart_path = optimizer.visualize_sideways_detection(eth, "ETH-USD")
            print(f"Đã lưu biểu đồ tại: {chart_path}")
            
            # Lấy các điều chỉnh chiến lược
            strategy_adjustments = optimizer.adjust_strategy_for_sideways(1.0)
            print(f"Kích thước vị thế điều chỉnh: {strategy_adjustments['position_size']:.2f}")
            print(f"Sử dụng mean reversion: {strategy_adjustments['use_mean_reversion']}")
            
            # Dự đoán hướng breakout
            breakout = optimizer.predict_breakout_direction(eth)
            print(f"Dự đoán hướng breakout: {breakout}")
            
            # Điều chỉnh TP/SL
            tp_sl = optimizer.optimize_takeprofit_stoploss(eth)
            print(f"Điều chỉnh Take Profit: {tp_sl['tp_adjustment']:.2f}x")
            print(f"Điều chỉnh Stop Loss: {tp_sl['sl_adjustment']:.2f}x")
        
        print("\nHoàn thành demo SidewaysMarketOptimizer")
        
    except Exception as e:
        print(f"Lỗi khi chạy demo: {str(e)}")
        print("Bạn có thể cần cài đặt yfinance: pip install yfinance")