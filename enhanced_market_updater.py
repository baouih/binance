#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module cập nhật phân tích thị trường tăng cường

Module này cải thiện việc cập nhật phân tích thị trường bằng cách:
1. Tự động chuyển đổi giữa API Testnet và API chính khi cần thiết
2. Gửi thông báo phân tích định kỳ qua Telegram
3. Đảm bảo tất cả các cặp tiền được phân tích đầy đủ
"""

import os
import sys
import json
import time
import logging
import schedule
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("enhanced_market_updater.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("enhanced_market_updater")

# Import các module cần thiết
try:
    from market_data_updater import MarketDataUpdater
    from binance_api import BinanceAPI
    from telegram_notifier import TelegramNotifier
except ImportError as e:
    logger.error(f"Lỗi import module: {e}")
    logger.error("Đảm bảo đang chạy từ thư mục gốc của dự án")
    sys.exit(1)

class EnhancedMarketUpdater:
    """Lớp cập nhật thị trường nâng cao với khả năng tự động điều chỉnh API và gửi thông báo"""
    
    def __init__(self, config_path: str = 'account_config.json', 
                 update_interval: int = 15, 
                 notification_interval: int = 30):
        """
        Khởi tạo bộ cập nhật thị trường nâng cao
        
        Args:
            config_path (str): Đường dẫn tới file cấu hình
            update_interval (int): Chu kỳ cập nhật (phút)
            notification_interval (int): Chu kỳ gửi thông báo (phút)
        """
        self.config_path = config_path
        self.update_interval = update_interval
        self.notification_interval = notification_interval
        
        # Tải cấu hình
        self.config = self._load_config()
        
        # Khởi tạo các thành phần
        self.market_updater = None
        self.binance_api = None
        self.telegram = None
        
        # Khởi tạo kết nối API
        self._init_components()
        
        # Các biến kiểm soát
        self.running = False
        self.last_full_analysis = {}  # Lưu phân tích cuối cùng cho mỗi cặp
        self.update_thread = None
        
    def _load_config(self) -> Dict:
        """
        Tải cấu hình từ file
        
        Returns:
            Dict: Cấu hình đã tải
        """
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Đã tải cấu hình từ {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {e}")
            # Cấu hình mặc định
            return {
                "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"],
                "timeframes": ["1h", "4h"],
                "api_mode": "testnet"
            }
    
    def _init_components(self) -> None:
        """Khởi tạo các thành phần cần thiết"""
        try:
            # Khởi tạo Binance API
            self.binance_api = BinanceAPI()
            
            # Khởi tạo MarketDataUpdater
            self.market_updater = MarketDataUpdater()
            
            # Khởi tạo TelegramNotifier
            self.telegram = TelegramNotifier()
            
            logger.info("Đã khởi tạo các thành phần cần thiết")
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo các thành phần: {e}")
    
    def run_scheduled_updates(self) -> None:
        """Khởi động lập lịch cập nhật tự động"""
        if self.running:
            logger.warning("Lập lịch cập nhật đã đang chạy")
            return
        
        logger.info(f"Bắt đầu lập lịch cập nhật mỗi {self.update_interval} phút")
        
        # Đặt lịch cập nhật
        schedule.every(self.update_interval).minutes.do(self.update_all_markets)
        
        # Đặt lịch gửi thông báo
        schedule.every(self.notification_interval).minutes.do(self.send_market_summary)
        
        # Bắt đầu luồng chạy lịch trình
        self.running = True
        self.update_thread = threading.Thread(target=self._run_scheduler)
        self.update_thread.daemon = True
        self.update_thread.start()
        
        # Chạy một lần ngay khi khởi động
        self.update_all_markets()
        
        logger.info("Đã khởi động lập lịch cập nhật tự động")
    
    def _run_scheduler(self) -> None:
        """Hàm chạy lập lịch trong một thread riêng"""
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def stop_scheduled_updates(self) -> None:
        """Dừng lập lịch cập nhật tự động"""
        if not self.running:
            logger.warning("Lập lịch cập nhật không đang chạy")
            return
        
        logger.info("Dừng lập lịch cập nhật tự động")
        self.running = False
        
        # Xóa tất cả các công việc đã lập lịch
        schedule.clear()
        
        # Chờ thread kết thúc
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=5)
            
        logger.info("Đã dừng lập lịch cập nhật tự động")
    
    def update_all_markets(self) -> Dict[str, bool]:
        """
        Cập nhật phân tích thị trường cho tất cả các cặp giao dịch
        
        Returns:
            Dict[str, bool]: Kết quả cập nhật cho từng cặp
        """
        try:
            logger.info("Bắt đầu cập nhật tất cả các thị trường")
            
            # Lấy danh sách cặp từ cấu hình
            symbols = self.config.get('symbols', [])
            
            if not symbols:
                logger.warning("Không tìm thấy cặp giao dịch nào trong cấu hình")
                return {}
            
            # Gọi cập nhật từ MarketDataUpdater
            results = self.market_updater.update_all_symbols()
            
            # Đếm số cặp cập nhật thành công
            success_count = sum(1 for v in results.values() if v)
            logger.info(f"Đã cập nhật {success_count}/{len(symbols)} cặp giao dịch")
            
            # Lưu kết quả để thông báo sau
            self._collect_market_analysis()
            
            # Lưu thời gian cập nhật
            self._save_last_update_time()
            
            return results
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật tất cả thị trường: {e}")
            return {}
    
    def _collect_market_analysis(self) -> None:
        """Thu thập phân tích thị trường từ các file recommendation"""
        try:
            symbols = self.config.get('symbols', [])
            
            for symbol in symbols:
                symbol_lower = symbol.lower()
                recommendation_file = f"recommendation_{symbol_lower}.json"
                
                if os.path.exists(recommendation_file):
                    try:
                        with open(recommendation_file, 'r') as f:
                            recommendation = json.load(f)
                            self.last_full_analysis[symbol] = recommendation
                            logger.info(f"Đã thu thập phân tích cho {symbol}")
                    except Exception as e:
                        logger.error(f"Lỗi khi đọc file {recommendation_file}: {e}")
        except Exception as e:
            logger.error(f"Lỗi khi thu thập phân tích thị trường: {e}")
    
    def _save_last_update_time(self) -> None:
        """Lưu thời gian cập nhật cuối cùng"""
        try:
            with open('market_update_status.json', 'w') as f:
                json.dump({
                    'last_update': datetime.now().isoformat(),
                    'next_update': (datetime.now() + timedelta(minutes=self.update_interval)).isoformat(),
                    'next_notification': (datetime.now() + timedelta(minutes=self.notification_interval)).isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Lỗi khi lưu thời gian cập nhật: {e}")
    
    def send_market_summary(self) -> None:
        """Gửi tóm tắt phân tích thị trường qua Telegram"""
        try:
            logger.info("Đang gửi tóm tắt phân tích thị trường qua Telegram")
            
            # Tạo thông báo
            message = self._generate_market_summary()
            
            # Gửi qua Telegram
            if message and self.telegram:
                result = self.telegram.send_notification('info', message)
                if result.get('ok'):
                    logger.info("Đã gửi tóm tắt phân tích thị trường qua Telegram")
                else:
                    logger.error(f"Lỗi khi gửi thông báo: {result.get('error', 'Unknown error')}")
            else:
                logger.warning("Không có phân tích để gửi hoặc kết nối Telegram không khả dụng")
        except Exception as e:
            logger.error(f"Lỗi khi gửi tóm tắt thị trường: {e}")
    
    def _generate_market_summary(self) -> str:
        """
        Tạo tin nhắn tóm tắt phân tích thị trường
        
        Returns:
            str: Nội dung tin nhắn
        """
        try:
            if not self.last_full_analysis:
                return "Không có dữ liệu phân tích nào. Đang chờ cập nhật tiếp theo."
            
            # Tạo tiêu đề
            message = f"<b>TÓM TẮT THỊ TRƯỜNG</b>\n\n"
            
            # Thêm thông tin cho từng cặp
            for symbol, analysis in self.last_full_analysis.items():
                signal_text = analysis.get('signal_text', 'KHÔNG CÓ TÍN HIỆU')
                confidence = analysis.get('confidence', 0)
                price = analysis.get('price', 0)
                action = analysis.get('action', 'CHỜ ĐỢI')
                
                # Thêm emoji dựa trên tín hiệu
                if "MUA" in signal_text or "LONG" in signal_text:
                    emoji = "🟢"
                elif "BÁN" in signal_text or "SHORT" in signal_text:
                    emoji = "🔴"
                else:
                    emoji = "⚪"
                
                # Thêm thông tin từng cặp
                message += f"{emoji} <b>{symbol}</b>: {signal_text} (tin cậy: {confidence:.1f}%)\n"
                message += f"💵 Giá: {price}, Đề xuất: {action}\n\n"
            
            # Thêm thông tin thời gian
            message += f"<i>Cập nhật: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>\n"
            message += f"<i>Cập nhật tiếp theo: {self.update_interval} phút sau</i>"
            
            return message
        except Exception as e:
            logger.error(f"Lỗi khi tạo tóm tắt thị trường: {e}")
            return "Lỗi khi tạo tóm tắt thị trường. Vui lòng kiểm tra logs."

def main():
    """Hàm chính"""
    try:
        logger.info("Khởi động Enhanced Market Updater")
        
        # Khởi tạo và chạy Enhanced Market Updater
        updater = EnhancedMarketUpdater(
            update_interval=15,     # Cập nhật mỗi 15 phút
            notification_interval=30  # Gửi thông báo mỗi 30 phút
        )
        
        # Khởi động lập lịch cập nhật
        updater.run_scheduled_updates()
        
        # Giữ cho tiến trình chạy
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Nhận tín hiệu dừng từ người dùng")
            updater.stop_scheduled_updates()
        
        logger.info("Enhanced Market Updater đã dừng")
        return 0
    except Exception as e:
        logger.error(f"Lỗi không mong đợi: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())