#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tối ưu hóa mô hình ML cho bot giao dịch Bitcoin

Script này thực hiện tối ưu hóa hyperparameters và feature engineering 
để cải thiện độ chính xác của các mô hình ML.
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Any, Union, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import seaborn as sns

from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, GridSearchCV, RandomizedSearchCV, cross_val_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.svm import SVC
from sklearn.pipeline import Pipeline

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def load_data(symbol: str, timeframe: str, period: str, data_folder: str = 'real_data') -> pd.DataFrame:
    """
    Tải dữ liệu từ file CSV
    
    Args:
        symbol (str): Mã cặp giao dịch
        timeframe (str): Khung thời gian
        period (str): Khoảng thời gian dữ liệu
        data_folder (str): Thư mục chứa dữ liệu
        
    Returns:
        pd.DataFrame: DataFrame chứa dữ liệu
    """
    # Nếu là thư mục enhanced_data, sử dụng quy ước đặt tên khác
    if 'enhanced' in data_folder:
        data_path = os.path.join(data_folder, f"{symbol}_{timeframe}_{period}_enhanced.csv")
    else:
        data_path = os.path.join(data_folder, period, f"{symbol}_{timeframe}.csv")
    
    if not os.path.exists(data_path):
        logger.error(f"Không tìm thấy file dữ liệu: {data_path}")
        raise FileNotFoundError(f"Không tìm thấy file dữ liệu: {data_path}")
    
    logger.info(f"Đang tải dữ liệu từ {data_path}")
    df = pd.read_csv(data_path)
    
    # Chuyển đổi cột timestamp nếu có
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
    
    logger.info(f"Đã tải dữ liệu: {len(df)} dòng")
    return df

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tính toán các chỉ báo kỹ thuật
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu giá
        
    Returns:
        pd.DataFrame: DataFrame với các chỉ báo đã tính
    """
    logger.info("Đang tính toán các chỉ báo kỹ thuật...")
    
    # Copy DataFrame để tránh SettingWithCopyWarning
    df_indicators = df.copy()
    
    # RSI
    delta = df_indicators['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df_indicators['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = df_indicators['close'].ewm(span=12, adjust=False).mean()
    ema26 = df_indicators['close'].ewm(span=26, adjust=False).mean()
    df_indicators['macd'] = ema12 - ema26
    df_indicators['macd_signal'] = df_indicators['macd'].ewm(span=9, adjust=False).mean()
    df_indicators['macd_hist'] = df_indicators['macd'] - df_indicators['macd_signal']
    
    # Bollinger Bands
    df_indicators['sma20'] = df_indicators['close'].rolling(window=20).mean()
    df_indicators['bb_std'] = df_indicators['close'].rolling(window=20).std()
    df_indicators['bb_upper'] = df_indicators['sma20'] + 2 * df_indicators['bb_std']
    df_indicators['bb_lower'] = df_indicators['sma20'] - 2 * df_indicators['bb_std']
    df_indicators['bb_width'] = (df_indicators['bb_upper'] - df_indicators['bb_lower']) / df_indicators['sma20']
    
    # EMA
    df_indicators['ema_9'] = df_indicators['close'].ewm(span=9, adjust=False).mean()
    df_indicators['ema_21'] = df_indicators['close'].ewm(span=21, adjust=False).mean()
    df_indicators['ema_50'] = df_indicators['close'].ewm(span=50, adjust=False).mean()
    df_indicators['ema_200'] = df_indicators['close'].ewm(span=200, adjust=False).mean()
    
    # SMA
    df_indicators['sma_10'] = df_indicators['close'].rolling(window=10).mean()
    df_indicators['sma_50'] = df_indicators['close'].rolling(window=50).mean()
    df_indicators['sma_200'] = df_indicators['close'].rolling(window=200).mean()
    
    # ATR
    high_low = df_indicators['high'] - df_indicators['low']
    high_close = np.abs(df_indicators['high'] - df_indicators['close'].shift())
    low_close = np.abs(df_indicators['low'] - df_indicators['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df_indicators['atr'] = true_range.rolling(14).mean()
    
    # Stochastic
    low_14 = df_indicators['low'].rolling(window=14).min()
    high_14 = df_indicators['high'].rolling(window=14).max()
    df_indicators['stoch_k'] = 100 * ((df_indicators['close'] - low_14) / (high_14 - low_14))
    df_indicators['stoch_d'] = df_indicators['stoch_k'].rolling(window=3).mean()
    
    # OBV
    df_indicators['obv'] = (np.sign(df_indicators['close'].diff()) * df_indicators['volume']).fillna(0).cumsum()
    
    # Price Returns
    df_indicators['returns'] = df_indicators['close'].pct_change()
    df_indicators['log_returns'] = np.log(df_indicators['close'] / df_indicators['close'].shift(1))
    
    # Volatility
    df_indicators['volatility'] = df_indicators['returns'].rolling(window=14).std() * np.sqrt(14)
    
    # --- Feature Engineering Nâng Cao ---
    
    # RSI Divergence
    df_indicators['rsi_change'] = df_indicators['rsi'].diff()
    df_indicators['price_change'] = df_indicators['close'].diff()
    df_indicators['rsi_divergence'] = np.where(
        (df_indicators['rsi_change'] > 0) & (df_indicators['price_change'] < 0), 1,
        np.where((df_indicators['rsi_change'] < 0) & (df_indicators['price_change'] > 0), -1, 0)
    )
    
    # Momentum
    df_indicators['momentum'] = df_indicators['close'] - df_indicators['close'].shift(10)
    
    # Volume Pressure
    df_indicators['volume_ma'] = df_indicators['volume'].rolling(window=20).mean()
    df_indicators['volume_pressure'] = df_indicators['volume'] / df_indicators['volume_ma']
    
    # Price Distance from MA
    df_indicators['dist_from_200ma'] = (df_indicators['close'] - df_indicators['sma_200']) / df_indicators['sma_200']
    
    # Bollinger Squeeze
    df_indicators['bbands_squeeze'] = df_indicators['bb_width'].rolling(window=20).apply(
        lambda x: 1 if x.min() == x[-1] else 0
    )
    
    # Close Relative to Bollinger Bands
    df_indicators['close_to_bb_upper'] = (df_indicators['bb_upper'] - df_indicators['close']) / df_indicators['bb_std']
    df_indicators['close_to_bb_lower'] = (df_indicators['close'] - df_indicators['bb_lower']) / df_indicators['bb_std']
    
    # EMA Crossovers
    df_indicators['ema_9_21_cross'] = np.where(
        (df_indicators['ema_9'].shift(1) < df_indicators['ema_21'].shift(1)) & 
        (df_indicators['ema_9'] > df_indicators['ema_21']), 1,
        np.where(
            (df_indicators['ema_9'].shift(1) > df_indicators['ema_21'].shift(1)) & 
            (df_indicators['ema_9'] < df_indicators['ema_21']), -1, 0
        )
    )
    
    # Stochastic Crossovers
    df_indicators['stoch_cross'] = np.where(
        (df_indicators['stoch_k'].shift(1) < df_indicators['stoch_d'].shift(1)) & 
        (df_indicators['stoch_k'] > df_indicators['stoch_d']), 1,
        np.where(
            (df_indicators['stoch_k'].shift(1) > df_indicators['stoch_d'].shift(1)) & 
            (df_indicators['stoch_k'] < df_indicators['stoch_d']), -1, 0
        )
    )
    
    # MACD Crossovers
    df_indicators['macd_cross'] = np.where(
        (df_indicators['macd'].shift(1) < df_indicators['macd_signal'].shift(1)) & 
        (df_indicators['macd'] > df_indicators['macd_signal']), 1,
        np.where(
            (df_indicators['macd'].shift(1) > df_indicators['macd_signal'].shift(1)) & 
            (df_indicators['macd'] < df_indicators['macd_signal']), -1, 0
        )
    )
    
    # Volatility Change
    df_indicators['volatility_change'] = df_indicators['volatility'].pct_change()
    
    # OBV Rate of Change
    df_indicators['obv_roc'] = df_indicators['obv'].pct_change(periods=5)
    
    # Choke Points (Liquidity Gaps)
    high_max = df_indicators['high'].rolling(window=10).max()
    low_min = df_indicators['low'].rolling(window=10).min()
    df_indicators['price_range'] = high_max - low_min
    df_indicators['volume_per_range'] = df_indicators['volume'] / df_indicators['price_range']
    
    # Loại bỏ các hàng NaN
    df_indicators.dropna(inplace=True)
    
    logger.info(f"Đã tính toán {df_indicators.shape[1] - 6} chỉ báo kỹ thuật")
    
    return df_indicators

def create_target(df: pd.DataFrame, prediction_days: int = 1) -> pd.DataFrame:
    """
    Tạo biến mục tiêu cho mô hình
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu giá và chỉ báo
        prediction_days (int): Số ngày dự đoán
        
    Returns:
        pd.DataFrame: DataFrame với biến mục tiêu
    """
    logger.info(f"Đang tạo biến mục tiêu cho {prediction_days} ngày...")
    
    # Copy DataFrame để tránh SettingWithCopyWarning
    df_target = df.copy()
    
    # Tạo biến mục tiêu là hướng giá trong n ngày tới
    df_target['future_close'] = df_target['close'].shift(-prediction_days)
    df_target['target'] = np.where(df_target['future_close'] > df_target['close'], 1, 0)
    
    # Loại bỏ các hàng NaN cuối cùng do shift
    df_target.dropna(inplace=True)
    
    logger.info(f"Đã tạo biến mục tiêu, còn lại {len(df_target)} dòng dữ liệu")
    
    return df_target

def prepare_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Chuẩn bị đặc trưng cho mô hình
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu và biến mục tiêu
        
    Returns:
        Tuple[pd.DataFrame, pd.Series]: (X_features, y_target)
    """
    logger.info("Đang chuẩn bị đặc trưng...")
    
    # Lọc ra các cột thời gian và metadata không dùng cho mô hình
    columns_to_drop = [
        'timestamp', 'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore',
        'open', 'high', 'low', 'close', 'volume', 'future_close', 'target'
    ]
    
    # Chỉ loại bỏ các cột tồn tại trong df
    drop_cols = [col for col in columns_to_drop if col in df.columns]
    feature_columns = df.columns.difference(drop_cols)
    
    X = df[feature_columns]
    y = df['target']
    
    logger.info(f"Đã chuẩn bị {len(feature_columns)} đặc trưng")
    
    return X, y

def perform_grid_search(X_train: pd.DataFrame, y_train: pd.Series, model_type: str) -> Dict:
    """
    Thực hiện Grid Search để tìm hyperparameters tối ưu
    
    Args:
        X_train (pd.DataFrame): Đặc trưng huấn luyện
        y_train (pd.Series): Mục tiêu huấn luyện
        model_type (str): Loại mô hình
        
    Returns:
        Dict: Kết quả Grid Search
    """
    logger.info(f"Đang thực hiện Grid Search cho mô hình {model_type}...")
    
    if model_type == 'random_forest':
        model = RandomForestClassifier(random_state=42)
        param_grid = {
            'n_estimators': [100, 200, 300],
            'max_depth': [None, 10, 20, 30],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4],
            'max_features': ['sqrt', 'log2', None]
        }
    elif model_type == 'gradient_boosting':
        model = GradientBoostingClassifier(random_state=42)
        param_grid = {
            'n_estimators': [100, 200, 300],
            'learning_rate': [0.01, 0.05, 0.1, 0.2],
            'max_depth': [3, 5, 7, 9],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4],
            'subsample': [0.8, 0.9, 1.0]
        }
    elif model_type == 'svm':
        model = SVC(probability=True, random_state=42)
        param_grid = {
            'C': [0.1, 1, 10, 100],
            'kernel': ['linear', 'rbf', 'poly'],
            'gamma': ['scale', 'auto', 0.1, 0.01]
        }
    else:
        logger.error(f"Loại mô hình không hợp lệ: {model_type}")
        raise ValueError(f"Loại mô hình không hợp lệ: {model_type}")
    
    # Sử dụng RandomizedSearchCV để tăng tốc quá trình tìm kiếm
    grid_search = RandomizedSearchCV(
        model, param_grid, cv=5, scoring='accuracy',
        n_iter=20, random_state=42, n_jobs=-1, verbose=1
    )
    
    # Huấn luyện
    grid_search.fit(X_train, y_train)
    
    logger.info(f"Đã tìm thấy tham số tốt nhất: {grid_search.best_params_}")
    logger.info(f"Độ chính xác tốt nhất: {grid_search.best_score_:.4f}")
    
    return {
        'best_params': grid_search.best_params_,
        'best_score': grid_search.best_score_,
        'model': grid_search.best_estimator_
    }

def train_ensemble_model(X_train: pd.DataFrame, y_train: pd.Series, 
                        model_params: Dict[str, Dict]) -> Dict:
    """
    Huấn luyện mô hình ensemble kết hợp nhiều mô hình
    
    Args:
        X_train (pd.DataFrame): Đặc trưng huấn luyện
        y_train (pd.Series): Mục tiêu huấn luyện
        model_params (Dict[str, Dict]): Tham số tối ưu cho từng mô hình
        
    Returns:
        Dict: Kết quả huấn luyện
    """
    logger.info("Đang huấn luyện mô hình ensemble...")
    
    # Khởi tạo các mô hình cơ sở với tham số tối ưu
    rf_model = RandomForestClassifier(random_state=42, **model_params['random_forest']['best_params'])
    gb_model = GradientBoostingClassifier(random_state=42, **model_params['gradient_boosting']['best_params'])
    svm_model = SVC(probability=True, random_state=42, **model_params['svm']['best_params'])
    
    # Tạo mô hình ensemble với voting soft (sử dụng xác suất)
    ensemble = VotingClassifier(
        estimators=[
            ('rf', rf_model),
            ('gb', gb_model),
            ('svm', svm_model)
        ],
        voting='soft',
        weights=[2, 1, 1]  # Trọng số lớn hơn cho RandomForest vì thường có hiệu suất tốt nhất
    )
    
    # Huấn luyện
    ensemble.fit(X_train, y_train)
    
    # Đánh giá cross-validation
    cv_scores = cross_val_score(ensemble, X_train, y_train, cv=5, scoring='accuracy')
    
    logger.info(f"Độ chính xác 5-fold CV của ensemble: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    
    return {
        'model': ensemble,
        'cv_scores': {
            'mean': cv_scores.mean(),
            'std': cv_scores.std(),
            'scores': cv_scores.tolist()
        }
    }

def evaluate_model(model: Any, X_test: pd.DataFrame, y_test: pd.Series) -> Dict:
    """
    Đánh giá hiệu suất mô hình
    
    Args:
        model (Any): Mô hình đã huấn luyện
        X_test (pd.DataFrame): Đặc trưng kiểm thử
        y_test (pd.Series): Mục tiêu kiểm thử
        
    Returns:
        Dict: Metrics đánh giá
    """
    logger.info("Đang đánh giá hiệu suất mô hình...")
    
    # Dự đoán
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    
    # Tính metrics
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)
    
    logger.info(f"Độ chính xác: {acc:.4f}")
    logger.info(f"Precision: {prec:.4f}")
    logger.info(f"Recall: {rec:.4f}")
    logger.info(f"F1-score: {f1:.4f}")
    logger.info(f"Confusion Matrix:\n{cm}")
    
    return {
        'accuracy': acc,
        'precision': prec,
        'recall': rec,
        'f1_score': f1,
        'confusion_matrix': cm.tolist(),
        'predictions': {
            'y_true': y_test.tolist(),
            'y_pred': y_pred.tolist(),
            'y_prob': y_prob.tolist()
        }
    }

def create_charts(df: pd.DataFrame, result: Dict, symbol: str, timeframe: str, 
                period: str, prediction_days: int, output_folder: str) -> Dict:
    """
    Tạo biểu đồ hiệu suất và phân tích
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu
        result (Dict): Kết quả đánh giá
        symbol (str): Mã cặp giao dịch
        timeframe (str): Khung thời gian
        period (str): Khoảng thời gian dữ liệu
        prediction_days (int): Số ngày dự đoán
        output_folder (str): Thư mục lưu biểu đồ
        
    Returns:
        Dict: Đường dẫn đến các biểu đồ
    """
    logger.info("Đang tạo biểu đồ...")
    
    os.makedirs(output_folder, exist_ok=True)
    
    # Biểu đồ giá và dự đoán
    price_chart_path = os.path.join(output_folder, f"{symbol}_{timeframe}_{period}_optimized_price_predictions.png")
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Chỉ hiển thị 100 điểm dữ liệu cuối cùng để dễ nhìn
    plot_df = df.copy().iloc[-100:]
    
    # Thêm thông tin dự đoán vào DataFrame
    y_true = result['predictions']['y_true'][-100:]
    y_pred = result['predictions']['y_pred'][-100:]
    y_prob = result['predictions']['y_prob'][-100:]
    
    # Plot giá đóng cửa
    ax.plot(plot_df.index, plot_df['close'], label='Giá đóng cửa', color='blue')
    
    # Plot dự đoán tăng và giảm
    for i in range(len(plot_df.index) - 1):
        if i >= len(y_pred):
            break
            
        if y_pred[i] == 1:  # Dự đoán tăng
            ax.scatter(plot_df.index[i], plot_df['close'].iloc[i], color='green', marker='^', s=100)
        else:  # Dự đoán giảm
            ax.scatter(plot_df.index[i], plot_df['close'].iloc[i], color='red', marker='v', s=100)
    
    ax.set_title(f'Giá {symbol} và dự đoán ({timeframe}, {period})')
    ax.set_xlabel('Thời gian')
    ax.set_ylabel('Giá')
    ax.legend()
    ax.grid(True)
    plt.tight_layout()
    plt.savefig(price_chart_path)
    plt.close()
    
    # Biểu đồ confusion matrix
    cm_chart_path = os.path.join(output_folder, f"{symbol}_{timeframe}_{period}_optimized_confusion_matrix.png")
    
    fig, ax = plt.subplots(figsize=(8, 6))
    cm = result['confusion_matrix']
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax)
    ax.set_title(f'Confusion Matrix - {symbol} ({timeframe}, {period})')
    ax.set_xlabel('Dự đoán')
    ax.set_ylabel('Thực tế')
    ax.set_xticklabels(['Giảm', 'Tăng'])
    ax.set_yticklabels(['Giảm', 'Tăng'])
    plt.tight_layout()
    plt.savefig(cm_chart_path)
    plt.close()
    
    # Biểu đồ độ quan trọng của đặc trưng
    if hasattr(result.get('ensemble_model', {}), 'estimators_'):
        importances = {}
        # Chỉ lấy feature importance từ RandomForest và GradientBoosting
        for i, est_name in enumerate(['rf', 'gb']):
            if hasattr(result['ensemble_model'].estimators_[i], 'feature_importances_'):
                imp = result['ensemble_model'].estimators_[i].feature_importances_
                importances[est_name] = dict(zip(X_train.columns, imp))
        
        # Tạo biểu đồ cho từng mô hình
        for est_name, imp_dict in importances.items():
            # Sắp xếp theo độ quan trọng giảm dần và lấy top 20
            sorted_imp = dict(sorted(imp_dict.items(), key=lambda x: x[1], reverse=True)[:20])
            
            fi_chart_path = os.path.join(output_folder, f"{symbol}_{timeframe}_{period}_optimized_{est_name}_feature_importance.png")
            
            fig, ax = plt.subplots(figsize=(10, 8))
            y_pos = np.arange(len(sorted_imp))
            ax.barh(y_pos, list(sorted_imp.values()), align='center')
            ax.set_yticks(y_pos)
            ax.set_yticklabels(list(sorted_imp.keys()))
            ax.invert_yaxis()  # Đặt giá trị lớn nhất ở trên cùng
            ax.set_title(f'Top 20 đặc trưng quan trọng - {est_name.upper()} ({timeframe}, {period})')
            ax.set_xlabel('Độ quan trọng')
            plt.tight_layout()
            plt.savefig(fi_chart_path)
            plt.close()
    
    # Biểu đồ phân phối xác suất dự đoán
    prob_chart_path = os.path.join(output_folder, f"{symbol}_{timeframe}_{period}_optimized_probability_dist.png")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Phân tách xác suất theo nhãn thực tế
    y_true_array = np.array(result['predictions']['y_true'])
    y_prob_array = np.array(result['predictions']['y_prob'])
    
    prob_true_pos = y_prob_array[y_true_array == 1]
    prob_true_neg = y_prob_array[y_true_array == 0]
    
    # Vẽ histogram
    ax.hist(prob_true_pos, bins=20, alpha=0.7, color='green', label='Thực tế: Tăng')
    ax.hist(prob_true_neg, bins=20, alpha=0.7, color='red', label='Thực tế: Giảm')
    
    ax.axvline(x=0.5, color='black', linestyle='--', alpha=0.7)
    ax.set_title(f'Phân phối xác suất dự đoán - {symbol} ({timeframe}, {period})')
    ax.set_xlabel('Xác suất dự đoán tăng')
    ax.set_ylabel('Số lượng')
    ax.legend()
    plt.tight_layout()
    plt.savefig(prob_chart_path)
    plt.close()
    
    # Biểu đồ so sánh các mô hình
    models_chart_path = os.path.join(output_folder, f"{symbol}_{timeframe}_{period}_optimized_model_comparison.png")
    
    if 'model_comparison' in result:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        models = list(result['model_comparison'].keys())
        accuracies = [result['model_comparison'][m]['accuracy'] for m in models]
        
        ax.bar(models, accuracies, color=['blue', 'orange', 'green', 'red'])
        
        for i, v in enumerate(accuracies):
            ax.text(i, v + 0.01, f"{v:.4f}", ha='center')
        
        ax.set_title(f'So sánh độ chính xác các mô hình - {symbol} ({timeframe}, {period})')
        ax.set_xlabel('Mô hình')
        ax.set_ylabel('Độ chính xác')
        ax.set_ylim(0.5, max(accuracies) + 0.1)
        plt.tight_layout()
        plt.savefig(models_chart_path)
        plt.close()
    
    chart_paths = {
        'price_predictions': price_chart_path,
        'confusion_matrix': cm_chart_path,
        'probability_distribution': prob_chart_path
    }
    
    # Thêm đường dẫn feature importance nếu có
    if hasattr(result.get('ensemble_model', {}), 'estimators_'):
        for est_name in importances.keys():
            chart_paths[f'{est_name}_feature_importance'] = os.path.join(
                output_folder, f"{symbol}_{timeframe}_{period}_optimized_{est_name}_feature_importance.png"
            )
    
    # Thêm đường dẫn so sánh mô hình nếu có
    if 'model_comparison' in result:
        chart_paths['model_comparison'] = models_chart_path
    
    logger.info(f"Đã tạo {len(chart_paths)} biểu đồ")
    
    return chart_paths

def save_results(result: Dict, symbol: str, timeframe: str, period: str, 
               prediction_days: int, output_folder: str, model_path: str = None) -> str:
    """
    Lưu kết quả vào file JSON
    
    Args:
        result (Dict): Kết quả đánh giá
        symbol (str): Mã cặp giao dịch
        timeframe (str): Khung thời gian
        period (str): Khoảng thời gian dữ liệu
        prediction_days (int): Số ngày dự đoán
        output_folder (str): Thư mục lưu kết quả
        model_path (str, optional): Đường dẫn đến file mô hình
        
    Returns:
        str: Đường dẫn đến file kết quả
    """
    logger.info("Đang lưu kết quả...")
    
    os.makedirs(output_folder, exist_ok=True)
    
    # Tạo đối tượng kết quả
    result_obj = {
        'symbol': symbol,
        'timeframe': timeframe,
        'period': period,
        'prediction_days': prediction_days,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'accuracy': result['accuracy'],
        'precision': result['precision'],
        'recall': result['recall'],
        'f1_score': result['f1_score'],
        'confusion_matrix': result['confusion_matrix'],
        'charts': result.get('charts', {}),
        'model_path': model_path,
        'model_comparison': result.get('model_comparison', {})
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
    result_path = os.path.join(output_folder, f"{symbol}_{timeframe}_{period}_{prediction_days}d_optimized_results.json")
    with open(result_path, 'w') as f:
        json.dump(result_obj, f, indent=2)
    
    logger.info(f"Đã lưu kết quả tại {result_path}")
    
    return result_path

def optimize_and_evaluate(symbol: str, timeframe: str, period: str, prediction_days: int = 1,
                        data_folder: str = 'real_data', output_folder: str = 'ml_results',
                        charts_folder: str = 'ml_charts', models_folder: str = 'ml_models') -> str:
    """
    Tối ưu hóa và đánh giá mô hình ML
    
    Args:
        symbol (str): Mã cặp giao dịch
        timeframe (str): Khung thời gian
        period (str): Khoảng thời gian dữ liệu
        prediction_days (int): Số ngày dự đoán
        data_folder (str): Thư mục chứa dữ liệu
        output_folder (str): Thư mục lưu kết quả
        charts_folder (str): Thư mục lưu biểu đồ
        models_folder (str): Thư mục lưu mô hình
        
    Returns:
        str: Đường dẫn đến file kết quả
    """
    # Tạo các thư mục nếu chưa tồn tại
    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(charts_folder, exist_ok=True)
    os.makedirs(models_folder, exist_ok=True)
    
    # Bước 1: Tải dữ liệu
    df = load_data(symbol, timeframe, period, data_folder)
    
    # Bước 2: Tính toán chỉ báo và feature engineering
    df_indicators = calculate_indicators(df)
    
    # Bước 3: Tạo biến mục tiêu
    df_with_target = create_target(df_indicators, prediction_days)
    
    # Bước 4: Chuẩn bị đặc trưng
    X, y = prepare_features(df_with_target)
    
    # Bước 5: Chia tập huấn luyện và kiểm thử
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    # Bước 6: Chuẩn hóa dữ liệu
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Bước 7: Tối ưu hóa hyperparameter cho từng mô hình
    model_params = {}
    for model_type in ['random_forest', 'gradient_boosting', 'svm']:
        logger.info(f"Đang tối ưu hóa mô hình {model_type}...")
        model_params[model_type] = perform_grid_search(X_train_scaled, y_train, model_type)
    
    # Bước 8: Huấn luyện mô hình ensemble
    ensemble_result = train_ensemble_model(X_train_scaled, y_train, model_params)
    
    # Bước 9: Đánh giá từng mô hình và ensemble
    evaluation_results = {}
    model_comparison = {}
    
    # Đánh giá Random Forest
    rf_model = model_params['random_forest']['model']
    rf_eval = evaluate_model(rf_model, X_test_scaled, y_test)
    model_comparison['random_forest'] = {
        'accuracy': rf_eval['accuracy'],
        'precision': rf_eval['precision'],
        'recall': rf_eval['recall'],
        'f1_score': rf_eval['f1_score']
    }
    
    # Đánh giá Gradient Boosting
    gb_model = model_params['gradient_boosting']['model']
    gb_eval = evaluate_model(gb_model, X_test_scaled, y_test)
    model_comparison['gradient_boosting'] = {
        'accuracy': gb_eval['accuracy'],
        'precision': gb_eval['precision'],
        'recall': gb_eval['recall'],
        'f1_score': gb_eval['f1_score']
    }
    
    # Đánh giá SVM
    svm_model = model_params['svm']['model']
    svm_eval = evaluate_model(svm_model, X_test_scaled, y_test)
    model_comparison['svm'] = {
        'accuracy': svm_eval['accuracy'],
        'precision': svm_eval['precision'],
        'recall': svm_eval['recall'],
        'f1_score': svm_eval['f1_score']
    }
    
    # Đánh giá Ensemble
    ensemble_model = ensemble_result['model']
    ensemble_eval = evaluate_model(ensemble_model, X_test_scaled, y_test)
    model_comparison['ensemble'] = {
        'accuracy': ensemble_eval['accuracy'],
        'precision': ensemble_eval['precision'],
        'recall': ensemble_eval['recall'],
        'f1_score': ensemble_eval['f1_score']
    }
    
    # Tìm mô hình tốt nhất
    best_model_name = max(model_comparison.items(), key=lambda x: x[1]['accuracy'])[0]
    best_model = {
        'random_forest': rf_model,
        'gradient_boosting': gb_model,
        'svm': svm_model,
        'ensemble': ensemble_model
    }[best_model_name]
    
    best_eval = {
        'random_forest': rf_eval,
        'gradient_boosting': gb_eval,
        'svm': svm_eval,
        'ensemble': ensemble_eval
    }[best_model_name]
    
    logger.info(f"Mô hình tốt nhất: {best_model_name} với độ chính xác {best_eval['accuracy']:.4f}")
    
    # Bước 10: Tạo biểu đồ
    chart_paths = create_charts(
        df_with_target, best_eval, symbol, timeframe, period, 
        prediction_days, charts_folder
    )
    
    # Bước 11: Lưu kết quả và mô hình
    # Lưu mô hình tốt nhất
    import joblib
    model_path = os.path.join(models_folder, f"{symbol}_{timeframe}_{period}_{prediction_days}d_optimized_{best_model_name}_model.joblib")
    joblib.dump({
        'model': best_model,
        'scaler': scaler,
        'feature_columns': list(X.columns)
    }, model_path)
    
    # Thêm thông tin vào kết quả
    best_eval['charts'] = chart_paths
    best_eval['model_comparison'] = model_comparison
    best_eval['best_model'] = best_model_name
    best_eval['ensemble_model'] = ensemble_model if best_model_name == 'ensemble' else None
    
    # Lưu kết quả
    result_path = save_results(
        best_eval, symbol, timeframe, period, prediction_days,
        output_folder, model_path
    )
    
    logger.info(f"Tối ưu hóa và đánh giá hoàn thành! Kết quả được lưu tại: {result_path}")
    
    return result_path

def main():
    parser = argparse.ArgumentParser(description='Tối ưu hóa mô hình ML cho bot giao dịch Bitcoin')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Mã cặp giao dịch')
    parser.add_argument('--timeframe', type=str, default='1h', help='Khung thời gian (1h, 4h, 1d)')
    parser.add_argument('--period', type=str, default='3_months', help='Khoảng thời gian dữ liệu (1_month, 3_months, 6_months)')
    parser.add_argument('--prediction_days', type=int, default=1, help='Số ngày dự đoán xu hướng')
    parser.add_argument('--data_folder', type=str, default='real_data', help='Thư mục chứa dữ liệu')
    parser.add_argument('--output_folder', type=str, default='ml_results', help='Thư mục lưu kết quả')
    parser.add_argument('--charts_folder', type=str, default='ml_charts', help='Thư mục lưu biểu đồ')
    parser.add_argument('--models_folder', type=str, default='ml_models', help='Thư mục lưu mô hình')
    
    args = parser.parse_args()
    
    result_path = optimize_and_evaluate(
        args.symbol, args.timeframe, args.period, args.prediction_days,
        args.data_folder, args.output_folder, args.charts_folder, args.models_folder
    )
    
    print(f"Tối ưu hóa hoàn thành! Kết quả được lưu tại: {result_path}")

if __name__ == "__main__":
    main()