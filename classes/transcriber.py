"""Transcribe videos using faster-whisper with auto device detection."""

import os
import json
from pathlib import Path
from faster_whisper import WhisperModel

class Transcriber:
    """Transcribe videos and save word-level JSON captions (auto device)."""

    def __init__(self, model_size="base"):
        self.model_size = model_size
        self.model = None

    def _load_model(self):
        if self.model is None:
            # Let faster-whisper auto-detect CUDA; if not available, fallback to CPU
            self.model = WhisperModel(self.model_size, device="auto", compute_type="auto")

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