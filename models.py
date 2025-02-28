from flask_login import UserMixin  # support for user session management
from sqlalchemy.dialects.postgresql import JSON  # PostgreSQL JSON column type
from app import db  # database instance

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)  # unique identifier
    username = db.Column(db.String(20), unique=True, nullable=False)  # username field
    email = db.Column(db.String(120), unique=True, nullable=False)  # email is stored
    password = db.Column(db.String(60), nullable=False)  # password field
    role = db.Column(db.String(10), nullable=False, default='participant')  # user role, default participant
    submissions = db.relationship('Submission', backref='user', lazy=True)  # related submissions

class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # unique identifier
    title = db.Column(db.String(100), nullable=False)  # problem title
    description = db.Column(db.String(255), nullable=False)  # problem description
    time_limit = db.Column(db.Float, nullable=False, default=1.0)  # execution time limit (seconds)
    memory_limit = db.Column(db.Integer, nullable=False, default=256)  # memory limit (MB)
    submissions = db.relationship('Submission', backref='problem', lazy=True)  # related submissions
    contest_id = db.Column(db.Integer, db.ForeignKey('contest.id'), nullable=True)  # associated contest
    category = db.Column(db.String(50), nullable=True)  # problem category
    problem_set_id = db.Column(db.Integer, db.ForeignKey('problem_set.id'), nullable=True)  # linked problem set

class TestCase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id',ondelete="CASCADE"), nullable=False)
    input_data = db.Column(db.Text, nullable=False)
    output_data = db.Column(db.Text, nullable=False)
    is_sample = db.Column(db.Boolean, default=False)  # Checkbox for sample test case

    problem = db.relationship('Problem', backref=db.backref('test_cases', lazy=True))

class ProblemSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # unique identifier
    name = db.Column(db.String(100), nullable=False)  # problem set name
    contest_id = db.Column(db.Integer, db.ForeignKey('contest.id'), nullable=False)  # associated contest
    contest = db.relationship('Contest', backref='problem_sets')  # contest relationship
    problems = db.relationship('Problem', backref='problem_set', lazy=True)  # related problems

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # unique identifier
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # associated user
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'), nullable=False)  # associated problem
    code = db.Column(db.Text, nullable=False)  # submitted code
    language = db.Column(db.String(10), nullable=False, default='python')  # programming language used
    status = db.Column(db.String(20), nullable=False, default='Pending')  # submission status
    timestamp = db.Column(db.DateTime, nullable=False, default=db.func.now())  # submission time

class Contest(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # unique identifier
    name = db.Column(db.String(100), nullable=False)  # contest name
    start_time = db.Column(db.DateTime, nullable=False)  # contest start time
    end_time = db.Column(db.DateTime, nullable=False)  # contest end time
    problems = db.relationship('Problem', backref='contest', lazy=True)  # related problems
    participation_options = db.Column(JSON, nullable=True)  # participation options in JSON format

class ContestParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # unique identifier
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # associated user
    contest_id = db.Column(db.Integer, db.ForeignKey('contest.id'), nullable=False)  # associated contest
    user = db.relationship('User', backref='participations')  # relationship to user participations
    contest = db.relationship('Contest', backref='participants')  # relationship to contest participants
    status = db.Column(db.String(20), nullable=False, default='active')  # participation status
