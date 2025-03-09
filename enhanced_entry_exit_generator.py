#!/usr/bin/env python3
"""
Module sinh điểm vào/ra lệnh nâng cao (Enhanced Entry/Exit Generator)

Module này cung cấp các phương pháp nâng cao để tạo điểm vào lệnh và điểm thoát lệnh
dự phòng khi không tìm thấy điểm vào/ra rõ ràng từ phân tích kỹ thuật.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
from datetime import datetime, timedelta

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("enhanced_entry_exit_generator")

# Đường dẫn lưu cấu hình
ENTRY_EXIT_CONFIG_PATH = "configs/entry_exit_generator_config.json"

class EnhancedEntryExitGenerator:
    """Lớp sinh điểm vào/ra lệnh nâng cao"""
    
    def __init__(self, binance_api=None):
        """
        Khởi tạo trình sinh điểm vào/ra lệnh
        
        Args:
            binance_api: Đối tượng BinanceAPI (tùy chọn)
        """
        self.binance_api = binance_api
        self.config = self._load_or_create_config()
        
    def _load_or_create_config(self) -> Dict:
        """
        Tải hoặc tạo cấu hình mặc định
        
        Returns:
            Dict: Cấu hình điểm vào/ra lệnh
        """
        if os.path.exists(ENTRY_EXIT_CONFIG_PATH):
            try:
                with open(ENTRY_EXIT_CONFIG_PATH, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình sinh điểm vào/ra từ {ENTRY_EXIT_CONFIG_PATH}")
                return config
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình sinh điểm vào/ra: {str(e)}")
        
        # Tạo cấu hình mặc định
        logger.info("Tạo cấu hình sinh điểm vào/ra mặc định")
        
        config = {
            "entry_methods": {
                "primary": "support_resistance",
                "fallbacks": ["atr_based", "volatility_bands", "fibonacci_retracement"]
            },
            "exit_methods": {
                "take_profit": {
                    "primary": "atr_based",
                    "fallbacks": ["fixed_risk_reward", "fibonacci_extension"]
                },
                "stop_loss": {
                    "primary": "swing_points",
                    "fallbacks": ["atr_based", "percent_based"]
                }
            },
            "atr_settings": {
                "period": 14,
                "entry_multiplier": 0.2,
                "sl_multiplier": 1.5,
                "tp_multiplier": {
                    "trending": 2.5,
                    "ranging": 1.5,
                    "volatile": 3.0,
                    "quiet": 1.0
                }
            },
            "fixed_risk_reward_ratio": {
                "trending": 3.0,
                "ranging": 1.5,
                "volatile": 2.0,
                "quiet": 1.5
            },
            "percent_based": {
                "entry_offset": {
                    "BTC": 0.5,
                    "ETH": 1.0,
                    "default": 1.5
                },
                "sl_percent": {
                    "BTC": 2.0,
                    "ETH": 3.0,
                    "default": 5.0
                },
                "tp_percent": {
                    "BTC": 5.0,
                    "ETH": 7.0,
                    "default": 10.0
                }
            },
            "support_resistance_settings": {
                "swing_lookback": 20,
                "pivot_strength": 3,
                "min_distance_percent": 0.5
            },
            "market_regime_adjustments": {
                "trending": {
                    "entry_bias": 0.2,  # Buy closer to current price in trending market
                    "sl_wider": False,
                    "tp_wider": True
                },
                "ranging": {
                    "entry_bias": -0.2,  # Buy deeper dips in ranging market
                    "sl_wider": True,
                    "tp_wider": False
                },
                "volatile": {
                    "entry_bias": -0.5,  # Buy much deeper in volatile market
                    "sl_wider": True,
                    "tp_wider": True
                },
                "quiet": {
                    "entry_bias": 0.1,  # Buy closer in quiet market
                    "sl_wider": False,
                    "tp_wider": False
                }
            },
            "currency_specific": {
                "BTC": {
                    "min_swing_strength": 2
                },
                "ETH": {
                    "min_swing_strength": 2
                }
                # Other currencies can be added here
            },
            "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Lưu cấu hình
        try:
            os.makedirs(os.path.dirname(ENTRY_EXIT_CONFIG_PATH), exist_ok=True)
            with open(ENTRY_EXIT_CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=4)
            logger.info(f"Đã tạo cấu hình sinh điểm vào/ra mặc định tại {ENTRY_EXIT_CONFIG_PATH}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình sinh điểm vào/ra: {str(e)}")
        
        return config
    
    def save_config(self) -> bool:
        """
        Lưu cấu hình hiện tại
        
        Returns:
            bool: True nếu lưu thành công, False nếu lỗi
        """
        try:
            # Cập nhật thời gian
            self.config["last_updated"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Đảm bảo thư mục tồn tại
            os.makedirs(os.path.dirname(ENTRY_EXIT_CONFIG_PATH), exist_ok=True)
            
            # Lưu cấu hình
            with open(ENTRY_EXIT_CONFIG_PATH, 'w') as f:
                json.dump(self.config, f, indent=4)
            
            logger.info(f"Đã lưu cấu hình sinh điểm vào/ra vào {ENTRY_EXIT_CONFIG_PATH}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình sinh điểm vào/ra: {str(e)}")
            return False
    
    def generate_entry_points(self, symbol: str, direction: str, current_price: float,
                            df: pd.DataFrame = None, market_regime: str = "ranging",
                            prefer_fallback: bool = False) -> List[float]:
        """
        Sinh điểm vào lệnh cho một cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền
            direction (str): Hướng giao dịch ('long' hoặc 'short')
            current_price (float): Giá hiện tại
            df (pd.DataFrame, optional): DataFrame chứa dữ liệu giá
            market_regime (str): Chế độ thị trường
            prefer_fallback (bool): Ưu tiên sử dụng phương pháp dự phòng
            
        Returns:
            List[float]: Danh sách các điểm vào lệnh
        """
        try:
            if df is None and self.binance_api:
                df = self._get_ohlcv_data(symbol)
            
            if df is None or df.empty:
                # Nếu không có dữ liệu, sử dụng phương pháp percent_based
                logger.warning(f"Không có dữ liệu cho {symbol}, sử dụng phương pháp percent_based")
                return self._generate_percent_based_entry(symbol, direction, current_price, market_regime)
            
            # Lấy phương pháp chính và dự phòng
            primary_method = self.config["entry_methods"]["primary"]
            fallback_methods = self.config["entry_methods"]["fallbacks"]
            
            # Nếu ưu tiên sử dụng fallback, đổi thứ tự
            if prefer_fallback and fallback_methods:
                methods = [fallback_methods[0], primary_method] + fallback_methods[1:]
            else:
                methods = [primary_method] + fallback_methods
            
            # Thử từng phương pháp
            for method in methods:
                try:
                    entry_points = []
                    
                    if method == "support_resistance":
                        entry_points = self._generate_sr_based_entry(symbol, direction, df, current_price, market_regime)
                    elif method == "atr_based":
                        entry_points = self._generate_atr_based_entry(symbol, direction, df, current_price, market_regime)
                    elif method == "volatility_bands":
                        entry_points = self._generate_volatility_band_entry(symbol, direction, df, current_price, market_regime)
                    elif method == "fibonacci_retracement":
                        entry_points = self._generate_fibonacci_entry(symbol, direction, df, current_price, market_regime)
                    elif method == "percent_based":
                        entry_points = self._generate_percent_based_entry(symbol, direction, current_price, market_regime)
                    
                    # Nếu có điểm vào, trả về
                    if entry_points and len(entry_points) > 0:
                        logger.info(f"Đã sinh {len(entry_points)} điểm vào cho {symbol} {direction} sử dụng phương pháp {method}")
                        return sorted(entry_points)
                    
                except Exception as e:
                    logger.error(f"Lỗi khi sinh điểm vào lệnh với phương pháp {method}: {str(e)}")
            
            # Nếu không thành công với bất kỳ phương pháp nào, sử dụng giá hiện tại
            logger.warning(f"Không thể sinh điểm vào cho {symbol} {direction}, sử dụng giá hiện tại")
            return [current_price]
            
        except Exception as e:
            logger.error(f"Lỗi khi sinh điểm vào lệnh: {str(e)}")
            # Trả về giá hiện tại nếu có lỗi
            return [current_price]
    
    def generate_exit_points(self, symbol: str, direction: str, entry_price: float,
                           df: pd.DataFrame = None, market_regime: str = "ranging",
                           prefer_fallback: bool = False) -> Dict[str, List[float]]:
        """
        Sinh điểm thoát lệnh (stop loss và take profit)
        
        Args:
            symbol (str): Mã cặp tiền
            direction (str): Hướng giao dịch ('long' hoặc 'short')
            entry_price (float): Giá vào lệnh
            df (pd.DataFrame, optional): DataFrame chứa dữ liệu giá
            market_regime (str): Chế độ thị trường
            prefer_fallback (bool): Ưu tiên sử dụng phương pháp dự phòng
            
        Returns:
            Dict[str, List[float]]: Từ điển chứa stop_loss và take_profit
        """
        try:
            if df is None and self.binance_api:
                df = self._get_ohlcv_data(symbol)
            
            # Tạo kết quả mặc định trống
            result = {
                "stop_loss": [],
                "take_profit": []
            }
            
            # Sinh stop loss
            sl_points = self._generate_stop_loss(symbol, direction, entry_price, df, market_regime, prefer_fallback)
            if sl_points and len(sl_points) > 0:
                result["stop_loss"] = sorted(sl_points, reverse=(direction == "long"))
            
            # Sinh take profit
            tp_points = self._generate_take_profit(symbol, direction, entry_price, sl_points[0] if sl_points else None, df, market_regime, prefer_fallback)
            if tp_points and len(tp_points) > 0:
                result["take_profit"] = sorted(tp_points, reverse=(direction == "short"))
            
            # Nếu không có stops hoặc targets, dùng phương pháp percent_based
            if not result["stop_loss"]:
                result["stop_loss"] = self._generate_percent_based_sl(symbol, direction, entry_price, market_regime)
                logger.info(f"Đã sinh {len(result['stop_loss'])} điểm stop loss cho {symbol} {direction} sử dụng phương pháp percent_based")
            
            if not result["take_profit"]:
                result["take_profit"] = self._generate_percent_based_tp(symbol, direction, entry_price, market_regime)
                logger.info(f"Đã sinh {len(result['take_profit'])} điểm take profit cho {symbol} {direction} sử dụng phương pháp percent_based")
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi sinh điểm thoát lệnh: {str(e)}")
            # Trả về điểm thoát dựa trên phần trăm nếu có lỗi
            return {
                "stop_loss": self._generate_percent_based_sl(symbol, direction, entry_price, market_regime),
                "take_profit": self._generate_percent_based_tp(symbol, direction, entry_price, market_regime)
            }
    
    def _generate_stop_loss(self, symbol: str, direction: str, entry_price: float,
                          df: pd.DataFrame, market_regime: str, prefer_fallback: bool) -> List[float]:
        """
        Sinh điểm stop loss sử dụng nhiều phương pháp
        
        Args:
            symbol (str): Mã cặp tiền
            direction (str): Hướng giao dịch ('long' hoặc 'short')
            entry_price (float): Giá vào lệnh
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            market_regime (str): Chế độ thị trường
            prefer_fallback (bool): Ưu tiên sử dụng phương pháp dự phòng
            
        Returns:
            List[float]: Danh sách các điểm stop loss
        """
        # Lấy phương pháp chính và dự phòng
        primary_method = self.config["exit_methods"]["stop_loss"]["primary"]
        fallback_methods = self.config["exit_methods"]["stop_loss"]["fallbacks"]
        
        # Nếu ưu tiên sử dụng fallback, đổi thứ tự
        if prefer_fallback and fallback_methods:
            methods = [fallback_methods[0], primary_method] + fallback_methods[1:]
        else:
            methods = [primary_method] + fallback_methods
        
        # Thử từng phương pháp
        for method in methods:
            try:
                sl_points = []
                
                if method == "swing_points":
                    sl_points = self._generate_swing_based_sl(symbol, direction, df, entry_price, market_regime)
                elif method == "atr_based":
                    sl_points = self._generate_atr_based_sl(symbol, direction, df, entry_price, market_regime)
                elif method == "percent_based":
                    sl_points = self._generate_percent_based_sl(symbol, direction, entry_price, market_regime)
                
                # Nếu có điểm stop loss, trả về
                if sl_points and len(sl_points) > 0:
                    logger.info(f"Đã sinh {len(sl_points)} điểm stop loss cho {symbol} {direction} sử dụng phương pháp {method}")
                    return sl_points
                
            except Exception as e:
                logger.error(f"Lỗi khi sinh điểm stop loss với phương pháp {method}: {str(e)}")
        
        # Nếu không thành công với bất kỳ phương pháp nào, sử dụng percent_based
        logger.warning(f"Không thể sinh điểm stop loss cho {symbol} {direction}, sử dụng phương pháp percent_based")
        return self._generate_percent_based_sl(symbol, direction, entry_price, market_regime)
    
    def _generate_take_profit(self, symbol: str, direction: str, entry_price: float,
                            stop_loss: float, df: pd.DataFrame, market_regime: str,
                            prefer_fallback: bool) -> List[float]:
        """
        Sinh điểm take profit sử dụng nhiều phương pháp
        
        Args:
            symbol (str): Mã cặp tiền
            direction (str): Hướng giao dịch ('long' hoặc 'short')
            entry_price (float): Giá vào lệnh
            stop_loss (float): Giá stop loss
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            market_regime (str): Chế độ thị trường
            prefer_fallback (bool): Ưu tiên sử dụng phương pháp dự phòng
            
        Returns:
            List[float]: Danh sách các điểm take profit
        """
        # Lấy phương pháp chính và dự phòng
        primary_method = self.config["exit_methods"]["take_profit"]["primary"]
        fallback_methods = self.config["exit_methods"]["take_profit"]["fallbacks"]
        
        # Nếu ưu tiên sử dụng fallback, đổi thứ tự
        if prefer_fallback and fallback_methods:
            methods = [fallback_methods[0], primary_method] + fallback_methods[1:]
        else:
            methods = [primary_method] + fallback_methods
        
        # Thử từng phương pháp
        for method in methods:
            try:
                tp_points = []
                
                if method == "atr_based":
                    tp_points = self._generate_atr_based_tp(symbol, direction, df, entry_price, market_regime)
                elif method == "fixed_risk_reward":
                    if stop_loss is not None:
                        tp_points = self._generate_risk_reward_tp(symbol, direction, entry_price, stop_loss, market_regime)
                    else:
                        # Nếu không có stop loss, bỏ qua phương pháp này
                        continue
                elif method == "fibonacci_extension":
                    tp_points = self._generate_fibonacci_tp(symbol, direction, df, entry_price, market_regime)
                elif method == "percent_based":
                    tp_points = self._generate_percent_based_tp(symbol, direction, entry_price, market_regime)
                
                # Nếu có điểm take profit, trả về
                if tp_points and len(tp_points) > 0:
                    logger.info(f"Đã sinh {len(tp_points)} điểm take profit cho {symbol} {direction} sử dụng phương pháp {method}")
                    return tp_points
                
            except Exception as e:
                logger.error(f"Lỗi khi sinh điểm take profit với phương pháp {method}: {str(e)}")
        
        # Nếu không thành công với bất kỳ phương pháp nào, sử dụng percent_based
        logger.warning(f"Không thể sinh điểm take profit cho {symbol} {direction}, sử dụng phương pháp percent_based")
        return self._generate_percent_based_tp(symbol, direction, entry_price, market_regime)
    
    def _generate_sr_based_entry(self, symbol: str, direction: str, df: pd.DataFrame,
                              current_price: float, market_regime: str) -> List[float]:
        """
        Sinh điểm vào lệnh dựa trên hỗ trợ/kháng cự
        
        Args:
            symbol (str): Mã cặp tiền
            direction (str): Hướng giao dịch ('long' hoặc 'short')
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            current_price (float): Giá hiện tại
            market_regime (str): Chế độ thị trường
            
        Returns:
            List[float]: Danh sách các điểm vào lệnh
        """
        try:
            # Lấy cài đặt
            settings = self.config["support_resistance_settings"]
            lookback = settings.get("swing_lookback", 20)
            strength = settings.get("pivot_strength", 3)
            min_distance = settings.get("min_distance_percent", 0.5) / 100
            
            # Điều chỉnh theo cặp tiền cụ thể
            base_currency = self._extract_base_currency(symbol)
            if base_currency in self.config.get("currency_specific", {}):
                currency_settings = self.config["currency_specific"][base_currency]
                if "min_swing_strength" in currency_settings:
                    strength = currency_settings["min_swing_strength"]
            
            # Điều chỉnh theo chế độ thị trường
            bias = self.config["market_regime_adjustments"].get(market_regime, {}).get("entry_bias", 0)
            
            # Tìm các điểm swing
            swings = self._find_swing_points(df, strength)
            
            entry_points = []
            
            if direction == "long":
                # Tìm các mức hỗ trợ gần đây dưới giá hiện tại
                supports = [swing for swing in swings["lows"] if swing < current_price]
                
                if not supports:
                    return []
                
                # Sắp xếp theo khoảng cách với giá hiện tại
                supports.sort(key=lambda x: current_price - x)
                
                # Lọc bỏ các mức quá gần hoặc quá xa giá hiện tại
                filtered_supports = []
                for support in supports:
                    distance_percent = (current_price - support) / current_price
                    if distance_percent >= min_distance and distance_percent <= min_distance * 5:
                        filtered_supports.append(support)
                
                # Điều chỉnh theo bias
                if filtered_supports:
                    base_entry = filtered_supports[0]
                    bias_adjustment = (current_price - base_entry) * bias
                    adjusted_entry = base_entry + bias_adjustment
                    entry_points.append(round(adjusted_entry, 2))
                
                    # Thêm một số mức hỗ trợ khác nếu có
                    if len(filtered_supports) > 1:
                        entry_points.append(round(filtered_supports[1], 2))
                
            else:  # direction == "short"
                # Tìm các mức kháng cự gần đây trên giá hiện tại
                resistances = [swing for swing in swings["highs"] if swing > current_price]
                
                if not resistances:
                    return []
                
                # Sắp xếp theo khoảng cách với giá hiện tại
                resistances.sort(key=lambda x: x - current_price)
                
                # Lọc bỏ các mức quá gần hoặc quá xa giá hiện tại
                filtered_resistances = []
                for resistance in resistances:
                    distance_percent = (resistance - current_price) / current_price
                    if distance_percent >= min_distance and distance_percent <= min_distance * 5:
                        filtered_resistances.append(resistance)
                
                # Điều chỉnh theo bias
                if filtered_resistances:
                    base_entry = filtered_resistances[0]
                    bias_adjustment = (base_entry - current_price) * bias
                    adjusted_entry = base_entry - bias_adjustment
                    entry_points.append(round(adjusted_entry, 2))
                
                    # Thêm một số mức kháng cự khác nếu có
                    if len(filtered_resistances) > 1:
                        entry_points.append(round(filtered_resistances[1], 2))
            
            return entry_points
        
        except Exception as e:
            logger.error(f"Lỗi khi sinh điểm vào dựa trên hỗ trợ/kháng cự: {str(e)}")
            return []
    
    def _generate_atr_based_entry(self, symbol: str, direction: str, df: pd.DataFrame,
                               current_price: float, market_regime: str) -> List[float]:
        """
        Sinh điểm vào lệnh dựa trên ATR
        
        Args:
            symbol (str): Mã cặp tiền
            direction (str): Hướng giao dịch ('long' hoặc 'short')
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            current_price (float): Giá hiện tại
            market_regime (str): Chế độ thị trường
            
        Returns:
            List[float]: Danh sách các điểm vào lệnh
        """
        try:
            # Tính ATR
            atr_period = self.config["atr_settings"]["period"]
            atr = self._calculate_atr(df, atr_period)
            
            if not atr:
                return []
            
            # Lấy hệ số điều chỉnh
            entry_multiplier = self.config["atr_settings"]["entry_multiplier"]
            
            # Điều chỉnh theo chế độ thị trường
            bias = self.config["market_regime_adjustments"].get(market_regime, {}).get("entry_bias", 0)
            
            # Tính điểm vào lệnh
            entry_points = []
            
            if direction == "long":
                # Điểm vào dưới giá hiện tại
                entry = current_price - atr * entry_multiplier
                # Điều chỉnh theo bias
                bias_adjustment = atr * entry_multiplier * bias
                adjusted_entry = entry + bias_adjustment
                entry_points.append(round(adjusted_entry, 2))
                
                # Thêm một điểm vào sâu hơn
                deep_entry = adjusted_entry - atr * entry_multiplier
                entry_points.append(round(deep_entry, 2))
                
            else:  # direction == "short"
                # Điểm vào trên giá hiện tại
                entry = current_price + atr * entry_multiplier
                # Điều chỉnh theo bias
                bias_adjustment = atr * entry_multiplier * bias
                adjusted_entry = entry - bias_adjustment
                entry_points.append(round(adjusted_entry, 2))
                
                # Thêm một điểm vào cao hơn
                high_entry = adjusted_entry + atr * entry_multiplier
                entry_points.append(round(high_entry, 2))
            
            return entry_points
        
        except Exception as e:
            logger.error(f"Lỗi khi sinh điểm vào dựa trên ATR: {str(e)}")
            return []
    
    def _generate_volatility_band_entry(self, symbol: str, direction: str, df: pd.DataFrame,
                                     current_price: float, market_regime: str) -> List[float]:
        """
        Sinh điểm vào lệnh dựa trên volatility bands
        
        Args:
            symbol (str): Mã cặp tiền
            direction (str): Hướng giao dịch ('long' hoặc 'short')
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            current_price (float): Giá hiện tại
            market_regime (str): Chế độ thị trường
            
        Returns:
            List[float]: Danh sách các điểm vào lệnh
        """
        try:
            # Tính SMA và độ lệch chuẩn
            period = 20
            if len(df) < period:
                return []
            
            df['sma'] = df['close'].rolling(window=period).mean()
            df['std'] = df['close'].rolling(window=period).std()
            
            if df['sma'].iloc[-1] is np.nan or df['std'].iloc[-1] is np.nan:
                return []
            
            sma = df['sma'].iloc[-1]
            std = df['std'].iloc[-1]
            
            # Tính volatility bands
            upper_band_1 = sma + 1 * std
            lower_band_1 = sma - 1 * std
            upper_band_2 = sma + 2 * std
            lower_band_2 = sma - 2 * std
            
            # Điều chỉnh theo chế độ thị trường
            bias = self.config["market_regime_adjustments"].get(market_regime, {}).get("entry_bias", 0)
            
            # Tính điểm vào lệnh
            entry_points = []
            
            if direction == "long":
                # Mua khi giá tiếp cận lower band
                if current_price > lower_band_1:
                    entry = lower_band_1
                else:
                    entry = lower_band_2
                
                # Điều chỉnh theo bias
                bias_adjustment = std * bias
                adjusted_entry = entry + bias_adjustment
                entry_points.append(round(adjusted_entry, 2))
                
                # Thêm một điểm vào sâu hơn
                entry_points.append(round(lower_band_2, 2))
                
            else:  # direction == "short"
                # Bán khi giá tiếp cận upper band
                if current_price < upper_band_1:
                    entry = upper_band_1
                else:
                    entry = upper_band_2
                
                # Điều chỉnh theo bias
                bias_adjustment = std * bias
                adjusted_entry = entry - bias_adjustment
                entry_points.append(round(adjusted_entry, 2))
                
                # Thêm một điểm vào cao hơn
                entry_points.append(round(upper_band_2, 2))
            
            return entry_points
        
        except Exception as e:
            logger.error(f"Lỗi khi sinh điểm vào dựa trên volatility bands: {str(e)}")
            return []
    
    def _generate_fibonacci_entry(self, symbol: str, direction: str, df: pd.DataFrame,
                               current_price: float, market_regime: str) -> List[float]:
        """
        Sinh điểm vào lệnh dựa trên Fibonacci retracement
        
        Args:
            symbol (str): Mã cặp tiền
            direction (str): Hướng giao dịch ('long' hoặc 'short')
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            current_price (float): Giá hiện tại
            market_regime (str): Chế độ thị trường
            
        Returns:
            List[float]: Danh sách các điểm vào lệnh
        """
        try:
            # Tìm swing high/low gần nhất
            lookback = 30
            if len(df) < lookback:
                return []
            
            recent_df = df.iloc[-lookback:]
            
            if direction == "long":
                # Tìm swing high và swing low gần nhất cho xu hướng giảm -> retracement tăng
                swing_high = recent_df['high'].max()
                swing_high_idx = recent_df['high'].idxmax()
                
                # Tìm swing low sau swing high
                if swing_high_idx == recent_df.index[-1]:
                    # Nếu swing high là điểm cuối cùng, không thể tìm swing low
                    return []
                
                swing_low = recent_df.loc[swing_high_idx:]['low'].min()
                
                if swing_high <= swing_low:
                    return []
                
                # Tính các mức Fibonacci retracement
                diff = swing_high - swing_low
                fib_38 = swing_low + 0.382 * diff
                fib_50 = swing_low + 0.5 * diff
                fib_61 = swing_low + 0.618 * diff
                
                # Tính điểm vào lệnh dựa trên mức giá hiện tại
                entry_points = []
                
                if current_price < fib_38:
                    # Giá thấp hơn mức 38.2%, dùng mức này làm điểm vào
                    entry_points.append(round(fib_38, 2))
                    entry_points.append(round(fib_50, 2))
                elif current_price < fib_50:
                    # Giá giữa mức 38.2% và 50%, dùng mức 50% làm điểm vào
                    entry_points.append(round(fib_50, 2))
                    entry_points.append(round(fib_38, 2))
                elif current_price < fib_61:
                    # Giá giữa mức 50% và 61.8%, dùng mức 61.8% làm điểm vào
                    entry_points.append(round(fib_61, 2))
                    entry_points.append(round(fib_50, 2))
                else:
                    # Giá cao hơn mức 61.8%, không vào lệnh
                    return []
                
            else:  # direction == "short"
                # Tìm swing low và swing high gần nhất cho xu hướng tăng -> retracement giảm
                swing_low = recent_df['low'].min()
                swing_low_idx = recent_df['low'].idxmin()
                
                # Tìm swing high sau swing low
                if swing_low_idx == recent_df.index[-1]:
                    # Nếu swing low là điểm cuối cùng, không thể tìm swing high
                    return []
                
                swing_high = recent_df.loc[swing_low_idx:]['high'].max()
                
                if swing_low >= swing_high:
                    return []
                
                # Tính các mức Fibonacci retracement
                diff = swing_high - swing_low
                fib_38 = swing_high - 0.382 * diff
                fib_50 = swing_high - 0.5 * diff
                fib_61 = swing_high - 0.618 * diff
                
                # Tính điểm vào lệnh dựa trên mức giá hiện tại
                entry_points = []
                
                if current_price > fib_38:
                    # Giá cao hơn mức 38.2%, dùng mức này làm điểm vào
                    entry_points.append(round(fib_38, 2))
                    entry_points.append(round(fib_50, 2))
                elif current_price > fib_50:
                    # Giá giữa mức 38.2% và 50%, dùng mức 50% làm điểm vào
                    entry_points.append(round(fib_50, 2))
                    entry_points.append(round(fib_38, 2))
                elif current_price > fib_61:
                    # Giá giữa mức 50% và 61.8%, dùng mức 61.8% làm điểm vào
                    entry_points.append(round(fib_61, 2))
                    entry_points.append(round(fib_50, 2))
                else:
                    # Giá thấp hơn mức 61.8%, không vào lệnh
                    return []
            
            return entry_points
        
        except Exception as e:
            logger.error(f"Lỗi khi sinh điểm vào dựa trên Fibonacci retracement: {str(e)}")
            return []
    
    def _generate_percent_based_entry(self, symbol: str, direction: str, current_price: float,
                                    market_regime: str) -> List[float]:
        """
        Sinh điểm vào lệnh dựa trên phần trăm offset
        
        Args:
            symbol (str): Mã cặp tiền
            direction (str): Hướng giao dịch ('long' hoặc 'short')
            current_price (float): Giá hiện tại
            market_regime (str): Chế độ thị trường
            
        Returns:
            List[float]: Danh sách các điểm vào lệnh
        """
        try:
            # Lấy cài đặt
            base_currency = self._extract_base_currency(symbol)
            offset_pct = self.config["percent_based"]["entry_offset"].get(
                base_currency, self.config["percent_based"]["entry_offset"].get("default", 1.5)) / 100
            
            # Điều chỉnh theo chế độ thị trường
            market_multiplier = {
                "trending": 0.8,
                "ranging": 1.0,
                "volatile": 1.5,
                "quiet": 0.5
            }.get(market_regime, 1.0)
            
            offset_pct *= market_multiplier
            
            # Tính điểm vào lệnh
            entry_points = []
            
            if direction == "long":
                # Điểm vào dưới giá hiện tại
                entry_1 = current_price * (1 - offset_pct)
                entry_2 = current_price * (1 - offset_pct * 1.5)
                entry_points.append(round(entry_1, 2))
                entry_points.append(round(entry_2, 2))
                
            else:  # direction == "short"
                # Điểm vào trên giá hiện tại
                entry_1 = current_price * (1 + offset_pct)
                entry_2 = current_price * (1 + offset_pct * 1.5)
                entry_points.append(round(entry_1, 2))
                entry_points.append(round(entry_2, 2))
            
            return entry_points
        
        except Exception as e:
            logger.error(f"Lỗi khi sinh điểm vào dựa trên phần trăm: {str(e)}")
            # Trả về mặc định nếu có lỗi
            if direction == "long":
                return [round(current_price * 0.99, 2), round(current_price * 0.98, 2)]
            else:
                return [round(current_price * 1.01, 2), round(current_price * 1.02, 2)]
    
    def _generate_swing_based_sl(self, symbol: str, direction: str, df: pd.DataFrame,
                               entry_price: float, market_regime: str) -> List[float]:
        """
        Sinh điểm stop loss dựa trên swing points
        
        Args:
            symbol (str): Mã cặp tiền
            direction (str): Hướng giao dịch ('long' hoặc 'short')
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            entry_price (float): Giá vào lệnh
            market_regime (str): Chế độ thị trường
            
        Returns:
            List[float]: Danh sách các điểm stop loss
        """
        try:
            # Lấy cài đặt
            settings = self.config["support_resistance_settings"]
            lookback = settings.get("swing_lookback", 20)
            strength = settings.get("pivot_strength", 3)
            
            # Điều chỉnh theo cặp tiền cụ thể
            base_currency = self._extract_base_currency(symbol)
            if base_currency in self.config.get("currency_specific", {}):
                currency_settings = self.config["currency_specific"][base_currency]
                if "min_swing_strength" in currency_settings:
                    strength = currency_settings["min_swing_strength"]
            
            # Tìm các điểm swing
            swings = self._find_swing_points(df, strength)
            
            # Kiểm tra nếu cần điều chỉnh stop loss rộng hơn
            wider_sl = self.config["market_regime_adjustments"].get(market_regime, {}).get("sl_wider", False)
            
            sl_points = []
            
            if direction == "long":
                # Tìm các mức swing low gần đây nhưng dưới điểm vào
                swing_lows = [low for low in swings["lows"] if low < entry_price]
                
                if not swing_lows:
                    # Không tìm thấy swing low thích hợp
                    return []
                
                # Sắp xếp theo khoảng cách với entry price (gần nhất trước)
                swing_lows.sort(key=lambda x: entry_price - x)
                
                # Lấy mức thích hợp tùy theo chế độ thị trường
                if wider_sl and len(swing_lows) > 1:
                    # Lấy mức thấp hơn (xa hơn)
                    sl_price = swing_lows[1]
                else:
                    # Lấy mức gần nhất
                    sl_price = swing_lows[0]
                
                # Thêm một chút buffer dưới mức swing low
                buffer = (entry_price - sl_price) * 0.1
                sl_price -= buffer
                
                sl_points.append(round(sl_price, 2))
                
            else:  # direction == "short"
                # Tìm các mức swing high gần đây nhưng trên điểm vào
                swing_highs = [high for high in swings["highs"] if high > entry_price]
                
                if not swing_highs:
                    # Không tìm thấy swing high thích hợp
                    return []
                
                # Sắp xếp theo khoảng cách với entry price (gần nhất trước)
                swing_highs.sort(key=lambda x: x - entry_price)
                
                # Lấy mức thích hợp tùy theo chế độ thị trường
                if wider_sl and len(swing_highs) > 1:
                    # Lấy mức cao hơn (xa hơn)
                    sl_price = swing_highs[1]
                else:
                    # Lấy mức gần nhất
                    sl_price = swing_highs[0]
                
                # Thêm một chút buffer trên mức swing high
                buffer = (sl_price - entry_price) * 0.1
                sl_price += buffer
                
                sl_points.append(round(sl_price, 2))
            
            return sl_points
        
        except Exception as e:
            logger.error(f"Lỗi khi sinh điểm stop loss dựa trên swing points: {str(e)}")
            return []
    
    def _generate_atr_based_sl(self, symbol: str, direction: str, df: pd.DataFrame,
                             entry_price: float, market_regime: str) -> List[float]:
        """
        Sinh điểm stop loss dựa trên ATR
        
        Args:
            symbol (str): Mã cặp tiền
            direction (str): Hướng giao dịch ('long' hoặc 'short')
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            entry_price (float): Giá vào lệnh
            market_regime (str): Chế độ thị trường
            
        Returns:
            List[float]: Danh sách các điểm stop loss
        """
        try:
            # Tính ATR
            atr_period = self.config["atr_settings"]["period"]
            atr = self._calculate_atr(df, atr_period)
            
            if not atr:
                return []
            
            # Lấy hệ số điều chỉnh
            sl_multiplier = self.config["atr_settings"]["sl_multiplier"]
            
            # Kiểm tra nếu cần điều chỉnh stop loss rộng hơn
            if self.config["market_regime_adjustments"].get(market_regime, {}).get("sl_wider", False):
                sl_multiplier *= 1.5
            
            # Tính điểm stop loss
            sl_points = []
            
            if direction == "long":
                sl_price = entry_price - atr * sl_multiplier
                sl_points.append(round(sl_price, 2))
                
            else:  # direction == "short"
                sl_price = entry_price + atr * sl_multiplier
                sl_points.append(round(sl_price, 2))
            
            return sl_points
        
        except Exception as e:
            logger.error(f"Lỗi khi sinh điểm stop loss dựa trên ATR: {str(e)}")
            return []
    
    def _generate_percent_based_sl(self, symbol: str, direction: str, entry_price: float,
                                 market_regime: str) -> List[float]:
        """
        Sinh điểm stop loss dựa trên phần trăm
        
        Args:
            symbol (str): Mã cặp tiền
            direction (str): Hướng giao dịch ('long' hoặc 'short')
            entry_price (float): Giá vào lệnh
            market_regime (str): Chế độ thị trường
            
        Returns:
            List[float]: Danh sách các điểm stop loss
        """
        try:
            # Lấy cài đặt
            base_currency = self._extract_base_currency(symbol)
            sl_pct = self.config["percent_based"]["sl_percent"].get(
                base_currency, self.config["percent_based"]["sl_percent"].get("default", 5.0)) / 100
            
            # Điều chỉnh theo chế độ thị trường
            market_multiplier = {
                "trending": 0.8,
                "ranging": 1.0,
                "volatile": 1.5,
                "quiet": 0.7
            }.get(market_regime, 1.0)
            
            # Kiểm tra nếu cần điều chỉnh stop loss rộng hơn
            if self.config["market_regime_adjustments"].get(market_regime, {}).get("sl_wider", False):
                market_multiplier *= 1.2
            
            sl_pct *= market_multiplier
            
            # Tính điểm stop loss
            sl_points = []
            
            if direction == "long":
                sl_price = entry_price * (1 - sl_pct)
                sl_points.append(round(sl_price, 2))
                
            else:  # direction == "short"
                sl_price = entry_price * (1 + sl_pct)
                sl_points.append(round(sl_price, 2))
            
            return sl_points
        
        except Exception as e:
            logger.error(f"Lỗi khi sinh điểm stop loss dựa trên phần trăm: {str(e)}")
            # Trả về mặc định nếu có lỗi
            if direction == "long":
                return [round(entry_price * 0.95, 2)]
            else:
                return [round(entry_price * 1.05, 2)]
    
    def _generate_atr_based_tp(self, symbol: str, direction: str, df: pd.DataFrame,
                             entry_price: float, market_regime: str) -> List[float]:
        """
        Sinh điểm take profit dựa trên ATR
        
        Args:
            symbol (str): Mã cặp tiền
            direction (str): Hướng giao dịch ('long' hoặc 'short')
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            entry_price (float): Giá vào lệnh
            market_regime (str): Chế độ thị trường
            
        Returns:
            List[float]: Danh sách các điểm take profit
        """
        try:
            # Tính ATR
            atr_period = self.config["atr_settings"]["period"]
            atr = self._calculate_atr(df, atr_period)
            
            if not atr:
                return []
            
            # Lấy hệ số điều chỉnh theo chế độ thị trường
            tp_multipliers = self.config["atr_settings"]["tp_multiplier"]
            tp_multiplier = tp_multipliers.get(market_regime, tp_multipliers.get("ranging", 1.5))
            
            # Kiểm tra nếu cần điều chỉnh take profit rộng hơn
            if self.config["market_regime_adjustments"].get(market_regime, {}).get("tp_wider", False):
                tp_multiplier *= 1.2
            
            # Tính điểm take profit
            tp_points = []
            
            if direction == "long":
                # Thêm nhiều mức take profit
                tp1 = entry_price + atr * tp_multiplier * 0.5
                tp2 = entry_price + atr * tp_multiplier
                tp3 = entry_price + atr * tp_multiplier * 1.5
                
                tp_points.append(round(tp1, 2))
                tp_points.append(round(tp2, 2))
                tp_points.append(round(tp3, 2))
                
            else:  # direction == "short"
                # Thêm nhiều mức take profit
                tp1 = entry_price - atr * tp_multiplier * 0.5
                tp2 = entry_price - atr * tp_multiplier
                tp3 = entry_price - atr * tp_multiplier * 1.5
                
                tp_points.append(round(tp1, 2))
                tp_points.append(round(tp2, 2))
                tp_points.append(round(tp3, 2))
            
            return tp_points
        
        except Exception as e:
            logger.error(f"Lỗi khi sinh điểm take profit dựa trên ATR: {str(e)}")
            return []
    
    def _generate_risk_reward_tp(self, symbol: str, direction: str, entry_price: float,
                               stop_loss: float, market_regime: str) -> List[float]:
        """
        Sinh điểm take profit dựa trên tỷ lệ risk/reward
        
        Args:
            symbol (str): Mã cặp tiền
            direction (str): Hướng giao dịch ('long' hoặc 'short')
            entry_price (float): Giá vào lệnh
            stop_loss (float): Giá stop loss
            market_regime (str): Chế độ thị trường
            
        Returns:
            List[float]: Danh sách các điểm take profit
        """
        try:
            # Lấy tỷ lệ risk/reward theo chế độ thị trường
            rr_ratios = self.config["fixed_risk_reward_ratio"]
            rr_ratio = rr_ratios.get(market_regime, rr_ratios.get("ranging", 1.5))
            
            # Kiểm tra nếu cần điều chỉnh take profit rộng hơn
            if self.config["market_regime_adjustments"].get(market_regime, {}).get("tp_wider", False):
                rr_ratio *= 1.2
            
            # Tính risk
            if direction == "long":
                risk = entry_price - stop_loss
                if risk <= 0:
                    return []
                
                # Tính các mức take profit
                tp1 = entry_price + risk * rr_ratio * 0.5
                tp2 = entry_price + risk * rr_ratio
                tp3 = entry_price + risk * rr_ratio * 1.5
                
            else:  # direction == "short"
                risk = stop_loss - entry_price
                if risk <= 0:
                    return []
                
                # Tính các mức take profit
                tp1 = entry_price - risk * rr_ratio * 0.5
                tp2 = entry_price - risk * rr_ratio
                tp3 = entry_price - risk * rr_ratio * 1.5
            
            tp_points = [round(tp1, 2), round(tp2, 2), round(tp3, 2)]
            return tp_points
        
        except Exception as e:
            logger.error(f"Lỗi khi sinh điểm take profit dựa trên tỷ lệ risk/reward: {str(e)}")
            return []
    
    def _generate_fibonacci_tp(self, symbol: str, direction: str, df: pd.DataFrame,
                             entry_price: float, market_regime: str) -> List[float]:
        """
        Sinh điểm take profit dựa trên Fibonacci extension
        
        Args:
            symbol (str): Mã cặp tiền
            direction (str): Hướng giao dịch ('long' hoặc 'short')
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            entry_price (float): Giá vào lệnh
            market_regime (str): Chế độ thị trường
            
        Returns:
            List[float]: Danh sách các điểm take profit
        """
        try:
            # Tìm swing high/low gần nhất
            lookback = 30
            if len(df) < lookback:
                return []
            
            recent_df = df.iloc[-lookback:]
            
            if direction == "long":
                # Tìm swing low và swing high gần nhất cho xu hướng tăng
                swing_low = recent_df['low'].min()
                swing_low_idx = recent_df['low'].idxmin()
                
                # Tìm swing high sau swing low
                if swing_low_idx == recent_df.index[-1]:
                    # Nếu swing low là điểm cuối cùng, lấy giá cao gần đây
                    swing_high = recent_df['high'].max()
                else:
                    swing_high = recent_df.loc[swing_low_idx:]['high'].max()
                
                if swing_high <= swing_low:
                    return []
                
                # Sử dụng entry_price làm điểm tham chiếu thứ ba
                diff = swing_high - swing_low
                
                # Tính các mức Fibonacci extension
                fib_127 = swing_high + 0.272 * diff
                fib_162 = swing_high + 0.618 * diff
                fib_200 = swing_high + 1.0 * diff
                
                # Tính điểm take profit
                tp_points = [round(fib_127, 2), round(fib_162, 2), round(fib_200, 2)]
                
            else:  # direction == "short"
                # Tìm swing high và swing low gần nhất cho xu hướng giảm
                swing_high = recent_df['high'].max()
                swing_high_idx = recent_df['high'].idxmax()
                
                # Tìm swing low sau swing high
                if swing_high_idx == recent_df.index[-1]:
                    # Nếu swing high là điểm cuối cùng, lấy giá thấp gần đây
                    swing_low = recent_df['low'].min()
                else:
                    swing_low = recent_df.loc[swing_high_idx:]['low'].min()
                
                if swing_low >= swing_high:
                    return []
                
                # Sử dụng entry_price làm điểm tham chiếu thứ ba
                diff = swing_high - swing_low
                
                # Tính các mức Fibonacci extension
                fib_127 = swing_low - 0.272 * diff
                fib_162 = swing_low - 0.618 * diff
                fib_200 = swing_low - 1.0 * diff
                
                # Tính điểm take profit
                tp_points = [round(fib_127, 2), round(fib_162, 2), round(fib_200, 2)]
            
            return tp_points
        
        except Exception as e:
            logger.error(f"Lỗi khi sinh điểm take profit dựa trên Fibonacci extension: {str(e)}")
            return []
    
    def _generate_percent_based_tp(self, symbol: str, direction: str, entry_price: float,
                                 market_regime: str) -> List[float]:
        """
        Sinh điểm take profit dựa trên phần trăm
        
        Args:
            symbol (str): Mã cặp tiền
            direction (str): Hướng giao dịch ('long' hoặc 'short')
            entry_price (float): Giá vào lệnh
            market_regime (str): Chế độ thị trường
            
        Returns:
            List[float]: Danh sách các điểm take profit
        """
        try:
            # Lấy cài đặt
            base_currency = self._extract_base_currency(symbol)
            tp_pct = self.config["percent_based"]["tp_percent"].get(
                base_currency, self.config["percent_based"]["tp_percent"].get("default", 10.0)) / 100
            
            # Điều chỉnh theo chế độ thị trường
            market_multiplier = {
                "trending": 1.5,
                "ranging": 1.0,
                "volatile": 2.0,
                "quiet": 0.7
            }.get(market_regime, 1.0)
            
            # Kiểm tra nếu cần điều chỉnh take profit rộng hơn
            if self.config["market_regime_adjustments"].get(market_regime, {}).get("tp_wider", False):
                market_multiplier *= 1.2
            
            tp_pct *= market_multiplier
            
            # Tính các mức take profit
            tp_points = []
            
            if direction == "long":
                tp1 = entry_price * (1 + tp_pct * 0.5)
                tp2 = entry_price * (1 + tp_pct)
                tp3 = entry_price * (1 + tp_pct * 1.5)
                
                tp_points.append(round(tp1, 2))
                tp_points.append(round(tp2, 2))
                tp_points.append(round(tp3, 2))
                
            else:  # direction == "short"
                tp1 = entry_price * (1 - tp_pct * 0.5)
                tp2 = entry_price * (1 - tp_pct)
                tp3 = entry_price * (1 - tp_pct * 1.5)
                
                tp_points.append(round(tp1, 2))
                tp_points.append(round(tp2, 2))
                tp_points.append(round(tp3, 2))
            
            return tp_points
        
        except Exception as e:
            logger.error(f"Lỗi khi sinh điểm take profit dựa trên phần trăm: {str(e)}")
            # Trả về mặc định nếu có lỗi
            if direction == "long":
                return [
                    round(entry_price * 1.05, 2),
                    round(entry_price * 1.10, 2),
                    round(entry_price * 1.15, 2)
                ]
            else:
                return [
                    round(entry_price * 0.95, 2),
                    round(entry_price * 0.90, 2),
                    round(entry_price * 0.85, 2)
                ]
    
    def get_entry_exit_points(self, symbol: str, direction: str, price: float,
                            df: pd.DataFrame = None, market_regime: str = "ranging") -> Dict:
        """
        Sinh tất cả các điểm vào/ra lệnh và lý do
        
        Args:
            symbol (str): Mã cặp tiền
            direction (str): Hướng giao dịch ('long' hoặc 'short')
            price (float): Giá hiện tại
            df (pd.DataFrame, optional): DataFrame chứa dữ liệu giá
            market_regime (str): Chế độ thị trường
            
        Returns:
            Dict: Từ điển chứa các điểm vào/ra và lý do
        """
        try:
            # Sinh điểm vào lệnh
            entry_points = self.generate_entry_points(symbol, direction, price, df, market_regime)
            
            # Sinh điểm thoát lệnh
            if entry_points and len(entry_points) > 0:
                exit_points = self.generate_exit_points(symbol, direction, entry_points[0], df, market_regime)
            else:
                exit_points = {
                    "stop_loss": [],
                    "take_profit": []
                }
            
            # Tạo lý do
            reasoning = self._generate_reasoning(symbol, direction, price, entry_points, exit_points, market_regime)
            
            # Tổng hợp kết quả
            result = {
                "entry_points": entry_points,
                "exit_points": {
                    "stop_loss": exit_points["stop_loss"],
                    "take_profit": exit_points["take_profit"]
                },
                "reasoning": reasoning
            }
            
            return result
        
        except Exception as e:
            logger.error(f"Lỗi khi sinh điểm vào/ra lệnh: {str(e)}")
            return {
                "entry_points": [],
                "exit_points": {
                    "stop_loss": [],
                    "take_profit": []
                },
                "reasoning": [f"Lỗi: {str(e)}"]
            }
    
    def _generate_reasoning(self, symbol: str, direction: str, current_price: float,
                          entry_points: List[float], exit_points: Dict, market_regime: str) -> List[str]:
        """
        Tạo lý do cho các điểm vào/ra lệnh
        
        Args:
            symbol (str): Mã cặp tiền
            direction (str): Hướng giao dịch ('long' hoặc 'short')
            current_price (float): Giá hiện tại
            entry_points (List[float]): Các điểm vào lệnh
            exit_points (Dict): Các điểm thoát lệnh
            market_regime (str): Chế độ thị trường
            
        Returns:
            List[str]: Danh sách các lý do
        """
        reasoning = []
        
        # Tạo lý do cho điểm vào lệnh
        if not entry_points or len(entry_points) == 0:
            reasoning.append(f"Không tìm thấy điểm vào {direction} phù hợp cho {symbol}")
        else:
            if direction == "long":
                if entry_points[0] < current_price:
                    reasoning.append(f"Đặt lệnh mua limit tại {entry_points[0]} (dưới giá hiện tại {current_price})")
                else:
                    reasoning.append(f"Đặt lệnh mua stop tại {entry_points[0]} (trên giá hiện tại {current_price})")
                
                if len(entry_points) > 1:
                    reasoning.append(f"Tăng vị thế nếu giá giảm đến {entry_points[1]}")
            else:
                if entry_points[0] > current_price:
                    reasoning.append(f"Đặt lệnh bán limit tại {entry_points[0]} (trên giá hiện tại {current_price})")
                else:
                    reasoning.append(f"Đặt lệnh bán stop tại {entry_points[0]} (dưới giá hiện tại {current_price})")
                
                if len(entry_points) > 1:
                    reasoning.append(f"Tăng vị thế nếu giá tăng đến {entry_points[1]}")
        
        # Thêm lý do về chế độ thị trường
        regime_desc = {
            "trending": "thị trường đang có xu hướng mạnh",
            "ranging": "thị trường đang sideway/giao động",
            "volatile": "thị trường đang có biến động cao",
            "quiet": "thị trường đang giao động nhẹ"
        }.get(market_regime, "")
        
        if regime_desc:
            reasoning.append(f"Thị trường hiện tại: {regime_desc}")
        
        # Tạo lý do cho stop loss
        if "stop_loss" in exit_points and exit_points["stop_loss"] and len(exit_points["stop_loss"]) > 0:
            if len(entry_points) > 0:
                entry = entry_points[0]
                sl = exit_points["stop_loss"][0]
                
                if direction == "long":
                    sl_pct = (entry - sl) / entry * 100
                    reasoning.append(f"Đặt stop loss tại {sl} (cắt lỗ {sl_pct:.2f}%)")
                else:
                    sl_pct = (sl - entry) / entry * 100
                    reasoning.append(f"Đặt stop loss tại {sl} (cắt lỗ {sl_pct:.2f}%)")
        
        # Tạo lý do cho take profit
        if "take_profit" in exit_points and exit_points["take_profit"] and len(exit_points["take_profit"]) > 0:
            if len(entry_points) > 0:
                entry = entry_points[0]
                tps = exit_points["take_profit"]
                
                if direction == "long":
                    tp_levels = []
                    for i, tp in enumerate(tps):
                        tp_pct = (tp - entry) / entry * 100
                        tp_levels.append(f"TP{i+1}: {tp} (+{tp_pct:.2f}%)")
                    
                    reasoning.append(f"Đặt take profit tại: {', '.join(tp_levels)}")
                else:
                    tp_levels = []
                    for i, tp in enumerate(tps):
                        tp_pct = (entry - tp) / entry * 100
                        tp_levels.append(f"TP{i+1}: {tp} (+{tp_pct:.2f}%)")
                    
                    reasoning.append(f"Đặt take profit tại: {', '.join(tp_levels)}")
        
        # Tạo lý do về tỷ lệ risk/reward
        if "stop_loss" in exit_points and exit_points["stop_loss"] and "take_profit" in exit_points and exit_points["take_profit"]:
            if len(entry_points) > 0 and len(exit_points["stop_loss"]) > 0 and len(exit_points["take_profit"]) > 0:
                entry = entry_points[0]
                sl = exit_points["stop_loss"][0]
                tp = exit_points["take_profit"][0]
                
                if direction == "long":
                    risk = entry - sl
                    reward = tp - entry
                else:
                    risk = sl - entry
                    reward = entry - tp
                
                if risk > 0:
                    rr_ratio = reward / risk
                    reasoning.append(f"Tỷ lệ risk/reward: 1:{rr_ratio:.2f}")
        
        return reasoning
    
    def _find_swing_points(self, df: pd.DataFrame, strength: int = 3) -> Dict[str, List[float]]:
        """
        Tìm các điểm swing high và swing low
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            strength (int): Độ mạnh của điểm swing
            
        Returns:
            Dict[str, List[float]]: Từ điển chứa các điểm swing
        """
        try:
            result = {
                "highs": [],
                "lows": []
            }
            
            if len(df) < 2 * strength + 1:
                return result
            
            # Tìm swing highs
            for i in range(strength, len(df) - strength):
                is_swing_high = True
                for j in range(1, strength + 1):
                    if df['high'].iloc[i] <= df['high'].iloc[i-j] or df['high'].iloc[i] <= df['high'].iloc[i+j]:
                        is_swing_high = False
                        break
                
                if is_swing_high:
                    result["highs"].append(df['high'].iloc[i])
            
            # Tìm swing lows
            for i in range(strength, len(df) - strength):
                is_swing_low = True
                for j in range(1, strength + 1):
                    if df['low'].iloc[i] >= df['low'].iloc[i-j] or df['low'].iloc[i] >= df['low'].iloc[i+j]:
                        is_swing_low = False
                        break
                
                if is_swing_low:
                    result["lows"].append(df['low'].iloc[i])
            
            return result
        
        except Exception as e:
            logger.error(f"Lỗi khi tìm điểm swing: {str(e)}")
            return {"highs": [], "lows": []}
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> Optional[float]:
        """
        Tính chỉ báo ATR
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            period (int): Số chu kỳ
            
        Returns:
            Optional[float]: Giá trị ATR hoặc None nếu lỗi
        """
        try:
            if len(df) < period:
                return None
            
            # Tính True Range
            df = df.copy()
            df['high_low'] = df['high'] - df['low']
            df['high_close'] = np.abs(df['high'] - df['close'].shift(1))
            df['low_close'] = np.abs(df['low'] - df['close'].shift(1))
            df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
            
            # Tính ATR
            df['atr'] = df['tr'].rolling(window=period).mean()
            
            # Trả về giá trị ATR mới nhất
            return df['atr'].iloc[-1]
        
        except Exception as e:
            logger.error(f"Lỗi khi tính ATR: {str(e)}")
            return None
    
    def _get_ohlcv_data(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> Optional[pd.DataFrame]:
        """
        Lấy dữ liệu OHLCV từ API
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            limit (int): Số lượng nến tối đa
            
        Returns:
            Optional[pd.DataFrame]: DataFrame chứa dữ liệu OHLCV hoặc None nếu lỗi
        """
        try:
            if not self.binance_api:
                return None
            
            # Lấy dữ liệu từ API
            klines = self.binance_api.get_klines(symbol=symbol, interval=timeframe, limit=limit)
            
            if not klines:
                return None
            
            # Chuyển đổi thành DataFrame
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                                             'close_time', 'quote_asset_volume', 'number_of_trades',
                                             'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
            
            # Chuyển đổi kiểu dữ liệu
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric)
            
            # Chuyển đổi timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
        
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu OHLCV: {str(e)}")
            return None
    
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

def main():
    """Hàm chính để test module"""
    
    try:
        # Khởi tạo
        from binance_api import BinanceAPI
        api = BinanceAPI()
        generator = EnhancedEntryExitGenerator(api)
        
        # Test các chức năng
        symbol = "BTCUSDT"
        direction = "long"
        current_price = 90000.0
        market_regime = "volatile"
        
        print(f"=== Điểm vào/ra lệnh cho {symbol} {direction} ===")
        print(f"Giá hiện tại: {current_price}")
        print(f"Chế độ thị trường: {market_regime}")
        print()
        
        # Lấy dữ liệu
        df = generator._get_ohlcv_data(symbol)
        
        # Sinh điểm vào
        entry_points = generator.generate_entry_points(symbol, direction, current_price, df, market_regime)
        print(f"Điểm vào: {entry_points}")
        
        # Sinh điểm thoát
        if entry_points and len(entry_points) > 0:
            exit_points = generator.generate_exit_points(symbol, direction, entry_points[0], df, market_regime)
            print(f"Stop loss: {exit_points['stop_loss']}")
            print(f"Take profit: {exit_points['take_profit']}")
            
            # Tính risk/reward
            if exit_points['stop_loss'] and exit_points['take_profit']:
                sl = exit_points['stop_loss'][0]
                tp = exit_points['take_profit'][0]
                if direction == "long":
                    risk = entry_points[0] - sl
                    reward = tp - entry_points[0]
                else:
                    risk = sl - entry_points[0]
                    reward = entry_points[0] - tp
                
                if risk > 0:
                    rr_ratio = reward / risk
                    print(f"Tỷ lệ risk/reward: 1:{rr_ratio:.2f}")
        
        # Lấy tất cả các điểm và lý do
        result = generator.get_entry_exit_points(symbol, direction, current_price, df, market_regime)
        
        print("\n=== Lý do ===")
        for reason in result["reasoning"]:
            print(f"- {reason}")
        
        # Test hướng khác
        direction = "short"
        print(f"\n\n=== Điểm vào/ra lệnh cho {symbol} {direction} ===")
        
        # Sinh điểm vào
        entry_points = generator.generate_entry_points(symbol, direction, current_price, df, market_regime)
        print(f"Điểm vào: {entry_points}")
        
        # Sinh điểm thoát
        if entry_points and len(entry_points) > 0:
            exit_points = generator.generate_exit_points(symbol, direction, entry_points[0], df, market_regime)
            print(f"Stop loss: {exit_points['stop_loss']}")
            print(f"Take profit: {exit_points['take_profit']}")
        
        # Lấy tất cả các điểm và lý do
        result = generator.get_entry_exit_points(symbol, direction, current_price, df, market_regime)
        
        print("\n=== Lý do ===")
        for reason in result["reasoning"]:
            print(f"- {reason}")
        
    except Exception as e:
        logger.error(f"Lỗi khi chạy test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()