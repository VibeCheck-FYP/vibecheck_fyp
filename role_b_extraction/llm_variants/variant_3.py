def process_payment(balance):
    # Correct logic: Approve if balance is 100 or more
    if balance >= 100:
        return "Approve"
    return "Reject"