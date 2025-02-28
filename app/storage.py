import os
import json
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

class Storage:
    """Storage class for persisting trading data to disk"""
    
    def __init__(self, storage_dir='data'):
        """
        Initialize storage.
        
        Args:
            storage_dir (str): Directory to store data files
        """
        self.storage_dir = storage_dir
        
        # Create storage directory if it doesn't exist
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
            
        # File paths
        self.positions_file = os.path.join(storage_dir, 'positions.json')
        self.trades_file = os.path.join(storage_dir, 'trades.json')
        self.settings_file = os.path.join(storage_dir, 'settings.json')
        self.bots_file = os.path.join(storage_dir, 'bots.json')
        
        # Initialize storage
        self._initialize_storage()
        
    def _initialize_storage(self):
        """Initialize storage files if they don't exist"""
        for file_path in [self.positions_file, self.trades_file, self.settings_file, self.bots_file]:
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    f.write('[]')
                logger.info(f"Created storage file: {file_path}")
                
    def _load_json(self, file_path):
        """Load JSON data from file"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading data from {file_path}: {str(e)}")
            return []
            
    def _save_json(self, file_path, data):
        """Save JSON data to file"""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=self._json_serializer)
            return True
        except Exception as e:
            logger.error(f"Error saving data to {file_path}: {str(e)}")
            return False
            
    def _json_serializer(self, obj):
        """Custom JSON serializer for datetime objects"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
        
    def save_position(self, position):
        """
        Save a position to storage.
        
        Args:
            position (dict): Position data
            
        Returns:
            bool: Success or failure
        """
        positions = self._load_json(self.positions_file)
        
        # Update if position with same ID exists, otherwise add
        position_id = position.get('id')
        for i, pos in enumerate(positions):
            if pos.get('id') == position_id:
                positions[i] = position
                return self._save_json(self.positions_file, positions)
                
        # Position not found, add it
        positions.append(position)
        return self._save_json(self.positions_file, positions)
        
    def get_positions(self, status=None):
        """
        Get positions from storage.
        
        Args:
            status (str, optional): Filter by status (e.g., 'OPEN', 'CLOSED')
            
        Returns:
            list: List of positions
        """
        positions = self._load_json(self.positions_file)
        
        if status:
            return [p for p in positions if p.get('status') == status]
            
        return positions
        
    def delete_position(self, position_id):
        """
        Delete a position from storage.
        
        Args:
            position_id (str/int): Position ID
            
        Returns:
            bool: Success or failure
        """
        positions = self._load_json(self.positions_file)
        positions = [p for p in positions if p.get('id') != position_id]
        return self._save_json(self.positions_file, positions)
        
    def save_trade(self, trade):
        """
        Save a trade to storage.
        
        Args:
            trade (dict): Trade data
            
        Returns:
            bool: Success or failure
        """
        trades = self._load_json(self.trades_file)
        trades.append(trade)
        return self._save_json(self.trades_file, trades)
        
    def get_trades(self, symbol=None, limit=None):
        """
        Get trades from storage.
        
        Args:
            symbol (str, optional): Filter by symbol
            limit (int, optional): Limit the number of trades returned
            
        Returns:
            list: List of trades
        """
        try:
            trades = self._load_json(self.trades_file)
            
            if symbol:
                trades = [t for t in trades if t.get('symbol') == symbol]
                
            # Sort by time (most recent first)
            # Use safe getter for timestamps that handles potential None values
            def safe_timestamp_getter(trade):
                exit_time = trade.get('exit_time')
                if exit_time:
                    if isinstance(exit_time, str):
                        try:
                            return datetime.fromisoformat(exit_time)
                        except:
                            return datetime.min
                    return exit_time
                
                entry_time = trade.get('entry_time')
                if entry_time:
                    if isinstance(entry_time, str):
                        try:
                            return datetime.fromisoformat(entry_time)
                        except:
                            return datetime.min
                    return entry_time
                
                return datetime.min
                
            trades.sort(key=safe_timestamp_getter, reverse=True)
            
            if limit and isinstance(limit, int) and limit > 0:
                return trades[:limit]
                
            return trades
        except Exception as e:
            logger.error(f"Error retrieving trades: {str(e)}")
            return []
        
    def save_settings(self, settings):
        """
        Save settings to storage.
        
        Args:
            settings (dict): Settings data
            
        Returns:
            bool: Success or failure
        """
        return self._save_json(self.settings_file, settings)
        
    def get_settings(self):
        """
        Get settings from storage.
        
        Returns:
            dict: Settings data
        """
        return self._load_json(self.settings_file)
        
    def save_bot(self, bot):
        """
        Save a bot configuration to storage.
        
        Args:
            bot (dict): Bot configuration
            
        Returns:
            bool: Success or failure
        """
        bots = self._load_json(self.bots_file)
        
        # Update if bot with same ID exists, otherwise add
        bot_id = bot.get('id')
        for i, b in enumerate(bots):
            if b.get('id') == bot_id:
                bots[i] = bot
                return self._save_json(self.bots_file, bots)
                
        # Bot not found, add it
        bots.append(bot)
        return self._save_json(self.bots_file, bots)
        
    def get_bots(self, status=None):
        """
        Get bot configurations from storage.
        
        Args:
            status (str, optional): Filter by status (e.g., 'active', 'stopped')
            
        Returns:
            list: List of bot configurations
        """
        bots = self._load_json(self.bots_file)
        
        if status:
            return [b for b in bots if b.get('status') == status]
            
        return bots
        
    def delete_bot(self, bot_id):
        """
        Delete a bot configuration from storage.
        
        Args:
            bot_id (str/int): Bot ID
            
        Returns:
            bool: Success or failure
        """
        bots = self._load_json(self.bots_file)
        bots = [b for b in bots if b.get('id') != bot_id]
        return self._save_json(self.bots_file, bots)