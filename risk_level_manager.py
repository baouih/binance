import os
import json
import logging
from typing import Dict, Any, Optional
import copy

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RiskLevelManager:
    """
    Manages risk level configurations for the trading bot.
    Supports changing between different predefined risk profiles.
    """
    def __init__(self):
        self.base_config_path = "risk_configs/advanced_risk_config.json"
        self.risk_configs = {
            "10": "risk_configs/risk_level_10.json",
            "15": "risk_configs/risk_level_15.json", 
            "20": "risk_configs/risk_level_20.json",
            "30": "risk_configs/risk_level_30.json"
        }
        self.current_risk_level = "10"  # Default to lowest risk
        self.base_config = self._load_base_config()
        
        # Create risk configs directory if it doesn't exist
        os.makedirs("risk_configs", exist_ok=True)
        
        # Create default risk configurations if they don't exist
        self._create_default_risk_configs()
        
    def _load_base_config(self) -> Dict[str, Any]:
        """Load the base configuration file or create it if it doesn't exist"""
        if not os.path.exists(self.base_config_path):
            # Create default base config
            default_config = {
                "max_open_positions": 3,
                "position_size_percent": 2.0,
                "stop_loss_percent": 1.0,
                "take_profit_percent": 3.0,
                "trailing_stop_percent": 0.5,
                "max_daily_trades": 10,
                "max_daily_drawdown_percent": 5.0,
                "use_adaptive_position_sizing": True,
                "use_dynamic_stop_loss": True,
                "leverage": 1
            }
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.base_config_path), exist_ok=True)
            
            with open(self.base_config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            
            return default_config
        
        try:
            with open(self.base_config_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading base config: {e}")
            return {}
            
    def _create_default_risk_configs(self) -> None:
        """Create the default risk configuration files if they don't exist"""
        # Risk level 10% - Conservative
        risk_10_config = {
            "max_open_positions": 2,
            "position_size_percent": 1.0,
            "stop_loss_percent": 1.0,
            "take_profit_percent": 2.0,
            "trailing_stop_percent": 0.3,
            "max_daily_trades": 5,
            "max_daily_drawdown_percent": 3.0,
            "use_adaptive_position_sizing": True,
            "use_dynamic_stop_loss": True,
            "leverage": 1,
            "risk_multipliers": {
                "stop_loss_multiplier": 1.0,
                "take_profit_multiplier": 1.0,
                "trailing_stop_callback": 0.1,
                "position_size_multiplier": 1.0
            }
        }
        
        # Risk level 15% - Moderate
        risk_15_config = {
            "max_open_positions": 3,
            "position_size_percent": 2.0,
            "stop_loss_percent": 1.5,
            "take_profit_percent": 3.0,
            "trailing_stop_percent": 0.5,
            "max_daily_trades": 8,
            "max_daily_drawdown_percent": 5.0,
            "use_adaptive_position_sizing": True,
            "use_dynamic_stop_loss": True,
            "leverage": 2,
            "risk_multipliers": {
                "stop_loss_multiplier": 1.5,
                "take_profit_multiplier": 1.5,
                "trailing_stop_callback": 0.15,
                "position_size_multiplier": 1.5
            }
        }
        
        # Risk level 20% - Aggressive
        risk_20_config = {
            "max_open_positions": 4,
            "position_size_percent": 3.0,
            "stop_loss_percent": 2.0,
            "take_profit_percent": 4.0,
            "trailing_stop_percent": 0.7,
            "max_daily_trades": 12,
            "max_daily_drawdown_percent": 7.0,
            "use_adaptive_position_sizing": True,
            "use_dynamic_stop_loss": True,
            "leverage": 3,
            "risk_multipliers": {
                "stop_loss_multiplier": 2.0,
                "take_profit_multiplier": 2.0,
                "trailing_stop_callback": 0.2,
                "position_size_multiplier": 2.0
            }
        }
        
        # Risk level 30% - Very Aggressive
        risk_30_config = {
            "max_open_positions": 5,
            "position_size_percent": 5.0,
            "stop_loss_percent": 3.0,
            "take_profit_percent": 6.0,
            "trailing_stop_percent": 1.0,
            "max_daily_trades": 15,
            "max_daily_drawdown_percent": 10.0,
            "use_adaptive_position_sizing": True,
            "use_dynamic_stop_loss": True,
            "leverage": 5,
            "risk_multipliers": {
                "stop_loss_multiplier": 3.0,
                "take_profit_multiplier": 3.0,
                "trailing_stop_callback": 0.3,
                "position_size_multiplier": 3.0
            }
        }
        
        risk_configs = {
            "10": risk_10_config,
            "15": risk_15_config,
            "20": risk_20_config,
            "30": risk_30_config
        }
        
        for risk_level, config in risk_configs.items():
            file_path = self.risk_configs[risk_level]
            if not os.path.exists(file_path):
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w') as f:
                    json.dump(config, f, indent=4)
                logger.info(f"Created default risk config for level {risk_level}%")
                
    def get_current_risk_level(self) -> str:
        """Get the current risk level"""
        return self.current_risk_level
    
    def get_risk_config(self, risk_level: Optional[str] = None) -> Dict[str, Any]:
        """Get the configuration for a specific risk level or the current risk level"""
        if risk_level is None:
            risk_level = self.current_risk_level
            
        if risk_level not in self.risk_configs:
            logger.error(f"Invalid risk level: {risk_level}. Using default level 10%.")
            risk_level = "10"
            
        try:
            with open(self.risk_configs[risk_level], 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading risk config for level {risk_level}: {e}")
            return {}
    
    def apply_risk_config(self, risk_level: str) -> bool:
        """Apply a specific risk level configuration to the system"""
        if risk_level not in self.risk_configs:
            logger.error(f"Invalid risk level: {risk_level}. Valid levels are: {list(self.risk_configs.keys())}")
            return False
            
        try:
            # Load the risk configuration
            risk_config = self.get_risk_config(risk_level)
            if not risk_config:
                return False
                
            # Update account_config.json with the new risk parameters
            self._update_account_config(risk_config)
            
            # Set the current risk level
            self.current_risk_level = risk_level
            
            logger.info(f"Successfully applied risk level {risk_level}%")
            return True
            
        except Exception as e:
            logger.error(f"Error applying risk level {risk_level}: {str(e)}")
            return False
    
    def _update_account_config(self, risk_config: Dict[str, Any]) -> None:
        """Update the account configuration with the new risk parameters"""
        account_config_path = "account_config.json"
        
        try:
            # Load existing account config
            if os.path.exists(account_config_path):
                with open(account_config_path, 'r') as f:
                    account_config = json.load(f)
            else:
                account_config = {}
                
            # Update account config with risk parameters
            if "risk_parameters" not in account_config:
                account_config["risk_parameters"] = {}
                
            # Copy risk config values to account config
            for key, value in risk_config.items():
                if key != "risk_multipliers":  # Handle risk multipliers separately
                    account_config["risk_parameters"][key] = value
            
            # Ensure risk multipliers are properly set
            if "risk_multipliers" in risk_config and "risk_multipliers" not in account_config["risk_parameters"]:
                account_config["risk_parameters"]["risk_multipliers"] = {}
                
            if "risk_multipliers" in risk_config:
                for key, value in risk_config["risk_multipliers"].items():
                    account_config["risk_parameters"]["risk_multipliers"][key] = value
            
            # Save updated config
            with open(account_config_path, 'w') as f:
                json.dump(account_config, f, indent=4)
                
            logger.info(f"Updated account configuration with risk level parameters")
            
        except Exception as e:
            logger.error(f"Error updating account configuration: {str(e)}")
            raise
    
    def get_risk_level_description(self, risk_level: Optional[str] = None) -> Dict[str, Any]:
        """Get a human-readable description of a risk level"""
        if risk_level is None:
            risk_level = self.current_risk_level
            
        risk_descriptions = {
            "10": {
                "name": "Bảo Thủ (10%)",
                "description": "Chiến lược rủi ro thấp nhất, ưu tiên bảo toàn vốn. Sử dụng stop loss hẹp, kích thước vị thế nhỏ và leverage thấp. Phù hợp cho người mới bắt đầu hoặc muốn giao dịch an toàn.",
                "pros": ["Bảo vệ vốn tốt", "Ít bị cuốn vào cảm xúc", "Phù hợp cho thị trường biến động cao"],
                "cons": ["Lợi nhuận tiềm năng thấp hơn", "Tốc độ tăng trưởng chậm"]
            },
            "15": {
                "name": "Vừa Phải (15%)",
                "description": "Chiến lược cân bằng giữa rủi ro và lợi nhuận. Sử dụng stop loss rộng hơn, kích thước vị thế trung bình và leverage khiêm tốn. Phù hợp cho người có kinh nghiệm cơ bản.",
                "pros": ["Cân bằng giữa bảo vệ vốn và tăng trưởng", "Linh hoạt trong các điều kiện thị trường"],
                "cons": ["Rủi ro cao hơn mức bảo thủ", "Cần kiến thức thị trường tốt hơn"]
            },
            "20": {
                "name": "Tích Cực (20%)",
                "description": "Chiến lược ưu tiên tăng trưởng nhanh với rủi ro cao hơn. Sử dụng stop loss rộng, kích thước vị thế lớn và leverage cao. Phù hợp cho người có kinh nghiệm.",
                "pros": ["Tiềm năng lợi nhuận cao", "Tận dụng tốt các cơ hội thị trường"],
                "cons": ["Rủi ro drawdown đáng kể", "Yêu cầu kỷ luật giao dịch cao", "Cần khả năng quản lý cảm xúc tốt"]
            },
            "30": {
                "name": "Mạo Hiểm (30%)",
                "description": "Chiến lược rủi ro cao nhất, ưu tiên tuyệt đối cho việc tăng trưởng nhanh. Sử dụng stop loss rất rộng, kích thước vị thế rất lớn và leverage cao. Chỉ phù hợp cho người chuyên nghiệp.",
                "pros": ["Tiềm năng lợi nhuận rất cao", "Tăng trưởng tài khoản nhanh trong điều kiện thuận lợi"],
                "cons": ["Rủi ro mất vốn cao", "Không phù hợp với thị trường biến động", "Yêu cầu kinh nghiệm và kỷ luật rất cao"]
            }
        }
        
        if risk_level not in risk_descriptions:
            logger.warning(f"No description available for risk level {risk_level}. Using default level 10%.")
            risk_level = "10"
            
        # Add the actual configuration values to the description
        risk_config = self.get_risk_config(risk_level)
        if risk_config:
            risk_descriptions[risk_level]["configuration"] = {
                "Vị thế tối đa": risk_config.get("max_open_positions", "N/A"),
                "Kích thước vị thế (%)": risk_config.get("position_size_percent", "N/A"),
                "Stop Loss (%)": risk_config.get("stop_loss_percent", "N/A"),
                "Take Profit (%)": risk_config.get("take_profit_percent", "N/A"),
                "Trailing Stop (%)": risk_config.get("trailing_stop_percent", "N/A"),
                "Giao dịch tối đa mỗi ngày": risk_config.get("max_daily_trades", "N/A"),
                "Drawdown tối đa mỗi ngày (%)": risk_config.get("max_daily_drawdown_percent", "N/A"),
                "Leverage": risk_config.get("leverage", "N/A")
            }
            
        return risk_descriptions[risk_level]
        
    def create_custom_risk_level(self, name: str, config: Dict[str, Any]) -> bool:
        """Create a custom risk level configuration"""
        if name in self.risk_configs:
            logger.warning(f"Risk level {name} already exists. Overwriting.")
            
        file_path = f"risk_configs/risk_level_{name}.json"
        
        try:
            # Create base config if doesn't exist
            if not self.base_config:
                self.base_config = self._load_base_config()
                
            # Start with a copy of the base config and merge with custom config
            merged_config = copy.deepcopy(self.base_config)
            for key, value in config.items():
                merged_config[key] = value
                
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Save the custom risk level
            with open(file_path, 'w') as f:
                json.dump(merged_config, f, indent=4)
                
            # Add to available risk levels
            self.risk_configs[name] = file_path
            
            logger.info(f"Successfully created custom risk level: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating custom risk level {name}: {str(e)}")
            return False
            
    def get_all_risk_levels(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all available risk levels"""
        result = {}
        
        for risk_level in self.risk_configs.keys():
            result[risk_level] = {
                "description": self.get_risk_level_description(risk_level),
                "config": self.get_risk_config(risk_level)
            }
            
        return result