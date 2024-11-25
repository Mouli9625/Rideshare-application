# utils/decorators.py
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != role:
                flash(f'Access denied. This area is for {role}s only.')
                return redirect(url_for('auth.role_selection'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator