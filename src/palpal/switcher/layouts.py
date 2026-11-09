"""Super Swatch Switcher: the Simple, Advanced and NuAge layouts."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..ui.theme import Theme
from ..ui.widgets import hsv_row, make_swatch, relay_swatches, swatch_grid
from ..ui.saved_colors import SavedColorsPanel
from ..ui.picker_row import picker_row
from ..ui.sort_button import sort_indices, SortButton
from ..preview.canvas import PreviewView, bind_pan_and_zoom
from .constants import SKIN_SIZES


class SwitcherLayoutMixin:
    """Super Swatch Switcher: the Simple, Advanced and NuAge layouts."""

    # ----- build -----
    def build(self):
        for child in self.win.winfo_children():
            child.destroy()
        self.swatches = {}
        self.app.saved_panels = [p for p in self.app.saved_panels if p.frame.winfo_exists()]
        self.preview = None
        self.frame_lbl = None
        self.h_var, self.s_var, self.v_var = tk.IntVar(value=0), tk.IntVar(value=0), tk.IntVar(value=0)
        self.hex_var = tk.StringVar()
        self.idx_var = tk.StringVar(value=str(self.sel_index))
        self.zoom_var = tk.StringVar(value="Fit")
        self.win.geometry(SKIN_SIZES[self.skin])
        if self.skin == "NuAge":
            self.build_nuage()
        else:
            self.build_simple_or_advanced()
        Theme.apply(self.app, self.win)
        self.select_index(self.sel_index, force=True)
        self.update_selection_ui()
        self.win.after(60, self.update_preview)

    def _settings_menu(self, button):
        menu = tk.Menu(button, tearoff=0)
        skin_var = tk.StringVar(value=self.skin)
        menu.add_command(label="%s UI" % SWITCHER_NAME, state="disabled")
        for name in SKINS:
            menu.add_radiobutton(label="   " + name, value=name, variable=skin_var,
                                 command=lambda n=name: self.set_skin(n))
        Theme.apply(self.app, menu)
        menu.tk_popup(button.winfo_rootx(), button.winfo_rooty() + button.winfo_height())

    def set_skin(self, name):
        self.skin = name
        self.app.store.set("live_pal_ui_mode", name)
        self.build()

    def _top_bar(self, parent):
        top = tk.Frame(parent)
        top.pack(fill="x", padx=6, pady=6)
        tk.Label(top, text="Edit which:").pack(side="left")
        om = ttk.Combobox(top, textvariable=self.target_var, values=self._names(), state="readonly", width=20)
        om.pack(side="left", padx=(4, 6))
        om.bind("<<ComboboxSelected>>", lambda e: self.on_target_changed())
        tk.Checkbutton(top, text="Multi-select", variable=self.multi_var,
                       command=self.on_multi_toggled).pack(side="left", padx=(4, 4))
        tk.Button(top, text="Select All", command=self.select_all).pack(side="left", padx=(0, 4))
        tk.Button(top, text="Clear Sel", command=self.clear_selection).pack(side="left")
        self.count_lbl = tk.Label(top, text="(0 selected)")
        self.count_lbl.pack(side="left", padx=(4, 0))
        gear = tk.Button(top, text="⚙", width=3)
        gear.configure(command=lambda: self._settings_menu(gear))
        gear.pack(side="right")
        self._reset_menubutton(top).pack(side="right", padx=(0, 4))
        tk.Button(top, text="Save Palette", command=self.save_palette).pack(side="right", padx=(0, 4))

    def _reset_menubutton(self, parent, ttk_style=False):
        mb = (ttk.Menubutton if ttk_style else tk.Menubutton)(parent, text="Reset Colors")
        if not ttk_style:
            mb.configure(relief="raised")
        menu = tk.Menu(mb, tearoff=0)
        menu.add_command(label="Selected Index(es)", command=self.reset_selected)
        menu.add_command(label="Whole Palette", command=self.reset_all)
        mb.configure(menu=menu)
        return mb

    def _advanced_top_bar(self, parent):
        """[Save] [Reset] Sort: Index [ ] Multi-Select [Select All] [Clear] (n selected) Edit: [ which ]"""
        top = tk.Frame(parent)
        top.pack(fill="x", padx=6, pady=6)
        tk.Button(top, text="Save", command=self.save_palette).pack(side="left", padx=(0, 3))
        reset = self._reset_menubutton(top)
        reset.configure(text="Reset")
        reset.pack(side="left", padx=(0, 6))
        SortButton(self.app, top, self.resort).pack(side="left", padx=(0, 8))
        tk.Checkbutton(top, text="Multi-Select", variable=self.multi_var,
                       command=self.on_multi_toggled).pack(side="left")
        green = tk.Button(top, text="Select All", bg="#2e7d32", fg="white", activebackground="#388e3c",
                          activeforeground="white", command=self.select_all)
        green._cp_keep = True
        green.pack(side="left", padx=(4, 3))
        red = tk.Button(top, text="Clear", bg="#c62828", fg="white", activebackground="#d32f2f",
                        activeforeground="white", command=self.clear_selection)
        red._cp_keep = True
        red.pack(side="left")
        self.count_lbl = tk.Label(top, text="(0 selected)")
        self.count_lbl.pack(side="left", padx=(5, 6))
        tk.Label(top, text="Edit:").pack(side="left", padx=(8, 2))
        om = ttk.Combobox(top, textvariable=self.target_var, values=self._names(), state="readonly", width=16)
        om.pack(side="left", fill="x", expand=True)
        om.bind("<<ComboboxSelected>>", lambda e: self.on_target_changed())
        gear = tk.Button(top, text="⚙", width=3)
        gear.configure(command=lambda: self._settings_menu(gear))
        gear.pack(side="right", padx=(4, 0))

    def sorted_editable(self):
        return sort_indices(self.app, self.editable(), self.layer())

    def resort(self):
        """Re-lay only the swatch grid, so the open Sort list survives."""
        holder = getattr(self, "grid_holder", None)
        swatches = relay_swatches(holder, self.sorted_editable(), 40, 8, self.on_swatch_click)
        if swatches is None:
            return
        self.swatches = swatches
        self.update_selection_ui()
        Theme.apply(self.app, holder)

    def build_simple_or_advanced(self):
        """Simple: the full 16x16 grid. Advanced: the image's own colors with a live preview under them."""
        if self.skin == "Advanced":
            self._advanced_top_bar(self.win)
        else:
            self._top_bar(self.win)
        body = tk.Frame(self.win)
        body.pack(fill="both", expand=True, padx=1)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)
        grid = tk.Frame(body)
        grid.grid(row=0, column=0, sticky="nsew")
        if self.skin == "Simple":
            self._grid_16x16(grid)
        else:
            self._image_colors_with_preview(grid)
        panel = tk.LabelFrame(body, text="Color Picker", padx=2, pady=1)
        panel.grid(row=0, column=1, padx=(4, 4), sticky="nsew")
        self._picker_panel(panel)

    def _grid_16x16(self, grid):
        for i in range(PALETTE_SIZE):
            sw = make_swatch(grid, 20)
            sw.grid(row=i // 16, column=i % 16, padx=1, pady=1)
            sw.bind("<Button-1>", lambda e, j=i: self.on_swatch_click(j, e))
            sw.bind("<Button-3>", lambda e, j=i: self.on_swatch_click(j, e))
            self.swatches[i] = sw

    def _image_colors_with_preview(self, grid):
        grid.configure(width=8 * 44 + 20)
        if not self.show_preview():
            self.grid_holder = tk.Frame(grid)
            self.grid_holder.pack(fill="both", expand=True)
            self.swatches = swatch_grid(self.grid_holder, self.sorted_editable(), 40, 8, self.on_swatch_click)
            return
        paned = tk.PanedWindow(grid, orient="vertical", sashwidth=5, sashrelief="raised", bd=1, relief="sunken")
        paned.pack(fill="both", expand=True)
        top = tk.Frame(paned, height=100)
        paned.add(top, minsize=60)
        self.grid_holder = tk.Frame(top)
        self.grid_holder.pack(fill="both", expand=True)
        self.swatches = swatch_grid(self.grid_holder, self.sorted_editable(), 40, 8, self.on_swatch_click)
        bottom = tk.Frame(paned)
        paned.add(bottom, minsize=100)
        self._preview_block(bottom, header=True)
        self.win.after(120, lambda: paned.sash_place(0, 0, max(60, paned.winfo_height() // 3)))

    def _preview_block(self, parent, header):
        if header:
            controls = tk.Frame(parent)
            controls.pack(fill="x", padx=5, pady=5)
            tk.Button(controls, text="◀", width=3, command=lambda: self.step_frame(-1)).pack(side="left", padx=(0, 2))
            tk.Button(controls, text="▶", width=3, command=lambda: self.step_frame(1)).pack(side="left")
            self.frame_lbl = tk.Label(controls, text="Frame 1")
            self.frame_lbl.pack(side="left", padx=(10, 5))
            tk.Label(controls, text="(click preview to select index)", font=("Arial", 8)).pack(side="left")
            zf = tk.Frame(controls)
            zf.pack(side="right")
            tk.Label(zf, text="Zoom:").pack(side="left")
            zc = ttk.Combobox(zf, textvariable=self.zoom_var, values=ZOOM_LEVELS, state="readonly", width=6)
            zc.pack(side="left", padx=(5, 0))
            zc.bind("<<ComboboxSelected>>", lambda e: self.update_preview())
        canvas = tk.Canvas(parent, highlightthickness=1, highlightbackground="gray", cursor="hand2")
        canvas._cp_preview = True
        canvas.pack(fill="both", expand=True, padx=5, pady=5)
        canvas.bind("<Configure>", lambda e: self.update_preview_soon())
        self.preview = PreviewView(self.app, canvas, self.zoom_var)
        bind_pan_and_zoom(self.app, canvas, self.zoom_var, self.update_preview, self.on_preview_click)

    def _picker_panel(self, panel):
        self.active_preview = tk.Label(panel, text=" ", relief="sunken", height=2)
        self.active_preview._cp_keep = True
        self.active_preview.pack(fill="x", padx=2, pady=(2, 2))
        picker_row(panel, self).pack(fill="x", pady=(2, 2))
        sliders = tk.Frame(panel)
        sliders.pack(fill="x", pady=(4, 2))
        hsv_row(sliders, 0, "Hue", self.h_var, 0, 360, self.on_hsv_changed)
        hsv_row(sliders, 1, "Sat", self.s_var, 0, 100, self.on_hsv_changed)
        hsv_row(sliders, 2, "Val", self.v_var, 0, 100, self.on_hsv_changed)
        sc = tk.LabelFrame(panel, text="Saved Colors")
        sc.pack(fill="x", pady=(2, 0))
        SavedColorsPanel(self.app, sc, self.current_color, self.apply_color, size=26, cols=10,
                         on_after_dialog=self.lift).pack(fill="x")
        tk.Button(panel, text="Close", width=12, command=self.close).pack(pady=(8, 0))

    def build_nuage(self):
        """NuAge: the old icon editor layout, now a palette organisation skin."""
        main = ttk.Frame(self.win)
        main.pack(fill="both", expand=True, padx=10, pady=10)
        title = ttk.Frame(main)
        title.pack(fill="x", pady=(0, 5))
        self.title_lbl = ttk.Label(title, font=("Arial", 12, "bold"))
        self.title_lbl.pack(side="left")
        gear = ttk.Button(title, text="⚙", width=3)
        gear.configure(command=lambda: self._settings_menu(gear))
        gear.pack(side="right")

        # Bottom buttons are packed before the panes so a short window never hides them
        buttons = ttk.Frame(main)
        buttons.pack(side="bottom", fill="x", pady=(5, 0))
        ttk.Button(buttons, text="Export Palette", command=self.save_palette).pack(side="left", padx=(0, 10))
        self._reset_menubutton(buttons, ttk_style=True).pack(side="left", padx=(0, 10))
        ttk.Button(buttons, text="Close", command=self.close).pack(side="right")

        paned = ttk.PanedWindow(main, orient="horizontal")
        paned.pack(fill="both", expand=True)
        left = ttk.Frame(paned, padding=(0, 0, 15, 0))
        paned.add(left, weight=4)

        picker = tk.Frame(left, relief="solid", bd=1)
        picker.pack(fill="x", pady=(0, 5))
        tk.Label(picker, text="Color Picker", font=("Arial", 10, "bold")).pack(anchor="w", pady=(5, 2), padx=4)
        inner = tk.Frame(picker)
        inner.pack(fill="x", padx=4, pady=(0, 4))
        picker_row(inner, self).pack(fill="x", pady=(0, 4))
        sliders = tk.Frame(inner)
        sliders.pack(fill="x")
        hsv_row(sliders, 0, "Hue:", self.h_var, 0, 360, self.on_hsv_changed)
        hsv_row(sliders, 1, "Sat:", self.s_var, 0, 100, self.on_hsv_changed)
        hsv_row(sliders, 2, "Val:", self.v_var, 0, 100, self.on_hsv_changed)
        self.active_preview = tk.Label(inner, text=" ", relief="sunken", bd=2, width=28, height=2)
        self.active_preview._cp_keep = True
        self.active_preview.pack(pady=5)

        multi = ttk.Frame(left)
        multi.pack(fill="x", pady=(0, 5))
        ttk.Checkbutton(multi, text="Multi-select", variable=self.multi_var,
                        command=self.on_multi_toggled).pack(side="left")
        ttk.Button(multi, text="Select All", command=self.select_all).pack(side="left", padx=(10, 0))
        ttk.Button(multi, text="Clear Sel", command=self.clear_selection).pack(side="left", padx=(5, 0))
        self.count_lbl = ttk.Label(multi, text="(0 selected)")
        self.count_lbl.pack(side="left", padx=(10, 0))

        header = ttk.Frame(left)
        header.pack(fill="x", pady=(0, 2))
        ttk.Label(header, text="Palette Colors", font=("Arial", 10, "bold")).pack(side="left")
        ttk.Button(header, text="Load Palette", command=self.load_into_layer).pack(side="right", padx=(5, 0))
        ttk.Button(header, text="Save Palette", command=self.save_palette).pack(side="right", padx=(5, 0))
        holder = ttk.Frame(left)
        holder.pack(fill="both", expand=True, pady=(0, 5))
        self.swatches = swatch_grid(holder, self.editable(), 80, 5, self.on_swatch_click,
                                    on_right=lambda i, e: self.on_swatch_click(i, e, button="right"), height=290)

        right = ttk.Frame(paned)
        paned.add(right, weight=1)
        if self.show_preview():
            ttk.Label(right, text="Live Preview", font=("Arial", 10, "bold")).pack(anchor="w")
            ttk.Label(right, text="(Click to select color, scroll to zoom)", font=("Arial", 8)).pack(anchor="w")
            pv = ttk.Frame(right)
            pv.pack(fill="both", expand=True, pady=(0, 2))
            self._preview_block(pv, header=False)
            nav = ttk.Frame(right)
            nav.pack(fill="x")
            ttk.Button(nav, text="◀", width=3, command=lambda: self.step_frame(-1)).pack(side="left")
            ttk.Button(nav, text="▶", width=3, command=lambda: self.step_frame(1)).pack(side="left", padx=(2, 0))
            self.frame_lbl = ttk.Label(nav, text="Frame 1")
            self.frame_lbl.pack(side="left", padx=(8, 0))
        edit = ttk.Frame(right)
        edit.pack(fill="x", pady=(1, 1))
        ttk.Label(edit, text="Edit which:").pack(side="left")
        combo = ttk.Combobox(edit, textvariable=self.target_var, values=self._names(), state="readonly", width=30)
        combo.pack(side="left", fill="x", expand=True, padx=(5, 5))
        combo.bind("<<ComboboxSelected>>", lambda e: self.on_target_changed())
        ttk.Label(right, text="Saved Colors", font=("Arial", 10, "bold")).pack(anchor="w", pady=(2, 1))
        SavedColorsPanel(self.app, right, self.current_color, self.apply_color, size=24, cols=10, visible_rows=3,
                         on_after_dialog=self.lift).pack(fill="x")   # a row taller; the Live Preview gives it up
        self._update_title()

    def _update_title(self):
        if getattr(self, "title_lbl", None) is not None and self.title_lbl.winfo_exists():
            ly = self.layer()
            self.title_lbl.configure(text="Organising palette: %s" % (ly.name if ly else "-"))
