#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Mô-đun Trailing Stop Nâng Cao với Chức Năng Thang Bộ (Escalator Mode)

Mô-đun này triển khai hệ thống trailing stop nâng cao với:
1. Trailing stop thông thường - stop loss di chuyển theo giá (1 chiều)
2. Chế độ thang bộ (Escalator) - stop loss chỉ tăng theo các ngưỡng giá nhất định
3. Nâng cấp khung thời gian tự động - khi lợi nhuận đạt ngưỡng, chuyển sang khung thời gian dài hơn
4. Trailing stop dựa trên ATR - điều chỉnh khoảng cách trailing theo độ biến động
"""

import os
import json
import time
import logging
from datetime import datetime
import traceback
from typing import Dict, List, Tuple, Optional, Union
import pandas as pd
import numpy as np

from binance_api import BinanceAPI

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trailing_stop.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('trailing_stop')

class EnhancedTrailingStop:
    """Lớp quản lý trailing stop nâng cao với nhiều tính năng thích ứng"""
    
    def __init__(self, config_path: str = 'configs/risk_management_config.json'):
        """
        Khởi tạo trình quản lý trailing stop
        
        Args:
            config_path (str, optional): Đường dẫn đến file cấu hình
        """
        self.api = BinanceAPI()
        self.config_path = config_path
        self.config = self._load_config()
        self.trailing_settings = self.config.get('trailing_stop_settings', {})
        self.active_positions = {}
        self.position_timeframes = {}
        self.last_update_time = {}
        self.update_interval = 5  # seconds
        
        # Khởi tạo dictionary lưu trữ trạng thái các vị thế đang trailing
        self.trailing_states = {}
        
        logger.info(f"Đã khởi tạo Enhanced Trailing Stop với {len(self.trailing_settings)} thiết lập")
        
    def _load_config(self) -> Dict:
        """
        Tải cấu hình từ file
        
        Returns:
            Dict: Cấu hình trailing stop
        """
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {e}")
            # Trả về cấu hình mặc định nếu không tải được
            return {
                "trailing_stop_settings": {
                    "enable_trailing_stop": True,
                    "activation_pct": 0.5,
                    "callback_pct": 0.2,
                    "dynamic_trailing": True,
                    "atr_multiplier": 1.0
                }
            }
    
    def _get_account_positions(self) -> List[Dict]:
        """
        Lấy danh sách các vị thế mở từ Binance
        
        Returns:
            List[Dict]: Danh sách vị thế
        """
        try:
            positions = self.api.get_futures_position_risk()
            # Lọc ra các vị thế có số lượng > 0
            active_positions = [p for p in positions if abs(float(p.get('positionAmt', 0))) > 0]
            return active_positions
        except Exception as e:
            logger.error(f"Lỗi khi lấy vị thế: {e}")
            return []
    
    def _calculate_atr(self, symbol: str, timeframe: str = '1h', period: int = 14) -> float:
        """
        Tính toán ATR (Average True Range) cho một cặp giao dịch
        
        Args:
            symbol (str): Mã cặp giao dịch
            timeframe (str): Khung thời gian
            period (int): Khoảng thời gian ATR
            
        Returns:
            float: Giá trị ATR
        """
        try:
            # Lấy dữ liệu giá
            klines = self.api.get_klines(symbol, timeframe, limit=period+10)
            df = self.api.convert_klines_to_dataframe(klines)
            
            # Tính ATR
            df['high_low'] = df['high'] - df['low']
            df['high_close'] = abs(df['high'] - df['close'].shift(1))
            df['low_close'] = abs(df['low'] - df['close'].shift(1))
            
            df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
            df['atr'] = df['tr'].rolling(window=period).mean()
            
            # Lấy giá trị ATR gần nhất
            atr = df['atr'].iloc[-1]
            return atr
        except Exception as e:
            logger.error(f"Lỗi khi tính ATR cho {symbol}: {e}")
            return 0.0
    
    def _get_dynamic_callback(self, symbol: str, side: str, entry_price: float, 
                            current_price: float, current_profit_pct: float,
                            timeframe: str = '1h') -> float:
        """
        Tính toán khoảng cách callback động dựa trên ATR và lợi nhuận hiện tại
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Phía giao dịch ('LONG' hoặc 'SHORT')
            entry_price (float): Giá vào
            current_price (float): Giá hiện tại
            current_profit_pct (float): Lợi nhuận hiện tại (%)
            timeframe (str): Khung thời gian
            
        Returns:
            float: Tỷ lệ callback động (%)
        """
        try:
            # Cấu hình cơ bản
            base_callback = self.trailing_settings.get('callback_pct', 0.5)
            
            if not self.trailing_settings.get('dynamic_trailing', True):
                return base_callback
                
            # Tính ATR
            atr = self._calculate_atr(symbol, timeframe)
            atr_multiplier = self.trailing_settings.get('atr_multiplier', 1.0)
            
            # Tính % ATR so với giá hiện tại
            atr_pct = (atr / current_price) * 100
            
            # Điều chỉnh callback dựa trên ATR và lợi nhuận
            dynamic_callback = base_callback
            
            # Tăng callback khi profit cao
            if current_profit_pct > 5.0:
                dynamic_callback = base_callback * 1.5
            elif current_profit_pct > 2.0:
                dynamic_callback = base_callback * 1.2
                
            # Điều chỉnh theo ATR
            dynamic_callback = max(dynamic_callback, atr_pct * atr_multiplier)
            
            # Đảm bảo callback không nhỏ hơn mức tối thiểu
            min_callback = self.trailing_settings.get('min_callback_pct', 0.1)
            dynamic_callback = max(dynamic_callback, min_callback)
            
            return dynamic_callback
            
        except Exception as e:
            logger.error(f"Lỗi khi tính callback động: {e}")
            return self.trailing_settings.get('callback_pct', 0.5)
    
    def _should_upgrade_timeframe(self, symbol: str, current_profit_pct: float, 
                                current_timeframe: str) -> Optional[str]:
        """
        Kiểm tra xem có nên nâng cấp khung thời gian không
        
        Args:
            symbol (str): Mã cặp giao dịch
            current_profit_pct (float): Lợi nhuận hiện tại (%)
            current_timeframe (str): Khung thời gian hiện tại
            
        Returns:
            Optional[str]: Khung thời gian mới nếu cần nâng cấp, None nếu không
        """
        if not self.trailing_settings.get('timeframe_upgrade', False):
            return None
            
        upgrade_trigger = self.trailing_settings.get('timeframe_upgrade_trigger_pct', 2.0)
        
        if current_profit_pct < upgrade_trigger:
            return None
            
        timeframe_map = self.trailing_settings.get('upgrade_timeframe_map', {
            '1m': '5m',
            '5m': '15m',
            '15m': '1h',
            '1h': '4h',
            '4h': '1d'
        })
        
        if current_timeframe in timeframe_map:
            return timeframe_map[current_timeframe]
            
        return None
    
    def _calculate_escalator_step(self, symbol: str, side: str, entry_price: float,
                                current_price: float, current_profit_pct: float) -> float:
        """
        Tính bậc thang tiếp theo cho chế độ escalator
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Phía giao dịch ('LONG' hoặc 'SHORT')
            entry_price (float): Giá vào
            current_price (float): Giá hiện tại
            current_profit_pct (float): Lợi nhuận hiện tại (%)
            
        Returns:
            float: Giá stop loss bậc thang tiếp theo
        """
        if not self.trailing_settings.get('escalator_mode', False):
            return 0.0
            
        step_size = self.trailing_settings.get('step_size_pct', 0.2)
        
        # Số bước hoàn thành dựa trên lợi nhuận hiện tại
        steps_completed = int(current_profit_pct / step_size)
        
        if steps_completed <= 0:
            return 0.0
            
        # Tính giá tương ứng với bậc thang
        if side == 'LONG':
            escalator_price = entry_price * (1 + steps_completed * step_size / 100)
        else:  # SHORT
            escalator_price = entry_price * (1 - steps_completed * step_size / 100)
            
        return escalator_price
    
    def update_trailing_stops(self):
        """Cập nhật trailing stop cho tất cả các vị thế mở"""
        try:
            positions = self._get_account_positions()
            
            # Cập nhật dictionary vị thế đang trailing
            current_symbols = {p['symbol']: p for p in positions}
            
            # Xử lý từng vị thế
            for position in positions:
                symbol = position['symbol']
                position_amt = float(position['positionAmt'])
                side = 'LONG' if position_amt > 0 else 'SHORT'
                entry_price = float(position['entryPrice'])
                current_price = float(position['markPrice'])
                unrealized_profit = float(position['unrealizedProfit'])
                leverage = int(position['leverage'])
                
                # Tính lợi nhuận hiện tại (%)
                position_value = abs(position_amt * entry_price)
                if position_value == 0:
                    continue
                    
                current_profit_pct = (unrealized_profit / (position_value / leverage)) * 100
                
                # Kiểm tra xem vị thế đã có trong trailing_states chưa
                if symbol not in self.trailing_states:
                    timeframe = '1h'  # Mặc định ban đầu
                    self.trailing_states[symbol] = {
                        'trailing_activated': False,
                        'current_stop_loss': 0.0,
                        'highest_price': current_price if side == 'LONG' else float('inf'),
                        'lowest_price': current_price if side == 'SHORT' else 0.0,
                        'timeframe': timeframe,
                        'last_update': datetime.now(),
                        'escalator_level': 0,
                        'side': side
                    }
                
                # Lấy trạng thái hiện tại
                state = self.trailing_states[symbol]
                
                # Kiểm tra nếu chưa kích hoạt trailing
                activation_threshold = self.trailing_settings.get('activation_pct', 1.0)
                if not state['trailing_activated'] and current_profit_pct >= activation_threshold:
                    state['trailing_activated'] = True
                    logger.info(f"Kích hoạt trailing stop cho {symbol} {side} tại mức lợi nhuận {current_profit_pct:.2f}%")
                
                # Nếu đã kích hoạt, cập nhật stop loss
                if state['trailing_activated']:
                    # Cập nhật giá cao/thấp nhất
                    if side == 'LONG':
                        state['highest_price'] = max(state['highest_price'], current_price)
                    else:  # SHORT
                        state['lowest_price'] = min(state['lowest_price'], current_price)
                    
                    # Kiểm tra nâng cấp timeframe
                    new_timeframe = self._should_upgrade_timeframe(
                        symbol, current_profit_pct, state['timeframe']
                    )
                    
                    if new_timeframe and new_timeframe != state['timeframe']:
                        logger.info(f"Nâng cấp khung thời gian cho {symbol} từ {state['timeframe']} lên {new_timeframe}")
                        state['timeframe'] = new_timeframe
                    
                    # Tính callback động
                    callback_pct = self._get_dynamic_callback(
                        symbol, side, entry_price, current_price, current_profit_pct, state['timeframe']
                    )
                    
                    # Tính giá stop loss dựa trên trailing
                    if side == 'LONG':
                        trailing_stop = state['highest_price'] * (1 - callback_pct / 100)
                    else:  # SHORT
                        trailing_stop = state['lowest_price'] * (1 + callback_pct / 100)
                    
                    # Tính giá stop loss dựa trên escalator mode
                    if self.trailing_settings.get('escalator_mode', False):
                        escalator_stop = self._calculate_escalator_step(
                            symbol, side, entry_price, current_price, current_profit_pct
                        )
                        
                        # Chọn stop loss có lợi nhất
                        if side == 'LONG':
                            new_stop_loss = max(trailing_stop, escalator_stop, state['current_stop_loss'])
                        else:  # SHORT
                            new_stop_loss = min(trailing_stop, escalator_stop) if escalator_stop > 0 else trailing_stop
                            if state['current_stop_loss'] > 0:
                                new_stop_loss = min(new_stop_loss, state['current_stop_loss'])
                    else:
                        # Chỉ dùng trailing stop thông thường
                        if side == 'LONG':
                            new_stop_loss = max(trailing_stop, state['current_stop_loss'])
                        else:  # SHORT
                            new_stop_loss = min(trailing_stop, state['current_stop_loss']) if state['current_stop_loss'] > 0 else trailing_stop
                    
                    # Cập nhật stop loss nếu có thay đổi đáng kể
                    min_price_movement = self.trailing_settings.get('min_price_movement_pct', 0.1) / 100
                    price_diff_pct = abs(new_stop_loss - state['current_stop_loss']) / current_price
                    
                    if state['current_stop_loss'] == 0 or price_diff_pct >= min_price_movement:
                        old_stop = state['current_stop_loss']
                        state['current_stop_loss'] = new_stop_loss
                        
                        # Log thay đổi
                        if old_stop > 0:
                            change_pct = (new_stop_loss - old_stop) / old_stop * 100
                            direction = "tăng" if change_pct > 0 else "giảm"
                            logger.info(f"Cập nhật trailing stop cho {symbol} {side}: {old_stop:.2f} -> {new_stop_loss:.2f} ({direction} {abs(change_pct):.2f}%)")
                        else:
                            logger.info(f"Đặt trailing stop ban đầu cho {symbol} {side}: {new_stop_loss:.2f}")
                    
                    # Kiểm tra nếu đã chạm stop loss
                    triggered = False
                    if side == 'LONG' and current_price <= state['current_stop_loss']:
                        triggered = True
                    elif side == 'SHORT' and current_price >= state['current_stop_loss']:
                        triggered = True
                    
                    if triggered:
                        profit_loss = unrealized_profit
                        profit_loss_pct = current_profit_pct
                        logger.info(f"TRAILING STOP TRIGGERED: {symbol} {side} tại giá {current_price:.2f}, SL={state['current_stop_loss']:.2f}, P/L={profit_loss:.2f} ({profit_loss_pct:.2f}%)")
                        
                        # Gửi thông báo qua Telegram
                        self._send_trailing_stop_notification(
                            symbol, side, entry_price, current_price, 
                            profit_loss, profit_loss_pct, state['timeframe']
                        )
                        
                        # Đóng vị thế (có thể thực hiện ở đây hoặc gửi tín hiệu để mô-đun khác xử lý)
                        # self._close_position(symbol, side)
                        
                        # Xóa khỏi danh sách tracking
                        del self.trailing_states[symbol]
                
                # Cập nhật thời gian xử lý
                state['last_update'] = datetime.now()
            
            # Xóa các vị thế đã đóng khỏi trạng thái tracking
            symbols_to_remove = [s for s in self.trailing_states if s not in current_symbols]
            for symbol in symbols_to_remove:
                logger.info(f"Vị thế {symbol} đã đóng, xóa khỏi danh sách theo dõi trailing stop")
                del self.trailing_states[symbol]
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật trailing stops: {e}")
            logger.debug(traceback.format_exc())
    
    def _send_trailing_stop_notification(self, symbol: str, side: str, entry_price: float,
                                      exit_price: float, profit_loss: float, 
                                      profit_loss_pct: float, timeframe: str):
        """
        Gửi thông báo khi trailing stop được kích hoạt
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Phía giao dịch ('LONG' hoặc 'SHORT')
            entry_price (float): Giá vào
            exit_price (float): Giá ra
            profit_loss (float): Lợi nhuận/lỗ
            profit_loss_pct (float): Lợi nhuận/lỗ (%)
            timeframe (str): Khung thời gian đang sử dụng
        """
        try:
            # Import telegram_notifier nếu có
            try:
                from telegram_notifier import send_message
                
                result_emoji = "✅" if profit_loss > 0 else "❌"
                message = (
                    f"{result_emoji} *TRAILING STOP: {symbol} {side}*\n"
                    f"💰 P/L: {profit_loss:.2f} USDT ({profit_loss_pct:.2f}%)\n"
                    f"📉 Giá vào: {entry_price:.2f} → Giá ra: {exit_price:.2f}\n"
                    f"⏱ Khung thời gian: {timeframe}\n"
                    f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                
                send_message(message)
            except ImportError:
                logger.warning("Không thể import telegram_notifier, bỏ qua gửi thông báo")
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo trailing stop: {e}")
    
    def run(self, interval: int = 5):
        """
        Chạy dịch vụ trailing stop liên tục
        
        Args:
            interval (int): Khoảng thời gian giữa các lần cập nhật (giây)
        """
        logger.info(f"Bắt đầu dịch vụ Enhanced Trailing Stop với chu kỳ {interval} giây")
        
        try:
            while True:
                self.update_trailing_stops()
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Dịch vụ Enhanced Trailing Stop đã dừng bởi người dùng")
        except Exception as e:
            logger.error(f"Lỗi không xử lý được trong dịch vụ Enhanced Trailing Stop: {e}")
            logger.debug(traceback.format_exc())
    
    def get_trailing_status(self) -> Dict:
        """
        Lấy trạng thái hiện tại của các trailing stop
        
        Returns:
            Dict: Trạng thái trailing stop
        """
        status = {
            'active_positions': len(self.trailing_states),
            'trailing_active': sum(1 for s in self.trailing_states.values() if s['trailing_activated']),
            'positions': {}
        }
        
        for symbol, state in self.trailing_states.items():
            status['positions'][symbol] = {
                'side': state['side'],
                'trailing_activated': state['trailing_activated'],
                'current_stop_loss': state['current_stop_loss'],
                'timeframe': state['timeframe'],
                'highest_price': state['highest_price'] if state['side'] == 'LONG' else None,
                'lowest_price': state['lowest_price'] if state['side'] == 'SHORT' else None
            }
        
        return status

def main():
    """Hàm chính để chạy dịch vụ trailing stop"""
    trailing_stop = EnhancedTrailingStop()
    trailing_stop.run()

if __name__ == "__main__":
    main()