"""
Volume Profile Analyzer - Phân tích cấu trúc khối lượng theo giá

Module này cung cấp công cụ phân tích Volume Profile để xác định vùng giá
tập trung giao dịch, hỗ trợ nhận diện vùng hỗ trợ, kháng cự và khả năng bứt phá.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import json
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional, Union, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('volume_profile_analyzer')

class VolumeProfileAnalyzer:
    """
    Phân tích cấu trúc khối lượng giao dịch theo giá để xác định
    vùng tập trung, điểm kiểm soát giá (POC), và các vùng giá quan trọng.
    """
    
    def __init__(self, data_storage_path='data/volume_profile'):
        """
        Khởi tạo VolumeProfileAnalyzer.
        
        Args:
            data_storage_path (str): Đường dẫn lưu trữ dữ liệu volume profile
        """
        self.data_storage_path = data_storage_path
        
        # Cấu hình
        self.config = {
            'num_bins': 100,          # Số lượng vùng giá (bars) trong volume profile
            'value_area_pct': 0.70,   # Phần trăm khối lượng cho Value Area (70%)
            'lookback_periods': 24,   # Số nến dùng để tính volume profile
            'profile_types': ['session', 'daily', 'weekly', 'monthly'],  # Các loại profile
            'significant_levels': 5,  # Số lượng vùng hỗ trợ/kháng cự quan trọng hiển thị
            'volume_factor': 1.5      # Hệ số nhận biết vùng tập trung khối lượng 
        }
        
        # Kết quả phân tích
        self.profiles = {}  # {'BTCUSDT': {'session': {...}, 'daily': {...}, ...}}
        
        # Vùng giá quan trọng
        self.key_levels = {}  # {'BTCUSDT': {'poc': 123, 'va_high': 125, 'va_low': 121, ...}}
        
        # Tạo thư mục lưu trữ nếu chưa tồn tại
        os.makedirs(data_storage_path, exist_ok=True)
    
    def calculate_volume_profile(self, df: pd.DataFrame, symbol: str, 
                               profile_type: str = 'session') -> Dict:
        """
        Tính toán volume profile từ dữ liệu nến.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu nến (OHLCV)
            symbol (str): Cặp tiền
            profile_type (str): Loại profile ('session', 'daily', 'weekly', 'monthly')
            
        Returns:
            Dict: Kết quả phân tích volume profile
        """
        try:
            if df.empty:
                logger.warning(f"DataFrame trống, không thể tính toán volume profile cho {symbol}")
                return {}
            
            # Đảm bảo columns cần thiết tồn tại
            required_columns = ['high', 'low', 'close', 'volume']
            missing = [col for col in required_columns if col not in df.columns]
            if missing:
                logger.warning(f"Thiếu các cột {missing} trong dữ liệu")
                return {}
            
            # Lọc dữ liệu theo loại profile
            filtered_df = self._filter_data_by_profile_type(df, profile_type)
            
            if filtered_df.empty:
                logger.warning(f"Không đủ dữ liệu cho profile type '{profile_type}'")
                return {}
            
            # Tính khoảng giá
            price_min = filtered_df['low'].min()
            price_max = filtered_df['high'].max()
            
            # Nếu min = max (hiếm khi xảy ra), điều chỉnh để tránh lỗi
            if price_min == price_max:
                price_min = price_min * 0.99
                price_max = price_max * 1.01
            
            # Tạo bins cho volume profile
            price_bins = np.linspace(price_min, price_max, self.config['num_bins'] + 1)
            bin_width = (price_max - price_min) / self.config['num_bins']
            
            # Khởi tạo mảng volume cho mỗi bin
            volumes = np.zeros(self.config['num_bins'])
            
            # Tính volume cho mỗi bin
            for _, candle in filtered_df.iterrows():
                # Xác định range price của nến này
                candle_min = candle['low']
                candle_max = candle['high']
                candle_volume = candle['volume']
                
                # Tính volume profile
                for i in range(self.config['num_bins']):
                    bin_low = price_bins[i]
                    bin_high = price_bins[i + 1]
                    
                    # Kiểm tra xem bin có overlap với candle không
                    if bin_high >= candle_min and bin_low <= candle_max:
                        # Tính tỷ lệ overlap
                        overlap_low = max(bin_low, candle_min)
                        overlap_high = min(bin_high, candle_max)
                        overlap_ratio = (overlap_high - overlap_low) / (candle_max - candle_min)
                        
                        # Thêm volume theo tỷ lệ overlap
                        volumes[i] += candle_volume * overlap_ratio
            
            # Tạo dữ liệu volume profile
            profile_data = pd.DataFrame({
                'price_low': price_bins[:-1],
                'price_high': price_bins[1:],
                'price_mid': (price_bins[:-1] + price_bins[1:]) / 2,
                'volume': volumes
            })
            
            # Sắp xếp theo khối lượng giảm dần
            profile_data_sorted = profile_data.sort_values('volume', ascending=False)
            
            # Tính Point of Control (POC) - giá có khối lượng cao nhất
            poc = profile_data_sorted.iloc[0]['price_mid']
            
            # Tính Value Area - vùng tập trung ~70% khối lượng
            total_volume = profile_data['volume'].sum()
            target_volume = total_volume * self.config['value_area_pct']
            
            cumulative_volume = 0
            value_area_prices = []
            
            for _, row in profile_data_sorted.iterrows():
                value_area_prices.append(row['price_mid'])
                cumulative_volume += row['volume']
                
                if cumulative_volume >= target_volume:
                    break
            
            # Xác định Value Area High (VAH) và Value Area Low (VAL)
            va_high = max(value_area_prices)
            va_low = min(value_area_prices)
            
            # Xác định các vùng tập trung khối lượng (volume nodes)
            avg_volume = profile_data['volume'].mean()
            high_volume_threshold = avg_volume * self.config['volume_factor']
            
            volume_nodes = profile_data[profile_data['volume'] > high_volume_threshold]
            
            # Tạo kết quả
            result = {
                'symbol': symbol,
                'profile_type': profile_type,
                'timestamp': datetime.now().isoformat(),
                'price_range': {'min': price_min, 'max': price_max},
                'poc': poc,
                'value_area': {'high': va_high, 'low': va_low},
                'volume_nodes': volume_nodes.to_dict('records'),
                'profile_data': profile_data.to_dict('records'),
                'bin_width': bin_width,
                'total_volume': total_volume
            }
            
            # Lưu kết quả
            if symbol not in self.profiles:
                self.profiles[symbol] = {}
            
            self.profiles[symbol][profile_type] = result
            
            # Cập nhật key levels
            self._update_key_levels(symbol, result)
            
            # Lưu dữ liệu
            self._save_profile_data(symbol)
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi tính toán volume profile: {str(e)}")
            return {}
    
    def get_key_levels(self, symbol: str) -> Dict:
        """
        Lấy thông tin các vùng giá quan trọng.
        
        Args:
            symbol (str): Cặp tiền
            
        Returns:
            Dict: Các vùng giá quan trọng từ volume profile
        """
        if symbol in self.key_levels:
            return self.key_levels[symbol]
        else:
            return {
                'support_levels': [],
                'resistance_levels': [],
                'poc': None,
                'value_area': {'high': None, 'low': None}
            }
    
    def analyze_trading_range(self, df: pd.DataFrame, symbol: str) -> Dict:
        """
        Phân tích vùng giao dịch dựa trên volume profile.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu nến
            symbol (str): Cặp tiền
            
        Returns:
            Dict: Phân tích vùng giao dịch
        """
        try:
            # Tính toán volume profile từ dữ liệu
            self.calculate_volume_profile(df, symbol, 'session')
            
            if symbol not in self.key_levels:
                logger.warning(f"Không có thông tin key levels cho {symbol}")
                return {}
            
            # Lấy giá hiện tại
            current_price = df['close'].iloc[-1] if not df.empty else None
            
            if current_price is None:
                logger.warning(f"Không thể lấy giá hiện tại cho {symbol}")
                return {}
                
            # Lấy thông tin key levels
            key_levels = self.key_levels[symbol]
            
            # Lấy POC, VAH, VAL
            poc = key_levels.get('poc')
            va_high = key_levels.get('value_area', {}).get('high')
            va_low = key_levels.get('value_area', {}).get('low')
            
            # Phân tích vị trí giá hiện tại so với vùng giá
            position = 'unknown'
            if poc is not None and va_high is not None and va_low is not None:
                if current_price > va_high:
                    position = 'above_value_area'
                elif current_price < va_low:
                    position = 'below_value_area'
                else:
                    position = 'inside_value_area'
                    
                    if abs(current_price - poc) < (va_high - va_low) * 0.1:
                        position = 'near_poc'
            
            # Xác định các vùng hỗ trợ/kháng cự gần nhất
            support_levels = [level for level in key_levels.get('support_levels', []) if level < current_price]
            resistance_levels = [level for level in key_levels.get('resistance_levels', []) if level > current_price]
            
            nearest_support = max(support_levels) if support_levels else None
            nearest_resistance = min(resistance_levels) if resistance_levels else None
            
            # Tính khoảng cách đến các vùng
            distance_to_poc = abs(current_price - poc) / current_price * 100 if poc else None
            distance_to_va_high = abs(current_price - va_high) / current_price * 100 if va_high else None
            distance_to_va_low = abs(current_price - va_low) / current_price * 100 if va_low else None
            distance_to_support = abs(current_price - nearest_support) / current_price * 100 if nearest_support else None
            distance_to_resistance = abs(current_price - nearest_resistance) / current_price * 100 if nearest_resistance else None
            
            # Đánh giá khả năng bứt phá
            breakout_potential_up = False
            breakout_potential_down = False
            
            if position == 'above_value_area' and distance_to_va_high and distance_to_va_high < 1.0:
                # Đang gần trên vùng Value Area, có thể bứt phá lên
                breakout_potential_up = True
                
            if position == 'below_value_area' and distance_to_va_low and distance_to_va_low < 1.0:
                # Đang gần dưới vùng Value Area, có thể bứt phá xuống
                breakout_potential_down = True
            
            # Tạo kết quả phân tích
            result = {
                'symbol': symbol,
                'current_price': current_price,
                'position': position,
                'poc': poc,
                'value_area': {'high': va_high, 'low': va_low},
                'nearest_support': nearest_support,
                'nearest_resistance': nearest_resistance,
                'distance': {
                    'to_poc': distance_to_poc,
                    'to_va_high': distance_to_va_high,
                    'to_va_low': distance_to_va_low,
                    'to_support': distance_to_support,
                    'to_resistance': distance_to_resistance
                },
                'breakout_potential': {
                    'up': breakout_potential_up,
                    'down': breakout_potential_down
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích vùng giao dịch: {str(e)}")
            return {}
    
    def identify_support_resistance(self, df: pd.DataFrame, symbol: str, 
                                  lookback_days: int = 30) -> Dict:
        """
        Xác định vùng hỗ trợ/kháng cự dựa trên volume profile nhiều khung thời gian.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu nến
            symbol (str): Cặp tiền
            lookback_days (int): Số ngày nhìn lại để phân tích
            
        Returns:
            Dict: Vùng hỗ trợ/kháng cự được xác định
        """
        try:
            # Lọc dữ liệu theo lookback_days
            if not df.empty:
                end_date = df.index[-1]
                start_date = end_date - timedelta(days=lookback_days)
                df_filtered = df[df.index >= start_date]
            else:
                logger.warning(f"DataFrame trống, không thể xác định hỗ trợ/kháng cự cho {symbol}")
                return {}
                
            # Tính toán volume profile cho các khung thời gian khác nhau
            self.calculate_volume_profile(df_filtered, symbol, 'daily')
            self.calculate_volume_profile(df_filtered, symbol, 'weekly')
            
            if symbol not in self.profiles:
                logger.warning(f"Không có dữ liệu profile cho {symbol}")
                return {}
            
            # Lấy giá hiện tại
            current_price = df['close'].iloc[-1]
            
            # Vùng hỗ trợ/kháng cự từ các khung thời gian khác nhau
            support_levels = set()
            resistance_levels = set()
            
            # Thêm các vùng từ các profile khác nhau
            for profile_type in ['session', 'daily', 'weekly']:
                if profile_type in self.profiles[symbol]:
                    profile = self.profiles[symbol][profile_type]
                    
                    # Thêm POC
                    poc = profile.get('poc')
                    if poc:
                        if poc < current_price:
                            support_levels.add(poc)
                        else:
                            resistance_levels.add(poc)
                            
                    # Thêm VAH và VAL
                    va_high = profile.get('value_area', {}).get('high')
                    va_low = profile.get('value_area', {}).get('low')
                    
                    if va_high and va_high > current_price:
                        resistance_levels.add(va_high)
                    
                    if va_low and va_low < current_price:
                        support_levels.add(va_low)
                        
                    # Thêm volume nodes
                    for node in profile.get('volume_nodes', []):
                        price = node.get('price_mid')
                        if price:
                            if price < current_price:
                                support_levels.add(price)
                            else:
                                resistance_levels.add(price)
            
            # Lọc các vùng quá gần nhau (trong khoảng 0.5%)
            support_levels = self._filter_close_levels(list(support_levels))
            resistance_levels = self._filter_close_levels(list(resistance_levels))
            
            # Sắp xếp theo khoảng cách với giá hiện tại
            support_levels.sort(key=lambda x: current_price - x)
            resistance_levels.sort(key=lambda x: x - current_price)
            
            # Chỉ lấy N vùng gần nhất
            support_levels = support_levels[:self.config['significant_levels']]
            resistance_levels = resistance_levels[:self.config['significant_levels']]
            
            # Cập nhật key levels
            if symbol not in self.key_levels:
                self.key_levels[symbol] = {}
                
            self.key_levels[symbol]['support_levels'] = support_levels
            self.key_levels[symbol]['resistance_levels'] = resistance_levels
            
            # Tạo kết quả
            result = {
                'symbol': symbol,
                'lookback_days': lookback_days,
                'current_price': current_price,
                'support_levels': support_levels,
                'resistance_levels': resistance_levels,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi xác định vùng hỗ trợ/kháng cự: {str(e)}")
            return {}
    
    def visualize_volume_profile(self, symbol: str, profile_type: str = 'session',
                               output_path: Optional[str] = None) -> str:
        """
        Tạo biểu đồ volume profile.
        
        Args:
            symbol (str): Cặp tiền
            profile_type (str): Loại profile
            output_path (str, optional): Đường dẫn lưu biểu đồ
            
        Returns:
            str: Đường dẫn đến biểu đồ
        """
        try:
            if symbol not in self.profiles or profile_type not in self.profiles[symbol]:
                logger.warning(f"Không có dữ liệu profile cho {symbol} - {profile_type}")
                return ""
                
            profile = self.profiles[symbol][profile_type]
            profile_data = pd.DataFrame(profile['profile_data'])
            
            # Tạo đường dẫn lưu biểu đồ nếu không cung cấp
            if not output_path:
                symbol_dir = os.path.join(self.data_storage_path, symbol)
                os.makedirs(symbol_dir, exist_ok=True)
                output_path = os.path.join(symbol_dir, f"{symbol}_{profile_type}_volume_profile.png")
                
            # Tạo biểu đồ
            plt.figure(figsize=(10, 8))
            
            # Vẽ volume profile (horizontal bars)
            plt.barh(profile_data['price_mid'], profile_data['volume'], 
                   height=profile['bin_width'], color='skyblue', alpha=0.7)
            
            # Thêm POC (Point of Control)
            poc = profile['poc']
            plt.axhline(y=poc, color='red', linestyle='-', linewidth=1.5, 
                      label=f'POC: {poc:.2f}')
            
            # Thêm Value Area
            va_high = profile['value_area']['high']
            va_low = profile['value_area']['low']
            
            plt.axhline(y=va_high, color='green', linestyle='--', linewidth=1.2, 
                      label=f'VA High: {va_high:.2f}')
            plt.axhline(y=va_low, color='green', linestyle='--', linewidth=1.2, 
                      label=f'VA Low: {va_low:.2f}')
            
            # Đánh dấu vùng Value Area
            plt.axhspan(va_low, va_high, alpha=0.2, color='green')
            
            # Thêm tiêu đề và nhãn
            plt.title(f'Volume Profile - {symbol} ({profile_type.capitalize()})')
            plt.xlabel('Volume')
            plt.ylabel('Price')
            plt.grid(True, alpha=0.3)
            plt.legend()
            
            # Lưu biểu đồ
            plt.tight_layout()
            plt.savefig(output_path)
            plt.close()
            
            logger.info(f"Đã tạo biểu đồ volume profile tại: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ volume profile: {str(e)}")
            return ""
    
    def _filter_data_by_profile_type(self, df: pd.DataFrame, profile_type: str) -> pd.DataFrame:
        """Lọc dữ liệu theo loại profile."""
        if df.empty:
            return pd.DataFrame()
            
        now = datetime.now()
        
        if profile_type == 'session':
            # Lấy N nến gần nhất
            return df.tail(self.config['lookback_periods'])
            
        elif profile_type == 'daily':
            # Lấy dữ liệu 1 ngày
            start_date = now - timedelta(days=1)
            return df[df.index >= start_date]
            
        elif profile_type == 'weekly':
            # Lấy dữ liệu 1 tuần
            start_date = now - timedelta(days=7)
            return df[df.index >= start_date]
            
        elif profile_type == 'monthly':
            # Lấy dữ liệu 1 tháng
            start_date = now - timedelta(days=30)
            return df[df.index >= start_date]
            
        else:
            # Mặc định lấy N nến gần nhất
            return df.tail(self.config['lookback_periods'])
    
    def _update_key_levels(self, symbol: str, profile_data: Dict) -> None:
        """Cập nhật thông tin key levels từ profile data."""
        if not profile_data:
            return
            
        # Tạo entry cho symbol nếu chưa có
        if symbol not in self.key_levels:
            self.key_levels[symbol] = {
                'support_levels': [],
                'resistance_levels': [],
                'poc': None,
                'value_area': {'high': None, 'low': None}
            }
            
        # Cập nhật POC
        self.key_levels[symbol]['poc'] = profile_data.get('poc')
        
        # Cập nhật Value Area
        self.key_levels[symbol]['value_area'] = profile_data.get('value_area', {'high': None, 'low': None})
    
    def _filter_close_levels(self, levels: List[float], threshold_pct: float = 0.5) -> List[float]:
        """Lọc bỏ các mức giá quá gần nhau."""
        if not levels:
            return []
            
        # Sắp xếp theo giá tăng dần
        sorted_levels = sorted(levels)
        
        # Lọc bỏ các mức quá gần nhau
        filtered = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            # Tính khoảng cách tới mức gần nhất
            closest = filtered[-1]
            pct_diff = abs(level - closest) / closest * 100
            
            # Chỉ thêm nếu khoảng cách > ngưỡng
            if pct_diff > threshold_pct:
                filtered.append(level)
                
        return filtered
    
    def _save_profile_data(self, symbol: str) -> None:
        """Lưu dữ liệu profile vào file."""
        try:
            if symbol not in self.profiles:
                return
                
            # Tạo thư mục theo symbol
            symbol_dir = os.path.join(self.data_storage_path, symbol)
            os.makedirs(symbol_dir, exist_ok=True)
            
            # Lưu dữ liệu từng profile
            for profile_type, profile_data in self.profiles[symbol].items():
                # Tạo bản sao để tránh lỗi circular reference khi lưu JSON
                profile_data_copy = profile_data.copy()
                
                # Chuyển profile_data thành list để giảm kích thước file
                if 'profile_data' in profile_data_copy:
                    top_n = 20  # Chỉ lưu 20 mức quan trọng nhất
                    df = pd.DataFrame(profile_data_copy['profile_data'])
                    df = df.sort_values('volume', ascending=False).head(top_n)
                    profile_data_copy['profile_data'] = df.to_dict('records')
                
                # Lưu dữ liệu
                file_path = os.path.join(symbol_dir, f"{profile_type}_profile.json")
                with open(file_path, 'w') as f:
                    json.dump(profile_data_copy, f, indent=2, default=str)
            
            # Lưu key levels
            if symbol in self.key_levels:
                file_path = os.path.join(symbol_dir, "key_levels.json")
                with open(file_path, 'w') as f:
                    json.dump(self.key_levels[symbol], f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu profile: {str(e)}")


if __name__ == "__main__":
    # Ví dụ sử dụng
    analyzer = VolumeProfileAnalyzer()
    
    # Tạo dữ liệu mẫu
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    # Dữ liệu 5 ngày, mỗi giờ 1 nến
    num_candles = 24 * 5
    now = datetime.now()
    dates = [now - timedelta(hours=i) for i in range(num_candles, 0, -1)]
    
    # Tạo giá theo mô hình đơn giản với một số vùng tập trung khối lượng
    base_price = 50000  # BTC price
    prices = []
    volumes = []
    
    for i in range(num_candles):
        # Tạo biến động giá
        if i < num_candles / 3:
            # Giai đoạn uptrend
            trend = 100 * (i / (num_candles / 3))
            noise = np.random.normal(0, 50)
        elif i < 2 * num_candles / 3:
            # Giai đoạn dao động ngang
            trend = 100
            noise = np.random.normal(0, 100)
        else:
            # Giai đoạn downtrend
            trend = 100 - 50 * ((i - 2 * num_candles / 3) / (num_candles / 3))
            noise = np.random.normal(0, 70)
            
        price = base_price + trend + noise
        prices.append(price)
        
        # Tạo khối lượng với một số vùng tập trung
        if abs(price - 50050) < 30:  # Tạo vùng tập trung khối lượng gần 50050
            volume = np.random.uniform(500, 1000)
        elif abs(price - 50150) < 20:  # Tạo vùng tập trung khối lượng gần 50150
            volume = np.random.uniform(800, 1200)
        else:
            volume = np.random.uniform(100, 300)
            
        volumes.append(volume)
    
    # Tạo DataFrame
    df = pd.DataFrame({
        'open': prices,
        'high': [p + np.random.uniform(10, 30) for p in prices],
        'low': [p - np.random.uniform(10, 30) for p in prices],
        'close': [prices[i] + np.random.normal(0, 5) for i in range(len(prices))],
        'volume': volumes
    }, index=dates)
    
    # Tính toán volume profile
    profile_result = analyzer.calculate_volume_profile(df, 'BTCUSDT', 'session')
    
    print(f"Point of Control (POC): {profile_result['poc']:.2f}")
    print(f"Value Area High: {profile_result['value_area']['high']:.2f}")
    print(f"Value Area Low: {profile_result['value_area']['low']:.2f}")
    
    # Phân tích vùng giao dịch
    range_analysis = analyzer.analyze_trading_range(df, 'BTCUSDT')
    
    print(f"\nGiá hiện tại: {range_analysis['current_price']:.2f}")
    print(f"Vị trí: {range_analysis['position']}")
    
    if range_analysis['breakout_potential']['up']:
        print("Có khả năng bứt phá lên")
    if range_analysis['breakout_potential']['down']:
        print("Có khả năng bứt phá xuống")
    
    # Xác định vùng hỗ trợ/kháng cự
    sr_levels = analyzer.identify_support_resistance(df, 'BTCUSDT')
    
    print("\nVùng hỗ trợ:")
    for level in sr_levels['support_levels']:
        print(f"  {level:.2f}")
    
    print("Vùng kháng cự:")
    for level in sr_levels['resistance_levels']:
        print(f"  {level:.2f}")
    
    # Tạo biểu đồ
    chart_path = analyzer.visualize_volume_profile('BTCUSDT')
    print(f"\nĐã tạo biểu đồ volume profile tại: {chart_path}")