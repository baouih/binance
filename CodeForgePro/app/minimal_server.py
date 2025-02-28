"""
Minimal Flask server for testing
"""
from flask import Flask
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('debug.log')
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask
app = Flask(__name__)

@app.route('/')
def hello():
    logger.info("Root endpoint accessed")
    return 'Trading Bot Server is running!'

if __name__ == '__main__':
    try:
        logger.info("Attempting to start server...")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Flask version: {Flask.__version__}")
        app.run(host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        logger.exception("Detailed error traceback:")
        sys.exit(1)
