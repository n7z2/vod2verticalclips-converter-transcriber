from moviepy.editor import VideoFileClip

class VideoIngestor:
    def __init__(self, video_path: str):
        self.video_path = video_path
        self.clip = None

    def load(self) -> VideoFileClip:
        if self.clip is None:
            self.clip = VideoFileClip(self.video_path)
        return self.clip

    def get_metadata(self) -> dict:
        clip = self.load()
        return {
            "duration": clip.duration,
            "fps": clip.fps,
            "size": clip.size,
            "audio_exists": clip.audio is not None,
            "codec": clip.reader.infos.get('video_codec', 'unknown')
        }

    def close(self):
        if self.clip:
            self.clip.close()
            self.clip = None