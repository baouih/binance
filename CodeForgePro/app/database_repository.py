"""
Database repository for storing trading data and ML predictions
"""
import logging
import os
import json
from datetime import datetime
import psycopg2
from psycopg2.extras import Json

logger = logging.getLogger(__name__)

class DatabaseRepository:
    def __init__(self):
        self.conn = psycopg2.connect(os.environ['DATABASE_URL'])
        self.cur = self.conn.cursor()
        logger.info("Database connection established")

    def save_trade(self, trade_data):
        """Save trade to database"""
        try:
            query = """
            INSERT INTO trades (
                symbol, entry_price, exit_price, entry_time, exit_time,
                position_type, volume, profit_loss, status, ml_confidence
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """
            self.cur.execute(query, (
                trade_data['symbol'],
                trade_data['entry_price'],
                trade_data.get('exit_price'),
                trade_data['entry_time'],
                trade_data.get('exit_time'),
                trade_data['position_type'],
                trade_data['volume'],
                trade_data.get('profit_loss'),
                trade_data.get('status', 'open'),
                trade_data.get('ml_confidence')
            ))
            trade_id = self.cur.fetchone()[0]
            self.conn.commit()
            logger.info(f"Trade saved with ID: {trade_id}")
            return trade_id
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error saving trade: {e}")
            raise

    def save_prediction(self, prediction_data):
        """Save ML prediction to database"""
        try:
            query = """
            INSERT INTO ml_predictions (
                symbol, prediction, confidence, features, actual_movement
            ) VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
            """
            self.cur.execute(query, (
                prediction_data['symbol'],
                prediction_data['prediction'],
                prediction_data['confidence'],
                Json(prediction_data['features']),
                prediction_data.get('actual_movement')
            ))
            pred_id = self.cur.fetchone()[0]
            self.conn.commit()
            logger.info(f"Prediction saved with ID: {pred_id}")
            return pred_id
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error saving prediction: {e}")
            raise

    def save_market_data(self, market_data):
        """Save market data with indicators to database"""
        try:
            query = """
            INSERT INTO market_data (
                symbol, timestamp, open, high, low, close,
                volume, indicators, regime
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """
            self.cur.execute(query, (
                market_data['symbol'],
                market_data['timestamp'],
                market_data['open'],
                market_data['high'],
                market_data['low'],
                market_data['close'],
                market_data['volume'],
                Json(market_data.get('indicators', {})),
                market_data.get('regime')
            ))
            data_id = self.cur.fetchone()[0]
            self.conn.commit()
            logger.info(f"Market data saved with ID: {data_id}")
            return data_id
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error saving market data: {e}")
            raise

    def update_bot_status(self, status_data):
        """Update bot status"""
        try:
            query = """
            INSERT INTO bot_status (
                is_running, current_position, current_profit_loss,
                last_trade_time, error_message, updated_at
            ) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING id;
            """
            self.cur.execute(query, (
                status_data['is_running'],
                status_data.get('current_position'),
                status_data.get('current_profit_loss', 0.0),
                status_data.get('last_trade_time'),
                status_data.get('error_message')
            ))
            status_id = self.cur.fetchone()[0]
            self.conn.commit()
            logger.info(f"Bot status updated with ID: {status_id}")
            return status_id
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error updating bot status: {e}")
            raise

    def add_notification(self, message, type='info'):
        """Add new notification"""
        try:
            query = """
            INSERT INTO notifications (message, type, created_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            RETURNING id;
            """
            self.cur.execute(query, (message, type))
            notif_id = self.cur.fetchone()[0]
            self.conn.commit()
            logger.info(f"Notification added with ID: {notif_id}")
            return notif_id
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error adding notification: {e}")
            raise

    def get_latest_trades(self, symbol=None, limit=100):
        """Get latest trades from database"""
        try:
            query = """
            SELECT * FROM trades
            WHERE symbol = COALESCE(%s, symbol)
            ORDER BY entry_time DESC
            LIMIT %s;
            """
            self.cur.execute(query, (symbol, limit))
            trades = self.cur.fetchall()
            logger.info(f"Retrieved {len(trades)} trades")
            return trades
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            raise

    def get_ml_performance(self, symbol=None, from_date=None):
        """Get ML prediction performance metrics"""
        try:
            query = """
            SELECT 
                COUNT(*) as total_predictions,
                AVG(CASE WHEN prediction > 0.5 AND actual_movement > 0 
                     OR prediction < 0.5 AND actual_movement < 0 
                    THEN 1 ELSE 0 END) as accuracy,
                AVG(confidence) as avg_confidence
            FROM ml_predictions
            WHERE symbol = COALESCE(%s, symbol)
            AND created_at >= COALESCE(%s, created_at);
            """
            self.cur.execute(query, (symbol, from_date))
            performance = self.cur.fetchone()
            logger.info(f"Retrieved ML performance metrics")
            return performance
        except Exception as e:
            logger.error(f"Error getting ML performance: {e}")
            raise

    def get_bot_config(self):
        """Get latest bot configuration"""
        try:
            query = """
            SELECT * FROM bot_configs 
            ORDER BY created_at DESC 
            LIMIT 1;
            """
            self.cur.execute(query)
            config = self.cur.fetchone()
            return config
        except Exception as e:
            logger.error(f"Error getting bot config: {e}")
            raise

    def __del__(self):
        """Close database connection"""
        try:
            self.cur.close()
            self.conn.close()
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
            pass