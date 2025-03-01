"""
Module tự động cập nhật tham số chiến lược (Adaptive Parameter Tuner)

Module này cung cấp các cơ chế tự động tối ưu hóa và điều chỉnh các tham số của chiến lược
dựa trên điều kiện thị trường thay đổi và hiệu suất gần đây. Các công cụ bao gồm:

- Tự động phát hiện và chuyển đổi mô hình/chiến lược dựa trên chế độ thị trường
- Tối ưu hóa tham số theo chuỗi thời gian
- Kết hợp các chiến lược với hệ số động
- Điều chỉnh tự động stop loss/take profit theo biến động thị trường
- Auto-correlation của tham số tối ưu với các chỉ số thị trường

Module này nhằm mục đích cải thiện sự thích nghi của hệ thống với thị trường biến động.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Tuple, Union, Callable, Any
from datetime import datetime, timedelta
import logging
import json
import time
import os
from sklearn.model_selection import ParameterGrid
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.cluster import KMeans
from scipy.optimize import minimize
from scipy.stats import pearsonr
import joblib

# Cấu hình logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("adaptive_optimizer")

class AdaptiveParameterTuner:
    """Lớp tự động điều chỉnh tham số chiến lược theo điều kiện thị trường"""
    
    def __init__(self, base_parameters: Dict = None, parameter_ranges: Dict = None,
                lookback_periods: int = 20, max_optimization_history: int = 100,
                data_folder: str = 'data', models_folder: str = 'models'):
        """
        Khởi tạo Adaptive Parameter Tuner.
        
        Args:
            base_parameters (Dict, optional): Tham số cơ sở ban đầu
            parameter_ranges (Dict, optional): Phạm vi giá trị cho mỗi tham số
            lookback_periods (int): Số chu kỳ dữ liệu để phân tích hiệu suất
            max_optimization_history (int): Số lượng lần tối ưu hóa lưu trong lịch sử
            data_folder (str): Thư mục lưu dữ liệu
            models_folder (str): Thư mục lưu các mô hình ML
        """
        self.base_parameters = base_parameters or {}
        self.parameter_ranges = parameter_ranges or {}
        self.lookback_periods = lookback_periods
        self.max_optimization_history = max_optimization_history
        self.data_folder = data_folder
        self.models_folder = models_folder
        
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(data_folder, exist_ok=True)
        os.makedirs(models_folder, exist_ok=True)
        
        # Lịch sử tối ưu hóa
        self.optimization_history = []
        
        # Mô hình dự đoán tham số
        self.parameter_prediction_model = None
        
        # Trạng thái hiện tại
        self.current_parameters = base_parameters.copy() if base_parameters else {}
        self.current_market_conditions = {}
        self.current_performance_metrics = {}
        
        # Cấu hình phân tích hiệu suất
        self.performance_metrics_weights = {
            'expectancy': 3.0,
            'sharpe_ratio': 2.0,
            'win_rate': 1.0,
            'profit_factor': 2.0,
            'drawdown': -1.5  # Âm vì drawdown thấp hơn là tốt hơn
        }
    
    def update_market_conditions(self, market_data: Dict) -> None:
        """
        Cập nhật điều kiện thị trường hiện tại.
        
        Args:
            market_data (Dict): Các chỉ số điều kiện thị trường
                {
                    'volatility': float,
                    'trend_strength': float,
                    'market_regime': str,
                    'trading_volume': float,
                    'rsi': float,
                    ...
                }
        """
        self.current_market_conditions = market_data
        
        # Lưu điều kiện thị trường vào lịch sử
        market_data_with_timestamp = market_data.copy()
        market_data_with_timestamp['timestamp'] = datetime.now()
        
        # Lưu vào file CSV
        df = pd.DataFrame([market_data_with_timestamp])
        file_path = os.path.join(self.data_folder, 'market_conditions.csv')
        
        if os.path.exists(file_path):
            df.to_csv(file_path, mode='a', header=False, index=False)
        else:
            df.to_csv(file_path, index=False)
            
        logger.info(f"Updated market conditions: {market_data['market_regime']} " +
                  f"(Volatility: {market_data.get('volatility', 'N/A')}, " +
                  f"Trend: {market_data.get('trend_strength', 'N/A')})")
    
    def update_performance_metrics(self, performance_data: Dict) -> None:
        """
        Cập nhật chỉ số hiệu suất hiện tại.
        
        Args:
            performance_data (Dict): Các chỉ số hiệu suất
                {
                    'win_rate': float,
                    'expectancy': float,
                    'sharpe_ratio': float,
                    'profit_factor': float,
                    'drawdown': float,
                    ...
                }
        """
        self.current_performance_metrics = performance_data
        
        # Lưu chỉ số hiệu suất vào lịch sử
        performance_data_with_timestamp = performance_data.copy()
        performance_data_with_timestamp['timestamp'] = datetime.now()
        performance_data_with_timestamp.update(self.current_parameters)
        performance_data_with_timestamp.update(self.current_market_conditions)
        
        # Lưu vào file CSV
        df = pd.DataFrame([performance_data_with_timestamp])
        file_path = os.path.join(self.data_folder, 'performance_metrics.csv')
        
        if os.path.exists(file_path):
            df.to_csv(file_path, mode='a', header=False, index=False)
        else:
            df.to_csv(file_path, index=False)
            
        logger.info(f"Updated performance metrics: " +
                  f"Win Rate: {performance_data.get('win_rate', 'N/A'):.2f}, " +
                  f"Expectancy: {performance_data.get('expectancy', 'N/A'):.2f}, " +
                  f"Profit Factor: {performance_data.get('profit_factor', 'N/A'):.2f}")
    
    def optimize_parameters(self, 
                          optimization_method: str = 'grid_search',
                          target_metric: str = 'composite',
                          max_iterations: int = 100,
                          use_ml_prediction: bool = False) -> Dict:
        """
        Tối ưu hóa các tham số chiến lược.
        
        Args:
            optimization_method (str): Phương pháp tối ưu ('grid_search', 'bayesian', 'genetic')
            target_metric (str): Chỉ số mục tiêu để tối ưu hóa
            max_iterations (int): Số lần lặp tối đa cho tối ưu hóa
            use_ml_prediction (bool): Có sử dụng dự đoán ML cho các tham số ban đầu không
            
        Returns:
            Dict: Tham số tối ưu
        """
        # Kiểm tra xem có đủ dữ liệu để tối ưu không
        if not self.parameter_ranges:
            logger.warning("No parameter ranges defined for optimization")
            return self.current_parameters.copy()
            
        # Nếu sử dụng dự đoán ML, tạo tham số ban đầu từ mô hình
        if use_ml_prediction and self.parameter_prediction_model:
            starting_parameters = self._predict_optimal_parameters(self.current_market_conditions)
        else:
            starting_parameters = self.current_parameters.copy()
            
        # Thực hiện tối ưu hóa theo phương pháp được chọn
        if optimization_method == 'grid_search':
            optimal_params = self._grid_search_optimization(target_metric, max_iterations)
        elif optimization_method == 'bayesian':
            optimal_params = self._bayesian_optimization(starting_parameters, target_metric, max_iterations)
        elif optimization_method == 'genetic':
            optimal_params = self._genetic_optimization(starting_parameters, target_metric, max_iterations)
        else:
            logger.warning(f"Unknown optimization method: {optimization_method}, falling back to grid search")
            optimal_params = self._grid_search_optimization(target_metric, max_iterations)
            
        # Lưu kết quả tối ưu hóa vào lịch sử
        optimization_record = {
            'timestamp': datetime.now(),
            'method': optimization_method,
            'target_metric': target_metric,
            'market_conditions': self.current_market_conditions.copy(),
            'previous_parameters': self.current_parameters.copy(),
            'optimal_parameters': optimal_params.copy(),
            'performance_metrics': self.current_performance_metrics.copy()
        }
        
        self.optimization_history.append(optimization_record)
        
        # Giới hạn kích thước lịch sử
        if len(self.optimization_history) > self.max_optimization_history:
            self.optimization_history = self.optimization_history[-self.max_optimization_history:]
            
        # Lưu lịch sử tối ưu hóa
        self._save_optimization_history()
        
        # Cập nhật tham số hiện tại
        self.current_parameters = optimal_params.copy()
        
        logger.info(f"Optimized parameters using {optimization_method}: {optimal_params}")
        
        return optimal_params
    
    def _grid_search_optimization(self, target_metric: str, max_iterations: int) -> Dict:
        """
        Tối ưu hóa tham số bằng grid search.
        
        Args:
            target_metric (str): Chỉ số mục tiêu để tối ưu hóa
            max_iterations (int): Số lần lặp tối đa
            
        Returns:
            Dict: Tham số tối ưu
        """
        # Tạo lưới tham số
        param_grid = {}
        for param_name, param_range in self.parameter_ranges.items():
            if isinstance(param_range, list):
                # Nếu là danh sách giá trị rời rạc
                param_grid[param_name] = param_range
            elif isinstance(param_range, tuple) and len(param_range) == 3:
                # Nếu là khoảng (min, max, step)
                min_val, max_val, step = param_range
                param_grid[param_name] = np.arange(min_val, max_val + step, step).tolist()
            else:
                # Giữ nguyên giá trị hiện tại
                param_grid[param_name] = [self.current_parameters.get(param_name, 0)]
                
        # Tạo tất cả các tổ hợp tham số
        grid = ParameterGrid(param_grid)
        
        # Giới hạn số lượng tổ hợp để thử
        grid_list = list(grid)
        if len(grid_list) > max_iterations:
            # Lấy mẫu ngẫu nhiên nếu quá nhiều tổ hợp
            indices = np.random.choice(len(grid_list), size=max_iterations, replace=False)
            grid_list = [grid_list[i] for i in indices]
            
        # Đánh giá từng tổ hợp tham số
        best_score = float('-inf')
        best_params = self.current_parameters.copy()
        
        for params in grid_list:
            # Đánh giá hiệu suất của tham số này
            score = self._evaluate_parameters(params, target_metric)
            
            # Cập nhật nếu tốt hơn
            if score > best_score:
                best_score = score
                best_params = params.copy()
                
        return best_params
    
    def _bayesian_optimization(self, starting_params: Dict, target_metric: str, max_iterations: int) -> Dict:
        """
        Tối ưu hóa tham số bằng Bayesian Optimization.
        
        Args:
            starting_params (Dict): Tham số ban đầu
            target_metric (str): Chỉ số mục tiêu để tối ưu hóa
            max_iterations (int): Số lần lặp tối đa
            
        Returns:
            Dict: Tham số tối ưu
        """
        # Đối với Bayesian Optimization, chúng ta cần thư viện như scikit-optimize
        # Trong ví dụ này, chúng ta sẽ mô phỏng đơn giản bằng phương pháp gradient descent
        
        # Tham số ban đầu
        current_params = starting_params.copy()
        current_score = self._evaluate_parameters(current_params, target_metric)
        
        # Tạo hàm mục tiêu để tối thiểu (tối đa hóa điểm)
        def objective_function(x):
            # Chuyển đổi tham số từ mảng thành dict
            params = {}
            for i, param_name in enumerate(self.parameter_ranges.keys()):
                params[param_name] = x[i]
                
            # Đánh giá điểm số
            score = self._evaluate_parameters(params, target_metric)
            
            # Trả về giá trị âm vì chúng ta muốn tối đa hóa, nhưng minimize tối thiểu hóa
            return -score
        
        # Tạo tham số ban đầu và ràng buộc
        x0 = []
        bounds = []
        
        for param_name, param_range in self.parameter_ranges.items():
            current_value = current_params.get(param_name, 0)
            x0.append(current_value)
            
            if isinstance(param_range, list):
                # Lấy giá trị min, max từ danh sách
                bounds.append((min(param_range), max(param_range)))
            elif isinstance(param_range, tuple) and len(param_range) >= 2:
                # Lấy giá trị min, max từ tuple
                bounds.append((param_range[0], param_range[1]))
            else:
                # Sử dụng giá trị hiện tại +/- 20%
                bounds.append((max(0, current_value * 0.8), current_value * 1.2))
        
        # Thực hiện tối ưu hóa
        result = minimize(
            objective_function,
            x0,
            bounds=bounds,
            method='L-BFGS-B',
            options={'maxiter': max_iterations}
        )
        
        # Chuyển đổi kết quả trở lại thành dict
        optimal_params = {}
        for i, param_name in enumerate(self.parameter_ranges.keys()):
            # Làm tròn giá trị nếu cần
            if param_name in self.parameter_ranges and isinstance(self.parameter_ranges[param_name], tuple):
                step = self.parameter_ranges[param_name][2] if len(self.parameter_ranges[param_name]) > 2 else 1
                optimal_params[param_name] = round(result.x[i] / step) * step
            else:
                optimal_params[param_name] = result.x[i]
                
        return optimal_params
    
    def _genetic_optimization(self, starting_params: Dict, target_metric: str, max_iterations: int) -> Dict:
        """
        Tối ưu hóa tham số bằng thuật toán di truyền (Genetic Algorithm).
        
        Args:
            starting_params (Dict): Tham số ban đầu
            target_metric (str): Chỉ số mục tiêu để tối ưu hóa
            max_iterations (int): Số lần lặp tối đa
            
        Returns:
            Dict: Tham số tối ưu
        """
        # Định nghĩa tham số cho GA
        population_size = min(50, max_iterations // 2)
        num_generations = min(max_iterations, 20)
        mutation_rate = 0.1
        crossover_rate = 0.7
        
        # Tạo quần thể ban đầu
        population = []
        
        # Thêm tham số ban đầu vào quần thể
        population.append(starting_params.copy())
        
        # Tạo các cá thể ngẫu nhiên
        for _ in range(population_size - 1):
            individual = {}
            for param_name, param_range in self.parameter_ranges.items():
                if isinstance(param_range, list):
                    # Chọn ngẫu nhiên từ danh sách
                    individual[param_name] = np.random.choice(param_range)
                elif isinstance(param_range, tuple) and len(param_range) >= 2:
                    # Tạo giá trị ngẫu nhiên trong khoảng (min, max)
                    min_val, max_val = param_range[0], param_range[1]
                    step = param_range[2] if len(param_range) > 2 else 0.01
                    
                    # Tạo giá trị ngẫu nhiên
                    value = np.random.uniform(min_val, max_val)
                    
                    # Làm tròn theo step
                    individual[param_name] = round(value / step) * step
                else:
                    # Sử dụng giá trị từ tham số ban đầu +/- ngẫu nhiên
                    base_value = starting_params.get(param_name, 0)
                    variation = base_value * 0.2  # 20% biến thiên
                    individual[param_name] = max(0, base_value + np.random.uniform(-variation, variation))
                    
            population.append(individual)
            
        # Tiến hóa qua các thế hệ
        for generation in range(num_generations):
            # Đánh giá quần thể
            fitness_scores = []
            for individual in population:
                score = self._evaluate_parameters(individual, target_metric)
                fitness_scores.append(score)
                
            # Chọn lọc (tournament selection)
            new_population = []
            
            # Thêm một số cá thể ưu tú (elitism)
            elite_count = max(1, int(population_size * 0.1))
            elite_indices = np.argsort(fitness_scores)[-elite_count:]
            for idx in elite_indices:
                new_population.append(population[idx].copy())
                
            # Sinh sản để điền phần còn lại của quần thể
            while len(new_population) < population_size:
                # Chọn cha mẹ
                parent1_idx = np.random.randint(0, population_size)
                parent2_idx = np.random.randint(0, population_size)
                
                # Tournament selection
                if fitness_scores[parent1_idx] < fitness_scores[parent2_idx]:
                    parent1_idx = parent2_idx
                    
                parent2_idx = np.random.randint(0, population_size)
                if fitness_scores[parent1_idx] < fitness_scores[parent2_idx]:
                    parent1_idx = parent2_idx
                    
                parent1 = population[parent1_idx]
                
                # Chọn parent 2 khác với parent 1
                while True:
                    parent2_idx = np.random.randint(0, population_size)
                    if parent1_idx != parent2_idx:
                        break
                        
                parent2 = population[parent2_idx]
                
                # Lai tạo (crossover)
                if np.random.random() < crossover_rate:
                    child = {}
                    for param_name in self.parameter_ranges.keys():
                        # Chọn từ một trong hai cha mẹ
                        if np.random.random() < 0.5:
                            child[param_name] = parent1[param_name]
                        else:
                            child[param_name] = parent2[param_name]
                else:
                    # Không lai tạo, sao chép từ parent 1
                    child = parent1.copy()
                    
                # Đột biến (mutation)
                for param_name, param_range in self.parameter_ranges.items():
                    if np.random.random() < mutation_rate:
                        if isinstance(param_range, list):
                            # Chọn giá trị mới từ danh sách
                            child[param_name] = np.random.choice(param_range)
                        elif isinstance(param_range, tuple) and len(param_range) >= 2:
                            # Tạo giá trị mới trong khoảng
                            min_val, max_val = param_range[0], param_range[1]
                            step = param_range[2] if len(param_range) > 2 else 0.01
                            
                            # Tạo giá trị mới
                            value = np.random.uniform(min_val, max_val)
                            
                            # Làm tròn theo step
                            child[param_name] = round(value / step) * step
                        else:
                            # Biến đổi giá trị hiện tại
                            current_value = child[param_name]
                            variation = current_value * 0.1  # 10% biến thiên
                            child[param_name] = max(0, current_value + np.random.uniform(-variation, variation))
                            
                # Thêm vào quần thể mới
                new_population.append(child)
                
            # Cập nhật quần thể
            population = new_population
            
            # Log tiến độ
            if (generation + 1) % 5 == 0 or generation == num_generations - 1:
                best_idx = np.argmax(fitness_scores)
                best_score = fitness_scores[best_idx]
                logger.info(f"Genetic optimization: Generation {generation+1}/{num_generations}, Best score: {best_score:.4f}")
                
        # Trả về cá thể tốt nhất
        final_fitness_scores = []
        for individual in population:
            score = self._evaluate_parameters(individual, target_metric)
            final_fitness_scores.append(score)
            
        best_idx = np.argmax(final_fitness_scores)
        best_individual = population[best_idx]
        
        return best_individual
    
    def _evaluate_parameters(self, params: Dict, target_metric: str) -> float:
        """
        Đánh giá hiệu suất của một bộ tham số.
        
        Args:
            params (Dict): Bộ tham số cần đánh giá
            target_metric (str): Chỉ số mục tiêu để tối ưu hóa
            
        Returns:
            float: Điểm số đánh giá
        """
        # Thực hiện đánh giá dựa trên dữ liệu hiệu suất gần đây
        # Trong thực tế, bạn có thể cần chạy backtest với các tham số này
        
        # Trường hợp đặc biệt nếu không có dữ liệu hiệu suất
        if not self.optimization_history:
            # Trả về một giá trị giả định dựa trên độ khác biệt so với tham số cơ sở
            similarity = self._calculate_parameter_similarity(params, self.base_parameters)
            return similarity
            
        # Tìm trong lịch sử tối ưu hóa các điều kiện thị trường tương tự
        similar_history = self._find_similar_market_conditions(self.current_market_conditions)
        
        if not similar_history:
            # Nếu không có dữ liệu tương tự, trả về độ tương đồng với tham số hiện tại
            similarity = self._calculate_parameter_similarity(params, self.current_parameters)
            return similarity
            
        # Tính điểm dựa trên các bản ghi tương tự
        total_score = 0
        total_weight = 0
        
        for record in similar_history:
            # Tính độ tương đồng của tham số
            param_similarity = self._calculate_parameter_similarity(params, record['optimal_parameters'])
            
            # Lấy chỉ số hiệu suất từ bản ghi
            performance = record['performance_metrics']
            
            # Tính điểm cho bản ghi này
            if target_metric == 'composite':
                # Tính điểm tổng hợp
                record_score = self._calculate_composite_score(performance)
            else:
                # Lấy chỉ số cụ thể
                record_score = performance.get(target_metric, 0)
                
            # Trọng số dựa trên độ tương đồng của điều kiện thị trường
            market_similarity = record.get('market_similarity', 1.0)
            
            # Tính điểm có trọng số
            weighted_score = record_score * param_similarity * market_similarity
            
            total_score += weighted_score
            total_weight += market_similarity
            
        # Tính điểm trung bình
        if total_weight > 0:
            average_score = total_score / total_weight
        else:
            average_score = 0
            
        return average_score
    
    def _calculate_composite_score(self, performance_metrics: Dict) -> float:
        """
        Tính điểm tổng hợp từ nhiều chỉ số hiệu suất.
        
        Args:
            performance_metrics (Dict): Các chỉ số hiệu suất
            
        Returns:
            float: Điểm tổng hợp
        """
        total_score = 0
        total_weight = 0
        
        for metric, weight in self.performance_metrics_weights.items():
            if metric in performance_metrics:
                total_score += performance_metrics[metric] * weight
                total_weight += abs(weight)
                
        if total_weight > 0:
            return total_score / total_weight
        else:
            return 0
    
    def _calculate_parameter_similarity(self, params1: Dict, params2: Dict) -> float:
        """
        Tính độ tương đồng giữa hai bộ tham số.
        
        Args:
            params1 (Dict): Bộ tham số thứ nhất
            params2 (Dict): Bộ tham số thứ hai
            
        Returns:
            float: Độ tương đồng (0-1)
        """
        if not params1 or not params2:
            return 0
            
        # Tìm các tham số chung
        common_params = set(params1.keys()) & set(params2.keys())
        
        if not common_params:
            return 0
            
        # Tính tổng khoảng cách chuẩn hóa
        total_distance = 0
        
        for param in common_params:
            # Lấy giá trị
            val1 = params1[param]
            val2 = params2[param]
            
            # Lấy phạm vi từ parameter_ranges
            if param in self.parameter_ranges:
                param_range = self.parameter_ranges[param]
                
                if isinstance(param_range, list):
                    # Đối với danh sách, lấy min/max
                    range_min = min(param_range)
                    range_max = max(param_range)
                elif isinstance(param_range, tuple) and len(param_range) >= 2:
                    # Lấy min/max từ tuple
                    range_min, range_max = param_range[0], param_range[1]
                else:
                    # Sử dụng giá trị hiện tại +/- 50%
                    base_value = max(abs(val1), abs(val2))
                    range_min = base_value * 0.5
                    range_max = base_value * 1.5
            else:
                # Sử dụng giá trị hiện tại +/- 50%
                base_value = max(abs(val1), abs(val2))
                range_min = base_value * 0.5
                range_max = base_value * 1.5
                
            # Tránh chia cho 0
            range_width = max(1e-10, range_max - range_min)
            
            # Tính khoảng cách chuẩn hóa
            normalized_distance = abs(val1 - val2) / range_width
            
            # Thêm vào tổng
            total_distance += normalized_distance
            
        # Tính độ tương đồng (1 - khoảng cách trung bình)
        average_distance = total_distance / len(common_params)
        similarity = max(0, 1 - average_distance)
        
        return similarity
    
    def _find_similar_market_conditions(self, current_conditions: Dict) -> List[Dict]:
        """
        Tìm các điều kiện thị trường tương tự trong lịch sử.
        
        Args:
            current_conditions (Dict): Điều kiện thị trường hiện tại
            
        Returns:
            List[Dict]: Danh sách các bản ghi lịch sử có điều kiện tương tự
        """
        if not self.optimization_history:
            return []
            
        # Tính độ tương đồng với mỗi bản ghi trong lịch sử
        similar_records = []
        
        for record in self.optimization_history:
            market_similarity = self._calculate_market_similarity(
                current_conditions,
                record['market_conditions']
            )
            
            # Thêm độ tương đồng vào bản ghi
            record_with_similarity = record.copy()
            record_with_similarity['market_similarity'] = market_similarity
            
            # Thêm vào danh sách
            similar_records.append(record_with_similarity)
            
        # Sắp xếp theo độ tương đồng giảm dần
        similar_records.sort(key=lambda x: x['market_similarity'], reverse=True)
        
        # Lấy top N bản ghi tương tự nhất
        top_n = min(10, len(similar_records))
        return similar_records[:top_n]
    
    def _calculate_market_similarity(self, conditions1: Dict, conditions2: Dict) -> float:
        """
        Tính độ tương đồng giữa hai điều kiện thị trường.
        
        Args:
            conditions1 (Dict): Điều kiện thị trường thứ nhất
            conditions2 (Dict): Điều kiện thị trường thứ hai
            
        Returns:
            float: Độ tương đồng (0-1)
        """
        if not conditions1 or not conditions2:
            return 0
            
        # Các trọng số cho từng chỉ số thị trường
        market_feature_weights = {
            'volatility': 2.0,
            'trend_strength': 1.5,
            'market_regime': 3.0,
            'trading_volume': 1.0,
            'rsi': 1.0
        }
        
        # Tính tổng khoảng cách có trọng số
        total_weighted_distance = 0
        total_weight = 0
        
        # Xử lý trường hợp đặc biệt cho 'market_regime'
        if 'market_regime' in conditions1 and 'market_regime' in conditions2:
            regime1 = conditions1['market_regime']
            regime2 = conditions2['market_regime']
            
            # Nếu cùng chế độ, similarity = 1, nếu không similarity = 0
            regime_similarity = 1.0 if regime1 == regime2 else 0.0
            
            # Thêm vào tổng
            weight = market_feature_weights.get('market_regime', 1.0)
            total_weighted_distance += (1 - regime_similarity) * weight
            total_weight += weight
            
        # Xử lý các chỉ số số học
        numeric_features = set(conditions1.keys()) & set(conditions2.keys()) - {'market_regime'}
        
        for feature in numeric_features:
            if feature in market_feature_weights:
                # Lấy giá trị
                val1 = conditions1[feature]
                val2 = conditions2[feature]
                
                # Chuẩn hóa khoảng cách tương đối
                max_val = max(abs(val1), abs(val2))
                if max_val > 0:
                    normalized_distance = abs(val1 - val2) / max_val
                else:
                    normalized_distance = 0
                    
                # Thêm vào tổng có trọng số
                weight = market_feature_weights.get(feature, 1.0)
                total_weighted_distance += normalized_distance * weight
                total_weight += weight
                
        # Tính độ tương đồng
        if total_weight > 0:
            average_weighted_distance = total_weighted_distance / total_weight
            similarity = max(0, 1 - average_weighted_distance)
        else:
            similarity = 0
            
        return similarity
    
    def train_parameter_prediction_model(self, min_history_size: int = 20) -> bool:
        """
        Huấn luyện mô hình dự đoán tham số tối ưu dựa trên điều kiện thị trường.
        
        Args:
            min_history_size (int): Số lượng bản ghi tối thiểu để huấn luyện
            
        Returns:
            bool: True nếu huấn luyện thành công, False nếu không
        """
        if len(self.optimization_history) < min_history_size:
            logger.warning(f"Not enough history for training. Need at least {min_history_size} records.")
            return False
            
        # Chuẩn bị dữ liệu huấn luyện
        X = []  # Features (market conditions)
        y = {}  # Target (optimal parameters)
        
        # Khởi tạo y với các tham số cần dự đoán
        for param_name in self.parameter_ranges.keys():
            y[param_name] = []
            
        # Trích xuất dữ liệu từ lịch sử
        for record in self.optimization_history:
            # Skip records with missing data
            if not record['market_conditions'] or not record['optimal_parameters']:
                continue
                
            # Chuyển đổi điều kiện thị trường thành đặc trưng
            features = self._extract_market_features(record['market_conditions'])
            X.append(features)
            
            # Lấy tham số tối ưu cho mỗi tham số
            for param_name in self.parameter_ranges.keys():
                if param_name in record['optimal_parameters']:
                    y[param_name].append(record['optimal_parameters'][param_name])
                else:
                    # Sử dụng giá trị mặc định
                    y[param_name].append(self.base_parameters.get(param_name, 0))
        
        if len(X) < min_history_size:
            logger.warning(f"Not enough valid records for training. Need at least {min_history_size} records.")
            return False
            
        # Chuyển đổi thành numpy array
        X = np.array(X)
        
        # Train một mô hình dự đoán cho mỗi tham số
        self.parameter_prediction_model = {}
        
        for param_name in self.parameter_ranges.keys():
            # Chuyển đổi target thành numpy array
            y_param = np.array(y[param_name])
            
            # Tạo và huấn luyện mô hình
            model = RandomForestRegressor(n_estimators=50, random_state=42)
            model.fit(X, y_param)
            
            # Lưu mô hình
            self.parameter_prediction_model[param_name] = model
            
            # Lưu mô hình vào file
            model_path = os.path.join(self.models_folder, f'parameter_model_{param_name}.joblib')
            joblib.dump(model, model_path)
            
        logger.info(f"Trained parameter prediction models for {len(self.parameter_prediction_model)} parameters")
        return True
    
    def _predict_optimal_parameters(self, market_conditions: Dict) -> Dict:
        """
        Dự đoán tham số tối ưu dựa trên điều kiện thị trường.
        
        Args:
            market_conditions (Dict): Điều kiện thị trường hiện tại
            
        Returns:
            Dict: Tham số tối ưu dự đoán
        """
        if not self.parameter_prediction_model:
            logger.warning("No prediction model available. Using current parameters.")
            return self.current_parameters.copy()
            
        # Chuyển đổi điều kiện thị trường thành đặc trưng
        features = self._extract_market_features(market_conditions)
        features = np.array([features])
        
        # Dự đoán mỗi tham số
        predicted_params = {}
        
        for param_name, model in self.parameter_prediction_model.items():
            # Dự đoán giá trị
            predicted_value = model.predict(features)[0]
            
            # Làm tròn giá trị nếu cần
            if param_name in self.parameter_ranges:
                param_range = self.parameter_ranges[param_name]
                
                if isinstance(param_range, tuple) and len(param_range) > 2:
                    # Làm tròn theo step
                    step = param_range[2]
                    predicted_value = round(predicted_value / step) * step
                    
                # Đảm bảo trong phạm vi cho phép
                if isinstance(param_range, list):
                    # Tìm giá trị gần nhất trong danh sách
                    predicted_value = min(param_range, key=lambda x: abs(x - predicted_value))
                elif isinstance(param_range, tuple) and len(param_range) >= 2:
                    # Giới hạn trong khoảng min, max
                    min_val, max_val = param_range[0], param_range[1]
                    predicted_value = max(min_val, min(max_val, predicted_value))
                    
            # Lưu giá trị dự đoán
            predicted_params[param_name] = predicted_value
            
        logger.info(f"Predicted optimal parameters: {predicted_params}")
        return predicted_params
    
    def _extract_market_features(self, market_conditions: Dict) -> List:
        """
        Trích xuất đặc trưng từ điều kiện thị trường.
        
        Args:
            market_conditions (Dict): Điều kiện thị trường
            
        Returns:
            List: Đặc trưng dưới dạng vector
        """
        # Danh sách các đặc trưng cần trích xuất
        feature_names = [
            'volatility',
            'trend_strength',
            'trading_volume',
            'rsi'
        ]
        
        # Trích xuất đặc trưng số học
        features = []
        for feature in feature_names:
            if feature in market_conditions:
                features.append(market_conditions[feature])
            else:
                features.append(0)  # Giá trị mặc định
                
        # One-hot encoding cho market_regime
        regimes = ['Bullish', 'Bearish', 'Sideways', 'Volatile', 'Ranging']
        current_regime = market_conditions.get('market_regime', '')
        
        for regime in regimes:
            if current_regime == regime:
                features.append(1)
            else:
                features.append(0)
                
        return features
    
    def _save_optimization_history(self) -> bool:
        """
        Lưu lịch sử tối ưu hóa vào file.
        
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        try:
            # Chuyển đổi datetime thành string để có thể JSON serialize
            serializable_history = []
            
            for record in self.optimization_history:
                serializable_record = record.copy()
                
                # Chuyển đổi datetime
                if 'timestamp' in serializable_record:
                    serializable_record['timestamp'] = serializable_record['timestamp'].isoformat()
                    
                serializable_history.append(serializable_record)
                
            # Lưu vào file
            file_path = os.path.join(self.data_folder, 'optimization_history.json')
            with open(file_path, 'w') as f:
                json.dump(serializable_history, f, indent=2)
                
            logger.info(f"Saved optimization history to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving optimization history: {e}")
            return False
    
    def load_optimization_history(self) -> bool:
        """
        Tải lịch sử tối ưu hóa từ file.
        
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        try:
            file_path = os.path.join(self.data_folder, 'optimization_history.json')
            
            if not os.path.exists(file_path):
                logger.warning(f"Optimization history file not found: {file_path}")
                return False
                
            # Đọc từ file
            with open(file_path, 'r') as f:
                serialized_history = json.load(f)
                
            # Chuyển đổi string thành datetime
            for record in serialized_history:
                if 'timestamp' in record:
                    record['timestamp'] = datetime.fromisoformat(record['timestamp'])
                    
            # Cập nhật lịch sử
            self.optimization_history = serialized_history
            
            logger.info(f"Loaded optimization history from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading optimization history: {e}")
            return False
    
    def load_parameter_prediction_models(self) -> bool:
        """
        Tải các mô hình dự đoán tham số từ file.
        
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        try:
            self.parameter_prediction_model = {}
            
            # Tải mô hình cho từng tham số
            for param_name in self.parameter_ranges.keys():
                model_path = os.path.join(self.models_folder, f'parameter_model_{param_name}.joblib')
                
                if os.path.exists(model_path):
                    model = joblib.load(model_path)
                    self.parameter_prediction_model[param_name] = model
                    
            if self.parameter_prediction_model:
                logger.info(f"Loaded {len(self.parameter_prediction_model)} parameter prediction models")
                return True
            else:
                logger.warning("No parameter prediction models found")
                return False
                
        except Exception as e:
            logger.error(f"Error loading parameter prediction models: {e}")
            return False


class MarketRegimeDetector:
    """Lớp phát hiện chế độ thị trường và chuyển đổi chiến lược phù hợp"""
    
    def __init__(self, regimes: List[str] = None, lookback_periods: int = 50,
                data_folder: str = 'data', models_folder: str = 'models'):
        """
        Khởi tạo Market Regime Detector.
        
        Args:
            regimes (List[str]): Danh sách các chế độ thị trường
            lookback_periods (int): Số chu kỳ dữ liệu để phân tích
            data_folder (str): Thư mục lưu dữ liệu
            models_folder (str): Thư mục lưu các mô hình ML
        """
        self.regimes = regimes or ['Bullish', 'Bearish', 'Sideways', 'Volatile', 'Ranging']
        self.lookback_periods = lookback_periods
        self.data_folder = data_folder
        self.models_folder = models_folder
        
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(data_folder, exist_ok=True)
        os.makedirs(models_folder, exist_ok=True)
        
        # Mô hình phát hiện chế độ thị trường
        self.regime_detection_model = None
        
        # Cửa sổ dữ liệu hiện tại
        self.price_history = []
        self.volume_history = []
        self.indicator_history = {}
        
        # Chế độ thị trường hiện tại
        self.current_regime = 'Unknown'
        self.regime_history = []
        self.regime_probabilities = {}
        
        # Danh sách các chiến lược phù hợp cho mỗi chế độ
        self.regime_strategies = {
            'Bullish': [],
            'Bearish': [],
            'Sideways': [],
            'Volatile': [],
            'Ranging': []
        }
    
    def add_price_data(self, timestamp: datetime, open_price: float, high_price: float,
                    low_price: float, close_price: float, volume: float = None) -> None:
        """
        Thêm dữ liệu giá mới.
        
        Args:
            timestamp (datetime): Thời gian
            open_price (float): Giá mở cửa
            high_price (float): Giá cao nhất
            low_price (float): Giá thấp nhất
            close_price (float): Giá đóng cửa
            volume (float, optional): Khối lượng
        """
        # Tạo bản ghi dữ liệu
        price_record = {
            'timestamp': timestamp,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price
        }
        
        # Thêm vào lịch sử giá
        self.price_history.append(price_record)
        
        # Giới hạn kích thước lịch sử
        if len(self.price_history) > self.lookback_periods * 2:
            self.price_history = self.price_history[-self.lookback_periods*2:]
            
        # Thêm khối lượng nếu có
        if volume is not None:
            self.volume_history.append({'timestamp': timestamp, 'volume': volume})
            
            # Giới hạn kích thước lịch sử
            if len(self.volume_history) > self.lookback_periods * 2:
                self.volume_history = self.volume_history[-self.lookback_periods*2:]
                
        # Sau khi thêm dữ liệu mới, phát hiện lại chế độ thị trường
        if len(self.price_history) >= self.lookback_periods:
            self.detect_market_regime()
    
    def add_indicator_data(self, timestamp: datetime, indicator_name: str, value: float) -> None:
        """
        Thêm dữ liệu chỉ báo kỹ thuật.
        
        Args:
            timestamp (datetime): Thời gian
            indicator_name (str): Tên chỉ báo
            value (float): Giá trị chỉ báo
        """
        # Khởi tạo mảng cho chỉ báo nếu chưa có
        if indicator_name not in self.indicator_history:
            self.indicator_history[indicator_name] = []
            
        # Thêm vào lịch sử
        self.indicator_history[indicator_name].append({
            'timestamp': timestamp,
            'value': value
        })
        
        # Giới hạn kích thước lịch sử
        if len(self.indicator_history[indicator_name]) > self.lookback_periods * 2:
            self.indicator_history[indicator_name] = self.indicator_history[indicator_name][-self.lookback_periods*2:]
    
    def detect_market_regime(self) -> str:
        """
        Phát hiện chế độ thị trường hiện tại.
        
        Returns:
            str: Chế độ thị trường hiện tại
        """
        # Kiểm tra nếu có đủ dữ liệu
        if len(self.price_history) < self.lookback_periods:
            logger.warning(f"Not enough price history. Need at least {self.lookback_periods} periods.")
            return "Unknown"
            
        # Sử dụng mô hình ML nếu có
        if self.regime_detection_model:
            regime, probabilities = self._predict_regime_with_model()
        else:
            # Sử dụng phương pháp rule-based
            regime, probabilities = self._detect_regime_rule_based()
            
        # Cập nhật chế độ hiện tại
        self.current_regime = regime
        self.regime_probabilities = probabilities
        
        # Lưu vào lịch sử
        self.regime_history.append({
            'timestamp': self.price_history[-1]['timestamp'],
            'regime': regime,
            'probabilities': probabilities
        })
        
        # Giới hạn kích thước lịch sử
        if len(self.regime_history) > self.lookback_periods * 2:
            self.regime_history = self.regime_history[-self.lookback_periods*2:]
            
        logger.info(f"Detected market regime: {regime} " +
                  f"(Probabilities: {', '.join([f'{k}: {v:.2f}' for k, v in probabilities.items()])})")
        
        return regime
    
    def _detect_regime_rule_based(self) -> Tuple[str, Dict[str, float]]:
        """
        Phát hiện chế độ thị trường sử dụng rule-based.
        
        Returns:
            Tuple[str, Dict[str, float]]: Chế độ thị trường và các xác suất tương ứng
        """
        # Lấy dữ liệu gần đây
        recent_data = self.price_history[-self.lookback_periods:]
        
        # Trích xuất giá đóng cửa
        closes = [data['close'] for data in recent_data]
        
        # Tính các chỉ số để phát hiện chế độ
        
        # 1. Xu hướng: Sử dụng đường hồi quy tuyến tính
        x = np.arange(len(closes))
        slope, _, r_value, _, _ = np.polyfit(x, closes, 1, full=True)[0:5]
        trend_strength = abs(r_value[0])  # Độ mạnh của xu hướng (0-1)
        
        # 2. Biến động: Sử dụng độ lệch chuẩn chuẩn hóa
        volatility = np.std(closes) / np.mean(closes)
        
        # 3. Tính toán các biến động ngắn hạn và dài hạn
        short_term = self.lookback_periods // 4
        long_term = self.lookback_periods
        
        short_volatility = np.std(closes[-short_term:]) / np.mean(closes[-short_term:])
        long_volatility = np.std(closes) / np.mean(closes)
        
        volatility_ratio = short_volatility / long_volatility if long_volatility > 0 else 1
        
        # 4. Range check: Kiểm tra xem giá có nằm trong một khoảng hẹp không
        price_range = (max(closes) - min(closes)) / np.mean(closes)
        
        # 5. Sử dụng thông tin khối lượng nếu có
        volume_trend = 0
        if self.volume_history and len(self.volume_history) >= self.lookback_periods:
            recent_volumes = [v['volume'] for v in self.volume_history[-self.lookback_periods:]]
            volume_slope, _, _, _, _ = np.polyfit(x, recent_volumes, 1, full=True)[0:5]
            volume_trend = volume_slope[0]  # Độ dốc của khối lượng
        
        # Xác định các xác suất cho từng chế độ
        prob_bullish = 0.0
        prob_bearish = 0.0
        prob_sideways = 0.0
        prob_volatile = 0.0
        prob_ranging = 0.0
        
        # Bullish: Xu hướng tăng mạnh
        if slope > 0:
            prob_bullish = min(1.0, slope * 1000 * trend_strength)  # Điều chỉnh hệ số theo dữ liệu thực tế
        
        # Bearish: Xu hướng giảm mạnh
        if slope < 0:
            prob_bearish = min(1.0, -slope * 1000 * trend_strength)  # Điều chỉnh hệ số theo dữ liệu thực tế
        
        # Sideways: Biến động thấp, không có xu hướng rõ ràng
        prob_sideways = min(1.0, (1 - trend_strength) * (1 - min(1.0, volatility * 10)))
        
        # Volatile: Biến động cao, tỷ lệ biến động ngắn hạn/dài hạn cao
        prob_volatile = min(1.0, volatility * 10 * volatility_ratio)
        
        # Ranging: Giá di chuyển trong một khoảng, có biến động nhưng không phải xu hướng
        prob_ranging = min(1.0, (1 - trend_strength) * min(1.0, price_range * 5))
        
        # Tạo dictionary xác suất
        probabilities = {
            'Bullish': prob_bullish,
            'Bearish': prob_bearish,
            'Sideways': prob_sideways,
            'Volatile': prob_volatile,
            'Ranging': prob_ranging
        }
        
        # Chuẩn hóa xác suất
        total_prob = sum(probabilities.values())
        if total_prob > 0:
            probabilities = {k: v / total_prob for k, v in probabilities.items()}
            
        # Chọn chế độ có xác suất cao nhất
        regime = max(probabilities, key=probabilities.get)
        
        return regime, probabilities
    
    def _predict_regime_with_model(self) -> Tuple[str, Dict[str, float]]:
        """
        Phát hiện chế độ thị trường sử dụng mô hình ML.
        
        Returns:
            Tuple[str, Dict[str, float]]: Chế độ thị trường và các xác suất tương ứng
        """
        # Trích xuất đặc trưng từ dữ liệu giá
        features = self._extract_regime_features()
        
        # Dự đoán chế độ
        features_array = np.array([features])
        regime_probs = self.regime_detection_model.predict_proba(features_array)[0]
        
        # Ánh xạ xác suất vào các chế độ
        probabilities = {}
        for i, regime in enumerate(self.regime_detection_model.classes_):
            probabilities[regime] = regime_probs[i]
            
        # Chọn chế độ có xác suất cao nhất
        regime = self.regime_detection_model.predict(features_array)[0]
        
        return regime, probabilities
    
    def _extract_regime_features(self) -> List[float]:
        """
        Trích xuất đặc trưng từ dữ liệu giá để phát hiện chế độ thị trường.
        
        Returns:
            List[float]: Các đặc trưng
        """
        # Lấy dữ liệu gần đây
        recent_data = self.price_history[-self.lookback_periods:]
        
        # Trích xuất OHLC
        opens = np.array([data['open'] for data in recent_data])
        highs = np.array([data['high'] for data in recent_data])
        lows = np.array([data['low'] for data in recent_data])
        closes = np.array([data['close'] for data in recent_data])
        
        # Tính các đặc trưng
        
        # 1. Các đặc trưng xu hướng
        returns = np.diff(closes) / closes[:-1]
        slope, intercept, r_value, p_value, std_err = np.polyfit(np.arange(len(closes)), closes, 1, full=True)[0:5]
        trend_strength = abs(r_value[0])
        
        # 2. Các đặc trưng biến động
        volatility = np.std(returns)
        normalized_volatility = volatility / np.mean(np.abs(returns)) if np.mean(np.abs(returns)) > 0 else 0
        
        # 3. Các đặc trưng khoảng giá
        price_range = (np.max(highs) - np.min(lows)) / np.mean(closes)
        
        # 4. Các đặc trưng mẫu nến
        body_sizes = np.abs(closes - opens) / ((highs - lows) + 1e-10)
        avg_body_size = np.mean(body_sizes)
        
        # 5. Các đặc trưng khối lượng nếu có
        volume_features = []
        if self.volume_history and len(self.volume_history) >= self.lookback_periods:
            recent_volumes = np.array([v['volume'] for v in self.volume_history[-self.lookback_periods:]])
            volume_slope, _, _, _, _ = np.polyfit(np.arange(len(recent_volumes)), recent_volumes, 1, full=True)[0:5]
            volume_volatility = np.std(recent_volumes) / np.mean(recent_volumes) if np.mean(recent_volumes) > 0 else 0
            
            volume_features = [
                volume_slope[0],
                volume_volatility,
                np.corrcoef(closes, recent_volumes)[0, 1] if len(closes) == len(recent_volumes) else 0
            ]
        else:
            volume_features = [0, 0, 0]  # Giá trị mặc định
            
        # 6. Các đặc trưng từ các chỉ báo nếu có
        indicator_features = []
        
        for indicator_name in ['rsi', 'macd', 'atr', 'adx']:
            if indicator_name in self.indicator_history and len(self.indicator_history[indicator_name]) >= self.lookback_periods:
                recent_values = [v['value'] for v in self.indicator_history[indicator_name][-self.lookback_periods:]]
                
                # Tính các thống kê
                indicator_mean = np.mean(recent_values)
                indicator_std = np.std(recent_values)
                indicator_slope, _, _, _, _ = np.polyfit(np.arange(len(recent_values)), recent_values, 1, full=True)[0:5]
                
                indicator_features.extend([
                    indicator_mean,
                    indicator_std,
                    indicator_slope[0]
                ])
            else:
                indicator_features.extend([0, 0, 0])  # Giá trị mặc định
                
        # Kết hợp tất cả các đặc trưng
        features = [
            slope[0],
            trend_strength,
            volatility,
            normalized_volatility,
            price_range,
            avg_body_size,
            np.mean(returns),
            np.std(returns)
        ]
        
        features.extend(volume_features)
        features.extend(indicator_features)
        
        return features
    
    def train_regime_detection_model(self, labeled_data: List[Dict] = None, 
                                   min_samples_per_regime: int = 10, 
                                   auto_labeling: bool = False, 
                                   use_clustering: bool = False) -> bool:
        """
        Huấn luyện mô hình phát hiện chế độ thị trường.
        
        Args:
            labeled_data (List[Dict], optional): Dữ liệu đã được gán nhãn
                [{'features': [...], 'regime': '...'}, ...]
            min_samples_per_regime (int): Số lượng mẫu tối thiểu cho mỗi chế độ
            auto_labeling (bool): Tự động gán nhãn dựa trên rule-based
            use_clustering (bool): Sử dụng clustering để tự động phát hiện chế độ
            
        Returns:
            bool: True nếu huấn luyện thành công, False nếu không
        """
        # Kiểm tra đầu vào
        if labeled_data is None and not auto_labeling and not use_clustering:
            logger.warning("No labeled data provided and auto_labeling/use_clustering not enabled")
            return False
            
        # Nếu sử dụng dữ liệu từ lịch sử
        if labeled_data is None and len(self.price_history) < self.lookback_periods * 2:
            logger.warning(f"Not enough price history. Need at least {self.lookback_periods * 2} periods.")
            return False
            
        # Chuẩn bị dữ liệu huấn luyện
        X = []  # Features
        y = []  # Labels (regimes)
        
        if labeled_data is not None:
            # Sử dụng dữ liệu đã gán nhãn
            for item in labeled_data:
                X.append(item['features'])
                y.append(item['regime'])
        elif auto_labeling:
            # Tự động gán nhãn sử dụng rule-based
            window_size = self.lookback_periods
            step_size = window_size // 4  # Overlap 75%
            
            for i in range(0, len(self.price_history) - window_size, step_size):
                window_data = self.price_history[i:i+window_size]
                
                # Lưu trữ tạm thời
                temp_price_history = self.price_history
                
                # Thiết lập cửa sổ dữ liệu
                self.price_history = window_data
                
                # Phát hiện chế độ
                regime, _ = self._detect_regime_rule_based()
                
                # Trích xuất đặc trưng
                features = self._extract_regime_features()
                
                # Thêm vào dữ liệu huấn luyện
                X.append(features)
                y.append(regime)
                
                # Khôi phục dữ liệu
                self.price_history = temp_price_history
        elif use_clustering:
            # Sử dụng clustering để tự động phát hiện chế độ
            window_size = self.lookback_periods
            step_size = window_size // 4  # Overlap 75%
            
            # Trích xuất đặc trưng cho từng cửa sổ
            features_list = []
            for i in range(0, len(self.price_history) - window_size, step_size):
                window_data = self.price_history[i:i+window_size]
                
                # Lưu trữ tạm thời
                temp_price_history = self.price_history
                
                # Thiết lập cửa sổ dữ liệu
                self.price_history = window_data
                
                # Trích xuất đặc trưng
                features = self._extract_regime_features()
                features_list.append(features)
                
                # Khôi phục dữ liệu
                self.price_history = temp_price_history
                
            # Áp dụng clustering
            if len(features_list) >= len(self.regimes):
                # Chuẩn hóa dữ liệu
                features_array = np.array(features_list)
                features_normalized = (features_array - np.mean(features_array, axis=0)) / (np.std(features_array, axis=0) + 1e-10)
                
                # Áp dụng K-means clustering
                kmeans = KMeans(n_clusters=len(self.regimes), random_state=42)
                clusters = kmeans.fit_predict(features_normalized)
                
                # Ánh xạ cluster -> regime
                cluster_to_regime = {}
                
                # Phương pháp 1: Dựa trên đặc trưng trung bình của từng cluster
                cluster_features = {}
                for i, cluster_idx in enumerate(clusters):
                    if cluster_idx not in cluster_features:
                        cluster_features[cluster_idx] = []
                    cluster_features[cluster_idx].append(features_list[i])
                    
                # Tính đặc trưng trung bình của từng cluster
                for cluster_idx, features in cluster_features.items():
                    avg_features = np.mean(features, axis=0)
                    
                    # Xác định chế độ dựa trên đặc trưng trung bình
                    # Giả định: features[0] là slope, features[1] là trend_strength, features[2] là volatility
                    slope = avg_features[0]
                    trend_strength = avg_features[1]
                    volatility = avg_features[2]
                    
                    if volatility > 0.03:  # Thay đổi ngưỡng cho phù hợp
                        cluster_to_regime[cluster_idx] = 'Volatile'
                    elif trend_strength > 0.6:  # Thay đổi ngưỡng cho phù hợp
                        if slope > 0:
                            cluster_to_regime[cluster_idx] = 'Bullish'
                        else:
                            cluster_to_regime[cluster_idx] = 'Bearish'
                    elif trend_strength < 0.3:  # Thay đổi ngưỡng cho phù hợp
                        cluster_to_regime[cluster_idx] = 'Sideways'
                    else:
                        cluster_to_regime[cluster_idx] = 'Ranging'
                        
                # Đảm bảo rằng mỗi chế độ được sử dụng ít nhất một lần
                used_regimes = set(cluster_to_regime.values())
                missing_regimes = set(self.regimes) - used_regimes
                
                for missing_regime in missing_regimes:
                    # Chọn cluster chưa được gán
                    unused_cluster = None
                    for i in range(len(self.regimes)):
                        if i not in cluster_to_regime:
                            unused_cluster = i
                            break
                            
                    if unused_cluster is not None:
                        cluster_to_regime[unused_cluster] = missing_regime
                        
                # Thêm dữ liệu vào X, y
                for i, cluster_idx in enumerate(clusters):
                    X.append(features_list[i])
                    y.append(cluster_to_regime[cluster_idx])
            else:
                logger.warning(f"Not enough data for clustering. Need at least {len(self.regimes)} windows.")
        
        # Kiểm tra đủ dữ liệu cho từng chế độ
        regime_counts = {}
        for regime in y:
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
            
        for regime in self.regimes:
            if regime not in regime_counts or regime_counts[regime] < min_samples_per_regime:
                logger.warning(f"Insufficient samples for regime '{regime}': {regime_counts.get(regime, 0)} < {min_samples_per_regime}")
                return False
                
        # Huấn luyện mô hình
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X, y)
        
        # Lưu mô hình
        self.regime_detection_model = model
        
        # Lưu mô hình vào file
        model_path = os.path.join(self.models_folder, 'regime_detection_model.joblib')
        joblib.dump(model, model_path)
        
        logger.info(f"Trained regime detection model with {len(X)} samples across {len(set(y))} regimes")
        return True
    
    def load_regime_detection_model(self) -> bool:
        """
        Tải mô hình phát hiện chế độ thị trường từ file.
        
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        try:
            model_path = os.path.join(self.models_folder, 'regime_detection_model.joblib')
            
            if not os.path.exists(model_path):
                logger.warning(f"Regime detection model file not found: {model_path}")
                return False
                
            # Tải mô hình
            self.regime_detection_model = joblib.load(model_path)
            
            logger.info(f"Loaded regime detection model from {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading regime detection model: {e}")
            return False
    
    def register_strategy_for_regime(self, regime: str, strategy_name: str,
                                  parameters: Dict = None, expected_performance: Dict = None) -> bool:
        """
        Đăng ký một chiến lược cho một chế độ thị trường cụ thể.
        
        Args:
            regime (str): Chế độ thị trường
            strategy_name (str): Tên chiến lược
            parameters (Dict, optional): Tham số chiến lược
            expected_performance (Dict, optional): Hiệu suất kỳ vọng
            
        Returns:
            bool: True nếu đăng ký thành công, False nếu không
        """
        if regime not in self.regimes:
            logger.warning(f"Unknown regime: {regime}")
            return False
            
        # Tạo bản ghi chiến lược
        strategy_record = {
            'name': strategy_name,
            'parameters': parameters or {},
            'expected_performance': expected_performance or {}
        }
        
        # Thêm vào danh sách
        self.regime_strategies[regime].append(strategy_record)
        
        logger.info(f"Registered strategy '{strategy_name}' for regime '{regime}'")
        return True
    
    def get_optimal_strategy(self, regime: str = None) -> Dict:
        """
        Lấy chiến lược tối ưu cho chế độ thị trường hiện tại hoặc đã cho.
        
        Args:
            regime (str, optional): Chế độ thị trường, mặc định là chế độ hiện tại
            
        Returns:
            Dict: Thông tin chiến lược tối ưu
        """
        # Sử dụng chế độ hiện tại nếu không chỉ định
        if regime is None:
            regime = self.current_regime
            
        if regime not in self.regime_strategies or not self.regime_strategies[regime]:
            logger.warning(f"No strategies registered for regime '{regime}'")
            return None
            
        # Lấy tất cả chiến lược cho chế độ này
        strategies = self.regime_strategies[regime]
        
        # Nếu chỉ có một chiến lược
        if len(strategies) == 1:
            return strategies[0]
            
        # Chọn chiến lược có hiệu suất kỳ vọng tốt nhất
        best_strategy = None
        best_score = float('-inf')
        
        for strategy in strategies:
            performance = strategy.get('expected_performance', {})
            
            # Tính điểm tổng hợp
            score = 0
            
            # Ưu tiên Expectancy và Sharpe Ratio
            expectancy = performance.get('expectancy', 0)
            sharpe = performance.get('sharpe_ratio', 0)
            profit_factor = performance.get('profit_factor', 0)
            
            score = expectancy * 3 + sharpe * 2 + profit_factor
            
            if score > best_score:
                best_score = score
                best_strategy = strategy
                
        return best_strategy
    
    def save_regime_data(self) -> bool:
        """
        Lưu dữ liệu chế độ thị trường vào file.
        
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        try:
            # Lưu lịch sử chế độ
            regime_data = {
                'current_regime': self.current_regime,
                'regime_probabilities': self.regime_probabilities,
                'regime_history': [],
                'regime_strategies': self.regime_strategies
            }
            
            # Chuyển đổi datetime thành string
            for record in self.regime_history:
                record_copy = record.copy()
                record_copy['timestamp'] = record_copy['timestamp'].isoformat()
                regime_data['regime_history'].append(record_copy)
                
            # Lưu vào file
            file_path = os.path.join(self.data_folder, 'regime_data.json')
            with open(file_path, 'w') as f:
                json.dump(regime_data, f, indent=2)
                
            logger.info(f"Saved regime data to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving regime data: {e}")
            return False
    
    def load_regime_data(self) -> bool:
        """
        Tải dữ liệu chế độ thị trường từ file.
        
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        try:
            file_path = os.path.join(self.data_folder, 'regime_data.json')
            
            if not os.path.exists(file_path):
                logger.warning(f"Regime data file not found: {file_path}")
                return False
                
            # Đọc từ file
            with open(file_path, 'r') as f:
                regime_data = json.load(f)
                
            # Cập nhật dữ liệu
            self.current_regime = regime_data.get('current_regime', 'Unknown')
            self.regime_probabilities = regime_data.get('regime_probabilities', {})
            self.regime_strategies = regime_data.get('regime_strategies', {})
            
            # Chuyển đổi string thành datetime
            self.regime_history = []
            for record in regime_data.get('regime_history', []):
                record_copy = record.copy()
                if 'timestamp' in record_copy:
                    record_copy['timestamp'] = datetime.fromisoformat(record_copy['timestamp'])
                self.regime_history.append(record_copy)
                
            logger.info(f"Loaded regime data from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading regime data: {e}")
            return False


class StrategyEnsemble:
    """Lớp kết hợp nhiều chiến lược giao dịch với trọng số động"""
    
    def __init__(self, strategies: List[Dict] = None, 
               use_dynamic_weights: bool = True,
               performance_lookback: int = 20,
               min_weight: float = 0.1,
               data_folder: str = 'data'):
        """
        Khởi tạo Strategy Ensemble.
        
        Args:
            strategies (List[Dict]): Danh sách các chiến lược
                [{'name': str, 'instance': object, 'weight': float, 'parameters': Dict}, ...]
            use_dynamic_weights (bool): Sử dụng trọng số động dựa trên hiệu suất
            performance_lookback (int): Số chu kỳ hiệu suất để xem xét
            min_weight (float): Trọng số tối thiểu cho mỗi chiến lược
            data_folder (str): Thư mục lưu dữ liệu
        """
        self.strategies = strategies or []
        self.use_dynamic_weights = use_dynamic_weights
        self.performance_lookback = performance_lookback
        self.min_weight = min_weight
        self.data_folder = data_folder
        
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(data_folder, exist_ok=True)
        
        # Lịch sử hiệu suất của từng chiến lược
        self.strategy_performance = {}
        
        # Lịch sử khuyến nghị
        self.recommendation_history = []
    
    def add_strategy(self, name: str, strategy_instance: Any, 
                    weight: float = 1.0, parameters: Dict = None) -> int:
        """
        Thêm một chiến lược vào ensemble.
        
        Args:
            name (str): Tên chiến lược
            strategy_instance (Any): Đối tượng chiến lược
            weight (float): Trọng số ban đầu
            parameters (Dict, optional): Tham số của chiến lược
            
        Returns:
            int: ID của chiến lược trong ensemble
        """
        strategy_id = len(self.strategies)
        
        # Tạo record chiến lược
        strategy_record = {
            'id': strategy_id,
            'name': name,
            'instance': strategy_instance,
            'weight': weight,
            'parameters': parameters or {},
            'active': True
        }
        
        # Thêm vào danh sách
        self.strategies.append(strategy_record)
        
        # Khởi tạo lịch sử hiệu suất
        self.strategy_performance[strategy_id] = []
        
        logger.info(f"Added strategy '{name}' to ensemble with weight {weight}")
        return strategy_id
    
    def update_strategy_parameters(self, strategy_id: int, parameters: Dict) -> bool:
        """
        Cập nhật tham số cho một chiến lược.
        
        Args:
            strategy_id (int): ID của chiến lược
            parameters (Dict): Tham số mới
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không
        """
        if strategy_id < 0 or strategy_id >= len(self.strategies):
            logger.warning(f"Invalid strategy ID: {strategy_id}")
            return False
            
        # Cập nhật tham số
        self.strategies[strategy_id]['parameters'] = parameters
        
        # Cập nhật tham số cho đối tượng chiến lược nếu hỗ trợ
        strategy_instance = self.strategies[strategy_id]['instance']
        if hasattr(strategy_instance, 'update_parameters'):
            strategy_instance.update_parameters(parameters)
            
        logger.info(f"Updated parameters for strategy '{self.strategies[strategy_id]['name']}'")
        return True
    
    def update_strategy_weight(self, strategy_id: int, weight: float) -> bool:
        """
        Cập nhật trọng số cho một chiến lược.
        
        Args:
            strategy_id (int): ID của chiến lược
            weight (float): Trọng số mới
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không
        """
        if strategy_id < 0 or strategy_id >= len(self.strategies):
            logger.warning(f"Invalid strategy ID: {strategy_id}")
            return False
            
        # Cập nhật trọng số
        self.strategies[strategy_id]['weight'] = max(self.min_weight, weight)
        
        logger.info(f"Updated weight for strategy '{self.strategies[strategy_id]['name']}' to {weight}")
        return True
    
    def toggle_strategy(self, strategy_id: int, active: bool) -> bool:
        """
        Bật/tắt một chiến lược.
        
        Args:
            strategy_id (int): ID của chiến lược
            active (bool): Trạng thái mới
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không
        """
        if strategy_id < 0 or strategy_id >= len(self.strategies):
            logger.warning(f"Invalid strategy ID: {strategy_id}")
            return False
            
        # Cập nhật trạng thái
        self.strategies[strategy_id]['active'] = active
        
        logger.info(f"{'Activated' if active else 'Deactivated'} strategy '{self.strategies[strategy_id]['name']}'")
        return True
    
    def update_strategy_performance(self, strategy_id: int, 
                                 performance_metrics: Dict, 
                                 timestamp: datetime = None) -> bool:
        """
        Cập nhật hiệu suất cho một chiến lược.
        
        Args:
            strategy_id (int): ID của chiến lược
            performance_metrics (Dict): Các chỉ số hiệu suất
            timestamp (datetime, optional): Thời gian, mặc định là hiện tại
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không
        """
        if strategy_id < 0 or strategy_id >= len(self.strategies):
            logger.warning(f"Invalid strategy ID: {strategy_id}")
            return False
            
        # Tạo bản ghi hiệu suất
        performance_record = {
            'timestamp': timestamp or datetime.now(),
            'metrics': performance_metrics
        }
        
        # Thêm vào lịch sử
        self.strategy_performance[strategy_id].append(performance_record)
        
        # Giới hạn kích thước lịch sử
        if len(self.strategy_performance[strategy_id]) > self.performance_lookback * 2:
            self.strategy_performance[strategy_id] = self.strategy_performance[strategy_id][-self.performance_lookback*2:]
            
        # Nếu sử dụng trọng số động, cập nhật trọng số
        if self.use_dynamic_weights:
            self._update_dynamic_weights()
            
        logger.info(f"Updated performance for strategy '{self.strategies[strategy_id]['name']}'")
        return True
    
    def _update_dynamic_weights(self) -> None:
        """Cập nhật trọng số động dựa trên hiệu suất gần đây"""
        # Kiểm tra xem có đủ dữ liệu hiệu suất không
        active_strategies = [s for s in self.strategies if s['active']]
        
        if not active_strategies:
            logger.warning("No active strategies")
            return
            
        # Tính điểm hiệu suất cho mỗi chiến lược
        performance_scores = {}
        
        for strategy in active_strategies:
            strategy_id = strategy['id']
            
            # Kiểm tra xem có đủ dữ liệu không
            if strategy_id not in self.strategy_performance or not self.strategy_performance[strategy_id]:
                performance_scores[strategy_id] = 1.0  # Giá trị mặc định
                continue
                
            # Lấy dữ liệu hiệu suất gần đây
            recent_performance = self.strategy_performance[strategy_id][-self.performance_lookback:]
            
            if not recent_performance:
                performance_scores[strategy_id] = 1.0  # Giá trị mặc định
                continue
                
            # Tính điểm tổng hợp
            total_score = 0
            
            for record in recent_performance:
                metrics = record['metrics']
                
                # Tính điểm cho bản ghi này
                record_score = 0
                
                # Ưu tiên Expectancy và Sharpe Ratio
                expectancy = metrics.get('expectancy', 0)
                sharpe = metrics.get('sharpe_ratio', 0)
                profit_factor = metrics.get('profit_factor', 0)
                
                record_score = expectancy * 3 + sharpe * 2 + profit_factor
                
                total_score += record_score
                
            # Tính điểm trung bình
            avg_score = total_score / len(recent_performance)
            
            # Lưu điểm
            performance_scores[strategy_id] = max(0.1, avg_score)
            
        # Chuẩn hóa thành trọng số
        total_score = sum(performance_scores.values())
        
        if total_score > 0:
            for strategy_id, score in performance_scores.items():
                # Tính trọng số mới
                new_weight = (score / total_score)
                
                # Áp dụng trọng số tối thiểu
                new_weight = max(self.min_weight, new_weight)
                
                # Cập nhật trọng số
                for i, strategy in enumerate(self.strategies):
                    if strategy['id'] == strategy_id:
                        self.strategies[i]['weight'] = new_weight
                        break
                        
        # Chuẩn hóa lại trọng số để tổng = 1
        total_weight = sum(s['weight'] for s in active_strategies)
        
        if total_weight > 0:
            for strategy in active_strategies:
                strategy['weight'] = strategy['weight'] / total_weight
                
        logger.info("Updated dynamic weights for strategies")
    
    def get_ensemble_recommendation(self, market_data: Dict) -> Dict:
        """
        Lấy khuyến nghị kết hợp từ tất cả các chiến lược.
        
        Args:
            market_data (Dict): Dữ liệu thị trường
            
        Returns:
            Dict: Khuyến nghị kết hợp
        """
        # Kiểm tra xem có chiến lược hoạt động không
        active_strategies = [s for s in self.strategies if s['active']]
        
        if not active_strategies:
            logger.warning("No active strategies")
            return {
                'signal': 'neutral',
                'confidence': 0,
                'timestamp': datetime.now(),
                'recommendations': []
            }
            
        # Lấy khuyến nghị từ mỗi chiến lược
        recommendations = []
        weighted_signals = {'buy': 0, 'sell': 0, 'neutral': 0}
        total_weight = 0
        
        for strategy in active_strategies:
            strategy_instance = strategy['instance']
            strategy_weight = strategy['weight']
            
            # Lấy tín hiệu từ chiến lược
            if hasattr(strategy_instance, 'generate_signal'):
                signal = strategy_instance.generate_signal(market_data)
            else:
                # Giả định rằng đối tượng chiến lược hỗ trợ phương thức này
                logger.warning(f"Strategy '{strategy['name']}' does not support generate_signal method")
                continue
                
            # Thêm vào danh sách
            recommendation = {
                'strategy_id': strategy['id'],
                'strategy_name': strategy['name'],
                'signal': signal.get('signal', 'neutral'),
                'confidence': signal.get('confidence', 0),
                'weight': strategy_weight,
                'details': signal.get('details', {})
            }
            
            recommendations.append(recommendation)
            
            # Cập nhật tín hiệu có trọng số
            signal_type = signal.get('signal', 'neutral')
            signal_confidence = signal.get('confidence', 0)
            
            weighted_signals[signal_type] += strategy_weight * signal_confidence
            total_weight += strategy_weight
            
        # Tính khuyến nghị kết hợp
        ensemble_signal = 'neutral'
        ensemble_confidence = 0
        
        if total_weight > 0:
            # Tìm tín hiệu có giá trị có trọng số cao nhất
            max_signal = max(weighted_signals.items(), key=lambda x: x[1])
            ensemble_signal = max_signal[0]
            ensemble_confidence = max_signal[1] / total_weight
            
        # Tạo khuyến nghị kết hợp
        ensemble_recommendation = {
            'signal': ensemble_signal,
            'confidence': ensemble_confidence,
            'timestamp': datetime.now(),
            'recommendations': recommendations,
            'weighted_signals': {k: v / total_weight if total_weight > 0 else 0 for k, v in weighted_signals.items()}
        }
        
        # Lưu vào lịch sử
        self.recommendation_history.append(ensemble_recommendation)
        
        # Giới hạn kích thước lịch sử
        if len(self.recommendation_history) > 100:
            self.recommendation_history = self.recommendation_history[-100:]
            
        logger.info(f"Generated ensemble recommendation: {ensemble_signal} " +
                  f"(confidence: {ensemble_confidence:.2f})")
        
        return ensemble_recommendation
    
    def save_ensemble_data(self) -> bool:
        """
        Lưu dữ liệu ensemble vào file.
        
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        try:
            # Chuẩn bị dữ liệu để lưu (không bao gồm đối tượng strategy)
            serializable_strategies = []
            
            for strategy in self.strategies:
                serializable_strategy = {
                    'id': strategy['id'],
                    'name': strategy['name'],
                    'weight': strategy['weight'],
                    'parameters': strategy['parameters'],
                    'active': strategy['active']
                }
                serializable_strategies.append(serializable_strategy)
                
            # Chuyển đổi dữ liệu hiệu suất
            serializable_performance = {}
            
            for strategy_id, performance_records in self.strategy_performance.items():
                serializable_records = []
                
                for record in performance_records:
                    serializable_record = {
                        'timestamp': record['timestamp'].isoformat(),
                        'metrics': record['metrics']
                    }
                    serializable_records.append(serializable_record)
                    
                serializable_performance[strategy_id] = serializable_records
                
            # Chuyển đổi lịch sử khuyến nghị
            serializable_history = []
            
            for record in self.recommendation_history:
                serializable_record = record.copy()
                serializable_record['timestamp'] = serializable_record['timestamp'].isoformat()
                serializable_history.append(serializable_record)
                
            # Tạo dữ liệu ensemble
            ensemble_data = {
                'strategies': serializable_strategies,
                'strategy_performance': serializable_performance,
                'recommendation_history': serializable_history,
                'use_dynamic_weights': self.use_dynamic_weights,
                'performance_lookback': self.performance_lookback,
                'min_weight': self.min_weight
            }
            
            # Lưu vào file
            file_path = os.path.join(self.data_folder, 'ensemble_data.json')
            with open(file_path, 'w') as f:
                json.dump(ensemble_data, f, indent=2)
                
            logger.info(f"Saved ensemble data to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving ensemble data: {e}")
            return False
    
    def load_ensemble_data(self, strategy_instances: Dict[str, Any]) -> bool:
        """
        Tải dữ liệu ensemble từ file.
        
        Args:
            strategy_instances (Dict[str, Any]): Ánh xạ tên chiến lược -> đối tượng
            
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        try:
            file_path = os.path.join(self.data_folder, 'ensemble_data.json')
            
            if not os.path.exists(file_path):
                logger.warning(f"Ensemble data file not found: {file_path}")
                return False
                
            # Đọc từ file
            with open(file_path, 'r') as f:
                ensemble_data = json.load(f)
                
            # Cập nhật cấu hình
            self.use_dynamic_weights = ensemble_data.get('use_dynamic_weights', True)
            self.performance_lookback = ensemble_data.get('performance_lookback', 20)
            self.min_weight = ensemble_data.get('min_weight', 0.1)
            
            # Tải các chiến lược
            self.strategies = []
            
            for strategy_data in ensemble_data.get('strategies', []):
                strategy_name = strategy_data['name']
                
                # Tìm đối tượng chiến lược
                if strategy_name in strategy_instances:
                    strategy_instance = strategy_instances[strategy_name]
                    
                    # Tạo record chiến lược
                    strategy_record = {
                        'id': strategy_data['id'],
                        'name': strategy_name,
                        'instance': strategy_instance,
                        'weight': strategy_data['weight'],
                        'parameters': strategy_data['parameters'],
                        'active': strategy_data['active']
                    }
                    
                    # Cập nhật tham số cho đối tượng chiến lược nếu hỗ trợ
                    if hasattr(strategy_instance, 'update_parameters'):
                        strategy_instance.update_parameters(strategy_data['parameters'])
                        
                    # Thêm vào danh sách
                    self.strategies.append(strategy_record)
                else:
                    logger.warning(f"Strategy instance not found: {strategy_name}")
                    
            # Tải dữ liệu hiệu suất
            self.strategy_performance = {}
            
            for strategy_id, performance_records in ensemble_data.get('strategy_performance', {}).items():
                # Chuyển đổi ID từ string thành int
                strategy_id = int(strategy_id)
                
                serializable_records = []
                
                for record in performance_records:
                    serializable_record = {
                        'timestamp': datetime.fromisoformat(record['timestamp']),
                        'metrics': record['metrics']
                    }
                    serializable_records.append(serializable_record)
                    
                self.strategy_performance[strategy_id] = serializable_records
                
            # Tải lịch sử khuyến nghị
            self.recommendation_history = []
            
            for record in ensemble_data.get('recommendation_history', []):
                serializable_record = record.copy()
                serializable_record['timestamp'] = datetime.fromisoformat(serializable_record['timestamp'])
                self.recommendation_history.append(serializable_record)
                
            logger.info(f"Loaded ensemble data from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading ensemble data: {e}")
            return False


def main():
    """Hàm chính để demo"""
    # Tạo dữ liệu thị trường mẫu
    market_conditions = {
        'volatility': 0.02,
        'trend_strength': 0.7,
        'market_regime': 'Bullish',
        'trading_volume': 1000000,
        'rsi': 65
    }
    
    # Tạo dữ liệu hiệu suất mẫu
    performance_metrics = {
        'win_rate': 0.6,
        'expectancy': 0.5,
        'sharpe_ratio': 1.2,
        'profit_factor': 1.5,
        'drawdown': 5.0
    }
    
    # Demo 1: Adaptive Parameter Tuner
    print("\n=== Testing Adaptive Parameter Tuner ===")
    
    tuner = AdaptiveParameterTuner(
        base_parameters={'rsi_period': 14, 'rsi_overbought': 70, 'rsi_oversold': 30},
        parameter_ranges={
            'rsi_period': (5, 30, 1),
            'rsi_overbought': (60, 85, 5),
            'rsi_oversold': (15, 40, 5)
        }
    )
    
    # Cập nhật điều kiện thị trường
    tuner.update_market_conditions(market_conditions)
    
    # Cập nhật chỉ số hiệu suất
    tuner.update_performance_metrics(performance_metrics)
    
    # Tối ưu hóa tham số
    optimal_params = tuner.optimize_parameters(optimization_method='grid_search', max_iterations=10)
    
    print(f"Optimal parameters: {optimal_params}")
    
    # Demo 2: Market Regime Detector
    print("\n=== Testing Market Regime Detector ===")
    
    detector = MarketRegimeDetector()
    
    # Thêm một số dữ liệu giá mẫu
    for i in range(100):
        timestamp = datetime.now() - timedelta(hours=100-i)
        
        # Tạo dữ liệu giả
        base_price = 40000
        noise = np.random.normal(0, 500)
        trend = i * 50  # Xu hướng tăng
        
        open_price = base_price + trend + noise
        high_price = open_price + abs(np.random.normal(0, 200))
        low_price = open_price - abs(np.random.normal(0, 200))
        close_price = open_price + np.random.normal(0, 200)
        volume = 1000000 + np.random.normal(0, 200000)
        
        detector.add_price_data(timestamp, open_price, high_price, low_price, close_price, volume)
        
        # Thêm chỉ báo RSI giả
        detector.add_indicator_data(timestamp, 'rsi', 50 + np.random.normal(0, 10))
    
    # Phát hiện chế độ thị trường
    regime = detector.detect_market_regime()
    
    print(f"Detected market regime: {regime}")
    print(f"Regime probabilities: {detector.regime_probabilities}")
    
    # Đăng ký chiến lược cho chế độ
    detector.register_strategy_for_regime(
        regime=regime,
        strategy_name='RSI Strategy',
        parameters={'rsi_period': 14, 'rsi_overbought': 70, 'rsi_oversold': 30},
        expected_performance={'win_rate': 0.6, 'expectancy': 0.5, 'sharpe_ratio': 1.2}
    )
    
    # Lấy chiến lược tối ưu
    optimal_strategy = detector.get_optimal_strategy()
    
    print(f"Optimal strategy for current regime: {optimal_strategy['name'] if optimal_strategy else 'None'}")
    
    # Demo 3: Strategy Ensemble
    print("\n=== Testing Strategy Ensemble ===")
    
    # Tạo các đối tượng chiến lược giả
    class MockStrategy:
        def __init__(self, name):
            self.name = name
            self.parameters = {}
            
        def generate_signal(self, market_data):
            # Tạo tín hiệu ngẫu nhiên
            signals = ['buy', 'sell', 'neutral']
            signal = np.random.choice(signals, p=[0.3, 0.3, 0.4])
            confidence = np.random.uniform(0.5, 1.0)
            
            return {
                'signal': signal,
                'confidence': confidence,
                'details': {'strategy': self.name}
            }
            
        def update_parameters(self, parameters):
            self.parameters = parameters
            
    # Tạo ensemble
    ensemble = StrategyEnsemble(use_dynamic_weights=True)
    
    # Thêm các chiến lược
    ensemble.add_strategy('RSI Strategy', MockStrategy('RSI'), weight=1.0)
    ensemble.add_strategy('MACD Strategy', MockStrategy('MACD'), weight=1.0)
    ensemble.add_strategy('Bollinger Strategy', MockStrategy('Bollinger'), weight=1.0)
    
    # Cập nhật hiệu suất
    for i in range(3):
        # Tạo hiệu suất ngẫu nhiên
        performance = {
            'win_rate': np.random.uniform(0.4, 0.7),
            'expectancy': np.random.uniform(0.2, 0.8),
            'sharpe_ratio': np.random.uniform(0.8, 1.5),
            'profit_factor': np.random.uniform(1.0, 2.0),
            'drawdown': np.random.uniform(3.0, 8.0)
        }
        
        ensemble.update_strategy_performance(i, performance)
    
    # Lấy khuyến nghị kết hợp
    recommendation = ensemble.get_ensemble_recommendation(market_conditions)
    
    print(f"Ensemble recommendation: {recommendation['signal']} (confidence: {recommendation['confidence']:.2f})")
    print(f"Individual recommendations:")
    for rec in recommendation['recommendations']:
        print(f"  {rec['strategy_name']}: {rec['signal']} (weight: {rec['weight']:.2f}, confidence: {rec['confidence']:.2f})")
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    main()