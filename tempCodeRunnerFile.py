from app import app, db
from models import User

with app.app_context():
    users = User.query.all()
    print(users)  # Should list all users
