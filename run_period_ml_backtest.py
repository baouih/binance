#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script backtest ML theo giai đoạn thời gian khác nhau (1 tháng, 3 tháng, 6 tháng)

Script này thực hiện huấn luyện và kiểm thử mô hình ML trên dữ liệu giai đoạn 
cụ thể, tạo dự đoán xu hướng giá, và đánh giá hiệu suất mô hình.
"""

import os
import json
import argparse
import logging
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Any
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    filename='period_ml_backtest.log',
    filemode='a',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def load_data(symbol: str, timeframe: str, period: str, data_folder: str = 'real_data') -> pd.DataFrame:
    """
    Tải dữ liệu từ file CSV theo đồng tiền, khung thời gian và khoảng thời gian
    
    Args:
        symbol (str): Mã cặp giao dịch (ví dụ: BTCUSDT)
        timeframe (str): Khung thời gian (ví dụ: 1h, 4h, 1d)
        period (str): Khoảng thời gian (ví dụ: 1_month, 3_months, 6_months)
        data_folder (str): Thư mục chứa dữ liệu
        
    Returns:
        pd.DataFrame: DataFrame với dữ liệu giá
    """
    file_path = os.path.join(data_folder, period, f"{symbol}_{timeframe}.csv")
    if not os.path.exists(file_path):
        logger.error(f"Không tìm thấy file dữ liệu: {file_path}")
        raise FileNotFoundError(f"Không tìm thấy file dữ liệu: {file_path}")
    
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    logger.info(f"Đã tải dữ liệu từ {file_path}: {len(df)} dòng từ {df.index.min()} đến {df.index.max()}")
    return df

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tính toán các chỉ báo kỹ thuật
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu giá
        
    Returns:
        pd.DataFrame: DataFrame với các chỉ báo đã tính
    """
    try:
        # Thử sử dụng module feature_engineering nâng cao
        from feature_engineering import add_technical_indicators
        
        logger.info("Sử dụng module feature_engineering để tính toán chỉ báo nâng cao")
        df_indicators = add_technical_indicators(df)
        
        # Loại bỏ NaN
        df_indicators.dropna(inplace=True)
        
        logger.info(f"Đã tính tổng cộng {len(df_indicators.columns) - len(df.columns)} chỉ báo nâng cao")
        return df_indicators
        
    except ImportError:
        logger.warning("Không thể import module feature_engineering, sử dụng phương pháp tính chỉ báo cơ bản")
        # Tạo một bản sao
        df_indicators = df.copy()
        
        # Tính RSI (Relative Strength Index)
        delta = df_indicators['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        
        rs = avg_gain / avg_loss
        df_indicators['rsi'] = 100 - (100 / (1 + rs))
        
        # Tính MACD (Moving Average Convergence Divergence)
        ema12 = df_indicators['close'].ewm(span=12, adjust=False).mean()
        ema26 = df_indicators['close'].ewm(span=26, adjust=False).mean()
        df_indicators['macd'] = ema12 - ema26
        df_indicators['macd_signal'] = df_indicators['macd'].ewm(span=9, adjust=False).mean()
        df_indicators['macd_hist'] = df_indicators['macd'] - df_indicators['macd_signal']
        
        # Tính Bollinger Bands
        df_indicators['bb_middle'] = df_indicators['close'].rolling(window=20).mean()
        df_indicators['bb_std'] = df_indicators['close'].rolling(window=20).std()
        df_indicators['bb_upper'] = df_indicators['bb_middle'] + (df_indicators['bb_std'] * 2)
        df_indicators['bb_lower'] = df_indicators['bb_middle'] - (df_indicators['bb_std'] * 2)
        df_indicators['bb_width'] = (df_indicators['bb_upper'] - df_indicators['bb_lower']) / df_indicators['bb_middle']
        
        # Tính EMA (Exponential Moving Average)
        for period in [9, 21, 50, 200]:
            df_indicators[f'ema_{period}'] = df_indicators['close'].ewm(span=period, adjust=False).mean()
        
        # Tính SMA (Simple Moving Average)
        for period in [10, 20, 50, 200]:
            df_indicators[f'sma_{period}'] = df_indicators['close'].rolling(window=period).mean()
        
        # Tính ATR (Average True Range)
        high_low = df_indicators['high'] - df_indicators['low']
        high_close = (df_indicators['high'] - df_indicators['close'].shift()).abs()
        low_close = (df_indicators['low'] - df_indicators['close'].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df_indicators['atr'] = true_range.rolling(window=14).mean()
        
        # Tính Stochastic Oscillator
        low_14 = df_indicators['low'].rolling(window=14).min()
        high_14 = df_indicators['high'].rolling(window=14).max()
        df_indicators['stoch_k'] = 100 * ((df_indicators['close'] - low_14) / (high_14 - low_14))
        df_indicators['stoch_d'] = df_indicators['stoch_k'].rolling(window=3).mean()
        
        # Tính OBV (On-Balance Volume)
        df_indicators['obv'] = np.where(
            df_indicators['close'] > df_indicators['close'].shift(1),
            df_indicators['volume'],
            np.where(
                df_indicators['close'] < df_indicators['close'].shift(1),
                -df_indicators['volume'],
                0
            )
        ).cumsum()
        
        # Các biến đặc trưng khác
        df_indicators['returns'] = df_indicators['close'].pct_change()
        df_indicators['log_returns'] = np.log(df_indicators['close'] / df_indicators['close'].shift(1))
        df_indicators['volatility'] = df_indicators['log_returns'].rolling(window=20).std() * np.sqrt(252)
        
        # Loại bỏ NaN
        df_indicators.dropna(inplace=True)
        
        logger.info(f"Đã tính {len(df_indicators.columns) - len(df.columns)} chỉ báo cơ bản")
        return df_indicators

def create_target(df: pd.DataFrame, prediction_days: int = 1, threshold: float = 0.0) -> pd.DataFrame:
    """
    Tạo biến mục tiêu (xu hướng giá tương lai)
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu giá và chỉ báo
        prediction_days (int): Số ngày dự đoán xu hướng
        threshold (float): Ngưỡng để xác định là xu hướng (%)
        
    Returns:
        pd.DataFrame: DataFrame với cột target đã thêm
    """
    # Tạo một bản sao
    df_with_target = df.copy()
    
    # Tính tỷ lệ thay đổi giá sau prediction_days ngày
    df_with_target['future_price'] = df_with_target['close'].shift(-prediction_days)
    df_with_target['price_change'] = df_with_target['future_price'] / df_with_target['close'] - 1
    
    # Tạo mục tiêu dựa trên threshold
    df_with_target['target'] = np.where(
        df_with_target['price_change'] > threshold, 
        1,  # Xu hướng lên
        np.where(
            df_with_target['price_change'] < -threshold,
            -1,  # Xu hướng xuống
            0   # Đi ngang
        )
    )
    
    # Loại bỏ NaN
    df_with_target.dropna(inplace=True)
    
    # Log phân phối mục tiêu
    target_distribution = df_with_target['target'].value_counts(normalize=True) * 100
    logger.info(f"Phân phối mục tiêu: Tăng={target_distribution.get(1, 0):.2f}%, Giảm={target_distribution.get(-1, 0):.2f}%, Đi ngang={target_distribution.get(0, 0):.2f}%")
    
    return df_with_target

def prepare_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Chuẩn bị đặc trưng và mục tiêu cho mô hình
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu đã xử lý
        
    Returns:
        Tuple[pd.DataFrame, pd.Series]: (Đặc trưng, Mục tiêu)
    """
    # Danh sách cột không phải đặc trưng
    non_feature_columns = ['open', 'high', 'low', 'close', 'volume', 'future_price', 'price_change', 'target',
                          'close_time', 'quote_asset_volume', 'number_of_trades', 
                          'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore']
    
    # Lọc các cột đặc trưng
    feature_columns = [col for col in df.columns if col not in non_feature_columns]
    
    X = df[feature_columns]
    y = df['target']
    
    logger.info(f"Đã chuẩn bị {len(feature_columns)} đặc trưng")
    return X, y

def train_test_model(X: pd.DataFrame, y: pd.Series, model_type: str = 'random_forest', 
                   tune_hyperparams: bool = False, test_size: float = 0.2, random_state: int = 42) -> Dict:
    """
    Huấn luyện và kiểm thử mô hình
    
    Args:
        X (pd.DataFrame): Dữ liệu đặc trưng
        y (pd.Series): Dữ liệu mục tiêu
        model_type (str): Loại mô hình ('random_forest', 'gradient_boosting')
        tune_hyperparams (bool): Có tinh chỉnh siêu tham số không
        test_size (float): Tỷ lệ dữ liệu kiểm thử
        random_state (int): Random seed
        
    Returns:
        Dict: Kết quả huấn luyện và kiểm thử
    """
    # Chuẩn hóa đặc trưng
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Tách dữ liệu thành tập huấn luyện và kiểm thử
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=test_size, random_state=random_state)
    
    # Thiết lập mô hình dựa trên loại
    if model_type.lower() == 'random_forest':
        model = RandomForestClassifier(random_state=random_state)
        param_grid = {
            'n_estimators': [50, 100, 200],
            'max_depth': [None, 10, 20, 30],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4]
        }
    elif model_type.lower() == 'gradient_boosting':
        model = GradientBoostingClassifier(random_state=random_state)
        param_grid = {
            'n_estimators': [50, 100, 200],
            'learning_rate': [0.01, 0.1, 0.2],
            'max_depth': [3, 5, 7],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4]
        }
    else:
        raise ValueError(f"Loại mô hình không hỗ trợ: {model_type}")
    
    # Tinh chỉnh siêu tham số nếu được yêu cầu
    if tune_hyperparams:
        logger.info(f"Bắt đầu tinh chỉnh siêu tham số cho {model_type}...")
        grid_search = GridSearchCV(model, param_grid, cv=5, scoring='f1_macro', n_jobs=-1)
        grid_search.fit(X_train, y_train)
        
        best_params = grid_search.best_params_
        model = grid_search.best_estimator_
        logger.info(f"Siêu tham số tốt nhất: {best_params}")
    else:
        model.fit(X_train, y_train)
        best_params = {}
    
    # Dự đoán trên tập kiểm thử
    y_pred = model.predict(X_test)
    
    # Tính các chỉ số hiệu suất
    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred, average='macro'),
        'recall': recall_score(y_test, y_pred, average='macro'),
        'f1_score': f1_score(y_test, y_pred, average='macro'),
        'confusion_matrix': confusion_matrix(y_test, y_pred).tolist()
    }
    
    # Tính feature importance
    feature_importance = {}
    if hasattr(model, 'feature_importances_'):
        # Lấy tên đặc trưng từ dữ liệu gốc
        feature_names = X.columns.tolist()
        importances = model.feature_importances_
        
        # Sắp xếp theo độ quan trọng
        indices = np.argsort(importances)[::-1]
        top_features = {i: feature_names[i] for i in indices[:20]}  # Top 20 features
        top_importance = {i: float(importances[i]) for i in indices[:20]}
        
        feature_importance = {
            'features': top_features,
            'importance': top_importance
        }
    
    logger.info(f"Kết quả huấn luyện {model_type}: Accuracy={metrics['accuracy']:.4f}, F1-Score={metrics['f1_score']:.4f}")
    
    return {
        'model': model,
        'scaler': scaler,
        'metrics': metrics,
        'best_params': best_params,
        'feature_importance': feature_importance
    }

def create_charts(df: pd.DataFrame, result: Dict, symbol: str, timeframe: str, 
                period: str, prediction_days: int, charts_folder: str = 'ml_charts') -> Dict:
    """
    Tạo biểu đồ phân tích và dự đoán
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu đã xử lý
        result (Dict): Kết quả huấn luyện và kiểm thử
        symbol (str): Mã cặp giao dịch
        timeframe (str): Khung thời gian
        period (str): Khoảng thời gian dữ liệu
        prediction_days (int): Số ngày dự đoán
        charts_folder (str): Thư mục lưu biểu đồ
        
    Returns:
        Dict: Đường dẫn đến các biểu đồ
    """
    os.makedirs(charts_folder, exist_ok=True)
    chart_paths = {}
    
    # Biểu đồ 1: Phân tích giá và xu hướng
    plt.figure(figsize=(12, 8))
    plt.subplot(2, 1, 1)
    plt.plot(df.index, df['close'], label='Giá đóng cửa')
    plt.title(f'Biểu đồ giá {symbol} {timeframe} ({period})')
    plt.ylabel('Giá')
    plt.grid(True)
    plt.legend()
    
    plt.subplot(2, 1, 2)
    plt.scatter(df.index, df['target'], c=df['target'], cmap='viridis', alpha=0.6)
    plt.title(f'Xu hướng tương lai ({prediction_days} ngày)')
    plt.ylabel('Xu hướng (-1, 0, 1)')
    plt.grid(True)
    
    chart_path = os.path.join(charts_folder, f"{symbol}_{timeframe}_{period}_price_trend.png")
    plt.tight_layout()
    plt.savefig(chart_path)
    plt.close()
    chart_paths['price_trend'] = chart_path
    
    # Biểu đồ 2: Confusion Matrix
    cm = result['metrics']['confusion_matrix']
    plt.figure(figsize=(8, 6))
    plt.imshow(cm, interpolation='nearest', cmap='Blues')
    plt.title(f'Confusion Matrix - {symbol} {timeframe} ({period})')
    plt.colorbar()
    
    classes = ['Giảm', 'Đi ngang', 'Tăng']
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes, rotation=45)
    plt.yticks(tick_marks, classes)
    
    # Hiển thị giá trị trên từng ô
    thresh = np.max(cm) / 2.
    for i in range(len(cm)):
        for j in range(len(cm[i])):
            plt.text(j, i, format(cm[i][j], 'd'),
                    horizontalalignment="center",
                    color="white" if cm[i][j] > thresh else "black")
    
    plt.xlabel('Dự đoán')
    plt.ylabel('Thực tế')
    plt.tight_layout()
    
    chart_path = os.path.join(charts_folder, f"{symbol}_{timeframe}_{period}_confusion_matrix.png")
    plt.savefig(chart_path)
    plt.close()
    chart_paths['confusion_matrix'] = chart_path
    
    # Biểu đồ 3: Feature Importance
    if 'feature_importance' in result and result['feature_importance']:
        features = result['feature_importance']['features']
        importance = result['feature_importance']['importance']
        
        # Lấy 10 đặc trưng quan trọng nhất
        top_indices = sorted(importance.keys(), key=lambda i: float(importance[i]), reverse=True)[:10]
        top_features = [features[i] for i in top_indices]
        top_importance = [importance[i] for i in top_indices]
        
        plt.figure(figsize=(10, 6))
        plt.barh(range(len(top_features)), top_importance, align='center')
        plt.yticks(range(len(top_features)), top_features)
        plt.xlabel('Độ quan trọng')
        plt.title(f'Top 10 đặc trưng quan trọng - {symbol} {timeframe} ({period})')
        plt.tight_layout()
        
        chart_path = os.path.join(charts_folder, f"{symbol}_{timeframe}_{period}_feature_importance.png")
        plt.savefig(chart_path)
        plt.close()
        chart_paths['feature_importance'] = chart_path
    
    return chart_paths

def save_results(result: Dict, symbol: str, timeframe: str, period: str, 
               prediction_days: int, model_type: str, chart_paths: Dict,
               output_folder: str = 'ml_results', models_folder: str = 'ml_models') -> str:
    """
    Lưu kết quả huấn luyện và kiểm thử
    
    Args:
        result (Dict): Kết quả huấn luyện và kiểm thử
        symbol (str): Mã cặp giao dịch
        timeframe (str): Khung thời gian
        period (str): Khoảng thời gian dữ liệu
        prediction_days (int): Số ngày dự đoán
        model_type (str): Loại mô hình
        chart_paths (Dict): Đường dẫn đến các biểu đồ
        output_folder (str): Thư mục lưu kết quả
        models_folder (str): Thư mục lưu mô hình
        
    Returns:
        str: Đường dẫn đến file kết quả
    """
    # Tạo thư mục đầu ra nếu chưa tồn tại
    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(models_folder, exist_ok=True)
    
    # Tạo tên file dựa trên tham số
    result_filename = f"{symbol}_{timeframe}_{period}_{prediction_days}d_{model_type}_results.json"
    model_filename = f"{symbol}_{timeframe}_{period}_{prediction_days}d_{model_type}_model.joblib"
    
    # Tạo đối tượng kết quả
    result_obj = {
        'symbol': symbol,
        'timeframe': timeframe,
        'period': period,
        'prediction_days': prediction_days,
        'model_type': model_type,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'accuracy': result['metrics']['accuracy'],
        'precision': result['metrics']['precision'],
        'recall': result['metrics']['recall'],
        'f1_score': result['metrics']['f1_score'],
        'confusion_matrix': result['metrics']['confusion_matrix'],
        'best_params': result['best_params'],
        'feature_importance': result['feature_importance'],
        'charts': chart_paths
    }
    
    # Hàm chuyển đổi NumPy types sang Python standard types
    def convert_numpy_types(obj):
        if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32, np.float16)):
            return float(obj)
        elif isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {convert_numpy_types(k): convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy_types(i) for i in obj]
        return obj

    # Chuyển đổi các giá trị NumPy trong result_obj
    result_obj = convert_numpy_types(result_obj)
    
    # Lưu kết quả
    result_path = os.path.join(output_folder, result_filename)
    with open(result_path, 'w') as f:
        json.dump(result_obj, f, indent=2)
    
    # Lưu mô hình (optional)
    try:
        import joblib
        model_path = os.path.join(models_folder, model_filename)
        joblib.dump({'model': result['model'], 'scaler': result['scaler']}, model_path)
        logger.info(f"Đã lưu mô hình tại {model_path}")
    except Exception as e:
        logger.warning(f"Không thể lưu mô hình: {e}")
    
    logger.info(f"Đã lưu kết quả tại {result_path}")
    return result_path

def run_backtest(symbol: str, timeframe: str, period: str, prediction_days: int = 1,
               model_type: str = 'random_forest', tune_hyperparams: bool = False,
               data_folder: str = 'real_data', output_folder: str = 'ml_results',
               charts_folder: str = 'ml_charts', models_folder: str = 'ml_models') -> str:
    """
    Chạy quá trình backtest đầy đủ
    
    Args:
        symbol (str): Mã cặp giao dịch
        timeframe (str): Khung thời gian
        period (str): Khoảng thời gian dữ liệu
        prediction_days (int): Số ngày dự đoán
        model_type (str): Loại mô hình
        tune_hyperparams (bool): Có tinh chỉnh siêu tham số không
        data_folder (str): Thư mục chứa dữ liệu
        output_folder (str): Thư mục lưu kết quả
        charts_folder (str): Thư mục lưu biểu đồ
        models_folder (str): Thư mục lưu mô hình
        
    Returns:
        str: Đường dẫn đến file kết quả
    """
    logger.info(f"Bắt đầu backtest: {symbol} {timeframe} ({period}), dự đoán {prediction_days} ngày, mô hình {model_type}")
    
    # Bước 1: Tải dữ liệu
    df = load_data(symbol, timeframe, period, data_folder)
    
    # Bước 2: Tính toán chỉ báo
    df_indicators = calculate_indicators(df)
    
    # Bước 3: Tạo biến mục tiêu
    df_with_target = create_target(df_indicators, prediction_days)
    
    # Bước 4: Chuẩn bị đặc trưng
    X, y = prepare_features(df_with_target)
    
    # Bước 5: Huấn luyện và kiểm thử mô hình
    result = train_test_model(X, y, model_type, tune_hyperparams)
    
    # Bước 6: Tạo biểu đồ
    chart_paths = create_charts(df_with_target, result, symbol, timeframe, period, prediction_days, charts_folder)
    
    # Bước 7: Lưu kết quả
    result_path = save_results(
        result, symbol, timeframe, period, prediction_days, model_type, chart_paths,
        output_folder, models_folder
    )
    
    logger.info(f"Hoàn thành backtest: {symbol} {timeframe} ({period}), dự đoán {prediction_days} ngày, mô hình {model_type}")
    return result_path

def main():
    parser = argparse.ArgumentParser(description='Chạy backtest ML theo giai đoạn thời gian')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Mã cặp giao dịch')
    parser.add_argument('--timeframe', type=str, default='1h', help='Khung thời gian (1h, 4h, 1d)')
    parser.add_argument('--period', type=str, default='1_month', help='Khoảng thời gian (1_month, 3_months, 6_months)')
    parser.add_argument('--prediction_days', type=int, default=1, help='Số ngày dự đoán xu hướng')
    parser.add_argument('--model_type', type=str, default='random_forest', help='Loại mô hình (random_forest, gradient_boosting)')
    parser.add_argument('--tune_hyperparams', action='store_true', help='Có tinh chỉnh siêu tham số không')
    parser.add_argument('--data_folder', type=str, default='real_data', help='Thư mục chứa dữ liệu')
    parser.add_argument('--output_folder', type=str, default='ml_results', help='Thư mục lưu kết quả')
    parser.add_argument('--charts_folder', type=str, default='ml_charts', help='Thư mục lưu biểu đồ')
    parser.add_argument('--models_folder', type=str, default='ml_models', help='Thư mục lưu mô hình')
    
    args = parser.parse_args()
    
    result_path = run_backtest(
        args.symbol, args.timeframe, args.period, args.prediction_days,
        args.model_type, args.tune_hyperparams,
        args.data_folder, args.output_folder, args.charts_folder, args.models_folder
    )
    
    print(f"Backtest hoàn thành! Kết quả được lưu tại: {result_path}")

if __name__ == "__main__":
    main()