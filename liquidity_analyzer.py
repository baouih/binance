#!/usr/bin/env python3
"""
Module phân tích thanh khoản thị trường (Liquidity Analyzer)

Module này cung cấp các hàm phân tích chi tiết về thanh khoản thị trường,
bao gồm độ sâu của order book, spread, và khối lượng giao dịch,
để đánh giá liệu một cặp tiền có đủ thanh khoản để giao dịch hay không.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("liquidity_analyzer")

# Đường dẫn lưu cấu hình thanh khoản
LIQUIDITY_CONFIG_PATH = "configs/liquidity_thresholds.json"

class LiquidityAnalyzer:
    """Lớp phân tích thanh khoản thị trường"""
    
    def __init__(self, binance_api=None):
        """
        Khởi tạo phân tích thanh khoản
        
        Args:
            binance_api: Đối tượng BinanceAPI (tùy chọn)
        """
        self.binance_api = binance_api
        self.config = self._load_or_create_config()
        
    def _load_or_create_config(self) -> Dict:
        """
        Tải hoặc tạo cấu hình thanh khoản
        
        Returns:
            Dict: Cấu hình thanh khoản
        """
        if os.path.exists(LIQUIDITY_CONFIG_PATH):
            try:
                with open(LIQUIDITY_CONFIG_PATH, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình thanh khoản từ {LIQUIDITY_CONFIG_PATH}")
                return config
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình thanh khoản: {str(e)}")
        
        # Tạo cấu hình mặc định
        logger.info("Tạo cấu hình thanh khoản mặc định")
        
        config = {
            "min_liquidity_score": 40,  # Điểm thanh khoản tối thiểu (0-100)
            "high_importance_threshold": 30,  # Ngưỡng dưới mức này sẽ là lý do high importance
            "score_weights": {
                "volume": 0.4,       # Trọng số điểm khối lượng
                "spread": 0.3,       # Trọng số điểm spread
                "depth": 0.3         # Trọng số điểm độ sâu order book
            },
            "volume_thresholds": {
                "very_high": 1.5,    # Khối lượng cao hơn 1.5x trung bình
                "high": 1.0,         # Khối lượng cao hơn trung bình
                "normal": 0.7,       # Khối lượng > 70% trung bình
                "low": 0.5,          # Khối lượng > 50% trung bình
                "very_low": 0.3      # Khối lượng < 30% trung bình
            },
            "spread_thresholds": {
                "very_tight": 0.05,  # Spread < 0.05%
                "tight": 0.1,        # Spread < 0.1%
                "normal": 0.2,       # Spread < 0.2%
                "wide": 0.5,         # Spread < 0.5%
                "very_wide": 1.0     # Spread > 1.0%
            },
            "depth_requirements": {
                "min_depth_sum": 20,   # Tổng độ sâu tối thiểu
                "min_depth_ratio": 0.5  # Tỷ lệ độ sâu tối thiểu (ask/bid)
            },
            "currency_specific": {
                "BTC": {
                    "min_liquidity_score": 30  # BTC có thể giao dịch với thanh khoản thấp hơn
                },
                "ETH": {
                    "min_liquidity_score": 35
                }
                # Có thể thêm cấu hình cho các đồng khác
            },
            "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Lưu cấu hình
        try:
            os.makedirs(os.path.dirname(LIQUIDITY_CONFIG_PATH), exist_ok=True)
            with open(LIQUIDITY_CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=4)
            logger.info(f"Đã tạo cấu hình thanh khoản mặc định tại {LIQUIDITY_CONFIG_PATH}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình thanh khoản: {str(e)}")
        
        return config
    
    def save_config(self) -> bool:
        """
        Lưu cấu hình thanh khoản
        
        Returns:
            bool: True nếu lưu thành công, False nếu lỗi
        """
        try:
            # Cập nhật thời gian
            self.config["last_updated"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Đảm bảo thư mục tồn tại
            os.makedirs(os.path.dirname(LIQUIDITY_CONFIG_PATH), exist_ok=True)
            
            # Lưu cấu hình
            with open(LIQUIDITY_CONFIG_PATH, 'w') as f:
                json.dump(self.config, f, indent=4)
            
            logger.info(f"Đã lưu cấu hình thanh khoản vào {LIQUIDITY_CONFIG_PATH}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình thanh khoản: {str(e)}")
            return False
    
    def check_liquidity_conditions(self, symbol: str, timeframe: str = "1h") -> Dict:
        """
        Kiểm tra điều kiện thanh khoản cho một cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian để phân tích
            
        Returns:
            Dict: Kết quả phân tích thanh khoản
        """
        try:
            # Lấy dữ liệu khối lượng giao dịch
            df = self._get_ohlcv_data(symbol, timeframe)
            
            # Tính toán trung bình khối lượng trong 20 chu kỳ
            avg_volume = df['volume'].rolling(window=20).mean()
            current_volume = df['volume'].iloc[-1]
            
            # Tính tỷ lệ khối lượng hiện tại so với trung bình
            volume_ratio = current_volume / avg_volume.iloc[-1] if not np.isnan(avg_volume.iloc[-1]) else 1.0
            
            # Lấy dữ liệu order book
            order_book = self._get_order_book(symbol)
            
            # Tính toán độ rộng của spread
            top_bid = float(order_book['bids'][0][0]) if len(order_book['bids']) > 0 else 0
            top_ask = float(order_book['asks'][0][0]) if len(order_book['asks']) > 0 else 0
            
            if top_bid > 0 and top_ask > 0:
                spread_pct = (top_ask - top_bid) / top_bid * 100
            else:
                spread_pct = 1.0  # Giá trị mặc định
            
            # Tính toán độ sâu của order book (tổng khối lượng trong 10 mức giá hàng đầu)
            bid_depth = sum([float(bid[1]) for bid in order_book['bids'][:10]]) if len(order_book['bids']) >= 10 else 0
            ask_depth = sum([float(ask[1]) for ask in order_book['asks'][:10]]) if len(order_book['asks']) >= 10 else 0
            
            # Tính toán điểm thanh khoản tổng hợp (0-100)
            liquidity_score = self._calculate_liquidity_score(volume_ratio, spread_pct, bid_depth, ask_depth, symbol)
            
            # Xác định ngưỡng thanh khoản tối thiểu cho cặp tiền này
            base_currency = self._extract_base_currency(symbol)
            min_score = self.config.get("currency_specific", {}).get(base_currency, {}).get(
                "min_liquidity_score", self.config.get("min_liquidity_score", 40))
            
            # Tạo lý do nếu điểm thanh khoản thấp
            reasons = []
            if liquidity_score < min_score:
                importance = "high" if liquidity_score < self.config.get("high_importance_threshold", 30) else "medium"
                reasons.append({
                    "category": "liquidity",
                    "reason": f"Thanh khoản thấp (điểm: {liquidity_score}/100, ngưỡng: {min_score})",
                    "importance": importance
                })
            
            # Kiểm tra các yếu tố cụ thể
            if volume_ratio < self.config.get("volume_thresholds", {}).get("low", 0.5):
                reasons.append({
                    "category": "liquidity",
                    "reason": f"Khối lượng thấp ({volume_ratio:.2f}x so với trung bình)",
                    "importance": "medium"
                })
            
            if spread_pct > self.config.get("spread_thresholds", {}).get("wide", 0.5):
                reasons.append({
                    "category": "liquidity",
                    "reason": f"Spread rộng ({spread_pct:.2f}%)",
                    "importance": "medium"
                })
            
            depth_sum = bid_depth + ask_depth
            depth_ratio = min(bid_depth, ask_depth) / max(bid_depth, ask_depth) if max(bid_depth, ask_depth) > 0 else 0
            
            min_depth_sum = self.config.get("depth_requirements", {}).get("min_depth_sum", 20)
            min_depth_ratio = self.config.get("depth_requirements", {}).get("min_depth_ratio", 0.5)
            
            if depth_sum < min_depth_sum:
                reasons.append({
                    "category": "liquidity",
                    "reason": f"Độ sâu order book thấp (tổng: {depth_sum:.2f})",
                    "importance": "medium"
                })
            
            if depth_ratio < min_depth_ratio:
                reasons.append({
                    "category": "liquidity",
                    "reason": f"Mất cân bằng order book (tỷ lệ: {depth_ratio:.2f})",
                    "importance": "low"
                })
            
            # Tạo kết quả phân tích
            return {
                "score": liquidity_score,
                "volume_ratio": volume_ratio,
                "spread_pct": spread_pct,
                "depth_sum": depth_sum,
                "depth_ratio": depth_ratio,
                "reasons": reasons,
                "is_tradable": liquidity_score >= min_score
            }
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra thanh khoản cho {symbol}: {str(e)}")
            # Trả về kết quả mặc định với điểm thanh khoản trung bình
            return {
                "score": 50,
                "volume_ratio": 1.0,
                "spread_pct": 0.2,
                "depth_sum": 50,
                "depth_ratio": 0.7,
                "reasons": [{
                    "category": "liquidity",
                    "reason": f"Lỗi khi phân tích thanh khoản: {str(e)}",
                    "importance": "low"
                }],
                "is_tradable": True,
                "error": str(e)
            }
    
    def _calculate_liquidity_score(self, volume_ratio: float, spread_pct: float, 
                                  bid_depth: float, ask_depth: float, symbol: str) -> float:
        """
        Tính toán điểm thanh khoản tổng hợp
        
        Args:
            volume_ratio (float): Tỷ lệ khối lượng so với trung bình
            spread_pct (float): Phần trăm spread
            bid_depth (float): Độ sâu phía bid
            ask_depth (float): Độ sâu phía ask
            symbol (str): Mã cặp tiền
            
        Returns:
            float: Điểm thanh khoản (0-100)
        """
        weights = self.config.get("score_weights", {})
        volume_weight = weights.get("volume", 0.4)
        spread_weight = weights.get("spread", 0.3)
        depth_weight = weights.get("depth", 0.3)
        
        # 1. Điểm khối lượng (0-100)
        volume_thresholds = self.config.get("volume_thresholds", {})
        if volume_ratio >= volume_thresholds.get("very_high", 1.5):
            volume_points = 100  # Khối lượng rất cao
        elif volume_ratio >= volume_thresholds.get("high", 1.0):
            volume_points = 80   # Khối lượng cao
        elif volume_ratio >= volume_thresholds.get("normal", 0.7):
            volume_points = 60   # Khối lượng bình thường
        elif volume_ratio >= volume_thresholds.get("low", 0.5):
            volume_points = 40   # Khối lượng thấp
        elif volume_ratio >= volume_thresholds.get("very_low", 0.3):
            volume_points = 20   # Khối lượng rất thấp
        else:
            volume_points = 0    # Khối lượng cực thấp
        
        # 2. Điểm spread (0-100)
        spread_thresholds = self.config.get("spread_thresholds", {})
        if spread_pct <= spread_thresholds.get("very_tight", 0.05):
            spread_points = 100  # Spread rất hẹp
        elif spread_pct <= spread_thresholds.get("tight", 0.1):
            spread_points = 80   # Spread hẹp
        elif spread_pct <= spread_thresholds.get("normal", 0.2):
            spread_points = 60   # Spread trung bình
        elif spread_pct <= spread_thresholds.get("wide", 0.5):
            spread_points = 40   # Spread rộng
        elif spread_pct <= spread_thresholds.get("very_wide", 1.0):
            spread_points = 20   # Spread rất rộng
        else:
            spread_points = 0    # Spread cực rộng
        
        # 3. Điểm độ sâu order book (0-100)
        depth_sum = bid_depth + ask_depth
        depth_ratio = min(bid_depth, ask_depth) / max(bid_depth, ask_depth) if max(bid_depth, ask_depth) > 0 else 0
        
        # Điều chỉnh yêu cầu độ sâu theo cặp tiền
        base_currency = self._extract_base_currency(symbol)
        min_depth_sum = self.config.get("currency_specific", {}).get(base_currency, {}).get(
            "min_depth_sum", self.config.get("depth_requirements", {}).get("min_depth_sum", 20))
        
        if depth_sum >= 5 * min_depth_sum and depth_ratio >= 0.7:
            depth_points = 100  # Độ sâu rất tốt và cân bằng
        elif depth_sum >= 3 * min_depth_sum and depth_ratio >= 0.6:
            depth_points = 80   # Độ sâu tốt
        elif depth_sum >= min_depth_sum and depth_ratio >= 0.5:
            depth_points = 60   # Độ sâu trung bình
        elif depth_sum >= 0.5 * min_depth_sum:
            depth_points = 40   # Độ sâu thấp
        elif depth_sum >= 0.2 * min_depth_sum:
            depth_points = 20   # Độ sâu rất thấp
        else:
            depth_points = 0    # Độ sâu cực thấp
        
        # Tính điểm tổng hợp theo trọng số
        liquidity_score = (
            volume_points * volume_weight +
            spread_points * spread_weight +
            depth_points * depth_weight
        )
        
        return liquidity_score
    
    def _extract_base_currency(self, symbol: str) -> str:
        """
        Trích xuất base currency từ mã cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền (ví dụ: BTCUSDT)
            
        Returns:
            str: Base currency (ví dụ: BTC)
        """
        # Loại bỏ các đuôi phổ biến
        common_quote_currencies = ["USDT", "BUSD", "USDC", "USD", "TUSD", "DAI", "FDUSD"]
        
        for quote in common_quote_currencies:
            if symbol.endswith(quote):
                return symbol[:-len(quote)]
        
        # Nếu không tìm thấy, trả về mã ban đầu
        return symbol
    
    def _get_ohlcv_data(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """
        Lấy dữ liệu OHLCV từ API
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            limit (int): Số lượng nến tối đa
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu OHLCV
        """
        if not self.binance_api:
            # Trả về DataFrame trống với cấu trúc đúng
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        try:
            # Lấy dữ liệu từ API
            klines = self.binance_api.get_klines(symbol=symbol, interval=timeframe, limit=limit)
            
            if not klines:
                return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Chuyển đổi thành DataFrame
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                                             'close_time', 'quote_asset_volume', 'number_of_trades',
                                             'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
            
            # Chuyển đổi kiểu dữ liệu
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric)
            
            # Chuyển đổi timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu OHLCV: {str(e)}")
            # Trả về DataFrame trống với cấu trúc đúng
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    def _get_order_book(self, symbol: str, limit: int = 20) -> Dict:
        """
        Lấy dữ liệu order book từ API
        
        Args:
            symbol (str): Mã cặp tiền
            limit (int): Số lượng mức giá tối đa
            
        Returns:
            Dict: Dữ liệu order book
        """
        if not self.binance_api:
            # Trả về cấu trúc trống
            return {'bids': [], 'asks': []}
        
        try:
            # Lấy dữ liệu từ API
            order_book = self.binance_api.get_order_book(symbol=symbol, limit=limit)
            return order_book
        except Exception as e:
            logger.error(f"Lỗi khi lấy order book: {str(e)}")
            # Trả về cấu trúc trống
            return {'bids': [], 'asks': []}
    
    def update_min_liquidity_score(self, currency: str, score: int) -> bool:
        """
        Cập nhật điểm thanh khoản tối thiểu cho một đồng tiền
        
        Args:
            currency (str): Mã đồng tiền (ví dụ: BTC)
            score (int): Điểm tối thiểu (0-100)
            
        Returns:
            bool: True nếu thành công, False nếu lỗi
        """
        try:
            # Đảm bảo score nằm trong khoảng 0-100
            score = max(0, min(score, 100))
            
            # Nếu là "default", cập nhật ngưỡng mặc định
            if currency.lower() == "default":
                self.config["min_liquidity_score"] = score
                logger.info(f"Đã cập nhật điểm thanh khoản tối thiểu mặc định: {score}")
            else:
                # Cập nhật cho đồng tiền cụ thể
                if "currency_specific" not in self.config:
                    self.config["currency_specific"] = {}
                
                if currency not in self.config["currency_specific"]:
                    self.config["currency_specific"][currency] = {}
                
                self.config["currency_specific"][currency]["min_liquidity_score"] = score
                logger.info(f"Đã cập nhật điểm thanh khoản tối thiểu cho {currency}: {score}")
            
            # Lưu cấu hình
            self.save_config()
            return True
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật điểm thanh khoản tối thiểu: {str(e)}")
            return False
    
    def update_score_weights(self, volume_weight: float, spread_weight: float, depth_weight: float) -> bool:
        """
        Cập nhật trọng số điểm thanh khoản
        
        Args:
            volume_weight (float): Trọng số khối lượng
            spread_weight (float): Trọng số spread
            depth_weight (float): Trọng số độ sâu
            
        Returns:
            bool: True nếu thành công, False nếu lỗi
        """
        try:
            # Chuẩn hóa trọng số
            total = volume_weight + spread_weight + depth_weight
            volume_weight = volume_weight / total
            spread_weight = spread_weight / total
            depth_weight = depth_weight / total
            
            # Cập nhật
            self.config["score_weights"] = {
                "volume": volume_weight,
                "spread": spread_weight,
                "depth": depth_weight
            }
            
            logger.info(f"Đã cập nhật trọng số điểm thanh khoản: volume={volume_weight:.2f}, " +
                      f"spread={spread_weight:.2f}, depth={depth_weight:.2f}")
            
            # Lưu cấu hình
            self.save_config()
            return True
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật trọng số điểm thanh khoản: {str(e)}")
            return False

def main():
    """Hàm chính để test module"""
    
    try:
        # Khởi tạo
        from binance_api import BinanceAPI
        api = BinanceAPI()
        liquidity_analyzer = LiquidityAnalyzer(api)
        
        # Test các chức năng
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "DOGEUSDT"]
        
        print("=== Phân tích thanh khoản ===")
        for symbol in symbols:
            result = liquidity_analyzer.check_liquidity_conditions(symbol)
            tradable = "✅ Có thể giao dịch" if result.get("is_tradable", False) else "❌ Không nên giao dịch"
            print(f"{symbol}: Điểm = {result.get('score', 0):.2f}, {tradable}")
            
            # In chi tiết
            print(f"  - Khối lượng: {result.get('volume_ratio', 0):.2f}x trung bình")
            print(f"  - Spread: {result.get('spread_pct', 0):.4f}%")
            print(f"  - Độ sâu: {result.get('depth_sum', 0):.2f}")
            
            # In lý do không giao dịch (nếu có)
            reasons = result.get("reasons", [])
            if reasons:
                print("  Lý do không giao dịch:")
                for reason in reasons:
                    print(f"  - [{reason.get('importance', 'medium')}] {reason.get('reason', '')}")
            
            print()
        
        # Test cập nhật cấu hình
        print("\n=== Cập nhật cấu hình ===")
        liquidity_analyzer.update_min_liquidity_score("BTC", 30)
        liquidity_analyzer.update_min_liquidity_score("ETH", 35)
        liquidity_analyzer.update_min_liquidity_score("default", 40)
        
        # Test cập nhật trọng số
        liquidity_analyzer.update_score_weights(4, 3, 3)
        
        print("\n=== Cấu hình hiện tại ===")
        import json
        print(json.dumps(liquidity_analyzer.config, indent=4))
        
    except Exception as e:
        logger.error(f"Lỗi khi chạy test: {str(e)}")

if __name__ == "__main__":
    main()