#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module thông báo chi tiết về giao dịch

Module này cải thiện việc gửi thông báo giao dịch chi tiết qua Telegram, bao gồm:
1. Thông báo vào lệnh với đầy đủ thông tin
2. Thông báo ra lệnh với chi tiết lãi/lỗ
3. Thống kê giao dịch theo ngày, tuần, tháng
4. Chi tiết lý do vào lệnh và ra lệnh
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("detailed_trade_notifications.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("detailed_trade_notifications")

# Import module Telegram Notifier
try:
    from telegram_notifier import TelegramNotifier
except ImportError as e:
    logger.error(f"Lỗi import module: {e}")
    logger.error("Đảm bảo đang chạy từ thư mục gốc của dự án")
    sys.exit(1)

class DetailedTradeNotifications:
    """Lớp thông báo chi tiết về giao dịch với các thông tin đầy đủ"""
    
    def __init__(self, trade_history_file: str = 'trade_history.json'):
        """
        Khởi tạo hệ thống thông báo giao dịch chi tiết
        
        Args:
            trade_history_file (str): Đường dẫn đến file lưu lịch sử giao dịch
        """
        self.trade_history_file = trade_history_file
        self.telegram = TelegramNotifier()
        
        # Lịch sử giao dịch
        self.trade_history = self._load_trade_history()
        
        # Thống kê
        self.daily_stats = {}
        self.weekly_stats = {}
        self.monthly_stats = {}
        
        # Cập nhật thống kê
        self._update_statistics()
        
        logger.info("Đã khởi tạo hệ thống thông báo giao dịch chi tiết")
    
    def _load_trade_history(self) -> List[Dict]:
        """
        Tải lịch sử giao dịch từ file
        
        Returns:
            List[Dict]: Lịch sử giao dịch
        """
        try:
            if os.path.exists(self.trade_history_file):
                with open(self.trade_history_file, 'r') as f:
                    history = json.load(f)
                    logger.info(f"Đã tải {len(history)} giao dịch từ {self.trade_history_file}")
                    return history
            else:
                logger.info(f"File lịch sử giao dịch {self.trade_history_file} không tồn tại, tạo mới")
                return []
        except Exception as e:
            logger.error(f"Lỗi khi tải lịch sử giao dịch: {str(e)}")
            return []
    
    def _save_trade_history(self) -> bool:
        """
        Lưu lịch sử giao dịch vào file
        
        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            # Tạo thư mục nếu chưa tồn tại
            os.makedirs(os.path.dirname(self.trade_history_file), exist_ok=True)
            
            with open(self.trade_history_file, 'w') as f:
                json.dump(self.trade_history, f, indent=2)
                
            logger.info(f"Đã lưu {len(self.trade_history)} giao dịch vào {self.trade_history_file}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu lịch sử giao dịch: {str(e)}")
            return False
    
    def _update_statistics(self) -> None:
        """Cập nhật thống kê giao dịch"""
        try:
            today = datetime.now().date()
            
            # Reset thống kê
            self.daily_stats = {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_profit': 0,
                'total_loss': 0,
                'net_profit': 0,
                'win_rate': 0,
                'date': today.strftime('%Y-%m-%d')
            }
            
            # Tính thống kê cho ngày hiện tại
            for trade in self.trade_history:
                trade_date = datetime.fromisoformat(trade.get('exit_time', datetime.now().isoformat())).date()
                
                # Chỉ tính các giao dịch đã đóng
                if 'exit_price' not in trade or trade.get('status') != 'CLOSED':
                    continue
                
                # Thống kê theo ngày
                if trade_date == today:
                    self.daily_stats['total_trades'] += 1
                    
                    profit = trade.get('profit_amount', 0)
                    if profit > 0:
                        self.daily_stats['winning_trades'] += 1
                        self.daily_stats['total_profit'] += profit
                    else:
                        self.daily_stats['losing_trades'] += 1
                        self.daily_stats['total_loss'] += profit
                    
                    self.daily_stats['net_profit'] += profit
            
            # Tính tỷ lệ thắng
            if self.daily_stats['total_trades'] > 0:
                self.daily_stats['win_rate'] = self.daily_stats['winning_trades'] / self.daily_stats['total_trades'] * 100
            
            logger.info(f"Đã cập nhật thống kê giao dịch: {self.daily_stats['total_trades']} giao dịch hôm nay")
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật thống kê: {str(e)}")
    
    def notify_entry(self, entry_data: Dict) -> bool:
        """
        Gửi thông báo khi vào lệnh
        
        Args:
            entry_data (Dict): Thông tin vào lệnh
                {
                    'symbol': str,
                    'side': str,
                    'entry_price': float,
                    'quantity': float,
                    'leverage': int,
                    'take_profit': float,
                    'stop_loss': float,
                    'margin_amount': float,
                    'entry_time': str,
                    'entry_reason': str,
                    'indicator_values': Dict,
                    'risk_reward_ratio': float,
                    ...
                }
        
        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            # Tạo ID giao dịch
            trade_id = f"{entry_data.get('symbol')}-{int(datetime.now().timestamp())}"
            
            # Thêm vào lịch sử giao dịch
            trade_data = {
                'id': trade_id,
                'symbol': entry_data.get('symbol'),
                'side': entry_data.get('side'),
                'entry_price': entry_data.get('entry_price'),
                'quantity': entry_data.get('quantity'),
                'leverage': entry_data.get('leverage', 1),
                'take_profit': entry_data.get('take_profit'),
                'stop_loss': entry_data.get('stop_loss'),
                'margin_amount': entry_data.get('margin_amount'),
                'entry_time': entry_data.get('entry_time', datetime.now().isoformat()),
                'entry_reason': entry_data.get('entry_reason', 'Không có lý do'),
                'indicator_values': entry_data.get('indicator_values', {}),
                'risk_reward_ratio': entry_data.get('risk_reward_ratio', 0),
                'status': 'OPEN'
            }
            
            self.trade_history.append(trade_data)
            self._save_trade_history()
            
            # Tạo tin nhắn thông báo
            message = self._generate_entry_message(trade_data)
            
            # Gửi thông báo qua Telegram
            result = self.telegram.send_notification('trade', message)
            
            if result.get('ok'):
                logger.info(f"Đã gửi thông báo vào lệnh cho {trade_data['symbol']} thành công")
                return True
            else:
                logger.error(f"Lỗi khi gửi thông báo vào lệnh: {result.get('error', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo vào lệnh: {str(e)}")
            return False
    
    def _generate_entry_message(self, trade_data: Dict) -> str:
        """
        Tạo tin nhắn thông báo vào lệnh
        
        Args:
            trade_data (Dict): Thông tin giao dịch
        
        Returns:
            str: Nội dung tin nhắn
        """
        # Emoji dựa trên phía giao dịch
        emoji = '🟢' if trade_data['side'].upper() == 'LONG' or trade_data['side'].upper() == 'BUY' else '🔴'
        
        # Định dạng thời gian
        entry_time = datetime.fromisoformat(trade_data['entry_time'])
        formatted_time = entry_time.strftime('%H:%M:%S %d/%m/%Y')
        
        # Tạo tin nhắn
        message = f"{emoji} <b>VÀO LỆNH - {trade_data['side'].upper()} {trade_data['symbol']}</b> {emoji}\n\n"
        
        # Thông tin giá và khối lượng
        message += f"💵 <b>Giá vào:</b> {trade_data['entry_price']}\n"
        message += f"🔢 <b>Số lượng:</b> {trade_data['quantity']}\n"
        message += f"⚡ <b>Đòn bẩy:</b> {trade_data['leverage']}x\n"
        message += f"💰 <b>Margin:</b> {trade_data['margin_amount']:.2f} USDT\n\n"
        
        # Thông tin về tỷ lệ risk/reward và target
        if trade_data.get('take_profit'):
            tp_distance = abs(trade_data['take_profit'] - trade_data['entry_price']) / trade_data['entry_price'] * 100
            message += f"🎯 <b>Take Profit:</b> {trade_data['take_profit']} ({tp_distance:.2f}%)\n"
        
        if trade_data.get('stop_loss'):
            sl_distance = abs(trade_data['stop_loss'] - trade_data['entry_price']) / trade_data['entry_price'] * 100
            message += f"🛑 <b>Stop Loss:</b> {trade_data['stop_loss']} ({sl_distance:.2f}%)\n"
        
        if trade_data.get('risk_reward_ratio'):
            message += f"⚖️ <b>Tỷ lệ Risk/Reward:</b> 1:{trade_data['risk_reward_ratio']:.2f}\n\n"
        else:
            message += "\n"
        
        # Thông tin về lý do vào lệnh
        message += f"🔍 <b>LÝ DO VÀO LỆNH:</b>\n"
        message += f"{trade_data['entry_reason']}\n\n"
        
        # Thông tin về chỉ báo
        if trade_data.get('indicator_values'):
            message += f"📊 <b>CHỈ BÁO:</b>\n"
            
            for indicator, value in trade_data['indicator_values'].items():
                if isinstance(value, (int, float)):
                    message += f"  • {indicator}: {value:.2f}\n"
                else:
                    message += f"  • {indicator}: {value}\n"
            
            message += "\n"
        
        # Thông tin thời gian
        message += f"<i>Thời gian: {formatted_time}</i>"
        
        return message
    
    def notify_exit(self, exit_data: Dict) -> bool:
        """
        Gửi thông báo khi ra lệnh
        
        Args:
            exit_data (Dict): Thông tin ra lệnh
                {
                    'symbol': str,
                    'side': str,
                    'exit_price': float,
                    'quantity': float,
                    'exit_time': str,
                    'exit_reason': str,
                    'profit_amount': float,
                    'profit_percent': float,
                    'trade_id': str,
                    ...
                }
        
        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            # Tìm giao dịch trong lịch sử
            trade_id = exit_data.get('trade_id')
            trade_data = None
            
            if trade_id:
                for trade in self.trade_history:
                    if trade.get('id') == trade_id:
                        trade_data = trade
                        break
            else:
                # Nếu không có trade_id, tìm theo symbol và trạng thái
                symbol = exit_data.get('symbol')
                side = exit_data.get('side')
                
                for trade in self.trade_history:
                    if (trade.get('symbol') == symbol and 
                        trade.get('side') == side and 
                        trade.get('status') == 'OPEN'):
                        trade_data = trade
                        break
            
            if not trade_data:
                logger.warning(f"Không tìm thấy giao dịch phù hợp để đóng. Symbol: {exit_data.get('symbol')}")
                # Tạo một bản ghi mới
                trade_data = {
                    'id': f"{exit_data.get('symbol')}-{int(datetime.now().timestamp())}",
                    'symbol': exit_data.get('symbol'),
                    'side': exit_data.get('side'),
                    'entry_price': exit_data.get('entry_price', 0),
                    'quantity': exit_data.get('quantity', 0),
                    'entry_time': exit_data.get('entry_time', (datetime.now() - timedelta(hours=1)).isoformat()),
                    'status': 'CLOSED'
                }
                self.trade_history.append(trade_data)
            
            # Cập nhật thông tin đóng lệnh
            trade_data['exit_price'] = exit_data.get('exit_price')
            trade_data['exit_time'] = exit_data.get('exit_time', datetime.now().isoformat())
            trade_data['exit_reason'] = exit_data.get('exit_reason', 'Không có lý do')
            trade_data['profit_amount'] = exit_data.get('profit_amount', 0)
            trade_data['profit_percent'] = exit_data.get('profit_percent', 0)
            trade_data['status'] = 'CLOSED'
            
            # Lưu lịch sử
            self._save_trade_history()
            
            # Cập nhật thống kê
            self._update_statistics()
            
            # Tạo tin nhắn thông báo
            message = self._generate_exit_message(trade_data)
            
            # Gửi thông báo qua Telegram
            result = self.telegram.send_notification('trade', message)
            
            if result.get('ok'):
                logger.info(f"Đã gửi thông báo thoát lệnh cho {trade_data['symbol']} thành công")
                
                # Gửi thống kê ngày nếu có đủ giao dịch
                if self.daily_stats['total_trades'] >= 3:
                    self.send_daily_stats()
                
                return True
            else:
                logger.error(f"Lỗi khi gửi thông báo thoát lệnh: {result.get('error', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo thoát lệnh: {str(e)}")
            return False
    
    def _generate_exit_message(self, trade_data: Dict) -> str:
        """
        Tạo tin nhắn thông báo thoát lệnh
        
        Args:
            trade_data (Dict): Thông tin giao dịch
        
        Returns:
            str: Nội dung tin nhắn
        """
        # Tính lợi nhuận
        profit_amount = trade_data.get('profit_amount', 0)
        profit_percent = trade_data.get('profit_percent', 0)
        
        # Emoji dựa trên lợi nhuận
        emoji = '✅' if profit_amount > 0 else '❌'
        
        # Định dạng thời gian
        entry_time = datetime.fromisoformat(trade_data['entry_time'])
        formatted_entry_time = entry_time.strftime('%H:%M:%S %d/%m/%Y')
        
        exit_time = datetime.fromisoformat(trade_data['exit_time'])
        formatted_exit_time = exit_time.strftime('%H:%M:%S %d/%m/%Y')
        
        # Tính thời gian giữ lệnh
        holding_time = exit_time - entry_time
        days, seconds = holding_time.days, holding_time.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        holding_text = ""
        if days > 0:
            holding_text += f"{days} ngày "
        if hours > 0:
            holding_text += f"{hours} giờ "
        if minutes > 0:
            holding_text += f"{minutes} phút"
        if not holding_text:
            holding_text = "dưới 1 phút"
        
        # Tạo tin nhắn
        message = f"{emoji} <b>ĐÓNG LỆNH - {trade_data['side'].upper()} {trade_data['symbol']}</b> {emoji}\n\n"
        
        # Thông tin giá và khối lượng
        message += f"💵 <b>Giá vào:</b> {trade_data['entry_price']}\n"
        message += f"💵 <b>Giá ra:</b> {trade_data['exit_price']}\n"
        message += f"🔢 <b>Số lượng:</b> {trade_data['quantity']}\n"
        if 'leverage' in trade_data:
            message += f"⚡ <b>Đòn bẩy:</b> {trade_data['leverage']}x\n"
        
        # Thông tin lợi nhuận
        profit_emoji = '📈' if profit_amount > 0 else '📉'
        message += f"{profit_emoji} <b>Lợi nhuận:</b> {profit_amount:.2f} USDT ({profit_percent:.2f}%)\n"
        message += f"⏱️ <b>Thời gian giữ:</b> {holding_text}\n\n"
        
        # Thông tin về lý do thoát lệnh
        message += f"🔍 <b>LÝ DO ĐÓNG LỆNH:</b>\n"
        message += f"{trade_data['exit_reason']}\n\n"
        
        # Thêm thông tin tổng kết (nếu có)
        message += f"📅 <b>TỔNG KẾT:</b>\n"
        message += f"  • Thời gian vào: {formatted_entry_time}\n"
        message += f"  • Thời gian ra: {formatted_exit_time}\n"
        message += f"  • Kết quả: {'Lãi' if profit_amount > 0 else 'Lỗ'} {abs(profit_amount):.2f} USDT\n\n"
        
        # Thông tin thời gian
        message += f"<i>Thời gian: {formatted_exit_time}</i>"
        
        return message
    
    def send_daily_stats(self) -> bool:
        """
        Gửi thống kê giao dịch hàng ngày
        
        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            # Cập nhật thống kê
            self._update_statistics()
            
            # Tạo tin nhắn thông báo
            message = self._generate_daily_stats_message()
            
            # Gửi thông báo qua Telegram
            result = self.telegram.send_notification('info', message)
            
            if result.get('ok'):
                logger.info("Đã gửi thông kê giao dịch hàng ngày thành công")
                return True
            else:
                logger.error(f"Lỗi khi gửi thông kê giao dịch hàng ngày: {result.get('error', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông kê giao dịch hàng ngày: {str(e)}")
            return False
    
    def _generate_daily_stats_message(self) -> str:
        """
        Tạo tin nhắn thống kê giao dịch hàng ngày
        
        Returns:
            str: Nội dung tin nhắn
        """
        # Tạo tin nhắn
        message = f"📊 <b>THỐNG KÊ GIAO DỊCH NGÀY {self.daily_stats['date']}</b> 📊\n\n"
        
        # Thông tin tổng quan
        message += f"🔢 <b>Tổng số giao dịch:</b> {self.daily_stats['total_trades']}\n"
        message += f"✅ <b>Số lệnh thắng:</b> {self.daily_stats['winning_trades']}\n"
        message += f"❌ <b>Số lệnh thua:</b> {self.daily_stats['losing_trades']}\n"
        message += f"📈 <b>Tỷ lệ thắng:</b> {self.daily_stats['win_rate']:.2f}%\n\n"
        
        # Thông tin lợi nhuận
        message += f"💰 <b>Tổng lợi nhuận:</b> {self.daily_stats['total_profit']:.2f} USDT\n"
        message += f"💸 <b>Tổng lỗ:</b> {abs(self.daily_stats['total_loss']):.2f} USDT\n"
        
        net_profit = self.daily_stats['net_profit']
        profit_emoji = '📈' if net_profit > 0 else '📉'
        message += f"{profit_emoji} <b>Lợi nhuận ròng:</b> {net_profit:.2f} USDT\n\n"
        
        # Thông tin về các giao dịch gần đây
        message += f"🕒 <b>CÁC GIAO DỊCH GẦN ĐÂY:</b>\n"
        
        # Lấy tối đa 5 giao dịch gần nhất đã đóng
        recent_trades = []
        today = datetime.now().date()
        
        for trade in sorted(self.trade_history, key=lambda x: x.get('exit_time', ''), reverse=True):
            if 'exit_time' not in trade or trade.get('status') != 'CLOSED':
                continue
            
            trade_date = datetime.fromisoformat(trade['exit_time']).date()
            if trade_date == today:
                recent_trades.append(trade)
            
            if len(recent_trades) >= 5:
                break
        
        # Thêm thông tin các giao dịch
        if recent_trades:
            for trade in recent_trades:
                profit = trade.get('profit_amount', 0)
                emoji = '✅' if profit > 0 else '❌'
                
                message += f"  • {emoji} {trade['side'].upper()} {trade['symbol']}: "
                message += f"{profit:.2f} USDT ({trade.get('profit_percent', 0):.2f}%)\n"
        else:
            message += "  • Không có giao dịch nào hôm nay\n"
        
        message += "\n"
        
        # Thông tin thời gian
        message += f"<i>Cập nhật: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
        
        return message
    
    def notify_account_summary(self, account_data: Dict) -> bool:
        """
        Gửi thông báo tóm tắt tài khoản
        
        Args:
            account_data (Dict): Thông tin tài khoản
                {
                    'total_balance': float,
                    'available_balance': float,
                    'margin_balance': float,
                    'unrealized_pnl': float,
                    'realized_pnl': float,
                    'positions': List[Dict],
                    ...
                }
        
        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            # Tạo tin nhắn thông báo
            message = self._generate_account_summary_message(account_data)
            
            # Gửi thông báo qua Telegram
            result = self.telegram.send_notification('info', message)
            
            if result.get('ok'):
                logger.info("Đã gửi thông báo tóm tắt tài khoản thành công")
                return True
            else:
                logger.error(f"Lỗi khi gửi thông báo tóm tắt tài khoản: {result.get('error', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo tóm tắt tài khoản: {str(e)}")
            return False
    
    def _generate_account_summary_message(self, account_data: Dict) -> str:
        """
        Tạo tin nhắn tóm tắt tài khoản
        
        Args:
            account_data (Dict): Thông tin tài khoản
        
        Returns:
            str: Nội dung tin nhắn
        """
        # Lấy thông tin tài khoản
        total_balance = account_data.get('total_balance', 0)
        available_balance = account_data.get('available_balance', 0)
        margin_balance = account_data.get('margin_balance', 0)
        unrealized_pnl = account_data.get('unrealized_pnl', 0)
        realized_pnl = account_data.get('realized_pnl', 0)
        positions = account_data.get('positions', [])
        
        # Tạo tin nhắn
        message = f"💼 <b>TÓM TẮT TÀI KHOẢN</b> 💼\n\n"
        
        # Thông tin số dư
        message += f"💵 <b>Tổng số dư:</b> {total_balance:.2f} USDT\n"
        message += f"💰 <b>Số dư khả dụng:</b> {available_balance:.2f} USDT\n"
        message += f"💹 <b>Số dư margin:</b> {margin_balance:.2f} USDT\n"
        
        # Thông tin lợi nhuận
        unrealized_emoji = '📈' if unrealized_pnl > 0 else '📉'
        realized_emoji = '📈' if realized_pnl > 0 else '📉'
        message += f"{unrealized_emoji} <b>Lợi nhuận chưa thực hiện:</b> {unrealized_pnl:.2f} USDT\n"
        message += f"{realized_emoji} <b>Lợi nhuận đã thực hiện:</b> {realized_pnl:.2f} USDT\n\n"
        
        # Thông tin vị thế mở
        if positions:
            message += f"📊 <b>VỊ THẾ ĐANG MỞ ({len(positions)}):</b>\n"
            
            for position in positions:
                symbol = position.get('symbol', 'UNKNOWN')
                entry_price = position.get('entry_price', 0)
                current_price = position.get('mark_price', 0)
                quantity = position.get('positionAmt', 0)
                
                # Xác định phía
                side = 'LONG' if float(quantity) > 0 else 'SHORT'
                quantity_abs = abs(float(quantity))
                
                # Tính lợi nhuận
                if side == 'LONG':
                    profit_percent = (current_price - entry_price) / entry_price * 100
                else:
                    profit_percent = (entry_price - current_price) / entry_price * 100
                
                # Emoji dựa trên lợi nhuận
                emoji = '🟢' if profit_percent > 0 else '🔴'
                
                # Thêm thông tin vị thế
                message += f"  • {emoji} {side} {symbol}: {profit_percent:.2f}%\n"
        else:
            message += f"📊 <b>VỊ THẾ ĐANG MỞ:</b> Không có\n"
        
        message += "\n"
        
        # Thông tin thời gian
        message += f"<i>Cập nhật: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
        
        return message

# Hàm kiểm thử
def main():
    """Hàm kiểm thử DetailedTradeNotifications"""
    try:
        # Khởi tạo hệ thống thông báo
        notifier = DetailedTradeNotifications()
        
        # Mô phỏng thông báo vào lệnh
        entry_data = {
            'symbol': 'BTCUSDT',
            'side': 'LONG',
            'entry_price': 85000,
            'quantity': 0.01,
            'leverage': 5,
            'take_profit': 87000,
            'stop_loss': 84000,
            'margin_amount': 170,
            'entry_reason': 'RSI vượt ngưỡng 30 từ dưới lên, MACD cho tín hiệu cắt lên, đường giá vượt MA20',
            'indicator_values': {
                'RSI': 32.5,
                'MACD': 'Tín hiệu dương',
                'MA20': 84500
            },
            'risk_reward_ratio': 2.0
        }
        
        print("Gửi thông báo vào lệnh...")
        notifier.notify_entry(entry_data)
        
        # Giả lập delay
        print("Đợi 3 giây...")
        time.sleep(3)
        
        # Mô phỏng thông báo ra lệnh
        exit_data = {
            'symbol': 'BTCUSDT',
            'side': 'LONG',
            'exit_price': 86500,
            'quantity': 0.01,
            'exit_reason': 'Đạt mục tiêu lợi nhuận 80%, RSI vượt ngưỡng 70, thị trường có dấu hiệu đảo chiều',
            'profit_amount': 150,
            'profit_percent': 1.76
        }
        
        print("Gửi thông báo ra lệnh...")
        notifier.notify_exit(exit_data)
        
        # Gửi thống kê ngày
        print("Gửi thống kê ngày...")
        notifier.send_daily_stats()
        
        # Gửi tóm tắt tài khoản
        account_data = {
            'total_balance': 13500,
            'available_balance': 13000,
            'margin_balance': 13500,
            'unrealized_pnl': 250,
            'realized_pnl': 500,
            'positions': [
                {
                    'symbol': 'ETHUSDT',
                    'entry_price': 2150,
                    'mark_price': 2180,
                    'positionAmt': 0.1
                }
            ]
        }
        
        print("Gửi tóm tắt tài khoản...")
        notifier.notify_account_summary(account_data)
        
        return 0
    except Exception as e:
        logger.error(f"Lỗi trong hàm kiểm thử: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())