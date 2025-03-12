#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dịch vụ thông báo thị trường tự động
Tác giả: BinanceTrader Bot
"""

import os
import time
import schedule
import requests
import logging
import json
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram_notifier import TelegramNotifier
from market_analysis_system import MarketAnalysisSystem
from binance_api import BinanceAPI

# Tải biến môi trường
load_dotenv()

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("market_notifier.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("market_notifier")

# Khởi tạo các thành phần
telegram = TelegramNotifier()
market_system = MarketAnalysisSystem()
binance_api = BinanceAPI()

# Danh sách các coin cần theo dõi
MONITORED_COINS = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "MATIC"]

# Thời gian cooldown (phút) giữa các thông báo cho mỗi coin
NOTIFICATION_COOLDOWN = 15

# Ngưỡng tự tin tối thiểu để gửi tín hiệu
CONFIDENCE_THRESHOLD = 70

# Biến kiểm soát thời gian gửi tin nhắn cuối cùng cho mỗi coin
last_notification_time = {}

# Biến lưu trữ tín hiệu cuối cùng cho mỗi coin
last_signals = {}

def initialize():
    """Khởi tạo dịch vụ thông báo thị trường"""
    global last_notification_time, last_signals
    
    logger.info("Khởi tạo dịch vụ thông báo thị trường")
    
    # Kiểm tra kết nối Telegram
    if telegram.test_connection():
        logger.info("Kết nối Telegram thành công")
    else:
        logger.error("Không thể kết nối Telegram. Vui lòng kiểm tra cấu hình.")
    
    # Kiểm tra kết nối Binance
    try:
        btc_price = binance_api.get_latest_price("BTCUSDT")
        logger.info(f"Kết nối Binance thành công. Giá BTC hiện tại: ${btc_price}")
    except Exception as e:
        logger.error(f"Không thể kết nối Binance: {str(e)}")
    
    # Khởi tạo các biến kiểm soát
    for coin in MONITORED_COINS:
        last_notification_time[coin] = datetime.now() - timedelta(minutes=NOTIFICATION_COOLDOWN)
        last_signals[coin] = None
    
    # Gửi thông báo khởi động
    telegram.send_message(
        message=f"<b>🤖 Dịch vụ thông báo thị trường đã được khởi động</b>\n\n"
                f"🕒 Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"🔍 Giám sát: {', '.join(MONITORED_COINS)}\n"
                f"⏱️ Cooldown: {NOTIFICATION_COOLDOWN} phút\n"
                f"🎯 Độ tự tin tối thiểu: {CONFIDENCE_THRESHOLD}%"
    )
    
    logger.info(f"Đang giám sát coin {', '.join(MONITORED_COINS)}")

def analyze_market():
    """Phân tích thị trường và gửi thông báo"""
    logger.info("Bắt đầu phân tích thị trường")
    current_time = datetime.now()
    
    try:
        # Lấy chế độ thị trường cho từng coin
        market_regimes = {}
        for coin in MONITORED_COINS:
            try:
                symbol = f"{coin}USDT"
                regime = market_system.get_market_regime(symbol)
                if regime:
                    market_regimes[coin] = regime
                    logger.debug(f"Chế độ thị trường {coin}: {regime}")
            except Exception as e:
                logger.error(f"Lỗi khi phân tích chế độ thị trường {coin}: {str(e)}")
        
        # Lấy tín hiệu giao dịch
        for coin in MONITORED_COINS:
            try:
                # Kiểm tra thời gian cooldown
                if current_time - last_notification_time.get(coin, datetime.min) < timedelta(minutes=NOTIFICATION_COOLDOWN):
                    logger.debug(f"Đang trong thời gian cooldown cho {coin}")
                    continue
                
                symbol = f"{coin}USDT"
                # Phân tích kỹ thuật
                signal = market_system.analyze_and_get_signal(symbol)
                
                if not signal:
                    continue
                
                # Lấy thông tin tín hiệu
                signal_type = signal.get('type', 'NEUTRAL')
                confidence = signal.get('confidence', 0)
                strategy = signal.get('strategy', 'Unknown')
                price = signal.get('price', 0)
                
                # Kiểm tra độ tự tin
                if confidence < CONFIDENCE_THRESHOLD:
                    logger.debug(f"Tín hiệu {coin} có độ tự tin {confidence}% - dưới ngưỡng {CONFIDENCE_THRESHOLD}%")
                    continue
                
                # Kiểm tra xung đột với tín hiệu trước
                previous_signal = last_signals.get(coin)
                if previous_signal and previous_signal.get('type') != signal_type:
                    logger.info(f"Tín hiệu mới ({signal_type}) khác với tín hiệu trước đó ({previous_signal.get('type')}) cho {coin}")
                
                # Lưu tín hiệu mới
                last_signals[coin] = signal
                
                # Cập nhật thời gian thông báo cuối
                last_notification_time[coin] = current_time
                
                # Tạo emoji phù hợp
                emoji = "🔴" if signal_type == "SELL" else "🟢" if signal_type == "BUY" else "⚪"
                
                # Lấy giá hiện tại
                current_price = binance_api.get_latest_price(symbol)
                
                # Tạo thông báo
                message = f"<b>{emoji} Tín hiệu giao dịch: {coin}</b>\n\n"
                message += f"<b>Loại tín hiệu:</b> {signal_type}\n"
                message += f"<b>Độ tự tin:</b> {confidence}%\n"
                message += f"<b>Giá hiện tại:</b> ${current_price}\n"
                message += f"<b>Chiến lược:</b> {strategy}\n"
                message += f"<b>Chế độ thị trường:</b> {market_regimes.get(coin, 'Unknown')}\n"
                message += f"<b>Thời gian:</b> {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
                
                # Gửi thông báo
                telegram.send_message(message=message)
                logger.info(f"Đã gửi thông báo tín hiệu {signal_type} cho {coin} với độ tự tin {confidence}%")
                
            except Exception as e:
                logger.error(f"Lỗi khi phân tích và gửi tín hiệu cho {coin}: {str(e)}")
        
        # Gửi báo cáo tổng quan thị trường mỗi 4 giờ
        if current_time.hour % 4 == 0 and current_time.minute < 5:
            send_market_overview()
            
    except Exception as e:
        logger.error(f"Lỗi khi phân tích thị trường: {str(e)}")

def send_market_overview():
    """Gửi báo cáo tổng quan thị trường"""
    try:
        logger.info("Đang tạo báo cáo tổng quan thị trường")
        
        # Lấy dữ liệu tổng quan
        message = "<b>🔍 TỔNG QUAN THỊ TRƯỜNG</b>\n\n"
        
        # Thêm thông tin giá của các coin chính
        message += "<b>💰 Giá hiện tại:</b>\n"
        for coin in MONITORED_COINS[:5]:  # Chỉ lấy 5 coin đầu tiên
            try:
                symbol = f"{coin}USDT"
                price = binance_api.get_latest_price(symbol)
                change_24h = binance_api.get_price_change_percent(symbol)
                emoji = "🟢" if change_24h >= 0 else "🔴"
                message += f"{coin}: ${price} ({emoji}{abs(change_24h):.2f}%)\n"
            except Exception as e:
                logger.error(f"Lỗi khi lấy thông tin giá {coin}: {str(e)}")
                message += f"{coin}: Không có dữ liệu\n"
        
        # Thêm thông tin chế độ thị trường
        message += "\n<b>🌐 Chế độ thị trường:</b>\n"
        for coin in MONITORED_COINS[:5]:
            try:
                symbol = f"{coin}USDT"
                regime = market_system.get_market_regime(symbol)
                emoji = "↗️" if regime == "Bullish" else "↘️" if regime == "Bearish" else "↔️"
                message += f"{coin}: {emoji} {regime}\n"
            except Exception as e:
                logger.error(f"Lỗi khi lấy chế độ thị trường {coin}: {str(e)}")
                message += f"{coin}: Không có dữ liệu\n"
        
        # Thêm phân tích xu hướng
        message += f"\n<b>📊 Xu hướng (4H):</b>\n"
        for coin in MONITORED_COINS[:5]:
            try:
                symbol = f"{coin}USDT"
                analysis = market_system.get_trend_analysis(symbol, "4h")
                trend = analysis.get('trend', 'Neutral')
                strength = analysis.get('strength', 0.5)
                emoji = "🟢" if trend == "Bullish" else "🔴" if trend == "Bearish" else "⚪"
                strength_bar = "▰" * int(strength * 10) + "▱" * (10 - int(strength * 10))
                message += f"{coin}: {emoji} {trend} ({strength_bar})\n"
            except Exception as e:
                logger.error(f"Lỗi khi lấy phân tích xu hướng {coin}: {str(e)}")
                message += f"{coin}: Không có dữ liệu\n"
        
        # Gửi thông báo
        telegram.send_message(message=message)
        logger.info("Đã gửi báo cáo tổng quan thị trường")
    except Exception as e:
        logger.error(f"Lỗi khi tạo báo cáo tổng quan thị trường: {str(e)}")

def schedule_jobs():
    """Lên lịch các công việc định kỳ"""
    # Lịch trình phân tích thị trường mỗi 10 phút
    schedule.every(10).minutes.do(analyze_market)
    
    logger.info("Đã lên lịch các công việc tự động")

def run_service():
    """Chạy dịch vụ thông báo thị trường"""
    logger.info("Dịch vụ thông báo thị trường đang chạy")
    
    # Khởi tạo dịch vụ
    initialize()
    
    # Lên lịch các công việc
    schedule_jobs()
    
    # Phân tích thị trường ngay lập tức
    analyze_market()
    
    # Vòng lặp chính
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Dịch vụ đã bị dừng bởi người dùng")
    except Exception as e:
        logger.error(f"Lỗi không xác định: {str(e)}")
        # Gửi thông báo lỗi
        telegram.send_message(
            message=f"<b>❌ Lỗi dịch vụ thông báo thị trường</b>\n\n"
                    f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Lỗi: {str(e)}"
        )

if __name__ == "__main__":
    # Lưu PID vào file
    with open("market_notifier.pid", "w") as f:
        f.write(str(os.getpid()))
    
    # Ghi ra stdout để xác nhận script đã chạy
    print(f"Dịch vụ thông báo thị trường đã được khởi động với PID {os.getpid()}")
    
    # Chạy dịch vụ
    run_service()