#!/usr/bin/env python3
"""
Script đơn giản hóa để triển khai bot giao dịch đa đồng tiền

Script này sẽ:
1. Đọc cấu hình từ multi_coin_config.json
2. Kết nối với Binance API (testnet hoặc thực)
3. Theo dõi nhiều cặp giao dịch đồng thời
4. Đưa ra tín hiệu giao dịch dựa trên phân tích kỹ thuật và mô hình ML
5. Gửi thông báo qua Telegram
"""

import os
import sys
import time
import logging
import json
import argparse
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('multi_coin_bot.log')
    ]
)
logger = logging.getLogger('multi_coin_bot')

# Đường dẫn tương đối
sys.path.append(".")
from app.binance_api import BinanceAPI
from app.data_processor import DataProcessor
from app.market_regime_detector import MarketRegimeDetector
try:
    from app.composite_indicator import CompositeIndicator
except ImportError:
    # Sử dụng phiên bản từ thư mục gốc nếu không tìm thấy trong app/
    from composite_indicator import CompositeIndicator
from telegram_notify import telegram_notifier

class MultiCoinBot:
    """Bot giao dịch đa đồng tiền đơn giản hóa"""
    
    def __init__(self, config_file="multi_coin_config.json", live_mode=False):
        """
        Khởi tạo bot giao dịch đa đồng tiền
        
        Args:
            config_file (str): Đường dẫn đến file cấu hình
            live_mode (bool): Chế độ giao dịch thực hay giả lập
        """
        self.config_file = config_file
        self.live_mode = live_mode
        self.config = self._load_config()
        
        # Kích hoạt các cặp giao dịch
        self.active_pairs = [pair for pair in self.config["trading_pairs"] if pair["enabled"]]
        self.symbols = [pair["symbol"] for pair in self.active_pairs]
        
        # Khởi tạo API Binance
        self.api = BinanceAPI(
            api_key=os.environ.get("BINANCE_API_KEY"),
            api_secret=os.environ.get("BINANCE_API_SECRET"),
            testnet=not live_mode  # Sử dụng testnet nếu không phải chế độ live
        )
        
        # Khởi tạo các thành phần phân tích
        self.data_processor = DataProcessor(self.api)
        self.market_regime_detector = MarketRegimeDetector()
        self.composite_indicator = CompositeIndicator()
        
        # Trạng thái theo dõi
        self.market_data = {}
        self.signals = {}
        
        # Gửi thông báo khi khởi động
        if self.config["general_settings"]["telegram_notifications"]:
            telegram_notifier.send_startup_notification()
        
        logger.info(f"Đã khởi tạo bot với {len(self.active_pairs)} cặp giao dịch: {', '.join(self.symbols)}")
    
    def _load_config(self):
        """Tải cấu hình từ file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
            raise
    
    def analyze_market(self, symbol):
        """
        Phân tích thị trường cho một cặp giao dịch
        
        Args:
            symbol (str): Cặp giao dịch cần phân tích
            
        Returns:
            dict: Kết quả phân tích
        """
        # Tìm cấu hình cho cặp này
        pair_config = next((p for p in self.active_pairs if p["symbol"] == symbol), None)
        if not pair_config:
            return None
        
        primary_timeframe = pair_config["timeframes"][0]
        
        # Lấy dữ liệu lịch sử
        df = self.data_processor.get_historical_data(
            symbol=symbol,
            interval=primary_timeframe,
            lookback_days=7
        )
        
        if df is None or df.empty:
            logger.error(f"Không thể lấy dữ liệu cho {symbol}")
            return None
        
        # Phát hiện chế độ thị trường
        market_regime = self.market_regime_detector.detect_regime(df)
        
        # Tính toán chỉ báo tổng hợp
        composite_score = self.composite_indicator.calculate_composite_score(df)
        
        # Lấy giá hiện tại
        current_price = self.api.get_symbol_price(symbol)
        
        # Tổng hợp kết quả
        analysis = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "market_regime": market_regime,
            "composite_score": composite_score['score'],
            "price": current_price,
            "individual_scores": composite_score.get('individual_scores', {}),
        }
        
        # Xác định tín hiệu giao dịch
        if composite_score['score'] > 0.5:
            analysis["signal"] = "buy"
        elif composite_score['score'] < -0.5:
            analysis["signal"] = "sell"
        else:
            analysis["signal"] = "neutral"
        
        # Tính toán ngưỡng tin cậy (0-1)
        analysis["confidence"] = abs(composite_score['score']) if abs(composite_score['score']) <= 1.0 else 1.0
        
        # Lưu lại thông tin thị trường
        self.market_data[symbol] = analysis
        
        return analysis
    
    def check_signals(self):
        """
        Kiểm tra tín hiệu giao dịch cho tất cả các cặp đang kích hoạt
        
        Returns:
            dict: Tín hiệu giao dịch cho mỗi cặp
        """
        signals = {}
        
        for symbol in self.symbols:
            analysis = self.analyze_market(symbol)
            if not analysis:
                continue
            
            # Tìm cấu hình cho cặp này
            pair_config = next((p for p in self.active_pairs if p["symbol"] == symbol), None)
            entry_threshold = pair_config.get("entry_threshold", 0.65)
            
            # Kiểm tra nếu tín hiệu đạt ngưỡng tin cậy
            if analysis["signal"] != "neutral" and analysis["confidence"] >= entry_threshold:
                signals[symbol] = {
                    "action": analysis["signal"],
                    "price": analysis["price"],
                    "confidence": analysis["confidence"],
                    "market_regime": analysis["market_regime"]
                }
                
                # Gửi thông báo Telegram nếu cấu hình
                if self.config["general_settings"]["telegram_notifications"]:
                    notification_level = self.config["general_settings"]["notification_level"]
                    if notification_level in ["all", "trades_and_signals", "signals_only"]:
                        telegram_notifier.send_trade_signal(analysis)
            
            # Log tín hiệu
            logger.info(f"Phân tích {symbol}: {analysis['signal']} "
                       f"(Confidence: {analysis['confidence']:.2f}, Regime: {analysis['market_regime']})")
        
        self.signals = signals
        return signals
    
    def run(self, check_interval=300, max_cycles=None):
        """
        Chạy bot theo định kỳ
        
        Args:
            check_interval (int): Thời gian giữa các lần kiểm tra (giây)
            max_cycles (int): Số chu kỳ tối đa, None nếu chạy vô hạn
        """
        logger.info(f"Bắt đầu chạy bot đa đồng tiền với chu kỳ {check_interval}s")
        
        cycle = 0
        try:
            while True:
                cycle += 1
                logger.info(f"=== Chu kỳ kiểm tra #{cycle} ===")
                
                # Kiểm tra kết nối API
                try:
                    self.api.test_connection()
                except Exception as e:
                    logger.error(f"Lỗi kết nối API: {str(e)}")
                    if self.config["general_settings"]["telegram_notifications"]:
                        telegram_notifier.send_error_alert(f"Kết nối API thất bại: {str(e)}", "API Error")
                    time.sleep(60)  # Chờ 1 phút trước khi thử lại
                    continue
                
                # Kiểm tra tín hiệu giao dịch
                signals = self.check_signals()
                
                # Hiển thị tín hiệu nếu có
                if signals:
                    logger.info("=== Tín hiệu giao dịch ===")
                    for symbol, signal in signals.items():
                        logger.info(f"{symbol}: {signal['action'].upper()} @ {signal['price']} "
                                  f"(Confidence: {signal['confidence']:.2f}, Regime: {signal['market_regime']})")
                else:
                    logger.info("Không có tín hiệu giao dịch đủ mạnh.")
                
                # Gửi báo cáo tổng hợp qua Telegram
                if cycle % 12 == 0:  # Khoảng 1 giờ nếu check_interval=300s
                    self._send_summary_report()
                
                # Kiểm tra nếu đã đạt số chu kỳ tối đa
                if max_cycles is not None and cycle >= max_cycles:
                    logger.info(f"Đã đạt số chu kỳ tối đa ({max_cycles}), dừng bot.")
                    break
                
                logger.info(f"Đang chờ {check_interval} giây đến lần kiểm tra tiếp theo...")
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            logger.info("Bot đã được dừng thủ công bởi người dùng.")
        except Exception as e:
            logger.error(f"Lỗi không mong muốn: {str(e)}")
            if self.config["general_settings"]["telegram_notifications"]:
                telegram_notifier.send_error_alert(str(e), "Critical Error")
        finally:
            logger.info("Bot đã dừng.")
            if self.config["general_settings"]["telegram_notifications"]:
                telegram_notifier.send_message("Bot giao dịch đã dừng hoạt động.")
    
    def _send_summary_report(self):
        """Gửi báo cáo tổng hợp tình hình thị trường qua Telegram"""
        if not self.config["general_settings"]["telegram_notifications"]:
            return
        
        # Tạo báo cáo
        report = "<b>📊 BÁO CÁO TỔNG QUAN THỊ TRƯỜNG</b>\n\n"
        report += f"<b>Thời gian:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Thêm thông tin cho mỗi cặp
        for symbol in self.symbols:
            if symbol in self.market_data:
                data = self.market_data[symbol]
                regime = data["market_regime"]
                price = data["price"]
                score = data["composite_score"]
                
                # Emoji dựa trên tín hiệu
                emoji = "🟢" if score > 0.3 else "🔴" if score < -0.3 else "⚪️"
                
                report += f"{emoji} <b>{symbol}:</b> ${price:,.2f}\n"
                report += f"    Regime: {regime}, Score: {score:.2f}\n"
        
        # Gửi báo cáo
        telegram_notifier.send_message(report)
        logger.info("Đã gửi báo cáo tổng quan thị trường qua Telegram")

def main():
    """Hàm chính để chạy bot"""
    parser = argparse.ArgumentParser(description='Bot giao dịch đa đồng tiền')
    parser.add_argument('--config', type=str, default='multi_coin_config.json',
                        help='Đường dẫn đến file cấu hình')
    parser.add_argument('--interval', type=int, default=300,
                        help='Thời gian giữa các lần kiểm tra (giây)')
    parser.add_argument('--live', action='store_true',
                        help='Chạy trong chế độ thực tế (mặc định là giả lập)')
    parser.add_argument('--cycles', type=int, default=None,
                        help='Số chu kỳ tối đa, None nếu chạy vô hạn')
    
    args = parser.parse_args()
    
    # Khởi tạo và chạy bot
    bot = MultiCoinBot(config_file=args.config, live_mode=args.live)
    bot.run(check_interval=args.interval, max_cycles=args.cycles)

if __name__ == "__main__":
    main()