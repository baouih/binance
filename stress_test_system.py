#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module kiểm thử dưới điều kiện khắc nghiệt cho hệ thống giao dịch

Module này thực hiện các bài kiểm tra dưới điều kiện cực đoan 
để đảm bảo tính ổn định của hệ thống giao dịch.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json
import time
import random
import traceback
from typing import Dict, List, Any, Optional

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/stress_test.log')
    ]
)

logger = logging.getLogger('stress_test')

# Đảm bảo thư mục logs tồn tại
os.makedirs('logs', exist_ok=True)
os.makedirs('stress_test_results', exist_ok=True)

# Import các module cần kiểm thử
try:
    from sideways_market_optimizer import SidewaysMarketOptimizer
    from enhanced_trailing_stop_manager import EnhancedTrailingStopManager
except ImportError as e:
    logger.error(f"Lỗi import module: {str(e)}")
    print(f"Lỗi import module: {str(e)}")
    print("Hãy chắc chắn các module sideways_market_optimizer.py và enhanced_trailing_stop_manager.py đã được tạo.")
    sys.exit(1)

class StressTestRunner:
    """
    Lớp thực hiện các bài kiểm tra khắc nghiệt
    """
    
    def __init__(self):
        """Khởi tạo bộ kiểm thử"""
        self.sideways_optimizer = None
        self.trailing_manager = None
        self.test_results = {}
        self.mock_api = self.create_mock_api()
        
        logger.info("Đã khởi tạo StressTestRunner")
    
    def create_mock_api(self):
        """
        Tạo mock API với khả năng giả lập lỗi
        
        Returns:
            object: Mock API client
        """
        class MockAPIClient:
            def __init__(self, failure_rate=0.0):
                self.failure_rate = failure_rate
                self.orders = {}
                self.call_count = 0
                self.slow_response = False
                self.response_delay = 0
                
            def set_failure_rate(self, rate):
                """Đặt tỷ lệ thất bại"""
                self.failure_rate = max(0.0, min(1.0, rate))
                
            def set_slow_response(self, is_slow, delay=1.0):
                """Đặt phản hồi chậm"""
                self.slow_response = is_slow
                self.response_delay = delay
                
            def _should_fail(self):
                """Kiểm tra xem có nên giả lập lỗi không"""
                self.call_count += 1
                if random.random() < self.failure_rate:
                    return True
                return False
                
            def create_order(self, **kwargs):
                """Tạo lệnh mới"""
                if self._should_fail():
                    raise Exception("API Error: Could not create order")
                    
                if self.slow_response:
                    time.sleep(self.response_delay)
                    
                order_id = str(random.randint(10000, 99999))
                self.orders[order_id] = {
                    "orderId": order_id,
                    "status": "FILLED",
                    "timestamp": datetime.now().timestamp() * 1000,
                    **kwargs
                }
                return self.orders[order_id]
                
            def cancel_order(self, **kwargs):
                """Hủy lệnh"""
                if self._should_fail():
                    raise Exception("API Error: Could not cancel order")
                    
                if self.slow_response:
                    time.sleep(self.response_delay)
                    
                order_id = kwargs.get("orderId")
                if order_id in self.orders:
                    self.orders[order_id]["status"] = "CANCELED"
                    return {"orderId": order_id, "status": "CANCELED"}
                else:
                    raise Exception(f"Order {order_id} not found")
                
            def get_klines(self, **kwargs):
                """Lấy dữ liệu K-lines"""
                if self._should_fail():
                    raise Exception("API Error: Could not fetch klines")
                    
                if self.slow_response:
                    time.sleep(self.response_delay)
                    
                # Tạo dữ liệu giả
                klines = []
                now = time.time() * 1000
                base_price = 50000
                
                for i in range(kwargs.get('limit', 100)):
                    timestamp = now - (kwargs.get('limit', 100) - i) * 60 * 60 * 1000
                    close = base_price + random.uniform(-1000, 1000)
                    klines.append([
                        timestamp,
                        close - random.uniform(-100, 100),
                        close + random.uniform(0, 200),
                        close - random.uniform(0, 200),
                        close,
                        random.uniform(100, 1000)
                    ])
                
                return klines
                
            def get_ticker(self, **kwargs):
                """Lấy thông tin ticker"""
                if self._should_fail():
                    raise Exception("API Error: Could not fetch ticker")
                    
                if self.slow_response:
                    time.sleep(self.response_delay)
                    
                return {
                    "symbol": kwargs.get("symbol", "BTCUSDT"),
                    "price": str(50000 + random.uniform(-1000, 1000)),
                    "time": datetime.now().timestamp() * 1000
                }
        
        return MockAPIClient()
    
    def generate_extreme_market_data(self, scenario: str = "normal") -> pd.DataFrame:
        """
        Tạo dữ liệu thị trường cực đoan cho các bài kiểm tra
        
        Args:
            scenario (str): Loại kịch bản thị trường
                'normal': Dữ liệu thị trường thông thường
                'flash_crash': Sụp đổ nhanh chóng
                'price_spike': Đợt tăng giá mạnh
                'sideways_squeeze': Thị trường sideway cực đoan
                'high_volatility': Biến động cao
                'low_liquidity': Thanh khoản thấp
            
        Returns:
            pd.DataFrame: DataFrame với dữ liệu OHLC
        """
        # Tạo dữ liệu cơ sở
        n_samples = 200
        dates = pd.date_range(start='2023-01-01', periods=n_samples, freq='1H')
        
        if scenario == "flash_crash":
            # Mô phỏng sụp đổ nhanh chóng (-20% trong vài giờ)
            base_price = 50000
            prices = np.ones(n_samples) * base_price
            
            # Thời điểm sụp đổ
            crash_start = int(n_samples * 0.7)
            crash_duration = 5
            
            for i in range(crash_duration):
                crash_idx = crash_start + i
                prices[crash_idx:] = prices[crash_idx-1] * 0.92  # Giảm 8% mỗi giờ
            
        elif scenario == "price_spike":
            # Mô phỏng đợt tăng giá đột ngột (+30% trong vài giờ)
            base_price = 50000
            prices = np.ones(n_samples) * base_price
            
            # Thời điểm tăng giá
            spike_start = int(n_samples * 0.6)
            spike_duration = 3
            
            for i in range(spike_duration):
                spike_idx = spike_start + i
                prices[spike_idx:] = prices[spike_idx-1] * 1.1  # Tăng 10% mỗi giờ
            
        elif scenario == "sideways_squeeze":
            # Thị trường sideway cực đoan (biến động < 0.1%)
            base_price = 50000
            volatility = 0.001  # 0.1%
            
            # Tạo dao động nhỏ quanh giá trung bình
            random_moves = np.random.normal(0, volatility, n_samples)
            prices = base_price * (1 + np.cumsum(random_moves))
            
            # Giới hạn biến động trong khoảng rất hẹp
            prices = np.clip(prices, base_price * 0.995, base_price * 1.005)
            
        elif scenario == "high_volatility":
            # Biến động cao, dao động mạnh trong cả hai chiều
            base_price = 50000
            volatility = 0.03  # 3%
            
            # Tạo chuyển động ngẫu nhiên với biến động cao
            random_moves = np.random.normal(0, volatility, n_samples)
            prices = base_price * (1 + np.cumsum(random_moves))
            
            # Thêm các đỉnh và đáy cực đoan
            for i in range(5):
                spike_idx = random.randint(20, n_samples-20)
                spike_direction = random.choice([-1, 1])
                spike_size = random.uniform(0.05, 0.15)  # 5% đến 15%
                
                prices[spike_idx] = prices[spike_idx-1] * (1 + spike_direction * spike_size)
                # Điều chỉnh các giá sau spike
                adjustment = np.linspace(spike_direction * spike_size, 0, 10)
                for j in range(1, 10):
                    if spike_idx + j < n_samples:
                        prices[spike_idx + j] = prices[spike_idx-1] * (1 + adjustment[j])
            
        elif scenario == "low_liquidity":
            # Thanh khoản thấp - giá chênh lệch cao, biến động không đều
            base_price = 50000
            
            # Tạo chuyển động cơ bản
            trend = np.linspace(0, 0.02, n_samples)  # Xu hướng tăng nhẹ
            noise = np.random.normal(0, 0.015, n_samples)  # Nhiễu
            prices = base_price * (1 + trend + noise)
            
            # Thêm các đợt giá bật mạnh do thanh khoản thấp
            for i in range(8):
                gap_idx = random.randint(10, n_samples-10)
                gap_direction = random.choice([-1, 1])
                gap_size = random.uniform(0.03, 0.08)  # 3% đến 8%
                
                prices[gap_idx:] = prices[gap_idx-1] * (1 + gap_direction * gap_size)
        
        else:  # normal
            # Thị trường thông thường với xu hướng nhẹ
            base_price = 50000
            trend = np.linspace(0, 0.1, n_samples)  # Xu hướng tăng 10%
            noise = np.random.normal(0, 0.01, n_samples)  # Nhiễu 1%
            prices = base_price * (1 + trend + noise)
        
        # Tạo DataFrame
        df = pd.DataFrame({
            'open': prices * 0.998,
            'high': prices * 1.004,
            'low': prices * 0.996,
            'close': prices,
            'volume': np.random.randint(100, 10000, n_samples)
        }, index=dates)
        
        # Điều chỉnh high/low để hợp lý
        for i in range(1, len(df)):
            df.loc[df.index[i], 'open'] = df.loc[df.index[i-1], 'close']
            df.loc[df.index[i], 'high'] = max(df.loc[df.index[i], 'open'], df.loc[df.index[i], 'close']) * (1 + random.uniform(0.001, 0.006))
            df.loc[df.index[i], 'low'] = min(df.loc[df.index[i], 'open'], df.loc[df.index[i], 'close']) * (1 - random.uniform(0.001, 0.006))
        
        # Điều chỉnh volume dựa trên biến động giá
        price_changes = np.abs(df['close'].pct_change().fillna(0))
        volume_factor = 1 + price_changes * 10
        df['volume'] = (df['volume'] * volume_factor).astype(int)
        
        return df
    
    def test_sideways_detection(self) -> Dict:
        """
        Kiểm tra phát hiện thị trường sideway với các điều kiện khắc nghiệt
        
        Returns:
            Dict: Kết quả kiểm tra
        """
        logger.info("Bắt đầu kiểm tra phát hiện thị trường sideway")
        
        test_results = {
            "name": "Kiểm tra phát hiện thị trường sideway",
            "scenarios": {},
            "success": True,
            "errors": []
        }
        
        try:
            # Khởi tạo SidewaysMarketOptimizer
            self.sideways_optimizer = SidewaysMarketOptimizer()
            
            # Các kịch bản kiểm tra
            scenarios = [
                "normal", 
                "flash_crash", 
                "price_spike", 
                "sideways_squeeze", 
                "high_volatility", 
                "low_liquidity"
            ]
            
            # Thực hiện kiểm tra với từng kịch bản
            for scenario in scenarios:
                logger.info(f"Kiểm tra kịch bản: {scenario}")
                
                # Tạo dữ liệu thị trường
                df = self.generate_extreme_market_data(scenario)
                
                # Phát hiện thị trường sideway
                try:
                    is_sideway = self.sideways_optimizer.detect_sideways_market(df)
                    score = self.sideways_optimizer.sideways_score
                    
                    # Kiểm tra tính hợp lý của kết quả
                    expected_sideway = scenario == "sideways_squeeze"
                    result_matches = (is_sideway == expected_sideway)
                    
                    # Lưu kết quả
                    test_results["scenarios"][scenario] = {
                        "is_sideway": is_sideway,
                        "score": score,
                        "expected_sideway": expected_sideway,
                        "result_matches": result_matches,
                        "status": "passed" if result_matches else "warning"
                    }
                    
                    if not result_matches:
                        logger.warning(f"Kết quả không khớp với kỳ vọng cho kịch bản {scenario}")
                        logger.warning(f"  - Kỳ vọng: {expected_sideway}, Thực tế: {is_sideway}, Score: {score}")
                    
                    # Tạo biểu đồ nếu là sideway hoặc kết quả không khớp
                    if is_sideway or not result_matches:
                        chart_path = self.sideways_optimizer.visualize_sideways_detection(
                            df, f"TEST_{scenario}", custom_path='stress_test_results'
                        )
                        test_results["scenarios"][scenario]["chart_path"] = chart_path
                        
                except Exception as e:
                    error_msg = f"Lỗi khi phát hiện sideway cho kịch bản {scenario}: {str(e)}"
                    logger.error(error_msg)
                    logger.error(traceback.format_exc())
                    
                    test_results["scenarios"][scenario] = {
                        "status": "failed",
                        "error": str(e)
                    }
                    test_results["success"] = False
                    test_results["errors"].append(error_msg)
            
            # Đánh giá tổng thể
            failed_scenarios = [s for s, data in test_results["scenarios"].items() 
                              if data.get("status") == "failed"]
            
            if failed_scenarios:
                test_results["status"] = "failed"
                test_results["message"] = f"Kiểm tra thất bại cho {len(failed_scenarios)} kịch bản: {', '.join(failed_scenarios)}"
            else:
                mismatches = [s for s, data in test_results["scenarios"].items() 
                            if data.get("status") == "warning"]
                
                if mismatches:
                    test_results["status"] = "warning"
                    test_results["message"] = f"Phát hiện không chính xác cho {len(mismatches)} kịch bản: {', '.join(mismatches)}"
                else:
                    test_results["status"] = "passed"
                    test_results["message"] = "Phát hiện thị trường sideway hoạt động chính xác trên tất cả kịch bản"
            
        except Exception as e:
            error_msg = f"Lỗi không mong đợi khi kiểm tra phát hiện sideway: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            test_results["status"] = "error"
            test_results["message"] = error_msg
            test_results["success"] = False
            test_results["errors"].append(error_msg)
        
        # Lưu kết quả
        self.test_results["sideways_detection"] = test_results
        logger.info(f"Kết thúc kiểm tra phát hiện thị trường sideway: {test_results['status']}")
        
        return test_results
    
    def test_trailing_stop_extreme(self) -> Dict:
        """
        Kiểm tra trailing stop trong điều kiện thị trường cực đoan
        
        Returns:
            Dict: Kết quả kiểm tra
        """
        logger.info("Bắt đầu kiểm tra trailing stop trong điều kiện cực đoan")
        
        test_results = {
            "name": "Kiểm tra trailing stop trong điều kiện cực đoan",
            "scenarios": {},
            "success": True,
            "errors": []
        }
        
        try:
            # Khởi tạo EnhancedTrailingStopManager với mock API
            self.trailing_manager = EnhancedTrailingStopManager(api_client=self.mock_api)
            
            # Các kịch bản kiểm tra
            scenarios = {
                "flash_crash": {"direction": "long", "entry_price": 50000},
                "price_spike": {"direction": "short", "entry_price": 50000},
                "high_volatility": {"direction": "long", "entry_price": 50000}
            }
            
            # Thực hiện kiểm tra với từng kịch bản
            for scenario, config in scenarios.items():
                logger.info(f"Kiểm tra kịch bản: {scenario}")
                
                # Tạo dữ liệu thị trường
                df = self.generate_extreme_market_data(scenario)
                
                # Các biến theo dõi
                initial_profit = 0
                max_profit = 0
                final_profit = 0
                is_closed = False
                saved_profit = 0
                tracking_id = None
                
                try:
                    # Đăng ký vị thế
                    symbol = f"TEST_{scenario}"
                    entry_price = config["entry_price"]
                    direction = config["direction"]
                    
                    tracking_id = self.trailing_manager.register_position(
                        symbol=symbol,
                        order_id="test_order_" + str(int(time.time())),
                        entry_price=entry_price,
                        position_size=1.0,
                        direction=direction,
                        stop_loss_price=entry_price * (0.95 if direction == "long" else 1.05)
                    )
                    
                    # Cập nhật giá theo dữ liệu
                    for idx, row in df.iterrows():
                        current_price = row['close']
                        
                        # Cập nhật giá
                        self.trailing_manager.update_price(symbol, current_price)
                        
                        # Kiểm tra vị thế
                        position = self.trailing_manager.get_position_info(tracking_id)
                        
                        # Nếu vị thế đã đóng, dừng vòng lặp
                        if position is None:
                            is_closed = True
                            break
                        
                        # Tính % lợi nhuận
                        if direction == "long":
                            profit_pct = (current_price - entry_price) / entry_price * 100
                        else:  # short
                            profit_pct = (entry_price - current_price) / entry_price * 100
                        
                        # Cập nhật lợi nhuận tối đa
                        if profit_pct > max_profit:
                            max_profit = profit_pct
                        
                        # Lấy lợi nhuận cuối cùng nếu vẫn còn vị thế
                        final_profit = profit_pct
                    
                    # Nếu vị thế vẫn mở, đóng thủ công
                    if not is_closed:
                        position = self.trailing_manager.get_position_info(tracking_id)
                        if position:
                            self.trailing_manager.manual_close_position(tracking_id, "test_end")
                    
                    # Tính lợi nhuận đã bảo toàn
                    saved_profit = max_profit - final_profit if max_profit > final_profit else 0
                    
                    # Đánh giá hiệu suất trailing stop
                    effectiveness = "poor"
                    if max_profit > 2.0:  # Nếu có lợi nhuận đáng kể
                        if saved_profit > max_profit * 0.5:
                            effectiveness = "excellent"  # Bảo toàn >50% lợi nhuận cao nhất
                        elif saved_profit > max_profit * 0.3:
                            effectiveness = "good"  # Bảo toàn >30% lợi nhuận cao nhất
                        elif saved_profit > max_profit * 0.1:
                            effectiveness = "fair"  # Bảo toàn >10% lợi nhuận cao nhất
                    
                    # Lưu kết quả
                    test_results["scenarios"][scenario] = {
                        "tracking_id": tracking_id,
                        "direction": direction,
                        "max_profit": max_profit,
                        "final_profit": final_profit,
                        "saved_profit": saved_profit,
                        "is_closed": is_closed,
                        "effectiveness": effectiveness,
                        "status": "passed"
                    }
                    
                    logger.info(f"Kết quả kịch bản {scenario}:")
                    logger.info(f"  - Lợi nhuận tối đa: {max_profit:.2f}%")
                    logger.info(f"  - Lợi nhuận cuối: {final_profit:.2f}%")
                    logger.info(f"  - Lợi nhuận đã bảo toàn: {saved_profit:.2f}%")
                    logger.info(f"  - Hiệu quả: {effectiveness}")
                    
                except Exception as e:
                    error_msg = f"Lỗi khi kiểm tra trailing stop cho kịch bản {scenario}: {str(e)}"
                    logger.error(error_msg)
                    logger.error(traceback.format_exc())
                    
                    test_results["scenarios"][scenario] = {
                        "status": "failed",
                        "error": str(e)
                    }
                    test_results["success"] = False
                    test_results["errors"].append(error_msg)
            
            # Đánh giá tổng thể
            failed_scenarios = [s for s, data in test_results["scenarios"].items() 
                              if data.get("status") == "failed"]
            
            if failed_scenarios:
                test_results["status"] = "failed"
                test_results["message"] = f"Kiểm tra thất bại cho {len(failed_scenarios)} kịch bản: {', '.join(failed_scenarios)}"
            else:
                # Đánh giá hiệu quả tổng thể
                effectiveness_counts = {}
                for s, data in test_results["scenarios"].items():
                    eff = data.get("effectiveness")
                    if eff:
                        effectiveness_counts[eff] = effectiveness_counts.get(eff, 0) + 1
                
                if effectiveness_counts.get("poor", 0) > len(scenarios) / 2:
                    test_results["status"] = "warning"
                    test_results["message"] = "Hiệu quả trailing stop kém trong phần lớn kịch bản"
                else:
                    test_results["status"] = "passed"
                    test_results["message"] = "Trailing stop hoạt động ổn định trên tất cả kịch bản"
                    
                test_results["effectiveness_summary"] = effectiveness_counts
            
        except Exception as e:
            error_msg = f"Lỗi không mong đợi khi kiểm tra trailing stop: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            test_results["status"] = "error"
            test_results["message"] = error_msg
            test_results["success"] = False
            test_results["errors"].append(error_msg)
        
        # Lưu kết quả
        self.test_results["trailing_stop_extreme"] = test_results
        logger.info(f"Kết thúc kiểm tra trailing stop: {test_results['status']}")
        
        return test_results
    
    def test_api_failure_handling(self) -> Dict:
        """
        Kiểm tra khả năng xử lý lỗi API
        
        Returns:
            Dict: Kết quả kiểm tra
        """
        logger.info("Bắt đầu kiểm tra khả năng xử lý lỗi API")
        
        test_results = {
            "name": "Kiểm tra khả năng xử lý lỗi API",
            "tests": {},
            "success": True,
            "errors": []
        }
        
        try:
            # Khởi tạo trailing manager với mock API
            self.mock_api.set_failure_rate(0.0)  # Bắt đầu với không có lỗi
            self.trailing_manager = EnhancedTrailingStopManager(api_client=self.mock_api)
            
            # Kiểm tra đăng ký vị thế với API hoạt động bình thường
            try:
                tracking_id = self.trailing_manager.register_position(
                    symbol="TEST_API",
                    order_id="normal_test_" + str(int(time.time())),
                    entry_price=50000,
                    position_size=1.0,
                    direction="long",
                    stop_loss_price=48000
                )
                
                test_results["tests"]["normal_registration"] = {
                    "tracking_id": tracking_id,
                    "status": "passed"
                }
                
                logger.info("Đăng ký vị thế bình thường: Thành công")
                
            except Exception as e:
                error_msg = f"Lỗi khi đăng ký vị thế bình thường: {str(e)}"
                logger.error(error_msg)
                
                test_results["tests"]["normal_registration"] = {
                    "status": "failed",
                    "error": str(e)
                }
                test_results["success"] = False
                test_results["errors"].append(error_msg)
            
            # Kiểm tra với tỷ lệ lỗi API cao
            self.mock_api.set_failure_rate(0.8)  # 80% tỷ lệ lỗi
            
            try:
                # Thử đăng ký và cập nhật nhiều lần
                error_count = 0
                success_count = 0
                
                for i in range(10):
                    try:
                        tracking_id = self.trailing_manager.register_position(
                            symbol=f"TEST_FAIL_{i}",
                            order_id=f"fail_test_{i}_{int(time.time())}",
                            entry_price=50000,
                            position_size=1.0,
                            direction="long",
                            stop_loss_price=48000
                        )
                        
                        # Nếu đăng ký thành công, thử cập nhật giá
                        self.trailing_manager.update_price(f"TEST_FAIL_{i}", 51000)
                        success_count += 1
                        
                    except Exception:
                        error_count += 1
                
                test_results["tests"]["high_failure_rate"] = {
                    "attempts": 10,
                    "errors": error_count,
                    "successes": success_count,
                    "status": "failed" if success_count == 0 else "warning" if error_count > 0 else "passed"
                }
                
                logger.info(f"Kiểm tra với tỷ lệ lỗi cao: {success_count} thành công, {error_count} lỗi")
                
                if success_count == 0:
                    test_results["success"] = False
                    test_results["errors"].append("Không thể xử lý khi tỷ lệ lỗi API cao")
                
            except Exception as e:
                error_msg = f"Lỗi không mong đợi khi kiểm tra với tỷ lệ lỗi cao: {str(e)}"
                logger.error(error_msg)
                
                test_results["tests"]["high_failure_rate"] = {
                    "status": "failed",
                    "error": str(e)
                }
                test_results["success"] = False
                test_results["errors"].append(error_msg)
            
            # Kiểm tra với API phản hồi chậm
            self.mock_api.set_failure_rate(0.0)  # Đặt lại tỷ lệ lỗi
            self.mock_api.set_slow_response(True, 2.0)  # 2 giây trễ
            
            try:
                start_time = time.time()
                
                tracking_id = self.trailing_manager.register_position(
                    symbol="TEST_SLOW",
                    order_id="slow_test_" + str(int(time.time())),
                    entry_price=50000,
                    position_size=1.0,
                    direction="long",
                    stop_loss_price=48000
                )
                
                elapsed_time = time.time() - start_time
                
                test_results["tests"]["slow_response"] = {
                    "tracking_id": tracking_id,
                    "elapsed_time": elapsed_time,
                    "status": "passed" if elapsed_time > 1.0 else "warning"
                }
                
                logger.info(f"Kiểm tra với API phản hồi chậm: {elapsed_time:.2f} giây")
                
            except Exception as e:
                error_msg = f"Lỗi khi kiểm tra với API phản hồi chậm: {str(e)}"
                logger.error(error_msg)
                
                test_results["tests"]["slow_response"] = {
                    "status": "failed",
                    "error": str(e)
                }
                test_results["success"] = False
                test_results["errors"].append(error_msg)
            
            # Đặt lại cài đặt
            self.mock_api.set_slow_response(False)
            
            # Đánh giá tổng thể
            failed_tests = [t for t, data in test_results["tests"].items() 
                          if data.get("status") == "failed"]
            
            if failed_tests:
                test_results["status"] = "failed"
                test_results["message"] = f"Kiểm tra thất bại cho {len(failed_tests)} bài test: {', '.join(failed_tests)}"
            else:
                warning_tests = [t for t, data in test_results["tests"].items() 
                               if data.get("status") == "warning"]
                
                if warning_tests:
                    test_results["status"] = "warning"
                    test_results["message"] = f"Cảnh báo cho {len(warning_tests)} bài test: {', '.join(warning_tests)}"
                else:
                    test_results["status"] = "passed"
                    test_results["message"] = "Xử lý lỗi API hoạt động chính xác trên tất cả bài test"
            
        except Exception as e:
            error_msg = f"Lỗi không mong đợi khi kiểm tra khả năng xử lý lỗi API: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            test_results["status"] = "error"
            test_results["message"] = error_msg
            test_results["success"] = False
            test_results["errors"].append(error_msg)
        
        # Lưu kết quả
        self.test_results["api_failure_handling"] = test_results
        logger.info(f"Kết thúc kiểm tra khả năng xử lý lỗi API: {test_results['status']}")
        
        return test_results
    
    def test_memory_usage(self) -> Dict:
        """
        Kiểm tra sử dụng bộ nhớ khi chạy trong thời gian dài
        
        Returns:
            Dict: Kết quả kiểm tra
        """
        logger.info("Bắt đầu kiểm tra sử dụng bộ nhớ")
        
        test_results = {
            "name": "Kiểm tra sử dụng bộ nhớ",
            "memory_usage": {},
            "success": True,
            "errors": []
        }
        
        try:
            import resource
            import gc
            
            # Khởi tạo các module
            self.sideways_optimizer = SidewaysMarketOptimizer()
            self.trailing_manager = EnhancedTrailingStopManager(api_client=self.mock_api)
            
            # Đo sử dụng bộ nhớ ban đầu
            gc.collect()
            initial_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            
            # Tạo nhiều vị thế và cập nhật nhiều lần
            position_count = 100
            update_count = 100
            
            start_time = time.time()
            tracking_ids = []
            
            # Tạo các vị thế
            for i in range(position_count):
                tracking_id = self.trailing_manager.register_position(
                    symbol=f"TEST_MEM_{i}",
                    order_id=f"mem_test_{i}_{int(time.time())}",
                    entry_price=50000,
                    position_size=1.0,
                    direction="long",
                    stop_loss_price=48000
                )
                tracking_ids.append(tracking_id)
            
            # Đo bộ nhớ sau khi tạo vị thế
            gc.collect()
            memory_after_creation = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            
            # Cập nhật giá nhiều lần
            for _ in range(update_count):
                for i in range(position_count):
                    symbol = f"TEST_MEM_{i}"
                    price = 50000 + random.uniform(-1000, 2000)
                    self.trailing_manager.update_price(symbol, price)
            
            # Đo bộ nhớ sau khi cập nhật
            gc.collect()
            memory_after_updates = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            
            # Đóng một nửa vị thế
            for i in range(position_count // 2):
                if i < len(tracking_ids):
                    self.trailing_manager.manual_close_position(tracking_ids[i], "test_close")
            
            # Đo bộ nhớ sau khi đóng một nửa vị thế
            gc.collect()
            memory_after_closing = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            
            # Tính tỷ lệ tăng bộ nhớ
            creation_increase = (memory_after_creation - initial_memory) / initial_memory * 100
            updates_increase = (memory_after_updates - memory_after_creation) / memory_after_creation * 100
            closing_change = (memory_after_closing - memory_after_updates) / memory_after_updates * 100
            
            elapsed_time = time.time() - start_time
            
            # Lưu kết quả
            test_results["memory_usage"] = {
                "initial_memory_kb": initial_memory,
                "after_creation_kb": memory_after_creation,
                "after_updates_kb": memory_after_updates,
                "after_closing_kb": memory_after_closing,
                "creation_increase_percent": creation_increase,
                "updates_increase_percent": updates_increase,
                "closing_change_percent": closing_change,
                "position_count": position_count,
                "update_count": update_count,
                "elapsed_time": elapsed_time
            }
            
            logger.info(f"Sử dụng bộ nhớ ban đầu: {initial_memory} KB")
            logger.info(f"Sau khi tạo {position_count} vị thế: {memory_after_creation} KB (+{creation_increase:.2f}%)")
            logger.info(f"Sau khi cập nhật {update_count} lần: {memory_after_updates} KB (+{updates_increase:.2f}%)")
            logger.info(f"Sau khi đóng một nửa vị thế: {memory_after_closing} KB ({closing_change:.2f}%)")
            
            # Đánh giá tổng thể
            # Phát hiện rò rỉ bộ nhớ nếu tỷ lệ tăng quá lớn sau cập nhật
            memory_leak = False
            
            if updates_increase > 50.0:  # Tăng >50% sau khi cập nhật
                memory_leak = True
                warning_msg = f"Có thể có rò rỉ bộ nhớ: tăng {updates_increase:.2f}% sau {update_count} lần cập nhật"
                logger.warning(warning_msg)
                test_results["memory_leak_warning"] = warning_msg
            
            # Phát hiện không giải phóng bộ nhớ nếu bộ nhớ không giảm sau khi đóng vị thế
            if closing_change > 0:  # Tăng thay vì giảm
                memory_leak = True
                warning_msg = f"Có thể không giải phóng bộ nhớ: tăng {closing_change:.2f}% sau khi đóng một nửa vị thế"
                logger.warning(warning_msg)
                test_results["memory_release_warning"] = warning_msg
            
            if memory_leak:
                test_results["status"] = "warning"
                test_results["message"] = "Phát hiện vấn đề tiềm ẩn về quản lý bộ nhớ"
            else:
                test_results["status"] = "passed"
                test_results["message"] = "Quản lý bộ nhớ hoạt động tốt"
            
        except Exception as e:
            error_msg = f"Lỗi khi kiểm tra sử dụng bộ nhớ: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            test_results["status"] = "error"
            test_results["message"] = error_msg
            test_results["success"] = False
            test_results["errors"].append(error_msg)
        
        # Lưu kết quả
        self.test_results["memory_usage"] = test_results
        logger.info(f"Kết thúc kiểm tra sử dụng bộ nhớ: {test_results['status']}")
        
        return test_results
    
    def test_multithreading_safety(self) -> Dict:
        """
        Kiểm tra an toàn đa luồng
        
        Returns:
            Dict: Kết quả kiểm tra
        """
        logger.info("Bắt đầu kiểm tra an toàn đa luồng")
        
        test_results = {
            "name": "Kiểm tra an toàn đa luồng",
            "thread_safety": {},
            "success": True,
            "errors": []
        }
        
        try:
            import threading
            
            # Khởi tạo trailing manager
            self.trailing_manager = EnhancedTrailingStopManager(api_client=self.mock_api)
            
            # Tạo một vị thế để kiểm tra
            base_tracking_id = self.trailing_manager.register_position(
                symbol="TEST_THREAD",
                order_id="thread_test_" + str(int(time.time())),
                entry_price=50000,
                position_size=1.0,
                direction="long",
                stop_loss_price=48000
            )
            
            # Số luồng và số lần cập nhật
            thread_count = 10
            updates_per_thread = 50
            
            # Biến theo dõi lỗi
            errors = []
            position_inconsistency = False
            
            # Khóa đồng bộ
            error_lock = threading.Lock()
            
            def update_prices():
                """Cập nhật giá trong một luồng riêng"""
                for _ in range(updates_per_thread):
                    try:
                        # Cập nhật giá ngẫu nhiên
                        price = 50000 + random.uniform(-1000, 3000)
                        self.trailing_manager.update_price("TEST_THREAD", price)
                        
                        # Lấy thông tin vị thế
                        position = self.trailing_manager.get_position_info(base_tracking_id)
                        
                        # Kiểm tra tính nhất quán
                        if position is None:
                            with error_lock:
                                nonlocal position_inconsistency
                                position_inconsistency = True
                                errors.append("Vị thế đã biến mất trong khi đang cập nhật")
                            break
                        
                        # Ngủ một chút để tăng khả năng xung đột
                        time.sleep(random.uniform(0.001, 0.01))
                        
                    except Exception as e:
                        with error_lock:
                            errors.append(f"Lỗi trong luồng con: {str(e)}")
            
            # Tạo và khởi động các luồng
            threads = []
            for i in range(thread_count):
                thread = threading.Thread(target=update_prices, name=f"UpdateThread-{i}")
                threads.append(thread)
                thread.start()
            
            # Chờ tất cả các luồng hoàn thành
            for thread in threads:
                thread.join()
            
            # Kiểm tra kết quả
            if errors:
                test_results["thread_safety"]["errors"] = errors
                test_results["status"] = "failed"
                test_results["message"] = f"Phát hiện {len(errors)} lỗi khi kiểm tra an toàn đa luồng"
                test_results["success"] = False
                test_results["errors"].extend(errors)
                
                logger.error(f"Phát hiện lỗi an toàn đa luồng: {errors[:5]}...")
            else:
                # Kiểm tra xem vị thế còn tồn tại không
                position = self.trailing_manager.get_position_info(base_tracking_id)
                position_exists = position is not None
                
                test_results["thread_safety"] = {
                    "thread_count": thread_count,
                    "updates_per_thread": updates_per_thread,
                    "position_exists": position_exists,
                    "position_inconsistency": position_inconsistency
                }
                
                if position_inconsistency:
                    test_results["status"] = "failed"
                    test_results["message"] = "Phát hiện tính không nhất quán của vị thế"
                    test_results["success"] = False
                else:
                    test_results["status"] = "passed"
                    test_results["message"] = "Không phát hiện vấn đề an toàn đa luồng"
            
            logger.info(f"Kết quả kiểm tra an toàn đa luồng: {test_results['status']}")
            
        except Exception as e:
            error_msg = f"Lỗi không mong đợi khi kiểm tra an toàn đa luồng: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            test_results["status"] = "error"
            test_results["message"] = error_msg
            test_results["success"] = False
            test_results["errors"].append(error_msg)
        
        # Lưu kết quả
        self.test_results["multithreading_safety"] = test_results
        logger.info(f"Kết thúc kiểm tra an toàn đa luồng: {test_results['status']}")
        
        return test_results
    
    def run_all_tests(self):
        """
        Chạy tất cả các bài kiểm tra
        """
        logger.info("===== Bắt đầu tất cả bài kiểm tra =====")
        
        # Thời gian bắt đầu
        start_time = time.time()
        
        # Kiểm tra phát hiện thị trường sideway
        self.test_sideways_detection()
        
        # Kiểm tra trailing stop trong điều kiện cực đoan
        self.test_trailing_stop_extreme()
        
        # Kiểm tra xử lý lỗi API
        self.test_api_failure_handling()
        
        # Kiểm tra sử dụng bộ nhớ
        try:
            self.test_memory_usage()
        except ImportError:
            logger.warning("Không thể kiểm tra sử dụng bộ nhớ (thiếu module resource)")
        
        # Kiểm tra an toàn đa luồng
        self.test_multithreading_safety()
        
        # Thời gian kết thúc
        elapsed_time = time.time() - start_time
        
        # Tổng hợp kết quả
        summary = {
            "total_tests": len(self.test_results),
            "passed": sum(1 for t in self.test_results.values() if t.get("status") == "passed"),
            "warning": sum(1 for t in self.test_results.values() if t.get("status") == "warning"),
            "failed": sum(1 for t in self.test_results.values() if t.get("status") == "failed"),
            "error": sum(1 for t in self.test_results.values() if t.get("status") == "error"),
            "elapsed_time": elapsed_time
        }
        
        self.test_results["summary"] = summary
        
        # Lưu kết quả vào file
        result_path = os.path.join('stress_test_results', f'stress_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        
        with open(result_path, 'w') as f:
            json.dump(self.test_results, f, indent=4)
        
        logger.info(f"===== Tất cả bài kiểm tra hoàn thành trong {elapsed_time:.2f} giây =====")
        logger.info(f"Tổng hợp: {summary['passed']} pass, {summary['warning']} warning, {summary['failed']} fail, {summary['error']} error")
        logger.info(f"Kết quả chi tiết đã được lưu vào {result_path}")
        
        # Hiển thị tổng quan
        self._print_test_summary()
        
        return self.test_results
    
    def _print_test_summary(self):
        """In tổng quan kết quả kiểm tra"""
        print("\n===== TỔNG QUAN KẾT QUẢ KIỂM TRA =====")
        
        for test_name, results in self.test_results.items():
            if test_name == "summary":
                continue
                
            status = results.get("status", "unknown")
            message = results.get("message", "")
            
            # Định dạng trạng thái
            if status == "passed":
                status_str = "\033[92mPASSED\033[0m"  # Xanh lá
            elif status == "warning":
                status_str = "\033[93mWARNING\033[0m"  # Vàng
            elif status == "failed":
                status_str = "\033[91mFAILED\033[0m"  # Đỏ
            elif status == "error":
                status_str = "\033[91mERROR\033[0m"  # Đỏ
            else:
                status_str = status
            
            print(f"{test_name}: {status_str}")
            if message:
                print(f"  - {message}")
        
        # In tổng hợp
        if "summary" in self.test_results:
            summary = self.test_results["summary"]
            print("\nTổng hợp:")
            print(f"- Tổng số bài kiểm tra: {summary['total_tests']}")
            print(f"- Passed: {summary['passed']}")
            print(f"- Warning: {summary['warning']}")
            print(f"- Failed: {summary['failed']}")
            print(f"- Error: {summary['error']}")
            print(f"- Thời gian chạy: {summary['elapsed_time']:.2f} giây")

# Chạy kiểm tra nếu được thực thi trực tiếp
if __name__ == "__main__":
    print("===== BẮT ĐẦU KIỂM TRA KHẮC NGHIỆT HỆ THỐNG GIAO DỊCH =====")
    print("(Kiểm tra này có thể mất vài phút để hoàn thành)")
    
    try:
        # Tạo và chạy bộ kiểm tra
        tester = StressTestRunner()
        tester.run_all_tests()
        
        print("\n===== KIỂM TRA HOÀN THÀNH =====")
        print("Kiểm tra chi tiết các file log để xem thông tin thêm.")
        
    except Exception as e:
        print(f"\nLỗi không mong đợi trong quá trình kiểm tra: {str(e)}")
        traceback.print_exc()
        print("\nKiểm tra không hoàn thành do lỗi. Xem logs để biết chi tiết.")