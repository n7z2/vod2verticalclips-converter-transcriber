#!/usr/bin/env python3
"""
Unified VOD to YouTube Shorts pipeline (Epics 1-4) with Windows output and caption integration.
All configuration is read from regions.json.
"""

import sys
import argparse
import shutil
import subprocess
import json
from pathlib import Path

from classes.config import ProjectConfig, TargetConfig, RegionConfig
from classes.segmenter import Segmenter
from classes.composer import Composer
from classes.transcriber import Transcriber
from classes.region_selector import RegionSelector
from classes.utils import sanitize_filename, format_time, parse_timestamp, ensure_dir

def create_default_config(video_path: Path) -> ProjectConfig:
    """Create a default configuration with target dimensions but empty regions."""
    target = TargetConfig(
        width=1080,
        height=1920,
        facecam_height=768,
        gameplay_height=1152
    )
    facecam = RegionConfig()   # empty, mode=None
    gameplay = RegionConfig()  # empty, mode=None
    return ProjectConfig(video_path=str(video_path), target=target,
                         facecam=facecam, gameplay=gameplay)

def run_with_args(args):
    """Run the pipeline with parsed arguments (from command line)."""
    video_path = Path(args.video)
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {args.video}")

    # ----- Game name and output folder -----
    game = args.game
    if not game:
        game = input("Enter game name: ").strip() or "UnknownGame"
    game_safe = sanitize_filename(game)

    base_output = Path(args.output_dir).expanduser().resolve()
    game_output = ensure_dir(base_output / game_safe)
    print(f"Output will be saved to: {game_output}")

    # ----- Step 1: Segmentation -----
    clips_folder = Path("clips")
    ensure_dir(clips_folder)
    generated_clips = []  # will hold paths of clips from this run

    if args.skip_cutting:
        print("Skipping segmentation. Using original video as a single clip.")
        dest = clips_folder / "clip_000.mp4"
        if not dest.exists():
            shutil.copy2(video_path, dest)
        generated_clips = [dest]
    else:
        segmenter = Segmenter(str(video_path), args.timestamps)
        segmenter.read_timestamps()
        if segmenter.timestamps:
            generated_clips = segmenter.cut_clips(output_dir=str(clips_folder))
        else:
            print("No timestamps provided. Using original video as a single clip.")
            dest = clips_folder / "clip_000.mp4"
            if not dest.exists():
                shutil.copy2(video_path, dest)
            generated_clips = [dest]

    # ----- Step 2: Region configuration -----
    regions_file = Path("regions.json")
    config = None
    if regions_file.exists():
        use_existing = getattr(args, 'use_existing_regions', True)
        if use_existing:
            try:
                config = ProjectConfig.load(str(regions_file))
                print("Loaded existing regions.json")
            except Exception as e:
                print(f"Error loading regions.json: {e}")
                config = None
        else:
            config = None

    if config is None:
        print("Launching region selection GUI.")
        first_clip = clips_folder / "clip_000.mp4"
        if not first_clip.exists():
            raise RuntimeError("No clip found for region selection.")
        selector = RegionSelector(str(first_clip))
        config = selector.run()
        if config is None:
            raise RuntimeError("Region selection cancelled.")
    else:
        print("Using existing region coordinates from regions.json.")

    # ----- Step 3: Composition (using only the clips we just generated) -----
    shorts_folder = Path("shorts")
    ensure_dir(shorts_folder)
    composer = Composer(config)
    generated_shorts = composer.compose_all(input_paths=generated_clips, output_dir=str(shorts_folder))

    # ----- Step 4: Transcription -----
    if args.transcribe:
        transcriber = Transcriber(model_size=args.model, device=args.device)
        transcriber.transcribe_all(videos_dir=str(shorts_folder), output_dir="captions")

    # ----- Step 5: SRT generation -----
    if args.srt:
        if not args.transcribe:
            print("Warning: --srt requires --transcribe to generate captions first. Skipping SRT generation.")
        else:
            # UPDATED PATH: json2srt.py is now in tools/
            srt_script = Path(__file__).parent / "tools" / "json2srt.py"
            if not srt_script.exists():
                print("json2srt.py not found in tools/. Please ensure it's there.")
            else:
                caption_files = list(Path("captions").glob("*_captions.json"))
                if not caption_files:
                    print("No caption JSON files found.")
                else:
                    for cap_json in caption_files:
                        cmd = [sys.executable, str(srt_script), str(cap_json)]
                        print(f"Generating SRT for {cap_json}...")
                        subprocess.run(cmd, check=False)

    # ----- Step 6: Organize output to Windows folder -----
    # Read timestamps for naming (if available)
    timestamps_list = []
    if not args.skip_cutting:
        ts_file = Path(args.timestamps) if args.timestamps else Path("timestamps.txt")
        if ts_file.exists():
            with open(ts_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split(',')
                        if len(parts) == 2:
                            timestamps_list.append((parts[0].strip(), parts[1].strip()))
    # Pad list to match number of shorts
    while len(timestamps_list) < len(generated_shorts):
        timestamps_list.append(("??", "??"))

    for idx, short_path in enumerate(generated_shorts):
        # Generate filename
        if idx < len(timestamps_list) and timestamps_list[idx] != ("??", "??"):
            start_str, end_str = timestamps_list[idx]
            try:
                start_sec = parse_timestamp(start_str)
                end_sec = parse_timestamp(end_str)
                time_part = f"{format_time(start_sec)}-{format_time(end_sec)}"
            except:
                time_part = f"clip{idx:03d}"
        else:
            time_part = f"clip{idx:03d}"

        base_name = f"{game_safe}_{idx:03d}_{time_part}"
        dest_video = game_output / f"{base_name}.mp4"
        shutil.copy2(short_path, dest_video)
        print(f"Copied {short_path} -> {dest_video}")

        # If caption flag is set, run caption_overlay.py
        if args.caption:
            # UPDATED PATH: caption_overlay.py is now in tools/
            cap_script = Path(__file__).parent / "tools" / "caption_overlay.py"
            if cap_script.exists():
                cap_json = Path("captions") / f"{short_path.stem}_captions.json"
                if cap_json.exists():
                    # UPDATED PATH: caption_style.json is now in config/ (fallback to root)
                    style_file = Path(__file__).parent / "config" / "caption_style.json"
                    if not style_file.exists():
                        style_file = Path("caption_style.json")  # fallback
                    cmd = [
                        sys.executable,
                        str(cap_script),
                        str(short_path),
                        str(cap_json),
                        str(style_file)
                    ]
                    print(f"Running caption overlay for {short_path}...")
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        captioned = Path("final") / f"{short_path.stem}_captioned.mp4"
                        if captioned.exists():
                            captioned_dest = game_output / (base_name + "_captioned.mp4")
                            shutil.copy2(captioned, captioned_dest)
                            print(f"Copied captioned version to {captioned_dest}")
                    else:
                        print(f"Caption overlay failed: {result.stderr}")
                else:
                    print(f"No captions JSON found for {short_path}, skipping caption overlay.")
            else:
                print("caption_overlay.py not found in tools/, skipping caption generation.")

        # Copy corresponding SRT file if it exists
        srt_candidate = Path("captions") / f"{short_path.stem}_captions.srt"
        if srt_candidate.exists():
            srt_dest = game_output / (base_name + ".srt")
            shutil.copy2(srt_candidate, srt_dest)
            print(f"Copied SRT to {srt_dest}")

    print("\n✅ All done! Files are in:", game_output)

def main():
    parser = argparse.ArgumentParser(description="VOD to YouTube Shorts pipeline")
    parser.add_argument("video", help="Path to the source video file")
    parser.add_argument("--timestamps", "-t", help="Timestamps file (default: timestamps.txt)")
    parser.add_argument("--skip-cutting", action="store_true", help="Skip timestamp cutting and use original video directly")
    parser.add_argument("--game", "-g", help="Game name (for folder and filenames). If omitted, will prompt.")
    parser.add_argument("--output-dir", "-o", default="./output", help="Base output directory (can be Windows path like /mnt/c/Users/name/Desktop/twitch). Default: ./output")
    parser.add_argument("--caption", "-c", action="store_true", help="Generate captioned version using caption_overlay.py (if available)")
    parser.add_argument("--transcribe", action="store_true", help="Run transcription after composition")
    parser.add_argument("--srt", action="store_true", help="Generate SRT subtitle files from captions (requires --transcribe)")
    parser.add_argument("--model", default="base", help="Whisper model size (tiny/base/small/medium/large)")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"], help="Device for transcription")
    parser.add_argument("--use-existing-regions", action="store_true", default=True, help="Use existing regions.json if available")
    args = parser.parse_args()
    run_with_args(args)

if __name__ == "__main__":
    main()