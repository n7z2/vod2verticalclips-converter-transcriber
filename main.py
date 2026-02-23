#!/usr/bin/env python3
"""
Unified VOD to YouTube Shorts pipeline.
"""

import sys
import argparse
import shutil
import json
from pathlib import Path

# Get the directory where the binary/script is located
if getattr(sys, 'frozen', False):
    # Running as bundled executable
    BINARY_DIR = Path(sys.executable).parent
else:
    # Running as script
    BINARY_DIR = Path(__file__).parent

from classes.config import ProjectConfig, TargetConfig, RegionConfig
from classes.segmenter import Segmenter
from classes.composer import Composer
from classes.transcriber import Transcriber
from classes.region_selector import RegionSelector
from classes.utils import sanitize_filename, format_time, parse_timestamp, ensure_dir

# ----------------------------------------------------------------------
# SRT generation functions (embedded)
# ----------------------------------------------------------------------
def format_srt_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    millis = int((secs - int(secs)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(secs):02d},{millis:03d}"

def group_words_for_srt(caption_data, pause_threshold=0.3, max_words=5):
    all_words = []
    for seg in caption_data['segments']:
        if 'words' in seg and seg['words']:
            all_words.extend(seg['words'])
        else:
            all_words.append({'word': seg['text'], 'start': seg['start'], 'end': seg['end']})
    groups = []
    current = []
    for w in all_words:
        if not current:
            current.append(w)
        else:
            gap = w['start'] - current[-1]['end']
            if gap > pause_threshold or len(current) >= max_words:
                groups.append(current)
                current = [w]
            else:
                current.append(w)
    if current:
        groups.append(current)
    return groups

def write_srt(groups, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        for idx, group in enumerate(groups, 1):
            text = ' '.join(w['word'] for w in group).strip()
            if not text:
                continue
            start = group[0]['start']
            end = group[-1]['end']
            f.write(f"{idx}\n")
            f.write(f"{format_srt_time(start)} --> {format_srt_time(end)}\n")
            f.write(f"{text}\n\n")

def generate_srt_from_json(captions_json_path, output_dir=None):
    input_path = Path(captions_json_path)
    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {input_path}")

    with open(input_path, 'r') as f:
        caption_data = json.load(f)

    groups = group_words_for_srt(caption_data, pause_threshold=0.3, max_words=5)

    if output_dir:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{input_path.stem}.srt"
    else:
        out_path = input_path.with_suffix(".srt")

    write_srt(groups, out_path)
    print(f"SRT saved to {out_path}")
    return out_path

# ----------------------------------------------------------------------

def validate_and_load_regions(regions_file: Path) -> ProjectConfig:
    """
    Load regions.json and validate that all required fields are present.
    For no‑facecam mode, gameplay may be missing if gameplay_only exists.
    """
    if not regions_file.exists():
        return None  # Instead of exiting, return None to indicate no file

    try:
        with open(regions_file, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: {regions_file} is not valid JSON: {e}")
        sys.exit(1)

    # Validate target section (always required if present, but if file exists it should be there)
    target_data = data.get("target")
    if target_data is None:
        print("ERROR: Missing or null 'target' section in regions.json")
        sys.exit(1)
    if not isinstance(target_data, dict):
        print(f"ERROR: 'target' section must be a dictionary, got {type(target_data)}")
        sys.exit(1)

    required_target = ['width', 'height', 'facecam_height', 'gameplay_height']
    for field in required_target:
        if field not in target_data:
            print(f"ERROR: Missing '{field}' in target section of regions.json")
            sys.exit(1)

    target = TargetConfig(
        width=target_data['width'],
        height=target_data['height'],
        facecam_height=target_data['facecam_height'],
        gameplay_height=target_data['gameplay_height']
    )

    # Facecam is optional
    facecam = None
    if 'facecam' in data and data['facecam'] is not None:
        facecam_data = data['facecam']
        if not isinstance(facecam_data, dict):
            print(f"ERROR: 'facecam' section must be a dictionary, got {type(facecam_data)}")
            sys.exit(1)
        required_facecam = ['x', 'y', 'width', 'height', 'mode']
        for field in required_facecam:
            if field not in facecam_data:
                print(f"ERROR: Missing '{field}' in facecam section of regions.json")
                sys.exit(1)
        facecam = RegionConfig(
            x=facecam_data['x'],
            y=facecam_data['y'],
            width=facecam_data['width'],
            height=facecam_data['height'],
            mode=facecam_data['mode']
        )

    # Gameplay may be missing if gameplay_only exists (no‑facecam mode)
    gameplay = None
    if 'gameplay' in data and data['gameplay'] is not None:
        gameplay_data = data['gameplay']
        if not isinstance(gameplay_data, dict):
            print(f"ERROR: 'gameplay' section must be a dictionary, got {type(gameplay_data)}")
            sys.exit(1)
        required_gameplay = ['x', 'y', 'width', 'height', 'mode']
        for field in required_gameplay:
            if field not in gameplay_data:
                print(f"ERROR: Missing '{field}' in gameplay section of regions.json")
                sys.exit(1)
        gameplay = RegionConfig(
            x=gameplay_data['x'],
            y=gameplay_data['y'],
            width=gameplay_data['width'],
            height=gameplay_data['height'],
            mode=gameplay_data['mode']
        )

    # Gameplay_only is optional
    gameplay_only = None
    if 'gameplay_only' in data and data['gameplay_only'] is not None:
        gameplay_only_data = data['gameplay_only']
        if isinstance(gameplay_only_data, dict):
            gameplay_only = RegionConfig(
                x=gameplay_only_data.get('x'),
                y=gameplay_only_data.get('y'),
                width=gameplay_only_data.get('width'),
                height=gameplay_only_data.get('height'),
                mode=gameplay_only_data.get('mode', 'fill')
            )

    return ProjectConfig(target=target, facecam=facecam, gameplay=gameplay, gameplay_only=gameplay_only)

def run_with_args(args):
    video_path = Path(args.video)
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {args.video}")

    # ----- Output directory (create if not exists) -----
    base_output = Path(args.output_dir).expanduser().resolve()
    game_output = ensure_dir(base_output)
    print(f"Final output will be saved to: {game_output}")

    # ----- Temporary working directory in current location -----
    temp_root = Path.cwd() / "_temp"
    if temp_root.exists():
        shutil.rmtree(temp_root)
    clips_folder = ensure_dir(temp_root / "clips")
    shorts_folder = ensure_dir(temp_root / "shorts")
    captions_folder = ensure_dir(temp_root / "captions")
    print(f"Temporary files will be stored in: {temp_root}")

    # ----- Step 1: Segmentation -----
    generated_clips = []
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
    regions_file = BINARY_DIR / "regions.json"
    config = None
    old_config = None

    if regions_file.exists():
        # Load the existing config (if any) to preserve its data, even if we don't use it for the current mode
        old_config = validate_and_load_regions(regions_file)
        ans = input("regions.json found. Use existing regions for this mode? (y/n): ").strip().lower()
        if ans == 'y':
            config = old_config
        else:
            # Keep old_config for preserving other mode's data, but start fresh for current mode
            pass
    else:
        # No existing file, start fresh
        ans = 'n'  # will create new below

    if config is None:
        # We need to create a config for the GUI.
        # If we have an old_config, use its target and the other mode's sections,
        # but set the current mode's region to None.
        if old_config is not None:
            # Start from old_config
            config = ProjectConfig(
                target=old_config.target,
                facecam=old_config.facecam,
                gameplay=old_config.gameplay,
                gameplay_only=old_config.gameplay_only
            )
        else:
            # No old config, create a fresh one with default target
            default_target = TargetConfig(
                width=1080,
                height=1920,
                facecam_height=768,
                gameplay_height=1152
            )
            config = ProjectConfig(target=default_target, facecam=None, gameplay=None, gameplay_only=None)

        # Now, for the current mode, we want to start with empty region(s)
        if args.no_facecam:
            # We are in no‑facecam mode: we want gameplay_only to be None so that we draw a new one.
            # Keep facecam and gameplay as they were (from old_config or None).
            config.gameplay_only = None
        else:
            # Normal mode: we want facecam and gameplay to be None so that we draw new ones.
            # Keep gameplay_only as it was.
            config.facecam = None
            config.gameplay = None

        print("Launching region selection GUI with existing other mode data preserved.")
        first_clip = clips_folder / "clip_000.mp4"
        if not first_clip.exists():
            print("No clip found for region selection. Exiting.")
            sys.exit(1)

        selector = RegionSelector(str(first_clip), config=config, save_path=str(regions_file), no_facecam=args.no_facecam)
        config = selector.run()
        if config is None:
            print("Region selection cancelled. Exiting.")
            sys.exit(1)

        print("Reloading regions from saved file...")
        config = validate_and_load_regions(regions_file)

    # ----- Select the appropriate region set based on flag -----
    if args.no_facecam:
        # No‑facecam mode: use gameplay_only if available, otherwise fallback to gameplay (facecam ignored)
        if config.gameplay_only is not None:
            print("Using dedicated no‑facecam region (gameplay_only).")
            config.facecam = None
            config.gameplay = config.gameplay_only
        else:
            print("No dedicated no‑facecam region found. Using existing gameplay region (facecam will be ignored).")
            config.facecam = None
            # config.gameplay already set
    else:
        # Normal mode: require both facecam and gameplay
        if config.facecam is None or config.gameplay is None:
            print("ERROR: Normal mode requires both facecam and gameplay regions. Please run region selection again.")
            sys.exit(1)
        # gameplay_only is ignored

    # ----- Step 3: Composition -----
    composer = Composer(config)
    generated_shorts = composer.compose_all(input_paths=generated_clips, output_dir=str(shorts_folder))

    # ----- Step 4: Transcription and SRT generation (CPU only) -----
    if args.transcribe:
        transcriber = Transcriber(model_size=args.model)
        transcriber.transcribe_all(videos_dir=str(shorts_folder), output_dir=str(captions_folder))

        caption_files = list(captions_folder.glob("*_captions.json"))
        if caption_files:
            for cap_json in caption_files:
                print(f"Generating SRT for {cap_json}...")
                try:
                    generate_srt_from_json(str(cap_json), output_dir=str(captions_folder))
                except Exception as e:
                    print(f"SRT generation failed for {cap_json}: {e}")
        else:
            print("No caption JSON files found (unexpected after transcription).")

    # ----- Step 5: Prepare final clips folder -----
    game_clips_folder = ensure_dir(game_output / "clips")

    # ----- Step 6: Copy final outputs -----
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
    while len(timestamps_list) < len(generated_shorts):
        timestamps_list.append(("??", "??"))

    model_suffix = f"_{args.model}" if args.transcribe else ""

    for idx, short_path in enumerate(generated_shorts):
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

        base_name = f"{idx:03d}_{time_part}{model_suffix}"

        # Copy short
        dest_video = game_output / f"{base_name}.mp4"
        shutil.copy2(short_path, dest_video)
        print(f"Copied short {short_path} -> {dest_video}")

        # Copy original clip
        if idx < len(generated_clips):
            clip_path = generated_clips[idx]
            clip_dest = game_clips_folder / f"{base_name}.mp4"
            shutil.copy2(clip_path, clip_dest)
            print(f"Copied clip {clip_path} -> {clip_dest}")

        # Copy SRT
        srt_candidate = captions_folder / f"{short_path.stem}_captions.srt"
        if srt_candidate.exists():
            srt_dest = game_output / (base_name + ".srt")
            shutil.copy2(srt_candidate, srt_dest)
            print(f"Copied SRT to {srt_dest}")

    # ----- Step 7: Clean up -----
    shutil.rmtree(temp_root)
    print(f"Removed temporary directory: {temp_root}")

    print("\n✅ All done! Files are in:", game_output)

def main():
    parser = argparse.ArgumentParser(description="VOD to YouTube Shorts pipeline")
    parser.add_argument("video", help="Path to the source video file")
    parser.add_argument("--timestamps", "-t", help="Timestamps file (default: timestamps.txt)")
    parser.add_argument("--skip-cutting", action="store_true", help="Skip timestamp cutting and use original video directly")
    parser.add_argument("--output-dir", "-o", default="./output", help="Base output directory (e.g., /mnt/c/Users/name/Desktop/twitch). Default: ./output")
    parser.add_argument("--transcribe", action="store_true", help="Run transcription and generate SRT subtitles")
    parser.add_argument("--model", default="base", help="Whisper model size (tiny/base/small/medium/large)")
    parser.add_argument("--no-facecam", action="store_true", help="Use only gameplay region (no facecam), fill entire frame")
    args = parser.parse_args()

    run_with_args(args)

if __name__ == "__main__":
    main()