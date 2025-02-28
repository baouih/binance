"""
Factory pattern cho việc tạo các chiến lược giao dịch khác nhau
"""

import os
import logging
from typing import Dict, List, Union, Optional

# Định nghĩa logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('strategy_factory')

# Các chiến lược sẽ được import động
AVAILABLE_STRATEGIES = {
    "rsi": {
        "class": "RSIStrategy",
        "module": "app.strategy",
        "label": "RSI Strategy",
        "description": "Chiến lược RSI cơ bản"
    },
    "macd": {
        "class": "MACDStrategy",
        "module": "app.strategy",
        "label": "MACD Strategy",
        "description": "Chiến lược MACD cơ bản"
    },
    "ema_cross": {
        "class": "EMACrossStrategy",
        "module": "app.strategy",
        "label": "EMA Crossover Strategy",
        "description": "Chiến lược EMA Crossover cơ bản"
    },
    "bbands": {
        "class": "BBandsStrategy",
        "module": "app.strategy",
        "label": "Bollinger Bands Strategy",
        "description": "Chiến lược Bollinger Bands cơ bản"
    },
    "ml": {
        "class": "MLStrategy",
        "module": "app.strategy",
        "label": "ML Strategy",
        "description": "Chiến lược học máy cơ bản"
    },
    "combined": {
        "class": "CombinedStrategy",
        "module": "app.strategy",
        "label": "Combined Strategy",
        "description": "Chiến lược kết hợp nhiều chiến lược khác nhau"
    },
    "auto": {
        "class": "AutoStrategy",
        "module": "app.strategy",
        "label": "Auto Strategy",
        "description": "Chiến lược tự động thích ứng với chế độ thị trường"
    },
    "advanced_ml": {
        "class": "AdvancedMLStrategy",
        "module": "app.advanced_ml_strategy",
        "label": "Advanced ML Strategy",
        "description": "Chiến lược học máy nâng cao với nhiều mô hình và chế độ thị trường"
    },
    "regime_ml": {
        "class": "AutoStrategy",  # Sử dụng AutoStrategy nhưng với tham số use_ml=True
        "module": "app.strategy",
        "label": "Regime ML Strategy",
        "description": "Chiến lược học máy thích ứng với chế độ thị trường"
    }
}

class StrategyFactory:
    """Factory class để tạo các đối tượng chiến lược"""
    
    @staticmethod
    def create_strategy(strategy_type: str, config: Dict = None, model_path: str = None, **kwargs):
        """
        Tạo đối tượng chiến lược dựa trên loại chiến lược
        
        Args:
            strategy_type (str): Loại chiến lược cần tạo
            config (Dict): Cấu hình cho chiến lược (tùy chọn)
            model_path (str): Đường dẫn đến mô hình ML (tùy chọn)
            **kwargs: Các tham số khác cho chiến lược
            
        Returns:
            Strategy: Đối tượng chiến lược đã tạo
        """
        strategy_type = strategy_type.lower()
        
        if strategy_type not in AVAILABLE_STRATEGIES:
            logger.error(f"Loại chiến lược {strategy_type} không tồn tại")
            available = ", ".join(AVAILABLE_STRATEGIES.keys())
            logger.info(f"Các chiến lược có sẵn: {available}")
            logger.info("Sử dụng chiến lược mặc định: combined")
            strategy_type = "combined"
        
        strategy_info = AVAILABLE_STRATEGIES[strategy_type]
        class_name = strategy_info["class"]
        module_name = strategy_info["module"]
        
        try:
            # Import động module chứa lớp chiến lược
            module = __import__(module_name, fromlist=[class_name])
            strategy_class = getattr(module, class_name)
            
            # Trường hợp đặc biệt cho các chiến lược nhất định
            if strategy_type == "advanced_ml":
                # Import động module advanced_ml_optimizer
                try:
                    from app.advanced_ml_optimizer import AdvancedMLOptimizer
                    from app.market_regime_detector import MarketRegimeDetector
                    
                    ml_optimizer = kwargs.get('ml_optimizer')
                    if ml_optimizer is None:
                        ml_optimizer = AdvancedMLOptimizer()
                    
                    market_regime_detector = kwargs.get('market_regime_detector')
                    if market_regime_detector is None:
                        market_regime_detector = MarketRegimeDetector()
                    
                    probability_threshold = kwargs.get('probability_threshold', 0.65)
                    
                    # Tạo chiến lược với tham số cụ thể
                    strategy = strategy_class(
                        ml_optimizer=ml_optimizer,
                        market_regime_detector=market_regime_detector,
                        model_path=model_path,
                        probability_threshold=probability_threshold
                    )
                except Exception as e:
                    logger.error(f"Lỗi khi tạo AdvancedMLStrategy: {str(e)}")
                    # Fallback to CombinedStrategy
                    from app.strategy import CombinedStrategy
                    strategy = CombinedStrategy([])
            
            elif strategy_type == "regime_ml":
                # Sử dụng AutoStrategy với use_ml=True
                from app.market_regime_detector import MarketRegimeDetector
                from app.ml_optimizer import MLOptimizer
                
                market_regime_detector = kwargs.get('market_regime_detector')
                if market_regime_detector is None:
                    market_regime_detector = MarketRegimeDetector()
                
                ml_optimizer = kwargs.get('ml_optimizer')
                if ml_optimizer is None:
                    ml_optimizer = MLOptimizer()
                
                # Tạo AutoStrategy với tham số ML
                strategy = strategy_class(
                    market_regime_detector=market_regime_detector,
                    ml_optimizer=ml_optimizer
                )
            
            elif strategy_type == "combined":
                # Tạo các chiến lược con cho CombinedStrategy
                from app.strategy import RSIStrategy, MACDStrategy, EMACrossStrategy, BBandsStrategy, MLStrategy
                
                strategies = []
                # Tạo RSI Strategy
                strategies.append(RSIStrategy())
                # Tạo MACD Strategy
                strategies.append(MACDStrategy())
                # Tạo EMA Cross Strategy
                strategies.append(EMACrossStrategy())
                # Tạo Bollinger Bands Strategy
                strategies.append(BBandsStrategy())
                # Tạo ML Strategy nếu use_ml=True
                if kwargs.get('use_ml', True):
                    from app.ml_optimizer import MLOptimizer
                    ml_optimizer = kwargs.get('ml_optimizer')
                    if ml_optimizer is None:
                        ml_optimizer = MLOptimizer()
                    strategies.append(MLStrategy(ml_optimizer=ml_optimizer))
                
                # Tạo CombinedStrategy với các chiến lược con
                weights = kwargs.get('weights')
                strategy = strategy_class(strategies=strategies, weights=weights)
            
            elif strategy_type == "auto":
                # Tạo AutoStrategy
                from app.market_regime_detector import MarketRegimeDetector
                
                market_regime_detector = kwargs.get('market_regime_detector')
                if market_regime_detector is None:
                    market_regime_detector = MarketRegimeDetector()
                
                ml_optimizer = None
                if kwargs.get('use_ml', False):
                    from app.ml_optimizer import MLOptimizer
                    ml_optimizer = kwargs.get('ml_optimizer')
                    if ml_optimizer is None:
                        ml_optimizer = MLOptimizer()
                
                # Tạo AutoStrategy
                strategy = strategy_class(
                    market_regime_detector=market_regime_detector,
                    ml_optimizer=ml_optimizer
                )
            
            elif strategy_type == "ml":
                # Tạo MLStrategy
                from app.ml_optimizer import MLOptimizer
                
                ml_optimizer = kwargs.get('ml_optimizer')
                if ml_optimizer is None:
                    ml_optimizer = MLOptimizer()
                
                probability_threshold = kwargs.get('probability_threshold', 0.65)
                
                # Tạo MLStrategy
                strategy = strategy_class(
                    ml_optimizer=ml_optimizer,
                    probability_threshold=probability_threshold
                )
            
            else:
                # Áp dụng cấu hình hoặc tham số tùy chọn nếu có
                if config and strategy_type in config:
                    # Tạo đối tượng chiến lược với các tham số từ config
                    strategy_params = config[strategy_type]
                    strategy = strategy_class(**strategy_params)
                else:
                    # Tạo đối tượng chiến lược với tham số mặc định
                    strategy = strategy_class(**kwargs)
            
            logger.info(f"Đã tạo chiến lược {strategy_type} thành công")
            return strategy
            
        except (ImportError, AttributeError) as e:
            logger.error(f"Lỗi khi tạo chiến lược {strategy_type}: {str(e)}")
            
            # Fallback to CombinedStrategy
            try:
                from app.strategy import CombinedStrategy
                logger.info("Sử dụng chiến lược mặc định CombinedStrategy")
                return CombinedStrategy([])
            except Exception as e2:
                logger.error(f"Lỗi khi tạo chiến lược mặc định: {str(e2)}")
                return None
    
    @staticmethod
    def get_available_strategies():
        """
        Lấy danh sách các chiến lược có sẵn
        
        Returns:
            List[Dict]: Danh sách các chiến lược có sẵn
        """
        result = []
        
        for strategy_id, info in AVAILABLE_STRATEGIES.items():
            result.append({
                "id": strategy_id,
                "label": info["label"],
                "description": info["description"]
            })
        
        return result