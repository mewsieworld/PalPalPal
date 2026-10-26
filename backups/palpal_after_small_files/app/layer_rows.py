"""PalPalPal main window: the Layers box rows, dragging and right-click menu."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.colors import to_hex
from ..core.images import BLEND_MODES, ImageLayer, PaletteLayer, clone_palette
from ..ui.theme import Theme, Tooltip


class AppLayerRowsMixin:
    """PalPalPal main window: the Layers box rows, dragging and right-click menu."""

    LAYER_ICONS = {"combined": "▲", "image": "●", "palette": "■"}

    LAYER_ICON_TIPS = {"combined": "Image + its palette (combined)", "image": "Image only (colored by the palettes above)",
                       "palette": "Palette"}

    def entry_kind(self, entry):
        if isinstance(entry, ImageLayer):
            return "combined" if entry.combined else "image"
        return "palette"

    def row_palette(self, entry):
        """The palette a row selects: its own for combined images and palettes, the coloring one for image-only rows."""
        if isinstance(entry, PaletteLayer):
            return entry
        return entry.palette if entry.combined else self.palette_coloring(entry)

    def refresh_layers_box(self):
        for w in self.layer_rows.winfo_children():
            w.destroy()
        self.refresh_palette_tabs()
        if not self.stack:
            tk.Label(self.layer_rows, text="Nothing here yet. Use New to add a layer or a palette.",
                     fg="gray").pack(pady=10)
        selected_entry = self.entry_of(self.selected_palette())
        self.layer_row_widgets = {}
        self.layer_thumbs = []
        for entry in reversed(self.stack):
            kind = self.entry_kind(entry)
            if self.layer_filter == "images" and kind == "palette" or self.layer_filter == "palettes" and kind == "image":
                continue
            is_image = kind != "palette"
            chosen = entry is selected_entry or (kind == "palette" and entry is self.selected_palette())
            row = tk.Frame(self.layer_rows, relief="sunken" if chosen else "flat", bd=1)
            row.pack(fill="x", pady=1)
            shown = self.entry_shown(entry)
            eye = tk.Button(row, text="👁" if shown else "–", width=2, relief="flat",
                            command=lambda e=entry: self.toggle_entry(e, not self.entry_shown(e)))
            eye.pack(side="left")
            Tooltip(eye, "Show / hide this layer", self)
            icon = tk.Label(row, text=self.LAYER_ICONS[kind], width=2, font=("Arial", 11))
            icon.pack(side="left")
            Tooltip(icon, self.LAYER_ICON_TIPS[kind], self)
            self._effects_button(row, entry, shown)
            if is_image:
                self._palette_source_button(row, entry)
            widgets = [row, icon]
            if is_image:
                widgets.append(self._layer_thumbnail(row, entry))
            if kind != "image":
                widgets.append(self._palette_strip(row, entry.palette if is_image else entry))
            extra = "  (%d frames)" % len(entry.frames) if is_image and len(entry.frames) > 1 else ""
            lbl = tk.Label(row, text=entry.name + extra, anchor="w", font=("Arial", 9, "bold" if chosen else "normal"))
            lbl.pack(side="left", fill="x", expand=True, padx=(4, 0))
            widgets.append(lbl)
            palette = self.row_palette(entry)
            index = self.layers.index(palette) if palette in self.layers else 0
            self.layer_row_widgets[row] = entry
            for w in widgets:
                w.bind("<ButtonPress-1>", lambda e, j=index, en=entry: self._layer_press(e, j, en))
                w.bind("<Button-3>", lambda e, en=entry: self.layer_context_menu(e, en))
        self.layer_rows.bind("<Button-3>", lambda e: self.layer_context_menu(e, None))
        self.layer_rows.master.bind("<Button-3>", lambda e: self.layer_context_menu(e, None))
        Theme.apply(self, self.layer_rows)
        self.refresh_layer_vis_button()

    def _effects_button(self, row, entry, shown):
        """The row's blend mode and opacity menu."""
        fx = tk.Menubutton(row, text="%s %d%% ▾" % (entry.blend, round(entry.opacity * 100)),
                           relief="raised", font=("Arial", 8), width=13)
        fx_menu = tk.Menu(fx, tearoff=0)
        blend_var = tk.StringVar(value=entry.blend)
        blend_menu = tk.Menu(fx_menu, tearoff=0)
        for mode in BLEND_MODES:
            blend_menu.add_radiobutton(label=mode, value=mode, variable=blend_var,
                                       command=lambda m=mode: self.set_entry_effect(entry, blend=m))
        fx_menu.add_cascade(label="Blend mode", menu=blend_menu)
        opacity_menu = tk.Menu(fx_menu, tearoff=0)
        for pct in (100, 75, 50, 25, 10):
            opacity_menu.add_command(label="%d%%" % pct,
                                     command=lambda v=pct: self.set_entry_effect(entry, opacity=v / 100.0))
        opacity_menu.add_command(label="Custom...", command=lambda: self.ask_opacity(entry))
        fx_menu.add_cascade(label="Opacity", menu=opacity_menu)
        fx_menu.add_separator()
        fx_menu.add_command(label="Hide" if shown else "Show",
                            command=lambda: self.toggle_entry(entry, not self.entry_shown(entry)))
        fx.configure(menu=fx_menu)
        fx.pack(side="right", padx=(4, 0))
        self.menus.extend([fx_menu, blend_menu, opacity_menu])

    def _layer_thumbnail(self, row, il):
        img = self.render_layer(il, self.current_frame if self.split_palettes is False else self.palette_tab)
        img.thumbnail((28, 18), Image.Resampling.NEAREST)
        photo = ImageTk.PhotoImage(img)
        self.layer_thumbs.append(photo)
        lbl = tk.Label(row, image=photo, width=28, height=18, relief="solid", bd=1)
        lbl._cp_keep = True
        lbl.pack(side="left", padx=(0, 4))
        return lbl

    def _palette_strip(self, row, palette):
        strip = tk.Canvas(row, width=64, height=14, highlightthickness=0)
        strip._cp_keep = True
        strip.pack(side="left", padx=(0, 6))
        used = self.editable_indices(palette)[:16] or list(range(16))
        for n, idx in enumerate(used):
            strip.create_rectangle(n * 4, 0, n * 4 + 4, 14, fill=to_hex(palette.colors[idx]), outline="")
        return strip

    def _palette_source_button(self, row, il):
        """Per image layer: pick whether its own palette, the palettes above it, or one chosen palette paints it."""
        self.stacked_palettes(il)  # drops a chosen palette that has since been removed
        src = il.palette_source
        label = "Own" if src == "own" else "Stack" if src == "stack" else src.name[:8]
        btn = tk.Menubutton(row, text="🎨 %s ▾" % label, relief="raised", font=("Arial", 8), width=9)
        menu = tk.Menu(btn, tearoff=0)
        var = tk.StringVar(value=src if isinstance(src, str) else "p%d" % self.stack.index(src))
        menu.add_radiobutton(label="Palettes above it (stack)", value="stack", variable=var,
                             command=lambda: self.set_palette_source(il, "stack"))
        menu.add_radiobutton(label="Its own palette", value="own", variable=var,
                             command=lambda: self.set_palette_source(il, "own"))
        palettes = [e for e in self.stack if isinstance(e, PaletteLayer)]
        if palettes:
            menu.add_separator()
        for p in palettes:
            menu.add_radiobutton(label=p.name, value="p%d" % self.stack.index(p), variable=var,
                                 command=lambda p=p: self.set_palette_source(il, p))
        btn.configure(menu=menu)
        btn.pack(side="right", padx=(4, 0))
        Tooltip(btn, "Which palette this image uses", self)
        self.menus.append(menu)

    def _layer_press(self, event, index, entry):
        now = event.time
        last = getattr(self, "_last_press", (None, 0))
        self._last_press = (entry, now)
        if last[0] is entry and 0 <= now - last[1] < 450:
            self._drag_entry = None
            self.rename_entry(entry)  # double-click
            return
        self._drag_entry = entry
        self.select_layer(index)
        # The row widgets are rebuilt when the selection changes, so wait for the release on the window
        self.master.bind("<ButtonRelease-1>", self._layer_release, add="+")
        self.master.configure(cursor="fleur")

    def _layer_release(self, event):
        """Drop a dragged row onto another row to move it there."""
        self.master.unbind("<ButtonRelease-1>")
        self.master.configure(cursor="")
        entry = getattr(self, "_drag_entry", None)
        self._drag_entry = None
        target_widget = self.master.winfo_containing(event.x_root, event.y_root)
        target = None
        while target_widget is not None and target is None:
            target = getattr(self, "layer_row_widgets", {}).get(target_widget)
            target_widget = target_widget.master if target is None else None
        if entry is None or target is None or target is entry:
            return
        palette = self.selected_palette()
        moving_up = self.stack.index(entry) < self.stack.index(target)
        self.stack.remove(entry)
        self.stack.insert(self.stack.index(target) + (1 if moving_up else 0), entry)
        if palette in self.layers:
            self.selected_layer = self.layers.index(palette)
        self.structure_changed()

    def layer_context_menu(self, event, entry):
        """Layer / Import / Show / Palette / Palette Inheritance, in that order."""
        menu = tk.Menu(self.master, tearoff=0)
        if entry is not None:
            palette = self.row_palette(entry)
            if palette in self.layers:
                self.select_layer(self.layers.index(palette))
        subs = []

        def sub(label):
            m = tk.Menu(menu, tearoff=0)
            menu.add_cascade(label=label, menu=m)
            subs.append(m)
            return m

        layer = sub("Layer")
        layer.add_command(label="Draw Layer", command=self.open_sprite_tool)
        layer.add_command(label="New Palette Layer", command=self.new_palette_layer)
        if entry is not None:
            layer.add_command(label="Rename...", command=lambda: self.rename_entry(entry))
            layer.add_command(label="Hide" if self.entry_shown(entry) else "Show",
                              command=lambda: self.toggle_entry(entry, not self.entry_shown(entry)))
            layer.add_command(label="Remove", command=self.remove_layer)

        imp = sub("Import")
        imp.add_command(label="Palette...", command=self.open_palette)
        imp.add_command(label="Img as Layer...", command=self.open_images)
        imp.add_command(label="Img as Frames...", command=self.import_frames)

        show = sub("Show")
        filter_var = tk.StringVar(value=self.layer_filter)
        for label, value in (("▲ All layers", "all"), ("■ Palette layers", "palettes"), ("● Img layers", "images")):
            show.add_radiobutton(label=label, value=value, variable=filter_var,
                                 command=lambda v=value: self.set_layer_filter(v))
        menu._filter_var = filter_var

        pal = sub("Palette")
        pal.add_command(label="New Palette Layer", command=self.new_palette_layer)
        if entry is not None:
            pal.add_command(label="Edit", command=lambda: self.open_switcher(force=True))
            if isinstance(entry, ImageLayer) and entry.combined:
                pal.add_command(label="Separate Img", command=lambda: self.separate_layer(entry))
            else:
                pal.add_command(label="Combine with Img", command=lambda: self.combine_layer(entry))

        if isinstance(entry, ImageLayer):
            inherit = sub("Palette Inheritance")
            source_var = tk.StringVar(value=entry.palette_source if isinstance(entry.palette_source, str) else "")
            menu._source_var = source_var
            inherit.add_radiobutton(label="Stack (palettes above it)", value="stack", variable=source_var,
                                    command=lambda: self.set_palette_source(entry, "stack"))
            inherit.add_radiobutton(label="Own palette", value="own", variable=source_var,
                                    command=lambda: self.set_palette_source(entry, "own"))
            others = [e for e in self.stack if isinstance(e, PaletteLayer)]
            if others:
                inherit.add_separator()
            for p in others:
                inherit.add_command(label=p.name, command=lambda p=p: self.set_palette_source(entry, p))
        for m in [menu] + subs:
            Theme.apply(self, m)
        menu.tk_popup(event.x_root, event.y_root)
