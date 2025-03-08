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
                },
                'patterns': []  # For returning patterns from pattern analysis
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
            
            # Sắp xếp và lọc các vùng gần nhau
            support_levels = self._filter_close_levels(list(support_levels))
            resistance_levels = self._filter_close_levels(list(resistance_levels))
            
            # Cập nhật key levels
            if symbol not in self.key_levels:
                self.key_levels[symbol] = {}
                
            self.key_levels[symbol]['support_levels'] = support_levels
            self.key_levels[symbol]['resistance_levels'] = resistance_levels
            
            # Lấy các mức quan trọng nhất
            top_support = sorted(support_levels, reverse=True)[:self.config['significant_levels']]
            top_resistance = sorted(resistance_levels)[:self.config['significant_levels']]
            
            result = {
                'symbol': symbol,
                'current_price': current_price,
                'support_levels': top_support,
                'resistance_levels': top_resistance,
                'all_support_levels': support_levels,
                'all_resistance_levels': resistance_levels,
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi xác định vùng hỗ trợ/kháng cự: {str(e)}")
            return {}
    
    def identify_vwap_zones(self, df: pd.DataFrame, period: str = 'day') -> Dict:
        """
        Tính toán VWAP (Volume Weighted Average Price) và xác định các vùng VWAP.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu nến
            period (str): Chu kỳ tính VWAP ('day', 'week', 'month')
            
        Returns:
            Dict: Thông tin về VWAP và các vùng dựa trên VWAP
        """
        try:
            if df.empty:
                return {'vwap': None, 'bands': {}}
                
            # Đảm bảo có các cột cần thiết
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                logger.warning("DataFrame thiếu các cột cần thiết để tính VWAP")
                return {'vwap': None, 'bands': {}}
                
            # Sao chép để tránh cảnh báo SettingWithCopyWarning
            data = df.copy()
            
            # Tạo cột timestamp từ index nếu có
            if isinstance(data.index, pd.DatetimeIndex):
                data['timestamp'] = data.index
            
            # Xác định chu kỳ tính VWAP
            if period == 'day':
                # Tính VWAP theo ngày
                data['typical_price'] = (data['high'] + data['low'] + data['close']) / 3
                data['price_volume'] = data['typical_price'] * data['volume']
                
                # Cumsum cho toàn bộ data frame (đơn giản hóa)
                data['cumulative_volume'] = data['volume'].cumsum()
                data['cumulative_price_volume'] = data['price_volume'].cumsum()
                
                # VWAP
                data['vwap'] = data['cumulative_price_volume'] / data['cumulative_volume']
                
            elif period == 'week':
                # Tính VWAP theo tuần - cần có cột timestamp
                if 'timestamp' not in data.columns:
                    logger.warning("Không thể tính VWAP theo tuần vì thiếu timestamp")
                    return {'vwap': None, 'bands': {}}
                
                data['typical_price'] = (data['high'] + data['low'] + data['close']) / 3
                data['price_volume'] = data['typical_price'] * data['volume']
                
                # Xác định tuần
                data['week'] = data['timestamp'].dt.isocalendar().week
                
                # Tính cumsum theo từng tuần
                grouped = data.groupby('week')
                data['cumulative_volume'] = grouped['volume'].cumsum()
                data['cumulative_price_volume'] = grouped['price_volume'].cumsum()
                
                # VWAP
                data['vwap'] = data['cumulative_price_volume'] / data['cumulative_volume']
                
            else:  # period == 'month'
                # Tính VWAP theo tháng
                if 'timestamp' not in data.columns:
                    logger.warning("Không thể tính VWAP theo tháng vì thiếu timestamp")
                    return {'vwap': None, 'bands': {}}
                
                data['typical_price'] = (data['high'] + data['low'] + data['close']) / 3
                data['price_volume'] = data['typical_price'] * data['volume']
                
                # Xác định tháng
                data['month'] = data['timestamp'].dt.month
                
                # Tính cumsum theo từng tháng
                grouped = data.groupby('month')
                data['cumulative_volume'] = grouped['volume'].cumsum()
                data['cumulative_price_volume'] = grouped['price_volume'].cumsum()
                
                # VWAP
                data['vwap'] = data['cumulative_price_volume'] / data['cumulative_volume']
            
            # Tính VWAP bands
            # Tính độ lệch chuẩn của (giá - VWAP)
            data['price_deviation'] = data['close'] - data['vwap']
            stdev = data['price_deviation'].std()
            
            # Tính các bands
            bands = {
                'upper_1sd': data['vwap'].iloc[-1] + stdev,
                'upper_2sd': data['vwap'].iloc[-1] + 2*stdev,
                'upper_3sd': data['vwap'].iloc[-1] + 3*stdev,
                'lower_1sd': data['vwap'].iloc[-1] - stdev,
                'lower_2sd': data['vwap'].iloc[-1] - 2*stdev,
                'lower_3sd': data['vwap'].iloc[-1] - 3*stdev
            }
            
            # VWAP hiện tại
            current_vwap = data['vwap'].iloc[-1]
            
            # Kết quả
            result = {
                'vwap': current_vwap,
                'bands': bands,
                'period': period,
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi tính VWAP: {str(e)}")
            return {'vwap': None, 'bands': {}}
            
    def visualize_vwap_zones(self, df: pd.DataFrame, symbol: str = 'TESTDATA', period: str = 'day', 
                           save_path: str = None, custom_path: str = None) -> str:
        """
        Tạo biểu đồ VWAP và các bands.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu nến
            symbol (str): Ký hiệu của cặp tiền tệ (e.g. 'BTCUSDT')
            period (str): Chu kỳ tính VWAP ('day', 'week', 'month')
            save_path (str, optional): Đường dẫn đầy đủ lưu biểu đồ
            custom_path (str, optional): Đường dẫn tùy chỉnh đến thư mục lưu biểu đồ
            
        Returns:
            str: Đường dẫn đến biểu đồ đã lưu
        """
        try:
            # Tính VWAP
            vwap_data = self.identify_vwap_zones(df, period)
            
            if vwap_data['vwap'] is None:
                logger.warning("Không thể tạo biểu đồ VWAP vì thiếu dữ liệu")
                return ""
                
            # Sao chép để tránh cảnh báo
            data = df.copy()
            
            # Tạo VWAP và bands
            data['vwap'] = self.identify_vwap_zones(data, period)['vwap']
            
            # Tính các bands 
            vwap_val = vwap_data['vwap']
            bands = vwap_data['bands']
            
            # Tạo biểu đồ
            plt.figure(figsize=(12, 8))
            
            # Vẽ giá đóng cửa
            plt.plot(data.index, data['close'], label='Close Price', color='black', alpha=0.7)
            
            # Vẽ VWAP
            plt.plot(data.index, [vwap_val] * len(data), label='VWAP', color='blue', linewidth=2)
            
            # Vẽ các bands
            plt.plot(data.index, [bands['upper_1sd']] * len(data), '--', label='+1 SD', color='green', alpha=0.6)
            plt.plot(data.index, [bands['upper_2sd']] * len(data), '--', label='+2 SD', color='green', alpha=0.5)
            plt.plot(data.index, [bands['upper_3sd']] * len(data), '--', label='+3 SD', color='green', alpha=0.4)
            
            plt.plot(data.index, [bands['lower_1sd']] * len(data), '--', label='-1 SD', color='red', alpha=0.6)
            plt.plot(data.index, [bands['lower_2sd']] * len(data), '--', label='-2 SD', color='red', alpha=0.5)
            plt.plot(data.index, [bands['lower_3sd']] * len(data), '--', label='-3 SD', color='red', alpha=0.4)
            
            # Thêm thông tin
            plt.title(f'VWAP Analysis ({period.capitalize()})', fontsize=14)
            plt.grid(True, alpha=0.3)
            plt.legend(loc='best')
            
            # Lưu biểu đồ
            if save_path is None:
                if custom_path is not None:
                    save_dir = custom_path
                else:
                    save_dir = 'charts/vwap'
                os.makedirs(save_dir, exist_ok=True)
                save_path = f"{save_dir}/vwap_{symbol}_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                
            plt.savefig(save_path)
            plt.close()
            
            return save_path
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ VWAP: {str(e)}")
            return ""
            
    def visualize_volume_profile(self, df: pd.DataFrame, lookback_periods: int = None, 
                               save_path: str = None, custom_path: str = None) -> str:
        """
        Tạo biểu đồ volume profile.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu nến
            lookback_periods (int, optional): Số nến lấy để vẽ biểu đồ
            save_path (str, optional): Đường dẫn đầy đủ lưu biểu đồ
            custom_path (str, optional): Đường dẫn tùy chỉnh đến thư mục lưu biểu đồ
            
        Returns:
            str: Đường dẫn đến biểu đồ đã lưu
        """
        try:
            if df.empty:
                logger.warning("DataFrame trống, không thể tạo biểu đồ")
                return ""
                
            # Tính Volume Profile
            symbol = "TESTDATA"  # Giá trị mặc định cho dữ liệu test
            
            # Lọc dữ liệu theo lookback_periods nếu cần
            filtered_df = df
            if lookback_periods is not None and lookback_periods > 0:
                filtered_df = df.iloc[-lookback_periods:]
                
            # Tính toán volume profile
            profile = self.calculate_volume_profile(filtered_df, symbol, 'session')
            
            if not profile:
                logger.warning("Không thể tính toán volume profile")
                return ""
                
            # Chuyển đổi dữ liệu
            profile_data = pd.DataFrame(profile.get('profile_data', []))
            
            if profile_data.empty:
                logger.warning("Dữ liệu profile rỗng")
                return ""
                
            # Point of Control và Value Area
            poc = profile.get('poc')
            va_high = profile.get('value_area', {}).get('high')
            va_low = profile.get('value_area', {}).get('low')
            
            # Tạo biểu đồ
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Vẽ volume profile (horizontal bars)
            ax.barh(profile_data['price_mid'], profile_data['volume'], 
                   height=profile_data['price_high'] - profile_data['price_low'],
                   color='skyblue', alpha=0.7)
            
            # Vẽ POC
            if poc:
                ax.axhline(y=poc, color='red', linestyle='-', linewidth=2, 
                          label=f'POC: {poc:.2f}')
            
            # Vẽ Value Area
            if va_high and va_low:
                ax.axhspan(va_low, va_high, alpha=0.2, color='green', 
                          label=f'Value Area: {va_low:.2f} - {va_high:.2f}')
            
            # Vẽ giá hiện tại
            current_price = df['close'].iloc[-1]
            ax.axhline(y=current_price, color='blue', linestyle='--', linewidth=1.5,
                      label=f'Current Price: {current_price:.2f}')
            
            # Định dạng biểu đồ
            periods_text = f"(Last {lookback_periods} periods)" if lookback_periods else ""
            ax.set_title(f'Volume Profile Analysis {periods_text}', fontsize=14)
            ax.set_xlabel('Volume')
            ax.set_ylabel('Price')
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper left')
            
            # Lưu biểu đồ
            if save_path is None:
                if custom_path is not None:
                    save_dir = custom_path
                else:
                    save_dir = 'charts/volume_profile'
                os.makedirs(save_dir, exist_ok=True)
                save_path = f"{save_dir}/volume_profile_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                
            plt.tight_layout()
            plt.savefig(save_path)
            plt.close()
            
            return save_path
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ volume profile: {str(e)}")
            return ""
    
    def _filter_data_by_profile_type(self, df: pd.DataFrame, profile_type: str) -> pd.DataFrame:
        """
        Lọc dữ liệu theo loại profile.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu nến
            profile_type (str): Loại profile ('session', 'daily', 'weekly', 'monthly')
            
        Returns:
            pd.DataFrame: DataFrame đã lọc
        """
        # Với session profile, sử dụng toàn bộ dữ liệu  
        if profile_type == 'session':
            # Lấy dữ liệu cho session hiện tại (ví dụ: 24 nến gần nhất)
            return df.iloc[-self.config['lookback_periods']:]
        
        # Với daily profile, lọc dữ liệu theo ngày
        elif profile_type == 'daily':
            # Kiểm tra xem df có datetime index không
            if isinstance(df.index, pd.DatetimeIndex):
                # Lấy dữ liệu những ngày gần nhất
                start_date = df.index[-1] - timedelta(days=1)
                return df[df.index >= start_date]
            else:
                # Nếu không có datetime index, lấy 24 nến gần nhất (giả định 1 ngày)
                return df.iloc[-24:]
        
        # Với weekly profile, lọc dữ liệu theo tuần
        elif profile_type == 'weekly':
            if isinstance(df.index, pd.DatetimeIndex):
                # Lấy dữ liệu tuần gần nhất
                start_date = df.index[-1] - timedelta(days=7)
                return df[df.index >= start_date]
            else:
                # Nếu không có datetime index, lấy 168 nến gần nhất (giả định 1 tuần = 7 ngày * 24 giờ)
                return df.iloc[-168:]
        
        # Với monthly profile, lọc dữ liệu theo tháng
        elif profile_type == 'monthly':
            if isinstance(df.index, pd.DatetimeIndex):
                # Lấy dữ liệu tháng gần nhất
                start_date = df.index[-1] - timedelta(days=30)
                return df[df.index >= start_date]
            else:
                # Nếu không có datetime index, lấy 720 nến gần nhất (giả định 1 tháng = 30 ngày * 24 giờ)
                return df.iloc[-720:]
        
        # Mặc định trả về toàn bộ dữ liệu
        return df
    
    def _update_key_levels(self, symbol: str, profile_data: Dict) -> None:
        """
        Cập nhật vùng giá quan trọng cho cặp tiền.
        
        Args:
            symbol (str): Cặp tiền
            profile_data (Dict): Dữ liệu volume profile
        """
        # Khởi tạo key levels nếu chưa có
        if symbol not in self.key_levels:
            self.key_levels[symbol] = {
                'support_levels': [],
                'resistance_levels': [],
                'poc': None,
                'value_area': {'high': None, 'low': None}
            }
            
        # Cập nhật POC (Point of Control)
        if 'poc' in profile_data:
            self.key_levels[symbol]['poc'] = profile_data['poc']
            
        # Cập nhật Value Area
        if 'value_area' in profile_data:
            self.key_levels[symbol]['value_area'] = profile_data['value_area']
    
    def _filter_close_levels(self, levels: List[float], threshold_pct: float = 0.5) -> List[float]:
        """
        Lọc và gộp các mức giá gần nhau.
        
        Args:
            levels (List[float]): Danh sách các mức giá
            threshold_pct (float): Ngưỡng phần trăm để lọc (% của giá)
            
        Returns:
            List[float]: Danh sách các mức giá đã lọc
        """
        if not levels:
            return []
            
        # Sắp xếp tăng dần
        sorted_levels = sorted(levels)
        
        # Tính threshold
        avg_price = sum(sorted_levels) / len(sorted_levels)
        threshold = avg_price * threshold_pct / 100  # % của giá trung bình
        
        # Gộp các mức gần nhau
        filtered_levels = []
        current_group = [sorted_levels[0]]
        
        for i in range(1, len(sorted_levels)):
            # Nếu mức giá hiện tại gần với mức giá trước đó, thêm vào nhóm hiện tại
            if sorted_levels[i] - sorted_levels[i-1] < threshold:
                current_group.append(sorted_levels[i])
            else:
                # Nếu không, tính trung bình cho nhóm hiện tại và bắt đầu nhóm mới
                filtered_levels.append(sum(current_group) / len(current_group))
                current_group = [sorted_levels[i]]
                
        # Thêm nhóm cuối cùng
        if current_group:
            filtered_levels.append(sum(current_group) / len(current_group))
            
        return filtered_levels
        
    def _save_profile_data(self, symbol: str) -> None:
        """
        Lưu profile data vào file để phân tích sau.
        
        Args:
            symbol (str): Cặp tiền phân tích
        """
        try:
            file_path = os.path.join(self.data_storage_path, f"{symbol}_profiles.json")
            
            # Chuyển đổi profile data thành JSON
            profile_data = {}
            if symbol in self.profiles:
                profile_data = {
                    profile_type: {
                        k: v for k, v in profile.items() 
                        if k != 'profile_data'  # Loại bỏ dữ liệu lớn
                    }
                    for profile_type, profile in self.profiles[symbol].items()
                }
            
            with open(file_path, 'w') as f:
                json.dump(profile_data, f, indent=2)
                
            # Lưu key levels
            key_levels_path = os.path.join(self.data_storage_path, f"{symbol}_key_levels.json")
            if symbol in self.key_levels:
                with open(key_levels_path, 'w') as f:
                    json.dump(self.key_levels[symbol], f, indent=2)
                    
            logger.debug(f"Đã lưu dữ liệu volume profile cho {symbol}")
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu volume profile: {str(e)}")