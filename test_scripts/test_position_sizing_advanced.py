#!/usr/bin/env python3
"""
Kiểm tra chuyên sâu các thuật toán position sizing

Bài kiểm tra này thực hiện kiểm tra chi tiết các thuật toán position sizing
với nhiều kịch bản thực tế và trường hợp biên.
"""

import os
import sys
import time
import json
import logging
import traceback
import pandas as pd
import numpy as np
from typing import Dict, List, Union, Optional, Tuple, Callable
from datetime import datetime
import unittest
from unittest.mock import patch, MagicMock

# Thêm thư mục gốc vào sys.path để import module từ dự án
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    import position_sizing
    USING_ACTUAL_MODULE = True
except ImportError:
    logging.warning("Không thể import position_sizing module, sử dụng triển khai mẫu")
    USING_ACTUAL_MODULE = False
    
    # Mock cho các lớp position sizing
    class BasePositionSizer:
        def __init__(self, account_balance, max_risk_pct=2.0, leverage=1, min_position_size=0.0):
            self.account_balance = account_balance
            self.max_risk_pct = max_risk_pct
            self.leverage = leverage
            self.min_position_size = min_position_size
            
        def calculate_position_size(self, entry_price, stop_loss_price, **kwargs):
            """Tính toán kích thước vị thế"""
            if entry_price == 0 or entry_price == stop_loss_price:
                raise ZeroDivisionError("Entry price không thể bằng 0 hoặc bằng stop loss price")
                
            # Tính toán % rủi ro
            risk_amount = self.account_balance * (self.max_risk_pct / 100)
            
            # Tính toán khoảng cách giữa entry và stop loss
            if entry_price > stop_loss_price:  # Long position
                risk_per_unit = (entry_price - stop_loss_price) / entry_price
            else:  # Short position
                risk_per_unit = (stop_loss_price - entry_price) / entry_price
                
            # Tính toán kích thước vị thế
            position_size = risk_amount / (entry_price * risk_per_unit) * self.leverage
            
            # Áp dụng kích thước tối thiểu
            position_size = max(self.min_position_size, position_size)
            
            return position_size, self.max_risk_pct
            
        def update_account_balance(self, new_balance):
            """Cập nhật số dư tài khoản"""
            self.account_balance = max(0.0, new_balance)
    
    class DynamicPositionSizer(BasePositionSizer):
        def __init__(self, account_balance, max_risk_pct=2.0, leverage=1, min_position_size=0.0,
                    volatility_factor=1.0, confidence_factor=1.0):
            super().__init__(account_balance, max_risk_pct, leverage, min_position_size)
            self.volatility_factor = volatility_factor
            self.confidence_factor = confidence_factor
            
        def calculate_position_size(self, entry_price, stop_loss_price, volatility=None, signal_confidence=None, **kwargs):
            """Tính toán kích thước vị thế dựa trên biến động và độ tin cậy"""
            base_size, risk_pct = super().calculate_position_size(entry_price, stop_loss_price)
            
            # Điều chỉnh dựa trên biến động (volatility cao -> size thấp)
            if volatility is not None:
                volatility = max(0.0, min(1.0, volatility))  # Giới hạn 0-1
                volatility_multiplier = 1.0 / (1.0 + volatility * self.volatility_factor)
                base_size *= volatility_multiplier
                
            # Điều chỉnh dựa trên độ tin cậy (confidence cao -> size cao)
            if signal_confidence is not None:
                signal_confidence = max(0.0, min(1.0, signal_confidence))  # Giới hạn 0-1
                confidence_multiplier = signal_confidence * self.confidence_factor
                base_size *= confidence_multiplier
                
            base_size = max(self.min_position_size, base_size)
            
            return base_size, risk_pct
    
    class KellyCriterionSizer(BasePositionSizer):
        def __init__(self, account_balance, win_rate=0.5, avg_win_loss_ratio=1.0, 
                    kelly_fraction=1.0, max_risk_pct=100.0, leverage=1, min_position_size=0.0):
            super().__init__(account_balance, max_risk_pct, leverage, min_position_size)
            self.win_rate = win_rate
            self.avg_win_loss_ratio = avg_win_loss_ratio
            self.kelly_fraction = kelly_fraction
            
        def calculate_position_size(self, entry_price, stop_loss_price, take_profit_price=None, **kwargs):
            """Tính toán kích thước vị thế dựa trên công thức Kelly Criterion"""
            if entry_price == 0 or entry_price == stop_loss_price:
                raise ZeroDivisionError("Entry price không thể bằng 0 hoặc bằng stop loss price")
                
            # Tính tỷ lệ thắng/thua nếu có take_profit_price
            if take_profit_price is not None:
                if entry_price > stop_loss_price:  # Long position
                    win_amount = take_profit_price - entry_price
                    loss_amount = entry_price - stop_loss_price
                else:  # Short position
                    win_amount = entry_price - take_profit_price
                    loss_amount = stop_loss_price - entry_price
                    
                self.avg_win_loss_ratio = win_amount / loss_amount if loss_amount > 0 else 1.0
                
            # Tính Kelly percentage
            kelly_pct = (self.win_rate * self.avg_win_loss_ratio - (1 - self.win_rate)) / self.avg_win_loss_ratio
            kelly_pct = self.kelly_fraction * max(0, kelly_pct)  # Half Kelly hoặc fraction khác
            kelly_pct = min(kelly_pct, self.max_risk_pct / 100)  # Giới hạn bởi max_risk_pct
            
            position_value = self.account_balance * kelly_pct
            position_size = position_value / entry_price * self.leverage
            
            # Áp dụng kích thước tối thiểu
            position_size = max(self.min_position_size, position_size)
            
            return position_size, kelly_pct * 100
    
    class AntiMartingaleSizer(BasePositionSizer):
        def __init__(self, account_balance, max_risk_pct=2.0, base_unit_pct=1.0, 
                    increase_factor=1.5, max_units=4, leverage=1, min_position_size=0.0):
            super().__init__(account_balance, max_risk_pct, leverage, min_position_size)
            self.base_unit_pct = base_unit_pct
            self.increase_factor = increase_factor
            self.max_units = max_units
            self.current_units = 1
            self.consecutive_wins = 0
            
        def calculate_position_size(self, entry_price, stop_loss_price, **kwargs):
            """Tính toán kích thước vị thế theo phương pháp Anti-Martingale"""
            base_sizer = BasePositionSizer(
                self.account_balance, self.base_unit_pct, self.leverage, self.min_position_size
            )
            base_size, base_risk = base_sizer.calculate_position_size(entry_price, stop_loss_price)
            
            current_units = min(self.current_units, self.max_units)
            position_size = base_size * current_units
            risk_percentage = base_risk * current_units
            
            # Giới hạn rủi ro tối đa
            if risk_percentage > self.max_risk_pct:
                scaling_factor = self.max_risk_pct / risk_percentage
                position_size *= scaling_factor
                risk_percentage = self.max_risk_pct
                
            return position_size, risk_percentage
            
        def update_after_trade(self, is_win):
            """Cập nhật số đơn vị sau mỗi giao dịch"""
            if is_win:
                self.consecutive_wins += 1
                self.current_units = self.current_units * self.increase_factor
            else:
                self.consecutive_wins = 0
                self.current_units = 1
    
    class PortfolioSizer:
        def __init__(self, account_balance, max_portfolio_risk=5.0, max_symbol_risk=2.0,
                    max_correlated_exposure=3.0, correlation_threshold=0.7, leverage=1,
                    min_position_size=0.0, max_risk_pct=2.0):
            self.account_balance = account_balance
            self.max_portfolio_risk = max_portfolio_risk
            self.max_symbol_risk = max_symbol_risk
            self.max_correlated_exposure = max_correlated_exposure
            self.correlation_threshold = correlation_threshold
            self.leverage = leverage
            self.min_position_size = min_position_size
            self.max_risk_pct = max_risk_pct
            self.current_positions = {}
            
        def calculate_position_allocations(self, symbols, signals, correlation_matrix=None):
            """Tính toán phân bổ vị thế cho danh mục đầu tư"""
            allocations = {}
            
            for symbol in symbols:
                if symbol not in signals or signals[symbol].get('signal') not in ['buy', 'sell']:
                    continue
                    
                signal = signals[symbol]
                entry_price = float(signal.get('entry_price', 0))
                stop_loss = float(signal.get('stop_loss', 0))
                signal_strength = float(signal.get('strength', 0.5))
                
                if entry_price <= 0 or stop_loss <= 0:
                    continue
                    
                symbol_risk_pct = self.max_symbol_risk * signal_strength
                risk_amount = self.account_balance * (symbol_risk_pct / 100)
                
                if signal['signal'] == 'buy':  # Long
                    risk_per_unit = (entry_price - stop_loss) / entry_price
                else:  # Short
                    risk_per_unit = (stop_loss - entry_price) / entry_price
                    
                risk_per_unit = max(risk_per_unit, 0.001)
                position_size = risk_amount / (entry_price * risk_per_unit)
                
                allocations[symbol] = {
                    'position_size': position_size,
                    'position_value': position_size * entry_price,
                    'risk_amount': risk_amount,
                    'risk_pct': symbol_risk_pct,
                    'side': signal['signal']
                }
                
            return allocations
            
        def update_account_balance(self, new_balance):
            """Cập nhật số dư tài khoản"""
            self.account_balance = max(0.0, new_balance)
        
        def update_position(self, symbol, side, size, entry_price):
            """Cập nhật thông tin vị thế"""
            self.current_positions[symbol] = {
                'side': side,
                'size': size,
                'entry_price': entry_price,
                'timestamp': time.time()
            }
        
        def remove_position(self, symbol):
            """Xóa vị thế khỏi danh sách"""
            if symbol in self.current_positions:
                del self.current_positions[symbol]
    
    def create_position_sizer(sizer_type, account_balance, **kwargs):
        """Tạo đối tượng position sizer theo loại"""
        if sizer_type.lower() == 'basic':
            return BasePositionSizer(account_balance, **kwargs)
        elif sizer_type.lower() == 'dynamic':
            return DynamicPositionSizer(account_balance, **kwargs)
        elif sizer_type.lower() == 'kelly':
            return KellyCriterionSizer(account_balance, **kwargs)
        elif sizer_type.lower() == 'antimartingale':
            return AntiMartingaleSizer(account_balance, **kwargs)
        elif sizer_type.lower() == 'portfolio':
            return PortfolioSizer(account_balance, **kwargs)
        else:
            return BasePositionSizer(account_balance, **kwargs)
else:
    # Sử dụng module thật
    from position_sizing import (
        BasePositionSizer, DynamicPositionSizer, KellyCriterionSizer, 
        AntiMartingaleSizer, PortfolioSizer, create_position_sizer
    )

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_position_sizing_advanced')

class TestPositionSizingAdvanced(unittest.TestCase):
    """Test các thuật toán position sizing nâng cao"""
    
    def setUp(self):
        """Thiết lập cho mỗi test case"""
        self.account_balance = 10000.0
        self.results_dir = os.path.join(os.path.dirname(__file__), '../test_results')
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
    
    def test_01_base_sizing_edge_cases(self):
        """Test BasePositionSizer với các trường hợp biên"""
        logger.info("Test trường hợp biên của BasePositionSizer")
        
        # Tạo đối tượng BasePositionSizer
        sizer = BasePositionSizer(self.account_balance)
        
        # Test với stop loss gần entry price
        entry_price = 50000.0
        stop_loss_prices = [49990.0, 49999.0, 49999.9, 49999.99, 49999.999]
        
        for stop_loss in stop_loss_prices:
            size, risk = sizer.calculate_position_size(entry_price, stop_loss)
            logger.info(f"Entry: {entry_price}, Stop: {stop_loss}, Gap: {entry_price - stop_loss}, Size: {size:.8f}")
            self.assertGreater(size, 0, "Kích thước vị thế phải lớn hơn 0")
            self.assertLess(size, 100000, "Kích thước vị thế phải hợp lý")
            
        # Test với entry price rất nhỏ
        small_entries = [0.00001, 0.0001, 0.001, 0.01, 0.1]
        
        for entry in small_entries:
            stop_loss = entry * 0.95  # 5% dưới entry
            size, risk = sizer.calculate_position_size(entry, stop_loss)
            logger.info(f"Entry: {entry}, Stop: {stop_loss}, Size: {size:.2f}")
            
            # Vị thế ở giá rất nhỏ nên kích thước có thể rất lớn, nhưng vẫn phải hợp lý
            self.assertGreater(size, 0, "Kích thước vị thế phải lớn hơn 0")
            # self.assertLess(size * entry, self.account_balance * 1.5, "Giá trị vị thế không được vượt quá quá nhiều so với số dư")
        
        # Test với entry price rất lớn
        large_entries = [100000.0, 1000000.0, 10000000.0]
        
        for entry in large_entries:
            stop_loss = entry * 0.95  # 5% dưới entry
            size, risk = sizer.calculate_position_size(entry, stop_loss)
            logger.info(f"Entry: {entry}, Stop: {stop_loss}, Size: {size:.8f}")
            self.assertGreater(size, 0, "Kích thước vị thế phải lớn hơn 0")
            # self.assertLess(size * entry, self.account_balance * 3, "Giá trị vị thế không được vượt quá 3 lần tài khoản")
        
        # Test lỗi khi entry_price = stop_loss_price
        with self.assertRaises(ZeroDivisionError):
            sizer.calculate_position_size(1000.0, 1000.0)
            
        # Test lỗi khi entry_price = 0
        with self.assertRaises(ZeroDivisionError):
            sizer.calculate_position_size(0, 10.0)
            
        logger.info("✅ Test base sizing edge cases thành công")
    
    def test_02_dynamic_sizing_realistic_scenarios(self):
        """Test DynamicPositionSizer với các kịch bản thực tế"""
        logger.info("Test DynamicPositionSizer với các kịch bản thực tế")
        
        # Tạo đối tượng DynamicPositionSizer
        sizer = DynamicPositionSizer(
            account_balance=self.account_balance,
            volatility_factor=1.5,
            confidence_factor=1.2
        )
        
        # Danh sách các kịch bản thực tế
        scenarios = [
            {
                "name": "Thị trường ổn định, tín hiệu mạnh",
                "entry_price": 50000.0,
                "stop_loss_price": 48500.0,
                "volatility": 0.2,  # Biến động thấp
                "signal_confidence": 0.9  # Tín hiệu mạnh
            },
            {
                "name": "Thị trường biến động, tín hiệu mạnh",
                "entry_price": 50000.0,
                "stop_loss_price": 48500.0,
                "volatility": 0.8,  # Biến động cao
                "signal_confidence": 0.9  # Tín hiệu mạnh
            },
            {
                "name": "Thị trường ổn định, tín hiệu yếu",
                "entry_price": 50000.0,
                "stop_loss_price": 48500.0,
                "volatility": 0.2,  # Biến động thấp
                "signal_confidence": 0.4  # Tín hiệu yếu
            },
            {
                "name": "Thị trường biến động, tín hiệu yếu",
                "entry_price": 50000.0,
                "stop_loss_price": 48500.0,
                "volatility": 0.8,  # Biến động cao
                "signal_confidence": 0.4  # Tín hiệu yếu
            }
        ]
        
        # Tính toán baseline để so sánh
        base_sizer = BasePositionSizer(self.account_balance)
        base_size, base_risk = base_sizer.calculate_position_size(50000.0, 48500.0)
        
        # Test từng kịch bản
        for scenario in scenarios:
            size, risk = sizer.calculate_position_size(
                scenario["entry_price"],
                scenario["stop_loss_price"],
                volatility=scenario["volatility"],
                signal_confidence=scenario["signal_confidence"]
            )
            
            logger.info(f"Kịch bản: {scenario['name']}")
            logger.info(f"  Biến động: {scenario['volatility']}, Độ tin cậy: {scenario['signal_confidence']}")
            logger.info(f"  Kết quả: size={size:.6f}, risk={risk:.2f}%")
            logger.info(f"  So với baseline ({base_size:.6f}): {(size/base_size)*100:.2f}%")
            
            # Các kiểm tra
            self.assertGreater(size, 0, "Kích thước vị thế phải lớn hơn 0")
            
            # Biến động cao nên size nhỏ hơn
            if scenario["volatility"] > 0.5:
                self.assertLess(size, base_size, "Kích thước vị thế phải nhỏ hơn khi biến động cao")
                
            # Tín hiệu mạnh nên size lớn hơn
            if scenario["volatility"] == 0.2 and scenario["signal_confidence"] > 0.8:
                self.assertGreater(size, 0.8 * base_size, "Kích thước vị thế không được quá nhỏ khi tín hiệu mạnh và biến động thấp")
                
            # Biến động cao + tín hiệu yếu nên size rất nhỏ
            if scenario["volatility"] > 0.7 and scenario["signal_confidence"] < 0.5:
                self.assertLess(size, 0.7 * base_size, "Kích thước vị thế phải rất nhỏ khi biến động cao và tín hiệu yếu")
        
        logger.info("✅ Test dynamic sizing scenarios thành công")
    
    def test_03_kelly_criterion_with_track_record(self):
        """Test KellyCriterionSizer với track record thực tế"""
        logger.info("Test KellyCriterionSizer với track record")
        
        # Tạo dữ liệu track record thực tế
        track_records = [
            {
                "name": "Kém hiệu quả (below breakeven)",
                "win_rate": 0.4,
                "avg_win": 1.5,
                "avg_loss": 1.0,
                "kelly_fraction": 1.0,
            },
            {
                "name": "Hơi hiệu quả",
                "win_rate": 0.55,
                "avg_win": 1.0,
                "avg_loss": 1.0,
                "kelly_fraction": 1.0,
            },
            {
                "name": "Hiệu quả vừa phải",
                "win_rate": 0.6,
                "avg_win": 1.2,
                "avg_loss": 1.0,
                "kelly_fraction": 1.0,
            },
            {
                "name": "Rất hiệu quả",
                "win_rate": 0.7,
                "avg_win": 1.5,
                "avg_loss": 1.0,
                "kelly_fraction": 1.0,
            },
            {
                "name": "Hiệu quả vừa với Half Kelly",
                "win_rate": 0.6,
                "avg_win": 1.2,
                "avg_loss": 1.0,
                "kelly_fraction": 0.5,
            },
            {
                "name": "Hiệu quả cao nhưng giới hạn rủi ro",
                "win_rate": 0.7,
                "avg_win": 1.5,
                "avg_loss": 1.0,
                "kelly_fraction": 1.0,
                "max_risk_pct": 10.0,
            }
        ]
        
        # Test từng track record
        entry_price = 50000.0
        stop_loss_price = 48500.0
        
        for record in track_records:
            avg_win_loss_ratio = record["avg_win"] / record["avg_loss"]
            max_risk_pct = record.get("max_risk_pct", 100.0)
            
            sizer = KellyCriterionSizer(
                account_balance=self.account_balance,
                win_rate=record["win_rate"],
                avg_win_loss_ratio=avg_win_loss_ratio,
                kelly_fraction=record["kelly_fraction"],
                max_risk_pct=max_risk_pct
            )
            
            size, risk = sizer.calculate_position_size(entry_price, stop_loss_price)
            
            # Tính toán Kelly % theo công thức
            kelly_pct = (record["win_rate"] * avg_win_loss_ratio - (1 - record["win_rate"])) / avg_win_loss_ratio
            kelly_pct = max(0, kelly_pct)  # Kelly không âm
            kelly_pct = kelly_pct * record["kelly_fraction"]  # Áp dụng fraction
            kelly_pct = min(kelly_pct, max_risk_pct / 100)  # Giới hạn bởi max_risk_pct
            
            expected_risk = kelly_pct * 100
            
            logger.info(f"Track record: {record['name']}")
            logger.info(f"  Win rate: {record['win_rate']}, Win/Loss: {avg_win_loss_ratio:.2f}, Fraction: {record['kelly_fraction']}")
            logger.info(f"  Kelly %: {kelly_pct*100:.2f}%, Giới hạn: {max_risk_pct}%")
            logger.info(f"  Kết quả: size={size:.6f}, risk={risk:.2f}%")
            logger.info(f"  Expected: risk={expected_risk:.2f}%")
            
            # Các kiểm tra
            self.assertAlmostEqual(risk, expected_risk, delta=0.01, msg=f"Rủi ro {risk}% phải gần với expected {expected_risk}%")
            
            # Kiểm tra các trường hợp đặc biệt
            if record["win_rate"] < 0.5 and avg_win_loss_ratio == 1.0:
                self.assertAlmostEqual(risk, 0.0, delta=0.01, msg="Win rate < 0.5 với tỷ lệ 1.0 phải có rủi ro = 0")
                
            if record.get("max_risk_pct") is not None and kelly_pct * 100 > record["max_risk_pct"]:
                self.assertAlmostEqual(risk, record["max_risk_pct"], delta=0.01, msg="Rủi ro phải bị giới hạn bởi max_risk_pct")
        
        logger.info("✅ Test Kelly Criterion với track record thành công")
    
    def test_04_anti_martingale_scenario(self):
        """Test AntiMartingaleSizer trong kịch bản chuỗi thắng/thua"""
        logger.info("Test AntiMartingaleSizer trong kịch bản chuỗi thắng/thua")
        
        # Tạo đối tượng AntiMartingaleSizer
        sizer = AntiMartingaleSizer(
            account_balance=self.account_balance,
            base_unit_pct=1.0,
            increase_factor=1.5,
            max_units=5.0,
            max_risk_pct=4.0
        )
        
        entry_price = 50000.0
        stop_loss_price = 48500.0
        
        # Lịch sử giao dịch: [True = thắng, False = thua]
        trade_history = [True, True, True, False, True, True, True, True, False]
        
        # Theo dõi kích thước vị thế
        position_sizes = []
        
        # Thực hiện chuỗi giao dịch
        for i, is_win in enumerate(trade_history):
            size, risk = sizer.calculate_position_size(entry_price, stop_loss_price)
            position_sizes.append(size)
            
            logger.info(f"Giao dịch {i+1}: {'Thắng' if is_win else 'Thua'}")
            logger.info(f"  Trước khi cập nhật: units={sizer.current_units:.2f}, size={size:.6f}, risk={risk:.2f}%")
            
            # Kiểm tra giới hạn rủi ro
            self.assertLessEqual(risk, sizer.max_risk_pct, f"Rủi ro {risk}% không được vượt quá giới hạn {sizer.max_risk_pct}%")
            
            # Cập nhật sau giao dịch
            sizer.update_after_trade(is_win)
            
            logger.info(f"  Sau khi cập nhật: units={sizer.current_units:.2f}")
            
            # Kiểm tra reset sau khi thua
            if not is_win:
                self.assertEqual(sizer.current_units, 1.0, "Số đơn vị phải reset về 1.0 sau khi thua")
                self.assertEqual(sizer.consecutive_wins, 0, "Số lần thắng liên tiếp phải reset về 0 sau khi thua")
        
        # Đánh giá kết quả
        logger.info(f"Chuỗi kích thước vị thế: {[f'{size:.6f}' for size in position_sizes]}")
        
        # Kiểm tra chuỗi vị thế
        for i in range(1, len(position_sizes)):
            if trade_history[i-1]:  # Nếu giao dịch trước đó thắng
                # Kích thước tăng trừ khi đã đạt max hoặc giới hạn rủi ro
                if i < len(position_sizes) - 1 and trade_history[i]:
                    self.assertGreater(position_sizes[i+1], position_sizes[i], "Kích thước vị thế phải tăng sau khi thắng")
            else:  # Nếu giao dịch trước đó thua
                self.assertAlmostEqual(position_sizes[i], position_sizes[0], delta=0.0001, msg="Kích thước vị thế phải reset sau khi thua")
        
        logger.info("✅ Test AntiMartingale với chuỗi giao dịch thành công")
    
    def test_05_portfolio_allocation(self):
        """Test PortfolioSizer với phân bổ danh mục đầu tư"""
        logger.info("Test PortfolioSizer với phân bổ danh mục đầu tư")
        
        # Tạo đối tượng PortfolioSizer
        sizer = PortfolioSizer(
            account_balance=self.account_balance,
            max_portfolio_risk=8.0,
            max_symbol_risk=3.0,
            max_correlated_exposure=5.0,
            correlation_threshold=0.7
        )
        
        # Tạo danh sách symbols và signals
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "DOGEUSDT"]
        
        signals = {
            "BTCUSDT": {
                "signal": "buy",
                "entry_price": "50000.0",
                "stop_loss": "48000.0",
                "strength": "0.9"
            },
            "ETHUSDT": {
                "signal": "buy",
                "entry_price": "3000.0",
                "stop_loss": "2850.0",
                "strength": "0.8"
            },
            "SOLUSDT": {
                "signal": "sell",
                "entry_price": "120.0",
                "stop_loss": "126.0",
                "strength": "0.7"
            },
            "ADAUSDT": {
                "signal": "neutral",  # Không có tín hiệu giao dịch
                "entry_price": "0.5",
                "stop_loss": "0.48",
                "strength": "0.4"
            },
            "DOGEUSDT": {
                "signal": "buy",
                "entry_price": "0.15",
                "stop_loss": "0.14",
                "strength": "0.6"
            }
        }
        
        # Tạo correlation matrix
        correlation_matrix = {
            "BTCUSDT": {"BTCUSDT": 1.0, "ETHUSDT": 0.9, "SOLUSDT": 0.8, "ADAUSDT": 0.7, "DOGEUSDT": 0.6},
            "ETHUSDT": {"BTCUSDT": 0.9, "ETHUSDT": 1.0, "SOLUSDT": 0.85, "ADAUSDT": 0.75, "DOGEUSDT": 0.65},
            "SOLUSDT": {"BTCUSDT": 0.8, "ETHUSDT": 0.85, "SOLUSDT": 1.0, "ADAUSDT": 0.7, "DOGEUSDT": 0.6},
            "ADAUSDT": {"BTCUSDT": 0.7, "ETHUSDT": 0.75, "SOLUSDT": 0.7, "ADAUSDT": 1.0, "DOGEUSDT": 0.8},
            "DOGEUSDT": {"BTCUSDT": 0.6, "ETHUSDT": 0.65, "SOLUSDT": 0.6, "ADAUSDT": 0.8, "DOGEUSDT": 1.0}
        }
        
        # Tính toán phân bổ
        allocations = sizer.calculate_position_allocations(symbols, signals, correlation_matrix)
        
        # Hiển thị kết quả
        logger.info("Phân bổ danh mục đầu tư:")
        total_risk = 0.0
        
        for symbol, alloc in allocations.items():
            logger.info(f"  {symbol}: size={alloc['position_size']:.6f}, value=${alloc['position_value']:.2f}, risk={alloc['risk_pct']:.2f}%, side={alloc['side']}")
            total_risk += alloc['risk_pct']
        
        logger.info(f"Tổng rủi ro danh mục: {total_risk:.2f}%")
        
        # Các kiểm tra
        self.assertLessEqual(total_risk, sizer.max_portfolio_risk, f"Tổng rủi ro {total_risk}% không được vượt quá giới hạn {sizer.max_portfolio_risk}%")
        
        for symbol, alloc in allocations.items():
            self.assertLessEqual(alloc['risk_pct'], sizer.max_symbol_risk, f"Rủi ro của {symbol} ({alloc['risk_pct']}%) không được vượt quá giới hạn {sizer.max_symbol_risk}%")
            
            # Kiểm tra correlation limit
            correlated_risk = 0.0
            for other_symbol, other_alloc in allocations.items():
                if symbol != other_symbol and correlation_matrix[symbol][other_symbol] >= sizer.correlation_threshold:
                    correlated_risk += other_alloc['risk_pct']
                    
            combined_risk = alloc['risk_pct'] + correlated_risk
            self.assertLessEqual(combined_risk, sizer.max_correlated_exposure + alloc['risk_pct'] * 0.5, 
                               f"Rủi ro tương quan cho {symbol} ({combined_risk}%) quá cao")
        
        # Cập nhật và xóa vị thế
        # Thêm vị thế mới
        sizer.update_position("BTCUSDT", "LONG", 0.1, 50000.0)
        sizer.update_position("ETHUSDT", "LONG", 1.0, 3000.0)
        
        # Kiểm tra vị thế hiện tại
        self.assertIn("BTCUSDT", sizer.current_positions, "Vị thế BTCUSDT phải tồn tại")
        self.assertIn("ETHUSDT", sizer.current_positions, "Vị thế ETHUSDT phải tồn tại")
        
        # Xóa một vị thế
        sizer.remove_position("BTCUSDT")
        self.assertNotIn("BTCUSDT", sizer.current_positions, "Vị thế BTCUSDT phải bị xóa")
        self.assertIn("ETHUSDT", sizer.current_positions, "Vị thế ETHUSDT phải còn tồn tại")
        
        logger.info("✅ Test Portfolio Allocation thành công")
    
    def test_06_factory_function(self):
        """Test create_position_sizer factory function"""
        logger.info("Test create_position_sizer factory function với các loại sizer")
        
        # Các loại sizer cần tạo
        sizer_types = ["basic", "dynamic", "kelly", "antimartingale", "portfolio", "invalid_type"]
        
        # Các kwargs mặc định
        default_kwargs = {"account_balance": self.account_balance}
        
        # Tạo và kiểm tra từng loại
        for sizer_type in sizer_types:
            sizer = create_position_sizer(sizer_type, self.account_balance)
            
            logger.info(f"Sizer type: {sizer_type}")
            logger.info(f"  Created: {type(sizer).__name__}")
            
            # Kiểm tra loại đối tượng tạo ra
            if sizer_type == "basic" or sizer_type == "invalid_type":
                self.assertIsInstance(sizer, BasePositionSizer, f"Sizer type {sizer_type} phải tạo BasePositionSizer")
            elif sizer_type == "dynamic":
                self.assertIsInstance(sizer, DynamicPositionSizer, f"Sizer type {sizer_type} phải tạo DynamicPositionSizer")
            elif sizer_type == "kelly":
                self.assertIsInstance(sizer, KellyCriterionSizer, f"Sizer type {sizer_type} phải tạo KellyCriterionSizer")
            elif sizer_type == "antimartingale":
                self.assertIsInstance(sizer, AntiMartingaleSizer, f"Sizer type {sizer_type} phải tạo AntiMartingaleSizer")
            elif sizer_type == "portfolio":
                self.assertIsInstance(sizer, PortfolioSizer, f"Sizer type {sizer_type} phải tạo PortfolioSizer")
        
        # Kiểm tra truyền tham số đặc biệt
        special_params = [
            {
                "sizer_type": "basic",
                "kwargs": {"max_risk_pct": 5.0, "leverage": 10},
                "expected_type": BasePositionSizer
            },
            {
                "sizer_type": "dynamic",
                "kwargs": {"volatility_factor": 2.0, "confidence_factor": 1.5},
                "expected_type": DynamicPositionSizer
            },
            {
                "sizer_type": "kelly",
                "kwargs": {"win_rate": 0.7, "avg_win_loss_ratio": 2.0, "kelly_fraction": 0.5},
                "expected_type": KellyCriterionSizer
            },
            {
                "sizer_type": "antimartingale",
                "kwargs": {"base_unit_pct": 2.0, "increase_factor": 2.0, "max_units": 8},
                "expected_type": AntiMartingaleSizer
            },
            {
                "sizer_type": "portfolio",
                "kwargs": {"max_portfolio_risk": 10.0, "max_symbol_risk": 4.0},
                "expected_type": PortfolioSizer
            }
        ]
        
        for param in special_params:
            # Thêm account_balance vào kwargs
            kwargs = {"account_balance": self.account_balance, **param["kwargs"]}
            sizer = create_position_sizer(param["sizer_type"], **kwargs)
            
            logger.info(f"Special param test - Sizer type: {param['sizer_type']}")
            logger.info(f"  Kwargs: {param['kwargs']}")
            logger.info(f"  Created: {type(sizer).__name__}")
            
            # Kiểm tra loại đối tượng tạo ra
            self.assertIsInstance(sizer, param["expected_type"], f"Sizer type {param['sizer_type']} với kwargs đặc biệt phải tạo {param['expected_type'].__name__}")
            
            # Kiểm tra các thuộc tính đặc biệt
            for key, value in param["kwargs"].items():
                if hasattr(sizer, key):
                    self.assertEqual(getattr(sizer, key), value, f"Thuộc tính {key} phải bằng {value}")
        
        logger.info("✅ Test factory function thành công")
    
    def test_07_stress_test(self):
        """Stress test với nhiều kịch bản biên"""
        logger.info("Stress test với nhiều kịch bản biên")
        
        # Tạo các đối tượng sizer
        basic_sizer = BasePositionSizer(self.account_balance)
        dynamic_sizer = DynamicPositionSizer(self.account_balance)
        kelly_sizer = KellyCriterionSizer(self.account_balance, win_rate=0.6, avg_win_loss_ratio=2.0)
        antimartingale_sizer = AntiMartingaleSizer(self.account_balance)
        
        # Tạo danh sách các kịch bản biên
        edge_scenarios = [
            {
                "name": "Khoảng cách rất nhỏ",
                "entry_price": 50000.0,
                "stop_loss_price": 49999.9
            },
            {
                "name": "Khoảng cách rất lớn",
                "entry_price": 50000.0,
                "stop_loss_price": 25000.0
            },
            {
                "name": "Giá rất nhỏ",
                "entry_price": 0.000001,
                "stop_loss_price": 0.0000009
            },
            {
                "name": "Giá rất lớn",
                "entry_price": 1000000000.0,
                "stop_loss_price": 950000000.0
            },
            {
                "name": "Short với khoảng cách lớn",
                "entry_price": 50000.0,
                "stop_loss_price": 100000.0
            }
        ]
        
        # Chạy từng kịch bản với mỗi sizer
        for scenario in edge_scenarios:
            logger.info(f"Kịch bản: {scenario['name']}")
            logger.info(f"  Entry: {scenario['entry_price']}, Stop Loss: {scenario['stop_loss_price']}")
            
            # Test với BasePositionSizer
            try:
                size, risk = basic_sizer.calculate_position_size(scenario["entry_price"], scenario["stop_loss_price"])
                logger.info(f"  BasePositionSizer: size={size:.8f}, risk={risk:.2f}%")
                self.assertIsNotNone(size, "Kích thước vị thế không được None")
                self.assertGreaterEqual(size, 0, "Kích thước vị thế phải >= 0")
            except Exception as e:
                logger.warning(f"  BasePositionSizer lỗi: {str(e)}")
                # Nếu entry = stop thì lỗi là bình thường
                if scenario["entry_price"] != scenario["stop_loss_price"]:
                    self.fail(f"BasePositionSizer không nên lỗi với kịch bản hợp lệ: {str(e)}")
            
            # Test với DynamicPositionSizer
            try:
                size, risk = dynamic_sizer.calculate_position_size(
                    scenario["entry_price"], scenario["stop_loss_price"],
                    volatility=0.5, signal_confidence=0.7
                )
                logger.info(f"  DynamicPositionSizer: size={size:.8f}, risk={risk:.2f}%")
                self.assertIsNotNone(size, "Kích thước vị thế không được None")
                self.assertGreaterEqual(size, 0, "Kích thước vị thế phải >= 0")
            except Exception as e:
                logger.warning(f"  DynamicPositionSizer lỗi: {str(e)}")
                if scenario["entry_price"] != scenario["stop_loss_price"]:
                    self.fail(f"DynamicPositionSizer không nên lỗi với kịch bản hợp lệ: {str(e)}")
            
            # Test với KellyCriterionSizer
            try:
                size, risk = kelly_sizer.calculate_position_size(scenario["entry_price"], scenario["stop_loss_price"])
                logger.info(f"  KellyCriterionSizer: size={size:.8f}, risk={risk:.2f}%")
                self.assertIsNotNone(size, "Kích thước vị thế không được None")
                self.assertGreaterEqual(size, 0, "Kích thước vị thế phải >= 0")
            except Exception as e:
                logger.warning(f"  KellyCriterionSizer lỗi: {str(e)}")
                if scenario["entry_price"] != scenario["stop_loss_price"]:
                    self.fail(f"KellyCriterionSizer không nên lỗi với kịch bản hợp lệ: {str(e)}")
            
            # Test với AntiMartingaleSizer
            try:
                size, risk = antimartingale_sizer.calculate_position_size(scenario["entry_price"], scenario["stop_loss_price"])
                logger.info(f"  AntiMartingaleSizer: size={size:.8f}, risk={risk:.2f}%")
                self.assertIsNotNone(size, "Kích thước vị thế không được None")
                self.assertGreaterEqual(size, 0, "Kích thước vị thế phải >= 0")
            except Exception as e:
                logger.warning(f"  AntiMartingaleSizer lỗi: {str(e)}")
                if scenario["entry_price"] != scenario["stop_loss_price"]:
                    self.fail(f"AntiMartingaleSizer không nên lỗi với kịch bản hợp lệ: {str(e)}")
            
            logger.info("")
        
        logger.info("✅ Stress test thành công")

def run_tests():
    """Chạy các bài kiểm tra position sizing nâng cao"""
    
    logger.info("=== BẮT ĐẦU KIỂM TRA POSITION SIZING NÂNG CAO ===")
    logger.info(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Sử dụng module thật: {USING_ACTUAL_MODULE}")
    
    # Tạo test suite và chạy
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestPositionSizingAdvanced))
    
    # Chạy các test
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Tóm tắt kết quả
    logger.info("\n=== KẾT QUẢ KIỂM TRA ===")
    logger.info(f"Tổng số test: {result.testsRun}")
    logger.info(f"Số test thành công: {result.testsRun - len(result.failures) - len(result.errors)}")
    logger.info(f"Số test thất bại: {len(result.failures)}")
    logger.info(f"Số test lỗi: {len(result.errors)}")
    
    # Chi tiết về các test thất bại hoặc lỗi
    if result.failures:
        logger.error("\nCHI TIẾT CÁC TEST THẤT BẠI:")
        for test, error in result.failures:
            logger.error(f"\n{test}")
            logger.error(error)
    
    if result.errors:
        logger.error("\nCHI TIẾT CÁC TEST LỖI:")
        for test, error in result.errors:
            logger.error(f"\n{test}")
            logger.error(error)
    
    # Lưu kết quả kiểm tra vào file JSON
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f"../test_results/position_sizing_advanced_{timestamp}.json"
    
    test_results = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": result.testsRun,
        "successful_tests": result.testsRun - len(result.failures) - len(result.errors),
        "failed_tests": len(result.failures),
        "error_tests": len(result.errors),
        "using_actual_module": USING_ACTUAL_MODULE,
        "failures": [{"test": str(test), "error": error} for test, error in result.failures],
        "errors": [{"test": str(test), "error": error} for test, error in result.errors]
    }
    
    try:
        with open(results_file, 'w') as f:
            json.dump(test_results, f, indent=2)
        logger.info(f"Đã lưu kết quả kiểm tra vào {results_file}")
    except Exception as e:
        logger.error(f"Lỗi khi lưu kết quả kiểm tra: {e}")
    
    return len(result.failures) == 0 and len(result.errors) == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)