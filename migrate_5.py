from app import create_app
from app.extensions import db
from app.models.lesson import Lesson
from sqlalchemy import text

app = create_app('development')

def run_migration():
    with app.app_context():
        print("Starting Phase 5 Migration...")
        
        columns = [
            ("audio_duration", "FLOAT"),
            ("audio_original_sr", "INTEGER"),
            ("audio_analysis_sr", "INTEGER"),
            ("audio_channels", "INTEGER"),
            ("audio_waveform_filename", "VARCHAR(255)"),
            ("audio_processing_status", "VARCHAR(50)")
        ]
        
        for col_name, col_type in columns:
            try:
                db.session.execute(text(f'ALTER TABLE lessons ADD COLUMN {col_name} {col_type};'))
                print(f"Added {col_name} column to lessons table.")
            except Exception as e:
                if 'duplicate column name' in str(e).lower() or 'operationalerror' in str(e).lower():
                    print(f"Column {col_name} already exists or could not be added.")
                else:
                    print(f"Error adding {col_name} column: {e}")
            db.session.commit()

        # Backfill existing lessons
        print("Backfilling existing lessons...")
        lessons = Lesson.query.all()
        for lesson in lessons:
            modified = False
            if lesson.audio_processing_status is None:
                lesson.audio_processing_status = "Pending"
                modified = True
            if modified:
                print(f"Updated lesson {lesson.id} with default audio status.")
        
        db.session.commit()
        print("Migration complete.")

if __name__ == '__main__':
    run_migration()
