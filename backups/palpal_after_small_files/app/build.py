"""PalPalPal main window: building the UI."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..ui.docs_viewer import open_doc
from ..core.colors import to_hex
from ..ui.theme import Theme, Tooltip
from ..ui.widgets import SavedColorsPanel
from ..preview.canvas import ALIGNMENTS, PreviewView, bind_pan_and_zoom
from .boxes import AppBoxesMixin
from .view_modes import AppViewModesMixin


class AppUiMixin(AppBoxesMixin, AppViewModesMixin):
    """Builds the main window: menus, top bar, timeline and layers boxes, compact bar."""

    # ----- UI -----
    def create_ui(self):
        m = self.master
        m.geometry("1050x650")
        m.minsize(1050, 650)

        m.bind("b", lambda e: self._shortcut(self.open_bg_options))
        m.bind("e", lambda e: self._shortcut(self.export_background))
        m.bind("E", lambda e: self._shortcut(self.export_all_frames))
        m.bind("o", lambda e: self._shortcut(self.open_settings))
        m.bind("p", lambda e: self._shortcut(self.open_switcher))
        m.bind("P", lambda e: self._shortcut(self.export_palette))
        m.bind("r", lambda e: self._shortcut(self.reset_pals))
        m.bind("d", lambda e: self._shortcut(self.debug_info))
        m.bind("v", lambda e: self._shortcut(self.toggle_view_mode))
        m.bind("f", lambda e: self._shortcut(self.flip_selected_frame))
        m.bind("<Control-s>", lambda e: self.save_project())
        m.bind("<Control-n>", lambda e: self.new_project())
        m.bind("<Control-o>", lambda e: self.open_project())
        m.bind_all("<Left>", lambda e: self._arrow(-1))
        m.bind_all("<Right>", lambda e: self._arrow(1))

        menubar = tk.Menu(m)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New", accelerator="Ctrl+N", command=self.new_project)
        file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self.open_project)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_project)
        file_menu.add_command(label="Save As...", command=self.save_project_as)
        file_menu.add_separator()
        file_menu.add_command(label="Import Image as Frames...", command=self.import_frames)
        file_menu.add_command(label="Import Image as Layer...", command=self.open_images)
        file_menu.add_command(label="Import Palette...", command=self.open_palette)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.on_quit)
        menubar.add_cascade(label="File", menu=file_menu)
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label=SWITCHER_NAME, accelerator="P", command=self.open_switcher)
        edit_menu.add_command(label="Draw Layer", command=self.open_sprite_tool)
        edit_menu.add_command(label="Mass Frame Editor (img2palette)", command=self.open_mass_editor)
        edit_menu.add_command(label="Img2img Palette Swap", command=self.open_adjuster)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        export_menu = tk.Menu(menubar, tearoff=0)
        export_menu.add_command(label="Export Frame", command=self.export_frame)
        export_menu.add_command(label="Export Background", command=self.export_background)
        export_menu.add_command(label="Export Palette", command=self.export_palette)
        export_menu.add_command(label="Export All Frames", command=self.export_all_frames)
        menubar.add_cascade(label="Export", menu=export_menu)
        options_menu = tk.Menu(menubar, tearoff=0)
        options_menu.add_checkbutton(label="3D Layer View", variable=self.view_3d_var, command=self.toggle_3d)
        options_menu.add_command(label="Reset 3D View", command=self.reset_3d)
        options_menu.add_separator()
        options_menu.add_command(label="Document Settings...", command=self.open_document_settings)
        options_menu.add_command(label="BG Options...", command=self.open_bg_options)
        options_menu.add_command(label="Frame Settings...", command=self.open_settings)
        menubar.add_cascade(label="Options", menu=options_menu)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Check for Updates...", command=self.check_for_updates)
        help_menu.add_command(label="Statistics", command=self.show_statistics)
        help_menu.add_command(label="Manual", command=lambda: open_doc(self, "manual"))
        help_menu.add_command(label="Changelog", command=lambda: open_doc(self, "changelog"))
        help_menu.add_command(label="About %s" % APP_NAME, command=self.show_about)
        help_menu.add_separator()
        help_menu.add_command(label="Reset Frames", command=self.reset_frames)
        help_menu.add_command(label="Reset Pals", command=self.reset_pals)
        help_menu.add_command(label="Current Display Info", command=self.show_current_display_info)
        help_menu.add_command(label="Debug Info", command=self.debug_info)
        menubar.add_cascade(label="Help", menu=help_menu)
        m.configure(menu=menubar)
        self.menus = [file_menu, edit_menu, export_menu, options_menu, help_menu]

        main = tk.Frame(m)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        top = tk.Frame(main)
        top.pack(fill="x", pady=(0, 10))
        self.zoom_group = tk.Frame(top)
        self.zoom_group.pack(side="left")
        tk.Label(self.zoom_group, text="Zoom:").pack(side="left")
        zc = ttk.Combobox(self.zoom_group, textvariable=self.zoom_var, values=ZOOM_LEVELS, state="readonly", width=10)
        zc.pack(side="left", padx=(5, 10))
        zc.bind("<<ComboboxSelected>>", lambda e: self.request_redraw())
        # The space between Zoom and the preview dropdown holds the Align button, centred in it
        middle = tk.Frame(top)
        middle.pack(side="left", fill="x", expand=True)
        self.align_var = tk.StringVar()
        self.align_btn = tk.Menubutton(middle, relief="raised", width=12)
        align_menu = tk.Menu(self.align_btn, tearoff=0)
        for label, anchor in ALIGNMENTS:
            align_menu.add_radiobutton(label=label, value=anchor, variable=self.align_var,
                                       command=lambda a=anchor: self.set_alignment(a))
        self.align_btn.configure(menu=align_menu)
        self.align_btn.pack(anchor="center")
        Tooltip(self.align_btn, "Where the image sits on the canvas (remembered per view and frame type)", self)
        self.menus.append(align_menu)
        right = tk.Frame(top)
        right.pack(side="right", padx=(0, 10))
        vc = ttk.Combobox(right, textvariable=self.view_var, values=PREVIEW_MODES, state="readonly", width=13)
        vc.pack(side="left", padx=(0, 10))
        vc.bind("<<ComboboxSelected>>", lambda e: self.choose_view_mode())
        tk.Label(right, text="Frame Type:").pack(side="left")
        for text, value in (("Single", "single"), ("All", "all"), ("Custom", "custom")):
            tk.Radiobutton(right, text=text, variable=self.preview_var, value=value,
                           command=self.on_preview_mode_change).pack(side="left", padx=(5, 0))
        self.dark_btn = tk.Button(right, text="🌙", font=("Arial", 10), width=2, command=self.toggle_dark_mode)
        self.dark_btn.pack(side="left", padx=(6, 2))
        Tooltip(self.dark_btn, "Dark mode", self)
        gear = tk.Button(right, text="⚙", font=("Arial", 10), width=2, command=self.open_settings)
        gear.pack(side="left")
        Tooltip(gear, "Frame Settings", self)

        # A draggable divider sits between the canvas side and the timeline / layers column
        content = tk.PanedWindow(main, orient="horizontal", sashwidth=6, sashrelief="raised", bd=0)
        content.pack(fill="both", expand=True, pady=(0, 10))
        self.content_pane = content
        self.img_frame = tk.Frame(content)
        content.add(self.img_frame, minsize=320, stretch="always")
        self.scroll_frame = tk.Frame(self.img_frame, relief="solid", bd=1)
        self.scroll_frame.pack(fill="both", expand=True)
        vs = ttk.Scrollbar(self.scroll_frame, orient="vertical")
        vs.pack(side="right", fill="y")
        hs = ttk.Scrollbar(self.scroll_frame, orient="horizontal")
        hs.pack(side="bottom", fill="x")
        self.canvas = tk.Canvas(self.scroll_frame, highlightthickness=0, yscrollcommand=vs.set,
                                xscrollcommand=hs.set)
        self.canvas._cp_preview = True
        self.canvas.pack(side="left", fill="both", expand=True)
        vs.configure(command=self.canvas.yview)
        hs.configure(command=self.canvas.xview)
        self.canvas.bind("<Configure>", lambda e: self.request_redraw())
        self.view = PreviewView(self, self.canvas, self.zoom_var)
        bind_pan_and_zoom(self, self.canvas, self.zoom_var, self.request_redraw, self.on_canvas_click,
                          band=(self.band_start, self.band_move, self.band_end),
                          view=self.view, on_right_click=self.on_canvas_right_click)

        self._build_compact_bar(self.img_frame)

        control = tk.Frame(content)
        content.add(control, minsize=300, stretch="never")
        self.paned = tk.PanedWindow(control, orient="vertical", sashwidth=4, sashrelief="raised")
        self.paned.pack(fill="both", expand=True)
        self.paned.bind("<Configure>", lambda e: self.master.after_idle(self.align_saved_colors_sash))
        # Dragging the divider can't stretch Saved Colors past its slots
        self.paned.bind("<B1-Motion>", lambda e: self.master.after_idle(self.clamp_saved_colors), add="+")
        self.paned.bind("<ButtonRelease-1>", lambda e: self.master.after_idle(self.clamp_saved_colors), add="+")
        self._build_timeline_box()
        self._build_layers_box()
        self.saved_box = tk.LabelFrame(self.paned, text="Saved Colors")
        SavedColorsPanel(self, self.saved_box, self.compact.current_color, self.compact.apply_color,
                         size=24, cols=10, visible_rows=3).pack(fill="x")

        self.bottom_bar = tk.Frame(main, height=40)
        self.bottom_bar.pack(fill="x", pady=(10, 0))
        self.nav_group = tk.Frame(self.bottom_bar)
        tk.Button(self.nav_group, text="◀", width=3, command=lambda: self.step_frame(-1)).pack(side="left", padx=(0, 2))
        tk.Button(self.nav_group, text="▶", width=3, command=lambda: self.step_frame(1)).pack(side="left")
        self.frame_lbl = tk.Label(self.nav_group, text="No frames")
        self.frame_lbl.pack(side="left", padx=(6, 8))
        fb = tk.Button(self.nav_group, text="Flip", width=4, command=self.toggle_flip)
        fb.pack(side="left", padx=(0, 2))
        Tooltip(fb, "Flip image horizontally", self)
        rb = tk.Button(self.nav_group, text="Rot 90°", width=6, command=self.rotate_preview)
        rb.pack(side="left")
        Tooltip(rb, "Rotate image 90°", self)
        self.bg_options_btn = tk.Button(self.bottom_bar, text="BG Options", command=self.open_bg_options)
        self.bg_options_btn._cp_keep = True
        self.update_bottom_bar()

    def update_bottom_bar(self):
        """Frame/flip row only in Big Preview; BG Options button unless it was moved to the Options menu."""
        self.nav_group.pack_forget()
        self.bg_options_btn.pack_forget()
        if self.view_var.get() == "Big Preview":
            self.nav_group.pack(side="left")
        if not self.store.get("bg_options_in_menu"):
            self.bg_options_btn.pack(side="right")
            # The button wears the BG color, as the old 🎨 button did
            if self.bg_color is None:
                c = Theme.colors(self)
                self.bg_options_btn.configure(bg=c["button"], activebackground=c["hover"], fg=c["fg"])
            else:
                self.bg_options_btn.configure(bg=to_hex(self.bg_color), activebackground=to_hex(self.bg_color),
                                              fg="black" if sum(self.bg_color) > 380 else "white")

    def update_title(self):
        name = os.path.splitext(os.path.basename(self.project_path))[0] if self.project_path else (
            "Untitled" if self.stack else "")
        title = APP_NAME + (" (%s)" % BUILD_LABEL if BUILD_LABEL else "") + (" - " + name if name else "") + (
            " *" if self.dirty else "")
        self.master.title(title)

    def mark_dirty(self):
        if not self.dirty:
            self.dirty = True
            self.update_title()

    def _shortcut(self, func):
        if isinstance(self.master.focus_get(), (tk.Entry, ttk.Entry, ttk.Combobox)):
            return
        func()

    def _arrow(self, step):
        focus = self.master.focus_get()
        if isinstance(focus, (tk.Entry, ttk.Entry, ttk.Combobox)):
            return
        if focus is not None and focus.winfo_toplevel() is not self.master:
            return
        self.step_frame(step)
