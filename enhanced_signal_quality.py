#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module đánh giá chất lượng tín hiệu giao dịch (Enhanced Signal Quality)

Module này cung cấp các công cụ để đánh giá chất lượng của tín hiệu giao dịch dựa trên
nhiều yếu tố bao gồm sức mạnh xu hướng, khối lượng, tương quan với BTC, và phân tích
đa khung thời gian.
"""

import os
import sys
import json
import time
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('signal_quality.log')
    ]
)
logger = logging.getLogger('signal_quality')

# Thêm thư mục gốc vào sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import các module cần thiết
try:
    from binance_api import BinanceAPI
except ImportError:
    logger.error("Không thể import module binance_api. Hãy đảm bảo bạn đang chạy từ thư mục gốc.")
    binance_api_available = False
else:
    binance_api_available = True

class EnhancedSignalQuality:
    """Lớp đánh giá chất lượng tín hiệu giao dịch nâng cao"""
    
    def __init__(self, binance_api: Optional[Any] = None, config_path: str = 'configs/signal_quality_config.json'):
        """
        Khởi tạo đánh giá chất lượng tín hiệu
        
        Args:
            binance_api: Đối tượng BinanceAPI
            config_path: Đường dẫn đến file cấu hình
        """
        self.binance_api = binance_api
        self.config_path = config_path
        self.config = self._load_config()
        self.signal_history = []
        
    def _load_config(self) -> Dict:
        """
        Tải cấu hình từ file
        
        Returns:
            Dict: Cấu hình đã tải
        """
        default_config = {
            "weights": {
                "trend_strength": 0.20,
                "momentum": 0.15,
                "volume": 0.15,
                "price_pattern": 0.15,
                "higher_timeframe_alignment": 0.15,
                "btc_alignment": 0.10,
                "liquidity": 0.05,
                "market_sentiment": 0.05
            },
            "thresholds": {
                "strong_signal": 70,
                "moderate_signal": 50,
                "weak_signal": 30
            },
            "timeframes": ["5m", "15m", "1h", "4h", "1d"]
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
                
                # Merge với default config
                for key, value in loaded_config.items():
                    default_config[key] = value
                    
                return default_config
            else:
                # Lưu default config
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                with open(self.config_path, 'w') as f:
                    json.dump(default_config, f, indent=4)
                logger.info(f"Đã tạo file cấu hình mặc định tại {self.config_path}")
                return default_config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
            return default_config
    
    def save_config(self) -> bool:
        """
        Lưu cấu hình vào file
        
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Đã lưu cấu hình vào {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {str(e)}")
            return False
    
    def get_market_data(self, symbol: str, timeframe: str, limit: int = 100) -> Optional[pd.DataFrame]:
        """
        Lấy dữ liệu thị trường
        
        Args:
            symbol: Cặp giao dịch
            timeframe: Khung thời gian
            limit: Số lượng nến
            
        Returns:
            Optional[pd.DataFrame]: DataFrame chứa dữ liệu hoặc None nếu có lỗi
        """
        if not self.binance_api:
            logger.warning("BinanceAPI không được cung cấp, không thể lấy dữ liệu thị trường")
            return None
        
        try:
            klines = self.binance_api.get_historical_klines(symbol, timeframe, limit)
            if not klines:
                logger.warning(f"Không có dữ liệu cho {symbol} ({timeframe})")
                return None
                
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Chuyển đổi kiểu dữ liệu
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
                
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu thị trường cho {symbol} ({timeframe}): {str(e)}")
            return None
    
    def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        Tính toán ADX (Average Directional Index)
        
        Args:
            df: DataFrame chứa dữ liệu giá
            period: Số chu kỳ tính ADX
            
        Returns:
            float: Giá trị ADX
        """
        try:
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            
            # Tính +DM và -DM
            plus_dm = np.zeros(len(df))
            minus_dm = np.zeros(len(df))
            
            for i in range(1, len(df)):
                up_move = high[i] - high[i-1]
                down_move = low[i-1] - low[i]
                
                if up_move > down_move and up_move > 0:
                    plus_dm[i] = up_move
                else:
                    plus_dm[i] = 0
                    
                if down_move > up_move and down_move > 0:
                    minus_dm[i] = down_move
                else:
                    minus_dm[i] = 0
            
            # Tính True Range
            tr = np.zeros(len(df))
            for i in range(1, len(df)):
                tr[i] = max(
                    high[i] - low[i],
                    abs(high[i] - close[i-1]),
                    abs(low[i] - close[i-1])
                )
            
            # Tính EMA của +DM, -DM, và TR
            tr_ema = np.zeros(len(df))
            plus_dm_ema = np.zeros(len(df))
            minus_dm_ema = np.zeros(len(df))
            
            # Khởi tạo giá trị đầu tiên
            tr_ema[period] = np.mean(tr[1:period+1])
            plus_dm_ema[period] = np.mean(plus_dm[1:period+1])
            minus_dm_ema[period] = np.mean(minus_dm[1:period+1])
            
            # Tính các giá trị tiếp theo
            k = 2 / (period + 1)
            for i in range(period+1, len(df)):
                tr_ema[i] = tr_ema[i-1] * (1 - k) + tr[i] * k
                plus_dm_ema[i] = plus_dm_ema[i-1] * (1 - k) + plus_dm[i] * k
                minus_dm_ema[i] = minus_dm_ema[i-1] * (1 - k) + minus_dm[i] * k
            
            # Tính +DI và -DI
            plus_di = np.zeros(len(df))
            minus_di = np.zeros(len(df))
            
            for i in range(period, len(df)):
                if tr_ema[i] > 0:
                    plus_di[i] = 100 * plus_dm_ema[i] / tr_ema[i]
                    minus_di[i] = 100 * minus_dm_ema[i] / tr_ema[i]
            
            # Tính DX và ADX
            dx = np.zeros(len(df))
            for i in range(period, len(df)):
                if (plus_di[i] + minus_di[i]) > 0:
                    dx[i] = 100 * abs(plus_di[i] - minus_di[i]) / (plus_di[i] + minus_di[i])
            
            # Tính ADX (EMA của DX)
            adx = np.zeros(len(df))
            adx[2*period-1] = np.mean(dx[period:2*period])
            
            for i in range(2*period, len(df)):
                adx[i] = adx[i-1] * (1 - k) + dx[i] * k
            
            # Trả về giá trị ADX cuối cùng
            return adx[-1]
        except Exception as e:
            logger.error(f"Lỗi khi tính ADX: {str(e)}")
            return 0
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        Tính toán RSI (Relative Strength Index)
        
        Args:
            df: DataFrame chứa dữ liệu giá
            period: Số chu kỳ tính RSI
            
        Returns:
            float: Giá trị RSI
        """
        try:
            close = df['close'].values
            delta = np.diff(close)
            
            # Tách thành gain và loss
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)
            
            # Tính trung bình gain và loss
            avg_gain = np.zeros_like(delta)
            avg_loss = np.zeros_like(delta)
            
            avg_gain[period-1] = np.mean(gain[:period])
            avg_loss[period-1] = np.mean(loss[:period])
            
            # Tính các giá trị tiếp theo
            for i in range(period, len(delta)):
                avg_gain[i] = (avg_gain[i-1] * (period-1) + gain[i]) / period
                avg_loss[i] = (avg_loss[i-1] * (period-1) + loss[i]) / period
            
            # Tính RS và RSI
            rs = avg_gain / np.where(avg_loss == 0, 0.001, avg_loss)
            rsi = 100 - (100 / (1 + rs))
            
            # Trả về giá trị RSI cuối cùng
            return rsi[-1]
        except Exception as e:
            logger.error(f"Lỗi khi tính RSI: {str(e)}")
            return 50
    
    def calculate_volume_ratio(self, df: pd.DataFrame, period: int = 20) -> float:
        """
        Tính toán tỷ lệ khối lượng hiện tại so với trung bình
        
        Args:
            df: DataFrame chứa dữ liệu giá và khối lượng
            period: Số chu kỳ tính trung bình
            
        Returns:
            float: Tỷ lệ khối lượng
        """
        try:
            volume = df['volume'].values
            
            # Tính trung bình khối lượng
            avg_volume = np.mean(volume[-period-1:-1])
            
            # Tính tỷ lệ
            volume_ratio = volume[-1] / avg_volume if avg_volume > 0 else 1.0
            
            return volume_ratio
        except Exception as e:
            logger.error(f"Lỗi khi tính tỷ lệ khối lượng: {str(e)}")
            return 1.0
    
    def calculate_price_action_score(self, df: pd.DataFrame) -> float:
        """
        Tính toán điểm mẫu hình giá
        
        Args:
            df: DataFrame chứa dữ liệu giá
            
        Returns:
            float: Điểm mẫu hình giá
        """
        try:
            # Lấy dữ liệu
            close = df['close'].values
            high = df['high'].values
            low = df['low'].values
            open_price = df['open'].values
            
            # Tính body và shadow
            body = np.abs(close[-1] - open_price[-1])
            upper_shadow = high[-1] - max(close[-1], open_price[-1])
            lower_shadow = min(close[-1], open_price[-1]) - low[-1]
            
            # Kiểm tra mẫu hình
            score = 50  # Điểm trung bình
            
            # Hammer/Inverted Hammer
            if (body > 0 and 
                ((lower_shadow > 2 * body and upper_shadow < 0.5 * body) or  # Hammer
                 (upper_shadow > 2 * body and lower_shadow < 0.5 * body))):  # Inverted Hammer
                score += 20
            
            # Engulfing
            if (len(close) > 1 and 
                ((close[-1] > open_price[-1] and  # Bullish Engulfing
                  open_price[-1] < close[-2] and
                  close[-1] > open_price[-2]) or
                 (close[-1] < open_price[-1] and  # Bearish Engulfing
                  open_price[-1] > close[-2] and
                  close[-1] < open_price[-2]))):
                score += 15
            
            # Doji
            if body < 0.1 * (high[-1] - low[-1]):
                score += 10
            
            # Trend confirmation
            if (len(close) > 2 and
                ((close[-1] > close[-2] > close[-3]) or  # Uptrend
                 (close[-1] < close[-2] < close[-3]))):  # Downtrend
                score += 15
            
            # Range bound
            if (len(close) > 5 and
                max(close[-5:]) - min(close[-5:]) < 0.02 * close[-1]):
                score -= 10
            
            # Giới hạn điểm số
            return max(0, min(100, score))
        except Exception as e:
            logger.error(f"Lỗi khi tính điểm mẫu hình giá: {str(e)}")
            return 50
    
    def get_multi_timeframe_alignment(self, symbol: str, base_timeframe: str, higher_timeframes: List[str] = None) -> float:
        """
        Kiểm tra độ khớp của tín hiệu với các khung thời gian cao hơn
        
        Args:
            symbol: Cặp giao dịch
            base_timeframe: Khung thời gian cơ sở
            higher_timeframes: Danh sách các khung thời gian cao hơn cần kiểm tra
            
        Returns:
            float: Điểm độ khớp (0-100)
        """
        if not higher_timeframes:
            if base_timeframe == '5m':
                higher_timeframes = ['15m', '1h', '4h']
            elif base_timeframe == '15m':
                higher_timeframes = ['1h', '4h', '1d']
            elif base_timeframe == '1h':
                higher_timeframes = ['4h', '1d']
            elif base_timeframe == '4h':
                higher_timeframes = ['1d']
            else:
                higher_timeframes = []
        
        if not higher_timeframes:
            return 50  # Điểm trung bình nếu không có khung thời gian cao hơn
            
        # Lấy dữ liệu
        base_df = self.get_market_data(symbol, base_timeframe)
        if base_df is None:
            return 50
            
        # Tính các chỉ báo cho khung thời gian cơ sở
        base_rsi = self.calculate_rsi(base_df)
        
        # Xác định xu hướng cơ sở (>50: up, <50: down)
        base_trend = 'up' if base_rsi > 50 else 'down'
        
        # Kiểm tra các khung thời gian cao hơn
        alignment_scores = []
        
        for tf in higher_timeframes:
            tf_df = self.get_market_data(symbol, tf)
            if tf_df is None:
                continue
                
            # Tính RSI
            tf_rsi = self.calculate_rsi(tf_df)
            
            # Xác định xu hướng
            tf_trend = 'up' if tf_rsi > 50 else 'down'
            
            # Tính điểm khớp
            if tf_trend == base_trend:
                # Khớp xu hướng
                # Càng xa 50, tín hiệu càng mạnh
                alignment_score = 50 + abs(tf_rsi - 50)
            else:
                # Không khớp xu hướng
                alignment_score = 50 - abs(tf_rsi - 50)
                
            alignment_scores.append(alignment_score)
        
        # Tính điểm trung bình
        if alignment_scores:
            return sum(alignment_scores) / len(alignment_scores)
        else:
            return 50
    
    def get_btc_correlation(self, symbol: str, timeframe: str, period: int = 14) -> Tuple[float, float]:
        """
        Tính toán tương quan với BTC và sức mạnh xu hướng BTC
        
        Args:
            symbol: Cặp giao dịch
            timeframe: Khung thời gian
            period: Số chu kỳ tính tương quan
            
        Returns:
            Tuple[float, float]: (Tương quan, Sức mạnh BTC)
        """
        # Nếu là BTC, tương quan = 1
        if symbol == 'BTCUSDT':
            btc_df = self.get_market_data('BTCUSDT', timeframe)
            if btc_df is None:
                return 1.0, 50
                
            btc_rsi = self.calculate_rsi(btc_df)
            btc_adx = self.calculate_adx(btc_df)
            
            btc_strength = min(100, (btc_adx / 25) * 50 + abs(btc_rsi - 50))
            
            return 1.0, btc_strength
        
        # Lấy dữ liệu
        symbol_df = self.get_market_data(symbol, timeframe)
        btc_df = self.get_market_data('BTCUSDT', timeframe)
        
        if symbol_df is None or btc_df is None:
            return 0.0, 50
            
        # Đảm bảo có cùng index
        symbol_close = symbol_df['close'][-period:]
        btc_close = btc_df['close'][-period:]
        
        if len(symbol_close) != period or len(btc_close) != period:
            return 0.0, 50
            
        # Tính % thay đổi
        symbol_returns = np.diff(symbol_close) / symbol_close[:-1]
        btc_returns = np.diff(btc_close) / btc_close[:-1]
        
        if len(symbol_returns) < 2 or len(btc_returns) < 2:
            return 0.0, 50
            
        # Tính tương quan
        correlation = np.corrcoef(symbol_returns, btc_returns)[0, 1]
        
        # Tính sức mạnh BTC
        btc_rsi = self.calculate_rsi(btc_df)
        btc_adx = self.calculate_adx(btc_df)
        
        btc_strength = min(100, (btc_adx / 25) * 50 + abs(btc_rsi - 50))
        
        return correlation, btc_strength
    
    def get_liquidity_score(self, symbol: str, timeframe: str = '1h') -> float:
        """
        Tính toán điểm thanh khoản
        
        Args:
            symbol: Cặp giao dịch
            timeframe: Khung thời gian
            
        Returns:
            float: Điểm thanh khoản (0-100)
        """
        try:
            df = self.get_market_data(symbol, timeframe, limit=24)
            if df is None:
                return 50
                
            # Tính khối lượng trung bình
            avg_volume = df['volume'].mean()
            
            # Tính spread (ước lượng từ high-low)
            avg_spread = ((df['high'] - df['low']) / df['close']).mean() * 100
            
            # Tính điểm thanh khoản
            volume_score = min(100, avg_volume / 1000) if symbol == 'BTCUSDT' else min(100, avg_volume / 100)
            spread_score = 100 - min(100, avg_spread * 20)
            
            # Tổng hợp
            liquidity_score = (volume_score * 0.7 + spread_score * 0.3)
            
            return liquidity_score
        except Exception as e:
            logger.error(f"Lỗi khi tính điểm thanh khoản: {str(e)}")
            return 50
    
    def get_market_sentiment(self) -> float:
        """
        Lấy tâm lý thị trường tổng thể
        
        Returns:
            float: Điểm tâm lý (0-100, >50 tích cực, <50 tiêu cực)
        """
        try:
            # Sử dụng BTC, ETH, và BNB làm chỉ báo tâm lý chung
            symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
            timeframe = '1h'
            
            sentiments = []
            
            for symbol in symbols:
                df = self.get_market_data(symbol, timeframe)
                if df is None:
                    continue
                    
                rsi = self.calculate_rsi(df)
                volume_ratio = self.calculate_volume_ratio(df)
                
                # Tính điểm tâm lý cho symbol này
                symbol_sentiment = (rsi * 0.6 + min(100, volume_ratio * 50) * 0.4)
                sentiments.append(symbol_sentiment)
            
            # Tính trung bình
            if sentiments:
                return sum(sentiments) / len(sentiments)
            else:
                return 50
        except Exception as e:
            logger.error(f"Lỗi khi tính tâm lý thị trường: {str(e)}")
            return 50
    
    def evaluate_signal_quality(self, symbol: str, timeframe: str) -> Tuple[float, Dict]:
        """
        Đánh giá chất lượng tín hiệu giao dịch
        
        Args:
            symbol: Cặp giao dịch
            timeframe: Khung thời gian
            
        Returns:
            Tuple[float, Dict]: (Điểm chất lượng, Chi tiết đánh giá)
        """
        try:
            # Lấy dữ liệu
            df = self.get_market_data(symbol, timeframe)
            if df is None:
                return 0, {'error': f'Không có dữ liệu cho {symbol} ({timeframe})'}
                
            # Tính các chỉ báo
            adx = self.calculate_adx(df)
            rsi = self.calculate_rsi(df)
            volume_ratio = self.calculate_volume_ratio(df)
            price_action_score = self.calculate_price_action_score(df)
            
            # Tính các điểm
            trend_strength = min(100, adx * 4)
            momentum_score = min(100, abs(rsi - 50) * 2)
            volume_score = min(100, volume_ratio * 100)
            
            # Lấy các yếu tố bổ sung
            higher_tf_alignment = self.get_multi_timeframe_alignment(symbol, timeframe)
            btc_correlation, btc_strength = self.get_btc_correlation(symbol, timeframe)
            
            # Tính điểm tương quan BTC
            if symbol != 'BTCUSDT':
                if abs(btc_correlation) < 0.3:
                    btc_alignment_score = 80  # Tương quan thấp, tín hiệu độc lập tốt
                elif btc_correlation > 0.7 and btc_strength > 70:
                    btc_alignment_score = 90  # BTC mạnh cùng hướng
                elif btc_correlation > 0.7 and btc_strength < 30:
                    btc_alignment_score = 20  # BTC yếu, rủi ro cao
                else:
                    btc_alignment_score = 50  # Trung tính
            else:
                # BTC là chính nó
                btc_alignment_score = 75
            
            # Tính các yếu tố khác
            liquidity_score = self.get_liquidity_score(symbol, timeframe)
            market_sentiment = self.get_market_sentiment()
            
            # Tổng hợp các điểm
            component_scores = {
                'trend_strength': trend_strength,
                'momentum': momentum_score,
                'volume': volume_score,
                'price_pattern': price_action_score,
                'higher_timeframe_alignment': higher_tf_alignment,
                'btc_alignment': btc_alignment_score,
                'liquidity': liquidity_score,
                'market_sentiment': market_sentiment
            }
            
            # Lấy trọng số
            weights = self.config.get('weights', {
                'trend_strength': 0.20,
                'momentum': 0.15,
                'volume': 0.15,
                'price_pattern': 0.15,
                'higher_timeframe_alignment': 0.15,
                'btc_alignment': 0.10,
                'liquidity': 0.05,
                'market_sentiment': 0.05
            })
            
            # Tính điểm cuối cùng
            final_score = sum(component_scores[k] * weights[k] for k in weights)
            
            # Xác định hướng tín hiệu
            signal_direction = 'BUY' if rsi > 50 else 'SELL'
            
            # Xác định mức độ mạnh
            strength_thresholds = self.config.get('thresholds', {
                'strong_signal': 70,
                'moderate_signal': 50,
                'weak_signal': 30
            })
            
            if final_score >= strength_thresholds.get('strong_signal', 70):
                signal_strength = 'STRONG'
            elif final_score >= strength_thresholds.get('moderate_signal', 50):
                signal_strength = 'MODERATE'
            elif final_score >= strength_thresholds.get('weak_signal', 30):
                signal_strength = 'WEAK'
            else:
                signal_strength = 'VERY_WEAK'
            
            # Tạo kết quả chi tiết
            details = {
                'timestamp': int(time.time()),
                'symbol': symbol,
                'timeframe': timeframe,
                'final_score': final_score,
                'signal_direction': signal_direction,
                'signal_strength': signal_strength,
                'component_scores': component_scores,
                'weights': weights,
                'indicators': {
                    'adx': adx,
                    'rsi': rsi,
                    'volume_ratio': volume_ratio
                },
                'btc_correlation': btc_correlation,
                'btc_strength': btc_strength
            }
            
            # Lưu vào lịch sử
            self.signal_history.append(details)
            
            # Giới hạn kích thước lịch sử
            if len(self.signal_history) > 1000:
                self.signal_history = self.signal_history[-1000:]
            
            logger.info(f"Đánh giá tín hiệu cho {symbol} ({timeframe}): {final_score:.2f}, hướng: {signal_direction}, mức độ: {signal_strength}")
            
            return final_score, details
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá chất lượng tín hiệu: {str(e)}")
            return 0, {'error': str(e)}
    
    def get_recent_signals(self, limit: int = 10, symbol: str = None) -> List[Dict]:
        """
        Lấy các tín hiệu gần đây
        
        Args:
            limit: Số lượng tín hiệu tối đa
            symbol: Lọc theo cặp giao dịch
            
        Returns:
            List[Dict]: Danh sách tín hiệu
        """
        if symbol:
            filtered = [s for s in self.signal_history if s.get('symbol') == symbol]
            return filtered[-limit:] if filtered else []
        else:
            return self.signal_history[-limit:] if self.signal_history else []
    
    def save_signal_history(self, file_path: str = 'signal_history.json') -> bool:
        """
        Lưu lịch sử tín hiệu vào file
        
        Args:
            file_path: Đường dẫn đến file
            
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(self.signal_history, f, indent=4)
            logger.info(f"Đã lưu lịch sử tín hiệu vào {file_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu lịch sử tín hiệu: {str(e)}")
            return False
    
    def load_signal_history(self, file_path: str = 'signal_history.json') -> bool:
        """
        Tải lịch sử tín hiệu từ file
        
        Args:
            file_path: Đường dẫn đến file
            
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    self.signal_history = json.load(f)
                logger.info(f"Đã tải lịch sử tín hiệu từ {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Lỗi khi tải lịch sử tín hiệu: {str(e)}")
            return False
    
    def analyze_signal_performance(self, days: int = 30, min_score: float = 70) -> Dict:
        """
        Phân tích hiệu suất của các tín hiệu
        
        Args:
            days: Số ngày cần phân tích
            min_score: Điểm tín hiệu tối thiểu
            
        Returns:
            Dict: Thông tin phân tích
        """
        now = int(time.time())
        start_time = now - days * 24 * 3600
        
        # Lọc tín hiệu trong khoảng thời gian
        signals = [s for s in self.signal_history 
                  if s.get('timestamp', 0) >= start_time and s.get('final_score', 0) >= min_score]
        
        if not signals:
            return {'error': 'Không đủ dữ liệu'}
        
        # Phân loại theo symbol
        symbol_signals = {}
        for s in signals:
            symbol = s.get('symbol')
            if symbol not in symbol_signals:
                symbol_signals[symbol] = []
            symbol_signals[symbol].append(s)
        
        # Phân tích mỗi symbol
        symbol_analysis = {}
        for symbol, sym_signals in symbol_signals.items():
            # Sắp xếp theo thời gian
            sym_signals.sort(key=lambda x: x.get('timestamp', 0))
            
            # Tính số lượng tín hiệu theo hướng
            buy_signals = [s for s in sym_signals if s.get('signal_direction') == 'BUY']
            sell_signals = [s for s in sym_signals if s.get('signal_direction') == 'SELL']
            
            # Tính điểm trung bình
            avg_score = sum(s.get('final_score', 0) for s in sym_signals) / len(sym_signals) if sym_signals else 0
            
            # Phân tích xu hướng điểm
            if len(sym_signals) >= 2:
                first_half = sym_signals[:len(sym_signals)//2]
                second_half = sym_signals[len(sym_signals)//2:]
                
                first_avg = sum(s.get('final_score', 0) for s in first_half) / len(first_half) if first_half else 0
                second_avg = sum(s.get('final_score', 0) for s in second_half) / len(second_half) if second_half else 0
                
                score_trend = second_avg - first_avg
            else:
                score_trend = 0
            
            symbol_analysis[symbol] = {
                'total_signals': len(sym_signals),
                'buy_signals': len(buy_signals),
                'sell_signals': len(sell_signals),
                'avg_score': avg_score,
                'score_trend': score_trend,
                'trend_direction': 'improving' if score_trend > 5 else ('declining' if score_trend < -5 else 'stable'),
                'top_signal': max(sym_signals, key=lambda x: x.get('final_score', 0)) if sym_signals else None
            }
        
        # Tổng hợp
        total_signals = len(signals)
        avg_score_overall = sum(s.get('final_score', 0) for s in signals) / total_signals if total_signals > 0 else 0
        
        return {
            'period_days': days,
            'min_score': min_score,
            'total_signals': total_signals,
            'avg_score': avg_score_overall,
            'symbols_analyzed': len(symbol_analysis),
            'symbol_details': symbol_analysis,
            'top_symbols': sorted(symbol_analysis.keys(), 
                                 key=lambda s: symbol_analysis[s]['avg_score'], 
                                 reverse=True)[:5] if symbol_analysis else []
        }


def main():
    """Hàm chính để test EnhancedSignalQuality"""
    # Khởi tạo BinanceAPI
    try:
        from binance_api import BinanceAPI
        binance_api = BinanceAPI()
    except ImportError:
        binance_api = None
        print("Không thể import module binance_api, sẽ chạy với dữ liệu mẫu.")
    
    # Khởi tạo EnhancedSignalQuality
    evaluator = EnhancedSignalQuality(binance_api=binance_api)
    
    # Đánh giá tín hiệu cho BTC
    try:
        score, details = evaluator.evaluate_signal_quality('BTCUSDT', '1h')
        
        print("\n=== Đánh giá tín hiệu BTC/USDT (1h) ===")
        print(f"Điểm chất lượng: {score:.2f}")
        print(f"Hướng tín hiệu: {details['signal_direction']}")
        print(f"Mức độ mạnh: {details['signal_strength']}")
        print("\nĐiểm thành phần:")
        for component, value in details['component_scores'].items():
            print(f"  {component}: {value:.2f}")
        
        print("\nChỉ báo kỹ thuật:")
        for indicator, value in details['indicators'].items():
            print(f"  {indicator}: {value:.2f}")
            
        print(f"\nTương quan với BTC: {details['btc_correlation']:.2f}")
    except Exception as e:
        print(f"Lỗi khi đánh giá tín hiệu: {str(e)}")
    
    # Phân tích nhiều cặp giao dịch
    try:
        if binance_api is not None:
            symbols = ['ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
            
            print("\n=== Đánh giá tín hiệu cho nhiều cặp giao dịch ===")
            for symbol in symbols:
                score, details = evaluator.evaluate_signal_quality(symbol, '1h')
                print(f"{symbol}: {score:.2f} - {details['signal_direction']} ({details['signal_strength']})")
    except Exception as e:
        print(f"Lỗi khi đánh giá nhiều tín hiệu: {str(e)}")


if __name__ == "__main__":
    main()