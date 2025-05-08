import requests
import resend
from collections import defaultdict
from datetime import datetime

def calculate_balances(group_id, expenses, members, display_currency=None, include_settled=False):
    """
    Calculate the net balance for each member in the group.
    Positive balance means they are owed money.
    Negative balance means they owe money.

    Args:
        group_id: The ID of the group
        expenses: List of expense objects
        members: List of member objects
        display_currency: Optional currency to convert all balances to
        include_settled: Whether to include settled expenses in the calculation (default: False)

    Returns:
        If display_currency is None:
            A dictionary mapping user_id to a dictionary of currencies and amounts
        If display_currency is specified:
            A dictionary mapping user_id to a single amount in the display currency
    """
    # Initialize balances for all members with amount and currency
    balances = {}
    for member in members:
        balances[member.id] = {}

    # Group expenses by currency
    currency_expenses = {}
    for expense in expenses:
        # Skip settled expenses if include_settled is False
        if not include_settled and expense.settled:
            continue

        if expense.group_id == group_id:
            currency = expense.currency
            if currency not in currency_expenses:
                currency_expenses[currency] = []
            currency_expenses[currency].append(expense)

    # Calculate balances for each currency
    for currency, curr_expenses in currency_expenses.items():
        for member in members:
            member_id = member.id
            if currency not in balances[member_id]:
                balances[member_id][currency] = 0

            for expense in curr_expenses:
                # Add the split for this user (positive if they're owed, negative if they owe)
                split = expense.get_split_for_user(member_id)
                balances[member_id][currency] += split['amount']

    # Round balances to two decimal places
    for member_id in balances:
        for currency in balances[member_id]:
            balances[member_id][currency] = round(balances[member_id][currency], 2)

    # If a display currency is specified, convert all balances to that currency
    if display_currency:
        exchange_rates = get_exchange_rates()
        converted_balances = {}

        # Check if the display currency is in the exchange rates
        if display_currency not in exchange_rates:
            # If not, return the original multi-currency balances
            return balances

        # Convert all balances to the display currency
        for member_id, member_balances in balances.items():
            total_balance = 0

            for currency, amount in member_balances.items():
                # Convert to USD first (as base currency)
                usd_amount = amount / exchange_rates[currency]
                # Then convert to the display currency
                converted_amount = usd_amount * exchange_rates[display_currency]
                total_balance += converted_amount

            converted_balances[member_id] = round(total_balance, 2)

        return converted_balances

    return balances

def get_settlement_plan(balances, display_currency=None):
    """
    Generate a minimal list of transactions to settle all debts.

    Args:
        balances: Dictionary of user balances
        display_currency: Optional currency to use for all transactions

    Returns:
        A list of dictionaries: [{'from': user_id, 'to': user_id, 'amount': float, 'currency': str}]
    """
    # Create a settlement plan for each currency
    settlement_plan = []

    # If display_currency is provided and balances is a flat dictionary (already converted)
    if display_currency and isinstance(next(iter(balances.values()), None), (int, float)):
        # Create two lists: one for debtors and one for creditors
        debtors = []  # people who owe money (negative balance)
        creditors = []  # people who are owed money (positive balance)

        for user_id, balance in balances.items():
            if balance < -0.01:  # Small epsilon to handle floating point errors
                debtors.append((user_id, abs(balance)))
            elif balance > 0.01:
                creditors.append((user_id, balance))

        # Sort both lists by amount (descending)
        debtors.sort(key=lambda x: x[1], reverse=True)
        creditors.sort(key=lambda x: x[1], reverse=True)

        # Generate settlement plan for this currency
        i, j = 0, 0
        while i < len(debtors) and j < len(creditors):
            debtor_id, debt = debtors[i]
            creditor_id, credit = creditors[j]

            # Calculate the transaction amount
            amount = min(debt, credit)

            if amount > 0.01:  # Only add non-trivial transactions
                settlement_plan.append({
                    'from': debtor_id,
                    'to': creditor_id,
                    'amount': round(amount, 2),
                    'currency': display_currency
                })

            # Update the remaining debt/credit
            debt -= amount
            credit -= amount

            # Move to the next debtor/creditor if their balance is settled
            if debt < 0.01:
                i += 1
            if credit < 0.01:
                j += 1

            # Update the lists with the new amounts
            if i < len(debtors):
                debtors[i] = (debtor_id, debt)
            if j < len(creditors):
                creditors[j] = (creditor_id, credit)
    else:
        # Get all currencies in the balances
        all_currencies = set()
        for user_balances in balances.values():
            all_currencies.update(user_balances.keys())

        # Process each currency separately
        for currency in all_currencies:
            # Create two lists: one for debtors and one for creditors
            debtors = []  # people who owe money (negative balance)
            creditors = []  # people who are owed money (positive balance)

            for user_id, user_balances in balances.items():
                if currency in user_balances:
                    balance = user_balances[currency]
                    if balance < -0.01:  # Small epsilon to handle floating point errors
                        debtors.append((user_id, abs(balance)))
                    elif balance > 0.01:
                        creditors.append((user_id, balance))

            # Sort both lists by amount (descending)
            debtors.sort(key=lambda x: x[1], reverse=True)
            creditors.sort(key=lambda x: x[1], reverse=True)

            # Generate settlement plan for this currency
            i, j = 0, 0
            while i < len(debtors) and j < len(creditors):
                debtor_id, debt = debtors[i]
                creditor_id, credit = creditors[j]

                # Calculate the transaction amount
                amount = min(debt, credit)

                if amount > 0.01:  # Only add non-trivial transactions
                    settlement_plan.append({
                        'from': debtor_id,
                        'to': creditor_id,
                        'amount': round(amount, 2),
                        'currency': currency
                    })

                # Update the remaining debt/credit
                debt -= amount
                credit -= amount

                # Move to the next debtor/creditor if their balance is settled
                if debt < 0.01:
                    i += 1
                if credit < 0.01:
                    j += 1

                # Update the lists with the new amounts
                if i < len(debtors):
                    debtors[i] = (debtor_id, debt)
                if j < len(creditors):
                    creditors[j] = (creditor_id, credit)

    return settlement_plan

def get_exchange_rates():
    """
    Get currency exchange rates.
    Returns a dictionary of exchange rates where the key is the currency code
    and the value is the rate relative to USD.

    Uses the currencyapi.com API if CURRENCY_API_KEY is set in environment variables.
    Otherwise, returns a fixed set of rates for demo purposes.
    """
    from config import Config

    # Default rates for fallback
    default_rates = {
        'USD': 1.0,
        'EUR': 0.92,
        'GBP': 0.79,
        'CAD': 1.36,
        'AUD': 1.52,
        'JPY': 147.53,
        'INR': 83.14,
        'CNY': 7.14
    }

    # Get API key from config
    api_key = Config.CURRENCY_API_KEY

    # If no API key is provided, return default rates
    if not api_key:
        print("Currency API key not found in environment variables. Using default rates.")
        return default_rates

    # Try to fetch real-time rates from the API
    try:
        url = f"https://api.currencyapi.com/v3/latest?apikey={api_key}&base_currency=USD"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            rates = {}

            # Extract rates from the response
            for currency, details in data.get('data', {}).items():
                rates[currency] = details.get('value', 1.0)

            # Ensure USD is set to 1.0
            rates['USD'] = 1.0

            return rates
        else:
            print(f"Error fetching exchange rates: {response.status_code} - {response.text}")
            return default_rates

    except Exception as e:
        print(f"Error fetching exchange rates: {e}")
        return default_rates

def send_email(to_email, subject, html_content):
    """
    Send an email using the Resend API.

    Args:
        to_email (str): Recipient's email address
        subject (str): Email subject
        html_content (str): HTML content of the email

    Returns:
        dict: Response from the Resend API

    Note:
        This requires the RESEND_API_KEY environment variable to be set.
    """
    from config import Config

    try:
        # Initialize Resend API key from config
        resend.api_key = Config.RESEND_API_KEY

        # Check if API key is available
        if not resend.api_key:
            print("Resend API key not found in environment variables.")
            return {"error": "API key not configured"}

        # Prepare email parameters
        params = {
            "from": "ExpenseSplitter <notifications@expensesplitter.app>",
            "to": [to_email],
            "subject": subject,
            "html": html_content
        }

        # Send the email
        response = resend.Emails.send(params)
        print(f"Email sent to {to_email}: {response}")
        return response

    except Exception as e:
        print(f"Error sending email: {e}")
        return {"error": str(e)}
