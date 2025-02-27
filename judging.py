import subprocess
import os
from app import db
from models import Problem, User, Submission
from extensions import socketio

def judge_submission(submission):
    from app import socketio  # 🔥 Prevent circular imports

    problem = Problem.query.get(submission.problem_id)
    
    user_dir = f"data/submissions/user_{submission.user_id}"
    os.makedirs(user_dir, exist_ok=True)

    # File extensions based on language
    lang_ext = {'python': 'py', 'cpp': 'cpp', 'c': 'c'}
    lang_compiler = {'python': 'python', 'cpp': 'g++', 'c': 'gcc'}

    if submission.language not in lang_ext:
        submission.status = 'Unsupported Language'
        db.session.commit()
        return

    code_file = os.path.join(user_dir, f"sub_{submission.id}.{lang_ext[submission.language]}")
    
    # Save submitted code
    with open(code_file, 'w') as f:
        f.write(submission.code)

    problem_dir = f"data/problems/problem_{problem.id}"
    
    try:
        # Read test case
        with open(os.path.join(problem_dir, "input.txt"), 'r') as f:
            test_input = f.read()
        with open(os.path.join(problem_dir, "output.txt"), 'r') as f:
            expected_output = f.read().strip()

        # Compilation step for C and C++
        if submission.language in ['c', 'cpp']:
            executable = os.path.join(user_dir, f"sub_{submission.id}.out")
            compile_result = subprocess.run(
                [lang_compiler[submission.language], code_file, "-o", executable],
                capture_output=True,
                text=True
            )
            if compile_result.returncode != 0:
                submission.status = "Compilation Error"
                db.session.commit()
                return
            exec_cmd = [executable]
        else:
            exec_cmd = ['python', code_file]

        # Execute user code
        result = subprocess.run(
            exec_cmd,
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
    
    except Exception as e:
        submission.status = f'Error: {str(e)}'  # Capture unexpected errors
    
    finally:
        # Cleanup generated files
        if os.path.exists(code_file):
            os.remove(code_file)
        if submission.language in ['c', 'cpp']:
            executable = os.path.join(user_dir, f"sub_{submission.id}.out")
            if os.path.exists(executable):
                os.remove(executable)
        
        db.session.commit()
        
        # Emit leaderboard update if socketio is available
        standings = calculate_standings()
        socketio.emit('update_leaderboard', {'standings': standings})

def calculate_standings():
    users = User.query.filter_by(role='participant').all()
    standings = []
    for user in users:
        solved = Submission.query.filter_by(user_id=user.id, status='Accepted').count()
        standings.append({'username': user.username, 'solved': solved})
    
    return sorted(standings, key=lambda x: x['solved'], reverse=True)
