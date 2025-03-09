"""
Enhanced Market Regime Detector - Phát hiện chế độ thị trường nâng cao

Module này cung cấp công cụ phát hiện chế độ thị trường với 6 chế độ:
- Trending Bullish (Xu hướng tăng)
- Trending Bearish (Xu hướng giảm)
- Ranging Narrow (Dao động hẹp)
- Ranging Wide (Dao động rộng)
- Volatile Breakout (Bứt phá mạnh)
- Quiet Accumulation (Tích lũy yên lặng)

Phát triển nâng cao so với phiên bản cũ với:
- Hệ thống tính độ tin cậy
- Phát hiện chuyển tiếp giữa các chế độ
- Bộ lọc nhiễu
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime
import os
import json
from typing import Dict, List, Tuple, Optional, Union, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('enhanced_market_regime_detector')

class EnhancedMarketRegimeDetector:
    """
    Phát hiện và phân loại chế độ thị trường với 6 loại chế độ khác nhau
    dựa trên các chỉ báo kỹ thuật và phân tích hành vi giá.
    """
    
    def __init__(self, lookback_period: int = 20, use_ml_enhancement: bool = False, 
                use_confidence_threshold: bool = True, save_history: bool = True):
        """
        Khởi tạo Market Regime Detector nâng cao.
        
        Args:
            lookback_period (int): Khoảng thời gian nhìn lại (số nến)
            use_ml_enhancement (bool): Sử dụng ML để cải thiện độ chính xác
            use_confidence_threshold (bool): Sử dụng ngưỡng tin cậy để chuyển đổi chế độ
            save_history (bool): Lưu lịch sử phát hiện chế độ
        """
        self.lookback_period = lookback_period
        self.use_ml_enhancement = use_ml_enhancement
        self.use_confidence_threshold = use_confidence_threshold
        self.save_history = save_history
        
        # Tất cả các chế độ thị trường
        self.regimes = [
            'trending_bullish',   # Xu hướng tăng
            'trending_bearish',   # Xu hướng giảm
            'ranging_narrow',     # Dao động hẹp
            'ranging_wide',       # Dao động rộng
            'volatile_breakout',  # Bứt phá mạnh 
            'quiet_accumulation', # Tích lũy yên lặng
            'neutral'             # Trung tính (Không thể xác định rõ ràng)
        ]
        
        # Chế độ hiện tại và lịch sử
        self.current_regime = 'neutral'
        self.regime_history = []
        
        # Độ tin cậy cho mỗi chế độ (dùng cho chuyển tiếp mượt)
        self.confidence_scores = {regime: 0.0 for regime in self.regimes}
        self.min_confidence_for_transition = 0.60  # Ngưỡng tối thiểu để chuyển chế độ
        
        # Lần cập nhật cuối
        self.last_update_time = None
        
        # Cấu hình
        self.config = {
            # Ngưỡng phát hiện xu hướng
            'adx_trend_threshold': 25,         # ADX > 25 được coi là xu hướng
            'ma_lookback': [20, 50, 100],      # Các MA dùng để kiểm tra xu hướng
            
            # Ngưỡng phát hiện vùng dao động
            'bollinger_width_narrow': 0.03,    # BB width < 3% là dao động hẹp
            'bollinger_width_wide': 0.06,      # BB width > 6% là dao động rộng
            
            # Ngưỡng phát hiện bứt phá
            'volatility_breakout_threshold': 2.5,  # ATR cao gấp 2.5 lần trung bình
            'volume_surge_threshold': 2.0,         # Volume cao gấp 2 lần trung bình
            
            # Ngưỡng phát hiện tích lũy
            'volume_decline_threshold': 0.7,    # Volume thấp hơn 70% trung bình
            'volatility_quiet_threshold': 0.6,  # ATR thấp hơn 60% trung bình
            
            # Tỷ trọng cho các chỉ báo
            'weights': {
                'price_action': 0.35,  # Hành vi giá
                'indicators': 0.35,    # Chỉ báo kỹ thuật
                'volume': 0.20,        # Khối lượng
                'volatility': 0.10     # Biến động
            },
            
            # Tỷ trọng cho chế độ trước đó (độ nhớt)
            'previous_regime_weight': 0.30  # 30% cho chế độ trước, 70% cho phát hiện mới
        }
        
        # Đảm bảo thư mục data tồn tại
        if self.save_history:
            os.makedirs('data/regimes', exist_ok=True)
    
    def detect_regime(self, df: pd.DataFrame, symbol: str = None) -> Dict:
        """
        Phát hiện chế độ thị trường dựa trên dữ liệu nến.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu nến OHLCV
            symbol (str, optional): Cặp tiền tệ
            
        Returns:
            Dict: Kết quả phát hiện gồm chế độ thị trường, độ tin cậy và các thông tin phụ
        """
        try:
            if df.empty or len(df) < self.lookback_period:
                logger.warning(f"Không đủ dữ liệu cho phát hiện chế độ thị trường (cần ít nhất {self.lookback_period} nến)")
                return {
                    'regime': 'neutral',
                    'confidence': 0.0,
                    'timestamp': datetime.now().isoformat(),
                    'detection_factors': {}
                }
            
            # Chuẩn bị dữ liệu
            df = self._prepare_data(df)
            
            # Tính toán các chỉ báo cần thiết nếu chưa có
            df = self._calculate_indicators(df)
            
            # Phát hiện chế độ
            detection_factors = self._detect_regime_factors(df)
            
            # Tính điểm cho mỗi chế độ
            scores = self._calculate_regime_scores(detection_factors)
            
            # Cập nhật điểm tin cậy cho mỗi chế độ
            self._update_confidence_scores(scores)
            
            # Xác định chế độ thị trường tối ưu
            best_regime, confidence = self._determine_best_regime()
            
            # Cập nhật chế độ hiện tại
            self._update_current_regime(best_regime, confidence)
            
            # Lưu lịch sử
            if self.save_history and symbol:
                self._save_regime_history(symbol)
                
            # Kết quả phát hiện
            result = {
                'regime': self.current_regime,
                'confidence': confidence,
                'timestamp': datetime.now().isoformat(),
                'detection_factors': detection_factors,
                'all_scores': {r: round(s, 2) for r, s in scores.items()},
                'all_confidence': {r: round(s, 2) for r, s in self.confidence_scores.items()}
            }
            
            # Lưu lịch sử
            self.last_update_time = datetime.now()
            self.regime_history.append({
                'timestamp': self.last_update_time,
                'regime': self.current_regime,
                'confidence': confidence
            })
            
            # Giữ giới hạn lịch sử
            if len(self.regime_history) > 1000:
                self.regime_history = self.regime_history[-1000:]
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện chế độ thị trường: {str(e)}")
            return {
                'regime': 'neutral',
                'confidence': 0.0,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def get_regime_transition_probability(self, from_regime: str, to_regime: str) -> float:
        """
        Ước tính xác suất chuyển đổi từ chế độ này sang chế độ khác.
        
        Args:
            from_regime (str): Chế độ thị trường nguồn
            to_regime (str): Chế độ thị trường đích
            
        Returns:
            float: Xác suất chuyển đổi (0-1)
        """
        # Ma trận chuyển đổi, dựa trên quan sát thực nghiệm
        # Giá trị cao hơn = khả năng chuyển đổi cao hơn
        transition_matrix = {
            'trending_bullish': {
                'trending_bullish': 0.70,
                'trending_bearish': 0.05,
                'ranging_narrow': 0.10,
                'ranging_wide': 0.05,
                'volatile_breakout': 0.05,
                'quiet_accumulation': 0.03,
                'neutral': 0.02
            },
            'trending_bearish': {
                'trending_bullish': 0.05,
                'trending_bearish': 0.70,
                'ranging_narrow': 0.10,
                'ranging_wide': 0.05,
                'volatile_breakout': 0.05,
                'quiet_accumulation': 0.03,
                'neutral': 0.02
            },
            'ranging_narrow': {
                'trending_bullish': 0.15,
                'trending_bearish': 0.15,
                'ranging_narrow': 0.40,
                'ranging_wide': 0.15,
                'volatile_breakout': 0.10,
                'quiet_accumulation': 0.03,
                'neutral': 0.02
            },
            'ranging_wide': {
                'trending_bullish': 0.15,
                'trending_bearish': 0.15,
                'ranging_narrow': 0.15,
                'ranging_wide': 0.30,
                'volatile_breakout': 0.20,
                'quiet_accumulation': 0.03,
                'neutral': 0.02
            },
            'volatile_breakout': {
                'trending_bullish': 0.25,
                'trending_bearish': 0.25,
                'ranging_narrow': 0.05,
                'ranging_wide': 0.20,
                'volatile_breakout': 0.20,
                'quiet_accumulation': 0.03,
                'neutral': 0.02
            },
            'quiet_accumulation': {
                'trending_bullish': 0.15,
                'trending_bearish': 0.15,
                'ranging_narrow': 0.30,
                'ranging_wide': 0.15,
                'volatile_breakout': 0.20,
                'quiet_accumulation': 0.03,
                'neutral': 0.02
            },
            'neutral': {
                'trending_bullish': 0.15,
                'trending_bearish': 0.15,
                'ranging_narrow': 0.20,
                'ranging_wide': 0.20,
                'volatile_breakout': 0.15,
                'quiet_accumulation': 0.10,
                'neutral': 0.05
            }
        }
        
        if from_regime in transition_matrix and to_regime in transition_matrix[from_regime]:
            return transition_matrix[from_regime][to_regime]
        
        # Mặc định nếu không có trong ma trận
        return 0.01
    
    def get_suitable_trading_approach(self, regime: str = None) -> Dict:
        """
        Đưa ra phương pháp giao dịch phù hợp với chế độ thị trường cụ thể.
        
        Args:
            regime (str, optional): Chế độ thị trường. Nếu None, sử dụng chế độ hiện tại.
            
        Returns:
            Dict: Thông tin phương pháp giao dịch phù hợp
        """
        if regime is None:
            regime = self.current_regime
            
        trading_approaches = {
            'trending_bullish': {
                'suitable_strategies': ['trend_following', 'pullback', 'breakout'],
                'timeframes': ['15m', '1h', '4h'],
                'indicators': ['Moving Averages', 'MACD', 'ADX'],
                'entry_approach': 'Mua tại pullback về MA, hoặc sau khi phá vỡ kháng cự',
                'stop_loss': 'Dưới MA dài hạn hoặc swing low gần nhất',
                'risk_level': 'medium',
                'target_rr': 2.0
            },
            'trending_bearish': {
                'suitable_strategies': ['trend_following', 'pullback', 'breakout'],
                'timeframes': ['15m', '1h', '4h'],
                'indicators': ['Moving Averages', 'MACD', 'ADX'],
                'entry_approach': 'Bán tại pullback lên MA, hoặc sau khi phá vỡ hỗ trợ',
                'stop_loss': 'Trên MA dài hạn hoặc swing high gần nhất',
                'risk_level': 'medium',
                'target_rr': 2.0
            },
            'ranging_narrow': {
                'suitable_strategies': ['range', 'mean_reversion', 'support_resistance'],
                'timeframes': ['5m', '15m', '1h'],
                'indicators': ['Bollinger Bands', 'RSI', 'Stochastic'],
                'entry_approach': 'Mua gần hỗ trợ, bán gần kháng cự trong vùng dao động đã xác định',
                'stop_loss': 'Ngoài vùng dao động một chút',
                'risk_level': 'low',
                'target_rr': 1.5
            },
            'ranging_wide': {
                'suitable_strategies': ['range', 'breakout', 'swing'],
                'timeframes': ['15m', '1h', '4h'],
                'indicators': ['Bollinger Bands', 'RSI', 'Support/Resistance'],
                'entry_approach': 'Mua gần hỗ trợ mạnh, bán gần kháng cự mạnh, với stop rộng hơn',
                'stop_loss': 'Dưới/trên vùng hỗ trợ/kháng cự quan trọng',
                'risk_level': 'medium',
                'target_rr': 1.8
            },
            'volatile_breakout': {
                'suitable_strategies': ['breakout', 'momentum', 'trend_reversal'],
                'timeframes': ['5m', '15m', '1h'],
                'indicators': ['Volume', 'ATR', 'Fibonacci'],
                'entry_approach': 'Mua/bán khi phá vỡ mức giá quan trọng với volume tăng',
                'stop_loss': 'Chặt chẽ, dưới mức breakout đối với lệnh mua',
                'risk_level': 'high',
                'target_rr': 2.5
            },
            'quiet_accumulation': {
                'suitable_strategies': ['breakout_anticipation', 'ichimoku', 'divergence'],
                'timeframes': ['1h', '4h', '1d'],
                'indicators': ['Volume', 'Ichimoku', 'OBV'],
                'entry_approach': 'Tích lũy vị thế dần dần hoặc đợi tín hiệu break khỏi vùng tích lũy',
                'stop_loss': 'Dưới vùng tích lũy',
                'risk_level': 'low',
                'target_rr': 3.0
            },
            'neutral': {
                'suitable_strategies': ['wait', 'very_selective', 'reduced_size'],
                'timeframes': ['1h', '4h', '1d'],
                'indicators': ['Multiple confirmations needed'],
                'entry_approach': 'Chỉ giao dịch với tín hiệu rất rõ ràng, giảm size',
                'stop_loss': 'Conservative, based on key levels',
                'risk_level': 'very_low',
                'target_rr': 2.0
            }
        }
        
        if regime in trading_approaches:
            return trading_approaches[regime]
        else:
            return trading_approaches['neutral']  # Mặc định nếu không tìm thấy
    
    def get_historical_regimes(self, symbol: str = None) -> List[Dict]:
        """
        Lấy lịch sử phát hiện chế độ thị trường.
        
        Args:
            symbol (str, optional): Cặp tiền tệ để tải lịch sử
            
        Returns:
            List[Dict]: Lịch sử phát hiện chế độ thị trường
        """
        if not self.save_history:
            return self.regime_history
            
        if symbol and os.path.exists(f'data/regimes/{symbol}_regimes.json'):
            try:
                with open(f'data/regimes/{symbol}_regimes.json', 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Lỗi khi đọc lịch sử chế độ: {str(e)}")
                
        return self.regime_history
    
    def _prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Chuẩn bị dữ liệu cho phát hiện chế độ."""
        # Tạo bản sao để tránh ảnh hưởng đến df gốc
        df = df.copy()
        
        # Kiểm tra các cột cần thiết
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in df.columns:
                logger.warning(f"Thiếu cột {col} trong dữ liệu")
                if col == 'volume':
                    # Tạo cột volume giả nếu không có
                    df['volume'] = 1
                else:
                    raise ValueError(f"Thiếu cột {col} trong dữ liệu")
        
        return df
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tính toán các chỉ báo kỹ thuật cần thiết cho phát hiện chế độ."""
        # Tạo bản sao để tránh ảnh hưởng đến df gốc
        df = df.copy()
        
        # === Chỉ báo xu hướng ===
        
        # Moving Averages
        for ma_period in self.config['ma_lookback']:
            if f'MA{ma_period}' not in df.columns:
                df[f'MA{ma_period}'] = df['close'].rolling(window=ma_period).mean()
        
        # ADX - Average Directional Index
        if 'ADX' not in df.columns:
            # Giả lập ADX nếu chưa có, trong thực tế sẽ tính toán đúng
            window = 14
            tr1 = abs(df['high'] - df['low'])
            tr2 = abs(df['high'] - df['close'].shift(1))
            tr3 = abs(df['low'] - df['close'].shift(1))
            tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
            atr = tr.rolling(window=window).mean()
            
            # +DM và -DM
            plus_dm = (df['high'] - df['high'].shift(1)).clip(lower=0)
            minus_dm = (df['low'].shift(1) - df['low']).clip(lower=0)
            plus_dm[(df['high'] - df['high'].shift(1)) <= (df['low'].shift(1) - df['low'])] = 0
            minus_dm[(df['low'].shift(1) - df['low']) <= (df['high'] - df['high'].shift(1))] = 0
            
            # +DI và -DI
            plus_di = 100 * (plus_dm.rolling(window=window).mean() / atr)
            minus_di = 100 * (minus_dm.rolling(window=window).mean() / atr)
            
            # Chỉ số định hướng (DX)
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            
            # ADX
            df['ADX'] = dx.rolling(window=window).mean()
            df['Plus_DI'] = plus_di
            df['Minus_DI'] = minus_di
        
        # Trend Strength (phần trăm biến động trung bình của giá)
        if 'Trend_Strength' not in df.columns:
            df['Price_Change'] = df['close'].pct_change()
            df['Trend_Strength'] = df['Price_Change'].rolling(window=self.lookback_period).mean() * self.lookback_period
        
        # Trend Direction (phương hướng xu hướng)
        if 'Trend_Direction' not in df.columns:
            df['Trend_Direction'] = np.where(df['MA20'] > df['MA50'], 1, -1)
        
        # === Chỉ báo dao động ===
        
        # Bollinger Bands
        if 'BB_Width' not in df.columns:
            window = 20
            df['BB_Middle'] = df['close'].rolling(window=window).mean()
            df['BB_Std'] = df['close'].rolling(window=window).std()
            df['BB_Upper'] = df['BB_Middle'] + 2 * df['BB_Std']
            df['BB_Lower'] = df['BB_Middle'] - 2 * df['BB_Std']
            df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle']
        
        # RSI
        if 'RSI' not in df.columns:
            window = 14
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=window).mean()
            loss = -delta.where(delta < 0, 0).rolling(window=window).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
        
        # === Chỉ báo biến động ===
        
        # ATR
        if 'ATR' not in df.columns:
            window = 14
            tr1 = abs(df['high'] - df['low'])
            tr2 = abs(df['high'] - df['close'].shift(1))
            tr3 = abs(df['low'] - df['close'].shift(1))
            tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
            df['ATR'] = tr.rolling(window=window).mean()
            df['ATR_Ratio'] = df['ATR'] / df['ATR'].rolling(window=window*2).mean()
        
        # Price Volatility
        if 'Price_Volatility' not in df.columns:
            df['Price_Volatility'] = df['close'].pct_change().rolling(window=self.lookback_period).std()
        
        # === Chỉ báo khối lượng ===
        
        # Volume Ratio
        if 'Volume_Ratio' not in df.columns:
            df['Volume_Ratio'] = df['volume'] / df['volume'].rolling(window=self.lookback_period).mean()
        
        # Volume Trend
        if 'Volume_Trend' not in df.columns:
            df['Volume_Trend'] = df['volume'].pct_change(5)
        
        # OBV (On-Balance Volume)
        if 'OBV' not in df.columns:
            df['OBV'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
            df['OBV_Ratio'] = df['OBV'].diff(5) / df['OBV'].shift(5)
        
        # Lọc bỏ các hàng có NaN
        df = df.dropna()
        
        return df
    
    def _detect_regime_factors(self, df: pd.DataFrame) -> Dict:
        """Phát hiện các yếu tố chỉ báo cho từng chế độ thị trường."""
        # Lấy giá trị mới nhất
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        # Kiểm tra xu hướng tăng
        trending_bullish_factors = {
            'price_above_ma': latest['close'] > latest['MA50'],
            'ma_alignment': latest['MA20'] > latest['MA50'],
            'adx_high': latest['ADX'] > self.config['adx_trend_threshold'],
            'positive_trend': latest['Trend_Strength'] > 0,
            'directional_strength': latest.get('Plus_DI', 0) > latest.get('Minus_DI', 0),
            'volume_confirming': latest['Volume_Ratio'] > 1.0
        }
        
        # Kiểm tra xu hướng giảm
        trending_bearish_factors = {
            'price_below_ma': latest['close'] < latest['MA50'],
            'ma_alignment': latest['MA20'] < latest['MA50'],
            'adx_high': latest['ADX'] > self.config['adx_trend_threshold'],
            'negative_trend': latest['Trend_Strength'] < 0,
            'directional_strength': latest.get('Minus_DI', 0) > latest.get('Plus_DI', 0),
            'volume_confirming': latest['Volume_Ratio'] > 1.0
        }
        
        # Kiểm tra dao động hẹp
        ranging_narrow_factors = {
            'low_bb_width': latest['BB_Width'] < self.config['bollinger_width_narrow'],
            'price_near_ma': abs(latest['close'] - latest['MA20']) / latest['close'] < 0.01,
            'adx_low': latest['ADX'] < self.config['adx_trend_threshold'],
            'low_volatility': latest['Price_Volatility'] < df['Price_Volatility'].rolling(window=50).mean().iloc[-1] * 0.8,
            'neutral_rsi': latest['RSI'] > 40 and latest['RSI'] < 60
        }
        
        # Kiểm tra dao động rộng
        ranging_wide_factors = {
            'high_bb_width': latest['BB_Width'] > self.config['bollinger_width_wide'],
            'adx_medium': latest['ADX'] > 15 and latest['ADX'] < self.config['adx_trend_threshold'],
            'price_swings': abs(latest['high'] - latest['low']) / latest['close'] > 0.02,
            'medium_volatility': latest['Price_Volatility'] > df['Price_Volatility'].rolling(window=50).mean().iloc[-1] * 1.2
        }
        
        # Kiểm tra bứt phá mạnh
        volatile_breakout_factors = {
            'high_atr_ratio': latest['ATR_Ratio'] > self.config['volatility_breakout_threshold'],
            'volume_surge': latest['Volume_Ratio'] > self.config['volume_surge_threshold'],
            'price_momentum': abs(latest['close'] - prev['close']) / prev['close'] > 0.02,
            'ma_cross': (latest['MA20'] > latest['MA50'] and prev['MA20'] < prev['MA50']) or \
                         (latest['MA20'] < latest['MA50'] and prev['MA20'] > prev['MA50']),
            'extreme_rsi': latest['RSI'] > 75 or latest['RSI'] < 25
        }
        
        # Kiểm tra tích lũy yên lặng
        quiet_accumulation_factors = {
            'low_atr_ratio': latest['ATR_Ratio'] < self.config['volatility_quiet_threshold'],
            'low_volume': latest['Volume_Ratio'] < self.config['volume_decline_threshold'],
            'tight_range': abs(latest['high'] - latest['low']) / latest['close'] < 0.01,
            'price_sideways': abs(latest['close'] - df['close'].rolling(window=10).mean().iloc[-1]) / latest['close'] < 0.005,
            'obv_divergence': (latest['OBV_Ratio'] > 0 and latest['Trend_Strength'] < 0) or \
                              (latest['OBV_Ratio'] < 0 and latest['Trend_Strength'] > 0)
        }
        
        return {
            'trending_bullish': trending_bullish_factors,
            'trending_bearish': trending_bearish_factors,
            'ranging_narrow': ranging_narrow_factors,
            'ranging_wide': ranging_wide_factors,
            'volatile_breakout': volatile_breakout_factors,
            'quiet_accumulation': quiet_accumulation_factors
        }
    
    def _calculate_regime_scores(self, detection_factors: Dict) -> Dict:
        """Tính điểm cho mỗi chế độ dựa trên các yếu tố phát hiện."""
        scores = {}
        
        # Tính điểm cho từng chế độ
        for regime, factors in detection_factors.items():
            # Đếm số yếu tố đúng
            true_factors = sum(1 for factor in factors.values() if factor)
            # Tính tỷ lệ yếu tố đúng
            score = true_factors / len(factors) if len(factors) > 0 else 0
            scores[regime] = score
        
        # Điểm cho chế độ trung tính
        scores['neutral'] = 0.3  # Mặc định
        
        # Điều chỉnh nếu không có chế độ nào có điểm cao
        max_score = max(scores.values())
        if max_score < 0.5:
            scores['neutral'] += (0.5 - max_score)
        
        # Xem xét chế độ hiện tại (độ nhớt)
        for regime in scores:
            if regime == self.current_regime:
                # Tăng cường điểm cho chế độ hiện tại dựa vào độ nhớt
                scores[regime] = scores[regime] * (1 - self.config['previous_regime_weight']) + \
                                self.config['previous_regime_weight']
        
        # Nếu có mâu thuẫn (nhiều chế độ có điểm cao)
        conflicting_regimes = [r for r, s in scores.items() if s >= 0.6]
        if len(conflicting_regimes) > 1:
            # Giảm điểm cho các chế độ mâu thuẫn
            for r in conflicting_regimes:
                scores[r] *= 0.8
            # Tăng điểm cho chế độ trung tính
            scores['neutral'] += 0.2
        
        return scores
    
    def _update_confidence_scores(self, scores: Dict) -> None:
        """Cập nhật điểm tin cậy cho mỗi chế độ."""
        # Áp dụng smoothing để cập nhật điểm tin cậy
        smoothing_factor = 0.7  # 70% điểm mới, 30% điểm cũ
        
        for regime in self.regimes:
            # Cập nhật điểm tin cậy
            new_score = scores.get(regime, 0)
            old_score = self.confidence_scores.get(regime, 0)
            
            # Áp dụng smoothing
            self.confidence_scores[regime] = new_score * smoothing_factor + old_score * (1 - smoothing_factor)
    
    def _determine_best_regime(self) -> Tuple[str, float]:
        """Xác định chế độ thị trường tối ưu và độ tin cậy."""
        # Tìm chế độ có điểm tin cậy cao nhất
        best_regime = max(self.confidence_scores, key=self.confidence_scores.get)
        best_confidence = self.confidence_scores[best_regime]
        
        if self.use_confidence_threshold:
            # Nếu sử dụng ngưỡng tin cậy và chế độ hiện tại khác với chế độ tốt nhất
            if best_regime != self.current_regime:
                # Kiểm tra xem độ tin cậy có đủ cao để chuyển đổi chế độ không
                if best_confidence < self.min_confidence_for_transition:
                    # Nếu không đủ cao, giữ nguyên chế độ hiện tại
                    return self.current_regime, self.confidence_scores[self.current_regime]
        
        return best_regime, best_confidence
    
    def _update_current_regime(self, new_regime: str, confidence: float) -> None:
        """Cập nhật chế độ thị trường hiện tại."""
        # Nếu chế độ mới khác chế độ hiện tại, ghi log
        if new_regime != self.current_regime:
            logger.info(f"Chế độ thị trường chuyển từ {self.current_regime} sang {new_regime} (Độ tin cậy: {confidence:.2f})")
            
        # Cập nhật chế độ hiện tại
        self.current_regime = new_regime
    
    def _save_regime_history(self, symbol: str) -> None:
        """Lưu lịch sử phát hiện chế độ thị trường."""
        try:
            # Đảm bảo thư mục tồn tại
            os.makedirs('data/regimes', exist_ok=True)
            
            # Lưu lịch sử
            with open(f'data/regimes/{symbol}_regimes.json', 'w') as f:
                # Chuyển đổi timestamp thành string để có thể lưu vào JSON
                history = []
                for record in self.regime_history:
                    record_copy = record.copy()
                    if isinstance(record_copy['timestamp'], datetime):
                        record_copy['timestamp'] = record_copy['timestamp'].isoformat()
                    history.append(record_copy)
                    
                json.dump(history, f, indent=2)
                
        except Exception as e:
            logger.error(f"Lỗi khi lưu lịch sử chế độ: {str(e)}")


if __name__ == "__main__":
    # Ví dụ sử dụng
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    # Tạo dữ liệu mẫu
    days = 100
    now = datetime.now()
    dates = [now - timedelta(days=i) for i in range(days, 0, -1)]
    
    # Tạo giá theo mô hình đơn giản để có các chế độ thị trường khác nhau
    prices = []
    
    for i in range(days):
        # Chia thành các đoạn khác nhau để mô phỏng các chế độ thị trường
        if i < days * 0.2:  # 20% đầu: trending bullish
            trend = 10 * (i / (days * 0.2))
            noise = np.random.normal(0, 1)
            price = 100 + trend + noise
        elif i < days * 0.4:  # 20% tiếp: ranging narrow
            mid_price = 110
            swing = 3 * np.sin(i * 0.3)
            noise = np.random.normal(0, 0.5)
            price = mid_price + swing + noise
        elif i < days * 0.6:  # 20% tiếp: trending bearish
            start_price = 110
            drop = 20 * ((i - days * 0.4) / (days * 0.2))
            noise = np.random.normal(0, 1)
            price = start_price - drop + noise
        elif i < days * 0.8:  # 20% tiếp: volatile breakout
            mid_price = 90
            # Tạo các spike
            if (i - int(days * 0.6)) % 5 == 0:
                spike = 5 * np.random.choice([-1, 1])
            else:
                spike = 0
            noise = np.random.normal(0, 2)
            price = mid_price + spike + noise
        else:  # 20% cuối: quiet accumulation
            mid_price = 90
            swing = 1 * np.sin(i * 0.2)
            noise = np.random.normal(0, 0.3)
            price = mid_price + swing + noise
        
        prices.append(price)
    
    # Tạo DataFrame
    df = pd.DataFrame({
        'open': [prices[i-1] if i > 0 else prices[i] * 0.99 for i in range(days)],
        'high': [p * (1 + 0.01 * np.random.random()) for p in prices],
        'low': [p * (1 - 0.01 * np.random.random()) for p in prices],
        'close': prices,
        'volume': [1000 * (1 + 0.5 * np.random.random()) for _ in range(days)]
    }, index=dates)
    
    # Tạo detector
    detector = EnhancedMarketRegimeDetector()
    
    # Phát hiện chế độ thị trường
    result = detector.detect_regime(df, symbol='EXAMPLE')
    
    print(f"Chế độ thị trường phát hiện: {result['regime']} (Độ tin cậy: {result['confidence']:.2f})")
    print("\nĐiểm chi tiết cho mỗi chế độ:")
    for regime, score in result['all_scores'].items():
        print(f"  {regime}: {score:.2f}")
    
    print("\nCác yếu tố phát hiện:")
    for regime, factors in result['detection_factors'].items():
        print(f"  {regime}:")
        for factor_name, is_true in factors.items():
            print(f"    {factor_name}: {is_true}")
    
    # Lấy phương pháp giao dịch phù hợp
    approach = detector.get_suitable_trading_approach()
    
    print("\nPhương pháp giao dịch phù hợp:")
    print(f"  Chiến lược phù hợp: {', '.join(approach['suitable_strategies'])}")
    print(f"  Khung thời gian: {', '.join(approach['timeframes'])}")
    print(f"  Chỉ báo: {', '.join(approach['indicators'])}")
    print(f"  Cách vào lệnh: {approach['entry_approach']}")
    print(f"  Stop loss: {approach['stop_loss']}")
    print(f"  Mức rủi ro: {approach['risk_level']}")
    print(f"  Target R:R: {approach['target_rr']}")