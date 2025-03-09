#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script kiểm thử Position Manager

Script này kiểm tra các chức năng của Position Manager với các tình huống khác nhau.
"""

import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from position_manager import PositionManager
from data_cache import DataCache

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockDataCache:
    """Lớp giả lập Data Cache để kiểm thử"""
    
    def __init__(self):
        self.data = {
            'indicators': {
                'BTCUSDT_1h_rsi': 65.0,  # Giá trị RSI
                'ETHUSDT_1h_rsi': 72.0,  # RSI quá mua
                'BNBUSDT_1h_rsi': 28.0   # RSI quá bán
            },
            'market_analysis': {
                'BTCUSDT_1h_volatility': 0.02,  # Biến động trung bình
                'ETHUSDT_1h_volatility': 0.04,  # Biến động cao
                'BNBUSDT_1h_volatility': 0.01   # Biến động thấp
            },
            'market_data': {
                'BTCUSDT_1h_candles': [
                    {'open': 51000, 'close': 51500, 'high': 51600, 'low': 50900},  # Nến xanh
                    {'open': 50500, 'close': 51000, 'high': 51200, 'low': 50400},  # Nến xanh
                    {'open': 50000, 'close': 50500, 'high': 50700, 'low': 49900}   # Nến xanh
                ],
                'ETHUSDT_1h_candles': [
                    {'open': 2200, 'close': 2150, 'high': 2210, 'low': 2140},  # Nến đỏ
                    {'open': 2250, 'close': 2200, 'high': 2260, 'low': 2190},  # Nến đỏ
                    {'open': 2300, 'close': 2250, 'high': 2310, 'low': 2240}   # Nến đỏ
                ]
            }
        }
    
    def get(self, category, key, default=None):
        """Lấy dữ liệu từ cache"""
        if category in self.data and key in self.data[category]:
            return self.data[category][key]
        return default
    
    def set(self, category, key, value):
        """Cập nhật dữ liệu vào cache"""
        if category not in self.data:
            self.data[category] = {}
        self.data[category][key] = value


def test_percentage_trailing_stop_with_profit_target():
    """Kiểm tra trailing stop percentage kết hợp với chốt lời theo target"""
    logger.info("=== Kiểm tra Percentage Trailing Stop kết hợp với Profit Target ===")
    
    # Tạo cache
    data_cache = MockDataCache()
    
    # Tạo cấu hình
    trailing_config = {
        'strategy_type': 'percentage',
        'config': {
            'activation_percent': 1.0,
            'callback_percent': 0.5
        }
    }
    
    profit_config = {
        'time_based': {
            'enabled': False
        },
        'target_profit': {
            'enabled': True,
            'profit_target': 2.0  # Chốt lời ở 2%
        },
        'indicator_based': {
            'enabled': False
        },
        'price_reversal': {
            'enabled': False
        },
        'dynamic_volatility': {
            'enabled': False
        }
    }
    
    # Tạo position manager
    position_manager = PositionManager(trailing_config, profit_config, data_cache)
    
    # Tạo vị thế
    position = {
        'id': 'test_long_position',
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry_price': 50000,
        'quantity': 0.1,
        'entry_time': datetime.now()
    }
    
    # Khởi tạo vị thế
    position = position_manager.initialize_position(position)
    
    # Mô phỏng cập nhật giá
    prices = [
        50200,  # +0.4%
        50500,  # +1.0% (kích hoạt trailing stop)
        50800,  # +1.6%
        51000,  # +2.0% (đạt target profit)
        51200,  # +2.4%
        51000,  # +2.0%
        50800   # +1.6%
    ]
    
    results = []
    
    for price in prices:
        # Cập nhật vị thế
        position = position_manager.update_position(position, price)
        
        # Kiểm tra điều kiện đóng
        should_close, reason = position_manager.check_exit_conditions(position, price)
        
        # Hiển thị trạng thái
        summary = position_manager.generate_position_summary(position, price)
        
        # Lưu kết quả
        result = {
            'price': price,
            'profit_pct': summary['current_profit_pct'],
            'trailing_activated': summary['trailing_stop']['activated'],
            'trailing_stop_price': summary['trailing_stop']['stop_price'],
            'should_close': should_close,
            'reason': reason
        }
        
        results.append(result)
        
        logger.info(f"Giá: {price}, Lợi nhuận: {summary['current_profit_pct']:.2f}%, "
                   f"Trailing: {summary['trailing_stop']['stop_price']}")
        
        if should_close:
            logger.info(f"Đóng vị thế: {reason}")
            break
    
    return results


def test_price_reversal_exit():
    """Kiểm tra chốt lời theo đảo chiều giá"""
    logger.info("=== Kiểm tra chốt lời theo đảo chiều giá ===")
    
    # Tạo cache
    data_cache = MockDataCache()
    
    # Tạo cấu hình
    trailing_config = {
        'strategy_type': 'percentage',
        'config': {
            'activation_percent': 1.0,
            'callback_percent': 0.5
        }
    }
    
    profit_config = {
        'time_based': {
            'enabled': False
        },
        'target_profit': {
            'enabled': False
        },
        'indicator_based': {
            'enabled': False
        },
        'price_reversal': {
            'enabled': True,
            'candle_count': 3
        },
        'dynamic_volatility': {
            'enabled': False
        }
    }
    
    # Tạo position manager
    position_manager = PositionManager(trailing_config, profit_config, data_cache)
    
    # Tạo vị thế SHORT
    position = {
        'id': 'test_short_position',
        'symbol': 'ETHUSDT',
        'side': 'SHORT',
        'entry_price': 2300,
        'quantity': 1.0,
        'entry_time': datetime.now()
    }
    
    # Khởi tạo vị thế
    position = position_manager.initialize_position(position)
    
    # Hiện tại ETHUSDT có 3 nến đỏ liên tiếp trong cache, nên vị thế SHORT sẽ được đóng
    current_price = 2150
    
    # Cập nhật vị thế
    position = position_manager.update_position(position, current_price)
    
    # Kiểm tra điều kiện đóng
    should_close, reason = position_manager.check_exit_conditions(position, current_price)
    
    # Hiển thị trạng thái
    summary = position_manager.generate_position_summary(position, current_price)
    
    logger.info(f"Giá: {current_price}, Lợi nhuận: {summary['current_profit_pct']:.2f}%, "
               f"Trailing: {summary['trailing_stop']['stop_price']}")
    
    if should_close:
        logger.info(f"Đóng vị thế: {reason}")
    
    return {
        'price': current_price,
        'profit_pct': summary['current_profit_pct'],
        'should_close': should_close,
        'reason': reason
    }


def test_dynamic_volatility_profit():
    """Kiểm tra chốt lời động theo biến động"""
    logger.info("=== Kiểm tra chốt lời động theo biến động ===")
    
    # Tạo cache
    data_cache = MockDataCache()
    
    # Thiết lập biến động thấp (0.01) cho BNBUSDT, mục tiêu lãi 1.5%
    data_cache.set('market_analysis', 'BNBUSDT_1h_volatility', 0.01)
    
    # Tạo cấu hình
    trailing_config = {
        'strategy_type': 'percentage',
        'config': {
            'activation_percent': 1.0,
            'callback_percent': 0.5
        }
    }
    
    profit_config = {
        'time_based': {
            'enabled': False
        },
        'target_profit': {
            'enabled': False
        },
        'indicator_based': {
            'enabled': False
        },
        'price_reversal': {
            'enabled': False
        },
        'dynamic_volatility': {
            'enabled': True,
            'low_vol_target': 1.5,
            'medium_vol_target': 3.0,
            'high_vol_target': 5.0
        }
    }
    
    # Tạo position manager
    position_manager = PositionManager(trailing_config, profit_config, data_cache)
    
    # Tạo vị thế
    position = {
        'id': 'test_long_position',
        'symbol': 'BNBUSDT',
        'side': 'LONG',
        'entry_price': 300,
        'quantity': 1.0,
        'entry_time': datetime.now()
    }
    
    # Khởi tạo vị thế
    position = position_manager.initialize_position(position)
    
    # Mô phỏng cập nhật giá
    prices = [
        302,    # +0.67%
        304,    # +1.33%
        304.5,  # +1.5% (đạt mục tiêu biến động thấp)
        305,    # +1.67%
        306     # +2.0%
    ]
    
    results = []
    
    for price in prices:
        # Cập nhật vị thế
        position = position_manager.update_position(position, price)
        
        # Kiểm tra điều kiện đóng
        should_close, reason = position_manager.check_exit_conditions(position, price)
        
        # Hiển thị trạng thái
        summary = position_manager.generate_position_summary(position, price)
        
        # Lưu kết quả
        result = {
            'price': price,
            'profit_pct': summary['current_profit_pct'],
            'trailing_activated': summary['trailing_stop']['activated'],
            'trailing_stop_price': summary['trailing_stop']['stop_price'],
            'should_close': should_close,
            'reason': reason
        }
        
        results.append(result)
        
        logger.info(f"Giá: {price}, Lợi nhuận: {summary['current_profit_pct']:.2f}%, "
                   f"Trailing: {summary['trailing_stop']['stop_price']}")
        
        if should_close:
            logger.info(f"Đóng vị thế: {reason}")
            break
    
    return results


def test_indicator_based_profit():
    """Kiểm tra chốt lời dựa trên chỉ báo kỹ thuật"""
    logger.info("=== Kiểm tra chốt lời dựa trên chỉ báo kỹ thuật ===")
    
    # Tạo cache
    data_cache = MockDataCache()
    
    # Thiết lập RSI cao (72) cho ETHUSDT
    data_cache.set('indicators', 'ETHUSDT_1h_rsi', 72.0)
    
    # Tạo cấu hình
    trailing_config = {
        'strategy_type': 'percentage',
        'config': {
            'activation_percent': 1.0,
            'callback_percent': 0.5
        }
    }
    
    profit_config = {
        'time_based': {
            'enabled': False
        },
        'target_profit': {
            'enabled': False
        },
        'indicator_based': {
            'enabled': True,
            'rsi_overbought': 70.0,
            'rsi_oversold': 30.0
        },
        'price_reversal': {
            'enabled': False
        },
        'dynamic_volatility': {
            'enabled': False
        }
    }
    
    # Tạo position manager
    position_manager = PositionManager(trailing_config, profit_config, data_cache)
    
    # Tạo vị thế LONG
    position = {
        'id': 'test_long_position',
        'symbol': 'ETHUSDT',
        'side': 'LONG',
        'entry_price': 2100,
        'quantity': 1.0,
        'entry_time': datetime.now()
    }
    
    # Khởi tạo vị thế
    position = position_manager.initialize_position(position)
    
    # Cập nhật vị thế với giá hiện tại
    current_price = 2200
    
    position = position_manager.update_position(position, current_price)
    
    # Kiểm tra điều kiện đóng
    should_close, reason = position_manager.check_exit_conditions(position, current_price)
    
    # Hiển thị trạng thái
    summary = position_manager.generate_position_summary(position, current_price)
    
    logger.info(f"Giá: {current_price}, Lợi nhuận: {summary['current_profit_pct']:.2f}%, "
               f"Trailing: {summary['trailing_stop']['stop_price']}")
    
    if should_close:
        logger.info(f"Đóng vị thế: {reason}")
    
    return {
        'price': current_price,
        'profit_pct': summary['current_profit_pct'],
        'should_close': should_close,
        'reason': reason
    }


def test_time_based_profit():
    """Kiểm tra chốt lời theo thời gian"""
    logger.info("=== Kiểm tra chốt lời theo thời gian ===")
    
    # Tạo cache
    data_cache = MockDataCache()
    
    # Tạo cấu hình
    trailing_config = {
        'strategy_type': 'percentage',
        'config': {
            'activation_percent': 1.0,
            'callback_percent': 0.5
        }
    }
    
    profit_config = {
        'time_based': {
            'enabled': True,
            'max_hold_time': 24  # 24 giờ
        },
        'target_profit': {
            'enabled': False
        },
        'indicator_based': {
            'enabled': False
        },
        'price_reversal': {
            'enabled': False
        },
        'dynamic_volatility': {
            'enabled': False
        }
    }
    
    # Tạo position manager
    position_manager = PositionManager(trailing_config, profit_config, data_cache)
    
    # Tạo vị thế với thời gian mở 25 giờ trước
    position = {
        'id': 'test_long_position',
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry_price': 50000,
        'quantity': 0.1,
        'entry_time': datetime.now() - timedelta(hours=25)
    }
    
    # Khởi tạo vị thế
    position = position_manager.initialize_position(position)
    
    # Cập nhật vị thế với giá hiện tại
    current_price = 50500
    
    position = position_manager.update_position(position, current_price)
    
    # Kiểm tra điều kiện đóng
    should_close, reason = position_manager.check_exit_conditions(position, current_price)
    
    # Hiển thị trạng thái
    summary = position_manager.generate_position_summary(position, current_price)
    
    logger.info(f"Giá: {current_price}, Lợi nhuận: {summary['current_profit_pct']:.2f}%, "
               f"Thời gian giữ: {summary['hold_duration_hours']:.2f} giờ")
    
    if should_close:
        logger.info(f"Đóng vị thế: {reason}")
    
    return {
        'price': current_price,
        'profit_pct': summary['current_profit_pct'],
        'hold_duration': summary['hold_duration_hours'],
        'should_close': should_close,
        'reason': reason
    }


def main():
    """Hàm chính để chạy tất cả các bài kiểm tra"""
    logger.info("=== Bắt đầu kiểm tra Position Manager ===")
    
    results = {}
    
    # Chạy các bài kiểm tra
    try:
        results['percentage_trailing_stop_with_profit_target'] = test_percentage_trailing_stop_with_profit_target()
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra Percentage Trailing Stop với Profit Target: {str(e)}")
    
    try:
        results['price_reversal_exit'] = test_price_reversal_exit()
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra Price Reversal Exit: {str(e)}")
    
    try:
        results['dynamic_volatility_profit'] = test_dynamic_volatility_profit()
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra Dynamic Volatility Profit: {str(e)}")
    
    try:
        results['indicator_based_profit'] = test_indicator_based_profit()
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra Indicator Based Profit: {str(e)}")
    
    try:
        results['time_based_profit'] = test_time_based_profit()
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra Time Based Profit: {str(e)}")
    
    # Lưu kết quả
    try:
        with open('test_results/position_manager_test_results.json', 'w') as f:
            json.dump(results, f, indent=4, default=str)
        logger.info("Đã lưu kết quả kiểm tra vào test_results/position_manager_test_results.json")
    except Exception as e:
        logger.error(f"Lỗi khi lưu kết quả kiểm tra: {str(e)}")
    
    logger.info("=== Hoàn thành kiểm tra Position Manager ===")


if __name__ == "__main__":
    main()