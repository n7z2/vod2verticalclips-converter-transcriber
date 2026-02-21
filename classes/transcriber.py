import os
import json
import glob
from faster_whisper import WhisperModel

class Transcriber:
    def __init__(self, model_size="base", device="cpu"):
        self.model_size = model_size
        self.device = device
        self.model = None

    def _load_model(self):
        if self.model is None:
            compute = "int8" if self.device == "cpu" else "float16"
            self.model = WhisperModel(self.model_size, device=self.device, compute_type=compute)

    def transcribe_video(self, video_path: str, output_dir="captions"):
        self._load_model()
        os.makedirs(output_dir, exist_ok=True)
        segments, info = self.model.transcribe(video_path, word_timestamps=True, vad_filter=True)
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

        base = os.path.basename(video_path)
        name, _ = os.path.splitext(base)
        out_path = os.path.join(output_dir, f"{name}_captions.json")
        with open(out_path, "w") as f:
            json.dump(caption_data, f, indent=2)
        print(f"Transcribed {video_path} -> {out_path}")

    def transcribe_all(self, videos_dir="shorts", output_dir="captions"):
        files = glob.glob(os.path.join(videos_dir, "*.mp4"))
        for f in files:
            self.transcribe_video(f, output_dir)