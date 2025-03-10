#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Setup Dependencies - Cài đặt tự động các thư viện cần thiết
"""

import os
import sys
import subprocess
import platform
import logging
from pathlib import Path

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('setup_dependencies')

# Danh sách các thư viện cần thiết
REQUIRED_PACKAGES = [
    # Giao diện đồ họa
    "PyQt5>=5.15.4",
    "pyqtgraph>=0.12.3",
    
    # Xử lý dữ liệu
    "numpy>=1.21.0",
    "pandas>=1.3.0",
    "matplotlib>=3.4.2",
    
    # Giao dịch tiền điện tử
    "ccxt>=1.60.0",
    "python-binance>=1.0.16",
    "binance-connector>=1.17.0",
    
    # Machine Learning
    "scikit-learn>=1.0.0",
    "tensorflow>=2.8.0",
    "joblib>=1.1.0",
    
    # Web và API
    "flask>=2.0.1",
    "flask-login>=0.5.0",
    "flask-sqlalchemy>=2.5.1",
    "flask-socketio>=5.1.1",
    "gunicorn>=20.1.0",
    
    # Khác
    "schedule>=1.1.0",
    "requests>=2.26.0",
    "python-dotenv>=0.19.0"
]

def check_python_version():
    """Kiểm tra phiên bản Python"""
    major, minor, _ = platform.python_version_tuple()
    version = f"{major}.{minor}"
    
    if int(major) < 3 or (int(major) == 3 and int(minor) < 9):
        logger.warning(f"Phiên bản Python hiện tại ({version}) thấp hơn khuyến nghị (3.9+)")
        logger.warning("Một số thư viện có thể không hoạt động đúng")
        
        if input("Bạn có muốn tiếp tục? (y/n): ").lower() != 'y':
            logger.info("Đã hủy quá trình cài đặt")
            sys.exit(0)
    else:
        logger.info(f"Phiên bản Python: {version} (OK)")

def install_package(package):
    """Cài đặt một gói thư viện"""
    logger.info(f"Đang cài đặt {package}...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        logger.error(f"Không thể cài đặt {package}")
        return False

def setup_virtual_env():
    """Thiết lập môi trường ảo nếu cần"""
    if os.path.exists("venv") or os.path.exists(".venv"):
        logger.info("Đã phát hiện môi trường ảo")
        return
    
    create_venv = input("Bạn có muốn tạo môi trường ảo (virtualenv)? (y/n): ")
    if create_venv.lower() == 'y':
        try:
            logger.info("Đang tạo môi trường ảo...")
            subprocess.check_call([sys.executable, "-m", "venv", "venv"])
            
            # Hiển thị hướng dẫn kích hoạt
            if platform.system() == "Windows":
                logger.info("Kích hoạt môi trường ảo với lệnh: .\\venv\\Scripts\\activate")
            else:
                logger.info("Kích hoạt môi trường ảo với lệnh: source venv/bin/activate")
                
            logger.info("Vui lòng kích hoạt môi trường ảo và chạy lại script này")
            sys.exit(0)
            
        except subprocess.CalledProcessError:
            logger.error("Không thể tạo môi trường ảo")
            logger.info("Tiếp tục cài đặt vào môi trường Python toàn cục")

def install_requirements():
    """Cài đặt tất cả thư viện cần thiết"""
    # Cập nhật pip
    logger.info("Đang cập nhật pip...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    
    # Cài đặt các thư viện
    success = True
    for package in REQUIRED_PACKAGES:
        if not install_package(package):
            success = False
    
    return success

def create_test_file():
    """Tạo file kiểm tra để xác minh cài đặt"""
    test_file = "check_installation.py"
    
    with open(test_file, "w") as f:
        f.write("""#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import importlib
import platform

def check_import(module_name):
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, "__version__", "Unknown")
        return True, version
    except ImportError:
        return False, None

# Danh sách các module cần kiểm tra
modules = [
    "PyQt5", "pyqtgraph", "numpy", "pandas", "matplotlib", 
    "ccxt", "binance", "tensorflow", "sklearn", "joblib",
    "flask", "flask_login", "flask_sqlalchemy", "flask_socketio",
    "requests", "schedule", "dotenv"
]

print("===== KIỂM TRA CÀI ĐẶT =====")
print(f"Python version: {platform.python_version()}")

all_success = True
for module in modules:
    success, version = check_import(module)
    status = "✓" if success else "✗"
    version_str = f"(v{version})" if version != "Unknown" and version else ""
    
    print(f"{status} {module} {version_str}")
    
    if not success:
        all_success = False

print("\\n===== KẾT QUẢ =====")
if all_success:
    print("Tất cả thư viện đã được cài đặt đúng!")
    print("Bạn có thể chạy bot bằng lệnh: python bot_gui.py")
else:
    print("Một số thư viện chưa được cài đặt đúng")
    print("Vui lòng chạy lại: python setup_dependencies.py")

input("Nhấn Enter để tiếp tục...")
""")
    
    logger.info(f"Đã tạo file kiểm tra: {test_file}")
    return test_file

def main():
    """Hàm main"""
    print("===== CÀI ĐẶT THƯ VIỆN PHỤ THUỘC =====")
    print("Script này sẽ cài đặt tất cả thư viện cần thiết để chạy Trading Bot")
    
    # Kiểm tra phiên bản Python
    check_python_version()
    
    # Thiết lập môi trường ảo
    setup_virtual_env()
    
    # Cài đặt thư viện
    print("\nBắt đầu cài đặt thư viện...")
    success = install_requirements()
    
    if success:
        print("\n===== CÀI ĐẶT HOÀN TẤT =====")
        print("Tất cả thư viện đã được cài đặt thành công!")
        
        # Tạo file kiểm tra
        test_file = create_test_file()
        
        # Chạy kiểm tra
        print("\nĐang kiểm tra cài đặt...")
        subprocess.call([sys.executable, test_file])
        
        print("\nBạn có thể chạy bot bằng lệnh:")
        print("  Giao diện đồ họa: python bot_gui.py")
        print("  Chế độ 24/7:     python auto_restart_guardian.py --risk-level 20")
        
    else:
        print("\n===== CÀI ĐẶT KHÔNG HOÀN TẤT =====")
        print("Một số thư viện không thể cài đặt")
        print("Vui lòng kiểm tra lỗi và thử lại")
    
    input("\nNhấn Enter để kết thúc...")

if __name__ == "__main__":
    main()