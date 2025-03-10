#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ML Integration Manager - Tích hợp và quản lý tất cả các thành phần ML trong hệ thống
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Union, Optional, Any
from datetime import datetime
import joblib
from concurrent.futures import ThreadPoolExecutor, as_completed

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ml_integration')

# Thử import các modules
try:
    from multi_task_model import MultiTaskModel, MultiTaskModelTrainer
    MULTI_TASK_AVAILABLE = True
except ImportError:
    MULTI_TASK_AVAILABLE = False
    logger.warning("Multi-task learning không khả dụng")

try:
    from feature_fusion_pipeline import FeatureFusionPipeline
    FEATURE_FUSION_AVAILABLE = True
except ImportError:
    FEATURE_FUSION_AVAILABLE = False
    logger.warning("Feature fusion không khả dụng")

try:
    from enhanced_market_regime_detector import EnhancedMarketRegimeDetector
    ENHANCED_REGIME_AVAILABLE = True
except ImportError:
    ENHANCED_REGIME_AVAILABLE = False
    logger.warning("Enhanced market regime detector không khả dụng")

try:
    from reinforcement_agent import ReinforcementTrader
    RL_AVAILABLE = True
except ImportError:
    RL_AVAILABLE = False
    logger.warning("Reinforcement learning không khả dụng")

class MLIntegrationManager:
    """
    Quản lý và tích hợp tất cả các thành phần ML của hệ thống
    """
    
    def __init__(
        self,
        api: 'BinanceAPI' = None,
        data_processor: 'DataProcessor' = None,
        symbol: str = 'BTCUSDT',
        base_interval: str = '1h',
        models_dir: str = 'ml_models',
        use_multi_task: bool = True,
        use_feature_fusion: bool = True,
        use_enhanced_regime: bool = True,
        use_reinforcement: bool = True,
        config_path: str = 'configs/ml_integration_config.json'
    ):
        """
        Khởi tạo ML Integration Manager
        
        Args:
            api: Đối tượng API giao dịch
            data_processor: Đối tượng xử lý dữ liệu
            symbol: Mã tiền
            base_interval: Khung thời gian cơ sở
            models_dir: Thư mục chứa mô hình
            use_multi_task: Sử dụng multi-task learning nếu True
            use_feature_fusion: Sử dụng feature fusion nếu True
            use_enhanced_regime: Sử dụng enhanced market regime detector nếu True
            use_reinforcement: Sử dụng reinforcement learning nếu True
            config_path: Đường dẫn file cấu hình
        """
        self.api = api
        self.data_processor = data_processor
        self.symbol = symbol
        self.base_interval = base_interval
        self.models_dir = models_dir
        self.use_multi_task = use_multi_task and MULTI_TASK_AVAILABLE
        self.use_feature_fusion = use_feature_fusion and FEATURE_FUSION_AVAILABLE
        self.use_enhanced_regime = use_enhanced_regime and ENHANCED_REGIME_AVAILABLE
        self.use_reinforcement = use_reinforcement and RL_AVAILABLE
        self.config_path = config_path
        
        # Tạo thư mục mô hình nếu chưa tồn tại
        os.makedirs(models_dir, exist_ok=True)
        
        # Tạo thư mục chứa các thư mục con cho từng loại mô hình
        os.makedirs(os.path.join(models_dir, 'multi_task'), exist_ok=True)
        os.makedirs(os.path.join(models_dir, 'feature_fusion'), exist_ok=True)
        os.makedirs(os.path.join(models_dir, 'market_regime'), exist_ok=True)
        os.makedirs(os.path.join(models_dir, 'reinforcement'), exist_ok=True)
        
        # Khởi tạo các thành phần
        self.multi_task_model = None
        self.feature_fusion = None
        self.regime_detector = None
        self.reinforcement_trader = None
        
        # Tải cấu hình
        self.config = self._load_config()
        
        # Khởi tạo các thành phần nếu được yêu cầu
        self._initialize_components()
        
        # Trạng thái hiện tại
        self.current_data = None
        self.current_predictions = {}
        self.current_regime = None
        self.current_features = None
        
        # Cache
        self.cached_data = {}
        self.last_update_time = {}
        
        logger.info(f"Đã khởi tạo ML Integration Manager cho {symbol} {base_interval}")
    
    def _load_config(self) -> Dict:
        """
        Tải cấu hình từ file
        
        Returns:
            Dict chứa cấu hình
        """
        # Cấu hình mặc định
        default_config = {
            'multi_task': {
                'model_name': f"{self.symbol}_{self.base_interval}_multi_task",
                'time_steps': 60,
                'target_columns': {
                    'trend': 'target_trend',
                    'volatility': 'target_volatility',
                    'reversal': 'target_reversal'
                },
                'shared_layers': [128, 64],
                'task_specific_layers': {
                    'trend': [64, 32],
                    'volatility': [64, 32],
                    'reversal': [64, 32]
                },
                'use_lstm': True,
                'use_attention': True
            },
            'feature_fusion': {
                'include_price_features': True,
                'include_volume_features': True,
                'include_technical_indicators': True,
                'include_fibonacci_features': True,
                'include_market_regime_features': True,
                'use_feature_selection': True,
                'n_features_to_select': 30
            },
            'market_regime': {
                'method': 'ensemble',
                'lookback_period': 20,
                'regime_change_threshold': 0.6,
                'use_volatility_scaling': True
            },
            'reinforcement': {
                'window_size': 60,
                'batch_size': 32,
                'use_double_dqn': True,
                'epsilon': 0.5
            },
            'integration': {
                'ensemble_weights': {
                    'multi_task': 0.4,
                    'technical': 0.3,
                    'regime': 0.2,
                    'reinforcement': 0.1
                },
                'confidence_threshold': 0.6,
                'use_weighted_voting': True,
                'cache_duration_seconds': 300,  # 5 phút
                'use_parallel_processing': True
            }
        }
        
        # Tạo thư mục chứa config nếu chưa tồn tại
        config_dir = os.path.dirname(self.config_path)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        
        # Tải cấu hình từ file nếu tồn tại
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                try:
                    loaded_config = json.load(f)
                    # Cập nhật cấu hình mặc định với cấu hình đã tải
                    self._deep_update(default_config, loaded_config)
                except Exception as e:
                    logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
        else:
            # Lưu cấu hình mặc định
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
            
            logger.info(f"Đã tạo file cấu hình mới tại {self.config_path}")
        
        return default_config
    
    def _deep_update(self, d: Dict, u: Dict) -> Dict:
        """
        Cập nhật dictionary sâu
        
        Args:
            d: Dictionary cần cập nhật
            u: Dictionary chứa thông tin cập nhật
        
        Returns:
            Dictionary đã cập nhật
        """
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._deep_update(d[k], v)
            else:
                d[k] = v
        return d
    
    def _initialize_components(self) -> None:
        """Khởi tạo các thành phần"""
        # Khởi tạo enhanced market regime detector
        if self.use_enhanced_regime:
            try:
                regime_config = self.config['market_regime']
                self.regime_detector = EnhancedMarketRegimeDetector(
                    method=regime_config['method'],
                    lookback_period=regime_config['lookback_period'],
                    regime_change_threshold=regime_config['regime_change_threshold'],
                    use_volatility_scaling=regime_config['use_volatility_scaling'],
                    models_dir=os.path.join(self.models_dir, 'market_regime')
                )
                # Tải mô hình nếu có
                self.regime_detector.load_models()
                logger.info("Đã khởi tạo Enhanced Market Regime Detector")
            except Exception as e:
                logger.error(f"Lỗi khi khởi tạo Enhanced Market Regime Detector: {str(e)}")
                self.use_enhanced_regime = False
        
        # Khởi tạo feature fusion pipeline
        if self.use_feature_fusion:
            try:
                fusion_config = self.config['feature_fusion']
                self.feature_fusion = FeatureFusionPipeline(
                    include_price_features=fusion_config['include_price_features'],
                    include_volume_features=fusion_config['include_volume_features'],
                    include_technical_indicators=fusion_config['include_technical_indicators'],
                    include_fibonacci_features=fusion_config['include_fibonacci_features'],
                    include_market_regime_features=fusion_config['include_market_regime_features'],
                    use_feature_selection=fusion_config['use_feature_selection'],
                    n_features_to_select=fusion_config['n_features_to_select'],
                    output_path=os.path.join(self.models_dir, 'feature_fusion')
                )
                logger.info("Đã khởi tạo Feature Fusion Pipeline")
            except Exception as e:
                logger.error(f"Lỗi khi khởi tạo Feature Fusion Pipeline: {str(e)}")
                self.use_feature_fusion = False
        
        # Khởi tạo multi-task model
        if self.use_multi_task and self.data_processor is not None:
            try:
                mt_config = self.config['multi_task']
                # MultiTaskModelTrainer sẽ được sử dụng khi training
                logger.info("Đã khởi tạo Multi-Task Model")
            except Exception as e:
                logger.error(f"Lỗi khi khởi tạo Multi-Task Model: {str(e)}")
                self.use_multi_task = False
        
        # Khởi tạo reinforcement trader
        if self.use_reinforcement:
            try:
                rl_config = self.config['reinforcement']
                self.reinforcement_trader = ReinforcementTrader(
                    model_dir=os.path.join(self.models_dir, 'reinforcement'),
                    use_double_dqn=rl_config['use_double_dqn'],
                    window_size=rl_config['window_size'],
                    batch_size=rl_config['batch_size'],
                    epsilon=rl_config['epsilon'],
                    mode='test'  # Chỉ dự đoán, không train
                )
                logger.info("Đã khởi tạo Reinforcement Trader")
            except Exception as e:
                logger.error(f"Lỗi khi khởi tạo Reinforcement Trader: {str(e)}")
                self.use_reinforcement = False
    
    def prepare_data(
        self, 
        symbol: str = None, 
        interval: str = None, 
        limit: int = 1000,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Chuẩn bị dữ liệu cho ML
        
        Args:
            symbol: Mã tiền, None sẽ sử dụng giá trị mặc định
            interval: Khung thời gian, None sẽ sử dụng giá trị mặc định
            limit: Số lượng nến tối đa
            use_cache: Sử dụng cache nếu có
        
        Returns:
            DataFrame chứa dữ liệu đã chuẩn bị
        """
        if symbol is None:
            symbol = self.symbol
        
        if interval is None:
            interval = self.base_interval
        
        # Cache key
        cache_key = f"{symbol}_{interval}"
        
        # Kiểm tra cache
        if use_cache and cache_key in self.cached_data:
            last_update = self.last_update_time.get(cache_key, 0)
            cache_duration = self.config['integration']['cache_duration_seconds']
            current_time = datetime.now().timestamp()
            
            # Nếu cache còn mới, sử dụng cache
            if current_time - last_update < cache_duration:
                logger.debug(f"Sử dụng cache cho {symbol} {interval}")
                return self.cached_data[cache_key]
        
        # Lấy dữ liệu mới
        if self.data_processor is not None and self.api is not None:
            try:
                # Lấy dữ liệu lịch sử
                df = self.data_processor.get_historical_data(symbol, interval, limit)
                
                # Thêm các đặc trưng kỹ thuật nếu chưa có
                df = self.data_processor.add_technical_indicators(df)
                
                # Thêm target cho multi-task learning
                # target_trend: 0=down, 1=sideway, 2=up
                df['target_trend'] = 1  # Mặc định là sideway
                price_change = df['close'].pct_change(24)  # Thay đổi giá sau 24 nến
                df.loc[price_change > 0.01, 'target_trend'] = 2  # Tăng hơn 1%
                df.loc[price_change < -0.01, 'target_trend'] = 0  # Giảm hơn 1%
                
                # target_volatility: Biến động giá tương đối trong 24 nến
                df['target_volatility'] = (
                    df['high'].rolling(24).max() / df['low'].rolling(24).min() - 1
                )
                
                # target_reversal: 1 nếu có đảo chiều trong 12 nến tiếp theo
                price_direction = np.sign(df['close'].diff())
                df['target_reversal'] = ((
                    price_direction != price_direction.shift(-1)
                ) & (
                    price_direction.shift(-1) != price_direction.shift(-2)
                )).astype(int)
                
                # Phát hiện chế độ thị trường nếu chưa có
                if 'market_regime' not in df.columns and self.regime_detector is not None:
                    try:
                        regimes = self.regime_detector.detect_regimes(df)
                        df['market_regime'] = regimes
                    except Exception as e:
                        logger.error(f"Lỗi khi phát hiện chế độ thị trường: {str(e)}")
                
                # Cập nhật cache
                self.cached_data[cache_key] = df
                self.last_update_time[cache_key] = datetime.now().timestamp()
                
                # Lưu dữ liệu hiện tại
                self.current_data = df
                
                return df
            except Exception as e:
                logger.error(f"Lỗi khi chuẩn bị dữ liệu: {str(e)}")
                
                # Trả về cache nếu có
                if cache_key in self.cached_data:
                    logger.warning(f"Sử dụng cache cũ cho {symbol} {interval}")
                    return self.cached_data[cache_key]
                
                raise
        
        raise ValueError("data_processor hoặc api chưa được khởi tạo")
    
    def get_integrated_signals(
        self, 
        df: pd.DataFrame = None, 
        symbol: str = None,
        interval: str = None
    ) -> Dict:
        """
        Lấy tín hiệu tích hợp từ tất cả các thành phần ML
        
        Args:
            df: DataFrame chứa dữ liệu, None sẽ tự động lấy dữ liệu
            symbol: Mã tiền, None sẽ sử dụng giá trị mặc định
            interval: Khung thời gian, None sẽ sử dụng giá trị mặc định
        
        Returns:
            Dict chứa tín hiệu tích hợp
        """
        if df is None:
            df = self.prepare_data(symbol, interval)
        
        # Kết quả
        signals = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol or self.symbol,
            'interval': interval or self.base_interval,
            'close_price': float(df['close'].iloc[-1]),
            'signals': {},
            'regime': None,
            'final_signal': 0,  # 1: mua, -1: bán, 0: không làm gì
            'confidence': 0.0,
            'details': {}
        }
        
        # Lấy tín hiệu từ từng thành phần
        component_signals = {}
        
        # Sử dụng xử lý song song nếu được cấu hình
        if self.config['integration']['use_parallel_processing']:
            component_signals = self._get_signals_parallel(df)
        else:
            component_signals = self._get_signals_sequential(df)
        
        # Cập nhật signals
        signals['signals'] = component_signals
        
        # Lấy chế độ thị trường
        if 'regime' in component_signals and component_signals['regime'] is not None:
            signals['regime'] = component_signals['regime']['current_regime']
        
        # Tính toán tín hiệu cuối cùng dựa trên ensemble
        final_signal, confidence = self._compute_final_signal(component_signals)
        signals['final_signal'] = final_signal
        signals['confidence'] = confidence
        
        # Thêm chi tiết về cách tính toán
        signals['details'] = {
            'ensemble_weights': self.config['integration']['ensemble_weights'],
            'active_components': [
                comp for comp in ['multi_task', 'technical', 'regime', 'reinforcement']
                if comp in component_signals
            ],
            'confidence_threshold': self.config['integration']['confidence_threshold']
        }
        
        # Lưu kết quả hiện tại
        self.current_predictions = signals
        
        return signals
    
    def _get_signals_parallel(self, df: pd.DataFrame) -> Dict:
        """
        Lấy tín hiệu từ các thành phần song song
        
        Args:
            df: DataFrame chứa dữ liệu
        
        Returns:
            Dict chứa tín hiệu từ các thành phần
        """
        component_signals = {}
        
        # Tạo các công việc
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit các công việc
            futures = []
            
            if self.use_multi_task:
                futures.append(executor.submit(self._get_multi_task_signals, df))
            
            if self.use_enhanced_regime:
                futures.append(executor.submit(self._get_regime_signals, df))
            
            # Luôn lấy tín hiệu kỹ thuật
            futures.append(executor.submit(self._get_technical_signals, df))
            
            if self.use_reinforcement and self.reinforcement_trader is not None:
                futures.append(executor.submit(self._get_reinforcement_signals, df))
            
            # Xử lý kết quả
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        component_signals.update(result)
                except Exception as e:
                    logger.error(f"Lỗi khi lấy tín hiệu: {str(e)}")
        
        return component_signals
    
    def _get_signals_sequential(self, df: pd.DataFrame) -> Dict:
        """
        Lấy tín hiệu từ các thành phần tuần tự
        
        Args:
            df: DataFrame chứa dữ liệu
        
        Returns:
            Dict chứa tín hiệu từ các thành phần
        """
        component_signals = {}
        
        # Multi-task learning
        if self.use_multi_task:
            try:
                mt_signals = self._get_multi_task_signals(df)
                if mt_signals:
                    component_signals.update(mt_signals)
            except Exception as e:
                logger.error(f"Lỗi khi lấy tín hiệu multi-task: {str(e)}")
        
        # Enhanced market regime
        if self.use_enhanced_regime:
            try:
                regime_signals = self._get_regime_signals(df)
                if regime_signals:
                    component_signals.update(regime_signals)
            except Exception as e:
                logger.error(f"Lỗi khi lấy tín hiệu chế độ thị trường: {str(e)}")
        
        # Technical indicators (luôn có)
        try:
            tech_signals = self._get_technical_signals(df)
            if tech_signals:
                component_signals.update(tech_signals)
        except Exception as e:
            logger.error(f"Lỗi khi lấy tín hiệu kỹ thuật: {str(e)}")
        
        # Reinforcement learning
        if self.use_reinforcement and self.reinforcement_trader is not None:
            try:
                rl_signals = self._get_reinforcement_signals(df)
                if rl_signals:
                    component_signals.update(rl_signals)
            except Exception as e:
                logger.error(f"Lỗi khi lấy tín hiệu reinforcement: {str(e)}")
        
        return component_signals
    
    def _get_multi_task_signals(self, df: pd.DataFrame) -> Dict:
        """
        Lấy tín hiệu từ multi-task model
        
        Args:
            df: DataFrame chứa dữ liệu
        
        Returns:
            Dict chứa tín hiệu
        """
        mt_config = self.config['multi_task']
        model_path = os.path.join(self.models_dir, 'multi_task', f"{mt_config['model_name']}.h5")
        
        # Kiểm tra mô hình tồn tại
        if not os.path.exists(model_path):
            return None
        
        try:
            # Tải mô hình nếu chưa tải
            if self.multi_task_model is None:
                self.multi_task_model = MultiTaskModel(
                    input_dim=df.shape[1],  # Sẽ được ghi đè khi load
                    shared_layers=mt_config['shared_layers'],
                    task_specific_layers=mt_config['task_specific_layers'],
                    use_lstm=mt_config['use_lstm'],
                    use_attention=mt_config['use_attention'],
                    time_steps=mt_config['time_steps'],
                    models_dir=os.path.join(self.models_dir, 'multi_task'),
                    model_name=mt_config['model_name']
                )
                self.multi_task_model.load()
            
            # Lấy đặc trưng nếu có feature fusion
            if self.use_feature_fusion and self.feature_fusion is not None:
                # Sử dụng feature fusion để lấy đặc trưng
                # Nếu chưa được training, chỉ dùng transform (không fit)
                if not hasattr(self.feature_fusion, 'selected_features') or not self.feature_fusion.selected_features:
                    features = self.feature_fusion.transform(df)
                else:
                    features = self.feature_fusion.fit_transform(df, df['target_trend'].values)
                
                # Lưu đặc trưng hiện tại
                self.current_features = features
                
                # Dự đoán trên đặc trưng
                predictions = self.multi_task_model.predict(features.values)
            else:
                # Dự đoán trực tiếp trên dữ liệu
                predictions = self.multi_task_model.predict(df.values)
            
            # Xử lý dự đoán
            results = {}
            
            if 'trend' in predictions:
                trend_pred = predictions['trend']
                # Lấy predicted class (0=down, 1=sideway, 2=up)
                if len(trend_pred.shape) > 1:
                    trend_class = np.argmax(trend_pred, axis=1)
                else:
                    trend_class = np.round(trend_pred).astype(int)
                
                # Lấy dự đoán cuối cùng
                last_trend = int(trend_class[-1])
                
                # Đặt tín hiệu dựa trên trend
                if last_trend == 2:  # Up
                    signal = 1
                elif last_trend == 0:  # Down
                    signal = -1
                else:  # Sideway
                    signal = 0
                
                # Tính confidence từ probabilites
                confidence = 0.7  # Mặc định
                if len(trend_pred.shape) > 1 and trend_pred.shape[1] > 1:
                    # Lấy xác suất của class được dự đoán
                    confidence = float(trend_pred[-1, last_trend])
                
                results['trend'] = {
                    'signal': signal,
                    'confidence': confidence,
                    'raw_prediction': last_trend,
                    'description': {
                        0: "Xu hướng giảm",
                        1: "Thị trường sideway",
                        2: "Xu hướng tăng"
                    }.get(last_trend, "Không xác định")
                }
            
            if 'volatility' in predictions:
                volatility_pred = predictions['volatility']
                last_volatility = float(volatility_pred[-1])
                
                # Quy đổi volatility thành độ tin cậy
                # Biến động cao -> độ tin cậy thấp
                volatility_confidence = max(0.3, 1.0 - last_volatility)
                
                results['volatility'] = {
                    'value': last_volatility,
                    'confidence': volatility_confidence,
                    'description': (
                        "Biến động cao" if last_volatility > 0.05 else
                        "Biến động trung bình" if last_volatility > 0.02 else
                        "Biến động thấp"
                    )
                }
            
            if 'reversal' in predictions:
                reversal_pred = predictions['reversal']
                last_reversal = float(reversal_pred[-1])
                
                # Đặt tín hiệu dựa trên xác suất đảo chiều
                reversal_signal = 1 if last_reversal > 0.5 else 0
                
                # Tính confidence từ xác suất
                reversal_confidence = max(last_reversal, 1.0 - last_reversal)
                
                results['reversal'] = {
                    'signal': reversal_signal,
                    'confidence': reversal_confidence,
                    'probability': last_reversal,
                    'description': (
                        "Có khả năng đảo chiều cao" if last_reversal > 0.7 else
                        "Có khả năng đảo chiều" if last_reversal > 0.5 else
                        "Khả năng đảo chiều thấp"
                    )
                }
            
            return {'multi_task': results}
        
        except Exception as e:
            logger.error(f"Lỗi khi dự đoán với multi-task model: {str(e)}")
            return None
    
    def _get_regime_signals(self, df: pd.DataFrame) -> Dict:
        """
        Lấy tín hiệu từ market regime detector
        
        Args:
            df: DataFrame chứa dữ liệu
        
        Returns:
            Dict chứa tín hiệu
        """
        if self.regime_detector is None:
            return None
        
        try:
            # Phân tích thị trường
            analysis = self.regime_detector.analyze_current_market(df)
            
            # Lưu chế độ thị trường hiện tại
            self.current_regime = analysis['regime']
            
            # Lấy tham số điều chỉnh theo chế độ thị trường
            params = self.regime_detector.get_regime_adjusted_parameters(
                df.iloc[[-1]], analysis['regime']
            )
            
            # Đặt tín hiệu dựa trên chế độ thị trường
            signal = 0
            
            if analysis['regime'] == 'trending_up':
                signal = 1
            elif analysis['regime'] == 'trending_down':
                signal = -1
            
            # Tin cậy dựa trên confidence và trend strength
            confidence = float(analysis['confidence'])
            if 'key_features' in analysis and 'adx' in analysis['key_features']:
                trend_strength = min(1.0, analysis['key_features']['adx'] / 40.0)
                confidence = (confidence + trend_strength) / 2
            
            return {'regime': {
                'current_regime': analysis['regime'],
                'signal': signal,
                'confidence': confidence,
                'adjusted_params': params,
                'description': analysis['description']
            }}
        
        except Exception as e:
            logger.error(f"Lỗi khi phân tích chế độ thị trường: {str(e)}")
            return None
    
    def _get_technical_signals(self, df: pd.DataFrame) -> Dict:
        """
        Lấy tín hiệu từ chỉ báo kỹ thuật
        
        Args:
            df: DataFrame chứa dữ liệu
        
        Returns:
            Dict chứa tín hiệu
        """
        try:
            results = {}
            
            # Lấy giá trị cuối cùng
            last_row = df.iloc[-1]
            
            # Tín hiệu từ MA
            ma_signal = 0
            if 'sma_20' in df.columns and 'ema_50' in df.columns:
                if last_row['close'] > last_row['sma_20'] and last_row['sma_20'] > last_row['ema_50']:
                    ma_signal = 1
                elif last_row['close'] < last_row['sma_20'] and last_row['sma_20'] < last_row['ema_50']:
                    ma_signal = -1
            
            # Tín hiệu từ MACD
            macd_signal = 0
            if 'macd' in df.columns and 'macd_signal' in df.columns:
                if last_row['macd'] > last_row['macd_signal'] and last_row['macd'] > 0:
                    macd_signal = 1
                elif last_row['macd'] < last_row['macd_signal'] and last_row['macd'] < 0:
                    macd_signal = -1
            
            # Tín hiệu từ RSI
            rsi_signal = 0
            if 'rsi_14' in df.columns:
                if last_row['rsi_14'] < 30:
                    rsi_signal = 1
                elif last_row['rsi_14'] > 70:
                    rsi_signal = -1
            
            # Tín hiệu từ Bollinger Bands
            bb_signal = 0
            if 'bb_lower' in df.columns and 'bb_upper' in df.columns:
                if last_row['close'] < last_row['bb_lower']:
                    bb_signal = 1
                elif last_row['close'] > last_row['bb_upper']:
                    bb_signal = -1
            
            # Tín hiệu từ Fibonacci
            fib_signal = 0
            if 'fib_signal' in df.columns:
                fib_signal = last_row['fib_signal']
            
            # Tín hiệu kết hợp (bình chọn đơn giản)
            signals = [ma_signal, macd_signal, rsi_signal, bb_signal, fib_signal]
            valid_signals = [s for s in signals if s != 0]
            
            if valid_signals:
                # Lấy tín hiệu phổ biến nhất
                buy_count = valid_signals.count(1)
                sell_count = valid_signals.count(-1)
                
                if buy_count > sell_count:
                    final_signal = 1
                elif sell_count > buy_count:
                    final_signal = -1
                else:
                    final_signal = 0
                
                # Tin cậy dựa trên tỷ lệ đồng thuận
                confidence = max(buy_count, sell_count) / len(valid_signals)
            else:
                final_signal = 0
                confidence = 0.0
            
            results = {
                'signal': final_signal,
                'confidence': confidence,
                'indicators': {
                    'ma': ma_signal,
                    'macd': macd_signal,
                    'rsi': rsi_signal,
                    'bollinger': bb_signal,
                    'fibonacci': fib_signal
                },
                'description': (
                    "Các chỉ báo kỹ thuật cho thấy xu hướng tăng" if final_signal == 1 else
                    "Các chỉ báo kỹ thuật cho thấy xu hướng giảm" if final_signal == -1 else
                    "Các chỉ báo kỹ thuật không cho thấy xu hướng rõ ràng"
                )
            }
            
            return {'technical': results}
        
        except Exception as e:
            logger.error(f"Lỗi khi tính tín hiệu kỹ thuật: {str(e)}")
            return None
    
    def _get_reinforcement_signals(self, df: pd.DataFrame) -> Dict:
        """
        Lấy tín hiệu từ reinforcement learning agent
        
        Args:
            df: DataFrame chứa dữ liệu
        
        Returns:
            Dict chứa tín hiệu
        """
        if self.reinforcement_trader is None:
            return None
        
        try:
            # Chuẩn bị môi trường cho reinforcement trader
            self.reinforcement_trader.prepare_environment(df.copy())
            
            # Khởi tạo môi trường
            state = self.reinforcement_trader.env.reset()
            
            # Dự đoán hành động
            action = self.reinforcement_trader.predict(state)
            
            # Mô tả hành động
            action_desc = self.reinforcement_trader.get_action_description(action)
            
            # Lấy tín hiệu
            signal = 0
            if action == 1:  # Mua (Long)
                signal = 1
            elif action == 2:  # Bán (Short)
                signal = -1
            
            # Tin cậy từ Q-values
            confidence = 0.6  # Mặc định
            if self.reinforcement_trader.agent.q_value_history:
                # Tính toán confidence từ q-value cuối cùng
                last_q = self.reinforcement_trader.agent.q_value_history[-1]
                confidence = min(0.9, max(0.4, abs(last_q) / 10.0))
            
            return {'reinforcement': {
                'signal': signal,
                'action': action,
                'confidence': confidence,
                'description': f"Reinforcement Agent đề xuất: {action_desc}"
            }}
        
        except Exception as e:
            logger.error(f"Lỗi khi lấy tín hiệu reinforcement: {str(e)}")
            return None
    
    def _compute_final_signal(
        self, 
        component_signals: Dict
    ) -> Tuple[int, float]:
        """
        Tính toán tín hiệu cuối cùng từ các thành phần
        
        Args:
            component_signals: Dict chứa tín hiệu từ các thành phần
        
        Returns:
            Tuple (final_signal, confidence)
        """
        # Lấy ensemble weights từ cấu hình
        weights = self.config['integration']['ensemble_weights']
        
        # Thu thập tín hiệu và độ tin cậy
        signals = {}
        confidences = {}
        
        if 'multi_task' in component_signals:
            mt_result = component_signals['multi_task']
            if 'trend' in mt_result:
                signals['multi_task'] = mt_result['trend']['signal']
                confidences['multi_task'] = mt_result['trend']['confidence']
        
        if 'technical' in component_signals:
            tech_result = component_signals['technical']
            signals['technical'] = tech_result['signal']
            confidences['technical'] = tech_result['confidence']
        
        if 'regime' in component_signals:
            regime_result = component_signals['regime']
            signals['regime'] = regime_result['signal']
            confidences['regime'] = regime_result['confidence']
        
        if 'reinforcement' in component_signals:
            rl_result = component_signals['reinforcement']
            signals['reinforcement'] = rl_result['signal']
            confidences['reinforcement'] = rl_result['confidence']
        
        # Sử dụng weighted voting
        if self.config['integration']['use_weighted_voting']:
            # Tính weighted votes cho mỗi loại tín hiệu (-1, 0, 1)
            votes = {-1: 0.0, 0: 0.0, 1: 0.0}
            total_weight = 0.0
            
            for component, signal in signals.items():
                if component in weights:
                    component_weight = weights[component]
                    # Áp dụng confidence scaling nếu có
                    if component in confidences:
                        confidence = confidences.get(component, 0.5)
                        component_weight *= confidence
                    
                    votes[signal] += component_weight
                    total_weight += component_weight
            
            # Chuẩn hóa votes
            if total_weight > 0:
                for signal in votes:
                    votes[signal] /= total_weight
            
            # Lấy tín hiệu có vote cao nhất
            max_vote = max(votes.values())
            if max_vote > 0:
                max_signals = [s for s, v in votes.items() if v == max_vote]
                final_signal = max_signals[0]
                
                # Tin cậy dựa trên độ mạnh của vote
                confidence = max_vote
            else:
                final_signal = 0
                confidence = 0.5
        else:
            # Simple majority voting
            signal_counts = {}
            for component, signal in signals.items():
                signal_counts[signal] = signal_counts.get(signal, 0) + 1
            
            # Lấy tín hiệu có count cao nhất
            max_count = max(signal_counts.values()) if signal_counts else 0
            max_signals = [s for s, c in signal_counts.items() if c == max_count]
            final_signal = max_signals[0] if max_signals else 0
            
            # Tin cậy dựa trên tỷ lệ đồng thuận
            confidence = max_count / len(signals) if signals else 0.5
        
        # Áp dụng confidence threshold
        threshold = self.config['integration']['confidence_threshold']
        if confidence < threshold:
            # Nếu confidence thấp, không đưa ra tín hiệu
            final_signal = 0
        
        return final_signal, confidence
    
    def train_multi_task_model(
        self,
        df: pd.DataFrame = None,
        symbol: str = None,
        interval: str = None,
        feature_columns: List[str] = None,
        model_params: Dict = None,
        training_params: Dict = None,
        save_model: bool = True
    ) -> Dict:
        """
        Huấn luyện multi-task model
        
        Args:
            df: DataFrame chứa dữ liệu, None sẽ tự động lấy dữ liệu
            symbol: Mã tiền, None sẽ sử dụng giá trị mặc định
            interval: Khung thời gian, None sẽ sử dụng giá trị mặc định
            feature_columns: Danh sách cột đặc trưng, None sẽ sử dụng tất cả
            model_params: Thông số mô hình, None sẽ sử dụng cấu hình mặc định
            training_params: Thông số huấn luyện, None sẽ sử dụng cấu hình mặc định
            save_model: Lưu mô hình nếu True
        
        Returns:
            Dict chứa kết quả huấn luyện
        """
        if not self.use_multi_task:
            raise ValueError("Multi-task learning không được kích hoạt")
        
        if self.data_processor is None:
            raise ValueError("data_processor chưa được khởi tạo")
        
        if df is None:
            df = self.prepare_data(symbol, interval)
        
        # Multi-task model trainer
        mt_config = self.config['multi_task']
        trainer = MultiTaskModelTrainer(
            data_processor=self.data_processor,
            model_name=mt_config['model_name'],
            models_dir=os.path.join(self.models_dir, 'multi_task'),
            target_columns=mt_config['target_columns'],
            time_steps=mt_config['time_steps'],
            test_size=0.2,
            n_splits=5
        )
        
        # Default feature_columns nếu không được cung cấp
        if feature_columns is None:
            feature_columns = [
                'open', 'high', 'low', 'close', 'volume',
                'rsi_14', 'macd', 'macd_signal', 'macd_hist',
                'sma_20', 'ema_12', 'ema_26',
                'bb_upper', 'bb_middle', 'bb_lower', 'bb_width'
            ]
            # Thêm các cột khác nếu có
            for col in df.columns:
                if col.startswith(('rsi_', 'ema_', 'sma_', 'atr_', 'fib_')) and col not in feature_columns:
                    feature_columns.append(col)
        
        # Thông số mô hình mặc định nếu không được cung cấp
        if model_params is None:
            model_params = {
                'shared_layers': mt_config['shared_layers'],
                'task_specific_layers': mt_config['task_specific_layers'],
                'dropout_rate': 0.3,
                'l1_reg': 0.001,
                'l2_reg': 0.001,
                'learning_rate': 0.001,
                'use_lstm': mt_config['use_lstm'],
                'use_attention': mt_config['use_attention'],
                'time_steps': mt_config['time_steps']
            }
        
        # Thông số huấn luyện mặc định nếu không được cung cấp
        if training_params is None:
            training_params = {
                'validation_split': 0.2,
                'batch_size': 32,
                'epochs': 100,
                'patience': 10,
                'verbose': 1
            }
        
        # Huấn luyện mô hình
        model, metrics = trainer.train_model(
            df=df,
            feature_columns=feature_columns,
            model_params=model_params,
            training_params=training_params,
            add_technical_indicators=True,
            add_market_regime=True,
            use_time_series_cv=True,
            save_best_model=save_model,
            plot_history=True
        )
        
        # Cập nhật multi_task_model
        self.multi_task_model = model
        
        return metrics
    
    def train_reinforcement_agent(
        self,
        df: pd.DataFrame = None,
        symbol: str = None,
        interval: str = None,
        episodes: int = 100,
        batch_size: int = 32,
        save_model: bool = True
    ) -> Dict:
        """
        Huấn luyện reinforcement agent
        
        Args:
            df: DataFrame chứa dữ liệu, None sẽ tự động lấy dữ liệu
            symbol: Mã tiền, None sẽ sử dụng giá trị mặc định
            interval: Khung thời gian, None sẽ sử dụng giá trị mặc định
            episodes: Số lượng episodes
            batch_size: Kích thước batch
            save_model: Lưu mô hình nếu True
        
        Returns:
            Dict chứa kết quả huấn luyện
        """
        if not self.use_reinforcement:
            raise ValueError("Reinforcement learning không được kích hoạt")
        
        if df is None:
            df = self.prepare_data(symbol, interval)
        
        # Cấu hình reinforcement
        rl_config = self.config['reinforcement']
        
        # Khởi tạo trader nếu chưa có
        if self.reinforcement_trader is None:
            self.reinforcement_trader = ReinforcementTrader(
                model_dir=os.path.join(self.models_dir, 'reinforcement'),
                use_double_dqn=rl_config['use_double_dqn'],
                window_size=rl_config['window_size'],
                batch_size=rl_config['batch_size'],
                epsilon=rl_config['epsilon'],
                mode='train'
            )
        
        # Chuẩn bị môi trường
        self.reinforcement_trader.prepare_environment(
            df=df,
            initial_balance=10000.0,
            transaction_fee_percent=0.04,
            reward_scaling=0.01,
            max_position_size=1.0,
            use_risk_adjustment=True
        )
        
        # Huấn luyện agent
        results = self.reinforcement_trader.train(
            episodes=episodes,
            batch_size=batch_size,
            print_interval=max(1, episodes // 10),
            save_best=save_model,
            plot_results=True
        )
        
        return results
    
    def train_feature_fusion(
        self,
        df: pd.DataFrame = None,
        symbol: str = None,
        interval: str = None,
        target_column: str = 'target_trend'
    ) -> Any:
        """
        Huấn luyện feature fusion pipeline
        
        Args:
            df: DataFrame chứa dữ liệu, None sẽ tự động lấy dữ liệu
            symbol: Mã tiền, None sẽ sử dụng giá trị mặc định
            interval: Khung thời gian, None sẽ sử dụng giá trị mặc định
            target_column: Tên cột mục tiêu
        
        Returns:
            Object chứa đặc trưng đã fusion
        """
        if not self.use_feature_fusion:
            raise ValueError("Feature fusion không được kích hoạt")
        
        if df is None:
            df = self.prepare_data(symbol, interval)
        
        if target_column not in df.columns:
            raise ValueError(f"Không tìm thấy cột mục tiêu '{target_column}' trong dữ liệu")
        
        # Fit và transform
        fused_features = self.feature_fusion.fit_transform(
            df, 
            y=df[target_column].values
        )
        
        # Lưu pipeline
        self.feature_fusion.save()
        
        # Lưu đặc trưng hiện tại
        self.current_features = fused_features
        
        return fused_features
    
    def test_integrated_system(
        self,
        df: pd.DataFrame = None,
        symbol: str = None,
        interval: str = None,
        lookback: int = 100,
        plot_results: bool = True
    ) -> Dict:
        """
        Kiểm thử hệ thống tích hợp
        
        Args:
            df: DataFrame chứa dữ liệu, None sẽ tự động lấy dữ liệu
            symbol: Mã tiền, None sẽ sử dụng giá trị mặc định
            interval: Khung thời gian, None sẽ sử dụng giá trị mặc định
            lookback: Số lượng nến để kiểm thử
            plot_results: Vẽ biểu đồ kết quả nếu True
        
        Returns:
            Dict chứa kết quả kiểm thử
        """
        if df is None:
            df = self.prepare_data(symbol, interval)
        
        # Chỉ lấy n nến cuối cùng
        if lookback and lookback < len(df):
            test_df = df.iloc[-lookback:]
        else:
            test_df = df
        
        # Kết quả
        results = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol or self.symbol,
            'interval': interval or self.base_interval,
            'lookback': lookback,
            'signals': [],
            'trades': [],
            'metrics': {}
        }
        
        # Mô phỏng giao dịch
        position = 0
        entry_price = 0
        profits = []
        
        for i in range(len(test_df)):
            # Lấy dữ liệu tới thời điểm i
            current_df = test_df.iloc[:i+1]
            
            # Lấy tín hiệu
            signals = self.get_integrated_signals(current_df)
            
            # Lấy tín hiệu cuối cùng
            signal = signals['final_signal']
            confidence = signals['confidence']
            
            # Giá hiện tại
            current_price = float(current_df['close'].iloc[-1])
            
            # Xử lý giao dịch
            trade = None
            
            if position == 0 and signal != 0:
                # Mở vị thế
                position = signal
                entry_price = current_price
                
                trade = {
                    'timestamp': current_df.index[-1],
                    'action': 'buy' if signal == 1 else 'sell',
                    'price': current_price,
                    'confidence': confidence
                }
            elif position != 0 and (signal == 0 or signal == -position):
                # Đóng vị thế
                profit_pct = position * (current_price - entry_price) / entry_price * 100
                profits.append(profit_pct)
                
                trade = {
                    'timestamp': current_df.index[-1],
                    'action': 'sell' if position == 1 else 'buy',
                    'price': current_price,
                    'profit_pct': profit_pct,
                    'confidence': confidence
                }
                
                position = 0
                entry_price = 0
            
            # Lưu tín hiệu
            signals['index'] = i
            signals['price'] = current_price
            results['signals'].append(signals)
            
            # Lưu giao dịch
            if trade:
                results['trades'].append(trade)
        
        # Tính toán metrics
        if profits:
            results['metrics'] = {
                'total_trades': len(profits),
                'win_rate': (np.array(profits) > 0).sum() / len(profits) * 100,
                'avg_profit': np.mean(profits),
                'total_profit': np.sum(profits),
                'max_profit': np.max(profits),
                'max_loss': np.min(profits),
                'profit_factor': (
                    np.sum(np.array(profits)[np.array(profits) > 0]) /
                    abs(np.sum(np.array(profits)[np.array(profits) < 0]))
                    if np.any(np.array(profits) < 0) else float('inf')
                )
            }
        else:
            results['metrics'] = {
                'total_trades': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'total_profit': 0,
                'max_profit': 0,
                'max_loss': 0,
                'profit_factor': 0
            }
        
        # Vẽ biểu đồ kết quả
        if plot_results and results['trades']:
            self._plot_test_results(results, test_df)
        
        return results
    
    def _plot_test_results(self, results: Dict, df: pd.DataFrame) -> None:
        """
        Vẽ biểu đồ kết quả kiểm thử
        
        Args:
            results: Dict chứa kết quả kiểm thử
            df: DataFrame chứa dữ liệu
        """
        import matplotlib.pyplot as plt
        from matplotlib.dates import DateFormatter
        
        # Tạo hình
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)
        
        # Vẽ giá
        ax1.plot(df.index, df['close'], label='Close Price')
        
        # Vẽ các điểm mua/bán
        buy_points = [t for t in results['trades'] if t['action'] == 'buy']
        sell_points = [t for t in results['trades'] if t['action'] == 'sell']
        
        if buy_points:
            buy_xs = [t['timestamp'] for t in buy_points]
            buy_ys = [t['price'] for t in buy_points]
            ax1.scatter(buy_xs, buy_ys, color='green', marker='^', s=100, label='Buy')
        
        if sell_points:
            sell_xs = [t['timestamp'] for t in sell_points]
            sell_ys = [t['price'] for t in sell_points]
            ax1.scatter(sell_xs, sell_ys, color='red', marker='v', s=100, label='Sell')
        
        # Vẽ chế độ thị trường
        regime_colors = {
            'trending_up': 'green',
            'trending_down': 'red',
            'ranging': 'blue',
            'volatile': 'orange',
            'neutral': 'gray'
        }
        
        if 'signals' in results and results['signals']:
            # Lấy regime từ mỗi signal
            regimes = []
            for signal in results['signals']:
                if 'regime' in signal:
                    regimes.append((signal['index'], signal['regime']))
            
            if regimes:
                # Tạo spans cho mỗi chế độ
                last_regime = None
                start_idx = 0
                
                for idx, regime in regimes:
                    if regime != last_regime and last_regime is not None:
                        # Kết thúc span trước đó
                        color = regime_colors.get(last_regime, 'gray')
                        ax1.axvspan(
                            df.index[start_idx], df.index[idx],
                            alpha=0.2, color=color
                        )
                        start_idx = idx
                    
                    last_regime = regime
                
                # Span cuối cùng
                if last_regime:
                    color = regime_colors.get(last_regime, 'gray')
                    ax1.axvspan(
                        df.index[start_idx], df.index[-1],
                        alpha=0.2, color=color
                    )
        
        # Labels
        ax1.set_title(f"Integrated ML System Test Results - {results['symbol']} {results['interval']}")
        ax1.set_ylabel('Price')
        ax1.legend()
        ax1.grid(True)
        
        # Vẽ lợi nhuận tích lũy
        if 'trades' in results and results['trades']:
            profits = [t.get('profit_pct', 0) for t in results['trades'] if 'profit_pct' in t]
            
            if profits:
                cum_profits = np.cumsum(profits)
                trade_idxs = range(len(profits))
                
                ax2.plot(trade_idxs, cum_profits, 'b-', linewidth=2)
                ax2.fill_between(trade_idxs, 0, cum_profits, where=cum_profits >= 0, color='green', alpha=0.3)
                ax2.fill_between(trade_idxs, 0, cum_profits, where=cum_profits < 0, color='red', alpha=0.3)
                
                ax2.set_title('Cumulative Profit (%)')
                ax2.set_ylabel('Profit %')
                ax2.set_xlabel('Trade')
                ax2.grid(True)
        
        # Thêm thông tin metrics
        if 'metrics' in results:
            metrics = results['metrics']
            metrics_text = (
                f"Total Trades: {metrics['total_trades']}\n"
                f"Win Rate: {metrics['win_rate']:.2f}%\n"
                f"Avg Profit: {metrics['avg_profit']:.2f}%\n"
                f"Total Profit: {metrics['total_profit']:.2f}%\n"
                f"Profit Factor: {metrics['profit_factor']:.2f}"
            )
            
            ax2.text(
                0.02, 0.95, metrics_text,
                transform=ax2.transAxes,
                verticalalignment='top',
                bbox={'boxstyle': 'round', 'facecolor': 'wheat', 'alpha': 0.5}
            )
        
        # Format dates
        date_formatter = DateFormatter('%Y-%m-%d')
        ax1.xaxis.set_major_formatter(date_formatter)
        fig.autofmt_xdate()
        
        plt.tight_layout()
        
        # Lưu biểu đồ
        plot_path = os.path.join(
            self.models_dir, 
            f"integrated_test_{results['symbol']}_{results['interval']}.png"
        )
        plt.savefig(plot_path, dpi=300)
        plt.close()
        
        logger.info(f"Đã lưu biểu đồ kết quả kiểm thử tại: {plot_path}")
    
    def get_best_parameters(
        self, 
        symbol: str = None,
        interval: str = None,
        regime: str = None
    ) -> Dict:
        """
        Lấy thông số tối ưu dựa trên chế độ thị trường
        
        Args:
            symbol: Mã tiền, None sẽ sử dụng giá trị mặc định
            interval: Khung thời gian, None sẽ sử dụng giá trị mặc định
            regime: Chế độ thị trường, None sẽ tự động phát hiện
        
        Returns:
            Dict chứa thông số tối ưu
        """
        if symbol is None:
            symbol = self.symbol
        
        if interval is None:
            interval = self.base_interval
        
        # Lấy dữ liệu mới nhất
        df = self.prepare_data(symbol, interval)
        
        # Phát hiện chế độ thị trường nếu không được cung cấp
        if regime is None:
            if self.use_enhanced_regime and self.regime_detector is not None:
                try:
                    analysis = self.regime_detector.analyze_current_market(df)
                    regime = analysis['regime']
                except Exception as e:
                    logger.error(f"Lỗi khi phát hiện chế độ thị trường: {str(e)}")
                    regime = 'neutral'
            else:
                regime = 'neutral'
        
        # Lấy tham số dựa trên chế độ thị trường
        if self.use_enhanced_regime and self.regime_detector is not None:
            params = self.regime_detector.get_regime_adjusted_parameters(
                df.iloc[[-1]], regime
            )
        else:
            # Tham số mặc định
            params = {
                'sl_atr_multiplier': 2.0,
                'tp_atr_multiplier': 3.0,
                'position_size': 1.0,
                'entry_threshold': 0.7,
                'exit_threshold': 0.7
            }
        
        # Thêm thông tin về chế độ thị trường và tín hiệu
        signals = self.get_integrated_signals(df, symbol, interval)
        
        params['market_regime'] = regime
        params['signal'] = signals['final_signal']
        params['confidence'] = signals['confidence']
        
        return params
    
    def save_state(self) -> None:
        """Lưu trạng thái hiện tại"""
        # Lưu cấu hình
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)
        
        # Lưu mô hình market regime
        if self.use_enhanced_regime and self.regime_detector is not None:
            self.regime_detector.save_models()
        
        # Lưu feature fusion pipeline
        if self.use_feature_fusion and self.feature_fusion is not None:
            self.feature_fusion.save()
        
        logger.info("Đã lưu trạng thái ML Integration Manager")
    
    def load_state(self) -> None:
        """Tải trạng thái"""
        # Tải cấu hình
        self.config = self._load_config()
        
        # Khởi tạo lại các thành phần
        self._initialize_components()
        
        logger.info("Đã tải trạng thái ML Integration Manager")

# Hàm demo
def test_ml_integration():
    """
    Demo sử dụng ML Integration Manager
    """
    from data_processor import DataProcessor
    from binance_api import BinanceAPI
    
    # Khởi tạo các thành phần cần thiết
    api = BinanceAPI()
    data_processor = DataProcessor(api=api)
    
    # Khởi tạo MLIntegrationManager
    manager = MLIntegrationManager(
        api=api,
        data_processor=data_processor,
        symbol='BTCUSDT',
        base_interval='1h',
        use_multi_task=True,
        use_feature_fusion=True,
        use_enhanced_regime=True,
        use_reinforcement=True
    )
    
    # Chuẩn bị dữ liệu
    df = manager.prepare_data(limit=1000)
    print(f"Đã tải {len(df)} nến cho BTCUSDT 1h")
    
    # Lấy tín hiệu tích hợp
    signals = manager.get_integrated_signals(df)
    print(f"Tín hiệu tích hợp: {signals['final_signal']} (confidence: {signals['confidence']:.2f})")
    
    # Kiểm thử hệ thống tích hợp
    results = manager.test_integrated_system(df, lookback=200)
    print(f"Kết quả kiểm thử: {results['metrics']}")
    
    return manager, signals, results

if __name__ == "__main__":
    # Demo và test
    manager, signals, results = test_ml_integration()