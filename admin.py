# This file is used to create an admin user for the application.

"""
from app import app, db
from models import User
from werkzeug.security import generate_password_hash
with app.app_context():
    admin = User(username='admin', password=generate_password_hash('adminpass'), role='admin')
    admin = User(username='admin', email='admin@example.com', password=generate_password_hash('adminpass'), role='admin')
    db.session.add(admin)
    db.session.commit()
"""