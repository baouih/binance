#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Risk Profile Selector - GUI
---------------------------
Giao diện đồ họa cho phép người dùng lựa chọn và tùy chỉnh mức độ rủi ro
dựa trên kích thước tài khoản và khẩu vị rủi ro của họ.
"""

import os
import sys
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QComboBox, QSlider, QPushButton, 
                            QSpinBox, QDoubleSpinBox, QTabWidget, QGridLayout, 
                            QGroupBox, QFormLayout, QCheckBox, QProgressBar, 
                            QTextEdit, QSplitter, QFrame, QTableWidget, QTableWidgetItem,
                            QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('risk_profile_selector')

# Định nghĩa các mức độ rủi ro
RISK_LEVELS = {
    'extremely_low': {
        'name': 'Cực kỳ thấp',
        'risk_range': (0.5, 1.0),
        'default': 1.0,
        'leverage_range': (1, 2),
        'default_leverage': 2,
        'description': 'Bảo toàn vốn là ưu tiên hàng đầu. Lợi nhuận thấp, ổn định.'
    },
    'low': {
        'name': 'Thấp',
        'risk_range': (1.5, 3.0),
        'default': 2.5,
        'leverage_range': (2, 5),
        'default_leverage': 3,
        'description': 'Cân bằng giữa bảo toàn vốn và tăng trưởng. An toàn cho người mới.'
    },
    'medium': {
        'name': 'Trung bình',
        'risk_range': (3.0, 7.0),
        'default': 5.0,
        'leverage_range': (3, 10),
        'default_leverage': 5,
        'description': 'Tăng trưởng ở mức vừa phải với drawdown có thể chấp nhận được.'
    },
    'high': {
        'name': 'Cao',
        'risk_range': (7.0, 15.0),
        'default': 10.0,
        'leverage_range': (5, 20),
        'default_leverage': 10,
        'description': 'Tăng trưởng nhanh với rủi ro đáng kể. Cho trader có kinh nghiệm.'
    },
    'extremely_high': {
        'name': 'Cực kỳ cao',
        'risk_range': (15.0, 50.0),
        'default': 25.0,
        'leverage_range': (10, 50),
        'default_leverage': 20,
        'description': 'Tăng trưởng cực nhanh với rủi ro rất lớn. Chỉ dành cho chuyên gia.'
    }
}

# Bảng điều chỉnh thích ứng theo kích thước tài khoản
ACCOUNT_SIZE_ADJUSTMENTS = {
    100: {'recommendation': 'extremely_high', 'leverage_boost': 1.5, 'profit_target_boost': 1.5},
    200: {'recommendation': 'extremely_high', 'leverage_boost': 1.3, 'profit_target_boost': 1.4},
    300: {'recommendation': 'high', 'leverage_boost': 1.2, 'profit_target_boost': 1.3},
    500: {'recommendation': 'high', 'leverage_boost': 1.1, 'profit_target_boost': 1.2},
    1000: {'recommendation': 'medium', 'leverage_boost': 1.0, 'profit_target_boost': 1.1},
    3000: {'recommendation': 'medium', 'leverage_boost': 0.9, 'profit_target_boost': 1.0},
    5000: {'recommendation': 'low', 'leverage_boost': 0.8, 'profit_target_boost': 0.9},
    10000: {'recommendation': 'low', 'leverage_boost': 0.7, 'profit_target_boost': 0.8},
    50000: {'recommendation': 'extremely_low', 'leverage_boost': 0.5, 'profit_target_boost': 0.7}
}

# Class để vẽ biểu đồ
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)
        self.fig.tight_layout()

# Luồng chạy backtest để tránh giao diện đứng
class BacktestThread(QThread):
    update_progress = pyqtSignal(int)
    backtest_complete = pyqtSignal(dict)
    
    def __init__(self, risk_params=None, symbols=None, timeframe='1h', days=90):
        QThread.__init__(self)
        self.risk_params = risk_params
        self.symbols = symbols or ['BTCUSDT', 'ETHUSDT']
        self.timeframe = timeframe
        self.days = days
        
    def run(self):
        try:
            # Mô phỏng chạy backtest
            results = {}
            for i, symbol in enumerate(self.symbols):
                # Mô phỏng thời gian chạy và cập nhật tiến trình
                progress = int((i + 0.5) / len(self.symbols) * 100)
                self.update_progress.emit(progress)
                
                # Mô phỏng kết quả backtest (trong thực tế sẽ gọi hàm backtest thực)
                # Ở đây chúng ta chỉ mô phỏng kết quả dựa trên mức rủi ro
                risk_pct = self.risk_params.get('risk_per_trade', 5.0)
                leverage = self.risk_params.get('max_leverage', 5)
                
                # Mô phỏng các chỉ số dựa trên mức rủi ro và đòn bẩy
                profit_factor = 1.0 + (risk_pct / 100)
                win_rate = 60 - (risk_pct / 2)  # Win rate giảm khi risk tăng
                avg_profit = risk_pct * 1.5  # Lợi nhuận tăng khi risk tăng
                max_drawdown = risk_pct * 3  # Drawdown tăng khi risk tăng
                
                # Mô phỏng kết quả dựa trên mức risk
                results[symbol] = {
                    'symbol': symbol,
                    'risk_level': self.risk_params.get('risk_level', 'medium'),
                    'risk_percentage': risk_pct,
                    'leverage': leverage,
                    'initial_balance': 10000,
                    'final_balance': 10000 * (1 + avg_profit/100),
                    'profit_loss': 10000 * (avg_profit/100),
                    'profit_loss_pct': avg_profit,
                    'max_drawdown': max_drawdown,
                    'win_rate': win_rate,
                    'profit_factor': profit_factor,
                    'total_trades': 100,
                    'winning_trades': int(win_rate),
                    'losing_trades': 100 - int(win_rate)
                }
                
                self.update_progress.emit(int((i + 1) / len(self.symbols) * 100))
                
            # Kết thúc backtest và trả về kết quả
            self.backtest_complete.emit(results)
        except Exception as e:
            logger.error(f"Lỗi trong quá trình backtest: {e}")
            self.backtest_complete.emit({})

class RiskProfileSelector(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Công cụ điều chỉnh mức độ rủi ro")
        self.setGeometry(100, 100, 1200, 800)
        
        # Khởi tạo các biến
        self.selected_risk_level = 'medium'
        self.account_size = 10000
        self.current_risk_params = self._get_default_risk_params('medium')
        self.backtest_results = {}
        
        # Set up UI
        self.setup_ui()
        
    def setup_ui(self):
        # Widget chính
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Tạo tabs
        tab_widget = QTabWidget()
        tab_config = QWidget()
        tab_backtest = QWidget()
        tab_result = QWidget()
        
        tab_widget.addTab(tab_config, "Cấu hình rủi ro")
        tab_widget.addTab(tab_backtest, "Backtest")
        tab_widget.addTab(tab_result, "Kết quả & So sánh")
        
        # === Tab cấu hình ===
        config_layout = QVBoxLayout()
        
        # Panel kích thước tài khoản
        account_group = QGroupBox("Kích thước tài khoản")
        account_layout = QFormLayout()
        
        self.account_size_input = QSpinBox()
        self.account_size_input.setRange(100, 1000000)
        self.account_size_input.setSingleStep(100)
        self.account_size_input.setValue(self.account_size)
        self.account_size_input.valueChanged.connect(self.on_account_size_changed)
        
        account_layout.addRow("Số dư tài khoản ($):", self.account_size_input)
        
        self.recommendation_label = QLabel("Đề xuất mức rủi ro: Trung bình")
        account_layout.addRow("", self.recommendation_label)
        
        account_group.setLayout(account_layout)
        
        # Panel mức độ rủi ro
        risk_group = QGroupBox("Lựa chọn mức độ rủi ro")
        risk_layout = QVBoxLayout()
        
        risk_selection_layout = QHBoxLayout()
        self.risk_level_combo = QComboBox()
        for risk_id, risk_data in RISK_LEVELS.items():
            self.risk_level_combo.addItem(risk_data['name'], risk_id)
        
        self.risk_level_combo.currentIndexChanged.connect(self.on_risk_level_changed)
        risk_selection_layout.addWidget(QLabel("Mức độ rủi ro:"))
        risk_selection_layout.addWidget(self.risk_level_combo)
        
        risk_layout.addLayout(risk_selection_layout)
        
        self.risk_description = QLabel(RISK_LEVELS['medium']['description'])
        risk_layout.addWidget(self.risk_description)
        
        # Panel tùy chỉnh rủi ro chi tiết
        params_layout = QGridLayout()
        
        # Risk per trade
        params_layout.addWidget(QLabel("Rủi ro mỗi giao dịch (%):"), 0, 0)
        self.risk_per_trade = QDoubleSpinBox()
        self.risk_per_trade.setRange(0.1, 50.0)
        self.risk_per_trade.setSingleStep(0.5)
        self.risk_per_trade.setValue(RISK_LEVELS['medium']['default'])
        params_layout.addWidget(self.risk_per_trade, 0, 1)
        
        # Leverage
        params_layout.addWidget(QLabel("Đòn bẩy (x):"), 1, 0)
        self.leverage = QSpinBox()
        self.leverage.setRange(1, 100)
        self.leverage.setSingleStep(1)
        self.leverage.setValue(RISK_LEVELS['medium']['default_leverage'])
        params_layout.addWidget(self.leverage, 1, 1)
        
        # Stop loss ATR multiplier
        params_layout.addWidget(QLabel("Hệ số ATR cho Stop Loss:"), 2, 0)
        self.sl_atr = QDoubleSpinBox()
        self.sl_atr.setRange(0.5, 3.0)
        self.sl_atr.setSingleStep(0.1)
        self.sl_atr.setValue(1.5)
        params_layout.addWidget(self.sl_atr, 2, 1)
        
        # Take profit ATR multiplier
        params_layout.addWidget(QLabel("Hệ số ATR cho Take Profit:"), 3, 0)
        self.tp_atr = QDoubleSpinBox()
        self.tp_atr.setRange(0.5, 8.0)
        self.tp_atr.setSingleStep(0.1)
        self.tp_atr.setValue(3.0)
        params_layout.addWidget(self.tp_atr, 3, 1)
        
        # Trailing stop activation
        params_layout.addWidget(QLabel("Kích hoạt Trailing Stop (%):"), 4, 0)
        self.trailing_activation = QDoubleSpinBox()
        self.trailing_activation.setRange(0.1, 5.0)
        self.trailing_activation.setSingleStep(0.1)
        self.trailing_activation.setValue(1.0)
        params_layout.addWidget(self.trailing_activation, 4, 1)
        
        # Trailing stop callback
        params_layout.addWidget(QLabel("Callback Trailing Stop (%):"), 5, 0)
        self.trailing_callback = QDoubleSpinBox()
        self.trailing_callback.setRange(0.05, 2.0)
        self.trailing_callback.setSingleStep(0.05)
        self.trailing_callback.setValue(0.5)
        params_layout.addWidget(self.trailing_callback, 5, 1)
        
        risk_layout.addLayout(params_layout)
        
        # Partial profit taking
        partial_group = QGroupBox("Chốt lời từng phần")
        partial_layout = QVBoxLayout()
        
        self.enable_partial = QCheckBox("Kích hoạt chốt lời từng phần")
        self.enable_partial.setChecked(True)
        partial_layout.addWidget(self.enable_partial)
        
        partial_params = QGridLayout()
        partial_params.addWidget(QLabel("25% đầu tiên tại:"), 0, 0)
        self.partial1 = QDoubleSpinBox()
        self.partial1.setRange(0.1, 10.0)
        self.partial1.setSingleStep(0.1)
        self.partial1.setValue(1.0)
        partial_params.addWidget(self.partial1, 0, 1)
        
        partial_params.addWidget(QLabel("25% tiếp theo tại:"), 1, 0)
        self.partial2 = QDoubleSpinBox()
        self.partial2.setRange(0.1, 15.0)
        self.partial2.setSingleStep(0.1)
        self.partial2.setValue(2.0)
        partial_params.addWidget(self.partial2, 1, 1)
        
        partial_params.addWidget(QLabel("25% tiếp theo tại:"), 2, 0)
        self.partial3 = QDoubleSpinBox()
        self.partial3.setRange(0.1, 20.0)
        self.partial3.setSingleStep(0.1)
        self.partial3.setValue(3.0)
        partial_params.addWidget(self.partial3, 2, 1)
        
        partial_params.addWidget(QLabel("25% còn lại tại:"), 3, 0)
        self.partial4 = QDoubleSpinBox()
        self.partial4.setRange(0.1, 30.0)
        self.partial4.setSingleStep(0.1)
        self.partial4.setValue(5.0)
        partial_params.addWidget(self.partial4, 3, 1)
        
        partial_layout.addLayout(partial_params)
        partial_group.setLayout(partial_layout)
        
        # Thêm vào layout
        risk_layout.addWidget(partial_group)
        risk_group.setLayout(risk_layout)
        
        # Khu vực biểu đồ mô phỏng rủi ro-lợi nhuận
        chart_group = QGroupBox("Mô phỏng rủi ro-lợi nhuận")
        chart_layout = QVBoxLayout()
        
        self.chart_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        chart_layout.addWidget(self.chart_canvas)
        
        chart_group.setLayout(chart_layout)
        
        # Layout chính cho tab cấu hình
        config_layout.addWidget(account_group)
        config_layout.addWidget(risk_group)
        config_layout.addWidget(chart_group)
        
        # Nút lưu cấu hình
        save_btn = QPushButton("Lưu cấu hình rủi ro")
        save_btn.clicked.connect(self.save_risk_config)
        config_layout.addWidget(save_btn)
        
        tab_config.setLayout(config_layout)
        
        # === Tab backtest ===
        backtest_layout = QVBoxLayout()
        
        # Panel cấu hình backtest
        backtest_config_group = QGroupBox("Cấu hình backtest")
        backtest_config_layout = QFormLayout()
        
        # Chọn cặp tiền
        self.symbols_input = QTextEdit()
        self.symbols_input.setPlainText("BTCUSDT\nETHUSDT\nSOLUSDT")
        self.symbols_input.setMaximumHeight(80)
        backtest_config_layout.addRow("Cặp tiền (mỗi dòng một cặp):", self.symbols_input)
        
        # Chọn timeframe
        self.timeframe_combo = QComboBox()
        timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
        for tf in timeframes:
            self.timeframe_combo.addItem(tf)
        self.timeframe_combo.setCurrentText("1h")
        backtest_config_layout.addRow("Khung thời gian:", self.timeframe_combo)
        
        # Số ngày backtest
        self.backtest_days = QSpinBox()
        self.backtest_days.setRange(7, 365)
        self.backtest_days.setValue(90)
        backtest_config_layout.addRow("Số ngày backtest:", self.backtest_days)
        
        # Chọn chiến lược
        self.strategy_combo = QComboBox()
        strategies = ["AdaptiveStrategy", "RSIStrategy", "MACDStrategy", "BollingerBandsStrategy", "SuperTrendStrategy"]
        for strategy in strategies:
            self.strategy_combo.addItem(strategy)
        backtest_config_layout.addRow("Chiến lược:", self.strategy_combo)
        
        backtest_config_group.setLayout(backtest_config_layout)
        
        # Panel thực hiện backtest
        backtest_run_group = QGroupBox("Thực hiện backtest")
        backtest_run_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        backtest_run_layout.addWidget(self.progress_bar)
        
        run_btn = QPushButton("Chạy backtest")
        run_btn.clicked.connect(self.run_backtest)
        backtest_run_layout.addWidget(run_btn)
        
        self.backtest_status = QLabel("Sẵn sàng chạy backtest")
        backtest_run_layout.addWidget(self.backtest_status)
        
        backtest_run_group.setLayout(backtest_run_layout)
        
        # Thêm vào layout chính
        backtest_layout.addWidget(backtest_config_group)
        backtest_layout.addWidget(backtest_run_group)
        
        tab_backtest.setLayout(backtest_layout)
        
        # === Tab kết quả ===
        result_layout = QVBoxLayout()
        
        # Bảng kết quả
        result_table_group = QGroupBox("Kết quả backtest")
        result_table_layout = QVBoxLayout()
        
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(9)
        self.result_table.setHorizontalHeaderLabels([
            "Cặp tiền", "Lợi nhuận (%)", "Drawdown (%)", "Win Rate (%)", 
            "Tổng GD", "GD thắng", "GD thua", "Profit Factor", "Số dư cuối"
        ])
        
        result_table_layout.addWidget(self.result_table)
        result_table_group.setLayout(result_table_layout)
        
        # Biểu đồ kết quả
        result_chart_group = QGroupBox("Biểu đồ hiệu suất")
        result_chart_layout = QVBoxLayout()
        
        self.result_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        result_chart_layout.addWidget(self.result_canvas)
        
        result_chart_group.setLayout(result_chart_layout)
        
        # So sánh với mức rủi ro khác
        compare_group = QGroupBox("So sánh với các mức rủi ro khác")
        compare_layout = QVBoxLayout()
        
        self.compare_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        compare_layout.addWidget(self.compare_canvas)
        
        compare_group.setLayout(compare_layout)
        
        # Nút xuất kết quả
        export_btn = QPushButton("Xuất kết quả backtest")
        export_btn.clicked.connect(self.export_results)
        
        # Thêm vào layout chính
        result_layout.addWidget(result_table_group)
        result_layout.addWidget(result_chart_group)
        result_layout.addWidget(compare_group)
        result_layout.addWidget(export_btn)
        
        tab_result.setLayout(result_layout)
        
        # Thêm tabs vào layout chính
        main_layout.addWidget(tab_widget)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Cập nhật biểu đồ ban đầu
        self.update_risk_chart()
        self.on_account_size_changed()
        
    def _get_default_risk_params(self, risk_level):
        """Lấy tham số mặc định cho mức rủi ro đã chọn"""
        risk_data = RISK_LEVELS[risk_level]
        
        return {
            'risk_level': risk_level,
            'risk_per_trade': risk_data['default'],
            'max_leverage': risk_data['default_leverage'],
            'stop_loss_atr_multiplier': 1.5 if risk_level in ['low', 'extremely_low'] else (
                1.2 if risk_level == 'medium' else (
                    1.0 if risk_level == 'high' else 0.7
                )
            ),
            'take_profit_atr_multiplier': 4.0 if risk_level in ['low', 'extremely_low'] else (
                3.0 if risk_level == 'medium' else (
                    2.0 if risk_level == 'high' else 1.5
                )
            ),
            'trailing_activation_pct': 1.0 if risk_level in ['low', 'extremely_low'] else (
                0.8 if risk_level == 'medium' else (
                    0.5 if risk_level == 'high' else 0.3
                )
            ),
            'trailing_callback_pct': 0.5 if risk_level in ['low', 'extremely_low'] else (
                0.4 if risk_level == 'medium' else (
                    0.3 if risk_level == 'high' else 0.2
                )
            ),
            'partial_profit_taking': [
                {'pct': 1.0, 'portion': 0.25},
                {'pct': 2.0, 'portion': 0.25},
                {'pct': 3.0, 'portion': 0.25},
                {'pct': 5.0, 'portion': 0.25}
            ]
        }
    
    def on_risk_level_changed(self):
        """Xử lý khi người dùng thay đổi mức rủi ro"""
        # Lấy mức rủi ro đã chọn
        risk_level = self.risk_level_combo.currentData()
        self.selected_risk_level = risk_level
        
        # Cập nhật mô tả
        self.risk_description.setText(RISK_LEVELS[risk_level]['description'])
        
        # Cập nhật các tham số
        risk_data = RISK_LEVELS[risk_level]
        self.risk_per_trade.setValue(risk_data['default'])
        self.leverage.setValue(risk_data['default_leverage'])
        
        # Cập nhật các tham số khác dựa trên mức rủi ro
        risk_params = self._get_default_risk_params(risk_level)
        self.sl_atr.setValue(risk_params['stop_loss_atr_multiplier'])
        self.tp_atr.setValue(risk_params['take_profit_atr_multiplier'])
        self.trailing_activation.setValue(risk_params['trailing_activation_pct'])
        self.trailing_callback.setValue(risk_params['trailing_callback_pct'])
        
        # Cập nhật chốt lời từng phần
        partial_profits = risk_params['partial_profit_taking']
        self.partial1.setValue(partial_profits[0]['pct'])
        self.partial2.setValue(partial_profits[1]['pct'])
        self.partial3.setValue(partial_profits[2]['pct'])
        self.partial4.setValue(partial_profits[3]['pct'])
        
        # Cập nhật biểu đồ
        self.update_risk_chart()
    
    def on_account_size_changed(self):
        """Xử lý khi người dùng thay đổi kích thước tài khoản"""
        self.account_size = self.account_size_input.value()
        
        # Tìm đề xuất mức rủi ro phù hợp
        recommended_risk = 'medium'  # Mặc định
        for size, adjustment in sorted(ACCOUNT_SIZE_ADJUSTMENTS.items()):
            if self.account_size <= size:
                recommended_risk = adjustment['recommendation']
                break
        
        if self.account_size > max(ACCOUNT_SIZE_ADJUSTMENTS.keys()):
            recommended_risk = ACCOUNT_SIZE_ADJUSTMENTS[max(ACCOUNT_SIZE_ADJUSTMENTS.keys())]['recommendation']
        
        # Cập nhật nhãn đề xuất
        self.recommendation_label.setText(f"Đề xuất mức rủi ro: {RISK_LEVELS[recommended_risk]['name']}")
        
        # Cập nhật biểu đồ
        self.update_risk_chart()
    
    def update_risk_chart(self):
        """Cập nhật biểu đồ mô phỏng rủi ro-lợi nhuận"""
        ax = self.chart_canvas.axes
        ax.clear()
        
        # Lấy các tham số rủi ro hiện tại
        risk_per_trade = self.risk_per_trade.value()
        
        # Mô phỏng các giá trị dựa trên mức rủi ro
        risk_values = np.arange(1, 51, 1)
        profit_values = []
        drawdown_values = []
        
        for risk in risk_values:
            # Công thức mô phỏng lợi nhuận và drawdown
            profit = risk * 1.5  # Lợi nhuận tỷ lệ thuận với rủi ro
            drawdown = risk * 1.5 + 5  # Drawdown tăng nhanh hơn lợi nhuận
            
            profit_values.append(profit)
            drawdown_values.append(drawdown)
        
        # Vẽ biểu đồ
        ax.plot(risk_values, profit_values, 'g-', label='Lợi nhuận dự kiến (%)')
        ax.plot(risk_values, drawdown_values, 'r-', label='Drawdown dự kiến (%)')
        
        # Đánh dấu mức rủi ro hiện tại
        current_profit = risk_per_trade * 1.5
        current_drawdown = risk_per_trade * 1.5 + 5
        
        ax.scatter([risk_per_trade], [current_profit], color='g', s=100, zorder=5)
        ax.scatter([risk_per_trade], [current_drawdown], color='r', s=100, zorder=5)
        
        # Thêm đường kết nối
        ax.plot([risk_per_trade, risk_per_trade], [0, max(drawdown_values)], 'k--', alpha=0.3)
        
        # Thêm chú thích
        ax.annotate(f"{current_profit:.1f}%", (risk_per_trade, current_profit), 
                   xytext=(5, 5), textcoords='offset points')
        ax.annotate(f"{current_drawdown:.1f}%", (risk_per_trade, current_drawdown), 
                   xytext=(5, 5), textcoords='offset points')
        
        # Thiết lập biểu đồ
        ax.set_title(f'Mô phỏng rủi ro/lợi nhuận với mức rủi ro {risk_per_trade}%')
        ax.set_xlabel('Rủi ro mỗi giao dịch (%)')
        ax.set_ylabel('Giá trị (%)')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Vẽ lại biểu đồ
        self.chart_canvas.draw()
    
    def get_current_risk_params(self):
        """Lấy các tham số rủi ro hiện tại từ giao diện"""
        return {
            'risk_level': self.selected_risk_level,
            'risk_per_trade': self.risk_per_trade.value(),
            'max_leverage': self.leverage.value(),
            'stop_loss_atr_multiplier': self.sl_atr.value(),
            'take_profit_atr_multiplier': self.tp_atr.value(),
            'trailing_activation_pct': self.trailing_activation.value(),
            'trailing_callback_pct': self.trailing_callback.value(),
            'partial_profit_taking': [
                {'pct': self.partial1.value(), 'portion': 0.25},
                {'pct': self.partial2.value(), 'portion': 0.25},
                {'pct': self.partial3.value(), 'portion': 0.25},
                {'pct': self.partial4.value(), 'portion': 0.25}
            ],
            'enable_partial_profit': self.enable_partial.isChecked()
        }
    
    def save_risk_config(self):
        """Lưu cấu hình rủi ro hiện tại"""
        try:
            risk_params = self.get_current_risk_params()
            
            # Thêm thông tin kích thước tài khoản
            risk_params['account_size'] = self.account_size
            
            # Tạo tên file cấu hình
            config_dir = 'risk_configs'
            os.makedirs(config_dir, exist_ok=True)
            
            filename = f"{config_dir}/risk_config_{risk_params['risk_level']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Lưu cấu hình
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(risk_params, f, indent=4)
            
            QMessageBox.information(self, "Thành công", f"Đã lưu cấu hình rủi ro vào file {filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu cấu hình rủi ro: {str(e)}")
    
    def run_backtest(self):
        """Chạy backtest với cấu hình hiện tại"""
        try:
            # Lấy các tham số backtest
            risk_params = self.get_current_risk_params()
            symbols = [s.strip() for s in self.symbols_input.toPlainText().split('\n') if s.strip()]
            timeframe = self.timeframe_combo.currentText()
            days = self.backtest_days.value()
            
            # Cập nhật trạng thái
            self.backtest_status.setText("Đang chạy backtest...")
            self.progress_bar.setValue(0)
            
            # Khởi tạo và chạy thread
            self.backtest_thread = BacktestThread(risk_params, symbols, timeframe, days)
            self.backtest_thread.update_progress.connect(self.update_backtest_progress)
            self.backtest_thread.backtest_complete.connect(self.on_backtest_complete)
            
            self.backtest_thread.start()
            
        except Exception as e:
            self.backtest_status.setText(f"Lỗi: {str(e)}")
            QMessageBox.critical(self, "Lỗi", f"Không thể chạy backtest: {str(e)}")
    
    def update_backtest_progress(self, progress):
        """Cập nhật tiến trình backtest"""
        self.progress_bar.setValue(progress)
    
    def on_backtest_complete(self, results):
        """Xử lý khi backtest hoàn thành"""
        self.backtest_status.setText("Backtest hoàn thành")
        self.backtest_results = results
        
        # Cập nhật bảng kết quả
        self.update_result_table()
        
        # Cập nhật biểu đồ kết quả
        self.update_result_charts()
        
        # Chuyển sang tab kết quả
        self.centralWidget().findChild(QTabWidget).setCurrentIndex(2)
    
    def update_result_table(self):
        """Cập nhật bảng kết quả backtest"""
        # Xóa dữ liệu cũ
        self.result_table.setRowCount(0)
        
        if not self.backtest_results:
            return
        
        # Thêm dữ liệu mới
        for symbol, result in self.backtest_results.items():
            row_position = self.result_table.rowCount()
            self.result_table.insertRow(row_position)
            
            # Thêm dữ liệu vào từng cột
            self.result_table.setItem(row_position, 0, QTableWidgetItem(symbol))
            self.result_table.setItem(row_position, 1, QTableWidgetItem(f"{result['profit_loss_pct']:.2f}"))
            self.result_table.setItem(row_position, 2, QTableWidgetItem(f"{result['max_drawdown']:.2f}"))
            self.result_table.setItem(row_position, 3, QTableWidgetItem(f"{result['win_rate']:.2f}"))
            self.result_table.setItem(row_position, 4, QTableWidgetItem(str(result['total_trades'])))
            self.result_table.setItem(row_position, 5, QTableWidgetItem(str(result['winning_trades'])))
            self.result_table.setItem(row_position, 6, QTableWidgetItem(str(result['losing_trades'])))
            self.result_table.setItem(row_position, 7, QTableWidgetItem(f"{result['profit_factor']:.2f}"))
            self.result_table.setItem(row_position, 8, QTableWidgetItem(f"{result['final_balance']:.2f}"))
            
            # Tô màu ô lợi nhuận
            profit_item = self.result_table.item(row_position, 1)
            if result['profit_loss_pct'] > 0:
                profit_item.setBackground(QColor(200, 255, 200))  # Màu xanh nhạt
            else:
                profit_item.setBackground(QColor(255, 200, 200))  # Màu đỏ nhạt
        
        # Điều chỉnh kích thước cột
        self.result_table.resizeColumnsToContents()
    
    def update_result_charts(self):
        """Cập nhật biểu đồ kết quả backtest"""
        if not self.backtest_results:
            return
        
        # Biểu đồ lợi nhuận
        ax1 = self.result_canvas.axes
        ax1.clear()
        
        symbols = list(self.backtest_results.keys())
        profits = [result['profit_loss_pct'] for result in self.backtest_results.values()]
        drawdowns = [result['max_drawdown'] for result in self.backtest_results.values()]
        
        x = np.arange(len(symbols))
        width = 0.35
        
        ax1.bar(x - width/2, profits, width, label='Lợi nhuận (%)')
        ax1.bar(x + width/2, drawdowns, width, label='Drawdown (%)')
        
        ax1.set_title('Lợi nhuận vs Drawdown theo cặp tiền')
        ax1.set_xticks(x)
        ax1.set_xticklabels(symbols)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        for i, profit in enumerate(profits):
            ax1.annotate(f"{profit:.2f}%", (i - width/2, profit), 
                       xytext=(0, 3), textcoords='offset points', ha='center')
        
        for i, dd in enumerate(drawdowns):
            ax1.annotate(f"{dd:.2f}%", (i + width/2, dd), 
                       xytext=(0, 3), textcoords='offset points', ha='center')
        
        self.result_canvas.draw()
        
        # Biểu đồ so sánh các mức rủi ro
        ax2 = self.compare_canvas.axes
        ax2.clear()
        
        # Dữ liệu mô phỏng cho so sánh
        risk_levels = ['cực thấp', 'thấp', 'trung bình', 'cao', 'cực cao']
        risk_values = [1.0, 3.0, 5.0, 10.0, 25.0]
        profit_values = [6.78, 16.45, 36.7, 96.2, 578.2]
        drawdown_values = [4.91, 10.16, 22.4, 42.5, 85.4]
        win_rates = [63.45, 62.87, 58.2, 53.2, 48.5]
        
        # Vẽ biểu đồ
        ax2.plot(risk_values, profit_values, 'go-', label='Lợi nhuận (%)')
        ax2.plot(risk_values, drawdown_values, 'ro-', label='Drawdown (%)')
        
        # Trục phụ cho win rate
        ax2_twin = ax2.twinx()
        ax2_twin.plot(risk_values, win_rates, 'bo-', label='Win Rate (%)')
        ax2_twin.set_ylabel('Win Rate (%)', color='b')
        
        # Đánh dấu mức rủi ro hiện tại
        current_risk = self.risk_per_trade.value()
        # Tính toán giá trị tương ứng
        current_profit = np.interp(current_risk, risk_values, profit_values)
        current_dd = np.interp(current_risk, risk_values, drawdown_values)
        current_wr = np.interp(current_risk, risk_values, win_rates)
        
        ax2.scatter([current_risk], [current_profit], color='g', s=100, zorder=5)
        ax2.scatter([current_risk], [current_dd], color='r', s=100, zorder=5)
        ax2_twin.scatter([current_risk], [current_wr], color='b', s=100, zorder=5)
        
        # Thêm đường kết nối
        ax2.plot([current_risk, current_risk], [0, max(profit_values, drawdown_values)], 'k--', alpha=0.3)
        
        # Thiết lập biểu đồ
        ax2.set_title('So sánh hiệu suất theo mức rủi ro')
        ax2.set_xlabel('Rủi ro mỗi giao dịch (%)')
        ax2.set_ylabel('Giá trị (%)')
        ax2.grid(True, alpha=0.3)
        
        # Kết hợp legend từ cả hai trục
        lines1, labels1 = ax2.get_legend_handles_labels()
        lines2, labels2 = ax2_twin.get_legend_handles_labels()
        ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        self.compare_canvas.draw()
    
    def export_results(self):
        """Xuất kết quả backtest"""
        if not self.backtest_results:
            QMessageBox.warning(self, "Cảnh báo", "Không có kết quả backtest để xuất")
            return
        
        try:
            # Tạo thư mục kết quả
            output_dir = 'backtest_results'
            os.makedirs(output_dir, exist_ok=True)
            
            # Lấy tên file
            filename, _ = QFileDialog.getSaveFileName(
                self, "Xuất kết quả backtest", 
                f"{output_dir}/backtest_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "JSON Files (*.json)"
            )
            
            if not filename:
                return
            
            # Lưu kết quả
            with open(filename, 'w', encoding='utf-8') as f:
                # Thêm thông tin cấu hình
                output_data = {
                    'risk_config': self.get_current_risk_params(),
                    'account_size': self.account_size,
                    'backtest_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'results': self.backtest_results
                }
                json.dump(output_data, f, indent=4)
            
            QMessageBox.information(self, "Thành công", f"Đã xuất kết quả backtest vào file {filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể xuất kết quả backtest: {str(e)}")

def main():
    app = QApplication(sys.argv)
    
    # Kiểm tra xem chương trình có đang chạy trong môi trường đồ họa không
    if 'DISPLAY' not in os.environ and not sys.platform.startswith('win') and not sys.platform.startswith('darwin'):
        # Nếu không có display, thử sử dụng QPA platform offscreen
        app.setStyle('Fusion')  # Sử dụng style fusion
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    
    window = RiskProfileSelector()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()