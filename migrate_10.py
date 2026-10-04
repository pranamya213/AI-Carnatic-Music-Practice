from app import create_app
from app.extensions import db
import sqlalchemy

app = create_app()

with app.app_context():
    engine = db.engine
    inspector = sqlalchemy.inspect(engine)
    
    columns = [col['name'] for col in inspector.get_columns('lessons')]
    
    if 'expected_swara_sequence' not in columns:
        print("Adding Phase 10A expected_swara_sequence column to 'lessons' table...")
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text('ALTER TABLE lessons ADD COLUMN expected_swara_sequence TEXT'))
            conn.commit()
        print("Column added successfully.")
    else:
        print("Column already exists. Skipping.")
