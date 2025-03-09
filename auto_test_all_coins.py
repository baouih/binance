"""
Auto Test All Coins - Script chạy tự động kiểm tra tất cả các đồng coin

Chạy test với các hệ số rủi ro khác nhau, kiểm tra lỗi trước khi
chạy toàn bộ hệ thống
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import subprocess
import time
import argparse
from typing import Dict, List, Optional, Any
from validate_all_symbols import SymbolValidator
import glob

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_test_all_coins.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('auto_test_all_coins')

class AutoTestAllCoins:
    """
    Tự động kiểm tra tất cả các đồng coin có dữ liệu 3 tháng và
    chạy backtest với các hệ số rủi ro khác nhau
    """
    
    def __init__(self, 
                data_dir: str = 'data', 
                output_dir: str = 'test_results',
                validate_first: bool = True,
                risk_levels: List[float] = [2.0, 2.5, 3.0, 4.0, 5.0],
                timeframes: List[str] = ['1h', '4h', '1d'],
                min_data_months: int = 3,
                max_parallel: int = 4):
        """
        Khởi tạo AutoTestAllCoins.
        
        Args:
            data_dir (str): Thư mục chứa dữ liệu
            output_dir (str): Thư mục lưu kết quả kiểm tra
            validate_first (bool): Có kiểm tra module trước khi chạy backtest không
            risk_levels (List[float]): Danh sách các hệ số rủi ro cần kiểm tra
            timeframes (List[str]): Danh sách các khung thời gian cần kiểm tra
            min_data_months (int): Số tháng dữ liệu tối thiểu
            max_parallel (int): Số lượng tác vụ chạy song song tối đa
        """
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.validate_first = validate_first
        self.risk_levels = risk_levels
        self.timeframes = timeframes
        self.min_data_months = min_data_months
        self.max_parallel = max_parallel
        
        # Tạo thư mục output nếu chưa tồn tại
        os.makedirs(output_dir, exist_ok=True)
        
        # Kết quả
        self.available_symbols = []
        self.validated_symbols = []
        self.backtest_results = {}
        
        # Thời gian bắt đầu
        self.start_time = datetime.now()
    
    def run(self, symbols_filter: Optional[List[str]] = None) -> None:
        """
        Chạy quá trình kiểm tra tự động.
        
        Args:
            symbols_filter (Optional[List[str]]): Danh sách các cặp tiền cần kiểm tra
                                               Nếu None sẽ kiểm tra tất cả cặp tiền có sẵn
        """
        logger.info("Bắt đầu quá trình kiểm tra tự động các đồng coin")
        
        # Bước 1: Kiểm tra các module nếu cần
        if self.validate_first:
            self._validate_modules(symbols_filter)
        
        # Bước 2: Tìm các cặp tiền có đủ dữ liệu
        if not self.available_symbols:
            self.available_symbols = self._find_available_symbols(symbols_filter)
        
        if not self.available_symbols:
            logger.warning("Không tìm thấy cặp tiền nào để kiểm tra")
            print("\n=======================")
            print("KHÔNG TÌM THẤY CẶP TIỀN NÀO ĐỂ KIỂM TRA!")
            print("Hãy kiểm tra lại thư mục dữ liệu và định dạng file.")
            print("=======================\n")
            return
        
        # Lấy danh sách các cặp tiền có thể sử dụng (đã qua validation)
        usable_symbols = self.validated_symbols if self.validate_first else self.available_symbols
        
        if not usable_symbols:
            logger.warning("Không có cặp tiền nào đạt yêu cầu sau khi kiểm tra")
            print("\n=======================")
            print("KHÔNG CÓ CẶP TIỀN NÀO ĐẠT YÊU CẦU SAU KHI KIỂM TRA!")
            print("Hãy kiểm tra lại các module và dữ liệu.")
            print("=======================\n")
            return
        
        # Hiển thị thông tin
        print(f"\n=======================")
        print(f"ĐÃ TÌM THẤY {len(usable_symbols)} CẶP TIỀN CÓ THỂ KIỂM TRA:")
        for i, symbol in enumerate(usable_symbols):
            print(f"- {symbol}", end="\t")
            if (i + 1) % 5 == 0:
                print()
        print("\n=======================\n")
        
        # Bước 3: Chạy backtest với các tham số khác nhau
        backtest_count = 0
        
        for symbol in usable_symbols:
            for timeframe in self.timeframes:
                for risk_level in self.risk_levels:
                    backtest_result = self._run_backtest(symbol, timeframe, risk_level)
                    
                    if backtest_result:
                        key = f"{symbol}_{timeframe}_{risk_level}"
                        self.backtest_results[key] = backtest_result
                        backtest_count += 1
                    
                    # Dừng một chút để tránh quá tải
                    time.sleep(1)
        
        # Bước 4: Tổng hợp kết quả
        self._summarize_results()
        
        logger.info(f"Đã hoàn thành quá trình kiểm tra tự động, đã chạy {backtest_count} backtest")
        
        # Thời gian thực hiện
        duration = datetime.now() - self.start_time
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        print(f"\n=======================")
        print(f"ĐÃ HOÀN THÀNH KIỂM TRA TỰ ĐỘNG")
        print(f"- Số cặp tiền đã kiểm tra: {len(usable_symbols)}")
        print(f"- Số backtest đã chạy: {backtest_count}")
        print(f"- Thời gian thực hiện: {int(hours)}h {int(minutes)}m {int(seconds)}s")
        print(f"- Báo cáo kết quả đã được lưu trong thư mục: {self.output_dir}")
        print("=======================\n")
    
    def _validate_modules(self, symbols_filter: Optional[List[str]] = None) -> None:
        """
        Kiểm tra các module trước khi chạy backtest.
        
        Args:
            symbols_filter (Optional[List[str]]): Danh sách các cặp tiền cần kiểm tra
        """
        logger.info("Đang kiểm tra các module...")
        
        # Khởi tạo validator
        validator = SymbolValidator(
            data_dir=self.data_dir,
            output_dir=os.path.join(self.output_dir, 'validation'),
            min_data_months=self.min_data_months,
            symbols_filter=symbols_filter
        )
        
        # Chạy kiểm tra
        validation_results = validator.validate_all_symbols(max_workers=self.max_parallel)
        
        # Lấy danh sách cặp tiền đạt yêu cầu (success hoặc warning)
        validated_symbols = [symbol for symbol, result in validation_results.items() 
                           if result['status'] in ['success', 'warning']]
        
        # Lưu lại các cặp tiền đạt yêu cầu và các cặp tiền sẵn có
        self.validated_symbols = validated_symbols
        self.available_symbols = validator.available_symbols
        
        # In thông tin
        logger.info(f"Đã xác nhận {len(validated_symbols)}/{len(validator.available_symbols)} cặp tiền đạt yêu cầu")
    
    def _find_available_symbols(self, symbols_filter: Optional[List[str]] = None) -> List[str]:
        """
        Tìm tất cả các cặp tiền có dữ liệu đủ số tháng yêu cầu.
        
        Args:
            symbols_filter (Optional[List[str]]): Danh sách các cặp tiền cần kiểm tra
            
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
            if symbols_filter:
                all_symbols = [s for s in all_symbols if s in symbols_filter]
            
            logger.info(f"Tìm thấy {len(all_symbols)} cặp tiền có đủ dữ liệu: {all_symbols}")
            
            return all_symbols
            
        except Exception as e:
            logger.error(f"Lỗi khi tìm các cặp tiền: {str(e)}")
            return []
    
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
    
    def _run_backtest(self, symbol: str, timeframe: str, risk_level: float) -> Optional[Dict]:
        """
        Chạy backtest cho một cặp tiền với các tham số nhất định.
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            risk_level (float): Hệ số rủi ro
            
        Returns:
            Optional[Dict]: Kết quả backtest hoặc None nếu thất bại
        """
        logger.info(f"Chạy backtest cho {symbol} với timeframe {timeframe} và risk {risk_level}%")
        
        # Xác định script backtest
        backtest_script = "backtest_strategy.py"
        if not os.path.exists(backtest_script):
            backtest_script = "backtest_module_test.py"
        if not os.path.exists(backtest_script):
            backtest_script = "backtest_controller.py"
        if not os.path.exists(backtest_script):
            logger.error("Không tìm thấy script backtest")
            return None
        
        # Tạo ID duy nhất cho backtest
        test_id = f"{symbol}_{timeframe}_{risk_level}_{int(time.time())}"
        output_file = os.path.join(self.output_dir, f"backtest_{test_id}.json")
        log_file = os.path.join(self.output_dir, f"backtest_{test_id}.log")
        
        # Tạo câu lệnh
        cmd = [
            "python", backtest_script,
            "--symbol", symbol,
            "--timeframe", timeframe,
            "--risk", str(risk_level),
            "--output", output_file,
            "--start_date", (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
            "--end_date", datetime.now().strftime("%Y-%m-%d"),
            "--use_new_indicators", "True",
            "--use_order_flow", "True",
            "--use_volume_profile", "True",
            "--use_adaptive_exit", "True"
        ]
        
        try:
            # Chạy subprocess
            with open(log_file, 'w') as log:
                process = subprocess.Popen(
                    cmd,
                    stdout=log,
                    stderr=log,
                    text=True
                )
                
                # Chờ đợi hoàn thành với timeout
                try:
                    process.wait(timeout=300)  # 5 phút timeout
                except subprocess.TimeoutExpired:
                    logger.warning(f"Backtest cho {symbol} bị timeout sau 5 phút, đang dừng quá trình")
                    process.kill()
                    return None
            
            # Kiểm tra mã thoát
            if process.returncode != 0:
                logger.warning(f"Backtest cho {symbol} thất bại với mã lỗi {process.returncode}")
                
                # Đọc log để tìm lỗi
                with open(log_file, 'r') as log:
                    last_lines = log.readlines()[-10:]  # 10 dòng cuối cùng
                    error_log = ''.join(last_lines)
                    logger.warning(f"Lỗi: {error_log}")
                
                return {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'risk_level': risk_level,
                    'status': 'error',
                    'error_code': process.returncode,
                    'error_log': error_log if 'error_log' in locals() else "Unknown error"
                }
            
            # Đọc kết quả
            if os.path.exists(output_file):
                try:
                    with open(output_file, 'r') as f:
                        result = json.load(f)
                    
                    logger.info(f"Backtest cho {symbol} hoàn thành thành công")
                    
                    # Thêm metadata
                    result.update({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'risk_level': risk_level,
                        'status': 'success',
                        'log_file': log_file,
                        'output_file': output_file,
                    })
                    
                    return result
                except json.JSONDecodeError:
                    logger.warning(f"Không thể đọc file kết quả {output_file}")
                    
                    # Đọc nội dung file
                    with open(output_file, 'r') as f:
                        file_content = f.read()
                    
                    logger.warning(f"Nội dung file: {file_content[:500]}...")
                    
                    return {
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'risk_level': risk_level,
                        'status': 'error',
                        'error': 'Invalid JSON output',
                        'file_content': file_content[:500]
                    }
            else:
                logger.warning(f"Không tìm thấy file kết quả {output_file}")
                return {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'risk_level': risk_level,
                    'status': 'error',
                    'error': 'No output file'
                }
        
        except Exception as e:
            logger.error(f"Lỗi khi chạy backtest cho {symbol}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'risk_level': risk_level,
                'status': 'error',
                'error': str(e)
            }
    
    def _summarize_results(self) -> None:
        """Tổng hợp kết quả các backtest."""
        try:
            logger.info("Đang tổng hợp kết quả backtest...")
            
            # Tạo tên file báo cáo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = os.path.join(self.output_dir, f"backtest_summary_{timestamp}.json")
            
            # Tạo báo cáo chi tiết theo cặp tiền
            symbol_results = {}
            
            for key, result in self.backtest_results.items():
                symbol = result['symbol']
                
                if symbol not in symbol_results:
                    symbol_results[symbol] = {
                        'total_tests': 0,
                        'success_tests': 0,
                        'error_tests': 0,
                        'timeframes': set(),
                        'risk_levels': set(),
                        'best_result': None,
                        'worst_result': None,
                        'results': []
                    }
                
                # Cập nhật thông tin
                symbol_results[symbol]['total_tests'] += 1
                symbol_results[symbol]['timeframes'].add(result['timeframe'])
                symbol_results[symbol]['risk_levels'].add(result['risk_level'])
                
                if result['status'] == 'success':
                    symbol_results[symbol]['success_tests'] += 1
                    
                    # Tính toán các giá trị quan trọng nếu có
                    profit = result.get('total_profit', 0)
                    win_rate = result.get('win_rate', 0)
                    profit_factor = result.get('profit_factor', 0)
                    
                    # Tính điểm số
                    score = profit * 0.5 + win_rate * 0.3 + profit_factor * 0.2
                    
                    result_summary = {
                        'timeframe': result['timeframe'],
                        'risk_level': result['risk_level'],
                        'profit': profit,
                        'win_rate': win_rate,
                        'profit_factor': profit_factor,
                        'score': score
                    }
                    
                    symbol_results[symbol]['results'].append(result_summary)
                    
                    # Kiểm tra kết quả tốt nhất/tệ nhất
                    if symbol_results[symbol]['best_result'] is None or score > symbol_results[symbol]['best_result']['score']:
                        symbol_results[symbol]['best_result'] = result_summary
                        
                    if symbol_results[symbol]['worst_result'] is None or score < symbol_results[symbol]['worst_result']['score']:
                        symbol_results[symbol]['worst_result'] = result_summary
                else:
                    symbol_results[symbol]['error_tests'] += 1
            
            # Chuyển set thành list để có thể serialize JSON
            for symbol in symbol_results:
                symbol_results[symbol]['timeframes'] = list(symbol_results[symbol]['timeframes'])
                symbol_results[symbol]['risk_levels'] = list(symbol_results[symbol]['risk_levels'])
            
            # Tạo báo cáo tổng hợp
            summary = {
                'timestamp': datetime.now().isoformat(),
                'total_symbols': len(self.available_symbols),
                'validated_symbols': len(self.validated_symbols) if self.validate_first else len(self.available_symbols),
                'tested_symbols': len(symbol_results),
                'total_tests': len(self.backtest_results),
                'success_tests': sum(1 for result in self.backtest_results.values() if result['status'] == 'success'),
                'error_tests': sum(1 for result in self.backtest_results.values() if result['status'] == 'error'),
                'timeframes': self.timeframes,
                'risk_levels': self.risk_levels,
                'execution_time': (datetime.now() - self.start_time).total_seconds(),
                'symbol_results': symbol_results
            }
            
            # Lưu báo cáo tổng hợp
            with open(report_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"Đã tạo báo cáo tổng hợp tại: {report_file}")
            
            # Tạo báo cáo tổng hợp theo timeframe và risk
            param_results = {}
            
            for tf in self.timeframes:
                for risk in self.risk_levels:
                    key = f"{tf}_{risk}"
                    param_results[key] = {
                        'timeframe': tf,
                        'risk_level': risk,
                        'total_tests': 0,
                        'success_tests': 0,
                        'avg_profit': 0,
                        'avg_win_rate': 0,
                        'avg_profit_factor': 0,
                        'symbols': []
                    }
            
            # Tính toán kết quả theo tham số
            for result in self.backtest_results.values():
                if result['status'] == 'success':
                    tf = result['timeframe']
                    risk = result['risk_level']
                    key = f"{tf}_{risk}"
                    
                    if key in param_results:
                        param_results[key]['total_tests'] += 1
                        param_results[key]['success_tests'] += 1
                        param_results[key]['symbols'].append(result['symbol'])
                        
                        profit = result.get('total_profit', 0)
                        win_rate = result.get('win_rate', 0)
                        profit_factor = result.get('profit_factor', 0)
                        
                        # Cập nhật giá trị trung bình
                        current_count = param_results[key]['success_tests']
                        param_results[key]['avg_profit'] = (param_results[key]['avg_profit'] * (current_count - 1) + profit) / current_count
                        param_results[key]['avg_win_rate'] = (param_results[key]['avg_win_rate'] * (current_count - 1) + win_rate) / current_count
                        param_results[key]['avg_profit_factor'] = (param_results[key]['avg_profit_factor'] * (current_count - 1) + profit_factor) / current_count
            
            # Lưu báo cáo tham số
            param_report_file = os.path.join(self.output_dir, f"param_summary_{timestamp}.json")
            
            with open(param_report_file, 'w') as f:
                json.dump(param_results, f, indent=2)
            
            logger.info(f"Đã tạo báo cáo tham số tại: {param_report_file}")
            
            # Hiển thị thông tin tóm tắt
            best_params = max(param_results.values(), key=lambda x: x['avg_profit'] if x['success_tests'] > 0 else -float('inf'))
            
            print("\n=======================")
            print("TÓM TẮT KẾT QUẢ BACKTEST:")
            print(f"- Tổng số cặp tiền: {summary['total_symbols']}")
            print(f"- Số cặp tiền đã test: {summary['tested_symbols']}")
            print(f"- Tổng số test: {summary['total_tests']}")
            print(f"- Thành công: {summary['success_tests']} ({summary['success_tests']/summary['total_tests']*100:.2f}%)")
            
            if best_params['success_tests'] > 0:
                print("\nTHAM SỐ TỐT NHẤT:")
                print(f"- Timeframe: {best_params['timeframe']}")
                print(f"- Risk Level: {best_params['risk_level']}%")
                print(f"- Lợi nhuận trung bình: {best_params['avg_profit']:.2f}%")
                print(f"- Tỷ lệ thắng trung bình: {best_params['avg_win_rate']:.2f}%")
                print(f"- Profit Factor trung bình: {best_params['avg_profit_factor']:.2f}")
            
            print("\nKẾT QUẢ THEO CẶP TIỀN TỐT NHẤT:")
            
            # Sắp xếp theo điểm số
            best_symbols = []
            for symbol, result in symbol_results.items():
                if result['best_result']:
                    best_symbols.append((symbol, result['best_result']))
            
            best_symbols.sort(key=lambda x: x[1]['score'], reverse=True)
            
            # Hiển thị top 5
            for i, (symbol, best_result) in enumerate(best_symbols[:5]):
                print(f"{i+1}. {symbol} - TF: {best_result['timeframe']}, Risk: {best_result['risk_level']}%, "
                      f"Profit: {best_result['profit']:.2f}%, WinRate: {best_result['win_rate']:.2f}%")
            
            print("=======================\n")
            
        except Exception as e:
            logger.error(f"Lỗi khi tổng hợp kết quả: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Auto Test All Coins - Tự động kiểm tra tất cả các đồng coin')
    parser.add_argument('--data_dir', type=str, default='data', help='Thư mục chứa dữ liệu')
    parser.add_argument('--output_dir', type=str, default='test_results', help='Thư mục lưu kết quả kiểm tra')
    parser.add_argument('--validate_first', type=bool, default=True, help='Có kiểm tra module trước khi chạy backtest không')
    parser.add_argument('--risk_levels', type=float, nargs='+', default=[2.0, 2.5, 3.0, 4.0, 5.0], help='Danh sách các hệ số rủi ro cần kiểm tra')
    parser.add_argument('--timeframes', type=str, nargs='+', default=['1h', '4h', '1d'], help='Danh sách các khung thời gian cần kiểm tra')
    parser.add_argument('--min_data_months', type=int, default=3, help='Số tháng dữ liệu tối thiểu')
    parser.add_argument('--max_parallel', type=int, default=4, help='Số lượng tác vụ chạy song song tối đa')
    parser.add_argument('--symbols', type=str, nargs='+', help='Danh sách các cặp tiền cần kiểm tra, mặc định là tất cả')
    
    args = parser.parse_args()
    
    # Khởi tạo auto tester
    auto_tester = AutoTestAllCoins(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        validate_first=args.validate_first,
        risk_levels=args.risk_levels,
        timeframes=args.timeframes,
        min_data_months=args.min_data_months,
        max_parallel=args.max_parallel
    )
    
    # Chạy kiểm tra
    auto_tester.run(symbols_filter=args.symbols)


if __name__ == "__main__":
    main()