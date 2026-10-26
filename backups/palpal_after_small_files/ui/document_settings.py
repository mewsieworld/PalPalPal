"""Options > Document Settings: the document (palette size, palettes per frame, 3D heights) and the
preferences that used to sit in the gear menu (palette format, Super Swatch Switcher UI, prompts)."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.storage import UserStore
from .dialogs import Dialog, color_count_picker, show_credits


class DocumentSettingsDialog(Dialog):
    """Left: palette color count, Separate Palettes by Frames, 3D height settings. Right: preferences.
    Credits / Ok / Cancel underneath, and Reset to default settings below them."""

    def __init__(self, app):
        Dialog.__init__(self, app, "Document Settings")
        columns = tk.Frame(self.body)
        columns.pack(fill="both")
        left = tk.Frame(columns)
        left.pack(side="left", fill="y", anchor="n")
        right = tk.Frame(columns)
        right.pack(side="left", fill="y", anchor="n", padx=(16, 0))
        self._document(left)
        self._preferences(right)

        buttons = tk.Frame(self.body)
        buttons.pack(pady=(12, 0))
        tk.Button(buttons, text="Credits ♥", command=lambda: show_credits(app, self.win)).pack(side="left",
                                                                                              padx=(0, 10))
        tk.Button(buttons, text="Ok", width=12, command=self.ok).pack(side="left")
        tk.Button(buttons, text="Cancel", width=8, command=lambda: self.close(None)).pack(side="left", padx=(6, 0))
        tk.Button(self.body, text="Reset to default settings", relief="flat", fg="gray",
                  font=("Arial", 8, "underline"), command=self.defaults).pack(pady=(8, 0))
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
        tk.Label(b, text="Images with more colors than this are reduced to it (one shared palette per image).",
                 fg="gray", font=("Arial", 8)).pack(anchor="w", pady=(2, 0))
        box = tk.LabelFrame(b, text="Separate Palettes by Frames")
        box.pack(fill="x", pady=(12, 0))
        self.split = tk.StringVar(value="Y" if app.split_palettes else "N")
        row = tk.Frame(box)
        row.pack(anchor="w", padx=6, pady=4)
        tk.Radiobutton(row, text="Yes", variable=self.split, value="Y").pack(side="left")
        tk.Radiobutton(row, text="No", variable=self.split, value="N").pack(side="left", padx=(10, 0))
        tk.Label(box, text="Yes gives every frame its own palette; the Layers box gets < > tabs, one per frame.",
                 fg="gray", font=("Arial", 8)).pack(anchor="w", padx=6, pady=(0, 4))
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
        tk.Label(box, text="Palette format, %s UI, prompts and the Mass Frame Editor default\nlive here "
                           "(they used to be in Frame Settings)." % SWITCHER_NAME, fg="gray", font=("Arial", 8),
                 justify="left").pack(anchor="w", padx=4, pady=(0, 4))
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

    def defaults(self):
        d = UserStore.DEFAULTS
        self.pal_format.set(d["palette_format"])
        self.ui.set(d["live_pal_ui_mode"])
        self.excess.set(d["show_excess_prompt"])
        self.mass_default.set(d.get("mass_editor_default", False))
        self.ask_new.set(True)
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
            if needs and not messagebox.askyesno("Document Settings", "%s will be reduced to %d colors. Continue?"
                                                 % (", ".join(needs), n), parent=self.win):
                return
        s = app.store
        skin_changed = self.ui.get() != s.get("live_pal_ui_mode")
        s.data.update(palette_format=self.pal_format.get(), show_excess_prompt=self.excess.get(),
                      live_pal_ui_mode=self.ui.get(), mass_editor_default=self.mass_default.get())
        if self.ask_new.get():
            s.data["new_project_remember"] = None
        s.save()
        self.apply_heights()
        self.close(True)
        if n != self.start_size:
            app.set_palette_color_count(n)
        if split != app.split_palettes:
            app.set_split_palettes(split)
        switcher = app.switcher
        if skin_changed and switcher and switcher.win.winfo_exists():
            switcher.skin = self.ui.get()
            switcher.build()
        app.request_redraw()
