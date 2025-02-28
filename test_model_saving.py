"""
Script kiểm tra tính năng lưu và tải mô hình

Script này sẽ huấn luyện một mô hình đơn giản, lưu vào thư mục models,
và sau đó tải lại để kiểm tra tính năng hoạt động đúng.
"""

import os
import logging
import numpy as np
from datetime import datetime

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import pandas as pd
    from app.advanced_ml_optimizer import AdvancedMLOptimizer
    from app.binance_api import BinanceAPI
    from app.data_processor import DataProcessor
except ImportError as e:
    logger.error(f"Không thể import các module cần thiết: {e}")
    raise

def generate_sample_data(size=1000):
    """Tạo dữ liệu mẫu cho việc huấn luyện"""
    logger.info(f"Tạo {size} mẫu dữ liệu giả lập")
    
    # Tạo dữ liệu giá ngẫu nhiên
    dates = pd.date_range(end=datetime.now(), periods=size)
    close = np.random.normal(100, 5, size=size).cumsum() + 10000
    open_price = close * np.random.normal(1, 0.01, size=size)
    high = np.maximum(close, open_price) * np.random.normal(1.01, 0.005, size=size)
    low = np.minimum(close, open_price) * np.random.normal(0.99, 0.005, size=size)
    volume = np.random.normal(1000, 100, size=size) * np.abs(close - open_price)
    
    # Tạo DataFrame
    df = pd.DataFrame({
        'open_time': dates,
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
        'datetime': dates
    })
    
    # Thêm một số chỉ báo đơn giản
    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_50'] = df['close'].rolling(50).mean()
    df['rsi'] = calculate_rsi(df['close'])
    df['atr'] = calculate_atr(df)
    
    return df

def calculate_rsi(prices, window=14):
    """Tính RSI đơn giản"""
    deltas = prices.diff()
    seed = deltas[:window+1]
    up = seed[seed >= 0].sum()/window
    down = -seed[seed < 0].sum()/window
    rs = up/down if down != 0 else float('inf')
    rsi = np.zeros_like(prices)
    rsi[:window] = 100. - 100./(1. + rs)
    
    for i in range(window, len(prices)):
        delta = deltas[i]
        if delta > 0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta
            
        up = (up * (window - 1) + upval) / window
        down = (down * (window - 1) + downval) / window
        rs = up/down if down != 0 else float('inf')
        rsi[i] = 100. - 100./(1. + rs)
    
    return rsi

def calculate_atr(df, window=14):
    """Tính ATR đơn giản"""
    tr1 = df['high'] - df['low']
    tr2 = abs(df['high'] - df['close'].shift())
    tr3 = abs(df['low'] - df['close'].shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window).mean()
    
    return atr

def prepare_training_data(df):
    """Chuẩn bị dữ liệu huấn luyện"""
    logger.info("Chuẩn bị dữ liệu huấn luyện")
    
    # Loại bỏ các dòng có giá trị NaN
    df = df.dropna()
    
    # Tạo nhãn cho mô hình (ví dụ: giá sẽ tăng sau 5 chu kỳ)
    df['target'] = np.where(df['close'].shift(-5) > df['close'] * 1.005, 1, 
                        np.where(df['close'].shift(-5) < df['close'] * 0.995, -1, 0))
    
    # Loại bỏ các dòng không có nhãn (5 dòng cuối)
    df = df[:-5]
    
    return df

def train_and_save_model():
    """Huấn luyện và lưu mô hình"""
    logger.info("Bắt đầu huấn luyện và lưu mô hình")
    
    # Tạo thư mục models nếu chưa tồn tại
    os.makedirs('models', exist_ok=True)
    
    # Tạo dữ liệu mẫu
    df = generate_sample_data()
    
    # Chuẩn bị dữ liệu huấn luyện
    df_train = prepare_training_data(df)
    
    # Khởi tạo Advanced ML Optimizer
    optimizer = AdvancedMLOptimizer(
        base_models=['random_forest', 'gradient_boosting'],
        use_model_per_regime=True, 
        feature_selection=True,
        use_ensemble=True
    )
    
    # Chuẩn bị features và target
    X = optimizer.prepare_features_for_prediction(df_train)
    y = df_train['target'].values
    
    logger.info(f"Shape của X: {X.shape}, Shape của y: {y.shape}")
    
    # Huấn luyện mô hình
    logger.info("Huấn luyện mô hình...")
    metrics = optimizer.train_models(X, y)
    
    logger.info(f"Kết quả huấn luyện: {metrics}")
    
    # Lưu mô hình vào thư mục models
    model_path = optimizer.save_models('models/test_model.joblib')
    
    logger.info(f"Đã lưu mô hình vào: {model_path}")
    
    return model_path

def load_and_test_model(model_path):
    """Tải và kiểm tra mô hình"""
    logger.info(f"Tải mô hình từ: {model_path}")
    
    # Khởi tạo optimizer mới
    new_optimizer = AdvancedMLOptimizer()
    
    # Tải mô hình
    success = new_optimizer.load_models(model_path)
    
    if success:
        logger.info("Tải mô hình thành công!")
        
        # Tạo dữ liệu kiểm tra
        df_test = generate_sample_data(size=100)
        df_test = prepare_training_data(df_test)
        
        # Chuẩn bị features
        X_test = new_optimizer.prepare_features_for_prediction(df_test)
        
        # Dự đoán
        logger.info("Thực hiện dự đoán với mô hình đã tải...")
        y_pred, probas = new_optimizer.predict(X_test)
        
        logger.info(f"Số lượng dự đoán: {len(y_pred)}")
        logger.info(f"Phân phối nhãn dự đoán: Tăng: {sum(y_pred == 1)}, Giảm: {sum(y_pred == -1)}, Giữ nguyên: {sum(y_pred == 0)}")
        
        return True
    else:
        logger.error("Không thể tải mô hình")
        return False

def main():
    """Hàm chính"""
    logger.info("=== Bắt đầu kiểm tra lưu và tải mô hình ===")
    
    # Huấn luyện và lưu mô hình
    model_path = train_and_save_model()
    
    # Tải và kiểm tra mô hình
    success = load_and_test_model(model_path)
    
    # Thử tải mô hình từ thư mục
    if success:
        logger.info("=== Kiểm tra tải mô hình từ thư mục ===")
        dir_success = load_and_test_model('models')
        if dir_success:
            logger.info("Tính năng tải mô hình từ thư mục hoạt động tốt!")
    
    logger.info("=== Kết thúc kiểm tra ===")

if __name__ == "__main__":
    main()