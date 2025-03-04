#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module phân tích cảm xúc thị trường (Market Sentiment Analyzer)

Module này phân tích cảm xúc thị trường dựa trên nhiều nguồn dữ liệu và
chỉ số kỹ thuật, tạo ra một chỉ số cảm xúc tổng hợp và biểu thị trực quan
bằng emoji.
"""

import os
import json
import logging
import math
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MarketSentimentAnalyzer:
    """Lớp phân tích cảm xúc thị trường"""
    
    # Định nghĩa các mức cảm xúc thị trường và emoji tương ứng
    SENTIMENT_LEVELS = {
        'extremely_bearish': {'emoji': '🧸', 'color': '#e74c3c', 'description': 'Cực kỳ tiêu cực'},
        'bearish': {'emoji': '🐻', 'color': '#e67e22', 'description': 'Tiêu cực'},
        'slightly_bearish': {'emoji': '😟', 'color': '#f1c40f', 'description': 'Hơi tiêu cực'},
        'neutral': {'emoji': '😐', 'color': '#95a5a6', 'description': 'Trung tính'},
        'slightly_bullish': {'emoji': '🙂', 'color': '#3498db', 'description': 'Hơi tích cực'},
        'bullish': {'emoji': '🐂', 'color': '#2ecc71', 'description': 'Tích cực'},
        'extremely_bullish': {'emoji': '🚀', 'color': '#27ae60', 'description': 'Cực kỳ tích cực'}
    }
    
    # Đường dẫn lưu dữ liệu cảm xúc
    SENTIMENT_DATA_PATH = 'data/market_sentiment.json'
    
    def __init__(self, data_path: str = None):
        """
        Khởi tạo trình phân tích cảm xúc thị trường
        
        Args:
            data_path (str, optional): Đường dẫn lưu dữ liệu cảm xúc
        """
        self.data_path = data_path or self.SENTIMENT_DATA_PATH
        self.sentiment_data = self._load_or_create_default()
        
        # Đảm bảo thư mục chứa data_path tồn tại
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        
        logger.info(f"Đã khởi tạo MarketSentimentAnalyzer, sử dụng file: {self.data_path}")
    
    def _load_or_create_default(self) -> Dict:
        """
        Tải dữ liệu cảm xúc hoặc tạo mới nếu không tồn tại
        
        Returns:
            Dict: Dữ liệu cảm xúc
        """
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)
                logger.info(f"Đã tải dữ liệu cảm xúc từ {self.data_path}")
                return data
            except Exception as e:
                logger.error(f"Lỗi khi tải dữ liệu cảm xúc: {e}")
        
        # Tạo dữ liệu mặc định
        default_data = {
            "current_sentiment": {
                "level": "neutral",
                "score": 0.0,
                "components": {},
                "emoji": self.SENTIMENT_LEVELS["neutral"]["emoji"],
                "color": self.SENTIMENT_LEVELS["neutral"]["color"],
                "description": self.SENTIMENT_LEVELS["neutral"]["description"],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "historical_data": [],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "metadata": {
                "version": "1.0",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        
        # Lưu dữ liệu mặc định
        try:
            with open(self.data_path, 'w') as f:
                json.dump(default_data, f, indent=4)
            logger.info(f"Đã tạo dữ liệu cảm xúc mặc định và lưu vào {self.data_path}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu cảm xúc mặc định: {e}")
        
        return default_data
    
    def _save_sentiment_data(self) -> bool:
        """
        Lưu dữ liệu cảm xúc vào file
        
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        try:
            self.sentiment_data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(self.data_path, 'w') as f:
                json.dump(self.sentiment_data, f, indent=4)
            logger.info(f"Đã lưu dữ liệu cảm xúc vào {self.data_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu cảm xúc: {e}")
            return False
    
    def analyze_technical_indicators(self, market_data: Dict) -> Dict:
        """
        Phân tích cảm xúc thị trường dựa trên chỉ báo kỹ thuật
        
        Args:
            market_data (Dict): Dữ liệu thị trường cần phân tích
                {
                    'rsi': float,
                    'macd_histogram': float,
                    'ema_crossover': int, # 1: bullish, -1: bearish, 0: neutral
                    'bb_position': float, # 0-1, vị trí giá trong dải Bollinger
                    'adx': float,
                    'volume_change': float,
                    'price_change_24h': float
                }
                
        Returns:
            Dict: Kết quả phân tích cảm xúc
        """
        components = {}
        
        # Phân tích RSI (Relative Strength Index)
        if 'rsi' in market_data:
            rsi = market_data['rsi']
            if rsi < 30:
                components['rsi'] = {'score': -0.5 + (rsi - 20) / 20, 'description': f'RSI quá bán ({rsi:.1f})'}
            elif rsi > 70:
                components['rsi'] = {'score': 0.5 + (rsi - 70) / 60, 'description': f'RSI quá mua ({rsi:.1f})'}
            else:
                # Chuẩn hóa RSI từ 30-70 thành -0.5 đến 0.5
                components['rsi'] = {'score': (rsi - 50) / 40, 'description': f'RSI = {rsi:.1f}'}
        
        # Phân tích MACD
        if 'macd_histogram' in market_data:
            macd_hist = market_data['macd_histogram']
            # Chuẩn hóa MACD histogram
            macd_score = np.tanh(macd_hist * 2)  # Squish -1 to 1
            components['macd'] = {'score': macd_score, 'description': f'MACD Hist = {macd_hist:.4f}'}
        
        # Phân tích EMA Crossover
        if 'ema_crossover' in market_data:
            ema_cross = market_data['ema_crossover']
            if ema_cross == 1:
                components['ema'] = {'score': 0.7, 'description': 'EMA cắt lên (bullish)'}
            elif ema_cross == -1:
                components['ema'] = {'score': -0.7, 'description': 'EMA cắt xuống (bearish)'}
            else:
                components['ema'] = {'score': 0, 'description': 'EMA không cắt nhau'}
        
        # Phân tích Bollinger Bands
        if 'bb_position' in market_data:
            bb_pos = market_data['bb_position']
            # 0 = dưới band dưới, 0.5 = giữa, 1 = trên band trên
            bb_score = (bb_pos - 0.5) * 2  # Chuyển thành -1 đến 1
            components['bollinger'] = {'score': bb_score, 'description': f'BB Position = {bb_pos:.2f}'}
        
        # Phân tích ADX (Trend Strength)
        if 'adx' in market_data:
            adx = market_data['adx']
            if adx > 25:
                # ADX cao = xu hướng mạnh, nhưng cần biết hướng từ các chỉ báo khác
                adx_contribution = (adx - 25) / 75  # 0 to 1 scaling
                components['adx'] = {'score': 0, 'description': f'ADX = {adx:.1f} (xu hướng mạnh)'}
            else:
                components['adx'] = {'score': 0, 'description': f'ADX = {adx:.1f} (không xu hướng rõ ràng)'}
        
        # Phân tích biến động khối lượng
        if 'volume_change' in market_data:
            vol_change = market_data['volume_change']
            vol_score = np.tanh(vol_change / 50)  # Squish to -1 to 1
            components['volume'] = {'score': vol_score, 'description': f'Volume change = {vol_change:.1f}%'}
        
        # Phân tích biến động giá 24h
        if 'price_change_24h' in market_data:
            price_change = market_data['price_change_24h']
            price_score = np.tanh(price_change / 10)  # Squish to -1 to 1
            components['price_change'] = {'score': price_score, 'description': f'24h change = {price_change:.2f}%'}
        
        # Tính điểm tổng hợp
        weights = {
            'rsi': 0.2,
            'macd': 0.2, 
            'ema': 0.15,
            'bollinger': 0.1,
            'adx': 0.05,
            'volume': 0.1,
            'price_change': 0.2
        }
        
        total_score = 0
        total_weight = 0
        
        for component, details in components.items():
            component_weight = weights.get(component, 0.1)
            total_score += details['score'] * component_weight
            total_weight += component_weight
        
        # Chuẩn hóa lại nếu không đủ tất cả các thành phần
        if total_weight > 0:
            final_score = total_score / total_weight
        else:
            final_score = 0
        
        # Giới hạn điểm trong khoảng -1 đến 1
        final_score = max(min(final_score, 1.0), -1.0)
        
        # Xác định mức cảm xúc
        sentiment_level = self._determine_sentiment_level(final_score)
        
        # Tạo kết quả
        result = {
            'score': final_score,
            'level': sentiment_level,
            'components': components,
            'emoji': self.SENTIMENT_LEVELS[sentiment_level]['emoji'],
            'color': self.SENTIMENT_LEVELS[sentiment_level]['color'],
            'description': self.SENTIMENT_LEVELS[sentiment_level]['description'],
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return result
    
    def _determine_sentiment_level(self, score: float) -> str:
        """
        Xác định mức cảm xúc dựa trên điểm
        
        Args:
            score (float): Điểm cảm xúc (-1 đến 1)
            
        Returns:
            str: Mức cảm xúc
        """
        if score < -0.75:
            return 'extremely_bearish'
        elif score < -0.35:
            return 'bearish'
        elif score < -0.1:
            return 'slightly_bearish'
        elif score < 0.1:
            return 'neutral'
        elif score < 0.35:
            return 'slightly_bullish'
        elif score < 0.75:
            return 'bullish'
        else:
            return 'extremely_bullish'
    
    def update_market_sentiment(self, market_data: Dict) -> Dict:
        """
        Cập nhật cảm xúc thị trường
        
        Args:
            market_data (Dict): Dữ liệu thị trường
            
        Returns:
            Dict: Cảm xúc thị trường hiện tại
        """
        # Phân tích cảm xúc từ chỉ báo kỹ thuật
        technical_sentiment = self.analyze_technical_indicators(market_data)
        
        # Lưu cảm xúc hiện tại
        current_sentiment = {
            'level': technical_sentiment['level'],
            'score': technical_sentiment['score'],
            'components': technical_sentiment['components'],
            'emoji': technical_sentiment['emoji'],
            'color': technical_sentiment['color'],
            'description': technical_sentiment['description'],
            'timestamp': technical_sentiment['timestamp']
        }
        
        # Lưu vào dữ liệu lịch sử
        historical_entry = current_sentiment.copy()
        self.sentiment_data['historical_data'].append(historical_entry)
        
        # Giới hạn lịch sử, chỉ giữ 100 mục gần nhất
        if len(self.sentiment_data['historical_data']) > 100:
            self.sentiment_data['historical_data'] = self.sentiment_data['historical_data'][-100:]
        
        # Cập nhật cảm xúc hiện tại
        self.sentiment_data['current_sentiment'] = current_sentiment
        
        # Lưu dữ liệu
        self._save_sentiment_data()
        
        return current_sentiment
    
    def get_current_sentiment(self) -> Dict:
        """
        Lấy cảm xúc thị trường hiện tại
        
        Returns:
            Dict: Cảm xúc thị trường hiện tại
        """
        return self.sentiment_data['current_sentiment']
    
    def get_sentiment_trend(self, lookback_hours: int = 24) -> Dict:
        """
        Lấy xu hướng cảm xúc thị trường
        
        Args:
            lookback_hours (int): Số giờ để nhìn lại
            
        Returns:
            Dict: Xu hướng cảm xúc thị trường
        """
        # Lọc dữ liệu lịch sử trong khoảng thời gian
        lookback_time = datetime.now() - timedelta(hours=lookback_hours)
        historical_data = self.sentiment_data['historical_data']
        
        recent_sentiment = []
        for entry in reversed(historical_data):
            try:
                entry_time = datetime.strptime(entry['timestamp'], "%Y-%m-%d %H:%M:%S")
                if entry_time >= lookback_time:
                    recent_sentiment.append(entry)
                else:
                    break
            except Exception:
                continue
        
        # Đảo ngược lại để theo thứ tự thời gian
        recent_sentiment.reverse()
        
        # Tính toán sự thay đổi
        if not recent_sentiment:
            change = 0
        elif len(recent_sentiment) == 1:
            change = 0
        else:
            first_score = recent_sentiment[0]['score']
            last_score = recent_sentiment[-1]['score']
            change = last_score - first_score
        
        # Phân loại xu hướng
        if change > 0.5:
            trend = "strong_positive"
            description = "Cảm xúc cải thiện mạnh"
            emoji = "📈"
        elif change > 0.2:
            trend = "positive"
            description = "Cảm xúc cải thiện"
            emoji = "⬆️"
        elif change > -0.2:
            trend = "neutral"
            description = "Cảm xúc ổn định"
            emoji = "➡️"
        elif change > -0.5:
            trend = "negative"
            description = "Cảm xúc xấu đi"
            emoji = "⬇️"
        else:
            trend = "strong_negative"
            description = "Cảm xúc xấu đi mạnh"
            emoji = "📉"
        
        return {
            'trend': trend,
            'change': change,
            'description': description,
            'emoji': emoji,
            'data_points': len(recent_sentiment),
            'start_sentiment': recent_sentiment[0] if recent_sentiment else None,
            'end_sentiment': recent_sentiment[-1] if recent_sentiment else None
        }
    
    def get_sentiment_widget_data(self) -> Dict:
        """
        Lấy dữ liệu cho widget cảm xúc thị trường
        
        Returns:
            Dict: Dữ liệu widget
        """
        current = self.get_current_sentiment()
        trend = self.get_sentiment_trend(24)
        
        sentiment_widget = {
            'current': {
                'level': current['level'],
                'score': current['score'],
                'emoji': current['emoji'],
                'color': current['color'],
                'description': current['description']
            },
            'trend': {
                'direction': trend['trend'],
                'emoji': trend['emoji'],
                'description': trend['description'],
                'change': trend['change']
            },
            'timestamp': current['timestamp'],
            'components': {name: details['description'] for name, details in current.get('components', {}).items()},
            'insights': self._generate_sentiment_insights(current, trend)
        }
        
        return sentiment_widget
    
    def _generate_sentiment_insights(self, current: Dict, trend: Dict) -> List[str]:
        """
        Tạo insights từ dữ liệu cảm xúc
        
        Args:
            current (Dict): Cảm xúc hiện tại
            trend (Dict): Xu hướng cảm xúc
            
        Returns:
            List[str]: Danh sách insights
        """
        insights = []
        
        # Tạo insights dựa trên mức cảm xúc hiện tại
        if current['level'] in ['extremely_bullish', 'bullish']:
            insights.append("Thị trường đang lạc quan, thận trọng với FOMO (sợ bỏ lỡ)")
        elif current['level'] in ['extremely_bearish', 'bearish']:
            insights.append("Thị trường đang bi quan, cẩn thận với sự hoảng loạn bán tháo")
        
        # Tạo insights dựa trên xu hướng
        if trend['trend'] == 'strong_positive' and current['level'] in ['slightly_bearish', 'bearish', 'extremely_bearish']:
            insights.append("Thị trường đang cải thiện mạnh từ vùng tiêu cực, có thể là dấu hiệu đảo chiều")
        elif trend['trend'] == 'strong_negative' and current['level'] in ['slightly_bullish', 'bullish', 'extremely_bullish']:
            insights.append("Thị trường đang xấu đi nhanh từ vùng tích cực, cân nhắc bảo vệ lợi nhuận")
        
        # Insights từ các components
        if 'components' in current:
            components = current.get('components', {})
            # RSI Insights
            if 'rsi' in components and components['rsi']['score'] < -0.4:
                insights.append("RSI cho thấy thị trường quá bán, có thể cân nhắc mua vào")
            elif 'rsi' in components and components['rsi']['score'] > 0.4:
                insights.append("RSI cho thấy thị trường quá mua, thận trọng khi mua mới")
                
            # MACD Insights
            if 'macd' in components and 'ema' in components:
                if components['macd']['score'] > 0.3 and components['ema']['score'] > 0.3:
                    insights.append("MACD và EMA đều tích cực, xác nhận xu hướng tăng")
                elif components['macd']['score'] < -0.3 and components['ema']['score'] < -0.3:
                    insights.append("MACD và EMA đều tiêu cực, xác nhận xu hướng giảm")
        
        # Giới hạn số lượng insights
        if not insights:
            insights.append("Thị trường không có tín hiệu rõ ràng, cân nhắc chiến lược trung tính")
            
        return insights[:3]  # Chỉ trả về tối đa 3 insights

def main():
    """Hàm chính để test và demo MarketSentimentAnalyzer"""
    sentiment_analyzer = MarketSentimentAnalyzer()
    
    # Tạo dữ liệu thị trường mẫu
    sample_market_data = {
        'rsi': 62.5,
        'macd_histogram': 0.0025,
        'ema_crossover': 1,  # Bullish
        'bb_position': 0.75,  # Gần band trên
        'adx': 30.0,
        'volume_change': 15.0,
        'price_change_24h': 2.5
    }
    
    # Cập nhật cảm xúc thị trường
    sentiment = sentiment_analyzer.update_market_sentiment(sample_market_data)
    
    # In kết quả
    print("=== CẢM XÚC THỊ TRƯỜNG ===")
    print(f"Mức: {sentiment['level']} ({sentiment['emoji']})")
    print(f"Điểm: {sentiment['score']:.3f}")
    print(f"Mô tả: {sentiment['description']}")
    print("\n=== CHI TIẾT THÀNH PHẦN ===")
    for component, details in sentiment['components'].items():
        print(f"{component}: {details['description']} (score: {details['score']:.3f})")
    
    # Tạo dữ liệu widget
    widget_data = sentiment_analyzer.get_sentiment_widget_data()
    print("\n=== DỮ LIỆU WIDGET ===")
    print(f"Hiện tại: {widget_data['current']['emoji']} - {widget_data['current']['description']}")
    print(f"Xu hướng: {widget_data['trend']['emoji']} - {widget_data['trend']['description']}")
    print("\nInsights:")
    for insight in widget_data['insights']:
        print(f"- {insight}")

if __name__ == "__main__":
    main()