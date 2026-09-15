from functools import wraps
from flask import abort
from flask_login import current_user

def role_required(role):
    """
    Decorator to restrict access to a specific role.
    Assumes the user is already authenticated (use @login_required first).
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return abort(401)
            
            if current_user.role != role and current_user.role != 'admin':
                # Admins can access everything, others only their specific role
                # For this specific app, let's strictly check the role
                # as students shouldn't see teacher dashboard even if they were teachers etc.
                pass
            
            # Stricter role check as requested
            if current_user.role != role:
                return abort(403) # Forbidden
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator
