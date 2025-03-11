#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Setup 24/7 Service - Cài đặt dịch vụ tự động chạy bot 24/7
"""

import os
import sys
import argparse
import logging
import platform
import subprocess
import getpass
import textwrap
from pathlib import Path

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('setup_service')

class ServiceSetup:
    """
    Lớp cài đặt dịch vụ 24/7 cho bot
    """
    def __init__(self, name="trading_bot", description="Trading Bot 24/7 Service", auto_start=True, risk_level=None):
        """
        Khởi tạo
        
        Args:
            name (str): Tên dịch vụ
            description (str): Mô tả dịch vụ
            auto_start (bool): Tự động khởi động dịch vụ khi hệ thống khởi động
            risk_level (str): Mức độ rủi ro (nếu có)
        """
        self.name = name
        self.description = description
        self.auto_start = auto_start
        self.risk_level = risk_level
        
        self.current_dir = os.path.abspath(os.path.dirname(__file__))
        self.python_path = sys.executable
        self.username = getpass.getuser()
        
        # Kiểm tra hệ điều hành
        self.is_windows = platform.system() == "Windows"
        self.is_linux = platform.system() == "Linux"
        self.is_macos = platform.system() == "Darwin"
    
    def setup_service(self):
        """Cài đặt dịch vụ phù hợp với hệ điều hành"""
        logger.info(f"Cài đặt dịch vụ cho {platform.system()}")
        
        if self.is_windows:
            return self.setup_windows_service()
        elif self.is_linux:
            return self.setup_linux_service()
        elif self.is_macos:
            return self.setup_macos_service()
        else:
            logger.error(f"Hệ điều hành không được hỗ trợ: {platform.system()}")
            return False
    
    def setup_windows_service(self):
        """Cài đặt Windows Service"""
        try:
            # Kiểm tra quyền admin
            if not self._check_admin_windows():
                logger.error("Bạn cần chạy với quyền Administrator để cài đặt dịch vụ Windows")
                return False
            
            # Tạo batch script để chạy bot
            batch_path = os.path.join(self.current_dir, f"{self.name}_service.bat")
            with open(batch_path, "w") as f:
                f.write(f'@echo off\r\n')
                f'cd /d "{self.current_dir}"\r\n'
                
                if self.risk_level:
                    f.write(f'"{self.python_path}" auto_restart_guardian.py --risk-level {self.risk_level}\r\n')
                else:
                    f.write(f'"{self.python_path}" auto_restart_guardian.py\r\n')
            
            # Cài đặt dịch vụ bằng NSSM (Non-Sucking Service Manager)
            nssm_path = os.path.join(self.current_dir, "tools", "nssm.exe")
            
            # Kiểm tra NSSM đã có chưa, nếu chưa thì tải về
            if not os.path.exists(nssm_path):
                self._download_nssm()
            
            # Cài đặt dịch vụ
            logger.info(f"Cài đặt dịch vụ Windows '{self.name}'...")
            cmd = [
                nssm_path, "install", self.name, batch_path
            ]
            subprocess.run(cmd, check=True)
            
            # Cấu hình dịch vụ
            subprocess.run([nssm_path, "set", self.name, "Description", self.description], check=True)
            subprocess.run([nssm_path, "set", self.name, "AppDirectory", self.current_dir], check=True)
            subprocess.run([nssm_path, "set", self.name, "AppStdout", os.path.join(self.current_dir, "logs", f"{self.name}_service.log")], check=True)
            subprocess.run([nssm_path, "set", self.name, "AppStderr", os.path.join(self.current_dir, "logs", f"{self.name}_error.log")], check=True)
            
            # Cài đặt khởi động tự động
            if self.auto_start:
                subprocess.run([nssm_path, "set", self.name, "Start", "SERVICE_AUTO_START"], check=True)
            
            # Khởi động dịch vụ
            logger.info("Khởi động dịch vụ...")
            subprocess.run(["net", "start", self.name], check=True)
            
            logger.info(f"Dịch vụ Windows '{self.name}' đã được cài đặt thành công")
            logger.info(f"Bạn có thể quản lý dịch vụ qua Services.msc hoặc sử dụng các lệnh sau:")
            logger.info(f"- Dừng dịch vụ: net stop {self.name}")
            logger.info(f"- Khởi động dịch vụ: net start {self.name}")
            logger.info(f"- Gỡ bỏ dịch vụ: {nssm_path} remove {self.name} confirm")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Lỗi khi cài đặt dịch vụ Windows: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Lỗi: {str(e)}")
            return False
    
    def _check_admin_windows(self):
        """Kiểm tra quyền Administrator trên Windows"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    
    def _download_nssm(self):
        """Tải NSSM"""
        import urllib.request
        import zipfile
        
        logger.info("Tải NSSM...")
        
        # Tạo thư mục tools
        os.makedirs(os.path.join(self.current_dir, "tools"), exist_ok=True)
        
        # Tải NSSM
        nssm_url = "https://nssm.cc/release/nssm-2.24.zip"
        zip_path = os.path.join(self.current_dir, "tools", "nssm.zip")
        
        # Tải về
        urllib.request.urlretrieve(nssm_url, zip_path)
        
        # Giải nén
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(os.path.join(self.current_dir, "tools"))
        
        # Di chuyển file nssm.exe sang thư mục tools
        if os.path.exists(os.path.join(self.current_dir, "tools", "nssm-2.24", "win64", "nssm.exe")):
            os.rename(
                os.path.join(self.current_dir, "tools", "nssm-2.24", "win64", "nssm.exe"),
                os.path.join(self.current_dir, "tools", "nssm.exe")
            )
        
        # Xóa file zip và thư mục tạm
        os.remove(zip_path)
        
        logger.info("Đã tải và giải nén NSSM thành công")
    
    def setup_linux_service(self):
        """Cài đặt Linux systemd service"""
        try:
            # Kiểm tra quyền root
            if os.geteuid() != 0:
                logger.error("Bạn cần chạy với quyền root để cài đặt dịch vụ systemd")
                return False
            
            # Tạo service file
            service_path = f"/etc/systemd/system/{self.name}.service"
            
            # Chuẩn bị nội dung file service
            service_content = textwrap.dedent(f"""
            [Unit]
            Description={self.description}
            After=network.target
            
            [Service]
            Type=simple
            User={self.username}
            WorkingDirectory={self.current_dir}
            ExecStart={self.python_path} {os.path.join(self.current_dir, 'auto_restart_guardian.py')} {f'--risk-level {self.risk_level}' if self.risk_level else ''}
            Restart=always
            RestartSec=5
            StandardOutput=append:{os.path.join(self.current_dir, 'logs', f'{self.name}_service.log')}
            StandardError=append:{os.path.join(self.current_dir, 'logs', f'{self.name}_error.log')}
            
            [Install]
            WantedBy=multi-user.target
            """).strip()
            
            # Ghi file service
            with open(service_path, "w") as f:
                f.write(service_content)
            
            # Cấp quyền
            os.chmod(service_path, 0o644)
            
            # Reload systemd
            subprocess.run(["systemctl", "daemon-reload"], check=True)
            
            # Kích hoạt service
            if self.auto_start:
                subprocess.run(["systemctl", "enable", f"{self.name}.service"], check=True)
            
            # Khởi động service
            subprocess.run(["systemctl", "start", f"{self.name}.service"], check=True)
            
            logger.info(f"Dịch vụ Linux '{self.name}' đã được cài đặt thành công")
            logger.info(f"Bạn có thể quản lý dịch vụ qua các lệnh sau:")
            logger.info(f"- Xem trạng thái: systemctl status {self.name}")
            logger.info(f"- Dừng dịch vụ: systemctl stop {self.name}")
            logger.info(f"- Khởi động dịch vụ: systemctl start {self.name}")
            logger.info(f"- Gỡ bỏ dịch vụ: systemctl disable {self.name} && rm {service_path}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Lỗi khi cài đặt dịch vụ Linux: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Lỗi: {str(e)}")
            return False
    
    def setup_macos_service(self):
        """Cài đặt macOS LaunchDaemon"""
        try:
            # Kiểm tra quyền root
            if os.geteuid() != 0:
                logger.error("Bạn cần chạy với quyền root để cài đặt LaunchDaemon")
                return False
            
            # Tạo plist file
            plist_name = f"com.{self.name}.plist"
            plist_path = f"/Library/LaunchDaemons/{plist_name}"
            
            # Chuẩn bị nội dung file plist
            plist_content = textwrap.dedent(f"""
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
            <plist version="1.0">
            <dict>
                <key>Label</key>
                <string>com.{self.name}</string>
                <key>ProgramArguments</key>
                <array>
                    <string>{self.python_path}</string>
                    <string>{os.path.join(self.current_dir, 'auto_restart_guardian.py')}</string>
                    {f'<string>--risk-level</string><string>{self.risk_level}</string>' if self.risk_level else ''}
                </array>
                <key>WorkingDirectory</key>
                <string>{self.current_dir}</string>
                <key>RunAtLoad</key>
                <true/>
                <key>KeepAlive</key>
                <true/>
                <key>StandardOutPath</key>
                <string>{os.path.join(self.current_dir, 'logs', f'{self.name}_service.log')}</string>
                <key>StandardErrorPath</key>
                <string>{os.path.join(self.current_dir, 'logs', f'{self.name}_error.log')}</string>
                <key>UserName</key>
                <string>{self.username}</string>
            </dict>
            </plist>
            """).strip()
            
            # Ghi file plist
            with open(plist_path, "w") as f:
                f.write(plist_content)
            
            # Cấp quyền
            os.chmod(plist_path, 0o644)
            os.chown(plist_path, 0, 0)  # root:wheel
            
            # Tải và khởi động
            subprocess.run(["launchctl", "load", "-w", plist_path], check=True)
            
            logger.info(f"Dịch vụ macOS '{plist_name}' đã được cài đặt thành công")
            logger.info(f"Bạn có thể quản lý dịch vụ qua các lệnh sau:")
            logger.info(f"- Xem trạng thái: launchctl list | grep {self.name}")
            logger.info(f"- Dừng dịch vụ: launchctl unload {plist_path}")
            logger.info(f"- Khởi động dịch vụ: launchctl load -w {plist_path}")
            logger.info(f"- Gỡ bỏ dịch vụ: launchctl unload -w {plist_path} && rm {plist_path}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Lỗi khi cài đặt dịch vụ macOS: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Lỗi: {str(e)}")
            return False

def main():
    """Hàm main"""
    parser = argparse.ArgumentParser(description="Cài đặt dịch vụ chạy bot 24/7")
    parser.add_argument('--name', type=str, default="trading_bot", help="Tên dịch vụ")
    parser.add_argument('--description', type=str, default="Trading Bot 24/7 Service", help="Mô tả dịch vụ")
    parser.add_argument('--no-auto-start', action='store_true', help="Không tự động khởi động khi hệ thống khởi động")
    parser.add_argument('--risk-level', type=str, help="Mức độ rủi ro (10, 15, 20, 30)")
    
    args = parser.parse_args()
    
    # Hiển thị cảnh báo
    print("===== THIẾT LẬP DỊCH VỤ CHẠY BOT 24/7 =====")
    print(f"Hệ điều hành: {platform.system()}")
    print(f"Tên dịch vụ: {args.name}")
    print(f"Mô tả: {args.description}")
    print(f"Tự động khởi động: {'Không' if args.no_auto_start else 'Có'}")
    print(f"Mức độ rủi ro: {args.risk_level if args.risk_level else 'Mặc định'}")
    print("\nCẢNH BÁO: Quá trình này sẽ cài đặt dịch vụ hệ thống và có thể yêu cầu quyền quản trị viên.")
    
    # Xác nhận
    confirm = input("\nBạn có muốn tiếp tục? (y/n): ")
    if confirm.lower() != 'y':
        print("Đã hủy cài đặt.")
        return
    
    # Thiết lập dịch vụ
    service_setup = ServiceSetup(
        name=args.name,
        description=args.description,
        auto_start=not args.no_auto_start,
        risk_level=args.risk_level
    )
    
    # Cài đặt dịch vụ
    success = service_setup.setup_service()
    
    if success:
        print("\n===== CÀI ĐẶT THÀNH CÔNG =====")
        print("Bot của bạn sẽ chạy 24/7 và tự động khởi động lại sau khi gặp lỗi hoặc sau khi khởi động lại hệ thống.")
    else:
        print("\n===== CÀI ĐẶT THẤT BẠI =====")
        print("Vui lòng kiểm tra nhật ký lỗi và thử lại.")

if __name__ == "__main__":
    # Trên Windows, import ctypes
    if platform.system() == "Windows":
        import ctypes
    
    main()