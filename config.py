import os
import secrets

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(16))  # Generate if not set in environment
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'data', 'site.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
