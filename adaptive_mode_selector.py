#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module thích ứng tự động lựa chọn giữa chế độ hedge mode và single direction
dựa trên điều kiện thị trường hiện tại và backtest
"""

import os
import json
import time
import logging
import datetime
import numpy as np
import pandas as pd
from collections import defaultdict

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('adaptive_controller.log')
    ]
)

logger = logging.getLogger('adaptive_mode')

class AdaptiveModeSelector:
    """
    Lớp thích ứng tự động quyết định chế độ giao dịch dựa trên phân tích thị trường
    """
    
    def __init__(self, api_connector, config_path='adaptive_mode_config.json'):
        """
        Khởi tạo bộ chọn chế độ thích ứng
        
        Args:
            api_connector: Kết nối API để lấy dữ liệu thị trường
            config_path (str): Đường dẫn file cấu hình
        """
        self.api = api_connector
        self.config_path = config_path
        self.load_config()
        
        # Các phiên giao dịch tối ưu dựa trên backtest
        self.optimal_sessions = {
            'London Open': {
                'start_time': '15:00',
                'end_time': '17:00',
                'optimal_mode': 'single',
                'optimal_direction': 'SHORT',
                'win_rate': 95.0
            },
            'New York Open': {
                'start_time': '20:30',
                'end_time': '22:30',
                'optimal_mode': 'single',
                'optimal_direction': 'SHORT',
                'win_rate': 90.0
            },
            'Major News Events': {
                'start_time': '21:30',
                'end_time': '22:00',
                'optimal_mode': 'single',
                'optimal_direction': 'SHORT',
                'win_rate': 80.0
            },
            'Daily Candle Close': {
                'start_time': '06:30',
                'end_time': '07:30',
                'optimal_mode': 'single',
                'optimal_direction': 'LONG',
                'win_rate': 75.0
            },
            'London/NY Close': {
                'start_time': '03:00',
                'end_time': '05:00',
                'optimal_mode': 'hedge',
                'optimal_direction': 'BOTH',
                'win_rate': 70.0
            }
        }
        
        # Theo dõi hiệu suất thị trường
        self.market_regimes = {}
        self.recent_signals = []
        self.performance_metrics = defaultdict(dict)
        
        # Chỉ số thống kê
        self.stats = {
            'hedge_win_count': 0,
            'hedge_loss_count': 0,
            'single_win_count': 0,
            'single_loss_count': 0,
            'adaptive_pnl': 0,
            'hedge_only_pnl': 0,
            'single_only_pnl': 0
        }
        
        # Phân tích thị trường
        self.last_analysis_time = None
        self.current_market_regime = None
        self.current_volatility = None
        self.current_trend_strength = None
        
        # Đọc dữ liệu lịch sử nếu có
        self.load_performance_history()
    
    def load_config(self):
        """
        Tải cấu hình từ file JSON
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
            else:
                # Tạo cấu hình mặc định
                self.config = {
                    'volatility_threshold': 2.5,  # Ngưỡng biến động để chuyển sang hedge mode
                    'trend_strength_threshold': 35.0,  # Ngưỡng mạnh của xu hướng để chuyển sang single direction
                    'lookback_period': 24,  # Số giờ nhìn lại để phân tích thị trường
                    'analysis_interval': 60,  # Tần suất phân tích thị trường (phút)
                    'hedge_mode_sl_percentage': 7.0,  # % stoploss cho hedge mode
                    'hedge_mode_tp_percentage': 21.0,  # % takeprofit cho hedge mode
                    'single_mode_sl_percentage': 5.0,  # % stoploss cho single direction
                    'single_mode_tp_percentage': 15.0,  # % takeprofit cho single direction
                    'risk_per_trade': 2.0,  # % risk trên mỗi lệnh
                    'preferred_leverage': 15,  # Đòn bẩy khuyến nghị
                    'max_hedge_positions': 5,  # Số lượng vị thế hedge tối đa
                    'max_single_positions': 8,  # Số lượng vị thế single tối đa
                    'optimize_based_on_time': True,  # Tối ưu dựa trên thời gian phiên
                    'enable_auto_regime_detection': True,  # Tự động phát hiện chế độ thị trường
                    'pairs_whitelist': [
                        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT',
                        'MATICUSDT', 'LINKUSDT', 'ATOMUSDT', 'AVAXUSDT', 'ADAUSDT'
                    ]
                }
                
                # Lưu cấu hình
                with open(self.config_path, 'w') as f:
                    json.dump(self.config, f, indent=2)
                logger.info(f"Đã tạo cấu hình mặc định và lưu vào {self.config_path}")
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {e}")
            raise
    
    def save_config(self):
        """
        Lưu cấu hình vào file
        """
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Đã lưu cấu hình vào {self.config_path}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {e}")
    
    def load_performance_history(self):
        """
        Tải lịch sử hiệu suất để cải thiện quyết định
        """
        try:
            history_path = 'data/regime_performance/mode_performance_history.json'
            if os.path.exists(history_path):
                with open(history_path, 'r') as f:
                    performance_history = json.load(f)
                
                self.stats.update(performance_history.get('stats', {}))
                self.performance_metrics.update(performance_history.get('metrics', {}))
                
                logger.info(f"Đã tải lịch sử hiệu suất: {len(self.performance_metrics)} chế độ thị trường")
            else:
                logger.info("Không tìm thấy lịch sử hiệu suất, sẽ bắt đầu từ đầu")
        except Exception as e:
            logger.error(f"Lỗi khi tải lịch sử hiệu suất: {e}")
    
    def save_performance_history(self):
        """
        Lưu lịch sử hiệu suất để phân tích sau này
        """
        try:
            os.makedirs('data/regime_performance', exist_ok=True)
            history_path = 'data/regime_performance/mode_performance_history.json'
            
            performance_history = {
                'stats': self.stats,
                'metrics': dict(self.performance_metrics),
                'last_updated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(history_path, 'w') as f:
                json.dump(performance_history, f, indent=2, default=str)
            
            logger.info(f"Đã lưu lịch sử hiệu suất vào {history_path}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu lịch sử hiệu suất: {e}")
    
    def is_analysis_needed(self):
        """
        Kiểm tra xem có cần phân tích lại thị trường không
        
        Returns:
            bool: True nếu cần phân tích lại
        """
        if self.last_analysis_time is None:
            return True
        
        now = datetime.datetime.now()
        time_diff = (now - self.last_analysis_time).total_seconds() / 60
        return time_diff >= self.config['analysis_interval']
    
    def analyze_market_conditions(self, symbol='BTCUSDT'):
        """
        Phân tích điều kiện thị trường hiện tại để xác định chế độ tối ưu
        
        Args:
            symbol (str): Cặp tiền để phân tích (mặc định là BTCUSDT)
            
        Returns:
            dict: Kết quả phân tích
        """
        try:
            # Lấy dữ liệu thị trường
            lookback_hours = self.config['lookback_period']
            end_time = int(time.time() * 1000)
            start_time = end_time - (lookback_hours * 60 * 60 * 1000)
            
            # Lấy dữ liệu 1h và 15m để phân tích
            klines_1h = self.api.get_historical_klines(symbol, '1h', start_time, end_time)
            klines_15m = self.api.get_historical_klines(symbol, '15m', start_time, end_time)
            
            if not klines_1h or not klines_15m:
                logger.warning(f"Không lấy được dữ liệu cho {symbol}, sử dụng phân tích trước đó")
                return None
            
            # Chuyển đổi thành DataFrame
            df_1h = pd.DataFrame(klines_1h, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 
                                                     'quote_volume', 'count', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore'])
            df_15m = pd.DataFrame(klines_15m, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 
                                                       'quote_volume', 'count', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore'])
            
            # Chuyển đổi dữ liệu
            for df in [df_1h, df_15m]:
                for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume', 'taker_buy_volume', 'taker_buy_quote_volume']:
                    df[col] = df[col].astype(float)
                df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            
            # 1. Tính toán biến động
            df_1h['volatility'] = (df_1h['high'] - df_1h['low']) / df_1h['low'] * 100  # Biến động theo %
            current_volatility = df_1h['volatility'].mean()
            
            # 2. Tính toán sức mạnh xu hướng
            df_1h['returns'] = df_1h['close'].pct_change() * 100
            df_1h['direction'] = np.where(df_1h['returns'] > 0, 1, -1)
            df_1h['streak'] = df_1h['direction'].groupby((df_1h['direction'] != df_1h['direction'].shift(1)).cumsum()).cumcount() + 1
            
            # Độ mạnh của xu hướng = chiều dài trung bình của các chuỗi * độ lớn trung bình của thay đổi
            recent_df = df_1h.tail(6)  # 6 giờ gần nhất
            trend_strength = recent_df['streak'].mean() * recent_df['returns'].abs().mean()
            
            # 3. Phát hiện chế độ thị trường
            # Tính toán ATR
            df_1h['atr'] = self._calculate_atr(df_1h, 14)
            
            # Biến động cao + xu hướng yếu = Sideway với biến động
            if current_volatility > self.config['volatility_threshold'] and trend_strength < self.config['trend_strength_threshold']:
                market_regime = 'volatile_sideway'
                recommended_mode = 'hedge'
            # Biến động thấp + xu hướng yếu = Sideway ổn định
            elif current_volatility <= self.config['volatility_threshold'] and trend_strength < self.config['trend_strength_threshold']:
                market_regime = 'stable_sideway'
                recommended_mode = 'single'
                
                # Phân tích thêm để xác định hướng entry tối ưu
                if recent_df['close'].iloc[-1] > recent_df['close'].iloc[-2]:
                    recommended_direction = 'LONG'
                else:
                    recommended_direction = 'SHORT'
            # Biến động cao + xu hướng mạnh = Xu hướng mạnh
            elif current_volatility > self.config['volatility_threshold'] and trend_strength >= self.config['trend_strength_threshold']:
                market_regime = 'trending_volatile'
                recommended_mode = 'single'
                
                # Xác định hướng xu hướng
                if recent_df['returns'].mean() > 0:
                    recommended_direction = 'LONG'
                else:
                    recommended_direction = 'SHORT'
            # Biến động thấp + xu hướng mạnh = Xu hướng ổn định
            else:
                market_regime = 'trending_stable'
                recommended_mode = 'single'
                
                # Xác định hướng xu hướng
                if recent_df['returns'].mean() > 0:
                    recommended_direction = 'LONG'
                else:
                    recommended_direction = 'SHORT'
            
            # 4. Lấy thời gian hiện tại để kiểm tra phiên giao dịch tối ưu
            now = datetime.datetime.now()
            current_time_str = now.strftime('%H:%M')
            
            optimal_session = None
            for session_name, session_info in self.optimal_sessions.items():
                start_time = session_info['start_time']
                end_time = session_info['end_time']
                
                # So sánh thời gian hiện tại với thời gian phiên
                if self._is_time_in_range(current_time_str, start_time, end_time):
                    optimal_session = session_name
                    session_recommended_mode = session_info['optimal_mode']
                    session_recommended_direction = session_info['optimal_direction']
                    break
            
            # 5. Kết hợp các phân tích
            if self.config['optimize_based_on_time'] and optimal_session:
                # Ưu tiên dựa trên phiên giao dịch tối ưu
                final_recommended_mode = session_recommended_mode
                final_recommended_direction = session_recommended_direction
                decision_basis = f"time_based:{optimal_session}"
            else:
                # Dựa trên phân tích thị trường
                final_recommended_mode = recommended_mode
                if recommended_mode == 'single':
                    final_recommended_direction = recommended_direction
                else:
                    final_recommended_direction = 'BOTH'
                decision_basis = f"market_regime:{market_regime}"
            
            # Cập nhật thời gian phân tích
            self.last_analysis_time = datetime.datetime.now()
            self.current_market_regime = market_regime
            self.current_volatility = current_volatility
            self.current_trend_strength = trend_strength
            
            # Kết quả phân tích
            analysis_result = {
                'timestamp': self.last_analysis_time.strftime('%Y-%m-%d %H:%M:%S'),
                'symbol': symbol,
                'market_regime': market_regime,
                'volatility': current_volatility,
                'trend_strength': trend_strength,
                'recommended_mode': final_recommended_mode,
                'recommended_direction': final_recommended_direction,
                'current_session': optimal_session,
                'decision_basis': decision_basis,
                'lookback_hours': lookback_hours
            }
            
            # Lưu phân tích để tham khảo sau
            self.recent_signals.append(analysis_result)
            if len(self.recent_signals) > 50:
                self.recent_signals.pop(0)
            
            logger.info(f"Phân tích thị trường: {market_regime}, biến động: {current_volatility:.2f}%, "
                       f"sức mạnh xu hướng: {trend_strength:.2f}, "
                       f"khuyến nghị: {final_recommended_mode.upper()} mode, {final_recommended_direction}")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích thị trường: {e}")
            return None
    
    def _calculate_atr(self, df, period=14):
        """
        Tính Average True Range (ATR)
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLC
            period (int): Period cho ATR
            
        Returns:
            pd.Series: ATR values
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Tính True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        
        # Tính ATR
        atr = tr.rolling(period).mean()
        return atr
    
    def _is_time_in_range(self, current_time, start_time, end_time):
        """
        Kiểm tra xem thời gian hiện tại có nằm trong khoảng start-end không
        
        Args:
            current_time (str): Thời gian hiện tại format 'HH:MM'
            start_time (str): Thời gian bắt đầu format 'HH:MM'
            end_time (str): Thời gian kết thúc format 'HH:MM'
            
        Returns:
            bool: True nếu thời gian nằm trong khoảng
        """
        # Chuyển đổi string thành giờ phút
        def parse_time(time_str):
            hour, minute = map(int, time_str.split(':'))
            return hour * 60 + minute
        
        current_minutes = parse_time(current_time)
        start_minutes = parse_time(start_time)
        end_minutes = parse_time(end_time)
        
        # So sánh
        if start_minutes <= end_minutes:
            # Trường hợp thông thường: start < end
            return start_minutes <= current_minutes <= end_minutes
        else:
            # Trường hợp qua ngày: start > end
            return current_minutes >= start_minutes or current_minutes <= end_minutes
    
    def get_trading_parameters(self, symbol, analysis=None):
        """
        Lấy tham số giao dịch dựa trên chế độ khuyến nghị
        
        Args:
            symbol (str): Cặp tiền giao dịch
            analysis (dict, optional): Kết quả phân tích thị trường
            
        Returns:
            dict: Tham số giao dịch
        """
        if analysis is None:
            analysis = self.analyze_market_conditions(symbol)
            if analysis is None:
                # Nếu không phân tích được, sử dụng chế độ mặc định
                logger.warning(f"Không phân tích được thị trường cho {symbol}, sử dụng chế độ mặc định")
                return {
                    'mode': 'single',
                    'direction': 'NONE',  # Sẽ được xác định bởi chiến lược
                    'sl_percentage': self.config['single_mode_sl_percentage'],
                    'tp_percentage': self.config['single_mode_tp_percentage'],
                    'risk_per_trade': self.config['risk_per_trade'],
                    'leverage': self.config['preferred_leverage'],
                    'max_positions': self.config['max_single_positions']
                }
        
        recommended_mode = analysis['recommended_mode']
        recommended_direction = analysis['recommended_direction']
        
        if recommended_mode == 'hedge':
            return {
                'mode': 'hedge',
                'direction': recommended_direction,  # 'BOTH' cho hedge mode
                'sl_percentage': self.config['hedge_mode_sl_percentage'],
                'tp_percentage': self.config['hedge_mode_tp_percentage'],
                'risk_per_trade': self.config['risk_per_trade'],
                'leverage': self.config['preferred_leverage'],
                'max_positions': self.config['max_hedge_positions']
            }
        else:  # single mode
            return {
                'mode': 'single',
                'direction': recommended_direction,
                'sl_percentage': self.config['single_mode_sl_percentage'],
                'tp_percentage': self.config['single_mode_tp_percentage'],
                'risk_per_trade': self.config['risk_per_trade'],
                'leverage': self.config['preferred_leverage'],
                'max_positions': self.config['max_single_positions']
            }
    
    def update_performance(self, mode, direction, symbol, entry_price, exit_price, position_size):
        """
        Cập nhật hiệu suất của chế độ giao dịch
        
        Args:
            mode (str): Chế độ giao dịch ('hedge' hoặc 'single')
            direction (str): Hướng giao dịch ('LONG', 'SHORT', 'BOTH')
            symbol (str): Cặp tiền
            entry_price (float): Giá vào lệnh
            exit_price (float): Giá thoát lệnh
            position_size (float): Kích thước vị thế
            
        Returns:
            None
        """
        try:
            # Tính P/L
            if direction == 'LONG':
                pnl = (exit_price - entry_price) / entry_price * position_size
            elif direction == 'SHORT':
                pnl = (entry_price - exit_price) / entry_price * position_size
            else:  # BOTH (hedge mode)
                # Giả định cả LONG và SHORT đều có cùng position size
                long_pnl = (exit_price - entry_price) / entry_price * position_size
                short_pnl = (entry_price - exit_price) / entry_price * position_size
                pnl = long_pnl + short_pnl
            
            # Cập nhật thống kê
            if mode == 'hedge':
                if pnl > 0:
                    self.stats['hedge_win_count'] += 1
                else:
                    self.stats['hedge_loss_count'] += 1
                self.stats['adaptive_pnl'] += pnl
                self.stats['hedge_only_pnl'] += pnl
            else:  # single
                if pnl > 0:
                    self.stats['single_win_count'] += 1
                else:
                    self.stats['single_loss_count'] += 1
                self.stats['adaptive_pnl'] += pnl
                self.stats['single_only_pnl'] += pnl
            
            # Cập nhật hiệu suất theo chế độ thị trường
            if self.current_market_regime:
                regime = self.current_market_regime
                if regime not in self.performance_metrics:
                    self.performance_metrics[regime] = {
                        'hedge_win_count': 0,
                        'hedge_loss_count': 0,
                        'single_win_count': 0,
                        'single_loss_count': 0,
                        'hedge_pnl': 0,
                        'single_pnl': 0,
                        'trades': []
                    }
                
                if mode == 'hedge':
                    if pnl > 0:
                        self.performance_metrics[regime]['hedge_win_count'] += 1
                    else:
                        self.performance_metrics[regime]['hedge_loss_count'] += 1
                    self.performance_metrics[regime]['hedge_pnl'] += pnl
                else:  # single
                    if pnl > 0:
                        self.performance_metrics[regime]['single_win_count'] += 1
                    else:
                        self.performance_metrics[regime]['single_loss_count'] += 1
                    self.performance_metrics[regime]['single_pnl'] += pnl
                
                # Lưu thông tin giao dịch
                trade_info = {
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'symbol': symbol,
                    'mode': mode,
                    'direction': direction,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'position_size': position_size,
                    'pnl': pnl,
                    'market_regime': regime
                }
                self.performance_metrics[regime]['trades'].append(trade_info)
            
            # Giới hạn số lượng giao dịch lưu trữ
            for regime in self.performance_metrics:
                if len(self.performance_metrics[regime]['trades']) > 100:
                    self.performance_metrics[regime]['trades'] = self.performance_metrics[regime]['trades'][-100:]
            
            # Lưu hiệu suất
            self.save_performance_history()
            
            logger.info(f"Cập nhật hiệu suất: {mode} mode, {direction}, {symbol}, PnL: {pnl:.2f} USDT")
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật hiệu suất: {e}")
    
    def optimize_parameters(self):
        """
        Tối ưu hóa các tham số dựa trên hiệu suất trước đó
        
        Returns:
            dict: Tham số đã được tối ưu hóa
        """
        try:
            # Nếu không đủ dữ liệu, không tối ưu
            if len(self.performance_metrics) == 0:
                logger.info("Chưa đủ dữ liệu để tối ưu hóa tham số")
                return self.config
            
            # Phân tích hiệu suất theo chế độ thị trường
            optimized_params = self.config.copy()
            
            for regime, metrics in self.performance_metrics.items():
                hedge_win_rate = 0
                single_win_rate = 0
                
                # Tính tỷ lệ thắng
                if metrics['hedge_win_count'] + metrics['hedge_loss_count'] > 0:
                    hedge_win_rate = metrics['hedge_win_count'] / (metrics['hedge_win_count'] + metrics['hedge_loss_count'])
                
                if metrics['single_win_count'] + metrics['single_loss_count'] > 0:
                    single_win_rate = metrics['single_win_count'] / (metrics['single_win_count'] + metrics['single_loss_count'])
                
                # Tối ưu các tham số dựa trên hiệu suất
                if regime == 'volatile_sideway':
                    # Thị trường sideway biến động
                    if hedge_win_rate > single_win_rate:
                        # Hedge mode hoạt động tốt hơn
                        logger.info(f"Tối ưu tham số cho {regime}: ưu tiên hedge mode")
                        optimized_params['volatility_threshold'] = max(1.8, optimized_params['volatility_threshold'] * 0.95)
                    else:
                        # Single mode hoạt động tốt hơn
                        logger.info(f"Tối ưu tham số cho {regime}: ưu tiên single mode")
                        optimized_params['volatility_threshold'] = min(3.5, optimized_params['volatility_threshold'] * 1.05)
                
                elif regime == 'trending_volatile':
                    # Thị trường xu hướng biến động
                    if single_win_rate > hedge_win_rate:
                        # Single mode hoạt động tốt hơn
                        logger.info(f"Tối ưu tham số cho {regime}: ưu tiên single mode")
                        optimized_params['trend_strength_threshold'] = max(25.0, optimized_params['trend_strength_threshold'] * 0.95)
                    else:
                        # Hedge mode hoạt động tốt hơn
                        logger.info(f"Tối ưu tham số cho {regime}: ưu tiên hedge mode")
                        optimized_params['trend_strength_threshold'] = min(45.0, optimized_params['trend_strength_threshold'] * 1.05)
            
            # Giới hạn các tham số
            optimized_params['volatility_threshold'] = max(1.0, min(5.0, optimized_params['volatility_threshold']))
            optimized_params['trend_strength_threshold'] = max(20.0, min(50.0, optimized_params['trend_strength_threshold']))
            
            # Lưu tham số đã tối ưu
            self.config = optimized_params
            self.save_config()
            
            logger.info(f"Đã tối ưu hóa tham số: volatility_threshold={optimized_params['volatility_threshold']:.2f}, "
                       f"trend_strength_threshold={optimized_params['trend_strength_threshold']:.2f}")
            
            return optimized_params
        except Exception as e:
            logger.error(f"Lỗi khi tối ưu hóa tham số: {e}")
            return self.config
    
    def get_summary_report(self):
        """
        Tạo báo cáo tóm tắt về hiệu suất và khuyến nghị
        
        Returns:
            dict: Báo cáo tóm tắt
        """
        try:
            # Tính tỷ lệ thắng
            hedge_total = self.stats['hedge_win_count'] + self.stats['hedge_loss_count']
            single_total = self.stats['single_win_count'] + self.stats['single_loss_count']
            
            hedge_win_rate = 0 if hedge_total == 0 else self.stats['hedge_win_count'] / hedge_total
            single_win_rate = 0 if single_total == 0 else self.stats['single_win_count'] / single_total
            
            # Phân tích hiệu suất theo chế độ thị trường
            regime_performance = {}
            for regime, metrics in self.performance_metrics.items():
                hedge_trades = metrics['hedge_win_count'] + metrics['hedge_loss_count']
                single_trades = metrics['single_win_count'] + metrics['single_loss_count']
                
                hedge_win_rate_regime = 0 if hedge_trades == 0 else metrics['hedge_win_count'] / hedge_trades
                single_win_rate_regime = 0 if single_trades == 0 else metrics['single_win_count'] / single_trades
                
                better_mode = 'hedge' if hedge_win_rate_regime > single_win_rate_regime else 'single'
                
                regime_performance[regime] = {
                    'hedge_win_rate': hedge_win_rate_regime,
                    'single_win_rate': single_win_rate_regime,
                    'hedge_pnl': metrics['hedge_pnl'],
                    'single_pnl': metrics['single_pnl'],
                    'better_mode': better_mode,
                    'trade_count': hedge_trades + single_trades
                }
            
            # Tạo báo cáo
            report = {
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'overall_stats': {
                    'hedge_win_rate': hedge_win_rate,
                    'single_win_rate': single_win_rate,
                    'hedge_total_trades': hedge_total,
                    'single_total_trades': single_total,
                    'adaptive_pnl': self.stats['adaptive_pnl'],
                    'hedge_only_pnl': self.stats['hedge_only_pnl'],
                    'single_only_pnl': self.stats['single_only_pnl']
                },
                'regime_performance': regime_performance,
                'current_market_regime': self.current_market_regime,
                'current_volatility': self.current_volatility,
                'current_trend_strength': self.current_trend_strength,
                'optimal_sessions': self.optimal_sessions,
                'config': self.config
            }
            
            return report
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo tóm tắt: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }


# Ví dụ sử dụng
if __name__ == "__main__":
    # Import các module cần thiết
    from binance_api import BinanceAPI
    from binance_api_fixes import apply_fixes_to_api
    
    # Khởi tạo API
    api = BinanceAPI()
    api = apply_fixes_to_api(api)
    
    # Khởi tạo selector
    mode_selector = AdaptiveModeSelector(api)
    
    # Phân tích thị trường
    analysis = mode_selector.analyze_market_conditions('BTCUSDT')
    print(f"Phân tích thị trường: {analysis}")
    
    # Lấy tham số giao dịch
    params = mode_selector.get_trading_parameters('BTCUSDT', analysis)
    print(f"Tham số giao dịch: {params}")
    
    # Tạo báo cáo tóm tắt
    report = mode_selector.get_summary_report()
    print(f"Báo cáo tóm tắt: {report}")