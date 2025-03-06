#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module kiểm thử tích hợp (Integration Test)

Module này thực hiện các test case tích hợp để kiểm tra hoạt động của toàn bộ hệ thống
và sự tương tác giữa các module.
"""

import os
import sys
import json
import time
import logging
import datetime
from typing import Dict, List, Tuple, Any, Optional, Union
import pandas as pd
import numpy as np

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('integration_test')

# Thêm thư mục gốc vào sys.path để import các module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import các module cần kiểm thử
try:
    from binance_api import BinanceAPI
    from calculate_pnl_with_full_details import PnLCalculator
    from dynamic_leverage_calculator import DynamicLeverageCalculator
    from enhanced_signal_quality import EnhancedSignalQuality
    from enhanced_adaptive_trailing_stop import EnhancedAdaptiveTrailingStop
    from performance_monitor import PerformanceMonitor
except ImportError as e:
    logger.error(f"Lỗi khi import module: {str(e)}")
    raise


class IntegrationTest:
    """Lớp kiểm thử tích hợp các module"""
    
    def __init__(self, config_path: str = 'configs/integration_test_config.json'):
        """
        Khởi tạo kiểm thử tích hợp
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
        """
        self.config = self._load_config(config_path)
        
        # Khởi tạo các module
        self.binance_api = BinanceAPI()
        self.pnl_calculator = PnLCalculator()
        self.leverage_calculator = DynamicLeverageCalculator()  # Không cần tham số binance_api
        self.signal_quality = EnhancedSignalQuality(binance_api=self.binance_api)
        self.trailing_stop = EnhancedAdaptiveTrailingStop(data_provider=self.binance_api)
        self.performance_monitor = PerformanceMonitor(
            binance_api=self.binance_api,
            pnl_calculator=self.pnl_calculator
        )
        
        # Khởi tạo biến lưu trữ kết quả test
        self.test_results = {}
        
        # Tạo thư mục lưu trữ kết quả test
        os.makedirs('test_results', exist_ok=True)
        
        logger.info("Đã khởi tạo IntegrationTest")
    
    def _load_config(self, config_path: str) -> Dict:
        """
        Tải cấu hình từ file
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
            
        Returns:
            Dict: Cấu hình đã tải
        """
        default_config = {
            'test_symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'],
            'test_timeframes': ['1h', '4h'],
            'test_strategies': ['rsi', 'macd', 'bbands'],
            'test_market_regimes': ['trending', 'ranging', 'volatile'],
            'test_account_balance': 10000,
            'test_position_sizes': [0.1, 0.05, 0.02],
            'test_leverage_levels': [1, 3, 5],
            'test_parameters': {
                'rsi': {
                    'overbought': 70,
                    'oversold': 30,
                    'period': 14
                },
                'macd': {
                    'fast_period': 12,
                    'slow_period': 26,
                    'signal_period': 9
                },
                'bbands': {
                    'period': 20,
                    'std_dev': 2.0
                }
            }
        }
        
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Tải cấu hình hoặc tạo file cấu hình mặc định
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {config_path}")
                return config
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning(f"Không tìm thấy hoặc không thể đọc file {config_path}, sử dụng cấu hình mặc định")
            
            # Lưu cấu hình mặc định
            try:
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=4)
                logger.info(f"Đã tạo file cấu hình mặc định tại {config_path}")
            except Exception as e:
                logger.error(f"Không thể tạo file cấu hình mặc định: {str(e)}")
            
            return default_config
    
    def _save_test_results(self) -> None:
        """Lưu kết quả test vào file"""
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        file_path = f'test_results/integration_test_{timestamp}.json'
        
        try:
            with open(file_path, 'w') as f:
                json.dump(self.test_results, f, indent=4)
            logger.info(f"Đã lưu kết quả test vào {file_path}")
        except Exception as e:
            logger.error(f"Không thể lưu kết quả test: {str(e)}")
    
    def run_all_tests(self) -> Dict:
        """
        Chạy tất cả các test case
        
        Returns:
            Dict: Kết quả tất cả các test
        """
        all_results = {}
        
        # Test 1: Kiểm tra kết nối API
        logger.info("Bắt đầu Test 1: Kiểm tra kết nối API")
        all_results['api_connection'] = self.test_api_connection()
        
        # Test 2: Kiểm tra PnL Calculator
        logger.info("Bắt đầu Test 2: Kiểm tra PnL Calculator")
        all_results['pnl_calculator'] = self.test_pnl_calculator()
        
        # Test 3: Kiểm tra Dynamic Leverage Calculator
        logger.info("Bắt đầu Test 3: Kiểm tra Dynamic Leverage Calculator")
        all_results['leverage_calculator'] = self.test_leverage_calculator()
        
        # Test 4: Kiểm tra Enhanced Signal Quality
        logger.info("Bắt đầu Test 4: Kiểm tra Enhanced Signal Quality")
        all_results['signal_quality'] = self.test_signal_quality()
        
        # Test 5: Kiểm tra Enhanced Adaptive Trailing Stop
        logger.info("Bắt đầu Test 5: Kiểm tra Enhanced Adaptive Trailing Stop")
        all_results['trailing_stop'] = self.test_trailing_stop()
        
        # Test 6: Kiểm tra Performance Monitor
        logger.info("Bắt đầu Test 6: Kiểm tra Performance Monitor")
        all_results['performance_monitor'] = self.test_performance_monitor()
        
        # Test 7: Kiểm tra tích hợp toàn bộ hệ thống
        logger.info("Bắt đầu Test 7: Kiểm tra tích hợp toàn bộ hệ thống")
        all_results['full_integration'] = self.test_full_integration()
        
        # Lưu kết quả test
        self.test_results = all_results
        self._save_test_results()
        
        # Tạo báo cáo tổng hợp
        self._create_summary_report(all_results)
        
        return all_results
    
    def test_api_connection(self) -> Dict:
        """
        Kiểm tra kết nối API
        
        Returns:
            Dict: Kết quả test
        """
        results = {'status': 'passed', 'details': []}
        
        try:
            # Kiểm tra lấy dữ liệu thị trường
            symbols = self.config.get('test_symbols', ['BTCUSDT', 'ETHUSDT'])
            
            for symbol in symbols:
                # Lấy ticker
                ticker = self.binance_api.get_symbol_ticker(symbol=symbol)
                if not ticker or 'price' not in ticker:
                    results['status'] = 'failed'
                    results['details'].append(f"Không thể lấy ticker cho {symbol}")
                    continue
                
                # Lấy klines
                timeframe = '1h'
                klines = self.binance_api.get_klines(symbol=symbol, interval=timeframe, limit=10)
                if not klines or len(klines) < 10:
                    results['status'] = 'failed'
                    results['details'].append(f"Không thể lấy klines cho {symbol} {timeframe}")
                    continue
                
                # Thêm kết quả thành công
                results['details'].append({
                    'symbol': symbol,
                    'price': ticker.get('price'),
                    'klines_count': len(klines)
                })
            
            # Kiểm tra lấy thông tin tài khoản
            try:
                # Kiểm tra tài khoản - sử dụng futures_account_balance thay cho get_account_info
                account_balance = self.binance_api.futures_account_balance()
                if not account_balance:
                    results['status'] = 'failed'
                    results['details'].append("Không thể lấy thông tin tài khoản")
                else:
                    # Tìm balance của USDT
                    usdt_balance = next((item['balance'] for item in account_balance if item['asset'] == 'USDT'), 0)
                    results['details'].append({
                        'account_info': 'success',
                        'balance': usdt_balance
                    })
            except Exception as e:
                results['status'] = 'failed'
                results['details'].append(f"Lỗi khi lấy thông tin tài khoản: {str(e)}")
            
        except Exception as e:
            results['status'] = 'failed'
            results['details'].append(f"Lỗi khi kiểm tra kết nối API: {str(e)}")
        
        return results
    
    def test_pnl_calculator(self) -> Dict:
        """
        Kiểm tra PnL Calculator
        
        Returns:
            Dict: Kết quả test
        """
        results = {'status': 'passed', 'details': []}
        
        try:
            # Test case 1: Long position
            test_case = {
                'entry_price': 50000,
                'exit_price': 52000,
                'position_size': 0.1,
                'leverage': 3,
                'position_side': 'LONG',
                'symbol': 'BTCUSDT'
            }
            
            pnl_result = self.pnl_calculator.calculate_pnl_with_full_details(**test_case)
            expected_pnl = (test_case['exit_price'] - test_case['entry_price']) * test_case['position_size'] * test_case['leverage']
            
            # Kiểm tra kết quả
            if 'net_pnl' not in pnl_result:
                results['status'] = 'failed'
                results['details'].append("Thiếu trường net_pnl trong kết quả")
            elif abs(pnl_result['net_pnl'] - expected_pnl) > 1:  # Cho phép sai số 1 USDT do phí
                results['status'] = 'failed'
                results['details'].append(f"Sai lệch PnL: Thực tế {pnl_result['net_pnl']}, Mong đợi ~{expected_pnl}")
            else:
                results['details'].append({
                    'test_case': 'long_position',
                    'expected_pnl': expected_pnl,
                    'actual_pnl': pnl_result['net_pnl'],
                    'roi': pnl_result.get('roi_percent'),
                    'fees': pnl_result.get('total_fee'),
                    'result': 'passed'
                })
            
            # Test case 2: Short position
            test_case = {
                'entry_price': 50000,
                'exit_price': 48000,
                'position_size': 0.1,
                'leverage': 3,
                'position_side': 'SHORT',
                'symbol': 'BTCUSDT'
            }
            
            pnl_result = self.pnl_calculator.calculate_pnl_with_full_details(**test_case)
            expected_pnl = (test_case['entry_price'] - test_case['exit_price']) * test_case['position_size'] * test_case['leverage']
            
            # Kiểm tra kết quả
            if 'net_pnl' not in pnl_result:
                results['status'] = 'failed'
                results['details'].append("Thiếu trường net_pnl trong kết quả")
            elif abs(pnl_result['net_pnl'] - expected_pnl) > 1:  # Cho phép sai số 1 USDT do phí
                results['status'] = 'failed'
                results['details'].append(f"Sai lệch PnL: Thực tế {pnl_result['net_pnl']}, Mong đợi ~{expected_pnl}")
            else:
                results['details'].append({
                    'test_case': 'short_position',
                    'expected_pnl': expected_pnl,
                    'actual_pnl': pnl_result['net_pnl'],
                    'roi': pnl_result.get('roi_percent'),
                    'fees': pnl_result.get('total_fee'),
                    'result': 'passed'
                })
            
            # Test case 3: Partial exits
            test_case = {
                'entry_price': 50000,
                'exit_price': 52000,
                'position_size': 0.2,
                'leverage': 3,
                'position_side': 'LONG',
                'symbol': 'BTCUSDT',
                'partial_exits': [(51000, 0.1), (52000, 0.1)]
            }
            
            pnl_result = self.pnl_calculator.calculate_pnl_with_full_details(**test_case)
            
            # Kiểm tra kết quả
            if 'net_pnl' not in pnl_result or 'partial_exits_detail' not in pnl_result:
                results['status'] = 'failed'
                results['details'].append("Thiếu trường trong kết quả partial exits")
            else:
                results['details'].append({
                    'test_case': 'partial_exits',
                    'actual_pnl': pnl_result['net_pnl'],
                    'roi': pnl_result.get('roi_percent'),
                    'partial_exits_detail': pnl_result.get('partial_exits_detail'),
                    'result': 'passed'
                })
            
        except Exception as e:
            results['status'] = 'failed'
            results['details'].append(f"Lỗi khi kiểm tra PnL Calculator: {str(e)}")
        
        return results
    
    def test_leverage_calculator(self) -> Dict:
        """
        Kiểm tra Dynamic Leverage Calculator
        
        Returns:
            Dict: Kết quả test
        """
        results = {'status': 'passed', 'details': []}
        
        try:
            # Test case 1: Tính toán đòn bẩy động
            symbols = self.config.get('test_symbols', ['BTCUSDT', 'ETHUSDT'])
            
            for symbol in symbols:
                # Lấy đòn bẩy đề xuất dựa trên biến động
                leverage_result = self.leverage_calculator.calculate_dynamic_leverage(
                    symbol=symbol,
                    account_balance=10000,
                    risk_profile='moderate',
                    market_regime='trending',
                    volatility=0.02,
                    open_positions=0,
                    trend_strength=0.5,
                    portfolio_correlation=0.5
                )
                
                if not leverage_result or 'recommended_leverage' not in leverage_result:
                    results['status'] = 'failed'
                    results['details'].append(f"Không thể tính đòn bẩy cho {symbol}")
                    continue
                
                # Kiểm tra giá trị đòn bẩy hợp lý
                recommended_leverage = leverage_result['recommended_leverage']
                if recommended_leverage < 1 or recommended_leverage > 20:
                    results['status'] = 'failed'
                    results['details'].append(f"Đòn bẩy không hợp lý cho {symbol}: {recommended_leverage}")
                    continue
                
                # Thêm kết quả thành công
                results['details'].append({
                    'symbol': symbol,
                    'recommended_leverage': recommended_leverage,
                    'volatility': leverage_result.get('volatility'),
                    'risk_profile': 'moderate',
                    'result': 'passed'
                })
            
            # Test case 2: Kiểm tra tính toán với tham số khác
            volatility_result = self.leverage_calculator.calculate_dynamic_leverage(
                symbol='BTCUSDT',
                account_balance=20000,
                risk_profile='aggressive',
                market_regime='volatile',
                volatility=0.05,
                open_positions=2,
                trend_strength=0.8,
                portfolio_correlation=0.2
            )
            
            if not volatility_result or 'recommended_leverage' not in volatility_result:
                results['status'] = 'failed'
                results['details'].append("Không thể tính đòn bẩy với tham số khác")
            else:
                results['details'].append({
                    'test_case': 'dynamic_leverage_aggressive',
                    'recommended_leverage': volatility_result['recommended_leverage'],
                    'risk_profile': 'aggressive',
                    'market_regime': 'volatile', 
                    'result': 'passed'
                })
            
        except Exception as e:
            results['status'] = 'failed'
            results['details'].append(f"Lỗi khi kiểm tra Dynamic Leverage Calculator: {str(e)}")
        
        return results
    
    def test_signal_quality(self) -> Dict:
        """
        Kiểm tra Enhanced Signal Quality
        
        Returns:
            Dict: Kết quả test
        """
        results = {'status': 'passed', 'details': []}
        
        try:
            # Test case 1: Đánh giá chất lượng tín hiệu
            symbols = self.config.get('test_symbols', ['BTCUSDT', 'ETHUSDT'])
            timeframes = self.config.get('test_timeframes', ['1h', '4h'])
            
            for symbol in symbols:
                for timeframe in timeframes:
                    # Đánh giá chất lượng tín hiệu
                    score, details = self.signal_quality.evaluate_signal_quality(symbol, timeframe)
                    
                    if score == 0 and 'error' in details:
                        results['status'] = 'failed'
                        results['details'].append(f"Không thể đánh giá tín hiệu cho {symbol} {timeframe}: {details['error']}")
                        continue
                    
                    # Kiểm tra điểm đánh giá hợp lý
                    if score < 0 or score > 100:
                        results['status'] = 'failed'
                        results['details'].append(f"Điểm đánh giá không hợp lý cho {symbol} {timeframe}: {score}")
                        continue
                    
                    # Kiểm tra các thành phần trong kết quả
                    required_fields = ['signal_direction', 'signal_strength', 'component_scores']
                    missing_fields = [f for f in required_fields if f not in details]
                    
                    if missing_fields:
                        results['status'] = 'failed'
                        results['details'].append(f"Thiếu các trường {', '.join(missing_fields)} trong kết quả đánh giá")
                        continue
                    
                    # Thêm kết quả thành công
                    results['details'].append({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'score': score,
                        'signal_direction': details['signal_direction'],
                        'signal_strength': details['signal_strength'],
                        'result': 'passed'
                    })
            
            # Test case 2: Lấy danh sách cặp tiền có chất lượng tín hiệu tốt nhất
            try:
                best_symbols = self.signal_quality.get_best_quality_symbols(symbols, '1h')
                
                if not isinstance(best_symbols, list):
                    results['status'] = 'failed'
                    results['details'].append(f"get_best_quality_symbols trả về kiểu không mong đợi: {type(best_symbols)}")
                elif len(best_symbols) == 0:
                    results['status'] = 'failed'
                    results['details'].append("Không thể lấy danh sách cặp tiền có chất lượng tín hiệu tốt nhất")
                else:
                    results['details'].append({
                        'test_case': 'best_quality_symbols',
                        'best_symbols': best_symbols,
                        'result': 'passed'
                    })
            except Exception as e:
                results['status'] = 'failed'
                results['details'].append(f"Lỗi khi lấy best_quality_symbols: {str(e)}")
            
        except Exception as e:
            results['status'] = 'failed'
            results['details'].append(f"Lỗi khi kiểm tra Enhanced Signal Quality: {str(e)}")
        
        return results
    
    def test_trailing_stop(self) -> Dict:
        """
        Kiểm tra Enhanced Adaptive Trailing Stop
        
        Returns:
            Dict: Kết quả test
        """
        results = {'status': 'passed', 'details': []}
        
        try:
            # Test case 1: Backtest với chiến lược trailing stop
            entry_price = 50000.0
            price_data = [49800.0, 50000.0, 50200.0, 50500.0, 51000.0, 51500.0, 52000.0, 51800.0, 51600.0, 51400.0, 51200.0, 51000.0, 50500.0, 50200.0]
            
            # Test với chiến lược percentage
            result1 = self.trailing_stop.backtest_trailing_stop(
                entry_price=entry_price,
                price_data=price_data,
                side='LONG',
                strategy_type='percentage',
                entry_index=1
            )
            
            if not result1 or 'exit_price' not in result1:
                results['status'] = 'failed'
                results['details'].append("Không thể backtest percentage trailing stop")
            else:
                results['details'].append({
                    'test_case': 'percentage_trailing_stop',
                    'entry_price': result1['entry_price'],
                    'exit_price': result1['exit_price'],
                    'pnl': result1['pnl'],
                    'roi': result1['roi'],
                    'exit_reason': result1['exit_reason'],
                    'result': 'passed'
                })
            
            # Test với chiến lược ATR
            result2 = self.trailing_stop.backtest_trailing_stop(
                entry_price=entry_price,
                price_data=price_data,
                side='LONG',
                strategy_type='atr_based',
                entry_index=1
            )
            
            if not result2 or 'exit_price' not in result2:
                results['status'] = 'failed'
                results['details'].append("Không thể backtest ATR trailing stop")
            else:
                results['details'].append({
                    'test_case': 'atr_trailing_stop',
                    'entry_price': result2['entry_price'],
                    'exit_price': result2['exit_price'],
                    'pnl': result2['pnl'],
                    'roi': result2['roi'],
                    'exit_reason': result2['exit_reason'],
                    'result': 'passed'
                })
            
            # Test case 2: Khởi tạo vị thế với trailing stop
            position = {
                'symbol': 'BTCUSDT',
                'side': 'LONG',
                'entry_price': 50000,
                'quantity': 0.1,
                'entry_time': int(time.time())
            }
            
            position = self.trailing_stop.initialize_position(position, 'percentage', 'trending')
            
            if 'trailing_status' not in position or 'trailing_strategy' not in position:
                results['status'] = 'failed'
                results['details'].append("Không thể khởi tạo vị thế với trailing stop")
            else:
                # Cập nhật trailing stop
                updated_position = self.trailing_stop.update_trailing_stop(position, 51000)
                
                if 'trailing_status' not in updated_position or 'stop_price' not in updated_position['trailing_status']:
                    results['status'] = 'failed'
                    results['details'].append("Không thể cập nhật trailing stop")
                else:
                    results['details'].append({
                        'test_case': 'initialize_and_update_position',
                        'symbol': position['symbol'],
                        'strategy_type': position['trailing_strategy']['type'],
                        'market_regime': position['trailing_strategy']['market_regime'],
                        'stop_price': updated_position['trailing_status']['stop_price'],
                        'result': 'passed'
                    })
            
        except Exception as e:
            results['status'] = 'failed'
            results['details'].append(f"Lỗi khi kiểm tra Enhanced Adaptive Trailing Stop: {str(e)}")
        
        return results
    
    def test_performance_monitor(self) -> Dict:
        """
        Kiểm tra Performance Monitor
        
        Returns:
            Dict: Kết quả test
        """
        results = {'status': 'passed', 'details': []}
        
        try:
            # Test case 1: Ghi nhận giao dịch
            trade_data = {
                'symbol': 'BTCUSDT',
                'side': 'LONG',
                'entry_price': 50000,
                'exit_price': 52000,
                'position_size': 0.1,
                'leverage': 3,
                'strategy': 'rsi',
                'entry_time': int(time.time()) - 3600,
                'exit_time': int(time.time())
            }
            
            trade_id = self.performance_monitor.record_trade(trade_data)
            
            if not trade_id:
                results['status'] = 'failed'
                results['details'].append("Không thể ghi nhận giao dịch")
            else:
                results['details'].append({
                    'test_case': 'record_trade',
                    'trade_id': trade_id,
                    'result': 'passed'
                })
            
            # Test case 2: Cập nhật chỉ số hiệu suất
            metrics = self.performance_monitor.update_metrics()
            
            if not metrics or 'overall' not in metrics:
                results['status'] = 'failed'
                results['details'].append("Không thể cập nhật chỉ số hiệu suất")
            else:
                results['details'].append({
                    'test_case': 'update_metrics',
                    'total_trades': metrics.get('overall', {}).get('total_trades', 0),
                    'win_rate': metrics.get('overall', {}).get('win_rate', 0),
                    'total_pnl': metrics.get('overall', {}).get('total_pnl', 0),
                    'result': 'passed'
                })
            
            # Test case 3: Tạo báo cáo hằng ngày
            daily_report = self.performance_monitor.create_daily_report()
            
            if not daily_report or not os.path.exists(daily_report):
                results['status'] = 'failed'
                results['details'].append("Không thể tạo báo cáo hằng ngày")
            else:
                results['details'].append({
                    'test_case': 'daily_report',
                    'report_path': daily_report,
                    'result': 'passed'
                })
            
            # Test case 4: Tạo đề xuất chiến lược
            recommendations = self.performance_monitor.generate_strategy_recommendations()
            
            if not recommendations or 'status' not in recommendations:
                results['status'] = 'failed'
                results['details'].append("Không thể tạo đề xuất chiến lược")
            else:
                results['details'].append({
                    'test_case': 'strategy_recommendations',
                    'status': recommendations['status'],
                    'result': 'passed'
                })
            
            # Test case 5: Tạo biểu đồ equity
            equity_chart = self.performance_monitor.create_equity_chart()
            
            # Nếu chưa có đủ dữ liệu giao dịch, kết quả có thể rỗng
            if equity_chart and os.path.exists(equity_chart):
                results['details'].append({
                    'test_case': 'equity_chart',
                    'chart_path': equity_chart,
                    'result': 'passed'
                })
            
        except Exception as e:
            results['status'] = 'failed'
            results['details'].append(f"Lỗi khi kiểm tra Performance Monitor: {str(e)}")
        
        return results
    
    def test_full_integration(self) -> Dict:
        """
        Kiểm tra tích hợp toàn bộ hệ thống
        
        Returns:
            Dict: Kết quả test
        """
        results = {'status': 'passed', 'details': []}
        
        try:
            # Test case: Mô phỏng quá trình giao dịch đầy đủ
            symbol = 'BTCUSDT'
            timeframe = '1h'
            
            # Bước 1: Đánh giá chất lượng tín hiệu
            signal_score, signal_details = self.signal_quality.evaluate_signal_quality(symbol, timeframe)
            
            if signal_score == 0 and 'error' in signal_details:
                results['status'] = 'failed'
                results['details'].append(f"Không thể đánh giá tín hiệu: {signal_details['error']}")
                return results
            
            # Lấy hướng tín hiệu và cường độ
            signal_direction = signal_details['signal_direction']
            signal_strength = signal_details['signal_strength']
            
            # Bước 2: Tính toán đòn bẩy động
            leverage_result = self.leverage_calculator.calculate_dynamic_leverage(
                symbol=symbol,
                account_balance=10000,
                risk_profile='moderate',
                market_regime='trending',
                volatility=0.02,
                open_positions=0,
                trend_strength=signal_strength,
                portfolio_correlation=0.5
            )
            
            if not leverage_result or 'recommended_leverage' not in leverage_result:
                results['status'] = 'failed'
                results['details'].append("Không thể tính đòn bẩy động")
                return results
            
            recommended_leverage = leverage_result['recommended_leverage']
            
            # Bước 3: Mô phỏng giao dịch
            # Lấy giá hiện tại
            ticker = self.binance_api.get_symbol_ticker(symbol=symbol)
            if not ticker or 'price' not in ticker:
                results['status'] = 'failed'
                results['details'].append("Không thể lấy giá hiện tại")
                return results
            
            current_price = float(ticker['price'])
            position_size = 0.01  # Kích thước vị thế nhỏ cho test
            
            # Mô phỏng entry
            entry_data = {
                'symbol': symbol,
                'side': signal_direction,
                'entry_price': current_price,
                'position_size': position_size,
                'leverage': recommended_leverage,
                'entry_time': int(time.time())
            }
            
            # Bước 4: Khởi tạo trailing stop
            position = self.trailing_stop.initialize_position(entry_data, 'percentage', 'trending')
            
            if 'trailing_status' not in position or 'trailing_strategy' not in position:
                results['status'] = 'failed'
                results['details'].append("Không thể khởi tạo trailing stop")
                return results
            
            # Mô phỏng giá thay đổi
            price_change_pct = 0.02  # 2% thay đổi
            if signal_direction == 'LONG':
                new_price = current_price * (1 + price_change_pct)
            else:
                new_price = current_price * (1 - price_change_pct)
            
            # Cập nhật trailing stop
            updated_position = self.trailing_stop.update_trailing_stop(position, new_price)
            
            # Bước 5: Mô phỏng exit
            exit_data = {
                'symbol': symbol,
                'side': signal_direction,
                'entry_price': current_price,
                'exit_price': new_price,
                'position_size': position_size,
                'leverage': recommended_leverage,
                'strategy': 'integration_test',
                'entry_time': int(time.time()) - 3600,
                'exit_time': int(time.time())
            }
            
            # Ghi nhận giao dịch
            trade_id = self.performance_monitor.record_trade(exit_data)
            
            if not trade_id:
                results['status'] = 'failed'
                results['details'].append("Không thể ghi nhận giao dịch")
                return results
            
            # Cập nhật chỉ số hiệu suất
            metrics = self.performance_monitor.update_metrics()
            
            # Tạo báo cáo
            report = self.performance_monitor.create_daily_report()
            
            # Thêm kết quả thành công
            results['details'].append({
                'symbol': symbol,
                'signal_score': signal_score,
                'signal_direction': signal_direction,
                'signal_strength': signal_strength,
                'recommended_leverage': recommended_leverage,
                'entry_price': current_price,
                'exit_price': new_price,
                'trailing_stop_status': updated_position['trailing_status']['status'],
                'stop_price': updated_position['trailing_status']['stop_price'],
                'trade_id': trade_id,
                'report_path': report,
                'result': 'passed'
            })
            
        except Exception as e:
            results['status'] = 'failed'
            results['details'].append(f"Lỗi khi kiểm tra tích hợp toàn bộ hệ thống: {str(e)}")
        
        return results
    
    def _create_summary_report(self, results: Dict) -> str:
        """
        Tạo báo cáo tổng hợp
        
        Args:
            results (Dict): Kết quả tất cả các test
            
        Returns:
            str: Đường dẫn đến file báo cáo
        """
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        file_path = f'test_results/summary_report_{timestamp}.txt'
        
        try:
            with open(file_path, 'w') as f:
                f.write("=== BÁO CÁO KIỂM THỦ TÍCH HỢP ===\n")
                f.write(f"Thời gian: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Tổng hợp kết quả
                total_tests = len(results)
                passed_tests = sum(1 for result in results.values() if result['status'] == 'passed')
                failed_tests = total_tests - passed_tests
                
                f.write(f"Tổng số test: {total_tests}\n")
                f.write(f"Test thành công: {passed_tests}\n")
                f.write(f"Test thất bại: {failed_tests}\n\n")
                
                # Chi tiết từng test
                for test_name, test_result in results.items():
                    status = "THÀNH CÔNG" if test_result['status'] == 'passed' else "THẤT BẠI"
                    f.write(f"=== {test_name.upper()} - {status} ===\n")
                    
                    # Ghi chi tiết thất bại (nếu có)
                    if test_result['status'] == 'failed':
                        for detail in test_result['details']:
                            if isinstance(detail, str):
                                f.write(f"- {detail}\n")
                    
                    f.write("\n")
                
                # Kết luận
                if failed_tests == 0:
                    f.write("KẾT LUẬN: Tất cả các test đều thành công!\n")
                else:
                    f.write(f"KẾT LUẬN: Có {failed_tests} test thất bại. Cần kiểm tra lại.\n")
            
            logger.info(f"Đã tạo báo cáo tổng hợp tại {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Không thể tạo báo cáo tổng hợp: {str(e)}")
            return ""


def run_single_test():
    """Chạy một test case đơn lẻ"""
    test = IntegrationTest()
    
    # Chỉ chạy test API connection
    result = test.test_api_connection()
    print("Kết quả test API connection:")
    print(f"Status: {result['status']}")
    print("Chi tiết:")
    for detail in result['details']:
        print(f"- {detail}")


def run_all_tests():
    """Chạy tất cả các test case"""
    test = IntegrationTest()
    results = test.run_all_tests()
    
    # In kết quả tổng quan
    print("=== KẾT QUẢ KIỂM THỬ TÍCH HỢP ===")
    for test_name, test_result in results.items():
        status = "PASSED" if test_result['status'] == 'passed' else "FAILED"
        print(f"{test_name}: {status}")


if __name__ == "__main__":
    # Chạy một test case đơn lẻ
    # run_single_test()
    
    # Chạy tất cả các test case
    run_all_tests()