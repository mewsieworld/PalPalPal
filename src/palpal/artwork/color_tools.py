"""Artwork Tool: palette, histogram, channels and invert."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .model import hex_to_rgba, rgba_hex


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
