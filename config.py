import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-me'
    # Add more base configurations here as needed

class DevelopmentConfig(Config):
    """Development specific configuration."""
    DEBUG = True
    ENV = 'development'

class ProductionConfig(Config):
    """Production specific configuration."""
    DEBUG = False
    ENV = 'production'
    # Use real secrets and database URIs in production

# Dictionary to map environment name to config class
config_by_name = dict(
    development=DevelopmentConfig,
    production=ProductionConfig
)
