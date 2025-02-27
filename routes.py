import os
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from models import User, Problem, Submission
from werkzeug.security import generate_password_hash, check_password_hash
from judging import judge_submission, calculate_standings
from app import login_manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # Load user by ID

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('problems'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
        else:
            user = User(username=username, password=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/problems')
@login_required
def problems():
    problems = Problem.query.all()
    return render_template('problems.html', problems=problems)

@app.route('/problem/<int:id>')
@login_required
def problem(id):
    problem = Problem.query.get_or_404(id)
    with open(f"data/problems/problem_{problem.id}/description.txt", 'r') as f:
        description = f.read()
    return render_template('problem.html', problem=problem, description=description)

@app.route('/submit/<int:problem_id>', methods=['GET', 'POST'])
@login_required
def submit(problem_id):
    problem = Problem.query.get_or_404(problem_id)
    if request.method == 'POST':
        code = request.form['code']
        submission = Submission(
            user_id=current_user.id,
            problem_id=problem_id,
            code=code,
            language='python'
        )
        db.session.add(submission)
        db.session.commit()
        judge_submission(submission)
        flash(f'Submission #{submission.id} judged: {submission.status}')
        return redirect(url_for('problems'))
    return render_template('submit.html', problem=problem)

@app.route('/leaderboard')
@login_required
def leaderboard():
    standings = calculate_standings()
    return render_template('leaderboard.html', standings=standings)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Admin access only')
        return redirect(url_for('index'))
    return render_template('admin/dashboard.html')

@app.route('/admin/add_problem', methods=['GET', 'POST'])
@login_required
def add_problem():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    if request.method == 'POST':
        title = request.form['title']
        time_limit = float(request.form['time_limit'])
        memory_limit = int(request.form['memory_limit'])
        problem = Problem(title=title, time_limit=time_limit, memory_limit=memory_limit)
        db.session.add(problem)
        db.session.commit()
        
        # Setup problem files
        problem_dir = f"data/problems/problem_{problem.id}"
        os.makedirs(problem_dir, exist_ok=True)
        with open(f"{problem_dir}/description.txt", 'w') as f:
            f.write(request.form['description'])
        with open(f"{problem_dir}/input.txt", 'w') as f:
            f.write(request.form['input'])
        with open(f"{problem_dir}/output.txt", 'w') as f:
            f.write(request.form['output'])
        problem.description = f"{problem_dir}/description.txt"
        db.session.commit()
        flash('Problem added successfully')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/add_problem.html')