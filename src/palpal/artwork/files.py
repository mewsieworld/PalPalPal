"""Artwork Tool: imports, projects, exports, workspace and autosave."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .model import Layer, hex_to_rgba, rgba_hex


class FilesMixin:
    """Imports, project files, exports, workspace, autosave and recovery."""

    def import_reference(self):
        path = filedialog.askopenfilename(parent=self.win, filetypes=IMAGE_TYPES)
        if not path:
            return
        img = Image.open(path).convert("RGBA")
        scale = min(1.0, 600.0 / max(img.size))
        shown = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))))
        aspect = self.W / float(self.H)
        top = self.popup()
        top.title("Crop Reference Image")
        tk.Label(top, text="Drag to select region. Aspect ratio is locked to sprite size.", fg="gray").pack(pady=4)
        cv = tk.Canvas(top, width=shown.width, height=shown.height, highlightthickness=0, cursor="crosshair")
        cv.pack(padx=10)
        photo = ImageTk.PhotoImage(shown)
        cv.photo = photo
        cv.create_image(0, 0, image=photo, anchor="nw")
        box = {"x": 0, "y": 0, "w": min(shown.width, shown.height * aspect), "h": min(shown.height, shown.width / aspect)}
        start = {}

        def draw():
            cv.delete("box")
            cv.create_rectangle(box["x"], box["y"], box["x"] + box["w"], box["y"] + box["h"], outline="#2196f3", width=2,
                                tags="box")

        def press(e):
            start["x"], start["y"] = e.x, e.y

        def drag(e):
            nw, nh = e.x - start["x"], e.y - start["y"]
            if nh == 0 or abs(nw) / max(1e-6, abs(nh)) > aspect:
                nh = math.copysign(abs(nw) / aspect, nh or 1)
            else:
                nw = math.copysign(abs(nh) * aspect, nw or 1)
            box.update(x=min(start["x"], start["x"] + nw), y=min(start["y"], start["y"] + nh), w=abs(nw), h=abs(nh))
            draw()

        cv.bind("<ButtonPress-1>", press)
        cv.bind("<B1-Motion>", drag)

        def apply():
            sx, sy, sw, sh = box["x"] / scale, box["y"] / scale, max(1, box["w"] / scale), max(1, box["h"] / scale)
            crop = img.crop((int(sx), int(sy), int(sx + sw), int(sy + sh))).resize((self.W, self.H), Image.Resampling.LANCZOS)
            self.save_state()
            layer = Layer("Ref Image", self.W, self.H, crop)
            layer.opacity = 0.5
            self.layers().insert(self.cur_layer + 1, layer)
            self.cur_layer += 1
            top.destroy()
            self.changed()

        row = tk.Frame(top)
        row.pack(pady=8)
        tk.Button(row, text="Import as New Layer", bg="#4CAF50", fg="white", command=apply).pack(side="left", padx=4)
        tk.Button(row, text="Cancel", bg="#f44336", fg="white", command=top.destroy).pack(side="left", padx=4)
        draw()

    def import_sprite_sheet(self):
        path = filedialog.askopenfilename(parent=self.win, filetypes=IMAGE_TYPES)
        if not path:
            return
        img = Image.open(path).convert("RGBA")
        fw = simpledialog.askinteger("📥 Import Sprite Sheet", "Sprite sheet loaded: %dx%d\n\nEnter frame width (pixels):"
                                     % img.size, initialvalue=self.W, minvalue=1, parent=self.win)
        if not fw:
            return
        fh = simpledialog.askinteger("📥 Frame Height", "Enter frame height (pixels):", initialvalue=self.H, minvalue=1,
                                     parent=self.win)
        if not fh:
            return
        cols, rows = img.width // fw, img.height // fh
        if not cols or not rows:
            messagebox.showerror("Import", "Invalid frame dimensions!", parent=self.win)
            return
        if not messagebox.askyesno("Import", "This will import %d frames (%d columns x %d rows)\nFrame size: %dx%d\n\n"
                                             "Continue?" % (cols * rows, cols, rows, fw, fh), parent=self.win):
            return
        self.save_state()
        self.W, self.H = fw, fh
        self.frames = [[Layer("Layer 1", fw, fh, img.crop((c * fw, r * fh, (c + 1) * fw, (r + 1) * fh)))]
                       for r in range(rows) for c in range(cols)]
        self.tags = [""] * len(self.frames)
        self.durations = [None] * len(self.frames)
        self.load_frame(0)

    def bulk_import(self):
        paths = filedialog.askopenfilenames(parent=self.win, filetypes=IMAGE_TYPES)
        if not paths or not messagebox.askyesno("Bulk Import", "Import %d images as frames?\n\nThis will replace your "
                                                               "current project!" % len(paths), parent=self.win):
            return
        self.save_state()
        self.frames = [[Layer("Layer 1", self.W, self.H, Image.open(p).convert("RGBA").resize((self.W, self.H)))] for p in paths]
        self.tags = [""] * len(self.frames)
        self.durations = [None] * len(self.frames)
        self.load_frame(0)

    def project_dict(self):
        def png(img):
            buf = io.BytesIO()
            img.save(buf, "PNG")
            return base64.b64encode(buf.getvalue()).decode("ascii")
        return {"version": "2.0", "gridWidth": self.W, "gridHeight": self.H, "currentFrameIndex": self.cur_frame,
                "currentLayerIndex": self.cur_layer, "frameTags": self.tags, "frameDurations": self.durations,
                "customBrush": {"size": self.custom_size, "pattern": self.custom_brush} if self.custom_brush else None,
                "frames": [[{"name": l.name, "visible": l.visible, "opacity": l.opacity, "blendMode": l.blend,
                             "data": png(l.img)} for l in frame] for frame in self.frames]}

    def save_project(self):
        path = filedialog.asksaveasfilename(parent=self.win, defaultextension=".json", filetypes=[("JSON", "*.json")],
                                            initialfile="spooksie_project_%dx%d_%dframes.json" % (self.W, self.H, len(self.frames)))
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.project_dict(), f, indent=2)

    def load_project(self):
        path = filedialog.askopenfilename(parent=self.win, filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not data.get("version") or not data.get("frames"):
                raise ValueError("Invalid project file!")
            if not messagebox.askyesno("Load project", "Load project?\n\nDimensions: %sx%s\nFrames: %d\n\nThis will replace "
                                                       "your current work!" % (data["gridWidth"], data["gridHeight"],
                                                                               len(data["frames"])), parent=self.win):
                return
            self.apply_project(data)
        except Exception as exc:
            messagebox.showerror("Load Project", str(exc), parent=self.win)

    def apply_project(self, data):
        self.save_state()
        self.W, self.H = int(data["gridWidth"]), int(data["gridHeight"])
        frames = []
        for frame in data["frames"]:
            layers = []
            for ld in frame:
                raw = ld["data"].split(",", 1)[-1]
                img = Image.open(io.BytesIO(base64.b64decode(raw))).convert("RGBA")
                layer = Layer(ld.get("name", "Layer"), self.W, self.H, img)
                layer.visible = ld.get("visible", True)
                layer.opacity = ld.get("opacity", 1.0)
                layer.blend = ld.get("blendMode", "normal")
                layers.append(layer)
            frames.append(layers)
        self.frames = frames
        self.tags = (data.get("frameTags") or [""] * len(frames))[:len(frames)]
        self.durations = (data.get("frameDurations") or [None] * len(frames))[:len(frames)]
        if data.get("customBrush"):
            self.custom_brush = data["customBrush"]["pattern"]
            self.custom_size = data["customBrush"]["size"]
        self.load_frame(min(int(data.get("currentFrameIndex", 0)), len(frames) - 1))
        self.w_var.set(self.W)
        self.h_var.set(self.H)

    def composites(self):
        return [self.composite_frame(i) for i in range(len(self.frames))]

    def export_sheet(self):
        path = filedialog.asksaveasfilename(parent=self.win, defaultextension=".png",
                                            initialfile="sprite_%dx%dx%d.png" % (self.W, self.H, len(self.frames)))
        if not path:
            return
        sheet = Image.new("RGBA", (self.W * len(self.frames), self.H), (0, 0, 0, 0))
        for i, img in enumerate(self.composites()):
            sheet.paste(img, (i * self.W, 0))
        sheet.save(path)

    def export_atlas(self):
        path = filedialog.asksaveasfilename(parent=self.win, defaultextension=".png",
                                            initialfile="sprite_atlas_%dx%d.png" % (self.W, self.H))
        if not path:
            return
        sheet = Image.new("RGBA", (self.W * len(self.frames), self.H), (0, 0, 0, 0))
        frames = {}
        for i, img in enumerate(self.composites()):
            sheet.paste(img, (i * self.W, 0))
            frames[self.tags[i] or "frame_%d" % i] = {"frame": {"x": i * self.W, "y": 0, "w": self.W, "h": self.H},
                                                      "rotated": False, "trimmed": False,
                                                      "spriteSourceSize": {"x": 0, "y": 0, "w": self.W, "h": self.H},
                                                      "sourceSize": {"w": self.W, "h": self.H}}
        sheet.save(path)
        meta = {"meta": {"app": "Spooksie's Stinky Sprite Tool v2.0", "version": "2.0", "image": os.path.basename(path),
                         "format": "RGBA8888", "size": {"w": sheet.width, "h": sheet.height}, "scale": "1"}, "frames": frames}
        with open(os.path.splitext(path)[0] + ".json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

    def export_bmp_frames(self, bg=None):
        folder = filedialog.askdirectory(parent=self.win, title="Export Background Frames (BMP) to...")
        if not folder:
            return
        bg = bg or hex_to_rgba(self.bg_color())
        for i, img in enumerate(self.composites()):
            back = Image.new("RGBA", img.size, bg)
            back.alpha_composite(img)
            back.convert("RGB").save(os.path.join(folder, "frame_%03d_%dx%d.bmp" % (i + 1, self.W, self.H)))
        messagebox.showinfo("Export", "Exported %d frames as BMP-v24!\n(Background color: %s)" % (len(self.frames), rgba_hex(bg)),
                            parent=self.win)

    def quick_export_fuse(self):
        messagebox.showinfo("Quick Export", "Please import the exported BMPs into the Fuse Tool and set the transparency color "
                                            "as #FF00FF (Magenta).", parent=self.win)
        self.export_bmp_frames((255, 0, 255, 255))

    def export_gif(self):
        path = filedialog.asksaveasfilename(parent=self.win, defaultextension=".gif",
                                            initialfile="animation_%dx%d_%dframes.gif" % (self.W, self.H, len(self.frames)))
        if not path:
            return
        frames = self.composites()
        frames[0].save(path, save_all=True, append_images=frames[1:], loop=0, duration=self.speed_var.get(), disposal=2)

    # ----- workspace / options windows -----
    def save_workspace(self):
        ws = {"brushSize": self.brush_size, "brushShape": self.brush_shape, "currentColor": self.color,
                           "secondaryColor": self.color2, "zoom": self.zoom, "pan": list(self.pan),
                           "grid": self.grid_vis.get(), "bg": self.bg_preset.get(), "onion": self.onion.get(),
                           "onionPrev": self.onion_prev.get(), "onionNext": self.onion_next.get(),
                           "onionCount": self.onion_count.get(), "tilemap": self.tilemap.get(),
                           "tileSize": self.tile_size.get(), "symmetry": self.symmetry, "pattern": self.pattern,
                           "guides": [self.guides.get(), self.v_guides, self.h_guides]}
        self.write_store(WORKSPACE_FILE, ws)
        messagebox.showinfo("Workspace", "Workspace layout saved!\n\nIncludes: Grid, colors, zoom, tools, guides, and more!",
                            parent=self.win)

    def load_workspace(self):
        ws = self.read_store(WORKSPACE_FILE)
        if not ws:
            messagebox.showinfo("Workspace", "No saved workspace found!", parent=self.win)
            return
        self.size_var.set(ws["brushSize"])
        self.set_brush_size(ws["brushSize"])
        self.set_brush_shape(ws["brushShape"])
        self.set_color(ws["currentColor"])
        self.set_color2(ws["secondaryColor"])
        self.zoom, self.pan = ws["zoom"], ws["pan"]
        self.grid_vis.set(ws["grid"])
        self.bg_preset.set(ws["bg"])
        self.onion.set(ws["onion"])
        self.onion_prev.set(ws["onionPrev"])
        self.onion_next.set(ws["onionNext"])
        self.onion_count.set(ws["onionCount"])
        self.tilemap.set(ws["tilemap"])
        self.tile_size.set(ws["tileSize"])
        self.symmetry, self.pattern = ws["symmetry"], ws["pattern"]
        self.guides.set(ws["guides"][0])
        self.v_guides, self.h_guides = ws["guides"][1], ws["guides"][2]
        self.redraw()

    def store_path(self, name):
        os.makedirs(self.store_dir, exist_ok=True)
        return os.path.join(self.store_dir, name)

    def write_store(self, name, data):
        path = self.store_path(name)
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(path + ".tmp", path)

    def read_store(self, name):
        try:
            with open(self.store_path(name), "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def toggle_autosave(self):
        if self.autosave_job:
            self.win.after_cancel(self.autosave_job)
            self.autosave_job = None
        if self.autosave.get():
            self.autosave_job = self.win.after(AUTO_SAVE_MS, self._autosave_tick)
            self.check_recovery()

    def _autosave_tick(self):
        try:
            data = self.project_dict()
            data["timestamp"] = time.time()
            self.write_store(AUTOSAVE_FILE, data)
            self.set_status("Auto-saved at %s" % time.strftime("%H:%M:%S"))
        except OSError as exc:
            self.autosave.set(False)
            messagebox.showerror("Auto-Save", "Auto-save disabled: could not write the recovery file.\n%s" % exc,
                                 parent=self.win)
        self.autosave_job = self.win.after(AUTO_SAVE_MS, self._autosave_tick) if self.autosave.get() else None

    def check_recovery(self):
        data = self.read_store(AUTOSAVE_FILE)
        if not data or not data.get("frames"):
            return
        when = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data.get("timestamp", 0)))
        if messagebox.askyesno("Recovery", "Recovery data found!\n\nSaved: %s\nFrames: %d\nDimensions: %sx%s\n\n"
                                           "Recover this project?" % (when, len(data["frames"]), data.get("gridWidth"),
                                                                      data.get("gridHeight")), parent=self.win):
            try:
                self.apply_project(data)
                messagebox.showinfo("Recovery", "Project recovered successfully!\n%d frames restored" % len(self.frames),
                                    parent=self.win)
            except Exception as exc:
                messagebox.showerror("Recovery", "Error recovering project:\n%s" % exc, parent=self.win)
                return
        try:
            os.remove(self.store_path(AUTOSAVE_FILE))
        except OSError:
            pass
