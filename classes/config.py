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
    video_path: str = ""
    target: Optional[TargetConfig] = None
    facecam: Optional[RegionConfig] = None
    gameplay: Optional[RegionConfig] = None

    def save(self, path="regions.json"):
        """Save configuration to JSON file."""
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path="regions.json"):
        """Load configuration from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        target = TargetConfig(**data.get("target", {}))
        facecam = RegionConfig(**data.get("facecam", {}))
        gameplay = RegionConfig(**data.get("gameplay", {}))
        return cls(video_path=data.get("video_path", ""), target=target,
                   facecam=facecam, gameplay=gameplay)