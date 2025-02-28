"""
Configuration file for trading bot
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Regime-specific parameters (Các tham số theo giai đoạn)
REGIME_PARAMETERS = {
    'trending_up': {
        'HEDGE_TRIGGER_THRESHOLD': 0.75,  # Giảm để dễ kích hoạt hedge trong xu hướng tăng
        'HEDGE_POSITION_SIZE': 0.3,  # Tăng kích thước hedge để bảo vệ tốt hơn
        'TAKE_PROFIT_ADJUSTMENT': 0.5,  # Tăng điều chỉnh lợi nhuận trong xu hướng tăng
        'VOLUME_THRESHOLD': 1.3,  # Tăng ngưỡng khối lượng để xác nhận xu hướng
    },
    'trending_down': {
        'HEDGE_TRIGGER_THRESHOLD': 0.70,  # Giảm thêm để hedge sớm hơn trong xu hướng giảm
        'HEDGE_POSITION_SIZE': 0.5,  # Tăng mạnh kích thước hedge để bảo vệ
        'TAKE_PROFIT_ADJUSTMENT': 0.3,  # Giảm điều chỉnh lợi nhuận trong xu hướng giảm
        'VOLUME_THRESHOLD': 1.4,  # Tăng ngưỡng khối lượng để xác nhận xu hướng
    },
    'volatile': {
        'HEDGE_TRIGGER_THRESHOLD': 0.80,  # Giảm ngưỡng hedge trong biến động
        'HEDGE_POSITION_SIZE': 0.6,  # Tăng mạnh kích thước hedge trong biến động
        'TAKE_PROFIT_ADJUSTMENT': 0.2,  # Giảm mạnh điều chỉnh lợi nhuận
        'VOLUME_THRESHOLD': 1.6,  # Tăng cao ngưỡng khối lượng
    },
    'ranging': {
        'HEDGE_TRIGGER_THRESHOLD': 0.85,  # Tăng ngưỡng hedge trong sideway
        'HEDGE_POSITION_SIZE': 0.2,  # Giảm kích thước hedge
        'TAKE_PROFIT_ADJUSTMENT': 0.4,  # Tăng điều chỉnh lợi nhuận trong sideway
        'VOLUME_THRESHOLD': 1.2,  # Giảm ngưỡng khối lượng
    }
}

# Simulation mode (Chế độ mô phỏng)
SIMULATION_MODE = os.getenv('SIMULATION_MODE', 'False').lower() == 'true'
SIMULATE_SIGNALS = os.getenv('SIMULATE_SIGNALS', 'BUY')  # Force BUY signals for testing

# Binance API configuration (Cấu hình API Binance)
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')
BINANCE_TESTNET = True  # Set to False for live trading (Đặt False để giao dịch thật)

# Trading parameters (Thông số giao dịch)
TRADING_SYMBOLS = ['BTCUSDT', 'ETHUSDT']  # Trading pairs (Cặp tiền giao dịch)
TRADE_QUANTITY = 0.001  # Default trade quantity (Khối lượng giao dịch mặc định)
MAX_TRADES_PER_DAY = 10  # Số giao dịch tối đa mỗi ngày
STOP_LOSS_PCT = 2.0  # Stop loss at 2% (Dừng lỗ ở mức 2%)
TAKE_PROFIT_PCT = 3.0  # Take profit at 3% (Chốt lời ở mức 3%)

# Risk management (Quản lý rủi ro)
MAX_POSITION_SIZE = 0.1  # Maximum 10% of portfolio per trade (Tối đa 10% danh mục cho mỗi lệnh)
MAX_DAILY_DRAWDOWN = 5.0  # Maximum 5% daily drawdown (Giảm giá tối đa 5% mỗi ngày)
TRAILING_STOP_ACTIVATION = 1.5  # Activate trailing stop when profit reaches 1.5% (Kích hoạt trailing stop khi lợi nhuận đạt 1.5%)
TRAILING_STOP_DISTANCE = 0.5  # Trailing stop follows price at 0.5% distance (Trailing stop theo giá ở khoảng cách 0.5%)
MAX_OPEN_POSITIONS = 5  # Maximum number of open positions including hedges (Số vị thế mở tối đa bao gồm cả hedge)
POSITION_SIZING_MODEL = 'dynamic'  # Use dynamic position sizing based on confidence (Sử dụng kích thước vị thế động dựa trên độ tin cậy)

# Smart DCA Configuration (Cấu hình DCA thông minh)
DCA_LEVELS = [1, 2, 3, 4, 5]  # DCA entry levels (Các mức vào lệnh DCA)
DCA_DISTRIBUTION = [0.2, 0.2, 0.2, 0.2, 0.2]  # Equal distribution across levels (Phân bố đều qua các mức)
DCA_PRICE_DEVIATION = 0.005  # 0.5% price difference between levels (Chênh lệch giá 0.5% giữa các mức)
DCA_VOLUME_SCALE = 1.2  # Increase volume by 20% for each level (Tăng khối lượng 20% cho mỗi mức)
DCA_MAX_ORDERS = 5  # Maximum number of active DCA orders (Số lệnh DCA hoạt động tối đa)
DCA_MIN_TREND_STRENGTH = 0.2  # Minimum trend strength to enable DCA (Độ mạnh xu hướng tối thiểu để kích hoạt DCA)

# Hedging configuration (Cấu hình hedging - Phòng hộ)
HEDGING_ENABLED = True  # Bật tính năng phòng hộ
HEDGE_TRIGGER_THRESHOLD = 0.85  # Strong signal needed to trigger hedge (Tín hiệu mạnh cần thiết để kích hoạt phòng hộ)
HEDGE_POSITION_SIZE = 0.3  # Size of hedge position relative to main position (Kích thước vị thế phòng hộ so với vị thế chính)
HEDGE_MIN_SPREAD = 0.01  # Minimum price spread to initiate hedge (1%) (Chênh lệch giá tối thiểu để bắt đầu phòng hộ)
HEDGE_MAX_SPREAD = 0.05  # Maximum price spread to maintain hedge (5%) (Chênh lệch giá tối đa để duy trì phòng hộ)
HEDGE_PROFIT_TARGET = 0.02  # Target profit to close hedge (2%) (Mục tiêu lợi nhuận để đóng vị thế phòng hộ)
HEDGE_STOP_LOSS = 0.03  # Stop loss level for hedge positions (3%) (Mức dừng lỗ cho vị thế phòng hộ)
HEDGE_MAX_POSITIONS = 3  # Maximum number of simultaneous hedge positions (Số vị thế phòng hộ đồng thời tối đa)
HEDGE_MIN_VOLUME = 2000  # Minimum volume required for hedging (Khối lượng tối thiểu cần thiết để phòng hộ)
HEDGE_REBALANCE_INTERVAL = 4  # Hours between hedge rebalancing (Số giờ giữa các lần cân bằng lại phòng hộ)
HEDGE_CORRELATION_THRESHOLD = -0.7  # Minimum negative correlation for hedge pairs (Tương quan âm tối thiểu cho các cặp phòng hộ)
HEDGE_MIN_TREND_STRENGTH = 0.015  # Minimum trend strength required for hedging (Độ mạnh xu hướng tối thiểu cần thiết để phòng hộ)
HEDGE_MIN_VOLUME_MOMENTUM = 1.2  # Minimum volume momentum (20% increase) (Động lượng khối lượng tối thiểu - tăng 20%)

# Take Profit Configuration (Cấu hình chốt lời)
TAKE_PROFIT_LEVELS = [0.5, 1.0, 1.5, 2.0, 3.0]  # Multiple take-profit levels (%) (Nhiều mức chốt lời)
TAKE_PROFIT_DISTRIBUTION = [0.3, 0.25, 0.2, 0.15, 0.1]  # Position size distribution (Phân bố kích thước vị thế)
TAKE_PROFIT_ADJUSTMENT = 0.3  # Adjustment factor for more frequent trades (Hệ số điều chỉnh cho giao dịch thường xuyên hơn)

# Technical indicators configuration (Cấu hình chỉ báo kỹ thuật)
SMA_SHORT_PERIOD = 20  # Đường trung bình động ngắn hạn
SMA_LONG_PERIOD = 50  # Đường trung bình động dài hạn
RSI_PERIOD = 14  # Chu kỳ RSI
RSI_OVERSOLD = 40  # Vùng quá bán
RSI_OVERBOUGHT = 60  # Vùng quá mua

# Bollinger Bands parameters (Thông số Bollinger Bands)
BOLLINGER_PERIOD = 20  # Chu kỳ
BOLLINGER_STD_DEV = 2.0  # Độ lệch chuẩn
BOLLINGER_BREAKOUT_PCT = 0.5  # Phần trăm phá vỡ dải

# MACD parameters (Thông số MACD)
MACD_FAST = 12  # Đường nhanh
MACD_SLOW = 26  # Đường chậm
MACD_SIGNAL = 9  # Đường tín hiệu
MACD_THRESHOLD = 5  # Ngưỡng MACD
MACD_DIVERGENCE_LOOKBACK = 5  # Số nến kiểm tra phân kỳ
MACD_HISTOGRAM_REVERSAL = 0.2  # Phần trăm đảo chiều histogram

# Volume analysis (Phân tích khối lượng)
VOLUME_MA_PERIOD = 20  # Chu kỳ trung bình động khối lượng
VOLUME_THRESHOLD = 1.1  # Ngưỡng khối lượng
VOLUME_PRICE_CORRELATION = 0.3  # Tương quan giá-khối lượng

# Performance metrics (Chỉ số hiệu suất)
METRICS_WINDOW = 30  # Days to calculate performance metrics (Số ngày tính toán hiệu suất)
PROFIT_FACTOR_MIN = 1.1  # Hệ số lợi nhuận tối thiểu
SHARPE_RATIO_MIN = 0.3  # Tỷ lệ Sharpe tối thiểu
MAX_DRAWDOWN_THRESHOLD = 25  # Ngưỡng drawdown tối đa
MIN_WIN_RATE = 0.25  # Tỷ lệ thắng tối thiểu

# Grid Trading Configuration (Cấu hình giao dịch lưới)
GRID_LEVELS = 10  # Number of grid levels (Số mức lưới)
GRID_SPREAD = 0.05  # 5% price range for grids (Phạm vi giá cho lưới)
GRID_SIZE = 20  # Grid order size in USDT (Kích thước lệnh lưới)
GRID_REBALANCE_THRESHOLD = 0.02  # 2% deviation triggers rebalance (Chênh lệch kích hoạt cân bằng lại)
MIN_PROFIT_PER_GRID = 0.002  # Minimum 0.2% profit per grid (Lợi nhuận tối thiểu mỗi lưới)

# Backtesting parameters (Thông số kiểm thử)
BACKTEST_PERIOD = 180  # Days of historical data for backtesting (Số ngày dữ liệu lịch sử để kiểm thử)
COMMISSION_RATE = 0.001  # 0.1% commission per trade (Phí giao dịch)
SLIPPAGE = 0.0005  # 0.05% slippage assumption (Giả định trượt giá)

# Database configuration (Cấu hình cơ sở dữ liệu)
DATABASE_URL = os.getenv('DATABASE_URL')

# Logging configuration (Cấu hình ghi log)
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_TO_FILE = True
LOG_FILE = 'trading_bot.log'

# Minimum trade amounts for each symbol (Số tiền giao dịch tối thiểu cho mỗi symbol)
MIN_TRADE_AMOUNTS = {
    'BTCUSDT': 20,  # Min $20 for BTC
    'ETHUSDT': 15,  # Min $15 for ETH
    'DEFAULT': 10    # Default min $10 for other coins
}