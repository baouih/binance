#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script chạy backtest ML cho một khoảng thời gian và symbol cụ thể,
tối ưu hóa và đánh giá hiệu suất với các tham số mục tiêu khác nhau.
"""

import os
import json
import argparse
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_score, recall_score, f1_score

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def load_data(symbol, timeframe, period, data_folder='real_data'):
    """
    Tải dữ liệu từ file CSV
    
    Args:
        symbol (str): Mã cặp giao dịch
        timeframe (str): Khung thời gian
        period (str): Khoảng thời gian (1_month, 3_months, 6_months)
        data_folder (str): Thư mục chứa dữ liệu
        
    Returns:
        pd.DataFrame: DataFrame dữ liệu
    """
    file_path = f"{data_folder}/{period}/{symbol}_{timeframe}.csv"
    logger.info(f"Đang tải dữ liệu từ {file_path}...")
    
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    logger.info(f"Đã tải dữ liệu từ {df.index.min()} đến {df.index.max()}, tổng cộng {len(df)} mẫu")
    return df

def add_features(df):
    """
    Thêm các đặc trưng kỹ thuật
    
    Args:
        df (pd.DataFrame): DataFrame dữ liệu gốc
        
    Returns:
        pd.DataFrame: DataFrame với các đặc trưng mới
    """
    # Sao chép dữ liệu để tránh thay đổi dữ liệu gốc
    df_feat = df.copy()
    
    # Thêm các chỉ báo price-based
    df_feat['price_change'] = df_feat['close'].pct_change()
    df_feat['price_change_1'] = df_feat['close'].pct_change(1)
    df_feat['price_change_2'] = df_feat['close'].pct_change(2) 
    df_feat['price_change_3'] = df_feat['close'].pct_change(3)
    df_feat['price_change_5'] = df_feat['close'].pct_change(5)
    df_feat['price_change_10'] = df_feat['close'].pct_change(10)
    
    # Volatility measures
    df_feat['high_low_diff'] = (df_feat['high'] - df_feat['low']) / df_feat['close']
    df_feat['high_close_diff'] = (df_feat['high'] - df_feat['close']) / df_feat['close']
    df_feat['low_close_diff'] = (df_feat['close'] - df_feat['low']) / df_feat['close']
    
    # Moving averages
    for window in [5, 10, 20, 50, 100]:
        df_feat[f'MA_{window}'] = df_feat['close'].rolling(window=window).mean()
        df_feat[f'MA_diff_{window}'] = df_feat['close'] / df_feat[f'MA_{window}'] - 1
    
    # Volume-based features
    df_feat['volume_change'] = df_feat['volume'].pct_change()
    df_feat['volume_ma_5'] = df_feat['volume'].rolling(window=5).mean()
    df_feat['volume_ma_10'] = df_feat['volume'].rolling(window=10).mean()
    df_feat['volume_ratio_5'] = df_feat['volume'] / df_feat['volume_ma_5']
    df_feat['volume_ratio_10'] = df_feat['volume'] / df_feat['volume_ma_10']
    
    # RSI (Relative Strength Index)
    delta = df_feat['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    for window in [14, 7, 21]:
        avg_gain = gain.rolling(window=window).mean()
        avg_loss = loss.rolling(window=window).mean()
        rs = avg_gain / avg_loss
        df_feat[f'RSI_{window}'] = 100 - (100 / (1 + rs))
    
    # Bollinger Bands
    for window in [20]:
        df_feat[f'BB_MA_{window}'] = df_feat['close'].rolling(window=window).mean()
        df_feat[f'BB_STD_{window}'] = df_feat['close'].rolling(window=window).std()
        df_feat[f'BB_Upper_{window}'] = df_feat[f'BB_MA_{window}'] + 2 * df_feat[f'BB_STD_{window}']
        df_feat[f'BB_Lower_{window}'] = df_feat[f'BB_MA_{window}'] - 2 * df_feat[f'BB_STD_{window}']
        df_feat[f'BB_Width_{window}'] = (df_feat[f'BB_Upper_{window}'] - df_feat[f'BB_Lower_{window}']) / df_feat[f'BB_MA_{window}']
        df_feat[f'BB_Position_{window}'] = (df_feat['close'] - df_feat[f'BB_Lower_{window}']) / (df_feat[f'BB_Upper_{window}'] - df_feat[f'BB_Lower_{window}'])
    
    # MACD
    ema_12 = df_feat['close'].ewm(span=12, adjust=False).mean()
    ema_26 = df_feat['close'].ewm(span=26, adjust=False).mean()
    df_feat['MACD_Line'] = ema_12 - ema_26
    df_feat['MACD_Signal'] = df_feat['MACD_Line'].ewm(span=9, adjust=False).mean()
    df_feat['MACD_Hist'] = df_feat['MACD_Line'] - df_feat['MACD_Signal']
    
    # ATR (Average True Range)
    high_low = df_feat['high'] - df_feat['low']
    high_close = (df_feat['high'] - df_feat['close'].shift()).abs()
    low_close = (df_feat['low'] - df_feat['close'].shift()).abs()
    
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df_feat['ATR_14'] = true_range.rolling(14).mean()
    
    # Stochastic Oscillator
    for window in [14]:
        df_feat[f'Stoch_Low_{window}'] = df_feat['low'].rolling(window=window).min()
        df_feat[f'Stoch_High_{window}'] = df_feat['high'].rolling(window=window).max()
        df_feat[f'Stoch_K_{window}'] = 100 * ((df_feat['close'] - df_feat[f'Stoch_Low_{window}']) / 
                                         (df_feat[f'Stoch_High_{window}'] - df_feat[f'Stoch_Low_{window}']))
        df_feat[f'Stoch_D_{window}'] = df_feat[f'Stoch_K_{window}'].rolling(window=3).mean()
    
    # ADX (Average Directional Index)
    plus_dm = df_feat['high'].diff()
    minus_dm = df_feat['low'].diff(-1).abs()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    tr = true_range
    plus_di_14 = 100 * (plus_dm.rolling(14).sum() / tr.rolling(14).sum())
    minus_di_14 = 100 * (minus_dm.rolling(14).sum() / tr.rolling(14).sum())
    dx = 100 * (plus_di_14 - minus_di_14).abs() / (plus_di_14 + minus_di_14)
    df_feat['ADX_14'] = dx.rolling(14).mean()
    df_feat['Plus_DI_14'] = plus_di_14
    df_feat['Minus_DI_14'] = minus_di_14
    
    # Làm sạch các giá trị NaN sau khi tính toán
    df_feat.dropna(inplace=True)
    
    logger.info(f"Đã tạo {len(df_feat.columns) - len(df.columns)} đặc trưng mới, còn lại {len(df_feat)} mẫu")
    
    return df_feat

def create_target(df, prediction_days=3):
    """
    Tạo biến mục tiêu dựa trên chuyển động giá trong tương lai
    
    Args:
        df (pd.DataFrame): DataFrame dữ liệu
        prediction_days (int): Số ngày dự đoán tương lai
        
    Returns:
        pd.DataFrame: DataFrame với biến mục tiêu
    """
    df_target = df.copy()
    
    # Tạo mục tiêu: tăng hay giảm giá sau prediction_days
    df_target['future_price'] = df_target['close'].shift(-prediction_days)
    df_target['target'] = (df_target['future_price'] > df_target['close']).astype(int)
    
    # Tạo % biến động
    df_target['price_change_pct'] = (df_target['future_price'] - df_target['close']) / df_target['close'] * 100
    
    # Loại bỏ các hàng không có giá trị mục tiêu
    df_target.dropna(subset=['future_price', 'target'], inplace=True)
    
    # Thống kê phân bố lớp
    class_distribution = df_target['target'].value_counts(normalize=True)
    logger.info(f"Phân bố lớp mục tiêu (target): \n{class_distribution}")
    logger.info(f"% thay đổi giá trung bình: {df_target['price_change_pct'].mean():.2f}%")
    logger.info(f"% thay đổi giá trung vị: {df_target['price_change_pct'].median():.2f}%")
    
    return df_target

def prepare_features_targets(df, drop_columns=None):
    """
    Chuẩn bị đặc trưng và mục tiêu cho huấn luyện
    
    Args:
        df (pd.DataFrame): DataFrame dữ liệu
        drop_columns (list): Danh sách cột cần loại bỏ
        
    Returns:
        tuple: (X_features, y_target)
    """
    if drop_columns is None:
        drop_columns = ['open', 'high', 'low', 'close', 'volume', 'close_time',
                         'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
                         'taker_buy_quote_asset_volume', 'ignore', 'future_price', 'price_change_pct']
    
    df_ml = df.copy()
    
    X = df_ml.drop(columns=drop_columns + ['target'])
    y = df_ml['target']
    
    logger.info(f"Dữ liệu đặc trưng có hình dạng: {X.shape}")
    logger.info(f"Biến mục tiêu có hình dạng: {y.shape}")
    
    return X, y

def train_and_evaluate_model(X, y, model_type='random_forest', output_folder='ml_results', 
                           charts_folder='ml_charts', models_folder='ml_models', 
                           symbol='BTCUSDT', timeframe='1h', period='1_month', 
                           prediction_days=1, test_size=0.2, tune_hyperparams=True):
    """
    Huấn luyện và đánh giá mô hình
    
    Args:
        X (pd.DataFrame): Đặc trưng đầu vào
        y (pd.Series): Biến mục tiêu
        model_type (str): Loại mô hình ('random_forest', 'gradient_boosting')
        output_folder (str): Thư mục lưu kết quả
        charts_folder (str): Thư mục lưu biểu đồ
        models_folder (str): Thư mục lưu mô hình
        symbol (str): Mã cặp giao dịch
        timeframe (str): Khung thời gian
        period (str): Khoảng thời gian
        prediction_days (int): Số ngày dự đoán tương lai
        test_size (float): Tỷ lệ dữ liệu test
        tune_hyperparams (bool): Có tối ưu hóa siêu tham số không
        
    Returns:
        dict: Kết quả đánh giá mô hình
    """
    # Đảm bảo thư mục tồn tại
    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(charts_folder, exist_ok=True)
    os.makedirs(models_folder, exist_ok=True)
    
    # Chuẩn hóa đặc trưng
    logger.info("Chuẩn hóa đặc trưng...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Chia tập dữ liệu train/test
    logger.info(f"Chia tập dữ liệu với test_size={test_size}...")
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=test_size, shuffle=False)
    
    # Chọn và khởi tạo mô hình
    if model_type == 'random_forest':
        model = RandomForestClassifier(random_state=42)
        param_grid = {
            'n_estimators': [100, 200, 300],
            'max_depth': [None, 10, 20, 30],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4]
        }
    elif model_type == 'gradient_boosting':
        model = GradientBoostingClassifier(random_state=42)
        param_grid = {
            'n_estimators': [100, 200, 300],
            'learning_rate': [0.01, 0.05, 0.1],
            'max_depth': [3, 5, 7],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4]
        }
    else:
        raise ValueError(f"Không hỗ trợ loại mô hình: {model_type}")
    
    # Tối ưu hóa siêu tham số nếu được yêu cầu
    if tune_hyperparams:
        logger.info("Bắt đầu tối ưu hóa siêu tham số...")
        grid_search = GridSearchCV(model, param_grid, cv=5, scoring='f1', n_jobs=-1)
        grid_search.fit(X_train, y_train)
        
        # Lấy mô hình tốt nhất
        model = grid_search.best_estimator_
        logger.info(f"Siêu tham số tốt nhất: {grid_search.best_params_}")
    else:
        # Huấn luyện mô hình với tham số mặc định
        logger.info("Huấn luyện mô hình với tham số mặc định...")
        model.fit(X_train, y_train)
    
    # Dự đoán
    logger.info("Dự đoán và đánh giá mô hình...")
    y_pred = model.predict(X_test)
    
    # Tính các chỉ số đánh giá
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    
    logger.info(f"Accuracy: {accuracy:.4f}")
    logger.info(f"Precision: {precision:.4f}")
    logger.info(f"Recall: {recall:.4f}")
    logger.info(f"F1-Score: {f1:.4f}")
    
    # Lấy báo cáo chi tiết
    classification_rep = classification_report(y_test, y_pred, output_dict=True)
    conf_matrix = confusion_matrix(y_test, y_pred)
    
    # Lấy tầm quan trọng đặc trưng
    feature_importance = None
    if hasattr(model, 'feature_importances_'):
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
    
    # Tạo các biểu đồ
    file_prefix = f"{symbol}_{timeframe}_{period.split('_')[0]}m_target{prediction_days}d"
    
    # 1. Vẽ ma trận nhầm lẫn
    plt.figure(figsize=(8, 6))
    plt.imshow(conf_matrix, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title(f'Ma trận nhầm lẫn ({symbol} {timeframe}, {period}, {prediction_days}d)')
    plt.colorbar()
    
    classes = ['Giảm', 'Tăng']
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes)
    plt.yticks(tick_marks, classes)
    
    thresh = conf_matrix.max() / 2
    for i in range(conf_matrix.shape[0]):
        for j in range(conf_matrix.shape[1]):
            plt.text(j, i, format(conf_matrix[i, j], 'd'),
                    ha="center", va="center",
                    color="white" if conf_matrix[i, j] > thresh else "black")
    
    plt.ylabel('Nhãn thực tế')
    plt.xlabel('Nhãn dự đoán')
    plt.tight_layout()
    conf_matrix_path = f"{charts_folder}/{file_prefix}_confusion_matrix.png"
    plt.savefig(conf_matrix_path)
    plt.close()
    
    # 2. Vẽ feature importance nếu có
    if feature_importance is not None:
        plt.figure(figsize=(10, 8))
        top_features = feature_importance.head(20)
        plt.barh(top_features['feature'][::-1], top_features['importance'][::-1])
        plt.title(f'Top 20 đặc trưng quan trọng nhất ({symbol} {timeframe}, {period}, {prediction_days}d)')
        plt.tight_layout()
        feature_importance_path = f"{charts_folder}/{file_prefix}_feature_importance.png"
        plt.savefig(feature_importance_path)
        plt.close()
    
    # Lưu kết quả đánh giá
    result = {
        'symbol': symbol,
        'timeframe': timeframe,
        'period': period,
        'prediction_days': prediction_days,
        'model_type': model_type,
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'classification_report': classification_rep,
        'confusion_matrix': conf_matrix.tolist(),
        'feature_importance': feature_importance.to_dict() if feature_importance is not None else None,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Thêm siêu tham số nếu có tối ưu hóa
    if tune_hyperparams:
        result['best_params'] = grid_search.best_params_
    
    # Lưu kết quả thành file JSON
    result_file = f"{output_folder}/{file_prefix}_results.json"
    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    # Lưu mô hình
    import joblib
    model_file = f"{models_folder}/{file_prefix}_model.joblib"
    joblib.dump(model, model_file)
    
    # Lưu scaler
    scaler_file = f"{models_folder}/{file_prefix}_scaler.joblib"
    joblib.dump(scaler, scaler_file)
    
    logger.info(f"Đã lưu kết quả vào {result_file}")
    logger.info(f"Đã lưu mô hình vào {model_file}")
    
    return result

def main():
    parser = argparse.ArgumentParser(description='ML Backtest cho một khoảng thời gian')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Mã cặp giao dịch')
    parser.add_argument('--timeframe', type=str, default='1h', help='Khung thời gian')
    parser.add_argument('--period', type=str, default='1_month', help='Khoảng thời gian')
    parser.add_argument('--prediction_days', type=int, default=1, help='Số ngày dự đoán tương lai')
    parser.add_argument('--model_type', type=str, default='random_forest', help='Loại mô hình')
    parser.add_argument('--data_folder', type=str, default='real_data', help='Thư mục dữ liệu')
    parser.add_argument('--output_folder', type=str, default='ml_results', help='Thư mục kết quả')
    parser.add_argument('--charts_folder', type=str, default='ml_charts', help='Thư mục biểu đồ')
    parser.add_argument('--models_folder', type=str, default='ml_models', help='Thư mục mô hình')
    parser.add_argument('--test_size', type=float, default=0.2, help='Tỷ lệ dữ liệu test')
    parser.add_argument('--tune_hyperparams', action='store_true', help='Tối ưu hóa siêu tham số')
    
    args = parser.parse_args()
    
    logger.info("=== Bắt đầu ML Backtest ===")
    logger.info(f"Symbol: {args.symbol}")
    logger.info(f"Timeframe: {args.timeframe}")
    logger.info(f"Khoảng thời gian: {args.period}")
    logger.info(f"Dự đoán tương lai: {args.prediction_days} ngày")
    logger.info(f"Loại mô hình: {args.model_type}")
    
    # Tải dữ liệu
    df = load_data(args.symbol, args.timeframe, args.period, args.data_folder)
    
    # Thêm đặc trưng kỹ thuật
    df_features = add_features(df)
    
    # Tạo biến mục tiêu
    df_target = create_target(df_features, args.prediction_days)
    
    # Chuẩn bị dữ liệu
    X, y = prepare_features_targets(df_target)
    
    # Huấn luyện và đánh giá mô hình
    result = train_and_evaluate_model(
        X, y, 
        model_type=args.model_type,
        output_folder=args.output_folder,
        charts_folder=args.charts_folder,
        models_folder=args.models_folder,
        symbol=args.symbol,
        timeframe=args.timeframe,
        period=args.period,
        prediction_days=args.prediction_days,
        test_size=args.test_size,
        tune_hyperparams=args.tune_hyperparams
    )
    
    logger.info("=== Hoàn tất ML Backtest ===")

if __name__ == "__main__":
    main()