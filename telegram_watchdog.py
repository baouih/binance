#!/usr/bin/env python3
"""
Script telegram watchdog - Gửi thông báo trạng thái và cảnh báo qua Telegram

Script này gửi thông báo về trạng thái của bot và cảnh báo khi có sự cố
thông qua kênh Telegram, giúp quản trị viên theo dõi hoạt động của bot từ xa.
"""

import os
import sys
import json
import time
import requests
import logging
from datetime import datetime
import traceback

# Cấu hình logging
logging.basicConfig(
    filename='telegram_watchdog.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Thông tin Telegram Bot (cần thay thế bằng thông tin thực tế)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'DEFAULT_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', 'DEFAULT_CHAT_ID')

# Đường dẫn tới các file cấu hình
BOT_STATUS_FILE = 'bot_status.json'
ACTIVE_POSITIONS_FILE = 'active_positions.json'

def load_json_file(file_path):
    """
    Tải nội dung từ file JSON
    
    Args:
        file_path (str): Đường dẫn tới file JSON
        
    Returns:
        dict: Dữ liệu từ file JSON hoặc {} nếu có lỗi
    """
    try:
        if not os.path.exists(file_path):
            logging.warning(f"File {file_path} không tồn tại")
            return {}
            
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Lỗi khi tải file {file_path}: {str(e)}")
        return {}

def send_telegram_message(message):
    """
    Gửi tin nhắn qua Telegram Bot
    
    Args:
        message (str): Nội dung tin nhắn
        
    Returns:
        bool: True nếu gửi thành công, False nếu thất bại
    """
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=payload)
        
        if response.status_code == 200:
            logging.info(f"Đã gửi tin nhắn Telegram: {message[:50]}...")
            return True
        else:
            logging.error(f"Không thể gửi tin nhắn Telegram. Mã lỗi: {response.status_code}")
            logging.error(f"Phản hồi: {response.text}")
            return False
            
    except Exception as e:
        logging.error(f"Lỗi khi gửi tin nhắn Telegram: {str(e)}")
        logging.error(traceback.format_exc())
        return False

def get_bot_status_summary():
    """
    Tạo tóm tắt trạng thái bot
    
    Returns:
        str: Tóm tắt trạng thái bot
    """
    bot_status = load_json_file(BOT_STATUS_FILE)
    
    if not bot_status:
        return "❌ Không thể đọc thông tin trạng thái bot!"
    
    # Tính thời gian bot đã chạy
    start_time = datetime.strptime(bot_status.get('start_time', '2025-01-01 00:00:00'), '%Y-%m-%d %H:%M:%S')
    last_update = datetime.strptime(bot_status.get('last_update', '2025-01-01 00:00:00'), '%Y-%m-%d %H:%M:%S')
    now = datetime.now()
    uptime = now - start_time
    last_update_delta = now - last_update
    
    # Định dạng uptime thành ngày, giờ, phút
    days = uptime.days
    hours = uptime.seconds // 3600
    minutes = (uptime.seconds % 3600) // 60
    
    # Tạo tóm tắt
    summary = []
    summary.append(f"<b>🤖 Trạng thái Crypto Trading Bot</b>")
    summary.append(f"🔹 Bot đang {'Hoạt động' if bot_status.get('running', False) else 'Dừng'}")
    summary.append(f"🔹 Thời gian hoạt động: {days} ngày, {hours} giờ, {minutes} phút")
    summary.append(f"🔹 Cập nhật cuối: {bot_status.get('last_update', 'N/A')} (cách đây {last_update_delta.seconds // 60} phút)")
    summary.append(f"🔹 Chế độ: {bot_status.get('mode', 'N/A').upper()}")
    summary.append(f"🔹 Số dư: {bot_status.get('balance', 0):.2f} USDT")
    summary.append(f"🔹 Số cặp giám sát: {len(bot_status.get('monitored_symbols', []))}")
    summary.append(f"🔹 Số cặp hoạt động: {len(bot_status.get('active_symbols', []))}")
    
    active_strategies = bot_status.get('active_strategies', [])
    summary.append(f"🔹 Chiến lược ({len(active_strategies)}): {', '.join(active_strategies)}")
    
    return "\n".join(summary)

def get_active_positions_summary():
    """
    Tạo tóm tắt các vị thế đang mở
    
    Returns:
        str: Tóm tắt các vị thế đang mở
    """
    positions = load_json_file(ACTIVE_POSITIONS_FILE)
    
    if not positions:
        return "❌ Không thể đọc thông tin vị thế đang mở!"
    
    # Tạo tóm tắt
    summary = []
    summary.append(f"<b>📊 Vị thế Đang Mở ({len(positions)})</b>")
    
    for pos_id, pos_data in positions.items():
        symbol = pos_data.get('symbol', 'UNKNOWN')
        side = pos_data.get('side', 'UNKNOWN')
        entry_price = pos_data.get('entry_price', 0)
        current_price = pos_data.get('current_price', 0)
        quantity = pos_data.get('quantity', 0)
        leverage = pos_data.get('leverage', 1)
        
        # Tính P/L
        if side == 'BUY':
            pnl_pct = (current_price - entry_price) / entry_price * 100 * leverage
        else:
            pnl_pct = (entry_price - current_price) / entry_price * 100 * leverage
            
        pnl_emoji = "🟢" if pnl_pct > 0 else "🔴"
        
        summary.append(f"{pnl_emoji} {symbol} {side} - Vào: {entry_price:.2f}, Hiện tại: {current_price:.2f}, SL lượng: {quantity:.4f}, Đòn bẩy: {leverage}x, P/L: {pnl_pct:.2f}%")
    
    return "\n".join(summary)

def check_bot_health():
    """
    Kiểm tra sức khỏe của bot và phát hiện vấn đề
    
    Returns:
        tuple: (is_healthy, warning_message)
    """
    bot_status = load_json_file(BOT_STATUS_FILE)
    
    if not bot_status:
        return False, "Không thể đọc file trạng thái bot!"
    
    # Kiểm tra thời gian cập nhật cuối
    if 'last_update' in bot_status:
        last_update = datetime.strptime(bot_status['last_update'], '%Y-%m-%d %H:%M:%S')
        now = datetime.now()
        delta = now - last_update
        
        # Nếu hơn 10 phút không cập nhật, bot có thể bị treo
        if delta.seconds > 600:
            return False, f"Bot không cập nhật trong {delta.seconds // 60} phút qua!"
    
    # Kiểm tra trạng thái running
    if not bot_status.get('running', False):
        return False, "Bot đang trong trạng thái dừng!"
    
    return True, "Bot đang hoạt động bình thường"

def main():
    """Hàm chính của script"""
    logging.info("Telegram watchdog đã khởi động")
    
    # Nếu có tham số dòng lệnh, sử dụng nó như là tin nhắn để gửi
    if len(sys.argv) > 1:
        message = sys.argv[1]
        send_telegram_message(message)
        return
    
    # Gửi thông báo khởi động
    send_telegram_message("🚀 Telegram Watchdog đã được khởi động và đang giám sát bot!")
    
    # Vòng lặp giám sát
    check_interval = 15 * 60  # 15 phút
    status_interval = 6 * 60 * 60  # 6 giờ
    
    last_status_time = time.time() - status_interval  # Gửi báo cáo trạng thái ngay lần đầu
    
    try:
        while True:
            # Kiểm tra sức khỏe bot
            is_healthy, health_message = check_bot_health()
            
            # Gửi cảnh báo nếu bot không khỏe mạnh
            if not is_healthy:
                warning_message = f"⚠️ CẢNH BÁO: {health_message}"
                send_telegram_message(warning_message)
            
            # Gửi báo cáo trạng thái định kỳ
            current_time = time.time()
            if current_time - last_status_time >= status_interval:
                status_summary = get_bot_status_summary()
                positions_summary = get_active_positions_summary()
                
                full_summary = f"{status_summary}\n\n{positions_summary}"
                send_telegram_message(full_summary)
                
                last_status_time = current_time
            
            # Ngủ trước khi kiểm tra tiếp
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        logging.info("Telegram watchdog đã dừng bởi người dùng")
        send_telegram_message("🛑 Telegram Watchdog đã dừng bởi người dùng")
    except Exception as e:
        error_message = f"Lỗi trong telegram_watchdog: {str(e)}"
        logging.error(error_message)
        logging.error(traceback.format_exc())
        send_telegram_message(f"❌ {error_message}")

if __name__ == "__main__":
    main()