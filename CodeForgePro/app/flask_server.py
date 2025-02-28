from flask import Flask
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def hello():
    logger.info("Root endpoint accessed")
    return 'Hello from Flask!'

if __name__ == '__main__':
    try:
        logger.info("Starting Flask server...")
        # ALWAYS serve on port 5000
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        raise