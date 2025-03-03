from flask import render_template, request, redirect, url_for, flash, jsonify  # Core Flask utilities for rendering, requests, and JSON responses
from flask_login import login_user, logout_user, login_required, current_user  # User session management tools
from app import app, db, login_manager  # Application instance, database, and login manager
from models import User, Problem, Submission, Contest, ContestParticipant, TestCase  # Database models for key entities
from werkzeug.security import generate_password_hash, check_password_hash  # Secure password hashing and verification
from judging import judge_submission, calculate_standings, run_code  # Custom functions for judging and standings
from datetime import datetime  # Timestamp handling
from sqlalchemy import and_, or_, func  # SQLAlchemy utilities for complex queries
from functools import wraps  # Decorator utility for wrapping functions

def admin_required(f):  # Decorator to restrict access to admins
    @wraps(f)  # Preserves the original function's metadata
    def decorated(*args, **kwargs):  # Wrapper function for admin check
        if current_user.role != 'admin': flash('Admin access only', 'error'); return redirect(url_for('index'))  # Redirects non-admins with error
        return f(*args, **kwargs)  # Proceeds if admin
    return decorated  # Returns decorated function

@login_manager.user_loader  # Registers user loader with Flask-Login
def load_user(user_id): return User.query.get(int(user_id))  # Fetches user by ID from database

@app.route('/')  # Root route
def index(): return render_template('index.html')  # Renders homepage

@app.route('/login', methods=['GET', 'POST'])  # Login route with GET/POST support
def login():  # Handles user login
    if request.method == 'POST':  # Processes login form submission
        user = User.query.filter_by(username=request.form['username']).first()  # Looks up user by username
        if user and check_password_hash(user.password, request.form['password']): login_user(user); return redirect(url_for('problems' if current_user.role != 'admin' else 'admin_dashboard'))  # Logs in user if credentials match
        flash('Invalid username or password')  # Shows error for invalid login
    return render_template('login.html')  # Displays login page for GET

@app.route('/register', methods=['GET', 'POST'])  # Registration route
def register():  # Manages new user signup
    if request.method == 'POST':  # Handles registration form
        username, email, password = request.form['username'], request.form['email'], request.form['password']  # Extracts form data
        if User.query.filter_by(username=username).first(): flash('Username already exists')  # Checks for duplicate username
        else: 
            user = User(username=username, email=email, password=generate_password_hash(password))  # Creates new user with hashed password
            db.session.add(user); db.session.commit(); flash('Registration successful! Please log in.'); return redirect(url_for('login'))  # Saves user and redirects
    return render_template('register.html')  # Shows registration page

@app.route('/logout')  # Logout route
@login_required  # Ensures user is logged in
def logout(): logout_user(); return redirect(url_for('index'))  # Logs out user and redirects to homepage

@app.route('/problems')  # Problems listing route
def problems():  # Displays filtered problem list
    args = request.args  # Gets query parameters
    search, category, difficulty, tags = args.get('search', '').lower(), args.get('category', ''), args.get('difficulty', ''), args.getlist('tags')  # Extracts filter criteria
    current_time = datetime.now()  # Gets current timestamp
    problems = Problem.query.filter(or_(Problem.contest_id == None, and_(Contest.end_time <= current_time, Problem.contest_id != None))).all()  # Fetches non-contest or past contest problems
    solvers = dict(db.session.query(Submission.problem_id, func.count(func.distinct(Submission.user_id))).join(User).filter(User.role == 'participant', Submission.status == 'Accepted').group_by(Submission.problem_id).all())  # Calculates solvers per problem
    filtered = [(p, solvers.get(p.id, 0)) for p in problems if (not search or search in p.title.lower()) and (not category or p.category == category) and (not difficulty or p.difficulty == difficulty) and (not tags or any(t in p.tags for t in tags))]  # Applies filters to problems
    sort_by, order = args.get('sort', 'solvers'), args.get('order', 'desc')  # Determines sorting criteria
    filtered.sort(key=lambda x: x[1] if sort_by == 'solvers' else getattr(x[0], sort_by), reverse=(order == 'desc'))  # Sorts filtered problems
    return render_template('problems.html', problems=filtered, search_query=search, category_filter=category, difficulty_filter=difficulty, selected_tags=tags, difficulties=['Easy', 'Medium', 'Hard', 'Extreme'], tags=["brute_force", "math", "dp", "greedy", "graph", "sorting", "binary_search", "bitwise", "recursion"])  # Renders problems page with filters

@app.route('/problem/<int:id>')  # Problem detail route
@login_required  # Requires login
def problem(id):  # Shows specific problem details
    p = Problem.query.get_or_404(id)  # Fetches problem or returns 404
    return render_template('problem.html', problem=p, description=p.description or "Description not available.", sample_test_cases=TestCase.query.filter_by(problem_id=id, is_sample=True).all())  # Renders problem page with description and samples

@app.route('/problem/<int:problem_id>', methods=['GET', 'POST'])  # Submission route
@login_required  # Requires login
def submit(problem_id):  # Handles problem submissions
    problem = Problem.query.get_or_404(problem_id)  # Gets problem or 404
    if request.method == 'POST':  # Processes submission form
        submission = Submission(user_id=current_user.id, problem_id=problem_id, code=request.form['code'], language=request.form.get('language', 'cpp'))  # Creates new submission object
        db.session.add(submission); db.session.commit(); judge_submission(submission); db.session.refresh(submission)  # Saves and judges submission
        flash(f'Submission #{submission.id} judged: {submission.status}', 'success'); return redirect(url_for('problems'))  # Notifies result and redirects
    return render_template('problem.html', problem=problem)  # Shows submission page for GET

@app.route('/submissions')  # Submission history route
@login_required  # Requires login
def submission_history():  # Displays user or all submissions
    mine = request.args.get('mine', 'false') == 'true'  # Filters to current user's submissions
    current_time = datetime.now()  # Gets current time
    active_pids = {p.id for c in Contest.query.filter(Contest.start_time <= current_time, Contest.end_time > current_time).all() for p in c.problems}  # Identifies active contest problems
    submissions = (Submission.query.filter_by(user_id=current_user.id) if mine else Submission.query).order_by(Submission.timestamp.desc()).all()  # Fetches submissions based on filter
    for s in submissions: 
        if s.problem_id in active_pids: s.code = "[Hidden until contest ends]"  # Hides code for active contest problems
    return render_template('submission_history.html', submissions=submissions, show_only_mine=mine)  # Renders submission history

@app.route('/admin/add_contest_problem/<int:contest_id>', methods=['GET', 'POST'])  # Add contest problem route
@login_required  # Requires login
@admin_required  # Restricts to admins
def admin_add_contest_problem(contest_id):  # Adds problem to specific contest
    contest = Contest.query.get_or_404(contest_id)  # Fetches contest or 404
    if request.method == 'POST':  # Handles problem creation
        problem = Problem(title=request.form.get('title', '').strip(), time_limit=float(request.form.get('time_limit', 1.0)), memory_limit=int(request.form.get('memory_limit', 256)), description=request.form.get('description', '').strip(), difficulty=request.form.get('difficulty', 'Easy').strip(), tags=",".join(request.form.getlist('tags[]')) or None, contest_id=contest_id)  # Creates problem linked to contest
        db.session.add(problem); db.session.commit()  # Saves problem
        for i, (inp, out) in enumerate(zip(request.form.getlist('input[]'), request.form.getlist('output[]'))):  # Iterates over test case pairs
            db.session.add(TestCase(problem_id=problem.id, input_data=inp.strip(), output_data=out.strip(), is_sample=str(i) in request.form.getlist('sample[]')))  # Adds test cases with sample flag
        db.session.commit(); flash(f'Problem added to contest "{contest.name}" successfully', 'success'); return redirect(url_for('manage_contests'))  # Commits and redirects with success message
    return render_template('admin/add_contest_problem.html', contest=contest)  # Renders add problem page

@app.route('/problem/<int:problem_id>/run', methods=['POST'])  # Code run route
@login_required  # Requires login
def run(problem_id): return jsonify(run_code(problem_id, request.form['code'], request.form.get('language', 'cpp'), current_user.id))  # Executes code and returns result as JSON

@app.route('/leaderboard')  # Leaderboard route
def leaderboard(): return render_template('leaderboard.html', standings=calculate_standings())  # Displays computed standings

@app.route('/admin/dashboard')  # Admin dashboard route
@login_required  # Requires login
@admin_required  # Restricts to admins
def admin_dashboard(): return render_template('admin/dashboard.html', users=User.query.all(), problems=Problem.query.all(), submissions=Submission.query.all())  # Shows admin overview

@app.route('/admin/add_problem', methods=['GET', 'POST'])  # Add problem route (standalone)
@app.route('/admin/add_problem/<int:contest_id>', methods=['GET', 'POST'])  # Add problem route (contest-specific)
@login_required  # Requires login
@admin_required  # Restricts to admins
def add_problem(contest_id=None):  # Adds new problem, optionally to contest
    if request.method == 'POST':  # Handles problem creation
        problem = Problem(title=request.form.get('title', '').strip(), time_limit=float(request.form.get('time_limit', 1.0)), memory_limit=int(request.form.get('memory_limit', 256)), description=request.form.get('description', '').strip(), difficulty=request.form.get('difficulty', 'Easy').strip(), tags=",".join(request.form.getlist('tags[]')) or None, contest_id=contest_id)  # Creates problem instance
        db.session.add(problem); db.session.commit()  # Saves problem
        for i, (inp, out) in enumerate(zip(request.form.getlist('input[]'), request.form.getlist('output[]'))):  # Loops through test cases
            db.session.add(TestCase(problem_id=problem.id, input_data=inp.strip(), output_data=out.strip(), is_sample=str(i) in request.form.getlist('sample[]')))  # Adds test cases
        db.session.commit(); flash('Problem added successfully', 'success'); return redirect(url_for('manage_problems', contest_id=contest_id) if contest_id else url_for('manage_problems'))  # Commits and redirects
    return render_template('admin/add_problem.html', contest_id=contest_id)  # Renders add problem form

@app.route('/admin/manage_problems')  # Manage problems route (standalone)
@app.route('/admin/manage_problems/<int:contest_id>')  # Manage problems route (contest-specific)
@login_required  # Requires login
@admin_required  # Restricts to admins
def manage_problems(contest_id=None): return render_template('admin/manage_problems.html', problems=Problem.query.filter_by(contest_id=contest_id).all() if contest_id else Problem.query.filter_by(contest_id=None).all(), contest_id=contest_id)  # Lists problems by contest or standalone

@app.route('/manage_submissions')  # Manage submissions route
@login_required  # Requires login
def manage_submissions(): return render_template('admin/manage_submissions.html', submissions=Submission.query.all())  # Displays all submissions

@app.route('/manage_users')  # Manage users route
@login_required  # Requires login
@admin_required  # Restricts to admins
def manage_users(): return render_template('admin/manage_users.html', users=User.query.all())  # Lists all users

@app.route('/delete_user/<int:user_id>', methods=['POST'])  # Delete user route
@login_required  # Requires login
@admin_required  # Restricts to admins
def delete_user(user_id):  # Removes user and their submissions
    user = User.query.get_or_404(user_id)  # Fetches user or 404
    if user.id == current_user.id: return redirect(url_for('manage_users'))  # Prevents self-deletion
    Submission.query.filter_by(user_id=user_id).delete(); db.session.delete(user); db.session.commit(); return redirect(url_for('manage_users'))  # Deletes user data and redirects

@app.route('/delete_problem/<int:problem_id>', methods=['POST'])  # Delete problem route
@login_required  # Requires login
@admin_required  # Restricts to admins
def delete_problem(problem_id):  # Removes problem and related data
    problem = Problem.query.get_or_404(problem_id)  # Fetches problem or 404
    TestCase.query.filter_by(problem_id=problem_id).delete(); Submission.query.filter_by(problem_id=problem_id).delete(); db.session.delete(problem); db.session.commit(); flash("Problem deleted successfully", "success"); return redirect(url_for('manage_problems'))  # Deletes problem assets and redirects

@app.route('/delete_submission/<int:submission_id>', methods=['POST'])  # Delete submission route
@login_required  # Requires login
def delete_submission(submission_id): db.session.delete(Submission.query.get_or_404(submission_id)); db.session.commit(); return redirect(url_for('manage_submissions'))  # Removes specific submission

@app.route('/contests', endpoint='get_contests')  # Contests listing route
def get_contests():  # Categorizes and displays contests
    now = datetime.now()  # Gets current time
    return render_template('contests.html', ongoing_contests=Contest.query.filter(and_(Contest.start_time <= now, Contest.end_time > now)).all(), upcoming_contests=Contest.query.filter(Contest.start_time > now).all(), past_contests=Contest.query.filter(Contest.end_time <= now).all(), user_participations={p.contest_id for p in ContestParticipant.query.filter_by(user_id=current_user.id).all()} if current_user.is_authenticated else set())  # Renders contests with user participation

@app.route('/join_contest/<int:contest_id>', methods=['POST'])  # Join contest route
@login_required  # Requires login
def join_contest(contest_id):  # Registers user for contest
    if ContestParticipant.query.filter_by(user_id=current_user.id, contest_id=contest_id).first(): flash("You have already joined this contest!", "info"); return redirect(url_for('get_contests'))  # Checks for existing participation
    db.session.add(ContestParticipant(user_id=current_user.id, contest_id=contest_id)); db.session.commit(); flash("Successfully registered for the contest!", "success"); return redirect(url_for('get_contests'))  # Adds participant and redirects

@app.route('/admin/add_contest', methods=['GET', 'POST'])  # Add contest route
@login_required  # Requires login
@admin_required  # Restricts to admins
def add_contest():  # Creates new contest
    if request.method == 'POST':  # Processes contest form
        try:  # Parses datetime inputs
            start, end = datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M'), datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')  # Converts form times
            now = datetime.now()  # Gets current time
            if start <= now or end <= start: flash("Invalid contest timing", "error"); return render_template('admin/add_contest.html')  # Validates timing
            db.session.add(Contest(name=request.form['name'], start_time=start, end_time=end)); db.session.commit(); flash("Contest added successfully!", "success"); return redirect(url_for('manage_contests'))  # Saves contest and redirects
        except ValueError: flash("Invalid date format", "error")  # Handles parsing errors
    return render_template('admin/add_contest.html')  # Renders add contest form

@app.route('/admin/manage_contests', methods=['GET', 'POST'])  # Manage contests route
@login_required  # Requires login
@admin_required  # Restricts to admins
def manage_contests():  # Updates or lists contests
    if request.method == 'POST':  # Handles contest update
        contest_id = request.form.get('contest_id')  # Retrieves contest ID
        contest = Contest.query.get(contest_id)  # Fetches contest object
        if contest:  # Ensures contest exists
            try:  # Parses new times
                start = datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M')  # Converts start time
                end = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')  # Converts end time
                now = datetime.now()  # Gets current time
                if start <= now or end <= start:  # Checks timing validity
                    flash("Invalid contest timing", "error")
                else:
                    contest.start_time = start  # Updates start
                    contest.end_time = end  # Updates end
                    db.session.commit()  # Saves changes
                    flash("Contest updated successfully!", "success")
            except ValueError:  # Catches invalid date formats
                flash("Invalid date format", "error")
        else:
            flash("Contest not found", "error")  # Reports missing contest
        return redirect(url_for('manage_contests'))  # Redirects after update
    contests = Contest.query.all()  # Fetches all contests
    return render_template('admin/manage_contests.html', contests=contests)  # Renders contest management page

@app.route('/admin/delete_contest/<int:contest_id>', methods=['POST'])  # Delete contest route
@login_required  # Requires login
@admin_required  # Restricts to admins
def delete_contest(contest_id):  # Removes contest and participants
    ContestParticipant.query.filter_by(contest_id=contest_id).delete(); contest = Contest.query.get(contest_id);  # Deletes participants and gets contest
    if contest: db.session.delete(contest); db.session.commit(); flash("Contest deleted successfully!", "success"); return redirect(url_for('manage_contests'))  # Deletes contest if found
    flash("Contest not found.", "danger"); return redirect(url_for('manage_contests'))  # Reports missing contest

@app.route('/contest/<int:contest_id>')  # Contest detail route
def contest_detail(contest_id):  # Shows contest specifics
    contest = Contest.query.get_or_404(contest_id)  # Fetches contest or 404
    solvers = dict(db.session.query(Submission.problem_id, func.count(func.distinct(Submission.user_id))).join(User).filter(User.role == 'participant', Submission.status == 'Accepted').group_by(Submission.problem_id).all())  # Counts solvers per problem
    standings = [{'username': participant.username, 'solved': sum(1 for problem in contest.problems if Submission.query.filter_by(user_id=participant.id, problem_id=problem.id, status='Accepted').count() > 0)} for participant in User.query.filter_by(role='participant').all()]  # Builds participant standings
    return render_template('contest_detail.html', contest=contest, problems=contest.problems, solvers_count=solvers, standings=sorted(standings, key=lambda x: x['solved'], reverse=True))  # Renders contest details with sorted standings

@app.route('/edit_problem/<int:problem_id>', methods=['GET', 'POST'])  # Edit problem route
def edit_problem(problem_id):  # Updates existing problem
    problem = Problem.query.get_or_404(problem_id)  # Fetches problem or 404
    if request.method == 'POST':  # Processes update form
        problem.title, problem.description, problem.difficulty = request.form.get('title', problem.title), request.form.get('description', problem.description), request.form.get('difficulty', 'Easy').strip()  # Updates basic fields
        problem.time_limit, problem.memory_limit = float(request.form.get('time_limit', problem.time_limit)), int(request.form.get('memory_limit', problem.memory_limit))  # Updates limits
        problem.tags = ",".join(request.form.getlist('tags[]')) or problem.tags  # Updates tags
        TestCase.query.filter_by(problem_id=problem.id).delete()  # Clears old test cases
        for i, (inp, out) in enumerate(zip(request.form.getlist('input[]'), request.form.getlist('output[]'))):  # Loops through new test cases
            db.session.add(TestCase(problem_id=problem.id, input_data=inp, output_data=out, is_sample=str(i+1) in request.form.getlist('sample[]')))  # Adds updated test cases
        db.session.commit(); flash("Problem updated successfully!", "success"); return redirect(url_for('manage_problems'))  # Saves changes and redirects
    return render_template('admin/edit_problem.html', problem=problem)  # Renders edit form