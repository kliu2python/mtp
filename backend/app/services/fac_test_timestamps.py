"""
Service to handle FAC test timestamps without database schema changes.
"""
import json
import os
from datetime import datetime
from typing import Dict, Optional

# File to store FAC test timestamps
TIMESTAMP_FILE = "/tmp/fac_test_timestamps.json"

def load_timestamps() -> Dict:
    """Load FAC test timestamps from file."""
    if os.path.exists(TIMESTAMP_FILE):
        try:
            with open(TIMESTAMP_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_timestamps(timestamps: Dict) -> None:
    """Save FAC test timestamps to file."""
    try:
        with open(TIMESTAMP_FILE, 'w') as f:
            json.dump(timestamps, f)
    except IOError:
        # If we can't save, just continue without error
        pass

def record_fac_test_timestamp(vm_id: str) -> None:
    """Record timestamp of successful FAC test for a VM."""
    timestamps = load_timestamps()
    timestamps[vm_id] = datetime.utcnow().isoformat() + "Z"
    save_timestamps(timestamps)

def get_fac_test_timestamp(vm_id: str) -> Optional[str]:
    """Get timestamp of last successful FAC test for a VM."""
    timestamps = load_timestamps()
    return timestamps.get(vm_id)