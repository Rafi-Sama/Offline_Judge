from flask_login import UserMixin
from app import db

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='participant')
    submissions = db.relationship('Submission', backref='user', lazy=True)

class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    time_limit = db.Column(db.Float, nullable=False, default=1.0)  # Seconds
    memory_limit = db.Column(db.Integer, nullable=False, default=256)  # MB
    submissions = db.relationship('Submission', backref='problem', lazy=True)

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'), nullable=False)
    code = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(10), nullable=False, default='python')
    status = db.Column(db.String(20), nullable=False, default='Pending')
    timestamp = db.Column(db.DateTime, nullable=False, default=db.func.now())
    # execution_time = db.Column(db.Float, nullable=False, default=0.0)
    # memory_used = db.Column(db.Float, nullable=False, default=0.0)
