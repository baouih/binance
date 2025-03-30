#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Desktop App - Ứng dụng giao dịch desktop PyQt5
------------------------------------------------
Ứng dụng desktop giao dịch crypto với các tính năng:
- Cập nhật dữ liệu tài khoản và thị trường theo thời gian thực
- Mở/đóng lệnh giao dịch tự động dựa trên tín hiệu
- Hiển thị danh sách vị thế và lịch sử giao dịch
- Phân tích thị trường và đề xuất giao dịch
- Quản lý rủi ro thông minh với nhiều cấu hình
- Tự động điều chỉnh SL/TP theo biến động thị trường
"""

import os
import sys
import json
import time
import logging
import traceback
import threading
from datetime import datetime, timedelta
from functools import partial
from typing import Dict, List, Tuple, Union, Any, Optional

# PyQt5 imports
from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QComboBox, QLineEdit, QFormLayout, QGroupBox, QMessageBox, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QCheckBox, QDoubleSpinBox,
    QSpinBox, QTextEdit, QSizePolicy, QSplitter, QStatusBar, QToolBar, QAction, QMenu,
    QSystemTrayIcon, QStyle, QDesktopWidget
)
from PyQt5.QtCore import Qt, QSize, QTimer, QThread, pyqtSignal, QDateTime, QSettings
from PyQt5.QtGui import QIcon, QFont, QPixmap, QColor, QPalette, QCursor

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("desktop_app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("desktop_app")

# Đường dẫn thư mục hiện tại
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

class MarketDataThread(QThread):
    """Thread cập nhật dữ liệu thị trường"""
    market_data_signal = pyqtSignal(dict)
    
    def __init__(self, interval=10, parent=None):
        """
        Khởi tạo thread cập nhật dữ liệu thị trường
        
        Args:
            interval (int): Khoảng thời gian cập nhật (giây)
            parent: Parent widget
        """
        super().__init__(parent)
        self.interval = interval
        self.running = True
        
        # Import các module cần thiết
        try:
            from binance_api import BinanceAPI
            from market_analyzer import MarketAnalyzer
            
            # Khởi tạo API và các đối tượng
            self.api = BinanceAPI()
            self.analyzer = MarketAnalyzer()
            
            logger.info("Khởi tạo MarketDataThread thành công")
        except Exception as e:
            logger.error(f"Lỗi khởi tạo MarketDataThread: {str(e)}")
            self.api = None
            self.analyzer = None
    
    def run(self):
        """Chạy thread cập nhật dữ liệu thị trường"""
        logger.info("Bắt đầu chạy MarketDataThread")
        
        while self.running:
            try:
                if not self.api or not self.analyzer:
                    logger.warning("API hoặc Analyzer chưa được khởi tạo")
                    time.sleep(self.interval)
                    continue
                
                # Thu thập dữ liệu thị trường
                market_data = {}
                
                # Lấy giá BTC và ETH
                btc_price = self.api.get_symbol_price("BTCUSDT")
                eth_price = self.api.get_symbol_price("ETHUSDT")
                
                market_data["btc_price"] = btc_price
                market_data["eth_price"] = eth_price
                
                # Lấy chỉ báo kỹ thuật
                for symbol in ["BTCUSDT", "ETHUSDT"]:
                    indicators = self.analyzer.get_technical_indicators(symbol, "1h")
                    market_data[f"{symbol}_indicators"] = indicators
                
                # Lấy tín hiệu giao dịch
                signals = self.analyzer.get_trading_signals()
                market_data["signals"] = signals
                
                # Xác định chế độ thị trường
                market_regime = self.analyzer.get_market_regime("BTCUSDT", "1h")
                market_data["market_regime"] = market_regime
                
                # Phát tín hiệu với dữ liệu đã thu thập
                self.market_data_signal.emit(market_data)
                
            except Exception as e:
                logger.error(f"Lỗi trong MarketDataThread: {str(e)}")
            
            # Nghỉ theo khoảng thời gian đã cấu hình
            time.sleep(self.interval)
    
    def stop(self):
        """Dừng thread"""
        self.running = False
        self.wait()

class AccountDataThread(QThread):
    """Thread cập nhật dữ liệu tài khoản"""
    account_data_signal = pyqtSignal(dict)
    
    def __init__(self, interval=10, parent=None):
        """
        Khởi tạo thread cập nhật dữ liệu tài khoản
        
        Args:
            interval (int): Khoảng thời gian cập nhật (giây)
            parent: Parent widget
        """
        super().__init__(parent)
        self.interval = interval
        self.running = True
        
        # Import các module cần thiết
        try:
            from binance_api import BinanceAPI
            
            # Khởi tạo API
            self.api = BinanceAPI()
            
            logger.info("Khởi tạo AccountDataThread thành công")
        except Exception as e:
            logger.error(f"Lỗi khởi tạo AccountDataThread: {str(e)}")
            self.api = None
    
    def run(self):
        """Chạy thread cập nhật dữ liệu tài khoản"""
        logger.info("Bắt đầu chạy AccountDataThread")
        
        while self.running:
            try:
                if not self.api:
                    logger.warning("API chưa được khởi tạo")
                    time.sleep(self.interval)
                    continue
                
                # Thu thập dữ liệu tài khoản
                account_data = {}
                
                # Lấy thông tin tài khoản
                account_info = self.api.get_account_info()
                account_data["account_info"] = account_info
                
                # Lấy số dư tài khoản
                balance = self.api.get_account_balance()
                account_data["balance"] = balance
                
                # Lấy danh sách vị thế đang mở
                positions = self.api.get_positions()
                account_data["positions"] = positions
                
                # Lấy danh sách lệnh đang chờ
                open_orders = self.api.get_open_orders()
                account_data["open_orders"] = open_orders
                
                # Lấy lịch sử giao dịch
                trade_history = self.api.get_trade_history(limit=20)
                account_data["trade_history"] = trade_history
                
                # Tính PnL
                total_pnl = 0
                for position in positions:
                    total_pnl += position.get("unrealized_pnl", 0)
                
                account_data["total_pnl"] = total_pnl
                
                # Phát tín hiệu với dữ liệu đã thu thập
                self.account_data_signal.emit(account_data)
                
            except Exception as e:
                logger.error(f"Lỗi trong AccountDataThread: {str(e)}")
            
            # Nghỉ theo khoảng thời gian đã cấu hình
            time.sleep(self.interval)
    
    def stop(self):
        """Dừng thread"""
        self.running = False
        self.wait()

class TradingThread(QThread):
    """Thread xử lý giao dịch tự động"""
    trading_signal = pyqtSignal(dict)
    
    def __init__(self, interval=30, parent=None):
        """
        Khởi tạo thread xử lý giao dịch tự động
        
        Args:
            interval (int): Khoảng thời gian kiểm tra tín hiệu (giây)
            parent: Parent widget
        """
        super().__init__(parent)
        self.interval = interval
        self.running = True
        self.trading_enabled = False
        
        # Import các module cần thiết
        try:
            from binance_api import BinanceAPI
            from market_analyzer import MarketAnalyzer
            from risk_manager import RiskManager
            
            # Khởi tạo các đối tượng
            self.api = BinanceAPI()
            self.analyzer = MarketAnalyzer()
            self.risk_manager = RiskManager()
            
            logger.info("Khởi tạo TradingThread thành công")
        except Exception as e:
            logger.error(f"Lỗi khởi tạo TradingThread: {str(e)}")
            self.api = None
            self.analyzer = None
            self.risk_manager = None
    
    def run(self):
        """Chạy thread xử lý giao dịch tự động"""
        logger.info("Bắt đầu chạy TradingThread")
        
        while self.running:
            try:
                if not self.trading_enabled:
                    # Nếu giao dịch tự động bị tắt, chỉ cập nhật trạng thái
                    self.trading_signal.emit({"status": "disabled"})
                    time.sleep(self.interval)
                    continue
                
                if not self.api or not self.analyzer or not self.risk_manager:
                    logger.warning("Các đối tượng cần thiết chưa được khởi tạo")
                    time.sleep(self.interval)
                    continue
                
                # Lấy các vị thế hiện tại
                positions = self.api.get_positions()
                
                # Lấy tín hiệu giao dịch mới
                signals = self.analyzer.get_trading_signals()
                
                # Kết quả xử lý
                result = {
                    "status": "running",
                    "actions": [],
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Xử lý các vị thế đang mở
                for position in positions:
                    symbol = position.get("symbol")
                    side = position.get("side")
                    entry_price = position.get("entry_price")
                    size = position.get("size")
                    
                    # Kiểm tra điều kiện đóng vị thế
                    close_signal = self.analyzer.get_close_signal(symbol, side)
                    
                    if close_signal:
                        # Đóng vị thế
                        close_result = self.api.close_position(symbol, side, size)
                        
                        action = {
                            "type": "close",
                            "symbol": symbol,
                            "side": side,
                            "size": size,
                            "result": close_result,
                            "reason": close_signal.get("reason", "Tín hiệu đóng vị thế")
                        }
                        
                        result["actions"].append(action)
                        logger.info(f"Đóng vị thế: {symbol} {side} {size}")
                    
                    # Kiểm tra điều chỉnh SL/TP
                    adjust_sl_tp = self.analyzer.should_adjust_sl_tp(symbol, side, entry_price)
                    
                    if adjust_sl_tp:
                        new_sl = adjust_sl_tp.get("new_sl")
                        new_tp = adjust_sl_tp.get("new_tp")
                        
                        # Cập nhật SL/TP
                        update_result = self.api.update_sl_tp(symbol, side, new_sl, new_tp)
                        
                        action = {
                            "type": "adjust_sl_tp",
                            "symbol": symbol,
                            "side": side,
                            "new_sl": new_sl,
                            "new_tp": new_tp,
                            "result": update_result,
                            "reason": adjust_sl_tp.get("reason", "Điều chỉnh SL/TP")
                        }
                        
                        result["actions"].append(action)
                        logger.info(f"Điều chỉnh SL/TP: {symbol} {side} SL={new_sl} TP={new_tp}")
                
                # Xử lý tín hiệu mở vị thế mới
                for signal in signals:
                    if signal.get("action") == "open":
                        symbol = signal.get("symbol")
                        side = signal.get("side")
                        
                        # Kiểm tra xem đã có vị thế cho cặp tiền này chưa
                        existing_position = False
                        for pos in positions:
                            if pos.get("symbol") == symbol:
                                existing_position = True
                                break
                        
                        if existing_position:
                            continue
                        
                        # Tính toán kích thước vị thế dựa trên quản lý rủi ro
                        risk_params = self.risk_manager.calculate_risk_params(symbol, side)
                        
                        if risk_params.get("status") == "success":
                            size = risk_params.get("position_size")
                            stop_loss = risk_params.get("stop_loss")
                            take_profit = risk_params.get("take_profit")
                            
                            # Mở vị thế mới
                            open_result = self.api.open_position(
                                symbol=symbol,
                                side=side,
                                size=size,
                                stop_loss=stop_loss,
                                take_profit=take_profit
                            )
                            
                            action = {
                                "type": "open",
                                "symbol": symbol,
                                "side": side,
                                "size": size,
                                "stop_loss": stop_loss,
                                "take_profit": take_profit,
                                "result": open_result,
                                "reason": signal.get("reason", "Tín hiệu mở vị thế")
                            }
                            
                            result["actions"].append(action)
                            logger.info(f"Mở vị thế: {symbol} {side} {size}")
                
                # Phát tín hiệu với kết quả xử lý
                self.trading_signal.emit(result)
                
            except Exception as e:
                logger.error(f"Lỗi trong TradingThread: {str(e)}")
                self.trading_signal.emit({
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            
            # Nghỉ theo khoảng thời gian đã cấu hình
            time.sleep(self.interval)
    
    def stop(self):
        """Dừng thread"""
        self.running = False
        self.wait()
    
    def enable_trading(self, enabled):
        """Bật/tắt giao dịch tự động"""
        self.trading_enabled = enabled
        logger.info(f"Giao dịch tự động: {'Bật' if enabled else 'Tắt'}")

class TradingApp(QMainWindow):
    """Ứng dụng giao dịch desktop"""
    
    def __init__(self):
        """Khởi tạo ứng dụng"""
        super().__init__()
        
        # Thiết lập window title và icon
        self.setWindowTitle("Bot Giao Dịch Crypto - Phiên Bản Desktop")
        self.setMinimumSize(1024, 768)
        
        # Khởi tạo UI
        self.init_ui()
        
        # Khởi tạo các thread
        self.init_threads()
        
        # Cập nhật trạng thái ban đầu
        self.update_status("Sẵn sàng")
        
        logger.info("Khởi tạo ứng dụng hoàn tất")
    
    def init_ui(self):
        """Khởi tạo giao diện người dùng"""
        # Tạo widget trung tâm
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Tạo layout chính
        main_layout = QVBoxLayout(central_widget)
        
        # Tạo tab widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Tạo các tab
        self.create_dashboard_tab()
        self.create_trading_tab()
        self.create_positions_tab()
        self.create_market_analysis_tab()
        self.create_settings_tab()
        
        # Tạo thanh trạng thái
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Tạo label trạng thái
        self.status_label = QLabel("Khởi động...")
        self.status_bar.addWidget(self.status_label)
        
        # Tạo label thời gian
        self.time_label = QLabel(datetime.now().strftime("%H:%M:%S"))
        self.status_bar.addPermanentWidget(self.time_label)
        
        # Timer cập nhật thời gian
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)  # Cập nhật mỗi giây
    
    def create_dashboard_tab(self):
        """Tạo tab tổng quan"""
        dashboard_tab = QWidget()
        self.tabs.addTab(dashboard_tab, "Tổng Quan")
        
        # Layout cho tab
        layout = QVBoxLayout(dashboard_tab)
        
        # Tạo các nhóm thông tin
        self.create_account_info_group(layout)
        self.create_market_overview_group(layout)
        self.create_active_positions_group(layout)
        
        # Tạo nhóm thông báo và hoạt động gần đây
        self.create_recent_activities_group(layout)
    
    def create_account_info_group(self, parent_layout):
        """Tạo nhóm thông tin tài khoản"""
        group = QGroupBox("Thông Tin Tài Khoản")
        layout = QGridLayout(group)
        
        # Tổng số dư
        layout.addWidget(QLabel("Tổng Số Dư:"), 0, 0)
        self.total_balance_label = QLabel("0.00 USDT")
        self.total_balance_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.total_balance_label, 0, 1)
        
        # Số dư khả dụng
        layout.addWidget(QLabel("Số Dư Khả Dụng:"), 0, 2)
        self.available_balance_label = QLabel("0.00 USDT")
        self.available_balance_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.available_balance_label, 0, 3)
        
        # PnL chưa thực hiện
        layout.addWidget(QLabel("PnL Chưa Thực Hiện:"), 1, 0)
        self.unrealized_pnl_label = QLabel("0.00 USDT")
        self.unrealized_pnl_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.unrealized_pnl_label, 1, 1)
        
        # Giá trị vị thế
        layout.addWidget(QLabel("Giá Trị Vị Thế:"), 1, 2)
        self.position_value_label = QLabel("0.00 USDT")
        self.position_value_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.position_value_label, 1, 3)
        
        parent_layout.addWidget(group)
    
    def create_market_overview_group(self, parent_layout):
        """Tạo nhóm tổng quan thị trường"""
        group = QGroupBox("Tổng Quan Thị Trường")
        layout = QGridLayout(group)
        
        # BTC Price
        layout.addWidget(QLabel("BTC/USDT:"), 0, 0)
        self.btc_price_label = QLabel("0.00 USDT")
        self.btc_price_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.btc_price_label, 0, 1)
        
        # BTC 24h Change
        layout.addWidget(QLabel("BTC 24h:"), 0, 2)
        self.btc_change_label = QLabel("0.00%")
        self.btc_change_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.btc_change_label, 0, 3)
        
        # ETH Price
        layout.addWidget(QLabel("ETH/USDT:"), 1, 0)
        self.eth_price_label = QLabel("0.00 USDT")
        self.eth_price_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.eth_price_label, 1, 1)
        
        # ETH 24h Change
        layout.addWidget(QLabel("ETH 24h:"), 1, 2)
        self.eth_change_label = QLabel("0.00%")
        self.eth_change_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.eth_change_label, 1, 3)
        
        # Market Regime
        layout.addWidget(QLabel("Chế Độ Thị Trường:"), 2, 0)
        self.market_regime_label = QLabel("Không xác định")
        self.market_regime_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.market_regime_label, 2, 1)
        
        # Market Sentiment
        layout.addWidget(QLabel("Tâm Lý Thị Trường:"), 2, 2)
        self.market_sentiment_label = QLabel("Trung tính")
        self.market_sentiment_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.market_sentiment_label, 2, 3)
        
        parent_layout.addWidget(group)
    
    def create_active_positions_group(self, parent_layout):
        """Tạo nhóm vị thế đang mở"""
        group = QGroupBox("Vị Thế Đang Mở")
        layout = QVBoxLayout(group)
        
        # Tạo bảng vị thế
        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(8)
        self.positions_table.setHorizontalHeaderLabels([
            "Cặp Tiền", "Phía", "Kích Thước", "Giá Vào", "Giá Hiện Tại",
            "PnL", "SL", "TP"
        ])
        
        # Thiết lập chiều rộng cột
        header = self.positions_table.horizontalHeader()
        for i in range(8):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        
        layout.addWidget(self.positions_table)
        
        parent_layout.addWidget(group)
    
    def create_recent_activities_group(self, parent_layout):
        """Tạo nhóm hoạt động gần đây"""
        group = QGroupBox("Hoạt Động Gần Đây")
        layout = QVBoxLayout(group)
        
        # Tạo text edit cho hoạt động
        self.activities_text = QTextEdit()
        self.activities_text.setReadOnly(True)
        self.activities_text.setMaximumHeight(150)
        
        layout.addWidget(self.activities_text)
        
        parent_layout.addWidget(group)
    
    def create_trading_tab(self):
        """Tạo tab giao dịch"""
        trading_tab = QWidget()
        self.tabs.addTab(trading_tab, "Giao Dịch")
        
        # Layout cho tab
        layout = QVBoxLayout(trading_tab)
        
        # Tạo form giao dịch
        form_group = QGroupBox("Tạo Lệnh Giao Dịch Mới")
        form_layout = QFormLayout(form_group)
        
        # Cặp tiền
        symbol_layout = QHBoxLayout()
        self.trading_symbol = QComboBox()
        self.trading_symbol.addItems([
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT",
            "DOGEUSDT", "XRPUSDT", "DOTUSDT", "LINKUSDT", "AVAXUSDT"
        ])
        self.refresh_symbols_btn = QPushButton("Làm Mới")
        symbol_layout.addWidget(self.trading_symbol)
        symbol_layout.addWidget(self.refresh_symbols_btn)
        form_layout.addRow("Cặp Tiền:", symbol_layout)
        
        # Phía giao dịch
        side_layout = QHBoxLayout()
        self.buy_btn = QPushButton("MUA")
        self.buy_btn.setStyleSheet("background-color: #10B981; color: white; font-weight: bold;")
        self.sell_btn = QPushButton("BÁN")
        self.sell_btn.setStyleSheet("background-color: #EF4444; color: white; font-weight: bold;")
        side_layout.addWidget(self.buy_btn)
        side_layout.addWidget(self.sell_btn)
        form_layout.addRow("Phía:", side_layout)
        
        # Kích thước lệnh
        size_layout = QHBoxLayout()
        self.order_size = QDoubleSpinBox()
        self.order_size.setRange(0.001, 1000.0)
        self.order_size.setValue(0.01)
        self.order_size.setSingleStep(0.01)
        
        self.order_value = QDoubleSpinBox()
        self.order_value.setRange(1.0, 100000.0)
        self.order_value.setValue(100.0)
        self.order_value.setSingleStep(10.0)
        self.order_value.setPrefix("$ ")
        
        size_layout.addWidget(self.order_size)
        size_layout.addWidget(QLabel("hoặc"))
        size_layout.addWidget(self.order_value)
        form_layout.addRow("Kích Thước:", size_layout)
        
        # Đòn bẩy
        leverage_layout = QHBoxLayout()
        self.order_leverage = QComboBox()
        for lev in [1, 2, 3, 5, 10, 20, 50, 100]:
            self.order_leverage.addItem(f"{lev}x", lev)
        self.order_leverage.setCurrentIndex(2)  # 3x default
        leverage_layout.addWidget(self.order_leverage)
        form_layout.addRow("Đòn Bẩy:", leverage_layout)
        
        # Stop Loss & Take Profit
        sl_tp_layout = QHBoxLayout()
        
        sl_layout = QVBoxLayout()
        sl_title = QLabel("Stop Loss:")
        self.use_sl = QCheckBox("Sử dụng SL")
        self.use_sl.setChecked(True)
        self.sl_value = QDoubleSpinBox()
        self.sl_value.setRange(0.1, 100.0)
        self.sl_value.setValue(5.0)
        self.sl_value.setSingleStep(0.5)
        self.sl_value.setSuffix("%")
        sl_layout.addWidget(sl_title)
        sl_layout.addWidget(self.use_sl)
        sl_layout.addWidget(self.sl_value)
        
        tp_layout = QVBoxLayout()
        tp_title = QLabel("Take Profit:")
        self.use_tp = QCheckBox("Sử dụng TP")
        self.use_tp.setChecked(True)
        self.tp_value = QDoubleSpinBox()
        self.tp_value.setRange(0.1, 500.0)
        self.tp_value.setValue(15.0)
        self.tp_value.setSingleStep(0.5)
        self.tp_value.setSuffix("%")
        tp_layout.addWidget(tp_title)
        tp_layout.addWidget(self.use_tp)
        tp_layout.addWidget(self.tp_value)
        
        sl_tp_layout.addLayout(sl_layout)
        sl_tp_layout.addLayout(tp_layout)
        form_layout.addRow("SL/TP:", sl_tp_layout)
        
        # Trailing Stop
        trailing_layout = QHBoxLayout()
        self.use_trailing = QCheckBox("Sử dụng Trailing Stop")
        self.trailing_value = QDoubleSpinBox()
        self.trailing_value.setRange(0.1, 50.0)
        self.trailing_value.setValue(3.0)
        self.trailing_value.setSingleStep(0.5)
        self.trailing_value.setSuffix("%")
        self.trailing_value.setEnabled(False)
        self.use_trailing.toggled.connect(self.trailing_value.setEnabled)
        trailing_layout.addWidget(self.use_trailing)
        trailing_layout.addWidget(self.trailing_value)
        form_layout.addRow("Trailing:", trailing_layout)
        
        # Thêm group vào layout chính
        layout.addWidget(form_group)
        
        # Thêm nhóm tỷ lệ rủi ro và phần thưởng
        risk_reward_group = QGroupBox("Phân Tích Rủi Ro")
        risk_layout = QGridLayout(risk_reward_group)
        
        # Rủi ro lệnh
        risk_layout.addWidget(QLabel("Rủi Ro Lệnh:"), 0, 0)
        self.order_risk_label = QLabel("0.00 USDT (0.0%)")
        self.order_risk_label.setStyleSheet("color: #EF4444; font-weight: bold;")
        risk_layout.addWidget(self.order_risk_label, 0, 1)
        
        # Lợi nhuận tiềm năng
        risk_layout.addWidget(QLabel("Lợi Nhuận Tiềm Năng:"), 1, 0)
        self.order_reward_label = QLabel("0.00 USDT (0.0%)")
        self.order_reward_label.setStyleSheet("color: #10B981; font-weight: bold;")
        risk_layout.addWidget(self.order_reward_label, 1, 1)
        
        # Tỷ lệ R:R
        risk_layout.addWidget(QLabel("Tỷ Lệ R:R:"), 2, 0)
        self.order_rr_label = QLabel("0.0")
        self.order_rr_label.setStyleSheet("font-weight: bold;")
        risk_layout.addWidget(self.order_rr_label, 2, 1)
        
        layout.addWidget(risk_reward_group)
        
        # Nút tạo lệnh
        buttons_layout = QHBoxLayout()
        
        self.market_order_btn = QPushButton("TẠO LỆNH THỊ TRƯỜNG")
        self.market_order_btn.setStyleSheet("background-color: #3B82F6; color: white; font-weight: bold; padding: 10px;")
        buttons_layout.addWidget(self.market_order_btn)
        
        self.limit_order_btn = QPushButton("TẠO LỆNH GIỚI HẠN")
        self.limit_order_btn.setStyleSheet("background-color: #8B5CF6; color: white; font-weight: bold; padding: 10px;")
        buttons_layout.addWidget(self.limit_order_btn)
        
        layout.addLayout(buttons_layout)
        
        # Thêm stretch để đẩy các widget lên trên
        layout.addStretch()
    
    def create_positions_tab(self):
        """Tạo tab quản lý vị thế"""
        positions_tab = QWidget()
        self.tabs.addTab(positions_tab, "Quản Lý Vị Thế")
        
        # Layout cho tab
        layout = QVBoxLayout(positions_tab)
        
        # Tạo bảng vị thế
        self.detail_positions_table = QTableWidget()
        self.detail_positions_table.setColumnCount(10)
        self.detail_positions_table.setHorizontalHeaderLabels([
            "Cặp Tiền", "Phía", "Kích Thước", "Giá Vào", "Giá Hiện Tại",
            "PnL", "SL", "TP", "Thời Gian", "Thao Tác"
        ])
        
        # Thiết lập chiều rộng cột
        header = self.detail_positions_table.horizontalHeader()
        for i in range(10):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        
        layout.addWidget(self.detail_positions_table)
        
        # Tạo group box quản lý vị thế
        position_management = QGroupBox("Quản Lý Vị Thế")
        position_layout = QGridLayout(position_management)
        
        # Lựa chọn vị thế
        position_layout.addWidget(QLabel("Cặp Tiền:"), 0, 0)
        self.position_symbol = QComboBox()
        position_layout.addWidget(self.position_symbol, 0, 1)
        
        # Phía
        position_layout.addWidget(QLabel("Phía:"), 0, 2)
        self.position_side = QComboBox()
        self.position_side.addItems(["MUA", "BÁN"])
        position_layout.addWidget(self.position_side, 0, 3)
        
        # Nút làm mới
        self.refresh_positions_btn = QPushButton("Làm Mới")
        position_layout.addWidget(self.refresh_positions_btn, 0, 4)
        
        # Stop Loss mới
        position_layout.addWidget(QLabel("Stop Loss Mới:"), 1, 0)
        self.new_sl = QDoubleSpinBox()
        self.new_sl.setRange(0.0, 1000000.0)
        self.new_sl.setDecimals(2)
        self.new_sl.setSingleStep(10.0)
        position_layout.addWidget(self.new_sl, 1, 1)
        
        # Take Profit mới
        position_layout.addWidget(QLabel("Take Profit Mới:"), 1, 2)
        self.new_tp = QDoubleSpinBox()
        self.new_tp.setRange(0.0, 1000000.0)
        self.new_tp.setDecimals(2)
        self.new_tp.setSingleStep(10.0)
        position_layout.addWidget(self.new_tp, 1, 3)
        
        # Nút cập nhật SL/TP
        self.update_sltp_btn = QPushButton("Cập Nhật SL/TP")
        self.update_sltp_btn.setStyleSheet("background-color: #3B82F6; color: white;")
        position_layout.addWidget(self.update_sltp_btn, 1, 4)
        
        # Kích thước đóng
        position_layout.addWidget(QLabel("Kích Thước Đóng (%):"), 2, 0)
        self.close_size = QDoubleSpinBox()
        self.close_size.setRange(1.0, 100.0)
        self.close_size.setValue(100.0)
        self.close_size.setSingleStep(10.0)
        self.close_size.setSuffix("%")
        position_layout.addWidget(self.close_size, 2, 1)
        
        # Nút đóng vị thế
        close_buttons_layout = QHBoxLayout()
        
        self.close_position_btn = QPushButton("Đóng Vị Thế")
        self.close_position_btn.setStyleSheet("background-color: #EF4444; color: white; font-weight: bold;")
        close_buttons_layout.addWidget(self.close_position_btn)
        
        self.close_all_positions_btn = QPushButton("Đóng Tất Cả Vị Thế")
        self.close_all_positions_btn.setStyleSheet("background-color: #B91C1C; color: white; font-weight: bold;")
        close_buttons_layout.addWidget(self.close_all_positions_btn)
        
        position_layout.addLayout(close_buttons_layout, 2, 2, 1, 3)
        
        layout.addWidget(position_management)
        
        # Tạo nhóm lịch sử giao dịch
        history_group = QGroupBox("Lịch Sử Giao Dịch")
        history_layout = QVBoxLayout(history_group)
        
        # Bảng lịch sử
        self.trade_history_table = QTableWidget()
        self.trade_history_table.setColumnCount(8)
        self.trade_history_table.setHorizontalHeaderLabels([
            "Cặp Tiền", "Phía", "Kích Thước", "Giá Vào", "Giá Ra",
            "PnL", "Thời Gian Vào", "Thời Gian Ra"
        ])
        
        # Thiết lập chiều rộng cột
        header = self.trade_history_table.horizontalHeader()
        for i in range(8):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        
        history_layout.addWidget(self.trade_history_table)
        
        layout.addWidget(history_group)
    
    def create_market_analysis_tab(self):
        """Tạo tab phân tích thị trường"""
        analysis_tab = QWidget()
        self.tabs.addTab(analysis_tab, "Phân Tích Thị Trường")
        
        # Layout cho tab
        layout = QVBoxLayout(analysis_tab)
        
        # Tạo form phân tích
        form_group = QGroupBox("Phân Tích Kỹ Thuật")
        form_layout = QGridLayout(form_group)
        
        # Lựa chọn cặp tiền và khung thời gian
        form_layout.addWidget(QLabel("Cặp Tiền:"), 0, 0)
        self.analysis_symbol = QComboBox()
        self.analysis_symbol.addItems([
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT",
            "DOGEUSDT", "XRPUSDT", "DOTUSDT", "LINKUSDT", "AVAXUSDT"
        ])
        form_layout.addWidget(self.analysis_symbol, 0, 1)
        
        form_layout.addWidget(QLabel("Khung Thời Gian:"), 0, 2)
        self.analysis_timeframe = QComboBox()
        self.analysis_timeframe.addItems(["5m", "15m", "1h", "4h", "1d"])
        self.analysis_timeframe.setCurrentIndex(2)  # 1h default
        form_layout.addWidget(self.analysis_timeframe, 0, 3)
        
        # Nút phân tích
        self.analyze_btn = QPushButton("Phân Tích")
        self.analyze_btn.setStyleSheet("background-color: #3B82F6; color: white; font-weight: bold;")
        form_layout.addWidget(self.analyze_btn, 0, 4)
        
        layout.addWidget(form_group)
        
        # Tạo khu vực hiển thị kết quả phân tích
        results_group = QGroupBox("Kết Quả Phân Tích")
        results_layout = QGridLayout(results_group)
        
        # Giá và xu hướng
        results_layout.addWidget(QLabel("Giá Hiện Tại:"), 0, 0)
        self.analysis_price_label = QLabel("0.00 USDT")
        self.analysis_price_label.setStyleSheet("font-weight: bold;")
        results_layout.addWidget(self.analysis_price_label, 0, 1)
        
        results_layout.addWidget(QLabel("Xu Hướng:"), 0, 2)
        self.analysis_trend_label = QLabel("Không xác định")
        self.analysis_trend_label.setStyleSheet("font-weight: bold;")
        results_layout.addWidget(self.analysis_trend_label, 0, 3)
        
        # RSI và MACD
        results_layout.addWidget(QLabel("RSI (14):"), 1, 0)
        self.analysis_rsi_label = QLabel("0.00")
        self.analysis_rsi_label.setStyleSheet("font-weight: bold;")
        results_layout.addWidget(self.analysis_rsi_label, 1, 1)
        
        results_layout.addWidget(QLabel("MACD:"), 1, 2)
        self.analysis_macd_label = QLabel("0.00, 0.00, 0.00")
        self.analysis_macd_label.setStyleSheet("font-weight: bold;")
        results_layout.addWidget(self.analysis_macd_label, 1, 3)
        
        # Bollinger Bands và ATR
        results_layout.addWidget(QLabel("Bollinger Bands:"), 2, 0)
        self.analysis_bb_label = QLabel("0.00, 0.00, 0.00")
        self.analysis_bb_label.setStyleSheet("font-weight: bold;")
        results_layout.addWidget(self.analysis_bb_label, 2, 1)
        
        results_layout.addWidget(QLabel("ATR (14):"), 2, 2)
        self.analysis_atr_label = QLabel("0.00")
        self.analysis_atr_label.setStyleSheet("font-weight: bold;")
        results_layout.addWidget(self.analysis_atr_label, 2, 3)
        
        # Hỗ trợ và kháng cự
        results_layout.addWidget(QLabel("Vùng Hỗ Trợ:"), 3, 0)
        self.analysis_support_label = QLabel("0.00, 0.00, 0.00")
        self.analysis_support_label.setStyleSheet("color: #10B981; font-weight: bold;")
        results_layout.addWidget(self.analysis_support_label, 3, 1)
        
        results_layout.addWidget(QLabel("Vùng Kháng Cự:"), 3, 2)
        self.analysis_resistance_label = QLabel("0.00, 0.00, 0.00")
        self.analysis_resistance_label.setStyleSheet("color: #EF4444; font-weight: bold;")
        results_layout.addWidget(self.analysis_resistance_label, 3, 3)
        
        # Khuyến nghị
        results_layout.addWidget(QLabel("Khuyến Nghị:"), 4, 0)
        self.analysis_recommendation_label = QLabel("Không xác định")
        self.analysis_recommendation_label.setStyleSheet("font-weight: bold;")
        results_layout.addWidget(self.analysis_recommendation_label, 4, 1, 1, 3)
        
        layout.addWidget(results_group)
        
        # Tạo nhóm tín hiệu giao dịch
        signals_group = QGroupBox("Tín Hiệu Giao Dịch")
        signals_layout = QVBoxLayout(signals_group)
        
        # Bảng tín hiệu
        self.signals_table = QTableWidget()
        self.signals_table.setColumnCount(6)
        self.signals_table.setHorizontalHeaderLabels([
            "Cặp Tiền", "Khung TG", "Tín Hiệu", "Loại", "Giá", "Độ Mạnh"
        ])
        
        # Thiết lập chiều rộng cột
        header = self.signals_table.horizontalHeader()
        for i in range(6):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        
        signals_layout.addWidget(self.signals_table)
        
        layout.addWidget(signals_group)
    
    def create_settings_tab(self):
        """Tạo tab cài đặt"""
        settings_tab = QWidget()
        self.tabs.addTab(settings_tab, "Cài Đặt")
        
        # Layout cho tab
        layout = QVBoxLayout(settings_tab)
        
        # Tạo nhiều tab con trong tab cài đặt
        settings_tabs = QTabWidget()
        layout.addWidget(settings_tabs)
        
        # Tab cài đặt API
        api_tab = QWidget()
        settings_tabs.addTab(api_tab, "Cài Đặt API")
        self.create_api_settings(api_tab)
        
        # Tab cài đặt giao dịch
        trading_tab = QWidget()
        settings_tabs.addTab(trading_tab, "Cài Đặt Giao Dịch")
        self.create_trading_settings(trading_tab)
        
        # Tab cài đặt rủi ro
        risk_tab = QWidget()
        settings_tabs.addTab(risk_tab, "Cài Đặt Rủi Ro")
        self.create_risk_settings(risk_tab)
        
        # Tab cài đặt thông báo
        notification_tab = QWidget()
        settings_tabs.addTab(notification_tab, "Cài Đặt Thông Báo")
        self.create_notification_settings(notification_tab)
        
        # Tab cài đặt giao diện
        ui_tab = QWidget()
        settings_tabs.addTab(ui_tab, "Cài Đặt Giao Diện")
        self.create_ui_settings(ui_tab)
    
    def create_api_settings(self, parent_widget):
        """Tạo cài đặt API"""
        layout = QVBoxLayout(parent_widget)
        
        # Group box cho cài đặt Binance API
        api_group = QGroupBox("Cài Đặt Binance API")
        api_layout = QFormLayout(api_group)
        
        # API Key
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        api_layout.addRow("API Key:", self.api_key_input)
        
        # API Secret
        self.api_secret_input = QLineEdit()
        self.api_secret_input.setEchoMode(QLineEdit.Password)
        api_layout.addRow("API Secret:", self.api_secret_input)
        
        # Chế độ API
        self.api_mode = QComboBox()
        self.api_mode.addItems(["Testnet (Thử Nghiệm)", "Mainnet (Thực Tế)"])
        api_layout.addRow("Chế Độ API:", self.api_mode)
        
        # Nút kiểm tra kết nối
        self.test_api_btn = QPushButton("Kiểm Tra Kết Nối")
        self.test_api_btn.setStyleSheet("background-color: #3B82F6; color: white;")
        api_layout.addRow("", self.test_api_btn)
        
        # Thêm group vào layout chính
        layout.addWidget(api_group)
        
        # Group box cho cài đặt chung
        general_group = QGroupBox("Cài Đặt Chung")
        general_layout = QFormLayout(general_group)
        
        # Tần suất cập nhật
        self.update_interval = QSpinBox()
        self.update_interval.setRange(5, 60)
        self.update_interval.setValue(10)
        self.update_interval.setSuffix(" giây")
        general_layout.addRow("Tần Suất Cập Nhật:", self.update_interval)
        
        # Cặp tiền mặc định
        self.default_symbol = QComboBox()
        self.default_symbol.addItems([
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT"
        ])
        general_layout.addRow("Cặp Tiền Mặc Định:", self.default_symbol)
        
        # Khung thời gian mặc định
        self.default_timeframe = QComboBox()
        self.default_timeframe.addItems(["5m", "15m", "1h", "4h", "1d"])
        self.default_timeframe.setCurrentIndex(2)  # 1h default
        general_layout.addRow("Khung Thời Gian Mặc Định:", self.default_timeframe)
        
        # Thêm group vào layout chính
        layout.addWidget(general_group)
        
        # Nút lưu cài đặt
        save_layout = QHBoxLayout()
        
        self.save_api_settings_btn = QPushButton("Lưu Cài Đặt")
        self.save_api_settings_btn.setStyleSheet("background-color: #10B981; color: white; font-weight: bold;")
        save_layout.addWidget(self.save_api_settings_btn)
        
        self.reset_api_settings_btn = QPushButton("Khôi Phục Mặc Định")
        save_layout.addWidget(self.reset_api_settings_btn)
        
        layout.addLayout(save_layout)
        
        # Thêm stretch để đẩy các widget lên trên
        layout.addStretch()
    
    def create_trading_settings(self, parent_widget):
        """Tạo cài đặt giao dịch"""
        layout = QVBoxLayout(parent_widget)
        
        # Group box cho cài đặt giao dịch tự động
        auto_group = QGroupBox("Giao Dịch Tự Động")
        auto_layout = QVBoxLayout(auto_group)
        
        # Bật/tắt giao dịch tự động
        self.auto_trading = QCheckBox("Bật Giao Dịch Tự Động")
        auto_layout.addWidget(self.auto_trading)
        
        # Thiết lập giao dịch tự động
        auto_settings_layout = QFormLayout()
        
        # Tần suất kiểm tra tín hiệu
        self.signal_check_interval = QSpinBox()
        self.signal_check_interval.setRange(10, 300)
        self.signal_check_interval.setValue(30)
        self.signal_check_interval.setSuffix(" giây")
        auto_settings_layout.addRow("Tần Suất Kiểm Tra Tín Hiệu:", self.signal_check_interval)
        
        # Loại lệnh mặc định
        self.default_order_type = QComboBox()
        self.default_order_type.addItems(["Lệnh Thị Trường", "Lệnh Giới Hạn"])
        auto_settings_layout.addRow("Loại Lệnh Mặc Định:", self.default_order_type)
        
        # Danh sách cặp tiền giao dịch
        self.trading_pairs_group = QGroupBox("Cặp Tiền Giao Dịch")
        trading_pairs_layout = QVBoxLayout(self.trading_pairs_group)
        
        pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", 
                "DOGEUSDT", "XRPUSDT", "DOTUSDT", "LINKUSDT", "AVAXUSDT"]
        
        for pair in pairs:
            checkbox = QCheckBox(pair)
            checkbox.setChecked(pair in ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
            trading_pairs_layout.addWidget(checkbox)
        
        auto_settings_layout.addRow(self.trading_pairs_group)
        
        auto_layout.addLayout(auto_settings_layout)
        
        # Thêm group vào layout chính
        layout.addWidget(auto_group)
        
        # Group box cho lọc tín hiệu
        filter_group = QGroupBox("Lọc Tín Hiệu")
        filter_layout = QFormLayout(filter_group)
        
        # Độ mạnh tín hiệu tối thiểu
        self.min_signal_strength = QDoubleSpinBox()
        self.min_signal_strength.setRange(0, 100)
        self.min_signal_strength.setValue(70)
        self.min_signal_strength.setSuffix("%")
        filter_layout.addRow("Độ Mạnh Tín Hiệu Tối Thiểu:", self.min_signal_strength)
        
        # Xác nhận nhiều chỉ báo
        self.multi_indicator_confirm = QCheckBox("Yêu Cầu Xác Nhận Từ Nhiều Chỉ Báo")
        self.multi_indicator_confirm.setChecked(True)
        filter_layout.addRow("", self.multi_indicator_confirm)
        
        # Loại bỏ tín hiệu nhiễu
        self.filter_noise = QCheckBox("Loại Bỏ Tín Hiệu Nhiễu")
        self.filter_noise.setChecked(True)
        filter_layout.addRow("", self.filter_noise)
        
        # Thêm group vào layout chính
        layout.addWidget(filter_group)
        
        # Nút lưu cài đặt
        save_layout = QHBoxLayout()
        
        self.save_trading_settings_btn = QPushButton("Lưu Cài Đặt")
        self.save_trading_settings_btn.setStyleSheet("background-color: #10B981; color: white; font-weight: bold;")
        save_layout.addWidget(self.save_trading_settings_btn)
        
        self.reset_trading_settings_btn = QPushButton("Khôi Phục Mặc Định")
        save_layout.addWidget(self.reset_trading_settings_btn)
        
        layout.addLayout(save_layout)
        
        # Thêm stretch để đẩy các widget lên trên
        layout.addStretch()
    
    def create_risk_settings(self, parent_widget):
        """Tạo cài đặt rủi ro"""
        layout = QVBoxLayout(parent_widget)
        
        # Group box cho cài đặt rủi ro chung
        general_risk_group = QGroupBox("Cài Đặt Rủi Ro Chung")
        general_risk_layout = QFormLayout(general_risk_group)
        
        # Mức độ rủi ro
        self.risk_level = QComboBox()
        self.risk_level.addItems([
            "Cực kỳ thấp (0.5-1% mỗi giao dịch)",
            "Thấp (1.5-3% mỗi giao dịch)",
            "Trung bình (3-7% mỗi giao dịch)",
            "Cao (7-15% mỗi giao dịch)",
            "Cực kỳ cao (15-50% mỗi giao dịch)"
        ])
        self.risk_level.setCurrentIndex(2)  # Medium risk default
        general_risk_layout.addRow("Mức Độ Rủi Ro:", self.risk_level)
        
        # Phần trăm rủi ro mỗi giao dịch
        self.risk_per_trade = QDoubleSpinBox()
        self.risk_per_trade.setRange(0.1, 50.0)
        self.risk_per_trade.setValue(5.0)
        self.risk_per_trade.setSuffix("%")
        general_risk_layout.addRow("Phần Trăm Rủi Ro Mỗi Giao Dịch:", self.risk_per_trade)
        
        # Đòn bẩy tối đa
        self.max_leverage = QComboBox()
        for lev in [1, 2, 3, 5, 10, 20, 50, 100]:
            self.max_leverage.addItem(f"{lev}x", lev)
        self.max_leverage.setCurrentIndex(3)  # 5x default
        general_risk_layout.addRow("Đòn Bẩy Tối Đa:", self.max_leverage)
        
        # Số lệnh giao dịch tối đa
        self.max_concurrent_trades = QSpinBox()
        self.max_concurrent_trades.setRange(1, 20)
        self.max_concurrent_trades.setValue(5)
        general_risk_layout.addRow("Số Lệnh Giao Dịch Tối Đa:", self.max_concurrent_trades)
        
        # Thêm group vào layout chính
        layout.addWidget(general_risk_group)
        
        # Group box cho Stop Loss và Take Profit
        sltp_group = QGroupBox("Stop Loss và Take Profit")
        sltp_layout = QFormLayout(sltp_group)
        
        # SL mặc định
        self.default_sl = QDoubleSpinBox()
        self.default_sl.setRange(0.5, 50.0)
        self.default_sl.setValue(5.0)
        self.default_sl.setSuffix("%")
        sltp_layout.addRow("Stop Loss Mặc Định:", self.default_sl)
        
        # TP mặc định
        self.default_tp = QDoubleSpinBox()
        self.default_tp.setRange(0.5, 200.0)
        self.default_tp.setValue(15.0)
        self.default_tp.setSuffix("%")
        sltp_layout.addRow("Take Profit Mặc Định:", self.default_tp)
        
        # Tỷ lệ R:R tối thiểu
        self.min_rr_ratio = QDoubleSpinBox()
        self.min_rr_ratio.setRange(0.5, 10.0)
        self.min_rr_ratio.setValue(2.0)
        self.min_rr_ratio.setSingleStep(0.1)
        sltp_layout.addRow("Tỷ Lệ R:R Tối Thiểu:", self.min_rr_ratio)
        
        # Trailing stop
        self.use_trailing_stop = QCheckBox("Sử Dụng Trailing Stop")
        self.use_trailing_stop.setChecked(True)
        sltp_layout.addRow("", self.use_trailing_stop)
        
        self.trailing_stop_activation = QDoubleSpinBox()
        self.trailing_stop_activation.setRange(1.0, 100.0)
        self.trailing_stop_activation.setValue(10.0)
        self.trailing_stop_activation.setSuffix("%")
        sltp_layout.addRow("Kích Hoạt Trailing Stop Sau:", self.trailing_stop_activation)
        
        self.trailing_stop_distance = QDoubleSpinBox()
        self.trailing_stop_distance.setRange(0.1, 20.0)
        self.trailing_stop_distance.setValue(3.0)
        self.trailing_stop_distance.setSuffix("%")
        sltp_layout.addRow("Khoảng Cách Trailing Stop:", self.trailing_stop_distance)
        
        # Thêm group vào layout chính
        layout.addWidget(sltp_group)
        
        # Nút lưu cài đặt
        save_layout = QHBoxLayout()
        
        self.save_risk_settings_btn = QPushButton("Lưu Cài Đặt")
        self.save_risk_settings_btn.setStyleSheet("background-color: #10B981; color: white; font-weight: bold;")
        save_layout.addWidget(self.save_risk_settings_btn)
        
        self.reset_risk_settings_btn = QPushButton("Khôi Phục Mặc Định")
        save_layout.addWidget(self.reset_risk_settings_btn)
        
        layout.addLayout(save_layout)
        
        # Thêm stretch để đẩy các widget lên trên
        layout.addStretch()
    
    def create_notification_settings(self, parent_widget):
        """Tạo cài đặt thông báo"""
        layout = QVBoxLayout(parent_widget)
        
        # Group box cho cài đặt Telegram
        telegram_group = QGroupBox("Cài Đặt Telegram")
        telegram_layout = QFormLayout(telegram_group)
        
        # Bật/tắt thông báo Telegram
        self.enable_telegram = QCheckBox("Bật Thông Báo Telegram")
        self.enable_telegram.setChecked(True)
        telegram_layout.addRow("", self.enable_telegram)
        
        # Bot Token
        self.telegram_token = QLineEdit()
        telegram_layout.addRow("Bot Token:", self.telegram_token)
        
        # Chat ID
        self.telegram_chat_id = QLineEdit()
        telegram_layout.addRow("Chat ID:", self.telegram_chat_id)
        
        # Nút kiểm tra kết nối
        self.test_telegram_btn = QPushButton("Kiểm Tra Kết Nối")
        self.test_telegram_btn.setStyleSheet("background-color: #3B82F6; color: white;")
        telegram_layout.addRow("", self.test_telegram_btn)
        
        # Thêm group vào layout chính
        layout.addWidget(telegram_group)
        
        # Group box cho cài đặt loại thông báo
        notification_types_group = QGroupBox("Loại Thông Báo")
        notification_types_layout = QVBoxLayout(notification_types_group)
        
        # Các loại thông báo
        self.notify_new_position = QCheckBox("Mở Vị Thế Mới")
        self.notify_new_position.setChecked(True)
        notification_types_layout.addWidget(self.notify_new_position)
        
        self.notify_close_position = QCheckBox("Đóng Vị Thế")
        self.notify_close_position.setChecked(True)
        notification_types_layout.addWidget(self.notify_close_position)
        
        self.notify_sl_tp_update = QCheckBox("Cập Nhật SL/TP")
        self.notify_sl_tp_update.setChecked(True)
        notification_types_layout.addWidget(self.notify_sl_tp_update)
        
        self.notify_trading_signal = QCheckBox("Tín Hiệu Giao Dịch Mới")
        self.notify_trading_signal.setChecked(True)
        notification_types_layout.addWidget(self.notify_trading_signal)
        
        self.notify_market_analysis = QCheckBox("Phân Tích Thị Trường")
        self.notify_market_analysis.setChecked(True)
        notification_types_layout.addWidget(self.notify_market_analysis)
        
        self.notify_error = QCheckBox("Lỗi Hệ Thống")
        self.notify_error.setChecked(True)
        notification_types_layout.addWidget(self.notify_error)
        
        # Thêm group vào layout chính
        layout.addWidget(notification_types_group)
        
        # Nút lưu cài đặt
        save_layout = QHBoxLayout()
        
        self.save_notification_settings_btn = QPushButton("Lưu Cài Đặt")
        self.save_notification_settings_btn.setStyleSheet("background-color: #10B981; color: white; font-weight: bold;")
        save_layout.addWidget(self.save_notification_settings_btn)
        
        self.reset_notification_settings_btn = QPushButton("Khôi Phục Mặc Định")
        save_layout.addWidget(self.reset_notification_settings_btn)
        
        layout.addLayout(save_layout)
        
        # Thêm stretch để đẩy các widget lên trên
        layout.addStretch()
    
    def create_ui_settings(self, parent_widget):
        """Tạo cài đặt giao diện"""
        layout = QVBoxLayout(parent_widget)
        
        # Group box cho cài đặt theme
        theme_group = QGroupBox("Theme")
        theme_layout = QVBoxLayout(theme_group)
        
        # Radio buttons cho theme
        self.light_theme = QCheckBox("Giao Diện Sáng")
        theme_layout.addWidget(self.light_theme)
        
        self.dark_theme = QCheckBox("Giao Diện Tối")
        self.dark_theme.setChecked(True)
        theme_layout.addWidget(self.dark_theme)
        
        self.high_contrast_theme = QCheckBox("Giao Diện Tương Phản Cao")
        theme_layout.addWidget(self.high_contrast_theme)
        
        # Thêm group vào layout chính
        layout.addWidget(theme_group)
        
        # Group box cho cài đặt hiển thị
        display_group = QGroupBox("Hiển Thị")
        display_layout = QVBoxLayout(display_group)
        
        # Hiển thị các widget
        self.show_toolbar = QCheckBox("Hiển Thị Thanh Công Cụ")
        self.show_toolbar.setChecked(True)
        display_layout.addWidget(self.show_toolbar)
        
        self.show_status_bar = QCheckBox("Hiển Thị Thanh Trạng Thái")
        self.show_status_bar.setChecked(True)
        display_layout.addWidget(self.show_status_bar)
        
        self.show_account_info = QCheckBox("Hiển Thị Thông Tin Tài Khoản")
        self.show_account_info.setChecked(True)
        display_layout.addWidget(self.show_account_info)
        
        self.minimize_to_tray = QCheckBox("Thu Nhỏ Vào Khay Hệ Thống")
        self.minimize_to_tray.setChecked(True)
        display_layout.addWidget(self.minimize_to_tray)
        
        # Thêm group vào layout chính
        layout.addWidget(display_group)
        
        # Group box cho cài đặt ngôn ngữ
        language_group = QGroupBox("Ngôn Ngữ")
        language_layout = QVBoxLayout(language_group)
        
        # Combobox cho ngôn ngữ
        self.language = QComboBox()
        self.language.addItems(["Tiếng Việt", "English"])
        language_layout.addWidget(self.language)
        
        # Thêm group vào layout chính
        layout.addWidget(language_group)
        
        # Nút lưu cài đặt
        save_layout = QHBoxLayout()
        
        self.save_ui_settings_btn = QPushButton("Lưu Cài Đặt")
        self.save_ui_settings_btn.setStyleSheet("background-color: #10B981; color: white; font-weight: bold;")
        save_layout.addWidget(self.save_ui_settings_btn)
        
        self.reset_ui_settings_btn = QPushButton("Khôi Phục Mặc Định")
        save_layout.addWidget(self.reset_ui_settings_btn)
        
        layout.addLayout(save_layout)
        
        # Thêm stretch để đẩy các widget lên trên
        layout.addStretch()
    
    def init_threads(self):
        """Khởi tạo các thread cho ứng dụng"""
        # Thread cập nhật dữ liệu thị trường
        self.market_thread = MarketDataThread(interval=10, parent=self)
        self.market_thread.market_data_signal.connect(self.update_market_data)
        
        # Thread cập nhật dữ liệu tài khoản
        self.account_thread = AccountDataThread(interval=10, parent=self)
        self.account_thread.account_data_signal.connect(self.update_account_data)
        
        # Thread giao dịch tự động
        self.trading_thread = TradingThread(interval=30, parent=self)
        self.trading_thread.trading_signal.connect(self.update_trading_status)
        
        # Bắt đầu các thread
        self.market_thread.start()
        self.account_thread.start()
        self.trading_thread.start()
        
        logger.info("Đã khởi tạo và bắt đầu các thread")
    
    def update_market_data(self, data):
        """Cập nhật dữ liệu thị trường trên giao diện"""
        try:
            # Cập nhật giá BTC và ETH
            btc_price = data.get("btc_price", 0)
            eth_price = data.get("eth_price", 0)
            
            if btc_price:
                self.btc_price_label.setText(f"{btc_price:,.2f} USDT")
            
            if eth_price:
                self.eth_price_label.setText(f"{eth_price:,.2f} USDT")
            
            # Cập nhật chế độ thị trường
            market_regime = data.get("market_regime", {})
            regime = market_regime.get("regime", "Không xác định")
            
            regime_text = {
                "ranging": "Đi Ngang",
                "trending": "Xu Hướng",
                "volatile": "Biến Động Mạnh",
                "quiet": "Biến Động Thấp"
            }.get(regime, "Không xác định")
            
            self.market_regime_label.setText(regime_text)
            
            # Cập nhật các chỉ báo kỹ thuật trong tab phân tích
            symbol = self.analysis_symbol.currentText()
            indicators = data.get(f"{symbol}_indicators", {})
            
            if indicators:
                # RSI
                rsi = indicators.get("rsi", 0)
                self.analysis_rsi_label.setText(f"{rsi:.2f}")
                
                # MACD
                macd = indicators.get("macd", {})
                macd_line = macd.get("macd_line", 0)
                signal_line = macd.get("signal_line", 0)
                histogram = macd.get("histogram", 0)
                self.analysis_macd_label.setText(f"{macd_line:.4f}, {signal_line:.4f}, {histogram:.4f}")
                
                # Bollinger Bands
                bb = indicators.get("bollinger_bands", {})
                upper = bb.get("upper", 0)
                middle = bb.get("middle", 0)
                lower = bb.get("lower", 0)
                self.analysis_bb_label.setText(f"{lower:.2f}, {middle:.2f}, {upper:.2f}")
                
                # ATR
                atr = indicators.get("atr", 0)
                self.analysis_atr_label.setText(f"{atr:.4f}")
            
            # Cập nhật tín hiệu giao dịch
            signals = data.get("signals", [])
            
            if signals:
                self.signals_table.setRowCount(len(signals))
                
                for row, signal in enumerate(signals):
                    self.signals_table.setItem(row, 0, QTableWidgetItem(signal.get("symbol", "")))
                    self.signals_table.setItem(row, 1, QTableWidgetItem(signal.get("timeframe", "")))
                    
                    signal_type = signal.get("type", "")
                    signal_item = QTableWidgetItem(signal_type)
                    
                    if signal_type == "buy":
                        signal_item.setForeground(QColor("#10B981"))  # Green
                    elif signal_type == "sell":
                        signal_item.setForeground(QColor("#EF4444"))  # Red
                    
                    self.signals_table.setItem(row, 2, signal_item)
                    self.signals_table.setItem(row, 3, QTableWidgetItem(signal.get("indicator", "")))
                    self.signals_table.setItem(row, 4, QTableWidgetItem(f"{signal.get('price', 0):.2f}"))
                    
                    strength = signal.get("strength", 0)
                    strength_item = QTableWidgetItem(f"{strength:.2f}%")
                    
                    if strength > 80:
                        strength_item.setForeground(QColor("#10B981"))  # Strong (Green)
                    elif strength > 50:
                        strength_item.setForeground(QColor("#3B82F6"))  # Medium (Blue)
                    else:
                        strength_item.setForeground(QColor("#EF4444"))  # Weak (Red)
                    
                    self.signals_table.setItem(row, 5, strength_item)
            
            # Thêm vào hoạt động gần đây
            current_time = datetime.now().strftime("%H:%M:%S")
            self.add_activity(f"[{current_time}] Cập nhật dữ liệu thị trường: BTC={btc_price:,.2f}, ETH={eth_price:,.2f}")
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật dữ liệu thị trường: {str(e)}", exc_info=True)
    
    def update_account_data(self, data):
        """Cập nhật dữ liệu tài khoản trên giao diện"""
        try:
            # Cập nhật số dư tài khoản
            balance = data.get("balance", {})
            total_balance = balance.get("total_balance", 0)
            available_balance = balance.get("available_balance", 0)
            
            self.total_balance_label.setText(f"{total_balance:,.2f} USDT")
            self.available_balance_label.setText(f"{available_balance:,.2f} USDT")
            
            # Cập nhật PnL
            total_pnl = data.get("total_pnl", 0)
            self.unrealized_pnl_label.setText(f"{total_pnl:,.2f} USDT")
            
            if total_pnl > 0:
                self.unrealized_pnl_label.setStyleSheet("color: #10B981; font-weight: bold; font-size: 14px;")
            elif total_pnl < 0:
                self.unrealized_pnl_label.setStyleSheet("color: #EF4444; font-weight: bold; font-size: 14px;")
            else:
                self.unrealized_pnl_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            
            # Cập nhật danh sách vị thế
            positions = data.get("positions", [])
            
            if positions:
                # Cập nhật bảng vị thế trong tab tổng quan
                self.positions_table.setRowCount(len(positions))
                
                # Cập nhật bảng vị thế chi tiết trong tab quản lý vị thế
                self.detail_positions_table.setRowCount(len(positions))
                
                for row, position in enumerate(positions):
                    symbol = position.get("symbol", "")
                    side = position.get("side", "")
                    size = position.get("size", 0)
                    entry_price = position.get("entry_price", 0)
                    current_price = position.get("current_price", 0)
                    pnl = position.get("unrealized_pnl", 0)
                    sl = position.get("stop_loss", 0)
                    tp = position.get("take_profit", 0)
                    open_time = position.get("open_time", "")
                    
                    # Định dạng phía giao dịch
                    side_text = "MUA" if side.upper() == "BUY" else "BÁN"
                    side_color = "#10B981" if side.upper() == "BUY" else "#EF4444"
                    
                    # Bảng vị thế trong tab tổng quan
                    self.positions_table.setItem(row, 0, QTableWidgetItem(symbol))
                    
                    side_item = QTableWidgetItem(side_text)
                    side_item.setForeground(QColor(side_color))
                    self.positions_table.setItem(row, 1, side_item)
                    
                    self.positions_table.setItem(row, 2, QTableWidgetItem(f"{size:.4f}"))
                    self.positions_table.setItem(row, 3, QTableWidgetItem(f"{entry_price:.2f}"))
                    self.positions_table.setItem(row, 4, QTableWidgetItem(f"{current_price:.2f}"))
                    
                    pnl_item = QTableWidgetItem(f"{pnl:.2f}")
                    pnl_item.setForeground(QColor("#10B981" if pnl >= 0 else "#EF4444"))
                    self.positions_table.setItem(row, 5, pnl_item)
                    
                    self.positions_table.setItem(row, 6, QTableWidgetItem(f"{sl:.2f}"))
                    self.positions_table.setItem(row, 7, QTableWidgetItem(f"{tp:.2f}"))
                    
                    # Bảng vị thế chi tiết trong tab quản lý vị thế (tương tự nhưng với thao tác)
                    self.detail_positions_table.setItem(row, 0, QTableWidgetItem(symbol))
                    
                    side_item = QTableWidgetItem(side_text)
                    side_item.setForeground(QColor(side_color))
                    self.detail_positions_table.setItem(row, 1, side_item)
                    
                    self.detail_positions_table.setItem(row, 2, QTableWidgetItem(f"{size:.4f}"))
                    self.detail_positions_table.setItem(row, 3, QTableWidgetItem(f"{entry_price:.2f}"))
                    self.detail_positions_table.setItem(row, 4, QTableWidgetItem(f"{current_price:.2f}"))
                    
                    pnl_item = QTableWidgetItem(f"{pnl:.2f}")
                    pnl_item.setForeground(QColor("#10B981" if pnl >= 0 else "#EF4444"))
                    self.detail_positions_table.setItem(row, 5, pnl_item)
                    
                    self.detail_positions_table.setItem(row, 6, QTableWidgetItem(f"{sl:.2f}"))
                    self.detail_positions_table.setItem(row, 7, QTableWidgetItem(f"{tp:.2f}"))
                    self.detail_positions_table.setItem(row, 8, QTableWidgetItem(open_time))
                    
                    # Thêm nút đóng vị thế
                    btn_widget = QWidget()
                    btn_layout = QHBoxLayout(btn_widget)
                    btn_layout.setContentsMargins(0, 0, 0, 0)
                    
                    close_btn = QPushButton("Đóng")
                    close_btn.setStyleSheet("background-color: #EF4444; color: white;")
                    close_btn.clicked.connect(lambda checked, s=symbol, sd=side: self.close_position_clicked(s, sd))
                    
                    edit_btn = QPushButton("SL/TP")
                    edit_btn.setStyleSheet("background-color: #3B82F6; color: white;")
                    edit_btn.clicked.connect(lambda checked, s=symbol, sd=side, sl_val=sl, tp_val=tp: self.edit_sltp_clicked(s, sd, sl_val, tp_val))
                    
                    btn_layout.addWidget(close_btn)
                    btn_layout.addWidget(edit_btn)
                    
                    self.detail_positions_table.setCellWidget(row, 9, btn_widget)
                
                # Cập nhật combobox vị thế
                self.position_symbol.clear()
                self.position_symbol.addItems([pos.get("symbol", "") for pos in positions])
                
                # Tính tổng giá trị vị thế
                total_position_value = sum(pos.get("size", 0) * pos.get("current_price", 0) for pos in positions)
                self.position_value_label.setText(f"{total_position_value:,.2f} USDT")
            else:
                # Nếu không có vị thế nào, xóa bảng
                self.positions_table.setRowCount(0)
                self.detail_positions_table.setRowCount(0)
                self.position_symbol.clear()
                self.position_value_label.setText("0.00 USDT")
            
            # Cập nhật lịch sử giao dịch
            trade_history = data.get("trade_history", [])
            
            if trade_history:
                self.trade_history_table.setRowCount(len(trade_history))
                
                for row, trade in enumerate(trade_history):
                    symbol = trade.get("symbol", "")
                    side = trade.get("side", "")
                    size = trade.get("size", 0)
                    entry_price = trade.get("entry_price", 0)
                    exit_price = trade.get("exit_price", 0)
                    pnl = trade.get("realized_pnl", 0)
                    open_time = trade.get("open_time", "")
                    close_time = trade.get("close_time", "")
                    
                    # Định dạng phía giao dịch
                    side_text = "MUA" if side.upper() == "BUY" else "BÁN"
                    side_color = "#10B981" if side.upper() == "BUY" else "#EF4444"
                    
                    self.trade_history_table.setItem(row, 0, QTableWidgetItem(symbol))
                    
                    side_item = QTableWidgetItem(side_text)
                    side_item.setForeground(QColor(side_color))
                    self.trade_history_table.setItem(row, 1, side_item)
                    
                    self.trade_history_table.setItem(row, 2, QTableWidgetItem(f"{size:.4f}"))
                    self.trade_history_table.setItem(row, 3, QTableWidgetItem(f"{entry_price:.2f}"))
                    self.trade_history_table.setItem(row, 4, QTableWidgetItem(f"{exit_price:.2f}"))
                    
                    pnl_item = QTableWidgetItem(f"{pnl:.2f}")
                    pnl_item.setForeground(QColor("#10B981" if pnl >= 0 else "#EF4444"))
                    self.trade_history_table.setItem(row, 5, pnl_item)
                    
                    self.trade_history_table.setItem(row, 6, QTableWidgetItem(open_time))
                    self.trade_history_table.setItem(row, 7, QTableWidgetItem(close_time))
            
            # Thêm vào hoạt động gần đây
            current_time = datetime.now().strftime("%H:%M:%S")
            self.add_activity(f"[{current_time}] Cập nhật dữ liệu tài khoản: Số dư={total_balance:,.2f}, PnL={total_pnl:,.2f}")
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật dữ liệu tài khoản: {str(e)}", exc_info=True)
    
    def update_trading_status(self, data):
        """Cập nhật trạng thái giao dịch tự động"""
        try:
            status = data.get("status", "unknown")
            timestamp = data.get("timestamp", "")
            
            if status == "disabled":
                self.update_status("Giao dịch tự động: TẮT")
            elif status == "running":
                self.update_status(f"Giao dịch tự động: ĐANG CHẠY ({timestamp})")
                
                # Xử lý các hành động giao dịch
                actions = data.get("actions", [])
                
                for action in actions:
                    action_type = action.get("type", "")
                    symbol = action.get("symbol", "")
                    side = action.get("side", "")
                    result = action.get("result", {})
                    reason = action.get("reason", "")
                    
                    # Định dạng phía giao dịch
                    side_text = "MUA" if side.upper() == "BUY" else "BÁN"
                    
                    if action_type == "open":
                        size = action.get("size", 0)
                        stop_loss = action.get("stop_loss", 0)
                        take_profit = action.get("take_profit", 0)
                        
                        # Thêm vào hoạt động gần đây
                        self.add_activity(
                            f"[{timestamp}] Mở vị thế {symbol} {side_text}, Kích thước: {size:.4f}, "
                            f"SL: {stop_loss:.2f}, TP: {take_profit:.2f} - {reason}"
                        )
                    
                    elif action_type == "close":
                        size = action.get("size", 0)
                        
                        # Thêm vào hoạt động gần đây
                        self.add_activity(
                            f"[{timestamp}] Đóng vị thế {symbol} {side_text}, Kích thước: {size:.4f} - {reason}"
                        )
                    
                    elif action_type == "adjust_sl_tp":
                        new_sl = action.get("new_sl", 0)
                        new_tp = action.get("new_tp", 0)
                        
                        # Thêm vào hoạt động gần đây
                        self.add_activity(
                            f"[{timestamp}] Điều chỉnh SL/TP {symbol} {side_text}, "
                            f"SL mới: {new_sl:.2f}, TP mới: {new_tp:.2f} - {reason}"
                        )
            
            elif status == "error":
                error = data.get("error", "Không xác định")
                self.update_status(f"Lỗi giao dịch tự động: {error}")
                
                # Thêm vào hoạt động gần đây
                self.add_activity(f"[{timestamp}] LỖI: {error}")
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật trạng thái giao dịch: {str(e)}", exc_info=True)
    
    def update_status(self, message):
        """Cập nhật thanh trạng thái"""
        self.status_label.setText(message)
    
    def update_time(self):
        """Cập nhật đồng hồ"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.setText(current_time)
    
    def add_activity(self, message):
        """Thêm hoạt động vào nhật ký hoạt động"""
        # Thêm vào đầu nội dung
        current_text = self.activities_text.toPlainText()
        new_text = message + "\n" + current_text
        
        # Giới hạn số dòng (giữ 100 dòng gần nhất)
        lines = new_text.split("\n")
        if len(lines) > 100:
            lines = lines[:100]
        
        self.activities_text.setPlainText("\n".join(lines))
    
    def close_position_clicked(self, symbol, side):
        """Xử lý khi click nút đóng vị thế"""
        try:
            # Hiển thị hộp thoại xác nhận
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Xác Nhận Đóng Vị Thế")
            msg_box.setText(f"Bạn có chắc chắn muốn đóng vị thế {symbol} {side} không?")
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg_box.setDefaultButton(QMessageBox.No)
            
            response = msg_box.exec()
            
            if response == QMessageBox.Yes:
                logger.info(f"Đóng vị thế: {symbol} {side}")
                
                # TODO: Gọi API để đóng vị thế
                # Ví dụ: self.api.close_position(symbol, side)
                
                # Thêm vào nhật ký hoạt động
                current_time = datetime.now().strftime("%H:%M:%S")
                self.add_activity(f"[{current_time}] Đóng vị thế {symbol} {side}")
                
                # Hiển thị thông báo thành công
                QMessageBox.information(self, "Thành Công", f"Đã đóng vị thế {symbol} {side}")
        
        except Exception as e:
            logger.error(f"Lỗi khi đóng vị thế: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Lỗi", f"Lỗi khi đóng vị thế: {str(e)}")
    
    def edit_sltp_clicked(self, symbol, side, current_sl, current_tp):
        """Xử lý khi click nút chỉnh sửa SL/TP"""
        try:
            # Cập nhật giá trị SL/TP hiện tại
            self.position_symbol.setCurrentText(symbol)
            self.position_side.setCurrentText("MUA" if side.upper() == "BUY" else "BÁN")
            self.new_sl.setValue(current_sl)
            self.new_tp.setValue(current_tp)
            
            # Chuyển đến tab quản lý vị thế
            self.tabs.setCurrentIndex(2)
            
            # Thêm vào nhật ký hoạt động
            current_time = datetime.now().strftime("%H:%M:%S")
            self.add_activity(f"[{current_time}] Chỉnh sửa SL/TP cho {symbol} {side}")
        
        except Exception as e:
            logger.error(f"Lỗi khi chỉnh sửa SL/TP: {str(e)}", exc_info=True)
    
    def closeEvent(self, event):
        """Xử lý khi đóng ứng dụng"""
        try:
            # Hiển thị hộp thoại xác nhận
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Xác Nhận Thoát")
            msg_box.setText("Bạn có chắc chắn muốn thoát không?")
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg_box.setDefaultButton(QMessageBox.No)
            
            response = msg_box.exec()
            
            if response == QMessageBox.Yes:
                # Dừng các thread
                logger.info("Đang dừng các thread...")
                self.market_thread.stop()
                self.account_thread.stop()
                self.trading_thread.stop()
                
                # Chấp nhận sự kiện đóng
                event.accept()
            else:
                # Từ chối sự kiện đóng
                event.ignore()
        
        except Exception as e:
            logger.error(f"Lỗi khi đóng ứng dụng: {str(e)}", exc_info=True)
            event.accept()

def main():
    """Hàm chính để chạy ứng dụng"""
    try:
        app = QApplication(sys.argv)
        
        # Tạo và hiển thị cửa sổ chính
        window = TradingApp()
        window.show()
        
        # Chạy vòng lặp sự kiện
        sys.exit(app.exec_())
    
    except Exception as e:
        logger.critical(f"Lỗi không thể khởi động ứng dụng: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()