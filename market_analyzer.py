#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module phân tích thị trường cho hệ thống giao dịch
Tương tác với Binance API để lấy dữ liệu thị trường thực tế
"""

import os
import logging
import time
import json
import traceback
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from binance.client import Client
from binance.exceptions import BinanceAPIException
import talib

# Cấu hình logging
logger = logging.getLogger("market_analyzer")

class MarketAnalyzer:
    """
    Lớp phân tích thị trường, tương tác với Binance API
    và cung cấp các phân tích kỹ thuật
    """
    
    def __init__(self, api_key=None, api_secret=None, testnet=True):
        """
        Khởi tạo với thông tin API
        
        :param api_key: Binance API key
        :param api_secret: Binance API secret
        :param testnet: Sử dụng testnet (True) hoặc mainnet (False)
        """
        self.api_key = api_key or os.environ.get("BINANCE_TESTNET_API_KEY")
        self.api_secret = api_secret or os.environ.get("BINANCE_TESTNET_API_SECRET")
        self.testnet = testnet
        self.client = None
        self.connect()
    
    def connect(self):
        """Kết nối tới Binance API"""
        try:
            self.client = Client(
                api_key=self.api_key,
                api_secret=self.api_secret,
                testnet=self.testnet
            )
            # Kiểm tra kết nối
            self.client.ping()
            logger.info("✅ Kết nối Binance API thành công")
            return True
        except BinanceAPIException as e:
            logger.error(f"❌ Lỗi kết nối Binance API: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Lỗi không xác định khi kết nối Binance API: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def is_connected(self):
        """Kiểm tra xem API có kết nối không"""
        if not self.client:
            return False
        
        try:
            self.client.ping()
            return True
        except:
            return False
    
    def reconnect(self):
        """Kết nối lại nếu mất kết nối"""
        logger.info("Đang kết nối lại với Binance API...")
        return self.connect()
    
    def get_market_overview(self):
        """
        Lấy tổng quan thị trường cho 5 coin phổ biến
        
        :return: Dictionary chứa thông tin thị trường
        """
        if not self.is_connected() and not self.reconnect():
            logger.error("Không thể kết nối tới Binance API")
            return {"status": "error", "message": "Không thể kết nối tới Binance API"}
        
        try:
            symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]
            market_data = []
            
            for symbol in symbols:
                # Lấy thông tin ticker
                ticker = self.client.get_ticker(symbol=symbol)
                
                # Lấy thông tin giao dịch 24h
                ticker_24h = self.client.get_ticker(symbol=symbol)
                
                # Đánh giá sơ bộ dựa trên thay đổi giá
                price_change = float(ticker_24h['priceChangePercent'])
                if price_change > 3:
                    signal = "Mua"
                    strength = "Mạnh" if price_change > 5 else "Trung bình"
                elif price_change < -3:
                    signal = "Bán"
                    strength = "Mạnh" if price_change < -5 else "Trung bình"
                else:
                    signal = "Giữ"
                    strength = "Yếu"
                
                market_data.append({
                    'symbol': symbol,
                    'price': float(ticker['lastPrice']),
                    'change_24h': price_change,
                    'volume': float(ticker['volume']),
                    'high_24h': float(ticker['highPrice']),
                    'low_24h': float(ticker['lowPrice']),
                    'signal': signal,
                    'strength': strength
                })
            
            return {
                "status": "success",
                "market_data": market_data,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except BinanceAPIException as e:
            logger.error(f"Lỗi Binance API khi lấy tổng quan thị trường: {str(e)}")
            return {"status": "error", "message": f"Lỗi Binance API: {str(e)}"}
        except Exception as e:
            logger.error(f"Lỗi không xác định khi lấy tổng quan thị trường: {str(e)}")
            logger.error(traceback.format_exc())
            return {"status": "error", "message": f"Lỗi hệ thống: {str(e)}"}
    
    def get_klines(self, symbol, interval, limit=100):
        """
        Lấy dữ liệu K-lines (nến) cho biểu đồ
        
        :param symbol: Cặp tiền, ví dụ BTCUSDT
        :param interval: Khung thời gian, ví dụ 1h, 4h, 1d
        :param limit: Số lượng nến
        :return: DataFrame chứa dữ liệu nến
        """
        if not self.is_connected() and not self.reconnect():
            logger.error("Không thể kết nối tới Binance API")
            return None
        
        try:
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            # Chuyển đổi sang DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 
                'volume', 'close_time', 'quote_asset_volume',
                'number_of_trades', 'taker_buy_base_asset_volume',
                'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Chuyển đổi kiểu dữ liệu
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            # Đặt timestamp làm index
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except BinanceAPIException as e:
            logger.error(f"Lỗi Binance API khi lấy dữ liệu K-lines: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Lỗi không xác định khi lấy dữ liệu K-lines: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def analyze_technical(self, symbol, interval):
        """
        Phân tích kỹ thuật cho một cặp tiền và khung thời gian
        
        :param symbol: Cặp tiền, ví dụ BTCUSDT
        :param interval: Khung thời gian, ví dụ 1h, 4h, 1d
        :return: Dictionary chứa các chỉ báo kỹ thuật và đánh giá
        """
        try:
            # Lấy dữ liệu K-lines
            df = self.get_klines(symbol, interval, limit=100)
            if df is None:
                return {"status": "error", "message": "Không thể lấy dữ liệu K-lines"}
            
            # Tính RSI
            df['rsi'] = talib.RSI(df['close'], timeperiod=14)
            
            # Tính MACD
            macd, macd_signal, macd_hist = talib.MACD(
                df['close'], 
                fastperiod=12, 
                slowperiod=26, 
                signalperiod=9
            )
            df['macd'] = macd
            df['macd_signal'] = macd_signal
            df['macd_hist'] = macd_hist
            
            # Tính Bollinger Bands
            upper, middle, lower = talib.BBANDS(
                df['close'], 
                timeperiod=20,
                nbdevup=2,
                nbdevdn=2,
                matype=0
            )
            df['bb_upper'] = upper
            df['bb_middle'] = middle
            df['bb_lower'] = lower
            
            # Tính MA
            df['ma50'] = talib.MA(df['close'], timeperiod=50)
            df['ma200'] = talib.MA(df['close'], timeperiod=200)
            
            # Tính Stochastic
            slowk, slowd = talib.STOCH(
                df['high'], 
                df['low'], 
                df['close'],
                fastk_period=5,
                slowk_period=3,
                slowk_matype=0,
                slowd_period=3,
                slowd_matype=0
            )
            df['stoch_k'] = slowk
            df['stoch_d'] = slowd
            
            # Lấy giá trị cuối cùng
            last_row = df.iloc[-1]
            current_price = last_row['close']
            
            # Đánh giá RSI
            rsi = last_row['rsi']
            if rsi > 70:
                rsi_signal = "Quá mua"
            elif rsi < 30:
                rsi_signal = "Quá bán"
            else:
                rsi_signal = "Trung tính"
            
            # Đánh giá MACD
            macd_last = last_row['macd']
            macd_signal_last = last_row['macd_signal']
            macd_hist_last = last_row['macd_hist']
            
            if macd_last > macd_signal_last:
                macd_trend = "Tăng"
                if macd_hist_last > 0 and macd_hist_last > df['macd_hist'][-2]:
                    macd_signal = "Mua mạnh"
                else:
                    macd_signal = "Mua"
            elif macd_last < macd_signal_last:
                macd_trend = "Giảm"
                if macd_hist_last < 0 and macd_hist_last < df['macd_hist'][-2]:
                    macd_signal = "Bán mạnh"
                else:
                    macd_signal = "Bán"
            else:
                macd_trend = "Đi ngang"
                macd_signal = "Trung tính"
            
            # Đánh giá Bollinger Bands
            bb_upper_last = last_row['bb_upper']
            bb_lower_last = last_row['bb_lower']
            
            if current_price > bb_upper_last:
                bb_signal = "Quá mua"
            elif current_price < bb_lower_last:
                bb_signal = "Quá bán"
            else:
                # Tính % vị trí trong BB
                bb_range = bb_upper_last - bb_lower_last
                if bb_range == 0:
                    bb_position = 50
                else:
                    bb_position = ((current_price - bb_lower_last) / bb_range) * 100
                
                if bb_position > 80:
                    bb_signal = "Gần quá mua"
                elif bb_position < 20:
                    bb_signal = "Gần quá bán"
                else:
                    bb_signal = "Trung tính"
            
            # Đánh giá MA
            ma50_last = last_row['ma50']
            ma200_last = last_row['ma200']
            
            if ma50_last > ma200_last:
                ma_signal = "Tín hiệu mua (Xu hướng tăng)"
            elif ma50_last < ma200_last:
                ma_signal = "Tín hiệu bán (Xu hướng giảm)"
            else:
                ma_signal = "Trung tính"
            
            # Đánh giá Stochastic
            stoch_k_last = last_row['stoch_k']
            stoch_d_last = last_row['stoch_d']
            
            if stoch_k_last > 80 and stoch_d_last > 80:
                stoch_signal = "Quá mua"
            elif stoch_k_last < 20 and stoch_d_last < 20:
                stoch_signal = "Quá bán"
            elif stoch_k_last > stoch_d_last:
                stoch_signal = "Mua"
            elif stoch_k_last < stoch_d_last:
                stoch_signal = "Bán"
            else:
                stoch_signal = "Trung tính"
            
            # Tổng hợp tín hiệu
            indicators = [
                {"name": "RSI(14)", "value": f"{rsi:.2f}", "signal": rsi_signal},
                {"name": "MACD", "value": macd_trend, "signal": macd_signal},
                {"name": "MA(50) vs MA(200)", "value": f"MA50: {ma50_last:.2f}, MA200: {ma200_last:.2f}", "signal": ma_signal},
                {"name": "Bollinger Bands", "value": f"Upper: {bb_upper_last:.2f}, Lower: {bb_lower_last:.2f}", "signal": bb_signal},
                {"name": "Stochastic", "value": f"K: {stoch_k_last:.2f}, D: {stoch_d_last:.2f}", "signal": stoch_signal}
            ]
            
            # Đánh giá tổng thể
            buy_signals = sum(1 for ind in indicators if "mua" in ind["signal"].lower())
            sell_signals = sum(1 for ind in indicators if "bán" in ind["signal"].lower())
            
            if buy_signals > sell_signals:
                overall_signal = "Mua"
                if buy_signals >= 4:
                    strength = "Mạnh"
                else:
                    strength = "Trung bình"
            elif sell_signals > buy_signals:
                overall_signal = "Bán"
                if sell_signals >= 4:
                    strength = "Mạnh"
                else:
                    strength = "Trung bình"
            else:
                overall_signal = "Giữ"
                strength = "Yếu"
            
            return {
                "status": "success",
                "symbol": symbol,
                "interval": interval,
                "price": current_price,
                "indicators": indicators,
                "overall_signal": overall_signal,
                "strength": strength,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích kỹ thuật: {str(e)}")
            logger.error(traceback.format_exc())
            return {"status": "error", "message": f"Lỗi khi phân tích kỹ thuật: {str(e)}"}
    
    def get_account_info(self):
        """
        Lấy thông tin tài khoản Binance
        
        :return: Dictionary chứa thông tin tài khoản
        """
        if not self.is_connected() and not self.reconnect():
            logger.error("Không thể kết nối tới Binance API")
            return {"status": "error", "message": "Không thể kết nối tới Binance API"}
        
        try:
            account = self.client.futures_account()
            
            # Chuẩn bị dữ liệu tài khoản
            account_info = {
                "balance": float(account['totalWalletBalance']),
                "unrealized_pnl": float(account['totalUnrealizedProfit']),
                "margin_balance": float(account['totalMarginBalance']),
                "available_balance": float(account['availableBalance']),
                "leverage": account.get('leverage', 1),
                "positions": []
            }
            
            # Lấy thông tin vị thế
            positions = [p for p in account['positions'] if float(p['positionAmt']) != 0]
            
            for position in positions:
                symbol = position['symbol']
                side = "LONG" if float(position['positionAmt']) > 0 else "SHORT"
                entry_price = float(position['entryPrice'])
                mark_price = float(position['markPrice'])
                amount = abs(float(position['positionAmt']))
                leverage = int(position['leverage'])
                unrealized_pnl = float(position['unrealizedProfit'])
                
                # Tính % lợi nhuận
                if entry_price == 0:
                    profit_percent = 0
                else:
                    if side == "LONG":
                        profit_percent = ((mark_price - entry_price) / entry_price) * 100 * leverage
                    else:
                        profit_percent = ((entry_price - mark_price) / entry_price) * 100 * leverage
                
                position_info = {
                    "symbol": symbol,
                    "side": side,
                    "entry_price": entry_price,
                    "mark_price": mark_price,
                    "amount": amount,
                    "leverage": leverage,
                    "unrealized_pnl": unrealized_pnl,
                    "profit_percent": profit_percent
                }
                
                account_info["positions"].append(position_info)
            
            return {
                "status": "success",
                "account": account_info,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except BinanceAPIException as e:
            logger.error(f"Lỗi Binance API khi lấy thông tin tài khoản: {str(e)}")
            return {"status": "error", "message": f"Lỗi Binance API: {str(e)}"}
        except Exception as e:
            logger.error(f"Lỗi không xác định khi lấy thông tin tài khoản: {str(e)}")
            logger.error(traceback.format_exc())
            return {"status": "error", "message": f"Lỗi hệ thống: {str(e)}"}

# Hàm để thử nghiệm module
def test_market_analyzer():
    """Hàm kiểm tra chức năng của MarketAnalyzer"""
    # Cấu hình logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print("Đang kiểm tra MarketAnalyzer...")
    analyzer = MarketAnalyzer(testnet=True)
    
    if not analyzer.is_connected():
        print("❌ Không thể kết nối tới Binance API")
        return
    
    print("✅ Đã kết nối tới Binance API")
    
    # Kiểm tra tổng quan thị trường
    overview = analyzer.get_market_overview()
    if overview["status"] == "success":
        print("✅ Lấy tổng quan thị trường thành công")
        for data in overview["market_data"]:
            print(f"  - {data['symbol']}: {data['price']} ({data['change_24h']}%)")
    else:
        print(f"❌ Lỗi khi lấy tổng quan thị trường: {overview.get('message', 'Unknown error')}")
    
    # Kiểm tra phân tích kỹ thuật
    analysis = analyzer.analyze_technical("BTCUSDT", "1h")
    if analysis["status"] == "success":
        print("✅ Phân tích kỹ thuật thành công")
        print(f"  - Giá hiện tại: {analysis['price']}")
        print(f"  - Tín hiệu tổng thể: {analysis['overall_signal']} ({analysis['strength']})")
        for ind in analysis["indicators"]:
            print(f"  - {ind['name']}: {ind['value']} ({ind['signal']})")
    else:
        print(f"❌ Lỗi khi phân tích kỹ thuật: {analysis.get('message', 'Unknown error')}")
    
    # Kiểm tra thông tin tài khoản
    account_info = analyzer.get_account_info()
    if account_info["status"] == "success":
        print("✅ Lấy thông tin tài khoản thành công")
        print(f"  - Số dư: {account_info['account']['balance']} USDT")
        print(f"  - Unrealized P/L: {account_info['account']['unrealized_pnl']} USDT")
        print(f"  - Margin Balance: {account_info['account']['margin_balance']} USDT")
        print(f"  - Số vị thế đang mở: {len(account_info['account']['positions'])}")
    else:
        print(f"❌ Lỗi khi lấy thông tin tài khoản: {account_info.get('message', 'Unknown error')}")

if __name__ == "__main__":
    test_market_analyzer()