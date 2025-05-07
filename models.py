from datetime import datetime
import uuid
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin):
    def __init__(self, username, email, password):
        self.id = username
        self.username = username
        self.email = email
        self.password_hash = generate_password_hash(password)
        self.created_at = datetime.now()
        self.groups = []  # List of group IDs the user belongs to
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at,
            'groups': self.groups
        }

class Group:
    def __init__(self, name, created_by):
        self.id = str(uuid.uuid4())
        self.name = name
        self.created_by = created_by
        self.created_at = datetime.now()
        self.invite_code = str(uuid.uuid4())[:8]  # Short invite code
        self.members = [created_by]  # List of user IDs who are members
        self.expenses = []  # List of expense IDs associated with this group
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_by': self.created_by,
            'created_at': self.created_at,
            'invite_code': self.invite_code,
            'members': self.members,
            'expenses': self.expenses
        }

class Expense:
    def __init__(self, group_id, amount, description, date, payer, participants, currency='USD', custom_splits=None):
        self.id = str(uuid.uuid4())
        self.group_id = group_id
        self.amount = float(amount)
        self.description = description
        self.date = date
        self.payer = payer  # User ID of who paid
        self.participants = participants  # List of user IDs who share the expense
        self.currency = currency
        # If custom_splits is None, equal splits assumed
        # Otherwise, it's a dict mapping user_id -> percentage (0-100)
        self.custom_splits = custom_splits if custom_splits else None
        self.created_at = datetime.now()
    
    def get_split_for_user(self, user_id):
        """Calculate how much this user owes or is owed for this expense"""
        if user_id not in self.participants:
            return 0
        
        if self.custom_splits:
            # Custom split based on percentages
            if user_id in self.custom_splits:
                share = self.amount * (self.custom_splits[user_id] / 100.0)
            else:
                share = 0
        else:
            # Equal split
            share = self.amount / len(self.participants)
        
        # If user is the payer, they paid the full amount but owe their share
        if user_id == self.payer:
            return self.amount - share  # Positive: user is owed money
        else:
            return -share  # Negative: user owes money
    
    def to_dict(self):
        return {
            'id': self.id,
            'group_id': self.group_id,
            'amount': self.amount,
            'description': self.description,
            'date': self.date,
            'payer': self.payer,
            'participants': self.participants,
            'currency': self.currency,
            'custom_splits': self.custom_splits,
            'created_at': self.created_at
        }

class Notification:
    def __init__(self, user_id, title, message, link=None):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.title = title
        self.message = message
        self.link = link
        self.read = False
        self.created_at = datetime.now()
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'link': self.link,
            'read': self.read,
            'created_at': self.created_at
        }
