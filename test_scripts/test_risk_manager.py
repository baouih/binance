#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test cho Risk Level Manager
"""

import os
import sys
import json
import unittest
import tempfile
import shutil
from pathlib import Path

# Thêm thư mục gốc vào sys.path để import module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from risk_level_manager import RiskLevelManager

class TestRiskLevelManager(unittest.TestCase):
    """
    Test class cho RiskLevelManager
    """
    def setUp(self):
        """Thiết lập trước mỗi test case"""
        # Tạo thư mục tạm cho test
        self.test_dir = tempfile.mkdtemp()
        self.old_pwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Tạo thư mục risk_configs
        os.makedirs("risk_configs", exist_ok=True)
        
        # Khởi tạo RiskLevelManager
        self.risk_manager = RiskLevelManager()
    
    def tearDown(self):
        """Dọn dẹp sau mỗi test case"""
        os.chdir(self.old_pwd)
        shutil.rmtree(self.test_dir)
    
    def test_init(self):
        """Test constructor"""
        self.assertEqual(self.risk_manager.current_risk_level, "10")
        self.assertTrue(os.path.exists("risk_configs/risk_level_10.json"))
        self.assertTrue(os.path.exists("risk_configs/risk_level_15.json"))
        self.assertTrue(os.path.exists("risk_configs/risk_level_20.json"))
        self.assertTrue(os.path.exists("risk_configs/risk_level_30.json"))
        self.assertTrue(os.path.exists("risk_configs/advanced_risk_config.json"))
    
    def test_get_current_risk_level(self):
        """Test get_current_risk_level"""
        self.assertEqual(self.risk_manager.get_current_risk_level(), "10")
    
    def test_get_risk_config(self):
        """Test get_risk_config"""
        # Kiểm tra có thể lấy cấu hình cho các mức rủi ro khác nhau
        risk_10_config = self.risk_manager.get_risk_config("10")
        self.assertEqual(risk_10_config["position_size_percent"], 1.0)
        
        risk_30_config = self.risk_manager.get_risk_config("30")
        self.assertEqual(risk_30_config["position_size_percent"], 5.0)
        
        # Kiểm tra trả về cấu hình mặc định khi mức rủi ro không hợp lệ
        default_config = self.risk_manager.get_risk_config("invalid")
        self.assertEqual(default_config, {})
    
    def test_apply_risk_config(self):
        """Test apply_risk_config"""
        # Tạo file account_config.json để test
        with open("account_config.json", "w") as f:
            json.dump({"api_key": "test"}, f)
        
        # Áp dụng cấu hình mức rủi ro hợp lệ
        result = self.risk_manager.apply_risk_config("20")
        self.assertTrue(result)
        self.assertEqual(self.risk_manager.current_risk_level, "20")
        
        # Kiểm tra account_config.json đã được cập nhật
        with open("account_config.json", "r") as f:
            account_config = json.load(f)
        
        self.assertIn("risk_parameters", account_config)
        self.assertEqual(account_config["risk_parameters"]["position_size_percent"], 3.0)
        
        # Thử áp dụng mức rủi ro không hợp lệ
        result = self.risk_manager.apply_risk_config("invalid")
        self.assertFalse(result)
        
    def test_get_risk_level_description(self):
        """Test get_risk_level_description"""
        # Kiểm tra mô tả cho các mức rủi ro khác nhau
        risk_10_desc = self.risk_manager.get_risk_level_description("10")
        self.assertEqual(risk_10_desc["name"], "Bảo Thủ (10%)")
        
        risk_30_desc = self.risk_manager.get_risk_level_description("30")
        self.assertEqual(risk_30_desc["name"], "Mạo Hiểm (30%)")
        
        # Kiểm tra với mức rủi ro không tồn tại
        invalid_desc = self.risk_manager.get_risk_level_description("invalid")
        self.assertEqual(invalid_desc["name"], "Bảo Thủ (10%)")  # Nên trả về mô tả mặc định
    
    def test_create_custom_risk_level(self):
        """Test create_custom_risk_level"""
        # Tạo mức rủi ro tùy chỉnh
        custom_config = {
            "position_size_percent": 2.5,
            "stop_loss_percent": 2.5,
            "take_profit_percent": 5.0,
            "leverage": 2
        }
        
        result = self.risk_manager.create_custom_risk_level("custom", custom_config)
        self.assertTrue(result)
        
        # Kiểm tra file đã được tạo
        self.assertTrue(os.path.exists("risk_configs/risk_level_custom.json"))
        
        # Kiểm tra nội dung file
        with open("risk_configs/risk_level_custom.json", "r") as f:
            saved_config = json.load(f)
        
        self.assertEqual(saved_config["position_size_percent"], 2.5)
        self.assertEqual(saved_config["stop_loss_percent"], 2.5)
        
        # Kiểm tra đã được thêm vào danh sách cấu hình có sẵn
        self.assertIn("custom", self.risk_manager.risk_configs)
    
    def test_get_all_risk_levels(self):
        """Test get_all_risk_levels"""
        # Lấy tất cả mức rủi ro
        all_levels = self.risk_manager.get_all_risk_levels()
        
        # Kiểm tra có các mức rủi ro mặc định
        self.assertIn("10", all_levels)
        self.assertIn("15", all_levels)
        self.assertIn("20", all_levels)
        self.assertIn("30", all_levels)
        
        # Kiểm tra mỗi mức có thông tin đầy đủ
        for level, info in all_levels.items():
            self.assertIn("description", info)
            self.assertIn("config", info)

if __name__ == "__main__":
    unittest.main()