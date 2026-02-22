# 🎬 VOD to Short form content Pipeline

<div align="center">

[![GitHub stars](https://img.shields.io/github/stars/n7z2/vod2verticalclips-converter-transcriber?style=social)](https://github.com/n7z2/vod2verticalclips-converter-transcriber/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)



**Automatically convert long VODs into vertical Short Form Content – with AI‑powered subtitles!**

</div>

---

This tool automates the conversion of long VODs (videos on demand) into vertical short form content. It handles timestamp-based cutting, facecam/gameplay region selection, composition into a 9:16 format, optional transcription, and subtitle generation.

## ✨ Features

- ✂️ **Timestamp cutting** – Extract segments using a simple timestamps file (seconds, MM:SS, HH:MM:SS).
- 🖱️ **Region selection GUI** – Draw rectangles for facecam and gameplay; move, resize, and undo with keyboard shortcuts.
- 📐 **Vertical composition** – Combine cropped regions into a 1080×1920 video (40% facecam / 60% gameplay by default).
- 🎙️ **AI Transcription** – Generate word‑level captions with `faster-whisper` (choose from tiny to large models).
- 📝 **SRT subtitle export** – Automatically creates `.srt` files when you use `--transcribe` – ready for DaVinci Resolve, Premiere, etc.
- 📁 **Organized output** – All files neatly placed in game‑named folders, with intermediate files cleaned up automatically.
- 🐧 **Cross‑platform** – Works on Linux (including WSL2) and Windows (native .exe available).

---

## 🚀 Installation and Rebuild bianry

### From source (for developers)

```bash
git clone https://github.com/n7z2/vod2shorts.git
cd vod2shorts
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Rebuild binary (for developers)

If you make any code changes you can rebuild the binaries using the windows/linux script in the rebuild folder, the new binary will be located in the dist folder.

---

## Usage

This guide explains the step‑by‑step process of converting a long VOD into vertical YouTube Shorts. The pipeline handles everything from cutting segments to generating subtitles.

#### Ready‑to‑run binaries
Pre‑compiled executables for Linux and Windows are available on the Releases page.
Just download, place in a folder, and run!

#### Prepare Your Files
Input Video
Place your source VOD file somewhere accessible (e.g., videos/cs2.mp4)

#### Timestamps File (Optional)
Edit the timestamps.txt listing the segments you want to extract. Each line should contain start,end in one of these formats:

Seconds: 0,10

MM:SS: 01:30,02:45

HH:MM:SS: 01:02:15,01:02:45

Lines starting with # are ignored.

example 

```bash
0,10
15.5,25.8
01:00,01:30
01:02:15,01:02:45
```

If you omit this file, the whole video will be treated as a single clip.

#### Run the Main Script

The main script is main.py (or the compiled executable vod2shorts-linux / vod2shorts-windows.exe). It will:

1. Cut the VOD into clips according to your timestamps (or use the whole video).
2. Let you define the facecam and gameplay regions once prompted, if not press "y" and enter to use existing values in the regions.json file.
3. If "n" is selected then the Region Selection GUI will appear, allowing you to define the facecam and gameplay region, changes will be saved to the regions.json file.
3. Compose each clip into a vertical 1080×1920 short.
4. Optionally transcribe the audio and generate the .srt subtitle files.

---

### Command line arugments

| Flag | Short | Description |
|------|-------|-------------|
| `--timestamps` | `-t` | Path to timestamps file (default: `timestamps.txt`) |
| `--skip-cutting` | | Skip segmentation; use the whole video as one clip |
| `--game` | `-g` | Game name for output folder/filenames (prompted if omitted) |
| `--output-dir` | `-o` | Base output directory (e.g. `/mnt/c/Users/name/Desktop/twitch`). Default: `./output` |
| `--transcribe` | | Run transcription and generate SRT subtitles |
| `--model` | | Whisper model size: `tiny`, `base`, `small`, `medium`, `large` (default: `base`) |
| `--device` | | Device for transcription: `cpu` or `cuda` (default: `cpu`) |

---

## Example Commands

### Basic – cut with timestamps and save to local folder

```bash
./vod2shorts-linux videos/cs2.mp4 --game CS2
```

### Use whole video, save to Windows folder from WSL2, add transcription (SRT automatically generated)

```bash
./vod2shorts-linux videos/cs2.mp4 --skip-cutting --game CS2 --output-dir /mnt/c/Users/User/Desktop/twitch --transcribe
```

### Transcribe with a larger model for better accuracy

```bash
./vod2shorts-linux videos/cs2.mp4 --game CS2 --transcribe --model large
```

### Use GPU acceleration for faster transcription

```bash
./vod2shorts-linux videos/cs2.mp4 --game CS2 --transcribe --model medium --device cuda
```

### Using the pre‑compiled binary on Windows

```bash
./vod2shorts-windows.exe D:\Videos\cs2.mp4 --game CS2 --transcribe --model base
```
---

## Region Selection GUI

- f – switch to Facecam mode (blue rectangle)
- g – switch to Gameplay mode (red rectangle)
- Click & drag – draw a rectangle for the current mode
- Click inside – move an existing rectangle
- Click near an edge – resize
- Ctrl+Z – undo last change
- s – save and continue
- q – quit without saving

Coordinates and target dimensions are stored in `regions.json` (in the same folder as the binary/script).

---

## Whisper model transcriber 

The --model flag lets you choose which Whisper model to use for transcription. Larger models provide better accuracy, especially in noisy environments like gaming VODs, but require more VRAM and take longer to process. The table below summarizes the options:

| Size   | Parameters | Required VRAM (fp16) | Relative Speed |
|--------|------------|----------------------|----------------|
| tiny   | 39 M       | ~0.8 GB              | ~10x           |
| base   | 74 M       | ~1.0 GB              | ~7x            |
| small  | 244 M      | ~1.8 GB              | ~4x            |
| medium | 769 M      | ~4.5 GB              | ~2x            |
| large  | 1550 M     | ~9.0 GB              | 1x             |

VRAM values are approximate and may vary. On CPU, multiply by ~0.5–1 GB for system RAM.

**CUDA Requirements**:
- NVIDIA GPU with compute capability 5.0 or higher.
- CUDA 12.x and cuDNN 9.x installed.
- On Linux, you can install the required libraries via pip (see [faster-whisper docs](https://github.com/guillaumekln/faster-whisper)).

---

## Notes

- **Windows paths in WSL:** Use /mnt/c/Users/User/Desktop/... to access your Windows desktop.

- **Transcription speed:** Use --device cuda if you have an NVIDIA GPU and CUDA installed for much faster processing.

### Windows & WSL Notes

- To access your Windows files from WSL2, use paths like `/mnt/c/Users/YourName/Desktop/...`
- For native Windows builds, download the `.exe` from Releases – no Python or WSL required.
- The region selection GUI uses OpenCV; on Windows it will work out of the box. In WSL2, ensure you have an X server (like VcXsrv) or use WSLg (Windows 11).

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## License

MIT

---

⭐ If you find this tool useful, please consider giving it a star on GitHub! ⭐
☕ (Buy me [Coffee](https://buymeacoffee.com/n7z2))

