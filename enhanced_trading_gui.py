#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module giao diện người dùng desktop nâng cao
"""

import os
import sys
import time
import json
import logging
import threading
from datetime import datetime

# PyQt5 imports
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QPushButton, QComboBox, QTextEdit, 
                           QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, 
                           QMessageBox, QProgressBar, QFrame, QGridLayout, QCheckBox, 
                           QSpinBox, QDoubleSpinBox, QSlider, QGroupBox, QRadioButton,
                           QSplitter, QSizePolicy, QFileDialog, QAction, QToolBar,
                           QStatusBar, QMenu, QMenuBar, QSystemTrayIcon, QScrollArea)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSettings, QSize, QPoint, QUrl
from PyQt5.QtGui import QIcon, QFont, QPixmap, QColor, QPalette, QDesktopServices, QTextCursor

# Logging setup
logger = logging.getLogger('trading_gui')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class UpdateThread(QThread):
    """Thread để cập nhật dữ liệu từ máy chủ"""
    update_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.running = True
    
    def run(self):
        while self.running:
            try:
                # Cập nhật tổng quan thị trường
                market_overview = self.app.market_analyzer.get_market_overview()
                
                # Cập nhật vị thế đang mở
                positions = self.app.position_manager.get_all_positions()
                
                # Chạy một chu kỳ của bot
                if self.app.trading_bot:
                    cycle_result = self.app.trading_bot.run_cycle()
                else:
                    cycle_result = {"actions": [], "errors": []}
                
                # Tổng hợp kết quả
                update_data = {
                    "market_overview": market_overview,
                    "positions": positions,
                    "cycle_result": cycle_result,
                    "timestamp": datetime.now()
                }
                
                # Gửi tín hiệu cập nhật
                self.update_signal.emit(update_data)
                
            except Exception as e:
                error_msg = f"Lỗi khi cập nhật dữ liệu: {str(e)}"
                logger.error(error_msg)
                self.error_signal.emit(error_msg)
            
            # Tạm dừng 10 giây
            time.sleep(10)
    
    def stop(self):
        self.running = False
        self.wait()

class TradingApp(QMainWindow):
    """Giao diện người dùng desktop nâng cao"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Crypto Trading Bot Desktop")
        self.setMinimumSize(1200, 800)
        
        # Khởi tạo các biến
        self.market_analyzer = None
        self.signal_generator = None
        self.position_manager = None
        self.risk_manager = None
        self.trading_bot = None
        self.telegram_notifier = None
        self.config = {}
        
        # Kiểm tra tệp cấu hình
        if os.path.exists("account_config.json"):
            try:
                with open("account_config.json", "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            except Exception as e:
                logger.error(f"Lỗi khi đọc tệp cấu hình: {str(e)}")
        
        # Thiết lập giao diện
        self.setup_ui()
        
        # Kiểm tra khả năng kết nối API
        self.check_api_connection()
        
        # Khởi động luồng cập nhật
        self.update_thread = None
    
    def setup_ui(self):
        """Thiết lập giao diện người dùng"""
        # Widget chính
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout chính
        main_layout = QVBoxLayout(central_widget)
        
        # Tạo thanh menu
        self.create_menu()
        
        # Tạo thanh công cụ
        self.create_toolbar()
        
        # Tab widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Tạo các tab
        self.create_dashboard_tab()
        self.create_positions_tab()
        self.create_market_tab()
        self.create_settings_tab()
        self.create_logs_tab()
        
        # Thanh trạng thái
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Sẵn sàng")
        
        # Thanh tiến trình (ẩn ban đầu)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
    
    def create_menu(self):
        """Tạo thanh menu"""
        # Menu chính
        menubar = self.menuBar()
        
        # Menu Tệp
        file_menu = menubar.addMenu("Tệp")
        
        # Hành động trong menu Tệp
        connect_action = QAction(QIcon("static/img/connect.png"), "Kết nối API", self)
        connect_action.triggered.connect(self.check_api_connection)
        file_menu.addAction(connect_action)
        
        reconnect_action = QAction(QIcon("static/img/reconnect.png"), "Kết nối lại", self)
        reconnect_action.triggered.connect(self.reconnect_api)
        file_menu.addAction(reconnect_action)
        
        file_menu.addSeparator()
        
        save_config_action = QAction(QIcon("static/img/save.png"), "Lưu cấu hình", self)
        save_config_action.triggered.connect(self.save_config)
        file_menu.addAction(save_config_action)
        
        load_config_action = QAction(QIcon("static/img/load.png"), "Tải cấu hình", self)
        load_config_action.triggered.connect(self.load_config)
        file_menu.addAction(load_config_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction(QIcon("static/img/exit.png"), "Thoát", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Menu Giao dịch
        trading_menu = menubar.addMenu("Giao dịch")
        
        start_bot_action = QAction(QIcon("static/img/start.png"), "Bắt đầu bot", self)
        start_bot_action.triggered.connect(self.start_bot)
        trading_menu.addAction(start_bot_action)
        
        stop_bot_action = QAction(QIcon("static/img/stop.png"), "Dừng bot", self)
        stop_bot_action.triggered.connect(self.stop_bot)
        trading_menu.addAction(stop_bot_action)
        
        trading_menu.addSeparator()
        
        market_order_action = QAction(QIcon("static/img/market.png"), "Lệnh thị trường", self)
        market_order_action.triggered.connect(self.show_market_order_dialog)
        trading_menu.addAction(market_order_action)
        
        limit_order_action = QAction(QIcon("static/img/limit.png"), "Lệnh giới hạn", self)
        limit_order_action.triggered.connect(self.show_limit_order_dialog)
        trading_menu.addAction(limit_order_action)
        
        trading_menu.addSeparator()
        
        close_position_action = QAction(QIcon("static/img/close.png"), "Đóng vị thế", self)
        close_position_action.triggered.connect(self.show_close_position_dialog)
        trading_menu.addAction(close_position_action)
        
        # Menu Công cụ
        tools_menu = menubar.addMenu("Công cụ")
        
        trailing_stop_action = QAction(QIcon("static/img/trailing.png"), "Trailing Stop", self)
        trailing_stop_action.triggered.connect(self.show_trailing_stop_dialog)
        tools_menu.addAction(trailing_stop_action)
        
        partial_tp_action = QAction(QIcon("static/img/partial.png"), "Chốt lời một phần", self)
        partial_tp_action.triggered.connect(self.show_partial_tp_dialog)
        tools_menu.addAction(partial_tp_action)
        
        tools_menu.addSeparator()
        
        risk_calculator_action = QAction(QIcon("static/img/calculator.png"), "Tính toán rủi ro", self)
        risk_calculator_action.triggered.connect(self.show_risk_calculator)
        tools_menu.addAction(risk_calculator_action)
        
        position_size_action = QAction(QIcon("static/img/size.png"), "Tính kích thước vị thế", self)
        position_size_action.triggered.connect(self.show_position_size_calculator)
        tools_menu.addAction(position_size_action)
        
        # Menu Trợ giúp
        help_menu = menubar.addMenu("Trợ giúp")
        
        about_action = QAction(QIcon("static/img/about.png"), "Giới thiệu", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        doc_action = QAction(QIcon("static/img/doc.png"), "Tài liệu", self)
        doc_action.triggered.connect(self.open_documentation)
        help_menu.addAction(doc_action)
        
        update_action = QAction(QIcon("static/img/update.png"), "Kiểm tra cập nhật", self)
        update_action.triggered.connect(self.check_updates)
        help_menu.addAction(update_action)
    
    def create_toolbar(self):
        """Tạo thanh công cụ"""
        toolbar = QToolBar("Thanh công cụ chính")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # Thêm các hành động vào thanh công cụ
        connect_action = QAction(QIcon("static/img/connect.png"), "Kết nối API", self)
        connect_action.triggered.connect(self.check_api_connection)
        toolbar.addAction(connect_action)
        
        toolbar.addSeparator()
        
        start_bot_action = QAction(QIcon("static/img/start.png"), "Bắt đầu bot", self)
        start_bot_action.triggered.connect(self.start_bot)
        toolbar.addAction(start_bot_action)
        
        stop_bot_action = QAction(QIcon("static/img/stop.png"), "Dừng bot", self)
        stop_bot_action.triggered.connect(self.stop_bot)
        toolbar.addAction(stop_bot_action)
        
        toolbar.addSeparator()
        
        market_action = QAction(QIcon("static/img/market.png"), "Lệnh thị trường", self)
        market_action.triggered.connect(self.show_market_order_dialog)
        toolbar.addAction(market_action)
        
        close_action = QAction(QIcon("static/img/close.png"), "Đóng vị thế", self)
        close_action.triggered.connect(self.show_close_position_dialog)
        toolbar.addAction(close_action)
        
        toolbar.addSeparator()
        
        setting_action = QAction(QIcon("static/img/settings.png"), "Cài đặt", self)
        setting_action.triggered.connect(lambda: self.tabs.setCurrentIndex(3))  # Chuyển đến tab Settings
        toolbar.addAction(setting_action)
    
    def create_dashboard_tab(self):
        """Tạo tab Tổng quan"""
        dashboard_tab = QWidget()
        layout = QVBoxLayout(dashboard_tab)
        
        # Header
        header_layout = QHBoxLayout()
        self.account_balance_label = QLabel("Số dư tài khoản: 0 USDT")
        self.account_balance_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(self.account_balance_label)
        
        self.pnl_label = QLabel("Lợi nhuận: 0 USDT")
        self.pnl_label.setFont(QFont("Arial", 14))
        header_layout.addWidget(self.pnl_label)
        
        header_layout.addStretch()
        
        self.risk_level_label = QLabel(f"Mức rủi ro: {self.config.get('risk_level', 10)}%")
        self.risk_level_label.setFont(QFont("Arial", 14))
        header_layout.addWidget(self.risk_level_label)
        
        layout.addLayout(header_layout)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # Main content
        content_layout = QHBoxLayout()
        
        # Left panel - Portfolio
        portfolio_group = QGroupBox("Danh mục đầu tư")
        portfolio_layout = QVBoxLayout(portfolio_group)
        
        self.positions_table = QTableWidget(0, 5)
        self.positions_table.setHorizontalHeaderLabels(["Cặp", "Vị thế", "Số lượng", "Giá vào", "Lợi nhuận"])
        self.positions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        portfolio_layout.addWidget(self.positions_table)
        
        content_layout.addWidget(portfolio_group, 3)
        
        # Right panel - Market
        market_group = QGroupBox("Thị trường")
        market_layout = QVBoxLayout(market_group)
        
        self.market_table = QTableWidget(0, 5)
        self.market_table.setHorizontalHeaderLabels(["Cặp", "Giá", "Thay đổi 24h", "Khối lượng", "Tín hiệu"])
        self.market_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        market_layout.addWidget(self.market_table)
        
        content_layout.addWidget(market_group, 2)
        
        layout.addLayout(content_layout, 3)
        
        # Bottom panel - Bot Actions
        actions_group = QGroupBox("Hành động của Bot")
        actions_layout = QVBoxLayout(actions_group)
        
        self.bot_log = QTextEdit()
        self.bot_log.setReadOnly(True)
        actions_layout.addWidget(self.bot_log)
        
        layout.addWidget(actions_group, 1)
        
        # Bottom buttons
        buttons_layout = QHBoxLayout()
        
        start_button = QPushButton("Bắt đầu Bot")
        start_button.clicked.connect(self.start_bot)
        buttons_layout.addWidget(start_button)
        
        stop_button = QPushButton("Dừng Bot")
        stop_button.clicked.connect(self.stop_bot)
        buttons_layout.addWidget(stop_button)
        
        buttons_layout.addStretch()
        
        telegram_button = QPushButton("Gửi thông báo Telegram")
        telegram_button.clicked.connect(self.send_telegram_notification)
        buttons_layout.addWidget(telegram_button)
        
        layout.addLayout(buttons_layout)
        
        # Add to tabs
        self.tabs.addTab(dashboard_tab, "Tổng quan")
    
    def create_positions_tab(self):
        """Tạo tab Vị thế"""
        positions_tab = QWidget()
        layout = QVBoxLayout(positions_tab)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Quản lý Vị thế"))
        header_layout.addStretch()
        
        refresh_button = QPushButton("Làm mới")
        refresh_button.clicked.connect(self.refresh_positions)
        header_layout.addWidget(refresh_button)
        
        layout.addLayout(header_layout)
        
        # Positions table
        self.detailed_positions_table = QTableWidget(0, 8)
        self.detailed_positions_table.setHorizontalHeaderLabels([
            "Cặp", "Vị thế", "Số lượng", "Giá vào", "Giá hiện tại", 
            "Stop Loss", "Take Profit", "Lợi nhuận"
        ])
        self.detailed_positions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.detailed_positions_table)
        
        # Position actions
        actions_layout = QHBoxLayout()
        
        close_button = QPushButton("Đóng vị thế")
        close_button.clicked.connect(self.close_selected_position)
        actions_layout.addWidget(close_button)
        
        edit_sl_button = QPushButton("Chỉnh sửa SL")
        edit_sl_button.clicked.connect(self.edit_sl)
        actions_layout.addWidget(edit_sl_button)
        
        edit_tp_button = QPushButton("Chỉnh sửa TP")
        edit_tp_button.clicked.connect(self.edit_tp)
        actions_layout.addWidget(edit_tp_button)
        
        add_trailing_button = QPushButton("Thêm Trailing Stop")
        add_trailing_button.clicked.connect(self.add_trailing_stop)
        actions_layout.addWidget(add_trailing_button)
        
        partial_tp_button = QPushButton("Chốt lời một phần")
        partial_tp_button.clicked.connect(self.show_partial_tp_dialog)
        actions_layout.addWidget(partial_tp_button)
        
        layout.addLayout(actions_layout)
        
        # Add to tabs
        self.tabs.addTab(positions_tab, "Vị thế")
    
    def create_market_tab(self):
        """Tạo tab Thị trường"""
        market_tab = QWidget()
        layout = QVBoxLayout(market_tab)
        
        # Market controls
        controls_layout = QHBoxLayout()
        
        controls_layout.addWidget(QLabel("Cặp:"))
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "DOGEUSDT"])
        self.symbol_combo.setCurrentText(self.config.get("symbols", ["BTCUSDT"])[0])
        self.symbol_combo.currentTextChanged.connect(self.update_market_analysis)
        controls_layout.addWidget(self.symbol_combo)
        
        controls_layout.addWidget(QLabel("Khung thời gian:"))
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(["1m", "5m", "15m", "1h", "4h", "1d"])
        self.timeframe_combo.setCurrentText(self.config.get("timeframes", ["1h"])[0])
        self.timeframe_combo.currentTextChanged.connect(self.update_market_analysis)
        controls_layout.addWidget(self.timeframe_combo)
        
        refresh_button = QPushButton("Phân tích")
        refresh_button.clicked.connect(self.update_market_analysis)
        controls_layout.addWidget(refresh_button)
        
        order_button = QPushButton("Đặt lệnh")
        order_button.clicked.connect(self.show_market_order_dialog)
        controls_layout.addWidget(order_button)
        
        layout.addLayout(controls_layout)
        
        # Market content
        content_layout = QHBoxLayout()
        
        # Left panel - Market data
        market_data_group = QGroupBox("Dữ liệu thị trường")
        market_data_layout = QVBoxLayout(market_data_group)
        
        self.market_data_text = QTextEdit()
        self.market_data_text.setReadOnly(True)
        market_data_layout.addWidget(self.market_data_text)
        
        content_layout.addWidget(market_data_group, 1)
        
        # Right panel - Technical analysis
        ta_group = QGroupBox("Phân tích kỹ thuật")
        ta_layout = QVBoxLayout(ta_group)
        
        self.ta_text = QTextEdit()
        self.ta_text.setReadOnly(True)
        ta_layout.addWidget(self.ta_text)
        
        content_layout.addWidget(ta_group, 1)
        
        layout.addLayout(content_layout)
        
        # Bottom panel - Signals
        signals_group = QGroupBox("Tín hiệu giao dịch")
        signals_layout = QVBoxLayout(signals_group)
        
        self.signals_table = QTableWidget(0, 7)
        self.signals_table.setHorizontalHeaderLabels([
            "Cặp", "Khung thời gian", "Tín hiệu", "Giá vào", "Stop Loss", 
            "Take Profit", "Tin cậy"
        ])
        self.signals_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        signals_layout.addWidget(self.signals_table)
        
        # Signal actions
        signal_actions_layout = QHBoxLayout()
        
        execute_signal_button = QPushButton("Thực thi tín hiệu")
        execute_signal_button.clicked.connect(self.execute_selected_signal)
        signal_actions_layout.addWidget(execute_signal_button)
        
        ignore_signal_button = QPushButton("Bỏ qua tín hiệu")
        ignore_signal_button.clicked.connect(self.ignore_selected_signal)
        signal_actions_layout.addWidget(ignore_signal_button)
        
        signals_layout.addLayout(signal_actions_layout)
        
        layout.addWidget(signals_group)
        
        # Add to tabs
        self.tabs.addTab(market_tab, "Thị trường")
    
    def create_settings_tab(self):
        """Tạo tab Cài đặt"""
        settings_tab = QWidget()
        layout = QVBoxLayout(settings_tab)
        
        # Create a scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # API Settings
        api_group = QGroupBox("Cài đặt API")
        api_layout = QGridLayout(api_group)
        
        api_layout.addWidget(QLabel("Testnet:"), 0, 0)
        self.testnet_checkbox = QCheckBox()
        self.testnet_checkbox.setChecked(self.config.get("testnet", True))
        api_layout.addWidget(self.testnet_checkbox, 0, 1)
        
        api_layout.addWidget(QLabel("API Key:"), 1, 0)
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("API Key Binance")
        api_layout.addWidget(self.api_key_input, 1, 1)
        
        api_layout.addWidget(QLabel("API Secret:"), 2, 0)
        self.api_secret_input = QLineEdit()
        self.api_secret_input.setEchoMode(QLineEdit.Password)
        self.api_secret_input.setPlaceholderText("API Secret Binance")
        api_layout.addWidget(self.api_secret_input, 2, 1)
        
        api_test_button = QPushButton("Kiểm tra API")
        api_test_button.clicked.connect(self.check_api_connection)
        api_layout.addWidget(api_test_button, 3, 1)
        
        scroll_layout.addWidget(api_group)
        
        # Telegram Settings
        telegram_group = QGroupBox("Cài đặt Telegram")
        telegram_layout = QGridLayout(telegram_group)
        
        telegram_layout.addWidget(QLabel("Bật thông báo:"), 0, 0)
        self.telegram_enabled_checkbox = QCheckBox()
        self.telegram_enabled_checkbox.setChecked(self.config.get("telegram_notifications", False))
        telegram_layout.addWidget(self.telegram_enabled_checkbox, 0, 1)
        
        telegram_layout.addWidget(QLabel("Bot Token:"), 1, 0)
        self.telegram_token_input = QLineEdit()
        self.telegram_token_input.setEchoMode(QLineEdit.Password)
        self.telegram_token_input.setPlaceholderText("Telegram Bot Token")
        telegram_layout.addWidget(self.telegram_token_input, 1, 1)
        
        telegram_layout.addWidget(QLabel("Chat ID:"), 2, 0)
        self.telegram_chat_id_input = QLineEdit()
        self.telegram_chat_id_input.setPlaceholderText("Telegram Chat ID")
        telegram_layout.addWidget(self.telegram_chat_id_input, 2, 1)
        
        telegram_test_button = QPushButton("Kiểm tra Telegram")
        telegram_test_button.clicked.connect(self.test_telegram)
        telegram_layout.addWidget(telegram_test_button, 3, 1)
        
        scroll_layout.addWidget(telegram_group)
        
        # Trading Settings
        trading_group = QGroupBox("Cài đặt Giao dịch")
        trading_layout = QGridLayout(trading_group)
        
        trading_layout.addWidget(QLabel("Mức độ rủi ro:"), 0, 0)
        self.risk_level_combo = QComboBox()
        self.risk_level_combo.addItems(["10%", "15%", "20%", "30%"])
        current_risk = str(self.config.get("risk_level", 10)) + "%"
        current_index = self.risk_level_combo.findText(current_risk)
        self.risk_level_combo.setCurrentIndex(current_index if current_index >= 0 else 0)
        trading_layout.addWidget(self.risk_level_combo, 0, 1)
        
        trading_layout.addWidget(QLabel("Cặp tiền:"), 1, 0)
        self.symbols_input = QLineEdit()
        self.symbols_input.setText(", ".join(self.config.get("symbols", ["BTCUSDT", "ETHUSDT"])))
        trading_layout.addWidget(self.symbols_input, 1, 1)
        
        trading_layout.addWidget(QLabel("Khung thời gian:"), 2, 0)
        self.timeframes_input = QLineEdit()
        self.timeframes_input.setText(", ".join(self.config.get("timeframes", ["1h", "4h"])))
        trading_layout.addWidget(self.timeframes_input, 2, 1)
        
        trading_layout.addWidget(QLabel("Trailing Stop:"), 3, 0)
        self.trailing_stop_checkbox = QCheckBox()
        self.trailing_stop_checkbox.setChecked(self.config.get("auto_trailing_stop", True))
        trading_layout.addWidget(self.trailing_stop_checkbox, 3, 1)
        
        scroll_layout.addWidget(trading_group)
        
        # Notification Settings
        notification_group = QGroupBox("Cài đặt Thông báo")
        notification_layout = QGridLayout(notification_group)
        
        notification_layout.addWidget(QLabel("Giờ không làm phiền:"), 0, 0)
        self.quiet_hours_checkbox = QCheckBox()
        self.quiet_hours_checkbox.setChecked(self.config.get("quiet_hours", {}).get("enabled", False))
        notification_layout.addWidget(self.quiet_hours_checkbox, 0, 1)
        
        notification_layout.addWidget(QLabel("Bắt đầu:"), 1, 0)
        self.quiet_start_input = QLineEdit()
        self.quiet_start_input.setText(self.config.get("quiet_hours", {}).get("start", "22:00"))
        notification_layout.addWidget(self.quiet_start_input, 1, 1)
        
        notification_layout.addWidget(QLabel("Kết thúc:"), 2, 0)
        self.quiet_end_input = QLineEdit()
        self.quiet_end_input.setText(self.config.get("quiet_hours", {}).get("end", "07:00"))
        notification_layout.addWidget(self.quiet_end_input, 2, 1)
        
        scroll_layout.addWidget(notification_group)
        
        # Auto Update Settings
        update_group = QGroupBox("Cài đặt Tự động Cập nhật")
        update_layout = QGridLayout(update_group)
        
        update_layout.addWidget(QLabel("Tự động cập nhật:"), 0, 0)
        self.auto_update_checkbox = QCheckBox()
        self.auto_update_checkbox.setChecked(self.config.get("auto_update", True))
        update_layout.addWidget(self.auto_update_checkbox, 0, 1)
        
        update_layout.addWidget(QLabel("Tần suất kiểm tra (giờ):"), 1, 0)
        self.update_frequency_spin = QSpinBox()
        self.update_frequency_spin.setRange(1, 24)
        self.update_frequency_spin.setValue(self.config.get("update_frequency", 24))
        update_layout.addWidget(self.update_frequency_spin, 1, 1)
        
        check_update_button = QPushButton("Kiểm tra cập nhật ngay")
        check_update_button.clicked.connect(self.check_updates)
        update_layout.addWidget(check_update_button, 2, 1)
        
        scroll_layout.addWidget(update_group)
        
        # Add buttons at the bottom
        buttons_layout = QHBoxLayout()
        
        save_button = QPushButton("Lưu cài đặt")
        save_button.clicked.connect(self.save_settings)
        buttons_layout.addWidget(save_button)
        
        defaults_button = QPushButton("Khôi phục mặc định")
        defaults_button.clicked.connect(self.reset_settings)
        buttons_layout.addWidget(defaults_button)
        
        scroll_layout.addLayout(buttons_layout)
        
        # Set up scroll area
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # Add to tabs
        self.tabs.addTab(settings_tab, "Cài đặt")
    
    def create_logs_tab(self):
        """Tạo tab Nhật ký"""
        logs_tab = QWidget()
        layout = QVBoxLayout(logs_tab)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        controls_layout.addWidget(QLabel("Loại nhật ký:"))
        self.log_type_combo = QComboBox()
        self.log_type_combo.addItems(["Bot", "Giao dịch", "Thị trường", "Lỗi", "Tất cả"])
        self.log_type_combo.currentTextChanged.connect(self.load_logs)
        controls_layout.addWidget(self.log_type_combo)
        
        refresh_logs_button = QPushButton("Làm mới")
        refresh_logs_button.clicked.connect(self.load_logs)
        controls_layout.addWidget(refresh_logs_button)
        
        clear_logs_button = QPushButton("Xóa nhật ký")
        clear_logs_button.clicked.connect(self.clear_logs)
        controls_layout.addWidget(clear_logs_button)
        
        layout.addLayout(controls_layout)
        
        # Log viewer
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setFont(QFont("Courier", 10))
        layout.addWidget(self.log_viewer)
        
        # Add to tabs
        self.tabs.addTab(logs_tab, "Nhật ký")
    
    def check_api_connection(self):
        """Kiểm tra kết nối API"""
        self.status_bar.showMessage("Đang kiểm tra kết nối API...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(30)
        
        try:
            # Thử nhập các module cần thiết
            from market_analyzer import MarketAnalyzer
            from signal_generator import SignalGenerator
            from position_manager import PositionManager
            from risk_manager import RiskManager
            from trading_bot import TradingBot
            from advanced_telegram_notifier import TelegramNotifier
            
            # Lấy API key từ cấu hình hoặc từ biến môi trường
            api_key = os.environ.get("BINANCE_TESTNET_API_KEY")
            api_secret = os.environ.get("BINANCE_TESTNET_API_SECRET")
            
            self.progress_bar.setValue(50)
            
            # Kiểm tra kết nối API
            self.market_analyzer = MarketAnalyzer(testnet=True)
            
            market_check = self.market_analyzer.get_market_overview()
            if market_check["status"] != "success":
                raise Exception(f"Lỗi kết nối: {market_check.get('message', 'Không rõ lỗi')}")
            
            self.progress_bar.setValue(70)
            
            # Khởi tạo các thành phần khác
            self.signal_generator = SignalGenerator(self.market_analyzer, self.config)
            
            risk_level = self.config.get("risk_level", 10)
            risk_config_file = f"risk_configs/risk_level_{risk_level}.json"
            risk_config = {}
            
            if os.path.exists(risk_config_file):
                with open(risk_config_file, "r") as f:
                    risk_config = json.load(f)
            
            self.position_manager = PositionManager(testnet=True, risk_config=risk_config)
            self.risk_manager = RiskManager(self.position_manager, risk_config)
            
            self.progress_bar.setValue(90)
            
            # Kiểm tra Telegram nếu được bật
            telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
            telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
            
            if self.config.get("telegram_notifications", False) and telegram_token and telegram_chat_id:
                self.telegram_notifier = TelegramNotifier()
                
                # Gửi thông báo kết nối thành công
                self.telegram_notifier.send_message("Kết nối thành công với Bot Trading")
            
            # Khởi tạo bot
            self.trading_bot = TradingBot(
                market_analyzer=self.market_analyzer,
                signal_generator=self.signal_generator,
                position_manager=self.position_manager,
                risk_manager=self.risk_manager,
                telegram_notifier=self.telegram_notifier,
                config=self.config
            )
            
            self.progress_bar.setValue(100)
            self.status_bar.showMessage("Kết nối API thành công", 3000)
            
            # Hiển thị thông báo thành công
            QMessageBox.information(self, "Kết nối thành công", "Đã kết nối thành công đến API Binance Testnet")
            
            # Khởi động luồng cập nhật
            self.start_update_thread()
            
            # Cập nhật giao diện
            self.update_dashboard()
            
        except Exception as e:
            error_msg = f"Lỗi kết nối API: {str(e)}"
            logger.error(error_msg)
            self.status_bar.showMessage("Kết nối API thất bại", 3000)
            self.progress_bar.setVisible(False)
            
            # Hiển thị thông báo lỗi
            QMessageBox.critical(self, "Lỗi kết nối", f"Không thể kết nối đến API: {str(e)}")
    
    def reconnect_api(self):
        """Kết nối lại API"""
        if self.update_thread:
            self.update_thread.stop()
            self.update_thread = None
        
        self.check_api_connection()
    
    def start_update_thread(self):
        """Khởi động luồng cập nhật"""
        if self.trading_bot and not self.update_thread:
            self.update_thread = UpdateThread(self)
            self.update_thread.update_signal.connect(self.update_from_thread)
            self.update_thread.error_signal.connect(self.show_error)
            self.update_thread.start()
    
    def update_from_thread(self, data):
        """Cập nhật dữ liệu từ luồng"""
        try:
            # Cập nhật tổng quan
            market_overview = data.get("market_overview", {"status": "error"})
            positions = data.get("positions", [])
            cycle_result = data.get("cycle_result", {"actions": [], "errors": []})
            
            # Cập nhật dashboard
            if market_overview["status"] == "success":
                self.update_market_tables(market_overview["data"])
            
            if positions:
                self.update_position_tables(positions)
            
            # Cập nhật log bot
            for action in cycle_result.get("actions", []):
                self.bot_log.append(f"{datetime.now().strftime('%H:%M:%S')} - {action}")
            
            for error in cycle_result.get("errors", []):
                self.bot_log.append(f"{datetime.now().strftime('%H:%M:%S')} - Lỗi: {error}")
                
            # Đảm bảo cuộn xuống cuối
            self.bot_log.moveCursor(QTextCursor.End)
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật từ luồng: {str(e)}")
    
    def show_error(self, error_msg):
        """Hiển thị thông báo lỗi"""
        self.status_bar.showMessage(error_msg, 5000)
        logger.error(error_msg)
        self.bot_log.append(f"{datetime.now().strftime('%H:%M:%S')} - Lỗi: {error_msg}")
    
    def update_dashboard(self):
        """Cập nhật tab Tổng quan"""
        if not self.market_analyzer:
            return
        
        try:
            # Lấy thông tin tài khoản
            account_info = self.market_analyzer.get_account_info()
            if account_info["status"] == "success":
                balance = account_info["account"]["balance"]
                pnl = account_info["account"].get("unrealized_pnl", 0)
                
                self.account_balance_label.setText(f"Số dư tài khoản: {balance:.2f} USDT")
                self.pnl_label.setText(f"Lợi nhuận: {pnl:.2f} USDT")
                
                # Đặt màu cho PnL
                if pnl > 0:
                    self.pnl_label.setStyleSheet("color: green;")
                elif pnl < 0:
                    self.pnl_label.setStyleSheet("color: red;")
                else:
                    self.pnl_label.setStyleSheet("")
            
            # Lấy thông tin thị trường
            market_overview = self.market_analyzer.get_market_overview()
            if market_overview["status"] == "success":
                self.update_market_tables(market_overview["data"])
            
            # Lấy vị thế đang mở
            positions = self.position_manager.get_all_positions()
            self.update_position_tables(positions)
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật dashboard: {str(e)}")
    
    def update_market_tables(self, market_data):
        """Cập nhật bảng thị trường"""
        try:
            # Cập nhật bảng thị trường trong tab Tổng quan
            self.market_table.setRowCount(len(market_data))
            
            for i, item in enumerate(market_data):
                # Lấy dữ liệu
                symbol = item["symbol"]
                price = item["price"]
                change_24h = item["change_24h"]
                volume = item["volume"]
                high_24h = item["high_24h"]
                low_24h = item["low_24h"]
                
                # Tạo các mục trong bảng
                self.market_table.setItem(i, 0, QTableWidgetItem(symbol))
                self.market_table.setItem(i, 1, QTableWidgetItem(f"{price:.2f}"))
                
                # Đặt màu cho thay đổi 24h
                change_item = QTableWidgetItem(f"{change_24h:.2f}%")
                if change_24h > 0:
                    change_item.setForeground(QColor("green"))
                elif change_24h < 0:
                    change_item.setForeground(QColor("red"))
                self.market_table.setItem(i, 2, change_item)
                
                self.market_table.setItem(i, 3, QTableWidgetItem(f"{volume:.2f}"))
                
                # Tạo tín hiệu dựa trên biến động giá
                signal = "Trung lập"
                if change_24h > 3:
                    signal = "Mua mạnh"
                elif change_24h > 1:
                    signal = "Mua"
                elif change_24h < -3:
                    signal = "Bán mạnh"
                elif change_24h < -1:
                    signal = "Bán"
                
                signal_item = QTableWidgetItem(signal)
                if "Mua" in signal:
                    signal_item.setForeground(QColor("green"))
                elif "Bán" in signal:
                    signal_item.setForeground(QColor("red"))
                self.market_table.setItem(i, 4, signal_item)
                
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật bảng thị trường: {str(e)}")
    
    def update_position_tables(self, positions):
        """Cập nhật bảng vị thế"""
        try:
            # Cập nhật bảng vị thế trong tab Tổng quan
            self.positions_table.setRowCount(len(positions))
            self.detailed_positions_table.setRowCount(len(positions))
            
            for i, position in enumerate(positions):
                # Lấy dữ liệu
                symbol = position["symbol"]
                side = position["side"]
                quantity = position["size"]
                entry_price = position["entry_price"]
                current_price = position["mark_price"]
                profit = position["unrealized_pnl"]
                profit_percent = position["profit_percent"]
                stop_loss = position.get("stop_loss", 0)
                take_profit = position.get("take_profit", 0)
                
                # Cập nhật bảng tổng quan
                self.positions_table.setItem(i, 0, QTableWidgetItem(symbol))
                self.positions_table.setItem(i, 1, QTableWidgetItem(side))
                self.positions_table.setItem(i, 2, QTableWidgetItem(f"{quantity:.4f}"))
                self.positions_table.setItem(i, 3, QTableWidgetItem(f"{entry_price:.2f}"))
                
                # Đặt màu cho lợi nhuận
                profit_item = QTableWidgetItem(f"{profit:.2f} ({profit_percent:.2f}%)")
                if profit > 0:
                    profit_item.setForeground(QColor("green"))
                elif profit < 0:
                    profit_item.setForeground(QColor("red"))
                self.positions_table.setItem(i, 4, profit_item)
                
                # Cập nhật bảng chi tiết
                self.detailed_positions_table.setItem(i, 0, QTableWidgetItem(symbol))
                
                side_item = QTableWidgetItem(side)
                if side == "LONG":
                    side_item.setForeground(QColor("green"))
                else:
                    side_item.setForeground(QColor("red"))
                self.detailed_positions_table.setItem(i, 1, side_item)
                
                self.detailed_positions_table.setItem(i, 2, QTableWidgetItem(f"{quantity:.4f}"))
                self.detailed_positions_table.setItem(i, 3, QTableWidgetItem(f"{entry_price:.2f}"))
                self.detailed_positions_table.setItem(i, 4, QTableWidgetItem(f"{current_price:.2f}"))
                self.detailed_positions_table.setItem(i, 5, QTableWidgetItem(f"{stop_loss:.2f}"))
                self.detailed_positions_table.setItem(i, 6, QTableWidgetItem(f"{take_profit:.2f}"))
                
                # Đặt màu cho lợi nhuận chi tiết
                detailed_profit_item = QTableWidgetItem(f"{profit:.2f} ({profit_percent:.2f}%)")
                if profit > 0:
                    detailed_profit_item.setForeground(QColor("green"))
                elif profit < 0:
                    detailed_profit_item.setForeground(QColor("red"))
                self.detailed_positions_table.setItem(i, 7, detailed_profit_item)
                
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật bảng vị thế: {str(e)}")
    
    def start_bot(self):
        """Bắt đầu bot giao dịch"""
        if not self.trading_bot:
            QMessageBox.warning(self, "Lỗi", "Chưa kết nối được đến API. Vui lòng kết nối trước khi bắt đầu bot.")
            return
        
        reply = QMessageBox.question(self, "Xác nhận", 
                                    "Bạn có chắc muốn bắt đầu bot giao dịch?\n\nBot sẽ tự động thực hiện giao dịch dựa trên cài đặt của bạn.",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Bắt đầu luồng cập nhật nếu chưa chạy
            if not self.update_thread:
                self.start_update_thread()
            
            self.status_bar.showMessage("Bot đã bắt đầu chạy", 3000)
            self.bot_log.append(f"{datetime.now().strftime('%H:%M:%S')} - Bot đã bắt đầu chạy")
            
            # Gửi thông báo Telegram
            if self.telegram_notifier:
                self.telegram_notifier.send_message("Bot giao dịch đã được bật")
    
    def stop_bot(self):
        """Dừng bot giao dịch"""
        if not self.update_thread:
            QMessageBox.warning(self, "Lỗi", "Bot chưa được bắt đầu.")
            return
        
        reply = QMessageBox.question(self, "Xác nhận", 
                                    "Bạn có chắc muốn dừng bot giao dịch?\n\nBot sẽ không thực hiện giao dịch mới, nhưng các vị thế hiện tại vẫn được giữ.",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Dừng luồng cập nhật
            self.update_thread.stop()
            self.update_thread = None
            
            self.status_bar.showMessage("Bot đã dừng", 3000)
            self.bot_log.append(f"{datetime.now().strftime('%H:%M:%S')} - Bot đã dừng")
            
            # Gửi thông báo Telegram
            if self.telegram_notifier:
                self.telegram_notifier.send_message("Bot giao dịch đã bị tắt")
    
    def save_config(self):
        """Lưu cấu hình hiện tại"""
        try:
            # Cập nhật cấu hình từ giao diện
            risk_level = int(self.risk_level_combo.currentText().replace("%", ""))
            symbols = [s.strip() for s in self.symbols_input.text().split(",")]
            timeframes = [t.strip() for t in self.timeframes_input.text().split(",")]
            
            self.config["risk_level"] = risk_level
            self.config["symbols"] = symbols
            self.config["timeframes"] = timeframes
            self.config["testnet"] = self.testnet_checkbox.isChecked()
            self.config["telegram_notifications"] = self.telegram_enabled_checkbox.isChecked()
            self.config["auto_trailing_stop"] = self.trailing_stop_checkbox.isChecked()
            
            self.config["quiet_hours"] = {
                "enabled": self.quiet_hours_checkbox.isChecked(),
                "start": self.quiet_start_input.text(),
                "end": self.quiet_end_input.text()
            }
            
            self.config["auto_update"] = self.auto_update_checkbox.isChecked()
            self.config["update_frequency"] = self.update_frequency_spin.value()
            
            # Lưu cấu hình
            with open("account_config.json", "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
            
            # Lưu API key và secret nếu được cung cấp
            api_key = self.api_key_input.text()
            api_secret = self.api_secret_input.text()
            
            if api_key and api_secret:
                # Đặt biến môi trường
                os.environ["BINANCE_TESTNET_API_KEY"] = api_key
                os.environ["BINANCE_TESTNET_API_SECRET"] = api_secret
            
            # Lưu thông tin Telegram nếu được cung cấp
            telegram_token = self.telegram_token_input.text()
            telegram_chat_id = self.telegram_chat_id_input.text()
            
            if telegram_token and telegram_chat_id:
                # Đặt biến môi trường
                os.environ["TELEGRAM_BOT_TOKEN"] = telegram_token
                os.environ["TELEGRAM_CHAT_ID"] = telegram_chat_id
            
            self.status_bar.showMessage("Cấu hình đã được lưu", 3000)
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {str(e)}")
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu cấu hình: {str(e)}")
    
    def load_config(self):
        """Tải cấu hình từ tệp"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn tệp cấu hình", "", "JSON Files (*.json)")
        
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    new_config = json.load(f)
                
                # Cập nhật cấu hình
                self.config.update(new_config)
                
                # Cập nhật giao diện
                self.testnet_checkbox.setChecked(self.config.get("testnet", True))
                self.telegram_enabled_checkbox.setChecked(self.config.get("telegram_notifications", False))
                self.trailing_stop_checkbox.setChecked(self.config.get("auto_trailing_stop", True))
                
                risk_level = str(self.config.get("risk_level", 10)) + "%"
                current_index = self.risk_level_combo.findText(risk_level)
                self.risk_level_combo.setCurrentIndex(current_index if current_index >= 0 else 0)
                
                self.symbols_input.setText(", ".join(self.config.get("symbols", ["BTCUSDT", "ETHUSDT"])))
                self.timeframes_input.setText(", ".join(self.config.get("timeframes", ["1h", "4h"])))
                
                self.quiet_hours_checkbox.setChecked(self.config.get("quiet_hours", {}).get("enabled", False))
                self.quiet_start_input.setText(self.config.get("quiet_hours", {}).get("start", "22:00"))
                self.quiet_end_input.setText(self.config.get("quiet_hours", {}).get("end", "07:00"))
                
                self.auto_update_checkbox.setChecked(self.config.get("auto_update", True))
                self.update_frequency_spin.setValue(self.config.get("update_frequency", 24))
                
                self.status_bar.showMessage(f"Cấu hình đã được tải từ {file_path}", 3000)
                
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
                QMessageBox.critical(self, "Lỗi", f"Không thể tải cấu hình: {str(e)}")
    
    def save_settings(self):
        """Lưu cài đặt từ tab Settings"""
        self.save_config()
        self.risk_level_label.setText(f"Mức rủi ro: {self.config.get('risk_level', 10)}%")
        QMessageBox.information(self, "Thành công", "Cài đặt đã được lưu")
        
        # Kết nối lại API nếu đã có
        if self.market_analyzer:
            self.reconnect_api()
    
    def reset_settings(self):
        """Khôi phục cài đặt mặc định"""
        reply = QMessageBox.question(self, "Xác nhận", 
                                    "Bạn có chắc muốn khôi phục cài đặt mặc định?\n\nMọi cài đặt tùy chỉnh sẽ bị mất.",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Cài đặt mặc định
            default_config = {
                "risk_level": 10,
                "symbols": ["BTCUSDT", "ETHUSDT"],
                "timeframes": ["1h", "4h"],
                "testnet": True,
                "telegram_notifications": True,
                "quiet_hours": {
                    "enabled": False,
                    "start": "22:00",
                    "end": "07:00"
                },
                "auto_trailing_stop": True,
                "language": "vi",
                "auto_update": True,
                "update_frequency": 24
            }
            
            # Cập nhật cấu hình
            self.config = default_config
            
            # Cập nhật giao diện
            self.testnet_checkbox.setChecked(True)
            self.telegram_enabled_checkbox.setChecked(True)
            self.trailing_stop_checkbox.setChecked(True)
            
            risk_level = "10%"
            current_index = self.risk_level_combo.findText(risk_level)
            self.risk_level_combo.setCurrentIndex(current_index if current_index >= 0 else 0)
            
            self.symbols_input.setText("BTCUSDT, ETHUSDT")
            self.timeframes_input.setText("1h, 4h")
            
            self.quiet_hours_checkbox.setChecked(False)
            self.quiet_start_input.setText("22:00")
            self.quiet_end_input.setText("07:00")
            
            self.auto_update_checkbox.setChecked(True)
            self.update_frequency_spin.setValue(24)
            
            # Lưu cấu hình
            with open("account_config.json", "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4)
            
            self.status_bar.showMessage("Cài đặt đã được khôi phục về mặc định", 3000)
    
    def test_telegram(self):
        """Kiểm tra kết nối Telegram"""
        telegram_token = self.telegram_token_input.text()
        telegram_chat_id = self.telegram_chat_id_input.text()
        
        if not telegram_token or not telegram_chat_id:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập Bot Token và Chat ID Telegram")
            return
        
        try:
            # Đặt biến môi trường
            os.environ["TELEGRAM_BOT_TOKEN"] = telegram_token
            os.environ["TELEGRAM_CHAT_ID"] = telegram_chat_id
            
            # Khởi tạo notifier
            from advanced_telegram_notifier import TelegramNotifier
            telegram_notifier = TelegramNotifier()
            
            # Gửi tin nhắn kiểm tra
            test_message = "Đây là tin nhắn kiểm tra từ Bot Trading"
            telegram_notifier.send_message(test_message)
            
            self.telegram_notifier = telegram_notifier
            self.status_bar.showMessage("Đã gửi tin nhắn kiểm tra đến Telegram", 3000)
            
            QMessageBox.information(self, "Thành công", "Tin nhắn kiểm tra đã được gửi đến Telegram")
            
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra Telegram: {str(e)}")
            QMessageBox.critical(self, "Lỗi", f"Không thể kết nối đến Telegram: {str(e)}")
    
    def send_telegram_notification(self):
        """Gửi thông báo Telegram tùy chỉnh"""
        if not self.telegram_notifier:
            QMessageBox.warning(self, "Lỗi", "Chưa kết nối được đến Telegram. Vui lòng kiểm tra cài đặt Telegram.")
            return
        
        # Lấy nội dung thông báo
        from PyQt5.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "Thông báo Telegram", "Nhập nội dung thông báo:")
        
        if ok and text:
            try:
                self.telegram_notifier.send_message(text)
                self.status_bar.showMessage("Đã gửi thông báo đến Telegram", 3000)
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo Telegram: {str(e)}")
                QMessageBox.critical(self, "Lỗi", f"Không thể gửi thông báo Telegram: {str(e)}")
    
    def update_market_analysis(self):
        """Cập nhật phân tích thị trường"""
        if not self.market_analyzer:
            QMessageBox.warning(self, "Lỗi", "Chưa kết nối được đến API. Vui lòng kết nối trước khi phân tích thị trường.")
            return
        
        symbol = self.symbol_combo.currentText()
        timeframe = self.timeframe_combo.currentText()
        
        try:
            # Hiển thị thông báo đang xử lý
            self.status_bar.showMessage(f"Đang phân tích {symbol} trên khung thời gian {timeframe}...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(30)
            
            # Lấy dữ liệu thị trường
            market_data = self.market_analyzer.get_market_data(symbol, timeframe)
            
            if market_data["status"] == "success":
                # Hiển thị dữ liệu thị trường
                data_text = f"Cặp: {symbol}\n"
                data_text += f"Khung thời gian: {timeframe}\n"
                data_text += f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                
                data_text += f"Giá hiện tại: {market_data['price']:.2f}\n"
                data_text += f"Thay đổi 24h: {market_data['change_24h']:.2f}%\n"
                data_text += f"Khối lượng 24h: {market_data['volume']:.2f}\n"
                data_text += f"Cao nhất 24h: {market_data['high_24h']:.2f}\n"
                data_text += f"Thấp nhất 24h: {market_data['low_24h']:.2f}\n\n"
                
                data_text += f"Giá mở: {market_data['open']:.2f}\n"
                data_text += f"Giá đóng: {market_data['close']:.2f}\n"
                data_text += f"Giá cao: {market_data['high']:.2f}\n"
                data_text += f"Giá thấp: {market_data['low']:.2f}\n"
                
                self.market_data_text.setText(data_text)
            else:
                self.market_data_text.setText(f"Lỗi khi lấy dữ liệu thị trường: {market_data.get('message', 'Không rõ lỗi')}")
            
            self.progress_bar.setValue(60)
            
            # Phân tích kỹ thuật
            analysis = self.market_analyzer.analyze_technical(symbol, timeframe)
            
            if analysis["status"] == "success":
                # Hiển thị phân tích kỹ thuật
                ta_text = f"Tín hiệu tổng hợp: {analysis['overall_signal']} ({analysis['strength']})\n\n"
                
                ta_text += "Các chỉ báo kỹ thuật:\n"
                for indicator in analysis.get("indicators", []):
                    ta_text += f"- {indicator['name']}: {indicator['value']} ({indicator['signal']})\n"
                
                ta_text += "\nTrend Analysis:\n"
                ta_text += f"- Xu hướng ngắn hạn: {analysis.get('short_term_trend', 'Không rõ')}\n"
                ta_text += f"- Xu hướng trung hạn: {analysis.get('mid_term_trend', 'Không rõ')}\n"
                ta_text += f"- Xu hướng dài hạn: {analysis.get('long_term_trend', 'Không rõ')}\n"
                
                ta_text += "\nSupport/Resistance:\n"
                for level in analysis.get("support_resistance", []):
                    ta_text += f"- {level['type']}: {level['value']:.2f}\n"
                
                self.ta_text.setText(ta_text)
            else:
                self.ta_text.setText(f"Lỗi khi phân tích kỹ thuật: {analysis.get('message', 'Không rõ lỗi')}")
            
            self.progress_bar.setValue(90)
            
            # Lấy tín hiệu giao dịch
            if self.signal_generator:
                signals = self.signal_generator.generate_signals([symbol], [timeframe])
                
                # Hiển thị tín hiệu giao dịch
                self.signals_table.setRowCount(len(signals))
                
                for i, signal in enumerate(signals):
                    # Lấy dữ liệu
                    signal_symbol = signal["symbol"]
                    signal_timeframe = signal["timeframe"]
                    side = signal["side"]
                    entry_price = signal["entry_price"]
                    stop_loss = signal["stop_loss"]
                    take_profit = signal["take_profit"]
                    confidence = signal["confidence"]
                    
                    # Tạo các mục trong bảng
                    self.signals_table.setItem(i, 0, QTableWidgetItem(signal_symbol))
                    self.signals_table.setItem(i, 1, QTableWidgetItem(signal_timeframe))
                    
                    # Đặt màu cho hướng giao dịch
                    side_item = QTableWidgetItem(side)
                    if side == "LONG":
                        side_item.setForeground(QColor("green"))
                    else:
                        side_item.setForeground(QColor("red"))
                    self.signals_table.setItem(i, 2, side_item)
                    
                    self.signals_table.setItem(i, 3, QTableWidgetItem(f"{entry_price:.2f}"))
                    self.signals_table.setItem(i, 4, QTableWidgetItem(f"{stop_loss:.2f}"))
                    self.signals_table.setItem(i, 5, QTableWidgetItem(f"{take_profit:.2f}"))
                    self.signals_table.setItem(i, 6, QTableWidgetItem(f"{confidence}%"))
            
            self.progress_bar.setValue(100)
            self.status_bar.showMessage("Phân tích hoàn tất", 3000)
            self.progress_bar.setVisible(False)
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích thị trường: {str(e)}")
            self.status_bar.showMessage("Phân tích thất bại", 3000)
            self.progress_bar.setVisible(False)
            
            # Hiển thị thông báo lỗi
            QMessageBox.critical(self, "Lỗi phân tích", f"Không thể phân tích thị trường: {str(e)}")
    
    def refresh_positions(self):
        """Làm mới danh sách vị thế"""
        if not self.position_manager:
            QMessageBox.warning(self, "Lỗi", "Chưa kết nối được đến API. Vui lòng kết nối trước khi làm mới vị thế.")
            return
        
        try:
            positions = self.position_manager.get_all_positions()
            self.update_position_tables(positions)
            self.status_bar.showMessage("Đã làm mới danh sách vị thế", 3000)
        except Exception as e:
            logger.error(f"Lỗi khi làm mới vị thế: {str(e)}")
            QMessageBox.critical(self, "Lỗi", f"Không thể làm mới vị thế: {str(e)}")
    
    def close_selected_position(self):
        """Đóng vị thế đã chọn"""
        if not self.position_manager:
            QMessageBox.warning(self, "Lỗi", "Chưa kết nối được đến API. Vui lòng kết nối trước khi đóng vị thế.")
            return
        
        # Lấy dòng đã chọn
        selected_rows = self.detailed_positions_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một vị thế để đóng.")
            return
        
        selected_row = selected_rows[0].row()
        symbol = self.detailed_positions_table.item(selected_row, 0).text()
        side = self.detailed_positions_table.item(selected_row, 1).text()
        
        reply = QMessageBox.question(self, "Xác nhận", 
                                    f"Bạn có chắc muốn đóng vị thế {side} trên {symbol}?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                result = self.position_manager.close_position(symbol)
                
                if result["status"] == "success":
                    self.status_bar.showMessage(f"Đã đóng vị thế {side} trên {symbol}", 3000)
                    self.refresh_positions()
                    
                    # Gửi thông báo Telegram
                    if self.telegram_notifier:
                        self.telegram_notifier.send_message(f"Đã đóng vị thế {side} trên {symbol}")
                else:
                    QMessageBox.critical(self, "Lỗi", f"Không thể đóng vị thế: {result.get('message', 'Không rõ lỗi')}")
            except Exception as e:
                logger.error(f"Lỗi khi đóng vị thế: {str(e)}")
                QMessageBox.critical(self, "Lỗi", f"Không thể đóng vị thế: {str(e)}")
    
    def edit_sl(self):
        """Chỉnh sửa Stop Loss"""
        if not self.position_manager:
            QMessageBox.warning(self, "Lỗi", "Chưa kết nối được đến API. Vui lòng kết nối trước khi chỉnh sửa SL.")
            return
        
        # Lấy dòng đã chọn
        selected_rows = self.detailed_positions_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một vị thế để chỉnh sửa SL.")
            return
        
        selected_row = selected_rows[0].row()
        symbol = self.detailed_positions_table.item(selected_row, 0).text()
        side = self.detailed_positions_table.item(selected_row, 1).text()
        current_sl = float(self.detailed_positions_table.item(selected_row, 5).text())
        
        # Lấy SL mới
        from PyQt5.QtWidgets import QInputDialog
        new_sl, ok = QInputDialog.getDouble(self, "Chỉnh sửa Stop Loss", 
                                           f"Nhập Stop Loss mới cho {symbol} {side}:", 
                                           current_sl, 0, 1000000, 2)
        
        if ok:
            try:
                result = self.position_manager.update_sl_tp(symbol, side, new_sl)
                
                if result["status"] == "success":
                    self.status_bar.showMessage(f"Đã cập nhật SL cho {symbol} {side}", 3000)
                    self.refresh_positions()
                    
                    # Gửi thông báo Telegram
                    if self.telegram_notifier:
                        self.telegram_notifier.send_sltp_update(symbol, side, current_sl, new_sl, "Cập nhật thủ công")
                else:
                    QMessageBox.critical(self, "Lỗi", f"Không thể cập nhật SL: {result.get('message', 'Không rõ lỗi')}")
            except Exception as e:
                logger.error(f"Lỗi khi cập nhật SL: {str(e)}")
                QMessageBox.critical(self, "Lỗi", f"Không thể cập nhật SL: {str(e)}")
    
    def edit_tp(self):
        """Chỉnh sửa Take Profit"""
        if not self.position_manager:
            QMessageBox.warning(self, "Lỗi", "Chưa kết nối được đến API. Vui lòng kết nối trước khi chỉnh sửa TP.")
            return
        
        # Lấy dòng đã chọn
        selected_rows = self.detailed_positions_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một vị thế để chỉnh sửa TP.")
            return
        
        selected_row = selected_rows[0].row()
        symbol = self.detailed_positions_table.item(selected_row, 0).text()
        side = self.detailed_positions_table.item(selected_row, 1).text()
        current_tp = float(self.detailed_positions_table.item(selected_row, 6).text())
        
        # Lấy TP mới
        from PyQt5.QtWidgets import QInputDialog
        new_tp, ok = QInputDialog.getDouble(self, "Chỉnh sửa Take Profit", 
                                           f"Nhập Take Profit mới cho {symbol} {side}:", 
                                           current_tp, 0, 1000000, 2)
        
        if ok:
            try:
                result = self.position_manager.update_sl_tp(symbol, side, None, new_tp)
                
                if result["status"] == "success":
                    self.status_bar.showMessage(f"Đã cập nhật TP cho {symbol} {side}", 3000)
                    self.refresh_positions()
                    
                    # Gửi thông báo Telegram
                    if self.telegram_notifier:
                        self.telegram_notifier.send_message(f"Đã cập nhật Take Profit cho {symbol} {side}: {current_tp:.2f} -> {new_tp:.2f}")
                else:
                    QMessageBox.critical(self, "Lỗi", f"Không thể cập nhật TP: {result.get('message', 'Không rõ lỗi')}")
            except Exception as e:
                logger.error(f"Lỗi khi cập nhật TP: {str(e)}")
                QMessageBox.critical(self, "Lỗi", f"Không thể cập nhật TP: {str(e)}")
    
    def add_trailing_stop(self):
        """Thêm Trailing Stop cho vị thế đã chọn"""
        if not self.position_manager:
            QMessageBox.warning(self, "Lỗi", "Chưa kết nối được đến API. Vui lòng kết nối trước khi thêm Trailing Stop.")
            return
        
        # Lấy dòng đã chọn
        selected_rows = self.detailed_positions_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một vị thế để thêm Trailing Stop.")
            return
        
        selected_row = selected_rows[0].row()
        symbol = self.detailed_positions_table.item(selected_row, 0).text()
        side = self.detailed_positions_table.item(selected_row, 1).text()
        
        # Form để lấy tham số Trailing Stop
        from PyQt5.QtWidgets import QDialog, QFormLayout, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Thêm Trailing Stop")
        layout = QFormLayout(dialog)
        
        activation_spinbox = QDoubleSpinBox()
        activation_spinbox.setRange(0.5, 20)
        activation_spinbox.setValue(2)
        activation_spinbox.setSuffix("%")
        layout.addRow("Điểm kích hoạt (% lợi nhuận):", activation_spinbox)
        
        callback_spinbox = QDoubleSpinBox()
        callback_spinbox.setRange(0.1, 10)
        callback_spinbox.setValue(1)
        callback_spinbox.setSuffix("%")
        layout.addRow("Callback (%):", callback_spinbox)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            activation_percent = activation_spinbox.value()
            callback_percent = callback_spinbox.value()
            
            try:
                # Trong thực tế, bạn sẽ cần một hàm hoặc lớp để xử lý trailing stop
                # Đây chỉ là giả lập
                self.status_bar.showMessage(f"Đã thêm Trailing Stop cho {symbol} {side} (Kích hoạt: {activation_percent}%, Callback: {callback_percent}%)", 3000)
                
                # Giả lập cập nhật
                QMessageBox.information(self, "Thành công", f"Đã thêm Trailing Stop cho {symbol} {side}\nKích hoạt: {activation_percent}%\nCallback: {callback_percent}%")
                
                # Gửi thông báo Telegram
                if self.telegram_notifier:
                    self.telegram_notifier.send_message(f"Đã thêm Trailing Stop cho {symbol} {side}\nKích hoạt: {activation_percent}%\nCallback: {callback_percent}%")
            except Exception as e:
                logger.error(f"Lỗi khi thêm Trailing Stop: {str(e)}")
                QMessageBox.critical(self, "Lỗi", f"Không thể thêm Trailing Stop: {str(e)}")
    
    def show_partial_tp_dialog(self):
        """Hiển thị hộp thoại chốt lời một phần"""
        if not self.position_manager:
            QMessageBox.warning(self, "Lỗi", "Chưa kết nối được đến API. Vui lòng kết nối trước khi chốt lời một phần.")
            return
        
        # Lấy dòng đã chọn
        selected_rows = self.detailed_positions_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một vị thế để chốt lời một phần.")
            return
        
        selected_row = selected_rows[0].row()
        symbol = self.detailed_positions_table.item(selected_row, 0).text()
        side = self.detailed_positions_table.item(selected_row, 1).text()
        
        # Form để lấy tham số chốt lời một phần
        from PyQt5.QtWidgets import QDialog, QFormLayout, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Chốt lời một phần")
        layout = QFormLayout(dialog)
        
        percentage_spinbox = QSpinBox()
        percentage_spinbox.setRange(10, 90)
        percentage_spinbox.setValue(50)
        percentage_spinbox.setSuffix("%")
        layout.addRow("Phần trăm chốt lời:", percentage_spinbox)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            percentage = percentage_spinbox.value()
            
            try:
                # Trong thực tế, bạn sẽ cần một hàm hoặc lớp để xử lý chốt lời một phần
                # Đây chỉ là giả lập
                self.status_bar.showMessage(f"Đã chốt lời {percentage}% vị thế {symbol} {side}", 3000)
                
                # Giả lập cập nhật
                QMessageBox.information(self, "Thành công", f"Đã chốt lời {percentage}% vị thế {symbol} {side}")
                
                # Gửi thông báo Telegram
                if self.telegram_notifier:
                    self.telegram_notifier.send_message(f"Đã chốt lời {percentage}% vị thế {symbol} {side}")
            except Exception as e:
                logger.error(f"Lỗi khi chốt lời một phần: {str(e)}")
                QMessageBox.critical(self, "Lỗi", f"Không thể chốt lời một phần: {str(e)}")
    
    def show_market_order_dialog(self):
        """Hiển thị hộp thoại đặt lệnh thị trường"""
        if not self.position_manager:
            QMessageBox.warning(self, "Lỗi", "Chưa kết nối được đến API. Vui lòng kết nối trước khi đặt lệnh.")
            return
        
        # Form để lấy tham số lệnh
        from PyQt5.QtWidgets import QDialog, QFormLayout, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Đặt lệnh thị trường")
        layout = QFormLayout(dialog)
        
        symbol_combo = QComboBox()
        symbol_combo.addItems(["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "DOGEUSDT"])
        layout.addRow("Cặp:", symbol_combo)
        
        side_combo = QComboBox()
        side_combo.addItems(["LONG", "SHORT"])
        layout.addRow("Hướng:", side_combo)
        
        amount_spinbox = QDoubleSpinBox()
        amount_spinbox.setRange(0.001, 1000)
        amount_spinbox.setValue(0.01)
        layout.addRow("Số lượng:", amount_spinbox)
        
        leverage_spinbox = QSpinBox()
        leverage_spinbox.setRange(1, 125)
        leverage_spinbox.setValue(10)
        layout.addRow("Đòn bẩy:", leverage_spinbox)
        
        sl_checkbox = QCheckBox("Thêm Stop Loss")
        sl_checkbox.setChecked(True)
        layout.addRow(sl_checkbox)
        
        sl_spinbox = QDoubleSpinBox()
        sl_spinbox.setRange(0.01, 100000)
        sl_spinbox.setValue(1000)
        layout.addRow("Stop Loss (%):", sl_spinbox)
        
        tp_checkbox = QCheckBox("Thêm Take Profit")
        tp_checkbox.setChecked(True)
        layout.addRow(tp_checkbox)
        
        tp_spinbox = QDoubleSpinBox()
        tp_spinbox.setRange(0.01, 100000)
        tp_spinbox.setValue(2000)
        layout.addRow("Take Profit (%):", tp_spinbox)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            symbol = symbol_combo.currentText()
            side = side_combo.currentText()
            amount = amount_spinbox.value()
            leverage = leverage_spinbox.value()
            
            # Thiết lập Stop Loss và Take Profit
            stop_loss = None
            take_profit = None
            
            if sl_checkbox.isChecked():
                stop_loss = sl_spinbox.value()
            
            if tp_checkbox.isChecked():
                take_profit = tp_spinbox.value()
            
            try:
                # Đặt lệnh
                result = self.position_manager.open_position(
                    symbol=symbol,
                    side=side,
                    amount=amount,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    leverage=leverage
                )
                
                if result["status"] == "success":
                    self.status_bar.showMessage(f"Đã đặt lệnh {side} trên {symbol}", 3000)
                    self.refresh_positions()
                    
                    # Gửi thông báo Telegram
                    if self.telegram_notifier:
                        self.telegram_notifier.send_message(f"Đã đặt lệnh {side} trên {symbol} với số lượng {amount}")
                else:
                    QMessageBox.critical(self, "Lỗi", f"Không thể đặt lệnh: {result.get('message', 'Không rõ lỗi')}")
            except Exception as e:
                logger.error(f"Lỗi khi đặt lệnh: {str(e)}")
                QMessageBox.critical(self, "Lỗi", f"Không thể đặt lệnh: {str(e)}")
    
    def show_limit_order_dialog(self):
        """Hiển thị hộp thoại đặt lệnh giới hạn"""
        # TODO: Implement limit order
        QMessageBox.information(self, "Thông báo", "Chức năng đặt lệnh giới hạn đang được phát triển")
    
    def show_close_position_dialog(self):
        """Hiển thị hộp thoại đóng vị thế"""
        if not self.position_manager:
            QMessageBox.warning(self, "Lỗi", "Chưa kết nối được đến API. Vui lòng kết nối trước khi đóng vị thế.")
            return
        
        try:
            positions = self.position_manager.get_all_positions()
            
            if not positions:
                QMessageBox.information(self, "Thông báo", "Không có vị thế nào đang mở")
                return
            
            # Form để chọn vị thế đóng
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Đóng vị thế")
            layout = QVBoxLayout(dialog)
            
            position_table = QTableWidget(len(positions), 5)
            position_table.setHorizontalHeaderLabels(["Cặp", "Vị thế", "Số lượng", "Giá vào", "Lợi nhuận"])
            position_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            
            for i, position in enumerate(positions):
                # Lấy dữ liệu
                symbol = position["symbol"]
                side = position["side"]
                quantity = position["size"]
                entry_price = position["entry_price"]
                profit = position["unrealized_pnl"]
                profit_percent = position["profit_percent"]
                
                # Tạo các mục trong bảng
                position_table.setItem(i, 0, QTableWidgetItem(symbol))
                position_table.setItem(i, 1, QTableWidgetItem(side))
                position_table.setItem(i, 2, QTableWidgetItem(f"{quantity:.4f}"))
                position_table.setItem(i, 3, QTableWidgetItem(f"{entry_price:.2f}"))
                
                # Đặt màu cho lợi nhuận
                profit_item = QTableWidgetItem(f"{profit:.2f} ({profit_percent:.2f}%)")
                if profit > 0:
                    profit_item.setForeground(QColor("green"))
                elif profit < 0:
                    profit_item.setForeground(QColor("red"))
                position_table.setItem(i, 4, profit_item)
            
            layout.addWidget(position_table)
            
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)
            
            if dialog.exec_() == QDialog.Accepted:
                selected_rows = position_table.selectedIndexes()
                if not selected_rows:
                    QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một vị thế để đóng.")
                    return
                
                selected_row = selected_rows[0].row()
                symbol = position_table.item(selected_row, 0).text()
                side = position_table.item(selected_row, 1).text()
                
                reply = QMessageBox.question(self, "Xác nhận", 
                                           f"Bạn có chắc muốn đóng vị thế {side} trên {symbol}?",
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                
                if reply == QMessageBox.Yes:
                    result = self.position_manager.close_position(symbol)
                    
                    if result["status"] == "success":
                        self.status_bar.showMessage(f"Đã đóng vị thế {side} trên {symbol}", 3000)
                        self.refresh_positions()
                        
                        # Gửi thông báo Telegram
                        if self.telegram_notifier:
                            self.telegram_notifier.send_message(f"Đã đóng vị thế {side} trên {symbol}")
                    else:
                        QMessageBox.critical(self, "Lỗi", f"Không thể đóng vị thế: {result.get('message', 'Không rõ lỗi')}")
        except Exception as e:
            logger.error(f"Lỗi khi hiển thị hộp thoại đóng vị thế: {str(e)}")
            QMessageBox.critical(self, "Lỗi", f"Không thể hiển thị hộp thoại đóng vị thế: {str(e)}")
    
    def show_trailing_stop_dialog(self):
        """Hiển thị hộp thoại Trailing Stop"""
        # TODO: Implement trailing stop dialog
        QMessageBox.information(self, "Thông báo", "Chức năng Trailing Stop đang được phát triển")
    
    def show_risk_calculator(self):
        """Hiển thị bộ tính toán rủi ro"""
        # TODO: Implement risk calculator
        QMessageBox.information(self, "Thông báo", "Chức năng tính toán rủi ro đang được phát triển")
    
    def show_position_size_calculator(self):
        """Hiển thị bộ tính toán kích thước vị thế"""
        # TODO: Implement position size calculator
        QMessageBox.information(self, "Thông báo", "Chức năng tính toán kích thước vị thế đang được phát triển")
    
    def execute_selected_signal(self):
        """Thực thi tín hiệu đã chọn"""
        if not self.position_manager:
            QMessageBox.warning(self, "Lỗi", "Chưa kết nối được đến API. Vui lòng kết nối trước khi thực thi tín hiệu.")
            return
        
        # Lấy dòng đã chọn
        selected_rows = self.signals_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một tín hiệu để thực thi.")
            return
        
        selected_row = selected_rows[0].row()
        symbol = self.signals_table.item(selected_row, 0).text()
        side = self.signals_table.item(selected_row, 2).text()
        entry_price = float(self.signals_table.item(selected_row, 3).text())
        stop_loss = float(self.signals_table.item(selected_row, 4).text())
        take_profit = float(self.signals_table.item(selected_row, 5).text())
        
        # Lấy kích thước vị thế
        account_info = self.market_analyzer.get_account_info()
        if account_info["status"] != "success":
            QMessageBox.critical(self, "Lỗi", f"Không thể lấy thông tin tài khoản: {account_info.get('message', 'Không rõ lỗi')}")
            return
        
        account_balance = account_info["account"]["balance"]
        position_size = self.risk_manager.calculate_position_size(account_balance, symbol)
        
        # Xác nhận
        reply = QMessageBox.question(self, "Xác nhận", 
                                   f"Bạn có chắc muốn thực thi tín hiệu {side} trên {symbol}?\n\nGiá vào: {entry_price:.2f}\nStop Loss: {stop_loss:.2f}\nTake Profit: {take_profit:.2f}\nKích thước: {position_size:.4f}",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                result = self.position_manager.open_position(
                    symbol=symbol,
                    side=side,
                    amount=position_size,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
                
                if result["status"] == "success":
                    self.status_bar.showMessage(f"Đã thực thi tín hiệu {side} trên {symbol}", 3000)
                    self.refresh_positions()
                    
                    # Gửi thông báo Telegram
                    if self.telegram_notifier:
                        self.telegram_notifier.send_message(f"Đã thực thi tín hiệu {side} trên {symbol} với giá {entry_price:.2f}")
                else:
                    QMessageBox.critical(self, "Lỗi", f"Không thể thực thi tín hiệu: {result.get('message', 'Không rõ lỗi')}")
            except Exception as e:
                logger.error(f"Lỗi khi thực thi tín hiệu: {str(e)}")
                QMessageBox.critical(self, "Lỗi", f"Không thể thực thi tín hiệu: {str(e)}")
    
    def ignore_selected_signal(self):
        """Bỏ qua tín hiệu đã chọn"""
        # Lấy dòng đã chọn
        selected_rows = self.signals_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một tín hiệu để bỏ qua.")
            return
        
        selected_row = selected_rows[0].row()
        self.signals_table.removeRow(selected_row)
        self.status_bar.showMessage("Đã bỏ qua tín hiệu", 3000)
    
    def load_logs(self):
        """Tải nhật ký"""
        try:
            log_type = self.log_type_combo.currentText()
            log_file = ""
            
            if log_type == "Bot":
                log_file = "desktop_app.log"
            elif log_type == "Giao dịch":
                log_file = "logs/trading.log"
            elif log_type == "Thị trường":
                log_file = "logs/market.log"
            elif log_type == "Lỗi":
                log_file = "logs/error.log"
            elif log_type == "Tất cả":
                log_file = "logs/all.log"
            
            if os.path.exists(log_file):
                with open(log_file, "r", encoding="utf-8") as f:
                    log_content = f.read()
                self.log_viewer.setText(log_content)
            else:
                self.log_viewer.setText(f"Không tìm thấy tệp nhật ký: {log_file}")
            
            # Di chuyển con trỏ đến cuối
            self.log_viewer.moveCursor(QTextCursor.End)
            
        except Exception as e:
            logger.error(f"Lỗi khi tải nhật ký: {str(e)}")
            self.log_viewer.setText(f"Lỗi khi tải nhật ký: {str(e)}")
    
    def clear_logs(self):
        """Xóa nhật ký"""
        reply = QMessageBox.question(self, "Xác nhận", 
                                   "Bạn có chắc muốn xóa nhật ký?",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            log_type = self.log_type_combo.currentText()
            log_file = ""
            
            if log_type == "Bot":
                log_file = "desktop_app.log"
            elif log_type == "Giao dịch":
                log_file = "logs/trading.log"
            elif log_type == "Thị trường":
                log_file = "logs/market.log"
            elif log_type == "Lỗi":
                log_file = "logs/error.log"
            elif log_type == "Tất cả":
                log_file = "logs/all.log"
            
            try:
                if os.path.exists(log_file):
                    # Xóa nội dung tệp
                    with open(log_file, "w", encoding="utf-8") as f:
                        f.write("Nhật ký đã được xóa lúc " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
                    
                    self.log_viewer.setText("Nhật ký đã được xóa")
                    self.status_bar.showMessage("Đã xóa nhật ký", 3000)
                else:
                    self.log_viewer.setText(f"Không tìm thấy tệp nhật ký: {log_file}")
            except Exception as e:
                logger.error(f"Lỗi khi xóa nhật ký: {str(e)}")
                QMessageBox.critical(self, "Lỗi", f"Không thể xóa nhật ký: {str(e)}")
    
    def show_about(self):
        """Hiển thị thông tin giới thiệu"""
        about_text = """<h2>Crypto Trading Bot Desktop</h2>
        <p>Phiên bản: 1.0.0</p>
        <p>Được phát triển bởi: Replit AI Assistant</p>
        <p>Bản quyền © 2025</p>
        <p>Phần mềm giao dịch bot tiền điện tử với các chức năng nâng cao:</p>
        <ul>
            <li>Phân tích kỹ thuật đa khung thời gian</li>
            <li>Quản lý vị thế tự động</li>
            <li>Nhiều mức độ rủi ro</li>
            <li>Thông báo Telegram</li>
            <li>Trailing Stop và chốt lời một phần</li>
            <li>Tự động cập nhật</li>
        </ul>
        """
        
        QMessageBox.about(self, "Giới thiệu", about_text)
    
    def open_documentation(self):
        """Mở tài liệu hướng dẫn"""
        if os.path.exists("HƯỚNG_DẪN_SỬ_DỤNG.md"):
            # Mở tệp trong trình duyệt mặc định
            url = QUrl.fromLocalFile(os.path.abspath("HƯỚNG_DẪN_SỬ_DỤNG.md"))
            QDesktopServices.openUrl(url)
        else:
            QMessageBox.information(self, "Thông báo", "Tài liệu hướng dẫn chưa được tạo")
    
    def check_updates(self):
        """Kiểm tra cập nhật"""
        self.status_bar.showMessage("Đang kiểm tra cập nhật...", 3000)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(50)
        
        # TODO: Implement update checker
        QMessageBox.information(self, "Kiểm tra cập nhật", "Bạn đang sử dụng phiên bản mới nhất (1.0.0)")
        
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
    
    def closeEvent(self, event):
        """Xử lý sự kiện đóng cửa sổ"""
        reply = QMessageBox.question(self, "Xác nhận", 
                                   "Bạn có chắc muốn thoát?\n\nNếu bot đang chạy, nó sẽ bị dừng.",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Dừng luồng cập nhật nếu đang chạy
            if self.update_thread:
                self.update_thread.stop()
            
            # Lưu cấu hình
            self.save_config()
            
            # Gửi thông báo Telegram
            if self.telegram_notifier:
                self.telegram_notifier.send_message("Ứng dụng đã được đóng")
            
            event.accept()
        else:
            event.ignore()

# Chạy ứng dụng nếu được gọi trực tiếp
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TradingApp()
    window.show()
    sys.exit(app.exec_())