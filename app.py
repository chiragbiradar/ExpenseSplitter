import os
import logging
from datetime import datetime
from flask import Flask
from flask_login import LoginManager

logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# In-memory data storage
users = {}  # username -> User object
groups = {}  # group_id -> Group object
expenses = {}  # expense_id -> Expense object
notifications = {}  # user_id -> list of notifications
group_memberships = {}  # group_id -> set of user_ids

# Import models after app initialization
from models import User, Group, Expense, Notification

@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)
