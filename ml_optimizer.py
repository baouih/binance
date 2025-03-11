"""
Module tối ưu hóa chiến lược bằng học máy (Machine Learning Optimizer)

Module này sử dụng các thuật toán học máy để tối ưu hóa tham số chiến lược giao dịch
dựa trên dữ liệu quá khứ và kết quả backtest trước đây.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
import joblib
from typing import List, Dict, Tuple, Any, Optional, Union
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error, r2_score

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ml_optimizer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ml_optimizer")

class MLOptimizer:
    """Lớp tối ưu hóa chiến lược bằng học máy"""
    
    def __init__(self, models_dir: str = 'models', results_dir: str = 'test_results'):
        """
        Khởi tạo ML Optimizer
        
        Args:
            models_dir (str): Thư mục lưu mô hình
            results_dir (str): Thư mục lưu kết quả
        """
        self.models_dir = models_dir
        self.results_dir = results_dir
        
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(models_dir, exist_ok=True)
        
        # Khởi tạo các mô hình
        self.models = {}
        self.scalers = {}
        self.strategy_params = {}
        self.market_regimes = []
        
class AdvancedMLOptimizer(MLOptimizer):
    """Lớp tối ưu hóa nâng cao sử dụng mô hình học máy"""
    
    def __init__(self, 
                 models_dir: str = 'models', 
                 results_dir: str = 'test_results',
                 use_advanced_features: bool = True,
                 feature_selection_method: str = 'recursive',
                 ensemble_method: str = 'stacking'):
        """
        Khởi tạo Advanced ML Optimizer
        
        Args:
            models_dir (str): Thư mục lưu mô hình
            results_dir (str): Thư mục lưu kết quả
            use_advanced_features (bool): Có sử dụng các đặc trưng nâng cao không
            feature_selection_method (str): Phương pháp lựa chọn đặc trưng
            ensemble_method (str): Phương pháp kết hợp mô hình
        """
        super().__init__(models_dir, results_dir)
        self.use_advanced_features = use_advanced_features
        self.feature_selection_method = feature_selection_method
        self.ensemble_method = ensemble_method
        self.hyperparams = {}
        self.feature_importance = None
        self.ensemble_models = {}
        
    def load_backtest_results(self, results_dir: str = None) -> List[Dict]:
        """
        Tải kết quả backtest từ file
        
        Args:
            results_dir (str, optional): Thư mục chứa kết quả
            
        Returns:
            List[Dict]: Danh sách kết quả backtest
        """
        if not results_dir:
            results_dir = self.results_dir
            
        results = []
        
        # Đọc tất cả file json trong thư mục
        for filename in os.listdir(results_dir):
            if filename.endswith('.json') and not filename.endswith('_ml_optimization.json') and not filename == 'comprehensive_report.json':
                try:
                    file_path = os.path.join(results_dir, filename)
                    with open(file_path, 'r') as f:
                        result = json.load(f)
                        
                    # Phân tích tên file để lấy thông tin
                    name_parts = filename.replace('.json', '').split('_')
                    if len(name_parts) >= 4:
                        symbol = name_parts[0]
                        timeframe = name_parts[1]
                        period = name_parts[2]
                        strategy = '_'.join(name_parts[3:])
                        
                        # Thêm thông tin
                        result['symbol'] = symbol
                        result['timeframe'] = timeframe
                        result['period'] = period
                        result['strategy'] = strategy
                        result['filename'] = filename
                        
                        results.append(result)
                except Exception as e:
                    logger.error(f"Lỗi khi đọc file {filename}: {str(e)}")
                    
        logger.info(f"Đã tải {len(results)} kết quả backtest")
        return results
        
    def prepare_training_data(self, backtest_results: List[Dict]) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """
        Chuẩn bị dữ liệu huấn luyện từ kết quả backtest
        
        Args:
            backtest_results (List[Dict]): Danh sách kết quả backtest
            
        Returns:
            Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]: (Dữ liệu huấn luyện tổng hợp, Dữ liệu theo chiến lược)
        """
        all_data = []
        strategy_data = {}
        
        for result in backtest_results:
            try:
                # Lấy thông tin cơ bản
                symbol = result.get('symbol')
                timeframe = result.get('timeframe')
                strategy = result.get('strategy')
                market_regime = result.get('market_regime')
                
                # Thêm market_regime vào danh sách nếu chưa có
                if market_regime and market_regime not in self.market_regimes:
                    self.market_regimes.append(market_regime)
                
                # Lấy tham số chiến lược
                params = result.get('parameters', {})
                
                # Lưu thông tin tham số theo strategy_name (để dùng khi dự đoán)
                if strategy not in self.strategy_params:
                    self.strategy_params[strategy] = params
                
                # Lấy hiệu suất
                performance = {
                    'total_profit': result.get('total_profit_pct', 0),
                    'win_rate': result.get('win_rate', 0),
                    'profit_factor': result.get('profit_factor', 0),
                    'max_drawdown': result.get('max_drawdown', 0),
                    'sharpe_ratio': result.get('sharpe_ratio', 0),
                    'expectancy': result.get('expectancy', 0),
                    'total_trades': result.get('total_trades', 0)
                }
                
                # Tạo entry cho dataset
                entry = {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'strategy': strategy,
                    'market_regime': market_regime
                }
                
                # Thêm tham số chiến lược
                for param_name, param_value in params.items():
                    if isinstance(param_value, (int, float)):
                        entry[f'param_{param_name}'] = param_value
                
                # Thêm hiệu suất
                for metric_name, metric_value in performance.items():
                    entry[metric_name] = metric_value
                
                # Thêm vào dataset tổng hợp
                all_data.append(entry)
                
                # Thêm vào dataset theo chiến lược
                if strategy not in strategy_data:
                    strategy_data[strategy] = []
                strategy_data[strategy].append(entry)
                
            except Exception as e:
                logger.error(f"Lỗi khi xử lý kết quả: {str(e)}")
        
        # Chuyển đổi sang DataFrame
        all_df = pd.DataFrame(all_data)
        
        strategy_dfs = {}
        for strategy, data in strategy_data.items():
            strategy_dfs[strategy] = pd.DataFrame(data)
            
        logger.info(f"Đã chuẩn bị dữ liệu huấn luyện: {len(all_df)} mẫu tổng hợp, {len(strategy_dfs)} chiến lược")
        return all_df, strategy_dfs
    
    def _prepare_training_features(self, df: pd.DataFrame, target_metric: str = 'total_profit') -> Tuple[np.ndarray, np.ndarray]:
        """
        Chuẩn bị đặc trưng huấn luyện
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu
            target_metric (str): Chỉ số mục tiêu cần tối ưu hóa
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: (X_features, y_target)
        """
        # Lấy cột param_*
        param_cols = [col for col in df.columns if col.startswith('param_')]
        
        if not param_cols:
            logger.warning(f"Không tìm thấy cột tham số nào trong DataFrame")
            return None, None
            
        # One-hot encoding cho các biến phân loại
        if 'market_regime' in df.columns:
            regimes = pd.get_dummies(df['market_regime'], prefix='regime')
            df = pd.concat([df, regimes], axis=1)
            
        if 'symbol' in df.columns:
            symbols = pd.get_dummies(df['symbol'], prefix='symbol')
            df = pd.concat([df, symbols], axis=1)
            
        if 'timeframe' in df.columns:
            timeframes = pd.get_dummies(df['timeframe'], prefix='timeframe')
            df = pd.concat([df, timeframes], axis=1)
        
        # Tạo feature columns
        feature_columns = param_cols.copy()
        feature_columns.extend([col for col in df.columns if col.startswith('regime_')])
        feature_columns.extend([col for col in df.columns if col.startswith('symbol_')])
        feature_columns.extend([col for col in df.columns if col.startswith('timeframe_')])
        
        # Tạo X và y
        X = df[feature_columns].values
        y = df[target_metric].values
        
        return X, y
    
    def train_models(self, target_metric: str = 'sharpe_ratio', test_size: float = 0.2, 
                   use_cross_validation: bool = True) -> bool:
        """
        Huấn luyện mô hình dự đoán
        
        Args:
            target_metric (str): Chỉ số mục tiêu cần tối ưu hóa
            test_size (float): Tỷ lệ dữ liệu test
            use_cross_validation (bool): Có sử dụng cross-validation không
            
        Returns:
            bool: True nếu huấn luyện thành công, False nếu không
        """
        try:
            # Tải kết quả backtest
            backtest_results = self.load_backtest_results()
            
            if not backtest_results:
                logger.warning("Không có kết quả backtest để huấn luyện")
                return False
                
            # Chuẩn bị dữ liệu
            all_df, strategy_dfs = self.prepare_training_data(backtest_results)
            
            # Huấn luyện mô hình tổng hợp
            if len(all_df) > 10:  # Cần ít nhất 10 mẫu để huấn luyện
                X, y = self._prepare_training_features(all_df, target_metric)
                
                if X is not None and y is not None:
                    # Chia dữ liệu
                    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
                    
                    # Chuẩn hóa dữ liệu
                    scaler = StandardScaler()
                    X_train_scaled = scaler.fit_transform(X_train)
                    X_test_scaled = scaler.transform(X_test)
                    
                    # Lưu scaler
                    self.scalers['global'] = scaler
                    
                    # Định nghĩa mô hình
                    if use_cross_validation:
                        # Sử dụng GridSearchCV
                        param_grid = {
                            'n_estimators': [50, 100, 200],
                            'max_depth': [3, 5, 7, None],
                            'min_samples_split': [2, 5, 10],
                            'learning_rate': [0.01, 0.1, 0.2]
                        }
                        
                        model = GridSearchCV(
                            GradientBoostingRegressor(random_state=42),
                            param_grid,
                            cv=5,
                            scoring='neg_mean_squared_error',
                            n_jobs=-1
                        )
                        
                        model.fit(X_train_scaled, y_train)
                        best_model = model.best_estimator_
                        
                        logger.info(f"Best parameters: {model.best_params_}")
                        
                    else:
                        # Sử dụng GradientBoostingRegressor
                        best_model = GradientBoostingRegressor(
                            n_estimators=100,
                            max_depth=5,
                            min_samples_split=5,
                            learning_rate=0.1,
                            random_state=42
                        )
                        
                        best_model.fit(X_train_scaled, y_train)
                    
                    # Đánh giá mô hình
                    y_pred = best_model.predict(X_test_scaled)
                    mse = mean_squared_error(y_test, y_pred)
                    r2 = r2_score(y_test, y_pred)
                    
                    logger.info(f"Mô hình tổng hợp - MSE: {mse:.4f}, R²: {r2:.4f}")
                    
                    # Lưu mô hình
                    self.models['global'] = best_model
                    
                    # Lưu mô hình vào file
                    model_path = os.path.join(self.models_dir, f"global_{target_metric}_model.joblib")
                    scaler_path = os.path.join(self.models_dir, f"global_{target_metric}_scaler.joblib")
                    
                    joblib.dump(best_model, model_path)
                    joblib.dump(scaler, scaler_path)
                    
                    logger.info(f"Đã lưu mô hình tổng hợp: {model_path}")
            
            # Huấn luyện mô hình theo chiến lược
            for strategy, df in strategy_dfs.items():
                if len(df) > 10:  # Cần ít nhất 10 mẫu để huấn luyện
                    X, y = self._prepare_training_features(df, target_metric)
                    
                    if X is not None and y is not None:
                        # Chia dữ liệu
                        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
                        
                        # Chuẩn hóa dữ liệu
                        scaler = StandardScaler()
                        X_train_scaled = scaler.fit_transform(X_train)
                        X_test_scaled = scaler.transform(X_test)
                        
                        # Lưu scaler
                        self.scalers[strategy] = scaler
                        
                        # Định nghĩa mô hình
                        model = GradientBoostingRegressor(
                            n_estimators=100,
                            max_depth=5,
                            min_samples_split=5,
                            learning_rate=0.1,
                            random_state=42
                        )
                        
                        model.fit(X_train_scaled, y_train)
                        
                        # Đánh giá mô hình
                        y_pred = model.predict(X_test_scaled)
                        mse = mean_squared_error(y_test, y_pred)
                        r2 = r2_score(y_test, y_pred)
                        
                        logger.info(f"Mô hình {strategy} - MSE: {mse:.4f}, R²: {r2:.4f}")
                        
                        # Lưu mô hình
                        self.models[strategy] = model
                        
                        # Lưu mô hình vào file
                        model_path = os.path.join(self.models_dir, f"{strategy}_{target_metric}_model.joblib")
                        scaler_path = os.path.join(self.models_dir, f"{strategy}_{target_metric}_scaler.joblib")
                        
                        joblib.dump(model, model_path)
                        joblib.dump(scaler, scaler_path)
                        
                        logger.info(f"Đã lưu mô hình {strategy}: {model_path}")
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi huấn luyện mô hình: {str(e)}")
            return False
    
    def load_models(self, target_metric: str = 'sharpe_ratio') -> bool:
        """
        Tải mô hình từ file
        
        Args:
            target_metric (str): Chỉ số mục tiêu
            
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        try:
            # Tải mô hình tổng hợp
            global_model_path = os.path.join(self.models_dir, f"global_{target_metric}_model.joblib")
            global_scaler_path = os.path.join(self.models_dir, f"global_{target_metric}_scaler.joblib")
            
            if os.path.exists(global_model_path) and os.path.exists(global_scaler_path):
                self.models['global'] = joblib.load(global_model_path)
                self.scalers['global'] = joblib.load(global_scaler_path)
                logger.info(f"Đã tải mô hình tổng hợp: {global_model_path}")
            
            # Tải các mô hình theo chiến lược
            for filename in os.listdir(self.models_dir):
                if filename.endswith('_model.joblib') and not filename.startswith('global'):
                    try:
                        # Phân tích tên file để lấy tên chiến lược
                        strategy = filename.split('_')[0]
                        
                        # Kiểm tra xem file scaler có tồn tại không
                        scaler_path = os.path.join(self.models_dir, f"{strategy}_{target_metric}_scaler.joblib")
                        if not os.path.exists(scaler_path):
                            continue
                        
                        # Tải mô hình và scaler
                        model_path = os.path.join(self.models_dir, filename)
                        self.models[strategy] = joblib.load(model_path)
                        self.scalers[strategy] = joblib.load(scaler_path)
                        
                        logger.info(f"Đã tải mô hình {strategy}: {model_path}")
                    except Exception as e:
                        logger.error(f"Lỗi khi tải mô hình {filename}: {str(e)}")
            
            return len(self.models) > 0
        except Exception as e:
            logger.error(f"Lỗi khi tải mô hình: {str(e)}")
            return False
    
    def predict_optimal_parameters(self, strategy: str, market_regime: str, 
                                 symbol: str = 'BTCUSDT', timeframe: str = '1h',
                                 current_params: Dict = None,
                                 target_metric: str = 'sharpe_ratio') -> Dict:
        """
        Dự đoán tham số tối ưu cho chiến lược
        
        Args:
            strategy (str): Tên chiến lược
            market_regime (str): Chế độ thị trường
            symbol (str): Symbol giao dịch
            timeframe (str): Khung thời gian
            current_params (Dict, optional): Tham số hiện tại
            target_metric (str): Chỉ số mục tiêu
            
        Returns:
            Dict: Tham số tối ưu dự đoán
        """
        try:
            # Kiểm tra nếu chưa có mô hình
            if not self.models:
                loaded = self.load_models(target_metric)
                if not loaded:
                    logger.warning("Không có mô hình để dự đoán, đang huấn luyện mô hình mới")
                    self.train_models(target_metric)
            
            # Sử dụng tham số mặc định nếu không có tham số hiện tại
            if not current_params and strategy in self.strategy_params:
                current_params = self.strategy_params[strategy]
                
            if not current_params:
                logger.warning(f"Không có tham số hiện tại cho chiến lược {strategy}")
                return {}
                
            # Kiểm tra mô hình chiến lược cụ thể
            if strategy in self.models:
                model = self.models[strategy]
                scaler = self.scalers[strategy]
            elif 'global' in self.models:
                model = self.models['global']
                scaler = self.scalers['global']
            else:
                logger.warning(f"Không có mô hình cho chiến lược {strategy}")
                return current_params
                
            # Tạo feature vector
            features = {}
            
            # Thêm tham số hiện tại
            for param_name, param_value in current_params.items():
                if isinstance(param_value, (int, float)):
                    features[f'param_{param_name}'] = param_value
            
            # Thêm one-hot encoding cho các biến phân loại
            if market_regime in self.market_regimes:
                for regime in self.market_regimes:
                    features[f'regime_{regime}'] = 1 if regime == market_regime else 0
            
            # Chuyển đổi thành numpy array
            feature_names = sorted(features.keys())
            feature_values = [features[name] for name in feature_names]
            X = np.array([feature_values])
            
            # Chuẩn hóa
            X_scaled = scaler.transform(X)
            
            # Grid search cho các tham số
            param_names = [name.replace('param_', '') for name in feature_names if name.startswith('param_')]
            best_params = current_params.copy()
            best_score = float('-inf')
            
            # Tạo grid tìm kiếm tham số tối ưu
            for param_name in param_names:
                # Tạo grid cho tham số này
                current_value = current_params[param_name]
                
                # Tạo range các giá trị cần thử
                if isinstance(current_value, int):
                    # Tham số nguyên
                    param_range = [
                        max(1, int(current_value * 0.5)),
                        max(1, int(current_value * 0.8)),
                        current_value,
                        int(current_value * 1.2),
                        int(current_value * 1.5)
                    ]
                elif isinstance(current_value, float):
                    # Tham số thực
                    param_range = [
                        max(0.01, current_value * 0.5),
                        max(0.01, current_value * 0.8),
                        current_value,
                        current_value * 1.2,
                        current_value * 1.5
                    ]
                else:
                    # Skip non-numeric parameters
                    continue
                
                # Loại bỏ các giá trị trùng lặp
                param_range = sorted(list(set(param_range)))
                
                # Thử từng giá trị
                for value in param_range:
                    # Tạo bản sao feature vector
                    test_features = features.copy()
                    test_features[f'param_{param_name}'] = value
                    
                    # Chuyển đổi thành numpy array
                    test_values = [test_features[name] for name in feature_names]
                    X_test = np.array([test_values])
                    
                    # Chuẩn hóa
                    X_test_scaled = scaler.transform(X_test)
                    
                    # Dự đoán
                    score = model.predict(X_test_scaled)[0]
                    
                    # Cập nhật nếu tốt hơn
                    if score > best_score:
                        best_score = score
                        best_params[param_name] = value
            
            logger.info(f"Tham số tối ưu dự đoán cho {strategy} trong chế độ {market_regime}: {best_params}")
            logger.info(f"Điểm số dự đoán: {best_score:.4f} (target: {target_metric})")
            
            return best_params
        except Exception as e:
            logger.error(f"Lỗi khi dự đoán tham số tối ưu: {str(e)}")
            return current_params
    
    def optimize_strategy_ensemble(self, market_regime: str, 
                                 target_metric: str = 'sharpe_ratio') -> Dict[str, Dict]:
        """
        Tối ưu hóa ensemble các chiến lược
        
        Args:
            market_regime (str): Chế độ thị trường
            target_metric (str): Chỉ số mục tiêu
            
        Returns:
            Dict[str, Dict]: Tham số tối ưu cho mỗi chiến lược trong ensemble
        """
        try:
            # Kiểm tra nếu chưa có mô hình
            if not self.models:
                loaded = self.load_models(target_metric)
                if not loaded:
                    logger.warning("Không có mô hình để tối ưu hóa, đang huấn luyện mô hình mới")
                    self.train_models(target_metric)
            
            # Dự đoán tham số tối ưu cho từng chiến lược
            optimal_params = {}
            
            for strategy in self.strategy_params.keys():
                current_params = self.strategy_params[strategy]
                
                optimal_params[strategy] = self.predict_optimal_parameters(
                    strategy=strategy,
                    market_regime=market_regime,
                    current_params=current_params,
                    target_metric=target_metric
                )
            
            return optimal_params
        except Exception as e:
            logger.error(f"Lỗi khi tối ưu hóa ensemble: {str(e)}")
            return {}

def main():
    """Hàm chính để test module"""
    try:
        # Khởi tạo ML Optimizer
        optimizer = MLOptimizer()
        
        # Huấn luyện mô hình
        print("Huấn luyện mô hình...")
        optimizer.train_models(target_metric='sharpe_ratio')
        
        # Dự đoán tham số tối ưu
        print("Dự đoán tham số tối ưu cho RSI trong chế độ trending...")
        current_params = {'rsi_period': 14, 'upper_threshold': 70, 'lower_threshold': 30}
        optimal_params = optimizer.predict_optimal_parameters(
            strategy='rsi',
            market_regime='trending',
            current_params=current_params,
            target_metric='sharpe_ratio'
        )
        
        print(f"Tham số hiện tại: {current_params}")
        print(f"Tham số tối ưu dự đoán: {optimal_params}")
        
    except Exception as e:
        logger.error(f"Lỗi khi chạy ML Optimizer: {str(e)}")

if __name__ == "__main__":
    main()