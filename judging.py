import subprocess, os  # Handle process execution and file operations
from app import db, socketio  # Database and real-time updates
from models import Problem, User, Submission, TestCase  # Import models

def run_code(problem_id, code, language, user_id):
    problem = Problem.query.get(problem_id)  # Fetch problem details
    sample_cases = TestCase.query.filter_by(problem_id=problem_id, is_sample=True).all()  # Get sample test cases
    if not sample_cases: return {'status': 'No Sample Cases', 'results': []}  # No sample cases available
    lang_ext = {'python': 'py', 'cpp': 'cpp', 'c': 'c'}  # File extensions
    lang_compiler = {'python': 'python', 'cpp': 'g++', 'c': 'gcc'}  # Compiler commands
    if language not in lang_ext: return {'status': 'Unsupported Language', 'results': []}  # Unsupported language
    user_dir = f"data/temp/user_{user_id}"  # User-specific directory
    code_file = os.path.join(user_dir, f"temp.{lang_ext[language]}")  # Code file path
    os.makedirs(user_dir, exist_ok=True)  # Ensure directory exists
    with open(code_file, 'w') as f: f.write(code)  # Save user code
    exec_cmd = [lang_compiler.get(language, 'python'), code_file] if language != 'python' else ['python', code_file]  # Execution command

    results = []
    for test in sample_cases:  # Iterate over test cases
        try:
            result = subprocess.run(exec_cmd, input=test.input_data, text=True, capture_output=True, timeout=problem.time_limit)  # Run code
            output, expected_output = result.stdout.strip(), test.output_data.strip()  # Get outputs
            status = 'Passed' if output == expected_output else 'Failed'  # Compare outputs
            results.append({'input': test.input_data, 'expected': expected_output, 'output': output, 'status': status})  # Store result
            if result.returncode != 0: return {'status': 'Runtime Error', 'error': result.stderr, 'results': results}  # Handle runtime error
        except subprocess.TimeoutExpired: return {'status': 'Time Limit Exceeded', 'results': results}  # Handle timeout
        except Exception as e: return {'status': f'Error: {str(e)}', 'results': results}  # Handle other errors

    return {'status': 'All Passed', 'results': results}  # All tests passed

def judge_submission(submission):
    problem = Problem.query.get(submission.problem_id)  # Fetch problem details
    test_cases = TestCase.query.filter_by(problem_id=submission.problem_id).all()  # Get all test cases
    if not test_cases: submission.status = 'No Test Cases'; db.session.commit(); return  # No test cases available
    user_dir = f"data/submissions/user_{submission.user_id}"  # User-specific directory
    lang_ext = {'python': 'py', 'cpp': 'cpp', 'c': 'c'}  # File extensions
    lang_compiler = {'python': 'python', 'cpp': 'g++', 'c': 'gcc'}  # Compiler commands
    if submission.language not in lang_ext: submission.status = 'Unsupported Language'; db.session.commit(); return  # Unsupported language
    submission.status = "Judging"  # Mark as judging
    code_file = os.path.join(user_dir, f"sub_{submission.id}.{lang_ext[submission.language]}")  # Code file path
    os.makedirs(user_dir, exist_ok=True)  # Ensure directory exists
    with open(code_file, 'w') as f: f.write(submission.code)  # Save submission code
    exec_cmd = [lang_compiler.get(submission.language, 'python'), code_file] if submission.language != 'python' else ['python', code_file]  # Execution command

    for test_case in test_cases:  # Iterate over test cases
        try:
            result = subprocess.run(exec_cmd, input=test_case.input_data, text=True, capture_output=True, timeout=problem.time_limit)  # Run code
            output, expected_output = result.stdout.strip(), test_case.output_data.strip()  # Get outputs
            if result.returncode != 0: submission.status = 'Runtime Error'; break  # Handle runtime error
            if output != expected_output: submission.status = 'Wrong Answer'; break  # Handle incorrect output
        except subprocess.TimeoutExpired: submission.status = 'Time Limit Exceeded'; break  # Handle timeout
        except Exception as e: submission.status = f'Error: {str(e)}'; break  # Handle other errors
    else: submission.status = 'Accepted'  # Passed all test cases

    for file_path in [code_file] + ([os.path.join(user_dir, f"sub_{submission.id}.out")] if submission.language in ['c', 'cpp'] else []):  
        if os.path.exists(file_path): os.remove(file_path)  # Cleanup generated files

    db.session.commit()  # Save status
    socketio.emit('update_leaderboard', {'standings': calculate_standings()})  # Update leaderboard

def calculate_standings():
    return sorted([{'username': user.username, 'solved': Submission.query.filter_by(user_id=user.id, status='Accepted').count()}  
                   for user in User.query.filter_by(role='participant').all()], key=lambda x: x['solved'], reverse=True)  # Rank users by solved problems
