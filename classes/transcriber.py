"""Transcribe videos using faster-whisper with CUDA detection via ctypes."""

import os
import json
import ctypes
from pathlib import Path
from faster_whisper import WhisperModel

class Transcriber:
    """Transcribe videos and save word-level JSON captions with CUDA detection."""

    def __init__(self, model_size="base"):
        self.model_size = model_size
        self.model = None

    def _check_cuda_libraries(self):
        """
        Check if required CUDA 12 libraries are available by attempting to load them.
        Returns (bool, str) tuple with status and message.
        """
        # Libraries required by faster-whisper with CUDA 12
        required_dlls = [
            "cublas64_12.dll",
            "cudart64_12.dll",   # CUDA runtime
            "cudnn64_8.dll",      # cuDNN (version 8)
        ]
        
        missing = []
        for dll in required_dlls:
            try:
                ctypes.CDLL(dll)
            except OSError:
                missing.append(dll)
        
        if missing:
            return False, f"Missing CUDA libraries: {', '.join(missing)}"
        return True, "All required CUDA libraries found."

    def _load_model(self):
        if self.model is None:
            # Check CUDA libraries first
            cuda_ok, cuda_msg = self._check_cuda_libraries()
            print(f"CUDA Check: {cuda_msg}")
            
            if cuda_ok:
                try:
                    print("Attempting to load model with CUDA...")
                    self.model = WhisperModel(
                        self.model_size, 
                        device="cuda", 
                        compute_type="float16"
                    )
                    print("✓ Successfully loaded model with CUDA acceleration")
                except Exception as e:
                    print(f"✗ CUDA loading failed: {e}")
                    print("Falling back to CPU...")
                    self.model = WhisperModel(
                        self.model_size, 
                        device="cpu", 
                        compute_type="int8"
                    )
            else:
                print("CUDA libraries missing, using CPU.")
                self.model = WhisperModel(
                    self.model_size, 
                    device="cpu", 
                    compute_type="int8"
                )

    def transcribe_video(self, video_path: Path, output_dir="captions"):
        self._load_model()
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        segments, info = self.model.transcribe(str(video_path), word_timestamps=True, vad_filter=True)
        caption_data = {
            "language": info.language,
            "duration": info.duration,
            "segments": []
        }
        for seg in segments:
            segment = {
                "text": seg.text.strip(),
                "start": seg.start,
                "end": seg.end,
                "words": []
            }
            if seg.words:
                for w in seg.words:
                    segment["words"].append({
                        "word": w.word.strip(),
                        "start": w.start,
                        "end": w.end,
                        "probability": w.probability
                    })
            caption_data["segments"].append(segment)

        out_path = out_dir / f"{video_path.stem}_captions.json"
        with open(out_path, "w") as f:
            json.dump(caption_data, f, indent=2)
        print(f"Transcribed {video_path} -> {out_path}")

    def transcribe_all(self, videos_dir="shorts", output_dir="captions"):
        in_dir = Path(videos_dir)
        for f in in_dir.glob("*.mp4"):
            self.transcribe_video(f, output_dir)