#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script huấn luyện các mô hình học máy nâng cao cho giao dịch tiền điện tử
Hỗ trợ nhiều loại mô hình và chế độ thị trường khác nhau
"""

import os
import logging
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

from app.binance_api import BinanceAPI
from app.data_processor import DataProcessor
from app.simple_feature_engineering import SimpleFeatureEngineering
from app.market_regime_detector import MarketRegimeDetector
from app.advanced_ml_optimizer import AdvancedMLOptimizer

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('train_ml_models')

def parse_arguments():
    """Phân tích đối số dòng lệnh"""
    parser = argparse.ArgumentParser(description='Huấn luyện các mô hình học máy cho giao dịch tiền điện tử')
    
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Cặp giao dịch cần huấn luyện')
    parser.add_argument('--interval', type=str, default='1h', help='Khung thời gian (1m, 5m, 15m, 1h, 4h, 1d)')
    parser.add_argument('--days', type=int, default=90, help='Số ngày dữ liệu lịch sử cần lấy')
    parser.add_argument('--models', type=str, nargs='+', default=['random_forest', 'gradient_boosting', 'neural_network'],
                        help='Các loại mô hình cần huấn luyện')
    parser.add_argument('--regime-models', action='store_true', help='Huấn luyện mô hình riêng cho mỗi chế độ thị trường')
    parser.add_argument('--feature-selection', action='store_true', help='Sử dụng lựa chọn tính năng tự động')
    parser.add_argument('--ensemble', action='store_true', help='Sử dụng kỹ thuật ensemble để kết hợp dự đoán')
    parser.add_argument('--output-dir', type=str, default='models', help='Thư mục xuất mô hình')
    parser.add_argument('--backtest', action='store_true', help='Chạy backtest sau khi huấn luyện')
    parser.add_argument('--plot', action='store_true', help='Vẽ đồ thị kết quả')
    
    return parser.parse_args()

def collect_training_data(api, symbol, interval, days):
    """Thu thập dữ liệu để huấn luyện"""
    
    logger.info(f"Thu thập dữ liệu cho {symbol} trên khung thời gian {interval}, {days} ngày")
    
    # Khởi tạo DataProcessor
    data_processor = DataProcessor(api, simulation_mode=True)
    
    # Lấy dữ liệu
    df = data_processor.get_historical_data(symbol, interval, lookback_days=days)
    
    if df is None or len(df) == 0:
        logger.error("Không thể thu thập dữ liệu!")
        return None
    
    logger.info(f"Đã thu thập {len(df)} mẫu dữ liệu")
    
    # Thêm các tính năng bổ sung
    feature_eng = SimpleFeatureEngineering()
    df = feature_eng.add_all_features(df)
    
    # Xác định chế độ thị trường cho mỗi mẫu
    regime_detector = MarketRegimeDetector()
    
    # Thêm cột chế độ thị trường
    regimes = []
    
    # Sử dụng cửa sổ trượt để xác định chế độ thị trường cho mỗi điểm dữ liệu
    window_size = 60  # Kích thước cửa sổ để xác định chế độ
    
    for i in range(len(df)):
        if i < window_size:
            regimes.append('neutral')  # Chế độ mặc định cho các điểm đầu tiên
        else:
            window_df = df.iloc[i-window_size:i].copy()
            regime = regime_detector.detect_regime(window_df)
            regimes.append(regime)
    
    df['market_regime'] = regimes
    
    return df

def prepare_data(df, lookahead=1, threshold=0):
    """Chuẩn bị dữ liệu cho huấn luyện"""
    
    # Loại bỏ các cột không cần thiết
    cols_to_drop = ['open_time', 'close_time', 'datetime', 'date', 'time']
    feature_cols = [col for col in df.columns if col not in cols_to_drop]
    
    # Tạo cột mục tiêu
    df['future_return'] = df['close'].shift(-lookahead) / df['close'] - 1
    
    # Tạo nhãn
    df['target'] = 0
    df.loc[df['future_return'] > threshold, 'target'] = 1  # Tăng
    df.loc[df['future_return'] < -threshold, 'target'] = -1  # Giảm
    
    # Chỉ giữ lại các hàng có đủ dữ liệu
    df_clean = df.dropna().copy()
    
    # Tạo X (tính năng) và y (mục tiêu)
    target_cols = ['target', 'future_return', 'market_regime']
    X = df_clean[[col for col in feature_cols if col not in target_cols]].copy()
    y = df_clean['target'].values
    
    # Xử lý giá trị thiếu và vô cùng
    X = X.fillna(0)
    X = X.replace([np.inf, -np.inf], 0)
    
    return X, y, df_clean['market_regime'].values, df_clean

def train_by_regime(ml_optimizer, X, y, regimes):
    """Huấn luyện các mô hình cho mỗi chế độ thị trường riêng biệt"""
    
    # Tạo dictionary để lưu chỉ mục cho mỗi chế độ
    regime_indices = {}
    unique_regimes = np.unique(regimes)
    
    for regime in unique_regimes:
        regime_indices[regime] = np.where(regimes == regime)[0]
        logger.info(f"Chế độ {regime}: {len(regime_indices[regime])} mẫu")
    
    # Huấn luyện mô hình cho mỗi chế độ
    for regime, indices in regime_indices.items():
        if len(indices) < 50:  # Bỏ qua nếu không có đủ dữ liệu
            logger.warning(f"Bỏ qua huấn luyện cho chế độ {regime} do không đủ dữ liệu ({len(indices)} mẫu)")
            continue
            
        logger.info(f"Huấn luyện mô hình cho chế độ {regime} với {len(indices)} mẫu")
        X_regime = X.iloc[indices]
        y_regime = y[indices]
        
        # Huấn luyện mô hình
        try:
            metrics = ml_optimizer.train_models(X_regime, y_regime, regime=regime)
            logger.info(f"Kết quả huấn luyện cho chế độ {regime}:")
            for model_key, model_metrics in metrics.items():
                logger.info(f"  {model_key}: Accuracy={model_metrics['accuracy']:.4f}, F1={model_metrics['f1_score']:.4f}")
        except Exception as e:
            logger.error(f"Lỗi khi huấn luyện mô hình cho chế độ {regime}: {str(e)}")
    
    return ml_optimizer

def train_general_model(ml_optimizer, X, y):
    """Huấn luyện mô hình chung cho tất cả các dữ liệu"""
    
    logger.info(f"Huấn luyện mô hình chung với {len(X)} mẫu")
    
    try:
        metrics = ml_optimizer.train_models(X, y)
        logger.info("Kết quả huấn luyện mô hình chung:")
        for model_key, model_metrics in metrics.items():
            logger.info(f"  {model_key}: Accuracy={model_metrics['accuracy']:.4f}, F1={model_metrics['f1_score']:.4f}")
    except Exception as e:
        logger.error(f"Lỗi khi huấn luyện mô hình chung: {str(e)}")
    
    return ml_optimizer

def backtest_model(ml_optimizer, df, output_dir=None):
    """Chạy backtest với mô hình đã huấn luyện"""
    
    logger.info("Bắt đầu backtest mô hình...")
    
    # Chạy backtest
    results = ml_optimizer.backtest_strategy(df)
    
    if results is None:
        logger.error("Backtest thất bại")
        return None
    
    # Hiển thị kết quả
    logger.info(f"Kết quả backtest:")
    logger.info(f"Số dư ban đầu: ${results['initial_balance']:.2f}")
    logger.info(f"Số dư cuối cùng: ${results['final_balance']:.2f}")
    logger.info(f"Lợi nhuận: {results['total_return']:.2f}%")
    logger.info(f"Drawdown tối đa: {results['max_drawdown']:.2f}%")
    logger.info(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    logger.info(f"Số giao dịch: {results['n_trades']}")
    logger.info(f"Tỷ lệ thắng: {results['win_rate']:.2f}%")
    
    # Vẽ đồ thị nếu cần
    if args.plot:
        plot_backtest_results(results, df, output_dir)
    
    return results

def plot_backtest_results(results, df, output_dir=None):
    """Vẽ đồ thị kết quả backtest"""
    
    plt.figure(figsize=(14, 10))
    
    # Đồ thị 1: Equity Curve
    plt.subplot(2, 1, 1)
    plt.plot(results['equity_curve'])
    plt.title('Equity Curve')
    plt.grid(True)
    
    # Đồ thị 2: Giá và Tín hiệu
    plt.subplot(2, 1, 2)
    plt.plot(df['close'].values)
    
    # Đánh dấu tín hiệu mua/bán
    buy_signals = np.where(results['predictions'] == 1)[0]
    sell_signals = np.where(results['predictions'] == -1)[0]
    
    plt.scatter(buy_signals, df['close'].values[buy_signals], color='green', marker='^', alpha=0.7)
    plt.scatter(sell_signals, df['close'].values[sell_signals], color='red', marker='v', alpha=0.7)
    
    plt.title('Price Chart with Signals')
    plt.grid(True)
    
    plt.tight_layout()
    
    # Lưu hoặc hiển thị
    if output_dir:
        output_file = os.path.join(output_dir, f'backtest_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
        plt.savefig(output_file)
        logger.info(f"Đã lưu đồ thị kết quả vào {output_file}")
    else:
        plt.show()
    
    plt.close()

def main(args):
    """Hàm chính"""
    
    # Tạo thư mục xuất nếu chưa tồn tại
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Khởi tạo Binance API
    api = BinanceAPI()
    
    # Thu thập dữ liệu
    df = collect_training_data(api, args.symbol, args.interval, args.days)
    
    if df is None:
        logger.error("Không thể tiếp tục do thiếu dữ liệu")
        return
    
    # Chuẩn bị dữ liệu
    X, y, regimes, df_clean = prepare_data(df)
    
    # Khởi tạo ML Optimizer
    ml_optimizer = AdvancedMLOptimizer(
        base_models=args.models,
        use_model_per_regime=args.regime_models,
        feature_selection=args.feature_selection,
        use_ensemble=args.ensemble
    )
    
    # Huấn luyện mô hình
    if args.regime_models:
        ml_optimizer = train_by_regime(ml_optimizer, X, y, regimes)
    else:
        ml_optimizer = train_general_model(ml_optimizer, X, y)
    
    # Lưu mô hình
    model_path = ml_optimizer.save_models(args.output_dir)
    logger.info(f"Đã lưu mô hình vào {model_path}")
    
    # Chạy backtest nếu cần
    if args.backtest:
        backtest_model(ml_optimizer, df_clean, args.output_dir)
    
    logger.info("Huấn luyện hoàn tất")

if __name__ == "__main__":
    args = parse_arguments()
    main(args)