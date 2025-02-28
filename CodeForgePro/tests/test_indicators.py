"""Tests for technical indicators calculations"""
import pytest
import pandas as pd
import numpy as np
import importlib
from app.data_processor import DataProcessor
from app.trading_strategy import TradingStrategy
from app.binance_api import BinanceAPI
import app.config as config
from app.config import MIN_TRADE_AMOUNTS, DCA_LEVELS, DCA_VOLUME_SCALE

# Constants for testing
VOLUME_THRESHOLD = 1.1  # Reduced threshold for testing
VOLUME_PRICE_CORRELATION = 0.3  # Reduced correlation requirement

def create_test_data(pattern='trend'):
    """Create sample price data for testing with different patterns"""
    dates = pd.date_range(start='2025-01-01', periods=100, freq='h')

    if pattern == 'flat':
        # Flat prices with very small random noise
        prices = [100 + np.random.normal(0, 0.005) for _ in range(100)]  # Reduced noise
    elif pattern == 'volatile':
        # Highly volatile prices
        prices = [100 + np.sin(i/5) * 10 + np.random.normal(0, 5) for i in range(100)]
    else:  # trend
        # Upward trend with cyclical volatility
        prices = []
        for i in range(100):
            trend = i * 0.1
            volatility = np.sin(i/10) * 5
            noise = np.random.normal(0, 1)
            price = 100 + trend + volatility + noise
            prices.append(price)

    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p * 1.02 for p in prices],
        'low': [p * 0.98 for p in prices],
        'close': prices,
        'volume': np.random.rand(100) * 1000
    })
    return df

class TestIndicators:
    @pytest.fixture
    def setup(self):
        # Force reload config to ensure simulation mode is set
        config.SIMULATION_MODE = True
        importlib.reload(config)

        # Create instances with reloaded config
        binance_client = BinanceAPI()
        data_processor = DataProcessor(binance_client)
        trading_strategy = TradingStrategy(binance_client, data_processor)
        return data_processor, trading_strategy

    def test_sma_calculation(self, setup):
        """Test SMA calculation with different price patterns"""
        data_processor, _ = setup

        # Test trending data
        df = create_test_data('trend')
        df = data_processor.calculate_indicators(df)
        assert not df['SMA_20'].isnull().all(), "SMA_20 values are null"
        assert not df['SMA_50'].isnull().all(), "SMA_50 values are all null"

        # Test flat data
        df_flat = create_test_data('flat')
        df_flat = data_processor.calculate_indicators(df_flat)
        assert (df_flat['SMA_20'] - 100).abs().mean() < 1, "SMA error on flat data"

        # Test volatile data
        df_volatile = create_test_data('volatile')
        df_volatile = data_processor.calculate_indicators(df_volatile)
        assert not df_volatile['SMA_20'].isnull().any(), "SMA has null values"

    def test_bollinger_bands(self, setup):
        """Test Bollinger Bands calculation and validation"""
        data_processor, _ = setup
        df = create_test_data('volatile')
        df = data_processor.calculate_indicators(df)

        # Skip initial NaN values
        df = df.dropna(subset=['BB_upper', 'BB_lower', 'BB_middle'])

        # Verify BB calculations
        assert not df.empty, "No valid Bollinger Bands data after dropping NaN"
        assert (df['BB_upper'] >= df['BB_middle']).all(), "BB upper should be >= middle band"
        assert (df['BB_lower'] <= df['BB_middle']).all(), "BB lower should be <= middle band"

        # Test band width
        band_width = (df['BB_upper'] - df['BB_lower']) / df['BB_middle']
        assert (band_width >= 0).all(), "Invalid BB band width"

    def test_rsi_calculation(self, setup):
        """Test RSI calculation with edge cases"""
        data_processor, _ = setup

        # Test trending data
        df = create_test_data('trend')
        df = data_processor.calculate_indicators(df)
        assert not df['RSI'].isnull().all(), "RSI values are null"
        assert (df['RSI'] >= 0).all() and (df['RSI'] <= 100).all(), "RSI out of range"

        # Test flat data with allowance for minor fluctuations
        df_flat = create_test_data('flat')
        df_flat = data_processor.calculate_indicators(df_flat)
        df_flat = df_flat.dropna(subset=['RSI'])  # Skip initial NaN values
        rsi_mean = df_flat['RSI'].mean()
        assert 45 <= rsi_mean <= 55, f"RSI mean ({rsi_mean:.2f}) too far from neutral on flat data"
        assert df_flat['RSI'].std() < 5, "RSI volatility too high for flat data"

    def test_macd_calculation(self, setup):
        """Test MACD calculation and histogram"""
        data_processor, _ = setup
        df = create_test_data('trend')
        df = data_processor.calculate_indicators(df)

        # Verify MACD components
        assert not df['MACD'].isnull().all(), "MACD values are null"
        assert not df['MACD_Signal'].isnull().all(), "MACD Signal is null"
        assert not df['MACD_Hist'].isnull().all(), "MACD Histogram is null"

        # Verify histogram calculation
        calculated_hist = df['MACD'] - df['MACD_Signal']
        assert np.allclose(calculated_hist, df['MACD_Hist'], rtol=1e-10), "MACD Histogram error"

    def test_volume_analysis(self, setup):
        """Test volume-related indicators"""
        data_processor, _ = setup
        df = create_test_data('volatile')
        df = data_processor.calculate_indicators(df)

        # Check volume ratio
        assert not df['Volume_Ratio'].isnull().all(), "Volume ratio is null"
        assert (df['Volume_Ratio'] >= 0).all(), "Invalid volume ratio"

        # Check correlation - ignoring NaN values
        correlation = df['Price_Volume_Corr'].dropna()
        assert not correlation.empty, "No valid price-volume correlation values"
        assert (correlation >= -1).all() and (correlation <= 1).all(), "Price-volume correlation outside [-1,1] range"

        # Test dynamic volume threshold with NaN handling
        price_changes = df['close'].pct_change().fillna(0)  # Replace NaN with 0 for first value
        dynamic_thresholds = [VOLUME_THRESHOLD * max(0.5, 1 - min(abs(pc) * 2, 0.5)) for pc in price_changes]
        assert all(dt > 0 for dt in dynamic_thresholds), "Invalid dynamic threshold"

        # Test trend-based volume confirmation
        df['Trend_Volume_Check'] = (df['close'] > df['SMA_20']) & (df['volume'] > df['volume'].shift(1))
        trend_volume = df['Trend_Volume_Check'].dropna()
        assert not trend_volume.empty, "No valid trend volume checks"

class TestTradeExecution:
    @pytest.fixture
    def setup(self):
        # Force reload config to ensure simulation mode is set
        config.SIMULATION_MODE = True
        importlib.reload(config)

        # Create clients after config reload
        binance_client = BinanceAPI()
        # Explicitly force simulation mode
        binance_client.simulation_mode = True
        binance_client.client = None

        data_processor = DataProcessor(binance_client)
        trading_strategy = TradingStrategy(binance_client, data_processor)

        # Verify simulation mode is set correctly
        assert binance_client.simulation_mode, "BinanceAPI not in simulation mode"
        assert trading_strategy.simulation_mode, "TradingStrategy not in simulation mode"

        return trading_strategy

    def test_min_trade_amount(self, setup):
        """Test minimum trade amount validation"""
        trading_strategy = setup

        # Test BTC min amount
        btc_quantity = trading_strategy.calculate_trade_quantity('BTCUSDT')
        assert btc_quantity * 85000 >= MIN_TRADE_AMOUNTS['BTCUSDT'], "BTC trade below minimum"

        # Test ETH min amount
        eth_quantity = trading_strategy.calculate_trade_quantity('ETHUSDT')
        assert eth_quantity * 2500 >= MIN_TRADE_AMOUNTS['ETHUSDT'], "ETH trade below minimum"

    def test_dca_distribution(self, setup):
        """Test DCA order distribution and minimum amounts"""
        trading_strategy = setup

        # Test BTC DCA
        total_quantity = 0.01  # 850 USD at 85000
        orders = trading_strategy.place_dca_orders('BTCUSDT', 'BUY', total_quantity, 85000)

        # Verify DCA levels
        assert len(orders) > 0, "No DCA orders created"
        assert len(orders) <= len(DCA_LEVELS), "Too many DCA levels"

        # Verify each order meets minimum
        for order in orders:
            order_value = float(order['quantity']) * 85000
            assert order_value >= MIN_TRADE_AMOUNTS['BTCUSDT'], f"DCA order below minimum: {order_value}"

        # Verify volume scaling
        quantities = [float(order['quantity']) for order in orders]
        for i in range(1, len(quantities)):
            ratio = quantities[i] / quantities[i-1]
            assert abs(ratio - DCA_VOLUME_SCALE) < 0.1, "Invalid DCA volume scaling"

if __name__ == '__main__':
    pytest.main(['-v'])