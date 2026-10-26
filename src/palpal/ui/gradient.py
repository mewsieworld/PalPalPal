"""The secret gradient (hue target) menu."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.colors import avoid_key, parse_hex, to_hex
from .theme import Theme, Tooltip, center_on


# ---------------------------------------------------------------------------
# Gradient ("secret button") menu, ported from code/ui/gradient_menu.py
# ---------------------------------------------------------------------------

GRADIENT_COLORS = [
    ("Pastel Pink", "#FFD1DC", 350, "pastel"), ("Pastel Peach", "#FFDBCC", 20, "pastel"),
    ("Pastel Yellow", "#FFFACD", 60, "pastel"), ("Pastel Mint", "#F0FFF0", 120, "pastel"),
    ("Pastel Blue", "#E6E6FA", 240, "pastel"), ("Pastel Lavender", "#E6E6FA", 270, "pastel"),
    ("Pastel Rose", "#F8BBD0", 330, "pastel"), ("Pastel Aqua", "#E0FFFF", 180, "pastel"),
    ("Light Red", "#FFB3B3", 0, "light"), ("Light Orange", "#FFD9B3", 30, "light"),
    ("Light Yellow", "#FFFF99", 60, "light"), ("Light Green", "#B3FFB3", 120, "light"),
    ("Light Blue", "#B3B3FF", 240, "light"), ("Light Purple", "#D9B3FF", 270, "light"),
    ("Pink", "#FF69B4", 330, None), ("Cyan", "#00FFFF", 180, None),
    ("Red", "#FF0000", 0, None), ("Orange", "#FF8000", 30, None),
    ("Yellow", "#FFFF00", 60, None), ("Green", "#00FF00", 120, None),
    ("Blue", "#0000FF", 240, None), ("Purple", "#8000FF", 270, None),
    ("Magenta", "#FF00FF", 300, None), ("Teal", "#008080", 180, None),
    ("Dark Red", "#800000", 0, "dark"), ("Dark Orange", "#CC4400", 30, "dark"),
    ("Dark Yellow", "#CCCC00", 60, "dark"), ("Dark Green", "#008000", 120, "dark"),
    ("Dark Blue", "#000080", 240, "dark"), ("Dark Purple", "#4B0082", 270, "dark"),
    ("Brown", "#8B4513", 30, "brown"), ("Navy", "#191970", 240, "dark"),
    ("Cool Blue", "#0080FF", 210, "cool"), ("Cool Cyan", "#00BFFF", 195, "cool"),
    ("Cool Teal", "#008B8B", 180, "cool"), ("Cool Green", "#00FF80", 150, "cool"),
    ("Cool Purple", "#8000FF", 270, "cool"), ("Cool Violet", "#4000FF", 255, "cool"),
    ("Cool Indigo", "#4B0082", 275, "cool"), ("Cool Mint", "#00FF9F", 165, "cool"),
    ("Warm Red", "#FF4000", 15, "warm"), ("Warm Orange", "#FF8000", 30, "warm"),
    ("Warm Yellow", "#FFD700", 51, "warm"), ("Warm Pink", "#FF69B4", 330, "warm"),
    ("Warm Coral", "#FF7F50", 16, "warm"), ("Warm Peach", "#FFCBA4", 28, "warm"),
    ("Warm Gold", "#FFD700", 51, "warm"), ("Warm Amber", "#FFBF00", 45, "warm"),
    ("Orange", "#FF8000", 30, "secondary"), ("Green", "#00FF00", 120, "secondary"),
    ("Purple", "#8000FF", 270, "secondary"), ("Lime", "#80FF00", 90, "secondary"),
    ("Teal", "#00FF80", 150, "secondary"), ("Magenta", "#FF0080", 315, "secondary"),
    ("Chartreuse", "#80FF00", 90, "secondary"), ("Spring Green", "#00FF80", 150, "secondary"),
    ("Red-Orange", "#FF4000", 15, "tertiary"), ("Yellow-Orange", "#FFBF00", 45, "tertiary"),
    ("Yellow-Green", "#80FF00", 90, "tertiary"), ("Blue-Green", "#00FF80", 150, "tertiary"),
    ("Blue-Purple", "#4000FF", 255, "tertiary"), ("Red-Purple", "#FF0080", 315, "tertiary"),
    ("Vermillion", "#FF4000", 15, "tertiary"), ("Turquoise", "#00FFBF", 165, "tertiary"),
    ("Light Grey", "#C0C0C0", None, "light_grey"), ("Grey", "#808080", None, "grey"),
    ("Dark Grey", "#404040", None, "dark_grey"), ("White", "#FFFFFF", None, "white"),
    ("Black", "#000000", None, "black"), ("Beige", "#F5F5DC", 60, "beige"),
    ("Cream", "#FFFDD0", 60, "cream"), ("Tan", "#D2B48C", 30, "tan"),
]


GRADIENT_ROWS = [
    ("Pastel:", 0, "pastel"), ("Light:", 8, "light"), ("Standard:", 16, None), ("Dark:", 24, "dark"),
    ("Cool:", 32, "cool"), ("Warm:", 40, "warm"), ("Secondary:", 48, "secondary"),
    ("Tertiary:", 56, "tertiary"), ("Neutral:", 64, "neutral"),
]


SECRET_MESSAGE = ("You found my secret button! Change multiple colors in a hurry using this menu. "
                  "Different UI available via Options Menu!")


def gradient_color(color, target_hue, variant, adjust_hue=True):
    """One color through the gradient rules. Variants apply inside the loop (the old code had them outside)."""
    r, g, b = color
    if target_hue is None or variant in ("grey", "light_grey", "dark_grey", "black", "white"):
        grey = int(0.299 * r + 0.587 * g + 0.114 * b)
        if variant == "light_grey":
            v = min(255, int(grey * 1.5))
            return (v, v, v)
        if variant == "dark_grey":
            v = int(grey * 0.5)
            return (v, v, v)
        if variant == "grey":
            return (grey, grey, grey)
        h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        v = v * 0.2 if variant == "black" else min(1.0, v + (1.0 - v) * 0.8)
        rr, gg, bb = colorsys.hsv_to_rgb(h, s, v)
        return (int(rr * 255), int(gg * 255), int(bb * 255))

    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    if adjust_hue and s > 0.1:
        h = (target_hue % 360) / 360.0
    if variant == "pastel":
        v, s = min(1.0, v + (1.0 - v) * 0.8), s * 0.3
    elif variant == "light":
        v, s = min(1.0, v + (1.0 - v) * 0.6), s * 0.7
    elif variant == "dark":
        v = v * 0.4
    elif variant in ("beige", "cream", "tan"):
        s = s * 0.3
        if variant == "cream":
            v = min(1.0, v + (1.0 - v) * 0.7)
        elif variant == "tan":
            v = v * 0.8
        else:
            v = min(1.0, v + (1.0 - v) * 0.4)
    elif variant == "brown":
        s, v = s * 0.6, v * 0.5
    elif variant == "cool":
        s, v = min(1.0, s * 1.2), min(1.0, v * 1.1)
    elif variant == "warm":
        s, v = min(1.0, s * 1.3), min(1.0, v * 1.05)
    elif variant == "secondary":
        s, v = min(1.0, s * 1.5), min(1.0, v * 1.1)
    elif variant == "tertiary":
        s, v = min(1.0, s * 1.2), min(1.0, v * 1.05)
    rr, gg, bb = colorsys.hsv_to_rgb(h, s, v)
    return (int(rr * 255), int(gg * 255), int(bb * 255))


class GradientTarget:
    """What a gradient menu edits: callables for the layer, the indexes, and what to do after a change."""

    def __init__(self, layer, indices, changed, step_frame=None):
        self.layer, self.indices, self.changed, self.step_frame = layer, indices, changed, step_frame


class GradientMenu:
    """target is a GradientTarget."""

    def __init__(self, app, parent, target):
        self.app, self.target = app, target
        layer = target.layer()
        if layer is None:
            return
        self.layer = layer
        self.original = list(layer.colors)
        self.adjust_hue = tk.BooleanVar(value=True)
        self.adjust_sat = tk.BooleanVar(value=False)
        self.adjust_val = tk.BooleanVar(value=False)

        self.win = tk.Toplevel(parent)
        self.win.title("Gradient Hue Adjustment")
        self.win.resizable(False, False)
        self.win.transient(parent)

        menubar = tk.Menu(self.win)
        options = tk.Menu(menubar, tearoff=0)
        self.ui_var = tk.StringVar(value=app.store.get("gradient_ui"))
        options.add_radiobutton(label="Buttons", value="Buttons", variable=self.ui_var, command=self.switch_ui)
        options.add_radiobutton(label="Strips", value="Strips", variable=self.ui_var, command=self.switch_ui)
        menubar.add_cascade(label="Options", menu=options)
        self.win.configure(menu=menubar)

        self.main = tk.Frame(self.win)
        self.main.pack(padx=15, pady=15)
        self.build()
        center_on(self.win, parent)
        self.win.grab_set()
        self.win.focus_set()
        # Arrow keys still flip through frames in the editor behind this window, as before
        step = target.step_frame
        if step:
            self.win.bind("<Left>", lambda e: step(-1))
            self.win.bind("<Right>", lambda e: step(1))

    def build(self):
        for w in self.main.winfo_children():
            w.destroy()
        tk.Label(self.main, text=SECRET_MESSAGE, wraplength=420, justify="center",
                 font=("Arial", 9, "italic")).pack(pady=(0, 8))
        tk.Label(self.main, text="Adjust all colors to match:", font=("Arial", 10, "bold")).pack(pady=(0, 5))
        checks = tk.Frame(self.main)
        checks.pack(pady=(0, 10))
        tk.Checkbutton(checks, text="Hue", variable=self.adjust_hue).pack(side="left", padx=5)
        tk.Checkbutton(checks, text="Saturation", variable=self.adjust_sat).pack(side="left", padx=5)
        tk.Checkbutton(checks, text="Value", variable=self.adjust_val).pack(side="left", padx=5)

        rows = tk.Frame(self.main)
        rows.pack(pady=(0, 10))
        strips = self.ui_var.get() == "Strips"
        for label, start, variant in GRADIENT_ROWS:
            entries = GRADIENT_COLORS[start:start + 8]
            row = tk.Frame(rows)
            row.pack(pady=(0, 3), anchor="w")
            tk.Label(row, text=label, width=9, anchor="w", font=("Arial", 8)).pack(side="left", padx=(0, 5))
            if strips:
                self._strip(row, entries, variant)
            else:
                for name, hex_color, hue, var in entries:
                    btn = tk.Button(row, text="  ", bg=hex_color, activebackground=hex_color, width=3, height=1,
                                    command=lambda h=hue, v=var: self.apply(h, v))
                    btn._cp_keep = True
                    btn.pack(side="left", padx=1)
                    Tooltip(btn, name, self.app)

        buttons = tk.Frame(self.main)
        buttons.pack(pady=(10, 0))
        tk.Button(buttons, text="Reset to Original", command=self.reset).pack(side="left", padx=(0, 10))
        tk.Button(buttons, text="Close", command=self.win.destroy).pack(side="left")
        Theme.apply(self.app, self.win)

    def _strip(self, row, entries, variant):
        width, height = 8 * 34, 20
        canvas = tk.Canvas(row, width=width, height=height, highlightthickness=1, highlightbackground="#888888",
                           cursor="crosshair")
        canvas._cp_keep = True
        canvas.pack(side="left")
        stops = [parse_hex(e[1]) for e in entries]

        def color_at(x):
            pos = max(0.0, min(len(stops) - 1.0, x / float(width) * (len(stops) - 1)))
            i = min(int(pos), len(stops) - 2)
            t = pos - i
            a, b = stops[i], stops[i + 1]
            return tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3)), int(round(pos))

        for x in range(width):
            canvas.create_line(x, 0, x, height, fill=to_hex(color_at(x)[0]))

        def on_click(event):
            color, nearest = color_at(event.x)
            name, _hex, hue, var = entries[nearest]
            if variant == "neutral":
                self.apply(hue, var)
                return
            h, s, _v = colorsys.rgb_to_hsv(color[0] / 255.0, color[1] / 255.0, color[2] / 255.0)
            self.apply(int(round(h * 360)) if s > 0.05 else hue, variant if variant else var)

        canvas.bind("<Button-1>", on_click)

    def switch_ui(self):
        self.app.store.set("gradient_ui", self.ui_var.get())
        self.build()

    def apply(self, target_hue, variant):
        layer = self.target.layer()
        if layer is None:
            return
        key = self.app.key_color
        for i in self.target.indices():
            # Slots holding the key (void) color stay keyed, like the old keying-color guard
            if 0 <= i < PALETTE_SIZE and not self.app.is_key(layer.colors[i]):
                layer.colors[i] = avoid_key(gradient_color(layer.colors[i], target_hue, variant,
                                                           self.adjust_hue.get()), key)
        self.app.stats.add("gradients_applied")
        self.target.changed()

    def reset(self):
        self.adjust_hue.set(True)
        self.adjust_sat.set(False)
        self.adjust_val.set(False)
        self.layer.colors[:] = self.original
        self.target.changed()
