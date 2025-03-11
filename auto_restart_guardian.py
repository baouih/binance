#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Auto Restart Guardian - Tự động giám sát và khởi động lại bot khi gặp lỗi
"""

import os
import sys
import time
import signal
import logging
import argparse
import subprocess
import json
import datetime
import traceback
from pathlib import Path

# Thiết lập logging
os.makedirs("logs", exist_ok=True)
log_file = f"logs/guardian_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('guardian')

# File trạng thái
GUARDIAN_STATUS_FILE = "guardian_status.json"
BOT_STARTUP_SCRIPT = "bot_startup.py"
BOT_HEARTBEAT_FILE = "bot_heartbeat.json"

class GuardianMonitor:
    """
    Lớp giám sát và khởi động lại bot tự động
    """
    def __init__(self, 
                max_restarts_per_hour=5, 
                check_interval=60, 
                risk_level=None,
                bot_args=None):
        """
        Khởi tạo
        
        Args:
            max_restarts_per_hour (int): Số lần khởi động lại tối đa trong 1 giờ
            check_interval (int): Khoảng thời gian kiểm tra (giây)
            risk_level (str): Mức độ rủi ro (10, 15, 20, 30)
            bot_args (list): Các tham số bổ sung cho bot
        """
        self.max_restarts_per_hour = max_restarts_per_hour
        self.check_interval = check_interval
        self.risk_level = risk_level
        self.bot_args = bot_args or []
        
        # Trạng thái
        self.start_time = datetime.datetime.now()
        self.restart_count = 0
        self.restart_times = []
        self.bot_process = None
        self.running = True
        
        # Tạo thư mục logs nếu chưa tồn tại
        os.makedirs("logs", exist_ok=True)
        
        # Khởi tạo file trạng thái
        self._init_status_file()
        
        # Đặt handler cho tín hiệu
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _init_status_file(self):
        """Khởi tạo file trạng thái"""
        status = {
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "initializing",
            "restart_count": 0,
            "last_restart": None,
            "bot_status": "not_running",
            "risk_level": self.risk_level,
            "running_time": "0m",
            "last_check": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Lưu file
        with open(GUARDIAN_STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=4, ensure_ascii=False)
    
    def _update_status(self, status="running", bot_status=None):
        """Cập nhật file trạng thái"""
        if os.path.exists(GUARDIAN_STATUS_FILE):
            try:
                with open(GUARDIAN_STATUS_FILE, "r", encoding="utf-8") as f:
                    current_status = json.load(f)
            except:
                current_status = {}
        else:
            current_status = {}
        
        # Cập nhật trạng thái
        current_status["status"] = status
        
        if bot_status:
            current_status["bot_status"] = bot_status
        
        current_status["restart_count"] = self.restart_count
        
        if self.restart_times and len(self.restart_times) > 0:
            current_status["last_restart"] = self.restart_times[-1].strftime("%Y-%m-%d %H:%M:%S")
        
        # Tính thời gian chạy
        running_time = datetime.datetime.now() - self.start_time
        hours, remainder = divmod(running_time.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours >= 24:
            days, hours = divmod(hours, 24)
            current_status["running_time"] = f"{int(days)}d {int(hours)}h {int(minutes)}m"
        elif hours >= 1:
            current_status["running_time"] = f"{int(hours)}h {int(minutes)}m"
        else:
            current_status["running_time"] = f"{int(minutes)}m"
        
        current_status["last_check"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Lưu file
        with open(GUARDIAN_STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(current_status, f, indent=4, ensure_ascii=False)
    
    def _signal_handler(self, sig, frame):
        """Xử lý tín hiệu"""
        logger.info(f"Đã nhận tín hiệu {sig}, dừng giám sát...")
        self.stop()
    
    def start(self):
        """Bắt đầu giám sát"""
        logger.info("===== KHỞI ĐỘNG GUARDIAN =====")
        logger.info(f"Mức độ rủi ro: {self.risk_level if self.risk_level else 'Mặc định'}")
        logger.info(f"Khoảng thời gian kiểm tra: {self.check_interval} giây")
        logger.info(f"Số lần khởi động lại tối đa trong 1 giờ: {self.max_restarts_per_hour}")
        
        # Cập nhật trạng thái
        self._update_status("starting", "not_running")
        
        # Khởi động bot
        self._start_bot()
        
        # Bắt đầu vòng lặp giám sát
        self._monitor_loop()
    
    def _start_bot(self):
        """Khởi động bot"""
        logger.info("Khởi động bot...")
        
        try:
            # Kiểm tra bot đã chạy chưa
            if self.bot_process is not None and self.bot_process.poll() is None:
                logger.warning("Bot đã đang chạy, không cần khởi động lại")
                return
            
            # Chuẩn bị lệnh
            cmd = [sys.executable, BOT_STARTUP_SCRIPT]
            
            # Thêm tham số risk_level nếu có
            if self.risk_level:
                cmd.extend(["--risk-level", self.risk_level])
            
            # Thêm các tham số bổ sung
            if self.bot_args:
                cmd.extend(self.bot_args)
            
            logger.info(f"Lệnh khởi động: {' '.join(cmd)}")
            
            # Tạo file log
            log_path = f"logs/bot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            log_file = open(log_path, "w")
            
            # Khởi động process
            self.bot_process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            logger.info(f"Bot đã được khởi động (PID: {self.bot_process.pid})")
            
            # Cập nhật thời gian khởi động lại
            self.restart_times.append(datetime.datetime.now())
            self.restart_count += 1
            
            # Cập nhật trạng thái
            self._update_status("running", "starting")
            
            # Chờ cho bot khởi động
            time.sleep(5)
            
            # Kiểm tra bot đã khởi động thành công chưa
            if self.bot_process.poll() is not None:
                exit_code = self.bot_process.poll()
                logger.error(f"Bot không khởi động được (Exit code: {exit_code})")
                self._update_status("error", "failed_to_start")
                
                # Kiểm tra log
                if os.path.exists(log_path):
                    logger.info("Kiểm tra log để tìm lỗi:")
                    with open(log_path, "r") as f:
                        log_content = f.read()
                        # Lấy 20 dòng cuối
                        lines = log_content.split("\n")[-20:]
                        for line in lines:
                            if line.strip():
                                logger.info(f"Log: {line.strip()}")
                
                raise Exception(f"Bot không khởi động được (Exit code: {exit_code})")
            
            logger.info("Bot đã khởi động thành công")
            
        except Exception as e:
            logger.error(f"Lỗi khi khởi động bot: {str(e)}")
            logger.error(traceback.format_exc())
            self._update_status("error", "failed_to_start")
            # Bỏ qua lỗi để tiếp tục giám sát
    
    def _monitor_loop(self):
        """Vòng lặp giám sát"""
        logger.info("Bắt đầu vòng lặp giám sát...")
        
        last_check_time = time.time()
        
        try:
            while self.running:
                current_time = time.time()
                
                # Kiểm tra bot nếu đã đến thời gian
                if current_time - last_check_time >= self.check_interval:
                    last_check_time = current_time
                    
                    # Kiểm tra bot
                    self._check_bot()
                
                # Kiểm tra số lần khởi động lại trong 1 giờ
                self._check_restart_limit()
                
                # Ngủ 1 giây
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Đã nhận tín hiệu dừng từ bàn phím")
            self.stop()
        except Exception as e:
            logger.error(f"Lỗi trong vòng lặp giám sát: {str(e)}")
            logger.error(traceback.format_exc())
            self._update_status("error")
    
    def _check_bot(self):
        """Kiểm tra bot có đang chạy bình thường không"""
        logger.debug("Kiểm tra trạng thái bot...")
        
        bot_status = "unknown"
        
        try:
            # Kiểm tra process
            if self.bot_process is None:
                logger.warning("Bot chưa được khởi động")
                bot_status = "not_running"
                self._start_bot()
                return
            
            # Kiểm tra process có đang chạy không
            if self.bot_process.poll() is not None:
                exit_code = self.bot_process.poll()
                logger.warning(f"Bot đã dừng với mã trạng thái: {exit_code}")
                bot_status = "stopped"
                
                # Khởi động lại bot
                self._start_bot()
                return
            
            # Bot đang chạy, kiểm tra heartbeat
            if os.path.exists(BOT_HEARTBEAT_FILE):
                try:
                    with open(BOT_HEARTBEAT_FILE, "r", encoding="utf-8") as f:
                        heartbeat = json.load(f)
                    
                    # Kiểm tra thời gian cập nhật
                    last_update_str = heartbeat.get("last_update")
                    if last_update_str:
                        last_update = datetime.datetime.strptime(last_update_str, "%Y-%m-%d %H:%M:%S")
                        now = datetime.datetime.now()
                        
                        # Nếu cập nhật trong vòng 2 phút, bot vẫn hoạt động
                        if (now - last_update).total_seconds() < 120:
                            bot_status = "running"
                            logger.debug("Bot đang hoạt động bình thường")
                            self._update_status("running", "running")
                            return
                        else:
                            logger.warning(f"Bot heartbeat đã cũ: {(now - last_update).total_seconds():.1f} giây")
                            bot_status = "stalled"
                except Exception as e:
                    logger.error(f"Lỗi khi đọc file heartbeat: {str(e)}")
            
            # Kiểm tra thêm các dấu hiệu khác nếu cần
            
            # Nếu không có heartbeat hoặc heartbeat cũ, thử kiểm tra thêm
            try:
                # Kiểm tra CPU của process
                if os.name == 'posix':  # Linux/Mac
                    cmd = f"ps -p {self.bot_process.pid} -o %cpu"
                    result = subprocess.check_output(cmd, shell=True).decode('utf-8').strip().split('\n')
                    if len(result) > 1:
                        cpu_usage = float(result[1])
                        logger.debug(f"CPU usage: {cpu_usage}%")
                        
                        # Nếu sử dụng CPU, bot đang hoạt động
                        if cpu_usage > 0.1:
                            bot_status = "running"
                            logger.debug("Bot đang hoạt động (sử dụng CPU)")
                            self._update_status("running", "running")
                            return
            except:
                pass
            
            # Nếu bot không phản hồi, khởi động lại
            if bot_status not in ["running"]:
                logger.warning(f"Bot không phản hồi (trạng thái: {bot_status}), khởi động lại...")
                
                # Kết thúc process
                try:
                    self.bot_process.terminate()
                    self.bot_process.wait(timeout=5)
                except:
                    # Nếu không kết thúc được, kill
                    try:
                        self.bot_process.kill()
                    except:
                        pass
                
                # Khởi động lại bot
                self._start_bot()
                
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra bot: {str(e)}")
            logger.error(traceback.format_exc())
            self._update_status("error", bot_status)
    
    def _check_restart_limit(self):
        """Kiểm tra số lần khởi động lại trong 1 giờ"""
        if len(self.restart_times) == 0:
            return
        
        # Chỉ giữ lại các lần khởi động lại trong 1 giờ gần đây
        now = datetime.datetime.now()
        one_hour_ago = now - datetime.timedelta(hours=1)
        
        # Lọc các lần khởi động lại trong 1 giờ
        recent_restarts = [t for t in self.restart_times if t > one_hour_ago]
        self.restart_times = recent_restarts
        
        # Kiểm tra giới hạn
        if len(recent_restarts) > self.max_restarts_per_hour:
            logger.error(f"Đã vượt quá giới hạn khởi động lại ({len(recent_restarts)} lần trong 1 giờ)")
            logger.error("Bot có thể đang gặp vấn đề nghiêm trọng")
            
            # Ghi log các thời điểm khởi động lại
            for i, t in enumerate(recent_restarts):
                logger.error(f"Khởi động lại #{i+1}: {t.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Cập nhật trạng thái
            self._update_status("warning", "restart_limit_exceeded")
            
            # Ngủ một khoảng thời gian dài hơn để tránh khởi động lại liên tục
            logger.info("Chờ 15 phút trước khi thử lại...")
            time.sleep(900)  # 15 phút
            
            # Xóa bớt restart_times để tiếp tục
            self.restart_times = self.restart_times[-self.max_restarts_per_hour:]
    
    def stop(self):
        """Dừng giám sát và bot"""
        logger.info("Dừng giám sát và bot...")
        
        # Đánh dấu dừng
        self.running = False
        
        # Cập nhật trạng thái
        self._update_status("stopping")
        
        # Dừng bot
        if self.bot_process is not None and self.bot_process.poll() is None:
            try:
                # Tạo file tín hiệu dừng
                with open("bot_stop_signal", "w") as f:
                    f.write("stop")
                
                # Chờ bot dừng
                logger.info("Chờ bot dừng...")
                for _ in range(10):
                    if self.bot_process.poll() is not None:
                        break
                    time.sleep(1)
                
                # Nếu bot vẫn chạy, terminate
                if self.bot_process.poll() is None:
                    logger.info("Gửi tín hiệu terminate...")
                    self.bot_process.terminate()
                    self.bot_process.wait(timeout=5)
                
                logger.info("Bot đã dừng")
                
            except Exception as e:
                logger.error(f"Lỗi khi dừng bot: {str(e)}")
                
                # Nếu không dừng được, kill
                try:
                    self.bot_process.kill()
                    logger.info("Đã buộc dừng bot")
                except:
                    pass
        
        # Xóa file tín hiệu dừng nếu có
        if os.path.exists("bot_stop_signal"):
            os.remove("bot_stop_signal")
        
        # Cập nhật trạng thái
        self._update_status("stopped", "stopped")
        
        logger.info("Guardian đã dừng")

def main():
    """Hàm main"""
    # Phân tích tham số dòng lệnh
    parser = argparse.ArgumentParser(description="Auto Restart Guardian - Tự động giám sát và khởi động lại bot")
    parser.add_argument("--max-restarts", type=int, default=5, help="Số lần khởi động lại tối đa trong 1 giờ")
    parser.add_argument("--check-interval", type=int, default=60, help="Khoảng thời gian kiểm tra (giây)")
    parser.add_argument("--risk-level", type=str, help="Mức độ rủi ro (10, 15, 20, 30)")
    parser.add_argument("--enable-telegram", action="store_true", help="Kích hoạt thông báo Telegram")
    parser.add_argument("--symbols", type=str, help="Danh sách cặp tiền (phân cách bằng dấu phẩy)")
    parser.add_argument("--test-mode", action="store_true", help="Chạy ở chế độ test")
    
    # Parse args
    args = parser.parse_args()
    
    # Chuẩn bị tham số cho bot
    bot_args = []
    
    if args.enable_telegram:
        bot_args.append("--enable-telegram")
    
    if args.symbols:
        bot_args.append(f"--symbols={args.symbols}")
    
    if args.test_mode:
        bot_args.append("--test-mode")
    
    # Khởi tạo guardian
    guardian = GuardianMonitor(
        max_restarts_per_hour=args.max_restarts,
        check_interval=args.check_interval,
        risk_level=args.risk_level,
        bot_args=bot_args
    )
    
    # Bắt đầu giám sát
    try:
        guardian.start()
    except KeyboardInterrupt:
        logger.info("Đã nhận tín hiệu dừng từ bàn phím")
    except Exception as e:
        logger.error(f"Lỗi không xử lý được: {str(e)}")
        logger.error(traceback.format_exc())
        return 1
    finally:
        # Dừng guardian
        guardian.stop()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())