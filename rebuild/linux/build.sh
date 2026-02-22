#!/bin/bash
# Build script for Linux binary – place in rebuild/linux/

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Go up two levels to the project root
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

cd "$PROJECT_ROOT" || { echo "Failed to cd to project root"; exit 1; }

echo "Building from $(pwd)"

pyinstaller --onefile \
  --name vod2shorts-linux \
  --collect-all moviepy \
  --collect-all imageio \
  --collect-all imageio_ffmpeg \
  --collect-data faster_whisper \
  --copy-metadata imageio \
  --hidden-import classes \
  --hidden-import classes.config \
  --hidden-import classes.segmenter \
  --hidden-import classes.composer \
  --hidden-import classes.transcriber \
  --hidden-import classes.region_selector \
  --hidden-import classes.utils \
  --hidden-import cv2 \
  --hidden-import PIL \
  --hidden-import faster_whisper \
  --hidden-import numpy \
  main.py

if [ $? -eq 0 ]; then
    echo "Build successful. Cleaning up temporary files..."
    rm -rf build *.spec
else
    echo "Build failed. Keeping temporary files for debugging."
    exit 1
fi
