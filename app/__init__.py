from flask import Flask
from config import config_by_name

def create_app(config_name='development'):
    """Application factory pattern."""
    
    # Initialize the Flask application
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config_by_name[config_name])
    
    # Initialize extensions (to be added in future phases)
    
    # Register blueprints (routes)
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)
    
    return app
