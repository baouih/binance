#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module Tính Toán Đòn Bẩy Động (Dynamic Leverage Calculator)

Module này cung cấp công cụ tự động điều chỉnh đòn bẩy dựa trên biến động thị trường,
chế độ thị trường, và tình trạng tài khoản để tối ưu hóa quản lý rủi ro.
"""

import logging
import json
import time
import datetime
import os
import math
from typing import Dict, List, Tuple, Any, Optional
import pandas as pd
import numpy as np

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('dynamic_leverage')


class DynamicLeverageCalculator:
    """Lớp tính toán đòn bẩy động dựa trên điều kiện thị trường"""
    
    def __init__(self, config_path: str = 'configs/leverage_config.json'):
        """
        Khởi tạo DynamicLeverageCalculator
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
        """
        self.config = self._load_config(config_path)
        self.history = {}
        self.cached_data = {}
        
        # Đảm bảo thư mục data tồn tại
        os.makedirs('data', exist_ok=True)
        
        # Tải lịch sử nếu có
        self._load_decision_history()
        logger.info("Đã khởi tạo Dynamic Leverage Calculator")
    
    def _load_config(self, config_path: str) -> Dict:
        """
        Tải cấu hình từ file hoặc sử dụng cấu hình mặc định
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
            
        Returns:
            Dict: Cấu hình đã tải
        """
        default_config = {
            'default_leverage': 3,
            'max_leverage': 10,
            'min_leverage': 1,
            'market_regime_adjustments': {
                'trending': 1.2,  # Tăng 20% đòn bẩy trong xu hướng rõ ràng
                'ranging': 0.8,   # Giảm 20% đòn bẩy trong thị trường sideway
                'volatile': 0.6,  # Giảm 40% đòn bẩy trong thị trường biến động cao
                'quiet': 1.0,     # Đòn bẩy cơ sở trong thị trường ít biến động
                'neutral': 1.0    # Đòn bẩy cơ sở trong thị trường trung tính
            },
            'volatility_thresholds': {
                'low': 0.01,     # Biến động thấp: <1% 
                'medium': 0.03,  # Biến động trung bình: 1-3%
                'high': 0.05     # Biến động cao: >5%
            },
            'volatility_adjustments': {
                'low': 1.2,      # Tăng 20% đòn bẩy khi biến động thấp
                'medium': 1.0,   # Đòn bẩy cơ sở khi biến động trung bình
                'high': 0.7      # Giảm 30% đòn bẩy khi biến động cao
            },
            'balance_adjustments': {
                'small': 0.8,    # Giảm 20% đòn bẩy khi balance nhỏ (<$1000)
                'medium': 1.0,   # Đòn bẩy cơ sở khi balance trung bình ($1000-$10000)
                'large': 1.2     # Tăng 20% đòn bẩy khi balance lớn (>$10000)
            },
            'balance_thresholds': {
                'small': 1000,   # Ngưỡng balance nhỏ
                'medium': 10000  # Ngưỡng balance trung bình
            },
            'open_positions_adjustments': {
                'none': 1.0,     # Không có vị thế mở
                'few': 0.9,      # Ít vị thế mở (1-3)
                'many': 0.7      # Nhiều vị thế mở (>3)
            },
            'open_positions_thresholds': {
                'few': 3,        # Ngưỡng số vị thế ít
                'many': 5        # Ngưỡng số vị thế nhiều
            },
            'trend_strength_adjustments': {
                'weak': 0.8,     # Giảm 20% đòn bẩy khi xu hướng yếu
                'moderate': 1.0, # Đòn bẩy cơ sở khi xu hướng trung bình
                'strong': 1.2    # Tăng 20% đòn bẩy khi xu hướng mạnh
            },
            'portfolio_correlation_adjustments': {
                'low': 1.1,      # Tăng 10% đòn bẩy khi tương quan thấp (đa dạng hóa tốt)
                'medium': 1.0,   # Đòn bẩy cơ sở khi tương quan trung bình
                'high': 0.8      # Giảm 20% đòn bẩy khi tương quan cao (ít đa dạng hóa)
            },
            'portfolio_correlation_thresholds': {
                'low': 0.3,      # Tương quan thấp: <0.3
                'medium': 0.7    # Tương quan trung bình: 0.3-0.7, cao: >0.7
            },
            'risk_profiles': {
                'conservative': {
                    'default_leverage': 2,
                    'max_leverage': 5,
                    'volatility_adjustments': {
                        'low': 1.1,
                        'medium': 0.9,
                        'high': 0.6
                    }
                },
                'moderate': {
                    'default_leverage': 5,
                    'max_leverage': 10,
                    'volatility_adjustments': {
                        'low': 1.2,
                        'medium': 1.0,
                        'high': 0.7
                    }
                },
                'aggressive': {
                    'default_leverage': 7,
                    'max_leverage': 20,
                    'volatility_adjustments': {
                        'low': 1.3,
                        'medium': 1.1,
                        'high': 0.8
                    }
                }
            }
        }
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {config_path}")
                return config
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning(f"Không thể tải cấu hình từ {config_path}, sử dụng cấu hình mặc định")
            return default_config
    
    def calculate_dynamic_leverage(
        self,
        market_regime: str = 'neutral',
        volatility: float = 0.02,
        account_balance: float = 10000,
        open_positions: int = 0,
        trend_strength: float = 0.5,
        portfolio_correlation: float = 0.5,
        risk_profile: str = 'moderate',
        symbol: str = None,
        timeframe: str = '1h',
        price_ratio_to_ma: float = 1.0
    ) -> Dict:
        """
        Tính toán đòn bẩy động dựa trên các điều kiện thị trường và tài khoản
        
        Args:
            market_regime (str): Chế độ thị trường ('trending', 'ranging', 'volatile', 'quiet', 'neutral')
            volatility (float): Tỷ lệ biến động thị trường (ví dụ: 0.02 = 2%)
            account_balance (float): Số dư tài khoản
            open_positions (int): Số vị thế đang mở
            trend_strength (float): Độ mạnh xu hướng (0-1)
            portfolio_correlation (float): Mức độ tương quan danh mục đầu tư (0-1)
            risk_profile (str): Hồ sơ rủi ro ('conservative', 'moderate', 'aggressive')
            symbol (str, optional): Mã cặp tiền
            timeframe (str, optional): Khung thời gian
            price_ratio_to_ma (float, optional): Tỷ lệ giá hiện tại so với MA
            
        Returns:
            Dict: Kết quả tính toán đòn bẩy
        """
        # Lấy cấu hình cho hồ sơ rủi ro
        profile_config = self.config.get('risk_profiles', {}).get(risk_profile, {})
        
        # Lấy đòn bẩy cơ sở theo hồ sơ rủi ro hoặc mặc định
        base_leverage = profile_config.get('default_leverage', self.config.get('default_leverage', 3))
        max_leverage = profile_config.get('max_leverage', self.config.get('max_leverage', 10))
        min_leverage = profile_config.get('min_leverage', self.config.get('min_leverage', 1))
        
        # Điều chỉnh theo chế độ thị trường
        market_regime_factor = self.config.get('market_regime_adjustments', {}).get(market_regime, 1.0)
        
        # Điều chỉnh theo biến động
        volatility_factor = self._get_volatility_adjustment(volatility, risk_profile)
        
        # Điều chỉnh theo số dư tài khoản
        balance_factor = self._get_balance_adjustment(account_balance)
        
        # Điều chỉnh theo số vị thế mở
        positions_factor = self._get_open_positions_adjustment(open_positions)
        
        # Điều chỉnh theo độ mạnh xu hướng
        trend_factor = self._get_trend_strength_adjustment(trend_strength)
        
        # Điều chỉnh theo tương quan danh mục
        correlation_factor = self._get_correlation_adjustment(portfolio_correlation)
        
        # Điều chỉnh theo tỷ lệ giá/MA
        price_ma_factor = self._get_price_ma_adjustment(price_ratio_to_ma, market_regime)
        
        # Tính đòn bẩy cuối cùng
        final_leverage = (base_leverage * 
                        market_regime_factor * 
                        volatility_factor * 
                        balance_factor * 
                        positions_factor * 
                        trend_factor * 
                        correlation_factor *
                        price_ma_factor)
        
        # Đảm bảo đòn bẩy trong khoảng min-max
        final_leverage = min(max(final_leverage, min_leverage), max_leverage)
        
        # Làm tròn đến 0.5
        final_leverage = round(final_leverage * 2) / 2
        
        # Lưu quyết định
        self._save_decision(
            symbol=symbol,
            timeframe=timeframe,
            market_regime=market_regime,
            volatility=volatility,
            base_leverage=base_leverage,
            final_leverage=final_leverage,
            factors={
                'market_regime': market_regime_factor,
                'volatility': volatility_factor,
                'balance': balance_factor,
                'positions': positions_factor,
                'trend': trend_factor,
                'correlation': correlation_factor,
                'price_ma': price_ma_factor
            }
        )
        
        return {
            'base_leverage': base_leverage,
            'final_leverage': final_leverage,
            'factors': {
                'market_regime': market_regime_factor,
                'volatility': volatility_factor,
                'balance': balance_factor,
                'positions': positions_factor,
                'trend': trend_factor,
                'correlation': correlation_factor,
                'price_ma': price_ma_factor
            },
            'market_regime': market_regime,
            'volatility': volatility,
            'timestamp': int(time.time())
        }
    
    def _get_volatility_adjustment(self, volatility: float, risk_profile: str = 'moderate') -> float:
        """
        Tính hệ số điều chỉnh theo biến động
        
        Args:
            volatility (float): Tỷ lệ biến động
            risk_profile (str): Hồ sơ rủi ro
            
        Returns:
            float: Hệ số điều chỉnh
        """
        # Lấy cấu hình cho hồ sơ rủi ro
        profile_config = self.config.get('risk_profiles', {}).get(risk_profile, {})
        volatility_adjustments = profile_config.get('volatility_adjustments', self.config.get('volatility_adjustments', {}))
        volatility_thresholds = self.config.get('volatility_thresholds', {})
        
        if volatility < volatility_thresholds.get('low', 0.01):
            return volatility_adjustments.get('low', 1.2)
        elif volatility < volatility_thresholds.get('medium', 0.03):
            return volatility_adjustments.get('medium', 1.0)
        else:
            return volatility_adjustments.get('high', 0.7)
    
    def _get_balance_adjustment(self, account_balance: float) -> float:
        """
        Tính hệ số điều chỉnh theo số dư tài khoản
        
        Args:
            account_balance (float): Số dư tài khoản
            
        Returns:
            float: Hệ số điều chỉnh
        """
        balance_adjustments = self.config.get('balance_adjustments', {})
        balance_thresholds = self.config.get('balance_thresholds', {})
        
        if account_balance < balance_thresholds.get('small', 1000):
            return balance_adjustments.get('small', 0.8)
        elif account_balance < balance_thresholds.get('medium', 10000):
            return balance_adjustments.get('medium', 1.0)
        else:
            return balance_adjustments.get('large', 1.2)
    
    def _get_open_positions_adjustment(self, open_positions: int) -> float:
        """
        Tính hệ số điều chỉnh theo số vị thế mở
        
        Args:
            open_positions (int): Số vị thế đang mở
            
        Returns:
            float: Hệ số điều chỉnh
        """
        positions_adjustments = self.config.get('open_positions_adjustments', {})
        positions_thresholds = self.config.get('open_positions_thresholds', {})
        
        if open_positions == 0:
            return positions_adjustments.get('none', 1.0)
        elif open_positions < positions_thresholds.get('few', 3):
            return positions_adjustments.get('few', 0.9)
        else:
            return positions_adjustments.get('many', 0.7)
    
    def _get_trend_strength_adjustment(self, trend_strength: float) -> float:
        """
        Tính hệ số điều chỉnh theo độ mạnh xu hướng
        
        Args:
            trend_strength (float): Độ mạnh xu hướng (0-1)
            
        Returns:
            float: Hệ số điều chỉnh
        """
        trend_adjustments = self.config.get('trend_strength_adjustments', {})
        
        if trend_strength < 0.3:
            return trend_adjustments.get('weak', 0.8)
        elif trend_strength < 0.7:
            return trend_adjustments.get('moderate', 1.0)
        else:
            return trend_adjustments.get('strong', 1.2)
    
    def _get_correlation_adjustment(self, correlation: float) -> float:
        """
        Tính hệ số điều chỉnh theo tương quan danh mục
        
        Args:
            correlation (float): Mức độ tương quan (0-1)
            
        Returns:
            float: Hệ số điều chỉnh
        """
        correlation_adjustments = self.config.get('portfolio_correlation_adjustments', {})
        correlation_thresholds = self.config.get('portfolio_correlation_thresholds', {})
        
        if correlation < correlation_thresholds.get('low', 0.3):
            return correlation_adjustments.get('low', 1.1)
        elif correlation < correlation_thresholds.get('medium', 0.7):
            return correlation_adjustments.get('medium', 1.0)
        else:
            return correlation_adjustments.get('high', 0.8)
    
    def _get_price_ma_adjustment(self, price_ratio: float, market_regime: str) -> float:
        """
        Tính hệ số điều chỉnh theo tỷ lệ giá/MA
        
        Args:
            price_ratio (float): Tỷ lệ giá hiện tại/MA
            market_regime (str): Chế độ thị trường
            
        Returns:
            float: Hệ số điều chỉnh
        """
        # Điều chỉnh đòn bẩy dựa trên vị trí của giá so với MA
        # Trong xu hướng tăng: giá > MA là tốt, giá < MA là xấu
        # Trong xu hướng giảm: giá < MA là tốt, giá > MA là xấu
        # Trong thị trường sideway: giá càng gần MA càng tốt
        
        if market_regime == 'trending':
            # Kiểm tra xem xu hướng là up hay down
            if price_ratio > 1.05:  # Giá > MA (xu hướng tăng)
                return min(price_ratio - 0.9, 1.2)  # Tăng đòn bẩy tối đa 20%
            elif price_ratio < 0.95:  # Giá < MA (xu hướng giảm)
                return min(1.9 - price_ratio, 1.2)  # Tăng đòn bẩy tối đa 20%
            else:
                return 1.0
        elif market_regime == 'ranging':
            # Trong thị trường sideway, giá càng gần MA càng tốt
            distance = abs(price_ratio - 1.0)
            if distance < 0.03:
                return 1.1  # Gần MA, tăng nhẹ
            elif distance < 0.07:
                return 1.0  # Trung bình
            else:
                return 0.9  # Xa MA, giảm nhẹ
        else:
            return 1.0  # Mặc định không điều chỉnh
    
    def _save_decision(self, 
                    symbol: str = None, 
                    timeframe: str = None, 
                    market_regime: str = None, 
                    volatility: float = None, 
                    base_leverage: float = None, 
                    final_leverage: float = None, 
                    factors: Dict = None) -> None:
        """
        Lưu quyết định đòn bẩy để phân tích sau này
        
        Args:
            symbol (str, optional): Mã cặp tiền
            timeframe (str, optional): Khung thời gian
            market_regime (str, optional): Chế độ thị trường
            volatility (float, optional): Tỷ lệ biến động
            base_leverage (float, optional): Đòn bẩy cơ sở
            final_leverage (float, optional): Đòn bẩy cuối cùng
            factors (Dict, optional): Các hệ số điều chỉnh
        """
        if not symbol:
            symbol = 'unknown'
        
        timestamp = int(time.time())
        
        decision = {
            'timestamp': timestamp,
            'timeframe': timeframe,
            'market_regime': market_regime,
            'volatility': volatility,
            'base_leverage': base_leverage,
            'final_leverage': final_leverage,
            'factors': factors
        }
        
        # Khởi tạo danh sách quyết định cho symbol nếu chưa có
        if symbol not in self.history:
            self.history[symbol] = []
        
        # Thêm quyết định mới
        self.history[symbol].append(decision)
        
        # Giới hạn số lượng quyết định lưu trữ (giữ 100 quyết định gần nhất)
        if len(self.history[symbol]) > 100:
            self.history[symbol] = self.history[symbol][-100:]
        
        # Lưu lịch sử định kỳ
        if len(self.history[symbol]) % 10 == 0:
            self._save_decision_history()
    
    def _save_decision_history(self) -> None:
        """Lưu lịch sử quyết định vào file"""
        try:
            with open('data/leverage_decisions.json', 'w') as f:
                json.dump(self.history, f)
            logger.info("Đã lưu lịch sử quyết định đòn bẩy")
        except Exception as e:
            logger.error(f"Lỗi khi lưu lịch sử quyết định: {str(e)}")
    
    def _load_decision_history(self) -> None:
        """Tải lịch sử quyết định từ file"""
        try:
            with open('data/leverage_decisions.json', 'r') as f:
                self.history = json.load(f)
            logger.info("Đã tải lịch sử quyết định đòn bẩy")
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning("Không tìm thấy hoặc không thể tải lịch sử quyết định")
            self.history = {}
    
    def get_leverage_trend(self, symbol: str = None, lookback: int = 20) -> Dict:
        """
        Phân tích xu hướng đòn bẩy trong một khoảng thời gian
        
        Args:
            symbol (str, optional): Mã cặp tiền
            lookback (int): Số quyết định gần nhất để phân tích
            
        Returns:
            Dict: Kết quả phân tích
        """
        if not symbol or symbol not in self.history:
            symbols = list(self.history.keys())
            if not symbols:
                return {
                    'trend_direction': 'unknown',
                    'trend_strength': 0,
                    'current_leverage': 0,
                    'average_leverage': 0,
                    'min_leverage': 0,
                    'max_leverage': 0,
                    'data_points': 0
                }
            symbol = symbols[0]
        
        # Lấy quyết định gần nhất
        decisions = self.history[symbol][-lookback:]
        
        if not decisions:
            return {
                'trend_direction': 'unknown',
                'trend_strength': 0,
                'current_leverage': 0,
                'average_leverage': 0,
                'min_leverage': 0,
                'max_leverage': 0,
                'data_points': 0
            }
        
        # Lấy các giá trị đòn bẩy
        leverages = [d['final_leverage'] for d in decisions]
        
        # Tính các chỉ số
        current_leverage = leverages[-1]
        average_leverage = sum(leverages) / len(leverages)
        min_leverage = min(leverages)
        max_leverage = max(leverages)
        
        # Tính xu hướng
        if len(leverages) < 3:
            trend_direction = 'stable'
            trend_strength = 0
        else:
            # Tính xu hướng đơn giản bằng cách so sánh nửa đầu và nửa sau
            half = len(leverages) // 2
            first_half_avg = sum(leverages[:half]) / half
            second_half_avg = sum(leverages[half:]) / (len(leverages) - half)
            
            difference = second_half_avg - first_half_avg
            
            if abs(difference) < 0.2:
                trend_direction = 'stable'
            else:
                trend_direction = 'increasing' if difference > 0 else 'decreasing'
            
            # Tính độ mạnh xu hướng (0-1)
            max_diff = max_leverage - min_leverage
            trend_strength = abs(difference) / max_diff if max_diff > 0 else 0
        
        return {
            'trend_direction': trend_direction,
            'trend_strength': trend_strength,
            'current_leverage': current_leverage,
            'average_leverage': average_leverage,
            'min_leverage': min_leverage,
            'max_leverage': max_leverage,
            'data_points': len(leverages)
        }
    
    def analyze_volatility_impact(self, symbol: str = None, lookback: int = 20) -> Dict:
        """
        Phân tích tác động của biến động đến đòn bẩy
        
        Args:
            symbol (str, optional): Mã cặp tiền
            lookback (int): Số quyết định gần nhất để phân tích
            
        Returns:
            Dict: Kết quả phân tích
        """
        if not symbol or symbol not in self.history:
            symbols = list(self.history.keys())
            if not symbols:
                return {
                    'correlation': 0,
                    'data_points': 0,
                    'average_volatility': 0,
                    'average_leverage': 0
                }
            symbol = symbols[0]
        
        # Lấy quyết định gần nhất
        decisions = self.history[symbol][-lookback:]
        
        if len(decisions) < 3:
            return {
                'correlation': 0,
                'data_points': len(decisions),
                'average_volatility': 0,
                'average_leverage': 0
            }
        
        # Lấy các giá trị
        volatilities = [d.get('volatility', 0) for d in decisions]
        leverages = [d.get('final_leverage', 0) for d in decisions]
        
        # Tính tương quan
        try:
            correlation = np.corrcoef(volatilities, leverages)[0, 1]
        except:
            correlation = 0
        
        # Tính trung bình
        avg_volatility = sum(volatilities) / len(volatilities)
        avg_leverage = sum(leverages) / len(leverages)
        
        return {
            'correlation': correlation,
            'data_points': len(decisions),
            'average_volatility': avg_volatility,
            'average_leverage': avg_leverage,
            'interpretation': self._interpret_correlation(correlation, 'volatility', 'leverage')
        }
    
    def analyze_market_regime_impact(self, symbol: str = None, lookback: int = 50) -> Dict:
        """
        Phân tích tác động của chế độ thị trường đến đòn bẩy
        
        Args:
            symbol (str, optional): Mã cặp tiền
            lookback (int): Số quyết định gần nhất để phân tích
            
        Returns:
            Dict: Kết quả phân tích
        """
        if not symbol or symbol not in self.history:
            symbols = list(self.history.keys())
            if not symbols:
                return {
                    'regime_leverages': {},
                    'data_points': 0
                }
            symbol = symbols[0]
        
        # Lấy quyết định gần nhất
        decisions = self.history[symbol][-lookback:]
        
        if not decisions:
            return {
                'regime_leverages': {},
                'data_points': 0
            }
        
        # Nhóm theo chế độ thị trường
        regime_groups = {}
        
        for d in decisions:
            regime = d.get('market_regime', 'unknown')
            leverage = d.get('final_leverage', 0)
            
            if regime not in regime_groups:
                regime_groups[regime] = []
            
            regime_groups[regime].append(leverage)
        
        # Tính trung bình cho mỗi chế độ
        regime_leverages = {}
        for regime, leverages in regime_groups.items():
            regime_leverages[regime] = {
                'average': sum(leverages) / len(leverages),
                'min': min(leverages),
                'max': max(leverages),
                'count': len(leverages)
            }
        
        return {
            'regime_leverages': regime_leverages,
            'data_points': len(decisions)
        }
    
    def _interpret_correlation(self, correlation: float, var1: str, var2: str) -> str:
        """
        Diễn giải ý nghĩa của hệ số tương quan
        
        Args:
            correlation (float): Hệ số tương quan
            var1 (str): Tên biến thứ nhất
            var2 (str): Tên biến thứ hai
            
        Returns:
            str: Diễn giải
        """
        abs_corr = abs(correlation)
        
        if abs_corr < 0.3:
            strength = "rất yếu"
        elif abs_corr < 0.5:
            strength = "yếu"
        elif abs_corr < 0.7:
            strength = "trung bình"
        elif abs_corr < 0.9:
            strength = "mạnh"
        else:
            strength = "rất mạnh"
        
        direction = "dương" if correlation > 0 else "âm"
        
        return f"Tương quan {direction} {strength} giữa {var1} và {var2}. " + \
               (f"Khi {var1} tăng, {var2} có xu hướng tăng." if correlation > 0 else f"Khi {var1} tăng, {var2} có xu hướng giảm.")
    
    def get_recommended_leverage_profile(self, 
                                       account_balance: float, 
                                       trading_experience: str = 'intermediate',
                                       risk_tolerance: str = 'moderate') -> str:
        """
        Gợi ý hồ sơ đòn bẩy phù hợp dựa trên số dư tài khoản và kinh nghiệm giao dịch
        
        Args:
            account_balance (float): Số dư tài khoản
            trading_experience (str): Kinh nghiệm giao dịch ('beginner', 'intermediate', 'expert')
            risk_tolerance (str): Khả năng chịu đựng rủi ro ('low', 'moderate', 'high')
            
        Returns:
            str: Hồ sơ đòn bẩy khuyên dùng ('conservative', 'moderate', 'aggressive')
        """
        # Xếp hạng dựa trên số dư
        if account_balance < 1000:
            balance_score = 1  # conservative
        elif account_balance < 10000:
            balance_score = 2  # moderate
        else:
            balance_score = 3  # aggressive
        
        # Xếp hạng dựa trên kinh nghiệm
        experience_score = {
            'beginner': 1,
            'intermediate': 2,
            'expert': 3
        }.get(trading_experience.lower(), 2)
        
        # Xếp hạng dựa trên khả năng chịu đựng rủi ro
        risk_score = {
            'low': 1,
            'moderate': 2,
            'high': 3
        }.get(risk_tolerance.lower(), 2)
        
        # Tính điểm tổng hợp
        total_score = balance_score + experience_score + risk_score
        
        # Quyết định hồ sơ
        if total_score <= 4:
            return 'conservative'
        elif total_score <= 7:
            return 'moderate'
        else:
            return 'aggressive'
    
    def calculate_risk_adjusted_position_size(self, 
                                           leverage: float, 
                                           account_balance: float,
                                           risk_per_trade: float = 2.0,
                                           stop_loss_percent: float = 1.0) -> Dict:
        """
        Tính kích thước vị thế điều chỉnh theo rủi ro
        
        Args:
            leverage (float): Đòn bẩy
            account_balance (float): Số dư tài khoản
            risk_per_trade (float): Phần trăm rủi ro trên mỗi giao dịch
            stop_loss_percent (float): Phần trăm stop loss
            
        Returns:
            Dict: Kết quả tính toán
        """
        # Tính số tiền rủi ro
        risk_amount = account_balance * (risk_per_trade / 100)
        
        # Tính kích thước vị thế (position size = risk_amount / (stop_loss_percent * entry_price))
        # Giả sử entry_price = 1 để có kích thước tương đối
        position_size_usd = risk_amount / (stop_loss_percent / 100)
        
        # Điều chỉnh theo đòn bẩy
        adjusted_position_size = position_size_usd / leverage
        
        # Tính margin sử dụng
        margin_used = position_size_usd / leverage
        
        # Tính phần trăm margin sử dụng
        margin_percent = (margin_used / account_balance) * 100
        
        return {
            'account_balance': account_balance,
            'leverage': leverage,
            'risk_per_trade_percent': risk_per_trade,
            'stop_loss_percent': stop_loss_percent,
            'risk_amount': risk_amount,
            'position_size_usd': position_size_usd,
            'adjusted_position_size': adjusted_position_size,
            'margin_used': margin_used,
            'margin_percent': margin_percent
        }
    
    def recommend_leverage_for_market_phase(self, 
                                          market_phase: str, 
                                          volatility_index: float,
                                          risk_profile: str = 'moderate') -> Dict:
        """
        Gợi ý đòn bẩy phù hợp với giai đoạn thị trường
        
        Args:
            market_phase (str): Giai đoạn thị trường 
                                ('bull_run', 'bear_market', 'sideways', 'recovery', 'distribution', 'accumulation')
            volatility_index (float): Chỉ số biến động (vd: ATR/Giá)
            risk_profile (str): Hồ sơ rủi ro ('conservative', 'moderate', 'aggressive')
            
        Returns:
            Dict: Gợi ý đòn bẩy
        """
        # Lấy cấu hình cho hồ sơ rủi ro
        profile_config = self.config.get('risk_profiles', {}).get(risk_profile, {})
        base_leverage = profile_config.get('default_leverage', self.config.get('default_leverage', 3))
        
        # Hệ số điều chỉnh theo giai đoạn thị trường
        phase_adjustments = {
            'bull_run': 1.3,      # Thị trường tăng mạnh, tận dụng xu hướng
            'bear_market': 0.7,   # Thị trường giảm mạnh, thận trọng
            'sideways': 0.8,      # Thị trường đi ngang, ít cơ hội
            'recovery': 1.1,      # Thị trường phục hồi, cơ hội ổn định
            'distribution': 0.7,  # Giai đoạn phân phối, rủi ro cao
            'accumulation': 1.0   # Giai đoạn tích lũy, cơ hội đang hình thành
        }
        
        phase_factor = phase_adjustments.get(market_phase, 1.0)
        
        # Điều chỉnh thêm theo biến động
        volatility_factor = 1.0
        if volatility_index < 0.01:
            volatility_factor = 1.2  # Biến động thấp, tăng đòn bẩy
        elif volatility_index > 0.05:
            volatility_factor = 0.7  # Biến động cao, giảm đòn bẩy
        
        # Tính đòn bẩy gợi ý
        recommended_leverage = base_leverage * phase_factor * volatility_factor
        
        # Làm tròn đến 0.5
        recommended_leverage = round(recommended_leverage * 2) / 2
        
        # Giới hạn đòn bẩy
        max_leverage = profile_config.get('max_leverage', self.config.get('max_leverage', 10))
        min_leverage = profile_config.get('min_leverage', self.config.get('min_leverage', 1))
        recommended_leverage = min(max(recommended_leverage, min_leverage), max_leverage)
        
        return {
            'market_phase': market_phase,
            'volatility_index': volatility_index,
            'risk_profile': risk_profile,
            'base_leverage': base_leverage,
            'phase_adjustment': phase_factor,
            'volatility_adjustment': volatility_factor,
            'recommended_leverage': recommended_leverage
        }


def main():
    """Hàm chính để test"""
    calculator = DynamicLeverageCalculator()
    
    # Test 1: Tính đòn bẩy trong điều kiện khác nhau
    print("Test 1: Chế độ thị trường khác nhau")
    for regime in ['trending', 'ranging', 'volatile', 'quiet', 'neutral']:
        result = calculator.calculate_dynamic_leverage(market_regime=regime)
        print(f"Chế độ {regime}: Đòn bẩy = {result['final_leverage']}x")
    
    # Test 2: Các mức biến động khác nhau
    print("\nTest 2: Mức biến động khác nhau")
    for vol in [0.01, 0.02, 0.05, 0.1]:
        result = calculator.calculate_dynamic_leverage(volatility=vol)
        print(f"Biến động {vol*100}%: Đòn bẩy = {result['final_leverage']}x")
    
    # Test 3: Phân tích xu hướng đòn bẩy
    print("\nTest 3: Phân tích xu hướng đòn bẩy")
    trend = calculator.get_leverage_trend()
    print(f"Xu hướng: {trend['trend_direction']}, Mạnh: {trend['trend_strength']:.2f}")
    print(f"Đòn bẩy hiện tại: {trend['current_leverage']}x, Trung bình: {trend['average_leverage']:.2f}x")
    
    # Test 4: Gợi ý hồ sơ đòn bẩy
    print("\nTest 4: Gợi ý hồ sơ đòn bẩy")
    profile = calculator.get_recommended_leverage_profile(
        account_balance=5000,
        trading_experience='intermediate',
        risk_tolerance='moderate'
    )
    print(f"Hồ sơ đòn bẩy khuyên dùng: {profile}")
    
    # Test 5: Tính kích thước vị thế điều chỉnh theo rủi ro
    print("\nTest 5: Kích thước vị thế điều chỉnh theo rủi ro")
    position = calculator.calculate_risk_adjusted_position_size(
        leverage=5,
        account_balance=10000,
        risk_per_trade=2.0,
        stop_loss_percent=1.0
    )
    print(f"Số tiền rủi ro: ${position['risk_amount']:.2f}")
    print(f"Kích thước vị thế: ${position['position_size_usd']:.2f}")
    print(f"Margin sử dụng: ${position['margin_used']:.2f} ({position['margin_percent']:.2f}%)")


if __name__ == "__main__":
    main()