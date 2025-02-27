import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config  # Assuming your config is in config.py
from extensions import socketio
from flask_migrate import Migrate


app = Flask(__name__)
app.config.from_object(Config)

socketio.init_app(app)  # Ensure socketio is initialized
db = SQLAlchemy(app)
with app.app_context():
    db.create_all()  # Creates tables based on your models 


migrate = Migrate(app, db)  # 'app' is your Flask app, 'db' is your SQLAlchemy instance


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # Redirect users who are not logged in

from routes import *

# @app.route('/')
def home():
    return "Welcome to the Offline Judge!"
# Ensure the 'data' directory exists
data_dir = os.path.join(os.path.dirname(__file__), 'data')
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

# Rest of your code...
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(host='0.0.0.0', port=5000, debug=True)
    # Start the app (e.g., app.run() or socketio.run())