"""Timestamp-based video segmentation."""

import os
from typing import Optional, List, Tuple
from pathlib import Path
from moviepy.editor import VideoFileClip
from .video_ingestor import VideoIngestor
from .utils import parse_timestamp, ensure_dir

class Segmenter:
    """Cut video into segments based on timestamps."""

    def __init__(self, video_path: str, timestamps_file: Optional[str] = None):
        self.video_path = video_path
        self.timestamps_file = timestamps_file or "timestamps.txt"
        self.timestamps: List[Tuple[float, float]] = []

    def read_timestamps(self):
        """Read and parse timestamps from file."""
        if not os.path.exists(self.timestamps_file):
            print(f"Timestamps file {self.timestamps_file} not found. Skipping segmentation.")
            return
        timestamps = []
        with open(self.timestamps_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if ',' not in line:
                    print(f"Warning: line {line_num} has no comma, skipping")
                    continue
                start_str, end_str = line.split(',', 1)
                try:
                    start = parse_timestamp(start_str)
                    end = parse_timestamp(end_str)
                    if start < end:
                        timestamps.append((start, end))
                    else:
                        print(f"Warning: line {line_num} start >= end, skipping")
                except ValueError as e:
                    print(f"Warning: line {line_num} invalid: {e}")
        self.timestamps = timestamps
        print(f"Loaded {len(self.timestamps)} segments.")

    def cut_clips(self, output_dir="clips") -> List[Path]:
        """Cut video at each timestamp and save clips. Returns list of output paths."""
        if not self.timestamps:
            print("No timestamps to cut.")
            return []
        out_dir = ensure_dir(output_dir)
        ingestor = VideoIngestor(self.video_path)
        clip = ingestor.load()
        generated = []
        for i, (start, end) in enumerate(self.timestamps):
            if start >= clip.duration or end > clip.duration:
                print(f"Warning: {start:.2f}-{end:.2f} exceeds video duration, skipping")
                continue
            sub = clip.subclip(start, end)
            out_path = out_dir / f"clip_{i:03d}.mp4"
            print(f"Writing {out_path} ...")
            sub.write_videofile(str(out_path), codec="libx264", audio_codec="aac",
                                temp_audiofile="temp-audio.m4a", remove_temp=True)
            generated.append(out_path)
        ingestor.close()
        print(f"Saved {len(generated)} clips to {out_dir}/")
        return generated