def process_payment(balance):
    # Buggy logic: Accidentally used > instead of >=
    if balance > 100:
        return "Approve"
    return "Reject"