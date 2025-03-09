#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram Position Notifier

Gửi thông báo về vị thế giao dịch qua Telegram
"""

import os
import sys
import time
import json
import logging
import argparse
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('telegram_notifier.log')
    ]
)
logger = logging.getLogger('telegram_notifier')

# Đặt đường dẫn hiện tại vào sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Import các module cần thiết
try:
    from binance_api import BinanceAPI
except ImportError:
    logger.error("Không thể import module BinanceAPI")
    sys.exit(1)

class TelegramNotifier:
    """Class để gửi thông báo qua Telegram"""
    
    def __init__(self, testnet: bool = False):
        """Khởi tạo Telegram Notifier
        
        Args:
            testnet: Sử dụng testnet Binance nếu True
        """
        self.testnet = testnet
        self.api = BinanceAPI(testnet=testnet)
        
        # Đọc thông tin Telegram từ biến môi trường hoặc file cấu hình
        self.telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        
        if not self.telegram_token or not self.telegram_chat_id:
            logger.warning("Không tìm thấy thông tin Telegram trong biến môi trường")
            # Thử đọc từ file cấu hình
            try:
                if os.path.exists('configs/telegram_config.json'):
                    with open('configs/telegram_config.json', 'r') as f:
                        config = json.load(f)
                        if not self.telegram_token:
                            self.telegram_token = config.get('bot_token')
                        if not self.telegram_chat_id:
                            self.telegram_chat_id = config.get('chat_id')
                    logger.info("Đã đọc thông tin Telegram từ file cấu hình")
            except Exception as e:
                logger.error(f"Lỗi khi đọc file cấu hình Telegram: {str(e)}")
        
        if not self.telegram_token or not self.telegram_chat_id:
            logger.error("Không thể tìm thấy thông tin Telegram, không thể gửi thông báo")
        else:
            logger.info("Đã khởi tạo Telegram Notifier thành công")
    
    def send_message(self, message: str) -> bool:
        """Gửi tin nhắn tới Telegram
        
        Args:
            message: Nội dung tin nhắn
            
        Returns:
            bool: True nếu gửi thành công
        """
        if not self.telegram_token or not self.telegram_chat_id:
            logger.error("Không có thông tin Telegram, không thể gửi thông báo")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, data=data)
            
            if response.status_code == 200:
                logger.info("Đã gửi thông báo Telegram thành công")
                return True
            else:
                logger.error(f"Lỗi khi gửi thông báo Telegram: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo Telegram: {str(e)}")
            return False
    
    def get_account_summary(self) -> Dict[str, Any]:
        """Lấy thông tin tóm tắt về tài khoản
        
        Returns:
            Dict[str, Any]: Thông tin tài khoản
        """
        try:
            account_info = self.api.get_futures_account_info()
            balance = float(account_info.get('totalWalletBalance', 0))
            unrealized_pnl = float(account_info.get('totalUnrealizedProfit', 0))
            
            available_balance = float(account_info.get('availableBalance', 0))
            positions = self.api.get_futures_position_risk()
            active_positions = [p for p in positions if abs(float(p.get('positionAmt', 0))) > 0]
            
            return {
                "balance": balance,
                "unrealized_pnl": unrealized_pnl,
                "total_balance": balance + unrealized_pnl,
                "available_balance": available_balance,
                "active_positions": len(active_positions),
                "positions": active_positions
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin tài khoản: {str(e)}")
            return {}
    
    def format_account_message(self) -> str:
        """Tạo tin nhắn thông tin tài khoản
        
        Returns:
            str: Tin nhắn đã định dạng
        """
        summary = self.get_account_summary()
        
        if not summary:
            return "❌ Không thể lấy thông tin tài khoản"
        
        mode = "TESTNET" if self.testnet else "MAINNET"
        
        message = f"<b>🔷 THÔNG TIN TÀI KHOẢN {mode}</b>\n\n"
        message += f"💰 Số dư: {summary.get('balance', 0):.2f} USDT\n"
        message += f"📊 Lợi nhuận chưa thực hiện: {summary.get('unrealized_pnl', 0):.2f} USDT\n"
        message += f"💵 Tổng số dư: {summary.get('total_balance', 0):.2f} USDT\n"
        message += f"💳 Số dư khả dụng: {summary.get('available_balance', 0):.2f} USDT\n\n"
        
        active_positions = summary.get('positions', [])
        
        if active_positions:
            message += f"<b>📌 VỊ THẾ ĐANG MỞ ({len(active_positions)})</b>\n\n"
            
            for pos in active_positions:
                symbol = pos.get('symbol', '')
                side = "LONG" if float(pos.get('positionAmt', 0)) > 0 else "SHORT"
                entry_price = float(pos.get('entryPrice', 0))
                mark_price = float(pos.get('markPrice', 0))
                pnl = float(pos.get('unRealizedProfit', 0))
                roe = float(pos.get('roe', 0)) * 100  # Convert to percentage
                
                icon = "🟢" if side == "LONG" else "🔴"
                pnl_icon = "✅" if pnl > 0 else "❌"
                
                message += f"{icon} <b>{symbol} {side}</b>\n"
                message += f"💲 Giá vào: {entry_price:.2f} | Giá hiện tại: {mark_price:.2f}\n"
                message += f"{pnl_icon} P/L: {pnl:.2f} USDT ({roe:.2f}%)\n\n"
        else:
            message += "📌 Không có vị thế nào đang mở\n"
        
        message += f"\n⏱ Cập nhật: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return message
    
    def notify_position_status(self) -> bool:
        """Gửi thông báo về trạng thái vị thế
        
        Returns:
            bool: True nếu gửi thành công
        """
        message = self.format_account_message()
        return self.send_message(message)

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Gửi thông báo về vị thế qua Telegram')
    parser.add_argument('--testnet', action='store_true', help='Sử dụng Binance Testnet')
    parser.add_argument('--message', type=str, help='Gửi tin nhắn tùy chỉnh thay vì thông tin vị thế')
    args = parser.parse_args()
    
    try:
        notifier = TelegramNotifier(testnet=args.testnet)
        
        if args.message:
            # Gửi tin nhắn tùy chỉnh
            result = notifier.send_message(args.message)
        else:
            # Gửi thông tin vị thế
            result = notifier.notify_position_status()
        
        if result:
            logger.info("Đã gửi thông báo thành công")
        else:
            logger.error("Không thể gửi thông báo")
            
    except Exception as e:
        logger.error(f"Lỗi không mong muốn: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()