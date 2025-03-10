#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Auto Restart Guardian - Bảo vệ và tự động khởi động lại bot khi gặp lỗi
"""

import os
import sys
import time
import signal
import logging
import datetime
import subprocess
import threading
import argparse
import json
from pathlib import Path

# Thiết lập logging
os.makedirs("logs", exist_ok=True)
log_file = f"logs/guardian_{datetime.datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('guardian')

class BotGuardian:
    """
    Lớp Guardian giám sát và tự động khởi động lại bot khi gặp lỗi
    """
    def __init__(self, bot_script="bot_startup.py", max_restarts=5, check_interval=60, risk_level=None):
        """
        Khởi tạo Guardian
        
        Args:
            bot_script (str): Đường dẫn đến script bot chính
            max_restarts (int): Số lần khởi động lại tối đa trong 1 giờ
            check_interval (int): Thời gian kiểm tra trạng thái (giây)
            risk_level (str): Mức độ rủi ro (nếu có)
        """
        self.bot_script = bot_script
        self.max_restarts = max_restarts
        self.check_interval = check_interval
        self.risk_level = risk_level
        
        self.process = None
        self.is_running = False
        self.restart_count = 0
        self.restart_timestamps = []
        self.last_restart = None
        self.start_time = datetime.datetime.now()
        
        # Thông tin trạng thái
        self.status = {
            "running": False,
            "uptime": 0,
            "restarts": 0,
            "last_restart": None,
            "bot_status": "stopped"
        }
        
        # Khởi tạo tín hiệu để xử lý khi nhận Ctrl+C
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)
    
    def handle_signal(self, sig, frame):
        """Xử lý khi nhận tín hiệu kết thúc"""
        logger.info(f"Nhận tín hiệu {sig}, dừng Guardian và Bot...")
        self.stop()
        sys.exit(0)
    
    def start(self):
        """Khởi động Guardian và Bot"""
        logger.info("===== Bot Guardian khởi động =====")
        logger.info(f"Sử dụng script: {self.bot_script}")
        logger.info(f"Mức độ rủi ro: {self.risk_level if self.risk_level else 'Mặc định'}")
        
        self.is_running = True
        self.status["running"] = True
        
        # Khởi động thread giám sát
        monitor_thread = threading.Thread(target=self.monitor_bot)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Khởi động bot
        self.start_bot()
        
        try:
            # Vòng lặp chính
            while self.is_running:
                self._update_status()
                self._save_status()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("Nhận lệnh dừng từ người dùng")
        finally:
            self.stop()
    
    def _update_status(self):
        """Cập nhật thông tin trạng thái"""
        if self.process:
            self.status["uptime"] = (datetime.datetime.now() - self.start_time).total_seconds() // 60
            self.status["restarts"] = self.restart_count
            self.status["last_restart"] = self.last_restart.strftime("%Y-%m-%d %H:%M:%S") if self.last_restart else None
            self.status["bot_status"] = "running" if self.process.poll() is None else "stopped"
    
    def _save_status(self):
        """Lưu trạng thái vào file"""
        try:
            with open("guardian_status.json", "w") as f:
                json.dump(self.status, f, indent=4)
        except Exception as e:
            logger.error(f"Lỗi khi lưu trạng thái: {str(e)}")
    
    def start_bot(self):
        """Khởi động bot"""
        if self.process is not None and self.process.poll() is None:
            logger.warning("Bot đã đang chạy, không khởi động lại")
            return
        
        # Chuẩn bị lệnh
        cmd = [sys.executable, self.bot_script]
        if self.risk_level:
            cmd.extend(["--risk-level", self.risk_level])
        
        # Ghi nhận thời gian khởi động
        self.last_restart = datetime.datetime.now()
        self.restart_timestamps.append(self.last_restart)
        self.restart_count += 1
        
        # Xóa các timestamp cũ (hơn 1 giờ)
        one_hour_ago = datetime.datetime.now() - datetime.timedelta(hours=1)
        self.restart_timestamps = [ts for ts in self.restart_timestamps if ts > one_hour_ago]
        
        # Kiểm tra số lần khởi động lại trong 1 giờ
        if len(self.restart_timestamps) > self.max_restarts:
            logger.error(f"Đã vượt quá giới hạn khởi động lại ({self.max_restarts} lần/giờ)")
            logger.error("Có thể bot đang gặp vấn đề nghiêm trọng. Guardian sẽ dừng để bảo vệ hệ thống.")
            self.is_running = False
            return
        
        try:
            # Mở file log
            log_file = open(f"logs/bot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log", "w")
            
            # Khởi động process
            logger.info(f"Khởi động bot với lệnh: {' '.join(cmd)}")
            self.process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            logger.info(f"Bot đã khởi động với PID: {self.process.pid}")
            
        except Exception as e:
            logger.error(f"Lỗi khi khởi động bot: {str(e)}")
    
    def monitor_bot(self):
        """Giám sát trạng thái bot và tự động khởi động lại nếu cần"""
        while self.is_running:
            # Kiểm tra bot có đang chạy không
            if self.process is not None:
                return_code = self.process.poll()
                
                # Nếu bot đã dừng
                if return_code is not None:
                    logger.warning(f"Bot đã dừng với mã trạng thái: {return_code}")
                    if return_code != 0:  # Lỗi
                        logger.info("Tự động khởi động lại bot...")
                        self.start_bot()
                    else:  # Dừng bình thường
                        logger.info("Bot dừng bình thường, không khởi động lại")
                        self.process = None
            
            # Ngủ 10 giây trước khi kiểm tra lại
            time.sleep(10)
    
    def stop(self):
        """Dừng Guardian và Bot"""
        logger.info("Dừng Guardian và Bot...")
        
        self.is_running = False
        self.status["running"] = False
        
        # Dừng bot nếu đang chạy
        if self.process is not None and self.process.poll() is None:
            try:
                logger.info(f"Gửi tín hiệu kết thúc đến bot (PID: {self.process.pid})...")
                if os.name == 'nt':  # Windows
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.process.pid)])
                else:  # Linux/Mac
                    self.process.terminate()
                    self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Bot không phản hồi, buộc đóng...")
                self.process.kill()
            except Exception as e:
                logger.error(f"Lỗi khi dừng bot: {str(e)}")
        
        logger.info("===== Guardian đã dừng =====")
        self._update_status()
        self._save_status()

def main():
    """Hàm main"""
    parser = argparse.ArgumentParser(description="Bot Guardian - Tự động giám sát và khởi động lại bot")
    parser.add_argument('--script', type=str, default="bot_startup.py", help="Đường dẫn đến script bot")
    parser.add_argument('--risk-level', type=str, help="Mức độ rủi ro (10, 15, 20, 30)")
    parser.add_argument('--max-restarts', type=int, default=5, help="Số lần khởi động lại tối đa trong 1 giờ")
    parser.add_argument('--check-interval', type=int, default=60, help="Thời gian kiểm tra trạng thái (giây)")
    
    args = parser.parse_args()
    
    # Khởi tạo Guardian
    guardian = BotGuardian(
        bot_script=args.script,
        max_restarts=args.max_restarts,
        check_interval=args.check_interval,
        risk_level=args.risk_level
    )
    
    # Khởi động Guardian
    guardian.start()

if __name__ == "__main__":
    main()