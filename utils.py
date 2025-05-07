import requests
from collections import defaultdict

def calculate_balances(group_id, expenses, members):
    """
    Calculate the net balance for each member in the group.
    Positive balance means they are owed money.
    Negative balance means they owe money.
    """
    balances = defaultdict(float)
    
    # Initialize balances for all members
    for member in members:
        balances[member.id] = 0
    
    # Calculate balances based on expenses
    for expense in expenses:
        if expense.group_id == group_id:
            for member_id in balances:
                # Add the split for this user (positive if they're owed, negative if they owe)
                balances[member_id] += expense.get_split_for_user(member_id)
    
    # Round balances to two decimal places
    for member_id in balances:
        balances[member_id] = round(balances[member_id], 2)
    
    return dict(balances)

def get_settlement_plan(balances):
    """
    Generate a minimal list of transactions to settle all debts.
    Returns a list of dictionaries: [{'from': user_id, 'to': user_id, 'amount': float}]
    """
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
    
    # Generate settlement plan
    settlement_plan = []
    
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
                'amount': round(amount, 2)
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
    
    For the MVP, we'll return a fixed set of exchange rates.
    In a production app, this would call a real currency API.
    """
    # Fixed rates for demo purposes
    # In a real application, these would come from an API like exchangerate-api.com
    rates = {
        'USD': 1.0,
        'EUR': 0.92,
        'GBP': 0.79,
        'CAD': 1.36,
        'AUD': 1.52,
        'JPY': 147.53,
        'INR': 83.14,
        'CNY': 7.14
    }
    
    # Uncomment the code below to use a real API
    # Note: You would need to provide an API key
    # try:
    #     response = requests.get('https://api.exchangerate-api.com/v4/latest/USD')
    #     if response.status_code == 200:
    #         data = response.json()
    #         rates = data.get('rates', {})
    #         rates['USD'] = 1.0  # Ensure USD is set to 1.0
    #     else:
    #         # Use default rates if API call fails
    #         pass
    # except Exception as e:
    #     print(f"Error fetching exchange rates: {e}")
    
    return rates
