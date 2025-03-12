#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module thông báo giao dịch và hoạt động chi tiết qua Telegram

Module này cung cấp thông báo chi tiết về:
1. Thông tin giao dịch (vào lệnh, ra lệnh, chốt lãi/lỗ)
2. Hoạt động của trailing stop
3. Cảnh báo thị trường
4. Phân tích các cặp giao dịch
5. Trạng thái hoạt động hệ thống
6. Lý do không giao dịch
7. Cập nhật cấu hình và chiến lược
"""

import os
import sys
import json
import time
import logging
import datetime
import threading
import traceback
from typing import Dict, List, Any, Optional, Union, Tuple
from collections import defaultdict

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("detailed_notifications.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("detailed_notifications")

# Import các module cần thiết
try:
    from telegram_notifier import TelegramNotifier
    # Thêm các module phân tích
    from analyze_no_trade_reasons import NoTradeReasonsAnalyzer
    from market_analysis_system import MarketAnalysisSystem
except ImportError as e:
    logger.error(f"Lỗi import module: {e}")
    logger.error("Đảm bảo đang chạy từ thư mục gốc của dự án")
    sys.exit(1)

class DetailedTradeNotifications:
    """Cung cấp thông báo chi tiết về giao dịch và hoạt động hệ thống"""
    
    def __init__(self, config_path: str = 'configs/telegram/telegram_notification_config.json'):
        """
        Khởi tạo hệ thống thông báo chi tiết
        
        Args:
            config_path (str): Đường dẫn tới file cấu hình Telegram
        """
        self.config_path = config_path
        self.notification_config = self._load_notification_config()
        
        # Khởi tạo Telegram notifier
        self.telegram = TelegramNotifier()
        
        # Khởi tạo các công cụ phân tích
        self.market_analyzer = MarketAnalysisSystem()
        self.no_trade_analyzer = NoTradeReasonsAnalyzer()
        
        # Thông tin theo dõi
        self.last_notification_time = defaultdict(lambda: datetime.datetime.min)
        self.notification_cooldowns = {
            'trade_signal': 60,  # giây
            'market_alert': 300,  # giây
            'system_status': 1800,  # giây
            'trailing_stop': 300,  # giây
            'position_update': 600,  # giây
            'no_trade_reasons': 1800,  # giây
            'strategy_change': 300,  # giây
        }
        
        # Thông tin các vị thế đang mở
        self.active_positions = {}
        self.trailing_stops = {}
        
        # Dữ liệu thị trường
        self.market_data = {}
        
        logger.info("Đã khởi tạo hệ thống thông báo chi tiết")
    
    def _load_notification_config(self) -> Dict:
        """
        Tải cấu hình thông báo từ file
        
        Returns:
            Dict: Cấu hình thông báo
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    logger.info(f"Đã tải cấu hình thông báo từ {self.config_path}")
                    return config
            
            # Nếu không tìm thấy file, tạo cấu hình mặc định
            default_config = {
                'enabled': True,
                'notification_types': {
                    'trade_signal': True,
                    'market_alert': True,
                    'system_status': True,
                    'trailing_stop': True,
                    'position_update': True,
                    'no_trade_reasons': True,
                    'strategy_change': True
                },
                'send_charts': True,
                'detailed_info': True,
                'max_symbols_per_message': 5,
                'cooldown_override': False
            }
            
            # Lưu cấu hình mặc định
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            
            logger.info(f"Đã tạo cấu hình thông báo mặc định tại {self.config_path}")
            return default_config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình thông báo: {str(e)}")
            return {
                'enabled': True,
                'notification_types': {
                    'trade_signal': True,
                    'market_alert': True,
                    'system_status': True,
                    'trailing_stop': True,
                    'position_update': True,
                    'no_trade_reasons': True,
                    'strategy_change': True
                },
                'send_charts': True,
                'detailed_info': True,
                'max_symbols_per_message': 5,
                'cooldown_override': False
            }
    
    def _check_cooldown(self, notification_type: str) -> bool:
        """
        Kiểm tra thời gian chờ giữa các thông báo
        
        Args:
            notification_type (str): Loại thông báo
            
        Returns:
            bool: True nếu có thể gửi thông báo, False nếu đang trong thời gian chờ
        """
        if self.notification_config.get('cooldown_override', False):
            return True
            
        now = datetime.datetime.now()
        last_time = self.last_notification_time[notification_type]
        cooldown = self.notification_cooldowns.get(notification_type, 60)  # mặc định 60 giây
        
        if (now - last_time).total_seconds() < cooldown:
            return False
            
        self.last_notification_time[notification_type] = now
        return True
    
    def update_market_data(self, market_data: Dict) -> None:
        """
        Cập nhật dữ liệu thị trường mới nhất
        
        Args:
            market_data (Dict): Dữ liệu thị trường
        """
        self.market_data = market_data
        logger.info(f"Đã cập nhật dữ liệu thị trường cho {len(market_data)} cặp giao dịch")
        
    def send_multi_symbol_analysis(self, symbols: List[str]) -> bool:
        """
        Gửi phân tích đa symbol
        
        Args:
            symbols: Danh sách các symbols cần phân tích
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        try:
            logger.info(f"Đang gửi phân tích đa symbol: {symbols}")
            
            # Thu thập dữ liệu phân tích cho từng symbol
            analysis_data = {}
            
            for symbol in symbols:
                # Lấy phân tích từ market_analyzer
                result = self.market_analyzer.analyze_symbol(symbol)
                if result:
                    analysis_data[symbol] = result
            
            if not analysis_data:
                logger.warning("Không có dữ liệu phân tích nào để gửi")
                return False
            
            # Tạo thông báo
            message = "<b>📊 PHÂN TÍCH ĐA COIN</b>\n\n"
            
            # Thêm thông tin cho từng symbol
            for symbol, data in analysis_data.items():
                symbol_name = symbol.replace("USDT", "")
                current_price = data.get("current_price", 0)
                
                # Lấy thông tin tín hiệu
                summary = data.get("summary", {})
                signal = summary.get("overall_signal", "NEUTRAL")
                confidence = summary.get("confidence", 0)
                
                signal_emoji = "⚪"
                if signal in ["STRONG_BUY", "BUY", "Mua"]:
                    signal_emoji = "🟢"
                elif signal in ["STRONG_SELL", "SELL", "Bán"]:
                    signal_emoji = "🔴"
                
                message += f"{signal_emoji} <b>{symbol_name} (${current_price:,.2f}):</b>\n"
                message += f"• Tín hiệu: {signal}\n"
                message += f"• Độ tin cậy: {confidence:.2f}%\n"
                
                # Thêm thông tin hỗ trợ/kháng cự
                support_resistance = data.get("support_resistance", [])
                support = None
                resistance = None
                
                for level in support_resistance:
                    if level.get("type") == "Hỗ trợ" and (support is None or level.get("value", 0) > support):
                        support = level.get("value", 0)
                    elif level.get("type") == "Kháng cự" and (resistance is None or level.get("value", 0) < resistance):
                        resistance = level.get("value", 0)
                
                if support:
                    message += f"• Hỗ trợ gần nhất: ${support:,.2f}\n"
                if resistance:
                    message += f"• Kháng cự gần nhất: ${resistance:,.2f}\n"
                
                # Thêm xu hướng
                if "short_term_trend" in data:
                    message += f"• Xu hướng ngắn hạn: {data.get('short_term_trend', 'N/A')}\n"
                if "mid_term_trend" in data:
                    message += f"• Xu hướng trung hạn: {data.get('mid_term_trend', 'N/A')}\n"
                
                message += "\n"
            
            # Thêm thời gian
            message += f"⏱ <i>Thời gian: {datetime.datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            # Gửi thông báo
            result = self.telegram.send_notification("info", message)
            
            if result:
                logger.info(f"Đã gửi phân tích đa symbol ({', '.join(symbols)}) thành công")
                return True
            else:
                logger.error(f"Lỗi khi gửi phân tích đa symbol")
                return False
                
        except Exception as e:
            logger.error(f"Lỗi khi gửi phân tích đa symbol: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def update_positions(self, positions: Dict) -> None:
        """
        Cập nhật thông tin các vị thế đang mở
        
        Args:
            positions (Dict): Thông tin vị thế
        """
        # Kiểm tra vị thế mới và gửi thông báo
        for symbol, position in positions.items():
            if symbol not in self.active_positions:
                # Vị thế mới
                self.send_new_position_notification(symbol, position)
            elif self._has_position_changed(self.active_positions[symbol], position):
                # Vị thế thay đổi
                self.send_position_update_notification(symbol, self.active_positions[symbol], position)
        
        # Kiểm tra vị thế đã đóng
        for symbol in list(self.active_positions.keys()):
            if symbol not in positions:
                # Vị thế đã đóng
                self.send_position_closed_notification(symbol, self.active_positions[symbol])
        
        # Cập nhật danh sách vị thế
        self.active_positions = positions.copy()
        logger.info(f"Đã cập nhật {len(positions)} vị thế đang mở")
    
    def update_trailing_stops(self, trailing_stops: Dict) -> None:
        """
        Cập nhật thông tin trailing stop
        
        Args:
            trailing_stops (Dict): Thông tin trailing stop
        """
        # Kiểm tra trailing stop mới và gửi thông báo
        for symbol, stop_info in trailing_stops.items():
            if symbol not in self.trailing_stops:
                # Trailing stop mới
                self.send_new_trailing_stop_notification(symbol, stop_info)
            elif self._has_trailing_stop_changed(self.trailing_stops[symbol], stop_info):
                # Trailing stop thay đổi
                self.send_trailing_stop_update_notification(symbol, self.trailing_stops[symbol], stop_info)
        
        # Kiểm tra trailing stop đã xóa
        for symbol in list(self.trailing_stops.keys()):
            if symbol not in trailing_stops:
                # Trailing stop đã xóa
                self.send_trailing_stop_removed_notification(symbol, self.trailing_stops[symbol])
        
        # Cập nhật danh sách trailing stop
        self.trailing_stops = trailing_stops.copy()
        logger.info(f"Đã cập nhật {len(trailing_stops)} trailing stop")
    
    def _has_position_changed(self, old_position: Dict, new_position: Dict) -> bool:
        """
        Kiểm tra xem vị thế có thay đổi không
        
        Args:
            old_position (Dict): Vị thế cũ
            new_position (Dict): Vị thế mới
            
        Returns:
            bool: True nếu có thay đổi, False nếu không
        """
        # Kiểm tra các thay đổi quan trọng
        if float(old_position.get('positionAmt', 0)) != float(new_position.get('positionAmt', 0)):
            return True
        if float(old_position.get('entryPrice', 0)) != float(new_position.get('entryPrice', 0)):
            return True
        if float(old_position.get('leverage', 0)) != float(new_position.get('leverage', 0)):
            return True
        if float(old_position.get('unrealizedProfit', 0)) != float(new_position.get('unrealizedProfit', 0)):
            return True
        
        return False
    
    def _has_trailing_stop_changed(self, old_stop: Dict, new_stop: Dict) -> bool:
        """
        Kiểm tra xem trailing stop có thay đổi không
        
        Args:
            old_stop (Dict): Trailing stop cũ
            new_stop (Dict): Trailing stop mới
            
        Returns:
            bool: True nếu có thay đổi, False nếu không
        """
        # Kiểm tra các thay đổi quan trọng
        if float(old_stop.get('activation_price', 0)) != float(new_stop.get('activation_price', 0)):
            return True
        if float(old_stop.get('callback_rate', 0)) != float(new_stop.get('callback_rate', 0)):
            return True
        if old_stop.get('status', '') != new_stop.get('status', ''):
            return True
        if float(old_stop.get('current_price', 0)) != float(new_stop.get('current_price', 0)):
            return True
        
        return False
    
    def send_new_position_notification(self, symbol: str, position: Dict) -> bool:
        """
        Gửi thông báo vị thế mới
        
        Args:
            symbol (str): Ký hiệu cặp giao dịch
            position (Dict): Thông tin vị thế
            
        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            if not self._check_notification_enabled('trade_signal'):
                return False
                
            if not self._check_cooldown('trade_signal'):
                logger.info(f"Bỏ qua thông báo vị thế mới cho {symbol} do đang trong thời gian chờ")
                return False
                
            logger.info(f"Đang gửi thông báo vị thế mới cho {symbol}")
            
            # Tạo nội dung thông báo
            message = self._create_new_position_message(symbol, position)
            
            # Gửi thông báo
            result = self.telegram.send_message(message, parse_mode="HTML")
            
            if result:
                logger.info(f"Đã gửi thông báo vị thế mới cho {symbol}")
                return True
            else:
                logger.error(f"Lỗi khi gửi thông báo vị thế mới cho {symbol}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo vị thế mới: {str(e)}")
            return False
    
    def _create_new_position_message(self, symbol: str, position: Dict) -> str:
        """
        Tạo nội dung thông báo vị thế mới
        
        Args:
            symbol (str): Ký hiệu cặp giao dịch
            position (Dict): Thông tin vị thế
            
        Returns:
            str: Nội dung thông báo
        """
        try:
            # Lấy thông tin cơ bản
            entry_price = float(position.get('entryPrice', 0))
            qty = float(position.get('positionAmt', 0))
            leverage = float(position.get('leverage', 1))
            
            # Xác định hướng giao dịch
            side = "LONG" if qty > 0 else "SHORT"
            emoji = "🟢" if side == "LONG" else "🔴"
            
            # Lấy giá hiện tại
            current_price = float(position.get('markPrice', 0)) or self.market_data.get(symbol, 0)
            
            # Tính lợi nhuận
            if side == "LONG":
                profit_percent = (current_price - entry_price) / entry_price * 100 * leverage
            else:
                profit_percent = (entry_price - current_price) / entry_price * 100 * leverage
                
            profit_icon = "📈" if profit_percent > 0 else "📉"
            
            # Tạo thông báo
            message = f"{emoji} <b>VỊ THẾ MỚI - {symbol} {side}</b> {emoji}\n\n"
            message += f"💰 <b>Entry Price:</b> {entry_price:.4f}\n"
            message += f"📊 <b>Số lượng:</b> {abs(qty):.4f}\n"
            message += f"🔄 <b>Đòn bẩy:</b> {leverage}x\n"
            message += f"💵 <b>Giá hiện tại:</b> {current_price:.4f}\n"
            message += f"{profit_icon} <b>Lợi nhuận:</b> {profit_percent:.2f}%\n\n"
            
            # Thêm phân tích nếu có
            analysis = self._get_symbol_analysis(symbol)
            if analysis:
                message += "<b>PHÂN TÍCH KỸ THUẬT</b>\n"
                message += f"📊 <b>Xu hướng:</b> {analysis.get('trend', 'N/A')}\n"
                message += f"🎯 <b>Mục tiêu:</b> {analysis.get('target_price', 'N/A')}\n"
                message += f"🛑 <b>Stop Loss:</b> {analysis.get('stop_loss', 'N/A')}\n\n"
            
            # Thêm thông tin thời gian
            message += f"<i>⏱️ {datetime.datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            return message
        except Exception as e:
            logger.error(f"Lỗi khi tạo thông báo vị thế mới: {str(e)}")
            return f"<b>🔔 VỊ THẾ MỚI - {symbol}</b>\n\nĐã mở vị thế mới cho {symbol}.\nXem chi tiết trong ứng dụng."
    
    def send_position_update_notification(self, symbol: str, old_position: Dict, new_position: Dict) -> bool:
        """
        Gửi thông báo cập nhật vị thế
        
        Args:
            symbol (str): Ký hiệu cặp giao dịch
            old_position (Dict): Thông tin vị thế cũ
            new_position (Dict): Thông tin vị thế mới
            
        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            if not self._check_notification_enabled('position_update'):
                return False
                
            if not self._check_cooldown('position_update'):
                logger.info(f"Bỏ qua thông báo cập nhật vị thế cho {symbol} do đang trong thời gian chờ")
                return False
                
            logger.info(f"Đang gửi thông báo cập nhật vị thế cho {symbol}")
            
            # Tạo nội dung thông báo
            message = self._create_position_update_message(symbol, old_position, new_position)
            
            # Gửi thông báo
            result = self.telegram.send_message(message, parse_mode="HTML")
            
            if result:
                logger.info(f"Đã gửi thông báo cập nhật vị thế cho {symbol}")
                return True
            else:
                logger.error(f"Lỗi khi gửi thông báo cập nhật vị thế cho {symbol}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo cập nhật vị thế: {str(e)}")
            return False
    
    def _create_position_update_message(self, symbol: str, old_position: Dict, new_position: Dict) -> str:
        """
        Tạo nội dung thông báo cập nhật vị thế
        
        Args:
            symbol (str): Ký hiệu cặp giao dịch
            old_position (Dict): Thông tin vị thế cũ
            new_position (Dict): Thông tin vị thế mới
            
        Returns:
            str: Nội dung thông báo
        """
        try:
            # Lấy thông tin cơ bản
            old_qty = float(old_position.get('positionAmt', 0))
            new_qty = float(new_position.get('positionAmt', 0))
            
            old_entry = float(old_position.get('entryPrice', 0))
            new_entry = float(new_position.get('entryPrice', 0))
            
            old_profit = float(old_position.get('unrealizedProfit', 0))
            new_profit = float(new_position.get('unrealizedProfit', 0))
            
            leverage = float(new_position.get('leverage', 1))
            
            # Xác định hướng giao dịch
            side = "LONG" if new_qty > 0 else "SHORT"
            emoji = "🟢" if side == "LONG" else "🔴"
            
            # Lấy giá hiện tại
            current_price = float(new_position.get('markPrice', 0)) or self.market_data.get(symbol, 0)
            
            # Tính lợi nhuận
            if side == "LONG":
                profit_percent = (current_price - new_entry) / new_entry * 100 * leverage
            else:
                profit_percent = (new_entry - current_price) / new_entry * 100 * leverage
                
            profit_icon = "📈" if profit_percent > 0 else "📉"
            profit_change = new_profit - old_profit
            profit_change_icon = "📈" if profit_change > 0 else "📉"
            
            # Xác định loại cập nhật
            if abs(new_qty) > abs(old_qty):
                update_type = "🔼 TĂNG VỊ THẾ"
            elif abs(new_qty) < abs(old_qty):
                update_type = "🔽 GIẢM VỊ THẾ"
            else:
                update_type = "🔄 CẬP NHẬT VỊ THẾ"
            
            # Tạo thông báo
            message = f"{emoji} <b>{update_type} - {symbol} {side}</b> {emoji}\n\n"
            
            # Chi tiết thay đổi
            message += "<b>THAY ĐỔI</b>\n"
            message += f"📊 <b>Số lượng:</b> {abs(old_qty):.4f} → {abs(new_qty):.4f}\n"
            message += f"💰 <b>Giá vào:</b> {old_entry:.4f} → {new_entry:.4f}\n"
            message += f"{profit_change_icon} <b>Thay đổi lợi nhuận:</b> {profit_change:.2f} USDT\n\n"
            
            # Thông tin hiện tại
            message += "<b>TRẠNG THÁI HIỆN TẠI</b>\n"
            message += f"💵 <b>Giá hiện tại:</b> {current_price:.4f}\n"
            message += f"{profit_icon} <b>Lợi nhuận:</b> {profit_percent:.2f}% ({new_profit:.2f} USDT)\n"
            
            # Thêm phân tích nếu có
            analysis = self._get_symbol_analysis(symbol)
            if analysis:
                message += "\n<b>PHÂN TÍCH KỸ THUẬT</b>\n"
                message += f"📊 <b>Xu hướng:</b> {analysis.get('trend', 'N/A')}\n"
                message += f"🎯 <b>Mục tiêu:</b> {analysis.get('target_price', 'N/A')}\n"
                message += f"🛑 <b>Stop Loss:</b> {analysis.get('stop_loss', 'N/A')}\n"
            
            # Thêm thông tin trailing stop nếu có
            if symbol in self.trailing_stops:
                stop_info = self.trailing_stops[symbol]
                message += f"\n<b>TRAILING STOP</b>\n"
                message += f"⚙️ <b>Trạng thái:</b> {stop_info.get('status', 'N/A')}\n"
                message += f"💹 <b>Giá kích hoạt:</b> {stop_info.get('activation_price', 'N/A')}\n"
                message += f"📉 <b>Callback Rate:</b> {stop_info.get('callback_rate', 'N/A')}%\n"
            
            # Thêm thông tin thời gian
            message += f"\n<i>⏱️ {datetime.datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            return message
        except Exception as e:
            logger.error(f"Lỗi khi tạo thông báo cập nhật vị thế: {str(e)}")
            return f"<b>🔔 CẬP NHẬT VỊ THẾ - {symbol}</b>\n\nVị thế của {symbol} đã được cập nhật.\nXem chi tiết trong ứng dụng."
    
    def send_position_closed_notification(self, symbol: str, position: Dict) -> bool:
        """
        Gửi thông báo đóng vị thế
        
        Args:
            symbol (str): Ký hiệu cặp giao dịch
            position (Dict): Thông tin vị thế
            
        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            if not self._check_notification_enabled('trade_signal'):
                return False
                
            logger.info(f"Đang gửi thông báo đóng vị thế cho {symbol}")
            
            # Tạo nội dung thông báo
            message = self._create_position_closed_message(symbol, position)
            
            # Gửi thông báo
            result = self.telegram.send_message(message, parse_mode="HTML")
            
            if result:
                logger.info(f"Đã gửi thông báo đóng vị thế cho {symbol}")
                return True
            else:
                logger.error(f"Lỗi khi gửi thông báo đóng vị thế cho {symbol}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo đóng vị thế: {str(e)}")
            return False
    
    def _create_position_closed_message(self, symbol: str, position: Dict) -> str:
        """
        Tạo nội dung thông báo đóng vị thế
        
        Args:
            symbol (str): Ký hiệu cặp giao dịch
            position (Dict): Thông tin vị thế
            
        Returns:
            str: Nội dung thông báo
        """
        try:
            # Lấy thông tin cơ bản
            entry_price = float(position.get('entryPrice', 0))
            qty = float(position.get('positionAmt', 0))
            leverage = float(position.get('leverage', 1))
            
            # Xác định hướng giao dịch
            side = "LONG" if qty > 0 else "SHORT"
            
            # Lấy giá đóng (giá hiện tại)
            exit_price = float(position.get('markPrice', 0)) or self.market_data.get(symbol, 0)
            
            # Tính lợi nhuận
            if side == "LONG":
                profit_percent = (exit_price - entry_price) / entry_price * 100 * leverage
            else:
                profit_percent = (entry_price - exit_price) / entry_price * 100 * leverage
                
            estimated_profit = abs(qty) * entry_price * profit_percent / 100
                
            # Xác định biểu tượng dựa trên lợi nhuận
            if profit_percent > 0:
                result_emoji = "✅"
                result_text = "THÀNH CÔNG"
            else:
                result_emoji = "❌"
                result_text = "LỖ"
            
            # Tạo thông báo
            message = f"{result_emoji} <b>ĐÓNG VỊ THẾ {result_text} - {symbol} {side}</b> {result_emoji}\n\n"
            
            message += "<b>CHI TIẾT GIAO DỊCH</b>\n"
            message += f"📊 <b>Số lượng:</b> {abs(qty):.4f}\n"
            message += f"💰 <b>Giá vào:</b> {entry_price:.4f}\n"
            message += f"💵 <b>Giá ra:</b> {exit_price:.4f}\n"
            message += f"🔄 <b>Đòn bẩy:</b> {leverage}x\n"
            
            if profit_percent > 0:
                message += f"📈 <b>Lợi nhuận:</b> +{profit_percent:.2f}% (+{estimated_profit:.2f} USDT)\n\n"
            else:
                message += f"📉 <b>Lợi nhuận:</b> {profit_percent:.2f}% ({estimated_profit:.2f} USDT)\n\n"
            
            # Thêm phân tích thị trường hiện tại
            analysis = self._get_symbol_analysis(symbol)
            if analysis:
                message += "<b>PHÂN TÍCH THỊ TRƯỜNG HIỆN TẠI</b>\n"
                message += f"📊 <b>Xu hướng:</b> {analysis.get('trend', 'N/A')}\n"
                message += f"🔍 <b>Tín hiệu:</b> {analysis.get('signal', 'N/A')}\n"
                message += f"📝 <b>Ghi chú:</b> {analysis.get('note', 'N/A')}\n\n"
            
            # Thêm thông tin thời gian
            message += f"<i>⏱️ {datetime.datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            return message
        except Exception as e:
            logger.error(f"Lỗi khi tạo thông báo đóng vị thế: {str(e)}")
            return f"<b>🔔 ĐÓNG VỊ THẾ - {symbol}</b>\n\nVị thế của {symbol} đã được đóng.\nXem chi tiết trong ứng dụng."
    
    def send_new_trailing_stop_notification(self, symbol: str, stop_info: Dict) -> bool:
        """
        Gửi thông báo trailing stop mới
        
        Args:
            symbol (str): Ký hiệu cặp giao dịch
            stop_info (Dict): Thông tin trailing stop
            
        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            if not self._check_notification_enabled('trailing_stop'):
                return False
                
            if not self._check_cooldown('trailing_stop'):
                logger.info(f"Bỏ qua thông báo trailing stop mới cho {symbol} do đang trong thời gian chờ")
                return False
                
            logger.info(f"Đang gửi thông báo trailing stop mới cho {symbol}")
            
            # Tạo nội dung thông báo
            message = self._create_new_trailing_stop_message(symbol, stop_info)
            
            # Gửi thông báo
            result = self.telegram.send_message(message, parse_mode="HTML")
            
            if result:
                logger.info(f"Đã gửi thông báo trailing stop mới cho {symbol}")
                return True
            else:
                logger.error(f"Lỗi khi gửi thông báo trailing stop mới cho {symbol}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo trailing stop mới: {str(e)}")
            return False
    
    def _create_new_trailing_stop_message(self, symbol: str, stop_info: Dict) -> str:
        """
        Tạo nội dung thông báo trailing stop mới
        
        Args:
            symbol (str): Ký hiệu cặp giao dịch
            stop_info (Dict): Thông tin trailing stop
            
        Returns:
            str: Nội dung thông báo
        """
        try:
            # Lấy thông tin trailing stop
            status = stop_info.get('status', 'Đang chờ')
            activation_price = float(stop_info.get('activation_price', 0))
            callback_rate = float(stop_info.get('callback_rate', 0))
            current_price = float(stop_info.get('current_price', 0)) or self.market_data.get(symbol, 0)
            
            # Lấy thông tin vị thế nếu có
            position = self.active_positions.get(symbol, {})
            side = "LONG" if float(position.get('positionAmt', 0)) > 0 else "SHORT"
            emoji = "🟢" if side == "LONG" else "🔴"
            
            # Tạo thông báo
            message = f"🔔 <b>TRAILING STOP MỚI - {symbol} {side}</b>\n\n"
            
            message += "<b>CẤU HÌNH TRAILING STOP</b>\n"
            message += f"⚙️ <b>Trạng thái:</b> {status}\n"
            message += f"💹 <b>Giá kích hoạt:</b> {activation_price:.4f}\n"
            message += f"📉 <b>Callback Rate:</b> {callback_rate:.2f}%\n"
            message += f"💵 <b>Giá hiện tại:</b> {current_price:.4f}\n\n"
            
            # Thêm thông tin vị thế nếu có
            if position:
                entry_price = float(position.get('entryPrice', 0))
                qty = float(position.get('positionAmt', 0))
                leverage = float(position.get('leverage', 1))
                
                # Tính lợi nhuận
                if side == "LONG":
                    profit_percent = (current_price - entry_price) / entry_price * 100 * leverage
                    distance_percent = (activation_price - current_price) / current_price * 100
                else:
                    profit_percent = (entry_price - current_price) / entry_price * 100 * leverage
                    distance_percent = (current_price - activation_price) / current_price * 100
                    
                profit_icon = "📈" if profit_percent > 0 else "📉"
                
                message += f"{emoji} <b>THÔNG TIN VỊ THẾ</b>\n"
                message += f"📊 <b>Số lượng:</b> {abs(qty):.4f}\n"
                message += f"💰 <b>Giá vào:</b> {entry_price:.4f}\n"
                message += f"{profit_icon} <b>Lợi nhuận hiện tại:</b> {profit_percent:.2f}%\n"
                message += f"📏 <b>Khoảng cách đến kích hoạt:</b> {distance_percent:.2f}%\n\n"
            
            # Thêm phân tích nếu có
            analysis = self._get_symbol_analysis(symbol)
            if analysis:
                message += "<b>PHÂN TÍCH KỸ THUẬT</b>\n"
                message += f"📊 <b>Xu hướng:</b> {analysis.get('trend', 'N/A')}\n"
                message += f"🎯 <b>Mục tiêu:</b> {analysis.get('target_price', 'N/A')}\n\n"
            
            # Thêm thông tin thời gian
            message += f"<i>⏱️ {datetime.datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            return message
        except Exception as e:
            logger.error(f"Lỗi khi tạo thông báo trailing stop mới: {str(e)}")
            return f"<b>🔔 TRAILING STOP MỚI - {symbol}</b>\n\nĐã thiết lập trailing stop mới cho {symbol}.\nXem chi tiết trong ứng dụng."
    
    def send_trailing_stop_update_notification(self, symbol: str, old_stop: Dict, new_stop: Dict) -> bool:
        """
        Gửi thông báo cập nhật trailing stop
        
        Args:
            symbol (str): Ký hiệu cặp giao dịch
            old_stop (Dict): Thông tin trailing stop cũ
            new_stop (Dict): Thông tin trailing stop mới
            
        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            if not self._check_notification_enabled('trailing_stop'):
                return False
                
            if not self._check_cooldown('trailing_stop'):
                logger.info(f"Bỏ qua thông báo cập nhật trailing stop cho {symbol} do đang trong thời gian chờ")
                return False
                
            logger.info(f"Đang gửi thông báo cập nhật trailing stop cho {symbol}")
            
            # Tạo nội dung thông báo
            message = self._create_trailing_stop_update_message(symbol, old_stop, new_stop)
            
            # Gửi thông báo
            result = self.telegram.send_message(message, parse_mode="HTML")
            
            if result:
                logger.info(f"Đã gửi thông báo cập nhật trailing stop cho {symbol}")
                return True
            else:
                logger.error(f"Lỗi khi gửi thông báo cập nhật trailing stop cho {symbol}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo cập nhật trailing stop: {str(e)}")
            return False
    
    def _create_trailing_stop_update_message(self, symbol: str, old_stop: Dict, new_stop: Dict) -> str:
        """
        Tạo nội dung thông báo cập nhật trailing stop
        
        Args:
            symbol (str): Ký hiệu cặp giao dịch
            old_stop (Dict): Thông tin trailing stop cũ
            new_stop (Dict): Thông tin trailing stop mới
            
        Returns:
            str: Nội dung thông báo
        """
        try:
            # Lấy thông tin trailing stop
            old_status = old_stop.get('status', 'Đang chờ')
            new_status = new_stop.get('status', 'Đang chờ')
            
            old_activation = float(old_stop.get('activation_price', 0))
            new_activation = float(new_stop.get('activation_price', 0))
            
            old_callback = float(old_stop.get('callback_rate', 0))
            new_callback = float(new_stop.get('callback_rate', 0))
            
            old_price = float(old_stop.get('current_price', 0))
            new_price = float(new_stop.get('current_price', 0)) or self.market_data.get(symbol, 0)
            
            # Lấy thông tin vị thế nếu có
            position = self.active_positions.get(symbol, {})
            side = "LONG" if float(position.get('positionAmt', 0)) > 0 else "SHORT"
            emoji = "🟢" if side == "LONG" else "🔴"
            
            # Xác định loại cập nhật
            if old_status != new_status and new_status == "Đã kích hoạt":
                update_type = "🚨 TRAILING STOP ĐÃ KÍCH HOẠT"
            elif old_status != new_status:
                update_type = "🔄 TRẠNG THÁI TRAILING STOP ĐÃ THAY ĐỔI"
            elif old_activation != new_activation:
                update_type = "🔄 GIÁ KÍCH HOẠT ĐÃ THAY ĐỔI"
            elif old_callback != new_callback:
                update_type = "🔄 CALLBACK RATE ĐÃ THAY ĐỔI"
            else:
                update_type = "🔄 CẬP NHẬT TRAILING STOP"
            
            # Tạo thông báo
            message = f"{emoji} <b>{update_type} - {symbol} {side}</b>\n\n"
            
            # Chi tiết thay đổi
            message += "<b>THAY ĐỔI</b>\n"
            
            if old_status != new_status:
                message += f"⚙️ <b>Trạng thái:</b> {old_status} → {new_status}\n"
                
            if old_activation != new_activation:
                message += f"💹 <b>Giá kích hoạt:</b> {old_activation:.4f} → {new_activation:.4f}\n"
                
            if old_callback != new_callback:
                message += f"📉 <b>Callback Rate:</b> {old_callback:.2f}% → {new_callback:.2f}%\n"
                
            message += f"💵 <b>Giá thị trường:</b> {old_price:.4f} → {new_price:.4f}\n\n"
            
            # Thêm thông tin vị thế nếu có
            if position:
                entry_price = float(position.get('entryPrice', 0))
                qty = float(position.get('positionAmt', 0))
                leverage = float(position.get('leverage', 1))
                
                # Tính lợi nhuận
                if side == "LONG":
                    profit_percent = (new_price - entry_price) / entry_price * 100 * leverage
                    if new_status == "Đã kích hoạt":
                        trailing_price = new_price * (1 - new_callback/100) if side == "LONG" else new_price * (1 + new_callback/100)
                    else:
                        trailing_price = None
                else:
                    profit_percent = (entry_price - new_price) / entry_price * 100 * leverage
                    if new_status == "Đã kích hoạt":
                        trailing_price = new_price * (1 + new_callback/100) if side == "SHORT" else new_price * (1 - new_callback/100)
                    else:
                        trailing_price = None
                    
                profit_icon = "📈" if profit_percent > 0 else "📉"
                
                message += f"{emoji} <b>THÔNG TIN VỊ THẾ</b>\n"
                message += f"📊 <b>Số lượng:</b> {abs(qty):.4f}\n"
                message += f"💰 <b>Giá vào:</b> {entry_price:.4f}\n"
                message += f"{profit_icon} <b>Lợi nhuận hiện tại:</b> {profit_percent:.2f}%\n"
                
                if trailing_price:
                    message += f"🎯 <b>Giá trailing stop:</b> {trailing_price:.4f}\n\n"
                else:
                    message += "\n"
            
            # Thêm phân tích nếu có
            analysis = self._get_symbol_analysis(symbol)
            if analysis:
                message += "<b>PHÂN TÍCH KỸ THUẬT</b>\n"
                message += f"📊 <b>Xu hướng:</b> {analysis.get('trend', 'N/A')}\n"
                message += f"🎯 <b>Mục tiêu:</b> {analysis.get('target_price', 'N/A')}\n\n"
            
            # Thêm thông tin thời gian
            message += f"<i>⏱️ {datetime.datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            return message
        except Exception as e:
            logger.error(f"Lỗi khi tạo thông báo cập nhật trailing stop: {str(e)}")
            return f"<b>🔔 CẬP NHẬT TRAILING STOP - {symbol}</b>\n\nTrailing stop cho {symbol} đã được cập nhật.\nXem chi tiết trong ứng dụng."
    
    def send_trailing_stop_removed_notification(self, symbol: str, stop_info: Dict) -> bool:
        """
        Gửi thông báo xóa trailing stop
        
        Args:
            symbol (str): Ký hiệu cặp giao dịch
            stop_info (Dict): Thông tin trailing stop
            
        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            if not self._check_notification_enabled('trailing_stop'):
                return False
                
            logger.info(f"Đang gửi thông báo xóa trailing stop cho {symbol}")
            
            # Tạo nội dung thông báo
            message = self._create_trailing_stop_removed_message(symbol, stop_info)
            
            # Gửi thông báo
            result = self.telegram.send_message(message, parse_mode="HTML")
            
            if result:
                logger.info(f"Đã gửi thông báo xóa trailing stop cho {symbol}")
                return True
            else:
                logger.error(f"Lỗi khi gửi thông báo xóa trailing stop cho {symbol}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo xóa trailing stop: {str(e)}")
            return False
    
    def _create_trailing_stop_removed_message(self, symbol: str, stop_info: Dict) -> str:
        """
        Tạo nội dung thông báo xóa trailing stop
        
        Args:
            symbol (str): Ký hiệu cặp giao dịch
            stop_info (Dict): Thông tin trailing stop
            
        Returns:
            str: Nội dung thông báo
        """
        try:
            # Lấy thông tin trailing stop
            status = stop_info.get('status', 'Đang chờ')
            activation_price = float(stop_info.get('activation_price', 0))
            callback_rate = float(stop_info.get('callback_rate', 0))
            
            # Lấy thông tin vị thế nếu có
            position = self.active_positions.get(symbol, {})
            if position:
                side = "LONG" if float(position.get('positionAmt', 0)) > 0 else "SHORT"
                emoji = "🟢" if side == "LONG" else "🔴"
            else:
                side = "N/A"
                emoji = "⚪"
            
            # Tạo thông báo
            message = f"🚫 <b>TRAILING STOP ĐÃ XÓA - {symbol} {side}</b>\n\n"
            
            message += "<b>THÔNG TIN TRAILING STOP ĐÃ XÓA</b>\n"
            message += f"⚙️ <b>Trạng thái:</b> {status}\n"
            message += f"💹 <b>Giá kích hoạt:</b> {activation_price:.4f}\n"
            message += f"📉 <b>Callback Rate:</b> {callback_rate:.2f}%\n\n"
            
            # Thêm thông tin hiện tại của thị trường
            current_price = self.market_data.get(symbol, 0)
            if current_price:
                message += f"💵 <b>Giá hiện tại:</b> {current_price:.4f}\n\n"
            
            # Thêm phân tích nếu có
            analysis = self._get_symbol_analysis(symbol)
            if analysis:
                message += "<b>PHÂN TÍCH KỸ THUẬT</b>\n"
                message += f"📊 <b>Xu hướng:</b> {analysis.get('trend', 'N/A')}\n"
                message += f"🎯 <b>Mục tiêu:</b> {analysis.get('target_price', 'N/A')}\n\n"
            
            # Thêm thông tin thời gian
            message += f"<i>⏱️ {datetime.datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            return message
        except Exception as e:
            logger.error(f"Lỗi khi tạo thông báo xóa trailing stop: {str(e)}")
            return f"<b>🔔 XÓA TRAILING STOP - {symbol}</b>\n\nTrailing stop cho {symbol} đã bị xóa.\nXem chi tiết trong ứng dụng."
    
    def send_market_alert(self, symbol: str, alert_type: str, alert_data: Dict) -> bool:
        """
        Gửi cảnh báo thị trường
        
        Args:
            symbol (str): Ký hiệu cặp giao dịch
            alert_type (str): Loại cảnh báo (price, volatility, trend, ...)
            alert_data (Dict): Dữ liệu cảnh báo
            
        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            if not self._check_notification_enabled('market_alert'):
                return False
                
            if not self._check_cooldown('market_alert'):
                logger.info(f"Bỏ qua cảnh báo thị trường cho {symbol} do đang trong thời gian chờ")
                return False
                
            logger.info(f"Đang gửi cảnh báo thị trường cho {symbol}, loại: {alert_type}")
            
            # Tạo nội dung thông báo
            message = self._create_market_alert_message(symbol, alert_type, alert_data)
            
            # Gửi thông báo
            result = self.telegram.send_message(message, parse_mode="HTML")
            
            if result:
                logger.info(f"Đã gửi cảnh báo thị trường cho {symbol}")
                return True
            else:
                logger.error(f"Lỗi khi gửi cảnh báo thị trường cho {symbol}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi cảnh báo thị trường: {str(e)}")
            return False
    
    def _create_market_alert_message(self, symbol: str, alert_type: str, alert_data: Dict) -> str:
        """
        Tạo nội dung thông báo cảnh báo thị trường
        
        Args:
            symbol (str): Ký hiệu cặp giao dịch
            alert_type (str): Loại cảnh báo (price, volatility, trend, ...)
            alert_data (Dict): Dữ liệu cảnh báo
            
        Returns:
            str: Nội dung thông báo
        """
        try:
            # Xác định loại cảnh báo và biểu tượng
            alert_title = ""
            alert_emoji = ""
            
            if alert_type == "price":
                alert_title = "CẢNH BÁO GIÁ"
                alert_emoji = "💰"
            elif alert_type == "volatility":
                alert_title = "CẢNH BÁO BIẾN ĐỘNG"
                alert_emoji = "📊"
            elif alert_type == "trend":
                alert_title = "CẢNH BÁO XU HƯỚNG"
                alert_emoji = "📈"
            elif alert_type == "volume":
                alert_title = "CẢNH BÁO KHỐI LƯỢNG"
                alert_emoji = "📦"
            elif alert_type == "breakout":
                alert_title = "CẢNH BÁO BREAKOUT"
                alert_emoji = "🚀"
            elif alert_type == "support_resistance":
                alert_title = "CẢNH BÁO HỖ TRỢ/KHÁNG CỰ"
                alert_emoji = "🧱"
            else:
                alert_title = "CẢNH BÁO THỊ TRƯỜNG"
                alert_emoji = "⚠️"
            
            # Tạo thông báo
            message = f"{alert_emoji} <b>{alert_title} - {symbol}</b> {alert_emoji}\n\n"
            
            # Nội dung cảnh báo
            message += f"<b>{alert_data.get('title', 'Thông tin cảnh báo')}</b>\n"
            message += f"{alert_data.get('description', 'Không có mô tả')}\n\n"
            
            # Thông tin chi tiết
            message += "<b>CHI TIẾT</b>\n"
            
            for key, value in alert_data.get('details', {}).items():
                if key not in ['title', 'description']:
                    message += f"• <b>{key}:</b> {value}\n"
            
            message += "\n"
            
            # Lấy thông tin vị thế nếu có
            if symbol in self.active_positions:
                position = self.active_positions[symbol]
                side = "LONG" if float(position.get('positionAmt', 0)) > 0 else "SHORT"
                emoji = "🟢" if side == "LONG" else "🔴"
                
                message += f"{emoji} <b>VỊ THẾ ĐANG MỞ</b>\n"
                message += f"📊 <b>Loại:</b> {side}\n"
                message += f"💰 <b>Giá vào:</b> {float(position.get('entryPrice', 0)):.4f}\n"
                message += f"📏 <b>Số lượng:</b> {abs(float(position.get('positionAmt', 0))):.4f}\n\n"
            
            # Thêm khuyến nghị nếu có
            if 'recommendation' in alert_data:
                message += f"🔍 <b>KHUYẾN NGHỊ</b>\n"
                message += f"{alert_data['recommendation']}\n\n"
            
            # Thêm thông tin thời gian
            message += f"<i>⏱️ {datetime.datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            return message
        except Exception as e:
            logger.error(f"Lỗi khi tạo thông báo cảnh báo thị trường: {str(e)}")
            return f"<b>⚠️ CẢNH BÁO THỊ TRƯỜNG - {symbol}</b>\n\n{alert_data.get('title', 'Có cảnh báo mới')}\n\nXem chi tiết trong ứng dụng."
    
    def send_no_trade_reasons(self, symbol: str, timeframe: str = "1h", direction: str = "long") -> bool:
        """
        Gửi thông báo lý do không giao dịch
        
        Args:
            symbol (str): Ký hiệu cặp giao dịch
            timeframe (str): Khung thời gian
            direction (str): Hướng giao dịch (long/short)
            
        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            if not self._check_notification_enabled('no_trade_reasons'):
                return False
                
            if not self._check_cooldown('no_trade_reasons'):
                logger.info(f"Bỏ qua thông báo lý do không giao dịch cho {symbol} do đang trong thời gian chờ")
                return False
                
            logger.info(f"Đang gửi thông báo lý do không giao dịch cho {symbol} ({timeframe}, {direction})")
            
            # Phân tích lý do không giao dịch
            analysis = self.no_trade_analyzer.analyze_no_trade_reasons(symbol, timeframe, direction)
            
            # Tạo nội dung thông báo
            message = self._create_no_trade_reasons_message(symbol, timeframe, direction, analysis)
            
            # Gửi thông báo
            result = self.telegram.send_message(message, parse_mode="HTML")
            
            if result:
                logger.info(f"Đã gửi thông báo lý do không giao dịch cho {symbol}")
                return True
            else:
                logger.error(f"Lỗi khi gửi thông báo lý do không giao dịch cho {symbol}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo lý do không giao dịch: {str(e)}")
            return False
    
    def _create_no_trade_reasons_message(self, symbol: str, timeframe: str, direction: str, analysis: Dict) -> str:
        """
        Tạo nội dung thông báo lý do không giao dịch
        
        Args:
            symbol (str): Ký hiệu cặp giao dịch
            timeframe (str): Khung thời gian
            direction (str): Hướng giao dịch (long/short)
            analysis (Dict): Kết quả phân tích
            
        Returns:
            str: Nội dung thông báo
        """
        try:
            # Xác định biểu tượng cho hướng giao dịch
            direction_emoji = "🟢" if direction.lower() == "long" else "🔴"
            direction_text = "LONG" if direction.lower() == "long" else "SHORT"
            
            # Tạo thông báo
            message = f"🔍 <b>LÝ DO KHÔNG GIAO DỊCH - {symbol} {direction_text} ({timeframe})</b>\n\n"
            
            # Lấy các lý do không giao dịch
            no_trade_reasons = analysis.get('no_trade_reasons', [])
            
            if not no_trade_reasons:
                message += "<i>Không tìm thấy lý do không giao dịch. Có thể thị trường đã đủ điều kiện để giao dịch.</i>\n\n"
            else:
                # Thêm các lý do không giao dịch
                message += f"<b>CÁC LÝ DO KHÔNG GIAO DỊCH ({len(no_trade_reasons)})</b>\n"
                
                for i, reason in enumerate(no_trade_reasons, 1):
                    message += f"{i}. {reason.get('reason', 'Không xác định')}\n"
                    
                    # Thêm chi tiết nếu có
                    details = reason.get('details', {})
                    if details:
                        for key, value in details.items():
                            message += f"   - {key}: {value}\n"
                
                message += "\n"
            
            # Thêm các điều kiện cần thiết để giao dịch
            required_conditions = analysis.get('required_conditions', [])
            
            if required_conditions:
                message += "<b>ĐIỀU KIỆN CẦN ĐỂ GIAO DỊCH</b>\n"
                
                for i, condition in enumerate(required_conditions, 1):
                    message += f"{i}. {condition.get('description', 'Không xác định')}\n"
                    message += f"   - Hiện tại: {condition.get('current_value', 'N/A')}\n"
                    message += f"   - Cần đạt: {condition.get('required_value', 'N/A')}\n"
                
                message += "\n"
            
            # Thêm phân tích thị trường hiện tại
            market_analysis = analysis.get('market_analysis', {})
            
            if market_analysis:
                message += "<b>PHÂN TÍCH THỊ TRƯỜNG HIỆN TẠI</b>\n"
                current_price = market_analysis.get('price', self.market_data.get(symbol, 0))
                
                message += f"💵 <b>Giá hiện tại:</b> {current_price:.4f}\n"
                message += f"📊 <b>Xu hướng:</b> {market_analysis.get('trend', 'N/A')}\n"
                message += f"📈 <b>RSI:</b> {market_analysis.get('rsi', 'N/A')}\n"
                message += f"📉 <b>MACD:</b> {market_analysis.get('macd', 'N/A')}\n"
                message += f"📊 <b>Bollinger Bands:</b> {market_analysis.get('bollinger', 'N/A')}\n\n"
            
            # Thêm thông tin thời gian
            message += f"<i>⏱️ {datetime.datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            return message
        except Exception as e:
            logger.error(f"Lỗi khi tạo thông báo lý do không giao dịch: {str(e)}")
            return f"<b>🔍 LÝ DO KHÔNG GIAO DỊCH - {symbol} {direction} ({timeframe})</b>\n\nKhông thể thực hiện phân tích chi tiết. Vui lòng kiểm tra trong ứng dụng."
    
    def send_system_status(self) -> bool:
        """
        Gửi thông báo trạng thái hệ thống
        
        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            if not self._check_notification_enabled('system_status'):
                return False
                
            if not self._check_cooldown('system_status'):
                logger.info("Bỏ qua thông báo trạng thái hệ thống do đang trong thời gian chờ")
                return False
                
            logger.info("Đang gửi thông báo trạng thái hệ thống")
            
            # Tạo nội dung thông báo
            message = self._create_system_status_message()
            
            # Gửi thông báo
            result = self.telegram.send_message(message, parse_mode="HTML")
            
            if result:
                logger.info("Đã gửi thông báo trạng thái hệ thống")
                return True
            else:
                logger.error("Lỗi khi gửi thông báo trạng thái hệ thống")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo trạng thái hệ thống: {str(e)}")
            return False
    
    def _create_system_status_message(self) -> str:
        """
        Tạo nội dung thông báo trạng thái hệ thống
        
        Returns:
            str: Nội dung thông báo
        """
        try:
            # Tạo thông báo
            message = "🤖 <b>BÁO CÁO TRẠNG THÁI HỆ THỐNG</b>\n\n"
            
            # Thông tin vị thế
            active_positions = len(self.active_positions)
            message += f"📊 <b>VỊ THẾ ĐANG MỞ:</b> {active_positions}\n"
            
            if active_positions > 0:
                message += "<b>Danh sách vị thế:</b>\n"
                
                for symbol, position in self.active_positions.items():
                    side = "LONG" if float(position.get('positionAmt', 0)) > 0 else "SHORT"
                    qty = abs(float(position.get('positionAmt', 0)))
                    entry = float(position.get('entryPrice', 0))
                    profit = float(position.get('unrealizedProfit', 0))
                    profit_emoji = "📈" if profit > 0 else "📉"
                    
                    message += f"  • {symbol} {side}: {qty:.4f} @ {entry:.4f} {profit_emoji} {profit:.2f} USDT\n"
                
                message += "\n"
            
            # Thông tin trailing stop
            active_stops = len(self.trailing_stops)
            message += f"🎯 <b>TRAILING STOP ĐANG HOẠT ĐỘNG:</b> {active_stops}\n"
            
            if active_stops > 0:
                message += "<b>Danh sách trailing stop:</b>\n"
                
                for symbol, stop in self.trailing_stops.items():
                    status = stop.get('status', 'Đang chờ')
                    activation = float(stop.get('activation_price', 0))
                    callback = float(stop.get('callback_rate', 0))
                    status_emoji = "✅" if status == "Đã kích hoạt" else "⏳"
                    
                    message += f"  • {symbol}: {status_emoji} {status}, Kích hoạt @ {activation:.4f}, Callback {callback:.2f}%\n"
                
                message += "\n"
            
            # Thông tin phân tích thị trường
            symbols_analyzed = len(self.market_data)
            message += f"📊 <b>CẶP GIAO DỊCH ĐANG PHÂN TÍCH:</b> {symbols_analyzed}\n\n"
            
            # Thông tin hệ thống
            start_time = self._get_system_start_time()
            uptime = self._get_system_uptime(start_time)
            
            message += f"⏱️ <b>THỜI GIAN HOẠT ĐỘNG:</b> {uptime}\n"
            message += f"🔌 <b>TRẠNG THÁI KẾT NỐI:</b> ✅ Hoạt động\n"
            message += f"💾 <b>BỘ NHỚ ĐÃ SỬ DỤNG:</b> {self._get_memory_usage()}MB\n"
            message += f"📟 <b>CPU ĐÃ SỬ DỤNG:</b> {self._get_cpu_usage()}%\n\n"
            
            # Thêm thông tin thời gian
            message += f"<i>⏱️ {datetime.datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            return message
        except Exception as e:
            logger.error(f"Lỗi khi tạo thông báo trạng thái hệ thống: {str(e)}")
            return "<b>🤖 BÁO CÁO TRẠNG THÁI HỆ THỐNG</b>\n\nHệ thống đang hoạt động, nhưng không thể tạo báo cáo chi tiết."
    
    def _get_system_start_time(self) -> datetime.datetime:
        """
        Lấy thời gian bắt đầu của hệ thống
        
        Returns:
            datetime.datetime: Thời gian bắt đầu
        """
        try:
            # Nếu có file pid, hãy kiểm tra thời gian tạo
            pid_files = [f for f in os.listdir('.') if f.endswith('.pid')]
            
            if pid_files:
                oldest_file = min(pid_files, key=lambda x: os.path.getctime(x))
                return datetime.datetime.fromtimestamp(os.path.getctime(oldest_file))
            
            # Nếu không có file pid, sử dụng thời gian hiện tại trừ 1 giờ
            return datetime.datetime.now() - datetime.timedelta(hours=1)
        except Exception as e:
            logger.error(f"Lỗi khi lấy thời gian bắt đầu hệ thống: {str(e)}")
            return datetime.datetime.now() - datetime.timedelta(hours=1)
    
    def _get_system_uptime(self, start_time: datetime.datetime = None) -> str:
        """
        Tính thời gian hoạt động của hệ thống
        
        Args:
            start_time (datetime.datetime): Thời gian bắt đầu
            
        Returns:
            str: Thời gian hoạt động định dạng
        """
        try:
            if not start_time:
                start_time = self._get_system_start_time()
                
            now = datetime.datetime.now()
            uptime = now - start_time
            
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if days > 0:
                return f"{days} ngày, {hours} giờ, {minutes} phút"
            elif hours > 0:
                return f"{hours} giờ, {minutes} phút"
            else:
                return f"{minutes} phút, {seconds} giây"
        except Exception as e:
            logger.error(f"Lỗi khi tính thời gian hoạt động: {str(e)}")
            return "Không xác định"
    
    def _get_memory_usage(self) -> float:
        """
        Lấy lượng bộ nhớ đã sử dụng
        
        Returns:
            float: Bộ nhớ đã sử dụng (MB)
        """
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            return memory_info.rss / 1024 / 1024  # Đổi từ byte sang MB
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin bộ nhớ: {str(e)}")
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """
        Lấy phần trăm CPU đã sử dụng
        
        Returns:
            float: Phần trăm CPU đã sử dụng
        """
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.cpu_percent(interval=0.1)
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin CPU: {str(e)}")
            return 0.0
    
    def _get_symbol_analysis(self, symbol: str) -> Dict:
        """
        Lấy thông tin phân tích cho một cặp giao dịch
        
        Args:
            symbol (str): Ký hiệu cặp giao dịch
            
        Returns:
            Dict: Thông tin phân tích
        """
        try:
            # Kiểm tra file recommendation
            symbol_lower = symbol.lower()
            recommendation_file = f"recommendation_{symbol_lower}.json"
            
            if os.path.exists(recommendation_file):
                with open(recommendation_file, 'r') as f:
                    return json.load(f)
            
            # Nếu không có file, trả về thông tin cơ bản
            return {
                'symbol': symbol,
                'trend': 'Không xác định',
                'signal': 'Không có tín hiệu',
                'target_price': 'Không xác định',
                'stop_loss': 'Không xác định',
                'note': 'Không có phân tích chi tiết'
            }
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin phân tích: {str(e)}")
            return {
                'symbol': symbol,
                'trend': 'Không xác định',
                'signal': 'Không có tín hiệu',
                'target_price': 'Không xác định',
                'stop_loss': 'Không xác định',
                'note': 'Lỗi khi đọc file phân tích'
            }
    
    def _check_notification_enabled(self, notification_type: str) -> bool:
        """
        Kiểm tra xem loại thông báo có được bật không
        
        Args:
            notification_type (str): Loại thông báo
            
        Returns:
            bool: True nếu được bật, False nếu không
        """
        if not self.notification_config.get('enabled', True):
            return False
            
        notification_types = self.notification_config.get('notification_types', {})
        return notification_types.get(notification_type, True)
    
    def send_all_symbol_analysis(self) -> bool:
        """
        Gửi phân tích tất cả các cặp giao dịch
        
        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            if not self._check_notification_enabled('system_status'):
                return False
                
            if not self._check_cooldown('system_status'):
                logger.info("Bỏ qua thông báo phân tích tất cả các cặp do đang trong thời gian chờ")
                return False
                
            logger.info("Đang gửi thông báo phân tích tất cả các cặp")
            
            # Lấy danh sách cặp giao dịch
            symbols = self._get_all_symbols()
            
            # Chia nhỏ thành các nhóm để tránh thông báo quá dài
            max_symbols_per_message = self.notification_config.get('max_symbols_per_message', 5)
            symbol_chunks = [symbols[i:i + max_symbols_per_message] for i in range(0, len(symbols), max_symbols_per_message)]
            
            success_count = 0
            
            for chunk in symbol_chunks:
                # Tạo nội dung thông báo
                message = self._create_all_symbol_analysis_message(chunk)
                
                # Gửi thông báo
                result = self.telegram.send_message(message, parse_mode="HTML")
                
                if result:
                    success_count += 1
                    logger.info(f"Đã gửi thông báo phân tích cho nhóm {chunk}")
                else:
                    logger.error(f"Lỗi khi gửi thông báo phân tích cho nhóm {chunk}")
                    
                # Chờ một chút để tránh spam
                time.sleep(1)
            
            if success_count == len(symbol_chunks):
                logger.info("Đã gửi thông báo phân tích tất cả các cặp")
                return True
            else:
                logger.warning(f"Chỉ gửi được {success_count}/{len(symbol_chunks)} thông báo phân tích")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo phân tích tất cả các cặp: {str(e)}")
            return False
    
    def _create_all_symbol_analysis_message(self, symbols: List[str]) -> str:
        """
        Tạo nội dung thông báo phân tích nhiều cặp giao dịch
        
        Args:
            symbols (List[str]): Danh sách cặp giao dịch
            
        Returns:
            str: Nội dung thông báo
        """
        try:
            # Tạo thông báo
            message = "📊 <b>PHÂN TÍCH NHIỀU CẶP GIAO DỊCH</b>\n\n"
            
            for symbol in symbols:
                # Lấy thông tin phân tích
                analysis = self._get_symbol_analysis(symbol)
                
                # Lấy giá hiện tại
                current_price = self.market_data.get(symbol, 0)
                
                # Xác định biểu tượng dựa trên tín hiệu
                signal = analysis.get('signal', 'NEUTRAL')
                if signal in ["BUY", "STRONG_BUY"]:
                    signal_emoji = "🟢"
                elif signal in ["SELL", "STRONG_SELL"]:
                    signal_emoji = "🔴"
                else:
                    signal_emoji = "⚪"
                
                # Thêm thông tin cho cặp giao dịch này
                message += f"{signal_emoji} <b>{symbol}</b>\n"
                message += f"💵 Giá: {current_price:.4f}\n"
                message += f"📊 Xu hướng: {analysis.get('trend', 'Không xác định')}\n"
                message += f"🔍 Tín hiệu: {analysis.get('signal', 'Không có tín hiệu')}\n"
                
                # Thêm mục tiêu và stop loss nếu có
                target_price = analysis.get('target_price', None)
                stop_loss = analysis.get('stop_loss', None)
                
                if target_price and target_price != 'Không xác định':
                    message += f"🎯 Mục tiêu: {target_price}\n"
                    
                if stop_loss and stop_loss != 'Không xác định':
                    message += f"🛑 Stop Loss: {stop_loss}\n"
                
                # Thêm ghi chú nếu có
                note = analysis.get('note', None)
                if note and note != 'Không có phân tích chi tiết':
                    message += f"📝 Ghi chú: {note}\n"
                
                message += "\n"
            
            # Thêm thông tin thời gian
            message += f"<i>⏱️ {datetime.datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            return message
        except Exception as e:
            logger.error(f"Lỗi khi tạo thông báo phân tích nhiều cặp: {str(e)}")
            return f"<b>📊 PHÂN TÍCH NHIỀU CẶP GIAO DỊCH</b>\n\nKhông thể tạo phân tích chi tiết cho: {', '.join(symbols)}"
    
    def _get_all_symbols(self) -> List[str]:
        """
        Lấy danh sách tất cả các cặp giao dịch từ file cấu hình
        
        Returns:
            List[str]: Danh sách các cặp giao dịch
        """
        try:
            # Thử đọc từ bot_config.json
            if os.path.exists('bot_config.json'):
                with open('bot_config.json', 'r') as f:
                    config = json.load(f)
                    if 'symbols' in config:
                        return config['symbols']
            
            # Thử đọc từ account_config.json
            if os.path.exists('account_config.json'):
                with open('account_config.json', 'r') as f:
                    config = json.load(f)
                    if 'symbols' in config:
                        return config['symbols']
            
            # Danh sách mặc định được hỗ trợ bởi Binance Testnet
            return [
                "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", 
                "XRPUSDT", "DOGEUSDT", "DOTUSDT", "AVAXUSDT", 
                "LINKUSDT", "LTCUSDT", "UNIUSDT", "ATOMUSDT"
            ]
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách cặp giao dịch: {str(e)}")
            # Danh sách cơ bản nếu có lỗi
            return [
                "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"
            ]
            
    def notify_entry(self, entry_data: Dict) -> bool:
        """
        Gửi thông báo khi vào lệnh
        
        Args:
            entry_data (Dict): Thông tin lệnh vào
            
        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            if not self._check_notification_enabled('trade_signal'):
                return False
                
            logger.info(f"Đang gửi thông báo vào lệnh cho {entry_data.get('symbol', 'Unknown')}")
            
            # Tạo thông báo dựa trên dữ liệu vào lệnh
            symbol = entry_data.get('symbol', 'Unknown')
            side = entry_data.get('side', 'LONG')
            entry_price = entry_data.get('entry_price', 0)
            quantity = entry_data.get('quantity', 0)
            leverage = entry_data.get('leverage', 1)
            take_profit = entry_data.get('take_profit', 0)
            stop_loss = entry_data.get('stop_loss', 0)
            entry_reason = entry_data.get('entry_reason', 'Tín hiệu kỹ thuật')
            
            # Xác định loại lệnh và emoji
            emoji = "🟢" if side == "LONG" else "🔴"
            
            # Tạo nội dung thông báo
            message = f"{emoji} <b>VÀO LỆNH - {symbol} {side}</b> {emoji}\n\n"
            message += f"💰 <b>Giá vào:</b> {entry_price:.4f}\n"
            message += f"📊 <b>Số lượng:</b> {abs(quantity):.4f}\n"
            message += f"🔄 <b>Đòn bẩy:</b> {leverage}x\n"
            message += f"🎯 <b>Take Profit:</b> {take_profit:.4f}\n"
            message += f"🛑 <b>Stop Loss:</b> {stop_loss:.4f}\n"
            message += f"📝 <b>Lý do vào lệnh:</b> {entry_reason}\n\n"
            
            # Thêm phân tích nếu có
            analysis = self._get_symbol_analysis(symbol)
            if analysis:
                message += "<b>PHÂN TÍCH KỸ THUẬT</b>\n"
                message += f"📊 <b>Xu hướng:</b> {analysis.get('trend', 'N/A')}\n"
                message += f"🔍 <b>Tín hiệu:</b> {analysis.get('signal', 'N/A')}\n"
                message += f"📈 <b>Risk/Reward:</b> {entry_data.get('risk_reward_ratio', 'N/A'):.2f}\n\n"
            
            # Thêm thông tin thời gian
            message += f"<i>⏱️ {datetime.datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            # Gửi thông báo
            result = self.telegram.send_message(message, parse_mode="HTML")
            
            if result:
                logger.info(f"Đã gửi thông báo vào lệnh cho {symbol}")
                
                # Lưu vị thế vào các vị thế đang mở
                position_data = {
                    'symbol': symbol,
                    'side': side,
                    'entry_price': entry_price,
                    'quantity': quantity,
                    'leverage': leverage,
                    'take_profit': take_profit,
                    'stop_loss': stop_loss,
                    'entry_time': datetime.datetime.now().isoformat(),
                    'entry_reason': entry_reason
                }
                self.active_positions[symbol] = position_data
                
                return True
            else:
                logger.error(f"Lỗi khi gửi thông báo vào lệnh cho {symbol}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi xử lý thông báo vào lệnh: {str(e)}")
            return False
    
    def notify_exit(self, exit_data: Dict) -> bool:
        """
        Gửi thông báo khi ra lệnh
        
        Args:
            exit_data (Dict): Thông tin lệnh ra
            
        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            if not self._check_notification_enabled('trade_signal'):
                return False
                
            logger.info(f"Đang gửi thông báo ra lệnh cho {exit_data.get('symbol', 'Unknown')}")
            
            # Tạo thông báo dựa trên dữ liệu ra lệnh
            symbol = exit_data.get('symbol', 'Unknown')
            side = exit_data.get('side', 'LONG')
            entry_price = exit_data.get('entry_price', 0)
            exit_price = exit_data.get('exit_price', 0)
            quantity = exit_data.get('quantity', 0)
            profit_loss = exit_data.get('profit_loss', 0)
            profit_loss_percent = exit_data.get('profit_loss_percent', 0)
            holding_time = exit_data.get('holding_time', 'N/A')
            exit_reason = exit_data.get('exit_reason', 'Tín hiệu thoát lệnh')
            
            # Xác định loại lệnh và emoji
            is_profit = profit_loss > 0
            result_emoji = "✅" if is_profit else "❌"
            result_text = "THÀNH CÔNG" if is_profit else "LỖ"
            side_emoji = "🟢" if side == "LONG" else "🔴"
            
            # Tạo nội dung thông báo
            message = f"{result_emoji} <b>RA LỆNH {result_text} - {symbol} {side}</b> {side_emoji}\n\n"
            
            message += "<b>CHI TIẾT GIAO DỊCH</b>\n"
            message += f"💰 <b>Giá vào:</b> {entry_price:.4f}\n"
            message += f"💵 <b>Giá ra:</b> {exit_price:.4f}\n"
            message += f"📊 <b>Số lượng:</b> {abs(quantity):.4f}\n"
            
            # Thêm thông tin lợi nhuận
            if is_profit:
                message += f"📈 <b>Lợi nhuận:</b> +{profit_loss:.2f} USDT (+{profit_loss_percent:.2f}%)\n"
            else:
                message += f"📉 <b>Lợi nhuận:</b> {profit_loss:.2f} USDT ({profit_loss_percent:.2f}%)\n"
                
            message += f"⏱️ <b>Thời gian giữ:</b> {holding_time}\n"
            message += f"📝 <b>Lý do ra lệnh:</b> {exit_reason}\n\n"
            
            # Thêm phân tích thị trường hiện tại
            analysis = self._get_symbol_analysis(symbol)
            if analysis:
                message += "<b>PHÂN TÍCH THỊ TRƯỜNG HIỆN TẠI</b>\n"
                message += f"📊 <b>Xu hướng:</b> {analysis.get('trend', 'N/A')}\n"
                message += f"🔍 <b>Tín hiệu:</b> {analysis.get('signal', 'N/A')}\n"
                message += f"📝 <b>Ghi chú:</b> {analysis.get('note', 'N/A')}\n\n"
            
            # Thêm thông tin thời gian
            message += f"<i>⏱️ {datetime.datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            # Gửi thông báo
            result = self.telegram.send_message(message, parse_mode="HTML")
            
            if result:
                logger.info(f"Đã gửi thông báo ra lệnh cho {symbol}")
                
                # Xóa vị thế khỏi các vị thế đang mở
                if symbol in self.active_positions:
                    del self.active_positions[symbol]
                
                return True
            else:
                logger.error(f"Lỗi khi gửi thông báo ra lệnh cho {symbol}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi xử lý thông báo ra lệnh: {str(e)}")
            return False
            
    def notify_market_analysis(self, analysis_data: Dict) -> bool:
        """
        Gửi thông báo phân tích thị trường
        
        Args:
            analysis_data (Dict): Dữ liệu phân tích thị trường
            
        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            if not self._check_notification_enabled('market_alert'):
                return False
                
            if not self._check_cooldown('market_alert'):
                return False
            
            symbol = analysis_data.get('symbol', 'Unknown')
            logger.info(f"Đang gửi thông báo phân tích thị trường cho {symbol}")
            
            # Tạo thông báo dựa trên dữ liệu phân tích
            trend = analysis_data.get('trend', 'NEUTRAL')
            signal = analysis_data.get('signal', 'NEUTRAL')
            price = analysis_data.get('price', 0)
            
            # Xác định biểu tượng dựa trên tín hiệu
            if signal in ["BUY", "STRONG_BUY"]:
                signal_emoji = "🟢"
                signal_text = "MUA" if signal == "BUY" else "MUA MẠNH"
            elif signal in ["SELL", "STRONG_SELL"]:
                signal_emoji = "🔴"
                signal_text = "BÁN" if signal == "SELL" else "BÁN MẠNH"
            else:
                signal_emoji = "⚪"
                signal_text = "TRUNG LẬP"
            
            # Tạo nội dung thông báo
            message = f"{signal_emoji} <b>PHÂN TÍCH THỊ TRƯỜNG - {symbol}</b>\n\n"
            
            message += f"💵 <b>Giá hiện tại:</b> {price:.4f}\n"
            message += f"📊 <b>Xu hướng:</b> {trend}\n"
            message += f"🔍 <b>Tín hiệu:</b> {signal_text}\n\n"
            
            # Thêm chi tiết chỉ báo nếu có
            indicators = analysis_data.get('indicators', {})
            if indicators:
                message += "<b>CHỈ BÁO KỸ THUẬT</b>\n"
                
                if 'rsi' in indicators:
                    rsi = indicators['rsi']
                    rsi_status = "Quá bán (<30)" if rsi < 30 else "Quá mua (>70)" if rsi > 70 else "Trung tính"
                    message += f"📉 <b>RSI:</b> {rsi:.2f} - {rsi_status}\n"
                
                if 'macd' in indicators:
                    macd = indicators['macd']
                    macd_signal = indicators.get('macd_signal', 0)
                    macd_status = "Tích cực" if macd > macd_signal else "Tiêu cực"
                    message += f"📊 <b>MACD:</b> {macd:.2f} - {macd_status}\n"
                
                if 'ema50' in indicators and 'ema200' in indicators:
                    ema50 = indicators['ema50']
                    ema200 = indicators['ema200']
                    ema_status = "Xu hướng tăng" if ema50 > ema200 else "Xu hướng giảm"
                    message += f"📈 <b>EMA50/200:</b> {ema_status}\n"
                
                if 'bb_upper' in indicators and 'bb_lower' in indicators:
                    bb_upper = indicators['bb_upper']
                    bb_lower = indicators['bb_lower']
                    bb_width = (bb_upper - bb_lower) / price * 100
                    message += f"📏 <b>BB Width:</b> {bb_width:.2f}%\n\n"
            
            # Thêm khuyến nghị nếu có
            recommendation = analysis_data.get('recommendation', {})
            if recommendation:
                message += "<b>KHUYẾN NGHỊ</b>\n"
                
                action = recommendation.get('action', 'WAIT')
                reason = recommendation.get('reason', 'Chờ đợi tín hiệu rõ ràng hơn')
                target = recommendation.get('target', 'N/A')
                stop = recommendation.get('stop', 'N/A')
                
                message += f"🎯 <b>Hành động:</b> {action}\n"
                message += f"📝 <b>Lý do:</b> {reason}\n"
                
                if target != 'N/A':
                    message += f"💹 <b>Mục tiêu:</b> {target}\n"
                
                if stop != 'N/A':
                    message += f"🛑 <b>Stop:</b> {stop}\n\n"
            
            # Thêm thông tin các vị thế đang mở cho cặp này nếu có
            if symbol in self.active_positions:
                position = self.active_positions[symbol]
                side = position.get('side', 'LONG')
                entry_price = position.get('entry_price', 0)
                side_emoji = "🟢" if side == "LONG" else "🔴"
                
                message += f"{side_emoji} <b>VỊ THẾ ĐANG MỞ</b>\n"
                message += f"⚙️ <b>Loại:</b> {side}\n"
                message += f"💰 <b>Giá vào:</b> {entry_price:.4f}\n"
                
                # Tính lợi nhuận
                current_profit = 0
                if side == "LONG":
                    current_profit = (price - entry_price) / entry_price * 100
                else:
                    current_profit = (entry_price - price) / entry_price * 100
                
                profit_emoji = "📈" if current_profit > 0 else "📉"
                message += f"{profit_emoji} <b>P/L Hiện tại:</b> {current_profit:.2f}%\n\n"
            
            # Thêm thông tin thời gian
            message += f"<i>⏱️ {datetime.datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            # Gửi thông báo
            result = self.telegram.send_message(message, parse_mode="HTML")
            
            if result:
                logger.info(f"Đã gửi thông báo phân tích thị trường cho {symbol}")
                return True
            else:
                logger.error(f"Lỗi khi gửi thông báo phân tích thị trường cho {symbol}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi xử lý thông báo phân tích thị trường: {str(e)}")
            return False


if __name__ == "__main__":
    # Test module
    try:
        notifier = DetailedTradeNotifications()
        
        # Gửi thông báo trạng thái hệ thống
        notifier.send_system_status()
        
        # Gửi phân tích tất cả các cặp
        notifier.send_all_symbol_analysis()
        
        logger.info("Đã gửi các thông báo test")
    except Exception as e:
        logger.error(f"Lỗi khi chạy module test: {str(e)}")
        logger.error(traceback.format_exc())