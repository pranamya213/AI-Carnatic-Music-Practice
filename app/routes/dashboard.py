import os
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, abort
from flask_login import login_required, current_user
from app.utilities.decorators import role_required
from app.models.lesson import Lesson
from app.models.user import User
from app.extensions import db

dashboard_bp = Blueprint('dashboard', __name__)

ALLOWED_EXTENSIONS = {'wav', 'mp3', 'm4a'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@dashboard_bp.route('/student', methods=['GET', 'POST'])
@login_required
@role_required('student')
def student():
    if request.method == 'POST':
        teacher_code = request.form.get('teacher_code')
        if teacher_code:
            teacher = User.query.filter_by(teacher_code=teacher_code, role='teacher').first()
            if teacher:
                if teacher in current_user.teachers:
                    flash('Already connected with this teacher.', 'info')
                else:
                    current_user.teachers.append(teacher)
                    db.session.commit()
                    flash(f'Successfully connected with {teacher.name}.', 'success')
            else:
                flash('Teacher code not found.', 'danger')
        return redirect(url_for('dashboard.student'))

    teacher_ids = [t.id for t in current_user.teachers]
    if teacher_ids:
        lessons = Lesson.query.filter(Lesson.teacher_id.in_(teacher_ids)).order_by(Lesson.created_at.desc()).all()
    else:
        lessons = []
        
    return render_template('dashboard/student.html', lessons=lessons)

@dashboard_bp.route('/student/lessons/<int:lesson_id>')
@login_required
@role_required('student')
def student_lesson_details(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    teacher_ids = [t.id for t in current_user.teachers]
    if lesson.teacher_id not in teacher_ids:
        abort(403)
    return render_template('dashboard/lesson_details.html', lesson=lesson, is_teacher=False)

@dashboard_bp.route('/teacher')
@login_required
@role_required('teacher')
def teacher():
    if not current_user.teacher_code:
        current_user.generate_teacher_code()
        db.session.commit()
        
    lessons = Lesson.query.filter_by(teacher_id=current_user.id).order_by(Lesson.created_at.desc()).all()
    students = current_user.students.all()
    return render_template('dashboard/teacher.html', lessons=lessons, students=students)

@dashboard_bp.route('/teacher/lessons/new', methods=['GET', 'POST'])
@login_required
@role_required('teacher')
def create_lesson():
    if request.method == 'POST':
        title = request.form.get('title')
        raga = request.form.get('raga')
        shruti = request.form.get('shruti')
        tala = request.form.get('tala')
        laya = request.form.get('laya')
        description = request.form.get('description')
        
        file = request.files.get('reference_audio')
        filename = None
        
        if file and file.filename != '':
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to ensure uniqueness
                import time
                filename = f"{int(time.time())}_{filename}"
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
            else:
                flash('Invalid file format. Allowed formats: WAV, MP3, M4A.', 'danger')
                return redirect(request.url)
        
        new_lesson = Lesson(
            teacher_id=current_user.id,
            title=title,
            raga=raga,
            shruti=shruti,
            tala=tala,
            laya=laya,
            description=description,
            reference_audio_filename=filename
        )
        
        db.session.add(new_lesson)
        db.session.commit()
        flash('Lesson created successfully.', 'success')
        return redirect(url_for('dashboard.teacher'))
        
    return render_template('dashboard/teacher_lesson_form.html', action='Create')

@dashboard_bp.route('/teacher/lessons/<int:lesson_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('teacher')
def edit_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.teacher_id != current_user.id:
        abort(403)
        
    if request.method == 'POST':
        lesson.title = request.form.get('title')
        lesson.raga = request.form.get('raga')
        lesson.shruti = request.form.get('shruti')
        lesson.tala = request.form.get('tala')
        lesson.laya = request.form.get('laya')
        lesson.description = request.form.get('description')
        
        file = request.files.get('reference_audio')
        if file and file.filename != '':
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                import time
                filename = f"{int(time.time())}_{filename}"
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Delete old file
                if lesson.reference_audio_filename:
                    old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], lesson.reference_audio_filename)
                    if os.path.exists(old_path):
                        try:
                            os.remove(old_path)
                        except OSError:
                            pass
                
                lesson.reference_audio_filename = filename
            else:
                flash('Invalid file format. Allowed formats: WAV, MP3, M4A.', 'danger')
                return redirect(request.url)
                
        db.session.commit()
        flash('Lesson updated successfully.', 'success')
        return redirect(url_for('dashboard.teacher'))
        
    return render_template('dashboard/teacher_lesson_form.html', action='Edit', lesson=lesson)

@dashboard_bp.route('/teacher/lessons/<int:lesson_id>/delete', methods=['POST'])
@login_required
@role_required('teacher')
def delete_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.teacher_id != current_user.id:
        abort(403)
        
    if lesson.reference_audio_filename:
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], lesson.reference_audio_filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as e:
                current_app.logger.error(f"Error deleting file {file_path}: {e}")
                
    db.session.delete(lesson)
    db.session.commit()
    flash('Lesson deleted successfully.', 'success')
    return redirect(url_for('dashboard.teacher'))

@dashboard_bp.route('/teacher/lessons/<int:lesson_id>')
@login_required
@role_required('teacher')
def teacher_lesson_details(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.teacher_id != current_user.id:
        abort(403)
    return render_template('dashboard/lesson_details.html', lesson=lesson, is_teacher=True)

@dashboard_bp.route('/uploads/lessons/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@dashboard_bp.route('/admin')
@login_required
@role_required('admin')
def admin():
    return render_template('dashboard/admin.html')
