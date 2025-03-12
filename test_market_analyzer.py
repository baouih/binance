#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script cho MarketAnalyzer
"""

import os
import sys
import logging
import json

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_market_analyzer")

def main():
    """Hàm chính để test MarketAnalyzer"""
    try:
        # Import MarketAnalyzer
        from market_analyzer import MarketAnalyzer
        logger.info("Đã import thành công MarketAnalyzer")
        
        # Hiển thị thông tin môi trường
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Có API key: {'Có' if os.environ.get('BINANCE_TESTNET_API_KEY') else 'Không'}")
        logger.info(f"Có API secret: {'Có' if os.environ.get('BINANCE_TESTNET_API_SECRET') else 'Không'}")
        
        # Khởi tạo MarketAnalyzer
        analyzer = MarketAnalyzer(testnet=True)
        logger.info("Đã khởi tạo MarketAnalyzer")
        
        # Hiển thị thông tin về các phương thức
        logger.info(f"Các phương thức của MarketAnalyzer: {[method for method in dir(analyzer) if not method.startswith('_')]}")
        
        # Kiểm tra phương thức scan_trading_opportunities
        if hasattr(analyzer, 'scan_trading_opportunities'):
            logger.info("Phương thức scan_trading_opportunities tồn tại")
            
            # Thực hiện quét cơ hội giao dịch
            logger.info("Bắt đầu quét cơ hội giao dịch...")
            opportunities = analyzer.scan_trading_opportunities()
            
            # Hiển thị kết quả
            logger.info(f"Kết quả quét cơ hội: {json.dumps(opportunities, indent=2)}")
            
            if opportunities and 'status' in opportunities:
                logger.info(f"Trạng thái quét: {opportunities['status']}")
            
            if opportunities and 'opportunities' in opportunities:
                logger.info(f"Số lượng cơ hội: {len(opportunities['opportunities'])}")
                
                # Hiển thị chi tiết từng cơ hội
                for i, opp in enumerate(opportunities['opportunities']):
                    logger.info(f"Cơ hội #{i+1}: {json.dumps(opp, indent=2)}")
            else:
                logger.info("Không tìm thấy cơ hội giao dịch")
        else:
            logger.error("Phương thức scan_trading_opportunities không tồn tại")
            logger.info(f"Các phương thức có sẵn: {[method for method in dir(analyzer) if not method.startswith('_')]}")
        
    except Exception as e:
        logger.error(f"Lỗi khi chạy test: {e}", exc_info=True)

if __name__ == "__main__":
    main()