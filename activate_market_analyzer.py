#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script kích hoạt hệ thống phân tích thị trường và thông báo
Script này:
1. Khởi tạo và kích hoạt Market Analysis System
2. Thiết lập thông báo chi tiết qua Telegram
3. Bắt đầu phân tích coin theo cấu hình
4. Chạy trong chế độ nền với lịch trình thông báo tự động
"""

import os
import sys
import time
import logging
import threading
import schedule
import json
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("market_analyzer_activation.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("market_analyzer")

# Import các module cần thiết
try:
    from telegram_notifier import TelegramNotifier
    from market_analysis_system import MarketAnalysisSystem
    from enhanced_telegram_notifications import EnhancedTelegramNotifications
except ImportError as e:
    logger.error(f"Lỗi import module: {e}")
    logger.error("Đảm bảo đã tạo và cài đặt đúng các module cần thiết")
    sys.exit(1)

def save_pid():
    """Lưu PID vào file để có thể dừng tiến trình sau này"""
    pid = os.getpid()
    
    with open('market_analyzer.pid', 'w') as f:
        f.write(str(pid))
    
    logger.info(f"Đã lưu PID {pid} vào market_analyzer.pid")

def scheduled_market_analysis(market_analyzer, telegram, symbols=None, timeframes=None):
    """
    Chạy phân tích thị trường theo lịch trình

    Args:
        market_analyzer: Đối tượng MarketAnalysisSystem
        telegram: Đối tượng TelegramNotifier
        symbols: Danh sách các cặp tiền điện tử cần phân tích
        timeframes: Danh sách các khung thời gian cần phân tích
    """
    logger.info("Đang chạy phân tích thị trường theo lịch trình...")
    
    try:
        # Phân tích tổng thể thị trường
        market_analyzer.analyze_market()
        logger.info("Đã phân tích tổng thể thị trường")
        
        # Phân tích các cặp coin theo cấu hình
        if symbols is None:
            symbols = market_analyzer.config['symbols_to_analyze']
        
        if timeframes is None:
            timeframes = market_analyzer.config['timeframes']
        
        # Phân tích từng coin và tạo báo cáo
        analysis_results = {}
        for symbol in symbols:
            logger.info(f"Đang phân tích {symbol}...")
            symbol_result = market_analyzer.analyze_symbol(symbol, timeframes)
            analysis_results[symbol] = symbol_result
            
            # Lưu phân tích riêng cho từng coin
            with open(f"market_analysis_{symbol.lower()}.json", "w") as f:
                json.dump(symbol_result, f, indent=4)
            
            # Tạo file recommendation
            recommendation = {
                'symbol': symbol,
                'price': market_analyzer.api.get_symbol_price(symbol),
                'signal': 'NEUTRAL',
                'signal_text': 'Đang phân tích dữ liệu',
                'confidence': 50,
                'action': 'THEO DÕI',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'timeframes': {},
                'summary': 'Tổng hợp các chỉ báo và phân tích kỹ thuật'
            }
            
            # Cập nhật recommendation dựa trên kết quả phân tích
            if symbol_result:
                # Tính toán tín hiệu từ kết quả phân tích
                bullish_count = 0
                bearish_count = 0
                neutral_count = 0
                total_signals = 0
                
                # Đánh giá tín hiệu từ các khung thời gian
                recommendation['timeframes'] = {}
                for timeframe, data in symbol_result.items():
                    if not isinstance(data, dict):
                        continue
                        
                    indicators = data.get('indicators', {})
                    signal = 'NEUTRAL'
                    signal_strength = 0
                    
                    # Đánh giá RSI
                    rsi = indicators.get('rsi', 50)
                    if rsi < 30:
                        bullish_count += 1
                        signal_strength += 1
                    elif rsi > 70:
                        bearish_count += 1
                        signal_strength += 1
                    else:
                        neutral_count += 1
                    
                    # Đánh giá MACD
                    macd = indicators.get('macd', {})
                    if macd.get('histogram', 0) > 0 and macd.get('signal_crossover', '') == 'bullish':
                        bullish_count += 1
                        signal_strength += 1
                    elif macd.get('histogram', 0) < 0 and macd.get('signal_crossover', '') == 'bearish':
                        bearish_count += 1
                        signal_strength += 1
                    
                    # Đánh giá MA
                    ma_trend = indicators.get('ma_trend', 'neutral')
                    if ma_trend == 'bullish':
                        bullish_count += 1
                    elif ma_trend == 'bearish':
                        bearish_count += 1
                    else:
                        neutral_count += 1
                    
                    # Xác định tín hiệu cho timeframe này
                    if bullish_count > bearish_count and bullish_count > neutral_count:
                        signal = 'BUY'
                        if bullish_count >= 3:
                            signal = 'STRONG_BUY'
                    elif bearish_count > bullish_count and bearish_count > neutral_count:
                        signal = 'SELL'
                        if bearish_count >= 3:
                            signal = 'STRONG_SELL'
                    
                    # Cập nhật thông tin cho timeframe
                    recommendation['timeframes'][timeframe] = {
                        'signal': signal,
                        'strength': signal_strength,
                        'indicators': indicators
                    }
                    
                    total_signals += 1
                
                # Xác định tín hiệu tổng thể
                if total_signals > 0:
                    if bullish_count > bearish_count and bullish_count > neutral_count:
                        recommendation['signal'] = 'BUY'
                        if bullish_count >= total_signals * 0.7:
                            recommendation['signal'] = 'STRONG_BUY'
                        recommendation['signal_text'] = 'Tín hiệu mua dựa trên phân tích kỹ thuật'
                        recommendation['action'] = 'XEM XÉT MUA'
                        recommendation['confidence'] = min(100, int(bullish_count / total_signals * 100))
                    elif bearish_count > bullish_count and bearish_count > neutral_count:
                        recommendation['signal'] = 'SELL'
                        if bearish_count >= total_signals * 0.7:
                            recommendation['signal'] = 'STRONG_SELL'
                        recommendation['signal_text'] = 'Tín hiệu bán dựa trên phân tích kỹ thuật'
                        recommendation['action'] = 'XEM XÉT BÁN'
                        recommendation['confidence'] = min(100, int(bearish_count / total_signals * 100))
                    else:
                        recommendation['signal'] = 'NEUTRAL'
                        recommendation['signal_text'] = 'Thị trường đang đi ngang, chờ tín hiệu rõ ràng'
                        recommendation['action'] = 'THEO DÕI'
                        recommendation['confidence'] = max(40, min(60, int(neutral_count / total_signals * 100)))
            
            with open(f"recommendation_{symbol.lower()}.json", "w") as f:
                json.dump(recommendation, f, indent=4)
        
        # Lưu kết quả tổng hợp
        with open("market_analysis.json", "w") as f:
            json.dump(analysis_results, f, indent=4)
        
        # Gửi thông báo
        telegram.send_notification(
            "info", 
            f"<b>✅ ĐÃ HOÀN THÀNH PHÂN TÍCH {len(symbols)} COIN</b>\n\n"
            f"Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n"
            f"Khung thời gian: {', '.join(timeframes)}"
        )
        
        logger.info(f"Đã hoàn thành phân tích {len(symbols)} coin trên {len(timeframes)} khung thời gian")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi phân tích thị trường: {str(e)}")
        
        # Gửi thông báo lỗi
        telegram.send_notification(
            "error",
            f"<b>❌ LỖI KHI PHÂN TÍCH THỊ TRƯỜNG</b>\n\n"
            f"Thông báo lỗi: {str(e)}\n\n"
            f"<i>Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
        )
        return False

def main():
    """Hàm chính khởi động hệ thống phân tích thị trường"""
    try:
        logger.info("Bắt đầu kích hoạt hệ thống phân tích thị trường")
        
        # Lưu PID
        save_pid()
        
        # Khởi tạo TelegramNotifier
        telegram = TelegramNotifier()
        
        # Thông báo bắt đầu
        telegram.send_notification(
            "info",
            "<b>🚀 BẮT ĐẦU KÍCH HOẠT HỆ THỐNG PHÂN TÍCH THỊ TRƯỜNG</b>\n\n"
            "Đang khởi tạo các module...\n"
            f"Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"
        )
        
        # Khởi tạo MarketAnalysisSystem
        config_path = "configs/market_analysis_config.json"
        market_analyzer = MarketAnalysisSystem(config_path=config_path)
        logger.info(f"Đã khởi tạo MarketAnalysisSystem từ {config_path}")
        
        # Khởi tạo thông báo Telegram nâng cao
        telegram_notifications = EnhancedTelegramNotifications(
            notification_interval=30  # 30 phút/lần thông báo
        )
        logger.info("Đã khởi tạo thông báo Telegram nâng cao")
        
        # Đọc cấu hình
        symbols = market_analyzer.config['symbols_to_analyze']
        timeframes = market_analyzer.config['timeframes']
        primary_timeframe = market_analyzer.config['primary_timeframe']
        
        # Thiết lập lịch trình phân tích
        schedule.every(30).minutes.do(
            scheduled_market_analysis, 
            market_analyzer=market_analyzer, 
            telegram=telegram, 
            symbols=symbols, 
            timeframes=timeframes
        )
        
        # Thiết lập lịch trình thông báo
        schedule.every(60).minutes.do(telegram_notifications.send_market_update)
        
        # Gửi thông báo về cấu hình
        telegram.send_notification(
            "success",
            "<b>✅ HỆ THỐNG PHÂN TÍCH THỊ TRƯỜNG ĐÃ ĐƯỢC KÍCH HOẠT</b>\n\n"
            "📊 <b>Thông tin chi tiết:</b>\n"
            f"• Cập nhật thị trường: mỗi 30 phút\n"
            f"• Thông báo phân tích: mỗi 60 phút\n"
            f"• Khung thời gian chính: {primary_timeframe}\n"
            f"• Các coin theo dõi: {len(symbols)}\n"
            f"• Các khung thời gian: {', '.join(timeframes)}\n\n"
            f"<i>Thời gian kích hoạt: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
        )
        
        # Chạy phân tích thị trường ngay lập tức
        logger.info("Bắt đầu phân tích thị trường lần đầu")
        scheduled_market_analysis(market_analyzer, telegram, symbols, timeframes)
        logger.info("Đã hoàn thành phân tích thị trường lần đầu")
        
        # Chạy thông báo phân tích ngay lập tức
        telegram_notifications.send_market_update()
        
        logger.info("Hệ thống phân tích thị trường đang chạy trong nền")
        
        # Giữ cho tiến trình chạy và chạy lịch trình
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Nhận tín hiệu dừng từ người dùng")
        
        # Thông báo hệ thống đã dừng
        telegram.send_notification(
            "warning",
            "<b>⚠️ HỆ THỐNG PHÂN TÍCH THỊ TRƯỜNG ĐÃ DỪNG</b>\n\n"
            f"<i>Thời gian dừng: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
        )
        
        logger.info("Hệ thống phân tích thị trường đã dừng thành công")
        return 0
        
    except Exception as e:
        logger.error(f"Lỗi không mong đợi khi khởi động hệ thống: {e}")
        
        # Thông báo lỗi qua Telegram
        try:
            telegram = TelegramNotifier()
            telegram.send_notification(
                "error",
                "<b>❌ LỖI KHI KHỞI ĐỘNG HỆ THỐNG PHÂN TÍCH</b>\n\n"
                f"Thông báo lỗi: {str(e)}\n\n"
                f"<i>Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            )
        except:
            pass  # Bỏ qua nếu không thể gửi thông báo
            
        return 1

if __name__ == "__main__":
    sys.exit(main())