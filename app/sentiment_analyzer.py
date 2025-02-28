"""
Market Sentiment Analyzer Module
This module calculates real-time market sentiment based on various indicators
"""

import random
import logging
import time
import numpy as np
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger("sentiment_analyzer")

class SentimentAnalyzer:
    """
    Analyzes market sentiment using a combination of technical indicators,
    price movements, and simulated data for social media trends.
    """
    
    # Sentiment categories
    SENTIMENT_CATEGORIES = {
        "extremely_bearish": {"score_range": (0, 20), "color": "#d32f2f", "label": "Extremely Bearish"},
        "bearish": {"score_range": (20, 40), "color": "#f44336", "label": "Bearish"},
        "neutral": {"score_range": (40, 60), "color": "#9e9e9e", "label": "Neutral"},
        "bullish": {"score_range": (60, 80), "color": "#4caf50", "label": "Bullish"},
        "extremely_bullish": {"score_range": (80, 100), "color": "#2e7d32", "label": "Extremely Bullish"}
    }
    
    def __init__(self, data_processor=None, simulation_mode=True):
        """
        Initialize the sentiment analyzer
        
        Args:
            data_processor: Data processor instance for technical indicators
            simulation_mode (bool): Whether to use simulated data
        """
        self.data_processor = data_processor
        self.simulation_mode = simulation_mode
        self.sentiment_history = []
        self.max_history_size = 100  # Keep the last 100 sentiment readings
        self.last_update = None
        self.sentiment_score = 50  # Default to neutral
        self.social_sentiment = None
        self.fear_greed_index = None
        self.technical_sentiment = None
        
        # In simulation mode, let's initialize with some data
        if simulation_mode:
            self._init_simulation_data()
    
    def _init_simulation_data(self):
        """Initialize simulation data for sentiment history"""
        now = datetime.now()
        for i in range(24):  # 24 hours of simulated data
            timestamp = now - timedelta(hours=24-i)
            # Generate a score that trends from bearish to bullish over time
            base_score = 30 + (i * 1.5)  # Trend from 30 to 66
            # Add some noise
            score = min(max(base_score + random.uniform(-10, 10), 0), 100)
            
            self.sentiment_history.append({
                'timestamp': timestamp.isoformat(),
                'sentiment_score': score,
                'category': self._get_sentiment_category(score),
                'technical': random.uniform(0, 100),
                'social': random.uniform(0, 100),
                'fear_greed': random.uniform(0, 100)
            })
    
    def _get_sentiment_category(self, score):
        """Get the sentiment category based on the score"""
        for category, data in self.SENTIMENT_CATEGORIES.items():
            min_val, max_val = data["score_range"]
            if min_val <= score < max_val:
                return category
        return "neutral"  # Default fallback
    
    def _calculate_technical_sentiment(self, symbol, interval='1h'):
        """
        Calculate sentiment based on technical indicators
        Returns a score between 0-100
        """
        if not self.data_processor or self.simulation_mode:
            # In simulation mode, generate realistic-looking technical sentiment
            return random.uniform(30, 70)
            
        try:
            # Get most recent data with indicators
            df = self.data_processor.get_historical_data(symbol, interval, lookback_days=3)
            
            if df is None or df.empty:
                logger.warning("No data available for technical sentiment calculation")
                return 50  # Neutral default
            
            # Get the most recent values for key indicators
            latest = df.iloc[-1]
            
            # Combine multiple indicators to form sentiment score
            rsi_score = latest.get('RSI', 50)
            
            # MACD signal - positive or negative
            macd = latest.get('MACD', 0)
            macd_signal = latest.get('MACD_Signal', 0)
            macd_hist = latest.get('MACD_Hist', 0)
            macd_score = 50
            if macd > macd_signal:
                macd_score = 65
            elif macd < macd_signal:
                macd_score = 35
                
            # Bollinger Bands position
            bb_score = 50
            price = latest.get('close', 0)
            bb_upper = latest.get('BB_upper', 0)
            bb_lower = latest.get('BB_lower', 0)
            bb_middle = latest.get('BB_middle', 0)
            
            if bb_upper > 0:
                # Calculate percent position in the bands
                band_width = bb_upper - bb_lower
                if band_width > 0:
                    position = (price - bb_lower) / band_width
                    bb_score = position * 100
            
            # EMA relationship
            ema_score = 50
            ema9 = latest.get('EMA_9', 0)
            ema21 = latest.get('EMA_21', 0)
            
            if ema9 > ema21:
                ema_score = 70
            elif ema9 < ema21:
                ema_score = 30
            
            # Weighted average of all scores
            technical_score = (
                rsi_score * 0.25 +
                macd_score * 0.25 +
                bb_score * 0.25 +
                ema_score * 0.25
            )
            
            return min(max(technical_score, 0), 100)
        
        except Exception as e:
            logger.error(f"Error calculating technical sentiment: {str(e)}")
            return 50
    
    def _calculate_social_sentiment(self, symbol):
        """
        Calculate sentiment based on simulated social media data
        Returns a score between 0-100
        """
        # In a real implementation, this would connect to a social media sentiment API
        # or analyze recent relevant posts/comments from Twitter, Reddit, etc.
        
        # For now, generate plausible-looking social sentiment
        # with some correlation to recent price movements
        
        # Get basic movement direction from historical data
        price_trend = random.choice([-1, 1])  # -1 for down, 1 for up
        
        if self.data_processor and not self.simulation_mode:
            try:
                df = self.data_processor.get_historical_data(symbol, '1h', lookback_days=1)
                if df is not None and not df.empty and len(df) > 2:
                    # Simple price movement over the period
                    first_price = df.iloc[0]['close']
                    last_price = df.iloc[-1]['close']
                    if last_price > first_price:
                        price_trend = 1
                    else:
                        price_trend = -1
            except Exception as e:
                logger.error(f"Error getting price trend for social sentiment: {str(e)}")
        
        # Generate a sentiment score with some bias from price trend
        base_score = 50 + (price_trend * random.uniform(5, 15))
        
        # Add random variations to simulate social media volatility
        variation = random.uniform(-20, 20)
        
        social_score = base_score + variation
        return min(max(social_score, 0), 100)
    
    def _calculate_fear_greed_index(self):
        """
        Calculate a fear and greed index similar to CNN's index
        Returns a score between 0-100
        """
        # In a real implementation, this would pull data from APIs
        # or calculate based on multiple market metrics
        
        # Components of the fear and greed index:
        # 1. Market volatility
        volatility = random.uniform(0, 100)
        
        # 2. Market momentum
        momentum = random.uniform(0, 100)
        
        # 3. Market volume
        volume = random.uniform(0, 100)
        
        # 4. Put/call ratio (options)
        put_call = random.uniform(0, 100)
        
        # Calculate weighted average
        fear_greed_score = (
            volatility * 0.25 +
            momentum * 0.25 +
            volume * 0.25 +
            put_call * 0.25
        )
        
        return min(max(fear_greed_score, 0), 100)
    
    def calculate_sentiment(self, symbol='BTCUSDT'):
        """
        Calculate the overall market sentiment
        
        Args:
            symbol (str): The symbol to analyze
            
        Returns:
            dict: Sentiment data including score and category
        """
        # Check if we need to update (don't update more than once per minute)
        now = datetime.now()
        if self.last_update and (now - self.last_update).total_seconds() < 60:
            # Return the most recent sentiment if it's recent enough
            if self.sentiment_history:
                return self.sentiment_history[-1]
        
        self.last_update = now
        
        # Calculate individual sentiment components
        self.technical_sentiment = self._calculate_technical_sentiment(symbol)
        self.social_sentiment = self._calculate_social_sentiment(symbol)
        self.fear_greed_index = self._calculate_fear_greed_index()
        
        # Calculate overall sentiment score (weighted average)
        self.sentiment_score = (
            self.technical_sentiment * 0.5 +  # Technical analysis has the most weight
            self.social_sentiment * 0.3 +     # Social sentiment
            self.fear_greed_index * 0.2       # Fear & greed index
        )
        
        # Determine the sentiment category
        sentiment_category = self._get_sentiment_category(self.sentiment_score)
        
        # Create the sentiment data record
        sentiment_data = {
            'timestamp': now.isoformat(),
            'sentiment_score': self.sentiment_score,
            'category': sentiment_category,
            'technical': self.technical_sentiment,
            'social': self.social_sentiment,
            'fear_greed': self.fear_greed_index
        }
        
        # Add to history and trim if needed
        self.sentiment_history.append(sentiment_data)
        if len(self.sentiment_history) > self.max_history_size:
            self.sentiment_history = self.sentiment_history[-self.max_history_size:]
        
        logger.info(f"Sentiment calculated: {sentiment_data['sentiment_score']:.2f} ({sentiment_category})")
        return sentiment_data
    
    def get_sentiment_history(self, hours=24):
        """
        Get sentiment history for a specific time period
        
        Args:
            hours (int): Number of hours of history to return
            
        Returns:
            list: List of sentiment data points
        """
        if not self.sentiment_history:
            return []
            
        try:
            # Calculate the cutoff time
            cutoff = datetime.now() - timedelta(hours=hours)
            cutoff_str = cutoff.isoformat()
            
            # Filter the history
            filtered_history = [
                data for data in self.sentiment_history
                if data['timestamp'] > cutoff_str
            ]
            
            return filtered_history
            
        except Exception as e:
            logger.error(f"Error getting sentiment history: {str(e)}")
            return self.sentiment_history[-min(24, len(self.sentiment_history)):]
    
    def get_current_sentiment(self, symbol='BTCUSDT'):
        """
        Get the current market sentiment
        
        Args:
            symbol (str): The symbol to analyze
            
        Returns:
            dict: Current sentiment data
        """
        if not self.sentiment_history:
            return self.calculate_sentiment(symbol)
        
        # Check if sentiment is fresh enough
        now = datetime.now()
        latest = self.sentiment_history[-1]
        latest_time = datetime.fromisoformat(latest['timestamp'])
        
        if (now - latest_time).total_seconds() > 60:
            # Recalculate if older than 1 minute
            return self.calculate_sentiment(symbol)
        
        return latest