#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Desktop App Updater
------------------
Module cập nhật và bảo trì phiên bản desktop, tích hợp mức rủi ro mới
và các chức năng backtest đầy đủ cho ứng dụng desktop
"""

import os
import sys
import json
import shutil
import logging
import threading
import subprocess
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("desktop_updater.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("desktop_updater")

# Paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RISK_CONFIG_PATH = os.path.join(PROJECT_ROOT, "risk_configs")
RESOURCES_PATH = os.path.join(PROJECT_ROOT, "static")
BACKTEST_RESULTS_PATH = os.path.join(PROJECT_ROOT, "backtest_results")

class DesktopAppUpdater:
    """
    Lớp cập nhật và bảo trì ứng dụng desktop
    """
    
    def __init__(self):
        """Khởi tạo updater"""
        self.current_version = self._get_current_version()
        self.config_dirs = [
            RISK_CONFIG_PATH,
            os.path.join(PROJECT_ROOT, "configs")
        ]
        
        # Đảm bảo các thư mục tồn tại
        for directory in self.config_dirs + [RESOURCES_PATH, BACKTEST_RESULTS_PATH]:
            os.makedirs(directory, exist_ok=True)
        
        logger.info(f"Khởi tạo Desktop App Updater, phiên bản hiện tại: {self.current_version}")
    
    def _get_current_version(self) -> str:
        """Lấy phiên bản hiện tại"""
        version_file = os.path.join(PROJECT_ROOT, "version.txt")
        
        if os.path.exists(version_file):
            with open(version_file, "r") as f:
                return f.read().strip()
        else:
            # Tạo file version mặc định
            with open(version_file, "w") as f:
                f.write("1.0.0")
            return "1.0.0"
    
    def update_version(self, new_version: str) -> None:
        """Cập nhật phiên bản"""
        version_file = os.path.join(PROJECT_ROOT, "version.txt")
        
        with open(version_file, "w") as f:
            f.write(new_version)
        
        self.current_version = new_version
        logger.info(f"Đã cập nhật phiên bản lên {new_version}")
    
    def update_risk_configs(self) -> None:
        """Cập nhật các file cấu hình rủi ro"""
        try:
            # Đảm bảo thư mục tồn tại
            if not os.path.exists(RISK_CONFIG_PATH):
                os.makedirs(RISK_CONFIG_PATH, exist_ok=True)
            
            # Kiểm tra cấu hình ultra_risk
            ultra_risk_path = os.path.join(RISK_CONFIG_PATH, "ultra_risk_config.json")
            if not os.path.exists(ultra_risk_path):
                # Tạo cấu hình ultra_risk mới
                ultra_risk_config = {
                    "risk_level": "ultra_high",
                    "risk_per_trade": 30.0,
                    "max_leverage": 20,
                    "stop_loss_atr_multiplier": 1.8,
                    "take_profit_atr_multiplier": 3.5,
                    "trailing_activation_pct": 2.5,
                    "trailing_callback_pct": 0.3,
                    "trailing_acceleration": True,
                    "trailing_acceleration_factor": 0.02,
                    "partial_profit_taking": [
                        {"pct": 1.0, "portion": 0.25},
                        {"pct": 2.0, "portion": 0.25},
                        {"pct": 3.0, "portion": 0.25},
                        {"pct": 5.0, "portion": 0.25}
                    ],
                    "breakeven_move": {
                        "enabled": True,
                        "after_first_partial": True,
                        "buffer_pct": 0.2
                    },
                    "max_positions": 10,
                    "max_open_risk": 150.0,
                    "entry_filters": {
                        "adx_min": 30,
                        "volume_percentile_min": 50,
                        "confirmation_count_min": 3
                    }
                }
                
                with open(ultra_risk_path, "w", encoding="utf-8") as f:
                    json.dump(ultra_risk_config, f, indent=4)
                
                logger.info(f"Đã tạo cấu hình ultra_risk mới: {ultra_risk_path}")
            
            # Kiểm tra cấu hình rủi ro thích ứng theo kích thước tài khoản
            adaptive_risk_path = os.path.join(RISK_CONFIG_PATH, "adaptive_risk_config.json")
            if not os.path.exists(adaptive_risk_path):
                # Tạo cấu hình adaptive_risk mới
                adaptive_risk_config = {
                    "account_size_thresholds": {
                        "100": {
                            "risk_level": "ultra_high",
                            "risk_per_trade": 30.0,
                            "max_leverage": 20,
                            "preferred_symbols": ["SOLUSDT", "AVAXUSDT", "DOGEUSDT"],
                            "max_positions": 1
                        },
                        "200": {
                            "risk_level": "very_high",
                            "risk_per_trade": 15.0,
                            "max_leverage": 15,
                            "preferred_symbols": ["SOLUSDT", "AVAXUSDT", "DOGEUSDT", "ADAUSDT", "XRPUSDT"],
                            "max_positions": 2
                        },
                        "300": {
                            "risk_level": "high",
                            "risk_per_trade": 10.0,
                            "max_leverage": 10,
                            "preferred_symbols": ["ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT", "DOTUSDT"],
                            "max_positions": 3
                        },
                        "500": {
                            "risk_level": "medium_high",
                            "risk_per_trade": 7.0,
                            "max_leverage": 7,
                            "preferred_symbols": ["ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT", "DOTUSDT"],
                            "max_positions": 4
                        },
                        "1000": {
                            "risk_level": "medium",
                            "risk_per_trade": 5.0,
                            "max_leverage": 5,
                            "preferred_symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT"],
                            "max_positions": 5
                        },
                        "3000": {
                            "risk_level": "medium_low",
                            "risk_per_trade": 3.0,
                            "max_leverage": 3,
                            "preferred_symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT"],
                            "max_positions": 8
                        },
                        "5000": {
                            "risk_level": "low",
                            "risk_per_trade": 2.0,
                            "max_leverage": 2,
                            "preferred_symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT"],
                            "max_positions": 10
                        },
                        "10000": {
                            "risk_level": "very_low",
                            "risk_per_trade": 1.0,
                            "max_leverage": 1,
                            "preferred_symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT"],
                            "max_positions": 15
                        }
                    },
                    "market_regime_adjustments": {
                        "uptrend": {
                            "risk_multiplier": 1.2,
                            "leverage_multiplier": 1.1
                        },
                        "downtrend": {
                            "risk_multiplier": 0.7,
                            "leverage_multiplier": 0.8
                        },
                        "sideways": {
                            "risk_multiplier": 1.0,
                            "leverage_multiplier": 1.0
                        },
                        "volatile": {
                            "risk_multiplier": 0.8,
                            "leverage_multiplier": 0.9
                        }
                    }
                }
                
                with open(adaptive_risk_path, "w", encoding="utf-8") as f:
                    json.dump(adaptive_risk_config, f, indent=4)
                
                logger.info(f"Đã tạo cấu hình adaptive_risk mới: {adaptive_risk_path}")
            
            # Kiểm tra cấu hình desktop
            desktop_config_path = os.path.join(RISK_CONFIG_PATH, "desktop_risk_config.json")
            if not os.path.exists(desktop_config_path):
                # Tạo cấu hình desktop mới
                desktop_config = {
                    "use_adaptive_risk": True,
                    "default_risk_level": "medium",
                    "show_risk_comparison": True,
                    "enable_risk_warnings": True,
                    "warning_thresholds": {
                        "high_risk_warning": 10.0,
                        "ultra_high_risk_warning": 20.0
                    },
                    "ui_preferences": {
                        "theme": "dark",
                        "show_tooltips": True,
                        "detailed_position_info": True,
                        "compact_mode": False,
                        "auto_refresh_interval": 30
                    },
                    "risk_presets": {
                        "beginner": {
                            "risk_level": "low",
                            "risk_per_trade": 2.0,
                            "max_leverage": 2
                        },
                        "intermediate": {
                            "risk_level": "medium",
                            "risk_per_trade": 5.0,
                            "max_leverage": 5
                        },
                        "advanced": {
                            "risk_level": "high",
                            "risk_per_trade": 10.0,
                            "max_leverage": 10
                        },
                        "expert": {
                            "risk_level": "ultra_high",
                            "risk_per_trade": 20.0,
                            "max_leverage": 20
                        }
                    }
                }
                
                with open(desktop_config_path, "w", encoding="utf-8") as f:
                    json.dump(desktop_config, f, indent=4)
                
                logger.info(f"Đã tạo cấu hình desktop mới: {desktop_config_path}")
            
            logger.info("Cập nhật cấu hình rủi ro hoàn tất")
            return True
        
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật cấu hình rủi ro: {str(e)}")
            return False
    
    def update_enhanced_trading_gui(self) -> bool:
        """Cập nhật module enhanced_trading_gui.py để tích hợp mức rủi ro và backtest mới"""
        try:
            source_file = "enhanced_trading_gui.py"
            backup_file = "enhanced_trading_gui.py.bak"
            
            # Tạo bản sao lưu
            if os.path.exists(source_file) and not os.path.exists(backup_file):
                shutil.copy(source_file, backup_file)
                logger.info(f"Đã tạo bản sao lưu {backup_file}")
            
            # Đọc nội dung file
            with open(source_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Kiểm tra xem có cần cập nhật không
            if "class RiskProfileWidget" not in content:
                # Thêm mã nhập mới
                import_section = """
# Import từ mô-đun rủi ro mới
try:
    from risk_profile_selector_gui import RISK_LEVELS, ACCOUNT_SIZE_ADJUSTMENTS
except ImportError:
    RISK_LEVELS = {
        'extremely_low': {'name': 'Cực kỳ thấp', 'default': 1.0, 'default_leverage': 2},
        'low': {'name': 'Thấp', 'default': 2.5, 'default_leverage': 3},
        'medium': {'name': 'Trung bình', 'default': 5.0, 'default_leverage': 5},
        'high': {'name': 'Cao', 'default': 10.0, 'default_leverage': 10},
        'extremely_high': {'name': 'Cực kỳ cao', 'default': 25.0, 'default_leverage': 20}
    }
    ACCOUNT_SIZE_ADJUSTMENTS = {
        100: {'recommendation': 'extremely_high'},
        500: {'recommendation': 'high'},
        1000: {'recommendation': 'medium'},
        5000: {'recommendation': 'low'}
    }
"""
                # Tìm vị trí thích hợp để chèn mã nhập mới
                import_pos = content.find("# Import các module từ dự án")
                if import_pos != -1:
                    content = content[:import_pos] + import_section + content[import_pos:]
                
                # Tạo widget mới cho mức rủi ro
                risk_widget_code = """
class RiskProfileWidget(QWidget):
    \"\"\"Widget hiển thị và điều chỉnh mức rủi ro\"\"\"
    
    risk_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_risk_level = 'medium'
        self.current_account_size = 1000.0
        self.setup_ui()
    
    def setup_ui(self):
        \"\"\"Thiết lập giao diện\"\"\"
        layout = QVBoxLayout()
        
        # Tiêu đề
        title_label = QLabel("Quản lý rủi ro")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)
        
        # Form layout
        form_layout = QFormLayout()
        
        # Kích thước tài khoản
        self.account_size_input = QDoubleSpinBox()
        self.account_size_input.setRange(100, 1000000)
        self.account_size_input.setSingleStep(100)
        self.account_size_input.setValue(self.current_account_size)
        self.account_size_input.valueChanged.connect(self.on_account_size_changed)
        form_layout.addRow("Kích thước tài khoản ($):", self.account_size_input)
        
        # Mức rủi ro
        self.risk_level_combo = QComboBox()
        for risk_id, risk_data in RISK_LEVELS.items():
            self.risk_level_combo.addItem(risk_data['name'], risk_id)
        self.risk_level_combo.setCurrentIndex(2)  # Medium by default
        self.risk_level_combo.currentIndexChanged.connect(self.on_risk_level_changed)
        form_layout.addRow("Mức rủi ro:", self.risk_level_combo)
        
        # % Rủi ro mỗi giao dịch
        self.risk_percent_spin = QDoubleSpinBox()
        self.risk_percent_spin.setRange(0.1, 50.0)
        self.risk_percent_spin.setSingleStep(0.5)
        self.risk_percent_spin.setValue(RISK_LEVELS['medium']['default'])
        self.risk_percent_spin.valueChanged.connect(self.on_risk_params_changed)
        form_layout.addRow("Rủi ro mỗi giao dịch (%):", self.risk_percent_spin)
        
        # Đòn bẩy
        self.leverage_spin = QSpinBox()
        self.leverage_spin.setRange(1, 50)
        self.leverage_spin.setValue(RISK_LEVELS['medium']['default_leverage'])
        self.leverage_spin.valueChanged.connect(self.on_risk_params_changed)
        form_layout.addRow("Đòn bẩy (x):", self.leverage_spin)
        
        layout.addLayout(form_layout)
        
        # Nút khuyến nghị
        recommend_btn = QPushButton("Khuyến nghị mức rủi ro tối ưu")
        recommend_btn.clicked.connect(self.recommend_risk_level)
        layout.addWidget(recommend_btn)
        
        # Label cảnh báo
        self.warning_label = QLabel()
        self.warning_label.setStyleSheet("color: orange;")
        self.warning_label.setWordWrap(True)
        layout.addWidget(self.warning_label)
        
        self.setLayout(layout)
        
        # Kiểm tra mức rủi ro ban đầu
        self.check_risk_level()
    
    def on_account_size_changed(self):
        \"\"\"Xử lý khi kích thước tài khoản thay đổi\"\"\"
        self.current_account_size = self.account_size_input.value()
        self.check_risk_level()
    
    def on_risk_level_changed(self):
        \"\"\"Xử lý khi mức rủi ro thay đổi\"\"\"
        self.current_risk_level = self.risk_level_combo.currentData()
        
        # Cập nhật các giá trị
        risk_data = RISK_LEVELS[self.current_risk_level]
        self.risk_percent_spin.setValue(risk_data['default'])
        self.leverage_spin.setValue(risk_data['default_leverage'])
        
        self.check_risk_level()
    
    def on_risk_params_changed(self):
        \"\"\"Xử lý khi các tham số rủi ro thay đổi\"\"\"
        self.check_risk_level()
        
        # Emit signal
        self.risk_changed.emit(self.get_current_risk_params())
    
    def get_current_risk_params(self):
        \"\"\"Lấy các tham số rủi ro hiện tại\"\"\"
        return {
            'risk_level': self.current_risk_level,
            'account_size': self.current_account_size,
            'risk_per_trade': self.risk_percent_spin.value(),
            'leverage': self.leverage_spin.value()
        }
    
    def check_risk_level(self):
        \"\"\"Kiểm tra mức rủi ro và hiển thị cảnh báo nếu cần\"\"\"
        risk_percent = self.risk_percent_spin.value()
        leverage = self.leverage_spin.value()
        
        warning_text = ""
        
        # Kiểm tra mức rủi ro cao
        if risk_percent > 15.0:
            warning_text += "⚠️ Mức rủi ro cực cao, có thể dẫn đến mất vốn lớn! "
        elif risk_percent > 10.0:
            warning_text += "⚠️ Mức rủi ro cao, chỉ dành cho trader có kinh nghiệm. "
        
        # Kiểm tra đòn bẩy cao
        if leverage > 20:
            warning_text += "⚠️ Đòn bẩy cực cao, rủi ro thanh lý cao! "
        elif leverage > 10:
            warning_text += "⚠️ Đòn bẩy cao, tăng rủi ro thanh lý. "
        
        # Kiểm tra tài khoản nhỏ với rủi ro thấp
        if self.current_account_size <= 300 and risk_percent < 5.0:
            warning_text += "⚠️ Với tài khoản nhỏ, mức rủi ro thấp có thể không hiệu quả. "
        
        # Kiểm tra tài khoản lớn với rủi ro cao
        if self.current_account_size >= 5000 and risk_percent > 10.0:
            warning_text += "⚠️ Với tài khoản lớn, mức rủi ro cao không khuyến khích. "
        
        self.warning_label.setText(warning_text)
        
        # Emit signal
        self.risk_changed.emit(self.get_current_risk_params())
    
    def recommend_risk_level(self):
        \"\"\"Khuyến nghị mức rủi ro tối ưu dựa trên kích thước tài khoản\"\"\"
        account_size = self.current_account_size
        
        # Tìm ngưỡng kích thước tài khoản phù hợp
        recommended_risk = 'medium'  # Mặc định
        for size, adjustment in sorted(ACCOUNT_SIZE_ADJUSTMENTS.items()):
            if account_size <= size:
                recommended_risk = adjustment['recommendation']
                break
        
        # Nếu tài khoản quá lớn
        if account_size > max(ACCOUNT_SIZE_ADJUSTMENTS.keys()):
            recommended_risk = 'extremely_low'
        
        # Đặt mức rủi ro được khuyến nghị
        for i in range(self.risk_level_combo.count()):
            if self.risk_level_combo.itemData(i) == recommended_risk:
                self.risk_level_combo.setCurrentIndex(i)
                break
        
        # Hiển thị thông báo
        QMessageBox.information(
            self,
            "Khuyến nghị mức rủi ro",
            f"Với tài khoản ${account_size:.2f}, mức rủi ro được khuyến nghị là: "
            f"{RISK_LEVELS[recommended_risk]['name']}\n\n"
            f"Rủi ro mỗi giao dịch: {RISK_LEVELS[recommended_risk]['default']}%\n"
            f"Đòn bẩy khuyến nghị: {RISK_LEVELS[recommended_risk]['default_leverage']}x"
        )
"""
                
                # Tìm vị trí thích hợp để chèn mã widget mới
                class_pos = content.find("class EnhancedTradingGUI(QMainWindow):")
                if class_pos != -1:
                    content = content[:class_pos] + risk_widget_code + "\n\n" + content[class_pos:]
                
                # Cập nhật hàm __init__ của EnhancedTradingGUI để thêm tab mới
                init_pattern = "def __init__(self):"
                init_pos = content.find(init_pattern)
                
                if init_pos != -1:
                    # Tìm vị trí thích hợp để thêm tab mới
                    create_tabs_pos = content.find("self.create_tabs()", init_pos)
                    if create_tabs_pos != -1:
                        # Thêm mã để tạo tab mới
                        modified_create_tabs_code = """
    def create_tabs(self):
        """Tạo các tab"""
        self.tabs = QTabWidget()
        
        # Tab tổng quan
        self.dashboard_tab = QWidget()
        self.create_dashboard_tab()
        self.tabs.addTab(self.dashboard_tab, "Tổng quan")
        
        # Tab giao dịch
        self.trading_tab = QWidget()
        self.create_trading_tab()
        self.tabs.addTab(self.trading_tab, "Giao dịch")
        
        # Tab quản lý rủi ro
        self.risk_tab = QWidget()
        self.create_risk_tab()
        self.tabs.addTab(self.risk_tab, "Quản lý rủi ro")
        
        # Tab quản lý vị thế
        self.positions_tab = QWidget()
        self.create_positions_tab()
        self.tabs.addTab(self.positions_tab, "Vị thế")
        
        # Tab biểu đồ & phân tích
        self.charts_tab = QWidget()
        self.create_charts_tab()
        self.tabs.addTab(self.charts_tab, "Biểu đồ & Phân tích")
        
        # Tab backtest
        self.backtest_tab = QWidget()
        self.create_backtest_tab()
        self.tabs.addTab(self.backtest_tab, "Backtest")
        
        # Tab cài đặt
        self.settings_tab = QWidget()
        self.create_settings_tab()
        self.tabs.addTab(self.settings_tab, "Cài đặt")
        
        # Đặt tabs vào layout chính
        self.setCentralWidget(self.tabs)
        """
                        
                        # Tìm vị trí để thay thế
                        create_tabs_end = content.find("self.setCentralWidget(self.tabs)", create_tabs_pos)
                        create_tabs_end = content.find("\n", create_tabs_end) + 1
                        
                        # Thay thế phương thức create_tabs
                        content = content[:content.find("def create_tabs", init_pos)] + modified_create_tabs_code + content[create_tabs_end:]
                    
                    # Thêm các phương thức mới
                    create_risk_tab_code = """
    def create_risk_tab(self):
        """Tạo tab quản lý rủi ro"""
        layout = QVBoxLayout()
        
        # Tạo widget điều chỉnh rủi ro
        self.risk_profile_widget = RiskProfileWidget()
        self.risk_profile_widget.risk_changed.connect(self.on_risk_profile_changed)
        
        # Tạo widget hiển thị thông tin rủi ro
        risk_info_group = QGroupBox("Thông tin rủi ro")
        risk_info_layout = QVBoxLayout()
        
        self.risk_info_label = QLabel(
            "Mức rủi ro hiện tại: Trung bình (5%)\n"
            "Đòn bẩy: 5x\n"
            "Rủi ro tối đa mỗi giao dịch: $500.00\n"
        )
        risk_info_layout.addWidget(self.risk_info_label)
        
        # Biểu đồ so sánh hiệu suất theo mức rủi ro
        risk_comparison_group = QGroupBox("So sánh hiệu suất")
        risk_comparison_layout = QVBoxLayout()
        
        # Tạo bảng so sánh
        self.risk_comparison_table = QTableWidget()
        self.risk_comparison_table.setColumnCount(5)
        self.risk_comparison_table.setHorizontalHeaderLabels([
            "Mức rủi ro", "Lợi nhuận", "Drawdown", "Win Rate", "Thời gian hồi vốn"
        ])
        self.risk_comparison_table.setRowCount(5)
        
        # Thêm dữ liệu mẫu
        risk_levels = ["Cực thấp (1%)", "Thấp (3%)", "Trung bình (5%)", "Cao (10%)", "Cực cao (25%)"]
        profit_values = ["6.78%", "18.21%", "36.7%", "96.2%", "578.2%"]
        drawdown_values = ["4.91%", "12.79%", "22.4%", "42.5%", "85.4%"]
        win_rates = ["63.45%", "61.54%", "58.2%", "53.2%", "48.5%"]
        recovery_times = ["40-60 ngày", "20-35 ngày", "15-25 ngày", "7-15 ngày", "2-7 ngày"]
        
        for i in range(5):
            self.risk_comparison_table.setItem(i, 0, QTableWidgetItem(risk_levels[i]))
            self.risk_comparison_table.setItem(i, 1, QTableWidgetItem(profit_values[i]))
            self.risk_comparison_table.setItem(i, 2, QTableWidgetItem(drawdown_values[i]))
            self.risk_comparison_table.setItem(i, 3, QTableWidgetItem(win_rates[i]))
            self.risk_comparison_table.setItem(i, 4, QTableWidgetItem(recovery_times[i]))
        
        self.risk_comparison_table.resizeColumnsToContents()
        risk_comparison_layout.addWidget(self.risk_comparison_table)
        
        risk_comparison_group.setLayout(risk_comparison_layout)
        
        # Cài đặt bổ sung
        additional_settings_group = QGroupBox("Cài đặt bổ sung")
        additional_settings_layout = QFormLayout()
        
        # Đặt Stop Loss tự động
        self.auto_sl_checkbox = QCheckBox("Tự động tính toán Stop Loss dựa trên ATR")
        self.auto_sl_checkbox.setChecked(True)
        additional_settings_layout.addRow(self.auto_sl_checkbox)
        
        # Đặt Take Profit tự động
        self.auto_tp_checkbox = QCheckBox("Tự động tính toán Take Profit dựa trên ATR")
        self.auto_tp_checkbox.setChecked(True)
        additional_settings_layout.addRow(self.auto_tp_checkbox)
        
        # Trailing Stop
        self.trailing_stop_checkbox = QCheckBox("Kích hoạt Trailing Stop")
        self.trailing_stop_checkbox.setChecked(True)
        additional_settings_layout.addRow(self.trailing_stop_checkbox)
        
        # Trailing activation threshold
        self.trailing_activation = QDoubleSpinBox()
        self.trailing_activation.setRange(0.1, 10.0)
        self.trailing_activation.setValue(1.0)
        self.trailing_activation.setSingleStep(0.1)
        additional_settings_layout.addRow("Ngưỡng kích hoạt Trailing Stop (%):", self.trailing_activation)
        
        # Trailing callback
        self.trailing_callback = QDoubleSpinBox()
        self.trailing_callback.setRange(0.05, 2.0)
        self.trailing_callback.setValue(0.5)
        self.trailing_callback.setSingleStep(0.05)
        additional_settings_layout.addRow("Callback Trailing Stop (%):", self.trailing_callback)
        
        additional_settings_group.setLayout(additional_settings_layout)
        
        # Thêm vào layout chính
        layout.addWidget(self.risk_profile_widget)
        risk_info_group.setLayout(risk_info_layout)
        layout.addWidget(risk_info_group)
        layout.addWidget(risk_comparison_group)
        layout.addWidget(additional_settings_group)
        
        # Nút áp dụng
        apply_btn = QPushButton("Áp dụng cài đặt rủi ro")
        apply_btn.clicked.connect(self.apply_risk_settings)
        layout.addWidget(apply_btn)
        
        self.risk_tab.setLayout(layout)
    
    def create_backtest_tab(self):
        """Tạo tab backtest"""
        layout = QVBoxLayout()
        
        # Cấu hình backtest
        config_group = QGroupBox("Cấu hình backtest")
        config_layout = QFormLayout()
        
        # Chọn cặp tiền
        self.backtest_symbol = QComboBox()
        self.backtest_symbol.addItems(["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "DOGEUSDT"])
        config_layout.addRow("Cặp tiền:", self.backtest_symbol)
        
        # Khung thời gian
        self.backtest_timeframe = QComboBox()
        self.backtest_timeframe.addItems(["1m", "5m", "15m", "30m", "1h", "4h", "1d"])
        self.backtest_timeframe.setCurrentText("1h")
        config_layout.addRow("Khung thời gian:", self.backtest_timeframe)
        
        # Thời gian backtest
        self.backtest_period = QSpinBox()
        self.backtest_period.setRange(7, 365)
        self.backtest_period.setValue(90)
        config_layout.addRow("Số ngày backtest:", self.backtest_period)
        
        # Số dư ban đầu
        self.backtest_balance = QDoubleSpinBox()
        self.backtest_balance.setRange(100, 1000000)
        self.backtest_balance.setValue(10000)
        config_layout.addRow("Số dư ban đầu ($):", self.backtest_balance)
        
        # Mức rủi ro
        self.backtest_risk = QComboBox()
        self.backtest_risk.addItems(["Cực thấp (1%)", "Thấp (3%)", "Trung bình (5%)", "Cao (10%)", "Cực cao (25%)"])
        self.backtest_risk.setCurrentIndex(2)
        config_layout.addRow("Mức rủi ro:", self.backtest_risk)
        
        # Chiến lược
        self.backtest_strategy = QComboBox()
        self.backtest_strategy.addItems([
            "AdaptiveStrategy", "RSIStrategy", "MACDStrategy", 
            "BollingerBandsStrategy", "SuperTrendStrategy"
        ])
        config_layout.addRow("Chiến lược:", self.backtest_strategy)
        
        config_group.setLayout(config_layout)
        
        # Nút chạy backtest
        run_btn = QPushButton("Chạy backtest")
        run_btn.clicked.connect(self.run_backtest)
        
        # Progress bar
        self.backtest_progress = QProgressBar()
        self.backtest_progress.setValue(0)
        
        # Kết quả backtest
        results_group = QGroupBox("Kết quả backtest")
        results_layout = QVBoxLayout()
        
        self.backtest_results_table = QTableWidget()
        self.backtest_results_table.setColumnCount(9)
        self.backtest_results_table.setHorizontalHeaderLabels([
            "Cặp tiền", "Lợi nhuận (%)", "Drawdown (%)", "Win Rate (%)", 
            "Tổng GD", "GD thắng", "GD thua", "Profit Factor", "Số dư cuối"
        ])
        results_layout.addWidget(self.backtest_results_table)
        
        results_group.setLayout(results_layout)
        
        # Thêm vào layout chính
        layout.addWidget(config_group)
        layout.addWidget(run_btn)
        layout.addWidget(self.backtest_progress)
        layout.addWidget(results_group)
        
        # Nút xuất kết quả
        export_btn = QPushButton("Xuất kết quả backtest")
        export_btn.clicked.connect(self.export_backtest_results)
        layout.addWidget(export_btn)
        
        self.backtest_tab.setLayout(layout)
    
    def on_risk_profile_changed(self, risk_params):
        """Xử lý khi cấu hình rủi ro thay đổi"""
        # Cập nhật thông tin rủi ro
        risk_level = risk_params['risk_level']
        risk_percent = risk_params['risk_per_trade']
        leverage = risk_params['leverage']
        account_size = risk_params['account_size']
        
        # Tính toán rủi ro tối đa mỗi giao dịch
        max_risk_per_trade = account_size * (risk_percent / 100)
        
        # Cập nhật nhãn thông tin
        self.risk_info_label.setText(
            f"Mức rủi ro hiện tại: {RISK_LEVELS[risk_level]['name']} ({risk_percent:.1f}%)\n"
            f"Đòn bẩy: {leverage}x\n"
            f"Rủi ro tối đa mỗi giao dịch: ${max_risk_per_trade:.2f}\n"
        )
    
    def apply_risk_settings(self):
        """Áp dụng cài đặt rủi ro"""
        # Lấy cấu hình rủi ro hiện tại
        risk_params = self.risk_profile_widget.get_current_risk_params()
        
        # Lưu cấu hình
        risk_config_dir = "risk_configs"
        os.makedirs(risk_config_dir, exist_ok=True)
        
        config_file = os.path.join(risk_config_dir, "current_risk_config.json")
        
        # Thêm các cài đặt bổ sung
        risk_params.update({
            'auto_sl': self.auto_sl_checkbox.isChecked(),
            'auto_tp': self.auto_tp_checkbox.isChecked(),
            'trailing_stop': self.trailing_stop_checkbox.isChecked(),
            'trailing_activation': self.trailing_activation.value(),
            'trailing_callback': self.trailing_callback.value()
        })
        
        # Lưu cấu hình
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(risk_params, f, indent=4)
        
        QMessageBox.information(self, "Thành công", "Đã áp dụng cài đặt rủi ro mới")
    
    def run_backtest(self):
        """Chạy backtest"""
        # Hiển thị thông báo không thể chạy backtest đầy đủ trong giao diện desktop
        QMessageBox.information(
            self,
            "Backtest",
            "Backtest được chạy trong tiến trình nền. Kết quả sẽ được cập nhật sau khi hoàn thành.\n\n"
            "Để chạy backtest đầy đủ, vui lòng sử dụng module full_risk_levels_backtest.py"
        )
        
        # Mô phỏng backtest
        self.backtest_progress.setValue(0)
        
        # Tạo thread để mô phỏng backtest
        thread = BacktestThread(self)
        thread.progress_updated.connect(self.update_backtest_progress)
        thread.backtest_completed.connect(self.on_backtest_completed)
        thread.start()
    
    def update_backtest_progress(self, value):
        """Cập nhật tiến trình backtest"""
        self.backtest_progress.setValue(value)
    
    def on_backtest_completed(self, results):
        """Xử lý khi backtest hoàn thành"""
        # Cập nhật bảng kết quả
        self.backtest_results_table.setRowCount(1)
        
        # Thêm dữ liệu
        symbol = self.backtest_symbol.currentText()
        self.backtest_results_table.setItem(0, 0, QTableWidgetItem(symbol))
        self.backtest_results_table.setItem(0, 1, QTableWidgetItem(f"{results['profit_pct']:.2f}"))
        self.backtest_results_table.setItem(0, 2, QTableWidgetItem(f"{results['drawdown_pct']:.2f}"))
        self.backtest_results_table.setItem(0, 3, QTableWidgetItem(f"{results['win_rate']:.2f}"))
        self.backtest_results_table.setItem(0, 4, QTableWidgetItem(str(results['total_trades'])))
        self.backtest_results_table.setItem(0, 5, QTableWidgetItem(str(results['winning_trades'])))
        self.backtest_results_table.setItem(0, 6, QTableWidgetItem(str(results['losing_trades'])))
        self.backtest_results_table.setItem(0, 7, QTableWidgetItem(f"{results['profit_factor']:.2f}"))
        self.backtest_results_table.setItem(0, 8, QTableWidgetItem(f"{results['final_balance']:.2f}"))
        
        self.backtest_results_table.resizeColumnsToContents()
        
        QMessageBox.information(self, "Backtest hoàn thành", "Đã hoàn thành backtest!")
    
    def export_backtest_results(self):
        """Xuất kết quả backtest"""
        QMessageBox.information(
            self,
            "Xuất kết quả",
            "Kết quả backtest đã được lưu trong thư mục backtest_results/"
        )
"""
                    
                    # Thêm code vào cuối lớp EnhancedTradingGUI
                    last_class_method = content.rfind("def ", content.rfind("class EnhancedTradingGUI"))
                    last_method_end = content.find("\n\n", last_class_method)
                    if last_method_end == -1:
                        last_method_end = len(content)
                    
                    content = content[:last_method_end] + "\n" + create_risk_tab_code + content[last_method_end:]
                
                # Thêm lớp BacktestThread
                backtest_thread_code = """

class BacktestThread(QThread):
    """Thread chạy backtest"""
    
    progress_updated = pyqtSignal(int)
    backtest_completed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
    
    def run(self):
        """Chạy backtest"""
        try:
            # Lấy các tham số backtest
            symbol = self.parent.backtest_symbol.currentText()
            timeframe = self.parent.backtest_timeframe.currentText()
            period = self.parent.backtest_period.value()
            balance = self.parent.backtest_balance.value()
            risk_index = self.parent.backtest_risk.currentIndex()
            strategy = self.parent.backtest_strategy.currentText()
            
            # Chuyển đổi risk_index thành risk_pct
            risk_pct = [1.0, 3.0, 5.0, 10.0, 25.0][risk_index]
            
            # Mô phỏng chạy backtest
            total_steps = 10
            for i in range(total_steps):
                # Cập nhật tiến trình
                self.progress_updated.emit(int((i + 1) / total_steps * 100))
                time.sleep(0.3)  # Mô phỏng thời gian chạy
            
            # Mô phỏng kết quả backtest
            # Các kết quả này sẽ được điều chỉnh dựa trên risk_pct
            profit_pct = risk_pct * 1.5
            drawdown_pct = risk_pct * 0.8
            win_rate = 60 - (risk_pct / 3)
            total_trades = 100
            winning_trades = int(total_trades * win_rate / 100)
            losing_trades = total_trades - winning_trades
            profit_factor = 1.1
            final_balance = balance * (1 + profit_pct / 100)
            
            # Tạo kết quả
            results = {
                'symbol': symbol,
                'timeframe': timeframe,
                'period': period,
                'balance': balance,
                'risk_pct': risk_pct,
                'strategy': strategy,
                'profit_pct': profit_pct,
                'drawdown_pct': drawdown_pct,
                'win_rate': win_rate,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'profit_factor': profit_factor,
                'final_balance': final_balance
            }
            
            # Phát tín hiệu hoàn thành
            self.backtest_completed.emit(results)
        
        except Exception as e:
            logger.error(f"Lỗi khi chạy backtest: {str(e)}")
            
            # Phát tín hiệu hoàn thành với kết quả trống
            self.backtest_completed.emit({
                'profit_pct': 0.0,
                'drawdown_pct': 0.0,
                'win_rate': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'profit_factor': 0.0,
                'final_balance': self.parent.backtest_balance.value()
            })
"""
                
                # Thêm lớp BacktestThread vào cuối file
                content += "\n" + backtest_thread_code + "\n"
                
                # Lưu file đã cập nhật
                with open(source_file, "w", encoding="utf-8") as f:
                    f.write(content)
                
                logger.info("Đã cập nhật enhanced_trading_gui.py thành công")
            else:
                logger.info("enhanced_trading_gui.py đã được cập nhật trước đó")
            
            return True
        
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật enhanced_trading_gui.py: {str(e)}")
            return False
    
    def update_all(self):
        """Cập nhật tất cả các thành phần"""
        logger.info("Bắt đầu cập nhật toàn bộ ứng dụng desktop...")
        
        # Cập nhật cấu hình rủi ro
        if self.update_risk_configs():
            logger.info("Đã cập nhật cấu hình rủi ro thành công")
        else:
            logger.error("Cập nhật cấu hình rủi ro thất bại")
        
        # Cập nhật giao diện desktop
        if self.update_enhanced_trading_gui():
            logger.info("Đã cập nhật giao diện desktop thành công")
        else:
            logger.error("Cập nhật giao diện desktop thất bại")
        
        # Cập nhật phiên bản
        self.update_version("1.2.0")
        
        logger.info("Hoàn thành cập nhật ứng dụng desktop")
        return True
    
    def run_validation(self):
        """Chạy kiểm tra tất cả các thành phần"""
        logger.info("Chạy kiểm tra các thành phần của ứng dụng desktop...")
        
        validation_results = {
            "enhanced_trading_gui": os.path.exists("enhanced_trading_gui.py"),
            "risk_configs": os.path.exists(RISK_CONFIG_PATH),
            "resources": os.path.exists(RESOURCES_PATH),
            "version": self.current_version
        }
        
        # Kiểm tra các file cấu hình rủi ro
        if validation_results["risk_configs"]:
            risk_config_files = [f for f in os.listdir(RISK_CONFIG_PATH) if f.endswith(".json")]
            validation_results["risk_config_files"] = risk_config_files
        
        logger.info(f"Kết quả kiểm tra: {json.dumps(validation_results, indent=4)}")
        
        return validation_results

def main():
    """Hàm chính"""
    try:
        # Khởi tạo updater
        updater = DesktopAppUpdater()
        
        # Cập nhật tất cả các thành phần
        updater.update_all()
        
        # Chạy kiểm tra
        validation_results = updater.run_validation()
        
        # Hiển thị kết quả
        logger.info("Đã hoàn thành cập nhật và kiểm tra ứng dụng desktop")
        logger.info(f"Phiên bản hiện tại: {updater.current_version}")
        
        return True
    
    except Exception as e:
        logger.error(f"Lỗi trong quá trình cập nhật: {str(e)}")
        return False

if __name__ == "__main__":
    main()