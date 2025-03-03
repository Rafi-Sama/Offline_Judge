from flask_login import UserMixin  
from sqlalchemy.dialects.postgresql import JSON  
from app import db  

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)  
    username = db.Column(db.String(20), unique=True, nullable=False)  
    email = db.Column(db.String(120), unique=True, nullable=False)  
    password = db.Column(db.String(60), nullable=False)  
    role = db.Column(db.String(10), nullable=False, default='participant')  
    submissions = db.relationship('Submission', backref='user', lazy=True)  

class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)  
    title = db.Column(db.String(100), nullable=False)  
    description = db.Column(db.String(255), nullable=False)  
    time_limit = db.Column(db.Float, nullable=False, default=1.0)  
    memory_limit = db.Column(db.Integer, nullable=False, default=256)  
    submissions = db.relationship('Submission', backref='problem', lazy=True)  
    contest_id = db.Column(db.Integer, db.ForeignKey('contest.id'), nullable=True)  
    category = db.Column(db.String(50), nullable=True)  
    problem_set_id = db.Column(db.Integer, db.ForeignKey('problem_set.id'), nullable=True)  
    difficulty = db.Column(db.String(10), nullable=False, default='Easy')  
    tags = db.Column(db.String(255), nullable=True)  

class TestCase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id',ondelete="CASCADE"), nullable=False)
    input_data = db.Column(db.Text, nullable=False)
    output_data = db.Column(db.Text, nullable=False)
    is_sample = db.Column(db.Boolean, default=False)  
    problem = db.relationship('Problem', backref=db.backref('test_cases', lazy=True))

class ProblemSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)  
    name = db.Column(db.String(100), nullable=False)  
    contest_id = db.Column(db.Integer, db.ForeignKey('contest.id'), nullable=False)  
    contest = db.relationship('Contest', backref='problem_sets')  
    problems = db.relationship('Problem', backref='problem_set', lazy=True)  

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
    problems = db.relationship('Problem', backref='contest', lazy=True)  
    participation_options = db.Column(JSON, nullable=True)  

class ContestParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)  
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  
    contest_id = db.Column(db.Integer, db.ForeignKey('contest.id'), nullable=False)  
    user = db.relationship('User', backref='participations')  
    contest = db.relationship('Contest', backref='participants')  
    status = db.Column(db.String(20), nullable=False, default='active')  
