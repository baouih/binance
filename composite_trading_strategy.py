#!/usr/bin/env python3
"""
Module chiến thuật giao dịch tổng hợp nâng cao (Composite Trading Strategy)

Module này triển khai một chiến thuật giao dịch tổng hợp tiên tiến, kết hợp nhiều chiến lược 
giao dịch với trọng số động, tự động điều chỉnh theo chế độ thị trường và hiệu suất gần đây.
Cung cấp khả năng thích ứng với điều kiện thị trường thay đổi để cải thiện hiệu suất.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union, Any
from datetime import datetime, timedelta
import time

from market_regime_detector import MarketRegimeDetector
from composite_indicator import CompositeIndicator
from data_processor import DataProcessor

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("composite_trading_strategy")

# Đường dẫn đến các file cấu hình
CONFIG_DIR = "configs"
ALGORITHM_CONFIG_PATH = os.path.join(CONFIG_DIR, "algorithm_config.json")
ACCOUNT_CONFIG_PATH = "account_config.json"

class CompositeTradingStrategy:
    """
    Lớp chiến thuật giao dịch tổng hợp kết hợp nhiều chiến thuật cơ bản 
    với trọng số động, tự động điều chỉnh theo điều kiện thị trường.
    """
    
    def __init__(self, 
                data_processor: Optional[DataProcessor] = None,
                config_path: str = ALGORITHM_CONFIG_PATH,
                account_config_path: str = ACCOUNT_CONFIG_PATH):
        """
        Khởi tạo chiến thuật giao dịch tổng hợp.
        
        Args:
            data_processor (DataProcessor, optional): Bộ xử lý dữ liệu
            config_path (str): Đường dẫn đến file cấu hình thuật toán
            account_config_path (str): Đường dẫn đến file cấu hình tài khoản
        """
        self.config_path = config_path
        self.account_config_path = account_config_path
        
        # Tải cấu hình
        self.config = self._load_config(config_path)
        self.account_config = self._load_config(account_config_path)
        
        # Khởi tạo bộ phát hiện chế độ thị trường
        self.market_regime_detector = MarketRegimeDetector()
        
        # Khởi tạo bộ xử lý dữ liệu nếu chưa được cung cấp
        if data_processor is None:
            self.data_processor = DataProcessor()
        else:
            self.data_processor = data_processor
        
        # Khởi tạo Composite Indicator
        indicators = ['rsi', 'macd', 'ema_cross', 'bbands', 'volume_trend', 'adx']
        self.composite_indicator = CompositeIndicator(
            indicators=indicators,
            dynamic_weights=True,
            lookback_period=20
        )
        
        # Lưu trữ trạng thái
        self.current_regime = None
        self.last_signals = {}
        self.performance_history = []
        self.current_positions = {}
        
        logger.info(f"Đã khởi tạo CompositeTradingStrategy với cấu hình từ {config_path}")
        
    def _load_config(self, config_path: str) -> Dict:
        """
        Tải cấu hình từ file.
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
            
        Returns:
            Dict: Cấu hình đã tải
        """
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {config_path}")
                return config
            else:
                logger.warning(f"File cấu hình {config_path} không tồn tại")
                return {}
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình từ {config_path}: {e}")
            return {}
    
    def analyze_market(self, symbol: str, timeframe: str) -> Dict:
        """
        Phân tích thị trường và cập nhật chế độ thị trường hiện tại.
        
        Args:
            symbol (str): Mã cặp giao dịch (vd: BTCUSDT)
            timeframe (str): Khung thời gian (vd: 1h, 4h)
            
        Returns:
            Dict: Kết quả phân tích thị trường
        """
        try:
            # Lấy dữ liệu giá
            df = self.data_processor.get_market_data(symbol, timeframe)
            
            if df is None or df.empty:
                logger.error(f"Không thể lấy dữ liệu thị trường cho {symbol} {timeframe}")
                return {'success': False, 'message': 'Không thể lấy dữ liệu thị trường'}
            
            # Phát hiện chế độ thị trường
            self.current_regime = self.market_regime_detector.detect_regime(df)
            
            # Tính toán các chỉ báo kỹ thuật nếu chưa có
            if 'rsi' not in df.columns:
                df = self.data_processor.add_basic_indicators(df)
            
            # Lấy khuyến nghị từ composite_indicator
            recommendation = self.composite_indicator.get_trading_recommendation(df)
            
            result = {
                'success': True,
                'symbol': symbol,
                'timeframe': timeframe,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'market_regime': self.current_regime,
                'composite_score': recommendation['composite_score'],
                'signal': recommendation['signal'],
                'confidence': recommendation['confidence'],
                'signal_description': recommendation['signal_description'],
                'individual_scores': recommendation['individual_scores'],
                'indicators': {}
            }
            
            # Thêm giá trị các chỉ báo chính
            latest = df.iloc[-1]
            result['indicators']['price'] = latest['close']
            result['indicators']['volume'] = latest['volume']
            
            for indicator in self.composite_indicator.indicators:
                if indicator in df.columns:
                    result['indicators'][indicator] = latest[indicator]
            
            # Thêm thông tin chế độ thị trường
            result['regime_description'] = self.market_regime_detector.get_regime_description(self.current_regime)
            
            # Lưu tín hiệu gần đây
            self.last_signals[symbol] = {
                'timeframe': timeframe,
                'timestamp': result['timestamp'],
                'signal': result['signal'],
                'confidence': result['confidence'],
                'market_regime': self.current_regime
            }
            
            logger.info(f"Phân tích thị trường {symbol} {timeframe}: {result['signal_description']} (Điểm: {result['composite_score']:.2f}, Độ tin cậy: {result['confidence']:.2f}%)")
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích thị trường {symbol} {timeframe}: {e}")
            return {'success': False, 'message': f'Lỗi khi phân tích thị trường: {str(e)}'}
    
    def get_trading_signal(self, symbol: str, timeframe: str) -> Dict:
        """
        Lấy tín hiệu giao dịch theo chiến thuật tổng hợp.
        
        Args:
            symbol (str): Mã cặp giao dịch (vd: BTCUSDT)
            timeframe (str): Khung thời gian (vd: 1h, 4h)
            
        Returns:
            Dict: Tín hiệu giao dịch
        """
        # Phân tích thị trường
        analysis = self.analyze_market(symbol, timeframe)
        
        if not analysis['success']:
            return analysis
        
        # Áp dụng bộ lọc tín hiệu
        filtered_signal = self._apply_signal_filters(analysis)
        
        # Tính toán tham số quản lý rủi ro
        risk_params = self._calculate_risk_params(analysis)
        
        # Tạo khuyến nghị giao dịch
        trading_signal = {
            'success': True,
            'symbol': symbol,
            'timeframe': timeframe,
            'timestamp': analysis['timestamp'],
            'action': self._get_action_from_signal(filtered_signal),
            'original_signal': analysis['signal'],
            'filtered_signal': filtered_signal,
            'confidence': analysis['confidence'],
            'market_regime': analysis['market_regime'],
            'risk_params': risk_params,
            'price': analysis['indicators'].get('price', 0)
        }
        
        # Thêm các thông tin khác
        if 'explanation' in analysis:
            trading_signal['explanation'] = analysis['explanation']
        
        # Ghi log
        logger.info(f"Tín hiệu giao dịch cho {symbol} {timeframe}: {trading_signal['action']} (Độ tin cậy: {trading_signal['confidence']:.2f}%)")
        
        return trading_signal
    
    def _apply_signal_filters(self, analysis: Dict) -> float:
        """
        Áp dụng các bộ lọc tín hiệu để tăng độ tin cậy.
        
        Args:
            analysis (Dict): Kết quả phân tích thị trường
            
        Returns:
            float: Tín hiệu sau khi lọc (-1 đến 1)
        """
        if not analysis['success']:
            return 0.0
            
        signal = analysis['signal']
        confidence = analysis['confidence'] / 100.0  # Chuyển từ % sang tỷ lệ 0-1
        
        # Lấy cấu hình bộ lọc tín hiệu
        filters = self.config.get('signal_filters', {})
        
        # Kiểm tra độ tin cậy tối thiểu
        min_confidence = filters.get('min_signal_strength', 0.5)
        if confidence < min_confidence:
            logger.info(f"Tín hiệu bị lọc do độ tin cậy thấp: {confidence:.2f} < {min_confidence:.2f}")
            return 0.0
        
        # Lọc theo chế độ thị trường
        if filters.get('filter_by_market_regime', True):
            if analysis['market_regime'] == 'ranging' and abs(signal) > 0.5:
                # Giảm cường độ tín hiệu trong thị trường sideway
                logger.info(f"Giảm cường độ tín hiệu trong thị trường sideway từ {signal:.2f} xuống {signal * 0.7:.2f}")
                signal *= 0.7
            elif analysis['market_regime'] == 'volatile' and abs(signal) > 0.5:
                # Giảm cường độ tín hiệu trong thị trường biến động
                logger.info(f"Giảm cường độ tín hiệu trong thị trường biến động từ {signal:.2f} xuống {signal * 0.8:.2f}")
                signal *= 0.8
        
        # Thêm các bộ lọc khác theo nhu cầu...
        
        return signal
    
    def _calculate_risk_params(self, analysis: Dict) -> Dict:
        """
        Tính toán tham số quản lý rủi ro dựa trên phân tích thị trường.
        
        Args:
            analysis (Dict): Kết quả phân tích thị trường
            
        Returns:
            Dict: Các tham số quản lý rủi ro
        """
        # Lấy cấu hình quản lý rủi ro
        risk_config = self.config.get('risk_management', {})
        
        # Lấy thông tin từ account_config
        leverage = self.account_config.get('leverage', 10)
        risk_per_trade = self.account_config.get('risk_per_trade', 1.0)
        
        # Lấy ATR nếu có
        atr = analysis.get('indicators', {}).get('atr', None)
        
        # Tính SL/TP dựa trên ATR nếu có, nếu không thì sử dụng giá trị % mặc định
        if atr is not None:
            # Sử dụng ATR để tính SL/TP
            sl_multiplier = risk_config.get('stop_loss_atr_multiplier', 1.5)
            tp_multiplier = risk_config.get('take_profit_atr_multiplier', 2.5)
            
            stop_loss_pct = (atr * sl_multiplier / analysis['indicators']['price']) * 100
            take_profit_pct = (atr * tp_multiplier / analysis['indicators']['price']) * 100
        else:
            # Sử dụng % mặc định
            stop_loss_pct = 1.5
            take_profit_pct = 3.0
        
        # Điều chỉnh SL/TP theo chế độ thị trường
        if risk_config.get('market_volatility_adjustment', True):
            if analysis['market_regime'] == 'volatile':
                # Tăng SL trong thị trường biến động
                stop_loss_pct *= 1.2
                take_profit_pct *= 1.1
            elif analysis['market_regime'] == 'ranging':
                # Giảm TP trong thị trường sideway
                take_profit_pct *= 0.8
        
        # Tính toán trailing stop
        trailing_activation = risk_config.get('trailing_stop_activation', 1.0)
        trailing_callback = risk_config.get('trailing_stop_callback', 0.3)
        
        return {
            'leverage': leverage,
            'risk_percentage': risk_per_trade,
            'stop_loss_pct': round(stop_loss_pct, 2),
            'take_profit_pct': round(take_profit_pct, 2),
            'trailing_stop_enabled': risk_config.get('trailing_stop_enabled', True),
            'trailing_activation_pct': trailing_activation,
            'trailing_callback_pct': trailing_callback
        }
    
    def _get_action_from_signal(self, signal: float) -> str:
        """
        Chuyển đổi tín hiệu số thành hành động giao dịch.
        
        Args:
            signal (float): Tín hiệu (-1 đến 1)
            
        Returns:
            str: Hành động giao dịch (BUY, SELL, STRONG_BUY, STRONG_SELL, HOLD)
        """
        if signal >= 0.7:
            return "STRONG_BUY"
        elif signal >= 0.3:
            return "BUY"
        elif signal <= -0.7:
            return "STRONG_SELL"
        elif signal <= -0.3:
            return "SELL"
        else:
            return "HOLD"
    
    def get_market_regime(self) -> str:
        """
        Lấy chế độ thị trường hiện tại.
        
        Returns:
            str: Chế độ thị trường
        """
        return self.current_regime or "unknown"
    
    def get_suitable_strategies(self, regime: Optional[str] = None) -> Dict[str, float]:
        """
        Lấy các chiến thuật phù hợp với chế độ thị trường hiện tại.
        
        Args:
            regime (str, optional): Chế độ thị trường, nếu None sẽ sử dụng chế độ hiện tại
            
        Returns:
            Dict[str, float]: Các chiến thuật và trọng số tương ứng
        """
        if regime is None:
            regime = self.current_regime or "unknown"
        
        # Lấy cấu hình chế độ thị trường
        regime_config = self.config.get('market_regime', {})
        regimes = regime_config.get('regimes', {})
        
        if regime in regimes:
            strategies = regimes[regime].get('strategies', [])
            weights = regimes[regime].get('weights', [])
            
            if len(strategies) == len(weights):
                return dict(zip(strategies, weights))
        
        # Mặc định
        return {
            'rsi_strategy': 0.25,
            'macd_strategy': 0.25,
            'bollinger_strategy': 0.25,
            'ema_cross_strategy': 0.25
        }
    
    def get_optimal_parameters(self, strategy: str) -> Dict:
        """
        Lấy tham số tối ưu cho một chiến thuật cụ thể.
        
        Args:
            strategy (str): Tên chiến thuật
            
        Returns:
            Dict: Tham số tối ưu
        """
        algorithms = self.config.get('algorithms', {})
        if strategy in algorithms:
            return algorithms[strategy].get('parameters', {})
        
        # Mặc định
        logger.warning(f"Không tìm thấy cấu hình cho chiến thuật {strategy}, sử dụng mặc định")
        if strategy == 'rsi_strategy':
            return {'rsi_period': 14, 'rsi_overbought': 70, 'rsi_oversold': 30}
        elif strategy == 'macd_strategy':
            return {'fast_period': 12, 'slow_period': 26, 'signal_period': 9}
        elif strategy == 'bollinger_strategy':
            return {'bb_period': 20, 'bb_std': 2.0}
        elif strategy == 'ema_cross_strategy':
            return {'fast_ema': 10, 'slow_ema': 50}
        else:
            return {}
    
    def get_last_signals(self, symbol: Optional[str] = None) -> Dict:
        """
        Lấy các tín hiệu gần đây.
        
        Args:
            symbol (str, optional): Mã cặp giao dịch, nếu None sẽ trả về tất cả
            
        Returns:
            Dict: Tín hiệu gần đây
        """
        if symbol:
            return self.last_signals.get(symbol, {})
        return self.last_signals
    
    def update_performance(self, trade_result: Dict) -> None:
        """
        Cập nhật lịch sử hiệu suất.
        
        Args:
            trade_result (Dict): Kết quả giao dịch
        """
        self.performance_history.append(trade_result)
        
        # Giới hạn lịch sử
        if len(self.performance_history) > 100:
            self.performance_history.pop(0)
    
    def calculate_performance_metrics(self) -> Dict:
        """
        Tính toán các chỉ số hiệu suất.
        
        Returns:
            Dict: Các chỉ số hiệu suất
        """
        if not self.performance_history:
            return {
                'win_rate': 0,
                'profit_factor': 0,
                'average_win': 0,
                'average_loss': 0,
                'max_drawdown': 0,
                'expectancy': 0,
                'total_trades': 0
            }
        
        total_trades = len(self.performance_history)
        winning_trades = [t for t in self.performance_history if t.get('profit', 0) > 0]
        losing_trades = [t for t in self.performance_history if t.get('profit', 0) <= 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        
        # Win rate
        win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0
        
        # Average win/loss
        avg_win = sum(t.get('profit', 0) for t in winning_trades) / win_count if win_count > 0 else 0
        avg_loss = sum(abs(t.get('profit', 0)) for t in losing_trades) / loss_count if loss_count > 0 else 0
        
        # Profit factor
        total_wins = sum(t.get('profit', 0) for t in winning_trades)
        total_losses = sum(abs(t.get('profit', 0)) for t in losing_trades)
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Expectancy
        expectancy = (win_rate / 100 * avg_win) - ((1 - win_rate / 100) * avg_loss)
        
        # Đơn giản hóa tính max drawdown
        max_drawdown = 0
        if len(self.performance_history) >= 5:
            # Tính toán max drawdown đơn giản
            equity_curve = [0]
            for trade in self.performance_history:
                equity_curve.append(equity_curve[-1] + trade.get('profit', 0))
            
            max_equity = equity_curve[0]
            max_drawdown_pct = 0
            
            for equity in equity_curve:
                max_equity = max(max_equity, equity)
                drawdown = (max_equity - equity) / max_equity * 100 if max_equity > 0 else 0
                max_drawdown_pct = max(max_drawdown_pct, drawdown)
            
            max_drawdown = max_drawdown_pct
        
        return {
            'win_rate': round(win_rate, 2),
            'profit_factor': round(profit_factor, 2),
            'average_win': round(avg_win, 2),
            'average_loss': round(avg_loss, 2),
            'max_drawdown': round(max_drawdown, 2),
            'expectancy': round(expectancy, 2),
            'total_trades': total_trades
        }
    
    def get_strategy_summary(self) -> Dict:
        """
        Lấy tóm tắt chiến thuật hiện tại.
        
        Returns:
            Dict: Tóm tắt chiến thuật
        """
        return {
            'primary_algorithm': self.config.get('primary_algorithm', 'combined_strategy'),
            'backup_algorithm': self.config.get('backup_algorithm', 'ema_cross_strategy'),
            'current_market_regime': self.current_regime or "unknown",
            'regime_strategies': self.get_suitable_strategies(),
            'performance_metrics': self.calculate_performance_metrics(),
            'signal_count': {k: len(v) for k, v in self.last_signals.items() if isinstance(v, list)}
        }
    
    def save_config(self, update_config: Optional[Dict] = None) -> bool:
        """
        Lưu cấu hình hiện tại vào file.
        
        Args:
            update_config (Dict, optional): Cập nhật cấu hình trước khi lưu
            
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        try:
            if update_config:
                # Cập nhật cấu hình
                self.config.update(update_config)
            
            # Cập nhật timestamp
            self.config['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            
            logger.info(f"Đã lưu cấu hình vào {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {e}")
            return False

def main():
    """Hàm chính để test CompositeTradingStrategy"""
    # Khởi tạo chiến thuật giao dịch tổng hợp
    strategy = CompositeTradingStrategy()
    
    # Test phân tích thị trường
    symbol = "BTCUSDT"
    timeframe = "1h"
    
    print(f"===== PHÂN TÍCH THỊ TRƯỜNG {symbol} {timeframe} =====")
    analysis = strategy.analyze_market(symbol, timeframe)
    
    if analysis['success']:
        print(f"Chế độ thị trường: {analysis['market_regime']}")
        print(f"Điểm tổng hợp: {analysis['composite_score']:.2f}")
        print(f"Tín hiệu: {analysis['signal_description']} (Độ tin cậy: {analysis['confidence']:.2f}%)")
        print("\nĐiểm của từng chỉ báo:")
        for indicator, score in analysis['individual_scores'].items():
            print(f"- {indicator}: {score:.2f}")
    else:
        print(f"Lỗi: {analysis.get('message', 'Không rõ lỗi')}")
    
    print("\n===== TÍN HIỆU GIAO DỊCH =====")
    signal = strategy.get_trading_signal(symbol, timeframe)
    
    if signal['success']:
        print(f"Hành động: {signal['action']}")
        print(f"Độ tin cậy: {signal['confidence']:.2f}%")
        print(f"Chế độ thị trường: {signal['market_regime']}")
        print("\nTham số quản lý rủi ro:")
        for param, value in signal['risk_params'].items():
            print(f"- {param}: {value}")
    else:
        print(f"Lỗi: {signal.get('message', 'Không rõ lỗi')}")
    
    print("\n===== CHIẾN THUẬT PHÙ HỢP CHO CHẾ ĐỘ THỊ TRƯỜNG HIỆN TẠI =====")
    strategies = strategy.get_suitable_strategies()
    for s, weight in strategies.items():
        print(f"- {s}: {weight:.2f}")
    
    print("\n===== TÓM TẮT CHIẾN THUẬT =====")
    summary = strategy.get_strategy_summary()
    for key, value in summary.items():
        print(f"- {key}: {value}")

if __name__ == "__main__":
    main()