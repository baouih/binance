#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module chức năng retry cho các API calls
"""

import time
import logging
import traceback
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Thiết lập logging
logger = logging.getLogger("retry")

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, 
          exceptions: tuple = (Exception,), validate_result: Optional[Callable] = None):
    """
    Decorator thực hiện thử lại các API calls tự động khi gặp lỗi
    
    :param max_attempts: Số lần thử tối đa
    :param delay: Thời gian chờ ban đầu giữa các lần thử (giây)
    :param backoff: Hệ số tăng thời gian chờ sau mỗi lần thử
    :param exceptions: Tuple các exceptions cần thử lại
    :param validate_result: Hàm kiểm tra kết quả (nếu có)
    :return: Decorator
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            last_exception = None
            
            # Lặp cho đến khi đạt số lần thử tối đa
            while attempt < max_attempts:
                try:
                    # Thực hiện gọi hàm
                    result = func(*args, **kwargs)
                    
                    # Nếu có hàm validate_result và kết quả không hợp lệ, xử lý như lỗi
                    if validate_result and not validate_result(result):
                        attempt += 1
                        logger.warning(f"Lần thử {attempt}/{max_attempts} thất bại: kết quả không hợp lệ")
                        
                        if attempt < max_attempts:
                            logger.info(f"Chờ {current_delay:.2f}s và thử lại...")
                            time.sleep(current_delay)
                            current_delay *= backoff
                        continue
                    
                    # Nếu thành công, trả về kết quả
                    return result
                
                except exceptions as e:
                    attempt += 1
                    last_exception = e
                    
                    # Ghi log lỗi
                    logger.warning(f"Lần thử {attempt}/{max_attempts} gặp lỗi: {str(e)}")
                    
                    # Nếu còn lần thử, đợi và thử lại
                    if attempt < max_attempts:
                        logger.info(f"Chờ {current_delay:.2f}s và thử lại...")
                        time.sleep(current_delay)
                        current_delay *= backoff
            
            # Nếu đã thử hết số lần mà vẫn thất bại, raise exception
            logger.error(f"Đã thử lại {max_attempts} lần nhưng thất bại")
            if last_exception:
                logger.error(f"Exception cuối cùng: {traceback.format_exc()}")
                raise last_exception
            
            # Trường hợp thất bại vì kết quả không hợp lệ
            raise Exception(f"Thất bại sau {max_attempts} lần thử với kết quả không hợp lệ")
        
        return wrapper
    
    return decorator

# Hàm retry_with_result tự động retry với kiểm tra kết quả
def retry_with_result(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, 
                      exceptions: tuple = (Exception,), success_check: Callable = lambda x: x):
    """
    Wrapper thực hiện thử lại API calls và kiểm tra kết quả
    
    :param max_attempts: Số lần thử tối đa
    :param delay: Thời gian chờ ban đầu giữa các lần thử (giây)
    :param backoff: Hệ số tăng thời gian chờ sau mỗi lần thử
    :param exceptions: Tuple các exceptions cần thử lại
    :param success_check: Hàm kiểm tra thành công từ kết quả
    :return: Tuple (success, result, error)
    """
    def retry_function(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            last_exception = None
            
            while attempt < max_attempts:
                try:
                    # Gọi hàm
                    result = func(*args, **kwargs)
                    
                    # Kiểm tra kết quả
                    if success_check(result):
                        return True, result, None
                    
                    # Kết quả không hợp lệ
                    attempt += 1
                    logger.warning(f"Lần thử {attempt}/{max_attempts} thất bại: kết quả không hợp lệ")
                    
                    if attempt < max_attempts:
                        logger.info(f"Chờ {current_delay:.2f}s và thử lại...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                
                except exceptions as e:
                    attempt += 1
                    last_exception = e
                    
                    logger.warning(f"Lần thử {attempt}/{max_attempts} gặp lỗi: {str(e)}")
                    
                    if attempt < max_attempts:
                        logger.info(f"Chờ {current_delay:.2f}s và thử lại...")
                        time.sleep(current_delay)
                        current_delay *= backoff
            
            # Nếu đã thử hết số lần mà vẫn thất bại
            logger.error(f"Đã thử lại {max_attempts} lần nhưng thất bại")
            if last_exception:
                logger.error(f"Exception cuối cùng: {str(last_exception)}")
                return False, None, last_exception
            
            return False, None, Exception(f"Thất bại sau {max_attempts} lần thử với kết quả không hợp lệ")
        
        return wrapper
    
    return retry_function

# Hàm wrapper tiện ích để retry một hàm nhanh chóng
def retry_call(func: Callable, args: tuple = (), kwargs: dict = None, 
              max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0,
              exceptions: tuple = (Exception,), success_check: Optional[Callable] = None) -> Tuple[bool, Any, Optional[Exception]]:
    """
    Hàm wrapper để retry một hàm với các tham số
    
    :param func: Hàm cần gọi
    :param args: Tham số vị trí
    :param kwargs: Tham số từ khóa
    :param max_attempts: Số lần thử tối đa
    :param delay: Thời gian chờ ban đầu giữa các lần thử (giây)
    :param backoff: Hệ số tăng thời gian chờ sau mỗi lần thử
    :param exceptions: Tuple các exceptions cần thử lại
    :param success_check: Hàm kiểm tra thành công từ kết quả
    :return: Tuple (success, result, error)
    """
    if kwargs is None:
        kwargs = {}
    
    attempt = 0
    current_delay = delay
    last_exception = None
    
    while attempt < max_attempts:
        try:
            # Gọi hàm
            result = func(*args, **kwargs)
            
            # Kiểm tra kết quả nếu có hàm kiểm tra
            if success_check and not success_check(result):
                attempt += 1
                logger.warning(f"Lần thử {attempt}/{max_attempts} thất bại: kết quả không hợp lệ")
                
                if attempt < max_attempts:
                    logger.info(f"Chờ {current_delay:.2f}s và thử lại...")
                    time.sleep(current_delay)
                    current_delay *= backoff
                continue
            
            # Nếu thành công, trả về kết quả
            return True, result, None
        
        except exceptions as e:
            attempt += 1
            last_exception = e
            
            # Ghi log lỗi
            logger.warning(f"Lần thử {attempt}/{max_attempts} gặp lỗi: {str(e)}")
            
            # Nếu còn lần thử, đợi và thử lại
            if attempt < max_attempts:
                logger.info(f"Chờ {current_delay:.2f}s và thử lại...")
                time.sleep(current_delay)
                current_delay *= backoff
    
    # Nếu đã thử hết số lần mà vẫn thất bại
    logger.error(f"Đã thử lại {max_attempts} lần nhưng thất bại")
    if last_exception:
        logger.error(f"Exception cuối cùng: {str(last_exception)}")
        return False, None, last_exception
    
    return False, None, Exception(f"Thất bại sau {max_attempts} lần thử với kết quả không hợp lệ")

# Hàm kiểm tra module
def test_retry():
    """Kiểm tra chức năng retry"""
    # Khởi tạo logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Hàm có xác suất lỗi để kiểm tra
    failed_attempts = 0
    
    def unstable_function(success_rate=0.3):
        nonlocal failed_attempts
        import random
        
        # Tăng số lần gọi
        failed_attempts += 1
        
        # Ngẫu nhiên thành công hoặc thất bại
        if random.random() < success_rate:
            logger.info(f"Hàm thành công sau {failed_attempts} lần gọi")
            failed_attempts = 0
            return {"status": "success", "data": "Dữ liệu mẫu"}
        else:
            logger.info(f"Lần gọi thứ {failed_attempts} thất bại")
            raise Exception("Lỗi ngẫu nhiên để kiểm tra retry")
    
    # Kiểm tra retry decorator
    print("\n=== Kiểm tra retry decorator ===")
    
    @retry(max_attempts=5, delay=0.5, backoff=1.5)
    def test_with_decorator():
        return unstable_function(success_rate=0.3)
    
    try:
        result = test_with_decorator()
        print(f"Kết quả: {result}")
    except Exception as e:
        print(f"Kiểm tra thất bại với lỗi: {e}")
    
    # Kiểm tra retry_call function
    print("\n=== Kiểm tra retry_call function ===")
    failed_attempts = 0
    success, result, error = retry_call(
        unstable_function, 
        kwargs={"success_rate": 0.3},
        max_attempts=5,
        delay=0.5,
        backoff=1.5
    )
    
    if success:
        print(f"Thành công: {result}")
    else:
        print(f"Thất bại: {error}")

if __name__ == "__main__":
    test_retry()