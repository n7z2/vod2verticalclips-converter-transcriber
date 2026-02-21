import matplotlib.pyplot as plt
import matplotlib.patches as patches
from moviepy.editor import VideoFileClip
import sys
import os

def pick_rectangle(image):
    fig, ax = plt.subplots(1)
    ax.imshow(image)
    plt.title("Click two opposite corners of the region")
    points = []

    def onclick(event):
        if event.xdata is None or event.ydata is None:
            return
        points.append((int(event.xdata), int(event.ydata)))
        ax.plot(event.xdata, event.ydata, 'ro')
        fig.canvas.draw()
        if len(points) == 2:
            plt.close()

    fig.canvas.mpl_connect('button_press_event', onclick)
    plt.show()

    if len(points) == 2:
        x1, y1 = points[0]
        x2, y2 = points[1]
        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        return x, y, w, h
    else:
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python pick_region.py <video_file>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    if not os.path.exists(video_path):
        print("Video not found.")
        sys.exit(1)
    
    clip = VideoFileClip(video_path)
    frame = clip.get_frame(0)  # first frame
    clip.close()
    
    print("Pick facecam region (click two opposite corners)")
    facecam = pick_rectangle(frame)
    if not facecam:
        print("Cancelled.")
        return
    
    print("Pick gameplay region (click two opposite corners)")
    gameplay = pick_rectangle(frame)
    if not gameplay:
        print("Cancelled.")
        return
    
    print("\n--- Region Coordinates ---")
    print(f"Facecam: x={facecam[0]}, y={facecam[1]}, w={facecam[2]}, h={facecam[3]}")
    print(f"Gameplay: x={gameplay[0]}, y={gameplay[1]}, w={gameplay[2]}, h={gameplay[3]}")
    print("\nUpdate your regions.json with these values.")

if __name__ == "__main__":
    main()