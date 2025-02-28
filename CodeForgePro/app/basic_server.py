"""
Most basic Flask server implementation
"""
from flask import Flask
import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('web_server.log')
    ]
)
logger = logging.getLogger(__name__)

try:
    app = Flask(__name__)
    logger.info("Successfully initialized Flask app")
except Exception as e:
    logger.error(f"Failed to initialize Flask: {e}")
    sys.exit(1)

@app.route('/')
def index():  # lint: ignore[name_conflict]
    """Root endpoint"""
    logger.info("Accessed root endpoint")
    return "Hello World"

if __name__ == "__main__":
    try:
        logger.info("Starting Flask server...")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Current working directory: {os.getcwd()}")
        # ALWAYS serve the app on port 5000
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        logger.exception("Detailed error traceback:")
        sys.exit(1)