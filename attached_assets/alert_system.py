"""
Alert system implementation for trading notifications via Telegram
"""
import logging
import os
from datetime import datetime
from typing import Dict, Optional

from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

class AlertSystem:
    def __init__(self):
        """Initialize alert system with Telegram bot"""
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.bot = None
        if self.telegram_token:
            try:
                self.bot = Bot(token=self.telegram_token)
                logger.info("Telegram bot initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")
                logger.exception("Detailed error traceback:")

    async def send_telegram_message(self, message: str) -> bool:
        """Send message via Telegram bot"""
        if not self.bot or not self.telegram_chat_id:
            logger.warning("Telegram bot not configured")
            return False

        try:
            await self.bot.send_message(
                chat_id=self.telegram_chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info("Telegram message sent successfully")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {e}")
            logger.exception("Detailed error traceback:")
            return False

    async def send_trade_alert(self, trade_data: Dict) -> bool:
        """Send detailed trade execution alert"""
        # Calculate price movement if available
        price_movement = ""
        if trade_data.get('previous_price') and trade_data.get('entry_price'):
            movement_pct = ((trade_data['entry_price'] - trade_data['previous_price']) / 
                          trade_data['previous_price'] * 100)
            direction = "↗️" if movement_pct > 0 else "↘️"
            price_movement = f"\nPrice Movement: {direction} {abs(movement_pct):.2f}%"

        message = (
            f"🤖 <b>Trade Alert</b>\n\n"
            f"Symbol: {trade_data['symbol']}\n"
            f"Side: {trade_data['side']}\n"
            f"Price: {trade_data['entry_price']:.2f} USDT{price_movement}\n"
            f"Quantity: {trade_data['quantity']:.6f}\n"
            f"Type: {trade_data['type']}\n"
            f"Value: {(trade_data['entry_price'] * trade_data['quantity']):.2f} USDT\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        return await self.send_telegram_message(message)

    async def send_performance_alert(self, metrics: Dict) -> bool:
        """Send detailed performance metrics alert"""
        message = (
            f"📊 <b>Performance Update</b>\n\n"
            f"Win Rate: {metrics['win_rate']:.1f}%\n"
            f"Profit Factor: {metrics['profit_factor']:.2f}\n"
            f"Daily PnL: {metrics['daily_pnl']} USDT\n"
            f"Sharpe Ratio: {metrics.get('sharpe_ratio', 'N/A')}\n"
            f"Max Drawdown: {metrics.get('max_drawdown', 'N/A')}%\n"
            f"Total Trades: {metrics.get('total_trades', 'N/A')}\n"
            f"Average Trade: {metrics.get('avg_trade', 'N/A')} USDT\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        return await self.send_telegram_message(message)

    async def send_system_alert(self, status: str, error: Optional[str] = None) -> bool:
        """Send detailed system status alert"""
        emoji = "✅" if status == "OK" else "❌"
        message = (
            f"{emoji} <b>System Status</b>\n\n"
            f"Status: {status}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        if error:
            message += f"\nError Details:\n<pre>{error}</pre>\n"
            message += "\nAction: System will attempt auto-recovery"
        return await self.send_telegram_message(message)

    async def send_signal_alert(self, symbol: str, signals: Dict) -> bool:
        """Send detailed trading signal alert with technical indicators"""
        # Count confirming signals
        buy_signals = sum(1 for s in signals.values() if s == 'BUY')
        sell_signals = sum(1 for s in signals.values() if s == 'SELL')

        # Determine overall signal strength
        signal_str = ("🟢 Strong BUY" if buy_signals >= 3 else
                     "🟡 Weak BUY" if buy_signals > sell_signals else
                     "🔴 Strong SELL" if sell_signals >= 3 else
                     "🟠 Weak SELL" if sell_signals > buy_signals else
                     "⚪ NEUTRAL")

        # Get ML confidence if available
        ml_confidence = ""
        if signals.get('ml_prediction'):
            ml_confidence = f" ({signals.get('ml_confidence', 0):.1f}% confidence)"

        message = (
            f"📈 <b>Trading Signal Alert</b>\n\n"
            f"Symbol: {symbol}\n"
            f"Signal: {signal_str}\n\n"
            f"Technical Indicators:\n"
            f"- SMA: {signals.get('sma_crossover', 'No signal')}\n"
            f"- RSI: {signals.get('rsi', 'No signal')}\n"
            f"- MACD: {signals.get('macd', 'No signal')}\n"
            f"- Bollinger: {signals.get('bollinger_bands', 'No signal')}\n"
            f"- ML Prediction: {signals.get('ml_prediction', 'No signal')}{ml_confidence}\n"
            f"Volume Confirmation: {'✅' if signals.get('volume_confirmation') else '❌'}\n\n"
            f"Signal Strength: {buy_signals + sell_signals}/5 indicators\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return await self.send_telegram_message(message)