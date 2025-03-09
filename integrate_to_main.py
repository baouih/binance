"""
Script tích hợp các module mới vào hệ thống chính
Script này sẽ được chạy để bắt đầu tích hợp các module mới vào bot hiện có
"""

import logging
import os
import sys
import json
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger('integrate_to_main')

# Import các module đã tạo
from telegram_notifier import TelegramNotifier
from detailed_trade_notifications import DetailedTradeNotifications
from position_monitoring import PositionMonitor
from enhanced_market_updater import EnhancedMarketUpdater
from integrate_modules import integrate_modules
from modules_manager import register_module_routes

def main():
    """
    Hàm chính để tích hợp các module mới
    """
    logger.info("Bắt đầu tích hợp các module mới vào hệ thống chính...")
    
    try:
        # Import các module từ hệ thống chính
        from binance_api import BinanceAPI
        from data_processor import DataProcessor
        from composite_trading_strategy import CompositeTradingStrategy
        import main as main_app
        
        # Thông báo
        logger.info("Đã import các module từ hệ thống chính thành công")
        
        # Kiểm tra các thư mục cần thiết
        os.makedirs('logs', exist_ok=True)
        os.makedirs('market_analysis', exist_ok=True)
        os.makedirs('position_analysis', exist_ok=True)
        os.makedirs('trade_notifications', exist_ok=True)
        
        # Khởi tạo các thành phần cần thiết
        api_connector = BinanceAPI()
        data_processor = DataProcessor()
        strategy_engine = CompositeTradingStrategy()
        
        # Tích hợp các module
        modules = integrate_modules(api_connector, data_processor, strategy_engine)
        
        # Thêm các API routes vào Flask app chính
        if hasattr(main_app, 'app'):
            register_module_routes(main_app.app)
            logger.info("Đã đăng ký các API routes vào Flask app chính")
        
        # Lưu modules vào biến toàn cục của main app
        main_app.integrated_modules = modules
        
        # In thông báo thành công
        if all([
            modules['detailed_notifier'],
            modules['position_monitor'],
            modules['market_updater']
        ]):
            logger.info("------------------------------------")
            logger.info("Tích hợp các module mới thành công!")
            logger.info("- Thông báo chi tiết về giao dịch: ✅")
            logger.info("- Giám sát vị thế giao dịch: ✅")
            logger.info("- Cập nhật thị trường nâng cao: ✅")
            logger.info("------------------------------------")
            
            # Gửi thông báo qua Telegram
            notifier = TelegramNotifier()
            message = (
                "🚀 *TÍCH HỢP MODULE MỚI THÀNH CÔNG*\n\n"
                "Các module sau đã được tích hợp vào hệ thống:\n"
                "✅ Thông báo chi tiết về giao dịch\n"
                "✅ Giám sát vị thế giao dịch\n"
                "✅ Cập nhật thị trường nâng cao\n\n"
                f"⏰ Thời gian: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
            )
            notifier.send_message(message, parse_mode='Markdown')
            
            return True
        else:
            logger.error("Tích hợp các module mới không thành công")
            return False
    
    except ImportError as e:
        logger.error(f"Lỗi khi import module từ hệ thống chính: {e}")
        return False
    except Exception as e:
        logger.error(f"Lỗi khi tích hợp các module mới: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)