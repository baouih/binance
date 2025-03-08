# Đối Phó Với Các Lỗi Tiềm Ẩn Trong Hệ Thống Giao Dịch

## Các Trường Hợp Lỗi Nghiêm Trọng Cần Xử Lý

### 1. Lỗi Khi Thị Trường Di Chuyển Đột Ngột

#### Vấn đề: 
Flash crash hoặc pump đột ngột có thể gây ra cập nhật giá không kịp thời, dẫn đến mất cơ hội chốt lời hoặc dừng lỗ.

#### Giải pháp:
```python
# Thêm kiểm tra giá di chuyển đột ngột trong EnhancedTrailingStopManager
def update_price(self, symbol: str, current_price: float, timestamp: Optional[datetime] = None) -> None:
    if symbol in self.last_prices:
        last_price = self.last_prices[symbol]
        # Kiểm tra sự thay đổi giá đột ngột >5%
        price_change_pct = abs(current_price - last_price) / last_price * 100
        if price_change_pct > 5.0:
            logger.warning(f"Phát hiện di chuyển giá đột ngột: {symbol} thay đổi {price_change_pct:.2f}%")
            # Xử lý theo cách đặc biệt cho trường hợp này
            self._handle_extreme_price_move(symbol, last_price, current_price, price_change_pct)
    
    # Tiếp tục xử lý cập nhật giá bình thường
    # ...

def _handle_extreme_price_move(self, symbol, last_price, current_price, change_pct):
    # Ưu tiên xử lý vị thế có rủi ro cao
    positions_at_risk = []
    for tracking_id, stop_data in self.active_stops.items():
        if stop_data['symbol'] != symbol:
            continue
        
        direction = stop_data['direction']
        entry_price = stop_data['entry_price']
        
        # Xác định vị thế có nguy cơ bị lỗ
        if (direction == 'long' and current_price < last_price) or \
           (direction == 'short' and current_price > last_price):
            positions_at_risk.append((tracking_id, stop_data))
    
    # Xử lý các vị thế bị ảnh hưởng
    for tracking_id, stop_data in positions_at_risk:
        # Điều chỉnh trailing stop để bảo vệ lợi nhuận tốt hơn
        if stop_data['trailing_active']:
            if stop_data['direction'] == 'long':
                # Di chuyển trailing stop gần hơn
                new_stop = current_price * (1 - (self.min_profit_protection / 100))
                if new_stop > stop_data['trailing_stop_price']:
                    stop_data['trailing_stop_price'] = new_stop
                    logger.info(f"Di chuyển trailing stop trong biến động mạnh: {tracking_id} -> {new_stop}")
            else:  # short
                new_stop = current_price * (1 + (self.min_profit_protection / 100))
                if new_stop < stop_data['trailing_stop_price']:
                    stop_data['trailing_stop_price'] = new_stop
                    logger.info(f"Di chuyển trailing stop trong biến động mạnh: {tracking_id} -> {new_stop}")
```

### 2. Lỗi Khi API Không Khả Dụng

#### Vấn đề:
Kết nối API bị gián đoạn, gây mất đồng bộ giữa trạng thái lệnh trong hệ thống và trên sàn.

#### Giải pháp:
```python
# Thêm cơ chế thử lại và dự phòng cho API
def _update_stop_loss_order(self, tracking_id: str, new_stop_price: float) -> bool:
    if not self.api_client:
        return False
    
    max_retries = 3
    retry_delay = 1.0  # giây
    
    for attempt in range(max_retries):
        try:
            # Thử cập nhật stop loss
            stop_data = self.active_stops[tracking_id]
            symbol = stop_data['symbol']
            direction = stop_data['direction']
            
            # Hủy lệnh cũ và đặt lệnh mới
            # ...
            
            logger.info(f"Đã cập nhật stop loss cho {tracking_id} tại {new_stop_price}")
            return True
            
        except Exception as e:
            # Xử lý thử lại
            if attempt < max_retries - 1:
                logger.warning(f"Lỗi khi cập nhật stop loss (thử lần {attempt+1}): {str(e)}")
                time.sleep(retry_delay * (2 ** attempt))  # Thời gian chờ tăng dần
            else:
                # Sau khi thử tối đa, ghi lại lỗi
                logger.error(f"Không thể cập nhật stop loss sau {max_retries} lần thử: {str(e)}")
                
                # Lưu trạng thái để đồng bộ lại sau
                self._record_pending_update(tracking_id, "stop_loss", new_stop_price)
                
                # Kích hoạt chế độ dự phòng nếu cần
                self._activate_fallback_mode(tracking_id)
                
                return False
    
    return False

def _record_pending_update(self, tracking_id: str, update_type: str, value: float):
    """Ghi lại các cập nhật đang chờ xử lý để thử lại sau"""
    if not hasattr(self, 'pending_updates'):
        self.pending_updates = {}
    
    if tracking_id not in self.pending_updates:
        self.pending_updates[tracking_id] = []
    
    self.pending_updates[tracking_id].append({
        'update_type': update_type,
        'value': value,
        'timestamp': datetime.now().isoformat()
    })
    
    logger.info(f"Đã ghi nhận cập nhật chờ xử lý: {tracking_id} - {update_type}")

def _sync_pending_updates(self):
    """Đồng bộ hóa các cập nhật đang chờ xử lý"""
    if not hasattr(self, 'pending_updates') or not self.pending_updates:
        return
    
    if not self.api_client:
        return
    
    for tracking_id, updates in list(self.pending_updates.items()):
        if tracking_id not in self.active_stops:
            # Vị thế đã đóng, xóa các cập nhật đang chờ
            del self.pending_updates[tracking_id]
            continue
        
        # Xử lý từng cập nhật theo thứ tự thời gian
        for update in sorted(updates, key=lambda x: x['timestamp']):
            success = False
            
            if update['update_type'] == 'stop_loss':
                success = self._update_stop_loss_order(tracking_id, update['value'])
            
            if success:
                # Xóa cập nhật đã xử lý thành công
                updates.remove(update)
    
    # Dọn dẹp các mục trống
    self.pending_updates = {k: v for k, v in self.pending_updates.items() if v}
```

### 3. Lỗi Khi Phát Hiện Thị Trường Sideway Không Chính Xác

#### Vấn đề:
Phát hiện sideway không chính xác có thể dẫn đến sử dụng chiến lược không phù hợp.

#### Giải pháp:
```python
# Cải thiện độ chính xác phát hiện thị trường sideway
def detect_sideways_market(self, df: pd.DataFrame, window: int = 20) -> bool:
    if len(df) < window * 2:
        logger.warning("Không đủ dữ liệu để phát hiện thị trường sideway")
        return False
    
    # Thêm nhiều chỉ báo để phát hiện chính xác hơn
    scores = []
    
    # 1. Kiểm tra biên độ dao động thấp
    atr = self._calculate_atr(df, window)
    avg_price = df['close'].iloc[-window:].mean()
    volatility_ratio = atr / avg_price
    
    volatility_score = 1 - min(volatility_ratio / self.volatility_threshold, 1)
    scores.append(volatility_score)
    
    # 2. Kiểm tra Bollinger Squeeze
    bb_squeeze = self._detect_bollinger_squeeze(df, window)
    scores.append(bb_squeeze)
    
    # 3. Kiểm tra ADX thấp (không có xu hướng)
    adx = self._calculate_adx(df, window)
    adx_score = 1 - min(adx / self.adx_threshold, 1)
    scores.append(adx_score)
    
    # 4. Thêm: Kiểm tra slope của giá
    last_n_prices = df['close'].iloc[-window:].values
    slope, _, _, _, _ = stats.linregress(range(len(last_n_prices)), last_n_prices)
    normalized_slope = abs(slope / avg_price) * window
    slope_score = 1 - min(normalized_slope / 0.05, 1)  # 5% thay đổi trên cửa sổ được coi là xu hướng
    scores.append(slope_score)
    
    # 5. Thêm: Kiểm tra phân phối giá trong khoảng hẹp
    price_range = (df['high'].iloc[-window:].max() - df['low'].iloc[-window:].min()) / avg_price * 100
    range_score = 1 - min(price_range / 5.0, 1)  # 5% range được coi là sideway
    scores.append(range_score)
    
    # Gán trọng số cho các chỉ báo (đánh giá cao hơn các chỉ báo quan trọng)
    weights = [0.25, 0.2, 0.25, 0.15, 0.15]
    weighted_scores = [score * weight for score, weight in zip(scores, weights)]
    
    # Tính điểm trung bình có trọng số
    self.sideways_score = sum(weighted_scores) / sum(weights)
    
    # Thêm điều kiện bổ sung: Đảm bảo biến động thực sự thấp
    must_be_low_volatility = volatility_ratio < self.volatility_threshold * 1.2
    
    # Phát hiện sideway dựa trên điểm và điều kiện bổ sung
    self.is_sideways = self.sideways_score > 0.6 and must_be_low_volatility
    
    logger.info(f"Phát hiện thị trường sideway: {self.is_sideways} (Score: {self.sideways_score:.2f})")
    return self.is_sideways
```

### 4. Lỗi Rò Rỉ Bộ Nhớ Khi Chạy Liên Tục

#### Vấn đề:
Hệ thống chạy liên tục trong thời gian dài có thể dẫn đến rò rỉ bộ nhớ do không giải phóng tài nguyên.

#### Giải pháp:
```python
# Cải thiện quản lý bộ nhớ
class EnhancedTrailingStopManager:
    def __init__(self, config_path: str = 'configs/trailing_stop_config.json', api_client=None):
        # ... code khởi tạo khác ...
        
        # Thêm giới hạn kích thước lịch sử
        self.max_history_size = 1000
        self.price_history_cleanup_interval = 100  # Số lần cập nhật giữa mỗi lần dọn dẹp
        self.update_counter = 0
        
    def update_price(self, symbol: str, current_price: float, timestamp: Optional[datetime] = None) -> None:
        # ... code xử lý cập nhật ...
        
        # Đếm số lần cập nhật và thực hiện dọn dẹp định kỳ
        self.update_counter += 1
        if self.update_counter % self.price_history_cleanup_interval == 0:
            self._cleanup_resources()
    
    def _cleanup_resources(self):
        """Dọn dẹp tài nguyên để tránh rò rỉ bộ nhớ"""
        # Giới hạn kích thước lịch sử giá
        for symbol in list(self.price_history.keys()):
            if len(self.price_history[symbol]) > self.max_history_size:
                # Giữ lại dữ liệu gần đây nhất
                self.price_history[symbol] = self.price_history[symbol][-self.max_history_size:]
        
        # Xóa dữ liệu thị trường cũ
        current_time = datetime.now()
        symbols_to_check = list(self.market_regimes.keys())
        
        for symbol in symbols_to_check:
            # Xóa dữ liệu thị trường cũ hơn 24 giờ và không có vị thế đang mở
            if symbol in self.market_regimes:
                regime_time = datetime.fromisoformat(self.market_regimes[symbol]['updated_at'])
                has_active_positions = any(
                    stop_data['symbol'] == symbol for stop_data in self.active_stops.values()
                )
                
                if not has_active_positions and (current_time - regime_time).total_seconds() > 86400:
                    del self.market_regimes[symbol]
                    logger.debug(f"Đã xóa dữ liệu thị trường cũ cho {symbol}")
        
        # Xác định các position_id không hợp lệ
        invalid_position_ids = []
        for position_id in list(self.active_stops.keys()):
            position = self.active_stops[position_id]
            if position.get('close_time'):  # Đã đóng nhưng chưa xóa
                invalid_position_ids.append(position_id)
        
        # Xóa các position_id không hợp lệ
        for position_id in invalid_position_ids:
            if position_id in self.active_stops:
                del self.active_stops[position_id]
                logger.debug(f"Đã xóa vị thế đã đóng {position_id} khỏi active_stops")
        
        # Buộc garbage collection nếu cần
        import gc
        gc.collect()
        
        logger.debug(f"Đã thực hiện dọn dẹp tài nguyên: {len(invalid_position_ids)} vị thế đã xóa")
```

### 5. Lỗi Xung Đột Trong Môi Trường Đa Luồng

#### Vấn đề:
Nhiều luồng truy cập cùng lúc có thể gây ra race condition và tham chiếu không nhất quán.

#### Giải pháp:
```python
# Cải thiện an toàn đa luồng
# Thay đổi trong phương thức update_price
def update_price(self, symbol: str, current_price: float, timestamp: Optional[datetime] = None) -> None:
    if timestamp is None:
        timestamp = datetime.now()
    
    positions_to_close = []
    
    with self.lock:  # Sử dụng khóa đồng bộ
        # Cập nhật giá mới nhất
        self.last_prices[symbol] = current_price
        
        # Lưu vào lịch sử giá
        if symbol not in self.price_history:
            self.price_history[symbol] = []
            
        self.price_history[symbol].append({
            'price': current_price,
            'timestamp': timestamp.isoformat()
        })
        
        # Giới hạn kích thước lịch sử giá
        max_history = self.volatility_measure_window * 10
        if len(self.price_history[symbol]) > max_history:
            self.price_history[symbol] = self.price_history[symbol][-max_history:]
        
        # Kiểm tra và cập nhật tất cả trạng thái trailing stop
        for tracking_id, stop_data in self.active_stops.items():
            if stop_data['symbol'] == symbol:
                triggered, action_type = self._process_trailing_stop(tracking_id, current_price, timestamp)
                if triggered:
                    positions_to_close.append((tracking_id, action_type))
    
    # Thực hiện đóng vị thế bên ngoài khối lock để tránh deadlock
    for tracking_id, action_type in positions_to_close:
        self._execute_stop(tracking_id, action_type)

# Đảm bảo các hoạt động đọc/ghi đều được bảo vệ bởi lock
def get_position_info(self, tracking_id: str) -> Optional[Dict]:
    """
    Lấy thông tin vị thế cụ thể
    
    Args:
        tracking_id (str): ID theo dõi
        
    Returns:
        Optional[Dict]: Thông tin vị thế hoặc None nếu không tìm thấy
    """
    with self.lock:
        return self.active_stops.get(tracking_id, {}).copy()
```

## Áp Dụng Best Practices Để Tăng Độ Ổn Định

### 1. Ghi Log Chi Tiết

```python
# Cải thiện ghi log
def __init__(self, ...):
    # Thiết lập logging chi tiết hơn
    log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    # Tạo một file handler riêng cho lỗi
    error_handler = logging.FileHandler('logs/error.log')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(log_formatter)
    
    # Thêm handler vào logger
    logger = logging.getLogger('trailing_stop')
    logger.addHandler(error_handler)
```

### 2. Bảo Vệ Dữ Liệu Quan Trọng

```python
# Sao lưu dữ liệu định kỳ
def _backup_active_positions(self):
    """Sao lưu vị thế đang hoạt động để khôi phục trong trường hợp lỗi"""
    backup_path = 'backups/active_positions.json'
    os.makedirs('backups', exist_ok=True)
    
    with self.lock:
        with open(backup_path, 'w') as f:
            positions_data = {
                'timestamp': datetime.now().isoformat(),
                'positions': self.active_stops,
                'last_prices': self.last_prices
            }
            json.dump(positions_data, f, indent=4)
    
    logger.debug(f"Đã sao lưu {len(self.active_stops)} vị thế đang hoạt động")

def restore_from_backup(self):
    """Khôi phục từ sao lưu trong trường hợp lỗi"""
    backup_path = 'backups/active_positions.json'
    if not os.path.exists(backup_path):
        logger.warning("Không tìm thấy file sao lưu để khôi phục")
        return False
    
    try:
        with open(backup_path, 'r') as f:
            backup_data = json.load(f)
        
        backup_time = datetime.fromisoformat(backup_data['timestamp'])
        positions = backup_data['positions']
        last_prices = backup_data.get('last_prices', {})
        
        # Kiểm tra tính hợp lệ của dữ liệu sao lưu
        if (datetime.now() - backup_time).total_seconds() > 3600:  # Sao lưu cũ hơn 1 giờ
            logger.warning(f"Sao lưu quá cũ: {backup_time}")
            return False
        
        with self.lock:
            self.active_stops = positions
            self.last_prices.update(last_prices)
        
        logger.info(f"Đã khôi phục {len(positions)} vị thế từ sao lưu")
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi khôi phục từ sao lưu: {str(e)}")
        return False
```

### 3. Chiến Lược Tự Phục Hồi

```python
# Thêm cơ chế tự phục hồi
def _activate_fallback_mode(self, tracking_id: str):
    """Kích hoạt chế độ dự phòng khi API không khả dụng"""
    with self.lock:
        stop_data = self.active_stops.get(tracking_id)
        if not stop_data:
            return
        
        # Đánh dấu vị thế đang ở chế độ dự phòng
        stop_data['fallback_mode'] = True
        stop_data['fallback_activated_at'] = datetime.now().isoformat()
        
        # Lưu trạng thái trailing hiện tại
        if stop_data['trailing_active']:
            stop_data['fallback_stop_price'] = stop_data['trailing_stop_price']
        
        logger.warning(f"Đã kích hoạt chế độ dự phòng cho vị thế {tracking_id}")

def _check_price_in_fallback_mode(self, tracking_id: str, current_price: float) -> bool:
    """
    Kiểm tra giá trong chế độ dự phòng
    
    Returns:
        bool: True nếu cần đóng vị thế
    """
    with self.lock:
        stop_data = self.active_stops.get(tracking_id)
        if not stop_data or not stop_data.get('fallback_mode'):
            return False
        
        direction = stop_data['direction']
        
        # Kiểm tra dựa trên giá
        if stop_data.get('fallback_stop_price'):
            if (direction == 'long' and current_price <= stop_data['fallback_stop_price']) or \
               (direction == 'short' and current_price >= stop_data['fallback_stop_price']):
                logger.info(f"Kích hoạt đóng vị thế trong chế độ dự phòng: {tracking_id}")
                return True
        
        # Thoát chế độ dự phòng nếu có thể
        if self.api_client:
            try:
                # Thử gọi API đơn giản để kiểm tra kết nối
                response = self.api_client.get_symbol_info(symbol=stop_data['symbol'])
                if response:
                    # API đã khôi phục, thoát chế độ dự phòng
                    stop_data.pop('fallback_mode', None)
                    logger.info(f"Đã thoát chế độ dự phòng cho vị thế {tracking_id}")
                    
                    # Đồng bộ lại thông tin
                    self._sync_pending_updates()
            except:
                # API vẫn không khả dụng
                pass
                
        return False
```

### 4. Xác Thực Dữ Liệu

```python
# Xác thực dữ liệu đầu vào
def register_position(self, symbol: str, order_id: str, entry_price: float, 
                      position_size: float, direction: str = 'long',
                      stop_loss_price: Optional[float] = None,
                      take_profit_price: Optional[float] = None) -> str:
    """
    Đăng ký vị thế để theo dõi trailing stop
    """
    # Xác thực đầu vào
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Symbol phải là chuỗi không rỗng")
    
    if not order_id or not isinstance(order_id, str):
        raise ValueError("Order ID phải là chuỗi không rỗng")
    
    if not isinstance(entry_price, (int, float)) or entry_price <= 0:
        raise ValueError("Entry price phải là số dương")
    
    if not isinstance(position_size, (int, float)) or position_size <= 0:
        raise ValueError("Position size phải là số dương")
    
    if direction not in ['long', 'short']:
        raise ValueError("Direction phải là 'long' hoặc 'short'")
    
    if stop_loss_price is not None:
        if not isinstance(stop_loss_price, (int, float)) or stop_loss_price <= 0:
            raise ValueError("Stop loss price phải là số dương")
        
        # Kiểm tra stop loss hợp lệ
        if direction == 'long' and stop_loss_price >= entry_price:
            raise ValueError("Stop loss price phải thấp hơn entry price cho lệnh long")
        elif direction == 'short' and stop_loss_price <= entry_price:
            raise ValueError("Stop loss price phải cao hơn entry price cho lệnh short")
    
    if take_profit_price is not None:
        if not isinstance(take_profit_price, (int, float)) or take_profit_price <= 0:
            raise ValueError("Take profit price phải là số dương")
        
        # Kiểm tra take profit hợp lệ
        if direction == 'long' and take_profit_price <= entry_price:
            raise ValueError("Take profit price phải cao hơn entry price cho lệnh long")
        elif direction == 'short' and take_profit_price >= entry_price:
            raise ValueError("Take profit price phải thấp hơn entry price cho lệnh short")
    
    # Tiếp tục code đăng ký...
```