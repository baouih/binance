"""
Chiến lược giao dịch dựa trên mô hình học máy nâng cao
Sử dụng nhiều mô hình khác nhau cho các chế độ thị trường khác nhau
"""

import os
import logging
import numpy as np
import pandas as pd
from typing import Optional, Dict, List, Tuple

from app.strategy import Strategy
from app.market_regime_detector import MarketRegimeDetector
from app.advanced_ml_optimizer import AdvancedMLOptimizer

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('advanced_ml_strategy')

class AdvancedMLStrategy(Strategy):
    """
    Chiến lược giao dịch nâng cao dựa trên học máy 
    với tối ưu hóa cho từng chế độ thị trường
    """
    
    def __init__(self, ml_optimizer=None, market_regime_detector=None, model_path=None, 
                 probability_threshold=0.65, confidence_threshold=0.6, window_size=3):
        """
        Khởi tạo chiến lược ML nâng cao
        
        Args:
            ml_optimizer (AdvancedMLOptimizer): Bộ tối ưu hóa ML đã được cấu hình
            market_regime_detector (MarketRegimeDetector): Bộ phát hiện chế độ thị trường
            model_path (str): Đường dẫn đến file mô hình đã huấn luyện
            probability_threshold (float): Ngưỡng xác suất để ra tín hiệu
            confidence_threshold (float): Ngưỡng tin cậy để lọc tín hiệu
            window_size (int): Kích thước cửa sổ để lọc tín hiệu liên tục
        """
        super().__init__(name="AdvancedMLStrategy")
        
        # Kiểm tra và khởi tạo các thành phần
        if ml_optimizer is None:
            self.ml_optimizer = AdvancedMLOptimizer()
        else:
            self.ml_optimizer = ml_optimizer
            
        if market_regime_detector is None:
            self.market_regime_detector = MarketRegimeDetector()
        else:
            self.market_regime_detector = market_regime_detector
        
        self.probability_threshold = probability_threshold
        self.confidence_threshold = confidence_threshold
        self.window_size = window_size
        
        # Tải mô hình nếu được cung cấp
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)
        else:
            self.model_loaded = False
            if model_path:
                logger.warning(f"Không tìm thấy mô hình tại {model_path}")
        
        # Trạng thái chiến lược
        self.current_regime = "neutral"
        self.signal_history = []
        self.probability_history = []
        self.performance_by_regime = {}
        
        # Thống kê hiệu suất
        for regime in self.market_regime_detector.REGIMES:
            self.performance_by_regime[regime] = {
                'wins': 0,
                'losses': 0,
                'total_pnl': 0.0,
                'trades': 0
            }
        
        logger.info(f"Khởi tạo AdvancedMLStrategy với probability_threshold={probability_threshold}")
    
    def load_model(self, model_path):
        """
        Tải mô hình từ file
        
        Args:
            model_path (str): Đường dẫn đến file mô hình
            
        Returns:
            bool: True nếu tải thành công, False nếu thất bại
        """
        try:
            self.model_loaded = self.ml_optimizer.load_models(model_path)
            if self.model_loaded:
                logger.info(f"Đã tải mô hình ML thành công từ {model_path}")
            else:
                logger.error(f"Không thể tải mô hình từ {model_path}")
            return self.model_loaded
        except Exception as e:
            logger.error(f"Lỗi khi tải mô hình: {str(e)}")
            self.model_loaded = False
            return False
    
    def _detect_regime(self, dataframe):
        """
        Phát hiện chế độ thị trường hiện tại
        
        Args:
            dataframe (pandas.DataFrame): DataFrame với dữ liệu giá và chỉ báo
            
        Returns:
            str: Chế độ thị trường được phát hiện
        """
        previous_regime = self.current_regime
        
        try:
            self.current_regime = self.market_regime_detector.detect_regime(dataframe)
            
            if previous_regime != self.current_regime:
                logger.info(f"Chế độ thị trường thay đổi: {previous_regime} -> {self.current_regime}")
            
            return self.current_regime
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện chế độ thị trường: {str(e)}")
            return previous_regime
    
    def _prepare_features(self, dataframe):
        """
        Chuẩn bị tính năng cho dự đoán
        
        Args:
            dataframe (pandas.DataFrame): DataFrame với dữ liệu giá và chỉ báo
            
        Returns:
            pandas.DataFrame: DataFrame với các tính năng đã xử lý
        """
        # Loại bỏ các cột không phải tính năng
        cols_to_drop = ['open_time', 'close_time', 'datetime', 'date', 'time']
        feature_cols = [col for col in dataframe.columns if col not in cols_to_drop]
        
        # Loại bỏ các cột mục tiêu nếu có
        target_cols = ['target', 'label', 'signal', 'next_return']
        feature_cols = [col for col in feature_cols if col not in target_cols]
        
        # Tạo DataFrame tính năng
        X = dataframe[feature_cols].copy()
        
        # Xử lý giá trị thiếu
        X = X.fillna(0)
        
        # Xử lý giá trị vô cùng
        X = X.replace([np.inf, -np.inf], 0)
        
        return X
    
    def _apply_signal_filter(self, signal, probability):
        """
        Áp dụng bộ lọc tín hiệu để giảm thiểu tín hiệu sai
        
        Args:
            signal (int): Tín hiệu dự đoán (-1, 0, 1)
            probability (float): Xác suất của tín hiệu
            
        Returns:
            int: Tín hiệu đã lọc (-1, 0, 1)
        """
        # Cập nhật lịch sử tín hiệu
        self.signal_history.append(signal)
        self.probability_history.append(probability)
        
        # Chỉ giữ window_size tín hiệu gần nhất
        if len(self.signal_history) > self.window_size:
            self.signal_history.pop(0)
            self.probability_history.pop(0)
        
        # Nếu chưa đủ tín hiệu, trả về tín hiệu hiện tại
        if len(self.signal_history) < self.window_size:
            return signal
        
        # Kiểm tra sự nhất quán của tín hiệu
        if all(s == signal for s in self.signal_history):
            # Tất cả tín hiệu trong window đều giống nhau
            return signal
        
        # Kiểm tra xác suất trung bình
        avg_probability = sum(self.probability_history) / len(self.probability_history)
        if avg_probability >= self.confidence_threshold:
            # Xác suất trung bình đủ cao
            # Trả về tín hiệu phổ biến nhất
            from collections import Counter
            most_common = Counter(self.signal_history).most_common(1)[0]
            return most_common[0]
        
        # Mặc định, trả về không có tín hiệu
        return 0
    
    def generate_signal(self, dataframe):
        """
        Tạo tín hiệu giao dịch dựa trên dự đoán của mô hình học máy
        
        Args:
            dataframe (pandas.DataFrame): DataFrame với dữ liệu giá và chỉ báo
            
        Returns:
            int: Tín hiệu giao dịch (-1 cho bán, 0 cho giữ, 1 cho mua)
        """
        # Kiểm tra xem mô hình đã được tải chưa
        if not hasattr(self, 'model_loaded') or not self.model_loaded:
            logger.warning("Mô hình ML chưa được tải, không thể tạo tín hiệu")
            return 0
        
        try:
            # Phát hiện chế độ thị trường
            regime = self._detect_regime(dataframe)
            logger.info(f"Chế độ thị trường hiện tại: {regime}")
            
            # Chuẩn bị tính năng cho dự đoán
            X = self._prepare_features(dataframe)
            
            # Chỉ lấy hàng cuối cùng cho dự đoán
            X_latest = X.iloc[[-1]]
            
            # Dự đoán
            pred, probas = self.ml_optimizer.predict(X_latest, regime=regime)
            
            if pred is None:
                logger.warning("Không thể tạo dự đoán")
                return 0
            
            # Lấy tín hiệu từ dự đoán
            raw_signal = pred[0]
            
            # Xác định xác suất cho tín hiệu
            if probas is not None and len(probas) > 0:
                # Lấy xác suất cao nhất
                probability = np.max(probas[0])
                
                logger.info(f"Dự đoán ML: {raw_signal}, xác suất: {probability:.4f}")
                
                # Áp dụng ngưỡng xác suất
                if probability < self.probability_threshold:
                    logger.info(f"Xác suất {probability:.4f} < ngưỡng {self.probability_threshold}, giữ nguyên vị thế")
                    raw_signal = 0
            else:
                probability = 0.5
                logger.info(f"Không có xác suất dự đoán, sử dụng mặc định: {probability}")
            
            # Áp dụng bộ lọc tín hiệu
            filtered_signal = self._apply_signal_filter(raw_signal, probability)
            
            if filtered_signal != raw_signal:
                logger.info(f"Tín hiệu sau khi lọc: {filtered_signal} (gốc: {raw_signal})")
            
            return filtered_signal
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo tín hiệu ML: {str(e)}")
            return 0
    
    def update_performance(self, is_win, pnl, regime=None):
        """
        Cập nhật thống kê hiệu suất theo chế độ thị trường
        
        Args:
            is_win (bool): True nếu giao dịch thắng
            pnl (float): Lợi nhuận hoặc thua lỗ
            regime (str): Chế độ thị trường, nếu None sẽ sử dụng chế độ hiện tại
        """
        if regime is None:
            regime = self.current_regime
            
        if regime not in self.performance_by_regime:
            logger.warning(f"Chế độ thị trường không hợp lệ: {regime}")
            return
            
        stats = self.performance_by_regime[regime]
        
        if is_win:
            stats['wins'] += 1
        else:
            stats['losses'] += 1
            
        stats['total_pnl'] += pnl
        stats['trades'] += 1
        
        # Cập nhật cho thống kê chung
        self.market_regime_detector.update_regime_performance(regime, is_win, pnl)
        
        logger.info(f"Cập nhật hiệu suất cho chế độ {regime}: {stats['wins']}/{stats['trades']} giao dịch thắng, PnL: {stats['total_pnl']:.2f}%")
    
    def get_performance_by_regime(self):
        """
        Lấy thống kê hiệu suất theo chế độ thị trường
        
        Returns:
            dict: Thống kê hiệu suất
        """
        performance = {}
        
        for regime, stats in self.performance_by_regime.items():
            if stats['trades'] > 0:
                win_rate = stats['wins'] / stats['trades'] * 100
                avg_pnl = stats['total_pnl'] / stats['trades']
                
                performance[regime] = {
                    'win_rate': win_rate,
                    'avg_pnl': avg_pnl,
                    'total_pnl': stats['total_pnl'],
                    'trades': stats['trades']
                }
        
        return performance
    
    def get_strategy_info(self):
        """
        Lấy thông tin chiến lược
        
        Returns:
            dict: Thông tin chiến lược
        """
        info = {
            'name': self.name,
            'description': 'Chiến lược dựa trên học máy nâng cao với tối ưu hóa cho từng chế độ thị trường',
            'current_regime': self.current_regime,
            'probability_threshold': self.probability_threshold,
            'confidence_threshold': self.confidence_threshold,
            'model_loaded': getattr(self, 'model_loaded', False),
            'performance': self.get_performance_by_regime()
        }
        
        return info