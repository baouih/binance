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
        
        # Tính biến động ATR so với giá (cách đơn giản nhất)
        # Xử lý giá trị NaN và 0 trong Close
        tmp_close = df['Close'].replace(0, np.nan)
        # Tính toán trực tiếp, để pandas tự xử lý các giá trị NaN
        df['atr_volatility'] = (df['atr'] / tmp_close * 100)
        
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
        """Phát hiện thị trường đi ngang"""
        # Tính các chỉ báo
        processed_data = self.calculate_indicators(data)
        
        # Điều kiện thị trường đi ngang
        processed_data['is_sideways'] = (
            (processed_data['price_range_pct'] < self.price_range_threshold) & 
            (processed_data['atr_volatility'] < self.atr_volatility_threshold) &
            (processed_data['bollinger_width'] < processed_data['bollinger_width'].rolling(30).mean())
        )
        
        # Xác định các giai đoạn thị trường đi ngang kéo dài
        sideways_periods = []
        current_sideways = {'start': None, 'end': None, 'duration': 0}
        
        for i, (index, row) in enumerate(processed_data.iterrows()):
            if row['is_sideways']:
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
        """Tạo tín hiệu giao dịch cho thị trường đi ngang"""
        signals = []
        
        for period in sideways_periods:
            start_idx = period['start_idx']
            end_idx = period['end_idx']
            
            # Dữ liệu trong giai đoạn sideways
            period_data = data.iloc[start_idx:end_idx+1].copy()
            
            # Tín hiệu khi giá chạm cận dưới Bollinger
            period_data['lower_band_signal'] = (
                (period_data['Close'] <= period_data['bollinger_lower']) & 
                (period_data['Close'].shift(1) > period_data['bollinger_lower'].shift(1))
            )
            
            # Tín hiệu khi giá chạm cận trên Bollinger
            period_data['upper_band_signal'] = (
                (period_data['Close'] >= period_data['bollinger_upper']) & 
                (period_data['Close'].shift(1) < period_data['bollinger_upper'].shift(1))
            )
            
            # Tìm tín hiệu
            for i, (date, row) in enumerate(period_data.iterrows()):
                if row['lower_band_signal']:
                    # Tín hiệu Long khi giá chạm cận dưới Bollinger
                    entry_price = row['Close']
                    sl_price = entry_price * (1 - 0.01)  # 1% stop loss
                    tp_price = entry_price * (1 + 0.02)  # 2% take profit
                    
                    signals.append({
                        'date': date,
                        'type': 'LONG',
                        'entry_price': entry_price,
                        'stop_loss': sl_price,
                        'take_profit': tp_price,
                        'signal_source': 'bollinger_lower',
                        'sideways_period': True
                    })
                
                if row['upper_band_signal']:
                    # Tín hiệu Short khi giá chạm cận trên Bollinger
                    entry_price = row['Close']
                    sl_price = entry_price * (1 + 0.01)  # 1% stop loss
                    tp_price = entry_price * (1 - 0.02)  # 2% take profit
                    
                    signals.append({
                        'date': date,
                        'type': 'SHORT',
                        'entry_price': entry_price,
                        'stop_loss': sl_price,
                        'take_profit': tp_price,
                        'signal_source': 'bollinger_upper',
                        'sideways_period': True
                    })
        
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