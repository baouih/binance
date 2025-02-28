"""
Basic Flask server implementation
"""
import logging
import os
from datetime import datetime
from flask import Flask, render_template

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure Flask app with template folder
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
logger.info(f"Template directory: {template_dir}")
logger.info(f"Template directory exists: {os.path.exists(template_dir)}")

try:
    app = Flask(__name__, template_folder=template_dir)
    logger.info("Successfully initialized Flask app")
except Exception as e:
    logger.error(f"Failed to initialize Flask: {e}")
    raise

@app.route('/')
def index():
    """Root endpoint"""
    try:
        logger.info("Attempting to render index page")
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Failed to render template: {e}")
        logger.exception("Template render error details:")
        return "Internal Server Error", 500

@app.route('/status')
def health():
    """Health check endpoint"""
    return {"status": "online", "time": datetime.now().isoformat()}

if __name__ == "__main__":
    try:
        logger.info("Starting Flask server...")
        app.run(host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise