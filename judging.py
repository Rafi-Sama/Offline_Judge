import asyncio, logging, subprocess, time
from pathlib import Path
from app import db, socketio
from models import Problem, User, Submission, TestCase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

language_config = {
    'python': {'extension': 'py', 'compiler': None, 'compile_flags': [], 'execute': ['python', '{source_file}']},
    'cpp':    {'extension': 'cpp', 'compiler': 'g++', 'compile_flags': ['-o', '{executable}'], 'execute': ['{executable}']},
    'c':      {'extension': 'c',   'compiler': 'gcc', 'compile_flags': ['-o', '{executable}'], 'execute': ['{executable}']},
    # Add more languages as needed
}

class CodeJudge:
    @staticmethod
    def compile_code(language, source_file: Path, executable: Path, working_dir: Path) -> dict:
        config = language_config.get(language)
        if not config or config['compiler'] is None:
            return {'status': 'Success'}
        compile_flags = [flag.format(executable=str(executable), source_file=str(source_file), user_dir=str(working_dir))
                         for flag in config['compile_flags']]
        compile_cmd = [config['compiler'], str(source_file)] + compile_flags
        try:
            result = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logger.error("Compilation failed: %s", result.stderr)
                return {'status': 'Compilation Error', 'error': result.stderr}
            return {'status': 'Success', 'executable': str(executable)}
        except subprocess.TimeoutExpired:
            return {'status': 'Compilation Error', 'error': 'Compilation timed out'}
        except Exception as e:
            return {'status': 'Compilation Error', 'error': str(e)}

    @staticmethod
    def normalize_output(text: str) -> str:
        # Remove trailing whitespace from each line and any extra newlines.
        return "\n".join(line.rstrip() for line in text.splitlines()).strip()

    @staticmethod
    async def run_test_case_async(exec_cmd: list, test: TestCase, time_limit: float) -> dict:
        try:
            proc = await asyncio.create_subprocess_exec(
                *exec_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=test.input_data.encode()), timeout=time_limit
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                return {
                    'input': test.input_data,
                    'expected': CodeJudge.normalize_output(test.output_data),
                    'output': '',
                    'status': 'Time Limit Exceeded',
                    'error': f"Exceeded {time_limit}s"
                }
            output = CodeJudge.normalize_output(stdout.decode())
            expected = CodeJudge.normalize_output(test.output_data)
            status = 'Runtime Error' if proc.returncode != 0 else ('Passed' if output == expected else 'Wrong Answer')
            error = stderr.decode() if proc.returncode != 0 else None
            return {
                'input': test.input_data,
                'expected': expected,
                'output': output,
                'status': status,
                'error': error
            }
        except Exception as e:
            return {
                'input': test.input_data,
                'expected': CodeJudge.normalize_output(test.output_data),
                'output': '',
                'status': f'Error: {str(e)}',
                'error': None
            }

    @staticmethod
    async def run_test_cases_async(exec_cmd: list, test_cases: list, time_limit: float) -> list:
        tasks = [CodeJudge.run_test_case_async(exec_cmd, test, time_limit) for test in test_cases]
        return await asyncio.gather(*tasks)

    @staticmethod
    def cleanup_files(*file_paths):
        for file_path in file_paths:
            if file_path and file_path.exists():
                file_path.unlink()

    @staticmethod
    def prepare_environment(language: str, code: str, working_dir: Path, prefix: str) -> tuple:
        """
        Writes code to file, compiles if needed, and builds the execution command.
        Returns a tuple: (exec_cmd, (code_file, executable), error_dict)
        """
        config = language_config.get(language)
        if not config:
            return None, None, {'status': 'Unsupported Language'}
        code_file = working_dir / f"{prefix}.{config['extension']}"
        executable = working_dir / prefix if config['compiler'] else None
        code_file.write_text(code)
        if config['compiler']:
            compile_result = CodeJudge.compile_code(language, code_file, executable, working_dir)
            if compile_result['status'] != 'Success':
                return None, (code_file, executable), compile_result
        exec_cmd = [cmd.format(
                        executable=str(executable) if executable else '',
                        source_file=str(code_file),
                        user_dir=str(working_dir))
                    for cmd in config['execute']]
        return exec_cmd, (code_file, executable), {'status': 'Success'}

    @staticmethod
    def run_code(problem_id, code: str, language: str, user_id: int) -> dict:
        problem = Problem.query.get(problem_id)
        sample_cases = TestCase.query.filter_by(problem_id=problem_id, is_sample=True).all()
        if not sample_cases:
            return {'status': 'No Sample Cases', 'results': []}

        working_dir = Path(f"data/temp/user_{user_id}")
        working_dir.mkdir(parents=True, exist_ok=True)
        exec_cmd, files, error = CodeJudge.prepare_environment(language, code, working_dir, "temp")
        if error['status'] != 'Success':
            CodeJudge.cleanup_files(*files)
            return {'status': 'Compilation Error', 'error': error.get('error', ''), 'results': []}
        # Run test cases concurrently using asyncio
        results = asyncio.run(CodeJudge.run_test_cases_async(exec_cmd, sample_cases, problem.time_limit))
        overall_status = 'All Passed' if all(r['status'] == 'Passed' for r in results) else 'Sample Run Failed'
        CodeJudge.cleanup_files(*files)
        return {'status': overall_status, 'results': results}

    @staticmethod
    def judge_submission(submission):
        # Use asynchronous execution for judging submissions just like run_code
        problem = Problem.query.get(submission.problem_id)
        test_cases = TestCase.query.filter_by(problem_id=submission.problem_id).all()
        config = language_config.get(submission.language)
        if not test_cases:
            submission.status = 'No Test Cases'
            db.session.commit()
            return
        if not config:
            submission.status = 'Unsupported Language'
            db.session.commit()
            return

        working_dir = Path(f"data/submissions/user_{submission.user_id}")
        working_dir.mkdir(parents=True, exist_ok=True)
        exec_cmd, files, error = CodeJudge.prepare_environment(submission.language, submission.code, working_dir, f"sub_{submission.id}")
        if error['status'] != 'Success':
            submission.status = 'Compilation Error'
            submission.error_message = error.get('error', '')
            db.session.commit()
            CodeJudge.cleanup_files(*files)
            return

        submission.status = 'Judging'
        db.session.commit()

        # Run all test cases concurrently (just like run_code)
        results = asyncio.run(CodeJudge.run_test_cases_async(exec_cmd, test_cases, problem.time_limit))
        # Mark submission as failed on the first non-passing test case, otherwise Accepted
        for test_result in results:
            if test_result['status'] != 'Passed':
                submission.status = test_result['status']
                submission.error_message = test_result['error'] or (
                    f"Test case failed: Input: {test_result['input']}, Expected: {test_result['expected']}, Got: {test_result['output']}"
                )
                break
        else:
            submission.status = 'Accepted'
        db.session.commit()
        socketio.emit('update_leaderboard', {'standings': calculate_standings()})
        CodeJudge.cleanup_files(*files)

def run_code(problem_id, code, language, user_id) -> dict:
    return CodeJudge.run_code(problem_id, code, language, user_id)

def judge_submission(submission):
    return CodeJudge.judge_submission(submission)

def calculate_standings():
    return sorted(
        [{'username': user.username, 'solved': solved_count, 'first_submission_time': db.session.query(Submission.timestamp).filter_by(user_id=user.id, status='Accepted').order_by(Submission.timestamp).first()[0] if solved_count > 0 else None}
         for user in User.query.filter_by(role='participant') 
         for solved_count in [Submission.query.filter_by(user_id=user.id, status='Accepted').count()]],
        key=lambda x: (-x['solved'], x['first_submission_time'])
    )
