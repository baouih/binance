#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Multi-Task Model - Mô hình đa nhiệm vụ cho giao dịch tiền điện tử
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Union, Optional, Any, Callable

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('multi_task_model')

class MultiTaskModel:
    """
    Lớp mô hình đa nhiệm vụ
    """
    
    def __init__(
        self,
        input_dim: int = 10,
        shared_layers: List[int] = [64, 32],
        task_specific_layers: List[int] = [16],
        tasks: List[str] = ['price_movement', 'volatility', 'regime'],
        learning_rate: float = 0.001,
        dropout_rate: float = 0.2,
        model_dir: str = 'ml_models'
    ):
        """
        Khởi tạo mô hình đa nhiệm vụ
        
        Args:
            input_dim: Số chiều đầu vào
            shared_layers: Danh sách số neuron trong các lớp chung
            task_specific_layers: Danh sách số neuron trong các lớp riêng cho từng nhiệm vụ
            tasks: Danh sách các nhiệm vụ
            learning_rate: Tốc độ học
            dropout_rate: Tỷ lệ dropout
            model_dir: Thư mục lưu mô hình
        """
        self.input_dim = input_dim
        self.shared_layers = shared_layers
        self.task_specific_layers = task_specific_layers
        self.tasks = tasks
        self.learning_rate = learning_rate
        self.dropout_rate = dropout_rate
        self.model_dir = model_dir
        
        # Tạo thư mục lưu mô hình nếu chưa tồn tại
        os.makedirs(model_dir, exist_ok=True)
        
        # Các mô hình
        self.shared_model = None
        self.task_models = {}
        self.is_trained = False
        
        logger.info(f"Đã khởi tạo MultiTaskModel với {len(tasks)} nhiệm vụ: {tasks}")
        
        # Ghi nhớ dự đoán gần đây nhất
        self.recent_predictions = {}
        
        # Mô phỏng mô hình được huấn luyện
        self._simulate_trained_model()
    
    def _simulate_trained_model(self):
        """
        Mô phỏng một mô hình đã được huấn luyện (cho mục đích kiểm thử)
        """
        self.is_trained = True
        
        # Thiết lập thông số mô hình
        self.model_info = {
            'input_dim': self.input_dim,
            'shared_layers': self.shared_layers,
            'task_specific_layers': self.task_specific_layers,
            'tasks': self.tasks,
            'learning_rate': self.learning_rate,
            'dropout_rate': self.dropout_rate
        }
        
        # Thiết lập các tham số giả cho dự đoán
        self.simulation_params = {
            'price_movement': {
                'mean': 0.0,
                'std': 0.02,
                'trend_factor': 0.6,  # Tác động của xu hướng
                'vol_factor': 0.3,    # Tác động của biến động
                'price_impact': 0.5   # Tác động của biến động giá
            },
            'volatility': {
                'base': 0.01,
                'price_factor': 0.5,  # Tác động của biến động giá
                'volume_factor': 0.3, # Tác động của khối lượng
                'trend_factor': 0.2   # Tác động của xu hướng
            },
            'regime': {
                'base_probs': {
                    'trending_up': 0.2,
                    'trending_down': 0.2,
                    'ranging': 0.4,
                    'volatile': 0.1,
                    'neutral': 0.1
                },
                'price_impact': 0.5,  # Tác động của giá
                'vol_impact': 0.3     # Tác động của biến động
            }
        }
        
        logger.info(f"Đã mô phỏng mô hình đã huấn luyện cho {len(self.tasks)} nhiệm vụ")
    
    def predict_dummy(self, X: np.ndarray) -> Dict[str, Any]:
        """
        Thực hiện dự đoán giả lập (cho mục đích kiểm thử)
        
        Args:
            X: Dữ liệu đầu vào, shape (n_samples, input_dim)
        
        Returns:
            Dict chứa kết quả dự đoán cho từng nhiệm vụ
        """
        if not self.is_trained:
            logger.warning("Mô hình chưa được huấn luyện, kết quả dự đoán sẽ không chính xác")
        
        # Kiểm tra dữ liệu đầu vào
        if X.shape[1] != self.input_dim:
            logger.warning(f"Chiều dữ liệu đầu vào ({X.shape[1]}) không khớp với input_dim ({self.input_dim})")
            # Cắt bớt hoặc pad để có đúng kích thước
            if X.shape[1] > self.input_dim:
                X = X[:, :self.input_dim]
            else:
                pad_width = ((0, 0), (0, self.input_dim - X.shape[1]))
                X = np.pad(X, pad_width, mode='constant')
        
        # Kết quả dự đoán
        predictions = {}
        
        # Mô phỏng dự đoán cho từng nhiệm vụ
        for task in self.tasks:
            if task == 'price_movement':
                # Mô phỏng dự đoán hướng giá
                params = self.simulation_params[task]
                
                # Tạo dự đoán ngẫu nhiên với xu hướng
                last_sample = X[-1] if len(X) > 0 else np.zeros(self.input_dim)
                
                # Đánh giá xu hướng từ dữ liệu
                if len(X) > 5:
                    recent_trend = np.mean(X[-5:, 0]) - np.mean(X[:5, 0])
                else:
                    recent_trend = 0
                
                # Tạo dự đoán với ảnh hưởng của xu hướng
                trend_influence = np.sign(recent_trend) * abs(recent_trend) * params['trend_factor']
                base_prediction = np.random.normal(params['mean'] + trend_influence, params['std'])
                
                predictions[task] = {
                    'direction': 1 if base_prediction > 0 else (-1 if base_prediction < 0 else 0),
                    'probability': abs(base_prediction) * 5,  # Chuyển đổi thành xác suất (0-1)
                    'strength': abs(base_prediction) * 10     # Độ mạnh tín hiệu (0-1)
                }
            
            elif task == 'volatility':
                # Mô phỏng dự đoán biến động
                params = self.simulation_params[task]
                
                # Ước tính biến động từ dữ liệu
                if len(X) > 10:
                    price_std = np.std(X[-10:, 0]) / np.mean(X[-10:, 0])
                else:
                    price_std = 0.01
                
                vol_prediction = (
                    params['base'] + 
                    price_std * params['price_factor']
                )
                
                predictions[task] = {
                    'expected_volatility': vol_prediction,
                    'high_volatility_prob': min(vol_prediction * 20, 1.0),  # Xác suất biến động cao
                    'percentile': min(int(vol_prediction * 100 * 2), 99)    # Phân vị biến động
                }
            
            elif task == 'regime':
                # Mô phỏng dự đoán chế độ thị trường
                params = self.simulation_params[task]
                base_probs = params['base_probs']
                
                # Xác định xu hướng và biến động từ dữ liệu
                if len(X) > 20:
                    price_trend = np.mean(X[-5:, 0]) - np.mean(X[-20:-15, 0])
                    normalized_trend = np.clip(price_trend / np.mean(X[-20:, 0]), -0.1, 0.1)
                    
                    price_vol = np.std(X[-20:, 0]) / np.mean(X[-20:, 0])
                    normalized_vol = np.clip(price_vol / 0.05, 0, 2)
                else:
                    normalized_trend = 0
                    normalized_vol = 0.5
                
                # Điều chỉnh xác suất dựa trên xu hướng và biến động
                regime_probs = base_probs.copy()
                
                # Xu hướng tăng
                if normalized_trend > 0.02:
                    regime_probs['trending_up'] += normalized_trend * params['price_impact']
                    regime_probs['trending_down'] -= normalized_trend * params['price_impact'] * 0.5
                # Xu hướng giảm
                elif normalized_trend < -0.02:
                    regime_probs['trending_down'] += abs(normalized_trend) * params['price_impact']
                    regime_probs['trending_up'] -= abs(normalized_trend) * params['price_impact'] * 0.5
                
                # Biến động cao
                if normalized_vol > 1.0:
                    regime_probs['volatile'] += (normalized_vol - 1.0) * params['vol_impact']
                    regime_probs['ranging'] -= (normalized_vol - 1.0) * params['vol_impact'] * 0.5
                # Biến động thấp
                elif normalized_vol < 0.5:
                    regime_probs['ranging'] += (0.5 - normalized_vol) * params['vol_impact']
                    regime_probs['volatile'] -= (0.5 - normalized_vol) * params['vol_impact'] * 0.5
                
                # Chuẩn hóa xác suất
                total_prob = sum(regime_probs.values())
                normalized_probs = {k: v / total_prob for k, v in regime_probs.items()}
                
                # Xác định chế độ có xác suất cao nhất
                max_regime = max(normalized_probs, key=normalized_probs.get)
                
                predictions[task] = {
                    'regime': max_regime,
                    'probabilities': normalized_probs
                }
            
            else:
                # Nhiệm vụ không được hỗ trợ
                logger.warning(f"Nhiệm vụ không được hỗ trợ: {task}")
                predictions[task] = None
        
        # Lưu dự đoán gần đây nhất
        self.recent_predictions = predictions
        
        return predictions
    
    def train_dummy(self, X: np.ndarray, y: Dict[str, np.ndarray], epochs: int = 10) -> Dict[str, Any]:
        """
        Mô phỏng huấn luyện mô hình (cho mục đích kiểm thử)
        
        Args:
            X: Dữ liệu đầu vào, shape (n_samples, input_dim)
            y: Dict chứa nhãn cho từng nhiệm vụ
            epochs: Số epoch huấn luyện
        
        Returns:
            Dict chứa lịch sử huấn luyện
        """
        logger.info(f"Mô phỏng huấn luyện mô hình cho {len(self.tasks)} nhiệm vụ với {epochs} epochs")
        
        # Kiểm tra dữ liệu
        if X.shape[1] != self.input_dim:
            logger.warning(f"Chiều dữ liệu đầu vào ({X.shape[1]}) không khớp với input_dim ({self.input_dim})")
        
        # Kiểm tra nhãn
        for task in self.tasks:
            if task not in y:
                logger.warning(f"Không tìm thấy nhãn cho nhiệm vụ: {task}")
        
        # Mô phỏng lịch sử huấn luyện
        history = {task: {'loss': [], 'val_loss': []} for task in self.tasks}
        
        # Mô phỏng các epoch
        for epoch in range(epochs):
            for task in self.tasks:
                if task in y:
                    # Mô phỏng loss giảm dần
                    base_loss = 0.5 * (1 - epoch / epochs)
                    train_loss = base_loss + np.random.normal(0, 0.1)
                    val_loss = base_loss * 1.2 + np.random.normal(0, 0.15)
                    
                    history[task]['loss'].append(max(0.1, train_loss))
                    history[task]['val_loss'].append(max(0.1, val_loss))
            
            logger.info(f"Epoch {epoch+1}/{epochs} - loss: {train_loss:.4f} - val_loss: {val_loss:.4f}")
        
        # Đánh dấu mô hình đã được huấn luyện
        self.is_trained = True
        
        return history
    
    def save(self, filepath: Optional[str] = None) -> str:
        """
        Lưu mô hình
        
        Args:
            filepath: Đường dẫn file lưu mô hình, None sẽ tạo tự động
        
        Returns:
            Đường dẫn đã lưu
        """
        if not self.is_trained:
            logger.warning("Mô hình chưa được huấn luyện, sẽ lưu mô hình rỗng")
        
        # Tạo đường dẫn tự động nếu không chỉ định
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(self.model_dir, f"multi_task_model_{timestamp}.json")
        
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Dữ liệu mô hình
        model_data = {
            'input_dim': self.input_dim,
            'shared_layers': self.shared_layers,
            'task_specific_layers': self.task_specific_layers,
            'tasks': self.tasks,
            'learning_rate': self.learning_rate,
            'dropout_rate': self.dropout_rate,
            'is_trained': self.is_trained,
            'simulation_params': self.simulation_params,
            'timestamp': datetime.now().isoformat()
        }
        
        # Lưu dữ liệu mô hình
        try:
            with open(filepath, 'w') as f:
                json.dump(model_data, f, indent=2)
            logger.info(f"Đã lưu mô hình tại: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Lỗi khi lưu mô hình: {str(e)}")
            return ""
    
    def load(self, filepath: str) -> bool:
        """
        Tải mô hình
        
        Args:
            filepath: Đường dẫn file mô hình
        
        Returns:
            True nếu tải thành công, False nếu thất bại
        """
        try:
            with open(filepath, 'r') as f:
                model_data = json.load(f)
            
            # Khôi phục tham số mô hình
            self.input_dim = model_data['input_dim']
            self.shared_layers = model_data['shared_layers']
            self.task_specific_layers = model_data['task_specific_layers']
            self.tasks = model_data['tasks']
            self.learning_rate = model_data['learning_rate']
            self.dropout_rate = model_data['dropout_rate']
            self.is_trained = model_data['is_trained']
            
            if 'simulation_params' in model_data:
                self.simulation_params = model_data['simulation_params']
            
            logger.info(f"Đã tải mô hình từ: {filepath}")
            return True
        
        except Exception as e:
            logger.error(f"Lỗi khi tải mô hình: {str(e)}")
            return False

if __name__ == "__main__":
    # Demo
    model = MultiTaskModel()
    
    # Tạo dữ liệu mẫu
    n_samples = 100
    input_dim = 10
    X = np.random.randn(n_samples, input_dim)
    
    # Dự đoán
    predictions = model.predict_dummy(X)
    print("Dự đoán:")
    for task, pred in predictions.items():
        print(f"- {task}: {pred}")
    
    # Mô phỏng huấn luyện
    y = {
        'price_movement': np.random.choice([-1, 0, 1], size=(n_samples,)),
        'volatility': np.random.rand(n_samples),
        'regime': np.random.choice(['trending_up', 'trending_down', 'ranging', 'volatile', 'neutral'], size=(n_samples,))
    }
    
    history = model.train_dummy(X, y, epochs=5)
    
    # Lưu mô hình
    model.save()