"""
Test script for Telegram notifications
"""
import asyncio
import logging
from alert_system import AlertSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_telegram_notifications():
    """Test all types of Telegram notifications"""
    alert_system = AlertSystem()

    # Test system alert
    logger.info("Testing system alert...")
    await alert_system.send_system_alert("OK", "Test system is running")

    # Test trade alert
    logger.info("Testing trade alert...")
    trade_data = {
        'symbol': 'BTCUSDT',
        'side': 'BUY',
        'entry_price': 45000.00,
        'previous_price': 44500.00,  # Add previous price for movement calculation
        'quantity': 0.001,
        'type': 'TEST'
    }
    await alert_system.send_trade_alert(trade_data)

    # Test performance alert
    logger.info("Testing performance alert...")
    metrics = {
        'win_rate': 65.5,
        'profit_factor': 1.45,
        'daily_pnl': '+245.50',
        'sharpe_ratio': 1.8,
        'max_drawdown': 12.5,
        'total_trades': 48,
        'avg_trade': '+5.12'
    }
    await alert_system.send_performance_alert(metrics)

    # Test signal alert
    logger.info("Testing signal alert...")
    signals = {
        'sma_crossover': 'BUY',
        'rsi': 'BUY',
        'bollinger_bands': 'NEUTRAL',
        'macd': 'BUY',
        'ml_prediction': 'BUY',
        'ml_confidence': 85.5,
        'volume_confirmation': True
    }
    await alert_system.send_signal_alert('BTCUSDT', signals)

if __name__ == "__main__":
    asyncio.run(test_telegram_notifications())