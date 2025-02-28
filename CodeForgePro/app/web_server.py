import logging
import os
import sys
from flask import Flask, render_template

# Configure logging with more detailed format
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
    # Initialize Flask
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.urandom(24)
    app.config['DEBUG'] = True
    logger.info("Flask app initialized successfully")

    @app.route('/')
    def index():
        """Test route for basic functionality"""
        logger.info("Index route accessed")
        return "Hello World! Flask is working."

    logger.info("All routes registered successfully")

except Exception as e:
    logger.critical(f"Failed to initialize Flask app: {e}")
    sys.exit(1)

if __name__ == "__main__":
    try:
        logger.info("Starting Flask server on port 5000...")
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        logger.exception("Detailed error traceback:")
        sys.exit(1)