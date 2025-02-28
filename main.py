import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the Flask app from the app module
try:
    from app.web_server import app, socketio, start_data_generation
    logger.info("Successfully imported Flask app and components")
except ImportError as e:
    logger.error(f"Error importing Flask app: {str(e)}")
    raise

# Initialize data generation thread
logger.info("Initializing data generation thread")
start_data_generation()

# This is used by gunicorn for production
# The app object is imported by gunicorn as specified in the .replit file
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting app on port {port}")
    
    # In development, we use socketio.run to include websocket support
    socketio.run(app, host='0.0.0.0', port=port, debug=True)