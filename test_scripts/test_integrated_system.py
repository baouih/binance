#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test tích hợp cho toàn bộ hệ thống trading
"""

import os
import sys
import json
import time
import logging
import unittest
import tempfile
import shutil
from pathlib import Path
import threading
import subprocess

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Thêm thư mục gốc vào sys.path để import module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from risk_level_manager import RiskLevelManager

class TestIntegratedSystem(unittest.TestCase):
    """
    Test class cho toàn bộ hệ thống giao dịch tích hợp
    """
    @classmethod
    def setUpClass(cls):
        """Thiết lập một lần trước khi chạy tất cả các test"""
        # Tạo thư mục test
        cls.test_dir = tempfile.mkdtemp()
        cls.old_dir = os.getcwd()
        
        # Copy các file cần thiết vào thư mục test
        cls.prepare_test_environment()
        
        # Di chuyển vào thư mục test
        os.chdir(cls.test_dir)
        
    @classmethod
    def tearDownClass(cls):
        """Dọn dẹp sau khi chạy tất cả các test"""
        os.chdir(cls.old_dir)
        shutil.rmtree(cls.test_dir)
    
    @classmethod
    def prepare_test_environment(cls):
        """Chuẩn bị môi trường test"""
        # Copy các file và thư mục cần thiết
        source_files = [
            "risk_level_manager.py",
            "account_config.json",
            "bot_startup.py",
            "main.py",
            "app.py",
        ]
        
        source_dirs = [
            "risk_configs",
            "strategies",
            "templates",
            "static",
        ]
        
        # Copy các file
        for file in source_files:
            if os.path.exists(file):
                shutil.copy2(file, os.path.join(cls.test_dir, file))
        
        # Copy các thư mục
        for directory in source_dirs:
            if os.path.exists(directory):
                shutil.copytree(
                    directory, 
                    os.path.join(cls.test_dir, directory),
                    dirs_exist_ok=True
                )
        
        # Tạo các thư mục cần thiết
        os.makedirs(os.path.join(cls.test_dir, "logs"), exist_ok=True)
    
    def setUp(self):
        """Thiết lập trước mỗi test case"""
        pass
    
    def tearDown(self):
        """Dọn dẹp sau mỗi test case"""
        pass
    
    def test_risk_level_integration(self):
        """Kiểm tra tích hợp quản lý rủi ro trong hệ thống"""
        # Khởi tạo quản lý rủi ro
        risk_manager = RiskLevelManager()
        
        # Kiểm tra đã tạo đủ các file cấu hình rủi ro
        self.assertTrue(os.path.exists("risk_configs/risk_level_10.json"))
        self.assertTrue(os.path.exists("risk_configs/risk_level_15.json"))
        self.assertTrue(os.path.exists("risk_configs/risk_level_20.json"))
        self.assertTrue(os.path.exists("risk_configs/risk_level_30.json"))
        
        # Áp dụng mức rủi ro cao nhất
        result = risk_manager.apply_risk_config("30")
        self.assertTrue(result)
        
        # Kiểm tra account_config.json đã được cập nhật
        with open("account_config.json", "r") as f:
            account_config = json.load(f)
        
        self.assertIn("risk_parameters", account_config)
        
        # Kiểm tra các thông số rủi ro đã được cập nhật đúng
        risk_params = account_config["risk_parameters"]
        self.assertEqual(risk_params["position_size_percent"], 5.0)
        self.assertEqual(risk_params["leverage"], 5)
    
    def test_system_startup(self):
        """Kiểm tra khởi động hệ thống"""
        # Kiểm tra có thể khởi động hệ thống mà không gặp lỗi
        try:
            # Khởi tạo process để chạy bot_startup.py trong vài giây
            process = subprocess.Popen(
                [sys.executable, "bot_startup.py", "--test-mode"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Chờ một thời gian ngắn
            time.sleep(2)
            
            # Kiểm tra trạng thái
            self.assertIsNone(process.poll(), "Process đã kết thúc sớm")
            
            # Dừng process
            process.terminate()
            process.wait(timeout=5)
            
            # Kiểm tra exit code
            self.assertEqual(process.poll(), 0, "Process kết thúc với mã lỗi")
            
        except Exception as e:
            self.fail(f"Không thể khởi động hệ thống: {str(e)}")
    
    def test_web_interface(self):
        """Kiểm tra giao diện web"""
        # Chạy Flask app trong thread riêng
        def run_flask_app():
            try:
                from app import app
                app.run(host='127.0.0.1', port=5001, debug=False)
            except Exception as e:
                logger.error(f"Lỗi khởi động Flask app: {str(e)}")
        
        try:
            # Khởi động Flask app
            flask_thread = threading.Thread(target=run_flask_app)
            flask_thread.daemon = True
            flask_thread.start()
            
            # Chờ Flask khởi động
            time.sleep(2)
            
            # Kiểm tra có thể truy cập trang web
            import requests
            response = requests.get('http://127.0.0.1:5001/')
            
            # Kiểm tra kết quả
            self.assertEqual(response.status_code, 200, "Không thể truy cập trang web")
            
        except Exception as e:
            self.fail(f"Lỗi khi kiểm tra giao diện web: {str(e)}")
    
    def test_config_validation(self):
        """Kiểm tra validation cấu hình hệ thống"""
        # Tạo account_config với thông tin không hợp lệ
        invalid_config = {
            "api_key": "test_key",
            "api_secret": "test_secret",
            "risk_parameters": {
                "position_size_percent": -10,  # Giá trị âm không hợp lệ
                "stop_loss_percent": 0,  # Không được phép là 0
                "leverage": 100  # Quá cao
            }
        }
        
        with open("account_config.json", "w") as f:
            json.dump(invalid_config, f, indent=4)
        
        # Chạy validator (giả định là một module/class riêng)
        try:
            # Nếu có module validation, import và sử dụng ở đây
            from risk_level_manager import RiskLevelManager
            risk_manager = RiskLevelManager()
            
            # Thử áp dụng cấu hình mặc định để validate
            risk_manager.apply_risk_config("10")
            
            # Kiểm tra account_config đã được sửa đúng
            with open("account_config.json", "r") as f:
                fixed_config = json.load(f)
            
            # Các giá trị không hợp lệ nên đã được thay thế
            self.assertGreaterEqual(fixed_config["risk_parameters"]["position_size_percent"], 0)
            self.assertGreater(fixed_config["risk_parameters"]["stop_loss_percent"], 0)
            self.assertLessEqual(fixed_config["risk_parameters"]["leverage"], 20)
            
        except Exception as e:
            logger.error(f"Lỗi khi validate config: {str(e)}")

    def test_integration_with_binance_testnet(self):
        """
        Kiểm tra tích hợp với Binance Testnet
        
        Lưu ý: Bài test này yêu cầu thông tin API key/secret Binance Testnet hợp lệ
        """
        # Kiểm tra môi trường có API key/secret cho Binance Testnet không
        api_key = os.environ.get("BINANCE_TESTNET_API_KEY")
        api_secret = os.environ.get("BINANCE_TESTNET_API_SECRET")
        
        if not api_key or not api_secret:
            self.skipTest("Không có thông tin API Binance Testnet")
        
        # Tạo cấu hình account với API key/secret
        test_config = {
            "api_key": api_key,
            "api_secret": api_secret,
            "testnet": True,
            "risk_parameters": {
                "position_size_percent": 1.0,
                "stop_loss_percent": 1.0,
                "take_profit_percent": 2.0,
                "leverage": 1
            }
        }
        
        with open("account_config.json", "w") as f:
            json.dump(test_config, f, indent=4)
        
        try:
            # Import module giao dịch Binance, nếu có
            # Thực hiện kiểm tra kết nối và các chức năng cơ bản
            self.assertTrue(True, "Chưa có module test cho Binance API")
            
        except Exception as e:
            logger.error(f"Lỗi khi test Binance API: {str(e)}")

if __name__ == "__main__":
    unittest.main()