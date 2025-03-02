# Roadmap Tối Ưu Hóa Bot Giao Dịch Bitcoin

## Tổng quan hiện trạng

Bot giao dịch hiện tại đã có các chức năng mạnh mẽ như:
- Hệ thống quản lý vị thế đa dạng (Fixed, Dynamic, Kelly, Anti-Martingale, Portfolio)
- Thực thi lệnh linh hoạt (Market, Iceberg, TWAP, Scaled, OCO)
- Quản lý rủi ro đa lớp (Trailing Stop, Dynamic Take Profit, Daily Loss Limit)
- Phát hiện và thích nghi với chế độ thị trường
- Chuyển đổi từ Web UI sang CLI để tăng hiệu suất và ổn định

## Lộ trình nâng cấp

### 1. Cải tiến quản lý vị thế (Q2/2025)

#### 1.1 Thêm chiến lược Pythagorean Position Sizer
```python
class PythagoreanPositionSizer(BasePositionSizer):
    """Sử dụng công thức Pythagoras để cân bằng giữa lợi nhuận và rủi ro"""
    
    def calculate_position_size(self, current_price: float, account_balance: float = None, 
                              leverage: int = 1, volatility: float = None, market_data: Dict = None,
                              entry_price: float = None, stop_loss_price: float = None) -> float:
        """
        Tính toán kích thước vị thế sử dụng công thức Pythagoras
        
        Args:
            current_price (float): Giá hiện tại
            account_balance (float, optional): Số dư tài khoản
            leverage (int): Đòn bẩy
            volatility (float, optional): Độ biến động
            market_data (Dict, optional): Dữ liệu thị trường bổ sung
            entry_price (float, optional): Giá vào lệnh
            stop_loss_price (float, optional): Giá stop loss
            
        Returns:
            float: Kích thước vị thế (tính bằng quote currency)
        """
        # Tính win_rate và profit_factor từ lịch sử giao dịch
        win_rate = self.calculate_win_rate()
        profit_factor = self.calculate_profit_factor()
        
        # Tính toán vị thế cơ bản
        base_size = super().calculate_position_size(
            current_price, account_balance, leverage, volatility, 
            market_data, entry_price, stop_loss_price
        )
        
        # Điều chỉnh theo "công thức Pythagoras"
        pythagoras_factor = math.sqrt(win_rate * profit_factor)
        adjusted_size = base_size * pythagoras_factor
        
        # Giới hạn kích thước tối đa
        max_size = account_balance * (self.max_risk_percentage / 100) * leverage
        return min(adjusted_size, max_size)
    
    def calculate_win_rate(self) -> float:
        """Tính tỷ lệ thắng từ lịch sử giao dịch"""
        if len(self.trade_history) < 10:
            return 0.5  # Giá trị mặc định nếu không đủ dữ liệu
        
        winning_trades = sum(1 for trade in self.trade_history if trade.get('pnl', 0) > 0)
        return winning_trades / len(self.trade_history)
    
    def calculate_profit_factor(self) -> float:
        """Tính hệ số lợi nhuận (tổng lợi nhuận / tổng thua lỗ)"""
        if len(self.trade_history) < 10:
            return 1.5  # Giá trị mặc định nếu không đủ dữ liệu
        
        total_profit = sum(trade.get('pnl', 0) for trade in self.trade_history if trade.get('pnl', 0) > 0)
        total_loss = abs(sum(trade.get('pnl', 0) for trade in self.trade_history if trade.get('pnl', 0) < 0))
        
        return total_profit / total_loss if total_loss > 0 else 1.5
```

#### 1.2 Adaptive Position Sizing (Điều chỉnh theo thị trường và hiệu suất)
- Thêm điều chỉnh vị thế dựa trên chế độ thị trường, tốc độ biến động và độ sâu của thị trường
- Tích hợp phân tích hiệu suất theo thời gian để tự điều chỉnh kích thước vị thế

### 2. Nâng cao quản lý rủi ro (Q2/2025)

#### 2.1 Phân tích Monte Carlo
```python
class MonteCarloRiskAnalyzer:
    """Phân tích rủi ro sử dụng mô phỏng Monte Carlo"""
    
    def __init__(self, trade_history: List[Dict], default_risk: float = 1.0):
        self.trade_history = trade_history
        self.default_risk = default_risk
    
    def analyze(self, confidence_level: float = 0.95, simulations: int = 1000, 
              sequence_length: int = 20, max_risk_limit: float = 2.0) -> float:
        """
        Thực hiện phân tích Monte Carlo và đề xuất % rủi ro
        
        Args:
            confidence_level (float): Mức độ tin cậy (0-1)
            simulations (int): Số lần mô phỏng
            sequence_length (int): Độ dài chuỗi giao dịch để mô phỏng
            max_risk_limit (float): Giới hạn % rủi ro tối đa
            
        Returns:
            float: % rủi ro đề xuất
        """
        if len(self.trade_history) < 30:
            return self.default_risk  # Không đủ dữ liệu
        
        # Tính toán phân phối lợi nhuận/thua lỗ
        pnl_distribution = [trade.get('pnl_pct', 0) for trade in self.trade_history]
        
        # Mô phỏng Monte Carlo
        drawdowns = []
        for _ in range(simulations):
            # Lấy mẫu ngẫu nhiên từ phân phối lợi nhuận
            sample = random.choices(pnl_distribution, k=sequence_length)
            # Tính toán đường cong vốn
            equity_curve = [100]  # Bắt đầu với 100 đơn vị
            for pnl in sample:
                equity_curve.append(equity_curve[-1] * (1 + pnl/100))
            
            # Tính drawdown tối đa
            max_dd = self._calculate_max_drawdown(equity_curve)
            drawdowns.append(max_dd)
        
        # Tính toán VaR (Value at Risk) tại mức độ tin cậy
        var = sorted(drawdowns)[int(simulations * confidence_level)]
        
        # Điều chỉnh % rủi ro để drawdown kỳ vọng <= max_acceptable_drawdown
        max_acceptable_drawdown = 20  # 20% drawdown tối đa có thể chấp nhận
        suggested_risk = self.default_risk * (max_acceptable_drawdown / var)
        
        # Giới hạn % rủi ro
        return max(0.1, min(suggested_risk, max_risk_limit))
    
    def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """Tính drawdown tối đa từ đường cong vốn"""
        max_dd = 0
        peak = equity_curve[0]
        
        for value in equity_curve:
            if value > peak:
                peak = value
            
            dd = 100 * (peak - value) / peak
            max_dd = max(max_dd, dd)
        
        return max_dd
```

#### 2.2 Quản lý rủi ro theo thời gian
- Điều chỉnh % rủi ro và số lượng vị thế theo thời gian trong ngày
- Giảm rủi ro trước các sự kiện kinh tế quan trọng và tăng sau khi thị trường đã phản ứng

### 3. Phát hiện Market Regime nâng cao (Q3/2025)

#### 3.1 Fractal-based Market Regime Detection
```python
class FractalMarketRegimeDetector:
    """Phát hiện chế độ thị trường sử dụng phân tích fractal"""
    
    def __init__(self, lookback_periods: int = 100):
        self.lookback_periods = lookback_periods
        self.regimes = ["trending", "ranging", "volatile", "quiet", "choppy"]
    
    def detect_regime(self, price_data: pd.DataFrame) -> Dict:
        """
        Phát hiện chế độ thị trường dựa trên phân tích fractal
        
        Args:
            price_data (pd.DataFrame): Dữ liệu giá (OHLCV)
            
        Returns:
            Dict: Kết quả phát hiện với chế độ và độ tin cậy
        """
        if len(price_data) < self.lookback_periods:
            return {"regime": "unknown", "confidence": 0.0, "details": {}}
        
        # Trích xuất đặc trưng fractal và thống kê
        features = self._extract_features(price_data)
        
        # Tính điểm cho từng chế độ
        regime_scores = self._calculate_regime_scores(features)
        
        # Chọn chế độ có điểm cao nhất
        top_regime = max(regime_scores.items(), key=lambda x: x[1])
        total_score = sum(regime_scores.values())
        
        return {
            "regime": top_regime[0],
            "confidence": top_regime[1] / total_score if total_score > 0 else 0,
            "details": {
                "regime_scores": regime_scores,
                "features": features
            }
        }
    
    def _extract_features(self, price_data: pd.DataFrame) -> Dict:
        """Trích xuất các đặc trưng fractal và thống kê từ dữ liệu giá"""
        # Lấy dữ liệu đóng cửa
        close_prices = price_data['close'].values[-self.lookback_periods:]
        
        # Tính Hurst Exponent (chỉ số fractal)
        hurst = self._calculate_hurst_exponent(close_prices)
        
        # Tính chỉ số khác
        atr = self._calculate_atr(price_data)
        atr_ratio = atr / np.mean(close_prices[-20:]) * 100
        
        # Tính chỉ số xu hướng (ADX)
        adx = self._calculate_adx(price_data)
        
        # Độ dịch chuyển biến động
        volatility_shift = self._calculate_volatility_shift(price_data)
        
        # Tính logarithmic return distribution
        log_returns = np.diff(np.log(close_prices))
        skewness = stats.skew(log_returns)
        kurtosis = stats.kurtosis(log_returns)
        
        return {
            "hurst_exponent": hurst,
            "atr_ratio": atr_ratio,
            "adx": adx,
            "volatility_shift": volatility_shift,
            "return_skewness": skewness,
            "return_kurtosis": kurtosis
        }
    
    def _calculate_regime_scores(self, features: Dict) -> Dict:
        """Tính điểm cho từng chế độ thị trường dựa trên đặc trưng"""
        scores = {regime: 0.0 for regime in self.regimes}
        
        # ===== Trending =====
        # Trending thường có Hurst > 0.6 và ADX > 25
        if features["hurst_exponent"] > 0.6:
            scores["trending"] += (features["hurst_exponent"] - 0.6) * 10
        
        if features["adx"] > 25:
            scores["trending"] += (features["adx"] - 25) / 25
            
        # Phân phối lợi nhuận lệch (skewed)
        if abs(features["return_skewness"]) > 0.5:
            scores["trending"] += abs(features["return_skewness"]) - 0.5
        
        # ===== Ranging =====
        # Ranging thường có Hurst ~ 0.5 và ADX thấp
        if 0.45 <= features["hurst_exponent"] <= 0.55:
            scores["ranging"] += 1 - abs(features["hurst_exponent"] - 0.5) * 10
            
        if features["adx"] < 25:
            scores["ranging"] += (25 - features["adx"]) / 25
        
        # ===== Volatile =====
        # Volatile có ATR cao và volatility shift lớn
        if features["atr_ratio"] > 2:
            scores["volatile"] += features["atr_ratio"] / 2
            
        if features["volatility_shift"] > 1.5:
            scores["volatile"] += features["volatility_shift"] - 1
            
        # Kurtosis cao (fat tails)
        if features["return_kurtosis"] > 3:
            scores["volatile"] += (features["return_kurtosis"] - 3) / 3
        
        # ===== Quiet =====
        # Quiet có ATR thấp
        if features["atr_ratio"] < 1:
            scores["quiet"] += 1 - features["atr_ratio"]
            
        # Ít biến động
        if features["volatility_shift"] < 0.5:
            scores["quiet"] += 1 - features["volatility_shift"]
        
        # ===== Choppy =====
        # Choppy có Hurst < 0.4 (anti-persistent)
        if features["hurst_exponent"] < 0.4:
            scores["choppy"] += (0.4 - features["hurst_exponent"]) * 10
            
        # Kurtosis thấp
        if features["return_kurtosis"] < 0:
            scores["choppy"] += abs(features["return_kurtosis"])
        
        return scores
    
    def _calculate_hurst_exponent(self, prices: np.ndarray) -> float:
        """Tính Hurst Exponent (chỉ số fractal tự tương quan)"""
        # Phương pháp R/S Analysis
        # (code thực hiện tính Hurst Exponent)
        return 0.6  # Giá trị mẫu, cần thay thế
    
    def _calculate_atr(self, price_data: pd.DataFrame, period: int = 14) -> float:
        """Tính Average True Range"""
        # (code thực hiện tính ATR)
        return 100.0  # Giá trị mẫu, cần thay thế
    
    def _calculate_adx(self, price_data: pd.DataFrame, period: int = 14) -> float:
        """Tính Average Directional Index"""
        # (code thực hiện tính ADX)
        return 30.0  # Giá trị mẫu, cần thay thế
    
    def _calculate_volatility_shift(self, price_data: pd.DataFrame) -> float:
        """Tính sự thay đổi biến động gần đây so với quá khứ"""
        # (code thực hiện tính volatility shift)
        return 1.2  # Giá trị mẫu, cần thay thế
```

#### 3.2 Machine Learning Market Regime Detection
- Thêm mô hình ML (Random Forest, XGBoost) để phát hiện chế độ thị trường
- Huấn luyện mô hình từ dữ liệu lịch sử với nhiều đặc trưng khác nhau

### 4. Tối ưu hóa thời gian giao dịch (Q3/2025)

#### 4.1 Phân tích hiệu suất theo thời gian
```python
class TradingTimeOptimizer:
    """Tối ưu hóa thời gian giao dịch dựa trên hiệu suất lịch sử"""
    
    def __init__(self, trade_history: List[Dict], time_segments: int = 24):
        self.trade_history = trade_history
        self.time_segments = time_segments
        self.hour_performance = {}
        self.day_performance = {}
        self.update_performance_analysis()
    
    def update_performance_analysis(self) -> None:
        """Cập nhật phân tích hiệu suất từ lịch sử giao dịch"""
        # Khởi tạo thống kê theo giờ
        self.hour_performance = {i: {
            'trades': 0, 'win_rate': 0, 'avg_profit': 0, 
            'sharpe': 0, 'expectancy': 0
        } for i in range(self.time_segments)}
        
        # Khởi tạo thống kê theo ngày trong tuần
        self.day_performance = {i: {
            'trades': 0, 'win_rate': 0, 'avg_profit': 0, 
            'sharpe': 0, 'expectancy': 0
        } for i in range(7)}  # 0 = Thứ 2, 6 = Chủ nhật
        
        if not self.trade_history:
            return
        
        # Tính toán thống kê theo giờ
        for trade in self.trade_history:
            # Phân tích theo giờ
            entry_time = trade.get('entry_time')
            if not entry_time:
                continue
                
            hour = entry_time.hour
            day = entry_time.weekday()
            pnl = trade.get('pnl_pct', 0)
            
            # Cập nhật thống kê giờ
            hour_stats = self.hour_performance[hour]
            hour_stats['trades'] += 1
            
            if hour_stats['trades'] == 1:
                hour_stats['win_rate'] = 1 if pnl > 0 else 0
                hour_stats['avg_profit'] = pnl
            else:
                hour_stats['win_rate'] = (hour_stats['win_rate'] * (hour_stats['trades'] - 1) + 
                                        (1 if pnl > 0 else 0)) / hour_stats['trades']
                hour_stats['avg_profit'] = (hour_stats['avg_profit'] * (hour_stats['trades'] - 1) + 
                                         pnl) / hour_stats['trades']
            
            # Cập nhật thống kê ngày
            day_stats = self.day_performance[day]
            day_stats['trades'] += 1
            
            if day_stats['trades'] == 1:
                day_stats['win_rate'] = 1 if pnl > 0 else 0
                day_stats['avg_profit'] = pnl
            else:
                day_stats['win_rate'] = (day_stats['win_rate'] * (day_stats['trades'] - 1) + 
                                       (1 if pnl > 0 else 0)) / day_stats['trades']
                day_stats['avg_profit'] = (day_stats['avg_profit'] * (day_stats['trades'] - 1) + 
                                        pnl) / day_stats['trades']
        
        # Tính toán metrics nâng cao
        self._calculate_advanced_metrics()
    
    def _calculate_advanced_metrics(self) -> None:
        """Tính toán các metrics nâng cao như Sharpe ratio và Expectancy"""
        # Tính cho từng giờ
        for hour, stats in self.hour_performance.items():
            if stats['trades'] < 5:
                continue
                
            hour_trades = [t.get('pnl_pct', 0) for t in self.trade_history 
                         if t.get('entry_time') and t.get('entry_time').hour == hour]
            
            if len(hour_trades) > 1:
                # Tính Sharpe ratio
                mean_return = np.mean(hour_trades)
                std_return = np.std(hour_trades)
                stats['sharpe'] = mean_return / std_return if std_return > 0 else 0
                
                # Tính Expectancy
                win_rate = stats['win_rate']
                avg_win = np.mean([pnl for pnl in hour_trades if pnl > 0]) if any(pnl > 0 for pnl in hour_trades) else 0
                avg_loss = np.mean([pnl for pnl in hour_trades if pnl < 0]) if any(pnl < 0 for pnl in hour_trades) else 0
                
                if avg_loss < 0:  # Tránh chia cho 0
                    stats['expectancy'] = (win_rate * avg_win + (1 - win_rate) * avg_loss) / abs(avg_loss)
                else:
                    stats['expectancy'] = 0
        
        # Tính cho từng ngày
        for day, stats in self.day_performance.items():
            if stats['trades'] < 5:
                continue
                
            day_trades = [t.get('pnl_pct', 0) for t in self.trade_history 
                        if t.get('entry_time') and t.get('entry_time').weekday() == day]
            
            if len(day_trades) > 1:
                # Tính Sharpe ratio
                mean_return = np.mean(day_trades)
                std_return = np.std(day_trades)
                stats['sharpe'] = mean_return / std_return if std_return > 0 else 0
                
                # Tính Expectancy
                win_rate = stats['win_rate']
                avg_win = np.mean([pnl for pnl in day_trades if pnl > 0]) if any(pnl > 0 for pnl in day_trades) else 0
                avg_loss = np.mean([pnl for pnl in day_trades if pnl < 0]) if any(pnl < 0 for pnl in day_trades) else 0
                
                if avg_loss < 0:  # Tránh chia cho 0
                    stats['expectancy'] = (win_rate * avg_win + (1 - win_rate) * avg_loss) / abs(avg_loss)
                else:
                    stats['expectancy'] = 0
    
    def get_optimal_trading_hours(self, min_trades: int = 10, min_expectancy: float = 0.1) -> List[int]:
        """Lấy các giờ tối ưu cho giao dịch"""
        optimal_hours = []
        
        for hour, stats in self.hour_performance.items():
            if (stats['trades'] >= min_trades and 
                stats['expectancy'] >= min_expectancy and
                stats['avg_profit'] > 0):
                optimal_hours.append(hour)
        
        return sorted(optimal_hours)
    
    def get_optimal_trading_days(self, min_trades: int = 10, min_expectancy: float = 0.1) -> List[int]:
        """Lấy các ngày tối ưu cho giao dịch"""
        optimal_days = []
        
        for day, stats in self.day_performance.items():
            if (stats['trades'] >= min_trades and 
                stats['expectancy'] >= min_expectancy and
                stats['avg_profit'] > 0):
                optimal_days.append(day)
        
        return sorted(optimal_days)
    
    def should_trade_now(self, current_time: datetime = None) -> Tuple[bool, str]:
        """
        Kiểm tra xem thời điểm hiện tại có nên giao dịch không
        
        Args:
            current_time (datetime): Thời gian hiện tại, mặc định là now()
            
        Returns:
            Tuple[bool, str]: (Có nên giao dịch, Lý do)
        """
        if current_time is None:
            current_time = datetime.now()
        
        hour = current_time.hour
        day = current_time.weekday()
        
        hour_stats = self.hour_performance.get(hour, {})
        day_stats = self.day_performance.get(day, {})
        
        # Kiểm tra đủ dữ liệu
        if hour_stats.get('trades', 0) < 10 or day_stats.get('trades', 0) < 5:
            return True, "Không đủ dữ liệu lịch sử để đánh giá thời gian giao dịch"
        
        # Kiểm tra nếu cả giờ và ngày đều không tốt
        if (hour_stats.get('avg_profit', 0) < 0 and 
            day_stats.get('avg_profit', 0) < 0):
            return False, f"Thời gian không tối ưu: Giờ {hour} và ngày {day} đều có hiệu suất âm"
        
        # Kiểm tra expectancy
        if hour_stats.get('expectancy', 0) < 0 and day_stats.get('expectancy', 0) < 0:
            return False, f"Thời gian không tối ưu: Giờ {hour} và ngày {day} đều có expectancy âm"
        
        # Trường hợp hiệu suất tốt
        if hour_stats.get('avg_profit', 0) > 0.2 or day_stats.get('expectancy', 0) > 0.5:
            return True, f"Thời gian tối ưu: Hiệu suất cao vào giờ {hour} ngày {day}"
        
        # Mặc định
        return True, "Thời gian chấp nhận được cho giao dịch"
```

#### 4.2 Event-based Trading Time Optimization
- Xây dựng lịch trình các sự kiện kinh tế quan trọng
- Điều chỉnh giao dịch trước/sau các sự kiện như công bố lãi suất, số liệu việc làm, v.v.

### 5. Tích hợp thanh khoản và Market Microstructure (Q4/2025)

#### 5.1 Order Book Analysis
```python
class OrderBookAnalyzer:
    """Phân tích order book để tối ưu hóa thời điểm vào lệnh"""
    
    def __init__(self, depth_limit: int = 10, update_interval: int = 1):
        self.depth_limit = depth_limit
        self.update_interval = update_interval
        self.current_order_book = {}
        self.historical_order_books = []
        self.last_update_time = 0
    
    def update_order_book(self, symbol: str, order_book_data: Dict) -> None:
        """
        Cập nhật dữ liệu order book
        
        Args:
            symbol (str): Mã giao dịch
            order_book_data (Dict): Dữ liệu order book từ API
        """
        current_time = time.time()
        
        # Chỉ cập nhật nếu đã qua khoảng thời gian update_interval
        if current_time - self.last_update_time < self.update_interval:
            return
            
        self.last_update_time = current_time
        
        # Lưu order book hiện tại vào lịch sử
        if self.current_order_book:
            self.historical_order_books.append({
                'time': self.last_update_time,
                'data': copy.deepcopy(self.current_order_book)
            })
            
            # Giới hạn kích thước lịch sử
            if len(self.historical_order_books) > 100:
                self.historical_order_books.pop(0)
        
        # Cập nhật order book hiện tại
        self.current_order_book = {
            'symbol': symbol,
            'bids': order_book_data.get('bids', [])[:self.depth_limit],
            'asks': order_book_data.get('asks', [])[:self.depth_limit],
            'timestamp': current_time
        }
    
    def calculate_liquidity_metrics(self) -> Dict:
        """
        Tính toán các chỉ số thanh khoản từ order book
        
        Returns:
            Dict: Các chỉ số thanh khoản
        """
        if not self.current_order_book:
            return {}
            
        bids = self.current_order_book.get('bids', [])
        asks = self.current_order_book.get('asks', [])
        
        if not bids or not asks:
            return {}
            
        # Tính spread
        best_bid = float(bids[0][0]) if bids else 0
        best_ask = float(asks[0][0]) if asks else 0
        
        if best_bid <= 0 or best_ask <= 0:
            return {}
            
        spread = best_ask - best_bid
        spread_pct = spread / best_bid * 100
        
        # Tính khối lượng và giá trị trên mỗi bên
        bid_volume = sum(float(b[1]) for b in bids)
        ask_volume = sum(float(a[1]) for a in asks)
        
        bid_value = sum(float(b[0]) * float(b[1]) for b in bids)
        ask_value = sum(float(a[0]) * float(a[1]) for a in asks)
        
        # Tính imbalance
        volume_imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume) if (bid_volume + ask_volume) > 0 else 0
        value_imbalance = (bid_value - ask_value) / (bid_value + ask_value) if (bid_value + ask_value) > 0 else 0
        
        # Tính market depth (đến giá tốt nhất + 1%)
        price_threshold_bid = best_bid * 0.99  # 1% dưới giá bid tốt nhất
        price_threshold_ask = best_ask * 1.01  # 1% trên giá ask tốt nhất
        
        depth_bid = sum(float(b[1]) for b in bids if float(b[0]) >= price_threshold_bid)
        depth_ask = sum(float(a[1]) for a in asks if float(a[0]) <= price_threshold_ask)
        
        return {
            'spread': spread,
            'spread_pct': spread_pct,
            'bid_volume': bid_volume,
            'ask_volume': ask_volume,
            'bid_value': bid_value,
            'ask_value': ask_value,
            'volume_imbalance': volume_imbalance,
            'value_imbalance': value_imbalance,
            'depth_bid': depth_bid,
            'depth_ask': depth_ask,
            'liquidity_score': self._calculate_liquidity_score(spread_pct, bid_volume, ask_volume, 
                                                            volume_imbalance, depth_bid, depth_ask)
        }
    
    def detect_liquidity_events(self) -> Dict:
        """
        Phát hiện các sự kiện thanh khoản đáng chú ý
        
        Returns:
            Dict: Các sự kiện thanh khoản và mức độ quan trọng
        """
        if len(self.historical_order_books) < 5:
            return {}
            
        current_metrics = self.calculate_liquidity_metrics()
        if not current_metrics:
            return {}
            
        # Tính các chỉ số từ lịch sử gần đây
        recent_books = self.historical_order_books[-5:]
        historical_metrics = []
        
        for book in recent_books:
            old_book = book['data']
            bids = old_book.get('bids', [])
            asks = old_book.get('asks', [])
            
            if not bids or not asks:
                continue
                
            best_bid = float(bids[0][0]) if bids else 0
            best_ask = float(asks[0][0]) if asks else 0
            
            if best_bid <= 0 or best_ask <= 0:
                continue
                
            spread = best_ask - best_bid
            spread_pct = spread / best_bid * 100
            
            bid_volume = sum(float(b[1]) for b in bids)
            ask_volume = sum(float(a[1]) for a in asks)
            
            historical_metrics.append({
                'spread_pct': spread_pct,
                'bid_volume': bid_volume,
                'ask_volume': ask_volume,
                'total_volume': bid_volume + ask_volume
            })
        
        if not historical_metrics:
            return {}
            
        # Tính trung bình và độ lệch chuẩn
        avg_spread = np.mean([m['spread_pct'] for m in historical_metrics])
        avg_volume = np.mean([m['total_volume'] for m in historical_metrics])
        
        events = {}
        
        # Kiểm tra spread thay đổi đột ngột
        if current_metrics['spread_pct'] > avg_spread * 2:
            events['spread_widening'] = {
                'severity': 'high',
                'current': current_metrics['spread_pct'],
                'average': avg_spread,
                'action': 'pause_trading'
            }
        elif current_metrics['spread_pct'] < avg_spread * 0.5:
            events['spread_narrowing'] = {
                'severity': 'medium',
                'current': current_metrics['spread_pct'],
                'average': avg_spread,
                'action': 'consider_entry'
            }
        
        # Kiểm tra imbalance lớn
        if abs(current_metrics['volume_imbalance']) > 0.4:  # Imbalance > 40%
            side = 'buy' if current_metrics['volume_imbalance'] > 0 else 'sell'
            events['significant_imbalance'] = {
                'severity': 'high',
                'side': side,
                'value': current_metrics['volume_imbalance'],
                'action': f'consider_{side}'
            }
        
        # Kiểm tra thanh khoản cạn
        current_total_volume = current_metrics['bid_volume'] + current_metrics['ask_volume']
        if current_total_volume < avg_volume * 0.5:
            events['low_liquidity'] = {
                'severity': 'high',
                'current': current_total_volume,
                'average': avg_volume,
                'action': 'reduce_position_size'
            }
        
        return events
    
    def get_execution_recommendations(self) -> Dict:
        """
        Đưa ra khuyến nghị về thời điểm và cách thức thực thi lệnh
        
        Returns:
            Dict: Khuyến nghị cho việc thực thi lệnh
        """
        events = self.detect_liquidity_events()
        metrics = self.calculate_liquidity_metrics()
        
        if not metrics:
            return {'execution_style': 'market', 'confidence': 'low'}
            
        # Khuyến nghị mặc định
        recommendations = {
            'execution_style': 'market',
            'execution_timing': 'immediate',
            'confidence': 'medium',
            'suggested_slippage': metrics['spread_pct'] * 1.5,
            'position_size_modifier': 1.0,
            'details': {}
        }
        
        # Điều chỉnh dựa trên sự kiện
        for event_type, event_data in events.items():
            if event_data['severity'] == 'high':
                if event_type == 'spread_widening':
                    recommendations['execution_style'] = 'limit'
                    recommendations['execution_timing'] = 'delayed'
                    recommendations['position_size_modifier'] = 0.7
                    recommendations['confidence'] = 'low'
                    
                elif event_type == 'low_liquidity':
                    recommendations['execution_style'] = 'iceberg'
                    recommendations['position_size_modifier'] = 0.5
                    recommendations['confidence'] = 'low'
                    
                elif event_type == 'significant_imbalance':
                    side = event_data['side']
                    if side == 'buy':
                        recommendations['execution_style'] = 'limit'
                        recommendations['execution_timing'] = 'immediate'
                        recommendations['confidence'] = 'high'
                    else:
                        recommendations['execution_style'] = 'market'
                        recommendations['execution_timing'] = 'immediate'
                        recommendations['confidence'] = 'high'
        
        # Điều chỉnh dựa trên metrics
        if metrics['liquidity_score'] < 3:
            recommendations['execution_style'] = 'twap'
            recommendations['position_size_modifier'] *= 0.8
            
        elif metrics['liquidity_score'] > 8:
            recommendations['position_size_modifier'] *= 1.2
            recommendations['confidence'] = 'high'
        
        recommendations['details'] = {
            'liquidity_score': metrics['liquidity_score'],
            'events': events,
            'metrics': metrics
        }
        
        return recommendations
    
    def _calculate_liquidity_score(self, spread_pct, bid_volume, ask_volume, 
                                 volume_imbalance, depth_bid, depth_ask) -> float:
        """
        Tính điểm thanh khoản tổng hợp (0-10)
        
        Returns:
            float: Điểm thanh khoản (0-10)
        """
        score = 10.0
        
        # Trừ điểm cho spread rộng
        if spread_pct > 0.1:  # Spread > 0.1%
            score -= min(5, spread_pct * 30)
        
        # Cộng điểm cho khối lượng lớn
        volume_score = min(3, math.log10(bid_volume + ask_volume) - 2)
        score += max(0, volume_score)
        
        # Trừ điểm cho imbalance cao
        score -= min(3, abs(volume_imbalance) * 5)
        
        # Cộng điểm cho độ sâu thị trường
        depth_score = min(3, math.log10(depth_bid + depth_ask) - 2)
        score += max(0, depth_score)
        
        return min(10, max(0, score))
```

#### 5.2 CEX-DEX Arbitrage Strategies
- Thêm khả năng theo dõi và khai thác chênh lệch giá giữa các sàn tập trung (CEX) và phi tập trung (DEX)
- Thực hiện giao dịch arbitrage an toàn với quản lý rủi ro thích hợp

### 6. Logging, Reporting và Giám sát (Q4/2025)

#### 6.1 Advanced Logging System
- Thêm hệ thống logging đa cấp, tách biệt theo loại hoạt động (trade, analyze, error)
- Tích hợp tự động phân tích và tóm tắt log

#### 6.2 Giám sát thời gian thực
- Xây dựng dashboard CLI với các chỉ số quan trọng
- Tích hợp cảnh báo cho các sự kiện quan trọng (drawdown lớn, lỗi kết nối API)

#### 6.3 Tự động báo cáo
- Tạo báo cáo hiệu suất tự động theo lịch (hàng ngày, hàng tuần)
- Gửi báo cáo qua Telegram/Email với phân tích chi tiết

## Kế hoạch triển khai

| Giai đoạn | Thời gian | Tính năng | Mức độ ưu tiên |
|-----------|-----------|-----------|----------------|
| 1 | Q2/2025 | Nâng cao quản lý vị thế và rủi ro | Cao |
| 2 | Q3/2025 | Phát hiện Market Regime nâng cao & Tối ưu thời gian giao dịch | Cao |
| 3 | Q4/2025 | Phân tích Market Microstructure & Logging nâng cao | Trung bình |
| 4 | Q1/2026 | Tích hợp CEX-DEX Arbitrage | Thấp |

## Yêu cầu tài nguyên
- Python libraries bổ sung: scipy, statsmodels, hurst
- Tăng tần suất lấy dữ liệu order book (tối thiểu 1 lần/giây)
- Tăng dung lượng lưu trữ cho dữ liệu phân tích thị trường và lịch sử giao dịch