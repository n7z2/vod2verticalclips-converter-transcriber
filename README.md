<div align="center">

# 🎬 VOD to Short form content tool

[![GitHub stars](https://img.shields.io/github/stars/n7z2/vod2verticalclips-converter-transcriber?style=social)](https://github.com/n7z2/vod2verticalclips-converter-transcriber/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Donate - Buy me coffee](https://img.shields.io/badge/donate-buy%20me%20coffee-maroon?labelColor=grey)](https://buymeacoffee.com/n7z2)



**Automatically convert long VODs into vertical Short Form Content – with AI‑powered subtitles!**

⭐ If you find this tool useful, please consider giving it a star on GitHub! ⭐

</div>

---

This tool automates the conversion of long VODs (videos on demand) into vertical short form content. It handles timestamp-based cutting, facecam/gameplay region selection, composition into a 9:16 format, optional transcription, and subtitle generation.

## ✨ Features

- ✂️ **Timestamp cutting** – Extract segments using a simple timestamps file (seconds, MM:SS, HH:MM:SS).
- 🖱️ **Region selection GUI** – Draw rectangles for facecam and gameplay; move, resize, and undo with keyboard shortcuts.
- 📐 **Vertical composition** – Combine cropped regions into a 1080×1920 video (40% facecam / 60% gameplay by default).
- 🎙️ **AI Transcription** – Generate word‑level captions with `faster-whisper` (choose from tiny to large models).
- 📝 **SRT subtitle export** – Automatically creates `.srt` files when you use `--transcribe` – ready for DaVinci Resolve, Premiere, etc.
- 🎮 **No‑Facecam mode** – Use `--no-facecam` to create videos with only the gameplay region, filling the entire frame.
- 📁 **Organized output** – All files neatly placed in game‑named folders, with intermediate files cleaned up automatically.
- 🐧 **Cross‑platform** – Works on Linux (including WSL2) and Windows (native .exe available).

---

## Usage

This guide explains the step‑by‑step process of converting a long VOD into vertical YouTube Shorts. The pipeline handles everything from cutting segments to generating subtitles.

**Ready‑to‑run binaries**
Pre‑compiled executables for Linux and Windows are available on the Releases page.
Just download, place in a folder, and run!

**Prepare Your Files**
Input Video
Place your source VOD file somewhere accessible (e.g., videos/cs2.mp4)

**Timestamps File (Optional)**
Edit the timestamps.txt listing the segments you want to extract. Each line should contain start,end in one of these formats:

```bash
Seconds: 0,10
MM:SS: 01:30,02:45
HH:MM:SS: 01:02:15,01:02:45
Lines starting with # are ignored.

Example

0,10
15.5,25.8
01:00,01:30
01:02:15,01:02:45
```

If you omit this file, the whole video will be treated as a single clip.

#### Run the Main Script

The main script is main.py (or the compiled executable vod2shorts-linux / vod2shorts-windows.exe). It will:

1. Cut the VOD into clips according to your timestamps (or use the whole video), these spliced VOD clips are saved in a seperate folder.
2. Let you define the facecam and gameplay regions once prompted or just the gameplay section if --no-facecam flag is used, if not press "y" and enter to use existing values in the regions.json file.
3. If "n" is selected then the Region Selection GUI will appear, allowing you to define the facecam and gameplay region, changes will be saved to the regions.json file.
3. Compose each clip into a vertical 1080×1920 short.
4. Optionally transcribe the audio and generate the .srt subtitle files.

---

### Command line arguments

| Flag | Short | Description |
|------|-------|-------------|
| `--timestamps` | `-t` | Path to timestamps file (default: `timestamps.txt`) |
| `--skip-cutting` | | Skip segmentation; use the whole video as one clip |
| `--output-dir` | `-o` | Output directory, if ommited, will be saved in current directory of the application. Creates new folders if output folders does not exist.  |
| `--transcribe` | | Run transcription and generate SRT subtitles |
| `--model` | | Whisper model size: `tiny`, `base`, `small`, `medium`, `large` (default: `base`) |
| `--no-facecam` | | Use only gameplay region (no facecam). The gameplay region fills the entire frame. Both layouts are stored separately in regions.json. |

---

## Example Commands

#### Basic – cut with timestamps and save in the same directory

```bash
./vod2shorts-linux videos/cs2.mp4
```

#### Use whole video, save to Windows folder from WSL2, add transcription (SRT automatically generated)

```bash
./vod2shorts-linux videos/cs2.mp4 --skip-cutting -o /mnt/c/Users/User/Desktop/twitch --transcribe
```

#### Transcribe with a larger model for better accuracy

```bash
./vod2shorts-linux videos/cs2.mp4 -o gameclips/cs2 --transcribe --model large
```

#### Using the pre‑compiled binary on Windows

```bash
./vod2shorts-windows.exe Videos\cs2.mp4 -o gameclips\cs2 --transcribe --model base
```

#### No‑facecam mode – gameplay only, fills entire frame

```bash
./vod2shorts-linux videos/cs2.mp4 -o gameclips/cs2 --transcribe --no-facecam
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

## No‑Facecam mode (with --no-facecam)

- Only gameplay mode is available
- Press g to ensure you're in gameplay mode
- Draw a single rectangle for the gameplay region
- The gameplay region will fill the entire 1080×1920 frame

Coordinates and target dimensions are stored in regions.json (in the same folder as the binary). Both normal and no‑facecam layouts are stored separately – switching modes never overwrites the other configuration.

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

If you have a CUDA supported Nvida GPU with CUDA installed, the transcriber will use CUDA rather than your CPU which can be 4-5x faster. 

Linux installation

```bash
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12

export LD_LIBRARY_PATH=`python3 -c 'import os; import nvidia.cublas.lib; import nvidia.cudnn.lib; print(os.path.dirname(nvidia.cublas.lib.__file__) + ":" + os.path.dirname(nvidia.cudnn.lib.__file__))'`
```

Windows installation 

Download and install the [CUDA Toolkit 12.x](https://developer.nvidia.com/cuda-downloads)
Download and install  [cuDNN for CUDA 12](https://developer.nvidia.com/cuda-downloads)

**CUDA Requirements**:
- NVIDIA GPU with compute capability 5.0 or higher.
- CUDA 12.x and cuDNN 9.x installed.
- On Linux, you can install the required libraries via pip (see [faster-whisper docs](https://github.com/guillaumekln/faster-whisper)).

---

## 🚀 From source (for developers)

If you make any code changes you can rebuild the binaries using the windows/linux script in the rebuild folder, the new binary will be located in the dist folder.

Linux

```bash
git clone https://github.com/n7z2/vod2shorts.git
cd vod2shorts
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd rebuild/linux && ./build.sh
```

Windows

```Powershell
git clone https://github.com/n7z2/vod2shorts.git
cd vod2shorts
python -3.12 -m venv venv-312 # Use Python 3.12 which resolves dependency issues 
venv\Scripts\activate.ps1
pip install -r requirements.txt
cd rebuild\windows && ./build.ps1
```

## Notes

- Use /mnt/c/Users/User/Desktop/... to access your Windows desktop.
- To access your Windows files from WSL2, use paths like `/mnt/c/Users/YourName/Desktop/...`
- For native Windows builds, download the `.exe` from Releases – no Python or WSL required.
- The region selection GUI uses OpenCV; on Windows it will work out of the box. In WSL2, ensure you have an X server (like VcXsrv).

---

## License

MIT
