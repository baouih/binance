#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kiểm tra chiến lược đa lệnh và rủi ro cao

Script này kiểm tra hiệu suất của chiến lược đa lệnh với mức rủi ro cao (25-30%)
trên nhiều cặp tiền và khung thời gian.
"""

import os
import sys
import json
import time
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional

# Thêm thư mục gốc vào PATH
sys.path.append(os.path.abspath('.'))

# Import các module
from adaptive_risk_manager import AdaptiveRiskManager
from adaptive_strategy_selector import AdaptiveStrategySelector
from multi_position_manager import MultiPositionManager
from data_loader import load_historical_data

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('high_risk_multi_position_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('high_risk_test')

class HighRiskMultiPositionTest:
    """
    Lớp kiểm tra chiến lược đa lệnh với rủi ro cao
    """
    
    def __init__(self, config_path: str = 'configs/high_risk_multi_position_config.json',
                start_date: str = None, end_date: str = None,
                symbols: List[str] = None, timeframes: List[str] = None,
                initial_balance: float = 10000.0):
        """
        Khởi tạo kiểm tra
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
            start_date (str): Ngày bắt đầu (YYYY-MM-DD)
            end_date (str): Ngày kết thúc (YYYY-MM-DD)
            symbols (List[str]): Danh sách cặp tiền cần test
            timeframes (List[str]): Danh sách khung thời gian
            initial_balance (float): Số dư ban đầu
        """
        # Tham số kiểm tra
        self.config_path = config_path
        
        # Mặc định là test 3 tháng gần nhất nếu không có ngày
        if not end_date:
            self.end_date = datetime.now()
        else:
            self.end_date = datetime.strptime(end_date, '%Y-%m-%d')
            
        if not start_date:
            self.start_date = self.end_date - timedelta(days=90)
        else:
            self.start_date = datetime.strptime(start_date, '%Y-%m-%d')
        
        # Mặc định test BTC, ETH và các đồng lớn
        self.symbols = symbols or ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "LINKUSDT"]
        
        # Mặc định test 1h, 4h, 1d
        self.timeframes = timeframes or ["1h", "4h", "1d"]
        
        # Số dư ban đầu
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        
        # Tải cấu hình
        self._load_config()
        
        # Khởi tạo các manager
        self._initialize_managers()
        
        # Dữ liệu lịch sử
        self.historical_data = {}
        
        # Kết quả kiểm tra
        self.test_results = {
            'overall': {},
            'by_symbol': {},
            'by_timeframe': {},
            'by_risk_level': {},
            'trades': []
        }
        
        # Chỉ số theo dõi
        self.balance_history = []
        self.drawdowns = []
        self.equity_curve = []
        
    def _load_config(self):
        """
        Tải cấu hình kiểm tra
        """
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            logger.info(f"Đã tải cấu hình từ {self.config_path}")
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {e}")
            # Cấu hình mặc định
            self.config = {
                "risk_config": {
                    "risk_levels": {
                        "default": 25.0,
                        "high": 30.0,
                        "medium": 20.0,
                        "low": 15.0
                    }
                }
            }
    
    def _initialize_managers(self):
        """
        Khởi tạo các manager cho kiểm tra
        """
        # Risk manager
        self.risk_manager = AdaptiveRiskManager(
            default_sl_pct=0.02, 
            default_tp_pct=0.06,
            atr_periods=14
        )
        
        # Strategy selector
        self.strategy_selector = AdaptiveStrategySelector()
        
        # Multi-position manager
        self.position_manager = MultiPositionManager(config_path=self.config_path)
    
    def _load_historical_data(self):
        """
        Tải dữ liệu lịch sử cho tất cả các cặp và khung thời gian
        """
        for symbol in self.symbols:
            self.historical_data[symbol] = {}
            
            for timeframe in self.timeframes:
                # Convert date to string
                start_str = self.start_date.strftime('%Y-%m-%d')
                end_str = self.end_date.strftime('%Y-%m-%d')
                
                try:
                    # Tải dữ liệu từ data_loader
                    df = load_historical_data(
                        symbol, 
                        timeframe, 
                        start_str, 
                        end_str
                    )
                    
                    if df is not None and not df.empty:
                        # Tính ATR
                        df = self.risk_manager.calculate_atr(df)
                        
                        # Lưu vào dictionary
                        self.historical_data[symbol][timeframe] = df
                        logger.info(f"Đã tải {len(df)} nến dữ liệu cho {symbol} {timeframe}")
                    else:
                        logger.warning(f"Không có dữ liệu cho {symbol} {timeframe}")
                except Exception as e:
                    logger.error(f"Lỗi khi tải dữ liệu {symbol} {timeframe}: {e}")
    
    def run_test(self):
        """
        Chạy kiểm tra chiến lược
        """
        # Tải dữ liệu lịch sử
        logger.info("Bắt đầu tải dữ liệu lịch sử...")
        self._load_historical_data()
        
        # Kiểm tra dữ liệu đã tải đầy đủ chưa
        if not self._validate_data():
            logger.error("Dữ liệu lịch sử không đầy đủ. Dừng kiểm tra.")
            return False
        
        # Chạy backtest theo thời gian
        logger.info("Bắt đầu chạy backtest...")
        self._run_backtest()
        
        # Tính toán các chỉ số và ghi kết quả
        logger.info("Tính toán các chỉ số và kết quả...")
        self._calculate_results()
        
        # Lưu kết quả
        self._save_results()
        
        # Vẽ biểu đồ
        self._plot_results()
        
        return True
    
    def _validate_data(self) -> bool:
        """
        Kiểm tra dữ liệu lịch sử đã tải đầy đủ chưa
        
        Returns:
            bool: True nếu dữ liệu đầy đủ, False nếu không
        """
        for symbol in self.symbols:
            if symbol not in self.historical_data:
                logger.error(f"Thiếu dữ liệu cho {symbol}")
                return False
            
            for timeframe in self.timeframes:
                if timeframe not in self.historical_data[symbol]:
                    logger.error(f"Thiếu dữ liệu cho {symbol} {timeframe}")
                    return False
                
                # Kiểm tra số lượng nến
                min_candles = 100
                if len(self.historical_data[symbol][timeframe]) < min_candles:
                    logger.error(f"Thiếu dữ liệu cho {symbol} {timeframe}: chỉ có {len(self.historical_data[symbol][timeframe])} nến (cần ít nhất {min_candles})")
                    return False
        
        return True
    
    def _run_backtest(self):
        """
        Chạy backtest theo thời gian
        """
        # Lấy các mức rủi ro từ cấu hình
        risk_levels = self.config.get('risk_config', {}).get('risk_levels', {})
        default_risk = risk_levels.get('default', 25.0)
        high_risk = risk_levels.get('high', 30.0)
        
        # Tạo danh sách date range tổng hợp từ tất cả các khung thời gian
        all_dates = set()
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                if timeframe in self.historical_data[symbol]:
                    dates = self.historical_data[symbol][timeframe].index.tolist()
                    all_dates.update(dates)
        
        # Sắp xếp lại các ngày
        date_list = sorted(list(all_dates))
        
        # Lặp qua từng ngày
        logger.info(f"Bắt đầu backtest từ {date_list[0]} đến {date_list[-1]}")
        
        # Danh sách vị thế đang mở
        open_positions = {}
        
        # Lịch sử tài khoản
        self.balance_history = [{'date': date_list[0], 'balance': self.initial_balance}]
        
        for i, current_date in enumerate(date_list):
            if i % 100 == 0:
                logger.info(f"Đang xử lý ngày {current_date} ({i+1}/{len(date_list)})")
            
            # Kiểm tra vị thế hiện tại và giá hiện tại
            current_prices = self._get_current_prices(current_date)
            
            # Cập nhật trailing stop cho các vị thế đang mở
            positions_to_close = self._update_positions(open_positions, current_prices, current_date)
            
            # Đóng các vị thế theo trailing stop
            for pos_id in positions_to_close:
                self._close_position(open_positions, pos_id, current_prices, current_date, 'trailing_stop')
            
            # Tìm kiếm tín hiệu mới cho từng cặp và khung thời gian
            for symbol in self.symbols:
                for timeframe in self.timeframes:
                    # Kiểm tra số lệnh mở hiện tại
                    if len(open_positions) >= self.position_manager.max_positions:
                        break
                    
                    # Lấy dữ liệu đến thời điểm hiện tại
                    df = self._get_data_until_date(symbol, timeframe, current_date)
                    
                    if df is not None and len(df) > 50:  # Cần ít nhất 50 nến để có đủ dữ liệu
                        # Phát hiện tín hiệu
                        signal = self._detect_signal(df, symbol, timeframe)
                        
                        if signal and signal['direction']:
                            # Tính SL và TP với mức rủi ro cao
                            entry_price = current_prices.get(symbol)
                            if not entry_price:
                                continue
                                
                            # Sử dụng market_regime để tính SL/TP
                            market_regime = self.strategy_selector.get_market_regime(symbol, timeframe)
                            
                            # Tính toán SL/TP với risk_level cao
                            sl_price = self.risk_manager.calculate_adaptive_stoploss(
                                df, signal['direction'], entry_price, market_regime, risk_level=high_risk
                            )
                            
                            tp_price = self.risk_manager.calculate_adaptive_takeprofit(
                                df, signal['direction'], entry_price, market_regime, risk_level=high_risk
                            )
                            
                            # Tính kích thước vị thế
                            position_size = self.position_manager.get_optimal_trade_size(
                                symbol, timeframe, self.current_balance, high_risk
                            )
                            
                            if position_size > 0:
                                # Mở vị thế mới
                                position_id = f"{symbol}_{timeframe}_{current_date.strftime('%Y%m%d%H%M')}_{signal['direction']}"
                                
                                open_positions[position_id] = {
                                    'position_id': position_id,
                                    'symbol': symbol,
                                    'timeframe': timeframe,
                                    'direction': signal['direction'],
                                    'entry_price': entry_price,
                                    'stop_loss': sl_price,
                                    'take_profit': tp_price,
                                    'size': position_size,
                                    'risk_level': high_risk,
                                    'open_date': current_date,
                                    'strategy': signal.get('strategy', 'unknown'),
                                    'market_regime': market_regime
                                }
                                
                                logger.info(f"Mở vị thế {position_id}: {symbol} {signal['direction']} tại {entry_price}, SL: {sl_price}, TP: {tp_price}, Size: {position_size}$")
            
            # Kiểm tra các vị thế đang mở có hit SL/TP không
            for pos_id, position in list(open_positions.items()):
                # Kiểm tra giá hiện tại
                symbol = position['symbol']
                if symbol not in current_prices:
                    continue
                    
                current_price = current_prices[symbol]
                
                # Kiểm tra SL/TP
                if position['direction'].lower() == 'long':
                    # Kiểm tra SL
                    if current_price <= position['stop_loss']:
                        self._close_position(open_positions, pos_id, current_prices, current_date, 'stop_loss')
                    # Kiểm tra TP
                    elif current_price >= position['take_profit']:
                        self._close_position(open_positions, pos_id, current_prices, current_date, 'take_profit')
                else:  # short
                    # Kiểm tra SL
                    if current_price >= position['stop_loss']:
                        self._close_position(open_positions, pos_id, current_prices, current_date, 'stop_loss')
                    # Kiểm tra TP
                    elif current_price <= position['take_profit']:
                        self._close_position(open_positions, pos_id, current_prices, current_date, 'take_profit')
            
            # Cập nhật lịch sử tài khoản
            self.balance_history.append({'date': current_date, 'balance': self.current_balance})
            
        # Đóng tất cả vị thế còn lại ở cuối kỳ
        final_prices = self._get_current_prices(date_list[-1])
        for pos_id in list(open_positions.keys()):
            self._close_position(open_positions, pos_id, final_prices, date_list[-1], 'end_of_test')
        
        logger.info(f"Hoàn thành backtest. Số dư cuối: ${self.current_balance:.2f}")
    
    def _get_current_prices(self, current_date) -> Dict[str, float]:
        """
        Lấy giá hiện tại của tất cả các cặp tại thời điểm cụ thể
        
        Args:
            current_date: Thời điểm cần lấy giá
            
        Returns:
            Dict[str, float]: Dictionary với key là symbol, value là giá
        """
        prices = {}
        
        for symbol in self.symbols:
            # Ưu tiên lấy giá từ khung 1h (chi tiết hơn)
            for timeframe in ["1h", "4h", "1d"]:
                if timeframe in self.historical_data[symbol]:
                    df = self.historical_data[symbol][timeframe]
                    # Lọc các nến đến current_date
                    df_until = df[df.index <= current_date]
                    
                    if not df_until.empty:
                        # Lấy giá đóng cửa của nến gần nhất
                        prices[symbol] = df_until['close'].iloc[-1]
                        break
        
        return prices
    
    def _get_data_until_date(self, symbol: str, timeframe: str, current_date) -> pd.DataFrame:
        """
        Lấy dữ liệu đến thời điểm cụ thể
        
        Args:
            symbol: Mã cặp tiền
            timeframe: Khung thời gian
            current_date: Thời điểm hiện tại
            
        Returns:
            pd.DataFrame: DataFrame với dữ liệu đến thời điểm hiện tại
        """
        if symbol not in self.historical_data or timeframe not in self.historical_data[symbol]:
            return None
            
        df = self.historical_data[symbol][timeframe]
        df_until = df[df.index <= current_date]
        
        return df_until
    
    def _detect_signal(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Dict:
        """
        Phát hiện tín hiệu giao dịch từ dữ liệu
        
        Args:
            df: DataFrame với dữ liệu
            symbol: Mã cặp tiền
            timeframe: Khung thời gian
            
        Returns:
            Dict: Thông tin tín hiệu
        """
        # Đây là phần mô phỏng cho việc phát hiện tín hiệu
        # Trong thực tế, cần có logic phức tạp hơn
        
        # Lấy N nến gần nhất
        n_candles = 10
        if len(df) < n_candles:
            return None
            
        recent_df = df.iloc[-n_candles:]
        
        # Kiểm tra phương thức mặc định
        # Đơn giản hóa ở đây: 1. Kiểm tra 3 nến đi xuống liên tiếp -> LONG
        #                     2. Kiểm tra 3 nến đi lên liên tiếp -> SHORT
        
        # Kiểm tra chế độ thị trường
        market_regime = self.strategy_selector.get_market_regime(symbol, timeframe)
        
        # Lấy chiến lược theo chế độ thị trường
        if market_regime == 'trending':
            # Chiến lược theo xu hướng
            # Đơn giản hóa: Kiểm tra xu hướng qua 5 nến gần nhất
            close_prices = recent_df['close'].values
            trend = close_prices[-1] > close_prices[-6] if len(close_prices) >= 6 else False
            
            if trend:
                # Xu hướng tăng -> LONG
                return {'direction': 'long', 'strategy': 'trend_following', 'market_regime': market_regime}
            else:
                # Xu hướng giảm -> SHORT
                return {'direction': 'short', 'strategy': 'trend_following', 'market_regime': market_regime}
        elif market_regime == 'ranging':
            # Chiến lược giao dịch đi ngang
            # Kiểm tra giá đang ở gần đỉnh hay đáy
            close = recent_df['close'].iloc[-1]
            high = recent_df['high'].max()
            low = recent_df['low'].min()
            
            range_percent = (high - low) / low * 100
            
            if range_percent < 5:  # Range nhỏ, không đủ biến động để giao dịch
                return None
                
            upper_range = high - (high - low) * 0.2
            lower_range = low + (high - low) * 0.2
            
            if close > upper_range:
                # Giá gần đỉnh -> SHORT
                return {'direction': 'short', 'strategy': 'range_trading', 'market_regime': market_regime}
            elif close < lower_range:
                # Giá gần đáy -> LONG
                return {'direction': 'long', 'strategy': 'range_trading', 'market_regime': market_regime}
        elif market_regime == 'volatile':
            # Chiến lược trong thị trường biến động
            # Kiểm tra sự đảo chiều đột ngột
            if len(recent_df) >= 3:
                last_3_candles = recent_df.iloc[-3:].reset_index(drop=True)
                candle1 = last_3_candles.iloc[0]
                candle2 = last_3_candles.iloc[1]
                candle3 = last_3_candles.iloc[2]
                
                # Đảo chiều tăng mạnh
                if candle1['close'] < candle1['open'] and candle2['close'] < candle2['open'] and candle3['close'] > candle3['open']:
                    return {'direction': 'long', 'strategy': 'breakout', 'market_regime': market_regime}
                
                # Đảo chiều giảm mạnh
                if candle1['close'] > candle1['open'] and candle2['close'] > candle2['open'] and candle3['close'] < candle3['open']:
                    return {'direction': 'short', 'strategy': 'breakout', 'market_regime': market_regime}
        
        # Mặc định không có tín hiệu
        return None
    
    def _update_positions(self, positions: Dict, current_prices: Dict, current_date) -> List[str]:
        """
        Cập nhật trạng thái các vị thế đang mở
        
        Args:
            positions: Dictionary các vị thế đang mở
            current_prices: Giá hiện tại của các cặp tiền
            current_date: Ngày hiện tại
            
        Returns:
            List[str]: Danh sách ID vị thế cần đóng
        """
        positions_to_close = []
        
        # Cập nhật trailing stop
        for pos_id, position in positions.items():
            symbol = position['symbol']
            if symbol not in current_prices:
                continue
                
            current_price = current_prices[symbol]
            direction = position['direction']
            entry_price = position['entry_price']
            
            # Kiểm tra trailing stop hiện tại
            has_trailing = position.get('has_trailing_stop', False)
            current_trailing_price = position.get('trailing_stop_price')
            
            # Tính toán trailing stop mới
            trail_params = self.position_manager.get_trailing_stop_parameters(
                symbol, entry_price, current_price, direction
            )
            
            # Nếu chưa có trailing stop và đạt ngưỡng kích hoạt
            if not has_trailing and trail_params.get('should_activate', False):
                position['has_trailing_stop'] = True
                position['trailing_stop_price'] = trail_params.get('trailing_stop_price')
                position['trailing_activation_date'] = current_date
                
            # Nếu đã có trailing stop, kiểm tra xem có cần cập nhật không
            elif has_trailing and trail_params.get('should_activate', False):
                new_trail_price = trail_params.get('trailing_stop_price')
                
                # Chỉ cập nhật nếu trailing stop mới có lợi hơn
                if direction.lower() == 'long' and new_trail_price > current_trailing_price:
                    position['trailing_stop_price'] = new_trail_price
                elif direction.lower() == 'short' and new_trail_price < current_trailing_price:
                    position['trailing_stop_price'] = new_trail_price
            
            # Kiểm tra xem đã hit trailing stop chưa
            if has_trailing:
                if (direction.lower() == 'long' and current_price <= position['trailing_stop_price']) or \
                   (direction.lower() == 'short' and current_price >= position['trailing_stop_price']):
                    # Thêm vào danh sách cần đóng
                    positions_to_close.append(pos_id)
        
        return positions_to_close
    
    def _close_position(self, positions: Dict, position_id: str, 
                        current_prices: Dict, current_date, exit_reason: str):
        """
        Đóng một vị thế và cập nhật số dư
        
        Args:
            positions: Dictionary các vị thế đang mở
            position_id: ID vị thế cần đóng
            current_prices: Giá hiện tại của các cặp tiền
            current_date: Ngày đóng vị thế
            exit_reason: Lý do đóng vị thế
        """
        if position_id not in positions:
            return
            
        position = positions[position_id]
        symbol = position['symbol']
        
        if symbol not in current_prices:
            return
            
        # Tính P/L
        exit_price = current_prices[symbol]
        entry_price = position['entry_price']
        direction = position['direction']
        position_size = position['size']
        
        if direction.lower() == 'long':
            pnl_pct = (exit_price - entry_price) / entry_price
        else:  # short
            pnl_pct = (entry_price - exit_price) / entry_price
            
        # Tính số tiền lãi/lỗ
        pnl_amount = position_size * pnl_pct
        
        # Cập nhật số dư
        self.current_balance += pnl_amount
        
        # Thêm thông tin vào vị thế
        position['exit_price'] = exit_price
        position['exit_date'] = current_date
        position['exit_reason'] = exit_reason
        position['pnl_pct'] = pnl_pct * 100  # Chuyển sang phần trăm
        position['pnl_amount'] = pnl_amount
        
        # Thêm vào danh sách giao dịch đã hoàn thành
        self.test_results['trades'].append(position)
        
        # Xóa khỏi danh sách vị thế đang mở
        del positions[position_id]
        
        # Log thông tin
        logger.info(f"Đóng vị thế {position_id}: {symbol} {direction} tại {exit_price}, P/L: {pnl_pct*100:.2f}%, ${pnl_amount:.2f}, Lý do: {exit_reason}")
    
    def _calculate_results(self):
        """
        Tính toán các chỉ số kết quả
        """
        trades = self.test_results['trades']
        if not trades:
            logger.warning("Không có giao dịch nào để tính toán kết quả")
            return
            
        # --- Kết quả tổng thể ---
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t['pnl_amount'] > 0)
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        
        profit_amount = sum(t['pnl_amount'] for t in trades)
        profit_pct = profit_amount / self.initial_balance * 100
        
        # Tính drawdown
        balances = [b['balance'] for b in self.balance_history]
        max_balance = balances[0]
        drawdowns = []
        
        for balance in balances:
            max_balance = max(max_balance, balance)
            drawdown = (max_balance - balance) / max_balance * 100
            drawdowns.append(drawdown)
            
        max_drawdown = max(drawdowns) if drawdowns else 0
        
        # Tính profit factor
        gross_profit = sum(t['pnl_amount'] for t in trades if t['pnl_amount'] > 0)
        gross_loss = abs(sum(t['pnl_amount'] for t in trades if t['pnl_amount'] < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Lưu kết quả tổng thể
        self.test_results['overall'] = {
            'start_date': self.start_date.strftime('%Y-%m-%d'),
            'end_date': self.end_date.strftime('%Y-%m-%d'),
            'initial_balance': self.initial_balance,
            'final_balance': self.current_balance,
            'profit_amount': profit_amount,
            'profit_pct': profit_pct,
            'max_drawdown': max_drawdown,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor
        }
        
        # --- Kết quả theo symbol ---
        for symbol in self.symbols:
            symbol_trades = [t for t in trades if t['symbol'] == symbol]
            if not symbol_trades:
                continue
                
            symbol_total = len(symbol_trades)
            symbol_winning = sum(1 for t in symbol_trades if t['pnl_amount'] > 0)
            symbol_losing = symbol_total - symbol_winning
            symbol_win_rate = symbol_winning / symbol_total * 100 if symbol_total > 0 else 0
            
            symbol_profit = sum(t['pnl_amount'] for t in symbol_trades)
            symbol_profit_pct = symbol_profit / self.initial_balance * 100
            
            self.test_results['by_symbol'][symbol] = {
                'total_trades': symbol_total,
                'winning_trades': symbol_winning,
                'losing_trades': symbol_losing,
                'win_rate': symbol_win_rate,
                'profit_amount': symbol_profit,
                'profit_pct': symbol_profit_pct
            }
            
        # --- Kết quả theo timeframe ---
        for timeframe in self.timeframes:
            tf_trades = [t for t in trades if t['timeframe'] == timeframe]
            if not tf_trades:
                continue
                
            tf_total = len(tf_trades)
            tf_winning = sum(1 for t in tf_trades if t['pnl_amount'] > 0)
            tf_losing = tf_total - tf_winning
            tf_win_rate = tf_winning / tf_total * 100 if tf_total > 0 else 0
            
            tf_profit = sum(t['pnl_amount'] for t in tf_trades)
            tf_profit_pct = tf_profit / self.initial_balance * 100
            
            self.test_results['by_timeframe'][timeframe] = {
                'total_trades': tf_total,
                'winning_trades': tf_winning,
                'losing_trades': tf_losing,
                'win_rate': tf_win_rate,
                'profit_amount': tf_profit,
                'profit_pct': tf_profit_pct
            }
        
        # --- Kết quả theo market regime ---
        market_regimes = set(t.get('market_regime', 'unknown') for t in trades)
        for regime in market_regimes:
            regime_trades = [t for t in trades if t.get('market_regime') == regime]
            if not regime_trades:
                continue
                
            regime_total = len(regime_trades)
            regime_winning = sum(1 for t in regime_trades if t['pnl_amount'] > 0)
            regime_losing = regime_total - regime_winning
            regime_win_rate = regime_winning / regime_total * 100 if regime_total > 0 else 0
            
            regime_profit = sum(t['pnl_amount'] for t in regime_trades)
            regime_profit_pct = regime_profit / self.initial_balance * 100
            
            self.test_results['by_market_regime'] = self.test_results.get('by_market_regime', {})
            self.test_results['by_market_regime'][regime] = {
                'total_trades': regime_total,
                'winning_trades': regime_winning,
                'losing_trades': regime_losing,
                'win_rate': regime_win_rate,
                'profit_amount': regime_profit,
                'profit_pct': regime_profit_pct
            }
    
    def _save_results(self):
        """
        Lưu kết quả kiểm tra
        """
        # Lưu kết quả tổng thể
        output_dir = 'high_risk_test_results'
        os.makedirs(output_dir, exist_ok=True)
        
        # Lưu kết quả JSON
        result_file = os.path.join(output_dir, 'high_risk_multi_position_results.json')
        try:
            with open(result_file, 'w') as f:
                json.dump(self.test_results, f, indent=4, default=str)
            logger.info(f"Đã lưu kết quả chi tiết vào {result_file}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu kết quả JSON: {e}")
        
        # Lưu chuỗi tài khoản
        balance_file = os.path.join(output_dir, 'balance_history.json')
        try:
            with open(balance_file, 'w') as f:
                json.dump(self.balance_history, f, indent=4, default=str)
            logger.info(f"Đã lưu lịch sử số dư vào {balance_file}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu lịch sử số dư: {e}")
        
        # Tạo báo cáo tóm tắt
        report_file = os.path.join(output_dir, 'high_risk_summary_report.txt')
        try:
            with open(report_file, 'w') as f:
                f.write("=== BÁO CÁO CHIẾN LƯỢC RỦI RO CAO VÀ ĐA LỆNH ===\n\n")
                
                overall = self.test_results['overall']
                f.write(f"Thời gian: {overall['start_date']} đến {overall['end_date']}\n")
                f.write(f"Số dư ban đầu: ${overall['initial_balance']:.2f}\n")
                f.write(f"Số dư cuối: ${overall['final_balance']:.2f}\n")
                f.write(f"Lợi nhuận: ${overall['profit_amount']:.2f} ({overall['profit_pct']:.2f}%)\n")
                f.write(f"Drawdown tối đa: {overall['max_drawdown']:.2f}%\n")
                f.write(f"Tổng giao dịch: {overall['total_trades']}\n")
                f.write(f"Thắng/Thua: {overall['winning_trades']}/{overall['losing_trades']}\n")
                f.write(f"Tỷ lệ thắng: {overall['win_rate']:.2f}%\n")
                f.write(f"Profit factor: {overall['profit_factor']:.2f}\n\n")
                
                f.write("=== KẾT QUẢ THEO CẶP TIỀN ===\n")
                for symbol, stats in self.test_results['by_symbol'].items():
                    f.write(f"\n{symbol}:\n")
                    f.write(f"  Tổng giao dịch: {stats['total_trades']}\n")
                    f.write(f"  Thắng/Thua: {stats['winning_trades']}/{stats['losing_trades']}\n")
                    f.write(f"  Tỷ lệ thắng: {stats['win_rate']:.2f}%\n")
                    f.write(f"  Lợi nhuận: ${stats['profit_amount']:.2f} ({stats['profit_pct']:.2f}%)\n")
                
                f.write("\n=== KẾT QUẢ THEO KHUNG THỜI GIAN ===\n")
                for timeframe, stats in self.test_results['by_timeframe'].items():
                    f.write(f"\n{timeframe}:\n")
                    f.write(f"  Tổng giao dịch: {stats['total_trades']}\n")
                    f.write(f"  Thắng/Thua: {stats['winning_trades']}/{stats['losing_trades']}\n")
                    f.write(f"  Tỷ lệ thắng: {stats['win_rate']:.2f}%\n")
                    f.write(f"  Lợi nhuận: ${stats['profit_amount']:.2f} ({stats['profit_pct']:.2f}%)\n")
                
                if 'by_market_regime' in self.test_results:
                    f.write("\n=== KẾT QUẢ THEO CHẾ ĐỘ THỊ TRƯỜNG ===\n")
                    for regime, stats in self.test_results['by_market_regime'].items():
                        f.write(f"\n{regime}:\n")
                        f.write(f"  Tổng giao dịch: {stats['total_trades']}\n")
                        f.write(f"  Thắng/Thua: {stats['winning_trades']}/{stats['losing_trades']}\n")
                        f.write(f"  Tỷ lệ thắng: {stats['win_rate']:.2f}%\n")
                        f.write(f"  Lợi nhuận: ${stats['profit_amount']:.2f} ({stats['profit_pct']:.2f}%)\n")
            
            logger.info(f"Đã lưu báo cáo tóm tắt vào {report_file}")
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo tóm tắt: {e}")
    
    def _plot_results(self):
        """
        Vẽ biểu đồ kết quả
        """
        try:
            output_dir = 'high_risk_test_results'
            
            # Chuẩn bị dữ liệu
            dates = [b['date'] for b in self.balance_history]
            balances = [b['balance'] for b in self.balance_history]
            
            # 1. Biểu đồ đường chuỗi tài khoản
            plt.figure(figsize=(12, 6))
            plt.plot(dates, balances)
            plt.title('Account Balance History')
            plt.xlabel('Date')
            plt.ylabel('Balance ($)')
            plt.grid(True)
            plt.savefig(os.path.join(output_dir, 'balance_history.png'))
            plt.close()
            
            # 2. Biểu đồ drawdown
            max_balance = balances[0]
            drawdowns = []
            
            for balance in balances:
                max_balance = max(max_balance, balance)
                drawdown = (max_balance - balance) / max_balance * 100
                drawdowns.append(drawdown)
                
            plt.figure(figsize=(12, 6))
            plt.plot(dates, drawdowns)
            plt.fill_between(dates, drawdowns, 0, alpha=0.3)
            plt.title('Drawdown History')
            plt.xlabel('Date')
            plt.ylabel('Drawdown (%)')
            plt.grid(True)
            plt.savefig(os.path.join(output_dir, 'drawdown_history.png'))
            plt.close()
            
            # 3. Biểu đồ lãi lỗ theo cặp tiền
            symbols = list(self.test_results['by_symbol'].keys())
            profits = [self.test_results['by_symbol'][s]['profit_pct'] for s in symbols]
            
            plt.figure(figsize=(10, 6))
            bars = plt.bar(symbols, profits)
            
            # Đổi màu các cột theo lãi/lỗ
            for i, p in enumerate(profits):
                if p >= 0:
                    bars[i].set_color('green')
                else:
                    bars[i].set_color('red')
                    
            plt.title('Profit/Loss by Symbol')
            plt.xlabel('Symbol')
            plt.ylabel('Profit/Loss (%)')
            plt.grid(axis='y')
            plt.savefig(os.path.join(output_dir, 'profit_by_symbol.png'))
            plt.close()
            
            # 4. Biểu đồ lãi lỗ theo khung thời gian
            timeframes = list(self.test_results['by_timeframe'].keys())
            tf_profits = [self.test_results['by_timeframe'][tf]['profit_pct'] for tf in timeframes]
            
            plt.figure(figsize=(8, 6))
            bars = plt.bar(timeframes, tf_profits)
            
            # Đổi màu các cột theo lãi/lỗ
            for i, p in enumerate(tf_profits):
                if p >= 0:
                    bars[i].set_color('green')
                else:
                    bars[i].set_color('red')
                    
            plt.title('Profit/Loss by Timeframe')
            plt.xlabel('Timeframe')
            plt.ylabel('Profit/Loss (%)')
            plt.grid(axis='y')
            plt.savefig(os.path.join(output_dir, 'profit_by_timeframe.png'))
            plt.close()
            
            # 5. Biểu đồ phân phối lãi lỗ
            if self.test_results['trades']:
                pnl_percentages = [t['pnl_pct'] for t in self.test_results['trades']]
                plt.figure(figsize=(10, 6))
                plt.hist(pnl_percentages, bins=30, alpha=0.7, color='skyblue')
                plt.axvline(x=0, color='r', linestyle='--')
                plt.title('Distribution of Trade P/L')
                plt.xlabel('P/L (%)')
                plt.ylabel('Number of Trades')
                plt.grid(True)
                plt.savefig(os.path.join(output_dir, 'pnl_distribution.png'))
                plt.close()
                
            logger.info(f"Đã tạo biểu đồ kết quả trong thư mục {output_dir}")
        except Exception as e:
            logger.error(f"Lỗi khi vẽ biểu đồ: {e}")

if __name__ == "__main__":
    # Chạy kiểm tra với tham số mặc định
    tester = HighRiskMultiPositionTest()
    tester.run_test()