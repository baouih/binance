#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phát hiện thị trường đi ngang (sideways market) và tối ưu hóa giao dịch
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import logging
from datetime import datetime
import yfinance as yf

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('sideways_detector')

class SidewaysMarketDetector:
    """Lớp phát hiện thị trường đi ngang và tối ưu hóa giao dịch"""
    
    def __init__(self, 
                 atr_period=14, 
                 lookback_period=20, 
                 price_range_threshold=5.0, 
                 atr_volatility_threshold=2.0,
                 min_sideways_duration=5):
        """
        Khởi tạo bộ phát hiện thị trường đi ngang
        
        Args:
            atr_period: Số phiên giao dịch để tính ATR
            lookback_period: Số phiên giao dịch để xem xét
            price_range_threshold: Ngưỡng biên độ giá (%) để xác định thị trường đi ngang
            atr_volatility_threshold: Ngưỡng biến động ATR/Giá (%) để xác định thị trường đi ngang
            min_sideways_duration: Số phiên tối thiểu để xác nhận thị trường đi ngang
        """
        self.atr_period = atr_period
        self.lookback_period = lookback_period
        self.price_range_threshold = price_range_threshold  # %
        self.atr_volatility_threshold = atr_volatility_threshold  # %
        self.min_sideways_duration = min_sideways_duration
    
    def calculate_indicators(self, data):
        """Tính các chỉ báo cần thiết"""
        # Tạo bản sao của dữ liệu để tránh warning
        df = data.copy()
        
        # Tính ATR
        high_low = df['High'] - df['Low']
        high_close = abs(df['High'] - df['Close'].shift())
        low_close = abs(df['Low'] - df['Close'].shift())
        
        # Đặt tên cho các Series
        high_low.name = 'high_low'
        high_close.name = 'high_close'
        low_close.name = 'low_close'
        
        # Tạo DataFrame mới với các cột đã đặt tên
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        
        # Tính true range và ATR
        true_range = ranges.max(axis=1)
        df['atr'] = true_range.rolling(self.atr_period).mean()
        
        # Kiểm tra và điều chỉnh cấu trúc DataFrame nếu cần thiết
        try:
            # Xử lý nếu DataFrame là MultiIndex
            if isinstance(df.columns, pd.MultiIndex):
                logger.info("Phát hiện MultiIndex DataFrame, đang chuyển đổi...")
                df.columns = [col[0] if col[0] != "" else col[1] for col in df.columns]
                logger.info(f"Cột sau khi chuyển đổi: {df.columns.tolist()}")
        except Exception as e:
            logger.warning(f"Lỗi khi xử lý cấu trúc DataFrame: {e}")
            
        # Tính biến động ATR so với giá
        df['atr_volatility'] = 0.0  # Khởi tạo với giá trị mặc định
        
        # Sử dụng phương pháp đơn giản hơn
        try:
            # Chỉ chọn các dòng có dữ liệu hợp lệ
            valid_rows = np.isfinite(df['atr']) & np.isfinite(df['Close']) & (df['Close'] > 0)
            # Tính toán trực tiếp cho các dòng hợp lệ
            df.loc[valid_rows, 'atr_volatility'] = df.loc[valid_rows, 'atr'].astype(float) / df.loc[valid_rows, 'Close'].astype(float) * 100
            logger.info(f"Đã tính ATR volatility cho {valid_rows.sum()} dòng dữ liệu")
        except Exception as e:
            logger.error(f"Lỗi khi tính ATR volatility: {e}")
            # Dùng vòng lặp nếu phương pháp vectorized không hoạt động
            for i in range(len(df)):
                try:
                    atr_val = df['atr'].iloc[i]
                    close_val = df['Close'].iloc[i]
                    
                    # Kiểm tra giá trị hợp lệ (chuyển đổi sang số trước khi kiểm tra)
                    if (isinstance(atr_val, (int, float)) and 
                        isinstance(close_val, (int, float)) and 
                        pd.notnull(atr_val) and pd.notnull(close_val) and close_val > 0):
                        # Tính toán và gán
                        volatility = float(atr_val) / float(close_val) * 100
                        df.at[df.index[i], 'atr_volatility'] = volatility
                except Exception as e:
                    logger.warning(f"Lỗi khi tính ATR volatility cho dòng {i}: {e}")
        
        # Tính biên độ giá trong khoảng lookback_period
        df['price_high'] = df['High'].rolling(self.lookback_period).max()
        df['price_low'] = df['Low'].rolling(self.lookback_period).min()
        df['price_range_pct'] = (df['price_high'] - df['price_low']) / df['price_low'] * 100
        
        # Tính các dải Bollinger
        df['sma20'] = df['Close'].rolling(20).mean()
        df['stddev'] = df['Close'].rolling(20).std()
        df['bollinger_upper'] = df['sma20'] + (df['stddev'] * 2)
        df['bollinger_lower'] = df['sma20'] - (df['stddev'] * 2)
        df['bollinger_width'] = (df['bollinger_upper'] - df['bollinger_lower']) / df['sma20'] * 100
        
        return df
    
    def detect_sideways_market(self, data):
        """Phát hiện thị trường đi ngang với cải tiến sử dụng ADX và Bollinger Band Width"""
        # Tính các chỉ báo
        processed_data = self.calculate_indicators(data)
        
        # Tính ADX (Average Directional Index) - chỉ báo xu hướng
        # ADX thấp (<20) thường là dấu hiệu thị trường đi ngang
        try:
            # Tính +DI và -DI
            processed_data['plus_dm'] = np.where(
                (data['High'] - data['High'].shift(1)) > (data['Low'].shift(1) - data['Low']),
                np.maximum(data['High'] - data['High'].shift(1), 0),
                0
            )
            processed_data['minus_dm'] = np.where(
                (data['Low'].shift(1) - data['Low']) > (data['High'] - data['High'].shift(1)),
                np.maximum(data['Low'].shift(1) - data['Low'], 0),
                0
            )
            
            # Tính True Range (đã có trong ATR)
            processed_data['tr'] = processed_data['atr'] * self.atr_period  # Lấy lại từ ATR
            
            # Smoothed +DM, -DM và TR
            processed_data['plus_di'] = 100 * (processed_data['plus_dm'].rolling(14).sum() / processed_data['tr'].rolling(14).sum())
            processed_data['minus_di'] = 100 * (processed_data['minus_dm'].rolling(14).sum() / processed_data['tr'].rolling(14).sum())
            
            # Tính DX và ADX
            processed_data['dx'] = 100 * (abs(processed_data['plus_di'] - processed_data['minus_di']) / 
                                         (processed_data['plus_di'] + processed_data['minus_di']))
            processed_data['adx'] = processed_data['dx'].rolling(14).mean()
            
            logger.info("Đã tính chỉ báo ADX thành công")
        except Exception as e:
            logger.error(f"Lỗi khi tính ADX: {e}")
            # Tạo cột ADX giả nếu tính toán thất bại
            processed_data['adx'] = 50  # Giá trị mặc định

        # Tính toán trung bình của Bollinger Band Width (BB Width)
        processed_data['bb_width_avg'] = processed_data['bollinger_width'].rolling(30).mean()
        
        # Điều kiện thị trường đi ngang cải tiến:
        # 1. Biên độ giá nhỏ
        # 2. Biến động ATR thấp
        # 3. BB Width nhỏ hơn trung bình
        # 4. ADX thấp (nếu có)
        
        has_adx = 'adx' in processed_data.columns and processed_data['adx'].notnull().any()
        
        if has_adx:
            # Sử dụng cả ADX
            processed_data['is_sideways'] = (
                (processed_data['price_range_pct'] < self.price_range_threshold) & 
                (processed_data['atr_volatility'] < self.atr_volatility_threshold) &
                (processed_data['bollinger_width'] < processed_data['bb_width_avg']) &
                (processed_data['adx'] < 25)  # ADX < 25 thường là dấu hiệu của thị trường không có xu hướng
            )
            logger.info("Áp dụng phát hiện thị trường đi ngang với ADX")
        else:
            # Không sử dụng ADX
            processed_data['is_sideways'] = (
                (processed_data['price_range_pct'] < self.price_range_threshold) & 
                (processed_data['atr_volatility'] < self.atr_volatility_threshold) &
                (processed_data['bollinger_width'] < processed_data['bb_width_avg'])
            )
            logger.info("Áp dụng phát hiện thị trường đi ngang không có ADX")
        
        # Xác định các giai đoạn thị trường đi ngang kéo dài
        sideways_periods = []
        current_sideways = {'start': None, 'end': None, 'duration': 0}
        
        for i, (index, row) in enumerate(processed_data.iterrows()):
            try:
                is_sideways_value = row['is_sideways']
                
                # Kiểm tra xem giá trị có phải là boolean không
                if isinstance(is_sideways_value, bool):
                    is_sideways = is_sideways_value
                elif isinstance(is_sideways_value, (int, float)):
                    is_sideways = bool(is_sideways_value)
                else:
                    is_sideways = False
                    logger.warning(f"Giá trị is_sideways không hợp lệ ở vị trí {i}: {is_sideways_value}")
                
                if is_sideways:
                    if current_sideways['start'] is None:
                        current_sideways['start'] = i
                    current_sideways['end'] = i
                    current_sideways['duration'] += 1
                else:
                    if (current_sideways['start'] is not None and 
                        current_sideways['duration'] >= self.min_sideways_duration):
                        sideways_periods.append({
                            'start_idx': current_sideways['start'],
                            'end_idx': current_sideways['end'],
                            'start_date': processed_data.index[current_sideways['start']],
                            'end_date': processed_data.index[current_sideways['end']],
                            'duration': current_sideways['duration']
                        })
                    # Reset
                    current_sideways = {'start': None, 'end': None, 'duration': 0}
            except Exception as e:
                logger.error(f"Lỗi khi xử lý dòng {i}: {e}")
        
        # Kiểm tra sideways period cuối cùng
        if (current_sideways['start'] is not None and 
            current_sideways['duration'] >= self.min_sideways_duration):
            sideways_periods.append({
                'start_idx': current_sideways['start'],
                'end_idx': current_sideways['end'],
                'start_date': processed_data.index[current_sideways['start']],
                'end_date': processed_data.index[current_sideways['end']],
                'duration': current_sideways['duration']
            })
        
        logger.info(f"Đã phát hiện {len(sideways_periods)} giai đoạn thị trường đi ngang")
        return processed_data, sideways_periods
    
    def optimize_trading_params(self, data, sideways_periods):
        """Tối ưu hóa các tham số giao dịch dựa trên thị trường đi ngang"""
        optimized_params = {}
        
        for i, period in enumerate(sideways_periods):
            start_idx = period['start_idx']
            end_idx = period['end_idx']
            
            # Dữ liệu trong giai đoạn sideways
            period_data = data.iloc[start_idx:end_idx+1]
            
            # Tính các thông số tối ưu
            avg_price = period_data['Close'].mean()
            avg_atr = period_data['atr'].mean()
            price_range = period_data['price_range_pct'].mean()
            
            # Chiến lược chốt lời/cắt lỗ tối ưu cho thị trường đi ngang
            # 1. Khoảng cách stop loss/take profit nhỏ hơn
            # 2. ATR multiplier thấp hơn
            # 3. Tập trung vào giao dịch dựa trên các dải Bollinger
            
            sl_pct = min(1.5, avg_atr / avg_price * 100)  # Stop loss thấp hơn
            tp_pct = min(3.0, price_range * 0.7)  # Take profit thấp hơn, khoảng 70% biên độ giá
            
            optimized_params[f'sideways_period_{i+1}'] = {
                'start_date': period['start_date'],
                'end_date': period['end_date'],
                'duration': period['duration'],
                'avg_price': avg_price,
                'avg_atr': avg_atr,
                'price_range_pct': price_range,
                'optimized_sl_pct': sl_pct,
                'optimized_tp_pct': tp_pct,
                'atr_multiplier': 1.0,  # Thấp hơn so với thông thường
                'bollinger_signal': True  # Sử dụng tín hiệu Bollinger
            }
        
        return optimized_params
    
    def generate_sideways_signals(self, data, sideways_periods):
        """Tạo tín hiệu giao dịch cho thị trường đi ngang với cải tiến"""
        signals = []
        
        for period in sideways_periods:
            try:
                start_idx = period['start_idx']
                end_idx = period['end_idx']
                
                # Dữ liệu trong giai đoạn sideways
                period_data = data.iloc[start_idx:end_idx+1].copy()
                
                # 1. Tín hiệu Bollinger Bands
                # Tín hiệu khi giá chạm cận dưới Bollinger và RSI thấp (nếu có)
                period_data['lower_band_signal'] = (
                    (period_data['Close'] <= period_data['bollinger_lower']) & 
                    (period_data['Close'].shift(1) > period_data['bollinger_lower'].shift(1))
                )
                
                # Thêm điều kiện RSI nếu có
                if 'rsi' in period_data.columns:
                    period_data['lower_band_signal'] = (
                        period_data['lower_band_signal'] & 
                        (period_data['rsi'] < 40)  # RSI thấp - vùng quá bán
                    )
                
                # Tín hiệu khi giá chạm cận trên Bollinger và RSI cao (nếu có)
                period_data['upper_band_signal'] = (
                    (period_data['Close'] >= period_data['bollinger_upper']) & 
                    (period_data['Close'].shift(1) < period_data['bollinger_upper'].shift(1))
                )
                
                # Thêm điều kiện RSI nếu có
                if 'rsi' in period_data.columns:
                    period_data['upper_band_signal'] = (
                        period_data['upper_band_signal'] & 
                        (period_data['rsi'] > 60)  # RSI cao - vùng quá mua
                    )
                
                # 2. Tín hiệu đảo chiều trong vùng giá
                # Phát hiện đảo chiều giá trong khoảng hẹp
                try:
                    period_data['local_min'] = period_data['Close'].rolling(5, center=True).min() == period_data['Close']
                    period_data['local_max'] = period_data['Close'].rolling(5, center=True).max() == period_data['Close']
                    
                    # Lọc các điểm cực đại/cực tiểu cục bộ
                    period_data['reversal_bottom'] = (
                        period_data['local_min'] & 
                        (period_data['Close'] < period_data['sma20']) &
                        (period_data['Close'].pct_change(3) < -0.01)  # Giảm trước đó
                    )
                    
                    period_data['reversal_top'] = (
                        period_data['local_max'] & 
                        (period_data['Close'] > period_data['sma20']) &
                        (period_data['Close'].pct_change(3) > 0.01)  # Tăng trước đó
                    )
                except Exception as e:
                    logger.error(f"Lỗi khi tính điểm đảo chiều: {e}")
                    period_data['reversal_bottom'] = False
                    period_data['reversal_top'] = False
                
                # Xác định tỷ lệ SL/TP dựa trên ATR
                try:
                    avg_atr = period_data['atr'].mean()
                    avg_price = period_data['Close'].mean()
                    atr_pct = avg_atr / avg_price * 100
                    
                    # Phần trăm stop loss và take profit
                    sl_pct = min(1.5, atr_pct)  # Tối đa 1.5%
                    tp_pct = min(3.0, atr_pct * 2)  # Tối đa 3%, gấp đôi SL
                except Exception as e:
                    logger.error(f"Lỗi khi tính SL/TP: {e}")
                    sl_pct = 1.0
                    tp_pct = 2.0
                
                # Tìm tín hiệu
                for i, (date, row) in enumerate(period_data.iterrows()):
                    # Bỏ qua ngày đầu và cuối để tránh lỗi
                    if i < 2 or i >= len(period_data) - 2:
                        continue
                    
                    # Tín hiệu từ Bollinger Band - LONG
                    if row['lower_band_signal']:
                        entry_price = row['Close']
                        sl_price = entry_price * (1 - sl_pct/100)
                        tp_price = entry_price * (1 + tp_pct/100)
                        
                        signals.append({
                            'date': date,
                            'type': 'LONG',
                            'entry_price': entry_price,
                            'stop_loss': sl_price,
                            'take_profit': tp_price,
                            'signal_source': 'bollinger_lower',
                            'sideways_period': True
                        })
                    
                    # Tín hiệu từ Bollinger Band - SHORT
                    if row['upper_band_signal']:
                        entry_price = row['Close']
                        sl_price = entry_price * (1 + sl_pct/100)
                        tp_price = entry_price * (1 - tp_pct/100)
                        
                        signals.append({
                            'date': date,
                            'type': 'SHORT',
                            'entry_price': entry_price,
                            'stop_loss': sl_price,
                            'take_profit': tp_price,
                            'signal_source': 'bollinger_upper',
                            'sideways_period': True
                        })
                    
                    # Tín hiệu từ điểm đảo chiều - LONG
                    if 'reversal_bottom' in row and row['reversal_bottom']:
                        entry_price = row['Close']
                        sl_price = entry_price * (1 - sl_pct/100)
                        tp_price = entry_price * (1 + tp_pct/100)
                        
                        signals.append({
                            'date': date,
                            'type': 'LONG',
                            'entry_price': entry_price,
                            'stop_loss': sl_price,
                            'take_profit': tp_price,
                            'signal_source': 'reversal_bottom',
                            'sideways_period': True
                        })
                    
                    # Tín hiệu từ điểm đảo chiều - SHORT
                    if 'reversal_top' in row and row['reversal_top']:
                        entry_price = row['Close']
                        sl_price = entry_price * (1 + sl_pct/100)
                        tp_price = entry_price * (1 - tp_pct/100)
                        
                        signals.append({
                            'date': date,
                            'type': 'SHORT',
                            'entry_price': entry_price,
                            'stop_loss': sl_price,
                            'take_profit': tp_price,
                            'signal_source': 'reversal_top',
                            'sideways_period': True
                        })
            except Exception as e:
                logger.error(f"Lỗi khi xử lý giai đoạn sideways: {e}")
                continue
        
        # Lọc các tín hiệu quá gần nhau
        if signals:
            filtered_signals = []
            signals.sort(key=lambda x: x['date'])
            
            last_date = None
            last_type = None
            
            for signal in signals:
                current_date = signal['date']
                current_type = signal['type']
                
                # Bỏ qua tín hiệu nếu ngày giống nhau và loại giống nhau
                if last_date is not None and last_type == current_type:
                    if isinstance(current_date, pd.Timestamp) and isinstance(last_date, pd.Timestamp):
                        if (current_date - last_date).days < 2:
                            continue
                
                filtered_signals.append(signal)
                last_date = current_date
                last_type = current_type
            
            logger.info(f"Đã tạo {len(signals)} tín hiệu thị trường đi ngang, sau khi lọc còn {len(filtered_signals)}")
            return filtered_signals
        
        return signals
    
    def plot_sideways_periods(self, data, sideways_periods, filename=None):
        """Vẽ biểu đồ các giai đoạn thị trường đi ngang"""
        plt.figure(figsize=(12, 8))
        
        # Vẽ giá
        plt.subplot(3, 1, 1)
        plt.plot(data.index, data['Close'], label='Giá đóng cửa')
        plt.plot(data.index, data['bollinger_upper'], 'r--', label='Bollinger Upper')
        plt.plot(data.index, data['bollinger_lower'], 'g--', label='Bollinger Lower')
        
        # Đánh dấu các giai đoạn sideways
        for period in sideways_periods:
            plt.axvspan(period['start_date'], period['end_date'], alpha=0.2, color='yellow')
        
        plt.title('Giá và Giai đoạn Thị trường Đi ngang')
        plt.legend()
        
        # Vẽ ATR Volatility
        plt.subplot(3, 1, 2)
        plt.plot(data.index, data['atr_volatility'], label='ATR Volatility (%)')
        plt.axhline(y=self.atr_volatility_threshold, color='r', linestyle='--', label=f'Ngưỡng ({self.atr_volatility_threshold}%)')
        
        for period in sideways_periods:
            plt.axvspan(period['start_date'], period['end_date'], alpha=0.2, color='yellow')
        
        plt.title('Biến động ATR (%)')
        plt.legend()
        
        # Vẽ Price Range
        plt.subplot(3, 1, 3)
        plt.plot(data.index, data['price_range_pct'], label='Biên độ giá (%)')
        plt.axhline(y=self.price_range_threshold, color='r', linestyle='--', label=f'Ngưỡng ({self.price_range_threshold}%)')
        
        for period in sideways_periods:
            plt.axvspan(period['start_date'], period['end_date'], alpha=0.2, color='yellow')
        
        plt.title('Biên độ giá (%)')
        plt.legend()
        
        plt.tight_layout()
        
        if filename:
            plt.savefig(filename)
            logger.info(f"Đã lưu biểu đồ vào {filename}")
        
        plt.close()
    
    def analyze_symbol(self, symbol, period='6mo', interval='1d', plot=True):
        """Phân tích một cặp tiền tệ"""
        logger.info(f"Đang phân tích {symbol}...")
        
        try:
            # Tải dữ liệu
            data = yf.download(symbol, period=period, interval=interval)
            logger.info(f"Đã tải {len(data)} mẫu dữ liệu cho {symbol}")
            
            if len(data) < self.lookback_period + 10:
                logger.warning(f"Không đủ dữ liệu cho {symbol}, cần ít nhất {self.lookback_period + 10} mẫu")
                return None, None, None
            
            # Phát hiện thị trường đi ngang
            processed_data, sideways_periods = self.detect_sideways_market(data)
            logger.info(f"Đã phát hiện {len(sideways_periods)} giai đoạn thị trường đi ngang cho {symbol}")
            
            for i, period in enumerate(sideways_periods):
                logger.info(f"Giai đoạn {i+1}: {period['start_date']} đến {period['end_date']} ({period['duration']} phiên)")
            
            # Tối ưu hóa tham số giao dịch
            optimized_params = self.optimize_trading_params(processed_data, sideways_periods)
            
            # Tạo tín hiệu giao dịch
            signals = self.generate_sideways_signals(processed_data, sideways_periods)
            logger.info(f"Đã tạo {len(signals)} tín hiệu giao dịch cho {symbol}")
            
            # Vẽ biểu đồ nếu được yêu cầu
            if plot and len(sideways_periods) > 0:
                filename = f"sideways_analysis_{symbol.replace('-', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                self.plot_sideways_periods(processed_data, sideways_periods, filename=filename)
            
            return processed_data, sideways_periods, optimized_params
        
        except Exception as e:
            logger.error(f"Lỗi khi phân tích {symbol}: {e}")
            return None, None, None
    
def main():
    """Hàm chính"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Công cụ phát hiện thị trường đi ngang')
    parser.add_argument('--symbols', nargs='+', default=['BTC-USD', 'ETH-USD', 'SOL-USD'],
                        help='Danh sách các cặp tiền tệ cần phân tích')
    parser.add_argument('--period', default='6mo', help='Khoảng thời gian dữ liệu (1mo, 3mo, 6mo, 1y...)')
    parser.add_argument('--interval', default='1d', help='Khung thời gian (1d, 4h, 1h...)')
    parser.add_argument('--no-plot', action='store_true', help='Không vẽ biểu đồ')
    
    args = parser.parse_args()
    
    detector = SidewaysMarketDetector()
    
    for symbol in args.symbols:
        detector.analyze_symbol(symbol, period=args.period, interval=args.interval, plot=not args.no_plot)

if __name__ == "__main__":
    main()