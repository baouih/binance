from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    api_key = db.Column(db.String(128))
    api_secret = db.Column(db.String(128))
    telegram_token = db.Column(db.String(128))
    telegram_chat_id = db.Column(db.String(128))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class TradingPosition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    side = db.Column(db.String(10), nullable=False)  # LONG or SHORT
    entry_price = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float)
    amount = db.Column(db.Float, nullable=False)
    leverage = db.Column(db.Integer, default=1)
    stop_loss = db.Column(db.Float)
    take_profit = db.Column(db.Float)
    pnl = db.Column(db.Float, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    def calculate_pnl(self):
        if not self.current_price or not self.entry_price:
            return 0
            
        if self.side == 'LONG':
            self.pnl = (self.current_price - self.entry_price) / self.entry_price * 100 * self.leverage
        else:  # SHORT
            self.pnl = (self.entry_price - self.current_price) / self.entry_price * 100 * self.leverage
            
        return self.pnl
    
    def __repr__(self):
        return f'<Position {self.symbol} {self.side} {self.amount}>'


class TradingStrategy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=False)
    risk_level = db.Column(db.String(10), default='10%')
    config = db.Column(db.Text)  # JSON config as string
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    def __repr__(self):
        return f'<Strategy {self.name}>'


class TradingHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    side = db.Column(db.String(10), nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    leverage = db.Column(db.Integer, default=1)
    pnl = db.Column(db.Float, nullable=False)
    pnl_percent = db.Column(db.Float, nullable=False)
    strategy_id = db.Column(db.Integer, db.ForeignKey('trading_strategy.id'))
    entry_time = db.Column(db.DateTime, nullable=False)
    exit_time = db.Column(db.DateTime, nullable=False)
    
    def __repr__(self):
        return f'<Trade {self.symbol} {self.side} {self.pnl_percent}%>'