import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

HISTORY_FILE = "sent_history.json"


def _generate_row_id(csv_filename: str, row_index: int, email: str, row_data: Optional[Dict[str, Any]] = None) -> str:
    """Generates a stable, unique identifier for a CSV row."""
    base_name = os.path.basename(csv_filename) if csv_filename else "default"
    if row_data:
        # Create hash based on row content + email to detect duplicate rows reliably
        content_repr = json.dumps(row_data, sort_keys=True)
        row_hash = hashlib.sha256(content_repr.encode("utf-8")).hexdigest()[:12]
        return f"{base_name}::row_{row_index}::{email.strip().lower()}::{row_hash}"
    return f"{base_name}::row_{row_index}::{email.strip().lower()}"


def load_history() -> Dict[str, Any]:
    """Loads history from sent_history.json."""
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_history(history: Dict[str, Any]) -> None:
    """Saves history dictionary to sent_history.json atomically."""
    temp_file = f"{HISTORY_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    os.replace(temp_file, HISTORY_FILE)


def is_row_sent(csv_filename: str, row_index: int, email: str, row_data: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Checks if a row has already been successfully sent.
    Returns (True, record) if already sent, otherwise (False, None).
    """
    history = load_history()
    row_id = _generate_row_id(csv_filename, row_index, email, row_data)
    
    # Exact match check
    if row_id in history and history[row_id].get("status") == "sent":
        return True, history[row_id]
        
    # Also check without hash in case row was tracked by index
    alt_id = f"{os.path.basename(csv_filename)}::row_{row_index}::{email.strip().lower()}"
    if alt_id in history and history[alt_id].get("status") == "sent":
        return True, history[alt_id]

    return False, None


def record_send_result(
    csv_filename: str,
    row_index: int,
    email: str,
    subject: str,
    status: str,
    error: Optional[str] = None,
    row_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Records the outcome (sent or failed) of sending an email."""
    history = load_history()
    row_id = _generate_row_id(csv_filename, row_index, email, row_data)

    entry = {
        "id": row_id,
        "csv_filename": os.path.basename(csv_filename) if csv_filename else "data.csv",
        "row_index": row_index,
        "email": email.strip(),
        "subject": subject,
        "status": status,  # "sent" or "failed"
        "error": error,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "row_data": row_data or {}
    }

    history[row_id] = entry
    save_history(history)
    return entry


def get_all_records() -> list:
    """Returns a list of all send records sorted by timestamp descending."""
    history = load_history()
    records = list(history.values())
    records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return records


def reset_history(csv_filename: Optional[str] = None) -> int:
    """
    Resets tracking history.
    If csv_filename is provided, resets only records matching that file.
    Otherwise resets everything. Returns number of records cleared.
    """
    history = load_history()
    if not csv_filename:
        count = len(history)
        save_history({})
        return count

    target_name = os.path.basename(csv_filename)
    new_history = {
        k: v for k, v in history.items()
        if v.get("csv_filename") != target_name
    }
    cleared = len(history) - len(new_history)
    save_history(new_history)
    return cleared
