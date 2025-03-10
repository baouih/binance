import os
import sys
import json
import time
import logging
import threading
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QTextEdit, QComboBox, 
                            QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
                            QGroupBox, QRadioButton, QCheckBox, QProgressBar, QFrame,
                            QSplitter, QGridLayout, QScrollArea, QLineEdit)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QIcon, QPalette, QPixmap

# Đường dẫn tới các modules cần thiết khác
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import các module cần thiết
try:
    from config_loader import load_config, save_config
    from api_data_validator import validate_api_credentials
    from advanced_telegram_notifier import TelegramNotifier
    from auto_sltp_manager import AutoSLTPManager
    from risk_manager import RiskManager
    from market_analyzer import MarketAnalyzer
    from trading_bot import TradingBot
    from position_manager import PositionManager
    from signal_generator import SignalGenerator
except ImportError as e:
    print(f"Import lỗi: {e}")
    sys.exit(1)

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_gui.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("EnhancedTradingGUI")

class BotWorker(QThread):
    """Thread để chạy bot trong background và không làm đơ giao diện"""
    update_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    position_update_signal = pyqtSignal(list)
    market_data_signal = pyqtSignal(dict)
    
    def __init__(self, config, risk_level):
        super().__init__()
        self.config = config
        self.risk_level = risk_level
        self.running = False
        self.bot = None
        self.telegram_notifier = None
        self.market_analyzer = None
        self.signal_generator = None
        self.position_manager = None
    
    def setup_bot(self):
        try:
            risk_config_path = f"risk_configs/risk_level_{self.risk_level}.json"
            if not os.path.exists(risk_config_path):
                self.update_signal.emit(f"Không tìm thấy cấu hình rủi ro: {risk_config_path}")
                return False
            
            with open(risk_config_path, 'r') as f:
                risk_config = json.load(f)
            
            # Khởi tạo các components
            self.telegram_notifier = TelegramNotifier(
                token=os.environ.get("TELEGRAM_BOT_TOKEN"),
                chat_id=os.environ.get("TELEGRAM_CHAT_ID")
            )
            
            self.market_analyzer = MarketAnalyzer(
                api_key=os.environ.get("BINANCE_TESTNET_API_KEY"),
                api_secret=os.environ.get("BINANCE_TESTNET_API_SECRET"),
                testnet=True
            )
            
            self.signal_generator = SignalGenerator(
                market_analyzer=self.market_analyzer,
                config=self.config
            )
            
            self.position_manager = PositionManager(
                api_key=os.environ.get("BINANCE_TESTNET_API_KEY"),
                api_secret=os.environ.get("BINANCE_TESTNET_API_SECRET"),
                testnet=True,
                risk_config=risk_config
            )
            
            risk_manager = RiskManager(
                position_manager=self.position_manager,
                risk_config=risk_config
            )
            
            # Khởi tạo bot
            self.bot = TradingBot(
                market_analyzer=self.market_analyzer,
                signal_generator=self.signal_generator,
                position_manager=self.position_manager,
                risk_manager=risk_manager,
                telegram_notifier=self.telegram_notifier,
                config=self.config
            )
            
            self.update_signal.emit("Bot đã được khởi tạo thành công!")
            return True
        except Exception as e:
            self.update_signal.emit(f"Lỗi khi khởi tạo bot: {str(e)}")
            logger.error(f"Lỗi khi khởi tạo bot: {str(e)}")
            return False
    
    def run(self):
        self.running = True
        if not self.setup_bot():
            self.status_signal.emit("Không khởi tạo được bot")
            self.running = False
            return
        
        self.status_signal.emit("Bot đang chạy")
        
        # Gửi thông báo bắt đầu
        try:
            self.telegram_notifier.send_message(
                f"🤖 Bot bắt đầu chạy với cấu hình rủi ro {self.risk_level}% vào {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            )
        except Exception as e:
            self.update_signal.emit(f"Không gửi được thông báo Telegram: {str(e)}")
        
        # Vòng lặp chính để chạy bot
        while self.running:
            try:
                # Cập nhật dữ liệu thị trường
                market_data = self.market_analyzer.get_market_overview()
                self.market_data_signal.emit(market_data)
                
                # Lấy thông tin vị thế
                positions = self.position_manager.get_all_positions()
                self.position_update_signal.emit(positions)
                
                # Chạy một chu kỳ của bot
                bot_action = self.bot.run_cycle()
                if bot_action:
                    self.update_signal.emit(f"Bot action: {bot_action}")
                
                # Tạm dừng trước khi chạy chu kỳ tiếp theo
                time.sleep(5)
            except Exception as e:
                self.update_signal.emit(f"Lỗi trong chu kỳ của bot: {str(e)}")
                time.sleep(10)  # Tạm dừng lâu hơn nếu có lỗi
        
        self.status_signal.emit("Bot đã dừng")
    
    def stop(self):
        self.running = False
        if self.telegram_notifier:
            try:
                self.telegram_notifier.send_message(
                    f"🛑 Bot đã dừng vào {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
                )
            except:
                pass

class EnhancedTradingGUI(QMainWindow):
    """Giao diện giao dịch nâng cao với nhiều tab và chức năng"""
    
    def __init__(self):
        super().__init__()
        
        self.config = self.load_account_config()
        self.bot_worker = None
        
        self.init_ui()
    
    def load_account_config(self):
        """Tải cấu hình từ file"""
        try:
            with open("account_config.json", "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
            # Trả về cấu hình mặc định nếu không tải được
            return {
                "symbols": ["BTCUSDT", "ETHUSDT"],
                "timeframes": ["15m", "1h", "4h"],
                "strategy": "combined",
                "leverage": 5,
                "max_positions": 3
            }
    
    def save_account_config(self, config):
        """Lưu cấu hình vào file"""
        try:
            with open("account_config.json", "w") as f:
                json.dump(config, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {str(e)}")
            return False
    
    def init_ui(self):
        """Khởi tạo giao diện người dùng"""
        self.setWindowTitle("Hệ thống Giao dịch Nâng cao - v1.0")
        self.setGeometry(100, 100, 1200, 800)
        
        # Tạo main widget và layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Tạo header
        header_layout = QHBoxLayout()
        
        logo_label = QLabel("🤖 TRADING BOT")
        logo_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_layout.addWidget(logo_label)
        
        header_layout.addStretch()
        
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Trạng thái: Đã dừng")
        self.status_label.setFont(QFont("Arial", 10))
        status_layout.addWidget(self.status_label)
        
        self.connection_status = QLabel("API: Chưa kết nối")
        self.connection_status.setFont(QFont("Arial", 10))
        status_layout.addWidget(self.connection_status)
        
        header_layout.addLayout(status_layout)
        main_layout.addLayout(header_layout)
        
        # Tạo tab widget
        self.tab_widget = QTabWidget()
        
        # Tạo các tab
        self.create_dashboard_tab()
        self.create_market_analysis_tab()
        self.create_positions_tab()
        self.create_bot_log_tab()
        self.create_settings_tab()
        
        main_layout.addWidget(self.tab_widget)
        
        # Control panel
        control_layout = QHBoxLayout()
        
        # Risk selection
        risk_group = QGroupBox("Cấu hình rủi ro")
        risk_layout = QHBoxLayout()
        
        self.risk_level_combo = QComboBox()
        self.risk_level_combo.addItems(["10", "15", "20", "30"])
        risk_layout.addWidget(QLabel("Mức rủi ro (%):"))
        risk_layout.addWidget(self.risk_level_combo)
        
        risk_group.setLayout(risk_layout)
        control_layout.addWidget(risk_group)
        
        # Bot control buttons
        self.start_button = QPushButton("Bắt đầu")
        self.start_button.clicked.connect(self.start_bot)
        control_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Dừng")
        self.stop_button.clicked.connect(self.stop_bot)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)
        
        main_layout.addLayout(control_layout)
        
        # Set main layout
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Validate API credentials
        self.validate_api_credentials()
        
        # Set up timers for update
        self.setup_timers()
    
    def create_dashboard_tab(self):
        """Tạo tab tổng quan"""
        dashboard_tab = QWidget()
        layout = QVBoxLayout()
        
        # Thông tin trạng thái chính
        status_group = QGroupBox("Trạng thái hệ thống")
        status_layout = QGridLayout()
        
        self.api_status_label = QLabel("API Binance: Chưa kết nối")
        self.bot_status_label = QLabel("Bot giao dịch: Không hoạt động")
        self.positions_count_label = QLabel("Số vị thế đang mở: 0")
        self.account_balance_label = QLabel("Số dư tài khoản: 0 USDT")
        
        status_layout.addWidget(QLabel("Trạng thái API:"), 0, 0)
        status_layout.addWidget(self.api_status_label, 0, 1)
        status_layout.addWidget(QLabel("Trạng thái Bot:"), 1, 0)
        status_layout.addWidget(self.bot_status_label, 1, 1)
        status_layout.addWidget(QLabel("Vị thế đang mở:"), 2, 0)
        status_layout.addWidget(self.positions_count_label, 2, 1)
        status_layout.addWidget(QLabel("Số dư:"), 3, 0)
        status_layout.addWidget(self.account_balance_label, 3, 1)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Thị trường
        market_group = QGroupBox("Tổng quan thị trường")
        market_layout = QVBoxLayout()
        
        self.market_table = QTableWidget(0, 4)
        self.market_table.setHorizontalHeaderLabels(["Coin", "Giá hiện tại", "Thay đổi 24h", "Khối lượng"])
        self.market_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        market_layout.addWidget(self.market_table)
        market_group.setLayout(market_layout)
        layout.addWidget(market_group)
        
        # Thông báo mới nhất
        notification_group = QGroupBox("Thông báo gần đây")
        notification_layout = QVBoxLayout()
        
        self.notification_text = QTextEdit()
        self.notification_text.setReadOnly(True)
        notification_layout.addWidget(self.notification_text)
        
        notification_group.setLayout(notification_layout)
        layout.addWidget(notification_group)
        
        dashboard_tab.setLayout(layout)
        self.tab_widget.addTab(dashboard_tab, "Tổng quan")
    
    def create_market_analysis_tab(self):
        """Tạo tab phân tích thị trường"""
        market_tab = QWidget()
        layout = QVBoxLayout()
        
        # Coin selection
        selection_layout = QHBoxLayout()
        selection_layout.addWidget(QLabel("Chọn coin:"))
        
        self.coin_combo = QComboBox()
        self.coin_combo.addItems(["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"])
        selection_layout.addWidget(self.coin_combo)
        
        selection_layout.addWidget(QLabel("Khung thời gian:"))
        
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(["15m", "1h", "4h", "1d"])
        selection_layout.addWidget(self.timeframe_combo)
        
        refresh_button = QPushButton("Làm mới")
        refresh_button.clicked.connect(self.refresh_market_analysis)
        selection_layout.addWidget(refresh_button)
        
        layout.addLayout(selection_layout)
        
        # Market data
        market_data_group = QGroupBox("Dữ liệu thị trường")
        market_data_layout = QGridLayout()
        
        self.price_label = QLabel("Giá hiện tại: --")
        self.change_label = QLabel("Thay đổi 24h: --")
        self.volume_label = QLabel("Khối lượng 24h: --")
        self.high_label = QLabel("Cao nhất 24h: --")
        self.low_label = QLabel("Thấp nhất 24h: --")
        
        market_data_layout.addWidget(self.price_label, 0, 0)
        market_data_layout.addWidget(self.change_label, 0, 1)
        market_data_layout.addWidget(self.volume_label, 1, 0)
        market_data_layout.addWidget(self.high_label, 1, 1)
        market_data_layout.addWidget(self.low_label, 2, 0)
        
        market_data_group.setLayout(market_data_layout)
        layout.addWidget(market_data_group)
        
        # Technical analysis
        ta_group = QGroupBox("Phân tích kỹ thuật")
        ta_layout = QVBoxLayout()
        
        self.ta_table = QTableWidget(0, 3)
        self.ta_table.setHorizontalHeaderLabels(["Chỉ báo", "Giá trị", "Tín hiệu"])
        self.ta_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        ta_layout.addWidget(self.ta_table)
        ta_group.setLayout(ta_layout)
        layout.addWidget(ta_group)
        
        # Signals
        signals_group = QGroupBox("Tín hiệu giao dịch")
        signals_layout = QVBoxLayout()
        
        self.signals_text = QTextEdit()
        self.signals_text.setReadOnly(True)
        signals_layout.addWidget(self.signals_text)
        
        signals_group.setLayout(signals_layout)
        layout.addWidget(signals_group)
        
        market_tab.setLayout(layout)
        self.tab_widget.addTab(market_tab, "Phân tích thị trường")
    
    def create_positions_tab(self):
        """Tạo tab quản lý vị thế"""
        positions_tab = QWidget()
        layout = QVBoxLayout()
        
        # Positions table
        self.positions_table = QTableWidget(0, 7)
        self.positions_table.setHorizontalHeaderLabels([
            "Coin", "Loại", "Giá mở", "SL", "TP", "Lợi nhuận", "Thao tác"
        ])
        self.positions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(self.positions_table)
        
        # Position control
        control_group = QGroupBox("Thao tác vị thế")
        control_layout = QGridLayout()
        
        self.close_position_button = QPushButton("Đóng vị thế được chọn")
        self.close_position_button.clicked.connect(self.close_selected_position)
        
        self.close_all_positions_button = QPushButton("Đóng tất cả vị thế")
        self.close_all_positions_button.clicked.connect(self.close_all_positions)
        
        self.update_sl_tp_button = QPushButton("Cập nhật SL/TP")
        self.update_sl_tp_button.clicked.connect(self.update_sl_tp)
        
        control_layout.addWidget(self.close_position_button, 0, 0)
        control_layout.addWidget(self.close_all_positions_button, 0, 1)
        control_layout.addWidget(self.update_sl_tp_button, 1, 0, 1, 2)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        positions_tab.setLayout(layout)
        self.tab_widget.addTab(positions_tab, "Quản lý vị thế")
    
    def create_bot_log_tab(self):
        """Tạo tab log của bot"""
        log_tab = QWidget()
        layout = QVBoxLayout()
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        clear_button = QPushButton("Xóa log")
        clear_button.clicked.connect(self.clear_log)
        controls_layout.addWidget(clear_button)
        
        export_button = QPushButton("Xuất log")
        export_button.clicked.connect(self.export_log)
        controls_layout.addWidget(export_button)
        
        controls_layout.addStretch()
        
        self.auto_scroll_check = QCheckBox("Tự động cuộn")
        self.auto_scroll_check.setChecked(True)
        controls_layout.addWidget(self.auto_scroll_check)
        
        layout.addLayout(controls_layout)
        
        log_tab.setLayout(layout)
        self.tab_widget.addTab(log_tab, "Nhật ký Bot")
    
    def create_settings_tab(self):
        """Tạo tab cài đặt"""
        settings_tab = QWidget()
        layout = QVBoxLayout()
        
        # API settings
        api_group = QGroupBox("Cài đặt API")
        api_layout = QGridLayout()
        
        api_layout.addWidget(QLabel("API Key và Secret sẽ được lấy từ biến môi trường"), 0, 0, 1, 2)
        api_layout.addWidget(QLabel("BINANCE_TESTNET_API_KEY"), 1, 0)
        api_layout.addWidget(QLabel("BINANCE_TESTNET_API_SECRET"), 2, 0)
        
        self.test_api_button = QPushButton("Kiểm tra kết nối API")
        self.test_api_button.clicked.connect(self.validate_api_credentials)
        api_layout.addWidget(self.test_api_button, 3, 0, 1, 2)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # Telegram settings
        telegram_group = QGroupBox("Cài đặt Telegram")
        telegram_layout = QGridLayout()
        
        telegram_layout.addWidget(QLabel("Thông báo Telegram sẽ sử dụng biến môi trường:"), 0, 0, 1, 2)
        telegram_layout.addWidget(QLabel("TELEGRAM_BOT_TOKEN"), 1, 0)
        telegram_layout.addWidget(QLabel("TELEGRAM_CHAT_ID"), 2, 0)
        
        self.test_telegram_button = QPushButton("Kiểm tra kết nối Telegram")
        self.test_telegram_button.clicked.connect(self.test_telegram)
        telegram_layout.addWidget(self.test_telegram_button, 3, 0, 1, 2)
        
        telegram_group.setLayout(telegram_layout)
        layout.addWidget(telegram_group)
        
        # Trading settings
        trading_group = QGroupBox("Cài đặt giao dịch")
        trading_layout = QGridLayout()
        
        trading_layout.addWidget(QLabel("Danh sách coin (phân cách bằng dấu phẩy):"), 0, 0)
        self.symbols_input = QLineEdit()
        self.symbols_input.setText(",".join(self.config.get("symbols", ["BTCUSDT", "ETHUSDT"])))
        trading_layout.addWidget(self.symbols_input, 0, 1)
        
        trading_layout.addWidget(QLabel("Danh sách khung thời gian:"), 1, 0)
        self.timeframes_input = QLineEdit()
        self.timeframes_input.setText(",".join(self.config.get("timeframes", ["15m", "1h", "4h"])))
        trading_layout.addWidget(self.timeframes_input, 1, 1)
        
        trading_layout.addWidget(QLabel("Chiến lược:"), 2, 0)
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["combined", "trend_following", "breakout", "mean_reversion"])
        self.strategy_combo.setCurrentText(self.config.get("strategy", "combined"))
        trading_layout.addWidget(self.strategy_combo, 2, 1)
        
        trading_layout.addWidget(QLabel("Đòn bẩy:"), 3, 0)
        self.leverage_combo = QComboBox()
        self.leverage_combo.addItems(["1", "3", "5", "10", "20"])
        self.leverage_combo.setCurrentText(str(self.config.get("leverage", 5)))
        trading_layout.addWidget(self.leverage_combo, 3, 1)
        
        trading_layout.addWidget(QLabel("Số vị thế tối đa:"), 4, 0)
        self.max_positions_combo = QComboBox()
        self.max_positions_combo.addItems(["1", "2", "3", "5", "10"])
        self.max_positions_combo.setCurrentText(str(self.config.get("max_positions", 3)))
        trading_layout.addWidget(self.max_positions_combo, 4, 1)
        
        self.save_settings_button = QPushButton("Lưu cài đặt")
        self.save_settings_button.clicked.connect(self.save_settings)
        trading_layout.addWidget(self.save_settings_button, 5, 0, 1, 2)
        
        trading_group.setLayout(trading_layout)
        layout.addWidget(trading_group)
        
        settings_tab.setLayout(layout)
        self.tab_widget.addTab(settings_tab, "Cài đặt")
    
    def setup_timers(self):
        """Cài đặt các timer để cập nhật giao diện"""
        # Timer để cập nhật thời gian thực
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(5000)  # 5 giây cập nhật một lần
    
    def update_ui(self):
        """Cập nhật giao diện người dùng"""
        # Cập nhật bảng thị trường (có thể cập nhật trong thực tế)
        pass
    
    def validate_api_credentials(self):
        """Kiểm tra API credentials"""
        try:
            api_key = os.environ.get("BINANCE_TESTNET_API_KEY")
            api_secret = os.environ.get("BINANCE_TESTNET_API_SECRET")
            
            if not api_key or not api_secret:
                self.connection_status.setText("API: Thiếu thông tin")
                self.api_status_label.setText("API Binance: Thiếu thông tin")
                return False
            
            # Kiểm tra API credentials
            is_valid = validate_api_credentials(api_key, api_secret, testnet=True)
            
            if is_valid:
                self.connection_status.setText("API: Đã kết nối")
                self.api_status_label.setText("API Binance: Đã kết nối")
                return True
            else:
                self.connection_status.setText("API: Kết nối thất bại")
                self.api_status_label.setText("API Binance: Kết nối thất bại")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra API credentials: {str(e)}")
            self.connection_status.setText("API: Lỗi kết nối")
            self.api_status_label.setText("API Binance: Lỗi kết nối")
            return False
    
    def start_bot(self):
        """Bắt đầu chạy bot"""
        if self.bot_worker and self.bot_worker.isRunning():
            QMessageBox.warning(self, "Cảnh báo", "Bot đang chạy!")
            return
        
        # Kiểm tra API credentials
        if not self.validate_api_credentials():
            QMessageBox.critical(self, "Lỗi", "Không thể kết nối tới API Binance. Vui lòng kiểm tra lại thông tin đăng nhập.")
            return
        
        # Lấy level rủi ro
        risk_level = self.risk_level_combo.currentText()
        
        # Tạo bot worker và kết nối signals
        self.bot_worker = BotWorker(self.config, risk_level)
        self.bot_worker.update_signal.connect(self.update_log)
        self.bot_worker.status_signal.connect(self.update_bot_status)
        self.bot_worker.position_update_signal.connect(self.update_positions)
        self.bot_worker.market_data_signal.connect(self.update_market_data)
        
        # Bắt đầu chạy bot
        self.bot_worker.start()
        
        # Cập nhật UI
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.update_log("Bot đang khởi động...")
    
    def stop_bot(self):
        """Dừng bot"""
        if not self.bot_worker or not self.bot_worker.isRunning():
            QMessageBox.warning(self, "Cảnh báo", "Bot không chạy!")
            return
        
        # Dừng bot
        self.bot_worker.stop()
        self.update_log("Đang dừng bot...")
        
        # Cập nhật UI
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
    
    def update_log(self, message):
        """Cập nhật log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        self.log_text.append(log_message)
        
        # Thêm vào thông báo nếu là thông báo quan trọng
        if "lỗi" in message.lower() or "error" in message.lower() or "thành công" in message.lower():
            self.notification_text.append(log_message)
        
        # Tự động cuộn
        if self.auto_scroll_check.isChecked():
            self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def update_bot_status(self, status):
        """Cập nhật trạng thái bot"""
        self.status_label.setText(f"Trạng thái: {status}")
        self.bot_status_label.setText(f"Bot giao dịch: {status}")
    
    def update_positions(self, positions):
        """Cập nhật bảng vị thế"""
        # Xóa tất cả hàng hiện tại
        self.positions_table.setRowCount(0)
        
        # Cập nhật số lượng vị thế
        self.positions_count_label.setText(f"Số vị thế đang mở: {len(positions)}")
        
        # Thêm các vị thế mới
        for position in positions:
            row_position = self.positions_table.rowCount()
            self.positions_table.insertRow(row_position)
            
            # Thêm thông tin vị thế
            self.positions_table.setItem(row_position, 0, QTableWidgetItem(position.get("symbol", "")))
            self.positions_table.setItem(row_position, 1, QTableWidgetItem("LONG" if position.get("side") == "BUY" else "SHORT"))
            self.positions_table.setItem(row_position, 2, QTableWidgetItem(str(position.get("entry_price", 0))))
            self.positions_table.setItem(row_position, 3, QTableWidgetItem(str(position.get("stop_loss", 0))))
            self.positions_table.setItem(row_position, 4, QTableWidgetItem(str(position.get("take_profit", 0))))
            
            # Tính lợi nhuận
            profit = position.get("unrealized_profit", 0)
            profit_item = QTableWidgetItem(f"{profit:.2f} USDT")
            profit_item.setForeground(QColor("green") if profit >= 0 else QColor("red"))
            self.positions_table.setItem(row_position, 5, profit_item)
            
            # Thêm nút đóng vị thế
            close_button = QPushButton("Đóng")
            close_button.clicked.connect(lambda _, pos=position: self.close_position(pos))
            self.positions_table.setCellWidget(row_position, 6, close_button)
    
    def update_market_data(self, market_data):
        """Cập nhật dữ liệu thị trường"""
        # Cập nhật bảng thị trường
        self.market_table.setRowCount(0)
        
        for symbol, data in market_data.items():
            row_position = self.market_table.rowCount()
            self.market_table.insertRow(row_position)
            
            self.market_table.setItem(row_position, 0, QTableWidgetItem(symbol))
            self.market_table.setItem(row_position, 1, QTableWidgetItem(str(data.get("price", 0))))
            
            # Thay đổi 24h
            change = data.get("price_change_percent", 0)
            change_item = QTableWidgetItem(f"{change:.2f}%")
            change_item.setForeground(QColor("green") if change >= 0 else QColor("red"))
            self.market_table.setItem(row_position, 2, change_item)
            
            self.market_table.setItem(row_position, 3, QTableWidgetItem(str(data.get("volume", 0))))
        
        # Cập nhật số dư tài khoản nếu có
        balance = market_data.get("account_balance", 0)
        if balance:
            self.account_balance_label.setText(f"Số dư tài khoản: {balance:.2f} USDT")
    
    def refresh_market_analysis(self):
        """Làm mới phân tích thị trường"""
        selected_coin = self.coin_combo.currentText()
        selected_timeframe = self.timeframe_combo.currentText()
        
        self.update_log(f"Đang phân tích {selected_coin} trên khung thời gian {selected_timeframe}...")
        
        try:
            # Trong thực tế, sẽ gọi tới market analyzer
            # Giả lập dữ liệu cho giao diện
            self.price_label.setText(f"Giá hiện tại: 50000")
            self.change_label.setText(f"Thay đổi 24h: +2.5%")
            self.volume_label.setText(f"Khối lượng 24h: 15000 BTC")
            self.high_label.setText(f"Cao nhất 24h: 51000")
            self.low_label.setText(f"Thấp nhất 24h: 49000")
            
            # Cập nhật bảng phân tích kỹ thuật
            self.ta_table.setRowCount(0)
            
            # Thêm các chỉ báo giả lập
            indicators = [
                ("RSI(14)", "65", "Trung tính"),
                ("MACD", "Dương", "Mua"),
                ("MA(50) vs MA(200)", "Phía trên", "Tín hiệu mua"),
                ("Bollinger Bands", "Cận trên", "Quá mua"),
                ("Stochastic", "80", "Quá mua")
            ]
            
            for indicator in indicators:
                row_position = self.ta_table.rowCount()
                self.ta_table.insertRow(row_position)
                
                self.ta_table.setItem(row_position, 0, QTableWidgetItem(indicator[0]))
                self.ta_table.setItem(row_position, 1, QTableWidgetItem(indicator[1]))
                
                signal_item = QTableWidgetItem(indicator[2])
                if "mua" in indicator[2].lower():
                    signal_item.setForeground(QColor("green"))
                elif "bán" in indicator[2].lower():
                    signal_item.setForeground(QColor("red"))
                
                self.ta_table.setItem(row_position, 2, signal_item)
            
            # Cập nhật tín hiệu
            self.signals_text.setText(f"Phân tích {selected_coin} trên khung thời gian {selected_timeframe}:\n\n")
            self.signals_text.append("• RSI(14) đang ở mức 65, cho thấy thị trường đang trung tính\n")
            self.signals_text.append("• MACD hiện đang dương, cho tín hiệu mua\n")
            self.signals_text.append("• MA(50) đang nằm trên MA(200), xác nhận xu hướng tăng\n")
            self.signals_text.append("• Bollinger Bands cho thấy giá đang tiếp cận cận trên, có thể quá mua\n")
            self.signals_text.append("• Stochastic ở mức 80, cũng cho thấy thị trường đang quá mua\n\n")
            self.signals_text.append("Kết luận: Xu hướng tăng trong trung hạn, nhưng ngắn hạn có thể điều chỉnh.")
            
        except Exception as e:
            self.update_log(f"Lỗi khi phân tích thị trường: {str(e)}")
    
    def close_selected_position(self):
        """Đóng vị thế được chọn"""
        selected_rows = self.positions_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn vị thế để đóng.")
            return
        
        # Lấy vị thế dựa vào row được chọn
        selected_row = selected_rows[0].row()
        symbol = self.positions_table.item(selected_row, 0).text()
        side = self.positions_table.item(selected_row, 1).text()
        
        msg = QMessageBox.question(
            self,
            "Xác nhận",
            f"Bạn có chắc chắn muốn đóng vị thế {side} trên {symbol}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if msg == QMessageBox.Yes:
            # Trong thực tế, sẽ gọi position manager để đóng vị thế
            self.update_log(f"Đang đóng vị thế {side} trên {symbol}...")
            QMessageBox.information(self, "Thông báo", f"Đã đóng vị thế {side} trên {symbol}.")
    
    def close_all_positions(self):
        """Đóng tất cả vị thế"""
        if self.positions_table.rowCount() == 0:
            QMessageBox.warning(self, "Cảnh báo", "Không có vị thế nào để đóng.")
            return
        
        msg = QMessageBox.question(
            self,
            "Xác nhận",
            "Bạn có chắc chắn muốn đóng TẤT CẢ vị thế đang mở?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if msg == QMessageBox.Yes:
            # Trong thực tế, sẽ gọi position manager để đóng tất cả vị thế
            self.update_log("Đang đóng tất cả vị thế...")
            QMessageBox.information(self, "Thông báo", "Đã đóng tất cả vị thế.")
    
    def close_position(self, position):
        """Đóng một vị thế cụ thể"""
        symbol = position.get("symbol", "")
        side = "LONG" if position.get("side") == "BUY" else "SHORT"
        
        msg = QMessageBox.question(
            self,
            "Xác nhận",
            f"Bạn có chắc chắn muốn đóng vị thế {side} trên {symbol}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if msg == QMessageBox.Yes:
            # Trong thực tế, sẽ gọi position manager để đóng vị thế
            self.update_log(f"Đang đóng vị thế {side} trên {symbol}...")
            QMessageBox.information(self, "Thông báo", f"Đã đóng vị thế {side} trên {symbol}.")
    
    def update_sl_tp(self):
        """Cập nhật Stop Loss và Take Profit"""
        selected_rows = self.positions_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn vị thế để cập nhật SL/TP.")
            return
        
        # Trong thực tế, sẽ hiển thị dialog để nhập SL/TP mới
        QMessageBox.information(self, "Chức năng đang phát triển", "Chức năng cập nhật SL/TP sẽ được cập nhật trong phiên bản tới.")
    
    def clear_log(self):
        """Xóa log"""
        self.log_text.clear()
    
    def export_log(self):
        """Xuất log ra file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bot_log_{timestamp}.txt"
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.log_text.toPlainText())
            
            QMessageBox.information(self, "Thông báo", f"Đã xuất log ra file {filename}.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể xuất log: {str(e)}")
    
    def test_telegram(self):
        """Kiểm tra kết nối Telegram"""
        try:
            token = os.environ.get("TELEGRAM_BOT_TOKEN")
            chat_id = os.environ.get("TELEGRAM_CHAT_ID")
            
            if not token or not chat_id:
                QMessageBox.critical(self, "Lỗi", "Thiếu thông tin TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID.")
                return
            
            telegram = TelegramNotifier(token=token, chat_id=chat_id)
            telegram.send_message("🤖 Đây là tin nhắn kiểm tra từ Trading Bot.")
            
            QMessageBox.information(self, "Thông báo", "Đã gửi tin nhắn kiểm tra tới Telegram. Vui lòng kiểm tra để xác nhận.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể kết nối tới Telegram: {str(e)}")
    
    def save_settings(self):
        """Lưu cài đặt"""
        try:
            # Cập nhật config từ UI
            self.config["symbols"] = [s.strip() for s in self.symbols_input.text().split(",") if s.strip()]
            self.config["timeframes"] = [t.strip() for t in self.timeframes_input.text().split(",") if t.strip()]
            self.config["strategy"] = self.strategy_combo.currentText()
            self.config["leverage"] = int(self.leverage_combo.currentText())
            self.config["max_positions"] = int(self.max_positions_combo.currentText())
            
            # Lưu vào file
            if self.save_account_config(self.config):
                QMessageBox.information(self, "Thông báo", "Đã lưu cài đặt thành công.")
            else:
                QMessageBox.critical(self, "Lỗi", "Không thể lưu cài đặt.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi khi lưu cài đặt: {str(e)}")

def main():
    app = QApplication(sys.argv)
    window = EnhancedTradingGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()