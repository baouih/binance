#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module cache dữ liệu (DataCache)

Module này cung cấp các lớp để lưu trữ cache dữ liệu, giúp giảm thiểu số lượng
request đến API và tăng tốc độ xử lý, đồng thời cung cấp các tính năng quan sát
thay đổi dữ liệu (observable).
"""

import os
import json
import time
import logging
import hashlib
import threading
from typing import Dict, List, Tuple, Optional, Union, Any, Callable

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('data_cache')

class DataCache:
    """Lớp lưu trữ cache dữ liệu"""
    
    def __init__(self, max_items: int = 1000, ttl: int = 3600,
                enable_disk_cache: bool = False, cache_dir: str = 'cache'):
        """
        Khởi tạo cache dữ liệu
        
        Args:
            max_items (int): Số lượng item tối đa trong cache
            ttl (int): Thời gian sống của dữ liệu (giây)
            enable_disk_cache (bool): Bật lưu cache ra đĩa
            cache_dir (str): Thư mục lưu cache
        """
        self.max_items = max_items
        self.ttl = ttl
        self.enable_disk_cache = enable_disk_cache
        self.cache_dir = cache_dir
        
        # Cache dữ liệu theo category và key
        # {category: {key: {'data': any, 'timestamp': float}}}
        self.cache = {}
        
        # Thống kê
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'evictions': 0,
            'disk_reads': 0,
            'disk_writes': 0
        }
        
        # Lock để đảm bảo thread-safety
        self.lock = threading.RLock()
        
        # Tạo thư mục cache nếu cần
        if enable_disk_cache and not os.path.exists(cache_dir):
            try:
                os.makedirs(cache_dir)
                logger.info(f"Đã tạo thư mục cache: {cache_dir}")
            except Exception as e:
                logger.warning(f"Không thể tạo thư mục cache: {str(e)}")
                self.enable_disk_cache = False
    
    def _get_cache_path(self, category: str, key: str) -> str:
        """
        Lấy đường dẫn file cache
        
        Args:
            category (str): Danh mục dữ liệu
            key (str): Khóa dữ liệu
            
        Returns:
            str: Đường dẫn file cache
        """
        # Tạo hash cho key để đảm bảo an toàn cho tên file
        key_hash = hashlib.md5(f"{category}:{key}".encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{category}_{key_hash}.json")
    
    def _write_disk_cache(self, category: str, key: str, data: Dict) -> bool:
        """
        Ghi dữ liệu ra đĩa
        
        Args:
            category (str): Danh mục dữ liệu
            key (str): Khóa dữ liệu
            data (Dict): Dữ liệu cần ghi
            
        Returns:
            bool: True nếu ghi thành công, False nếu không
        """
        if not self.enable_disk_cache:
            return False
        
        try:
            cache_path = self._get_cache_path(category, key)
            with open(cache_path, 'w') as f:
                json.dump(data, f)
            
            self.stats['disk_writes'] += 1
            return True
        except Exception as e:
            logger.warning(f"Không thể ghi cache ra đĩa: {str(e)}")
            return False
    
    def _read_disk_cache(self, category: str, key: str) -> Optional[Dict]:
        """
        Đọc dữ liệu từ đĩa
        
        Args:
            category (str): Danh mục dữ liệu
            key (str): Khóa dữ liệu
            
        Returns:
            Optional[Dict]: Dữ liệu nếu đọc thành công, None nếu không
        """
        if not self.enable_disk_cache:
            return None
        
        try:
            cache_path = self._get_cache_path(category, key)
            if os.path.exists(cache_path):
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                
                self.stats['disk_reads'] += 1
                return data
            else:
                return None
        except Exception as e:
            logger.warning(f"Không thể đọc cache từ đĩa: {str(e)}")
            return None
    
    def _evict_old_items(self) -> int:
        """
        Xóa các item cũ để giải phóng bộ nhớ
        
        Returns:
            int: Số lượng item đã xóa
        """
        with self.lock:
            current_time = time.time()
            total_evicted = 0
            
            for category in self.cache:
                keys_to_remove = []
                
                for key, item in self.cache[category].items():
                    if current_time - item['timestamp'] > self.ttl:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self.cache[category][key]
                    total_evicted += 1
            
            self.stats['evictions'] += total_evicted
            return total_evicted
    
    def _evict_if_full(self) -> bool:
        """
        Kiểm tra và xóa các item nếu cache đầy
        
        Returns:
            bool: True nếu đã xóa, False nếu không
        """
        with self.lock:
            # Đếm tổng số item
            total_items = sum(len(items) for items in self.cache.values())
            
            if total_items >= self.max_items:
                # Xóa các item cũ trước
                evicted = self._evict_old_items()
                
                # Nếu vẫn đầy, xóa bớt 20% item cũ nhất
                if evicted < 1 or total_items - evicted >= self.max_items:
                    all_items = []
                    for category, items in self.cache.items():
                        for key, item in items.items():
                            all_items.append((category, key, item['timestamp']))
                    
                    # Sắp xếp theo thời gian cũ nhất
                    all_items.sort(key=lambda x: x[2])
                    
                    # Xóa 20% đầu
                    items_to_remove = int(len(all_items) * 0.2) + 1
                    for category, key, _ in all_items[:items_to_remove]:
                        if category in self.cache and key in self.cache[category]:
                            del self.cache[category][key]
                            self.stats['evictions'] += 1
                
                return True
            
            return False
    
    def set(self, category: str, key: str, data: Any) -> bool:
        """
        Lưu dữ liệu vào cache
        
        Args:
            category (str): Danh mục dữ liệu
            key (str): Khóa dữ liệu
            data (Any): Dữ liệu cần lưu
            
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        with self.lock:
            try:
                # Xóa bớt nếu đầy
                self._evict_if_full()
                
                # Khởi tạo category nếu chưa có
                if category not in self.cache:
                    self.cache[category] = {}
                
                # Lưu dữ liệu
                self.cache[category][key] = {
                    'data': data,
                    'timestamp': time.time()
                }
                
                # Cập nhật thống kê
                self.stats['sets'] += 1
                
                # Lưu ra đĩa nếu cần
                if self.enable_disk_cache:
                    try:
                        self._write_disk_cache(category, key, {
                            'data': data,
                            'timestamp': time.time()
                        })
                    except:
                        pass  # Bỏ qua lỗi lưu đĩa
                
                return True
            except Exception as e:
                logger.error(f"Lỗi khi lưu dữ liệu vào cache: {str(e)}")
                return False
    
    def get(self, category: str, key: str, default: Any = None) -> Any:
        """
        Lấy dữ liệu từ cache
        
        Args:
            category (str): Danh mục dữ liệu
            key (str): Khóa dữ liệu
            default (Any, optional): Giá trị mặc định nếu không tìm thấy
            
        Returns:
            Any: Dữ liệu nếu tìm thấy, default nếu không
        """
        with self.lock:
            try:
                # Kiểm tra trong memory cache
                if category in self.cache and key in self.cache[category]:
                    item = self.cache[category][key]
                    # Kiểm tra TTL
                    if time.time() - item['timestamp'] <= self.ttl:
                        self.stats['hits'] += 1
                        return item['data']
                    else:
                        # Xóa item hết hạn
                        del self.cache[category][key]
                
                # Không có trong memory cache, thử đọc từ disk cache
                if self.enable_disk_cache:
                    disk_data = self._read_disk_cache(category, key)
                    if disk_data:
                        # Kiểm tra TTL
                        if time.time() - disk_data['timestamp'] <= self.ttl:
                            # Cache lại vào memory
                            if category not in self.cache:
                                self.cache[category] = {}
                            self.cache[category][key] = disk_data
                            
                            self.stats['hits'] += 1
                            return disk_data['data']
                
                # Không tìm thấy hoặc hết hạn
                self.stats['misses'] += 1
                return default
            except Exception as e:
                logger.error(f"Lỗi khi lấy dữ liệu từ cache: {str(e)}")
                self.stats['misses'] += 1
                return default
    
    def delete(self, category: str, key: str = None) -> bool:
        """
        Xóa dữ liệu khỏi cache
        
        Args:
            category (str): Danh mục dữ liệu
            key (str, optional): Khóa dữ liệu, nếu None sẽ xóa toàn bộ category
            
        Returns:
            bool: True nếu xóa thành công, False nếu không
        """
        with self.lock:
            try:
                if category not in self.cache:
                    return False
                
                if key is None:
                    # Xóa toàn bộ category
                    del self.cache[category]
                    return True
                elif key in self.cache[category]:
                    # Xóa một key cụ thể
                    del self.cache[category][key]
                    return True
                else:
                    return False
            except Exception as e:
                logger.error(f"Lỗi khi xóa dữ liệu khỏi cache: {str(e)}")
                return False
    
    def clear(self) -> bool:
        """
        Xóa toàn bộ cache
        
        Returns:
            bool: True nếu xóa thành công, False nếu không
        """
        with self.lock:
            try:
                self.cache = {}
                return True
            except Exception as e:
                logger.error(f"Lỗi khi xóa toàn bộ cache: {str(e)}")
                return False
    
    def refresh_ttl(self, category: str, key: str) -> bool:
        """
        Làm mới thời gian sống của một item
        
        Args:
            category (str): Danh mục dữ liệu
            key (str): Khóa dữ liệu
            
        Returns:
            bool: True nếu làm mới thành công, False nếu không
        """
        with self.lock:
            try:
                if (category in self.cache and 
                    key in self.cache[category]):
                    # Cập nhật timestamp
                    self.cache[category][key]['timestamp'] = time.time()
                    return True
                return False
            except Exception as e:
                logger.error(f"Lỗi khi làm mới TTL: {str(e)}")
                return False
    
    def is_valid(self, category: str, key: str) -> bool:
        """
        Kiểm tra xem một item có hợp lệ (còn hạn) hay không
        
        Args:
            category (str): Danh mục dữ liệu
            key (str): Khóa dữ liệu
            
        Returns:
            bool: True nếu hợp lệ, False nếu không
        """
        with self.lock:
            try:
                if (category in self.cache and 
                    key in self.cache[category]):
                    # Kiểm tra TTL
                    return time.time() - self.cache[category][key]['timestamp'] <= self.ttl
                return False
            except Exception as e:
                logger.error(f"Lỗi khi kiểm tra tính hợp lệ: {str(e)}")
                return False
    
    def get_timestamp(self, category: str, key: str) -> Optional[float]:
        """
        Lấy timestamp của một item trong cache
        
        Args:
            category (str): Danh mục dữ liệu
            key (str): Khóa dữ liệu
            
        Returns:
            Optional[float]: Timestamp nếu item tồn tại, None nếu không
        """
        with self.lock:
            try:
                if (category in self.cache and 
                    key in self.cache[category]):
                    return self.cache[category][key]['timestamp']
                return None
            except Exception as e:
                logger.error(f"Lỗi khi lấy timestamp: {str(e)}")
                return None
    
    def get_stats(self) -> Dict:
        """
        Lấy thống kê về cache
        
        Returns:
            Dict: Thống kê về cache
        """
        with self.lock:
            # Đếm số lượng item trong cache
            total_items = sum(len(items) for items in self.cache.values())
            
            # Tạo bản sao thống kê và bổ sung thông tin
            stats = self.stats.copy()
            stats['total_items'] = total_items
            stats['max_items'] = self.max_items
            stats['ttl'] = self.ttl
            stats['hit_ratio'] = 0
            
            total_requests = stats['hits'] + stats['misses']
            if total_requests > 0:
                stats['hit_ratio'] = stats['hits'] / total_requests
            
            return stats
    
    def dump_to_disk(self) -> bool:
        """
        Lưu toàn bộ cache ra đĩa
        
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        if not self.enable_disk_cache:
            return False
        
        with self.lock:
            try:
                success_count = 0
                fail_count = 0
                
                for category, items in self.cache.items():
                    for key, item in items.items():
                        if self._write_disk_cache(category, key, item):
                            success_count += 1
                        else:
                            fail_count += 1
                
                logger.info(f"Đã lưu {success_count} item ra đĩa, {fail_count} item lỗi")
                return fail_count == 0
            except Exception as e:
                logger.error(f"Lỗi khi lưu cache ra đĩa: {str(e)}")
                return False
    
    def load_from_disk(self) -> bool:
        """
        Tải toàn bộ cache từ đĩa
        
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        if not self.enable_disk_cache or not os.path.exists(self.cache_dir):
            return False
        
        with self.lock:
            try:
                self.cache = {}
                loaded_count = 0
                
                # Lấy tất cả file cache
                for filename in os.listdir(self.cache_dir):
                    if not filename.endswith('.json'):
                        continue
                    
                    try:
                        # Phân tích tên file để lấy category
                        parts = filename.split('_')
                        if len(parts) < 2:
                            continue
                        
                        category = parts[0]
                        file_path = os.path.join(self.cache_dir, filename)
                        
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                        
                        # Tạo key giả làm hash từ tên file
                        key_hash = filename.replace(f"{category}_", '').replace('.json', '')
                        
                        # Tìm key thực tế (trong trường hợp lý tưởng)
                        real_key = None
                        for candidate_key in data.get('meta_keys', []):
                            test_hash = hashlib.md5(f"{category}:{candidate_key}".encode()).hexdigest()
                            if test_hash == key_hash:
                                real_key = candidate_key
                                break
                        
                        # Nếu không tìm thấy key thực tế, sử dụng hash
                        if real_key is None:
                            real_key = key_hash
                        
                        # Kiểm tra TTL
                        if 'timestamp' in data and time.time() - data['timestamp'] <= self.ttl:
                            # Thêm vào cache
                            if category not in self.cache:
                                self.cache[category] = {}
                            
                            self.cache[category][real_key] = data
                            loaded_count += 1
                    except Exception as e:
                        logger.warning(f"Lỗi khi tải file cache {filename}: {str(e)}")
                
                logger.info(f"Đã tải {loaded_count} item từ đĩa")
                return True
            except Exception as e:
                logger.error(f"Lỗi khi tải cache từ đĩa: {str(e)}")
                return False


class CacheObserver:
    """Lớp cơ sở cho observer theo dõi thay đổi dữ liệu trong cache"""
    
    def __init__(self, callback: Callable):
        """
        Khởi tạo observer
        
        Args:
            callback (Callable): Hàm callback khi có thay đổi
        """
        self.callback = callback
    
    def notify(self, category: str, key: str, data: Any) -> None:
        """
        Thông báo khi có thay đổi
        
        Args:
            category (str): Danh mục dữ liệu
            key (str): Khóa dữ liệu
            data (Any): Dữ liệu mới
        """
        if callable(self.callback):
            self.callback(category, key, data)


class ObservableDataCache(DataCache):
    """Lớp cache dữ liệu với khả năng theo dõi thay đổi"""
    
    def __init__(self, max_items: int = 1000, ttl: int = 3600,
                enable_disk_cache: bool = False, cache_dir: str = 'cache'):
        """
        Khởi tạo cache dữ liệu có thể quan sát
        
        Args:
            max_items (int): Số lượng item tối đa trong cache
            ttl (int): Thời gian sống của dữ liệu (giây)
            enable_disk_cache (bool): Bật lưu cache ra đĩa
            cache_dir (str): Thư mục lưu cache
        """
        super().__init__(max_items, ttl, enable_disk_cache, cache_dir)
        
        # Dict lưu trữ observers theo category và key
        # {category: {key: [observer1, observer2, ...]}}
        self.observers = {}
        
        # Dict lưu trữ observers theo pattern
        # {pattern: [observer1, observer2, ...]}
        self.pattern_observers = {}
        
        # Lock riêng cho observers
        self.observer_lock = threading.RLock()
    
    def register_observer(self, category: str, key: str, callback: Callable) -> None:
        """
        Đăng ký observer cho một key cụ thể
        
        Args:
            category (str): Danh mục dữ liệu
            key (str): Khóa dữ liệu
            callback (Callable): Hàm callback khi có thay đổi
        """
        with self.observer_lock:
            # Khởi tạo category và key nếu chưa có
            if category not in self.observers:
                self.observers[category] = {}
            if key not in self.observers[category]:
                self.observers[category][key] = []
            
            # Tạo và thêm observer
            observer = CacheObserver(callback)
            self.observers[category][key].append(observer)
            
            logger.debug(f"Đã đăng ký observer cho {category}/{key}")
    
    def register_pattern_observer(self, pattern: str, callback: Callable) -> None:
        """
        Đăng ký observer theo pattern (dạng 'category/key_pattern')
        
        Args:
            pattern (str): Pattern dạng 'category/key_pattern' (hỗ trợ * làm wildcard)
            callback (Callable): Hàm callback khi có thay đổi
        """
        with self.observer_lock:
            if pattern not in self.pattern_observers:
                self.pattern_observers[pattern] = []
            
            # Tạo và thêm observer
            observer = CacheObserver(callback)
            self.pattern_observers[pattern].append(observer)
            
            logger.debug(f"Đã đăng ký pattern observer cho {pattern}")
    
    def unregister_observer(self, category: str, key: str, callback: Callable) -> bool:
        """
        Hủy đăng ký observer
        
        Args:
            category (str): Danh mục dữ liệu
            key (str): Khóa dữ liệu
            callback (Callable): Hàm callback đã đăng ký
            
        Returns:
            bool: True nếu hủy thành công, False nếu không
        """
        with self.observer_lock:
            if (category in self.observers and 
                key in self.observers[category]):
                # Tìm và xóa observer có callback trùng khớp
                observers = self.observers[category][key]
                for i, observer in enumerate(observers):
                    if observer.callback == callback:
                        observers.pop(i)
                        logger.debug(f"Đã hủy đăng ký observer cho {category}/{key}")
                        return True
            
            return False
    
    def unregister_pattern_observer(self, pattern: str, callback: Callable) -> bool:
        """
        Hủy đăng ký pattern observer
        
        Args:
            pattern (str): Pattern đã đăng ký
            callback (Callable): Hàm callback đã đăng ký
            
        Returns:
            bool: True nếu hủy thành công, False nếu không
        """
        with self.observer_lock:
            if pattern in self.pattern_observers:
                # Tìm và xóa observer có callback trùng khớp
                observers = self.pattern_observers[pattern]
                for i, observer in enumerate(observers):
                    if observer.callback == callback:
                        observers.pop(i)
                        logger.debug(f"Đã hủy đăng ký pattern observer cho {pattern}")
                        return True
            
            return False
    
    def _match_pattern(self, pattern: str, category: str, key: str) -> bool:
        """
        Kiểm tra xem category/key có khớp với pattern không
        
        Args:
            pattern (str): Pattern dạng 'category/key_pattern'
            category (str): Danh mục dữ liệu
            key (str): Khóa dữ liệu
            
        Returns:
            bool: True nếu khớp, False nếu không
        """
        try:
            # Tách pattern
            if '/' not in pattern:
                return False
            
            cat_pattern, key_pattern = pattern.split('/', 1)
            
            # So khớp category
            if cat_pattern != '*' and cat_pattern != category:
                return False
            
            # So khớp key
            if key_pattern == '*':
                return True
            elif '*' in key_pattern:
                # Chuyển pattern thành regex
                import re
                regex_pattern = key_pattern.replace('*', '.*')
                return bool(re.match(f"^{regex_pattern}$", key))
            else:
                return key_pattern == key
        except Exception as e:
            logger.error(f"Lỗi khi so khớp pattern: {str(e)}")
            return False
    
    def _notify_observers(self, category: str, key: str, data: Any) -> None:
        """
        Thông báo cho tất cả observers về thay đổi
        
        Args:
            category (str): Danh mục dữ liệu
            key (str): Khóa dữ liệu
            data (Any): Dữ liệu mới
        """
        with self.observer_lock:
            # Thông báo cho observers cụ thể
            if category in self.observers and key in self.observers[category]:
                for observer in self.observers[category][key]:
                    try:
                        observer.notify(category, key, data)
                    except Exception as e:
                        logger.error(f"Lỗi khi thông báo cho observer: {str(e)}")
            
            # Thông báo cho pattern observers
            for pattern, observers in self.pattern_observers.items():
                if self._match_pattern(pattern, category, key):
                    for observer in observers:
                        try:
                            observer.notify(category, key, data)
                        except Exception as e:
                            logger.error(f"Lỗi khi thông báo cho pattern observer: {str(e)}")
    
    def set(self, category: str, key: str, data: Any) -> bool:
        """
        Lưu dữ liệu vào cache và thông báo cho observers
        
        Args:
            category (str): Danh mục dữ liệu
            key (str): Khóa dữ liệu
            data (Any): Dữ liệu cần lưu
            
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        # Gọi phương thức set của lớp cha
        result = super().set(category, key, data)
        
        # Nếu lưu thành công, thông báo cho observers
        if result:
            self._notify_observers(category, key, data)
        
        return result
    
    def delete(self, category: str, key: str = None) -> bool:
        """
        Xóa dữ liệu khỏi cache và thông báo cho observers
        
        Args:
            category (str): Danh mục dữ liệu
            key (str, optional): Khóa dữ liệu, nếu None sẽ xóa toàn bộ category
            
        Returns:
            bool: True nếu xóa thành công, False nếu không
        """
        with self.lock:
            # Nếu xóa toàn bộ category
            if key is None and category in self.cache:
                # Lưu lại danh sách keys để thông báo sau
                keys = list(self.cache[category].keys())
                
                # Xóa category
                result = super().delete(category)
                
                # Thông báo cho mỗi key đã xóa
                if result:
                    for k in keys:
                        self._notify_observers(category, k, None)
                
                return result
            
            # Nếu xóa một key cụ thể
            if (category in self.cache and 
                key in self.cache[category]):
                # Xóa key
                result = super().delete(category, key)
                
                # Thông báo nếu xóa thành công
                if result:
                    self._notify_observers(category, key, None)
                
                return result
            
            return super().delete(category, key)
    
    def clear(self) -> bool:
        """
        Xóa toàn bộ cache và thông báo cho tất cả observers
        
        Returns:
            bool: True nếu xóa thành công, False nếu không
        """
        with self.lock:
            # Lưu lại toàn bộ cấu trúc cache để thông báo sau
            cache_copy = {}
            for category, items in self.cache.items():
                cache_copy[category] = list(items.keys())
            
            # Xóa toàn bộ cache
            result = super().clear()
            
            # Thông báo cho tất cả keys đã xóa
            if result:
                for category, keys in cache_copy.items():
                    for key in keys:
                        self._notify_observers(category, key, None)
            
            return result


def main():
    """Hàm chính để test DataCache và ObservableDataCache"""
    
    print("=== Test DataCache ===")
    
    # Tạo cache
    cache = DataCache(enable_disk_cache=True, cache_dir='test_cache')
    
    # Lưu dữ liệu
    cache.set('market', 'BTC', {'price': 50000, 'volume': 1000})
    cache.set('market', 'ETH', {'price': 3000, 'volume': 5000})
    cache.set('account', 'balance', {'BTC': 0.5, 'ETH': 10})
    
    # Đọc dữ liệu
    btc_data = cache.get('market', 'BTC')
    eth_data = cache.get('market', 'ETH')
    balance = cache.get('account', 'balance')
    
    print(f"BTC: {btc_data}")
    print(f"ETH: {eth_data}")
    print(f"Balance: {balance}")
    
    # Đọc dữ liệu không tồn tại
    sol_data = cache.get('market', 'SOL', {'price': 0, 'volume': 0})
    print(f"SOL (default): {sol_data}")
    
    # Hiển thị thống kê
    stats = cache.get_stats()
    print(f"Stats: {stats}")
    
    # Lưu ra đĩa
    cache.dump_to_disk()
    
    print("\n=== Test ObservableDataCache ===")
    
    # Callback khi có thay đổi
    def on_change(category, key, data):
        print(f"Change: {category}/{key} = {data}")
    
    # Callback khi giá BTC thay đổi
    def on_btc_change(category, key, data):
        print(f"BTC price changed: {data['price'] if data else 'deleted'}")
    
    # Callback khi có thay đổi về giá
    def on_price_change(category, key, data):
        if key.endswith('_price'):
            coin = key.split('_')[0]
            print(f"{coin} price: {data}")
    
    # Tạo observable cache
    obs_cache = ObservableDataCache()
    
    # Đăng ký observers
    obs_cache.register_observer('market', 'BTC', on_btc_change)
    obs_cache.register_pattern_observer('market/*', on_change)
    obs_cache.register_pattern_observer('market/*_price', on_price_change)
    
    # Lưu dữ liệu và kích hoạt observer
    print("\nSetting BTC data:")
    obs_cache.set('market', 'BTC', {'price': 51000, 'volume': 1200})
    
    print("\nSetting ETH data:")
    obs_cache.set('market', 'ETH', {'price': 3100, 'volume': 5200})
    
    print("\nSetting individual prices:")
    obs_cache.set('market', 'BTC_price', 52000)
    obs_cache.set('market', 'ETH_price', 3200)
    
    print("\nDeleting BTC data:")
    obs_cache.delete('market', 'BTC')


if __name__ == "__main__":
    main()