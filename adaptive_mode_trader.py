#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Thực hiện chiến lược giao dịch thích ứng với Hedge Mode và Single Direction
tự động lựa chọn dựa trên điều kiện thị trường
"""

import os
import json
import time
import logging
import threading
import datetime
import pandas as pd
from collections import defaultdict

# Đường dẫn tới thư mục làm việc
import adaptive_mode_selector
from adaptive_mode_selector import AdaptiveModeSelector

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('adaptive_trader.log')
    ]
)

logger = logging.getLogger('adaptive_trader')

class AdaptiveModeTrader:
    """
    Lớp thực hiện chiến lược giao dịch thích ứng tự động chuyển đổi giữa
    Hedge Mode và Single Direction dựa trên điều kiện thị trường
    """
    
    def __init__(self, api_connector, config_path='adaptive_trader_config.json'):
        """
        Khởi tạo Trader thích ứng
        
        Args:
            api_connector: Kết nối API Binance
            config_path (str): Đường dẫn file cấu hình
        """
        self.api = api_connector
        self.config_path = config_path
        self.load_config()
        
        # Khởi tạo bộ chọn chế độ thích ứng
        self.mode_selector = AdaptiveModeSelector(api_connector)
        
        # Quản lý vị thế
        self.active_positions = defaultdict(dict)  # symbol -> positions
        self.pending_orders = defaultdict(list)  # symbol -> orders
        
        # Thống kê
        self.performance_stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0,
            'hedge_mode_trades': 0,
            'single_mode_trades': 0,
            'hedge_mode_pnl': 0.0,
            'single_mode_pnl': 0.0
        }
        
        # Đánh dấu chương trình đang chạy
        self.is_running = False
        self.threads = []
        
        logger.info(f"Đã khởi tạo Adaptive Mode Trader với {len(self.config['symbols'])} cặp tiền")
    
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
                    'symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT'],
                    'max_concurrent_positions': 10,
                    'max_positions_per_symbol': 2,
                    'use_market_orders': True,
                    'market_check_interval': 10,  # phút
                    'position_check_interval': 5,  # phút
                    'enable_telegram_notifications': True,
                    'enable_auto_optimization': True,
                    'optimization_interval': 24,  # giờ
                    'account_risk_limit': 20.0,  # % tổng tài khoản có thể đặt cọc
                    'fallback_mode': 'single',  # Chế độ dự phòng nếu lỗi phân tích
                    'max_spread_percentage': 0.5,  # % chênh lệch giá mua/bán tối đa
                    'min_volume_usd': 1000000.0  # Volume tối thiểu cho các cặp (USD)
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
    
    def save_positions(self):
        """
        Lưu trạng thái vị thế hiện tại
        """
        try:
            positions_path = 'data/active_positions_adaptive.json'
            os.makedirs('data', exist_ok=True)
            
            with open(positions_path, 'w') as f:
                json.dump({
                    'active_positions': dict(self.active_positions),
                    'pending_orders': dict(self.pending_orders),
                    'last_updated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }, f, indent=2, default=str)
            
            logger.info(f"Đã lưu trạng thái vị thế vào {positions_path}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu trạng thái vị thế: {e}")
    
    def load_positions(self):
        """
        Tải trạng thái vị thế đã lưu
        """
        try:
            positions_path = 'data/active_positions_adaptive.json'
            if os.path.exists(positions_path):
                with open(positions_path, 'r') as f:
                    position_data = json.load(f)
                
                self.active_positions = defaultdict(dict, position_data.get('active_positions', {}))
                self.pending_orders = defaultdict(list, position_data.get('pending_orders', {}))
                
                logger.info(f"Đã tải trạng thái vị thế từ {positions_path}")
                return True
            else:
                logger.info("Không tìm thấy file trạng thái vị thế")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi tải trạng thái vị thế: {e}")
            return False
    
    def start(self):
        """
        Khởi động trader thích ứng
        """
        if self.is_running:
            logger.warning("Trader đã đang chạy")
            return
        
        self.is_running = True
        logger.info("Bắt đầu Adaptive Mode Trader")
        
        # Tải các vị thế trước đó nếu có
        self.load_positions()
        
        # Đồng bộ với vị thế thực tế trên API
        self.sync_positions_from_api()
        
        # Khởi động các thread riêng cho từng chức năng
        market_analyzer_thread = threading.Thread(target=self.market_analyzer_loop)
        position_manager_thread = threading.Thread(target=self.position_manager_loop)
        optimization_thread = threading.Thread(target=self.optimization_loop)
        
        # Lưu các thread để quản lý
        self.threads = [market_analyzer_thread, position_manager_thread, optimization_thread]
        
        # Đánh dấu là daemon để tự kết thúc khi chương trình chính kết thúc
        for thread in self.threads:
            thread.daemon = True
            thread.start()
        
        logger.info(f"Đã khởi động {len(self.threads)} luồng xử lý")
    
    def stop(self):
        """
        Dừng trader thích ứng
        """
        if not self.is_running:
            logger.warning("Trader chưa chạy")
            return
        
        logger.info("Dừng Adaptive Mode Trader")
        self.is_running = False
        
        # Lưu trạng thái vị thế
        self.save_positions()
        
        # Đợi các thread kết thúc (timeout 10s)
        for thread in self.threads:
            thread.join(timeout=10)
        
        self.threads.clear()
        logger.info("Đã dừng tất cả các luồng xử lý")
    
    def market_analyzer_loop(self):
        """
        Vòng lặp phân tích thị trường và đưa ra quyết định
        """
        logger.info("Bắt đầu vòng lặp phân tích thị trường")
        
        while self.is_running:
            try:
                # Phân tích thị trường cho từng cặp tiền
                for symbol in self.config['symbols']:
                    # Kiểm tra xem có đủ volume không
                    if not self.check_symbol_volume(symbol):
                        logger.warning(f"{symbol} không đủ volume để giao dịch, bỏ qua")
                        continue
                    
                    # Phân tích thị trường
                    analysis = self.mode_selector.analyze_market_conditions(symbol)
                    
                    if analysis:
                        # Kiểm tra xem có nên mở vị thế mới không
                        self.evaluate_new_position(symbol, analysis)
                    
                # Nghỉ một khoảng thời gian trước khi phân tích tiếp
                interval_minutes = self.config['market_check_interval']
                logger.info(f"Hoàn tất phân tích thị trường, nghỉ {interval_minutes} phút")
                
                # Chia nhỏ thời gian nghỉ để dễ thoát
                for _ in range(interval_minutes * 60 // 10):
                    if not self.is_running:
                        break
                    time.sleep(10)
            
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp phân tích thị trường: {e}")
                time.sleep(60)  # Nghỉ 1 phút nếu có lỗi
    
    def position_manager_loop(self):
        """
        Vòng lặp quản lý vị thế hiện tại
        """
        logger.info("Bắt đầu vòng lặp quản lý vị thế")
        
        while self.is_running:
            try:
                # Kiểm tra và cập nhật các vị thế hiện tại
                for symbol in self.active_positions:
                    positions = self.active_positions[symbol]
                    
                    # Kiểm tra các vị thế hedge mode
                    if 'hedge' in positions:
                        hedge_pos = positions['hedge']
                        self.update_position_status(symbol, 'hedge', hedge_pos)
                    
                    # Kiểm tra các vị thế single direction
                    if 'single' in positions:
                        single_pos = positions['single']
                        self.update_position_status(symbol, 'single', single_pos)
                
                # Kiểm tra các lệnh đang chờ
                for symbol in list(self.pending_orders.keys()):
                    if not self.pending_orders[symbol]:
                        continue
                    
                    orders = self.pending_orders[symbol]
                    for order in list(orders):
                        order_id = order.get('order_id')
                        if order_id:
                            # Kiểm tra trạng thái lệnh
                            try:
                                order_status = self.api.get_order(symbol=symbol, orderId=order_id)
                                
                                if order_status['status'] == 'FILLED':
                                    # Lệnh đã được khớp, cập nhật vị thế
                                    logger.info(f"Lệnh {order_id} đã được khớp: {symbol} {order.get('side')} {order.get('quantity')}")
                                    self.update_position_after_fill(symbol, order, order_status)
                                    self.pending_orders[symbol].remove(order)
                                elif order_status['status'] in ['CANCELED', 'REJECTED', 'EXPIRED']:
                                    # Lệnh đã bị hủy
                                    logger.warning(f"Lệnh {order_id} đã bị hủy/từ chối: {symbol}")
                                    self.pending_orders[symbol].remove(order)
                            except Exception as e:
                                logger.error(f"Lỗi khi kiểm tra lệnh {order_id}: {e}")
                
                # Lưu trạng thái vị thế sau mỗi lần cập nhật
                self.save_positions()
                
                # Nghỉ một khoảng thời gian trước khi kiểm tra tiếp
                interval_minutes = self.config['position_check_interval']
                logger.info(f"Hoàn tất kiểm tra vị thế, nghỉ {interval_minutes} phút")
                
                # Chia nhỏ thời gian nghỉ để dễ thoát
                for _ in range(interval_minutes * 60 // 10):
                    if not self.is_running:
                        break
                    time.sleep(10)
            
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp quản lý vị thế: {e}")
                time.sleep(60)  # Nghỉ 1 phút nếu có lỗi
    
    def optimization_loop(self):
        """
        Vòng lặp tối ưu hóa tham số
        """
        logger.info("Bắt đầu vòng lặp tối ưu hóa")
        
        while self.is_running:
            try:
                if self.config['enable_auto_optimization']:
                    # Tối ưu hóa tham số dựa trên hiệu suất
                    optimized_params = self.mode_selector.optimize_parameters()
                    
                    # Tạo báo cáo hiệu suất
                    report = self.mode_selector.get_summary_report()
                    
                    # Ghi báo cáo vào file
                    report_path = 'data/performance_report.json'
                    with open(report_path, 'w') as f:
                        json.dump(report, f, indent=2, default=str)
                    
                    logger.info(f"Đã tối ưu hóa tham số và lưu báo cáo vào {report_path}")
                
                # Nghỉ một khoảng thời gian trước khi tối ưu tiếp
                interval_hours = self.config['optimization_interval']
                logger.info(f"Hoàn tất tối ưu hóa, nghỉ {interval_hours} giờ")
                
                # Chia nhỏ thời gian nghỉ để dễ thoát
                for _ in range(interval_hours * 60 * 60 // 30):
                    if not self.is_running:
                        break
                    time.sleep(30)
            
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp tối ưu hóa: {e}")
                time.sleep(300)  # Nghỉ 5 phút nếu có lỗi
    
    def sync_positions_from_api(self):
        """
        Đồng bộ vị thế từ API Binance
        """
        try:
            # Lấy vị thế futures hiện tại
            positions = self.api.get_futures_position_risk()
            
            if not positions:
                logger.warning("Không lấy được thông tin vị thế từ API")
                return
            
            # Reset active positions từ API
            updated_positions = defaultdict(dict)
            
            # Lọc các vị thế có số lượng > 0
            active_positions = [p for p in positions if float(p['positionAmt']) != 0]
            
            for position in active_positions:
                symbol = position['symbol']
                position_amt = float(position['positionAmt'])
                entry_price = float(position['entryPrice'])
                leverage = int(position['leverage'])
                unrealized_pnl = float(position['unRealizedProfit'])
                
                # Xác định hướng và chế độ
                if 'positionSide' in position:
                    position_side = position['positionSide']
                    
                    # Hedge Mode
                    if position_side in ['LONG', 'SHORT']:
                        if 'hedge' not in updated_positions[symbol]:
                            updated_positions[symbol]['hedge'] = {
                                'long': None,
                                'short': None,
                                'mode': 'hedge',
                                'entry_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'updated_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'status': 'active'
                            }
                        
                        direction = position_side.lower()
                        updated_positions[symbol]['hedge'][direction] = {
                            'quantity': abs(position_amt),
                            'entry_price': entry_price,
                            'leverage': leverage,
                            'unrealized_pnl': unrealized_pnl,
                            'position_side': position_side
                        }
                    
                    # One-way Mode (BOTH)
                    else:
                        direction = 'long' if position_amt > 0 else 'short'
                        updated_positions[symbol]['single'] = {
                            'direction': direction,
                            'quantity': abs(position_amt),
                            'entry_price': entry_price,
                            'leverage': leverage,
                            'unrealized_pnl': unrealized_pnl,
                            'mode': 'single',
                            'entry_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'updated_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'status': 'active'
                        }
                else:
                    # One-way Mode (cũ)
                    direction = 'long' if position_amt > 0 else 'short'
                    updated_positions[symbol]['single'] = {
                        'direction': direction,
                        'quantity': abs(position_amt),
                        'entry_price': entry_price,
                        'leverage': leverage,
                        'unrealized_pnl': unrealized_pnl,
                        'mode': 'single',
                        'entry_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'updated_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'status': 'active'
                    }
            
            # Cập nhật active positions
            for symbol, positions in updated_positions.items():
                self.active_positions[symbol] = positions
            
            logger.info(f"Đã đồng bộ {len(updated_positions)} vị thế từ API Binance")
        except Exception as e:
            logger.error(f"Lỗi khi đồng bộ vị thế từ API: {e}")
    
    def check_symbol_volume(self, symbol):
        """
        Kiểm tra volume của một cặp tiền có đủ tiêu chuẩn không
        
        Args:
            symbol (str): Cặp tiền cần kiểm tra
            
        Returns:
            bool: True nếu đủ volume để giao dịch
        """
        try:
            # Lấy thông tin 24h của symbol
            ticker = self.api.get_ticker(symbol=symbol)
            
            if not ticker:
                logger.warning(f"Không lấy được thông tin ticker cho {symbol}")
                return False
            
            # Kiểm tra volume
            volume_24h = float(ticker.get('quoteVolume', 0))
            min_volume = self.config['min_volume_usd']
            
            if volume_24h < min_volume:
                logger.warning(f"{symbol} volume 24h ({volume_24h:.2f} USD) < ngưỡng tối thiểu ({min_volume:.2f} USD)")
                return False
            
            # Kiểm tra spread
            last_price = float(ticker.get('lastPrice', 0))
            bid_price = float(ticker.get('bidPrice', 0))
            ask_price = float(ticker.get('askPrice', 0))
            
            if bid_price == 0 or ask_price == 0:
                logger.warning(f"{symbol} không có giá mua/bán hợp lệ")
                return False
            
            # Tính spread
            spread_pct = (ask_price - bid_price) / bid_price * 100
            max_spread = self.config['max_spread_percentage']
            
            if spread_pct > max_spread:
                logger.warning(f"{symbol} spread ({spread_pct:.2f}%) > ngưỡng tối đa ({max_spread:.2f}%)")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra volume của {symbol}: {e}")
            return False
    
    def evaluate_new_position(self, symbol, analysis):
        """
        Đánh giá xem có nên mở vị thế mới không
        
        Args:
            symbol (str): Cặp tiền
            analysis (dict): Kết quả phân tích thị trường
        """
        try:
            # Kiểm tra xem đã có vị thế cho symbol này chưa
            if symbol in self.active_positions:
                positions = self.active_positions[symbol]
                
                # Nếu đã có cả hedge và single, không mở thêm
                if 'hedge' in positions and 'single' in positions:
                    logger.info(f"{symbol} đã có cả vị thế hedge và single, không mở thêm")
                    return
                
                # Nếu đã có hedge và phân tích khuyến nghị hedge, không mở thêm
                if 'hedge' in positions and analysis['recommended_mode'] == 'hedge':
                    logger.info(f"{symbol} đã có vị thế hedge, không mở thêm vị thế hedge")
                    return
                
                # Nếu đã có single và phân tích khuyến nghị single cùng hướng, không mở thêm
                if ('single' in positions and analysis['recommended_mode'] == 'single' and
                        positions['single']['direction'].upper() == analysis['recommended_direction']):
                    logger.info(f"{symbol} đã có vị thế single {analysis['recommended_direction']}, không mở thêm")
                    return
            
            # Kiểm tra số lượng vị thế hiện tại
            total_positions = sum(len(self.active_positions[s]) for s in self.active_positions)
            if total_positions >= self.config['max_concurrent_positions']:
                logger.warning(f"Đã đạt giới hạn vị thế tối đa ({self.config['max_concurrent_positions']}), không mở thêm")
                return
            
            # Lấy thông số giao dịch từ bộ chọn chế độ
            trading_params = self.mode_selector.get_trading_parameters(symbol, analysis)
            
            # Kiểm tra độ tin cậy của phân tích
            decision_basis = analysis.get('decision_basis', '')
            confidence_high = True
            
            if 'market_regime' in decision_basis:
                # Dựa trên phân tích thị trường - độ tin cậy cao
                pass
            elif 'time_based' in decision_basis:
                # Dựa trên phiên giao dịch - độ tin cậy cao
                pass
            else:
                # Độ tin cậy thấp - không mở vị thế
                confidence_high = False
                logger.warning(f"{symbol} phân tích có độ tin cậy thấp, không mở vị thế")
                return
            
            # Mở vị thế mới dựa trên chế độ khuyến nghị
            mode = trading_params['mode']
            direction = trading_params['direction']
            
            # Lấy giá hiện tại
            current_price = float(self.api.get_symbol_price(symbol)['price'])
            
            if mode == 'hedge':
                # Mở vị thế hedge (cả LONG và SHORT)
                self.open_hedge_position(symbol, current_price, trading_params)
            else:  # single mode
                # Mở vị thế single direction
                self.open_single_position(symbol, direction, current_price, trading_params)
        
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá vị thế mới cho {symbol}: {e}")
    
    def open_hedge_position(self, symbol, current_price, trading_params):
        """
        Mở vị thế hedge mode (cả LONG và SHORT)
        
        Args:
            symbol (str): Cặp tiền giao dịch
            current_price (float): Giá hiện tại
            trading_params (dict): Thông số giao dịch
        """
        try:
            # Kiểm tra xem có vị thế hedge đang mở hay không
            if symbol in self.active_positions and 'hedge' in self.active_positions[symbol]:
                logger.info(f"{symbol} đã có vị thế hedge, không mở thêm")
                return False
            
            # Tính toán số lượng dựa trên cân bằng tài khoản và risk
            account_balance = float(self.api.get_futures_account_balance()[0]['balance'])
            risk_per_trade = trading_params['risk_per_trade'] / 100.0
            
            # Kiểm tra minimum quantity và lot size
            symbol_info = self.api.get_symbol_info(symbol)
            if not symbol_info:
                logger.error(f"Không lấy được thông tin symbolInfo cho {symbol}")
                return False
            
            # Tìm bộ lọc cho stepSize
            step_size = None
            min_qty = None
            
            for filter in symbol_info.get('filters', []):
                if filter['filterType'] == 'LOT_SIZE':
                    step_size = float(filter['stepSize'])
                    min_qty = float(filter['minQty'])
                    break
            
            if not step_size or not min_qty:
                logger.error(f"Không tìm được stepSize hoặc minQty cho {symbol}")
                return False
            
            # Tính toán kích thước vị thế
            position_size_usd = account_balance * risk_per_trade
            quantity = position_size_usd / current_price
            
            # Làm tròn xuống theo stepSize
            quantity = self.round_step_size(quantity, step_size)
            
            # Kiểm tra xem có đạt minimum quantity không
            if quantity < min_qty:
                logger.warning(f"{symbol} số lượng tính toán ({quantity}) < số lượng tối thiểu ({min_qty})")
                quantity = min_qty
            
            # Thiết lập đòn bẩy
            leverage = trading_params['leverage']
            try:
                self.api.change_leverage(symbol=symbol, leverage=leverage)
                logger.info(f"Đã thiết lập đòn bẩy {leverage}x cho {symbol}")
            except Exception as e:
                logger.error(f"Lỗi khi thiết lập đòn bẩy cho {symbol}: {e}")
                leverage = 10  # Mặc định nếu không thiết lập được
            
            # Thiết lập chế độ hedge
            try:
                self.api.change_margin_type(symbol=symbol, marginType='ISOLATED')
                logger.info(f"Đã thiết lập margin type ISOLATED cho {symbol}")
            except Exception as e:
                logger.warning(f"Lỗi khi thiết lập margin type cho {symbol}: {e}")
            
            try:
                self.api.change_position_mode(dualSidePosition=True)
                logger.info(f"Đã thiết lập position mode HEDGE cho {symbol}")
            except Exception as e:
                logger.warning(f"Lỗi khi thiết lập position mode cho {symbol}: {e}")
            
            # Tính SL/TP
            sl_percentage = trading_params['sl_percentage'] / 100.0
            tp_percentage = trading_params['tp_percentage'] / 100.0
            
            # LONG position
            long_entry_price = current_price
            long_sl = long_entry_price * (1 - sl_percentage)
            long_tp = long_entry_price * (1 + tp_percentage)
            
            # SHORT position
            short_entry_price = current_price
            short_sl = short_entry_price * (1 + sl_percentage)
            short_tp = short_entry_price * (1 - tp_percentage)
            
            # Đặt lệnh LONG
            try:
                if self.config['use_market_orders']:
                    long_order = self.api.create_order_with_position_side(
                        symbol=symbol,
                        side='BUY',
                        positionSide='LONG',
                        type='MARKET',
                        quantity=quantity
                    )
                    logger.info(f"Đã đặt lệnh MARKET BUY (LONG) cho {symbol}: {quantity}")
                else:
                    long_order = self.api.create_order_with_position_side(
                        symbol=symbol,
                        side='BUY',
                        positionSide='LONG',
                        type='LIMIT',
                        timeInForce='GTC',
                        quantity=quantity,
                        price=long_entry_price
                    )
                    logger.info(f"Đã đặt lệnh LIMIT BUY (LONG) cho {symbol}: {quantity} @ {long_entry_price}")
                
                # Thêm vào danh sách lệnh đang chờ
                self.pending_orders[symbol].append({
                    'order_id': long_order['orderId'],
                    'symbol': symbol,
                    'side': 'BUY',
                    'position_side': 'LONG',
                    'quantity': quantity,
                    'entry_price': long_entry_price,
                    'sl_price': long_sl,
                    'tp_price': long_tp,
                    'leverage': leverage,
                    'mode': 'hedge',
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            except Exception as e:
                logger.error(f"Lỗi khi đặt lệnh LONG cho {symbol}: {e}")
                return False
            
            # Đặt lệnh SHORT
            try:
                if self.config['use_market_orders']:
                    short_order = self.api.create_order_with_position_side(
                        symbol=symbol,
                        side='SELL',
                        positionSide='SHORT',
                        type='MARKET',
                        quantity=quantity
                    )
                    logger.info(f"Đã đặt lệnh MARKET SELL (SHORT) cho {symbol}: {quantity}")
                else:
                    short_order = self.api.create_order_with_position_side(
                        symbol=symbol,
                        side='SELL',
                        positionSide='SHORT',
                        type='LIMIT',
                        timeInForce='GTC',
                        quantity=quantity,
                        price=short_entry_price
                    )
                    logger.info(f"Đã đặt lệnh LIMIT SELL (SHORT) cho {symbol}: {quantity} @ {short_entry_price}")
                
                # Thêm vào danh sách lệnh đang chờ
                self.pending_orders[symbol].append({
                    'order_id': short_order['orderId'],
                    'symbol': symbol,
                    'side': 'SELL',
                    'position_side': 'SHORT',
                    'quantity': quantity,
                    'entry_price': short_entry_price,
                    'sl_price': short_sl,
                    'tp_price': short_tp,
                    'leverage': leverage,
                    'mode': 'hedge',
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            except Exception as e:
                logger.error(f"Lỗi khi đặt lệnh SHORT cho {symbol}: {e}")
                return False
            
            # Tạo vị thế HEDGE trong danh sách vị thế
            self.active_positions[symbol]['hedge'] = {
                'long': {
                    'quantity': quantity,
                    'entry_price': long_entry_price,
                    'stop_loss': long_sl,
                    'take_profit': long_tp,
                    'leverage': leverage,
                    'position_side': 'LONG'
                },
                'short': {
                    'quantity': quantity,
                    'entry_price': short_entry_price,
                    'stop_loss': short_sl,
                    'take_profit': short_tp,
                    'leverage': leverage,
                    'position_side': 'SHORT'
                },
                'mode': 'hedge',
                'entry_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'updated_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'pending'
            }
            
            # Đặt SL/TP
            try:
                # LONG SL/TP
                self.api.set_stop_loss_take_profit(
                    symbol=symbol,
                    position_side='LONG',
                    stop_loss_price=long_sl,
                    take_profit_price=long_tp
                )
                logger.info(f"Đã đặt SL/TP cho LONG {symbol}: SL={long_sl}, TP={long_tp}")
                
                # SHORT SL/TP
                self.api.set_stop_loss_take_profit(
                    symbol=symbol,
                    position_side='SHORT',
                    stop_loss_price=short_sl,
                    take_profit_price=short_tp
                )
                logger.info(f"Đã đặt SL/TP cho SHORT {symbol}: SL={short_sl}, TP={short_tp}")
            except Exception as e:
                logger.error(f"Lỗi khi đặt SL/TP cho {symbol}: {e}")
            
            # Cập nhật thống kê
            self.performance_stats['total_trades'] += 2  # LONG và SHORT
            self.performance_stats['hedge_mode_trades'] += 2
            
            # Lưu vị thế
            self.save_positions()
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi mở vị thế hedge cho {symbol}: {e}")
            return False
    
    def open_single_position(self, symbol, direction, current_price, trading_params):
        """
        Mở vị thế single direction
        
        Args:
            symbol (str): Cặp tiền giao dịch
            direction (str): Hướng giao dịch ('LONG' hoặc 'SHORT')
            current_price (float): Giá hiện tại
            trading_params (dict): Thông số giao dịch
        """
        try:
            # Nếu không có direction cụ thể, không mở vị thế
            if direction not in ['LONG', 'SHORT']:
                logger.warning(f"{symbol} không có hướng giao dịch cụ thể, không mở vị thế")
                return False
            
            # Kiểm tra xem có vị thế single đang mở hay không
            if (symbol in self.active_positions and 'single' in self.active_positions[symbol] and
                    self.active_positions[symbol]['single']['direction'].upper() == direction):
                logger.info(f"{symbol} đã có vị thế single {direction}, không mở thêm")
                return False
            
            # Tính toán số lượng dựa trên cân bằng tài khoản và risk
            account_balance = float(self.api.get_futures_account_balance()[0]['balance'])
            risk_per_trade = trading_params['risk_per_trade'] / 100.0
            
            # Kiểm tra minimum quantity và lot size
            symbol_info = self.api.get_symbol_info(symbol)
            if not symbol_info:
                logger.error(f"Không lấy được thông tin symbolInfo cho {symbol}")
                return False
            
            # Tìm bộ lọc cho stepSize
            step_size = None
            min_qty = None
            
            for filter in symbol_info.get('filters', []):
                if filter['filterType'] == 'LOT_SIZE':
                    step_size = float(filter['stepSize'])
                    min_qty = float(filter['minQty'])
                    break
            
            if not step_size or not min_qty:
                logger.error(f"Không tìm được stepSize hoặc minQty cho {symbol}")
                return False
            
            # Tính toán kích thước vị thế
            position_size_usd = account_balance * risk_per_trade
            quantity = position_size_usd / current_price
            
            # Làm tròn xuống theo stepSize
            quantity = self.round_step_size(quantity, step_size)
            
            # Kiểm tra xem có đạt minimum quantity không
            if quantity < min_qty:
                logger.warning(f"{symbol} số lượng tính toán ({quantity}) < số lượng tối thiểu ({min_qty})")
                quantity = min_qty
            
            # Thiết lập đòn bẩy
            leverage = trading_params['leverage']
            try:
                self.api.change_leverage(symbol=symbol, leverage=leverage)
                logger.info(f"Đã thiết lập đòn bẩy {leverage}x cho {symbol}")
            except Exception as e:
                logger.error(f"Lỗi khi thiết lập đòn bẩy cho {symbol}: {e}")
                leverage = 10  # Mặc định nếu không thiết lập được
            
            # Thiết lập chế độ margin
            try:
                self.api.change_margin_type(symbol=symbol, marginType='ISOLATED')
                logger.info(f"Đã thiết lập margin type ISOLATED cho {symbol}")
            except Exception as e:
                logger.warning(f"Lỗi khi thiết lập margin type cho {symbol}: {e}")
            
            # Thiết lập chế độ ONE-WAY (để chắc chắn)
            try:
                self.api.change_position_mode(dualSidePosition=False)
                logger.info(f"Đã thiết lập position mode ONE-WAY cho {symbol}")
            except Exception as e:
                logger.warning(f"Lỗi khi thiết lập position mode cho {symbol}: {e}")
            
            # Tính SL/TP
            sl_percentage = trading_params['sl_percentage'] / 100.0
            tp_percentage = trading_params['tp_percentage'] / 100.0
            
            if direction == 'LONG':
                entry_price = current_price
                sl_price = entry_price * (1 - sl_percentage)
                tp_price = entry_price * (1 + tp_percentage)
                order_side = 'BUY'
            else:  # SHORT
                entry_price = current_price
                sl_price = entry_price * (1 + sl_percentage)
                tp_price = entry_price * (1 - tp_percentage)
                order_side = 'SELL'
            
            # Đặt lệnh
            try:
                if self.config['use_market_orders']:
                    order = self.api.create_order(
                        symbol=symbol,
                        side=order_side,
                        type='MARKET',
                        quantity=quantity
                    )
                    logger.info(f"Đã đặt lệnh MARKET {order_side} cho {symbol}: {quantity}")
                else:
                    order = self.api.create_order(
                        symbol=symbol,
                        side=order_side,
                        type='LIMIT',
                        timeInForce='GTC',
                        quantity=quantity,
                        price=entry_price
                    )
                    logger.info(f"Đã đặt lệnh LIMIT {order_side} cho {symbol}: {quantity} @ {entry_price}")
                
                # Thêm vào danh sách lệnh đang chờ
                self.pending_orders[symbol].append({
                    'order_id': order['orderId'],
                    'symbol': symbol,
                    'side': order_side,
                    'quantity': quantity,
                    'entry_price': entry_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'leverage': leverage,
                    'mode': 'single',
                    'direction': direction.lower(),
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            except Exception as e:
                logger.error(f"Lỗi khi đặt lệnh {direction} cho {symbol}: {e}")
                return False
            
            # Tạo vị thế SINGLE trong danh sách vị thế
            self.active_positions[symbol]['single'] = {
                'direction': direction.lower(),
                'quantity': quantity,
                'entry_price': entry_price,
                'stop_loss': sl_price,
                'take_profit': tp_price,
                'leverage': leverage,
                'mode': 'single',
                'entry_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'updated_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'pending'
            }
            
            # Đặt SL/TP
            try:
                # Xác định side cho SL/TP (ngược với side của vị thế)
                sl_side = 'SELL' if direction == 'LONG' else 'BUY'
                
                # Đặt SL
                self.api.create_order(
                    symbol=symbol,
                    side=sl_side,
                    type='STOP_MARKET',
                    timeInForce='GTC',
                    quantity=quantity,
                    stopPrice=sl_price,
                    reduceOnly=True
                )
                logger.info(f"Đã đặt SL cho {direction} {symbol}: {sl_price}")
                
                # Đặt TP
                self.api.create_order(
                    symbol=symbol,
                    side=sl_side,
                    type='TAKE_PROFIT_MARKET',
                    timeInForce='GTC',
                    quantity=quantity,
                    stopPrice=tp_price,
                    reduceOnly=True
                )
                logger.info(f"Đã đặt TP cho {direction} {symbol}: {tp_price}")
            except Exception as e:
                logger.error(f"Lỗi khi đặt SL/TP cho {symbol}: {e}")
            
            # Cập nhật thống kê
            self.performance_stats['total_trades'] += 1
            self.performance_stats['single_mode_trades'] += 1
            
            # Lưu vị thế
            self.save_positions()
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi mở vị thế single cho {symbol}: {e}")
            return False
    
    def update_position_status(self, symbol, mode, position):
        """
        Cập nhật trạng thái của vị thế
        
        Args:
            symbol (str): Cặp tiền giao dịch
            mode (str): Chế độ ('hedge' hoặc 'single')
            position (dict): Thông tin vị thế
        """
        try:
            # Lấy giá hiện tại
            current_price = float(self.api.get_symbol_price(symbol)['price'])
            
            if mode == 'hedge':
                # Cập nhật vị thế LONG
                if 'long' in position and position['long']:
                    long_pos = position['long']
                    entry_price = long_pos['entry_price']
                    sl_price = long_pos.get('stop_loss')
                    tp_price = long_pos.get('take_profit')
                    
                    # Kiểm tra hit SL/TP
                    if sl_price and current_price <= sl_price:
                        # Hit SL
                        logger.info(f"{symbol} LONG hit SL: {sl_price}")
                        # Vị thế sẽ tự động đóng bởi lệnh SL
                        # Cập nhật hiệu suất
                        self.update_performance_after_close(symbol, 'hedge', 'LONG', entry_price, sl_price, long_pos['quantity'])
                    elif tp_price and current_price >= tp_price:
                        # Hit TP
                        logger.info(f"{symbol} LONG hit TP: {tp_price}")
                        # Vị thế sẽ tự động đóng bởi lệnh TP
                        # Cập nhật hiệu suất
                        self.update_performance_after_close(symbol, 'hedge', 'LONG', entry_price, tp_price, long_pos['quantity'])
                
                # Cập nhật vị thế SHORT
                if 'short' in position and position['short']:
                    short_pos = position['short']
                    entry_price = short_pos['entry_price']
                    sl_price = short_pos.get('stop_loss')
                    tp_price = short_pos.get('take_profit')
                    
                    # Kiểm tra hit SL/TP
                    if sl_price and current_price >= sl_price:
                        # Hit SL
                        logger.info(f"{symbol} SHORT hit SL: {sl_price}")
                        # Vị thế sẽ tự động đóng bởi lệnh SL
                        # Cập nhật hiệu suất
                        self.update_performance_after_close(symbol, 'hedge', 'SHORT', entry_price, sl_price, short_pos['quantity'])
                    elif tp_price and current_price <= tp_price:
                        # Hit TP
                        logger.info(f"{symbol} SHORT hit TP: {tp_price}")
                        # Vị thế sẽ tự động đóng bởi lệnh TP
                        # Cập nhật hiệu suất
                        self.update_performance_after_close(symbol, 'hedge', 'SHORT', entry_price, tp_price, short_pos['quantity'])
            
            else:  # single mode
                direction = position['direction']
                entry_price = position['entry_price']
                sl_price = position.get('stop_loss')
                tp_price = position.get('take_profit')
                
                if direction == 'long':
                    # Kiểm tra hit SL/TP
                    if sl_price and current_price <= sl_price:
                        # Hit SL
                        logger.info(f"{symbol} SINGLE LONG hit SL: {sl_price}")
                        # Vị thế sẽ tự động đóng bởi lệnh SL
                        # Cập nhật hiệu suất
                        self.update_performance_after_close(symbol, 'single', 'LONG', entry_price, sl_price, position['quantity'])
                    elif tp_price and current_price >= tp_price:
                        # Hit TP
                        logger.info(f"{symbol} SINGLE LONG hit TP: {tp_price}")
                        # Vị thế sẽ tự động đóng bởi lệnh TP
                        # Cập nhật hiệu suất
                        self.update_performance_after_close(symbol, 'single', 'LONG', entry_price, tp_price, position['quantity'])
                else:  # short
                    # Kiểm tra hit SL/TP
                    if sl_price and current_price >= sl_price:
                        # Hit SL
                        logger.info(f"{symbol} SINGLE SHORT hit SL: {sl_price}")
                        # Vị thế sẽ tự động đóng bởi lệnh SL
                        # Cập nhật hiệu suất
                        self.update_performance_after_close(symbol, 'single', 'SHORT', entry_price, sl_price, position['quantity'])
                    elif tp_price and current_price <= tp_price:
                        # Hit TP
                        logger.info(f"{symbol} SINGLE SHORT hit TP: {tp_price}")
                        # Vị thế sẽ tự động đóng bởi lệnh TP
                        # Cập nhật hiệu suất
                        self.update_performance_after_close(symbol, 'single', 'SHORT', entry_price, tp_price, position['quantity'])
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật trạng thái vị thế {symbol}: {e}")
    
    def update_performance_after_close(self, symbol, mode, direction, entry_price, exit_price, quantity):
        """
        Cập nhật hiệu suất sau khi đóng vị thế
        
        Args:
            symbol (str): Cặp tiền giao dịch
            mode (str): Chế độ ('hedge' hoặc 'single')
            direction (str): Hướng ('LONG' hoặc 'SHORT')
            entry_price (float): Giá vào lệnh
            exit_price (float): Giá thoát lệnh
            quantity (float): Số lượng
        """
        try:
            # Tính P/L
            if direction == 'LONG':
                pnl_pct = (exit_price - entry_price) / entry_price
                pnl_amount = quantity * entry_price * pnl_pct
            else:  # SHORT
                pnl_pct = (entry_price - exit_price) / entry_price
                pnl_amount = quantity * entry_price * pnl_pct
            
            # Cập nhật bộ chọn chế độ
            self.mode_selector.update_performance(mode, direction, symbol, entry_price, exit_price, quantity * entry_price)
            
            # Cập nhật thống kê
            self.performance_stats['total_pnl'] += pnl_amount
            
            if pnl_amount > 0:
                self.performance_stats['winning_trades'] += 1
            else:
                self.performance_stats['losing_trades'] += 1
            
            if mode == 'hedge':
                self.performance_stats['hedge_mode_pnl'] += pnl_amount
            else:  # single
                self.performance_stats['single_mode_pnl'] += pnl_amount
            
            # Tính win rate
            total_trades = self.performance_stats['winning_trades'] + self.performance_stats['losing_trades']
            if total_trades > 0:
                self.performance_stats['win_rate'] = self.performance_stats['winning_trades'] / total_trades
            
            # Xóa vị thế khỏi active positions
            if mode == 'hedge':
                hedge_pos = self.active_positions[symbol].get('hedge', {})
                if direction == 'LONG' and 'long' in hedge_pos:
                    hedge_pos['long'] = None
                elif direction == 'SHORT' and 'short' in hedge_pos:
                    hedge_pos['short'] = None
                
                # Nếu cả long và short đều đã đóng, xóa hoàn toàn vị thế hedge
                if (('long' not in hedge_pos or hedge_pos['long'] is None) and
                        ('short' not in hedge_pos or hedge_pos['short'] is None)):
                    del self.active_positions[symbol]['hedge']
            else:  # single
                if 'single' in self.active_positions[symbol]:
                    del self.active_positions[symbol]['single']
            
            # Nếu không còn vị thế nào, xóa symbol khỏi active positions
            if not self.active_positions[symbol]:
                del self.active_positions[symbol]
            
            # Lưu trạng thái vị thế
            self.save_positions()
            
            # Log kết quả
            logger.info(f"Đóng vị thế {mode} {direction} {symbol}: Entry={entry_price}, Exit={exit_price}, "
                       f"PnL={pnl_amount:.2f} USD ({pnl_pct:.2%})")
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật hiệu suất sau khi đóng vị thế {symbol}: {e}")
    
    def update_position_after_fill(self, symbol, order, order_status):
        """
        Cập nhật vị thế sau khi lệnh được khớp
        
        Args:
            symbol (str): Cặp tiền giao dịch
            order (dict): Thông tin lệnh
            order_status (dict): Trạng thái lệnh
        """
        try:
            # Lấy thông tin từ lệnh và trạng thái
            mode = order.get('mode')
            
            if not mode:
                logger.warning(f"Lệnh {order['order_id']} không có thông tin mode, bỏ qua")
                return
            
            # Cập nhật trạng thái vị thế
            if mode == 'hedge':
                position_side = order.get('position_side')
                
                if not position_side:
                    logger.warning(f"Lệnh {order['order_id']} không có thông tin position_side, bỏ qua")
                    return
                
                # Cập nhật vị thế HEDGE
                if symbol in self.active_positions and 'hedge' in self.active_positions[symbol]:
                    hedge_pos = self.active_positions[symbol]['hedge']
                    
                    if position_side == 'LONG':
                        if 'long' in hedge_pos:
                            hedge_pos['long']['status'] = 'active'
                            hedge_pos['long']['updated_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    elif position_side == 'SHORT':
                        if 'short' in hedge_pos:
                            hedge_pos['short']['status'] = 'active'
                            hedge_pos['short']['updated_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Cập nhật trạng thái chung
                    if (('long' in hedge_pos and hedge_pos['long'] and hedge_pos['long'].get('status') == 'active') and
                            ('short' in hedge_pos and hedge_pos['short'] and hedge_pos['short'].get('status') == 'active')):
                        hedge_pos['status'] = 'active'
                        hedge_pos['updated_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            else:  # single mode
                # Cập nhật vị thế SINGLE
                if symbol in self.active_positions and 'single' in self.active_positions[symbol]:
                    single_pos = self.active_positions[symbol]['single']
                    single_pos['status'] = 'active'
                    single_pos['updated_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Lưu trạng thái vị thế
            self.save_positions()
            
            logger.info(f"Cập nhật vị thế {mode} {symbol} sau khi lệnh {order['order_id']} được khớp")
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật vị thế sau khi lệnh được khớp: {e}")
    
    def round_step_size(self, quantity, step_size):
        """
        Làm tròn số lượng theo step size
        
        Args:
            quantity (float): Số lượng gốc
            step_size (float): Step size
            
        Returns:
            float: Số lượng đã làm tròn
        """
        precision = 0
        
        # Xác định số chữ số thập phân của step_size
        if step_size < 1:
            precision = len(str(step_size).split('.')[-1].rstrip('0'))
        
        # Làm tròn xuống theo step_size
        return float(int(quantity / step_size) * step_size)
    
    def get_status_report(self):
        """
        Tạo báo cáo tổng quan về trạng thái hiện tại
        
        Returns:
            dict: Báo cáo trạng thái
        """
        try:
            # Lấy thông tin tài khoản
            account_info = self.api.get_futures_account()
            account_balance = float(account_info.get('totalWalletBalance', 0))
            unrealized_pnl = float(account_info.get('totalUnrealizedProfit', 0))
            
            # Lấy thống kê
            total_positions = sum(len(self.active_positions[s]) for s in self.active_positions)
            hedge_positions = sum(1 for s in self.active_positions if 'hedge' in self.active_positions[s])
            single_positions = sum(1 for s in self.active_positions if 'single' in self.active_positions[s])
            
            # Tính win rate
            total_trades = self.performance_stats['winning_trades'] + self.performance_stats['losing_trades']
            win_rate = 0 if total_trades == 0 else self.performance_stats['winning_trades'] / total_trades
            
            # Lấy phân tích thị trường
            market_analysis = {}
            for symbol in self.config['symbols'][:3]:  # Lấy 3 cặp tiền đầu tiên
                analysis = self.mode_selector.analyze_market_conditions(symbol)
                if analysis:
                    market_analysis[symbol] = {
                        'market_regime': analysis.get('market_regime'),
                        'volatility': analysis.get('volatility'),
                        'trend_strength': analysis.get('trend_strength'),
                        'recommended_mode': analysis.get('recommended_mode'),
                        'recommended_direction': analysis.get('recommended_direction'),
                        'decision_basis': analysis.get('decision_basis')
                    }
            
            # Tạo báo cáo
            report = {
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'account': {
                    'balance': account_balance,
                    'unrealized_pnl': unrealized_pnl,
                    'equity': account_balance + unrealized_pnl
                },
                'positions': {
                    'total': total_positions,
                    'hedge': hedge_positions,
                    'single': single_positions,
                    'active_symbols': list(self.active_positions.keys())
                },
                'performance': {
                    'total_trades': self.performance_stats['total_trades'],
                    'winning_trades': self.performance_stats['winning_trades'],
                    'losing_trades': self.performance_stats['losing_trades'],
                    'win_rate': win_rate,
                    'total_pnl': self.performance_stats['total_pnl'],
                    'hedge_mode_pnl': self.performance_stats['hedge_mode_pnl'],
                    'single_mode_pnl': self.performance_stats['single_mode_pnl']
                },
                'market_analysis': market_analysis,
                'config': {
                    'symbols': self.config['symbols'],
                    'max_concurrent_positions': self.config['max_concurrent_positions'],
                    'use_market_orders': self.config['use_market_orders'],
                    'enable_auto_optimization': self.config['enable_auto_optimization']
                }
            }
            
            # Lưu báo cáo vào file
            report_path = 'data/adaptive_trader_status.json'
            os.makedirs('data', exist_ok=True)
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Đã tạo báo cáo trạng thái và lưu vào {report_path}")
            
            return report
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo trạng thái: {e}")
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
    
    # Khởi tạo trader
    trader = AdaptiveModeTrader(api)
    
    # Bắt đầu trader
    trader.start()
    
    try:
        # Chạy vô hạn
        while True:
            time.sleep(60)
            
            # Tạo báo cáo trạng thái mỗi 30 phút
            if datetime.datetime.now().minute in [0, 30]:
                report = trader.get_status_report()
                print(f"Báo cáo trạng thái: {report}")
    except KeyboardInterrupt:
        # Dừng khi nhấn Ctrl+C
        trader.stop()
        print("Đã dừng trader")