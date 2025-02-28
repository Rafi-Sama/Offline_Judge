import os  # OS operations
from flask import Flask  # web framework
from flask_sqlalchemy import SQLAlchemy  # ORM support
from flask_login import LoginManager  # user session management
from config import Config  # configuration settings
from extensions import socketio  # real-time communication
from flask_migrate import Migrate  # database migrations

app = Flask(__name__)  # instantiate Flask app
app.config.from_object(Config)  # load configuration

socketio.init_app(app)  # initialize real-time communication
db = SQLAlchemy(app)  # set up ORM

with app.app_context():  # ensure operations run within application context
    if not os.path.exists(os.path.join("data", "site.db")):  # check if database file does not exist
        db.create_all()  # create all database tables

migrate = Migrate(app, db)  # enable database migrations

login_manager = LoginManager()  # create login manager
login_manager.init_app(app)  # initialize login management
login_manager.login_view = "login"  # set login route

from routes import *  # import route definitions

def home(): return "Welcome to the Offline Judge!"  # define home endpoint

data_dir = os.path.join(os.path.dirname(__file__), 'data')  # determine data directory path
os.makedirs(data_dir, exist_ok=True)  # ensure data directory exists

if __name__ == '__main__':
    with app.app_context(): db.create_all()  # ensure tables exist within context
    app.run(host='0.0.0.0', port=5000, debug=True)  # run the application