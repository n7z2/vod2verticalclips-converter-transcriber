import sys
import os
import json
import re
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def apply_emojis(text, emoji_map):
    words = text.split()
    new_words = []
    for w in words:
        clean = re.sub(r'[^\w]', '', w).lower()
        if clean in emoji_map:
            new_words.append(f"{w} {emoji_map[clean]}")
        else:
            new_words.append(w)
    return ' '.join(new_words)

def create_word_groups(caption_data, pause_threshold=0.3, max_words=5):
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

def create_outline_clip(text, start, end, style, gameplay_region):
    """Create a clip with an outline by layering multiple copies."""
    margin = style.get('margin_bottom', 50)
    target_bottom_y = gameplay_region[1] + gameplay_region[3] - margin
    max_width = int(gameplay_region[2] * 0.9)

    font = style.get('font', 'Arial')
    fontsize = style.get('fontsize', 60)
    color = style.get('color', 'white')
    outline_color = style.get('outline_color', 'black')
    outline_width = style.get('outline_width', 2)

    # Create base and outline text clips
    try:
        base_txt = TextClip(text, fontsize=fontsize, font=font, color=color, method='label')
        outline_txt = TextClip(text, fontsize=fontsize, font=font, color=outline_color, method='label')
    except Exception as e:
        print(f"Font '{font}' not found, using Arial. Error: {e}")
        base_txt = TextClip(text, fontsize=fontsize, font='Arial', color=color, method='label')
        outline_txt = TextClip(text, fontsize=fontsize, font='Arial', color=outline_color, method='label')

    # Scale down if too wide
    if base_txt.w > max_width:
        base_txt = base_txt.resize(width=max_width)
        outline_txt = outline_txt.resize(width=max_width)

    # Calculate position within gameplay region (centered horizontally)
    abs_x = (gameplay_region[2] - base_txt.w) // 2
    abs_y = target_bottom_y - base_txt.h

    # Create outline layers (shifted)
    layers = []
    shifts = [(-outline_width, -outline_width), (-outline_width, outline_width),
              (outline_width, -outline_width), (outline_width, outline_width)]
    for dx, dy in shifts:
        layer = outline_txt.set_position((abs_x + dx, abs_y + dy))
        layers.append(layer)

    # Add base text
    base_layer = base_txt.set_position((abs_x, abs_y))
    layers.append(base_layer)

    # Composite all layers into one clip with proper duration
    composite = CompositeVideoClip(layers, size=(gameplay_region[2], gameplay_region[3]))
    composite = composite.set_start(start).set_duration(end - start)
    return composite

def overlay_captions(video_path, captions_path, regions_path, style, output_dir="final"):
    os.makedirs(output_dir, exist_ok=True)

    video = VideoFileClip(video_path)
    regions = load_json(regions_path)
    target = regions['target']
    gameplay_region = (0, target['facecam_height'], target['width'], target['gameplay_height'])
    print(f"DEBUG: gameplay_region = {gameplay_region}")

    caption_data = load_json(captions_path)
    groups = create_word_groups(caption_data,
                                pause_threshold=style.get('pause_threshold', 0.3),
                                max_words=style.get('max_words_per_caption', 5))

    caption_clips = []
    emoji_map = style.get('emoji_map', {})
    use_outline = style.get('outline_color') and style.get('outline_width', 0) > 0

    for group in groups:
        text = ' '.join(w['word'] for w in group).strip()
        if not text:
            continue
        if emoji_map:
            text = apply_emojis(text, emoji_map)
        start = group[0]['start']
        end = group[-1]['end']
        if use_outline:
            clip = create_outline_clip(text, start, end, style, gameplay_region)
            # Position the clip at the top-left of the gameplay region
            clip = clip.set_position((0, target['facecam_height']))
            caption_clips.append(clip)

    print(f"DEBUG: Created {len(caption_clips)} caption clips")

    final = CompositeVideoClip([video] + caption_clips, size=video.size)
    final.audio = video.audio

    base = os.path.basename(video_path)
    name, _ = os.path.splitext(base)
    out_path = os.path.join(output_dir, f"{name}_captioned.mp4")

    final.write_videofile(out_path, codec='libx264', audio_codec='aac', preset='medium')

    video.close()
    final.close()
    print(f"Saved {out_path}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python caption_overlay.py <video_file> <captions_json> [style_json]")
        sys.exit(1)

    video_path = sys.argv[1]
    captions_path = sys.argv[2]
    style_path = sys.argv[3] if len(sys.argv) > 3 else "caption_style.json"

    style = {
        "font": "Open Sans Extrabold",
        "fontsize": 86,
        "color": "white",
        "outline_color": "black",
        "outline_width": 5,
        "margin_bottom": 200,
        "animation": "fade",
        "fade_duration": 0.2,
        "pause_threshold": 0.3,
        "max_words_per_caption": 3,
        "emoji_map": {}
    }

    if os.path.exists(style_path):
        user_style = load_json(style_path)
        style.update(user_style)
        print(f"Loaded style from {style_path}")
        print("Current style settings:")
        for key, value in style.items():
            print(f"  {key}: {value}")
    else:
        print("Using default style.")

    if not os.path.exists("regions.json"):
        print("regions.json not found.")
        sys.exit(1)

    overlay_captions(video_path, captions_path, "regions.json", style)

if __name__ == "__main__":
    main()