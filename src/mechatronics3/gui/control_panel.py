"""Tkinter GUI for manual robot control.

Provides a :class:`ControlPanel` window with directional buttons, servo
controls, mode toggling, a sensor bar-chart canvas, and keyboard event
dispatch — used by :mod:`mechatronics3.strategies.manual_strategy`.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

# ---------------------------------------------------------------------------
# Virtual keycodes — portable across platforms via _KEYSYM_TO_CODE mapping
# ---------------------------------------------------------------------------

KEY_UP = 38
KEY_LEFT = 37
KEY_RIGHT = 39
KEY_DOWN = 40
KEY_PAGE_UP = 33
KEY_PAGE_DOWN = 34
KEY_HOME = 36
KEY_END = 35
KEY_SPACE = 32
KEY_P = 80
KEY_S = 83
KEY_ESCAPE = 27

_KEYSYM_TO_CODE: dict[str, int] = {
    "Up": KEY_UP,
    "Left": KEY_LEFT,
    "Right": KEY_RIGHT,
    "Down": KEY_DOWN,
    "Prior": KEY_PAGE_UP,
    "Next": KEY_PAGE_DOWN,
    "Home": KEY_HOME,
    "End": KEY_END,
    "space": KEY_SPACE,
    "Escape": KEY_ESCAPE,
    "p": KEY_P,
    "P": KEY_P,
    "s": KEY_S,
    "S": KEY_S,
}

# Colour palette
_BG = "#1e1e2e"
_FG = "#cdd6f4"
_ACCENT = "#89b4fa"
_ACCENT_ACTIVE = "#74c7ec"
_BTN_BG = "#313244"
_BTN_ACTIVE = "#45475a"
_CANVAS_BG = "#181825"
_BAR_FILL = "#89b4fa"
_BAR_OUTLINE = "#74c7ec"
_STATUS_OK = "#a6e3a1"
_STATUS_WARN = "#f9e2af"


class ControlPanel:
    """Tkinter window with directional buttons, servo controls, and sensor canvas.

    Parameters
    ----------
    title:
        Window title.
    canvas_width:
        Width (px) of the sensor bar-chart area.
    canvas_height:
        Height (px) of the sensor bar-chart area.
    """

    def __init__(
        self,
        *,
        title: str = "Mechatronics3 Control",
        canvas_width: int = 360,
        canvas_height: int = 200,
    ) -> None:
        self._root = tk.Tk()
        self._root.title(title)
        self._root.geometry("480x560")
        self._root.minsize(400, 480)
        self._root.configure(bg=_BG)

        self._canvas_w = canvas_width
        self._canvas_h = canvas_height
        self._key_callback: Callable[[int], None] | None = None

        self._configure_style()
        self._build_ui()
        self._root.bind("<Key>", self._on_key)

    # ------------------------------------------------------------------
    # Theming
    # ------------------------------------------------------------------

    def _configure_style(self) -> None:
        style = ttk.Style(self._root)
        style.theme_use("clam")

        style.configure(".", background=_BG, foreground=_FG)
        style.configure("TFrame", background=_BG)
        style.configure(
            "TLabel",
            background=_BG,
            foreground=_FG,
            font=("Helvetica", 10),
        )
        style.configure(
            "Title.TLabel",
            background=_BG,
            foreground=_ACCENT,
            font=("Helvetica", 14, "bold"),
        )
        style.configure(
            "Status.TLabel",
            background=_BG,
            foreground=_STATUS_OK,
            font=("Helvetica", 10),
        )
        style.configure(
            "TButton",
            background=_BTN_BG,
            foreground=_FG,
            font=("Helvetica", 12, "bold"),
            borderwidth=0,
            padding=6,
        )
        style.map(
            "TButton",
            background=[("active", _BTN_ACTIVE)],
            foreground=[("active", _ACCENT)],
        )
        style.configure(
            "Accent.TButton",
            background=_ACCENT,
            foreground=_BG,
            font=("Helvetica", 10, "bold"),
        )
        style.map(
            "Accent.TButton",
            background=[("active", _ACCENT_ACTIVE)],
        )
        style.configure(
            "TLabelframe",
            background=_BG,
            foreground=_FG,
        )
        style.configure(
            "TLabelframe.Label",
            background=_BG,
            foreground=_ACCENT,
            font=("Helvetica", 10, "bold"),
        )

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        container = ttk.Frame(self._root, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        # Title
        ttk.Label(container, text="Mechatronics3", style="Title.TLabel").pack(pady=(0, 8))

        # --- Motor controls ---
        motor_frame = ttk.LabelFrame(container, text="Drive", padding=6)
        motor_frame.pack(fill=tk.X, pady=(0, 8))

        grid = ttk.Frame(motor_frame)
        grid.pack()
        for col in range(3):
            grid.columnconfigure(col, weight=1, minsize=72)
        for row in range(2):
            grid.rowconfigure(row, weight=1, minsize=40)

        self._add_btn(grid, "\u25b2  Up", KEY_UP, row=0, col=1)
        self._add_btn(grid, "\u25c0  Left", KEY_LEFT, row=1, col=0)
        self._add_btn(grid, "\u25bc  Down", KEY_DOWN, row=1, col=1)
        self._add_btn(grid, "\u25b6  Right", KEY_RIGHT, row=1, col=2)

        # --- Servo controls ---
        servo_frame = ttk.LabelFrame(container, text="Servo", padding=6)
        servo_frame.pack(fill=tk.X, pady=(0, 8))

        sgrid = ttk.Frame(servo_frame)
        sgrid.pack()
        for col in range(4):
            sgrid.columnconfigure(col, weight=1, minsize=56)

        self._add_btn(sgrid, "H \u2212", KEY_PAGE_DOWN, row=0, col=0, width=10)
        self._add_btn(sgrid, "H +", KEY_PAGE_UP, row=0, col=1, width=10)
        self._add_btn(sgrid, "V \u2212", KEY_HOME, row=0, col=2, width=10)
        self._add_btn(sgrid, "V +", KEY_END, row=0, col=3, width=10)

        # --- Mode controls ---
        mode_frame = ttk.Frame(container)
        mode_frame.pack(fill=tk.X, pady=(0, 8))

        self._btn_start = ttk.Button(
            mode_frame,
            text="\u25b6 Start [S]",
            style="Accent.TButton",
            command=lambda: self._dispatch(KEY_S),
        )
        self._btn_start.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 4))

        self._btn_pause = ttk.Button(
            mode_frame,
            text="\u23f8 Pause [P]",
            command=lambda: self._dispatch(KEY_P),
        )
        self._btn_pause.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(4, 4))

        self._btn_stop = ttk.Button(
            mode_frame,
            text="\u23f9 Stop [Esc]",
            command=lambda: self._dispatch(KEY_ESCAPE),
        )
        self._btn_stop.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(4, 0))

        # --- Sensor canvas ---
        canvas_frame = ttk.LabelFrame(container, text="Sensor", padding=4)
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        self._canvas = tk.Canvas(
            canvas_frame,
            bg=_CANVAS_BG,
            highlightthickness=0,
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._canvas.bind("<Configure>", self._on_canvas_resize)
        self._last_sensor_data: list[int] | list[float] = []

        # --- Status bar ---
        self._status_var = tk.StringVar(value="Ready")
        self._status_label = ttk.Label(
            container,
            textvariable=self._status_var,
            style="Status.TLabel",
            anchor=tk.W,
        )
        self._status_label.pack(fill=tk.X)

        # --- Key legend ---
        legend = "Keys: \u2190\u2191\u2192\u2193 drive  |  PgUp/PgDn H-servo  |  Home/End V-servo  |  Space pause 5 s"
        ttk.Label(container, text=legend, font=("Helvetica", 8)).pack(fill=tk.X, pady=(2, 0))

    def _add_btn(
        self,
        parent: ttk.Frame,
        text: str,
        keycode: int,
        *,
        row: int,
        col: int,
        width: int = 12,
    ) -> ttk.Button:
        btn = ttk.Button(
            parent,
            text=text,
            width=width,
            command=lambda c=keycode: self._dispatch(c),
        )
        btn.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")
        return btn

    # ------------------------------------------------------------------
    # Event dispatch
    # ------------------------------------------------------------------

    def set_key_handler(self, callback: Callable[[int], None]) -> None:
        """Register *callback* to receive keycode integers on every key/button press."""
        self._key_callback = callback

    def _dispatch(self, keycode: int) -> None:
        if self._key_callback is not None:
            self._key_callback(keycode)

    def _on_key(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        code = _KEYSYM_TO_CODE.get(event.keysym, event.keycode)
        self._dispatch(code)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def set_status(self, text: str, *, warn: bool = False) -> None:
        """Update the status bar text."""
        self._status_var.set(text)
        style = ttk.Style(self._root)
        colour = _STATUS_WARN if warn else _STATUS_OK
        style.configure("Status.TLabel", foreground=colour)

    # ------------------------------------------------------------------
    # Sensor visualisation
    # ------------------------------------------------------------------

    def _on_canvas_resize(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._last_sensor_data:
            self._draw_bars(self._last_sensor_data)

    def visualize(self, sensor_data: list[int] | list[float]) -> None:
        """Draw a bar chart of *sensor_data* on the canvas."""
        self._last_sensor_data = list(sensor_data)
        self._draw_bars(self._last_sensor_data)

    def _draw_bars(self, data: list[int] | list[float]) -> None:
        self._canvas.delete("all")
        if not data:
            return

        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()
        if cw < 2 or ch < 2:
            return

        padding = 4
        draw_w = cw - 2 * padding
        draw_h = ch - 2 * padding

        peak = max(data) if data else 1
        scale = draw_h / (peak + 1) if peak else 1.0
        bar_w = draw_w / len(data)
        gap = max(1, int(bar_w * 0.1))

        for i, value in enumerate(data):
            x1 = padding + i * bar_w + gap
            x2 = padding + (i + 1) * bar_w - gap
            y1 = ch - padding
            y2 = ch - padding - value * scale
            self._canvas.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                fill=_BAR_FILL,
                outline=_BAR_OUTLINE,
                width=1,
            )

    # ------------------------------------------------------------------
    # Scheduling / lifecycle
    # ------------------------------------------------------------------

    def schedule(self, delay_ms: int, callback: Callable[[], None]) -> None:
        """Schedule *callback* to run after *delay_ms* milliseconds."""
        self._root.after(delay_ms, callback)

    def update(self) -> None:
        """Process pending tkinter events (keeps the UI responsive)."""
        self._root.update_idletasks()
        self._root.update()

    def run(self) -> None:
        """Enter the tkinter main loop (blocks until the window is closed)."""
        self._root.mainloop()

    def destroy(self) -> None:
        """Destroy the tkinter root window."""
        self._root.destroy()
