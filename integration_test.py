#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Integration Test cho các module cải tiến

Script này thực hiện kiểm thử tích hợp các module mới phát triển:
1. calculate_pnl_with_full_details.py
2. dynamic_leverage_calculator.py
3. enhanced_signal_quality.py
4. enhanced_adaptive_trailing_stop.py
5. performance_monitor.py
"""

import os
import sys
import time
import json
import logging
import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('integration_test.log')
    ]
)
logger = logging.getLogger('integration_test')

# Import các module cần kiểm thử
try:
    from calculate_pnl_with_full_details import PnLCalculator
    from dynamic_leverage_calculator import DynamicLeverageCalculator
    from enhanced_signal_quality import EnhancedSignalQuality
    from enhanced_adaptive_trailing_stop import EnhancedAdaptiveTrailingStop
    from performance_monitor import PerformanceMonitor, PerformanceMetrics
    from binance_api import BinanceAPI
    
    # Kiểm tra đã import thành công
    logger.info("Đã import tất cả các module thành công")
    modules_available = True
except ImportError as e:
    logger.error(f"Lỗi khi import module: {str(e)}")
    modules_available = False


class IntegrationTest:
    """Lớp kiểm thử tích hợp các module"""
    
    def __init__(self):
        """Khởi tạo"""
        # Kiểm tra các module đã được import thành công chưa
        if not modules_available:
            logger.error("Các module chưa được import đầy đủ. Không thể tiếp tục kiểm thử.")
            return
        
        logger.info("Bắt đầu khởi tạo các thành phần cần thiết cho kiểm thử tích hợp")
        
        # Khởi tạo Binance API
        try:
            self.binance_api = BinanceAPI()
            logger.info("Đã khởi tạo BinanceAPI thành công")
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo BinanceAPI: {str(e)}")
            self.binance_api = None
        
        # Khởi tạo các module
        self.pnl_calculator = PnLCalculator(binance_api=self.binance_api)
        self.leverage_calculator = DynamicLeverageCalculator()
        self.signal_quality = EnhancedSignalQuality(binance_api=self.binance_api)
        self.trailing_stop = EnhancedAdaptiveTrailingStop()
        self.performance_monitor = PerformanceMonitor()
        
        # Chuẩn bị dữ liệu cho test
        self.test_data = {
            'symbol': 'BTCUSDT',
            'entry_price': 50000,
            'leverage': 5,
            'quantity': 0.1,
            'side': 'LONG',
            'timeframe': '1h'
        }
        
        # Dữ liệu về chế độ thị trường
        self.market_data = {
            'market_regime': 'trending',
            'volatility': 0.02,
            'account_balance': 10000,
            'max_open_positions': 2,
            'portfolio_correlation': 0.3,
            'price_ratio_to_ma': 1.05
        }
        
        logger.info("Đã khởi tạo IntegrationTest thành công")
    
    def test_pnl_calculator(self):
        """Kiểm thử PnL Calculator"""
        logger.info("Bắt đầu kiểm thử PnL Calculator")
        
        # Dữ liệu kiểm thử
        test_cases = [
            {
                'name': 'Test LONG simple',
                'entry_price': 50000,
                'exit_price': 51000,
                'quantity': 0.1,
                'leverage': 5,
                'position_side': 'LONG',
                'expected_pnl': 500  # (51000-50000) * 0.1 * 5
            },
            {
                'name': 'Test SHORT simple',
                'entry_price': 50000,
                'exit_price': 49000,
                'quantity': 0.1,
                'leverage': 5,
                'position_side': 'SHORT',
                'expected_pnl': 500  # (50000-49000) * 0.1 * 5
            },
            {
                'name': 'Test with fees',
                'entry_price': 50000,
                'exit_price': 51000,
                'quantity': 0.1,
                'leverage': 5,
                'position_side': 'LONG',
                'open_fee_rate': 0.0004,
                'close_fee_rate': 0.0004,
                'expected_pnl': 500 - (50000 * 0.1 * 0.0004) - (51000 * 0.1 * 0.0004)
                # 500 - 2 - 2.04 = 495.96
            },
            {
                'name': 'Test with partial exits',
                'entry_price': 50000,
                'exit_price': 51000,
                'quantity': 0.1,
                'leverage': 5,
                'position_side': 'LONG',
                'partial_exits': [
                    (50500, 0.04),  # Đóng 40% vị thế ở 50500
                    (51000, 0.06)   # Đóng 60% vị thế ở 51000
                ],
                'expected_pnl': (50500 - 50000) * 0.04 * 5 + (51000 - 50000) * 0.06 * 5
                # 100 + 300 = 400
            }
        ]
        
        # Chạy các trường hợp kiểm thử
        for tc in test_cases:
            try:
                # Gọi hàm tính PnL
                result = self.pnl_calculator.calculate_pnl_with_full_details(
                    entry_price=tc['entry_price'],
                    exit_price=tc['exit_price'],
                    position_size=tc['quantity'],
                    leverage=tc['leverage'],
                    position_side=tc['position_side'],
                    open_fee_rate=tc.get('open_fee_rate', 0.0004),
                    close_fee_rate=tc.get('close_fee_rate', 0.0004),
                    partial_exits=tc.get('partial_exits', None)
                )
                
                # Kiểm tra kết quả
                pnl_diff = abs(result['net_pnl'] - tc['expected_pnl'])
                if pnl_diff < 0.01:  # Chênh lệch nhỏ do làm tròn
                    logger.info(f"✅ {tc['name']} passed: Kết quả {result['net_pnl']:.2f}, kỳ vọng {tc['expected_pnl']:.2f}")
                else:
                    logger.error(f"❌ {tc['name']} failed: Kết quả {result['net_pnl']:.2f}, kỳ vọng {tc['expected_pnl']:.2f}")
            except Exception as e:
                logger.error(f"❌ {tc['name']} failed with exception: {str(e)}")
        
        logger.info("Kết thúc kiểm thử PnL Calculator")
    
    def test_dynamic_leverage(self):
        """Kiểm thử Dynamic Leverage Calculator"""
        logger.info("Bắt đầu kiểm thử Dynamic Leverage Calculator")
        
        # Kiểm thử các chế độ thị trường khác nhau
        market_regimes = ['trending', 'ranging', 'volatile', 'quiet', 'neutral']
        for regime in market_regimes:
            try:
                result = self.leverage_calculator.calculate_dynamic_leverage(
                    market_regime=regime,
                    volatility=0.02,
                    account_balance=10000
                )
                
                logger.info(f"Chế độ {regime}: Đòn bẩy = {result['final_leverage']}x")
            except Exception as e:
                logger.error(f"❌ Kiểm thử chế độ {regime} failed: {str(e)}")
        
        # Kiểm thử biến động khác nhau
        volatilities = [0.01, 0.02, 0.05, 0.1]
        for vol in volatilities:
            try:
                result = self.leverage_calculator.calculate_dynamic_leverage(
                    market_regime='neutral',
                    volatility=vol,
                    account_balance=10000
                )
                
                logger.info(f"Biến động {vol*100}%: Đòn bẩy = {result['final_leverage']}x")
            except Exception as e:
                logger.error(f"❌ Kiểm thử biến động {vol} failed: {str(e)}")
        
        # Kiểm thử phân tích
        try:
            # Thêm một số quyết định vào lịch sử
            for i in range(10):
                # Tạo quyết định với biến động và chế độ khác nhau
                volatility = 0.01 + (i % 5) * 0.01
                regime = market_regimes[i % len(market_regimes)]
                
                self.leverage_calculator.calculate_dynamic_leverage(
                    market_regime=regime,
                    volatility=volatility,
                    account_balance=10000,
                    symbol='BTCUSDT'
                )
            
            # Phân tích xu hướng đòn bẩy
            trend_analysis = self.leverage_calculator.get_leverage_trend(symbol='BTCUSDT')
            logger.info(f"Phân tích xu hướng đòn bẩy: {trend_analysis['trend_direction']}")
            
            # Phân tích tác động của biến động
            volatility_analysis = self.leverage_calculator.analyze_volatility_impact(symbol='BTCUSDT')
            logger.info(f"Tương quan biến động-đòn bẩy: {volatility_analysis['correlation']:.2f}")
        except Exception as e:
            logger.error(f"❌ Kiểm thử phân tích đòn bẩy failed: {str(e)}")
        
        logger.info("Kết thúc kiểm thử Dynamic Leverage Calculator")
    
    def test_signal_quality(self):
        """Kiểm thử Enhanced Signal Quality"""
        logger.info("Bắt đầu kiểm thử Enhanced Signal Quality")
        
        if not self.binance_api:
            logger.error("❌ Không có API Binance, không thể kiểm thử Signal Quality")
            return
        
        # Kiểm tra một số cặp tiền
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        timeframe = '1h'
        
        for symbol in symbols:
            try:
                # Đánh giá chất lượng tín hiệu
                score, details = self.signal_quality.evaluate_signal_quality(symbol, timeframe)
                
                # Kiểm tra kết quả
                logger.info(f"{symbol}: Điểm chất lượng = {score:.2f}, Hướng = {details['signal_direction']}, Mạnh = {details['signal_strength']}")
                
                # Kiểm tra các thành phần
                components = details['component_scores']
                logger.info(f"{symbol} - Trend Strength: {components['trend_strength']:.2f}")
                logger.info(f"{symbol} - BTC Alignment: {components['btc_alignment']:.2f}")
                
                # Kiểm tra tương quan BTC
                logger.info(f"{symbol} - BTC Correlation: {details['btc_correlation']:.2f}")
            except Exception as e:
                logger.error(f"❌ Kiểm thử signal quality cho {symbol} failed: {str(e)}")
        
        logger.info("Kết thúc kiểm thử Enhanced Signal Quality")
    
    def test_trailing_stop(self):
        """Kiểm thử Enhanced Adaptive Trailing Stop"""
        logger.info("Bắt đầu kiểm thử Enhanced Adaptive Trailing Stop")
        
        # Tạo vị thế mẫu
        position = {
            'symbol': 'BTCUSDT',
            'side': 'LONG',
            'entry_price': 50000,
            'quantity': 0.1,
            'entry_time': int(time.time()) - 24 * 3600  # 1 ngày trước
        }
        
        # Khởi tạo trailing stop
        try:
            # Khởi tạo vị thế
            position = self.trailing_stop.initialize_position(position)
            logger.info(f"Khởi tạo vị thế: {position['trailing_status']}")
            
            # Kiểm thử với giá tăng dần
            prices = [50500, 51000, 51500, 52000, 51500, 51000, 50500]
            for price in prices:
                # Cập nhật trailing stop
                position = self.trailing_stop.update_trailing_stop(position, price)
                should_close, reason = self.trailing_stop.check_stop_condition(position, price)
                
                status = self.trailing_stop.get_trailing_status(position)
                logger.info(f"Giá: {price}, Stop: {status['stop_price']:.2f if status['stop_price'] else None}, Kích hoạt: {status['activated']}")
                
                if should_close:
                    logger.info(f"Đóng vị thế tại giá {price}: {reason}")
                    break
            
            # Kiểm thử backtest
            test_prices = [49500, 50000, 50500, 51000, 51500, 52000, 51500, 51000, 50500, 50000, 49500]
            backtest_result = self.trailing_stop.backtest_trailing_stop(
                entry_price=50000,
                price_data=test_prices,
                side='LONG',
                position_size=0.1,
                entry_index=1  # Vào ở index 1 (giá 50000)
            )
            
            logger.info(f"Backtest: Vào giá {backtest_result['entry_price']}, ra giá {backtest_result['exit_price']}")
            logger.info(f"Backtest: PnL = {backtest_result['pnl']:.2f}")
        except Exception as e:
            logger.error(f"❌ Kiểm thử trailing stop failed: {str(e)}")
        
        logger.info("Kết thúc kiểm thử Enhanced Adaptive Trailing Stop")
    
    def test_performance_monitor(self):
        """Kiểm thử Performance Monitor"""
        logger.info("Bắt đầu kiểm thử Performance Monitor")
        
        # Tạo một số giao dịch mẫu
        trades = [
            {
                'trade_id': 'trade_1',
                'symbol': 'BTCUSDT',
                'side': 'LONG',
                'entry_price': 50000,
                'exit_price': 52000,
                'quantity': 0.1,
                'leverage': 5,
                'entry_time': int(time.time()) - 7 * 24 * 3600,  # 7 ngày trước
                'exit_time': int(time.time()) - 6 * 24 * 3600,   # 6 ngày trước
                'strategy': 'trend_following',
                'market_regime': 'trending',
                'net_pnl': 1000  # (52000 - 50000) * 0.1 * 5
            },
            {
                'trade_id': 'trade_2',
                'symbol': 'ETHUSDT',
                'side': 'SHORT',
                'entry_price': 3000,
                'exit_price': 3100,
                'quantity': 0.5,
                'leverage': 3,
                'entry_time': int(time.time()) - 5 * 24 * 3600,  # 5 ngày trước
                'exit_time': int(time.time()) - 4 * 24 * 3600,   # 4 ngày trước
                'strategy': 'mean_reversion',
                'market_regime': 'ranging',
                'net_pnl': -150  # (3000 - 3100) * 0.5 * 3
            },
            {
                'trade_id': 'trade_3',
                'symbol': 'BTCUSDT',
                'side': 'LONG',
                'entry_price': 51000,
                'exit_price': 51500,
                'quantity': 0.2,
                'leverage': 3,
                'entry_time': int(time.time()) - 3 * 24 * 3600,  # 3 ngày trước
                'exit_time': int(time.time()) - 2 * 24 * 3600,   # 2 ngày trước
                'strategy': 'breakout',
                'market_regime': 'volatile',
                'net_pnl': 300  # (51500 - 51000) * 0.2 * 3
            }
        ]
        
        try:
            # Thêm các giao dịch
            for trade in trades:
                self.performance_monitor.add_trade(trade)
            
            # Tính các chỉ số hiệu suất
            self.performance_monitor.calculate_equity_curve()
            self.performance_monitor.calculate_daily_returns()
            
            # Lấy thống kê
            stats = self.performance_monitor.get_trade_statistics()
            logger.info(f"Tổng số giao dịch: {stats['total_trades']}")
            logger.info(f"Tỷ lệ thắng: {stats['win_rate']*100:.2f}%")
            logger.info(f"Profit Factor: {stats['profit_factor']:.2f}")
            logger.info(f"Lợi nhuận ròng: {stats['net_profit']:.2f}")
            logger.info(f"Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
            logger.info(f"Drawdown tối đa: {stats['max_drawdown']:.2f}%")
            
            # Phân tích theo chiến lược
            strategy_perf = self.performance_monitor.analyze_by_strategy()
            for strategy, perf in strategy_perf.items():
                logger.info(f"Chiến lược {strategy}: Win Rate={perf['win_rate']*100:.2f}%, Profit={perf['net_profit']:.2f}")
            
            # Phân tích theo cặp tiền
            symbol_perf = self.performance_monitor.analyze_by_symbol()
            for symbol, perf in symbol_perf.items():
                logger.info(f"Cặp tiền {symbol}: Win Rate={perf['win_rate']*100:.2f}%, Profit={perf['net_profit']:.2f}")
            
            # Phân tích theo chế độ thị trường
            regime_perf = self.performance_monitor.analyze_by_market_regime()
            for regime, perf in regime_perf.items():
                logger.info(f"Chế độ {regime}: Win Rate={perf['win_rate']*100:.2f}%, Profit={perf['net_profit']:.2f}")
            
            # Tạo báo cáo
            report_path = "test_report.html"
            self.performance_monitor.generate_full_report(report_path)
            logger.info(f"Đã tạo báo cáo tại: {report_path}")
            
            # Vẽ đường cong vốn
            equity_chart = self.performance_monitor.plot_equity_curve("test_equity.png")
            logger.info(f"Đã vẽ đường cong vốn tại: {equity_chart}")
        except Exception as e:
            logger.error(f"❌ Kiểm thử performance monitor failed: {str(e)}")
        
        logger.info("Kết thúc kiểm thử Performance Monitor")
    
    def test_integration(self):
        """Kiểm thử tích hợp tất cả các module"""
        logger.info("Bắt đầu kiểm thử tích hợp")
        
        # Các thông số cơ bản
        symbol = 'BTCUSDT'
        entry_price = 50000
        leverage = 5
        initial_quantity = 0.1
        side = 'LONG'
        timeframe = '1h'
        
        # Sequence: Signal Quality -> Dynamic Leverage -> Open Position -> Trailing Stop -> Close Position -> PnL Calculation -> Performance Monitor
        
        try:
            # 1. Đánh giá chất lượng tín hiệu
            if self.binance_api:
                signal_score, signal_details = self.signal_quality.evaluate_signal_quality(symbol, timeframe)
                logger.info(f"1. Signal Quality: {signal_score:.2f}, Direction: {signal_details['signal_direction']}")
                
                # Chỉ tiếp tục nếu tín hiệu đủ mạnh và đúng hướng
                if signal_score < 50 or signal_details['signal_direction'] != side:
                    logger.warning("Tín hiệu không đủ mạnh hoặc không đúng hướng, sẽ sử dụng giá trị mẫu")
            else:
                logger.warning("Không có API Binance, sẽ sử dụng giá trị mẫu")
                signal_score = 75
                signal_details = {
                    'signal_direction': side,
                    'signal_strength': 'STRONG'
                }
            
            # 2. Tính toán đòn bẩy động
            market_data = self.market_data.copy()
            leverage_result = self.leverage_calculator.calculate_dynamic_leverage(
                market_regime=market_data['market_regime'],
                volatility=market_data['volatility'],
                account_balance=market_data['account_balance'],
                symbol=symbol
            )
            
            dynamic_leverage = leverage_result['final_leverage']
            logger.info(f"2. Dynamic Leverage: {dynamic_leverage}x (Original: {leverage}x)")
            
            # 3. Mở vị thế
            position = {
                'symbol': symbol,
                'side': side,
                'entry_price': entry_price,
                'quantity': initial_quantity,
                'leverage': dynamic_leverage,
                'entry_time': int(time.time()) - 3600  # 1 giờ trước
            }
            
            # 4. Thiết lập trailing stop
            position = self.trailing_stop.initialize_position(position)
            logger.info(f"4. Initialize Position: {position['trailing_status']}")
            
            # 5. Mô phỏng giá thay đổi và trailing stop
            prices = [50100, 50300, 50600, 51000, 51400, 51200, 51000, 50800, 50500]
            exit_price = None
            exit_reason = None
            
            for price in prices:
                # Cập nhật trailing stop
                position = self.trailing_stop.update_trailing_stop(position, price)
                should_close, reason = self.trailing_stop.check_stop_condition(position, price)
                
                status = self.trailing_stop.get_trailing_status(position)
                logger.info(f"Giá: {price}, Stop: {status['stop_price']:.2f if status['stop_price'] else None}, Trạng thái: {status['status']}")
                
                # Kiểm tra thoát một phần
                partial_exit = self.trailing_stop.check_partial_exit(position, price)
                if partial_exit:
                    logger.info(f"Thoát một phần {partial_exit['percentage']*100:.0f}% vị thế ở ngưỡng {partial_exit['threshold']*100:.1f}%, giá: {price}")
                
                if should_close:
                    exit_price = price
                    exit_reason = reason
                    logger.info(f"Đóng vị thế tại giá {price}: {reason}")
                    break
            
            # Nếu không có tín hiệu đóng vị thế, lấy giá cuối cùng
            if exit_price is None:
                exit_price = prices[-1]
                exit_reason = "End of simulation"
                logger.info(f"Đóng vị thế tại giá cuối cùng {exit_price}: {exit_reason}")
            
            # 6. Tính toán PnL
            position['exit_price'] = exit_price
            position['exit_time'] = int(time.time())
            
            # Lấy thông tin thoát một phần
            partial_exits = self.trailing_stop.get_partial_exits(position)
            
            pnl_result = self.pnl_calculator.calculate_pnl_with_full_details(
                entry_price=position['entry_price'],
                exit_price=position['exit_price'],
                position_size=position['quantity'],
                leverage=position['leverage'],
                position_side=position['side'],
                entry_time=position['entry_time'],
                exit_time=position['exit_time'],
                symbol=position['symbol'],
                partial_exits=[(exit_info['price'], exit_info['quantity']) for exit_info in partial_exits] if partial_exits else None
            )
            
            logger.info(f"6. PnL Calculation: {pnl_result['net_pnl']:.2f} ({pnl_result['roi_percent']:.2f}%)")
            
            # 7. Cập nhật Performance Monitor
            trade_record = {
                'trade_id': f"trade_{int(time.time())}",
                'symbol': position['symbol'],
                'side': position['side'],
                'entry_price': position['entry_price'],
                'exit_price': position['exit_price'],
                'quantity': position['quantity'],
                'leverage': position['leverage'],
                'entry_time': position['entry_time'],
                'exit_time': position['exit_time'],
                'strategy': 'adaptive_strategy',
                'market_regime': market_data['market_regime'],
                'net_pnl': pnl_result['net_pnl'],
                'roi_percent': pnl_result['roi_percent'],
                'exit_reason': exit_reason
            }
            
            self.performance_monitor.add_trade(trade_record)
            
            # Tính các chỉ số hiệu suất
            self.performance_monitor.calculate_equity_curve()
            stats = self.performance_monitor.get_trade_statistics()
            
            logger.info(f"7. Performance: Win Rate={stats['win_rate']*100:.2f}%, Net Profit={stats['net_profit']:.2f}")
            
            # 8. Tóm tắt kết quả tích hợp
            logger.info(f"""
            === KẾT QUẢ TÍCH HỢP ===
            Symbol: {symbol}
            Entry Price: {position['entry_price']}
            Exit Price: {position['exit_price']}
            Leverage: {position['leverage']}x (Dynamic)
            Signal Quality: {signal_score:.2f}
            PnL: {pnl_result['net_pnl']:.2f} USDT ({pnl_result['roi_percent']:.2f}%)
            Reason: {exit_reason}
            """)
            
            logger.info("Kiểm thử tích hợp thành công!")
        except Exception as e:
            logger.error(f"❌ Kiểm thử tích hợp failed: {str(e)}")
        
        logger.info("Kết thúc kiểm thử tích hợp")
    
    def run_all_tests(self):
        """Chạy tất cả các kiểm thử"""
        logger.info("=== BẮT ĐẦU KIỂM THỬ TÍCH HỢP CÁC MODULE ===")
        
        # Kiểm thử từng module riêng biệt
        self.test_pnl_calculator()
        self.test_dynamic_leverage()
        self.test_signal_quality()
        self.test_trailing_stop()
        self.test_performance_monitor()
        
        # Kiểm thử tích hợp
        self.test_integration()
        
        logger.info("=== KẾT THÚC KIỂM THỬ TÍCH HỢP CÁC MODULE ===")


def main():
    """Hàm chính"""
    # Tạo và chạy kiểm thử tích hợp
    integration_test = IntegrationTest()
    integration_test.run_all_tests()


if __name__ == "__main__":
    main()