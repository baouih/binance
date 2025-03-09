"""
Hệ thống giao dịch nâng cao tích hợp nhiều kỹ thuật tiên tiến

Module này kết hợp các kỹ thuật nâng cao như phân tích đa khung thời gian, 
chỉ báo tổng hợp, phân tích thanh khoản và quản lý rủi ro tối ưu để tạo ra
một hệ thống giao dịch hoàn chỉnh và mạnh mẽ.
"""

import numpy as np
import pandas as pd
import json
import logging
import time
from typing import Dict, List, Tuple, Optional, Union, Any
from datetime import datetime, timedelta

from app.binance_api import BinanceAPI
from app.data_processor import DataProcessor
from app.market_regime_detector import MarketRegimeDetector
from multi_timeframe_analyzer import MultiTimeframeAnalyzer
from composite_indicator import CompositeIndicator
from liquidity_analyzer import LiquidityAnalyzer

# Thiết lập logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('advanced_trading')

class TradePosition:
    """Lớp đại diện cho một vị thế giao dịch"""
    
    def __init__(self, symbol: str, side: str, entry_price: float, quantity: float, 
                leverage: int = 1, entry_time: datetime = None):
        """
        Khởi tạo vị thế giao dịch.
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng vị thế ('BUY' hoặc 'SELL')
            entry_price (float): Giá vào lệnh
            quantity (float): Số lượng giao dịch
            leverage (int): Đòn bẩy
            entry_time (datetime): Thời gian vào lệnh
        """
        self.symbol = symbol
        self.side = side
        self.entry_price = entry_price
        self.quantity = quantity
        self.leverage = leverage
        self.entry_time = entry_time or datetime.now()
        
        # Thông tin quản lý rủi ro
        self.take_profit_price = None
        self.stop_loss_price = None
        self.trailing_stop_active = False
        self.trailing_stop_price = None
        self.highest_price = entry_price if side == 'BUY' else None
        self.lowest_price = entry_price if side == 'SELL' else None
        
        # Thông tin kết quả
        self.exit_price = None
        self.exit_time = None
        self.pnl = None
        self.pnl_percent = None
        self.exit_reason = None
        self.status = "OPEN"  # OPEN, CLOSED
        
        # Thông tin bổ sung
        self.entry_signals = {}
        self.trade_id = f"{symbol}_{int(time.time())}"
        
        logger.info(f"Tạo vị thế mới: {side} {symbol} tại {entry_price:.2f}, số lượng: {quantity:.6f}, đòn bẩy: {leverage}x")
    
    def set_risk_parameters(self, take_profit_pct: float = None, stop_loss_pct: float = None, 
                           trailing_stop: bool = False, ts_activation_pct: float = None,
                           ts_callback_pct: float = None):
        """
        Thiết lập các tham số quản lý rủi ro.
        
        Args:
            take_profit_pct (float): Phần trăm chốt lời
            stop_loss_pct (float): Phần trăm cắt lỗ
            trailing_stop (bool): Có sử dụng trailing stop không
            ts_activation_pct (float): Phần trăm để kích hoạt trailing stop
            ts_callback_pct (float): Phần trăm callback cho trailing stop
        """
        if take_profit_pct is not None:
            if self.side == 'BUY':
                self.take_profit_price = self.entry_price * (1 + take_profit_pct / 100)
            else:
                self.take_profit_price = self.entry_price * (1 - take_profit_pct / 100)
        
        if stop_loss_pct is not None:
            if self.side == 'BUY':
                self.stop_loss_price = self.entry_price * (1 - stop_loss_pct / 100)
            else:
                self.stop_loss_price = self.entry_price * (1 + stop_loss_pct / 100)
        
        self.trailing_stop_active = trailing_stop
        self.ts_activation_pct = ts_activation_pct or take_profit_pct * 0.5 if take_profit_pct else None
        self.ts_callback_pct = ts_callback_pct or (stop_loss_pct * 0.5 if stop_loss_pct else 1.0)
        
        logger.info(f"Thiết lập quản lý rủi ro cho {self.symbol}: TP={take_profit_pct}%, SL={stop_loss_pct}%, "
                  f"TrailingStop={trailing_stop}")
    
    def update_price(self, current_price: float) -> Tuple[bool, str]:
        """
        Cập nhật trạng thái vị thế với giá hiện tại và kiểm tra các điều kiện đóng vị thế.
        
        Args:
            current_price (float): Giá hiện tại
            
        Returns:
            Tuple[bool, str]: (Có đóng vị thế không, Lý do đóng vị thế)
        """
        if self.status != "OPEN":
            return False, "Vị thế đã đóng"
        
        # Cập nhật giá cao nhất/thấp nhất
        if self.side == 'BUY':
            if self.highest_price is None or current_price > self.highest_price:
                self.highest_price = current_price
        else:  # SELL
            if self.lowest_price is None or current_price < self.lowest_price:
                self.lowest_price = current_price
        
        # Kiểm tra trailing stop
        trailing_stop_hit = False
        if self.trailing_stop_active:
            # Kiểm tra xem trailing stop đã được kích hoạt chưa
            ts_activated = False
            
            if self.side == 'BUY' and self.ts_activation_pct:
                activation_price = self.entry_price * (1 + self.ts_activation_pct / 100)
                if current_price >= activation_price:
                    ts_activated = True
                    # Cập nhật trailing stop price nếu chưa có hoặc nếu giá cao hơn đã tạo mức trailing stop cao hơn
                    new_ts_price = self.highest_price * (1 - self.ts_callback_pct / 100)
                    if self.trailing_stop_price is None or new_ts_price > self.trailing_stop_price:
                        self.trailing_stop_price = new_ts_price
                        logger.info(f"Trailing stop kích hoạt/cập nhật: {self.trailing_stop_price:.2f}")
                    
                    # Kiểm tra xem giá có xuống dưới trailing stop không
                    if current_price < self.trailing_stop_price:
                        trailing_stop_hit = True
            
            elif self.side == 'SELL' and self.ts_activation_pct:
                activation_price = self.entry_price * (1 - self.ts_activation_pct / 100)
                if current_price <= activation_price:
                    ts_activated = True
                    # Cập nhật trailing stop price nếu chưa có hoặc nếu giá thấp hơn đã tạo mức trailing stop thấp hơn
                    new_ts_price = self.lowest_price * (1 + self.ts_callback_pct / 100)
                    if self.trailing_stop_price is None or new_ts_price < self.trailing_stop_price:
                        self.trailing_stop_price = new_ts_price
                        logger.info(f"Trailing stop kích hoạt/cập nhật: {self.trailing_stop_price:.2f}")
                    
                    # Kiểm tra xem giá có lên trên trailing stop không
                    if current_price > self.trailing_stop_price:
                        trailing_stop_hit = True
        
        # Kiểm tra các điều kiện đóng vị thế
        if trailing_stop_hit:
            return True, "Trailing Stop"
        
        elif self.take_profit_price is not None:
            if (self.side == 'BUY' and current_price >= self.take_profit_price) or \
               (self.side == 'SELL' and current_price <= self.take_profit_price):
                return True, "Take Profit"
        
        elif self.stop_loss_price is not None:
            if (self.side == 'BUY' and current_price <= self.stop_loss_price) or \
               (self.side == 'SELL' and current_price >= self.stop_loss_price):
                return True, "Stop Loss"
        
        return False, None
    
    def close_position(self, exit_price: float, exit_time: datetime = None, exit_reason: str = None):
        """
        Đóng vị thế.
        
        Args:
            exit_price (float): Giá thoát
            exit_time (datetime): Thời gian thoát
            exit_reason (str): Lý do thoát
        """
        if self.status != "OPEN":
            logger.warning(f"Vị thế {self.trade_id} đã đóng trước đó")
            return
        
        self.exit_price = exit_price
        self.exit_time = exit_time or datetime.now()
        self.exit_reason = exit_reason
        
        # Tính toán PnL
        if self.side == 'BUY':
            self.pnl_percent = (exit_price - self.entry_price) / self.entry_price * 100 * self.leverage
        else:  # SELL
            self.pnl_percent = (self.entry_price - exit_price) / self.entry_price * 100 * self.leverage
        
        self.pnl = self.pnl_percent * self.entry_price * self.quantity / 100
        self.status = "CLOSED"
        
        logger.info(f"Đóng vị thế {self.symbol} {self.side} tại {exit_price:.2f}, "
                  f"PnL: {self.pnl_percent:.2f}% (${self.pnl:.2f}), "
                  f"Lý do: {exit_reason}")
    
    def to_dict(self) -> Dict:
        """Chuyển đổi vị thế thành từ điển"""
        return {
            'trade_id': self.trade_id,
            'symbol': self.symbol,
            'side': self.side,
            'entry_price': self.entry_price,
            'quantity': self.quantity,
            'leverage': self.leverage,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'take_profit_price': self.take_profit_price,
            'stop_loss_price': self.stop_loss_price,
            'trailing_stop_active': self.trailing_stop_active,
            'trailing_stop_price': self.trailing_stop_price,
            'highest_price': self.highest_price,
            'lowest_price': self.lowest_price,
            'exit_price': self.exit_price,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'pnl': self.pnl,
            'pnl_percent': self.pnl_percent,
            'exit_reason': self.exit_reason,
            'status': self.status
        }

class AdvancedTradingSystem:
    """
    Hệ thống giao dịch nâng cao tích hợp nhiều chiến lược và kỹ thuật.
    """
    
    def __init__(self, 
                 binance_api: BinanceAPI = None, 
                 data_processor: DataProcessor = None,
                 initial_balance: float = 10000.0,
                 risk_percentage: float = 1.0,
                 timeframes: List[str] = None,
                 use_multi_timeframe: bool = True,
                 use_composite_indicators: bool = True,
                 use_liquidity_analysis: bool = True,
                 use_market_regimes: bool = True):
        """
        Khởi tạo hệ thống giao dịch nâng cao.
        
        Args:
            binance_api (BinanceAPI): Đối tượng API Binance
            data_processor (DataProcessor): Bộ xử lý dữ liệu
            initial_balance (float): Số dư ban đầu
            risk_percentage (float): Phần trăm rủi ro trên mỗi giao dịch
            timeframes (List[str]): Danh sách các khung thời gian để phân tích
            use_multi_timeframe (bool): Sử dụng phân tích đa khung thời gian
            use_composite_indicators (bool): Sử dụng chỉ báo tổng hợp
            use_liquidity_analysis (bool): Sử dụng phân tích thanh khoản
            use_market_regimes (bool): Sử dụng phát hiện giai đoạn thị trường
        """
        self.binance_api = binance_api
        self.data_processor = data_processor
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.risk_percentage = risk_percentage
        
        # Thiết lập các khung thời gian
        self.timeframes = timeframes or ['15m', '1h', '4h', '1d']
        
        # Thiết lập các thành phần
        self.use_multi_timeframe = use_multi_timeframe
        self.use_composite_indicators = use_composite_indicators
        self.use_liquidity_analysis = use_liquidity_analysis
        self.use_market_regimes = use_market_regimes
        
        # Khởi tạo các module phân tích
        if self.use_multi_timeframe:
            self.multi_timeframe_analyzer = MultiTimeframeAnalyzer(
                binance_api=binance_api,
                data_processor=data_processor,
                timeframes=self.timeframes
            )
        else:
            self.multi_timeframe_analyzer = None
        
        if self.use_composite_indicators:
            self.composite_indicator = CompositeIndicator(
                indicators=['rsi', 'macd', 'ema_cross', 'bbands', 'volume_trend'],
                dynamic_weights=True
            )
        else:
            self.composite_indicator = None
        
        if self.use_liquidity_analysis:
            self.liquidity_analyzer = LiquidityAnalyzer(
                binance_api=binance_api
            )
        else:
            self.liquidity_analyzer = None
        
        if self.use_market_regimes:
            self.market_regime_detector = MarketRegimeDetector()
        else:
            self.market_regime_detector = None
        
        # Theo dõi vị thế
        self.open_positions = {}  # trade_id -> TradePosition
        self.closed_positions = []  # list of TradePosition objects
        
        # Theo dõi hiệu suất
        self.performance_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_profit': 0.0,
            'total_loss': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'average_profit': 0.0,
            'average_loss': 0.0
        }
        
        # Bộ nhớ cache
        self.cache = {
            'signals': {},
            'analysis': {},
            'last_update': {}
        }
        
        logger.info(f"Khởi tạo Hệ thống giao dịch nâng cao với số dư ban đầu: ${initial_balance:.2f}, "
                  f"Rủi ro: {risk_percentage:.1f}%, Timeframes: {self.timeframes}")
    
    def analyze_market(self, symbol: str, primary_timeframe: str = '1h') -> Dict:
        """
        Phân tích thị trường sử dụng tất cả các kỹ thuật nâng cao.
        
        Args:
            symbol (str): Mã cặp giao dịch
            primary_timeframe (str): Khung thời gian chính để phân tích
            
        Returns:
            Dict: Kết quả phân tích thị trường
        """
        # Kiểm tra cache
        cache_key = f"{symbol}_{primary_timeframe}"
        current_time = time.time()
        
        if cache_key in self.cache['analysis']:
            last_update = self.cache['last_update'].get(cache_key, 0)
            # Nếu cập nhật trong 60s qua, sử dụng cache
            if current_time - last_update < 60:
                return self.cache['analysis'][cache_key]
        
        # Lấy dữ liệu chính
        df = None
        if self.data_processor and self.binance_api:
            df = self.data_processor.get_historical_data(symbol, primary_timeframe, lookback_days=30)
        
        if df is None or df.empty:
            logger.error(f"Không thể lấy dữ liệu cho {symbol} trên khung {primary_timeframe}")
            return None
        
        # Khởi tạo kết quả
        result = {
            'symbol': symbol,
            'primary_timeframe': primary_timeframe,
            'analysis_time': datetime.now().isoformat(),
            'current_price': df['close'].iloc[-1],
            'signals': {},
            'market_regime': None,
            'multi_timeframe': None,
            'composite_indicator': None,
            'liquidity_analysis': None,
            'entry_points': [],
            'risk_management': {},
            'current_volatility': None,
            'signal_strength': None,
            'summary': None
        }
        
        # 1. Phân tích giai đoạn thị trường
        if self.use_market_regimes and self.market_regime_detector:
            regime = self.market_regime_detector.detect_regime(df)
            result['market_regime'] = {
                'regime': regime,
                'description': self.market_regime_detector._get_regime_description(regime)
            }
            
            logger.info(f"Giai đoạn thị trường {symbol}: {regime}")
        
        # 2. Phân tích đa khung thời gian
        if self.use_multi_timeframe and self.multi_timeframe_analyzer:
            try:
                mtf_result = self.multi_timeframe_analyzer.consolidate_signals(symbol, lookback_days=30)
                result['multi_timeframe'] = mtf_result
                result['signals']['mtf'] = mtf_result['signal']
                
                # Thêm điểm vào lệnh tối ưu
                entry_points = self.multi_timeframe_analyzer.get_optimal_entry_points(symbol, lookback_days=30)
                if entry_points and 'entry_points' in entry_points:
                    result['entry_points'].extend(entry_points['entry_points'])
            except Exception as e:
                logger.error(f"Lỗi khi phân tích đa khung thời gian: {e}")
        
        # 3. Phân tích chỉ báo tổng hợp
        if self.use_composite_indicators and self.composite_indicator:
            try:
                ci_result = self.composite_indicator.calculate_composite_score(df)
                result['composite_indicator'] = ci_result
                result['signals']['ci'] = ci_result['signal']
                
                # Lấy khuyến nghị giao dịch
                recommendation = self.composite_indicator.get_trading_recommendation(df)
                if recommendation and 'action' in recommendation:
                    result['trading_recommendation'] = recommendation
            except Exception as e:
                logger.error(f"Lỗi khi phân tích chỉ báo tổng hợp: {e}")
        
        # 4. Phân tích thanh khoản
        if self.use_liquidity_analysis and self.liquidity_analyzer:
            try:
                liq_result = self.liquidity_analyzer.analyze_orderbook(symbol)
                result['liquidity_analysis'] = liq_result
                
                # Phát hiện sự kiện thanh khoản đáng chú ý
                liq_events = self.liquidity_analyzer.detect_liquidity_events(symbol)
                if liq_events and liq_events['events']:
                    result['liquidity_events'] = liq_events
                
                # Đề xuất điểm vào/ra dựa trên thanh khoản
                entry_exit_recs = self.liquidity_analyzer.get_entry_exit_recommendations(symbol)
                if entry_exit_recs:
                    result['liquidity_recommendations'] = entry_exit_recs
                    
                    # Thêm điểm vào lệnh từ phân tích thanh khoản
                    if 'buy_entries' in entry_exit_recs:
                        for entry in entry_exit_recs['buy_entries']:
                            entry['source'] = 'liquidity'
                            result['entry_points'].append(entry)
                    
                    if 'sell_entries' in entry_exit_recs:
                        for entry in entry_exit_recs['sell_entries']:
                            entry['source'] = 'liquidity'
                            result['entry_points'].append(entry)
            except Exception as e:
                logger.error(f"Lỗi khi phân tích thanh khoản: {e}")
        
        # 5. Tính toán biến động hiện tại
        result['current_volatility'] = self._calculate_volatility(df)
        
        # 6. Tính toán độ mạnh tín hiệu tổng hợp
        signals = result['signals']
        if signals:
            # Tính trọng số
            weights = {
                'mtf': 0.5,  # Đa khung thời gian
                'ci': 0.3,   # Chỉ báo tổng hợp
                'regime': 0.2  # Giai đoạn thị trường
            }
            
            weighted_signal = 0
            total_weight = 0
            
            for signal_type, signal_value in signals.items():
                weight = weights.get(signal_type, 0)
                weighted_signal += signal_value * weight
                total_weight += weight
            
            if total_weight > 0:
                result['signal_strength'] = weighted_signal / total_weight
                
                # Chuyển đổi thành tín hiệu rõ ràng
                if result['signal_strength'] >= 0.5:
                    result['signal'] = 'BUY'
                    result['confidence'] = min(abs(result['signal_strength']) * 2 * 100, 100)
                elif result['signal_strength'] <= -0.5:
                    result['signal'] = 'SELL'
                    result['confidence'] = min(abs(result['signal_strength']) * 2 * 100, 100)
                else:
                    result['signal'] = 'NEUTRAL'
                    result['confidence'] = 50 - min(abs(result['signal_strength']) * 100, 50)
        
        # 7. Đề xuất quản lý rủi ro dựa trên biến động
        result['risk_management'] = self._suggest_risk_management(result['current_volatility'],
                                                                result.get('market_regime', {}).get('regime'))
        
        # 8. Tạo tóm tắt
        result['summary'] = self._generate_summary(result)
        
        # Lưu vào cache
        self.cache['analysis'][cache_key] = result
        self.cache['last_update'][cache_key] = current_time
        
        return result
    
    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """
        Tính toán biến động hiện tại của thị trường.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            
        Returns:
            float: Giá trị biến động
        """
        if 'atr' in df.columns:
            return df['atr'].iloc[-1]
        
        # Tính ATR thủ công nếu không có sẵn
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        tr1 = np.abs(high[1:] - low[1:])
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        
        tr = np.vstack([tr1, tr2, tr3]).max(axis=0)
        atr = np.mean(tr[-14:])  # 14-period ATR
        
        return atr
    
    def _suggest_risk_management(self, volatility: float, market_regime: str = None) -> Dict:
        """
        Đề xuất các tham số quản lý rủi ro dựa trên biến động và giai đoạn thị trường.
        
        Args:
            volatility (float): Giá trị biến động hiện tại
            market_regime (str): Giai đoạn thị trường hiện tại
            
        Returns:
            Dict: Các tham số quản lý rủi ro được đề xuất
        """
        # Tính toán tỷ lệ biến động
        current_price = None
        for cache_key, analysis in self.cache['analysis'].items():
            if 'current_price' in analysis:
                current_price = analysis['current_price']
                break
        
        if current_price is None:
            current_price = 50000  # Giá mặc định nếu không có thông tin
        
        volatility_percent = (volatility / current_price) * 100
        
        # Điều chỉnh dựa trên giai đoạn thị trường
        regime_multipliers = {
            'trending_up': 1.2,    # Xu hướng tăng - tăng size
            'trending_down': 0.8,  # Xu hướng giảm - giảm size
            'ranging': 1.0,        # Đi ngang - bình thường
            'volatile': 0.6,       # Biến động - giảm size nhiều
            'breakout': 1.1,       # Breakout - tăng size vừa phải
            'neutral': 1.0         # Trung tính - bình thường
        }
        
        regime_multiplier = regime_multipliers.get(market_regime, 1.0)
        
        # Tính toán các tham số quản lý rủi ro
        # 1. Stop Loss: 2-3x volatility
        stop_loss_pct = min(volatility_percent * 2.5, 10)  # Giới hạn tối đa 10%
        
        # 2. Take Profit: 1.5-3x Stop Loss
        take_profit_pct = stop_loss_pct * 2.5
        
        # 3. Position Size: điều chỉnh theo giai đoạn thị trường
        position_size_pct = self.risk_percentage * regime_multiplier
        
        # 4. Trailing Stop: kích hoạt ở 40-60% của TP
        trailing_stop_activation = take_profit_pct * 0.5
        trailing_stop_callback = stop_loss_pct * 0.4
        
        return {
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct,
            'position_size_pct': position_size_pct,
            'trailing_stop': True,
            'trailing_stop_activation': trailing_stop_activation,
            'trailing_stop_callback': trailing_stop_callback,
            'volatility_percent': volatility_percent,
            'regime_multiplier': regime_multiplier
        }
    
    def _generate_summary(self, analysis: Dict) -> str:
        """
        Tạo tóm tắt từ kết quả phân tích.
        
        Args:
            analysis (Dict): Kết quả phân tích thị trường
            
        Returns:
            str: Tóm tắt phân tích
        """
        symbol = analysis['symbol']
        primary_tf = analysis['primary_timeframe']
        current_price = analysis.get('current_price', 0)
        
        summary = []
        
        # Thêm thông tin giai đoạn thị trường
        if 'market_regime' in analysis and analysis['market_regime']:
            regime = analysis['market_regime'].get('regime', 'unknown')
            summary.append(f"Thị trường đang ở giai đoạn {regime}.")
        
        # Thêm tín hiệu tổng hợp
        if 'signal' in analysis:
            signal = analysis['signal']
            confidence = analysis.get('confidence', 0)
            
            if signal == 'BUY':
                summary.append(f"Tín hiệu MUA với độ tin cậy {confidence:.1f}%.")
            elif signal == 'SELL':
                summary.append(f"Tín hiệu BÁN với độ tin cậy {confidence:.1f}%.")
            else:
                summary.append(f"Không có tín hiệu rõ ràng (NEUTRAL).")
        
        # Thêm thông tin thanh khoản
        if 'liquidity_analysis' in analysis and analysis['liquidity_analysis']:
            market_pressure = analysis['liquidity_analysis'].get('market_pressure', 'neutral')
            bid_ask_ratio = analysis['liquidity_analysis'].get('bid_ask_ratio', 1.0)
            
            if market_pressure == 'buy':
                summary.append(f"Áp lực mua mạnh (tỷ lệ bid/ask: {bid_ask_ratio:.2f}).")
            elif market_pressure == 'sell':
                summary.append(f"Áp lực bán mạnh (tỷ lệ bid/ask: {bid_ask_ratio:.2f}).")
        
        # Thêm thông tin biến động
        if 'current_volatility' in analysis and analysis['current_volatility']:
            volatility = analysis['current_volatility']
            volatility_pct = (volatility / current_price) * 100
            
            if volatility_pct > 3:
                summary.append(f"Biến động cao ({volatility_pct:.2f}%).")
            elif volatility_pct < 1:
                summary.append(f"Biến động thấp ({volatility_pct:.2f}%).")
        
        # Thêm đề xuất giao dịch
        if 'signal' in analysis:
            signal = analysis['signal']
            
            if signal == 'BUY':
                entry_points = [e for e in analysis.get('entry_points', []) 
                               if e.get('price', 0) < current_price]
                
                if entry_points:
                    best_entry = min(entry_points, key=lambda x: abs(x['price'] - current_price))
                    summary.append(f"Đề xuất MUA gần {best_entry['price']:.2f}.")
                else:
                    summary.append(f"Đề xuất MUA khi giá điều chỉnh về gần hơn.")
            
            elif signal == 'SELL':
                entry_points = [e for e in analysis.get('entry_points', []) 
                               if e.get('price', 0) > current_price]
                
                if entry_points:
                    best_entry = min(entry_points, key=lambda x: abs(x['price'] - current_price))
                    summary.append(f"Đề xuất BÁN gần {best_entry['price']:.2f}.")
                else:
                    summary.append(f"Đề xuất BÁN khi giá phục hồi lên cao hơn.")
            
            else:
                summary.append("Đề xuất CHỜ ĐỢI thêm tín hiệu rõ ràng.")
        
        # Ghép tất cả lại và trả về
        return " ".join(summary)
    
    def execute_trade(self, symbol: str, side: str, position_size: float = None, 
                     entry_price: float = None, leverage: int = 1, 
                     risk_params: Dict = None) -> str:
        """
        Thực hiện giao dịch.
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng giao dịch ('BUY' hoặc 'SELL')
            position_size (float): Kích thước vị thế (% của balance)
            entry_price (float): Giá vào lệnh
            leverage (int): Đòn bẩy
            risk_params (Dict): Tham số quản lý rủi ro
            
        Returns:
            str: ID của giao dịch nếu thành công, None nếu thất bại
        """
        # Kiểm tra các tham số
        if side not in ['BUY', 'SELL']:
            logger.error(f"Hướng giao dịch không hợp lệ: {side}")
            return None
        
        # Nếu không có giá vào lệnh, lấy giá hiện tại
        if entry_price is None:
            # Lấy giá hiện tại
            if self.binance_api:
                current_price = self.binance_api.get_symbol_price(symbol)
                if current_price:
                    entry_price = current_price
                else:
                    logger.error(f"Không thể lấy giá hiện tại cho {symbol}")
                    return None
            else:
                logger.error("Không có binance_api để lấy giá")
                return None
        
        # Nếu không có position_size, sử dụng risk_percentage mặc định
        if position_size is None:
            position_size = self.risk_percentage
        
        # Tính toán số lượng giao dịch
        position_value = self.current_balance * (position_size / 100)
        quantity = position_value / entry_price
        
        # Tạo vị thế
        position = TradePosition(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            quantity=quantity,
            leverage=leverage
        )
        
        # Thiết lập các tham số quản lý rủi ro
        if risk_params:
            position.set_risk_parameters(
                take_profit_pct=risk_params.get('take_profit_pct'),
                stop_loss_pct=risk_params.get('stop_loss_pct'),
                trailing_stop=risk_params.get('trailing_stop', False),
                ts_activation_pct=risk_params.get('trailing_stop_activation'),
                ts_callback_pct=risk_params.get('trailing_stop_callback')
            )
        
        # Thực hiện giao dịch với API (nếu có)
        if self.binance_api:
            try:
                order = self.binance_api.create_order(
                    symbol=symbol,
                    side=side,
                    order_type='MARKET',
                    quantity=quantity
                )
                
                if order:
                    logger.info(f"Đã đặt lệnh: {side} {symbol}, Số lượng: {quantity:.6f}, "
                             f"Giá: {entry_price:.2f}")
                else:
                    logger.error(f"Không thể đặt lệnh: {side} {symbol}")
                    return None
            except Exception as e:
                logger.error(f"Lỗi khi đặt lệnh: {e}")
                return None
        
        # Lưu vị thế
        self.open_positions[position.trade_id] = position
        
        # Cập nhật số dư (mô phỏng)
        # Thực tế số dư sẽ được cập nhật sau khi đóng vị thế
        
        logger.info(f"Đã thực hiện giao dịch: {side} {symbol}, ID: {position.trade_id}")
        
        return position.trade_id
    
    def update_positions(self, current_prices: Dict[str, float] = None) -> List[str]:
        """
        Cập nhật trạng thái tất cả các vị thế đang mở.
        
        Args:
            current_prices (Dict[str, float]): Giá hiện tại cho mỗi mã
            
        Returns:
            List[str]: Danh sách ID của các vị thế đã đóng
        """
        closed_positions_ids = []
        
        # Lấy giá hiện tại nếu chưa được cung cấp
        if not current_prices and self.binance_api:
            current_prices = {}
            
            for trade_id, position in self.open_positions.items():
                symbol = position.symbol
                if symbol not in current_prices:
                    price = self.binance_api.get_symbol_price(symbol)
                    if price:
                        current_prices[symbol] = price
        
        # Cập nhật từng vị thế
        for trade_id, position in list(self.open_positions.items()):
            symbol = position.symbol
            
            if symbol in current_prices:
                current_price = current_prices[symbol]
                
                # Kiểm tra các điều kiện đóng vị thế
                should_close, reason = position.update_price(current_price)
                
                if should_close:
                    self.close_position(trade_id, current_price, reason)
                    closed_positions_ids.append(trade_id)
            else:
                logger.warning(f"Không có giá hiện tại cho {symbol}, không thể cập nhật vị thế {trade_id}")
        
        return closed_positions_ids
    
    def close_position(self, trade_id: str, exit_price: float = None, exit_reason: str = None) -> bool:
        """
        Đóng một vị thế.
        
        Args:
            trade_id (str): ID của vị thế
            exit_price (float): Giá thoát lệnh
            exit_reason (str): Lý do thoát lệnh
            
        Returns:
            bool: True nếu đóng thành công, False nếu thất bại
        """
        if trade_id not in self.open_positions:
            logger.error(f"Không tìm thấy vị thế với ID {trade_id}")
            return False
        
        position = self.open_positions[trade_id]
        
        # Nếu không có giá thoát, lấy giá hiện tại
        if exit_price is None:
            if self.binance_api:
                exit_price = self.binance_api.get_symbol_price(position.symbol)
            
            if exit_price is None:
                logger.error(f"Không thể lấy giá thoát cho {position.symbol}")
                return False
        
        # Đóng vị thế với binance_api (nếu có)
        if self.binance_api:
            try:
                close_side = 'SELL' if position.side == 'BUY' else 'BUY'
                
                order = self.binance_api.create_order(
                    symbol=position.symbol,
                    side=close_side,
                    order_type='MARKET',
                    quantity=position.quantity
                )
                
                if not order:
                    logger.error(f"Không thể đóng vị thế {trade_id}")
                    return False
            except Exception as e:
                logger.error(f"Lỗi khi đóng vị thế {trade_id}: {e}")
                return False
        
        # Đóng vị thế trong hệ thống
        position.close_position(exit_price, datetime.now(), exit_reason)
        
        # Cập nhật số dư
        if position.pnl is not None:
            self.current_balance += position.pnl
        
        # Chuyển vị thế sang danh sách đã đóng
        self.closed_positions.append(position)
        del self.open_positions[trade_id]
        
        # Cập nhật các chỉ số hiệu suất
        self._update_performance_metrics()
        
        logger.info(f"Đã đóng vị thế {trade_id} tại {exit_price:.2f}, Lý do: {exit_reason}, "
                  f"Số dư hiện tại: ${self.current_balance:.2f}")
        
        return True
    
    def _update_performance_metrics(self):
        """Cập nhật các chỉ số hiệu suất của hệ thống"""
        # Tính toán các chỉ số từ các vị thế đã đóng
        total_trades = len(self.closed_positions)
        
        if total_trades == 0:
            return
        
        # Phân loại giao dịch
        winning_trades = [p for p in self.closed_positions if p.pnl and p.pnl > 0]
        losing_trades = [p for p in self.closed_positions if p.pnl and p.pnl <= 0]
        
        # Tính win rate
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        # Tính tổng lợi nhuận và thua lỗ
        total_profit = sum(p.pnl for p in winning_trades) if winning_trades else 0
        total_loss = sum(p.pnl for p in losing_trades) if losing_trades else 0
        
        # Tính profit factor
        profit_factor = abs(total_profit / total_loss) if total_loss != 0 else float('inf')
        
        # Tính trung bình lợi nhuận và thua lỗ
        average_profit = total_profit / len(winning_trades) if winning_trades else 0
        average_loss = total_loss / len(losing_trades) if losing_trades else 0
        
        # Tính max drawdown
        balances = [self.initial_balance]
        for position in sorted(self.closed_positions, key=lambda p: p.exit_time):
            if position.pnl is not None:
                balances.append(balances[-1] + position.pnl)
        
        # Tính max drawdown
        max_balance = balances[0]
        max_drawdown = 0
        for balance in balances:
            max_balance = max(max_balance, balance)
            drawdown = (max_balance - balance) / max_balance * 100
            max_drawdown = max(max_drawdown, drawdown)
        
        # Cập nhật số liệu
        self.performance_metrics = {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'total_profit': total_profit,
            'total_loss': total_loss,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'average_profit': average_profit,
            'average_loss': average_loss,
            'current_balance': self.current_balance,
            'profit_percent': (self.current_balance - self.initial_balance) / self.initial_balance * 100
        }
        
        logger.info(f"Hiệu suất cập nhật: Win rate {win_rate:.1f}%, "
                  f"Profit factor {profit_factor:.2f}, "
                  f"Tổng PnL ${total_profit + total_loss:.2f}")
    
    def get_performance_summary(self) -> Dict:
        """
        Lấy tóm tắt hiệu suất của hệ thống.
        
        Returns:
            Dict: Tóm tắt hiệu suất
        """
        # Cập nhật số liệu hiệu suất
        self._update_performance_metrics()
        
        # Trả về số liệu
        return self.performance_metrics
    
    def get_active_positions(self) -> List[Dict]:
        """
        Lấy danh sách các vị thế đang mở.
        
        Returns:
            List[Dict]: Danh sách các vị thế đang mở
        """
        return [position.to_dict() for position in self.open_positions.values()]
    
    def get_closed_positions(self, limit: int = None) -> List[Dict]:
        """
        Lấy danh sách các vị thế đã đóng.
        
        Args:
            limit (int): Số lượng vị thế tối đa để trả về
            
        Returns:
            List[Dict]: Danh sách các vị thế đã đóng
        """
        positions = [position.to_dict() for position in self.closed_positions]
        
        # Sắp xếp theo thời gian đóng, mới nhất trước
        positions = sorted(positions, key=lambda p: p['exit_time'] if p['exit_time'] else '', reverse=True)
        
        if limit:
            return positions[:limit]
        return positions
    
    def generate_trading_plan(self, symbol: str, timeframe: str = '1h') -> Dict:
        """
        Tạo kế hoạch giao dịch chi tiết cho một mã.
        
        Args:
            symbol (str): Mã cặp giao dịch
            timeframe (str): Khung thời gian
            
        Returns:
            Dict: Kế hoạch giao dịch
        """
        # Phân tích thị trường
        analysis = self.analyze_market(symbol, timeframe)
        if not analysis:
            logger.error(f"Không thể phân tích thị trường cho {symbol}")
            return None
        
        # Lấy giá hiện tại
        current_price = analysis['current_price']
        
        # Lấy tín hiệu và độ tin cậy
        signal = analysis.get('signal', 'NEUTRAL')
        confidence = analysis.get('confidence', 0)
        
        # Lấy thông tin quản lý rủi ro
        risk_management = analysis.get('risk_management', {})
        
        # Lấy các điểm vào lệnh tiềm năng
        entry_points = analysis.get('entry_points', [])
        
        # Tạo kế hoạch giao dịch
        trading_plan = {
            'symbol': symbol,
            'timeframe': timeframe,
            'analysis_time': datetime.now().isoformat(),
            'current_price': current_price,
            'signal': signal,
            'confidence': confidence,
            'market_regime': analysis.get('market_regime', {}).get('regime'),
            'primary_action': None,
            'entry_levels': [],
            'take_profit_levels': [],
            'stop_loss_levels': [],
            'position_sizing': risk_management.get('position_size_pct', self.risk_percentage),
            'risk_reward_ratio': None,
            'notes': [],
            'summary': None
        }
        
        # Xác định hành động chính
        if signal == 'BUY' and confidence >= 70:
            trading_plan['primary_action'] = 'STRONG_BUY'
        elif signal == 'BUY' and confidence >= 50:
            trading_plan['primary_action'] = 'BUY'
        elif signal == 'SELL' and confidence >= 70:
            trading_plan['primary_action'] = 'STRONG_SELL'
        elif signal == 'SELL' and confidence >= 50:
            trading_plan['primary_action'] = 'SELL'
        else:
            trading_plan['primary_action'] = 'WAIT'
        
        # Thêm các điểm vào lệnh
        if trading_plan['primary_action'] in ['STRONG_BUY', 'BUY']:
            # Tìm các điểm vào lệnh mua dưới giá hiện tại
            buy_entries = [e for e in entry_points if e.get('price', 0) < current_price]
            
            if buy_entries:
                # Sắp xếp theo khoảng cách từ giá hiện tại
                buy_entries = sorted(buy_entries, key=lambda x: abs(x['price'] - current_price))
                
                # Lấy 3 điểm mua tốt nhất
                for entry in buy_entries[:3]:
                    trading_plan['entry_levels'].append({
                        'price': entry['price'],
                        'distance_pct': ((current_price - entry['price']) / current_price) * 100,
                        'type': 'BUY',
                        'description': f"Mua tại {entry['price']:.2f}"
                    })
            
            # Nếu không có điểm vào lệnh hoặc tín hiệu mạnh, thêm một điểm tại giá thị trường
            if not trading_plan['entry_levels'] or trading_plan['primary_action'] == 'STRONG_BUY':
                trading_plan['entry_levels'].append({
                    'price': current_price,
                    'distance_pct': 0,
                    'type': 'BUY',
                    'description': f"Mua tại giá thị trường {current_price:.2f}"
                })
        
        elif trading_plan['primary_action'] in ['STRONG_SELL', 'SELL']:
            # Tìm các điểm vào lệnh bán trên giá hiện tại
            sell_entries = [e for e in entry_points if e.get('price', 0) > current_price]
            
            if sell_entries:
                # Sắp xếp theo khoảng cách từ giá hiện tại
                sell_entries = sorted(sell_entries, key=lambda x: abs(x['price'] - current_price))
                
                # Lấy 3 điểm bán tốt nhất
                for entry in sell_entries[:3]:
                    trading_plan['entry_levels'].append({
                        'price': entry['price'],
                        'distance_pct': ((entry['price'] - current_price) / current_price) * 100,
                        'type': 'SELL',
                        'description': f"Bán tại {entry['price']:.2f}"
                    })
            
            # Nếu không có điểm vào lệnh hoặc tín hiệu mạnh, thêm một điểm tại giá thị trường
            if not trading_plan['entry_levels'] or trading_plan['primary_action'] == 'STRONG_SELL':
                trading_plan['entry_levels'].append({
                    'price': current_price,
                    'distance_pct': 0,
                    'type': 'SELL',
                    'description': f"Bán tại giá thị trường {current_price:.2f}"
                })
        
        # Thêm các điểm chốt lời và dừng lỗ
        # Dựa trên các tham số quản lý rủi ro đề xuất
        take_profit_pct = risk_management.get('take_profit_pct', 10)
        stop_loss_pct = risk_management.get('stop_loss_pct', 5)
        
        # Tính risk-reward ratio
        trading_plan['risk_reward_ratio'] = take_profit_pct / stop_loss_pct if stop_loss_pct > 0 else None
        
        # Thêm các điểm TP và SL cho mỗi điểm vào lệnh
        for entry in trading_plan['entry_levels']:
            if entry['type'] == 'BUY':
                # TP cho vị thế mua
                tp_price = entry['price'] * (1 + take_profit_pct / 100)
                trading_plan['take_profit_levels'].append({
                    'price': tp_price,
                    'distance_pct': ((tp_price - entry['price']) / entry['price']) * 100,
                    'entry_price': entry['price'],
                    'description': f"TP tại {tp_price:.2f} (+{take_profit_pct:.1f}%)"
                })
                
                # SL cho vị thế mua
                sl_price = entry['price'] * (1 - stop_loss_pct / 100)
                trading_plan['stop_loss_levels'].append({
                    'price': sl_price,
                    'distance_pct': ((entry['price'] - sl_price) / entry['price']) * 100,
                    'entry_price': entry['price'],
                    'description': f"SL tại {sl_price:.2f} (-{stop_loss_pct:.1f}%)"
                })
            
            elif entry['type'] == 'SELL':
                # TP cho vị thế bán
                tp_price = entry['price'] * (1 - take_profit_pct / 100)
                trading_plan['take_profit_levels'].append({
                    'price': tp_price,
                    'distance_pct': ((entry['price'] - tp_price) / entry['price']) * 100,
                    'entry_price': entry['price'],
                    'description': f"TP tại {tp_price:.2f} (-{take_profit_pct:.1f}%)"
                })
                
                # SL cho vị thế bán
                sl_price = entry['price'] * (1 + stop_loss_pct / 100)
                trading_plan['stop_loss_levels'].append({
                    'price': sl_price,
                    'distance_pct': ((sl_price - entry['price']) / entry['price']) * 100,
                    'entry_price': entry['price'],
                    'description': f"SL tại {sl_price:.2f} (+{stop_loss_pct:.1f}%)"
                })
        
        # Thêm ghi chú
        if trading_plan['primary_action'] in ['STRONG_BUY', 'BUY']:
            trading_plan['notes'].append(f"Tín hiệu MUA với độ tin cậy {confidence:.1f}%")
            
            if analysis.get('market_regime', {}).get('regime') == 'trending_up':
                trading_plan['notes'].append("Xu hướng tăng đã được xác nhận")
            elif analysis.get('market_regime', {}).get('regime') == 'ranging':
                trading_plan['notes'].append("Thị trường đang trong vùng tích lũy, cân nhắc giảm vị thế")
        
        elif trading_plan['primary_action'] in ['STRONG_SELL', 'SELL']:
            trading_plan['notes'].append(f"Tín hiệu BÁN với độ tin cậy {confidence:.1f}%")
            
            if analysis.get('market_regime', {}).get('regime') == 'trending_down':
                trading_plan['notes'].append("Xu hướng giảm đã được xác nhận")
            elif analysis.get('market_regime', {}).get('regime') == 'ranging':
                trading_plan['notes'].append("Thị trường đang trong vùng tích lũy, cân nhắc giảm vị thế")
        
        else:
            trading_plan['notes'].append("Tín hiệu không rõ ràng, nên chờ đợi thêm xác nhận")
        
        # Thêm thông tin về biến động
        if 'current_volatility' in analysis:
            volatility_pct = (analysis['current_volatility'] / current_price) * 100
            if volatility_pct > 3:
                trading_plan['notes'].append(f"Biến động cao ({volatility_pct:.2f}%), cân nhắc giảm kích thước vị thế")
            elif volatility_pct < 1:
                trading_plan['notes'].append(f"Biến động thấp ({volatility_pct:.2f}%), có thể tăng kích thước vị thế")
        
        # Tạo tóm tắt
        summary_parts = []
        
        if trading_plan['primary_action'] == 'STRONG_BUY':
            summary_parts.append(f"MUA MẠNH {symbol} với độ tin cậy {confidence:.1f}%.")
        elif trading_plan['primary_action'] == 'BUY':
            summary_parts.append(f"MUA {symbol} với độ tin cậy {confidence:.1f}%.")
        elif trading_plan['primary_action'] == 'STRONG_SELL':
            summary_parts.append(f"BÁN MẠNH {symbol} với độ tin cậy {confidence:.1f}%.")
        elif trading_plan['primary_action'] == 'SELL':
            summary_parts.append(f"BÁN {symbol} với độ tin cậy {confidence:.1f}%.")
        else:
            summary_parts.append(f"CHỜ ĐỢI thêm tín hiệu rõ ràng cho {symbol}.")
        
        if trading_plan['entry_levels']:
            entry = trading_plan['entry_levels'][0]
            if entry['distance_pct'] == 0:
                summary_parts.append(f"Vào lệnh tại giá thị trường {entry['price']:.2f}.")
            else:
                summary_parts.append(f"Vào lệnh tại {entry['price']:.2f} (cách {entry['distance_pct']:.1f}%).")
        
        if trading_plan['take_profit_levels'] and trading_plan['stop_loss_levels']:
            tp = trading_plan['take_profit_levels'][0]
            sl = trading_plan['stop_loss_levels'][0]
            summary_parts.append(f"TP: {tp['price']:.2f}, SL: {sl['price']:.2f}, RR: {trading_plan['risk_reward_ratio']:.2f}.")
        
        if trading_plan['notes']:
            summary_parts.append(trading_plan['notes'][0])
        
        trading_plan['summary'] = " ".join(summary_parts)
        
        logger.info(f"Đã tạo kế hoạch giao dịch cho {symbol}: {trading_plan['summary']}")
        
        return trading_plan
    
    def save_state(self, file_path: str = 'advanced_trading_state.json') -> bool:
        """
        Lưu trạng thái của hệ thống.
        
        Args:
            file_path (str): Đường dẫn đến file lưu trạng thái
            
        Returns:
            bool: True nếu lưu thành công, False nếu thất bại
        """
        try:
            # Chuyển đổi trạng thái thành JSON
            state = {
                'initial_balance': self.initial_balance,
                'current_balance': self.current_balance,
                'risk_percentage': self.risk_percentage,
                'timeframes': self.timeframes,
                'use_multi_timeframe': self.use_multi_timeframe,
                'use_composite_indicators': self.use_composite_indicators,
                'use_liquidity_analysis': self.use_liquidity_analysis,
                'use_market_regimes': self.use_market_regimes,
                'open_positions': [p.to_dict() for p in self.open_positions.values()],
                'closed_positions': [p.to_dict() for p in self.closed_positions],
                'performance_metrics': self.performance_metrics,
                'timestamp': datetime.now().isoformat()
            }
            
            # Lưu vào file
            with open(file_path, 'w') as f:
                json.dump(state, f, indent=2)
            
            logger.info(f"Đã lưu trạng thái hệ thống vào {file_path}")
            
            return True
        
        except Exception as e:
            logger.error(f"Lỗi khi lưu trạng thái: {e}")
            return False
    
    def load_state(self, file_path: str = 'advanced_trading_state.json') -> bool:
        """
        Tải trạng thái của hệ thống.
        
        Args:
            file_path (str): Đường dẫn đến file chứa trạng thái
            
        Returns:
            bool: True nếu tải thành công, False nếu thất bại
        """
        try:
            # Đọc từ file
            with open(file_path, 'r') as f:
                state = json.load(f)
            
            # Khôi phục các thuộc tính
            self.initial_balance = state.get('initial_balance', self.initial_balance)
            self.current_balance = state.get('current_balance', self.current_balance)
            self.risk_percentage = state.get('risk_percentage', self.risk_percentage)
            self.timeframes = state.get('timeframes', self.timeframes)
            self.use_multi_timeframe = state.get('use_multi_timeframe', self.use_multi_timeframe)
            self.use_composite_indicators = state.get('use_composite_indicators', self.use_composite_indicators)
            self.use_liquidity_analysis = state.get('use_liquidity_analysis', self.use_liquidity_analysis)
            self.use_market_regimes = state.get('use_market_regimes', self.use_market_regimes)
            self.performance_metrics = state.get('performance_metrics', self.performance_metrics)
            
            # Khôi phục vị thế đang mở
            self.open_positions = {}
            for position_dict in state.get('open_positions', []):
                position = TradePosition(
                    symbol=position_dict['symbol'],
                    side=position_dict['side'],
                    entry_price=position_dict['entry_price'],
                    quantity=position_dict['quantity'],
                    leverage=position_dict['leverage'],
                    entry_time=datetime.fromisoformat(position_dict['entry_time']) 
                                if position_dict['entry_time'] else None
                )
                position.take_profit_price = position_dict.get('take_profit_price')
                position.stop_loss_price = position_dict.get('stop_loss_price')
                position.trailing_stop_active = position_dict.get('trailing_stop_active', False)
                position.trailing_stop_price = position_dict.get('trailing_stop_price')
                position.highest_price = position_dict.get('highest_price')
                position.lowest_price = position_dict.get('lowest_price')
                position.status = position_dict.get('status', 'OPEN')
                position.trade_id = position_dict.get('trade_id', position.trade_id)
                
                self.open_positions[position.trade_id] = position
            
            # Khôi phục vị thế đã đóng
            self.closed_positions = []
            for position_dict in state.get('closed_positions', []):
                position = TradePosition(
                    symbol=position_dict['symbol'],
                    side=position_dict['side'],
                    entry_price=position_dict['entry_price'],
                    quantity=position_dict['quantity'],
                    leverage=position_dict['leverage'],
                    entry_time=datetime.fromisoformat(position_dict['entry_time']) 
                                if position_dict['entry_time'] else None
                )
                position.take_profit_price = position_dict.get('take_profit_price')
                position.stop_loss_price = position_dict.get('stop_loss_price')
                position.trailing_stop_active = position_dict.get('trailing_stop_active', False)
                position.trailing_stop_price = position_dict.get('trailing_stop_price')
                position.highest_price = position_dict.get('highest_price')
                position.lowest_price = position_dict.get('lowest_price')
                position.exit_price = position_dict.get('exit_price')
                position.exit_time = datetime.fromisoformat(position_dict['exit_time']) if position_dict.get('exit_time') else None
                position.pnl = position_dict.get('pnl')
                position.pnl_percent = position_dict.get('pnl_percent')
                position.exit_reason = position_dict.get('exit_reason')
                position.status = position_dict.get('status', 'CLOSED')
                position.trade_id = position_dict.get('trade_id', position.trade_id)
                
                self.closed_positions.append(position)
            
            logger.info(f"Đã tải trạng thái hệ thống từ {file_path}: "
                      f"{len(self.open_positions)} vị thế đang mở, "
                      f"{len(self.closed_positions)} vị thế đã đóng")
            
            return True
        
        except FileNotFoundError:
            logger.warning(f"Không tìm thấy file trạng thái {file_path}")
            return False
        
        except Exception as e:
            logger.error(f"Lỗi khi tải trạng thái: {e}")
            return False


def main():
    """Hàm chính để test hệ thống giao dịch nâng cao"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hệ thống giao dịch tiên tiến')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Mã giao dịch')
    parser.add_argument('--timeframe', type=str, default='1h', help='Khung thời gian chính')
    parser.add_argument('--balance', type=float, default=10000.0, help='Số dư ban đầu')
    parser.add_argument('--risk', type=float, default=1.0, help='Phần trăm rủi ro trên mỗi giao dịch')
    parser.add_argument('--mode', type=str, choices=['analyze', 'plan', 'execute'], 
                        default='analyze', help='Chế độ hoạt động')
    parser.add_argument('--simulation', action='store_true', help='Chạy ở chế độ mô phỏng')
    
    args = parser.parse_args()
    
    # Khởi tạo API và bộ xử lý dữ liệu
    binance_api = BinanceAPI(simulation_mode=args.simulation)
    data_processor = DataProcessor(binance_api, simulation_mode=args.simulation)
    
    # Khởi tạo hệ thống giao dịch
    trading_system = AdvancedTradingSystem(
        binance_api=binance_api,
        data_processor=data_processor,
        initial_balance=args.balance,
        risk_percentage=args.risk
    )
    
    # Xử lý theo chế độ
    if args.mode == 'analyze':
        # Phân tích thị trường
        analysis = trading_system.analyze_market(args.symbol, args.timeframe)
        if analysis:
            print(f"=== Phân tích {args.symbol} trên khung {args.timeframe} ===")
            print(f"Giá hiện tại: {analysis['current_price']:.2f}")
            print(f"Tín hiệu: {analysis.get('signal', 'NEUTRAL')}")
            print(f"Độ tin cậy: {analysis.get('confidence', 0):.1f}%")
            print(f"Giai đoạn thị trường: {analysis.get('market_regime', {}).get('regime', 'unknown')}")
            print(f"Tóm tắt: {analysis.get('summary', '')}")
        else:
            print(f"Không thể phân tích {args.symbol}")
    
    elif args.mode == 'plan':
        # Tạo kế hoạch giao dịch
        plan = trading_system.generate_trading_plan(args.symbol, args.timeframe)
        if plan:
            print(f"=== Kế hoạch giao dịch {args.symbol} trên khung {args.timeframe} ===")
            print(f"Hành động chính: {plan['primary_action']}")
            print(f"Điểm vào lệnh:")
            for entry in plan['entry_levels']:
                print(f"- {entry['description']} (cách {entry['distance_pct']:.1f}%)")
            print(f"Điểm chốt lời:")
            for tp in plan['take_profit_levels']:
                print(f"- {tp['description']}")
            print(f"Điểm dừng lỗ:")
            for sl in plan['stop_loss_levels']:
                print(f"- {sl['description']}")
            print(f"Tỷ lệ rủi ro/phần thưởng: {plan.get('risk_reward_ratio', 0):.2f}")
            print(f"Kích thước vị thế đề xuất: {plan.get('position_sizing', 1):.1f}%")
            print(f"Ghi chú:")
            for note in plan['notes']:
                print(f"- {note}")
            print(f"Tóm tắt: {plan.get('summary', '')}")
        else:
            print(f"Không thể tạo kế hoạch giao dịch cho {args.symbol}")
    
    elif args.mode == 'execute':
        # Thực hiện giao dịch
        if args.simulation:
            print("Chạy ở chế độ mô phỏng")
            
            # Phân tích thị trường
            analysis = trading_system.analyze_market(args.symbol, args.timeframe)
            if not analysis:
                print(f"Không thể phân tích {args.symbol}")
                return
            
            # Lấy tín hiệu
            signal = analysis.get('signal', 'NEUTRAL')
            
            if signal in ['BUY', 'SELL']:
                # Lấy thông tin quản lý rủi ro
                risk_params = analysis.get('risk_management', {})
                
                # Thực hiện giao dịch
                trade_id = trading_system.execute_trade(
                    symbol=args.symbol,
                    side=signal,
                    position_size=args.risk,
                    entry_price=analysis['current_price'],
                    leverage=3,
                    risk_params=risk_params
                )
                
                if trade_id:
                    print(f"Đã thực hiện giao dịch {signal} {args.symbol}, ID: {trade_id}")
                    
                    # Mô phỏng cập nhật giá
                    current_price = analysis['current_price']
                    price_change = current_price * 0.02  # Giả sử thay đổi 2%
                    
                    # Giá tăng nếu BUY, giảm nếu SELL (mô phỏng lãi)
                    if signal == 'BUY':
                        new_price = current_price * 1.02
                    else:
                        new_price = current_price * 0.98
                    
                    print(f"Mô phỏng thay đổi giá từ {current_price:.2f} thành {new_price:.2f}")
                    
                    # Cập nhật vị thế với giá mới
                    closed_positions = trading_system.update_positions({args.symbol: new_price})
                    
                    # Hiển thị kết quả
                    performance = trading_system.get_performance_summary()
                    print(f"Số dư hiện tại: ${performance['current_balance']:.2f}")
                    print(f"PnL: ${performance['current_balance'] - args.balance:.2f} "
                         f"({(performance['current_balance'] - args.balance) / args.balance * 100:.2f}%)")
                else:
                    print(f"Không thể thực hiện giao dịch {signal} {args.symbol}")
            else:
                print(f"Không có tín hiệu giao dịch rõ ràng cho {args.symbol}")
        else:
            print("Chế độ thực thi thực tế chưa được hỗ trợ trong demo này")


if __name__ == "__main__":
    main()