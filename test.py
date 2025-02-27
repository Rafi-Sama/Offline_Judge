from app import app, db
from models import Problem

with db.engine.connect() as connection:
    result = connection.execute("PRAGMA table_info(submission)")
    print(result.fetchall())
