#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pipeline tự động cho huấn luyện và kiểm thử ML,
tạo ra các mô hình tối ưu và tích hợp vào hệ thống giao dịch
"""

import os
import sys
import logging
import argparse
import json
from datetime import datetime
import time
from typing import Dict, List, Optional

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ml_pipeline.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ml_pipeline')

# Import các module cần thiết
try:
    from enhanced_ml_trainer import EnhancedMLTrainer
    from ml_strategy_tester import MLStrategyTester
except ImportError as e:
    logger.error(f"Lỗi khi import modules: {str(e)}")
    sys.exit(1)

class MLPipeline:
    """
    Pipeline tự động cho huấn luyện, kiểm thử ML và tích hợp vào hệ thống giao dịch
    """
    
    def __init__(self, simulation_mode=True):
        """Khởi tạo Pipeline"""
        self.simulation_mode = simulation_mode
        
        # Khởi tạo các thành phần
        self.trainer = EnhancedMLTrainer(simulation_mode=simulation_mode)
        self.tester = MLStrategyTester(simulation_mode=simulation_mode)
        
        # Thư mục lưu kết quả
        self.pipeline_results_dir = "ml_pipeline_results"
        os.makedirs(self.pipeline_results_dir, exist_ok=True)
        
        logger.info(f"Khởi tạo MLPipeline, chế độ mô phỏng: {simulation_mode}")
    
    def run_full_pipeline(self, symbols: List[str], intervals: List[str],
                       lookback_periods: List[int], target_days_list: List[int],
                       optimize_hyperparams: bool = False,
                       integration_risk: float = 10,
                       integration_leverage: float = 20) -> Dict:
        """
        Chạy toàn bộ pipeline từ huấn luyện đến tích hợp
        
        Args:
            symbols: Danh sách các cặp tiền
            intervals: Danh sách khung thời gian
            lookback_periods: Danh sách khoảng thời gian lịch sử (ngày)
            target_days_list: Danh sách khoảng thời gian mục tiêu (ngày)
            optimize_hyperparams: Tối ưu siêu tham số
            integration_risk: Phần trăm rủi ro cho tích hợp
            integration_leverage: Đòn bẩy cho tích hợp
            
        Returns:
            Dict chứa kết quả pipeline
        """
        start_time = time.time()
        
        # Step 1: Huấn luyện mô hình ML
        logger.info("BƯỚC 1: Huấn luyện mô hình ML")
        training_results = self.trainer.train_multiple_models(
            symbols=symbols,
            intervals=intervals,
            lookback_periods=lookback_periods,
            target_days_list=target_days_list,
            optimize_hyperparams=optimize_hyperparams
        )
        
        # Step 2: Tạo báo cáo tổng hợp
        logger.info("BƯỚC 2: Tạo báo cáo tổng hợp")
        summary_report = self.trainer.generate_training_summary()
        
        # Step 3: So sánh các mô hình với chiến lược rủi ro cao
        logger.info("BƯỚC 3: So sánh các mô hình ML")
        comparison_results = {}
        
        for symbol in symbols:
            for interval in intervals:
                logger.info(f"So sánh các mô hình cho {symbol} {interval}")
                comparison = self.tester.compare_multiple_ml_models(
                    symbol=symbol,
                    interval=interval,
                    risk_pct=integration_risk,
                    leverage=integration_leverage
                )
                
                comparison_results[f"{symbol}_{interval}"] = comparison
        
        # Step 4: Tìm mô hình tốt nhất cho mỗi cặp tiền
        logger.info("BƯỚC 4: Tìm mô hình tốt nhất")
        best_models = {}
        
        for key, comparison in comparison_results.items():
            if "error" in comparison:
                continue
                
            if "ranking" in comparison and comparison["ranking"]:
                # Lọc ra các mô hình ML (không phải high_risk)
                ml_models = [item for item in comparison["ranking"] 
                           if item["model"] != "high_risk"]
                
                if ml_models:
                    # Lấy mô hình ML tốt nhất
                    best_model = ml_models[0]["model"]
                    best_models[key] = best_model
                    logger.info(f"Mô hình tốt nhất cho {key}: {best_model} (Lợi nhuận: {ml_models[0]['profit_pct']:.2f}%)")
        
        # Step 5: Tích hợp mô hình ML tốt nhất với chiến lược rủi ro cao
        logger.info("BƯỚC 5: Tích hợp ML và chiến lược rủi ro cao")
        integration_results = {}
        
        for key, best_model in best_models.items():
            symbol, interval = key.split('_')
            
            logger.info(f"Tích hợp {best_model} với chiến lược rủi ro cao cho {symbol} {interval}")
            
            integration = self.tester.integrate_ml_with_high_risk(
                symbol=symbol,
                interval=interval,
                best_ml_model=best_model,
                risk_pct=integration_risk,
                leverage=integration_leverage
            )
            
            integration_results[key] = integration
        
        # Step 6: Tạo báo cáo kết quả tổng thể
        total_time = time.time() - start_time
        
        pipeline_results = {
            'timestamp': datetime.now().isoformat(),
            'configuration': {
                'symbols': symbols,
                'intervals': intervals,
                'lookback_periods': lookback_periods,
                'target_days': target_days_list,
                'optimize_hyperparams': optimize_hyperparams,
                'integration_risk': integration_risk,
                'integration_leverage': integration_leverage
            },
            'training_summary': summary_report,
            'best_models': best_models,
            'integration_summary': {},
            'execution_time': total_time
        }
        
        # Tổng hợp kết quả tích hợp
        for key, integration in integration_results.items():
            if "error" in integration:
                continue
                
            if "ranking" in integration and integration["ranking"]:
                # Tìm kết quả chiến lược tích hợp
                integrated_results = [item for item in integration["ranking"] 
                                     if item["strategy"] == "integrated"]
                
                if integrated_results:
                    pipeline_results['integration_summary'][key] = {
                        'profit_pct': integrated_results[0]['profit_pct'],
                        'max_drawdown': integrated_results[0]['max_drawdown'],
                        'win_rate': integrated_results[0]['win_rate'],
                        'profit_factor': integrated_results[0]['profit_factor'],
                        'trades': integrated_results[0]['trades']
                    }
        
        # Lưu kết quả pipeline
        result_filename = os.path.join(
            self.pipeline_results_dir,
            f"ml_pipeline_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        with open(result_filename, 'w') as f:
            json.dump(pipeline_results, f, indent=2)
            
        logger.info(f"Đã lưu kết quả pipeline tại {result_filename}")
        logger.info(f"Pipeline hoàn tất sau {total_time:.2f} giây")
        
        return pipeline_results
    
    def run_partial_pipeline(self, stage: str, symbols: List[str], intervals: List[str],
                          **kwargs) -> Dict:
        """
        Chạy một phần của pipeline
        
        Args:
            stage: Giai đoạn cần chạy ('train', 'test', 'integrate')
            symbols: Danh sách các cặp tiền
            intervals: Danh sách khung thời gian
            **kwargs: Tham số bổ sung
            
        Returns:
            Dict chứa kết quả
        """
        if stage == 'train':
            logger.info("Chạy giai đoạn huấn luyện mô hình")
            
            lookback_periods = kwargs.get('lookback_periods', [30, 90])
            target_days_list = kwargs.get('target_days_list', [1, 3])
            optimize_hyperparams = kwargs.get('optimize_hyperparams', False)
            
            training_results = self.trainer.train_multiple_models(
                symbols=symbols,
                intervals=intervals,
                lookback_periods=lookback_periods,
                target_days_list=target_days_list,
                optimize_hyperparams=optimize_hyperparams
            )
            
            # Tạo báo cáo tổng hợp
            summary_report = self.trainer.generate_training_summary()
            
            return {
                'stage': 'train',
                'training_results': training_results,
                'summary_report': summary_report
            }
            
        elif stage == 'test':
            logger.info("Chạy giai đoạn kiểm thử mô hình")
            
            risk_pct = kwargs.get('risk_pct', 5)
            leverage = kwargs.get('leverage', 1)
            
            comparison_results = {}
            
            for symbol in symbols:
                for interval in intervals:
                    logger.info(f"So sánh các mô hình cho {symbol} {interval}")
                    comparison = self.tester.compare_multiple_ml_models(
                        symbol=symbol,
                        interval=interval,
                        risk_pct=risk_pct,
                        leverage=leverage
                    )
                    
                    comparison_results[f"{symbol}_{interval}"] = comparison
            
            return {
                'stage': 'test',
                'comparison_results': comparison_results
            }
            
        elif stage == 'integrate':
            logger.info("Chạy giai đoạn tích hợp ML với chiến lược rủi ro cao")
            
            model_names = kwargs.get('model_names', {})
            risk_pct = kwargs.get('risk_pct', 10)
            leverage = kwargs.get('leverage', 20)
            
            if not model_names:
                logger.error("Cần cung cấp tên mô hình cho mỗi cặp tiền")
                return {'error': 'Missing model names'}
            
            integration_results = {}
            
            for symbol in symbols:
                for interval in intervals:
                    key = f"{symbol}_{interval}"
                    
                    if key not in model_names:
                        logger.warning(f"Không có tên mô hình cho {key}")
                        continue
                    
                    best_model = model_names[key]
                    
                    logger.info(f"Tích hợp {best_model} với chiến lược rủi ro cao cho {symbol} {interval}")
                    
                    integration = self.tester.integrate_ml_with_high_risk(
                        symbol=symbol,
                        interval=interval,
                        best_ml_model=best_model,
                        risk_pct=risk_pct,
                        leverage=leverage
                    )
                    
                    integration_results[key] = integration
            
            return {
                'stage': 'integrate',
                'integration_results': integration_results
            }
        
        else:
            logger.error(f"Giai đoạn không hợp lệ: {stage}")
            return {'error': f"Invalid stage: {stage}"}
    
    def generate_deployment_config(self, integration_results: Dict, threshold_profit: float = 20.0,
                               threshold_win_rate: float = 60.0) -> Dict:
        """
        Tạo cấu hình triển khai cho hệ thống giao dịch
        
        Args:
            integration_results: Kết quả tích hợp
            threshold_profit: Ngưỡng lợi nhuận tối thiểu
            threshold_win_rate: Ngưỡng tỷ lệ thắng tối thiểu
            
        Returns:
            Dict chứa cấu hình triển khai
        """
        # Danh sách mô hình tích hợp đạt ngưỡng
        qualified_models = {}
        best_configs = {}
        
        for key, integration in integration_results.items():
            if "error" in integration:
                continue
                
            if "ranking" in integration and integration["ranking"]:
                # Tìm kết quả chiến lược tích hợp
                integrated_results = [item for item in integration["ranking"] 
                                     if item["strategy"] == "integrated"]
                
                if integrated_results:
                    result = integrated_results[0]
                    
                    # Kiểm tra ngưỡng
                    if (result["profit_pct"] >= threshold_profit and 
                        result["win_rate"] >= threshold_win_rate):
                        
                        symbol, interval = key.split('_')
                        model_name = None
                        
                        # Tìm tên mô hình từ các tham số
                        for r in integration["ranking"]:
                            if r["strategy"] == "ml_only" and "model" in r:
                                model_name = r["model"]
                                break
                        
                        if model_name:
                            qualified_models[key] = {
                                "model_name": model_name,
                                "profit_pct": result["profit_pct"],
                                "win_rate": result["win_rate"],
                                "profit_factor": result["profit_factor"]
                            }
                            
                            # Lưu cấu hình tốt nhất
                            best_configs[key] = {
                                "symbol": symbol,
                                "interval": interval,
                                "model_name": model_name,
                                "use_integration": True,
                                "risk_pct": integration["risk_pct"],
                                "leverage": integration["leverage"]
                            }
        
        # Tạo cấu hình triển khai
        deployment_config = {
            "timestamp": datetime.now().isoformat(),
            "qualified_models": qualified_models,
            "trading_configs": best_configs,
            "ml_integration_enabled": True,
            "thresholds": {
                "profit_pct": threshold_profit,
                "win_rate": threshold_win_rate
            }
        }
        
        # Lưu cấu hình
        config_filename = os.path.join(
            self.pipeline_results_dir,
            f"ml_deployment_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        with open(config_filename, 'w') as f:
            json.dump(deployment_config, f, indent=2)
            
        logger.info(f"Đã tạo cấu hình triển khai tại {config_filename}")
        
        return deployment_config

def main():
    """Hàm chính"""
    # Thiết lập parser dòng lệnh
    parser = argparse.ArgumentParser(description='Pipeline tự động cho huấn luyện và kiểm thử ML')
    parser.add_argument('--symbols', type=str, nargs='+', default=['BTCUSDT', 'ETHUSDT'], 
                      help='Danh sách cặp tiền (mặc định: BTCUSDT ETHUSDT)')
    parser.add_argument('--intervals', type=str, nargs='+', default=['1h'], 
                      help='Danh sách khung thời gian (mặc định: 1h)')
    parser.add_argument('--lookback', type=int, nargs='+', default=[30, 90], 
                      help='Khoảng thời gian lịch sử ngày (mặc định: 30 90)')
    parser.add_argument('--target', type=int, nargs='+', default=[1, 3], 
                      help='Khoảng thời gian mục tiêu ngày (mặc định: 1 3)')
    parser.add_argument('--optimize', action='store_true', 
                      help='Tối ưu siêu tham số (mặc định: False)')
    parser.add_argument('--risk', type=float, default=10, 
                      help='Phần trăm rủi ro cho tích hợp (mặc định: 10)')
    parser.add_argument('--leverage', type=float, default=20, 
                      help='Đòn bẩy cho tích hợp (mặc định: 20)')
    parser.add_argument('--stage', type=str, choices=['all', 'train', 'test', 'integrate'], 
                      default='all', help='Giai đoạn pipeline cần chạy (mặc định: all)')
    parser.add_argument('--simulation', action='store_true', 
                      help='Chế độ mô phỏng (mặc định: False)')
    
    args = parser.parse_args()
    
    # Khởi tạo pipeline
    pipeline = MLPipeline(simulation_mode=args.simulation)
    
    # Chạy pipeline
    if args.stage == 'all':
        logger.info("Chạy toàn bộ pipeline")
        results = pipeline.run_full_pipeline(
            symbols=args.symbols,
            intervals=args.intervals,
            lookback_periods=args.lookback,
            target_days_list=args.target,
            optimize_hyperparams=args.optimize,
            integration_risk=args.risk,
            integration_leverage=args.leverage
        )
    else:
        logger.info(f"Chạy giai đoạn {args.stage} của pipeline")
        results = pipeline.run_partial_pipeline(
            stage=args.stage,
            symbols=args.symbols,
            intervals=args.intervals,
            lookback_periods=args.lookback,
            target_days_list=args.target,
            optimize_hyperparams=args.optimize,
            risk_pct=args.risk,
            leverage=args.leverage
        )
    
    logger.info("Pipeline đã hoàn tất")
    
    # Nếu đã hoàn tất giai đoạn tích hợp, tạo cấu hình triển khai
    if args.stage in ['all', 'integrate'] and 'integration_results' in results:
        pipeline.generate_deployment_config(results['integration_results'])
    
    return results

if __name__ == "__main__":
    main()