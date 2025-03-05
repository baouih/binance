#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script cập nhật dữ liệu phân tích thị trường tự động

Script này tự động cập nhật dữ liệu phân tích thị trường cho tất cả các cặp giao dịch
đã cấu hình trong account_config.json. Được thiết kế để chạy định kỳ thông qua cron hoặc
được gọi từ các script khác.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("market_updater.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("market_updater")

# Import các module cần thiết
try:
    from binance_api import BinanceAPI
    from app.data_processor import DataProcessor
    from multi_timeframe_analyzer import MultiTimeframeAnalyzer
    from composite_indicator import CompositeIndicator
    from liquidity_analyzer import LiquidityAnalyzer
    from market_regime_detector import MarketRegimeDetector
except ImportError as e:
    logger.error(f"Lỗi import module: {e}")
    logger.error("Đảm bảo đang chạy từ thư mục gốc của dự án")
    sys.exit(1)

class MarketDataUpdater:
    """Lớp tự động cập nhật dữ liệu phân tích thị trường"""
    
    def __init__(self, account_config_path: str = 'account_config.json'):
        """
        Khởi tạo bộ cập nhật dữ liệu thị trường
        
        Args:
            account_config_path (str): Đường dẫn đến file cấu hình tài khoản
        """
        self.account_config_path = account_config_path
        self.account_config = self._load_account_config()
        
        # Lấy danh sách cặp giao dịch từ cấu hình
        self.symbols = self.account_config.get('symbols', ['BTCUSDT', 'ETHUSDT'])
        self.timeframes = self.account_config.get('timeframes', ['1h', '4h'])
        
        # Khởi tạo các thành phần
        self.binance_api = None
        self.data_processor = None
        self.mtf_analyzer = None
        self.composite_indicator = None
        self.liquidity_analyzer = None
        
        # Kết nối API
        self._connect_api()
        
    def _load_account_config(self) -> Dict:
        """
        Tải cấu hình tài khoản
        
        Returns:
            Dict: Cấu hình tài khoản
        """
        try:
            with open(self.account_config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình tài khoản: {e}")
            return {
                "symbols": ["BTCUSDT", "ETHUSDT"],
                "timeframes": ["1h", "4h"],
                "api_mode": "testnet"
            }
    
    def _connect_api(self):
        """Kết nối với Binance API và khởi tạo các thành phần"""
        try:
            # Lấy thông tin API từ cấu hình
            api_key = self.account_config.get('api_key', '')
            api_secret = self.account_config.get('api_secret', '')
            testnet = self.account_config.get('api_mode', 'testnet') == 'testnet'
            
            # Khởi tạo BinanceAPI
            self.binance_api = BinanceAPI(api_key=api_key, api_secret=api_secret, testnet=testnet)
            logger.info(f"Đã kết nối tới Binance API ({testnet and 'testnet' or 'mainnet'})")
            
            # Khởi tạo các thành phần phân tích
            self.data_processor = DataProcessor(binance_api=self.binance_api)  # Truyền BinanceAPI vào
            self.mtf_analyzer = MultiTimeframeAnalyzer(
                binance_api=self.binance_api,
                data_processor=self.data_processor,
                timeframes=self.timeframes
            )
            self.composite_indicator = CompositeIndicator(
                indicators=['rsi', 'macd', 'ema_cross', 'bbands', 'volume_trend'],
                dynamic_weights=True
            )
            self.liquidity_analyzer = LiquidityAnalyzer(binance_api=self.binance_api)
            
            logger.info("Đã khởi tạo các thành phần phân tích thị trường")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi kết nối API: {e}")
            return False
    
    def update_market_analysis(self, symbol: str, timeframe: str = '1h') -> bool:
        """
        Cập nhật phân tích thị trường cho một cặp giao dịch
        
        Args:
            symbol (str): Mã cặp giao dịch
            timeframe (str): Khung thời gian chính
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không
        """
        try:
            logger.info(f"Đang cập nhật phân tích thị trường cho {symbol} ({timeframe})")
            
            # Lấy giá hiện tại
            ticker = self.binance_api.get_symbol_ticker(symbol)
            current_price = float(ticker.get('price', 0))
            
            if current_price == 0:
                logger.error(f"Lỗi lấy giá {symbol}")
                return False
            
            logger.info(f"Giá hiện tại {symbol}: {current_price}")
            
            # Phân tích đa khung thời gian
            mtf_result = self.mtf_analyzer.consolidate_signals(symbol, lookback_days=7)
            
            # Lấy dữ liệu lịch sử
            df = self.data_processor.get_historical_data(symbol, timeframe, lookback_days=30)
            
            # Kiểm tra nếu df là None hoặc là list rỗng hoặc DataFrame rỗng
            if df is None or (hasattr(df, 'empty') and df.empty) or (isinstance(df, list) and len(df) == 0):
                logger.error(f"Không thể lấy dữ liệu lịch sử cho {symbol}")
                return False
            
            # Phân tích chỉ báo tổng hợp
            ci_result = self.composite_indicator.calculate_composite_score(df)
            
            # Phân tích thanh khoản
            liq_result = self.liquidity_analyzer.analyze_orderbook(symbol)
            
            # Phát hiện chế độ thị trường
            market_regime = "ranging"  # Mặc định
            try:
                mrd = MarketRegimeDetector()
                market_regime = mrd.detect_regime(df)
                regime_desc = mrd.get_regime_description(market_regime)
            except:
                regime_desc = {
                    "en": "Ranging market - price moving sideways within a defined range.",
                    "vi": "Thị trường đi ngang - giá dao động trong một khoảng hẹp xác định."
                }
            
            # Tạo khuyến nghị tổng hợp
            recommendation = self.composite_indicator.get_trading_recommendation(df)
            
            # Tạo điểm vào lệnh
            entry_points = self.mtf_analyzer.get_optimal_entry_points(symbol, lookback_days=30)
            
            # Tạo kết quả phân tích
            analysis = {
                "symbol": symbol,
                "primary_timeframe": timeframe,
                "analysis_time": datetime.now().isoformat(),
                "current_price": current_price,
                "signals": {
                    "mtf": mtf_result.get('signal', 0) if mtf_result else 0,
                    "ci": ci_result.get('signal', 0) if ci_result else 0
                },
                "market_regime": {
                    "regime": market_regime,
                    "description": regime_desc
                },
                "multi_timeframe": mtf_result or {},
                "composite_indicator": ci_result or {},
                "liquidity_analysis": liq_result or {},
                "entry_points": entry_points.get('entry_points', []) if entry_points else [],
                "summary": self._generate_summary(
                    symbol, current_price, market_regime, 
                    mtf_result, ci_result, liq_result, recommendation
                )
            }
            
            # Lưu kết quả
            self._save_analysis(symbol, analysis)
            
            # Lưu khuyến nghị
            if recommendation:
                self._save_recommendation(symbol, recommendation)
            
            logger.info(f"Đã cập nhật phân tích thị trường cho {symbol}")
            return True
        
        except Exception as e:
            logger.error(f"Lỗi khi phân tích {symbol}: {e}")
            return False
    
    def _generate_summary(self, symbol, price, regime, mtf, ci, liq, recommendation) -> str:
        """Tạo tóm tắt phân tích thị trường"""
        try:
            summary = f"Thị trường đang ở giai đoạn {regime}. "
            
            # Tín hiệu tổng hợp
            signal = "TRUNG LẬP"
            confidence = 0
            
            if recommendation:
                signal = recommendation.get('action', 'NEUTRAL')
                confidence = recommendation.get('confidence', 0) * 100
            elif mtf and 'signal_description' in mtf:
                signal = mtf.get('signal_description', 'TRUNG LẬP')
                confidence = mtf.get('confidence', 0)
            
            summary += f"Tín hiệu {signal} với độ tin cậy {confidence:.1f}%. "
            
            # Thông tin thanh khoản
            pressure = "trung tính"
            if liq and 'market_pressure' in liq:
                pressure = "mua" if liq.get('market_pressure') == 'buy' else "bán"
                bid_ask_ratio = liq.get('bid_ask_ratio', 1.0)
                summary += f"Áp lực {pressure} {pressure == 'mua' and 'mạnh' or 'yếu'} (tỷ lệ bid/ask: {bid_ask_ratio:.2f}). "
            
            # Thông tin biến động
            volatility = 0
            if mtf and 'volatility' in mtf:
                volatility = mtf.get('volatility', 0)
            
            if volatility > 0:
                vol_level = "cao" if volatility > 1.5 else "trung bình" if volatility > 0.8 else "thấp"
                summary += f"Biến động {vol_level} ({volatility:.2f}%). "
            
            # Đề xuất
            if recommendation and 'action' in recommendation:
                action = recommendation.get('action', 'NEUTRAL')
                details = recommendation.get('action_details', '')
                
                if "BUY" in action or "MUA" in action:
                    if regime == 'trending' and pressure == 'mua':
                        summary += f"Đề xuất MUA khi giá điều chỉnh."
                    elif regime == 'ranging':
                        summary += f"Đề xuất MUA khi giá chạm vùng hỗ trợ."
                    else:
                        summary += f"Đề xuất {action}."
                elif "SELL" in action or "BÁN" in action:
                    if regime == 'trending' and pressure == 'bán':
                        summary += f"Đề xuất BÁN khi có dấu hiệu đảo chiều."
                    elif regime == 'ranging':
                        summary += f"Đề xuất BÁN khi giá phục hồi lên cao hơn."
                    else:
                        summary += f"Đề xuất {action}."
                else:
                    summary += f"Đề xuất theo dõi thêm."
            
            return summary
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo tóm tắt: {e}")
            return f"Phân tích thị trường cho {symbol} lúc {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"
    
    def _save_analysis(self, symbol: str, analysis: Dict) -> bool:
        """
        Lưu kết quả phân tích thị trường
        
        Args:
            symbol (str): Mã cặp giao dịch
            analysis (Dict): Kết quả phân tích
            
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        try:
            # Tạo tên file dựa trên symbol
            filename = f"market_analysis_{symbol.lower()}.json"
            
            # Lưu cả vào file chung (backward compatibility)
            if symbol == "BTCUSDT":
                with open('market_analysis.json', 'w') as f:
                    json.dump(analysis, f, indent=2)
                logger.info(f"Đã lưu phân tích {symbol} vào market_analysis.json")
            
            # Lưu vào file riêng theo symbol
            with open(filename, 'w') as f:
                json.dump(analysis, f, indent=2)
            logger.info(f"Đã lưu phân tích {symbol} vào {filename}")
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu phân tích {symbol}: {e}")
            return False
    
    def _save_recommendation(self, symbol: str, recommendation: Dict) -> bool:
        """
        Lưu khuyến nghị giao dịch
        
        Args:
            symbol (str): Mã cặp giao dịch
            recommendation (Dict): Khuyến nghị giao dịch
            
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        try:
            # Lưu vào file khuyến nghị riêng
            filename = f"recommendation_{symbol.lower()}.json"
            with open(filename, 'w') as f:
                json.dump(recommendation, f, indent=2)
            
            # Lưu vào composite_recommendation.json (backward compatibility)
            if symbol == "BTCUSDT":
                with open('composite_recommendation.json', 'w') as f:
                    json.dump(recommendation, f, indent=2)
            
            # Cập nhật khuyến nghị tổng hợp
            self._update_combined_recommendations(symbol, recommendation)
            
            logger.info(f"Đã lưu khuyến nghị {symbol} vào {filename}")
            return True
        
        except Exception as e:
            logger.error(f"Lỗi khi lưu khuyến nghị {symbol}: {e}")
            return False
    
    def _update_combined_recommendations(self, symbol: str, recommendation: Dict) -> bool:
        """
        Cập nhật file khuyến nghị tổng hợp
        
        Args:
            symbol (str): Mã cặp giao dịch
            recommendation (Dict): Khuyến nghị giao dịch
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không
        """
        try:
            filename = "all_recommendations.json"
            all_recommendations = {}
            
            # Tải file khuyến nghị nếu đã tồn tại
            if os.path.exists(filename):
                try:
                    with open(filename, 'r') as f:
                        all_recommendations = json.load(f)
                except:
                    all_recommendations = {}
            
            # Cập nhật khuyến nghị cho symbol hiện tại
            all_recommendations[symbol] = {
                "signal": recommendation.get('signal', 0),
                "signal_text": recommendation.get('signal_text', 'NEUTRAL'),
                "confidence": recommendation.get('confidence', 0),
                "price": recommendation.get('price', 0),
                "action": recommendation.get('action', 'NEUTRAL'),
                "take_profit": recommendation.get('take_profit', 0),
                "stop_loss": recommendation.get('stop_loss', 0),
                "timestamp": datetime.now().isoformat()
            }
            
            # Lưu file
            with open(filename, 'w') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "recommendations": all_recommendations
                }, f, indent=2)
            
            return True
        
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật khuyến nghị tổng hợp: {e}")
            return False
    
    def update_all_symbols(self, primary_timeframe: str = '1h') -> Dict[str, bool]:
        """
        Cập nhật phân tích thị trường cho tất cả các cặp giao dịch
        
        Args:
            primary_timeframe (str): Khung thời gian chính
            
        Returns:
            Dict[str, bool]: Kết quả cập nhật (symbol -> thành công/thất bại)
        """
        results = {}
        
        logger.info(f"Bắt đầu cập nhật phân tích thị trường cho {len(self.symbols)} cặp giao dịch")
        
        for symbol in self.symbols:
            start_time = time.time()
            success = self.update_market_analysis(symbol, primary_timeframe)
            
            results[symbol] = success
            duration = time.time() - start_time
            
            logger.info(f"Cập nhật {symbol}: {'Thành công' if success else 'Thất bại'} ({duration:.2f}s)")
            
            # Tạm dừng giữa các yêu cầu để tránh bị rate limit
            time.sleep(1)
        
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"Hoàn thành cập nhật: {success_count}/{len(self.symbols)} thành công")
        
        return results

def main():
    """Hàm chính"""
    try:
        logger.info("Bắt đầu cập nhật dữ liệu thị trường")
        
        updater = MarketDataUpdater()
        results = updater.update_all_symbols(primary_timeframe='1h')
        
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"Tóm tắt: Cập nhật {success_count}/{len(results)} cặp giao dịch thành công")
        
        # Lưu kết quả
        with open('market_updater_results.json', 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "results": {k: "success" if v else "failed" for k, v in results.items()},
                "success_count": success_count,
                "total_count": len(results)
            }, f, indent=2)
        
        logger.info("Hoàn thành cập nhật dữ liệu thị trường")
        return 0
    
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật dữ liệu thị trường: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())