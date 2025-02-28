from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/')
def hello():
    return 'Trading Bot Server is running!'

if __name__ == '__main__':
    print("Starting Flask server on port 5000...")
    socketio.run(app, host='0.0.0.0', port=5000)