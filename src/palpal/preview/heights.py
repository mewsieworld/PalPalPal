"""3D height settings: how many beads tall each pixel stands in the 3D bead view.

Modes (Options > Document & 3D Settings > 3D height settings):
  flat   every pixel is one bead tall (the plain bead view)
  luma   per color, as a heightmap: lighter colors stand taller
  index  per color, set by hand: a slider for every palette index the image uses
  drawn  drawn by hand in the Artwork Tool (black = 1 bead, white = the max height)
Each image layer gets its own slab of max-height beads, so with one layer the heights read directly.
Back (Wall / Mirror): a wall stands the heights up off a flat back; a mirror copies them onto the back too,
so turning the view round shows the same relief reversed.
"""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.colors import to_hex
from ..ui.theme import Theme, center_on, hint

HEIGHT_MODES = [("flat", "Flat (one bead per pixel)"),
                ("luma", "Per color (heightmap: lighter colors stand taller)"),
                ("index", "Per color (sliders / set by hand)"),
                ("drawn", "Manually drawn using the pixel art tool")]
BACK_MODES = [("wall", "Wall (flat back)"), ("mirror", "Mirror (same heights on the back)")]
MAX_HEIGHT_LIMIT = 32


class HeightSettings:
    def __init__(self):
        self.mode = "flat"
        self.max = 8
        self.by_index = {}   # palette index -> beads, for the "index" mode
        self.back = "wall"   # "wall": flat back; "mirror": the heights again on the back

    def to_dict(self):
        return {"mode": self.mode, "max": self.max, "by_index": {str(k): v for k, v in self.by_index.items()},
                "back": self.back}

    @classmethod
    def from_dict(cls, d):
        s = cls()
        if d:
            s.mode = d.get("mode", "flat") if d.get("mode") in dict(HEIGHT_MODES) else "flat"
            s.max = max(1, min(MAX_HEIGHT_LIMIT, int(d.get("max", 8))))
            s.by_index = {int(k): int(v) for k, v in (d.get("by_index") or {}).items()}
            s.back = "mirror" if d.get("back") == "mirror" else "wall"
        return s

    def mirrored(self):
        return self.back == "mirror" and self.mode != "flat"

    def slab(self):
        """How many beads deep each image layer's slab is."""
        if self.mode == "flat":
            return 1
        return 2 * self.max - 1 if self.mirrored() else self.max

    def span(self, h):
        """The z offsets (within a layer's slab) a pixel h beads tall fills. A wall grows up from the back;
        a mirror grows both ways from the slab's middle, so it is 2h - 1 beads thick."""
        if self.mirrored():
            mid = self.max - 1
            return range(mid - (h - 1), mid + h)
        return range(h)

    def scale(self):
        """0-255 brightness -> 1..max beads."""
        return [1 + int(round(v * (self.max - 1) / 255.0)) for v in range(256)]


def height_image(app, il, t, size, transform=True, settings=None):
    """An "L" image (in the 3D view's orientation, unless transform=False) whose pixel values are bead
    heights, or None when flat. settings overrides the document's 3D height settings."""
    s = settings or app.heights
    if s.mode == "flat":
        return None
    canvas = Image.new("L", size, 0)
    frame = il.frame_at(t)
    if s.mode == "luma":
        canvas.paste(app.render_layer(il, t).convert("L"), (0, 0))
        lut = s.scale()
    elif s.mode == "index":
        canvas.paste(Image.frombytes("L", frame.image.size, frame.image.tobytes()), (0, 0))
        lut = [max(1, min(s.max, s.by_index.get(i, 1))) for i in range(256)]
    else:
        hm = getattr(il, "height_map", None)
        if hm is not None:
            canvas.paste(hm.resize(frame.image.size, Image.Resampling.NEAREST), (0, 0))
        lut = s.scale()
    out = canvas.point(lut)
    return app.transform(out) if transform else out


def height_settings_section(parent, app):
    """The 3D height settings block of Document & 3D Settings. Returns apply() for its Ok button."""
    box = tk.LabelFrame(parent, text="3D height settings")
    box.pack(fill="x", pady=(12, 0))
    mode = tk.StringVar(value=app.heights.mode)
    for value, label in HEIGHT_MODES:
        tk.Radiobutton(box, text=label, variable=mode, value=value).pack(anchor="w", padx=6)
    row = tk.Frame(box)
    row.pack(fill="x", padx=6, pady=(4, 2))
    tk.Label(row, text="Tallest:").pack(side="left")
    tallest = tk.IntVar(value=app.heights.max)
    tk.Spinbox(row, from_=1, to=MAX_HEIGHT_LIMIT, textvariable=tallest, width=4).pack(side="left", padx=(4, 2))
    tk.Label(row, text="beads").pack(side="left")
    back_row = tk.Frame(box)
    back_row.pack(fill="x", padx=6, pady=(2, 2))
    tk.Label(back_row, text="Back:").pack(side="left")
    back = tk.StringVar(value=app.heights.back)
    for value, label in BACK_MODES:
        tk.Radiobutton(back_row, text=label, variable=back, value=value).pack(side="left", padx=(4, 0))
    buttons = tk.Frame(box)
    buttons.pack(fill="x", padx=6, pady=(2, 6))

    def apply():
        try:
            app.heights.max = max(1, min(MAX_HEIGHT_LIMIT, int(tallest.get())))
        except (tk.TclError, ValueError):
            pass
        app.heights.mode = mode.get()
        app.heights.back = back.get()
        app.mark_dirty()
        app.request_redraw()

    def free_dialog():
        """Document & 3D Settings is modal; let go of it so the height editor can be used (it stays open)."""
        try:
            box.winfo_toplevel().grab_release()
        except tk.TclError:
            pass

    def bring_up(win):
        if win is not None and win.winfo_exists():
            win.lift()
            win.focus_force()

    def sliders():
        apply()
        mode.set("index")
        apply()
        free_dialog()
        editor = HeightSliders(app)
        bring_up(getattr(editor, "win", None))

    def draw():
        apply()
        mode.set("drawn")
        apply()
        free_dialog()
        tool = draw_heightmap(app)
        if tool is not None:
            tool.win.after(60, lambda: bring_up(tool.win))

    tk.Button(buttons, text="Set heights per color...", command=sliders).pack(side="left")
    tk.Button(buttons, text="Draw heightmap...", command=draw).pack(side="left", padx=(6, 0))
    hint(tk.Label(box, text="Shown in Options > 3D Layer View. Each image layer stacks on its own slab.",
                  fg="gray", font=("Arial", 8)), anchor="w", padx=6, pady=(0, 4))
    def reset():
        mode.set("flat")
        tallest.set(8)
        back.set("wall")

    apply.reset = reset
    return apply


class HeightSliders:
    """A slider for every color the selected image uses: how many beads tall that color stands."""

    def __init__(self, app):
        self.app = app
        il = app.target_image_layer()
        if il is None:
            messagebox.showinfo("3D heights", "Select an image layer first.")
            return
        colors = app.effective_colors(il, app.current_frame)
        used = sorted({i for f in il.frames for i in f.used_indices()} - app.key_indices(il.frame_at(0), colors))
        self.win = tk.Toplevel(app.master)
        self.win.title("3D heights per color - %s" % il.name)
        self.win.transient(app.master)
        holder = tk.Frame(self.win)
        holder.pack(fill="both", expand=True, padx=8, pady=8)
        canvas = tk.Canvas(holder, width=330, height=min(420, 30 * max(1, len(used))), highlightthickness=0)
        sb = ttk.Scrollbar(holder, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        inner = tk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        for i in used:
            row = tk.Frame(inner)
            row.pack(fill="x", pady=1)
            sw = tk.Label(row, text="  ", bg=to_hex(colors[i]), width=3, relief="solid", bd=1)
            sw._cp_keep = True
            sw.pack(side="left")
            tk.Label(row, text="#%d" % i, width=5).pack(side="left")
            var = tk.IntVar(value=app.heights.by_index.get(i, 1))
            tk.Scale(row, from_=1, to=app.heights.max, orient="horizontal", variable=var, length=220,
                     command=lambda v, i=i: self.set_height(i, int(float(v)))).pack(side="left")
        tk.Button(self.win, text="Done", width=10, command=self.win.destroy).pack(pady=(0, 8))
        Theme.apply(app, self.win)
        center_on(self.win, app.master)

    def set_height(self, index, value):
        self.app.heights.by_index[index] = value
        self.app.mark_dirty()
        self.app.request_redraw()


def draw_heightmap(app):
    """Open the Artwork Tool on the selected image's heightmap (black = 1 bead, white = tallest)."""
    il = app.target_image_layer()
    if il is None:
        messagebox.showinfo("3D heights", "Select an image layer first.")
        return
    from ..artwork import SpriteTool
    w, h = il.frames[0].image.size
    start = getattr(il, "height_map", None)
    if start is None:
        start = app.render_layer(il, 0).convert("L")   # start from the picture's brightness
    start = start.convert("RGBA")

    def done(frames):
        il.height_map = frames[0].convert("L")
        app.heights.mode = "drawn"
        app.mark_dirty()
        app.request_redraw()

    return SpriteTool(app.master, w, h, on_return=done, theme=lambda widget: Theme.apply(app, widget),
                      colors=Theme.colors(app), start_frames=[start])
