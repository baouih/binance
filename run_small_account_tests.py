#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import argparse
import time
from test_small_account_trading import SmallAccountTester
from small_account_position_manager import SmallAccountManager

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("small_account_tests.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("small_account_tests")

def run_all_tests():
    """Chạy tất cả các bài kiểm tra"""
    logger.info("="*80)
    logger.info("BẮT ĐẦU KIỂM TRA CẤU HÌNH TÀI KHOẢN NHỎ")
    logger.info("="*80)
    
    # Bước 1: Kiểm tra cấu hình tài khoản
    logger.info("\n\n" + "="*80)
    logger.info("BƯỚC 1: KIỂM TRA CẤU HÌNH TÀI KHOẢN")
    logger.info("="*80)
    
    tester = SmallAccountTester()
    tester.run_test()
    
    time.sleep(2)  # Nghỉ giữa các bước để tránh rate limit
    
    # Bước 2: Kiểm tra quản lý vị thế
    logger.info("\n\n" + "="*80)
    logger.info("BƯỚC 2: KIỂM TRA QUẢN LÝ VỊ THẾ")
    logger.info("="*80)
    
    manager = SmallAccountManager()
    manager.run_tests()
    
    logger.info("\n\n" + "="*80)
    logger.info("ĐÃ HOÀN THÀNH TẤT CẢ CÁC BÀI KIỂM TRA")
    logger.info("="*80)

def parse_arguments():
    """Phân tích tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description='Kiểm tra giao dịch cho tài khoản nhỏ')
    parser.add_argument('--config-only', action='store_true', help='Chỉ kiểm tra cấu hình, không thử đặt lệnh')
    parser.add_argument('--position-only', action='store_true', help='Chỉ kiểm tra quản lý vị thế, không phân tích cấu hình')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    
    if args.config_only:
        logger.info("Chỉ chạy kiểm tra cấu hình...")
        tester = SmallAccountTester()
        tester.run_test()
    elif args.position_only:
        logger.info("Chỉ chạy kiểm tra quản lý vị thế...")
        manager = SmallAccountManager()
        manager.run_tests()
    else:
        run_all_tests()