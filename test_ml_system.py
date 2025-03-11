#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test ML System - Kiểm thử hệ thống ML cho giao dịch tiền điện tử
"""

import os
import json
import logging
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Dict, List, Any, Optional, Union

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_ml_system')

def parse_args():
    """
    Phân tích đối số dòng lệnh
    """
    parser = argparse.ArgumentParser(description='Kiểm thử hệ thống ML')
    
    # Tham số bắt buộc
    parser.add_argument('--mode', type=str, required=True, 
                      choices=['signals', 'backtest', 'train', 'optimize'],
                      help='Chế độ kiểm thử')
    
    # Tham số dữ liệu
    parser.add_argument('--symbol', type=str, default='BTCUSDT',
                      help='Mã tiền')
    parser.add_argument('--interval', type=str, default='1h',
                      help='Khung thời gian')
    parser.add_argument('--limit', type=int, default=500,
                      help='Số lượng nến')
    
    # Tham số output
    parser.add_argument('--output', type=str, default='ml_test_results',
                      help='Thư mục đầu ra')
    parser.add_argument('--plot', action='store_true',
                      help='Vẽ biểu đồ')
    
    # Tham số mô hình
    parser.add_argument('--model', type=str, default=None,
                      help='Đường dẫn mô hình')
    
    return parser.parse_args()

def load_data(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    """
    Tải dữ liệu
    """
    from data_processor import DataProcessor
    
    # Khởi tạo DataProcessor
    processor = DataProcessor(api=None)
    
    # Lấy dữ liệu lịch sử
    df = processor.get_historical_data(
        symbol=symbol,
        interval=interval,
        limit=limit
    )
    
    # Thêm chỉ báo kỹ thuật
    df = processor.add_technical_indicators(df)
    
    logger.info(f"Đã tải {len(df)} dòng dữ liệu cho {symbol} {interval}")
    return df

def test_market_regime_detector(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Kiểm thử Market Regime Detector
    """
    from market_regime_detector import MarketRegimeDetector
    
    # Khởi tạo detector
    detector = MarketRegimeDetector(
        window_size=20,
        ema_fast=5,
        ema_slow=20,
        rsi_window=14,
        rsi_thresholds=(30, 70),
        volatility_window=14
    )
    
    # Phát hiện chế độ thị trường
    result = detector.detect_regime_changes(df)
    
    # Lấy chế độ hiện tại
    current_regime = detector.get_current_regime(df)
    
    logger.info(f"Chế độ thị trường hiện tại: {current_regime}")
    logger.info(f"Phát hiện {len(result['changes'])} thay đổi chế độ thị trường")
    
    return result

def test_fibonacci_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Kiểm thử Fibonacci Analysis
    """
    from fibonacci_helper import FibonacciAnalyzer
    
    # Khởi tạo analyzer
    analyzer = FibonacciAnalyzer()
    
    # Tính toán các mức Fibonacci
    levels = analyzer.calculate_fibonacci_levels(df)
    
    # Tạo tín hiệu giao dịch
    signals = analyzer.generate_trading_signals(df, levels)
    
    logger.info(f"Tín hiệu Fibonacci: {signals['signal']} (độ mạnh: {signals['strength']:.2f})")
    
    # Vẽ biểu đồ
    analyzer.plot_fibonacci_levels(
        df,
        levels=levels,
        symbol=df.index.name or 'CRYPTO',
        output_file=os.path.join('ml_test_results', f"{df.index.name or 'CRYPTO'}_fibonacci.png")
    )
    
    return signals

def test_enhanced_regime_detector(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Kiểm thử Enhanced Market Regime Detector
    """
    try:
        from enhanced_market_regime_detector import EnhancedMarketRegimeDetector, MarketRegimeType
        
        # Khởi tạo detector nâng cao
        detector = EnhancedMarketRegimeDetector(
            method='ensemble',
            lookback_period=20,
            regime_change_threshold=0.6,
            use_volatility_scaling=True
        )
        
        # Chuẩn bị đặc trưng
        features_df = detector.prepare_features(df)
        
        # Phân tích chế độ thị trường hiện tại
        current_regime = detector.analyze_current_market(features_df)
        
        # Đảm bảo probabilities là một dict chuẩn (nếu có)
        if 'probabilities' in current_regime:
            # Nếu là một pandas Series hoặc một object không phải dict
            if not isinstance(current_regime['probabilities'], dict):
                # Chuyển đổi thành dict
                try:
                    probabilities = current_regime['probabilities']
                    if hasattr(probabilities, 'to_dict'):
                        # Nếu là pandas Series
                        current_regime['probabilities'] = probabilities.to_dict()
                    else:
                        # Khác, chỉ lưu giá trị chế độ hiện tại
                        current_regime['probabilities'] = {str(current_regime['regime']): 1.0}
                except:
                    # Gán giá trị mặc định an toàn
                    current_regime['probabilities'] = {"neutral": 1.0}
        else:
            # Nếu không có xác suất, gán xác suất 100% cho chế độ hiện tại
            current_regime['probabilities'] = {str(current_regime.get('regime', 'neutral')): 1.0}
        
        logger.info(f"Chế độ thị trường nâng cao hiện tại: {current_regime['regime']}")
        logger.info(f"Xác suất các chế độ: {current_regime['probabilities']}")
        
        return current_regime
    except Exception as e:
        logger.error(f"Lỗi khi kiểm thử Enhanced Market Regime Detector: {str(e)}")
        return {"regime": "neutral", "probabilities": {"neutral": 1.0}}

def test_feature_fusion_pipeline(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Kiểm thử Feature Fusion Pipeline
    """
    try:
        from feature_fusion_pipeline import FeatureFusionPipeline
        
        # Khởi tạo pipeline
        pipeline = FeatureFusionPipeline(
            use_pca=True,
            pca_components=10,
            feature_selection='mutual_info',
            n_features_to_select=20
        )
        
        # Chuẩn bị đặc trưng
        features = pipeline.prepare_data(df)
        
        # Phân tích đặc trưng
        feature_importance = pipeline.analyze_feature_importance(features)
        
        # Chọn đặc trưng hàng đầu
        top_features = feature_importance[:5]
        
        logger.info(f"5 đặc trưng hàng đầu: {top_features}")
        
        return {
            'features': features,
            'feature_importance': feature_importance
        }
    except Exception as e:
        logger.error(f"Lỗi khi kiểm thử Feature Fusion Pipeline: {str(e)}")
        return {}

def test_reinforcement_agent(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Kiểm thử Reinforcement Agent
    """
    try:
        from reinforcement_agent import ReinforcementTrader
        
        # Khởi tạo agent
        agent = ReinforcementTrader(
            state_size=10,
            action_size=3,
            learning_rate=0.001,
            gamma=0.95,
            epsilon=0.5
        )
        
        # Chuẩn bị đặc trưng
        features = df[['close', 'volume', 'rsi_14', 'macd', 'bb_width']].dropna()
        
        # Thực hiện giao dịch kiểm thử
        results = agent.backtest(
            df=features,
            initial_balance=1000,
            position_size=0.1,
            max_positions=1
        )
        
        logger.info(f"Kết quả kiểm thử Reinforcement Agent:")
        logger.info(f"Số lượng giao dịch: {results['n_trades']}")
        logger.info(f"Tỷ lệ thắng: {results['win_rate']:.2f}%")
        logger.info(f"Lợi nhuận: {results['profit']:.2f}")
        
        return results
    except Exception as e:
        logger.error(f"Lỗi khi kiểm thử Reinforcement Agent: {str(e)}")
        return {}

def test_multi_task_model(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Kiểm thử Multi-Task Model
    """
    try:
        from multi_task_model import MultiTaskModel
        
        # Khởi tạo mô hình
        model = MultiTaskModel(
            input_dim=10,
            shared_layers=[64, 32],
            task_specific_layers=[16],
            tasks=['price_movement', 'volatility', 'regime']
        )
        
        # Chuẩn bị đặc trưng
        features = ['close', 'open', 'high', 'low', 'volume', 
                    'rsi_14', 'macd', 'bb_width', 'ema_12', 'ema_26']
        
        X = df[features].dropna().values
        
        # Dự đoán
        predictions = model.predict_dummy(X)
        
        logger.info(f"Dự đoán Multi-Task Model:")
        
        for task, pred in predictions.items():
            logger.info(f"{task}: {pred}")
        
        return predictions
    except Exception as e:
        logger.error(f"Lỗi khi kiểm thử Multi-Task Model: {str(e)}")
        return {}

def plot_results(df: pd.DataFrame, results: Dict[str, Any], output_dir: str):
    """
    Vẽ biểu đồ kết quả
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Vẽ biểu đồ giá và chế độ thị trường
    try:
        plt.figure(figsize=(12, 8))
        
        # Subplot 1: Giá
        plt.subplot(3, 1, 1)
        plt.plot(df.index, df['close'], label='Close Price')
        plt.title('Price')
        plt.grid(True)
        plt.legend()
        
        # Subplot 2: RSI
        plt.subplot(3, 1, 2)
        plt.plot(df.index, df['rsi_14'], label='RSI')
        plt.axhline(y=70, color='r', linestyle='--')
        plt.axhline(y=30, color='g', linestyle='--')
        plt.title('RSI')
        plt.grid(True)
        plt.legend()
        
        # Subplot 3: MACD
        plt.subplot(3, 1, 3)
        plt.plot(df.index, df['macd'], label='MACD')
        plt.plot(df.index, df['macd_signal'], label='Signal')
        plt.bar(df.index, df['macd_hist'], alpha=0.5, label='Histogram')
        plt.title('MACD')
        plt.grid(True)
        plt.legend()
        
        # Định dạng trục x
        plt.gcf().autofmt_xdate()
        
        # Lưu biểu đồ
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'price_indicators.png'), dpi=300)
        plt.close()
        
        logger.info(f"Đã lưu biểu đồ tại: {os.path.join(output_dir, 'price_indicators.png')}")
    
    except Exception as e:
        logger.error(f"Lỗi khi vẽ biểu đồ: {str(e)}")

def main():
    """
    Hàm chính
    """
    # Phân tích đối số
    args = parse_args()
    
    # Tạo thư mục đầu ra
    os.makedirs(args.output, exist_ok=True)
    
    # Tải dữ liệu
    df = load_data(args.symbol, args.interval, args.limit)
    
    # Thực hiện kiểm thử theo chế độ
    if args.mode == 'signals':
        # Kiểm thử các bộ phát hiện tín hiệu
        logger.info("Kiểm thử Market Regime Detector")
        regime_results = test_market_regime_detector(df)
        
        logger.info("Kiểm thử Fibonacci Analysis")
        fib_results = test_fibonacci_analysis(df)
        
        logger.info("Kiểm thử Enhanced Market Regime Detector")
        enhanced_regime_results = test_enhanced_regime_detector(df)
        
        # Tổng hợp kết quả - Chuyển đổi các giá trị không tương thích với JSON
        # Xử lý regime_results
        for key in regime_results['changes']:
            if not isinstance(key, (str, int, float, bool)) and key is not None:
                # Chuyển đổi timestamp thành chuỗi
                changes = regime_results['changes']
                new_changes = {str(k): v for k, v in changes.items()}
                regime_results['changes'] = new_changes
                break
        
        results = {
            'market_regime': regime_results,
            'fibonacci': fib_results,
            'enhanced_regime': enhanced_regime_results
        }
        
    elif args.mode == 'backtest':
        # Kiểm thử các mô hình ML trong backtest
        logger.info("Kiểm thử Feature Fusion Pipeline")
        fusion_results = test_feature_fusion_pipeline(df)
        
        logger.info("Kiểm thử Reinforcement Agent")
        rl_results = test_reinforcement_agent(df)
        
        # Tổng hợp kết quả
        results = {
            'feature_fusion': fusion_results,
            'reinforcement': rl_results
        }
        
    elif args.mode == 'train':
        # Kiểm thử huấn luyện mô hình
        logger.info("Kiểm thử Multi-Task Model")
        multi_task_results = test_multi_task_model(df)
        
        # Tổng hợp kết quả
        results = {
            'multi_task': multi_task_results
        }
        
    elif args.mode == 'optimize':
        # Kiểm thử tối ưu hóa
        logger.info("Chế độ optimize chưa được triển khai")
        results = {}
    
    else:
        logger.error(f"Chế độ không hợp lệ: {args.mode}")
        return
    
    # Lưu kết quả
    result_path = os.path.join(args.output, f"{args.symbol}_{args.interval}_{args.mode}_results.json")
    
    try:
        with open(result_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"Đã lưu kết quả tại: {result_path}")
    except Exception as e:
        logger.error(f"Lỗi khi lưu kết quả: {str(e)}")
    
    # Vẽ biểu đồ nếu cần
    if args.plot:
        plot_results(df, results, args.output)

if __name__ == "__main__":
    main()