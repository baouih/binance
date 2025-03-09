"""
Module cập nhật thị trường nâng cao
Cung cấp chức năng phân tích thị trường và gửi thông báo định kỳ
"""

import logging
import json
import os
import time
import threading
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from telegram_notifier import TelegramNotifier
from detailed_trade_notifications import DetailedTradeNotifications

# Thiết lập logging
logger = logging.getLogger('enhanced_market_updater')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# File handler
file_handler = logging.FileHandler('logs/enhanced_market_updater.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

class EnhancedMarketUpdater:
    """
    Lớp xử lý cập nhật thị trường nâng cao
    """
    
    def __init__(self, api_connector, data_processor, strategy_engine, telegram_config_path='configs/telegram/telegram_notification_config.json'):
        """
        Khởi tạo enhanced market updater
        
        Args:
            api_connector: Connector API của sàn giao dịch
            data_processor: Bộ xử lý dữ liệu
            strategy_engine: Engine chiến lược giao dịch
            telegram_config_path (str, optional): Đường dẫn đến file cấu hình Telegram
        """
        self.api_connector = api_connector
        self.data_processor = data_processor
        self.strategy_engine = strategy_engine
        
        # Tải cấu hình
        self.config = self._load_config()
        
        # Danh sách các cặp tiền điện tử cần theo dõi
        self.symbols = self.config.get('symbols', [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT', 
            'DOGEUSDT', 'XRPUSDT', 'DOTUSDT', 'AVAXUSDT', 'MATICUSDT',
            'LINKUSDT', 'UNIUSDT', 'ATOMUSDT', 'LTCUSDT'
        ])
        
        # Tạo thư mục lưu trữ
        self.data_dir = 'data'
        self.analysis_dir = 'market_analysis'
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.analysis_dir, exist_ok=True)
        
        # Khung thời gian (timeframe)
        self.timeframes = self.config.get('timeframes', ['1h', '4h', '1d'])
        
        # Tải cấu hình Telegram
        self.telegram_config = self._load_telegram_config(telegram_config_path)
        
        # Khởi tạo Telegram notifier
        if self.telegram_config.get('enabled', False):
            self.telegram = TelegramNotifier(config_path=telegram_config_path)
            logger.info("Đã kích hoạt thông báo Telegram cho cập nhật thị trường")
        else:
            self.telegram = None
            logger.warning("Thông báo Telegram bị tắt cho cập nhật thị trường")
        
        # Khởi tạo module thông báo chi tiết
        self.detailed_notifier = DetailedTradeNotifications(telegram_config_path)
        
        # Biến quản lý thread
        self.updating_active = False
        self.updating_thread = None
        
        # Thời gian cập nhật (giây)
        self.update_interval = self.config.get('update_interval', 60)
        
        # Thời gian báo cáo (giây)
        self.report_interval = self.config.get('report_interval', 3600)  # 1 giờ
        self.last_report_time = datetime.now()
        
        logger.info(f"Đã khởi tạo EnhancedMarketUpdater với {len(self.symbols)} cặp tiền và {len(self.timeframes)} khung thời gian")
    
    def _load_config(self):
        """
        Tải cấu hình từ file
        
        Returns:
            dict: Cấu hình
        """
        config_path = 'configs/market_updater_config.json'
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {config_path}")
                return config
            else:
                logger.warning(f"Không tìm thấy file cấu hình: {config_path}, sử dụng cấu hình mặc định")
                return {
                    'symbols': [
                        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT', 
                        'DOGEUSDT', 'XRPUSDT', 'DOTUSDT', 'AVAXUSDT', 'MATICUSDT',
                        'LINKUSDT', 'UNIUSDT', 'ATOMUSDT', 'LTCUSDT'
                    ],
                    'timeframes': ['1h', '4h', '1d'],
                    'update_interval': 60,
                    'report_interval': 3600,
                    'notification': {
                        'threshold_change': 3.0,  # Ngưỡng thay đổi giá (%) để thông báo
                        'threshold_volume': 50.0,  # Ngưỡng thay đổi khối lượng (%) để thông báo
                        'threshold_signal': 80.0   # Ngưỡng độ tin cậy tín hiệu (%) để thông báo
                    }
                }
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
            return {
                'symbols': ['BTCUSDT', 'ETHUSDT'],
                'timeframes': ['1h'],
                'update_interval': 60,
                'report_interval': 3600,
                'notification': {
                    'threshold_change': 3.0,
                    'threshold_volume': 50.0,
                    'threshold_signal': 80.0
                }
            }
    
    def _load_telegram_config(self, config_path):
        """
        Tải cấu hình Telegram
        
        Args:
            config_path (str): Đường dẫn tới file cấu hình
            
        Returns:
            dict: Cấu hình Telegram
        """
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình Telegram từ {config_path}")
                return config
            else:
                logger.warning(f"Không tìm thấy file cấu hình Telegram: {config_path}")
                return {'enabled': False}
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình Telegram: {str(e)}")
            return {'enabled': False}
    
    def update_market_data(self):
        """
        Cập nhật dữ liệu thị trường cho tất cả các cặp tiền
        
        Returns:
            dict: Dữ liệu thị trường đã cập nhật
        """
        market_data = {}
        
        for symbol in self.symbols:
            try:
                # Lấy giá hiện tại
                current_price = self.api_connector.get_current_price(symbol)
                
                if current_price is None:
                    logger.warning(f"Không lấy được giá hiện tại cho {symbol}")
                    continue
                
                # Lấy dữ liệu theo khung thời gian
                timeframe_data = {}
                for tf in self.timeframes:
                    # Lấy dữ liệu OHLCV
                    ohlcv = self.data_processor.get_candles(symbol, tf, limit=100)
                    
                    if ohlcv is None or len(ohlcv) < 20:
                        logger.warning(f"Không đủ dữ liệu OHLCV cho {symbol} trên khung {tf}")
                        continue
                    
                    # Lưu dữ liệu
                    timeframe_data[tf] = {
                        'ohlcv': ohlcv.to_dict('records')[-20:],  # Chỉ lấy 20 nến gần nhất
                        'last_close': float(ohlcv['close'].iloc[-1]),
                        'prev_close': float(ohlcv['close'].iloc[-2]),
                        'change_percent': float((ohlcv['close'].iloc[-1] / ohlcv['close'].iloc[-2] - 1) * 100),
                        'volume': float(ohlcv['volume'].iloc[-1]),
                        'avg_volume': float(ohlcv['volume'].iloc[-20:].mean()),
                        'high': float(ohlcv['high'].max()),
                        'low': float(ohlcv['low'].min()),
                        'volatility': float(ohlcv['high'].pct_change().abs().mean() * 100)
                    }
                
                # Tính toán các chỉ số
                analysis = self.strategy_engine.analyze_symbol(symbol)
                
                # Tổng hợp dữ liệu
                market_data[symbol] = {
                    'current_price': current_price,
                    'timeframes': timeframe_data,
                    'analysis': analysis,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                logger.info(f"Đã cập nhật dữ liệu thị trường cho {symbol}: {current_price:.2f} USDT")
                
            except Exception as e:
                logger.error(f"Lỗi khi cập nhật dữ liệu cho {symbol}: {str(e)}")
        
        return market_data
    
    def analyze_market_regime(self, market_data):
        """
        Phân tích chế độ thị trường
        
        Args:
            market_data (dict): Dữ liệu thị trường
            
        Returns:
            dict: Kết quả phân tích chế độ thị trường
        """
        try:
            if not market_data or 'BTCUSDT' not in market_data:
                logger.warning("Không có đủ dữ liệu để phân tích chế độ thị trường")
                return {
                    'regime': 'unknown',
                    'trend': 'neutral',
                    'volatility': 0,
                    'strength': 0
                }
            
            # Sử dụng BTC làm đại diện cho thị trường
            btc_data = market_data['BTCUSDT']
            
            # Kiểm tra xu hướng dựa trên dữ liệu 1d
            if '1d' in btc_data['timeframes']:
                day_data = btc_data['timeframes']['1d']
                closes = [candle['close'] for candle in day_data['ohlcv']]
                
                # Tính EMA 20
                ema20 = np.array(closes).mean()  # Đơn giản hóa, chỉ dùng mean
                
                current_price = btc_data['current_price']
                
                # Xác định xu hướng
                if current_price > ema20 * 1.05:
                    trend = 'bullish'
                    strength = min((current_price / ema20 - 1) * 100, 100)
                elif current_price < ema20 * 0.95:
                    trend = 'bearish'
                    strength = min((1 - current_price / ema20) * 100, 100)
                else:
                    trend = 'neutral'
                    strength = 0
                
                # Tính độ biến động
                volatility = day_data['volatility']
                
                # Xác định chế độ thị trường
                if volatility > 5:  # Độ biến động cao
                    if trend == 'bullish':
                        regime = 'bull_volatile'
                    elif trend == 'bearish':
                        regime = 'bear_volatile'
                    else:
                        regime = 'range_volatile'
                else:  # Độ biến động thấp
                    if trend == 'bullish':
                        regime = 'bull_quiet'
                    elif trend == 'bearish':
                        regime = 'bear_quiet'
                    else:
                        regime = 'range_bound'
            else:
                # Dữ liệu mặc định nếu không có khung 1d
                trend = 'neutral'
                volatility = 0
                strength = 0
                regime = 'unknown'
            
            return {
                'regime': regime,
                'trend': trend,
                'volatility': volatility,
                'strength': strength
            }
        except Exception as e:
            logger.error(f"Lỗi khi phân tích chế độ thị trường: {str(e)}")
            return {
                'regime': 'unknown',
                'trend': 'neutral',
                'volatility': 0,
                'strength': 0
            }
    
    def generate_market_summary(self, market_data, market_regime):
        """
        Tạo tóm tắt thị trường
        
        Args:
            market_data (dict): Dữ liệu thị trường
            market_regime (dict): Thông tin chế độ thị trường
            
        Returns:
            dict: Tóm tắt thị trường
        """
        try:
            # Thông tin tổng quan
            summary = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'market_regime': market_regime,
                'coins': []
            }
            
            # Thông tin từng coin
            for symbol, data in market_data.items():
                if not data or 'analysis' not in data:
                    continue
                
                analysis = data['analysis']
                
                # Lấy giá và thay đổi giá
                current_price = data['current_price']
                
                # Lấy khung giờ 1h nếu có
                if '1h' in data['timeframes']:
                    change_percent = data['timeframes']['1h']['change_percent']
                    volatility = data['timeframes']['1h']['volatility']
                else:
                    change_percent = 0
                    volatility = 0
                
                # Tạo thông tin coin
                coin_info = {
                    'symbol': symbol,
                    'price': current_price,
                    'change_percent': change_percent,
                    'volatility': volatility,
                    'signal': analysis.get('signal', 'NEUTRAL'),
                    'strength': analysis.get('strength', 0),
                    'confidence': analysis.get('confidence', 0),
                    'indicators': analysis.get('indicators', {})
                }
                
                summary['coins'].append(coin_info)
            
            # Sắp xếp danh sách coin theo độ tin cậy
            summary['coins'].sort(key=lambda x: x['confidence'], reverse=True)
            
            # Thêm một số thông tin bổ sung
            summary['total_coins'] = len(summary['coins'])
            summary['market_trend'] = market_regime['trend']
            summary['market_volatility'] = market_regime['volatility']
            
            # Thêm các chỉ số thống kê
            bullish_count = sum(1 for coin in summary['coins'] if coin['signal'] == 'BUY')
            bearish_count = sum(1 for coin in summary['coins'] if coin['signal'] == 'SELL')
            neutral_count = sum(1 for coin in summary['coins'] if coin['signal'] == 'NEUTRAL')
            
            summary['statistics'] = {
                'bullish_percent': bullish_count / len(summary['coins']) * 100 if summary['coins'] else 0,
                'bearish_percent': bearish_count / len(summary['coins']) * 100 if summary['coins'] else 0,
                'neutral_percent': neutral_count / len(summary['coins']) * 100 if summary['coins'] else 0
            }
            
            return summary
        except Exception as e:
            logger.error(f"Lỗi khi tạo tóm tắt thị trường: {str(e)}")
            return {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'market_regime': market_regime,
                'coins': [],
                'error': str(e)
            }
    
    def save_market_analysis(self, summary):
        """
        Lưu phân tích thị trường vào file
        
        Args:
            summary (dict): Tóm tắt thị trường
            
        Returns:
            bool: True nếu lưu thành công
        """
        try:
            # Lưu tóm tắt chung
            summary_file = os.path.join(self.analysis_dir, 'market_analysis.json')
            
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"Đã lưu phân tích thị trường vào {summary_file}")
            
            # Lưu phân tích riêng cho BTC
            if any(coin['symbol'] == 'BTCUSDT' for coin in summary['coins']):
                btc_summary = next(coin for coin in summary['coins'] if coin['symbol'] == 'BTCUSDT')
                btc_summary_file = os.path.join(self.analysis_dir, 'market_analysis_btcusdt.json')
                
                with open(btc_summary_file, 'w') as f:
                    json.dump({**btc_summary, 'market_regime': summary['market_regime']}, f, indent=2)
                
                logger.info(f"Đã lưu phân tích BTCUSDT vào {btc_summary_file}")
            
            # Lưu phân tích riêng cho ETH
            if any(coin['symbol'] == 'ETHUSDT' for coin in summary['coins']):
                eth_summary = next(coin for coin in summary['coins'] if coin['symbol'] == 'ETHUSDT')
                eth_summary_file = os.path.join(self.analysis_dir, 'market_analysis_ethusdt.json')
                
                with open(eth_summary_file, 'w') as f:
                    json.dump({**eth_summary, 'market_regime': summary['market_regime']}, f, indent=2)
                
                logger.info(f"Đã lưu phân tích ETHUSDT vào {eth_summary_file}")
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu phân tích thị trường: {str(e)}")
            return False
    
    def should_send_notification(self, summary):
        """
        Quyết định xem có nên gửi thông báo hay không
        
        Args:
            summary (dict): Tóm tắt thị trường
            
        Returns:
            tuple: (bool, str) - Có nên gửi không và lý do
        """
        try:
            # Lấy ngưỡng từ cấu hình
            thresholds = self.config.get('notification', {})
            threshold_change = thresholds.get('threshold_change', 3.0)
            threshold_signal = thresholds.get('threshold_signal', 80.0)
            
            # Kiểm tra thời gian
            now = datetime.now()
            if (now - self.last_report_time).total_seconds() >= self.report_interval:
                return True, "Báo cáo định kỳ"
            
            # Kiểm tra BTC
            btc_info = next((coin for coin in summary['coins'] if coin['symbol'] == 'BTCUSDT'), None)
            if btc_info and abs(btc_info['change_percent']) >= threshold_change:
                return True, f"BTC thay đổi {btc_info['change_percent']:.2f}%"
            
            # Kiểm tra tín hiệu mạnh
            strong_signals = [coin for coin in summary['coins'] if coin['confidence'] >= threshold_signal]
            if strong_signals:
                return True, f"Có {len(strong_signals)} tín hiệu mạnh"
            
            # Kiểm tra chế độ thị trường thay đổi
            # (Cần lưu trạng thái trước đó để so sánh)
            
            return False, "Không có thông tin nổi bật"
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra điều kiện thông báo: {str(e)}")
            return False, f"Lỗi: {str(e)}"
    
    def format_market_notification(self, summary):
        """
        Format thông báo thị trường cho Telegram
        
        Args:
            summary (dict): Tóm tắt thị trường
            
        Returns:
            str: Thông báo đã format
        """
        try:
            # Lấy thông tin chế độ thị trường
            market_regime = summary['market_regime']
            market_trend = market_regime['trend']
            market_volatility = market_regime['volatility']
            
            # Emoji dựa trên xu hướng thị trường
            if market_trend == 'bullish':
                trend_emoji = "📈"
                trend_text = "TĂNG"
            elif market_trend == 'bearish':
                trend_emoji = "📉"
                trend_text = "GIẢM"
            else:
                trend_emoji = "📊"
                trend_text = "TRUNG LẬP"
            
            # Tạo thông báo
            notification = (
                f"{trend_emoji} *PHÂN TÍCH THỊ TRƯỜNG*\n\n"
                f"📊 *Xu hướng chung:* `{trend_text}`\n"
                f"🌡️ *Biến động:* `{market_volatility:.2f}%`\n\n"
                f"*Top 5 coin tiềm năng:*\n"
            )
            
            # Thêm thông tin về các coin
            for i, coin in enumerate(summary['coins'][:5], 1):
                symbol = coin['symbol']
                signal = coin['signal']
                confidence = coin['confidence']
                change = coin['change_percent']
                
                # Emoji dựa trên tín hiệu
                if signal == 'BUY':
                    signal_emoji = "🟢"
                elif signal == 'SELL':
                    signal_emoji = "🔴"
                else:
                    signal_emoji = "⚪"
                
                # Emoji thay đổi giá
                if change > 0:
                    change_emoji = "↗️"
                elif change < 0:
                    change_emoji = "↘️"
                else:
                    change_emoji = "↔️"
                
                notification += f"{i}. {signal_emoji} `{symbol}`: {confidence:.1f}% tin cậy {change_emoji} {change:+.2f}%\n"
            
            notification += f"\n⏰ *Thời gian phân tích:* `{summary['timestamp']}`\n\n"
            
            # Thêm gợi ý
            notification += "_💡 Tiếp tục theo dõi thị trường và chờ đợi cơ hội giao dịch tiếp theo._"
            
            return notification
        except Exception as e:
            logger.error(f"Lỗi khi format thông báo thị trường: {str(e)}")
            return f"*⚠️ LỖI KHI TẠO THÔNG BÁO THỊ TRƯỜNG*\n\n{str(e)}"
    
    def send_market_notification(self, summary):
        """
        Gửi thông báo thị trường qua Telegram
        
        Args:
            summary (dict): Tóm tắt thị trường
            
        Returns:
            bool: True nếu gửi thành công
        """
        if not self.telegram or not self.telegram_config.get('enabled', False):
            logger.warning("Telegram không được bật, không thể gửi thông báo")
            return False
        
        try:
            # Kiểm tra xem có nên gửi thông báo không
            should_send, reason = self.should_send_notification(summary)
            
            if not should_send:
                logger.info(f"Bỏ qua thông báo thị trường: {reason}")
                return False
            
            # Format thông báo
            message = self.format_market_notification(summary)
            
            # Gửi thông báo
            success = self.telegram.send_message(message, parse_mode='Markdown')
            
            if success:
                logger.info(f"Đã gửi thông báo thị trường qua Telegram: {reason}")
                self.last_report_time = datetime.now()
                
                # Gửi thông báo chi tiết
                self.detailed_notifier.notify_market_analysis(summary)
                
                return True
            else:
                logger.error("Lỗi khi gửi thông báo thị trường qua Telegram")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo thị trường: {str(e)}")
            return False
    
    def update_market(self):
        """
        Cập nhật thị trường và gửi thông báo
        
        Returns:
            dict: Kết quả cập nhật
        """
        try:
            # Cập nhật dữ liệu thị trường
            market_data = self.update_market_data()
            
            # Phân tích chế độ thị trường
            market_regime = self.analyze_market_regime(market_data)
            
            # Tạo tóm tắt thị trường
            summary = self.generate_market_summary(market_data, market_regime)
            
            # Lưu phân tích
            self.save_market_analysis(summary)
            
            # Gửi thông báo
            self.send_market_notification(summary)
            
            return {
                'success': True,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'coins': len(market_data),
                'summary': summary
            }
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật thị trường: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    
    def start_updating(self):
        """
        Bắt đầu thread cập nhật thị trường
        
        Returns:
            bool: True nếu bắt đầu thành công
        """
        if self.updating_active:
            logger.warning("Thread cập nhật đã đang chạy")
            return False
        
        self.updating_active = True
        self.updating_thread = threading.Thread(target=self._updating_worker)
        self.updating_thread.daemon = True
        self.updating_thread.start()
        
        logger.info("Đã bắt đầu thread cập nhật thị trường")
        return True
    
    def stop_updating(self):
        """
        Dừng thread cập nhật thị trường
        
        Returns:
            bool: True nếu dừng thành công
        """
        if not self.updating_active:
            logger.warning("Thread cập nhật không chạy")
            return False
        
        self.updating_active = False
        
        # Chờ thread kết thúc (tối đa 5 giây)
        if self.updating_thread and self.updating_thread.is_alive():
            self.updating_thread.join(5)
        
        logger.info("Đã dừng thread cập nhật thị trường")
        return True
    
    def _updating_worker(self):
        """
        Worker function cho thread cập nhật thị trường
        """
        logger.info("Thread cập nhật thị trường bắt đầu")
        
        while self.updating_active:
            try:
                self.update_market()
            except Exception as e:
                logger.error(f"Lỗi trong thread cập nhật: {str(e)}")
            
            # Ngủ trước khi chạy lại
            time.sleep(self.update_interval)
        
        logger.info("Thread cập nhật thị trường kết thúc")


# Hàm để sử dụng module này độc lập
def start_market_updater(api_connector, data_processor, strategy_engine):
    """
    Khởi động updater thị trường độc lập
    
    Args:
        api_connector: API connector
        data_processor: Bộ xử lý dữ liệu
        strategy_engine: Engine chiến lược giao dịch
        
    Returns:
        EnhancedMarketUpdater: Instance của updater
    """
    updater = EnhancedMarketUpdater(api_connector, data_processor, strategy_engine)
    updater.start_updating()
    
    return updater