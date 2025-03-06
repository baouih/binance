#!/usr/bin/env python3
"""
Module điều chỉnh ngưỡng biến động thông minh (Adaptive Volatility Threshold)

Module này cung cấp các hàm để tính toán ngưỡng biến động thông minh cho từng cặp tiền,
dựa trên dữ liệu lịch sử và các đặc điểm riêng của từng đồng coin.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("adaptive_volatility_threshold")

# Đường dẫn lưu cấu hình ngưỡng biến động
VOLATILITY_CONFIG_PATH = "configs/volatility_thresholds.json"

# Cấu hình mặc định theo nhóm tiền
DEFAULT_VOLATILITY_THRESHOLDS = {
    "BTC": 8.0,     # Bitcoin có biến động cao hơn
    "ETH": 7.0,     # Ethereum cũng khá biến động
    "BNB": 6.0,     # Binance Coin 
    "SOL": 9.0,     # Solana có biến động cao
    "ADA": 8.0,     # Cardano
    "XRP": 7.0,     # Ripple
    "DOT": 9.0,     # Polkadot
    "DOGE": 10.0,   # Dogecoin biến động rất cao
    "SHIB": 12.0,   # Shiba Inu biến động rất cao
    "AVAX": 9.0,    # Avalanche
    "default": 5.0  # Ngưỡng mặc định cho các cặp khác
}

class AdaptiveVolatilityThreshold:
    """Lớp quản lý ngưỡng biến động thông minh"""
    
    def __init__(self, binance_api=None):
        """
        Khởi tạo quản lý ngưỡng biến động
        
        Args:
            binance_api: Đối tượng BinanceAPI (tùy chọn)
        """
        self.binance_api = binance_api
        self.thresholds = self._load_or_create_config()
        self.volatility_history = {}
        
    def _load_or_create_config(self) -> Dict:
        """
        Tải hoặc tạo cấu hình ngưỡng biến động
        
        Returns:
            Dict: Cấu hình ngưỡng biến động
        """
        if os.path.exists(VOLATILITY_CONFIG_PATH):
            try:
                with open(VOLATILITY_CONFIG_PATH, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình ngưỡng biến động từ {VOLATILITY_CONFIG_PATH}")
                return config
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình ngưỡng biến động: {str(e)}")
        
        # Tạo cấu hình mặc định
        logger.info("Tạo cấu hình ngưỡng biến động mặc định")
        
        config = {
            "static_thresholds": DEFAULT_VOLATILITY_THRESHOLDS,
            "use_adaptive_thresholds": True,
            "adaptive_settings": {
                "lookback_periods": 30,
                "min_threshold": 3.0,
                "max_threshold": 15.0,
                "std_multiplier": 1.5
            },
            "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Lưu cấu hình
        try:
            os.makedirs(os.path.dirname(VOLATILITY_CONFIG_PATH), exist_ok=True)
            with open(VOLATILITY_CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=4)
            logger.info(f"Đã tạo cấu hình ngưỡng biến động mặc định tại {VOLATILITY_CONFIG_PATH}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình ngưỡng biến động: {str(e)}")
        
        return config
    
    def save_config(self) -> bool:
        """
        Lưu cấu hình ngưỡng biến động
        
        Returns:
            bool: True nếu lưu thành công, False nếu lỗi
        """
        try:
            # Cập nhật thời gian
            self.thresholds["last_updated"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Đảm bảo thư mục tồn tại
            os.makedirs(os.path.dirname(VOLATILITY_CONFIG_PATH), exist_ok=True)
            
            # Lưu cấu hình
            with open(VOLATILITY_CONFIG_PATH, 'w') as f:
                json.dump(self.thresholds, f, indent=4)
            
            logger.info(f"Đã lưu cấu hình ngưỡng biến động vào {VOLATILITY_CONFIG_PATH}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình ngưỡng biến động: {str(e)}")
            return False
    
    def get_volatility_threshold(self, symbol: str) -> float:
        """
        Lấy ngưỡng biến động cho một cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền (ví dụ: BTCUSDT)
            
        Returns:
            float: Ngưỡng biến động
        """
        # Xác định base currency
        base_currency = self._extract_base_currency(symbol)
        
        # Nếu sử dụng ngưỡng thích ứng
        if self.thresholds.get("use_adaptive_thresholds", True):
            # Tính ngưỡng thích ứng dựa trên dữ liệu lịch sử
            adaptive_threshold = self._calculate_adaptive_threshold(symbol)
            if adaptive_threshold is not None:
                return adaptive_threshold
        
        # Lấy ngưỡng tĩnh từ cấu hình
        static_thresholds = self.thresholds.get("static_thresholds", DEFAULT_VOLATILITY_THRESHOLDS)
        return static_thresholds.get(base_currency, static_thresholds.get("default", 5.0))
    
    def _extract_base_currency(self, symbol: str) -> str:
        """
        Trích xuất base currency từ mã cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền (ví dụ: BTCUSDT)
            
        Returns:
            str: Base currency (ví dụ: BTC)
        """
        # Loại bỏ các đuôi phổ biến
        common_quote_currencies = ["USDT", "BUSD", "USDC", "USD", "TUSD", "DAI", "FDUSD"]
        
        for quote in common_quote_currencies:
            if symbol.endswith(quote):
                return symbol[:-len(quote)]
        
        # Nếu không tìm thấy, trả về mã ban đầu
        return symbol
    
    def update_volatility_history(self, symbol: str, volatility: float) -> None:
        """
        Cập nhật lịch sử biến động cho một cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền
            volatility (float): Giá trị biến động
        """
        if symbol not in self.volatility_history:
            self.volatility_history[symbol] = []
        
        # Thêm giá trị biến động mới
        self.volatility_history[symbol].append({
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "value": volatility
        })
        
        # Giới hạn kích thước lịch sử
        max_history = self.thresholds.get("adaptive_settings", {}).get("lookback_periods", 30)
        if len(self.volatility_history[symbol]) > max_history:
            self.volatility_history[symbol] = self.volatility_history[symbol][-max_history:]
    
    def _calculate_adaptive_threshold(self, symbol: str) -> Optional[float]:
        """
        Tính toán ngưỡng biến động thích ứng dựa trên dữ liệu lịch sử
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            Optional[float]: Ngưỡng biến động thích ứng, hoặc None nếu không đủ dữ liệu
        """
        # Lấy dữ liệu lịch sử biến động
        if symbol not in self.volatility_history or len(self.volatility_history[symbol]) < 5:
            # Không đủ dữ liệu
            if self.binance_api:
                # Thử lấy dữ liệu lịch sử từ API
                historical_volatility = self._get_historical_volatility(symbol)
                if historical_volatility:
                    # Bổ sung vào lịch sử
                    for vol in historical_volatility:
                        self.update_volatility_history(symbol, vol)
                else:
                    return None
            else:
                return None
        
        # Lấy cài đặt
        settings = self.thresholds.get("adaptive_settings", {})
        min_threshold = settings.get("min_threshold", 3.0)
        max_threshold = settings.get("max_threshold", 15.0)
        std_multiplier = settings.get("std_multiplier", 1.5)
        
        # Lấy các giá trị biến động
        volatility_values = [entry["value"] for entry in self.volatility_history[symbol]]
        
        # Tính toán ngưỡng thích ứng
        mean_volatility = np.mean(volatility_values)
        std_volatility = np.std(volatility_values)
        
        # Ngưỡng = Trung bình + std_multiplier * Độ lệch chuẩn
        adaptive_threshold = mean_volatility + std_multiplier * std_volatility
        
        # Giới hạn trong khoảng min-max
        adaptive_threshold = max(min_threshold, min(adaptive_threshold, max_threshold))
        
        return adaptive_threshold
    
    def _get_historical_volatility(self, symbol: str) -> List[float]:
        """
        Lấy dữ liệu biến động lịch sử từ API
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            List[float]: Danh sách các giá trị biến động
        """
        if not self.binance_api:
            return []
        
        try:
            # Lấy dữ liệu giá từ API
            lookback = self.thresholds.get("adaptive_settings", {}).get("lookback_periods", 30)
            klines = self.binance_api.get_klines(symbol=symbol, interval="1d", limit=lookback+1)
            
            if not klines or len(klines) < 2:
                return []
            
            # Tính biến động hàng ngày
            volatility_values = []
            for i in range(1, len(klines)):
                prev_close = float(klines[i-1][4])
                high = float(klines[i][2])
                low = float(klines[i][3])
                
                # Biến động = (high - low) / prev_close * 100
                volatility = (high - low) / prev_close * 100
                volatility_values.append(volatility)
            
            return volatility_values
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu biến động lịch sử: {str(e)}")
            return []
    
    def set_static_threshold(self, currency: str, threshold: float) -> bool:
        """
        Đặt ngưỡng biến động tĩnh cho một đồng tiền
        
        Args:
            currency (str): Mã đồng tiền (ví dụ: BTC)
            threshold (float): Ngưỡng biến động
            
        Returns:
            bool: True nếu thành công, False nếu lỗi
        """
        try:
            # Đảm bảo threshold nằm trong khoảng hợp lý
            if threshold < 0:
                logger.warning(f"Ngưỡng biến động không thể âm. Đặt ngưỡng cho {currency} thành 0")
                threshold = 0
            
            # Cập nhật ngưỡng
            static_thresholds = self.thresholds.get("static_thresholds", {})
            static_thresholds[currency] = threshold
            self.thresholds["static_thresholds"] = static_thresholds
            
            # Lưu cấu hình
            self.save_config()
            
            logger.info(f"Đã đặt ngưỡng biến động tĩnh cho {currency}: {threshold}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi đặt ngưỡng biến động tĩnh: {str(e)}")
            return False
    
    def toggle_adaptive_threshold(self, enabled: bool) -> bool:
        """
        Bật/tắt tính năng ngưỡng biến động thích ứng
        
        Args:
            enabled (bool): True để bật, False để tắt
            
        Returns:
            bool: True nếu thành công, False nếu lỗi
        """
        try:
            self.thresholds["use_adaptive_thresholds"] = enabled
            self.save_config()
            
            status = "bật" if enabled else "tắt"
            logger.info(f"Đã {status} tính năng ngưỡng biến động thích ứng")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi {status} tính năng ngưỡng biến động thích ứng: {str(e)}")
            return False
    
    def update_adaptive_settings(self, settings: Dict) -> bool:
        """
        Cập nhật cài đặt ngưỡng biến động thích ứng
        
        Args:
            settings (Dict): Cài đặt mới
            
        Returns:
            bool: True nếu thành công, False nếu lỗi
        """
        try:
            # Kiểm tra các cài đặt bắt buộc
            required_settings = ["lookback_periods", "min_threshold", "max_threshold", "std_multiplier"]
            for setting in required_settings:
                if setting not in settings:
                    logger.error(f"Thiếu cài đặt bắt buộc: {setting}")
                    return False
            
            # Cập nhật cài đặt
            self.thresholds["adaptive_settings"] = settings
            self.save_config()
            
            logger.info(f"Đã cập nhật cài đặt ngưỡng biến động thích ứng")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật cài đặt ngưỡng biến động thích ứng: {str(e)}")
            return False

def main():
    """Hàm chính để test module"""
    
    try:
        # Khởi tạo
        from binance_api import BinanceAPI
        api = BinanceAPI()
        volatility_manager = AdaptiveVolatilityThreshold(api)
        
        # Test các chức năng
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "DOGEUSDT"]
        
        print("=== Ngưỡng biến động theo cặp tiền ===")
        for symbol in symbols:
            threshold = volatility_manager.get_volatility_threshold(symbol)
            print(f"{symbol}: {threshold:.2f}%")
        
        # Test cập nhật lịch sử
        print("\n=== Cập nhật lịch sử biến động ===")
        for symbol in symbols:
            # Giả lập một số giá trị biến động
            for i in range(10):
                volatility = np.random.uniform(2.0, 12.0)
                volatility_manager.update_volatility_history(symbol, volatility)
            
            print(f"{symbol}: Đã cập nhật {len(volatility_manager.volatility_history.get(symbol, []))} bản ghi")
        
        # Test ngưỡng thích ứng
        print("\n=== Ngưỡng biến động thích ứng ===")
        for symbol in symbols:
            threshold = volatility_manager._calculate_adaptive_threshold(symbol)
            print(f"{symbol}: {threshold:.2f}%")
        
        # Test set ngưỡng tĩnh
        print("\n=== Cập nhật ngưỡng tĩnh ===")
        base_currencies = [volatility_manager._extract_base_currency(symbol) for symbol in symbols]
        for currency in base_currencies:
            threshold = np.random.uniform(4.0, 10.0)
            volatility_manager.set_static_threshold(currency, threshold)
            print(f"{currency}: {threshold:.2f}%")
        
        print("\n=== Cấu hình hiện tại ===")
        import json
        print(json.dumps(volatility_manager.thresholds, indent=4))
        
    except Exception as e:
        logger.error(f"Lỗi khi chạy test: {str(e)}")

if __name__ == "__main__":
    main()