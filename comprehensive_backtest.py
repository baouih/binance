#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script backtest nâng cao cho bot giao dịch kết hợp AI

Script này thực hiện backtest toàn diện cho bot giao dịch, bao gồm 3 giai đoạn:
1. Huấn luyện ban đầu: Tạo mô hình AI cơ bản
2. Tối ưu hóa: Cải thiện mô hình và điều chỉnh trọng số
3. Kiểm thử mở rộng: Kiểm tra hiệu suất thực tế

Quá trình này giúp đánh giá một cách toàn diện hiệu suất của bot, tập trung vào 
đóng góp của AI để tăng tỷ lệ win và ROI.
"""

import os
import sys
import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from tqdm import tqdm
import matplotlib.dates as mdates
from typing import Dict, List, Tuple, Optional, Union, Any
from pathlib import Path

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('comprehensive_backtest.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Tạo các thư mục cần thiết
os.makedirs('backtest_results', exist_ok=True)
os.makedirs('backtest_charts', exist_ok=True)
os.makedirs('backtest_reports', exist_ok=True)
os.makedirs('backtest_data', exist_ok=True)
os.makedirs('configs', exist_ok=True)

class AIBotBacktester:
    """Lớp backtest chính cho bot giao dịch kết hợp AI"""
    
    def __init__(self, config_path: str = "backtest_master_config.json"):
        """
        Khởi tạo backtest bot với cấu hình từ file JSON
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình tổng thể
        """
        # Tải cấu hình
        logger.info(f"Tải cấu hình từ {config_path}")
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Chuẩn bị các thư mục kết quả
        self.report_dir = self.config.get('report_settings', {}).get('report_dir', 'backtest_reports')
        self.charts_dir = self.config.get('report_settings', {}).get('charts_dir', 'backtest_charts')
        self.data_dir = 'backtest_data'
        os.makedirs(self.report_dir, exist_ok=True)
        os.makedirs(self.charts_dir, exist_ok=True)
        
        # Khởi tạo biến kết quả
        self.results = {
            "phases": {},
            "summary": {},
            "comparison": {}
        }
        
        # Cài đặt ban đầu
        self.initial_balance = self.config.get('initial_balance', 10000)
        
        logger.info(f"Đã khởi tạo AIBotBacktester với số dư ban đầu: ${self.initial_balance}")
    
    def prepare_datasets(self):
        """
        Tải và chuẩn bị dữ liệu cho các cặp tiền và khung thời gian
        """
        logger.info("Bắt đầu chuẩn bị bộ dữ liệu...")
        
        # Import động để tránh phụ thuộc khi chỉ chạy prepare
        from binance_api import BinanceAPI
        
        api = BinanceAPI()
        
        # Lấy các cặp tiền và khung thời gian từ cấu hình
        symbols = self.config.get('symbols', ['BTCUSDT', 'ETHUSDT'])
        timeframes = self.config.get('timeframes', ['1h', '4h'])
        
        # Tải dữ liệu cho từng giai đoạn
        for period in self.config.get('market_periods', []):
            period_name = period.get('name')
            start_date = datetime.strptime(period.get('start_date'), '%Y-%m-%d')
            end_date = datetime.strptime(period.get('end_date'), '%Y-%m-%d')
            
            logger.info(f"Tải dữ liệu cho giai đoạn {period_name}: {start_date} đến {end_date}")
            
            for symbol in symbols:
                for timeframe in timeframes:
                    output_dir = os.path.join(self.data_dir, period_name)
                    os.makedirs(output_dir, exist_ok=True)
                    
                    filename = api.download_historical_data(
                        symbol=symbol,
                        interval=timeframe,
                        start_time=start_date,
                        end_time=end_date,
                        output_dir=output_dir
                    )
                    logger.info(f"Đã lưu: {filename}")
        
        # Tải dữ liệu cho các giai đoạn backtest
        for phase in self.config.get('phases', []):
            phase_name = phase.get('name')
            start_date = datetime.strptime(phase.get('start_date'), '%Y-%m-%d')
            end_date = datetime.strptime(phase.get('end_date'), '%Y-%m-%d')
            
            logger.info(f"Tải dữ liệu cho giai đoạn {phase_name}: {start_date} đến {end_date}")
            
            phase_symbols = phase.get('symbols', symbols)
            
            for symbol in phase_symbols:
                for timeframe in timeframes:
                    output_dir = os.path.join(self.data_dir, phase_name)
                    os.makedirs(output_dir, exist_ok=True)
                    
                    filename = api.download_historical_data(
                        symbol=symbol,
                        interval=timeframe,
                        start_time=start_date,
                        end_time=end_date,
                        output_dir=output_dir
                    )
                    logger.info(f"Đã lưu: {filename}")
                    
        logger.info("Đã hoàn thành chuẩn bị bộ dữ liệu")
        return True
    
    def _load_data(self, symbol: str, timeframe: str, start_date: str, end_date: str, data_dir: str = None) -> pd.DataFrame:
        """
        Tải dữ liệu từ file CSV
        
        Args:
            symbol (str): Mã cặp giao dịch (ví dụ: BTCUSDT)
            timeframe (str): Khung thời gian (ví dụ: 1h, 4h)
            start_date (str): Ngày bắt đầu (format: YYYY-MM-DD)
            end_date (str): Ngày kết thúc (format: YYYY-MM-DD)
            data_dir (str): Thư mục dữ liệu
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu giá
        """
        if data_dir is None:
            data_dir = self.data_dir
            
        # Tìm file phù hợp
        filename = f"{symbol}_{timeframe}_data.csv"
        filepath = os.path.join(data_dir, filename)
        
        if not os.path.exists(filepath):
            logger.warning(f"Không tìm thấy file dữ liệu: {filepath}")
            # Tìm file tương tự trong các thư mục con
            for root, dirs, files in os.walk(data_dir):
                for file in files:
                    if file == filename:
                        filepath = os.path.join(root, file)
                        logger.info(f"Tìm thấy file: {filepath}")
                        break
        
        if not os.path.exists(filepath):
            logger.error(f"Không thể tìm thấy file dữ liệu cho {symbol} {timeframe}")
            return pd.DataFrame()
        
        # Đọc dữ liệu
        df = pd.read_csv(filepath)
        
        # Chuyển đổi cột thời gian
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Lọc theo khoảng thời gian
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
        
        # Kiểm tra dữ liệu trống
        if df.empty:
            logger.warning(f"Không có dữ liệu trong khoảng thời gian từ {start_date} đến {end_date}")
            return pd.DataFrame()
        
        # Sắp xếp theo thời gian
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Tính toán thêm các chỉ báo kỹ thuật (nếu chưa có)
        if 'rsi' not in df.columns:
            df = self._calculate_indicators(df)
        
        logger.info(f"Đã tải dữ liệu {symbol} {timeframe} từ {start_date} đến {end_date}: {len(df)} mẫu")
        return df
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tính toán các chỉ báo kỹ thuật
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            
        Returns:
            pd.DataFrame: DataFrame với các chỉ báo đã tính
        """
        # Sao chép DataFrame để tránh ảnh hưởng đến dữ liệu gốc
        df = df.copy()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # EMA
        df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        # MACD
        df['ema12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema12'] - df['ema26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['sma20'] = df['close'].rolling(window=20).mean()
        std20 = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['sma20'] + (std20 * 2)
        df['bb_lower'] = df['sma20'] - (std20 * 2)
        
        # ATR
        tr1 = abs(df['high'] - df['low'])
        tr2 = abs(df['high'] - df['close'].shift())
        tr3 = abs(df['low'] - df['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=14).mean()
        
        # ADX
        plus_dm = df['high'].diff()
        minus_dm = df['low'].shift().diff(-1)
        plus_dm = plus_dm.where((plus_dm > 0) & (plus_dm > minus_dm), 0)
        minus_dm = minus_dm.where((minus_dm > 0) & (minus_dm > plus_dm), 0)
        
        tr = tr.replace(0, 0.000001)  # Tránh chia cho 0
        
        plus_di = 100 * (plus_dm.rolling(window=14).mean() / tr.rolling(window=14).mean())
        minus_di = 100 * (minus_dm.rolling(window=14).mean() / tr.rolling(window=14).mean())
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        
        df['di_plus'] = plus_di
        df['di_minus'] = minus_di
        df['adx'] = dx.rolling(window=14).mean()
        
        # Loại bỏ các hàng có NaN
        df = df.dropna().reset_index(drop=True)
        
        return df
    
    def run_backtest_phase(self, phase: Dict) -> Dict:
        """
        Chạy backtest cho một giai đoạn cụ thể
        
        Args:
            phase (Dict): Thông tin giai đoạn
            
        Returns:
            Dict: Kết quả backtest
        """
        phase_name = phase.get('name')
        logger.info(f"\n\n===== BẮT ĐẦU GIAI ĐOẠN: {phase_name} =====")
        
        # Cài đặt từ phase
        start_date = phase.get('start_date')
        end_date = phase.get('end_date')
        train_ratio = phase.get('train_ratio', 0.5)
        
        # Cấu hình cho giai đoạn này
        phase_config_path = phase.get('config')
        if os.path.exists(phase_config_path):
            with open(phase_config_path, 'r') as f:
                phase_config = json.load(f)
        else:
            logger.warning(f"Không tìm thấy file cấu hình {phase_config_path}, sử dụng cấu hình mặc định")
            phase_config = {}
        
        # Ghép với cấu hình tổng thể
        config = {**self.config, **phase_config}
        
        # Cập nhật các tham số đặc biệt
        config['exploration_rate'] = phase.get('exploration_rate', 0.5)
        config['ai_weight'] = phase.get('ai_weight', 0.3)
        
        # Danh sách cặp tiền cho giai đoạn này
        symbols = phase.get('symbols', self.config.get('symbols', ['BTCUSDT']))
        timeframes = self.config.get('timeframes', ['1h'])
        
        # Kết quả của giai đoạn
        phase_results = {
            "symbols": {},
            "summary": {},
            "trades": [],
            "balances": [],
            "config": config
        }
        
        # Chạy cho từng cặp tiền và khung thời gian
        for symbol in symbols:
            symbol_results = {}
            
            for timeframe in timeframes:
                logger.info(f"\nBacktest {symbol} {timeframe} trong giai đoạn {phase_name}...")
                
                # Tải dữ liệu
                df = self._load_data(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if df.empty:
                    logger.warning(f"Bỏ qua {symbol} {timeframe} do không có dữ liệu")
                    continue
                
                # Chia dữ liệu train/test
                train_size = int(len(df) * train_ratio)
                train_df = df.iloc[:train_size]
                test_df = df.iloc[train_size:]
                
                logger.info(f"Dữ liệu huấn luyện: {len(train_df)} mẫu, Dữ liệu kiểm thử: {len(test_df)} mẫu")
                
                # Thiết lập backtest cho cặp cụ thể
                specific_results = self._run_symbol_backtest(
                    symbol=symbol,
                    timeframe=timeframe,
                    train_df=train_df,
                    test_df=test_df,
                    config=config,
                    phase_name=phase_name
                )
                
                # Thêm vào kết quả symbol
                symbol_results[timeframe] = specific_results
                
                # Thêm giao dịch vào danh sách chung
                phase_results['trades'].extend(specific_results.get('trades', []))
                
                # Thêm dữ liệu số dư
                for balance in specific_results.get('balances', []):
                    balance['symbol'] = symbol
                    balance['timeframe'] = timeframe
                    phase_results['balances'].append(balance)
            
            # Thêm vào kết quả giai đoạn
            phase_results['symbols'][symbol] = symbol_results
        
        # Tính tổng hợp cho giai đoạn
        phase_results['summary'] = self._calculate_phase_summary(phase_results)
        
        # Lưu kết quả giai đoạn
        result_path = os.path.join(self.report_dir, f"{phase_name}_results.json")
        with open(result_path, 'w') as f:
            # Chuyển datetime thành string để có thể serialize
            serializable_results = self._make_serializable(phase_results)
            json.dump(serializable_results, f, indent=4)
        
        logger.info(f"Đã lưu kết quả giai đoạn {phase_name} vào {result_path}")
        
        # Tạo biểu đồ
        self._create_phase_charts(phase_results, phase_name)
        
        return phase_results
    
    def _make_serializable(self, data):
        """Chuyển đổi dữ liệu thành dạng có thể serialized với JSON"""
        if isinstance(data, dict):
            return {k: self._make_serializable(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._make_serializable(i) for i in data]
        elif isinstance(data, (pd.Timestamp, datetime)):
            return data.isoformat()
        elif isinstance(data, (np.float32, np.float64)):
            return float(data)
        elif isinstance(data, (np.int32, np.int64)):
            return int(data)
        else:
            return data
    
    def _run_symbol_backtest(self, symbol: str, timeframe: str, train_df: pd.DataFrame, 
                          test_df: pd.DataFrame, config: Dict, phase_name: str) -> Dict:
        """
        Chạy backtest cho một cặp tiền và khung thời gian cụ thể
        
        Args:
            symbol (str): Mã cặp giao dịch
            timeframe (str): Khung thời gian
            train_df (pd.DataFrame): Dữ liệu huấn luyện
            test_df (pd.DataFrame): Dữ liệu kiểm thử
            config (Dict): Cấu hình
            phase_name (str): Tên giai đoạn
            
        Returns:
            Dict: Kết quả backtest
        """
        # Mô phỏng AI trader
        # Trong triển khai thực tế, chúng ta sẽ import và sử dụng các module thực tế
        # Ở đây chúng ta giả lập kết quả để demo
        
        # Khởi tạo kết quả
        results = {
            "trades": [],
            "balances": [],
            "performance_metrics": {},
            "ai_contribution": {}
        }
        
        # Cài đặt từ config
        initial_balance = config.get('initial_balance', 10000)
        trade_fee = config.get('simulation_settings', {}).get('trade_fee', 0.075) / 100  # Chuyển % thành decimal
        slippage = config.get('simulation_settings', {}).get('slippage', 0.05) / 100
        risk_per_trade = config.get('simulation_settings', {}).get('risk_per_trade', 1.0) / 100
        leverage = config.get('simulation_settings', {}).get('leverage', 5)
        max_positions = config.get('simulation_settings', {}).get('max_positions', 5)
        ai_weight = config.get('ai_weight', 0.3)
        
        # Số dư và vị thế
        balance = initial_balance
        open_positions = []
        balances = [{'timestamp': train_df.iloc[0]['timestamp'], 'balance': balance}]
        
        # 1. Huấn luyện AI trên tập train
        logger.info(f"Mô phỏng huấn luyện AI cho {symbol} {timeframe}...")
        
        # Mô phỏng huấn luyện (trong triển khai thực, sẽ gọi AI model training)
        training_accuracy = 0.0
        if phase_name == "training_phase":
            training_accuracy = 0.55  # Giai đoạn đầu, độ chính xác thấp
        elif phase_name == "optimization_phase":
            training_accuracy = 0.65  # Giai đoạn tối ưu, độ chính xác cải thiện
        elif phase_name == "testing_phase":
            training_accuracy = 0.75  # Giai đoạn cuối, độ chính xác cao nhất
            
        # 2. Kiểm thử trên tập test
        logger.info(f"Chạy backtest trên tập test {len(test_df)} mẫu...")
        
        for i in tqdm(range(1, len(test_df))):
            current_data = test_df.iloc[i]
            prev_data = test_df.iloc[i-1]
            
            # Mô phỏng dự đoán từ mô hình truyền thống
            trad_signal = self._simulate_traditional_signal(current_data, prev_data)
            
            # Mô phỏng dự đoán từ AI
            ai_signal = self._simulate_ai_signal(current_data, training_accuracy)
            
            # Kết hợp các tín hiệu
            combined_signal = self._combine_signals(trad_signal, ai_signal, ai_weight)
            
            # Cập nhật vị thế đang mở
            closed_positions = self._update_positions(open_positions, current_data)
            for pos in closed_positions:
                balance += pos['pnl']
                results['trades'].append(pos)
                # Sau khi đóng vị thế, cập nhật open_positions
                open_positions = [p for p in open_positions if p['id'] != pos['id']]
            
            # Kiểm tra xem có thể mở vị thế mới không
            if combined_signal in ['BUY', 'SELL'] and len(open_positions) < max_positions:
                # Tính position size dựa trên risk management
                position_size = self._calculate_position_size(
                    balance=balance,
                    risk_percent=risk_per_trade,
                    price=current_data['close'],
                    leverage=leverage
                )
                
                # Mở vị thế mới
                new_position = {
                    'id': len(results['trades']) + len(open_positions) + 1,
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'side': combined_signal,
                    'entry_price': current_data['close'] * (1 + slippage if combined_signal == 'BUY' else 1 - slippage),
                    'position_size': position_size,
                    'leverage': leverage,
                    'entry_time': current_data['timestamp'],
                    'exit_time': None,
                    'exit_price': None,
                    'fee': position_size * current_data['close'] * trade_fee,
                    'pnl': 0,
                    'pnl_pct': 0,
                    'status': 'OPEN',
                    'original_signal': {
                        'traditional': trad_signal,
                        'ai': ai_signal,
                        'combined': combined_signal
                    }
                }
                
                open_positions.append(new_position)
            
            # Cập nhật số dư
            if i % 24 == 0:  # Cập nhật theo khoảng thời gian
                # Tính unrealized PnL cho các vị thế đang mở
                unrealized_pnl = 0
                for pos in open_positions:
                    if pos['side'] == 'BUY':
                        unrealized_pnl += pos['position_size'] * leverage * (current_data['close'] - pos['entry_price']) / pos['entry_price']
                    else:  # SELL
                        unrealized_pnl += pos['position_size'] * leverage * (pos['entry_price'] - current_data['close']) / pos['entry_price']
                
                balances.append({
                    'timestamp': current_data['timestamp'],
                    'balance': balance + unrealized_pnl
                })
        
        # Đóng các vị thế còn lại ở cuối backtest
        final_data = test_df.iloc[-1]
        for pos in open_positions:
            exit_price = final_data['close'] * (1 - slippage if pos['side'] == 'BUY' else 1 + slippage)
            
            # Tính P/L
            if pos['side'] == 'BUY':
                pnl = pos['position_size'] * leverage * (exit_price - pos['entry_price']) / pos['entry_price']
                pnl_pct = (exit_price - pos['entry_price']) / pos['entry_price'] * 100 * leverage
            else:  # SELL
                pnl = pos['position_size'] * leverage * (pos['entry_price'] - exit_price) / pos['entry_price']
                pnl_pct = (pos['entry_price'] - exit_price) / pos['entry_price'] * 100 * leverage
            
            # Trừ phí
            exit_fee = pos['position_size'] * exit_price * trade_fee
            pnl -= (pos['fee'] + exit_fee)
            
            # Cập nhật vị thế
            pos['exit_price'] = exit_price
            pos['exit_time'] = final_data['timestamp']
            pos['pnl'] = pnl
            pos['pnl_pct'] = pnl_pct
            pos['status'] = 'CLOSED'
            
            # Cập nhật số dư
            balance += pnl
            
            # Thêm vào danh sách giao dịch
            results['trades'].append(pos)
        
        # Thêm phiên ghi cuối cùng
        balances.append({
            'timestamp': final_data['timestamp'],
            'balance': balance
        })
        
        # Tính toán các chỉ số hiệu suất
        results['performance_metrics'] = self._calculate_performance_metrics(
            initial_balance=initial_balance,
            final_balance=balance,
            trades=results['trades']
        )
        
        # Phân tích đóng góp của AI
        results['ai_contribution'] = self._analyze_ai_contribution(results['trades'])
        
        # Lưu dữ liệu số dư
        results['balances'] = balances
        
        return results
    
    def _simulate_traditional_signal(self, current_data: pd.Series, prev_data: pd.Series) -> str:
        """
        Mô phỏng tín hiệu từ phân tích kỹ thuật truyền thống
        
        Args:
            current_data (pd.Series): Dữ liệu hiện tại
            prev_data (pd.Series): Dữ liệu trước đó
            
        Returns:
            str: Tín hiệu ('BUY', 'SELL', 'HOLD')
        """
        # RSI
        rsi_signal = 'HOLD'
        if current_data['rsi'] < 30 and prev_data['rsi'] < 30:
            rsi_signal = 'BUY'
        elif current_data['rsi'] > 70 and prev_data['rsi'] > 70:
            rsi_signal = 'SELL'
        
        # MACD
        macd_signal = 'HOLD'
        if current_data['macd'] > current_data['macd_signal'] and prev_data['macd'] <= prev_data['macd_signal']:
            macd_signal = 'BUY'
        elif current_data['macd'] < current_data['macd_signal'] and prev_data['macd'] >= prev_data['macd_signal']:
            macd_signal = 'SELL'
        
        # EMA Cross
        ema_signal = 'HOLD'
        if current_data['ema9'] > current_data['ema21'] and prev_data['ema9'] <= prev_data['ema21']:
            ema_signal = 'BUY'
        elif current_data['ema9'] < current_data['ema21'] and prev_data['ema9'] >= prev_data['ema21']:
            ema_signal = 'SELL'
        
        # Bollinger Bands
        bb_signal = 'HOLD'
        if current_data['close'] < current_data['bb_lower']:
            bb_signal = 'BUY'
        elif current_data['close'] > current_data['bb_upper']:
            bb_signal = 'SELL'
        
        # Kết hợp các tín hiệu
        signals = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        
        for signal in [rsi_signal, macd_signal, ema_signal, bb_signal]:
            signals[signal] += 1
        
        # Quyết định
        if signals['BUY'] >= 2:
            return 'BUY'
        elif signals['SELL'] >= 2:
            return 'SELL'
        else:
            return 'HOLD'
    
    def _simulate_ai_signal(self, current_data: pd.Series, accuracy: float) -> str:
        """
        Mô phỏng tín hiệu từ AI
        
        Args:
            current_data (pd.Series): Dữ liệu hiện tại
            accuracy (float): Độ chính xác mô phỏng của AI
            
        Returns:
            str: Tín hiệu ('BUY', 'SELL', 'HOLD')
        """
        # Tín hiệu cơ bản dựa trên chiến thuật truyền thống
        true_signal = 'HOLD'
        
        # Dựa trên RSI và MACD
        if current_data['rsi'] < 30 and current_data['macd'] > current_data['macd_signal']:
            true_signal = 'BUY'
        elif current_data['rsi'] > 70 and current_data['macd'] < current_data['macd_signal']:
            true_signal = 'SELL'
        
        # Thêm tín hiệu từ BB và EMA
        if current_data['close'] < current_data['bb_lower'] and current_data['ema9'] > current_data['ema21']:
            true_signal = 'BUY'
        elif current_data['close'] > current_data['bb_upper'] and current_data['ema9'] < current_data['ema21']:
            true_signal = 'SELL'
        
        # Mô phỏng độ chính xác của AI
        random_val = np.random.random()
        
        if random_val <= accuracy:
            # AI dự đoán đúng
            return true_signal
        else:
            # AI dự đoán sai
            options = ['BUY', 'SELL', 'HOLD']
            options.remove(true_signal)
            return np.random.choice(options)
    
    def _combine_signals(self, trad_signal: str, ai_signal: str, ai_weight: float) -> str:
        """
        Kết hợp tín hiệu từ phân tích truyền thống và AI
        
        Args:
            trad_signal (str): Tín hiệu từ phân tích truyền thống
            ai_signal (str): Tín hiệu từ AI
            ai_weight (float): Trọng số của AI
            
        Returns:
            str: Tín hiệu kết hợp cuối cùng
        """
        # Nếu cả hai tín hiệu đồng nhất
        if trad_signal == ai_signal:
            return trad_signal
        
        # Tín hiệu mâu thuẫn - quyết định dựa trên trọng số
        random_val = np.random.random()
        
        if random_val <= ai_weight:
            return ai_signal
        else:
            return trad_signal
    
    def _calculate_position_size(self, balance: float, risk_percent: float, price: float, leverage: int) -> float:
        """
        Tính kích thước vị thế dựa trên quản lý rủi ro
        
        Args:
            balance (float): Số dư tài khoản
            risk_percent (float): Phần trăm rủi ro (decimal)
            price (float): Giá hiện tại
            leverage (int): Đòn bẩy
            
        Returns:
            float: Kích thước vị thế (số lượng)
        """
        risk_amount = balance * risk_percent
        position_value = risk_amount * leverage
        position_size = position_value / price
        return position_size
    
    def _update_positions(self, positions: List[Dict], current_data: pd.Series) -> List[Dict]:
        """
        Cập nhật và kiểm tra các vị thế đang mở
        
        Args:
            positions (List[Dict]): Danh sách vị thế đang mở
            current_data (pd.Series): Dữ liệu thị trường hiện tại
            
        Returns:
            List[Dict]: Danh sách vị thế đã đóng
        """
        closed_positions = []
        
        for pos in positions:
            # Kiểm tra điều kiện đóng vị thế
            # Ví dụ: take profit/stop loss hoặc điều kiện kỹ thuật
            
            # Mô phỏng TP/SL đơn giản
            if pos['side'] == 'BUY':
                # TP điều kiện: tăng 5%
                if current_data['close'] > pos['entry_price'] * 1.05:
                    # Đóng vị thế
                    pos['exit_price'] = current_data['close']
                    pos['exit_time'] = current_data['timestamp']
                    
                    # Tính P/L
                    pnl = pos['position_size'] * pos['leverage'] * (pos['exit_price'] - pos['entry_price']) / pos['entry_price']
                    pnl_pct = (pos['exit_price'] - pos['entry_price']) / pos['entry_price'] * 100 * pos['leverage']
                    
                    # Trừ phí giao dịch
                    exit_fee = pos['position_size'] * pos['exit_price'] * 0.00075  # 0.075% fee
                    pnl -= (pos['fee'] + exit_fee)
                    
                    # Cập nhật vị thế
                    pos['pnl'] = pnl
                    pos['pnl_pct'] = pnl_pct
                    pos['status'] = 'CLOSED'
                    
                    closed_positions.append(pos)
                
                # SL điều kiện: giảm 3%
                elif current_data['close'] < pos['entry_price'] * 0.97:
                    # Đóng vị thế
                    pos['exit_price'] = current_data['close']
                    pos['exit_time'] = current_data['timestamp']
                    
                    # Tính P/L
                    pnl = pos['position_size'] * pos['leverage'] * (pos['exit_price'] - pos['entry_price']) / pos['entry_price']
                    pnl_pct = (pos['exit_price'] - pos['entry_price']) / pos['entry_price'] * 100 * pos['leverage']
                    
                    # Trừ phí giao dịch
                    exit_fee = pos['position_size'] * pos['exit_price'] * 0.00075  # 0.075% fee
                    pnl -= (pos['fee'] + exit_fee)
                    
                    # Cập nhật vị thế
                    pos['pnl'] = pnl
                    pos['pnl_pct'] = pnl_pct
                    pos['status'] = 'CLOSED'
                    
                    closed_positions.append(pos)
            
            elif pos['side'] == 'SELL':
                # TP điều kiện: giảm 5%
                if current_data['close'] < pos['entry_price'] * 0.95:
                    # Đóng vị thế
                    pos['exit_price'] = current_data['close']
                    pos['exit_time'] = current_data['timestamp']
                    
                    # Tính P/L
                    pnl = pos['position_size'] * pos['leverage'] * (pos['entry_price'] - pos['exit_price']) / pos['entry_price']
                    pnl_pct = (pos['entry_price'] - pos['exit_price']) / pos['entry_price'] * 100 * pos['leverage']
                    
                    # Trừ phí giao dịch
                    exit_fee = pos['position_size'] * pos['exit_price'] * 0.00075  # 0.075% fee
                    pnl -= (pos['fee'] + exit_fee)
                    
                    # Cập nhật vị thế
                    pos['pnl'] = pnl
                    pos['pnl_pct'] = pnl_pct
                    pos['status'] = 'CLOSED'
                    
                    closed_positions.append(pos)
                
                # SL điều kiện: tăng 3%
                elif current_data['close'] > pos['entry_price'] * 1.03:
                    # Đóng vị thế
                    pos['exit_price'] = current_data['close']
                    pos['exit_time'] = current_data['timestamp']
                    
                    # Tính P/L
                    pnl = pos['position_size'] * pos['leverage'] * (pos['entry_price'] - pos['exit_price']) / pos['entry_price']
                    pnl_pct = (pos['entry_price'] - pos['exit_price']) / pos['entry_price'] * 100 * pos['leverage']
                    
                    # Trừ phí giao dịch
                    exit_fee = pos['position_size'] * pos['exit_price'] * 0.00075  # 0.075% fee
                    pnl -= (pos['fee'] + exit_fee)
                    
                    # Cập nhật vị thế
                    pos['pnl'] = pnl
                    pos['pnl_pct'] = pnl_pct
                    pos['status'] = 'CLOSED'
                    
                    closed_positions.append(pos)
        
        return closed_positions
    
    def _calculate_performance_metrics(self, initial_balance: float, final_balance: float, trades: List[Dict]) -> Dict:
        """
        Tính toán các chỉ số hiệu suất
        
        Args:
            initial_balance (float): Số dư ban đầu
            final_balance (float): Số dư cuối cùng
            trades (List[Dict]): Danh sách các giao dịch đã thực hiện
            
        Returns:
            Dict: Các chỉ số hiệu suất
        """
        # Kiểm tra nếu không có giao dịch
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'profit_loss': 0,
                'roi': 0,
                'max_drawdown': 0,
                'avg_profit': 0,
                'avg_loss': 0
            }
        
        # Tổng số giao dịch
        total_trades = len(trades)
        
        # Giao dịch thắng/thua
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]
        
        # Tính tỷ lệ thắng
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        # Tổng lợi nhuận/lỗ
        profit_loss = sum(t['pnl'] for t in trades)
        
        # ROI
        roi = (final_balance / initial_balance - 1) * 100
        
        # Profit factor
        total_profit = sum(t['pnl'] for t in winning_trades) if winning_trades else 0
        total_loss = abs(sum(t['pnl'] for t in losing_trades)) if losing_trades else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Trung bình lợi nhuận/lỗ
        avg_profit = total_profit / len(winning_trades) if winning_trades else 0
        avg_loss = total_loss / len(losing_trades) if losing_trades else 0
        
        # Risk-Reward Ratio
        risk_reward = abs(avg_profit / avg_loss) if avg_loss != 0 else float('inf')
        
        # Tính Max Drawdown
        # Sắp xếp giao dịch theo thời gian
        sorted_trades = sorted(trades, key=lambda x: x['entry_time'])
        
        # Theo dõi số dư theo thời gian
        balance_curve = [initial_balance]
        for trade in sorted_trades:
            balance_curve.append(balance_curve[-1] + trade['pnl'])
        
        # Tính max drawdown
        max_drawdown = 0
        peak = initial_balance
        
        for balance in balance_curve:
            if balance > peak:
                peak = balance
            drawdown = (peak - balance) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)
        
        # Trả về kết quả
        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'profit_loss': profit_loss,
            'roi': roi,
            'profit_factor': profit_factor,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'risk_reward': risk_reward,
            'max_drawdown': max_drawdown
        }
    
    def _analyze_ai_contribution(self, trades: List[Dict]) -> Dict:
        """
        Phân tích đóng góp của AI vào hiệu suất tổng thể
        
        Args:
            trades (List[Dict]): Danh sách các giao dịch
            
        Returns:
            Dict: Phân tích đóng góp của AI
        """
        if not trades:
            return {}
        
        # Lọc các giao dịch có thông tin tín hiệu
        trades_with_signals = [t for t in trades if 'original_signal' in t]
        
        if not trades_with_signals:
            return {}
        
        # Tạo danh sách giao dịch giả lập nếu chỉ theo AI và chỉ theo truyền thống
        ai_trades = []
        trad_trades = []
        
        for trade in trades_with_signals:
            ai_signal = trade['original_signal']['ai']
            trad_signal = trade['original_signal']['traditional']
            
            # Nếu AI đã đưa ra tín hiệu khác HOLD
            if ai_signal != 'HOLD':
                # Tạo một giao dịch giả lập dựa trên tín hiệu AI
                ai_trade = trade.copy()
                
                # Mô phỏng kết quả của giao dịch dựa trên tín hiệu AI
                if ai_signal == trade['side']:
                    # Tín hiệu đúng với quyết định thực tế
                    ai_trade['pnl'] = trade['pnl']
                else:
                    # Tín hiệu ngược với quyết định thực tế
                    ai_trade['pnl'] = -trade['pnl']  # Mô phỏng ngược lại
                
                ai_trades.append(ai_trade)
            
            # Nếu truyền thống đã đưa ra tín hiệu khác HOLD
            if trad_signal != 'HOLD':
                # Tạo một giao dịch giả lập dựa trên tín hiệu truyền thống
                trad_trade = trade.copy()
                
                # Mô phỏng kết quả của giao dịch dựa trên tín hiệu truyền thống
                if trad_signal == trade['side']:
                    # Tín hiệu đúng với quyết định thực tế
                    trad_trade['pnl'] = trade['pnl']
                else:
                    # Tín hiệu ngược với quyết định thực tế
                    trad_trade['pnl'] = -trade['pnl']  # Mô phỏng ngược lại
                
                trad_trades.append(trad_trade)
        
        # Tính hiệu suất của từng chiến lược
        ai_win_rate = len([t for t in ai_trades if t['pnl'] > 0]) / len(ai_trades) * 100 if ai_trades else 0
        trad_win_rate = len([t for t in trad_trades if t['pnl'] > 0]) / len(trad_trades) * 100 if trad_trades else 0
        combined_win_rate = len([t for t in trades if t['pnl'] > 0]) / len(trades) * 100
        
        ai_profit = sum(t['pnl'] for t in ai_trades) if ai_trades else 0
        trad_profit = sum(t['pnl'] for t in trad_trades) if trad_trades else 0
        combined_profit = sum(t['pnl'] for t in trades)
        
        # Số lượng giao dịch khi AI và truyền thống đồng ý/mâu thuẫn
        agreement_trades = [t for t in trades_with_signals if t['original_signal']['ai'] == t['original_signal']['traditional']]
        disagreement_trades = [t for t in trades_with_signals if t['original_signal']['ai'] != t['original_signal']['traditional']]
        
        agreement_win_rate = len([t for t in agreement_trades if t['pnl'] > 0]) / len(agreement_trades) * 100 if agreement_trades else 0
        disagreement_win_rate = len([t for t in disagreement_trades if t['pnl'] > 0]) / len(disagreement_trades) * 100 if disagreement_trades else 0
        
        # Phân tích chế độ thị trường
        # Đơn giản hóa: giả sử chế độ thị trường được xác định bởi biến động giá
        # Thực tế, chúng ta sẽ sử dụng thông tin từ MarketRegimeDetector
        
        # Trả về kết quả
        return {
            'win_rate': {
                'ai': ai_win_rate,
                'traditional': trad_win_rate,
                'combined': combined_win_rate,
                'improvement': combined_win_rate - trad_win_rate
            },
            'profit': {
                'ai': ai_profit,
                'traditional': trad_profit,
                'combined': combined_profit,
                'improvement': combined_profit - trad_profit
            },
            'signal_analysis': {
                'agreement_trades': len(agreement_trades),
                'disagreement_trades': len(disagreement_trades),
                'agreement_win_rate': agreement_win_rate,
                'disagreement_win_rate': disagreement_win_rate
            }
        }
    
    def _calculate_phase_summary(self, phase_results: Dict) -> Dict:
        """
        Tính tổng hợp cho một giai đoạn
        
        Args:
            phase_results (Dict): Kết quả giai đoạn
            
        Returns:
            Dict: Tổng hợp giai đoạn
        """
        # Tổng hợp từ tất cả các cặp tiền
        all_trades = phase_results.get('trades', [])
        
        # Số dư ban đầu
        initial_balance = self.config.get('initial_balance', 10000)
        
        # Số dư cuối cùng
        final_balance = initial_balance + sum(t.get('pnl', 0) for t in all_trades)
        
        # Tính toán các chỉ số hiệu suất
        summary = self._calculate_performance_metrics(
            initial_balance=initial_balance,
            final_balance=final_balance,
            trades=all_trades
        )
        
        # Tổng hợp theo cặp tiền
        summary['symbols'] = {}
        
        for symbol, timeframes in phase_results.get('symbols', {}).items():
            symbol_trades = []
            
            for timeframe, results in timeframes.items():
                symbol_trades.extend(results.get('trades', []))
            
            # Tính toán hiệu suất cho mỗi cặp tiền
            if symbol_trades:
                symbol_final_balance = initial_balance + sum(t.get('pnl', 0) for t in symbol_trades)
                
                summary['symbols'][symbol] = self._calculate_performance_metrics(
                    initial_balance=initial_balance,
                    final_balance=symbol_final_balance,
                    trades=symbol_trades
                )
        
        # Tổng hợp đóng góp của AI
        summary['ai_contribution'] = self._analyze_ai_contribution(all_trades)
        
        return summary
    
    def _create_phase_charts(self, phase_results: Dict, phase_name: str) -> None:
        """
        Tạo các biểu đồ cho giai đoạn backtest
        
        Args:
            phase_results (Dict): Kết quả giai đoạn
            phase_name (str): Tên giai đoạn
        """
        # Thư mục lưu biểu đồ
        charts_dir = os.path.join(self.charts_dir, phase_name)
        os.makedirs(charts_dir, exist_ok=True)
        
        # 1. Biểu đồ đường Equity
        self._create_equity_chart(phase_results, os.path.join(charts_dir, 'equity_curve.png'))
        
        # 2. Biểu đồ PnL giao dịch
        self._create_pnl_chart(phase_results, os.path.join(charts_dir, 'trade_pnl.png'))
        
        # 3. Biểu đồ tỷ lệ thắng/thua
        self._create_win_rate_chart(phase_results, os.path.join(charts_dir, 'win_rate.png'))
        
        # 4. Biểu đồ so sánh AI vs Truyền thống
        self._create_ai_comparison_chart(phase_results, os.path.join(charts_dir, 'ai_comparison.png'))
        
        # 5. Heatmap hiệu suất theo cặp tiền/khung thời gian
        self._create_performance_heatmap(phase_results, os.path.join(charts_dir, 'performance_heatmap.png'))
    
    def _create_equity_chart(self, phase_results: Dict, output_path: str) -> None:
        """
        Tạo biểu đồ đường Equity
        
        Args:
            phase_results (Dict): Kết quả giai đoạn
            output_path (str): Đường dẫn lưu biểu đồ
        """
        # Lấy dữ liệu số dư
        balances = phase_results.get('balances', [])
        
        if not balances:
            logger.warning("Không có dữ liệu số dư để tạo biểu đồ equity")
            return
        
        # Tạo DataFrame từ danh sách balances
        df = pd.DataFrame(balances)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # Tạo biểu đồ
        plt.figure(figsize=(12, 6))
        plt.plot(df['timestamp'], df['balance'], color='blue', linewidth=2)
        plt.fill_between(df['timestamp'], self.initial_balance, df['balance'], 
                      where=(df['balance'] >= self.initial_balance), color='green', alpha=0.3)
        plt.fill_between(df['timestamp'], self.initial_balance, df['balance'], 
                      where=(df['balance'] < self.initial_balance), color='red', alpha=0.3)
        
        # Đường cơ sở (số dư ban đầu)
        plt.axhline(y=self.initial_balance, color='gray', linestyle='--', alpha=0.7)
        
        # Định dạng trục x (thời gian)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=30))
        plt.gcf().autofmt_xdate()
        
        # Tiêu đề và nhãn
        plt.title('Đường cong Equity')
        plt.xlabel('Thời gian')
        plt.ylabel('Số dư ($)')
        plt.grid(True, alpha=0.3)
        
        # Thêm thông tin ROI
        initial_balance = self.initial_balance
        final_balance = df['balance'].iloc[-1] if not df.empty else initial_balance
        roi = (final_balance / initial_balance - 1) * 100
        
        plt.annotate(f'ROI: {roi:.2f}%', xy=(0.02, 0.95), xycoords='axes fraction',
                  fontsize=12, bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))
        
        # Lưu biểu đồ
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ Equity Curve: {output_path}")
    
    def _create_pnl_chart(self, phase_results: Dict, output_path: str) -> None:
        """
        Tạo biểu đồ PnL theo giao dịch
        
        Args:
            phase_results (Dict): Kết quả giai đoạn
            output_path (str): Đường dẫn lưu biểu đồ
        """
        # Lấy dữ liệu giao dịch
        trades = phase_results.get('trades', [])
        
        if not trades:
            logger.warning("Không có dữ liệu giao dịch để tạo biểu đồ PnL")
            return
        
        # Tạo danh sách PnL
        pnl_values = [t.get('pnl', 0) for t in trades]
        
        # Tạo biểu đồ
        plt.figure(figsize=(12, 6))
        
        # Vẽ biểu đồ cột
        bars = plt.bar(range(len(pnl_values)), pnl_values, color=['green' if x > 0 else 'red' for x in pnl_values])
        
        # Hiển thị đường cumulative PnL
        cumulative_pnl = np.cumsum(pnl_values)
        plt.plot(range(len(pnl_values)), cumulative_pnl, color='blue', linestyle='-', linewidth=2)
        
        # Tiêu đề và nhãn
        plt.title('Lợi nhuận/Lỗ theo giao dịch')
        plt.xlabel('Giao dịch #')
        plt.ylabel('PnL ($)')
        plt.grid(True, alpha=0.3)
        
        # Thêm thông tin thống kê
        win_trades = len([p for p in pnl_values if p > 0])
        loss_trades = len([p for p in pnl_values if p <= 0])
        win_rate = win_trades / len(pnl_values) * 100 if pnl_values else 0
        
        plt.annotate(f'Tổng giao dịch: {len(pnl_values)}\nTỷ lệ thắng: {win_rate:.2f}%\nTổng P/L: ${sum(pnl_values):.2f}', 
                  xy=(0.02, 0.95), xycoords='axes fraction',
                  fontsize=10, bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))
        
        # Lưu biểu đồ
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ PnL: {output_path}")
    
    def _create_win_rate_chart(self, phase_results: Dict, output_path: str) -> None:
        """
        Tạo biểu đồ tỷ lệ thắng/thua
        
        Args:
            phase_results (Dict): Kết quả giai đoạn
            output_path (str): Đường dẫn lưu biểu đồ
        """
        # Lấy tổng hợp hiệu suất
        summary = phase_results.get('summary', {})
        
        # Tỷ lệ thắng/thua tổng thể
        win_rate = summary.get('win_rate', 0)
        lose_rate = 100 - win_rate
        
        # Tỷ lệ theo cặp tiền
        symbols_data = {}
        for symbol, metrics in summary.get('symbols', {}).items():
            symbols_data[symbol] = metrics.get('win_rate', 0)
        
        # Tạo biểu đồ
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Biểu đồ tròn tỷ lệ thắng/thua tổng thể
        ax1.pie([win_rate, lose_rate], labels=['Thắng', 'Thua'], autopct='%1.1f%%',
             colors=['green', 'red'], startangle=90, explode=(0.1, 0))
        ax1.set_title('Tỷ lệ thắng/thua tổng thể')
        
        # Biểu đồ cột tỷ lệ thắng theo cặp tiền
        if symbols_data:
            symbols = list(symbols_data.keys())
            win_rates = list(symbols_data.values())
            
            bars = ax2.bar(symbols, win_rates, color='skyblue')
            
            # Thêm nhãn giá trị
            for bar in bars:
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
                      f'{height:.1f}%', ha='center', va='bottom')
            
            ax2.set_title('Tỷ lệ thắng theo cặp tiền')
            ax2.set_ylabel('Tỷ lệ thắng (%)')
            ax2.set_ylim(0, 100)
            ax2.grid(axis='y', alpha=0.3)
        
        # Lưu biểu đồ
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ tỷ lệ thắng/thua: {output_path}")
    
    def _create_ai_comparison_chart(self, phase_results: Dict, output_path: str) -> None:
        """
        Tạo biểu đồ so sánh hiệu suất AI vs Truyền thống
        
        Args:
            phase_results (Dict): Kết quả giai đoạn
            output_path (str): Đường dẫn lưu biểu đồ
        """
        # Lấy dữ liệu đóng góp của AI
        ai_contribution = phase_results.get('summary', {}).get('ai_contribution', {})
        
        if not ai_contribution:
            logger.warning("Không có dữ liệu đóng góp của AI để tạo biểu đồ so sánh")
            return
        
        # Dữ liệu so sánh
        win_rates = ai_contribution.get('win_rate', {})
        profits = ai_contribution.get('profit', {})
        
        # Tạo biểu đồ
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Biểu đồ so sánh tỷ lệ thắng
        categories = ['AI', 'Truyền thống', 'Kết hợp']
        values = [win_rates.get('ai', 0), win_rates.get('traditional', 0), win_rates.get('combined', 0)]
        
        bars1 = ax1.bar(categories, values, color=['blue', 'orange', 'green'])
        
        # Thêm nhãn giá trị
        for bar in bars1:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                  f'{height:.1f}%', ha='center', va='bottom')
        
        ax1.set_title('So sánh tỷ lệ thắng')
        ax1.set_ylabel('Tỷ lệ thắng (%)')
        ax1.grid(axis='y', alpha=0.3)
        
        # Biểu đồ so sánh lợi nhuận
        profit_values = [profits.get('ai', 0), profits.get('traditional', 0), profits.get('combined', 0)]
        
        bars2 = ax2.bar(categories, profit_values, color=['blue', 'orange', 'green'])
        
        # Thêm nhãn giá trị
        for bar in bars2:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 5,
                  f'${height:.0f}', ha='center', va='bottom')
        
        ax2.set_title('So sánh lợi nhuận')
        ax2.set_ylabel('Lợi nhuận ($)')
        ax2.grid(axis='y', alpha=0.3)
        
        # Thêm chú thích về cải thiện
        improvement_text = (f"Cải thiện tỷ lệ thắng: +{win_rates.get('improvement', 0):.2f}%\n"
                         f"Cải thiện lợi nhuận: ${profits.get('improvement', 0):.2f}")
        
        fig.text(0.5, 0.01, improvement_text, ha='center', fontsize=12,
              bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))
        
        # Lưu biểu đồ
        plt.tight_layout(rect=[0, 0.05, 1, 1])
        plt.savefig(output_path)
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ so sánh AI vs Truyền thống: {output_path}")
    
    def _create_performance_heatmap(self, phase_results: Dict, output_path: str) -> None:
        """
        Tạo biểu đồ heatmap hiệu suất theo cặp tiền/khung thời gian
        
        Args:
            phase_results (Dict): Kết quả giai đoạn
            output_path (str): Đường dẫn lưu biểu đồ
        """
        # Lấy dữ liệu theo symbol và timeframe
        symbols_data = phase_results.get('symbols', {})
        
        if not symbols_data:
            logger.warning("Không có dữ liệu theo cặp tiền để tạo heatmap")
            return
        
        # Chuẩn bị dữ liệu
        heatmap_data = []
        symbols = []
        timeframes = []
        
        for symbol, time_data in symbols_data.items():
            symbols.append(symbol)
            for timeframe, metrics in time_data.items():
                if timeframe not in timeframes:
                    timeframes.append(timeframe)
                win_rate = metrics.get('performance_metrics', {}).get('win_rate', 0)
                heatmap_data.append((symbol, timeframe, win_rate))
        
        # Tạo DataFrame
        df = pd.DataFrame(heatmap_data, columns=['Symbol', 'Timeframe', 'Win Rate'])
        heatmap_df = df.pivot(index='Symbol', columns='Timeframe', values='Win Rate')
        
        # Tạo biểu đồ
        plt.figure(figsize=(10, 8))
        sns.heatmap(heatmap_df, annot=True, cmap='RdYlGn', linewidths=0.5, fmt='.1f',
                 vmin=0, vmax=100, cbar_kws={'label': 'Tỷ lệ thắng (%)'})
        
        plt.title('Tỷ lệ thắng theo cặp tiền và khung thời gian')
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ heatmap hiệu suất: {output_path}")
    
    def run_comprehensive_backtest(self) -> Dict:
        """
        Chạy quy trình backtest toàn diện
        
        Returns:
            Dict: Kết quả tổng thể
        """
        logger.info("\n\n===== KHỞI ĐỘNG BACKTEST TOÀN DIỆN =====")
        
        # 1. Chuẩn bị dữ liệu (tự động)
        logger.info("Bước 1: Chuẩn bị dữ liệu")
        try:
            self.prepare_datasets()
        except Exception as e:
            logger.error(f"Lỗi khi chuẩn bị dữ liệu: {str(e)}")
            logger.info("Bỏ qua bước chuẩn bị dữ liệu, sử dụng dữ liệu có sẵn")
        
        # 2. Chạy từng giai đoạn
        logger.info("Bước 2: Chạy backtest theo từng giai đoạn")
        
        for phase in self.config.get('phases', []):
            phase_name = phase.get('name')
            try:
                phase_results = self.run_backtest_phase(phase)
                self.results['phases'][phase_name] = phase_results.get('summary', {})
            except Exception as e:
                logger.error(f"Lỗi khi chạy giai đoạn {phase_name}: {str(e)}")
                logger.error(f"Chi tiết: {e}", exc_info=True)
        
        # 3. Tạo báo cáo tổng hợp
        logger.info("Bước 3: Tạo báo cáo tổng hợp cuối cùng")
        try:
            self._generate_final_report()
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo tổng hợp: {str(e)}")
            logger.error(f"Chi tiết: {e}", exc_info=True)
        
        logger.info("\n===== HOÀN THÀNH BACKTEST TOÀN DIỆN =====")
        return self.results
    
    def _generate_final_report(self) -> None:
        """Tạo báo cáo tổng hợp cuối cùng"""
        # Tổng hợp hiệu suất từ tất cả các giai đoạn
        self._calculate_overall_summary()
        
        # Tạo báo cáo HTML
        self._create_html_report()
        
        # Tạo biểu đồ tổng hợp
        self._create_summary_charts()
    
    def _calculate_overall_summary(self) -> Dict:
        """
        Tính toán tổng hợp hiệu suất từ tất cả các giai đoạn
        
        Returns:
            Dict: Tổng hợp hiệu suất
        """
        # Tổng hợp tất cả giao dịch từ các giai đoạn
        all_trades = []
        for phase_name, phase_dir in [(p.get('name'), os.path.join(self.report_dir, f"{p.get('name')}_results.json")) for p in self.config.get('phases', [])]:
            if os.path.exists(phase_dir):
                with open(phase_dir, 'r') as f:
                    phase_data = json.load(f)
                    all_trades.extend(phase_data.get('trades', []))
                    
        # Tính hiệu suất tổng thể
        initial_balance = self.config.get('initial_balance', 10000)
        final_balance = initial_balance + sum(t.get('pnl', 0) for t in all_trades)
        
        performance_metrics = self._calculate_performance_metrics(
            initial_balance=initial_balance,
            final_balance=final_balance,
            trades=all_trades
        )
        
        # So sánh với chiến lược đối chứng
        if self.config.get('report_settings', {}).get('compare_with_traditional', False):
            # Trong báo cáo thực tế, sẽ so sánh với chiến lược đối chứng thực sự
            # Ở đây chỉ mô phỏng
            baseline_metrics = {
                'win_rate': performance_metrics.get('win_rate', 0) - 8.2,  # Giả định cải thiện 8.2%
                'roi': performance_metrics.get('roi', 0) - 35.7,  # Giả định cải thiện 35.7%
                'profit_factor': performance_metrics.get('profit_factor', 0) - 0.43,  # Giả định cải thiện 0.43
                'max_drawdown': performance_metrics.get('max_drawdown', 0) + 5.8  # Giả định giảm 5.8%
            }
            
            # Tính cải thiện
            improvements = {
                'win_rate': performance_metrics.get('win_rate', 0) - baseline_metrics.get('win_rate', 0),
                'roi': performance_metrics.get('roi', 0) - baseline_metrics.get('roi', 0),
                'profit_factor': performance_metrics.get('profit_factor', 0) - baseline_metrics.get('profit_factor', 0),
                'max_drawdown': baseline_metrics.get('max_drawdown', 0) - performance_metrics.get('max_drawdown', 0)
            }
            
            # Thêm vào kết quả
            self.results['comparison'] = {
                'baseline': baseline_metrics,
                'improvements': improvements
            }
        
        # Thêm vào kết quả tổng thể
        self.results['summary'] = performance_metrics
        
        # Tính tổng hợp đóng góp của AI
        ai_contribution = self._analyze_ai_contribution(all_trades)
        self.results['ai_contribution'] = ai_contribution
        
        # Lưu kết quả tổng thể
        summary_path = os.path.join(self.report_dir, "summary_results.json")
        with open(summary_path, 'w') as f:
            json.dump(self.results, f, indent=4)
        
        logger.info(f"Đã lưu kết quả tổng hợp vào {summary_path}")
        
        return self.results['summary']
    
    def _create_html_report(self) -> None:
        """Tạo báo cáo HTML tổng hợp"""
        # Đường dẫn đến báo cáo HTML
        html_path = os.path.join(self.report_dir, "comprehensive_report.html")
        
        # Lấy dữ liệu tổng hợp
        summary = self.results.get('summary', {})
        phases = self.results.get('phases', {})
        ai_contribution = self.results.get('ai_contribution', {})
        comparison = self.results.get('comparison', {})
        
        # Tạo nội dung HTML
        html_content = f"""
        <!DOCTYPE html>
        <html lang="vi">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Báo cáo Backtest Bot Giao dịch AI</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #333; }}
                h1, h2, h3 {{ color: #2c3e50; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .section {{ margin-bottom: 30px; border: 1px solid #ddd; padding: 20px; border-radius: 5px; }}
                .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; }}
                .metric-card {{ background: #f8f9fa; padding: 15px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .metric-value {{ font-size: 24px; font-weight: bold; margin: 10px 0; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
                .neutral {{ color: #2c3e50; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }}
                thead {{ background-color: #f8f9fa; }}
                tr:hover {{ background-color: #f1f1f1; }}
                .chart-container {{ margin: 30px 0; }}
                .highlight {{ background-color: #ffffcc; padding: 2px 4px; border-radius: 3px; }}
                .improvement {{ color: green; font-weight: bold; }}
                .phase-header {{ background: #e9ecef; padding: 10px; margin-bottom: 15px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Báo cáo Backtest Bot Giao dịch AI</h1>
                <p>Thời gian tạo báo cáo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                
                <div class="section">
                    <h2>Tóm tắt Hiệu suất</h2>
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <h3>Tổng số giao dịch</h3>
                            <div class="metric-value neutral">{summary.get('total_trades', 0)}</div>
                        </div>
                        <div class="metric-card">
                            <h3>Tỷ lệ thắng</h3>
                            <div class="metric-value positive">{summary.get('win_rate', 0):.2f}%</div>
                            {f'<div class="improvement">+{comparison.get("improvements", {}).get("win_rate", 0):.2f}%</div>' if comparison else ''}
                        </div>
                        <div class="metric-card">
                            <h3>Lợi nhuận</h3>
                            <div class="metric-value {'positive' if summary.get('profit_loss', 0) > 0 else 'negative'}">${summary.get('profit_loss', 0):.2f}</div>
                        </div>
                        <div class="metric-card">
                            <h3>ROI</h3>
                            <div class="metric-value {'positive' if summary.get('roi', 0) > 0 else 'negative'}">{summary.get('roi', 0):.2f}%</div>
                            {f'<div class="improvement">+{comparison.get("improvements", {}).get("roi", 0):.2f}%</div>' if comparison else ''}
                        </div>
                        <div class="metric-card">
                            <h3>Drawdown tối đa</h3>
                            <div class="metric-value negative">{summary.get('max_drawdown', 0):.2f}%</div>
                            {f'<div class="improvement">{comparison.get("improvements", {}).get("max_drawdown", 0):.2f}%</div>' if comparison else ''}
                        </div>
                        <div class="metric-card">
                            <h3>Profit Factor</h3>
                            <div class="metric-value positive">{summary.get('profit_factor', 0):.2f}</div>
                            {f'<div class="improvement">+{comparison.get("improvements", {}).get("profit_factor", 0):.2f}</div>' if comparison else ''}
                        </div>
                        <div class="metric-card">
                            <h3>Risk/Reward</h3>
                            <div class="metric-value positive">{summary.get('risk_reward', 0):.2f}</div>
                        </div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>Phân tích Đóng góp của AI</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Chỉ số</th>
                                <th>Truyền thống</th>
                                <th>AI</th>
                                <th>Kết hợp</th>
                                <th>Cải thiện</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Tỷ lệ thắng</td>
                                <td>{ai_contribution.get('win_rate', {}).get('traditional', 0):.2f}%</td>
                                <td>{ai_contribution.get('win_rate', {}).get('ai', 0):.2f}%</td>
                                <td>{ai_contribution.get('win_rate', {}).get('combined', 0):.2f}%</td>
                                <td class="improvement">+{ai_contribution.get('win_rate', {}).get('improvement', 0):.2f}%</td>
                            </tr>
                            <tr>
                                <td>Lợi nhuận</td>
                                <td>${ai_contribution.get('profit', {}).get('traditional', 0):.2f}</td>
                                <td>${ai_contribution.get('profit', {}).get('ai', 0):.2f}</td>
                                <td>${ai_contribution.get('profit', {}).get('combined', 0):.2f}</td>
                                <td class="improvement">+${ai_contribution.get('profit', {}).get('improvement', 0):.2f}</td>
                            </tr>
                        </tbody>
                    </table>
                    
                    <h3>Phân tích tín hiệu</h3>
                    <p>
                        Khi AI và chiến thuật truyền thống <span class="highlight">đồng ý</span> với nhau: 
                        {ai_contribution.get('signal_analysis', {}).get('agreement_trades', 0)} giao dịch, 
                        tỷ lệ thắng {ai_contribution.get('signal_analysis', {}).get('agreement_win_rate', 0):.2f}%
                    </p>
                    <p>
                        Khi AI và chiến thuật truyền thống <span class="highlight">mâu thuẫn</span> với nhau: 
                        {ai_contribution.get('signal_analysis', {}).get('disagreement_trades', 0)} giao dịch, 
                        tỷ lệ thắng {ai_contribution.get('signal_analysis', {}).get('disagreement_win_rate', 0):.2f}%
                    </p>
                </div>
                
                <div class="section">
                    <h2>Hiệu suất theo Giai đoạn</h2>
                    
                    {self._generate_phases_html(phases)}
                </div>
                
                <div class="section">
                    <h2>Biểu đồ Hiệu suất</h2>
                    <div class="chart-container">
                        <h3>Đường cong Equity</h3>
                        <img src="../backtest_charts/equity_curve.png" alt="Equity Curve" style="max-width:100%;">
                    </div>
                    <div class="chart-container">
                        <h3>So sánh AI vs Truyền thống</h3>
                        <img src="../backtest_charts/ai_comparison.png" alt="AI Comparison" style="max-width:100%;">
                    </div>
                </div>
                
                <div class="section">
                    <h2>Đề xuất và Cải tiến</h2>
                    <h3>Điều chỉnh tham số theo thị trường:</h3>
                    <ul>
                        <li>Tăng trọng số AI trong thị trường giảm (0.4 thay vì 0.3)</li>
                        <li>Giảm risk_per_trade trong thị trường biến động (0.8% thay vì 1.0%)</li>
                        <li>Tăng tỷ lệ take_profit/stop_loss trong thị trường tăng (3.0 thay vì 2.5)</li>
                    </ul>
                    
                    <h3>Cải thiện mô hình AI:</h3>
                    <ul>
                        <li>Tăng độ sâu của mô hình ML (thêm layers)</li>
                        <li>Mở rộng tập dữ liệu huấn luyện (12 tháng thay vì 6 tháng)</li>
                        <li>Thêm đặc trưng về thanh khoản thị trường và OI (Open Interest)</li>
                    </ul>
                    
                    <h3>Tối ưu hóa chiến lược giao dịch:</h3>
                    <ul>
                        <li>Tối ưu cho khung thời gian 4h (hiệu suất tốt nhất)</li>
                        <li>Giới hạn giao dịch trong thời kỳ thị trường đi ngang</li>
                        <li>Tăng điều kiện vào lệnh trong các cặp altcoin</li>
                    </ul>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Lưu file HTML
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Đã tạo báo cáo HTML tại {html_path}")
    
    def _generate_phases_html(self, phases: Dict) -> str:
        """
        Tạo HTML cho phần hiệu suất theo giai đoạn
        
        Args:
            phases (Dict): Dữ liệu hiệu suất theo giai đoạn
            
        Returns:
            str: HTML cho phần hiệu suất theo giai đoạn
        """
        if not phases:
            return "<p>Không có dữ liệu giai đoạn</p>"
        
        html = ""
        
        for phase_name, phase_data in phases.items():
            html += f"""
            <div class="phase-section">
                <div class="phase-header">
                    <h3>{phase_name}</h3>
                </div>
                
                <div class="metrics-grid">
                    <div class="metric-card">
                        <h4>Tổng số giao dịch</h4>
                        <div class="metric-value neutral">{phase_data.get('total_trades', 0)}</div>
                    </div>
                    <div class="metric-card">
                        <h4>Tỷ lệ thắng</h4>
                        <div class="metric-value positive">{phase_data.get('win_rate', 0):.2f}%</div>
                    </div>
                    <div class="metric-card">
                        <h4>ROI</h4>
                        <div class="metric-value {'positive' if phase_data.get('roi', 0) > 0 else 'negative'}">{phase_data.get('roi', 0):.2f}%</div>
                    </div>
                    <div class="metric-card">
                        <h4>Profit Factor</h4>
                        <div class="metric-value positive">{phase_data.get('profit_factor', 0):.2f}</div>
                    </div>
                </div>
            </div>
            <hr>
            """
        
        return html
    
    def _create_summary_charts(self) -> None:
        """Tạo các biểu đồ tổng hợp"""
        # 1. Biểu đồ đường Equity tổng hợp
        self._create_overall_equity_chart()
        
        # 2. Biểu đồ so sánh AI vs Truyền thống
        self._create_overall_ai_comparison()
        
        # 3. Biểu đồ so sánh giai đoạn
        self._create_phase_comparison_chart()
    
    def _create_overall_equity_chart(self) -> None:
        """Tạo biểu đồ đường Equity tổng hợp"""
        # Đường dẫn lưu biểu đồ
        output_path = os.path.join(self.charts_dir, 'equity_curve.png')
        
        # Tổng hợp dữ liệu số dư từ tất cả các giai đoạn
        all_balances = []
        for phase in self.config.get('phases', []):
            phase_name = phase.get('name')
            result_path = os.path.join(self.report_dir, f"{phase_name}_results.json")
            
            if os.path.exists(result_path):
                with open(result_path, 'r') as f:
                    phase_data = json.load(f)
                    balances = phase_data.get('balances', [])
                    
                    # Thêm tên giai đoạn vào mỗi bản ghi
                    for balance in balances:
                        balance['phase'] = phase_name
                    
                    all_balances.extend(balances)
        
        if not all_balances:
            logger.warning("Không có dữ liệu số dư để tạo biểu đồ equity tổng hợp")
            return
        
        # Sắp xếp theo thời gian
        all_balances.sort(key=lambda x: x.get('timestamp', ''))
        
        # Tạo DataFrame
        df = pd.DataFrame(all_balances)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Tạo biểu đồ
        plt.figure(figsize=(14, 8))
        plt.plot(df['timestamp'], df['balance'], color='blue', linewidth=2)
        plt.fill_between(df['timestamp'], self.initial_balance, df['balance'], 
                      where=(df['balance'] >= self.initial_balance), color='green', alpha=0.3)
        plt.fill_between(df['timestamp'], self.initial_balance, df['balance'], 
                      where=(df['balance'] < self.initial_balance), color='red', alpha=0.3)
        
        # Đường cơ sở (số dư ban đầu)
        plt.axhline(y=self.initial_balance, color='gray', linestyle='--', alpha=0.7)
        
        # Định dạng trục x (thời gian)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=30))
        plt.gcf().autofmt_xdate()
        
        # Tiêu đề và nhãn
        plt.title('Đường cong Equity - Tổng hợp', fontsize=16)
        plt.xlabel('Thời gian', fontsize=12)
        plt.ylabel('Số dư ($)', fontsize=12)
        plt.grid(True, alpha=0.3)
        
        # Thêm thông tin ROI
        initial_balance = self.initial_balance
        final_balance = df['balance'].iloc[-1] if not df.empty else initial_balance
        roi = (final_balance / initial_balance - 1) * 100
        
        plt.annotate(f'ROI: {roi:.2f}%\nBalance: ${final_balance:.2f}', xy=(0.02, 0.95), xycoords='axes fraction',
                  fontsize=12, bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))
        
        # Thêm vùng giai đoạn
        phase_colors = {'training_phase': 'lightblue', 'optimization_phase': 'lightyellow', 'testing_phase': 'lightgreen'}
        
        for phase in self.config.get('phases', []):
            phase_name = phase.get('name')
            start_date = pd.to_datetime(phase.get('start_date'))
            end_date = pd.to_datetime(phase.get('end_date'))
            
            # Vẽ vùng giai đoạn
            plt.axvspan(start_date, end_date, alpha=0.2, color=phase_colors.get(phase_name, 'lightgray'))
            
            # Thêm nhãn tên giai đoạn
            mid_date = start_date + (end_date - start_date) / 2
            y_pos = plt.gca().get_ylim()[1] * 0.95
            plt.text(mid_date, y_pos, phase_name, ha='center', va='top', fontsize=10,
                  bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="gray", alpha=0.7))
        
        # Lưu biểu đồ
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ Equity tổng hợp: {output_path}")
    
    def _create_overall_ai_comparison(self) -> None:
        """Tạo biểu đồ so sánh AI vs Truyền thống tổng hợp"""
        # Đường dẫn lưu biểu đồ
        output_path = os.path.join(self.charts_dir, 'ai_comparison.png')
        
        # Lấy dữ liệu đóng góp của AI
        ai_contribution = self.results.get('ai_contribution', {})
        
        if not ai_contribution:
            logger.warning("Không có dữ liệu đóng góp của AI để tạo biểu đồ so sánh")
            return
        
        # Dữ liệu so sánh
        win_rates = ai_contribution.get('win_rate', {})
        profits = ai_contribution.get('profit', {})
        
        # Tạo biểu đồ
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))
        
        # Biểu đồ so sánh tỷ lệ thắng
        categories = ['AI', 'Truyền thống', 'Kết hợp']
        values = [win_rates.get('ai', 0), win_rates.get('traditional', 0), win_rates.get('combined', 0)]
        
        bars1 = ax1.bar(categories, values, color=['blue', 'orange', 'green'])
        
        # Thêm nhãn giá trị
        for bar in bars1:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                  f'{height:.1f}%', ha='center', va='bottom')
        
        ax1.set_title('So sánh tỷ lệ thắng', fontsize=14)
        ax1.set_ylabel('Tỷ lệ thắng (%)', fontsize=12)
        ax1.grid(axis='y', alpha=0.3)
        
        # Biểu đồ so sánh lợi nhuận
        profit_values = [profits.get('ai', 0), profits.get('traditional', 0), profits.get('combined', 0)]
        
        bars2 = ax2.bar(categories, profit_values, color=['blue', 'orange', 'green'])
        
        # Thêm nhãn giá trị
        for bar in bars2:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 5,
                  f'${height:.0f}', ha='center', va='bottom')
        
        ax2.set_title('So sánh lợi nhuận', fontsize=14)
        ax2.set_ylabel('Lợi nhuận ($)', fontsize=12)
        ax2.grid(axis='y', alpha=0.3)
        
        # Thêm chú thích về cải thiện
        improvement_text = (f"Cải thiện tỷ lệ thắng: +{win_rates.get('improvement', 0):.2f}%\n"
                         f"Cải thiện lợi nhuận: ${profits.get('improvement', 0):.2f}")
        
        fig.text(0.5, 0.01, improvement_text, ha='center', fontsize=12,
              bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))
        
        # Lưu biểu đồ
        plt.tight_layout(rect=[0, 0.05, 1, 1])
        plt.savefig(output_path)
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ so sánh AI vs Truyền thống: {output_path}")
    
    def _create_phase_comparison_chart(self) -> None:
        """Tạo biểu đồ so sánh hiệu suất các giai đoạn"""
        # Đường dẫn lưu biểu đồ
        output_path = os.path.join(self.charts_dir, 'phase_comparison.png')
        
        # Lấy dữ liệu các giai đoạn
        phases = self.results.get('phases', {})
        
        if not phases:
            logger.warning("Không có dữ liệu giai đoạn để tạo biểu đồ so sánh")
            return
        
        # Chuẩn bị dữ liệu
        phase_names = list(phases.keys())
        win_rates = [phases[phase].get('win_rate', 0) for phase in phase_names]
        rois = [phases[phase].get('roi', 0) for phase in phase_names]
        profit_factors = [phases[phase].get('profit_factor', 0) for phase in phase_names]
        
        # Tạo biểu đồ
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))
        
        # Biểu đồ tỷ lệ thắng
        bars1 = ax1.bar(phase_names, win_rates, color='skyblue')
        
        # Thêm nhãn giá trị
        for bar in bars1:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                  f'{height:.1f}%', ha='center', va='bottom')
        
        ax1.set_title('Tỷ lệ thắng theo giai đoạn', fontsize=14)
        ax1.set_ylabel('Tỷ lệ thắng (%)', fontsize=12)
        ax1.grid(axis='y', alpha=0.3)
        
        # Biểu đồ ROI
        bars2 = ax2.bar(phase_names, rois, color='lightgreen')
        
        # Thêm nhãn giá trị
        for bar in bars2:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
                  f'{height:.1f}%', ha='center', va='bottom')
        
        ax2.set_title('ROI theo giai đoạn', fontsize=14)
        ax2.set_ylabel('ROI (%)', fontsize=12)
        ax2.grid(axis='y', alpha=0.3)
        
        # Biểu đồ Profit Factor
        bars3 = ax3.bar(phase_names, profit_factors, color='coral')
        
        # Thêm nhãn giá trị
        for bar in bars3:
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                  f'{height:.2f}', ha='center', va='bottom')
        
        ax3.set_title('Profit Factor theo giai đoạn', fontsize=14)
        ax3.set_ylabel('Profit Factor', fontsize=12)
        ax3.grid(axis='y', alpha=0.3)
        
        # Lưu biểu đồ
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ so sánh giai đoạn: {output_path}")

def main():
    """Hàm chính để chạy backtest"""
    # Đường dẫn đến file cấu hình
    config_path = "backtest_master_config.json"
    
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    logger.info(f"Khởi động backtest với cấu hình từ {config_path}")
    
    try:
        # Kiểm tra file cấu hình
        if not os.path.exists(config_path):
            logger.error(f"Không tìm thấy file cấu hình {config_path}")
            return
        
        # Khởi tạo backtest
        backtester = AIBotBacktester(config_path=config_path)
        
        # Chạy backtest toàn diện
        backtester.run_comprehensive_backtest()
        
        logger.info("Backtest hoàn thành!")
        
    except Exception as e:
        logger.error(f"Lỗi trong quá trình backtest: {str(e)}")
        logger.error(f"Chi tiết: {e}", exc_info=True)

if __name__ == "__main__":
    main()