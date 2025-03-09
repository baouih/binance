#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tự động thiết lập stop loss và take profit cho các vị thế BTC đang mở

Script này kiểm tra các vị thế BTC đang mở và tự động thiết lập stop loss (SL) và
take profit (TP) cho các vị thế chưa có, mục đích là đảm bảo BTC luôn có SL/TP
đủ an toàn.
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('auto_btc_sltp')

# Thêm thư mục gốc vào sys.path để import các module
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from binance_api import BinanceAPI
from profit_manager import ProfitManager
from data_cache import DataCache

def setup_btc_sltp(api_key: str = None, api_secret: str = None, testnet: bool = True):
    """
    Thiết lập SL/TP cho các vị thế BTC đang mở
    
    Args:
        api_key (str, optional): API key Binance
        api_secret (str, optional): API secret Binance
        testnet (bool): Sử dụng testnet hay không
    """
    try:
        # Khởi tạo các đối tượng cần thiết
        binance_api = BinanceAPI(api_key=api_key, api_secret=api_secret, testnet=testnet)
        data_cache = DataCache()
        
        # Tải cấu hình profit manager
        try:
            with open('configs/profit_manager_config.json', 'r') as f:
                profit_config = json.load(f)
        except Exception as e:
            logger.warning(f"Không thể tải cấu hình profit manager: {str(e)}")
            profit_config = {}
            
        # Khởi tạo profit manager
        profit_manager = ProfitManager(config=profit_config, data_cache=data_cache)
        
        # Lấy danh sách vị thế đang mở
        positions = binance_api.futures_get_position()
        
        # Lọc ra chỉ các vị thế BTC
        btc_positions = [p for p in positions if p.get('symbol') == 'BTCUSDT' and abs(float(p.get('positionAmt', 0))) > 0]
        
        if not btc_positions:
            logger.info("Không có vị thế BTC nào đang mở")
            return
            
        logger.info(f"Đã tìm thấy {len(btc_positions)} vị thế BTC đang mở")
        
        # Kiểm tra và thiết lập SL/TP cho từng vị thế BTC
        for position in btc_positions:
            symbol = 'BTCUSDT'
            side = 'LONG' if float(position.get('positionAmt', 0)) > 0 else 'SHORT'
            entry_price = float(position.get('entryPrice', 0))
            leverage = int(position.get('leverage', 1))
            position_amt = float(position.get('positionAmt', 0))
            
            logger.info(f"Kiểm tra vị thế BTC {side}: Entry price={entry_price}, Lượng={position_amt}")
            
            # Kiểm tra nếu đã có SL/TP
            existing_orders = binance_api.get_open_orders(symbol)
            has_sl = any(order.get('type') == 'STOP_MARKET' for order in existing_orders)
            has_tp = any(order.get('type') == 'TAKE_PROFIT_MARKET' for order in existing_orders)
            
            # Lấy giá hiện tại
            current_price = float(binance_api.get_symbol_ticker(symbol).get('price', 0))
            
            # Lấy giá trị ATR nếu có
            try:
                klines = binance_api.get_klines(symbol, '1h', limit=15)
                if not klines or len(klines) < 14:
                    atr_value = None
                else:
                    # Chuyển đổi dữ liệu
                    highs = [float(kline[2]) for kline in klines]
                    lows = [float(kline[3]) for kline in klines]
                    closes = [float(kline[4]) for kline in klines]
                    
                    # Tính True Range
                    tr_values = []
                    for i in range(1, len(closes)):
                        high = highs[i]
                        low = lows[i]
                        prev_close = closes[i-1]
                        
                        tr1 = high - low
                        tr2 = abs(high - prev_close)
                        tr3 = abs(low - prev_close)
                        
                        tr = max(tr1, tr2, tr3)
                        tr_values.append(tr)
                    
                    # Tính ATR
                    atr_value = sum(tr_values) / len(tr_values)
            except Exception as e:
                logger.warning(f"Không thể lấy giá trị ATR cho BTC: {str(e)}")
                atr_value = None
            
            # Thiết lập SL nếu chưa có
            if not has_sl:
                # Thiết lập giới hạn % tối đa cho SL
                max_sl_percent = 5.0  # Tối đa 5% từ giá entry
                
                # Tính toán SL phù hợp
                if side == 'LONG':
                    # Sử dụng % cố định, có áp dụng đòn bẩy
                    sl_percent = 2.0  # Mặc định 2%
                    sl_percent_adjusted = min(sl_percent, max_sl_percent)
                    sl_price = entry_price * (1 - sl_percent_adjusted / 100)
                    
                    # Giới hạn SL không quá xa giá hiện tại
                    min_sl_price = current_price * 0.9  # Không thấp hơn 90% giá hiện tại
                    sl_price = max(sl_price, min_sl_price)
                else:
                    # Sử dụng % cố định, có áp dụng đòn bẩy
                    sl_percent = 2.0  # Mặc định 2%
                    sl_percent_adjusted = min(sl_percent, max_sl_percent)
                    sl_price = entry_price * (1 + sl_percent_adjusted / 100)
                    
                    # Giới hạn SL không quá xa giá hiện tại
                    max_sl_price = current_price * 1.1  # Không cao hơn 110% giá hiện tại
                    sl_price = min(sl_price, max_sl_price)
                
                # Đảm bảo SL không quá gần giá hiện tại
                min_distance = current_price * 0.005  # Ít nhất 0.5% từ giá hiện tại
                if side == 'LONG' and sl_price > current_price - min_distance:
                    sl_price = current_price - min_distance
                elif side == 'SHORT' and sl_price < current_price + min_distance:
                    sl_price = current_price + min_distance
                    
                # Làm tròn giá
                sl_price = round(sl_price, 1)
                
                # Log chi tiết về cách tính SL
                logger.info(f"Tính toán SL cho BTC {side}: Entry={entry_price}, Current={current_price}, SL={sl_price}")
                
                if sl_price > 0:
                    try:
                        result = binance_api.futures_set_stop_loss(symbol, side, sl_price)
                        if 'error' in result:
                            logger.error(f"Lỗi khi đặt SL cho BTC: {result.get('error')}")
                        else:
                            logger.info(f"Đã đặt SL cho BTC {side} tại giá {sl_price}")
                    except Exception as e:
                        logger.error(f"Lỗi khi đặt SL cho BTC: {str(e)}")
                else:
                    logger.warning(f"Không thể tính giá SL hợp lệ cho BTC")
            else:
                logger.info(f"Vị thế BTC {side} đã có SL")
            
            # Thiết lập TP nếu chưa có
            if not has_tp:
                # Lấy target profit từ cấu hình cho BTC
                small_account_settings = profit_config.get('small_account_settings', {})
                if small_account_settings.get('enabled', False):
                    target_profit = small_account_settings.get('btc_profit_target', 1.5)
                else:
                    target_profit = profit_config.get('target_profit', {}).get('profit_target', 2.0)
                
                # Điều chỉnh target dựa trên đòn bẩy
                effective_target = target_profit / leverage if leverage > 1 else target_profit
                
                # Thiết lập giới hạn % tối đa cho TP
                max_tp_percent = 10.0  # Tối đa 10% từ giá entry
                
                # Tính toán TP phù hợp
                if side == 'LONG':
                    # Sử dụng % mục tiêu
                    tp_percent = effective_target  # Từ cấu hình
                    tp_percent_adjusted = min(tp_percent, max_tp_percent)
                    tp_price = entry_price * (1 + tp_percent_adjusted / 100)
                    
                    # Giới hạn TP không quá xa giá hiện tại
                    max_tp_price = current_price * 1.15  # Không cao hơn 115% giá hiện tại
                    tp_price = min(tp_price, max_tp_price)
                else:
                    # Sử dụng % mục tiêu
                    tp_percent = effective_target  # Từ cấu hình
                    tp_percent_adjusted = min(tp_percent, max_tp_percent)
                    tp_price = entry_price * (1 - tp_percent_adjusted / 100)
                    
                    # Giới hạn TP không quá xa giá hiện tại
                    min_tp_price = current_price * 0.85  # Không thấp hơn 85% giá hiện tại
                    tp_price = max(tp_price, min_tp_price)
                
                # Đảm bảo TP không quá gần giá hiện tại
                min_distance = current_price * 0.01  # Ít nhất 1% từ giá hiện tại
                if side == 'LONG' and tp_price < current_price + min_distance:
                    tp_price = current_price + min_distance
                elif side == 'SHORT' and tp_price > current_price - min_distance:
                    tp_price = current_price - min_distance
                    
                # Làm tròn giá
                tp_price = round(tp_price, 1)
                
                # Log chi tiết về cách tính TP
                logger.info(f"Tính toán TP cho BTC {side}: Entry={entry_price}, Current={current_price}, TP={tp_price}")
                
                if tp_price > 0:
                    try:
                        result = binance_api.futures_set_take_profit(symbol, side, tp_price)
                        if 'error' in result:
                            logger.error(f"Lỗi khi đặt TP cho BTC: {result.get('error')}")
                        else:
                            logger.info(f"Đã đặt TP cho BTC {side} tại giá {tp_price}")
                    except Exception as e:
                        logger.error(f"Lỗi khi đặt TP cho BTC: {str(e)}")
                else:
                    logger.warning(f"Không thể tính giá TP hợp lệ cho BTC")
            else:
                logger.info(f"Vị thế BTC {side} đã có TP")
        
        logger.info("Đã kiểm tra và thiết lập SL/TP cho tất cả vị thế BTC")
        
    except Exception as e:
        logger.error(f"Lỗi trong quá trình thiết lập SL/TP cho BTC: {str(e)}")

def schedule_check(interval_minutes: int = 5, duration_hours: int = 24, testnet: bool = True):
    """
    Lên lịch kiểm tra và thiết lập SL/TP cho BTC định kỳ
    
    Args:
        interval_minutes (int): Khoảng thời gian giữa các lần kiểm tra (phút)
        duration_hours (int): Thời gian chạy tổng cộng (giờ)
        testnet (bool): Sử dụng testnet hay không
    """
    start_time = time.time()
    end_time = start_time + (duration_hours * 60 * 60)
    
    logger.info(f"Bắt đầu lịch trình kiểm tra SL/TP cho BTC mỗi {interval_minutes} phút trong {duration_hours} giờ")
    
    while time.time() < end_time:
        try:
            logger.info("Bắt đầu kiểm tra SL/TP cho BTC")
            setup_btc_sltp(testnet=testnet)
            
            # Chờ đến lần kiểm tra tiếp theo
            logger.info(f"Hoàn thành kiểm tra, chờ {interval_minutes} phút cho lần tiếp theo")
            time.sleep(interval_minutes * 60)
            
        except KeyboardInterrupt:
            logger.info("Nhận lệnh dừng từ người dùng")
            break
        except Exception as e:
            logger.error(f"Lỗi không mong đợi: {str(e)}")
            # Vẫn chờ trước khi thử lại
            logger.info(f"Thử lại sau {interval_minutes} phút")
            time.sleep(interval_minutes * 60)
    
    logger.info("Kết thúc lịch trình kiểm tra SL/TP cho BTC")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Tự động thiết lập SL/TP cho các vị thế BTC đang mở')
    parser.add_argument('--testnet', action='store_true', help='Sử dụng testnet')
    parser.add_argument('--schedule', action='store_true', help='Lên lịch kiểm tra định kỳ')
    parser.add_argument('--interval', type=int, default=5, help='Khoảng thời gian giữa các lần kiểm tra (phút)')
    parser.add_argument('--duration', type=int, default=24, help='Thời gian chạy tổng cộng (giờ)')
    args = parser.parse_args()
    
    if args.schedule:
        schedule_check(args.interval, args.duration, args.testnet)
    else:
        setup_btc_sltp(testnet=args.testnet)

if __name__ == "__main__":
    main()