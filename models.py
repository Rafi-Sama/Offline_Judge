from flask_login import UserMixin
from sqlalchemy.dialects.postgresql import JSON
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
    contest_id = db.Column(db.Integer, db.ForeignKey('contest.id'), nullable=True)  # Problem belongs to a contest
    category = db.Column(db.String(50), nullable=True)
    problem_set_id = db.Column(db.Integer, db.ForeignKey('problem_set.id'), nullable=True)  # Foreign key to ProblemSet

class ProblemSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contest_id = db.Column(db.Integer, db.ForeignKey('contest.id'), nullable=False)
    contest = db.relationship('Contest', backref='problem_sets')  # Link to contest
    problems = db.relationship('Problem', backref='problem_set', lazy=True)  # Link to problems

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'), nullable=False)
    code = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(10), nullable=False, default='python')
    status = db.Column(db.String(20), nullable=False, default='Pending')
    timestamp = db.Column(db.DateTime, nullable=False, default=db.func.now())

class Contest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    problems = db.relationship('Problem', backref='contest', lazy=True)  # Relationship with problems
    participation_options = db.Column(JSON, nullable=True)  # Store options as a JSON column

class ContestParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    contest_id = db.Column(db.Integer, db.ForeignKey('contest.id'), nullable=False)
    user = db.relationship('User', backref='participations')
    contest = db.relationship('Contest', backref='participants')
    status = db.Column(db.String(20), nullable=False, default='active')  # Track active, completed, etc.
