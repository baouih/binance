#!/usr/bin/env python3
"""
Module giải quyết xung đột tín hiệu đa khung thời gian (Multi-Timeframe Conflict Resolver)

Module này cung cấp các phương pháp nâng cao để phát hiện và giải quyết xung đột giữa các
tín hiệu giao dịch từ nhiều khung thời gian khác nhau, bao gồm cả trường hợp hòa (tie).
"""

import os
import json
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime, timedelta

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("multi_timeframe_conflict_resolver")

# Đường dẫn lưu cấu hình
CONFLICT_RESOLVER_CONFIG_PATH = "configs/conflict_resolver_config.json"

class MultiTimeframeConflictResolver:
    """Lớp giải quyết xung đột tín hiệu giữa các khung thời gian"""
    
    def __init__(self):
        """Khởi tạo resolver"""
        self.config = self._load_or_create_config()
        
    def _load_or_create_config(self) -> Dict:
        """
        Tải hoặc tạo cấu hình mặc định
        
        Returns:
            Dict: Cấu hình giải quyết xung đột
        """
        if os.path.exists(CONFLICT_RESOLVER_CONFIG_PATH):
            try:
                with open(CONFLICT_RESOLVER_CONFIG_PATH, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình giải quyết xung đột từ {CONFLICT_RESOLVER_CONFIG_PATH}")
                return config
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình giải quyết xung đột: {str(e)}")
        
        # Tạo cấu hình mặc định
        logger.info("Tạo cấu hình giải quyết xung đột mặc định")
        
        config = {
            "resolution_methods": {
                "default": "weighted_average",  # Phương pháp mặc định: weighted_average, majority_vote, primary_only
                "by_market_regime": {
                    "trending": "weighted_average",  # Trong thị trường trending, ưu tiên trọng số KTG lớn
                    "ranging": "weighted_average",   # Trong thị trường ranging, điều chỉnh trọng số cho cân bằng
                    "volatile": "primary_only",      # Trong thị trường biến động, ưu tiên KTG lớn nhất
                    "quiet": "consensus"             # Trong thị trường ít biến động, yêu cầu đồng thuận
                }
            },
            "timeframe_weights": {
                "default": {
                    "1m": 0.05,
                    "5m": 0.10,
                    "15m": 0.15,
                    "30m": 0.15,
                    "1h": 0.20,
                    "4h": 0.25,
                    "1d": 0.30
                },
                "by_market_regime": {
                    "trending": {
                        "1m": 0.025,
                        "5m": 0.05,
                        "15m": 0.10,
                        "30m": 0.125,
                        "1h": 0.20,
                        "4h": 0.25,
                        "1d": 0.35
                    },
                    "ranging": {
                        "1m": 0.10,
                        "5m": 0.15,
                        "15m": 0.15,
                        "30m": 0.15,
                        "1h": 0.15,
                        "4h": 0.15,
                        "1d": 0.15
                    },
                    "volatile": {
                        "1m": 0.025,
                        "5m": 0.05,
                        "15m": 0.075,
                        "30m": 0.10,
                        "1h": 0.15,
                        "4h": 0.25,
                        "1d": 0.35
                    },
                    "quiet": {
                        "1m": 0.075,
                        "5m": 0.10,
                        "15m": 0.125,
                        "30m": 0.15,
                        "1h": 0.175,
                        "4h": 0.20,
                        "1d": 0.25
                    }
                }
            },
            "primary_timeframes": {
                "default": "1h",
                "by_market_regime": {
                    "trending": "4h",
                    "ranging": "1h",
                    "volatile": "4h",
                    "quiet": "1h"
                }
            },
            "tie_breaking_rules": {
                "safety_first": True,  # Nếu True, ưu tiên 'neutral' khi hòa
                "prefer_higher_timeframe": True,  # Nếu True, ưu tiên khung thời gian cao hơn khi hòa
                "recent_performance_bonus": 0.1,  # Bonus cho chiến lược hoạt động tốt gần đây
                "safety_order": ["neutral", "buy", "strong_buy", "sell", "strong_sell"]  # Thứ tự ưu tiên an toàn
            },
            "consensus": {
                "required_agreement": 0.66,  # Tỷ lệ đồng thuận cần thiết (66%)
                "minimum_timeframes": 3,     # Số khung thời gian tối thiểu cần kiểm tra
                "neutral_threshold": 0.5,    # Tỷ lệ các khung thời gian mâu thuẫn dẫn đến neutral
                "strong_consensus_boost": 0.1  # Tăng cường điểm khi có đồng thuận mạnh
            },
            "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Lưu cấu hình
        try:
            os.makedirs(os.path.dirname(CONFLICT_RESOLVER_CONFIG_PATH), exist_ok=True)
            with open(CONFLICT_RESOLVER_CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=4)
            logger.info(f"Đã tạo cấu hình giải quyết xung đột mặc định tại {CONFLICT_RESOLVER_CONFIG_PATH}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình giải quyết xung đột: {str(e)}")
        
        return config
    
    def save_config(self) -> bool:
        """
        Lưu cấu hình hiện tại
        
        Returns:
            bool: True nếu lưu thành công, False nếu lỗi
        """
        try:
            # Cập nhật thời gian
            self.config["last_updated"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Đảm bảo thư mục tồn tại
            os.makedirs(os.path.dirname(CONFLICT_RESOLVER_CONFIG_PATH), exist_ok=True)
            
            # Lưu cấu hình
            with open(CONFLICT_RESOLVER_CONFIG_PATH, 'w') as f:
                json.dump(self.config, f, indent=4)
            
            logger.info(f"Đã lưu cấu hình giải quyết xung đột vào {CONFLICT_RESOLVER_CONFIG_PATH}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình giải quyết xung đột: {str(e)}")
            return False
    
    def resolve_conflicts(self, timeframe_analyses: Dict[str, Dict], 
                        market_regime: str = "ranging", 
                        method: str = None) -> Dict:
        """
        Giải quyết xung đột giữa các khung thời gian
        
        Args:
            timeframe_analyses (Dict[str, Dict]): Kết quả phân tích theo từng khung thời gian
            market_regime (str): Chế độ thị trường hiện tại
            method (str, optional): Phương pháp giải quyết xung đột
            
        Returns:
            Dict: Kết quả tích hợp
        """
        if not timeframe_analyses:
            return {}
        
        # Nếu chỉ có một khung thời gian, trả về trực tiếp
        if len(timeframe_analyses) == 1:
            tf = list(timeframe_analyses.keys())[0]
            return {
                "recommendation": timeframe_analyses[tf].get("recommendation", "neutral"),
                "score": timeframe_analyses[tf].get("score", 50),
                "market_regime": market_regime,
                "primary_timeframe": tf,
                "timeframe_signals": {tf: timeframe_analyses[tf]},
                "resolution_method": "single_timeframe",
                "confidence": 1.0,
                "conflicts_detected": False,
                "conflict_details": {}
            }
        
        # Xác định phương pháp giải quyết
        if not method:
            method = self.config["resolution_methods"]["by_market_regime"].get(
                market_regime, self.config["resolution_methods"]["default"])
        
        # Phát hiện xung đột
        conflict_details = self._detect_conflicts(timeframe_analyses)
        
        # Giải quyết xung đột theo phương pháp đã chọn
        if method == "weighted_average":
            result = self._weighted_average_resolution(timeframe_analyses, market_regime)
        elif method == "majority_vote":
            result = self._majority_vote_resolution(timeframe_analyses, market_regime)
        elif method == "primary_only":
            result = self._primary_only_resolution(timeframe_analyses, market_regime)
        elif method == "consensus":
            result = self._consensus_resolution(timeframe_analyses, market_regime)
        else:
            # Mặc định sử dụng weighted_average
            result = self._weighted_average_resolution(timeframe_analyses, market_regime)
        
        # Thêm thông tin về xung đột và phương pháp giải quyết
        result.update({
            "market_regime": market_regime,
            "timeframe_signals": timeframe_analyses,
            "resolution_method": method,
            "conflicts_detected": conflict_details["has_conflict"],
            "conflict_details": conflict_details
        })
        
        return result
    
    def _detect_conflicts(self, timeframe_analyses: Dict[str, Dict]) -> Dict:
        """
        Phát hiện xung đột giữa các khung thời gian
        
        Args:
            timeframe_analyses (Dict[str, Dict]): Kết quả phân tích theo từng khung thời gian
            
        Returns:
            Dict: Thông tin về xung đột
        """
        # Khởi tạo kết quả
        result = {
            "has_conflict": False,
            "conflict_type": None,
            "conflict_timeframes": [],
            "conflicting_signals": {},
            "conflict_severity": 0.0
        }
        
        # Thu thập các khuyến nghị
        recommendations = {}
        scores = {}
        
        for tf, analysis in timeframe_analyses.items():
            rec = analysis.get("recommendation", "neutral")
            score = analysis.get("score", 50)
            
            recommendations[tf] = rec
            scores[tf] = score
        
        # Nhóm các khuyến nghị
        recommendation_groups = {}
        for tf, rec in recommendations.items():
            if rec not in recommendation_groups:
                recommendation_groups[rec] = []
            recommendation_groups[rec].append(tf)
        
        # Kiểm tra xung đột
        if len(recommendation_groups) > 1:
            # Có ít nhất 2 loại khuyến nghị khác nhau
            result["has_conflict"] = True
            
            # Xác định loại xung đột
            directions = set()
            for rec in recommendation_groups.keys():
                if rec in ["buy", "strong_buy"]:
                    directions.add("buy")
                elif rec in ["sell", "strong_sell"]:
                    directions.add("sell")
                else:
                    directions.add("neutral")
            
            if len(directions) > 1:
                if "buy" in directions and "sell" in directions:
                    result["conflict_type"] = "direction_conflict"
                else:
                    result["conflict_type"] = "strength_conflict"
            
            # Tìm các khung thời gian xung đột
            for rec, tfs in recommendation_groups.items():
                for tf in tfs:
                    result["conflicting_signals"][tf] = {
                        "recommendation": rec,
                        "score": scores[tf]
                    }
            
            # Tính mức độ nghiêm trọng của xung đột
            if result["conflict_type"] == "direction_conflict":
                # Xung đột hướng (buy vs sell) là nghiêm trọng nhất
                result["conflict_severity"] = 1.0
            elif result["conflict_type"] == "strength_conflict":
                # Xung đột cường độ (buy vs strong_buy hoặc neutral vs buy)
                # Tính dựa trên khoảng cách giữa các điểm số
                min_score = min(scores.values())
                max_score = max(scores.values())
                score_range = max_score - min_score
                
                result["conflict_severity"] = min(1.0, score_range / 50.0)
        
        return result
    
    def _weighted_average_resolution(self, timeframe_analyses: Dict[str, Dict], market_regime: str) -> Dict:
        """
        Giải quyết xung đột bằng phương pháp trung bình có trọng số
        
        Args:
            timeframe_analyses (Dict[str, Dict]): Kết quả phân tích theo từng khung thời gian
            market_regime (str): Chế độ thị trường
            
        Returns:
            Dict: Kết quả tích hợp
        """
        # Lấy trọng số theo chế độ thị trường
        weights = self.config["timeframe_weights"]["by_market_regime"].get(
            market_regime, self.config["timeframe_weights"]["default"])
        
        # Tính điểm trung bình có trọng số
        weighted_sum = 0
        total_weight = 0
        
        weighted_scores = {}
        
        for tf, analysis in timeframe_analyses.items():
            score = analysis.get("score", 50)
            weight = weights.get(tf, 0.1)  # Mặc định 0.1 nếu không có trọng số
            
            weighted_sum += score * weight
            total_weight += weight
            
            weighted_scores[tf] = score * weight
        
        # Tính điểm trung bình
        if total_weight > 0:
            avg_score = weighted_sum / total_weight
        else:
            avg_score = 50  # Mặc định neutral
        
        # Xác định khuyến nghị từ điểm trung bình
        if avg_score >= 80:
            recommendation = "strong_buy"
        elif avg_score >= 60:
            recommendation = "buy"
        elif avg_score >= 40:
            recommendation = "neutral"
        elif avg_score >= 20:
            recommendation = "sell"
        else:
            recommendation = "strong_sell"
        
        # Tìm khung thời gian có ảnh hưởng lớn nhất
        primary_tf = max(weighted_scores.items(), key=lambda x: x[1])[0]
        
        # Tính độ tin cậy
        conflict_details = self._detect_conflicts(timeframe_analyses)
        confidence = 1.0 - conflict_details["conflict_severity"]
        
        return {
            "recommendation": recommendation,
            "score": avg_score,
            "primary_timeframe": primary_tf,
            "weighted_scores": weighted_scores,
            "confidence": confidence
        }
    
    def _majority_vote_resolution(self, timeframe_analyses: Dict[str, Dict], market_regime: str) -> Dict:
        """
        Giải quyết xung đột bằng phương pháp biểu quyết đa số
        
        Args:
            timeframe_analyses (Dict[str, Dict]): Kết quả phân tích theo từng khung thời gian
            market_regime (str): Chế độ thị trường
            
        Returns:
            Dict: Kết quả tích hợp
        """
        # Đếm số khuyến nghị theo loại
        rec_counts = {}
        sum_score = {}
        count_by_rec = {}
        
        for tf, analysis in timeframe_analyses.items():
            rec = analysis.get("recommendation", "neutral")
            score = analysis.get("score", 50)
            
            if rec not in rec_counts:
                rec_counts[rec] = 0
                sum_score[rec] = 0
                count_by_rec[rec] = 0
            
            rec_counts[rec] += 1
            sum_score[rec] += score
            count_by_rec[rec] += 1
        
        # Tìm khuyến nghị có phiếu bầu nhiều nhất
        if not rec_counts:
            recommendation = "neutral"
            avg_score = 50
        else:
            # Kiểm tra trường hợp hòa
            max_count = max(rec_counts.values())
            max_recs = [rec for rec, count in rec_counts.items() if count == max_count]
            
            if len(max_recs) > 1:
                # Xử lý trường hợp hòa
                recommendation = self._resolve_majority_vote_tie(max_recs, timeframe_analyses, market_regime)
            else:
                recommendation = max_recs[0]
            
            # Tính điểm trung bình của khuyến nghị được chọn
            if recommendation in sum_score and count_by_rec[recommendation] > 0:
                avg_score = sum_score[recommendation] / count_by_rec[recommendation]
            else:
                avg_score = 50
        
        # Xác định khung thời gian chính
        primary_tf = self.config["primary_timeframes"]["by_market_regime"].get(
            market_regime, self.config["primary_timeframes"]["default"])
        
        # Tính độ tin cậy
        max_possible_votes = len(timeframe_analyses)
        if max_possible_votes > 0:
            confidence = rec_counts.get(recommendation, 0) / max_possible_votes
        else:
            confidence = 0.5
        
        return {
            "recommendation": recommendation,
            "score": avg_score,
            "primary_timeframe": primary_tf,
            "vote_counts": rec_counts,
            "confidence": confidence
        }
    
    def _resolve_majority_vote_tie(self, tied_recommendations: List[str], 
                                  timeframe_analyses: Dict[str, Dict],
                                  market_regime: str) -> str:
        """
        Giải quyết trường hợp hòa trong biểu quyết đa số
        
        Args:
            tied_recommendations (List[str]): Danh sách các khuyến nghị bị hòa
            timeframe_analyses (Dict[str, Dict]): Kết quả phân tích theo từng khung thời gian
            market_regime (str): Chế độ thị trường
            
        Returns:
            str: Khuyến nghị được chọn
        """
        # Lấy quy tắc xử lý hòa
        tie_rules = self.config["tie_breaking_rules"]
        
        # Ưu tiên an toàn
        if tie_rules.get("safety_first", True):
            safety_order = tie_rules.get("safety_order", ["neutral", "buy", "strong_buy", "sell", "strong_sell"])
            for rec in safety_order:
                if rec in tied_recommendations:
                    return rec
        
        # Ưu tiên khung thời gian lớn hơn
        if tie_rules.get("prefer_higher_timeframe", True):
            # Sắp xếp khung thời gian theo thứ tự giảm dần
            timeframe_order = ["1d", "4h", "1h", "30m", "15m", "5m", "1m"]
            
            # Lọc các khung thời gian có khuyến nghị trong danh sách hòa
            relevant_tfs = {}
            for tf, analysis in timeframe_analyses.items():
                rec = analysis.get("recommendation", "neutral")
                if rec in tied_recommendations:
                    relevant_tfs[tf] = rec
            
            # Tìm khung thời gian lớn nhất
            for tf in timeframe_order:
                if tf in relevant_tfs:
                    return relevant_tfs[tf]
        
        # Sử dụng khung thời gian chính theo chế độ thị trường
        primary_tf = self.config["primary_timeframes"]["by_market_regime"].get(
            market_regime, self.config["primary_timeframes"]["default"])
        
        if primary_tf in timeframe_analyses:
            return timeframe_analyses[primary_tf].get("recommendation", "neutral")
        
        # Nếu mọi cách đều thất bại, trả về neutral để an toàn
        return "neutral"
    
    def _primary_only_resolution(self, timeframe_analyses: Dict[str, Dict], market_regime: str) -> Dict:
        """
        Giải quyết xung đột bằng cách chỉ sử dụng khung thời gian chính
        
        Args:
            timeframe_analyses (Dict[str, Dict]): Kết quả phân tích theo từng khung thời gian
            market_regime (str): Chế độ thị trường
            
        Returns:
            Dict: Kết quả tích hợp
        """
        # Xác định khung thời gian chính
        primary_tf = self.config["primary_timeframes"]["by_market_regime"].get(
            market_regime, self.config["primary_timeframes"]["default"])
        
        # Kiểm tra xem khung thời gian chính có trong dữ liệu không
        if primary_tf not in timeframe_analyses:
            # Nếu không có, sử dụng khung thời gian lớn nhất
            timeframe_order = ["1d", "4h", "1h", "30m", "15m", "5m", "1m"]
            for tf in timeframe_order:
                if tf in timeframe_analyses:
                    primary_tf = tf
                    break
            else:
                # Nếu không tìm thấy khung thời gian nào, sử dụng khung thời gian đầu tiên
                primary_tf = list(timeframe_analyses.keys())[0]
        
        # Lấy kết quả phân tích từ khung thời gian chính
        analysis = timeframe_analyses[primary_tf]
        recommendation = analysis.get("recommendation", "neutral")
        score = analysis.get("score", 50)
        
        # Độ tin cậy giảm khi có xung đột
        conflict_details = self._detect_conflicts(timeframe_analyses)
        
        # Điều chỉnh độ tin cậy dựa trên mức độ nghiêm trọng của xung đột
        if conflict_details["has_conflict"]:
            confidence = 0.8 - 0.3 * conflict_details["conflict_severity"]
        else:
            confidence = 1.0
        
        return {
            "recommendation": recommendation,
            "score": score,
            "primary_timeframe": primary_tf,
            "confidence": confidence
        }
    
    def _consensus_resolution(self, timeframe_analyses: Dict[str, Dict], market_regime: str) -> Dict:
        """
        Giải quyết xung đột bằng phương pháp đồng thuận
        
        Args:
            timeframe_analyses (Dict[str, Dict]): Kết quả phân tích theo từng khung thời gian
            market_regime (str): Chế độ thị trường
            
        Returns:
            Dict: Kết quả tích hợp
        """
        # Lấy cài đặt đồng thuận
        consensus_settings = self.config["consensus"]
        required_agreement = consensus_settings.get("required_agreement", 0.66)
        minimum_timeframes = consensus_settings.get("minimum_timeframes", 3)
        neutral_threshold = consensus_settings.get("neutral_threshold", 0.5)
        strong_consensus_boost = consensus_settings.get("strong_consensus_boost", 0.1)
        
        # Yêu cầu ít nhất số lượng khung thời gian tối thiểu
        if len(timeframe_analyses) < minimum_timeframes:
            return self._weighted_average_resolution(timeframe_analyses, market_regime)
        
        # Đếm số khuyến nghị theo loại
        rec_counts = {}
        direction_counts = {"buy": 0, "neutral": 0, "sell": 0}
        
        for tf, analysis in timeframe_analyses.items():
            rec = analysis.get("recommendation", "neutral")
            
            if rec not in rec_counts:
                rec_counts[rec] = 0
            rec_counts[rec] += 1
            
            # Đếm theo hướng
            if rec in ["buy", "strong_buy"]:
                direction_counts["buy"] += 1
            elif rec in ["sell", "strong_sell"]:
                direction_counts["sell"] += 1
            else:
                direction_counts["neutral"] += 1
        
        total_timeframes = len(timeframe_analyses)
        
        # Kiểm tra đồng thuận theo hướng
        max_direction = max(direction_counts.items(), key=lambda x: x[1])
        direction_ratio = max_direction[1] / total_timeframes
        
        # Nếu không đạt được đồng thuận đủ mạnh, trả về neutral
        if direction_ratio < required_agreement:
            # Kiểm tra xem có nhiều xung đột không
            if direction_counts["buy"] > 0 and direction_counts["sell"] > 0:
                conflict_ratio = min(direction_counts["buy"], direction_counts["sell"]) / total_timeframes
                
                # Nếu mức độ xung đột cao, trả về neutral
                if conflict_ratio >= neutral_threshold:
                    return {
                        "recommendation": "neutral",
                        "score": 50,
                        "primary_timeframe": self.config["primary_timeframes"]["by_market_regime"].get(
                            market_regime, self.config["primary_timeframes"]["default"]),
                        "consensus_ratio": direction_ratio,
                        "confidence": 0.5
                    }
            
            # Nếu không đạt đủ đồng thuận nhưng không xung đột mạnh, sử dụng weighted_average
            return self._weighted_average_resolution(timeframe_analyses, market_regime)
        
        # Có đồng thuận đủ mạnh
        direction = max_direction[0]  # buy, neutral hoặc sell
        
        # Tính điểm trung bình cho các khuyến nghị thuộc hướng này
        scores_in_direction = []
        
        for tf, analysis in timeframe_analyses.items():
            rec = analysis.get("recommendation", "neutral")
            score = analysis.get("score", 50)
            
            if (direction == "buy" and rec in ["buy", "strong_buy"]) or \
               (direction == "sell" and rec in ["sell", "strong_sell"]) or \
               (direction == "neutral" and rec == "neutral"):
                scores_in_direction.append(score)
        
        avg_score = sum(scores_in_direction) / len(scores_in_direction) if scores_in_direction else 50
        
        # Điều chỉnh điểm theo hướng
        if direction == "buy":
            # Kiểm tra xem có nên là strong_buy hay không
            if avg_score >= 75 or "strong_buy" in rec_counts and rec_counts.get("strong_buy", 0) > rec_counts.get("buy", 0):
                recommendation = "strong_buy"
                # Điều chỉnh điểm cho strong_buy
                avg_score = max(80, avg_score)
            else:
                recommendation = "buy"
                # Điều chỉnh điểm cho buy
                avg_score = max(60, min(79, avg_score))
        elif direction == "sell":
            # Kiểm tra xem có nên là strong_sell hay không
            if avg_score <= 25 or "strong_sell" in rec_counts and rec_counts.get("strong_sell", 0) > rec_counts.get("sell", 0):
                recommendation = "strong_sell"
                # Điều chỉnh điểm cho strong_sell
                avg_score = min(20, avg_score)
            else:
                recommendation = "sell"
                # Điều chỉnh điểm cho sell
                avg_score = max(21, min(40, avg_score))
        else:
            recommendation = "neutral"
            # Điều chỉnh điểm cho neutral
            avg_score = max(40, min(60, avg_score))
        
        # Tính độ tin cậy
        confidence = direction_ratio
        
        # Tăng cường độ tin cậy nếu có đồng thuận mạnh
        if direction_ratio >= 0.8:
            confidence += strong_consensus_boost
        
        # Giới hạn độ tin cậy
        confidence = min(1.0, confidence)
        
        return {
            "recommendation": recommendation,
            "score": avg_score,
            "primary_timeframe": self.config["primary_timeframes"]["by_market_regime"].get(
                market_regime, self.config["primary_timeframes"]["default"]),
            "consensus_ratio": direction_ratio,
            "confidence": confidence
        }

def main():
    """Hàm chính để test module"""
    
    try:
        # Khởi tạo
        resolver = MultiTimeframeConflictResolver()
        
        # Test với các khung thời gian khác nhau
        print("=== Test xung đột nhẹ ===")
        timeframe_analyses = {
            "5m": {"recommendation": "buy", "score": 65},
            "15m": {"recommendation": "buy", "score": 70},
            "1h": {"recommendation": "strong_buy", "score": 85},
            "4h": {"recommendation": "buy", "score": 75}
        }
        
        result = resolver.resolve_conflicts(timeframe_analyses, market_regime="trending")
        
        print(f"Khuyến nghị: {result['recommendation']}")
        print(f"Điểm: {result['score']:.2f}")
        print(f"Phương pháp: {result['resolution_method']}")
        print(f"Độ tin cậy: {result['confidence']:.2f}")
        print(f"Xung đột: {result['conflicts_detected']}")
        if result['conflicts_detected']:
            print(f"Loại xung đột: {result['conflict_details']['conflict_type']}")
            print(f"Mức độ nghiêm trọng: {result['conflict_details']['conflict_severity']:.2f}")
        
        # Test với xung đột mạnh
        print("\n=== Test xung đột mạnh ===")
        timeframe_analyses = {
            "5m": {"recommendation": "buy", "score": 65},
            "15m": {"recommendation": "buy", "score": 70},
            "1h": {"recommendation": "neutral", "score": 55},
            "4h": {"recommendation": "sell", "score": 35}
        }
        
        result = resolver.resolve_conflicts(timeframe_analyses, market_regime="volatile")
        
        print(f"Khuyến nghị: {result['recommendation']}")
        print(f"Điểm: {result['score']:.2f}")
        print(f"Phương pháp: {result['resolution_method']}")
        print(f"Độ tin cậy: {result['confidence']:.2f}")
        print(f"Xung đột: {result['conflicts_detected']}")
        if result['conflicts_detected']:
            print(f"Loại xung đột: {result['conflict_details']['conflict_type']}")
            print(f"Mức độ nghiêm trọng: {result['conflict_details']['conflict_severity']:.2f}")
        
        # Test biểu quyết đa số với trường hợp hòa
        print("\n=== Test biểu quyết đa số với trường hợp hòa ===")
        timeframe_analyses = {
            "5m": {"recommendation": "buy", "score": 65},
            "15m": {"recommendation": "neutral", "score": 50},
            "1h": {"recommendation": "sell", "score": 35},
            "4h": {"recommendation": "neutral", "score": 45}
        }
        
        result = resolver.resolve_conflicts(timeframe_analyses, market_regime="ranging", method="majority_vote")
        
        print(f"Khuyến nghị: {result['recommendation']}")
        print(f"Điểm: {result['score']:.2f}")
        print(f"Phương pháp: {result['resolution_method']}")
        print(f"Độ tin cậy: {result['confidence']:.2f}")
        print(f"Số phiếu: {result['vote_counts']}")
        
        # Test đồng thuận
        print("\n=== Test đồng thuận ===")
        timeframe_analyses = {
            "5m": {"recommendation": "buy", "score": 65},
            "15m": {"recommendation": "buy", "score": 70},
            "1h": {"recommendation": "buy", "score": 75},
            "4h": {"recommendation": "strong_buy", "score": 85},
            "1d": {"recommendation": "buy", "score": 72}
        }
        
        result = resolver.resolve_conflicts(timeframe_analyses, market_regime="quiet", method="consensus")
        
        print(f"Khuyến nghị: {result['recommendation']}")
        print(f"Điểm: {result['score']:.2f}")
        print(f"Phương pháp: {result['resolution_method']}")
        print(f"Độ tin cậy: {result['confidence']:.2f}")
        print(f"Tỷ lệ đồng thuận: {result['consensus_ratio']:.2f}")
        
    except Exception as e:
        logger.error(f"Lỗi khi chạy test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()