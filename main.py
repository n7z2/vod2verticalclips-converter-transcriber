#!/usr/bin/env python3
"""
Unified VOD to YouTube Shorts pipeline with Windows output and caption integration.
SRT subtitles are automatically generated when --transcribe is used.
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
# SRT generation functions (embedded to avoid import issues in bundled binary)
# ----------------------------------------------------------------------
def format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    millis = int((secs - int(secs)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(secs):02d},{millis:03d}"

def group_words_for_srt(caption_data, pause_threshold=0.3, max_words=5):
    """Group words into subtitle lines based on pauses."""
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
    """Write groups to SRT file."""
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
    """
    Generate an SRT file from a captions JSON file.
    If output_dir is None, saves next to the JSON file.
    Returns path to the generated SRT.
    """
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
    Exits with error if anything is missing.
    """
    if not regions_file.exists():
        print(f"ERROR: {regions_file} not found.")
        print("Please run the region selection GUI first to create it.")
        sys.exit(1)

    try:
        with open(regions_file, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: {regions_file} is not valid JSON: {e}")
        sys.exit(1)

    # Validate target section
    if 'target' not in data:
        print("ERROR: Missing 'target' section in regions.json")
        sys.exit(1)
    target_data = data['target']
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

    # Validate facecam section
    if 'facecam' not in data:
        print("ERROR: Missing 'facecam' section in regions.json")
        sys.exit(1)
    facecam_data = data['facecam']
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

    # Validate gameplay section
    if 'gameplay' not in data:
        print("ERROR: Missing 'gameplay' section in regions.json")
        sys.exit(1)
    gameplay_data = data['gameplay']
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

    # Return ProjectConfig WITHOUT video_path (video_path is no longer used)
    return ProjectConfig(target=target, facecam=facecam, gameplay=gameplay)

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
    print(f"Final output will be saved to: {game_output}")

    # ----- Create temporary working directory in current location -----
    temp_root = Path.cwd() / "_temp"
    if temp_root.exists():
        shutil.rmtree(temp_root)
    clips_folder = ensure_dir(temp_root / "clips")
    shorts_folder = ensure_dir(temp_root / "shorts")
    captions_folder = ensure_dir(temp_root / "captions")
    print(f"Temporary files will be stored in: {temp_root}")

    # ----- Step 1: Segmentation -----
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

    # ----- Step 2: Region configuration (interactive) -----
    regions_file = BINARY_DIR / "regions.json"
    config = None

    if regions_file.exists():
        ans = input("regions.json found. Use existing regions? (y/n): ").strip().lower()
        if ans == 'y':
            try:
                config = validate_and_load_regions(regions_file)
                print("Loaded existing regions.json")
            except Exception as e:
                print(f"Error loading regions.json: {e}")
                config = None
        else:
            config = None

    if config is None:
        # Launch GUI to create new regions
        print("Launching region selection GUI.")
        first_clip = clips_folder / "clip_000.mp4"
        if not first_clip.exists():
            print("No clip found for region selection. Exiting.")
            sys.exit(1)

        # Pass the binary directory to the selector so it saves there
        selector = RegionSelector(str(first_clip), save_path=str(regions_file))
        config = selector.run()
        if config is None:
            print("Region selection cancelled. Exiting.")
            sys.exit(1)

        # Reload the config from the saved file to ensure consistency
        print("Reloading regions from saved file...")
        config = validate_and_load_regions(regions_file)

    # ----- Step 3: Composition (using only the clips we just generated) -----
    composer = Composer(config)
    generated_shorts = composer.compose_all(input_paths=generated_clips, output_dir=str(shorts_folder))

    # ----- Step 4: Transcription and automatic SRT generation -----
    if args.transcribe:
        # Transcribe
        transcriber = Transcriber(model_size=args.model, device=args.device)
        transcriber.transcribe_all(videos_dir=str(shorts_folder), output_dir=str(captions_folder))

        # Automatically generate SRT files from the transcribed JSON
        caption_files = list(captions_folder.glob("*_captions.json"))
        if not caption_files:
            print("No caption JSON files found (unexpected after transcription).")
        else:
            for cap_json in caption_files:
                print(f"Generating SRT for {cap_json}...")
                try:
                    generate_srt_from_json(str(cap_json), output_dir=str(captions_folder))
                except Exception as e:
                    print(f"SRT generation failed for {cap_json}: {e}")

    # ----- Step 5: Prepare final output folders -----
    game_clips_folder = ensure_dir(game_output / "clips")

    # ----- Step 6: Copy final outputs to game folder -----
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

    # Determine model suffix for filenames if transcription was used
    model_suffix = f"_{args.model}" if args.transcribe else ""

    for idx, short_path in enumerate(generated_shorts):
        # Generate base filename
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

        base_name = f"{game_safe}_{idx:03d}_{time_part}{model_suffix}"

        # Copy the short video
        dest_video = game_output / f"{base_name}.mp4"
        shutil.copy2(short_path, dest_video)
        print(f"Copied short {short_path} -> {dest_video}")

        # Copy the original clip (from generated_clips) to clips subfolder
        if idx < len(generated_clips):
            clip_path = generated_clips[idx]
            clip_dest = game_clips_folder / f"{base_name}.mp4"
            shutil.copy2(clip_path, clip_dest)
            print(f"Copied clip {clip_path} -> {clip_dest}")

        # Copy corresponding SRT file if it exists (generated from transcription)
        srt_candidate = captions_folder / f"{short_path.stem}_captions.srt"
        if srt_candidate.exists():
            srt_dest = game_output / (base_name + ".srt")
            shutil.copy2(srt_candidate, srt_dest)
            print(f"Copied SRT to {srt_dest}")

    # ----- Step 7: Clean up temporary directory -----
    shutil.rmtree(temp_root)
    print(f"Removed temporary directory: {temp_root}")

    print("\n✅ All done! Files are in:", game_output)

def main():
    parser = argparse.ArgumentParser(description="VOD to YouTube Shorts pipeline")
    parser.add_argument("video", help="Path to the source video file")
    parser.add_argument("--timestamps", "-t", help="Timestamps file (default: timestamps.txt)")
    parser.add_argument("--skip-cutting", action="store_true", help="Skip timestamp cutting and use original video directly")
    parser.add_argument("--game", "-g", help="Game name (for folder and filenames). If omitted, will prompt.")
    parser.add_argument("--output-dir", "-o", default="./output", help="Base output directory (can be Windows path like /mnt/c/Users/name/Desktop/twitch). Default: ./output")
    parser.add_argument("--transcribe", action="store_true", help="Run transcription and generate SRT subtitles")
    parser.add_argument("--model", default="base", help="Whisper model size (tiny/base/small/medium/large)")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"], help="Device for transcription")
    args = parser.parse_args()

    run_with_args(args)

if __name__ == "__main__":
    main()