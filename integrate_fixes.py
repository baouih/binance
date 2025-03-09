#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script tích hợp các bản vá lỗi vào hệ thống giao dịch chính
"""

import os
import sys
import json
import time
import logging
import threading
from binance_api import BinanceAPI
from binance_api_fixes import apply_fixes_to_api
from thread_monitor import monitor_threads, register_thread

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("integrate_fixes.log")
    ]
)
logger = logging.getLogger("integrate_fixes")

# Các symbols giao dịch
TARGET_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT",
    "DOGEUSDT", "MATICUSDT", "LTCUSDT", "DOTUSDT", "XRPUSDT",
    "AVAXUSDT", "LINKUSDT", "ATOMUSDT"
]

def test_account_connection():
    """Kiểm tra kết nối tới tài khoản Binance"""
    logger.info("Kiểm tra kết nối tới tài khoản Binance")
    
    # Tạo instance API chuẩn
    api = BinanceAPI()
    
    # Áp dụng các bản vá
    api = apply_fixes_to_api(api)
    
    # Kiểm tra số dư
    try:
        account = api.get_futures_account()
        if account and 'totalWalletBalance' in account:
            balance = float(account['totalWalletBalance'])
            logger.info(f"Kết nối thành công, số dư ví: {balance} USDT")
            return True
        else:
            logger.error(f"Không lấy được thông tin tài khoản: {account}")
            return False
    except Exception as e:
        logger.error(f"Lỗi kết nối: {str(e)}")
        return False

def check_position_mode(api):
    """Kiểm tra và cập nhật chế độ position mode"""
    logger.info("Kiểm tra chế độ position mode")
    
    # Kiểm tra hedge mode
    hedge_status = api.hedge_mode
    logger.info(f"Tài khoản đang ở chế độ hedge mode: {hedge_status}")
    
    if not hedge_status:
        # Nếu chưa ở hedge mode, hỏi người dùng có muốn chuyển không
        logger.warning("Tài khoản chưa ở chế độ hedge mode.")
        logger.warning("Chế độ hedge mode cho phép mở đồng thời cả vị thế Long và Short trên cùng một symbol")
        
        # Trong tình huống thực tế, nên hỏi người dùng trước khi thay đổi
        logger.warning("Để đảm bảo hệ thống hoạt động đúng, KHÔNG tự động chuyển sang chế độ hedge mode")
        return False
    
    return True

def check_all_symbols(api):
    """Kiểm tra thông tin của tất cả các symbols mục tiêu"""
    logger.info(f"Kiểm tra thông tin {len(TARGET_SYMBOLS)} symbols mục tiêu")
    
    # Lấy thông tin giá hiện tại
    prices = {}
    try:
        # Sử dụng futures_ticker_price để lấy giá tất cả các symbols
        ticker_data = api.futures_ticker_price()
        if isinstance(ticker_data, list):
            for item in ticker_data:
                if 'symbol' in item and 'price' in item:
                    prices[item['symbol']] = float(item['price'])
        else:
            logger.error(f"Không nhận được dữ liệu ticker theo định dạng mong đợi: {ticker_data}")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi lấy thông tin giá: {str(e)}")
        return False
    
    # Kiểm tra từng symbol
    valid_symbols = 0
    min_notional_values = {}
    
    for symbol in TARGET_SYMBOLS:
        if symbol in prices:
            price = prices[symbol]
            
            # Tính số lượng tối thiểu
            quantity = api.calculate_min_quantity(symbol, 100)
            if quantity:
                notional = quantity * price
                min_notional_values[symbol] = notional
                logger.info(f"{symbol}: Giá = {price}, Số lượng tối thiểu = {quantity}, Giá trị = {notional} USDT")
                valid_symbols += 1
            else:
                logger.warning(f"{symbol}: Không tính được số lượng tối thiểu")
        else:
            logger.warning(f"{symbol}: Không tìm thấy thông tin giá")
    
    logger.info(f"Đã xác nhận {valid_symbols}/{len(TARGET_SYMBOLS)} symbols hợp lệ")
    
    # Lưu thông tin số lượng tối thiểu cho các lần sử dụng sau
    if min_notional_values:
        with open("min_notional_values.json", "w") as f:
            json.dump(min_notional_values, f, indent=2)
            logger.info("Đã lưu thông tin notional value vào min_notional_values.json")
    
    return valid_symbols > 0

def test_create_order(api, symbol="BTCUSDT", usd_value=100):
    """Thử tạo lệnh market và TP/SL"""
    logger.info(f"Thử tạo lệnh market với giá trị {usd_value} USD cho {symbol}")
    
    # Lấy giá hiện tại từ futures_ticker_price
    ticker_data = api.futures_ticker_price(symbol)
    if isinstance(ticker_data, dict) and 'price' in ticker_data:
        price = float(ticker_data['price'])
    else:
        price = None
            
    if not price:
        logger.error(f"Không lấy được giá của {symbol}")
        return False
    
    logger.info(f"{symbol} giá hiện tại: {price}")
    
    # Tạo lệnh Market BUY
    side = "BUY"
    position_side = "LONG" if api.hedge_mode else None
    
    logger.info(f"Tạo lệnh {side} {symbol} (position_side={position_side}) với giá trị {usd_value} USD")
    order = api.create_order_with_position_side(
        symbol=symbol,
        side=side,
        order_type="MARKET",
        usd_value=usd_value,
        position_side=position_side
    )
    
    if order.get('error'):
        logger.error(f"Lỗi tạo lệnh: {order.get('error')}")
        return False
    
    logger.info(f"Lệnh thành công: {json.dumps(order, indent=2)}")
    
    # Lấy vị thế sau khi tạo lệnh
    time.sleep(1)  # Chờ một chút để vị thế được cập nhật
    
    positions = api.get_futures_position_risk()
    active_pos = None
    
    for pos in positions:
        if pos['symbol'] == symbol and float(pos.get('positionAmt', 0)) > 0:
            active_pos = pos
            break
    
    if not active_pos:
        logger.warning(f"Không tìm thấy vị thế active nào cho {symbol}")
        return False
    
    position_side = active_pos['positionSide']
    entry_price = float(active_pos['entryPrice'])
    pos_qty = float(active_pos['positionAmt'])
    
    logger.info(f"Vị thế hiện tại: {symbol} ({position_side}): {pos_qty} @ {entry_price}")
    
    # Tính toán giá TP/SL
    tp_price = round(entry_price * 1.03, 1)  # +3%
    sl_price = round(entry_price * 0.98, 1)  # -2%
    
    logger.info(f"Đặt TP/SL cho {symbol}: Entry={entry_price}, TP={tp_price}, SL={sl_price}")
    
    # Đặt TP/SL
    tp_sl = api.set_stop_loss_take_profit(
        symbol=symbol,
        position_side=position_side,
        entry_price=entry_price,
        stop_loss_price=sl_price,
        take_profit_price=tp_price,
        usd_value=usd_value / 2  # Đóng 50% vị thế
    )
    
    if tp_sl.get('error') or (tp_sl.get('take_profit') and tp_sl['take_profit'].get('error')) or (tp_sl.get('stop_loss') and tp_sl['stop_loss'].get('error')):
        logger.error(f"Lỗi đặt TP/SL: {json.dumps(tp_sl, indent=2)}")
        return False
    
    logger.info(f"TP/SL đặt thành công: {json.dumps(tp_sl, indent=2)}")
    return True

def update_active_positions(api, target_symbols=None):
    """Cập nhật thông tin về các vị thế đang mở"""
    logger.info("Đang cập nhật thông tin vị thế đang mở")
    
    if not target_symbols:
        target_symbols = TARGET_SYMBOLS
    
    # Lấy thông tin vị thế
    positions = api.get_futures_position_risk()
    active_positions = {}
    
    for pos in positions:
        symbol = pos['symbol']
        if symbol not in target_symbols:
            continue
            
        pos_amt = float(pos.get('positionAmt', 0))
        if abs(pos_amt) > 0:
            position_side = pos['positionSide']
            entry_price = float(pos['entryPrice'])
            mark_price = float(pos['markPrice'])
            unreal_pnl = float(pos['unRealizedProfit'])
            leverage = float(pos['leverage'])
            
            if symbol not in active_positions:
                active_positions[symbol] = []
                
            active_positions[symbol].append({
                'positionSide': position_side,
                'positionAmt': pos_amt,
                'entryPrice': entry_price,
                'markPrice': mark_price,
                'pnl': unreal_pnl,
                'leverage': leverage,
                'lastUpdate': int(time.time() * 1000)
            })
            
            logger.info(f"Vị thế {symbol} ({position_side}): {pos_amt} @ {entry_price} (Mark: {mark_price}, PnL: {unreal_pnl})")
    
    # Lưu thông tin vị thế vào file
    if active_positions:
        with open("active_positions.json", "w") as f:
            json.dump(active_positions, f, indent=2)
            logger.info(f"Đã lưu thông tin {sum(len(v) for v in active_positions.values())} vị thế vào active_positions.json")
    else:
        logger.info("Không có vị thế đang mở")
        # Tạo file trống nếu không có vị thế
        with open("active_positions.json", "w") as f:
            json.dump({}, f)
    
    return active_positions

def monitor_positions(api):
    """Thread theo dõi liên tục các vị thế"""
    logger.info("Bắt đầu thread theo dõi vị thế")
    
    try:
        while True:
            update_active_positions(api)
            time.sleep(60)  # Cập nhật mỗi 60 giây
    except Exception as e:
        logger.error(f"Lỗi trong thread theo dõi vị thế: {str(e)}")
        raise e

def main():
    """Hàm chính để tích hợp và kiểm tra các bản vá lỗi"""
    logger.info("===== BẮT ĐẦU TÍCH HỢP CÁC BẢN VÁ LỖI =====")
    
    # Bắt đầu thread monitor
    monitor_threads()
    
    # Kiểm tra kết nối tài khoản
    if not test_account_connection():
        logger.error("Kiểm tra kết nối thất bại, không thể tiếp tục")
        return
        
    # Tạo instance API
    api = BinanceAPI()
    api = apply_fixes_to_api(api)
    
    # Kiểm tra hedge mode
    if not check_position_mode(api):
        logger.warning("Tiếp tục mà không thay đổi chế độ position mode")
    
    # Kiểm tra thông tin symbols
    if not check_all_symbols(api):
        logger.error("Kiểm tra symbols thất bại, không thể tiếp tục")
        return
    
    # Cập nhật thông tin vị thế đang mở
    active_positions = update_active_positions(api)
    
    # Đăng ký thread theo dõi vị thế
    position_monitor_thread = register_thread(
        "position_monitor", 
        monitor_positions,
        (api,)
    )
    
    # Thử tạo lệnh nếu không có vị thế đang mở
    if not active_positions:
        try:
            test_create_order(api, "BTCUSDT", 100)
        except Exception as e:
            logger.error(f"Lỗi khi thử tạo lệnh: {str(e)}")
    
    logger.info("Tích hợp các bản vá thành công, hệ thống đang chạy")
    
    # Giữ script chạy để thread monitor hoạt động
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Nhận tín hiệu dừng, kết thúc chương trình")
        
    logger.info("===== HOÀN THÀNH TÍCH HỢP =====")

if __name__ == "__main__":
    main()