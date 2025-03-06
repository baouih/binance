import subprocess
import sys
import os
import time
import signal
import requests
import platform

def kill_process_on_port(port):
    """Kill any process running on the specified port"""
    if platform.system() == "Windows":
        try:
            # For Windows
            result = subprocess.run(f"netstat -ano | findstr :{port}", shell=True, capture_output=True, text=True)
            for line in result.stdout.strip().split('\n'):
                if f":{port}" in line:
                    pid = line.strip().split()[-1]
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True)
                    print(f"Killed process {pid} on port {port}")
                    time.sleep(1)
        except Exception as e:
            print(f"Error killing process on port {port}: {e}")
    else:
        try:
            # For Linux/Mac
            cmd = f"lsof -i:{port} -t"
            port_pid = subprocess.getoutput(cmd).strip()
            if port_pid:
                for pid in port_pid.split('\n'):
                    pid = pid.strip()
                    if pid:
                        os.kill(int(pid), signal.SIGKILL)
                        print(f"Killed process {pid} on port {port}")
                        time.sleep(1)
        except Exception as e:
            print(f"Error killing process on port {port}: {e}")

def start_flask_app():
    """Start the Flask app using app.py"""
    print("Starting Binance Trading Bot web application...")
    
    # Set environment variables
    env = os.environ.copy()
    env["FLASK_APP"] = "app.py"
    env["FLASK_ENV"] = "development"
    
    # Start the process
    process = subprocess.Popen([sys.executable, "app.py"], env=env)
    
    # Wait for server to start
    for i in range(10):
        try:
            time.sleep(1)
            response = requests.get("http://localhost:5000/health")
            if response.status_code == 200:
                print("Web application started successfully!")
                print("Visit http://localhost:5000 to access the trading interface")
                return process
        except requests.RequestException:
            if i == 9:
                print(f"Failed to connect to server after 10 attempts")
            pass
    
    # If we reach here, server didn't start properly
    process.terminate()
    print("Failed to start web application. Check logs for errors.")
    return None

if __name__ == "__main__":
    # Kill any existing process on port 5000
    kill_process_on_port(5000)
    
    # Start the Flask app
    app_process = start_flask_app()
    
    if app_process:
        try:
            # Keep the script running until interrupted
            app_process.wait()
        except KeyboardInterrupt:
            print("Shutting down...")
            app_process.terminate()
            app_process.wait()