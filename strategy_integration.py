#!/usr/bin/env python3
"""
Module tích hợp chiến thuật giao dịch (Strategy Integration)

Module này tích hợp các chiến thuật giao dịch vào hệ thống chính, đảm bảo rằng
các tín hiệu giao dịch được tạo ra đúng cách và được ghi log đầy đủ.
"""

import os
import json
import logging
import time
from typing import Dict, List, Tuple, Optional, Union, Any
from datetime import datetime, timedelta

from composite_trading_strategy import CompositeTradingStrategy
from market_regime_detector import MarketRegimeDetector
from data_processor import DataProcessor
from binance_api import BinanceAPI
from telegram_notifier import TelegramNotifier

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("strategy_integration")

class StrategyIntegration:
    """Lớp tích hợp chiến thuật giao dịch vào hệ thống"""
    
    def __init__(self, account_config_path: str = 'account_config.json',
               bot_config_path: str = 'bot_config.json',
               algorithm_config_path: str = 'configs/algorithm_config.json'):
        """
        Khởi tạo bộ tích hợp chiến thuật
        
        Args:
            account_config_path (str): Đường dẫn đến file cấu hình tài khoản
            bot_config_path (str): Đường dẫn đến file cấu hình bot
            algorithm_config_path (str): Đường dẫn đến file cấu hình thuật toán
        """
        self.account_config_path = account_config_path
        self.bot_config_path = bot_config_path
        self.algorithm_config_path = algorithm_config_path
        
        # Tải cấu hình
        self.account_config = self._load_config(account_config_path)
        self.bot_config = self._load_config(bot_config_path)
        
        # Khởi tạo các thành phần
        self.data_processor = DataProcessor()
        self.binance_api = BinanceAPI()
        self.market_regime_detector = MarketRegimeDetector()
        
        # Khởi tạo chiến thuật tổng hợp
        self.trading_strategy = CompositeTradingStrategy(
            data_processor=self.data_processor,
            config_path=algorithm_config_path,
            account_config_path=account_config_path
        )
        
        # Tạo Telegram notifier
        self.telegram_enabled = self.account_config.get('telegram_enabled', False)
        if self.telegram_enabled:
            bot_token = self.account_config.get('telegram_bot_token', '')
            chat_id = self.account_config.get('telegram_chat_id', '')
            self.telegram = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)
        else:
            self.telegram = None
        
        # Trạng thái hệ thống
        self.active_positions = {}
        self.last_signals = {}
        self.signal_history = []
        
        logger.info("Đã khởi tạo StrategyIntegration")
        
    def _load_config(self, config_path: str) -> Dict:
        """
        Tải cấu hình từ file
        
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
    
    def analyze_market(self, symbol: str = 'BTCUSDT', timeframe: str = '1h') -> Dict:
        """
        Phân tích thị trường và tạo tín hiệu giao dịch
        
        Args:
            symbol (str): Mã cặp giao dịch
            timeframe (str): Khung thời gian
            
        Returns:
            Dict: Kết quả phân tích thị trường
        """
        try:
            # Sử dụng chiến thuật tổng hợp để phân tích
            analysis = self.trading_strategy.analyze_market(symbol, timeframe)
            
            if analysis['success']:
                # Lưu tín hiệu gần đây
                self.last_signals[symbol] = {
                    'timeframe': timeframe,
                    'timestamp': analysis['timestamp'],
                    'signal': analysis['signal'],
                    'score': analysis['composite_score'],
                    'confidence': analysis['confidence'],
                    'market_regime': analysis['market_regime']
                }
                
                # Ghi log
                logger.info(f"Phân tích thị trường {symbol} {timeframe}: " +
                         f"{analysis['signal_description']} (Điểm: {analysis['composite_score']:.2f}, " +
                         f"Độ tin cậy: {analysis['confidence']:.2f}%)")
                
                # Gửi thông báo Telegram nếu có tín hiệu mạnh
                if self.telegram_enabled and self.telegram and abs(analysis['signal']) >= 0.7:
                    signal_type = "MUA mạnh" if analysis['signal'] >= 0.7 else "BÁN mạnh"
                    message = (f"📊 Tín hiệu {signal_type} được phát hiện\n"
                              f"💱 {symbol} / {timeframe}\n"
                              f"📈 Điểm: {analysis['composite_score']:.2f}\n"
                              f"✅ Độ tin cậy: {analysis['confidence']:.2f}%\n"
                              f"🔄 Chế độ: {analysis['market_regime']}")
                    self.telegram.send_message(message)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích thị trường {symbol} {timeframe}: {e}")
            return {'success': False, 'message': f'Lỗi khi phân tích thị trường: {str(e)}'}
    
    def get_trading_signal(self, symbol: str = 'BTCUSDT', timeframe: str = '1h') -> Dict:
        """
        Lấy tín hiệu giao dịch đã được lọc
        
        Args:
            symbol (str): Mã cặp giao dịch
            timeframe (str): Khung thời gian
            
        Returns:
            Dict: Tín hiệu giao dịch
        """
        # Sử dụng chiến thuật tổng hợp để lấy tín hiệu
        signal = self.trading_strategy.get_trading_signal(symbol, timeframe)
        
        if signal['success']:
            # Lưu lại lịch sử tín hiệu
            signal_record = {
                'symbol': symbol,
                'timeframe': timeframe,
                'timestamp': signal['timestamp'],
                'action': signal['action'],
                'confidence': signal['confidence'],
                'price': signal['price'],
                'market_regime': signal['market_regime']
            }
            self.signal_history.append(signal_record)
            
            # Giới hạn lịch sử
            if len(self.signal_history) > 100:
                self.signal_history.pop(0)
            
            # Ghi log
            logger.info(f"Tín hiệu giao dịch cho {symbol} {timeframe}: {signal['action']} " +
                     f"(Độ tin cậy: {signal['confidence']:.2f}%)")
        
        return signal
    
    def analyze_all_markets(self) -> Dict[str, Dict]:
        """
        Phân tích tất cả các cặp giao dịch đã cấu hình
        
        Returns:
            Dict[str, Dict]: Kết quả phân tích cho từng cặp giao dịch
        """
        results = {}
        
        # Lấy danh sách cặp giao dịch và khung thời gian từ cấu hình
        symbols = self.account_config.get('symbols', ['BTCUSDT', 'ETHUSDT'])
        timeframes = self.account_config.get('timeframes', ['1h', '4h'])
        
        # Ưu tiên khung thời gian dài hơn
        timeframes.sort(key=lambda x: self._timeframe_to_minutes(x), reverse=True)
        
        # Phân tích từng cặp
        for symbol in symbols:
            # Bắt đầu với khung thời gian dài nhất
            for timeframe in timeframes:
                analysis = self.analyze_market(symbol, timeframe)
                
                if analysis['success']:
                    if symbol not in results:
                        results[symbol] = {}
                    
                    results[symbol][timeframe] = analysis
        
        return results
    
    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """
        Chuyển đổi khung thời gian sang số phút
        
        Args:
            timeframe (str): Khung thời gian (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 3d, 1w, 1M)
            
        Returns:
            int: Số phút
        """
        if 'm' in timeframe:
            return int(timeframe.replace('m', ''))
        elif 'h' in timeframe:
            return int(timeframe.replace('h', '')) * 60
        elif 'd' in timeframe:
            return int(timeframe.replace('d', '')) * 60 * 24
        elif 'w' in timeframe:
            return int(timeframe.replace('w', '')) * 60 * 24 * 7
        elif 'M' in timeframe:
            return int(timeframe.replace('M', '')) * 60 * 24 * 30
        return 0
    
    def get_market_summary(self, symbol: str = 'BTCUSDT') -> Dict:
        """
        Lấy tóm tắt thị trường cho một cặp giao dịch
        
        Args:
            symbol (str): Mã cặp giao dịch
            
        Returns:
            Dict: Tóm tắt thị trường
        """
        return self.data_processor.get_market_summary(symbol)
    
    def get_market_regime(self, symbol: str = 'BTCUSDT', timeframe: str = '1h') -> str:
        """
        Lấy chế độ thị trường hiện tại
        
        Args:
            symbol (str): Mã cặp giao dịch
            timeframe (str): Khung thời gian
            
        Returns:
            str: Chế độ thị trường
        """
        df = self.data_processor.get_market_data(symbol, timeframe)
        regime = self.market_regime_detector.detect_regime(df)
        return regime
    
    def get_suitable_strategies_for_current_market(self, symbol: str = 'BTCUSDT', timeframe: str = '1h') -> Dict[str, float]:
        """
        Lấy các chiến thuật phù hợp với chế độ thị trường hiện tại
        
        Args:
            symbol (str): Mã cặp giao dịch
            timeframe (str): Khung thời gian
            
        Returns:
            Dict[str, float]: Ánh xạ chiến thuật -> trọng số
        """
        # Lấy chế độ thị trường
        regime = self.get_market_regime(symbol, timeframe)
        
        # Lấy các chiến thuật phù hợp
        return self.trading_strategy.get_suitable_strategies(regime)
    
    def execute_trade(self, signal: Dict) -> Dict:
        """
        Thực hiện giao dịch dựa trên tín hiệu
        
        Args:
            signal (Dict): Tín hiệu giao dịch
            
        Returns:
            Dict: Kết quả giao dịch
        """
        if not signal.get('success', False):
            return {'success': False, 'message': 'Tín hiệu không hợp lệ'}
        
        symbol = signal.get('symbol', '')
        action = signal.get('action', 'HOLD')
        price = signal.get('price', 0)
        
        # Kiểm tra xem có nên giao dịch không
        if action in ['HOLD']:
            return {'success': True, 'message': 'Không có hành động', 'action': action}
        
        # Kiểm tra rủi ro
        max_positions = int(self.account_config.get('max_open_positions', 5))
        if len(self.active_positions) >= max_positions and action in ['BUY', 'STRONG_BUY']:
            return {'success': False, 'message': f'Đã đạt giới hạn vị thế mở ({max_positions})'}
        
        # Lấy tham số quản lý rủi ro
        risk_params = signal.get('risk_params', {})
        leverage = risk_params.get('leverage', int(self.account_config.get('leverage', 5)))
        risk_percentage = risk_params.get('risk_percentage', float(self.account_config.get('risk_per_trade', 1.0)))
        stop_loss_pct = risk_params.get('stop_loss_pct', 1.5)
        take_profit_pct = risk_params.get('take_profit_pct', 3.0)
        
        # Tính toán kích thước vị thế
        balance = float(self.bot_config.get('balance', 10000.0))
        position_size_usd = balance * (risk_percentage / 100.0)
        
        # Tính toán số lượng
        quantity = position_size_usd / price
        
        # Tính toán giá stop loss và take profit
        if action in ['BUY', 'STRONG_BUY']:
            side = 'BUY'
            stop_loss = price * (1 - stop_loss_pct / 100.0)
            take_profit = price * (1 + take_profit_pct / 100.0)
        else:
            side = 'SELL'
            stop_loss = price * (1 + stop_loss_pct / 100.0)
            take_profit = price * (1 - take_profit_pct / 100.0)
        
        # Tạo lệnh giao dịch (giả lập hoặc thật tùy vào mode)
        order_result = self._create_order(symbol, side, quantity, price, leverage, stop_loss, take_profit)
        
        if order_result.get('success', False):
            # Lưu vị thế mở
            position_id = order_result.get('order_id', '')
            self.active_positions[position_id] = {
                'symbol': symbol,
                'side': side,
                'entry_price': price,
                'quantity': quantity,
                'leverage': leverage,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'entry_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'action': action,
                'confidence': signal.get('confidence', 0)
            }
            
            # Gửi thông báo
            if self.telegram_enabled and self.telegram:
                message = (f"🔔 Lệnh {side} đã được thực hiện\n"
                          f"💱 {symbol}\n"
                          f"💰 Giá: {price}\n"
                          f"📊 SL: {stop_loss:.2f} / TP: {take_profit:.2f}\n"
                          f"📈 Đòn bẩy: {leverage}x\n"
                          f"💵 Giá trị: {position_size_usd:.2f} USD")
                self.telegram.send_message(message)
            
            logger.info(f"Đã thực hiện lệnh {side} cho {symbol}: {quantity} @ {price}")
        
        return order_result
    
    def _create_order(self, symbol: str, side: str, quantity: float, price: float,
                   leverage: int, stop_loss: float, take_profit: float) -> Dict:
        """
        Tạo lệnh giao dịch (giả lập hoặc thật tùy vào mode)
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng giao dịch (BUY/SELL)
            quantity (float): Số lượng
            price (float): Giá
            leverage (int): Đòn bẩy
            stop_loss (float): Giá stop loss
            take_profit (float): Giá take profit
            
        Returns:
            Dict: Kết quả tạo lệnh
        """
        # Lấy mode từ cấu hình
        mode = self.account_config.get('api_mode', 'testnet')
        
        if mode == 'demo':
            # Chế độ demo, tạo lệnh giả lập
            return {
                'success': True,
                'order_id': f"demo_{int(time.time())}",
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': price,
                'status': 'FILLED',
                'leverage': leverage,
                'stop_loss': stop_loss,
                'take_profit': take_profit
            }
        elif mode in ['testnet', 'live']:
            # Chế độ testnet hoặc live, tạo lệnh thật
            try:
                # Đặt đòn bẩy
                self.binance_api.futures_change_leverage(symbol, leverage)
                
                # Tạo lệnh market
                order = self.binance_api.create_order(
                    symbol=symbol,
                    side=side,
                    type='MARKET',
                    quantity=round(quantity, 6)  # Làm tròn số lượng theo yêu cầu của Binance
                )
                
                # Tạo order_id từ kết quả
                order_id = str(order.get('orderId', f"api_{int(time.time())}"))
                
                # TODO: Thêm stop loss và take profit
                
                return {
                    'success': True,
                    'order_id': order_id,
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'price': price,
                    'status': order.get('status', 'UNKNOWN'),
                    'leverage': leverage,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'api_response': order
                }
            except Exception as e:
                logger.error(f"Lỗi khi tạo lệnh: {str(e)}")
                return {'success': False, 'message': f'Lỗi khi tạo lệnh: {str(e)}'}
        else:
            return {'success': False, 'message': f'Chế độ không hợp lệ: {mode}'}
    
    def update_positions(self) -> List[Dict]:
        """
        Cập nhật trạng thái các vị thế đang mở
        
        Returns:
            List[Dict]: Danh sách các vị thế đã đóng
        """
        closed_positions = []
        
        # Lấy giá hiện tại
        current_prices = {}
        for position_id, position in self.active_positions.items():
            symbol = position['symbol']
            if symbol not in current_prices:
                ticker = self.binance_api.get_symbol_ticker(symbol)
                current_prices[symbol] = float(ticker['price']) if 'price' in ticker else 0
        
        # Cập nhật từng vị thế
        for position_id, position in list(self.active_positions.items()):
            symbol = position['symbol']
            current_price = current_prices.get(symbol, 0)
            
            if current_price <= 0:
                continue
            
            # Kiểm tra điều kiện đóng vị thế
            side = position['side']
            entry_price = position['entry_price']
            stop_loss = position['stop_loss']
            take_profit = position['take_profit']
            
            # Tính lợi nhuận/thua lỗ
            if side == 'BUY':
                pnl_pct = (current_price / entry_price - 1) * 100
                hit_stop_loss = current_price <= stop_loss
                hit_take_profit = current_price >= take_profit
            else:  # SELL
                pnl_pct = (entry_price / current_price - 1) * 100
                hit_stop_loss = current_price >= stop_loss
                hit_take_profit = current_price <= take_profit
            
            # Kiểm tra xem có nên đóng vị thế không
            close_reason = None
            if hit_stop_loss:
                close_reason = 'stop_loss'
            elif hit_take_profit:
                close_reason = 'take_profit'
            
            # Đóng vị thế nếu cần
            if close_reason:
                # Tính lợi nhuận tuyệt đối
                entry_value = entry_price * position['quantity']
                current_value = current_price * position['quantity']
                
                if side == 'BUY':
                    pnl_abs = current_value - entry_value
                else:  # SELL
                    pnl_abs = entry_value - current_value
                
                pnl_abs_with_leverage = pnl_abs * position['leverage']
                
                # Thêm thông tin vào vị thế đã đóng
                position['exit_price'] = current_price
                position['exit_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                position['close_reason'] = close_reason
                position['pnl_pct'] = pnl_pct
                position['pnl_abs'] = pnl_abs_with_leverage
                
                # Thêm vào danh sách vị thế đã đóng
                closed_positions.append(position)
                
                # Xóa khỏi danh sách vị thế đang mở
                del self.active_positions[position_id]
                
                # Gửi thông báo
                if self.telegram_enabled and self.telegram:
                    emoji = "🔴" if pnl_abs_with_leverage < 0 else "🟢"
                    message = (f"{emoji} Vị thế đã đóng ({close_reason})\n"
                              f"💱 {symbol} {side}\n"
                              f"📈 Vào: {entry_price:.2f} / Ra: {current_price:.2f}\n"
                              f"💰 P/L: {pnl_pct:.2f}% ({pnl_abs_with_leverage:.2f} USD)")
                    self.telegram.send_message(message)
                
                logger.info(f"Đã đóng vị thế {side} {symbol}: P/L = {pnl_pct:.2f}% ({pnl_abs_with_leverage:.2f} USD)")
        
        return closed_positions
    
    def run_strategy_cycle(self) -> Dict:
        """
        Chạy một chu kỳ của chiến thuật: phân tích, tạo tín hiệu, thực hiện giao dịch
        
        Returns:
            Dict: Kết quả của chu kỳ
        """
        try:
            logger.info("Bắt đầu chu kỳ chiến thuật mới")
            
            # Cập nhật các vị thế đang mở
            closed_positions = self.update_positions()
            
            # Phân tích tất cả các thị trường
            analysis_results = self.analyze_all_markets()
            
            # Tạo tín hiệu giao dịch và thực hiện giao dịch nếu cần
            trade_results = []
            
            for symbol, timeframe_results in analysis_results.items():
                # Ưu tiên khung thời gian dài hơn
                for timeframe, analysis in sorted(timeframe_results.items(), 
                                              key=lambda x: self._timeframe_to_minutes(x[0]), 
                                              reverse=True):
                    # Chỉ lấy tín hiệu giao dịch nếu có tín hiệu mạnh
                    if abs(analysis.get('signal', 0)) >= 0.5:
                        signal = self.get_trading_signal(symbol, timeframe)
                        
                        # Thực hiện giao dịch nếu có tín hiệu hành động
                        if signal.get('action', 'HOLD') in ['BUY', 'STRONG_BUY', 'SELL', 'STRONG_SELL']:
                            trade_result = self.execute_trade(signal)
                            trade_results.append(trade_result)
                            
                            # Chỉ thực hiện một giao dịch cho mỗi symbol
                            break
            
            return {
                'success': True,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'closed_positions': closed_positions,
                'analysis_count': len(analysis_results),
                'trade_results': trade_results
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi chạy chu kỳ chiến thuật: {str(e)}")
            return {'success': False, 'message': f'Lỗi: {str(e)}'}
    
    def get_system_status(self) -> Dict:
        """
        Lấy trạng thái hệ thống
        
        Returns:
            Dict: Trạng thái hệ thống
        """
        # Tính hiệu suất
        performance = self.trading_strategy.calculate_performance_metrics()
        
        # Đếm tín hiệu theo loại
        signal_counts = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        for signal in self.signal_history:
            action = signal.get('action', 'HOLD')
            if 'STRONG_' in action:
                action = action.replace('STRONG_', '')
            if action in signal_counts:
                signal_counts[action] += 1
        
        return {
            'active_positions': len(self.active_positions),
            'signal_history_count': len(self.signal_history),
            'win_rate': performance.get('win_rate', 0),
            'profit_factor': performance.get('profit_factor', 0),
            'signal_counts': signal_counts,
            'market_regimes': {s: self.trading_strategy.current_regime for s in self.account_config.get('symbols', ['BTCUSDT'])},
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

def main():
    """Hàm chính để test StrategyIntegration"""
    strategy = StrategyIntegration()
    
    # Chạy chu kỳ chiến thuật
    result = strategy.run_strategy_cycle()
    
    print("\n===== KẾT QUẢ CHU KỲ CHIẾN THUẬT =====")
    print(f"Thành công: {result['success']}")
    if 'message' in result:
        print(f"Thông báo: {result['message']}")
    
    if result['success']:
        print(f"Thời gian: {result['timestamp']}")
        print(f"Số phân tích: {result['analysis_count']}")
        print(f"Số vị thế đã đóng: {len(result['closed_positions'])}")
        print(f"Số giao dịch mới: {len(result['trade_results'])}")
    
    # Hiển thị trạng thái hệ thống
    status = strategy.get_system_status()
    
    print("\n===== TRẠNG THÁI HỆ THỐNG =====")
    print(f"Số vị thế đang mở: {status['active_positions']}")
    print(f"Số tín hiệu đã lưu: {status['signal_history_count']}")
    print(f"Tỷ lệ thắng: {status['win_rate']:.2f}%")
    print(f"Hệ số lợi nhuận: {status['profit_factor']:.2f}")
    
    print("\nPhân bố tín hiệu:")
    for action, count in status['signal_counts'].items():
        print(f"- {action}: {count}")
    
    print("\nChế độ thị trường:")
    for symbol, regime in status['market_regimes'].items():
        print(f"- {symbol}: {regime}")

if __name__ == "__main__":
    main()