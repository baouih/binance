#!/usr/bin/env python3
"""
Script kiểm thử điều kiện vào lệnh với các tính năng cải tiến

Script này kiểm thử tính năng kiểm tra điều kiện vào lệnh với tất cả
các module cải tiến đã được tích hợp, và so sánh kết quả với hệ thống cũ.
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, List

# Import module cải tiến
from market_analysis_system_enhanced import MarketAnalysisSystemEnhanced
# Import module cũ để so sánh
from market_analysis_system import MarketAnalysisSystem
from binance_api import BinanceAPI

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_trading_conditions")

class TradingConditionsTester:
    """Lớp kiểm thử điều kiện vào lệnh"""
    
    def __init__(self):
        """Khởi tạo tester"""
        self.api = BinanceAPI()
        self.enhanced_system = MarketAnalysisSystemEnhanced()
        self.base_system = MarketAnalysisSystem()
        
        # Đảm bảo thư mục kết quả tồn tại
        os.makedirs("test_results", exist_ok=True)
    
    def test_single_symbol(self, symbol: str) -> Dict:
        """
        Kiểm thử điều kiện vào lệnh cho một cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            Dict: Kết quả kiểm thử
        """
        logger.info(f"Kiểm thử điều kiện vào lệnh cho {symbol}")
        
        try:
            # 1. Kiểm thử phân tích cơ bản (hệ thống cũ)
            base_start_time = time.time()
            base_analysis = self.base_system.analyze_symbol(symbol, "1h")
            base_direction = None
            
            if base_analysis["recommendation"] in ["strong_buy", "buy"]:
                base_direction = "long"
            elif base_analysis["recommendation"] in ["strong_sell", "sell"]:
                base_direction = "short"
            
            # Kiểm tra điều kiện giao dịch cơ bản
            base_conditions = None
            if base_direction:
                base_conditions = self.base_system.check_trading_conditions(symbol, base_direction)
            else:
                base_conditions = {
                    "should_trade": False,
                    "reasons": ["Không có khuyến nghị rõ ràng"]
                }
            base_end_time = time.time()
            base_execution_time = base_end_time - base_start_time
            
            # 2. Kiểm thử phân tích nâng cao (hệ thống mới)
            enhanced_start_time = time.time()
            enhanced_analysis = self.enhanced_system.analyze_multiple_timeframes(symbol)
            enhanced_direction = None
            
            if enhanced_analysis["recommendation"] in ["strong_buy", "buy"]:
                enhanced_direction = "long"
            elif enhanced_analysis["recommendation"] in ["strong_sell", "sell"]:
                enhanced_direction = "short"
            elif (enhanced_analysis.get("recommendation_source") == "reversal" and 
                 "reversal_signals" in enhanced_analysis and
                 enhanced_analysis["reversal_signals"]["is_reversal"]):
                
                if enhanced_analysis["reversal_signals"]["direction"] == "up":
                    enhanced_direction = "long"
                else:
                    enhanced_direction = "short"
            
            # Kiểm tra điều kiện giao dịch nâng cao
            enhanced_conditions = None
            if enhanced_direction:
                enhanced_conditions = self.enhanced_system.check_trading_conditions(
                    symbol, enhanced_direction, None, enhanced_analysis
                )
            else:
                enhanced_conditions = {
                    "should_trade": False,
                    "reasons": ["Không có khuyến nghị rõ ràng hoặc tín hiệu đảo chiều"]
                }
            enhanced_end_time = time.time()
            enhanced_execution_time = enhanced_end_time - enhanced_start_time
            
            # 3. So sánh kết quả
            has_differences = (
                base_direction != enhanced_direction or
                base_conditions["should_trade"] != enhanced_conditions["should_trade"] or
                len(base_conditions.get("reasons", [])) != len(enhanced_conditions.get("reasons", []))
            )
            
            differences = []
            if base_direction != enhanced_direction:
                differences.append(f"Khuyến nghị khác nhau: {base_direction} vs {enhanced_direction}")
            
            if base_conditions["should_trade"] != enhanced_conditions["should_trade"]:
                differences.append(f"Quyết định giao dịch khác nhau: {base_conditions['should_trade']} vs {enhanced_conditions['should_trade']}")
            
            # 4. Tạo báo cáo
            result = {
                "symbol": symbol,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "base_system": {
                    "analysis": {
                        "recommendation": base_analysis["recommendation"],
                        "score": base_analysis["score"],
                        "market_regime": base_analysis["market_regime"],
                        "current_price": base_analysis.get("price", {}).get("current", 0)
                    },
                    "direction": base_direction,
                    "should_trade": base_conditions["should_trade"],
                    "reasons": base_conditions.get("reasons", []),
                    "execution_time": base_execution_time
                },
                "enhanced_system": {
                    "analysis": {
                        "recommendation": enhanced_analysis["recommendation"],
                        "score": enhanced_analysis["score"],
                        "market_regime": enhanced_analysis["market_regime"],
                        "current_price": enhanced_analysis.get("price", {}).get("current", 0),
                        "confidence": enhanced_analysis.get("confidence", 0),
                        "resolution_method": enhanced_analysis.get("resolution_method", "unknown")
                    },
                    "direction": enhanced_direction,
                    "should_trade": enhanced_conditions["should_trade"],
                    "reasons": enhanced_conditions.get("reasons", []),
                    "execution_time": enhanced_execution_time,
                    "entry_points": enhanced_conditions.get("entry_points", []),
                    "stop_loss": enhanced_conditions.get("stop_loss", []),
                    "take_profit": enhanced_conditions.get("take_profit", [])
                },
                "comparison": {
                    "has_differences": has_differences,
                    "differences": differences,
                    "execution_time_ratio": enhanced_execution_time / base_execution_time if base_execution_time > 0 else 0
                }
            }
            
            # Lưu kết quả
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result_path = f"test_results/trading_conditions_{symbol}_{timestamp}.json"
            
            with open(result_path, 'w') as f:
                json.dump(result, f, indent=4)
            
            logger.info(f"Đã lưu kết quả kiểm thử của {symbol} tại {result_path}")
            
            return result
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm thử {symbol}: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                "symbol": symbol,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "error": str(e)
            }
    
    def test_multiple_symbols(self, symbols: List[str] = None) -> Dict:
        """
        Kiểm thử điều kiện vào lệnh cho nhiều cặp tiền
        
        Args:
            symbols (List[str], optional): Danh sách cặp tiền
            
        Returns:
            Dict: Kết quả kiểm thử
        """
        # Nếu không có danh sách cặp tiền, sử dụng danh sách mặc định
        if not symbols:
            account_config = self.api.get_account_config()
            symbols = account_config.get('symbols', ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'])
        
        logger.info(f"Kiểm thử điều kiện vào lệnh cho {len(symbols)} cặp tiền: {symbols}")
        
        # Kiểm thử từng cặp và ghi nhận kết quả
        results = {}
        for symbol in symbols:
            results[symbol] = self.test_single_symbol(symbol)
        
        # Tạo báo cáo tổng hợp
        total_symbols = len(results)
        different_count = sum(1 for result in results.values() if result.get("comparison", {}).get("has_differences", False))
        base_trade_count = sum(1 for result in results.values() if result.get("base_system", {}).get("should_trade", False))
        enhanced_trade_count = sum(1 for result in results.values() if result.get("enhanced_system", {}).get("should_trade", False))
        
        avg_execution_time_ratio = 0
        count = 0
        for result in results.values():
            ratio = result.get("comparison", {}).get("execution_time_ratio", 0)
            if ratio > 0:
                avg_execution_time_ratio += ratio
                count += 1
        
        if count > 0:
            avg_execution_time_ratio /= count
        
        summary = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "total_symbols": total_symbols,
            "different_results_count": different_count,
            "different_percentage": (different_count / total_symbols) * 100 if total_symbols > 0 else 0,
            "base_system_trade_signals": base_trade_count,
            "enhanced_system_trade_signals": enhanced_trade_count,
            "avg_execution_time_ratio": avg_execution_time_ratio,
            "symbols_tested": list(results.keys()),
            "symbols_with_differences": [
                symbol for symbol, result in results.items() 
                if result.get("comparison", {}).get("has_differences", False)
            ],
            "detailed_results": {
                symbol: {
                    "base_system": {
                        "direction": result.get("base_system", {}).get("direction"),
                        "should_trade": result.get("base_system", {}).get("should_trade", False)
                    },
                    "enhanced_system": {
                        "direction": result.get("enhanced_system", {}).get("direction"),
                        "should_trade": result.get("enhanced_system", {}).get("should_trade", False)
                    },
                    "has_differences": result.get("comparison", {}).get("has_differences", False)
                }
                for symbol, result in results.items()
            }
        }
        
        # Lưu báo cáo tổng hợp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        summary_path = f"test_results/trading_conditions_summary_{timestamp}.json"
        
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=4)
        
        logger.info(f"Đã lưu báo cáo tổng hợp tại {summary_path}")
        
        return summary

def parse_arguments():
    """Phân tích tham số dòng lệnh"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Kiểm thử điều kiện vào lệnh')
    parser.add_argument('--symbols', type=str, nargs='+', default=None, help='Danh sách cặp tiền cần kiểm thử')
    
    return parser.parse_args()

def main():
    """Hàm chính"""
    args = parse_arguments()
    
    # Khởi tạo tester
    tester = TradingConditionsTester()
    
    # Nếu chỉ có 1 cặp tiền, kiểm thử và in chi tiết
    if args.symbols and len(args.symbols) == 1:
        symbol = args.symbols[0]
        print(f"=== Kiểm thử chi tiết điều kiện vào lệnh cho {symbol} ===")
        
        result = tester.test_single_symbol(symbol)
        
        # In thông tin phân tích cơ bản
        print("\n--- Phân tích cơ bản (hệ thống cũ) ---")
        print(f"Khuyến nghị: {result['base_system']['analysis']['recommendation']}")
        print(f"Điểm: {result['base_system']['analysis']['score']}")
        print(f"Chế độ thị trường: {result['base_system']['analysis']['market_regime']}")
        print(f"Hướng giao dịch: {result['base_system']['direction']}")
        print(f"Nên vào lệnh: {result['base_system']['should_trade']}")
        if not result['base_system']['should_trade'] and result['base_system']['reasons']:
            print("Lý do không vào lệnh:")
            for reason in result['base_system']['reasons']:
                print(f"- {reason}")
        print(f"Thời gian thực thi: {result['base_system']['execution_time']:.2f}s")
        
        # In thông tin phân tích nâng cao
        print("\n--- Phân tích nâng cao (hệ thống mới) ---")
        print(f"Khuyến nghị: {result['enhanced_system']['analysis']['recommendation']}")
        print(f"Điểm: {result['enhanced_system']['analysis']['score']}")
        print(f"Chế độ thị trường: {result['enhanced_system']['analysis']['market_regime']}")
        print(f"Độ tin cậy: {result['enhanced_system']['analysis'].get('confidence', 0):.2f}")
        print(f"Phương pháp tích hợp: {result['enhanced_system']['analysis'].get('resolution_method', 'unknown')}")
        print(f"Hướng giao dịch: {result['enhanced_system']['direction']}")
        print(f"Nên vào lệnh: {result['enhanced_system']['should_trade']}")
        if not result['enhanced_system']['should_trade'] and result['enhanced_system']['reasons']:
            print("Lý do không vào lệnh:")
            for reason in result['enhanced_system']['reasons']:
                print(f"- {reason}")
        
        if result['enhanced_system'].get('entry_points'):
            print(f"Điểm vào: {result['enhanced_system']['entry_points']}")
        if result['enhanced_system'].get('stop_loss'):
            print(f"Stop loss: {result['enhanced_system']['stop_loss']}")
        if result['enhanced_system'].get('take_profit'):
            print(f"Take profit: {result['enhanced_system']['take_profit']}")
        
        print(f"Thời gian thực thi: {result['enhanced_system']['execution_time']:.2f}s")
        
        # In thông tin so sánh
        print("\n--- So sánh kết quả ---")
        print(f"Có sự khác biệt: {result['comparison']['has_differences']}")
        if result['comparison']['differences']:
            print("Chi tiết khác biệt:")
            for diff in result['comparison']['differences']:
                print(f"- {diff}")
        print(f"Tỷ lệ thời gian thực thi (enhanced/base): {result['comparison']['execution_time_ratio']:.2f}x")
    
    else:
        # Kiểm thử nhiều cặp tiền
        summary = tester.test_multiple_symbols(args.symbols)
        
        print("\n=== BÁO CÁO TỔNG HỢP ===")
        print(f"Tổng số cặp tiền: {summary['total_symbols']}")
        print(f"Số cặp có kết quả khác nhau: {summary['different_results_count']} ({summary['different_percentage']:.2f}%)")
        print(f"Số tín hiệu vào lệnh (hệ thống cũ): {summary['base_system_trade_signals']}")
        print(f"Số tín hiệu vào lệnh (hệ thống mới): {summary['enhanced_system_trade_signals']}")
        print(f"Tỷ lệ thời gian thực thi trung bình: {summary['avg_execution_time_ratio']:.2f}x")
        
        if summary['symbols_with_differences']:
            print("\nCác cặp tiền có kết quả khác nhau:")
            for symbol in summary['symbols_with_differences']:
                base_dir = summary['detailed_results'][symbol]['base_system']['direction']
                base_trade = summary['detailed_results'][symbol]['base_system']['should_trade']
                enh_dir = summary['detailed_results'][symbol]['enhanced_system']['direction']
                enh_trade = summary['detailed_results'][symbol]['enhanced_system']['should_trade']
                
                print(f"- {symbol}: {base_dir}/{enh_dir}, {base_trade}/{enh_trade}")

if __name__ == "__main__":
    main()