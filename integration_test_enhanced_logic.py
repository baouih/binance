#!/usr/bin/env python3
"""
Script kiểm thử tích hợp cho logic quyết định vào lệnh cải tiến

Script này kiểm thử việc tích hợp các module cải tiến vào hệ thống chính:
1. Ngưỡng biến động thông minh
2. Phân tích thanh khoản thị trường
3. Sinh điểm vào/ra lệnh nâng cao
4. Giải quyết xung đột đa khung thời gian
5. Phát hiện đảo chiều kỹ thuật
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Union

# Thêm đường dẫn gốc vào sys.path
sys.path.append('.')

# Import các module đã cải tiến
from adaptive_volatility_threshold import AdaptiveVolatilityThreshold
from liquidity_analyzer import LiquidityAnalyzer
from enhanced_entry_exit_generator import EnhancedEntryExitGenerator
from multi_timeframe_conflict_resolver import MultiTimeframeConflictResolver
from technical_reversal_detector import TechnicalReversalDetector

# Import các module hệ thống hiện có
from binance_api import BinanceAPI
from market_analysis_system import MarketAnalysisSystem
from multi_timeframe_integration import MultiTimeframeIntegration

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("integration_test_enhanced_logic")

class EnhancedTradingLogicTester:
    """
    Lớp kiểm thử tích hợp các cải tiến logic quyết định vào lệnh
    """
    
    def __init__(self):
        """Khởi tạo tester"""
        
        # Khởi tạo BinanceAPI
        self.api = BinanceAPI()
        
        # Khởi tạo các module cải tiến
        self.volatility_analyzer = AdaptiveVolatilityThreshold(self.api)
        self.liquidity_analyzer = LiquidityAnalyzer(self.api)
        self.entry_exit_generator = EnhancedEntryExitGenerator(self.api)
        self.conflict_resolver = MultiTimeframeConflictResolver()
        self.reversal_detector = TechnicalReversalDetector(self.api)
        
        # Khởi tạo các module hệ thống
        self.market_analyzer = MarketAnalysisSystem()
        self.timeframe_integrator = MultiTimeframeIntegration()
        
        # Đảm bảo thư mục kết quả tồn tại
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Tạo các thư mục cần thiết"""
        directories = [
            "test_results",
            "test_results/enhanced_logic",
            "test_results/original_logic",
            "test_charts"
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
    
    def test_adaptive_volatility(self, symbol: str) -> Dict:
        """
        Kiểm thử ngưỡng biến động thông minh
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            Dict: Kết quả kiểm thử
        """
        logger.info(f"Kiểm thử ngưỡng biến động thông minh cho {symbol}")
        
        try:
            # Lấy ngưỡng biến động mặc định
            default_threshold = self.volatility_analyzer.get_volatility_threshold(symbol)
            
            # Lấy dữ liệu giá
            df = self.api.get_klines_dataframe(symbol=symbol, interval="1h", limit=100)
            
            if df is None or df.empty:
                return {
                    "status": "error",
                    "message": f"Không thể lấy dữ liệu cho {symbol}",
                    "default_threshold": default_threshold,
                    "adaptive_threshold": None
                }
            
            # Tính biến động hiện tại
            current_volatility = 0
            if len(df) >= 20:
                high_max = df['high'].rolling(window=20).max().iloc[-1]
                low_min = df['low'].rolling(window=20).min().iloc[-1]
                close_prev = df['close'].iloc[-2]
                
                if close_prev > 0:
                    current_volatility = (high_max - low_min) / close_prev * 100
            
            # Cập nhật lịch sử biến động
            self.volatility_analyzer.update_volatility_history(symbol, current_volatility)
            
            # Tính ngưỡng thích ứng
            adaptive_threshold = self.volatility_analyzer._calculate_adaptive_threshold(symbol)
            
            return {
                "status": "success",
                "default_threshold": default_threshold,
                "adaptive_threshold": adaptive_threshold,
                "current_volatility": current_volatility,
                "is_high_volatility": current_volatility > adaptive_threshold if adaptive_threshold else current_volatility > default_threshold
            }
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm thử ngưỡng biến động thông minh: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def test_liquidity_analysis(self, symbol: str) -> Dict:
        """
        Kiểm thử phân tích thanh khoản
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            Dict: Kết quả kiểm thử
        """
        logger.info(f"Kiểm thử phân tích thanh khoản cho {symbol}")
        
        try:
            # Phân tích thanh khoản
            liquidity_result = self.liquidity_analyzer.check_liquidity_conditions(symbol)
            
            return {
                "status": "success",
                "liquidity_score": liquidity_result.get("score", 0),
                "volume_ratio": liquidity_result.get("volume_ratio", 0),
                "spread_pct": liquidity_result.get("spread_pct", 0),
                "depth_sum": liquidity_result.get("depth_sum", 0),
                "depth_ratio": liquidity_result.get("depth_ratio", 0),
                "is_tradable": liquidity_result.get("is_tradable", False),
                "reasons": liquidity_result.get("reasons", [])
            }
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm thử phân tích thanh khoản: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def test_enhanced_entry_exit(self, symbol: str, direction: str) -> Dict:
        """
        Kiểm thử sinh điểm vào/ra lệnh nâng cao
        
        Args:
            symbol (str): Mã cặp tiền
            direction (str): Hướng giao dịch ('long' hoặc 'short')
            
        Returns:
            Dict: Kết quả kiểm thử
        """
        logger.info(f"Kiểm thử sinh điểm vào/ra lệnh nâng cao cho {symbol} {direction}")
        
        try:
            # Lấy giá hiện tại
            ticker = self.api.get_symbol_ticker(symbol=symbol)
            current_price = float(ticker['price']) if ticker else 0
            
            if current_price == 0:
                return {
                    "status": "error",
                    "message": f"Không thể lấy giá hiện tại cho {symbol}"
                }
            
            # Lấy dữ liệu giá
            df = self.api.get_klines_dataframe(symbol=symbol, interval="1h", limit=100)
            
            # Phát hiện chế độ thị trường từ phân tích hiện có
            analysis = self.market_analyzer.analyze_symbol(symbol, "1h")
            market_regime = analysis.get("market_regime", "ranging")
            
            # Sinh điểm vào/ra lệnh
            entry_exit_result = self.entry_exit_generator.get_entry_exit_points(
                symbol, direction, current_price, df, market_regime
            )
            
            return {
                "status": "success",
                "current_price": current_price,
                "market_regime": market_regime,
                "entry_points": entry_exit_result.get("entry_points", []),
                "stop_loss": entry_exit_result.get("exit_points", {}).get("stop_loss", []),
                "take_profit": entry_exit_result.get("exit_points", {}).get("take_profit", []),
                "reasoning": entry_exit_result.get("reasoning", [])
            }
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm thử sinh điểm vào/ra lệnh: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def test_multi_timeframe_conflict_resolution(self, symbol: str) -> Dict:
        """
        Kiểm thử giải quyết xung đột đa khung thời gian
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            Dict: Kết quả kiểm thử
        """
        logger.info(f"Kiểm thử giải quyết xung đột đa khung thời gian cho {symbol}")
        
        try:
            # Phân tích trên nhiều khung thời gian
            timeframes = ["5m", "15m", "1h", "4h"]
            timeframe_analyses = {}
            
            for tf in timeframes:
                analysis = self.market_analyzer.analyze_symbol(symbol, tf)
                timeframe_analyses[tf] = analysis
            
            # Phát hiện chế độ thị trường từ phân tích hiện có
            market_regime = timeframe_analyses["1h"].get("market_regime", "ranging")
            
            # Giải quyết xung đột
            conflict_result = self.conflict_resolver.resolve_conflicts(timeframe_analyses, market_regime)
            
            # Kết hợp kết quả hệ thống hiện có để so sánh
            original_result = self.timeframe_integrator.integrate_analyses(timeframe_analyses)
            
            return {
                "status": "success",
                "market_regime": market_regime,
                "enhanced_recommendation": conflict_result.get("recommendation", "neutral"),
                "enhanced_score": conflict_result.get("score", 50),
                "enhanced_confidence": conflict_result.get("confidence", 0),
                "enhanced_method": conflict_result.get("resolution_method", ""),
                "has_conflict": conflict_result.get("conflicts_detected", False),
                "conflict_type": conflict_result.get("conflict_details", {}).get("conflict_type", ""),
                "conflict_severity": conflict_result.get("conflict_details", {}).get("conflict_severity", 0),
                "original_recommendation": original_result.get("recommendation", "neutral"),
                "original_score": original_result.get("score", 50),
                "timeframe_recommendations": {
                    tf: analysis.get("recommendation", "neutral") for tf, analysis in timeframe_analyses.items()
                }
            }
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm thử giải quyết xung đột đa khung thời gian: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def test_technical_reversal_detection(self, symbol: str) -> Dict:
        """
        Kiểm thử phát hiện đảo chiều kỹ thuật
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            Dict: Kết quả kiểm thử
        """
        logger.info(f"Kiểm thử phát hiện đảo chiều kỹ thuật cho {symbol}")
        
        try:
            # Lấy phân tích thị trường hiện tại
            analysis = self.market_analyzer.analyze_symbol(symbol, "1h")
            
            # Xác định hướng cần kiểm tra đảo chiều
            current_recommendation = analysis.get("recommendation", "neutral")
            
            if current_recommendation in ["strong_sell", "sell"]:
                # Đang giảm, tìm đảo chiều lên
                reversal_direction = "up"
            elif current_recommendation in ["strong_buy", "buy"]:
                # Đang tăng, tìm đảo chiều xuống
                reversal_direction = "down"
            else:
                # Neutral, kiểm tra cả hai hướng
                up_result, _ = self.reversal_detector.check_technical_reversal(symbol, "up", "1h")
                down_result, _ = self.reversal_detector.check_technical_reversal(symbol, "down", "1h")
                
                if up_result:
                    reversal_direction = "up"
                elif down_result:
                    reversal_direction = "down"
                else:
                    # Nếu không có đảo chiều nào, chọn chiều dựa trên phân tích biến động gần đây
                    df = self.api.get_klines_dataframe(symbol=symbol, interval="1h", limit=10)
                    if not df.empty:
                        recent_change = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
                        reversal_direction = "up" if recent_change < 0 else "down"
                    else:
                        reversal_direction = "up"  # Mặc định
            
            # Phát hiện đảo chiều
            is_reversal, reversal_details = self.reversal_detector.check_technical_reversal(
                symbol, reversal_direction, "1h", analysis.get("market_regime", "ranging")
            )
            
            return {
                "status": "success",
                "current_recommendation": current_recommendation,
                "reversal_direction": reversal_direction,
                "is_reversal": is_reversal,
                "reversal_score": reversal_details.get("score", 0),
                "reversal_signals": reversal_details.get("signals", []),
                "reversal_threshold": reversal_details.get("threshold", 0),
                "reason": reversal_details.get("reason", "")
            }
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm thử phát hiện đảo chiều kỹ thuật: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def test_enhanced_trading_decision(self, symbol: str) -> Dict:
        """
        Kiểm thử quyết định giao dịch tích hợp với các cải tiến
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            Dict: Kết quả kiểm thử
        """
        logger.info(f"Kiểm thử quyết định giao dịch nâng cao cho {symbol}")
        
        try:
            # Lấy giá hiện tại
            ticker = self.api.get_symbol_ticker(symbol=symbol)
            current_price = float(ticker['price']) if ticker else 0
            
            if current_price == 0:
                return {
                    "status": "error",
                    "message": f"Không thể lấy giá hiện tại cho {symbol}"
                }
            
            # 1. Phân tích trên nhiều khung thời gian
            timeframes = ["5m", "15m", "1h", "4h"]
            timeframe_analyses = {}
            
            for tf in timeframes:
                analysis = self.market_analyzer.analyze_symbol(symbol, tf)
                timeframe_analyses[tf] = analysis
            
            # 2. Xác định chế độ thị trường
            market_regime = timeframe_analyses["1h"].get("market_regime", "ranging")
            
            # 3. Giải quyết xung đột đa khung thời gian
            mtf_result = self.conflict_resolver.resolve_conflicts(timeframe_analyses, market_regime)
            recommendation = mtf_result.get("recommendation", "neutral")
            
            # 4. Xác định hướng giao dịch
            trade_direction = None
            if recommendation in ["strong_buy", "buy"]:
                trade_direction = "long"
            elif recommendation in ["strong_sell", "sell"]:
                trade_direction = "short"
            
            if trade_direction is None:
                # Nếu không có khuyến nghị rõ ràng, kiểm tra xem có tín hiệu đảo chiều không
                up_reversal, up_details = self.reversal_detector.check_technical_reversal(symbol, "up", "1h", market_regime)
                down_reversal, down_details = self.reversal_detector.check_technical_reversal(symbol, "down", "1h", market_regime)
                
                if up_reversal:
                    trade_direction = "long"
                    mtf_result["recommendation"] = "buy"
                    mtf_result["score"] = 65  # Điểm mặc định cho tín hiệu đảo chiều
                    mtf_result["confidence"] = up_details.get("score", 65) / 100
                elif down_reversal:
                    trade_direction = "short"
                    mtf_result["recommendation"] = "sell"
                    mtf_result["score"] = 35  # Điểm mặc định cho tín hiệu đảo chiều
                    mtf_result["confidence"] = down_details.get("score", 65) / 100
            
            # Nếu vẫn không có hướng giao dịch, không có giao dịch
            if trade_direction is None:
                return {
                    "status": "success",
                    "should_trade": False,
                    "current_price": current_price,
                    "market_regime": market_regime,
                    "mtf_recommendation": mtf_result.get("recommendation", "neutral"),
                    "mtf_score": mtf_result.get("score", 50),
                    "mtf_confidence": mtf_result.get("confidence", 0),
                    "reasons": ["Không có khuyến nghị giao dịch rõ ràng hoặc tín hiệu đảo chiều"]
                }
            
            # 5. Kiểm tra ngưỡng biến động
            volatility_result = self.test_adaptive_volatility(symbol)
            volatility_threshold = volatility_result.get("adaptive_threshold") or volatility_result.get("default_threshold", 5.0)
            current_volatility = volatility_result.get("current_volatility", 0)
            
            # 6. Kiểm tra thanh khoản
            liquidity_result = self.liquidity_analyzer.check_liquidity_conditions(symbol)
            
            # 7. Sinh điểm vào/ra lệnh
            entry_exit_result = self.entry_exit_generator.get_entry_exit_points(
                symbol, trade_direction, current_price, None, market_regime
            )
            
            # 8. Đưa ra quyết định giao dịch tổng hợp
            reasons = []
            should_trade = True
            
            # Kiểm tra độ tin cậy của tín hiệu
            if mtf_result.get("confidence", 1.0) < 0.6:
                should_trade = False
                reasons.append(f"Độ tin cậy tín hiệu thấp ({mtf_result.get('confidence', 0):.2f} < 0.6)")
            
            # Kiểm tra biến động
            if current_volatility > volatility_threshold:
                # Biến động cao, nhưng vẫn cho phép giao dịch nếu là tín hiệu đảo chiều
                if (trade_direction == "long" and up_reversal) or (trade_direction == "short" and down_reversal):
                    reasons.append(f"Biến động cao ({current_volatility:.2f}% > {volatility_threshold:.2f}%) nhưng có tín hiệu đảo chiều mạnh")
                else:
                    should_trade = False
                    reasons.append(f"Biến động quá cao ({current_volatility:.2f}% > {volatility_threshold:.2f}%)")
            
            # Kiểm tra thanh khoản
            if not liquidity_result.get("is_tradable", False):
                should_trade = False
                for reason in liquidity_result.get("reasons", []):
                    reasons.append(reason.get("reason", "Thanh khoản không đủ"))
            
            # Kiểm tra điểm vào/ra
            if not entry_exit_result.get("entry_points"):
                should_trade = False
                reasons.append("Không tìm thấy điểm vào lệnh phù hợp")
            
            if not entry_exit_result.get("exit_points", {}).get("stop_loss"):
                should_trade = False
                reasons.append("Không tìm thấy điểm stop loss phù hợp")
            
            if not entry_exit_result.get("exit_points", {}).get("take_profit"):
                should_trade = False
                reasons.append("Không tìm thấy điểm take profit phù hợp")
            
            # Tính tỷ lệ risk/reward
            risk_reward_ratio = None
            if (should_trade and 
                entry_exit_result.get("entry_points") and 
                entry_exit_result.get("exit_points", {}).get("stop_loss") and 
                entry_exit_result.get("exit_points", {}).get("take_profit")):
                
                entry = entry_exit_result["entry_points"][0]
                sl = entry_exit_result["exit_points"]["stop_loss"][0]
                tp = entry_exit_result["exit_points"]["take_profit"][0]
                
                if trade_direction == "long":
                    risk = entry - sl
                    reward = tp - entry
                else:  # trade_direction == "short"
                    risk = sl - entry
                    reward = entry - tp
                
                if risk > 0:
                    risk_reward_ratio = reward / risk
                    
                    # Kiểm tra tỷ lệ risk/reward
                    if risk_reward_ratio < 1.5:
                        should_trade = False
                        reasons.append(f"Tỷ lệ risk/reward không đủ hấp dẫn (1:{risk_reward_ratio:.2f} < 1:1.5)")
            
            return {
                "status": "success",
                "should_trade": should_trade,
                "current_price": current_price,
                "trade_direction": trade_direction,
                "market_regime": market_regime,
                "mtf_recommendation": mtf_result.get("recommendation", "neutral"),
                "mtf_score": mtf_result.get("score", 50),
                "mtf_confidence": mtf_result.get("confidence", 0),
                "volatility": current_volatility,
                "volatility_threshold": volatility_threshold,
                "liquidity_score": liquidity_result.get("score", 0),
                "entry_points": entry_exit_result.get("entry_points", []),
                "stop_loss": entry_exit_result.get("exit_points", {}).get("stop_loss", []),
                "take_profit": entry_exit_result.get("exit_points", {}).get("take_profit", []),
                "risk_reward_ratio": risk_reward_ratio,
                "reasons": reasons,
                "reasoning": entry_exit_result.get("reasoning", [])
            }
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm thử quyết định giao dịch nâng cao: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": str(e)
            }
    
    def run_full_test(self, symbols: List[str] = None) -> Dict:
        """
        Chạy tất cả các kiểm thử trên tất cả các cặp tiền
        
        Args:
            symbols (List[str], optional): Danh sách cặp tiền cần kiểm thử
            
        Returns:
            Dict: Kết quả kiểm thử
        """
        # Nếu không có danh sách cặp tiền, sử dụng danh sách mặc định
        if not symbols:
            symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]
        
        # Lưu kết quả kiểm thử
        results = {}
        
        for symbol in symbols:
            logger.info(f"Chạy kiểm thử đầy đủ cho {symbol}")
            
            symbol_results = {
                "adaptive_volatility": self.test_adaptive_volatility(symbol),
                "liquidity_analysis": self.test_liquidity_analysis(symbol),
                "enhanced_entry_exit_long": self.test_enhanced_entry_exit(symbol, "long"),
                "enhanced_entry_exit_short": self.test_enhanced_entry_exit(symbol, "short"),
                "multi_timeframe_conflict": self.test_multi_timeframe_conflict_resolution(symbol),
                "technical_reversal": self.test_technical_reversal_detection(symbol),
                "enhanced_trading_decision": self.test_enhanced_trading_decision(symbol)
            }
            
            results[symbol] = symbol_results
            
            # Lưu kết quả chi tiết
            self._save_test_results(symbol, symbol_results)
        
        # Tạo báo cáo tổng hợp
        summary = self._create_test_summary(results)
        
        # Lưu báo cáo tổng hợp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        summary_path = f"test_results/enhanced_logic/summary_{timestamp}.json"
        
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=4)
        
        logger.info(f"Đã lưu báo cáo tổng hợp tại {summary_path}")
        
        return summary
    
    def _save_test_results(self, symbol: str, results: Dict) -> None:
        """
        Lưu kết quả kiểm thử chi tiết
        
        Args:
            symbol (str): Mã cặp tiền
            results (Dict): Kết quả kiểm thử
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        result_path = f"test_results/enhanced_logic/{symbol}_{timestamp}.json"
        
        with open(result_path, 'w') as f:
            json.dump(results, f, indent=4)
        
        logger.info(f"Đã lưu kết quả kiểm thử cho {symbol} tại {result_path}")
    
    def _create_test_summary(self, results: Dict) -> Dict:
        """
        Tạo báo cáo tổng hợp từ kết quả kiểm thử
        
        Args:
            results (Dict): Kết quả kiểm thử
            
        Returns:
            Dict: Báo cáo tổng hợp
        """
        summary = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "total_symbols": len(results),
            "symbols_tested": list(results.keys()),
            "success_rate": 0,
            "volatility_analysis": {
                "avg_threshold": 0,
                "high_volatility_count": 0
            },
            "liquidity_analysis": {
                "avg_score": 0,
                "tradable_count": 0
            },
            "trading_decisions": {
                "long_count": 0,
                "short_count": 0,
                "no_trade_count": 0,
                "avg_confidence": 0,
                "top_reasons": {}
            },
            "detailed_results": {}
        }
        
        # Tính tỉ lệ thành công
        success_count = 0
        volatility_threshold_sum = 0
        volatility_high_count = 0
        liquidity_score_sum = 0
        liquidity_tradable_count = 0
        long_count = 0
        short_count = 0
        no_trade_count = 0
        confidence_sum = 0
        
        all_reasons = []
        
        for symbol, symbol_results in results.items():
            # Kiểm tra trạng thái của từng phần
            if (symbol_results["adaptive_volatility"].get("status") == "success" and
                symbol_results["liquidity_analysis"].get("status") == "success" and
                symbol_results["enhanced_entry_exit_long"].get("status") == "success" and
                symbol_results["enhanced_entry_exit_short"].get("status") == "success" and
                symbol_results["multi_timeframe_conflict"].get("status") == "success" and
                symbol_results["technical_reversal"].get("status") == "success" and
                symbol_results["enhanced_trading_decision"].get("status") == "success"):
                success_count += 1
            
            # Thống kê volatility
            if symbol_results["adaptive_volatility"].get("status") == "success":
                threshold = (symbol_results["adaptive_volatility"].get("adaptive_threshold") or 
                           symbol_results["adaptive_volatility"].get("default_threshold", 0))
                volatility_threshold_sum += threshold
                
                if symbol_results["adaptive_volatility"].get("is_high_volatility", False):
                    volatility_high_count += 1
            
            # Thống kê liquidity
            if symbol_results["liquidity_analysis"].get("status") == "success":
                liquidity_score_sum += symbol_results["liquidity_analysis"].get("liquidity_score", 0)
                
                if symbol_results["liquidity_analysis"].get("is_tradable", False):
                    liquidity_tradable_count += 1
            
            # Thống kê trading decisions
            if symbol_results["enhanced_trading_decision"].get("status") == "success":
                if symbol_results["enhanced_trading_decision"].get("should_trade", False):
                    if symbol_results["enhanced_trading_decision"].get("trade_direction") == "long":
                        long_count += 1
                    else:
                        short_count += 1
                    
                    confidence_sum += symbol_results["enhanced_trading_decision"].get("mtf_confidence", 0)
                else:
                    no_trade_count += 1
                
                # Tổng hợp reasons
                for reason in symbol_results["enhanced_trading_decision"].get("reasons", []):
                    all_reasons.append(reason)
            
            # Thêm tóm tắt cho từng symbol
            summary["detailed_results"][symbol] = {
                "volatility": symbol_results["adaptive_volatility"].get("current_volatility", 0),
                "volatility_threshold": (symbol_results["adaptive_volatility"].get("adaptive_threshold") or 
                                      symbol_results["adaptive_volatility"].get("default_threshold", 0)),
                "liquidity_score": symbol_results["liquidity_analysis"].get("liquidity_score", 0),
                "is_tradable": symbol_results["liquidity_analysis"].get("is_tradable", False),
                "recommendation": symbol_results["enhanced_trading_decision"].get("mtf_recommendation", "neutral"),
                "should_trade": symbol_results["enhanced_trading_decision"].get("should_trade", False),
                "trade_direction": symbol_results["enhanced_trading_decision"].get("trade_direction"),
                "reasons_count": len(symbol_results["enhanced_trading_decision"].get("reasons", []))
            }
        
        # Tính giá trị trung bình
        if len(results) > 0:
            summary["success_rate"] = success_count / len(results)
            summary["volatility_analysis"]["avg_threshold"] = volatility_threshold_sum / len(results)
            summary["volatility_analysis"]["high_volatility_count"] = volatility_high_count
            summary["liquidity_analysis"]["avg_score"] = liquidity_score_sum / len(results)
            summary["liquidity_analysis"]["tradable_count"] = liquidity_tradable_count
            summary["trading_decisions"]["long_count"] = long_count
            summary["trading_decisions"]["short_count"] = short_count
            summary["trading_decisions"]["no_trade_count"] = no_trade_count
            
            trading_count = long_count + short_count
            if trading_count > 0:
                summary["trading_decisions"]["avg_confidence"] = confidence_sum / trading_count
        
        # Tổng hợp lý do hàng đầu
        reason_counts = {}
        for reason in all_reasons:
            reason = reason.split("(")[0].strip()  # Lấy phần đầu của lý do, bỏ các chi tiết trong ngoặc
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        # Sắp xếp theo số lần xuất hiện
        top_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)
        summary["trading_decisions"]["top_reasons"] = {reason: count for reason, count in top_reasons[:5]}
        
        return summary

def parse_arguments():
    """Phân tích tham số dòng lệnh"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Kiểm thử tích hợp logic quyết định vào lệnh cải tiến')
    parser.add_argument('--symbols', type=str, nargs='+', default=None, help='Danh sách cặp tiền cần kiểm thử')
    
    return parser.parse_args()

def main():
    """Hàm chính"""
    args = parse_arguments()
    
    # Khởi tạo và chạy kiểm thử
    tester = EnhancedTradingLogicTester()
    results = tester.run_full_test(args.symbols)
    
    # In kết quả tóm tắt
    print("\n===== KẾT QUẢ KIỂM THỬ TÍCH HỢP =====")
    print(f"Số cặp tiền đã kiểm thử: {results['total_symbols']}")
    print(f"Tỉ lệ thành công: {results['success_rate']*100:.2f}%")
    
    print("\n----- Thống kê biến động -----")
    print(f"Ngưỡng biến động trung bình: {results['volatility_analysis']['avg_threshold']:.2f}%")
    print(f"Số cặp tiền có biến động cao: {results['volatility_analysis']['high_volatility_count']}")
    
    print("\n----- Thống kê thanh khoản -----")
    print(f"Điểm thanh khoản trung bình: {results['liquidity_analysis']['avg_score']:.2f}/100")
    print(f"Số cặp tiền có thanh khoản đủ tốt: {results['liquidity_analysis']['tradable_count']}")
    
    print("\n----- Thống kê quyết định giao dịch -----")
    print(f"Số lệnh LONG: {results['trading_decisions']['long_count']}")
    print(f"Số lệnh SHORT: {results['trading_decisions']['short_count']}")
    print(f"Số không vào lệnh: {results['trading_decisions']['no_trade_count']}")
    print(f"Độ tin cậy trung bình: {results['trading_decisions']['avg_confidence']*100:.2f}%")
    
    print("\n----- Top 5 lý do không vào lệnh -----")
    for reason, count in results['trading_decisions']['top_reasons'].items():
        print(f"- {reason}: {count} lần")

if __name__ == "__main__":
    main()