#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Chạy tất cả các bài test cho hệ thống
"""

import os
import sys
import unittest
import logging
from datetime import datetime

# Thiết lập logging
os.makedirs("logs", exist_ok=True)
log_file = f"logs/test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('test_runner')

def run_all_tests():
    """Chạy tất cả các bài test và tạo báo cáo"""
    logger.info("===== Bắt đầu chạy bộ test toàn bộ hệ thống =====")
    
    # Tìm tất cả các file test trong thư mục test_scripts
    start_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Khám phá và chạy tất cả các test
    test_suite = unittest.defaultTestLoader.discover(start_dir, pattern="test_*.py")
    
    # Chạy các test với TextTestRunner
    runner = unittest.TextTestRunner(verbosity=2)
    test_results = runner.run(test_suite)
    
    # Tạo báo cáo
    logger.info("===== Kết quả các bài test =====")
    logger.info(f"Số lượng test: {test_results.testsRun}")
    logger.info(f"Số lỗi: {len(test_results.errors)}")
    logger.info(f"Số thất bại: {len(test_results.failures)}")
    
    # Hiển thị chi tiết lỗi và thất bại
    if test_results.errors:
        logger.error("===== Chi tiết các lỗi =====")
        for test, error in test_results.errors:
            logger.error(f"\n{test}: {error}")
    
    if test_results.failures:
        logger.error("===== Chi tiết các thất bại =====")
        for test, failure in test_results.failures:
            logger.error(f"\n{test}: {failure}")
    
    # Lưu báo cáo
    report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, "w") as f:
        f.write(f"===== Báo cáo kiểm thử hệ thống giao dịch =====\n")
        f.write(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Số lượng test chạy: {test_results.testsRun}\n")
        f.write(f"Số lượng test thành công: {test_results.testsRun - len(test_results.errors) - len(test_results.failures)}\n")
        f.write(f"Số lượng lỗi: {len(test_results.errors)}\n")
        f.write(f"Số lượng thất bại: {len(test_results.failures)}\n\n")
        
        if test_results.errors:
            f.write("===== Chi tiết các lỗi =====\n")
            for test, error in test_results.errors:
                f.write(f"\n{test}:\n{error}\n")
        
        if test_results.failures:
            f.write("===== Chi tiết các thất bại =====\n")
            for test, failure in test_results.failures:
                f.write(f"\n{test}:\n{failure}\n")
    
    logger.info(f"Đã lưu báo cáo chi tiết vào file: {report_file}")
    
    # Kiểm tra và hiển thị kết quả tổng quát
    if test_results.wasSuccessful():
        logger.info("===== Tất cả các bài test đều THÀNH CÔNG =====")
        return 0
    else:
        logger.error("===== Có những bài test THẤT BẠI hoặc LỖI =====")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())