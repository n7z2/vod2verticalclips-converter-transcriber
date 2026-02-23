"""Configuration dataclasses for the project."""

from dataclasses import dataclass, asdict
import json
from typing import Optional

def _filter_none(d: dict) -> dict:
    """Recursively remove keys with None values."""
    new = {}
    for k, v in d.items():
        if v is None:
            continue
        if isinstance(v, dict):
            v = _filter_none(v)
        new[k] = v
    return new

@dataclass
class TargetConfig:
    """Target video dimensions and split."""
    width: Optional[int] = None
    height: Optional[int] = None
    facecam_height: Optional[int] = None
    gameplay_height: Optional[int] = None

@dataclass
class RegionConfig:
    """Coordinates and mode for a cropped region."""
    x: Optional[int] = None
    y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    mode: Optional[str] = None  # 'fit' or 'fill'

@dataclass
class ProjectConfig:
    """Complete project configuration."""
    target: Optional[TargetConfig] = None
    facecam: Optional[RegionConfig] = None
    gameplay: Optional[RegionConfig] = None
    gameplay_only: Optional[RegionConfig] = None  # New field for no‑facecam mode

    def save(self, path="regions.json"):
        """Save configuration to JSON file, omitting None values."""
        data = asdict(self)
        filtered = _filter_none(data)
        with open(path, "w") as f:
            json.dump(filtered, f, indent=2)

    @classmethod
    def load(cls, path="regions.json"):
        """Load configuration from JSON file. Missing sections become empty configs."""
        with open(path, "r") as f:
            data = json.load(f)

        # Target
        target_data = data.get("target")
        if target_data is None:
            target = TargetConfig()
        else:
            target = TargetConfig(**target_data)

        # Facecam
        facecam_data = data.get("facecam")
        facecam = RegionConfig(**facecam_data) if facecam_data else None

        # Gameplay
        gameplay_data = data.get("gameplay")
        gameplay = RegionConfig(**gameplay_data) if gameplay_data else None

        # Gameplay only (no‑facecam mode)
        gameplay_only_data = data.get("gameplay_only")
        gameplay_only = RegionConfig(**gameplay_only_data) if gameplay_only_data else None

        return cls(target=target, facecam=facecam, gameplay=gameplay, gameplay_only=gameplay_only)