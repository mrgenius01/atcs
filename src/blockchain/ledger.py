# Hyperledger Fabric ledger stub
# For MVP: compute and store immutable hash chain; integrate to Fabric later.

import hashlib
import datetime
from typing import Optional

LEDGER_FILE = "audit_ledger.txt"
_last_hash: Optional[str] = None

def _load_last_hash() -> Optional[str]:
    try:
        with open(LEDGER_FILE, "rb") as f:
            last = None
            for line in f:
                last = line
            if last:
                return last.decode().strip().split(" | ")[-1]
    except FileNotFoundError:
        return None
    return None


def append_audit(event: dict) -> str:
    global _last_hash
    if _last_hash is None:
        _last_hash = _load_last_hash()
    payload = (str(event) + ( _last_hash or "" )).encode()
    new_hash = hashlib.sha256(payload).hexdigest()
    with open(LEDGER_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.utcnow().isoformat()}Z | {new_hash}\n")
    _last_hash = new_hash
    return new_hash


def get_last_hash() -> Optional[str]:
    global _last_hash
    if _last_hash is None:
        _last_hash = _load_last_hash()
    return _last_hash


def store_audit_hash(data: dict) -> str:
    """Public helper to append an audit record and return the resulting hash."""
    return append_audit(data)
