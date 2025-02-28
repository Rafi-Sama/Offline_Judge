import subprocess  # process execution
import os  # OS operations
from app import db  # database access
from models import Problem, User, Submission  # model definitions
from extensions import socketio  # real-time communication

def judge_submission(submission):
    from app import socketio  # prevent circular import
    problem = Problem.query.get(submission.problem_id)  # fetch problem record
    user_dir = f"data/submissions/user_{submission.user_id}"  # user submissions directory
    os.makedirs(user_dir, exist_ok=True)  # create directory if missing

    lang_ext = {'python': 'py', 'cpp': 'cpp', 'c': 'c'}  # file extensions mapping
    lang_compiler = {'python': 'python', 'cpp': 'g++', 'c': 'gcc'}  # compiler mapping

    if submission.language not in lang_ext:
        submission.status = 'Unsupported Language'  # update status for unsupported language
        db.session.commit()  # commit update
        return

    code_file = os.path.join(user_dir, f"sub_{submission.id}.{lang_ext[submission.language]}")  # path for code file
    with open(code_file, 'w') as f: f.write(submission.code)  # save submission code

    problem_dir = f"data/problems/problem_{problem.id}"  # problem directory path
    try:
        test_input, expected_output = None, None
        for fname in ["input.txt", "output.txt"]:
            path = os.path.join(problem_dir, fname)  # construct file path
            with open(path, 'r') as f: content = f.read()  # read file content
            if fname == "output.txt": expected_output = content.strip()  # trim expected output
            else: test_input = content  # assign test input
        if submission.language in ['c', 'cpp']:
            executable = os.path.join(user_dir, f"sub_{submission.id}.out")  # executable path for compiled languages
            compile_result = subprocess.run(
                [lang_compiler[submission.language], code_file, "-o", executable],
                capture_output=True, text=True)  # compile code
            if compile_result.returncode != 0:
                submission.status = "Compilation Error"  # update status on compile failure
                db.session.commit()  # commit update
                return
            exec_cmd = [executable]  # set execution command for compiled code
        else:
            exec_cmd = ['python', code_file]  # set execution command for Python
        result = subprocess.run(exec_cmd, input=test_input, text=True, capture_output=True, timeout=problem.time_limit)  # run submission
        output = result.stdout.strip()  # capture output
        submission.status = 'Accepted' if result.returncode == 0 and output == expected_output else ('Runtime Error' if result.returncode != 0 else 'Wrong Answer')  # set status based on result
    except subprocess.TimeoutExpired:
        submission.status = 'Time Limit Exceeded'  # update status on timeout
    except Exception as e:
        submission.status = f'Error: {str(e)}'  # update status on unexpected error
    finally:
        files_to_remove = [code_file]  # list of files for cleanup
        if submission.language in ['c', 'cpp']:
            files_to_remove.append(os.path.join(user_dir, f"sub_{submission.id}.out"))  # add executable for compiled languages
        for file_path in files_to_remove:
            if os.path.exists(file_path): os.remove(file_path)  # remove file if exists
        db.session.commit()  # commit final status
        standings = calculate_standings()  # calculate leaderboard standings
        socketio.emit('update_leaderboard', {'standings': standings})  # emit leaderboard update

def calculate_standings():
    users = User.query.filter_by(role='participant').all()  # retrieve participant users
    standings = []
    for user in users:
        solved = Submission.query.filter_by(user_id=user.id, status='Accepted').count()  # count accepted submissions
        standings.append({'username': user.username, 'solved': solved})  # append user standings
    return sorted(standings, key=lambda x: x['solved'], reverse=True)  # sort standings descending
