"""
Module thông báo Telegram cho BinanceTrader Bot

Module này cung cấp chức năng gửi thông báo tới Telegram về các hoạt động quan trọng
của bot: ra vào lệnh, lãi lỗ, cảnh báo thị trường, v.v.
"""
import os
import logging
import requests
import json
from datetime import datetime

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('telegram_notifier')

class TelegramNotifier:
    """
    Lớp quản lý gửi thông báo tới Telegram
    """
    def __init__(self, token: str = None, chat_id: str = None):
        """
        Khởi tạo TelegramNotifier
        
        Args:
            token (str): Token của Telegram bot API
            chat_id (str): ID của chat/người dùng nhận thông báo
        """
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "8069189803:AAF3PJc3BNQgZmpQ2Oj7o0-ySJGmi2AQ9OM")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "1834332146")
        self.api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        
        # Màu cho các loại thông báo
        self.colors = {
            'info': '🔵',
            'success': '🟢',
            'warning': '🟠',
            'error': '🔴',
            'trade_entry': '🟢',
            'trade_exit': '🟣',
            'trade_profit': '💰',
            'trade_loss': '📉',
            'market_alert': '⚠️',
            'system': '⚙️'
        }
    
    def send_message(self, message: str, category: str = 'info') -> bool:
        """
        Gửi thông báo tới Telegram
        
        Args:
            message (str): Nội dung thông báo
            category (str): Loại thông báo (info/success/warning/error/trade_entry/trade_exit...)
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
        """
        try:
            emoji = self.colors.get(category, '🔷')
            formatted_message = f"{emoji} {message}"
            
            # Thêm timestamp
            formatted_message += f"\n⏱️ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            payload = {
                'chat_id': self.chat_id,
                'text': formatted_message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(self.api_url, json=payload)
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get('ok'):
                logger.info(f"Đã gửi thông báo Telegram thành công: {category}")
                return True
            else:
                logger.error(f"Lỗi khi gửi thông báo Telegram: {response_data}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo Telegram: {str(e)}")
            return False
    
    def send_trade_entry(self, symbol: str, side: str, entry_price: float, 
                       quantity: float, stop_loss: float = None, 
                       take_profit: float = None, reason: str = None) -> bool:
        """
        Gửi thông báo vào lệnh
        
        Args:
            symbol (str): Mã cặp giao dịch (BTCUSDT, ETHUSDT, ...)
            side (str): Hướng lệnh (BUY/SELL)
            entry_price (float): Giá vào lệnh
            quantity (float): Số lượng
            stop_loss (float, optional): Giá stop loss
            take_profit (float, optional): Giá take profit
            reason (str, optional): Lý do vào lệnh
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
        """
        # Biểu tượng mũi tên
        direction_arrow = '🔼' if side == 'BUY' else '🔽'
        side_text = 'MUA' if side == 'BUY' else 'BÁN'
        
        message = f"<b>{direction_arrow} VÀO LỆNH {side_text}</b>\n\n"
        message += f"<b>Cặp:</b> {symbol}\n"
        message += f"<b>Giá vào:</b> {entry_price:,.2f} USDT\n"
        message += f"<b>Số lượng:</b> {quantity}\n"
        
        if stop_loss:
            message += f"<b>Stop Loss:</b> {stop_loss:,.2f} USDT\n"
        
        if take_profit:
            message += f"<b>Take Profit:</b> {take_profit:,.2f} USDT\n"
        
        if reason:
            message += f"\n<b>Lý do:</b> {reason}"
        
        return self.send_message(message, 'trade_entry')
    
    def send_trade_exit(self, symbol: str, side: str, exit_price: float, 
                      entry_price: float, quantity: float, profit_loss: float,
                      profit_loss_percent: float, exit_reason: str = None) -> bool:
        """
        Gửi thông báo thoát lệnh
        
        Args:
            symbol (str): Mã cặp giao dịch (BTCUSDT, ETHUSDT, ...)
            side (str): Hướng lệnh ban đầu (BUY/SELL)
            exit_price (float): Giá thoát lệnh
            entry_price (float): Giá vào lệnh
            quantity (float): Số lượng
            profit_loss (float): Lãi/lỗ (USDT)
            profit_loss_percent (float): Lãi/lỗ (%)
            exit_reason (str, optional): Lý do thoát lệnh
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
        """
        # Xác định lãi/lỗ
        is_profit = profit_loss > 0
        pl_emoji = '💰' if is_profit else '📉'
        
        # Xác định loại lệnh
        side_text = 'MUA' if side == 'BUY' else 'BÁN'
        exit_text = 'BÁN' if side == 'BUY' else 'MUA'
        
        message = f"<b>{pl_emoji} THOÁT LỆNH {side_text}</b>\n\n"
        message += f"<b>Cặp:</b> {symbol}\n"
        message += f"<b>Giá vào:</b> {entry_price:,.2f} USDT\n"
        message += f"<b>Giá thoát:</b> {exit_price:,.2f} USDT\n"
        message += f"<b>Số lượng:</b> {quantity}\n"
        
        # Highlight profit/loss
        profit_loss_text = f"+{profit_loss:,.2f}" if is_profit else f"{profit_loss:,.2f}"
        profit_loss_percent_text = f"+{profit_loss_percent:.2f}%" if is_profit else f"{profit_loss_percent:.2f}%"
        
        if is_profit:
            message += f"<b>Lợi nhuận:</b> {profit_loss_text} USDT ({profit_loss_percent_text})\n"
        else:
            message += f"<b>Lỗ:</b> {profit_loss_text} USDT ({profit_loss_percent_text})\n"
        
        if exit_reason:
            message += f"\n<b>Lý do thoát:</b> {exit_reason}"
        
        category = 'trade_profit' if is_profit else 'trade_loss'
        return self.send_message(message, category)
    
    def send_market_alert(self, symbol: str, alert_type: str, 
                        price: float = None, message: str = None) -> bool:
        """
        Gửi cảnh báo thị trường
        
        Args:
            symbol (str): Mã cặp giao dịch (BTCUSDT, ETHUSDT, ...)
            alert_type (str): Loại cảnh báo
            price (float, optional): Giá hiện tại
            message (str, optional): Nội dung cảnh báo
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
        """
        alert_message = f"<b>⚠️ CẢNH BÁO THỊ TRƯỜNG</b>\n\n"
        alert_message += f"<b>Cặp:</b> {symbol}\n"
        
        if price:
            alert_message += f"<b>Giá hiện tại:</b> {price:,.2f} USDT\n"
        
        alert_message += f"<b>Loại cảnh báo:</b> {alert_type}\n"
        
        if message:
            alert_message += f"\n<b>Chi tiết:</b> {message}"
        
        return self.send_message(alert_message, 'market_alert')
    
    def send_bot_status(self, status: str, mode: str, uptime: str = None, 
                      stats: dict = None) -> bool:
        """
        Gửi thông báo trạng thái bot
        
        Args:
            status (str): Trạng thái bot (running/stopped)
            mode (str): Chế độ API (demo/testnet/live)
            uptime (str, optional): Thời gian hoạt động
            stats (dict, optional): Thống kê hoạt động
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
        """
        status_text = 'đang chạy' if status == 'running' else 'đã dừng'
        status_emoji = '🟢' if status == 'running' else '🔴'
        
        message = f"<b>{status_emoji} BOT {status_text.upper()}</b>\n\n"
        message += f"<b>Chế độ:</b> {mode.capitalize()}\n"
        
        if uptime:
            message += f"<b>Thời gian hoạt động:</b> {uptime}\n"
        
        if stats:
            message += "\n<b>Thống kê:</b>\n"
            for key, value in stats.items():
                message += f"- {key}: {value}\n"
        
        return self.send_message(message, 'system')
    
    def send_daily_summary(self, date: str, total_trades: int, winning_trades: int,
                         losing_trades: int, profit_loss: float, win_rate: float,
                         top_pairs: list = None) -> bool:
        """
        Gửi báo cáo tổng kết hàng ngày
        
        Args:
            date (str): Ngày báo cáo
            total_trades (int): Tổng số giao dịch
            winning_trades (int): Số giao dịch thắng
            losing_trades (int): Số giao dịch thua
            profit_loss (float): Tổng lãi/lỗ
            win_rate (float): Tỷ lệ thắng (%)
            top_pairs (list, optional): Danh sách cặp giao dịch tốt nhất
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
        """
        is_profit = profit_loss > 0
        pl_emoji = '📈' if is_profit else '📉'
        
        message = f"<b>📊 BÁO CÁO NGÀY {date}</b>\n\n"
        message += f"<b>Tổng giao dịch:</b> {total_trades}\n"
        message += f"<b>Thắng:</b> {winning_trades}\n"
        message += f"<b>Thua:</b> {losing_trades}\n"
        message += f"<b>Tỷ lệ thắng:</b> {win_rate:.2f}%\n"
        
        profit_loss_text = f"+{profit_loss:,.2f}" if is_profit else f"{profit_loss:,.2f}"
        message += f"<b>{pl_emoji} P&L:</b> {profit_loss_text} USDT\n"
        
        if top_pairs and len(top_pairs) > 0:
            message += "\n<b>Top cặp giao dịch:</b>\n"
            for pair in top_pairs:
                pair_profit = pair.get('profit', 0)
                pair_emoji = '📈' if pair_profit > 0 else '📉'
                message += f"- {pair['symbol']}: {pair_profit:,.2f} USDT {pair_emoji}\n"
        
        return self.send_message(message, 'info')

def test_telegram_notification():
    """Hàm test thông báo Telegram"""
    notifier = TelegramNotifier()
    
    # Test thông báo vào lệnh
    notifier.send_trade_entry(
        symbol="BTCUSDT",
        side="BUY",
        entry_price=47250.50,
        quantity=0.01,
        stop_loss=46500.00,
        take_profit=48500.00,
        reason="RSI vượt ngưỡng 30 từ dưới lên, giá đang nằm trên MA50"
    )
    
    # Test thông báo thoát lệnh lãi
    notifier.send_trade_exit(
        symbol="BTCUSDT",
        side="BUY",
        exit_price=48100.75,
        entry_price=47250.50,
        quantity=0.01,
        profit_loss=85.0,
        profit_loss_percent=1.8,
        exit_reason="Đạt mức Take Profit"
    )
    
    # Test thông báo thoát lệnh lỗ
    notifier.send_trade_exit(
        symbol="ETHUSDT",
        side="SELL",
        exit_price=3250.25,
        entry_price=3300.25,
        quantity=0.05,
        profit_loss=-25.0,
        profit_loss_percent=-0.75,
        exit_reason="Kích hoạt Stop Loss"
    )
    
    # Test cảnh báo thị trường
    notifier.send_market_alert(
        symbol="BTCUSDT",
        alert_type="Biến động lớn",
        price=47500.00,
        message="Giá BTC đã di chuyển 5% trong 10 phút, biến động cao"
    )
    
    # Test báo cáo trạng thái bot
    notifier.send_bot_status(
        status="running",
        mode="testnet",
        uptime="14h 35m",
        stats={
            "Tổng phân tích": 342,
            "Quyết định": 28,
            "Giao dịch": 12
        }
    )
    
    # Test báo cáo tổng kết ngày
    notifier.send_daily_summary(
        date="03/03/2025",
        total_trades=15,
        winning_trades=9,
        losing_trades=6,
        profit_loss=125.5,
        win_rate=60.0,
        top_pairs=[
            {"symbol": "BTCUSDT", "profit": 85.0},
            {"symbol": "ETHUSDT", "profit": 45.5},
            {"symbol": "SOLUSDT", "profit": -5.0}
        ]
    )
    
    return True

if __name__ == "__main__":
    test_telegram_notification()