import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-me'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload configurations
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads', 'lessons')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB limit

    # Add more base configurations here as needed

class DevelopmentConfig(Config):
    """Development specific configuration."""
    DEBUG = True
    ENV = 'development'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'carnatic_dev.sqlite')

class ProductionConfig(Config):
    """Production specific configuration."""
    DEBUG = False
    ENV = 'production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'carnatic_prod.sqlite')
    # Use real secrets and database URIs in production

# Dictionary to map environment name to config class
config_by_name = dict(
    development=DevelopmentConfig,
    production=ProductionConfig
)
