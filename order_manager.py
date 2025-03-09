import os
import json
import uuid
import time
import logging
import threading
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('order_manager.log')
    ]
)
logger = logging.getLogger('order_manager')

class OrderManager:
    """
    Quản lý tín hiệu giao dịch và lệnh chờ
    
    Đảm bảo các tín hiệu giao dịch được xác nhận đủ trước khi vào lệnh,
    đồng thời quản lý các lệnh chờ và hủy lệnh khi điều kiện thị trường thay đổi.
    """
    
    def __init__(self, signal_confirmation_threshold: int = 2, 
               signal_valid_period: int = 300, 
               pending_order_timeout: int = 1800,
               storage_path: str = '.'):
        """
        Khởi tạo Order Manager
        
        Args:
            signal_confirmation_threshold: Số lần xác nhận cần thiết để tín hiệu được chấp nhận
            signal_valid_period: Thời gian hiệu lực của tín hiệu (giây)
            pending_order_timeout: Thời gian chờ tối đa cho lệnh chờ (giây)
            storage_path: Đường dẫn lưu trữ dữ liệu
        """
        self.signal_confirmation_threshold = signal_confirmation_threshold
        self.signal_valid_period = signal_valid_period
        self.pending_order_timeout = pending_order_timeout
        self.storage_path = storage_path
        
        # Dữ liệu tín hiệu và lệnh
        self.pending_signals = {}  # Tín hiệu đang chờ xác nhận
        self.confirmed_signals = {}  # Tín hiệu đã được xác nhận đủ
        self.pending_orders = {}  # Lệnh đang chờ khớp
        
        # Tạo thư mục lưu trữ nếu chưa tồn tại
        os.makedirs(storage_path, exist_ok=True)
        
        # Tải dữ liệu từ file (nếu có)
        self._load_data()
        
        # Khởi động thread kiểm tra định kỳ
        self._start_background_checker()
        
        logger.info("Đã khởi tạo Order Manager")
    
    def register_signal(self, symbol: str, action: str, price: float, indicators: Dict,
                      source: str = 'primary') -> Dict:
        """
        Đăng ký một tín hiệu giao dịch mới hoặc xác nhận tín hiệu hiện có
        
        Args:
            symbol: Cặp giao dịch
            action: Hành động (BUY/SELL)
            price: Giá tham chiếu
            indicators: Các chỉ báo kỹ thuật liên quan
            source: Nguồn tín hiệu (primary/secondary/...)
            
        Returns:
            Dict: Thông tin tín hiệu (bao gồm ID và trạng thái)
        """
        timestamp = datetime.now()
        
        # Tạo key duy nhất cho tín hiệu dựa trên symbol và action
        signal_key = f"{symbol}_{action}"
        
        # Kiểm tra xem đã có tín hiệu tương tự chờ xác nhận chưa
        matching_signal = None
        for signal_id, signal in self.pending_signals.items():
            if signal['symbol'] == symbol and signal['action'] == action:
                # Kiểm tra thời gian còn hiệu lực
                if datetime.fromisoformat(signal['expiry']) > timestamp:
                    matching_signal = signal
                    matching_signal_id = signal_id
                    break
        
        if matching_signal:
            # Cập nhật tín hiệu hiện có
            matching_signal['confirmations'] += 1
            matching_signal['last_price'] = price
            matching_signal['last_updated'] = timestamp.isoformat()
            matching_signal['sources'].append(source)
            
            # Nếu đủ số lần xác nhận, chuyển sang danh sách tín hiệu đã xác nhận
            if matching_signal['confirmations'] >= self.signal_confirmation_threshold:
                matching_signal['status'] = 'confirmed'
                
                # Tính toán điểm vào lệnh tối ưu
                optimal_entry = self._calculate_optimal_entry(matching_signal)
                matching_signal['optimal_entry'] = optimal_entry
                
                # Chuyển từ pending sang confirmed
                self.confirmed_signals[matching_signal_id] = matching_signal
                self.pending_signals.pop(matching_signal_id)
                
                logger.info(f"Tín hiệu {matching_signal_id} đã được xác nhận đủ, "
                          f"điểm vào tối ưu: {optimal_entry['price']}")
            else:
                logger.info(f"Tín hiệu {matching_signal_id} cập nhật: "
                          f"{matching_signal['confirmations']}/{self.signal_confirmation_threshold} xác nhận")
            
            signal = matching_signal
            signal['id'] = matching_signal_id
        else:
            # Tạo tín hiệu mới
            signal_id = str(uuid.uuid4())
            expiry = timestamp + timedelta(seconds=self.signal_valid_period)
            
            signal = {
                'id': signal_id,
                'symbol': symbol,
                'action': action,
                'price': price,
                'initial_price': price,
                'last_price': price,
                'timestamp': timestamp.isoformat(),
                'expiry': expiry.isoformat(),
                'indicators': indicators,
                'confirmations': 1,
                'sources': [source],
                'status': 'pending',  # pending, confirmed, executed, expired
                'last_updated': timestamp.isoformat()
            }
            
            self.pending_signals[signal_id] = signal
            logger.info(f"Đã đăng ký tín hiệu mới: {signal_id} ({symbol} {action})")
        
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
        current_price = signal['price']
        action = signal['action']
        indicators = signal.get('indicators', {})
        
        # Phân tích trend để xác định vùng giá tốt hơn
        trend = indicators.get('trend', 'neutral')
        rsi = indicators.get('rsi', 50.0)
        
        # Xác định vùng giá dựa trên trend và RSI
        # 1. Tìm vùng giá tối ưu dựa trên tín hiệu và chỉ báo
        price_adjustment = 0.0
        
        # Điều chỉnh giá dựa trên RSI
        if action == 'BUY':
            # Mua: Nếu RSI thấp, giảm điều chỉnh (mua gần giá hiện tại hơn)
            # Nếu RSI cao, tăng điều chỉnh (đặt mức mua thấp hơn)
            if rsi < 30:  # Rất quá bán
                price_adjustment = 0.001  # Giảm mức điều chỉnh, mua gần với giá hiện tại
            elif rsi < 40:  # Quá bán nhẹ
                price_adjustment = 0.003  # Điều chỉnh vừa phải
            else:  # RSI trung tính hoặc cao
                price_adjustment = 0.005  # Điều chỉnh lớn, chờ giá giảm sâu hơn
                
        else:  # SELL
            # Bán: Nếu RSI cao, giảm điều chỉnh (bán gần giá hiện tại hơn)
            # Nếu RSI thấp, tăng điều chỉnh (đặt mức bán cao hơn)
            if rsi > 70:  # Rất quá mua
                price_adjustment = 0.001  # Giảm mức điều chỉnh, bán gần với giá hiện tại 
            elif rsi > 60:  # Quá mua nhẹ
                price_adjustment = 0.003  # Điều chỉnh vừa phải
            else:  # RSI trung tính hoặc thấp
                price_adjustment = 0.005  # Điều chỉnh lớn, chờ giá tăng cao hơn
        
        # Điều chỉnh thêm dựa trên trend
        if trend == 'uptrend' and action == 'BUY':
            # Trong uptrend, mua với điều chỉnh ít hơn (mua sớm hơn)
            price_adjustment = max(0.001, price_adjustment * 0.7)
        elif trend == 'downtrend' and action == 'SELL':
            # Trong downtrend, bán với điều chỉnh ít hơn (bán sớm hơn)
            price_adjustment = max(0.001, price_adjustment * 0.7)
        elif trend == 'volatile':
            # Trong thị trường biến động, tăng mức điều chỉnh để tìm điểm vào tốt hơn
            price_adjustment = min(0.01, price_adjustment * 1.5)
        
        # Tính toán giá tối ưu dựa trên điều chỉnh
        if action == 'BUY':
            optimal_price = current_price * (1 - price_adjustment)
            reason = f'Mua tại mức giảm {price_adjustment*100:.2f}% từ giá hiện tại, '
            reason += f'dựa trên RSI={rsi:.1f} và xu hướng {trend}'
        else:  # SELL
            optimal_price = current_price * (1 + price_adjustment)
            reason = f'Bán tại mức tăng {price_adjustment*100:.2f}% từ giá hiện tại, '
            reason += f'dựa trên RSI={rsi:.1f} và xu hướng {trend}'
        
        # 2. Chia lệnh thành các phần (triển khai trong phiên bản sau)
        entry_parts = [
            {'percent': 40, 'price': optimal_price, 'description': 'Phần đầu vào điểm tối ưu'},
            {'percent': 30, 'price': current_price, 'description': 'Phần tiếp theo vào giá thị trường nếu xác nhận mạnh'},
            {'percent': 30, 'price': None, 'description': 'Phần dự phòng để theo dõi diễn biến'}
        ]
        
        return {
            'price': optimal_price,
            'valid_until': (datetime.now() + timedelta(seconds=self.pending_order_timeout)).isoformat(),
            'reason': reason,
            'entry_parts': entry_parts,
            'adjustment_percent': price_adjustment * 100
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
                
                # Kiểm tra biến động thị trường mạnh 
                # (chủ yếu là không vào lệnh trong thị trường biến động lớn)
                if 'trend' in current_indicators and current_indicators['trend'] == 'volatile':
                    order['cancel_reason'] = f"Thị trường đang biến động mạnh, không thích hợp cho lệnh này"
                    orders_to_cancel.append(order)
                    continue
                
                # Nếu tín hiệu đối nghịch xuất hiện
                opposite_action = 'SELL' if order['action'] == 'BUY' else 'BUY'
                if current_indicators.get('type') == opposite_action:
                    order['cancel_reason'] = f'Tín hiệu đối nghịch ({opposite_action}) xuất hiện'
                    orders_to_cancel.append(order)
                    continue
                
                # Nếu RSI thay đổi đáng kể
                if 'rsi' in current_indicators:
                    # Hủy lệnh khi RSI chạm ngưỡng ngược lại với tín hiệu ban đầu
                    if (order['action'] == 'BUY' and current_indicators['rsi'] > 70) or \
                       (order['action'] == 'SELL' and current_indicators['rsi'] < 30):
                        order['cancel_reason'] = f"RSI thay đổi đáng kể: {current_indicators['rsi']}"
                        orders_to_cancel.append(order)
                        continue
                
                # Nếu MACD thay đổi chiều của tín hiệu
                if 'macd' in current_indicators and 'macd_signal' in current_indicators:
                    # Với lệnh BUY, nếu MACD cắt xuống đường tín hiệu
                    if order['action'] == 'BUY' and current_indicators['macd'] < current_indicators['macd_signal']:
                        order['cancel_reason'] = "MACD cắt xuống đường tín hiệu, xu hướng tăng suy yếu"
                        orders_to_cancel.append(order)
                        continue
                    # Với lệnh SELL, nếu MACD cắt lên đường tín hiệu
                    elif order['action'] == 'SELL' and current_indicators['macd'] > current_indicators['macd_signal']:
                        order['cancel_reason'] = "MACD cắt lên đường tín hiệu, xu hướng giảm suy yếu"
                        orders_to_cancel.append(order)
                        continue
            
            # Kiểm tra biến động giá lớn
            if symbol_base.lower() + '_price' in market_data:
                current_price = market_data[symbol_base.lower() + '_price']
                if current_price > 0 and order['price'] > 0:  # Tránh lỗi chia cho 0
                    price_change_pct = abs(current_price - order['price']) / order['price'] * 100
                    
                    # Nếu giá chuyển động theo hướng bất lợi cho lệnh
                    if (order['action'] == 'BUY' and current_price > order['price'] * 1.02) or \
                       (order['action'] == 'SELL' and current_price < order['price'] * 0.98):
                        order['cancel_reason'] = f"Giá đã di chuyển {price_change_pct:.2f}% theo hướng bất lợi"
                        orders_to_cancel.append(order)
                        continue
                    
                    # Nếu giá thay đổi quá 2% so với giá đặt lệnh (theo bất kỳ hướng nào)
                    if price_change_pct > 2.0:
                        order['cancel_reason'] = f"Giá thay đổi {price_change_pct:.2f}% so với giá đặt lệnh"
                        orders_to_cancel.append(order)
            
            # Kiểm tra biến động khối lượng bất thường
            if symbol_base.lower() + '_volume' in market_data:
                current_volume = market_data[symbol_base.lower() + '_volume']
                avg_volume = market_data.get(symbol_base.lower() + '_avg_volume', current_volume)
                
                # Nếu khối lượng tăng đột biến (gấp 3 lần trung bình), thị trường có thể đang bất ổn
                if current_volume > avg_volume * 3:
                    order['cancel_reason'] = f"Khối lượng giao dịch tăng đột biến, thị trường bất ổn"
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
            
            
if __name__ == "__main__":
    # Test cơ bản OrderManager
    order_manager = OrderManager()
    
    # Đăng ký một tín hiệu
    signal = order_manager.register_signal(
        symbol="BTCUSDT",
        action="BUY",
        price=84000.0,
        indicators={
            "rsi": 32.5,
            "macd": 150.0,
            "trend": "uptrend"
        }
    )
    
    print(f"Đã đăng ký tín hiệu: {signal['id']}")
    
    # Đăng ký tín hiệu lần thứ 2 (xác nhận)
    signal = order_manager.register_signal(
        symbol="BTCUSDT",
        action="BUY",
        price=84100.0,
        indicators={
            "rsi": 33.5,
            "macd": 155.0,
            "trend": "uptrend"
        }
    )
    
    print(f"Tín hiệu sau khi xác nhận: {signal}")
    
    # Kiểm tra các tín hiệu sẵn sàng thực thi
    executable_signals = order_manager.get_executable_signals()
    print(f"Tín hiệu sẵn sàng thực thi: {len(executable_signals)}")
    
    if executable_signals:
        # Đăng ký lệnh chờ
        order = order_manager.register_pending_order(
            symbol="BTCUSDT",
            action="BUY",
            price=84050.0,
            quantity=0.01,
            stop_loss=83000.0,
            take_profit=86000.0,
            order_id="test_order_1",
            signal_id=executable_signals[0]['id']
        )
        
        print(f"Đã đăng ký lệnh chờ: {order['id']}")
        
        # Cập nhật trạng thái lệnh
        updated_order = order_manager.update_order_status(
            order_id="test_order_1",
            status="filled",
            fill_price=84055.0
        )
        
        print(f"Lệnh sau khi cập nhật: {updated_order}")