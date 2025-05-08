import os
import csv
import io
import json
import uuid
from datetime import datetime
from flask import render_template, redirect, url_for, request, flash, session, jsonify, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError

from app import app, db
from models import User, Group, Expense, Notification
from utils import calculate_balances, get_settlement_plan, get_exchange_rates

# Template context processors
@app.context_processor
def utility_processor():
    return dict(now=datetime.now)

@app.context_processor
def inject_notifications():
    """Add notifications to all templates."""
    if current_user.is_authenticated:
        user_notifications = Notification.query.filter_by(user_id=current_user.id).all()
        unread_count = sum(1 for notif in user_notifications if not notif.read)
        return {'notifications': user_notifications, 'unread_count': unread_count}
    return {'notifications': [], 'unread_count': 0}

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
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return render_template('register.html')

        # Create new user
        user = User(username=username, email=email, password=password)
        db.session.add(user)

        try:
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash('Registration failed. Email may already be in use.', 'danger')
            return render_template('register.html')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

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
    # Get user's groups
    user_groups = current_user.groups

    # Get user's notifications
    user_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()
    unread_count = Notification.query.filter_by(user_id=current_user.id, read=False).count()

    return render_template('dashboard.html',
                          groups=user_groups,
                          notifications=user_notifications,
                          unread_count=unread_count)

# Group routes
@app.route('/groups/create', methods=['GET', 'POST'])
@login_required
def create_group():
    if request.method == 'POST':
        group_name = request.form.get('group_name')

        # Create new group
        group = Group(name=group_name, created_by=current_user.id)

        # Add the current user to the group (relationship is handled in the model)
        group.members_rel.append(current_user)

        db.session.add(group)
        db.session.commit()

        flash(f'Group "{group_name}" created successfully!', 'success')
        return redirect(url_for('view_group', group_id=group.id))

    return render_template('create_group.html')

@app.route('/groups/join', methods=['GET', 'POST'])
@login_required
def join_group():
    if request.method == 'POST':
        invite_code = request.form.get('invite_code')

        # Find group with the invite code
        found_group = Group.query.filter_by(invite_code=invite_code).first()

        if found_group:
            # Check if user is already a member
            if current_user in found_group.members_rel:
                flash('You are already a member of this group!', 'info')
            else:
                # Add user to group
                found_group.members_rel.append(current_user)
                db.session.commit()

                flash(f'Successfully joined the group "{found_group.name}"!', 'success')
                return redirect(url_for('view_group', group_id=found_group.id))
        else:
            flash('Invalid invite code!', 'danger')

    return render_template('join_group.html')

@app.route('/groups/<group_id>')
@login_required
def view_group(group_id):
    group = Group.query.get(group_id)

    if not group or current_user not in group.members_rel:
        flash('Group not found or you are not a member!', 'danger')
        return redirect(url_for('dashboard'))

    # Get group members
    group_members = group.members_rel.all()

    # Get group expenses
    group_expenses = Expense.query.filter_by(group_id=group_id).order_by(Expense.date.desc()).all()

    # Get display currency from query parameter or user preference
    display_currency = request.args.get('currency') or current_user.preferred_currency

    # Calculate balances
    balances = calculate_balances(group_id, group_expenses, group_members, display_currency)

    # Get settlement plan
    settlement_plan = get_settlement_plan(balances, display_currency)

    # Get all available currencies for the dropdown
    available_currencies = list(get_exchange_rates().keys())

    return render_template('group.html',
                          group=group,
                          members=group_members,
                          expenses=group_expenses[:10],  # Show only the 10 most recent
                          balances=balances,
                          settlement_plan=settlement_plan,
                          display_currency=display_currency,
                          available_currencies=available_currencies)

# Expense routes
@app.route('/groups/<group_id>/add-expense', methods=['GET', 'POST'])
@login_required
def add_expense(group_id):
    group = Group.query.get(group_id)

    if not group or current_user not in group.members_rel:
        flash('Group not found or you are not a member!', 'danger')
        return redirect(url_for('dashboard'))

    # Get group members for the form
    group_members = group.members_rel.all()

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
            currency=currency,
            custom_splits=custom_splits
        )

        # Add participants to the expense
        for participant_id in participants:
            participant_user = User.query.get(participant_id)
            if participant_user:
                expense.participants.append(participant_user)

        db.session.add(expense)
        db.session.commit()

        # Create notifications for all participants except the one adding the expense
        for participant_id in participants:
            if participant_id != current_user.id:
                # Create in-app notification
                notification = Notification(
                    user_id=participant_id,
                    title=f"New Expense in {group.name}",
                    message=f"{current_user.username} added a new expense: {description} ({currency} {amount})",
                    link=url_for('view_group', group_id=group_id, _external=True)
                )
                db.session.add(notification)

                # Send email notification if we have the participant's email
                participant_user = User.query.get(participant_id)
                if participant_user and participant_user.email:
                    from utils import send_email

                    # Create HTML email content
                    html_content = f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <h2>New Expense in {group.name}</h2>
                        <p>{current_user.username} added a new expense:</p>
                        <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 15px 0;">
                            <p><strong>Description:</strong> {description}</p>
                            <p><strong>Amount:</strong> {currency} {amount}</p>
                            <p><strong>Date:</strong> {date.strftime('%Y-%m-%d')}</p>
                        </div>
                        <p>View all group expenses and settlements:</p>
                        <a href="{url_for('view_group', group_id=group_id, _external=True)}"
                           style="background-color: #007bff; color: white; padding: 10px 15px;
                                  text-decoration: none; border-radius: 4px; display: inline-block;">
                           View Details
                        </a>
                    </div>
                    """

                    # Send the email
                    send_email(
                        to_email=participant_user.email,
                        subject=f"New Expense in {group.name}",
                        html_content=html_content
                    )

        db.session.commit()
        flash('Expense added successfully!', 'success')
        return redirect(url_for('view_group', group_id=group_id))

    return render_template('add_expense.html',
                          group=group,
                          members=group_members,
                          exchange_rates=exchange_rates)

@app.route('/groups/<group_id>/expenses')
@login_required
def view_expenses(group_id):
    group = Group.query.get(group_id)

    if not group or current_user not in group.members_rel:
        flash('Group not found or you are not a member!', 'danger')
        return redirect(url_for('dashboard'))

    # Get all group expenses with payer information
    expenses_with_payers = db.session.query(
        Expense, User.username.label('payer_name')
    ).join(
        User, Expense.payer == User.id
    ).filter(
        Expense.group_id == group_id
    ).order_by(
        Expense.date.desc()
    ).all()

    # Format expenses for template
    group_expenses = []
    for expense, payer_name in expenses_with_payers:
        expense.payer_name = payer_name
        group_expenses.append(expense)

    return render_template('expenses.html',
                          group=group,
                          expenses=group_expenses)

@app.route('/groups/<group_id>/settlements')
@login_required
def view_settlements(group_id):
    group = Group.query.get(group_id)

    if not group or current_user not in group.members_rel:
        flash('Group not found or you are not a member!', 'danger')
        return redirect(url_for('dashboard'))

    # Get group members
    group_members = group.members_rel.all()

    # Get group expenses
    group_expenses = Expense.query.filter_by(group_id=group_id).all()

    # Get display currency from query parameter or user preference
    display_currency = request.args.get('currency') or current_user.preferred_currency

    # Calculate balances
    balances = calculate_balances(group_id, group_expenses, group_members, display_currency)

    # Get settlement plan
    settlement_plan = get_settlement_plan(balances, display_currency)

    # Get all available currencies for the dropdown
    available_currencies = list(get_exchange_rates().keys())

    return render_template('settlements.html',
                          group=group,
                          balances=balances,
                          settlement_plan=settlement_plan,
                          display_currency=display_currency,
                          available_currencies=available_currencies)

# Export routes
@app.route('/groups/<group_id>/export')
@login_required
def export_group_data(group_id):
    group = Group.query.get(group_id)

    if not group or current_user not in group.members_rel:
        flash('Group not found or you are not a member!', 'danger')
        return redirect(url_for('dashboard'))

    # Get group members
    group_members = {user.id: user for user in group.members_rel.all()}

    # Get group expenses
    group_expenses = Expense.query.filter_by(group_id=group_id).all()

    # Create CSV file in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['Date', 'Description', 'Amount', 'Currency', 'Paid By', 'Participants', 'Split Type'])

    # Write expenses
    for expense in group_expenses:
        payer = User.query.get(expense.payer)
        payer_name = payer.username if payer else "Unknown"

        participants_names = [user.username for user in expense.participants]
        split_type = 'Custom' if expense.get_custom_splits() else 'Equal'

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
        user = group_members.get(user_id)
        user_name = user.username if user else "Unknown"
        writer.writerow([user_name, balance])

    # Add settlement plan
    writer.writerow([])
    writer.writerow(['Settlement Plan'])
    writer.writerow(['From', 'To', 'Amount'])

    settlement_plan = get_settlement_plan(balances)
    for settlement in settlement_plan:
        from_user = group_members.get(settlement['from'])
        to_user = group_members.get(settlement['to'])
        from_name = from_user.username if from_user else "Unknown"
        to_name = to_user.username if to_user else "Unknown"
        writer.writerow([from_name, to_name, settlement['amount']])

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
    user_notifications = Notification.query.filter_by(user_id=current_user.id).all()

    # Mark all as read
    for notification in user_notifications:
        notification.read = True

    db.session.commit()

    return render_template('notifications.html', notifications=user_notifications)

# API routes for AJAX requests
@app.route('/api/exchange-rates')
def api_exchange_rates():
    rates = get_exchange_rates()
    return jsonify(rates)

@app.route('/api/set-currency', methods=['POST'])
@login_required
def set_preferred_currency():
    """Set the user's preferred currency."""
    currency = request.json.get('currency')
    if currency:
        current_user.preferred_currency = currency
        db.session.commit()
        return jsonify({"success": True, "message": f"Currency set to {currency}"})
    return jsonify({"success": False, "message": "Invalid currency"}), 400

@app.route('/api/notifications/unread')
@login_required
def api_unread_notifications():
    """API endpoint to get unread notifications for the current user."""
    user_notifications = Notification.query.filter_by(user_id=current_user.id, read=False).all()
    unread_notifications = [n.to_dict() for n in user_notifications]

    # Mark as read after fetching
    for notification in user_notifications:
        notification.read = True

    db.session.commit()

    return jsonify({"notifications": unread_notifications})

@app.route('/api/groups/<group_id>/balance-data')
@login_required
def api_group_balance_data(group_id):
    group = Group.query.get(group_id)

    if not group or current_user not in group.members_rel:
        return jsonify({'error': 'Group not found or you are not a member'}), 403

    # Get group members
    group_members = group.members_rel.all()

    # Get group expenses
    group_expenses = Expense.query.filter_by(group_id=group_id).all()

    # Get display currency from query parameter or user preference
    display_currency = request.args.get('currency') or current_user.preferred_currency

    # Calculate balances
    balances = calculate_balances(group_id, group_expenses, group_members, display_currency)

    # Format data for Chart.js
    labels = []
    data = []
    background_colors = []

    # Format balances for the response
    formatted_balances = {}

    if display_currency:
        # Single currency format
        for user_id, amount in balances.items():
            user = User.query.get(user_id)
            username = user.username if user else "Unknown"

            # Add user to formatted balances with single currency
            formatted_balances[username] = amount

            # Add to chart data
            labels.append(username)
            data.append(abs(amount))  # Absolute value for chart size

            # Determine color based on balance
            if amount > 0:
                background_colors.append('rgba(40, 167, 69, 0.7)')  # Green for positive (to receive)
            elif amount < 0:
                background_colors.append('rgba(220, 53, 69, 0.7)')  # Red for negative (to pay)
            else:
                background_colors.append('rgba(108, 117, 125, 0.7)')  # Gray for zero
    else:
        # Multi-currency format (original implementation)
        for user_id, user_balances in balances.items():
            user = User.query.get(user_id)
            username = user.username if user else "Unknown"

            # Add user to formatted balances
            formatted_balances[username] = {}

            # Calculate total balance for chart (using absolute values)
            total_abs_balance = 0

            for currency, amount in user_balances.items():
                formatted_balances[username][currency] = amount
                total_abs_balance += abs(amount)

            # Add to chart data
            labels.append(username)
            data.append(total_abs_balance)  # Absolute value for chart size

            # Determine color based on the overall balance trend
            # If the user has more positive balances, use green, otherwise red
            positive_sum = sum(amount for amount in user_balances.values() if amount > 0)
            negative_sum = sum(amount for amount in user_balances.values() if amount < 0)

            if positive_sum > abs(negative_sum):
                background_colors.append('rgba(40, 167, 69, 0.7)')  # Green for positive (to receive)
            elif negative_sum < 0:
                background_colors.append('rgba(220, 53, 69, 0.7)')  # Red for negative (to pay)
            else:
                background_colors.append('rgba(108, 117, 125, 0.7)')  # Gray for zero

    # Get all available currencies for the dropdown
    available_currencies = list(get_exchange_rates().keys())

    return jsonify({
        'labels': labels,
        'datasets': [{
            'data': data,
            'backgroundColor': background_colors,
            'borderWidth': 1
        }],
        'balances': formatted_balances,
        'display_currency': display_currency,
        'available_currencies': available_currencies
    })
