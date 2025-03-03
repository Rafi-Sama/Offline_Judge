import subprocess, os 
from app import db, socketio 
from models import Problem, User, Submission, TestCase 

def run_code(problem_id, code, language, user_id) -> dict:
    problem = Problem.query.get(problem_id) 
    sample_cases = TestCase.query.filter_by(problem_id=problem_id, is_sample=True).all() 
    if not sample_cases: return {'status': 'No Sample Cases', 'results': []} 
    lang_ext = {'python': 'py', 'cpp': 'cpp', 'c': 'c'} 
    lang_compiler = {'python': 'python', 'cpp': 'g++', 'c': 'gcc'} 
    if language not in lang_ext: return {'status': 'Unsupported Language', 'results': []} 
    user_dir = f"data/temp/user_{user_id}" 
    code_file = os.path.join(user_dir, f"temp.{lang_ext[language]}") 
    os.makedirs(user_dir, exist_ok=True) 
    with open(code_file, 'w') as f: f.write(code) 
    exec_cmd = [lang_compiler.get(language, 'python'), code_file] if language != 'python' else ['python', code_file] 

    results = []
    for test in sample_cases: 
        try:
            result = subprocess.run(exec_cmd, input=test.input_data, text=True, capture_output=True, timeout=problem.time_limit) 
            output, expected_output = result.stdout.strip(), test.output_data.strip() 
            status = 'Passed' if output == expected_output else 'Failed' 
            results.append({'input': test.input_data, 'expected': expected_output, 'output': output, 'status': status}) 
            if result.returncode != 0: return {'status': 'Runtime Error', 'error': result.stderr, 'results': results} 
        except subprocess.TimeoutExpired: return {'status': 'Time Limit Exceeded', 'results': results} 
        except Exception as e: return {'status': f'Error: {str(e)}', 'results': results} 

    return {'status': 'All Passed', 'results': results} 

def judge_submission(submission):
    problem = Problem.query.get(submission.problem_id) 
    test_cases = TestCase.query.filter_by(problem_id=submission.problem_id).all() 
    if not test_cases: submission.status = 'No Test Cases'; db.session.commit(); return 
    user_dir = f"data/submissions/user_{submission.user_id}" 
    lang_ext = {'python': 'py', 'cpp': 'cpp', 'c': 'c'} 
    lang_compiler = {'python': 'python', 'cpp': 'g++', 'c': 'gcc'} 
    if submission.language not in lang_ext: submission.status = 'Unsupported Language'; db.session.commit(); return 
    submission.status = "Judging" 
    code_file = os.path.join(user_dir, f"sub_{submission.id}.{lang_ext[submission.language]}") 
    os.makedirs(user_dir, exist_ok=True) 
    with open(code_file, 'w') as f: f.write(submission.code) 
    exec_cmd = [lang_compiler.get(submission.language, 'python'), code_file] if submission.language != 'python' else ['python', code_file] 

    for test_case in test_cases: 
        try:
            result = subprocess.run(exec_cmd, input=test_case.input_data, text=True, capture_output=True, timeout=problem.time_limit) 
            output, expected_output = result.stdout.strip(), test_case.output_data.strip() 
            if result.returncode != 0: submission.status = 'Runtime Error'; break 
            if output != expected_output: submission.status = 'Wrong Answer'; break 
        except subprocess.TimeoutExpired: submission.status = 'Time Limit Exceeded'; break 
        except Exception as e: submission.status = f'Error: {str(e)}'; break 
    else: submission.status = 'Accepted' 

    for file_path in [code_file] + ([os.path.join(user_dir, f"sub_{submission.id}.out")] if submission.language in ['c', 'cpp'] else []):  
        if os.path.exists(file_path): os.remove(file_path) 

    db.session.commit() 
    socketio.emit('update_leaderboard', {'standings': calculate_standings()}) 

def calculate_standings():
    return sorted([{'username': user.username, 'solved': Submission.query.filter_by(user_id=user.id, status='Accepted').count()}  
                   for user in User.query.filter_by(role='participant').all()], key=lambda x: x['solved'], reverse=True) 
