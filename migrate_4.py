from app import create_app
from app.extensions import db
from app.models.lesson import Lesson
from sqlalchemy import text

app = create_app('development')

def run_migration():
    with app.app_context():
        print("Starting Phase 4 Migration...")
        
        # Add new columns safely
        try:
            db.session.execute(text('ALTER TABLE lessons ADD COLUMN category VARCHAR(100);'))
            print("Added category column to lessons table.")
        except Exception as e:
            if 'duplicate column name' in str(e).lower() or 'operationalerror' in str(e).lower():
                print("Column category already exists or could not be added.")
            else:
                print(f"Error adding category column: {e}")
        db.session.commit()

        try:
            db.session.execute(text('ALTER TABLE lessons ADD COLUMN exercise_name VARCHAR(200);'))
            print("Added exercise_name column to lessons table.")
        except Exception as e:
            if 'duplicate column name' in str(e).lower() or 'operationalerror' in str(e).lower():
                print("Column exercise_name already exists or could not be added.")
            else:
                print(f"Error adding exercise_name column: {e}")
        db.session.commit()

        try:
            db.session.execute(text('ALTER TABLE lessons ADD COLUMN exercise_number INTEGER;'))
            print("Added exercise_number column to lessons table.")
        except Exception as e:
            if 'duplicate column name' in str(e).lower() or 'operationalerror' in str(e).lower():
                print("Column exercise_number already exists or could not be added.")
            else:
                print(f"Error adding exercise_number column: {e}")
        db.session.commit()
        
        # Backfill existing lessons
        print("Backfilling existing lessons...")
        lessons = Lesson.query.all()
        for lesson in lessons:
            modified = False
            if lesson.category is None:
                lesson.category = "Other"
                modified = True
            if lesson.exercise_name is None:
                lesson.exercise_name = lesson.title
                modified = True
            if modified:
                print(f"Updated lesson {lesson.id} with default category and exercise name.")
        
        db.session.commit()
        print("Migration complete.")

if __name__ == '__main__':
    run_migration()
