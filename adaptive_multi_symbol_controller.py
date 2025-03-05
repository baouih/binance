#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bộ điều khiển giao dịch đa cặp tiền thích ứng

Module này điều phối chiến lược giao dịch trên nhiều cặp tiền khác nhau, 
với khả năng phân bổ vốn, quản lý rủi ro động, và lọc tín hiệu giao dịch 
theo thanh khoản thị trường.
"""

import os
import json
import time
import logging
from datetime import datetime
import traceback
from typing import Dict, List, Tuple, Optional, Union
import pandas as pd
import numpy as np

from binance_api import BinanceAPI
from enhanced_trailing_stop import EnhancedTrailingStop

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("adaptive_controller.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('adaptive_controller')

class AdaptiveMultiSymbolController:
    """Lớp điều khiển giao dịch đa cặp tiền thích ứng"""
    
    def __init__(self, 
                account_config_path: str = 'account_config.json',
                strategy_config_path: str = 'configs/multi_symbol_strategy_config.json',
                liquidity_config_path: str = 'configs/symbol_liquidity_config.json',
                signal_filter_config_path: str = 'configs/trading_signal_filter_config.json'):
        """
        Khởi tạo bộ điều khiển
        
        Args:
            account_config_path (str): Đường dẫn đến cấu hình tài khoản
            strategy_config_path (str): Đường dẫn đến cấu hình chiến lược
            liquidity_config_path (str): Đường dẫn đến cấu hình thanh khoản
            signal_filter_config_path (str): Đường dẫn đến cấu hình lọc tín hiệu
        """
        self.api = BinanceAPI()
        self.trailing_stop_manager = EnhancedTrailingStop()
        
        # Load các cấu hình
        self.account_config = self._load_config(account_config_path)
        self.strategy_config = self._load_config(strategy_config_path)
        self.liquidity_config = self._load_config(liquidity_config_path)
        self.signal_filter_config = self._load_config(signal_filter_config_path)
        
        # Khởi tạo danh sách các cặp tiền được theo dõi
        self.monitored_symbols = self.account_config.get('symbols', [])
        
        # Trạng thái của bộ điều khiển
        self.active_positions = {}
        self.pending_orders = {}
        self.market_conditions = {}
        self.symbol_metrics = {}
        self.signal_history = {}
        self.performance_metrics = {}
        
        logger.info(f"Đã khởi tạo bộ điều khiển đa cặp tiền với {len(self.monitored_symbols)} cặp")
        
    def _load_config(self, config_path: str) -> Dict:
        """
        Tải cấu hình từ file
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
            
        Returns:
            Dict: Cấu hình đã tải
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình từ {config_path}: {e}")
            return {}
    
    def update_market_data(self):
        """Cập nhật dữ liệu thị trường cho tất cả các cặp tiền được theo dõi"""
        try:
            # Lấy thông tin giá và khối lượng giao dịch
            for symbol in self.monitored_symbols:
                # Lấy dữ liệu giá từ các khung thời gian khác nhau
                for timeframe in ['1h', '4h', '1d']:
                    klines = self.api.get_klines(symbol, timeframe, limit=100)
                    df = self.api.convert_klines_to_dataframe(klines)
                    
                    # Lưu vào bộ nhớ tạm thời
                    if symbol not in self.symbol_metrics:
                        self.symbol_metrics[symbol] = {}
                    
                    self.symbol_metrics[symbol][timeframe] = df
                    
                # Lấy thông tin order book
                order_book = self.api.get_order_book(symbol, limit=100)
                
                # Tính toán các chỉ số thanh khoản
                liquidity_score = self._calculate_liquidity_score(symbol, order_book)
                
                # Lưu thông tin thanh khoản
                self.symbol_metrics[symbol]['liquidity_score'] = liquidity_score
                
                # Phát hiện chế độ thị trường
                market_regime = self._detect_market_regime(symbol)
                self.market_conditions[symbol] = market_regime
                
                logger.debug(f"Đã cập nhật dữ liệu thị trường cho {symbol}, chế độ: {market_regime}")
                
            return True
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật dữ liệu thị trường: {e}")
            return False
    
    def _calculate_liquidity_score(self, symbol: str, order_book: Dict) -> float:
        """
        Tính điểm thanh khoản cho một cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền
            order_book (Dict): Dữ liệu order book
            
        Returns:
            float: Điểm thanh khoản (0-100)
        """
        try:
            # Tính tổng khối lượng trong order book
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            bid_volume = sum(float(bid[1]) for bid in bids)
            ask_volume = sum(float(ask[1]) for ask in asks)
            
            total_volume = bid_volume + ask_volume
            
            # Tính spread
            if bids and asks:
                best_bid = float(bids[0][0])
                best_ask = float(asks[0][0])
                spread_pct = (best_ask - best_bid) / best_bid * 100
            else:
                spread_pct = 999  # Giá trị cao nếu không có dữ liệu
            
            # Lấy thông tin khối lượng giao dịch 24h
            ticker_24h = self.api.get_24h_ticker(symbol)
            volume_24h = float(ticker_24h.get('volume', 0))
            quote_volume_24h = float(ticker_24h.get('quoteVolume', 0))
            
            # Tính điểm thanh khoản (0-100)
            # Trọng số: 50% khối lượng 24h, 30% độ sâu order book, 20% spread
            
            # Chuyển đổi giá trị thành thang điểm 0-100
            volume_score = min(100, quote_volume_24h / 1000000)  # 100 điểm cho $100M+
            depth_score = min(100, total_volume / 1000)  # 100 điểm cho 1000+ BTC/ETH
            spread_score = max(0, 100 - spread_pct * 100)  # Spread càng thấp càng tốt
            
            # Tính điểm tổng hợp
            liquidity_score = volume_score * 0.5 + depth_score * 0.3 + spread_score * 0.2
            
            return liquidity_score
        except Exception as e:
            logger.error(f"Lỗi khi tính điểm thanh khoản cho {symbol}: {e}")
            return 0
    
    def _detect_market_regime(self, symbol: str) -> str:
        """
        Phát hiện chế độ thị trường hiện tại
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            str: Chế độ thị trường ('trending', 'ranging', 'volatile', 'quiet')
        """
        try:
            if symbol not in self.symbol_metrics:
                return 'ranging'  # Giá trị mặc định
                
            df_1h = self.symbol_metrics[symbol].get('1h')
            df_4h = self.symbol_metrics[symbol].get('4h')
            
            if df_1h is None or len(df_1h) < 30:
                return 'ranging'  # Không đủ dữ liệu
                
            # Tính các chỉ báo
            # ADX để đo lường sức mạnh xu hướng
            df_temp = df_1h.copy()
            high = df_temp['high']
            low = df_temp['low']
            close = df_temp['close']
            
            # Tính +DM và -DM
            plus_dm = high.diff()
            minus_dm = low.diff()
            plus_dm[plus_dm < 0] = 0
            minus_dm[minus_dm > 0] = 0
            minus_dm = abs(minus_dm)
            
            # Điều kiện để lấy giá trị +DM
            temp_df = pd.DataFrame({
                'up': plus_dm,
                'down': minus_dm
            })
            
            plus_dm = temp_df.apply(lambda x: x['up'] if x['up'] > x['down'] and x['up'] > 0 else 0, axis=1)
            minus_dm = temp_df.apply(lambda x: x['down'] if x['down'] > x['up'] and x['down'] > 0 else 0, axis=1)
            
            # Tính TR
            tr1 = pd.DataFrame(high - low)
            tr2 = pd.DataFrame(abs(high - close.shift(1)))
            tr3 = pd.DataFrame(abs(low - close.shift(1)))
            frames = [tr1, tr2, tr3]
            tr = pd.concat(frames, axis=1, join='inner').max(axis=1)
            tr = tr.tolist()
            
            # Tính ATR
            atr = sum(tr[-14:]) / 14
            
            # Tính biến động dựa trên ATR
            volatility = atr / close.iloc[-1] * 100
            
            # Tính RSI
            delta = df_temp['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            # Phát hiện chế độ thị trường
            adx_value = 0  # Giả lập giá trị ADX
            if adx_value > 25:  # Xu hướng mạnh
                if rsi.iloc[-1] > 70 or rsi.iloc[-1] < 30:
                    return 'trending'
                else:
                    return 'trending'
            elif volatility > 3:  # Biến động cao
                return 'volatile'
            elif volatility < 1:  # Biến động thấp
                return 'quiet'
            else:  # Thị trường đi ngang
                return 'ranging'
                
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện chế độ thị trường cho {symbol}: {e}")
            return 'ranging'  # Giá trị mặc định
    
    def generate_trading_signals(self) -> Dict[str, Dict]:
        """
        Tạo tín hiệu giao dịch cho tất cả các cặp tiền được theo dõi
        
        Returns:
            Dict[str, Dict]: Tín hiệu giao dịch theo cặp tiền
        """
        signals = {}
        
        try:
            # Lặp qua từng cặp tiền
            for symbol in self.monitored_symbols:
                # Kiểm tra thanh khoản
                liquidity_score = self.symbol_metrics.get(symbol, {}).get('liquidity_score', 0)
                min_liquidity = self.liquidity_config['minimum_requirements']['min_daily_volume_usd']
                
                if liquidity_score < 50:
                    logger.info(f"Bỏ qua {symbol} do thanh khoản thấp (điểm: {liquidity_score})")
                    continue
                
                # Lấy chế độ thị trường
                market_regime = self.market_conditions.get(symbol, 'ranging')
                
                # Lấy cấu hình chiến lược cho cặp tiền
                strategy_config = self._get_strategy_config_for_symbol(symbol)
                
                # Lấy danh sách chiến lược phù hợp với chế độ thị trường
                suitable_strategies = self._get_suitable_strategies(symbol, market_regime)
                
                # Tạo tín hiệu từ các chiến lược
                symbol_signals = {}
                
                for strategy in suitable_strategies:
                    signal = self._generate_signal_for_strategy(symbol, strategy, market_regime)
                    
                    if signal:
                        symbol_signals[strategy] = signal
                
                # Lọc và tổng hợp các tín hiệu
                final_signal = self._filter_signals(symbol, symbol_signals, market_regime)
                
                if final_signal:
                    signals[symbol] = final_signal
            
            return signals
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo tín hiệu giao dịch: {e}")
            return {}
    
    def _get_strategy_config_for_symbol(self, symbol: str) -> Dict:
        """
        Lấy cấu hình chiến lược cho một cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            Dict: Cấu hình chiến lược
        """
        pair_specific = self.strategy_config.get('pair_specific_strategies', {})
        
        # Kiểm tra nếu có cấu hình riêng cho cặp tiền
        if symbol in pair_specific:
            return pair_specific[symbol]
        
        # Nếu không, sử dụng cấu hình mặc định
        return pair_specific.get('default', {})
    
    def _get_suitable_strategies(self, symbol: str, market_regime: str) -> List[str]:
        """
        Lấy danh sách chiến lược phù hợp với chế độ thị trường
        
        Args:
            symbol (str): Mã cặp tiền
            market_regime (str): Chế độ thị trường
            
        Returns:
            List[str]: Danh sách chiến lược phù hợp
        """
        # Lấy cấu hình chiến lược cho cặp tiền
        strategy_config = self._get_strategy_config_for_symbol(symbol)
        
        # Lấy danh sách chiến lược chính và phụ
        primary_strategies = strategy_config.get('primary_strategies', [])
        secondary_strategies = strategy_config.get('secondary_strategies', [])
        
        # Lọc chiến lược theo chế độ thị trường
        suitable_strategies = []
        
        market_filter = self.signal_filter_config.get('market_condition_filters', {}).get(market_regime, {})
        preferred_strategies = market_filter.get('preferred_strategies', [])
        avoid_strategies = market_filter.get('avoid_strategies', [])
        
        # Ưu tiên chiến lược chính và phù hợp với chế độ thị trường
        for strategy in primary_strategies:
            if strategy in preferred_strategies:
                suitable_strategies.append(strategy)
        
        # Thêm các chiến lược chính khác (nếu không thuộc danh sách tránh)
        for strategy in primary_strategies:
            if strategy not in avoid_strategies and strategy not in suitable_strategies:
                suitable_strategies.append(strategy)
        
        # Thêm các chiến lược phụ phù hợp
        for strategy in secondary_strategies:
            if strategy in preferred_strategies and strategy not in suitable_strategies:
                suitable_strategies.append(strategy)
        
        return suitable_strategies
    
    def _generate_signal_for_strategy(self, symbol: str, strategy: str, market_regime: str) -> Optional[Dict]:
        """
        Tạo tín hiệu giao dịch cho một chiến lược cụ thể
        
        Args:
            symbol (str): Mã cặp tiền
            strategy (str): Tên chiến lược
            market_regime (str): Chế độ thị trường
            
        Returns:
            Optional[Dict]: Tín hiệu giao dịch hoặc None nếu không có
        """
        try:
            if symbol not in self.symbol_metrics:
                return None
                
            # Lấy dữ liệu giá
            df_1h = self.symbol_metrics[symbol].get('1h')
            
            if df_1h is None or len(df_1h) < 30:
                return None
                
            # Tạo tín hiệu dựa trên loại chiến lược
            if strategy == 'trend_following':
                return self._generate_trend_following_signal(symbol, df_1h)
            elif strategy == 'momentum':
                return self._generate_momentum_signal(symbol, df_1h)
            elif strategy == 'breakout':
                return self._generate_breakout_signal(symbol, df_1h)
            elif strategy == 'mean_reversion':
                return self._generate_mean_reversion_signal(symbol, df_1h)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Lỗi khi tạo tín hiệu cho {symbol} với chiến lược {strategy}: {e}")
            return None
    
    def _generate_trend_following_signal(self, symbol: str, df: pd.DataFrame) -> Optional[Dict]:
        """Tạo tín hiệu theo xu hướng"""
        try:
            # Lấy tham số chiến lược
            strategy_params = self.strategy_config.get('strategy_profiles', {}).get('trend_following', {}).get('parameters', {})
            
            # Tính EMA
            ema_short_period = strategy_params.get('ema_short', 9)
            ema_long_period = strategy_params.get('ema_long', 21)
            
            df['ema_short'] = df['close'].ewm(span=ema_short_period, adjust=False).mean()
            df['ema_long'] = df['close'].ewm(span=ema_long_period, adjust=False).mean()
            
            # Tính ADX
            adx_period = strategy_params.get('adx_period', 14)
            adx_threshold = strategy_params.get('adx_threshold', 25)
            
            # Giả lập ADX đơn giản để demo
            adx_value = 30  # Giá trị giả lập
            
            # Kiểm tra tín hiệu
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            # Tính toán CrossOver
            ema_cross_up = prev_row['ema_short'] <= prev_row['ema_long'] and last_row['ema_short'] > last_row['ema_long']
            ema_cross_down = prev_row['ema_short'] >= prev_row['ema_long'] and last_row['ema_short'] < last_row['ema_long']
            
            # Tạo tín hiệu
            signal = None
            confidence = 0
            
            if ema_cross_up and adx_value > adx_threshold:
                signal = {
                    'side': 'BUY',
                    'strategy': 'trend_following',
                    'confidence': 80,
                    'reason': f"EMA CrossOver Bullish + ADX={adx_value}",
                    'timestamp': datetime.now().isoformat()
                }
            elif ema_cross_down and adx_value > adx_threshold:
                signal = {
                    'side': 'SELL',
                    'strategy': 'trend_following',
                    'confidence': 80,
                    'reason': f"EMA CrossOver Bearish + ADX={adx_value}",
                    'timestamp': datetime.now().isoformat()
                }
            
            return signal
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo tín hiệu trend_following cho {symbol}: {e}")
            return None
    
    def _generate_momentum_signal(self, symbol: str, df: pd.DataFrame) -> Optional[Dict]:
        """Tạo tín hiệu dựa trên động lượng"""
        try:
            # Lấy tham số chiến lược
            strategy_params = self.strategy_config.get('strategy_profiles', {}).get('momentum', {}).get('parameters', {})
            
            # Tính RSI
            rsi_period = strategy_params.get('rsi_period', 14)
            rsi_overbought = strategy_params.get('rsi_overbought', 70)
            rsi_oversold = strategy_params.get('rsi_oversold', 30)
            
            # Tính RSI
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=rsi_period).mean()
            avg_loss = loss.rolling(window=rsi_period).mean()
            
            rs = avg_gain / avg_loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Tính MACD
            macd_fast = strategy_params.get('macd_fast', 12)
            macd_slow = strategy_params.get('macd_slow', 26)
            macd_signal = strategy_params.get('macd_signal', 9)
            
            df['ema_fast'] = df['close'].ewm(span=macd_fast, adjust=False).mean()
            df['ema_slow'] = df['close'].ewm(span=macd_slow, adjust=False).mean()
            df['macd'] = df['ema_fast'] - df['ema_slow']
            df['macd_signal'] = df['macd'].ewm(span=macd_signal, adjust=False).mean()
            df['macd_hist'] = df['macd'] - df['macd_signal']
            
            # Kiểm tra tín hiệu
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            # Tạo tín hiệu
            signal = None
            
            # RSI thoát vùng quá bán + MACD Histogram chuyển dương
            if (last_row['rsi'] > rsi_oversold and prev_row['rsi'] <= rsi_oversold) and \
               (last_row['macd_hist'] > 0 and prev_row['macd_hist'] <= 0):
                signal = {
                    'side': 'BUY',
                    'strategy': 'momentum',
                    'confidence': 85,
                    'reason': f"RSI thoát vùng quá bán ({last_row['rsi']:.1f}) + MACD Histogram chuyển dương",
                    'timestamp': datetime.now().isoformat()
                }
            
            # RSI thoát vùng quá mua + MACD Histogram chuyển âm
            elif (last_row['rsi'] < rsi_overbought and prev_row['rsi'] >= rsi_overbought) and \
                 (last_row['macd_hist'] < 0 and prev_row['macd_hist'] >= 0):
                signal = {
                    'side': 'SELL',
                    'strategy': 'momentum',
                    'confidence': 85,
                    'reason': f"RSI thoát vùng quá mua ({last_row['rsi']:.1f}) + MACD Histogram chuyển âm",
                    'timestamp': datetime.now().isoformat()
                }
            
            return signal
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo tín hiệu momentum cho {symbol}: {e}")
            return None
    
    def _generate_breakout_signal(self, symbol: str, df: pd.DataFrame) -> Optional[Dict]:
        """Tạo tín hiệu đột phá"""
        try:
            # Lấy tham số chiến lược
            strategy_params = self.strategy_config.get('strategy_profiles', {}).get('breakout', {}).get('parameters', {})
            
            # Tính Bollinger Bands
            bollinger_period = strategy_params.get('bollinger_period', 20)
            bollinger_std = strategy_params.get('bollinger_std', 2)
            
            df['sma'] = df['close'].rolling(window=bollinger_period).mean()
            df['std'] = df['close'].rolling(window=bollinger_period).std()
            df['upper_band'] = df['sma'] + (df['std'] * bollinger_std)
            df['lower_band'] = df['sma'] - (df['std'] * bollinger_std)
            
            # Tính ATR
            atr_period = strategy_params.get('atr_period', 14)
            
            tr1 = pd.DataFrame(df['high'] - df['low'])
            tr2 = pd.DataFrame(abs(df['high'] - df['close'].shift(1)))
            tr3 = pd.DataFrame(abs(df['low'] - df['close'].shift(1)))
            frames = [tr1, tr2, tr3]
            tr = pd.concat(frames, axis=1, join='inner').max(axis=1)
            df['atr'] = tr.rolling(window=atr_period).mean()
            
            # Kiểm tra tín hiệu
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            # Tạo tín hiệu
            signal = None
            
            # Breakout lên trên
            if prev_row['close'] <= prev_row['upper_band'] and last_row['close'] > last_row['upper_band']:
                # Kiểm tra khối lượng
                if last_row['volume'] > prev_row['volume'] * strategy_params.get('volume_threshold', 1.5):
                    signal = {
                        'side': 'BUY',
                        'strategy': 'breakout',
                        'confidence': 75,
                        'reason': "Đột phá lên trên dải Bollinger Band với khối lượng tăng",
                        'timestamp': datetime.now().isoformat()
                    }
            
            # Breakout xuống dưới
            elif prev_row['close'] >= prev_row['lower_band'] and last_row['close'] < last_row['lower_band']:
                # Kiểm tra khối lượng
                if last_row['volume'] > prev_row['volume'] * strategy_params.get('volume_threshold', 1.5):
                    signal = {
                        'side': 'SELL',
                        'strategy': 'breakout',
                        'confidence': 75,
                        'reason': "Đột phá xuống dưới dải Bollinger Band với khối lượng tăng",
                        'timestamp': datetime.now().isoformat()
                    }
            
            return signal
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo tín hiệu breakout cho {symbol}: {e}")
            return None
    
    def _generate_mean_reversion_signal(self, symbol: str, df: pd.DataFrame) -> Optional[Dict]:
        """Tạo tín hiệu quay về trung bình"""
        try:
            # Lấy tham số chiến lược
            strategy_params = self.strategy_config.get('strategy_profiles', {}).get('mean_reversion', {}).get('parameters', {})
            
            # Tính RSI
            rsi_period = strategy_params.get('rsi_period', 14)
            rsi_overbought = strategy_params.get('rsi_overbought', 75)
            rsi_oversold = strategy_params.get('rsi_oversold', 25)
            
            # Tính RSI
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=rsi_period).mean()
            avg_loss = loss.rolling(window=rsi_period).mean()
            
            rs = avg_gain / avg_loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Tính Bollinger Bands
            bollinger_period = strategy_params.get('bollinger_period', 20)
            bollinger_std = strategy_params.get('bollinger_std', 2.5)
            
            df['sma'] = df['close'].rolling(window=bollinger_period).mean()
            df['std'] = df['close'].rolling(window=bollinger_period).std()
            df['upper_band'] = df['sma'] + (df['std'] * bollinger_std)
            df['lower_band'] = df['sma'] - (df['std'] * bollinger_std)
            
            # Kiểm tra tín hiệu
            last_row = df.iloc[-1]
            prev_rows = df.iloc[-5:-1]  # 4 nến trước đó
            
            # Tạo tín hiệu
            signal = None
            
            # Phục hồi từ vùng oversold
            if last_row['rsi'] < rsi_oversold and last_row['close'] < last_row['lower_band']:
                # Kiểm tra xu hướng giảm trước đó
                if all(prev_rows['close'].diff().dropna() < 0):
                    signal = {
                        'side': 'BUY',
                        'strategy': 'mean_reversion',
                        'confidence': 70,
                        'reason': f"RSI quá bán ({last_row['rsi']:.1f}) + Giá dưới dải Bollinger dưới sau xu hướng giảm",
                        'timestamp': datetime.now().isoformat()
                    }
            
            # Phục hồi từ vùng overbought
            elif last_row['rsi'] > rsi_overbought and last_row['close'] > last_row['upper_band']:
                # Kiểm tra xu hướng tăng trước đó
                if all(prev_rows['close'].diff().dropna() > 0):
                    signal = {
                        'side': 'SELL',
                        'strategy': 'mean_reversion',
                        'confidence': 70,
                        'reason': f"RSI quá mua ({last_row['rsi']:.1f}) + Giá trên dải Bollinger trên sau xu hướng tăng",
                        'timestamp': datetime.now().isoformat()
                    }
            
            return signal
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo tín hiệu mean_reversion cho {symbol}: {e}")
            return None
    
    def _filter_signals(self, symbol: str, signals: Dict[str, Dict], market_regime: str) -> Optional[Dict]:
        """
        Lọc và tổng hợp các tín hiệu cho một cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền
            signals (Dict[str, Dict]): Các tín hiệu theo chiến lược
            market_regime (str): Chế độ thị trường
            
        Returns:
            Optional[Dict]: Tín hiệu cuối cùng hoặc None nếu không có
        """
        if not signals:
            return None
            
        # Lấy cấu hình lọc
        global_settings = self.signal_filter_config.get('global_settings', {})
        min_confidence = global_settings.get('min_confidence_threshold', 70)
        
        # Lọc tín hiệu có confidence thấp
        valid_signals = {k: v for k, v in signals.items() if v.get('confidence', 0) >= min_confidence}
        
        if not valid_signals:
            return None
            
        # Lọc theo chế độ thị trường
        market_filter = self.signal_filter_config.get('market_condition_filters', {}).get(market_regime, {})
        preferred_strategies = market_filter.get('preferred_strategies', [])
        avoid_strategies = market_filter.get('avoid_strategies', [])
        
        # Ưu tiên chiến lược phù hợp với chế độ thị trường
        for strategy in preferred_strategies:
            if strategy in valid_signals:
                return valid_signals[strategy]
        
        # Loại bỏ chiến lược không phù hợp
        filtered_signals = {k: v for k, v in valid_signals.items() if k not in avoid_strategies}
        
        if not filtered_signals:
            return None
            
        # Chọn tín hiệu có confidence cao nhất
        final_signal = sorted(filtered_signals.values(), key=lambda x: x.get('confidence', 0), reverse=True)[0]
        
        return final_signal
    
    def execute_trading_signals(self, signals: Dict[str, Dict]) -> Dict[str, bool]:
        """
        Thực thi các tín hiệu giao dịch
        
        Args:
            signals (Dict[str, Dict]): Các tín hiệu giao dịch theo cặp tiền
            
        Returns:
            Dict[str, bool]: Kết quả thực thi theo cặp tiền
        """
        results = {}
        
        try:
            # Kiểm tra còn bao nhiêu slot giao dịch
            max_positions = int(self.account_config.get('max_open_positions', 3))
            current_positions = len(self._get_active_positions())
            available_slots = max_positions - current_positions
            
            if available_slots <= 0:
                logger.info(f"Đã đạt giới hạn vị thế ({max_positions}), không mở thêm")
                return results
                
            # Sắp xếp tín hiệu theo mức độ ưu tiên
            sorted_signals = sorted(
                signals.items(), 
                key=lambda x: (
                    x[1].get('confidence', 0),  # Ưu tiên theo confidence
                    self.symbol_metrics.get(x[0], {}).get('liquidity_score', 0)  # Sau đó theo thanh khoản
                ),
                reverse=True
            )
            
            # Giới hạn số lượng tín hiệu theo số slot còn lại
            signals_to_execute = sorted_signals[:available_slots]
            
            # Thực thi từng tín hiệu
            for symbol, signal in signals_to_execute:
                success = self._execute_single_signal(symbol, signal)
                results[symbol] = success
            
            return results
            
        except Exception as e:
            logger.error(f"Lỗi khi thực thi tín hiệu giao dịch: {e}")
            return results
    
    def _execute_single_signal(self, symbol: str, signal: Dict) -> bool:
        """
        Thực thi một tín hiệu giao dịch
        
        Args:
            symbol (str): Mã cặp tiền
            signal (Dict): Tín hiệu giao dịch
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            # Kiểm tra nếu đã có vị thế cho cặp tiền này
            active_positions = self._get_active_positions()
            
            for position in active_positions:
                if position['symbol'] == symbol:
                    logger.info(f"Đã có vị thế cho {symbol}, không mở thêm")
                    return False
            
            # Lấy thông tin tài khoản
            account = self.api.get_futures_account()
            balance = float(account.get('totalWalletBalance', 0))
            
            # Lấy cấu hình vị thế
            pair_config = self._get_strategy_config_for_symbol(symbol)
            risk_profile = pair_config.get('risk_profile', 'medium')
            max_leverage = pair_config.get('max_leverage', 10)
            
            # Lấy cấu hình rủi ro
            risk_profiles = self.strategy_config.get('risk_profiles', {})
            risk_config = risk_profiles.get(risk_profile, {})
            
            risk_per_trade = risk_config.get('risk_per_trade', 1.0)
            stop_loss_atr = risk_config.get('stop_loss_atr_multiplier', 1.5)
            
            # Lấy giá hiện tại
            ticker = self.api.get_symbol_ticker(symbol)
            current_price = float(ticker.get('price', 0))
            
            if current_price <= 0:
                logger.error(f"Giá không hợp lệ cho {symbol}: {current_price}")
                return False
            
            # Tính ATR cho stop loss
            df = self.symbol_metrics.get(symbol, {}).get('1h')
            
            if df is None:
                logger.error(f"Không có dữ liệu để tính ATR cho {symbol}")
                return False
                
            # Tính ATR đơn giản
            tr1 = pd.DataFrame(df['high'] - df['low'])
            tr2 = pd.DataFrame(abs(df['high'] - df['close'].shift(1)))
            tr3 = pd.DataFrame(abs(df['low'] - df['close'].shift(1)))
            frames = [tr1, tr2, tr3]
            tr = pd.concat(frames, axis=1, join='inner').max(axis=1)
            atr = tr.rolling(window=14).mean().iloc[-1]
            
            # Tính stop loss
            side = signal.get('side')
            
            if side == 'BUY':
                stop_price = current_price - (atr * stop_loss_atr)
            else:  # SELL
                stop_price = current_price + (atr * stop_loss_atr)
            
            # Tính khoảng cách % đến stop loss
            stop_distance_pct = abs(stop_price - current_price) / current_price * 100
            
            # Tính leverage dựa trên khoảng cách stop loss
            leverage = min(max_leverage, int(10 / stop_distance_pct) + 1)
            leverage = max(1, min(leverage, max_leverage))  # Đảm bảo trong khoảng hợp lệ
            
            # Tính size vị thế
            risk_amount = balance * risk_per_trade / 100
            position_size_usd = risk_amount * leverage
            
            # Kiểm tra tối đa cho phép
            max_size_usd = pair_config.get('capital_allocation_pct', 10) * balance / 100
            position_size_usd = min(position_size_usd, max_size_usd)
            
            # Chuyển đổi sang số lượng
            quantity = position_size_usd / current_price
            
            # Làm tròn số lượng (đơn giản hóa)
            quantity = round(quantity, 4)
            
            if quantity <= 0:
                logger.error(f"Số lượng không hợp lệ cho {symbol}: {quantity}")
                return False
            
            # Mở vị thế (giả lập thành công)
            logger.info(f"Mở vị thế {side} cho {symbol}: {quantity} đơn vị, đòn bẩy {leverage}x, giá {current_price}, stop {stop_price}")
            
            # Thêm vào danh sách vị thế đã mở
            new_position = {
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'entry_price': current_price,
                'stop_loss': stop_price,
                'leverage': leverage,
                'strategy': signal.get('strategy'),
                'entry_time': datetime.now().isoformat(),
                'market_regime': self.market_conditions.get(symbol, 'ranging')
            }
            
            # Theo dõi vị thế (không thực sự mở vị thế trong testnet)
            self.active_positions[symbol] = new_position
            
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi thực thi tín hiệu cho {symbol}: {e}")
            return False
    
    def _get_active_positions(self) -> List[Dict]:
        """
        Lấy danh sách vị thế đang mở
        
        Returns:
            List[Dict]: Danh sách vị thế
        """
        try:
            positions = self.api.get_futures_position_risk()
            return [p for p in positions if abs(float(p.get('positionAmt', 0))) > 0]
        except Exception as e:
            logger.error(f"Lỗi khi lấy vị thế: {e}")
            return []
    
    def update_trailing_stops(self) -> Dict[str, bool]:
        """
        Cập nhật trailing stop cho tất cả vị thế
        
        Returns:
            Dict[str, bool]: Kết quả cập nhật theo cặp tiền
        """
        # Sử dụng EnhancedTrailingStop để quản lý
        self.trailing_stop_manager.update_trailing_stops()
        
        # Đơn giản trả về thành công
        return {'status': 'success'}
    
    def run(self, interval: int = 60):
        """
        Chạy bộ điều khiển
        
        Args:
            interval (int): Khoảng thời gian giữa các lần kiểm tra (giây)
        """
        logger.info(f"Bắt đầu chạy bộ điều khiển đa cặp tiền với {len(self.monitored_symbols)} cặp")
        
        while True:
            try:
                # Cập nhật dữ liệu thị trường
                self.update_market_data()
                
                # Tạo tín hiệu giao dịch
                signals = self.generate_trading_signals()
                
                if signals:
                    logger.info(f"Phát hiện {len(signals)} tín hiệu giao dịch")
                    
                    # Thực thi tín hiệu
                    results = self.execute_trading_signals(signals)
                    
                    if any(results.values()):
                        logger.info(f"Đã thực thi thành công {sum(results.values())} tín hiệu")
                
                # Cập nhật trailing stop
                self.update_trailing_stops()
                
                # Đợi đến lần kiểm tra tiếp theo
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("Đã nhận tín hiệu dừng, kết thúc bộ điều khiển")
                break
            except Exception as e:
                logger.error(f"Lỗi khi chạy bộ điều khiển: {e}")
                logger.error(traceback.format_exc())
                time.sleep(10)  # Đợi một chút trước khi thử lại
    
def main():
    """Hàm chính để chạy bộ điều khiển"""
    controller = AdaptiveMultiSymbolController()
    controller.run()

if __name__ == "__main__":
    main()