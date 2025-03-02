#!/usr/bin/env python3
"""
Script backtest toàn diện tích hợp tất cả tính năng mới

Script này thực hiện backtest toàn diện sử dụng tất cả các tính năng nâng cao:
1. Sử dụng dữ liệu thực hoặc giả lập
2. Tích hợp vị thế Pythagorean Position Sizer
3. Tích hợp phân tích rủi ro Monte Carlo
4. Tích hợp phát hiện chế độ thị trường Fractal
5. Tích hợp tối ưu hóa thời gian giao dịch
6. Tạo báo cáo và biểu đồ chi tiết
"""

import os
import sys
import json
import time
import random
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("comprehensive_backtest.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("comprehensive_backtest")

# Tạo thư mục kết quả nếu chưa tồn tại
os.makedirs("backtest_results", exist_ok=True)
os.makedirs("backtest_charts", exist_ok=True)

# Import các module mới phát triển
from position_sizing_enhanced import PythagoreanPositionSizer, MonteCarloRiskAnalyzer
from fractal_market_regime import FractalMarketRegimeDetector
from trading_time_optimizer import TradingTimeOptimizer

# Import các module cơ bản
try:
    # Import từ repository
    from binance_api import BinanceAPI
    from data_processor import DataProcessor
except ImportError as e:
    logger.warning(f"Không thể import các module cơ bản: {e}")
    logger.warning("Sử dụng các chức năng mới mà không có API Binance và Data Processor")

class ComprehensiveBacktester:
    """Thực hiện backtest toàn diện với tất cả tính năng nâng cao"""
    
    def __init__(self, config: Dict = None):
        """
        Khởi tạo backtester
        
        Args:
            config (Dict): Cấu hình backtest
        """
        self.config = config or {
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_balance": 10000.0,
            "leverage": 1,
            "risk_percentage": 1.0,
            "use_trailing_stop": True,
            "trailing_stop_callback": 0.5,  # 50% của profit
            "take_profit_ratio": 2.0,       # 2x stop loss
            "use_market_regime": True,
            "use_time_optimization": True,
            "use_monte_carlo": True,
            "use_pythagorean_sizer": True,
            "data_source": "synthetic",   # 'binance' hoặc 'synthetic'
            "log_trades": True
        }
        
        # Khởi tạo các biến trạng thái
        self.price_data = None
        self.trades = []
        self.balance_history = []
        self.regime_history = []
        self.current_position = None
        self.current_balance = self.config["initial_balance"]
        self.max_balance = self.current_balance
        self.min_balance = self.current_balance
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
        
        # Khởi tạo các thành phần
        logger.info("Khởi tạo các thành phần cho backtest...")
        
        # Market Regime Detector
        self.regime_detector = FractalMarketRegimeDetector(
            lookback_periods=100
        )
        
        # Position Sizer
        self.pythag_sizer = PythagoreanPositionSizer(
            trade_history=[],
            account_balance=self.current_balance,
            risk_percentage=self.config["risk_percentage"]
        )
        
        # Monte Carlo Risk Analyzer
        self.mc_analyzer = MonteCarloRiskAnalyzer(
            trade_history=[],
            default_risk=self.config["risk_percentage"]
        )
        
        # Trading Time Optimizer
        self.time_optimizer = TradingTimeOptimizer(
            trade_history=[],
            time_segments=24
        )
        
        # Nếu sử dụng API Binance
        self.api = None
        self.data_processor = None
        
        if hasattr(self, 'BinanceAPI') and self.config["data_source"] == "binance":
            try:
                self.api = BinanceAPI(testnet=True)
                self.data_processor = DataProcessor(self.api)
                logger.info("Đã khởi tạo Binance API và Data Processor")
            except Exception as e:
                logger.error(f"Không thể khởi tạo Binance API: {e}")
                self.config["data_source"] = "synthetic"
        
        logger.info(f"Đã khởi tạo ComprehensiveBacktester với cấu hình: {json.dumps(self.config, indent=2)}")
    
    def load_data(self):
        """
        Tải dữ liệu cho backtest từ API hoặc tạo dữ liệu giả lập
        
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        if self.config["data_source"] == "binance" and self.api and self.data_processor:
            try:
                logger.info(f"Tải dữ liệu từ Binance: {self.config['symbol']} {self.config['timeframe']}")
                
                # Parse dates
                start_date = datetime.strptime(self.config["start_date"], "%Y-%m-%d")
                end_date = datetime.strptime(self.config["end_date"], "%Y-%m-%d")
                
                # Download data
                self.price_data = self.data_processor.download_historical_data(
                    symbol=self.config["symbol"],
                    interval=self.config["timeframe"],
                    start_time=self.config["start_date"],
                    end_time=self.config["end_date"],
                    save_to_file=True
                )
                
                # Add indicators
                self.price_data = self.data_processor.add_indicators(
                    df=self.price_data,
                    indicators=["rsi", "macd", "bbands", "ema", "atr", "stochastic", "adx"]
                )
                
                logger.info(f"Đã tải {len(self.price_data)} candlesticks từ Binance")
                return True
                
            except Exception as e:
                logger.error(f"Lỗi khi tải dữ liệu từ Binance: {e}")
                logger.info("Chuyển sang sử dụng dữ liệu giả lập")
                self.config["data_source"] = "synthetic"
        
        # Sử dụng dữ liệu giả lập
        if self.config["data_source"] == "synthetic":
            logger.info("Tạo dữ liệu giả lập...")
            
            # Parse dates
            start_date = datetime.strptime(self.config["start_date"], "%Y-%m-%d")
            end_date = datetime.strptime(self.config["end_date"], "%Y-%m-%d")
            
            # Tạo index các ngày
            date_range = pd.date_range(start=start_date, end=end_date, freq=self.config["timeframe"])
            
            # Tạo dữ liệu giá
            prices = np.zeros(len(date_range))
            prices[0] = 50000  # Giá ban đầu $50k
            
            # Thêm xu hướng và nhiễu
            for i in range(1, len(prices)):
                # Thay đổi chế độ thị trường theo từng phần
                segment = i // (len(prices) // 5)  # Chia thành 5 phần
                
                if segment == 0:  # Trending up
                    trend = 0.05
                    volatility = 0.5
                elif segment == 1:  # Ranging
                    trend = 0.0
                    volatility = 0.3
                elif segment == 2:  # Trending down
                    trend = -0.05
                    volatility = 0.5
                elif segment == 3:  # Volatile
                    trend = -0.01
                    volatility = 1.2
                else:  # Quiet
                    trend = 0.01
                    volatility = 0.2
                    
                # Tạo giá
                price_change = np.random.normal(trend, volatility)
                prices[i] = max(1, prices[i-1] * (1 + price_change / 100))
            
            # Tạo DataFrame
            self.price_data = pd.DataFrame(index=date_range)
            self.price_data['close'] = prices
            
            # Tạo OHLCV
            self.price_data['open'] = self.price_data['close'].shift(1)
            self.price_data.loc[self.price_data.index[0], 'open'] = self.price_data['close'].iloc[0] * 0.99
            
            # High & Low - thêm nhiễu ngẫu nhiên
            random_factors = np.random.uniform(0.001, 0.01, len(self.price_data))
            self.price_data['high'] = self.price_data['close'] * (1 + random_factors)
            self.price_data['low'] = self.price_data['close'] * (1 - random_factors)
            
            # Thêm volume
            self.price_data['volume'] = np.random.uniform(100, 1000, len(self.price_data)) * self.price_data['close'] / 1000
            
            # Thêm các indicator
            self._add_indicators()
            
            logger.info(f"Đã tạo {len(self.price_data)} candlesticks giả lập")
            return True
            
        return False
    
    def _add_indicators(self):
        """Thêm các indicator vào dữ liệu giá"""
        # RSI
        delta = self.price_data['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        
        rs = avg_gain / avg_loss
        self.price_data['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        self.price_data['bb_middle'] = self.price_data['close'].rolling(window=20).mean()
        std = self.price_data['close'].rolling(window=20).std()
        self.price_data['bb_upper'] = self.price_data['bb_middle'] + 2 * std
        self.price_data['bb_lower'] = self.price_data['bb_middle'] - 2 * std
        
        # EMA
        self.price_data['ema9'] = self.price_data['close'].ewm(span=9, adjust=False).mean()
        self.price_data['ema21'] = self.price_data['close'].ewm(span=21, adjust=False).mean()
        self.price_data['ema50'] = self.price_data['close'].ewm(span=50, adjust=False).mean()
        self.price_data['ema200'] = self.price_data['close'].ewm(span=200, adjust=False).mean()
        
        # MACD
        self.price_data['macd_fast'] = self.price_data['close'].ewm(span=12, adjust=False).mean()
        self.price_data['macd_slow'] = self.price_data['close'].ewm(span=26, adjust=False).mean()
        self.price_data['macd'] = self.price_data['macd_fast'] - self.price_data['macd_slow']
        self.price_data['macd_signal'] = self.price_data['macd'].ewm(span=9, adjust=False).mean()
        self.price_data['macd_hist'] = self.price_data['macd'] - self.price_data['macd_signal']
        
        # ATR
        high_low = self.price_data['high'] - self.price_data['low']
        high_close = abs(self.price_data['high'] - self.price_data['close'].shift())
        low_close = abs(self.price_data['low'] - self.price_data['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        self.price_data['atr'] = tr.rolling(window=14).mean()
        
        # Stochastic
        low_14 = self.price_data['low'].rolling(window=14).min()
        high_14 = self.price_data['high'].rolling(window=14).max()
        
        self.price_data['stoch_k'] = 100 * ((self.price_data['close'] - low_14) / (high_14 - low_14))
        self.price_data['stoch_d'] = self.price_data['stoch_k'].rolling(window=3).mean()
        
        # ADX (Simplified for backtest)
        self.price_data['adx'] = abs(self.price_data['ema9'] - self.price_data['ema21']) / self.price_data['ema21'] * 100
    
    def _generate_signal(self, idx: int) -> str:
        """
        Tạo tín hiệu giao dịch dựa trên các indicator
        
        Args:
            idx (int): Chỉ số của candlestick trong price_data
            
        Returns:
            str: Tín hiệu giao dịch ('buy', 'sell', 'neutral', 'close')
        """
        if idx < 20:  # Cần đủ dữ liệu cho các indicator
            return 'neutral'
            
        # Lấy dữ liệu gần đây
        recent_data = self.price_data.iloc[:idx+1].copy()
        
        # Sử dụng Market Regime Detector
        if self.config["use_market_regime"] and len(recent_data) > 100:
            regime_result = self.regime_detector.detect_regime(recent_data)
            regime = regime_result['regime']
            
            # Lưu chế độ thị trường vào lịch sử
            self.regime_history.append({
                'time': recent_data.index[-1],
                'regime': regime,
                'confidence': regime_result['confidence']
            })
            
            # Lấy chiến lược phù hợp với chế độ thị trường
            strategies = self.regime_detector.get_suitable_strategies()
            
            # Tạo tín hiệu dựa trên chiến lược phù hợp
            signal = 'neutral'
            
            if regime == 'trending':
                # Kết hợp EMA Cross và MACD
                ema_cross = recent_data['ema9'].iloc[-1] > recent_data['ema21'].iloc[-1]
                macd_hist = recent_data['macd_hist'].iloc[-1]
                
                if ema_cross and macd_hist > 0:
                    signal = 'buy'
                elif not ema_cross and macd_hist < 0:
                    signal = 'sell'
                    
            elif regime == 'ranging':
                # Kết hợp RSI và Bollinger Bands
                rsi = recent_data['rsi'].iloc[-1]
                close = recent_data['close'].iloc[-1]
                bb_upper = recent_data['bb_upper'].iloc[-1]
                bb_lower = recent_data['bb_lower'].iloc[-1]
                
                if rsi < 30 and close < bb_lower:
                    signal = 'buy'
                elif rsi > 70 and close > bb_upper:
                    signal = 'sell'
                    
            elif regime == 'volatile':
                # Kết hợp Bollinger Bands và ATR
                close = recent_data['close'].iloc[-1]
                bb_upper = recent_data['bb_upper'].iloc[-1]
                bb_lower = recent_data['bb_lower'].iloc[-1]
                
                if close < bb_lower * 0.99:  # Breakout dưới BB
                    signal = 'buy'
                elif close > bb_upper * 1.01:  # Breakout trên BB
                    signal = 'sell'
                    
            elif regime == 'quiet':
                # Kết hợp Bollinger Bands và RSI
                rsi = recent_data['rsi'].iloc[-1]
                close = recent_data['close'].iloc[-1]
                bb_middle = recent_data['bb_middle'].iloc[-1]
                
                if rsi < 40 and close < bb_middle * 0.99:
                    signal = 'buy'
                elif rsi > 60 and close > bb_middle * 1.01:
                    signal = 'sell'
                    
            else:  # choppy hoặc unknown
                # Sử dụng RSI một cách cẩn thận
                rsi = recent_data['rsi'].iloc[-1]
                
                if rsi < 20:
                    signal = 'buy'
                elif rsi > 80:
                    signal = 'sell'
        
        else:
            # Chiến lược mặc định: kết hợp RSI và MACD
            rsi = recent_data['rsi'].iloc[-1]
            macd_hist = recent_data['macd_hist'].iloc[-1]
            
            if rsi < 30 and macd_hist > 0:
                signal = 'buy'
            elif rsi > 70 and macd_hist < 0:
                signal = 'sell'
            else:
                signal = 'neutral'
        
        # Kiểm tra nếu đang có vị thế
        if self.current_position:
            # Đảo tín hiệu để đóng vị thế
            if (self.current_position['side'] == 'buy' and signal == 'sell') or \
               (self.current_position['side'] == 'sell' and signal == 'buy'):
                signal = 'close'
        
        return signal
    
    def _check_trading_time(self, timestamp: datetime) -> bool:
        """
        Kiểm tra xem có nên giao dịch vào thời điểm hiện tại không
        
        Args:
            timestamp (datetime): Thời gian kiểm tra
            
        Returns:
            bool: True nếu nên giao dịch, False nếu không
        """
        if not self.config["use_time_optimization"]:
            return True
            
        if len(self.trades) < 10:  # Chưa đủ dữ liệu để tối ưu
            return True
            
        # Cập nhật dữ liệu cho optimizer
        self.time_optimizer.trade_history = self.trades
        self.time_optimizer.update_performance_analysis()
        
        # Kiểm tra thời gian
        should_trade, reason = self.time_optimizer.should_trade_now(timestamp)
        
        if not should_trade:
            logger.info(f"Bỏ qua giao dịch tại {timestamp}: {reason}")
            
        return should_trade
    
    def _calculate_position_size(self, price: float, stop_loss: float) -> float:
        """
        Tính toán kích thước vị thế
        
        Args:
            price (float): Giá vào lệnh
            stop_loss (float): Giá stop loss
            
        Returns:
            float: Kích thước vị thế (đơn vị)
        """
        # Tính toán % rủi ro
        risk_percentage = self.config["risk_percentage"]
        
        # Điều chỉnh % rủi ro theo Monte Carlo nếu được kích hoạt
        if self.config["use_monte_carlo"] and len(self.trades) >= 30:
            # Cập nhật lịch sử giao dịch
            self.mc_analyzer.trade_history = self.trades
            
            # Phân tích Monte Carlo
            mc_risk = self.mc_analyzer.analyze(
                confidence_level=0.95,
                simulations=1000,
                sequence_length=20,
                max_risk_limit=self.config["risk_percentage"] * 2
            )
            
            # Sử dụng % rủi ro từ Monte Carlo
            risk_percentage = mc_risk
            logger.info(f"Điều chỉnh % rủi ro theo Monte Carlo: {risk_percentage:.2f}%")
        
        # Điều chỉnh % rủi ro theo Market Regime nếu được kích hoạt
        if self.config["use_market_regime"] and self.regime_history:
            # Lấy chế độ thị trường gần nhất
            latest_regime = self.regime_history[-1]['regime']
            
            # Lấy hệ số điều chỉnh
            regime_adjustment = self.regime_detector.get_risk_adjustment()
            
            # Điều chỉnh % rủi ro
            risk_percentage *= regime_adjustment
            logger.info(f"Điều chỉnh % rủi ro theo chế độ thị trường ({latest_regime}): {risk_percentage:.2f}%")
        
        # Điều chỉnh % rủi ro theo thời gian nếu được kích hoạt
        if self.config["use_time_optimization"] and len(self.trades) >= 10:
            # Cập nhật lịch sử giao dịch
            self.time_optimizer.trade_history = self.trades
            
            # Lấy hệ số điều chỉnh theo thời gian
            timestamp = self.price_data.index[-1]
            time_adjustment = self.time_optimizer.get_risk_adjustment(timestamp)
            
            # Điều chỉnh % rủi ro
            risk_percentage *= time_adjustment
            logger.info(f"Điều chỉnh % rủi ro theo thời gian: {risk_percentage:.2f}%")
        
        # Tính kích thước vị thế
        if self.config["use_pythagorean_sizer"]:
            # Cập nhật lịch sử giao dịch và số dư
            self.pythag_sizer.trade_history = self.trades
            self.pythag_sizer.account_balance = self.current_balance
            self.pythag_sizer.max_risk_percentage = risk_percentage
            
            # Tính kích thước vị thế sử dụng PythagoreanPositionSizer
            position_size = self.pythag_sizer.calculate_position_size(
                current_price=price,
                account_balance=self.current_balance,
                entry_price=price,
                stop_loss_price=stop_loss,
                leverage=self.config["leverage"]
            )
            
            logger.info(f"Kích thước vị thế (Pythagorean): {position_size:.2f} USD")
            
        else:
            # Tính toán vị thế đơn giản
            risk_amount = self.current_balance * (risk_percentage / 100)
            stop_loss_pct = abs(price - stop_loss) / price
            position_size = risk_amount / (price * stop_loss_pct)
            
            logger.info(f"Kích thước vị thế (Đơn giản): {position_size:.2f} đơn vị")
        
        # Giới hạn kích thước vị thế
        max_position = self.current_balance * self.config["leverage"] / price
        position_size = min(position_size, max_position)
        
        return position_size
    
    def _execute_trade(self, timestamp: datetime, signal: str, price: float):
        """
        Thực hiện giao dịch
        
        Args:
            timestamp (datetime): Thời gian giao dịch
            signal (str): Tín hiệu giao dịch ('buy', 'sell', 'close')
            price (float): Giá thực hiện
        """
        # Nếu tín hiệu là đóng vị thế
        if signal == 'close' and self.current_position:
            # Tính P&L
            if self.current_position['side'] == 'buy':
                pnl = (price - self.current_position['entry_price']) * self.current_position['size']
            else:  # 'sell'
                pnl = (self.current_position['entry_price'] - price) * self.current_position['size']
                
            pnl_pct = pnl / (self.current_position['entry_price'] * self.current_position['size']) * 100
            
            # Cập nhật số dư
            self.current_balance += pnl
            
            # Cập nhật số liệu thống kê
            if pnl > 0:
                self.win_count += 1
            else:
                self.loss_count += 1
                
            # Cập nhật số dư tối đa/tối thiểu
            self.max_balance = max(self.max_balance, self.current_balance)
            self.min_balance = min(self.min_balance, self.current_balance)
            
            # Ghi log giao dịch
            trade = {
                'id': self.trade_count,
                'symbol': self.config["symbol"],
                'side': self.current_position['side'],
                'entry_time': self.current_position['entry_time'],
                'entry_price': self.current_position['entry_price'],
                'exit_time': timestamp,
                'exit_price': price,
                'size': self.current_position['size'],
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'balance_after': self.current_balance,
                'stop_loss': self.current_position['stop_loss'],
                'take_profit': self.current_position['take_profit'],
                'exit_reason': 'signal'
            }
            
            self.trades.append(trade)
            self.trade_count += 1
            
            logger.info(f"Đóng vị thế: {self.current_position['side']} | P&L: {pnl:.2f} USD ({pnl_pct:.2f}%)")
            
            # Reset vị thế hiện tại
            self.current_position = None
            
        # Nếu tín hiệu là mở vị thế mới và không có vị thế nào hiện tại
        elif signal in ['buy', 'sell'] and not self.current_position:
            # Kiểm tra thời gian giao dịch
            if not self._check_trading_time(timestamp):
                return
                
            # Tính stop loss
            atr = self.price_data['atr'].iloc[-1]
            
            if signal == 'buy':
                stop_loss = price - 2 * atr
            else:  # 'sell'
                stop_loss = price + 2 * atr
                
            # Tính take profit
            if signal == 'buy':
                take_profit = price + (price - stop_loss) * self.config["take_profit_ratio"]
            else:  # 'sell'
                take_profit = price - (stop_loss - price) * self.config["take_profit_ratio"]
                
            # Tính kích thước vị thế
            size = self._calculate_position_size(price, stop_loss)
            
            # Mở vị thế mới
            self.current_position = {
                'side': signal,
                'entry_time': timestamp,
                'entry_price': price,
                'size': size,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'trailing_stop': None if not self.config["use_trailing_stop"] else stop_loss
            }
            
            logger.info(f"Mở vị thế: {signal} | Giá: {price:.2f} | Size: {size:.4f} | SL: {stop_loss:.2f} | TP: {take_profit:.2f}")
    
    def _update_position(self, timestamp: datetime, row: pd.Series):
        """
        Cập nhật vị thế (kiểm tra stop loss, take profit, trailing stop)
        
        Args:
            timestamp (datetime): Thời gian hiện tại
            row (pd.Series): Dữ liệu candlestick hiện tại
        """
        if not self.current_position:
            return
            
        # Lấy giá hiện tại
        price_high = row['high']
        price_low = row['low']
        price_close = row['close']
        
        # Kiểm tra trailing stop
        if self.config["use_trailing_stop"] and self.current_position['trailing_stop'] is not None:
            # Mua: trailing stop tăng theo giá
            if self.current_position['side'] == 'buy':
                # Giá đã tăng đủ để kích hoạt trailing stop
                activation_price = self.current_position['entry_price'] + (self.current_position['entry_price'] - self.current_position['stop_loss'])
                
                if price_high >= activation_price:
                    # Tính mức trailing stop mới
                    new_stop = price_high * (1 - self.config["trailing_stop_callback"] / 100)
                    
                    # Chỉ cập nhật nếu stop mới cao hơn stop cũ
                    if new_stop > self.current_position['trailing_stop']:
                        self.current_position['trailing_stop'] = new_stop
                        logger.info(f"Cập nhật trailing stop: {new_stop:.2f}")
            
            # Bán: trailing stop giảm theo giá
            else:  # 'sell'
                # Giá đã giảm đủ để kích hoạt trailing stop
                activation_price = self.current_position['entry_price'] - (self.current_position['stop_loss'] - self.current_position['entry_price'])
                
                if price_low <= activation_price:
                    # Tính mức trailing stop mới
                    new_stop = price_low * (1 + self.config["trailing_stop_callback"] / 100)
                    
                    # Chỉ cập nhật nếu stop mới thấp hơn stop cũ
                    if new_stop < self.current_position['trailing_stop']:
                        self.current_position['trailing_stop'] = new_stop
                        logger.info(f"Cập nhật trailing stop: {new_stop:.2f}")
        
        # Kiểm tra stop loss
        if self.current_position['side'] == 'buy':
            stop_level = self.current_position['trailing_stop'] if self.config["use_trailing_stop"] else self.current_position['stop_loss']
            if price_low <= stop_level:
                # Thực hiện stop loss
                self._close_position(timestamp, stop_level, 'stop_loss')
                return
                
        else:  # 'sell'
            stop_level = self.current_position['trailing_stop'] if self.config["use_trailing_stop"] else self.current_position['stop_loss']
            if price_high >= stop_level:
                # Thực hiện stop loss
                self._close_position(timestamp, stop_level, 'stop_loss')
                return
        
        # Kiểm tra take profit
        if self.current_position['side'] == 'buy':
            if price_high >= self.current_position['take_profit']:
                # Thực hiện take profit
                self._close_position(timestamp, self.current_position['take_profit'], 'take_profit')
                return
                
        else:  # 'sell'
            if price_low <= self.current_position['take_profit']:
                # Thực hiện take profit
                self._close_position(timestamp, self.current_position['take_profit'], 'take_profit')
                return
    
    def _close_position(self, timestamp: datetime, price: float, reason: str):
        """
        Đóng vị thế với giá và lý do cụ thể
        
        Args:
            timestamp (datetime): Thời gian đóng vị thế
            price (float): Giá đóng vị thế
            reason (str): Lý do đóng vị thế
        """
        if not self.current_position:
            return
            
        # Tính P&L
        if self.current_position['side'] == 'buy':
            pnl = (price - self.current_position['entry_price']) * self.current_position['size']
        else:  # 'sell'
            pnl = (self.current_position['entry_price'] - price) * self.current_position['size']
            
        pnl_pct = pnl / (self.current_position['entry_price'] * self.current_position['size']) * 100
        
        # Cập nhật số dư
        self.current_balance += pnl
        
        # Cập nhật số liệu thống kê
        if pnl > 0:
            self.win_count += 1
        else:
            self.loss_count += 1
            
        # Cập nhật số dư tối đa/tối thiểu
        self.max_balance = max(self.max_balance, self.current_balance)
        self.min_balance = min(self.min_balance, self.current_balance)
        
        # Ghi log giao dịch
        trade = {
            'id': self.trade_count,
            'symbol': self.config["symbol"],
            'side': self.current_position['side'],
            'entry_time': self.current_position['entry_time'],
            'entry_price': self.current_position['entry_price'],
            'exit_time': timestamp,
            'exit_price': price,
            'size': self.current_position['size'],
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'balance_after': self.current_balance,
            'stop_loss': self.current_position['stop_loss'],
            'take_profit': self.current_position['take_profit'],
            'exit_reason': reason
        }
        
        self.trades.append(trade)
        self.trade_count += 1
        
        logger.info(f"Đóng vị thế ({reason}): {self.current_position['side']} | P&L: {pnl:.2f} USD ({pnl_pct:.2f}%)")
        
        # Reset vị thế hiện tại
        self.current_position = None
    
    def run(self):
        """
        Chạy backtest
        
        Returns:
            Dict: Kết quả backtest
        """
        # Tải dữ liệu
        if not self.load_data():
            logger.error("Không thể tải dữ liệu. Dừng backtest.")
            return None
            
        # Khởi tạo số dư
        self.current_balance = self.config["initial_balance"]
        self.balance_history = [{
            'timestamp': self.price_data.index[0],
            'balance': self.current_balance
        }]
        
        # Reset các biến khác
        self.trades = []
        self.regime_history = []
        self.current_position = None
        self.max_balance = self.current_balance
        self.min_balance = self.current_balance
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
        
        # Log bắt đầu backtest
        logger.info(f"Bắt đầu backtest với {len(self.price_data)} candlesticks")
        logger.info(f"Thời gian: {self.price_data.index[0]} đến {self.price_data.index[-1]}")
        
        # Lặp qua từng candlestick
        for i in range(len(self.price_data)):
            timestamp = self.price_data.index[i]
            row = self.price_data.iloc[i]
            
            # Cập nhật vị thế hiện tại nếu có
            if self.current_position:
                self._update_position(timestamp, row)
                
            # Chỉ tạo tín hiệu nếu không có vị thế hoặc cần đóng vị thế
            if not self.current_position or i % 5 == 0:  # Kiểm tra mỗi 5 candle để tối ưu hiệu suất
                signal = self._generate_signal(i)
                
                # Thực hiện giao dịch
                self._execute_trade(timestamp, signal, row['close'])
            
            # Lưu số dư vào lịch sử
            if i % 10 == 0 or i == len(self.price_data) - 1:  # Mỗi 10 candle hoặc candle cuối cùng
                self.balance_history.append({
                    'timestamp': timestamp,
                    'balance': self.current_balance
                })
                
        # Đóng vị thế cuối cùng nếu còn
        if self.current_position:
            last_price = self.price_data['close'].iloc[-1]
            self._close_position(self.price_data.index[-1], last_price, 'end_of_backtest')
            
        # Tính toán kết quả
        results = self._calculate_results()
        
        # Vẽ biểu đồ
        self._plot_results()
        
        return results
    
    def _calculate_results(self) -> Dict:
        """
        Tính toán kết quả backtest
        
        Returns:
            Dict: Kết quả backtest
        """
        # Số liệu cơ bản
        initial_balance = self.config["initial_balance"]
        final_balance = self.current_balance
        profit = final_balance - initial_balance
        profit_pct = profit / initial_balance * 100
        
        # Win rate
        total_trades = len(self.trades)
        win_rate = self.win_count / total_trades if total_trades > 0 else 0
        
        # Drawdown
        max_drawdown_pct = (1 - self.min_balance / self.max_balance) * 100 if self.max_balance > 0 else 0
        
        # Thống kê giao dịch
        if total_trades > 0:
            winning_trades = [trade for trade in self.trades if trade['pnl'] > 0]
            losing_trades = [trade for trade in self.trades if trade['pnl'] <= 0]
            
            avg_profit = sum(trade['pnl'] for trade in winning_trades) / len(winning_trades) if winning_trades else 0
            avg_loss = sum(trade['pnl'] for trade in losing_trades) / len(losing_trades) if losing_trades else 0
            avg_profit_pct = sum(trade['pnl_pct'] for trade in winning_trades) / len(winning_trades) if winning_trades else 0
            avg_loss_pct = sum(trade['pnl_pct'] for trade in losing_trades) / len(losing_trades) if losing_trades else 0
            
            profit_factor = abs(sum(trade['pnl'] for trade in winning_trades) / sum(trade['pnl'] for trade in losing_trades)) if sum(trade['pnl'] for trade in losing_trades) != 0 else float('inf')
            
            expectancy = (win_rate * avg_profit + (1 - win_rate) * avg_loss) if (win_rate > 0 and avg_profit != 0) or (win_rate < 1 and avg_loss != 0) else 0
            expectancy_pct = (win_rate * avg_profit_pct + (1 - win_rate) * avg_loss_pct) if (win_rate > 0 and avg_profit_pct != 0) or (win_rate < 1 and avg_loss_pct != 0) else 0
            
            # Phân tích lý do đóng vị thế
            exit_reasons = {}
            for trade in self.trades:
                reason = trade['exit_reason']
                if reason in exit_reasons:
                    exit_reasons[reason] += 1
                else:
                    exit_reasons[reason] = 1
        else:
            avg_profit = 0
            avg_loss = 0
            avg_profit_pct = 0
            avg_loss_pct = 0
            profit_factor = 0
            expectancy = 0
            expectancy_pct = 0
            exit_reasons = {}
        
        # Phân tích chế độ thị trường
        regime_stats = {}
        if self.regime_history:
            for regime_info in self.regime_history:
                regime = regime_info['regime']
                if regime in regime_stats:
                    regime_stats[regime] += 1
                else:
                    regime_stats[regime] = 1
        
        # Tạo kết quả
        results = {
            'config': self.config,
            'summary': {
                'initial_balance': initial_balance,
                'final_balance': final_balance,
                'profit': profit,
                'profit_pct': profit_pct,
                'max_balance': self.max_balance,
                'min_balance': self.min_balance,
                'max_drawdown_pct': max_drawdown_pct,
                'total_trades': total_trades,
                'winning_trades': self.win_count,
                'losing_trades': self.loss_count,
                'win_rate': win_rate,
                'avg_profit': avg_profit,
                'avg_loss': avg_loss,
                'avg_profit_pct': avg_profit_pct,
                'avg_loss_pct': avg_loss_pct,
                'profit_factor': profit_factor,
                'expectancy': expectancy,
                'expectancy_pct': expectancy_pct,
                'start_date': self.price_data.index[0],
                'end_date': self.price_data.index[-1]
            },
            'trades': self.trades,
            'balance_history': self.balance_history,
            'exit_reasons': exit_reasons,
            'regime_stats': regime_stats
        }
        
        # Log kết quả
        logger.info("\n" + "="*50)
        logger.info("KẾT QUẢ BACKTEST")
        logger.info("="*50)
        logger.info(f"Số dư ban đầu: ${initial_balance:.2f}")
        logger.info(f"Số dư cuối cùng: ${final_balance:.2f}")
        logger.info(f"Lợi nhuận: ${profit:.2f} ({profit_pct:.2f}%)")
        logger.info(f"Số dư tối đa: ${self.max_balance:.2f}")
        logger.info(f"Số dư tối thiểu: ${self.min_balance:.2f}")
        logger.info(f"Drawdown tối đa: {max_drawdown_pct:.2f}%")
        logger.info(f"Tổng số giao dịch: {total_trades}")
        logger.info(f"Số giao dịch thắng: {self.win_count}")
        logger.info(f"Số giao dịch thua: {self.loss_count}")
        logger.info(f"Win rate: {win_rate:.2f}")
        logger.info(f"Profit factor: {profit_factor:.2f}")
        logger.info(f"Expectancy: ${expectancy:.2f} ({expectancy_pct:.2f}%)")
        logger.info("Lý do đóng vị thế:")
        for reason, count in exit_reasons.items():
            logger.info(f"  - {reason}: {count}")
        logger.info("Chế độ thị trường:")
        for regime, count in regime_stats.items():
            logger.info(f"  - {regime}: {count}")
        logger.info("="*50)
        
        # Lưu kết quả vào file
        result_file = f"backtest_results/{self.config['symbol']}_{self.config['timeframe']}_backtest_results.json"
        with open(result_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
            
        logger.info(f"Đã lưu kết quả vào {result_file}")
        
        return results
    
    def _plot_results(self):
        """Vẽ biểu đồ kết quả backtest"""
        try:
            # Tạo figure với 4 subplot
            fig = plt.figure(figsize=(15, 12))
            
            # 1. Biểu đồ giá và vị thế
            ax1 = plt.subplot2grid((3, 1), (0, 0), rowspan=1)
            
            # Vẽ giá
            ax1.plot(self.price_data.index, self.price_data['close'], color='blue', alpha=0.5)
            
            # Vẽ các điểm vào lệnh và thoát lệnh
            buy_entries = [trade['entry_time'] for trade in self.trades if trade['side'] == 'buy']
            buy_prices = [trade['entry_price'] for trade in self.trades if trade['side'] == 'buy']
            
            sell_entries = [trade['entry_time'] for trade in self.trades if trade['side'] == 'sell']
            sell_prices = [trade['entry_price'] for trade in self.trades if trade['side'] == 'sell']
            
            exits = [trade['exit_time'] for trade in self.trades]
            exit_prices = [trade['exit_price'] for trade in self.trades]
            
            if buy_entries:
                ax1.scatter(buy_entries, buy_prices, color='green', marker='^', s=100, label='Buy')
            
            if sell_entries:
                ax1.scatter(sell_entries, sell_prices, color='red', marker='v', s=100, label='Sell')
            
            if exits:
                ax1.scatter(exits, exit_prices, color='black', marker='x', s=70, label='Exit')
            
            ax1.set_title('Giá và Vị thế')
            ax1.set_ylabel('Giá')
            ax1.grid(True)
            ax1.legend()
            
            # 2. Biểu đồ số dư
            ax2 = plt.subplot2grid((3, 1), (1, 0), rowspan=1)
            
            if self.balance_history:
                timestamps = [entry['timestamp'] for entry in self.balance_history]
                balances = [entry['balance'] for entry in self.balance_history]
                
                ax2.plot(timestamps, balances, color='green')
                ax2.axhline(y=self.config["initial_balance"], color='red', linestyle='--')
                
                ax2.set_title('Đường cong Equity')
                ax2.set_ylabel('Số dư')
                ax2.grid(True)
            
            # 3. Biểu đồ Win/Loss và phân bố P&L
            ax3 = plt.subplot2grid((3, 1), (2, 0), rowspan=1)
            
            if self.trades:
                # Phân bố P&L
                pnl_values = [trade['pnl_pct'] for trade in self.trades]
                
                ax3.hist(pnl_values, bins=30, alpha=0.7, color='blue')
                ax3.axvline(x=0, color='red', linestyle='--')
                
                ax3.set_title('Phân bố P&L (%)')
                ax3.set_xlabel('P&L (%)')
                ax3.set_ylabel('Số lượng')
                ax3.grid(True)
            
            plt.tight_layout()
            
            # 4. Biểu đồ bổ sung: chế độ thị trường
            if self.regime_history:
                fig2 = plt.figure(figsize=(15, 5))
                ax4 = fig2.add_subplot(111)
                
                timestamps = [entry['time'] for entry in self.regime_history]
                regimes = [entry['regime'] for entry in self.regime_history]
                confidences = [entry['confidence'] for entry in self.regime_history]
                
                # Chuyển đổi chế độ thành số
                regime_mapping = {
                    'trending': 5,
                    'ranging': 4,
                    'volatile': 3,
                    'quiet': 2,
                    'choppy': 1,
                    'unknown': 0
                }
                
                regime_values = [regime_mapping.get(r, 0) for r in regimes]
                
                # Vẽ colormap
                cmap = plt.cm.get_cmap('viridis', len(regime_mapping))
                sc = ax4.scatter(timestamps, regime_values, c=regime_values, cmap=cmap, s=50, alpha=0.7)
                
                # Tạo colorbar
                cbar = plt.colorbar(sc, ticks=list(regime_mapping.values()))
                cbar.set_ticklabels(list(regime_mapping.keys()))
                
                ax4.set_yticks(list(regime_mapping.values()))
                ax4.set_yticklabels(list(regime_mapping.keys()))
                
                ax4.set_title('Chế độ thị trường')
                ax4.set_xlabel('Thời gian')
                ax4.grid(True)
                
                plt.tight_layout()
                plt.savefig(f"backtest_charts/{self.config['symbol']}_{self.config['timeframe']}_market_regimes.png")
            
            # Lưu biểu đồ
            plt.figure(fig.number)
            plt.savefig(f"backtest_charts/{self.config['symbol']}_{self.config['timeframe']}_backtest_results.png")
            
            logger.info(f"Đã lưu biểu đồ vào backtest_charts/{self.config['symbol']}_{self.config['timeframe']}_backtest_results.png")
            
        except Exception as e:
            logger.error(f"Lỗi khi vẽ biểu đồ: {e}")
            logger.error(traceback.format_exc())
    
    def analyze_results(self):
        """Phân tích chi tiết kết quả backtest"""
        if not self.trades:
            logger.warning("Không có dữ liệu giao dịch để phân tích")
            return
        
        # 1. Phân tích giao dịch theo chế độ thị trường
        if self.regime_history:
            logger.info("\n" + "="*50)
            logger.info("PHÂN TÍCH THEO CHẾ ĐỘ THỊ TRƯỜNG")
            logger.info("="*50)
            
            # Tạo mapping của thời gian -> chế độ
            regime_map = {}
            for entry in self.regime_history:
                regime_map[entry['time']] = entry['regime']
            
            # Gán chế độ thị trường cho từng giao dịch
            for trade in self.trades:
                # Tìm chế độ gần nhất với thời gian vào lệnh
                closest_time = min(regime_map.keys(), key=lambda x: abs((x - trade['entry_time']).total_seconds()))
                trade['market_regime'] = regime_map[closest_time]
            
            # Phân tích theo chế độ
            regime_stats = {}
            for regime in set(trade['market_regime'] for trade in self.trades):
                regime_trades = [trade for trade in self.trades if trade['market_regime'] == regime]
                
                win_count = sum(1 for trade in regime_trades if trade['pnl'] > 0)
                loss_count = len(regime_trades) - win_count
                
                win_rate = win_count / len(regime_trades) if len(regime_trades) > 0 else 0
                
                avg_profit = sum(trade['pnl'] for trade in regime_trades if trade['pnl'] > 0) / win_count if win_count > 0 else 0
                avg_loss = sum(trade['pnl'] for trade in regime_trades if trade['pnl'] <= 0) / loss_count if loss_count > 0 else 0
                
                profit_factor = abs(sum(trade['pnl'] for trade in regime_trades if trade['pnl'] > 0) / 
                                   sum(trade['pnl'] for trade in regime_trades if trade['pnl'] <= 0)) if sum(trade['pnl'] for trade in regime_trades if trade['pnl'] <= 0) != 0 else float('inf')
                
                regime_stats[regime] = {
                    'trades': len(regime_trades),
                    'win_count': win_count,
                    'loss_count': loss_count,
                    'win_rate': win_rate,
                    'avg_profit': avg_profit,
                    'avg_loss': avg_loss,
                    'profit_factor': profit_factor
                }
            
            # In kết quả
            for regime, stats in regime_stats.items():
                logger.info(f"Chế độ: {regime}")
                logger.info(f"  - Số giao dịch: {stats['trades']}")
                logger.info(f"  - Win rate: {stats['win_rate']:.2f}")
                logger.info(f"  - Avg profit: ${stats['avg_profit']:.2f}")
                logger.info(f"  - Avg loss: ${stats['avg_loss']:.2f}")
                logger.info(f"  - Profit factor: {stats['profit_factor']:.2f}")
                logger.info("---")
        
        # 2. Phân tích theo thời gian trong ngày
        logger.info("\n" + "="*50)
        logger.info("PHÂN TÍCH THEO THỜI GIAN")
        logger.info("="*50)
        
        # Phân tích theo giờ
        hour_stats = {}
        for trade in self.trades:
            hour = trade['entry_time'].hour
            
            if hour not in hour_stats:
                hour_stats[hour] = {
                    'trades': 0,
                    'win_count': 0,
                    'loss_count': 0,
                    'total_pnl': 0
                }
                
            hour_stats[hour]['trades'] += 1
            hour_stats[hour]['total_pnl'] += trade['pnl']
            
            if trade['pnl'] > 0:
                hour_stats[hour]['win_count'] += 1
            else:
                hour_stats[hour]['loss_count'] += 1
        
        # Tính win rate và profit
        for hour, stats in hour_stats.items():
            stats['win_rate'] = stats['win_count'] / stats['trades'] if stats['trades'] > 0 else 0
            stats['avg_pnl'] = stats['total_pnl'] / stats['trades'] if stats['trades'] > 0 else 0
        
        # In kết quả
        logger.info("Phân tích theo giờ (top 5 tốt nhất):")
        sorted_hours = sorted(hour_stats.items(), key=lambda x: x[1]['avg_pnl'], reverse=True)
        for hour, stats in sorted_hours[:5]:
            logger.info(f"Giờ {hour}:00:")
            logger.info(f"  - Số giao dịch: {stats['trades']}")
            logger.info(f"  - Win rate: {stats['win_rate']:.2f}")
            logger.info(f"  - Avg P&L: ${stats['avg_pnl']:.2f}")
            logger.info("---")
        
        # Phân tích theo ngày trong tuần
        day_stats = {}
        for trade in self.trades:
            day = trade['entry_time'].weekday()
            
            if day not in day_stats:
                day_stats[day] = {
                    'trades': 0,
                    'win_count': 0,
                    'loss_count': 0,
                    'total_pnl': 0
                }
                
            day_stats[day]['trades'] += 1
            day_stats[day]['total_pnl'] += trade['pnl']
            
            if trade['pnl'] > 0:
                day_stats[day]['win_count'] += 1
            else:
                day_stats[day]['loss_count'] += 1
        
        # Tính win rate và profit
        for day, stats in day_stats.items():
            stats['win_rate'] = stats['win_count'] / stats['trades'] if stats['trades'] > 0 else 0
            stats['avg_pnl'] = stats['total_pnl'] / stats['trades'] if stats['trades'] > 0 else 0
        
        # In kết quả
        day_names = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
        logger.info("Phân tích theo ngày trong tuần:")
        for day in range(7):
            if day in day_stats:
                logger.info(f"{day_names[day]}:")
                logger.info(f"  - Số giao dịch: {day_stats[day]['trades']}")
                logger.info(f"  - Win rate: {day_stats[day]['win_rate']:.2f}")
                logger.info(f"  - Avg P&L: ${day_stats[day]['avg_pnl']:.2f}")
                logger.info("---")
        
        # 3. Phân tích chuỗi giao dịch
        logger.info("\n" + "="*50)
        logger.info("PHÂN TÍCH CHUỖI GIAO DỊCH")
        logger.info("="*50)
        
        # Tìm chuỗi thắng/thua dài nhất
        current_win_streak = 0
        current_loss_streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        
        for trade in self.trades:
            if trade['pnl'] > 0:
                current_win_streak += 1
                current_loss_streak = 0
            else:
                current_loss_streak += 1
                current_win_streak = 0
                
            max_win_streak = max(max_win_streak, current_win_streak)
            max_loss_streak = max(max_loss_streak, current_loss_streak)
        
        logger.info(f"Chuỗi thắng dài nhất: {max_win_streak}")
        logger.info(f"Chuỗi thua dài nhất: {max_loss_streak}")
        
        # Phân tích drawdown
        if self.balance_history:
            drawdowns = []
            peak = self.balance_history[0]['balance']
            
            for entry in self.balance_history:
                if entry['balance'] > peak:
                    peak = entry['balance']
                
                dd = (peak - entry['balance']) / peak * 100
                drawdowns.append({
                    'timestamp': entry['timestamp'],
                    'balance': entry['balance'],
                    'peak': peak,
                    'drawdown_pct': dd
                })
            
            # Tìm drawdown tối đa
            max_dd = max(drawdowns, key=lambda x: x['drawdown_pct'])
            
            logger.info(f"Drawdown tối đa: {max_dd['drawdown_pct']:.2f}% (từ ${max_dd['peak']:.2f} xuống ${max_dd['balance']:.2f})")
            
            # Tìm thời kỳ drawdown lâu nhất
            current_dd_start = None
            current_dd_duration = timedelta(0)
            max_dd_duration = timedelta(0)
            
            for i in range(1, len(drawdowns)):
                if drawdowns[i]['drawdown_pct'] > 5 and current_dd_start is None:  # Drawdown > 5%
                    current_dd_start = drawdowns[i]['timestamp']
                elif drawdowns[i]['drawdown_pct'] <= 5 and current_dd_start is not None:
                    duration = drawdowns[i]['timestamp'] - current_dd_start
                    max_dd_duration = max(max_dd_duration, duration)
                    current_dd_start = None
            
            if current_dd_start is not None:
                duration = drawdowns[-1]['timestamp'] - current_dd_start
                max_dd_duration = max(max_dd_duration, duration)
            
            logger.info(f"Thời kỳ drawdown lâu nhất (>5%): {max_dd_duration.days} ngày, {max_dd_duration.seconds//3600} giờ")
        
        # 4. Phân tích Monte Carlo
        if len(self.trades) >= 30:
            logger.info("\n" + "="*50)
            logger.info("PHÂN TÍCH MONTE CARLO")
            logger.info("="*50)
            
            # Cập nhật trade history
            self.mc_analyzer.trade_history = self.trades
            
            # Lấy phân phối drawdown
            drawdown_dist = self.mc_analyzer.get_drawdown_distribution(simulations=1000)
            
            if 'percentiles' in drawdown_dist:
                logger.info(f"Drawdown VaR (95%): {drawdown_dist['percentiles']['95%']:.2f}%")
                logger.info(f"Drawdown VaR (99%): {drawdown_dist['percentiles']['99%']:.2f}%")
            
            # Lấy mức rủi ro đề xuất
            risk_levels = self.mc_analyzer.get_risk_levels()
            
            logger.info("Mức rủi ro đề xuất:")
            for level, risk in risk_levels.items():
                logger.info(f"  - Mức tin cậy {level}: {risk:.2f}%")
                
        # Lưu báo cáo phân tích vào file
        result_file = f"backtest_results/{self.config['symbol']}_{self.config['timeframe']}_backtest_analysis.txt"
        
        with open(result_file, 'w') as f:
            f.write("KẾT QUẢ PHÂN TÍCH BACKTEST\n")
            f.write("="*50 + "\n")
            f.write(f"Symbol: {self.config['symbol']}\n")
            f.write(f"Timeframe: {self.config['timeframe']}\n")
            f.write(f"Thời gian: {self.price_data.index[0]} đến {self.price_data.index[-1]}\n")
            f.write(f"Số dư ban đầu: ${self.config['initial_balance']:.2f}\n")
            f.write(f"Số dư cuối cùng: ${self.current_balance:.2f}\n")
            f.write(f"Lợi nhuận: ${self.current_balance - self.config['initial_balance']:.2f} ({(self.current_balance - self.config['initial_balance']) / self.config['initial_balance'] * 100:.2f}%)\n")
            f.write(f"Tổng số giao dịch: {len(self.trades)}\n")
            f.write(f"Win rate: {self.win_count / len(self.trades) if len(self.trades) > 0 else 0:.2f}\n")
            
            # Và các thông tin khác từ phân tích ở trên
            
        logger.info(f"Đã lưu báo cáo phân tích vào {result_file}")
        
        return {
            'hour_stats': hour_stats,
            'day_stats': day_stats,
            'max_win_streak': max_win_streak,
            'max_loss_streak': max_loss_streak
        }

def main():
    """Hàm chính để chạy backtest"""
    # Cấu hình
    config = {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "initial_balance": 10000.0,
        "leverage": 1,
        "risk_percentage": 1.0,
        "use_trailing_stop": True,
        "trailing_stop_callback": 0.5,  # 50% của profit
        "take_profit_ratio": 2.0,       # 2x stop loss
        "use_market_regime": True,
        "use_time_optimization": True,
        "use_monte_carlo": True,
        "use_pythagorean_sizer": True,
        "data_source": "synthetic",   # 'binance' hoặc 'synthetic'
        "log_trades": True
    }
    
    # Chạy backtest
    backtester = ComprehensiveBacktester(config)
    results = backtester.run()
    
    if results:
        # Phân tích kết quả
        analysis = backtester.analyze_results()
        
        # In kết quả
        print("\n" + "="*50)
        print("KẾT QUẢ BACKTEST")
        print("="*50)
        print(f"Số dư ban đầu: ${config['initial_balance']:.2f}")
        print(f"Số dư cuối cùng: ${results['summary']['final_balance']:.2f}")
        print(f"Lợi nhuận: ${results['summary']['profit']:.2f} ({results['summary']['profit_pct']:.2f}%)")
        print(f"Tổng số giao dịch: {results['summary']['total_trades']}")
        print(f"Win rate: {results['summary']['win_rate']:.2f}")
        print(f"Profit factor: {results['summary']['profit_factor']:.2f}")
        print(f"Drawdown tối đa: {results['summary']['max_drawdown_pct']:.2f}%")
        print("="*50)
        
    return results

if __name__ == "__main__":
    main()