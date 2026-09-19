from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app('development')

def run_migration():
    with app.app_context():
        print("Starting Phase 3A Migration...")
        
        # 1. Add teacher_code column safely
        try:
            db.session.execute(db.text('ALTER TABLE users ADD COLUMN teacher_code VARCHAR(20);'))
            db.session.commit()
            print("Added teacher_code column to users table.")
        except Exception as e:
            db.session.rollback()
            if 'duplicate column name' in str(e).lower() or 'operationalerror' in str(e).lower():
                print("Column teacher_code already exists or could not be added (may already exist).")
            else:
                print(f"Error adding column: {e}")
        
        # 2. Create the teacher_student association table
        print("Creating association table...")
        db.create_all()
        
        # 3. Generate teacher codes for existing teachers
        teachers = User.query.filter_by(role='teacher').all()
        for teacher in teachers:
            if not teacher.teacher_code:
                teacher.generate_teacher_code()
                print(f"Generated code {teacher.teacher_code} for teacher {teacher.name}")
        
        db.session.commit()
        print("Migration complete.")

if __name__ == '__main__':
    run_migration()
