#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram Notifier
--------------
Module cung cấp chức năng gửi thông báo qua Telegram Bot
Hỗ trợ định dạng thông báo, gửi ảnh, và nhiều loại thông báo khác nhau
"""

import os
import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Union, Optional, Any
import traceback

# Thiết lập logging
logger = logging.getLogger("telegram_notifier")

class TelegramNotifier:
    """
    Lớp cung cấp chức năng gửi thông báo qua Telegram Bot
    """
    
    def __init__(self, token: str = None, chat_id: str = None, enabled: bool = True):
        """
        Khởi tạo Telegram Notifier
        
        Args:
            token: Token của Telegram Bot
            chat_id: ID của chat để gửi thông báo
            enabled: Trạng thái bật/tắt thông báo
        """
        self.token = token or os.environ.get('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.environ.get('TELEGRAM_CHAT_ID')
        self.enabled = enabled
        
        # URL cơ sở để gọi Telegram API
        self.api_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""
        
        # Kiểm tra cấu hình
        if not self.token or not self.chat_id:
            self._load_config_from_file()
        
        # Thông báo trạng thái
        if self.enabled and self.token and self.chat_id:
            logger.info("Telegram Notifier đã được kích hoạt")
        elif not self.enabled:
            logger.info("Telegram Notifier đã được tắt")
        else:
            logger.warning("Telegram Notifier không thể kích hoạt do thiếu token hoặc chat_id")
            self.enabled = False
    
    def _load_config_from_file(self):
        """Tải cấu hình từ file"""
        config_files = [
            'telegram_config.json',
            'configs/telegram_config.json',
            'config.json',
            'configs/config.json',
            'account_config.json'
        ]
        
        for config_file in config_files:
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                    
                    self.token = self.token or config.get('telegram_bot_token')
                    self.chat_id = self.chat_id or config.get('telegram_chat_id')
                    
                    if self.token and self.chat_id:
                        self.api_url = f"https://api.telegram.org/bot{self.token}"
                        logger.info(f"Đã tải cấu hình Telegram từ {config_file}")
                        return
                except Exception as e:
                    logger.warning(f"Lỗi khi tải cấu hình Telegram từ {config_file}: {e}")
        
        logger.warning("Không tìm thấy cấu hình Telegram trong các file")
    
    def send_notification(self, level: str, message: str, parse_mode: str = "HTML") -> bool:
        """
        Gửi thông báo với mức độ được chỉ định
        
        Args:
            level: Mức độ thông báo (info, warning, error, success)
            message: Nội dung thông báo
            parse_mode: Chế độ phân tích cú pháp (HTML, Markdown)
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled:
            logger.info(f"Telegram Notifier đã bị tắt. Bỏ qua thông báo: {message[:50]}...")
            return False
        
        # Thêm emoji theo mức độ
        if level == "info":
            icon = "ℹ️"
        elif level == "warning":
            icon = "⚠️"
        elif level == "error":
            icon = "🔴"
        elif level == "success":
            icon = "✅"
        else:
            icon = "🔔"
        
        formatted_message = f"{icon} {message}"
        return self.send_message(formatted_message, parse_mode)
    
    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Gửi tin nhắn Telegram
        
        Args:
            message: Nội dung tin nhắn
            parse_mode: Chế độ phân tích cú pháp (HTML, Markdown)
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled or not self.token or not self.chat_id:
            logger.info(f"Bỏ qua tin nhắn Telegram: {message[:50]}...")
            return False
        
        try:
            url = f"{self.api_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                logger.info("Đã gửi tin nhắn Telegram thành công")
                return True
            else:
                logger.error(f"Lỗi khi gửi tin nhắn Telegram: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi tin nhắn Telegram: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def send_photo(self, photo_path: str, caption: str = "", parse_mode: str = "HTML") -> bool:
        """
        Gửi ảnh qua Telegram
        
        Args:
            photo_path: Đường dẫn đến file ảnh
            caption: Chú thích cho ảnh
            parse_mode: Chế độ phân tích cú pháp (HTML, Markdown)
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled or not self.token or not self.chat_id:
            logger.info(f"Bỏ qua gửi ảnh Telegram: {photo_path}")
            return False
        
        try:
            url = f"{self.api_url}/sendPhoto"
            
            # Kiểm tra xem file ảnh có tồn tại không
            if not os.path.exists(photo_path):
                logger.error(f"File ảnh không tồn tại: {photo_path}")
                return False
            
            with open(photo_path, 'rb') as photo:
                files = {'photo': photo}
                data = {
                    "chat_id": self.chat_id,
                    "caption": caption,
                    "parse_mode": parse_mode
                }
                
                response = requests.post(url, data=data, files=files, timeout=30)
                
                if response.status_code == 200:
                    logger.info(f"Đã gửi ảnh Telegram thành công: {photo_path}")
                    return True
                else:
                    logger.error(f"Lỗi khi gửi ảnh Telegram: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi ảnh Telegram: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def send_document(self, document_path: str, caption: str = "", parse_mode: str = "HTML") -> bool:
        """
        Gửi tài liệu qua Telegram
        
        Args:
            document_path: Đường dẫn đến file tài liệu
            caption: Chú thích cho tài liệu
            parse_mode: Chế độ phân tích cú pháp (HTML, Markdown)
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled or not self.token or not self.chat_id:
            logger.info(f"Bỏ qua gửi tài liệu Telegram: {document_path}")
            return False
        
        try:
            url = f"{self.api_url}/sendDocument"
            
            # Kiểm tra xem file tài liệu có tồn tại không
            if not os.path.exists(document_path):
                logger.error(f"File tài liệu không tồn tại: {document_path}")
                return False
            
            with open(document_path, 'rb') as document:
                files = {'document': document}
                data = {
                    "chat_id": self.chat_id,
                    "caption": caption,
                    "parse_mode": parse_mode
                }
                
                response = requests.post(url, data=data, files=files, timeout=30)
                
                if response.status_code == 200:
                    logger.info(f"Đã gửi tài liệu Telegram thành công: {document_path}")
                    return True
                else:
                    logger.error(f"Lỗi khi gửi tài liệu Telegram: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi tài liệu Telegram: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def send_market_analysis(self, market_data: Dict) -> bool:
        """
        Gửi phân tích thị trường
        
        Args:
            market_data: Dữ liệu phân tích thị trường
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled or not self.token or not self.chat_id:
            logger.info("Bỏ qua gửi phân tích thị trường Telegram")
            return False
        
        try:
            # Tạo tin nhắn phân tích thị trường
            message = "<b>📊 PHÂN TÍCH THỊ TRƯỜNG</b>\n\n"
            
            # Thêm thông tin thị trường tổng thể
            market_status = market_data.get('market_status', 'UNKNOWN')
            status_emoji = "🟢" if market_status == 'BULLISH' else "🔴" if market_status == 'BEARISH' else "⚪"
            
            message += f"<b>Trạng thái thị trường:</b> {status_emoji} {market_status}\n"
            message += f"<b>Giá BTC:</b> ${market_data.get('btc_price', 0):,.2f}\n"
            message += f"<b>Thay đổi 24h:</b> {market_data.get('btc_price_change_24h', 0):+.2f}%\n\n"
            
            # Thêm top gainers/losers
            if 'top_gainers' in market_data and market_data['top_gainers']:
                message += "<b>Top tăng giá:</b>\n"
                
                for i, coin in enumerate(market_data['top_gainers'][:3], 1):
                    symbol = coin.get('symbol', '').replace('USDT', '')
                    price = coin.get('price', 0)
                    change = coin.get('price_change_24h', 0)
                    
                    message += f"{i}. {symbol}: ${price:,.2f} ({change:+.2f}%)\n"
                
                message += "\n"
            
            if 'top_losers' in market_data and market_data['top_losers']:
                message += "<b>Top giảm giá:</b>\n"
                
                for i, coin in enumerate(market_data['top_losers'][:3], 1):
                    symbol = coin.get('symbol', '').replace('USDT', '')
                    price = coin.get('price', 0)
                    change = coin.get('price_change_24h', 0)
                    
                    message += f"{i}. {symbol}: ${price:,.2f} ({change:+.2f}%)\n"
                
                message += "\n"
            
            # Thêm phân tích BTC
            if 'btc_analysis' in market_data:
                btc_analysis = market_data['btc_analysis']
                btc_signal = btc_analysis.get('overall_signal', 'NEUTRAL')
                btc_confidence = btc_analysis.get('confidence', 0)
                
                message += "<b>Phân tích BTC:</b>\n"
                
                signal_emoji = "⚪"
                if btc_signal in ['STRONG_BUY', 'BUY']:
                    signal_emoji = "🟢"
                elif btc_signal in ['STRONG_SELL', 'SELL']:
                    signal_emoji = "🔴"
                
                message += f"- Tín hiệu: {signal_emoji} {btc_signal}\n"
                message += f"- Độ tin cậy: {btc_confidence}%\n\n"
            
            # Thêm chế độ thị trường
            if 'market_regime' in market_data:
                regime = market_data['market_regime']
                message += "<b>Chế độ thị trường:</b>\n"
                
                primary = regime.get('primary', 'RANGE_BOUND')
                volatility = regime.get('volatility', 'NORMAL')
                
                message += f"- Primary: {primary}\n"
                message += f"- Volatility: {volatility}\n\n"
            
            # Thêm thời gian
            message += f"⏱ <i>Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            # Gửi tin nhắn
            return self.send_message(message, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi phân tích thị trường Telegram: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def send_signal_alert(self, signal_data: Dict) -> bool:
        """
        Gửi cảnh báo tín hiệu giao dịch
        
        Args:
            signal_data: Dữ liệu tín hiệu giao dịch
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled or not self.token or not self.chat_id:
            logger.info("Bỏ qua gửi cảnh báo tín hiệu Telegram")
            return False
        
        try:
            # Lấy thông tin tín hiệu
            symbol = signal_data.get('symbol', 'UNKNOWN')
            signal = signal_data.get('signal', 'NEUTRAL')
            confidence = signal_data.get('confidence', 0)
            price = signal_data.get('price', 0)
            description = signal_data.get('description', '')
            
            # Xác định emoji và tiêu đề
            signal_emoji = "⚪"
            title = "CẬP NHẬT THỊ TRƯỜNG"
            
            if signal in ['STRONG_BUY', 'BUY']:
                signal_emoji = "🟢"
                title = "TÍN HIỆU MUA"
            elif signal in ['STRONG_SELL', 'SELL']:
                signal_emoji = "🔴"
                title = "TÍN HIỆU BÁN"
            
            # Tạo tin nhắn
            message = f"<b>{signal_emoji} {title}: {symbol}</b>\n\n"
            
            # Symbol và giá
            symbol_name = symbol.replace("USDT", "")
            message += f"<b>{symbol_name}:</b> ${price:,.2f}\n"
            message += f"<b>Tín hiệu:</b> {signal}\n"
            message += f"<b>Độ tin cậy:</b> {confidence}%\n\n"
            
            # Thêm giá mục tiêu và stop loss
            target_price = signal_data.get('target_price', 0)
            stop_loss = signal_data.get('stop_loss', 0)
            
            if target_price > 0:
                target_pct = (target_price - price) / price * 100
                message += f"<b>Giá mục tiêu:</b> ${target_price:,.2f} ({target_pct:+.2f}%)\n"
            
            if stop_loss > 0:
                sl_pct = (stop_loss - price) / price * 100
                message += f"<b>Stop Loss:</b> ${stop_loss:,.2f} ({sl_pct:+.2f}%)\n\n"
            
            # Thêm mô tả
            if description:
                message += f"<b>Phân tích:</b>\n{description}\n\n"
            
            # Thêm thời gian
            message += f"⏱ <i>Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            # Gửi tin nhắn
            return self.send_message(message, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi cảnh báo tín hiệu Telegram: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def send_trade_notification(self, trade_data: Dict) -> bool:
        """
        Gửi thông báo giao dịch
        
        Args:
            trade_data: Dữ liệu giao dịch
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled or not self.token or not self.chat_id:
            logger.info("Bỏ qua gửi thông báo giao dịch Telegram")
            return False
        
        try:
            # Lấy thông tin giao dịch
            symbol = trade_data.get('symbol', 'UNKNOWN')
            side = trade_data.get('side', 'UNKNOWN')
            entry_price = trade_data.get('entry_price', 0)
            quantity = trade_data.get('quantity', 0)
            take_profit = trade_data.get('take_profit', 0)
            stop_loss = trade_data.get('stop_loss', 0)
            reason = trade_data.get('reason', '')
            
            # Xác định emoji và tiêu đề
            if side == 'BUY':
                emoji = "🟢"
                title = "MUA/LONG"
            elif side == 'SELL':
                emoji = "🔴"
                title = "BÁN/SHORT"
            else:
                emoji = "⚪"
                title = "GIAO DỊCH"
            
            # Tạo tin nhắn
            message = f"<b>{emoji} {title}: {symbol}</b>\n\n"
            
            # Symbol và giá
            symbol_name = symbol.replace("USDT", "")
            message += f"<b>{symbol_name}:</b> ${entry_price:,.2f}\n"
            message += f"<b>Số lượng:</b> {quantity}\n"
            
            # Thêm take profit và stop loss
            if take_profit > 0:
                tp_pct = (take_profit - entry_price) / entry_price * 100
                tp_sign = "+" if side == 'BUY' else "-"
                message += f"<b>Take Profit:</b> ${take_profit:,.2f} ({tp_sign}{abs(tp_pct):.2f}%)\n"
            
            if stop_loss > 0:
                sl_pct = (stop_loss - entry_price) / entry_price * 100
                sl_sign = "-" if side == 'BUY' else "+"
                message += f"<b>Stop Loss:</b> ${stop_loss:,.2f} ({sl_sign}{abs(sl_pct):.2f}%)\n"
            
            # Tính Risk/Reward
            if take_profit > 0 and stop_loss > 0:
                if side == 'BUY':
                    risk = entry_price - stop_loss
                    reward = take_profit - entry_price
                else:
                    risk = stop_loss - entry_price
                    reward = entry_price - take_profit
                
                if risk > 0:
                    rr_ratio = reward / risk
                    message += f"<b>Risk/Reward:</b> 1:{rr_ratio:.2f}\n"
            
            message += "\n"
            
            # Thêm lý do
            if reason:
                message += f"<b>Lý do:</b>\n{reason}\n\n"
            
            # Thêm thời gian
            message += f"⏱ <i>Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            # Gửi tin nhắn
            return self.send_message(message, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo giao dịch Telegram: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def send_bot_status(self, status_data: Dict) -> bool:
        """
        Gửi trạng thái của bot
        
        Args:
            status_data: Dữ liệu trạng thái
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled or not self.token or not self.chat_id:
            logger.info("Bỏ qua gửi trạng thái bot Telegram")
            return False
        
        try:
            # Lấy thông tin trạng thái
            status = status_data.get('status', 'UNKNOWN')
            uptime = status_data.get('uptime', 0)
            active_positions = status_data.get('active_positions', 0)
            account_balance = status_data.get('account_balance', 0)
            pnl_24h = status_data.get('pnl_24h', 0)
            
            # Xác định emoji
            if status == 'RUNNING':
                emoji = "✅"
            elif status == 'STOPPED':
                emoji = "🛑"
            elif status == 'WARNING':
                emoji = "⚠️"
            elif status == 'ERROR':
                emoji = "🔴"
            else:
                emoji = "ℹ️"
            
            # Tạo tin nhắn
            message = f"<b>{emoji} BOT STATUS: {status}</b>\n\n"
            
            # Thêm thông tin
            message += f"<b>Uptime:</b> {uptime}\n"
            message += f"<b>Vị thế hoạt động:</b> {active_positions}\n"
            message += f"<b>Số dư tài khoản:</b> ${account_balance:,.2f}\n"
            
            if pnl_24h != 0:
                pnl_emoji = "📈" if pnl_24h > 0 else "📉"
                message += f"<b>P&L 24h:</b> {pnl_emoji} ${pnl_24h:+,.2f}\n\n"
            
            # Thêm thông tin bổ sung
            if 'additional_info' in status_data:
                message += "<b>Thông tin bổ sung:</b>\n"
                
                for key, value in status_data['additional_info'].items():
                    message += f"- {key}: {value}\n"
                
                message += "\n"
            
            # Thêm thời gian
            message += f"⏱ <i>Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            # Gửi tin nhắn
            return self.send_message(message, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi trạng thái bot Telegram: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def send_startup_notification(self) -> bool:
        """
        Gửi thông báo khởi động hệ thống
        
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        message = "<b>🚀 HỆ THỐNG ĐÃ KHỞI ĐỘNG</b>\n\n"
        message += f"<b>Phiên bản:</b> 1.0.0\n"
        message += f"<b>Thời gian khởi động:</b> {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n"
        
        # Lấy thông tin tài khoản nếu có thể
        try:
            from enhanced_binance_api import get_account_balance
            balance = get_account_balance(testnet=True)
            
            if balance:
                message += "\n<b>Số dư tài khoản:</b>\n"
                
                for symbol, amount in balance.items():
                    if amount > 0:
                        message += f"- {symbol}: {amount:,.2f}\n"
        except Exception:
            pass
        
        return self.send_notification("info", message)

# Test nếu chạy trực tiếp
if __name__ == "__main__":
    # Thiết lập logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Kiểm tra và test thông báo
    notifier = TelegramNotifier()
    
    if notifier.enabled:
        print("Telegram Notifier đã được kích hoạt")
        
        # Gửi thông báo thử nghiệm
        notifier.send_notification("info", "Đây là thông báo thử nghiệm từ <b>Telegram Notifier</b>")
        
        # Gửi thông báo khởi động
        notifier.send_startup_notification()
    else:
        print("Telegram Notifier không được kích hoạt")
        print("Hãy cung cấp TELEGRAM_BOT_TOKEN và TELEGRAM_CHAT_ID trong biến môi trường hoặc file cấu hình")