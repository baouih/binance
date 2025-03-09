#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Trình điều khiển backtest với thông báo Telegram

Script này khởi chạy quá trình backtest toàn diện và gửi cập nhật trạng thái
qua Telegram theo các mốc quan trọng.
"""

import os
import sys
import time
import json
import logging
import datetime
import subprocess
from dotenv import load_dotenv

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('backtest_controller.log')
    ]
)
logger = logging.getLogger(__name__)

# Tải các biến môi trường
load_dotenv()

# Đường dẫn đến các file quan trọng
BACKTEST_SCRIPT = "comprehensive_backtest.py"
BACKTEST_LOG = "backtest_output.log"
BACKTEST_PID = "backtest.pid"
BACKTEST_CONFIG = "backtest_master_config.json"
TELEGRAM_NOTIFIER = "telegram_notifier.py"

def send_telegram_notification(message_type, message_content):
    """
    Gửi thông báo qua Telegram
    
    Args:
        message_type (str): Loại thông báo ('info', 'warning', 'success', 'error')
        message_content (str): Nội dung thông báo
    """
    try:
        cmd = [sys.executable, TELEGRAM_NOTIFIER, message_type, message_content]
        subprocess.run(cmd, check=True)
        logger.info(f"Đã gửi thông báo Telegram thành công: {message_type}")
    except Exception as e:
        logger.error(f"Lỗi khi gửi thông báo Telegram: {e}")

def check_process_running(pid_file):
    """
    Kiểm tra xem tiến trình có đang chạy không
    
    Args:
        pid_file (str): Đường dẫn đến file PID
        
    Returns:
        bool: True nếu tiến trình đang chạy, False nếu không
    """
    if not os.path.exists(pid_file):
        return False
    
    try:
        with open(pid_file, 'r') as f:
            pid_str = f.read().strip()
            if not pid_str:
                return False
            pid = int(pid_str)
            
        # Kiểm tra tiến trình có tồn tại không
        try:
            os.kill(pid, 0)
            
            # Kiểm tra thêm qua /proc (Linux) hoặc ps (Unix)
            if sys.platform.startswith('linux'):
                return os.path.exists(f"/proc/{pid}")
            else:
                import subprocess
                result = subprocess.run(["ps", "-p", str(pid)], capture_output=True)
                return result.returncode == 0
                
        except OSError:
            return False
            
    except (OSError, ValueError, Exception) as e:
        logger.error(f"Lỗi khi kiểm tra tiến trình: {e}")
        return False

def start_backtest():
    """
    Khởi động quá trình backtest
    
    Returns:
        bool: True nếu khởi động thành công, False nếu không
    """
    if check_process_running(BACKTEST_PID):
        logger.warning("Backtest đã đang chạy")
        return False
    
    try:
        # Đọc cấu hình để hiển thị thông tin
        config = {}
        with open(BACKTEST_CONFIG, 'r') as f:
            config = json.load(f)
            
        # Khởi động backtest trong nền
        env = os.environ.copy()
        # Chắc chắn PYTHONPATH được thiết lập đúng
        env["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__))
        
        # Thêm các thiết lập môi trường cần thiết
        env["BACKTEST_MODE"] = "comprehensive"
        env["NOTIFIER_ENABLED"] = "true"
        
        with open(BACKTEST_LOG, 'w') as log_file:
            process = subprocess.Popen(
                [sys.executable, BACKTEST_SCRIPT],
                stdout=log_file,
                stderr=log_file,
                env=env,
                # Đảm bảo chạy trong thư mục hiện tại
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
        # Lưu PID
        with open(BACKTEST_PID, 'w') as f:
            f.write(str(process.pid))
            
        logger.info(f"Đã khởi động backtest với PID: {process.pid}")
        
        # Tạo thông báo khởi động
        symbols = ', '.join(config.get('symbols', ['BTCUSDT']))
        timeframes = ', '.join(config.get('timeframes', ['1h']))
        phases = len(config.get('phases', []))
        
        start_msg = (
            f"🚀 BẮT ĐẦU BACKTEST TOÀN DIỆN\n\n"
            f"🔸 Số dư ban đầu: ${config.get('initial_balance', 10000)}\n"
            f"🔸 Cặp tiền: {symbols}\n"
            f"🔸 Khung thời gian: {timeframes}\n"
            f"🔸 Số giai đoạn: {phases}\n"
            f"🔸 Thời gian bắt đầu: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Quá trình này sẽ mất nhiều thời gian. Bạn sẽ nhận được thông báo theo tiến độ."
        )
        
        send_telegram_notification('info', start_msg)
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi khởi động backtest: {e}")
        send_telegram_notification('error', f"❌ Lỗi khi khởi động backtest: {e}")
        return False

def monitor_backtest():
    """
    Giám sát tiến trình backtest và gửi thông báo
    """
    if not check_process_running(BACKTEST_PID):
        logger.warning("Không tìm thấy tiến trình backtest đang chạy")
        return
    
    try:
        with open(BACKTEST_PID, 'r') as f:
            pid = int(f.read().strip())
            
        # Theo dõi log file để gửi cập nhật
        last_position = 0
        data_preparation_notified = False
        training_phase_notified = False
        optimization_phase_notified = False
        testing_phase_notified = False
        completion_notified = False
        
        check_interval = 60  # Kiểm tra mỗi 60 giây
        
        logger.info(f"Bắt đầu giám sát backtest (PID: {pid})")
        
        while check_process_running(BACKTEST_PID):
            # Đọc nội dung mới từ log file
            if os.path.exists(BACKTEST_LOG):
                with open(BACKTEST_LOG, 'r') as f:
                    f.seek(last_position)
                    new_content = f.read()
                    last_position = f.tell()
                
                # Kiểm tra các mốc quan trọng trong log
                if "Bước 1: Chuẩn bị dữ liệu" in new_content and not data_preparation_notified:
                    data_preparation_notified = True
                    send_telegram_notification('info', "🔄 BACKTEST: Đang chuẩn bị dữ liệu thị trường...")
                
                if "Giai đoạn huấn luyện ban đầu" in new_content and not training_phase_notified:
                    training_phase_notified = True
                    send_telegram_notification('info', "📊 BACKTEST: Đã bắt đầu giai đoạn huấn luyện ban đầu")
                
                if "Giai đoạn tối ưu hóa" in new_content and not optimization_phase_notified:
                    optimization_phase_notified = True
                    send_telegram_notification('info', "⚙️ BACKTEST: Đã bắt đầu giai đoạn tối ưu hóa")
                
                if "Giai đoạn kiểm thử mở rộng" in new_content and not testing_phase_notified:
                    testing_phase_notified = True
                    send_telegram_notification('info', "🧪 BACKTEST: Đã bắt đầu giai đoạn kiểm thử mở rộng")
                
                if "Đã hoàn thành backtest" in new_content and not completion_notified:
                    completion_notified = True
                    # Lấy kết quả từ log để đưa vào thông báo
                    roi_line = ""
                    for line in new_content.split('\n'):
                        if "ROI:" in line:
                            roi_line = line.strip()
                            break
                    
                    completion_msg = (
                        f"✅ BACKTEST HOÀN THÀNH\n\n"
                        f"🔹 Thời gian kết thúc: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"🔹 {roi_line if roi_line else 'Kết quả: Xem báo cáo chi tiết'}\n\n"
                        f"Báo cáo chi tiết đã được lưu vào thư mục backtest_reports"
                    )
                    send_telegram_notification('success', completion_msg)
            
            # Kiểm tra trạng thái RAM và CPU
            if last_position > 0 and last_position % (5 * 1024 * 1024) < 100:  # Cứ mỗi 5MB log
                try:
                    memory_info = subprocess.check_output(['ps', '-p', str(pid), '-o', 'rss,pcpu']).decode('utf-8')
                    memory_info = memory_info.strip().split('\n')[1].strip()
                    send_telegram_notification('info', f"📈 BACKTEST: Tiến độ cập nhật\nSử dụng tài nguyên: {memory_info}")
                except Exception:
                    pass
            
            time.sleep(check_interval)
        
        # Kiểm tra xem backtest đã hoàn thành hay bị lỗi
        if not completion_notified:
            logger.warning("Backtest dừng mà không có thông báo hoàn thành")
            send_telegram_notification('warning', "⚠️ BACKTEST: Quá trình đã dừng mà không hoàn thành. Kiểm tra log để biết thêm thông tin.")
            
    except Exception as e:
        logger.error(f"Lỗi khi giám sát backtest: {e}")
        send_telegram_notification('error', f"❌ Lỗi khi giám sát backtest: {e}")

def main():
    """Hàm chính"""
    logger.info("Khởi động controller backtest với thông báo Telegram")
    
    if start_backtest():
        monitor_backtest()
    else:
        logger.warning("Không thể khởi động backtest")

if __name__ == "__main__":
    main()