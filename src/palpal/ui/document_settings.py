"""Options > Document & 3D Settings: the document (palette size, palettes per frame, 3D heights) and the
preferences that used to sit in the gear menu (palette format, Super Swatch Switcher UI, prompts)."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.storage import UserStore
from .dialogs import Dialog
from .theme import hint, set_hints_shown
from .settings_dialog import show_credits
from .new_project import color_count_picker


class DocumentSettingsDialog(Dialog):
    """Left: palette color count, Separate Palettes by Frames, 3D height settings. Right: preferences.
    Credits / Ok / Cancel underneath, and Reset to default settings below them."""

    def __init__(self, app):
        Dialog.__init__(self, app, "Document & 3D Settings")
        # Seven columns across the window: 1-3 are the document column, 5-7 the preferences column and
        # 4 is the divider between them. The buttons sit centered in #1, #3, #5 and #7.
        g = self.body
        left = tk.Frame(g)
        left.grid(row=0, column=0, columnspan=3, sticky="nw")
        ttk.Separator(g, orient="vertical").grid(row=0, column=3, sticky="ns", padx=12)
        right = tk.Frame(g)
        right.grid(row=0, column=4, columnspan=3, sticky="nw")
        self._document(left)
        self._preferences(right)
        for col in (0, 1, 2, 4, 5, 6):
            g.grid_columnconfigure(col, weight=1, uniform="half")
        tk.Button(g, text="Credits ♥", width=10, command=lambda: show_credits(app, self.win)).grid(
            row=1, column=0, pady=(14, 0))
        tk.Button(g, text="Ok", width=10, command=self.ok).grid(row=1, column=2, pady=(14, 0))
        from ..app.cache import clear_cache
        tk.Button(g, text="Clear Cache", width=10, command=lambda: clear_cache(app, self.win)).grid(
            row=1, column=4, pady=(14, 0))
        tk.Button(g, text="Close", width=10, command=lambda: self.close(None)).grid(row=1, column=6, pady=(14, 0))
        tk.Button(g, text="Reset to default settings", relief="flat", fg="gray",
                  font=("Arial", 8, "underline"), command=self.defaults).grid(row=2, column=0, columnspan=7,
                                                                             pady=(8, 0))
        self.finish()

    # ----- the document -----
    def _document(self, b):
        app = self.app
        sizes = [p.size for p in app.all_palettes()] or [PALETTE_SIZE]
        self.start_size = max(sizes)
        self.count = tk.IntVar(value=self.start_size)
        self.count_text = tk.StringVar(value=str(self.start_size))
        self.typed = color_count_picker(b, self.count, self.count_text,
                                        lambda: self.count_text.set(str(self.count.get())))
        hint(tk.Label(b, text="Images with more colors than this are reduced to it (one shared palette per image).",
                      fg="gray", font=("Arial", 8)), anchor="w", pady=(2, 0))
        box = tk.LabelFrame(b, text="Separate Palettes by Frames")
        box.pack(fill="x", pady=(12, 0))
        self.split = tk.StringVar(value="Y" if app.split_palettes else "N")
        row = tk.Frame(box)
        row.pack(anchor="w", padx=6, pady=4)
        tk.Radiobutton(row, text="Yes", variable=self.split, value="Y").pack(side="left")
        tk.Radiobutton(row, text="No", variable=self.split, value="N").pack(side="left", padx=(10, 0))
        hint(tk.Label(box, text="Yes gives every frame its own palette; the Layers box gets < > tabs, one per frame.",
                      fg="gray", font=("Arial", 8)), anchor="w", padx=6, pady=(0, 4))
        from ..preview.heights import height_settings_section
        self.apply_heights = height_settings_section(b, app)

    # ----- preferences (from the gear menu) -----
    def _preferences(self, b):
        s = self.app.store
        tk.Label(b, text="Preferences", font=("Arial", 11, "bold")).pack(anchor="w")
        self.pal_format = tk.StringVar(value=s.get("palette_format"))
        box = tk.LabelFrame(b, text="Palette Format")
        box.pack(fill="x", pady=(6, 0))
        row = tk.Frame(box)
        row.pack(fill="x")
        for text, value in (("PAL", "pal"), ("PNG Grid", "png"), ("Both", "both")):
            tk.Radiobutton(row, text=text, variable=self.pal_format, value=value).pack(side="left", padx=4)
        hint(tk.Label(box, text="Palette format, %s UI, prompts and the Mass Frame Editor default\nlive here "
                                "(they used to be in Frame Settings)." % SWITCHER_NAME, fg="gray", font=("Arial", 8),
                      justify="left"), anchor="w", padx=4, pady=(0, 4))
        self.ui = tk.StringVar(value=s.get("live_pal_ui_mode"))
        box = tk.LabelFrame(b, text="%s UI" % SWITCHER_NAME)
        box.pack(fill="x", pady=(8, 0))
        for name in SKINS:
            tk.Radiobutton(box, text=name, variable=self.ui, value=name).pack(side="left", padx=4)
        self.excess = tk.BooleanVar(value=bool(s.get("show_excess_prompt")))
        tk.Checkbutton(b, text="Show Excess Colors Prompts", variable=self.excess).pack(anchor="w", pady=(8, 0))
        self.mass_default = tk.BooleanVar(value=bool(s.get("mass_editor_default")))
        tk.Checkbutton(b, text="Edit palettes in the Mass Frame Editor by default",
                       variable=self.mass_default).pack(anchor="w")
        self.ask_new = tk.BooleanVar(value=not s.get("new_project_remember"))
        tk.Checkbutton(b, text="Ask the New Project questions", variable=self.ask_new).pack(anchor="w")
        self.debug = tk.BooleanVar(value=bool(s.get("show_debug_menu")))
        tk.Checkbutton(b, text="Show debug options under Help", variable=self.debug).pack(anchor="w")
        self.hints = tk.BooleanVar(value=not s.get("hide_hints"))
        tk.Checkbutton(b, text="Show helpful hints (the grey how-to lines)", variable=self.hints).pack(anchor="w")

    def defaults(self):
        d = UserStore.DEFAULTS
        self.pal_format.set(d["palette_format"])
        self.ui.set(d["live_pal_ui_mode"])
        self.excess.set(d["show_excess_prompt"])
        self.mass_default.set(d.get("mass_editor_default", False))
        self.ask_new.set(True)
        self.debug.set(False)
        self.hints.set(True)
        self.split.set("N")
        self.apply_heights.reset()
        # The palette size is left as it is: lowering it would change the images

    def ok(self):
        self.typed()
        app = self.app
        n = self.count.get()
        split = self.split.get() == "Y"
        if n != self.start_size:
            needs = [il.name for il in app.image_layers()
                     if len({i for f in il.frames for i in f.used_indices()}) > n]
            if needs and not messagebox.askyesno("Document & 3D Settings", "%s will be reduced to %d colors. Continue?"
                                                 % (", ".join(needs), n), parent=self.win):
                return
        s = app.store
        skin_changed = self.ui.get() != s.get("live_pal_ui_mode")
        s.data.update(palette_format=self.pal_format.get(), show_excess_prompt=self.excess.get(),
                      live_pal_ui_mode=self.ui.get(), mass_editor_default=self.mass_default.get(),
                      show_debug_menu=self.debug.get(), hide_hints=not self.hints.get())
        set_hints_shown(self.hints.get())
        if self.ask_new.get():
            s.data["new_project_remember"] = None
        s.save()
        self.apply_heights()
        self.close(True)
        if n != self.start_size:
            app.set_palette_color_count(n)
        if split != app.split_palettes:
            app.set_split_palettes(split)
        app.fill_help_menu()
        switcher = app.switcher
        if skin_changed and switcher and switcher.win.winfo_exists():
            switcher.skin = self.ui.get()
            switcher.build()
        app.request_redraw()
