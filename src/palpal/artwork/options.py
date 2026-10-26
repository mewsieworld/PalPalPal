"""Artwork Tool: the Options windows."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)


class OptionsMixin:
    """The Size, Display and Other Options windows, tilemap and guides."""

    def _options_window(self, title):
        name = "_opt_" + title
        old = getattr(self, name, None)
        if old is not None and old.winfo_exists():
            old.lift()
            return None
        top = self.popup()
        top.title(title)
        top.resizable(False, False)
        top.transient(self.win)
        setattr(self, name, top)
        return top

    def open_size_options(self):
        top = self._options_window("Size Options")
        if top is None:
            return
        f = tk.Frame(top)
        f.pack(padx=12, pady=10)
        tk.Label(f, text="Sprite Size (Pixels):", font=("Arial", 9, "bold")).grid(row=0, column=0, columnspan=4, sticky="w")
        preset = ttk.Combobox(f, values=["-- Presets --"] + [p[0] for p in PRESETS], state="readonly", width=28)
        preset.set("-- Presets --")
        preset.grid(row=1, column=0, columnspan=4, sticky="w", pady=2)

        def apply_preset(_e):
            for name, w, h in PRESETS:
                if name == preset.get():
                    self.w_var.set(w)
                    self.h_var.set(h)
                    self.resize_sprite(w, h)

        preset.bind("<<ComboboxSelected>>", apply_preset)
        tk.Checkbutton(f, text="🔗 Link", variable=self.link_var).grid(row=2, column=0, sticky="w")
        tk.Label(f, text="W:").grid(row=2, column=1)
        we = tk.Spinbox(f, from_=1, to=512, textvariable=self.w_var, width=5)
        we.grid(row=2, column=2)
        tk.Label(f, text="H:").grid(row=2, column=3)
        he = tk.Spinbox(f, from_=1, to=512, textvariable=self.h_var, width=5)
        he.grid(row=2, column=4)

        def linked(which):
            if self.link_var.get():
                try:
                    v = (self.w_var if which == "w" else self.h_var).get()
                except tk.TclError:
                    return
                (self.h_var if which == "w" else self.w_var).set(v)

        we.configure(command=lambda: linked("w"))
        he.configure(command=lambda: linked("h"))
        tk.Button(f, text="Change Size & Migrate Data", command=lambda: self.resize_sprite(int(self.w_var.get()),
                                                                                           int(self.h_var.get()))).grid(
            row=3, column=0, columnspan=5, sticky="we", pady=4)
        z = tk.Frame(f)
        z.grid(row=4, column=0, columnspan=5, sticky="w")
        tk.Label(z, text="Canvas Zoom (View):").pack(side="left")
        tk.Button(z, text="−", command=lambda: self.zoom_by(-1)).pack(side="left")
        tk.Button(z, text="+", command=lambda: self.zoom_by(1)).pack(side="left")
        tk.Button(z, text="Reset", command=lambda: self.zoom_by(0)).pack(side="left")
        tk.Button(f, text="⌨️ Shortcuts", command=self.show_shortcuts).grid(row=5, column=0, sticky="w", pady=(4, 0))
        self.theme(top)

    def open_display_options(self):
        top = self._options_window("Display Options")
        if top is None:
            return
        f = tk.Frame(top)
        f.pack(padx=12, pady=10)
        tk.Label(f, text="👁️ Display Options:", font=("Arial", 9, "bold")).grid(row=0, column=0, columnspan=4, sticky="w")
        tk.Label(f, text="Grid:").grid(row=1, column=0, sticky="w")
        g = ttk.Combobox(f, values=["high", "low", "none"], state="readonly", width=8, textvariable=self.grid_vis)
        g.grid(row=1, column=1, sticky="w")
        g.bind("<<ComboboxSelected>>", lambda e: self.redraw())

        def pick(attr, btn):
            res = self.askcolor(color=getattr(self, attr), parent=top)
            if res and res[1]:
                setattr(self, attr, res[1])
                btn.configure(bg=res[1])
                self.redraw()

        tk.Label(f, text="Line Color:").grid(row=1, column=2)
        b1 = tk.Button(f, bg=self.grid_color, width=3)
        b1.configure(command=lambda: pick("grid_color", b1))
        b1._cp_keep = True
        b1.grid(row=1, column=3)
        tk.Checkbutton(f, text="Darkened Grid Pattern", variable=self.dark_grid, command=self.redraw).grid(row=2, column=0,
                                                                                                         columnspan=2, sticky="w")
        tk.Label(f, text="Every:").grid(row=2, column=2)
        sp = tk.Spinbox(f, from_=1, to=64, textvariable=self.dark_every, width=4, command=self.redraw)
        sp.grid(row=2, column=3)
        sp.bind("<Return>", lambda e: self.redraw())
        b2 = tk.Button(f, bg=self.dark_color, width=3)
        b2.configure(command=lambda: pick("dark_color", b2))
        b2._cp_keep = True
        b2.grid(row=2, column=4)
        tk.Label(f, text="Canvas BG:").grid(row=3, column=0, sticky="w")
        bgs = {"White": "#ffffff", "Black": "#000000", "Gray": "#808080", "Checkerboard": "checker", "Custom Color": "custom"}
        bg = ttk.Combobox(f, values=list(bgs), state="readonly", width=12)
        bg.set(next((k for k, v in bgs.items() if v == self.bg_preset.get()), "White"))
        bg.grid(row=3, column=1, sticky="w")

        def set_bg(_e):
            self.bg_preset.set(bgs[bg.get()])
            self.redraw()

        bg.bind("<<ComboboxSelected>>", set_bg)
        tk.Label(f, text="Custom:").grid(row=3, column=2)
        b3 = tk.Button(f, bg=self.bg_custom, width=3)
        b3.configure(command=lambda: pick("bg_custom", b3))
        b3._cp_keep = True
        b3.grid(row=3, column=3)
        tk.Label(f, text="*Affects BMP exports", fg="gray", font=("Arial", 8)).grid(row=4, column=0, columnspan=4, sticky="w")
        if self.dark_mode:
            get_dark, toggle_dark = self.dark_mode
            # Kept on self: a local variable would be garbage collected and the tick would vanish
            self._dark_var = dark = tk.BooleanVar(master=top, value=bool(get_dark()))

            def flip_dark():
                self.colors = toggle_dark() or self.colors
                self.theme(self.win)
                self.theme(top)
                self.render_layers()

            tk.Checkbutton(f, text="🌙 Dark Mode", variable=dark, command=flip_dark).grid(row=5, column=0, columnspan=5,
                                                                                          sticky="e")
        self.theme(top)

    def open_other_options(self):
        top = self._options_window("Other Options")
        if top is None:
            return
        f = tk.Frame(top)
        f.pack(padx=12, pady=10)
        for text, var, cmd in (("Perspective Grid", self.persp, self.redraw),
                               ("Guides & Rulers", self.guides, lambda: (self.redraw(), show_rows())),
                               ("Auto-Save (1 min)", self.autosave, self.toggle_autosave),
                               ("Tilemap Mode", self.tilemap, lambda: (self.toggle_tilemap(), show_rows())),
                               ("Onion Skinning", self.onion, lambda: (self.redraw(), show_rows())),
                               ("Show Color Palette & Extended Options", self.show_palette, self.apply_panels),
                               ("Show Histogram & Extended Options (Channels)", self.show_hist_var, self.apply_panels)):
            tk.Checkbutton(f, text=text, variable=var, command=cmd).pack(anchor="w")
        guides = tk.Frame(f)
        for label, cmd in (("Add Vertical Guide", lambda: self.add_guide("v")), ("Add Horizontal Guide", lambda: self.add_guide("h")),
                           ("Manage Guides", self.manage_guides), ("Clear All Guides", self.clear_guides)):
            tk.Button(guides, text=label, font=("Arial", 8), command=cmd).pack(side="left")
        tile = tk.Frame(f)
        tk.Label(tile, text="Tile Size").pack(side="left")
        tk.Scale(tile, from_=4, to=32, resolution=4, orient="horizontal", variable=self.tile_size,
                 command=lambda v: self.toggle_tilemap()).pack(side="left")
        onion = tk.Frame(f)
        for label, var, lo, hi, step in (("Prev Frames %", self.onion_prev, 0, 100, 5), ("Next Frames %", self.onion_next, 0, 100, 5),
                                         ("Frames Count", self.onion_count, 1, 5, 1)):
            r = tk.Frame(onion)
            r.pack(fill="x")
            tk.Label(r, text=label, width=14, anchor="w").pack(side="left")
            tk.Scale(r, from_=lo, to=hi, resolution=step, orient="horizontal", variable=var,
                     command=lambda v: self.redraw()).pack(side="left")

        def show_rows():
            for frame, on in ((guides, self.guides.get()), (tile, self.tilemap.get()), (onion, self.onion.get())):
                if on:
                    frame.pack(fill="x", pady=2)
                else:
                    frame.pack_forget()

        show_rows()
        self.theme(top)

    def apply_panels(self):
        for box, var in ((self.palette_box, self.show_palette), (self.hist_box, self.show_hist_var)):
            if var.get():
                box.pack(fill="x", pady=(0, 4))
            else:
                box.pack_forget()
        if self.show_palette.get():
            self.refresh_palette()
        if self.show_hist_var.get():
            self.show_histogram_channel()
        self.theme(self.palette_box)
        self.theme(self.hist_box)

    def show_histogram_channel(self):
        self.show_histogram(self.hist_channel)

    def toggle_tilemap(self):
        if self.tilemap.get():
            self.brush_size = self.tile_size.get()
            self.size_var.set(self.brush_size)
            self.size_scale.configure(state="disabled")
        else:
            self.size_scale.configure(state="normal")
        self.draw_brush_preview()
        self.redraw()

    def add_guide(self, kind):
        limit = self.W if kind == "v" else self.H
        v = simpledialog.askinteger("📐 Add Guide", "Add %s guide at %s position (0-%d):"
                                    % ("vertical" if kind == "v" else "horizontal", "X" if kind == "v" else "Y", limit - 1),
                                    initialvalue=limit // 2, minvalue=0, maxvalue=limit - 1, parent=self.win)
        if v is not None:
            (self.v_guides if kind == "v" else self.h_guides).append(v)
            self.redraw()

    def manage_guides(self):
        text = "VERTICAL:\n" + "\n".join("  %d: X=%d" % (i + 1, g) for i, g in enumerate(self.v_guides))
        text += "\nHORIZONTAL:\n" + "\n".join("  %d: Y=%d" % (i + 1, g) for i, g in enumerate(self.h_guides))
        action = simpledialog.askstring("📐 Manage Guides", text + '\n\nEnter "v" + number to remove a vertical guide, '
                                                                  '"h" + number for horizontal (e.g. v1)', parent=self.win)
        if action and len(action) >= 2 and action[1:].isdigit():
            seq = self.v_guides if action[0].lower() == "v" else self.h_guides if action[0].lower() == "h" else None
            i = int(action[1:]) - 1
            if seq is not None and 0 <= i < len(seq):
                del seq[i]
                self.redraw()

    def clear_guides(self):
        if messagebox.askyesno("Guides", "Clear all %d guides?" % (len(self.v_guides) + len(self.h_guides)), parent=self.win):
            self.v_guides, self.h_guides = [], []
            self.redraw()
