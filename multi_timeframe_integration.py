#!/usr/bin/env python3
"""
Module tích hợp phân tích đa khung thời gian

Module này giải quyết vấn đề mâu thuẫn giữa các khuyến nghị trên các khung
thời gian khác nhau bằng cách:
1. Gán trọng số cho từng khung thời gian
2. Tích hợp phân tích từ nhiều khung thời gian thành một điểm chung
3. Cung cấp khuyến nghị tổng hợp thống nhất

Điều này giúp tránh tình trạng khung thời gian nhỏ khuyến nghị SELL
trong khi khung thời gian lớn khuyến nghị BUY cùng lúc.
"""

import os
import json
import logging
from typing import Dict, List, Tuple, Optional, Union

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("multi_timeframe_integration")

# Đường dẫn file cấu hình
CONFIG_PATH = "configs/multi_timeframe_config.json"

class MultiTimeframeIntegration:
    """
    Lớp tích hợp phân tích từ nhiều khung thời gian
    """
    
    def __init__(self, config_path: str = CONFIG_PATH):
        """
        Khởi tạo tích hợp đa khung thời gian
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
        """
        self.config_path = config_path
        self.config = self._load_or_create_config()
        logger.info(f"Đã khởi tạo MultiTimeframeIntegration với cấu hình từ {config_path}")
    
    def _load_or_create_config(self) -> Dict:
        """
        Tải cấu hình từ file hoặc tạo cấu hình mặc định nếu không tồn tại
        
        Returns:
            Dict: Cấu hình đã tải hoặc tạo mới
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
                return config
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
        
        # Tạo cấu hình mặc định
        default_config = {
            "timeframe_weights": {
                "5m": 0.1,
                "15m": 0.15,
                "1h": 0.4,
                "4h": 0.25,
                "1d": 0.1
            },
            "primary_timeframe": "1h",
            "conflict_resolution": "weighted_average",  # weighted_average, primary_only, majority_vote
            "significance_threshold": 20,  # Mức chênh lệch điểm đáng kể giữa các khung
            "entry_exit_preferences": {
                "entry_points": "primary_timeframe",  # primary_timeframe, most_conservative, most_aggressive
                "take_profit": "most_conservative",   # primary_timeframe, most_conservative, most_aggressive
                "stop_loss": "most_conservative"      # primary_timeframe, most_conservative, most_aggressive
            },
            "market_regime_influence": {
                "enabled": True,
                "trending_up_boost": 10,
                "trending_down_boost": 10,
                "volatile_discount": 5,
                "ranging_discount": 0
            }
        }
        
        # Lưu cấu hình mặc định
        try:
            # Đảm bảo thư mục tồn tại
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            
            logger.info(f"Đã tạo cấu hình mặc định tại {self.config_path}")
            return default_config
        except Exception as e:
            logger.error(f"Lỗi khi tạo cấu hình mặc định: {str(e)}")
            return default_config
    
    def integrate_timeframes(self, symbol: str, timeframe_analyses: Dict[str, Dict]) -> Dict:
        """
        Tích hợp phân tích từ nhiều khung thời gian
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe_analyses (Dict[str, Dict]): Phân tích theo từng khung thời gian
                {
                    "5m": {...},
                    "15m": {...},
                    "1h": {...},
                    "4h": {...}
                }
            
        Returns:
            Dict: Kết quả tích hợp
        """
        try:
            # Kiểm tra đầu vào
            if not timeframe_analyses:
                logger.error("Không có dữ liệu phân tích để tích hợp")
                return {}
            
            # Lọc các khung thời gian đã cấu hình
            weighted_analyses = {}
            for tf, weight in self.config["timeframe_weights"].items():
                if tf in timeframe_analyses:
                    weighted_analyses[tf] = {
                        "analysis": timeframe_analyses[tf],
                        "weight": weight
                    }
            
            # Kiểm tra sau khi lọc
            if not weighted_analyses:
                logger.warning("Không có khung thời gian nào phù hợp với cấu hình")
                # Sử dụng tất cả với trọng số bằng nhau
                total_weight = 1.0 / len(timeframe_analyses)
                for tf in timeframe_analyses:
                    weighted_analyses[tf] = {
                        "analysis": timeframe_analyses[tf],
                        "weight": total_weight
                    }
            
            # Tích hợp điểm
            integrated_score = self._calculate_integrated_score(weighted_analyses)
            
            # Kiểm tra xung đột
            conflict_info = self._check_conflicts(weighted_analyses)
            
            # Xác định điểm vào và điểm ra
            entry_exit_points = self._determine_entry_exit_points(weighted_analyses)
            
            # Xác định khuyến nghị tổng hợp
            integrated_recommendation = self._determine_recommendation(integrated_score)
            
            # Tạo kết quả tích hợp
            result = {
                "symbol": symbol,
                "integrated_score": integrated_score,
                "recommendation": integrated_recommendation,
                "entry_exit_points": entry_exit_points,
                "conflict_info": conflict_info,
                "timeframe_breakdown": {
                    tf: {
                        "score": analysis["analysis"]["score"],
                        "recommendation": analysis["analysis"]["recommendation"],
                        "weight": analysis["weight"]
                    } for tf, analysis in weighted_analyses.items()
                }
            }
            
            logger.info(f"Đã tích hợp phân tích đa khung thời gian cho {symbol}, điểm tích hợp: {integrated_score}, khuyến nghị: {integrated_recommendation}")
            return result
        
        except Exception as e:
            logger.error(f"Lỗi khi tích hợp đa khung thời gian: {str(e)}")
            return {
                "symbol": symbol,
                "error": str(e),
                "integrated_score": 50,
                "recommendation": "neutral",
                "entry_exit_points": {
                    "long": {"entry_points": [], "exit_points": {"take_profit": [], "stop_loss": []}},
                    "short": {"entry_points": [], "exit_points": {"take_profit": [], "stop_loss": []}}
                }
            }
    
    def _calculate_integrated_score(self, weighted_analyses: Dict[str, Dict]) -> int:
        """
        Tính điểm tích hợp từ nhiều khung thời gian
        
        Args:
            weighted_analyses (Dict[str, Dict]): Phân tích theo từng khung thời gian và trọng số
            
        Returns:
            int: Điểm tích hợp (0-100)
        """
        conflict_resolution = self.config["conflict_resolution"]
        
        if conflict_resolution == "primary_only":
            # Chỉ sử dụng khung thời gian chính
            primary_tf = self.config["primary_timeframe"]
            if primary_tf in weighted_analyses:
                return weighted_analyses[primary_tf]["analysis"]["score"]
            else:
                # Nếu không có khung thời gian chính, sử dụng khung thời gian có trọng số cao nhất
                max_weight_tf = max(weighted_analyses.items(), key=lambda x: x[1]["weight"])[0]
                return weighted_analyses[max_weight_tf]["analysis"]["score"]
        
        elif conflict_resolution == "majority_vote":
            # Đếm số khuyến nghị cho mỗi loại
            rec_counts = {"buy": 0, "strong_buy": 0, "neutral": 0, "sell": 0, "strong_sell": 0}
            
            for tf_data in weighted_analyses.values():
                rec = tf_data["analysis"]["recommendation"]
                rec_counts[rec] = rec_counts.get(rec, 0) + 1
            
            # Tìm khuyến nghị phổ biến nhất
            max_rec = max(rec_counts.items(), key=lambda x: x[1])[0]
            
            # Chuyển khuyến nghị thành điểm
            if max_rec == "strong_buy":
                return 90
            elif max_rec == "buy":
                return 70
            elif max_rec == "neutral":
                return 50
            elif max_rec == "sell":
                return 30
            else:  # strong_sell
                return 10
        
        else:  # weighted_average
            # Tính điểm theo trung bình có trọng số
            total_score = 0
            total_weight = 0
            
            for tf_data in weighted_analyses.values():
                total_score += tf_data["analysis"]["score"] * tf_data["weight"]
                total_weight += tf_data["weight"]
            
            if total_weight > 0:
                return round(total_score / total_weight)
            else:
                return 50  # Trung lập
    
    def _check_conflicts(self, weighted_analyses: Dict[str, Dict]) -> Dict:
        """
        Kiểm tra xung đột giữa các khung thời gian
        
        Args:
            weighted_analyses (Dict[str, Dict]): Phân tích theo từng khung thời gian và trọng số
            
        Returns:
            Dict: Thông tin xung đột
        """
        if len(weighted_analyses) <= 1:
            return {"has_conflict": False}
        
        # Xác định ngưỡng xung đột
        threshold = self.config["significance_threshold"]
        
        # Kiểm tra các cặp khung thời gian
        conflicts = []
        timeframes = list(weighted_analyses.keys())
        
        for i in range(len(timeframes)):
            for j in range(i+1, len(timeframes)):
                tf1 = timeframes[i]
                tf2 = timeframes[j]
                
                score1 = weighted_analyses[tf1]["analysis"]["score"]
                score2 = weighted_analyses[tf2]["analysis"]["score"]
                
                # Nếu chênh lệch điểm lớn hơn ngưỡng
                if abs(score1 - score2) >= threshold:
                    # Và khuyến nghị khác nhau
                    rec1 = weighted_analyses[tf1]["analysis"]["recommendation"]
                    rec2 = weighted_analyses[tf2]["analysis"]["recommendation"]
                    
                    if (rec1 in ["buy", "strong_buy"] and rec2 in ["sell", "strong_sell"]) or \
                       (rec1 in ["sell", "strong_sell"] and rec2 in ["buy", "strong_buy"]):
                        conflicts.append({
                            "timeframe1": tf1,
                            "timeframe2": tf2,
                            "score1": score1,
                            "score2": score2,
                            "rec1": rec1,
                            "rec2": rec2
                        })
        
        return {
            "has_conflict": len(conflicts) > 0,
            "conflicts": conflicts,
            "resolution_method": self.config["conflict_resolution"]
        }
    
    def _determine_entry_exit_points(self, weighted_analyses: Dict[str, Dict]) -> Dict:
        """
        Xác định điểm vào và ra tốt nhất từ phân tích đa khung thời gian
        
        Args:
            weighted_analyses (Dict[str, Dict]): Phân tích theo từng khung thời gian và trọng số
            
        Returns:
            Dict: Điểm vào và ra tối ưu
        """
        # Cài đặt từ cấu hình
        entry_preference = self.config["entry_exit_preferences"]["entry_points"]
        tp_preference = self.config["entry_exit_preferences"]["take_profit"]
        sl_preference = self.config["entry_exit_preferences"]["stop_loss"]
        
        # Lấy khung thời gian chính
        primary_tf = self.config["primary_timeframe"]
        if primary_tf not in weighted_analyses:
            # Sử dụng khung thời gian có trọng số cao nhất
            primary_tf = max(weighted_analyses.items(), key=lambda x: x[1]["weight"])[0]
        
        # Khởi tạo kết quả
        result = {
            "long": {
                "entry_points": [],
                "exit_points": {
                    "take_profit": [],
                    "stop_loss": []
                },
                "reasoning": []
            },
            "short": {
                "entry_points": [],
                "exit_points": {
                    "take_profit": [],
                    "stop_loss": []
                },
                "reasoning": []
            }
        }
        
        # Thu thập điểm vào/ra từ tất cả các khung thời gian
        all_entry_points = {"long": [], "short": []}
        all_tp_points = {"long": [], "short": []}
        all_sl_points = {"long": [], "short": []}
        all_reasoning = {"long": [], "short": []}
        
        for tf, tf_data in weighted_analyses.items():
            analysis = tf_data["analysis"]
            
            for direction in ["long", "short"]:
                # Điểm vào
                entry_points = analysis.get("entry_exit_points", {}).get(direction, {}).get("entry_points", [])
                for point in entry_points:
                    all_entry_points[direction].append({"value": point, "tf": tf})
                
                # Điểm take profit
                tp_points = analysis.get("entry_exit_points", {}).get(direction, {}).get("exit_points", {}).get("take_profit", [])
                for point in tp_points:
                    all_tp_points[direction].append({"value": point, "tf": tf})
                
                # Điểm stop loss
                sl_points = analysis.get("entry_exit_points", {}).get(direction, {}).get("exit_points", {}).get("stop_loss", [])
                for point in sl_points:
                    all_sl_points[direction].append({"value": point, "tf": tf})
                
                # Lý do
                reasoning = analysis.get("entry_exit_points", {}).get(direction, {}).get("reasoning", [])
                for reason in reasoning:
                    all_reasoning[direction].append({"reason": reason, "tf": tf})
        
        # Xác định điểm vào
        for direction in ["long", "short"]:
            # Lọc các điểm vào không trống
            entry_points = [p for p in all_entry_points[direction] if p["value"] is not None]
            
            # Lấy điểm vào theo ưu tiên
            if entry_points:
                if entry_preference == "primary_timeframe":
                    # Chỉ lấy từ khung thời gian chính
                    primary_entries = [p["value"] for p in entry_points if p["tf"] == primary_tf]
                    if primary_entries:
                        result[direction]["entry_points"] = primary_entries
                
                elif entry_preference == "most_conservative":
                    # Chọn điểm vào bảo thủ nhất
                    if direction == "long":
                        # Điểm vào cao nhất cho LONG (ít lợi nhuận nhất)
                        best_entry = max(entry_points, key=lambda x: x["value"])
                        result[direction]["entry_points"] = [best_entry["value"]]
                    else:
                        # Điểm vào thấp nhất cho SHORT (ít lợi nhuận nhất)
                        best_entry = min(entry_points, key=lambda x: x["value"])
                        result[direction]["entry_points"] = [best_entry["value"]]
                
                elif entry_preference == "most_aggressive":
                    # Chọn điểm vào tích cực nhất
                    if direction == "long":
                        # Điểm vào thấp nhất cho LONG (nhiều lợi nhuận nhất)
                        best_entry = min(entry_points, key=lambda x: x["value"])
                        result[direction]["entry_points"] = [best_entry["value"]]
                    else:
                        # Điểm vào cao nhất cho SHORT (nhiều lợi nhuận nhất)
                        best_entry = max(entry_points, key=lambda x: x["value"])
                        result[direction]["entry_points"] = [best_entry["value"]]
            
            # Xác định điểm take profit
            if all_tp_points[direction]:
                if tp_preference == "primary_timeframe":
                    # Chỉ lấy từ khung thời gian chính
                    primary_tp = [p["value"] for p in all_tp_points[direction] if p["tf"] == primary_tf]
                    if primary_tp:
                        result[direction]["exit_points"]["take_profit"] = primary_tp
                
                elif tp_preference == "most_conservative":
                    # Chọn điểm take profit bảo thủ nhất
                    if direction == "long":
                        # TP thấp nhất cho LONG (ít lợi nhuận nhất)
                        best_tp = min(all_tp_points[direction], key=lambda x: x["value"])
                        result[direction]["exit_points"]["take_profit"] = [best_tp["value"]]
                    else:
                        # TP cao nhất cho SHORT (ít lợi nhuận nhất)
                        best_tp = max(all_tp_points[direction], key=lambda x: x["value"])
                        result[direction]["exit_points"]["take_profit"] = [best_tp["value"]]
                
                elif tp_preference == "most_aggressive":
                    # Chọn điểm take profit tích cực nhất
                    if direction == "long":
                        # TP cao nhất cho LONG (nhiều lợi nhuận nhất)
                        best_tp = max(all_tp_points[direction], key=lambda x: x["value"])
                        result[direction]["exit_points"]["take_profit"] = [best_tp["value"]]
                    else:
                        # TP thấp nhất cho SHORT (nhiều lợi nhuận nhất)
                        best_tp = min(all_tp_points[direction], key=lambda x: x["value"])
                        result[direction]["exit_points"]["take_profit"] = [best_tp["value"]]
            
            # Xác định điểm stop loss
            if all_sl_points[direction]:
                if sl_preference == "primary_timeframe":
                    # Chỉ lấy từ khung thời gian chính
                    primary_sl = [p["value"] for p in all_sl_points[direction] if p["tf"] == primary_tf]
                    if primary_sl:
                        result[direction]["exit_points"]["stop_loss"] = primary_sl
                
                elif sl_preference == "most_conservative":
                    # Chọn điểm stop loss bảo thủ nhất
                    if direction == "long":
                        # SL cao nhất cho LONG (ít lỗ nhất)
                        best_sl = max(all_sl_points[direction], key=lambda x: x["value"])
                        result[direction]["exit_points"]["stop_loss"] = [best_sl["value"]]
                    else:
                        # SL thấp nhất cho SHORT (ít lỗ nhất)
                        best_sl = min(all_sl_points[direction], key=lambda x: x["value"])
                        result[direction]["exit_points"]["stop_loss"] = [best_sl["value"]]
                
                elif sl_preference == "most_aggressive":
                    # Chọn điểm stop loss tích cực nhất
                    if direction == "long":
                        # SL thấp nhất cho LONG (nhiều lỗ hơn)
                        best_sl = min(all_sl_points[direction], key=lambda x: x["value"])
                        result[direction]["exit_points"]["stop_loss"] = [best_sl["value"]]
                    else:
                        # SL cao nhất cho SHORT (nhiều lỗ hơn)
                        best_sl = max(all_sl_points[direction], key=lambda x: x["value"])
                        result[direction]["exit_points"]["stop_loss"] = [best_sl["value"]]
            
            # Lấy lý do từ tất cả các khung thời gian
            if all_reasoning[direction]:
                unique_reasons = {}
                for reason_data in all_reasoning[direction]:
                    reason = reason_data["reason"]
                    tf = reason_data["tf"]
                    if reason not in unique_reasons:
                        unique_reasons[reason] = tf
                
                result[direction]["reasoning"] = [f"{reason} ({tf})" for reason, tf in unique_reasons.items()]
        
        return result
    
    def _determine_recommendation(self, score: int) -> str:
        """
        Xác định khuyến nghị dựa trên điểm
        
        Args:
            score (int): Điểm phân tích
            
        Returns:
            str: Khuyến nghị
        """
        if score >= 80:
            return "strong_buy"
        elif score >= 60:
            return "buy"
        elif score >= 40:
            return "neutral"
        elif score >= 20:
            return "sell"
        else:
            return "strong_sell"

    def update_config(self, new_config: Dict) -> bool:
        """
        Cập nhật cấu hình
        
        Args:
            new_config (Dict): Cấu hình mới
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu thất bại
        """
        try:
            self.config.update(new_config)
            
            # Lưu cấu hình
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            
            logger.info(f"Đã cập nhật cấu hình tại {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật cấu hình: {str(e)}")
            return False

def main():
    """Hàm chính để test MultiTimeframeIntegration"""
    print("\nHỆ THỐNG TÍCH HỢP ĐA KHUNG THỜI GIAN\n")
    
    integration = MultiTimeframeIntegration()
    
    # Dữ liệu mẫu để test
    sample_data = {
        "5m": {
            "symbol": "BTCUSDT",
            "timeframe": "5m",
            "score": 25,
            "recommendation": "sell",
            "entry_exit_points": {
                "long": {
                    "entry_points": [],
                    "exit_points": {"take_profit": [], "stop_loss": []},
                    "reasoning": []
                },
                "short": {
                    "entry_points": [50000],
                    "exit_points": {"take_profit": [49000], "stop_loss": [51000]},
                    "reasoning": ["RSI overbought"]
                },
                "score": {"long": 0, "short": 25}
            }
        },
        "15m": {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "score": 25,
            "recommendation": "sell",
            "entry_exit_points": {
                "long": {
                    "entry_points": [],
                    "exit_points": {"take_profit": [], "stop_loss": []},
                    "reasoning": []
                },
                "short": {
                    "entry_points": [50100],
                    "exit_points": {"take_profit": [49100], "stop_loss": [51100]},
                    "reasoning": ["MACD bearish crossover"]
                },
                "score": {"long": 0, "short": 25}
            }
        },
        "1h": {
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "score": 75,
            "recommendation": "buy",
            "entry_exit_points": {
                "long": {
                    "entry_points": [49800],
                    "exit_points": {"take_profit": [52000], "stop_loss": [48000]},
                    "reasoning": ["Support level bounce", "Bullish divergence"]
                },
                "short": {
                    "entry_points": [],
                    "exit_points": {"take_profit": [], "stop_loss": []},
                    "reasoning": []
                },
                "score": {"long": 75, "short": 0}
            }
        },
        "4h": {
            "symbol": "BTCUSDT",
            "timeframe": "4h",
            "score": 45,
            "recommendation": "neutral",
            "entry_exit_points": {
                "long": {
                    "entry_points": [49500],
                    "exit_points": {"take_profit": [51500], "stop_loss": [48000]},
                    "reasoning": ["Near support level"]
                },
                "short": {
                    "entry_points": [51000],
                    "exit_points": {"take_profit": [49000], "stop_loss": [52500]},
                    "reasoning": ["Resistance zone"]
                },
                "score": {"long": 45, "short": 45}
            }
        }
    }
    
    # Tích hợp phân tích
    result = integration.integrate_timeframes("BTCUSDT", sample_data)
    
    # In kết quả
    print(f"Điểm tích hợp: {result['integrated_score']}")
    print(f"Khuyến nghị: {result['recommendation'].upper()}")
    
    # Kiểm tra xung đột
    if result['conflict_info']['has_conflict']:
        print("\nPhát hiện xung đột giữa các khung thời gian:")
        for conflict in result['conflict_info']['conflicts']:
            print(f"  - {conflict['timeframe1']} ({conflict['rec1'].upper()}, {conflict['score1']}) vs {conflict['timeframe2']} ({conflict['rec2'].upper()}, {conflict['score2']})")
        print(f"Giải quyết bằng phương pháp: {result['conflict_info']['resolution_method']}")
    
    # Hiển thị điểm vào/ra
    print("\nThông tin hướng BUY:")
    print(f"  - Điểm vào: {result['entry_exit_points']['long']['entry_points']}")
    print(f"  - Take profit: {result['entry_exit_points']['long']['exit_points']['take_profit']}")
    print(f"  - Stop loss: {result['entry_exit_points']['long']['exit_points']['stop_loss']}")
    print(f"  - Lý do: {result['entry_exit_points']['long']['reasoning']}")
    
    print("\nThông tin hướng SELL:")
    print(f"  - Điểm vào: {result['entry_exit_points']['short']['entry_points']}")
    print(f"  - Take profit: {result['entry_exit_points']['short']['exit_points']['take_profit']}")
    print(f"  - Stop loss: {result['entry_exit_points']['short']['exit_points']['stop_loss']}")
    print(f"  - Lý do: {result['entry_exit_points']['short']['reasoning']}")
    
    # Hiển thị điểm từng khung thời gian
    print("\nĐiểm theo từng khung thời gian:")
    for tf, data in result['timeframe_breakdown'].items():
        print(f"  - {tf}: {data['recommendation'].upper()} (Điểm: {data['score']}, Trọng số: {data['weight']})")

if __name__ == "__main__":
    main()