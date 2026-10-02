from app.extensions import db
from datetime import datetime

class PracticeAttempt(db.Model):
    """Model for a student's practice attempt of a lesson."""
    __tablename__ = 'practice_attempts'

    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    practice_audio_filename = db.Column(db.String(255), nullable=False)
    practice_audio_duration = db.Column(db.Float, nullable=True)
    practice_audio_original_sr = db.Column(db.Integer, nullable=True)
    practice_audio_analysis_sr = db.Column(db.Integer, nullable=True)
    practice_audio_channels = db.Column(db.Integer, nullable=True)
    practice_audio_processing_status = db.Column(db.String(50), default="Pending")
    
    # Phase 9: Comparison Metadata
    student_tonic_frequency = db.Column(db.Float, nullable=True)
    comparison_status = db.Column(db.String(50), default="Not compared")
    comparison_data_filename = db.Column(db.String(255), nullable=True)
    comparison_plot_filename = db.Column(db.String(255), nullable=True)
    swara_match_percentage = db.Column(db.Float, nullable=True)
    mean_pitch_deviation_cents = db.Column(db.Float, nullable=True)
    median_pitch_deviation_cents = db.Column(db.Float, nullable=True)
    comparison_method = db.Column(db.String(50), nullable=True)
    comparison_created_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    lesson = db.relationship('Lesson', backref=db.backref('practice_attempts', lazy=True))
    student = db.relationship('User', backref=db.backref('practice_attempts', lazy=True))

    def __repr__(self):
        return f'<PracticeAttempt {self.id} (Lesson: {self.lesson_id}, Student: {self.student_id})>'
