from app import create_app
from app.extensions import db
import sqlalchemy

app = create_app()

with app.app_context():
    engine = db.engine
    inspector = sqlalchemy.inspect(engine)
    
    if 'practice_attempts' not in inspector.get_table_names():
        print("Creating 'practice_attempts' table...")
        from app.models.practice_attempt import PracticeAttempt
        from app.models.user import User
        from app.models.lesson import Lesson
        PracticeAttempt.__table__.create(engine)
        print("Table 'practice_attempts' created successfully.")
    else:
        print("Table 'practice_attempts' already exists. Skipping.")
