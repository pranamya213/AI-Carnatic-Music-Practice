import os
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, abort
from flask_login import login_required, current_user
from app.utilities.decorators import role_required
from app.models.lesson import Lesson
from app.models.user import User
from app.models.practice_attempt import PracticeAttempt
from app.extensions import db
from app.services.audio_processor import process_reference_audio
from app.services.pitch_analyzer import analyze_pitch_for_lesson
from app.services.swara_mapper import analyze_swaras_for_lesson

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
        categories = {}
        for lesson in lessons:
            cat = lesson.category
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1
    else:
        categories = {}
        
    return render_template('dashboard/student.html', categories=categories)

@dashboard_bp.route('/student/lessons/category/<string:category>')
@login_required
@role_required('student')
def student_category_lessons(category):
    teacher_ids = [t.id for t in current_user.teachers]
    if not teacher_ids:
        return redirect(url_for('dashboard.student'))
        
    lessons = Lesson.query.filter(
        Lesson.teacher_id.in_(teacher_ids),
        Lesson.category == category
    ).order_by(Lesson.exercise_number.asc().nullslast(), Lesson.created_at.desc()).all()
    
    return render_template('dashboard/category_lessons.html', category=category, lessons=lessons)

@dashboard_bp.route('/student/lessons/<int:lesson_id>')
@login_required
@role_required('student')
def student_lesson_details(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    teacher_ids = [t.id for t in current_user.teachers]
    if lesson.teacher_id not in teacher_ids:
        abort(403)
    attempts = PracticeAttempt.query.filter_by(lesson_id=lesson.id, student_id=current_user.id).order_by(PracticeAttempt.created_at.desc()).all()
    return render_template('dashboard/lesson_details.html', lesson=lesson, attempts=attempts, is_teacher=False)

@dashboard_bp.route('/teacher')
@login_required
@role_required('teacher')
def teacher():
    if not current_user.teacher_code:
        current_user.generate_teacher_code()
        db.session.commit()
        
    lessons = Lesson.query.filter_by(teacher_id=current_user.id).order_by(Lesson.category.asc(), Lesson.exercise_number.asc().nullslast(), Lesson.created_at.desc()).all()
    
    # Group lessons by category
    lessons_by_category = {}
    for lesson in lessons:
        cat = lesson.category
        if cat not in lessons_by_category:
            lessons_by_category[cat] = []
        lessons_by_category[cat].append(lesson)
        
    students = current_user.students.all()
    return render_template('dashboard/teacher.html', lessons_by_category=lessons_by_category, students=students)

@dashboard_bp.route('/teacher/lessons/new', methods=['GET', 'POST'])
@login_required
@role_required('teacher')
def create_lesson():
    if request.method == 'POST':
        category = request.form.get('category')
        exercise_name = request.form.get('exercise_name')
        exercise_number = request.form.get('exercise_number')
        if exercise_number:
            try:
                exercise_number = int(exercise_number)
            except ValueError:
                exercise_number = None
        else:
            exercise_number = None
            
        title = request.form.get('title')
        raga = request.form.get('raga')
        shruti = request.form.get('shruti')
        tala = request.form.get('tala')
        laya = request.form.get('laya')
        description = request.form.get('description')
        
        expected_swara_sequence = request.form.get('expected_swara_sequence')
        if expected_swara_sequence:
            expected_swara_sequence = expected_swara_sequence.strip()
        else:
            expected_swara_sequence = None
        
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
            category=category,
            exercise_name=exercise_name,
            exercise_number=exercise_number,
            title=title,
            raga=raga,
            shruti=shruti,
            tala=tala,
            laya=laya,
            description=description,
            expected_swara_sequence=expected_swara_sequence,
            reference_audio_filename=filename
        )
        
        # Audio Processing
        if filename:
            try:
                metadata = process_reference_audio(file_path, current_app.config['UPLOAD_FOLDER'], filename)
                new_lesson.audio_duration = metadata['audio_duration']
                new_lesson.audio_original_sr = metadata['audio_original_sr']
                new_lesson.audio_analysis_sr = metadata['audio_analysis_sr']
                new_lesson.audio_channels = metadata['audio_channels']
                new_lesson.audio_waveform_filename = metadata['audio_waveform_filename']
                new_lesson.audio_processing_status = metadata['audio_processing_status']
                
                # Phase 6: Pitch Analysis
                try:
                    pitch_metadata = analyze_pitch_for_lesson(file_path, current_app.config['UPLOAD_FOLDER'], filename)
                    new_lesson.pitch_analysis_status = pitch_metadata['pitch_analysis_status']
                    new_lesson.pitch_data_filename = pitch_metadata['pitch_data_filename']
                    new_lesson.pitch_plot_filename = pitch_metadata['pitch_plot_filename']
                    new_lesson.pitch_analysis_method = pitch_metadata['pitch_analysis_method']
                    new_lesson.pitch_fmin = pitch_metadata['pitch_fmin']
                    new_lesson.pitch_fmax = pitch_metadata['pitch_fmax']
                    new_lesson.pitch_median = pitch_metadata['pitch_median']
                    new_lesson.pitch_min = pitch_metadata['pitch_min']
                    new_lesson.pitch_max = pitch_metadata['pitch_max']
                    new_lesson.pitch_voiced_percentage = pitch_metadata['pitch_voiced_percentage']
                except Exception as e:
                    current_app.logger.error(f"Error extracting pitch for lesson: {e}")
                    new_lesson.pitch_analysis_status = "Failed"
                    
            except Exception as e:
                current_app.logger.exception(f"Error processing audio for lesson: {e}")
                new_lesson.audio_processing_status = "Failed"
                new_lesson.pitch_analysis_status = "Failed"
        
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
        lesson.category = request.form.get('category')
        lesson.exercise_name = request.form.get('exercise_name')
        exercise_number = request.form.get('exercise_number')
        if exercise_number:
            try:
                lesson.exercise_number = int(exercise_number)
            except ValueError:
                lesson.exercise_number = None
        else:
            lesson.exercise_number = None
            
        lesson.title = request.form.get('title')
        lesson.raga = request.form.get('raga')
        lesson.shruti = request.form.get('shruti')
        lesson.tala = request.form.get('tala')
        lesson.laya = request.form.get('laya')
        lesson.description = request.form.get('description')
        
        expected_swara_sequence = request.form.get('expected_swara_sequence')
        if expected_swara_sequence:
            lesson.expected_swara_sequence = expected_swara_sequence.strip()
        else:
            lesson.expected_swara_sequence = None
            
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
                if lesson.audio_waveform_filename:
                    old_wf_path = os.path.join(current_app.config['UPLOAD_FOLDER'], lesson.audio_waveform_filename)
                    if os.path.exists(old_wf_path):
                        try:
                            os.remove(old_wf_path)
                        except OSError:
                            pass
                
                lesson.reference_audio_filename = filename
                
                # Audio Processing for new file
                try:
                    metadata = process_reference_audio(file_path, current_app.config['UPLOAD_FOLDER'], filename)
                    lesson.audio_duration = metadata['audio_duration']
                    lesson.audio_original_sr = metadata['audio_original_sr']
                    lesson.audio_analysis_sr = metadata['audio_analysis_sr']
                    lesson.audio_channels = metadata['audio_channels']
                    lesson.audio_waveform_filename = metadata['audio_waveform_filename']
                    lesson.audio_processing_status = metadata['audio_processing_status']
                    
                    # Phase 6: Pitch Analysis
                    try:
                        pitch_metadata = analyze_pitch_for_lesson(file_path, current_app.config['UPLOAD_FOLDER'], filename)
                        lesson.pitch_analysis_status = pitch_metadata['pitch_analysis_status']
                        lesson.pitch_data_filename = pitch_metadata['pitch_data_filename']
                        lesson.pitch_plot_filename = pitch_metadata['pitch_plot_filename']
                        lesson.pitch_analysis_method = pitch_metadata['pitch_analysis_method']
                        lesson.pitch_fmin = pitch_metadata['pitch_fmin']
                        lesson.pitch_fmax = pitch_metadata['pitch_fmax']
                        lesson.pitch_median = pitch_metadata['pitch_median']
                        lesson.pitch_min = pitch_metadata['pitch_min']
                        lesson.pitch_max = pitch_metadata['pitch_max']
                        lesson.pitch_voiced_percentage = pitch_metadata['pitch_voiced_percentage']
                    except Exception as e:
                        current_app.logger.error(f"Error extracting pitch for lesson edit: {e}")
                        lesson.pitch_analysis_status = "Failed"
                        
                except Exception as e:
                    current_app.logger.exception(f"Error processing audio for lesson edit: {e}")
                    lesson.audio_processing_status = "Failed"
                    lesson.pitch_analysis_status = "Failed"
                    
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

@dashboard_bp.route('/teacher/lessons/<int:lesson_id>/analyze_pitch', methods=['POST'])
@login_required
@role_required('teacher')
def analyze_pitch_route(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.teacher_id != current_user.id:
        abort(403)
        
    if not lesson.reference_audio_filename:
        flash("No reference audio to analyze.", "danger")
        return redirect(url_for('dashboard.teacher_lesson_details', lesson_id=lesson.id))
        
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], lesson.reference_audio_filename)
    if not os.path.exists(file_path):
        flash("Reference audio file not found on server.", "danger")
        return redirect(url_for('dashboard.teacher_lesson_details', lesson_id=lesson.id))
        
    try:
        pitch_metadata = analyze_pitch_for_lesson(file_path, current_app.config['UPLOAD_FOLDER'], lesson.reference_audio_filename)
        lesson.pitch_analysis_status = pitch_metadata['pitch_analysis_status']
        lesson.pitch_data_filename = pitch_metadata['pitch_data_filename']
        lesson.pitch_plot_filename = pitch_metadata['pitch_plot_filename']
        lesson.pitch_analysis_method = pitch_metadata['pitch_analysis_method']
        lesson.pitch_fmin = pitch_metadata['pitch_fmin']
        lesson.pitch_fmax = pitch_metadata['pitch_fmax']
        lesson.pitch_median = pitch_metadata['pitch_median']
        lesson.pitch_min = pitch_metadata['pitch_min']
        lesson.pitch_max = pitch_metadata['pitch_max']
        lesson.pitch_voiced_percentage = pitch_metadata['pitch_voiced_percentage']
        db.session.commit()
        flash('Pitch analysis completed successfully.', 'success')
    except Exception as e:
        current_app.logger.error(f"Error extracting pitch manually: {e}")
        lesson.pitch_analysis_status = "Failed"
        db.session.commit()
        flash('Pitch analysis failed. Please try again.', 'danger')
        
    return redirect(url_for('dashboard.teacher_lesson_details', lesson_id=lesson.id))

@dashboard_bp.route('/teacher/lessons/<int:lesson_id>/analyze_swaras', methods=['POST'])
@login_required
@role_required('teacher')
def analyze_swaras_route(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.teacher_id != current_user.id:
        abort(403)
        
    if not lesson.pitch_data_filename:
        flash("Phase 6 Pitch Analysis data is missing. Please run Pitch Analysis first.", "danger")
        return redirect(url_for('dashboard.teacher_lesson_details', lesson_id=lesson.id))
        
    if not lesson.shruti:
        flash("Swara analysis requires a valid tonic/shruti.", "danger")
        return redirect(url_for('dashboard.teacher_lesson_details', lesson_id=lesson.id))
        
    try:
        swara_metadata = analyze_swaras_for_lesson(lesson, current_app.config['UPLOAD_FOLDER'])
        lesson.swara_analysis_status = swara_metadata['swara_analysis_status']
        lesson.swara_data_filename = swara_metadata['swara_data_filename']
        lesson.swara_plot_filename = swara_metadata['swara_plot_filename']
        lesson.swara_analysis_method = swara_metadata['swara_analysis_method']
        lesson.tonic_frequency = swara_metadata['tonic_frequency']
        lesson.swara_voiced_percentage = swara_metadata['swara_voiced_percentage']
        db.session.commit()
        flash('Swara mapping completed successfully.', 'success')
    except Exception as e:
        current_app.logger.error(f"Error mapping swaras manually: {e}")
        lesson.swara_analysis_status = "Failed"
        db.session.commit()
        flash('Swara mapping failed. Please try again.', 'danger')
        
    return redirect(url_for('dashboard.teacher_lesson_details', lesson_id=lesson.id))

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

@dashboard_bp.route('/student/lessons/<int:lesson_id>/practice', methods=['POST'])
@login_required
@role_required('student')
def upload_practice_recording(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    teacher_ids = [t.id for t in current_user.teachers]
    if lesson.teacher_id not in teacher_ids:
        abort(403)
        
    file = request.files.get('practice_audio')
    if not file or file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('dashboard.student_lesson_details', lesson_id=lesson.id))
        
    if not allowed_file(file.filename):
        flash('Invalid file format. Allowed formats: WAV, MP3, M4A.', 'danger')
        return redirect(url_for('dashboard.student_lesson_details', lesson_id=lesson.id))
        
    filename = secure_filename(file.filename)
    import time
    filename = f"attempt_{current_user.id}_{lesson.id}_{int(time.time())}_{filename}"
    
    practice_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'practice')
    os.makedirs(practice_dir, exist_ok=True)
    
    file_path = os.path.join(practice_dir, filename)
    file.save(file_path)
    
    # Create DB record
    attempt = PracticeAttempt(
        lesson_id=lesson.id,
        student_id=current_user.id,
        practice_audio_filename=filename,
        practice_audio_processing_status="Processing"
    )
    db.session.add(attempt)
    db.session.commit()
    
    # Process audio
    try:
        from app.services.audio_processor import load_audio, validate_audio_file
        is_valid, error_msg = validate_audio_file(file_path)
        if not is_valid:
            raise ValueError(error_msg)
            
        target_sr = 22050
        y, sr, orig_sr, duration, channels = load_audio(file_path, target_sr=target_sr)
        
        attempt.practice_audio_duration = duration
        attempt.practice_audio_original_sr = orig_sr
        attempt.practice_audio_analysis_sr = sr
        attempt.practice_audio_channels = channels
        attempt.practice_audio_processing_status = "Ready"
        
    except Exception as e:
        current_app.logger.exception(f"Error processing practice audio: {e}")
        attempt.practice_audio_processing_status = "Failed"
        flash(f'Processing failed: {str(e)}', 'danger')
    
    db.session.commit()
    if attempt.practice_audio_processing_status == "Ready":
        flash('Practice recording uploaded and processed successfully.', 'success')
        
    return redirect(url_for('dashboard.student_lesson_details', lesson_id=lesson.id))

@dashboard_bp.route('/uploads/practice/<filename>')
@login_required
@role_required('student')
def uploaded_practice_file(filename):
    # Verify ownership before serving
    attempt = PracticeAttempt.query.filter_by(practice_audio_filename=filename).first_or_404()
    if attempt.student_id != current_user.id:
        abort(403)
    practice_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'practice')
    return send_from_directory(practice_dir, filename)

@dashboard_bp.route('/student/lessons/<int:lesson_id>/practice/<int:attempt_id>/compare', methods=['POST'])
@login_required
@role_required('student')
def compare_practice_attempt(lesson_id, attempt_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    attempt = PracticeAttempt.query.get_or_404(attempt_id)
    
    if attempt.student_id != current_user.id or attempt.lesson_id != lesson.id:
        abort(403)
        
    student_shruti = request.form.get('student_shruti')
    if not student_shruti:
        student_shruti = lesson.shruti # Default to teacher's shruti
        
    try:
        from app.services.performance_comparator import compare_performances
        from datetime import datetime
        results = compare_performances(lesson, attempt, current_app.config['UPLOAD_FOLDER'], student_shruti)
        
        attempt.comparison_status = results['comparison_status']
        attempt.comparison_data_filename = results['comparison_data_filename']
        attempt.comparison_plot_filename = results['comparison_plot_filename']
        attempt.swara_match_percentage = results['swara_match_percentage']
        attempt.mean_pitch_deviation_cents = results['mean_pitch_deviation_cents']
        attempt.median_pitch_deviation_cents = results['median_pitch_deviation_cents']
        attempt.comparison_method = results['comparison_method']
        attempt.student_tonic_frequency = results['student_tonic_frequency']
        attempt.comparison_created_at = datetime.utcnow()
        
        db.session.commit()
        flash('Comparison completed successfully.', 'success')
        
    except Exception as e:
        current_app.logger.exception(f"Error comparing performance: {e}")
        attempt.comparison_status = "Failed"
        db.session.commit()
        flash(f'Comparison failed: {str(e)}', 'danger')
        
    return redirect(url_for('dashboard.student_lesson_details', lesson_id=lesson.id))

@dashboard_bp.route('/admin')
@login_required
@role_required('admin')
def admin():
    return render_template('dashboard/admin.html')
