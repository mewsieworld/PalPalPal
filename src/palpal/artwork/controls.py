"""Artwork Tool: tools, brush, colors and keyboard shortcuts."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .look import button_color, round_button
from .look import TOOL_GROUP_COLORS
from .model import hex_to_rgba, rgba_hex


class ControlsMixin:
    """Artwork Tool: tools, brush, colors and keyboard shortcuts."""

    # ----- tools -----
    def tool_action(self, tool):
        actions = {"@curves": self.color_curves, "@clearsel": self.clear_selection, "@clearframe": self.clear_frame,
                   "@swap": self.toggle_swap, "@remap": self.toggle_remap, "@rot90": lambda: self.rotate_layer(90),
                   "@rot-90": lambda: self.rotate_layer(-90), "@fliph": lambda: self.flip_layer("h"),
                   "@flipv": lambda: self.flip_layer("v"), "@persp": self.perspective, "@undoxform": self.undo_transformations,
                   "@brot": lambda: self.batch_rotate(90), "@bfliph": lambda: self.batch_flip("h"),
                   "@bflipv": lambda: self.batch_flip("v"), "@bbright": self.batch_brightness,
                   "@bmagenta": self.batch_magenta}
        if tool in actions:
            actions[tool]()
        else:
            self.activate_tool(tool)

    def activate_tool(self, tool):
        self.tool = tool
        self.shape_points, self.line_start, self.curve_points = [], None, []
        self.circle_center, self.shape_start = None, None
        self.set_status(TOOL_MESSAGES.get(tool, ""))
        for t, b in self.tool_buttons.items():
            b._selected = t == tool   # the active tool gets a dark ring around its rounded button
            round_button(b, button_color(b), b._selected)
        for row in (self.secondary_row, self.grad_row, self.pattern_row, self.sym_row, self.shape_row):
            row.pack_forget()
        if tool in ("gradient", "dither", "pattern"):
            self.secondary_row.pack(fill="x", before=self.options_anchor)
        if tool == "gradient":
            self.grad_row.pack(fill="x", before=self.options_anchor)
        if tool == "pattern":
            self.pattern_row.pack(fill="x", before=self.options_anchor)
        if tool == "symmetrical":
            self.sym_row.pack(fill="x", before=self.options_anchor)
        if tool in ("rectangle", "circle", "polygon"):
            self.shape_row.pack(fill="x", before=self.options_anchor)
        # 1px tool locks the brush to 1x1 and gives the old size back afterwards
        if tool == "refined":
            if self.saved_size is None:
                self.saved_size = self.brush_size
            self.brush_size = 1
            self.size_scale.configure(state="disabled")
        else:
            self.size_scale.configure(state="disabled" if self.tilemap.get() else "normal")
            if self.saved_size is not None:
                self.brush_size = self.saved_size
                self.size_var.set(self.saved_size)
                self.saved_size = None
        self.canvas.configure(cursor="fleur" if tool == "pan" else "crosshair")
        self.update_tool_display()
        self.draw_brush_preview()
        self.redraw_overlay()

    def update_tool_display(self):
        name = TOOL_NAMES.get(self.tool, self.tool)
        if self.selection:
            kind = self.selection.get("kind", "Rectangle")
            name += " + %s Selection" % kind
        if self.mask_mode:
            name += " (mask)"
        self.tool_lbl.configure(text=name, bg="#fff3cd" if self.mask_mode else self.colors.get("bg", "#F0F0F0"))

    def set_brush_size(self, n):
        if self.tool == "refined":
            return
        self.brush_size = n
        self.size_lbl.configure(text="Size %dx%d" % (n, n))
        self.draw_brush_preview()

    def set_brush_shape(self, shape):
        self.brush_shape = shape
        if shape == "custom":
            self.custom_row.grid(row=2, column=0, columnspan=2, sticky="w")
        else:
            self.custom_row.grid_forget()
        self.draw_brush_preview()

    def brush_offsets(self, size, shape_on):
        """(dx, dy) cells a brush covers, with the same shape rules as drawPixelCore."""
        half = size // 2
        cells = []
        for yo in range(size):
            for xo in range(size):
                rx, ry = xo - half, yo - half
                if shape_on and size > 1:
                    s = self.brush_shape
                    if s == "circle" and math.sqrt(rx * rx + ry * ry) > size / 2 - 0.25:
                        continue
                    if s == "plus" and rx != 0 and ry != 0:
                        continue
                    if s == "x" and abs(rx) != abs(ry):
                        continue
                    if s == "diamond" and abs(rx) + abs(ry) > half:
                        continue
                    if s == "star" and rx != 0 and ry != 0 and abs(rx) != abs(ry):
                        continue
                    if s == "custom":
                        if not self.custom_brush:
                            continue
                        ch = self.custom_size // 2
                        cx, cy = xo - half + ch, yo - half + ch
                        if not (0 <= cx < self.custom_size and 0 <= cy < self.custom_size) or not self.custom_brush[cy][cx]:
                            continue
                cells.append((rx, ry))
        return cells

    def draw_brush_preview(self):
        """The current brush, drawn under the tool name (Mew's layout)."""
        c = self.brush_canvas
        c.delete("all")
        size = 1 if self.tool == "refined" else self.brush_size
        shape_on = self.tool in ("pencil", "eraser", "jumble") and self.brush_shape != "square"
        cells = self.brush_offsets(size, shape_on)
        cell = max(2, min(8, 36 // max(1, size)))
        cx, cy = 48, 20
        for dx, dy in cells:
            c.create_rectangle(cx + dx * cell - cell // 2, cy + dy * cell - cell // 2,
                               cx + dx * cell + cell // 2, cy + dy * cell + cell // 2, fill=self.color, outline="")
        self.brush_lbl.configure(text="Brush %dx%d %s" % (size, size, dict(BRUSH_SHAPES).get(self.brush_shape, "")))

    # ----- colours -----
    def set_color(self, text):
        c = hex_to_rgba(text)
        if c is None:
            return
        self.color = rgba_hex(c)
        self.color_entry.delete(0, "end")
        self.color_entry.insert(0, self.color)
        self.color_btn.configure(bg=self.color, activebackground=self.color)
        self.add_recent(self.color)
        self.draw_brush_preview()

    def set_color2(self, text):
        c = hex_to_rgba(text)
        if c is None:
            return
        self.color2 = rgba_hex(c)
        self.color2_entry.delete(0, "end")
        self.color2_entry.insert(0, self.color2)
        self.color2_btn.configure(bg=self.color2, activebackground=self.color2)

    def pick_primary(self):
        r = self.askcolor(color=self.color, parent=self.win, title="Primary color")
        if r and r[1]:
            self.set_color(r[1])

    def pick_secondary(self):
        r = self.askcolor(color=self.color2, parent=self.win, title="Secondary color")
        if r and r[1]:
            self.set_color2(r[1])

    def add_recent(self, hexcolor):
        self.recent = [hexcolor] + [c for c in self.recent if c != hexcolor]
        del self.recent[MAX_RECENT:]
        for w in self.recent_frame.winfo_children():
            w.destroy()
        for n, c in enumerate(self.recent):
            b = tk.Label(self.recent_frame, bg=c, width=2, relief="solid", bd=1, cursor="hand2")
            b.grid(row=n // 8, column=n % 8, padx=1, pady=1)
            b.bind("<Button-1>", lambda e, col=c: self.set_color(col))

    def pick_from_image(self):
        path = filedialog.askopenfilename(parent=self.win, title="Pick color from image",
                                          filetypes=IMAGE_TYPES)
        if not path:
            return
        img = Image.open(path).convert("RGB")
        scale = min(1.0, 600.0 / max(img.size))
        shown = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))))
        top = self.popup()
        top.title("Click on image to pick color (Esc to cancel)")
        photo = ImageTk.PhotoImage(shown)
        lbl = tk.Label(top, image=photo, cursor="crosshair")
        lbl.photo = photo
        lbl.pack()

        def pick(e):
            c = shown.getpixel((min(e.x, shown.width - 1), min(e.y, shown.height - 1)))
            self.set_color(rgba_hex(c))
            top.destroy()

        lbl.bind("<Button-1>", pick)
        top.bind("<Escape>", lambda e: top.destroy())

    # ----- keys -----
    def on_key(self, event):
        if isinstance(self.win.focus_get(), (tk.Entry, ttk.Entry, ttk.Combobox, tk.Spinbox)):
            return
        key = (event.keysym or "").lower()
        ctrl = bool(event.state & 0x0004)
        shift = bool(event.state & 0x0001)
        if key == "return" and self.tool == "gradientmesh":
            self.fill_mesh()
            return
        if key == "escape":
            if self.tool == "gradientmesh":
                self.mesh_points = []
                self.set_status("Gradient mesh cancelled")
            elif self.tool == "beziercurve":
                self.bezier_points = []
                self.set_status("Bezier curve cancelled")
            self.redraw_overlay()
            return
        if ctrl and key == "z":
            self.undo()
        elif ctrl and key == "y":
            self.redo()
        elif shift and key == "a":
            self.clear_selection()
        elif shift and key == "l":
            self.add_layer()
        elif shift and key == "f":
            self.add_frame("blank")
        elif shift and key == "p":
            self.export_sheet()
        elif shift and key == "b":
            self.export_bmp_frames()
        elif shift and key == "g":
            self.export_gif()
        elif shift and key == "e":
            self.export_vga_palette()
        elif not ctrl and not shift and key in SHORTCUT_TOOLS:
            self.activate_tool(SHORTCUT_TOOLS[key])

    def show_shortcuts(self):
        lines = ["TOOLS: " + ", ".join("%s = %s" % (k.upper(), TOOL_NAMES.get(t, t)) for k, t in SHORTCUT_TOOLS.items()),
                 "", "ACTIONS: Shift+A clear selection · Shift+L add layer · Shift+F add frame · Shift+P export PNG · "
                 "Shift+B export BMP · Shift+G export GIF · Shift+E export VGA palette",
                 "", "UNDO/REDO: Ctrl+Z / Ctrl+Y", "", "Gradient mesh: Enter fills, Esc cancels."]
        messagebox.showinfo("⌨️ Keyboard Shortcuts", "\n".join(lines), parent=self.win)
