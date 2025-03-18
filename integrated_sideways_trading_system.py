#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hệ thống giao dịch tích hợp cho thị trường đi ngang

Script này kết hợp tất cả các module đã phát triển để tạo một hệ thống giao dịch hoàn chỉnh
có khả năng thích ứng với các điều kiện thị trường khác nhau, đặc biệt là thị trường đi ngang.
"""

import os
import logging
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union, Any
import argparse


def json_serialize_pandas(obj: Any) -> Any:
    """
    Hàm helper để chuyển đổi các đối tượng pandas (như Timestamp) thành định dạng có thể JSON serialize
    
    Args:
        obj (Any): Đối tượng cần chuyển đổi
        
    Returns:
        Any: Đối tượng đã được chuyển đổi
    """
    if isinstance(obj, pd.Timestamp):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj):
        return None
    else:
        return obj


def convert_timestamps_in_dict(data: Dict) -> Dict:
    """
    Chuyển đổi tất cả giá trị Timestamp trong một dictionary
    
    Args:
        data (Dict): Dictionary cần chuyển đổi
        
    Returns:
        Dict: Dictionary đã được chuyển đổi
    """
    if not isinstance(data, dict):
        return data
        
    result = {}
    
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = convert_timestamps_in_dict(value)
        elif isinstance(value, list):
            result[key] = [convert_timestamps_in_dict(item) if isinstance(item, dict) else json_serialize_pandas(item) for item in value]
        else:
            result[key] = json_serialize_pandas(value)
            
    return result

# Import các module đã phát triển
from sideways_market_optimizer import SidewaysMarketOptimizer
from rsi_divergence_detector import RSIDivergenceDetector

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/integrated_system.log')
    ]
)

logger = logging.getLogger('integrated_system')

class IntegratedSidewaysTrader:
    """
    Lớp triển khai hệ thống giao dịch tích hợp
    """
    
    def __init__(self, config_path: str = 'configs/sideways_config.json'):
        """
        Khởi tạo hệ thống với cấu hình
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
        """
        # Tạo thư mục đầu ra
        os.makedirs('reports', exist_ok=True)
        os.makedirs('charts', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        # Tải cấu hình
        self.config = self._load_config(config_path)
        
        # Khởi tạo các module
        self.sideways_optimizer = SidewaysMarketOptimizer(config_path)
        
        logger.info("Đã khởi tạo Integrated Sideways Trader")
    
    def _load_config(self, config_path: str) -> Dict:
        """
        Tải cấu hình từ file JSON
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
            
        Returns:
            Dict: Cấu hình đã tải
        """
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
            else:
                logger.error(f"Không tìm thấy file cấu hình: {config_path}")
                return {}
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
            return {}
    
    def load_data(self, symbol: str, timeframe: str = '1d', period: str = '3mo') -> pd.DataFrame:
        """
        Tải dữ liệu thị trường
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            timeframe (str): Khung thời gian
            period (str): Khoảng thời gian
            
        Returns:
            pd.DataFrame: DataFrame với dữ liệu OHLC
        """
        try:
            import yfinance as yf
            
            logger.info(f"Đang tải dữ liệu {symbol} ({timeframe}, {period})")
            df = yf.download(symbol, period=period, interval=timeframe)
            
            # Xử lý MultiIndex DataFrame từ yfinance
            if isinstance(df.columns, pd.MultiIndex):
                logger.info("Dữ liệu có cấu trúc MultiIndex, đang xử lý...")
                # Lấy cấp đầu tiên của MultiIndex (tên cột)
                df.columns = [col[0].lower() for col in df.columns]
            else:
                # Đổi tên cột nếu không phải MultiIndex
                df.columns = [c.lower() if isinstance(c, str) else str(c).lower() for c in df.columns]
            
            # Kiểm tra xem có đủ các cột cần thiết không
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                logger.warning(f"Thiếu các cột dữ liệu: {missing_columns}")
                # In các cột hiện có để debug
                logger.info(f"Các cột hiện có: {df.columns.tolist()}")
                
                # Chuyển đổi các tên cột từ DataFrame.columns thành list strings để dễ debug
                column_list = [str(col) for col in df.columns]
                logger.info(f"Danh sách cột (dạng string): {column_list}")
            
            logger.info(f"Đã tải {len(df)} dòng dữ liệu cho {symbol}")
            return df
        
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu: {str(e)}")
            return pd.DataFrame()
    
    def analyze_market(self, symbol: str, timeframe: str = '1d', period: str = '3mo') -> Dict:
        """
        Phân tích thị trường và tạo báo cáo
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            timeframe (str): Khung thời gian
            period (str): Khoảng thời gian
            
        Returns:
            Dict: Kết quả phân tích
        """
        # Tải dữ liệu
        df = self.load_data(symbol, timeframe, period)
        
        if df.empty:
            logger.error(f"Không thể phân tích do thiếu dữ liệu")
            return {}
        
        # Phân tích thị trường với divergence
        market_analysis = self.sideways_optimizer.analyze_market_with_divergence(df, symbol)
        
        # Tạo báo cáo và lưu
        report_path = os.path.join(
            'reports',
            f'market_analysis_{symbol}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )
        
        # Chuyển đổi tất cả Timestamp trong kết quả phân tích trước khi lưu JSON
        serializable_analysis = convert_timestamps_in_dict(market_analysis)
        
        with open(report_path, 'w') as f:
            json.dump(serializable_analysis, f, indent=4)
        
        logger.info(f"Đã lưu báo cáo phân tích thị trường tại {report_path}")
        
        return market_analysis
    
    def get_trading_signals(self, symbol: str, timeframe: str = '1d', period: str = '3mo') -> Dict:
        """
        Lấy tín hiệu giao dịch từ phân tích thị trường
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            timeframe (str): Khung thời gian
            period (str): Khoảng thời gian
            
        Returns:
            Dict: Tín hiệu giao dịch
        """
        try:
            logger.info(f"Bắt đầu lấy tín hiệu giao dịch cho {symbol}")
            
            # Phân tích thị trường
            analysis = self.analyze_market(symbol, timeframe, period)
            
            if not analysis:
                logger.warning(f"Không có dữ liệu phân tích cho {symbol}")
                return {"signal": "neutral", "confidence": 0}
            
            # Mặc định là tín hiệu trung tính
            signal = "neutral"
            confidence = 0
            reason = "Không có tín hiệu rõ ràng"
            
            try:
                # Xác định tín hiệu từ phân tích
                sideways = analysis.get('is_sideways_market', False)
                
                if 'divergence' in analysis:
                    divergence_signal = analysis['divergence'].get('signal', 'neutral')
                    divergence_confidence = analysis['divergence'].get('signal_confidence', 0)
                else:
                    logger.warning("Không tìm thấy thông tin 'divergence' trong kết quả phân tích")
                    divergence_signal = 'neutral'
                    divergence_confidence = 0
                
                if 'strategy' in analysis:
                    breakout_prediction = analysis['strategy'].get('breakout_prediction', 'unknown')
                else:
                    logger.warning("Không tìm thấy thông tin 'strategy' trong kết quả phân tích")
                    breakout_prediction = 'unknown'
                
                # Ưu tiên tín hiệu divergence trong thị trường đi ngang
                if sideways and divergence_confidence > 0.6:
                    signal = divergence_signal
                    confidence = divergence_confidence
                    reason = "RSI Divergence có độ tin cậy cao trong thị trường đi ngang"
                
                # Trong thị trường đi ngang nhưng không có divergence mạnh, sử dụng dự đoán breakout
                elif sideways and breakout_prediction != "unknown":
                    signal = "buy" if breakout_prediction == "up" else "sell"
                    confidence = 0.5  # Độ tin cậy trung bình
                    reason = f"Dự đoán breakout hướng {breakout_prediction} trong thị trường đi ngang"
                
                # Trong tình huống khác, dựa vào tín hiệu mean reversion
                elif sideways:
                    # Lấy giá trị %B (vị trí trong Bollinger Bands)
                    if 'price_data' in analysis and 'pct_b' in analysis['price_data']:
                        pct_b = analysis['price_data']['pct_b']
                        
                        if pct_b > 0.8:
                            signal = "sell"
                            confidence = 0.6
                            reason = "Giá ở cận trên Bollinger Bands trong thị trường đi ngang (mean reversion)"
                        elif pct_b < 0.2:
                            signal = "buy"
                            confidence = 0.6
                            reason = "Giá ở cận dưới Bollinger Bands trong thị trường đi ngang (mean reversion)"
                        else:
                            reason = "Giá trong vùng trung tính của Bollinger Bands"
                    else:
                        reason = "Không đủ dữ liệu cho tín hiệu mean reversion"
                
                # Trường hợp còn lại
                else:
                    reason = "Không có tín hiệu rõ ràng trong thị trường trend"
                
            except KeyError as ke:
                logger.error(f"Thiếu khóa trong dữ liệu phân tích: {str(ke)}")
                logger.debug(f"Dữ liệu phân tích: {analysis.keys()}")
            
            # Đảm bảo tất cả các khóa bắt buộc có trong kết quả phân tích
            result = {
                "symbol": symbol,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "signal": signal,
                "confidence": confidence,
                "reason": reason,
                "is_sideways": analysis.get('is_sideways_market', False),
                "sideways_score": analysis.get('sideways_score', 0),
            }
            
            # Thêm các trường không bắt buộc nếu có
            if 'position_sizing' in analysis and 'adjusted' in analysis['position_sizing']:
                result["position_size"] = analysis['position_sizing']['adjusted']
            else:
                result["position_size"] = 1.0
                
            if 'strategy' in analysis:
                result["use_mean_reversion"] = analysis['strategy'].get('use_mean_reversion', False)
                result["tp_sl_ratio"] = analysis['strategy'].get('tp_sl_ratio', 3.0)
            else:
                result["use_mean_reversion"] = False
                result["tp_sl_ratio"] = 3.0
            
            logger.info(f"Đã tạo tín hiệu giao dịch: {signal} (Độ tin cậy: {confidence:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy tín hiệu giao dịch: {str(e)}")
            return {"signal": "neutral", "confidence": 0, "reason": f"Lỗi: {str(e)}"}
    
    def get_trade_parameters(self, symbol: str, timeframe: str = '1d', period: str = '3mo') -> Dict:
        """
        Lấy thông số giao dịch chi tiết cho một lệnh
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            timeframe (str): Khung thời gian
            period (str): Khoảng thời gian
            
        Returns:
            Dict: Thông số giao dịch
        """
        try:
            logger.info(f"Bắt đầu lấy thông số giao dịch cho {symbol}")
            
            # Phân tích thị trường
            analysis = self.analyze_market(symbol, timeframe, period)
            
            if not analysis:
                logger.warning(f"Không có dữ liệu phân tích cho {symbol}")
                return {
                    "signal": "neutral",
                    "message": "Không có dữ liệu phân tích"
                }
            
            # Lấy tín hiệu
            signal_data = self.get_trading_signals(symbol, timeframe, period)
            
            # Nếu không có tín hiệu, không cần trả về thông số
            if signal_data['signal'] == 'neutral' or signal_data['confidence'] < 0.5:
                return {
                    "signal": "neutral",
                    "message": "Không có tín hiệu giao dịch đủ mạnh"
                }
            
            # Xác định giá hiện tại và chỉ báo
            if 'price_data' not in analysis:
                logger.error("Thiếu dữ liệu giá trong phân tích")
                return {
                    "signal": "neutral",
                    "message": "Thiếu dữ liệu giá trong phân tích"
                }
                
            # Lấy giá hiện tại an toàn
            current_price = analysis['price_data'].get('current_price', 0)
            if current_price == 0:
                logger.error("Giá hiện tại không hợp lệ")
                return {
                    "signal": "neutral",
                    "message": "Giá hiện tại không hợp lệ"
                }
            
            # Xác định TP/SL
            tp_price = 0
            sl_price = 0
            tp_pct = 0
            sl_pct = 0
            
            if 'price_targets' in analysis:
                # Lấy giá trị từ price_targets nếu có
                tp_price = analysis['price_targets'].get('tp_price', 0)
                sl_price = analysis['price_targets'].get('sl_price', 0)
                tp_pct = analysis['price_targets'].get('tp_distance_pct', 0)
                sl_pct = analysis['price_targets'].get('sl_distance_pct', 0)
            
            # Nếu không có mục tiêu cụ thể hoặc không hợp lệ, tính toán lại
            if tp_price == 0 or sl_price == 0:
                logger.info("Tính toán lại TP/SL dựa trên ATR và tỷ lệ")
                
                # Lấy tỷ lệ và ATR
                tp_sl_ratio = 3.0
                atr = 0
                
                if 'strategy' in analysis:
                    tp_sl_ratio = analysis['strategy'].get('tp_sl_ratio', 3.0)
                
                if 'price_data' in analysis:
                    atr = analysis['price_data'].get('atr_20d', 0)
                
                # Nếu không có ATR, sử dụng 2% giá hiện tại
                if atr == 0:
                    atr = current_price * 0.02
                
                # Với tín hiệu mua
                if signal_data['signal'] == 'buy':
                    sl_pct = (1.2 * atr / current_price) * 100
                    tp_pct = sl_pct * tp_sl_ratio
                    sl_price = current_price * (1 - sl_pct/100)
                    tp_price = current_price * (1 + tp_pct/100)
                # Với tín hiệu bán
                else:
                    sl_pct = (1.2 * atr / current_price) * 100
                    tp_pct = sl_pct * tp_sl_ratio
                    sl_price = current_price * (1 + sl_pct/100)
                    tp_price = current_price * (1 - tp_pct/100)
            
            # Tính kích thước vị thế
            position_size = 1.0
            if 'position_sizing' in analysis:
                position_size = analysis['position_sizing'].get('adjusted', 1.0)
            
            # Tính risk/reward ratio
            risk_reward_ratio = tp_pct / sl_pct if sl_pct > 0 else 0
            
            # Tạo thông số giao dịch
            trade_params = {
                "symbol": symbol,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "signal": signal_data['signal'],
                "confidence": signal_data['confidence'],
                "reason": signal_data['reason'],
                "entry_price": current_price,
                "take_profit": tp_price,
                "stop_loss": sl_price,
                "tp_distance_pct": tp_pct,
                "sl_distance_pct": sl_pct,
                "position_size": position_size,
                "risk_reward_ratio": risk_reward_ratio,
                "is_sideways_market": analysis.get('is_sideways_market', False),
                "notes": "Tỷ lệ TP/SL"
            }
            
            # Thêm chiến lược nếu có
            if 'strategy' in analysis:
                trade_params["use_mean_reversion"] = analysis['strategy'].get('use_mean_reversion', False)
                tp_sl_ratio = analysis['strategy'].get('tp_sl_ratio', 3.0)
                trade_params["notes"] = f"Tỷ lệ TP/SL: {tp_sl_ratio:.1f}:1"
            
            logger.info(f"Đã tạo thông số giao dịch cho {symbol}")
            return trade_params
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông số giao dịch: {str(e)}")
            return {
                "signal": "neutral", 
                "message": f"Lỗi: {str(e)}"
            }

def main():
    """
    Hàm main cho script
    """
    parser = argparse.ArgumentParser(description='Integrated Sideways Trading System')
    parser.add_argument('--symbol', type=str, default='BTC-USD', help='Symbol to analyze')
    parser.add_argument('--timeframe', type=str, default='1d', help='Timeframe (e.g., 1d, 4h, 1h)')
    parser.add_argument('--period', type=str, default='3mo', help='Period (e.g., 1mo, 3mo, 6mo)')
    parser.add_argument('--mode', type=str, default='analyze', 
                       choices=['analyze', 'signal', 'parameters'],
                       help='Mode (analyze, signal, parameters)')
    
    args = parser.parse_args()
    
    # Khởi tạo hệ thống
    trader = IntegratedSidewaysTrader()
    
    # Chọn chế độ
    if args.mode == 'analyze':
        # Phân tích đầy đủ
        analysis = trader.analyze_market(args.symbol, args.timeframe, args.period)
        
        # In kết quả
        print("\n=== Phân Tích Thị Trường ===")
        print(f"Symbol: {args.symbol}")
        print(f"Thị trường đi ngang: {analysis['is_sideways_market']} (Score: {analysis['sideways_score']:.2f})")
        
        if analysis['is_sideways_market']:
            print("\n-- Phát hiện Divergence --")
            print(f"Bullish: {analysis['divergence']['bullish']['detected']} (Conf: {analysis['divergence']['bullish']['confidence']:.2f})")
            print(f"Bearish: {analysis['divergence']['bearish']['detected']} (Conf: {analysis['divergence']['bearish']['confidence']:.2f})")
            print(f"Tín hiệu: {analysis['divergence']['signal']} (Conf: {analysis['divergence']['signal_confidence']:.2f})")
            
            print("\n-- Chiến lược --")
            print(f"Kích thước vị thế: {analysis['position_sizing']['adjusted']:.2f}x (Giảm {analysis['position_sizing']['reduction_pct']:.1f}%)")
            print(f"Chiến lược: {'Mean Reversion' if analysis['strategy']['use_mean_reversion'] else 'Trend Following'}")
            print(f"Dự đoán breakout: {analysis['strategy']['breakout_prediction']}")
            print(f"Tỷ lệ TP/SL: {analysis['strategy']['tp_sl_ratio']:.1f}:1")
            
            if 'price_targets' in analysis:
                print("\n-- Mục tiêu giá --")
                print(f"Take Profit: ${analysis['price_targets']['tp_price']:.0f} (+{analysis['price_targets']['tp_distance_pct']:.1f}%)")
                print(f"Stop Loss: ${analysis['price_targets']['sl_price']:.0f} (-{analysis['price_targets']['sl_distance_pct']:.1f}%)")
        
    elif args.mode == 'signal':
        # Lấy tín hiệu giao dịch
        signal = trader.get_trading_signals(args.symbol, args.timeframe, args.period)
        
        # In kết quả
        print("\n=== Tín Hiệu Giao Dịch ===")
        print(f"Symbol: {args.symbol}")
        print(f"Tín hiệu: {signal['signal']} (Độ tin cậy: {signal['confidence']:.2f})")
        print(f"Lý do: {signal['reason']}")
        print(f"Thị trường đi ngang: {signal['is_sideways']} (Score: {signal['sideways_score']:.2f})")
        print(f"Kích thước vị thế đề xuất: {signal['position_size']:.2f}x")
        
    elif args.mode == 'parameters':
        # Lấy thông số giao dịch chi tiết
        params = trader.get_trade_parameters(args.symbol, args.timeframe, args.period)
        
        # In kết quả
        if params.get('signal') == 'neutral':
            print(f"\n=== Không Có Tín Hiệu Giao Dịch ===")
            print(f"Symbol: {args.symbol}")
            print(f"Thông báo: {params.get('message', 'Không có tín hiệu giao dịch')}")
        else:
            print(f"\n=== Thông Số Giao Dịch ===")
            print(f"Symbol: {args.symbol}")
            print(f"Tín hiệu: {params['signal']} (Độ tin cậy: {params['confidence']:.2f})")
            print(f"Lý do: {params['reason']}")
            print(f"Giá vào lệnh: ${params['entry_price']:.2f}")
            print(f"Take Profit: ${params['take_profit']:.2f} ({'+' if params['signal'] == 'buy' else '-'}{params['tp_distance_pct']:.1f}%)")
            print(f"Stop Loss: ${params['stop_loss']:.2f} ({'-' if params['signal'] == 'buy' else '+'}{params['sl_distance_pct']:.1f}%)")
            print(f"Risk/Reward Ratio: 1:{params['risk_reward_ratio']:.1f}")
            print(f"Kích thước vị thế đề xuất: {params['position_size']:.2f}x")
            print(f"Ghi chú: {params['notes']}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        print(f"Lỗi: {str(e)}")