"""
Tích hợp các module mới vào hệ thống chính
Module này giúp khởi động và tích hợp các module thông báo chi tiết,
giám sát vị thế và cập nhật thị trường nâng cao vào hệ thống chính
"""

import logging
import os
import json
import time
import threading
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger('module_integration')

# Import các module đã tạo
from telegram_notifier import TelegramNotifier
from detailed_trade_notifications import DetailedTradeNotifications
from position_monitoring import PositionMonitor
from enhanced_market_updater import EnhancedMarketUpdater

# Đường dẫn file cấu hình
TELEGRAM_CONFIG_PATH = 'telegram_config.json'
BOT_CONFIG_PATH = 'bot_config.json'
ACCOUNT_CONFIG_PATH = 'account_config.json'

def load_config(config_path):
    """
    Tải cấu hình từ file
    
    Args:
        config_path (str): Đường dẫn đến file cấu hình
        
    Returns:
        dict: Cấu hình đã tải
    """
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Đã tải cấu hình từ {config_path}")
            return config
        else:
            logger.warning(f"Không tìm thấy file cấu hình: {config_path}")
            return {}
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình từ {config_path}: {str(e)}")
        return {}

def test_telegram_connection():
    """
    Kiểm tra kết nối Telegram
    
    Returns:
        bool: True nếu kết nối thành công
    """
    try:
        logger.info("Kiểm tra kết nối Telegram...")
        notifier = TelegramNotifier(config_path=TELEGRAM_CONFIG_PATH)
        success = notifier.test_connection()
        
        if success:
            logger.info("Kết nối Telegram thành công")
            return True
        else:
            logger.warning("Kết nối Telegram thất bại")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra kết nối Telegram: {str(e)}")
        return False

def start_enhanced_market_updater(api_connector, data_processor, strategy_engine):
    """
    Khởi động module cập nhật thị trường nâng cao
    
    Args:
        api_connector: API connector
        data_processor: Bộ xử lý dữ liệu
        strategy_engine: Engine chiến lược giao dịch
        
    Returns:
        EnhancedMarketUpdater: Instance của updater
    """
    try:
        logger.info("Khởi động EnhancedMarketUpdater...")
        updater = EnhancedMarketUpdater(
            api_connector=api_connector,
            data_processor=data_processor,
            strategy_engine=strategy_engine,
            telegram_config_path=TELEGRAM_CONFIG_PATH
        )
        
        # Tạo thư mục phân tích thị trường nếu chưa có
        os.makedirs(updater.analysis_dir, exist_ok=True)
        
        # Bắt đầu thread cập nhật
        updater.start_updating()
        
        logger.info("Đã khởi động EnhancedMarketUpdater")
        return updater
    except Exception as e:
        logger.error(f"Lỗi khi khởi động EnhancedMarketUpdater: {str(e)}")
        return None

def start_position_monitor(api_connector):
    """
    Khởi động module giám sát vị thế
    
    Args:
        api_connector: API connector
        
    Returns:
        PositionMonitor: Instance của monitor
    """
    try:
        logger.info("Khởi động PositionMonitor...")
        monitor = PositionMonitor(
            api_connector=api_connector,
            telegram_config_path=TELEGRAM_CONFIG_PATH
        )
        
        # Tạo thư mục phân tích vị thế nếu chưa có
        os.makedirs(monitor.analysis_dir, exist_ok=True)
        
        # Bắt đầu thread giám sát
        monitor.start_monitoring()
        
        logger.info("Đã khởi động PositionMonitor")
        return monitor
    except Exception as e:
        logger.error(f"Lỗi khi khởi động PositionMonitor: {str(e)}")
        return None

def start_detailed_notifications():
    """
    Khởi động module thông báo chi tiết
    
    Returns:
        DetailedTradeNotifications: Instance của notifier
    """
    try:
        logger.info("Khởi động DetailedTradeNotifications...")
        notifier = DetailedTradeNotifications(telegram_config_path=TELEGRAM_CONFIG_PATH)
        
        # Tạo thư mục lưu trữ thông báo nếu chưa có
        os.makedirs('trade_notifications', exist_ok=True)
        
        logger.info("Đã khởi động DetailedTradeNotifications")
        return notifier
    except Exception as e:
        logger.error(f"Lỗi khi khởi động DetailedTradeNotifications: {str(e)}")
        return None

def integrate_modules(api_connector, data_processor, strategy_engine, main_bot=None):
    """
    Tích hợp tất cả các module mới vào hệ thống chính
    
    Args:
        api_connector: API connector
        data_processor: Bộ xử lý dữ liệu
        strategy_engine: Engine chiến lược giao dịch
        main_bot: Instance của bot chính (nếu có)
        
    Returns:
        dict: Các module đã tích hợp
    """
    # Kiểm tra kết nối Telegram (nếu được cấu hình)
    test_telegram_connection()
    
    # Khởi động các module
    detailed_notifier = start_detailed_notifications()
    position_monitor = start_position_monitor(api_connector)
    market_updater = start_enhanced_market_updater(api_connector, data_processor, strategy_engine)
    
    # Thông báo tích hợp thành công
    if all([detailed_notifier, position_monitor, market_updater]):
        telegram = TelegramNotifier(config_path=TELEGRAM_CONFIG_PATH)
        
        if telegram.enabled:
            message = (
                "🚀 *TÍCH HỢP MODULE MỚI THÀNH CÔNG*\n\n"
                "Các module sau đã được tích hợp vào hệ thống:\n"
                "✅ Thông báo chi tiết về giao dịch\n"
                "✅ Giám sát vị thế giao dịch\n"
                "✅ Cập nhật thị trường nâng cao\n\n"
                f"⏰ Thời gian: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
            )
            
            telegram.send_message(message, parse_mode='Markdown')
            logger.info("Đã gửi thông báo tích hợp thành công qua Telegram")
    
    # Trả về các module đã tích hợp
    return {
        'detailed_notifier': detailed_notifier,
        'position_monitor': position_monitor,
        'market_updater': market_updater
    }

# Sử dụng hàm này để tắt các module khi cần
def stop_modules(modules):
    """
    Dừng các module đã tích hợp
    
    Args:
        modules (dict): Dict chứa các module cần dừng
        
    Returns:
        bool: True nếu dừng thành công
    """
    try:
        # Dừng market updater
        if 'market_updater' in modules and modules['market_updater']:
            modules['market_updater'].stop_updating()
            logger.info("Đã dừng EnhancedMarketUpdater")
        
        # Dừng position monitor
        if 'position_monitor' in modules and modules['position_monitor']:
            modules['position_monitor'].stop_monitoring()
            logger.info("Đã dừng PositionMonitor")
        
        return True
    except Exception as e:
        logger.error(f"Lỗi khi dừng các module: {str(e)}")
        return False


if __name__ == "__main__":
    # Import các module cần thiết nếu chạy trực tiếp
    try:
        from binance_api import BinanceAPI
        from data_processor import DataProcessor
        from composite_trading_strategy import CompositeTradingStrategy
        
        # Khởi tạo các thành phần cần thiết
        api_connector = BinanceAPI()
        data_processor = DataProcessor()
        strategy_engine = CompositeTradingStrategy()
        
        # Tích hợp các module
        modules = integrate_modules(api_connector, data_processor, strategy_engine)
        
        logger.info("Đã khởi động tất cả các module thành công")
        
        # Giữ chương trình chạy
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Nhận tín hiệu kết thúc từ người dùng, đang dừng các module...")
        if 'modules' in locals():
            stop_modules(modules)
        logger.info("Đã dừng tất cả các module")
    except Exception as e:
        logger.error(f"Lỗi khi chạy chương trình: {str(e)}")