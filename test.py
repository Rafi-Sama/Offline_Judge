from app import app, db
from models import Problem

with app.app_context():
    problems = db.session.query(Problem).all()
    db.session.close()
# print(problems)

for problem in problems:
    print(f"ID: {problem.id}, Title: {problem.title}, Description: {problem.description}")
