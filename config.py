import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration."""
    # Application settings
    SECRET_KEY = os.environ.get('SESSION_SECRET', 'dev-secret-key')
    DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 't')

    # Database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # API keys
    RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
    CURRENCY_API_KEY = os.environ.get('CURRENCY_API_KEY')

    # Other settings
    # ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
