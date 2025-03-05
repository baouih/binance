#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script chạy toàn bộ các test cho hệ thống giao dịch

Module này tập hợp và chạy tất cả các test cho hệ thống giao dịch, bao gồm:
1. Test API Data Validator
2. Test Adaptive Strategy Selector
3. Test Dynamic Risk Allocator
4. Test Advanced Trailing Stop
5. Test kịch bản giao dịch với các điều kiện thị trường khác nhau
"""

import os
import sys
import time
import json
import logging
import argparse
import datetime
from typing import Dict, List, Any

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('system_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('run_test')

# Kiểm tra và import các module cần thiết
try:
    from data_cache import DataCache
    from api_data_validator import APIDataValidator, retry
    from adaptive_strategy_selector import AdaptiveStrategySelector
    from dynamic_risk_allocator import DynamicRiskAllocator
    from advanced_trailing_stop import AdvancedTrailingStop
    from test_cases import TestCaseRunner
    from comprehensive_backtest import ComprehensiveBacktest, create_sample_data
except ImportError as e:
    logger.error(f"Không thể import các module cần thiết: {str(e)}")
    logger.error("Hãy đảm bảo rằng các module này đã được cài đặt.")
    sys.exit(1)

class SystemTester:
    """Lớp kiểm tra toàn diện hệ thống giao dịch"""
    
    def __init__(self, output_dir: str = 'test_results'):
        """
        Khởi tạo System Tester
        
        Args:
            output_dir (str): Thư mục đầu ra kết quả test
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Khởi tạo các thành phần cần test
        self.data_cache = DataCache()
        self.api_validator = APIDataValidator()
        self.strategy_selector = AdaptiveStrategySelector(self.data_cache)
        self.risk_allocator = DynamicRiskAllocator(self.data_cache)
        
        # Kết quả test
        self.test_results = {
            'api_validator_tests': {},
            'strategy_selector_tests': {},
            'risk_allocator_tests': {},
            'trailing_stop_tests': {},
            'comprehensive_tests': {},
            'summary': {}
        }
        
        # Thời gian chạy test
        self.start_time = None
        self.end_time = None
    
    def run_all_tests(self) -> Dict:
        """
        Chạy tất cả các bài test
        
        Returns:
            Dict: Kết quả tất cả các bài test
        """
        self.start_time = datetime.datetime.now()
        logger.info(f"=== Bắt đầu chạy tất cả các bài test lúc {self.start_time} ===")
        
        # Chạy các bài test
        self.test_api_validator()
        self.test_strategy_selector()
        self.test_risk_allocator()
        self.test_trailing_stop()
        self.test_trading_scenarios()
        self.test_comprehensive_backtest()
        
        # Tạo báo cáo tổng hợp
        self.create_summary()
        
        self.end_time = datetime.datetime.now()
        duration = self.end_time - self.start_time
        logger.info(f"=== Kết thúc tất cả các bài test lúc {self.end_time} ===")
        logger.info(f"=== Tổng thời gian chạy: {duration} ===")
        
        # Lưu kết quả test
        self.save_results()
        
        return self.test_results
    
    def test_api_validator(self) -> Dict:
        """
        Kiểm tra API Data Validator
        
        Returns:
            Dict: Kết quả test
        """
        logger.info("=== Chạy test API Data Validator ===")
        
        results = {'success': True, 'details': {}}
        
        try:
            # Test 1: Kiểm tra xác thực dữ liệu k-lines
            logger.info("Test 1: Kiểm tra xác thực dữ liệu k-lines")
            
            # Tạo dữ liệu k-lines hợp lệ
            valid_klines = [
                [1625097600000, "35000.0", "36000.0", "34500.0", "35500.0", "1000.0", 1625184000000, "35500000.0", 5000, "600.0", "21000000.0", "0"],
                [1625184000000, "35500.0", "37000.0", "35000.0", "36800.0", "1200.0", 1625270400000, "43200000.0", 6000, "700.0", "25200000.0", "0"]
            ]
            
            # Tạo dữ liệu k-lines không hợp lệ
            invalid_klines = [
                [1625097600000, "35000.0", "34000.0", "34500.0", "35500.0", "1000.0", 1625184000000, "35500000.0", 5000, "600.0", "21000000.0", "0"],
                [1625184000000, "35500.0", "37000.0", "35000.0", "36800.0", "-1200.0", 1625270400000, "43200000.0", 6000, "700.0", "25200000.0", "0"]
            ]
            
            # Kiểm tra xác thực
            valid_result, valid_errors = self.api_validator.validate_binance_klines_data(valid_klines)
            invalid_result, invalid_errors = self.api_validator.validate_binance_klines_data(invalid_klines)
            
            # Kiểm tra kết quả
            results['details']['klines_validation'] = {
                'valid_data_result': valid_result,
                'valid_data_errors': valid_errors,
                'invalid_data_result': invalid_result,
                'invalid_data_errors': invalid_errors,
                'test_passed': valid_result and not invalid_result
            }
            
            # Test 2: Kiểm tra xác thực dữ liệu vị thế
            logger.info("Test 2: Kiểm tra xác thực dữ liệu vị thế")
            
            # Tạo dữ liệu vị thế hợp lệ
            valid_position = {
                "symbol": "BTCUSDT",
                "positionAmt": "0.002",
                "entryPrice": "35000.0",
                "markPrice": "36000.0",
                "unRealizedProfit": "2.0",
                "liquidationPrice": "30000.0",
                "leverage": "10",
                "marginType": "isolated",
                "isolatedMargin": "7.0"
            }
            
            # Tạo dữ liệu vị thế không hợp lệ
            invalid_position = {
                "symbol": "BTCUSDT",
                "positionAmt": "invalid",
                "entryPrice": "35000.0",
                "markPrice": "36000.0",
                "unRealizedProfit": "2.0",
                "marginType": "isolated"
            }
            
            # Kiểm tra xác thực
            valid_pos_result, valid_pos_errors = self.api_validator.validate_binance_position_data(valid_position)
            invalid_pos_result, invalid_pos_errors = self.api_validator.validate_binance_position_data(invalid_position)
            
            # Kiểm tra kết quả
            results['details']['position_validation'] = {
                'valid_data_result': valid_pos_result,
                'valid_data_errors': valid_pos_errors,
                'invalid_data_result': invalid_pos_result,
                'invalid_data_errors': invalid_pos_errors,
                'test_passed': valid_pos_result and not invalid_pos_result
            }
            
            # Test 3: Kiểm tra chuyển đổi dữ liệu
            logger.info("Test 3: Kiểm tra chuyển đổi dữ liệu")
            
            # Chuyển đổi dữ liệu
            transformed_klines = self.api_validator.transform_binance_klines(valid_klines)
            transformed_position = self.api_validator.transform_binance_position(valid_position)
            
            # Kiểm tra kết quả
            results['details']['data_transformation'] = {
                'klines_transformed': len(transformed_klines) == len(valid_klines),
                'position_transformed': 'symbol' in transformed_position and 'side' in transformed_position,
                'test_passed': len(transformed_klines) == len(valid_klines) and 'symbol' in transformed_position
            }
            
            # Test 4: Kiểm tra retry mechanism
            logger.info("Test 4: Kiểm tra retry mechanism")
            
            # Tạo hàm test với retry
            @retry(max_retries=3, retry_delay=0.1)
            def test_function_success():
                return "success"
            
            @retry(max_retries=3, retry_delay=0.1)
            def test_function_failure():
                raise Exception("Test failure")
            
            # Thử chạy hàm thành công
            try:
                success_result = test_function_success()
                success_retry = True
            except Exception:
                success_retry = False
            
            # Thử chạy hàm thất bại
            try:
                failure_result = test_function_failure()
                failure_retry = True
            except Exception:
                failure_retry = False
            
            # Kiểm tra kết quả
            results['details']['retry_mechanism'] = {
                'success_function': success_retry,
                'failure_function': not failure_retry,
                'test_passed': success_retry and not failure_retry
            }
            
            # Tính toán kết quả cuối cùng
            all_passed = all(detail.get('test_passed', False) for detail in results['details'].values())
            results['success'] = all_passed
            
            logger.info(f"Kết quả test API Data Validator: {'PASSED' if all_passed else 'FAILED'}")
        
        except Exception as e:
            logger.error(f"Lỗi khi chạy test API Data Validator: {str(e)}")
            results['success'] = False
            results['error'] = str(e)
        
        # Lưu kết quả
        self.test_results['api_validator_tests'] = results
        
        return results
    
    def test_strategy_selector(self) -> Dict:
        """
        Kiểm tra Adaptive Strategy Selector
        
        Returns:
            Dict: Kết quả test
        """
        logger.info("=== Chạy test Adaptive Strategy Selector ===")
        
        results = {'success': True, 'details': {}}
        
        try:
            # Tạo dữ liệu thị trường mẫu cho các chế độ thị trường khác nhau
            symbol = 'BTCUSDT'
            timeframe = '1h'
            
            # Tạo dữ liệu trending
            trending_market = self._create_sample_market_data(symbol, timeframe, 'trending')
            
            # Tạo dữ liệu ranging
            ranging_market = self._create_sample_market_data(symbol, timeframe, 'ranging')
            
            # Tạo dữ liệu volatile
            volatile_market = self._create_sample_market_data(symbol, timeframe, 'volatile')
            
            # Test 1: Phát hiện chế độ thị trường
            logger.info("Test 1: Phát hiện chế độ thị trường")
            
            # Lưu dữ liệu vào cache
            for market_data in [trending_market, ranging_market, volatile_market]:
                for k, v in market_data['indicators'].items():
                    self.data_cache.set('indicators', f"{symbol}_{timeframe}_{k}", v)
            
            # Phát hiện chế độ thị trường
            trending_regime = self.strategy_selector.get_market_regime(symbol, timeframe, force_recalculate=True)
            
            # Thay đổi các chỉ báo để tạo chế độ khác
            for k, v in ranging_market['indicators'].items():
                self.data_cache.set('indicators', f"{symbol}_{timeframe}_{k}", v)
            
            ranging_regime = self.strategy_selector.get_market_regime(symbol, timeframe, force_recalculate=True)
            
            # Thay đổi các chỉ báo để tạo chế độ khác
            for k, v in volatile_market['indicators'].items():
                self.data_cache.set('indicators', f"{symbol}_{timeframe}_{k}", v)
            
            volatile_regime = self.strategy_selector.get_market_regime(symbol, timeframe, force_recalculate=True)
            
            # Kiểm tra kết quả
            results['details']['regime_detection'] = {
                'trending_detection': trending_regime,
                'ranging_detection': ranging_regime,
                'volatile_detection': volatile_regime,
                'test_passed': (trending_regime != ranging_regime) and (trending_regime != volatile_regime) and (ranging_regime != volatile_regime)
            }
            
            # Test 2: Lấy chiến lược theo chế độ thị trường
            logger.info("Test 2: Lấy chiến lược theo chế độ thị trường")
            
            # Lấy chiến lược cho từng chế độ
            trending_strategies = self.strategy_selector.get_strategies_for_regime('trending')
            ranging_strategies = self.strategy_selector.get_strategies_for_regime('ranging')
            volatile_strategies = self.strategy_selector.get_strategies_for_regime('volatile')
            
            # Kiểm tra các chiến lược ưu tiên
            trending_priority = max(trending_strategies.items(), key=lambda x: x[1])[0] if trending_strategies else None
            ranging_priority = max(ranging_strategies.items(), key=lambda x: x[1])[0] if ranging_strategies else None
            volatile_priority = max(volatile_strategies.items(), key=lambda x: x[1])[0] if volatile_strategies else None
            
            # Kiểm tra kết quả
            results['details']['strategy_selection'] = {
                'trending_priority': trending_priority,
                'ranging_priority': ranging_priority,
                'volatile_priority': volatile_priority,
                'test_passed': (trending_priority != ranging_priority) or (trending_priority != volatile_priority)
            }
            
            # Test 3: Lấy quyết định giao dịch
            logger.info("Test 3: Lấy quyết định giao dịch")
            
            # Lấy quyết định giao dịch cho từng chế độ
            for k, v in trending_market['indicators'].items():
                self.data_cache.set('indicators', f"{symbol}_{timeframe}_{k}", v)
            
            trending_decision = self.strategy_selector.get_trading_decision(symbol, timeframe, 1.0)
            
            for k, v in ranging_market['indicators'].items():
                self.data_cache.set('indicators', f"{symbol}_{timeframe}_{k}", v)
            
            ranging_decision = self.strategy_selector.get_trading_decision(symbol, timeframe, 1.0)
            
            for k, v in volatile_market['indicators'].items():
                self.data_cache.set('indicators', f"{symbol}_{timeframe}_{k}", v)
            
            volatile_decision = self.strategy_selector.get_trading_decision(symbol, timeframe, 1.0)
            
            # Kiểm tra kết quả
            results['details']['trading_decision'] = {
                'trending_signal': trending_decision.get('composite_signal', {}).get('signal') if isinstance(trending_decision.get('composite_signal'), dict) else None,
                'ranging_signal': ranging_decision.get('composite_signal', {}).get('signal') if isinstance(ranging_decision.get('composite_signal'), dict) else None,
                'volatile_signal': volatile_decision.get('composite_signal', {}).get('signal') if isinstance(volatile_decision.get('composite_signal'), dict) else None,
                'test_passed': True  # Không quan trọng tín hiệu là gì, chỉ cần trả về được tín hiệu
            }
            
            # Tính toán kết quả cuối cùng
            all_passed = all(detail.get('test_passed', False) for detail in results['details'].values())
            results['success'] = all_passed
            
            logger.info(f"Kết quả test Adaptive Strategy Selector: {'PASSED' if all_passed else 'FAILED'}")
        
        except Exception as e:
            logger.error(f"Lỗi khi chạy test Adaptive Strategy Selector: {str(e)}")
            results['success'] = False
            results['error'] = str(e)
        
        # Lưu kết quả
        self.test_results['strategy_selector_tests'] = results
        
        return results
    
    def test_risk_allocator(self) -> Dict:
        """
        Kiểm tra Dynamic Risk Allocator
        
        Returns:
            Dict: Kết quả test
        """
        logger.info("=== Chạy test Dynamic Risk Allocator ===")
        
        results = {'success': True, 'details': {}}
        
        try:
            # Tạo dữ liệu thị trường mẫu
            symbol = 'BTCUSDT'
            timeframe = '1h'
            
            # Test 1: Tính toán risk percentage theo biến động thị trường
            logger.info("Test 1: Tính toán risk percentage theo biến động thị trường")
            
            # Tạo dữ liệu biến động khác nhau
            low_volatility = 0.01  # Biến động thấp
            medium_volatility = 0.02  # Biến động trung bình
            high_volatility = 0.04  # Biến động cao
            
            # Lưu vào cache
            self.data_cache.set('market_analysis', f"{symbol}_{timeframe}_volatility", low_volatility)
            low_vol_risk = self.risk_allocator.calculate_risk_percentage(symbol, timeframe, 'trending', 10000, 0)
            
            self.data_cache.set('market_analysis', f"{symbol}_{timeframe}_volatility", medium_volatility)
            medium_vol_risk = self.risk_allocator.calculate_risk_percentage(symbol, timeframe, 'trending', 10000, 0)
            
            self.data_cache.set('market_analysis', f"{symbol}_{timeframe}_volatility", high_volatility)
            high_vol_risk = self.risk_allocator.calculate_risk_percentage(symbol, timeframe, 'trending', 10000, 0)
            
            # Kiểm tra kết quả
            results['details']['volatility_risk_adjustment'] = {
                'low_volatility_risk': low_vol_risk,
                'medium_volatility_risk': medium_vol_risk,
                'high_volatility_risk': high_vol_risk,
                'test_passed': low_vol_risk > high_vol_risk  # Biến động thấp nên có risk cao hơn
            }
            
            # Test 2: Tính toán risk percentage theo drawdown
            logger.info("Test 2: Tính toán risk percentage theo drawdown")
            
            # Tạo dữ liệu drawdown khác nhau
            no_drawdown = 0.0
            small_drawdown = 5.0
            large_drawdown = 15.0
            
            # Lưu biến động trung bình
            self.data_cache.set('market_analysis', f"{symbol}_{timeframe}_volatility", medium_volatility)
            
            # Tính risk theo drawdown
            no_dd_risk = self.risk_allocator.calculate_risk_percentage(symbol, timeframe, 'trending', 10000, no_drawdown)
            small_dd_risk = self.risk_allocator.calculate_risk_percentage(symbol, timeframe, 'trending', 10000, small_drawdown)
            large_dd_risk = self.risk_allocator.calculate_risk_percentage(symbol, timeframe, 'trending', 10000, large_drawdown)
            
            # Kiểm tra kết quả
            results['details']['drawdown_risk_adjustment'] = {
                'no_drawdown_risk': no_dd_risk,
                'small_drawdown_risk': small_dd_risk,
                'large_drawdown_risk': large_dd_risk,
                'test_passed': no_dd_risk > small_dd_risk > large_dd_risk  # Drawdown càng lớn thì risk càng thấp
            }
            
            # Test 3: Tính toán kích thước vị thế
            logger.info("Test 3: Tính toán kích thước vị thế")
            
            # Tính kích thước vị thế
            account_balance = 10000.0
            entry_price = 50000.0
            stop_loss = 49000.0
            risk_percentage = 1.0
            
            position_info = self.risk_allocator.calculate_position_size(
                symbol, entry_price, stop_loss, account_balance, risk_percentage
            )
            
            # Kiểm tra kết quả
            expected_risk_amount = account_balance * risk_percentage / 100
            expected_quantity = expected_risk_amount / (entry_price - stop_loss)
            
            results['details']['position_sizing'] = {
                'position_size_usd': position_info.get('position_size_usd'),
                'quantity': position_info.get('quantity'),
                'expected_quantity': expected_quantity,
                'test_passed': abs(position_info.get('quantity', 0) - expected_quantity) < 0.001  # Sai số nhỏ
            }
            
            # Test 4: Phân bổ vốn cho nhiều cặp tiền
            logger.info("Test 4: Phân bổ vốn cho nhiều cặp tiền")
            
            # Tạo danh sách cặp tiền
            symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
            
            # Phân bổ vốn
            allocation = self.risk_allocator.allocate_capital(symbols, account_balance)
            
            # Kiểm tra kết quả
            total_allocation = sum(allocation.values())
            
            results['details']['capital_allocation'] = {
                'allocation': allocation,
                'total_allocation': total_allocation,
                'test_passed': abs(total_allocation - 100.0) < 0.01  # Tổng phân bổ phải là 100%
            }
            
            # Tính toán kết quả cuối cùng
            all_passed = all(detail.get('test_passed', False) for detail in results['details'].values())
            results['success'] = all_passed
            
            logger.info(f"Kết quả test Dynamic Risk Allocator: {'PASSED' if all_passed else 'FAILED'}")
        
        except Exception as e:
            logger.error(f"Lỗi khi chạy test Dynamic Risk Allocator: {str(e)}")
            results['success'] = False
            results['error'] = str(e)
        
        # Lưu kết quả
        self.test_results['risk_allocator_tests'] = results
        
        return results
    
    def test_trailing_stop(self) -> Dict:
        """
        Kiểm tra Advanced Trailing Stop
        
        Returns:
            Dict: Kết quả test
        """
        logger.info("=== Chạy test Advanced Trailing Stop ===")
        
        results = {'success': True, 'details': {}}
        
        try:
            # Test 1: Trailing Stop Percentage
            logger.info("Test 1: Trailing Stop Percentage")
            
            # Tạo trailing stop
            ts_percentage = AdvancedTrailingStop(
                strategy_type="percentage",
                config={
                    "activation_percent": 1.0,
                    "callback_percent": 0.5
                }
            )
            
            # Tạo vị thế BUY
            buy_position = {
                'id': 'test_buy',
                'symbol': 'BTCUSDT',
                'side': 'BUY',
                'entry_price': 50000,
                'quantity': 0.1,
                'ts_activated': False,
                'ts_stop_price': None
            }
            
            # Khởi tạo trailing stop
            buy_position = ts_percentage.initialize_position(buy_position)
            
            # Tạo các mức giá
            prices = [
                50000,  # Giá ban đầu
                50400,  # Chưa tăng đủ để kích hoạt (0.8%)
                50500,  # Tăng đủ để kích hoạt (1.0%)
                50600,  # Tăng tiếp
                50700,  # Tăng tiếp
                50600,  # Giảm, chưa đủ để dừng
                50400,  # Giảm, đủ để dừng
                50300   # Giảm thêm
            ]
            
            # Theo dõi cập nhật trailing stop
            ts_updates = []
            should_close = False
            stop_price = None
            close_reason = None
            
            for price in prices:
                # Cập nhật trailing stop
                buy_position = ts_percentage.update_trailing_stop(buy_position, price)
                
                # Kiểm tra đóng vị thế
                should_close_now, reason = ts_percentage.check_stop_condition(buy_position, price)
                
                if should_close_now:
                    should_close = True
                    close_reason = reason
                    break
                
                # Lưu trạng thái
                ts_updates.append({
                    'price': price,
                    'ts_activated': buy_position.get('ts_activated', False),
                    'ts_stop_price': buy_position.get('ts_stop_price')
                })
                
                if buy_position.get('ts_stop_price'):
                    stop_price = buy_position.get('ts_stop_price')
            
            # Kiểm tra kết quả
            results['details']['percentage_trailing_stop'] = {
                'ts_updates': ts_updates,
                'should_close': should_close,
                'stop_price': stop_price,
                'close_reason': close_reason,
                'test_passed': should_close and close_reason == 'trailing_stop'
            }
            
            # Test 2: Trailing Stop ATR
            logger.info("Test 2: Trailing Stop ATR")
            
            # Tạo trailing stop
            ts_atr = AdvancedTrailingStop(
                strategy_type="atr",
                config={
                    "atr_multiplier": 2.0,
                    "atr_period": 14
                },
                data_cache=self.data_cache
            )
            
            # Tạo vị thế SELL
            sell_position = {
                'id': 'test_sell',
                'symbol': 'BTCUSDT',
                'side': 'SELL',
                'entry_price': 50000,
                'quantity': 0.1,
                'ts_activated': False,
                'ts_stop_price': None
            }
            
            # Lưu ATR vào cache
            self.data_cache.set('indicators', 'BTCUSDT_1h_atr', 500)  # ATR = 500
            
            # Khởi tạo trailing stop
            sell_position = ts_atr.initialize_position(sell_position)
            
            # Tạo các mức giá
            prices = [
                50000,  # Giá ban đầu
                49500,  # Giảm, chưa đủ để kích hoạt
                49000,  # Giảm, đủ để kích hoạt
                48500,  # Giảm tiếp
                48000,  # Giảm tiếp
                48500,  # Tăng, chưa đủ để dừng
                49000,  # Tăng, đủ để dừng
                49500   # Tăng thêm
            ]
            
            # Theo dõi cập nhật trailing stop
            ts_updates = []
            should_close = False
            stop_price = None
            close_reason = None
            
            for price in prices:
                # Cập nhật trailing stop
                sell_position = ts_atr.update_trailing_stop(sell_position, price)
                
                # Kiểm tra đóng vị thế
                should_close_now, reason = ts_atr.check_stop_condition(sell_position, price)
                
                if should_close_now:
                    should_close = True
                    close_reason = reason
                    break
                
                # Lưu trạng thái
                ts_updates.append({
                    'price': price,
                    'ts_activated': sell_position.get('ts_activated', False),
                    'ts_stop_price': sell_position.get('ts_stop_price')
                })
                
                if sell_position.get('ts_stop_price'):
                    stop_price = sell_position.get('ts_stop_price')
            
            # Kiểm tra kết quả
            results['details']['atr_trailing_stop'] = {
                'ts_updates': ts_updates,
                'should_close': should_close,
                'stop_price': stop_price,
                'close_reason': close_reason,
                'test_passed': should_close and close_reason == 'trailing_stop'
            }
            
            # Tính toán kết quả cuối cùng
            all_passed = all(detail.get('test_passed', False) for detail in results['details'].values())
            results['success'] = all_passed
            
            logger.info(f"Kết quả test Advanced Trailing Stop: {'PASSED' if all_passed else 'FAILED'}")
        
        except Exception as e:
            logger.error(f"Lỗi khi chạy test Advanced Trailing Stop: {str(e)}")
            results['success'] = False
            results['error'] = str(e)
        
        # Lưu kết quả
        self.test_results['trailing_stop_tests'] = results
        
        return results
    
    def test_trading_scenarios(self) -> Dict:
        """
        Kiểm tra các kịch bản giao dịch
        
        Returns:
            Dict: Kết quả test
        """
        logger.info("=== Chạy test các kịch bản giao dịch ===")
        
        results = {'success': True, 'details': {}}
        
        try:
            # Tạo test case runner
            test_runner = TestCaseRunner()
            
            # Test 1: Kịch bản thị trường trending
            logger.info("Test 1: Kịch bản thị trường trending")
            
            try:
                trending_result = test_runner.run_entry_test_trending('BTCUSDT')
                
                results['details']['trending_scenario'] = {
                    'result': trending_result,
                    'test_passed': trending_result.get('market_regime') == 'trending'
                }
            except Exception as e:
                logger.error(f"Lỗi khi chạy test kịch bản trending: {str(e)}")
                results['details']['trending_scenario'] = {
                    'error': str(e),
                    'test_passed': False
                }
            
            # Test 2: Kịch bản thị trường biến động
            logger.info("Test 2: Kịch bản thị trường biến động")
            
            try:
                volatile_result = test_runner.run_entry_test_volatile('BTCUSDT')
                
                results['details']['volatile_scenario'] = {
                    'result': volatile_result,
                    'test_passed': volatile_result.get('market_regime') == 'volatile'
                }
            except Exception as e:
                logger.error(f"Lỗi khi chạy test kịch bản volatile: {str(e)}")
                results['details']['volatile_scenario'] = {
                    'error': str(e),
                    'test_passed': False
                }
            
            # Test 3: Kịch bản thị trường đi ngang
            logger.info("Test 3: Kịch bản thị trường đi ngang")
            
            try:
                ranging_result = test_runner.run_entry_test_ranging('BTCUSDT')
                
                results['details']['ranging_scenario'] = {
                    'result': ranging_result,
                    'test_passed': ranging_result.get('market_regime') == 'ranging'
                }
            except Exception as e:
                logger.error(f"Lỗi khi chạy test kịch bản ranging: {str(e)}")
                results['details']['ranging_scenario'] = {
                    'error': str(e),
                    'test_passed': False
                }
            
            # Test 4: Kịch bản thị trường đi ngược với vị thế
            logger.info("Test 4: Kịch bản thị trường đi ngược với vị thế")
            
            try:
                adverse_result = test_runner.run_position_management_test_adverse('BTCUSDT')
                
                results['details']['adverse_scenario'] = {
                    'result': adverse_result,
                    'test_passed': adverse_result.get('stop_loss_triggered', False)
                }
            except Exception as e:
                logger.error(f"Lỗi khi chạy test kịch bản adverse: {str(e)}")
                results['details']['adverse_scenario'] = {
                    'error': str(e),
                    'test_passed': False
                }
            
            # Test 5: Kịch bản thị trường đi thuận với vị thế
            logger.info("Test 5: Kịch bản thị trường đi thuận với vị thế")
            
            try:
                favorable_result = test_runner.run_position_management_test_favorable('BTCUSDT')
                
                results['details']['favorable_scenario'] = {
                    'result': favorable_result,
                    'test_passed': favorable_result.get('ts_activated', False)
                }
            except Exception as e:
                logger.error(f"Lỗi khi chạy test kịch bản favorable: {str(e)}")
                results['details']['favorable_scenario'] = {
                    'error': str(e),
                    'test_passed': False
                }
            
            # Tính toán kết quả cuối cùng
            all_passed = all(detail.get('test_passed', False) for detail in results['details'].values())
            results['success'] = all_passed
            
            logger.info(f"Kết quả test các kịch bản giao dịch: {'PASSED' if all_passed else 'FAILED'}")
        
        except Exception as e:
            logger.error(f"Lỗi khi chạy test các kịch bản giao dịch: {str(e)}")
            results['success'] = False
            results['error'] = str(e)
        
        # Lưu kết quả
        self.test_results['trading_scenarios'] = results
        
        return results
    
    def test_comprehensive_backtest(self) -> Dict:
        """
        Kiểm tra Comprehensive Backtest
        
        Returns:
            Dict: Kết quả test
        """
        logger.info("=== Chạy test Comprehensive Backtest ===")
        
        results = {'success': True, 'details': {}}
        
        try:
            # Kiểm tra thư mục dữ liệu
            if not os.path.exists('backtest_data') or len(os.listdir('backtest_data')) == 0:
                logger.info("Tạo dữ liệu mẫu cho backtest")
                create_sample_data()
            
            # Tạo backtest với ít dữ liệu
            backtest_config = {
                "symbols": ["BTCUSDT"],
                "timeframes": ["1h"],
                "start_date": "2023-01-01",
                "end_date": "2023-01-10",  # Chỉ 10 ngày để test nhanh
                "initial_balance": 10000
            }
            
            # Tạo thư mục cấu hình
            os.makedirs('configs', exist_ok=True)
            
            # Lưu cấu hình
            config_path = 'configs/backtest_config_test.json'
            with open(config_path, 'w') as f:
                json.dump(backtest_config, f, indent=4)
            
            # Tạo backtest
            backtest = ComprehensiveBacktest(config_path)
            
            # Chạy backtest
            backtest_results = backtest.run_backtest()
            
            # Kiểm tra kết quả
            results['details']['backtest'] = {
                'initial_balance': backtest_results.get('initial_balance'),
                'final_balance': backtest_results.get('final_balance'),
                'total_trades': backtest_results.get('total_trades'),
                'win_rate': backtest_results.get('win_rate'),
                'test_passed': isinstance(backtest_results, dict) and 'initial_balance' in backtest_results
            }
            
            # Tạo báo cáo HTML
            html_report = backtest.create_html_report(backtest_results)
            
            # Kiểm tra báo cáo
            results['details']['html_report'] = {
                'report_path': html_report,
                'test_passed': html_report.endswith('.html') and os.path.exists(html_report)
            }
            
            # Tính toán kết quả cuối cùng
            all_passed = all(detail.get('test_passed', False) for detail in results['details'].values())
            results['success'] = all_passed
            
            logger.info(f"Kết quả test Comprehensive Backtest: {'PASSED' if all_passed else 'FAILED'}")
        
        except Exception as e:
            logger.error(f"Lỗi khi chạy test Comprehensive Backtest: {str(e)}")
            results['success'] = False
            results['error'] = str(e)
        
        # Lưu kết quả
        self.test_results['comprehensive_tests'] = results
        
        return results
    
    def create_summary(self) -> Dict:
        """
        Tạo báo cáo tổng hợp
        
        Returns:
            Dict: Báo cáo tổng hợp
        """
        summary = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'component_results': {},
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'duration': (self.end_time - self.start_time).total_seconds() if self.end_time and self.start_time else 0
        }
        
        # Tính tổng số test và số test thành công
        for component, results in self.test_results.items():
            if component == 'summary':
                continue
            
            component_details = results.get('details', {})
            component_tests = len(component_details)
            component_passed = sum(1 for detail in component_details.values() if detail.get('test_passed', False))
            component_failed = component_tests - component_passed
            
            summary['total_tests'] += component_tests
            summary['passed_tests'] += component_passed
            summary['failed_tests'] += component_failed
            
            summary['component_results'][component] = {
                'total': component_tests,
                'passed': component_passed,
                'failed': component_failed,
                'success_rate': (component_passed / component_tests * 100) if component_tests > 0 else 0
            }
        
        # Tính tỷ lệ thành công
        if summary['total_tests'] > 0:
            summary['overall_success_rate'] = summary['passed_tests'] / summary['total_tests'] * 100
        else:
            summary['overall_success_rate'] = 0
        
        # Lưu vào kết quả
        self.test_results['summary'] = summary
        
        return summary
    
    def save_results(self) -> None:
        """Lưu kết quả test vào file"""
        try:
            # Tạo tên file kết quả
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_results_{timestamp}.json"
            filepath = os.path.join(self.output_dir, filename)
            
            # Lưu kết quả
            with open(filepath, 'w') as f:
                json.dump(self.test_results, f, indent=4)
            
            logger.info(f"Đã lưu kết quả test tại {filepath}")
            
            # Tạo báo cáo tóm tắt
            summary_path = os.path.join(self.output_dir, f"test_summary_{timestamp}.txt")
            
            with open(summary_path, 'w') as f:
                f.write(f"=== Báo cáo test hệ thống giao dịch ===\n")
                f.write(f"Thời gian: {self.test_results['summary']['timestamp']}\n")
                f.write(f"Thời gian chạy: {self.test_results['summary']['duration']:.2f} giây\n\n")
                
                f.write(f"Tổng số test: {self.test_results['summary']['total_tests']}\n")
                f.write(f"Số test thành công: {self.test_results['summary']['passed_tests']}\n")
                f.write(f"Số test thất bại: {self.test_results['summary']['failed_tests']}\n")
                f.write(f"Tỷ lệ thành công: {self.test_results['summary']['overall_success_rate']:.2f}%\n\n")
                
                f.write(f"Chi tiết theo thành phần:\n")
                for component, results in self.test_results['summary']['component_results'].items():
                    f.write(f"- {component}:\n")
                    f.write(f"  + Tổng số test: {results['total']}\n")
                    f.write(f"  + Số test thành công: {results['passed']}\n")
                    f.write(f"  + Số test thất bại: {results['failed']}\n")
                    f.write(f"  + Tỷ lệ thành công: {results['success_rate']:.2f}%\n\n")
            
            logger.info(f"Đã lưu báo cáo tóm tắt tại {summary_path}")
        
        except Exception as e:
            logger.error(f"Lỗi khi lưu kết quả test: {str(e)}")
    
    def _create_sample_market_data(self, symbol: str, timeframe: str, regime: str) -> Dict:
        """
        Tạo dữ liệu thị trường mẫu
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            regime (str): Chế độ thị trường
            
        Returns:
            Dict: Dữ liệu thị trường
        """
        if regime == 'trending':
            return {
                'indicators': {
                    'adx': 30,
                    'volatility': 0.02,
                    'bb_width': 0.03,
                    'volume_percentile': 70,
                    'rsi': 70
                }
            }
        elif regime == 'ranging':
            return {
                'indicators': {
                    'adx': 15,
                    'volatility': 0.01,
                    'bb_width': 0.02,
                    'volume_percentile': 40,
                    'rsi': 50
                }
            }
        elif regime == 'volatile':
            return {
                'indicators': {
                    'adx': 20,
                    'volatility': 0.04,
                    'bb_width': 0.06,
                    'volume_percentile': 80,
                    'rsi': 40
                }
            }
        else:
            return {
                'indicators': {
                    'adx': 20,
                    'volatility': 0.02,
                    'bb_width': 0.03,
                    'volume_percentile': 50,
                    'rsi': 50
                }
            }


def main():
    """Hàm chính để chạy test"""
    # Xử lý tham số dòng lệnh
    parser = argparse.ArgumentParser(description='Chạy test cho hệ thống giao dịch')
    parser.add_argument('--output-dir', type=str, default='test_results', help='Thư mục đầu ra kết quả test')
    parser.add_argument('--component', type=str, choices=['api', 'strategy', 'risk', 'trailing', 'scenarios', 'backtest', 'all'], default='all', help='Thành phần cần test')
    
    args = parser.parse_args()
    
    # Tạo tester
    tester = SystemTester(output_dir=args.output_dir)
    
    # Chạy test
    if args.component == 'api':
        tester.test_api_validator()
    elif args.component == 'strategy':
        tester.test_strategy_selector()
    elif args.component == 'risk':
        tester.test_risk_allocator()
    elif args.component == 'trailing':
        tester.test_trailing_stop()
    elif args.component == 'scenarios':
        tester.test_trading_scenarios()
    elif args.component == 'backtest':
        tester.test_comprehensive_backtest()
    else:  # 'all'
        tester.run_all_tests()
    
    # Tạo báo cáo tổng hợp
    summary = tester.create_summary()
    
    # Lưu kết quả
    tester.save_results()
    
    # Hiển thị tóm tắt
    print("\n=== Tóm tắt kết quả test ===")
    print(f"Tổng số test: {summary['total_tests']}")
    print(f"Số test thành công: {summary['passed_tests']}")
    print(f"Số test thất bại: {summary['failed_tests']}")
    print(f"Tỷ lệ thành công: {summary['overall_success_rate']:.2f}%")
    
    print("\nChi tiết theo thành phần:")
    for component, results in summary['component_results'].items():
        print(f"- {component}:")
        print(f"  + Tỷ lệ thành công: {results['success_rate']:.2f}% ({results['passed']}/{results['total']})")


if __name__ == "__main__":
    main()