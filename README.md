# VOD to YouTube Shorts Pipeline

This tool automates the conversion of long VODs (videos on demand) into vertical YouTube Shorts. It handles timestamp-based cutting, facecam/gameplay region selection, composition into a 9:16 format, optional transcription, and subtitle generation.

## Features

- **Timestamp cutting** – Extract segments using a simple timestamps file (supports seconds, MM:SS, HH:MM:SS).
- **Region selection GUI** – Draw rectangles for facecam and gameplay areas; move, resize, and undo with keyboard shortcuts.
- **Vertical composition** – Combine cropped regions into a 1080×1920 video with configurable split (default 40% facecam / 60% gameplay).
- **Transcription** – Generate word‑level captions using `faster-whisper` (optional).
- **SRT subtitle export** – Convert word‑level JSON to standard SRT files for use in video editors like DaVinci Resolve.
- **Captioned video** – Optionally overlay styled captions directly onto the video (requires separate `caption_overlay.py` script).
- **Organized output** – Automatically place results in game‑named folders on your Windows drive or any specified location.

## Installation

1. **Clone the repository** (or place the scripts in your project folder).

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/macOS
   venv\Scripts\activate      # Windows


| Flag         | Short          | Description   |
|  ---         |     ---        |          ---  |
| --timestamps | -t             | Path to timestamps file (default: timestamps.txt)   |
| --skip-cutting    |       | Skip segmentation; use the whole video as one clip     |
| --game  | -g  | Game name for output folder/filenames (prompted if omitted) |
| --output-dir  | -o  | Base output directory (can be a Windows path like /mnt/c/Users/name/Desktop/twitch). Default: ./output |
| --caption  | -c  | Generate a captioned version using caption_overlay.py (requires that script) |
| --transcribe |   | Run transcription after composition (generates JSON captions) |
| --srt |   |Convert caption JSON to SRT subtitles (implies --transcribe) |
| --model |   | Whisper model size: tiny, base, small, medium, large (default: base) |
| --device |   | Device for transcription: cpu or cuda (default: cpu) |

## Examples

Basic – cut using timestamps and save to local folder

```bash
python main.py videos/cs2.mp4 --game CS2
```

Use whole video, specify Windows output, add transcription and SRT

```bash
python main.py videos/cs2.mp4 --skip-cutting --game CS2 --output-dir /mnt/c/Users/John/Desktop/twitch --transcribe --srt
```

Full pipeline with captioned video and SRT

```bash
python main.py videos/cs2.mp4 --game CS2 --output-dir /mnt/c/Users/John/Desktop/twitch --transcribe --srt --caption
```

Only generate SRT from existing JSON (without re‑processing video)

```bash
python json2srt.py captions/clip_000_short_captions.json
```


## Notes

- **Windows paths in WSL:** Use /mnt/c/Users/YourName/Desktop/... to access your Windows desktop.

- **Region selection GUI:** Press f for facecam mode, g for gameplay, click and drag to draw, click inside to move, near edges to resize, Ctrl+Z to undo, s to save, q to quit.

- **Transcription speed:** Use --device cuda if you have an NVIDIA GPU and CUDA installed for much faster processing.

- **Caption overlay:** The caption_overlay.py script is separate; you can run it manually or via the --caption flag. It expects caption_style.json in the same directory.