import os

basedir = os.path.abspath(os.path.dirname(__file__))
class Config:
    SECRET_KEY = 'your-secret-key-here'  # Change this to a random string
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'data', 'site.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False