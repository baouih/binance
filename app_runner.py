from flask import Flask, render_template
import main

if __name__ == '__main__':
    # Run the Flask app directly
    main.app.run(host='0.0.0.0', port=5000, debug=True)