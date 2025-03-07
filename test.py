from app import app
from models import Submission

with app.app_context():
    submission = Submission.query.get(76)
    print(submission.code)