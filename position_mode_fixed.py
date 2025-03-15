import logging
import os
import time
import json
from binance.client import Client
from binance.exceptions import BinanceAPIException

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('position_manager')

class PositionManager:
    def __init__(self, api_key=None, api_secret=None, testnet=True):
        """
        Khởi tạo Position Manager với các tham số kết nối API
        
        Args:
            api_key (str): Binance API key
            api_secret (str): Binance API secret
            testnet (bool): Kết nối đến testnet nếu True, mainnet nếu False
        """
        self.api_key = api_key or os.environ.get('BINANCE_API_KEY')
        self.api_secret = api_secret or os.environ.get('BINANCE_API_SECRET')
        self.testnet = testnet
        
        try:
            logger.info("Đang kết nối đến Binance API...")
            self.client = Client(api_key=self.api_key, api_secret=self.api_secret, testnet=self.testnet)
            server_time = self.client.get_server_time()
            logger.info(f"Thời gian máy chủ Binance: {server_time}")
            logger.info("Đã kết nối thành công với Binance API")
        except Exception as e:
            logger.error(f"Lỗi kết nối đến Binance API: {str(e)}")
            raise
        
        logger.info("Đã khởi tạo Position Manager")
    
    def get_current_position_mode(self):
        """
        Lấy chế độ vị thế hiện tại (Hedge Mode hoặc One-way Mode)
        
        Returns:
            bool: True nếu đang ở Hedge Mode, False nếu đang ở One-way Mode
        """
        try:
            mode_info = self.client.futures_get_position_mode()
            is_hedge_mode = mode_info.get('dualSidePosition', False)
            logger.info(f"Chế độ vị thế hiện tại: {'Hedge Mode' if is_hedge_mode else 'One-way Mode'}")
            return is_hedge_mode
        except BinanceAPIException as e:
            logger.error(f"Lỗi khi lấy thông tin chế độ vị thế: {str(e)}")
            return None
    
    def change_position_mode(self, enable_hedge_mode=True):
        """
        Chuyển đổi giữa Hedge Mode và One-way Mode
        
        Args:
            enable_hedge_mode (bool): True để bật Hedge Mode, False để bật One-way Mode
        
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        current_mode = self.get_current_position_mode()
        
        # Nếu đã ở chế độ muốn chuyển đến, không cần thay đổi
        if current_mode == enable_hedge_mode:
            logger.info(f"Đã ở chế độ {'Hedge Mode' if enable_hedge_mode else 'One-way Mode'} rồi, không cần thay đổi")
            return True
        
        # Kiểm tra nếu có vị thế đang mở, cần đóng trước khi chuyển chế độ
        positions = self.client.futures_position_information()
        open_positions = [p for p in positions if float(p['positionAmt']) != 0]
        
        if open_positions:
            logger.warning(f"Có {len(open_positions)} vị thế đang mở, cần đóng trước khi chuyển chế độ")
            logger.info("Chi tiết vị thế đang mở:")
            for pos in open_positions:
                logger.info(f"  {pos['symbol']}: {pos['positionAmt']} (Side: {pos['positionSide']})")
            
            # Có thể thêm code để tự động đóng vị thế ở đây nếu cần
            return False
        
        # Thực hiện chuyển đổi chế độ
        try:
            mode_name = 'Hedge Mode' if enable_hedge_mode else 'One-way Mode'
            logger.info(f"Đang chuyển sang {mode_name}...")
            
            response = self.client.futures_change_position_mode(dualSidePosition=enable_hedge_mode)
            
            if response.get('code') == 200 or response == {}:
                logger.info(f"Đã chuyển sang {mode_name} thành công")
                return True
            else:
                logger.error(f"Chuyển sang {mode_name} thất bại: {response}")
                return False
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi khi chuyển chế độ vị thế: {str(e)}")
            return False
    
    def open_position(self, symbol, side, quantity, position_side=None, stop_loss=None, take_profit=None, leverage=5):
        """
        Mở vị thế với các tham số được chỉ định
        
        Args:
            symbol (str): Mã cặp giao dịch (ví dụ: 'BTCUSDT')
            side (str): 'BUY' hoặc 'SELL'
            quantity (float): Số lượng muốn giao dịch
            position_side (str): 'LONG', 'SHORT', hoặc None (cho One-way Mode)
            stop_loss (float): Giá stop loss (tùy chọn)
            take_profit (float): Giá take profit (tùy chọn)
            leverage (int): Đòn bẩy (mặc định: 5)
        
        Returns:
            dict: Thông tin đơn hàng nếu thành công, None nếu thất bại
        """
        try:
            # Kiểm tra và thiết lập đòn bẩy
            self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            logger.info(f"Đã thiết lập đòn bẩy {leverage}x cho {symbol}")
            
            # Xác định chế độ vị thế hiện tại
            is_hedge_mode = self.get_current_position_mode()
            
            # Chuẩn bị tham số cho lệnh
            order_params = {
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'type': 'MARKET'
            }
            
            # Trong Hedge Mode, luôn cần tham số positionSide
            if is_hedge_mode:
                if not position_side:
                    position_side = 'LONG' if side == 'BUY' else 'SHORT'
                order_params['positionSide'] = position_side
            
            # Thực hiện lệnh
            logger.info(f"Đang mở vị thế {side} {quantity} {symbol} " + 
                      (f"với positionSide={position_side}" if is_hedge_mode else ""))
            
            order = self.client.futures_create_order(**order_params)
            logger.info(f"Đã mở vị thế thành công: {order}")
            
            # Đặt Stop Loss nếu có
            if stop_loss:
                self._set_stop_loss(symbol, side, quantity, stop_loss, position_side, is_hedge_mode)
            
            # Đặt Take Profit nếu có
            if take_profit:
                self._set_take_profit(symbol, side, quantity, take_profit, position_side, is_hedge_mode)
            
            return order
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi khi mở vị thế: {str(e)}")
            
            # Xử lý một số lỗi phổ biến
            if "Order's notional must be no smaller than" in str(e):
                min_notional = str(e).split("than")[1].strip().split(" ")[0]
                logger.warning(f"Giá trị lệnh quá nhỏ, cần tối thiểu {min_notional} USDT")
                
                # Có thể tự động điều chỉnh quantity ở đây để đáp ứng yêu cầu
            
            return None
    
    def _set_stop_loss(self, symbol, side, quantity, stop_price, position_side, is_hedge_mode):
        """
        Đặt lệnh stop loss
        """
        try:
            # Trong Hedge Mode, cần đảo ngược side cho SL
            sl_side = 'SELL' if side == 'BUY' else 'BUY'
            
            sl_params = {
                'symbol': symbol,
                'side': sl_side,
                'type': 'STOP_MARKET',
                'quantity': quantity,
                'stopPrice': stop_price,
                'closePosition': True
            }
            
            # Trong Hedge Mode, luôn cần positionSide
            if is_hedge_mode:
                sl_params['positionSide'] = position_side
            
            # Trong một số trường hợp, không cần tham số reduceOnly
            sl_params['reduceOnly'] = True
            
            sl_order = self.client.futures_create_order(**sl_params)
            logger.info(f"Đã đặt Stop Loss tại {stop_price}: {sl_order}")
            return sl_order
        
        except BinanceAPIException as e:
            # Nếu lỗi liên quan đến reduceOnly, thử lại không có tham số này
            if "Parameter reduceOnly sent when not required" in str(e):
                logger.warning("Lỗi reduceOnly, thử lại không có tham số này")
                sl_params.pop('reduceOnly', None)
                try:
                    sl_order = self.client.futures_create_order(**sl_params)
                    logger.info(f"Đã đặt Stop Loss tại {stop_price} (không có reduceOnly): {sl_order}")
                    return sl_order
                except BinanceAPIException as e2:
                    logger.error(f"Vẫn lỗi khi đặt Stop Loss: {str(e2)}")
            else:
                logger.error(f"Lỗi khi đặt Stop Loss: {str(e)}")
            
            return None
    
    def _set_take_profit(self, symbol, side, quantity, take_profit_price, position_side, is_hedge_mode):
        """
        Đặt lệnh take profit
        """
        try:
            # Trong Hedge Mode, cần đảo ngược side cho TP
            tp_side = 'SELL' if side == 'BUY' else 'BUY'
            
            tp_params = {
                'symbol': symbol,
                'side': tp_side,
                'type': 'TAKE_PROFIT_MARKET',
                'quantity': quantity,
                'stopPrice': take_profit_price,
                'closePosition': True
            }
            
            # Trong Hedge Mode, luôn cần positionSide
            if is_hedge_mode:
                tp_params['positionSide'] = position_side
            
            # Trong một số trường hợp, không cần tham số reduceOnly
            tp_params['reduceOnly'] = True
            
            tp_order = self.client.futures_create_order(**tp_params)
            logger.info(f"Đã đặt Take Profit tại {take_profit_price}: {tp_order}")
            return tp_order
        
        except BinanceAPIException as e:
            # Nếu lỗi liên quan đến reduceOnly, thử lại không có tham số này
            if "Parameter reduceOnly sent when not required" in str(e):
                logger.warning("Lỗi reduceOnly, thử lại không có tham số này")
                tp_params.pop('reduceOnly', None)
                try:
                    tp_order = self.client.futures_create_order(**tp_params)
                    logger.info(f"Đã đặt Take Profit tại {take_profit_price} (không có reduceOnly): {tp_order}")
                    return tp_order
                except BinanceAPIException as e2:
                    logger.error(f"Vẫn lỗi khi đặt Take Profit: {str(e2)}")
            else:
                logger.error(f"Lỗi khi đặt Take Profit: {str(e)}")
            
            return None
    
    def close_position(self, symbol, position_side=None):
        """
        Đóng một vị thế cụ thể
        
        Args:
            symbol (str): Mã cặp giao dịch
            position_side (str): 'LONG', 'SHORT', hoặc None (cho One-way Mode)
        
        Returns:
            dict: Thông tin đơn hàng đóng vị thế nếu thành công, None nếu thất bại
        """
        try:
            # Lấy thông tin vị thế
            positions = self.client.futures_position_information(symbol=symbol)
            
            # Xác định chế độ vị thế hiện tại
            is_hedge_mode = self.get_current_position_mode()
            
            # Lọc vị thế cần đóng
            position_to_close = None
            for pos in positions:
                amt = float(pos['positionAmt'])
                if amt == 0:
                    continue
                
                if is_hedge_mode:
                    # Trong Hedge Mode, chỉ đóng vị thế với positionSide được chỉ định
                    if position_side and pos['positionSide'] == position_side:
                        position_to_close = pos
                        break
                else:
                    # Trong One-way Mode, đóng vị thế duy nhất
                    position_to_close = pos
                    break
            
            if not position_to_close:
                logger.warning(f"Không tìm thấy vị thế {position_side if position_side else ''} để đóng cho {symbol}")
                return None
            
            # Chuẩn bị tham số để đóng vị thế
            amt = abs(float(position_to_close['positionAmt']))
            side = 'SELL' if float(position_to_close['positionAmt']) > 0 else 'BUY'
            
            close_params = {
                'symbol': symbol,
                'side': side,
                'type': 'MARKET',
                'quantity': amt
            }
            
            # Trong Hedge Mode, luôn cần positionSide
            if is_hedge_mode:
                close_params['positionSide'] = position_to_close['positionSide']
            
            # Đóng vị thế
            logger.info(f"Đang đóng vị thế {symbol}" + 
                      (f" với positionSide={position_to_close['positionSide']}" if is_hedge_mode else ""))
            
            close_order = self.client.futures_create_order(**close_params)
            logger.info(f"Đã đóng vị thế thành công: {close_order}")
            
            return close_order
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi khi đóng vị thế: {str(e)}")
            return None
    
    def get_open_positions(self):
        """
        Lấy danh sách tất cả các vị thế đang mở
        
        Returns:
            list: Danh sách các vị thế đang mở
        """
        try:
            positions = self.client.futures_position_information()
            open_positions = [p for p in positions if float(p['positionAmt']) != 0]
            
            logger.info(f"Tìm thấy {len(open_positions)} vị thế đang mở")
            
            # Format lại thông tin vị thế để dễ đọc
            formatted_positions = []
            for pos in open_positions:
                formatted_positions.append({
                    'symbol': pos['symbol'],
                    'amount': float(pos['positionAmt']),
                    'entryPrice': float(pos['entryPrice']),
                    'markPrice': float(pos['markPrice']),
                    'unRealizedProfit': float(pos['unRealizedProfit']),
                    'liquidationPrice': float(pos['liquidationPrice']),
                    'leverage': int(pos['leverage']),
                    'positionSide': pos['positionSide']
                })
            
            return formatted_positions
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi khi lấy thông tin vị thế: {str(e)}")
            return []
    
    def add_trailing_stop_to_position(self, symbol, activation_price, callback_rate, position_side=None):
        """
        Thêm trailing stop cho vị thế
        
        Args:
            symbol (str): Mã cặp giao dịch
            activation_price (float): Giá kích hoạt trailing stop
            callback_rate (float): Tỉ lệ callback (từ 0.1% đến 5%)
            position_side (str): 'LONG', 'SHORT', hoặc None (cho One-way Mode)
        
        Returns:
            dict: Thông tin đơn hàng trailing stop nếu thành công, None nếu thất bại
        """
        try:
            # Lấy thông tin vị thế
            positions = self.client.futures_position_information(symbol=symbol)
            
            # Xác định chế độ vị thế hiện tại
            is_hedge_mode = self.get_current_position_mode()
            
            # Lọc vị thế cần thêm trailing stop
            position_to_add = None
            for pos in positions:
                amt = float(pos['positionAmt'])
                if amt == 0:
                    continue
                
                if is_hedge_mode:
                    # Trong Hedge Mode, chỉ thêm cho vị thế với positionSide được chỉ định
                    if position_side and pos['positionSide'] == position_side:
                        position_to_add = pos
                        break
                else:
                    # Trong One-way Mode, thêm cho vị thế duy nhất
                    position_to_add = pos
                    break
            
            if not position_to_add:
                logger.warning(f"Không tìm thấy vị thế {position_side if position_side else ''} để thêm trailing stop cho {symbol}")
                return None
            
            # Chuẩn bị tham số cho trailing stop
            amt = abs(float(position_to_add['positionAmt']))
            side = 'SELL' if float(position_to_add['positionAmt']) > 0 else 'BUY'
            
            ts_params = {
                'symbol': symbol,
                'side': side,
                'type': 'TRAILING_STOP_MARKET',
                'quantity': amt,
                'callbackRate': callback_rate,
                'activationPrice': activation_price,
                'reduceOnly': True
            }
            
            # Trong Hedge Mode, luôn cần positionSide
            if is_hedge_mode:
                ts_params['positionSide'] = position_to_add['positionSide']
            
            # Thêm trailing stop
            logger.info(f"Đang thêm trailing stop cho {symbol} với activation_price={activation_price}, callback_rate={callback_rate}%" + 
                      (f", positionSide={position_to_add['positionSide']}" if is_hedge_mode else ""))
            
            ts_order = self.client.futures_create_order(**ts_params)
            logger.info(f"Đã thêm trailing stop thành công: {ts_order}")
            
            return ts_order
        
        except BinanceAPIException as e:
            # Xử lý lỗi reduceOnly nếu cần
            if "Parameter reduceOnly sent when not required" in str(e):
                logger.warning("Lỗi reduceOnly, thử lại không có tham số này")
                ts_params.pop('reduceOnly', None)
                try:
                    ts_order = self.client.futures_create_order(**ts_params)
                    logger.info(f"Đã thêm trailing stop thành công (không có reduceOnly): {ts_order}")
                    return ts_order
                except BinanceAPIException as e2:
                    logger.error(f"Vẫn lỗi khi thêm trailing stop: {str(e2)}")
            else:
                logger.error(f"Lỗi khi thêm trailing stop: {str(e)}")
            
            return None

# Hàm test
def test_position_manager():
    """
    Thử nghiệm các chức năng của PositionManager
    """
    logger.info("=== BẮT ĐẦU KIỂM TRA POSITION MANAGER ===")
    
    # Khởi tạo PositionManager
    pm = PositionManager(testnet=True)
    
    # 1. Kiểm tra chế độ vị thế hiện tại
    is_hedge_mode = pm.get_current_position_mode()
    logger.info(f"Chế độ vị thế hiện tại: {'Hedge Mode' if is_hedge_mode else 'One-way Mode'}")
    
    # 2. Lấy danh sách vị thế đang mở
    open_positions = pm.get_open_positions()
    logger.info(f"Vị thế đang mở: {json.dumps(open_positions, indent=2)}")
    
    # 3. Test mở vị thế trong Hedge Mode
    if is_hedge_mode:
        logger.info("Test mở vị thế LONG và SHORT trong Hedge Mode")
        
        # Mở vị thế LONG
        long_order = pm.open_position(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.001,
            position_side="LONG",
            stop_loss=80000,  # Giả sử BTC ~85000
            take_profit=90000,
            leverage=5
        )
        
        if long_order:
            logger.info(f"Đã mở vị thế LONG thành công: {long_order}")
        
        # Đợi 2 giây
        time.sleep(2)
        
        # Mở vị thế SHORT
        short_order = pm.open_position(
            symbol="BTCUSDT",
            side="SELL",
            quantity=0.001,
            position_side="SHORT",
            stop_loss=90000,
            take_profit=80000,
            leverage=5
        )
        
        if short_order:
            logger.info(f"Đã mở vị thế SHORT thành công: {short_order}")
    
    # 4. Test chuyển đổi chế độ vị thế (phải đóng vị thế trước)
    logger.info("Kiểm tra chuyển đổi chế độ vị thế")
    open_positions = pm.get_open_positions()
    
    if open_positions:
        logger.info(f"Cần đóng {len(open_positions)} vị thế trước khi chuyển chế độ")
        
        # Đóng từng vị thế
        for pos in open_positions:
            close_order = pm.close_position(
                symbol=pos['symbol'],
                position_side=pos['positionSide'] if is_hedge_mode else None
            )
            
            if close_order:
                logger.info(f"Đã đóng vị thế {pos['symbol']} {pos['positionSide'] if is_hedge_mode else ''} thành công")
            
            # Đợi 1 giây
            time.sleep(1)
    
    # Kiểm tra lại vị thế đang mở
    open_positions = pm.get_open_positions()
    
    if not open_positions:
        # Chuyển đổi chế độ
        new_mode = not is_hedge_mode
        change_result = pm.change_position_mode(enable_hedge_mode=new_mode)
        
        if change_result:
            logger.info(f"Đã chuyển sang {'Hedge Mode' if new_mode else 'One-way Mode'} thành công")
        else:
            logger.warning("Chuyển đổi chế độ vị thế thất bại")
    else:
        logger.warning("Vẫn còn vị thế đang mở, không thể chuyển đổi chế độ")
    
    logger.info("=== KẾT THÚC KIỂM TRA POSITION MANAGER ===")

if __name__ == "__main__":
    # Chạy test
    test_position_manager()