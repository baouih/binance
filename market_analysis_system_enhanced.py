#!/usr/bin/env python3
"""
Hệ thống phân tích thị trường và vào/ra lệnh tổng hợp nâng cao (cải tiến)

Phiên bản cải tiến của market_analysis_system.py, tích hợp:
1. Ngưỡng biến động thông minh
2. Phân tích thanh khoản thị trường
3. Sinh điểm vào/ra lệnh nâng cao
4. Giải quyết xung đột đa khung thời gian
5. Phát hiện đảo chiều kỹ thuật
"""

import os
import json
import time
import logging
import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union

from binance_api import BinanceAPI
from market_analysis_system import MarketAnalysisSystem

# Import các module cải tiến
from adaptive_volatility_threshold import AdaptiveVolatilityThreshold
from liquidity_analyzer import LiquidityAnalyzer
from enhanced_entry_exit_generator import EnhancedEntryExitGenerator
from multi_timeframe_conflict_resolver import MultiTimeframeConflictResolver
from technical_reversal_detector import TechnicalReversalDetector

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("market_analysis_system_enhanced")

# Đường dẫn file
ENHANCED_CONFIG_PATH = "configs/market_analysis_enhanced_config.json"

class MarketAnalysisSystemEnhanced:
    """
    Hệ thống phân tích thị trường và logic vào/ra lệnh toàn diện nâng cao
    """
    
    def __init__(self, config_path: str = ENHANCED_CONFIG_PATH):
        """
        Khởi tạo hệ thống phân tích thị trường nâng cao
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
        """
        self.config_path = config_path
        self.config = self._load_or_create_config()
        self.api = BinanceAPI()
        
        # Khởi tạo hệ thống phân tích cơ bản
        self.base_system = MarketAnalysisSystem()
        
        # Khởi tạo các module cải tiến
        self.volatility_analyzer = AdaptiveVolatilityThreshold(self.api)
        self.liquidity_analyzer = LiquidityAnalyzer(self.api)
        self.entry_exit_generator = EnhancedEntryExitGenerator(self.api)
        self.conflict_resolver = MultiTimeframeConflictResolver()
        self.reversal_detector = TechnicalReversalDetector(self.api)
        
        # Tạo các thư mục cần thiết
        self._ensure_directories()
        
        logger.info("Đã khởi tạo hệ thống phân tích thị trường nâng cao")
    
    def _ensure_directories(self):
        """Tạo các thư mục cần thiết nếu chưa tồn tại"""
        directories = [
            "configs",
            "reports",
            "logs",
            "data",
            "charts/enhanced_analysis"
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
    
    def _load_or_create_config(self) -> Dict:
        """
        Tải hoặc tạo cấu hình từ file
        
        Returns:
            Dict: Cấu hình đã tải
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình nâng cao từ {self.config_path}")
                return config
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình nâng cao: {str(e)}")
        
        # Tạo cấu hình mặc định
        default_config = {
            "version": "1.0.0",
            "enable_enhanced_features": {
                "adaptive_volatility_threshold": True,
                "liquidity_analysis": True,
                "enhanced_entry_exit": True,
                "multi_timeframe_conflict_resolution": True,
                "technical_reversal_detection": True
            },
            "reversal_consideration": {
                "enabled": True,
                "min_score": 65,
                "override_market_direction": True
            },
            "multi_timeframe_settings": {
                "resolution_method": "weighted_average",  # weighted_average, majority_vote, primary_only, consensus
                "timeframes": ["5m", "15m", "1h", "4h", "1d"],
                "primary_timeframe": "1h"
            },
            "trading_conditions": {
                "min_liquidity_score": 40,
                "min_mtf_confidence": 0.6,
                "min_risk_reward_ratio": 1.5,
                "require_entry_exit_points": True,
                "allow_reversal_signals": True
            },
            "logging": {
                "save_enhanced_analysis": True,
                "detailed_reasoning": True,
                "log_level": "INFO"
            },
            "last_updated": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Lưu cấu hình mặc định
        try:
            # Đảm bảo thư mục tồn tại
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            
            logger.info(f"Đã tạo cấu hình nâng cao mặc định tại {self.config_path}")
            return default_config
        except Exception as e:
            logger.error(f"Lỗi khi tạo cấu hình nâng cao mặc định: {str(e)}")
            return default_config
    
    def save_config(self) -> bool:
        """
        Lưu cấu hình vào file
        
        Returns:
            bool: True nếu lưu thành công, False nếu thất bại
        """
        try:
            # Cập nhật thời gian
            self.config["last_updated"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Đảm bảo thư mục tồn tại
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Lưu cấu hình
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            
            logger.info(f"Đã lưu cấu hình nâng cao vào {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình nâng cao: {str(e)}")
            return False
    
    def analyze_symbol(self, symbol: str, timeframe: str = "1h") -> Dict:
        """
        Phân tích một cặp tiền với các tính năng nâng cao
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            
        Returns:
            Dict: Kết quả phân tích
        """
        logger.info(f"Đang phân tích nâng cao {symbol} trên khung {timeframe}...")
        
        try:
            # Sử dụng phân tích cơ bản từ hệ thống gốc
            base_analysis = self.base_system.analyze_symbol(symbol, timeframe)
            
            # Bổ sung các phân tích nâng cao
            enhanced_analysis = self._enhance_analysis(symbol, timeframe, base_analysis)
            
            # Lưu kết quả phân tích nếu được cấu hình
            if self.config["logging"]["save_enhanced_analysis"]:
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                result_path = f"reports/enhanced_analysis_{symbol}_{timeframe}_{timestamp}.json"
                
                with open(result_path, 'w') as f:
                    json.dump(enhanced_analysis, f, indent=4)
            
            logger.info(f"Đã phân tích nâng cao {symbol}, điểm: {enhanced_analysis['score']}, khuyến nghị: {enhanced_analysis['recommendation']}")
            
            return enhanced_analysis
        
        except Exception as e:
            logger.error(f"Lỗi khi phân tích nâng cao {symbol}: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Trả về phân tích cơ bản nếu phân tích nâng cao thất bại
            return self.base_system.analyze_symbol(symbol, timeframe)
    
    def _enhance_analysis(self, symbol: str, timeframe: str, base_analysis: Dict) -> Dict:
        """
        Bổ sung các phân tích nâng cao vào phân tích cơ bản
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            base_analysis (Dict): Phân tích cơ bản
            
        Returns:
            Dict: Phân tích nâng cao
        """
        enhanced_analysis = base_analysis.copy()
        
        # 1. Cập nhật và kiểm tra ngưỡng biến động thông minh
        if self.config["enable_enhanced_features"]["adaptive_volatility_threshold"]:
            volatility = base_analysis.get("volatility", 0)
            threshold = self.volatility_analyzer.get_volatility_threshold(symbol)
            
            # Cập nhật lịch sử biến động
            self.volatility_analyzer.update_volatility_history(symbol, volatility)
            
            # Tính ngưỡng thích ứng
            adaptive_threshold = self.volatility_analyzer._calculate_adaptive_threshold(symbol)
            if adaptive_threshold:
                threshold = adaptive_threshold
            
            enhanced_analysis["volatility_threshold"] = threshold
            enhanced_analysis["is_high_volatility"] = volatility > threshold
        
        # 2. Bổ sung phân tích thanh khoản
        if self.config["enable_enhanced_features"]["liquidity_analysis"]:
            liquidity_result = self.liquidity_analyzer.check_liquidity_conditions(symbol)
            
            enhanced_analysis["liquidity"] = {
                "score": liquidity_result.get("score", 0),
                "is_tradable": liquidity_result.get("is_tradable", False),
                "volume_ratio": liquidity_result.get("volume_ratio", 0),
                "spread_pct": liquidity_result.get("spread_pct", 0),
                "depth_sum": liquidity_result.get("depth_sum", 0),
                "depth_ratio": liquidity_result.get("depth_ratio", 0),
                "reasons": liquidity_result.get("reasons", [])
            }
        
        # 3. Tạo điểm vào/ra lệnh nâng cao
        if self.config["enable_enhanced_features"]["enhanced_entry_exit"]:
            # Xác định hướng từ khuyến nghị
            direction = None
            if base_analysis["recommendation"] in ["strong_buy", "buy"]:
                direction = "long"
            elif base_analysis["recommendation"] in ["strong_sell", "sell"]:
                direction = "short"
            
            # Nếu có hướng rõ ràng, tạo điểm vào/ra
            if direction:
                current_price = base_analysis["price"]["current"]
                market_regime = base_analysis["market_regime"]
                
                # Lấy dữ liệu giá nếu cần
                df = None
                if hasattr(self, 'df') and symbol in self.df and timeframe in self.df[symbol]:
                    df = self.df[symbol][timeframe]
                
                entry_exit_result = self.entry_exit_generator.get_entry_exit_points(
                    symbol, direction, current_price, df, market_regime
                )
                
                enhanced_analysis["entry_exit_enhanced"] = entry_exit_result
        
        # 4. Kiểm tra tín hiệu đảo chiều kỹ thuật
        if self.config["enable_enhanced_features"]["technical_reversal_detection"]:
            # Kiểm tra đảo chiều ngược với xu hướng hiện tại
            reversal_direction = None
            if base_analysis["recommendation"] in ["strong_sell", "sell"]:
                # Đang giảm, tìm đảo chiều lên
                reversal_direction = "up"
            elif base_analysis["recommendation"] in ["strong_buy", "buy"]:
                # Đang tăng, tìm đảo chiều xuống
                reversal_direction = "down"
            elif base_analysis["recommendation"] == "neutral":
                # Neutral, kiểm tra cả hai chiều
                recent_change = base_analysis.get("price", {}).get("change_pct", 0)
                reversal_direction = "up" if recent_change < 0 else "down"
            
            if reversal_direction:
                is_reversal, reversal_details = self.reversal_detector.check_technical_reversal(
                    symbol, reversal_direction, timeframe, base_analysis["market_regime"]
                )
                
                enhanced_analysis["reversal_signals"] = {
                    "is_reversal": is_reversal,
                    "direction": reversal_direction,
                    "score": reversal_details.get("score", 0),
                    "signals": reversal_details.get("signals", []),
                    "threshold": reversal_details.get("threshold", 0),
                    "reason": reversal_details.get("reason", ""),
                    "details": reversal_details.get("details", {})
                }
                
                # Ghi đè khuyến nghị nếu được cấu hình và có tín hiệu đảo chiều mạnh
                if (is_reversal and 
                    self.config["reversal_consideration"]["enabled"] and 
                    self.config["reversal_consideration"]["override_market_direction"] and
                    reversal_details.get("score", 0) >= self.config["reversal_consideration"]["min_score"]):
                    
                    if reversal_direction == "up":
                        enhanced_analysis["recommendation"] = "buy"
                        enhanced_analysis["score"] = 65  # Điểm mặc định cho tín hiệu đảo chiều
                    else:  # reversal_direction == "down"
                        enhanced_analysis["recommendation"] = "sell"
                        enhanced_analysis["score"] = 35  # Điểm mặc định cho tín hiệu đảo chiều
                    
                    # Đánh dấu là khuyến nghị từ tín hiệu đảo chiều
                    enhanced_analysis["recommendation_source"] = "reversal"
        
        return enhanced_analysis
    
    def analyze_multiple_timeframes(self, symbol: str, timeframes: List[str] = None) -> Dict:
        """
        Phân tích một cặp tiền trên nhiều khung thời gian và tích hợp kết quả
        
        Args:
            symbol (str): Mã cặp tiền
            timeframes (List[str], optional): Danh sách khung thời gian
            
        Returns:
            Dict: Kết quả tích hợp
        """
        if not timeframes:
            timeframes = self.config["multi_timeframe_settings"]["timeframes"]
        
        logger.info(f"Phân tích {symbol} trên {len(timeframes)} khung thời gian: {', '.join(timeframes)}")
        
        try:
            # Phân tích trên từng khung thời gian
            timeframe_analyses = {}
            
            for tf in timeframes:
                analysis = self.analyze_symbol(symbol, tf)
                timeframe_analyses[tf] = analysis
            
            # Xác định chế độ thị trường (sử dụng khung thời gian chính)
            primary_tf = self.config["multi_timeframe_settings"]["primary_timeframe"]
            if primary_tf not in timeframe_analyses:
                primary_tf = timeframes[0]  # Sử dụng khung đầu tiên nếu không có khung chính
            
            market_regime = timeframe_analyses[primary_tf]["market_regime"]
            
            # Sử dụng conflict_resolver nếu được bật
            if self.config["enable_enhanced_features"]["multi_timeframe_conflict_resolution"]:
                resolution_method = self.config["multi_timeframe_settings"]["resolution_method"]
                integrated_result = self.conflict_resolver.resolve_conflicts(
                    timeframe_analyses, market_regime, resolution_method
                )
            else:
                # Sử dụng phương pháp tích hợp của hệ thống gốc
                from multi_timeframe_integration import MultiTimeframeIntegration
                integrator = MultiTimeframeIntegration()
                integrated_result = integrator.integrate_analyses(timeframe_analyses)
            
            # Bổ sung thông tin vào kết quả
            integrated_result["symbol"] = symbol
            integrated_result["timestamp"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            integrated_result["timeframes_analyzed"] = timeframes
            
            # Lấy thông tin giá từ khung thời gian chính
            if "price" in timeframe_analyses[primary_tf]:
                integrated_result["price"] = timeframe_analyses[primary_tf]["price"]
            
            logger.info(f"Hoàn thành phân tích đa khung {symbol}, khuyến nghị: {integrated_result.get('recommendation', 'neutral')}")
            
            return integrated_result
        
        except Exception as e:
            logger.error(f"Lỗi khi phân tích đa khung {symbol}: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Trả về phân tích trên khung thời gian mặc định nếu phân tích đa khung thất bại
            return self.analyze_symbol(symbol, self.config["multi_timeframe_settings"]["primary_timeframe"])
    
    def check_trading_conditions(self, symbol: str, direction: str = None, timeframe: str = None,
                             integrated_result: Dict = None) -> Dict:
        """
        Kiểm tra chi tiết các điều kiện giao dịch với logic nâng cao
        
        Args:
            symbol (str): Mã cặp tiền
            direction (str, optional): Hướng giao dịch ('long' hoặc 'short')
            timeframe (str, optional): Khung thời gian chính
            integrated_result (Dict, optional): Kết quả phân tích tích hợp
            
        Returns:
            Dict: Kết quả kiểm tra điều kiện giao dịch
        """
        try:
            # Xác định timeframe nếu không được cung cấp
            if not timeframe:
                timeframe = self.config["multi_timeframe_settings"]["primary_timeframe"]
            
            # Phân tích nếu chưa có kết quả tích hợp
            if not integrated_result:
                if self.config["enable_enhanced_features"]["multi_timeframe_conflict_resolution"]:
                    integrated_result = self.analyze_multiple_timeframes(symbol)
                else:
                    integrated_result = self.analyze_symbol(symbol, timeframe)
            
            # Lấy giá hiện tại
            current_price = 0
            if "price" in integrated_result and "current" in integrated_result["price"]:
                current_price = integrated_result["price"]["current"]
            else:
                ticker = self.api.get_symbol_ticker(symbol=symbol)
                current_price = float(ticker['price']) if ticker else 0
            
            # Xác định hướng giao dịch nếu không được cung cấp
            if not direction:
                recommendation = integrated_result.get("recommendation", "neutral")
                if recommendation in ["strong_buy", "buy"]:
                    direction = "long"
                elif recommendation in ["strong_sell", "sell"]:
                    direction = "short"
                else:
                    # Kiểm tra tín hiệu đảo chiều
                    if (self.config["enable_enhanced_features"]["technical_reversal_detection"] and
                        self.config["trading_conditions"]["allow_reversal_signals"]):
                        
                        is_up_reversal, _ = self.reversal_detector.check_technical_reversal(
                            symbol, "up", timeframe, integrated_result.get("market_regime", "ranging")
                        )
                        
                        is_down_reversal, _ = self.reversal_detector.check_technical_reversal(
                            symbol, "down", timeframe, integrated_result.get("market_regime", "ranging")
                        )
                        
                        if is_up_reversal:
                            direction = "long"
                        elif is_down_reversal:
                            direction = "short"
            
            # Nếu không xác định được hướng, không vào lệnh
            if not direction:
                return {
                    "should_trade": False,
                    "direction": None,
                    "current_price": current_price,
                    "reasons": ["Không xác định được hướng giao dịch"]
                }
            
            # Bắt đầu kiểm tra các điều kiện giao dịch
            reasons = []
            should_trade = True
            
            # Kiểm tra độ tin cậy của tín hiệu
            confidence = integrated_result.get("confidence", 1.0)
            min_confidence = self.config["trading_conditions"]["min_mtf_confidence"]
            
            if confidence < min_confidence:
                should_trade = False
                reasons.append(f"Độ tin cậy tín hiệu thấp ({confidence:.2f} < {min_confidence})")
            
            # Kiểm tra biến động
            if self.config["enable_enhanced_features"]["adaptive_volatility_threshold"]:
                volatility = integrated_result.get("volatility", 0)
                threshold = integrated_result.get("volatility_threshold", 
                                               self.volatility_analyzer.get_volatility_threshold(symbol))
                
                if volatility > threshold:
                    # Kiểm tra xem có phải tín hiệu đảo chiều không
                    is_reversal = False
                    if "reversal_signals" in integrated_result:
                        is_reversal = integrated_result["reversal_signals"].get("is_reversal", False)
                    
                    if (is_reversal and 
                        self.config["trading_conditions"]["allow_reversal_signals"] and
                        integrated_result["reversal_signals"].get("score", 0) >= self.config["reversal_consideration"]["min_score"]):
                        
                        reasons.append(f"Biến động cao ({volatility:.2f}% > {threshold:.2f}%) nhưng có tín hiệu đảo chiều mạnh")
                    else:
                        should_trade = False
                        reasons.append(f"Biến động quá cao ({volatility:.2f}% > {threshold:.2f}%)")
            
            # Kiểm tra thanh khoản
            if self.config["enable_enhanced_features"]["liquidity_analysis"]:
                if "liquidity" in integrated_result:
                    liquidity = integrated_result["liquidity"]
                    min_liquidity_score = self.config["trading_conditions"]["min_liquidity_score"]
                    
                    if liquidity["score"] < min_liquidity_score:
                        should_trade = False
                        reasons.append(f"Thanh khoản thấp (điểm: {liquidity['score']}/100 < {min_liquidity_score})")
                else:
                    # Phân tích thanh khoản nếu chưa có
                    liquidity_result = self.liquidity_analyzer.check_liquidity_conditions(symbol)
                    
                    if not liquidity_result.get("is_tradable", False):
                        should_trade = False
                        for reason in liquidity_result.get("reasons", []):
                            reasons.append(reason.get("reason", "Thanh khoản không đủ"))
            
            # Kiểm tra điểm vào/ra
            if self.config["enable_enhanced_features"]["enhanced_entry_exit"] and self.config["trading_conditions"]["require_entry_exit_points"]:
                entry_exit_key = "entry_exit_enhanced" if "entry_exit_enhanced" in integrated_result else "entry_exit_points"
                
                if entry_exit_key not in integrated_result:
                    # Tạo điểm vào/ra nếu chưa có
                    market_regime = integrated_result.get("market_regime", "ranging")
                    
                    entry_exit_result = self.entry_exit_generator.get_entry_exit_points(
                        symbol, direction, current_price, None, market_regime
                    )
                    
                    integrated_result[entry_exit_key] = entry_exit_result
                
                # Kiểm tra các điểm vào/ra
                if not integrated_result[entry_exit_key].get("entry_points"):
                    should_trade = False
                    reasons.append("Không tìm thấy điểm vào lệnh phù hợp")
                
                exit_points = integrated_result[entry_exit_key].get("exit_points", {})
                if not exit_points.get("stop_loss"):
                    should_trade = False
                    reasons.append("Không tìm thấy điểm stop loss phù hợp")
                
                if not exit_points.get("take_profit"):
                    should_trade = False
                    reasons.append("Không tìm thấy điểm take profit phù hợp")
                
                # Tính tỷ lệ risk/reward nếu có đủ thông tin
                if (integrated_result[entry_exit_key].get("entry_points") and 
                    exit_points.get("stop_loss") and exit_points.get("take_profit")):
                    
                    entry = integrated_result[entry_exit_key]["entry_points"][0]
                    sl = exit_points["stop_loss"][0]
                    tp = exit_points["take_profit"][0]
                    
                    if direction == "long":
                        risk = entry - sl
                        reward = tp - entry
                    else:  # direction == "short"
                        risk = sl - entry
                        reward = entry - tp
                    
                    if risk > 0:
                        risk_reward_ratio = reward / risk
                        min_rr_ratio = self.config["trading_conditions"]["min_risk_reward_ratio"]
                        
                        if risk_reward_ratio < min_rr_ratio:
                            should_trade = False
                            reasons.append(f"Tỷ lệ risk/reward không đủ hấp dẫn (1:{risk_reward_ratio:.2f} < 1:{min_rr_ratio})")
            
            # Tạo kết quả
            result = {
                "should_trade": should_trade,
                "direction": direction,
                "current_price": current_price,
                "market_regime": integrated_result.get("market_regime", "unknown"),
                "recommendation": integrated_result.get("recommendation", "neutral"),
                "score": integrated_result.get("score", 50),
                "confidence": integrated_result.get("confidence", 1.0),
                "reasons": reasons
            }
            
            # Thêm thông tin về điểm vào/ra nếu có
            if "entry_exit_enhanced" in integrated_result:
                result["entry_points"] = integrated_result["entry_exit_enhanced"].get("entry_points", [])
                result["stop_loss"] = integrated_result["entry_exit_enhanced"].get("exit_points", {}).get("stop_loss", [])
                result["take_profit"] = integrated_result["entry_exit_enhanced"].get("exit_points", {}).get("take_profit", [])
                result["entry_reasoning"] = integrated_result["entry_exit_enhanced"].get("reasoning", [])
            
            # Ghi log lý do nếu không vào lệnh
            if not should_trade:
                log_data = {
                    "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "direction": direction,
                    "price": current_price,
                    "reasons": reasons
                }
                
                self.base_system._log_no_trade_reason(symbol, direction, timeframe, log_data)
            
            logger.info(f"Đã kiểm tra điều kiện giao dịch cho {symbol} {timeframe} {direction}: {'Nên vào lệnh' if should_trade else 'Không nên vào lệnh'}")
            
            return result
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra điều kiện giao dịch: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                "should_trade": False,
                "direction": direction,
                "current_price": 0,
                "reasons": [f"Lỗi khi kiểm tra điều kiện giao dịch: {str(e)}"]
            }
    
    def create_trading_plan(self, symbols: List[str] = None) -> Dict:
        """
        Tạo kế hoạch giao dịch tự động với phân tích nâng cao
        
        Args:
            symbols (List[str], optional): Danh sách cặp tiền, nếu None sẽ sử dụng danh sách mặc định
            
        Returns:
            Dict: Kế hoạch giao dịch
        """
        try:
            # Nếu không có danh sách cặp tiền, sử dụng danh sách mặc định
            if not symbols:
                account_config = self.api.get_account_config()
                symbols = account_config.get('symbols', ['BTCUSDT', 'ETHUSDT'])
            
            logger.info(f"Tạo kế hoạch giao dịch nâng cao cho {len(symbols)} cặp tiền")
            
            # Phân tích tổng thể thị trường
            global_analysis = self.base_system.analyze_global_market()
            
            # Phân tích từng cặp tiền
            symbols_analysis = {}
            trading_opportunities = []
            
            for symbol in symbols:
                # Phân tích đa khung thời gian
                if self.config["enable_enhanced_features"]["multi_timeframe_conflict_resolution"]:
                    analysis = self.analyze_multiple_timeframes(symbol)
                else:
                    primary_tf = self.config["multi_timeframe_settings"]["primary_timeframe"]
                    analysis = self.analyze_symbol(symbol, primary_tf)
                
                symbols_analysis[symbol] = analysis
                
                # Xác định hướng
                direction = None
                if analysis.get("recommendation") in ["strong_buy", "buy"]:
                    direction = "long"
                elif analysis.get("recommendation") in ["strong_sell", "sell"]:
                    direction = "short"
                elif (self.config["enable_enhanced_features"]["technical_reversal_detection"] and
                     "reversal_signals" in analysis and
                     analysis["reversal_signals"].get("is_reversal", False)):
                    
                    if analysis["reversal_signals"]["direction"] == "up":
                        direction = "long"
                    else:
                        direction = "short"
                
                # Nếu có hướng, kiểm tra điều kiện giao dịch
                if direction:
                    conditions = self.check_trading_conditions(symbol, direction, None, analysis)
                    
                    if conditions["should_trade"]:
                        opportunity = {
                            "symbol": symbol,
                            "direction": direction,
                            "recommendation": analysis.get("recommendation", "neutral"),
                            "score": analysis.get("score", 50),
                            "confidence": analysis.get("confidence", 1.0),
                            "current_price": conditions["current_price"],
                            "entry_points": conditions.get("entry_points", []),
                            "stop_loss": conditions.get("stop_loss", []),
                            "take_profit": conditions.get("take_profit", []),
                            "market_regime": analysis.get("market_regime", "unknown"),
                            "reasoning": conditions.get("entry_reasoning", [])
                        }
                        
                        trading_opportunities.append(opportunity)
            
            # Tạo kế hoạch giao dịch
            trading_plan = {
                "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "global_market": global_analysis,
                "symbols_analysis": {
                    symbol: {
                        "recommendation": analysis["recommendation"],
                        "score": analysis["score"],
                        "market_regime": analysis["market_regime"],
                        "current_price": analysis.get("price", {}).get("current", 0)
                    } for symbol, analysis in symbols_analysis.items()
                },
                "trading_opportunities": trading_opportunities
            }
            
            logger.info(f"Đã tạo kế hoạch giao dịch nâng cao với {len(trading_opportunities)} cơ hội")
            
            # Lưu kế hoạch giao dịch
            if self.config["logging"]["save_enhanced_analysis"]:
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                plan_path = f"reports/enhanced_trading_plan_{timestamp}.json"
                
                with open(plan_path, 'w') as f:
                    json.dump(trading_plan, f, indent=4)
                
                logger.info(f"Đã lưu kế hoạch giao dịch nâng cao tại {plan_path}")
            
            return trading_plan
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo kế hoạch giao dịch nâng cao: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "error": str(e),
                "trading_opportunities": []
            }

def main():
    """Hàm chính để test MarketAnalysisSystemEnhanced"""
    
    try:
        # Khởi tạo hệ thống phân tích nâng cao
        enhanced_system = MarketAnalysisSystemEnhanced()
        
        # Danh sách cặp tiền để test
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        
        print("=== Test phân tích nâng cao ===")
        for symbol in symbols:
            # Phân tích trên khung thời gian chính
            primary_tf = enhanced_system.config["multi_timeframe_settings"]["primary_timeframe"]
            analysis = enhanced_system.analyze_symbol(symbol, primary_tf)
            
            print(f"\n{symbol} - Phân tích nâng cao:")
            print(f"- Khuyến nghị: {analysis['recommendation']}")
            print(f"- Điểm: {analysis['score']}")
            print(f"- Chế độ thị trường: {analysis['market_regime']}")
            
            if "volatility_threshold" in analysis:
                print(f"- Biến động: {analysis.get('volatility', 0):.2f}% (ngưỡng: {analysis['volatility_threshold']:.2f}%)")
            
            if "liquidity" in analysis:
                print(f"- Thanh khoản: {analysis['liquidity']['score']}/100 (tradable: {analysis['liquidity']['is_tradable']})")
            
            if "reversal_signals" in analysis and analysis["reversal_signals"]["is_reversal"]:
                print(f"- Tín hiệu đảo chiều: {analysis['reversal_signals']['direction']} (điểm: {analysis['reversal_signals']['score']:.2f})")
        
        print("\n=== Test phân tích đa khung thời gian ===")
        for symbol in symbols:
            # Phân tích đa khung thời gian
            mtf_result = enhanced_system.analyze_multiple_timeframes(symbol)
            
            print(f"\n{symbol} - Phân tích đa khung thời gian:")
            print(f"- Khuyến nghị: {mtf_result['recommendation']}")
            print(f"- Điểm: {mtf_result['score']}")
            print(f"- Phương pháp: {mtf_result.get('resolution_method', 'N/A')}")
            print(f"- Độ tin cậy: {mtf_result.get('confidence', 0):.2f}")
            
            if "conflicts_detected" in mtf_result:
                print(f"- Xung đột: {mtf_result['conflicts_detected']}")
                if mtf_result['conflicts_detected']:
                    print(f"  - Loại xung đột: {mtf_result.get('conflict_details', {}).get('conflict_type', 'N/A')}")
        
        print("\n=== Test kiểm tra điều kiện giao dịch ===")
        for symbol in symbols:
            # Phân tích đa khung thời gian
            mtf_result = enhanced_system.analyze_multiple_timeframes(symbol)
            
            # Xác định hướng
            direction = None
            if mtf_result["recommendation"] in ["strong_buy", "buy"]:
                direction = "long"
            elif mtf_result["recommendation"] in ["strong_sell", "sell"]:
                direction = "short"
            
            if direction:
                # Kiểm tra điều kiện giao dịch
                conditions = enhanced_system.check_trading_conditions(symbol, direction, None, mtf_result)
                
                print(f"\n{symbol} - Kiểm tra điều kiện giao dịch ({direction}):")
                print(f"- Nên vào lệnh: {conditions['should_trade']}")
                
                if not conditions['should_trade']:
                    print(f"- Lý do không vào lệnh:")
                    for reason in conditions['reasons']:
                        print(f"  - {reason}")
                else:
                    print(f"- Điểm vào: {conditions.get('entry_points', [])}")
                    print(f"- Stop loss: {conditions.get('stop_loss', [])}")
                    print(f"- Take profit: {conditions.get('take_profit', [])}")
            else:
                print(f"\n{symbol} - Không có hướng giao dịch rõ ràng")
        
        print("\n=== Test tạo kế hoạch giao dịch ===")
        trading_plan = enhanced_system.create_trading_plan(symbols)
        
        print(f"Cơ hội giao dịch: {len(trading_plan['trading_opportunities'])}")
        for opportunity in trading_plan['trading_opportunities']:
            print(f"\n{opportunity['symbol']} - {opportunity['direction'].upper()}:")
            print(f"- Khuyến nghị: {opportunity['recommendation']} (điểm: {opportunity['score']})")
            print(f"- Giá hiện tại: {opportunity['current_price']}")
            print(f"- Điểm vào: {opportunity.get('entry_points', [])}")
            print(f"- Stop loss: {opportunity.get('stop_loss', [])}")
            print(f"- Take profit: {opportunity.get('take_profit', [])}")
    
    except Exception as e:
        logger.error(f"Lỗi khi chạy test MarketAnalysisSystemEnhanced: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()