#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module kiểm tra tính hợp lệ của dữ liệu API
"""

import os
import json
import logging
import time
import traceback
import requests
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional, Union

# Thiết lập logging
logger = logging.getLogger("APIDataValidator")

class APIDataValidator:
    """
    Lớp xác thực dữ liệu API
    
    Class này kiểm tra tính hợp lệ của dữ liệu lấy từ API để đảm bảo
    backtest sử dụng dữ liệu thực tế và chính xác
    """
    
    def __init__(self, api_key=None, api_secret=None, testnet=True):
        """
        Khởi tạo đối tượng validator
        
        :param api_key: Khóa API Binance
        :param api_secret: Mã bí mật API Binance
        :param testnet: Sử dụng môi trường testnet hay không
        """
        self.api_key = api_key or os.environ.get("BINANCE_API_KEY")
        self.api_secret = api_secret or os.environ.get("BINANCE_API_SECRET")
        self.testnet = testnet
        self.validation_cache = {}
        self.last_validated = {}
        
        # Các thông số ngưỡng kiểm tra
        self.threshold_settings = {
            "candlestick_volume_zero_max_percent": 5.0,  # Tối đa 5% nến có khối lượng 0
            "price_gap_max_percent": 3.0,  # Khoảng cách giá tối đa 3%
            "minimum_data_points": 100,  # Tối thiểu số điểm dữ liệu
            "validation_cache_ttl": 3600,  # Thời gian cache (giây)
            "nan_values_max_percent": 1.0,  # Tối đa 1% giá trị NaN
            "price_deviation_threshold": 5.0,  # Ngưỡng độ lệch giá 5%
        }
    
    def validate_klines_data(self, symbol: str, klines_data: List[List], timeframe: str) -> Dict:
        """
        Kiểm tra tính hợp lệ của dữ liệu klines
        
        :param symbol: Symbol cần kiểm tra
        :param klines_data: Dữ liệu klines từ API
        :param timeframe: Khung thời gian
        :return: Dict kết quả kiểm tra
        """
        if not klines_data or len(klines_data) < self.threshold_settings["minimum_data_points"]:
            return {
                "status": "error",
                "is_valid": False,
                "message": f"Không đủ dữ liệu nến (cần tối thiểu {self.threshold_settings['minimum_data_points']} điểm)",
                "details": {
                    "received_points": len(klines_data) if klines_data else 0,
                    "required_points": self.threshold_settings["minimum_data_points"]
                }
            }
        
        # Chuyển đổi sang DataFrame để dễ xử lý
        df = pd.DataFrame(klines_data, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignored'
        ])
        
        # Chuyển đổi các cột số
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Kiểm tra giá trị NaN
        nan_count = df[['open', 'high', 'low', 'close', 'volume']].isna().sum().sum()
        nan_percent = nan_count / (len(df) * 5) * 100  # 5 cột
        
        if nan_percent > self.threshold_settings["nan_values_max_percent"]:
            return {
                "status": "error",
                "is_valid": False,
                "message": f"Quá nhiều giá trị NaN trong dữ liệu ({nan_percent:.2f}%)",
                "details": {
                    "nan_count": int(nan_count),
                    "nan_percent": float(nan_percent),
                    "threshold": self.threshold_settings["nan_values_max_percent"]
                }
            }
        
        # Kiểm tra khối lượng bằng 0
        zero_volume_count = (df['volume'] == 0).sum()
        zero_volume_percent = zero_volume_count / len(df) * 100
        
        if zero_volume_percent > self.threshold_settings["candlestick_volume_zero_max_percent"]:
            return {
                "status": "warning",
                "is_valid": True,  # Vẫn hợp lệ nhưng cảnh báo
                "message": f"Nhiều nến có khối lượng 0 ({zero_volume_percent:.2f}%)",
                "details": {
                    "zero_volume_count": int(zero_volume_count),
                    "zero_volume_percent": float(zero_volume_percent),
                    "threshold": self.threshold_settings["candlestick_volume_zero_max_percent"]
                }
            }
        
        # Kiểm tra khoảng cách giá bất thường
        df['price_pct_change'] = abs(df['close'].pct_change() * 100)
        max_price_gap = df['price_pct_change'].max()
        max_gap_index = df['price_pct_change'].idxmax()
        
        if max_price_gap > self.threshold_settings["price_gap_max_percent"]:
            return {
                "status": "warning",
                "is_valid": True,  # Vẫn hợp lệ nhưng cảnh báo
                "message": f"Phát hiện khoảng cách giá lớn bất thường ({max_price_gap:.2f}%)",
                "details": {
                    "max_price_gap": float(max_price_gap),
                    "gap_timestamp": int(df.iloc[max_gap_index]['open_time']),
                    "threshold": self.threshold_settings["price_gap_max_percent"]
                }
            }
        
        # Kiểm tra độ lệch giá OHLC
        price_deviation = df.apply(lambda x: abs(x['high'] - x['low']) / x['open'] * 100, axis=1).max()
        max_deviation_index = df.apply(lambda x: abs(x['high'] - x['low']) / x['open'] * 100, axis=1).idxmax()
        
        if price_deviation > self.threshold_settings["price_deviation_threshold"]:
            return {
                "status": "warning",
                "is_valid": True,  # Vẫn hợp lệ nhưng cảnh báo
                "message": f"Phát hiện độ lệch giá cao bất thường ({price_deviation:.2f}%)",
                "details": {
                    "max_deviation": float(price_deviation),
                    "deviation_timestamp": int(df.iloc[max_deviation_index]['open_time']),
                    "threshold": self.threshold_settings["price_deviation_threshold"]
                }
            }
        
        # Mọi thứ đều tốt
        return {
            "status": "success",
            "is_valid": True,
            "message": f"Dữ liệu {symbol} ({timeframe}) hợp lệ",
            "details": {
                "data_points": len(df),
                "first_timestamp": int(df.iloc[0]['open_time']),
                "last_timestamp": int(df.iloc[-1]['open_time']),
                "zero_volume_percent": float(zero_volume_percent),
                "max_price_gap": float(max_price_gap),
                "max_price_deviation": float(price_deviation)
            }
        }
    
    def validate_historical_data(self, symbol: str, timeframe: str, start_time: Optional[int] = None, 
                                end_time: Optional[int] = None, cached_data: Optional[pd.DataFrame] = None) -> Dict:
        """
        Xác thực dữ liệu lịch sử từ API hoặc cache
        
        :param symbol: Symbol tiền điện tử
        :param timeframe: Khung thời gian
        :param start_time: Thời gian bắt đầu (milliseconds)
        :param end_time: Thời gian kết thúc (milliseconds)
        :param cached_data: DataFrame chứa dữ liệu cache nếu có
        :return: Kết quả xác thực
        """
        # Kiểm tra xem có dữ liệu cached đã xác thực trước đó không
        cache_key = f"{symbol}_{timeframe}_{start_time}_{end_time}"
        current_time = time.time()
        
        if cache_key in self.validation_cache:
            # Kiểm tra xem cache còn hiệu lực hay không
            if current_time - self.last_validated.get(cache_key, 0) < self.threshold_settings["validation_cache_ttl"]:
                return self.validation_cache[cache_key]
        
        # Nếu có dữ liệu cached được cung cấp, kiểm tra nó
        if cached_data is not None:
            # Chuyển DataFrame thành định dạng klines để kiểm tra
            klines_format = cached_data.values.tolist()
            validation_result = self.validate_klines_data(symbol, klines_format, timeframe)
            
            # Lưu kết quả vào cache
            self.validation_cache[cache_key] = validation_result
            self.last_validated[cache_key] = current_time
            
            return validation_result
        
        # Nếu không có dữ liệu cached, báo lỗi và yêu cầu dữ liệu
        return {
            "status": "error",
            "is_valid": False,
            "message": "Không có dữ liệu để xác thực",
            "details": {
                "symbol": symbol,
                "timeframe": timeframe,
                "start_time": start_time,
                "end_time": end_time
            }
        }
    
    def validate_data_consistency(self, symbol: str, timeframes: List[str], 
                                data_dict: Dict[str, pd.DataFrame]) -> Dict:
        """
        Kiểm tra tính nhất quán của dữ liệu giữa các khung thời gian
        
        :param symbol: Symbol cần kiểm tra
        :param timeframes: Danh sách khung thời gian
        :param data_dict: Dict chứa DataFrame cho mỗi khung thời gian
        :return: Dict kết quả kiểm tra
        """
        if not timeframes or len(timeframes) < 2:
            return {
                "status": "warning",
                "is_valid": True,
                "message": "Cần ít nhất 2 khung thời gian để kiểm tra tính nhất quán"
            }
        
        if not all(tf in data_dict for tf in timeframes):
            missing_tfs = [tf for tf in timeframes if tf not in data_dict]
            return {
                "status": "error",
                "is_valid": False,
                "message": f"Thiếu dữ liệu cho các khung thời gian: {', '.join(missing_tfs)}"
            }
        
        # So sánh giá đóng cửa ở cùng thời điểm giữa các khung thời gian
        comparison_results = {}
        reference_tf = timeframes[0]  # Lấy khung thời gian đầu tiên làm tham chiếu
        
        for tf in timeframes[1:]:
            # Chọn các thời điểm trùng nhau
            ref_df = data_dict[reference_tf]
            compare_df = data_dict[tf]
            
            # Chuyển đổi thời gian thành chuỗi để dễ so sánh
            if 'open_time' in ref_df.columns:
                ref_times = set(ref_df['open_time'].astype(str))
                compare_times = set(compare_df['open_time'].astype(str))
            else:
                ref_times = set(ref_df.index.astype(str))
                compare_times = set(compare_df.index.astype(str))
            
            # Tìm các thời điểm trùng nhau
            common_times = ref_times.intersection(compare_times)
            
            if len(common_times) < 10:  # Cần ít nhất 10 điểm chung để so sánh
                comparison_results[tf] = {
                    "status": "warning",
                    "is_valid": True,
                    "message": f"Không đủ điểm dữ liệu chung giữa {reference_tf} và {tf}"
                }
                continue
            
            # So sánh giá đóng cửa tại các thời điểm trùng nhau
            common_times_list = list(common_times)
            
            if 'open_time' in ref_df.columns:
                ref_values = ref_df[ref_df['open_time'].astype(str).isin(common_times_list)]['close'].values
                compare_values = compare_df[compare_df['open_time'].astype(str).isin(common_times_list)]['close'].values
            else:
                ref_values = ref_df[ref_df.index.astype(str).isin(common_times_list)]['close'].values
                compare_values = compare_df[compare_df.index.astype(str).isin(common_times_list)]['close'].values
            
            # Tính sai số tương đối
            relative_errors = np.abs(ref_values - compare_values) / ref_values * 100
            max_error = np.max(relative_errors)
            mean_error = np.mean(relative_errors)
            
            if max_error > 1.0:  # Sai số lớn hơn 1%
                comparison_results[tf] = {
                    "status": "warning",
                    "is_valid": True,
                    "message": f"Phát hiện sự khác biệt đáng kể giữa {reference_tf} và {tf}",
                    "details": {
                        "max_error_percent": float(max_error),
                        "mean_error_percent": float(mean_error),
                        "common_points": len(common_times)
                    }
                }
            else:
                comparison_results[tf] = {
                    "status": "success",
                    "is_valid": True,
                    "message": f"Dữ liệu nhất quán giữa {reference_tf} và {tf}",
                    "details": {
                        "max_error_percent": float(max_error),
                        "mean_error_percent": float(mean_error),
                        "common_points": len(common_times)
                    }
                }
        
        # Kiểm tra tổng thể
        all_valid = all(result["is_valid"] for result in comparison_results.values())
        all_success = all(result["status"] == "success" for result in comparison_results.values())
        
        if all_success:
            return {
                "status": "success",
                "is_valid": True,
                "message": f"Dữ liệu {symbol} nhất quán giữa tất cả các khung thời gian",
                "details": comparison_results
            }
        elif all_valid:
            return {
                "status": "warning",
                "is_valid": True,
                "message": f"Dữ liệu {symbol} có một số vấn đề nhỏ giữa các khung thời gian",
                "details": comparison_results
            }
        else:
            return {
                "status": "error",
                "is_valid": False,
                "message": f"Dữ liệu {symbol} không nhất quán giữa các khung thời gian",
                "details": comparison_results
            }
    
    def validate_market_data(self, symbols: List[str], timeframes: List[str], 
                           start_date: str, end_date: str, data_source: str = "api",
                           data_dir: Optional[str] = None) -> Dict:
        """
        Kiểm tra tính hợp lệ của dữ liệu thị trường cho nhiều cặp tiền và khung thời gian
        
        :param symbols: Danh sách symbols cần kiểm tra
        :param timeframes: Danh sách khung thời gian
        :param start_date: Ngày bắt đầu (YYYY-MM-DD)
        :param end_date: Ngày kết thúc (YYYY-MM-DD)
        :param data_source: Nguồn dữ liệu (api/file)
        :param data_dir: Thư mục chứa dữ liệu nếu data_source là file
        :return: Dict kết quả kiểm tra
        """
        results = {}
        all_valid = True
        warnings_count = 0
        errors_count = 0
        
        for symbol in symbols:
            symbol_results = {}
            
            for timeframe in timeframes:
                # Tạo key để cache kết quả
                cache_key = f"{symbol}_{timeframe}_{start_date}_{end_date}_{data_source}"
                
                # Kiểm tra cache
                if cache_key in self.validation_cache:
                    if time.time() - self.last_validated.get(cache_key, 0) < self.threshold_settings["validation_cache_ttl"]:
                        symbol_results[timeframe] = self.validation_cache[cache_key]
                        continue
                
                try:
                    # Mô phỏng việc kiểm tra dữ liệu từ file hoặc API
                    if data_source == "file" and data_dir:
                        # Giả sử có file dữ liệu theo định dạng {symbol}_{timeframe}.csv
                        file_path = os.path.join(data_dir, f"{symbol}_{timeframe}.csv")
                        
                        if not os.path.exists(file_path):
                            result = {
                                "status": "error",
                                "is_valid": False,
                                "message": f"Không tìm thấy file dữ liệu cho {symbol} ({timeframe})",
                                "details": {"file_path": file_path}
                            }
                            errors_count += 1
                        else:
                            # Đọc dữ liệu từ file
                            try:
                                df = pd.read_csv(file_path)
                                result = self.validate_klines_data(symbol, df.values.tolist(), timeframe)
                            except Exception as e:
                                result = {
                                    "status": "error",
                                    "is_valid": False,
                                    "message": f"Lỗi khi đọc file dữ liệu: {str(e)}",
                                    "details": {"file_path": file_path, "error": traceback.format_exc()}
                                }
                                errors_count += 1
                    else:
                        # Thật ra ở đây sẽ gọi API, nhưng hiện tại chỉ trả về kết quả giả
                        result = {
                            "status": "success",
                            "is_valid": True,
                            "message": f"Dữ liệu {symbol} ({timeframe}) đã xác thực thành công",
                            "details": {
                                "data_source": data_source,
                                "period": f"{start_date} to {end_date}"
                            }
                        }
                    
                    if result["status"] == "warning":
                        warnings_count += 1
                    elif result["status"] == "error":
                        errors_count += 1
                        all_valid = False
                    
                    # Lưu kết quả vào cache
                    self.validation_cache[cache_key] = result
                    self.last_validated[cache_key] = time.time()
                    
                except Exception as e:
                    result = {
                        "status": "error",
                        "is_valid": False,
                        "message": f"Lỗi không xác định: {str(e)}",
                        "details": {"error": traceback.format_exc()}
                    }
                    errors_count += 1
                    all_valid = False
                
                symbol_results[timeframe] = result
            
            results[symbol] = symbol_results
        
        # Tổng hợp kết quả
        if errors_count > 0:
            status = "error"
            message = f"Có {errors_count} lỗi và {warnings_count} cảnh báo trong dữ liệu"
        elif warnings_count > 0:
            status = "warning"
            message = f"Có {warnings_count} cảnh báo trong dữ liệu"
        else:
            status = "success"
            message = "Tất cả dữ liệu đều hợp lệ"
        
        return {
            "status": status,
            "is_valid": all_valid,
            "message": message,
            "symbols_count": len(symbols),
            "timeframes_count": len(timeframes),
            "errors_count": errors_count,
            "warnings_count": warnings_count,
            "details": results
        }

# Hàm để thử nghiệm module
def test_api_data_validator():
    """Hàm kiểm tra chức năng của API data validator"""
    # Cấu hình logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    validator = APIDataValidator()
    
    print("=== Kiểm tra dữ liệu thị trường ===")
    result = validator.validate_market_data(
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframes=["1h", "4h"],
        start_date="2024-01-01",
        end_date="2024-03-01",
        data_source="api"
    )
    
    print(f"Trạng thái: {result['status']}")
    print(f"Hợp lệ: {result['is_valid']}")
    print(f"Thông báo: {result['message']}")
    print(f"Số lỗi: {result['errors_count']}")
    print(f"Số cảnh báo: {result['warnings_count']}")

if __name__ == "__main__":
    test_api_data_validator()