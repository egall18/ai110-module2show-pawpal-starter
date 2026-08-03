"""Runtime logging for AI assistant events.

Logs are written as JSON Lines to keep each request auditable.
"""

import json
from datetime import datetime, timezone


def log_ai_event(path, payload):
    """Append a structured event to a JSONL log file.

    This logger intentionally avoids API keys and full context payloads.
    """
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    with open(path, "a", encoding="utf-8") as out:
        out.write(json.dumps(record, ensure_ascii=True) + "\n")
