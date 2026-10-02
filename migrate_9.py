from app import create_app
from app.extensions import db
import sqlalchemy

app = create_app()

with app.app_context():
    engine = db.engine
    inspector = sqlalchemy.inspect(engine)
    
    columns = [col['name'] for col in inspector.get_columns('practice_attempts')]
    
    if 'comparison_status' not in columns:
        print("Adding Phase 9 columns to 'practice_attempts' table...")
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text('ALTER TABLE practice_attempts ADD COLUMN student_tonic_frequency FLOAT'))
            conn.execute(sqlalchemy.text('ALTER TABLE practice_attempts ADD COLUMN comparison_status VARCHAR(50) DEFAULT "Not compared"'))
            conn.execute(sqlalchemy.text('ALTER TABLE practice_attempts ADD COLUMN comparison_data_filename VARCHAR(255)'))
            conn.execute(sqlalchemy.text('ALTER TABLE practice_attempts ADD COLUMN comparison_plot_filename VARCHAR(255)'))
            conn.execute(sqlalchemy.text('ALTER TABLE practice_attempts ADD COLUMN swara_match_percentage FLOAT'))
            conn.execute(sqlalchemy.text('ALTER TABLE practice_attempts ADD COLUMN mean_pitch_deviation_cents FLOAT'))
            conn.execute(sqlalchemy.text('ALTER TABLE practice_attempts ADD COLUMN median_pitch_deviation_cents FLOAT'))
            conn.execute(sqlalchemy.text('ALTER TABLE practice_attempts ADD COLUMN comparison_method VARCHAR(50)'))
            conn.execute(sqlalchemy.text('ALTER TABLE practice_attempts ADD COLUMN comparison_created_at DATETIME'))
            conn.commit()
        print("Columns added successfully.")
    else:
        print("Columns already exist. Skipping.")
