"""
Module giám sát vị thế giao dịch
Cung cấp các công cụ để giám sát và quản lý các vị thế giao dịch tiền điện tử đang hoạt động
"""

import logging
import json
import os
import time
from datetime import datetime, timedelta
import threading
import pandas as pd
import numpy as np
from telegram_notifier import TelegramNotifier
from detailed_trade_notifications import DetailedTradeNotifications

# Thiết lập logging
logger = logging.getLogger('position_monitoring')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# File handler
file_handler = logging.FileHandler('logs/position_monitoring.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

class PositionMonitor:
    """
    Lớp xử lý giám sát và quản lý vị thế
    """
    
    def __init__(self, api_connector, telegram_config_path='telegram_config.json'):
        """
        Khởi tạo monitor
        
        Args:
            api_connector: Connector API cho sàn giao dịch
            telegram_config_path (str, optional): Đường dẫn tới file cấu hình Telegram
        """
        self.api_connector = api_connector
        self.positions_file = 'active_positions.json'
        self.history_file = 'position_history.json'
        self.analysis_dir = 'position_analysis'
        
        # Đảm bảo thư mục tồn tại
        os.makedirs(self.analysis_dir, exist_ok=True)
        
        # Thông báo chi tiết
        self.notifier = DetailedTradeNotifications(telegram_config_path)
        
        # Tải cấu hình Telegram
        self.telegram_config = self._load_telegram_config(telegram_config_path)
        
        # Khởi tạo Telegram notifier
        if self.telegram_config.get('enabled', False):
            self.telegram = TelegramNotifier(
                token=self.telegram_config.get('bot_token', ''),
                chat_id=self.telegram_config.get('chat_id', '')
            )
        else:
            self.telegram = None
        
        # Biến quản lý thread
        self.monitoring_active = False
        self.monitoring_thread = None
        
        # Thời gian kiểm tra vị thế (giây)
        self.check_interval = 10
        
        logger.info("Đã khởi tạo PositionMonitor")
    
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
    
    def load_active_positions(self):
        """
        Tải danh sách vị thế đang hoạt động
        
        Returns:
            dict: Danh sách vị thế
        """
        try:
            if os.path.exists(self.positions_file):
                with open(self.positions_file, 'r') as f:
                    positions = json.load(f)
                logger.info(f"Đã tải {len(positions)} vị thế đang hoạt động từ {self.positions_file}")
                return positions
            else:
                logger.warning(f"Không tìm thấy file vị thế: {self.positions_file}")
                return {}
        except Exception as e:
            logger.error(f"Lỗi khi tải vị thế: {str(e)}")
            return {}
    
    def save_active_positions(self, positions):
        """
        Lưu danh sách vị thế đang hoạt động
        
        Args:
            positions (dict): Danh sách vị thế
            
        Returns:
            bool: True nếu lưu thành công
        """
        try:
            with open(self.positions_file, 'w') as f:
                json.dump(positions, f, indent=4)
            logger.info(f"Đã lưu {len(positions)} vị thế vào {self.positions_file}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu vị thế: {str(e)}")
            return False
    
    def load_position_history(self):
        """
        Tải lịch sử vị thế
        
        Returns:
            list: Lịch sử vị thế
        """
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
                logger.info(f"Đã tải {len(history)} vị thế từ lịch sử")
                return history
            else:
                logger.warning(f"Không tìm thấy file lịch sử: {self.history_file}")
                return []
        except Exception as e:
            logger.error(f"Lỗi khi tải lịch sử vị thế: {str(e)}")
            return []
    
    def save_position_history(self, history):
        """
        Lưu lịch sử vị thế
        
        Args:
            history (list): Lịch sử vị thế
            
        Returns:
            bool: True nếu lưu thành công
        """
        try:
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=4)
            logger.info(f"Đã lưu {len(history)} vị thế vào lịch sử")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu lịch sử vị thế: {str(e)}")
            return False
    
    def analyze_position_profit(self, entry_price, current_price, position_size, side, leverage=1):
        """
        Phân tích lợi nhuận của vị thế
        
        Args:
            entry_price (float): Giá vào lệnh
            current_price (float): Giá hiện tại
            position_size (float): Kích thước vị thế
            side (str): Hướng vị thế (LONG hoặc SHORT)
            leverage (int, optional): Đòn bẩy, mặc định là 1
        
        Returns:
            dict: Thông tin lợi nhuận
        """
        try:
            # Tính toán lợi nhuận
            if side == 'LONG':
                profit_percent = (current_price - entry_price) / entry_price * 100 * leverage
                profit_usdt = (current_price - entry_price) * position_size * leverage
            else:  # SHORT
                profit_percent = (entry_price - current_price) / entry_price * 100 * leverage
                profit_usdt = (entry_price - current_price) * position_size * leverage
            
            return {
                'profit_percent': profit_percent,
                'profit_usdt': profit_usdt,
                'current_price': current_price,
                'entry_price': entry_price,
                'leverage': leverage,
                'roi': profit_percent  # Tỷ suất lợi nhuận
            }
        except Exception as e:
            logger.error(f"Lỗi khi tính toán lợi nhuận: {str(e)}")
            return {
                'profit_percent': 0,
                'profit_usdt': 0,
                'current_price': current_price,
                'entry_price': entry_price,
                'leverage': leverage,
                'roi': 0
            }
    
    def check_stop_loss_hit(self, position, current_price):
        """
        Kiểm tra xem stop loss có bị kích hoạt không
        
        Args:
            position (dict): Thông tin vị thế
            current_price (float): Giá hiện tại
        
        Returns:
            bool: True nếu SL bị kích hoạt
        """
        try:
            side = position.get('side', 'LONG')
            stop_loss = float(position.get('stop_loss', 0))
            
            if stop_loss == 0:
                return False
            
            if side == 'LONG' and current_price <= stop_loss:
                return True
            elif side == 'SHORT' and current_price >= stop_loss:
                return True
            
            return False
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra stop loss: {str(e)}")
            return False
    
    def check_take_profit_hit(self, position, current_price):
        """
        Kiểm tra xem take profit có bị kích hoạt không
        
        Args:
            position (dict): Thông tin vị thế
            current_price (float): Giá hiện tại
        
        Returns:
            bool: True nếu TP bị kích hoạt
        """
        try:
            side = position.get('side', 'LONG')
            take_profit = float(position.get('take_profit', 0))
            
            if take_profit == 0:
                return False
            
            if side == 'LONG' and current_price >= take_profit:
                return True
            elif side == 'SHORT' and current_price <= take_profit:
                return True
            
            return False
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra take profit: {str(e)}")
            return False
    
    def update_trailing_stop(self, symbol, position, current_price):
        """
        Cập nhật trailing stop cho vị thế
        
        Args:
            symbol (str): Ký hiệu cặp giao dịch
            position (dict): Thông tin vị thế
            current_price (float): Giá hiện tại
        
        Returns:
            dict: Vị thế đã cập nhật
        """
        try:
            # Kiểm tra xem trailing stop có được kích hoạt không
            if 'trailing_activation' not in position:
                return position
            
            side = position.get('side', 'LONG')
            activation_price = float(position.get('trailing_activation', 0))
            callback_rate = float(position.get('trailing_callback', 1.0))
            
            # Kiểm tra xem giá đã đạt đến mức kích hoạt chưa
            if side == 'LONG' and current_price >= activation_price:
                # Tính toán stop loss mới dựa trên callback
                new_stop_loss = current_price * (1 - callback_rate / 100)
                
                # Chỉ cập nhật nếu stop loss mới cao hơn stop loss hiện tại
                if new_stop_loss > float(position.get('stop_loss', 0)):
                    position['stop_loss'] = new_stop_loss
                    logger.info(f"Đã cập nhật trailing stop cho {symbol} LONG: {new_stop_loss:.2f} (giá hiện tại: {current_price:.2f})")
                    
                    # Cập nhật lệnh stop loss trên sàn nếu có trailing_order_id
                    if 'trailing_order_id' in position:
                        try:
                            order_id = position['trailing_order_id']
                            self.api_connector.update_stop_loss_order(symbol, order_id, new_stop_loss)
                            logger.info(f"Đã cập nhật lệnh trailing stop trên sàn cho {symbol}: {new_stop_loss:.2f}")
                        except Exception as e:
                            logger.error(f"Lỗi khi cập nhật lệnh trailing stop trên sàn: {str(e)}")
            
            elif side == 'SHORT' and current_price <= activation_price:
                # Tính toán stop loss mới dựa trên callback
                new_stop_loss = current_price * (1 + callback_rate / 100)
                
                # Chỉ cập nhật nếu stop loss mới thấp hơn stop loss hiện tại
                if new_stop_loss < float(position.get('stop_loss', 0)) or float(position.get('stop_loss', 0)) == 0:
                    position['stop_loss'] = new_stop_loss
                    logger.info(f"Đã cập nhật trailing stop cho {symbol} SHORT: {new_stop_loss:.2f} (giá hiện tại: {current_price:.2f})")
                    
                    # Cập nhật lệnh stop loss trên sàn nếu có trailing_order_id
                    if 'trailing_order_id' in position:
                        try:
                            order_id = position['trailing_order_id']
                            self.api_connector.update_stop_loss_order(symbol, order_id, new_stop_loss)
                            logger.info(f"Đã cập nhật lệnh trailing stop trên sàn cho {symbol}: {new_stop_loss:.2f}")
                        except Exception as e:
                            logger.error(f"Lỗi khi cập nhật lệnh trailing stop trên sàn: {str(e)}")
            
            return position
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật trailing stop: {str(e)}")
            return position
    
    def check_partial_take_profit(self, symbol, position, current_price):
        """
        Kiểm tra và thực hiện take profit từng phần
        
        Args:
            symbol (str): Ký hiệu cặp giao dịch
            position (dict): Thông tin vị thế
            current_price (float): Giá hiện tại
        
        Returns:
            dict: Vị thế đã cập nhật
        """
        try:
            if 'partial_tp' not in position:
                return position
            
            side = position.get('side', 'LONG')
            
            # Sắp xếp danh sách partial TP theo giá (gần nhất đến xa nhất)
            partial_tps = sorted(position['partial_tp'], 
                                key=lambda x: x['price'],
                                reverse=(side != 'LONG'))
            
            for i, tp in enumerate(partial_tps):
                price = float(tp['price'])
                percent = float(tp['percent'])
                quantity = float(tp['quantity'])
                
                is_triggered = False
                
                # Kiểm tra xem giá đã đạt đến mức TP chưa
                if side == 'LONG' and current_price >= price:
                    is_triggered = True
                elif side == 'SHORT' and current_price <= price:
                    is_triggered = True
                
                # Nếu đã đạt đến mức TP và chưa thực hiện
                if is_triggered and not tp.get('executed', False):
                    # Thực hiện lệnh take profit từng phần
                    try:
                        # Cập nhật trạng thái executed
                        position['partial_tp'][i]['executed'] = True
                        position['partial_tp'][i]['executed_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        position['partial_tp'][i]['executed_price'] = current_price
                        
                        logger.info(f"Đã kích hoạt TP từng phần cho {symbol}: {percent}% tại giá {current_price:.2f}")
                        
                        # Gửi thông báo
                        profit_data = self.analyze_position_profit(
                            entry_price=float(position.get('entry_price', 0)),
                            current_price=current_price,
                            position_size=quantity,
                            side=side,
                            leverage=float(position.get('leverage', 1))
                        )
                        
                        exit_data = {
                            'symbol': symbol,
                            'side': side,
                            'exit_price': current_price,
                            'quantity': quantity,
                            'profit_amount': profit_data['profit_usdt'],
                            'profit_percent': profit_data['profit_percent'],
                            'exit_reason': f'Partial TP {percent}%',
                            'trade_id': f"{symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                        }
                        
                        # Gửi thông báo chi tiết
                        self.notifier.notify_exit(exit_data)
                        
                    except Exception as e:
                        logger.error(f"Lỗi khi thực hiện TP từng phần: {str(e)}")
            
            return position
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra TP từng phần: {str(e)}")
            return position
    
    def analyze_positions(self):
        """
        Phân tích tất cả các vị thế đang hoạt động
        
        Returns:
            dict: Thông tin phân tích
        """
        positions = self.load_active_positions()
        if not positions:
            logger.info("Không có vị thế đang hoạt động")
            return {'positions': [], 'count': 0, 'total_profit': 0}
        
        position_analysis = []
        total_profit = 0
        
        for symbol, position in positions.items():
            try:
                # Lấy giá hiện tại
                current_price = self.api_connector.get_current_price(symbol)
                
                if current_price is None:
                    logger.warning(f"Không lấy được giá hiện tại cho {symbol}")
                    continue
                
                # Cập nhật trailing stop nếu có
                position = self.update_trailing_stop(symbol, position, current_price)
                
                # Kiểm tra partial take profit
                position = self.check_partial_take_profit(symbol, position, current_price)
                
                # Phân tích lợi nhuận
                side = position.get('side', 'LONG')
                entry_price = float(position.get('entry_price', 0))
                position_size = float(position.get('position_size', 0))
                leverage = float(position.get('leverage', 1))
                
                profit_data = self.analyze_position_profit(
                    entry_price=entry_price,
                    current_price=current_price,
                    position_size=position_size,
                    side=side,
                    leverage=leverage
                )
                
                # Kiểm tra stop loss và take profit
                is_sl_hit = self.check_stop_loss_hit(position, current_price)
                is_tp_hit = self.check_take_profit_hit(position, current_price)
                
                position_info = {
                    'symbol': symbol,
                    'side': side,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'position_size': position_size,
                    'leverage': leverage,
                    'profit_percent': profit_data['profit_percent'],
                    'profit_usdt': profit_data['profit_usdt'],
                    'stop_loss': float(position.get('stop_loss', 0)),
                    'take_profit': float(position.get('take_profit', 0)),
                    'entry_time': position.get('entry_time', ''),
                    'duration': self._calculate_duration(position.get('entry_time', '')),
                    'is_sl_hit': is_sl_hit,
                    'is_tp_hit': is_tp_hit
                }
                
                position_analysis.append(position_info)
                total_profit += profit_data['profit_usdt']
                
                # Cập nhật vị thế
                positions[symbol] = position
                
                logger.debug(f"Đã phân tích vị thế {symbol}: P/L={profit_data['profit_percent']:.2f}%, {profit_data['profit_usdt']:.2f} USDT")
                
            except Exception as e:
                logger.error(f"Lỗi khi phân tích vị thế {symbol}: {str(e)}")
        
        # Lưu lại vị thế đã cập nhật
        self.save_active_positions(positions)
        
        return {
            'positions': position_analysis,
            'count': len(position_analysis),
            'total_profit': total_profit,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _calculate_duration(self, entry_time_str):
        """
        Tính thời gian giữ vị thế
        
        Args:
            entry_time_str (str): Thời gian vào lệnh (format %Y-%m-%d %H:%M:%S)
            
        Returns:
            str: Thời gian giữ vị thế theo định dạng dễ đọc
        """
        try:
            if not entry_time_str:
                return "Unknown"
            
            entry_time = datetime.strptime(entry_time_str, '%Y-%m-%d %H:%M:%S')
            now = datetime.now()
            
            duration = now - entry_time
            
            days = duration.days
            hours, remainder = divmod(duration.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m {seconds}s"
        except Exception as e:
            logger.error(f"Lỗi khi tính thời gian giữ vị thế: {str(e)}")
            return "Unknown"
    
    def generate_positions_report(self):
        """
        Tạo báo cáo tổng quan về vị thế
        
        Returns:
            str: Báo cáo dạng văn bản
        """
        analysis = self.analyze_positions()
        positions = analysis['positions']
        
        if not positions:
            return "📊 *BÁO CÁO VỊ THẾ*\n\nKhông có vị thế đang hoạt động"
        
        # Sắp xếp vị thế theo lợi nhuận
        positions.sort(key=lambda x: x['profit_percent'], reverse=True)
        
        report = "📊 *BÁO CÁO VỊ THẾ ĐANG HOẠT ĐỘNG*\n\n"
        report += f"🕒 *Thời gian:* `{analysis['timestamp']}`\n"
        report += f"📈 *Tổng vị thế:* `{analysis['count']}`\n"
        report += f"💰 *Tổng lợi nhuận:* `{analysis['total_profit']:.2f} USDT`\n\n"
        
        # Chi tiết từng vị thế
        for i, pos in enumerate(positions, 1):
            symbol = pos['symbol']
            side = pos['side']
            profit_percent = pos['profit_percent']
            profit_usdt = pos['profit_usdt']
            duration = pos['duration']
            
            # Emoji dựa vào lợi nhuận và hướng của vị thế
            if profit_percent > 0:
                emoji = "✅"
            else:
                emoji = "❌"
            
            # Biểu tượng hướng vị thế
            if side == 'LONG':
                direction_emoji = "🟢"
            else:
                direction_emoji = "🔴"
            
            report += f"{i}. {emoji} {direction_emoji} *{symbol}*: "
            report += f"`{profit_percent:+.2f}%` (`{profit_usdt:+.2f} USDT`) - {duration}\n"
        
        return report
    
    def send_positions_report(self):
        """
        Gửi báo cáo vị thế qua Telegram
        
        Returns:
            bool: True nếu gửi thành công
        """
        if not self.telegram or not self.telegram_config.get('enabled', False):
            logger.warning("Telegram không được bật, không thể gửi báo cáo")
            return False
        
        try:
            report = self.generate_positions_report()
            success = self.telegram.send_message(report, parse_mode='Markdown')
            
            if success:
                logger.info("Đã gửi báo cáo vị thế qua Telegram")
                return True
            else:
                logger.error("Lỗi khi gửi báo cáo vị thế qua Telegram")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi báo cáo vị thế: {str(e)}")
            return False
    
    def close_all_positions(self, reason="Thực hiện lệnh đóng toàn bộ vị thế"):
        """
        Đóng tất cả các vị thế
        
        Args:
            reason (str, optional): Lý do đóng vị thế
            
        Returns:
            dict: Kết quả đóng vị thế
        """
        positions = self.load_active_positions()
        if not positions:
            logger.info("Không có vị thế đang hoạt động để đóng")
            return {'success': True, 'closed': 0, 'message': "Không có vị thế để đóng"}
        
        closed_count = 0
        failed_positions = []
        
        for symbol, position in positions.items():
            try:
                logger.info(f"Đang đóng vị thế {symbol}...")
                
                # Lấy thông tin cần thiết
                side = position.get('side', 'LONG')
                position_size = float(position.get('position_size', 0))
                
                # Lấy giá hiện tại
                current_price = self.api_connector.get_current_price(symbol)
                
                if current_price is None:
                    logger.warning(f"Không lấy được giá hiện tại cho {symbol}, không thể đóng vị thế")
                    failed_positions.append(symbol)
                    continue
                
                # Phân tích lợi nhuận trước khi đóng
                profit_data = self.analyze_position_profit(
                    entry_price=float(position.get('entry_price', 0)),
                    current_price=current_price,
                    position_size=position_size,
                    side=side,
                    leverage=float(position.get('leverage', 1))
                )
                
                # Thực hiện đóng vị thế
                close_side = "SELL" if side == "LONG" else "BUY"
                
                # Chuẩn bị thông báo
                exit_data = {
                    'symbol': symbol,
                    'side': side,
                    'exit_price': current_price,
                    'quantity': position_size,
                    'profit_amount': profit_data['profit_usdt'],
                    'profit_percent': profit_data['profit_percent'],
                    'exit_reason': reason,
                    'trade_id': f"{symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                }
                
                # Gửi thông báo chi tiết
                self.notifier.notify_exit(exit_data)
                
                # Tăng số lượng đã đóng
                closed_count += 1
                
                logger.info(f"Đã đóng vị thế {symbol} tại {current_price:.2f} với P/L={profit_data['profit_percent']:.2f}%")
                
            except Exception as e:
                logger.error(f"Lỗi khi đóng vị thế {symbol}: {str(e)}")
                failed_positions.append(symbol)
        
        # Lưu lịch sử
        if closed_count > 0:
            history = self.load_position_history()
            history.append({
                'action': 'close_all',
                'reason': reason,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'closed_count': closed_count,
                'failed': failed_positions
            })
            self.save_position_history(history)
        
        # Xóa active_positions.json nếu đóng thành công tất cả
        if not failed_positions and closed_count > 0:
            try:
                with open(self.positions_file, 'w') as f:
                    json.dump({}, f)
                logger.info("Đã xóa file active_positions.json sau khi đóng tất cả vị thế")
            except Exception as e:
                logger.error(f"Lỗi khi xóa file active_positions.json: {str(e)}")
        
        return {
            'success': len(failed_positions) == 0,
            'closed': closed_count,
            'failed': failed_positions,
            'message': f"Đã đóng {closed_count}/{len(positions)} vị thế" + (
                f", {len(failed_positions)} vị thế lỗi" if failed_positions else ""
            )
        }
    
    def start_monitoring(self):
        """
        Bắt đầu thread giám sát vị thế
        
        Returns:
            bool: True nếu bắt đầu thành công
        """
        if self.monitoring_active:
            logger.warning("Thread giám sát đã đang chạy")
            return False
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_worker)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        logger.info("Đã bắt đầu thread giám sát vị thế")
        return True
    
    def stop_monitoring(self):
        """
        Dừng thread giám sát vị thế
        
        Returns:
            bool: True nếu dừng thành công
        """
        if not self.monitoring_active:
            logger.warning("Thread giám sát không chạy")
            return False
        
        self.monitoring_active = False
        
        # Chờ thread kết thúc (tối đa 5 giây)
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(5)
        
        logger.info("Đã dừng thread giám sát vị thế")
        return True
    
    def _monitoring_worker(self):
        """
        Worker function cho thread giám sát vị thế
        """
        logger.info("Thread giám sát vị thế bắt đầu")
        
        while self.monitoring_active:
            try:
                # Phân tích vị thế
                analysis = self.analyze_positions()
                
                # Kiểm tra các vị thế đã đạt stop loss hoặc take profit
                closed_positions = []
                
                for pos in analysis['positions']:
                    if pos['is_sl_hit'] or pos['is_tp_hit']:
                        symbol = pos['symbol']
                        logger.info(f"Vị thế {symbol} đã đạt {'SL' if pos['is_sl_hit'] else 'TP'}")
                        closed_positions.append(symbol)
                
                # Nếu có vị thế đã đóng, cập nhật active_positions.json
                if closed_positions:
                    active_positions = self.load_active_positions()
                    
                    for symbol in closed_positions:
                        if symbol in active_positions:
                            del active_positions[symbol]
                    
                    self.save_active_positions(active_positions)
                    logger.info(f"Đã xóa {len(closed_positions)} vị thế đã đóng khỏi active_positions.json")
                
                # Lưu phân tích định kỳ
                if len(analysis['positions']) > 0:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    analysis_file = os.path.join(self.analysis_dir, f'position_analysis_{timestamp}.json')
                    
                    with open(analysis_file, 'w') as f:
                        json.dump(analysis, f, indent=4)
                    
                    logger.debug(f"Đã lưu phân tích vị thế vào {analysis_file}")
                
                # Gửi báo cáo định kỳ nếu được cấu hình
                now = datetime.now()
                if now.minute % 30 == 0 and now.second < 10:  # Mỗi 30 phút
                    if self.telegram_config.get('periodic_reports', False):
                        self.send_positions_report()
            
            except Exception as e:
                logger.error(f"Lỗi trong thread giám sát: {str(e)}")
            
            # Ngủ trước khi chạy lại
            time.sleep(self.check_interval)
        
        logger.info("Thread giám sát vị thế kết thúc")


# Hàm để sử dụng module này độc lập
def start_position_monitor(api_connector):
    """
    Khởi động monitor vị thế độc lập
    
    Args:
        api_connector: API connector
        
    Returns:
        PositionMonitor: Instance của monitor
    """
    monitor = PositionMonitor(api_connector)
    monitor.start_monitoring()
    
    return monitor