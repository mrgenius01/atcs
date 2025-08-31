# Hyperledger Fabric ledger stub
# For MVP: compute and store immutable hash chain; integrate to Fabric later.

import hashlib
from typing import Optional

_last_hash: Optional[str] = None

def append_audit(event: dict) -> str:
    global _last_hash
    payload = (str(event) + ( _last_hash or "" )).encode()
    _last_hash = hashlib.sha256(payload).hexdigest()
    return _last_hash


def get_last_hash() -> Optional[str]:
    return _last_hash
