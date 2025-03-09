#!/usr/bin/env python3
"""
Module quản lý stop loss thích ứng dựa trên phân tích đa khung thời gian

Module này quản lý stop loss và take profit thích ứng dựa trên:
1. Biến động thị trường hiện tại
2. Phân tích đa khung thời gian (5m, 1h, 4h)
3. Đặc tính của cặp giao dịch
4. Kết hợp nhiều chiến lược để đưa ra quyết định
"""

import os
import sys
import json
import logging
import argparse
import datetime
import time
from typing import Dict, List, Tuple, Optional, Any, Union

from binance_api import BinanceAPI
from multi_timeframe_volatility_analyzer import MultiTimeframeVolatilityAnalyzer

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("adaptive_stop_loss_manager")

class AdaptiveStopLossManager:
    """Quản lý stop loss thích ứng dựa trên biến động thị trường"""
    
    def __init__(self):
        """Khởi tạo quản lý stop loss thích ứng"""
        self.api = BinanceAPI()
        self.volatility_analyzer = MultiTimeframeVolatilityAnalyzer()
        
        # Mặc định risk-reward ratio
        self.default_risk_reward_ratio = 1.5
        
        # Lưu trữ cấu hình
        self.config_dir = "configs"
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            
        # Lưu trữ lịch sử biến động
        self.volatility_history = {}
        
    def load_config(self) -> Dict:
        """
        Tải cấu hình
        
        Returns:
            Dict: Cấu hình
        """
        config_path = os.path.join(self.config_dir, "adaptive_stop_loss_config.json")
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
                
        # Cấu hình mặc định
        default_config = {
            "base_settings": {
                "min_stop_loss_percent": 1.5,
                "max_stop_loss_percent": 5.0,
                "default_risk_reward_ratio": 1.5,
                "update_interval_seconds": 300,  # 5 phút
                "trailing_sensitivity": 0.5  # 0-1, càng cao càng nhạy
            },
            "timeframe_weights": {
                "5m": 0.2,
                "1h": 0.5, 
                "4h": 0.3
            },
            "volatility_adjustment": {
                "low_volatility_threshold": 1.0,
                "high_volatility_threshold": 2.0,
                "low_volatility_factor": 1.5,
                "medium_volatility_factor": 1.2,
                "high_volatility_factor": 1.0
            },
            "strategy_specific": {
                "trend_following": {
                    "extra_buffer": 0.5  # Thêm buffer cho trend-following
                },
                "breakout": {
                    "extra_buffer": 0.3  # Thêm buffer cho breakout
                },
                "bollinger_bounce": {
                    "extra_buffer": 0.2  # Thêm buffer cho bollinger bounce
                }
            },
            "pair_specific": {
                "BTCUSDT": {
                    "extra_buffer": 0.5  # Bitcoin thường cần buffer lớn hơn
                },
                "ETHUSDT": {
                    "extra_buffer": 0.4  # Ethereum cũng có biến động lớn
                }
            }
        }
        
        # Lưu cấu hình mặc định
        try:
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình mặc định: {str(e)}")
            
        return default_config
    
    def get_active_positions(self) -> List[Dict]:
        """
        Lấy danh sách vị thế đang mở
        
        Returns:
            List[Dict]: Danh sách vị thế
        """
        try:
            positions = self.api.get_futures_position_risk()
            active_positions = []
            
            for position in positions:
                # Kiểm tra vị thế đang mở (có số lượng != 0)
                if float(position.get('positionAmt', '0')) != 0:
                    active_positions.append(position)
                    
            return active_positions
        except Exception as e:
            logger.error(f"Lỗi khi lấy vị thế: {str(e)}")
            return []
    
    def analyze_position_volatility(self, symbol: str, strategy_name: str = "") -> Dict:
        """
        Phân tích biến động cho một cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền
            strategy_name (str): Tên chiến lược (nếu có)
            
        Returns:
            Dict: Kết quả phân tích
        """
        # Lấy cấu hình
        config = self.load_config()
        
        # Phân tích biến động đa khung thời gian
        volatility_data = self.volatility_analyzer.calculate_weighted_volatility(symbol)
        weighted_volatility = volatility_data["weighted_volatility"]
        
        # Xác định hệ số an toàn dựa trên ngưỡng biến động
        volatility_config = config.get("volatility_adjustment", {})
        low_threshold = volatility_config.get("low_volatility_threshold", 1.0)
        high_threshold = volatility_config.get("high_volatility_threshold", 2.0)
        
        if weighted_volatility < low_threshold:
            safety_factor = volatility_config.get("low_volatility_factor", 1.5)
        elif weighted_volatility < high_threshold:
            safety_factor = volatility_config.get("medium_volatility_factor", 1.2)
        else:
            safety_factor = volatility_config.get("high_volatility_factor", 1.0)
            
        # Điều chỉnh thêm dựa trên chiến lược
        strategy_buffer = 0
        if strategy_name and strategy_name in config.get("strategy_specific", {}):
            strategy_buffer = config.get("strategy_specific", {}).get(strategy_name, {}).get("extra_buffer", 0)
            
        # Điều chỉnh thêm dựa trên cặp tiền
        pair_buffer = 0
        if symbol in config.get("pair_specific", {}):
            pair_buffer = config.get("pair_specific", {}).get(symbol, {}).get("extra_buffer", 0)
            
        # Tổng hợp các điều chỉnh
        total_adjustment = safety_factor + strategy_buffer + pair_buffer
        
        # Lưu lịch sử biến động
        timestamp = datetime.datetime.now().isoformat()
        if symbol not in self.volatility_history:
            self.volatility_history[symbol] = []
            
        self.volatility_history[symbol].append({
            "timestamp": timestamp,
            "weighted_volatility": weighted_volatility,
            "safety_factor": safety_factor,
            "total_adjustment": total_adjustment
        })
        
        # Giữ lịch sử trong 24 giờ gần nhất
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=24)
        cutoff_iso = cutoff_time.isoformat()
        self.volatility_history[symbol] = [
            item for item in self.volatility_history[symbol] 
            if item["timestamp"] > cutoff_iso
        ]
        
        # Kết quả phân tích
        analysis_result = {
            "symbol": symbol,
            "strategy_name": strategy_name,
            "current_volatility": weighted_volatility,
            "volatility_by_timeframe": volatility_data.get("volatility_by_timeframe", {}),
            "safety_factor": safety_factor,
            "strategy_buffer": strategy_buffer,
            "pair_buffer": pair_buffer,
            "total_adjustment": total_adjustment,
            "volatility_history": self.volatility_history.get(symbol, [])[-5:]  # 5 giá trị gần nhất
        }
        
        return analysis_result
    
    def calculate_optimal_stop_loss(self, symbol: str, side: str, entry_price: float, 
                                   strategy_name: str = "") -> Dict:
        """
        Tính toán stop loss tối ưu
        
        Args:
            symbol (str): Mã cặp tiền
            side (str): Phía giao dịch (BUY hoặc SELL)
            entry_price (float): Giá vào lệnh
            strategy_name (str): Tên chiến lược (nếu có)
            
        Returns:
            Dict: Thông tin stop loss và take profit
        """
        # Lấy cấu hình
        config = self.load_config()
        base_settings = config.get("base_settings", {})
        
        # Ngưỡng stop loss tối thiểu và tối đa
        min_stop_loss = base_settings.get("min_stop_loss_percent", 1.5)
        max_stop_loss = base_settings.get("max_stop_loss_percent", 5.0)
        
        # Phân tích biến động
        analysis = self.analyze_position_volatility(symbol, strategy_name)
        weighted_volatility = analysis["current_volatility"]
        total_adjustment = analysis["total_adjustment"]
        
        # Tính toán stop loss theo phần trăm
        raw_stop_loss_percent = weighted_volatility * total_adjustment
        
        # Giới hạn trong ngưỡng min và max
        stop_loss_percent = max(min_stop_loss, min(max_stop_loss, raw_stop_loss_percent))
        
        # Tính toán risk-reward ratio
        risk_reward_ratio = base_settings.get("default_risk_reward_ratio", 1.5)
        take_profit_percent = stop_loss_percent * risk_reward_ratio
        
        # Tính giá stop loss và take profit
        if side.upper() == "BUY" or side.upper() == "LONG":
            stop_loss_price = entry_price * (1 - stop_loss_percent / 100)
            take_profit_price = entry_price * (1 + take_profit_percent / 100)
        else:  # SELL hoặc SHORT
            stop_loss_price = entry_price * (1 + stop_loss_percent / 100)
            take_profit_price = entry_price * (1 - take_profit_percent / 100)
            
        # Kết quả
        result = {
            "symbol": symbol,
            "side": side,
            "entry_price": entry_price,
            "strategy_name": strategy_name,
            "weighted_volatility": weighted_volatility,
            "total_adjustment": total_adjustment,
            "stop_loss": {
                "percent": stop_loss_percent,
                "price": stop_loss_price
            },
            "take_profit": {
                "percent": take_profit_percent,
                "price": take_profit_price
            },
            "risk_reward_ratio": risk_reward_ratio,
            "analysis": analysis
        }
        
        return result
    
    def update_active_positions_sltp(self) -> List[Dict]:
        """
        Cập nhật stop loss và take profit cho các vị thế đang mở
        
        Returns:
            List[Dict]: Danh sách kết quả cập nhật
        """
        # Lấy vị thế đang mở
        positions = self.get_active_positions()
        
        # Kết quả cập nhật
        update_results = []
        
        for position in positions:
            symbol = position.get("symbol")
            position_amt = float(position.get("positionAmt", "0"))
            entry_price = float(position.get("entryPrice", "0"))
            
            if position_amt == 0 or entry_price == 0:
                continue
                
            # Xác định phía giao dịch
            side = "BUY" if position_amt > 0 else "SELL"
            
            try:
                # Đọc thông tin vị thế từ file
                position_info = self.get_position_info(symbol)
                strategy_name = position_info.get("strategy", "")
                
                # Tính toán stop loss và take profit tối ưu
                optimal_sltp = self.calculate_optimal_stop_loss(
                    symbol=symbol,
                    side=side, 
                    entry_price=entry_price,
                    strategy_name=strategy_name
                )
                
                # Lấy giá stop loss và take profit
                stop_loss_price = optimal_sltp["stop_loss"]["price"]
                take_profit_price = optimal_sltp["take_profit"]["price"]
                
                # Báo cáo điều chỉnh
                logger.info(f"Cập nhật SL/TP cho {symbol} ({side}): "
                           f"SL={optimal_sltp['stop_loss']['percent']:.2f}% "
                           f"({stop_loss_price:.2f}), "
                           f"TP={optimal_sltp['take_profit']['percent']:.2f}% "
                           f"({take_profit_price:.2f})")
                
                # Cập nhật vị thế
                # Trong ứng dụng thực, ở đây gọi API Binance để cập nhật stop loss và take profit
                
                # Lưu kết quả
                update_results.append({
                    "symbol": symbol,
                    "side": side,
                    "entry_price": entry_price,
                    "updated_stop_loss": stop_loss_price,
                    "updated_take_profit": take_profit_price,
                    "stop_loss_percent": optimal_sltp["stop_loss"]["percent"],
                    "take_profit_percent": optimal_sltp["take_profit"]["percent"]
                })
                
            except Exception as e:
                logger.error(f"Lỗi khi cập nhật SL/TP cho {symbol}: {str(e)}")
                
        return update_results
    
    def get_position_info(self, symbol: str) -> Dict:
        """
        Lấy thông tin vị thế từ file
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            Dict: Thông tin vị thế
        """
        position_file = os.path.join("data", "positions", f"{symbol}_position.json")
        
        if os.path.exists(position_file):
            try:
                with open(position_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Lỗi khi đọc thông tin vị thế {symbol}: {str(e)}")
                
        return {"symbol": symbol, "strategy": ""}
    
    def run_monitoring_loop(self):
        """Vòng lặp theo dõi và cập nhật stop loss"""
        config = self.load_config()
        update_interval = config.get("base_settings", {}).get("update_interval_seconds", 300)
        
        logger.info(f"Bắt đầu theo dõi và cập nhật stop loss (interval={update_interval}s)")
        
        try:
            while True:
                # Cập nhật stop loss và take profit
                update_results = self.update_active_positions_sltp()
                
                if update_results:
                    logger.info(f"Đã cập nhật SL/TP cho {len(update_results)} vị thế")
                else:
                    logger.info("Không có vị thế nào cần cập nhật SL/TP")
                
                # Chờ đến lần cập nhật tiếp theo
                time.sleep(update_interval)
                
        except KeyboardInterrupt:
            logger.info("Đã dừng theo dõi stop loss")
        except Exception as e:
            logger.error(f"Lỗi trong vòng lặp theo dõi: {str(e)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quản lý stop loss thích ứng")
    parser.add_argument("--monitor", action="store_true", help="Chạy vòng lặp theo dõi")
    parser.add_argument("--one-time", action="store_true", help="Chỉ chạy một lần thay vì theo vòng lặp liên tục")
    parser.add_argument("--symbol", type=str, help="Mã cặp tiền cần phân tích")
    parser.add_argument("--side", type=str, choices=["BUY", "SELL"], help="Phía giao dịch")
    parser.add_argument("--price", type=float, help="Giá vào lệnh")
    parser.add_argument("--strategy", type=str, help="Tên chiến lược")
    
    args = parser.parse_args()
    
    manager = AdaptiveStopLossManager()
    
    if args.monitor:
        if args.one_time:
            # Chỉ chạy một lần cập nhật cho tất cả vị thế
            logger.info("Đang chạy cập nhật một lần cho tất cả vị thế...")
            update_results = manager.update_active_positions_sltp()
            if update_results:
                logger.info(f"Đã cập nhật SL/TP cho {len(update_results)} vị thế")
                for result in update_results:
                    logger.info(f"Đã cập nhật {result['symbol']} ({result['side']}): SL={result['stop_loss_percent']:.2f}% ({result['updated_stop_loss']:.2f}), TP={result['take_profit_percent']:.2f}% ({result['updated_take_profit']:.2f})")
            else:
                logger.info("Không có vị thế nào cần cập nhật SL/TP")
        else:
            # Chạy vòng lặp theo dõi liên tục
            manager.run_monitoring_loop()
    elif args.symbol and args.side and args.price:
        # Phân tích một cặp tiền cụ thể
        result = manager.calculate_optimal_stop_loss(
            symbol=args.symbol,
            side=args.side,
            entry_price=args.price,
            strategy_name=args.strategy
        )
        
        print(json.dumps(result, indent=2))
    else:
        # Hiển thị hướng dẫn
        parser.print_help()