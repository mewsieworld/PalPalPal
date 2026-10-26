"""Img2img Palette Swap: the window layout, advanced options and the console."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.storage import export_dir
from ..core.colors import bg_fill, color_dist, hsl_to_rgb, luminosity, rgb_to_hsl, to_hex
from ..core.images import Frame, ImageLayer, convert_image, sample_unique_colors
from ..ui.theme import Theme, Tooltip, center_on
from ..preview.canvas import unxform_point, xform_image
from ..ui.dialogs import ChoiceDialog
from .mapper import MapperMixin
from .console import ConsoleLog


class AdjusterLayoutMixin:
    """Img2img Palette Swap: the window layout, advanced options and the console."""

    # ----- layout -----
    def build(self):
        top = tk.Frame(self.win)
        top.pack(fill="x", padx=10, pady=(8, 4))
        thumbs = tk.Frame(top)
        thumbs.pack(side="left")
        self.thumb_src = tk.Label(thumbs, text="Source", width=12, height=5, relief="groove", cursor="hand2")
        self.thumb_src.pack(side="left")
        self.thumb_ref = tk.Label(thumbs, text="Reference", width=12, height=5, relief="groove", cursor="hand2")
        self.thumb_ref.pack(side="left", padx=(6, 0))
        for label, kind, choose in ((self.thumb_src, "source", self.choose_source),
                                    (self.thumb_ref, "reference", self.choose_reference)):
            label.bind("<Button-1>", lambda e, c=choose: self._thumb_click(c))
            label.bind("<Double-Button-1>", lambda e, k=kind: self._thumb_view(k))
            label.bind("<Triple-Button-1>", lambda e: self._thumb_view("both"))
        Tooltip(self.thumb_src, "Click: choose another source image. Double-click: show it. Triple-click: both side "
                                "by side", self.app)
        Tooltip(self.thumb_ref, "Click: choose another color reference. Double-click: show it. Triple-click: both "
                                "side by side", self.app)

        go = tk.Button(top, text="▶", font=("Arial", 14, "bold"), bg="#2e7d32", fg="white", width=3,
                       activebackground="#388e3c", activeforeground="white", command=self.generate_result)
        go._cp_keep = True
        go.pack(side="right")
        Tooltip(go, "Perform recolor and generate the result", self.app)
        reset = tk.Button(top, text="✖", font=("Arial", 14, "bold"), bg="#c62828", fg="white", width=3,
                          activebackground="#d32f2f", activeforeground="white", command=self.reset_mapping)
        reset._cp_keep = True
        reset.pack(side="right", padx=(0, 6))
        Tooltip(reset, "Reset live preview and mapping", self.app)
        tools = tk.Frame(top)
        tools.pack(side="top", pady=(6, 0))
        buttons = tk.Frame(tools)
        buttons.pack()
        brush = tk.Button(buttons, text="🖌", font=("Arial", 14), width=3, command=self.open_mapper)
        brush.pack(side="left")
        Tooltip(brush, "Palette to Palette Mapper", self.app)
        tk.Button(buttons, text="Flip", command=lambda: self.view_transform(flip=True)).pack(side="left", padx=(6, 0),
                                                                                            fill="y")
        tk.Button(buttons, text="Rotate", command=lambda: self.view_transform(rotate=True)).pack(side="left",
                                                                                                padx=(4, 0), fill="y")
        # Only while both pictures are on screen: flip / rotate the clicked one, or both together
        self.per_image = tk.BooleanVar(value=True)
        self.per_image_box = tk.Checkbutton(tools, text="per image", variable=self.per_image, font=("Arial", 8))

        # The result canvas is the main thing on screen
        stage = tk.Frame(self.win, relief="solid", bd=1)
        stage.pack(fill="both", expand=True, padx=10, pady=4)
        self.canvas = tk.Canvas(stage, highlightthickness=0)
        self.canvas._cp_preview = True
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.schedule())
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.zoom = 1.0
        self.canvas.bind("<MouseWheel>", self.on_wheel)
        self.canvas.bind("<Button-3>", lambda e: self.canvas.scan_mark(e.x, e.y))
        self.canvas.bind("<B3-Motion>", lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))
        # Eyedropper sits in the bottom-left corner, clear of the picture
        self.eye_btn = tk.Button(stage, text="🎨", font=("Arial", 12), command=self.toggle_eyedropper)
        self.eye_btn.place(relx=0.0, rely=1.0, x=6, y=-6, anchor="sw")
        Tooltip(self.eye_btn, "Eyedropper: click the picture to pick a source color", self.app)
        self.hover = None

        options = tk.LabelFrame(self.win, text="Filters & Options", font=("Arial", 10, "bold"))
        options.pack(fill="x", padx=10, pady=(4, 0))
        self.tol_var = tk.IntVar(value=0)
        self._slider(options, "Color Swap Tolerance", self.tol_var, 0, 64, self.on_tolerance)
        self.filter_vars = {}
        for key, label, lo, hi in (("hue", "Global Hue Filter", 0, 360), ("saturation", "Global Saturation Filter", 0, 200),
                                   ("brightness", "Global Brightness Filter", 0, 200),
                                   ("contrast", "Global Contrast Filter", 0, 200)):
            var = tk.IntVar(value=self.filters[key])
            self.filter_vars[key] = var
            self._slider(options, label, var, lo, hi, lambda k=key: self.on_filter(k))

        self.adv_var = tk.BooleanVar(value=bool(self.app.store.get("i2i_advanced")))
        tk.Checkbutton(self.win, text="Advanced Options", variable=self.adv_var,
                       command=self.toggle_advanced).pack(anchor="w", padx=10)
        self.advanced = tk.Frame(self.win)
        self._build_advanced(self.advanced)
        self.toggle_advanced(save=False)

    def _slider(self, parent, label, var, lo, hi, command):
        row = tk.Frame(parent)
        row.pack(fill="x", padx=6, pady=1)
        tk.Label(row, text=label, width=22, anchor="w", font=("Arial", 8)).pack(side="left")
        e = tk.Entry(row, textvariable=var, width=5, font=("Arial", 8), justify="right")
        e.pack(side="left", padx=(0, 4))
        e.bind("<Return>", lambda ev: command())
        tk.Scale(row, from_=lo, to=hi, orient="horizontal", variable=var, showvalue=False, sliderrelief="flat",
                 sliderlength=14, width=9, bd=0, highlightthickness=0,
                 command=lambda *_: command()).pack(side="left", fill="x", expand=True)

    def _build_advanced(self, frame):
        cols = tk.Frame(frame)
        cols.pack(fill="x", padx=10)
        c = tk.LabelFrame(cols, text="Swaps & Refinement", font=("Arial", 9, "bold"))
        c.pack(side="left", fill="both", expand=True, padx=(0, 4))
        row = tk.Frame(c)
        row.pack(fill="x", padx=4, pady=2)
        tk.Button(row, text="Autoswap (Luminosity)", command=lambda: self.autoswap(None)).pack(side="left", fill="x",
                                                                                              expand=True)
        self.autoswap_sel_btn = tk.Button(row, text="Autoswap to Selected", state="disabled",
                                          command=lambda: self.autoswap(self.selected_target))
        self.autoswap_sel_btn.pack(side="left", fill="x", expand=True, padx=(4, 0))
        self.refine_lbl = tk.Label(c, text="Selected source index: ---", font=("Arial", 8))
        self.refine_lbl.pack(anchor="w", padx=4)
        self.refine_var = tk.IntVar(value=0)
        self._slider(c, "Index Hue Shift", self.refine_var, -180, 180, lambda: None)
        tk.Button(c, text="Apply Refinement", command=self.apply_refinement).pack(fill="x", padx=4, pady=(0, 4))

        d = tk.LabelFrame(cols, text="Creative Tools & Advanced Indexing", font=("Arial", 9, "bold"))
        d.pack(side="left", fill="both", expand=True, padx=(4, 0))
        self.shift_var = tk.IntVar(value=0)
        self._slider(d, "Selected Target Index Shift", self.shift_var, -5, 5, self.on_target_shift)
        self.grad_vars = [tk.StringVar(value="0") for _ in range(4)]
        self.range_vars = [tk.StringVar(value="0") for _ in range(3)]
        for label, vars_, button, command in (
                ("Gradient: source", self.grad_vars[:2], None, None),
                ("Gradient: target path", self.grad_vars[2:], "Apply Gradient", self.run_gradient),
                ("Remap: source range", self.range_vars[:2], None, None),
                ("Remap: target start", self.range_vars[2:], "Apply Index Mapping", self.run_index_shift)):
            row = tk.Frame(d)
            row.pack(fill="x", padx=4, pady=1)
            tk.Label(row, text=label, width=18, anchor="w", font=("Arial", 8)).pack(side="left")
            for n, var in enumerate(vars_):
                if n:
                    tk.Label(row, text="to", font=("Arial", 8)).pack(side="left")
                tk.Entry(row, textvariable=var, width=4).pack(side="left", padx=2)
            if button:
                tk.Button(row, text=button, font=("Arial", 8), command=command).pack(side="right")

        self.console_var = tk.BooleanVar(value=bool(self.app.store.get("i2i_console")))
        tk.Checkbutton(frame, text="Console", variable=self.console_var, command=self.toggle_console).pack(anchor="w",
                                                                                                         padx=10)
        self.console = ConsoleLog(self.app, frame)
        self.toggle_console(save=False)

    def toggle_advanced(self, save=True):
        if save:
            self.app.store.set("i2i_advanced", self.adv_var.get())
        if self.adv_var.get():
            self.advanced.pack(fill="x", pady=(0, 8))
        else:
            self.advanced.pack_forget()

    def toggle_console(self, save=True):
        if save:
            self.app.store.set("i2i_console", self.console_var.get())
        if self.console_var.get():
            self.console.frame.pack(fill="both", expand=True, padx=10, pady=(0, 4))
        else:
            self.console.frame.pack_forget()

    def log(self, message):
        self.console.log(message)

    # ----- loading -----
    def show_prompt(self):
        if self.source is None:
            self.prompt("Choose a Source Image", self.choose_source, "Use the current frame", self.use_current_frame)
        elif self.reference is None:
            self.prompt("Choose a color reference file.", self.choose_reference)

    def prompt(self, text, command, alt_text=None, alt_command=None):
        c = self.canvas
        c.delete("all")
        cw, ch = max(1, c.winfo_width()), max(1, c.winfo_height())
        if cw < 50:
            cw, ch = 860, 420
        c.create_text(cw // 2, ch // 2 - 20, text=text, font=("Arial", 15, "bold"), fill="#888888")
        b = tk.Button(c, text="Choose file...", command=command)
        c.create_window(cw // 2 - (70 if alt_text else 0), ch // 2 + 20, window=b)
        if alt_text:
            c.create_window(cw // 2 + 80, ch // 2 + 20, window=tk.Button(c, text=alt_text, command=alt_command))
