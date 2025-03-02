from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db, login_manager
from models import User, Problem, Submission, Contest, ContestParticipant, TestCase
from werkzeug.security import generate_password_hash, check_password_hash
from judging import judge_submission, calculate_standings, run_code
from datetime import datetime
from sqlalchemy import and_, or_, func
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'admin': flash('Admin access only', 'error'); return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

@login_manager.user_loader
def load_user(user_id): return User.query.get(int(user_id))

@app.route('/')
def index(): return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']): login_user(user); return redirect(url_for('problems'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username, email, password = request.form['username'], request.form['email'], request.form['password']
        if User.query.filter_by(username=username).first(): flash('Username already exists')
        else: 
            user = User(username=username, email=email, password=generate_password_hash(password))
            db.session.add(user); db.session.commit(); flash('Registration successful! Please log in.'); return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout(): logout_user(); return redirect(url_for('index'))

@app.route('/problems')
def problems():
    args = request.args
    search, category, difficulty, tags = args.get('search', '').lower(), args.get('category', ''), args.get('difficulty', ''), args.getlist('tags')
    current_time = datetime.now()
    problems = Problem.query.filter(or_(Problem.contest_id == None, and_(Contest.end_time <= current_time, Problem.contest_id != None))).all()
    solvers = dict(db.session.query(Submission.problem_id, func.count(func.distinct(Submission.user_id))).join(User).filter(User.role == 'participant', Submission.status == 'Accepted').group_by(Submission.problem_id).all())
    filtered = [(p, solvers.get(p.id, 0)) for p in problems if (not search or search in p.title.lower()) and (not category or p.category == category) and (not difficulty or p.difficulty == difficulty) and (not tags or any(t in p.tags for t in tags))]
    sort_by, order = args.get('sort', 'solvers'), args.get('order', 'desc')
    filtered.sort(key=lambda x: x[1] if sort_by == 'solvers' else getattr(x[0], sort_by), reverse=(order == 'desc'))
    return render_template('problems.html', problems=filtered, search_query=search, category_filter=category, difficulty_filter=difficulty, selected_tags=tags, difficulties=['Easy', 'Medium', 'Hard', 'Extreme'], tags=["brute_force", "math", "dp", "greedy", "graph", "sorting", "binary_search", "bitwise", "recursion"])

@app.route('/problem/<int:id>')
@login_required
def problem(id):
    p = Problem.query.get_or_404(id)
    return render_template('problem.html', problem=p, description=p.description or "Description not available.", sample_test_cases=TestCase.query.filter_by(problem_id=id, is_sample=True).all())

@app.route('/problem/<int:problem_id>', methods=['GET', 'POST'])
@login_required
def submit(problem_id):
    problem = Problem.query.get_or_404(problem_id)
    if request.method == 'POST':
        submission = Submission(user_id=current_user.id, problem_id=problem_id, code=request.form['code'], language=request.form.get('language', 'cpp'))
        db.session.add(submission); db.session.commit(); judge_submission(submission); db.session.refresh(submission)
        flash(f'Submission #{submission.id} judged: {submission.status}', 'success'); return redirect(url_for('problems'))
    return render_template('problem.html', problem=problem)

@app.route('/submissions')
@login_required
def submission_history():
    mine = request.args.get('mine', 'false') == 'true'
    current_time = datetime.now()
    active_pids = {p.id for c in Contest.query.filter(Contest.start_time <= current_time, Contest.end_time > current_time).all() for p in c.problems}
    submissions = (Submission.query.filter_by(user_id=current_user.id) if mine else Submission.query).order_by(Submission.timestamp.desc()).all()
    for s in submissions: 
        if s.problem_id in active_pids: s.code = "[Hidden until contest ends]"
    return render_template('submission_history.html', submissions=submissions, show_only_mine=mine)

@app.route('/admin/add_contest_problem/<int:contest_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_contest_problem(contest_id):
    contest = Contest.query.get_or_404(contest_id)
    if request.method == 'POST':
        problem = Problem(title=request.form.get('title', '').strip(), time_limit=float(request.form.get('time_limit', 1.0)), memory_limit=int(request.form.get('memory_limit', 256)), description=request.form.get('description', '').strip(), difficulty=request.form.get('difficulty', 'Easy').strip(), tags=",".join(request.form.getlist('tags[]')) or None, contest_id=contest_id)
        db.session.add(problem); db.session.commit()
        for i, (inp, out) in enumerate(zip(request.form.getlist('input[]'), request.form.getlist('output[]'))):
            db.session.add(TestCase(problem_id=problem.id, input_data=inp.strip(), output_data=out.strip(), is_sample=str(i) in request.form.getlist('sample[]')))
        db.session.commit(); flash(f'Problem added to contest "{contest.name}" successfully', 'success'); return redirect(url_for('manage_contests'))
    return render_template('admin/add_contest_problem.html', contest=contest)

@app.route('/problem/<int:problem_id>/run', methods=['POST'])
@login_required
def run(problem_id): return jsonify(run_code(problem_id, request.form['code'], request.form.get('language', 'cpp'), current_user.id))

@app.route('/leaderboard')
def leaderboard(): return render_template('leaderboard.html', standings=calculate_standings())

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard(): return render_template('admin/dashboard.html', users=User.query.all(), problems=Problem.query.all(), submissions=Submission.query.all())

@app.route('/admin/add_problem', methods=['GET', 'POST'])
@app.route('/admin/add_problem/<int:contest_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def add_problem(contest_id=None):
    if request.method == 'POST':
        problem = Problem(title=request.form.get('title', '').strip(), time_limit=float(request.form.get('time_limit', 1.0)), memory_limit=int(request.form.get('memory_limit', 256)), description=request.form.get('description', '').strip(), difficulty=request.form.get('difficulty', 'Easy').strip(), tags=",".join(request.form.getlist('tags[]')) or None, contest_id=contest_id)
        db.session.add(problem); db.session.commit()
        for i, (inp, out) in enumerate(zip(request.form.getlist('input[]'), request.form.getlist('output[]'))):
            db.session.add(TestCase(problem_id=problem.id, input_data=inp.strip(), output_data=out.strip(), is_sample=str(i) in request.form.getlist('sample[]')))
        db.session.commit(); flash('Problem added successfully', 'success'); return redirect(url_for('manage_problems', contest_id=contest_id) if contest_id else url_for('manage_problems'))
    return render_template('admin/add_problem.html', contest_id=contest_id)

@app.route('/admin/manage_problems')
@app.route('/admin/manage_problems/<int:contest_id>')
@login_required
@admin_required
def manage_problems(contest_id=None): return render_template('admin/manage_problems.html', problems=Problem.query.filter_by(contest_id=contest_id).all() if contest_id else Problem.query.filter_by(contest_id=None).all(), contest_id=contest_id)

@app.route('/manage_submissions')
@login_required
def manage_submissions(): return render_template('admin/manage_submissions.html', submissions=Submission.query.all())

@app.route('/manage_users')
@login_required
@admin_required
def manage_users(): return render_template('admin/manage_users.html', users=User.query.all())

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id: return redirect(url_for('manage_users'))
    Submission.query.filter_by(user_id=user_id).delete(); db.session.delete(user); db.session.commit(); return redirect(url_for('manage_users'))

@app.route('/delete_problem/<int:problem_id>', methods=['POST'])
@login_required
@admin_required
def delete_problem(problem_id):
    problem = Problem.query.get_or_404(problem_id)
    TestCase.query.filter_by(problem_id=problem_id).delete(); Submission.query.filter_by(problem_id=problem_id).delete(); db.session.delete(problem); db.session.commit(); flash("Problem deleted successfully", "success"); return redirect(url_for('manage_problems'))

@app.route('/delete_submission/<int:submission_id>', methods=['POST'])
@login_required
def delete_submission(submission_id): db.session.delete(Submission.query.get_or_404(submission_id)); db.session.commit(); return redirect(url_for('manage_submissions'))

@app.route('/contests', endpoint='get_contests')
def get_contests():
    now = datetime.now()
    return render_template('contests.html', ongoing_contests=Contest.query.filter(and_(Contest.start_time <= now, Contest.end_time > now)).all(), upcoming_contests=Contest.query.filter(Contest.start_time > now).all(), past_contests=Contest.query.filter(Contest.end_time <= now).all(), user_participations={p.contest_id for p in ContestParticipant.query.filter_by(user_id=current_user.id).all()} if current_user.is_authenticated else set())

@app.route('/join_contest/<int:contest_id>', methods=['POST'])
@login_required
def join_contest(contest_id):
    if ContestParticipant.query.filter_by(user_id=current_user.id, contest_id=contest_id).first(): flash("You have already joined this contest!", "info"); return redirect(url_for('get_contests'))
    db.session.add(ContestParticipant(user_id=current_user.id, contest_id=contest_id)); db.session.commit(); flash("Successfully registered for the contest!", "success"); return redirect(url_for('get_contests'))

@app.route('/admin/add_contest', methods=['GET', 'POST'])
@login_required
@admin_required
def add_contest():
    if request.method == 'POST':
        try:
            start, end = datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M'), datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')
            now = datetime.now()
            if start <= now or end <= start: flash("Invalid contest timing", "error"); return render_template('admin/add_contest.html')
            db.session.add(Contest(name=request.form['name'], start_time=start, end_time=end)); db.session.commit(); flash("Contest added successfully!", "success"); return redirect(url_for('manage_contests'))
        except ValueError: flash("Invalid date format", "error")
    return render_template('admin/add_contest.html')

@app.route('/admin/manage_contests', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_contests():
    if request.method == 'POST':
        contest_id = request.form.get('contest_id')  # Get the contest ID from the form
        contest = Contest.query.get(contest_id)  # Get the contest object from the database
        if contest:
            try:
                start = datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M')  # Convert start time
                end = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')  # Convert end time
                now = datetime.now()  # Get current time
                if start <= now or end <= start:  # Validate times
                    flash("Invalid contest timing", "error")
                else:
                    contest.start_time = start  # Update start time
                    contest.end_time = end  # Update end time
                    db.session.commit()  # Commit changes to the database
                    flash("Contest updated successfully!", "success")
            except ValueError:
                flash("Invalid date format", "error")
        else:
            flash("Contest not found", "error")
        return redirect(url_for('manage_contests'))
    
    contests = Contest.query.all()  # Fetch all contests for display
    return render_template('admin/manage_contests.html', contests=contests)



@app.route('/admin/delete_contest/<int:contest_id>', methods=['POST'])
@login_required
@admin_required
def delete_contest(contest_id):
    ContestParticipant.query.filter_by(contest_id=contest_id).delete(); contest = Contest.query.get(contest_id); 
    if contest: db.session.delete(contest); db.session.commit(); flash("Contest deleted successfully!", "success"); return redirect(url_for('manage_contests'))
    flash("Contest not found.", "danger"); return redirect(url_for('manage_contests'))

@app.route('/contest/<int:contest_id>')
def contest_detail(contest_id):
    contest = Contest.query.get_or_404(contest_id)
    
    solvers = dict(db.session.query(Submission.problem_id, func.count(func.distinct(Submission.user_id)))
                   .join(User)
                   .filter(User.role == 'participant', Submission.status == 'Accepted')
                   .group_by(Submission.problem_id)
                   .all())

    standings = [{'username': participant.username, 'solved': sum(1 for problem in contest.problems if 
                             Submission.query.filter_by(user_id=participant.id, problem_id=problem.id, status='Accepted').count() > 0)}
                 for participant in User.query.filter_by(role='participant').all()]
    
    return render_template('contest_detail.html', contest=contest, problems=contest.problems, solvers_count=solvers, standings=sorted(standings, key=lambda x: x['solved'], reverse=True))

@app.route('/edit_problem/<int:problem_id>', methods=['GET', 'POST'])
def edit_problem(problem_id):
    problem = Problem.query.get_or_404(problem_id)
    if request.method == 'POST':
        problem.title, problem.description, problem.difficulty = request.form.get('title', problem.title), request.form.get('description', problem.description), request.form.get('difficulty', 'Easy').strip()
        problem.time_limit, problem.memory_limit = float(request.form.get('time_limit', problem.time_limit)), int(request.form.get('memory_limit', problem.memory_limit))
        problem.tags = ",".join(request.form.getlist('tags[]')) or problem.tags
        TestCase.query.filter_by(problem_id=problem.id).delete()
        for i, (inp, out) in enumerate(zip(request.form.getlist('input[]'), request.form.getlist('output[]'))):
            db.session.add(TestCase(problem_id=problem.id, input_data=inp, output_data=out, is_sample=str(i+1) in request.form.getlist('sample[]')))
        db.session.commit(); flash("Problem updated successfully!", "success"); return redirect(url_for('manage_problems'))
    return render_template('admin/edit_problem.html', problem=problem)