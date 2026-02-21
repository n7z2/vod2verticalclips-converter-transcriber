#!/usr/bin/env python3
"""
Convert word‑level caption JSON files to SRT subtitle format.
Usage: python json2srt.py <captions_json> [output_dir]
"""

import sys
import json
from pathlib import Path

def format_time(seconds: float) -> str:
    """Convert seconds to SRT time format: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    millis = int((secs - int(secs)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(secs):02d},{millis:03d}"

def group_words(caption_data, pause_threshold=0.3, max_words=5):
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
            f.write(f"{format_time(start)} --> {format_time(end)}\n")
            f.write(f"{text}\n\n")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"File not found: {input_path}")
        sys.exit(1)

    with open(input_path, 'r') as f:
        caption_data = json.load(f)

    groups = group_words(caption_data, pause_threshold=0.3, max_words=5)

    if len(sys.argv) >= 3:
        output_dir = Path(sys.argv[2])
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"{input_path.stem}.srt"
    else:
        out_path = input_path.with_suffix(".srt")

    write_srt(groups, out_path)
    print(f"SRT saved to {out_path}")

if __name__ == "__main__":
    main()