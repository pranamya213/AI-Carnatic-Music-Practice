import random
import string
from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

teacher_student = db.Table('teacher_student',
    db.Column('teacher_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('student_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

class User(UserMixin, db.Model):
    """User model for authentication and role management."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')
    teacher_code = db.Column(db.String(20), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    students = db.relationship(
        'User', secondary=teacher_student,
        primaryjoin=(teacher_student.c.teacher_id == id),
        secondaryjoin=(teacher_student.c.student_id == id),
        backref=db.backref('teachers', lazy='dynamic'), lazy='dynamic'
    )

    def set_password(self, password):
        """Hash the password and store it."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the hash."""
        return check_password_hash(self.password_hash, password)

    def generate_teacher_code(self):
        """Generate a unique teacher code."""
        if not self.teacher_code and self.role == 'teacher':
            while True:
                code = 'TCH-' + ''.join(random.choices(string.digits, k=4))
                # Ensure uniqueness
                if not User.query.filter_by(teacher_code=code).first():
                    self.teacher_code = code
                    break

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'
