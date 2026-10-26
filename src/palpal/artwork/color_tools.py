"""Artwork Tool: palette, histogram, curves, swap and remap."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .model import color_match, hex_to_rgba, map_rgb, rgba_hex


class ColorToolsMixin:
    """Colour palette panel, histogram and channels, curves, colour swap and remap."""

    # ----- palette & histogram (Other Options) -----
    def refresh_palette(self):
        seen = set(self.palette_colors)
        for layer in self.all_layers():
            for _count, p in layer.img.getcolors(self.W * self.H + 1) or []:
                if p[3] > 0 and p not in seen:
                    seen.add(p)
                    self.palette_colors.append(p)
        self.palette_colors.sort()
        for w in self.palette_grid.winfo_children():
            w.destroy()
        for n, p in enumerate(self.palette_colors[:256]):
            b = tk.Label(self.palette_grid, bg=rgba_hex(p), width=2, relief="solid", bd=1, cursor="hand2")
            b._cp_keep = True
            b.grid(row=n // 12, column=n % 12, padx=1, pady=1)
            b.bind("<Button-1>", lambda e, p=p: self.set_color(rgba_hex(p)))
        self.palette_count.configure(text="%d colors detected" % len(self.palette_colors))

    def add_palette_color(self):
        c = hex_to_rgba(self.color)
        if c not in self.palette_colors:
            self.palette_colors.append(c)
        self.refresh_palette()

    def clear_palette(self):
        if messagebox.askyesno("Clear Palette", "Clear all colors from palette?\n\nThis only clears the palette display, "
                                                "not your sprite.", parent=self.win):
            self.palette_colors = []
            for w in self.palette_grid.winfo_children():
                w.destroy()
            self.palette_count.configure(text="0 colors detected")

    def gradient_palette(self):
        steps = simpledialog.askinteger("🌈 Gradient Palette", "How many color steps? (2-32)", initialvalue=8, minvalue=2,
                                        maxvalue=32, parent=self.win)
        if not steps:
            return
        a, b = hex_to_rgba(self.color), hex_to_rgba(self.color2)
        self.palette_colors = [tuple(round(a[k] + (b[k] - a[k]) * i / (steps - 1)) for k in range(3)) + (255,)
                               for i in range(steps)]
        self.show_palette.set(True)
        self.apply_panels()
        self.refresh_palette()

    def export_palette(self):
        if not self.palette_colors:
            self.refresh_palette()
        if not self.palette_colors:
            messagebox.showinfo("Export", "No colors in palette! Draw something first.", parent=self.win)
            return
        kind = simpledialog.askstring("📤 Export Palette", "Type PAL for JASC-PAL text or VGA for a 768-byte VGA palette:",
                                      initialvalue="PAL", parent=self.win)
        if not kind:
            return
        if kind.strip().upper() == "VGA":
            self.export_vga_palette()
            return
        path = filedialog.asksaveasfilename(parent=self.win, defaultextension=".pal", filetypes=[("JASC-PAL", "*.pal")],
                                            initialfile="sprite_palette_%d_colors.pal" % len(self.palette_colors))
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("JASC-PAL\n0100\n%d\n" % len(self.palette_colors))
                for p in self.palette_colors:
                    f.write("%d %d %d\n" % p[:3])

    def export_vga_palette(self):
        if not self.palette_colors:
            self.refresh_palette()
        path = filedialog.asksaveasfilename(parent=self.win, defaultextension=".pal", filetypes=[("VGA palette", "*.pal")],
                                            initialfile="sprite_vga_palette_%d_colors.pal" % len(self.palette_colors))
        if not path:
            return
        bg = hex_to_rgba(self.bg_color())
        data = bytearray()
        for i in range(256):
            p = self.palette_colors[i] if i < len(self.palette_colors) else bg
            data += bytes(p[:3])
        with open(path, "wb") as f:
            f.write(bytes(data))

    def import_palette(self):
        path = filedialog.askopenfilename(parent=self.win, filetypes=self.palette_types)
        if not path:
            return
        if self.read_palette is not None and not path.lower().endswith(".vga"):
            try:
                colors = [tuple(c[:3]) + (255,) for c in self.read_palette(path)]
            except Exception:
                colors = []
            if colors:
                self._use_imported_palette(colors)
                return
        with open(path, "rb") as f:
            raw = f.read()
        colors = []
        try:
            lines = [l.strip() for l in raw.decode("utf-8").splitlines() if l.strip()]
        except UnicodeDecodeError:
            lines = []
        if len(lines) >= 3 and lines[0] == "JASC-PAL" and lines[1] == "0100":
            for line in lines[3:3 + int(lines[2])]:
                parts = line.split()
                if len(parts) >= 3:
                    colors.append((int(parts[0]), int(parts[1]), int(parts[2]), 255))
        elif len(raw) == 768:
            colors = [(raw[i], raw[i + 1], raw[i + 2], 255) for i in range(0, 768, 3)]
        else:
            messagebox.showerror("Import Palette", "Could not detect palette format!\n\nFile is not JASC-PAL format and is "
                                                   "%d bytes (expected 768 for VGA format)." % len(raw), parent=self.win)
            return
        self._use_imported_palette(colors)

    def _use_imported_palette(self, colors):
        unique = []
        for c in colors:
            if c not in unique:
                unique.append(c)
        self.palette_colors = unique
        self.show_palette.set(True)
        self.apply_panels()
        self.refresh_palette()

    def show_histogram(self, channel):
        self.hist_channel = channel
        c = self.hist_canvas
        c.delete("all")
        hist = [[0] * 256 for _ in range(3)]
        total = 0
        for layer in self.layers():
            if not layer.visible:
                continue
            for p in layer.img.getdata():
                if p[3] > 0:
                    for k in range(3):
                        hist[k][p[k]] += 1
                    total += 1
        mx = max(1, max(max(h) for h in hist))
        w, h = 300, 100
        for k, (ch, col, solid) in enumerate((("r", "#ff8080", "#ff0000"), ("g", "#80ff80", "#00ff00"),
                                             ("b", "#8080ff", "#0000ff"))):
            if channel in ("all", ch):
                for i in range(256):
                    bh = hist[k][i] / mx * h
                    if bh:
                        c.create_rectangle(i * w / 256, h - bh, (i + 1) * w / 256, h, fill=solid if channel == ch else col,
                                           outline="")
        avg = [sum(i * n for i, n in enumerate(hist[k])) / total if total else 0 for k in range(3)]
        self.hist_lbl.configure(text="Pixels: %d | Avg RGB: (%d, %d, %d)" % (total, *avg))

    def extract_channel(self, k):
        self.save_state()
        px = self.layer().img.load()
        for y in range(self.H):
            for x in range(self.W):
                p = px[x, y]
                if p[3]:
                    px[x, y] = (p[k], p[k], p[k], p[3])
        self.changed()

    def invert_colors(self):
        self.save_state()
        px = self.layer().img.load()
        for y in range(self.H):
            for x in range(self.W):
                p = px[x, y]
                if p[3]:
                    px[x, y] = (255 - p[0], 255 - p[1], 255 - p[2], p[3])
        self.changed()

    def color_curves(self):
        layer = self.layer()
        original = layer.img.copy()
        points = [[0.0, 0.0], [0.5, 0.5], [1.0, 1.0]]
        top = self.popup()
        top.title("📊 Color Curves")
        cv = tk.Canvas(top, width=550, height=200, bg="#1a1a1a", highlightthickness=0)
        cv.pack(padx=10, pady=10)
        tk.Label(top, text="Click on the curve to add points. Drag points to adjust. Double-click a point to remove it.").pack()
        pad = 20
        gw, gh = 550 - 2 * pad, 200 - 2 * pad
        drag = {"i": -1}

        def poly(x):
            res = 0
            for i, (xi, yi) in enumerate(points):
                term = yi
                for j, (xj, _yj) in enumerate(points):
                    if i != j and abs(xi - xj) > 0.001:
                        term = term * (x - xj) / (xi - xj)
                res += term
            return max(0.0, min(1.0, res))

        def apply():
            lut = [round(poly(i / 255) * 255) for i in range(256)]
            img = map_rgb(original, lut)
            a = original.getchannel("A")
            # Transparent pixels keep their colour values, as the web tool skipped them
            img.paste(original, mask=a.point(lambda v: 255 if v == 0 else 0))
            layer.img = img
            self.redraw()
            draw()

        def draw():
            cv.delete("all")
            for i in range(5):
                cv.create_line(pad + gw / 4 * i, pad, pad + gw / 4 * i, 200 - pad, fill="#444")
                cv.create_line(pad, pad + gh / 4 * i, 550 - pad, pad + gh / 4 * i, fill="#444")
            cv.create_line(pad, 200 - pad, 550 - pad, pad, fill="#666", dash=(5, 5))
            pts = []
            for i in range(256):
                v = i / 255
                pts += [pad + v * gw, 200 - pad - poly(v) * gh]
            cv.create_line(*pts, fill="#9c27b0", width=3)
            for n, (x, y) in enumerate(points):
                px, py = pad + x * gw, 200 - pad - y * gh
                cv.create_oval(px - 6, py - 6, px + 6, py + 6, fill="#fff" if n == drag["i"] else "#00bcd4", outline="#fff",
                               width=2)

        def near(e):
            for n, (x, y) in enumerate(points):
                if math.hypot(e.x - (pad + x * gw), e.y - (200 - pad - y * gh)) < 10:
                    return n
            return -1

        def press(e):
            drag["i"] = near(e)
            if drag["i"] == -1:
                vx = max(0, min(1, (e.x - pad) / gw))
                vy = max(0, min(1, (200 - pad - e.y) / gh))
                points.append([vx, vy])
                points.sort(key=lambda p: p[0])
                drag["i"] = points.index([vx, vy])
                apply()

        def move(e):
            i = drag["i"]
            if i == -1:
                return
            vx = (e.x - pad) / gw
            vy = max(0, min(1, (200 - pad - e.y) / gh))
            if i == 0:
                vx = 0
            elif i == len(points) - 1:
                vx = 1
            else:
                vx = max(points[i - 1][0] + 0.01, min(points[i + 1][0] - 0.01, vx))
            points[i] = [vx, vy]
            apply()

        def release(_e):
            drag["i"] = -1
            draw()

        def double(e):
            i = near(e)
            if 0 < i < len(points) - 1:
                del points[i]
                apply()

        cv.bind("<ButtonPress-1>", press)
        cv.bind("<B1-Motion>", move)
        cv.bind("<ButtonRelease-1>", release)
        cv.bind("<Double-Button-1>", double)

        def finish(keep):
            if keep:
                layer.img, cur = original, layer.img
                self.save_state()
                layer.img = cur
                self.changed()
            else:
                layer.img = original
                self.redraw()
            top.destroy()

        row = tk.Frame(top)
        row.pack(pady=8)
        tk.Button(row, text="Apply", bg="#4CAF50", fg="white", command=lambda: finish(True)).pack(side="left", padx=4)
        tk.Button(row, text="Cancel", bg="#f44336", fg="white", command=lambda: finish(False)).pack(side="left", padx=4)
        top.bind("<Escape>", lambda e: finish(False))
        top.protocol("WM_DELETE_WINDOW", lambda: finish(False))
        self.theme(top)
        apply()

    # ----- global colour tools -----
    def toggle_swap(self):
        if self.swap_frame.winfo_ismapped():
            self.swap_frame.pack_forget()
            if self.tool == "swap":
                self.activate_tool("pencil")
            return
        for w in self.swap_frame.winfo_children():
            w.destroy()
        self.tool = "swap"
        self.update_tool_display()
        self.set_status("🎨 Color Swap is active - Click a pixel to select source color, or type colors below")
        tk.Label(self.swap_frame, text="Source color (click a pixel or type):", font=("Arial", 8)).pack(anchor="w")
        self.swap_src = tk.Entry(self.swap_frame, width=10)
        self.swap_src.insert(0, "#000000")
        self.swap_src.pack(fill="x")
        tk.Label(self.swap_frame, text="Replace with:", font=("Arial", 8)).pack(anchor="w")
        self.swap_dst = tk.Entry(self.swap_frame, width=10)
        self.swap_dst.insert(0, self.color)
        self.swap_dst.pack(fill="x")
        tk.Button(self.swap_frame, text="Apply Color Swap to ALL Frames", bg="#8a2be2", fg="white",
                  command=self.apply_swap).pack(fill="x", pady=2)
        tk.Button(self.swap_frame, text="Cancel", command=self.toggle_swap).pack(fill="x")
        self.swap_frame.pack(fill="x", before=self.options_anchor)
        self.theme(self.swap_frame)

    def apply_swap(self):
        src, dst = hex_to_rgba(self.swap_src.get()), hex_to_rgba(self.swap_dst.get())
        if src is None or dst is None:
            messagebox.showerror("Color Swap", "Invalid hex color! Use format: #RRGGBB", parent=self.win)
            return
        self.save_state()
        for layer in self.all_layers():
            px = layer.img.load()
            for y in range(self.H):
                for x in range(self.W):
                    if color_match(px[x, y], src):
                        px[x, y] = dst
        self.toggle_swap()
        self.changed()
        messagebox.showinfo("Color Swap", "Color swap complete!\n%s → %s across all frames and layers!"
                            % (rgba_hex(src), rgba_hex(dst)), parent=self.win)

    def toggle_remap(self):
        if getattr(self, "remap_win", None) is not None and self.remap_win.winfo_exists():
            self.remap_win.destroy()
            self.set_status("")
            return
        self.refresh_palette()
        colors = [c for c in self.palette_colors if c[3] > 0]
        if not colors:
            messagebox.showinfo("Color Remap", "No colors found!\nDraw something first.", parent=self.win)
            return
        top = self.remap_win = self.popup()
        top.title("Color Remap (%d colors)" % len(colors))
        self.set_status("🎨 Color Remap (Multi) is active - set target colors and click Apply Remap to All Frames")
        holder = tk.Frame(top)
        holder.pack(fill="both", expand=True, padx=8, pady=8)
        cv = tk.Canvas(holder, height=320, width=260, highlightthickness=0)
        sb = ttk.Scrollbar(holder, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=sb.set)
        inner = tk.Frame(cv)
        cv.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        entries = []
        for c in colors:
            r = tk.Frame(inner)
            r.pack(fill="x", pady=1)
            sw = tk.Label(r, bg=rgba_hex(c), width=3, relief="solid", bd=1)
            sw._cp_keep = True
            sw.pack(side="left")
            tk.Label(r, text="→").pack(side="left", padx=4)
            e = tk.Entry(r, width=9)
            e.insert(0, rgba_hex(c))
            e.pack(side="left")
            entries.append((c, e))

        def apply():
            mapping = {}
            for c, e in entries:
                t = hex_to_rgba(e.get())
                if t:
                    mapping[c] = t[:3] + (c[3],)
            self.save_state()
            n = 0
            for layer in self.all_layers():
                px = layer.img.load()
                for y in range(self.H):
                    for x in range(self.W):
                        new = mapping.get(px[x, y])
                        if new:
                            px[x, y] = new
                            n += 1
            top.destroy()
            self.set_status("")
            self.palette_colors = []
            self.changed()
            messagebox.showinfo("Color Remap", "Color remap complete!\n%d pixels remapped across all frames and layers!" % n,
                                parent=self.win)

        tk.Button(top, text="Apply Remap to All Frames", bg="#e91e63", fg="white", command=apply).pack(fill="x", padx=8)
        tk.Button(top, text="Cancel", command=self.toggle_remap).pack(fill="x", padx=8, pady=(2, 8))
        self.theme(top)
