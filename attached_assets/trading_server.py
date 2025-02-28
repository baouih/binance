"""
Simple trading bot server
"""
import logging
from flask import Flask

# Configure logging (from original, enhanced)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('trading_bot.log')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def index():
    return "Trading Bot Server is Running"

if __name__ == '__main__':
    try:
        logger.info("Starting Trading Bot Server on port 5000...")
        app.run(host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise