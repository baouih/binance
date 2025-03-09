#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script triển khai ML vào môi trường sản xuất
"""

import os
import sys
import logging
import argparse
import json
import shutil
import time
from datetime import datetime
import subprocess

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ml_deployment.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('deploy_ml_to_production')

def backup_existing_models():
    """
    Sao lưu các mô hình ML hiện có
    
    Returns:
        Đường dẫn đến thư mục sao lưu hoặc None nếu thất bại
    """
    try:
        # Kiểm tra xem thư mục ml_models có tồn tại và có mô hình không
        if not os.path.exists("ml_models") or not os.listdir("ml_models"):
            logger.info("Không có mô hình ML hiện có để sao lưu")
            return None
        
        # Tạo thư mục sao lưu
        backup_dir = f"backups/ml_models_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(backup_dir, exist_ok=True)
        
        # Sao lưu tất cả các mô hình
        files_copied = 0
        for filename in os.listdir("ml_models"):
            src_path = os.path.join("ml_models", filename)
            dst_path = os.path.join(backup_dir, filename)
            
            if os.path.isfile(src_path):
                shutil.copy2(src_path, dst_path)
                files_copied += 1
        
        logger.info(f"Đã sao lưu {files_copied} file mô hình ML vào {backup_dir}")
        return backup_dir
        
    except Exception as e:
        logger.error(f"Lỗi khi sao lưu mô hình ML: {str(e)}")
        return None

def sync_deployment_config():
    """
    Đồng bộ file cấu hình triển khai giữa môi trường phát triển và sản xuất
    
    Returns:
        True nếu thành công
    """
    try:
        # Kiểm tra xem file cấu hình có tồn tại không
        config_path = "ml_pipeline_results/ml_deployment_config.json"
        
        if not os.path.exists(config_path):
            logger.error(f"Không tìm thấy file cấu hình {config_path}")
            return False
        
        # Đọc cấu hình
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Lưu file cấu hình vào thư mục gốc
        prod_config_path = "ml_deployment_config.json"
        
        with open(prod_config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Đã đồng bộ cấu hình triển khai từ {config_path} đến {prod_config_path}")
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi đồng bộ cấu hình triển khai: {str(e)}")
        return False

def deploy_models_to_production(source_dir="ml_models", dest_dir="ml_models_prod"):
    """
    Triển khai các mô hình ML đã huấn luyện vào môi trường sản xuất
    
    Args:
        source_dir: Thư mục nguồn chứa các mô hình ML
        dest_dir: Thư mục đích cho môi trường sản xuất
    
    Returns:
        True nếu thành công
    """
    try:
        # Kiểm tra xem thư mục nguồn có tồn tại không
        if not os.path.exists(source_dir):
            logger.error(f"Không tìm thấy thư mục nguồn {source_dir}")
            return False
        
        # Tạo thư mục đích nếu chưa tồn tại
        os.makedirs(dest_dir, exist_ok=True)
        
        # Đọc cấu hình triển khai
        config_path = "ml_pipeline_results/ml_deployment_config.json"
        
        if not os.path.exists(config_path):
            logger.error(f"Không tìm thấy file cấu hình {config_path}")
            return False
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Lấy danh sách các mô hình cần triển khai
        model_names = []
        
        if "trading_configs" in config:
            for key, cfg in config["trading_configs"].items():
                if "model_name" in cfg:
                    model_names.append(cfg["model_name"])
        
        if not model_names:
            logger.error("Không tìm thấy mô hình nào trong cấu hình triển khai")
            return False
        
        logger.info(f"Chuẩn bị triển khai {len(model_names)} mô hình: {', '.join(model_names)}")
        
        # Sao chép các file mô hình
        files_copied = 0
        
        for model_name in model_names:
            # Kiểm tra và sao chép file model
            model_file = f"{model_name}_model.joblib"
            model_path = os.path.join(source_dir, model_file)
            
            if os.path.exists(model_path):
                shutil.copy2(model_path, os.path.join(dest_dir, model_file))
                files_copied += 1
            else:
                logger.warning(f"Không tìm thấy file mô hình {model_path}")
            
            # Kiểm tra và sao chép file scaler
            scaler_file = f"{model_name}_scaler.joblib"
            scaler_path = os.path.join(source_dir, scaler_file)
            
            if os.path.exists(scaler_path):
                shutil.copy2(scaler_path, os.path.join(dest_dir, scaler_file))
                files_copied += 1
            else:
                logger.warning(f"Không tìm thấy file scaler {scaler_path}")
            
            # Kiểm tra và sao chép file features
            features_file = f"{model_name}_features.json"
            features_path = os.path.join(source_dir, features_file)
            
            if os.path.exists(features_path):
                shutil.copy2(features_path, os.path.join(dest_dir, features_file))
                files_copied += 1
            else:
                logger.warning(f"Không tìm thấy file features {features_path}")
        
        logger.info(f"Đã triển khai {files_copied} file mô hình ML vào {dest_dir}")
        
        # Tạo symlink từ ml_models đến ml_models_prod
        if os.path.exists("ml_models") and os.path.islink("ml_models"):
            os.unlink("ml_models")
        
        # Đồng bộ cấu hình triển khai
        sync_deployment_config()
        
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi triển khai mô hình ML: {str(e)}")
        return False

def start_production_integration_service():
    """
    Khởi động dịch vụ tích hợp ML trong môi trường sản xuất
    
    Returns:
        True nếu thành công
    """
    try:
        # Dừng dịch vụ hiện có nếu có
        subprocess.run("python start_ml_integration.py --stop", shell=True)
        
        # Khởi động dịch vụ mới
        log_file = f"ml_integration_prod_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        command = f"nohup python ml_integration_manager.py --mode continuous > {log_file} 2>&1 &"
        
        subprocess.Popen(command, shell=True)
        
        # Đợi một chút để kiểm tra quá trình khởi động
        time.sleep(2)
        
        # Kiểm tra xem dịch vụ đã chạy chưa
        ps_command = "ps aux | grep ml_integration_manager.py | grep -v grep"
        ps_result = subprocess.run(ps_command, shell=True, capture_output=True, text=True)
        
        if ps_result.stdout.strip():
            logger.info("Dịch vụ tích hợp ML đã được khởi động thành công")
            logger.info(f"Log file: {log_file}")
            return True
        else:
            logger.error("Không thể khởi động dịch vụ tích hợp ML")
            return False
            
    except Exception as e:
        logger.error(f"Lỗi khi khởi động dịch vụ tích hợp ML: {str(e)}")
        return False

def deploy_full_ml_system(start_service=True):
    """
    Triển khai toàn bộ hệ thống ML vào môi trường sản xuất
    
    Args:
        start_service: Khởi động dịch vụ tích hợp ML sau khi triển khai
    
    Returns:
        True nếu thành công
    """
    logger.info("=== Bắt đầu triển khai hệ thống ML vào môi trường sản xuất ===")
    
    # Sao lưu mô hình hiện có
    backup_dir = backup_existing_models()
    
    # Thiết lập thư mục sản xuất
    prod_dir = "ml_models"
    
    # Triển khai mô hình vào thư mục sản xuất
    deploy_success = deploy_models_to_production(source_dir="ml_models", dest_dir=prod_dir)
    
    if not deploy_success:
        logger.error("Triển khai mô hình ML thất bại")
        return False
    
    # Đồng bộ cấu hình triển khai
    sync_success = sync_deployment_config()
    
    if not sync_success:
        logger.error("Đồng bộ cấu hình triển khai thất bại")
        return False
    
    # Khởi động dịch vụ tích hợp ML nếu cần
    if start_service:
        service_success = start_production_integration_service()
        
        if not service_success:
            logger.error("Khởi động dịch vụ tích hợp ML thất bại")
            return False
    
    logger.info("=== Triển khai hệ thống ML vào môi trường sản xuất thành công ===")
    return True

def rollback_deployment(backup_dir=None):
    """
    Khôi phục triển khai trước đó
    
    Args:
        backup_dir: Thư mục sao lưu (nếu None, sử dụng sao lưu gần nhất)
    
    Returns:
        True nếu thành công
    """
    try:
        # Nếu không cung cấp thư mục sao lưu, tìm sao lưu gần nhất
        if backup_dir is None:
            backup_dirs = sorted([d for d in os.listdir("backups") if d.startswith("ml_models_")], reverse=True)
            
            if not backup_dirs:
                logger.error("Không tìm thấy sao lưu nào để khôi phục")
                return False
            
            backup_dir = os.path.join("backups", backup_dirs[0])
        
        logger.info(f"Khôi phục từ sao lưu: {backup_dir}")
        
        # Dừng dịch vụ tích hợp ML
        subprocess.run("python start_ml_integration.py --stop", shell=True)
        
        # Xóa thư mục ml_models hiện tại
        if os.path.exists("ml_models"):
            for filename in os.listdir("ml_models"):
                file_path = os.path.join("ml_models", filename)
                if os.path.isfile(file_path):
                    os.unlink(file_path)
        else:
            os.makedirs("ml_models", exist_ok=True)
        
        # Sao chép các file từ sao lưu
        files_copied = 0
        for filename in os.listdir(backup_dir):
            src_path = os.path.join(backup_dir, filename)
            dst_path = os.path.join("ml_models", filename)
            
            if os.path.isfile(src_path):
                shutil.copy2(src_path, dst_path)
                files_copied += 1
        
        logger.info(f"Đã khôi phục {files_copied} file mô hình ML từ {backup_dir}")
        
        # Khởi động lại dịch vụ tích hợp ML
        start_production_integration_service()
        
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi khôi phục triển khai: {str(e)}")
        return False

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Triển khai ML vào môi trường sản xuất')
    parser.add_argument('--no-service', action='store_true', 
                      help='Không khởi động dịch vụ tích hợp ML sau khi triển khai (mặc định: False)')
    parser.add_argument('--rollback', action='store_true', 
                      help='Khôi phục triển khai trước đó (mặc định: False)')
    parser.add_argument('--backup-dir', type=str, 
                      help='Thư mục sao lưu để khôi phục (chỉ với --rollback)')
    
    args = parser.parse_args()
    
    if args.rollback:
        rollback_deployment(args.backup_dir)
    else:
        deploy_full_ml_system(start_service=not args.no_service)

if __name__ == "__main__":
    main()