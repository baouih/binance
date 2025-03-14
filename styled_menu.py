#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module cung cấp các chức năng menu có kiểu dáng và màu sắc được cải thiện
cho giao diện desktop PyQt5
"""

from PyQt5.QtWidgets import QMenuBar, QMenu, QAction
from PyQt5.QtGui import QColor, QPalette, QFont
from PyQt5.QtCore import Qt

class StyledMenuBar(QMenuBar):
    """QMenuBar có kiểu dáng cao cấp với độ tương phản cao hơn"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Thiết lập kiểu dáng cơ bản
        self.setStyleSheet("""
            QMenuBar {
                background-color: #2D3748;
                color: #FFFFFF;
                padding: 2px;
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
            QMenuBar::item:pressed {
                background-color: #4A5568;
                color: #FFFFFF;
                border: 1px solid #63B3ED;
            }
        """)
        
        # Đặt font đậm
        font = self.font()
        font.setBold(True)
        self.setFont(font)

class StyledMenu(QMenu):
    """QMenu có kiểu dáng cao cấp với độ tương phản cao hơn"""
    
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        
        # Thiết lập kiểu dáng cơ bản
        self.setStyleSheet("""
            QMenu {
                background-color: #2D3748;
                color: #FFFFFF;
                border: 1px solid #4A5568;
                padding: 2px;
            }
            QMenu::item {
                padding: 6px 20px;
                color: #FFFFFF;
                border-radius: 4px;
                margin: 2px;
            }
            QMenu::item:selected {
                background-color: #4A5568;
                color: #FFFFFF;
                border-left: 2px solid #63B3ED;
            }
            QMenu::separator {
                height: 1px;
                background-color: #4A5568;
                margin: 6px 0px;
            }
            QMenu::indicator {
                width: 14px;
                height: 14px;
            }
        """)
        
        # Đặt font đậm
        font = self.font()
        font.setBold(True)
        self.setFont(font)

class HighContrastAction(QAction):
    """QAction có kiểu dáng cao cấp với độ tương phản cao hơn"""
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        
        # Đặt font đậm
        font = self.font()
        font.setBold(True)
        self.setFont(font)

def apply_menu_style_to_widget(widget):
    """Áp dụng kiểu dáng menu tương phản cao cho widget"""
    
    # Kiểu dáng chung
    widget.setStyleSheet("""
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
    """)

def create_high_contrast_menubar(parent):
    """Tạo menubar tương phản cao"""
    menubar = StyledMenuBar(parent)
    return menubar

def create_high_contrast_menu(title, parent=None):
    """Tạo menu tương phản cao"""
    menu = StyledMenu(title, parent)
    return menu

def create_high_contrast_action(text, parent=None):
    """Tạo action tương phản cao"""
    action = HighContrastAction(text, parent)
    return action