import subprocess
import os
from app import db

def judge_submission(submission):
    problem = submission.problem
    user_dir = f"data/submissions/user_{submission.user_id}"
    os.makedirs(user_dir, exist_ok=True)
    code_file = f"{user_dir}/sub_{submission.id}.py"
    
    # Save submitted code
    with open(code_file, 'w') as f:
        f.write(submission.code)
    
    # Read test case
    problem_dir = f"data/problems/problem_{problem.id}"
    with open(f"{problem_dir}/input.txt", 'r') as f:
        test_input = f.read()
    with open(f"{problem_dir}/output.txt", 'r') as f:
        expected_output = f.read().strip()
    
    # Execute code
    try:
        result = subprocess.run(
            ['python', code_file],
            input=test_input,
            text=True,
            capture_output=True,
            timeout=problem.time_limit
        )
        output = result.stdout.strip()
        
        if result.returncode == 0:
            submission.status = 'Accepted' if output == expected_output else 'Wrong Answer'
        else:
            submission.status = 'Runtime Error'
    except subprocess.TimeoutExpired:
        submission.status = 'Time Limit Exceeded'
    finally:
        os.remove(code_file)
        db.session.commit()
        
        # Emit leaderboard update
        standings = calculate_standings()
        socketio.emit('update_leaderboard', {'standings': standings})

# judging.py
from models import User, Submission

def calculate_standings():
    users = User.query.filter_by(role='participant').all()
    standings = []
    for user in users:
        solved = Submission.query.filter_by(user_id=user.id, status='Accepted').count()
        standings.append({'username': user.username, 'solved': solved})
    return sorted(standings, key=lambda x: x['solved'], reverse=True)