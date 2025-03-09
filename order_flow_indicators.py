"""
Order Flow Indicators - Phân tích dòng lệnh trong thị trường

Module này cung cấp các công cụ phân tích dòng lệnh (Order Flow) để hiểu rõ hơn
về áp lực mua/bán, phân bố khối lượng, và các yếu tố quan trọng khác dưới mức nến.
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
logger = logging.getLogger('order_flow_indicators')

class OrderFlowAnalyzer:
    """
    Phân tích dòng lệnh và áp lực mua/bán trong thị trường cryptocurrency.
    
    Cung cấp các công cụ để phân tích:
    - Cumulative Delta: Chênh lệch tích lũy giữa khối lượng mua và bán
    - Order Imbalance: Mất cân bằng giữa lệnh mua và bán
    - Liquidity Levels: Các mức thanh khoản quan trọng
    - Volume Profile và Point of Control
    """
    
    def __init__(self, data_storage_path='data/order_flow'):
        """
        Khởi tạo Order Flow Analyzer.
        
        Args:
            data_storage_path (str): Đường dẫn lưu trữ dữ liệu order flow
        """
        self.data_storage_path = data_storage_path
        
        # Lưu trữ dữ liệu phân tích
        self.order_flow_data = {}  # {symbol: {timestamp: data}}
        self.liquidity_data = {}   # {symbol: {levels: [price levels], volumes: [volumes]}}
        self.delta_data = {}       # {symbol: {timestamp: delta}}
        self.imbalance_data = {}   # {symbol: {timestamp: imbalance_ratio}}
        
        # Cấu hình
        self.config = {
            # Các ngưỡng phát hiện
            'significant_volume_ratio': 2.0,     # Tỷ lệ khối lượng để coi là đáng kể
            'liquidity_cluster_threshold': 1.5,  # Ngưỡng để gom các vùng thanh khoản
            'delta_significance': 0.6,           # Ngưỡng delta để xác định xu hướng
            'signal_lookback': 5,                # Số nến để xác định xu hướng
            
            # Khung thời gian lưu trữ
            'storage_days': 7,                   # Số ngày lưu dữ liệu
            
            # Các tham số mô phỏng
            'buy_sell_ratio_volatility': 0.2,    # Biến động trong tỷ lệ mua/bán mô phỏng
            'price_impact_factor': 0.5,          # Mức ảnh hưởng của khối lượng lên giá
            'liquidity_density': 20,             # Số điểm thanh khoản mô phỏng
            'simulation_seed': 42                # Seed cho tính toán mô phỏng
        }
        
        # Tạo thư mục lưu trữ
        os.makedirs(data_storage_path, exist_ok=True)
        
        # Đặt seed cho mô phỏng
        np.random.seed(self.config['simulation_seed'])
    
    def simulate_from_candle_data(self, symbol: str, df: pd.DataFrame) -> None:
        """
        Mô phỏng dữ liệu order flow từ dữ liệu nến OHLCV.
        
        Args:
            symbol (str): Cặp tiền tệ
            df (pd.DataFrame): DataFrame chứa dữ liệu nến OHLCV
        """
        try:
            if df.empty:
                logger.warning(f"DataFrame trống, không thể mô phỏng order flow cho {symbol}")
                return
                
            # Đảm bảo các cột cần thiết tồn tại
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in df.columns:
                    logger.warning(f"Thiếu cột {col} trong dữ liệu")
                    return
            
            # Tạo thư mục lưu trữ theo symbol
            symbol_path = os.path.join(self.data_storage_path, symbol)
            os.makedirs(symbol_path, exist_ok=True)
            
            # Khởi tạo dữ liệu cho symbol
            if symbol not in self.order_flow_data:
                self.order_flow_data[symbol] = {}
                self.liquidity_data[symbol] = {'levels': [], 'volumes': []}
                self.delta_data[symbol] = {}
                self.imbalance_data[symbol] = {}
            
            # Mô phỏng dữ liệu order flow cho mỗi nến
            for idx, row in df.iterrows():
                timestamp = idx.isoformat() if isinstance(idx, pd.Timestamp) else str(idx)
                
                # Mô phỏng tỷ lệ khối lượng mua/bán dựa trên biến động giá
                price_change = row['close'] - row['open']
                price_range = row['high'] - row['low']
                
                # Tính tỷ lệ mua/bán dựa trên biến động giá
                # Nếu giá tăng: tỷ lệ mua > bán, giá giảm: tỷ lệ bán > mua
                if price_range > 0:
                    # Chuẩn hóa biến đổi giá thành tỷ lệ từ -1 đến 1
                    normalized_change = price_change / price_range
                    
                    # Thêm nhiễu
                    noise = np.random.normal(0, self.config['buy_sell_ratio_volatility'])
                    buy_ratio = 0.5 + (normalized_change + noise) / 2
                    
                    # Giới hạn trong khoảng 0.1 - 0.9 để tránh các giá trị cực đoan
                    buy_ratio = min(max(buy_ratio, 0.1), 0.9)
                else:
                    # Nếu giá không thay đổi, coi như 50-50
                    buy_ratio = 0.5
                
                sell_ratio = 1 - buy_ratio
                
                # Tính khối lượng mua và bán dựa trên tỷ lệ
                buy_volume = row['volume'] * buy_ratio
                sell_volume = row['volume'] * sell_ratio
                
                # Tính delta (chênh lệch mua - bán)
                delta = buy_volume - sell_volume
                
                # Tính tỷ lệ mất cân bằng (imbalance) đơn giản
                imbalance_ratio = delta / row['volume'] if row['volume'] > 0 else 0
                
                # Lưu dữ liệu
                self.order_flow_data[symbol][timestamp] = {
                    'buy_volume': buy_volume,
                    'sell_volume': sell_volume,
                    'delta': delta,
                    'imbalance_ratio': imbalance_ratio,
                    'price_range': price_range,
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close'],
                    'total_volume': row['volume']
                }
                
                self.delta_data[symbol][timestamp] = delta
                self.imbalance_data[symbol][timestamp] = imbalance_ratio
            
            # Mô phỏng các mức thanh khoản dựa trên giá
            self._simulate_liquidity_levels(symbol, df)
            
            # Lưu dữ liệu
            self._save_order_flow_data(symbol)
            
            logger.info(f"Đã mô phỏng dữ liệu order flow cho {symbol} từ {len(df)} nến")
            
        except Exception as e:
            logger.error(f"Lỗi khi mô phỏng order flow: {str(e)}")
    
    def get_order_flow_signals(self, symbol: str, df: pd.DataFrame = None) -> Dict:
        """
        Lấy tín hiệu dựa trên phân tích order flow.
        
        Args:
            symbol (str): Cặp tiền tệ
            df (pd.DataFrame, optional): DataFrame chứa dữ liệu nến mới nhất
            
        Returns:
            Dict: Các tín hiệu order flow
        """
        try:
            # Nếu có df mới, cập nhật mô phỏng
            if df is not None and not df.empty:
                self.simulate_from_candle_data(symbol, df)
            
            # Kiểm tra dữ liệu
            if symbol not in self.order_flow_data or not self.order_flow_data[symbol]:
                logger.warning(f"Không có dữ liệu order flow cho {symbol}")
                return {
                    'signals': {
                        'buy_signal': False,
                        'sell_signal': False,
                        'neutral': True,
                        'strength': 0.0
                    },
                    'key_levels': {
                        'support': [],
                        'resistance': []
                    },
                    'liquidity': {
                        'ratio': 1.0,
                        'above_price': 0,
                        'below_price': 0
                    }
                }
            
            # Lấy n dòng dữ liệu gần nhất
            n = self.config['signal_lookback']
            recent_data = list(self.order_flow_data[symbol].values())[-n:]
            
            if not recent_data:
                logger.warning(f"Không đủ dữ liệu gần đây cho {symbol}")
                return {
                    'signals': {
                        'buy_signal': False,
                        'sell_signal': False,
                        'neutral': True,
                        'strength': 0.0
                    }
                }
            
            # Tính tích lũy delta gần đây
            recent_delta = sum(item['delta'] for item in recent_data)
            recent_volume = sum(item['total_volume'] for item in recent_data)
            
            delta_ratio = recent_delta / recent_volume if recent_volume > 0 else 0
            
            # Xác định tín hiệu mua/bán dựa trên delta và imbalance
            buy_signal = delta_ratio > self.config['delta_significance']
            sell_signal = delta_ratio < -self.config['delta_significance']
            neutral = not (buy_signal or sell_signal)
            
            # Tính độ mạnh tín hiệu (0-1)
            signal_strength = abs(delta_ratio)
            
            # Lấy giá hiện tại
            current_price = recent_data[-1]['close']
            
            # Xác định các mức hỗ trợ/kháng cự
            support_levels, resistance_levels = self._identify_key_levels(symbol, current_price)
            
            # Đánh giá thanh khoản trên/dưới giá hiện tại
            liquidity_above, liquidity_below = self._assess_liquidity(symbol, current_price)
            liquidity_ratio = liquidity_above / liquidity_below if liquidity_below > 0 else 1.0
            
            # Tạo kết quả
            result = {
                'signals': {
                    'buy_signal': buy_signal,
                    'sell_signal': sell_signal,
                    'neutral': neutral,
                    'strength': signal_strength
                },
                'key_levels': {
                    'support': support_levels,
                    'resistance': resistance_levels
                },
                'liquidity': {
                    'ratio': liquidity_ratio,
                    'above_price': liquidity_above,
                    'below_price': liquidity_below
                },
                'extra_info': {
                    'cumulative_delta': recent_delta,
                    'delta_ratio': delta_ratio,
                    'current_price': current_price
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy tín hiệu order flow: {str(e)}")
            return {
                'signals': {
                    'buy_signal': False,
                    'sell_signal': False,
                    'neutral': True,
                    'strength': 0.0
                },
                'error': str(e)
            }
    
    def get_cumulative_delta(self, symbol: str, timeframe: str = 'recent') -> float:
        """
        Lấy delta tích lũy (chênh lệch mua - bán).
        
        Args:
            symbol (str): Cặp tiền tệ
            timeframe (str): Khung thời gian ('recent', 'daily', 'all')
            
        Returns:
            float: Delta tích lũy
        """
        try:
            if symbol not in self.delta_data or not self.delta_data[symbol]:
                return 0.0
                
            # Lấy tất cả giá trị delta
            all_deltas = list(self.delta_data[symbol].values())
            
            if timeframe == 'recent':
                # Lấy n giá trị gần nhất
                n = min(self.config['signal_lookback'], len(all_deltas))
                return sum(all_deltas[-n:])
            elif timeframe == 'daily':
                # Lấy khoảng 24h gần nhất (tương đương daily)
                n = min(24, len(all_deltas))
                return sum(all_deltas[-n:])
            else:
                # Lấy tất cả
                return sum(all_deltas)
                
        except Exception as e:
            logger.error(f"Lỗi khi lấy delta tích lũy: {str(e)}")
            return 0.0
    
    def get_order_imbalance(self, symbol: str, timeframe: str = 'recent') -> float:
        """
        Lấy tỷ lệ mất cân bằng giữa lệnh mua và bán.
        
        Args:
            symbol (str): Cặp tiền tệ
            timeframe (str): Khung thời gian ('recent', 'daily', 'all')
            
        Returns:
            float: Tỷ lệ mất cân bằng (-1 đến 1, âm = áp lực bán, dương = áp lực mua)
        """
        try:
            if symbol not in self.imbalance_data or not self.imbalance_data[symbol]:
                return 0.0
                
            # Lấy tất cả giá trị imbalance
            all_imbalances = list(self.imbalance_data[symbol].values())
            
            if timeframe == 'recent':
                # Lấy n giá trị gần nhất
                n = min(self.config['signal_lookback'], len(all_imbalances))
                imbalances = all_imbalances[-n:]
            elif timeframe == 'daily':
                # Lấy khoảng 24h gần nhất
                n = min(24, len(all_imbalances))
                imbalances = all_imbalances[-n:]
            else:
                # Lấy tất cả
                imbalances = all_imbalances
                
            # Tính trung bình
            return sum(imbalances) / len(imbalances) if imbalances else 0.0
                
        except Exception as e:
            logger.error(f"Lỗi khi lấy tỷ lệ mất cân bằng lệnh: {str(e)}")
            return 0.0
    
    def visualize_delta_flow(self, symbol: str, output_path: Optional[str] = None) -> str:
        """
        Tạo biểu đồ dòng chảy delta.
        
        Args:
            symbol (str): Cặp tiền tệ
            output_path (str, optional): Đường dẫn lưu biểu đồ
            
        Returns:
            str: Đường dẫn đến biểu đồ
        """
        try:
            if symbol not in self.order_flow_data or not self.order_flow_data[symbol]:
                logger.warning(f"Không có dữ liệu order flow cho {symbol}")
                return ""
                
            # Tạo DataFrame từ dữ liệu
            data = []
            timestamps = []
            
            for timestamp, values in self.order_flow_data[symbol].items():
                data.append({
                    'close': values['close'],
                    'delta': values['delta'],
                    'buy_volume': values['buy_volume'],
                    'sell_volume': values['sell_volume'],
                    'imbalance_ratio': values['imbalance_ratio']
                })
                timestamps.append(timestamp)
                
            df = pd.DataFrame(data)
            df.index = timestamps
            
            # Tạo đường dẫn lưu biểu đồ nếu không cung cấp
            if not output_path:
                symbol_dir = os.path.join(self.data_storage_path, symbol)
                os.makedirs(symbol_dir, exist_ok=True)
                output_path = os.path.join(symbol_dir, f"{symbol}_delta_flow.png")
                
            # Tạo biểu đồ
            plt.figure(figsize=(12, 8))
            
            # Subplot 1: Giá
            plt.subplot(3, 1, 1)
            plt.plot(df.index, df['close'], 'b-')
            plt.title(f'{symbol} Price')
            plt.grid(True, alpha=0.3)
            
            # Subplot 2: Delta
            plt.subplot(3, 1, 2)
            plt.bar(df.index, df['delta'], color=['g' if d > 0 else 'r' for d in df['delta']])
            plt.title('Delta (Buy - Sell Volume)')
            plt.grid(True, alpha=0.3)
            
            # Subplot 3: Mất cân bằng
            plt.subplot(3, 1, 3)
            plt.plot(df.index, df['imbalance_ratio'], 'purple')
            plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            plt.axhline(y=self.config['delta_significance'], color='green', linestyle='--', alpha=0.7)
            plt.axhline(y=-self.config['delta_significance'], color='red', linestyle='--', alpha=0.7)
            plt.title('Order Imbalance Ratio')
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(output_path)
            plt.close()
            
            logger.info(f"Đã tạo biểu đồ delta flow tại: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ delta flow: {str(e)}")
            return ""
    
    def analyze_liquidity_distribution(self, symbol: str) -> Dict:
        """
        Phân tích phân bố thanh khoản.
        
        Args:
            symbol (str): Cặp tiền tệ
            
        Returns:
            Dict: Kết quả phân tích thanh khoản
        """
        try:
            if symbol not in self.liquidity_data or not self.liquidity_data[symbol]:
                logger.warning(f"Không có dữ liệu thanh khoản cho {symbol}")
                return {}
                
            # Lấy dữ liệu thanh khoản
            levels = self.liquidity_data[symbol]['levels']
            volumes = self.liquidity_data[symbol]['volumes']
            
            if not levels or not volumes:
                return {}
                
            # Tìm mức có thanh khoản cao nhất
            max_idx = np.argmax(volumes)
            max_liquidity_level = levels[max_idx]
            max_liquidity_volume = volumes[max_idx]
            
            # Tìm mức có thanh khoản thấp nhất
            min_idx = np.argmin(volumes)
            min_liquidity_level = levels[min_idx]
            min_liquidity_volume = volumes[min_idx]
            
            # Tìm các cụm thanh khoản (liquidity clusters)
            clusters = self._find_liquidity_clusters(levels, volumes)
            
            # Lấy giá mới nhất
            latest_data = list(self.order_flow_data[symbol].values())[-1] if self.order_flow_data[symbol] else None
            current_price = latest_data['close'] if latest_data else None
            
            # Tính toán mức trung bình và phân phối
            avg_liquidity = np.mean(volumes)
            std_liquidity = np.std(volumes)
            median_liquidity = np.median(volumes)
            
            # Tạo kết quả
            result = {
                'symbol': symbol,
                'max_liquidity': {
                    'price': max_liquidity_level,
                    'volume': max_liquidity_volume
                },
                'min_liquidity': {
                    'price': min_liquidity_level,
                    'volume': min_liquidity_volume
                },
                'liquidity_clusters': clusters,
                'current_price': current_price,
                'statistics': {
                    'avg_liquidity': avg_liquidity,
                    'median_liquidity': median_liquidity,
                    'std_liquidity': std_liquidity
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích phân bố thanh khoản: {str(e)}")
            return {}
    
    def _simulate_liquidity_levels(self, symbol: str, df: pd.DataFrame) -> None:
        """
        Mô phỏng các mức thanh khoản dựa trên giá.
        
        Args:
            symbol (str): Cặp tiền tệ
            df (pd.DataFrame): DataFrame chứa dữ liệu nến
        """
        try:
            # Tìm phạm vi giá
            min_price = df['low'].min() * 0.99  # Giảm một chút để lấy cả phạm vi ngoài
            max_price = df['high'].max() * 1.01  # Tăng một chút để lấy cả phạm vi ngoài
            
            # Tạo số lượng mức thanh khoản
            n_levels = self.config['liquidity_density']
            
            # Tạo các mức giá ngẫu nhiên theo phân phối cụ thể
            # Chúng ta sẽ tập trung gấp đôi thanh khoản gần vùng có lịch sử giao dịch
            price_history = list(df['close']) + list(df['open']) + list(df['high']) + list(df['low'])
            
            # Chọn một số mức dựa trên lịch sử giá
            history_sample = np.random.choice(price_history, size=n_levels // 2)
            
            # Thêm nhiễu nhỏ để tránh quá tập trung
            history_levels = history_sample + np.random.normal(0, (max_price - min_price) * 0.005, size=n_levels // 2)
            
            # Tạo các mức ngẫu nhiên khác trong phạm vi giá
            random_levels = np.random.uniform(min_price, max_price, size=n_levels // 2)
            
            # Kết hợp các mức
            all_levels = np.concatenate([history_levels, random_levels])
            
            # Mô phỏng khối lượng cho mỗi mức
            # Sử dụng phân phối lognormal để có một số mức có khối lượng rất cao (mô phỏng các vùng thanh khoản lớn)
            base_volumes = np.random.lognormal(mean=0, sigma=1, size=n_levels)
            
            # Điều chỉnh khối lượng dựa trên khoảng cách đến giá gần nhất trong lịch sử
            volumes = []
            for level in all_levels:
                # Tìm khoảng cách đến giá gần nhất trong lịch sử
                distances = np.abs(np.array(price_history) - level)
                min_distance = distances.min()
                
                # Tính hệ số dựa trên khoảng cách (càng gần càng có khả năng có thanh khoản cao)
                distance_factor = np.exp(-min_distance / (max_price - min_price) * 10)
                
                # Lấy khối lượng cơ sở và điều chỉnh theo khoảng cách
                base_idx = len(volumes) % len(base_volumes)
                adjusted_volume = base_volumes[base_idx] * (1 + distance_factor * 2)
                
                volumes.append(adjusted_volume)
            
            # Chuẩn hóa khối lượng
            volumes = np.array(volumes)
            volumes = volumes / volumes.sum() * df['volume'].sum()
            
            # Lưu kết quả
            self.liquidity_data[symbol] = {
                'levels': all_levels.tolist(),
                'volumes': volumes.tolist()
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi mô phỏng các mức thanh khoản: {str(e)}")
    
    def _identify_key_levels(self, symbol: str, current_price: float) -> Tuple[List[float], List[float]]:
        """
        Xác định các mức giá quan trọng (hỗ trợ/kháng cự) dựa trên thanh khoản.
        
        Args:
            symbol (str): Cặp tiền tệ
            current_price (float): Giá hiện tại
            
        Returns:
            Tuple[List[float], List[float]]: Danh sách (mức hỗ trợ, mức kháng cự)
        """
        try:
            if symbol not in self.liquidity_data or not self.liquidity_data[symbol]:
                return [], []
                
            # Lấy dữ liệu thanh khoản
            levels = np.array(self.liquidity_data[symbol]['levels'])
            volumes = np.array(self.liquidity_data[symbol]['volumes'])
            
            if len(levels) == 0 or len(volumes) == 0:
                return [], []
                
            # Tính ngưỡng khối lượng đáng kể
            avg_volume = np.mean(volumes)
            significant_threshold = avg_volume * self.config['significant_volume_ratio']
            
            # Tìm các mức có khối lượng đáng kể
            significant_indices = np.where(volumes >= significant_threshold)[0]
            significant_levels = levels[significant_indices]
            
            # Lọc thành hỗ trợ (dưới giá hiện tại) và kháng cự (trên giá hiện tại)
            support_levels = significant_levels[significant_levels < current_price]
            resistance_levels = significant_levels[significant_levels > current_price]
            
            # Sắp xếp theo khoảng cách đến giá hiện tại
            support_levels = sorted(support_levels, reverse=True)  # Gần nhất đầu tiên
            resistance_levels = sorted(resistance_levels)  # Gần nhất đầu tiên
            
            # Giới hạn số lượng mức trả về
            max_levels = 5
            support_levels = support_levels[:max_levels]
            resistance_levels = resistance_levels[:max_levels]
            
            return support_levels, resistance_levels
            
        except Exception as e:
            logger.error(f"Lỗi khi xác định mức giá quan trọng: {str(e)}")
            return [], []
    
    def _assess_liquidity(self, symbol: str, current_price: float) -> Tuple[float, float]:
        """
        Đánh giá thanh khoản trên và dưới mức giá hiện tại.
        
        Args:
            symbol (str): Cặp tiền tệ
            current_price (float): Giá hiện tại
            
        Returns:
            Tuple[float, float]: (thanh khoản trên, thanh khoản dưới)
        """
        try:
            if symbol not in self.liquidity_data or not self.liquidity_data[symbol]:
                return 0.0, 0.0
                
            # Lấy dữ liệu thanh khoản
            levels = np.array(self.liquidity_data[symbol]['levels'])
            volumes = np.array(self.liquidity_data[symbol]['volumes'])
            
            if len(levels) == 0 or len(volumes) == 0:
                return 0.0, 0.0
                
            # Tìm các mức trên và dưới giá hiện tại
            above_indices = np.where(levels > current_price)[0]
            below_indices = np.where(levels < current_price)[0]
            
            # Tính tổng khối lượng
            liquidity_above = np.sum(volumes[above_indices]) if len(above_indices) > 0 else 0.0
            liquidity_below = np.sum(volumes[below_indices]) if len(below_indices) > 0 else 0.0
            
            return liquidity_above, liquidity_below
            
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá thanh khoản: {str(e)}")
            return 0.0, 0.0
    
    def _find_liquidity_clusters(self, levels: List[float], volumes: List[float]) -> List[Dict]:
        """
        Tìm các cụm thanh khoản.
        
        Args:
            levels (List[float]): Danh sách các mức giá
            volumes (List[float]): Danh sách khối lượng tương ứng
            
        Returns:
            List[Dict]: Danh sách các cụm thanh khoản
        """
        try:
            if not levels or not volumes:
                return []
                
            # Tính ngưỡng khối lượng đáng kể
            avg_volume = np.mean(volumes)
            significant_threshold = avg_volume * self.config['liquidity_cluster_threshold']
            
            # Tìm các mức có khối lượng đáng kể
            significant_indices = np.where(np.array(volumes) >= significant_threshold)[0]
            
            if len(significant_indices) == 0:
                return []
                
            # Sắp xếp theo mức giá
            indices = sorted(significant_indices, key=lambda i: levels[i])
            
            # Gom các mức giá gần nhau thành cụm
            clusters = []
            current_cluster = {
                'start_idx': indices[0],
                'end_idx': indices[0],
                'total_volume': volumes[indices[0]]
            }
            
            for i in range(1, len(indices)):
                curr_idx = indices[i]
                prev_idx = indices[i-1]
                
                # Nếu khoảng cách giữa hai mức liên tiếp nhỏ, gom vào cùng cụm
                if levels[curr_idx] - levels[prev_idx] < (max(levels) - min(levels)) * 0.02:  # 2% phạm vi
                    current_cluster['end_idx'] = curr_idx
                    current_cluster['total_volume'] += volumes[curr_idx]
                else:
                    # Thêm cụm hiện tại vào danh sách và tạo cụm mới
                    clusters.append(current_cluster)
                    current_cluster = {
                        'start_idx': curr_idx,
                        'end_idx': curr_idx,
                        'total_volume': volumes[curr_idx]
                    }
            
            # Thêm cụm cuối cùng
            clusters.append(current_cluster)
            
            # Tính thông tin chi tiết cho mỗi cụm
            result = []
            for cluster in clusters:
                cluster_indices = list(range(cluster['start_idx'], cluster['end_idx'] + 1))
                cluster_levels = [levels[i] for i in cluster_indices]
                cluster_volumes = [volumes[i] for i in cluster_indices]
                
                # Tính giá trung bình theo khối lượng
                volume_weighted_price = sum(l * v for l, v in zip(cluster_levels, cluster_volumes)) / sum(cluster_volumes)
                
                result.append({
                    'min_price': min(cluster_levels),
                    'max_price': max(cluster_levels),
                    'avg_price': volume_weighted_price,
                    'total_volume': sum(cluster_volumes),
                    'volume_ratio': sum(cluster_volumes) / sum(volumes)
                })
            
            # Sắp xếp theo khối lượng giảm dần
            result = sorted(result, key=lambda x: x['total_volume'], reverse=True)
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi tìm cụm thanh khoản: {str(e)}")
            return []
    
    def _save_order_flow_data(self, symbol: str) -> None:
        """
        Lưu dữ liệu order flow.
        
        Args:
            symbol (str): Cặp tiền tệ
        """
        try:
            symbol_dir = os.path.join(self.data_storage_path, symbol)
            os.makedirs(symbol_dir, exist_ok=True)
            
            # Lưu dữ liệu
            if symbol in self.order_flow_data:
                with open(os.path.join(symbol_dir, 'order_flow_data.json'), 'w') as f:
                    json.dump(self.order_flow_data[symbol], f, indent=2)
            
            if symbol in self.liquidity_data:
                with open(os.path.join(symbol_dir, 'liquidity_data.json'), 'w') as f:
                    json.dump(self.liquidity_data[symbol], f, indent=2)
                    
            if symbol in self.delta_data:
                with open(os.path.join(symbol_dir, 'delta_data.json'), 'w') as f:
                    json.dump(self.delta_data[symbol], f, indent=2)
                    
            if symbol in self.imbalance_data:
                with open(os.path.join(symbol_dir, 'imbalance_data.json'), 'w') as f:
                    json.dump(self.imbalance_data[symbol], f, indent=2)
                    
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu order flow: {str(e)}")


if __name__ == "__main__":
    # Ví dụ sử dụng
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    # Tạo dữ liệu mẫu
    days = 10
    now = datetime.now()
    dates = [now - timedelta(hours=i) for i in range(days * 24, 0, -1)]
    
    # Tạo giá theo mô hình đơn giản
    prices = []
    base_price = 50000  # BTC price
    for i in range(days * 24):
        # Tạo một số xu hướng
        if i < days * 24 * 0.3:  # Uptrend
            trend = 1000 * (i / (days * 24 * 0.3))
            noise = np.random.normal(0, 100)
        elif i < days * 24 * 0.6:  # Sideway
            trend = 1000
            noise = np.random.normal(0, 200)
        else:  # Downtrend
            trend = 1000 - 500 * ((i - days * 24 * 0.6) / (days * 24 * 0.4))
            noise = np.random.normal(0, 100)
            
        price = base_price + trend + noise
        prices.append(price)
    
    # Tạo DataFrame
    df = pd.DataFrame({
        'open': [prices[i-1] if i > 0 else prices[i] * 0.999 for i in range(days * 24)],
        'high': [p * (1 + 0.001 * np.random.random()) for p in prices],
        'low': [p * (1 - 0.001 * np.random.random()) for p in prices],
        'close': prices,
        'volume': [100 + 900 * np.random.random() for _ in range(days * 24)]
    }, index=dates)
    
    # Tạo analyzer
    analyzer = OrderFlowAnalyzer()
    
    # Mô phỏng order flow từ dữ liệu nến
    analyzer.simulate_from_candle_data('BTCUSDT', df)
    
    # Lấy tín hiệu
    signals = analyzer.get_order_flow_signals('BTCUSDT')
    
    print("=== Order Flow Signals ===")
    print(f"Buy Signal: {signals['signals']['buy_signal']}")
    print(f"Sell Signal: {signals['signals']['sell_signal']}")
    print(f"Neutral: {signals['signals']['neutral']}")
    print(f"Signal Strength: {signals['signals']['strength']:.2f}")
    
    # Lấy delta tích lũy
    delta = analyzer.get_cumulative_delta('BTCUSDT')
    print(f"\nCumulative Delta: {delta:.2f}")
    
    # Lấy tỷ lệ mất cân bằng
    imbalance = analyzer.get_order_imbalance('BTCUSDT')
    print(f"Order Imbalance: {imbalance:.2f}")
    
    # Phân tích thanh khoản
    liquidity = analyzer.analyze_liquidity_distribution('BTCUSDT')
    if liquidity:
        print("\n=== Liquidity Analysis ===")
        print(f"Max Liquidity Level: {liquidity['max_liquidity']['price']:.2f}")
        print(f"Current Price: {liquidity['current_price']:.2f}")
        
        print("\nLiquidity Clusters:")
        for i, cluster in enumerate(liquidity['liquidity_clusters'][:3]):
            print(f"Cluster {i+1}: {cluster['min_price']:.2f} - {cluster['max_price']:.2f}, Volume: {cluster['total_volume']:.2f}")
    
    # Tạo biểu đồ
    chart_path = analyzer.visualize_delta_flow('BTCUSDT')
    print(f"\nDelta Flow Chart: {chart_path}")