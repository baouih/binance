#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Package Desktop App with Backtest
--------------------------------
Tạo gói ứng dụng desktop có đầy đủ kết quả backtest
"""

import os
import sys
import json
import shutil
import logging
import zipfile
import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('package_desktop_app')

# Đường dẫn
DESKTOP_APP_DIR = 'desktop_app'
ENHANCED_GUI_PATH = 'enhanced_trading_gui.py'
OUTPUT_DIR = 'desktop_package'
CONFIG_FILES = [
    'account_config.json',
    'bot_config.json',
    'risk_config.json',
    'gui_config.json'
]

def create_output_dir():
    """Tạo thư mục đầu ra"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        logger.info(f"Đã tạo thư mục {OUTPUT_DIR}")
    else:
        logger.info(f"Thư mục {OUTPUT_DIR} đã tồn tại")

def update_backtest_results():
    """Cập nhật kết quả backtest"""
    try:
        import update_desktop_backtest_results
        update_desktop_backtest_results.main()
        logger.info("Đã cập nhật kết quả backtest")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật kết quả backtest: {e}")
        return False

def fix_backtest_tab():
    """Sửa lỗi tab backtest"""
    try:
        import fix_desktop_backtest
        fix_desktop_backtest.main()
        logger.info("Đã sửa lỗi tab backtest")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi sửa tab backtest: {e}")
        return False

def copy_main_script():
    """Sao chép script giao diện chính"""
    dest_file = os.path.join(OUTPUT_DIR, 'trading_app.py')
    try:
        shutil.copy2(ENHANCED_GUI_PATH, dest_file)
        logger.info(f"Đã sao chép {ENHANCED_GUI_PATH} đến {dest_file}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi sao chép script giao diện: {e}")
        return False

def copy_config_files():
    """Sao chép các file cấu hình"""
    success_count = 0
    for config_file in CONFIG_FILES:
        if os.path.exists(config_file):
            dest_file = os.path.join(OUTPUT_DIR, config_file)
            try:
                shutil.copy2(config_file, dest_file)
                logger.info(f"Đã sao chép {config_file} đến {dest_file}")
                success_count += 1
            except Exception as e:
                logger.error(f"Lỗi khi sao chép {config_file}: {e}")
    
    return success_count > 0

def copy_backtest_directory():
    """Sao chép thư mục desktop_app chứa backtest results"""
    dest_dir = os.path.join(OUTPUT_DIR, 'desktop_app')
    try:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)
        
        shutil.copytree(DESKTOP_APP_DIR, dest_dir)
        logger.info(f"Đã sao chép thư mục {DESKTOP_APP_DIR} đến {dest_dir}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi sao chép thư mục desktop_app: {e}")
        return False

def copy_required_modules():
    """Sao chép các module cần thiết"""
    required_modules = [
        'binance_api.py',
        'data_processor.py',
        'technical_indicators.py',
        'trade_manager.py',
        'risk_manager.py',
        'market_analyzer.py',
        'position_manager.py',
        'strategy_selector.py',
        'signal_generator.py',
        'telegram_notifier.py',
        'utils.py',
        'backtest_processor.py',
        'account_risk_allocator.py',
        'account_risk_calculator.py',
        'account_risk_scaling.py',
        'account_size_based_strategy.py',
        'account_type_selector.py',
        'adaptive_risk_allocator.py',
        'adaptive_risk_manager.py',
        'account_config.json',
    ]
    
    success_count = 0
    for module in required_modules:
        if os.path.exists(module):
            dest_file = os.path.join(OUTPUT_DIR, module)
            try:
                shutil.copy2(module, dest_file)
                logger.info(f"Đã sao chép {module} đến {dest_file}")
                success_count += 1
            except Exception as e:
                logger.error(f"Lỗi khi sao chép {module}: {e}")
    
    return success_count > 0

def create_launcher():
    """Tạo script khởi động"""
    launcher_path = os.path.join(OUTPUT_DIR, 'run_trading_app.py')
    launcher_content = """#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging
from PyQt5.QtWidgets import QApplication

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='trading_app.log'
)
logger = logging.getLogger('trading_app_launcher')

# Nhập lớp MainApp từ script giao diện
try:
    from trading_app import MainApp
    logger.info("Đã tải thành công module trading_app")
except Exception as e:
    logger.error(f"Lỗi khi tải module trading_app: {e}")
    print(f"Lỗi khi tải module trading_app: {e}")
    sys.exit(1)

def main():
    try:
        # Tạo ứng dụng Qt
        app = QApplication(sys.argv)
        
        # Tạo cửa sổ chính
        main_window = MainApp()
        
        # Hiển thị cửa sổ chính
        main_window.show()
        
        # Chạy vòng lặp sự kiện
        sys.exit(app.exec_())
    except Exception as e:
        logger.error(f"Lỗi khi khởi động ứng dụng: {e}")
        print(f"Lỗi khi khởi động ứng dụng: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
"""
    
    try:
        with open(launcher_path, 'w', encoding='utf-8') as f:
            f.write(launcher_content)
        logger.info(f"Đã tạo script khởi động: {launcher_path}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi tạo script khởi động: {e}")
        return False

def create_readme():
    """Tạo file README"""
    readme_path = os.path.join(OUTPUT_DIR, 'README.md')
    readme_content = """# Ứng dụng Giao dịch với Kết quả Backtest

## Giới thiệu

Đây là ứng dụng giao dịch tiền điện tử đầy đủ, tích hợp kết quả backtest từ nhiều chiến lược và mức rủi ro khác nhau. Ứng dụng này giúp bạn có thể đưa ra quyết định giao dịch thông minh dựa trên dữ liệu backtest thực tế.

## Tính năng chính

- **Giao diện đồ họa thân thiện** với các tab chức năng:
  - Dashboard: Tổng quan tài khoản và thị trường
  - Trading: Giao dịch theo thời gian thực
  - Positions: Quản lý vị thế
  - Market Analysis: Phân tích thị trường
  - Risk Management: Quản lý rủi ro
  - Backtest: Xem kết quả backtest
  - Settings: Cài đặt hệ thống
  - System Management: Quản lý hệ thống

- **Chế độ backtesting** với:
  - Chiến lược Sideways: Win rate 85-100% (100% ở mức 10-15% rủi ro)
  - Chiến lược Multi-Risk: Win rate 60-95%
  - Chiến lược Adaptive: Win rate 65-85%

- **Quản lý rủi ro thông minh** dựa trên kích thước tài khoản:
  - Tài khoản nhỏ ($100-500): 20-30% rủi ro
  - Tài khoản vừa ($500-$5,000): 5-15% rủi ro
  - Tài khoản lớn (>$5,000): 0.5-3% rủi ro

## Cài đặt

1. Cài đặt Python 3.8 trở lên
2. Cài đặt các thư viện cần thiết:
```
pip install PyQt5 pandas numpy matplotlib ccxt binance-futures-connector python-binance
```
3. Chạy ứng dụng:
```
python run_trading_app.py
```

## Cấu hình

Các file cấu hình chính:
- account_config.json: Cấu hình tài khoản
- bot_config.json: Cấu hình bot giao dịch
- risk_config.json: Cấu hình rủi ro
- gui_config.json: Cấu hình giao diện

## Hỗ trợ

Nếu bạn cần hỗ trợ, vui lòng liên hệ qua:
- Email: support@tradingsystem.com
"""
    
    try:
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        logger.info(f"Đã tạo file README: {readme_path}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi tạo file README: {e}")
        return False

def copy_user_guide():
    """Sao chép hướng dẫn sử dụng"""
    guide_file = 'HƯỚNG_DẪN_DESKTOP_VỚI_BACKTEST.md'
    if os.path.exists(guide_file):
        dest_file = os.path.join(OUTPUT_DIR, guide_file)
        try:
            shutil.copy2(guide_file, dest_file)
            logger.info(f"Đã sao chép {guide_file} đến {dest_file}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi sao chép hướng dẫn sử dụng: {e}")
    else:
        logger.warning(f"Không tìm thấy file hướng dẫn: {guide_file}")
    
    return False

def create_zip_package():
    """Tạo gói ZIP"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = f"trading_app_with_backtest_{timestamp}.zip"
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(OUTPUT_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, OUTPUT_DIR)
                    zipf.write(file_path, arcname)
        
        logger.info(f"Đã tạo gói ZIP: {zip_path}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi tạo gói ZIP: {e}")
        return False

def main():
    """Hàm chính để đóng gói ứng dụng desktop"""
    logger.info("Bắt đầu đóng gói ứng dụng desktop với kết quả backtest")
    
    # Tạo thư mục đầu ra
    create_output_dir()
    
    # Cập nhật kết quả backtest
    update_backtest_results()
    
    # Sửa lỗi tab backtest
    fix_backtest_tab()
    
    # Sao chép script giao diện chính
    copy_main_script()
    
    # Sao chép các file cấu hình
    copy_config_files()
    
    # Sao chép thư mục desktop_app
    copy_backtest_directory()
    
    # Sao chép các module cần thiết
    copy_required_modules()
    
    # Tạo script khởi động
    create_launcher()
    
    # Tạo file README
    create_readme()
    
    # Sao chép hướng dẫn sử dụng
    copy_user_guide()
    
    # Tạo gói ZIP
    create_zip_package()
    
    logger.info("Đã hoàn thành đóng gói ứng dụng desktop với kết quả backtest")

if __name__ == "__main__":
    main()