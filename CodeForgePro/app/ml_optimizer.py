"""
Enhanced machine learning module with market regime analysis
"""
import logging
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report
from joblib import dump, load
import os
from market_regime_analyzer import MarketRegimeAnalyzer

logger = logging.getLogger(__name__)

class MLOptimizer:
    def __init__(self):
        """Initialize ML optimizer with market regime analysis"""
        self.models = {
            'random_forest': RandomForestClassifier(
                n_estimators=200,
                max_depth=8,
                min_samples_split=10,
                min_samples_leaf=4,
                class_weight='balanced',
                random_state=42
            ),
            'gradient_boosting': GradientBoostingClassifier(
                n_estimators=150,
                learning_rate=0.05,
                max_depth=4,
                subsample=0.8,
                min_samples_split=10,
                random_state=42
            ),
            'svm': SVC(
                kernel='rbf',
                probability=True,
                class_weight='balanced',
                random_state=42
            )
        }
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_importance = {}
        self.model_metrics = {}
        self.best_model = None
        self.best_model_name = None

        # Dynamic feature weights based on market regime
        self.feature_weights = {
            'trend_indicators': {
                'default': 0.4,
                'volatile': 0.3,
                'trending': 0.5,
                'ranging': 0.3
            },
            'momentum_indicators': {
                'default': 0.3,
                'volatile': 0.4,
                'trending': 0.3,
                'ranging': 0.2
            },
            'volume_indicators': {
                'default': 0.2,
                'volatile': 0.2,
                'trending': 0.1,
                'ranging': 0.3
            },
            'volatility_indicators': {
                'default': 0.1,
                'volatile': 0.1,
                'trending': 0.1,
                'ranging': 0.2
            }
        }

        # Add hedging state tracking
        self.hedge_positions = []
        self.hedge_pairs = {}
        self.last_hedge_rebalance = None

        # Add market regime analyzer
        self.regime_analyzer = MarketRegimeAnalyzer()
        self.current_strategy = None
        self.strategy_performance = {
            'trades': [],
            'win_rate': 0.0,
            'profit_factor': 0.0
        }

    def calculate_technical_indicators(self, df):
        """Calculate or verify technical indicators with enhanced error checking"""
        try:
            df = df.copy()  # Create a copy to avoid warnings

            # Verify we have minimum required data
            if len(df) < 50:
                logger.warning(f"Insufficient data for indicators. Need 50 bars, got {len(df)}")
                return None

            # Ensure required columns exist
            required_columns = ['close', 'high', 'low', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"Missing required columns: {missing_columns}")
                return None

            # Pre-calculate rolling windows to avoid repetition
            sma_20 = df['close'].rolling(window=20, min_periods=1).mean()
            sma_50 = df['close'].rolling(window=50, min_periods=1).mean()

            # Calculate moving averages with proper index handling
            df.loc[:, 'SMA_20'] = sma_20
            df.loc[:, 'SMA_50'] = sma_50

            # Calculate SMA ratio with validation
            # Ensure no division by zero
            df.loc[:, 'SMA_Ratio'] = np.where(
                sma_50 != 0,
                sma_20 / sma_50,
                1.0  # Default to neutral when denominator is zero
            )

            # Calculate Bollinger Bands
            df.loc[:, 'BB_middle'] = sma_20
            bb_std = df['close'].rolling(window=20, min_periods=1).std()
            df.loc[:, 'BB_upper'] = df['BB_middle'] + (2 * bb_std)
            df.loc[:, 'BB_lower'] = df['BB_middle'] - (2 * bb_std)
            df.loc[:, 'BB_Width'] = np.where(
                df['BB_middle'] != 0,
                (df['BB_upper'] - df['BB_lower']) / df['BB_middle'],
                0.0  # Default to zero width when price is zero
            )

            # Calculate RSI with error checking
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
            rs = gain / loss.replace(0, np.inf)  # Handle division by zero
            df.loc[:, 'RSI'] = 100 - (100 / (1 + rs))

            # Calculate MACD
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            df.loc[:, 'MACD'] = exp1 - exp2
            df.loc[:, 'MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df.loc[:, 'MACD_Hist'] = df['MACD'] - df['MACD_Signal']

            # Price momentum and volatility
            df.loc[:, 'Price_Change'] = df['close'].pct_change()
            df.loc[:, 'Price_Momentum'] = df['close'].pct_change(5)
            df.loc[:, 'Price_Volatility'] = df['Price_Change'].rolling(window=20, min_periods=1).std()

            # Volume indicators with validation
            volume_sma = df['volume'].rolling(window=20, min_periods=1).mean()
            df.loc[:, 'Volume_Ratio'] = np.where(
                volume_sma != 0,
                df['volume'] / volume_sma,
                1.0  # Default to neutral when volume SMA is zero
            )
            df.loc[:, 'Volume_Trend'] = df['volume'].pct_change(5)

            # Handle missing/invalid values
            df = df.replace([np.inf, -np.inf], np.nan)
            df = df.fillna(method='ffill').fillna(method='bfill')

            # Log calculated indicators for debugging
            latest = df.iloc[-1]
            logger.info("\nCalculated Technical Indicators:")
            for col in df.columns:
                if col in ['timestamp', 'close_time', 'trades', 'ignore']:
                    continue
                logger.info(f"{col}: {latest[col]:.4f}")

            return df

        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}")
            logger.exception("Detailed error traceback:")
            return None

    def detect_market_regime(self, data):
        """Detect current market regime based on multiple indicators"""
        try:
            latest = data.iloc[-1]

            # Volatility check
            volatility = latest['Price_Volatility']
            price_change = abs(latest['Price_Change'])
            high_volatility = volatility > data['Price_Volatility'].quantile(0.7)

            # Trend check using multiple indicators
            trend_strength = abs(latest['SMA_Ratio'] - 1)
            macd_trend = latest['MACD'] > latest['MACD_Signal']
            strong_trend = trend_strength > 0.02 and macd_trend

            # Volume analysis
            volume_trend = latest['Volume_Ratio']
            high_volume = volume_trend > 1.5

            if high_volatility and price_change > volatility:
                return 'volatile'
            elif strong_trend and high_volume:
                return 'trending'
            else:
                return 'ranging'

        except Exception as e:
            logger.error(f"Error detecting market regime: {e}")
            return 'default'

    def prepare_features(self, df):
        """Prepare features for ML models"""
        try:
            if df is None or df.empty:
                logger.error("Empty dataframe provided for feature preparation")
                return None

            # Calculate technical indicators
            df = self.calculate_technical_indicators(df)

            # Select base features
            X = pd.DataFrame()

            # Price action features
            X['Price_Level'] = df['close'] / df['SMA_50']
            X['Price_Momentum'] = df['Price_Momentum']
            X['Price_Volatility'] = df['Price_Volatility']

            # Trend features
            X['SMA_Ratio'] = df['SMA_Ratio']
            X['Trend_Strength'] = abs(X['SMA_Ratio'] - 1)
            X['BB_Position'] = (df['close'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'])

            # Momentum features
            X['RSI'] = df['RSI']
            X['MACD'] = df['MACD']
            X['MACD_Signal'] = df['MACD_Signal']
            X['MACD_Hist'] = df['MACD_Hist']

            # Volume features
            X['Volume_Ratio'] = df['Volume_Ratio']
            X['Volume_Trend'] = df['Volume_Trend']

            # Clean and normalize features
            X = X.replace([np.inf, -np.inf], np.nan)
            X = X.ffill().bfill()
            X = X.fillna(0)

            # Clip extreme values
            for col in X.columns:
                if X[col].dtype in [np.float64, np.float32]:
                    q_low = X[col].quantile(0.01)
                    q_high = X[col].quantile(0.99)
                    X[col] = X[col].clip(q_low, q_high)

            return X

        except Exception as e:
            logger.error(f"Error preparing features: {e}")
            return None

    def prepare_labels(self, df, lookahead=6):
        """Create enhanced labels for training"""
        try:
            if df is None or df.empty:
                logger.error("Empty dataframe provided for label preparation")
                return None

            # Calculate returns over multiple timeframes
            returns_short = df['close'].pct_change(periods=lookahead).shift(-lookahead)
            returns_med = df['close'].pct_change(periods=lookahead*2).shift(-lookahead*2)
            returns_long = df['close'].pct_change(periods=lookahead*3).shift(-lookahead*3)

            # Calculate volatility-adjusted returns
            volatility = df['close'].pct_change().rolling(window=20).std()
            vol_adjusted_returns = returns_short / volatility

            # Combine returns with weights
            weighted_returns = (
                0.5 * vol_adjusted_returns +
                0.3 * returns_med +
                0.2 * returns_long
            )

            # Dynamic thresholds based on volatility
            threshold = volatility * 0.3  # Reduced threshold for more signals

            # Create labels
            labels = pd.Series(0, index=df.index)
            labels[weighted_returns > threshold] = 1  # Buy signals
            labels[weighted_returns < -threshold] = -1  # Sell signals

            # Fill NaN values and remove lookahead bias
            labels = labels.fillna(0)
            labels = labels[:-lookahead*3]  # Remove future lookahead periods

            # Get features for the same periods
            features = self.prepare_features(df.iloc[:(len(labels))])

            if features is None:
                return None

            # Return labels aligned with features
            labels = labels[:len(features)]
            return labels

        except Exception as e:
            logger.error(f"Error preparing labels: {e}")
            logger.exception("Detailed error traceback:")
            return None

    def detect_hedge_opportunities(self, current_data, signal_probability):
        """Detect opportunities for hedging positions with trend validation"""
        try:
            if not config.HEDGING_ENABLED:
                logger.info("\n=== Phân tích Hedge (Phòng hộ) ===")
                logger.info("Hedging đang bị tắt")
                return None

            # Calculate technical indicators if needed
            if 'SMA_Ratio' not in current_data.columns:
                current_data = self.calculate_technical_indicators(current_data)
                if current_data is None:
                    logger.error("Không thể tính toán các chỉ báo kỹ thuật")
                    return None

            # Log initial signal strength check
            logger.info("\n=== Phân tích Hedge (Phòng hộ) ===")
            logger.info(f"Độ mạnh tín hiệu: {signal_probability:.4f}")
            logger.info(f"Ngưỡng kích hoạt: {config.HEDGE_TRIGGER_THRESHOLD}")

            # Only consider hedging for very strong signals
            if abs(signal_probability - 0.5) < (config.HEDGE_TRIGGER_THRESHOLD - 0.5):
                logger.info(f"Tín hiệu {signal_probability:.4f} yếu hơn ngưỡng {config.HEDGE_TRIGGER_THRESHOLD}")
                return None

            # Get current market conditions
            latest = current_data.iloc[-1]
            volume_sufficient = latest['volume'] > config.HEDGE_MIN_VOLUME

            logger.info("\nĐiều kiện thị trường:")
            logger.info(f"Khối lượng hiện tại: {latest['volume']:.2f}")
            logger.info(f"Khối lượng tối thiểu cần thiết: {config.HEDGE_MIN_VOLUME}")

            if not volume_sufficient:
                logger.info(f"Khối lượng không đủ: {latest['volume']:.2f} < {config.HEDGE_MIN_VOLUME}")
                return None

            # Check volume momentum
            volume_momentum = latest.get('Volume_Ratio', 0)
            logger.info(f"Động lượng khối lượng: {volume_momentum:.2f}")
            logger.info(f"Động lượng tối thiểu cần thiết: {config.HEDGE_MIN_VOLUME_MOMENTUM}")

            if volume_momentum < config.HEDGE_MIN_VOLUME_MOMENTUM:
                logger.info(f"Động lượng khối lượng không đủ: {volume_momentum:.2f} < {config.HEDGE_MIN_VOLUME_MOMENTUM}")
                return None

            # Calculate trend strength
            trend_strength = abs(latest['SMA_Ratio'] - 1)
            logger.info("\nPhân tích xu hướng:")
            logger.info(f"Độ mạnh xu hướng: {trend_strength:.4f}")
            logger.info(f"Độ mạnh tối thiểu cần thiết: {config.HEDGE_MIN_TREND_STRENGTH}")

            if trend_strength < config.HEDGE_MIN_TREND_STRENGTH:
                logger.info(f"Xu hướng không đủ mạnh: {trend_strength:.4f} < {config.HEDGE_MIN_TREND_STRENGTH}")
                return None

            # Check spread and correlation for potential hedge pairs
            hedge_opportunities = []

            logger.info("\nPhân tích các cặp tiền phòng hộ tiềm năng:")
            for symbol in config.TRADING_SYMBOLS:
                if symbol == current_data['symbol'].iloc[0]:
                    continue

                correlation = self.calculate_correlation(current_data, symbol)
                price_spread = self.calculate_spread(current_data, symbol)

                logger.info(f"\nPhân tích {symbol}:")
                logger.info(f"Tương quan: {correlation:.2f}")
                logger.info(f"Chênh lệch giá: {price_spread:.2%}")
                logger.info(f"Yêu cầu tương quan: < {config.HEDGE_CORRELATION_THRESHOLD}")
                logger.info(f"Phạm vi chênh lệch yêu cầu: {config.HEDGE_MIN_SPREAD:.2%} - {config.HEDGE_MAX_SPREAD:.2%}")

                if (correlation < config.HEDGE_CORRELATION_THRESHOLD and
                    config.HEDGE_MIN_SPREAD < price_spread < config.HEDGE_MAX_SPREAD):
                    hedge_opportunities.append({
                        'symbol': symbol,
                        'correlation': correlation,
                        'spread': price_spread,
                        'volume': latest['volume'],
                        'trend_strength': trend_strength
                    })
                    logger.info("✓ Thỏa mãn điều kiện phòng hộ")
                else:
                    logger.info("✗ Không thỏa mãn điều kiện phòng hộ")

            if hedge_opportunities:
                # Sort by correlation (most negative first) and trend strength
                hedge_opportunities.sort(key=lambda x: (x['correlation'], -x['trend_strength']))
                selected = hedge_opportunities[0]
                logger.info("\nCơ hội phòng hộ được chọn:")
                logger.info(f"Cặp tiền: {selected['symbol']}")
                logger.info(f"Tương quan: {selected['correlation']:.2f}")
                logger.info(f"Chênh lệch giá: {selected['spread']:.2%}")
                logger.info(f"Độ mạnh xu hướng: {selected['trend_strength']:.4f}")
                return selected

            logger.info("\nKhông tìm thấy cơ hội phòng hộ phù hợp")
            return None

        except Exception as e:
            logger.error(f"Lỗi khi phát hiện cơ hội phòng hộ: {e}")
            logger.exception("Chi tiết lỗi:")
            return None

    def manage_hedge_positions(self, current_data, signal_probability):
        """Manage open hedge positions and adjust as needed"""
        try:
            if not self.hedge_positions:
                return

            current_time = pd.Timestamp.now()

            # Check if rebalancing is needed
            if (self.last_hedge_rebalance is None or
                (current_time - self.last_hedge_rebalance).total_seconds() > config.HEDGE_REBALANCE_INTERVAL * 3600):

                logger.info("\nCân bằng lại các vị thế phòng hộ...")
                for hedge_pos in self.hedge_positions:
                    # Calculate hedge position P&L
                    entry_price = hedge_pos['entry_price']
                    current_price = current_data.iloc[-1]['close']
                    pnl = (current_price - entry_price) / entry_price if hedge_pos['side'] == 'long' else (entry_price - current_price) / entry_price

                    logger.info(f"\nPhân tích vị thế phòng hộ:")
                    logger.info(f"Cặp tiền: {hedge_pos['symbol']}")
                    logger.info(f"Chiều: {hedge_pos['side']}")
                    logger.info(f"Giá vào: {entry_price:.2f}")
                    logger.info(f"Giá hiện tại: {current_price:.2f}")
                    logger.info(f"Lợi nhuận: {pnl:.2%}")

                    # Check profit target or stop loss
                    if pnl >= config.HEDGE_PROFIT_TARGET:
                        logger.info(f"Đóng vị thế phòng hộ: {hedge_pos['symbol']} tại mục tiêu lợi nhuận {pnl:.2%}")
                        self.hedge_positions.remove(hedge_pos)
                        continue
                    elif pnl <= -config.HEDGE_STOP_LOSS:
                        logger.info(f"Đóng vị thế phòng hộ: {hedge_pos['symbol']} tại mức dừng lỗ {pnl:.2%}")
                        self.hedge_positions.remove(hedge_pos)
                        continue

                    # Verify hedge correlation is still valid
                    correlation = self.calculate_correlation(current_data, hedge_pos['symbol'])
                    logger.info(f"Tương quan hiện tại: {correlation:.2f}")

                    if correlation > config.HEDGE_CORRELATION_THRESHOLD:
                        logger.info(f"Đóng vị thế phòng hộ do thay đổi tương quan: {correlation:.2f}")
                        self.hedge_positions.remove(hedge_pos)

                self.last_hedge_rebalance = current_time
                logger.info(f"Số vị thế phòng hộ đang hoạt động: {len(self.hedge_positions)}")

        except Exception as e:
            logger.error(f"Lỗi khi quản lý vị thế phòng hộ: {e}")
            logger.exception("Chi tiết lỗi:")

    def calculate_correlation(self, data_1, symbol_2, lookback=30):
        """Calculate price correlation between two symbols"""
        try:
            # In simulation mode, generate correlated price data
            if getattr(self, 'simulation_mode', False):
                # Generate synthetic correlation based on symbol characteristics
                base_correlation = -0.8 if 'USD' in symbol_2 else -0.6
                noise = np.random.normal(0, 0.1)
                return base_correlation + noise

            # In live mode, fetch actual correlation data
            returns_1 = data_1['close'].pct_change().dropna()
            # Fetch data for symbol_2 and calculate correlation
            # This would need actual API integration
            return -0.7  # Placeholder for demo

        except Exception as e:
            logger.error(f"Error calculating correlation: {e}")
            return 0

    def calculate_spread(self, data_1, symbol_2):
        """Calculate price spread between two symbols"""
        try:
            # In simulation mode, generate realistic spread
            if getattr(self, 'simulation_mode', False):
                base_spread = 0.02  # 2% base spread
                noise = np.random.normal(0, 0.005)
                return max(0.001, base_spread + noise)

            # In live mode, calculate actual spread
            # This would need actual API integration
            return 0.02  # Placeholder for demo

        except Exception as e:
            logger.error(f"Error calculating spread: {e}")
            return 0

    def filter_signals(self, signal_probability, current_data):
        """Filter trading signals with enhanced hedge position tracking"""
        try:
            # Log input data shape and columns
            logger.info(f"\nPhân tích tín hiệu giao dịch:")
            logger.info(f"Số lượng dữ liệu: {current_data.shape}")
            logger.info(f"Xác suất tín hiệu: {signal_probability:.4f}")

            # Ensure we have enough data for technical indicators
            if len(current_data) < 50:
                logger.warning("Không đủ dữ liệu cho chỉ báo kỹ thuật")
                return signal_probability

            # Calculate technical indicators
            df = self.calculate_technical_indicators(current_data)
            latest = df.iloc[-1]

            # Initialize confirmation tracking
            confirmations = 0
            total_rules = 8
            confirmation_details = []

            # 1. Strong trend confirmation
            trend_strength = abs(latest['SMA_Ratio'] - 1)
            if trend_strength > 0.015:  # Reduced from 0.02 for more signals
                confirmations += 1
                confirmation_details.append(f"✓ Độ mạnh xu hướng: {trend_strength:.4f}")
            else:
                confirmation_details.append(f"✗ Xu hướng yếu: {trend_strength:.4f}")

            # 2. RSI confirmation
            if 40 < latest['RSI'] < 60:  # Widened from 35-65 for more signals
                confirmations += 1
                confirmation_details.append(f"✓ RSI tối ưu: {latest['RSI']:.1f}")
            else:
                confirmation_details.append(f"✗ RSI ngoài phạm vi: {latest['RSI']:.1f}")

            # 3. MACD confirmation
            macd_diff = latest['MACD'] - latest['MACD_Signal']
            if (signal_probability > 0.5 and macd_diff > 0) or \
               (signal_probability < 0.5 and macd_diff < 0):
                confirmations += 1
                confirmation_details.append(f"✓ MACD phù hợp: {macd_diff:.2f}")
            else:
                confirmation_details.append(f"✗ MACD không phù hợp: {macd_diff:.2f}")

            # Log all confirmation details
            logger.info("\nKết quả xác nhận:")
            for detail in confirmation_details:
                logger.info(detail)

            # Calculate confidence
            confidence = confirmations / total_rules
            logger.info(f"\nĐiểm tin cậy: {confirmations}/{total_rules} = {confidence:.2f}")

            # Apply confidence-based filtering
            if confidence < 0.625:  # Need 5/8 confirmations
                logger.info("✗ Không đủ xác nhận - trả về tín hiệu trung lập")
                return 0.5
            elif confidence < 0.75:  # Need 6/8 for full signal
                logger.info("! Tin cậy trung bình - điều chỉnh độ mạnh tín hiệu")
                signal_probability = signal_probability * 0.8 + 0.5 * 0.2

            # Check for hedging opportunities
            hedge_opportunity = self.detect_hedge_opportunities(current_data, signal_probability)

            if hedge_opportunity and len(self.hedge_positions) < config.HEDGE_MAX_POSITIONS:
                logger.info("\n=== Phát hiện cơ hội phòng hộ ===")
                logger.info(f"Cặp tiền: {hedge_opportunity['symbol']}")
                logger.info(f"Tương quan: {hedge_opportunity['correlation']:.2f}")
                logger.info(f"Chênh lệch giá: {hedge_opportunity['spread']:.2%}")

                # Calculate hedge position size based on regime
                regime = self.regime_analyzer.detect_regime(current_data)
                base_position_size = config.REGIME_PARAMETERS[regime]['HEDGE_POSITION_SIZE']

                # Add hedge position
                self.hedge_positions.append({
                    'symbol': hedge_opportunity['symbol'],
                    'size': base_position_size,
                    'entry_price': current_data.iloc[-1]['close'],
                    'entry_time': pd.Timestamp.now(),
                    'side': 'short' if signal_probability > 0.5 else 'long',
                    'regime': regime
                })

                logger.info(f"✓ Đã thêm vị thế phòng hộ: {hedge_opportunity['symbol']}")
                logger.info(f"Kích thước: {base_position_size:.2f}")
                logger.info(f"Giá vào: {current_data.iloc[-1]['close']:.2f}")
                logger.info(f"Chiều: {'SHORT' if signal_probability > 0.5 else 'LONG'}")
                logger.info(f"Giai đoạn: {regime}")

            # Manage existing hedge positions
            self.manage_hedge_positions(current_data, signal_probability)

            # Get current regime for position tracking
            regime = self.regime_analyzer.detect_regime(current_data)

            # Create position info for tracking
            position_info = {
                'entry_price': current_data.iloc[-1]['close'],
                'position_size': signal_probability,
                'signal_strength': abs(signal_probability - 0.5) * 2,
                'indicators': {
                    'trend_strength': abs(latest['SMA_Ratio'] - 1),
                    'rsi': latest['RSI'],
                    'macd_diff': latest['MACD'] - latest['MACD_Signal'],
                    'volume_ratio': latest['Volume_Ratio']
                }
            }

            # Track position for regime analysis
            self._track_regime_position(position_info, regime)

            return signal_probability

        except Exception as e:
            logger.error(f"Lỗi lọc tín hiệu với phòng hộ: {e}")
            logger.exception("Chi tiết lỗi:")
            return 0.5

    def predict_signal(self, current_data):
        """Generate trading signal prediction with regime analysis"""
        try:
            if not self.is_trained or not self.best_model:
                logger.warning("Models not trained yet")
                return 0.5

            # Detect current market regime with confidence score
            regime = self.regime_analyzer.detect_regime(current_data)
            logger.info("\n=== Phân tích giai đoạn thị trường ===")
            logger.info(f"Giai đoạn hiện tại: {regime}")

            # Get recommended strategy for current regime
            recommended_strategy = self.regime_analyzer.get_recommended_strategy()

            if recommended_strategy and recommended_strategy != self.current_strategy:
                logger.info("\n=== Thay đổi chiến lược giao dịch ===")
                logger.info(f"Giai đoạn hiện tại: {regime}")
                logger.info(f"Chiến lược cũ: {self.current_strategy['name'] if self.current_strategy else 'None'}")
                logger.info(f"Chiến lược mới: {recommended_strategy['name']}")
                logger.info(f"Tỷ lệ thắng lịch sử: {recommended_strategy['win_rate']:.2%}")
                logger.info(f"Hệ số lợi nhuận: {recommended_strategy['profit_factor']:.2f}")
                logger.info("\nCác tham số giao dịch:")
                for param, value in recommended_strategy['parameters'].items():
                    logger.info(f"- {param}: {value}")
                self.current_strategy = recommended_strategy

            # Ensure we have enough historical data for indicators
            min_required = 50  # Need 50 bars for SMA50
            if len(current_data) < min_required:
                logger.warning(f"Insufficient historical data. Need at least {min_required} bars.")
                return 0.5

            # Prepare features
            X = self.prepare_features(current_data)
            if X is None:
                logger.error("Failed to prepare features")
                return 0.5

            # Use only last row
            X = X.iloc[-1:]

            # Log feature values
            logger.info("\nGiá trị các đặc trưng:")
            for col in X.columns:
                logger.info(f"{col}: {X.iloc[0][col]:.4f}")

            # Scale features
            X_scaled = self.scaler.transform(X)

            # Get predictions from all models with regime-specific weights
            predictions = {}
            regime_weights = {
                'trending_up': {'random_forest': 0.5, 'gradient_boosting': 0.3, 'svm': 0.2},
                'trending_down': {'random_forest': 0.5, 'gradient_boosting': 0.3, 'svm': 0.2},
                'volatile': {'random_forest': 0.3, 'gradient_boosting': 0.5, 'svm': 0.2},
                'ranging': {'random_forest': 0.4, 'gradient_boosting': 0.3, 'svm': 0.3},
            }

            weights = regime_weights.get(regime, {'random_forest': 0.4, 'gradient_boosting': 0.4, 'svm': 0.2})

            for name, model in self.models.items():
                pred_proba = model.predict_proba(X_scaled)[0]
                weight = weights[name] * self.model_metrics['model_scores'][name]['test_score']
                predictions[name] = {
                    'buy': pred_proba[1] if len(pred_proba) > 1 else 0.5,
                    'weight': weight
                }
                logger.info(f"\nDự đoán từ {name}:")
                logger.info(f"Xác suất mua: {pred_proba[1]:.4f}")
                logger.info(f"Trọng số mô hình: {weight:.4f}")

            # Calculate weighted ensemble prediction
            total_weight = sum(p['weight'] for p in predictions.values())
            weighted_prob = sum(
                p['buy'] * p['weight'] for p in predictions.values()
            ) / total_weight

            logger.info(f"\nDự đoán tổng hợp (trước khi lọc): {weighted_prob:.4f}")

            # Apply signal filtering with regime-specific thresholds
            filtered_prob = self.filter_signals(weighted_prob, current_data)

            # Log final decision
            logger.info("\nQuyết định giao dịch cuối cùng:")
            if filtered_prob > 0.6:
                logger.info("✓ Phát hiện tín hiệu MUA")
            elif filtered_prob < 0.4:
                logger.info("✓ Phát hiện tín hiệu BÁN")
            else:
                logger.info("✗ Tín hiệu TRUNG LẬP")

            # Update strategy performance
            if len(self.strategy_performance['trades']) >= 20:
                self.regime_analyzer.update_regime_performance(
                    self.strategy_performance['trades']
                )

                # If strategy is performing well, save it
                if (self.strategy_performance['win_rate'] > 0.5 and
                    self.strategy_performance['profit_factor'] > 1.2):
                    self.regime_analyzer.save_successful_strategy({
                        'name': 'ml_strategy',
                        'win_rate': self.strategy_performance['win_rate'],
                        'profit_factor': self.strategy_performance['profit_factor'],
                        'parameters': {
                            'hedge_threshold': config.REGIME_PARAMETERS[regime]['HEDGE_TRIGGER_THRESHOLD'],
                            'position_size': config.REGIME_PARAMETERS[regime]['HEDGE_POSITION_SIZE'],
                            'take_profit': config.REGIME_PARAMETERS[regime]['TAKE_PROFIT_ADJUSTMENT'],
                            'volume_threshold': config.REGIME_PARAMETERS[regime]['VOLUME_THRESHOLD']
                        }
                    })

                # Reset performance tracking
                self.strategy_performance = {
                    'trades': [],
                    'win_rate': 0.0,
                    'profit_factor': 0.0
                }

            return filtered_prob

        except Exception as e:
            logger.error(f"Error generating prediction: {e}")
            logger.exception("Detailed error traceback:")
            return 0.5

    def train_model(self, df):
        """Train multiple ML models"""
        try:
            # Prepare features and labels
            X = self.prepare_features(df)
            y = self.prepare_labels(df)

            if X is None or y is None:
                logger.error("Failed to prepare features or labels")
                return False

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # Scale features
            self.scaler.fit(X_train)
            X_train_scaled = self.scaler.transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            # Train and evaluate each model
            best_score = 0
            self.model_metrics['model_scores'] = {}

            for name, model in self.models.items():
                logger.info(f"\nTraining {name}...")

                # Train model
                model.fit(X_train_scaled, y_train)

                # Cross-validation
                cv_scores = cross_val_score(
                    model, X_train_scaled, y_train, cv=5, scoring='accuracy'
                )

                # Test set performance
                test_score = model.score(X_test_scaled, y_test)
                y_pred = model.predict(X_test_scaled)

                # Store metrics
                self.model_metrics['model_scores'][name] = {
                    'cv_scores': cv_scores,
                    'cv_mean': cv_scores.mean(),
                    'cv_std': cv_scores.std(),
                    'test_score': test_score,
                    'classification_report': classification_report(y_test, y_pred)
                }

                # Update best model
                if test_score > best_score:
                    best_score = test_score
                    self.best_model = model
                    self.best_model_name = name

                logger.info(f"CV Score: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
                logger.info(f"Test Score: {test_score:.4f}")

            if self.best_model:
                logger.info(f"\nBest model: {self.best_model_name}")
                logger.info(f"Best test score: {best_score:.4f}")
                self.is_trained = True
                return True

            return False

        except Exception as e:
            logger.error(f"Error training models: {e}")
            logger.exception("Detailed error traceback:")
            return False

    def save_model(self, path):
        """Save trained models and metadata"""
        try:
            if not self.is_trained:
                logger.warning("Cannot save untrained models")
                return False

            os.makedirs(path, exist_ok=True)

            for name, model in self.models.items():
                dump(model, f"{path}/{name}_model.joblib")
            dump(self.scaler, f"{path}/scaler.joblib")

            metadata = {
                'feature_importance': self.feature_importance,
                'model_metrics': self.model_metrics,
                'best_model_name': self.best_model_name
            }
            dump(metadata, f"{path}/metadata.joblib")

            return True

        except Exception as e:
            logger.error(f"Error saving models: {e}")
            return False

    def load_model(self, path):
        """Load trained models and metadata"""
        try:
            # Load model components
            for name, model in self.models.items():
                self.models[name] = load(f"{path}/{name}_model.joblib")
            self.scaler = load(f"{path}/scaler.joblib")

            # Load metadata
            metadata = load(f"{path}/metadata.joblib")
            self.feature_importance = metadata['feature_importance']
            self.model_metrics = metadata['model_metrics']
            self.best_model_name = metadata['best_model_name']
            self.best_model = self.models[self.best_model_name]

            self.is_trained = True
            return True

        except Exception as e:
            logger.error(f"Error loading models: {e}")
            return False
    
    def _track_regime_position(self, position_info, regime):
        """Track position performance for specific regime"""
        try:
            if not hasattr(self, 'regime_positions'):
                self.regime_positions = {}

            if regime not in self.regime_positions:
                self.regime_positions[regime] = {
                    'active_positions': [],
                    'closed_positions': [],
                    'total_pnl': 0,
                    'win_count': 0,
                    'loss_count': 0,
                    'best_win': 0,
                    'worst_loss': 0,
                    'avg_win': 0,
                    'avg_loss': 0,
                    'win_streak': 0,
                    'current_streak': 0
                }

            # Add new position tracking
            position_info['regime'] = regime
            position_info['entry_time'] = pd.Timestamp.now()
            self.regime_positions[regime]['active_positions'].append(position_info)

            # Close positions that hit targets
            for pos in self.regime_positions[regime]['active_positions'][:]:
                if self._should_close_position(pos, regime):
                    self._close_position(pos, regime)

            # Calculate regime metrics
            regime_stats = self.regime_positions[regime]
            win_rate = regime_stats['win_count'] / (regime_stats['win_count'] + regime_stats['loss_count']) if (regime_stats['win_count'] + regime_stats['loss_count']) > 0 else 0

            logger.info(f"\n=== Theo dõi hiệu suất giai đoạn {regime} ===")
            logger.info(f"Số vị thế đang mở: {len(regime_stats['active_positions'])}")
            logger.info(f"Số vị thế đã đóng: {len(regime_stats['closed_positions'])}")
            logger.info(f"Tổng P&L: {regime_stats['total_pnl']:.2%}")
            logger.info(f"Tỷ lệ thắng: {win_rate:.2%}")
            logger.info(f"Chuỗi thắng hiện tại: {regime_stats['current_streak']}")
            logger.info(f"Chuỗi thắng tốt nhất: {regime_stats['win_streak']}")
            logger.info(f"Lợi nhuận TB/lệnh thắng: {regime_stats['avg_win']:.2%}")
            logger.info(f"Thua lỗ TB/lệnh thua: {regime_stats['avg_loss']:.2%}")

            # Update strategy if needed
            if len(regime_stats['closed_positions']) >= 10:
                if win_rate > 0.6 and regime_stats['total_pnl'] > 0:
                    self._save_successful_regime_strategy(regime)
                elif win_rate < 0.4 or regime_stats['total_pnl'] < -0.1:
                    self._adjust_regime_strategy(regime)

        except Exception as e:
            logger.error(f"Lỗi khi theo dõi vị thế: {e}")
            logger.exception("Chi tiết lỗi:")

    def _should_close_position(self, position, regime):
        """Check if position should be closed based on regime-specific rules"""
        try:
            current_price = self.get_current_price(position['entry_price'])  # Simulated price
            pnl = (current_price - position['entry_price']) / position['entry_price']

            # Get regime-specific parameters
            regime_params = config.REGIME_PARAMETERS[regime]
            take_profit = regime_params['TAKE_PROFIT_ADJUSTMENT']

            # Close conditions
            if pnl >= take_profit:  # Take profit hit
                return True
            if pnl <= -take_profit * 0.5:  # Stop loss at half the take profit
                return True

            return False

        except Exception as e:
            logger.error(f"Lỗi kiểm tra đóng vị thế: {e}")
            return False

    def _close_position(self, position, regime):
        """Close position and update regime statistics"""
        try:
            regime_stats = self.regime_positions[regime]

            # Calculate P&L
            current_price = self.get_current_price(position['entry_price'])
            pnl = (current_price - position['entry_price']) / position['entry_price']
            position['exit_price'] = current_price
            position['pnl'] = pnl
            position['exit_time'] = pd.Timestamp.now()

            # Update statistics
            regime_stats['total_pnl'] += pnl
            if pnl > 0:
                regime_stats['win_count'] += 1
                regime_stats['current_streak'] += 1
                regime_stats['win_streak'] = max(regime_stats['win_streak'], regime_stats['current_streak'])
                regime_stats['best_win'] = max(regime_stats['best_win'], pnl)
                regime_stats['avg_win'] = (regime_stats['avg_win'] * (regime_stats['win_count'] - 1) + pnl) / regime_stats['win_count']
            else:
                regime_stats['loss_count'] += 1
                regime_stats['current_streak'] = 0
                regime_stats['worst_loss'] = min(regime_stats['worst_loss'], pnl)
                regime_stats['avg_loss'] = (regime_stats['avg_loss'] * (regime_stats['loss_count'] - 1) + pnl) / regime_stats['loss_count']

            # Move to closed positions
            regime_stats['active_positions'].remove(position)
            regime_stats['closed_positions'].append(position)

            logger.info(f"\n=== Đóng vị thế trong giai đoạn {regime} ===")
            logger.info(f"P&L: {pnl:.2%}")
            logger.info(f"Thời gian nắm giữ: {position['exit_time'] - position['entry_time']}")

        except Exception as e:
            logger.error(f"Lỗi đóng vị thế: {e}")

    def _save_successful_regime_strategy(self, regime):
        """Save successful strategy parameters for regime"""
        try:
            strategy = {
                'name': 'ml_strategy',  # Fix extra quote
                'win_rate': self.regime_positions[regime]['win_count'] / (self.regime_positions[regime]['win_count'] + self.regime_positions[regime]['loss_count']),
                'profit_factor': abs(self.regime_positions[regime]['avg_win'] / self.regime_positions[regime]['avg_loss']) if self.regime_positions[regime]['avg_loss'] != 0 else float('inf'),
                'parameters': config.REGIME_PARAMETERS[regime].copy()
            }

            self.regime_analyzer.save_successful_strategy(strategy)
            logger.info(f"\n=== Lưu chiến lược thành công cho {regime} ===")
            logger.info(f"Tỷ lệ thắng: {strategy['win_rate']:.2%}")
            logger.info(f"Hệ số lợi nhuận: {strategy['profit_factor']:.2f}")

        except Exception as e:
            logger.error(f"Lỗi lưu chiến lược: {e}")

    def _adjust_regime_strategy(self, regime):
        """Adjust strategy parameters for underperforming regime"""
        try:
            current_params = config.REGIME_PARAMETERS[regime]

            # Adjust parameters based on performance
            if self.regime_positions[regime]['avg_loss'] < -0.05:  # Big losses
                current_params['HEDGE_POSITION_SIZE'] *= 1.2  # Increase hedge
                current_params['TAKE_PROFIT_ADJUSTMENT'] *= 0.8  # Lower targets
            elif self.regime_positions[regime]['win_rate'] < 0.4:  # Low win rate
                current_params['HEDGE_TRIGGER_THRESHOLD'] *= 0.9  # More conservative

            logger.info(f"\n=== Điều chỉnh chiến lược cho {regime} ===")
            logger.info("Các tham số mới:")
            for param, value in current_params.items():
                logger.info(f"- {param}: {value}")

        except Exception as e:
            logger.error(f"Lỗi điều chỉnh chiến lược: {e}")

    def get_current_price(self, entry_price):
        """Simulate current price for testing with safety checks"""
        try:
            # Generate random price movement with bounds
            change = np.random.normal(0, 0.02)  # 2% volatility
            change = np.clip(change, -0.05, 0.05)  # Limit to +-5%
            return entry_price * (1 + change)
        except Exception as e:
            logger.error(f"Lỗi khi lấy giá hiện tại: {e}")
            return entry_price  # Return entry price as fallback