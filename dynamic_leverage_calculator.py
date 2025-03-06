#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module tính toán đòn bẩy động (Dynamic Leverage Calculator)

Module này cung cấp các công cụ để tính toán đòn bẩy tối ưu dựa trên nhiều yếu tố
như chế độ thị trường, biến động, số dư tài khoản, và mức độ tương quan danh mục đầu tư.
"""

import os
import sys
import json
import time
import math
import logging
import datetime
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('leverage_calculator.log')
    ]
)
logger = logging.getLogger('leverage_calculator')

# Thêm thư mục gốc vào sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import các module cần thiết
try:
    from binance_api import BinanceAPI
except ImportError:
    logger.error("Không thể import module binance_api. Hãy đảm bảo bạn đang chạy từ thư mục gốc.")
    binance_api_available = False
else:
    binance_api_available = True

class DynamicLeverageCalculator:
    """Lớp tính toán đòn bẩy động dựa trên điều kiện thị trường"""
    
    def __init__(self, config_path: str = 'configs/dynamic_leverage_config.json'):
        """
        Khởi tạo Dynamic Leverage Calculator
        
        Args:
            config_path: Đường dẫn đến file cấu hình
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.decision_history = []
        
    def _load_config(self) -> Dict:
        """
        Tải cấu hình từ file
        
        Returns:
            Dict: Cấu hình đã tải
        """
        default_config = {
            "base_leverage": {
                "conservative": 2.0,
                "moderate": 3.0,
                "aggressive": 4.0
            },
            "regime_multiplier": {
                "trending": 1.2,
                "ranging": 0.7,
                "volatile": 0.5,
                "quiet": 0.9,
                "neutral": 1.0
            },
            "max_leverage": 5.0,
            "min_leverage": 1.0,
            "weights": {
                "regime": 0.3,
                "volatility": 0.25,
                "balance": 0.1,
                "positions": 0.15,
                "correlation": 0.1,
                "price_to_ma": 0.1
            },
            "default_risk_profile": "moderate"
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
                
                # Merge với default config
                for key, value in loaded_config.items():
                    default_config[key] = value
                    
                return default_config
            else:
                # Lưu default config
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                with open(self.config_path, 'w') as f:
                    json.dump(default_config, f, indent=4)
                logger.info(f"Đã tạo file cấu hình mặc định tại {self.config_path}")
                return default_config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
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
    
    def update_config(self, new_config: Dict) -> bool:
        """
        Cập nhật cấu hình
        
        Args:
            new_config: Cấu hình mới
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không
        """
        try:
            # Cập nhật từng phần của config
            for key, value in new_config.items():
                if key in self.config:
                    if isinstance(value, dict) and isinstance(self.config[key], dict):
                        # Merge nested dict
                        self.config[key].update(value)
                    else:
                        self.config[key] = value
                else:
                    self.config[key] = value
                    
            # Lưu config mới
            return self.save_config()
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật cấu hình: {str(e)}")
            return False
    
    def calculate_dynamic_leverage(
        self, market_regime: str, volatility: float, account_balance: float, 
        risk_profile: str = None, max_open_positions: int = 0, 
        portfolio_correlation: float = 0, price_ratio_to_ma: float = 1.0,
        symbol: str = None
    ) -> Dict:
        """
        Tính toán đòn bẩy động dựa trên nhiều yếu tố
        
        Args:
            market_regime: Chế độ thị trường ('trending', 'ranging', etc.)
            volatility: Biến động thị trường 
            account_balance: Số dư tài khoản (USDT)
            risk_profile: Mức độ chấp nhận rủi ro ('conservative', 'moderate', 'aggressive')
            max_open_positions: Số vị thế đang mở
            portfolio_correlation: Mức độ tương quan trong danh mục (0-1)
            price_ratio_to_ma: Tỷ lệ giá hiện tại so với MA200
            symbol: Cặp giao dịch (nếu có)
        
        Returns:
            Dict: Thông tin đòn bẩy đề xuất và các thành phần
        """
        # Kiểm tra và sử dụng cấu hình mặc định nếu cần
        risk_profile = risk_profile or self.config.get('default_risk_profile', 'moderate')
        
        # Lấy đòn bẩy cơ sở theo mức độ rủi ro
        base_leverage = self.config.get('base_leverage', {}).get(
            risk_profile, 
            self.config.get('base_leverage', {}).get('moderate', 3.0)
        )
        
        # Lấy hệ số nhân theo chế độ thị trường
        regime_multiplier = self.config.get('regime_multiplier', {}).get(
            market_regime, 
            self.config.get('regime_multiplier', {}).get('neutral', 1.0)
        )
        
        # Tính hệ số theo biến động (tỷ lệ nghịch)
        # volatility càng cao, đòn bẩy càng thấp
        volatility_factor = max(0.5, min(1.2, 0.04/max(volatility, 0.001)))
        
        # Tính hệ số theo kích thước tài khoản (tăng nhẹ khi tài khoản lớn)
        balance_factor = min(1.2, max(0.8, math.log10(max(account_balance, 100)/1000)))
        
        # Tính hệ số theo số vị thế đang mở (càng nhiều vị thế, đòn bẩy càng thấp)
        position_factor = max(0.7, 1.0 - (max_open_positions * 0.05))
        
        # Tính hệ số theo tương quan danh mục (càng tương quan, đòn bẩy càng thấp)
        correlation_factor = max(0.7, 1.0 - max(0, portfolio_correlation) * 0.5)
        
        # Tính hệ số theo vị trí giá so với MA (xa MA, giảm đòn bẩy)
        ma_factor = max(0.8, min(1.2, 1.0 / max(0.7, abs(price_ratio_to_ma - 1.0) * 5)))
        
        # Lấy trọng số
        weights = self.config.get('weights', {
            'regime': 0.3,
            'volatility': 0.25,
            'balance': 0.1,
            'positions': 0.15,
            'correlation': 0.1,
            'price_to_ma': 0.1
        })
        
        # Tính đòn bẩy tối ưu với trọng số
        optimal_leverage = (
            base_leverage * regime_multiplier * weights.get('regime', 0.3) +
            base_leverage * volatility_factor * weights.get('volatility', 0.25) +
            base_leverage * balance_factor * weights.get('balance', 0.1) +
            base_leverage * position_factor * weights.get('positions', 0.15) +
            base_leverage * correlation_factor * weights.get('correlation', 0.1) +
            base_leverage * ma_factor * weights.get('price_to_ma', 0.1)
        )
        
        # Giới hạn trong phạm vi an toàn
        min_leverage = self.config.get('min_leverage', 1.0)
        max_leverage = self.config.get('max_leverage', 5.0)
        final_leverage = max(min_leverage, min(max_leverage, round(optimal_leverage, 1)))
        
        # Lưu quyết định vào lịch sử
        decision = {
            'timestamp': int(time.time()),
            'symbol': symbol,
            'market_regime': market_regime,
            'volatility': volatility,
            'account_balance': account_balance,
            'risk_profile': risk_profile,
            'max_open_positions': max_open_positions,
            'portfolio_correlation': portfolio_correlation,
            'price_ratio_to_ma': price_ratio_to_ma,
            'base_leverage': base_leverage,
            'final_leverage': final_leverage,
            'factors': {
                'regime_multiplier': regime_multiplier,
                'volatility_factor': volatility_factor,
                'balance_factor': balance_factor,
                'position_factor': position_factor,
                'correlation_factor': correlation_factor,
                'ma_factor': ma_factor
            }
        }
        
        self.decision_history.append(decision)
        
        # Giới hạn kích thước lịch sử
        if len(self.decision_history) > 1000:
            self.decision_history = self.decision_history[-1000:]
            
        logger.info(f"Đã tính toán đòn bẩy động: {final_leverage}x (chế độ thị trường: {market_regime}, biến động: {volatility:.4f})")
        
        return decision
    
    def get_recent_decisions(self, limit: int = 10, symbol: str = None) -> List[Dict]:
        """
        Lấy các quyết định gần đây
        
        Args:
            limit: Số lượng quyết định tối đa
            symbol: Lọc theo cặp giao dịch
            
        Returns:
            List[Dict]: Danh sách quyết định
        """
        if symbol:
            filtered = [d for d in self.decision_history if d.get('symbol') == symbol]
            return filtered[-limit:] if filtered else []
        else:
            return self.decision_history[-limit:] if self.decision_history else []
    
    def save_decision_history(self, file_path: str = 'leverage_decisions.json') -> bool:
        """
        Lưu lịch sử quyết định vào file
        
        Args:
            file_path: Đường dẫn đến file
            
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(self.decision_history, f, indent=4)
            logger.info(f"Đã lưu lịch sử quyết định vào {file_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu lịch sử quyết định: {str(e)}")
            return False
    
    def load_decision_history(self, file_path: str = 'leverage_decisions.json') -> bool:
        """
        Tải lịch sử quyết định từ file
        
        Args:
            file_path: Đường dẫn đến file
            
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    self.decision_history = json.load(f)
                logger.info(f"Đã tải lịch sử quyết định từ {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Lỗi khi tải lịch sử quyết định: {str(e)}")
            return False
    
    def get_leverage_trend(self, symbol: str = None, days: int = 7) -> Dict:
        """
        Phân tích xu hướng đòn bẩy trong khoảng thời gian
        
        Args:
            symbol: Cặp giao dịch
            days: Số ngày cần phân tích
            
        Returns:
            Dict: Thông tin xu hướng đòn bẩy
        """
        # Lọc dữ liệu
        now = int(time.time())
        start_time = now - days * 24 * 3600
        
        if symbol:
            decisions = [d for d in self.decision_history 
                        if d.get('timestamp', 0) >= start_time and d.get('symbol') == symbol]
        else:
            decisions = [d for d in self.decision_history 
                        if d.get('timestamp', 0) >= start_time]
        
        if not decisions:
            return {'error': 'Không đủ dữ liệu'}
        
        # Tính các thống kê
        leverages = [d.get('final_leverage', 1.0) for d in decisions]
        avg_leverage = sum(leverages) / len(leverages) if leverages else 1.0
        max_leverage = max(leverages) if leverages else 1.0
        min_leverage = min(leverages) if leverages else 1.0
        
        # Tính xu hướng (hệ số góc)
        if len(decisions) >= 2:
            times = [d.get('timestamp', 0) for d in decisions]
            min_time = min(times)
            max_time = max(times)
            
            if max_time > min_time:
                # Chuẩn hóa thời gian về 0-1
                normalized_times = [(t - min_time) / (max_time - min_time) for t in times]
                
                # Tính hệ số góc
                slope = 0
                n = len(normalized_times)
                sum_x = sum(normalized_times)
                sum_y = sum(leverages)
                sum_xy = sum(x*y for x, y in zip(normalized_times, leverages))
                sum_xx = sum(x*x for x in normalized_times)
                
                slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x) if (n * sum_xx - sum_x * sum_x) != 0 else 0
            else:
                slope = 0
        else:
            slope = 0
        
        return {
            'symbol': symbol,
            'days': days,
            'data_points': len(decisions),
            'average_leverage': avg_leverage,
            'max_leverage': max_leverage,
            'min_leverage': min_leverage,
            'trend_slope': slope,
            'trend_direction': 'increasing' if slope > 0.1 else ('decreasing' if slope < -0.1 else 'stable'),
            'current_leverage': leverages[-1] if leverages else None,
            'samples': decisions
        }
    
    def analyze_volatility_impact(self, symbol: str = None, days: int = 30) -> Dict:
        """
        Phân tích tác động của biến động đến đòn bẩy
        
        Args:
            symbol: Cặp giao dịch
            days: Số ngày cần phân tích
            
        Returns:
            Dict: Thông tin phân tích
        """
        # Lọc dữ liệu
        now = int(time.time())
        start_time = now - days * 24 * 3600
        
        if symbol:
            decisions = [d for d in self.decision_history 
                        if d.get('timestamp', 0) >= start_time and d.get('symbol') == symbol]
        else:
            decisions = [d for d in self.decision_history 
                        if d.get('timestamp', 0) >= start_time]
        
        if not decisions:
            return {'error': 'Không đủ dữ liệu'}
        
        # Tính tương quan giữa biến động và đòn bẩy
        volatilities = [d.get('volatility', 0.01) for d in decisions]
        leverages = [d.get('final_leverage', 1.0) for d in decisions]
        
        # Tính hệ số tương quan
        correlation = 0
        if len(volatilities) >= 2 and len(leverages) >= 2:
            n = len(volatilities)
            sum_x = sum(volatilities)
            sum_y = sum(leverages)
            sum_xy = sum(x*y for x, y in zip(volatilities, leverages))
            sum_xx = sum(x*x for x in volatilities)
            sum_yy = sum(y*y for y in leverages)
            
            numerator = n * sum_xy - sum_x * sum_y
            denominator = math.sqrt((n * sum_xx - sum_x * sum_x) * (n * sum_yy - sum_y * sum_y))
            
            correlation = numerator / denominator if denominator != 0 else 0
        
        # Phân loại biến động
        volatility_ranges = {
            'low': [],
            'medium': [],
            'high': []
        }
        
        for d in decisions:
            vol = d.get('volatility', 0.01)
            lev = d.get('final_leverage', 1.0)
            
            if vol < 0.02:
                volatility_ranges['low'].append(lev)
            elif vol < 0.05:
                volatility_ranges['medium'].append(lev)
            else:
                volatility_ranges['high'].append(lev)
        
        # Tính trung bình đòn bẩy cho mỗi khoảng biến động
        avg_leverage_by_volatility = {}
        for key, values in volatility_ranges.items():
            avg_leverage_by_volatility[key] = sum(values) / len(values) if values else None
        
        return {
            'symbol': symbol,
            'days': days,
            'correlation': correlation,
            'relationship': 'strong_negative' if correlation < -0.7 else
                           ('negative' if correlation < -0.3 else
                           ('weak' if abs(correlation) <= 0.3 else
                           ('positive' if correlation < 0.7 else 'strong_positive'))),
            'avg_leverage_by_volatility': avg_leverage_by_volatility,
            'data_points': len(decisions)
        }
    
    def analyze_market_regime_impact(self, symbol: str = None, days: int = 30) -> Dict:
        """
        Phân tích tác động của chế độ thị trường đến đòn bẩy
        
        Args:
            symbol: Cặp giao dịch
            days: Số ngày cần phân tích
            
        Returns:
            Dict: Thông tin phân tích
        """
        # Lọc dữ liệu
        now = int(time.time())
        start_time = now - days * 24 * 3600
        
        if symbol:
            decisions = [d for d in self.decision_history 
                        if d.get('timestamp', 0) >= start_time and d.get('symbol') == symbol]
        else:
            decisions = [d for d in self.decision_history 
                        if d.get('timestamp', 0) >= start_time]
        
        if not decisions:
            return {'error': 'Không đủ dữ liệu'}
        
        # Phân loại theo chế độ thị trường
        regime_leverages = {}
        for d in decisions:
            regime = d.get('market_regime', 'neutral')
            leverage = d.get('final_leverage', 1.0)
            
            if regime not in regime_leverages:
                regime_leverages[regime] = []
                
            regime_leverages[regime].append(leverage)
        
        # Tính trung bình đòn bẩy cho mỗi chế độ
        avg_leverage_by_regime = {}
        for regime, leverages in regime_leverages.items():
            avg_leverage_by_regime[regime] = sum(leverages) / len(leverages)
        
        # Tần suất của mỗi chế độ
        regime_frequency = {}
        total_decisions = len(decisions)
        for regime, leverages in regime_leverages.items():
            regime_frequency[regime] = len(leverages) / total_decisions if total_decisions > 0 else 0
        
        return {
            'symbol': symbol,
            'days': days,
            'avg_leverage_by_regime': avg_leverage_by_regime,
            'regime_frequency': regime_frequency,
            'recommended_leverage_by_regime': self.config.get('regime_multiplier', {}),
            'data_points': len(decisions)
        }
    
    def get_recommendation(self, symbol: str, market_data: Dict) -> Dict:
        """
        Lấy đề xuất đòn bẩy cho một cặp giao dịch dựa trên dữ liệu thị trường
        
        Args:
            symbol: Cặp giao dịch
            market_data: Dữ liệu thị trường
                {
                    'market_regime': str,
                    'volatility': float,
                    'account_balance': float,
                    'max_open_positions': int,
                    'portfolio_correlation': float,
                    'price_ratio_to_ma': float,
                    'risk_profile': str
                }
                
        Returns:
            Dict: Đề xuất đòn bẩy
        """
        # Kiểm tra dữ liệu đầu vào
        if not all(k in market_data for k in ['market_regime', 'volatility', 'account_balance']):
            logger.error("Thiếu dữ liệu thị trường cần thiết")
            return {'error': 'Thiếu dữ liệu thị trường cần thiết'}
        
        # Tính toán đòn bẩy động
        return self.calculate_dynamic_leverage(
            market_regime=market_data['market_regime'],
            volatility=market_data['volatility'],
            account_balance=market_data['account_balance'],
            risk_profile=market_data.get('risk_profile'),
            max_open_positions=market_data.get('max_open_positions', 0),
            portfolio_correlation=market_data.get('portfolio_correlation', 0),
            price_ratio_to_ma=market_data.get('price_ratio_to_ma', 1.0),
            symbol=symbol
        )


def main():
    """Hàm chính để test DynamicLeverageCalculator"""
    # Khởi tạo DynamicLeverageCalculator
    calculator = DynamicLeverageCalculator()
    
    # Ví dụ tính đòn bẩy động cho các chế độ thị trường khác nhau
    regimes = ['trending', 'ranging', 'volatile', 'quiet', 'neutral']
    
    print("\n=== Ví dụ tính đòn bẩy động cho các chế độ thị trường ===")
    for regime in regimes:
        result = calculator.calculate_dynamic_leverage(
            market_regime=regime,
            volatility=0.02,  # 2% biến động
            account_balance=10000,  # 10,000 USDT
            symbol='BTCUSDT'
        )
        print(f"Chế độ thị trường: {regime}, Đòn bẩy: {result['final_leverage']}x")
    
    # Ví dụ tính đòn bẩy động với các mức biến động khác nhau
    volatilities = [0.01, 0.02, 0.05, 0.1]
    
    print("\n=== Ví dụ tính đòn bẩy động với các mức biến động khác nhau ===")
    for vol in volatilities:
        result = calculator.calculate_dynamic_leverage(
            market_regime='neutral',
            volatility=vol,
            account_balance=10000,
            symbol='BTCUSDT'
        )
        print(f"Biến động: {vol*100:.1f}%, Đòn bẩy: {result['final_leverage']}x")
    
    # Ví dụ tính đòn bẩy động với các mức độ rủi ro khác nhau
    risk_profiles = ['conservative', 'moderate', 'aggressive']
    
    print("\n=== Ví dụ tính đòn bẩy động với các mức độ rủi ro khác nhau ===")
    for profile in risk_profiles:
        result = calculator.calculate_dynamic_leverage(
            market_regime='neutral',
            volatility=0.02,
            account_balance=10000,
            risk_profile=profile,
            symbol='BTCUSDT'
        )
        print(f"Mức độ rủi ro: {profile}, Đòn bẩy: {result['final_leverage']}x")
    
    # Phân tích tác động của biến động đến đòn bẩy
    print("\n=== Phân tích tác động của biến động đến đòn bẩy ===")
    # Mô phỏng dữ liệu lịch sử
    for i in range(30):
        vol = 0.01 + (i % 10) * 0.01  # 1% to 10%
        calculator.calculate_dynamic_leverage(
            market_regime='neutral',
            volatility=vol,
            account_balance=10000,
            symbol='BTCUSDT'
        )
    
    analysis = calculator.analyze_volatility_impact(symbol='BTCUSDT')
    print(f"Tương quan biến động-đòn bẩy: {analysis['correlation']:.2f} ({analysis['relationship']})")
    print(f"Đòn bẩy trung bình theo biến động: {analysis['avg_leverage_by_volatility']}")
    

if __name__ == "__main__":
    main()