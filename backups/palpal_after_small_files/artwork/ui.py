"""Artwork Tool: window layout and controls."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .look import TOOL_GROUP_COLORS
from .model import hex_to_rgba, rgba_hex
from .controls import ControlsMixin


class UiMixin(ControlsMixin):
    """Window layout, tool buttons, brush and colour controls, keyboard shortcuts."""

    # ----- layout -----
    def build(self):
        menubar = tk.Menu(self.win)
        file_menu = tk.Menu(menubar, tearoff=0)
        imp = tk.Menu(file_menu, tearoff=0)
        imp.add_command(label="Image as Layer (crop)...", command=self.import_reference)
        imp.add_command(label="Sprite Sheet...", command=self.import_sprite_sheet)
        imp.add_command(label="Bulk Images as Frames...", command=self.bulk_import)
        imp.add_command(label="Project (JSON)...", command=self.load_project)
        imp.add_command(label="Palette...", command=self.import_palette)
        imp.add_command(label="Custom Brush...", command=self.load_custom_brush)
        file_menu.add_cascade(label="Import", menu=imp)
        file_menu.add_command(label="Save and Return", command=self.save_and_return)
        file_menu.add_separator()
        file_menu.add_command(label="Close without returning", command=self.close)
        menubar.add_cascade(label="File", menu=file_menu)
        # Options, Export and Shortcuts are their own menus next to File
        opts = tk.Menu(menubar, tearoff=0)
        opts.add_command(label="Size Options", command=self.open_size_options)
        opts.add_command(label="Display Options", command=self.open_display_options)
        opts.add_command(label="Other Options", command=self.open_other_options)
        menubar.add_cascade(label="Options", menu=opts)
        exp = tk.Menu(menubar, tearoff=0)
        exp.add_command(label="Sprite Sheet (PNG)", command=self.export_sheet)
        exp.add_command(label="Sprite Atlas (PNG+JSON)", command=self.export_atlas)
        exp.add_command(label="Background Frames (BMP)", command=self.export_bmp_frames)
        exp.add_command(label="Transparent Animation (GIF)", command=self.export_gif)
        exp.add_command(label="🚀 Quick Export for Fuse Tool", command=self.quick_export_fuse)
        exp.add_separator()
        exp.add_command(label="Save Project (JSON)", command=self.save_project)
        exp.add_command(label="Save Workspace Layout", command=self.save_workspace)
        exp.add_command(label="Load Workspace Layout", command=self.load_workspace)
        exp.add_command(label="Save Custom Brush", command=self.save_custom_brush)
        menubar.add_cascade(label="Export", menu=exp)
        keys = tk.Menu(menubar, tearoff=0)
        keys.add_command(label="⌨️ Keyboard Shortcuts", command=self.show_shortcuts)
        menubar.add_cascade(label="Shortcuts", menu=keys)
        self.win.configure(menu=menubar)

        body = tk.Frame(self.win)
        body.pack(fill="both", expand=True, padx=6, pady=6)

        # Left: tool name, brush preview, colours, tool options, then the icon grids
        left = tk.Frame(body, width=300)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        self.tool_lbl = tk.Label(left, text="Pencil (Circle)", font=("Arial", 11, "bold"), relief="groove", pady=4)
        self.tool_lbl.pack(fill="x")
        self.brush_canvas = tk.Canvas(left, width=96, height=40, highlightthickness=0)
        self.brush_canvas.pack(pady=(4, 2))
        self.brush_lbl = tk.Label(left, text="Brush 1x1", font=("Arial", 8))
        self.brush_lbl.pack()
        row = tk.Frame(left)
        row.pack(fill="x", pady=(4, 0))
        tk.Label(row, text="Primary:", font=("Arial", 9, "bold")).pack(side="left")
        self.color_btn = tk.Button(row, width=3, command=self.pick_primary)
        self.color_btn.pack(side="left", padx=4)
        self.color_entry = tk.Entry(row, width=8)
        self.color_entry.pack(side="left")
        self.color_entry.bind("<Return>", lambda e: self.set_color(self.color_entry.get()))
        tk.Button(row, text="💧", command=self.pick_from_image).pack(side="left", padx=(4, 0))
        self.recent_frame = tk.Frame(left)
        self.recent_frame.pack(fill="x", pady=2)
        self.secondary_row = tk.Frame(left)
        tk.Label(self.secondary_row, text="Secondary:", font=("Arial", 9)).pack(side="left")
        self.color2_btn = tk.Button(self.secondary_row, width=3, command=self.pick_secondary)
        self.color2_btn.pack(side="left", padx=4)
        self.color2_entry = tk.Entry(self.secondary_row, width=8)
        self.color2_entry.pack(side="left")
        self.color2_entry.bind("<Return>", lambda e: self.set_color2(self.color2_entry.get()))
        self.grad_row = tk.Frame(left)
        tk.Label(self.grad_row, text="Gradient max length", font=("Arial", 8)).pack(side="left")
        tk.Scale(self.grad_row, from_=1, to=100, orient="horizontal", variable=self.grad_var, length=120,
                 command=lambda v: setattr(self, "grad_len", int(float(v)))).pack(side="left")
        self.pattern_row = tk.Frame(left)
        tk.Label(self.pattern_row, text="Pattern", font=("Arial", 8)).pack(side="left")
        ttk.Combobox(self.pattern_row, textvariable=self.pattern_var, values=[p for _k, p in PATTERNS],
                     state="readonly", width=18).pack(side="left", padx=4)
        self.pattern_var.trace_add("write", lambda *_: setattr(
            self, "pattern", {l: k for k, l in PATTERNS}[self.pattern_var.get()]))
        self.sym_row = tk.Frame(left)
        tk.Label(self.sym_row, text="Symmetry", font=("Arial", 8)).pack(side="left")
        ttk.Combobox(self.sym_row, textvariable=self.sym_var, values=[s for _k, s in SYMMETRY],
                     state="readonly", width=18).pack(side="left", padx=4)
        self.sym_var.trace_add("write", lambda *_: setattr(
            self, "symmetry", {l: k for k, l in SYMMETRY}[self.sym_var.get()]))
        self.shape_row = tk.Frame(left)
        for text, var in (("Fill Shape", self.fill_shape), ("Gradient Fill", self.grad_shape),
                          ("Pixel-Perfect Circles", self.perfect_circle)):
            tk.Checkbutton(self.shape_row, text=text, variable=var, font=("Arial", 8)).pack(anchor="w")
        self.options_anchor = tk.Frame(left)
        self.options_anchor.pack(fill="x")

        brush = tk.Frame(left)
        brush.pack(fill="x", pady=(4, 0))
        self.size_lbl = tk.Label(brush, text="Size 1x1", width=10, anchor="w", font=("Arial", 8))
        self.size_lbl.grid(row=0, column=0, sticky="w")
        self.size_scale = tk.Scale(brush, from_=1, to=32, orient="horizontal", variable=self.size_var, showvalue=False,
                                   command=lambda v: self.set_brush_size(int(float(v))))
        self.size_scale.grid(row=0, column=1, sticky="we")
        tk.Label(brush, text="Shape", font=("Arial", 8)).grid(row=1, column=0, sticky="w")
        shape = ttk.Combobox(brush, textvariable=self.shape_var, values=[s for _k, s in BRUSH_SHAPES], state="readonly",
                             width=12)
        shape.grid(row=1, column=1, sticky="w")
        shape.bind("<<ComboboxSelected>>", lambda e: self.set_brush_shape({l: k for k, l in BRUSH_SHAPES}[self.shape_var.get()]))
        self.custom_row = tk.Frame(brush)
        tk.Button(self.custom_row, text="🎨 Create", font=("Arial", 8), command=self.create_custom_brush).pack(side="left")
        tk.Button(self.custom_row, text="💾 Save", font=("Arial", 8), command=self.save_custom_brush).pack(side="left")
        tk.Button(self.custom_row, text="📥 Load", font=("Arial", 8), command=self.load_custom_brush).pack(side="left")
        tk.Label(brush, text="Stroke delay", font=("Arial", 8)).grid(row=3, column=0, sticky="w")
        tk.Scale(brush, from_=0, to=100, resolution=5, orient="horizontal", variable=self.delay_var,
                 command=lambda v: setattr(self, "brush_delay", int(float(v)))).grid(row=3, column=1, sticky="we")
        brush.grid_columnconfigure(1, weight=1)
        self.brush_frame = brush

        undo = tk.Frame(left)
        undo.pack(fill="x", pady=4)
        tk.Button(undo, text="↶ Undo", command=self.undo).pack(side="left", expand=True, fill="x")
        tk.Button(undo, text="↷ Redo", command=self.redo).pack(side="left", expand=True, fill="x")
        self.sel_lbl = tk.Label(left, text="", font=("Arial", 8, "bold"), fg="#2196f3")
        self.sel_lbl.pack(anchor="w")

        tools = tk.Frame(left)
        tools.pack(fill="both", expand=True)
        self.tool_buttons = {}
        for group, items in TOOL_GROUPS:
            box = tk.LabelFrame(tools, text=group, font=("Arial", 8, "bold"))
            box.pack(fill="x", pady=1)
            for n, (tool, icon, name, key) in enumerate(items):
                b = tk.Button(box, text=icon, width=3, font=("Segoe UI Emoji", 10),
                              command=lambda t=tool: self.tool_action(t))
                b.grid(row=n // 8, column=n % 8, padx=1, pady=1)
                tip = name + (" (%s)" % key if key else "")
                self._tooltip(b, tip)
                b._paint = TOOL_GROUP_COLORS[group]
                self.tool_buttons[tool] = b
        self.swap_frame = tk.Frame(left)

        # Centre: the drawing canvas
        centre = tk.Frame(body)
        centre.pack(side="left", fill="both", expand=True, padx=6)
        self.status = tk.Label(centre, text="", anchor="w", font=("Arial", 9, "bold"), fg="#2196f3", wraplength=560)
        self.status.pack(fill="x")
        wrap = tk.Frame(centre, relief="sunken", bd=1)
        wrap.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(wrap, highlightthickness=0, bg="#888888")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Double-Button-1>", self.on_double)
        self.canvas.bind("<ButtonPress-3>", self.on_right_press)
        self.canvas.bind("<B3-Motion>", self.on_pan_drag)
        self.canvas.bind("<MouseWheel>", self.on_wheel)
        self.pan = [0, 0]
        zoom = tk.Frame(centre)
        zoom.pack(fill="x", pady=(2, 0))
        tk.Button(zoom, text="−", width=2, command=lambda: self.zoom_by(-1)).pack(side="left")
        self.zoom_lbl = tk.Label(zoom, text="1x", width=4)
        self.zoom_lbl.pack(side="left")
        tk.Button(zoom, text="+", width=2, command=lambda: self.zoom_by(1)).pack(side="left")
        tk.Button(zoom, text="Reset", command=lambda: self.zoom_by(0)).pack(side="left", padx=4)
        tk.Label(zoom, text="Scroll to zoom · right-drag to pan", fg="gray", font=("Arial", 8)).pack(side="left")

        # Right: layers, frames, preview, and the panels Other Options can reveal
        right_outer = tk.Frame(body, width=330)
        right_outer.pack(side="right", fill="y")
        right_outer.pack_propagate(False)
        sc = tk.Canvas(right_outer, highlightthickness=0)
        sb = ttk.Scrollbar(right_outer, orient="vertical", command=sc.yview)
        sc.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        sc.pack(side="left", fill="both", expand=True)
        right = tk.Frame(sc)
        sc.create_window((0, 0), window=right, anchor="nw", width=312)
        right.bind("<Configure>", lambda e: sc.configure(scrollregion=sc.bbox("all")))
        sc.bind_all("<MouseWheel>", lambda e: sc.yview_scroll(int(-e.delta / 120), "units")
                    if str(e.widget).startswith(str(right_outer)) else None, add="+")

        lay = tk.LabelFrame(right, text="Layers", font=("Arial", 10, "bold"))
        lay.pack(fill="x", pady=(0, 4))
        self.layer_list = tk.Frame(lay)
        self.layer_list.pack(fill="x")
        row = tk.Frame(lay)
        row.pack(fill="x", pady=2)
        tk.Button(row, text="Add Layer", command=self.add_layer).pack(side="left", expand=True, fill="x")
        tk.Button(row, text="Delete Layer", command=self.delete_layer).pack(side="left", expand=True, fill="x")

        fr = tk.LabelFrame(right, text="Animation Frames", font=("Arial", 10, "bold"))
        fr.pack(fill="x", pady=(0, 4))
        tk.Checkbutton(fr, text="Timeline View", variable=self.timeline_var, command=self.toggle_timeline).pack(anchor="w")
        self.timeline_row = tk.Frame(fr)
        for text, cmd in (("⏮", lambda: self.load_frame(0)), ("◀", lambda: self.load_frame(self.cur_frame - 1))):
            tk.Button(self.timeline_row, text=text, width=2, command=cmd).pack(side="left")
        self.scrub_var = tk.IntVar(value=0)
        self.scrub = tk.Scale(self.timeline_row, from_=0, to=0, orient="horizontal", variable=self.scrub_var,
                              showvalue=False, length=110, command=lambda v: self.load_frame(int(float(v))))
        self.scrub.pack(side="left")
        for text, cmd in (("▶", lambda: self.load_frame(self.cur_frame + 1)),
                          ("⏭", lambda: self.load_frame(len(self.frames) - 1))):
            tk.Button(self.timeline_row, text=text, width=2, command=cmd).pack(side="left")
        self.timeline_lbl = tk.Label(self.timeline_row, text="1/1", font=("Arial", 8))
        self.timeline_lbl.pack(side="left", padx=2)
        thumbs = tk.Frame(fr)
        thumbs.pack(fill="x")
        self.thumb_canvas = tk.Canvas(thumbs, height=THUMB + 18, highlightthickness=0)
        tsb = ttk.Scrollbar(thumbs, orient="horizontal", command=self.thumb_canvas.xview)
        self.thumb_canvas.configure(xscrollcommand=tsb.set)
        self.thumb_canvas.pack(fill="x")
        tsb.pack(fill="x")
        self.thumb_canvas.bind("<Button-1>", self.on_thumb_click)
        self.thumb_canvas.bind("<Button-3>", self.on_thumb_right)
        self.thumb_canvas.bind("<Double-Button-1>", self.on_thumb_double)
        self.thumb_canvas.bind("<ButtonRelease-1>", self.on_thumb_release)
        tools = tk.Frame(fr)
        tools.pack(fill="x", pady=2)
        for n, (label, cmd) in enumerate((("Clone", lambda: self.add_frame("clone")), ("Add Blank", lambda: self.add_frame("blank")),
                                          ("Delete", self.delete_frame), ("Copy", self.copy_frame),
                                          ("Paste", self.paste_frame), ("Set Loop", self.set_loop))):
            tk.Button(tools, text=label, font=("Arial", 8), command=cmd).grid(row=n // 3, column=n % 3, sticky="we", padx=1, pady=1)
        tk.Button(tools, text="◄ Move", font=("Arial", 8), command=self.move_frame_left).grid(row=2, column=0, sticky="we", padx=1)
        tk.Button(tools, text="Move ►", font=("Arial", 8), command=self.move_frame_right).grid(row=2, column=2, sticky="we", padx=1)
        for c in range(3):
            tools.grid_columnconfigure(c, weight=1)

        ap = tk.LabelFrame(right, text="Animation Preview", font=("Arial", 10, "bold"))
        ap.pack(fill="x", pady=(0, 4))
        row = tk.Frame(ap)
        row.pack(fill="x")
        tk.Label(row, text="Speed (ms)", font=("Arial", 8)).pack(side="left")
        tk.Scale(row, from_=50, to=1000, resolution=50, orient="horizontal", variable=self.speed_var, length=120).pack(side="left")
        ttk.Combobox(row, textvariable=self.mult_var, values=["0.25x", "0.5x", "1x", "2x", "4x"], state="readonly",
                     width=5).pack(side="left", padx=2)
        row = tk.Frame(ap)
        row.pack(fill="x")
        self.preview_canvas = tk.Canvas(row, width=PREVIEW, height=PREVIEW, highlightthickness=1, highlightbackground="#888")
        self.preview_canvas.pack(side="left", padx=4, pady=4)
        info = tk.Frame(row)
        info.pack(side="left", fill="y")
        self.play_btn = tk.Button(info, text="Pause Preview", bg="#dc3545", fg="white", command=self.toggle_preview)
        self.play_btn._cp_keep = True  # keeps its own red / green
        self.play_btn.pack(fill="x", pady=2)
        self.preview_lbl = tk.Label(info, text="Frame 1 / 1", font=("Arial", 8))
        self.preview_lbl.pack(anchor="w")
        self.fps_lbl = tk.Label(info, text="FPS ~6.7", font=("Arial", 8))
        self.fps_lbl.pack(anchor="w")
        self.loop_lbl = tk.Label(info, text="Loop: all", font=("Arial", 8))
        self.loop_lbl.pack(anchor="w")

        # Colour Palette & Histogram/Channels: hidden until Other Options turns them on
        self.palette_box = tk.LabelFrame(right, text="Color Palette", font=("Arial", 10, "bold"))
        self.palette_grid = tk.Frame(self.palette_box)
        self.palette_grid.pack(fill="x")
        self.palette_count = tk.Label(self.palette_box, text="0 colors detected", font=("Arial", 8))
        self.palette_count.pack(anchor="w")
        pbtn = tk.Frame(self.palette_box)
        pbtn.pack(fill="x", pady=2)
        for n, (label, cmd) in enumerate((("Import", self.import_palette), ("Add Color", self.add_palette_color),
                                          ("Refresh Colors", self.refresh_palette), ("Export", self.export_palette),
                                          ("Generate Gradient", self.gradient_palette), ("Clear", self.clear_palette))):
            tk.Button(pbtn, text=label, font=("Arial", 8), command=cmd).grid(row=n // 3, column=n % 3, sticky="we", padx=1, pady=1)
        for c in range(3):
            pbtn.grid_columnconfigure(c, weight=1)
        self.hist_box = tk.LabelFrame(right, text="Histogram & Channels", font=("Arial", 10, "bold"))
        self.hist_canvas = tk.Canvas(self.hist_box, width=300, height=100, highlightthickness=1, highlightbackground="#ccc")
        self.hist_canvas.pack(pady=2)
        self.hist_lbl = tk.Label(self.hist_box, text="RGB color distribution", font=("Arial", 8))
        self.hist_lbl.pack(anchor="w")
        hrow = tk.Frame(self.hist_box)
        hrow.pack(fill="x")
        self.hist_channel = "all"
        for n, (label, ch) in enumerate((("Update", None), ("Red", "r"), ("Green", "g"), ("Blue", "b"), ("All", "all"))):
            tk.Button(hrow, text=label, font=("Arial", 8),
                      command=lambda c=ch: self.show_histogram(c or self.hist_channel)).pack(side="left", expand=True, fill="x")
        crow = tk.Frame(self.hist_box)
        crow.pack(fill="x", pady=2)
        for label, cmd in (("Extract Red", lambda: self.extract_channel(0)), ("Extract Green", lambda: self.extract_channel(1)),
                           ("Extract Blue", lambda: self.extract_channel(2)), ("Invert", self.invert_colors)):
            tk.Button(crow, text=label, font=("Arial", 8), command=cmd).pack(side="left", expand=True, fill="x")

    def _tooltip(self, widget, text):
        tip = {"w": None}

        def show(_e):
            if tip["w"]:
                return
            t = tk.Toplevel(widget)
            t.wm_overrideredirect(True)
            t.wm_geometry("+%d+%d" % (widget.winfo_rootx() + 20, widget.winfo_rooty() + widget.winfo_height() + 2))
            tk.Label(t, text=text, bg="#333333", fg="white", font=("Arial", 8), padx=4, pady=2).pack()
            tip["w"] = t

        def hide(_e):
            if tip["w"]:
                tip["w"].destroy()
                tip["w"] = None

        widget.bind("<Enter>", show, add="+")
        widget.bind("<Leave>", hide, add="+")
