import os
import csv
import io
import json
import uuid
from datetime import datetime
from flask import render_template, redirect, url_for, request, flash, session, jsonify, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash

from app import app, users, groups, expenses, notifications
from models import User, Group, Expense, Notification
from utils import calculate_balances, get_settlement_plan, get_exchange_rates

# Home route
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('home.html')

# Authentication routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if username in users:
            flash('Username already exists!', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return render_template('register.html')
        
        # Create new user
        user = User(username=username, email=email, password=password)
        users[username] = user
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = users.get(username)
        
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out!', 'info')
    return redirect(url_for('home'))

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    user_groups = []
    for group_id in current_user.groups:
        group = groups.get(group_id)
        if group:
            user_groups.append(group)
    
    user_notifications = notifications.get(current_user.id, [])
    unread_count = sum(1 for notif in user_notifications if not notif.read)
    
    return render_template('dashboard.html', 
                          groups=user_groups, 
                          notifications=user_notifications[:5],
                          unread_count=unread_count)

# Group routes
@app.route('/groups/create', methods=['GET', 'POST'])
@login_required
def create_group():
    if request.method == 'POST':
        group_name = request.form.get('group_name')
        
        # Create new group
        group = Group(name=group_name, created_by=current_user.id)
        groups[group.id] = group
        
        # Add group to user's groups
        current_user.groups.append(group.id)
        
        flash(f'Group "{group_name}" created successfully!', 'success')
        return redirect(url_for('view_group', group_id=group.id))
    
    return render_template('create_group.html')

@app.route('/groups/join', methods=['GET', 'POST'])
@login_required
def join_group():
    if request.method == 'POST':
        invite_code = request.form.get('invite_code')
        
        # Find group with the invite code
        found_group = None
        for group in groups.values():
            if group.invite_code == invite_code:
                found_group = group
                break
        
        if found_group:
            if current_user.id in found_group.members:
                flash('You are already a member of this group!', 'info')
            else:
                # Add user to group
                found_group.members.append(current_user.id)
                # Add group to user's groups
                current_user.groups.append(found_group.id)
                
                flash(f'Successfully joined the group "{found_group.name}"!', 'success')
                return redirect(url_for('view_group', group_id=found_group.id))
        else:
            flash('Invalid invite code!', 'danger')
    
    return render_template('join_group.html')

@app.route('/groups/<group_id>')
@login_required
def view_group(group_id):
    group = groups.get(group_id)
    
    if not group or current_user.id not in group.members:
        flash('Group not found or you are not a member!', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get group members
    group_members = []
    for user_id in group.members:
        user = users.get(user_id)
        if user:
            group_members.append(user)
    
    # Get group expenses
    group_expenses = []
    for expense_id in group.expenses:
        expense = expenses.get(expense_id)
        if expense:
            group_expenses.append(expense)
    
    # Sort expenses by date (newest first)
    group_expenses.sort(key=lambda exp: exp.date, reverse=True)
    
    # Calculate balances
    balances = calculate_balances(group_id, group_expenses, group_members)
    
    # Get settlement plan
    settlement_plan = get_settlement_plan(balances)
    
    return render_template('group.html', 
                          group=group, 
                          members=group_members,
                          expenses=group_expenses[:10],  # Show only the 10 most recent
                          balances=balances,
                          settlement_plan=settlement_plan)

# Expense routes
@app.route('/groups/<group_id>/add-expense', methods=['GET', 'POST'])
@login_required
def add_expense(group_id):
    group = groups.get(group_id)
    
    if not group or current_user.id not in group.members:
        flash('Group not found or you are not a member!', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get group members for the form
    group_members = []
    for user_id in group.members:
        user = users.get(user_id)
        if user:
            group_members.append(user)
    
    # Get exchange rates for currency conversion
    exchange_rates = get_exchange_rates()
    
    if request.method == 'POST':
        amount = request.form.get('amount')
        description = request.form.get('description')
        date_str = request.form.get('date')
        payer = request.form.get('payer')
        currency = request.form.get('currency', 'USD')
        split_type = request.form.get('split_type')
        
        # Parse date
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            date = datetime.now()
        
        # Get participants
        participants = request.form.getlist('participants')
        
        # Handle custom splits if selected
        custom_splits = None
        if split_type == 'custom':
            custom_splits = {}
            for participant in participants:
                percentage = request.form.get(f'split_{participant}', '0')
                try:
                    custom_splits[participant] = float(percentage)
                except ValueError:
                    custom_splits[participant] = 0
            
            # Validate percentages add up to 100
            if sum(custom_splits.values()) != 100:
                flash('Custom split percentages must add up to 100%!', 'danger')
                return render_template('add_expense.html', 
                                      group=group, 
                                      members=group_members,
                                      exchange_rates=exchange_rates)
        
        # Create new expense
        expense = Expense(
            group_id=group_id,
            amount=float(amount),
            description=description,
            date=date,
            payer=payer,
            participants=participants,
            currency=currency,
            custom_splits=custom_splits
        )
        
        expenses[expense.id] = expense
        group.expenses.append(expense.id)
        
        # Create notifications for all participants except the one adding the expense
        for participant in participants:
            if participant != current_user.id:
                notification = Notification(
                    user_id=participant,
                    title=f"New Expense in {group.name}",
                    message=f"{current_user.username} added a new expense: {description} ({currency} {amount})",
                    link=url_for('view_group', group_id=group_id)
                )
                if participant not in notifications:
                    notifications[participant] = []
                notifications[participant].append(notification)
        
        flash('Expense added successfully!', 'success')
        return redirect(url_for('view_group', group_id=group_id))
    
    return render_template('add_expense.html', 
                          group=group, 
                          members=group_members,
                          exchange_rates=exchange_rates)

@app.route('/groups/<group_id>/expenses')
@login_required
def view_expenses(group_id):
    group = groups.get(group_id)
    
    if not group or current_user.id not in group.members:
        flash('Group not found or you are not a member!', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get all group expenses
    group_expenses = []
    for expense_id in group.expenses:
        expense = expenses.get(expense_id)
        if expense:
            # Add payer name for easier display
            payer_user = users.get(expense.payer)
            if payer_user:
                expense.payer_name = payer_user.username
            else:
                expense.payer_name = "Unknown"
            group_expenses.append(expense)
    
    # Sort expenses by date (newest first)
    group_expenses.sort(key=lambda exp: exp.date, reverse=True)
    
    return render_template('expenses.html', 
                          group=group, 
                          expenses=group_expenses)

@app.route('/groups/<group_id>/settlements')
@login_required
def view_settlements(group_id):
    group = groups.get(group_id)
    
    if not group or current_user.id not in group.members:
        flash('Group not found or you are not a member!', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get group members
    group_members = []
    for user_id in group.members:
        user = users.get(user_id)
        if user:
            group_members.append(user)
    
    # Get group expenses
    group_expenses = []
    for expense_id in group.expenses:
        expense = expenses.get(expense_id)
        if expense:
            group_expenses.append(expense)
    
    # Calculate balances
    balances = calculate_balances(group_id, group_expenses, group_members)
    
    # Get settlement plan
    settlement_plan = get_settlement_plan(balances)
    
    return render_template('settlements.html', 
                          group=group, 
                          balances=balances,
                          settlement_plan=settlement_plan)

# Export routes
@app.route('/groups/<group_id>/export')
@login_required
def export_group_data(group_id):
    group = groups.get(group_id)
    
    if not group or current_user.id not in group.members:
        flash('Group not found or you are not a member!', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get group members
    group_members = {}
    for user_id in group.members:
        user = users.get(user_id)
        if user:
            group_members[user_id] = user
    
    # Get group expenses
    group_expenses = []
    for expense_id in group.expenses:
        expense = expenses.get(expense_id)
        if expense:
            group_expenses.append(expense)
    
    # Create CSV file in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Date', 'Description', 'Amount', 'Currency', 'Paid By', 'Participants', 'Split Type'])
    
    # Write expenses
    for expense in group_expenses:
        payer_name = group_members.get(expense.payer, User('Unknown', '', '')).username
        participants_names = [group_members.get(p, User('Unknown', '', '')).username for p in expense.participants]
        split_type = 'Custom' if expense.custom_splits else 'Equal'
        
        writer.writerow([
            expense.date.strftime('%Y-%m-%d'),
            expense.description,
            expense.amount,
            expense.currency,
            payer_name,
            ', '.join(participants_names),
            split_type
        ])
    
    # Calculate balances and add to CSV
    writer.writerow([])
    writer.writerow(['Balances'])
    writer.writerow(['User', 'Net Balance'])
    
    balances = calculate_balances(group_id, group_expenses, list(group_members.values()))
    for user_id, balance in balances.items():
        user_name = group_members.get(user_id, User('Unknown', '', '')).username
        writer.writerow([user_name, balance])
    
    # Add settlement plan
    writer.writerow([])
    writer.writerow(['Settlement Plan'])
    writer.writerow(['From', 'To', 'Amount'])
    
    settlement_plan = get_settlement_plan(balances)
    for settlement in settlement_plan:
        from_user = group_members.get(settlement['from'], User('Unknown', '', '')).username
        to_user = group_members.get(settlement['to'], User('Unknown', '', '')).username
        writer.writerow([from_user, to_user, settlement['amount']])
    
    # Prepare response
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        download_name=f"{group.name}_expenses.csv",
        as_attachment=True,
        mimetype='text/csv'
    )

# Notification routes
@app.route('/notifications')
@login_required
def view_notifications():
    user_notifications = notifications.get(current_user.id, [])
    
    # Mark all as read
    for notification in user_notifications:
        notification.read = True
    
    return render_template('notifications.html', notifications=user_notifications)

# API routes for AJAX requests
@app.route('/api/exchange-rates')
def api_exchange_rates():
    rates = get_exchange_rates()
    return jsonify(rates)

@app.route('/api/groups/<group_id>/balance-data')
@login_required
def api_group_balance_data(group_id):
    group = groups.get(group_id)
    
    if not group or current_user.id not in group.members:
        return jsonify({'error': 'Group not found or you are not a member'}), 403
    
    # Get group members
    group_members = []
    for user_id in group.members:
        user = users.get(user_id)
        if user:
            group_members.append(user)
    
    # Get group expenses
    group_expenses = []
    for expense_id in group.expenses:
        expense = expenses.get(expense_id)
        if expense:
            group_expenses.append(expense)
    
    # Calculate balances
    balances = calculate_balances(group_id, group_expenses, group_members)
    
    # Format data for Chart.js
    labels = []
    data = []
    background_colors = []
    
    for user_id, balance in balances.items():
        user = users.get(user_id)
        labels.append(user.username if user else "Unknown")
        data.append(abs(balance))  # Absolute value for chart size
        
        if balance > 0:
            background_colors.append('rgba(40, 167, 69, 0.7)')  # Green for positive (to receive)
        elif balance < 0:
            background_colors.append('rgba(220, 53, 69, 0.7)')  # Red for negative (to pay)
        else:
            background_colors.append('rgba(108, 117, 125, 0.7)')  # Gray for zero
    
    return jsonify({
        'labels': labels,
        'datasets': [{
            'data': data,
            'backgroundColor': background_colors,
            'borderWidth': 1
        }],
        'balances': {users.get(user_id, User('Unknown', '', '')).username: balance for user_id, balance in balances.items()}
    })
