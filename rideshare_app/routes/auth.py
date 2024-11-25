from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models.user import User
from utils.db import db

bp = Blueprint('auth', __name__)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('auth.register'))

        user = User(username=username, email=email, role=role)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash('Registration successful!')
        return redirect(url_for('auth.role_selection'))

    return render_template('auth/register.html')

@bp.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if user.role != role:
                flash(f'Access denied. This login is for {role}s only.')
                return redirect(url_for('auth.login', role=role))
            
            login_user(user)
            return redirect(url_for(f'{role}.dashboard'))
            
        flash('Invalid username or password')
    
    return render_template('auth/login.html', role=role)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.role_selection'))
@bp.route('/ai-assistance')
def ai_assistance():
    return render_template('auth/ai_assistance.html')

@bp.route('/role-selection')
def role_selection():
    return render_template('auth/role_selection.html')