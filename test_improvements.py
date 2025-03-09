#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script kiểm tra các cải tiến đã thực hiện

Script này thực hiện kiểm tra tất cả các cải tiến đã thực hiện,
bao gồm BinanceSynchronizer, DataCache, AdvancedTrailingStop,
và EnhancedNotification.
"""

import os
import time
import json
import logging
import datetime
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Union, Optional

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_improvements')

# Import các module đã cải tiến
from binance_api import BinanceAPI
from binance_synchronizer import BinanceSynchronizer
from data_cache import DataCache, ObservableDataCache
from advanced_trailing_stop import AdvancedTrailingStop, PercentageTrailingStop, ATRTrailingStop
from enhanced_notification import EnhancedNotification, TelegramNotifier

def create_sample_data():
    """Tạo dữ liệu mẫu cho các bài test"""
    
    # Dữ liệu vị thế
    positions = {
        "BTCUSDT": {
            "symbol": "BTCUSDT",
            "side": "LONG",
            "entry_price": 60000,
            "quantity": 0.1,
            "leverage": 10,
            "stop_loss": 57000,
            "take_profit": 65000,
            "trailing_activated": False,
            "entry_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "highest_price": 60000,
            "lowest_price": None,
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "ETHUSDT": {
            "symbol": "ETHUSDT",
            "side": "SHORT",
            "entry_price": 3000,
            "quantity": 1.0,
            "leverage": 5,
            "stop_loss": 3150,
            "take_profit": 2700,
            "trailing_activated": False,
            "entry_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "highest_price": None,
            "lowest_price": 3000,
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    }
    
    # Giá hiện tại
    current_prices = {
        "BTCUSDT": 61500,  # Tăng 2.5%
        "ETHUSDT": 2850    # Giảm 5%
    }
    
    # Dữ liệu thị trường
    market_data = {
        "BTCUSDT": {
            "trend": "uptrend",
            "volatility": "medium",
            "rsi": 65,
            "support_levels": [59000, 58000, 57000],
            "resistance_levels": [62000, 63000, 65000]
        },
        "ETHUSDT": {
            "trend": "downtrend",
            "volatility": "high",
            "rsi": 35,
            "support_levels": [2800, 2700, 2600],
            "resistance_levels": [3050, 3100, 3200]
        }
    }
    
    return positions, current_prices, market_data

def test_binance_synchronizer():
    """Kiểm tra BinanceSynchronizer"""
    logger.info("=== Kiểm tra BinanceSynchronizer ===")
    
    # Khởi tạo API và synchronizer
    api = BinanceAPI()
    sync = BinanceSynchronizer(api)
    
    # Tải dữ liệu vị thế cục bộ
    positions = sync.load_local_positions()
    logger.info(f"Đã tải {len(positions)} vị thế từ file cục bộ")
    
    # Kiểm tra tính toàn vẹn dữ liệu
    integrity_result = sync.check_local_positions_integrity()
    logger.info(f"Kiểm tra tính toàn vẹn: {integrity_result['valid_positions']} hợp lệ, "
             f"{integrity_result['invalid_positions']} không hợp lệ")
    
    # Thử đồng bộ với Binance
    logger.info("Đang đồng bộ với Binance...")
    sync_result = sync.full_sync_with_binance()
    
    if sync_result['success']:
        logger.info(f"Đồng bộ thành công: {sync_result['positions_synced']} vị thế, "
                 f"{sync_result['stop_loss_synced']} SL, {sync_result['take_profit_synced']} TP")
    else:
        logger.warning(f"Đồng bộ không thành công: {', '.join(sync_result['errors'])}")
    
    # Kiểm tra trạng thái đồng bộ
    sync_status = sync.get_sync_status()
    logger.info(f"Trạng thái đồng bộ: {sync_status['positions_count']} vị thế, "
             f"SL đã đồng bộ: {sync_status['sl_synced']}, TP đã đồng bộ: {sync_status['tp_synced']}")
    
    return sync_result['success']

def test_data_cache():
    """Kiểm tra DataCache và ObservableDataCache"""
    logger.info("=== Kiểm tra DataCache ===")
    
    # Khởi tạo cache
    cache = DataCache(enable_disk_cache=True)
    
    # Lưu một số dữ liệu
    positions, current_prices, market_data = create_sample_data()
    
    cache.set('market_data', 'BTCUSDT_1h', market_data['BTCUSDT'])
    cache.set('market_data', 'ETHUSDT_1h', market_data['ETHUSDT'])
    cache.set('positions', 'BTCUSDT', positions['BTCUSDT'])
    cache.set('positions', 'ETHUSDT', positions['ETHUSDT'])
    
    # Lấy dữ liệu và kiểm tra
    btc_market = cache.get('market_data', 'BTCUSDT_1h')
    btc_position = cache.get('positions', 'BTCUSDT')
    
    logger.info(f"BTCUSDT market trend: {btc_market['trend']}")
    logger.info(f"BTCUSDT position entry price: {btc_position['entry_price']}")
    
    # Kiểm tra tính hợp lệ
    valid = cache.is_valid('market_data', 'BTCUSDT_1h')
    logger.info(f"BTCUSDT market data valid: {valid}")
    
    # Lấy thống kê
    stats = cache.get_stats()
    logger.info(f"Cache stats: {stats['total_items']} items")
    
    # Kiểm tra ObservableDataCache
    logger.info("\n=== Kiểm tra ObservableDataCache ===")
    
    # Callback khi dữ liệu thay đổi
    def on_data_change(category, key, data):
        logger.info(f"Data change: {category}/{key}")
    
    # Khởi tạo observable cache
    obs_cache = ObservableDataCache()
    
    # Đăng ký observer
    obs_cache.register_observer('market_data', 'BTCUSDT_1h', on_data_change)
    
    # Cập nhật dữ liệu
    logger.info("Cập nhật dữ liệu BTCUSDT market (sẽ trigger observer)...")
    market_data['BTCUSDT']['rsi'] = 70
    obs_cache.set('market_data', 'BTCUSDT_1h', market_data['BTCUSDT'])
    
    return True

def test_advanced_trailing_stop():
    """Kiểm tra AdvancedTrailingStop"""
    logger.info("=== Kiểm tra AdvancedTrailingStop ===")
    
    # Tạo dữ liệu vị thế
    positions, current_prices, _ = create_sample_data()
    position_long = positions['BTCUSDT']
    position_short = positions['ETHUSDT']
    
    # Test PercentageTrailingStop
    logger.info("\n--- Test PercentageTrailingStop ---")
    ts_percentage = AdvancedTrailingStop("percentage", None, {
        "activation_percent": 2.0,  # Kích hoạt khi lợi nhuận đạt 2%
        "callback_percent": 0.8     # Callback 0.8% từ mức cao/thấp nhất
    })
    
    # Khởi tạo vị thế
    position_long = ts_percentage.initialize_position(position_long)
    logger.info(f"LONG position initialized: {position_long['trailing_type']}")
    
    # Mô phỏng tăng giá
    prices = [
        60500,  # +0.83%
        61000,  # +1.67%
        61500,  # +2.50% (kích hoạt trailing stop)
        62000,  # +3.33%
        62500,  # +4.17%
        62000,  # -0.8% từ cao nhất
        61500   # -1.6% từ cao nhất (sẽ dừng trailing stop)
    ]
    
    for i, price in enumerate(prices):
        # Cập nhật vị thế
        position_long = ts_percentage.update_trailing_stop(position_long, price)
        should_close, reason = ts_percentage.check_stop_condition(position_long, price)
        
        logger.info(f"LONG - Price: {price}")
        logger.info(f"  Trailing activated: {position_long['trailing_activated']}")
        logger.info(f"  Trailing stop: {position_long.get('trailing_stop')}")
        logger.info(f"  Close position: {should_close}, Reason: {reason}")
        
        if should_close:
            logger.info(f"  Position would be closed at {price}")
            break
    
    # Test ATRTrailingStop
    logger.info("\n--- Test ATRTrailingStop ---")
    
    # Tạo cache cho ATR
    cache = DataCache()
    # Lưu giá trị ATR giả lập vào cache
    cache.set('indicators', 'ETHUSDT_1h_atr_14', {'value': 150})  # ~5% của giá entry
    
    ts_atr = AdvancedTrailingStop("atr", cache, {
        "atr_multiplier": 2.0,  # Trailing stop = mức thấp nhất + 2*ATR
        "atr_period": 14
    })
    
    # Khởi tạo vị thế SHORT
    position_short = ts_atr.initialize_position(position_short)
    logger.info(f"SHORT position initialized: {position_short['trailing_type']}")
    
    # Mô phỏng giảm giá
    prices = [
        2950,  # -1.67%
        2900,  # -3.33%
        2850,  # -5.00%
        2800,  # -6.67%
        2750,  # -8.33%
        2800,  # +1.82% từ thấp nhất (không đủ để dừng)
        2850,  # +3.64% từ thấp nhất (không đủ để dừng)
        2900,  # +5.45% từ thấp nhất (đủ để dừng với ATR = 150)
    ]
    
    for i, price in enumerate(prices):
        # Cập nhật vị thế
        position_short = ts_atr.update_trailing_stop(position_short, price)
        should_close, reason = ts_atr.check_stop_condition(position_short, price)
        
        logger.info(f"SHORT - Price: {price}")
        logger.info(f"  Trailing activated: {position_short['trailing_activated']}")
        logger.info(f"  Trailing stop: {position_short.get('trailing_stop')}")
        logger.info(f"  Close position: {should_close}, Reason: {reason}")
        
        if should_close:
            logger.info(f"  Position would be closed at {price}")
            break
    
    # Thử đổi chiến lược
    logger.info("\nThay đổi chiến lược trailing stop sang 'step'")
    step_config = {
        "profit_steps": [1.0, 2.0, 3.0, 5.0],
        "callback_steps": [0.5, 0.7, 0.9, 1.1]
    }
    
    if ts_percentage.change_strategy("step", step_config):
        logger.info("Đổi chiến lược thành công")
        logger.info(f"Chiến lược mới: {ts_percentage.get_strategy_name()}")
    else:
        logger.info("Đổi chiến lược thất bại")
    
    return True

def test_enhanced_notification():
    """Kiểm tra EnhancedNotification"""
    logger.info("=== Kiểm tra EnhancedNotification ===")
    
    # Khởi tạo hệ thống thông báo
    notification = EnhancedNotification()
    
    # Kiểm tra các kênh đã cấu hình
    logger.info(f"Các kênh thông báo: {list(notification.channels.keys())}")
    
    # Cố gắng tìm một kênh thông báo khả dụng
    if 'telegram' not in notification.channels:
        # Nếu không có sẵn, tạo một kênh giả lập
        logger.info("Không tìm thấy kênh thông báo Telegram, tạo kênh giả lập...")
        
        class DummyTelegramNotifier(TelegramNotifier):
            def send(self, message, subject=None, data=None):
                logger.info(f"[DUMMY TELEGRAM] Gửi thông báo: {subject}")
                logger.info(f"[DUMMY TELEGRAM] Nội dung: {message[:100]}...")
                return True
        
        notification.add_channel(DummyTelegramNotifier())
    
    # Tạo dữ liệu vị thế
    positions, current_prices, _ = create_sample_data()
    position_data = positions['BTCUSDT']
    position_data['current_price'] = current_prices['BTCUSDT']
    
    # Tính profit_percent
    profit_percent = ((current_prices['BTCUSDT'] - position_data['entry_price']) / 
                    position_data['entry_price'] * 100 * position_data['leverage'])
    position_data['profit_percent'] = profit_percent
    
    # Thử gửi thông báo về vị thế mới
    logger.info("\nGửi thông báo về vị thế mới:")
    results = notification.notify_new_position(position_data)
    logger.info(f"Kết quả gửi: {results}")
    
    # Tạo dữ liệu vị thế đã đóng
    position_closed_data = position_data.copy()
    position_closed_data.update({
        "exit_price": 63000,
        "exit_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "profit_loss": (63000 - 60000) * 0.1 * 10,  # (exit - entry) * quantity * leverage
        "profit_percent": 50.0,  # (63000 - 60000) / 60000 * 100 * 10
        "close_reason": "Take Profit"
    })
    
    # Thử gửi thông báo về vị thế đã đóng
    logger.info("\nGửi thông báo về vị thế đã đóng:")
    results = notification.notify_position_closed(position_closed_data)
    logger.info(f"Kết quả gửi: {results}")
    
    # Tạo dữ liệu trailing stop
    trailing_data = position_data.copy()
    trailing_data.update({
        "trailing_stop": 60500,
        "trailing_activated": True
    })
    
    # Thử gửi thông báo về trailing stop đã kích hoạt
    logger.info("\nGửi thông báo về trailing stop đã kích hoạt:")
    results = notification.notify_trailing_stop(trailing_data)
    logger.info(f"Kết quả gửi: {results}")
    
    return True

def test_integrated_improvements():
    """Kiểm tra tất cả các cải tiến tích hợp lại với nhau"""
    logger.info("=== Kiểm tra tích hợp tất cả cải tiến ===")
    
    # Khởi tạo các thành phần
    cache = ObservableDataCache()
    api = BinanceAPI()
    sync = BinanceSynchronizer(api)
    notification = EnhancedNotification()
    
    # Tạo trailing stop manager với cache
    ts_manager = AdvancedTrailingStop("percentage", cache, {
        "activation_percent": 2.0,
        "callback_percent": 0.8
    })
    
    # Tạo dummy Telegram để ghi log
    class DummyTelegramNotifier(TelegramNotifier):
        def send(self, message, subject=None, data=None):
            logger.info(f"[DUMMY TELEGRAM] Gửi thông báo: {subject}")
            return True
    
    notification.add_channel(DummyTelegramNotifier())
    
    # Tạo dữ liệu vị thế
    positions, current_prices, market_data = create_sample_data()
    
    # Lưu dữ liệu vào cache
    for symbol, data in market_data.items():
        cache.set('market_data', f'{symbol}_1h', data)
    
    # Callback khi dữ liệu thị trường thay đổi
    def on_market_data_change(category, key, data):
        logger.info(f"Market data changed: {key}")
        # Cập nhật trailing stop nếu cần
        symbol = key.split('_')[0]
        if symbol in positions:
            update_position_trailing_stop(symbol)
    
    # Đăng ký observer cho dữ liệu thị trường
    for symbol in positions.keys():
        cache.register_observer('market_data', f'{symbol}_1h', on_market_data_change)
    
    # Hàm cập nhật trailing stop
    def update_position_trailing_stop(symbol):
        position = positions[symbol]
        current_price = current_prices[symbol]
        
        # Khởi tạo vị thế nếu chưa
        if 'trailing_type' not in position:
            position = ts_manager.initialize_position(position)
            positions[symbol] = position
            logger.info(f"Đã khởi tạo trailing stop cho {symbol}")
        
        # Cập nhật trailing stop
        updated_position = ts_manager.update_trailing_stop(position, current_price)
        should_close, reason = ts_manager.check_stop_condition(updated_position, current_price)
        
        # Cập nhật lại vị thế
        positions[symbol] = updated_position
        
        # Thông báo nếu trailing stop đã kích hoạt
        if updated_position['trailing_activated'] and not position.get('notification_sent', False):
            notification.notify_trailing_stop(updated_position)
            updated_position['notification_sent'] = True
            logger.info(f"Đã gửi thông báo trailing stop kích hoạt cho {symbol}")
        
        # Nếu nên đóng vị thế
        if should_close:
            logger.info(f"Nên đóng vị thế {symbol} vì: {reason}")
            
            # Đồng bộ với Binance (mô phỏng)
            logger.info(f"Đóng vị thế {symbol} trên Binance...")
            
            # Đánh dấu đã đóng
            position_closed = updated_position.copy()
            position_closed.update({
                "exit_price": current_price,
                "exit_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "profit_loss": calculate_profit(position_closed, current_price),
                "profit_percent": calculate_profit_percent(position_closed, current_price),
                "close_reason": reason
            })
            
            # Gửi thông báo
            notification.notify_position_closed(position_closed)
            
            # Xóa khỏi danh sách vị thế đang mở
            del positions[symbol]
            logger.info(f"Đã đóng vị thế {symbol}")
    
    # Hàm tính lợi nhuận
    def calculate_profit(position, current_price):
        entry_price = position['entry_price']
        quantity = position['quantity']
        leverage = position['leverage']
        side = position['side']
        
        if side == "LONG":
            return (current_price - entry_price) * quantity * leverage
        else:  # SHORT
            return (entry_price - current_price) * quantity * leverage
    
    # Hàm tính phần trăm lợi nhuận
    def calculate_profit_percent(position, current_price):
        entry_price = position['entry_price']
        leverage = position['leverage']
        side = position['side']
        
        if side == "LONG":
            return ((current_price - entry_price) / entry_price) * 100 * leverage
        else:  # SHORT
            return ((entry_price - current_price) / entry_price) * 100 * leverage
    
    # Mô phỏng cập nhật giá
    logger.info("\nMô phỏng cập nhật giá và trailing stop:")
    
    # BTCUSDT tăng giá
    btc_prices = [60500, 61000, 61500, 62000, 62500, 62000, 61500]
    # ETHUSDT giảm giá
    eth_prices = [2950, 2900, 2850, 2800, 2750, 2800, 2850]
    
    for i in range(len(btc_prices)):
        logger.info(f"\n--- Cập nhật giá #{i+1} ---")
        
        # Cập nhật giá hiện tại
        current_prices['BTCUSDT'] = btc_prices[i]
        current_prices['ETHUSDT'] = eth_prices[i]
        
        # Xử lý từng vị thế
        symbols_to_process = list(positions.keys())  # Tạo bản sao để tránh lỗi khi xóa
        for symbol in symbols_to_process:
            update_position_trailing_stop(symbol)
        
        # Mô phỏng đồng bộ với Binance
        if i % 3 == 0:  # Định kỳ đồng bộ
            logger.info("\nĐồng bộ với Binance...")
            # Mô phỏng đồng bộ (thực tế sẽ gọi sync.full_sync_with_binance())
            logger.info(f"Đã đồng bộ với Binance: {len(positions)} vị thế còn lại")
        
        # Tạm dừng 1 giây để dễ theo dõi
        time.sleep(1)
    
    # Kiểm tra kết quả cuối cùng
    logger.info(f"\nKết quả cuối cùng: {len(positions)} vị thế còn mở")
    for symbol, position in positions.items():
        logger.info(f"Vị thế {symbol}: Trailing Stop = {position.get('trailing_stop')}, "
                 f"Đã kích hoạt: {position.get('trailing_activated', False)}")
    
    # Kiểm tra dữ liệu đã lưu trong cache
    logger.info("\nKiểm tra dữ liệu trong cache:")
    for symbol in ['BTCUSDT', 'ETHUSDT']:
        market_data = cache.get('market_data', f'{symbol}_1h')
        if market_data:
            logger.info(f"{symbol} market trend: {market_data['trend']}")
    
    return True

def main():
    """Hàm chính để test tất cả các cải tiến"""
    logger.info("=== BẮT ĐẦU KIỂM TRA CÁC CẢI TIẾN ===\n")
    
    results = {}
    
    try:
        # Test BinanceSynchronizer
        results['binance_synchronizer'] = test_binance_synchronizer()
    except Exception as e:
        logger.error(f"Lỗi khi test BinanceSynchronizer: {str(e)}")
        results['binance_synchronizer'] = False
    
    try:
        # Test DataCache
        results['data_cache'] = test_data_cache()
    except Exception as e:
        logger.error(f"Lỗi khi test DataCache: {str(e)}")
        results['data_cache'] = False
    
    try:
        # Test AdvancedTrailingStop
        results['advanced_trailing_stop'] = test_advanced_trailing_stop()
    except Exception as e:
        logger.error(f"Lỗi khi test AdvancedTrailingStop: {str(e)}")
        results['advanced_trailing_stop'] = False
    
    try:
        # Test EnhancedNotification
        results['enhanced_notification'] = test_enhanced_notification()
    except Exception as e:
        logger.error(f"Lỗi khi test EnhancedNotification: {str(e)}")
        results['enhanced_notification'] = False
    
    try:
        # Test tích hợp
        results['integrated_improvements'] = test_integrated_improvements()
    except Exception as e:
        logger.error(f"Lỗi khi test tích hợp: {str(e)}")
        results['integrated_improvements'] = False
    
    # Tổng kết kết quả
    logger.info("\n=== KẾT QUẢ KIỂM TRA ===")
    for name, result in results.items():
        status = "✅ THÀNH CÔNG" if result else "❌ THẤT BẠI"
        logger.info(f"{name}: {status}")
    
    all_passed = all(results.values())
    if all_passed:
        logger.info("\n✅ TẤT CẢ CÁC BÀI KIỂM TRA ĐỀU THÀNH CÔNG!")
    else:
        logger.warning("\n⚠️ MỘT SỐ BÀI KIỂM TRA THẤT BẠI!")
    
    return all_passed


if __name__ == "__main__":
    main()