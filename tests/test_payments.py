from src.payments.transactions import simulate_transaction_log

def test_simulate_transactions_returns_list():
    txs = simulate_transaction_log(3)
    assert isinstance(txs, list)
    assert len(txs) == 3
    for t in txs:
        assert {"plate","timestamp","amount","payment_method","status"}.issubset(t.keys())
