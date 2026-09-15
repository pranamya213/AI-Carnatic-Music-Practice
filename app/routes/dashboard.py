from flask import Blueprint, render_template
from flask_login import login_required
from app.utilities.decorators import role_required

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/student')
@login_required
@role_required('student')
def student():
    return render_template('dashboard/student.html')

@dashboard_bp.route('/teacher')
@login_required
@role_required('teacher')
def teacher():
    return render_template('dashboard/teacher.html')

@dashboard_bp.route('/admin')
@login_required
@role_required('admin')
def admin():
    return render_template('dashboard/admin.html')
