"""Shared widgets: swatches, HSV rows, the picker row, Saved Colors and the Sort button."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.storage import export_dir
from ..core.colors import parse_color_any, rgb_to_hsv_int, to_hex
from ..core.palettes import read_palette, write_palette
from .theme import Theme, Tooltip


# ---------------------------------------------------------------------------
# Small shared widgets
# ---------------------------------------------------------------------------

def make_swatch(parent, size, **kw):
    canvas = tk.Canvas(parent, width=size, height=size, highlightthickness=0, bd=0, **kw)
    canvas._cp_keep = True
    canvas._cp_size = size
    return canvas


def draw_swatch(app, canvas, color, selected=False):
    size = canvas._cp_size
    dark = app.dark_mode
    canvas.configure(bg="#1E1E1E" if dark else "#F0F0F0")
    canvas.delete("all")
    if color is None:
        fill, outline = ("#1E1E1E", "#444444") if dark else ("white", "#888888")
    else:
        fill, outline = to_hex(color), ("#888888" if dark else "black")
    canvas.create_rectangle(1, 1, size - 1, size - 1, fill=fill, outline=outline)
    if selected:
        canvas.create_rectangle(1, 1, size - 1, size - 1, outline="red", width=2)


def swatch_grid(parent, indices, size, cols, on_left, on_right=None, height=None):
    """A vertically scrolling grid of palette swatches. Returns {palette_index: swatch canvas}."""
    sb = ttk.Scrollbar(parent, orient="vertical")
    sb.pack(side="right", fill="y")
    canvas = tk.Canvas(parent, highlightthickness=0, yscrollcommand=sb.set, **({"height": height} if height else {}))
    canvas.pack(side="left", fill="both", expand=True)
    sb.configure(command=canvas.yview)
    inner = tk.Frame(canvas)
    canvas.create_window((0, 0), window=inner, anchor="nw")
    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    def wheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    canvas.bind("<MouseWheel>", wheel)
    swatches = {}
    for pos, idx in enumerate(indices):
        sw = make_swatch(inner, size)
        sw.grid(row=pos // cols, column=pos % cols, padx=2, pady=2)
        sw.bind("<Button-1>", lambda e, i=idx: on_left(i, e))
        if on_right:
            sw.bind("<Button-3>", lambda e, i=idx: on_right(i, e))
        sw.bind("<MouseWheel>", wheel)
        swatches[idx] = sw
    return swatches


def relay_swatches(holder, indices, size, cols, on_click):
    """Rebuild just a swatch grid inside its holder (so an open Sort list survives); None if it's gone."""
    if holder is None or not holder.winfo_exists():
        return None
    for w in holder.winfo_children():
        w.destroy()
    return swatch_grid(holder, indices, size, cols, on_click)


def hsv_row(parent, row, label, var, lo, hi, on_change, label_width=4):
    """Label [value] [slider] in one row, the order the spec asks for."""
    tk.Label(parent, text=label, width=label_width, anchor="w", font=("Arial", 8)).grid(row=row, column=0, sticky="w")
    entry = tk.Entry(parent, textvariable=var, width=5, font=("Arial", 8), justify="right")
    entry.grid(row=row, column=1, sticky="w", padx=(2, 4))
    scale = tk.Scale(parent, from_=lo, to=hi, orient="horizontal", variable=var, showvalue=False,
                     sliderrelief="flat", sliderlength=14, width=9, bd=0, highlightthickness=0,
                     command=lambda *_: on_change())
    scale.grid(row=row, column=2, sticky="we", pady=1)
    parent.grid_columnconfigure(2, weight=1)

    def commit(_event=None):
        try:
            value = int(float(var.get()))
        except (tk.TclError, ValueError):
            value = 0
        var.set(max(lo, min(hi, value)))
        on_change()

    entry.bind("<Return>", commit)
    entry.bind("<FocusOut>", commit)
    return scale


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

def picker_row(parent, owner):
    """Index: [ ] [Go] Hex #: [ ] [🎨 Pick] [Apply, only while picking] ........ [🌈]

    owner needs idx_var, hex_var, goto_index(), apply_hex_entry(), toggle_pick(), open_gradient().
    """
    row = tk.Frame(parent)
    tk.Label(row, text="Index:").pack(side="left")
    idx = tk.Entry(row, textvariable=owner.idx_var, width=4)
    idx.pack(side="left", padx=(2, 2))
    idx.bind("<Return>", lambda e: owner.goto_index())
    tk.Button(row, text="Go", command=owner.goto_index).pack(side="left", padx=(0, 8))
    tk.Label(row, text="Hex #:").pack(side="left")
    hx = tk.Entry(row, textvariable=owner.hex_var, width=8)
    hx.pack(side="left", padx=(2, 4))
    hx.bind("<Return>", lambda e: owner.apply_hex_entry())
    owner.pick_btn = tk.Button(row, text="🎨 Exit" if owner.picking else "🎨 Pick", command=owner.toggle_pick)
    owner.pick_btn.pack(side="left")
    owner.apply_btn = tk.Button(row, text="Apply", command=owner.apply_hex_entry)
    if owner.picking:
        owner.apply_btn.pack(side="left", padx=(4, 0))
    grad = tk.Button(row, text="🌈", command=owner.open_gradient, bg="#FF4081", fg="white",
                     activebackground="#E91E63", font=("Arial", 9, "bold"), width=4)
    grad._cp_keep = True
    grad.pack(side="right")
    Tooltip(grad, "Gradient", owner.app)
    return row


def set_pick_mode(owner, on):
    """Shared Pick/Exit behaviour: Apply only shows while Pick says Exit."""
    owner.picking = on
    try:
        owner.pick_btn.configure(text="🎨 Exit" if on else "🎨 Pick")
        if on:
            owner.apply_btn.pack(side="left", padx=(4, 0), after=owner.pick_btn)
        else:
            owner.apply_btn.pack_forget()
    except (tk.TclError, AttributeError):
        pass


# ---------------------------------------------------------------------------
# Active Colors editor (Small Preview bar, and the whole view in No Preview)
# ---------------------------------------------------------------------------

ARROW_UP, ARROW_DOWN = "\u25b2", "\u25bc"  # ▲ ▼


def sort_indices(app, indices, palette):
    """Order palette indexes by the Sort setting: by index, or by the hue / saturation / value of their color."""
    key, ascending = app.store.get("active_sort") or ("index", True)
    if key != "index" and palette is not None:
        part = {"hue": 0, "sat": 1, "val": 2}[key]
        indices = sorted(indices, key=lambda i: (rgb_to_hsv_int(palette.colors[i])[part], i))
    else:
        indices = sorted(indices)
    return indices if ascending else list(reversed(indices))


def is_custom_sort(app):
    return tuple(app.store.get("active_sort") or ("index", True)) != ("index", True)


class SortButton:
    """'Sort: [Index]' button. Its list stays open while you switch keys and directions; click away to close."""

    CHOICES = [("index", "Default (Index)", "Index"), ("hue", "Hue", "Hue"), ("sat", "Saturation", "Sat"),
               ("val", "Value", "Val")]

    def __init__(self, app, parent, on_change):
        self.app, self.on_change, self.popup = app, on_change, None
        self.button = tk.Button(parent, command=self.toggle_popup, font=("Arial", 8))
        self.refresh_label()

    def pack(self, **kw):
        self.button.pack(**kw)
        return self

    def current(self):
        key, ascending = self.app.store.get("active_sort") or ("index", True)
        return key, bool(ascending)

    def refresh_label(self):
        key = self.current()[0]
        short = next(s for k, _l, s in self.CHOICES if k == key)
        key, ascending = self.current()
        self.button.configure(text="Sort: %s %s" % (short, ARROW_UP if ascending else ARROW_DOWN))

    def toggle_popup(self):
        if self.popup is not None:
            self.close()
            return
        c = Theme.colors(self.app)
        self.popup = tk.Toplevel(self.app.master)
        self.popup.wm_overrideredirect(True)
        self.popup.configure(bg="#888888")
        self.popup.geometry("+%d+%d" % (self.button.winfo_rootx(),
                                        self.button.winfo_rooty() + self.button.winfo_height()))
        self.rows = []
        for key, label, _short in self.CHOICES:
            row = tk.Label(self.popup, anchor="w", padx=10, pady=3, width=18, cursor="hand2",
                           bg=c["input"], fg=c["fg"])
            row.pack(fill="x", padx=1, pady=(1, 0))
            row.bind("<Button-1>", lambda e, k=key: self.choose(k))
            row.bind("<Enter>", lambda e, w=row: w.configure(bg=c["hover"]))
            row.bind("<Leave>", lambda e, w=row: w.configure(bg=c["input"]))
            self.rows.append((key, label, row))
        tk.Frame(self.popup, height=1, bg="#888888").pack(fill="x")
        self.relabel_rows()
        # Close on any click outside the list (or on the Sort button itself)
        self._click_id = self.app.master.bind_all("<Button-1>", self._outside_click, add="+")
        self.popup.bind("<Escape>", lambda e: self.close())
        self.popup.focus_set()

    def relabel_rows(self):
        key, ascending = self.current()
        for k, label, row in self.rows:
            row.configure(text=label + ((" " + (ARROW_UP if ascending else ARROW_DOWN)) if k == key else ""),
                          font=("Arial", 9, "bold" if k == key else "normal"))

    def choose(self, key):
        current, ascending = self.current()
        # Picking the active choice again flips its direction; a new choice starts ascending
        self.app.store.set("active_sort", [key, (not ascending) if key == current else True])
        self.relabel_rows()
        self.refresh_label()
        self.on_change()

    def _outside_click(self, event):
        if self.popup is None:
            return
        widget = event.widget
        try:
            inside = str(widget).startswith(str(self.popup)) or widget is self.button
        except tk.TclError:
            inside = False
        if not inside:
            self.close()

    def close(self):
        if self.popup is not None:
            self.popup.destroy()
            self.popup = None
            try:
                self.app.master.unbind_all("<Button-1>")
            except tk.TclError:
                pass
