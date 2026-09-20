from app.extensions import db
from datetime import datetime

class Lesson(db.Model):
    """Lesson model for teacher-guided Carnatic music practice."""
    __tablename__ = 'lessons'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    raga = db.Column(db.String(100), nullable=False)
    shruti = db.Column(db.String(10), nullable=False)
    tala = db.Column(db.String(50), nullable=False)
    laya = db.Column(db.String(50), nullable=False)
    
    # Phase 4: Category and Exercise Organization
    category = db.Column(db.String(100), nullable=False, default="Other")
    exercise_name = db.Column(db.String(200), nullable=False, default="Exercise")
    exercise_number = db.Column(db.Integer, nullable=True)

    description = db.Column(db.Text, nullable=True)
    reference_audio_filename = db.Column(db.String(255), nullable=True)
    
    # Phase 5: Audio Processing Metadata
    audio_duration = db.Column(db.Float, nullable=True)
    audio_original_sr = db.Column(db.Integer, nullable=True)
    audio_analysis_sr = db.Column(db.Integer, nullable=True)
    audio_channels = db.Column(db.Integer, nullable=True)
    audio_waveform_filename = db.Column(db.String(255), nullable=True)
    audio_processing_status = db.Column(db.String(50), default="Pending")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to User (Teacher)
    teacher = db.relationship('User', backref=db.backref('lessons', lazy=True))

    def __repr__(self):
        return f'<Lesson {self.title} (Teacher ID: {self.teacher_id})>'
