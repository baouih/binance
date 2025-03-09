#!/usr/bin/env python3
"""
Module tăng cường thông báo và ghi log giao dịch

Module này cải thiện hệ thống thông báo và ghi log chi tiết về các giao dịch,
hỗ trợ nhiều kênh thông báo (Telegram, Discord, Email) và lưu trữ lịch sử giao dịch
"""

import os
import json
import time
import logging
import datetime
from typing import Dict, List, Union, Optional
from telegram_notifier import TelegramNotifier

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("enhanced_notifications")

# File lưu trữ
TRADE_HISTORY_FILE = 'trade_history.json'
NOTIFICATION_CONFIG_FILE = 'notification_config.json'

class EnhancedNotifications:
    """Lớp quản lý thông báo nâng cao"""
    
    def __init__(self, config_path: str = NOTIFICATION_CONFIG_FILE):
        """
        Khởi tạo quản lý thông báo
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình thông báo
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # Khởi tạo các kênh thông báo
        self.telegram = self._init_telegram() if self.config.get('telegram', {}).get('enabled', False) else None
        
        # Lịch sử thông báo
        self.notification_history = []
        
        # Lịch sử giao dịch
        self.trade_history = self._load_trade_history()
    
    def _load_config(self) -> Dict:
        """
        Tải cấu hình thông báo từ file
        
        Returns:
            Dict: Cấu hình thông báo
        """
        try:
            if not os.path.exists(self.config_path):
                # Tạo cấu hình mặc định
                default_config = {
                    'telegram': {
                        'enabled': True,
                        'bot_token': None,  # Sẽ lấy từ file telegram_config.json
                        'chat_id': None,    # Sẽ lấy từ file telegram_config.json
                        'rate_limit': 5,    # Giới hạn số thông báo mỗi phút
                    },
                    'discord': {
                        'enabled': False,
                        'webhook_url': '',
                        'rate_limit': 10,
                    },
                    'email': {
                        'enabled': False,
                        'smtp_server': '',
                        'smtp_port': 587,
                        'username': '',
                        'password': '',
                        'from_email': '',
                        'to_email': '',
                        'rate_limit': 10,
                    },
                    'notification_levels': {
                        'trade_opened': True,
                        'trade_closed': True,
                        'trailing_stop_activated': True,
                        'partial_exit': True,
                        'stop_loss_hit': True,
                        'take_profit_hit': True,
                        'error': True,
                        'warning': True,
                        'info': False,
                        'daily_summary': True,
                    },
                    'thresholds': {
                        'min_profit_notify': 1.0,  # % lợi nhuận tối thiểu để thông báo
                        'min_loss_notify': 1.0,    # % lỗ tối thiểu để thông báo
                        'significant_trade_amount': 100.0,  # USD, thông báo ưu tiên khi vượt ngưỡng này
                    },
                    'schedule': {
                        'daily_summary_time': '20:00',  # Thời gian gửi báo cáo hàng ngày
                        'quiet_hours_start': '23:00',   # Bắt đầu giờ yên tĩnh
                        'quiet_hours_end': '07:00',     # Kết thúc giờ yên tĩnh
                    },
                    'language': 'vi',  # Ngôn ngữ thông báo: 'en' hoặc 'vi'
                }
                
                # Lưu cấu hình mặc định
                with open(self.config_path, 'w') as f:
                    json.dump(default_config, f, indent=4)
                
                logger.info(f"Đã tạo file cấu hình mặc định tại {self.config_path}")
                return default_config
            else:
                # Tải cấu hình từ file
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                
                logger.info(f"Đã tải cấu hình thông báo từ {self.config_path}")
                return config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình thông báo: {str(e)}")
            return {
                'telegram': {'enabled': False},
                'notification_levels': {'error': True, 'trade_closed': True, 'trade_opened': True},
                'language': 'vi'
            }
    
    def _init_telegram(self) -> Optional[TelegramNotifier]:
        """
        Khởi tạo kênh thông báo Telegram
        
        Returns:
            Optional[TelegramNotifier]: Đối tượng TelegramNotifier hoặc None nếu lỗi
        """
        try:
            # Tải thông tin token & chat_id từ config
            if not self.config['telegram'].get('bot_token') or not self.config['telegram'].get('chat_id'):
                # Thử tải từ file telegram_config.json
                if os.path.exists('telegram_config.json'):
                    with open('telegram_config.json', 'r') as f:
                        telegram_config = json.load(f)
                    
                    self.config['telegram']['bot_token'] = telegram_config.get('bot_token')
                    self.config['telegram']['chat_id'] = telegram_config.get('chat_id')
                else:
                    logger.error("Không tìm thấy thông tin bot_token và chat_id Telegram")
                    return None
            
            # Tạo đối tượng TelegramNotifier
            return TelegramNotifier(
                token=self.config['telegram']['bot_token'],
                chat_id=self.config['telegram']['chat_id']
            )
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo kênh thông báo Telegram: {str(e)}")
            return None
    
    def _load_trade_history(self) -> List[Dict]:
        """
        Tải lịch sử giao dịch từ file
        
        Returns:
            List[Dict]: Lịch sử giao dịch
        """
        try:
            if os.path.exists(TRADE_HISTORY_FILE):
                with open(TRADE_HISTORY_FILE, 'r') as f:
                    trade_history = json.load(f)
                logger.info(f"Đã tải {len(trade_history)} giao dịch từ {TRADE_HISTORY_FILE}")
                return trade_history
            else:
                logger.info(f"Không tìm thấy file {TRADE_HISTORY_FILE}, tạo mới")
                return []
        except Exception as e:
            logger.error(f"Lỗi khi tải lịch sử giao dịch: {str(e)}")
            return []
    
    def _save_trade_history(self) -> bool:
        """
        Lưu lịch sử giao dịch vào file
        
        Returns:
            bool: True nếu lưu thành công, False nếu thất bại
        """
        try:
            with open(TRADE_HISTORY_FILE, 'w') as f:
                json.dump(self.trade_history, f, indent=4)
            logger.info(f"Đã lưu {len(self.trade_history)} giao dịch vào {TRADE_HISTORY_FILE}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu lịch sử giao dịch: {str(e)}")
            return False
    
    def log_trade(self, trade_data: Dict) -> bool:
        """
        Ghi log một giao dịch mới
        
        Args:
            trade_data (Dict): Thông tin giao dịch
            
        Returns:
            bool: True nếu ghi log thành công, False nếu thất bại
        """
        try:
            # Thêm timestamp nếu chưa có
            if 'timestamp' not in trade_data:
                trade_data['timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Thêm ID giao dịch nếu chưa có
            if 'trade_id' not in trade_data:
                trade_data['trade_id'] = f"{int(time.time())}-{trade_data['symbol']}"
            
            # Thêm giao dịch vào lịch sử
            self.trade_history.append(trade_data)
            
            # Lưu lịch sử giao dịch
            self._save_trade_history()
            
            # Gửi thông báo nếu cần
            self._notify_trade(trade_data)
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi ghi log giao dịch: {str(e)}")
            return False
    
    def log_position_update(self, position_data: Dict) -> bool:
        """
        Ghi log cập nhật vị thế
        
        Args:
            position_data (Dict): Thông tin vị thế
            
        Returns:
            bool: True nếu ghi log thành công, False nếu thất bại
        """
        try:
            # Tìm giao dịch tương ứng trong lịch sử
            symbol = position_data.get('symbol')
            found = False
            
            for trade in self.trade_history:
                if (trade.get('symbol') == symbol and 
                    trade.get('side') == position_data.get('side') and
                    trade.get('status') != 'CLOSED'):
                    
                    # Cập nhật thông tin vị thế
                    trade['position_updates'] = trade.get('position_updates', [])
                    update_data = {
                        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'current_price': position_data.get('current_price'),
                        'trailing_stop': position_data.get('trailing_stop'),
                        'trailing_activated': position_data.get('trailing_activated', False),
                        'profit_percent': position_data.get('profit_percent')
                    }
                    trade['position_updates'].append(update_data)
                    
                    # Gửi thông báo nếu trailing stop được kích hoạt lần đầu
                    if (position_data.get('trailing_activated', False) and 
                        len(trade['position_updates']) > 1 and
                        not trade['position_updates'][-2].get('trailing_activated', False)):
                        
                        self._notify_trailing_stop_activated(position_data)
                    
                    found = True
                    break
            
            if not found and position_data.get('status') != 'CLOSED':
                # Tạo giao dịch mới nếu không tìm thấy
                trade_data = {
                    'trade_id': f"{int(time.time())}-{symbol}",
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'symbol': symbol,
                    'side': position_data.get('side'),
                    'entry_price': position_data.get('entry_price'),
                    'quantity': position_data.get('quantity'),
                    'leverage': position_data.get('leverage'),
                    'status': 'OPEN',
                    'position_updates': [{
                        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'current_price': position_data.get('current_price'),
                        'trailing_stop': position_data.get('trailing_stop'),
                        'trailing_activated': position_data.get('trailing_activated', False),
                        'profit_percent': position_data.get('profit_percent')
                    }]
                }
                self.trade_history.append(trade_data)
                
                # Gửi thông báo giao dịch mới
                self._notify_trade(trade_data)
            
            # Lưu lịch sử giao dịch
            self._save_trade_history()
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi log cập nhật vị thế: {str(e)}")
            return False
    
    def log_position_closed(self, position_data: Dict) -> bool:
        """
        Ghi log đóng vị thế
        
        Args:
            position_data (Dict): Thông tin vị thế đóng
            
        Returns:
            bool: True nếu ghi log thành công, False nếu thất bại
        """
        try:
            # Tìm giao dịch tương ứng trong lịch sử
            symbol = position_data.get('symbol')
            found = False
            
            for trade in self.trade_history:
                if (trade.get('symbol') == symbol and 
                    trade.get('side') == position_data.get('side') and
                    trade.get('status') != 'CLOSED'):
                    
                    # Cập nhật thông tin vị thế
                    trade['status'] = 'CLOSED'
                    trade['exit_price'] = position_data.get('exit_price')
                    trade['exit_time'] = position_data.get('exit_time', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    trade['profit_loss'] = position_data.get('profit_loss')
                    trade['profit_percent'] = position_data.get('profit_percent')
                    trade['close_reason'] = position_data.get('close_reason', 'manual')
                    
                    # Gửi thông báo đóng vị thế
                    self._notify_position_closed(trade)
                    
                    found = True
                    break
            
            if not found:
                logger.warning(f"Không tìm thấy vị thế {symbol} {position_data.get('side')} trong lịch sử để đánh dấu đóng")
            
            # Lưu lịch sử giao dịch
            self._save_trade_history()
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi log đóng vị thế: {str(e)}")
            return False
    
    def _notify_trade(self, trade_data: Dict) -> bool:
        """
        Gửi thông báo về giao dịch mới
        
        Args:
            trade_data (Dict): Thông tin giao dịch
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
        """
        try:
            # Kiểm tra nếu thông báo được bật
            if not self.config.get('notification_levels', {}).get('trade_opened', True):
                return False
            
            # Kiểm tra kênh thông báo
            if self.telegram:
                try:
                    # Xác định ngôn ngữ
                    lang = self.config.get('language', 'vi')
                    
                    # Tạo thông báo
                    if lang == 'vi':
                        symbol = trade_data.get('symbol', '')
                        side = 'MUA' if trade_data.get('side') == 'LONG' or trade_data.get('side') == 'BUY' else 'BÁN'
                        entry_price = trade_data.get('entry_price', 0)
                        quantity = trade_data.get('quantity', 0)
                        leverage = trade_data.get('leverage', 1)
                        usd_value = entry_price * quantity
                        
                        message = f"🔔 *GD MỚI: {symbol} {side}*\n\n"
                        message += f"💰 Giá vào: {entry_price:.2f} USDT\n"
                        message += f"🔢 Số lượng: {quantity}\n"
                        message += f"📊 Giá trị: {usd_value:.2f} USDT\n"
                        message += f"⚡ Đòn bẩy: {leverage}x\n"
                        message += f"⏱ Thời gian: {trade_data.get('timestamp')}\n\n"
                        message += f"🎯 Theo dõi tại: `{symbol} {side}`"
                    else:
                        symbol = trade_data.get('symbol', '')
                        side = 'BUY' if trade_data.get('side') == 'LONG' or trade_data.get('side') == 'BUY' else 'SELL'
                        entry_price = trade_data.get('entry_price', 0)
                        quantity = trade_data.get('quantity', 0)
                        leverage = trade_data.get('leverage', 1)
                        usd_value = entry_price * quantity
                        
                        message = f"🔔 *NEW TRADE: {symbol} {side}*\n\n"
                        message += f"💰 Entry price: {entry_price:.2f} USDT\n"
                        message += f"🔢 Quantity: {quantity}\n"
                        message += f"📊 Value: {usd_value:.2f} USDT\n"
                        message += f"⚡ Leverage: {leverage}x\n"
                        message += f"⏱ Time: {trade_data.get('timestamp')}\n\n"
                        message += f"🎯 Track with: `{symbol} {side}`"
                    
                    # Gửi thông báo
                    self.telegram.send_message(message, parse_mode='Markdown')
                    logger.info(f"Đã gửi thông báo giao dịch mới qua Telegram: {symbol} {side}")
                    return True
                except Exception as e:
                    logger.error(f"Lỗi khi gửi thông báo Telegram: {str(e)}")
                    return False
            else:
                logger.warning("Không có kênh thông báo Telegram")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo giao dịch: {str(e)}")
            return False
    
    def _notify_position_closed(self, trade_data: Dict) -> bool:
        """
        Gửi thông báo về đóng vị thế
        
        Args:
            trade_data (Dict): Thông tin giao dịch đã đóng
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
        """
        try:
            # Kiểm tra nếu thông báo được bật
            if not self.config.get('notification_levels', {}).get('trade_closed', True):
                return False
            
            # Kiểm tra ngưỡng thông báo
            profit_percent = trade_data.get('profit_percent', 0)
            min_profit = self.config.get('thresholds', {}).get('min_profit_notify', 1.0)
            min_loss = self.config.get('thresholds', {}).get('min_loss_notify', 1.0)
            
            if profit_percent > 0 and profit_percent < min_profit:
                logger.info(f"Lợi nhuận {profit_percent:.2f}% dưới ngưỡng thông báo {min_profit}%")
                return False
            
            if profit_percent < 0 and abs(profit_percent) < min_loss:
                logger.info(f"Lỗ {abs(profit_percent):.2f}% dưới ngưỡng thông báo {min_loss}%")
                return False
            
            # Kiểm tra kênh thông báo
            if self.telegram:
                try:
                    # Xác định ngôn ngữ
                    lang = self.config.get('language', 'vi')
                    
                    # Tạo thông báo
                    if lang == 'vi':
                        symbol = trade_data.get('symbol', '')
                        side = 'MUA' if trade_data.get('side') == 'LONG' or trade_data.get('side') == 'BUY' else 'BÁN'
                        entry_price = trade_data.get('entry_price', 0)
                        exit_price = trade_data.get('exit_price', 0)
                        quantity = trade_data.get('quantity', 0)
                        leverage = trade_data.get('leverage', 1)
                        profit_percent = trade_data.get('profit_percent', 0)
                        profit_loss = trade_data.get('profit_loss', 0)
                        close_reason = trade_data.get('close_reason', 'manual')
                        
                        # Emoji tương ứng với kết quả
                        if profit_percent > 0:
                            result_emoji = "✅ LỜI"
                        else:
                            result_emoji = "❌ LỖ"
                        
                        # Emoji tương ứng với lý do đóng
                        reason_emoji = "🔄"
                        if close_reason == 'take_profit':
                            reason_emoji = "🎯"
                        elif close_reason == 'stop_loss':
                            reason_emoji = "🛑"
                        elif close_reason == 'trailing_stop':
                            reason_emoji = "📉"
                        
                        message = f"{result_emoji} *ĐÓNG: {symbol} {side}*\n\n"
                        message += f"💰 Giá vào: {entry_price:.2f} → Giá ra: {exit_price:.2f}\n"
                        message += f"🔢 Số lượng: {quantity}\n"
                        message += f"⚡ Đòn bẩy: {leverage}x\n"
                        message += f"💵 Lợi nhuận: {profit_loss:.2f} USDT ({profit_percent:.2f}%)\n"
                        message += f"⏱ Thời gian: {trade_data.get('exit_time')}\n"
                        message += f"{reason_emoji} Lý do: {close_reason}\n"
                    else:
                        symbol = trade_data.get('symbol', '')
                        side = 'BUY' if trade_data.get('side') == 'LONG' or trade_data.get('side') == 'BUY' else 'SELL'
                        entry_price = trade_data.get('entry_price', 0)
                        exit_price = trade_data.get('exit_price', 0)
                        quantity = trade_data.get('quantity', 0)
                        leverage = trade_data.get('leverage', 1)
                        profit_percent = trade_data.get('profit_percent', 0)
                        profit_loss = trade_data.get('profit_loss', 0)
                        close_reason = trade_data.get('close_reason', 'manual')
                        
                        # Emoji tương ứng với kết quả
                        if profit_percent > 0:
                            result_emoji = "✅ PROFIT"
                        else:
                            result_emoji = "❌ LOSS"
                        
                        # Emoji tương ứng với lý do đóng
                        reason_emoji = "🔄"
                        if close_reason == 'take_profit':
                            reason_emoji = "🎯"
                        elif close_reason == 'stop_loss':
                            reason_emoji = "🛑"
                        elif close_reason == 'trailing_stop':
                            reason_emoji = "📉"
                        
                        message = f"{result_emoji} *CLOSED: {symbol} {side}*\n\n"
                        message += f"💰 Entry: {entry_price:.2f} → Exit: {exit_price:.2f}\n"
                        message += f"🔢 Quantity: {quantity}\n"
                        message += f"⚡ Leverage: {leverage}x\n"
                        message += f"💵 Profit: {profit_loss:.2f} USDT ({profit_percent:.2f}%)\n"
                        message += f"⏱ Time: {trade_data.get('exit_time')}\n"
                        message += f"{reason_emoji} Reason: {close_reason}\n"
                    
                    # Gửi thông báo
                    self.telegram.send_message(message, parse_mode='Markdown')
                    logger.info(f"Đã gửi thông báo đóng vị thế qua Telegram: {symbol} {side}")
                    return True
                except Exception as e:
                    logger.error(f"Lỗi khi gửi thông báo Telegram: {str(e)}")
                    return False
            else:
                logger.warning("Không có kênh thông báo Telegram")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo đóng vị thế: {str(e)}")
            return False
    
    def _notify_trailing_stop_activated(self, position_data: Dict) -> bool:
        """
        Gửi thông báo về kích hoạt trailing stop
        
        Args:
            position_data (Dict): Thông tin vị thế
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
        """
        try:
            # Kiểm tra nếu thông báo được bật
            if not self.config.get('notification_levels', {}).get('trailing_stop_activated', True):
                return False
            
            # Kiểm tra kênh thông báo
            if self.telegram:
                try:
                    # Xác định ngôn ngữ
                    lang = self.config.get('language', 'vi')
                    
                    # Tạo thông báo
                    if lang == 'vi':
                        symbol = position_data.get('symbol', '')
                        side = 'MUA' if position_data.get('side') == 'LONG' or position_data.get('side') == 'BUY' else 'BÁN'
                        current_price = position_data.get('current_price', 0)
                        trailing_stop = position_data.get('trailing_stop', 0)
                        profit_percent = position_data.get('profit_percent', 0)
                        
                        message = f"📉 *TRAILING STOP: {symbol} {side}*\n\n"
                        message += f"💰 Giá hiện tại: {current_price:.2f} USDT\n"
                        message += f"🛑 Trailing stop: {trailing_stop:.2f} USDT\n"
                        message += f"📊 Lợi nhuận: {profit_percent:.2f}%\n"
                        message += f"⏱ Thời gian: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    else:
                        symbol = position_data.get('symbol', '')
                        side = 'BUY' if position_data.get('side') == 'LONG' or position_data.get('side') == 'BUY' else 'SELL'
                        current_price = position_data.get('current_price', 0)
                        trailing_stop = position_data.get('trailing_stop', 0)
                        profit_percent = position_data.get('profit_percent', 0)
                        
                        message = f"📉 *TRAILING STOP: {symbol} {side}*\n\n"
                        message += f"💰 Current price: {current_price:.2f} USDT\n"
                        message += f"🛑 Trailing stop: {trailing_stop:.2f} USDT\n"
                        message += f"📊 Profit: {profit_percent:.2f}%\n"
                        message += f"⏱ Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    
                    # Gửi thông báo
                    self.telegram.send_message(message, parse_mode='Markdown')
                    logger.info(f"Đã gửi thông báo kích hoạt trailing stop qua Telegram: {symbol} {side}")
                    return True
                except Exception as e:
                    logger.error(f"Lỗi khi gửi thông báo Telegram: {str(e)}")
                    return False
            else:
                logger.warning("Không có kênh thông báo Telegram")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo trailing stop: {str(e)}")
            return False

def send_test_notification():
    """
    Gửi thông báo kiểm tra
    
    Returns:
        bool: True nếu gửi thành công, False nếu thất bại
    """
    try:
        # Khởi tạo đối tượng thông báo
        notification = EnhancedNotifications()
        
        # Tạo thông tin giao dịch giả
        trade_data = {
            'trade_id': f"test-{int(time.time())}",
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': 'BTCUSDT',
            'side': 'LONG',
            'entry_price': 90000,
            'quantity': 0.05,
            'leverage': 10,
            'status': 'OPEN'
        }
        
        # Gửi thông báo giao dịch mới
        notification._notify_trade(trade_data)
        
        # Thông báo trailing stop kích hoạt
        position_data = {
            'symbol': 'BTCUSDT',
            'side': 'LONG',
            'current_price': 92000,
            'trailing_stop': 91000,
            'profit_percent': 22.2
        }
        notification._notify_trailing_stop_activated(position_data)
        
        # Thông báo đóng vị thế
        trade_data.update({
            'status': 'CLOSED',
            'exit_price': 93000,
            'exit_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'profit_loss': 150,
            'profit_percent': 33.3,
            'close_reason': 'trailing_stop'
        })
        notification._notify_position_closed(trade_data)
        
        logger.info("Đã gửi thông báo kiểm tra thành công")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi gửi thông báo kiểm tra: {str(e)}")
        return False

if __name__ == "__main__":
    print("Đang gửi thông báo kiểm tra...")
    send_test_notification()