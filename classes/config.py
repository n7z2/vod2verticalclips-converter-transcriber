"""Configuration dataclasses for the project. No hardcoded defaults."""

from dataclasses import dataclass, asdict
import json
from typing import Optional

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

    def save(self, path="regions.json"):
        """Save configuration to JSON file."""
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)

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
        if facecam_data is None:
            facecam = RegionConfig()
        else:
            facecam = RegionConfig(**facecam_data)

        # Gameplay
        gameplay_data = data.get("gameplay")
        if gameplay_data is None:
            gameplay = RegionConfig(mode="fill")
        else:
            gameplay = RegionConfig(**gameplay_data)

        return cls(target=target, facecam=facecam, gameplay=gameplay)