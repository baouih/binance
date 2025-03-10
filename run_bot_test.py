#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Run Bot Test - Chạy kiểm tra bot trong chế độ test
"""

import os
import sys
import time
import signal
import logging
import argparse
import subprocess
import datetime
from pathlib import Path

# Thiết lập logging
os.makedirs("logs", exist_ok=True)
log_file = f"logs/bot_test_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('bot_test')

class BotTester:
    """
    Lớp tester cho bot
    """
    def __init__(self, risk_level=None, duration=3600, check_interval=10):
        """
        Khởi tạo
        
        Args:
            risk_level (str): Mức độ rủi ro (nếu có)
            duration (int): Thời gian chạy test (giây)
            check_interval (int): Thời gian kiểm tra trạng thái (giây)
        """
        self.risk_level = risk_level
        self.duration = duration
        self.check_interval = check_interval
        
        self.start_time = None
        self.end_time = None
        self.process = None
        self.is_running = False
        
        # Khởi tạo handler cho tín hiệu
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)
    
    def handle_signal(self, sig, frame):
        """Xử lý khi nhận tín hiệu"""
        logger.info(f"Nhận tín hiệu {sig}, dừng test...")
        self.stop_test()
        sys.exit(0)
    
    def run_test(self):
        """Chạy test"""
        logger.info("===== BẮT ĐẦU KIỂM TRA BOT =====")
        logger.info(f"Mức độ rủi ro: {self.risk_level if self.risk_level else 'Mặc định'}")
        logger.info(f"Thời gian chạy: {self.duration} giây ({self.duration/60:.1f} phút)")
        
        self.start_time = datetime.datetime.now()
        self.end_time = self.start_time + datetime.timedelta(seconds=self.duration)
        
        logger.info(f"Thời gian bắt đầu: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Thời gian kết thúc dự kiến: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Khởi động bot
        self.start_bot()
        self.is_running = True
        
        try:
            # Vòng lặp kiểm tra
            while datetime.datetime.now() < self.end_time and self.is_running:
                # Kiểm tra bot có đang chạy không
                if self.process is not None:
                    if self.process.poll() is not None:
                        logger.error(f"Bot đã dừng với mã trạng thái: {self.process.poll()}")
                        logger.error("Test thất bại")
                        return False
                
                # Tính thời gian còn lại
                remaining = (self.end_time - datetime.datetime.now()).total_seconds()
                elapsed = (datetime.datetime.now() - self.start_time).total_seconds()
                
                # Hiển thị tiến trình
                progress = min(100, elapsed / self.duration * 100)
                logger.info(f"Tiến trình: {progress:.1f}% | Còn lại: {remaining:.1f} giây")
                
                # Kiểm tra log của bot
                self.check_bot_logs()
                
                # Ngủ
                time.sleep(self.check_interval)
            
            # Kiểm tra kết quả
            if datetime.datetime.now() >= self.end_time:
                logger.info("===== KIỂM TRA HOÀN TẤT =====")
                logger.info("Bot đã chạy ổn định trong thời gian yêu cầu")
                logger.info("Test thành công")
                return True
                
        except KeyboardInterrupt:
            logger.info("Người dùng dừng test")
        finally:
            # Dừng bot
            self.stop_test()
        
        return False
    
    def start_bot(self):
        """Khởi động bot với chế độ test"""
        # Chuẩn bị lệnh
        cmd = [sys.executable, "bot_startup.py", "--test-mode"]
        if self.risk_level:
            cmd.extend(["--risk-level", self.risk_level])
        
        logger.info(f"Khởi động bot với lệnh: {' '.join(cmd)}")
        
        try:
            # Mở file log
            log_file = open(f"logs/bot_process_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log", "w")
            
            # Khởi động process
            self.process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            logger.info(f"Bot đã khởi động với PID: {self.process.pid}")
            
            # Chờ bot khởi động
            logger.info("Chờ bot khởi động...")
            time.sleep(5)
            
            # Kiểm tra bot đã khởi động thành công chưa
            if self.process.poll() is not None:
                logger.error(f"Bot khởi động thất bại với mã trạng thái: {self.process.poll()}")
                raise Exception("Không thể khởi động bot")
            
            logger.info("Bot đã khởi động thành công")
            
        except Exception as e:
            logger.error(f"Lỗi khi khởi động bot: {str(e)}")
            raise
    
    def check_bot_logs(self):
        """Kiểm tra log của bot"""
        # Tìm file log mới nhất
        try:
            log_dir = Path("logs")
            log_files = list(log_dir.glob("bot_process_*.log"))
            
            if not log_files:
                return
            
            # Lấy file log mới nhất
            latest_log = max(log_files, key=os.path.getmtime)
            
            # Kiểm tra log có lỗi không
            with open(latest_log, "r") as f:
                lines = f.readlines()
                
                # Tìm 10 dòng cuối
                last_lines = lines[-10:] if len(lines) >= 10 else lines
                
                # Kiểm tra có lỗi nghiêm trọng không
                for line in last_lines:
                    if "ERROR" in line and "CRITICAL" in line:
                        logger.warning(f"Phát hiện lỗi trong log: {line.strip()}")
            
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra log: {str(e)}")
    
    def stop_test(self):
        """Dừng test và bot"""
        self.is_running = False
        
        if self.process is not None and self.process.poll() is None:
            logger.info(f"Dừng bot (PID: {self.process.pid})...")
            
            try:
                # Gửi tín hiệu để dừng
                if os.name == 'nt':  # Windows
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.process.pid)])
                else:  # Linux/Mac
                    self.process.terminate()
                    
                # Chờ quá trình kết thúc
                self.process.wait(timeout=5)
                logger.info("Bot đã dừng thành công")
                
            except subprocess.TimeoutExpired:
                logger.warning("Bot không phản hồi, buộc dừng...")
                self.process.kill()
            except Exception as e:
                logger.error(f"Lỗi khi dừng bot: {str(e)}")
        
        # Tính toán thời gian chạy
        if self.start_time:
            run_time = (datetime.datetime.now() - self.start_time).total_seconds()
            logger.info(f"Tổng thời gian chạy: {run_time:.1f} giây ({run_time/60:.1f} phút)")

def main():
    """Hàm main"""
    parser = argparse.ArgumentParser(description="Chạy kiểm tra Bot")
    parser.add_argument('--risk-level', type=str, help="Mức độ rủi ro (10, 15, 20, 30)")
    parser.add_argument('--duration', type=int, default=3600, help="Thời gian chạy test (giây)")
    parser.add_argument('--check-interval', type=int, default=10, help="Thời gian kiểm tra trạng thái (giây)")
    
    args = parser.parse_args()
    
    # Hiển thị thông tin
    print("===== CHẠY KIỂM TRA BOT =====")
    print(f"Thời gian chạy: {args.duration} giây ({args.duration/60:.1f} phút)")
    print(f"Mức độ rủi ro: {args.risk_level if args.risk_level else 'Mặc định'}")
    
    # Khởi tạo tester
    tester = BotTester(
        risk_level=args.risk_level,
        duration=args.duration,
        check_interval=args.check_interval
    )
    
    # Chạy test
    try:
        success = tester.run_test()
        
        if success:
            print("\n===== TEST THÀNH CÔNG =====")
            print("Bot đã chạy ổn định trong toàn bộ thời gian kiểm tra")
            print(f"Bạn có thể xem log tại: {log_file}")
        else:
            print("\n===== TEST THẤT BẠI =====")
            print("Bot gặp lỗi trong quá trình chạy")
            print(f"Vui lòng kiểm tra log tại: {log_file}")
        
        return 0 if success else 1
    
    except Exception as e:
        logger.error(f"Lỗi không xử lý được: {str(e)}")
        print(f"\n===== LỖI: {str(e)} =====")
        return 1

if __name__ == "__main__":
    sys.exit(main())