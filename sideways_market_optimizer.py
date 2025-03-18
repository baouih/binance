#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sideways Market Optimizer

Module để phát hiện và tối ưu hóa chiến lược giao dịch cho thị trường đi ngang,
với khả năng tích hợp RSI Divergence để cải thiện tín hiệu.
"""

import os
import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Union
import talib as ta

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/sideways_optimizer.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('sideways_optimizer')

class SidewaysMarketOptimizer:
    """
    Lớp phát hiện thị trường đi ngang và tối ưu hóa chiến lược giao dịch
    """
    
    def __init__(self, config_path: str = 'configs/sideways_config.json'):
        """
        Khởi tạo optimizer với cấu hình
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
        """
        self.config = self._load_config(config_path)
        
        # Khởi tạo bộ phát hiện RSI Divergence nếu nằm trong cùng thư mục
        try:
            from rsi_divergence_detector import RSIDivergenceDetector
            self.divergence_detector = RSIDivergenceDetector()
            self.has_divergence_detector = True
            logger.info("Đã tải RSI Divergence Detector")
        except ImportError:
            self.has_divergence_detector = False
            logger.warning("Không thể tải RSI Divergence Detector, chức năng phát hiện phân kỳ không khả dụng")
        
        # Tạo thư mục đầu ra
        os.makedirs('charts', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        logger.info("Đã khởi tạo Sideways Market Optimizer")
    
    def _load_config(self, config_path: str) -> Dict:
        """
        Tải cấu hình từ file JSON
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
            
        Returns:
            Dict: Cấu hình đã tải
        """
        default_config = {
            "volatility_threshold": 0.5,
            "bollinger_squeeze_threshold": 0.1,
            "keltner_factor": 1.5,
            "adx_threshold": 25,
            "position_size_reduction": 0.5,
            "mean_reversion_enabled": True,
            "squeeze_detection_enabled": True,
            "volatility_filter_enabled": True,
            "rsi_period": 14,
            "sideways_tp_sl_ratio": 1.2,
            "trending_tp_sl_ratio": 3.0,
            "use_atr_targets": True,
            "tp_atr_multiplier": 1.5,
            "sl_atr_multiplier": 1.2
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Không tìm thấy file cấu hình: {config_path}")
                logger.info("Sử dụng cấu hình mặc định")
                return default_config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
            logger.info("Sử dụng cấu hình mặc định")
            return default_config
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tính toán các chỉ báo cần thiết cho phát hiện thị trường đi ngang
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLC
            
        Returns:
            pd.DataFrame: DataFrame với các chỉ báo đã tính
        """
        # Chuyển đổi cột thành chữ thường
        df.columns = [c.lower() for c in df.columns]
        df_copy = df.copy()
        
        # Tạo Bollinger Bands
        upper, middle, lower = ta.BBANDS(
            df_copy['close'], 
            timeperiod=20, 
            nbdevup=2, 
            nbdevdn=2, 
            matype=0
        )
        df_copy['bb_upper'] = upper
        df_copy['bb_middle'] = middle
        df_copy['bb_lower'] = lower
        df_copy['bb_width'] = (upper - lower) / middle
        
        # Tính %B (vị trí trong Bollinger Bands)
        df_copy['pct_b'] = (df_copy['close'] - lower) / (upper - lower)
        
        # Tạo Keltner Channels
        typical_price = (df_copy['high'] + df_copy['low'] + df_copy['close']) / 3
        atr = ta.ATR(df_copy['high'], df_copy['low'], df_copy['close'], timeperiod=20)
        keltner_factor = self.config.get('keltner_factor', 1.5)
        
        ema = ta.EMA(typical_price, timeperiod=20)
        df_copy['kc_upper'] = ema + keltner_factor * atr
        df_copy['kc_middle'] = ema
        df_copy['kc_lower'] = ema - keltner_factor * atr
        
        # Tính bollinger squeeze
        df_copy['bb_squeeze'] = (df_copy['bb_upper'] - df_copy['bb_lower']) < (df_copy['kc_upper'] - df_copy['kc_lower'])
        
        # Tính ADX
        df_copy['adx'] = ta.ADX(df_copy['high'], df_copy['low'], df_copy['close'], timeperiod=14)
        
        # Tính RSI
        df_copy['rsi'] = ta.RSI(df_copy['close'], timeperiod=self.config.get('rsi_period', 14))
        
        # Thêm ATR
        df_copy['atr_20d'] = atr
        df_copy['atr_ratio'] = atr / df_copy['close']
        
        # Thêm momentum
        df_copy['momentum'] = df_copy['close'].pct_change(5)
        
        return df_copy
    
    def is_sideways_market(self, df: pd.DataFrame) -> Tuple[bool, float]:
        """
        Phát hiện thị trường đi ngang
        
        Args:
            df (pd.DataFrame): DataFrame với các chỉ báo đã tính
            
        Returns:
            Tuple[bool, float]: Là thị trường đi ngang hay không và điểm số xác định mức độ
        """
        # Lấy các ngưỡng từ cấu hình
        volatility_threshold = self.config.get('volatility_threshold', 0.5)
        squeeze_threshold = self.config.get('bollinger_squeeze_threshold', 0.1)
        adx_threshold = self.config.get('adx_threshold', 25)
        
        # Lấy dữ liệu mới nhất
        recent_data = df.iloc[-10:].copy()
        
        # Tính các tiêu chí xác định thị trường đi ngang
        
        # 1. Bollinger Bands thu hẹp (squeeze)
        squeeze_score = 0
        bb_widths = recent_data['bb_width'].values
        avg_bb_width = np.mean(bb_widths)
        
        if avg_bb_width < squeeze_threshold:
            squeeze_score = 1.0
        else:
            # Chuẩn hóa để có giá trị giữa 0 và 1
            squeeze_score = max(0, 1 - (avg_bb_width / squeeze_threshold))
        
        # 2. ATR thấp
        volatility_score = 0
        atr_ratios = recent_data['atr_ratio'].values
        avg_atr_ratio = np.mean(atr_ratios)
        
        if avg_atr_ratio < volatility_threshold:
            volatility_score = 1.0
        else:
            # Chuẩn hóa để có giá trị giữa 0 và 1
            volatility_score = max(0, 1 - (avg_atr_ratio / volatility_threshold))
        
        # 3. ADX thấp (xu hướng yếu)
        trend_score = 0
        adx_values = recent_data['adx'].values
        avg_adx = np.mean(adx_values)
        
        if avg_adx < adx_threshold:
            trend_score = 1.0
        else:
            # Chuẩn hóa để có giá trị giữa 0 và 1
            trend_score = max(0, 1 - (avg_adx / adx_threshold))
        
        # 4. Momentum thấp
        momentum_values = np.abs(recent_data['momentum'].values)
        avg_momentum = np.mean(momentum_values)
        momentum_score = max(0, 1 - (avg_momentum / 0.05))  # 5% momentum as threshold
        
        # Tính điểm tổng hợp
        # Trọng số: Squeeze (0.3), Volatility (0.3), Trend (0.3), Momentum (0.1)
        sideways_score = (0.3 * squeeze_score) + (0.3 * volatility_score) + (0.3 * trend_score) + (0.1 * momentum_score)
        
        # Xác định thị trường đi ngang nếu điểm số cao
        is_sideways = sideways_score > 0.6
        
        return is_sideways, sideways_score
    
    def predict_breakout_direction(self, df: pd.DataFrame) -> str:
        """
        Dự đoán hướng breakout của thị trường đi ngang
        
        Args:
            df (pd.DataFrame): DataFrame với các chỉ báo đã tính
            
        Returns:
            str: Hướng breakout dự đoán ('up', 'down', hoặc 'unknown')
        """
        # Lấy dữ liệu gần đây nhất
        recent_data = df.iloc[-20:].copy()
        
        # Phân tích vị trí giá trong Bollinger Bands
        recent_pct_b = recent_data['pct_b'].iloc[-1]
        avg_pct_b = recent_data['pct_b'].mean()
        
        # Phân tích RSI
        recent_rsi = recent_data['rsi'].iloc[-1]
        
        # Phân tích volume (nếu có)
        if 'volume' in recent_data.columns:
            volume_trend = recent_data['volume'].iloc[-5:].mean() / recent_data['volume'].iloc[-10:-5].mean()
            has_volume_increase = volume_trend > 1.2
        else:
            has_volume_increase = False
        
        # Xác định hướng có nhiều khả năng
        if recent_pct_b > 0.8 and recent_rsi > 60:
            # Giá đang ở gần cận trên của BB và RSI cao => Breakout hướng lên
            if has_volume_increase:
                return "up"
            else:
                return "up" if recent_pct_b > 0.9 and recent_rsi > 65 else "unknown"
        
        elif recent_pct_b < 0.2 and recent_rsi < 40:
            # Giá đang ở gần cận dưới của BB và RSI thấp => Breakout hướng xuống
            if has_volume_increase:
                return "down"
            else:
                return "down" if recent_pct_b < 0.1 and recent_rsi < 35 else "unknown"
        
        # Tìm kiếm dấu hiệu xác định hướng khác
        if recent_rsi > 65 and avg_pct_b > 0.6:
            return "up"
        elif recent_rsi < 35 and avg_pct_b < 0.4:
            return "down"
        
        # Không đủ dấu hiệu xác định
        return "unknown"
    
    def get_position_size_adjustment(self, is_sideways: bool, sideways_score: float) -> Dict:
        """
        Xác định điều chỉnh kích thước vị thế dựa trên trạng thái thị trường
        
        Args:
            is_sideways (bool): Là thị trường đi ngang hay không
            sideways_score (float): Điểm số xác định mức độ đi ngang
            
        Returns:
            Dict: Điều chỉnh kích thước vị thế
        """
        default_position_size = 1.0
        
        if not is_sideways:
            return {
                "original": default_position_size,
                "adjusted": default_position_size,
                "reduction_pct": 0
            }
        
        # Lấy cấu hình giảm kích thước vị thế
        position_size_reduction = self.config.get('position_size_reduction', 0.5)
        
        # Điều chỉnh mức độ giảm dựa trên điểm số
        # sideways_score: 0.6 -> 0.9 = reduction: min -> max
        if sideways_score > 0.9:
            # Thị trường rất đi ngang
            reduction_factor = position_size_reduction
        else:
            # Điều chỉnh theo thang từ 0.6 đến 0.9
            normalized_score = (sideways_score - 0.6) / 0.3
            normalized_score = max(0, min(1, normalized_score))
            reduction_factor = position_size_reduction * normalized_score
        
        adjusted_position_size = default_position_size * (1 - reduction_factor)
        reduction_pct = reduction_factor * 100
        
        return {
            "original": default_position_size,
            "adjusted": adjusted_position_size,
            "reduction_pct": reduction_pct
        }
    
    def get_tp_sl_adjustment(self, is_sideways: bool, df: pd.DataFrame) -> Dict:
        """
        Xác định điều chỉnh TP/SL dựa trên trạng thái thị trường
        
        Args:
            is_sideways (bool): Là thị trường đi ngang hay không
            df (pd.DataFrame): DataFrame với các chỉ báo đã tính
            
        Returns:
            Dict: Điều chỉnh tỷ lệ TP/SL
        """
        # Lấy cấu hình tỷ lệ TP/SL
        sideways_tp_sl_ratio = self.config.get('sideways_tp_sl_ratio', 1.2)
        trending_tp_sl_ratio = self.config.get('trending_tp_sl_ratio', 3.0)
        
        if is_sideways:
            tp_sl_ratio = sideways_tp_sl_ratio
        else:
            tp_sl_ratio = trending_tp_sl_ratio
        
        return {
            "tp_sl_ratio": tp_sl_ratio,
            "is_sideways": is_sideways
        }
    
    def calculate_price_targets(
        self, 
        df: pd.DataFrame, 
        is_sideways: bool, 
        tp_sl_ratio: float
    ) -> Dict:
        """
        Tính toán mục tiêu giá TP/SL
        
        Args:
            df (pd.DataFrame): DataFrame với các chỉ báo đã tính
            is_sideways (bool): Là thị trường đi ngang hay không
            tp_sl_ratio (float): Tỷ lệ Take Profit / Stop Loss
            
        Returns:
            Dict: Mục tiêu giá
        """
        # Lấy cấu hình
        use_atr = self.config.get('use_atr_targets', True)
        tp_atr_multiplier = self.config.get('tp_atr_multiplier', 1.5)
        sl_atr_multiplier = self.config.get('sl_atr_multiplier', 1.2)
        
        # Lấy giá và ATR hiện tại
        current_price = df['close'].iloc[-1]
        atr = df['atr_20d'].iloc[-1]
        
        # Vị trí trong BB
        pct_b = df['pct_b'].iloc[-1]
        
        # Xác định hướng vào lệnh dựa trên vị trí trong BB (cho mean reversion)
        if is_sideways:
            if pct_b > 0.8:
                # Giá gần cận trên, vào lệnh bán (mean reversion)
                direction = "sell"
            elif pct_b < 0.2:
                # Giá gần cận dưới, vào lệnh mua (mean reversion)
                direction = "buy"
            else:
                # Chưa có tín hiệu rõ ràng, mặc định là mua
                direction = "buy"
        else:
            # Trong xu hướng, mặc định là mua (có thể cải thiện với các chỉ báo xu hướng)
            direction = "buy"
        
        # Tính TP/SL dựa trên ATR
        if use_atr:
            if direction == "buy":
                sl_price = current_price - (sl_atr_multiplier * atr)
                sl_distance_pct = ((current_price - sl_price) / current_price) * 100
                tp_distance_pct = sl_distance_pct * tp_sl_ratio
                tp_price = current_price + (current_price * tp_distance_pct / 100)
            else:  # sell
                sl_price = current_price + (sl_atr_multiplier * atr)
                sl_distance_pct = ((sl_price - current_price) / current_price) * 100
                tp_distance_pct = sl_distance_pct * tp_sl_ratio
                tp_price = current_price - (current_price * tp_distance_pct / 100)
        else:
            # Sử dụng % cố định
            if direction == "buy":
                sl_distance_pct = 2.0  # 2%
                tp_distance_pct = sl_distance_pct * tp_sl_ratio
                sl_price = current_price * (1 - sl_distance_pct/100)
                tp_price = current_price * (1 + tp_distance_pct/100)
            else:  # sell
                sl_distance_pct = 2.0  # 2%
                tp_distance_pct = sl_distance_pct * tp_sl_ratio
                sl_price = current_price * (1 + sl_distance_pct/100)
                tp_price = current_price * (1 - tp_distance_pct/100)
        
        return {
            "current_price": current_price,
            "direction": direction,
            "tp_price": tp_price,
            "sl_price": sl_price,
            "tp_distance_pct": tp_distance_pct,
            "sl_distance_pct": sl_distance_pct,
            "risk_reward_ratio": tp_distance_pct / sl_distance_pct
        }
    
    def plot_sideways_detection(self, df: pd.DataFrame, is_sideways: bool, 
                               sideways_score: float, symbol: str) -> str:
        """
        Vẽ biểu đồ phát hiện thị trường đi ngang
        
        Args:
            df (pd.DataFrame): DataFrame với các chỉ báo đã tính
            is_sideways (bool): Là thị trường đi ngang hay không
            sideways_score (float): Điểm số xác định mức độ đi ngang
            symbol (str): Ký hiệu tiền tệ
            
        Returns:
            str: Đường dẫn đến biểu đồ đã lưu
        """
        # Chọn 50 điểm dữ liệu gần nhất
        plot_df = df.iloc[-50:].copy()
        
        # Tạo biểu đồ
        fig, axs = plt.subplots(3, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1, 1]})
        
        # Biểu đồ 1: Giá và Bollinger Bands
        axs[0].plot(plot_df.index, plot_df['close'], label='Giá đóng cửa')
        axs[0].plot(plot_df.index, plot_df['bb_upper'], 'r--', label='BB Trên')
        axs[0].plot(plot_df.index, plot_df['bb_middle'], 'g--', label='BB Giữa')
        axs[0].plot(plot_df.index, plot_df['bb_lower'], 'r--', label='BB Dưới')
        
        # Vẽ vùng đi ngang
        if is_sideways:
            # Đánh dấu 10 điểm dữ liệu gần nhất
            sideways_region = plot_df.iloc[-10:].index
            y_min, y_max = axs[0].get_ylim()
            axs[0].fill_between(sideways_region, y_min, y_max, 
                              color='yellow', alpha=0.3, label='Vùng đi ngang')
        
        # Thêm tiêu đề
        market_type = "ĐI NGANG" if is_sideways else "XU HƯỚNG"
        axs[0].set_title(f'{symbol} - Thị trường {market_type} (Score: {sideways_score:.2f})', fontsize=14)
        axs[0].set_ylabel('Giá')
        axs[0].grid(True)
        axs[0].legend()
        
        # Biểu đồ 2: BB Width và Squeeze
        axs[1].plot(plot_df.index, plot_df['bb_width'], label='BB Width')
        axs[1].axhline(y=self.config.get('bollinger_squeeze_threshold', 0.1), color='r', linestyle='--', 
                     label=f"Ngưỡng squeeze: {self.config.get('bollinger_squeeze_threshold', 0.1)}")
        axs[1].set_ylabel('BB Width')
        axs[1].grid(True)
        axs[1].legend()
        
        # Biểu đồ 3: ADX
        axs[2].plot(plot_df.index, plot_df['adx'], label='ADX')
        axs[2].axhline(y=self.config.get('adx_threshold', 25), color='r', linestyle='--', 
                     label=f"Ngưỡng ADX: {self.config.get('adx_threshold', 25)}")
        axs[2].set_ylabel('ADX')
        axs[2].set_xlabel('Ngày')
        axs[2].grid(True)
        axs[2].legend()
        
        # Định dạng ngày tháng trên trục x
        for ax in axs:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Thêm thông tin chi tiết
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        textstr = f"""
        Sideways Score: {sideways_score:.2f}
        ADX: {plot_df['adx'].iloc[-1]:.2f}
        BB Width: {plot_df['bb_width'].iloc[-1]:.4f}
        ATR: {plot_df['atr_20d'].iloc[-1]:.2f}
        ATR Ratio: {plot_df['atr_ratio'].iloc[-1]*100:.2f}%
        """
        axs[0].text(0.02, 0.05, textstr, transform=axs[0].transAxes, fontsize=10,
                  verticalalignment='bottom', bbox=props)
        
        plt.tight_layout()
        
        # Lưu biểu đồ
        chart_path = f'charts/sideways_detection_{symbol}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        plt.savefig(chart_path)
        plt.close()
        
        logger.info(f"Đã lưu biểu đồ phát hiện thị trường đi ngang: {chart_path}")
        
        return chart_path
    
    def analyze_market(self, df: pd.DataFrame, symbol: str = '') -> Dict:
        """
        Phân tích thị trường và tạo báo cáo
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLC
            symbol (str): Ký hiệu tiền tệ
            
        Returns:
            Dict: Kết quả phân tích
        """
        # Tính toán các chỉ báo
        df_indicators = self.calculate_indicators(df)
        
        # Phát hiện thị trường đi ngang
        is_sideways, sideways_score = self.is_sideways_market(df_indicators)
        
        # Xác định hướng breakout tiềm năng
        breakout_direction = self.predict_breakout_direction(df_indicators)
        
        # Điều chỉnh kích thước vị thế
        position_sizing = self.get_position_size_adjustment(is_sideways, sideways_score)
        
        # Điều chỉnh tỷ lệ TP/SL
        tp_sl_adjustments = self.get_tp_sl_adjustment(is_sideways, df_indicators)
        
        # Tính toán mục tiêu giá
        price_targets = self.calculate_price_targets(
            df_indicators, 
            is_sideways, 
            tp_sl_adjustments['tp_sl_ratio']
        )
        
        # Chiến lược giao dịch
        strategy_adjustments = {
            "use_mean_reversion": is_sideways and self.config.get('mean_reversion_enabled', True),
            "breakout_prediction": breakout_direction,
            "tp_sl_ratio": tp_sl_adjustments['tp_sl_ratio']
        }
        
        # Lưu biểu đồ
        if symbol:
            chart_path = self.plot_sideways_detection(
                df_indicators, 
                is_sideways, 
                sideways_score, 
                symbol
            )
        else:
            chart_path = ""
        
        # Dữ liệu giá bổ sung
        price_data = {
            "current_price": df_indicators['close'].iloc[-1],
            "atr_20d": df_indicators['atr_20d'].iloc[-1],
            "atr_ratio": df_indicators['atr_ratio'].iloc[-1],
            "bb_width": df_indicators['bb_width'].iloc[-1],
            "pct_b": df_indicators['pct_b'].iloc[-1],
            "adx": df_indicators['adx'].iloc[-1],
            "rsi": df_indicators['rsi'].iloc[-1]
        }
        
        # Kết quả
        result = {
            "symbol": symbol,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "is_sideways_market": is_sideways,
            "sideways_score": sideways_score,
            "position_sizing": position_sizing,
            "strategy": strategy_adjustments,
            "price_targets": price_targets,
            "price_data": price_data,
            "chart_path": chart_path
        }
        
        return result
    
    def analyze_market_with_divergence(self, df: pd.DataFrame, symbol: str = '') -> Dict:
        """
        Phân tích thị trường với tích hợp phát hiện RSI Divergence
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLC
            symbol (str): Ký hiệu tiền tệ
            
        Returns:
            Dict: Kết quả phân tích
        """
        # Phân tích thị trường chuẩn
        market_analysis = self.analyze_market(df, symbol)
        
        # Thêm phát hiện phân kỳ nếu có
        if self.has_divergence_detector:
            try:
                # Tính toán các chỉ báo (nếu chưa có)
                if 'rsi' not in df.columns:
                    df_indicators = self.calculate_indicators(df)
                else:
                    df_indicators = df
                
                # Phát hiện phân kỳ
                bullish_divergence = self.divergence_detector.detect_divergence(df_indicators, is_bullish=True)
                bearish_divergence = self.divergence_detector.detect_divergence(df_indicators, is_bullish=False)
                
                # Lấy tín hiệu
                divergence_signal = self.divergence_detector.get_trading_signal(df_indicators)
                
                # Trực quan hóa phân kỳ nếu phát hiện
                visualized_chart = ""
                if bullish_divergence["detected"] or bearish_divergence["detected"]:
                    detected_divergence = bullish_divergence if bullish_divergence["detected"] else bearish_divergence
                    visualized_chart = self.divergence_detector.visualize_divergence(
                        df_indicators,
                        detected_divergence,
                        symbol
                    )
                
                # Thêm kết quả phân kỳ vào phân tích
                market_analysis['divergence'] = {
                    "bullish": bullish_divergence,
                    "bearish": bearish_divergence,
                    "signal": divergence_signal["signal"],
                    "signal_confidence": divergence_signal["confidence"],
                    "chart_path": visualized_chart
                }
                
            except Exception as e:
                logger.error(f"Lỗi khi phát hiện RSI Divergence: {str(e)}")
                market_analysis['divergence'] = {
                    "error": str(e),
                    "bullish": {"detected": False},
                    "bearish": {"detected": False},
                    "signal": "neutral",
                    "signal_confidence": 0,
                    "chart_path": ""
                }
        else:
            market_analysis['divergence'] = {
                "bullish": {"detected": False},
                "bearish": {"detected": False},
                "signal": "neutral",
                "signal_confidence": 0,
                "chart_path": "",
                "note": "RSI Divergence Detector không khả dụng"
            }
        
        return market_analysis
    
    def generate_market_report(self, df: pd.DataFrame, symbol: str = '') -> Dict:
        """
        Tạo báo cáo phân tích thị trường đầy đủ
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLC
            symbol (str): Ký hiệu tiền tệ
            
        Returns:
            Dict: Báo cáo phân tích
        """
        # Phân tích thị trường với RSI Divergence
        analysis = self.analyze_market_with_divergence(df, symbol)
        
        # Tính toán thông tin bổ sung
        current_price = analysis['price_data']['current_price']
        
        # Lấy tín hiệu từ phân tích
        is_sideways = analysis['is_sideways_market']
        sideways_score = analysis['sideways_score']
        
        # Xác định tín hiệu giao dịch
        if 'divergence' in analysis and analysis['divergence']['signal_confidence'] > 0.5:
            # Ưu tiên tín hiệu Divergence nếu có độ tin cậy cao
            trading_signal = analysis['divergence']['signal']
            signal_confidence = analysis['divergence']['signal_confidence']
            signal_source = "RSI Divergence"
        else:
            # Sử dụng tín hiệu mean reversion trong thị trường đi ngang
            if is_sideways and analysis['price_data']['pct_b'] > 0.8:
                trading_signal = "sell"
                signal_confidence = min(1.0, sideways_score * 1.2)
                signal_source = "Mean Reversion (Overbought)"
            elif is_sideways and analysis['price_data']['pct_b'] < 0.2:
                trading_signal = "buy"
                signal_confidence = min(1.0, sideways_score * 1.2)
                signal_source = "Mean Reversion (Oversold)"
            else:
                # Không có tín hiệu rõ ràng
                trading_signal = "neutral"
                signal_confidence = 0
                signal_source = "Không có tín hiệu rõ ràng"
        
        # Lấy thông tin mục tiêu giá
        price_targets = analysis.get('price_targets', {})
        
        # Tạo báo cáo đầy đủ
        report = {
            "symbol": symbol,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "market_analysis": {
                "is_sideways": is_sideways,
                "sideways_score": sideways_score,
                "market_type": "Đi ngang" if is_sideways else "Xu hướng",
                "breakout_prediction": analysis['strategy']['breakout_prediction'],
                "adx": analysis['price_data']['adx'],
                "volatility": analysis['price_data']['atr_ratio'] * 100  # Dưới dạng %
            },
            "trading_signal": {
                "signal": trading_signal,
                "confidence": signal_confidence,
                "source": signal_source
            },
            "position_sizing": {
                "recommended_size": analysis['position_sizing']['adjusted'],
                "reduction": analysis['position_sizing']['reduction_pct']
            },
            "price_levels": {
                "current_price": current_price,
                "entry_price": current_price,
                "take_profit": price_targets.get('tp_price', 0),
                "stop_loss": price_targets.get('sl_price', 0),
                "risk_reward_ratio": price_targets.get('risk_reward_ratio', 0),
                "tp_distance_pct": price_targets.get('tp_distance_pct', 0),
                "sl_distance_pct": price_targets.get('sl_distance_pct', 0)
            },
            "analysis_charts": {
                "sideways_detection": analysis.get('chart_path', ''),
                "divergence_detection": analysis.get('divergence', {}).get('chart_path', '')
            }
        }
        
        # Lưu báo cáo
        report_path = f'reports/market_report_{symbol}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        os.makedirs('reports', exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=4)
        
        logger.info(f"Đã lưu báo cáo phân tích thị trường: {report_path}")
        
        return report