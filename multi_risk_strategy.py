import os
import sys
import logging
import numpy as np
import pandas as pd
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('multi_risk_strategy.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('multi_risk_strategy')

class MultiRiskStrategy:
    """
    Chiến lược giao dịch đa mức rủi ro với khả năng thích ứng theo điều kiện thị trường
    """
    
    def __init__(self, risk_level=0.15, lookback_period=14):
        """
        Khởi tạo chiến lược giao dịch
        
        Args:
            risk_level (float): Mức rủi ro (0.1-0.25)
            lookback_period (int): Số nến quá khứ để xem xét
        """
        self.risk_level = risk_level
        self.lookback_period = lookback_period
        logger.info(f"Khởi tạo MultiRiskStrategy với risk_level={risk_level}, lookback_period={lookback_period}")
    
    def calculate_indicators(self, data):
        """
        Tính toán các chỉ báo kỹ thuật
        
        Args:
            data (pd.DataFrame): DataFrame chứa dữ liệu giá
            
        Returns:
            pd.DataFrame: DataFrame với các chỉ báo đã tính
        """
        # Kiểm tra dữ liệu đầu vào
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in data.columns for col in required_columns):
            # Thử chuyển đổi từ chữ thường sang chữ hoa
            lowercase_cols = ['open', 'high', 'low', 'close', 'volume']
            if all(col in data.columns for col in lowercase_cols):
                data = data.rename(columns={
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                })
            else:
                logger.error(f"Thiếu các cột dữ liệu cần thiết. Yêu cầu: {required_columns}, Hiện có: {data.columns.tolist()}")
                return None
        
        # Copy dữ liệu để tránh ảnh hưởng đến dữ liệu gốc
        df = data.copy()
        
        # 1. Tính RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=self.lookback_period).mean()
        avg_loss = loss.rolling(window=self.lookback_period).mean()
        
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 2. Tính MACD
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 3. Tính Bollinger Bands
        df['sma20'] = df['Close'].rolling(window=20).mean()
        df['std20'] = df['Close'].rolling(window=20).std()
        df['upper_band'] = df['sma20'] + (df['std20'] * 2)
        df['lower_band'] = df['sma20'] - (df['std20'] * 2)
        
        # 4. Tính ATR (Average True Range)
        tr1 = df['High'] - df['Low']
        tr2 = abs(df['High'] - df['Close'].shift())
        tr3 = abs(df['Low'] - df['Close'].shift())
        df['tr'] = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        df['atr'] = df['tr'].rolling(window=14).mean()
        
        # 5. Tính Stochastic Oscillator
        df['lowest_14'] = df['Low'].rolling(window=14).min()
        df['highest_14'] = df['High'].rolling(window=14).max()
        df['%K'] = (df['Close'] - df['lowest_14']) / (df['highest_14'] - df['lowest_14']) * 100
        df['%D'] = df['%K'].rolling(window=3).mean()
        
        # 6. Detect Market Condition
        df['market_condition'] = self._detect_market_condition(df)
        
        # Loại bỏ dữ liệu NaN
        return df.dropna()
    
    def _detect_market_condition(self, df):
        """
        Phát hiện điều kiện thị trường dựa trên dữ liệu giá
        
        Args:
            df (pd.DataFrame): DataFrame đã có các chỉ báo
            
        Returns:
            pd.Series: Series chứa điều kiện thị trường cho mỗi điểm dữ liệu
        """
        # Tạo mảng để lưu kết quả
        conditions = np.full(len(df), 'NEUTRAL', dtype=object)
        
        # Số nến để xác định xu hướng
        trend_period = min(50, len(df) // 2)
        
        # Tính phần trăm thay đổi giá trong giai đoạn xu hướng
        for i in range(trend_period, len(df)):
            # Tính % thay đổi từ đầu kỳ
            price_change = (df['Close'].iloc[i] - df['Close'].iloc[i - trend_period]) / df['Close'].iloc[i - trend_period] * 100
            
            # Biến động (dựa trên ATR so với giá)
            if 'atr' in df.columns and not pd.isna(df['atr'].iloc[i]):
                volatility = df['atr'].iloc[i] / df['Close'].iloc[i] * 100
            else:
                volatility = 0
            
            # Xác định điều kiện thị trường
            if price_change > 5:  # Tăng > 5%
                if volatility > 3:
                    conditions[i] = 'VOLATILE'
                else:
                    conditions[i] = 'BULL'
            elif price_change < -5:  # Giảm > 5%
                if volatility > 3:
                    conditions[i] = 'VOLATILE'
                else:
                    conditions[i] = 'BEAR'
            else:  # Đi ngang
                if volatility > 2:
                    conditions[i] = 'VOLATILE'
                else:
                    conditions[i] = 'SIDEWAYS'
        
        return pd.Series(conditions, index=df.index)
    
    def generate_signals(self, data):
        """
        Tạo tín hiệu giao dịch
        
        Args:
            data (pd.DataFrame): DataFrame đã có các chỉ báo
            
        Returns:
            dict: Dictionary chứa các tín hiệu giao dịch
        """
        signals = {}
        
        # Điều chỉnh tín hiệu dựa trên mức rủi ro
        for i in range(1, len(data)):
            # Xác định điều kiện thị trường
            market_condition = data['market_condition'].iloc[i]
            
            # Tín hiệu RSI
            rsi = data['rsi'].iloc[i]
            prev_rsi = data['rsi'].iloc[i-1]
            
            # Tín hiệu MACD
            macd = data['macd'].iloc[i]
            macd_signal = data['macd_signal'].iloc[i]
            prev_macd = data['macd'].iloc[i-1]
            prev_macd_signal = data['macd_signal'].iloc[i-1]
            
            # Tín hiệu Bollinger Bands
            close = data['Close'].iloc[i]
            upper_band = data['upper_band'].iloc[i]
            lower_band = data['lower_band'].iloc[i]
            
            # Tính SL và TP dựa trên ATR và mức rủi ro
            atr = data['atr'].iloc[i]
            
            # Điều chỉnh hệ số ATR dựa trên mức rủi ro
            sl_factor = 1.5  # Mặc định
            tp_factor = 2.0  # Mặc định
            
            if self.risk_level <= 0.10:  # Rủi ro thấp
                sl_factor = 2.0  # Stop loss xa hơn
                tp_factor = 1.5  # Take profit gần hơn
            elif self.risk_level <= 0.15:  # Rủi ro trung bình
                sl_factor = 1.5
                tp_factor = 2.0
            elif self.risk_level <= 0.20:  # Rủi ro cao
                sl_factor = 1.0  # Stop loss gần hơn
                tp_factor = 2.5  # Take profit xa hơn
            else:  # Rủi ro rất cao (> 0.20)
                sl_factor = 0.8
                tp_factor = 3.0
            
            # Tín hiệu mua (LONG)
            long_signal = False
            long_reason = []
            
            # RSI vượt lên từ vùng quá bán
            if prev_rsi < 30 and rsi >= 30:
                long_signal = True
                long_reason.append(f"RSI vượt lên từ vùng quá bán ({rsi:.2f})")
            
            # MACD cắt lên đường tín hiệu
            if prev_macd < prev_macd_signal and macd >= macd_signal and macd < 0:
                long_signal = True
                long_reason.append(f"MACD cắt lên đường tín hiệu (histogram: {macd - macd_signal:.6f})")
            
            # Giá chạm Bollinger Bands dưới
            if close <= lower_band:
                long_signal = True
                long_reason.append(f"Giá chạm Bollinger Band dưới ({close:.2f} <= {lower_band:.2f})")
            
            # Chỉ tạo tín hiệu nếu có điều kiện thoả mãn
            if long_signal:
                # Tính SL và TP
                stop_loss = close - (atr * sl_factor)
                take_profit = close + (atr * tp_factor)
                
                signals[i] = {
                    'index': i,
                    'timestamp': data.index[i],
                    'price': close,
                    'type': 'LONG',
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'reason': long_reason,
                    'market_condition': market_condition
                }
            
            # Tín hiệu bán (SHORT)
            short_signal = False
            short_reason = []
            
            # RSI vượt xuống từ vùng quá mua
            if prev_rsi > 70 and rsi <= 70:
                short_signal = True
                short_reason.append(f"RSI vượt xuống từ vùng quá mua ({rsi:.2f})")
            
            # MACD cắt xuống đường tín hiệu
            if prev_macd > prev_macd_signal and macd <= macd_signal and macd > 0:
                short_signal = True
                short_reason.append(f"MACD cắt xuống đường tín hiệu (histogram: {macd - macd_signal:.6f})")
            
            # Giá chạm Bollinger Bands trên
            if close >= upper_band:
                short_signal = True
                short_reason.append(f"Giá chạm Bollinger Band trên ({close:.2f} >= {upper_band:.2f})")
            
            # Chỉ tạo tín hiệu nếu có điều kiện thoả mãn
            if short_signal:
                # Tính SL và TP
                stop_loss = close + (atr * sl_factor)
                take_profit = close - (atr * tp_factor)
                
                signals[i] = {
                    'index': i,
                    'timestamp': data.index[i],
                    'price': close,
                    'type': 'SHORT',
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'reason': short_reason,
                    'market_condition': market_condition
                }
        
        logger.info(f"Đã tạo {len(signals)} tín hiệu giao dịch")
        return signals
    
    def apply_strategy(self, data):
        """
        Áp dụng chiến lược vào dữ liệu
        
        Args:
            data (pd.DataFrame): DataFrame chứa dữ liệu giá
            
        Returns:
            dict: Dictionary chứa các tín hiệu giao dịch
        """
        # Tính toán các chỉ báo
        df_indicators = self.calculate_indicators(data)
        if df_indicators is None:
            logger.error("Không thể tính toán các chỉ báo")
            return {}
        
        # Tạo tín hiệu giao dịch
        signals = self.generate_signals(df_indicators)
        
        return signals
    
    def backtest(self, data, balance=10000, position_size=None):
        """
        Chạy backtest chiến lược
        
        Args:
            data (pd.DataFrame): DataFrame chứa dữ liệu giá
            balance (float): Số dư ban đầu
            position_size (float, optional): Kích thước vị thế cố định, nếu None sẽ tính dựa trên % rủi ro
            
        Returns:
            dict: Kết quả backtest
        """
        # Tính toán các chỉ báo
        df = self.calculate_indicators(data)
        if df is None:
            logger.error("Không thể tính toán các chỉ báo")
            return None
        
        # Tạo tín hiệu giao dịch
        signals = self.generate_signals(df)
        
        # Thực hiện backtest
        initial_balance = balance
        current_balance = balance
        position = None
        trades = []
        equity_curve = [balance]
        
        for i in range(1, len(df)):
            current_price = df['Close'].iloc[i]
            
            # Xử lý vị thế đang mở
            if position is not None:
                # Kiểm tra điều kiện chốt lời
                if (position['type'] == 'LONG' and current_price >= position['take_profit']) or \
                   (position['type'] == 'SHORT' and current_price <= position['take_profit']):
                    # Tính lợi nhuận
                    if position['type'] == 'LONG':
                        profit = position['qty'] * (current_price - position['entry_price'])
                    else:
                        profit = position['qty'] * (position['entry_price'] - current_price)
                    
                    # Cập nhật số dư
                    current_balance += profit
                    
                    # Lưu thông tin giao dịch
                    trade = {
                        'entry_time': position['time'],
                        'exit_time': df.index[i],
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'qty': position['qty'],
                        'profit': profit,
                        'profit_pct': (profit / (position['entry_price'] * position['qty'])) * 100,
                        'exit_reason': 'take_profit',
                        'market_condition': position['market_condition']
                    }
                    trades.append(trade)
                    
                    # Đóng vị thế
                    position = None
                
                # Kiểm tra điều kiện cắt lỗ
                elif (position['type'] == 'LONG' and current_price <= position['stop_loss']) or \
                     (position['type'] == 'SHORT' and current_price >= position['stop_loss']):
                    # Tính lỗ
                    if position['type'] == 'LONG':
                        loss = position['qty'] * (current_price - position['entry_price'])
                    else:
                        loss = position['qty'] * (position['entry_price'] - current_price)
                    
                    # Cập nhật số dư
                    current_balance += loss
                    
                    # Lưu thông tin giao dịch
                    trade = {
                        'entry_time': position['time'],
                        'exit_time': df.index[i],
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'qty': position['qty'],
                        'profit': loss,
                        'profit_pct': (loss / (position['entry_price'] * position['qty'])) * 100,
                        'exit_reason': 'stop_loss',
                        'market_condition': position['market_condition']
                    }
                    trades.append(trade)
                    
                    # Đóng vị thế
                    position = None
            
            # Mở vị thế mới nếu có tín hiệu và không có vị thế đang mở
            if i in signals and position is None:
                signal = signals[i]
                
                # Tính kích thước vị thế
                if position_size is not None:
                    qty = position_size
                else:
                    risk_amount = current_balance * self.risk_level
                    
                    if signal['type'] == 'LONG':
                        sl_distance = signal['price'] - signal['stop_loss']
                    else:
                        sl_distance = signal['stop_loss'] - signal['price']
                    
                    # Đảm bảo sl_distance > 0
                    sl_distance = max(sl_distance, signal['price'] * 0.005)
                    qty = risk_amount / sl_distance
                
                # Mở vị thế
                position = {
                    'time': signal['timestamp'],
                    'type': signal['type'],
                    'entry_price': signal['price'],
                    'qty': qty,
                    'stop_loss': signal['stop_loss'],
                    'take_profit': signal['take_profit'],
                    'market_condition': signal['market_condition']
                }
            
            # Cập nhật equity curve
            equity_curve.append(current_balance)
        
        # Đóng vị thế cuối cùng nếu còn
        if position is not None:
            # Đóng ở giá cuối cùng
            final_price = df['Close'].iloc[-1]
            
            # Tính lãi/lỗ
            if position['type'] == 'LONG':
                profit = position['qty'] * (final_price - position['entry_price'])
            else:
                profit = position['qty'] * (position['entry_price'] - final_price)
            
            # Cập nhật số dư
            current_balance += profit
            
            # Lưu thông tin giao dịch
            trade = {
                'entry_time': position['time'],
                'exit_time': df.index[-1],
                'type': position['type'],
                'entry_price': position['entry_price'],
                'exit_price': final_price,
                'qty': position['qty'],
                'profit': profit,
                'profit_pct': (profit / (position['entry_price'] * position['qty'])) * 100,
                'exit_reason': 'end_of_data',
                'market_condition': position['market_condition']
            }
            trades.append(trade)
            
            # Cập nhật equity curve
            equity_curve[-1] = current_balance
        
        # Tính các chỉ số hiệu suất
        profit_loss = current_balance - initial_balance
        profit_loss_pct = (profit_loss / initial_balance) * 100
        
        # Tính drawdown
        peak = initial_balance
        drawdowns = []
        max_drawdown = 0
        max_drawdown_pct = 0
        
        for balance in equity_curve:
            if balance > peak:
                peak = balance
            drawdown = peak - balance
            drawdown_pct = (drawdown / peak) * 100
            drawdowns.append(drawdown_pct)
            
            if drawdown_pct > max_drawdown_pct:
                max_drawdown = drawdown
                max_drawdown_pct = drawdown_pct
        
        # Tính win rate
        winning_trades = [t for t in trades if t['profit'] > 0]
        losing_trades = [t for t in trades if t['profit'] <= 0]
        win_rate = len(winning_trades) / len(trades) * 100 if trades else 0
        
        # Tính profit factor
        total_profit = sum([t['profit'] for t in winning_trades]) if winning_trades else 0
        total_loss = sum([abs(t['profit']) for t in losing_trades]) if losing_trades else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Phân tích theo điều kiện thị trường
        trades_by_market = {}
        for trade in trades:
            condition = trade['market_condition']
            if condition not in trades_by_market:
                trades_by_market[condition] = []
            trades_by_market[condition].append(trade)
        
        market_condition_performance = {}
        for condition, condition_trades in trades_by_market.items():
            winning = len([t for t in condition_trades if t['profit'] > 0])
            win_rate_by_market = winning / len(condition_trades) * 100 if condition_trades else 0
            avg_profit = sum([t['profit'] for t in condition_trades]) / len(condition_trades) if condition_trades else 0
            
            market_condition_performance[condition] = {
                'trades': len(condition_trades),
                'win_rate': win_rate_by_market,
                'avg_profit': avg_profit
            }
        
        # Kết quả backtest
        backtest_result = {
            'initial_balance': initial_balance,
            'final_balance': current_balance,
            'profit_loss': profit_loss,
            'profit_loss_pct': profit_loss_pct,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown_pct,
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'trades': trades,
            'equity_curve': equity_curve,
            'market_condition_performance': market_condition_performance
        }
        
        logger.info(f"Kết quả backtest: Profit/Loss: {profit_loss_pct:.2f}%, Win Rate: {win_rate:.2f}%, "
                  f"Max Drawdown: {max_drawdown_pct:.2f}%, Profit Factor: {profit_factor:.2f}")
        
        return backtest_result

# Hàm test
def test_multi_risk_strategy():
    """Test chiến lược đa mức rủi ro"""
    # Tạo dữ liệu mẫu
    import yfinance as yf
    
    # Tải dữ liệu BTC
    data = yf.download("BTC-USD", start="2024-01-01", end="2024-03-01")
    
    # Tạo chiến lược
    strategy = MultiRiskStrategy(risk_level=0.15)
    
    # Chạy backtest
    backtest_result = strategy.backtest(data)
    
    if backtest_result:
        print("\n=== KẾT QUẢ BACKTEST ===")
        print(f"Lợi nhuận: ${backtest_result['profit_loss']:.2f} ({backtest_result['profit_loss_pct']:.2f}%)")
        print(f"Win Rate: {backtest_result['win_rate']:.2f}%")
        print(f"Max Drawdown: {backtest_result['max_drawdown_pct']:.2f}%")
        print(f"Profit Factor: {backtest_result['profit_factor']:.2f}")
        print(f"Số lệnh: {backtest_result['total_trades']}")
        
        # Hiệu suất theo điều kiện thị trường
        print("\n=== HIỆU SUẤT THEO ĐIỀU KIỆN THỊ TRƯỜNG ===")
        for condition, perf in backtest_result['market_condition_performance'].items():
            print(f"{condition}: {perf['trades']} lệnh, Win Rate: {perf['win_rate']:.2f}%, Lợi nhuận TB: ${perf['avg_profit']:.2f}")

if __name__ == "__main__":
    test_multi_risk_strategy()