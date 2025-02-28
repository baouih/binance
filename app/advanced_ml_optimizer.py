"""
Bộ tối ưu hóa học máy nâng cao cho giao dịch tiền điện tử
Hỗ trợ nhiều loại mô hình và kỹ thuật ensemble để cải thiện độ chính xác dự đoán
"""

import os
import time
import joblib
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Union, Optional

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report, confusion_matrix
from sklearn.feature_selection import SelectKBest, f_classif

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('advanced_ml_optimizer')

class AdvancedMLOptimizer:
    """Bộ tối ưu hóa học máy nâng cao với các tính năng mở rộng"""
    
    # Các trạng thái thị trường
    MARKET_REGIMES = ["trending_up", "trending_down", "ranging", "volatile", "breakout", "neutral"]
    
    # Các mô hình chính
    MODEL_TYPES = {
        "random_forest": RandomForestClassifier,
        "gradient_boosting": GradientBoostingClassifier,
        "svm": SVC,
        "logistic_regression": LogisticRegression,
        "neural_network": MLPClassifier
    }
    
    def __init__(self, base_models=None, use_model_per_regime=True, feature_selection=True, use_ensemble=True):
        """
        Khởi tạo bộ tối ưu hóa học máy nâng cao
        
        Args:
            base_models (list): Danh sách các loại mô hình cơ sở sẽ được sử dụng
            use_model_per_regime (bool): Sử dụng mô hình riêng cho mỗi chế độ thị trường
            feature_selection (bool): Sử dụng lựa chọn tính năng tự động
            use_ensemble (bool): Sử dụng kỹ thuật ensemble để kết hợp dự đoán
        """
        self.models = {}
        self.ensemble_model = None
        self.scalers = {}
        self.feature_selectors = {}
        self.feature_importances = {}
        self.model_metrics = {}
        self.use_model_per_regime = use_model_per_regime
        self.feature_selection = feature_selection
        self.use_ensemble = use_ensemble
        self.model_params = self._get_default_params()
        self.selected_features = {}
        
        # Thiết lập các mô hình cơ sở
        if base_models is None:
            self.base_models = ["random_forest", "gradient_boosting", "neural_network"]
        else:
            self.base_models = base_models
            
        for model_type in self.base_models:
            if model_type not in self.MODEL_TYPES:
                logger.warning(f"Mô hình {model_type} không được hỗ trợ, bỏ qua.")
                self.base_models.remove(model_type)
        
        logger.info(f"Khởi tạo AdvancedMLOptimizer với {len(self.base_models)} loại mô hình cơ sở")
        logger.info(f"Mô hình riêng cho mỗi chế độ thị trường: {use_model_per_regime}")
        logger.info(f"Sử dụng lựa chọn tính năng tự động: {feature_selection}")
        logger.info(f"Sử dụng kỹ thuật ensemble: {use_ensemble}")
    
    def _get_model_key(self, model_type, regime=None):
        """Tạo khóa duy nhất cho mỗi mô hình"""
        if regime and self.use_model_per_regime:
            return f"{model_type}_{regime}"
        return model_type
    
    def _get_default_params(self):
        """Lấy tham số mặc định cho mỗi loại mô hình"""
        return {
            "random_forest": {
                "n_estimators": 100,
                "max_depth": 10,
                "min_samples_split": 5,
                "min_samples_leaf": 2,
                "random_state": 42,
                "class_weight": "balanced"
            },
            "gradient_boosting": {
                "n_estimators": 100,
                "learning_rate": 0.1,
                "max_depth": 5,
                "min_samples_split": 5,
                "min_samples_leaf": 2,
                "random_state": 42
            },
            "svm": {
                "C": 1.0,
                "kernel": "rbf",
                "gamma": "scale",
                "probability": True,
                "class_weight": "balanced",
                "random_state": 42
            },
            "logistic_regression": {
                "C": 1.0,
                "penalty": "l2",
                "solver": "liblinear",
                "class_weight": "balanced",
                "random_state": 42
            },
            "neural_network": {
                "hidden_layer_sizes": (100, 50),
                "activation": "relu",
                "solver": "adam",
                "alpha": 0.0001,
                "max_iter": 300,
                "random_state": 42
            }
        }
    
    def _get_model_params_for_regime(self, model_type, regime):
        """Lấy tham số tối ưu cho mô hình với chế độ thị trường cụ thể"""
        base_params = self.model_params[model_type].copy()
        
        # Điều chỉnh tham số cho từng chế độ thị trường
        if regime == "trending_up" or regime == "trending_down":
            # Trong xu hướng, chúng ta muốn mô hình nhạy cảm hơn
            if model_type == "random_forest":
                base_params["n_estimators"] = 150
                base_params["max_depth"] = 15
            elif model_type == "gradient_boosting":
                base_params["n_estimators"] = 150
                base_params["learning_rate"] = 0.15
            elif model_type == "neural_network":
                base_params["hidden_layer_sizes"] = (150, 75)
                base_params["alpha"] = 0.00005
                
        elif regime == "ranging":
            # Trong biên độ giao dịch, chúng ta cần mô hình ổn định hơn
            if model_type == "random_forest":
                base_params["n_estimators"] = 200
                base_params["min_samples_split"] = 10
            elif model_type == "gradient_boosting":
                base_params["learning_rate"] = 0.05
                base_params["max_depth"] = 3
            elif model_type == "neural_network":
                base_params["hidden_layer_sizes"] = (80, 40)
                base_params["alpha"] = 0.001
                
        elif regime == "volatile":
            # Trong thị trường biến động, chúng ta cần mô hình thích ứng nhanh
            if model_type == "random_forest":
                base_params["n_estimators"] = 80
                base_params["max_depth"] = 8
            elif model_type == "gradient_boosting":
                base_params["learning_rate"] = 0.2
                base_params["max_depth"] = 7
            elif model_type == "neural_network":
                base_params["hidden_layer_sizes"] = (120, 60)
                base_params["alpha"] = 0.00001
        
        return base_params
    
    def _preprocess_features(self, X, y=None, regime=None, is_training=False):
        """
        Tiền xử lý tính năng bao gồm chuẩn hóa và lựa chọn tính năng
        
        Args:
            X: Dữ liệu tính năng đầu vào
            y: Nhãn đích (cần thiết nếu is_training=True và feature_selection=True)
            regime: Chế độ thị trường hiện tại
            is_training: Nếu đây là dữ liệu đào tạo
            
        Returns:
            X_processed: Dữ liệu đã xử lý
        """
        key = regime if regime and self.use_model_per_regime else "default"
        
        # Chuẩn hóa dữ liệu
        if is_training:
            self.scalers[key] = StandardScaler()
            X_scaled = self.scalers[key].fit_transform(X)
        else:
            if key not in self.scalers:
                logger.warning(f"Không tìm thấy bộ scaler cho {key}, sử dụng scaler mặc định")
                key = "default"
                if key not in self.scalers:
                    logger.error("Không tìm thấy bộ scaler mặc định")
                    # Nếu không có scaler nào, trả về dữ liệu gốc
                    return X
            
            X_scaled = self.scalers[key].transform(X)
        
        # Lựa chọn tính năng
        if self.feature_selection:
            if is_training:
                if y is None:
                    logger.warning("Biến y không được cung cấp cho lựa chọn tính năng, đang bỏ qua bước này")
                    return X_scaled
                
                # Sử dụng SelectKBest để chọn các tính năng tốt nhất
                n_features = min(20, X.shape[1])  # Chọn tối đa 20 tính năng hoặc tất cả nếu ít hơn
                self.feature_selectors[key] = SelectKBest(f_classif, k=n_features)
                X_selected = self.feature_selectors[key].fit_transform(X_scaled, y)
                
                # Lưu trữ các tính năng đã chọn
                feature_mask = self.feature_selectors[key].get_support()
                self.selected_features[key] = [i for i, selected in enumerate(feature_mask) if selected]
                
                logger.info(f"Đã chọn {len(self.selected_features[key])}/{X.shape[1]} tính năng cho {key}")
                
                return X_selected
            else:
                if key not in self.feature_selectors:
                    logger.warning(f"Không tìm thấy bộ chọn tính năng cho {key}, sử dụng tất cả tính năng")
                    return X_scaled
                    
                return self.feature_selectors[key].transform(X_scaled)
        
        return X_scaled
    
    def train_models(self, X, y, regime=None):
        """
        Đào tạo mô hình cho chế độ thị trường cụ thể hoặc mô hình chung
        
        Args:
            X: Tính năng đầu vào
            y: Nhãn đích
            regime: Chế độ thị trường hiện tại
            
        Returns:
            metrics: Các số liệu hiệu suất của mô hình
        """
        metrics = {}
        
        if len(np.unique(y)) < 2:
            logger.warning("Dữ liệu đào tạo không có đủ các lớp khác nhau, cần ít nhất 2 lớp")
            return metrics
        
        # Chia dữ liệu thành tập train và test
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        # Tiền xử lý dữ liệu
        X_train_processed = self._preprocess_features(X_train, y_train, regime, is_training=True)
        X_test_processed = self._preprocess_features(X_test, None, regime, is_training=False)
        
        # Đào tạo mô hình cho mỗi loại
        for model_type in self.base_models:
            model_key = self._get_model_key(model_type, regime)
            
            # Lấy tham số mô hình phù hợp với chế độ thị trường
            params = self._get_model_params_for_regime(model_type, regime) if regime else self.model_params[model_type]
            
            # Tạo mô hình
            model = self.MODEL_TYPES[model_type](**params)
            
            # Đào tạo mô hình
            start_time = time.time()
            model.fit(X_train_processed, y_train)
            training_time = time.time() - start_time
            
            # Lưu mô hình
            self.models[model_key] = model
            
            # Đánh giá mô hình
            y_pred = model.predict(X_test_processed)
            
            # Tính toán số liệu hiệu suất
            acc = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, average='weighted')
            recall = recall_score(y_test, y_pred, average='weighted')
            f1 = f1_score(y_test, y_pred, average='weighted')
            
            # Lưu số liệu
            model_metrics = {
                'accuracy': acc,
                'precision': precision,
                'recall': recall,
                'f1_score': f1,
                'training_time': training_time,
                'n_samples': len(X_train)
            }
            
            self.model_metrics[model_key] = model_metrics
            metrics[model_key] = model_metrics
            
            logger.info(f"Đã đào tạo {model_key}: Accuracy={acc:.4f}, F1={f1:.4f}, Thời gian={training_time:.2f}s")
            
            # Lưu độ quan trọng của tính năng nếu mô hình hỗ trợ
            if hasattr(model, 'feature_importances_'):
                self.feature_importances[model_key] = model.feature_importances_
        
        # Đào tạo mô hình tổng hợp nếu cần
        if self.use_ensemble and len(self.base_models) > 1:
            logger.info("Đào tạo mô hình tổng hợp...")
            self._train_ensemble_model(X_train_processed, y_train, X_test_processed, y_test, regime)
        
        return metrics
    
    def _train_ensemble_model(self, X_train, y_train, X_test, y_test, regime=None):
        """
        Đào tạo mô hình tổng hợp bằng cách kết hợp các dự đoán từ các mô hình cơ sở
        """
        # Đảm bảo y_train và y_test chỉ chứa các giá trị nguyên (0, 1, 2, ...)
        y_train_classes = np.unique(y_train)
        y_test_classes = np.unique(y_test)
        num_classes = max(len(y_train_classes), len(y_test_classes))
        
        # Tạo đặc trưng mới bằng dự đoán xác suất từ các mô hình cơ sở
        ensemble_features_train = np.zeros((X_train.shape[0], len(self.base_models) * num_classes))
        ensemble_features_test = np.zeros((X_test.shape[0], len(self.base_models) * num_classes))
        
        col_idx = 0
        for model_type in self.base_models:
            model_key = self._get_model_key(model_type, regime)
            model = self.models[model_key]
            
            if hasattr(model, 'predict_proba'):
                proba_train = model.predict_proba(X_train)
                proba_test = model.predict_proba(X_test)
                
                n_classes = proba_train.shape[1]
                ensemble_features_train[:, col_idx:col_idx+n_classes] = proba_train
                ensemble_features_test[:, col_idx:col_idx+n_classes] = proba_test
                col_idx += n_classes
        
        # Đào tạo mô hình meta để kết hợp các dự đoán
        meta_model = LogisticRegression(C=10.0, class_weight='balanced', random_state=42, max_iter=1000)
        meta_model.fit(ensemble_features_train, y_train)
        
        # Đánh giá mô hình tổng hợp
        y_pred = meta_model.predict(ensemble_features_test)
        
        # Tính toán số liệu hiệu suất
        acc = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average='weighted')
        recall = recall_score(y_test, y_pred, average='weighted')
        f1 = f1_score(y_test, y_pred, average='weighted')
        
        # Lưu mô hình và số liệu
        ensemble_key = f"ensemble_{regime}" if regime else "ensemble"
        self.models[ensemble_key] = meta_model
        
        model_metrics = {
            'accuracy': acc,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'n_samples': len(X_train)
        }
        
        self.model_metrics[ensemble_key] = model_metrics
        
        logger.info(f"Đã đào tạo {ensemble_key}: Accuracy={acc:.4f}, F1={f1:.4f}")
    
    def predict(self, X, regime=None):
        """
        Dự đoán sử dụng mô hình phù hợp nhất cho chế độ thị trường hiện tại
        
        Args:
            X: Tính năng đầu vào
            regime: Chế độ thị trường hiện tại
            
        Returns:
            y_pred: Nhãn dự đoán
            probas: Xác suất dự đoán
        """
        if len(self.models) == 0:
            logger.error("Không có mô hình nào được đào tạo")
            return None, None
        
        # Tiền xử lý dữ liệu
        X_processed = self._preprocess_features(X, y=None, regime=regime, is_training=False)
        
        # Sử dụng mô hình tổng hợp nếu có
        if self.use_ensemble:
            ensemble_key = f"ensemble_{regime}" if regime and self.use_model_per_regime else "ensemble"
            if ensemble_key in self.models:
                # Xác định số lượng lớp dự kiến dựa vào mô hình đã đào tạo
                num_classes = 2  # Giá trị mặc định (binary classification)
                
                # Tạo đặc trưng tổng hợp
                ensemble_features = np.zeros((X_processed.shape[0], len(self.base_models) * num_classes))
                
                col_idx = 0
                for model_type in self.base_models:
                    model_key = self._get_model_key(model_type, regime)
                    if model_key in self.models:
                        model = self.models[model_key]
                        if hasattr(model, 'predict_proba'):
                            proba = model.predict_proba(X_processed)
                            n_classes = proba.shape[1]
                            ensemble_features[:, col_idx:col_idx+n_classes] = proba
                            col_idx += n_classes
                
                # Dự đoán bằng mô hình tổng hợp
                meta_model = self.models[ensemble_key]
                y_pred = meta_model.predict(ensemble_features)
                probas = meta_model.predict_proba(ensemble_features)
                
                logger.info(f"Dự đoán bằng mô hình tổng hợp {ensemble_key}")
                return y_pred, probas
        
        # Sử dụng mô hình dành riêng cho chế độ thị trường nếu có
        if regime and self.use_model_per_regime:
            best_model_key = None
            best_f1_score = -1
            
            # Tìm mô hình tốt nhất cho chế độ thị trường hiện tại
            for model_key in self.models:
                if regime in model_key and model_key in self.model_metrics:
                    f1_score = self.model_metrics[model_key].get('f1_score', 0)
                    if f1_score > best_f1_score:
                        best_f1_score = f1_score
                        best_model_key = model_key
            
            if best_model_key:
                model = self.models[best_model_key]
                y_pred = model.predict(X_processed)
                
                if hasattr(model, 'predict_proba'):
                    probas = model.predict_proba(X_processed)
                else:
                    probas = None
                
                logger.info(f"Dự đoán bằng mô hình tốt nhất cho chế độ {regime}: {best_model_key}")
                return y_pred, probas
        
        # Sử dụng mô hình mặc định tốt nhất
        best_model_key = None
        best_f1_score = -1
        
        for model_key in self.models:
            if model_key in self.model_metrics and 'ensemble' not in model_key:
                f1_score = self.model_metrics[model_key].get('f1_score', 0)
                if f1_score > best_f1_score:
                    best_f1_score = f1_score
                    best_model_key = model_key
        
        if best_model_key:
            model = self.models[best_model_key]
            y_pred = model.predict(X_processed)
            
            if hasattr(model, 'predict_proba'):
                probas = model.predict_proba(X_processed)
            else:
                probas = None
            
            logger.info(f"Dự đoán bằng mô hình mặc định tốt nhất: {best_model_key}")
            return y_pred, probas
        
        logger.error("Không tìm thấy mô hình phù hợp")
        return None, None
    
    def save_models(self, directory='models'):
        """
        Lưu tất cả các mô hình đã đào tạo
        
        Args:
            directory: Thư mục để lưu mô hình
        """
        try:
            # Kiểm tra nếu đường dẫn chứa .joblib, thì lấy thư mục cha
            if '.joblib' in directory:
                parent_dir = os.path.dirname(directory)
                os.makedirs(parent_dir, exist_ok=True)
                base_path = parent_dir
            else:
                # Nếu không, sử dụng như thư mục
                os.makedirs(directory, exist_ok=True)
                base_path = directory
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(base_path, f'ml_models_{timestamp}.pkl')
            
            save_data = {
                'models': self.models,
                'scalers': self.scalers,
                'feature_selectors': self.feature_selectors,
                'feature_importances': self.feature_importances,
                'model_metrics': self.model_metrics,
                'base_models': self.base_models,
                'use_model_per_regime': self.use_model_per_regime,
                'feature_selection': self.feature_selection,
                'use_ensemble': self.use_ensemble,
                'selected_features': self.selected_features,
                'timestamp': timestamp
            }
            
            joblib.dump(save_data, filename)
            logger.info(f"Đã lưu mô hình vào {filename}")
            
            return filename
        except Exception as e:
            logger.error(f"Lỗi khi lưu mô hình: {str(e)}")
            # Dự phòng: lưu trong thư mục models gốc
            fallback_dir = 'models' 
            os.makedirs(fallback_dir, exist_ok=True)
            fallback_filename = os.path.join(fallback_dir, f'ml_models_backup_{timestamp}.pkl')
            joblib.dump(save_data, fallback_filename)
            logger.info(f"Đã lưu mô hình dự phòng vào {fallback_filename}")
            return fallback_filename
    
    def load_models(self, filename):
        """
        Tải các mô hình đã lưu
        
        Args:
            filename: Đường dẫn đến file mô hình
            
        Returns:
            success: True nếu tải thành công, False nếu thất bại
        """
        try:
            # Kiểm tra nếu đường dẫn là thư mục
            if os.path.isdir(filename):
                # Nếu là thư mục, tìm file pkl mới nhất
                model_files = []
                for root, dirs, files in os.walk(filename):
                    for file in files:
                        if file.endswith('.pkl'):
                            model_files.append(os.path.join(root, file))
                
                if not model_files:
                    logger.error(f"Không tìm thấy file mô hình nào trong thư mục {filename}")
                    return False
                
                # Lấy file mới nhất dựa trên ngày sửa đổi
                latest_model = max(model_files, key=os.path.getmtime)
                logger.info(f"Tải mô hình mới nhất: {latest_model}")
                actual_file = latest_model
            else:
                actual_file = filename
            
            # Tải mô hình từ file
            save_data = joblib.load(actual_file)
            
            self.models = save_data['models']
            self.scalers = save_data['scalers']
            self.feature_selectors = save_data.get('feature_selectors', {})
            self.feature_importances = save_data.get('feature_importances', {})
            self.model_metrics = save_data.get('model_metrics', {})
            self.base_models = save_data.get('base_models', self.base_models)
            self.use_model_per_regime = save_data.get('use_model_per_regime', self.use_model_per_regime)
            self.feature_selection = save_data.get('feature_selection', self.feature_selection)
            self.use_ensemble = save_data.get('use_ensemble', self.use_ensemble)
            self.selected_features = save_data.get('selected_features', {})
            
            logger.info(f"Đã tải mô hình từ {actual_file}")
            logger.info(f"Số lượng mô hình: {len(self.models)}")
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tải mô hình: {str(e)}")
            return False
    
    def evaluate_models(self, X, y, regime=None):
        """
        Đánh giá tất cả các mô hình trên bộ dữ liệu mới
        
        Args:
            X: Tính năng đầu vào
            y: Nhãn đích
            regime: Chế độ thị trường hiện tại
            
        Returns:
            eval_metrics: Kết quả đánh giá
        """
        eval_metrics = {}
        
        # Tiền xử lý dữ liệu
        X_processed = self._preprocess_features(X, y=None, regime=regime, is_training=False)
        
        for model_key, model in self.models.items():
            # Bỏ qua các mô hình không phù hợp với chế độ thị trường hiện tại
            if regime and self.use_model_per_regime and regime not in model_key and 'ensemble' not in model_key:
                continue
                
            try:
                y_pred = model.predict(X_processed)
                
                # Tính toán số liệu hiệu suất
                acc = accuracy_score(y, y_pred)
                precision = precision_score(y, y_pred, average='weighted')
                recall = recall_score(y, y_pred, average='weighted')
                f1 = f1_score(y, y_pred, average='weighted')
                
                model_eval = {
                    'accuracy': acc,
                    'precision': precision,
                    'recall': recall,
                    'f1_score': f1
                }
                
                eval_metrics[model_key] = model_eval
                
                logger.info(f"Đánh giá {model_key}: Accuracy={acc:.4f}, F1={f1:.4f}")
            except Exception as e:
                logger.error(f"Lỗi khi đánh giá {model_key}: {str(e)}")
        
        return eval_metrics
    
    def get_feature_importance(self, feature_names=None, model_key=None):
        """
        Lấy độ quan trọng của tính năng cho mô hình cụ thể
        
        Args:
            feature_names: Danh sách tên tính năng
            model_key: Khóa mô hình cần lấy độ quan trọng
            
        Returns:
            feature_importance: Dictionary chứa độ quan trọng của tính năng
        """
        if not self.feature_importances:
            return {}
            
        if model_key and model_key in self.feature_importances:
            importances = self.feature_importances[model_key]
            
            if feature_names and len(feature_names) == len(importances):
                return {name: importance for name, importance in zip(feature_names, importances)}
            else:
                return {f"feature_{i}": importance for i, importance in enumerate(importances)}
        
        # Trả về độ quan trọng trung bình của tất cả các mô hình
        avg_importance = {}
        
        for model_key, importances in self.feature_importances.items():
            if feature_names and len(feature_names) == len(importances):
                for i, name in enumerate(feature_names):
                    if name not in avg_importance:
                        avg_importance[name] = []
                    avg_importance[name].append(importances[i])
            else:
                for i, importance in enumerate(importances):
                    feature_name = f"feature_{i}"
                    if feature_name not in avg_importance:
                        avg_importance[feature_name] = []
                    avg_importance[feature_name].append(importance)
        
        # Tính trung bình
        for feature, values in avg_importance.items():
            avg_importance[feature] = sum(values) / len(values)
            
        return avg_importance
    
    def get_best_models_by_regime(self):
        """
        Lấy mô hình tốt nhất cho mỗi chế độ thị trường
        
        Returns:
            best_models: Dictionary chứa mô hình tốt nhất cho mỗi chế độ
        """
        best_models = {}
        
        for regime in self.MARKET_REGIMES:
            best_model_key = None
            best_f1_score = -1
            
            for model_key, metrics in self.model_metrics.items():
                if regime in model_key and 'f1_score' in metrics:
                    f1_score = metrics['f1_score']
                    if f1_score > best_f1_score:
                        best_f1_score = f1_score
                        best_model_key = model_key
            
            if best_model_key:
                best_models[regime] = {
                    'model_key': best_model_key,
                    'f1_score': best_f1_score,
                    'metrics': self.model_metrics[best_model_key]
                }
        
        return best_models
    
    def prepare_features_for_prediction(self, df):
        """
        Chuẩn bị tính năng cho dự đoán
        
        Args:
            df: DataFrame gốc
            
        Returns:
            X: Tính năng đã chuẩn bị
        """
        # Loại bỏ các cột không phải tính năng
        cols_to_drop = ['open_time', 'close_time', 'datetime', 'date', 'time']
        feature_cols = [col for col in df.columns if col not in cols_to_drop]
        
        # Loại bỏ các cột mục tiêu
        target_cols = ['target', 'label', 'signal', 'next_return']
        feature_cols = [col for col in feature_cols if col not in target_cols]
        
        # Tạo X
        X = df[feature_cols].copy()
        
        # Xử lý giá trị thiếu
        X = X.fillna(0)
        
        # Xử lý giá trị vô cùng
        X = X.replace([np.inf, -np.inf], 0)
        
        return X
    
    def prepare_target_for_training(self, df, lookahead=1, threshold=0.0):
        """
        Chuẩn bị nhãn mục tiêu cho đào tạo
        
        Args:
            df: DataFrame gốc
            lookahead: Số chu kỳ nhìn trước
            threshold: Ngưỡng để xác định tín hiệu (phần trăm thay đổi giá)
            
        Returns:
            y: Nhãn mục tiêu
        """
        if 'close' not in df.columns:
            logger.error("Cột 'close' không có trong DataFrame")
            return None
            
        # Tạo một bản sao để tránh ảnh hưởng đến DataFrame gốc
        df_copy = df.copy()
        
        # Tính toán phần trăm thay đổi giá sau lookahead chu kỳ
        df_copy['future_return'] = df_copy['close'].shift(-lookahead) / df_copy['close'] - 1
        
        # Tạo nhãn
        y = np.zeros(len(df_copy))
        mask_up = df_copy['future_return'] > threshold
        mask_down = df_copy['future_return'] < -threshold
        
        # Thay thế giá trị NaN bằng False trước khi gán
        mask_up = mask_up.fillna(False)
        mask_down = mask_down.fillna(False)
        
        y[mask_up] = 1  # Tăng
        y[mask_down] = -1  # Giảm
        
        # Xử lý các giá trị NaN ở cuối
        if lookahead > 0:
            # Cắt bỏ các hàng cuối cùng có giá trị NaN
            y = y[:-lookahead]
        
        # Đảm bảo kích thước y khớp với X
        X = self.prepare_features_for_prediction(df)
        if len(X) > len(y):
            # Cắt X để khớp với y
            X = X[:len(y)]
            logger.info(f"Đã cắt X từ {len(df)} xuống {len(y)} để khớp với y")
        elif len(X) < len(y):
            # Cắt y để khớp với X
            y = y[:len(X)]
            logger.info(f"Đã cắt y từ {len(df)-lookahead} xuống {len(X)} để khớp với X")
        
        # Thông báo kích thước cuối cùng
        logger.info(f"Kích thước cuối cùng: X = {len(X)}, y = {len(y)}")
        
        return y

    def backtest_strategy(self, df, initial_balance=10000, commission=0.001):
        """
        Backtest chiến lược dựa trên dự đoán mô hình
        
        Args:
            df: DataFrame với dữ liệu giá
            initial_balance: Số dư ban đầu
            commission: Phí giao dịch (phần trăm)
            
        Returns:
            results: Kết quả backtest
        """
        if len(self.models) == 0:
            logger.error("Không có mô hình nào được đào tạo")
            return None
        
        # Chuẩn bị tính năng
        X = self.prepare_features_for_prediction(df)
        
        # Tách dữ liệu hợp lệ (loại bỏ hàng đầu có NaN sau khi tính toán các chỉ báo)
        valid_idx = X.dropna().index
        X_valid = X.loc[valid_idx]
        df_valid = df.loc[valid_idx].copy()
        
        # Dự đoán tín hiệu
        y_pred, probas = self.predict(X_valid)
        
        if y_pred is None:
            logger.error("Không thể dự đoán tín hiệu")
            return None
        
        # Thêm tín hiệu vào DataFrame
        df_valid['signal'] = y_pred
        
        # Khởi tạo các biến theo dõi
        balance = initial_balance
        position = 0
        entry_price = 0
        trades = []
        equity_curve = [balance]
        
        # Mô phỏng giao dịch
        for i in range(1, len(df_valid)):
            current_row = df_valid.iloc[i]
            prev_row = df_valid.iloc[i-1]
            close_price = current_row['close']
            
            # Cập nhật giá trị vốn nếu đang trong vị thế
            if position != 0:
                equity_curve.append(balance + position * (close_price - entry_price))
            else:
                equity_curve.append(balance)
            
            # Kiểm tra tín hiệu
            signal = prev_row['signal']
            
            # Mở vị thế mới nếu chưa có
            if position == 0:
                if signal == 1:  # Tín hiệu mua
                    position = balance / close_price
                    entry_price = close_price
                    trade_cost = balance * commission
                    balance -= trade_cost
                    
                    trades.append({
                        'type': 'buy',
                        'entry_time': current_row.name,
                        'entry_price': close_price,
                        'size': position,
                        'cost': trade_cost
                    })
                elif signal == -1:  # Tín hiệu bán
                    position = -balance / close_price
                    entry_price = close_price
                    trade_cost = balance * commission
                    balance -= trade_cost
                    
                    trades.append({
                        'type': 'sell',
                        'entry_time': current_row.name,
                        'entry_price': close_price,
                        'size': abs(position),
                        'cost': trade_cost
                    })
            
            # Đóng vị thế nếu có tín hiệu ngược hoặc không có tín hiệu
            elif (position > 0 and signal <= 0) or (position < 0 and signal >= 0):
                # Tính lợi nhuận
                pnl = position * (close_price - entry_price)
                trade_cost = abs(position) * close_price * commission
                balance += pnl - trade_cost
                
                # Ghi nhận giao dịch
                last_trade = trades[-1]
                last_trade.update({
                    'exit_time': current_row.name,
                    'exit_price': close_price,
                    'pnl': pnl,
                    'return': pnl / (abs(position) * entry_price),
                    'cost': last_trade['cost'] + trade_cost
                })
                
                # Đặt lại vị thế
                position = 0
                entry_price = 0
                
                # Mở vị thế mới ngay lập tức nếu có tín hiệu
                if signal == 1:  # Tín hiệu mua
                    position = balance / close_price
                    entry_price = close_price
                    trade_cost = balance * commission
                    balance -= trade_cost
                    
                    trades.append({
                        'type': 'buy',
                        'entry_time': current_row.name,
                        'entry_price': close_price,
                        'size': position,
                        'cost': trade_cost
                    })
                elif signal == -1:  # Tín hiệu bán
                    position = -balance / close_price
                    entry_price = close_price
                    trade_cost = balance * commission
                    balance -= trade_cost
                    
                    trades.append({
                        'type': 'sell',
                        'entry_time': current_row.name,
                        'entry_price': close_price,
                        'size': abs(position),
                        'cost': trade_cost
                    })
        
        # Đóng vị thế cuối cùng nếu còn
        if position != 0:
            close_price = df_valid.iloc[-1]['close']
            
            # Tính lợi nhuận
            pnl = position * (close_price - entry_price)
            trade_cost = abs(position) * close_price * commission
            balance += pnl - trade_cost
            
            # Ghi nhận giao dịch
            last_trade = trades[-1]
            last_trade.update({
                'exit_time': df_valid.index[-1],
                'exit_price': close_price,
                'pnl': pnl,
                'return': pnl / (abs(position) * entry_price),
                'cost': last_trade['cost'] + trade_cost
            })
        
        # Tính toán các số liệu hiệu suất
        final_balance = balance
        total_return = (final_balance / initial_balance - 1) * 100
        
        # Tính toán drawdown
        equity_array = np.array(equity_curve)
        peak = np.maximum.accumulate(equity_array)
        drawdown = 100 * ((peak - equity_array) / peak)
        max_drawdown = drawdown.max()
        
        # Tính toán thông tin giao dịch
        n_trades = len([t for t in trades if 'exit_time' in t])
        win_trades = len([t for t in trades if 'pnl' in t and t['pnl'] > 0])
        loss_trades = n_trades - win_trades
        win_rate = 100 * win_trades / n_trades if n_trades > 0 else 0
        
        # Tính toán Sharpe Ratio
        daily_returns = np.diff(equity_array) / equity_array[:-1]
        sharpe_ratio = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252) if len(daily_returns) > 0 and np.std(daily_returns) > 0 else 0
        
        results = {
            'initial_balance': initial_balance,
            'final_balance': final_balance,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'n_trades': n_trades,
            'win_trades': win_trades,
            'loss_trades': loss_trades,
            'win_rate': win_rate,
            'trades': trades,
            'equity_curve': equity_curve,
            'predictions': df_valid['signal'].values
        }
        
        logger.info(f"Backtest kết thúc: Lợi nhuận={total_return:.2f}%, Win Rate={win_rate:.2f}%, Sharpe={sharpe_ratio:.2f}")
        
        return results