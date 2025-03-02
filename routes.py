import os
from flask import render_template,request,redirect,url_for,flash,jsonify
from flask_login import login_user,logout_user,login_required,current_user
from app import app,db,login_manager
from models import User,Problem,Submission,Contest,ContestParticipant,TestCase
from werkzeug.security import generate_password_hash,check_password_hash
from judging import judge_submission,calculate_standings,run_code
from datetime import datetime
from sqlalchemy import and_,or_
from collections import defaultdict
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args,**kwargs):
        if current_user.role!='admin': flash('Admin access only','error');return redirect(url_for('index'))
        return f(*args,**kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id): return User.query.get(int(user_id))

@app.route('/')
def index(): return render_template('index.html')

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        user=User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password,password): login_user(user);return redirect(url_for('problems'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        username=request.form['username']
        email=request.form['email']
        password=request.form['password']
        if User.query.filter_by(username=username).first(): flash('Username already exists')
        else:
            user=User(username=username,email=email,password=generate_password_hash(password))
            db.session.add(user);db.session.commit()
            flash('Registration successful! Please log in.');return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout(): logout_user();return redirect(url_for('index'))

@app.route('/problems')
def problems():
    search_query=request.args.get('search','')
    category_filter=request.args.get('category','')
    difficulty_filter=request.args.get('difficulty','')
    selected_tags=request.args.getlist('tags')
    problems=Problem.query.all()
    solvers_count=calculate_solvers_per_problem()
    filtered_problems=[]
    for problem in problems:
        if search_query and search_query.lower() not in problem.title.lower(): continue
        if category_filter and problem.category!=category_filter: continue
        if difficulty_filter and problem.difficulty!=difficulty_filter: continue
        if selected_tags and not any(tag in problem.tags for tag in selected_tags): continue
        filtered_problems.append((problem,solvers_count.get(problem.id,0)))
    sort_by=request.args.get('sort','solvers')
    order=request.args.get('order','desc')
    reverse_order=order=='desc'
    if sort_by=='solvers': filtered_problems.sort(key=lambda x:x[1],reverse=reverse_order)
    else: filtered_problems.sort(key=lambda x:getattr(x[0],sort_by),reverse=reverse_order)
    difficulties=['Easy','Medium','Hard','Extreme']
    tags=["brute_force","math","dp","greedy","graph","sorting","binary_search","bitwise","recursion"]
    return render_template('problems.html',problems=filtered_problems,search_query=search_query,category_filter=category_filter,difficulty_filter=difficulty_filter,selected_tags=selected_tags,difficulties=difficulties,tags=tags)

def calculate_solvers_per_problem():
    solvers_count=defaultdict(int)
    users=User.query.filter_by(role='participant').all()
    for user in users:
        solved_problems=Submission.query.filter_by(user_id=user.id,status='Accepted').distinct(Submission.problem_id).all()
        for submission in solved_problems: solvers_count[submission.problem_id]+=1
    return solvers_count

@app.route('/problem/<int:id>')
@login_required
def problem(id):
    problem=Problem.query.get_or_404(id)
    description=problem.description if problem.description else "Description not available."
    sample_test_cases=TestCase.query.filter_by(problem_id=id,is_sample=True).all()
    return render_template('problem.html',problem=problem,description=description,sample_test_cases=sample_test_cases)

@app.route('/problem/<int:problem_id>',methods=['GET','POST'])
@login_required
def submit(problem_id):
    problem=Problem.query.get_or_404(problem_id)
    if request.method=='POST':
        code=request.form['code']
        language=request.form.get('language','cpp')
        submission=Submission(user_id=current_user.id,problem_id=problem_id,code=code,language=language)
        db.session.add(submission);db.session.commit()
        judge_submission(submission);db.session.refresh(submission)
        flash(f'Submission #{submission.id} judged: {submission.status}','success');return redirect(url_for('problems'))
    return render_template('problem.html',problem=problem)

@app.route('/submissions')
@login_required
def submission_history():
    show_only_mine=request.args.get('mine','false')=='true'
    submissions=Submission.query.filter_by(user_id=current_user.id).order_by(Submission.timestamp.desc()).all() if show_only_mine else Submission.query.order_by(Submission.timestamp.desc()).all()
    return render_template('submission_history.html',submissions=submissions,show_only_mine=show_only_mine)

@app.route('/problem/<int:problem_id>/run',methods=['POST'])
@login_required
def run(problem_id):
    code=request.form['code']
    language=request.form.get('language','cpp')
    result=run_code(problem_id,code,language,current_user.id)
    return jsonify(result)

@app.route('/leaderboard')
def leaderboard(): standings=calculate_standings();return render_template('leaderboard.html',standings=standings)

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    users=User.query.all()
    problems=Problem.query.all()
    submissions=Submission.query.all()
    return render_template('admin/dashboard.html',users=users,problems=problems,submissions=submissions)

@app.route('/admin/add_problem',methods=['GET','POST'])
@login_required
@admin_required
def add_problem():
    if request.method=='POST':
        title=request.form.get('title','').strip()
        time_limit=float(request.form.get('time_limit',1.0))
        memory_limit=int(request.form.get('memory_limit',256))
        description=request.form.get('description','').strip()
        difficulty=request.form.get('difficulty','Easy').strip()
        tags_string=",".join(request.form.getlist('tags[]')) if request.form.getlist('tags[]') else None
        problem=Problem(title=title,time_limit=time_limit,memory_limit=memory_limit,description=description,difficulty=difficulty,tags=tags_string)
        db.session.add(problem);db.session.commit()
        test_inputs,test_outputs,sample_indices=request.form.getlist('input[]'),request.form.getlist('output[]'),request.form.getlist('sample[]')
        for i in range(len(test_inputs)):
            test_case=TestCase(problem_id=problem.id,input_data=test_inputs[i].strip(),output_data=test_outputs[i].strip(),is_sample=str(i) in sample_indices)
            db.session.add(test_case)
        db.session.commit();flash('Problem added successfully','success');return redirect(url_for('admin_dashboard'))
    return render_template('admin/add_problem.html')

@app.route('/manage_problems')
@login_required
def manage_problems(): problems=Problem.query.all();return render_template('admin/manage_problems.html',problems=problems)

@app.route('/manage_submissions')
@login_required
def manage_submissions(): submissions=Submission.query.all();return render_template('admin/manage_submissions.html',submissions=submissions)

@app.route('/manage_users')
@login_required
@admin_required
def manage_users(): users=User.query.all();return render_template('admin/manage_users.html',users=users)

@app.route('/delete_user/<int:user_id>',methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user=User.query.get_or_404(user_id)
    if user.id==current_user.id: return redirect(url_for('manage_users'))
    Submission.query.filter_by(user_id=user_id).delete();db.session.delete(user);db.session.commit()
    return redirect(url_for('manage_users'))

@app.route('/delete_problem/<int:problem_id>',methods=['POST'])
@login_required
@admin_required
def delete_problem(problem_id):
    problem=Problem.query.get_or_404(problem_id)
    if problem:
        TestCase.query.filter_by(problem_id=problem_id).delete();Submission.query.filter_by(problem_id=problem_id).delete();Problem.query.filter_by(id=problem_id).delete()
        db.session.delete(problem);db.session.commit();flash("Problem deleted successfully","success")
    else: flash("Problem not found","error")
    return redirect(url_for('manage_problems'))

@app.route('/delete_submission/<int:submission_id>',methods=['POST'])
@login_required
def delete_submission(submission_id):
    submission=Submission.query.get_or_404(submission_id)
    db.session.delete(submission);db.session.commit()
    return redirect(url_for('manage_submissions'))

@app.route('/contests',endpoint='get_contests')
def get_contests():
    current_time=datetime.utcnow()
    ongoing_contests=Contest.query.filter(Contest.end_time>current_time).all()
    upcoming_contests=Contest.query.filter(Contest.start_time>current_time).all()
    past_contests=Contest.query.filter(Contest.end_time<current_time).all()
    return render_template('contests.html',ongoing_contests=ongoing_contests,upcoming_contests=upcoming_contests,past_contests=past_contests)

@app.route('/admin/add_contest',methods=['GET','POST'])
@login_required
@admin_required
def add_contest():
    if request.method=='POST':
        name=request.form['name']
        try:
            start_time=datetime.strptime(request.form['start_time'],'%Y-%m-%dT%H:%M')
            end_time=datetime.strptime(request.form['end_time'],'%Y-%m-%dT%H:%M')
        except ValueError: flash("Invalid date format. Please use the correct format.","error");return render_template('admin/add_contest.html')
        now=datetime.utcnow()
        if start_time<=now: flash("Contest start time must be in the future.","error");return render_template('admin/add_contest.html')
        if end_time<=start_time: flash("Contest end time must be after the start time.","error");return render_template('admin/add_contest.html')
        contest=Contest(name=name,start_time=start_time,end_time=end_time)
        db.session.add(contest);db.session.commit();flash("Contest added successfully!","success");return redirect(url_for('admin_dashboard'))
    return render_template('admin/add_contest.html')

@app.route('/admin/manage_contests')
@login_required
@admin_required
def manage_contests(): contests=Contest.query.all();return render_template('admin/manage_contests.html',contests=contests)

@app.route('/admin/delete_contest/<int:contest_id>',methods=['POST'])
@login_required
@admin_required
def delete_contest(contest_id):
    contest=Contest.query.get(contest_id)
    if contest: db.session.delete(contest);db.session.commit();flash("Contest deleted successfully!","success")
    else: flash("Contest not found.","danger")
    return redirect(url_for('manage_contests'))

@app.route('/contest/<int:contest_id>')
def contest_detail(contest_id):
    contest=Contest.query.get_or_404(contest_id)
    problem_sets=contest.problem_sets
    participation_options=contest.participation_options if contest.participation_options else []
    return render_template('contest_detail.html',contest=contest,problem_sets=problem_sets,participation_options=participation_options)

@app.route('/join_contest/<int:contest_id>',methods=['POST'])
def join_contest(contest_id): pass

@app.route('/edit_problem/<int:problem_id>',methods=['GET','POST'])
def edit_problem(problem_id):
    problem=Problem.query.get_or_404(problem_id)
    if request.method=='POST':
        problem.title=request.form.get('title')
        problem.description=request.form.get('description')
        problem.time_limit=float(request.form.get('time_limit',1.0))
        problem.memory_limit=int(request.form.get('memory_limit',256))
        problem.difficulty=request.form.get('difficulty','Easy').strip()
        problem.tags=",".join(request.form.getlist('tags[]')) if request.form.getlist('tags[]') else None
        TestCase.query.filter_by(problem_id=problem.id).delete()
        inputs,outputs,sample_cases=request.form.getlist('input[]'),request.form.getlist('output[]'),request.form.getlist('sample[]')
        for i in range(len(inputs)):
            test_case=TestCase(problem_id=problem.id,input_data=inputs[i],output_data=outputs[i],is_sample=(str(i+1) in sample_cases))
            db.session.add(test_case)
        db.session.commit();flash("Problem updated successfully!","success");return redirect(url_for('manage_problems'))
    return render_template('admin/edit_problem.html',problem=problem)