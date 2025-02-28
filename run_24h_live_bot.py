#!/usr/bin/env python3
"""
Script để chạy bot giao dịch 24/7 với khả năng tự học liên tục

Chức năng:
1. Kết nối API Binance để giao dịch thời gian thực
2. Thu thập dữ liệu thị trường liên tục
3. Huấn luyện lại mô hình ML theo lịch trình
4. Tự động điều chỉnh chiến lược dựa trên hiệu suất
5. Gửi thông báo qua Telegram
"""

import os
import time
import json
import logging
import signal
import threading
import schedule
from datetime import datetime, timedelta

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_bot_live.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("live_trading_bot")

# Kiểm tra API keys
try:
    from dotenv import load_dotenv
    load_dotenv()
    
    BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY")
    BINANCE_API_SECRET = os.environ.get("BINANCE_API_SECRET")
    
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        logger.error("API keys không được cấu hình. Vui lòng kiểm tra biến môi trường BINANCE_API_KEY và BINANCE_API_SECRET")
        exit(1)
except Exception as e:
    logger.error(f"Lỗi khi tải API keys: {e}")
    exit(1)

# Import các module cần thiết
try:
    from app.binance_api import BinanceAPI
    from app.data_processor import DataProcessor
    from app.advanced_ml_optimizer import AdvancedMLOptimizer
    from app.market_regime_detector import MarketRegimeDetector
    from app.trading_bot import TradingBot
    from telegram_notify import TelegramNotifier
except Exception as e:
    logger.error(f"Lỗi khi import các module: {e}")
    exit(1)

class LiveTradingBot:
    """Bot giao dịch 24/7 với khả năng tự học liên tục"""
    
    def __init__(self, config_file="live_trading_config.json"):
        """
        Khởi tạo bot giao dịch
        
        Args:
            config_file (str): Đường dẫn đến file cấu hình
        """
        self.running = False
        self.config_file = config_file
        self.load_config()
        
        # Khởi tạo các thành phần cốt lõi
        self.init_components()
        
        # Thiết lập xử lý tín hiệu dừng
        signal.signal(signal.SIGINT, self.handle_exit)
        signal.signal(signal.SIGTERM, self.handle_exit)
        
        # Thời gian huấn luyện cuối cùng
        self.last_training_time = datetime.now() - timedelta(hours=24)  # Khởi đầu huấn luyện ngay lập tức
        
        logger.info("LiveTradingBot đã khởi tạo thành công")
    
    def load_config(self):
        """Tải cấu hình từ file"""
        try:
            if not os.path.exists(self.config_file):
                self.create_default_config()
            
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
                
            logger.info(f"Đã tải cấu hình từ {self.config_file}")
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {e}")
            self.config = self.get_default_config()
    
    def create_default_config(self):
        """Tạo file cấu hình mặc định"""
        default_config = self.get_default_config()
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
                
            logger.info(f"Đã tạo file cấu hình mặc định tại {self.config_file}")
        except Exception as e:
            logger.error(f"Lỗi khi tạo file cấu hình mặc định: {e}")
    
    def get_default_config(self):
        """Lấy cấu hình mặc định"""
        return {
            "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "DOGEUSDT"],
            "timeframes": ["1m", "5m", "15m", "1h", "4h", "1d"],
            "primary_timeframe": "1h",
            "trade_mode": "live",  # live hoặc test
            "risk_per_trade": 1.0,  # % tài khoản cho mỗi giao dịch
            "max_positions": 3,     # Số vị thế tối đa cùng lúc
            "leverage": 2,          # Đòn bẩy mặc định
            "training_interval_hours": 6,  # Huấn luyện lại mô hình sau mỗi x giờ
            "use_trailing_stop": True,
            "trailing_stop_activation": 1.0,  # % lợi nhuận kích hoạt trailing stop
            "trailing_stop_callback": 0.5,    # % callback cho trailing stop
            "take_profit": 5.0,      # % chốt lời
            "stop_loss": 2.0,        # % cắt lỗ
            "active_strategies": ["ml_composite", "multi_timeframe", "market_regime"],
            "notification_settings": {
                "telegram_enabled": True,
                "notify_on_trade": True,
                "notify_on_signal": True,
                "daily_report": True,
                "performance_threshold_alert": 5.0  # Cảnh báo nếu P&L hàng ngày vượt quá x%
            }
        }
    
    def init_components(self):
        """Khởi tạo các thành phần của bot"""
        try:
            # Kết nối API Binance
            self.binance_api = BinanceAPI(
                api_key=BINANCE_API_KEY,
                api_secret=BINANCE_API_SECRET,
                testnet=(self.config["trade_mode"] != "live")
            )
            
            # Bộ xử lý dữ liệu
            self.data_processor = DataProcessor()
            
            # Bộ phát hiện chế độ thị trường
            self.regime_detector = MarketRegimeDetector()
            
            # Bộ tối ưu hóa ML
            self.ml_optimizer = AdvancedMLOptimizer(
                use_model_per_regime=True,
                feature_selection=True,
                use_ensemble=True
            )
            
            # Bot giao dịch
            self.trading_bot = TradingBot(
                binance_api=self.binance_api,
                data_processor=self.data_processor,
                ml_optimizer=self.ml_optimizer,
                regime_detector=self.regime_detector,
                config=self.config
            )
            
            # Thông báo Telegram
            if self.config["notification_settings"]["telegram_enabled"]:
                self.notifier = TelegramNotifier()
                self.notifier.send_startup_notification()
            else:
                self.notifier = None
                
            logger.info("Tất cả các thành phần đã được khởi tạo thành công")
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo các thành phần: {e}")
            raise e
    
    def retrain_models(self):
        """Huấn luyện lại các mô hình ML với dữ liệu mới nhất"""
        if not self.running:
            return
            
        logger.info("Bắt đầu huấn luyện lại mô hình...")
        self.last_training_time = datetime.now()
        
        try:
            for symbol in self.config["symbols"]:
                logger.info(f"Huấn luyện mô hình cho {symbol}...")
                
                # Thu thập dữ liệu mới
                df = self.data_processor.get_historical_data(
                    symbol=symbol,
                    timeframe=self.config["primary_timeframe"],
                    limit=1000  # Lấy 1000 điểm dữ liệu gần nhất
                )
                
                if df is None or len(df) < 200:
                    logger.warning(f"Không đủ dữ liệu cho {symbol}, bỏ qua huấn luyện")
                    continue
                
                # Phát hiện chế độ thị trường hiện tại
                market_regime = self.regime_detector.detect_regime(df)
                
                # Chuẩn bị dữ liệu huấn luyện
                X, y = self.data_processor.prepare_ml_data(df)
                
                # Huấn luyện mô hình
                metrics = self.ml_optimizer.train_models(X, y, regime=market_regime)
                
                # Đánh giá hiệu suất mô hình
                logger.info(f"Hiệu suất mô hình mới cho {symbol}: {metrics}")
                
                # Cập nhật trạng thái của bot giao dịch
                self.trading_bot.update_ml_models()
            
            # Lưu các mô hình đã huấn luyện
            os.makedirs("models", exist_ok=True)
            self.ml_optimizer.save_models(directory="models")
            
            logger.info("Hoàn tất huấn luyện lại mô hình")
            
            # Gửi thông báo
            if self.notifier:
                self.notifier.send_message("Bot đã hoàn tất huấn luyện lại mô hình ML với dữ liệu mới nhất")
        except Exception as e:
            logger.error(f"Lỗi khi huấn luyện lại mô hình: {e}")
            
            # Gửi thông báo lỗi
            if self.notifier:
                self.notifier.send_error_alert(f"Lỗi khi huấn luyện lại mô hình: {e}", "ML Training")
    
    def daily_performance_report(self):
        """Tạo và gửi báo cáo hiệu suất hàng ngày"""
        if not self.running or not self.notifier:
            return
            
        try:
            # Lấy dữ liệu hiệu suất
            performance = self.trading_bot.get_performance_summary()
            
            # Gửi báo cáo
            self.notifier.send_daily_report(performance)
            
            logger.info("Đã gửi báo cáo hiệu suất hàng ngày")
        except Exception as e:
            logger.error(f"Lỗi khi gửi báo cáo hiệu suất hàng ngày: {e}")
    
    def schedule_tasks(self):
        """Lên lịch các tác vụ định kỳ"""
        # Huấn luyện lại mô hình
        training_interval = self.config.get("training_interval_hours", 6)
        schedule.every(training_interval).hours.do(self.retrain_models)
        
        # Báo cáo hàng ngày
        if self.config["notification_settings"]["daily_report"]:
            schedule.every().day.at("20:00").do(self.daily_performance_report)
        
        # Kiểm tra sức khỏe hệ thống
        schedule.every(1).hours.do(self.check_system_health)
        
        logger.info(f"Đã lên lịch các tác vụ định kỳ: huấn luyện mỗi {training_interval} giờ, báo cáo hàng ngày lúc 20:00")
    
    def check_system_health(self):
        """Kiểm tra sức khỏe hệ thống"""
        if not self.running:
            return
            
        try:
            # Kiểm tra kết nối API
            account_info = self.binance_api.get_account_info()
            if not account_info:
                logger.warning("Không thể kết nối đến Binance API")
                if self.notifier:
                    self.notifier.send_error_alert("Không thể kết nối đến Binance API", "API Connection")
            
            # Kiểm tra tài khoản
            account_balance = self.binance_api.get_balance()
            if account_balance <= 0:
                logger.warning("Số dư tài khoản không đủ để giao dịch")
                if self.notifier:
                    self.notifier.send_error_alert("Số dư tài khoản không đủ để giao dịch", "Account Balance")
            
            # Kiểm tra tình trạng thị trường
            for symbol in self.config["symbols"]:
                current_price = self.binance_api.get_current_price(symbol)
                if current_price <= 0:
                    logger.warning(f"Không thể lấy giá hiện tại cho {symbol}")
            
            logger.info("Kiểm tra sức khỏe hệ thống: OK")
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra sức khỏe hệ thống: {e}")
            if self.notifier:
                self.notifier.send_error_alert(f"Lỗi khi kiểm tra sức khỏe hệ thống: {e}", "System Health")
    
    def run(self):
        """Chạy bot giao dịch"""
        self.running = True
        logger.info("Bot giao dịch đang khởi động...")
        
        if self.notifier:
            self.notifier.send_message("Bot giao dịch đã khởi động và đang chạy")
        
        # Lên lịch các tác vụ định kỳ
        self.schedule_tasks()
        
        # Kiểm tra xem có cần huấn luyện lại mô hình không
        hours_since_last_training = (datetime.now() - self.last_training_time).total_seconds() / 3600
        if hours_since_last_training >= self.config.get("training_interval_hours", 6):
            logger.info("Huấn luyện mô hình ban đầu...")
            self.retrain_models()
        
        # Bắt đầu bot giao dịch
        trading_thread = threading.Thread(target=self._run_trading_bot)
        trading_thread.daemon = True
        trading_thread.start()
        
        # Chạy các tác vụ định kỳ
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp chính: {e}")
                time.sleep(5)  # Đợi trước khi thử lại
    
    def _run_trading_bot(self):
        """Chạy bot giao dịch trong một thread riêng"""
        while self.running:
            try:
                # Kiểm tra tín hiệu giao dịch cho mỗi cặp tiền
                for symbol in self.config["symbols"]:
                    signals = self.trading_bot.check_trading_signals(symbol)
                    
                    # Gửi thông báo tín hiệu nếu được cấu hình
                    if signals and self.notifier and self.config["notification_settings"]["notify_on_signal"]:
                        self.notifier.send_trade_signal({
                            "symbol": symbol,
                            "signals": signals
                        })
                    
                    # Thực hiện giao dịch nếu có tín hiệu
                    if signals and self.trading_bot.should_execute_trade(symbol, signals):
                        trade_result = self.trading_bot.execute_trade(symbol, signals)
                        
                        # Gửi thông báo giao dịch nếu được cấu hình
                        if trade_result and self.notifier and self.config["notification_settings"]["notify_on_trade"]:
                            self.notifier.send_trade_execution(trade_result)
                
                # Cập nhật và kiểm tra các vị thế hiện tại
                closed_positions = self.trading_bot.update_positions()
                
                # Gửi thông báo về các vị thế đã đóng
                if closed_positions and self.notifier and self.config["notification_settings"]["notify_on_trade"]:
                    for position in closed_positions:
                        self.notifier.send_position_closed(position)
                
                # Đợi trước khi kiểm tra lại
                time.sleep(10)  # Kiểm tra tín hiệu mỗi 10 giây
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp giao dịch: {e}")
                time.sleep(30)  # Đợi dài hơn trước khi thử lại
    
    def handle_exit(self, signum, frame):
        """Xử lý khi nhận tín hiệu dừng"""
        logger.info("Đang dừng bot giao dịch...")
        self.running = False
        
        # Đóng tất cả các vị thế nếu cấu hình
        # Lưu ý: Tùy chọn này có thể được cấu hình
        # self.trading_bot.close_all_positions()
        
        if self.notifier:
            self.notifier.send_message("Bot giao dịch đang dừng lại. Các vị thế hiện tại vẫn được giữ nguyên.")
        
        logger.info("Bot giao dịch đã dừng an toàn")

def main():
    """Hàm chính để chạy bot giao dịch 24/7"""
    try:
        # Khởi tạo bot
        bot = LiveTradingBot()
        
        # Chạy bot
        bot.run()
    except Exception as e:
        logger.critical(f"Lỗi nghiêm trọng khi chạy bot: {e}", exc_info=True)

if __name__ == "__main__":
    main()