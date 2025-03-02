import subprocess  # process execution
import os  # OS operations
from app import db  # database access
from models import Problem, User, Submission,TestCase  # model definitions
from extensions import socketio  # real-time communication

def run_code(problem_id, code, language, user_id):
    problem = Problem.query.get(problem_id)
    sample_cases = TestCase.query.filter_by(problem_id=problem_id, is_sample=True).all()

    if not sample_cases:
        return {'status': 'No Sample Cases', 'results': []}

    lang_ext = {'python': 'py', 'cpp': 'cpp', 'c': 'c'}
    lang_compiler = {'python': 'python', 'cpp': 'g++', 'c': 'gcc'}

    if language not in lang_ext:
        return {'status': 'Unsupported Language', 'results': []}

    user_dir = f"data/temp/user_{user_id}"
    os.makedirs(user_dir, exist_ok=True)

    code_file = os.path.join(user_dir, f"temp.{lang_ext[language]}")
    with open(code_file, 'w') as f:
        f.write(code)

    if language in ['c', 'cpp']:
        executable = os.path.join(user_dir, "temp.out")
        compile_result = subprocess.run(
            [lang_compiler[language], code_file, "-o", executable],
            capture_output=True, text=True
        )

        if compile_result.returncode != 0:
            return {'status': 'Compilation Error', 'error': compile_result.stderr, 'results': []}

        exec_cmd = [executable]
    else:
        exec_cmd = ['python', code_file]

    results = []
    for test in sample_cases:
        try:
            result = subprocess.run(
                exec_cmd, input=test.input_data, text=True, capture_output=True, timeout=problem.time_limit
            )
            output = result.stdout.strip()
            expected_output = test.output_data.strip()

            status = 'Passed' if output == expected_output else 'Failed'
            results.append({'input': test.input_data, 'expected': expected_output, 'output': output, 'status': status})

            if result.returncode != 0:
                return {'status': 'Runtime Error', 'error': result.stderr, 'results': results}

        except subprocess.TimeoutExpired:
            return {'status': 'Time Limit Exceeded', 'results': results}
        except Exception as e:
            return {'status': f'Error: {str(e)}', 'results': results}

    return {'status': 'All Passed', 'results': results}


def judge_submission(submission):
    from app import socketio  # prevent circular import
    problem = Problem.query.get(submission.problem_id)
    test_cases = TestCase.query.filter_by(problem_id=problem.id).all()  

    # ✅ 1️⃣ Check if there are test cases
    if not test_cases:
        submission.status = 'No Test Cases'
        db.session.commit()
        return

    user_dir = f"data/submissions/user_{submission.user_id}"
    os.makedirs(user_dir, exist_ok=True)

    lang_ext = {'python': 'py', 'cpp': 'cpp', 'c': 'c'}
    lang_compiler = {'python': 'python', 'cpp': 'g++', 'c': 'gcc'}

    if submission.language not in lang_ext:
        submission.status = 'Unsupported Language'
        db.session.commit()
        return

    # ✅ 2️⃣ Reset status before checking
    submission.status = "Judging"
    db.session.commit()

    # Save user code
    code_file = os.path.join(user_dir, f"sub_{submission.id}.{lang_ext[submission.language]}")
    with open(code_file, 'w') as f:
        f.write(submission.code)

    # Compilation step for C/C++
    if submission.language in ['c', 'cpp']:
        executable = os.path.join(user_dir, f"sub_{submission.id}.out")
        compile_result = subprocess.run(
            [lang_compiler[submission.language], code_file, "-o", executable],
            capture_output=True, text=True)
        
        if compile_result.returncode != 0:
            submission.status = "Compilation Error"
            db.session.commit()
            return
        exec_cmd = [executable]
    else:
        exec_cmd = ['python', code_file]

    # ✅ 3️⃣ Check against all test cases
    for test_case in test_cases:
        try:
            result = subprocess.run(
                exec_cmd, input=test_case.input_data, text=True, capture_output=True,
                timeout=problem.time_limit)
            
            output = result.stdout.strip()
            expected_output = test_case.output_data.strip()

            if result.returncode != 0:
                submission.status = 'Runtime Error'
                break
            if output != expected_output:
                submission.status = 'Wrong Answer'
                break
        except subprocess.TimeoutExpired:
            submission.status = 'Time Limit Exceeded'
            break
        except Exception as e:
            submission.status = f'Error: {str(e)}'
            break
    else:
        # ✅ 4️⃣ If all test cases passed, mark as accepted
        submission.status = 'Accepted'

    # Cleanup
    files_to_remove = [code_file]
    if submission.language in ['c', 'cpp']:
        files_to_remove.append(executable)

    for file_path in files_to_remove:
        if os.path.exists(file_path):
            os.remove(file_path)

    db.session.commit()
    standings = calculate_standings()
    socketio.emit('update_leaderboard', {'standings': standings})

def calculate_standings():
    users = User.query.filter_by(role='participant').all()  # retrieve participant users
    standings = []
    for user in users:
        solved = Submission.query.filter_by(user_id=user.id, status='Accepted').count()  # count accepted submissions
        standings.append({'username': user.username, 'solved': solved})  # append user standings
    return sorted(standings, key=lambda x: x['solved'], reverse=True)  # sort standings descending

