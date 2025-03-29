import os
import sys
import time
import json
import logging
import threading
import schedule
from datetime import datetime

logger = logging.getLogger('background_tasks')

# Biến để theo dõi trạng thái scheduler
scheduler_running = False
scheduler_thread = None

# Hàm để kiểm tra trạng thái bot
def check_bot_status():
    """Kiểm tra và cập nhật trạng thái bot"""
    try:
        from bot_status_checker import check_status
        status = check_status()
        logger.info(f"Đã cập nhật trạng thái bot: {status}")
        return status
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra trạng thái bot: {str(e)}")
        return None

# Hàm để cập nhật dữ liệu thị trường
def update_market_data():
    """Cập nhật dữ liệu thị trường từ API"""
    try:
        from market_data_updater import update_data
        data = update_data()
        logger.info("Đã cập nhật dữ liệu thị trường")
        return data
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật dữ liệu thị trường: {str(e)}")
        return None

# Hàm để kiểm tra và cập nhật vị thế
def check_positions():
    """Kiểm tra và cập nhật thông tin vị thế"""
    try:
        from check_active_positions_v2 import check_and_update_positions
        positions = check_and_update_positions()
        logger.info(f"Đã cập nhật thông tin vị thế: {len(positions)} vị thế")
        return positions
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật thông tin vị thế: {str(e)}")
        return None

# Hàm để gửi thông báo định kỳ
def send_periodic_notification():
    """Gửi thông báo định kỳ về trạng thái hệ thống"""
    try:
        from telegram_notifier import TelegramNotifier
        
        # Thử đọc từ file cấu hình nếu có
        telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        
        # Nếu không có trong biến môi trường, thử đọc từ file config
        if not telegram_token or not telegram_chat_id:
            try:
                if os.path.exists("telegram_config.json"):
                    with open("telegram_config.json", "r") as config_file:
                        config = json.load(config_file)
                        if not telegram_token and "bot_token" in config:
                            telegram_token = config["bot_token"]
                        if not telegram_chat_id and "chat_id" in config:
                            telegram_chat_id = config["chat_id"]
                        logger.info("Đã tải thông tin Telegram từ file config")
            except Exception as e:
                logger.error(f"Lỗi khi đọc file config Telegram: {e}")
        
        # Nếu có đủ thông tin, khởi tạo notifier và gửi thông báo
        if telegram_token and telegram_chat_id:
            telegram = TelegramNotifier(token=telegram_token, chat_id=telegram_chat_id)
            
            # Lấy thông tin tài khoản
            from binance_api import BinanceAPI
            client = BinanceAPI(
                api_key=os.environ.get("BINANCE_API_KEY"),
                api_secret=os.environ.get("BINANCE_API_SECRET"),
                testnet=True
            )
            
            account = client.get_futures_account()
            positions = client.get_positions()
            
            # Tạo nội dung thông báo
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"""
<b>🤖 BÁO CÁO ĐỊNH KỲ HỆ THỐNG</b>

📊 <b>Trạng thái:</b> Hoạt động
⏱ <b>Thời gian:</b> {current_time}

<b>Thông tin tài khoản:</b>
💰 Số dư: {account.get('totalWalletBalance', 0):.2f} USDT
📈 P&L chưa thực hiện: {account.get('totalUnrealizedProfit', 0):.2f} USDT
⚡ Đòn bẩy hiện tại: {account.get('leverageMultiplier', 1)}x

<b>Vị thế đang mở ({len(positions)}):</b>
"""
            
            # Thêm thông tin từng vị thế
            for pos in positions[:5]:  # Giới hạn 5 vị thế để thông báo không quá dài
                symbol = pos.get('symbol', 'UNKNOWN')
                side = "LONG" if pos.get('positionSide', 'LONG') == 'LONG' else "SHORT"
                entry_price = float(pos.get('entryPrice', 0))
                current_price = float(pos.get('markPrice', 0))
                pnl = float(pos.get('unrealizedProfit', 0))
                pnl_percent = (current_price / entry_price - 1) * 100 if side == "LONG" else (1 - current_price / entry_price) * 100
                
                emoji = "🟢" if pnl > 0 else "🔴"
                message += f"\n{emoji} {symbol} ({side}): {pnl:.2f} USDT ({pnl_percent:.2f}%)"
            
            message += "\n\n<i>Đây là thông báo tự động từ hệ thống giao dịch.</i>"
            
            # Gửi thông báo
            telegram.send_message(message)
            logger.info("Đã gửi thông báo định kỳ qua Telegram")
        else:
            logger.warning("Không thể gửi thông báo Telegram: Thiếu thông tin cấu hình")
    except Exception as e:
        logger.error(f"Lỗi khi gửi thông báo định kỳ: {str(e)}")

# Hàm chạy scheduler trong thread riêng
def scheduler_thread_func():
    """Chạy scheduler trong một thread riêng"""
    global scheduler_running
    scheduler_running = True
    logger.info("Đã khởi động thread scheduler")
    
    while scheduler_running:
        schedule.run_pending()
        time.sleep(1)
    
    logger.info("Thread scheduler đã dừng")

# Hàm khởi động scheduler
def start_scheduler():
    """Khởi động scheduler và đăng ký các task định kỳ"""
    global scheduler_thread, scheduler_running
    
    if scheduler_running:
        logger.info("Scheduler đã đang chạy, không khởi động lại")
        return
    
    try:
        # Xóa tất cả các task đã đăng ký trước đó
        schedule.clear()
        
        # Đăng ký các task định kỳ
        schedule.every(1).minutes.do(check_bot_status)
        schedule.every(5).minutes.do(update_market_data)
        schedule.every(2).minutes.do(check_positions)
        schedule.every(30).minutes.do(send_periodic_notification)
        
        # Gửi thông báo khởi động hệ thống
        try:
            from telegram_notifier import TelegramNotifier
            # Thử đọc từ file cấu hình
            telegram_token = ""
            telegram_chat_id = ""
            if os.path.exists("telegram_config.json"):
                with open("telegram_config.json", "r") as config_file:
                    config = json.load(config_file)
                    telegram_token = config.get("bot_token", "")
                    telegram_chat_id = config.get("chat_id", "")
            
            if telegram_token and telegram_chat_id:
                telegram = TelegramNotifier(token=telegram_token, chat_id=telegram_chat_id)
                
                # Lấy thông tin tài khoản để gửi thông báo khởi động
                try:
                    from binance_api import BinanceAPI
                    client = BinanceAPI(
                        api_key=os.environ.get("BINANCE_API_KEY", ""),
                        api_secret=os.environ.get("BINANCE_API_SECRET", ""),
                        testnet=True
                    )
                    
                    account = client.get_futures_account()
                    balance = account.get('totalWalletBalance', 0)
                    pnl = account.get('totalUnrealizedProfit', 0)
                    
                    message = f"""
<b>🤖 HỆ THỐNG GIAO DỊCH ĐÃ KHỞI ĐỘNG</b>

📊 <b>Trạng thái:</b> Hoạt động
⏱ <b>Thời gian:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

<b>Thông tin tài khoản:</b>
💰 Số dư: {balance:.2f} USDT
📈 P&L chưa thực hiện: {pnl:.2f} USDT

<i>Hệ thống sẽ gửi báo cáo định kỳ về trạng thái giao dịch.</i>
"""
                    
                    telegram.send_message(message)
                    logger.info(f"Đã gửi thông báo khởi động hệ thống với dữ liệu tài khoản: số dư={balance}, PNL chưa thực hiện={pnl}")
                except Exception as acc_error:
                    logger.error(f"Lỗi khi lấy thông tin tài khoản: {str(acc_error)}")
                    telegram.send_message("<b>🤖 HỆ THỐNG GIAO DỊCH ĐÃ KHỞI ĐỘNG</b>\n\n<i>Không thể lấy thông tin tài khoản.</i>")
            
        except Exception as startup_error:
            logger.error(f"Lỗi khi gửi thông báo khởi động: {str(startup_error)}")
        
        # Chạy scheduler trong một thread riêng
        scheduler_thread = threading.Thread(target=scheduler_thread_func)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
        logger.info("Đã khởi động scheduler và đăng ký các task định kỳ")
    except Exception as e:
        logger.error(f"Lỗi khi khởi động scheduler: {str(e)}")

# Hàm dừng scheduler
def stop_scheduler():
    """Dừng scheduler và thread liên quan"""
    global scheduler_running, scheduler_thread
    
    if not scheduler_running:
        logger.info("Scheduler đã dừng, không cần dừng lại")
        return
    
    try:
        # Đánh dấu dừng thread
        scheduler_running = False
        
        # Chờ thread kết thúc
        if scheduler_thread and scheduler_thread.is_alive():
            scheduler_thread.join(timeout=5)
            
        # Xóa tất cả các task
        schedule.clear()
        
        logger.info("Đã dừng scheduler và xóa các task định kỳ")
    except Exception as e:
        logger.error(f"Lỗi khi dừng scheduler: {str(e)}")

# Chạy scheduler nếu file được chạy trực tiếp
if __name__ == "__main__":
    start_scheduler()
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_scheduler()
        print("Đã dừng scheduler")