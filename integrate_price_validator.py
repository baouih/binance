#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script tích hợp price_validator và hệ thống giao dịch
"""

import os
import sys
import logging
import json
import time
from typing import Dict, Any, Optional, List

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("integrate_price_validator.log")
    ]
)
logger = logging.getLogger(__name__)

def create_integration_file():
    """Tạo integration file để tích hợp với hệ thống hiện có"""
    
    integration_code = """#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Module kết nối price_validator với hệ thống giao dịch chính
'''

import logging
import importlib
import inspect
import sys
from typing import Dict, Any, Optional, List, Tuple, Union

logger = logging.getLogger(__name__)

class PriceValidationIntegrator:
    '''
    Lớp tích hợp hệ thống xác thực giá vào hệ thống giao dịch chính.
    Được thiết kế để có thể hoạt động kể cả khi các module xác thực giá không tồn tại.
    '''
    
    def __init__(self):
        self.price_validator_available = False
        self.price_monitor_available = False
        self.price_cache_available = False
        
        # Thử import các module
        try:
            import price_validator
            self.price_validator = price_validator
            self.price_validator_available = True
            logger.info("Đã tìm thấy và tích hợp price_validator")
        except ImportError:
            logger.warning("Không tìm thấy module price_validator, sẽ sử dụng chức năng mặc định")
            self.price_validator = None
        
        try:
            import price_monitor
            self.price_monitor = price_monitor
            self.price_monitor_available = True
            self.monitor_instance = None
            logger.info("Đã tìm thấy và tích hợp price_monitor")
        except ImportError:
            logger.warning("Không tìm thấy module price_monitor, sẽ không giám sát giá")
            self.price_monitor = None
        
        try:
            import prices_cache
            self.prices_cache = prices_cache
            self.price_cache_available = True
            logger.info("Đã tìm thấy và tích hợp prices_cache")
        except ImportError:
            logger.warning("Không tìm thấy module prices_cache, sẽ không cache giá")
            self.prices_cache = None
    
    def get_price(self, symbol: str, api=None) -> Tuple[float, bool]:
        '''
        Lấy giá đã được xác thực.
        
        Args:
            symbol (str): Symbol cần lấy giá
            api: Instance của BinanceAPI
            
        Returns:
            Tuple[float, bool]: (Giá, True nếu đáng tin cậy)
        '''
        if self.price_validator_available:
            try:
                return self.price_validator.get_verified_price(symbol, api)
            except Exception as e:
                logger.error(f"Lỗi khi lấy giá đã xác thực: {str(e)}")
        
        # Fallback: Lấy giá trực tiếp từ API
        if api:
            try:
                ticker_data = api.futures_ticker_price(symbol)
                if isinstance(ticker_data, dict) and 'price' in ticker_data:
                    price = float(ticker_data['price'])
                    return price, True
            except Exception as e:
                logger.error(f"Lỗi khi lấy giá từ API: {str(e)}")
        
        # Không lấy được giá
        logger.warning(f"Không thể lấy giá cho {symbol}")
        return None, False
    
    def cache_price(self, symbol: str, price: float) -> None:
        '''
        Lưu giá vào cache.
        
        Args:
            symbol (str): Symbol cần lưu
            price (float): Giá cần lưu
        '''
        if self.price_cache_available:
            try:
                self.prices_cache.update_price(symbol, price)
            except Exception as e:
                logger.error(f"Lỗi khi cache giá: {str(e)}")
    
    def get_cached_price(self, symbol: str) -> Optional[float]:
        '''
        Lấy giá từ cache.
        
        Args:
            symbol (str): Symbol cần lấy giá
            
        Returns:
            Optional[float]: Giá từ cache hoặc None
        '''
        if self.price_cache_available:
            try:
                return self.prices_cache.get_price(symbol)
            except Exception as e:
                logger.error(f"Lỗi khi lấy giá từ cache: {str(e)}")
        
        return None
    
    def safe_create_order(self, api, symbol: str, side: str, order_type: str, **kwargs) -> Dict[str, Any]:
        '''
        Tạo lệnh an toàn với xác thực giá.
        
        Args:
            api: Instance của BinanceAPI
            symbol (str): Symbol giao dịch
            side (str): Phía giao dịch (BUY/SELL)
            order_type (str): Loại lệnh
            **kwargs: Tham số khác
            
        Returns:
            Dict[str, Any]: Kết quả API hoặc lỗi
        '''
        if self.price_validator_available:
            try:
                return self.price_validator.safe_create_order(api, symbol, side, order_type, **kwargs)
            except Exception as e:
                logger.error(f"Lỗi khi tạo lệnh an toàn: {str(e)}")
        
        # Fallback: Sử dụng phương thức gốc
        if hasattr(api, 'create_order_with_position_side'):
            return api.create_order_with_position_side(
                symbol=symbol,
                side=side,
                order_type=order_type,
                **kwargs
            )
        else:
            return api.create_order(
                symbol=symbol,
                side=side,
                type=order_type,
                **kwargs
            )
    
    def is_trading_enabled(self) -> bool:
        '''
        Kiểm tra xem giao dịch có được phép không.
        
        Returns:
            bool: True nếu giao dịch được phép, False nếu không
        '''
        if self.price_validator_available:
            try:
                return self.price_validator.is_trading_enabled()
            except Exception as e:
                logger.error(f"Lỗi khi kiểm tra trạng thái giao dịch: {str(e)}")
        
        # Mặc định là được phép
        return True
    
    def start_price_monitor(self, api=None) -> None:
        '''
        Khởi động monitor giám sát giá.
        
        Args:
            api: Instance của BinanceAPI
        '''
        if self.price_monitor_available and not self.monitor_instance:
            try:
                self.monitor_instance = self.price_monitor.start_price_monitor(api)
                logger.info("Đã khởi động price_monitor")
            except Exception as e:
                logger.error(f"Lỗi khi khởi động price_monitor: {str(e)}")
    
    def stop_price_monitor(self) -> None:
        '''Dừng monitor giám sát giá.'''
        if self.monitor_instance:
            try:
                self.monitor_instance.stop()
                self.monitor_instance = None
                logger.info("Đã dừng price_monitor")
            except Exception as e:
                logger.error(f"Lỗi khi dừng price_monitor: {str(e)}")

# Tạo instance mặc định sẵn sàng để sử dụng
price_integrator = PriceValidationIntegrator()

# Các hàm tiện ích để dễ dàng sử dụng
def get_verified_price(symbol: str, api=None) -> Tuple[float, bool]:
    '''Lấy giá đã được xác thực từ nhiều nguồn.'''
    return price_integrator.get_price(symbol, api)

def safe_create_order(api, symbol: str, side: str, order_type: str, **kwargs) -> Dict[str, Any]:
    '''Tạo lệnh với cơ chế bảo vệ giá.'''
    return price_integrator.safe_create_order(api, symbol, side, order_type, **kwargs)

def is_trading_enabled() -> bool:
    '''Kiểm tra xem giao dịch có được phép không.'''
    return price_integrator.is_trading_enabled()

def cache_price(symbol: str, price: float) -> None:
    '''Lưu giá vào cache.'''
    price_integrator.cache_price(symbol, price)

def get_cached_price(symbol: str) -> Optional[float]:
    '''Lấy giá từ cache.'''
    return price_integrator.get_cached_price(symbol)

def start_price_monitor(api=None) -> None:
    '''Khởi động monitor giám sát giá.'''
    price_integrator.start_price_monitor(api)

def stop_price_monitor() -> None:
    '''Dừng monitor giám sát giá.'''
    price_integrator.stop_price_monitor()
"""

    # Tạo file
    with open("price_integration.py", "w") as f:
        f.write(integration_code)
    
    logger.info("Đã tạo file price_integration.py")
    return True

def create_usage_examples():
    """Tạo file example để hướng dẫn sử dụng"""
    
    examples_code = """#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Ví dụ cách sử dụng price_integration
'''

import logging
import time
from typing import Dict, Any

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import module tích hợp
from price_integration import (
    get_verified_price, safe_create_order, is_trading_enabled,
    cache_price, get_cached_price, start_price_monitor, stop_price_monitor
)

def example_get_prices():
    '''Ví dụ lấy giá đã được xác thực'''
    try:
        # Import BinanceAPI nếu có
        from binance_api import BinanceAPI
        from binance_api_fixes import apply_fixes_to_api
        
        api = BinanceAPI()
        api = apply_fixes_to_api(api)
        
        # Lấy giá cho một số cặp tiền
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        
        for symbol in symbols:
            # Lấy giá đã được xác thực
            price, is_reliable = get_verified_price(symbol, api)
            
            if price:
                logger.info(f"Giá {symbol}: {price} (đáng tin cậy: {is_reliable})")
                
                # Lưu giá vào cache
                cache_price(symbol, price)
            else:
                logger.warning(f"Không thể lấy giá cho {symbol}")
                
                # Thử lấy từ cache
                cached_price = get_cached_price(symbol)
                if cached_price:
                    logger.info(f"Giá cache cho {symbol}: {cached_price}")
    
    except ImportError:
        logger.error("Không thể import BinanceAPI")

def example_create_order():
    '''Ví dụ tạo lệnh an toàn'''
    try:
        # Import BinanceAPI nếu có
        from binance_api import BinanceAPI
        from binance_api_fixes import apply_fixes_to_api
        
        api = BinanceAPI()
        api = apply_fixes_to_api(api)
        
        # Kiểm tra xem giao dịch có được phép không
        if not is_trading_enabled():
            logger.warning("Giao dịch đã bị tạm dừng do vấn đề với giá")
            return
        
        # Tạo lệnh market với bảo vệ giá
        symbol = "BTCUSDT"
        side = "BUY"
        order_type = "MARKET"
        
        result = safe_create_order(
            api=api,
            symbol=symbol,
            side=side,
            order_type=order_type,
            usd_value=100,  # Giá trị 100 USD
            position_side="LONG"
        )
        
        if "error" in result:
            logger.error(f"Lỗi khi tạo lệnh: {result['error']}")
        else:
            logger.info(f"Đã tạo lệnh thành công: {result}")
            
    except ImportError:
        logger.error("Không thể import BinanceAPI")

def example_monitor_prices():
    '''Ví dụ giám sát giá'''
    try:
        # Import BinanceAPI nếu có
        from binance_api import BinanceAPI
        from binance_api_fixes import apply_fixes_to_api
        
        api = BinanceAPI()
        api = apply_fixes_to_api(api)
        
        # Khởi động monitor giám sát giá
        start_price_monitor(api)
        
        # Giữ script chạy một thời gian
        logger.info("Đã khởi động price_monitor, chờ 60 giây...")
        for i in range(6):
            time.sleep(10)
            logger.info(f"Đã chạy được {(i+1)*10} giây")
            
            # Kiểm tra trạng thái giao dịch
            if not is_trading_enabled():
                logger.warning("Giao dịch đã bị tạm dừng do vấn đề với giá")
        
        # Dừng monitor
        stop_price_monitor()
        logger.info("Đã dừng price_monitor")
        
    except ImportError:
        logger.error("Không thể import BinanceAPI")

def main():
    '''Hàm chính chạy các ví dụ'''
    logger.info("= Ví dụ 1: Lấy giá đã được xác thực =")
    example_get_prices()
    
    logger.info("\\n= Ví dụ 2: Tạo lệnh an toàn =")
    example_create_order()
    
    logger.info("\\n= Ví dụ 3: Giám sát giá =")
    example_monitor_prices()

if __name__ == "__main__":
    main()
"""

    # Tạo file
    with open("price_integration_examples.py", "w") as f:
        f.write(examples_code)
    
    logger.info("Đã tạo file price_integration_examples.py")
    return True

def update_main_py():
    """Tạo file patch để cập nhật main.py"""
    
    patch_code = """#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Patch để cập nhật main.py với tích hợp price_validator
'''

import os
import sys
import logging
import fileinput
import re
import shutil
from typing import List, Dict, Any

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def backup_file(file_path: str) -> str:
    '''Tạo bản sao lưu của file'''
    backup_path = f"{file_path}.bak"
    shutil.copy2(file_path, backup_path)
    logger.info(f"Đã tạo bản sao lưu: {backup_path}")
    return backup_path

def update_imports(file_path: str) -> bool:
    """Cập nhật phần import trong main.py"""
    try:
        import_statement = "from price_integration import get_verified_price, safe_create_order, is_trading_enabled, start_price_monitor, stop_price_monitor"
        
        # Kiểm tra xem import đã tồn tại chưa
        with open(file_path, 'r') as f:
            content = f.read()
            if import_statement in content:
                logger.info("Import đã tồn tại, bỏ qua")
                return True
        
        # Thêm import vào sau các import khác
        pattern = r"(import.*\n|from.*import.*\n)"
        last_import_pos = 0
        
        with open(file_path, 'r') as f:
            content = f.read()
            
            for match in re.finditer(pattern, content):
                last_import_pos = match.end()
        
        if last_import_pos > 0:
            new_content = content[:last_import_pos] + import_statement + "\\n" + content[last_import_pos:]
            
            with open(file_path, 'w') as f:
                f.write(new_content)
                
            logger.info(f"Đã thêm import vào {file_path}")
            return True
        else:
            logger.error("Không tìm thấy vị trí để thêm import")
            return False
            
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật imports: {str(e)}")
        return False

def add_price_monitor_code(file_path: str) -> bool:
    """Thêm code khởi động price_monitor vào main.py"""
    try:
        # Đọc nội dung file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Kiểm tra xem code đã tồn tại chưa
        if "start_price_monitor(api)" in content:
            logger.info("Code khởi động price_monitor đã tồn tại, bỏ qua")
            return True
            
        # Tìm vị trí thích hợp để thêm code
        # Thường là sau khi khởi tạo API và trước khi vào vòng lặp chính
        main_init_pattern = r"if __name__ == ['\"]__main__['\"]:.*?\n"
        
        match = re.search(main_init_pattern, content)
        if match:
            insert_pos = match.end()
            
            # Code cần thêm
            monitor_code = """
    # Khởi động price_monitor
    try:
        logger.info("Khởi động price_monitor")
        start_price_monitor(api)
    except Exception as e:
        logger.error(f"Lỗi khi khởi động price_monitor: {str(e)}")
    
"""
            new_content = content[:insert_pos] + monitor_code + content[insert_pos:]
            
            with open(file_path, 'w') as f:
                f.write(new_content)
                
            logger.info(f"Đã thêm code khởi động price_monitor vào {file_path}")
            return True
        else:
            logger.error("Không tìm thấy vị trí để thêm code")
            return False
            
    except Exception as e:
        logger.error(f"Lỗi khi thêm code khởi động price_monitor: {str(e)}")
        return False

def update_order_creation(file_path: str) -> bool:
    """Cập nhật phần tạo lệnh để sử dụng safe_create_order"""
    try:
        # Đọc nội dung file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Kiểm tra xem đã sử dụng safe_create_order chưa
        if "safe_create_order" in content:
            logger.info("Đã sử dụng safe_create_order, bỏ qua")
            return True
            
        # Tìm và thay thế các lệnh tạo order
        # Đây là mẫu đơn giản, trong thực tế cần phân tích code kỹ hơn
        order_pattern = r"(api\.create_order\(|api\.create_order_with_position_side\()"
        
        if re.search(order_pattern, content):
            # Thay thế bằng safe_create_order
            new_content = re.sub(
                order_pattern,
                "safe_create_order(api, ",
                content
            )
            
            with open(file_path, 'w') as f:
                f.write(new_content)
                
            logger.info(f"Đã cập nhật lệnh tạo order trong {file_path}")
            return True
        else:
            logger.info("Không tìm thấy lệnh tạo order nào để cập nhật")
            return True
            
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật order creation: {str(e)}")
        return False

def add_trading_check(file_path: str) -> bool:
    """Thêm kiểm tra is_trading_enabled trước khi tạo lệnh"""
    try:
        # Đọc nội dung file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Kiểm tra xem đã có is_trading_enabled chưa
        if "is_trading_enabled()" in content:
            logger.info("Đã có kiểm tra is_trading_enabled, bỏ qua")
            return True
            
        # Tìm các chỗ tạo lệnh và thêm kiểm tra
        # Đây là mẫu đơn giản, trong thực tế cần phân tích code kỹ hơn
        pattern = r"(def\s+(?:create_order|place_order|execute_trade|open_position).*?:.*?\n)"
        
        if re.search(pattern, content):
            # Thêm kiểm tra vào đầu các hàm tạo lệnh
            new_content = re.sub(
                pattern,
                "\\g<1>    # Kiểm tra xem giao dịch có được phép không\\n    if not is_trading_enabled():\\n        logger.warning(\"Giao dịch đã bị tạm dừng do vấn đề với giá\")\\n        return {\"error\": \"Giao dịch đã bị tạm dừng\"}\\n\\n",
                content
            )
            
            with open(file_path, 'w') as f:
                f.write(new_content)
                
            logger.info(f"Đã thêm kiểm tra is_trading_enabled vào {file_path}")
            return True
        else:
            logger.info("Không tìm thấy hàm tạo lệnh nào để thêm kiểm tra")
            return True
            
    except Exception as e:
        logger.error(f"Lỗi khi thêm kiểm tra is_trading_enabled: {str(e)}")
        return False

def main():
    """Hàm chính để cập nhật main.py"""
    logger.info("Bắt đầu cập nhật main.py")
    
    # Đường dẫn đến main.py
    main_file = "main.py"
    
    # Kiểm tra file tồn tại
    if not os.path.exists(main_file):
        logger.error(f"Không tìm thấy file {main_file}")
        return False
    
    # Tạo bản sao lưu
    backup_file(main_file)
    
    # Cập nhật imports
    if not update_imports(main_file):
        logger.error("Lỗi khi cập nhật imports")
        return False
    
    # Thêm code khởi động price_monitor
    if not add_price_monitor_code(main_file):
        logger.error("Lỗi khi thêm code khởi động price_monitor")
        return False
    
    # Cập nhật order creation
    if not update_order_creation(main_file):
        logger.error("Lỗi khi cập nhật order creation")
        return False
    
    # Thêm kiểm tra is_trading_enabled
    if not add_trading_check(main_file):
        logger.error("Lỗi khi thêm kiểm tra is_trading_enabled")
        return False
    
    logger.info("Đã cập nhật thành công main.py")
    logger.info("Vui lòng kiểm tra các thay đổi trước khi chạy")
    
    return True

if __name__ == "__main__":
    # Tạo các file tích hợp
    create_integration_file()
    create_usage_examples()
    
    # Hỏi trước khi cập nhật main.py
    answer = input("Bạn có muốn cập nhật main.py không? (y/n): ")
    if answer.lower() == 'y':
        main()
    else:
        logger.info("Bỏ qua cập nhật main.py")
        
    logger.info("Hoàn tất")
"""

    # Tạo file
    with open("patch_main.py", "w") as f:
        f.write(patch_code)
    
    logger.info("Đã tạo file patch_main.py")
    return True

def main():
    """Hàm chính thực hiện tích hợp"""
    logger.info("===== BẮT ĐẦU TÍCH HỢP PRICE VALIDATOR =====")
    
    # Tạo file tích hợp
    create_integration_file()
    
    # Tạo ví dụ sử dụng
    create_usage_examples()
    
    # Tạo file patch
    update_main_py()
    
    logger.info("===== HOÀN TẤT TÍCH HỢP PRICE VALIDATOR =====")
    logger.info("Các file đã được tạo:")
    logger.info("1. price_integration.py - Module tích hợp")
    logger.info("2. price_integration_examples.py - Ví dụ sử dụng")
    logger.info("3. patch_main.py - Script cập nhật main.py")
    logger.info("")
    logger.info("Để cập nhật main.py, chạy: python patch_main.py")
    
if __name__ == "__main__":
    main()