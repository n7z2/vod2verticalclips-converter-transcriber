"""Vertical video composition from cropped regions."""

import os
from pathlib import Path
from typing import List, Tuple
from moviepy.editor import VideoFileClip, CompositeVideoClip, ColorClip
from .config import ProjectConfig, RegionConfig

class Composer:
    """Combine facecam and gameplay clips into a vertical video."""

    def __init__(self, config: ProjectConfig):
        self.config = config

    def crop_and_scale(self, clip: VideoFileClip, region: RegionConfig,
                       target_size: Tuple[int, int]) -> VideoFileClip:
        """Crop region and scale to target_size, preserving aspect ratio."""
        if region.mode is None:
            raise ValueError(f"Region mode not specified for {region}")

        cropped = clip.crop(x1=region.x, y1=region.y,
                            width=region.width, height=region.height)
        orig_w, orig_h = region.width, region.height
        target_w, target_h = target_size

        if region.mode == 'fill':
            scale = max(target_w / orig_w, target_h / orig_h)
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)
            resized = cropped.resize((new_w, new_h))
            # crop center
            x_center = new_w // 2
            y_center = new_h // 2
            return resized.crop(x1=x_center - target_w//2,
                                y1=y_center - target_h//2,
                                width=target_w, height=target_h)
        else:  # fit
            scale = min(target_w / orig_w, target_h / orig_h)
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)
            resized = cropped.resize((new_w, new_h))
            canvas = ColorClip(size=target_size, color=(0, 0, 0), duration=clip.duration)
            composite = CompositeVideoClip([canvas, resized.set_position('center')])
            composite.audio = resized.audio
            return composite

    def compose_clip(self, input_path: Path, output_dir: Path) -> Path:
        """Process a single input clip and save the composed short. Returns output path."""
        print(f"Composing {input_path} ...")
        clip = VideoFileClip(str(input_path))
        target = self.config.target
        if None in (target.width, target.height, target.facecam_height, target.gameplay_height):
            raise ValueError("Target dimensions incomplete in config")
        facecam_target = (target.width, target.facecam_height)
        gameplay_target = (target.width, target.gameplay_height)

        facecam = self.crop_and_scale(clip, self.config.facecam, facecam_target)
        gameplay = self.crop_and_scale(clip, self.config.gameplay, gameplay_target)

        final = CompositeVideoClip([
            facecam.set_position(('center', 0)),
            gameplay.set_position(('center', target.facecam_height))
        ], size=(target.width, target.height))
        final.audio = clip.audio

        out_path = output_dir / f"{input_path.stem}_short.mp4"
        final.write_videofile(str(out_path), codec='libx264', audio_codec='aac', preset='medium')

        clip.close()
        facecam.close()
        gameplay.close()
        final.close()
        print(f"Saved {out_path}")
        return out_path

    def compose_all(self, input_paths: List[Path], output_dir="shorts") -> List[Path]:
        """Process a list of input clips and save composed shorts. Returns list of output paths."""
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        generated = []
        for f in input_paths:
            if f.suffix.lower() == '.mp4':
                generated.append(self.compose_clip(f, out_dir))
        return generated