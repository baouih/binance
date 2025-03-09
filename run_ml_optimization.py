"""
Script chạy tối ưu hóa chiến lược bằng học máy

Script này thực hiện:
1. Tải kết quả backtest từ các lần chạy trước
2. Huấn luyện mô hình học máy để dự đoán tham số tối ưu
3. Tạo chiến lược tối ưu cho từng chế độ thị trường
4. Lưu kết quả tối ưu hóa để sử dụng trong giao dịch thực
"""

import os
import sys
import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from typing import List, Dict, Tuple, Any, Optional, Union

# Thêm thư mục gốc vào đường dẫn
sys.path.append('.')

# Import các module cần thiết
from ml_optimizer import MLOptimizer
from market_regime_detector import MarketRegimeDetector

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ml_optimization.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ml_optimization")

def visualize_parameter_impact(optimizer: MLOptimizer, strategy: str, param_name: str,
                           market_regimes: List[str], target_metric: str = 'sharpe_ratio'):
    """
    Hiển thị ảnh hưởng của tham số đến hiệu suất
    
    Args:
        optimizer (MLOptimizer): Đối tượng ML Optimizer
        strategy (str): Tên chiến lược
        param_name (str): Tên tham số
        market_regimes (List[str]): Danh sách chế độ thị trường
        target_metric (str): Chỉ số mục tiêu
    """
    try:
        # Kiểm tra nếu chưa có mô hình
        if not optimizer.models:
            loaded = optimizer.load_models(target_metric)
            if not loaded:
                logger.warning("Không có mô hình để tạo biểu đồ")
                return
        
        # Lấy tham số hiện tại
        if strategy not in optimizer.strategy_params:
            logger.warning(f"Không có tham số cho chiến lược {strategy}")
            return
            
        current_params = optimizer.strategy_params[strategy]
        
        if param_name not in current_params:
            logger.warning(f"Không có tham số {param_name} trong chiến lược {strategy}")
            return
            
        current_value = current_params[param_name]
        
        # Tạo range các giá trị cần thử
        if isinstance(current_value, int):
            # Tham số nguyên
            param_range = list(range(
                max(1, int(current_value * 0.5)),
                int(current_value * 2.0) + 1,
                max(1, int(current_value * 0.1))
            ))
        elif isinstance(current_value, float):
            # Tham số thực
            param_range = np.linspace(
                max(0.01, current_value * 0.5),
                current_value * 2.0,
                20
            )
        else:
            # Skip non-numeric parameters
            logger.warning(f"Tham số {param_name} không phải số, không thể tạo biểu đồ")
            return
        
        # Tạo biểu đồ
        plt.figure(figsize=(12, 8))
        
        for market_regime in market_regimes:
            scores = []
            
            for value in param_range:
                # Tạo bản sao tham số
                test_params = current_params.copy()
                test_params[param_name] = value
                
                # Dự đoán điểm số
                modified_params = optimizer.predict_optimal_parameters(
                    strategy=strategy,
                    market_regime=market_regime,
                    current_params=test_params,
                    target_metric=target_metric
                )
                
                # Lấy điểm số từ mô hình
                if strategy in optimizer.models:
                    model = optimizer.models[strategy]
                    scaler = optimizer.scalers[strategy]
                elif 'global' in optimizer.models:
                    model = optimizer.models['global']
                    scaler = optimizer.scalers['global']
                else:
                    logger.warning(f"Không có mô hình cho chiến lược {strategy}")
                    return
                
                # Tạo feature vector
                features = {}
                
                # Thêm tham số
                for p_name, p_value in test_params.items():
                    if isinstance(p_value, (int, float)):
                        features[f'param_{p_name}'] = p_value
                
                # Thêm one-hot encoding cho các biến phân loại
                if market_regime in optimizer.market_regimes:
                    for regime in optimizer.market_regimes:
                        features[f'regime_{regime}'] = 1 if regime == market_regime else 0
                
                # Chuyển đổi thành numpy array
                feature_names = sorted(features.keys())
                feature_values = [features[name] for name in feature_names]
                X = np.array([feature_values])
                
                # Chuẩn hóa
                X_scaled = scaler.transform(X)
                
                # Dự đoán
                score = model.predict(X_scaled)[0]
                scores.append(score)
            
            # Vẽ đường
            plt.plot(param_range, scores, label=f"Chế độ: {market_regime}", marker='o')
        
        plt.title(f"Ảnh hưởng của tham số {param_name} trong chiến lược {strategy}")
        plt.xlabel(f"Giá trị {param_name}")
        plt.ylabel(f"Điểm số {target_metric}")
        plt.grid(True)
        plt.legend()
        
        # Lưu biểu đồ
        chart_dir = "ml_charts"
        os.makedirs(chart_dir, exist_ok=True)
        chart_path = os.path.join(chart_dir, f"{strategy}_{param_name}_impact.png")
        plt.savefig(chart_path)
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ ảnh hưởng tham số: {chart_path}")
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo biểu đồ ảnh hưởng tham số: {str(e)}")

def create_optimization_report(optimizer: MLOptimizer, target_metrics: List[str] = None):
    """
    Tạo báo cáo tối ưu hóa
    
    Args:
        optimizer (MLOptimizer): Đối tượng ML Optimizer
        target_metrics (List[str], optional): Danh sách chỉ số mục tiêu
    """
    if not target_metrics:
        target_metrics = ['sharpe_ratio', 'total_profit', 'expectancy']
        
    try:
        # Tạo thư mục báo cáo
        report_dir = "ml_reports"
        os.makedirs(report_dir, exist_ok=True)
        
        # Tạo báo cáo cho từng chỉ số mục tiêu
        for target_metric in target_metrics:
            # Tải mô hình
            optimizer.load_models(target_metric)
            
            # Tạo báo cáo
            report = {
                'timestamp': datetime.now().isoformat(),
                'target_metric': target_metric,
                'strategies': {},
                'market_regimes': {}
            }
            
            # Tối ưu hóa cho từng chế độ thị trường
            for market_regime in optimizer.market_regimes:
                # Tối ưu hóa ensemble
                optimal_params = optimizer.optimize_strategy_ensemble(
                    market_regime=market_regime,
                    target_metric=target_metric
                )
                
                report['market_regimes'][market_regime] = optimal_params
                
                # Lưu thông tin cho từng chiến lược
                for strategy, params in optimal_params.items():
                    if strategy not in report['strategies']:
                        report['strategies'][strategy] = {}
                        
                    report['strategies'][strategy][market_regime] = params
            
            # Lưu báo cáo vào file
            report_path = os.path.join(report_dir, f"optimization_{target_metric}.json")
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
                
            logger.info(f"Đã tạo báo cáo tối ưu hóa cho {target_metric}: {report_path}")
            
            # Tạo biểu đồ cho một số tham số quan trọng
            for strategy in report['strategies'].keys():
                if strategy == 'rsi':
                    visualize_parameter_impact(optimizer, strategy, 'rsi_period', optimizer.market_regimes, target_metric)
                    visualize_parameter_impact(optimizer, strategy, 'upper_threshold', optimizer.market_regimes, target_metric)
                    visualize_parameter_impact(optimizer, strategy, 'lower_threshold', optimizer.market_regimes, target_metric)
                elif strategy == 'macd':
                    visualize_parameter_impact(optimizer, strategy, 'fast_length', optimizer.market_regimes, target_metric)
                    visualize_parameter_impact(optimizer, strategy, 'slow_length', optimizer.market_regimes, target_metric)
                    visualize_parameter_impact(optimizer, strategy, 'signal_length', optimizer.market_regimes, target_metric)
                elif strategy == 'bbands':
                    visualize_parameter_impact(optimizer, strategy, 'length', optimizer.market_regimes, target_metric)
                    visualize_parameter_impact(optimizer, strategy, 'std_dev', optimizer.market_regimes, target_metric)
                elif strategy == 'ema_cross':
                    visualize_parameter_impact(optimizer, strategy, 'fast_length', optimizer.market_regimes, target_metric)
                    visualize_parameter_impact(optimizer, strategy, 'slow_length', optimizer.market_regimes, target_metric)
            
    except Exception as e:
        logger.error(f"Lỗi khi tạo báo cáo tối ưu hóa: {str(e)}")

def create_strategy_config_file(optimizer: MLOptimizer, target_metric: str = 'sharpe_ratio'):
    """
    Tạo file cấu hình chiến lược từ kết quả tối ưu hóa
    
    Args:
        optimizer (MLOptimizer): Đối tượng ML Optimizer
        target_metric (str): Chỉ số mục tiêu
    """
    try:
        # Tải mô hình
        optimizer.load_models(target_metric)
        
        # Khởi tạo bộ phát hiện chế độ thị trường
        market_detector = MarketRegimeDetector()
        
        # Tạo cấu hình
        config = {
            'timestamp': datetime.now().isoformat(),
            'target_metric': target_metric,
            'market_regimes': {},
            'strategies': {}
        }
        
        # Thêm thông tin chế độ thị trường
        for market_regime in optimizer.market_regimes:
            config['market_regimes'][market_regime] = {
                'description': market_detector.get_regime_description(market_regime),
                'strategy_weights': {}
            }
            
            # Tối ưu hóa ensemble
            optimal_params = optimizer.optimize_strategy_ensemble(
                market_regime=market_regime,
                target_metric=target_metric
            )
            
            # Lấy điểm số cho từng chiến lược
            for strategy, params in optimal_params.items():
                # Dự đoán điểm số
                score = 0
                
                try:
                    # Lấy điểm số từ mô hình
                    if strategy in optimizer.models:
                        model = optimizer.models[strategy]
                        scaler = optimizer.scalers[strategy]
                    elif 'global' in optimizer.models:
                        model = optimizer.models['global']
                        scaler = optimizer.scalers['global']
                    else:
                        logger.warning(f"Không có mô hình cho chiến lược {strategy}")
                        continue
                    
                    # Tạo feature vector
                    features = {}
                    
                    # Thêm tham số
                    for param_name, param_value in params.items():
                        if isinstance(param_value, (int, float)):
                            features[f'param_{param_name}'] = param_value
                    
                    # Thêm one-hot encoding cho các biến phân loại
                    if market_regime in optimizer.market_regimes:
                        for regime in optimizer.market_regimes:
                            features[f'regime_{regime}'] = 1 if regime == market_regime else 0
                    
                    # Chuyển đổi thành numpy array
                    feature_names = sorted(features.keys())
                    feature_values = [features[name] for name in feature_names]
                    X = np.array([feature_values])
                    
                    # Chuẩn hóa
                    X_scaled = scaler.transform(X)
                    
                    # Dự đoán
                    score = float(model.predict(X_scaled)[0])
                except Exception as e:
                    logger.error(f"Lỗi khi dự đoán điểm số cho {strategy}: {str(e)}")
                
                # Thêm vào trọng số chiến lược
                config['market_regimes'][market_regime]['strategy_weights'][strategy] = max(0.1, score)
        
        # Thêm thông tin chiến lược
        for strategy in optimizer.strategy_params.keys():
            config['strategies'][strategy] = {
                'parameters_by_regime': {}
            }
            
            # Thêm tham số cho từng chế độ thị trường
            for market_regime in optimizer.market_regimes:
                # Tối ưu hóa tham số
                optimal_params = optimizer.predict_optimal_parameters(
                    strategy=strategy,
                    market_regime=market_regime,
                    target_metric=target_metric
                )
                
                config['strategies'][strategy]['parameters_by_regime'][market_regime] = optimal_params
        
        # Lưu cấu hình vào file
        config_path = "strategy_config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        logger.info(f"Đã tạo file cấu hình chiến lược: {config_path}")
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo file cấu hình chiến lược: {str(e)}")

def main():
    """Hàm chính"""
    try:
        # Khởi tạo ML Optimizer
        optimizer = MLOptimizer()
        
        # Huấn luyện mô hình
        print("Huấn luyện mô hình...")
        optimizer.train_models(target_metric='sharpe_ratio')
        optimizer.train_models(target_metric='total_profit')
        optimizer.train_models(target_metric='expectancy')
        
        # Tạo báo cáo tối ưu hóa
        print("Tạo báo cáo tối ưu hóa...")
        create_optimization_report(optimizer)
        
        # Tạo file cấu hình chiến lược
        print("Tạo file cấu hình chiến lược...")
        create_strategy_config_file(optimizer)
        
        print("Đã hoàn thành tối ưu hóa chiến lược!")
        
    except Exception as e:
        logger.error(f"Lỗi khi chạy tối ưu hóa ML: {str(e)}")

if __name__ == "__main__":
    main()