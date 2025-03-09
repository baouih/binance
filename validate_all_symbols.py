"""
Validate All Symbols - Kiểm tra tất cả các cặp tiền tệ trước khi chạy hệ thống

Script này sẽ tự động kiểm tra tất cả các cặp tiền tệ có dữ liệu 3 tháng,
kiểm tra tính toàn vẹn dữ liệu, và kiểm tra các module mới như Order Flow,
Volume Profile, Adaptive Exit Strategy, và Partial Take Profit Manager.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import glob
from typing import Dict, List, Tuple, Any, Optional, Union
import traceback
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('validate_symbols.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('validate_symbols')

# Import các module tự tạo
try:
    from order_flow_indicators import OrderFlowAnalyzer
    from volume_profile_analyzer import VolumeProfileAnalyzer
    from adaptive_exit_strategy import AdaptiveExitStrategy
    from partial_take_profit_manager import PartialTakeProfitManager
    from enhanced_market_regime_detector import EnhancedMarketRegimeDetector
    
    # Các module khác nếu cần
    from binance_api import BinanceAPI
except ImportError as e:
    logger.error(f"Lỗi import module: {str(e)}")
    logger.error(traceback.format_exc())
    sys.exit(1)

class SymbolValidator:
    """
    Lớp kiểm tra tất cả các cặp tiền tệ và module mới.
    """
    
    def __init__(self, 
                data_dir: str = 'data', 
                output_dir: str = 'validation_results',
                min_data_months: int = 3,
                symbols_filter: List[str] = None):
        """
        Khởi tạo SymbolValidator.
        
        Args:
            data_dir (str): Thư mục chứa dữ liệu
            output_dir (str): Thư mục lưu kết quả kiểm tra
            min_data_months (int): Số tháng dữ liệu tối thiểu
            symbols_filter (List[str], optional): Danh sách các cặp tiền cần kiểm tra
        """
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.min_data_months = min_data_months
        self.symbols_filter = symbols_filter
        
        # Tạo thư mục output nếu chưa tồn tại
        os.makedirs(output_dir, exist_ok=True)
        
        # Khởi tạo các module cần kiểm tra
        self.order_flow = OrderFlowAnalyzer()
        self.volume_profile = VolumeProfileAnalyzer()
        self.exit_strategy = AdaptiveExitStrategy()
        self.tp_manager = PartialTakeProfitManager()
        self.regime_detector = EnhancedMarketRegimeDetector()
        
        # Lưu trữ kết quả kiểm tra
        self.validation_results = {}
        self.available_symbols = []
        self.error_symbols = []
        
        # Trạng thái
        self.start_time = datetime.now()
    
    def find_available_symbols(self) -> List[str]:
        """
        Tìm tất cả các cặp tiền có dữ liệu đủ số tháng yêu cầu.
        
        Returns:
            List[str]: Danh sách các cặp tiền
        """
        try:
            logger.info(f"Đang tìm các cặp tiền có đủ {self.min_data_months} tháng dữ liệu...")
            
            all_symbols = []
            today = datetime.now()
            min_date = today - timedelta(days=self.min_data_months * 30)
            
            # Tìm tất cả các file dữ liệu
            data_files = glob.glob(os.path.join(self.data_dir, '**/*.csv'), recursive=True)
            
            # Tìm tất cả các thư mục con trong data_dir
            for root, dirs, files in os.walk(self.data_dir):
                for file in files:
                    if file.endswith('.csv'):
                        # Trích xuất symbol từ tên file
                        full_path = os.path.join(root, file)
                        symbol = self._extract_symbol_from_filename(file)
                        
                        if symbol:
                            # Kiểm tra xem dữ liệu có đủ lâu không
                            df = pd.read_csv(full_path, nrows=5)  # Chỉ đọc 5 dòng đầu để kiểm tra ngày
                            
                            if 'timestamp' in df.columns or 'time' in df.columns or 'date' in df.columns:
                                date_col = 'timestamp' if 'timestamp' in df.columns else ('time' if 'time' in df.columns else 'date')
                                try:
                                    # Kiểm tra ngày đầu tiên
                                    first_date = pd.to_datetime(df[date_col].iloc[0])
                                    
                                    if first_date <= min_date:
                                        all_symbols.append(symbol)
                                except:
                                    # Nếu không thể parse ngày, thử đọc toàn bộ file để lấy thống kê
                                    full_df = pd.read_csv(full_path)
                                    
                                    if len(full_df) >= 90 * 24:  # 90 ngày x 24 giờ (giả định dữ liệu giờ)
                                        all_symbols.append(symbol)
            
            # Loại bỏ trùng lặp
            all_symbols = list(set(all_symbols))
            
            # Lọc theo danh sách nếu có
            if self.symbols_filter:
                all_symbols = [s for s in all_symbols if s in self.symbols_filter]
            
            logger.info(f"Tìm thấy {len(all_symbols)} cặp tiền có đủ dữ liệu: {all_symbols}")
            
            self.available_symbols = all_symbols
            return all_symbols
            
        except Exception as e:
            logger.error(f"Lỗi khi tìm các cặp tiền: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    def load_symbol_data(self, symbol: str, timeframe: str = '1h', limit: int = 2000) -> pd.DataFrame:
        """
        Tải dữ liệu cho một cặp tiền.
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            limit (int): Số lượng nến tối đa
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu
        """
        try:
            # Tìm file dữ liệu
            potential_paths = [
                os.path.join(self.data_dir, f"{symbol}_{timeframe}.csv"),
                os.path.join(self.data_dir, f"{symbol.lower()}_{timeframe}.csv"),
                os.path.join(self.data_dir, symbol, f"{timeframe}.csv"),
                os.path.join(self.data_dir, 'klines', symbol, f"{timeframe}.csv"),
                os.path.join(self.data_dir, 'historical', symbol, f"{timeframe}.csv")
            ]
            
            data_file = None
            for path in potential_paths:
                if os.path.exists(path):
                    data_file = path
                    break
            
            if not data_file:
                logger.warning(f"Không tìm thấy dữ liệu cho {symbol} với timeframe {timeframe}")
                return None
            
            # Đọc dữ liệu
            df = pd.read_csv(data_file)
            
            # Chuẩn hóa tên cột
            column_mapping = {
                'timestamp': 'timestamp',
                'time': 'timestamp',
                'date': 'timestamp',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            }
            
            # Đổi tên cột nếu cần
            df = df.rename(columns={col: std_col for col, std_col in column_mapping.items() if col in df.columns})
            
            # Đảm bảo có đủ các cột cần thiết
            required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                logger.warning(f"Thiếu các cột {missing_columns} trong dữ liệu {symbol}")
                return None
            
            # Chuyển đổi timestamp sang datetime nếu cần
            if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                try:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                except:
                    # Nếu không chuyển được, có thể là timestamp dạng số, thử cách khác
                    try:
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    except:
                        logger.warning(f"Không thể chuyển đổi timestamp sang datetime cho {symbol}")
                        return None
            
            # Đặt làm index
            df = df.set_index('timestamp')
            
            # Sắp xếp theo thời gian
            df = df.sort_index()
            
            # Giới hạn số lượng
            if len(df) > limit:
                df = df.iloc[-limit:]
            
            # Chuyển đổi các cột số
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            logger.info(f"Đã tải thành công dữ liệu {symbol} với {len(df)} nến")
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu {symbol}: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def validate_symbol(self, symbol: str) -> Dict:
        """
        Kiểm tra một cặp tiền.
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            Dict: Kết quả kiểm tra
        """
        try:
            logger.info(f"Đang kiểm tra {symbol}...")
            
            result = {
                'symbol': symbol,
                'status': 'success',
                'data_quality': {},
                'modules': {},
                'errors': [],
                'warnings': [],
                'execution_time': 0
            }
            
            start_time = time.time()
            
            # Tải dữ liệu
            df = self.load_symbol_data(symbol)
            
            if df is None or df.empty:
                result['status'] = 'error'
                result['errors'].append('Không thể tải dữ liệu hoặc dữ liệu rỗng')
                return result
            
            # Kiểm tra chất lượng dữ liệu
            result['data_quality'] = self._check_data_quality(df)
            
            if result['data_quality']['missing_data_pct'] > 10:
                result['status'] = 'warning'
                result['warnings'].append(f"Dữ liệu thiếu nhiều ({result['data_quality']['missing_data_pct']:.2f}%)")
            
            # Tạo fake position data cho việc kiểm tra
            current_price = df['close'].iloc[-1]
            position_data = {
                'symbol': symbol,
                'position_id': 'test_validation',
                'position_type': 'long',
                'entry_price': current_price * 0.98,  # Giả định vào lệnh ở giá thấp hơn 2%
                'current_price': current_price,
                'position_size': 0.1,
                'unrealized_pnl_pct': 2.0,
                'entry_time': (datetime.now() - timedelta(hours=5)).isoformat()
            }
            
            # Kiểm tra các module
            module_results = {}
            
            # 1. Kiểm tra Order Flow
            try:
                of_result = self._validate_order_flow(df)
                module_results['order_flow'] = of_result
            except Exception as e:
                logger.error(f"Lỗi khi kiểm tra Order Flow cho {symbol}: {str(e)}")
                logger.error(traceback.format_exc())
                module_results['order_flow'] = {'status': 'error', 'error': str(e)}
            
            # 2. Kiểm tra Volume Profile
            try:
                vp_result = self._validate_volume_profile(df)
                module_results['volume_profile'] = vp_result
            except Exception as e:
                logger.error(f"Lỗi khi kiểm tra Volume Profile cho {symbol}: {str(e)}")
                logger.error(traceback.format_exc())
                module_results['volume_profile'] = {'status': 'error', 'error': str(e)}
            
            # 3. Kiểm tra Adaptive Exit Strategy
            try:
                exit_result = self._validate_exit_strategy(df, position_data)
                module_results['exit_strategy'] = exit_result
            except Exception as e:
                logger.error(f"Lỗi khi kiểm tra Exit Strategy cho {symbol}: {str(e)}")
                logger.error(traceback.format_exc())
                module_results['exit_strategy'] = {'status': 'error', 'error': str(e)}
            
            # 4. Kiểm tra Partial Take Profit Manager
            try:
                tp_result = self._validate_tp_manager(df, position_data)
                module_results['tp_manager'] = tp_result
            except Exception as e:
                logger.error(f"Lỗi khi kiểm tra TP Manager cho {symbol}: {str(e)}")
                logger.error(traceback.format_exc())
                module_results['tp_manager'] = {'status': 'error', 'error': str(e)}
            
            # 5. Kiểm tra Market Regime Detector
            try:
                regime_result = self._validate_regime_detector(df)
                module_results['regime_detector'] = regime_result
            except Exception as e:
                logger.error(f"Lỗi khi kiểm tra Regime Detector cho {symbol}: {str(e)}")
                logger.error(traceback.format_exc())
                module_results['regime_detector'] = {'status': 'error', 'error': str(e)}
            
            # Tổng hợp kết quả kiểm tra module
            result['modules'] = module_results
            
            # Kiểm tra tổng thể
            module_errors = [module for module, res in module_results.items() if res.get('status') == 'error']
            
            if module_errors:
                if len(module_errors) > 2:  # Nếu có từ 3 module lỗi trở lên
                    result['status'] = 'error'
                    result['errors'].append(f"Nhiều module lỗi: {', '.join(module_errors)}")
                else:
                    result['status'] = 'warning'
                    result['warnings'].append(f"Một số module lỗi: {', '.join(module_errors)}")
            
            # Tính thời gian thực thi
            result['execution_time'] = time.time() - start_time
            
            # Lưu vào kết quả
            self.validation_results[symbol] = result
            
            # Lưu vào danh sách lỗi nếu cần
            if result['status'] == 'error':
                self.error_symbols.append(symbol)
            
            logger.info(f"Đã kiểm tra xong {symbol} với kết quả: {result['status']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra {symbol}: {str(e)}")
            logger.error(traceback.format_exc())
            
            result = {
                'symbol': symbol,
                'status': 'error',
                'errors': [str(e)],
                'execution_time': time.time() - start_time
            }
            
            self.validation_results[symbol] = result
            self.error_symbols.append(symbol)
            
            return result
    
    def validate_all_symbols(self, max_workers: int = 4) -> Dict:
        """
        Kiểm tra tất cả các cặp tiền.
        
        Args:
            max_workers (int): Số lượng worker tối đa
            
        Returns:
            Dict: Kết quả kiểm tra
        """
        logger.info("Bắt đầu quá trình kiểm tra tất cả các cặp tiền...")
        
        # Tìm các cặp tiền
        symbols = self.find_available_symbols()
        
        if not symbols:
            logger.warning("Không tìm thấy cặp tiền nào để kiểm tra")
            return {}
        
        # Kiểm tra từng cặp tiền sử dụng ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit tất cả các job
            future_to_symbol = {executor.submit(self.validate_symbol, symbol): symbol for symbol in symbols}
            
            # Thu thập kết quả
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    logger.info(f"Kết quả kiểm tra {symbol}: {result['status']}")
                except Exception as e:
                    logger.error(f"Lỗi khi kiểm tra {symbol}: {str(e)}")
                    logger.error(traceback.format_exc())
        
        # Tạo báo cáo tổng hợp
        self._generate_summary_report()
        
        # Phân tích kết quả
        success_count = sum(1 for result in self.validation_results.values() if result['status'] == 'success')
        warning_count = sum(1 for result in self.validation_results.values() if result['status'] == 'warning')
        error_count = sum(1 for result in self.validation_results.values() if result['status'] == 'error')
        
        logger.info(f"Kết quả kiểm tra tổng thể:")
        logger.info(f"- Thành công: {success_count}/{len(symbols)} ({success_count/len(symbols)*100:.2f}%)")
        logger.info(f"- Cảnh báo: {warning_count}/{len(symbols)} ({warning_count/len(symbols)*100:.2f}%)")
        logger.info(f"- Lỗi: {error_count}/{len(symbols)} ({error_count/len(symbols)*100:.2f}%)")
        
        if error_count > 0:
            logger.warning(f"Các cặp tiền lỗi: {self.error_symbols}")
        
        return self.validation_results
    
    def _check_data_quality(self, df: pd.DataFrame) -> Dict:
        """
        Kiểm tra chất lượng dữ liệu.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu
            
        Returns:
            Dict: Kết quả kiểm tra chất lượng
        """
        result = {}
        
        # Tính số lượng dữ liệu
        result['data_points'] = len(df)
        
        # Kiểm tra dữ liệu thiếu
        missing_values = df.isnull().sum().sum()
        result['missing_values'] = missing_values
        result['missing_data_pct'] = (missing_values / (len(df) * len(df.columns))) * 100 if len(df) > 0 else 0
        
        # Kiểm tra giá âm
        negative_prices = (df[['open', 'high', 'low', 'close']] <= 0).any(axis=1).sum()
        result['negative_prices'] = negative_prices
        
        # Kiểm tra khối lượng âm
        negative_volume = (df['volume'] <= 0).sum()
        result['negative_volume'] = negative_volume
        
        # Kiểm tra khoảng thời gian
        if isinstance(df.index, pd.DatetimeIndex):
            result['date_range'] = {
                'start': df.index.min().isoformat(),
                'end': df.index.max().isoformat(),
                'days': (df.index.max() - df.index.min()).days
            }
        
        # Kiểm tra các giá trị bất thường
        price_std = df['close'].std()
        price_mean = df['close'].mean()
        price_outliers = ((df['close'] - price_mean).abs() > 3 * price_std).sum()
        result['price_outliers'] = price_outliers
        
        # Tính biến động giá
        if len(df) > 1:
            price_volatility = df['close'].pct_change().std() * 100  # as percentage
            result['price_volatility'] = price_volatility
        
        return result
    
    def _validate_order_flow(self, df: pd.DataFrame) -> Dict:
        """
        Kiểm tra Order Flow Indicators.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu
            
        Returns:
            Dict: Kết quả kiểm tra
        """
        result = {
            'status': 'success',
            'indicators': {},
            'signals': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            # Tính toán Order Flow Indicators
            enhanced_df = self.order_flow.calculate_order_flow_indicators(df)
            
            # Kiểm tra các chỉ báo đã được thêm
            expected_indicators = ['Delta_Volume', 'Cumulative_Delta_Volume', 'Money_Flow_Volume', 'AD_Line']
            
            for indicator in expected_indicators:
                indicator_exists = indicator in enhanced_df.columns
                result['indicators'][indicator] = indicator_exists
                
                if not indicator_exists:
                    result['warnings'].append(f"Chỉ báo {indicator} không được tạo")
            
            # Tạo tín hiệu
            signals = self.order_flow.get_order_flow_signals(enhanced_df)
            
            # Kiểm tra tín hiệu
            result['signals'] = {
                'buy_signals': len(signals.get('buy_signals', [])),
                'sell_signals': len(signals.get('sell_signals', [])),
                'overall_bias': signals.get('overall_bias', 'unknown')
            }
            
            # Tạo biểu đồ để kiểm tra
            try:
                chart_path = self.order_flow.visualize_order_flow(enhanced_df, n_periods=50)
                result['chart_path'] = chart_path
            except Exception as e:
                result['warnings'].append(f"Không thể tạo biểu đồ: {str(e)}")
        
        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(str(e))
        
        return result
    
    def _validate_volume_profile(self, df: pd.DataFrame) -> Dict:
        """
        Kiểm tra Volume Profile Analyzer.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu
            
        Returns:
            Dict: Kết quả kiểm tra
        """
        result = {
            'status': 'success',
            'profile': {},
            'support_resistance': {},
            'patterns': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            # Tính Volume Profile
            profile = self.volume_profile.calculate_volume_profile(df, lookback_periods=50)
            
            # Kiểm tra kết quả
            if not profile:
                result['status'] = 'warning'
                result['warnings'].append("Không thể tính Volume Profile")
            else:
                result['profile'] = {
                    'poc': profile.get('poc'),
                    'value_area': profile.get('value_area'),
                    'secondary_pocs_count': len(profile.get('secondary_pocs', [])),
                    'total_volume': profile.get('total_volume')
                }
            
            # Tìm vùng hỗ trợ/kháng cự
            sr_zones = self.volume_profile.find_support_resistance_zones(df)
            
            if not sr_zones:
                result['warnings'].append("Không thể tính vùng hỗ trợ/kháng cự")
            else:
                result['support_resistance'] = {
                    'support_count': len(sr_zones.get('support_zones', [])),
                    'resistance_count': len(sr_zones.get('resistance_zones', [])),
                    'current_price': sr_zones.get('current_price')
                }
            
            # Phân tích mẫu hình Volume
            patterns = self.volume_profile.analyze_volume_patterns(df)
            
            if patterns:
                result['patterns'] = {
                    'count': len(patterns.get('patterns', [])),
                    'average_volume': patterns.get('average_volume'),
                    'latest_volume': patterns.get('latest_volume')
                }
            
            # Tạo biểu đồ để kiểm tra
            try:
                chart_path = self.volume_profile.visualize_volume_profile(df, lookback_periods=50)
                result['chart_path'] = chart_path
            except Exception as e:
                result['warnings'].append(f"Không thể tạo biểu đồ: {str(e)}")
        
        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(str(e))
        
        return result
    
    def _validate_exit_strategy(self, df: pd.DataFrame, position_data: Dict) -> Dict:
        """
        Kiểm tra Adaptive Exit Strategy.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu
            position_data (Dict): Thông tin vị thế
            
        Returns:
            Dict: Kết quả kiểm tra
        """
        result = {
            'status': 'success',
            'strategy': {},
            'exit_points': {},
            'exit_signal': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            # Xác định chiến lược thoát lệnh
            strategy = self.exit_strategy.determine_exit_strategy(df, position_data)
            
            # Kiểm tra kết quả
            if not strategy:
                result['status'] = 'warning'
                result['warnings'].append("Không thể xác định chiến lược thoát lệnh")
            else:
                result['strategy'] = {
                    'regime': strategy.get('regime'),
                    'active_strategies': strategy.get('active_strategies'),
                    'strategy_scores': strategy.get('strategy_scores')
                }
            
            # Tính toán các điểm thoát
            exit_points = self.exit_strategy.calculate_exit_points(df, position_data, strategy)
            
            if not exit_points:
                result['warnings'].append("Không thể tính toán điểm thoát lệnh")
            else:
                result['exit_points'] = {
                    'stop_loss': exit_points.get('stop_loss', {}).get('price') if exit_points.get('stop_loss') else None,
                    'take_profit': exit_points.get('take_profit', {}).get('price') if exit_points.get('take_profit') else None,
                    'trailing_stop': exit_points.get('trailing_stop', {}).get('price') if exit_points.get('trailing_stop') else None,
                    'partial_take_profits_count': len(exit_points.get('partial_take_profits', [])),
                    'indicator_exits_count': len(exit_points.get('indicator_exits', [])),
                    'risk_reward_ratio': exit_points.get('risk_reward_ratio')
                }
            
            # Lấy tín hiệu thoát lệnh
            exit_signal = self.exit_strategy.get_exit_signal(df, position_data)
            
            result['exit_signal'] = {
                'exit_signal': exit_signal.get('exit_signal'),
                'exit_type': exit_signal.get('exit_type'),
                'exit_price': exit_signal.get('exit_price'),
                'exit_reason': exit_signal.get('exit_reason'),
                'confidence': exit_signal.get('confidence')
            }
            
            # Tạo biểu đồ để kiểm tra
            try:
                chart_path = self.exit_strategy.visualize_exit_points(df, position_data, exit_points)
                result['chart_path'] = chart_path
            except Exception as e:
                result['warnings'].append(f"Không thể tạo biểu đồ: {str(e)}")
        
        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(str(e))
        
        return result
    
    def _validate_tp_manager(self, df: pd.DataFrame, position_data: Dict) -> Dict:
        """
        Kiểm tra Partial Take Profit Manager.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu
            position_data (Dict): Thông tin vị thế
            
        Returns:
            Dict: Kết quả kiểm tra
        """
        result = {
            'status': 'success',
            'tp_levels': {},
            'tp_signal': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            # Thiết lập các mức chốt lời
            tp_levels = self.tp_manager.set_tp_levels(df, position_data)
            
            # Kiểm tra kết quả
            if not tp_levels:
                result['status'] = 'warning'
                result['warnings'].append("Không thể thiết lập mức chốt lời")
            else:
                result['tp_levels'] = {
                    'symbol': tp_levels.get('symbol'),
                    'position_type': tp_levels.get('position_type'),
                    'entry_price': tp_levels.get('entry_price'),
                    'levels_count': len(tp_levels.get('tp_levels', [])),
                    'regime': tp_levels.get('regime')
                }
            
            # Kiểm tra tín hiệu chốt lời
            if tp_levels and 'tp_levels' in tp_levels and len(tp_levels['tp_levels']) > 0:
                # Giả sử giá tăng đến mức chốt lời đầu tiên
                first_tp_price = tp_levels['tp_levels'][0]['price']
                tp_signal = self.tp_manager.check_tp_signals(position_data['symbol'], position_data['position_id'], first_tp_price)
                
                result['tp_signal'] = {
                    'tp_signal': tp_signal.get('tp_signal'),
                    'level': tp_signal.get('level'),
                    'price': tp_signal.get('price'),
                    'quantity': tp_signal.get('quantity') if tp_signal.get('tp_signal') else None,
                }
                
                # Thử thực hiện chốt lời
                if tp_signal.get('tp_signal'):
                    execution_data = {
                        'level': tp_signal.get('level'),
                        'price': tp_signal.get('price'),
                        'quantity': tp_signal.get('quantity')
                    }
                    
                    execute_result = self.tp_manager.execute_partial_tp(position_data['symbol'], position_data['position_id'], execution_data)
                    
                    result['tp_execution'] = {
                        'success': execute_result.get('success'),
                        'adjusted_stop': execute_result.get('adjusted_stop'),
                        'remaining_levels': execute_result.get('remaining_levels')
                    }
                    
                    # Kiểm tra trạng thái sau khi thực hiện
                    status = self.tp_manager.get_position_tp_status(position_data['symbol'], position_data['position_id'])
                    
                    result['tp_status'] = {
                        'executed_percent': status.get('executed_percent'),
                        'remaining_quantity': status.get('remaining_quantity')
                    }
            
            # Tạo biểu đồ để kiểm tra
            try:
                chart_path = self.tp_manager.visualize_tp_levels(position_data['symbol'], position_data['position_id'], df)
                result['chart_path'] = chart_path
            except Exception as e:
                result['warnings'].append(f"Không thể tạo biểu đồ: {str(e)}")
                
            # Reset position để tránh ảnh hưởng đến các cặp tiền khác
            self.tp_manager.reset_position_tp(position_data['symbol'], position_data['position_id'])
        
        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(str(e))
        
        return result
    
    def _validate_regime_detector(self, df: pd.DataFrame) -> Dict:
        """
        Kiểm tra Enhanced Market Regime Detector.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu
            
        Returns:
            Dict: Kết quả kiểm tra
        """
        result = {
            'status': 'success',
            'regime': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            # Phát hiện chế độ thị trường
            regime_result = self.regime_detector.detect_regime(df)
            
            # Kiểm tra kết quả
            if not regime_result:
                result['status'] = 'warning'
                result['warnings'].append("Không thể phát hiện chế độ thị trường")
            else:
                result['regime'] = {
                    'regime': regime_result.get('regime'),
                    'confidence': regime_result.get('confidence'),
                    'indicators': regime_result.get('supporting_indicators')
                }
                
                # Các thông tin khác nếu có
                for key in ['trend_strength', 'volatility', 'range_width', 'momentum']:
                    if key in regime_result:
                        result['regime'][key] = regime_result[key]
        
        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(str(e))
        
        return result
    
    def _generate_summary_report(self) -> None:
        """Tạo báo cáo tổng hợp kết quả kiểm tra."""
        try:
            # Tạo tên file báo cáo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = os.path.join(self.output_dir, f"validation_report_{timestamp}.json")
            
            # Tạo báo cáo tổng hợp
            summary = {
                'timestamp': datetime.now().isoformat(),
                'total_symbols': len(self.validation_results),
                'success_count': sum(1 for result in self.validation_results.values() if result['status'] == 'success'),
                'warning_count': sum(1 for result in self.validation_results.values() if result['status'] == 'warning'),
                'error_count': sum(1 for result in self.validation_results.values() if result['status'] == 'error'),
                'execution_time': (datetime.now() - self.start_time).total_seconds(),
                'error_symbols': self.error_symbols,
                'symbol_results': {k: {'status': v['status'], 'execution_time': v['execution_time']} for k, v in self.validation_results.items()}
            }
            
            # Phân tích module lỗi
            module_errors = defaultdict(int)
            for result in self.validation_results.values():
                if 'modules' in result:
                    for module, module_result in result['modules'].items():
                        if module_result.get('status') == 'error':
                            module_errors[module] += 1
            
            summary['module_errors'] = dict(module_errors)
            
            # Lưu báo cáo tổng hợp
            with open(report_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"Đã tạo báo cáo tổng hợp tại: {report_file}")
            
            # Tạo báo cáo chi tiết
            detailed_report_file = os.path.join(self.output_dir, f"validation_detailed_{timestamp}.json")
            
            with open(detailed_report_file, 'w') as f:
                json.dump(self.validation_results, f, indent=2)
            
            logger.info(f"Đã tạo báo cáo chi tiết tại: {detailed_report_file}")
            
            # Tạo biểu đồ thống kê
            self._generate_summary_charts(summary, os.path.join(self.output_dir, f"validation_charts_{timestamp}.png"))
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo tổng hợp: {str(e)}")
            logger.error(traceback.format_exc())
    
    def _generate_summary_charts(self, summary: Dict, output_path: str) -> None:
        """Tạo biểu đồ thống kê kết quả kiểm tra."""
        try:
            plt.figure(figsize=(15, 10))
            
            # 1. Biểu đồ tròn trạng thái
            plt.subplot(2, 2, 1)
            status_counts = [summary['success_count'], summary['warning_count'], summary['error_count']]
            labels = ['Success', 'Warning', 'Error']
            colors = ['green', 'orange', 'red']
            
            plt.pie(status_counts, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            plt.axis('equal')
            plt.title('Validation Status')
            
            # 2. Biểu đồ module lỗi
            if summary['module_errors']:
                plt.subplot(2, 2, 2)
                modules = list(summary['module_errors'].keys())
                errors = list(summary['module_errors'].values())
                
                plt.bar(modules, errors, color='red', alpha=0.7)
                plt.title('Module Errors')
                plt.xticks(rotation=45, ha='right')
                plt.ylabel('Error Count')
                
            # 3. Biểu đồ thời gian thực thi
            plt.subplot(2, 2, 3)
            execution_times = [result['execution_time'] for result in summary['symbol_results'].values()]
            
            plt.hist(execution_times, bins=20, color='blue', alpha=0.7)
            plt.title('Execution Time Distribution')
            plt.xlabel('Execution Time (s)')
            plt.ylabel('Symbol Count')
            
            # 4. Biểu đồ lỗi theo cặp tiền
            plt.subplot(2, 2, 4)
            error_symbols = summary['error_symbols'][:10]  # Top 10 lỗi
            
            if error_symbols:
                error_counts = [1] * len(error_symbols)  # Mỗi symbol xuất hiện 1 lần
                plt.barh(error_symbols, error_counts, color='red', alpha=0.7)
                plt.title('Top Error Symbols')
                plt.xlabel('Error Count')
            else:
                plt.text(0.5, 0.5, 'No Error Symbols', horizontalalignment='center', verticalalignment='center')
                plt.title('Error Symbols')
            
            plt.tight_layout()
            plt.savefig(output_path)
            plt.close()
            
            logger.info(f"Đã tạo biểu đồ thống kê tại: {output_path}")
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ thống kê: {str(e)}")
            logger.error(traceback.format_exc())
    
    def _extract_symbol_from_filename(self, filename: str) -> Optional[str]:
        """
        Trích xuất mã cặp tiền từ tên file.
        
        Args:
            filename (str): Tên file dữ liệu
            
        Returns:
            Optional[str]: Mã cặp tiền hoặc None nếu không xác định được
        """
        # Loại bỏ phần mở rộng
        name_without_ext = os.path.splitext(filename)[0]
        
        # Các mẫu phổ biến
        patterns = [
            r'([A-Z0-9]+)_1h',
            r'([A-Z0-9]+)_\d+[mhdw]',
            r'([A-Z0-9]+)USDT',
            r'([A-Z0-9]+)BTC',
            r'([A-Z0-9]+)'
        ]
        
        for pattern in patterns:
            import re
            match = re.search(pattern, name_without_ext, re.IGNORECASE)
            if match:
                symbol = match.group(1).upper()
                # Thêm USDT nếu chỉ có tên coin
                if len(symbol) <= 5 and not symbol.endswith(('USDT', 'BTC', 'ETH', 'BNB')):
                    return f"{symbol}USDT"
                return symbol
        
        return None


def main():
    # Cấu hình logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('validate_symbols.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Khởi tạo validator
    validator = SymbolValidator(
        data_dir='data',
        output_dir='validation_results',
        min_data_months=3
    )
    
    # Bắt đầu quá trình kiểm tra
    results = validator.validate_all_symbols(max_workers=4)
    
    # In kết quả
    logger.info("Quá trình kiểm tra hoàn tất.")
    
    # Đưa ra kết luận
    success_count = sum(1 for result in results.values() if result['status'] == 'success')
    warning_count = sum(1 for result in results.values() if result['status'] == 'warning')
    error_count = sum(1 for result in results.values() if result['status'] == 'error')
    
    if len(results) == 0:
        logger.warning("Không tìm thấy cặp tiền nào để kiểm tra!")
        print("\n=======================")
        print("KHÔNG TÌM THẤY CẶP TIỀN NÀO ĐỂ KIỂM TRA!")
        print("Hãy kiểm tra lại thư mục dữ liệu và định dạng file.")
        print("=======================\n")
        return
    
    print("\n=======================")
    print(f"KẾT QUẢ KIỂM TRA {len(results)} CẶP TIỀN:")
    print(f"- Thành công: {success_count} ({success_count/len(results)*100:.2f}%)")
    print(f"- Cảnh báo: {warning_count} ({warning_count/len(results)*100:.2f}%)")
    print(f"- Lỗi: {error_count} ({error_count/len(results)*100:.2f}%)")
    
    if error_count > 0:
        print("\nCÁC CẶP TIỀN LỖI:")
        for symbol in validator.error_symbols:
            print(f"- {symbol}")
    
    # Kết luận
    if error_count == 0:
        print("\nKẾT LUẬN: Tất cả các module hoạt động tốt trên các cặp tiền đã kiểm tra.")
        print("Hệ thống đã sẵn sàng để chạy toàn bộ.")
    elif error_count <= len(results) * 0.1:  # Dưới 10% lỗi
        print("\nKẾT LUẬN: Hầu hết các module hoạt động tốt, chỉ có một số lỗi nhỏ.")
        print("Hệ thống có thể chạy được, nhưng nên loại bỏ các cặp tiền lỗi.")
    else:
        print("\nKẾT LUẬN: Có nhiều lỗi trong các module.")
        print("Cần sửa lỗi trước khi chạy toàn bộ hệ thống.")
    
    print("=======================\n")
    
    # Hiển thị thông tin chi tiết
    print(f"Báo cáo chi tiết đã được lưu trong thư mục: {validator.output_dir}")
    print(f"Log đã được lưu trong file: validate_symbols.log")


if __name__ == "__main__":
    main()