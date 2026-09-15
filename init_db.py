from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app('development')

def init_db():
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        
        # Create an admin user if it doesn't exist
        admin = User.query.filter_by(email='admin@carnatic.ai').first()
        if not admin:
            print("Creating default admin user...")
            admin_user = User(
                name='Platform Admin',
                email='admin@carnatic.ai',
                role='admin'
            )
            admin_user.set_password('admin123') # Default password, should be changed in production
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created successfully.")
            print("Email: admin@carnatic.ai")
            print("Password: admin123")
        else:
            print("Admin user already exists.")
            
        print("Database initialization complete.")

if __name__ == '__main__':
    init_db()
