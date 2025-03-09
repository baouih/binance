#!/usr/bin/env python3
"""
Mô-đun phân tích biến động đa khung thời gian

Module này phân tích biến động thị trường trên nhiều khung thời gian (5m, 1h, 4h)
và điều chỉnh các ngưỡng stop loss phù hợp để tránh bị stopped out quá sớm.
"""

import logging
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from binance_api import BinanceAPI

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("multi_timeframe_volatility_analyzer")

class MultiTimeframeVolatilityAnalyzer:
    """Phân tích biến động thị trường trên nhiều khung thời gian"""
    
    def __init__(self):
        """Khởi tạo phân tích biến động đa khung thời gian"""
        self.api = BinanceAPI()
        self.timeframes = {
            "5m": {"weight": 0.2, "data": None},  # Khung thời gian ngắn hạn
            "1h": {"weight": 0.5, "data": None},  # Khung thời gian trung hạn
            "4h": {"weight": 0.3, "data": None}   # Khung thời gian dài hạn
        }
        
    def fetch_market_data(self, symbol: str) -> Dict:
        """
        Lấy dữ liệu thị trường cho nhiều khung thời gian
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            Dict: Dữ liệu thị trường
        """
        data = {}
        for timeframe in self.timeframes.keys():
            try:
                # Lấy 100 nến gần nhất
                candles = self.api.futures_klines(symbol=symbol, interval=timeframe, limit=100)
                
                # Chuyển đổi thành DataFrame
                df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                                                 'close_time', 'quote_asset_volume', 'trades', 
                                                 'taker_buy_base', 'taker_buy_quote', 'ignore'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df['open'] = pd.to_numeric(df['open'])
                df['high'] = pd.to_numeric(df['high'])
                df['low'] = pd.to_numeric(df['low'])
                df['close'] = pd.to_numeric(df['close'])
                df['volume'] = pd.to_numeric(df['volume'])
                
                # Thêm chỉ báo ATR
                df = self.add_atr(df)
                
                # Lưu vào bộ nhớ
                self.timeframes[timeframe]["data"] = df
                data[timeframe] = df
                
            except Exception as e:
                logger.error(f"Lỗi khi lấy dữ liệu cho {symbol} timeframe {timeframe}: {str(e)}")
                data[timeframe] = None
                
        return data
    
    def add_atr(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        Thêm chỉ báo ATR (Average True Range) vào DataFrame
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu
            period (int): Chu kỳ ATR
            
        Returns:
            pd.DataFrame: DataFrame với chỉ báo ATR
        """
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        true_range = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        atr = true_range.rolling(period).mean()
        
        df['true_range'] = true_range
        df['atr'] = atr
        
        # Thêm ATR phần trăm (ATR/Giá hiện tại)
        df['atr_percent'] = df['atr'] / df['close'] * 100
        
        return df
    
    def calculate_weighted_volatility(self, symbol: str) -> Dict:
        """
        Tính toán biến động có trọng số dựa trên nhiều khung thời gian
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            Dict: Thông tin biến động
        """
        # Lấy dữ liệu thị trường
        data = self.fetch_market_data(symbol)
        
        # Tính toán biến động có trọng số
        weighted_volatility = 0
        for timeframe, info in self.timeframes.items():
            weight = info["weight"]
            df = data.get(timeframe)
            
            if df is not None and not df.empty:
                # Lấy ATR phần trăm gần nhất
                recent_atr_percent = df['atr_percent'].iloc[-1]
                
                # Cộng dồn theo trọng số
                weighted_volatility += recent_atr_percent * weight
            
        # Kết quả phân tích
        volatility_data = {
            "symbol": symbol,
            "weighted_volatility": weighted_volatility,
            "volatility_by_timeframe": {}
        }
        
        # Thêm chi tiết theo từng khung thời gian
        for timeframe, info in self.timeframes.items():
            df = data.get(timeframe)
            if df is not None and not df.empty:
                volatility_data["volatility_by_timeframe"][timeframe] = {
                    "atr_percent": df['atr_percent'].iloc[-1],
                    "atr_value": df['atr'].iloc[-1],
                    "weight": info["weight"]
                }
        
        return volatility_data
    
    def recommend_stop_loss(self, symbol: str, side: str = "BUY") -> Dict:
        """
        Đề xuất các mức stop loss dựa trên biến động thị trường
        
        Args:
            symbol (str): Mã cặp tiền
            side (str): Phía giao dịch (BUY hoặc SELL)
            
        Returns:
            Dict: Đề xuất stop loss
        """
        # Tính toán biến động có trọng số
        volatility_data = self.calculate_weighted_volatility(symbol)
        weighted_volatility = volatility_data["weighted_volatility"]
        
        # Điều chỉnh hệ số an toàn, thay đổi tùy theo biên độ giao động
        if weighted_volatility < 1.0:
            safety_factor = 1.5  # Biến động thấp, cần stop loss rộng hơn để tránh dừng sớm
        elif weighted_volatility < 2.0:
            safety_factor = 1.2  # Biến động trung bình
        else:
            safety_factor = 1.0  # Biến động cao, stop loss có thể chặt hơn
            
        # Tính toán stop loss theo phần trăm
        stop_loss_percent = weighted_volatility * safety_factor
        
        # Tính toán giá stop loss cụ thể
        ticker_data = self.api.futures_ticker_price(symbol=symbol)
        if isinstance(ticker_data, list) and len(ticker_data) > 0:
            current_price = float(ticker_data[0]["price"])
        else:
            # Backup method
            logger.warning(f"Không thể lấy giá hiện tại qua futures_ticker_price cho {symbol}, sử dụng phương thức dự phòng")
            try:
                ticker = self.api.get_symbol_ticker(symbol=symbol)
                current_price = float(ticker.get("price", 0))
            except Exception as e:
                logger.error(f"Không thể lấy giá hiện tại cho {symbol}: {str(e)}")
                current_price = 0
        
        if side.upper() == "BUY":
            stop_loss_price = current_price * (1 - stop_loss_percent / 100)
        else:  # SELL
            stop_loss_price = current_price * (1 + stop_loss_percent / 100)
            
        # Thêm đề xuất take profit dựa trên risk-reward ratio
        risk_reward_ratio = 1.5  # Mặc định 1:1.5
        take_profit_percent = stop_loss_percent * risk_reward_ratio
        
        if side.upper() == "BUY":
            take_profit_price = current_price * (1 + take_profit_percent / 100)
        else:  # SELL
            take_profit_price = current_price * (1 - take_profit_percent / 100)
        
        # Kết quả đề xuất
        recommendation = {
            "symbol": symbol,
            "current_price": current_price,
            "side": side,
            "weighted_volatility": weighted_volatility,
            "volatility_by_timeframe": volatility_data["volatility_by_timeframe"],
            "safety_factor": safety_factor,
            "stop_loss": {
                "percent": stop_loss_percent,
                "price": stop_loss_price
            },
            "take_profit": {
                "percent": take_profit_percent,
                "price": take_profit_price
            },
            "risk_reward_ratio": risk_reward_ratio
        }
        
        return recommendation
    
    def adjust_strategy_parameters(self, symbol: str, strategy_params: Dict) -> Dict:
        """
        Điều chỉnh các tham số chiến lược dựa trên biến động thị trường
        
        Args:
            symbol (str): Mã cặp tiền
            strategy_params (Dict): Các tham số chiến lược cần điều chỉnh
            
        Returns:
            Dict: Tham số chiến lược đã điều chỉnh
        """
        # Tính toán biến động có trọng số
        volatility_data = self.calculate_weighted_volatility(symbol)
        weighted_volatility = volatility_data["weighted_volatility"]
        
        # Sao chép tham số ban đầu
        adjusted_params = strategy_params.copy()
        
        # Điều chỉnh stop loss dựa trên biến động
        if "stop_loss_percent" in adjusted_params:
            # Tính toán hệ số an toàn
            safety_factor = 1.0
            if weighted_volatility < 1.0:
                safety_factor = 1.5  # Biến động thấp, cần stop loss rộng hơn
            elif weighted_volatility < 2.0:
                safety_factor = 1.2  # Biến động trung bình
                
            # Điều chỉnh stop loss, đảm bảo không nhỏ hơn 1.5%
            min_stop_loss = 1.5
            base_stop_loss = adjusted_params["stop_loss_percent"]
            
            # Tính toán stop loss điều chỉnh
            adjusted_stop_loss = max(min_stop_loss, base_stop_loss * safety_factor)
            
            # Giới hạn tối đa 5% để quản lý rủi ro
            adjusted_stop_loss = min(5.0, adjusted_stop_loss)
            
            # Cập nhật giá trị
            adjusted_params["stop_loss_percent"] = adjusted_stop_loss
            
            # Đồng thời điều chỉnh take profit để duy trì risk-reward ratio
            if "take_profit_percent" in adjusted_params:
                risk_reward_ratio = 1.5  # Mặc định 1:1.5
                if base_stop_loss > 0:
                    risk_reward_ratio = adjusted_params["take_profit_percent"] / base_stop_loss
                
                adjusted_params["take_profit_percent"] = adjusted_stop_loss * risk_reward_ratio
        
        # Ghi log các điều chỉnh
        logger.info(f"Điều chỉnh tham số cho {symbol}: weighted_volatility={weighted_volatility:.2f}%, "
                   f"adjusted_stop_loss={adjusted_params.get('stop_loss_percent', 'N/A')}%, "
                   f"adjusted_take_profit={adjusted_params.get('take_profit_percent', 'N/A')}%")
        
        return adjusted_params


if __name__ == "__main__":
    # Mã kiểm thử
    analyzer = MultiTimeframeVolatilityAnalyzer()
    
    # Thử nghiệm với BTC
    recommendation = analyzer.recommend_stop_loss("BTCUSDT", "BUY")
    print(json.dumps(recommendation, indent=2))
    
    # Thử nghiệm điều chỉnh tham số
    original_params = {
        "stop_loss_percent": 2.0,
        "take_profit_percent": 3.0
    }
    
    adjusted_params = analyzer.adjust_strategy_parameters("BTCUSDT", original_params)
    print("\nOriginal parameters:", original_params)
    print("Adjusted parameters:", adjusted_params)