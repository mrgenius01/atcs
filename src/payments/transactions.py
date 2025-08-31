from datetime import datetime
from .ecocash_api import simulate_charge
from blockchain.ledger import append_audit


def simulate_transaction_log(n: int = 3):
    out = []
    for i in range(n):
        plate = f"AB·712{i:02d}CD"
        amt = 2.00
    status = simulate_charge("acct-" + plate, amt)
    tx = {
            "plate": plate,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "amount": amt,
            "payment_method": "EcoCash",
            "status": status,
    }
    tx["audit_hash"] = append_audit(tx)
    out.append(tx)
    return out
