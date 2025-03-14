#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script áp dụng phong cách menu độ tương phản cao cho ứng dụng.
Chạy script này để sửa lỗi menu chữ trùng màu nền.
"""

import os
import sys
import logging
from pathlib import Path

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fix_menu_colors")

# Import styled_menu
try:
    from styled_menu import apply_menu_style_to_widget
except ImportError:
    logger.error("Không thể import module styled_menu, vui lòng đảm bảo file styled_menu.py tồn tại")
    sys.exit(1)

def inject_style_to_enhanced_trading_gui():
    """
    Tiêm CSS độ tương phản cao vào enhanced_trading_gui.py
    """
    try:
        # Đường dẫn đến file enhanced_trading_gui.py
        gui_file = 'enhanced_trading_gui.py'
        
        if not os.path.exists(gui_file):
            logger.error(f"Không tìm thấy file {gui_file}")
            return False
        
        # Đọc nội dung file
        with open(gui_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Kiểm tra xem đã tiêm CSS chưa
        if "HIGH_CONTRAST_DARK_THEME_CSS" in content:
            logger.info("File đã được cập nhật với CSS độ tương phản cao")
            return True
        
        # Thêm biến CSS mới
        high_contrast_css = '''
# CSS cho dark theme độ tương phản cao
HIGH_CONTRAST_DARK_THEME_CSS = """
    QMainWindow {
        background-color: #1F2937;
        color: #FFFFFF;
    }
    QTabWidget {
        background-color: #1F2937;
        color: #FFFFFF;
    }
    QTabWidget::pane {
        border: 1px solid #3B4252;
        background-color: #1F2937;
    }
    QTabBar::tab {
        background-color: #2D3748;
        color: white;
        padding: 8px 16px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    QTabBar::tab:selected {
        background-color: #4B5563;
        font-weight: bold;
        border-bottom: 2px solid #63B3ED;
    }
    QPushButton {
        background-color: #3B82F6;
        color: white;
        padding: 6px 12px;
        border-radius: 4px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #2563EB;
    }
    QPushButton:pressed {
        background-color: #1D4ED8;
    }
    QMenuBar {
        background-color: #2D3748;
        color: #FFFFFF;
        padding: 4px;
        font-weight: bold;
        border-bottom: 1px solid #4A5568;
    }
    QMenuBar::item {
        background-color: transparent;
        padding: 6px 12px;
        color: #FFFFFF;
        font-weight: bold;
        border-radius: 4px;
        margin: 1px;
    }
    QMenuBar::item:selected {
        background-color: #4A5568;
        color: #FFFFFF;
        border: 1px solid #63B3ED;
    }
    QMenu {
        background-color: #2D3748;
        color: #FFFFFF;
        border: 1px solid #4A5568;
        padding: 4px;
    }
    QMenu::item {
        padding: 8px 24px;
        color: #FFFFFF;
        font-weight: bold;
        border-radius: 4px;
        margin: 2px;
    }
    QMenu::item:selected {
        background-color: #4A5568;
        color: #FFFFFF;
        border-left: 3px solid #63B3ED;
    }
    QMenu::separator {
        height: 1px;
        background-color: #4A5568;
        margin: 6px 0px;
    }
"""
'''
        
        # Tìm vị trí để thêm CSS
        position = content.find("class EnhancedTradingGUI")
        if position == -1:
            logger.error("Không tìm thấy lớp EnhancedTradingGUI trong file")
            return False
        
        # Tìm vị trí trước lớp EnhancedTradingGUI để thêm CSS
        import_end = content.rfind("import", 0, position)
        insert_position = content.find("\n", import_end)
        
        # Thêm CSS vào nội dung
        new_content = content[:insert_position+1] + high_contrast_css + content[insert_position+1:]
        
        # Thay thế phương thức set_dark_theme
        old_method = """    def set_dark_theme(self):
        \"\"\"Thiết lập dark theme\"\"\"
        # Stylesheet chung
        self.setStyleSheet(self.styleSheet())"""
        
        new_method = """    def set_dark_theme(self):
        \"\"\"Thiết lập dark theme với độ tương phản cao\"\"\"
        # Stylesheet chung với độ tương phản cao
        self.setStyleSheet(HIGH_CONTRAST_DARK_THEME_CSS)
        
        # Áp dụng kiểu dáng menu tương phản cao
        try:
            from styled_menu import apply_menu_style_to_widget
            apply_menu_style_to_widget(self)
            logger.info("Đã áp dụng kiểu dáng menu tương phản cao")
        except ImportError:
            logger.warning("Không thể import module styled_menu")"""
        
        # Thay thế phương thức
        if old_method in new_content:
            new_content = new_content.replace(old_method, new_method)
        else:
            logger.warning("Không tìm thấy phương thức set_dark_theme để thay thế")
        
        # Ghi nội dung mới vào file
        with open(gui_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info(f"Đã cập nhật file {gui_file} với CSS độ tương phản cao")
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật file: {str(e)}")
        return False

def main():
    """Hàm chính"""
    logger.info("Bắt đầu cập nhật CSS cho menu")
    
    # Tiêm CSS vào enhanced_trading_gui.py
    result = inject_style_to_enhanced_trading_gui()
    
    if result:
        logger.info("Cập nhật CSS thành công!")
        logger.info("Vui lòng khởi động lại ứng dụng để áp dụng thay đổi")
    else:
        logger.error("Cập nhật CSS thất bại!")
        logger.info("Vui lòng kiểm tra lại các file và thư viện")

if __name__ == "__main__":
    main()