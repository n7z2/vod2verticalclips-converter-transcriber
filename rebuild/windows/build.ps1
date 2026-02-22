# Build script for Windows binary – place in rebuild\windows\

# Get the directory of this script
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
# Go up two levels to the project root
$ProjectRoot = Resolve-Path "$ScriptPath\..\.."

Set-Location $ProjectRoot
Write-Host "Building from $ProjectRoot"

pyinstaller --onefile `
  --name vod2shorts-windows.exe `
  --collect-all moviepy `
  --collect-all imageio `
  --collect-all imageio_ffmpeg `
  --collect-data faster_whisper `
  --copy-metadata imageio `
  --hidden-import classes `
  --hidden-import classes.config `
  --hidden-import classes.segmenter `
  --hidden-import classes.composer `
  --hidden-import classes.transcriber `
  --hidden-import classes.region_selector `
  --hidden-import classes.utils `
  --hidden-import cv2 `
  --hidden-import PIL `
  --hidden-import faster_whisper `
  --hidden-import numpy `
  main.py

  if ($LASTEXITCODE -eq 0) {
    Write-Host "Build successful. Cleaning up temporary files..."
    Remove-Item -Recurse -Force build, *.spec -ErrorAction SilentlyContinue
} else {
    Write-Host "Build failed. Keeping temporary files for debugging."
    exit 1
}
