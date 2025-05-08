import os

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SESSION_SECRET', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://ExpenseSplitter_owner:npg_lwcyRgUBx6s1@ep-raspy-mud-a4o8lo1t-pooler.us-east-1.aws.neon.tech/ExpenseSplitter?sslmode=require')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
