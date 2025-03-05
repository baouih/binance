#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script chạy cập nhật dữ liệu thị trường cho tất cả các cặp tiền
"""

import os
import sys
import json
import time
import logging
from datetime import datetime

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("full_market_update.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("full_market_update")

def get_symbols_from_config():
    """Lấy danh sách các cặp giao dịch từ cấu hình"""
    try:
        with open('account_config.json', 'r') as f:
            config = json.load(f)
            return config.get('symbols', ['BTCUSDT', 'ETHUSDT'])
    except Exception as e:
        logger.error(f"Lỗi khi đọc file cấu hình: {e}")
        return ['BTCUSDT', 'ETHUSDT']

def update_market_data_for_symbol(symbol):
    """Cập nhật dữ liệu thị trường cho một cặp tiền"""
    try:
        logger.info(f"Đang cập nhật dữ liệu thị trường cho {symbol}")
        start_time = time.time()
        
        # Tạo command với tham số đầu vào là 1 symbol
        cmd = f"python update_single_symbol.py {symbol}"
        exit_code = os.system(cmd)
        
        duration = time.time() - start_time
        if exit_code == 0:
            logger.info(f"Cập nhật dữ liệu thị trường cho {symbol} thành công ({duration:.2f}s)")
            return True
        else:
            logger.error(f"Cập nhật dữ liệu thị trường cho {symbol} thất bại với mã lỗi {exit_code} ({duration:.2f}s)")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật dữ liệu cho {symbol}: {e}")
        return False

def create_single_symbol_updater():
    """Tạo script cập nhật cho một symbol"""
    script_content = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import logging
from market_data_updater import MarketDataUpdater

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("update_single_symbol.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("update_single_symbol")

def main():
    """Hàm chính"""
    if len(sys.argv) < 2:
        logger.error("Thiếu tham số: cần chỉ định symbol")
        return 1
        
    symbol = sys.argv[1]
    logger.info(f"Bắt đầu cập nhật dữ liệu thị trường cho {symbol}")
    
    updater = MarketDataUpdater()
    success = updater.update_market_analysis(symbol, timeframe='1h')
    
    if success:
        logger.info(f"Cập nhật thành công dữ liệu thị trường cho {symbol}")
        return 0
    else:
        logger.error(f"Cập nhật thất bại dữ liệu thị trường cho {symbol}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
"""
    
    try:
        with open('update_single_symbol.py', 'w') as f:
            f.write(script_content)
        os.chmod('update_single_symbol.py', 0o755)  # Đặt quyền thực thi
        logger.info("Đã tạo script update_single_symbol.py")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi tạo script update_single_symbol.py: {e}")
        return False

def main():
    """Hàm chính"""
    try:
        logger.info("Bắt đầu cập nhật dữ liệu thị trường cho tất cả các cặp tiền")
        
        # Tạo script cập nhật cho 1 symbol
        create_single_symbol_updater()
        
        # Lấy danh sách các cặp giao dịch
        symbols = get_symbols_from_config()
        logger.info(f"Số lượng cặp giao dịch: {len(symbols)}")
        
        # Cập nhật từng cặp một
        results = {}
        for symbol in symbols:
            success = update_market_data_for_symbol(symbol)
            results[symbol] = success
            # Nghỉ giữa các lần gọi API để tránh rate limit
            time.sleep(2)
        
        # Thống kê kết quả
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"Tóm tắt: Cập nhật {success_count}/{len(results)} cặp giao dịch thành công")
        
        # Lưu kết quả
        with open('full_market_update_results.json', 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "results": {k: "success" if v else "failed" for k, v in results.items()},
                "success_count": success_count,
                "total_count": len(results)
            }, f, indent=2)
        
        logger.info("Hoàn thành cập nhật dữ liệu thị trường cho tất cả các cặp tiền")
        return 0
    
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật dữ liệu thị trường: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())