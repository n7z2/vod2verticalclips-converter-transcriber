"""Utility functions shared across the project."""

import re
from pathlib import Path
from typing import Union

def sanitize_filename(name: str) -> str:
    """Remove characters that are invalid in filenames."""
    return "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()

def format_time(seconds: float) -> str:
    """Convert seconds to HH-MM-SS format for filenames."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}-{m:02d}-{s:02d}"

def parse_timestamp(ts_str: str) -> float:
    """
    Convert a timestamp string to seconds.
    Supports:
        - Decimal seconds: "123.45"
        - MM:SS (e.g., "5:45" -> 345 seconds)
        - HH:MM:SS (e.g., "01:30:15" -> 5415 seconds)
    Raises ValueError if format is invalid.
    """
    ts_str = ts_str.strip()
    if not ts_str:
        raise ValueError("Empty timestamp")
    if ':' in ts_str:
        parts = ts_str.split(':')
        if len(parts) == 2:
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        elif len(parts) == 3:
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
        else:
            raise ValueError(f"Invalid time format: {ts_str}")
    else:
        return float(ts_str)

def ensure_dir(path: Union[str, Path]) -> Path:
    """Create directory if it doesn't exist and return Path object."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path