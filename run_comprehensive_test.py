"""
Script chạy kiểm thử toàn diện với tất cả chiến lược

Script này thực hiện:
1. Tải dữ liệu Binance cho 9 đồng coin trong các khoảng thời gian 1,3,6 tháng
2. Chạy backtest cho tất cả chiến lược trên tất cả dữ liệu
3. Áp dụng học máy để tối ưu hóa tham số chiến lược
4. Tạo báo cáo chi tiết về hiệu suất và so sánh
"""

import os
import sys
import time
import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Any, Optional, Union

# Thêm thư mục gốc vào đường dẫn
sys.path.append('.')

# Import các module cần thiết
from binance_api import BinanceAPI
from data_processor import DataProcessor
from market_regime_detector import MarketRegimeDetector
from strategy_factory import StrategyFactory
from position_sizing import create_position_sizer
from risk_manager import RiskManager
from order_execution_factory import OrderExecutionFactory
from adapter_pattern_optimizer import AdaptiveParameterTuner

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('comprehensive_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("comprehensive_test")

# Danh sách các coin cần test
COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT", 
         "DOTUSDT", "XRPUSDT", "AVAXUSDT", "MATICUSDT"]

# Danh sách các khung thời gian
TIMEFRAMES = ["1h", "4h", "1d"]

# Danh sách các chiến lược
STRATEGIES = ["rsi", "macd", "ema_cross", "bbands", "composite", "auto"]

# Thời gian kiểm thử
PERIODS = {
    "1m": 30,   # 1 tháng: 30 ngày
    "3m": 90,   # 3 tháng: 90 ngày
    "6m": 180,  # 6 tháng: 180 ngày
}

class ComprehensiveTester:
    """Lớp kiểm thử toàn diện"""
    
    def __init__(self, api_key: str = None, api_secret: str = None, 
               use_testnet: bool = True, data_dir: str = 'test_data',
               results_dir: str = 'test_results', charts_dir: str = 'test_charts'):
        """
        Khởi tạo tester
        
        Args:
            api_key (str, optional): API Key Binance
            api_secret (str, optional): API Secret Binance
            use_testnet (bool): Sử dụng testnet hay mainnet
            data_dir (str): Thư mục lưu dữ liệu
            results_dir (str): Thư mục lưu kết quả
            charts_dir (str): Thư mục lưu biểu đồ
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.use_testnet = use_testnet
        
        # Tạo các thư mục nếu chưa tồn tại
        self.data_dir = data_dir
        self.results_dir = results_dir
        self.charts_dir = charts_dir
        
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(results_dir, exist_ok=True)
        os.makedirs(charts_dir, exist_ok=True)
        
        # Khởi tạo các thành phần
        self.binance_api = self._init_binance_api()
        self.data_processor = DataProcessor(binance_api=self.binance_api)
        self.market_regime_detector = MarketRegimeDetector()
        
        # Lưu kết quả và dữ liệu
        self.data_cache = {}
        self.results = {}
        self.ml_models = {}
        
    def _init_binance_api(self) -> BinanceAPI:
        """
        Khởi tạo Binance API
        
        Returns:
            BinanceAPI: Đối tượng Binance API
        """
        try:
            # Lấy API key và secret từ biến môi trường nếu không được cung cấp
            if not self.api_key:
                self.api_key = os.environ.get('BINANCE_API_KEY')
            if not self.api_secret:
                self.api_secret = os.environ.get('BINANCE_API_SECRET')
                
            return BinanceAPI(
                api_key=self.api_key,
                api_secret=self.api_secret,
                testnet=self.use_testnet
            )
        except Exception as e:
            logger.error(f"Không thể khởi tạo Binance API: {str(e)}")
            return None
    
    def fetch_data(self, coins: List[str] = None, timeframes: List[str] = None, 
                 periods: Dict[str, int] = None) -> bool:
        """
        Tải dữ liệu từ Binance
        
        Args:
            coins (List[str], optional): Danh sách coin, mặc định dùng COINS
            timeframes (List[str], optional): Danh sách khung thời gian, mặc định dùng TIMEFRAMES
            periods (Dict[str, int], optional): Thời gian kiểm thử, mặc định dùng PERIODS
            
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        if not coins:
            coins = COINS
        if not timeframes:
            timeframes = TIMEFRAMES
        if not periods:
            periods = PERIODS
            
        logger.info(f"Tải dữ liệu cho {len(coins)} coins, {len(timeframes)} khung thời gian, {len(periods)} khoảng thời gian")
        
        success_count = 0
        total_count = len(coins) * len(timeframes) * len(periods)
        
        for coin in coins:
            for timeframe in timeframes:
                for period_name, days in periods.items():
                    try:
                        # Tính thời gian bắt đầu và kết thúc
                        end_time = datetime.now()
                        start_time = end_time - timedelta(days=days)
                        
                        # Tải dữ liệu
                        df = self.data_processor.download_historical_data(
                            symbol=coin,
                            interval=timeframe,
                            start_time=start_time.strftime("%Y-%m-%d"),
                            end_time=end_time.strftime("%Y-%m-%d"),
                            output_dir=self.data_dir
                        )
                        
                        if df is not None and not df.empty:
                            # Thêm vào cache
                            key = f"{coin}_{timeframe}_{period_name}"
                            self.data_cache[key] = df
                            success_count += 1
                            
                            logger.info(f"Đã tải dữ liệu {key}: {len(df)} dòng")
                        else:
                            logger.warning(f"Không tải được dữ liệu {coin}_{timeframe}_{period_name}")
                            
                    except Exception as e:
                        logger.error(f"Lỗi khi tải dữ liệu {coin}_{timeframe}_{period_name}: {str(e)}")
                        
        logger.info(f"Đã tải {success_count}/{total_count} bộ dữ liệu")
        return success_count > 0
    
    def run_backtest(self, coins: List[str] = None, timeframes: List[str] = None, 
                   periods: Dict[str, int] = None, strategies: List[str] = None) -> bool:
        """
        Chạy backtest cho tất cả chiến lược và dữ liệu
        
        Args:
            coins (List[str], optional): Danh sách coin, mặc định dùng COINS
            timeframes (List[str], optional): Danh sách khung thời gian, mặc định dùng TIMEFRAMES
            periods (Dict[str, int], optional): Thời gian kiểm thử, mặc định dùng PERIODS
            strategies (List[str], optional): Danh sách chiến lược, mặc định dùng STRATEGIES
            
        Returns:
            bool: True nếu thành công, False nếu không
        """
        if not coins:
            coins = COINS
        if not timeframes:
            timeframes = TIMEFRAMES
        if not periods:
            periods = PERIODS
        if not strategies:
            strategies = STRATEGIES
            
        logger.info(f"Chạy backtest cho {len(coins)} coins, {len(timeframes)} khung thời gian, "
                 f"{len(periods)} khoảng thời gian, {len(strategies)} chiến lược")
        
        success_count = 0
        total_count = len(coins) * len(timeframes) * len(periods) * len(strategies)
        
        for coin in coins:
            for timeframe in timeframes:
                for period_name, days in periods.items():
                    # Lấy dữ liệu từ cache
                    key = f"{coin}_{timeframe}_{period_name}"
                    if key not in self.data_cache:
                        logger.warning(f"Không có dữ liệu {key} trong cache, bỏ qua")
                        continue
                        
                    df = self.data_cache[key]
                    
                    # Phát hiện chế độ thị trường
                    market_regime = self.market_regime_detector.detect_regime(df)
                    logger.info(f"Chế độ thị trường cho {key}: {market_regime}")
                    
                    for strategy_name in strategies:
                        try:
                            # Tạo chiến lược
                            strategy = StrategyFactory.create_strategy(strategy_name)
                            
                            if strategy is None:
                                logger.warning(f"Không thể tạo chiến lược {strategy_name}, bỏ qua")
                                continue
                                
                            # Điều chỉnh tham số theo chế độ thị trường
                            strategy.adapt_to_market_regime(market_regime)
                            
                            # Thiết lập quản lý rủi ro
                            risk_manager = RiskManager(
                                account_balance=10000.0,
                                stop_loss_pct=2.0,
                                take_profit_pct=6.0,
                                trailing_stop=True,
                                risk_method='volatility_based'
                            )
                            
                            # Thiết lập position sizer
                            position_sizer = create_position_sizer(
                                'dynamic',
                                account_balance=10000.0,
                                risk_percentage=1.0,
                                atr_multiplier=2.0
                            )
                            
                            # Chạy backtest
                            result = self._run_single_backtest(
                                df=df,
                                strategy=strategy,
                                risk_manager=risk_manager,
                                position_sizer=position_sizer,
                                market_regime=market_regime,
                                symbol=coin,
                                timeframe=timeframe
                            )
                            
                            # Lưu kết quả
                            result_key = f"{key}_{strategy_name}"
                            self.results[result_key] = result
                            
                            # Lưu kết quả vào file
                            self._save_result(result, result_key)
                            
                            # Tạo biểu đồ
                            self._create_chart(result, result_key)
                            
                            success_count += 1
                            
                            logger.info(f"Đã chạy backtest {result_key}: Lợi nhuận: {result['total_profit']:.2f}%, "
                                     f"Win rate: {result['win_rate']:.2f}%, Profit factor: {result['profit_factor']:.2f}")
                                     
                        except Exception as e:
                            logger.error(f"Lỗi khi chạy backtest {key}_{strategy_name}: {str(e)}")
                            
        logger.info(f"Đã chạy {success_count}/{total_count} backtest")
        return success_count > 0
    
    def _run_single_backtest(self, df: pd.DataFrame, strategy: Any, risk_manager: RiskManager,
                          position_sizer: Any, market_regime: str, symbol: str, 
                          timeframe: str) -> Dict:
        """
        Chạy backtest đơn lẻ
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu
            strategy (Any): Chiến lược giao dịch
            risk_manager (RiskManager): Quản lý rủi ro
            position_sizer (Any): Position sizer
            market_regime (str): Chế độ thị trường
            symbol (str): Symbol giao dịch
            timeframe (str): Khung thời gian
            
        Returns:
            Dict: Kết quả backtest
        """
        # Reset trạng thái
        initial_balance = 10000.0
        risk_manager = RiskManager(account_balance=initial_balance)
        current_balance = initial_balance
        
        trades = []
        equity_curve = [initial_balance]
        positions = []
        
        # Duyệt từng nến dữ liệu
        for i in range(50, len(df)):  # Bỏ qua 50 nến đầu để đảm bảo đủ dữ liệu cho các chỉ báo
            current_data = df.iloc[:i+1]
            current_row = df.iloc[i]
            
            # Tính ATR cho volatility
            atr = current_row.get('atr', None)
            
            # Lấy tín hiệu từ chiến lược
            signal_result = strategy.generate_signal(current_data)
            
            # Xử lý kết quả tín hiệu
            if isinstance(signal_result, dict):
                signal = signal_result.get('signal', 0)
                reason = signal_result.get('reason', '')
            else:
                signal = signal_result
                reason = ''
                
            # Xử lý các vị thế đang mở
            current_time = current_row.name if isinstance(current_row.name, datetime) else datetime.now()
            current_price = current_row['close']
            
            # Kiểm tra giá hiện tại với các stop loss và take profit
            price_dict = {trade_id: current_price for trade_id in range(1, len(positions) + 1)}
            closed_trades = risk_manager.update_trades(price_dict, current_time)
            
            # Cập nhật trades list
            for trade in closed_trades:
                trades.append(trade)
                
                # Cập nhật balance
                current_balance += trade.get('profit', 0)
                
                # Cập nhật position_sizer
                position_sizer.update_balance(current_balance)
                trade_result = {'profit': trade.get('profit', 0), 'profit_pct': trade.get('profit_pct', 0)}
                position_sizer.update_trade_result(trade_result)
                
            # Lọc ra các vị thế vẫn đang mở
            positions = [p for p in positions if p['id'] not in [t['id'] for t in closed_trades]]
            
            # Xử lý tín hiệu mới
            if signal != 0:
                # Kiểm tra nếu có thể thực hiện giao dịch
                execute_trade = True
                
                # Không giao dịch nếu đã có vị thế cùng chiều
                for pos in positions:
                    if (signal > 0 and pos['side'] == 'BUY') or (signal < 0 and pos['side'] == 'SELL'):
                        execute_trade = False
                        break
                
                if execute_trade and risk_manager.should_execute_trade(symbol, 'BUY' if signal > 0 else 'SELL', current_balance):
                    # Tính toán stop loss và take profit
                    side = 'BUY' if signal > 0 else 'SELL'
                    stop_loss, take_profit = risk_manager.calculate_stop_levels(current_price, side, 
                                                                            current_data, None, current_balance)
                    
                    # Tính toán kích thước vị thế
                    position_size = position_sizer.calculate_position_size(
                        current_price=current_price,
                        account_balance=current_balance,
                        volatility=atr,
                        entry_price=current_price,
                        stop_loss_price=stop_loss
                    )
                    
                    # Mở vị thế mới
                    new_position = risk_manager.open_trade(
                        symbol=symbol,
                        side=side,
                        entry_price=current_price,
                        quantity=position_size / current_price,  # Chuyển USD sang số lượng coin
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        entry_time=current_time
                    )
                    
                    if new_position:
                        positions.append(new_position)
                        
            # Cập nhật equity curve
            equity_curve.append(current_balance + sum([(current_price - p['entry_price']) * p['quantity'] 
                                                if p['side'] == 'BUY' else 
                                                (p['entry_price'] - current_price) * p['quantity'] 
                                                for p in positions]))
                                                
        # Đóng các vị thế còn lại ở cuối kỳ backtest
        if positions:
            last_price = df.iloc[-1]['close']
            last_time = df.iloc[-1].name if isinstance(df.iloc[-1].name, datetime) else datetime.now()
            
            for position in positions:
                closed_trade = risk_manager.close_trade(
                    trade_id=position['id'],
                    exit_price=last_price,
                    exit_time=last_time,
                    exit_reason='end_of_backtest'
                )
                
                if closed_trade:
                    trades.append(closed_trade)
                    
        # Tính toán các chỉ số hiệu suất
        performance = risk_manager.get_performance_metrics()
        
        # Thêm thông tin bổ sung
        performance.update({
            'symbol': symbol,
            'timeframe': timeframe,
            'strategy': strategy.get_name(),
            'market_regime': market_regime,
            'initial_balance': initial_balance,
            'final_balance': current_balance,
            'trades': trades,
            'equity_curve': equity_curve,
            'total_trades': len(trades),
            'parameters': strategy.get_parameters()
        })
        
        return performance
    
    def _save_result(self, result: Dict, key: str) -> None:
        """
        Lưu kết quả vào file
        
        Args:
            result (Dict): Kết quả backtest
            key (str): Khóa xác định kết quả
        """
        try:
            # Tạo bản sao để tránh thay đổi dữ liệu gốc
            result_copy = result.copy()
            
            # Chuyển đổi các kiểu dữ liệu không thể serialize
            if 'trades' in result_copy:
                # Chuyển datetime thành string
                for trade in result_copy['trades']:
                    if 'entry_time' in trade and isinstance(trade['entry_time'], datetime):
                        trade['entry_time'] = trade['entry_time'].isoformat()
                    if 'exit_time' in trade and isinstance(trade['exit_time'], datetime):
                        trade['exit_time'] = trade['exit_time'].isoformat()
            
            # Lưu vào file json
            file_path = os.path.join(self.results_dir, f"{key}.json")
            with open(file_path, 'w') as f:
                json.dump(result_copy, f, indent=2)
                
            # Lưu các giao dịch vào file csv
            if 'trades' in result_copy and result_copy['trades']:
                trades_df = pd.DataFrame(result_copy['trades'])
                trades_path = os.path.join(self.results_dir, f"{key}_trades.csv")
                trades_df.to_csv(trades_path, index=False)
                
            logger.info(f"Đã lưu kết quả vào {file_path}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu kết quả {key}: {str(e)}")
    
    def _create_chart(self, result: Dict, key: str) -> None:
        """
        Tạo biểu đồ từ kết quả
        
        Args:
            result (Dict): Kết quả backtest
            key (str): Khóa xác định kết quả
        """
        try:
            # Tạo biểu đồ equity curve
            if 'equity_curve' in result and result['equity_curve']:
                plt.figure(figsize=(12, 6))
                plt.plot(result['equity_curve'])
                plt.title(f"Equity Curve - {key}")
                plt.xlabel('Candles')
                plt.ylabel('Balance')
                plt.grid(True)
                
                # Lưu biểu đồ
                chart_path = os.path.join(self.charts_dir, f"{key}_equity.png")
                plt.savefig(chart_path)
                plt.close()
                
                logger.info(f"Đã tạo biểu đồ equity curve: {chart_path}")
                
            # Tạo biểu đồ trades
            if 'trades' in result and result['trades']:
                trades = result['trades']
                
                # Tạo DataFrame từ trades
                try:
                    trades_df = pd.DataFrame(trades)
                    
                    # Tạo biểu đồ win/loss
                    plt.figure(figsize=(10, 6))
                    trades_df['profit_color'] = trades_df['profit'].apply(lambda x: 'green' if x > 0 else 'red')
                    plt.bar(range(len(trades_df)), trades_df['profit'], color=trades_df['profit_color'])
                    plt.title(f"Trades Profit/Loss - {key}")
                    plt.xlabel('Trade #')
                    plt.ylabel('Profit/Loss')
                    plt.grid(True)
                    
                    # Lưu biểu đồ
                    trades_chart_path = os.path.join(self.charts_dir, f"{key}_trades.png")
                    plt.savefig(trades_chart_path)
                    plt.close()
                    
                    logger.info(f"Đã tạo biểu đồ trades: {trades_chart_path}")
                except Exception as e:
                    logger.error(f"Lỗi khi tạo biểu đồ trades: {str(e)}")
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ {key}: {str(e)}")
    
    def apply_machine_learning(self) -> bool:
        """
        Áp dụng học máy để tối ưu hóa tham số chiến lược
        
        Returns:
            bool: True nếu thành công, False nếu không
        """
        logger.info("Áp dụng học máy để tối ưu hóa tham số chiến lược")
        
        # Kiểm tra nếu không có kết quả backtest
        if not self.results:
            logger.warning("Không có kết quả backtest để áp dụng học máy")
            return False
            
        try:
            # Tạo bộ tối ưu hóa tham số
            parameter_tuner = AdaptiveParameterTuner()
            
            # Duyệt qua kết quả backtest
            for key, result in self.results.items():
                try:
                    # Phân tích key để lấy thông tin
                    parts = key.split('_')
                    if len(parts) < 4:
                        continue
                        
                    symbol = parts[0]
                    timeframe = parts[1]
                    period = parts[2]
                    strategy_name = '_'.join(parts[3:])
                    
                    # Lấy thông tin thị trường
                    market_regime = result.get('market_regime', 'unknown')
                    
                    # Lấy thông tin hiệu suất
                    performance_data = {
                        'win_rate': result.get('win_rate', 0),
                        'profit_factor': result.get('profit_factor', 0),
                        'expectancy': result.get('expectancy', 0),
                        'sharpe_ratio': result.get('sharpe_ratio', 0),
                        'max_drawdown': result.get('max_drawdown', 0),
                        'total_profit': result.get('total_profit_pct', 0)
                    }
                    
                    # Lấy tham số hiện tại
                    current_parameters = result.get('parameters', {})
                    
                    # Cập nhật điều kiện thị trường
                    market_data = {
                        'market_regime': market_regime,
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'period': period
                    }
                    
                    # Cập nhật dữ liệu vào parameter tuner
                    parameter_tuner.update_market_conditions(market_data)
                    parameter_tuner.update_performance_metrics(performance_data)
                    
                    # Tối ưu hóa tham số
                    optimal_params = parameter_tuner.optimize_parameters(
                        optimization_method='bayesian',
                        target_metric='composite',
                        max_iterations=50,
                        use_ml_prediction=True
                    )
                    
                    # Lưu tham số tối ưu
                    ml_key = f"{symbol}_{timeframe}_{strategy_name}"
                    self.ml_models[ml_key] = {
                        'optimal_parameters': optimal_params,
                        'market_regime': market_regime,
                        'performance': performance_data,
                        'current_parameters': current_parameters
                    }
                    
                    # Lưu vào file
                    ml_path = os.path.join(self.results_dir, f"{ml_key}_ml_optimization.json")
                    with open(ml_path, 'w') as f:
                        json.dump(self.ml_models[ml_key], f, indent=2)
                        
                    logger.info(f"Đã tối ưu hóa tham số cho {ml_key}")
                    
                except Exception as e:
                    logger.error(f"Lỗi khi tối ưu hóa tham số cho {key}: {str(e)}")
                    
            # Huấn luyện mô hình dự đoán tham số
            if len(self.ml_models) > 5:  # Cần ít nhất 5 mẫu để huấn luyện
                parameter_tuner.train_parameter_prediction_model()
                logger.info("Đã huấn luyện mô hình dự đoán tham số")
                
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi áp dụng học máy: {str(e)}")
            return False
    
    def generate_report(self) -> Dict:
        """
        Tạo báo cáo tổng hợp
        
        Returns:
            Dict: Báo cáo tổng hợp
        """
        logger.info("Tạo báo cáo tổng hợp")
        
        # Kiểm tra nếu không có kết quả backtest
        if not self.results:
            logger.warning("Không có kết quả backtest để tạo báo cáo")
            return {}
            
        try:
            # Tạo báo cáo
            report = {
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total_tests': len(self.results),
                    'coins_tested': len(set([k.split('_')[0] for k in self.results.keys()])),
                    'timeframes_tested': len(set([k.split('_')[1] for k in self.results.keys()])),
                    'periods_tested': len(set([k.split('_')[2] for k in self.results.keys()])),
                    'strategies_tested': len(set(['_'.join(k.split('_')[3:]) for k in self.results.keys()]))
                },
                'top_performers': {},
                'strategy_comparison': {},
                'coin_comparison': {},
                'timeframe_comparison': {},
                'period_comparison': {},
                'ml_optimization': {}
            }
            
            # Tính toán hiệu suất trung bình cho từng chiến lược
            strategy_metrics = {}
            for key, result in self.results.items():
                parts = key.split('_')
                if len(parts) < 4:
                    continue
                    
                strategy_name = '_'.join(parts[3:])
                
                if strategy_name not in strategy_metrics:
                    strategy_metrics[strategy_name] = {
                        'total_profit': [],
                        'win_rate': [],
                        'profit_factor': [],
                        'max_drawdown': [],
                        'sharpe_ratio': [],
                        'expectancy': [],
                        'count': 0
                    }
                    
                metrics = strategy_metrics[strategy_name]
                metrics['total_profit'].append(result.get('total_profit_pct', 0))
                metrics['win_rate'].append(result.get('win_rate', 0))
                metrics['profit_factor'].append(result.get('profit_factor', 0))
                metrics['max_drawdown'].append(result.get('max_drawdown', 0))
                metrics['sharpe_ratio'].append(result.get('sharpe_ratio', 0))
                metrics['expectancy'].append(result.get('expectancy', 0))
                metrics['count'] += 1
                
            # Tính trung bình
            for strategy_name, metrics in strategy_metrics.items():
                report['strategy_comparison'][strategy_name] = {
                    'avg_total_profit': np.mean(metrics['total_profit']),
                    'avg_win_rate': np.mean(metrics['win_rate']),
                    'avg_profit_factor': np.mean(metrics['profit_factor']),
                    'avg_max_drawdown': np.mean(metrics['max_drawdown']),
                    'avg_sharpe_ratio': np.mean(metrics['sharpe_ratio']),
                    'avg_expectancy': np.mean(metrics['expectancy']),
                    'count': metrics['count']
                }
                
            # Tìm top performers
            top_profit = sorted(self.results.items(), key=lambda x: x[1].get('total_profit_pct', 0), reverse=True)
            top_sharpe = sorted(self.results.items(), key=lambda x: x[1].get('sharpe_ratio', 0), reverse=True)
            top_expectancy = sorted(self.results.items(), key=lambda x: x[1].get('expectancy', 0), reverse=True)
            
            report['top_performers']['by_profit'] = [{'key': k, 'profit': v.get('total_profit_pct', 0)} 
                                                for k, v in top_profit[:10]]
            report['top_performers']['by_sharpe'] = [{'key': k, 'sharpe': v.get('sharpe_ratio', 0)} 
                                                for k, v in top_sharpe[:10]]
            report['top_performers']['by_expectancy'] = [{'key': k, 'expectancy': v.get('expectancy', 0)} 
                                                    for k, v in top_expectancy[:10]]
                                                    
            # Thêm thông tin ML optimization
            if self.ml_models:
                improvements = []
                
                for key, model in self.ml_models.items():
                    current_params = model.get('current_parameters', {})
                    optimal_params = model.get('optimal_parameters', {})
                    
                    # Tính sự khác biệt giữa tham số hiện tại và tham số tối ưu
                    param_diff = {}
                    for param, value in optimal_params.items():
                        if param in current_params:
                            old_value = current_params[param]
                            if isinstance(old_value, (int, float)) and isinstance(value, (int, float)):
                                change_pct = (value - old_value) / old_value * 100 if old_value != 0 else 0
                                param_diff[param] = {
                                    'old': old_value,
                                    'new': value,
                                    'change_pct': change_pct
                                }
                    
                    improvements.append({
                        'key': key,
                        'market_regime': model.get('market_regime', 'unknown'),
                        'performance': model.get('performance', {}),
                        'param_diff': param_diff
                    })
                
                report['ml_optimization']['improvements'] = improvements
                                                    
            # Lưu báo cáo vào file
            report_path = os.path.join(self.results_dir, "comprehensive_report.json")
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
                
            # Tạo báo cáo HTML
            self._create_html_report(report)
                
            logger.info(f"Đã tạo báo cáo tổng hợp: {report_path}")
            
            return report
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo: {str(e)}")
            return {}
    
    def _create_html_report(self, report: Dict) -> None:
        """
        Tạo báo cáo HTML
        
        Args:
            report (Dict): Báo cáo tổng hợp
        """
        try:
            # Tạo nội dung HTML
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Báo cáo kiểm thử toàn diện</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1, h2, h3 {{ color: #333; }}
                    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    tr:nth-child(even) {{ background-color: #f9f9f9; }}
                    .positive {{ color: green; }}
                    .negative {{ color: red; }}
                    .chart {{ margin: 20px 0; max-width: 100%; }}
                </style>
            </head>
            <body>
                <h1>Báo cáo kiểm thử toàn diện</h1>
                <p>Thời gian: {report.get('timestamp', datetime.now().isoformat())}</p>
                
                <h2>Tổng quan</h2>
                <table>
                    <tr>
                        <th>Số lượng kiểm thử</th>
                        <td>{report.get('summary', {}).get('total_tests', 0)}</td>
                    </tr>
                    <tr>
                        <th>Số lượng coin</th>
                        <td>{report.get('summary', {}).get('coins_tested', 0)}</td>
                    </tr>
                    <tr>
                        <th>Số lượng khung thời gian</th>
                        <td>{report.get('summary', {}).get('timeframes_tested', 0)}</td>
                    </tr>
                    <tr>
                        <th>Số lượng khoảng thời gian</th>
                        <td>{report.get('summary', {}).get('periods_tested', 0)}</td>
                    </tr>
                    <tr>
                        <th>Số lượng chiến lược</th>
                        <td>{report.get('summary', {}).get('strategies_tested', 0)}</td>
                    </tr>
                </table>
                
                <h2>So sánh chiến lược</h2>
                <table>
                    <tr>
                        <th>Chiến lược</th>
                        <th>Lợi nhuận trung bình (%)</th>
                        <th>Tỷ lệ thắng trung bình (%)</th>
                        <th>Profit factor trung bình</th>
                        <th>Drawdown tối đa trung bình (%)</th>
                        <th>Sharpe ratio trung bình</th>
                        <th>Expectancy trung bình</th>
                        <th>Số lượng kiểm thử</th>
                    </tr>
            """
            
            # Thêm dữ liệu so sánh chiến lược
            for strategy, metrics in report.get('strategy_comparison', {}).items():
                profit_class = "positive" if metrics.get('avg_total_profit', 0) > 0 else "negative"
                html += f"""
                    <tr>
                        <td>{strategy}</td>
                        <td class="{profit_class}">{metrics.get('avg_total_profit', 0):.2f}</td>
                        <td>{metrics.get('avg_win_rate', 0):.2f}</td>
                        <td>{metrics.get('avg_profit_factor', 0):.2f}</td>
                        <td>{metrics.get('avg_max_drawdown', 0):.2f}</td>
                        <td>{metrics.get('avg_sharpe_ratio', 0):.2f}</td>
                        <td>{metrics.get('avg_expectancy', 0):.2f}</td>
                        <td>{metrics.get('count', 0)}</td>
                    </tr>
                """
                
            html += """
                </table>
                
                <h2>Top Performers</h2>
                <h3>Top 10 theo lợi nhuận</h3>
                <table>
                    <tr>
                        <th>Kiểm thử</th>
                        <th>Lợi nhuận (%)</th>
                    </tr>
            """
            
            # Thêm top performers by profit
            for performer in report.get('top_performers', {}).get('by_profit', []):
                profit_class = "positive" if performer.get('profit', 0) > 0 else "negative"
                html += f"""
                    <tr>
                        <td>{performer.get('key', '')}</td>
                        <td class="{profit_class}">{performer.get('profit', 0):.2f}</td>
                    </tr>
                """
                
            html += """
                </table>
                
                <h3>Top 10 theo Sharpe ratio</h3>
                <table>
                    <tr>
                        <th>Kiểm thử</th>
                        <th>Sharpe ratio</th>
                    </tr>
            """
            
            # Thêm top performers by sharpe
            for performer in report.get('top_performers', {}).get('by_sharpe', []):
                html += f"""
                    <tr>
                        <td>{performer.get('key', '')}</td>
                        <td>{performer.get('sharpe', 0):.2f}</td>
                    </tr>
                """
                
            html += """
                </table>
                
                <h2>Tối ưu hóa ML</h2>
                <table>
                    <tr>
                        <th>Chiến lược</th>
                        <th>Chế độ thị trường</th>
                        <th>Tham số cải thiện</th>
                        <th>Hiệu suất hiện tại</th>
                    </tr>
            """
            
            # Thêm ML optimization results
            for improvement in report.get('ml_optimization', {}).get('improvements', []):
                # Format param diff
                param_diff_html = ""
                for param, diff in improvement.get('param_diff', {}).items():
                    change_class = "positive" if diff.get('change_pct', 0) > 0 else "negative"
                    param_diff_html += f"{param}: {diff.get('old', 0)} → {diff.get('new', 0)} ({diff.get('change_pct', 0):.2f}%)<br>"
                
                # Format performance
                performance = improvement.get('performance', {})
                performance_html = f"""
                    Lợi nhuận: {performance.get('total_profit', 0):.2f}%<br>
                    Win rate: {performance.get('win_rate', 0):.2f}%<br>
                    Profit factor: {performance.get('profit_factor', 0):.2f}<br>
                    Sharpe ratio: {performance.get('sharpe_ratio', 0):.2f}
                """
                
                html += f"""
                    <tr>
                        <td>{improvement.get('key', '')}</td>
                        <td>{improvement.get('market_regime', 'unknown')}</td>
                        <td>{param_diff_html}</td>
                        <td>{performance_html}</td>
                    </tr>
                """
                
            html += """
                </table>
                
                <h2>Biểu đồ</h2>
                <h3>Một số biểu đồ hiệu suất tiêu biểu</h3>
            """
            
            # Thêm một số biểu đồ tiêu biểu (top 5 performance)
            top_performers = report.get('top_performers', {}).get('by_profit', [])
            for i, performer in enumerate(top_performers[:5]):
                key = performer.get('key', '')
                equity_chart = os.path.join(self.charts_dir, f"{key}_equity.png")
                trades_chart = os.path.join(self.charts_dir, f"{key}_trades.png")
                
                if os.path.exists(equity_chart) and os.path.exists(trades_chart):
                    html += f"""
                        <h4>{i+1}. {key}</h4>
                        <div class="chart">
                            <img src="{equity_chart}" alt="Equity Curve" width="800">
                        </div>
                        <div class="chart">
                            <img src="{trades_chart}" alt="Trades" width="800">
                        </div>
                    """
                    
            html += """
            </body>
            </html>
            """
            
            # Lưu báo cáo HTML
            html_path = os.path.join(self.results_dir, "comprehensive_report.html")
            with open(html_path, 'w') as f:
                f.write(html)
                
            logger.info(f"Đã tạo báo cáo HTML: {html_path}")
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo HTML: {str(e)}")

def main():
    """Hàm chính"""
    try:
        # Khởi tạo tester
        tester = ComprehensiveTester()
        
        # Tải dữ liệu
        print("Đang tải dữ liệu...")
        tester.fetch_data()
        
        # Chạy backtest
        print("Đang chạy backtest...")
        tester.run_backtest()
        
        # Áp dụng học máy
        print("Đang áp dụng học máy...")
        tester.apply_machine_learning()
        
        # Tạo báo cáo
        print("Đang tạo báo cáo...")
        report = tester.generate_report()
        
        print(f"Đã hoàn thành! Kết quả được lưu trong thư mục {tester.results_dir}")
        print(f"Báo cáo chi tiết: {os.path.join(tester.results_dir, 'comprehensive_report.html')}")
        
    except Exception as e:
        logger.error(f"Lỗi khi chạy kiểm thử toàn diện: {str(e)}")
        logger.error(str(traceback.format_exc()))

if __name__ == "__main__":
    main()