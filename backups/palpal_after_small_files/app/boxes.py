"""PalPalPal main window: the Timeline and Layers boxes and the compact bar."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..ui.docs_viewer import open_doc
from ..core.colors import to_hex
from ..ui.theme import Theme, Tooltip
from ..ui.widgets import SavedColorsPanel
from ..preview.canvas import ALIGNMENTS, PreviewView, bind_pan_and_zoom


class AppBoxesMixin:
    """PalPalPal main window: the Timeline and Layers boxes and the compact bar."""

    def _build_timeline_box(self):
        """Play / pause, a snapping scrub slider, speed, loop, and the frame tools (the old Hair box spot)."""
        box = tk.LabelFrame(self.paned, text="Timeline", width=450)
        self.paned.add(box, minsize=118, stretch="never")
        row = tk.Frame(box)
        row.pack(fill="x", padx=4, pady=(4, 2))
        for text, tip, command in (("⏮", "First frame", lambda: self.jump_frame(0)),
                                   ("◀", "Previous frame", lambda: self.step_frame(-1)),
                                   (None, None, None),
                                   ("▶", "Next frame", lambda: self.step_frame(1)),
                                   ("⏭", "Last frame", lambda: self.jump_frame(-1))):
            if text is None:
                self.play_btn = tk.Button(row, text="⏵ Play", width=7, command=self.toggle_playback)
                self.play_btn.pack(side="left", padx=2)
                continue
            b = tk.Button(row, text=text, width=3, command=command)
            b.pack(side="left", padx=1)
            Tooltip(b, tip, self)
        self.layer_vis_btn = tk.Button(row, text="Hide Layer", width=9, command=self.toggle_selected_layer)
        self.layer_vis_btn.pack(side="left", padx=(4, 0))
        Tooltip(self.layer_vis_btn, "Show or hide the selected layer", self)
        self.speed_var = tk.StringVar(value=self.store.get("anim_speed") or "1x")
        speed = ttk.Combobox(row, textvariable=self.speed_var, values=["0.25x", "0.5x", "1x", "2x", "4x"],
                             state="readonly", width=5)
        speed.pack(side="right")
        speed.bind("<<ComboboxSelected>>", lambda e: self.store.set("anim_speed", self.speed_var.get()))
        tk.Label(row, text="Speed").pack(side="right", padx=(0, 3))
        scrub = tk.Frame(box)
        scrub.pack(fill="x", padx=4)
        self.scrub_var = tk.IntVar(value=1)
        self.scrub = tk.Scale(scrub, from_=1, to=1, orient="horizontal", variable=self.scrub_var, showvalue=False,
                              resolution=1, sliderrelief="flat", sliderlength=14, width=10, bd=0,
                              highlightthickness=0, command=lambda *_: self.on_scrub())
        self.scrub.pack(side="left", fill="x", expand=True)
        self.timeline_lbl = tk.Label(scrub, text="0 / 0", width=12)
        self.timeline_lbl.pack(side="left")
        tools = tk.Frame(box)
        tools.pack(fill="x", padx=4, pady=(2, 4))
        frame_tools = [("Copy", self.copy_frame), ("Paste", self.paste_frame), ("Delete", self.delete_frame),
                       ("Add Blank", self.add_blank_frame), ("Clone", self.clone_frame), ("Set Loop", self.set_loop_point)]
        for n, (label, command) in enumerate(frame_tools):
            b = tk.Button(tools, text=label, font=("Arial", 8), command=command)
            b.grid(row=n // 3, column=n % 3, sticky="we", padx=1, pady=1)
            if label == "Set Loop":
                self.loop_btn = b
        for c in range(3):
            tools.grid_columnconfigure(c, weight=1)
        add = tk.Button(tools, text="+ Frames", font=("Arial", 8), command=self.import_frames)
        add.grid(row=0, column=3, rowspan=2, sticky="ns", padx=(4, 0), pady=1)
        Tooltip(add, "Import an image as new frames of the selected layer", self)

    def _build_layers_box(self):
        box = tk.LabelFrame(self.paned, text="Layers", width=450)
        self.paned.add(box, minsize=120, stretch="always")
        tools = tk.Frame(box)
        tools.pack(fill="x", padx=4, pady=4)
        new = tk.Menubutton(tools, text="New ▾", relief="raised")
        new_menu = tk.Menu(new, tearoff=0)
        new_menu.add_command(label="Image Layer...", command=self.open_images)
        new_menu.add_command(label="Palette Layer", command=self.new_palette_layer)
        new_menu.add_command(label="Draw Pixel Layer", command=self.open_sprite_tool)
        new.configure(menu=new_menu)
        new.pack(side="left")
        self.menus.append(new_menu)
        Tooltip(new, "Image Layer: import an image (it comes in with its palette). Palette Layer: a new palette "
                     "over the selected layer. Draw Pixel Layer: open the Artwork Tool.", self)
        # Frame tabs, only while palettes are separated by frames
        self.tab_row = tk.Frame(box)
        tk.Button(self.tab_row, text="<", width=2, command=lambda: self.set_palette_tab(self.palette_tab - 1)).pack(
            side="left")
        self.tab_lbl = tk.Label(self.tab_row, text="", font=("Arial", 9, "bold"))
        self.tab_lbl.pack(side="left", expand=True)
        tk.Button(self.tab_row, text=">", width=2, command=lambda: self.set_palette_tab(self.palette_tab + 1)).pack(
            side="right")
        tk.Button(tools, text="▲", width=2, command=lambda: self.move_layer(1)).pack(side="right")
        tk.Button(tools, text="▼", width=2, command=lambda: self.move_layer(-1)).pack(side="right", padx=(0, 2))
        tk.Button(tools, text="Remove", command=self.remove_layer).pack(side="right", padx=(0, 6))
        holder = tk.Frame(box)
        holder.pack(fill="both", expand=True, padx=4, pady=4)
        sb = ttk.Scrollbar(holder, orient="vertical")
        sb.pack(side="right", fill="y")
        self.layer_canvas_widget = tk.Canvas(holder, highlightthickness=0, yscrollcommand=sb.set, height=120)
        self.layer_canvas_widget.pack(side="left", fill="both", expand=True)
        sb.configure(command=self.layer_canvas_widget.yview)
        self.layer_rows = tk.Frame(self.layer_canvas_widget)
        win = self.layer_canvas_widget.create_window((0, 0), window=self.layer_rows, anchor="nw")
        self.layer_rows.bind("<Configure>", lambda e: self.layer_canvas_widget.configure(
            scrollregion=self.layer_canvas_widget.bbox("all")))
        self.layer_canvas_widget.bind("<Configure>", lambda e: self.layer_canvas_widget.itemconfigure(
            win, width=e.width))

    def _build_compact_bar(self, parent):
        self.compact_bar = tk.Frame(parent, relief="raised", bd=2)
        self.compact_row = row = tk.Frame(self.compact_bar)
        row.pack(side="top", fill="x", padx=5, pady=(5, 2))
        tk.Button(row, text="◀", width=3, command=lambda: self.step_frame(-1)).pack(side="left", padx=2)
        tk.Button(row, text="▶", width=3, command=lambda: self.step_frame(1)).pack(side="left", padx=2)
        eye = tk.Button(row, text="👁", width=3, command=self.toggle_all_frames_visibility)
        eye.pack(side="left", padx=2)
        Tooltip(eye, "Toggle All Frames' Visibility", self)
        tk.Button(row, text="Flip", width=4, command=self.toggle_flip).pack(side="left", padx=2)
        tk.Button(row, text="Rot", width=3, command=self.rotate_preview).pack(side="left", padx=2)
        undo = tk.Button(row, text="↶", width=3, command=self.undo_frame_visibility)
        undo.pack(side="left", padx=2)
        Tooltip(undo, "Undo Frame Visibility", self)
        self.compact_frame_lbl = tk.Label(row, text="")
        self.compact_frame_lbl.pack(side="left", padx=6)
        emb = tk.Menubutton(row, text="Export", relief="raised", width=8)
        em = tk.Menu(emb, tearoff=0)
        em.add_command(label="Background", command=self.export_background)
        em.add_command(label="Pal", command=self.export_palette)
        emb.configure(menu=em)
        emb.pack(side="right", padx=2)
        self.menus.append(em)
        tk.Checkbutton(row, text="Multi", variable=self.compact.multi_var, font=("Arial", 8)).pack(side="right", padx=2)
        tk.Button(row, text="None", width=4, font=("Arial", 8), command=self.compact.clear).pack(side="right", padx=1)
        tk.Button(row, text="All", width=4, font=("Arial", 8), command=self.compact.select_all).pack(side="right", padx=1)

        self.compact_holder = tk.Frame(self.compact_bar)
        self.compact_holder.pack(side="top", fill="both", expand=True, padx=5, pady=(2, 5))
        self.resize_handle = tk.Frame(self.compact_holder, bg="gray", height=5, cursor="sb_v_double_arrow")
        self.resize_handle._cp_keep = True
        self.resize_handle.pack(side="top", fill="x")
        self.resize_handle.bind("<Button-1>", self._resize_start)
        self.resize_handle.bind("<B1-Motion>", self._resize_drag)
        self.active_colors_height = 200
        self.active_colors_frame = tk.Frame(self.compact_holder, relief="sunken", bd=1, height=self.active_colors_height)
        self.active_colors_frame.pack(side="top", fill="both", expand=True)

    def _resize_start(self, event):
        self._resize_y, self._resize_h = event.y_root, self.active_colors_height

    def _resize_drag(self, event):
        self.active_colors_height = max(120, min(300, self._resize_h - (event.y_root - self._resize_y)))
        self.active_colors_frame.configure(height=self.active_colors_height)
        self.align_saved_colors_sash()

    def align_saved_colors_sash(self):
        """Place the Layers / Saved Colors divider.

        In Small Preview it lines up with the Active Colors (Sort) row; everywhere, the Saved Colors box is
        never allowed to grow past the bottom of its own slots.
        """
        if len(self.paned.panes()) < 2 or str(self.saved_box) not in [str(p) for p in self.paned.panes()]:
            return
        self.master.update_idletasks()
        lowest_y = self.paned.winfo_height() - self.saved_box.winfo_reqheight() - int(self.paned.cget("sashwidth"))
        last = len(self.paned.panes()) - 2
        y = self.paned.sash_coord(last)[1]
        header = getattr(self.compact, "header", None)
        if self.view_var.get() == "Small Preview" and header is not None and header.winfo_exists():
            y = header.winfo_rooty() - self.paned.winfo_rooty()
        y = max(120, y, lowest_y)
        if y != self.paned.sash_coord(last)[1]:
            self.paned.sash_place(last, 0, y)

    def clamp_saved_colors(self):
        if len(self.paned.panes()) < 2 or str(self.saved_box) not in [str(p) for p in self.paned.panes()]:
            return
        lowest_y = self.paned.winfo_height() - self.saved_box.winfo_reqheight() - int(self.paned.cget("sashwidth"))
        last = len(self.paned.panes()) - 2
        if self.paned.sash_coord(last)[1] < lowest_y:
            self.paned.sash_place(last, 0, lowest_y)
