#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module xử lý thông báo Telegram cho ứng dụng desktop
"""

import os
import json
import logging
import datetime
import traceback
import requests
import time
import hashlib
from typing import Dict, List, Any, Optional, Union

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("telegram_notifier")

class TelegramNotifier:
    """
    Lớp xử lý gửi thông báo đến Telegram
    """
    
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Khởi tạo TelegramNotifier
        
        :param token: Telegram Bot Token
        :param chat_id: Telegram Chat ID
        """
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""
        self.enabled = bool(self.token and self.chat_id)
        
        # Cache lưu trữ thông báo gần đây để tránh spam
        self.recent_messages = {}
        self.message_cooldown = 300  # 5 phút (300 giây)
        
        # Lưu trữ dữ liệu thông báo trước đó để so sánh
        self.previous_system_status = None
        self.last_notification_time = {}
        
        # Kiểm tra cài đặt
        if not self.token:
            logger.warning("Thiếu Telegram Bot Token")
        
        if not self.chat_id:
            logger.warning("Thiếu Telegram Chat ID")
    
    def set_credentials(self, token: str, chat_id: str) -> Dict[str, Any]:
        """
        Thiết lập token và chat_id mới
        
        :param token: Telegram Bot Token mới
        :param chat_id: Telegram Chat ID mới
        :return: Kết quả kiểm tra kết nối
        """
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""
        self.enabled = bool(self.token and self.chat_id)
        
        # Kiểm tra kết nối
        return self.test_connection()
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Kiểm tra kết nối Telegram
        
        :return: Kết quả kiểm tra kết nối
        """
        if not self.enabled:
            return {
                "status": "error",
                "message": "Thiếu cấu hình Telegram (Bot Token hoặc Chat ID)"
            }
        
        try:
            # Gửi tin nhắn test
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"🔄 Kiểm tra kết nối Telegram thành công!\n⏱️ Thời gian: {current_time}"
            
            response = requests.get(
                f"{self.base_url}/sendMessage",
                params={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "HTML"
                }
            )
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "message": "Kết nối Telegram thành công"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Lỗi kết nối Telegram: {response.json().get('description', 'Lỗi không xác định')}"
                }
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra kết nối Telegram: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Lỗi khi kiểm tra kết nối Telegram: {str(e)}"
            }
    
    def _is_duplicate_message(self, message: str, notification_type: str) -> bool:
        """
        Kiểm tra tin nhắn đã gửi gần đây để tránh spam
        
        :param message: Nội dung tin nhắn
        :param notification_type: Loại thông báo
        :return: True nếu tin nhắn là trùng lặp trong khoảng thời gian cho phép
        """
        # Tạo mã hash đơn giản cho tin nhắn
        msg_hash = hashlib.md5(message.encode('utf-8')).hexdigest()
        
        # Lấy thời gian hiện tại
        current_time = time.time()
        
        # Kiểm tra trong cache tin nhắn gần đây
        if notification_type in self.recent_messages and msg_hash in self.recent_messages[notification_type]:
            last_time = self.recent_messages[notification_type][msg_hash]
            
            # Nếu tin nhắn đã gửi trong khoảng thời gian cooldown
            if current_time - last_time < self.message_cooldown:
                logger.info(f"Bỏ qua tin nhắn trùng lặp loại '{notification_type}' (gửi gần đây trong vòng {self.message_cooldown}s)")
                return True
        
        # Lưu tin nhắn vào cache
        if notification_type not in self.recent_messages:
            self.recent_messages[notification_type] = {}
            
        self.recent_messages[notification_type][msg_hash] = current_time
        return False
        
    def send_message(self, message: str, parse_mode: str = "HTML", notification_type: str = "general") -> Dict[str, Any]:
        """
        Gửi tin nhắn đến Telegram
        
        :param message: Nội dung tin nhắn
        :param parse_mode: Chế độ định dạng (HTML, Markdown, MarkdownV2)
        :param notification_type: Loại thông báo để kiểm tra trùng lặp
        :return: Kết quả gửi tin nhắn
        """
        if not self.enabled:
            logger.warning("Không thể gửi tin nhắn: Thiếu cấu hình Telegram")
            return {
                "status": "error",
                "message": "Thiếu cấu hình Telegram (Bot Token hoặc Chat ID)"
            }
        
        # Kiểm tra xem có phải là thông báo trùng lặp không
        if self._is_duplicate_message(message, notification_type):
            return {
                "status": "skipped",
                "message": "Bỏ qua tin nhắn trùng lặp để tránh spam"
            }
        
        try:
            response = requests.get(
                f"{self.base_url}/sendMessage",
                params={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": parse_mode
                }
            )
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "message": "Đã gửi tin nhắn thành công"
                }
            else:
                error_msg = response.json().get('description', 'Lỗi không xác định')
                logger.error(f"Lỗi khi gửi tin nhắn Telegram: {error_msg}")
                return {
                    "status": "error",
                    "message": f"Lỗi khi gửi tin nhắn Telegram: {error_msg}"
                }
        
        except Exception as e:
            logger.error(f"Lỗi khi gửi tin nhắn Telegram: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Lỗi khi gửi tin nhắn Telegram: {str(e)}"
            }
    
    def notify_position_opened(self, position_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Thông báo mở vị thế mới
        
        :param position_data: Dữ liệu vị thế
        :return: Kết quả gửi tin nhắn
        """
        try:
            # Lấy thông tin vị thế
            symbol = position_data.get("symbol", "Unknown")
            side = position_data.get("side", "Unknown")
            entry_price = position_data.get("entry_price", 0)
            amount = position_data.get("amount", 0)
            leverage = position_data.get("leverage", 1)
            stop_loss = position_data.get("stop_loss", 0)
            take_profit = position_data.get("take_profit", 0)
            
            # Định dạng tin nhắn
            message = (
                f"🚀 <b>ĐÃ MỞ VỊ THẾ MỚI</b>\n\n"
                f"📊 <b>Cặp giao dịch:</b> {symbol}\n"
                f"📈 <b>Hướng:</b> {'LONG 📈' if side.upper() == 'LONG' else 'SHORT 📉'}\n"
                f"💰 <b>Giá vào lệnh:</b> {entry_price}\n"
                f"📏 <b>Kích thước:</b> {amount} ({leverage}x)\n"
                f"🛑 <b>Stop Loss:</b> {stop_loss}\n"
                f"🎯 <b>Take Profit:</b> {take_profit}\n\n"
                f"⏱️ <b>Thời gian:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # Gửi tin nhắn
            return self.send_message(message)
        
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo mở vị thế: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Lỗi khi gửi thông báo mở vị thế: {str(e)}"
            }
    
    def notify_position_closed(self, position_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Thông báo đóng vị thế
        
        :param position_data: Dữ liệu vị thế
        :return: Kết quả gửi tin nhắn
        """
        try:
            # Lấy thông tin vị thế
            symbol = position_data.get("symbol", "Unknown")
            side = position_data.get("side", "Unknown")
            entry_price = position_data.get("entry_price", 0)
            exit_price = position_data.get("exit_price", 0)
            amount = position_data.get("amount", 0)
            profit_loss = position_data.get("profit_loss", 0)
            profit_percentage = position_data.get("profit_percentage", 0)
            duration = position_data.get("duration", "Unknown")
            close_reason = position_data.get("close_reason", "Manual")
            
            # Xác định emoji dựa trên kết quả
            result_emoji = "🟢" if profit_loss > 0 else "🔴"
            
            # Định dạng tin nhắn
            message = (
                f"{result_emoji} <b>ĐÃ ĐÓNG VỊ THẾ</b>\n\n"
                f"📊 <b>Cặp giao dịch:</b> {symbol}\n"
                f"📈 <b>Hướng:</b> {'LONG 📈' if side.upper() == 'LONG' else 'SHORT 📉'}\n"
                f"💰 <b>Giá vào lệnh:</b> {entry_price}\n"
                f"💰 <b>Giá ra lệnh:</b> {exit_price}\n"
                f"📏 <b>Kích thước:</b> {amount}\n"
                f"💵 <b>Lợi nhuận:</b> {profit_loss:.2f} USDT ({profit_percentage:.2f}%)\n"
                f"⏱️ <b>Thời gian nắm giữ:</b> {duration}\n"
                f"📝 <b>Lý do đóng:</b> {close_reason}\n\n"
                f"🕒 <b>Thời gian:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # Gửi tin nhắn
            return self.send_message(message)
        
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo đóng vị thế: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Lỗi khi gửi thông báo đóng vị thế: {str(e)}"
            }
    
    def notify_sl_tp_update(self, position_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Thông báo cập nhật SL/TP
        
        :param position_data: Dữ liệu vị thế
        :return: Kết quả gửi tin nhắn
        """
        try:
            # Lấy thông tin vị thế
            symbol = position_data.get("symbol", "Unknown")
            side = position_data.get("side", "Unknown")
            current_price = position_data.get("current_price", 0)
            old_sl = position_data.get("old_sl", 0)
            old_tp = position_data.get("old_tp", 0)
            new_sl = position_data.get("new_sl", 0)
            new_tp = position_data.get("new_tp", 0)
            
            # Định dạng tin nhắn
            message = (
                f"🔄 <b>CẬP NHẬT SL/TP</b>\n\n"
                f"📊 <b>Cặp giao dịch:</b> {symbol}\n"
                f"📈 <b>Hướng:</b> {'LONG 📈' if side.upper() == 'LONG' else 'SHORT 📉'}\n"
                f"💰 <b>Giá hiện tại:</b> {current_price}\n"
                f"🛑 <b>Stop Loss cũ:</b> {old_sl} ➡️ <b>Stop Loss mới:</b> {new_sl}\n"
                f"🎯 <b>Take Profit cũ:</b> {old_tp} ➡️ <b>Take Profit mới:</b> {new_tp}\n\n"
                f"⏱️ <b>Thời gian:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # Gửi tin nhắn
            return self.send_message(message)
        
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo cập nhật SL/TP: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Lỗi khi gửi thông báo cập nhật SL/TP: {str(e)}"
            }
    
    def notify_trading_opportunity(self, opportunity_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Thông báo cơ hội giao dịch
        
        :param opportunity_data: Dữ liệu cơ hội giao dịch
        :return: Kết quả gửi tin nhắn
        """
        try:
            # Lấy thông tin cơ hội
            symbol = opportunity_data.get("symbol", "Unknown")
            signal = opportunity_data.get("signal", "Unknown")
            price = opportunity_data.get("price", 0)
            strength = opportunity_data.get("strength", "Unknown")
            timeframe = opportunity_data.get("timeframe", "Unknown")
            indicators = opportunity_data.get("indicators", [])
            reason = opportunity_data.get("reason", "Unknown")
            
            # Xác định emoji dựa trên tín hiệu
            signal_emoji = "📈" if signal.upper() == "LONG" else "📉"
            
            # Định dạng thông tin chỉ báo
            indicators_str = ""
            for indicator in indicators:
                indicators_str += f"  • {indicator.get('name')}: {indicator.get('value')} - {indicator.get('signal')}\n"
            
            # Định dạng tin nhắn
            message = (
                f"🔍 <b>CƠ HỘI GIAO DỊCH MỚI</b> {signal_emoji}\n\n"
                f"📊 <b>Cặp giao dịch:</b> {symbol}\n"
                f"📈 <b>Tín hiệu:</b> {signal.upper()}\n"
                f"💰 <b>Giá hiện tại:</b> {price}\n"
                f"⏲️ <b>Khung thời gian:</b> {timeframe}\n"
                f"💪 <b>Độ mạnh:</b> {strength}\n"
                f"📝 <b>Lý do:</b> {reason}\n\n"
                f"📊 <b>Chỉ báo:</b>\n{indicators_str}\n"
                f"⏱️ <b>Thời gian:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # Gửi tin nhắn
            return self.send_message(message)
        
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo cơ hội giao dịch: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Lỗi khi gửi thông báo cơ hội giao dịch: {str(e)}"
            }
    
    def send_bot_status(self, status: str, mode: str, uptime: str, stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gửi trạng thái bot
        
        :param status: Trạng thái bot ("running", "stopped", "restarting")
        :param mode: Chế độ bot ("testnet", "live")
        :param uptime: Thời gian hoạt động
        :param stats: Dữ liệu thống kê
        :return: Kết quả gửi tin nhắn
        """
        
        # Xử lý với API mới
        try:
            # Xác định emoji dựa trên trạng thái
            if status.lower() == "running":
                emoji = "✅"
                title = "BOT ĐANG CHẠY"
            elif status.lower() == "stopped":
                emoji = "⛔"
                title = "BOT ĐÃ DỪNG"
            elif status.lower() == "restarting":
                emoji = "🔄"
                title = "BOT ĐANG KHỞI ĐỘNG LẠI"
            else:
                emoji = "ℹ️"
                title = "TRẠNG THÁI BOT"
            
            # Định dạng thống kê
            stats_str = ""
            for key, value in stats.items():
                stats_str += f"• {key}: {value}\n"
            
            # Định dạng chế độ
            mode_emoji = "🧪" if mode.lower() == "testnet" else "🔴"
            mode_text = "TESTNET" if mode.lower() == "testnet" else "LIVE"
            
            # Định dạng tin nhắn
            message = (
                f"{emoji} <b>{title}</b>\n\n"
                f"{mode_emoji} <b>Chế độ:</b> {mode_text}\n"
                f"⏱️ <b>Uptime:</b> {uptime}\n\n"
                f"📊 <b>Thống kê:</b>\n{stats_str}\n"
                f"🕒 <b>Thời gian:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # Gửi tin nhắn
            return self.send_message(message)
        
        except Exception as e:
            logger.error(f"Lỗi khi gửi trạng thái bot: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Lỗi khi gửi trạng thái bot: {str(e)}"
            }
    
    def notify_bot_status(self, status: str, details: Optional[str] = None) -> Dict[str, Any]:
        """
        Thông báo trạng thái bot
        
        :param status: Trạng thái bot ("started", "stopped", "error")
        :param details: Chi tiết bổ sung
        :return: Kết quả gửi tin nhắn
        """
        try:
            # Xác định emoji và tiêu đề dựa trên trạng thái
            if status.lower() == "started":
                emoji = "✅"
                title = "BOT ĐÃ KHỞI ĐỘNG"
            elif status.lower() == "stopped":
                emoji = "⛔"
                title = "BOT ĐÃ DỪNG"
            elif status.lower() == "error":
                emoji = "❗"
                title = "LỖI BOT"
            else:
                emoji = "ℹ️"
                title = "TRẠNG THÁI BOT"
            
            # Định dạng tin nhắn
            message = (
                f"{emoji} <b>{title}</b>\n\n"
                f"⏱️ <b>Thời gian:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # Thêm chi tiết nếu có
            if details:
                message += f"\n\n📝 <b>Chi tiết:</b> {details}"
            
            # Gửi tin nhắn
            return self.send_message(message)
        
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo trạng thái bot: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Lỗi khi gửi thông báo trạng thái bot: {str(e)}"
            }
    
    def notify_error(self, error_type: str, message: str, details: Optional[str] = None) -> Dict[str, Any]:
        """
        Thông báo lỗi
        
        :param error_type: Loại lỗi
        :param message: Thông báo lỗi
        :param details: Chi tiết bổ sung
        :return: Kết quả gửi tin nhắn
        """
        try:
            # Định dạng tin nhắn
            error_message = (
                f"❌ <b>LỖI: {error_type}</b>\n\n"
                f"📝 <b>Thông báo:</b> {message}\n"
                f"⏱️ <b>Thời gian:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # Thêm chi tiết nếu có
            if details:
                error_message += f"\n\n📋 <b>Chi tiết:</b>\n<pre>{details}</pre>"
            
            # Gửi tin nhắn
            return self.send_message(error_message)
        
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo lỗi: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Lỗi khi gửi thông báo lỗi: {str(e)}"
            }
    
    def notify_system_update(self, version: str, changes: List[str]) -> Dict[str, Any]:
        """
        Thông báo cập nhật hệ thống
        
        :param version: Phiên bản mới
        :param changes: Danh sách thay đổi
        :return: Kết quả gửi tin nhắn
        """
        try:
            # Định dạng danh sách thay đổi
            changes_str = ""
            for i, change in enumerate(changes, 1):
                changes_str += f"  {i}. {change}\n"
            
            # Định dạng tin nhắn
            message = (
                f"🆕 <b>CẬP NHẬT HỆ THỐNG</b>\n\n"
                f"📦 <b>Phiên bản mới:</b> {version}\n\n"
                f"📋 <b>Thay đổi:</b>\n{changes_str}\n"
                f"⏱️ <b>Thời gian:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # Gửi tin nhắn
            return self.send_message(message)
        
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo cập nhật hệ thống: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Lỗi khi gửi thông báo cập nhật hệ thống: {str(e)}"
            }
    
    def send_startup_notification(self, account_balance: float, positions: List[Dict[str, Any]],
                            unrealized_pnl: float, market_data: Dict[str, Any], mode: str) -> Dict[str, Any]:
        """
        Gửi thông báo khởi động hệ thống với phân tích đa coin 
        
        :param account_balance: Số dư tài khoản
        :param positions: Danh sách vị thế
        :param unrealized_pnl: PnL chưa thực hiện
        :param market_data: Dữ liệu thị trường
        :param mode: Chế độ API (testnet/live)
        :return: Kết quả gửi tin nhắn
        """
        try:
            # Định dạng chế độ API
            mode_emoji = "🧪" if mode.lower() == "testnet" else "🔴"
            mode_text = "TESTNET" if mode.lower() == "testnet" else "LIVE"
            
            # Lấy giá BTC và các coin khác từ market_data
            btc_price = market_data.get('btc_price', 0)
            eth_price = market_data.get('eth_price', 0)
            btc_change = market_data.get('btc_change_24h', 0)
            eth_change = market_data.get('eth_change_24h', 0)
            
            # Lấy xu hướng thị trường
            market_trends = market_data.get('market_trends', {})
            
            # Lấy khuyến nghị từ bot (nếu có)
            recommendations = market_data.get('recommendations', [])
            
            # Định dạng danh sách vị thế
            positions_str = ""
            active_position_count = 0
            
            if positions:
                for i, pos in enumerate(positions, 1):
                    symbol = pos.get('symbol', 'Unknown')
                    position_type = pos.get('type', 'Unknown')
                    size = pos.get('size', 0)
                    entry_price = pos.get('entry_price', 0)
                    pnl = pos.get('pnl', 0)
                    pnl_percent = pos.get('pnl_percent', 0)
                    
                    active_position_count += 1
                    
                    # Xác định emoji dựa trên loại vị thế và PnL
                    type_emoji = "📈" if position_type.upper() == "LONG" else "📉"
                    result_emoji = "🟢" if pnl > 0 else "🔴"
                    
                    positions_str += f"  {result_emoji} {type_emoji} <b>{symbol}</b>: {size} @ {entry_price} ({pnl_percent:.2f}%)\n"
            else:
                positions_str = "  Không có vị thế đang mở.\n"
            
            # Phân tích thị trường và tạo khuyến nghị
            market_analysis = self._analyze_market(market_data)
            
            # Tạo thông báo khởi động
            message = (
                f"🚀 <b>HỆ THỐNG GIAO DỊCH ĐÃ KHỞI ĐỘNG</b>\n\n"
                f"{mode_emoji} <b>Chế độ:</b> {mode_text}\n"
                f"⏰ <b>Thời gian:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"🏦 <b>THÔNG TIN TÀI KHOẢN</b>\n"
                f"💰 <b>Số dư:</b> {account_balance:.2f} USDT\n"
                f"💵 <b>PnL chưa thực hiện:</b> {unrealized_pnl:.2f} USDT\n"
                f"📋 <b>Vị thế đang mở:</b> {active_position_count}\n"
            )
            
            if positions_str:
                message += f"\n📊 <b>CHI TIẾT VỊ THẾ</b>\n{positions_str}\n"
                
            # Thêm thông tin thị trường
            message += (
                f"\n📈 <b>TỔNG QUAN THỊ TRƯỜNG</b>\n"
                f"  • BTC: ${btc_price:.2f} ({btc_change:+.2f}%)\n"
                f"  • ETH: ${eth_price:.2f} ({eth_change:+.2f}%)\n"
            )
            
            # Thêm phân tích thị trường
            if market_analysis:
                message += f"\n🔍 <b>PHÂN TÍCH THỊ TRƯỜNG</b>\n{market_analysis}\n"
            
            # Thêm top 5 coin biến động mạnh nhất
            if market_trends:
                volatile_coins = sorted(market_trends.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
                if volatile_coins:
                    message += f"\n📊 <b>TOP COIN BIẾN ĐỘNG MẠNH (24H)</b>\n"
                    for symbol, change in volatile_coins:
                        trend_emoji = "📈" if change > 0 else "📉"
                        message += f"  • {symbol}: {trend_emoji} {change:+.2f}%\n"
            
            # Thêm khuyến nghị nếu có
            if recommendations:
                message += f"\n💡 <b>KHUYẾN NGHỊ GIAO DỊCH</b>\n"
                for rec in recommendations[:3]:  # Chỉ lấy top 3 khuyến nghị
                    symbol = rec.get('symbol', 'Unknown')
                    signal = rec.get('signal', 'Unknown')
                    signal_emoji = "📈" if signal.upper() == "LONG" else "📉"
                    strength = rec.get('strength', 'Unknown')
                    timeframe = rec.get('timeframe', 'Unknown')
                    message += f"  • {signal_emoji} <b>{symbol}:</b> {signal.upper()} (Độ mạnh: {strength}, TF: {timeframe})\n"
            
            # Gửi tin nhắn
            return self.send_message(message, notification_type='startup_notification')
        
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo khởi động hệ thống: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Lỗi khi gửi thông báo khởi động hệ thống: {str(e)}"
            }
            
    def _analyze_market(self, market_data: Dict[str, Any]) -> str:
        """
        Phân tích thị trường dựa trên dữ liệu
        
        :param market_data: Dữ liệu thị trường
        :return: Phân tích thị trường dạng văn bản
        """
        try:
            # Lấy dữ liệu thị trường
            btc_change = market_data.get('btc_change_24h', 0)
            fear_greed = market_data.get('sentiment', {}).get('value', 50)
            sentiment = market_data.get('sentiment', {}).get('text', 'Trung tính')
            market_trends = market_data.get('market_trends', {})
            
            # Xác định trạng thái thị trường dựa trên BTC
            market_state = "Trung tính"
            state_emoji = "⚖️"
            
            if btc_change > 3:
                market_state = "Tăng mạnh"
                state_emoji = "🚀"
            elif btc_change > 1:
                market_state = "Tăng nhẹ"
                state_emoji = "📈"
            elif btc_change < -3:
                market_state = "Giảm mạnh"
                state_emoji = "📉"
            elif btc_change < -1:
                market_state = "Giảm nhẹ" 
                state_emoji = "⬇️"
                
            # Xác định xu hướng chung của thị trường
            positive_coins = sum(1 for change in market_trends.values() if change > 0)
            total_coins = len(market_trends) if market_trends else 1
            positive_ratio = positive_coins / total_coins if total_coins > 0 else 0.5
            
            trend_description = ""
            if positive_ratio > 0.7:
                trend_description = "Thị trường đang tăng mạnh. Hầu hết các coin đều trong xu hướng tăng."
            elif positive_ratio > 0.5:
                trend_description = "Thị trường đang tăng nhẹ. Đa số các coin đang có xu hướng tích cực."
            elif positive_ratio < 0.3:
                trend_description = "Thị trường đang giảm mạnh. Hầu hết các coin đều trong xu hướng giảm."
            elif positive_ratio < 0.5:
                trend_description = "Thị trường đang giảm nhẹ. Đa số các coin đang có xu hướng tiêu cực."
            else:
                trend_description = "Thị trường đang đi ngang. Các coin không có xu hướng rõ ràng."
            
            # Tổng hợp phân tích
            analysis = (
                f"  {state_emoji} <b>Trạng thái:</b> {market_state}\n"
                f"  😮 <b>Chỉ số sợ hãi/tham lam:</b> {fear_greed} - {sentiment}\n"
            )
            
            if trend_description:
                analysis += f"  📋 <b>Nhận định:</b> {trend_description}\n"
                
            return analysis
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích thị trường: {str(e)}", exc_info=True)
            return ""
            
    def send_system_status(self, account_balance: float, positions: List[Dict[str, Any]], 
                      unrealized_pnl: float, market_data: Dict[str, Any], mode: str) -> Dict[str, Any]:
        """
        Gửi trạng thái hệ thống
        
        :param account_balance: Số dư tài khoản
        :param positions: Danh sách vị thế
        :param unrealized_pnl: PnL chưa thực hiện
        :param market_data: Dữ liệu thị trường
        :param mode: Chế độ API (testnet/live)
        :return: Kết quả gửi tin nhắn
        """
        try:
            # Kiểm tra thời gian kể từ thông báo trạng thái cuối cùng
            current_time = time.time()
            last_status_time = self.last_notification_time.get('system_status', 0)
            
            # Nếu chưa đến thời gian để gửi lại thông báo mới (5 phút)
            if current_time - last_status_time < self.message_cooldown:
                logger.info(f"Bỏ qua thông báo trạng thái hệ thống (đã gửi trong vòng {self.message_cooldown}s)")
                return {
                    "status": "skipped",
                    "message": "Bỏ qua thông báo trạng thái hệ thống (quá sớm)"
                }
                
            # Định dạng chế độ API
            mode_emoji = "🧪" if mode.lower() == "testnet" else "🔴"
            mode_text = "TESTNET" if mode.lower() == "testnet" else "LIVE"
            
            # Lấy giá BTC và các coin khác từ market_data
            btc_price = market_data.get('btc_price', 0)
            market_trends = market_data.get('market_trends', {})
            market_volumes = market_data.get('market_volumes', {})
            
            # Định dạng danh sách vị thế
            positions_str = ""
            total_profit = 0
            active_position_count = 0
            
            if positions:
                for i, pos in enumerate(positions, 1):
                    symbol = pos.get('symbol', 'Unknown')
                    position_type = pos.get('type', 'Unknown')
                    size = pos.get('size', 0)
                    entry_price = pos.get('entry_price', 0)
                    current_price = pos.get('current_price', 0)
                    pnl = pos.get('pnl', 0)
                    pnl_percent = pos.get('pnl_percent', 0)
                    stop_loss = pos.get('stop_loss', 0)
                    take_profit = pos.get('take_profit', 0)
                    
                    active_position_count += 1
                    
                    # Xác định emoji dựa trên loại vị thế và PnL
                    type_emoji = "📈" if position_type.upper() == "LONG" else "📉"
                    pnl_emoji = "🟢" if pnl > 0 else "🔴"
                    
                    positions_str += (
                        f"  {i}. {type_emoji} <b>{symbol}</b>: "
                        f"{size} @ {entry_price}\n"
                        f"     {pnl_emoji} PnL: {pnl:.2f} USDT ({pnl_percent:.2f}%)\n"
                        f"     🛑 SL: {stop_loss} | 🎯 TP: {take_profit}\n"
                    )
                    
                    total_profit += pnl
            else:
                positions_str = "  Không có vị thế đang mở\n"
            
            # Lấy thông tin xu hướng thị trường
            market_trend_str = ""
            if market_trends:
                for symbol, change in market_trends.items():
                    if isinstance(change, (int, float)):
                        trend_emoji = "🟢" if change > 0 else "🔴"
                        market_trend_str += f"  • {symbol}: {trend_emoji} {change:.2f}%\n"
            
            # Định dạng tin nhắn
            message = (
                f"🖥️ <b>TRẠNG THÁI HỆ THỐNG</b>\n\n"
                f"{mode_emoji} <b>Chế độ:</b> {mode_text}\n"
                f"💰 <b>Số dư tài khoản:</b> {account_balance:.2f} USDT\n"
                f"📊 <b>BTC/USDT:</b> ${btc_price:.2f}\n"
                f"💵 <b>PnL chưa thực hiện:</b> {unrealized_pnl:.2f} USDT\n\n"
            )
            
            # Thêm thông tin vị thế
            message += f"📋 <b>Vị thế đang mở ({active_position_count}):</b>\n{positions_str}\n"
            
            # Thêm thông tin xu hướng thị trường nếu có
            if market_trend_str:
                message += f"📈 <b>Xu hướng thị trường (24h):</b>\n{market_trend_str}\n"
            
            # Thêm khuyến nghị nếu có từ bot
            if market_data.get('recommendations'):
                rec_str = ""
                for rec in market_data.get('recommendations', []):
                    symbol = rec.get('symbol', 'Unknown')
                    signal = rec.get('signal', 'Unknown')
                    signal_emoji = "📈" if signal.upper() == "LONG" else "📉"
                    strength = rec.get('strength', 'Unknown')
                    rec_str += f"  • {signal_emoji} {symbol}: {signal.upper()} (Độ mạnh: {strength})\n"
                
                if rec_str:
                    message += f"🔍 <b>Khuyến nghị giao dịch:</b>\n{rec_str}\n"
            
            # Thêm thời gian cập nhật
            message += f"⏱️ <b>Cập nhật lúc:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Cập nhật thời gian thông báo cuối cùng
            self.last_notification_time['system_status'] = current_time
            
            # Gửi tin nhắn
            return self.send_message(message, notification_type='system_status')
        
        except Exception as e:
            logger.error(f"Lỗi khi gửi trạng thái hệ thống: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Lỗi khi gửi trạng thái hệ thống: {str(e)}"
            }
            
    def notify_daily_summary(self, summary_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gửi báo cáo tổng kết hàng ngày
        
        :param summary_data: Dữ liệu tổng kết
        :return: Kết quả gửi tin nhắn
        """
        try:
            # Lấy thông tin tổng kết
            date = summary_data.get("date", datetime.datetime.now().strftime("%Y-%m-%d"))
            total_trades = summary_data.get("total_trades", 0)
            win_trades = summary_data.get("win_trades", 0)
            loss_trades = summary_data.get("loss_trades", 0)
            win_rate = summary_data.get("win_rate", 0)
            total_profit_loss = summary_data.get("total_profit_loss", 0)
            best_trade = summary_data.get("best_trade", {})
            worst_trade = summary_data.get("worst_trade", {})
            
            # Định dạng tin nhắn
            message = (
                f"📊 <b>TỔNG KẾT GIAO DỊCH NGÀY {date}</b>\n\n"
                f"🔢 <b>Tổng số giao dịch:</b> {total_trades}\n"
                f"✅ <b>Thắng:</b> {win_trades}\n"
                f"❌ <b>Thua:</b> {loss_trades}\n"
                f"📈 <b>Tỷ lệ thắng:</b> {win_rate:.2f}%\n"
                f"💰 <b>Tổng lợi nhuận:</b> {total_profit_loss:.2f} USDT\n\n"
            )
            
            # Thêm thông tin về giao dịch tốt nhất
            if best_trade:
                message += (
                    f"🏆 <b>Giao dịch tốt nhất:</b>\n"
                    f"  • Cặp giao dịch: {best_trade.get('symbol', 'N/A')}\n"
                    f"  • Hướng: {best_trade.get('side', 'N/A')}\n"
                    f"  • Lợi nhuận: {best_trade.get('profit', 0):.2f} USDT ({best_trade.get('profit_percentage', 0):.2f}%)\n\n"
                )
            
            # Thêm thông tin về giao dịch tệ nhất
            if worst_trade:
                message += (
                    f"📉 <b>Giao dịch tệ nhất:</b>\n"
                    f"  • Cặp giao dịch: {worst_trade.get('symbol', 'N/A')}\n"
                    f"  • Hướng: {worst_trade.get('side', 'N/A')}\n"
                    f"  • Lỗ: {worst_trade.get('loss', 0):.2f} USDT ({worst_trade.get('loss_percentage', 0):.2f}%)\n\n"
                )
            
            # Gửi tin nhắn
            return self.send_message(message)
        
        except Exception as e:
            logger.error(f"Lỗi khi gửi báo cáo tổng kết hàng ngày: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Lỗi khi gửi báo cáo tổng kết hàng ngày: {str(e)}"
            }
            
# Singleton instance
_instance = None

def get_notifier() -> TelegramNotifier:
    """
    Lấy instance của TelegramNotifier
    
    :return: TelegramNotifier instance
    """
    global _instance
    if _instance is None:
        _instance = TelegramNotifier()
    return _instance