"""
Hệ thống thông báo thị trường tự động
Module này sẽ tự động gửi thông báo phân tích thị trường theo lịch trình cho các cặp tiền điện tử
"""
import time
import logging
import threading
import schedule
import json
import os
from datetime import datetime, timedelta
import random

# Import các module thông báo của hệ thống
from detailed_trade_notifications import DetailedTradeNotifications
from telegram_notifier import TelegramNotifier
from market_analysis_system import MarketAnalysisSystem

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('auto_market_notifier')

class AutoMarketNotifier:
    """Lớp quản lý thông báo thị trường tự động theo lịch trình"""
    
    def __init__(self):
        """Khởi tạo hệ thống thông báo thị trường tự động"""
        self.notifier = DetailedTradeNotifications()
        self.market_analyzer = MarketAnalysisSystem()
        self.telegram = TelegramNotifier()
        self.active = False
        self.thread = None
        self.monitored_coins = self._load_monitored_coins()
        self.last_notification_time = {}
        
        # Tạo thư mục logs nếu chưa tồn tại
        os.makedirs('logs', exist_ok=True)
        
        logger.info(f"Khởi tạo Auto Market Notifier với {len(self.monitored_coins)} cặp tiền điện tử")
        
    def _load_monitored_coins(self):
        """Tải danh sách các cặp tiền điện tử được theo dõi từ cấu hình"""
        try:
            # Thử tải từ account_config.json
            with open('account_config.json', 'r') as f:
                config = json.load(f)
                if 'monitored_symbols' in config:
                    return config['monitored_symbols']
            
            # Mặc định nếu không tìm thấy
            return [
                "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", 
                "DOGEUSDT", "MATICUSDT", "LINKUSDT", "DOTUSDT", "LTCUSDT",
                "AVAXUSDT", "XRPUSDT", "NEARUSDT"
            ]
        except Exception as e:
            logger.error(f"Lỗi khi tải danh sách cặp tiền điện tử: {e}")
            # Trả về danh sách mặc định
            return ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
    
    def send_single_coin_analysis(self, symbol):
        """Gửi phân tích cho một cặp tiền điện tử"""
        try:
            logger.info(f"Đang gửi phân tích thị trường cho {symbol}")
            # Tạo phân tích thị trường
            analysis = self.market_analyzer.analyze_symbol(symbol)
            if analysis:
                # Gửi thông báo
                self.notifier.notify_market_analysis(analysis)
                # Cập nhật thời gian thông báo cuối cùng
                self.last_notification_time[symbol] = datetime.now()
                logger.info(f"Đã gửi phân tích thị trường thành công cho {symbol}")
                return True
            else:
                logger.warning(f"Không thể tạo phân tích thị trường cho {symbol}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi phân tích thị trường cho {symbol}: {e}")
            return False

    def send_multi_coin_analysis(self):
        """Gửi phân tích đa cặp tiền điện tử"""
        try:
            # Lấy ngẫu nhiên 4-5 cặp tiền điện tử để phân tích
            num_coins = min(len(self.monitored_coins), random.randint(4, 5))
            selected_coins = random.sample(self.monitored_coins, num_coins)
            
            logger.info(f"Đang gửi phân tích đa cặp tiền điện tử: {selected_coins}")
            self.notifier.send_multi_symbol_analysis(selected_coins)
            logger.info(f"Đã gửi phân tích đa cặp tiền điện tử thành công")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi gửi phân tích đa cặp tiền điện tử: {e}")
            return False
    
    def send_no_trade_reasons(self, symbol):
        """Gửi lý do không giao dịch cho một cặp tiền điện tử"""
        try:
            logger.info(f"Đang gửi lý do không giao dịch cho {symbol}")
            self.notifier.send_no_trade_reasons(symbol)
            logger.info(f"Đã gửi lý do không giao dịch thành công cho {symbol}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi gửi lý do không giao dịch cho {symbol}: {e}")
            return False
    
    def send_important_market_update(self):
        """Gửi cập nhật quan trọng về thị trường"""
        try:
            # Lấy cặp BTC làm chuẩn cho phân tích thị trường tổng thể
            logger.info("Đang gửi cập nhật quan trọng về thị trường")
            
            # Thực hiện phân tích thị trường tổng thể
            market_state = self.market_analyzer.get_market_regime()
            
            # Tạo thông báo
            message = f"🔎 *PHÂN TÍCH THỊ TRƯỜNG TỔNG THỂ*\n\n"
            message += f"⏰ *Thời gian*: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
            message += f"📊 *Trạng thái thị trường*: {market_state['regime']}\n"
            message += f"📈 *Độ biến động*: {market_state['volatility']:.2f}%\n"
            message += f"🧮 *Chỉ số thị trường*: {market_state['market_score']:.2f}/100\n\n"
            message += f"💡 *Gợi ý*: {market_state['recommendation']}\n\n"
            message += f"_Đây là thông báo tự động từ hệ thống Auto Market Notifier_"
            
            # Gửi thông báo
            self.telegram.send_message(message)
            logger.info("Đã gửi cập nhật quan trọng về thị trường thành công")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi gửi cập nhật quan trọng về thị trường: {e}")
            return False
    
    def _schedule_jobs(self):
        """Lập lịch các công việc thông báo tự động"""
        # Xóa tất cả các công việc đã lập lịch trước đó
        schedule.clear()
        
        # Lập lịch gửi phân tích đơn cặp tiền điện tử (mỗi 2 giờ)
        for symbol in self.monitored_coins:
            # Phân bổ ngẫu nhiên thời gian để tránh gửi cùng lúc tất cả các thông báo
            hour = random.randint(0, 23)
            minute = random.randint(0, 59)
            schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(self.send_single_coin_analysis, symbol=symbol)
            logger.info(f"Đã lập lịch phân tích hàng ngày cho {symbol} vào lúc {hour:02d}:{minute:02d}")
        
        # Lập lịch gửi phân tích đa cặp tiền điện tử (4 lần mỗi ngày)
        for hour in [6, 12, 18, 23]:
            minute = random.randint(0, 59)
            schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(self.send_multi_coin_analysis)
            logger.info(f"Đã lập lịch phân tích đa cặp tiền điện tử vào lúc {hour:02d}:{minute:02d}")
        
        # Lập lịch gửi cập nhật quan trọng về thị trường (2 lần mỗi ngày)
        schedule.every().day.at("08:30").do(self.send_important_market_update)
        schedule.every().day.at("20:30").do(self.send_important_market_update)
        logger.info("Đã lập lịch cập nhật quan trọng về thị trường vào lúc 08:30 và 20:30")
        
        # Lập lịch ngẫu nhiên để gửi lý do không giao dịch
        for symbol in self.monitored_coins[:4]:  # Chỉ lấy 4 cặp đầu tiên
            hour = random.randint(0, 23)
            minute = random.randint(0, 59)
            schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(self.send_no_trade_reasons, symbol=symbol)
            logger.info(f"Đã lập lịch gửi lý do không giao dịch cho {symbol} vào lúc {hour:02d}:{minute:02d}")
        
        # Thêm một số thông báo mỗi vài giờ cho các trường hợp cần thiết
        schedule.every(4).hours.do(self.send_single_coin_analysis, symbol="BTCUSDT")
        schedule.every(6).hours.do(self.send_single_coin_analysis, symbol="ETHUSDT")
        
        logger.info("Đã cấu hình tất cả các lịch trình thông báo tự động")
    
    def _run_scheduler(self):
        """Chạy bộ lập lịch trong một vòng lặp vô hạn"""
        logger.info("Bắt đầu bộ lập lịch thông báo tự động")
        self._schedule_jobs()
        
        # Lập lịch lại mỗi ngày để đảm bảo cập nhật
        last_reschedule_date = datetime.now().date()
        
        while self.active:
            try:
                # Kiểm tra và chạy các công việc theo lịch
                schedule.run_pending()
                
                # Lập lịch lại mỗi ngày để cập nhật ngẫu nhiên thời gian thông báo
                current_date = datetime.now().date()
                if current_date > last_reschedule_date:
                    logger.info("Lập lịch lại các công việc thông báo tự động")
                    self._schedule_jobs()
                    last_reschedule_date = current_date
                
                # Ngủ 10 giây trước khi kiểm tra lại
                time.sleep(10)
            except Exception as e:
                logger.error(f"Lỗi trong bộ lập lịch: {e}")
                time.sleep(60)  # Tạm dừng 1 phút nếu có lỗi
    
    def start(self):
        """Bắt đầu hệ thống thông báo tự động"""
        if not self.active:
            self.active = True
            # Khởi tạo và bắt đầu thread
            self.thread = threading.Thread(target=self._run_scheduler)
            self.thread.daemon = True
            self.thread.start()
            logger.info("Đã bắt đầu hệ thống thông báo thị trường tự động")
            
            # Gửi thông báo về việc khởi động hệ thống
            startup_message = (
                "🤖 *HỆ THỐNG THÔNG BÁO TỰ ĐỘNG ĐÃ KHỞI ĐỘNG*\n\n"
                f"Thời gian: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                f"Coins được theo dõi: {len(self.monitored_coins)} cặp\n"
                "Các loại thông báo:\n"
                "✓ Phân tích đơn cặp tiền\n"
                "✓ Phân tích đa cặp tiền\n"
                "✓ Cập nhật trạng thái thị trường\n"
                "✓ Lý do không giao dịch\n\n"
                "_Hệ thống sẽ tự động gửi thông báo theo lịch trình_"
            )
            try:
                self.telegram.send_message(startup_message)
            except Exception as e:
                logger.warning(f"Không thể gửi thông báo khởi động: {e}")
            
            return True
        else:
            logger.warning("Hệ thống thông báo tự động đã được khởi động trước đó")
            return False
    
    def stop(self):
        """Dừng hệ thống thông báo tự động"""
        if self.active:
            self.active = False
            # Chờ thread kết thúc
            if self.thread:
                self.thread.join(timeout=2.0)
            logger.info("Đã dừng hệ thống thông báo thị trường tự động")
            
            # Gửi thông báo về việc dừng hệ thống
            try:
                shutdown_message = (
                    "🛑 *HỆ THỐNG THÔNG BÁO TỰ ĐỘNG ĐÃ DỪNG*\n\n"
                    f"Thời gian: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                    "_Hệ thống sẽ không gửi thông báo tự động cho đến khi được khởi động lại_"
                )
                self.telegram.send_message(shutdown_message)
            except Exception as e:
                logger.warning(f"Không thể gửi thông báo dừng: {e}")
            
            return True
        else:
            logger.warning("Hệ thống thông báo tự động chưa được khởi động")
            return False
    
    def is_running(self):
        """Kiểm tra xem hệ thống thông báo tự động có đang chạy hay không"""
        return self.active
    
    def get_status(self):
        """Lấy trạng thái của hệ thống thông báo tự động"""
        status = {
            "active": self.active,
            "monitored_coins": self.monitored_coins,
            "scheduled_jobs": len(schedule.get_jobs()) if self.active else 0,
            "last_notification": {symbol: time.strftime("%Y-%m-%d %H:%M:%S") 
                                 for symbol, time in self.last_notification_time.items()}
        }
        return status
    
    def test_notification(self, symbol="BTCUSDT"):
        """Gửi thông báo phân tích thử nghiệm"""
        logger.info(f"Gửi thông báo thử nghiệm cho {symbol}")
        return self.send_single_coin_analysis(symbol)

# Tạo một instance toàn cục của AutoMarketNotifier
auto_notifier = None

def get_auto_notifier():
    """Trả về instance toàn cục của AutoMarketNotifier"""
    global auto_notifier
    if auto_notifier is None:
        auto_notifier = AutoMarketNotifier()
    return auto_notifier

# Hàm này được gọi từ main.py để khởi động hệ thống thông báo tự động
def start_auto_notifier():
    """Khởi động hệ thống thông báo tự động"""
    notifier = get_auto_notifier()
    return notifier.start()

if __name__ == "__main__":
    # Khi chạy file này trực tiếp, khởi động hệ thống và gửi thông báo thử nghiệm
    logging.info("Khởi động hệ thống thông báo tự động trực tiếp")
    notifier = get_auto_notifier()
    notifier.start()
    
    # Gửi thông báo thử nghiệm
    notifier.test_notification("BTCUSDT")
    
    # Giữ cho chương trình chạy
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        notifier.stop()
        logging.info("Đã dừng hệ thống thông báo tự động")