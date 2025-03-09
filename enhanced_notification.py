#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module thông báo nâng cao (EnhancedNotification)

Module này cung cấp các chức năng thông báo nâng cao qua Telegram, Email
với các định dạng phong phú và báo cáo chi tiết đầy đủ.
"""

import os
import json
import time
import logging
import smtplib
import datetime
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Tuple, Union, Optional, Any

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('enhanced_notification')

class NotificationChannel:
    """Lớp cơ sở cho các kênh thông báo"""
    
    def __init__(self, name: str):
        """
        Khởi tạo kênh thông báo
        
        Args:
            name (str): Tên kênh thông báo
        """
        self.name = name
        self.enabled = True
    
    def send(self, message: str, subject: str = None, data: Dict = None) -> bool:
        """
        Gửi thông báo
        
        Args:
            message (str): Nội dung thông báo
            subject (str, optional): Tiêu đề thông báo
            data (Dict, optional): Dữ liệu bổ sung
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
        """
        raise NotImplementedError("Phương thức send() phải được ghi đè")
    
    def format_message(self, template_name: str, data: Dict) -> str:
        """
        Định dạng thông báo theo template
        
        Args:
            template_name (str): Tên template
            data (Dict): Dữ liệu để điền vào template
            
        Returns:
            str: Thông báo đã định dạng
        """
        raise NotImplementedError("Phương thức format_message() phải được ghi đè")


class TelegramNotifier(NotificationChannel):
    """Lớp gửi thông báo qua Telegram"""
    
    def __init__(self, bot_token: str = None, chat_id: str = None, 
                config_path: str = None, disable_notification: bool = False):
        """
        Khởi tạo TelegramNotifier
        
        Args:
            bot_token (str, optional): Token của Telegram Bot
            chat_id (str, optional): ID của chat/channel nhận thông báo
            config_path (str, optional): Đường dẫn đến file cấu hình
            disable_notification (bool): Tắt âm thanh thông báo
        """
        super().__init__("telegram")
        
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.disable_notification = disable_notification
        
        # Nếu có config_path, đọc cấu hình từ file
        if config_path:
            self._load_config(config_path)
        # Nếu không có bot_token hoặc chat_id, thử đọc từ env
        elif not bot_token or not chat_id:
            self._load_from_env()
    
    def _load_config(self, config_path: str) -> bool:
        """
        Tải cấu hình từ file
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
            
        Returns:
            bool: True nếu tải thành công, False nếu thất bại
        """
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                telegram_config = config.get('telegram', {})
                self.bot_token = telegram_config.get('bot_token') or self.bot_token
                self.chat_id = telegram_config.get('chat_id') or self.chat_id
                
                logger.info(f"Đã tải cấu hình Telegram từ {config_path}")
                return True
            else:
                logger.warning(f"Không tìm thấy file cấu hình Telegram: {config_path}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình Telegram: {str(e)}")
            return False
    
    def _load_from_env(self) -> bool:
        """
        Tải cấu hình từ biến môi trường
        
        Returns:
            bool: True nếu tải thành công, False nếu thất bại
        """
        try:
            # Thử đọc từ biến môi trường
            self.bot_token = os.environ.get('TELEGRAM_BOT_TOKEN') or self.bot_token
            self.chat_id = os.environ.get('TELEGRAM_CHAT_ID') or self.chat_id
            
            if self.bot_token and self.chat_id:
                logger.info("Đã tải cấu hình Telegram từ biến môi trường")
                return True
            else:
                logger.warning("Không tìm thấy cấu hình Telegram trong biến môi trường")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình Telegram từ biến môi trường: {str(e)}")
            return False
    
    def _is_configured(self) -> bool:
        """
        Kiểm tra xem kênh Telegram đã được cấu hình chưa
        
        Returns:
            bool: True nếu đã cấu hình, False nếu chưa
        """
        return bool(self.bot_token and self.chat_id)
    
    def send(self, message: str, subject: str = None, data: Dict = None) -> bool:
        """
        Gửi thông báo qua Telegram
        
        Args:
            message (str): Nội dung thông báo
            subject (str, optional): Tiêu đề thông báo
            data (Dict, optional): Dữ liệu bổ sung
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
        """
        if not self.enabled:
            logger.info("Thông báo Telegram đã bị tắt")
            return False
        
        if not self._is_configured():
            logger.error("Chưa cấu hình Telegram (thiếu bot_token hoặc chat_id)")
            return False
        
        try:
            # Kết hợp subject vào message nếu có
            if subject:
                full_message = f"*{subject}*\n\n{message}"
            else:
                full_message = message
            
            # Chuẩn bị payload
            payload = {
                'chat_id': self.chat_id,
                'text': full_message,
                'parse_mode': 'Markdown',
                'disable_notification': self.disable_notification
            }
            
            # Gửi request
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            response = requests.post(url, json=payload)
            
            # Kiểm tra kết quả
            if response.status_code == 200:
                logger.info("Đã gửi thông báo Telegram thành công")
                return True
            else:
                logger.error(f"Lỗi khi gửi thông báo Telegram: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo Telegram: {str(e)}")
            return False
    
    def format_message(self, template_name: str, data: Dict) -> str:
        """
        Định dạng thông báo Telegram theo template
        
        Args:
            template_name (str): Tên template
            data (Dict): Dữ liệu để điền vào template
            
        Returns:
            str: Thông báo đã định dạng
        """
        # Danh sách các template
        templates = {
            # Thông báo khi có vị thế mới mở
            'new_position': (
                "🔔 *Vị thế mới*\n\n"
                f"*Symbol:* `{data.get('symbol', 'N/A')}`\n"
                f"*Loại:* `{data.get('side', 'N/A')}`\n"
                f"*Giá vào:* `{data.get('entry_price', 0):.2f}`\n"
                f"*Khối lượng:* `{data.get('quantity', 0):.4f}`\n"
                f"*Đòn bẩy:* `{data.get('leverage', 1)}x`\n"
                f"*Stop Loss:* `{data.get('stop_loss', 'N/A')}`\n"
                f"*Take Profit:* `{data.get('take_profit', 'N/A')}`\n"
                f"*Thời gian:* `{data.get('entry_time', 'N/A')}`"
            ),
            
            # Thông báo khi một vị thế đóng
            'position_closed': (
                "🔔 *Vị thế đã đóng*\n\n"
                f"*Symbol:* `{data.get('symbol', 'N/A')}`\n"
                f"*Loại:* `{data.get('side', 'N/A')}`\n"
                f"*Giá vào:* `{data.get('entry_price', 0):.2f}`\n"
                f"*Giá ra:* `{data.get('exit_price', 0):.2f}`\n"
                f"*P&L:* `{data.get('profit_loss', 0):.2f} ({data.get('profit_percent', 0):.2f}%)`\n"
                f"*Lý do:* `{data.get('close_reason', 'N/A')}`\n"
                f"*Thời gian:* `{data.get('exit_time', 'N/A')}`"
            ),
            
            # Thông báo khi trailing stop được kích hoạt
            'trailing_stop_activated': (
                "🔔 *Trailing Stop kích hoạt*\n\n"
                f"*Symbol:* `{data.get('symbol', 'N/A')}`\n"
                f"*Loại:* `{data.get('side', 'N/A')}`\n"
                f"*Giá vào:* `{data.get('entry_price', 0):.2f}`\n"
                f"*Giá hiện tại:* `{data.get('current_price', 0):.2f}`\n"
                f"*Mức trailing:* `{data.get('trailing_stop', 0):.2f}`\n"
                f"*P&L hiện tại:* `{data.get('profit_percent', 0):.2f}%`\n"
                f"*Thời gian:* `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
            ),
            
            # Thông báo lỗi
            'error': (
                "⚠️ *Cảnh báo lỗi*\n\n"
                f"*Loại lỗi:* `{data.get('error_type', 'N/A')}`\n"
                f"*Chi tiết:* `{data.get('error_message', 'N/A')}`\n"
                f"*Thời gian:* `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
            ),
            
            # Thông báo khởi động hệ thống
            'system_start': (
                "🚀 *Hệ thống đã khởi động*\n\n"
                f"*Phiên bản:* `{data.get('version', 'N/A')}`\n"
                f"*Mode:* `{data.get('mode', 'N/A')}`\n"
                f"*Tài khoản:* `{data.get('account', 'N/A')}`\n"
                f"*Số dư:* `{data.get('balance', 0):.2f} USDT`\n"
                f"*Thời gian:* `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
            ),
            
            # Báo cáo hiệu suất định kỳ
            'performance_report': (
                "📊 *Báo cáo hiệu suất*\n\n"
                f"*Khoảng thời gian:* `{data.get('period', 'N/A')}`\n"
                f"*Tổng P&L:* `{data.get('total_pnl', 0):.2f} USDT ({data.get('pnl_percent', 0):.2f}%)`\n"
                f"*Số giao dịch:* `{data.get('total_trades', 0)}`\n"
                f"*Tỷ lệ thắng:* `{data.get('win_rate', 0):.2f}%`\n"
                f"*Drawdown tối đa:* `{data.get('max_drawdown', 0):.2f}%`\n"
                f"*Hệ số lợi nhuận:* `{data.get('profit_factor', 0):.2f}`\n"
                f"*Sharpe Ratio:* `{data.get('sharpe_ratio', 0):.2f}`\n"
                f"*Thời gian:* `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
            )
        }
        
        # Nếu template không tồn tại, trả về message mặc định
        if template_name not in templates:
            logger.warning(f"Template '{template_name}' không tồn tại, sử dụng mặc định")
            return f"*Thông báo*\n\n{json.dumps(data, indent=2)}"
        
        try:
            # Lấy template và thay thế các biến
            return templates[template_name]
        except Exception as e:
            logger.error(f"Lỗi khi định dạng thông báo Telegram: {str(e)}")
            return f"*Thông báo*\n\n{json.dumps(data, indent=2)}"
    
    def send_position_notification(self, data: Dict) -> bool:
        """
        Gửi thông báo về vị thế
        
        Args:
            data (Dict): Dữ liệu vị thế
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
        """
        message = self.format_message('new_position', data)
        subject = f"Vị thế mới: {data.get('symbol')} {data.get('side')}"
        return self.send(message, subject, data)
    
    def send_position_close_notification(self, data: Dict) -> bool:
        """
        Gửi thông báo về vị thế đã đóng
        
        Args:
            data (Dict): Dữ liệu vị thế
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
        """
        message = self.format_message('position_closed', data)
        subject = f"Vị thế đóng: {data.get('symbol')} {data.get('side')}"
        return self.send(message, subject, data)
    
    def send_trailing_stop_notification(self, data: Dict) -> bool:
        """
        Gửi thông báo về trailing stop đã kích hoạt
        
        Args:
            data (Dict): Dữ liệu trailing stop
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
        """
        message = self.format_message('trailing_stop_activated', data)
        subject = f"Trailing Stop: {data.get('symbol')} {data.get('side')}"
        return self.send(message, subject, data)
    
    def send_error_notification(self, error_type: str, error_message: str) -> bool:
        """
        Gửi thông báo về lỗi
        
        Args:
            error_type (str): Loại lỗi
            error_message (str): Chi tiết lỗi
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
        """
        data = {
            'error_type': error_type,
            'error_message': error_message
        }
        message = self.format_message('error', data)
        subject = f"Lỗi: {error_type}"
        return self.send(message, subject, data)
    
    def send_system_start_notification(self, version: str, mode: str, account: str, balance: float) -> bool:
        """
        Gửi thông báo về việc hệ thống đã khởi động
        
        Args:
            version (str): Phiên bản hệ thống
            mode (str): Chế độ hoạt động
            account (str): Thông tin tài khoản
            balance (float): Số dư tài khoản
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
        """
        data = {
            'version': version,
            'mode': mode,
            'account': account,
            'balance': balance
        }
        message = self.format_message('system_start', data)
        subject = f"Hệ thống đã khởi động"
        return self.send(message, subject, data)
    
    def send_performance_report(self, data: Dict) -> bool:
        """
        Gửi báo cáo hiệu suất
        
        Args:
            data (Dict): Dữ liệu báo cáo
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
        """
        message = self.format_message('performance_report', data)
        subject = f"Báo cáo hiệu suất: {data.get('period', 'N/A')}"
        return self.send(message, subject, data)


class EmailNotifier(NotificationChannel):
    """Lớp gửi thông báo qua Email"""
    
    def __init__(self, smtp_server: str = None, smtp_port: int = 587,
                sender_email: str = None, password: str = None, 
                recipients: List[str] = None, config_path: str = None):
        """
        Khởi tạo EmailNotifier
        
        Args:
            smtp_server (str, optional): Địa chỉ SMTP server
            smtp_port (int): Port của SMTP server
            sender_email (str, optional): Email người gửi
            password (str, optional): Mật khẩu email
            recipients (List[str], optional): Danh sách email người nhận
            config_path (str, optional): Đường dẫn đến file cấu hình
        """
        super().__init__("email")
        
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.password = password
        self.recipients = recipients or []
        
        # Nếu có config_path, đọc cấu hình từ file
        if config_path:
            self._load_config(config_path)
        # Nếu không có cấu hình đầy đủ, thử đọc từ env
        elif not smtp_server or not sender_email or not password or not recipients:
            self._load_from_env()
    
    def _load_config(self, config_path: str) -> bool:
        """
        Tải cấu hình từ file
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
            
        Returns:
            bool: True nếu tải thành công, False nếu thất bại
        """
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                email_config = config.get('email', {})
                self.smtp_server = email_config.get('smtp_server') or self.smtp_server
                self.smtp_port = email_config.get('smtp_port') or self.smtp_port
                self.sender_email = email_config.get('sender_email') or self.sender_email
                self.password = email_config.get('password') or self.password
                self.recipients = email_config.get('recipients') or self.recipients
                
                logger.info(f"Đã tải cấu hình Email từ {config_path}")
                return True
            else:
                logger.warning(f"Không tìm thấy file cấu hình Email: {config_path}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình Email: {str(e)}")
            return False
    
    def _load_from_env(self) -> bool:
        """
        Tải cấu hình từ biến môi trường
        
        Returns:
            bool: True nếu tải thành công, False nếu thất bại
        """
        try:
            # Thử đọc từ biến môi trường
            self.smtp_server = os.environ.get('EMAIL_SMTP_SERVER') or self.smtp_server
            self.smtp_port = int(os.environ.get('EMAIL_SMTP_PORT') or self.smtp_port)
            self.sender_email = os.environ.get('EMAIL_SENDER') or self.sender_email
            self.password = os.environ.get('EMAIL_PASSWORD') or self.password
            
            recipients_str = os.environ.get('EMAIL_RECIPIENTS')
            if recipients_str:
                self.recipients = [r.strip() for r in recipients_str.split(',')]
            
            if self.smtp_server and self.sender_email and self.password and self.recipients:
                logger.info("Đã tải cấu hình Email từ biến môi trường")
                return True
            else:
                logger.warning("Không tìm thấy cấu hình Email đầy đủ trong biến môi trường")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình Email từ biến môi trường: {str(e)}")
            return False
    
    def _is_configured(self) -> bool:
        """
        Kiểm tra xem kênh Email đã được cấu hình đầy đủ chưa
        
        Returns:
            bool: True nếu đã cấu hình, False nếu chưa
        """
        return bool(self.smtp_server and self.sender_email and self.password and self.recipients)
    
    def send(self, message: str, subject: str = None, data: Dict = None) -> bool:
        """
        Gửi thông báo qua Email
        
        Args:
            message (str): Nội dung thông báo
            subject (str, optional): Tiêu đề thông báo
            data (Dict, optional): Dữ liệu bổ sung
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
        """
        if not self.enabled:
            logger.info("Thông báo Email đã bị tắt")
            return False
        
        if not self._is_configured():
            logger.error("Chưa cấu hình Email đầy đủ")
            return False
        
        try:
            # Chuẩn bị email
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(self.recipients)
            msg['Subject'] = subject or "Thông báo từ hệ thống Trading Bot"
            
            # Định dạng nội dung email
            html_content = f"<html><body>{message}</body></html>"
            msg.attach(MIMEText(html_content, 'html'))
            
            # Gửi email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Bảo mật kết nối
                server.login(self.sender_email, self.password)
                server.send_message(msg)
            
            logger.info(f"Đã gửi email thành công đến {len(self.recipients)} người nhận")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi gửi email: {str(e)}")
            return False
    
    def format_message(self, template_name: str, data: Dict) -> str:
        """
        Định dạng thông báo Email theo template
        
        Args:
            template_name (str): Tên template
            data (Dict): Dữ liệu để điền vào template
            
        Returns:
            str: Thông báo đã định dạng dạng HTML
        """
        # Danh sách các template
        templates = {
            # Thông báo khi có vị thế mới mở
            'new_position': (
                "<h2>Vị thế mới</h2>"
                "<table style='width: 100%; border-collapse: collapse;'>"
                f"<tr><td style='font-weight: bold; padding: 5px;'>Symbol:</td><td>{data.get('symbol', 'N/A')}</td></tr>"
                f"<tr><td style='font-weight: bold; padding: 5px;'>Loại:</td><td>{data.get('side', 'N/A')}</td></tr>"
                f"<tr><td style='font-weight: bold; padding: 5px;'>Giá vào:</td><td>{data.get('entry_price', 0):.2f}</td></tr>"
                f"<tr><td style='font-weight: bold; padding: 5px;'>Khối lượng:</td><td>{data.get('quantity', 0):.4f}</td></tr>"
                f"<tr><td style='font-weight: bold; padding: 5px;'>Đòn bẩy:</td><td>{data.get('leverage', 1)}x</td></tr>"
                f"<tr><td style='font-weight: bold; padding: 5px;'>Stop Loss:</td><td>{data.get('stop_loss', 'N/A')}</td></tr>"
                f"<tr><td style='font-weight: bold; padding: 5px;'>Take Profit:</td><td>{data.get('take_profit', 'N/A')}</td></tr>"
                f"<tr><td style='font-weight: bold; padding: 5px;'>Thời gian:</td><td>{data.get('entry_time', 'N/A')}</td></tr>"
                "</table>"
            ),
            
            # Thông báo khi một vị thế đóng
            'position_closed': (
                "<h2>Vị thế đã đóng</h2>"
                "<table style='width: 100%; border-collapse: collapse;'>"
                f"<tr><td style='font-weight: bold; padding: 5px;'>Symbol:</td><td>{data.get('symbol', 'N/A')}</td></tr>"
                f"<tr><td style='font-weight: bold; padding: 5px;'>Loại:</td><td>{data.get('side', 'N/A')}</td></tr>"
                f"<tr><td style='font-weight: bold; padding: 5px;'>Giá vào:</td><td>{data.get('entry_price', 0):.2f}</td></tr>"
                f"<tr><td style='font-weight: bold; padding: 5px;'>Giá ra:</td><td>{data.get('exit_price', 0):.2f}</td></tr>"
                f"<tr><td style='font-weight: bold; padding: 5px;'>P&L:</td><td>{data.get('profit_loss', 0):.2f} ({data.get('profit_percent', 0):.2f}%)</td></tr>"
                f"<tr><td style='font-weight: bold; padding: 5px;'>Lý do:</td><td>{data.get('close_reason', 'N/A')}</td></tr>"
                f"<tr><td style='font-weight: bold; padding: 5px;'>Thời gian:</td><td>{data.get('exit_time', 'N/A')}</td></tr>"
                "</table>"
            ),
            
            # Báo cáo hiệu suất định kỳ
            'performance_report': (
                "<h2>Báo cáo hiệu suất</h2>"
                "<p>Khoảng thời gian: " + data.get('period', 'N/A') + "</p>"
                "<table style='width: 100%; border-collapse: collapse; border: 1px solid #ddd;'>"
                "<tr style='background-color: #f2f2f2;'>"
                "<th style='padding: 8px; text-align: left; border: 1px solid #ddd;'>Chỉ số</th>"
                "<th style='padding: 8px; text-align: right; border: 1px solid #ddd;'>Giá trị</th>"
                "</tr>"
                f"<tr><td style='padding: 8px; border: 1px solid #ddd;'>Tổng P&L</td><td style='padding: 8px; text-align: right; border: 1px solid #ddd;'>{data.get('total_pnl', 0):.2f} USDT ({data.get('pnl_percent', 0):.2f}%)</td></tr>"
                f"<tr><td style='padding: 8px; border: 1px solid #ddd;'>Số giao dịch</td><td style='padding: 8px; text-align: right; border: 1px solid #ddd;'>{data.get('total_trades', 0)}</td></tr>"
                f"<tr><td style='padding: 8px; border: 1px solid #ddd;'>Tỷ lệ thắng</td><td style='padding: 8px; text-align: right; border: 1px solid #ddd;'>{data.get('win_rate', 0):.2f}%</td></tr>"
                f"<tr><td style='padding: 8px; border: 1px solid #ddd;'>Drawdown tối đa</td><td style='padding: 8px; text-align: right; border: 1px solid #ddd;'>{data.get('max_drawdown', 0):.2f}%</td></tr>"
                f"<tr><td style='padding: 8px; border: 1px solid #ddd;'>Hệ số lợi nhuận</td><td style='padding: 8px; text-align: right; border: 1px solid #ddd;'>{data.get('profit_factor', 0):.2f}</td></tr>"
                f"<tr><td style='padding: 8px; border: 1px solid #ddd;'>Sharpe Ratio</td><td style='padding: 8px; text-align: right; border: 1px solid #ddd;'>{data.get('sharpe_ratio', 0):.2f}</td></tr>"
                "</table>"
                "<p>Thời gian: " + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "</p>"
            )
        }
        
        # Nếu template không tồn tại, trả về message mặc định
        if template_name not in templates:
            logger.warning(f"Template '{template_name}' không tồn tại, sử dụng mặc định")
            return f"<h2>Thông báo</h2><pre>{json.dumps(data, indent=2)}</pre>"
        
        try:
            # Lấy template
            return templates[template_name]
        except Exception as e:
            logger.error(f"Lỗi khi định dạng thông báo Email: {str(e)}")
            return f"<h2>Thông báo</h2><pre>{json.dumps(data, indent=2)}</pre>"


class EnhancedNotification:
    """Lớp thông báo nâng cao kết hợp nhiều kênh"""
    
    def __init__(self, config_path: str = None):
        """
        Khởi tạo EnhancedNotification
        
        Args:
            config_path (str, optional): Đường dẫn đến file cấu hình
        """
        self.config_path = config_path
        self.channels = {}
        
        # Tải cấu hình
        if config_path:
            self._load_config()
        
        # Khởi tạo các kênh mặc định
        if not self.channels:
            self._init_default_channels()
    
    def _load_config(self) -> bool:
        """
        Tải cấu hình từ file
        
        Returns:
            bool: True nếu tải thành công, False nếu thất bại
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                
                # Khởi tạo các kênh từ cấu hình
                if 'telegram' in config and config['telegram'].get('enabled', True):
                    self.channels['telegram'] = TelegramNotifier(
                        bot_token=config['telegram'].get('bot_token'),
                        chat_id=config['telegram'].get('chat_id'),
                        disable_notification=config['telegram'].get('disable_notification', False)
                    )
                
                if 'email' in config and config['email'].get('enabled', True):
                    self.channels['email'] = EmailNotifier(
                        smtp_server=config['email'].get('smtp_server'),
                        smtp_port=config['email'].get('smtp_port', 587),
                        sender_email=config['email'].get('sender_email'),
                        password=config['email'].get('password'),
                        recipients=config['email'].get('recipients')
                    )
                
                logger.info(f"Đã tải cấu hình thông báo từ {self.config_path}")
                return True
            else:
                logger.warning(f"Không tìm thấy file cấu hình thông báo: {self.config_path}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình thông báo: {str(e)}")
            return False
    
    def _init_default_channels(self) -> None:
        """Khởi tạo các kênh thông báo mặc định"""
        # Thử khởi tạo Telegram từ biến môi trường
        telegram = TelegramNotifier()
        if telegram._is_configured():
            self.channels['telegram'] = telegram
        
        # Thử khởi tạo Email từ biến môi trường
        email = EmailNotifier()
        if email._is_configured():
            self.channels['email'] = email
    
    def add_channel(self, channel: NotificationChannel) -> bool:
        """
        Thêm một kênh thông báo
        
        Args:
            channel (NotificationChannel): Kênh thông báo
            
        Returns:
            bool: True nếu thêm thành công, False nếu không
        """
        if channel.name in self.channels:
            logger.warning(f"Kênh thông báo '{channel.name}' đã tồn tại, sẽ ghi đè")
        
        self.channels[channel.name] = channel
        logger.info(f"Đã thêm kênh thông báo: {channel.name}")
        return True
    
    def remove_channel(self, channel_name: str) -> bool:
        """
        Xóa một kênh thông báo
        
        Args:
            channel_name (str): Tên kênh thông báo
            
        Returns:
            bool: True nếu xóa thành công, False nếu không
        """
        if channel_name not in self.channels:
            logger.warning(f"Kênh thông báo '{channel_name}' không tồn tại")
            return False
        
        del self.channels[channel_name]
        logger.info(f"Đã xóa kênh thông báo: {channel_name}")
        return True
    
    def enable_channel(self, channel_name: str) -> bool:
        """
        Bật một kênh thông báo
        
        Args:
            channel_name (str): Tên kênh thông báo
            
        Returns:
            bool: True nếu bật thành công, False nếu không
        """
        if channel_name not in self.channels:
            logger.warning(f"Kênh thông báo '{channel_name}' không tồn tại")
            return False
        
        self.channels[channel_name].enabled = True
        logger.info(f"Đã bật kênh thông báo: {channel_name}")
        return True
    
    def disable_channel(self, channel_name: str) -> bool:
        """
        Tắt một kênh thông báo
        
        Args:
            channel_name (str): Tên kênh thông báo
            
        Returns:
            bool: True nếu tắt thành công, False nếu không
        """
        if channel_name not in self.channels:
            logger.warning(f"Kênh thông báo '{channel_name}' không tồn tại")
            return False
        
        self.channels[channel_name].enabled = False
        logger.info(f"Đã tắt kênh thông báo: {channel_name}")
        return True
    
    def send(self, message: str, subject: str = None, data: Dict = None, 
           channels: List[str] = None) -> Dict[str, bool]:
        """
        Gửi thông báo qua các kênh
        
        Args:
            message (str): Nội dung thông báo
            subject (str, optional): Tiêu đề thông báo
            data (Dict, optional): Dữ liệu bổ sung
            channels (List[str], optional): Danh sách kênh cần gửi, None để gửi tất cả
            
        Returns:
            Dict[str, bool]: Kết quả gửi theo từng kênh
        """
        results = {}
        
        # Nếu không chỉ định kênh, sử dụng tất cả kênh đã bật
        if channels is None:
            use_channels = [name for name, channel in self.channels.items() if channel.enabled]
        else:
            use_channels = [name for name in channels if name in self.channels and self.channels[name].enabled]
        
        if not use_channels:
            logger.warning("Không có kênh thông báo nào khả dụng để gửi thông báo")
            return results
        
        # Gửi thông báo qua từng kênh
        for channel_name in use_channels:
            channel = self.channels[channel_name]
            try:
                result = channel.send(message, subject, data)
                results[channel_name] = result
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo qua kênh {channel_name}: {str(e)}")
                results[channel_name] = False
        
        return results
    
    def notify_new_position(self, position_data: Dict) -> Dict[str, bool]:
        """
        Thông báo về vị thế mới
        
        Args:
            position_data (Dict): Dữ liệu vị thế
            
        Returns:
            Dict[str, bool]: Kết quả gửi theo từng kênh
        """
        results = {}
        
        for channel_name, channel in self.channels.items():
            if not channel.enabled:
                continue
            
            try:
                if isinstance(channel, TelegramNotifier):
                    # Sử dụng phương thức chuyên biệt cho Telegram
                    result = channel.send_position_notification(position_data)
                else:
                    # Đối với các kênh khác, định dạng message theo cách riêng
                    formatted_message = channel.format_message('new_position', position_data)
                    subject = f"Vị thế mới: {position_data.get('symbol')} {position_data.get('side')}"
                    result = channel.send(formatted_message, subject, position_data)
                
                results[channel_name] = result
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo vị thế mới qua kênh {channel_name}: {str(e)}")
                results[channel_name] = False
        
        return results
    
    def notify_position_closed(self, position_data: Dict) -> Dict[str, bool]:
        """
        Thông báo về vị thế đã đóng
        
        Args:
            position_data (Dict): Dữ liệu vị thế
            
        Returns:
            Dict[str, bool]: Kết quả gửi theo từng kênh
        """
        results = {}
        
        for channel_name, channel in self.channels.items():
            if not channel.enabled:
                continue
            
            try:
                if isinstance(channel, TelegramNotifier):
                    # Sử dụng phương thức chuyên biệt cho Telegram
                    result = channel.send_position_close_notification(position_data)
                else:
                    # Đối với các kênh khác, định dạng message theo cách riêng
                    formatted_message = channel.format_message('position_closed', position_data)
                    subject = f"Vị thế đóng: {position_data.get('symbol')} {position_data.get('side')}"
                    result = channel.send(formatted_message, subject, position_data)
                
                results[channel_name] = result
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo vị thế đóng qua kênh {channel_name}: {str(e)}")
                results[channel_name] = False
        
        return results
    
    def notify_trailing_stop(self, position_data: Dict) -> Dict[str, bool]:
        """
        Thông báo về trailing stop đã kích hoạt
        
        Args:
            position_data (Dict): Dữ liệu vị thế
            
        Returns:
            Dict[str, bool]: Kết quả gửi theo từng kênh
        """
        results = {}
        
        for channel_name, channel in self.channels.items():
            if not channel.enabled:
                continue
            
            try:
                if isinstance(channel, TelegramNotifier):
                    # Sử dụng phương thức chuyên biệt cho Telegram
                    result = channel.send_trailing_stop_notification(position_data)
                else:
                    # Đối với các kênh khác, định dạng message theo cách riêng
                    formatted_message = channel.format_message('trailing_stop_activated', position_data)
                    subject = f"Trailing Stop: {position_data.get('symbol')} {position_data.get('side')}"
                    result = channel.send(formatted_message, subject, position_data)
                
                results[channel_name] = result
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo trailing stop qua kênh {channel_name}: {str(e)}")
                results[channel_name] = False
        
        return results
    
    def notify_error(self, error_type: str, error_message: str) -> Dict[str, bool]:
        """
        Thông báo về lỗi
        
        Args:
            error_type (str): Loại lỗi
            error_message (str): Chi tiết lỗi
            
        Returns:
            Dict[str, bool]: Kết quả gửi theo từng kênh
        """
        data = {
            'error_type': error_type,
            'error_message': error_message
        }
        results = {}
        
        for channel_name, channel in self.channels.items():
            if not channel.enabled:
                continue
            
            try:
                formatted_message = channel.format_message('error', data)
                subject = f"Lỗi: {error_type}"
                result = channel.send(formatted_message, subject, data)
                
                results[channel_name] = result
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo lỗi qua kênh {channel_name}: {str(e)}")
                results[channel_name] = False
        
        return results
    
    def notify_performance(self, performance_data: Dict) -> Dict[str, bool]:
        """
        Thông báo về hiệu suất
        
        Args:
            performance_data (Dict): Dữ liệu hiệu suất
            
        Returns:
            Dict[str, bool]: Kết quả gửi theo từng kênh
        """
        results = {}
        
        for channel_name, channel in self.channels.items():
            if not channel.enabled:
                continue
            
            try:
                if isinstance(channel, TelegramNotifier):
                    # Sử dụng phương thức chuyên biệt cho Telegram
                    result = channel.send_performance_report(performance_data)
                else:
                    # Đối với các kênh khác, định dạng message theo cách riêng
                    formatted_message = channel.format_message('performance_report', performance_data)
                    subject = f"Báo cáo hiệu suất: {performance_data.get('period', 'N/A')}"
                    result = channel.send(formatted_message, subject, performance_data)
                
                results[channel_name] = result
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo hiệu suất qua kênh {channel_name}: {str(e)}")
                results[channel_name] = False
        
        return results


def main():
    """Hàm chính để test EnhancedNotification"""
    # Tạo dữ liệu vị thế giả lập
    position_data = {
        "symbol": "BTCUSDT",
        "side": "LONG",
        "entry_price": 60000,
        "current_price": 61500,
        "quantity": 0.1,
        "leverage": 10,
        "stop_loss": 57000,
        "take_profit": 65000,
        "entry_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "profit_percent": 25.0  # (61500 - 60000) / 60000 * 100 * 10
    }
    
    # Khởi tạo hệ thống thông báo
    print("Khởi tạo hệ thống thông báo...")
    notification = EnhancedNotification()
    
    # Kiểm tra các kênh đã cấu hình
    print(f"Các kênh thông báo: {list(notification.channels.keys())}")
    
    # Thử gửi thông báo về vị thế mới
    print("\nGửi thông báo về vị thế mới:")
    results = notification.notify_new_position(position_data)
    print(f"Kết quả gửi: {results}")
    
    # Tạo dữ liệu vị thế đã đóng
    position_closed_data = position_data.copy()
    position_closed_data.update({
        "exit_price": 63000,
        "exit_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "profit_loss": (63000 - 60000) * 0.1 * 10,
        "profit_percent": 50.0,  # (63000 - 60000) / 60000 * 100 * 10
        "close_reason": "Take Profit"
    })
    
    # Thử gửi thông báo về vị thế đã đóng
    print("\nGửi thông báo về vị thế đã đóng:")
    results = notification.notify_position_closed(position_closed_data)
    print(f"Kết quả gửi: {results}")
    
    # Tạo dữ liệu hiệu suất
    performance_data = {
        "period": "Tháng 3/2025",
        "total_pnl": 1250.75,
        "pnl_percent": 12.5,
        "total_trades": 25,
        "win_rate": 68.0,
        "max_drawdown": 5.2,
        "profit_factor": 2.3,
        "sharpe_ratio": 1.8
    }
    
    # Thử gửi thông báo về hiệu suất
    print("\nGửi báo cáo hiệu suất:")
    results = notification.notify_performance(performance_data)
    print(f"Kết quả gửi: {results}")
    
    # Thử gửi thông báo về lỗi
    print("\nGửi thông báo về lỗi:")
    results = notification.notify_error("API_ERROR", "Không thể kết nối đến Binance API")
    print(f"Kết quả gửi: {results}")


if __name__ == "__main__":
    main()