"""Artwork Tool: transforms, batch tools, custom brushes and resizing."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .model import Layer, flip_op, map_rgb


class TransformsMixin:
    """Rotate / flip / perspective, batch tools, custom brushes and resizing."""

    # ----- transforms & batch -----
    def _rotate_img(self, img, degrees):
        out = img.rotate(-degrees, expand=True)
        canvas = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        canvas.paste(out, ((self.W - out.width) // 2, (self.H - out.height) // 2))
        return canvas

    def rotate_layer(self, degrees):
        self.save_state("transform")
        if self.W != self.H:
            messagebox.showinfo("Rotate", "Note: Rotation requires square canvas for non-square sprites.\nConsider resizing "
                                          "to square dimensions first.", parent=self.win)
        self.layer().img = self._rotate_img(self.layer().img, degrees)
        self.changed()

    def flip_layer(self, direction):
        self.save_state("transform")
        self.layer().img = self.layer().img.transpose(flip_op(direction))
        self.changed()

    def perspective(self):
        skew = simpledialog.askfloat("📐 Perspective Transform", "Perspective skew (-1.0 to +1.0):\n\n-1.0 = Skew left\n"
                                                               "0 = No skew\n+1.0 = Skew right", initialvalue=0.5,
                                     minvalue=-1.0, maxvalue=1.0, parent=self.win)
        if skew is None:
            return
        self.save_state("transform")
        # Canvas setTransform(1, skew*0.3, 0, 1, 0, 0): y' = y + 0.3*skew*x
        img = self.layer().img
        self.layer().img = img.transform(img.size, Image.Transform.AFFINE, (1, 0, 0, -skew * 0.3, 1, 0),
                                         Image.Resampling.NEAREST)
        self.changed()

    def batch_rotate(self, degrees):
        if not messagebox.askyesno("Batch", "Rotate ALL frames by %d°?\nThis will affect all layers in all %d frames."
                                   % (degrees, len(self.frames)), parent=self.win):
            return
        self.save_state("transform")
        for layer in self.all_layers():
            layer.img = self._rotate_img(layer.img, degrees)
        self.changed()

    def batch_flip(self, direction):
        if not messagebox.askyesno("Batch", "Flip ALL frames %s?" % ("horizontal" if direction == "h" else "vertical"),
                                   parent=self.win):
            return
        self.save_state("transform")
        for layer in self.all_layers():
            layer.img = layer.img.transpose(flip_op(direction))
        self.changed()

    def batch_brightness(self):
        adj = simpledialog.askfloat("☀️ Batch Brightness", "Brightness adjustment (-1.0 to +1.0):\n\nNegative = darker, "
                                                         "Positive = brighter\n\nSuggested: -0.2 to +0.2",
                                    initialvalue=0.1, minvalue=-1.0, maxvalue=1.0, parent=self.win)
        if adj is None:
            return
        self.save_state()
        lut = [min(255, max(0, round(v * (1 + adj)))) for v in range(256)]
        for layer in self.all_layers():
            layer.img = map_rgb(layer.img, lut)
        self.changed()

    def batch_magenta(self):
        if not messagebox.askyesno("Batch", "Create/Replace Magenta Background for ALL %d frames?" % len(self.frames),
                                   parent=self.win):
            return
        self.save_state("transform")
        for fi, frame in enumerate(self.frames):
            bottom = frame[0]
            colors = bottom.img.getcolors(2)
            solid = colors is not None and len(colors) == 1 and colors[0][1][3] == 255
            if not solid:
                bottom = Layer("Magenta BG", self.W, self.H)
                frame.insert(0, bottom)
                if fi == self.cur_frame:
                    self.cur_layer += 1
            bottom.img = Image.new("RGBA", (self.W, self.H), (255, 0, 255, 255))
        self.changed()

    # ----- custom brush -----
    def create_custom_brush(self):
        size = simpledialog.askinteger("🖌️ Create Custom Brush", "Custom brush size (4-16 pixels):", initialvalue=8,
                                       minvalue=4, maxvalue=16, parent=self.win)
        if not size:
            return
        pattern = [[False] * size for _ in range(size)]
        top = self.popup()
        top.title("Custom Brush Editor (%d×%d)" % (size, size))
        tk.Label(top, text="Left click pixels to toggle ON (black) or OFF (white).", wraplength=300).pack(padx=10, pady=6)
        grid = tk.Frame(top)
        grid.pack(padx=10)
        cells = {}

        def toggle(x, y):
            pattern[y][x] = not pattern[y][x]
            cells[(x, y)].configure(bg="#000000" if pattern[y][x] else "#ffffff")

        for y in range(size):
            for x in range(size):
                c = tk.Label(grid, bg="#ffffff", width=2, height=1, relief="solid", bd=1)
                c._cp_keep = True
                c.grid(row=y, column=x)
                c.bind("<Button-1>", lambda e, x=x, y=y: toggle(x, y))
                cells[(x, y)] = c

        def save():
            self.custom_brush, self.custom_size = pattern, size
            self.shape_var.set("Custom...")
            self.set_brush_shape("custom")
            top.destroy()

        row = tk.Frame(top)
        row.pack(pady=8)
        tk.Button(row, text="Save Brush", bg="#28a745", fg="white", command=save).pack(side="left", padx=4)
        tk.Button(row, text="Cancel", bg="#dc3545", fg="white", command=top.destroy).pack(side="left", padx=4)

    def save_custom_brush(self):
        if not self.custom_brush:
            messagebox.showinfo("Custom Brush", "No custom brush to save! Create a custom brush first.", parent=self.win)
            return
        path = filedialog.asksaveasfilename(parent=self.win, defaultextension=".brush", initialfile="MyCustomBrush.brush",
                                            filetypes=[("Brush", "*.brush"), ("JSON", "*.json")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"version": "1.0", "size": self.custom_size, "pattern": self.custom_brush}, f, indent=2)

    def load_custom_brush(self):
        path = filedialog.askopenfilename(parent=self.win, filetypes=[("Brush", "*.brush *.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data.get("pattern"), list) or not 1 <= int(data.get("size", 0)) <= 32:
                raise ValueError("Invalid brush file format")
            self.custom_brush, self.custom_size = data["pattern"], int(data["size"])
            self.shape_var.set("Custom...")
            self.set_brush_shape("custom")
        except Exception as exc:
            messagebox.showerror("Custom Brush", "Error loading brush file: %s" % exc, parent=self.win)

    # ----- size / import / export -----
    def resize_sprite(self, w, h, migrate=True):
        if w == self.W and h == self.H:
            return
        self.save_state()
        for layer in self.all_layers():
            layer.img = layer.img.resize((w, h), Image.Resampling.NEAREST) if migrate else Image.new("RGBA", (w, h))
            if layer.mask is not None:
                layer.mask = layer.mask.resize((w, h), Image.Resampling.NEAREST)
        self.W, self.H = w, h
        if self.dark_grid.get() and self.link_var.get():
            self.dark_every.set(max(1, round(math.sqrt(w))))
        self.cur_layer = 0
        self.refresh_all()
