"""Mass Frame Editor: the window layout."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..ui.widgets import swatch_grid
from ..ui.theme import hint
from .constants import FRAME_EXPORT_FORMATS


class MassEditorLayoutMixin:
    """Mass Frame Editor: the window layout."""

    # ----- layout -----
    def build(self):
        top = tk.Frame(self.win)
        top.pack(fill="x", padx=10, pady=(8, 4))
        name = self.layer.name if self.layer else "-"
        tk.Label(top, text="Mass Frame Editor", font=("Arial", 13, "bold")).pack(side="left")
        tk.Label(top, text="   editing %s through %s: every change reaches every frame that uses the index"
                 % (name, self.palette.name if self.palette else "-"), fg="gray").pack(side="left")
        apply = tk.Button(top, text="Apply", width=10, bg="#2e7d32", fg="white", activebackground="#388e3c",
                          activeforeground="white", command=self.apply_changes)
        apply._cp_keep = True
        apply.pack(side="right")
        self.applied_lbl = tk.Label(top, text="", fg="gray")
        self.applied_lbl.pack(side="right", padx=(0, 8))

        # Close (bottom left) cancels whatever wasn't applied; packed first so it keeps its place at the bottom
        bottom = tk.Frame(self.win)
        bottom.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        tk.Button(bottom, text="Close", width=10, command=self.close).pack(side="left")
        hint(tk.Label(bottom, text="Changes show live; Apply keeps them, Close throws away anything not applied.",
                      fg="gray", font=("Arial", 8)), side="left", padx=(10, 0))

        body = tk.Frame(self.win)
        body.pack(fill="both", expand=True, padx=10)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_columnconfigure(2, weight=2)
        body.grid_rowconfigure(0, weight=1)

        # Step 0: frames
        step0 = tk.LabelFrame(body, text="Step 0: Frames", font=("Arial", 10, "bold"))
        step0.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.canvas = tk.Canvas(step0, highlightthickness=0, cursor="fleur")
        self.canvas._cp_preview = True
        self.canvas.pack(fill="both", expand=True, padx=4, pady=4)
        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Motion>", self.on_move)
        self.canvas.bind("<MouseWheel>", lambda e: self.change_zoom(1 if e.delta > 0 else -1))
        controls = tk.Frame(step0)
        controls.pack(fill="x", padx=4, pady=(0, 4))
        tk.Label(controls, text="Zoom").pack(side="left")
        tk.Button(controls, text="−", width=2, command=lambda: self.change_zoom(-1)).pack(side="left", padx=(4, 0))
        self.zoom_lbl = tk.Label(controls, width=5)
        self.zoom_lbl.pack(side="left")
        tk.Button(controls, text="+", width=2, command=lambda: self.change_zoom(1)).pack(side="left")
        tk.Button(controls, text="◀", width=3, command=lambda: self.change_frame(-1)).pack(side="left", padx=(12, 2))
        self.frame_lbl = tk.Label(controls, width=7, font=("Arial", 9, "bold"))
        self.frame_lbl.pack(side="left")
        tk.Button(controls, text="▶", width=3, command=lambda: self.change_frame(1)).pack(side="left", padx=2)
        tk.Button(controls, text="Reset Position (X)", command=self.reset_position).pack(side="left", padx=(12, 0))
        self.eye_btn = tk.Button(controls, text="🎨 Eyedropper", command=self.toggle_eyedropper)
        self.eye_btn.pack(side="right")
        readout = tk.Frame(step0)
        readout.pack(fill="x", padx=4, pady=(0, 4))
        self.read_lbl = tk.Label(readout, text="Color read: --", font=("Consolas", 9))
        self.read_lbl.pack(side="left")
        self.live_lbl = tk.Label(readout, text="Live index: --", font=("Consolas", 9))
        self.live_lbl.pack(side="left", padx=(16, 0))

        # Step 1: source indexes
        step1 = tk.LabelFrame(body, text="Step 1: Source Indexes", font=("Arial", 10, "bold"))
        step1.grid(row=0, column=1, sticky="nsew", padx=6)
        holder = tk.Frame(step1)
        holder.pack(fill="both", expand=True, padx=4, pady=4)
        self.indices = self.app.editable_indices(self.palette) if self.palette else []
        self.boxes = swatch_grid(holder, self.indices, 22, 10, self.on_box_click)
        info = tk.Frame(step1)
        info.pack(fill="x", padx=4)
        self.confirmed_lbl = tk.Label(info, text="Confirmed index: --", font=("Arial", 9, "bold"))
        self.confirmed_lbl.pack(anchor="w")
        self.original_lbl = tk.Label(info, text="Original color: --", font=("Consolas", 9))
        self.original_lbl.pack(anchor="w")
        self.multi_btn = tk.Button(step1, text="Enable Multiselect", command=self.toggle_multi)
        self.multi_btn.pack(fill="x", padx=4, pady=(6, 2))
        self.multi_lbl = tk.Label(step1, text="Shift+click picks a range while Multiselect is on", fg="gray",
                                  font=("Arial", 8))
        self.multi_lbl.pack(pady=(0, 4))

        # Target color, mappings, export
        right = tk.Frame(body)
        right.grid(row=0, column=2, sticky="nsew", padx=(6, 0))
        target = tk.LabelFrame(right, text="Target Color (live)", font=("Arial", 10, "bold"))
        target.pack(fill="x")
        self.h_var, self.s_var, self.l_var = tk.DoubleVar(value=0), tk.DoubleVar(value=0), tk.DoubleVar(value=0)
        sliders = tk.Frame(target)
        sliders.pack(fill="x", padx=4, pady=4)
        for row, (label, var, hi) in enumerate((("Hue", self.h_var, 360), ("Sat", self.s_var, 100),
                                                 ("Light", self.l_var, 100))):
            tk.Label(sliders, text=label, width=5, anchor="w", font=("Arial", 8)).grid(row=row, column=0, sticky="w")
            value = tk.Label(sliders, width=6, font=("Consolas", 8))
            value.grid(row=row, column=1)
            setattr(self, "%s_value" % label.lower(), value)
            tk.Scale(sliders, from_=0, to=hi, resolution=0.1 if hi == 100 else 1, orient="horizontal", variable=var,
                     showvalue=False, sliderrelief="flat", sliderlength=14, width=9, bd=0, highlightthickness=0,
                     command=lambda *_: self.on_hsl()).grid(row=row, column=2, sticky="we")
        sliders.grid_columnconfigure(2, weight=1)
        hexrow = tk.Frame(target)
        hexrow.pack(fill="x", padx=4, pady=(0, 6))
        self.target_swatch = tk.Button(hexrow, width=3, command=self.choose_color)
        self.target_swatch._cp_keep = True
        self.target_swatch.pack(side="left")
        tk.Label(hexrow, text="Hex #:").pack(side="left", padx=(6, 2))
        self.hex_var = tk.StringVar()
        he = tk.Entry(hexrow, textvariable=self.hex_var, width=8)
        he.pack(side="left")
        he.bind("<Return>", lambda e: self.on_hex())
        tk.Button(hexrow, text="Apply", command=self.on_hex).pack(side="left", padx=(4, 0))

        maps = tk.LabelFrame(right, text="Mappings", font=("Arial", 10, "bold"))
        maps.pack(fill="both", expand=True, pady=(8, 0))
        self.map_text = tk.Text(maps, height=8, width=24, font=("Consolas", 9), undo=True)
        self.map_text.pack(fill="both", expand=True, padx=4, pady=4)
        # Typing "index=#RRGGBB" lines here recolors those indexes live
        self.map_text.bind("<KeyRelease>", lambda e: self.mappings_edited())
        row = tk.Frame(maps)
        row.pack(fill="x", padx=4, pady=(0, 4))
        tk.Button(row, text="Copy", command=self.copy_mappings).pack(side="left")
        tk.Button(row, text="Paste", command=self.paste_mappings).pack(side="left", padx=(4, 0))
        tk.Button(row, text="Reset", command=self.reset_all).pack(side="right")

        export = tk.LabelFrame(right, text="Export Frames", font=("Arial", 10, "bold"))
        export.pack(fill="x", pady=(8, 0))
        row = tk.Frame(export)
        row.pack(fill="x", padx=4, pady=4)
        self.export_var = tk.StringVar(value=self.app.store.get("mass_export_format") or FRAME_EXPORT_FORMATS[0][0])
        ttk.Combobox(row, textvariable=self.export_var, values=[label for label, _fmt in FRAME_EXPORT_FORMATS],
                     state="readonly", width=22).pack(side="left", fill="x", expand=True)
        tk.Button(row, text="Export", width=8,
                  command=lambda: self.export_frames(dict(FRAME_EXPORT_FORMATS)[self.export_var.get()])).pack(
            side="left", padx=(4, 0))

        strip_box = tk.LabelFrame(self.win, text="Frame Strip", font=("Arial", 10, "bold"))
        strip_box.pack(fill="x", padx=10, pady=(6, 6))
        row = tk.Frame(strip_box)
        row.pack(fill="x", padx=4, pady=(2, 0))
        tk.Label(row, text="Frames to show:").pack(side="left")
        self.strip_count = tk.StringVar(value="3")
        spin = tk.Spinbox(row, from_=1, to=32, textvariable=self.strip_count, width=4, command=self.draw_strip)
        spin.pack(side="left", padx=4)
        spin.bind("<Return>", lambda e: self.draw_strip())
        self.strip = tk.Canvas(strip_box, height=112, highlightthickness=0)
        self.strip._cp_preview = True
        self.strip.pack(fill="x", padx=4, pady=4)
        self.strip.bind("<Button-1>", self.on_strip_click)
