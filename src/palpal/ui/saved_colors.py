"""The Saved Colors panel (shared by the main window and the editors)."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.storage import export_dir
from ..core.colors import parse_color_any
from ..core.palettes import read_palette, write_palette
from .theme import Tooltip
from .widgets import draw_swatch, make_swatch


class SavedColorsPanel:
    """Saved Colors box: vertical scrollbar only, Load/Save/Clear icons, +/- rows."""

    def __init__(self, app, parent, get_color, apply_color, size=24, cols=10, visible_rows=2, on_after_dialog=None):
        self.app, self.get_color, self.apply_color = app, get_color, apply_color
        self.size, self.cols, self.visible_rows = size, cols, visible_rows
        self.on_after_dialog = on_after_dialog
        self.frame = tk.Frame(parent)

        top = tk.Frame(self.frame)
        top.pack(fill="x", padx=2, pady=2)
        load = tk.Button(top, text="📂", width=3, command=self.load)
        save = tk.Button(top, text="💾", width=3, command=self.save)
        clear = tk.Button(top, text="✖", width=3, command=self.clear)
        for b in (load, save, clear):
            b.pack(side="left", padx=(0, 3))
        Tooltip(load, "Load colors", app)
        Tooltip(save, "Save colors", app)
        Tooltip(clear, "Clear colors", app)
        minus = tk.Button(top, text="−", width=2, command=lambda: self.change_rows(-1))
        plus = tk.Button(top, text="+", width=2, command=lambda: self.change_rows(1))
        minus.pack(side="left", padx=(8, 1))
        plus.pack(side="left")
        Tooltip(minus, "Remove a row of slots", app)
        Tooltip(plus, "Add a row of slots", app)
        self.mouse_btn = tk.Button(top, text="R", width=2, font=("Arial", 9, "bold"), command=self.toggle_mouse)
        self.mouse_btn.pack(side="right")
        Tooltip(self.mouse_btn, "Swap which mouse button saves and which applies", app)

        self.help = tk.Label(self.frame, anchor="w", justify="left", font=("Arial", 8))
        self.help.pack(fill="x", padx=6)

        body = tk.Frame(self.frame)
        body.pack(padx=2, pady=(0, 2))  # no fill: the grid stays centred in the box
        self.canvas = tk.Canvas(body, highlightthickness=0, bd=0,
                                width=cols * (size + 2), height=visible_rows * (size + 2))
        self.scroll = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.pack(side="left")
        self.scroll.pack(side="left", fill="y")
        self.grid = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.grid, anchor="nw")
        self.grid.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<MouseWheel>", self._wheel)
        self.slots = []
        app.saved_panels.append(self)
        self.rebuild()

    def pack(self, **kw):
        self.frame.pack(**kw)
        return self

    def _wheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def rebuild(self):
        for w in self.slots:
            w.destroy()
        self.slots = []
        for i in range(len(self.app.saved_colors)):
            sw = make_swatch(self.grid, self.size)
            sw.grid(row=i // self.cols, column=i % self.cols, padx=1, pady=1)
            sw.bind("<Button-1>", lambda e, j=i: self.click(j, right=False))
            sw.bind("<Button-3>", lambda e, j=i: self.click(j, right=True))
            sw.bind("<MouseWheel>", self._wheel)
            self.slots.append(sw)
        self.refresh()

    def refresh(self):
        if not self.frame.winfo_exists():
            return
        if len(self.slots) != len(self.app.saved_colors):
            self.rebuild()
            return
        for sw, color in zip(self.slots, self.app.saved_colors):
            draw_swatch(self.app, sw, color)
        right = self.app.use_right_click
        self.mouse_btn.configure(text="R" if right else "L", relief="sunken" if right else "raised")
        if right:
            self.help.configure(text="Left click to apply color | Right click to save color")
        else:
            self.help.configure(text="Left click to save color | Right click to apply color")

    def click(self, slot, right):
        save = right if self.app.use_right_click else not right
        if save:
            color = self.get_color()
            if color is not None:
                self.app.saved_colors[slot] = tuple(color)
                self.app.stats.add("colors_saved")
                self.app.saved_colors_changed()
        else:
            color = self.app.saved_colors[slot]
            if color is not None:
                self.apply_color(color)

    def toggle_mouse(self):
        self.app.use_right_click = not self.app.use_right_click
        self.app.store.set("use_right_click", self.app.use_right_click)
        self.app.saved_colors_changed()

    def change_rows(self, delta):
        colors = self.app.saved_colors
        if delta > 0:
            room = PALETTE_SIZE - len(colors)
            colors.extend([None] * min(self.cols, room))
        else:
            target = max(DEFAULT_SAVED_SLOTS, len(colors) - self.cols)
            del colors[target:]
        self.app.saved_colors_changed()

    def _after_dialog(self):
        if self.on_after_dialog:
            self.on_after_dialog()

    def load(self):
        path = filedialog.askopenfilename(title="Load Colors", filetypes=SAVED_COLOR_TYPES + PALETTE_TYPES[1:],
                                          initialdir=export_dir("colors"))
        self._after_dialog()
        if not path:
            return
        try:
            if path.lower().endswith(".json"):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    data = data.get("colors", [])
                colors = [parse_color_any(c) for c in data]
            else:
                colors = read_palette(path)
        except Exception as exc:
            messagebox.showerror("Load Colors", "Could not read that file:\n%s" % exc)
            return
        colors = colors[:PALETTE_SIZE]
        size = max(DEFAULT_SAVED_SLOTS, len(colors))
        size = min(PALETTE_SIZE, -(-size // 10) * 10)
        self.app.saved_colors[:] = colors + [None] * (size - len(colors))
        self.app.saved_colors_changed()

    def save(self):
        path = filedialog.asksaveasfilename(title="Save Colors", defaultextension=".json",
                                            filetypes=SAVED_COLOR_TYPES, initialdir=export_dir("colors"))
        self._after_dialog()
        if not path:
            return
        try:
            if path.lower().endswith(".json"):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump([list(c) if c else None for c in self.app.saved_colors], f)
            else:
                write_palette(path, [c for c in self.app.saved_colors if c], self.app.store.get("pal_style"))
        except OSError as exc:
            messagebox.showerror("Save Colors", "Could not save:\n%s" % exc)

    def clear(self):
        self.app.saved_colors[:] = [None] * len(self.app.saved_colors)
        self.app.saved_colors_changed()


# ---------------------------------------------------------------------------
# The shared one-line color picker
# ---------------------------------------------------------------------------
