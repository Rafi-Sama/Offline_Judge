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
    path = os.path.join("data", "problems", f"problem_{problem.id}", "description.txt")
    if os.path.exists(path):
        with open(path, 'r', encoding="utf-8") as f:
            description = f.read()
    else:
        description = "Description not available."
    return render_template('problem.html', problem=problem, description=description)

@app.route('/submit/<int:problem_id>', methods=['GET', 'POST'])
@login_required
def submit(problem_id):
    problem = Problem.query.get_or_404(problem_id)
    
    if request.method == 'POST':
        code = request.form['code']
        language = request.form.get('language', 'cpp')  # Default to C++ if not selected
        
        submission = Submission(
            user_id=current_user.id,
            problem_id=problem_id,
            code=code,
            language=language
        )
        db.session.add(submission)
        db.session.commit()
        
        # Ensure judge_submission updates the status before flashing
        judge_submission(submission)
        db.session.refresh(submission)  # Ensures we get the latest status from DB
        
        flash(f'Submission #{submission.id} judged: {submission.status}', 'success')
        return redirect(url_for('problems'))
    
    return render_template('submit.html', problem=problem)

@app.route('/submissions')
@login_required
def submission_history():
    show_only_mine = request.args.get('mine', 'false') == 'true'

    if show_only_mine:
        submissions = Submission.query.filter_by(user_id=current_user.id).order_by(Submission.timestamp.desc()).all()
    else:
        submissions = Submission.query.order_by(Submission.timestamp.desc()).all()

    return render_template('submission_history.html', submissions=submissions, show_only_mine=show_only_mine)

@app.route('/leaderboard')
@login_required
def leaderboard():
    standings = calculate_standings()
    return render_template('leaderboard.html', standings=standings)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Admin access only', 'error')
        return redirect(url_for('index'))
    
    users = User.query.all()
    problems = Problem.query.all()
    submissions = Submission.query.all()

    return render_template('admin/dashboard.html', users=users, problems=problems, submissions=submissions)

@app.route('/admin/add_problem', methods=['GET', 'POST'])
def add_problem():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        time_limit = float(request.form.get('time_limit', 1.0))  # Default: 1.0
        memory_limit = int(request.form.get('memory_limit', 256))  # Default: 256
        description = request.form.get('description', '').strip()
        input_data = request.form.get('input', '').strip()
        output_data = request.form.get('output', '').strip()

        if not (title and description and input_data and output_data):
            flash("All fields are required!", "error")
            return redirect(url_for('admin_dashboard'))

        problem = Problem(title=title, time_limit=time_limit, memory_limit=memory_limit,description="")
        db.session.add(problem)
        db.session.commit()  # Ensure problem.id is set

        # Setup problem files
        problem_dir = f"data/problems/problem_{problem.id}"

        try:
            os.makedirs(problem_dir, exist_ok=True)
            with open(f"{problem_dir}/description.txt", 'w', encoding='utf-8') as f:
                f.write(description)
            with open(f"{problem_dir}/input.txt", 'w', encoding='utf-8') as f:
                f.write(input_data)
            with open(f"{problem_dir}/output.txt", 'w', encoding='utf-8') as f:
                f.write(output_data)

        except Exception as e:
            flash(f"Error creating problem files: {e}", "error")
            db.session.rollback()
            return redirect(url_for('admin_dashboard'))

        problem.description = f"{problem_dir}/description.txt"
        db.session.commit()
        flash('Problem added successfully', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/add_problem.html')

@app.route('/manage_problems')
@login_required
def manage_problems():
    problems = Problem.query.all()
    return render_template('admin/manage_problems.html', problems=problems)

@app.route('/manage_users')
@login_required
def manage_users():
    users = User.query.all()
    return render_template('admin/manage_users.html', users=users)

@app.route('/manage_submissions')
@login_required
def manage_submissions():
    submissions = Submission.query.all()
    return render_template('admin/manage_submissions.html', submissions=submissions)

@app.route('/delete_problem/<int:problem_id>', methods=['POST'])
@login_required
def delete_problem(problem_id):
    problem = Problem.query.get_or_404(problem_id)
    db.session.delete(problem)
    db.session.commit()
    return redirect(url_for('manage_problems'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return redirect(url_for('manage_users'))  # Prevent self-deletion
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('manage_users'))

@app.route('/delete_submission/<int:submission_id>', methods=['POST'])
@login_required
def delete_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    db.session.delete(submission)
    db.session.commit()
    return redirect(url_for('manage_submissions'))

