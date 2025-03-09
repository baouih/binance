#!/usr/bin/env python3
"""
Tệp test cho Advanced ML Strategy
Sử dụng để kiểm tra giá trị trước khi tích hợp vào trading_bot_run.py
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_advanced_ml')

# Import các module cần thiết
try:
    from app.binance_api import BinanceAPI
    from app.data_processor import DataProcessor
    from app.market_regime_detector import MarketRegimeDetector
    from app.advanced_ml_optimizer import AdvancedMLOptimizer
    from app.advanced_ml_strategy import AdvancedMLStrategy
    from app.strategy_factory import StrategyFactory
except ImportError as e:
    logger.error(f"Lỗi khi import modules: {str(e)}")
    sys.exit(1)

def test_market_regime_detection():
    """Test chức năng phát hiện chế độ thị trường"""
    logger.info("=== TEST MARKET REGIME DETECTION ===")
    
    # Khởi tạo API và các module
    binance_api = BinanceAPI(simulation_mode=True)
    data_processor = DataProcessor(binance_api, simulation_mode=True)
    market_regime_detector = MarketRegimeDetector()
    
    # Lấy dữ liệu lịch sử
    symbol = "BTCUSDT"
    interval = "1h"
    df = data_processor.get_historical_data(symbol, interval, lookback_days=30)
    
    if df is not None and not df.empty:
        # Phát hiện chế độ thị trường
        regime = market_regime_detector.detect_regime(df)
        logger.info(f"Chế độ thị trường hiện tại: {regime}")
        
        # Lấy thông tin chi tiết về chế độ thị trường
        regime_info = market_regime_detector._get_regime_description(regime)
        logger.info(f"Mô tả: {regime_info}")
        
        # Lấy chiến lược được đề xuất
        recommended_strategy = market_regime_detector.get_recommended_strategy()
        logger.info(f"Chiến lược đề xuất: {recommended_strategy}")
        
        return True
    else:
        logger.error("Không thể lấy dữ liệu lịch sử")
        return False

def test_advanced_ml_optimizer():
    """Test Advanced ML Optimizer"""
    logger.info("=== TEST ADVANCED ML OPTIMIZER ===")
    
    # Khởi tạo API và các module
    binance_api = BinanceAPI(simulation_mode=True)
    data_processor = DataProcessor(binance_api, simulation_mode=True)
    
    # Khởi tạo Advanced ML Optimizer
    ml_optimizer = AdvancedMLOptimizer(
        base_models=["random_forest", "gradient_boosting", "neural_network"],
        use_model_per_regime=True,
        feature_selection=True,
        use_ensemble=True
    )
    
    # Lấy dữ liệu lịch sử
    symbol = "BTCUSDT"
    interval = "1h"
    df = data_processor.get_historical_data(symbol, interval, lookback_days=90)
    
    if df is not None and not df.empty:
        # Chuẩn bị tính năng và nhãn
        X = ml_optimizer.prepare_features_for_prediction(df)
        y = ml_optimizer.prepare_target_for_training(df, lookahead=6, threshold=0)
        
        if X is not None and y is not None:
            # Huấn luyện mô hình
            logger.info("Huấn luyện mô hình ML...")
            ml_optimizer.train_models(X, y)
            
            # Lưu mô hình
            os.makedirs("models", exist_ok=True)
            ml_optimizer.save_models("models")
            logger.info("Đã lưu mô hình ML")
            
            # Dự đoán
            X_test = X.iloc[-10:]
            predictions, probas = ml_optimizer.predict(X_test)
            
            logger.info(f"Dự đoán: {predictions}")
            logger.info(f"Xác suất: {probas}")
            
            # Lấy thông tin về tầm quan trọng của tính năng
            feature_importance = ml_optimizer.get_feature_importance(
                feature_names=X.columns.tolist()
            )
            
            # Hiển thị 10 tính năng quan trọng nhất
            logger.info("10 tính năng quan trọng nhất:")
            for i, (feature, importance) in enumerate(sorted(feature_importance.items(), 
                                                            key=lambda x: x[1], reverse=True)[:10]):
                logger.info(f"{i+1}. {feature}: {importance:.4f}")
            
            return True
        else:
            logger.error("Không thể chuẩn bị tính năng hoặc nhãn")
            return False
    else:
        logger.error("Không thể lấy dữ liệu lịch sử")
        return False

def test_advanced_ml_strategy():
    """Test Advanced ML Strategy"""
    logger.info("=== TEST ADVANCED ML STRATEGY ===")
    
    # Khởi tạo API và các module
    binance_api = BinanceAPI(simulation_mode=True)
    data_processor = DataProcessor(binance_api, simulation_mode=True)
    
    # Lấy dữ liệu lịch sử
    symbol = "BTCUSDT"
    interval = "1h"
    df = data_processor.get_historical_data(symbol, interval, lookback_days=30)
    
    if df is not None and not df.empty:
        try:
            # Tạo strategy thông qua factory
            strategy = StrategyFactory.create_strategy(
                strategy_type="advanced_ml",
                probability_threshold=0.65,
                confidence_threshold=0.6,
                window_size=3
            )
            
            if strategy:
                # Generate signal
                signal = strategy.generate_signal(df)
                logger.info(f"Tín hiệu giao dịch: {signal}")
                
                # Thông tin chiến lược
                strategy_info = strategy.get_strategy_info()
                logger.info(f"Thông tin chiến lược: {strategy_info}")
                
                return True
            else:
                logger.error("Không thể tạo AdvancedMLStrategy")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi test AdvancedMLStrategy: {str(e)}")
            return False
    else:
        logger.error("Không thể lấy dữ liệu lịch sử")
        return False

def main():
    logger.info("=== BẮT ĐẦU TEST ADVANCED ML ===")
    
    # Test market regime detection
    market_regime_result = test_market_regime_detection()
    logger.info(f"Market Regime Detection Test: {'PASSED' if market_regime_result else 'FAILED'}")
    
    # Test Advanced ML Optimizer
    ml_optimizer_result = test_advanced_ml_optimizer()
    logger.info(f"Advanced ML Optimizer Test: {'PASSED' if ml_optimizer_result else 'FAILED'}")
    
    # Test Advanced ML Strategy
    ml_strategy_result = test_advanced_ml_strategy()
    logger.info(f"Advanced ML Strategy Test: {'PASSED' if ml_strategy_result else 'FAILED'}")
    
    logger.info("=== KẾT THÚC TEST ===")

if __name__ == "__main__":
    main()