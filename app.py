import os
import logging
from datetime import datetime
from flask import Flask
from flask_login import LoginManager
from config import Config

logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
from models import db, User, Group, Expense, Notification
db.init_app(app)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# Create database tables if they don't exist
with app.app_context():
    db.create_all()
