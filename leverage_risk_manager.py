#!/usr/bin/env python3
"""
Module quản lý rủi ro đòn bẩy nâng cao

Module này cung cấp các công cụ để quản lý rủi ro đòn bẩy một cách tự động,
bao gồm trailing stop thông minh, điều chỉnh đòn bẩy động theo biến động thị trường,
và các cơ chế bảo vệ vốn tự động.
"""

import os
import json
import time
import logging
import datetime
from typing import Dict, List, Tuple, Optional, Union
from binance_api import BinanceAPI
import numpy as np
import pandas as pd
import math

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("leverage_risk_manager")

# Các đường dẫn mặc định
CONFIG_PATH = 'account_config.json'
RISK_CONFIG_PATH = 'risk_config.json'

class LeverageRiskManager:
    """Lớp quản lý rủi ro và đòn bẩy tự động"""
    
    def __init__(self, binance_api: BinanceAPI = None, config_path: str = CONFIG_PATH,
                 risk_config_path: str = RISK_CONFIG_PATH):
        """
        Khởi tạo quản lý rủi ro đòn bẩy
        
        Args:
            binance_api (BinanceAPI, optional): Instance của BinanceAPI
            config_path (str): Đường dẫn đến file cấu hình tài khoản
            risk_config_path (str): Đường dẫn đến file cấu hình rủi ro
        """
        self.config_path = config_path
        self.risk_config_path = risk_config_path
        
        if binance_api:
            self.api = binance_api
        else:
            self.api = BinanceAPI()
        
        self.load_risk_config()
        self.positions = {}  # Theo dõi vị thế hiện tại
        self.max_daily_loss_hit = False  # Cờ báo đã chạm ngưỡng lỗ tối đa
        self.market_volatility = {}  # Theo dõi biến động thị trường theo symbol
    
    def load_risk_config(self) -> Dict:
        """
        Tải cấu hình quản lý rủi ro
        
        Returns:
            Dict: Cấu hình quản lý rủi ro
        """
        try:
            if os.path.exists(self.risk_config_path):
                with open(self.risk_config_path, 'r') as f:
                    self.risk_config = json.load(f)
                    logger.info(f"Đã tải cấu hình rủi ro từ {self.risk_config_path}")
            else:
                self.risk_config = self._create_default_risk_config()
                self._save_risk_config()
                logger.info(f"Đã tạo cấu hình rủi ro mặc định và lưu vào {self.risk_config_path}")
            
            return self.risk_config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình rủi ro: {str(e)}")
            self.risk_config = self._create_default_risk_config()
            return self.risk_config
    
    def _create_default_risk_config(self) -> Dict:
        """
        Tạo cấu hình rủi ro mặc định
        
        Returns:
            Dict: Cấu hình rủi ro mặc định
        """
        return {
            "max_leverage": {
                "default": 10,
                "BTCUSDT": 10,
                "ETHUSDT": 10,
                "high_volatility": 5,
                "medium_volatility": 10,
                "low_volatility": 15
            },
            "stop_loss": {
                "default_percent": 5.0,  # Phần trăm vốn tối đa mất cho một giao dịch
                "trailing": {
                    "enabled": True,
                    "activation_percent": 2.0,  # Kích hoạt trailing khi lời 2%
                    "callback_percent": 1.0,  # Callback 1% từ đỉnh
                    "step_percent": 0.5  # Di chuyển mỗi bước 0.5%
                }
            },
            "take_profit": {
                "default_percent": 10.0,  # Mục tiêu lợi nhuận mặc định
                "dynamic": {
                    "enabled": True,
                    "ratio_to_atr": 3.0  # Tỷ lệ với ATR
                }
            },
            "position_sizing": {
                "max_capital_per_trade_percent": 5.0,  # Tối đa 5% vốn cho một giao dịch
                "increase_size_on_win_streaks": True,
                "reduce_size_on_loss_streaks": True
            },
            "risk_limits": {
                "max_daily_loss_percent": 5.0,  # Tối đa 5% vốn lỗ mỗi ngày
                "max_weekly_loss_percent": 10.0,  # Tối đa 10% vốn lỗ mỗi tuần
                "max_open_positions": 5,  # Tối đa 5 vị thế mở cùng lúc
                "max_same_direction_positions": 3  # Tối đa 3 vị thế cùng chiều
            },
            "volatility_adjustment": {
                "use_atr": True,
                "atr_period": 14,
                "high_volatility_threshold": 3.0,  # ATR > 3% của giá
                "medium_volatility_threshold": 1.5,  # ATR > 1.5% của giá
                "low_volatility_threshold": 0.5  # ATR < 0.5% của giá
            },
            "market_condition_adaptation": {
                "trending_market": {
                    "leverage_factor": 1.0,  # Không thay đổi đòn bẩy
                    "stop_loss_factor": 1.2,  # Nới rộng stop loss 20%
                    "take_profit_factor": 1.3  # Tăng take profit 30%
                },
                "ranging_market": {
                    "leverage_factor": 0.8,  # Giảm đòn bẩy 20%
                    "stop_loss_factor": 0.8,  # Thu hẹp stop loss 20%
                    "take_profit_factor": 0.8  # Giảm take profit 20%
                },
                "volatile_market": {
                    "leverage_factor": 0.5,  # Giảm đòn bẩy 50%
                    "stop_loss_factor": 0.7,  # Thu hẹp stop loss 30%
                    "take_profit_factor": 0.7  # Giảm take profit 30%
                }
            },
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def _save_risk_config(self) -> bool:
        """
        Lưu cấu hình quản lý rủi ro vào file
        
        Returns:
            bool: True nếu lưu thành công, False nếu thất bại
        """
        try:
            self.risk_config["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.risk_config_path, 'w') as f:
                json.dump(self.risk_config, f, indent=4)
            logger.info(f"Đã lưu cấu hình rủi ro vào {self.risk_config_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình rủi ro: {str(e)}")
            return False
    
    def update_volatility_metrics(self, symbol: str, price_data: pd.DataFrame) -> Dict:
        """
        Cập nhật các chỉ số biến động thị trường
        
        Args:
            symbol (str): Mã cặp giao dịch
            price_data (pd.DataFrame): DataFrame chứa dữ liệu giá
            
        Returns:
            Dict: Các chỉ số biến động thị trường
        """
        try:
            # Tính ATR (Average True Range)
            price_data['tr1'] = abs(price_data['high'] - price_data['low'])
            price_data['tr2'] = abs(price_data['high'] - price_data['close'].shift(1))
            price_data['tr3'] = abs(price_data['low'] - price_data['close'].shift(1))
            price_data['tr'] = price_data[['tr1', 'tr2', 'tr3']].max(axis=1)
            
            atr_period = self.risk_config["volatility_adjustment"]["atr_period"]
            price_data['atr'] = price_data['tr'].rolling(window=atr_period).mean()
            
            # Tính volatility (ATR % của giá)
            current_price = price_data['close'].iloc[-1]
            current_atr = price_data['atr'].iloc[-1]
            volatility_percent = (current_atr / current_price) * 100
            
            # Xác định mức biến động
            high_threshold = self.risk_config["volatility_adjustment"]["high_volatility_threshold"]
            medium_threshold = self.risk_config["volatility_adjustment"]["medium_volatility_threshold"]
            
            if volatility_percent > high_threshold:
                volatility_level = "high"
            elif volatility_percent > medium_threshold:
                volatility_level = "medium"
            else:
                volatility_level = "low"
            
            # Cập nhật thông tin biến động
            self.market_volatility[symbol] = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "current_price": current_price,
                "atr": current_atr,
                "volatility_percent": volatility_percent,
                "volatility_level": volatility_level
            }
            
            logger.info(f"Đã cập nhật thông tin biến động cho {symbol}: {volatility_level} ({volatility_percent:.2f}%)")
            return self.market_volatility[symbol]
        except Exception as e:
            logger.error(f"Lỗi khi tính toán biến động cho {symbol}: {str(e)}")
            return {"error": str(e)}
    
    def update_position_with_trailing_stop(self, symbol: str, current_price: float) -> Dict:
        """
        Cập nhật vị thế với trailing stop thông minh
        
        Args:
            symbol (str): Mã cặp giao dịch
            current_price (float): Giá hiện tại
            
        Returns:
            Dict: Thông tin cập nhật vị thế
        """
        if symbol not in self.positions:
            logger.warning(f"Không tìm thấy vị thế cho {symbol}")
            return {"status": "error", "message": f"Không tìm thấy vị thế cho {symbol}"}
        
        position = self.positions[symbol]
        side = position["side"]  # "LONG" hoặc "SHORT"
        entry_price = position["entry_price"]
        
        # Kiểm tra trailing stop đã được kích hoạt chưa
        if not position.get("trailing_activated", False):
            # Tính toán % lợi nhuận hiện tại
            if side == "LONG":
                profit_percent = (current_price - entry_price) / entry_price * 100 * position["leverage"]
            else:  # SHORT
                profit_percent = (entry_price - current_price) / entry_price * 100 * position["leverage"]
            
            # Kiểm tra xem đã đạt ngưỡng kích hoạt trailing stop chưa
            activation_percent = self.risk_config["stop_loss"]["trailing"]["activation_percent"]
            
            if profit_percent >= activation_percent:
                # Kích hoạt trailing stop
                position["trailing_activated"] = True
                
                if side == "LONG":
                    # Với LONG, trailing stop bắt đầu từ (giá hiện tại - callback%)
                    callback_value = current_price * (self.risk_config["stop_loss"]["trailing"]["callback_percent"] / 100)
                    position["trailing_stop"] = current_price - callback_value
                else:  # SHORT
                    # Với SHORT, trailing stop bắt đầu từ (giá hiện tại + callback%)
                    callback_value = current_price * (self.risk_config["stop_loss"]["trailing"]["callback_percent"] / 100)
                    position["trailing_stop"] = current_price + callback_value
                
                logger.info(f"Đã kích hoạt trailing stop cho {symbol} ở mức {position['trailing_stop']}")
        else:
            # Trailing stop đã được kích hoạt, cập nhật nếu cần
            if side == "LONG" and current_price > position.get("highest_price", entry_price):
                # Cập nhật giá cao nhất và trailing stop cho LONG
                position["highest_price"] = current_price
                callback_value = current_price * (self.risk_config["stop_loss"]["trailing"]["callback_percent"] / 100)
                new_stop = current_price - callback_value
                
                # Chỉ di chuyển trailing stop nếu mức mới cao hơn mức cũ
                if new_stop > position["trailing_stop"]:
                    position["trailing_stop"] = new_stop
                    logger.info(f"Đã cập nhật trailing stop cho {symbol} LONG lên {new_stop}")
            
            elif side == "SHORT" and current_price < position.get("lowest_price", entry_price):
                # Cập nhật giá thấp nhất và trailing stop cho SHORT
                position["lowest_price"] = current_price
                callback_value = current_price * (self.risk_config["stop_loss"]["trailing"]["callback_percent"] / 100)
                new_stop = current_price + callback_value
                
                # Chỉ di chuyển trailing stop nếu mức mới thấp hơn mức cũ
                if new_stop < position["trailing_stop"]:
                    position["trailing_stop"] = new_stop
                    logger.info(f"Đã cập nhật trailing stop cho {symbol} SHORT xuống {new_stop}")
        
        # Kiểm tra xem trailing stop có bị kích hoạt không
        position_closed = False
        close_reason = None
        
        if position.get("trailing_activated", False):
            if (side == "LONG" and current_price <= position["trailing_stop"]) or \
               (side == "SHORT" and current_price >= position["trailing_stop"]):
                position_closed = True
                close_reason = "trailing_stop"
                logger.info(f"Trailing stop được kích hoạt cho {symbol} ở mức {position['trailing_stop']}")
        
        # Cập nhật vị thế trong từ điển
        self.positions[symbol] = position
        
        result = {
            "symbol": symbol,
            "side": side,
            "current_price": current_price,
            "entry_price": entry_price,
            "trailing_activated": position.get("trailing_activated", False),
            "trailing_stop": position.get("trailing_stop", None),
            "position_closed": position_closed,
            "close_reason": close_reason
        }
        
        return result
    
    def calculate_adaptive_leverage(self, symbol: str, market_condition: str = None) -> int:
        """
        Tính toán đòn bẩy thích ứng dựa trên điều kiện thị trường
        
        Args:
            symbol (str): Mã cặp giao dịch
            market_condition (str, optional): Điều kiện thị trường ('trending', 'ranging', 'volatile')
            
        Returns:
            int: Đòn bẩy được đề xuất
        """
        try:
            # Lấy đòn bẩy mặc định
            default_leverage = self.risk_config["max_leverage"]["default"]
            
            # Lấy đòn bẩy theo symbol cụ thể nếu có
            symbol_leverage = self.risk_config["max_leverage"].get(symbol, default_leverage)
            
            # Lấy thông tin biến động thị trường
            volatility_info = self.market_volatility.get(symbol, {})
            volatility_level = volatility_info.get("volatility_level", "medium")
            
            # Đòn bẩy theo mức biến động
            volatility_leverage = self.risk_config["max_leverage"].get(f"{volatility_level}_volatility", symbol_leverage)
            
            # Điều chỉnh theo điều kiện thị trường nếu có
            if market_condition and market_condition in self.risk_config["market_condition_adaptation"]:
                leverage_factor = self.risk_config["market_condition_adaptation"][market_condition]["leverage_factor"]
                adjusted_leverage = int(volatility_leverage * leverage_factor)
            else:
                adjusted_leverage = volatility_leverage
            
            # Đảm bảo đòn bẩy trong phạm vi cho phép
            adjusted_leverage = max(1, min(adjusted_leverage, 20))
            
            logger.info(f"Đề xuất đòn bẩy cho {symbol}: {adjusted_leverage}x " + 
                       f"(Biến động: {volatility_level}, Thị trường: {market_condition})")
            
            return adjusted_leverage
        except Exception as e:
            logger.error(f"Lỗi khi tính toán đòn bẩy thích ứng cho {symbol}: {str(e)}")
            return 5  # Trả về đòn bẩy an toàn trong trường hợp lỗi
    
    def update_leverage(self, symbol: str, suggested_leverage: int = None) -> bool:
        """
        Cập nhật đòn bẩy cho một cặp giao dịch
        
        Args:
            symbol (str): Mã cặp giao dịch
            suggested_leverage (int, optional): Đòn bẩy được đề xuất
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu thất bại
        """
        try:
            # Nếu không cung cấp đòn bẩy đề xuất, tính toán dựa trên điều kiện thị trường
            if suggested_leverage is None:
                suggested_leverage = self.calculate_adaptive_leverage(symbol)
            
            # Thay đổi đòn bẩy trên Binance
            result = self.api.futures_change_leverage(symbol=symbol, leverage=suggested_leverage)
            
            # Kiểm tra kết quả
            if "leverage" in result:
                actual_leverage = result["leverage"]
                logger.info(f"Đã cập nhật đòn bẩy cho {symbol} thành {actual_leverage}x")
                
                # Cập nhật thông tin vị thế hiện tại nếu có
                if symbol in self.positions:
                    self.positions[symbol]["leverage"] = actual_leverage
                
                return True
            else:
                logger.error(f"Không thể cập nhật đòn bẩy cho {symbol}: {result}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật đòn bẩy cho {symbol}: {str(e)}")
            return False
    
    def calculate_position_size(self, symbol: str, entry_price: float, 
                             stop_loss_price: float, account_balance: float = None, 
                             risk_percent: float = None, leverage: int = None) -> Dict:
        """
        Tính toán kích thước vị thế dựa trên quản lý rủi ro
        
        Args:
            symbol (str): Mã cặp giao dịch
            entry_price (float): Giá vào lệnh
            stop_loss_price (float): Giá stop loss
            account_balance (float, optional): Số dư tài khoản
            risk_percent (float, optional): Phần trăm rủi ro
            leverage (int, optional): Đòn bẩy
            
        Returns:
            Dict: Thông tin về kích thước vị thế
        """
        try:
            # Lấy số dư tài khoản nếu không được cung cấp
            if account_balance is None:
                account_info = self.api.get_futures_account()
                account_balance = float(account_info["totalWalletBalance"])
            
            # Lấy phần trăm rủi ro nếu không được cung cấp
            if risk_percent is None:
                risk_percent = self.risk_config["position_sizing"]["max_capital_per_trade_percent"]
            
            # Lấy đòn bẩy nếu không được cung cấp
            if leverage is None:
                leverage = self.calculate_adaptive_leverage(symbol)
            
            # Tính khoảng cách phần trăm giữa giá vào và stop loss
            price_distance_percent = abs(entry_price - stop_loss_price) / entry_price * 100
            
            # Tính số tiền rủi ro
            risk_amount = account_balance * (risk_percent / 100)
            
            # Tính số tiền margin cần thiết
            margin_amount = risk_amount / (price_distance_percent / 100)
            
            # Tính số lượng hợp đồng/coin với đòn bẩy
            position_size = (margin_amount * leverage) / entry_price
            
            # Làm tròn số lượng theo yêu cầu của sàn
            # Thông thường BTC là 0.001, ETH là 0.01, các coin khác là 1
            if symbol == "BTCUSDT":
                position_size = round(position_size, 3)
            elif symbol == "ETHUSDT":
                position_size = round(position_size, 2)
            else:
                position_size = round(position_size, 0)
            
            result = {
                "symbol": symbol,
                "entry_price": entry_price,
                "stop_loss_price": stop_loss_price,
                "account_balance": account_balance,
                "risk_percent": risk_percent,
                "risk_amount": risk_amount,
                "leverage": leverage,
                "position_size": position_size,
                "margin_required": margin_amount
            }
            
            logger.info(f"Đề xuất kích thước vị thế cho {symbol}: {position_size} " + 
                       f"(Rủi ro: {risk_amount:.2f} USDT, Đòn bẩy: {leverage}x)")
            
            return result
        except Exception as e:
            logger.error(f"Lỗi khi tính toán kích thước vị thế cho {symbol}: {str(e)}")
            return {"error": str(e)}
    
    def calculate_dynamic_stop_loss(self, symbol: str, entry_price: float, side: str, 
                                  atr_value: float = None, market_condition: str = None) -> float:
        """
        Tính toán mức stop loss động dựa trên ATR và điều kiện thị trường
        
        Args:
            symbol (str): Mã cặp giao dịch
            entry_price (float): Giá vào lệnh
            side (str): Hướng vị thế ('LONG' hoặc 'SHORT')
            atr_value (float, optional): Giá trị ATR
            market_condition (str, optional): Điều kiện thị trường
            
        Returns:
            float: Giá stop loss
        """
        try:
            # Lấy phần trăm stop loss mặc định
            default_stop_percent = self.risk_config["stop_loss"]["default_percent"]
            
            # Nếu không có ATR, sử dụng stop loss dựa trên phần trăm mặc định
            if atr_value is None:
                volatility_info = self.market_volatility.get(symbol, {})
                atr_value = volatility_info.get("atr", entry_price * (default_stop_percent / 100))
            
            # Điều chỉnh theo điều kiện thị trường
            stop_factor = 1.0
            if market_condition and market_condition in self.risk_config["market_condition_adaptation"]:
                stop_factor = self.risk_config["market_condition_adaptation"][market_condition]["stop_loss_factor"]
            
            # Tính stop loss (2 lần ATR mặc định)
            atr_stop_distance = atr_value * 2 * stop_factor
            
            # Tính giá stop loss
            if side == "LONG":
                stop_loss_price = entry_price - atr_stop_distance
            else:  # SHORT
                stop_loss_price = entry_price + atr_stop_distance
            
            # Kiểm tra xem stop loss có quá gần giá vào không
            min_distance_percent = 0.5  # Tối thiểu 0.5% khoảng cách
            min_distance = entry_price * (min_distance_percent / 100)
            
            if side == "LONG" and (entry_price - stop_loss_price) < min_distance:
                stop_loss_price = entry_price - min_distance
            elif side == "SHORT" and (stop_loss_price - entry_price) < min_distance:
                stop_loss_price = entry_price + min_distance
            
            # Làm tròn stop loss
            stop_loss_price = round(stop_loss_price, 2)
            
            logger.info(f"Đề xuất stop loss cho {symbol} {side}: {stop_loss_price} " + 
                       f"(ATR: {atr_value:.2f}, Thị trường: {market_condition})")
            
            return stop_loss_price
        except Exception as e:
            logger.error(f"Lỗi khi tính toán stop loss động cho {symbol}: {str(e)}")
            # Trả về stop loss an toàn trong trường hợp lỗi
            if side == "LONG":
                return entry_price * 0.95
            else:  # SHORT
                return entry_price * 1.05
    
    def calculate_dynamic_take_profit(self, symbol: str, entry_price: float, side: str, 
                                    stop_loss_price: float, atr_value: float = None, 
                                    market_condition: str = None) -> float:
        """
        Tính toán mức take profit động dựa trên ATR và điều kiện thị trường
        
        Args:
            symbol (str): Mã cặp giao dịch
            entry_price (float): Giá vào lệnh
            side (str): Hướng vị thế ('LONG' hoặc 'SHORT')
            stop_loss_price (float): Giá stop loss
            atr_value (float, optional): Giá trị ATR
            market_condition (str, optional): Điều kiện thị trường
            
        Returns:
            float: Giá take profit
        """
        try:
            # Tính khoảng cách từ giá vào đến stop loss
            if side == "LONG":
                stop_distance = entry_price - stop_loss_price
            else:  # SHORT
                stop_distance = stop_loss_price - entry_price
            
            # Tính take profit dựa trên tỷ lệ risk:reward
            risk_reward_ratio = 2.0  # Mặc định 1:2
            
            # Điều chỉnh tỷ lệ theo điều kiện thị trường
            if market_condition and market_condition in self.risk_config["market_condition_adaptation"]:
                tp_factor = self.risk_config["market_condition_adaptation"][market_condition]["take_profit_factor"]
                risk_reward_ratio *= tp_factor
            
            # Tính khoảng cách take profit
            take_profit_distance = stop_distance * risk_reward_ratio
            
            # Tính giá take profit
            if side == "LONG":
                take_profit_price = entry_price + take_profit_distance
            else:  # SHORT
                take_profit_price = entry_price - take_profit_distance
            
            # Nếu có ATR, điều chỉnh take profit dựa trên ATR và tỷ lệ cấu hình
            if atr_value is not None and self.risk_config["take_profit"]["dynamic"]["enabled"]:
                atr_ratio = self.risk_config["take_profit"]["dynamic"]["ratio_to_atr"]
                atr_take_profit_distance = atr_value * atr_ratio
                
                if side == "LONG":
                    atr_take_profit = entry_price + atr_take_profit_distance
                    # Chọn giá trị thấp hơn giữa R:R và ATR
                    take_profit_price = min(take_profit_price, atr_take_profit)
                else:  # SHORT
                    atr_take_profit = entry_price - atr_take_profit_distance
                    # Chọn giá trị cao hơn giữa R:R và ATR
                    take_profit_price = max(take_profit_price, atr_take_profit)
            
            # Làm tròn take profit
            take_profit_price = round(take_profit_price, 2)
            
            logger.info(f"Đề xuất take profit cho {symbol} {side}: {take_profit_price} " + 
                       f"(R:R {risk_reward_ratio:.1f}:1, Thị trường: {market_condition})")
            
            return take_profit_price
        except Exception as e:
            logger.error(f"Lỗi khi tính toán take profit động cho {symbol}: {str(e)}")
            # Trả về take profit an toàn trong trường hợp lỗi
            if side == "LONG":
                return entry_price * 1.1
            else:  # SHORT
                return entry_price * 0.9
    
    def track_open_position(self, symbol: str, side: str, entry_price: float, 
                         quantity: float, leverage: int, stop_loss: float = None, 
                         take_profit: float = None, entry_time: str = None) -> Dict:
        """
        Theo dõi vị thế mở
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng vị thế ('LONG' hoặc 'SHORT') 
            entry_price (float): Giá vào lệnh
            quantity (float): Số lượng
            leverage (int): Đòn bẩy
            stop_loss (float, optional): Giá stop loss
            take_profit (float, optional): Giá take profit
            entry_time (str, optional): Thời gian vào lệnh
            
        Returns:
            Dict: Thông tin vị thế
        """
        if entry_time is None:
            entry_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Tính stop loss nếu không được cung cấp
        if stop_loss is None:
            volatility_info = self.market_volatility.get(symbol, {})
            atr_value = volatility_info.get("atr")
            stop_loss = self.calculate_dynamic_stop_loss(symbol, entry_price, side, atr_value)
        
        # Tính take profit nếu không được cung cấp
        if take_profit is None:
            volatility_info = self.market_volatility.get(symbol, {})
            atr_value = volatility_info.get("atr")
            take_profit = self.calculate_dynamic_take_profit(
                symbol, entry_price, side, stop_loss, atr_value
            )
        
        # Tạo thông tin vị thế
        position = {
            "symbol": symbol,
            "side": side,
            "entry_price": entry_price,
            "quantity": quantity,
            "leverage": leverage,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "entry_time": entry_time,
            "trailing_activated": False,
            "highest_price": entry_price if side == "LONG" else None,
            "lowest_price": entry_price if side == "SHORT" else None,
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Lưu vị thế
        self.positions[symbol] = position
        logger.info(f"Đang theo dõi vị thế {symbol} {side} tại {entry_price}")
        
        return position
    
    def check_daily_loss_limit(self) -> bool:
        """
        Kiểm tra giới hạn lỗ hàng ngày
        
        Returns:
            bool: True nếu đã đạt giới hạn, False nếu chưa
        """
        try:
            account_info = self.api.get_futures_account()
            
            # Lấy thông tin tài khoản
            total_balance = float(account_info["totalWalletBalance"])
            unrealized_pnl = float(account_info["totalUnrealizedProfit"])
            available_balance = float(account_info["availableBalance"])
            
            # TODO: Lấy balance đầu ngày từ database hoặc file
            # Bài tập cho bạn: Lưu balance đầu ngày vào file
            daily_starting_balance = 10000.0  # Giả sử balance đầu ngày là 10,000 USDT
            
            # Tính lỗ/lãi trong ngày
            daily_pnl = total_balance - daily_starting_balance + unrealized_pnl
            daily_pnl_percent = (daily_pnl / daily_starting_balance) * 100
            
            # Kiểm tra giới hạn lỗ
            max_daily_loss_percent = self.risk_config["risk_limits"]["max_daily_loss_percent"]
            
            if daily_pnl_percent < -max_daily_loss_percent:
                self.max_daily_loss_hit = True
                logger.warning(f"Đã đạt giới hạn lỗ hàng ngày: {daily_pnl_percent:.2f}% (Giới hạn: -{max_daily_loss_percent}%)")
                return True
            else:
                self.max_daily_loss_hit = False
                return False
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra giới hạn lỗ hàng ngày: {str(e)}")
            return False
    
    def __str__(self) -> str:
        """String representation of the risk manager"""
        return f"LeverageRiskManager with {len(self.positions)} tracked positions"

def main():
    """Hàm chính để demo LeverageRiskManager"""
    try:
        # Khởi tạo risk manager
        risk_manager = LeverageRiskManager()
        
        # Demo tính toán đòn bẩy thích ứng
        print("\n=== DEMO TÍNH TOÁN ĐÒN BẨY THÍCH ỨNG ===")
        for market_condition in ["trending", "ranging", "volatile"]:
            btc_leverage = risk_manager.calculate_adaptive_leverage("BTCUSDT", market_condition)
            eth_leverage = risk_manager.calculate_adaptive_leverage("ETHUSDT", market_condition)
            print(f"Thị trường {market_condition.upper()}:")
            print(f"  - BTC đề xuất đòn bẩy: {btc_leverage}x")
            print(f"  - ETH đề xuất đòn bẩy: {eth_leverage}x")
        
        # Demo tính toán kích thước vị thế
        print("\n=== DEMO TÍNH TOÁN KÍCH THƯỚC VỊ THẾ ===")
        position_size = risk_manager.calculate_position_size(
            symbol="BTCUSDT",
            entry_price=60000.0,
            stop_loss_price=58000.0,
            account_balance=10000.0,
            risk_percent=1.0,
            leverage=10
        )
        print(f"Size vị thế đề xuất: {position_size['position_size']} BTC")
        print(f"Số tiền rủi ro: {position_size['risk_amount']:.2f} USDT")
        
        # Demo tính toán stop loss và take profit động
        print("\n=== DEMO TÍNH TOÁN STOP LOSS & TAKE PROFIT ĐỘNG ===")
        entry_price = 60000.0
        side = "LONG"
        atr_value = 1800.0  # Giả định ATR là 1800
        
        for market_condition in ["trending", "ranging", "volatile"]:
            sl = risk_manager.calculate_dynamic_stop_loss(
                "BTCUSDT", entry_price, side, atr_value, market_condition
            )
            tp = risk_manager.calculate_dynamic_take_profit(
                "BTCUSDT", entry_price, side, sl, atr_value, market_condition
            )
            distance_sl = entry_price - sl
            distance_tp = tp - entry_price
            risk_reward = distance_tp / distance_sl if distance_sl > 0 else 0
            
            print(f"Thị trường {market_condition.upper()}:")
            print(f"  - Giá vào: {entry_price}")
            print(f"  - Stop Loss: {sl} ({(distance_sl/entry_price*100):.2f}%)")
            print(f"  - Take Profit: {tp} ({(distance_tp/entry_price*100):.2f}%)")
            print(f"  - Tỷ lệ R:R: 1:{risk_reward:.1f}")
        
        # Demo trailing stop
        print("\n=== DEMO TRAILING STOP ===")
        # Giả lập vị thế LONG BTC
        position = risk_manager.track_open_position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=60000.0,
            quantity=0.1,
            leverage=10,
            stop_loss=58000.0,
            take_profit=65000.0
        )
        print(f"Vị thế mới: {position}")
        
        # Giả lập giá tăng và kích hoạt trailing stop
        prices = [60500, 61000, 62000, 63000, 62000, 61000]
        for price in prices:
            result = risk_manager.update_position_with_trailing_stop("BTCUSDT", price)
            trailing_status = "Đã kích hoạt" if result["trailing_activated"] else "Chưa kích hoạt"
            trailing_price = result["trailing_stop"] if result["trailing_activated"] else "N/A"
            print(f"Giá BTC: {price}, Trailing Stop: {trailing_status} tại {trailing_price}")
            
            if result["position_closed"]:
                print(f"VỊ THẾ ĐÃ ĐÓNG! Lý do: {result['close_reason']}")
                break
    
    except Exception as e:
        print(f"Lỗi: {str(e)}")

if __name__ == "__main__":
    main()