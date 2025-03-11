#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Market Regime Detector - Phát hiện chế độ thị trường
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Union, Optional, Any

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('market_regime_detector')

class MarketRegimeDetector:
    """
    Phát hiện chế độ thị trường dựa trên các chỉ báo kỹ thuật
    """
    
    def __init__(
        self, 
        window_size: int = 20,
        ema_fast: int = 5,
        ema_slow: int = 20,
        rsi_window: int = 14,
        rsi_thresholds: Tuple[int, int] = (30, 70),
        volatility_window: int = 14
    ):
        """
        Khởi tạo Market Regime Detector
        
        Args:
            window_size: Kích thước cửa sổ phân tích
            ema_fast: Chu kỳ EMA nhanh
            ema_slow: Chu kỳ EMA chậm
            rsi_window: Chu kỳ RSI
            rsi_thresholds: Ngưỡng RSI (oversold, overbought)
            volatility_window: Chu kỳ tính biến động
        """
        self.window_size = window_size
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.rsi_window = rsi_window
        self.rsi_thresholds = rsi_thresholds
        self.volatility_window = volatility_window
        
        logger.info(f"Đã khởi tạo Market Regime Detector với window_size={window_size}")
    
    def detect_regimes(self, df: pd.DataFrame) -> pd.Series:
        """
        Phát hiện chế độ thị trường
        
        Args:
            df: DataFrame chứa dữ liệu giá
        
        Returns:
            Series chứa các chế độ thị trường
        """
        # Phiên bản đơn giản: mặc định là 'neutral'
        regimes = pd.Series(['neutral'] * len(df), index=df.index)
        
        try:
            # Tính các chỉ báo cần thiết
            if 'close' in df.columns:
                # EMA
                if 'ema_fast' not in df.columns:
                    df['ema_fast'] = df['close'].ewm(span=self.ema_fast, adjust=False).mean()
                if 'ema_slow' not in df.columns:
                    df['ema_slow'] = df['close'].ewm(span=self.ema_slow, adjust=False).mean()
                
                # Volatility (đơn giản: độ lệch chuẩn của giá)
                if 'volatility' not in df.columns:
                    df['volatility'] = df['close'].pct_change().rolling(self.volatility_window).std()
                
                # RSI
                if 'rsi' not in df.columns:
                    delta = df['close'].diff()
                    gain = delta.where(delta > 0, 0)
                    loss = -delta.where(delta < 0, 0)
                    
                    avg_gain = gain.rolling(self.rsi_window).mean()
                    avg_loss = loss.rolling(self.rsi_window).mean()
                    
                    rs = avg_gain / avg_loss.replace(0, 0.001)  # Tránh chia cho 0
                    df['rsi'] = 100 - (100 / (1 + rs))
                
                # Phát hiện chế độ thị trường
                for i in range(self.window_size, len(df)):
                    # Xu hướng
                    trend_up = df['ema_fast'].iloc[i] > df['ema_slow'].iloc[i]
                    price_above_ema = df['close'].iloc[i] > df['ema_slow'].iloc[i]
                    
                    # Đánh giá biến động
                    high_volatility = df['volatility'].iloc[i] > df['volatility'].iloc[i-self.window_size:i].quantile(0.8)
                    
                    # Xác định chế độ thị trường
                    if trend_up and price_above_ema:
                        regimes.iloc[i] = 'trending_up'
                    elif not trend_up and not price_above_ema:
                        regimes.iloc[i] = 'trending_down'
                    elif high_volatility:
                        regimes.iloc[i] = 'volatile'
                    elif df['volatility'].iloc[i] < df['volatility'].iloc[i-self.window_size:i].quantile(0.3):
                        regimes.iloc[i] = 'ranging'
                    else:
                        regimes.iloc[i] = 'neutral'
        
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện chế độ thị trường: {str(e)}")
        
        return regimes
    
    def detect_regime_changes(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Phát hiện các thay đổi chế độ thị trường
        
        Args:
            df: DataFrame chứa dữ liệu giá
        
        Returns:
            Dict chứa thông tin về thay đổi chế độ thị trường
        """
        # Phát hiện chế độ thị trường
        regimes = self.detect_regimes(df)
        
        # Phát hiện các thay đổi
        regime_changes = {}
        prev_regime = None
        
        for i, regime in enumerate(regimes):
            if regime != prev_regime:
                if i > 0:  # Bỏ qua phần tử đầu tiên
                    regime_changes[df.index[i]] = {
                        'from': prev_regime,
                        'to': regime
                    }
                prev_regime = regime
        
        return {
            'regimes': regimes,
            'changes': regime_changes
        }
    
    def get_current_regime(self, df: pd.DataFrame) -> str:
        """
        Lấy chế độ thị trường hiện tại
        
        Args:
            df: DataFrame chứa dữ liệu giá
        
        Returns:
            Chế độ thị trường hiện tại
        """
        # Phát hiện chế độ thị trường
        regimes = self.detect_regimes(df)
        
        # Lấy chế độ cuối cùng
        if len(regimes) > 0:
            return regimes.iloc[-1]
        else:
            return 'neutral'