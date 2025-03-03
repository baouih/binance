"""
Order Manager - Module quản lý lệnh chờ và xác nhận tín hiệu

Module này cung cấp các tính năng:
1. Xác nhận tín hiệu qua nhiều khung thời gian trước khi vào lệnh
2. Quản lý lệnh chờ và hủy lệnh khi điều kiện thị trường thay đổi
3. Tìm điểm vào lệnh tối ưu dựa trên phân tích kỹ thuật
"""

import os
import json
import time
import logging
import threading
from typing import Dict, List, Tuple, Union, Optional
from datetime import datetime, timedelta

logger = logging.getLogger('order_manager')

class OrderManager:
    """Quản lý xác nhận tín hiệu và lệnh chờ"""
    
    def __init__(self, 
                 signal_confirmation_threshold: int = 2,  # Số lần xác nhận tín hiệu cần thiết
                 signal_valid_period: int = 300,  # Thời gian hiệu lực của tín hiệu (giây)
                 pending_order_timeout: int = 1800,  # Thời gian timeout cho lệnh chờ (giây)
                 storage_path: str = 'data/signals'):
        """
        Khởi tạo Order Manager
        
        Args:
            signal_confirmation_threshold: Số lần phải xác nhận tín hiệu trước khi vào lệnh
            signal_valid_period: Thời gian (giây) mà tín hiệu còn hiệu lực
            pending_order_timeout: Thời gian (giây) trước khi hủy lệnh chờ
            storage_path: Đường dẫn lưu trữ dữ liệu tín hiệu
        """
        self.signal_confirmation_threshold = signal_confirmation_threshold
        self.signal_valid_period = signal_valid_period
        self.pending_order_timeout = pending_order_timeout
        self.storage_path = storage_path
        
        # Đảm bảo thư mục lưu trữ tồn tại
        os.makedirs(storage_path, exist_ok=True)
        
        # Khởi tạo các dict lưu trữ tín hiệu và lệnh chờ
        self.pending_signals = {}  # Dict lưu tín hiệu chờ xác nhận
        self.pending_orders = {}   # Dict lưu lệnh đang chờ thực thi
        self.confirmed_signals = {}  # Dict lưu tín hiệu đã xác nhận
        
        # Tải dữ liệu từ file nếu có
        self._load_data()
        
        # Bắt đầu thread kiểm tra định kỳ
        self._start_background_checker()
    
    def register_signal(self, 
                       symbol: str,
                       action: str,  # 'BUY' hoặc 'SELL'
                       price: float,
                       indicators: Dict,
                       source: str = 'primary') -> Dict:
        """
        Đăng ký tín hiệu mới để chờ xác nhận
        
        Args:
            symbol: Cặp giao dịch (ví dụ: 'BTCUSDT')
            action: Hành động (BUY/SELL)
            price: Giá tại thời điểm tạo tín hiệu
            indicators: Dict các chỉ báo kỹ thuật hỗ trợ tín hiệu
            source: Nguồn tín hiệu (primary/secondary/confirmation)
            
        Returns:
            Dict: Thông tin tín hiệu đã đăng ký
        """
        timestamp = datetime.now()
        signal_id = f"{symbol}_{action}_{int(timestamp.timestamp())}"
        
        # Kiểm tra tín hiệu đối nghịch gần đây
        opposite_action = 'SELL' if action == 'BUY' else 'BUY'
        opposite_key = f"{symbol}_{opposite_action}"
        
        # Nếu có tín hiệu đối nghịch trong pending_signals, xem xét loại bỏ
        opposite_signals = [s for s in self.pending_signals.values() 
                           if s['symbol'] == symbol and s['action'] == opposite_action]
        
        if opposite_signals:
            logger.info(f"Phát hiện {len(opposite_signals)} tín hiệu {opposite_action} đối nghịch với {action} mới")
            # Chỉ giữ lại tín hiệu đối nghịch nếu chúng rất mạnh (xác nhận > 1)
            for opp_signal in opposite_signals:
                if opp_signal['confirmations'] <= 1:
                    logger.info(f"Hủy tín hiệu đối nghịch yếu: {opp_signal['id']}")
                    self.pending_signals.pop(opp_signal['id'], None)
        
        # Tạo tín hiệu mới
        signal = {
            'id': signal_id,
            'symbol': symbol,
            'action': action,
            'price': price,
            'timestamp': timestamp.isoformat(),
            'expiry': (timestamp + timedelta(seconds=self.signal_valid_period)).isoformat(),
            'indicators': indicators,
            'confirmations': 1,
            'sources': [source],
            'status': 'pending'  # pending, confirmed, expired, executed
        }
        
        # Kiểm tra xem đã có tín hiệu cùng loại chưa
        existing_signals = [s for s in self.pending_signals.values() 
                           if s['symbol'] == symbol and s['action'] == action]
        
        if existing_signals:
            # Nếu có, tăng số lần xác nhận cho tín hiệu gần nhất
            latest_signal = max(existing_signals, key=lambda s: datetime.fromisoformat(s['timestamp']))
            latest_signal['confirmations'] += 1
            latest_signal['sources'].append(source)
            
            # Cập nhật thời gian hết hạn
            latest_signal['expiry'] = (timestamp + timedelta(seconds=self.signal_valid_period)).isoformat()
            
            logger.info(f"Tăng xác nhận tín hiệu {latest_signal['id']} lên {latest_signal['confirmations']}")
            
            # Nếu đạt ngưỡng xác nhận, chuyển sang trạng thái confirmed
            if latest_signal['confirmations'] >= self.signal_confirmation_threshold:
                self._confirm_signal(latest_signal['id'])
            
            return latest_signal
        else:
            # Nếu không, thêm tín hiệu mới
            self.pending_signals[signal_id] = signal
            logger.info(f"Đăng ký tín hiệu mới: {signal_id}, cần thêm {self.signal_confirmation_threshold-1} xác nhận")
            
            # Lưu dữ liệu
            self._save_data()
            
            return signal
    
    def _confirm_signal(self, signal_id: str) -> Optional[Dict]:
        """
        Xác nhận tín hiệu và chuyển sang trạng thái sẵn sàng vào lệnh
        
        Args:
            signal_id: ID của tín hiệu cần xác nhận
            
        Returns:
            Dict: Tín hiệu đã xác nhận hoặc None nếu không tìm thấy
        """
        if signal_id not in self.pending_signals:
            logger.warning(f"Không tìm thấy tín hiệu {signal_id} để xác nhận")
            return None
        
        signal = self.pending_signals.pop(signal_id)
        signal['status'] = 'confirmed'
        signal['confirmed_at'] = datetime.now().isoformat()
        
        # Tính toán điểm vào lệnh tối ưu dựa trên phân tích kỹ thuật
        optimized_entry = self._calculate_optimal_entry(signal)
        signal['optimized_entry'] = optimized_entry
        
        # Xác định mức stop loss và take profit phù hợp
        if signal['action'] == 'BUY':
            signal['stop_loss'] = optimized_entry['price'] * 0.985  # -1.5%
            signal['take_profit'] = optimized_entry['price'] * 1.03  # +3%
        else:  # SELL
            signal['stop_loss'] = optimized_entry['price'] * 1.015  # +1.5%
            signal['take_profit'] = optimized_entry['price'] * 0.97  # -3%
        
        self.confirmed_signals[signal_id] = signal
        logger.info(f"Đã xác nhận tín hiệu {signal_id} với điểm vào tối ưu: {optimized_entry['price']}")
        
        # Lưu dữ liệu
        self._save_data()
        
        return signal
    
    def _calculate_optimal_entry(self, signal: Dict) -> Dict:
        """
        Tính toán điểm vào lệnh tối ưu dựa trên phân tích kỹ thuật
        
        Args:
            signal: Tín hiệu đã đăng ký
            
        Returns:
            Dict: Thông tin điểm vào tối ưu
        """
        # TODO: Triển khai logic phân tích kỹ thuật thực sự
        # Trong phiên bản đơn giản, chỉ sử dụng giá hiện tại với nhỏ chênh lệch
        current_price = signal['price']
        action = signal['action']
        
        # Chênh lệch nhỏ để tạo lệnh giới hạn thay vì lệnh thị trường
        if action == 'BUY':
            # Đặt giá mua thấp hơn 0.1% so với giá hiện tại
            optimal_price = current_price * 0.999
        else:  # SELL
            # Đặt giá bán cao hơn 0.1% so với giá hiện tại
            optimal_price = current_price * 1.001
        
        return {
            'price': optimal_price,
            'valid_until': (datetime.now() + timedelta(seconds=self.pending_order_timeout)).isoformat(),
            'reason': 'Điểm vào tạo cơ hội lệnh giới hạn tốt hơn so với lệnh thị trường'
        }
    
    def register_pending_order(self, 
                             symbol: str,
                             action: str,
                             price: float,
                             quantity: float,
                             stop_loss: float,
                             take_profit: float,
                             order_id: str,
                             signal_id: Optional[str] = None) -> Dict:
        """
        Đăng ký lệnh đang chờ để theo dõi
        
        Args:
            symbol: Cặp giao dịch
            action: Hành động (BUY/SELL)
            price: Giá đặt lệnh
            quantity: Số lượng
            stop_loss: Mức stop loss
            take_profit: Mức take profit
            order_id: ID của lệnh từ sàn
            signal_id: ID của tín hiệu liên quan (nếu có)
            
        Returns:
            Dict: Thông tin lệnh chờ
        """
        timestamp = datetime.now()
        
        pending_order = {
            'id': order_id,
            'symbol': symbol,
            'action': action,
            'price': price,
            'quantity': quantity,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'timestamp': timestamp.isoformat(),
            'expiry': (timestamp + timedelta(seconds=self.pending_order_timeout)).isoformat(),
            'signal_id': signal_id,
            'status': 'pending',  # pending, filled, cancelled, expired
            'last_check': timestamp.isoformat()
        }
        
        self.pending_orders[order_id] = pending_order
        logger.info(f"Đăng ký lệnh chờ: {order_id} cho {symbol} {action} tại {price}")
        
        # Lưu dữ liệu
        self._save_data()
        
        return pending_order
    
    def update_order_status(self, order_id: str, status: str, 
                          fill_price: Optional[float] = None) -> Optional[Dict]:
        """
        Cập nhật trạng thái lệnh
        
        Args:
            order_id: ID của lệnh
            status: Trạng thái mới (filled, cancelled, expired)
            fill_price: Giá thực tế khi lệnh được khớp (nếu status='filled')
            
        Returns:
            Dict: Thông tin lệnh đã cập nhật hoặc None nếu không tìm thấy
        """
        if order_id not in self.pending_orders:
            logger.warning(f"Không tìm thấy lệnh {order_id} để cập nhật trạng thái")
            return None
        
        order = self.pending_orders[order_id]
        order['status'] = status
        order['last_check'] = datetime.now().isoformat()
        
        if status == 'filled' and fill_price is not None:
            order['fill_price'] = fill_price
            order['filled_at'] = datetime.now().isoformat()
            
            # Nếu có liên kết tới tín hiệu, cập nhật trạng thái của tín hiệu
            if order['signal_id'] and order['signal_id'] in self.confirmed_signals:
                self.confirmed_signals[order['signal_id']]['status'] = 'executed'
        
        elif status in ['cancelled', 'expired']:
            # Nếu lệnh bị hủy hoặc hết hạn, loại bỏ khỏi danh sách theo dõi
            self.pending_orders.pop(order_id)
        
        # Lưu dữ liệu
        self._save_data()
        
        return order
    
    def check_orders_need_cancel(self, 
                               market_data: Dict,
                               indicators: Dict) -> List[Dict]:
        """
        Kiểm tra các lệnh cần hủy do điều kiện thị trường thay đổi
        
        Args:
            market_data: Dữ liệu thị trường hiện tại
            indicators: Các chỉ báo kỹ thuật hiện tại
            
        Returns:
            List[Dict]: Danh sách các lệnh cần hủy
        """
        orders_to_cancel = []
        current_time = datetime.now()
        
        for order_id, order in list(self.pending_orders.items()):
            # Kiểm tra lệnh hết hạn
            if datetime.fromisoformat(order['expiry']) < current_time:
                order['cancel_reason'] = 'Lệnh hết hạn'
                orders_to_cancel.append(order)
                continue
            
            # Lấy symbol (không có USDT)
            symbol_base = order['symbol'].replace('USDT', '')
            
            # Kiểm tra sự thay đổi đáng kể trong chỉ báo kỹ thuật
            if symbol_base.lower() in indicators:
                current_indicators = indicators[symbol_base.lower()]
                
                # Nếu tín hiệu đối nghịch xuất hiện
                opposite_action = 'SELL' if order['action'] == 'BUY' else 'BUY'
                if current_indicators['type'] == opposite_action:
                    order['cancel_reason'] = f'Tín hiệu đối nghịch ({opposite_action}) xuất hiện'
                    orders_to_cancel.append(order)
                    continue
                
                # Nếu RSI thay đổi đáng kể
                if 'rsi' in current_indicators:
                    if (order['action'] == 'BUY' and current_indicators['rsi'] > 70) or \
                       (order['action'] == 'SELL' and current_indicators['rsi'] < 30):
                        order['cancel_reason'] = f"RSI thay đổi đáng kể: {current_indicators['rsi']}"
                        orders_to_cancel.append(order)
                        continue
            
            # Kiểm tra biến động giá lớn
            if symbol_base.lower() + '_price' in market_data:
                current_price = market_data[symbol_base.lower() + '_price']
                price_change_pct = abs(current_price - order['price']) / order['price'] * 100
                
                # Nếu giá thay đổi quá 2% so với giá đặt lệnh
                if price_change_pct > 2.0:
                    order['cancel_reason'] = f"Giá thay đổi {price_change_pct:.2f}% so với giá đặt lệnh"
                    orders_to_cancel.append(order)
            
        return orders_to_cancel
    
    def get_executable_signals(self) -> List[Dict]:
        """
        Lấy danh sách tín hiệu đã xác nhận và sẵn sàng thực thi
        
        Returns:
            List[Dict]: Danh sách tín hiệu sẵn sàng thực thi
        """
        executable = []
        current_time = datetime.now()
        
        for signal_id, signal in list(self.confirmed_signals.items()):
            # Kiểm tra tín hiệu còn hiệu lực
            if datetime.fromisoformat(signal['expiry']) < current_time:
                # Tín hiệu hết hạn
                signal['status'] = 'expired'
                logger.info(f"Tín hiệu {signal_id} đã hết hạn")
                continue
                
            # Kiểm tra tín hiệu đã thực thi chưa
            if signal['status'] == 'confirmed':
                executable.append(signal)
        
        return executable
    
    def _start_background_checker(self):
        """Bắt đầu thread kiểm tra định kỳ"""
        def checker_thread():
            while True:
                try:
                    # Kiểm tra các tín hiệu hết hạn
                    self._check_expired_signals()
                    
                    # Kiểm tra các lệnh hết hạn
                    self._check_expired_orders()
                    
                    # Lưu dữ liệu
                    self._save_data()
                except Exception as e:
                    logger.error(f"Lỗi trong thread kiểm tra: {str(e)}")
                
                # Ngủ 60s trước khi kiểm tra lại
                time.sleep(60)
        
        thread = threading.Thread(target=checker_thread, daemon=True)
        thread.start()
        logger.info("Đã khởi động thread kiểm tra tín hiệu và lệnh")
    
    def _check_expired_signals(self):
        """Kiểm tra và xử lý các tín hiệu hết hạn"""
        current_time = datetime.now()
        
        # Kiểm tra tín hiệu chờ xác nhận
        for signal_id, signal in list(self.pending_signals.items()):
            if datetime.fromisoformat(signal['expiry']) < current_time:
                # Loại bỏ tín hiệu hết hạn
                self.pending_signals.pop(signal_id)
                logger.info(f"Đã loại bỏ tín hiệu chờ hết hạn: {signal_id}")
        
        # Kiểm tra tín hiệu đã xác nhận
        for signal_id, signal in list(self.confirmed_signals.items()):
            if datetime.fromisoformat(signal['expiry']) < current_time:
                # Đánh dấu tín hiệu hết hạn
                signal['status'] = 'expired'
                logger.info(f"Đã đánh dấu tín hiệu xác nhận hết hạn: {signal_id}")
    
    def _check_expired_orders(self):
        """Kiểm tra và xử lý các lệnh hết hạn"""
        current_time = datetime.now()
        
        for order_id, order in list(self.pending_orders.items()):
            if datetime.fromisoformat(order['expiry']) < current_time:
                # Loại bỏ lệnh hết hạn
                self.pending_orders.pop(order_id)
                logger.info(f"Đã loại bỏ lệnh chờ hết hạn: {order_id}")
    
    def _save_data(self):
        """Lưu dữ liệu vào file"""
        data = {
            'pending_signals': self.pending_signals,
            'confirmed_signals': self.confirmed_signals,
            'pending_orders': self.pending_orders,
            'last_updated': datetime.now().isoformat()
        }
        
        try:
            with open(os.path.join(self.storage_path, 'order_manager_state.json'), 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu: {str(e)}")
    
    def _load_data(self):
        """Tải dữ liệu từ file"""
        file_path = os.path.join(self.storage_path, 'order_manager_state.json')
        
        if not os.path.exists(file_path):
            logger.info("Không tìm thấy file dữ liệu, sử dụng trạng thái mặc định")
            return
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            self.pending_signals = data.get('pending_signals', {})
            self.confirmed_signals = data.get('confirmed_signals', {})
            self.pending_orders = data.get('pending_orders', {})
            
            logger.info(f"Đã tải dữ liệu: {len(self.pending_signals)} tín hiệu chờ, "
                      f"{len(self.confirmed_signals)} tín hiệu xác nhận, "
                      f"{len(self.pending_orders)} lệnh chờ")
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu: {str(e)}")