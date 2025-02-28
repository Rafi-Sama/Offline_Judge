import os  # OS operations
import secrets  # cryptographic token generation

basedir = os.path.abspath(os.path.dirname(__file__))  # determine base directory

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(16))  # secure key generation from environment or generated token
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'data', 'site.db')  # SQLite database URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # disable modification tracking
