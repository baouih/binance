#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script chạy toàn bộ quy trình ML từ huấn luyện đến triển khai
Tạo mô hình và tích hợp cho tất cả các coin thanh khoản cao
"""

import os
import sys
import logging
import argparse
import json
import time
from datetime import datetime
import subprocess

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("complete_ml_pipeline.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('complete_ml_pipeline')

# Danh sách coin thanh khoản cao
HIGH_LIQUIDITY_COINS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", 
    "XRPUSDT", "DOGEUSDT", "DOTUSDT", "AVAXUSDT", "MATICUSDT"
]

# Khung thời gian được hỗ trợ
SUPPORTED_TIMEFRAMES = ["1h", "4h"]

# Khoảng thời gian lịch sử (ngày)
LOOKBACK_PERIODS = [30, 90]

# Khoảng thời gian mục tiêu (ngày)
TARGET_DAYS = [1, 3]

def run_command(command, description=None):
    """
    Chạy lệnh shell và ghi log
    
    Args:
        command: Lệnh shell cần chạy
        description: Mô tả lệnh (tùy chọn)
    
    Returns:
        Kết quả thực thi lệnh
    """
    if description:
        logger.info(f"Running: {description}")
    else:
        logger.info(f"Running command: {command}")
        
    try:
        start_time = time.time()
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        execution_time = time.time() - start_time
        logger.info(f"Command completed in {execution_time:.2f} seconds with exit code {result.returncode}")
        
        if result.stdout:
            logger.debug(f"Command output: {result.stdout}")
        
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}: {e.stderr}")
        raise

def train_ml_models(coins, timeframes, lookback_periods, target_days, optimize=False, data_dir='real_data'):
    """
    Huấn luyện mô hình ML cho các coin và khung thời gian
    
    Args:
        coins: Danh sách coin
        timeframes: Danh sách khung thời gian
        lookback_periods: Danh sách khoảng thời gian lịch sử
        target_days: Danh sách khoảng thời gian mục tiêu
        optimize: Tối ưu siêu tham số hay không
        data_dir: Thư mục chứa dữ liệu thị trường thực (mặc định: real_data)
    
    Returns:
        True nếu thành công
    """
    logger.info("=== Bắt đầu huấn luyện mô hình ML ===")
    
    # Convert lists to strings for command line
    coins_str = " ".join(coins)
    timeframes_str = " ".join(timeframes)
    lookback_str = " ".join(map(str, lookback_periods))
    target_str = " ".join(map(str, target_days))
    
    # Build command
    optimize_flag = "--optimize" if optimize else ""
    
    command = (
        f"python enhanced_ml_trainer.py "
        f"--symbols {coins_str} "
        f"--intervals {timeframes_str} "
        f"--lookback {lookback_str} "
        f"--target {target_str} "
        f"{optimize_flag} "
        f"--data-dir {data_dir}"
    )
    
    # Run training
    try:
        run_command(command, "Huấn luyện mô hình ML")
        
        # Generate summary
        report_command = f"python enhanced_ml_trainer.py --report-only --data-dir {data_dir}"
        run_command(report_command, "Tạo báo cáo tổng hợp")
        
        logger.info("=== Hoàn thành huấn luyện mô hình ML ===")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi huấn luyện mô hình ML: {str(e)}")
        return False

def test_ml_models(coins, timeframes, risk_pct=10, leverage=20, data_dir='real_data'):
    """
    Kiểm thử mô hình ML và so sánh với chiến lược rủi ro cao
    
    Args:
        coins: Danh sách coin
        timeframes: Danh sách khung thời gian
        risk_pct: Phần trăm rủi ro
        leverage: Đòn bẩy
        data_dir: Thư mục chứa dữ liệu thị trường thực (mặc định: real_data)
    
    Returns:
        Dict của các cặp tiền và mô hình tốt nhất
    """
    logger.info("=== Bắt đầu kiểm thử mô hình ML ===")
    
    best_models = {}
    
    for coin in coins:
        for timeframe in timeframes:
            # Build command for ML model comparison
            command = (
                f"python ml_strategy_tester.py "
                f"--symbol {coin} "
                f"--interval {timeframe} "
                f"--risk {risk_pct} "
                f"--leverage {leverage} "
                f"--mode ml-compare "
                f"--data-dir {data_dir}"
            )
            
            try:
                # Run ML model comparison
                run_command(command, f"So sánh các mô hình ML cho {coin} {timeframe}")
                
                # Load comparison results
                result_file = f"ml_test_results/{coin}_{timeframe}_ml_model_comparison.json"
                
                if os.path.exists(result_file):
                    with open(result_file, 'r') as f:
                        comparison = json.load(f)
                    
                    if "ranking" in comparison and comparison["ranking"]:
                        # Get best ML model
                        ml_models = [item for item in comparison["ranking"] 
                                  if item["model"] != "high_risk"]
                        
                        if ml_models:
                            best_model = ml_models[0]["model"]
                            best_models[f"{coin}_{timeframe}"] = best_model
                            logger.info(f"Mô hình tốt nhất cho {coin} {timeframe}: {best_model}")
                        
            except Exception as e:
                logger.error(f"Lỗi khi kiểm thử mô hình cho {coin} {timeframe}: {str(e)}")
    
    logger.info("=== Hoàn thành kiểm thử mô hình ML ===")
    logger.info(f"Đã tìm thấy {len(best_models)} mô hình tốt nhất")
    
    return best_models

def integrate_ml_models(best_models, risk_pct=10, leverage=20, data_dir='real_data'):
    """
    Tích hợp mô hình ML tốt nhất với chiến lược rủi ro cao
    
    Args:
        best_models: Dict của các cặp tiền và mô hình tốt nhất
        risk_pct: Phần trăm rủi ro
        leverage: Đòn bẩy
        data_dir: Thư mục chứa dữ liệu thị trường thực (mặc định: real_data)
    
    Returns:
        Dict chứa kết quả tích hợp
    """
    logger.info("=== Bắt đầu tích hợp mô hình ML với chiến lược rủi ro cao ===")
    
    integration_results = {}
    
    for key, model in best_models.items():
        coin, timeframe = key.split('_')
        
        # Build command for integration
        command = (
            f"python ml_strategy_tester.py "
            f"--symbol {coin} "
            f"--interval {timeframe} "
            f"--ml-model {model} "
            f"--risk {risk_pct} "
            f"--leverage {leverage} "
            f"--mode integrate "
            f"--data-dir {data_dir}"
        )
        
        try:
            # Run integration
            run_command(command, f"Tích hợp ML và chiến lược rủi ro cao cho {coin} {timeframe}")
            
            # Load integration results
            result_file = f"ml_test_results/{coin}_{timeframe}_integration_test.json"
            
            if os.path.exists(result_file):
                with open(result_file, 'r') as f:
                    result = json.load(f)
                
                integration_results[key] = result
                
                # Log performance
                if "ranking" in result:
                    strategies = {item["strategy"]: item for item in result["ranking"]}
                    
                    if "integrated" in strategies:
                        integrated = strategies["integrated"]
                        logger.info(
                            f"{coin} {timeframe} tích hợp: "
                            f"Lợi nhuận={integrated['profit_pct']:.2f}%, "
                            f"Win rate={integrated['win_rate']:.2f}%, "
                            f"Số lệnh={integrated['trades']}"
                        )
        
        except Exception as e:
            logger.error(f"Lỗi khi tích hợp ML cho {coin} {timeframe}: {str(e)}")
    
    logger.info("=== Hoàn thành tích hợp mô hình ML ===")
    
    return integration_results

def create_deployment_config(best_models, integration_results, threshold_profit=20.0, threshold_win_rate=60.0):
    """
    Tạo cấu hình triển khai cho hệ thống giao dịch
    
    Args:
        best_models: Dict của các cặp tiền và mô hình tốt nhất
        integration_results: Kết quả tích hợp
        threshold_profit: Ngưỡng lợi nhuận tối thiểu
        threshold_win_rate: Ngưỡng tỷ lệ thắng tối thiểu
    
    Returns:
        Dict chứa cấu hình triển khai
    """
    logger.info("=== Tạo cấu hình triển khai ML ===")
    
    # Danh sách mô hình đạt ngưỡng
    qualified_models = {}
    trading_configs = {}
    
    for key, model in best_models.items():
        if key in integration_results:
            result = integration_results[key]
            
            if "ranking" in result:
                # Tìm kết quả chiến lược tích hợp
                integrated_results = [item for item in result["ranking"] 
                                     if item["strategy"] == "integrated"]
                
                if integrated_results:
                    perf = integrated_results[0]
                    
                    # Kiểm tra ngưỡng
                    if (perf["profit_pct"] >= threshold_profit and 
                        perf["win_rate"] >= threshold_win_rate):
                        
                        coin, timeframe = key.split('_')
                        
                        qualified_models[key] = {
                            "model_name": model,
                            "profit_pct": perf["profit_pct"],
                            "win_rate": perf["win_rate"],
                            "profit_factor": perf.get("profit_factor", 0)
                        }
                        
                        trading_configs[key] = {
                            "symbol": coin,
                            "interval": timeframe,
                            "model_name": model,
                            "use_integration": True,
                            "risk_pct": result.get("risk_pct", 10),
                            "leverage": result.get("leverage", 20)
                        }
    
    # Tạo cấu hình triển khai
    deployment_config = {
        "timestamp": datetime.now().isoformat(),
        "qualified_models": qualified_models,
        "trading_configs": trading_configs,
        "ml_integration_enabled": True,
        "thresholds": {
            "profit_pct": threshold_profit,
            "win_rate": threshold_win_rate
        }
    }
    
    # Lưu cấu hình
    config_filename = os.path.join(
        "ml_pipeline_results",
        f"ml_deployment_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    
    with open(config_filename, 'w') as f:
        json.dump(deployment_config, f, indent=2)
    
    # Tạo liên kết đến file mới nhất
    latest_config = os.path.join("ml_pipeline_results", "ml_deployment_config.json")
    if os.path.exists(latest_config):
        os.remove(latest_config)
    
    with open(latest_config, 'w') as f:
        json.dump(deployment_config, f, indent=2)
    
    logger.info(f"Đã tạo cấu hình triển khai tại {config_filename}")
    logger.info(f"Số mô hình đạt ngưỡng: {len(qualified_models)}/{len(best_models)}")
    
    return deployment_config

def run_complete_pipeline(coins=None, timeframes=None, optimize=False, 
                       risk_pct=10, leverage=20, threshold_profit=20.0, 
                       threshold_win_rate=60.0, data_dir='real_data'):
    """
    Chạy toàn bộ pipeline ML
    
    Args:
        coins: Danh sách coin (mặc định: tất cả coin thanh khoản cao)
        timeframes: Danh sách khung thời gian (mặc định: 1h, 4h)
        optimize: Tối ưu siêu tham số hay không
        risk_pct: Phần trăm rủi ro
        leverage: Đòn bẩy
        threshold_profit: Ngưỡng lợi nhuận tối thiểu
        threshold_win_rate: Ngưỡng tỷ lệ thắng tối thiểu
        data_dir: Thư mục chứa dữ liệu thị trường thực (mặc định: real_data)
    
    Returns:
        Dict chứa kết quả pipeline
    """
    start_time = time.time()
    
    # Thiết lập tham số mặc định
    if coins is None:
        coins = HIGH_LIQUIDITY_COINS
    
    if timeframes is None:
        timeframes = SUPPORTED_TIMEFRAMES
    
    # Step 1: Huấn luyện mô hình ML
    success = train_ml_models(
        coins=coins,
        timeframes=timeframes,
        lookback_periods=LOOKBACK_PERIODS,
        target_days=TARGET_DAYS,
        optimize=optimize,
        data_dir=data_dir
    )
    
    if not success:
        logger.error("Huấn luyện mô hình ML thất bại, dừng pipeline")
        return {"error": "Model training failed"}
    
    # Step 2: Kiểm thử mô hình ML
    best_models = test_ml_models(
        coins=coins,
        timeframes=timeframes,
        risk_pct=risk_pct,
        leverage=leverage,
        data_dir=data_dir
    )
    
    if not best_models:
        logger.error("Không tìm thấy mô hình tốt nhất, dừng pipeline")
        return {"error": "No best models found"}
    
    # Step 3: Tích hợp mô hình ML với chiến lược rủi ro cao
    integration_results = integrate_ml_models(
        best_models=best_models,
        risk_pct=risk_pct,
        leverage=leverage,
        data_dir=data_dir
    )
    
    # Step 4: Tạo cấu hình triển khai
    deployment_config = create_deployment_config(
        best_models=best_models,
        integration_results=integration_results,
        threshold_profit=threshold_profit,
        threshold_win_rate=threshold_win_rate
    )
    
    # Kết quả tổng hợp
    total_time = time.time() - start_time
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "execution_time": total_time,
        "best_models": best_models,
        "deployment_config": deployment_config
    }
    
    logger.info(f"=== Pipeline hoàn tất sau {total_time:.2f} giây ===")
    
    return result

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Chạy toàn bộ pipeline ML')
    parser.add_argument('--coins', type=str, nargs='+', 
                      help='Danh sách coin (mặc định: tất cả coin thanh khoản cao)')
    parser.add_argument('--timeframes', type=str, nargs='+', 
                      help='Danh sách khung thời gian (mặc định: 1h, 4h)')
    parser.add_argument('--optimize', action='store_true', 
                      help='Tối ưu siêu tham số (mặc định: False)')
    parser.add_argument('--risk', type=float, default=10, 
                      help='Phần trăm rủi ro (mặc định: 10)')
    parser.add_argument('--data-dir', type=str, default='real_data',
                      help='Thư mục chứa dữ liệu thị trường thực (mặc định: real_data)')
    parser.add_argument('--leverage', type=float, default=20, 
                      help='Đòn bẩy (mặc định: 20)')
    parser.add_argument('--profit-threshold', type=float, default=20.0, 
                      help='Ngưỡng lợi nhuận tối thiểu (mặc định: 20.0)')
    parser.add_argument('--winrate-threshold', type=float, default=60.0, 
                      help='Ngưỡng tỷ lệ thắng tối thiểu (mặc định: 60.0)')
    
    args = parser.parse_args()
    
    run_complete_pipeline(
        coins=args.coins,
        timeframes=args.timeframes,
        optimize=args.optimize,
        risk_pct=args.risk,
        leverage=args.leverage,
        threshold_profit=args.profit_threshold,
        threshold_win_rate=args.winrate_threshold,
        data_dir=args.data_dir
    )

if __name__ == "__main__":
    main()