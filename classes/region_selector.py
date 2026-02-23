import cv2
import numpy as np
from .config import ProjectConfig, RegionConfig, TargetConfig

class RegionSelector:
    def __init__(self, video_path: str, config: ProjectConfig = None, save_path: str = "regions.json", no_facecam: bool = False):
        self.video_path = video_path
        self.save_path = save_path
        self.no_facecam = no_facecam

        # If no config provided, create a new one with default target dimensions
        if config is None:
            default_target = TargetConfig(
                width=1080,
                height=1920,
                facecam_height=768,
                gameplay_height=1152
            )
            self.config = ProjectConfig(target=default_target, facecam=None, gameplay=None, gameplay_only=None)
        else:
            self.config = config
            # If config has no target or target is None, set default target
            if self.config.target is None or self.config.target.width is None:
                self.config.target = TargetConfig(
                    width=1080,
                    height=1920,
                    facecam_height=768,
                    gameplay_height=1152
                )

        self.frame = None
        self.display = None
        self.mode = 'gameplay' if self.no_facecam else 'facecam'
        self.facecam_rect = None
        self.gameplay_rect = None
        self.drawing = False
        self.drag_start = None
        self.drag_end = None
        self.drag_type = None
        self.selected_rect = None
        self.history = []

        # Pre-populate from config based on mode
        if not self.no_facecam and self.config.facecam and self.config.facecam.width is not None:
            self.facecam_rect = (
                self.config.facecam.x,
                self.config.facecam.y,
                self.config.facecam.width,
                self.config.facecam.height
            )
        if self.config.gameplay and self.config.gameplay.width is not None:
            self.gameplay_rect = (
                self.config.gameplay.x,
                self.config.gameplay.y,
                self.config.gameplay.width,
                self.config.gameplay.height
            )
        # For no‑facecam mode, also pre‑populate from gameplay_only if available
        if self.no_facecam and self.config.gameplay_only and self.config.gameplay_only.width is not None:
            self.gameplay_rect = (
                self.config.gameplay_only.x,
                self.config.gameplay_only.y,
                self.config.gameplay_only.width,
                self.config.gameplay_only.height
            )

    def push_history(self, mode, rect):
        self.history.append((mode, rect))

    def undo(self):
        if not self.history:
            return
        mode, rect = self.history.pop()
        if mode == 'facecam':
            self.facecam_rect = rect
        else:
            self.gameplay_rect = rect

    def redraw_display(self):
        if self.frame is None:
            return
        self.display = self.frame.copy()
        h, w = self.display.shape[:2]

        # Instructions depend on mode
        if self.no_facecam:
            inst = [
                "g: Gameplay   s: Save   q: Quit   Ctrl+Z: Undo",
                "Click inside to move   Click edges to resize"
            ]
        else:
            inst = [
                "f: Facecam   g: Gameplay   s: Save   q: Quit   Ctrl+Z: Undo",
                "Click inside to move   Click edges to resize"
            ]
        for i, line in enumerate(inst):
            cv2.putText(self.display, line, (10, 30 + i*30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        if self.facecam_rect and not self.no_facecam:
            x, y, w, h = self.facecam_rect
            color = (255, 0, 0) if self.mode == 'facecam' else (128, 128, 255)
            cv2.rectangle(self.display, (x, y), (x+w, y+h), color, 2)
            cv2.putText(self.display, "Facecam", (x, y-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        if self.gameplay_rect:
            x, y, w, h = self.gameplay_rect
            color = (0, 0, 255) if self.mode == 'gameplay' else (255, 128, 128)
            cv2.rectangle(self.display, (x, y), (x+w, y+h), color, 2)
            cv2.putText(self.display, "Gameplay", (x, y-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        if self.selected_rect:
            x, y, w, h = self.selected_rect
            cv2.rectangle(self.display, (x, y), (x+w, y+h), (0, 255, 255), 3)

        if self.drawing and self.drag_start and self.drag_end:
            x1, y1 = self.drag_start
            x2, y2 = self.drag_end
            cv2.rectangle(self.display, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(self.display, f"{self.mode} selection", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

        cv2.imshow("Select Regions", self.display)

    def get_rect_at(self, x, y):
        rects = []
        if self.facecam_rect and not self.no_facecam:
            rects.append(('facecam', self.facecam_rect))
        if self.gameplay_rect:
            rects.append(('gameplay', self.gameplay_rect))
        for m, (rx, ry, rw, rh) in rects:
            if rx <= x <= rx+rw and ry <= y <= ry+rh:
                return m, (rx, ry, rw, rh)
        return None, None

    def get_resize_type(self, rect, x, y, threshold=10):
        rx, ry, rw, rh = rect
        left = abs(x - rx) <= threshold
        right = abs(x - (rx+rw)) <= threshold
        top = abs(y - ry) <= threshold
        bottom = abs(y - (ry+rh)) <= threshold
        if left and top: return 'tl'
        if left and bottom: return 'bl'
        if right and top: return 'tr'
        if right and bottom: return 'br'
        if left: return 'l'
        if right: return 'r'
        if top: return 't'
        if bottom: return 'b'
        return None

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            mode_hit, rect = self.get_rect_at(x, y)
            if mode_hit == self.mode:
                self.selected_rect = rect
                resize_type = self.get_resize_type(rect, x, y)
                if resize_type:
                    self.drag_type = resize_type
                    self.drag_start = (x, y)
                    self.push_history(self.mode, rect)
                else:
                    self.drag_type = 'move'
                    self.drag_start = (x, y)
                    self.push_history(self.mode, rect)
                self.drawing = False
            else:
                self.drawing = True
                self.selected_rect = None
                self.drag_start = (x, y)
                self.drag_end = (x, y)
                # Save previous rect for undo if we're replacing it
                if self.mode == 'facecam' and self.facecam_rect and not self.no_facecam:
                    self.push_history('facecam', self.facecam_rect)
                elif self.mode == 'gameplay' and self.gameplay_rect:
                    self.push_history('gameplay', self.gameplay_rect)

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                self.drag_end = (x, y)
            elif self.drag_type:
                dx = x - self.drag_start[0]
                dy = y - self.drag_start[1]
                rx, ry, rw, rh = self.selected_rect
                new_rect = list(self.selected_rect)
                if self.drag_type == 'move':
                    new_rect[0] = rx + dx
                    new_rect[1] = ry + dy
                elif self.drag_type == 'l':
                    new_rect[0] = rx + dx
                    new_rect[2] = rw - dx
                elif self.drag_type == 'r':
                    new_rect[2] = rw + dx
                elif self.drag_type == 't':
                    new_rect[1] = ry + dy
                    new_rect[3] = rh - dy
                elif self.drag_type == 'b':
                    new_rect[3] = rh + dy
                elif self.drag_type == 'tl':
                    new_rect[0] = rx + dx
                    new_rect[1] = ry + dy
                    new_rect[2] = rw - dx
                    new_rect[3] = rh - dy
                elif self.drag_type == 'tr':
                    new_rect[1] = ry + dy
                    new_rect[2] = rw + dx
                    new_rect[3] = rh - dy
                elif self.drag_type == 'bl':
                    new_rect[0] = rx + dx
                    new_rect[2] = rw - dx
                    new_rect[3] = rh + dy
                elif self.drag_type == 'br':
                    new_rect[2] = rw + dx
                    new_rect[3] = rh + dy

                if new_rect[2] < 5: new_rect[2] = 5
                if new_rect[3] < 5: new_rect[3] = 5

                if self.mode == 'facecam' and not self.no_facecam:
                    self.facecam_rect = tuple(new_rect)
                else:
                    self.gameplay_rect = tuple(new_rect)
                self.selected_rect = tuple(new_rect)
                self.drag_start = (x, y)

        elif event == cv2.EVENT_LBUTTONUP:
            if self.drawing:
                x1, y1 = self.drag_start
                x2, y2 = x, y
                if abs(x2-x1) > 5 and abs(y2-y1) > 5:
                    rect = (min(x1,x2), min(y1,y2), abs(x2-x1), abs(y2-y1))
                    if self.mode == 'facecam' and not self.no_facecam:
                        self.facecam_rect = rect
                    else:
                        self.gameplay_rect = rect
                self.drawing = False
                self.drag_end = None
            elif self.drag_type:
                self.drag_type = None
                self.drag_start = None
                self.selected_rect = None

    def run(self) -> ProjectConfig:
        cap = cv2.VideoCapture(self.video_path)
        ret, self.frame = cap.read()
        cap.release()
        if not ret:
            raise RuntimeError("Could not read first frame from video.")

        cv2.namedWindow("Select Regions")
        cv2.setMouseCallback("Select Regions", self.mouse_callback)

        print("\n=== Region Selection ===")
        if self.no_facecam:
            print("No‑Facecam mode: draw gameplay rectangle only.")
            print("Press 'g' to ensure you're in gameplay mode (it's the only mode).")
        else:
            print("Press 'f' to switch to Facecam mode")
            print("Press 'g' to switch to Gameplay mode")
        print("Click and drag to draw new rectangle for current mode")
        print("Click inside a rectangle to move it")
        print("Click near an edge to resize")
        print("Ctrl+Z to undo last change")
        print("Press 's' to save and quit")
        print("Press 'q' to quit without saving")

        while True:
            self.redraw_display()
            key = cv2.waitKey(50) & 0xFF
            if not self.no_facecam:
                if key == ord('f'):
                    self.mode = 'facecam'
                    print("Mode: Facecam")
                elif key == ord('g'):
                    self.mode = 'gameplay'
                    print("Mode: Gameplay")
            else:
                # In no‑facecam mode, pressing 'g' still switches to gameplay (only mode)
                if key == ord('g'):
                    self.mode = 'gameplay'
                    print("Mode: Gameplay")
            if key == 26:  # Ctrl+Z
                self.undo()
            elif key == ord('s'):
                if self.no_facecam:
                    if self.gameplay_rect is None:
                        print("Gameplay region must be defined before saving.")
                        continue
                else:
                    if self.facecam_rect is None or self.gameplay_rect is None:
                        print("Both regions must be defined before saving.")
                        continue

                # Ensure target is not None (set default if missing)
                if self.config.target is None or self.config.target.width is None:
                    self.config.target = TargetConfig(
                        width=1080,
                        height=1920,
                        facecam_height=768,
                        gameplay_height=1152
                    )

                if self.no_facecam:
                    # Save to gameplay_only – do not modify target, facecam, or gameplay
                    self.config.gameplay_only = RegionConfig(
                        x=self.gameplay_rect[0], y=self.gameplay_rect[1],
                        width=self.gameplay_rect[2], height=self.gameplay_rect[3],
                        mode="fill"
                    )
                    # Leave facecam and gameplay untouched (they may still exist from previous normal mode)
                else:
                    # Save normal regions – preserve existing target and leave gameplay_only untouched
                    facecam_mode = self.config.facecam.mode if self.config.facecam and self.config.facecam.mode else "fill"
                    gameplay_mode = self.config.gameplay.mode if self.config.gameplay and self.config.gameplay.mode else "fill"

                    self.config.facecam = RegionConfig(
                        x=self.facecam_rect[0], y=self.facecam_rect[1],
                        width=self.facecam_rect[2], height=self.facecam_rect[3],
                        mode=facecam_mode
                    )
                    self.config.gameplay = RegionConfig(
                        x=self.gameplay_rect[0], y=self.gameplay_rect[1],
                        width=self.gameplay_rect[2], height=self.gameplay_rect[3],
                        mode=gameplay_mode
                    )
                self.config.save(self.save_path)
                print(f"Configuration saved to {self.save_path}")
                break
            elif key == ord('q'):
                print("Quit without saving.")
                return None

        cv2.destroyAllWindows()
        return self.config