import os  # OS operations
from flask import render_template, request, redirect, url_for, flash  # HTML rendering, request handling, redirection, flash messaging
from flask_login import login_user, logout_user, login_required, current_user  # session management functions
from app import app, db  # application instance and database
from models import User, Problem, Submission, Contest, ContestParticipant, TestCase  # model definitions
from werkzeug.security import generate_password_hash, check_password_hash  # password security utilities
from judging import judge_submission, calculate_standings  # judging and standings functions
from app import login_manager  # login manager instance
from datetime import datetime  # datetime utilities
from flask import jsonify  # JSON responses
from sqlalchemy import and_  # SQL logical operator

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # load user by ID

@app.route('/')
def index():
    return render_template('index.html')  # render home page

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':  # process login form
        username = request.form['username']  # retrieve username
        password = request.form['password']  # retrieve password
        user = User.query.filter_by(username=username).first()  # fetch user by username
        if user and check_password_hash(user.password, password):  # verify credentials
            login_user(user)  # log in user
            return redirect(url_for('problems'))  # redirect to problems page
        flash('Invalid username or password')  # flash error message
    return render_template('login.html')  # render login page

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':  # process registration form
        username = request.form['username']  # retrieve username
        email = request.form['email']  # retrieve email
        password = request.form['password']  # retrieve password
        if User.query.filter_by(username=username).first():  # check if username exists
            flash('Username already exists')  # flash error message
        else:
            user = User(username=username, email=email, password=generate_password_hash(password))  # create new user with hashed password
            db.session.add(user)  # add user to session
            db.session.commit()  # commit new user
            flash('Registration successful! Please log in.')  # flash success message
            return redirect(url_for('login'))  # redirect to login page
    return render_template('register.html')  # render registration page

@app.route('/logout')
@login_required
def logout():
    logout_user()  # log out user
    return redirect(url_for('index'))  # redirect to home page

@app.route('/problems')
@login_required
def problems():
    problems = Problem.query.all()  # fetch all problems
    return render_template('problems.html', problems=problems)  # render problems list

@app.route('/problem/<int:id>')
@login_required
def problem(id):
    problem = Problem.query.get_or_404(id)  # fetch problem by ID or 404
    description = problem.description if problem.description else "Description not available."
    sample_test_cases = []  # empty sample test cases
    sample_test_cases = TestCase.query.filter_by(problem_id=id, is_sample=True).all()
    return render_template('problem.html', problem=problem, description=description, sample_test_cases=sample_test_cases)  # render problem detail page
    

@app.route('/submit/<int:problem_id>', methods=['GET', 'POST'])
@login_required
def submit(problem_id):
    problem = Problem.query.get_or_404(problem_id)  # fetch problem or 404
    if request.method == 'POST':  # process submission form
        code = request.form['code']  # retrieve submitted code
        language = request.form.get('language', 'cpp')  # retrieve language, default to C++
        submission = Submission(user_id=current_user.id, problem_id=problem_id, code=code, language=language)  # create submission record
        db.session.add(submission)  # add submission to session
        db.session.commit()  # commit submission
        judge_submission(submission)  # judge the submission
        db.session.refresh(submission)  # refresh submission status
        flash(f'Submission #{submission.id} judged: {submission.status}', 'success')  # flash result message
        return redirect(url_for('problems'))  # redirect to problems page
    return render_template('submit.html', problem=problem)  # render submission form

@app.route('/submissions')
@login_required
def submission_history():
    show_only_mine = request.args.get('mine', 'false') == 'true'  # determine filter option
    if show_only_mine:
        submissions = Submission.query.filter_by(user_id=current_user.id).order_by(Submission.timestamp.desc()).all()  # fetch current user's submissions
    else:
        submissions = Submission.query.order_by(Submission.timestamp.desc()).all()  # fetch all submissions
    return render_template('submission_history.html', submissions=submissions, show_only_mine=show_only_mine)  # render submission history

@app.route('/leaderboard')
def leaderboard():
    standings = calculate_standings()  # calculate standings
    return render_template('leaderboard.html', standings=standings)  # render leaderboard

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':  # verify admin role
        flash('Admin access only', 'error')  # flash error message
        return redirect(url_for('index'))  # redirect to home page
    users = User.query.all()  # fetch all users
    problems = Problem.query.all()  # fetch all problems
    submissions = Submission.query.all()  # fetch all submissions
    return render_template('admin/dashboard.html', users=users, problems=problems, submissions=submissions)  # render admin dashboard

@app.route('/admin/add_problem', methods=['GET', 'POST'])
def add_problem():
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        time_limit = float(request.form.get('time_limit', 1.0))
        memory_limit = int(request.form.get('memory_limit', 256))
        description = request.form.get('description', '').strip()

        problem = Problem(title=title, time_limit=time_limit, memory_limit=memory_limit, description=description)
        db.session.add(problem)
        db.session.commit()

        # Handling multiple test cases
        test_inputs = request.form.getlist('input[]')
        test_outputs = request.form.getlist('output[]')
        sample_flags = request.form.getlist('sample[]')  # Gets checked values

        for i in range(len(test_inputs)):
            is_sample = sample_flags[i] == 'on' if i < len(sample_flags) else False
            test_case = TestCase(
                problem_id=problem.id,
                input_data=test_inputs[i].strip(),
                output_data=test_outputs[i].strip(),
                is_sample=is_sample
            )
            db.session.add(test_case)

        db.session.commit()
        flash('Problem added successfully', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/add_problem.html')


@app.route('/manage_problems')
@login_required
def manage_problems():
    problems = Problem.query.all()  # fetch all problems
    return render_template('admin/manage_problems.html', problems=problems)  # render manage problems page

@app.route('/manage_submissions')
@login_required
def manage_submissions():
    submissions = Submission.query.all()  # fetch all submissions
    return render_template('admin/manage_submissions.html', submissions=submissions)  # render manage submissions page

@app.route('/manage_users')
@login_required
def manage_users():
    if current_user.role != 'admin':  # Ensure only admins can access
        flash('Admin access only', 'error')  # flash error message
        return redirect(url_for('index'))  # redirect to home page
    users = User.query.all()  # Fetch all users
    return render_template('admin/manage_users.html', users=users)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)  # fetch user or 404
    if user.id == current_user.id: return redirect(url_for('manage_users'))  # prevent self-deletion
    db.session.delete(user)  # delete user record
    db.session.commit()  # commit deletion
    return redirect(url_for('manage_users'))  # redirect to manage users

@app.route('/delete_problem/<int:problem_id>', methods=['POST'])
@login_required
def delete_problem(problem_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    problem = Problem.query.get_or_404(problem_id)  # fetch problem or 404
    if problem:
        # Delete test cases first
        TestCase.query.filter_by(problem_id=problem_id).delete()
        Submission.query.filter_by(problem_id=problem_id).delete()
        Problem.query.filter_by(id=problem_id).delete()
        db.session.delete(problem)
        db.session.commit()
        flash("Problem deleted successfully", "success")
    else:
        flash("Problem not found", "error")
    return redirect(url_for('manage_problems'))  # redirect to manage problems

@app.route('/delete_submission/<int:submission_id>', methods=['POST'])
@login_required
def delete_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)  # fetch submission or 404
    db.session.delete(submission)  # delete submission record
    db.session.commit()  # commit deletion
    return redirect(url_for('manage_submissions'))  # redirect to manage submissions

@app.route('/contests', endpoint='get_contests')
def get_contests():
    current_time = datetime.utcnow()  # current UTC time
    ongoing_contests = Contest.query.filter(Contest.end_time > current_time).all()  # fetch ongoing contests
    upcoming_contests = Contest.query.filter(Contest.start_time > current_time).all()  # fetch upcoming contests
    past_contests = Contest.query.filter(Contest.end_time < current_time).all()  # fetch past contests
    return render_template('contests.html', ongoing_contests=ongoing_contests, upcoming_contests=upcoming_contests, past_contests=past_contests)  # render contests page

@app.route('/admin/add_contest', methods=['GET', 'POST'])
@login_required
def add_contest():
    if current_user.role != 'admin':  # verify admin privileges
        flash('Admin access only', 'error')  # flash error message
        return redirect(url_for('index'))  # redirect to home page
    if request.method == 'POST':  # process contest addition form
        name = request.form['name']  # retrieve contest name
        try:
            start_time = datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M')  # parse start time
            end_time = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')  # parse end time
        except ValueError:
            flash("Invalid date format. Please use the correct format.", "error")  # flash error if date parsing fails
            return render_template('admin/add_contest.html')
        now = datetime.utcnow()  # current UTC time
        if start_time <= now:  # ensure contest starts in the future
            flash("Contest start time must be in the future.", "error")
            return render_template('admin/add_contest.html')
        if end_time <= start_time:  # ensure contest ends after it starts
            flash("Contest end time must be after the start time.", "error")
            return render_template('admin/add_contest.html')
        contest = Contest(name=name, start_time=start_time, end_time=end_time)  # create contest record
        db.session.add(contest)  # add contest to session
        db.session.commit()  # commit contest
        flash("Contest added successfully!", "success")  # flash success message
        return redirect(url_for('admin_dashboard'))  # redirect to admin dashboard
    return render_template('admin/add_contest.html')  # render add contest page

@app.route('/admin/manage_contests')
@login_required
def manage_contests():
    if current_user.role != 'admin':  # verify admin privileges
        flash('Admin access only', 'error')  # flash error message
        return redirect(url_for('index'))  # redirect to home page
    contests = Contest.query.all()  # fetch all contests
    return render_template('admin/manage_contests.html', contests=contests)  # render manage contests page

@app.route('/admin/delete_contest/<int:contest_id>', methods=['POST'])
@login_required
def delete_contest(contest_id):
    if current_user.role != 'admin':  # verify admin privileges
        flash('Admin access only', 'error')  # flash error message
        return redirect(url_for('index'))  # redirect to home page
    contest = Contest.query.get(contest_id)  # fetch contest
    if contest:
        db.session.delete(contest)  # delete contest record
        db.session.commit()  # commit deletion
        flash("Contest deleted successfully!", "success")  # flash success message
    else:
        flash("Contest not found.", "danger")  # flash error message
    return redirect(url_for('manage_contests'))  # redirect to manage contests

@app.route('/contest/<int:contest_id>')
def contest_detail(contest_id):
    contest = Contest.query.get_or_404(contest_id)  # fetch contest or 404
    problem_sets = contest.problem_sets  # retrieve related problem sets
    participation_options = contest.participation_options if contest.participation_options else []  # get participation options or empty list
    return render_template('contest_detail.html', contest=contest, problem_sets=problem_sets, participation_options=participation_options)  # render contest detail page

@app.route('/join_contest/<int:contest_id>', methods=['POST'])
def join_contest(contest_id):
    pass  # implement joining contest logic
