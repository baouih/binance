from flask import Flask, render_template
import main

# Application handler for Gunicorn
app = main.app

if __name__ == '__main__':
    # Run the Flask app directly
    main.app.run(host='0.0.0.0', port=8080, debug=True)