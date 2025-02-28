#!/usr/bin/env python3
"""
Script huấn luyện mô hình ML và chạy test đơn giản
"""

import os
import logging
import time
import json
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('train_ml')

# Đảm bảo thư mục models tồn tại
os.makedirs('models', exist_ok=True)

def main():
    """
    Hàm chính để huấn luyện mô hình và test
    """
    logger.info("=== BẮT ĐẦU HUẤN LUYỆN MÔ HÌNH ML ===")
    
    try:
        # Import các module cần thiết
        from app.binance_api import BinanceAPI
        from app.data_processor import DataProcessor
        from app.advanced_ml_optimizer import AdvancedMLOptimizer

        # Khởi tạo các đối tượng
        binance_api = BinanceAPI(simulation_mode=True)
        data_processor = DataProcessor(binance_api, simulation_mode=True)

        # Tạo dữ liệu mẫu
        symbol = 'BTCUSDT'
        timeframe = '1h'
        days = 30
        
        logger.info(f"Lấy dữ liệu cho {symbol} khung {timeframe} trong {days} ngày")
        df = data_processor.get_historical_data(symbol, timeframe, lookback_days=days)
        
        if df is None or len(df) < 100:
            logger.error(f"Không đủ dữ liệu để huấn luyện. Số mẫu: {0 if df is None else len(df)}")
            return
            
        logger.info(f"Đã lấy được {len(df)} mẫu dữ liệu")
        
        # Khởi tạo ML Optimizer
        logger.info("Khởi tạo ML Optimizer")
        ml_optimizer = AdvancedMLOptimizer(
            base_models=['random_forest', 'gradient_boosting'],
            use_model_per_regime=True,
            feature_selection=True,
            use_ensemble=True
        )
        
        # Chuẩn bị tính năng và mục tiêu
        logger.info("Chuẩn bị dữ liệu huấn luyện")
        X = ml_optimizer.prepare_features_for_prediction(df)
        y = ml_optimizer.prepare_target_for_training(df, lookahead=3, threshold=0.005)
        
        if X is None or y is None:
            logger.error("Lỗi khi chuẩn bị dữ liệu")
            return
        
        # Đảm bảo X và y có cùng số lượng mẫu
        if len(X) > len(y):
            logger.info(f"Cắt X từ {len(X)} xuống {len(y)} để khớp với y")
            X = X.iloc[-len(y):].copy()
        elif len(y) > len(X):
            logger.info(f"Cắt y từ {len(y)} xuống {len(X)} để khớp với X")
            y = y[-len(X):].copy()
            
        logger.info(f"Dữ liệu huấn luyện: X={X.shape}, y={y.shape}")
        
        # Huấn luyện mô hình
        logger.info("Bắt đầu huấn luyện mô hình...")
        metrics = ml_optimizer.train_models(X, y)
        
        if metrics:
            logger.info(f"Hiệu suất huấn luyện: {metrics}")
            
            # Lưu mô hình
            logger.info("Lưu mô hình vào thư mục models")
            ml_optimizer.save_models('models/advanced_ml_models.joblib')
            
            # Chạy backtest
            logger.info("Chạy backtest với mô hình đã huấn luyện")
            results = ml_optimizer.backtest_strategy(df)
            
            if results:
                logger.info(f"Kết quả backtest: {results}")
                
                # Lưu kết quả
                with open('models/backtest_results.json', 'w') as f:
                    json.dump(results, f, indent=2)
                
                logger.info("Đã lưu kết quả backtest vào models/backtest_results.json")
        else:
            logger.error("Không có kết quả hiệu suất từ quá trình huấn luyện")
    
    except Exception as e:
        logger.error(f"Lỗi trong quá trình huấn luyện: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
    logger.info("=== KẾT THÚC HUẤN LUYỆN MÔ HÌNH ML ===")
            
if __name__ == "__main__":
    main()