#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script kiểm tra bot giao dịch với dữ liệu thị trường thật

Script này thực hiện việc:
1. Kết nối với Binance API để lấy dữ liệu thị trường thời gian thực
2. Chạy bot giao dịch trong một khoảng thời gian nhất định
3. Ghi nhận đầy đủ các hoạt động và quyết định của bot
4. Tạo báo cáo chi tiết về việc bot vận dụng các thuật toán
"""

import os
import sys
import time
import json
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("real_market_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load môi trường
load_dotenv()

# Import các module cần thiết
from binance_api import BinanceAPI
from market_regime_ml_optimized import AdaptiveTrader, MarketRegimeDetector, StrategySelector
from data_processor import DataProcessor

class RealMarketTester:
    """Lớp kiểm tra bot với dữ liệu thị trường thật"""
    
    def __init__(self, symbols=None, time_frames=None, test_duration_hours=24):
        """
        Khởi tạo tester
        
        Args:
            symbols (list): Danh sách các cặp tiền cần test
            time_frames (list): Danh sách các khung thời gian
            test_duration_hours (int): Thời gian test (giờ)
        """
        self.symbols = symbols or ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        self.time_frames = time_frames or ['1h', '4h', '1d']
        self.test_duration_hours = test_duration_hours
        
        # Khởi tạo các thành phần
        self.api_key = os.environ.get('BINANCE_API_KEY')
        self.api_secret = os.environ.get('BINANCE_API_SECRET')
        
        if not self.api_key or not self.api_secret:
            logger.error("API key hoặc secret không tồn tại. Vui lòng kiểm tra file .env")
            raise ValueError("API key/secret không tồn tại")
            
        self.binance_api = BinanceAPI(api_key=self.api_key, api_secret=self.api_secret, testnet=True)
        self.data_processor = DataProcessor(binance_api=self.binance_api)
        
        # Khởi tạo các bot và bộ phát hiện
        self.regime_detectors = {}
        self.adaptive_traders = {}
        
        for symbol in self.symbols:
            self.regime_detectors[symbol] = MarketRegimeDetector()
            self.adaptive_traders[symbol] = AdaptiveTrader(
                regime_detector=self.regime_detectors[symbol],
                strategy_selector=StrategySelector()
            )
        
        # Dữ liệu lịch sử
        self.historical_data = {}
        
        # Báo cáo kiểm tra
        self.test_reports = {}
        self.algorithm_usage = {}
        self.decisions = {}
        
    def initialize_data(self):
        """Khởi tạo dữ liệu lịch sử"""
        logger.info("Đang tải dữ liệu lịch sử...")
        
        for symbol in self.symbols:
            self.historical_data[symbol] = {}
            
            for timeframe in self.time_frames:
                try:
                    # Tải dữ liệu từ 30 ngày trước
                    start_time = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                    
                    df = self.data_processor.download_historical_data(
                        symbol=symbol,
                        interval=timeframe,
                        start_time=start_time,
                        save_to_file=False
                    )
                    
                    # Thêm các chỉ báo kỹ thuật
                    df = self.data_processor.add_indicators(df)
                    
                    self.historical_data[symbol][timeframe] = df
                    logger.info(f"Đã tải dữ liệu {symbol} {timeframe} ({len(df)} nến)")
                    
                except Exception as e:
                    logger.error(f"Lỗi khi tải dữ liệu {symbol} {timeframe}: {str(e)}")
                    continue
    
    def _initialize_reports(self):
        """Khởi tạo cấu trúc báo cáo"""
        for symbol in self.symbols:
            self.test_reports[symbol] = {
                'market_regimes': [],
                'signals': [],
                'decisions': [],
                'performance': {}
            }
            
            self.algorithm_usage[symbol] = {
                'regime_detection_counts': {},
                'strategy_usage_counts': {},
                'indicators_usage': {}
            }
    
    def update_market_data(self):
        """Cập nhật dữ liệu thị trường trong thời gian thực"""
        for symbol in self.symbols:
            for timeframe in self.time_frames:
                try:
                    # Lấy nến mới nhất
                    new_candles = self.binance_api.get_klines(
                        symbol=symbol,
                        interval=timeframe,
                        limit=5  # Chỉ lấy 5 nến gần nhất
                    )
                    
                    if not new_candles:
                        logger.warning(f"Không có dữ liệu mới cho {symbol} {timeframe}")
                        continue
                    
                    # Chuyển đổi thành DataFrame
                    new_df = self.binance_api.convert_klines_to_dataframe(new_candles)
                    
                    # Cập nhật dữ liệu lịch sử
                    df = self.historical_data[symbol][timeframe]
                    
                    # Loại bỏ các nến trùng lặp và thêm nến mới
                    df = pd.concat([df, new_df]).drop_duplicates(subset=['timestamp']).sort_values('timestamp')
                    
                    # Thêm các chỉ báo kỹ thuật
                    df = self.data_processor.add_indicators(df)
                    
                    # Cập nhật lại dữ liệu
                    self.historical_data[symbol][timeframe] = df
                    
                    logger.info(f"Đã cập nhật dữ liệu {symbol} {timeframe} - Nến mới nhất: {df.index[-1]}")
                    
                except Exception as e:
                    logger.error(f"Lỗi khi cập nhật dữ liệu {symbol} {timeframe}: {str(e)}")
                    continue
    
    def run_bot_iteration(self):
        """Chạy một vòng lặp của bot"""
        for symbol in self.symbols:
            try:
                # Lấy dữ liệu khung thời gian chính (1h)
                primary_tf = '1h'
                df = self.historical_data[symbol][primary_tf]
                
                if df.empty:
                    logger.warning(f"Không có dữ liệu cho {symbol} {primary_tf}")
                    continue
                
                # Phát hiện chế độ thị trường
                regime_detector = self.regime_detectors[symbol]
                current_regime = regime_detector.detect_regime(df)
                
                # Lấy tín hiệu giao dịch thích ứng
                adaptive_trader = self.adaptive_traders[symbol]
                signal = adaptive_trader.generate_signal(df)
                
                # Ghi nhận thông tin
                timestamp = datetime.now()
                
                # Lấy thông tin về các chiến lược được sử dụng
                strategy_info = {}
                if hasattr(adaptive_trader, 'current_strategy') and adaptive_trader.current_strategy:
                    if hasattr(adaptive_trader.current_strategy, 'strategies'):
                        strategy_info = {
                            name: {
                                'weight': adaptive_trader.current_strategy.strategy_weights.get(name, 0),
                                'signal': strategy.generate_signal(df) if hasattr(strategy, 'generate_signal') else 0
                            }
                            for name, strategy in adaptive_trader.current_strategy.strategies.items()
                        }
                
                # Ghi nhận sử dụng thuật toán
                self._record_algorithm_usage(symbol, current_regime, strategy_info, df)
                
                # Ghi nhận quyết định
                decision_record = {
                    'timestamp': timestamp,
                    'regime': current_regime,
                    'signal': signal,
                    'price': df['close'].iloc[-1] if not df.empty else None,
                    'strategies_used': strategy_info,
                    'indicators': {
                        'rsi': df['rsi'].iloc[-1] if 'rsi' in df.columns else None,
                        'macd': df['macd'].iloc[-1] if 'macd' in df.columns else None,
                        'bb_width': ((df['bb_upper'].iloc[-1] - df['bb_lower'].iloc[-1]) / df['bb_middle'].iloc[-1]) 
                                     if all(x in df.columns for x in ['bb_upper', 'bb_lower', 'bb_middle']) else None
                    }
                }
                
                self.test_reports[symbol]['decisions'].append(decision_record)
                logger.info(f"{symbol}: Chế độ: {current_regime}, Tín hiệu: {signal['action'] if isinstance(signal, dict) else signal}")
                
            except Exception as e:
                logger.error(f"Lỗi khi chạy bot cho {symbol}: {str(e)}")
                continue
    
    def _record_algorithm_usage(self, symbol, regime, strategy_info, df):
        """Ghi nhận việc sử dụng thuật toán"""
        # Đếm số lần phát hiện mỗi chế độ thị trường
        if regime in self.algorithm_usage[symbol]['regime_detection_counts']:
            self.algorithm_usage[symbol]['regime_detection_counts'][regime] += 1
        else:
            self.algorithm_usage[symbol]['regime_detection_counts'][regime] = 1
        
        # Đếm số lần sử dụng mỗi chiến lược
        for strategy_name in strategy_info:
            if strategy_name in self.algorithm_usage[symbol]['strategy_usage_counts']:
                self.algorithm_usage[symbol]['strategy_usage_counts'][strategy_name] += 1
            else:
                self.algorithm_usage[symbol]['strategy_usage_counts'][strategy_name] = 1
        
        # Ghi nhận các chỉ báo được sử dụng
        indicators_used = []
        
        # Kiểm tra RSI
        if 'rsi' in df.columns and not df['rsi'].isna().all():
            indicators_used.append('rsi')
            
        # Kiểm tra MACD
        if all(x in df.columns for x in ['macd', 'macd_signal']) and not df['macd'].isna().all():
            indicators_used.append('macd')
            
        # Kiểm tra Bollinger Bands
        if all(x in df.columns for x in ['bb_upper', 'bb_lower', 'bb_middle']) and not df['bb_upper'].isna().all():
            indicators_used.append('bbands')
            
        # Kiểm tra EMA
        ema_columns = [col for col in df.columns if col.startswith('ema_')]
        if ema_columns and not all(df[col].isna().all() for col in ema_columns):
            indicators_used.append('ema')
            
        # Kiểm tra ADX
        if all(x in df.columns for x in ['adx', 'plus_di', 'minus_di']) and not df['adx'].isna().all():
            indicators_used.append('adx')
            
        # Kiểm tra ATR
        if 'atr' in df.columns and not df['atr'].isna().all():
            indicators_used.append('atr')
        
        for indicator in indicators_used:
            if indicator in self.algorithm_usage[symbol]['indicators_usage']:
                self.algorithm_usage[symbol]['indicators_usage'][indicator] += 1
            else:
                self.algorithm_usage[symbol]['indicators_usage'][indicator] = 1
    
    def run_test(self):
        """Chạy kiểm tra thị trường thật"""
        logger.info(f"Bắt đầu kiểm tra thị trường thật (thời lượng: {self.test_duration_hours} giờ)")
        
        # Khởi tạo dữ liệu
        self.initialize_data()
        
        # Khởi tạo báo cáo
        self._initialize_reports()
        
        # Tính thời điểm kết thúc
        end_time = datetime.now() + timedelta(hours=self.test_duration_hours)
        
        # Vòng lặp chính
        try:
            while datetime.now() < end_time:
                # Cập nhật dữ liệu thị trường
                self.update_market_data()
                
                # Chạy một vòng lặp của bot
                self.run_bot_iteration()
                
                # Tạo báo cáo tạm thời mỗi giờ
                current_hour = datetime.now().hour
                if hasattr(self, 'last_report_hour') and self.last_report_hour != current_hour:
                    self.generate_interim_report()
                
                self.last_report_hour = current_hour
                
                # Chờ một khoảng thời gian trước khi lặp lại
                logger.info("Hoàn thành vòng lặp. Chờ 5 phút trước khi cập nhật.")
                time.sleep(300)  # 5 phút
                
        except KeyboardInterrupt:
            logger.info("Kiểm tra bị ngắt bởi người dùng")
        except Exception as e:
            logger.error(f"Lỗi không xác định: {str(e)}")
        finally:
            # Tạo báo cáo cuối cùng
            self.generate_final_report()
    
    def generate_interim_report(self):
        """Tạo báo cáo tạm thời"""
        report_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"reports/interim_report_{report_time}.json"
        
        # Đảm bảo thư mục tồn tại
        os.makedirs("reports", exist_ok=True)
        
        # Lưu báo cáo dưới dạng JSON
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                # Chuyển đổi timestamp thành string để có thể serialize
                serializable_reports = self._make_json_serializable(self.test_reports)
                json.dump(serializable_reports, f, indent=4, ensure_ascii=False)
                
            logger.info(f"Đã tạo báo cáo tạm thời: {report_path}")
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo tạm thời: {str(e)}")
    
    def _make_json_serializable(self, obj):
        """Chuyển đổi đối tượng phức tạp thành dạng có thể serialize JSON"""
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, (datetime, pd.Timestamp)):
            return obj.isoformat()
        elif isinstance(obj, (np.int64, np.int32, np.float64, np.float32)):
            return obj.item()
        elif pd.isna(obj):
            return None
        return obj
    
    def generate_final_report(self):
        """Tạo báo cáo cuối cùng"""
        report_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Đảm bảo thư mục tồn tại
        os.makedirs("reports", exist_ok=True)
        
        # Tạo báo cáo chi tiết
        detailed_report = {
            "test_summary": {
                "start_time": self.test_reports[self.symbols[0]]['decisions'][0]['timestamp'] if self.test_reports[self.symbols[0]]['decisions'] else None,
                "end_time": datetime.now(),
                "duration_hours": self.test_duration_hours,
                "symbols_tested": self.symbols,
                "timeframes": self.time_frames
            },
            "algorithm_usage": self.algorithm_usage,
            "detailed_reports": self.test_reports
        }
        
        # Tạo báo cáo tổng quan
        overview_report = self._generate_overview_report()
        
        # Lưu báo cáo chi tiết
        detailed_report_path = f"reports/detailed_report_{report_time}.json"
        try:
            with open(detailed_report_path, 'w', encoding='utf-8') as f:
                serializable_report = self._make_json_serializable(detailed_report)
                json.dump(serializable_report, f, indent=4, ensure_ascii=False)
                
            logger.info(f"Đã tạo báo cáo chi tiết: {detailed_report_path}")
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo chi tiết: {str(e)}")
        
        # Lưu báo cáo tổng quan
        overview_report_path = f"reports/overview_report_{report_time}.txt"
        try:
            with open(overview_report_path, 'w', encoding='utf-8') as f:
                f.write(overview_report)
                
            logger.info(f"Đã tạo báo cáo tổng quan: {overview_report_path}")
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo tổng quan: {str(e)}")
    
    def _generate_overview_report(self):
        """Tạo báo cáo tổng quan dạng văn bản"""
        report = []
        report.append("="*80)
        report.append(f"BÁO CÁO TỔNG QUAN - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("="*80)
        report.append(f"Thời gian test: {self.test_duration_hours} giờ")
        report.append(f"Các cặp tiền được test: {', '.join(self.symbols)}")
        report.append(f"Các khung thời gian: {', '.join(self.time_frames)}")
        report.append("")
        
        for symbol in self.symbols:
            report.append(f"--- {symbol} ---")
            
            # Thống kê chế độ thị trường
            report.append("\nChế độ thị trường phát hiện:")
            for regime, count in self.algorithm_usage[symbol]['regime_detection_counts'].items():
                report.append(f"  - {regime}: {count} lần")
            
            # Thống kê sử dụng chiến lược
            report.append("\nChiến lược được sử dụng:")
            for strategy, count in self.algorithm_usage[symbol]['strategy_usage_counts'].items():
                report.append(f"  - {strategy}: {count} lần")
            
            # Thống kê sử dụng chỉ báo
            report.append("\nChỉ báo kỹ thuật được sử dụng:")
            for indicator, count in self.algorithm_usage[symbol]['indicators_usage'].items():
                report.append(f"  - {indicator}: {count} lần")
            
            # Thống kê tín hiệu
            decisions = self.test_reports[symbol]['decisions']
            if decisions:
                signals = [d['signal'] for d in decisions]
                if isinstance(signals[0], dict) and 'action' in signals[0]:
                    signal_counts = {}
                    for s in signals:
                        action = s['action']
                        signal_counts[action] = signal_counts.get(action, 0) + 1
                    
                    report.append("\nTín hiệu giao dịch:")
                    for action, count in signal_counts.items():
                        report.append(f"  - {action}: {count} lần")
            
            report.append("\n" + "-"*40)
        
        report.append("\n## PHÂN TÍCH VẬN DỤNG THUẬT TOÁN ##")
        
        # Đánh giá tổng quát về việc vận dụng thuật toán
        all_indicators = set()
        all_strategies = set()
        all_regimes = set()
        
        for symbol in self.symbols:
            all_indicators.update(self.algorithm_usage[symbol]['indicators_usage'].keys())
            all_strategies.update(self.algorithm_usage[symbol]['strategy_usage_counts'].keys())
            all_regimes.update(self.algorithm_usage[symbol]['regime_detection_counts'].keys())
        
        # Đánh giá phát hiện chế độ thị trường
        report.append("\n1. Phát hiện chế độ thị trường:")
        
        if len(all_regimes) >= 3:
            report.append("   ✓ Bot đã phát hiện đa dạng các chế độ thị trường")
        else:
            report.append("   ✗ Bot chưa phát hiện đủ các chế độ thị trường")
        
        # Đánh giá sử dụng chiến lược
        report.append("\n2. Sử dụng chiến lược giao dịch:")
        
        if len(all_strategies) >= 3:
            report.append("   ✓ Bot đã vận dụng đa dạng các chiến lược giao dịch")
        else:
            report.append("   ✗ Bot chưa vận dụng đa dạng các chiến lược giao dịch")
            
        # Đánh giá chiến lược BBands trong thị trường yên tĩnh
        has_quiet_market = any('quiet' in self.algorithm_usage[symbol]['regime_detection_counts'] 
                               for symbol in self.symbols)
        bbands_used = any('bbands' in self.algorithm_usage[symbol]['indicators_usage'] 
                          for symbol in self.symbols)
        
        report.append("\n3. Hiệu quả của chiến lược BBands trong thị trường yên tĩnh:")
        
        if has_quiet_market and bbands_used:
            report.append("   ✓ Bot đã vận dụng chiến lược BBands trong thị trường yên tĩnh")
        elif has_quiet_market and not bbands_used:
            report.append("   ✗ Bot đã phát hiện thị trường yên tĩnh nhưng không vận dụng chiến lược BBands")
        else:
            report.append("   ? Chưa có cơ hội đánh giá do không phát hiện thị trường yên tĩnh")
        
        # Đánh giá sử dụng chỉ báo
        report.append("\n4. Sử dụng chỉ báo kỹ thuật:")
        
        expected_indicators = {'rsi', 'macd', 'bbands', 'ema', 'adx', 'atr'}
        used_indicators = all_indicators
        
        missing_indicators = expected_indicators - used_indicators
        
        if not missing_indicators:
            report.append("   ✓ Bot đã vận dụng tất cả các chỉ báo kỹ thuật như thiết kế")
        else:
            report.append(f"   ✗ Bot chưa vận dụng các chỉ báo: {', '.join(missing_indicators)}")
        
        report.append("\n5. Tình trạng kỹ thuật và lỗi:")
        
        # TODO: Kiểm tra log để tìm lỗi
        
        report.append("\n" + "="*80)
        return "\n".join(report)

if __name__ == "__main__":
    # Kiểm tra tham số dòng lệnh
    import argparse
    
    parser = argparse.ArgumentParser(description='Kiểm tra bot với dữ liệu thị trường thật')
    parser.add_argument('--duration', type=int, default=6, help='Thời lượng test (giờ)')
    parser.add_argument('--symbols', type=str, default='BTCUSDT,ETHUSDT', help='Các cặp tiền cần test (phân cách bằng dấu phẩy)')
    parser.add_argument('--timeframes', type=str, default='1h,4h', help='Các khung thời gian (phân cách bằng dấu phẩy)')
    
    args = parser.parse_args()
    
    symbols = args.symbols.split(',')
    timeframes = args.timeframes.split(',')
    
    tester = RealMarketTester(
        symbols=symbols,
        time_frames=timeframes,
        test_duration_hours=args.duration
    )
    
    tester.run_test()