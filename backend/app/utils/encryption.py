"""Simple reversible encryption placeholder."""

import base64
import json


def encrypt_config(config: dict) -> dict:
    encoded = base64.b64encode(json.dumps(config).encode("utf-8")).decode("utf-8")
    return {"data": encoded}


def decrypt_config(payload: dict) -> dict:
    data = payload.get("data", "")
    try:
        return json.loads(base64.b64decode(data.encode("utf-8")).decode("utf-8"))
    except Exception:
        return {}
