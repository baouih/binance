#!/usr/bin/env python3
"""
Script sửa lỗi và khởi động lại toàn bộ hệ thống
"""

import os
import sys
import json
import time
import logging
import subprocess
import datetime
from typing import Dict, List, Any

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("fix_and_restart")

class SystemRestarter:
    """Lớp khởi động lại và kiểm tra hệ thống"""
    
    def __init__(self):
        """Khởi tạo restarter"""
        self.processes = {}
        self.commands = {
            'trailing_stop': ['python', 'position_trailing_stop.py', '--interval', '30'],
            'market_updater': ['python', 'auto_start_market_updater.py'],
            'notification_test': ['python', 'enhanced_notifications.py']
        }
        self.pid_files = {
            'trailing_stop': 'trailing_stop.pid',
            'market_updater': 'market_updater.pid'
        }
        self.log_files = {
            'trailing_stop': 'trailing_stop.log',
            'market_updater': 'market_updater.log',
            'notification_test': 'notification_test.log'
        }
    
    def fix_active_positions(self) -> bool:
        """
        Sửa lỗi file active_positions.json
        
        Returns:
            bool: True nếu sửa thành công, False nếu thất bại
        """
        try:
            # Tạo bản sao lưu của file hiện tại nếu có
            if os.path.exists('active_positions.json'):
                backup_path = f'active_positions_backup_{int(time.time())}.json'
                logger.info(f"Tạo bản sao lưu của active_positions.json tại {backup_path}")
                
                try:
                    with open('active_positions.json', 'r') as src:
                        with open(backup_path, 'w') as dest:
                            dest.write(src.read())
                except Exception as e:
                    logger.error(f"Lỗi khi tạo bản sao lưu: {str(e)}")
            
            # Tạo file mới với nội dung trống
            with open('active_positions.json', 'w') as f:
                f.write('{}')
            
            logger.info("Đã xóa và tạo mới file active_positions.json")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi sửa file active_positions.json: {str(e)}")
            return False
    
    def stop_services(self) -> Dict[str, bool]:
        """
        Dừng tất cả các dịch vụ đang chạy
        
        Returns:
            Dict[str, bool]: Kết quả dừng dịch vụ
        """
        results = {}
        
        for service, pid_file in self.pid_files.items():
            try:
                if os.path.exists(pid_file):
                    with open(pid_file, 'r') as f:
                        pid = int(f.read().strip())
                    
                    # Gửi tín hiệu dừng
                    logger.info(f"Đang dừng dịch vụ {service} với PID {pid}")
                    os.kill(pid, 15)  # SIGTERM
                    
                    # Đợi tối đa 5 giây
                    for _ in range(10):
                        try:
                            os.kill(pid, 0)  # Kiểm tra tiến trình còn tồn tại không
                            time.sleep(0.5)
                        except OSError:
                            break
                    
                    # Kiểm tra nếu tiến trình vẫn chạy
                    try:
                        os.kill(pid, 0)
                        logger.warning(f"Tiến trình {pid} không dừng, đang buộc dừng...")
                        os.kill(pid, 9)  # SIGKILL
                    except OSError:
                        pass
                    
                    # Xóa file PID
                    os.remove(pid_file)
                    
                    results[service] = True
                    logger.info(f"Đã dừng dịch vụ {service}")
                else:
                    logger.info(f"Không tìm thấy file PID cho dịch vụ {service}")
                    results[service] = True
            except Exception as e:
                logger.error(f"Lỗi khi dừng dịch vụ {service}: {str(e)}")
                results[service] = False
        
        return results
    
    def start_services(self) -> Dict[str, Any]:
        """
        Khởi động lại tất cả các dịch vụ
        
        Returns:
            Dict[str, Any]: Thông tin về các dịch vụ đã khởi động
        """
        results = {}
        
        for service, command in self.commands.items():
            try:
                log_file_path = self.log_files.get(service, f"{service}.log")
                
                # Mở file log để ghi
                with open(log_file_path, 'a') as log_file:
                    # Ghi thông tin khởi động
                    log_file.write(f"\n\n--- NEW SERVICE START: {datetime.datetime.now()} ---\n\n")
                    
                    # Khởi động dịch vụ
                    logger.info(f"Đang khởi động dịch vụ {service}: {' '.join(command)}")
                    
                    # Chạy trong nền
                    process = subprocess.Popen(
                        command,
                        stdout=log_file,
                        stderr=log_file,
                        start_new_session=True
                    )
                    
                    # Lưu thông tin tiến trình
                    self.processes[service] = process
                    
                    # Lưu PID vào file nếu cần
                    if service in self.pid_files:
                        with open(self.pid_files[service], 'w') as pid_file:
                            pid_file.write(str(process.pid))
                    
                    results[service] = {
                        'pid': process.pid,
                        'command': ' '.join(command),
                        'log_file': log_file_path,
                        'start_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    logger.info(f"Đã khởi động dịch vụ {service} với PID {process.pid}")
                    
                    # Đợi 1 giây trước khi khởi động dịch vụ tiếp theo
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Lỗi khi khởi động dịch vụ {service}: {str(e)}")
                results[service] = {'error': str(e)}
        
        return results
    
    def check_services(self) -> Dict[str, bool]:
        """
        Kiểm tra trạng thái của các dịch vụ
        
        Returns:
            Dict[str, bool]: Trạng thái các dịch vụ
        """
        results = {}
        
        for service, pid_file in self.pid_files.items():
            try:
                if os.path.exists(pid_file):
                    with open(pid_file, 'r') as f:
                        pid = int(f.read().strip())
                    
                    # Kiểm tra tiến trình
                    try:
                        os.kill(pid, 0)  # Chỉ kiểm tra, không gửi tín hiệu thực sự
                        results[service] = True
                        logger.info(f"Dịch vụ {service} đang chạy với PID {pid}")
                    except OSError:
                        results[service] = False
                        logger.warning(f"Dịch vụ {service} không chạy với PID {pid}")
                else:
                    results[service] = False
                    logger.warning(f"Không tìm thấy file PID cho dịch vụ {service}")
            except Exception as e:
                logger.error(f"Lỗi khi kiểm tra dịch vụ {service}: {str(e)}")
                results[service] = False
        
        return results
    
    def create_test_position(self) -> bool:
        """
        Tạo vị thế thử nghiệm
        
        Returns:
            bool: True nếu tạo thành công, False nếu thất bại
        """
        try:
            # Kiểm tra nếu file create_test_position.py tồn tại
            if not os.path.exists('create_test_position.py'):
                logger.error("Không tìm thấy file create_test_position.py")
                return False
            
            # Chạy script tạo vị thế
            logger.info("Đang tạo vị thế thử nghiệm...")
            
            with open('create_test_position.log', 'a') as log_file:
                log_file.write(f"\n\n--- NEW TEST POSITION: {datetime.datetime.now()} ---\n\n")
                
                process = subprocess.Popen(
                    [sys.executable, 'create_test_position.py'],
                    stdout=log_file,
                    stderr=log_file
                )
                
                # Đợi tiến trình hoàn thành
                process.wait()
                
                if process.returncode == 0:
                    logger.info("Đã tạo vị thế thử nghiệm thành công")
                    return True
                else:
                    logger.error(f"Lỗi khi tạo vị thế thử nghiệm, mã lỗi: {process.returncode}")
                    return False
        except Exception as e:
            logger.error(f"Lỗi khi tạo vị thế thử nghiệm: {str(e)}")
            return False
    
    def fix_and_restart_all(self) -> Dict[str, Any]:
        """
        Sửa lỗi và khởi động lại toàn bộ hệ thống
        
        Returns:
            Dict[str, Any]: Kết quả sửa lỗi và khởi động lại
        """
        results = {}
        
        # 1. Sửa lỗi file active_positions.json
        logger.info("Bước 1: Sửa lỗi file active_positions.json")
        results['fix_active_positions'] = self.fix_active_positions()
        
        # 2. Dừng tất cả các dịch vụ đang chạy
        logger.info("Bước 2: Dừng tất cả các dịch vụ đang chạy")
        results['stop_services'] = self.stop_services()
        
        # 3. Khởi động lại các dịch vụ
        logger.info("Bước 3: Khởi động lại các dịch vụ")
        results['start_services'] = self.start_services()
        
        # 4. Đợi các dịch vụ khởi động
        logger.info("Bước 4: Đợi các dịch vụ khởi động (5 giây)")
        time.sleep(5)
        
        # 5. Kiểm tra trạng thái các dịch vụ
        logger.info("Bước 5: Kiểm tra trạng thái các dịch vụ")
        results['check_services'] = self.check_services()
        
        # 6. Tạo vị thế thử nghiệm
        logger.info("Bước 6: Tạo vị thế thử nghiệm")
        results['create_test_position'] = self.create_test_position()
        
        return results

def main():
    """Hàm chính"""
    print("\n=== BẮT ĐẦU SỬA LỖI VÀ KHỞI ĐỘNG LẠI HỆ THỐNG ===\n")
    
    restarter = SystemRestarter()
    results = restarter.fix_and_restart_all()
    
    print("\n=== KẾT QUẢ SỬA LỖI VÀ KHỞI ĐỘNG LẠI ===\n")
    
    # Hiển thị kết quả
    for step, result in results.items():
        if isinstance(result, dict):
            print(f"- {step}:")
            for key, value in result.items():
                print(f"  + {key}: {value}")
        else:
            print(f"- {step}: {result}")
    
    print("\n=== HOÀN THÀNH ===\n")
    print("Kiểm tra log để biết thêm chi tiết.")

if __name__ == "__main__":
    main()