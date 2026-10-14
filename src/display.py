import math
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk

import config


class RadarDisplay:
    def __init__(self, radar, on_detection=None):
        self.radar = radar
        self.on_detection = on_detection
        self.root = tk.Tk()
        self.root.title("RADVEM - Radar")
        self.root.geometry(
            f"{config.SCREEN_WIDTH}x{config.SCREEN_HEIGHT}"
        )
        self.root.resizable(False, False)

        self.events = queue.Queue()
        self.detections = {}
        self.closing = threading.Event()
        self.scan_failed = False
        self.scan_error = None
        self.scanner = threading.Thread(
            target=self._scan_loop,
            name="radar-scan",
            daemon=False,
        )

        self.canvas = tk.Canvas(
            self.root,
            width=config.SCREEN_WIDTH,
            height=config.SCREEN_HEIGHT,
            background="#08121b",
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        controls = ttk.Frame(self.root, padding=8)
        controls.place(x=12, y=10)

        self.toggle_button = ttk.Button(
            controls,
            text="Iniciar varredura",
            command=self._toggle_scan,
        )
        self.toggle_button.pack(side="left")

        self.status = tk.StringVar(value="Parado")
        ttk.Label(controls, textvariable=self.status).pack(
            side="left", padx=12
        )

        self._draw_radar()
        self.radar.on_detection = self._queue_detection
        self.root.protocol("WM_DELETE_WINDOW", self._begin_shutdown)
        self.root.after(50, self._process_events)
        self.scanner.start()

    def run(self):
        self.root.mainloop()

    def _draw_radar(self):
        center_x = config.RADAR_CENTER_X
        center_y = config.RADAR_CENTER_Y
        radius = config.RADAR_RADIUS

        for fraction in (0.25, 0.5, 0.75, 1.0):
            ring_radius = radius * fraction
            self.canvas.create_oval(
                center_x - ring_radius,
                center_y - ring_radius,
                center_x + ring_radius,
                center_y + ring_radius,
                outline="#1d554b",
                width=1,
            )

        self.canvas.create_oval(
            center_x - 3,
            center_y - 3,
            center_x + 3,
            center_y + 3,
            fill="#54e39b",
            outline="",
        )

        for angle in range(config.ANGLE_MIN, config.ANGLE_MAX + 1, 30):
            radians = math.radians(angle)
            end_x = center_x + radius * math.cos(radians)
            end_y = center_y - radius * math.sin(radians)
            self.canvas.create_line(
                center_x,
                center_y,
                end_x,
                end_y,
                fill="#174238",
                width=1,
            )
            self.canvas.create_text(
                center_x + (radius + 16) * math.cos(radians),
                center_y - (radius + 16) * math.sin(radians),
                text=f"{angle}°",
                fill="#8bb8a7",
                font=("TkDefaultFont", 8),
            )

        self.sweep_line = self.canvas.create_line(
            center_x,
            center_y,
            center_x,
            center_y,
            fill="#54e39b",
            width=2,
        )
        self._draw_angle(self.radar.get_angle())

    def _draw_angle(self, angle):
        radians = math.radians(angle)
        end_x = config.RADAR_CENTER_X + config.RADAR_RADIUS * math.cos(radians)
        end_y = config.RADAR_CENTER_Y - config.RADAR_RADIUS * math.sin(radians)
        self.canvas.coords(
            self.sweep_line,
            config.RADAR_CENTER_X,
            config.RADAR_CENTER_Y,
            end_x,
            end_y,
        )

    def _toggle_scan(self):
        if self.scan_failed:
            return
        if self.radar.is_active():
            self.radar.stop()
        else:
            self.radar.start()
        self._update_status()

    def _update_status(self):
        active = self.radar.is_active()
        if self.scan_failed:
            self.status.set(f"Falha de varredura: {self.scan_error}")
        else:
            self.status.set("Varredura ativa" if active else "Parado")
        self.toggle_button.configure(
            text="Parar varredura" if active else "Iniciar varredura",
            state="disabled" if self.scan_failed else "normal",
        )

    def _scan_loop(self):
        while not self.closing.is_set():
            if not self.radar.is_active():
                self.closing.wait(0.05)
                continue

            try:
                self.radar.update()
            except Exception as error:
                self.events.put(("error", str(error)))
                return

    def _queue_detection(self, detection):
        self.events.put(("detection", detection))

    def _process_events(self):
        if self.closing.is_set():
            return

        self._draw_angle(self.radar.get_angle())
        self._update_status()

        while True:
            try:
                event_type, payload = self.events.get_nowait()
            except queue.Empty:
                break

            if event_type == "detection":
                self._show_detection(payload)
            else:
                self.scan_failed = True
                self.scan_error = payload
                self.radar.stop()
                self._update_status()

        now = time.monotonic()
        expired = [
            item_id
            for item_id, created_at in self.detections.items()
            if now - created_at >= config.FADEOUT_TIME
        ]
        for item_id in expired:
            self.canvas.delete(item_id)
            del self.detections[item_id]

        self.root.after(50, self._process_events)

    def _show_detection(self, detection):
        x = detection["x"]
        y = detection["y"]
        radius = 5
        item_id = self.canvas.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            fill="#ff5c6c",
            outline="#ffd1d5",
            width=1,
        )
        self.detections[item_id] = time.monotonic()

        if self.on_detection is not None:
            self.on_detection(detection)

    def _begin_shutdown(self):
        self.closing.set()
        self.radar.stop()
        self._finish_shutdown()

    def _finish_shutdown(self):
        if self.scanner.is_alive():
            self.root.after(50, self._finish_shutdown)
            return
        self.root.destroy()
