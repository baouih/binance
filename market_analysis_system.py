#!/usr/bin/env python3
"""
Hệ thống phân tích thị trường và vào/ra lệnh tổng hợp

Module này cung cấp:
1. Phân tích tổng thể thị trường crypto
2. Phân tích chi tiết từng đồng tiền
3. Xác định điểm vào/ra lệnh tối ưu
4. Ghi log và phân tích lý do không đánh coin sau khi phân tích
5. Hệ thống logic vào/ra lệnh thống nhất
"""

import os
import json
import time
import logging
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional, Any, Union
from binance_api import BinanceAPI

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("market_analysis_system")

# Đường dẫn file
MARKET_ANALYSIS_CONFIG = "configs/market_analysis_config.json"
MARKET_ANALYSIS_RESULTS = "reports/market_analysis_results.json"
TRADING_DECISIONS_LOG = "logs/trading_decisions.log"
NO_TRADE_REASONS_LOG = "logs/no_trade_reasons.log"
MARKET_REGIME_DATA = "data/market_regime_data.json"

class MarketAnalysisSystem:
    """
    Hệ thống phân tích thị trường và logic vào/ra lệnh toàn diện
    """
    
    def __init__(self, config_path: str = MARKET_ANALYSIS_CONFIG):
        """
        Khởi tạo hệ thống phân tích thị trường
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
        """
        self.config_path = config_path
        self.config = self._load_or_create_config()
        self.api = BinanceAPI()
        
        # Tạo các thư mục cần thiết
        self._ensure_directories()
        
        # Lưu lịch sử phân tích
        self.analysis_history = self._load_analysis_history()
        
        # Lưu lịch sử quyết định không giao dịch
        self.no_trade_reasons = self._load_no_trade_reasons()
        
        # Dữ liệu chế độ thị trường
        self.market_regime_data = self._load_market_regime_data()
        
        logger.info("Đã khởi tạo hệ thống phân tích thị trường")
    
    def _ensure_directories(self):
        """Tạo các thư mục cần thiết nếu chưa tồn tại"""
        directories = [
            "configs",
            "reports",
            "logs",
            "data",
            "charts/market_analysis"
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"Đã tạo thư mục: {directory}")
    
    def _load_or_create_config(self) -> Dict:
        """
        Tải cấu hình hoặc tạo mới nếu chưa tồn tại
        
        Returns:
            Dict: Cấu hình hệ thống phân tích
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
                return config
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
        
        # Tạo cấu hình mặc định
        default_config = {
            "symbols_to_analyze": [
                "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", 
                "DOGEUSDT", "MATICUSDT", "SOLUSDT", "DOTUSDT", "AVAXUSDT",
                "LTCUSDT", "LINKUSDT", "UNIUSDT", "ATOMUSDT"
            ],
            "timeframes": ["5m", "15m", "1h", "4h", "1d"],
            "primary_timeframe": "1h",
            "indicators": {
                "moving_averages": {
                    "enabled": True,
                    "periods": [20, 50, 100, 200],
                    "types": ["SMA", "EMA"]
                },
                "oscillators": {
                    "enabled": True,
                    "rsi": {
                        "enabled": True,
                        "period": 14,
                        "overbought": 70,
                        "oversold": 30
                    },
                    "macd": {
                        "enabled": True,
                        "fast_period": 12,
                        "slow_period": 26,
                        "signal_period": 9
                    },
                    "stochastic": {
                        "enabled": True,
                        "k_period": 14,
                        "d_period": 3,
                        "smooth_k": 3
                    }
                },
                "volume": {
                    "enabled": True,
                    "vwap": True,
                    "obv": True
                },
                "volatility": {
                    "enabled": True,
                    "bollinger_bands": {
                        "enabled": True,
                        "period": 20,
                        "std_dev": 2.0
                    },
                    "atr": {
                        "enabled": True,
                        "period": 14
                    }
                },
                "support_resistance": {
                    "enabled": True,
                    "lookback_periods": 100,
                    "zone_threshold": 0.02
                }
            },
            "market_regimes": {
                "detection": {
                    "enabled": True,
                    "lookback_periods": 30,
                    "update_frequency": "daily"
                },
                "regimes": [
                    "trending_up",
                    "trending_down",
                    "ranging",
                    "high_volatility",
                    "low_volatility"
                ]
            },
            "strategy_settings": {
                "entry_conditions": {
                    "trending_market": {
                        "indicators": ["moving_averages", "macd", "volume"],
                        "confirmation_count": 2
                    },
                    "ranging_market": {
                        "indicators": ["rsi", "bollinger_bands", "support_resistance"],
                        "confirmation_count": 2
                    },
                    "volatile_market": {
                        "indicators": ["atr", "obv", "support_resistance"],
                        "confirmation_count": 3
                    }
                },
                "exit_conditions": {
                    "take_profit": {
                        "default_percentage": 5.0,
                        "adjust_by_volatility": True
                    },
                    "stop_loss": {
                        "default_percentage": 3.0,
                        "adjust_by_volatility": True
                    },
                    "trailing_stop": {
                        "enabled": True,
                        "activation_percentage": 1.0,
                        "callback_percentage": 0.5
                    },
                    "indicator_based": {
                        "enabled": True,
                        "indicators": ["rsi", "macd", "bollinger_bands"]
                    }
                },
                "risk_management": {
                    "max_risk_per_trade": 1.0,  # % của tài khoản
                    "max_trades_per_day": 5,
                    "max_active_trades": 3,
                    "correlation_threshold": 0.7  # Không mở vị thế tương quan cao
                }
            },
            "analysis_thresholds": {
                "strong_buy": 80,
                "buy": 60,
                "neutral": 40,
                "sell": 20,
                "strong_sell": 0
            },
            "no_trade_reasons_categories": [
                "market_conditions",
                "technical_indicators",
                "risk_management",
                "volatility",
                "liquidity",
                "correlation",
                "fundamental"
            ]
        }
        
        # Lưu cấu hình mặc định
        try:
            # Đảm bảo thư mục tồn tại
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            
            logger.info(f"Đã tạo cấu hình mặc định tại {self.config_path}")
            return default_config
        except Exception as e:
            logger.error(f"Lỗi khi tạo cấu hình mặc định: {str(e)}")
            return default_config
    
    def _load_analysis_history(self) -> List[Dict]:
        """
        Tải lịch sử phân tích
        
        Returns:
            List[Dict]: Lịch sử phân tích
        """
        if os.path.exists(MARKET_ANALYSIS_RESULTS):
            try:
                with open(MARKET_ANALYSIS_RESULTS, 'r') as f:
                    history = json.load(f)
                logger.info(f"Đã tải {len(history)} bản ghi phân tích từ {MARKET_ANALYSIS_RESULTS}")
                return history
            except Exception as e:
                logger.error(f"Lỗi khi tải lịch sử phân tích: {str(e)}")
        
        return []
    
    def _save_analysis_history(self) -> bool:
        """
        Lưu lịch sử phân tích
        
        Returns:
            bool: True nếu lưu thành công, False nếu thất bại
        """
        try:
            # Đảm bảo thư mục tồn tại
            os.makedirs(os.path.dirname(MARKET_ANALYSIS_RESULTS), exist_ok=True)
            
            with open(MARKET_ANALYSIS_RESULTS, 'w') as f:
                json.dump(self.analysis_history, f, indent=4)
            
            logger.info(f"Đã lưu {len(self.analysis_history)} bản ghi phân tích vào {MARKET_ANALYSIS_RESULTS}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu lịch sử phân tích: {str(e)}")
            return False
    
    def _load_no_trade_reasons(self) -> List[Dict]:
        """
        Tải lịch sử lý do không giao dịch
        
        Returns:
            List[Dict]: Lịch sử lý do không giao dịch
        """
        if os.path.exists(NO_TRADE_REASONS_LOG):
            try:
                with open(NO_TRADE_REASONS_LOG, 'r') as f:
                    reasons = json.load(f)
                logger.info(f"Đã tải {len(reasons)} bản ghi lý do không giao dịch từ {NO_TRADE_REASONS_LOG}")
                return reasons
            except Exception as e:
                logger.error(f"Lỗi khi tải lý do không giao dịch: {str(e)}")
        
        return []
    
    def _save_no_trade_reasons(self) -> bool:
        """
        Lưu lịch sử lý do không giao dịch
        
        Returns:
            bool: True nếu lưu thành công, False nếu thất bại
        """
        try:
            # Đảm bảo thư mục tồn tại
            os.makedirs(os.path.dirname(NO_TRADE_REASONS_LOG), exist_ok=True)
            
            with open(NO_TRADE_REASONS_LOG, 'w') as f:
                json.dump(self.no_trade_reasons, f, indent=4)
            
            logger.info(f"Đã lưu {len(self.no_trade_reasons)} bản ghi lý do không giao dịch vào {NO_TRADE_REASONS_LOG}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu lý do không giao dịch: {str(e)}")
            return False
    
    def _load_market_regime_data(self) -> Dict:
        """
        Tải dữ liệu chế độ thị trường
        
        Returns:
            Dict: Dữ liệu chế độ thị trường
        """
        if os.path.exists(MARKET_REGIME_DATA):
            try:
                with open(MARKET_REGIME_DATA, 'r') as f:
                    data = json.load(f)
                logger.info(f"Đã tải dữ liệu chế độ thị trường từ {MARKET_REGIME_DATA}")
                return data
            except Exception as e:
                logger.error(f"Lỗi khi tải dữ liệu chế độ thị trường: {str(e)}")
        
        # Tạo dữ liệu mặc định
        default_data = {
            "last_updated": "",
            "btc_dominance": 0,
            "total_market_cap": 0,
            "global_regime": "unknown",
            "symbols_regime": {}
        }
        
        return default_data
    
    def _save_market_regime_data(self) -> bool:
        """
        Lưu dữ liệu chế độ thị trường
        
        Returns:
            bool: True nếu lưu thành công, False nếu thất bại
        """
        try:
            # Đảm bảo thư mục tồn tại
            os.makedirs(os.path.dirname(MARKET_REGIME_DATA), exist_ok=True)
            
            with open(MARKET_REGIME_DATA, 'w') as f:
                json.dump(self.market_regime_data, f, indent=4)
            
            logger.info(f"Đã lưu dữ liệu chế độ thị trường vào {MARKET_REGIME_DATA}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu chế độ thị trường: {str(e)}")
            return False
    
    def log_trading_decision(self, decision_data: Dict) -> bool:
        """
        Ghi log quyết định giao dịch
        
        Args:
            decision_data (Dict): Thông tin quyết định giao dịch
            
        Returns:
            bool: True nếu ghi log thành công, False nếu thất bại
        """
        try:
            # Đảm bảo thư mục tồn tại
            os.makedirs(os.path.dirname(TRADING_DECISIONS_LOG), exist_ok=True)
            
            # Thêm thời gian
            if 'timestamp' not in decision_data:
                decision_data['timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Ghi vào file log
            with open(TRADING_DECISIONS_LOG, 'a') as f:
                json_str = json.dumps(decision_data)
                f.write(f"{json_str}\n")
            
            logger.info(f"Đã ghi log quyết định giao dịch cho {decision_data.get('symbol', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi ghi log quyết định giao dịch: {str(e)}")
            return False
    
    def log_no_trade_reason(self, symbol: str, timeframe: str, reasons: List[Dict]) -> bool:
        """
        Ghi log lý do không giao dịch
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            reasons (List[Dict]): Danh sách lý do
            
        Returns:
            bool: True nếu ghi log thành công, False nếu thất bại
        """
        try:
            entry = {
                "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "symbol": symbol,
                "timeframe": timeframe,
                "price": self._get_current_price(symbol),
                "reasons": reasons
            }
            
            # Thêm vào lịch sử
            self.no_trade_reasons.append(entry)
            
            # Giới hạn kích thước (giữ 1000 bản ghi gần nhất)
            if len(self.no_trade_reasons) > 1000:
                self.no_trade_reasons = self.no_trade_reasons[-1000:]
            
            # Lưu vào file
            self._save_no_trade_reasons()
            
            logger.info(f"Đã ghi log {len(reasons)} lý do không giao dịch cho {symbol}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi ghi log lý do không giao dịch: {str(e)}")
            return False
    
    def _get_current_price(self, symbol: str) -> float:
        """
        Lấy giá hiện tại của một mã
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            float: Giá hiện tại
        """
        try:
            ticker = self.api.get_symbol_ticker(symbol)
            if ticker and 'price' in ticker:
                return float(ticker['price'])
        except Exception as e:
            logger.error(f"Lỗi khi lấy giá hiện tại của {symbol}: {str(e)}")
        
        return 0.0
    
    def analyze_global_market(self) -> Dict:
        """
        Phân tích thị trường toàn cầu
        
        Returns:
            Dict: Kết quả phân tích thị trường toàn cầu
        """
        logger.info("Đang phân tích thị trường toàn cầu...")
        
        try:
            # Lấy dữ liệu thị trường
            btc_data = self._get_klines_data("BTCUSDT", "1d", 30)
            
            result = {
                "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "global_market_cap": 0,  # Cần API bên ngoài
                "btc_dominance": 0,      # Cần API bên ngoài
                "btc_price": self._get_current_price("BTCUSDT"),
                "btc_volatility": self._calculate_volatility(btc_data) if btc_data is not None else 0,
                "market_trend": "unknown",
                "market_regime": "unknown",
                "sentiment": "neutral",
                "symbols_correlation": self._calculate_symbols_correlation()
            }
            
            # Xác định xu hướng thị trường
            if btc_data is not None:
                result["market_trend"] = self._determine_trend(btc_data)
                result["market_regime"] = self._detect_market_regime(btc_data)
            
            # Cập nhật dữ liệu chế độ thị trường
            self.market_regime_data["last_updated"] = result["timestamp"]
            self.market_regime_data["btc_dominance"] = result["btc_dominance"]
            self.market_regime_data["global_regime"] = result["market_regime"]
            self._save_market_regime_data()
            
            logger.info(f"Đã phân tích thị trường toàn cầu, chế độ: {result['market_regime']}")
            return result
        except Exception as e:
            logger.error(f"Lỗi khi phân tích thị trường toàn cầu: {str(e)}")
            return {
                "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "error": str(e),
                "market_trend": "unknown",
                "market_regime": "unknown"
            }
    
    def analyze_symbol(self, symbol: str, timeframe: str = None) -> Dict:
        """
        Phân tích chi tiết một cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str, optional): Khung thời gian, nếu None sẽ sử dụng primary_timeframe
            
        Returns:
            Dict: Kết quả phân tích
        """
        if timeframe is None:
            timeframe = self.config.get("primary_timeframe", "1h")
        
        logger.info(f"Đang phân tích {symbol} trên khung {timeframe}...")
        
        try:
            # Lấy dữ liệu giá
            klines_data = self._get_klines_data(symbol, timeframe, 200)
            
            if klines_data is None or len(klines_data) < 100:
                logger.warning(f"Không đủ dữ liệu để phân tích {symbol}")
                return {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "error": "Không đủ dữ liệu",
                    "score": 0,
                    "recommendation": "neutral"
                }
            
            # Phân tích chỉ báo kỹ thuật
            indicators = self._calculate_indicators(symbol, klines_data, timeframe)
            
            # Phân tích hỗ trợ/kháng cự
            support_resistance = self._analyze_support_resistance(klines_data)
            
            # Phân tích điểm vào/ra
            entry_exit_points = self._analyze_entry_exit_points(symbol, klines_data, indicators, support_resistance)
            
            # Tính điểm tổng hợp
            score = self._calculate_analysis_score(indicators, entry_exit_points)
            
            # Xác định khuyến nghị
            recommendation = self._determine_recommendation(score)
            
            # Phát hiện chế độ thị trường cho symbol
            market_regime = self._detect_market_regime(klines_data)
            
            # Phân tích biến động
            volatility = self._calculate_volatility(klines_data)
            
            # Tổng hợp kết quả
            result = {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "price": {
                    "current": self._get_current_price(symbol),
                    "open": float(klines_data[-1][1]),
                    "high": float(klines_data[-1][2]),
                    "low": float(klines_data[-1][3]),
                    "close": float(klines_data[-1][4]),
                    "volume": float(klines_data[-1][5])
                },
                "indicators": indicators,
                "support_resistance": support_resistance,
                "market_regime": market_regime,
                "volatility": volatility,
                "entry_exit_points": entry_exit_points,
                "score": score,
                "recommendation": recommendation
            }
            
            # Cập nhật dữ liệu chế độ thị trường cho symbol
            self.market_regime_data["symbols_regime"][symbol] = {
                "timeframe": timeframe,
                "regime": market_regime,
                "volatility": volatility,
                "last_updated": result["timestamp"]
            }
            self._save_market_regime_data()
            
            # Lưu vào lịch sử phân tích
            self.analysis_history.append(result)
            
            # Giới hạn kích thước lịch sử (giữ 1000 bản ghi gần nhất)
            if len(self.analysis_history) > 1000:
                self.analysis_history = self.analysis_history[-1000:]
            
            # Lưu lịch sử phân tích
            self._save_analysis_history()
            
            logger.info(f"Đã phân tích {symbol}, điểm: {score}, khuyến nghị: {recommendation}")
            
            # Tạo biểu đồ phân tích nếu cần
            self._generate_analysis_chart(symbol, timeframe, klines_data, result)
            
            return result
        except Exception as e:
            logger.error(f"Lỗi khi phân tích {symbol}: {str(e)}")
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "error": str(e),
                "score": 0,
                "recommendation": "neutral"
            }
    
    def _get_klines_data(self, symbol: str, timeframe: str, limit: int = 200) -> Optional[List]:
        """
        Lấy dữ liệu k-lines từ Binance
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            limit (int): Số lượng nến
            
        Returns:
            Optional[List]: Dữ liệu k-lines hoặc None nếu lỗi
        """
        try:
            klines = self.api.get_klines(symbol=symbol, interval=timeframe, limit=limit)
            if klines and len(klines) > 0:
                return klines
            else:
                logger.warning(f"Không có dữ liệu k-lines cho {symbol} {timeframe}")
                return None
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu k-lines cho {symbol} {timeframe}: {str(e)}")
            return None
    
    def _calculate_indicators(self, symbol: str, klines_data: List, timeframe: str) -> Dict:
        """
        Tính toán các chỉ báo kỹ thuật
        
        Args:
            symbol (str): Mã cặp tiền
            klines_data (List): Dữ liệu k-lines
            timeframe (str): Khung thời gian
            
        Returns:
            Dict: Kết quả các chỉ báo
        """
        try:
            # Chuyển đổi dữ liệu thành DataFrame
            df = pd.DataFrame(klines_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Chuyển đổi kiểu dữ liệu
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            # Chuyển đổi timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Khởi tạo kết quả
            result = {
                "moving_averages": {},
                "oscillators": {},
                "volume": {},
                "volatility": {}
            }
            
            # Tính moving averages
            if self.config["indicators"]["moving_averages"]["enabled"]:
                for period in self.config["indicators"]["moving_averages"]["periods"]:
                    if "SMA" in self.config["indicators"]["moving_averages"]["types"]:
                        df[f'sma_{period}'] = df['close'].rolling(window=period).mean()
                        result["moving_averages"][f"sma_{period}"] = df[f'sma_{period}'].iloc[-1]
                    
                    if "EMA" in self.config["indicators"]["moving_averages"]["types"]:
                        df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
                        result["moving_averages"][f"ema_{period}"] = df[f'ema_{period}'].iloc[-1]
            
            # Tính RSI
            if self.config["indicators"]["oscillators"]["rsi"]["enabled"]:
                period = self.config["indicators"]["oscillators"]["rsi"]["period"]
                delta = df['close'].diff()
                gain = delta.mask(delta < 0, 0)
                loss = -delta.mask(delta > 0, 0)
                avg_gain = gain.rolling(window=period).mean()
                avg_loss = loss.rolling(window=period).mean()
                rs = avg_gain / avg_loss
                df['rsi'] = 100 - (100 / (1 + rs))
                result["oscillators"]["rsi"] = df['rsi'].iloc[-1]
            
            # Tính MACD
            if self.config["indicators"]["oscillators"]["macd"]["enabled"]:
                fast = self.config["indicators"]["oscillators"]["macd"]["fast_period"]
                slow = self.config["indicators"]["oscillators"]["macd"]["slow_period"]
                signal = self.config["indicators"]["oscillators"]["macd"]["signal_period"]
                
                df['ema_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
                df['ema_slow'] = df['close'].ewm(span=slow, adjust=False).mean()
                df['macd'] = df['ema_fast'] - df['ema_slow']
                df['macd_signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
                df['macd_histogram'] = df['macd'] - df['macd_signal']
                
                result["oscillators"]["macd"] = {
                    "macd": df['macd'].iloc[-1],
                    "signal": df['macd_signal'].iloc[-1],
                    "histogram": df['macd_histogram'].iloc[-1]
                }
            
            # Tính Stochastic
            if self.config["indicators"]["oscillators"]["stochastic"]["enabled"]:
                k_period = self.config["indicators"]["oscillators"]["stochastic"]["k_period"]
                d_period = self.config["indicators"]["oscillators"]["stochastic"]["d_period"]
                smooth_k = self.config["indicators"]["oscillators"]["stochastic"]["smooth_k"]
                
                df['stoch_k'] = 100 * ((df['close'] - df['low'].rolling(window=k_period).min()) / 
                               (df['high'].rolling(window=k_period).max() - df['low'].rolling(window=k_period).min()))
                df['stoch_k'] = df['stoch_k'].rolling(window=smooth_k).mean()
                df['stoch_d'] = df['stoch_k'].rolling(window=d_period).mean()
                
                result["oscillators"]["stochastic"] = {
                    "k": df['stoch_k'].iloc[-1],
                    "d": df['stoch_d'].iloc[-1]
                }
            
            # Tính chỉ báo khối lượng
            if self.config["indicators"]["volume"]["enabled"]:
                # Volume Moving Average
                df['volume_sma'] = df['volume'].rolling(window=20).mean()
                
                # OBV (On-Balance Volume)
                if self.config["indicators"]["volume"]["obv"]:
                    df['obv'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
                    result["volume"]["obv"] = df['obv'].iloc[-1]
                
                # Chỉ số khối lượng tương đối
                df['relative_volume'] = df['volume'] / df['volume'].rolling(window=20).mean()
                
                result["volume"]["current"] = df['volume'].iloc[-1]
                result["volume"]["sma_20"] = df['volume_sma'].iloc[-1]
                result["volume"]["relative"] = df['relative_volume'].iloc[-1]
            
            # Tính chỉ báo biến động
            if self.config["indicators"]["volatility"]["enabled"]:
                # Bollinger Bands
                if self.config["indicators"]["volatility"]["bollinger_bands"]["enabled"]:
                    period = self.config["indicators"]["volatility"]["bollinger_bands"]["period"]
                    std_dev = self.config["indicators"]["volatility"]["bollinger_bands"]["std_dev"]
                    
                    df['bb_middle'] = df['close'].rolling(window=period).mean()
                    df['bb_std'] = df['close'].rolling(window=period).std()
                    df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * std_dev)
                    df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * std_dev)
                    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
                    
                    result["volatility"]["bollinger_bands"] = {
                        "upper": df['bb_upper'].iloc[-1],
                        "middle": df['bb_middle'].iloc[-1],
                        "lower": df['bb_lower'].iloc[-1],
                        "width": df['bb_width'].iloc[-1]
                    }
                
                # ATR (Average True Range)
                if self.config["indicators"]["volatility"]["atr"]["enabled"]:
                    period = self.config["indicators"]["volatility"]["atr"]["period"]
                    
                    df['tr0'] = abs(df['high'] - df['low'])
                    df['tr1'] = abs(df['high'] - df['close'].shift())
                    df['tr2'] = abs(df['low'] - df['close'].shift())
                    df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
                    df['atr'] = df['tr'].rolling(window=period).mean()
                    
                    result["volatility"]["atr"] = df['atr'].iloc[-1]
                    result["volatility"]["atr_percent"] = df['atr'].iloc[-1] / df['close'].iloc[-1] * 100
            
            return result
        except Exception as e:
            logger.error(f"Lỗi khi tính chỉ báo cho {symbol}: {str(e)}")
            return {
                "moving_averages": {},
                "oscillators": {},
                "volume": {},
                "volatility": {}
            }
    
    def _analyze_support_resistance(self, klines_data: List) -> Dict:
        """
        Phân tích các mức hỗ trợ/kháng cự
        
        Args:
            klines_data (List): Dữ liệu k-lines
            
        Returns:
            Dict: Các mức hỗ trợ/kháng cự
        """
        try:
            # Chuyển đổi dữ liệu
            df = pd.DataFrame(klines_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Chuyển đổi kiểu dữ liệu
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            # Tìm các đỉnh và đáy
            price_history = df['close'].values
            
            # Tối đa hóa tìm mức đủ dài
            high_points = []
            low_points = []
            
            # Sử dụng thuật toán fractals
            for i in range(2, len(price_history) - 2):
                # Đỉnh (high)
                if (price_history[i] > price_history[i-1] and 
                    price_history[i] > price_history[i-2] and 
                    price_history[i] > price_history[i+1] and 
                    price_history[i] > price_history[i+2]):
                    high_points.append((i, price_history[i]))
                
                # Đáy (low)
                if (price_history[i] < price_history[i-1] and 
                    price_history[i] < price_history[i-2] and 
                    price_history[i] < price_history[i+1] and 
                    price_history[i] < price_history[i+2]):
                    low_points.append((i, price_history[i]))
            
            # Lọc mức S/R quan trọng bằng cách gộp các mức gần nhau
            zone_threshold = self.config["indicators"]["support_resistance"]["zone_threshold"] * price_history[-1]
            
            resistance_levels = []
            support_levels = []
            
            # Gộp các đỉnh gần nhau
            if high_points:
                high_points.sort(key=lambda x: x[1], reverse=True)  # Sắp xếp theo giá từ cao xuống thấp
                
                current_zone = [high_points[0]]
                current_price = high_points[0][1]
                
                for i in range(1, len(high_points)):
                    if abs(high_points[i][1] - current_price) <= zone_threshold:
                        current_zone.append(high_points[i])
                    else:
                        # Tính giá trung bình của zone
                        avg_price = sum(point[1] for point in current_zone) / len(current_zone)
                        resistance_levels.append(avg_price)
                        
                        # Bắt đầu zone mới
                        current_zone = [high_points[i]]
                        current_price = high_points[i][1]
                
                # Xử lý zone cuối cùng
                if current_zone:
                    avg_price = sum(point[1] for point in current_zone) / len(current_zone)
                    resistance_levels.append(avg_price)
            
            # Gộp các đáy gần nhau
            if low_points:
                low_points.sort(key=lambda x: x[1])  # Sắp xếp theo giá từ thấp lên cao
                
                current_zone = [low_points[0]]
                current_price = low_points[0][1]
                
                for i in range(1, len(low_points)):
                    if abs(low_points[i][1] - current_price) <= zone_threshold:
                        current_zone.append(low_points[i])
                    else:
                        # Tính giá trung bình của zone
                        avg_price = sum(point[1] for point in current_zone) / len(current_zone)
                        support_levels.append(avg_price)
                        
                        # Bắt đầu zone mới
                        current_zone = [low_points[i]]
                        current_price = low_points[i][1]
                
                # Xử lý zone cuối cùng
                if current_zone:
                    avg_price = sum(point[1] for point in current_zone) / len(current_zone)
                    support_levels.append(avg_price)
            
            # Lọc các mức gần với giá hiện tại
            current_price = float(klines_data[-1][4])  # Giá đóng cửa
            
            nearby_resistance = [price for price in resistance_levels if price > current_price]
            nearby_resistance.sort()  # Sắp xếp tăng dần
            
            nearby_support = [price for price in support_levels if price < current_price]
            nearby_support.sort(reverse=True)  # Sắp xếp giảm dần
            
            result = {
                "current_price": current_price,
                "resistance_levels": resistance_levels,
                "support_levels": support_levels,
                "nearest_resistance": nearby_resistance[0] if nearby_resistance else None,
                "nearest_support": nearby_support[0] if nearby_support else None
            }
            
            return result
        except Exception as e:
            logger.error(f"Lỗi khi phân tích hỗ trợ/kháng cự: {str(e)}")
            return {
                "current_price": float(klines_data[-1][4]) if klines_data else 0,
                "resistance_levels": [],
                "support_levels": [],
                "nearest_resistance": None,
                "nearest_support": None
            }
    
    def _analyze_entry_exit_points(self, symbol: str, klines_data: List, indicators: Dict, support_resistance: Dict) -> Dict:
        """
        Phân tích các điểm vào/ra lệnh
        
        Args:
            symbol (str): Mã cặp tiền
            klines_data (List): Dữ liệu k-lines
            indicators (Dict): Chỉ báo kỹ thuật
            support_resistance (Dict): Thông tin hỗ trợ/kháng cự
            
        Returns:
            Dict: Thông tin điểm vào/ra lệnh
        """
        try:
            current_price = float(klines_data[-1][4])  # Giá đóng cửa
            market_regime = self._detect_market_regime(klines_data)
            
            # Khởi tạo kết quả
            result = {
                "long": {
                    "entry_points": [],
                    "exit_points": {
                        "take_profit": [],
                        "stop_loss": []
                    },
                    "reasoning": []
                },
                "short": {
                    "entry_points": [],
                    "exit_points": {
                        "take_profit": [],
                        "stop_loss": []
                    },
                    "reasoning": []
                },
                "score": {
                    "long": 0,
                    "short": 0
                }
            }
            
            # Điểm vào lệnh LONG
            long_entry_reasons = []
            
            # Điểm vào dựa trên RSI
            if "oscillators" in indicators and "rsi" in indicators["oscillators"]:
                rsi = indicators["oscillators"]["rsi"]
                oversold = self.config["indicators"]["oscillators"]["rsi"]["oversold"]
                
                if rsi < oversold:
                    result["long"]["entry_points"].append(current_price)
                    long_entry_reasons.append(f"RSI oversold ({rsi:.2f} < {oversold})")
            
            # Điểm vào dựa trên MACD
            if "oscillators" in indicators and "macd" in indicators["oscillators"]:
                macd = indicators["oscillators"]["macd"]["macd"]
                signal = indicators["oscillators"]["macd"]["signal"]
                histogram = indicators["oscillators"]["macd"]["histogram"]
                
                if macd > signal and histogram > 0 and histogram > 0:
                    result["long"]["entry_points"].append(current_price)
                    long_entry_reasons.append(f"MACD bullish crossover (histogram: {histogram:.6f})")
            
            # Điểm vào dựa trên Bollinger Bands
            if "volatility" in indicators and "bollinger_bands" in indicators["volatility"]:
                bb_lower = indicators["volatility"]["bollinger_bands"]["lower"]
                
                if current_price <= bb_lower:
                    result["long"]["entry_points"].append(current_price)
                    long_entry_reasons.append(f"Price at/below BB lower ({current_price:.2f} <= {bb_lower:.2f})")
            
            # Điểm vào dựa trên mức hỗ trợ
            if "nearest_support" in support_resistance and support_resistance["nearest_support"]:
                nearest_support = support_resistance["nearest_support"]
                
                if abs(current_price - nearest_support) / current_price < 0.02:  # Nếu giá gần mức hỗ trợ (2%)
                    result["long"]["entry_points"].append(nearest_support)
                    long_entry_reasons.append(f"Price near support level ({nearest_support:.2f})")
            
            # Điểm ra (take profit) cho LONG
            if "nearest_resistance" in support_resistance and support_resistance["nearest_resistance"]:
                tp_level = support_resistance["nearest_resistance"]
                result["long"]["exit_points"]["take_profit"].append(tp_level)
            else:
                # Nếu không có mức kháng cự, sử dụng % mặc định
                tp_pct = self.config["strategy_settings"]["exit_conditions"]["take_profit"]["default_percentage"] / 100
                tp_level = current_price * (1 + tp_pct)
                result["long"]["exit_points"]["take_profit"].append(tp_level)
            
            # Điểm dừng lỗ (stop loss) cho LONG
            if "nearest_support" in support_resistance and support_resistance["nearest_support"]:
                sl_level = support_resistance["nearest_support"] * 0.99  # Thêm buffer 1%
                result["long"]["exit_points"]["stop_loss"].append(sl_level)
            else:
                # Nếu không có mức hỗ trợ, sử dụng % mặc định
                sl_pct = self.config["strategy_settings"]["exit_conditions"]["stop_loss"]["default_percentage"] / 100
                sl_level = current_price * (1 - sl_pct)
                result["long"]["exit_points"]["stop_loss"].append(sl_level)
            
            # Điểm vào lệnh SHORT
            short_entry_reasons = []
            
            # Điểm vào dựa trên RSI
            if "oscillators" in indicators and "rsi" in indicators["oscillators"]:
                rsi = indicators["oscillators"]["rsi"]
                overbought = self.config["indicators"]["oscillators"]["rsi"]["overbought"]
                
                if rsi > overbought:
                    result["short"]["entry_points"].append(current_price)
                    short_entry_reasons.append(f"RSI overbought ({rsi:.2f} > {overbought})")
            
            # Điểm vào dựa trên MACD
            if "oscillators" in indicators and "macd" in indicators["oscillators"]:
                macd = indicators["oscillators"]["macd"]["macd"]
                signal = indicators["oscillators"]["macd"]["signal"]
                histogram = indicators["oscillators"]["macd"]["histogram"]
                
                if macd < signal and histogram < 0:
                    result["short"]["entry_points"].append(current_price)
                    short_entry_reasons.append(f"MACD bearish crossover (histogram: {histogram:.6f})")
            
            # Điểm vào dựa trên Bollinger Bands
            if "volatility" in indicators and "bollinger_bands" in indicators["volatility"]:
                bb_upper = indicators["volatility"]["bollinger_bands"]["upper"]
                
                if current_price >= bb_upper:
                    result["short"]["entry_points"].append(current_price)
                    short_entry_reasons.append(f"Price at/above BB upper ({current_price:.2f} >= {bb_upper:.2f})")
            
            # Điểm vào dựa trên mức kháng cự
            if "nearest_resistance" in support_resistance and support_resistance["nearest_resistance"]:
                nearest_resistance = support_resistance["nearest_resistance"]
                
                if abs(current_price - nearest_resistance) / current_price < 0.02:  # Nếu giá gần mức kháng cự (2%)
                    result["short"]["entry_points"].append(nearest_resistance)
                    short_entry_reasons.append(f"Price near resistance level ({nearest_resistance:.2f})")
            
            # Điểm ra (take profit) cho SHORT
            if "nearest_support" in support_resistance and support_resistance["nearest_support"]:
                tp_level = support_resistance["nearest_support"]
                result["short"]["exit_points"]["take_profit"].append(tp_level)
            else:
                # Nếu không có mức hỗ trợ, sử dụng % mặc định
                tp_pct = self.config["strategy_settings"]["exit_conditions"]["take_profit"]["default_percentage"] / 100
                tp_level = current_price * (1 - tp_pct)
                result["short"]["exit_points"]["take_profit"].append(tp_level)
            
            # Điểm dừng lỗ (stop loss) cho SHORT
            if "nearest_resistance" in support_resistance and support_resistance["nearest_resistance"]:
                sl_level = support_resistance["nearest_resistance"] * 1.01  # Thêm buffer 1%
                result["short"]["exit_points"]["stop_loss"].append(sl_level)
            else:
                # Nếu không có mức kháng cự, sử dụng % mặc định
                sl_pct = self.config["strategy_settings"]["exit_conditions"]["stop_loss"]["default_percentage"] / 100
                sl_level = current_price * (1 + sl_pct)
                result["short"]["exit_points"]["stop_loss"].append(sl_level)
            
            # Lưu lý do
            result["long"]["reasoning"] = long_entry_reasons
            result["short"]["reasoning"] = short_entry_reasons
            
            # Tính điểm dựa trên số lý do
            result["score"]["long"] = len(long_entry_reasons) * 25  # Mỗi lý do tối đa 25 điểm
            result["score"]["short"] = len(short_entry_reasons) * 25  # Mỗi lý do tối đa 25 điểm
            
            # Điều chỉnh điểm theo chế độ thị trường
            if market_regime == "trending_up":
                result["score"]["long"] += 20
                result["score"]["short"] -= 20
            elif market_regime == "trending_down":
                result["score"]["long"] -= 20
                result["score"]["short"] += 20
            
            # Giới hạn điểm từ 0-100
            result["score"]["long"] = max(0, min(100, result["score"]["long"]))
            result["score"]["short"] = max(0, min(100, result["score"]["short"]))
            
            return result
        except Exception as e:
            logger.error(f"Lỗi khi phân tích điểm vào/ra lệnh cho {symbol}: {str(e)}")
            return {
                "long": {"entry_points": [], "exit_points": {"take_profit": [], "stop_loss": []}, "reasoning": []},
                "short": {"entry_points": [], "exit_points": {"take_profit": [], "stop_loss": []}, "reasoning": []},
                "score": {"long": 0, "short": 0}
            }
    
    def _calculate_analysis_score(self, indicators: Dict, entry_exit_points: Dict) -> int:
        """
        Tính điểm phân tích tổng hợp
        
        Args:
            indicators (Dict): Chỉ báo kỹ thuật
            entry_exit_points (Dict): Thông tin điểm vào/ra lệnh
            
        Returns:
            int: Điểm phân tích (0-100)
        """
        try:
            long_score = entry_exit_points["score"]["long"]
            short_score = entry_exit_points["score"]["short"]
            
            # Thiên về long hoặc short
            if long_score > short_score:
                final_score = long_score
            else:
                final_score = 100 - short_score  # Đảo ngược để 0 = strong sell, 100 = strong buy
            
            return final_score
        except Exception as e:
            logger.error(f"Lỗi khi tính điểm phân tích: {str(e)}")
            return 50  # Điểm trung lập
    
    def _determine_recommendation(self, score: int) -> str:
        """
        Xác định khuyến nghị dựa trên điểm
        
        Args:
            score (int): Điểm phân tích
            
        Returns:
            str: Khuyến nghị
        """
        thresholds = self.config["analysis_thresholds"]
        
        if score >= thresholds["strong_buy"]:
            return "strong_buy"
        elif score >= thresholds["buy"]:
            return "buy"
        elif score >= thresholds["neutral"]:
            return "neutral"
        elif score >= thresholds["sell"]:
            return "sell"
        else:
            return "strong_sell"
    
    def _determine_trend(self, klines_data: List) -> str:
        """
        Xác định xu hướng thị trường
        
        Args:
            klines_data (List): Dữ liệu k-lines
            
        Returns:
            str: Xu hướng thị trường
        """
        try:
            # Chuyển đổi dữ liệu
            closes = [float(kline[4]) for kline in klines_data]
            
            # Tính EMA 50
            ema_period = 50
            ema = closes[0]
            k = 2 / (ema_period + 1)
            
            for close in closes[1:]:
                ema = close * k + ema * (1 - k)
            
            # So sánh với giá hiện tại
            current_price = closes[-1]
            
            if current_price > ema * 1.05:  # Nếu giá cao hơn EMA 5%
                return "bullish"
            elif current_price < ema * 0.95:  # Nếu giá thấp hơn EMA 5%
                return "bearish"
            else:
                return "neutral"
        except Exception as e:
            logger.error(f"Lỗi khi xác định xu hướng: {str(e)}")
            return "unknown"
    
    def _detect_market_regime(self, klines_data: List) -> str:
        """
        Phát hiện chế độ thị trường
        
        Args:
            klines_data (List): Dữ liệu k-lines
            
        Returns:
            str: Chế độ thị trường
        """
        try:
            # Chuyển đổi dữ liệu
            closes = [float(kline[4]) for kline in klines_data]
            
            # Tính biến động
            volatility = self._calculate_volatility(klines_data)
            
            # Tính ADX để đo lường sức mạnh xu hướng
            adx = self._calculate_adx(klines_data)
            
            # Phân tích xu hướng
            trend = self._determine_trend(klines_data)
            
            # Xác định chế độ thị trường
            if adx > 25:  # Xu hướng mạnh
                if trend == "bullish":
                    return "trending_up"
                elif trend == "bearish":
                    return "trending_down"
            
            # Biến động cao
            if volatility > 3.0:  # Biến động > 3%
                return "high_volatility"
            
            # Biến động thấp
            if volatility < 1.0:  # Biến động < 1%
                return "low_volatility"
            
            # Mặc định: thị trường đi ngang
            return "ranging"
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện chế độ thị trường: {str(e)}")
            return "unknown"
    
    def _calculate_volatility(self, klines_data: List) -> float:
        """
        Tính biến động thị trường dựa trên ATR%
        
        Args:
            klines_data (List): Dữ liệu k-lines
            
        Returns:
            float: Biến động (%)
        """
        try:
            if len(klines_data) < 14:
                return 0.0
            
            # Chuyển đổi dữ liệu
            df = pd.DataFrame(klines_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Chuyển đổi kiểu dữ liệu
            for col in ['open', 'high', 'low', 'close']:
                df[col] = df[col].astype(float)
            
            # Tính True Range
            df['tr0'] = abs(df['high'] - df['low'])
            df['tr1'] = abs(df['high'] - df['close'].shift())
            df['tr2'] = abs(df['low'] - df['close'].shift())
            df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
            
            # Tính ATR
            atr = df['tr'].rolling(window=14).mean().iloc[-1]
            
            # Tính ATR%
            current_price = float(klines_data[-1][4])
            atr_percent = (atr / current_price) * 100
            
            return atr_percent
        except Exception as e:
            logger.error(f"Lỗi khi tính biến động: {str(e)}")
            return 0.0
    
    def _calculate_adx(self, klines_data: List, period: int = 14) -> float:
        """
        Tính ADX (Average Directional Index)
        
        Args:
            klines_data (List): Dữ liệu k-lines
            period (int): Chu kỳ
            
        Returns:
            float: Giá trị ADX
        """
        try:
            if len(klines_data) < period * 2:
                return 0.0
            
            # Chuyển đổi dữ liệu
            df = pd.DataFrame(klines_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Chuyển đổi kiểu dữ liệu
            for col in ['high', 'low', 'close']:
                df[col] = df[col].astype(float)
            
            # Tính +DM và -DM
            df['high_diff'] = df['high'].diff()
            df['low_diff'] = df['low'].diff() * -1
            
            df['+DM'] = np.where((df['high_diff'] > df['low_diff']) & (df['high_diff'] > 0), df['high_diff'], 0)
            df['-DM'] = np.where((df['low_diff'] > df['high_diff']) & (df['low_diff'] > 0), df['low_diff'], 0)
            
            # Tính True Range
            df['tr0'] = abs(df['high'] - df['low'])
            df['tr1'] = abs(df['high'] - df['close'].shift())
            df['tr2'] = abs(df['low'] - df['close'].shift())
            df['TR'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
            
            # Tính +DI và -DI
            df['ATR'] = df['TR'].rolling(window=period).mean()
            df['+DI'] = (df['+DM'].rolling(window=period).mean() / df['ATR']) * 100
            df['-DI'] = (df['-DM'].rolling(window=period).mean() / df['ATR']) * 100
            
            # Tính DX và ADX
            df['DX'] = (abs(df['+DI'] - df['-DI']) / (df['+DI'] + df['-DI'])) * 100
            df['ADX'] = df['DX'].rolling(window=period).mean()
            
            return df['ADX'].iloc[-1]
        except Exception as e:
            logger.error(f"Lỗi khi tính ADX: {str(e)}")
            return 0.0
    
    def _calculate_symbols_correlation(self) -> Dict:
        """
        Tính tương quan giữa các cặp tiền
        
        Returns:
            Dict: Ma trận tương quan
        """
        try:
            symbols = self.config["symbols_to_analyze"]
            timeframe = self.config["primary_timeframe"]
            
            # Lấy dữ liệu giá đóng cửa
            price_data = {}
            
            for symbol in symbols:
                klines = self._get_klines_data(symbol, timeframe, 30)
                if klines:
                    closes = [float(kline[4]) for kline in klines]
                    price_data[symbol] = closes
            
            # Tính tương quan
            correlation_matrix = {}
            
            for symbol1 in price_data:
                correlation_matrix[symbol1] = {}
                
                for symbol2 in price_data:
                    if len(price_data[symbol1]) == len(price_data[symbol2]):
                        correlation = np.corrcoef(price_data[symbol1], price_data[symbol2])[0, 1]
                        correlation_matrix[symbol1][symbol2] = correlation
                    else:
                        correlation_matrix[symbol1][symbol2] = 0
            
            return correlation_matrix
        except Exception as e:
            logger.error(f"Lỗi khi tính tương quan: {str(e)}")
            return {}
    
    def _generate_analysis_chart(self, symbol: str, timeframe: str, klines_data: List, analysis_result: Dict) -> bool:
        """
        Tạo biểu đồ phân tích
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            klines_data (List): Dữ liệu k-lines
            analysis_result (Dict): Kết quả phân tích
            
        Returns:
            bool: True nếu tạo thành công, False nếu thất bại
        """
        try:
            # Đảm bảo thư mục tồn tại
            chart_dir = "charts/market_analysis"
            os.makedirs(chart_dir, exist_ok=True)
            
            # Tạo DataFrame
            df = pd.DataFrame(klines_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Chuyển đổi kiểu dữ liệu
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            # Chuyển đổi timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Tính các chỉ báo
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            
            # Tạo biểu đồ
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [4, 1, 1]})
            
            # Đặt tiêu đề
            fig.suptitle(f'{symbol} - {timeframe} - Phân tích: {analysis_result["recommendation"].upper()}', fontsize=16)
            
            # Vẽ giá
            ax1.plot(df['timestamp'], df['close'], label='Close')
            ax1.plot(df['timestamp'], df['sma_20'], label='SMA 20')
            ax1.plot(df['timestamp'], df['sma_50'], label='SMA 50')
            
            # Vẽ các mức hỗ trợ/kháng cự
            if "support_resistance" in analysis_result:
                sr_levels = analysis_result["support_resistance"]
                
                for level in sr_levels.get("resistance_levels", [])[:3]:  # Chỉ vẽ 3 mức kháng cự quan trọng nhất
                    ax1.axhline(y=level, color='r', linestyle='--', alpha=0.5)
                
                for level in sr_levels.get("support_levels", [])[:3]:  # Chỉ vẽ 3 mức hỗ trợ quan trọng nhất
                    ax1.axhline(y=level, color='g', linestyle='--', alpha=0.5)
            
            # Vẽ điểm vào/ra
            if "entry_exit_points" in analysis_result:
                entry_exit = analysis_result["entry_exit_points"]
                
                # Điểm vào long
                for entry in entry_exit.get("long", {}).get("entry_points", []):
                    ax1.axhline(y=entry, color='blue', linestyle='-', alpha=0.3)
                
                # Điểm vào short
                for entry in entry_exit.get("short", {}).get("entry_points", []):
                    ax1.axhline(y=entry, color='red', linestyle='-', alpha=0.3)
                
                # Take profit và stop loss
                for tp in entry_exit.get("long", {}).get("exit_points", {}).get("take_profit", []):
                    ax1.axhline(y=tp, color='green', linestyle=':', alpha=0.5)
                
                for sl in entry_exit.get("long", {}).get("exit_points", {}).get("stop_loss", []):
                    ax1.axhline(y=sl, color='red', linestyle=':', alpha=0.5)
            
            # Vẽ volume
            ax2.bar(df['timestamp'], df['volume'], color='blue', alpha=0.5)
            ax2.set_ylabel('Volume')
            
            # Vẽ điểm
            ax3.plot(df['timestamp'].iloc[-1], analysis_result.get("score", 50), 'ro', markersize=10)
            ax3.axhline(y=50, color='black', linestyle='-', alpha=0.3)
            ax3.set_ylim(0, 100)
            
            # Thêm thông tin
            text = f"Score: {analysis_result.get('score', 50)}/100\n"
            text += f"Market Regime: {analysis_result.get('market_regime', 'unknown')}\n"
            text += f"Volatility: {analysis_result.get('volatility', 0):.2f}%\n"
            
            if "entry_exit_points" in analysis_result:
                entry_exit = analysis_result["entry_exit_points"]
                long_reasons = entry_exit.get("long", {}).get("reasoning", [])
                short_reasons = entry_exit.get("short", {}).get("reasoning", [])
                
                if long_reasons:
                    text += f"\nLong Reasons ({entry_exit.get('score', {}).get('long', 0)}):\n"
                    for reason in long_reasons[:3]:  # Chỉ hiện 3 lý do hàng đầu
                        text += f"- {reason}\n"
                
                if short_reasons:
                    text += f"\nShort Reasons ({entry_exit.get('score', {}).get('short', 0)}):\n"
                    for reason in short_reasons[:3]:  # Chỉ hiện 3 lý do hàng đầu
                        text += f"- {reason}\n"
            
            ax3.text(df['timestamp'].iloc[0], 50, text, fontsize=10, verticalalignment='center')
            
            # Đặt nhãn
            ax1.set_ylabel('Price')
            ax3.set_ylabel('Score')
            ax3.set_xlabel('Time')
            
            # Thêm legend
            ax1.legend()
            
            # Điều chỉnh định dạng
            plt.tight_layout()
            
            # Lưu biểu đồ
            chart_path = f"{chart_dir}/{symbol}_{timeframe}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(chart_path)
            plt.close()
            
            logger.info(f"Đã tạo biểu đồ phân tích tại {chart_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ phân tích: {str(e)}")
            return False
    
    def check_trading_conditions(self, symbol: str, timeframe: str = None, direction: str = None) -> Tuple[bool, List[Dict]]:
        """
        Kiểm tra điều kiện giao dịch và trả về quyết định cùng các lý do
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str, optional): Khung thời gian
            direction (str, optional): Hướng giao dịch ('long' hoặc 'short'), nếu None sẽ chọn dựa trên phân tích
            
        Returns:
            Tuple[bool, List[Dict]]: (Có nên giao dịch không, Danh sách lý do)
        """
        if timeframe is None:
            timeframe = self.config["primary_timeframe"]
        
        logger.info(f"Đang kiểm tra điều kiện giao dịch cho {symbol} {timeframe} {direction or 'auto'}")
        
        try:
            # Phân tích cặp tiền
            analysis = self.analyze_symbol(symbol, timeframe)
            
            # Nếu có lỗi trong phân tích
            if "error" in analysis:
                reasons = [{
                    "category": "technical_indicators",
                    "reason": f"Lỗi khi phân tích: {analysis['error']}",
                    "importance": "high"
                }]
                self.log_no_trade_reason(symbol, timeframe, reasons)
                return False, reasons
            
            # Xác định hướng giao dịch nếu không được cung cấp
            if direction is None:
                if analysis["recommendation"] in ["strong_buy", "buy"]:
                    direction = "long"
                elif analysis["recommendation"] in ["strong_sell", "sell"]:
                    direction = "short"
                else:
                    reasons = [{
                        "category": "technical_indicators",
                        "reason": f"Không có khuyến nghị rõ ràng (điểm: {analysis['score']})",
                        "importance": "medium"
                    }]
                    self.log_no_trade_reason(symbol, timeframe, reasons)
                    return False, reasons
            
            # Kiểm tra điều kiện về chỉ báo kỹ thuật
            reasons = []
            
            # Không điểm nào
            if (direction == "long" and analysis["entry_exit_points"]["score"]["long"] == 0) or \
               (direction == "short" and analysis["entry_exit_points"]["score"]["short"] == 0):
                reasons.append({
                    "category": "technical_indicators",
                    "reason": f"Không có điểm {direction} (điểm: 0)",
                    "importance": "high"
                })
            
            # Các điểm quá thấp
            if (direction == "long" and analysis["entry_exit_points"]["score"]["long"] < 50) or \
               (direction == "short" and analysis["entry_exit_points"]["score"]["short"] < 50):
                reasons.append({
                    "category": "technical_indicators",
                    "reason": f"Điểm {direction} quá thấp ({analysis['entry_exit_points']['score'][direction]})",
                    "importance": "medium"
                })
            
            # Điểm vào không đủ
            if len(analysis["entry_exit_points"][direction]["entry_points"]) == 0:
                reasons.append({
                    "category": "technical_indicators",
                    "reason": f"Không có điểm vào cho {direction}",
                    "importance": "high"
                })
            
            # Điểm ra không đủ
            if len(analysis["entry_exit_points"][direction]["exit_points"]["take_profit"]) == 0 or \
               len(analysis["entry_exit_points"][direction]["exit_points"]["stop_loss"]) == 0:
                reasons.append({
                    "category": "risk_management",
                    "reason": f"Thiếu điểm take profit hoặc stop loss cho {direction}",
                    "importance": "high"
                })
            
            # Chế độ thị trường không phù hợp với hướng giao dịch
            if direction == "long" and analysis["market_regime"] == "trending_down":
                reasons.append({
                    "category": "market_conditions",
                    "reason": f"Không nên mua khi thị trường đang giảm ({analysis['market_regime']})",
                    "importance": "high"
                })
            elif direction == "short" and analysis["market_regime"] == "trending_up":
                reasons.append({
                    "category": "market_conditions",
                    "reason": f"Không nên bán khi thị trường đang tăng ({analysis['market_regime']})",
                    "importance": "high"
                })
            
            # Biến động quá cao
            if analysis.get("volatility", 0) > 5.0:  # Biến động > 5%
                reasons.append({
                    "category": "volatility",
                    "reason": f"Biến động quá cao ({analysis['volatility']:.2f}%)",
                    "importance": "medium"
                })
            
            # Nếu đang ở thị trường biến động cao mà không có lý do vào lệnh rõ ràng
            if analysis["market_regime"] == "high_volatility" and len(analysis["entry_exit_points"][direction]["reasoning"]) < 2:
                reasons.append({
                    "category": "volatility",
                    "reason": f"Không đủ lý do vào lệnh trong thị trường biến động cao",
                    "importance": "medium"
                })
            
            # Nếu có quá nhiều lý do không giao dịch
            if len(reasons) >= 2:
                self.log_no_trade_reason(symbol, timeframe, reasons)
                return False, reasons
            
            # Nếu có ít nhất một lý do quan trọng cao
            for reason in reasons:
                if reason["importance"] == "high":
                    self.log_no_trade_reason(symbol, timeframe, reasons)
                    return False, reasons
            
            # Nếu không có lý do nào không giao dịch
            if len(reasons) == 0:
                # Ghi log quyết định giao dịch
                decision_data = {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "direction": direction,
                    "price": analysis["price"]["current"],
                    "score": analysis["entry_exit_points"]["score"][direction],
                    "entry_points": analysis["entry_exit_points"][direction]["entry_points"],
                    "take_profit": analysis["entry_exit_points"][direction]["exit_points"]["take_profit"],
                    "stop_loss": analysis["entry_exit_points"][direction]["exit_points"]["stop_loss"],
                    "reasoning": analysis["entry_exit_points"][direction]["reasoning"],
                    "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                self.log_trading_decision(decision_data)
                
                logger.info(f"Quyết định giao dịch {direction.upper()} cho {symbol} với điểm {analysis['entry_exit_points']['score'][direction]}")
                return True, []
            
            # Nếu có lý do không giao dịch nhưng không quan trọng
            self.log_no_trade_reason(symbol, timeframe, reasons)
            return False, reasons
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra điều kiện giao dịch cho {symbol}: {str(e)}")
            reasons = [{
                "category": "technical_indicators",
                "reason": f"Lỗi hệ thống: {str(e)}",
                "importance": "high"
            }]
            self.log_no_trade_reason(symbol, timeframe, reasons)
            return False, reasons
    
    def generate_trading_plan(self) -> Dict:
        """
        Tạo kế hoạch giao dịch cho tất cả các cặp tiền được theo dõi
        
        Returns:
            Dict: Kế hoạch giao dịch
        """
        logger.info("Đang tạo kế hoạch giao dịch...")
        
        try:
            # Phân tích thị trường toàn cầu
            global_analysis = self.analyze_global_market()
            
            # Phân tích từng cặp tiền
            symbols_analysis = {}
            trading_opportunities = []
            
            for symbol in self.config["symbols_to_analyze"]:
                analysis = self.analyze_symbol(symbol, self.config["primary_timeframe"])
                symbols_analysis[symbol] = analysis
                
                # Kiểm tra cơ hội giao dịch
                if analysis["recommendation"] in ["strong_buy", "buy"]:
                    can_trade, reasons = self.check_trading_conditions(symbol, self.config["primary_timeframe"], "long")
                    if can_trade:
                        trading_opportunities.append({
                            "symbol": symbol,
                            "direction": "long",
                            "timeframe": self.config["primary_timeframe"],
                            "score": analysis["entry_exit_points"]["score"]["long"],
                            "reasoning": analysis["entry_exit_points"]["long"]["reasoning"],
                            "entry_points": analysis["entry_exit_points"]["long"]["entry_points"],
                            "take_profit": analysis["entry_exit_points"]["long"]["exit_points"]["take_profit"],
                            "stop_loss": analysis["entry_exit_points"]["long"]["exit_points"]["stop_loss"]
                        })
                elif analysis["recommendation"] in ["strong_sell", "sell"]:
                    can_trade, reasons = self.check_trading_conditions(symbol, self.config["primary_timeframe"], "short")
                    if can_trade:
                        trading_opportunities.append({
                            "symbol": symbol,
                            "direction": "short",
                            "timeframe": self.config["primary_timeframe"],
                            "score": analysis["entry_exit_points"]["score"]["short"],
                            "reasoning": analysis["entry_exit_points"]["short"]["reasoning"],
                            "entry_points": analysis["entry_exit_points"]["short"]["entry_points"],
                            "take_profit": analysis["entry_exit_points"]["short"]["exit_points"]["take_profit"],
                            "stop_loss": analysis["entry_exit_points"]["short"]["exit_points"]["stop_loss"]
                        })
            
            # Sắp xếp cơ hội theo điểm
            trading_opportunities.sort(key=lambda x: x["score"], reverse=True)
            
            # Tạo kế hoạch giao dịch
            plan = {
                "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "global_market": {
                    "trend": global_analysis["market_trend"],
                    "regime": global_analysis["market_regime"],
                    "btc_price": global_analysis["btc_price"]
                },
                "symbols_analysis": {
                    symbol: {
                        "score": analysis["score"],
                        "recommendation": analysis["recommendation"],
                        "market_regime": analysis["market_regime"],
                        "current_price": analysis["price"]["current"]
                    } for symbol, analysis in symbols_analysis.items()
                },
                "trading_opportunities": trading_opportunities
            }
            
            logger.info(f"Đã tạo kế hoạch giao dịch với {len(trading_opportunities)} cơ hội")
            return plan
        except Exception as e:
            logger.error(f"Lỗi khi tạo kế hoạch giao dịch: {str(e)}")
            return {
                "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "error": str(e),
                "trading_opportunities": []
            }
    
    def get_no_trade_reasons_summary(self) -> Dict:
        """
        Lấy tóm tắt về các lý do không giao dịch
        
        Returns:
            Dict: Thống kê về lý do không giao dịch
        """
        try:
            # Đếm số lần xuất hiện của từng loại lý do
            categories_count = {}
            
            for entry in self.no_trade_reasons:
                for reason in entry.get("reasons", []):
                    category = reason.get("category")
                    if category:
                        categories_count[category] = categories_count.get(category, 0) + 1
            
            # Thống kê theo cặp tiền
            symbols_count = {}
            
            for entry in self.no_trade_reasons:
                symbol = entry.get("symbol")
                if symbol:
                    symbols_count[symbol] = symbols_count.get(symbol, 0) + 1
            
            # Sắp xếp theo số lượng giảm dần
            categories_sorted = sorted(categories_count.items(), key=lambda x: x[1], reverse=True)
            symbols_sorted = sorted(symbols_count.items(), key=lambda x: x[1], reverse=True)
            
            # Lấy những lý do chi tiết phổ biến nhất
            detailed_reasons = {}
            
            for entry in self.no_trade_reasons:
                for reason in entry.get("reasons", []):
                    reason_text = reason.get("reason")
                    if reason_text:
                        detailed_reasons[reason_text] = detailed_reasons.get(reason_text, 0) + 1
            
            # Sắp xếp lý do chi tiết
            detailed_reasons_sorted = sorted(detailed_reasons.items(), key=lambda x: x[1], reverse=True)
            
            return {
                "total_entries": len(self.no_trade_reasons),
                "by_category": categories_sorted,
                "by_symbol": symbols_sorted,
                "top_reasons": detailed_reasons_sorted[:10]
            }
        except Exception as e:
            logger.error(f"Lỗi khi tổng hợp lý do không giao dịch: {str(e)}")
            return {"error": str(e)}

def main():
    """Hàm chính"""
    print("\nHỆ THỐNG PHÂN TÍCH THỊ TRƯỜNG VÀ LOGIC VÀO/RA LỆNH\n")
    
    analyzer = MarketAnalysisSystem()
    
    print("1. Phân tích thị trường")
    global_market = analyzer.analyze_global_market()
    print(f"   Xu hướng: {global_market['market_trend']}")
    print(f"   Chế độ: {global_market['market_regime']}")
    print(f"   Giá BTC: ${global_market['btc_price']:.2f}")
    
    print("\n2. Sinh kế hoạch giao dịch")
    plan = analyzer.generate_trading_plan()
    print(f"   Tìm thấy {len(plan['trading_opportunities'])} cơ hội giao dịch")
    
    if plan['trading_opportunities']:
        print("\n3. Top 3 cơ hội giao dịch:")
        for i, opportunity in enumerate(plan['trading_opportunities'][:3]):
            print(f"   {i+1}. {opportunity['symbol']} - {opportunity['direction'].upper()} (Điểm: {opportunity['score']:.1f})")
            print(f"      - Giá vào: {opportunity['entry_points'][0] if opportunity['entry_points'] else 'N/A'}")
            print(f"      - Take profit: {opportunity['take_profit'][0] if opportunity['take_profit'] else 'N/A'}")
            print(f"      - Stop loss: {opportunity['stop_loss'][0] if opportunity['stop_loss'] else 'N/A'}")
            print(f"      - Lý do: {opportunity['reasoning'][0] if opportunity['reasoning'] else 'N/A'}")
    
    print("\n4. Tóm tắt lý do không giao dịch")
    reasons_summary = analyzer.get_no_trade_reasons_summary()
    
    if "error" not in reasons_summary:
        print(f"   Tổng số bản ghi: {reasons_summary['total_entries']}")
        
        print("   Top 3 danh mục:")
        for category, count in reasons_summary.get('by_category', [])[:3]:
            print(f"      - {category}: {count}")
        
        print("   Top 3 lý do chi tiết:")
        for reason, count in reasons_summary.get('top_reasons', [])[:3]:
            print(f"      - {reason}: {count}")
    
    print("\nHoàn thành phân tích và sinh kế hoạch giao dịch!")

if __name__ == "__main__":
    main()