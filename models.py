from datetime import datetime
import uuid
import json
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Association tables for many-to-many relationships
group_members = db.Table('group_members',
    db.Column('user_id', db.String(120), db.ForeignKey('user.id'), primary_key=True),
    db.Column('group_id', db.String(36), db.ForeignKey('group.id'), primary_key=True)
)

expense_participants = db.Table('expense_participants',
    db.Column('user_id', db.String(120), db.ForeignKey('user.id'), primary_key=True),
    db.Column('expense_id', db.String(36), db.ForeignKey('expense.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.String(120), primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    preferred_currency = db.Column(db.String(3), default='USD')

    # Relationships
    groups = db.relationship('Group', secondary=group_members,
                            backref=db.backref('members_rel', lazy='dynamic'))
    expenses_paid = db.relationship('Expense', backref='payer_rel', foreign_keys='Expense.payer')
    notifications = db.relationship('Notification', backref='user', lazy=True)

    def __init__(self, username, email, password):
        self.id = username
        self.username = username
        self.email = email
        self.password_hash = generate_password_hash(password)
        self.created_at = datetime.now()
        self.preferred_currency = 'USD'

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at,
            'groups': [group.id for group in self.groups],
            'preferred_currency': self.preferred_currency
        }

class Group(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_by = db.Column(db.String(120), db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    invite_code = db.Column(db.String(8), unique=True, nullable=False)

    # Relationships
    expenses = db.relationship('Expense', backref='group', lazy=True)
    creator = db.relationship('User', foreign_keys=[created_by])

    def __init__(self, name, created_by):
        self.id = str(uuid.uuid4())
        self.name = name
        self.created_by = created_by
        self.created_at = datetime.now()
        self.invite_code = str(uuid.uuid4())[:8]

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_by': self.created_by,
            'created_at': self.created_at,
            'invite_code': self.invite_code,
            'members': [member.id for member in self.members_rel],
            'expenses': [expense.id for expense in self.expenses]
        }

class Expense(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    group_id = db.Column(db.String(36), db.ForeignKey('group.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    payer = db.Column(db.String(120), db.ForeignKey('user.id'), nullable=False)
    currency = db.Column(db.String(3), default='USD')
    custom_splits = db.Column(db.Text, nullable=True)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.now)
    settled = db.Column(db.Boolean, default=False)  # Whether the expense has been settled
    settled_at = db.Column(db.DateTime, nullable=True)  # When the expense was settled
    settled_by = db.Column(db.String(120), db.ForeignKey('user.id'), nullable=True)  # Who settled the expense

    # Relationships
    participants = db.relationship('User', secondary=expense_participants,
                                  backref=db.backref('expenses_participated', lazy='dynamic'))
    settler = db.relationship('User', foreign_keys=[settled_by], backref='settled_expenses')

    def __init__(self, group_id, amount, description, date, payer, participants=None, currency='USD', custom_splits=None):
        self.id = str(uuid.uuid4())
        self.group_id = group_id
        self.amount = float(amount)
        self.description = description
        self.date = date
        self.payer = payer
        self.currency = currency
        self.custom_splits = json.dumps(custom_splits) if custom_splits else None
        self.created_at = datetime.now()
        self.settled = False
        self.settled_at = None
        self.settled_by = None

        # Participants will be added after the object is created

    def get_custom_splits(self):
        """Get custom splits as a dictionary"""
        if self.custom_splits:
            return json.loads(self.custom_splits)
        return None

    def get_split_for_user(self, user_id):
        """Calculate how much this user owes or is owed for this expense"""
        participants_ids = [user.id for user in self.participants]

        if user_id not in participants_ids:
            return {'amount': 0, 'currency': self.currency}

        custom_splits = self.get_custom_splits()

        if custom_splits:
            # Custom split based on percentages
            if user_id in custom_splits:
                share = self.amount * (custom_splits[user_id] / 100.0)
            else:
                share = 0
        else:
            # Equal split
            share = self.amount / len(participants_ids)

        # If user is the payer, they paid the full amount but owe their share
        if user_id == self.payer:
            amount = self.amount - share  # Positive: user is owed money
        else:
            amount = -share  # Negative: user owes money

        return {'amount': amount, 'currency': self.currency}

    def to_dict(self):
        return {
            'id': self.id,
            'group_id': self.group_id,
            'amount': self.amount,
            'description': self.description,
            'date': self.date,
            'payer': self.payer,
            'participants': [user.id for user in self.participants],
            'currency': self.currency,
            'custom_splits': self.get_custom_splits(),
            'created_at': self.created_at,
            'settled': self.settled,
            'settled_at': self.settled_at,
            'settled_by': self.settled_by
        }

class Notification(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(120), db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(200), nullable=True)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

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
