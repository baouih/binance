#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module quản lý rủi ro động (Dynamic Risk Allocator)

Module này tự động điều chỉnh phần trăm rủi ro (risk_percentage) dựa trên biến động thị trường
và phân bổ vốn thông minh cho nhiều cặp tiền giao dịch đồng thời.
"""

import os
import json
import time
import math
import logging
import datetime
import random
from typing import Dict, List, Tuple, Any, Optional, Union
from api_data_validator import retry
from data_cache import DataCache

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('dynamic_risk_allocator')

class DynamicRiskAllocator:
    """Lớp quản lý rủi ro động theo biến động thị trường"""
    
    def __init__(self, data_cache: DataCache = None, config_path: str = 'configs/risk_config.json'):
        """
        Khởi tạo Dynamic Risk Allocator
        
        Args:
            data_cache (DataCache, optional): Cache dữ liệu
            config_path (str): Đường dẫn file cấu hình
        """
        self.data_cache = data_cache if data_cache else DataCache()
        self.config_path = config_path
        
        # Tải cấu hình
        self.config = self._load_config()
        
        # Thời gian cập nhật gần nhất
        self.last_update_time = None
        
        # Lịch sử phân bổ rủi ro
        self.risk_allocation_history = []
        
        # Theo dõi vị thế
        self.active_positions = {}
        self.position_metrics = {}
    
    def reload_config(self) -> Dict:
        """
        Tải lại cấu hình từ file
        
        Returns:
            Dict: Cấu hình đã tải lại
        """
        self.config = self._load_config()
        logger.info(f"Đã tải lại cấu hình từ {self.config_path}")
        return self.config
    
    def _load_config(self) -> Dict:
        """
        Tải cấu hình từ file
        
        Returns:
            Dict: Cấu hình
        """
        default_config = {
            "base_risk_percentage": 1.0,
            "max_risk_percentage": 3.0,
            "min_risk_percentage": 0.2,
            "volatility_adjustment": {
                "enabled": True,
                "high_volatility_threshold": 0.03,
                "low_volatility_threshold": 0.01,
                "high_volatility_multiplier": 0.5,
                "low_volatility_multiplier": 1.5
            },
            "drawdown_protection": {
                "enabled": True,
                "drawdown_levels": [5, 10, 15, 20],
                "risk_reduction_percents": [20, 40, 60, 80]
            },
            "position_limits": {
                "max_positions": 5,
                "max_positions_per_direction": 3,
                "position_correlation_threshold": 0.7
            },
            "capital_allocation": {
                "method": "equal",  # options: equal, volatility_based, sharp_based, volume_based
                "multi_timeframe_weight": {
                    "1m": 0.1,
                    "5m": 0.15,
                    "15m": 0.2,
                    "1h": 0.3,
                    "4h": 0.15,
                    "1d": 0.1
                }
            },
            "liquidity_requirements": {
                "min_24h_volume": 10000000,  # 10M USD
                "min_orderbook_depth": 1000000,  # 1M USD
                "max_slippage_percent": 0.5
            }
        }
        
        # Kiểm tra file cấu hình tồn tại
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
                return config
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình từ {self.config_path}: {str(e)}")
        
        # Tạo file cấu hình mặc định nếu không tồn tại
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            logger.info(f"Đã tạo cấu hình mặc định tại {self.config_path}")
        except Exception as e:
            logger.error(f"Lỗi khi tạo cấu hình mặc định: {str(e)}")
        
        return default_config
    
    def save_config(self) -> bool:
        """
        Lưu cấu hình vào file
        
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Đã lưu cấu hình vào {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {str(e)}")
            return False
    
    def calculate_risk_percentage(self, symbol: str, timeframe: str, market_regime: str = None,
                               account_balance: float = None, current_drawdown: float = None) -> float:
        """
        Tính toán risk_percentage động dựa trên biến động thị trường
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            market_regime (str, optional): Chế độ thị trường
            account_balance (float, optional): Số dư tài khoản
            current_drawdown (float, optional): % drawdown hiện tại
            
        Returns:
            float: Phần trăm rủi ro
        """
        # Lấy % rủi ro cơ sở từ cấu hình
        base_risk = self.config.get('base_risk_percentage', 1.0)
        max_risk = self.config.get('max_risk_percentage', 3.0)
        min_risk = self.config.get('min_risk_percentage', 0.2)
        
        # Lấy biến động hiện tại
        volatility = self._get_current_volatility(symbol, timeframe)
        
        # Điều chỉnh theo biến động
        risk = self._adjust_risk_by_volatility(base_risk, volatility)
        
        # Điều chỉnh theo chế độ thị trường
        if market_regime:
            risk = self._adjust_risk_by_market_regime(risk, market_regime)
        
        # Điều chỉnh theo drawdown nếu được cung cấp
        if current_drawdown is not None:
            risk = self._adjust_risk_by_drawdown(risk, current_drawdown)
        
        # Kiểm tra giới hạn
        risk = max(min_risk, min(risk, max_risk))
        
        # Lưu vào lịch sử
        self.risk_allocation_history.append({
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'symbol': symbol,
            'timeframe': timeframe,
            'market_regime': market_regime,
            'volatility': volatility,
            'base_risk': base_risk,
            'adjusted_risk': risk,
            'current_drawdown': current_drawdown
        })
        
        # Giới hạn lịch sử
        if len(self.risk_allocation_history) > 100:
            self.risk_allocation_history = self.risk_allocation_history[-100:]
        
        # Cập nhật thời gian
        self.last_update_time = time.time()
        
        return risk
    
    def _get_current_volatility(self, symbol: str, timeframe: str) -> float:
        """
        Lấy biến động hiện tại của thị trường
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            
        Returns:
            float: Biến động hiện tại
        """
        # Kiểm tra cache
        cache_key = f"{symbol}_{timeframe}_volatility"
        cached_volatility = self.data_cache.get('market_analysis', cache_key)
        
        if cached_volatility is not None:
            cached_time = self.data_cache.get_timestamp('market_analysis', cache_key)
            if cached_time:
                # Kiểm tra thời gian cache, nếu mới hơn 15 phút thì sử dụng
                cache_age = time.time() - cached_time
                if cache_age < 900:  # 15 minutes
                    return cached_volatility
        
        # Tính toán biến động
        volatility = self._calculate_volatility(symbol, timeframe)
        
        # Lưu vào cache
        self.data_cache.set('market_analysis', cache_key, volatility)
        
        return volatility
    
    def _calculate_volatility(self, symbol: str, timeframe: str, period: int = 14) -> float:
        """
        Tính toán biến động thị trường (ATR/Price)
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            period (int): Số chu kỳ
            
        Returns:
            float: Biến động thị trường
        """
        try:
            # Lấy dữ liệu giá
            price_data = self.data_cache.get('market_data', f"{symbol}_{timeframe}_data")
            
            if price_data is None or not isinstance(price_data, list) or len(price_data) < period:
                # Nếu không có dữ liệu, trả về giá trị mặc định
                return 0.02  # 2% biến động mặc định
            
            # Lấy giá
            close_prices = [float(candle[4]) for candle in price_data[-period-1:]]
            high_prices = [float(candle[2]) for candle in price_data[-period:]]
            low_prices = [float(candle[3]) for candle in price_data[-period:]]
            
            # Tính true range
            tr_values = []
            for i in range(1, len(close_prices)):
                tr1 = high_prices[i-1] - low_prices[i-1]
                tr2 = abs(high_prices[i-1] - close_prices[i-2]) if i > 1 else 0
                tr3 = abs(low_prices[i-1] - close_prices[i-2]) if i > 1 else 0
                tr_values.append(max(tr1, tr2, tr3))
            
            # Tính ATR
            atr = sum(tr_values) / len(tr_values) if tr_values else 0
            
            # Tính biến động (ATR/Giá đóng cửa)
            current_price = close_prices[-1]
            volatility = atr / current_price if current_price > 0 else 0
            
            return volatility
        except Exception as e:
            logger.error(f"Lỗi khi tính biến động cho {symbol} {timeframe}: {str(e)}")
            return 0.02  # Giá trị mặc định
    
    def _adjust_risk_by_volatility(self, base_risk: float, volatility: float) -> float:
        """
        Điều chỉnh risk_percentage theo biến động
        
        Args:
            base_risk (float): Phần trăm rủi ro cơ sở
            volatility (float): Biến động thị trường
            
        Returns:
            float: Phần trăm rủi ro đã điều chỉnh
        """
        # Kiểm tra cấu hình
        volatility_config = self.config.get('volatility_adjustment', {})
        if not volatility_config.get('enabled', True):
            return base_risk
        
        # Lấy ngưỡng biến động
        high_vol_threshold = volatility_config.get('high_volatility_threshold', 0.03)
        low_vol_threshold = volatility_config.get('low_volatility_threshold', 0.01)
        
        # Lấy hệ số điều chỉnh
        high_vol_multiplier = volatility_config.get('high_volatility_multiplier', 0.5)
        low_vol_multiplier = volatility_config.get('low_volatility_multiplier', 1.5)
        
        # Điều chỉnh theo biến động
        if volatility >= high_vol_threshold:
            # Biến động cao - giảm rủi ro
            adjustment = high_vol_multiplier
        elif volatility <= low_vol_threshold:
            # Biến động thấp - tăng rủi ro
            adjustment = low_vol_multiplier
        else:
            # Biến động trung bình - nội suy tuyến tính
            vol_range = high_vol_threshold - low_vol_threshold
            vol_position = (volatility - low_vol_threshold) / vol_range
            adjustment = low_vol_multiplier - vol_position * (low_vol_multiplier - high_vol_multiplier)
        
        # Áp dụng điều chỉnh
        adjusted_risk = base_risk * adjustment
        
        return adjusted_risk
    
    def _adjust_risk_by_market_regime(self, base_risk: float, market_regime: str) -> float:
        """
        Điều chỉnh risk_percentage theo chế độ thị trường
        
        Args:
            base_risk (float): Phần trăm rủi ro cơ sở
            market_regime (str): Chế độ thị trường
            
        Returns:
            float: Phần trăm rủi ro đã điều chỉnh
        """
        # Hệ số điều chỉnh theo chế độ thị trường
        regime_multipliers = {
            'trending': 1.2,  # Tăng rủi ro khi có xu hướng
            'ranging': 0.8,   # Giảm rủi ro khi dao động
            'volatile': 0.6,  # Giảm rủi ro khi biến động mạnh
            'quiet': 1.0      # Giữ nguyên khi ít biến động
        }
        
        # Lấy hệ số điều chỉnh
        multiplier = regime_multipliers.get(market_regime, 1.0)
        
        # Áp dụng điều chỉnh
        adjusted_risk = base_risk * multiplier
        
        return adjusted_risk
    
    def _adjust_risk_by_drawdown(self, base_risk: float, drawdown_percent: float) -> float:
        """
        Điều chỉnh risk_percentage theo drawdown hiện tại
        
        Args:
            base_risk (float): Phần trăm rủi ro cơ sở
            drawdown_percent (float): Phần trăm drawdown hiện tại
            
        Returns:
            float: Phần trăm rủi ro đã điều chỉnh
        """
        # Kiểm tra cấu hình
        drawdown_config = self.config.get('drawdown_protection', {})
        if not drawdown_config.get('enabled', True):
            return base_risk
        
        # Lấy các mức drawdown và % giảm rủi ro tương ứng
        drawdown_levels = drawdown_config.get('drawdown_levels', [5, 10, 15, 20])
        risk_reduction = drawdown_config.get('risk_reduction_percents', [20, 40, 60, 80])
        
        # Tìm mức drawdown thích hợp
        reduction_percent = 0
        for i, level in enumerate(drawdown_levels):
            if drawdown_percent >= level:
                reduction_percent = risk_reduction[i]
        
        # Áp dụng giảm rủi ro
        adjusted_risk = base_risk * (1 - reduction_percent / 100)
        
        return adjusted_risk
    
    def _get_min_notional(self, symbol: str) -> float:
        """
        Lấy giá trị giao dịch tối thiểu cho một cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            float: Giá trị giao dịch tối thiểu
        """
        # Giá trị mặc định dựa trên Binance Futures
        default_min_notional = {
            'BTCUSDT': 100.0,
            'ETHUSDT': 20.0,
            'BNBUSDT': 10.0,
            'SOLUSDT': 5.0,
            'ADAUSDT': 5.0,
            'XRPUSDT': 5.0,
            'DOGEUSDT': 5.0,
            'MATICUSDT': 5.0,
            'LTCUSDT': 10.0,
            'DOTUSDT': 5.0,
            'LINKUSDT': 5.0,
            'AVAXUSDT': 5.0,
            'ATOMUSDT': 5.0,
            'UNIUSDT': 5.0
        }
        
        return default_min_notional.get(symbol, 5.0)
    
    def _get_step_size(self, symbol: str) -> float:
        """
        Lấy step size cho một cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            float: Step size
        """
        # Step size mặc định dựa trên Binance Futures
        default_step_size = {
            'BTCUSDT': 0.001,
            'ETHUSDT': 0.001,
            'BNBUSDT': 0.01,
            'SOLUSDT': 0.01,
            'ADAUSDT': 1.0,
            'XRPUSDT': 1.0,
            'DOGEUSDT': 1.0,
            'MATICUSDT': 1.0,
            'LTCUSDT': 0.01,
            'DOTUSDT': 0.1,
            'LINKUSDT': 0.1,
            'AVAXUSDT': 0.1,
            'ATOMUSDT': 0.01,
            'UNIUSDT': 0.1
        }
        
        return default_step_size.get(symbol, 0.001)
    
    def is_small_account(self, account_balance: float) -> bool:
        """
        Kiểm tra xem có phải là tài khoản nhỏ không
        
        Args:
            account_balance (float): Số dư tài khoản
            
        Returns:
            bool: True nếu là tài khoản nhỏ, False nếu không
        """
        small_account_settings = self.config.get('small_account_settings', {})
        if not small_account_settings.get('enabled', False):
            return False
            
        threshold = small_account_settings.get('account_size_threshold', 200.0)
        return account_balance < threshold
    
    def calculate_position_size(self, symbol: str, entry_price: float, stop_loss: float, 
                             account_balance: float, risk_percentage: float, 
                             max_position_percent: float = 20.0) -> Dict:
        """
        Tính toán kích thước vị thế
        
        Args:
            symbol (str): Mã cặp tiền
            entry_price (float): Giá vào lệnh
            stop_loss (float): Giá stop loss
            account_balance (float): Số dư tài khoản
            risk_percentage (float): Phần trăm rủi ro
            max_position_percent (float): Phần trăm tối đa của tài khoản cho một vị thế
            
        Returns:
            Dict: Thông tin vị thế
        """
        # Kiểm tra xem có phải tài khoản nhỏ không
        if self.is_small_account(account_balance):
            return self.calculate_position_size_for_small_account(
                symbol, entry_price, stop_loss, account_balance, risk_percentage)
        
        # Xử lý cho tài khoản thông thường
        # Tính risk amount (số tiền rủi ro)
        risk_amount = account_balance * risk_percentage / 100
        
        # Tính khoảng cách SL
        sl_distance_percent = abs(entry_price - stop_loss) / entry_price * 100
        
        # Tính kích thước vị thế (quantity) dựa trên khoảng cách SL
        if sl_distance_percent > 0:
            position_size_usd = risk_amount / (sl_distance_percent / 100)
        else:
            # Nếu không có SL hoặc SL trùng giá vào
            position_size_usd = 0
        
        # Kiểm tra giới hạn vị thế
        max_position_size = account_balance * max_position_percent / 100
        position_size_usd = min(position_size_usd, max_position_size)
        
        # Tính số lượng (quantity)
        quantity = position_size_usd / entry_price if entry_price > 0 else 0
        
        # Làm tròn số lượng theo step size
        step_size = self._get_step_size(symbol)
        precision = len(str(step_size).split('.')[-1])
        quantity = round(quantity, precision)
        
        return {
            'symbol': symbol,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'risk_percentage': risk_percentage,
            'risk_amount': risk_amount,
            'position_size_usd': position_size_usd,
            'quantity': quantity,
            'account_balance': account_balance,
            'max_position_percent': max_position_percent
        }
        
    def calculate_position_size_for_small_account(self, symbol: str, entry_price: float, stop_loss: float, 
                             account_balance: float, risk_percentage: float) -> Dict:
        """
        Tính toán kích thước vị thế đặc biệt cho tài khoản nhỏ
        
        Args:
            symbol (str): Mã cặp tiền
            entry_price (float): Giá vào lệnh
            stop_loss (float): Giá stop loss
            account_balance (float): Số dư tài khoản
            risk_percentage (float): Phần trăm rủi ro
            
        Returns:
            Dict: Thông tin vị thế
        """
        small_account_settings = self.config.get('small_account_settings', {})
        
        # Lấy giá trị giao dịch tối thiểu
        min_notional = self._get_min_notional(symbol)
        
        # Điều chỉnh đòn bẩy dựa trên cặp tiền
        leverage_adjustment = small_account_settings.get('altcoin_leverage_adjustment', 10)
        if symbol == "BTCUSDT":
            leverage_adjustment = small_account_settings.get('btc_leverage_adjustment', 20)
        elif symbol == "ETHUSDT":
            leverage_adjustment = small_account_settings.get('eth_leverage_adjustment', 15)
        
        # Điều chỉnh risk_percentage
        adjusted_risk = risk_percentage * small_account_settings.get('risk_per_trade_adjustment', 0.7)
        
        # Tính toán risk amount
        risk_amount = account_balance * adjusted_risk / 100
        
        # Tính khoảng cách SL
        sl_distance_percent = abs(entry_price - stop_loss) / entry_price * 100
        sl_distance_percent = max(sl_distance_percent, 1.0)  # Đảm bảo ít nhất 1%
        
        # Tính giá trị vị thế ban đầu dựa trên risk
        if sl_distance_percent > 0:
            position_size_usd = risk_amount / (sl_distance_percent / 100) * leverage_adjustment / 10
        else:
            position_size_usd = risk_amount * leverage_adjustment
            
        # Đảm bảo đạt giá trị tối thiểu
        min_position_value = small_account_settings.get('min_position_value', 5.0)
        position_size_usd = max(position_size_usd, min(min_position_value, min_notional))
        
        # Đảm bảo không vượt quá % tài khoản tối đa
        max_account_percent = small_account_settings.get('max_account_percent', 50.0)
        max_position_size = account_balance * max_account_percent / 100
        position_size_usd = min(position_size_usd, max_position_size)
        
        # Tính số lượng
        quantity = position_size_usd / entry_price if entry_price > 0 else 0
        
        # Làm tròn theo step size
        step_size = self._get_step_size(symbol)
        precision = len(str(step_size).split('.')[-1])
        quantity = round(quantity, precision)
        
        return {
            'symbol': symbol,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'risk_percentage': adjusted_risk,
            'risk_amount': risk_amount,
            'position_size_usd': position_size_usd,
            'quantity': quantity,
            'account_balance': account_balance,
            'leverage': leverage_adjustment,
            'is_small_account': True,
            'min_notional': min_notional
        }
    
    def allocate_capital(self, symbols: List[str], account_balance: float, market_data: Dict = None,
                      strategy_signals: Dict = None) -> Dict[str, float]:
        """
        Phân bổ vốn cho nhiều cặp tiền
        
        Args:
            symbols (List[str]): Danh sách cặp tiền
            account_balance (float): Số dư tài khoản
            market_data (Dict, optional): Dữ liệu thị trường
            strategy_signals (Dict, optional): Tín hiệu từ chiến lược
            
        Returns:
            Dict[str, float]: Ánh xạ cặp tiền -> % vốn
        """
        # Lấy phương pháp phân bổ vốn từ cấu hình
        capital_config = self.config.get('capital_allocation', {})
        method = capital_config.get('method', 'equal')
        
        # Nếu không có cặp tiền nào, trả về dict rỗng
        if not symbols:
            return {}
        
        # Phân bổ vốn theo phương pháp được chọn
        if method == 'equal':
            allocation = self._allocate_capital_equal(symbols)
        elif method == 'volatility_based':
            allocation = self._allocate_capital_volatility(symbols, market_data)
        elif method == 'signal_strength':
            allocation = self._allocate_capital_signal_strength(symbols, strategy_signals)
        elif method == 'volume_based':
            allocation = self._allocate_capital_volume(symbols, market_data)
        else:
            # Phương pháp không hỗ trợ, sử dụng mặc định
            allocation = self._allocate_capital_equal(symbols)
        
        return allocation
    
    def _allocate_capital_equal(self, symbols: List[str]) -> Dict[str, float]:
        """
        Phân bổ vốn đều cho các cặp tiền
        
        Args:
            symbols (List[str]): Danh sách cặp tiền
            
        Returns:
            Dict[str, float]: Ánh xạ cặp tiền -> % vốn
        """
        # Tính % vốn cho mỗi cặp tiền
        if not symbols:
            return {}
        
        percent_per_symbol = 100.0 / len(symbols)
        
        # Phân bổ đều
        allocation = {symbol: percent_per_symbol for symbol in symbols}
        
        return allocation
    
    def _allocate_capital_volatility(self, symbols: List[str], market_data: Dict) -> Dict[str, float]:
        """
        Phân bổ vốn dựa trên biến động (volatility)
        
        Args:
            symbols (List[str]): Danh sách cặp tiền
            market_data (Dict): Dữ liệu thị trường
            
        Returns:
            Dict[str, float]: Ánh xạ cặp tiền -> % vốn
        """
        if not symbols or not market_data:
            return self._allocate_capital_equal(symbols)
        
        # Tính biến động cho mỗi cặp tiền
        volatilities = {}
        for symbol in symbols:
            volatility = market_data.get(symbol, {}).get('volatility', 0.02)
            volatilities[symbol] = volatility
        
        # Phân bổ ngược với biến động (biến động càng thấp, phân bổ càng cao)
        inverse_volatilities = {symbol: 1/vol if vol > 0 else 0 for symbol, vol in volatilities.items()}
        
        # Tính tổng
        total_inverse = sum(inverse_volatilities.values())
        
        # Phân bổ % vốn
        if total_inverse > 0:
            allocation = {symbol: (inv_vol / total_inverse) * 100 for symbol, inv_vol in inverse_volatilities.items()}
        else:
            allocation = self._allocate_capital_equal(symbols)
        
        return allocation
    
    def _allocate_capital_signal_strength(self, symbols: List[str], strategy_signals: Dict) -> Dict[str, float]:
        """
        Phân bổ vốn dựa trên độ mạnh của tín hiệu
        
        Args:
            symbols (List[str]): Danh sách cặp tiền
            strategy_signals (Dict): Tín hiệu từ chiến lược
            
        Returns:
            Dict[str, float]: Ánh xạ cặp tiền -> % vốn
        """
        if not symbols or not strategy_signals:
            return self._allocate_capital_equal(symbols)
        
        # Lấy độ mạnh tín hiệu cho mỗi cặp tiền
        signal_strengths = {}
        for symbol in symbols:
            signal = strategy_signals.get(symbol, {}).get('composite_signal', {})
            strength = signal.get('strength', 0.0)
            signal_strengths[symbol] = strength
        
        # Tính tổng độ mạnh
        total_strength = sum(signal_strengths.values())
        
        # Phân bổ % vốn
        if total_strength > 0:
            allocation = {symbol: (strength / total_strength) * 100 for symbol, strength in signal_strengths.items()}
        else:
            allocation = self._allocate_capital_equal(symbols)
        
        return allocation
    
    def _allocate_capital_volume(self, symbols: List[str], market_data: Dict) -> Dict[str, float]:
        """
        Phân bổ vốn dựa trên khối lượng giao dịch
        
        Args:
            symbols (List[str]): Danh sách cặp tiền
            market_data (Dict): Dữ liệu thị trường
            
        Returns:
            Dict[str, float]: Ánh xạ cặp tiền -> % vốn
        """
        if not symbols or not market_data:
            return self._allocate_capital_equal(symbols)
        
        # Lấy khối lượng giao dịch cho mỗi cặp tiền
        volumes = {}
        for symbol in symbols:
            volume = market_data.get(symbol, {}).get('volume', 0.0)
            volumes[symbol] = volume
        
        # Tính tổng khối lượng
        total_volume = sum(volumes.values())
        
        # Phân bổ % vốn
        if total_volume > 0:
            allocation = {symbol: (volume / total_volume) * 100 for symbol, volume in volumes.items()}
        else:
            allocation = self._allocate_capital_equal(symbols)
        
        return allocation
    
    def check_liquidity(self, symbol: str, position_size_usd: float, orderbook: Dict) -> Dict:
        """
        Kiểm tra thanh khoản trước khi đặt lệnh
        
        Args:
            symbol (str): Mã cặp tiền
            position_size_usd (float): Kích thước vị thế (USD)
            orderbook (Dict): Dữ liệu order book
            
        Returns:
            Dict: Kết quả kiểm tra
        """
        result = {
            'is_liquid': True,
            'slippage': 0.0,
            'warning': None
        }
        
        # Lấy cấu hình thanh khoản
        liquidity_config = self.config.get('liquidity_requirements', {})
        min_24h_volume = liquidity_config.get('min_24h_volume', 10000000)
        min_orderbook_depth = liquidity_config.get('min_orderbook_depth', 1000000)
        max_slippage_percent = liquidity_config.get('max_slippage_percent', 0.5)
        
        # Kiểm tra khối lượng 24h
        market_data = self.data_cache.get('market_data', f"{symbol}_ticker")
        if market_data:
            volume_24h = float(market_data.get('quoteVolume', 0))
            if volume_24h < min_24h_volume:
                result['is_liquid'] = False
                result['warning'] = f"Khối lượng 24h thấp: ${volume_24h:,.0f} < ${min_24h_volume:,.0f}"
                return result
        
        # Kiểm tra order book
        if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
            result['is_liquid'] = False
            result['warning'] = "Không có dữ liệu order book"
            return result
        
        # Tính độ sâu của order book
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        
        bid_depth = sum(float(bid[0]) * float(bid[1]) for bid in bids)
        ask_depth = sum(float(ask[0]) * float(ask[1]) for ask in asks)
        
        # Kiểm tra độ sâu
        if bid_depth < min_orderbook_depth or ask_depth < min_orderbook_depth:
            result['is_liquid'] = False
            result['warning'] = f"Độ sâu order book thấp: Bid=${bid_depth:,.0f}, Ask=${ask_depth:,.0f} < ${min_orderbook_depth:,.0f}"
            return result
        
        # Tính slippage
        if position_size_usd > 0:
            # Giả sử vị thế là BUY
            remaining_size = position_size_usd
            executed_value = 0
            weighted_price = 0
            
            for ask in asks:
                price = float(ask[0])
                size = float(ask[1]) * price
                
                if remaining_size <= 0:
                    break
                
                executed = min(size, remaining_size)
                executed_value += executed
                weighted_price += price * executed
                remaining_size -= executed
            
            if executed_value > 0:
                avg_price = weighted_price / executed_value
                market_price = float(asks[0][0])
                slippage = (avg_price - market_price) / market_price * 100
                
                result['slippage'] = slippage
                
                if slippage > max_slippage_percent:
                    result['is_liquid'] = False
                    result['warning'] = f"Slippage cao: {slippage:.2f}% > {max_slippage_percent:.2f}%"
                    return result
        
        return result
    
    def adjust_position_size_by_liquidity(self, position_info: Dict, orderbook: Dict) -> Dict:
        """
        Điều chỉnh kích thước vị thế theo thanh khoản
        
        Args:
            position_info (Dict): Thông tin vị thế
            orderbook (Dict): Dữ liệu order book
            
        Returns:
            Dict: Thông tin vị thế đã điều chỉnh
        """
        # Kiểm tra thanh khoản
        symbol = position_info.get('symbol')
        position_size_usd = position_info.get('position_size_usd', 0)
        
        liquidity_check = self.check_liquidity(symbol, position_size_usd, orderbook)
        
        # Nếu thanh khoản không đủ, giảm kích thước vị thế
        if not liquidity_check['is_liquid']:
            # Lấy cấu hình thanh khoản
            liquidity_config = self.config.get('liquidity_requirements', {})
            max_slippage_percent = liquidity_config.get('max_slippage_percent', 0.5)
            
            # Tính toán % giảm kích thước
            slippage = liquidity_check.get('slippage', 0)
            if slippage > max_slippage_percent and slippage > 0:
                reduction_factor = max_slippage_percent / slippage
                new_position_size_usd = position_size_usd * reduction_factor
                new_quantity = position_info.get('quantity', 0) * reduction_factor
                
                # Làm tròn số lượng
                new_quantity = math.floor(new_quantity * 1000) / 1000
                
                # Cập nhật thông tin vị thế
                position_info['position_size_usd'] = new_position_size_usd
                position_info['quantity'] = new_quantity
                position_info['liquidity_adjusted'] = True
                position_info['liquidity_warning'] = liquidity_check['warning']
                position_info['original_position_size_usd'] = position_size_usd
                
                logger.warning(f"Đã điều chỉnh kích thước vị thế {symbol} do thanh khoản thấp: {liquidity_check['warning']}")
            else:
                # Nếu không phải do slippage, giảm 50% kích thước vị thế
                new_position_size_usd = position_size_usd * 0.5
                new_quantity = position_info.get('quantity', 0) * 0.5
                
                # Làm tròn số lượng
                new_quantity = math.floor(new_quantity * 1000) / 1000
                
                # Cập nhật thông tin vị thế
                position_info['position_size_usd'] = new_position_size_usd
                position_info['quantity'] = new_quantity
                position_info['liquidity_adjusted'] = True
                position_info['liquidity_warning'] = liquidity_check['warning']
                position_info['original_position_size_usd'] = position_size_usd
                
                logger.warning(f"Đã giảm 50% kích thước vị thế {symbol} do thanh khoản thấp: {liquidity_check['warning']}")
        else:
            # Nếu thanh khoản đủ, thêm thông tin liquidity vào position_info
            position_info['liquidity_adjusted'] = False
            position_info['slippage'] = liquidity_check['slippage']
        
        return position_info
    
    def set_position_limits(self, max_positions: int = None, max_positions_per_direction: int = None,
                         position_correlation_threshold: float = None) -> bool:
        """
        Thiết lập giới hạn số lượng vị thế
        
        Args:
            max_positions (int, optional): Số lượng vị thế tối đa
            max_positions_per_direction (int, optional): Số lượng vị thế tối đa theo một hướng
            position_correlation_threshold (float, optional): Ngưỡng tương quan giữa các vị thế
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không
        """
        try:
            # Cập nhật cấu hình
            position_limits = self.config.get('position_limits', {})
            
            if max_positions is not None:
                position_limits['max_positions'] = max_positions
            
            if max_positions_per_direction is not None:
                position_limits['max_positions_per_direction'] = max_positions_per_direction
            
            if position_correlation_threshold is not None:
                position_limits['position_correlation_threshold'] = position_correlation_threshold
            
            # Cập nhật cấu hình
            self.config['position_limits'] = position_limits
            
            # Lưu cấu hình
            return self.save_config()
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập giới hạn vị thế: {str(e)}")
            return False
    
    def set_volatility_adjustment(self, enabled: bool = None, high_volatility_threshold: float = None,
                              low_volatility_threshold: float = None, high_volatility_multiplier: float = None,
                              low_volatility_multiplier: float = None) -> bool:
        """
        Thiết lập điều chỉnh biến động
        
        Args:
            enabled (bool, optional): Bật/tắt điều chỉnh biến động
            high_volatility_threshold (float, optional): Ngưỡng biến động cao
            low_volatility_threshold (float, optional): Ngưỡng biến động thấp
            high_volatility_multiplier (float, optional): Hệ số điều chỉnh biến động cao
            low_volatility_multiplier (float, optional): Hệ số điều chỉnh biến động thấp
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không
        """
        try:
            # Cập nhật cấu hình
            volatility_adjustment = self.config.get('volatility_adjustment', {})
            
            if enabled is not None:
                volatility_adjustment['enabled'] = enabled
            
            if high_volatility_threshold is not None:
                volatility_adjustment['high_volatility_threshold'] = high_volatility_threshold
            
            if low_volatility_threshold is not None:
                volatility_adjustment['low_volatility_threshold'] = low_volatility_threshold
            
            if high_volatility_multiplier is not None:
                volatility_adjustment['high_volatility_multiplier'] = high_volatility_multiplier
            
            if low_volatility_multiplier is not None:
                volatility_adjustment['low_volatility_multiplier'] = low_volatility_multiplier
            
            # Cập nhật cấu hình
            self.config['volatility_adjustment'] = volatility_adjustment
            
            # Lưu cấu hình
            return self.save_config()
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập điều chỉnh biến động: {str(e)}")
            return False
    
    def set_drawdown_protection(self, enabled: bool = None, drawdown_levels: List[float] = None,
                            risk_reduction_percents: List[float] = None) -> bool:
        """
        Thiết lập bảo vệ drawdown
        
        Args:
            enabled (bool, optional): Bật/tắt bảo vệ drawdown
            drawdown_levels (List[float], optional): Các mức drawdown
            risk_reduction_percents (List[float], optional): Các % giảm rủi ro tương ứng
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không
        """
        try:
            # Cập nhật cấu hình
            drawdown_protection = self.config.get('drawdown_protection', {})
            
            if enabled is not None:
                drawdown_protection['enabled'] = enabled
            
            if drawdown_levels is not None:
                drawdown_protection['drawdown_levels'] = drawdown_levels
            
            if risk_reduction_percents is not None:
                drawdown_protection['risk_reduction_percents'] = risk_reduction_percents
            
            # Cập nhật cấu hình
            self.config['drawdown_protection'] = drawdown_protection
            
            # Lưu cấu hình
            return self.save_config()
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập bảo vệ drawdown: {str(e)}")
            return False


def main():
    """Hàm chính để test DynamicRiskAllocator"""
    
    print("=== Testing DynamicRiskAllocator ===\n")
    
    # Khởi tạo DataCache và DynamicRiskAllocator
    data_cache = DataCache()
    risk_allocator = DynamicRiskAllocator(data_cache)
    
    # Lưu dữ liệu giá giả lập vào cache
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    timeframe = "1h"
    
    for symbol in symbols:
        # Tạo dữ liệu biến động ngẫu nhiên
        volatility = random.uniform(0.01, 0.04)
        data_cache.set('market_analysis', f"{symbol}_{timeframe}_volatility", volatility)
        
        # Tạo dữ liệu khối lượng ngẫu nhiên
        volume = random.uniform(10000000, 100000000)
        data_cache.set('market_data', f"{symbol}_ticker", {'quoteVolume': volume})
    
    # Test tính toán risk_percentage
    print("Tính toán risk_percentage cho các cặp tiền:")
    for symbol in symbols:
        risk = risk_allocator.calculate_risk_percentage(symbol, timeframe, 'trending', 10000, 2.0)
        vol = data_cache.get('market_analysis', f"{symbol}_{timeframe}_volatility")
        print(f"- {symbol}: Risk={risk:.2f}%, Volatility={vol:.4f}")
    
    # Test tính toán kích thước vị thế
    print("\nTính toán kích thước vị thế cho BTCUSDT:")
    position_info = risk_allocator.calculate_position_size('BTCUSDT', 50000, 49000, 10000, 1.0, 20.0)
    print(f"- Entry: ${position_info['entry_price']}")
    print(f"- Stop Loss: ${position_info['stop_loss']}")
    print(f"- Risk %: {position_info['risk_percentage']}%")
    print(f"- Risk Amount: ${position_info['risk_amount']:.2f}")
    print(f"- Position Size: ${position_info['position_size_usd']:.2f}")
    print(f"- Quantity: {position_info['quantity']}")
    
    # Test phân bổ vốn
    print("\nPhân bổ vốn cho các cặp tiền:")
    allocation = risk_allocator.allocate_capital(symbols, 10000)
    for symbol, percent in allocation.items():
        print(f"- {symbol}: {percent:.2f}%")
    
    # Test thực hiện phân bổ vốn theo từng phương pháp
    print("\nPhân bổ vốn theo từng phương pháp:")
    
    # Tạo dữ liệu giả lập
    market_data = {}
    strategy_signals = {}
    
    for symbol in symbols:
        market_data[symbol] = {
            'volatility': data_cache.get('market_analysis', f"{symbol}_{timeframe}_volatility"),
            'volume': data_cache.get('market_data', f"{symbol}_ticker", {}).get('quoteVolume', 0)
        }
        
        strategy_signals[symbol] = {
            'composite_signal': {
                'signal': random.choice(['BUY', 'SELL', 'NEUTRAL']),
                'strength': random.uniform(0.1, 1.0)
            }
        }
    
    # Test từng phương pháp
    methods = ['equal', 'volatility_based', 'signal_strength', 'volume_based']
    for method in methods:
        risk_allocator.config['capital_allocation']['method'] = method
        allocation = risk_allocator.allocate_capital(symbols, 10000, market_data, strategy_signals)
        
        print(f"\nPhương pháp: {method}")
        for symbol, percent in allocation.items():
            print(f"- {symbol}: {percent:.2f}%")


if __name__ == "__main__":
    main()