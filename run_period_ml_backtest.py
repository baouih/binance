"""
Script thực hiện kiểm thử kỹ lưỡng với mô hình ML trên nhiều khoảng thời gian
"""
import os
import sys
import logging
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report, confusion_matrix

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('period_ml_backtest.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("period_ml_backtest")

# Danh sách các đồng tiền cần kiểm thử
DEFAULT_COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

# Danh sách các khung thời gian
DEFAULT_TIMEFRAMES = ["1h"]

# Danh sách các khoảng thời gian kiểm thử
DEFAULT_PERIODS = {
    "1m": 30,   # 1 tháng: 30 ngày
    "3m": 90,   # 3 tháng: 90 ngày
    "6m": 180,  # 6 tháng: 180 ngày
}

class MLBacktester:
    """Lớp kiểm thử mô hình ML trên nhiều khoảng thời gian"""
    
    def __init__(self, data_dir: str = 'test_data', 
                results_dir: str = 'ml_results',
                charts_dir: str = 'ml_charts',
                models_dir: str = 'ml_models'):
        """
        Khởi tạo kiểm thử ML
        
        Args:
            data_dir (str): Thư mục chứa dữ liệu
            results_dir (str): Thư mục lưu kết quả
            charts_dir (str): Thư mục lưu biểu đồ
            models_dir (str): Thư mục lưu mô hình
        """
        self.data_dir = data_dir
        self.results_dir = results_dir
        self.charts_dir = charts_dir
        self.models_dir = models_dir
        
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(results_dir, exist_ok=True)
        os.makedirs(charts_dir, exist_ok=True)
        os.makedirs(models_dir, exist_ok=True)
        
        # Lưu trữ dữ liệu
        self.data_cache = {}
        self.models = {}
        self.scalers = {}
        self.results = {}
        
    def prepare_feature_periods(self, 
                             coins: List[str] = None, 
                             timeframes: List[str] = None, 
                             periods: Dict[str, int] = None,
                             extract_features: bool = True) -> bool:
        """
        Chuẩn bị dữ liệu và trích xuất đặc trưng
        
        Args:
            coins (List[str]): Danh sách đồng tiền
            timeframes (List[str]): Danh sách khung thời gian
            periods (Dict[str, int]): Các khoảng thời gian kiểm thử
            extract_features (bool): Có trích xuất đặc trưng không
            
        Returns:
            bool: True nếu thành công, False nếu không
        """
        # Sử dụng mặc định nếu không cung cấp
        if not coins:
            coins = DEFAULT_COINS
        if not timeframes:
            timeframes = DEFAULT_TIMEFRAMES
        if not periods:
            periods = DEFAULT_PERIODS
            
        logger.info(f"Chuẩn bị dữ liệu cho {len(coins)} coins, {len(timeframes)} khung thời gian, {len(periods)} khoảng thời gian")
        
        success_count = 0
        
        for coin in coins:
            for timeframe in timeframes:
                for period_name, days in periods.items():
                    try:
                        # Tạo key
                        key = f"{coin}_{timeframe}_{period_name}"
                        
                        # Kiểm tra file dữ liệu
                        data_file = os.path.join(self.data_dir, f"{coin}_{timeframe}.csv")
                        
                        if not os.path.exists(data_file):
                            logger.warning(f"Không tìm thấy file dữ liệu {data_file}, bỏ qua")
                            continue
                            
                        # Đọc dữ liệu
                        df = pd.read_csv(data_file)
                        
                        # Chuyển đổi timestamp
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                        df.set_index('timestamp', inplace=True)
                        
                        # Lấy dữ liệu trong khoảng thời gian
                        end_date = df.index.max()
                        start_date = end_date - timedelta(days=days)
                        
                        period_df = df[df.index >= start_date]
                        
                        if len(period_df) < 100:  # Cần ít nhất 100 mẫu
                            logger.warning(f"Không đủ dữ liệu cho {key}: chỉ có {len(period_df)} mẫu, bỏ qua")
                            continue
                        
                        logger.info(f"Đã tải dữ liệu {key}: {len(period_df)} mẫu từ {period_df.index.min()} đến {period_df.index.max()}")
                        
                        # Trích xuất đặc trưng nếu cần
                        if extract_features:
                            # Thêm các đặc trưng
                            features_df = self._extract_features(period_df)
                            
                            if features_df is not None:
                                # Lưu vào cache
                                self.data_cache[key] = features_df
                                success_count += 1
                                
                                logger.info(f"Đã trích xuất đặc trưng cho {key}: {len(features_df)} mẫu")
                        else:
                            # Lưu nguyên dữ liệu
                            self.data_cache[key] = period_df
                            success_count += 1
                            
                    except Exception as e:
                        logger.error(f"Lỗi khi chuẩn bị dữ liệu {key}: {str(e)}")
                        
        logger.info(f"Đã chuẩn bị {success_count} bộ dữ liệu thành công")
        return success_count > 0
    
    def _extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Trích xuất đặc trưng từ dữ liệu giá
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu giá
            
        Returns:
            pd.DataFrame: DataFrame với đặc trưng đã thêm
        """
        try:
            # Tạo bản sao để tránh thay đổi dữ liệu gốc
            features_df = df.copy()
            
            # Thêm SMA
            for window in [5, 10, 20, 50, 100]:
                features_df[f'sma{window}'] = features_df['close'].rolling(window=window).mean()
            
            # Thêm EMA
            for window in [5, 10, 20, 50]:
                features_df[f'ema{window}'] = features_df['close'].ewm(span=window, adjust=False).mean()
            
            # Tính RSI
            delta = features_df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            
            rs = avg_gain / avg_loss
            features_df['rsi'] = 100 - (100 / (1 + rs))
            
            # Tính MACD
            ema12 = features_df['close'].ewm(span=12, adjust=False).mean()
            ema26 = features_df['close'].ewm(span=26, adjust=False).mean()
            features_df['macd'] = ema12 - ema26
            features_df['macd_signal'] = features_df['macd'].ewm(span=9, adjust=False).mean()
            features_df['macd_hist'] = features_df['macd'] - features_df['macd_signal']
            
            # Tính Bollinger Bands
            features_df['bb_middle'] = features_df['close'].rolling(window=20).mean()
            bb_std = features_df['close'].rolling(window=20).std()
            features_df['bb_upper'] = features_df['bb_middle'] + 2 * bb_std
            features_df['bb_lower'] = features_df['bb_middle'] - 2 * bb_std
            
            # Tính tỷ lệ price/SMA
            features_df['price_sma20_ratio'] = features_df['close'] / features_df['sma20']
            features_df['price_sma50_ratio'] = features_df['close'] / features_df['sma50']
            
            # Thêm biến động
            features_df['volatility'] = (features_df['high'] - features_df['low']) / features_df['close']
            features_df['daily_return'] = features_df['close'].pct_change()
            features_df['weekly_return'] = features_df['close'].pct_change(7)
            
            # Thêm đặc trưng khối lượng
            features_df['volume_sma5'] = features_df['volume'].rolling(window=5).mean()
            features_df['volume_ratio'] = features_df['volume'] / features_df['volume_sma5']
            
            # Thêm đặc trưng hướng
            features_df['direction_1d'] = (features_df['close'] > features_df['close'].shift(1)).astype(int)
            features_df['direction_3d'] = (features_df['close'] > features_df['close'].shift(3)).astype(int)
            features_df['direction_5d'] = (features_df['close'] > features_df['close'].shift(5)).astype(int)
            
            # Tạo mục tiêu: xu hướng trong tương lai
            for days in [1, 3, 7]:
                # Mục tiêu nhị phân: lên/xuống
                features_df[f'target_{days}d'] = (features_df['close'].shift(-days) > features_df['close']).astype(int)
                
                # Mục tiêu % thay đổi giá
                features_df[f'return_{days}d'] = features_df['close'].pct_change(-days)
            
            # Loại bỏ NaN
            features_df = features_df.dropna()
            
            return features_df
            
        except Exception as e:
            logger.error(f"Lỗi khi trích xuất đặc trưng: {str(e)}")
            return None
    
    def train_test_model(self, data_key: str, target_days: int = 1,
                       test_size: float = 0.2, use_time_series_cv: bool = True,
                       n_splits: int = 5, feature_importance: bool = True) -> Dict:
        """
        Huấn luyện và kiểm thử mô hình
        
        Args:
            data_key (str): Khóa dữ liệu (coin_timeframe_period)
            target_days (int): Số ngày dự đoán (1, 3, 7)
            test_size (float): Tỷ lệ dữ liệu kiểm thử
            use_time_series_cv (bool): Sử dụng cross validation theo chuỗi thời gian
            n_splits (int): Số fold cho time series CV
            feature_importance (bool): Có tính feature importance không
            
        Returns:
            Dict: Kết quả kiểm thử
        """
        try:
            # Kiểm tra dữ liệu
            if data_key not in self.data_cache:
                logger.warning(f"Không tìm thấy dữ liệu {data_key} trong cache")
                return {}
                
            # Lấy dữ liệu
            df = self.data_cache[data_key]
            
            # Thông tin data_key
            parts = data_key.split('_')
            coin = parts[0]
            timeframe = parts[1]
            period = parts[2]
            
            # Xác định mục tiêu
            target_col = f'target_{target_days}d'
            
            if target_col not in df.columns:
                logger.warning(f"Không tìm thấy cột mục tiêu {target_col} trong dữ liệu")
                return {}
                
            # Tạo model key
            model_key = f"{data_key}_target{target_days}d"
            
            # Danh sách đặc trưng
            features = [
                'open', 'high', 'low', 'close', 'volume',
                'sma5', 'sma10', 'sma20', 'sma50', 'sma100',
                'ema5', 'ema10', 'ema20', 'ema50',
                'rsi', 'macd', 'macd_signal', 'macd_hist',
                'bb_middle', 'bb_upper', 'bb_lower',
                'price_sma20_ratio', 'price_sma50_ratio',
                'volatility', 'daily_return', 'weekly_return',
                'volume_sma5', 'volume_ratio',
                'direction_1d', 'direction_3d', 'direction_5d'
            ]
            
            # Loại bỏ các cột không có trong dữ liệu
            features = [f for f in features if f in df.columns]
            
            # Tạo X và y
            X = df[features].values
            y = df[target_col].values
            
            # Chia dữ liệu thành tập huấn luyện và tập kiểm thử
            if use_time_series_cv:
                # Sử dụng time series cross validation
                cv_results = {
                    'accuracy': [],
                    'precision': [],
                    'recall': [],
                    'f1': []
                }
                
                tscv = TimeSeriesSplit(n_splits=n_splits)
                
                for train_index, test_index in tscv.split(X):
                    X_train, X_test = X[train_index], X[test_index]
                    y_train, y_test = y[train_index], y[test_index]
                    
                    # Chuẩn hóa dữ liệu
                    scaler = StandardScaler()
                    X_train_scaled = scaler.fit_transform(X_train)
                    X_test_scaled = scaler.transform(X_test)
                    
                    # Huấn luyện mô hình
                    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
                    model.fit(X_train_scaled, y_train)
                    
                    # Dự đoán
                    y_pred = model.predict(X_test_scaled)
                    
                    # Đánh giá
                    cv_results['accuracy'].append(accuracy_score(y_test, y_pred))
                    cv_results['precision'].append(precision_score(y_test, y_pred, zero_division=0))
                    cv_results['recall'].append(recall_score(y_test, y_pred, zero_division=0))
                    cv_results['f1'].append(f1_score(y_test, y_pred, zero_division=0))
                
                # Tính trung bình các fold
                avg_results = {metric: np.mean(values) for metric, values in cv_results.items()}
                
                # Huấn luyện lại trên toàn bộ dữ liệu
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X)
                
                model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
                model.fit(X_scaled, y)
                
                # Lưu mô hình và scaler
                self.models[model_key] = model
                self.scalers[model_key] = scaler
                
                # Kết quả tổng hợp
                results = {
                    'model_key': model_key,
                    'coin': coin,
                    'timeframe': timeframe,
                    'period': period,
                    'target_days': target_days,
                    'cross_validation': {
                        'n_splits': n_splits,
                        'results': cv_results,
                        'average': avg_results
                    },
                    'final_model': {
                        'n_estimators': 100,
                        'max_depth': 10
                    },
                    'data_info': {
                        'n_samples': len(df),
                        'date_range': [str(df.index.min()), str(df.index.max())],
                        'features': features,
                        'class_distribution': {
                            'up': int(sum(y)),
                            'down': int(len(y) - sum(y))
                        }
                    }
                }
                
            else:
                # Chia dữ liệu theo tỷ lệ
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, shuffle=False)
                
                # Chuẩn hóa dữ liệu
                scaler = StandardScaler()
                X_train_scaled = scaler.fit_transform(X_train)
                X_test_scaled = scaler.transform(X_test)
                
                # Huấn luyện mô hình
                model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
                model.fit(X_train_scaled, y_train)
                
                # Dự đoán
                y_pred = model.predict(X_test_scaled)
                
                # Đánh giá
                accuracy = accuracy_score(y_test, y_pred)
                precision = precision_score(y_test, y_pred, zero_division=0)
                recall = recall_score(y_test, y_pred, zero_division=0)
                f1 = f1_score(y_test, y_pred, zero_division=0)
                
                # Lưu mô hình và scaler
                self.models[model_key] = model
                self.scalers[model_key] = scaler
                
                # Lưu y_test và y_pred để vẽ biểu đồ
                y_test_dates = df.index[-len(y_test):].tolist()
                
                # Kết quả
                results = {
                    'model_key': model_key,
                    'coin': coin,
                    'timeframe': timeframe,
                    'period': period,
                    'target_days': target_days,
                    'metrics': {
                        'accuracy': float(accuracy),
                        'precision': float(precision),
                        'recall': float(recall),
                        'f1': float(f1)
                    },
                    'data_info': {
                        'n_samples': len(df),
                        'train_samples': len(X_train),
                        'test_samples': len(X_test),
                        'date_range': [str(df.index.min()), str(df.index.max())],
                        'features': features,
                        'class_distribution': {
                            'up': int(sum(y)),
                            'down': int(len(y) - sum(y))
                        }
                    }
                }
                
                # Lưu report và confusion matrix
                report = classification_report(y_test, y_pred, output_dict=True)
                results['classification_report'] = report
                
                cf_matrix = confusion_matrix(y_test, y_pred).tolist()
                results['confusion_matrix'] = cf_matrix
                
                # Tạo biểu đồ confusion matrix
                plt.figure(figsize=(8, 6))
                plt.imshow(cf_matrix, cmap=plt.cm.Blues)
                plt.title(f'Confusion Matrix - {model_key}')
                plt.colorbar()
                
                classes = ['Down', 'Up']
                tick_marks = [0, 1]
                plt.xticks(tick_marks, classes)
                plt.yticks(tick_marks, classes)
                
                # Thêm số liệu vào biểu đồ
                thresh = cf_matrix[0][0] + cf_matrix[1][1]
                for i in range(2):
                    for j in range(2):
                        plt.text(j, i, str(cf_matrix[i][j]),
                                horizontalalignment="center",
                                color="white" if cf_matrix[i][j] > thresh/2 else "black")
                                
                plt.xlabel('Predicted')
                plt.ylabel('True')
                plt.tight_layout()
                
                # Lưu biểu đồ
                cm_chart_path = os.path.join(self.charts_dir, f"{model_key}_confusion_matrix.png")
                plt.savefig(cm_chart_path)
                plt.close()
                
                # Tạo biểu đồ dự đoán
                plt.figure(figsize=(12, 6))
                
                # Giá và dự đoán
                ax1 = plt.subplot(2, 1, 1)
                ax1.plot(df.index[-len(y_test):], df['close'].values[-len(y_test):], label='Price')
                ax1.set_title(f'Price & Predictions - {model_key}')
                ax1.set_ylabel('Price')
                ax1.grid(True)
                ax1.legend()
                
                # Dự đoán
                ax2 = plt.subplot(2, 1, 2)
                ax2.plot(df.index[-len(y_test):], y_test, 'b-', label='True Direction')
                ax2.plot(df.index[-len(y_test):], y_pred, 'r--', label='Predicted Direction')
                ax2.set_xlabel('Date')
                ax2.set_ylabel('Direction (1=Up, 0=Down)')
                ax2.set_yticks([0, 1])
                ax2.grid(True)
                ax2.legend()
                
                plt.tight_layout()
                
                # Lưu biểu đồ
                pred_chart_path = os.path.join(self.charts_dir, f"{model_key}_predictions.png")
                plt.savefig(pred_chart_path)
                plt.close()
                
                # Thêm đường dẫn biểu đồ vào kết quả
                results['charts'] = {
                    'confusion_matrix': cm_chart_path,
                    'predictions': pred_chart_path
                }
            
            # Tính feature importance nếu cần
            if feature_importance:
                # Lấy feature importance từ mô hình
                importance = model.feature_importances_
                
                # Sắp xếp theo thứ tự giảm dần
                feature_importance = pd.DataFrame({
                    'feature': features,
                    'importance': importance
                }).sort_values('importance', ascending=False)
                
                # Lưu vào kết quả
                results['feature_importance'] = feature_importance.to_dict('records')
                
                # Vẽ biểu đồ top 15 feature importance
                plt.figure(figsize=(10, 8))
                top_features = feature_importance.head(15)
                plt.barh(top_features['feature'], top_features['importance'])
                plt.title(f'Top Feature Importance - {model_key}')
                plt.xlabel('Importance')
                plt.tight_layout()
                
                # Lưu biểu đồ
                fi_chart_path = os.path.join(self.charts_dir, f"{model_key}_feature_importance.png")
                plt.savefig(fi_chart_path)
                plt.close()
                
                # Thêm đường dẫn biểu đồ vào kết quả
                if 'charts' not in results:
                    results['charts'] = {}
                results['charts']['feature_importance'] = fi_chart_path
            
            # Lưu mô hình và scaler
            import joblib
            model_path = os.path.join(self.models_dir, f"{model_key}_model.joblib")
            scaler_path = os.path.join(self.models_dir, f"{model_key}_scaler.joblib")
            
            joblib.dump(model, model_path)
            joblib.dump(scaler, scaler_path)
            
            # Lưu danh sách đặc trưng
            feature_path = os.path.join(self.models_dir, f"{model_key}_features.json")
            with open(feature_path, 'w') as f:
                json.dump({
                    'features': features,
                    'creation_date': datetime.now().isoformat(),
                    'info': {
                        'coin': coin,
                        'timeframe': timeframe,
                        'period': period,
                        'target_days': target_days
                    }
                }, f, indent=2)
            
            # Lưu kết quả
            results_path = os.path.join(self.results_dir, f"{model_key}_results.json")
            with open(results_path, 'w') as f:
                json.dump(results, f, indent=2)
                
            # Lưu vào đối tượng
            self.results[model_key] = results
            
            logger.info(f"Đã huấn luyện và lưu mô hình {model_key}")
            
            return results
            
        except Exception as e:
            logger.error(f"Lỗi khi huấn luyện mô hình cho {data_key}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {}
    
    def run_all_models(self, target_days: List[int] = None,
                     time_series_cv: bool = True) -> Dict:
        """
        Chạy huấn luyện cho tất cả các bộ dữ liệu
        
        Args:
            target_days (List[int]): Danh sách ngày dự đoán
            time_series_cv (bool): Sử dụng time series CV
            
        Returns:
            Dict: Kết quả tổng hợp
        """
        # Sử dụng mặc định nếu không cung cấp
        if not target_days:
            target_days = [1, 3, 7]
            
        logger.info(f"Chạy huấn luyện cho {len(self.data_cache)} bộ dữ liệu, {len(target_days)} mục tiêu")
        
        all_results = {}
        
        for data_key in self.data_cache.keys():
            for days in target_days:
                try:
                    # Huấn luyện mô hình
                    results = self.train_test_model(
                        data_key=data_key,
                        target_days=days,
                        use_time_series_cv=time_series_cv
                    )
                    
                    if results:
                        model_key = f"{data_key}_target{days}d"
                        all_results[model_key] = results
                        
                except Exception as e:
                    logger.error(f"Lỗi khi chạy mô hình {data_key} cho {days} ngày: {str(e)}")
        
        # Tạo báo cáo tổng hợp
        self._create_summary_report(all_results)
        
        logger.info(f"Đã chạy huấn luyện cho {len(all_results)} mô hình")
        
        return all_results
    
    def _create_summary_report(self, all_results: Dict) -> None:
        """
        Tạo báo cáo tổng hợp từ các kết quả
        
        Args:
            all_results (Dict): Kết quả của tất cả các mô hình
        """
        try:
            if not all_results:
                logger.warning("Không có kết quả để tạo báo cáo tổng hợp")
                return
                
            # Tổng hợp dữ liệu
            summary = {
                'timestamp': datetime.now().isoformat(),
                'total_models': len(all_results),
                'coins': list(set(result['coin'] for result in all_results.values())),
                'timeframes': list(set(result['timeframe'] for result in all_results.values())),
                'periods': list(set(result['period'] for result in all_results.values())),
                'target_days': list(set(result['target_days'] for result in all_results.values())),
                'performance_by_coin': {},
                'performance_by_period': {},
                'performance_by_target': {},
                'best_models': {
                    'accuracy': {'model': '', 'value': 0},
                    'precision': {'model': '', 'value': 0},
                    'recall': {'model': '', 'value': 0},
                    'f1': {'model': '', 'value': 0}
                }
            }
            
            # Tính hiệu suất theo coin
            for coin in summary['coins']:
                coin_results = [r for r in all_results.values() if r['coin'] == coin]
                
                if coin_results:
                    if 'cross_validation' in coin_results[0]:
                        # Lấy kết quả cross-validation
                        accuracy = np.mean([r['cross_validation']['average']['accuracy'] for r in coin_results])
                        precision = np.mean([r['cross_validation']['average']['precision'] for r in coin_results])
                        recall = np.mean([r['cross_validation']['average']['recall'] for r in coin_results])
                        f1 = np.mean([r['cross_validation']['average']['f1'] for r in coin_results])
                    else:
                        # Lấy kết quả thông thường
                        accuracy = np.mean([r['metrics']['accuracy'] for r in coin_results])
                        precision = np.mean([r['metrics']['precision'] for r in coin_results])
                        recall = np.mean([r['metrics']['recall'] for r in coin_results])
                        f1 = np.mean([r['metrics']['f1'] for r in coin_results])
                        
                    summary['performance_by_coin'][coin] = {
                        'accuracy': float(accuracy),
                        'precision': float(precision),
                        'recall': float(recall),
                        'f1': float(f1),
                        'n_models': len(coin_results)
                    }
            
            # Tính hiệu suất theo khoảng thời gian
            for period in summary['periods']:
                period_results = [r for r in all_results.values() if r['period'] == period]
                
                if period_results:
                    if 'cross_validation' in period_results[0]:
                        # Lấy kết quả cross-validation
                        accuracy = np.mean([r['cross_validation']['average']['accuracy'] for r in period_results])
                        precision = np.mean([r['cross_validation']['average']['precision'] for r in period_results])
                        recall = np.mean([r['cross_validation']['average']['recall'] for r in period_results])
                        f1 = np.mean([r['cross_validation']['average']['f1'] for r in period_results])
                    else:
                        # Lấy kết quả thông thường
                        accuracy = np.mean([r['metrics']['accuracy'] for r in period_results])
                        precision = np.mean([r['metrics']['precision'] for r in period_results])
                        recall = np.mean([r['metrics']['recall'] for r in period_results])
                        f1 = np.mean([r['metrics']['f1'] for r in period_results])
                        
                    summary['performance_by_period'][period] = {
                        'accuracy': float(accuracy),
                        'precision': float(precision),
                        'recall': float(recall),
                        'f1': float(f1),
                        'n_models': len(period_results)
                    }
            
            # Tính hiệu suất theo mục tiêu dự đoán
            for days in summary['target_days']:
                target_results = [r for r in all_results.values() if r['target_days'] == days]
                
                if target_results:
                    if 'cross_validation' in target_results[0]:
                        # Lấy kết quả cross-validation
                        accuracy = np.mean([r['cross_validation']['average']['accuracy'] for r in target_results])
                        precision = np.mean([r['cross_validation']['average']['precision'] for r in target_results])
                        recall = np.mean([r['cross_validation']['average']['recall'] for r in target_results])
                        f1 = np.mean([r['cross_validation']['average']['f1'] for r in target_results])
                    else:
                        # Lấy kết quả thông thường
                        accuracy = np.mean([r['metrics']['accuracy'] for r in target_results])
                        precision = np.mean([r['metrics']['precision'] for r in target_results])
                        recall = np.mean([r['metrics']['recall'] for r in target_results])
                        f1 = np.mean([r['metrics']['f1'] for r in target_results])
                        
                    summary['performance_by_target'][str(days)] = {
                        'accuracy': float(accuracy),
                        'precision': float(precision),
                        'recall': float(recall),
                        'f1': float(f1),
                        'n_models': len(target_results)
                    }
            
            # Tìm các mô hình tốt nhất
            for model_key, result in all_results.items():
                if 'cross_validation' in result:
                    # Lấy kết quả cross-validation
                    accuracy = result['cross_validation']['average']['accuracy']
                    precision = result['cross_validation']['average']['precision']
                    recall = result['cross_validation']['average']['recall']
                    f1 = result['cross_validation']['average']['f1']
                else:
                    # Lấy kết quả thông thường
                    accuracy = result['metrics']['accuracy']
                    precision = result['metrics']['precision']
                    recall = result['metrics']['recall']
                    f1 = result['metrics']['f1']
                    
                # Kiểm tra và cập nhật nếu tốt hơn
                if accuracy > summary['best_models']['accuracy']['value']:
                    summary['best_models']['accuracy'] = {'model': model_key, 'value': float(accuracy)}
                    
                if precision > summary['best_models']['precision']['value']:
                    summary['best_models']['precision'] = {'model': model_key, 'value': float(precision)}
                    
                if recall > summary['best_models']['recall']['value']:
                    summary['best_models']['recall'] = {'model': model_key, 'value': float(recall)}
                    
                if f1 > summary['best_models']['f1']['value']:
                    summary['best_models']['f1'] = {'model': model_key, 'value': float(f1)}
            
            # Lưu báo cáo tổng hợp
            summary_path = os.path.join(self.results_dir, "ml_summary_report.json")
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2)
                
            logger.info(f"Đã tạo báo cáo tổng hợp: {summary_path}")
            
            # Tạo báo cáo HTML
            self._create_html_report(summary, all_results)
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo tổng hợp: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _create_html_report(self, summary: Dict, all_results: Dict) -> None:
        """
        Tạo báo cáo HTML
        
        Args:
            summary (Dict): Báo cáo tổng hợp
            all_results (Dict): Kết quả của tất cả các mô hình
        """
        try:
            # Tạo nội dung HTML
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Báo cáo ML - Dự đoán xu hướng</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    h1, h2, h3 { color: #333; }
                    table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #f2f2f2; }
                    .card { border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin-bottom: 20px; }
                    .positive { color: green; }
                    .negative { color: red; }
                    .chart { margin: 20px 0; max-width: 100%; }
                    .tabs { display: flex; margin-bottom: 10px; }
                    .tab { padding: 8px 16px; background-color: #f2f2f2; cursor: pointer; border: 1px solid #ddd; border-bottom: none; }
                    .tab.active { background-color: #fff; border-bottom: 1px solid #fff; }
                    .tab-content { display: none; border: 1px solid #ddd; padding: 15px; }
                    .tab-content.active { display: block; }
                </style>
                <script>
                    function openTab(evt, tabName) {
                        var i, tabcontent, tablinks;
                        tabcontent = document.getElementsByClassName("tab-content");
                        for (i = 0; i < tabcontent.length; i++) {
                            tabcontent[i].className = tabcontent[i].className.replace(" active", "");
                        }
                        tablinks = document.getElementsByClassName("tab");
                        for (i = 0; i < tablinks.length; i++) {
                            tablinks[i].className = tablinks[i].className.replace(" active", "");
                        }
                        document.getElementById(tabName).className += " active";
                        evt.currentTarget.className += " active";
                    }
                </script>
            </head>
            <body>
                <h1>Báo cáo ML - Dự đoán xu hướng</h1>
                <p>Thời gian: """ + summary['timestamp'] + """</p>
                
                <div class="card">
                    <h2>Tổng quan</h2>
                    <table>
                        <tr>
                            <th>Tổng số mô hình</th>
                            <td>""" + str(summary['total_models']) + """</td>
                        </tr>
                        <tr>
                            <th>Coins</th>
                            <td>""" + ", ".join(summary['coins']) + """</td>
                        </tr>
                        <tr>
                            <th>Khung thời gian</th>
                            <td>""" + ", ".join(summary['timeframes']) + """</td>
                        </tr>
                        <tr>
                            <th>Khoảng thời gian</th>
                            <td>""" + ", ".join(summary['periods']) + """</td>
                        </tr>
                        <tr>
                            <th>Mục tiêu dự đoán (ngày)</th>
                            <td>""" + ", ".join(str(d) for d in summary['target_days']) + """</td>
                        </tr>
                    </table>
                </div>
                
                <div class="card">
                    <h2>Mô hình tốt nhất</h2>
                    <table>
                        <tr>
                            <th>Chỉ số</th>
                            <th>Mô hình</th>
                            <th>Giá trị</th>
                        </tr>
            """
            
            for metric, data in summary['best_models'].items():
                html += f"""
                        <tr>
                            <td>{metric.capitalize()}</td>
                            <td>{data['model']}</td>
                            <td>{data['value']:.4f}</td>
                        </tr>
                """
                
            html += """
                    </table>
                </div>
                
                <div class="tabs">
                    <button class="tab active" onclick="openTab(event, 'byCoin')">Theo Coin</button>
                    <button class="tab" onclick="openTab(event, 'byPeriod')">Theo khoảng thời gian</button>
                    <button class="tab" onclick="openTab(event, 'byTarget')">Theo mục tiêu dự đoán</button>
                    <button class="tab" onclick="openTab(event, 'allModels')">Tất cả mô hình</button>
                </div>
                
                <div id="byCoin" class="tab-content active">
                    <h2>Hiệu suất theo Coin</h2>
                    <table>
                        <tr>
                            <th>Coin</th>
                            <th>Accuracy</th>
                            <th>Precision</th>
                            <th>Recall</th>
                            <th>F1</th>
                            <th>Số lượng mô hình</th>
                        </tr>
            """
            
            # Thêm dữ liệu hiệu suất theo coin
            for coin, metrics in summary['performance_by_coin'].items():
                html += f"""
                        <tr>
                            <td>{coin}</td>
                            <td>{metrics['accuracy']:.4f}</td>
                            <td>{metrics['precision']:.4f}</td>
                            <td>{metrics['recall']:.4f}</td>
                            <td>{metrics['f1']:.4f}</td>
                            <td>{metrics['n_models']}</td>
                        </tr>
                """
                
            html += """
                    </table>
                </div>
                
                <div id="byPeriod" class="tab-content">
                    <h2>Hiệu suất theo khoảng thời gian</h2>
                    <table>
                        <tr>
                            <th>Khoảng thời gian</th>
                            <th>Accuracy</th>
                            <th>Precision</th>
                            <th>Recall</th>
                            <th>F1</th>
                            <th>Số lượng mô hình</th>
                        </tr>
            """
            
            # Thêm dữ liệu hiệu suất theo khoảng thời gian
            for period, metrics in summary['performance_by_period'].items():
                html += f"""
                        <tr>
                            <td>{period}</td>
                            <td>{metrics['accuracy']:.4f}</td>
                            <td>{metrics['precision']:.4f}</td>
                            <td>{metrics['recall']:.4f}</td>
                            <td>{metrics['f1']:.4f}</td>
                            <td>{metrics['n_models']}</td>
                        </tr>
                """
                
            html += """
                    </table>
                </div>
                
                <div id="byTarget" class="tab-content">
                    <h2>Hiệu suất theo mục tiêu dự đoán</h2>
                    <table>
                        <tr>
                            <th>Mục tiêu (ngày)</th>
                            <th>Accuracy</th>
                            <th>Precision</th>
                            <th>Recall</th>
                            <th>F1</th>
                            <th>Số lượng mô hình</th>
                        </tr>
            """
            
            # Thêm dữ liệu hiệu suất theo mục tiêu
            for days, metrics in summary['performance_by_target'].items():
                html += f"""
                        <tr>
                            <td>{days}</td>
                            <td>{metrics['accuracy']:.4f}</td>
                            <td>{metrics['precision']:.4f}</td>
                            <td>{metrics['recall']:.4f}</td>
                            <td>{metrics['f1']:.4f}</td>
                            <td>{metrics['n_models']}</td>
                        </tr>
                """
                
            html += """
                    </table>
                </div>
                
                <div id="allModels" class="tab-content">
                    <h2>Tất cả mô hình</h2>
                    <table>
                        <tr>
                            <th>Mô hình</th>
                            <th>Coin</th>
                            <th>Timeframe</th>
                            <th>Khoảng thời gian</th>
                            <th>Mục tiêu (ngày)</th>
                            <th>Accuracy</th>
                            <th>Precision</th>
                            <th>Recall</th>
                            <th>F1</th>
                            <th>Biểu đồ</th>
                        </tr>
            """
            
            # Thêm dữ liệu tất cả mô hình
            for model_key, result in all_results.items():
                if 'cross_validation' in result:
                    # Lấy kết quả cross-validation
                    accuracy = result['cross_validation']['average']['accuracy']
                    precision = result['cross_validation']['average']['precision']
                    recall = result['cross_validation']['average']['recall']
                    f1 = result['cross_validation']['average']['f1']
                    charts = ""
                else:
                    # Lấy kết quả thông thường
                    accuracy = result['metrics']['accuracy']
                    precision = result['metrics']['precision']
                    recall = result['metrics']['recall']
                    f1 = result['metrics']['f1']
                    
                    # Thêm liên kết biểu đồ
                    charts = ""
                    if 'charts' in result:
                        for chart_name, chart_path in result['charts'].items():
                            chart_filename = os.path.basename(chart_path)
                            # Sử dụng đường dẫn tương đối
                            charts += f'<a href="../{chart_path}" target="_blank">{chart_name}</a><br>'
                
                html += f"""
                        <tr>
                            <td>{model_key}</td>
                            <td>{result['coin']}</td>
                            <td>{result['timeframe']}</td>
                            <td>{result['period']}</td>
                            <td>{result['target_days']}</td>
                            <td>{accuracy:.4f}</td>
                            <td>{precision:.4f}</td>
                            <td>{recall:.4f}</td>
                            <td>{f1:.4f}</td>
                            <td>{charts}</td>
                        </tr>
                """
                
            html += """
                    </table>
                </div>
                
                <div class="card">
                    <h2>Kết luận</h2>
                    <p>Dựa trên kết quả kiểm thử các mô hình ML, chúng ta có thể đưa ra các nhận xét sau:</p>
                    <ul>
            """
            
            # Thêm một số kết luận dựa trên dữ liệu
            
            # 1. Coin nào hiệu quả nhất
            best_coin = max(summary['performance_by_coin'].items(), key=lambda x: x[1]['f1'])
            html += f"""
                        <li>Coin có hiệu suất dự đoán tốt nhất là <strong>{best_coin[0]}</strong> với F1-score trung bình {best_coin[1]['f1']:.4f}</li>
            """
            
            # 2. Khoảng thời gian nào hiệu quả nhất
            best_period = max(summary['performance_by_period'].items(), key=lambda x: x[1]['f1'])
            html += f"""
                        <li>Khoảng thời gian kiểm thử cho kết quả tốt nhất là <strong>{best_period[0]}</strong> với F1-score trung bình {best_period[1]['f1']:.4f}</li>
            """
            
            # 3. Mục tiêu dự đoán nào hiệu quả nhất
            best_target = max(summary['performance_by_target'].items(), key=lambda x: x[1]['f1'])
            html += f"""
                        <li>Mục tiêu dự đoán cho kết quả tốt nhất là <strong>{best_target[0]} ngày</strong> với F1-score trung bình {best_target[1]['f1']:.4f}</li>
            """
            
            html += """
                    </ul>
                </div>
            </body>
            </html>
            """
            
            # Lưu báo cáo HTML
            html_path = os.path.join(self.results_dir, "ml_summary_report.html")
            with open(html_path, 'w') as f:
                f.write(html)
                
            logger.info(f"Đã tạo báo cáo HTML: {html_path}")
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo HTML: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

def main():
    """Hàm chính để chạy kiểm thử ML"""
    import argparse
    
    # Tạo parser cho đối số dòng lệnh
    parser = argparse.ArgumentParser(description='Kiểm thử ML với nhiều khoảng thời gian')
    parser.add_argument('--full', action='store_true', help='Chạy kiểm thử đầy đủ với tất cả khoảng thời gian')
    parser.add_argument('--coins', nargs='+', default=["BTCUSDT", "ETHUSDT"], 
                      help='Danh sách các đồng tiền cần kiểm thử (mặc định: BTCUSDT ETHUSDT)')
    parser.add_argument('--timeframes', nargs='+', default=["1h"], 
                      help='Danh sách các khung thời gian (mặc định: 1h)')
    parser.add_argument('--periods', nargs='+', default=["1m", "3m"], 
                      help='Danh sách các khoảng thời gian (mặc định: 1m 3m)')
    parser.add_argument('--target-days', nargs='+', type=int, default=[1, 3], 
                      help='Danh sách các ngày dự đoán (mặc định: 1 3)')
    parser.add_argument('--cv', action='store_true', help='Sử dụng time series cross-validation')
    parser.add_argument('--output-dir', default='ml_results', help='Thư mục lưu kết quả')
    
    # Parse đối số
    args = parser.parse_args()
    
    try:
        # Khởi tạo backtester
        backtester = MLBacktester(
            results_dir=args.output_dir,
            charts_dir='ml_charts',
            models_dir='ml_models'
        )
        
        # Xác định khoảng thời gian cần kiểm thử
        if args.full:
            # Chạy kiểm thử đầy đủ
            periods_dict = {
                "1m": 30,    # 1 tháng: 30 ngày
                "3m": 90,    # 3 tháng: 90 ngày
                "6m": 180    # 6 tháng: 180 ngày
            }
            coins = DEFAULT_COINS
            timeframes = ["1h", "4h"]
            target_days = [1, 3, 7]
            logger.info("Chạy kiểm thử đầy đủ với tất cả khoảng thời gian")
        else:
            # Chạy kiểm thử với tham số đã chọn
            periods_dict = {}
            for period in args.periods:
                if period == "1m":
                    periods_dict[period] = 30
                elif period == "3m":
                    periods_dict[period] = 90
                elif period == "6m":
                    periods_dict[period] = 180
                else:
                    # Thử chuyển đổi thành số ngày
                    try:
                        days = int(period.replace("d", ""))
                        periods_dict[period] = days
                    except:
                        logger.warning(f"Không nhận dạng được khoảng thời gian {period}, bỏ qua")
            
            coins = args.coins
            timeframes = args.timeframes
            target_days = args.target_days
        
        logger.info(f"Tham số chạy: coins={coins}, timeframes={timeframes}, periods={periods_dict}, target_days={target_days}")
        
        # Chuẩn bị dữ liệu và trích xuất đặc trưng
        print("Chuẩn bị dữ liệu và trích xuất đặc trưng...")
        backtester.prepare_feature_periods(
            coins=coins,
            timeframes=timeframes,
            periods=periods_dict
        )
        
        # Chạy huấn luyện và kiểm thử cho tất cả dữ liệu
        print("Chạy huấn luyện và kiểm thử...")
        all_results = backtester.run_all_models(
            target_days=target_days,
            time_series_cv=args.cv
        )
        
        print(f"Đã hoàn thành! Đã huấn luyện {len(all_results)} mô hình")
        print(f"Báo cáo tổng hợp: {os.path.join(backtester.results_dir, 'ml_summary_report.html')}")
        
    except Exception as e:
        logger.error(f"Lỗi khi chạy kiểm thử ML: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()