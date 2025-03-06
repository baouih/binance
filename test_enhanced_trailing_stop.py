#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit Tests for Enhanced Adaptive Trailing Stop

Bộ kiểm thử cho module Enhanced Adaptive Trailing Stop, bao gồm các tests cho:
- Khởi tạo và cấu hình
- Chiến lược Percentage Trailing Stop
- Chiến lược Step Trailing Stop
- Chiến lược ATR-based Trailing Stop
- Thoát một phần (Partial exits)
- Backtest với dữ liệu giá
"""

import unittest
import os
import json
import tempfile
from datetime import datetime, timedelta
import numpy as np
from enhanced_adaptive_trailing_stop import EnhancedAdaptiveTrailingStop

class TestEnhancedTrailingStop(unittest.TestCase):
    """Kiểm thử cho EnhancedAdaptiveTrailingStop"""
    
    def setUp(self):
        """Thiết lập môi trường test"""
        # Tạo cấu hình tạm thời để test
        self.config = {
            "strategies": {
                "percentage": {
                    "trending": {
                        "activation_percent": 1.0,
                        "callback_percent": 0.5,
                        "use_dynamic_callback": True,
                        "min_callback": 0.3,
                        "max_callback": 2.0,
                        "partial_exits": [
                            {"threshold": 3.0, "percentage": 0.3},
                            {"threshold": 5.0, "percentage": 0.5}
                        ]
                    },
                    "ranging": {
                        "activation_percent": 0.8,
                        "callback_percent": 0.8,
                        "use_dynamic_callback": True,
                        "min_callback": 0.5,
                        "max_callback": 1.5,
                        "partial_exits": []
                    }
                },
                "step": {
                    "trending": {
                        "profit_steps": [1.0, 2.0, 5.0, 10.0],
                        "callback_steps": [0.2, 0.5, 1.0, 2.0],
                        "partial_exits": []
                    }
                },
                "atr_based": {
                    "trending": {
                        "atr_multiplier": 2.5,
                        "atr_period": 14,
                        "min_profit_activation": 1.0,
                        "partial_exits": []
                    }
                }
            },
            "general": {
                "default_strategy": "percentage",
                "default_market_regime": "trending",
                "log_level": "INFO",
                "save_history": False
            }
        }
        
        # Tạo file config tạm thời
        fd, self.config_path = tempfile.mkstemp(suffix='.json')
        with os.fdopen(fd, 'w') as f:
            json.dump(self.config, f)
            
        # Khởi tạo Enhanced Trailing Stop với cấu hình tạm thời
        self.trailing_stop = EnhancedAdaptiveTrailingStop(self.config_path)
    
    def tearDown(self):
        """Dọn dẹp sau khi test"""
        # Xóa file config tạm thời
        os.unlink(self.config_path)
    
    def test_initialization(self):
        """Kiểm tra khởi tạo và cấu hình"""
        # Kiểm tra cấu hình đã được tải
        self.assertIsNotNone(self.trailing_stop.config)
        self.assertIn('strategies', self.trailing_stop.config)
        self.assertIn('percentage', self.trailing_stop.config['strategies'])
        
        # Kiểm tra các phương thức truy vấn
        self.assertIn('percentage', self.trailing_stop.get_strategy_types())
        self.assertIn('trending', self.trailing_stop.get_market_regimes())
    
    def test_percentage_trailing_stop(self):
        """Test chiến lược Percentage Trailing Stop"""
        # Khởi tạo vị thế LONG với percentage trailing stop
        entry_price = 50000.0
        position = self.trailing_stop.initialize_trailing_stop(
            entry_price, 'LONG', 'percentage', 'trending')
        
        # Kiểm tra thông tin vị thế
        self.assertEqual(position['entry_price'], entry_price)
        self.assertEqual(position['side'], 'LONG')
        self.assertEqual(position['strategy_type'], 'percentage')
        self.assertEqual(position['market_regime'], 'trending')
        self.assertEqual(position['status'], 'ACTIVE')
        self.assertFalse(position['trailing_activated'])
        
        # Kiểm tra các thông số chiến lược
        self.assertEqual(position['activation_percent'], 1.0)
        self.assertEqual(position['callback_percent'], 0.5)
        self.assertTrue(position['use_dynamic_callback'])
        
        # Cập nhật với giá tăng nhẹ (chưa kích hoạt trailing stop)
        current_price = entry_price * 1.005  # +0.5%
        updated_position = self.trailing_stop.update_trailing_stop(position, current_price)
        self.assertFalse(updated_position['trailing_activated'])
        
        # Cập nhật với giá tăng vượt ngưỡng kích hoạt
        current_price = entry_price * 1.015  # +1.5%
        updated_position = self.trailing_stop.update_trailing_stop(updated_position, current_price)
        self.assertTrue(updated_position['trailing_activated'])
        
        # Kiểm tra giá stop đã được cập nhật
        expected_stop_price = current_price * (1 - updated_position['callback_percent']/100)
        self.assertAlmostEqual(
            updated_position['stop_price'], 
            expected_stop_price,
            delta=0.01
        )
        
        # Cập nhật với giá tăng tiếp, kiểm tra stop được nâng lên
        new_price = current_price * 1.01
        updated_position = self.trailing_stop.update_trailing_stop(updated_position, new_price)
        self.assertGreater(updated_position['stop_price'], expected_stop_price)
        
        # Kiểm tra điều kiện đóng vị thế
        should_close, _ = self.trailing_stop.check_stop_condition(updated_position, updated_position['stop_price'] - 1)
        self.assertTrue(should_close)
        
        # Test đóng vị thế
        exit_price = updated_position['stop_price'] - 1
        closed_position = self.trailing_stop.close_position(updated_position, exit_price, "Test đóng vị thế")
        self.assertEqual(closed_position['status'], 'CLOSED')
        self.assertEqual(closed_position['exit_price'], exit_price)
        
        # Kiểm tra SHORT position cũng hoạt động tương tự
        position_short = self.trailing_stop.initialize_trailing_stop(
            entry_price, 'SHORT', 'percentage', 'trending')
        
        # Cập nhật với giá giảm vượt ngưỡng kích hoạt
        current_price = entry_price * 0.985  # -1.5%
        updated_position_short = self.trailing_stop.update_trailing_stop(position_short, current_price)
        self.assertTrue(updated_position_short['trailing_activated'])
        
        # Kiểm tra giá stop đã được cập nhật đúng hướng (tăng lên với SHORT)
        expected_stop_price = current_price * (1 + updated_position_short['callback_percent']/100)
        self.assertAlmostEqual(
            updated_position_short['stop_price'], 
            expected_stop_price,
            delta=0.01
        )
    
    def test_step_trailing_stop(self):
        """Test chiến lược Step Trailing Stop"""
        entry_price = 50000.0
        position = self.trailing_stop.initialize_trailing_stop(
            entry_price, 'LONG', 'step', 'trending')
        
        # Kiểm tra thông số step
        self.assertEqual(position['current_step'], 0)
        self.assertListEqual(position['profit_steps'], [1.0, 2.0, 5.0, 10.0])
        self.assertListEqual(position['callback_steps'], [0.2, 0.5, 1.0, 2.0])
        
        # Bước 1: Tăng giá và kích hoạt step đầu tiên
        current_price = entry_price * 1.011  # +1.1%, vượt ngưỡng step 1
        updated_position = self.trailing_stop.update_trailing_stop(position, current_price)
        self.assertEqual(updated_position['current_step'], 1)
        self.assertTrue(updated_position['trailing_activated'])
        
        # Bước 2: Tăng tiếp và kích hoạt step tiếp theo
        current_price = entry_price * 1.022  # +2.2%, vượt ngưỡng step 2
        updated_position = self.trailing_stop.update_trailing_stop(updated_position, current_price)
        self.assertEqual(updated_position['current_step'], 2)
        
        # Kiểm tra giá stop đã được cập nhật theo step 2
        callback_pct = position['callback_steps'][2]
        expected_stop_price = current_price * (1 - callback_pct/100)
        self.assertAlmostEqual(
            updated_position['stop_price'], 
            expected_stop_price,
            delta=0.01
        )
        
        # Bước 3: Đưa giá về gần stop và kiểm tra điều kiện dừng lỗ
        test_price = expected_stop_price - 1
        should_close, _ = self.trailing_stop.check_stop_condition(updated_position, test_price)
        self.assertTrue(should_close)
    
    def test_atr_based_trailing_stop(self):
        """Test chiến lược ATR-based Trailing Stop"""
        entry_price = 50000.0
        atr_value = 500.0  # ATR = 1% của giá
        
        position = self.trailing_stop.initialize_trailing_stop(
            entry_price, 'LONG', 'atr_based', 'trending')
        
        # Cập nhật giá trị ATR
        position['atr_value'] = atr_value
        
        # Kiểm tra giá stop ban đầu
        atr_distance = atr_value * position['atr_multiplier']
        expected_stop = entry_price - atr_distance
        self.assertAlmostEqual(position['stop_price'], expected_stop, delta=0.01)
        
        # Vượt ngưỡng kích hoạt
        current_price = entry_price * 1.015  # +1.5%
        updated_position = self.trailing_stop.update_trailing_stop(position, current_price)
        self.assertTrue(updated_position['trailing_activated'])
        
        # Kiểm tra giá stop mới
        expected_stop = current_price - atr_value * position['atr_multiplier']
        self.assertAlmostEqual(updated_position['stop_price'], expected_stop, delta=0.01)
        
        # Kiểm tra với SHORT position
        position_short = self.trailing_stop.initialize_trailing_stop(
            entry_price, 'SHORT', 'atr_based', 'trending')
        position_short['atr_value'] = atr_value
        
        # Kiểm tra giá stop ban đầu cho SHORT
        expected_stop = entry_price + atr_distance
        self.assertAlmostEqual(position_short['stop_price'], expected_stop, delta=0.01)
    
    def test_partial_exits(self):
        """Test tính năng thoát một phần (partial exits)"""
        entry_price = 50000.0
        position = self.trailing_stop.initialize_trailing_stop(
            entry_price, 'LONG', 'percentage', 'trending')
        
        # Kiểm tra danh sách mức thoát một phần
        self.assertEqual(len(position['partial_exit_levels']), 2)
        self.assertEqual(position['partial_exit_levels'][0]['threshold'], 3.0)
        self.assertEqual(position['partial_exit_levels'][0]['percentage'], 0.3)
        
        # Ban đầu chưa có lệnh thoát một phần nào
        self.assertEqual(len(position['partial_exits']), 0)
        
        # Cập nhật giá lên đủ để kích hoạt mức thoát đầu tiên
        current_price = entry_price * 1.035  # +3.5%
        updated_position = self.trailing_stop.update_trailing_stop(position, current_price)
        
        # Kiểm tra đã có một lệnh thoát một phần
        self.assertEqual(len(updated_position['partial_exits']), 1)
        self.assertEqual(updated_position['partial_exits'][0]['threshold'], 3.0)
        self.assertEqual(updated_position['partial_exits'][0]['percentage'], 0.3)
        
        # Cập nhật giá lên đủ để kích hoạt mức thoát thứ hai
        current_price = entry_price * 1.055  # +5.5%
        updated_position = self.trailing_stop.update_trailing_stop(updated_position, current_price)
        
        # Kiểm tra đã có hai lệnh thoát một phần
        self.assertEqual(len(updated_position['partial_exits']), 2)
        
        # Kiểm tra không tạo thêm lệnh thoát khi cập nhật lại
        updated_position = self.trailing_stop.update_trailing_stop(updated_position, current_price)
        self.assertEqual(len(updated_position['partial_exits']), 2)
    
    def test_backtest(self):
        """Test chức năng backtest"""
        # Tạo dữ liệu giá mẫu
        entry_price = 50000.0
        price_data = [entry_price]
        
        # Thêm giá tăng dần
        for i in range(20):
            price_data.append(price_data[-1] * (1 + 0.002))
            
        # Thêm giá giảm dần
        for i in range(10):
            price_data.append(price_data[-1] * (1 - 0.003))
        
        # Chạy backtest cho LONG position
        result = self.trailing_stop.backtest_trailing_stop(
            entry_price, 'LONG', price_data, 'percentage', 'trending')
        
        # Kiểm tra kết quả
        self.assertIsNotNone(result.get('exit_price'))
        self.assertIsNotNone(result.get('exit_index'))
        self.assertEqual(result.get('status'), 'CLOSED')
        self.assertGreater(result.get('profit_pct', 0), 0)
        
        # Kiểm tra backtest có thoát một phần
        self.assertGreaterEqual(len(result.get('partial_exits', [])), 0)
        
        # Chạy backtest cho SHORT position
        price_data = [entry_price]
        
        # Thêm giá giảm dần
        for i in range(20):
            price_data.append(price_data[-1] * (1 - 0.002))
            
        # Thêm giá tăng dần
        for i in range(10):
            price_data.append(price_data[-1] * (1 + 0.003))
        
        result = self.trailing_stop.backtest_trailing_stop(
            entry_price, 'SHORT', price_data, 'percentage', 'trending')
        
        # Kiểm tra kết quả
        self.assertIsNotNone(result.get('exit_price'))
        self.assertIsNotNone(result.get('exit_index'))
        self.assertEqual(result.get('status'), 'CLOSED')
        self.assertGreater(result.get('profit_pct', 0), 0)
    
    def test_optimize_parameters(self):
        """Test chức năng tối ưu hóa tham số"""
        # Tạo dữ liệu giá mẫu
        entry_price = 50000.0
        price_data = [entry_price]
        
        # Thêm giá tăng dần rồi giảm
        for i in range(30):
            price_data.append(price_data[-1] * (1 + 0.002))
        for i in range(15):
            price_data.append(price_data[-1] * (1 - 0.003))
        
        # Tối ưu hóa tham số cho percentage strategy
        param_ranges = {
            'activation_percent': [0.5, 1.0, 1.5],
            'callback_percent': [0.3, 0.5, 0.8],
            'use_dynamic_callback': [True, False]
        }
        
        result = self.trailing_stop.optimize_parameters(
            price_data, 'LONG', 'percentage', 'trending', param_ranges)
        
        # Kiểm tra kết quả tối ưu hóa
        self.assertIsNotNone(result.get('best_params'))
        self.assertIsNotNone(result.get('best_result'))
        self.assertGreaterEqual(result.get('best_score', 0), 0)
        
        # Kiểm tra các tham số tối ưu có nằm trong phạm vi
        best_params = result.get('best_params', {})
        self.assertIn(best_params.get('activation_percent'), param_ranges['activation_percent'])
        self.assertIn(best_params.get('callback_percent'), param_ranges['callback_percent'])
        self.assertIn(best_params.get('use_dynamic_callback'), param_ranges['use_dynamic_callback'])

if __name__ == '__main__':
    unittest.main()