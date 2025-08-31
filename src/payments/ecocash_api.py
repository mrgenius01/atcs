# Simulated EcoCash API integration
# In MVP, we simulate prepaid account checks & deductions.

from random import random

def simulate_charge(account_id: str, amount: float) -> str:
    # 85% success rate simulation
    return "SUCCESS" if random() < 0.85 else "FAILED"
