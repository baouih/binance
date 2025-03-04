#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Routes cho Crypto Mood Meter

Module này cung cấp các routes Flask để hiển thị và tương tác với
Crypto Mood Meter, một công cụ phân tích cảm xúc thị trường.
"""

import os
import json
import logging
from flask import Blueprint, jsonify, render_template, request, session, redirect, url_for

from market_sentiment_analyzer import MarketSentimentAnalyzer
from data_processor import DataProcessor

# Tạo blueprint
sentiment_bp = Blueprint('sentiment', __name__)

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Khởi tạo phân tích cảm xúc
sentiment_analyzer = MarketSentimentAnalyzer()
data_processor = DataProcessor()

@sentiment_bp.route('/mood', methods=['GET'])
def mood_meter():
    """Trang Crypto Mood Meter"""
    # Lấy dữ liệu sentiment widget
    sentiment_widget = sentiment_analyzer.get_sentiment_widget_data()
    
    # Lấy dữ liệu và chỉ báo thị trường cho BTC để phân tích
    try:
        # Lấy dữ liệu BTC
        btc_data = data_processor.get_market_data('BTCUSDT', '1h', limit=24)
        
        # Tính toán chỉ báo cho phân tích cảm xúc
        indicators = {}
        
        if btc_data is not None and len(btc_data) > 0:
            df = btc_data.copy()
            
            # Tính RSI
            if 'rsi' in df.columns:
                indicators['rsi'] = float(df['rsi'].iloc[-1])
            
            # Tính MACD
            if all(col in df.columns for col in ['macd', 'macd_signal']):
                indicators['macd_histogram'] = float(df['macd'].iloc[-1] - df['macd_signal'].iloc[-1])
            
            # Tính EMA crossover
            if all(col in df.columns for col in ['ema_short', 'ema_long']):
                current_short = df['ema_short'].iloc[-1]
                current_long = df['ema_long'].iloc[-1]
                prev_short = df['ema_short'].iloc[-2] if len(df) > 1 else None
                prev_long = df['ema_long'].iloc[-2] if len(df) > 1 else None
                
                if prev_short is not None and prev_long is not None:
                    if prev_short < prev_long and current_short > current_long:
                        indicators['ema_crossover'] = 1  # Bullish crossover
                    elif prev_short > prev_long and current_short < current_long:
                        indicators['ema_crossover'] = -1  # Bearish crossover
                    else:
                        indicators['ema_crossover'] = 0  # No crossover
            
            # Bollinger Bands position
            if all(col in df.columns for col in ['bb_upper', 'bb_lower']):
                close = df['close'].iloc[-1]
                bb_upper = df['bb_upper'].iloc[-1]
                bb_lower = df['bb_lower'].iloc[-1]
                
                bb_range = bb_upper - bb_lower
                if bb_range > 0:
                    indicators['bb_position'] = (close - bb_lower) / bb_range
                else:
                    indicators['bb_position'] = 0.5
            
            # ADX (Average Directional Index)
            if 'adx' in df.columns:
                indicators['adx'] = float(df['adx'].iloc[-1])
            
            # Volume change
            if 'volume' in df.columns and len(df) > 1:
                current_vol = df['volume'].iloc[-1]
                prev_vol = df['volume'].iloc[-2]
                if prev_vol > 0:
                    indicators['volume_change'] = ((current_vol - prev_vol) / prev_vol) * 100
            
            # 24h price change
            if len(df) >= 24:
                current_price = df['close'].iloc[-1]
                prev_price = df['close'].iloc[-24]
                if prev_price > 0:
                    indicators['price_change_24h'] = ((current_price - prev_price) / prev_price) * 100
        
        # Cập nhật cảm xúc thị trường
        if indicators:
            sentiment_analyzer.update_market_sentiment(indicators)
            sentiment_widget = sentiment_analyzer.get_sentiment_widget_data()
    
    except Exception as e:
        logger.error(f"Lỗi khi tính toán chỉ báo cho cảm xúc thị trường: {e}")
    
    return render_template('sentiment.html', widget=sentiment_widget)

@sentiment_bp.route('/api/sentiment', methods=['GET'])
def get_sentiment_data():
    """API endpoint trả về dữ liệu cảm xúc thị trường"""
    try:
        sentiment_data = sentiment_analyzer.get_sentiment_widget_data()
        return jsonify(sentiment_data)
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu cảm xúc thị trường: {e}")
        return jsonify({'error': str(e)}), 500

@sentiment_bp.route('/api/sentiment/trend', methods=['GET'])
def get_sentiment_trend():
    """API endpoint trả về xu hướng cảm xúc thị trường"""
    try:
        hours = request.args.get('hours', 24, type=int)
        trend_data = sentiment_analyzer.get_sentiment_trend(lookback_hours=hours)
        return jsonify(trend_data)
    except Exception as e:
        logger.error(f"Lỗi khi lấy xu hướng cảm xúc thị trường: {e}")
        return jsonify({'error': str(e)}), 500

@sentiment_bp.route('/api/sentiment/history', methods=['GET'])
def get_sentiment_history():
    """API endpoint trả về lịch sử cảm xúc thị trường"""
    try:
        limit = request.args.get('limit', 100, type=int)
        history = sentiment_analyzer.sentiment_data.get('historical_data', [])[-limit:]
        
        # Chuyển đổi định dạng để dễ vẽ biểu đồ
        formatted_history = []
        for entry in history:
            formatted_history.append({
                'timestamp': entry.get('timestamp', ''),
                'score': entry.get('score', 0),
                'level': entry.get('level', 'neutral'),
                'emoji': entry.get('emoji', '😐')
            })
            
        return jsonify(formatted_history)
    except Exception as e:
        logger.error(f"Lỗi khi lấy lịch sử cảm xúc thị trường: {e}")
        return jsonify({'error': str(e)}), 500

def register_blueprint(app):
    """Đăng ký blueprint với ứng dụng Flask"""
    app.register_blueprint(sentiment_bp, url_prefix='/sentiment')