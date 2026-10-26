"""Artwork Tool: drawing the canvas."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .model import composite_layers, hex_to_rgba, rgba_hex


class RenderMixin:
    """Drawing the canvas: composite, background, grid, guides and overlays."""

    # ----- rendering -----
    def composite_frame(self, index):
        return composite_layers(self.frames[index], (self.W, self.H))

    def bg_color(self):
        preset = self.bg_preset.get()
        if preset == "checker":
            return "#ffffff"
        if preset == "custom":
            return self.bg_custom
        return preset

    def changed(self):
        """After an edit: redraw, refresh the thumbnail and the palette."""
        self.redraw()
        self.render_thumbs()
        self.render_layers()
        if self.show_palette.get():
            self.refresh_palette()

    def redraw(self):
        c = self.canvas
        if not c.winfo_exists():
            return
        s = self.scale()
        ox, oy = self.origin()
        dw, dh = max(1, int(self.W * s)), max(1, int(self.H * s))
        comp = self.composite_frame(self.cur_frame)
        if self.bg_preset.get() == "checker":
            back = Image.new("RGBA", (self.W, self.H))
            bp = back.load()
            for y in range(self.H):
                for x in range(self.W):
                    bp[x, y] = (255, 255, 255, 255) if (x + y) % 2 == 0 else (204, 204, 204, 255)
        else:
            back = Image.new("RGBA", (self.W, self.H), hex_to_rgba(self.bg_color()))
        back.alpha_composite(comp)
        if self.onion.get() and len(self.frames) > 1:
            for direction, opacity, tint in ((-1, self.onion_prev.get() / 100, (100, -50, -50)),
                                             (1, self.onion_next.get() / 100, (-50, -50, 100))):
                for i in range(1, self.onion_count.get() + 1):
                    idx = self.cur_frame + direction * i
                    if 0 <= idx < len(self.frames):
                        ghost = self.composite_frame(idx)
                        gp = ghost.load()
                        for y in range(self.H):
                            for x in range(self.W):
                                p = gp[x, y]
                                if p[3]:
                                    gp[x, y] = (max(0, min(255, p[0] + tint[0])), max(0, min(255, p[1] + tint[1])),
                                                max(0, min(255, p[2] + tint[2])), int(p[3] * opacity / i))
                        back.alpha_composite(ghost)
        shown = back.resize((dw, dh), Image.Resampling.NEAREST)
        self.photos["main"] = ImageTk.PhotoImage(shown)
        c.delete("all")
        c.create_image(ox, oy, image=self.photos["main"], anchor="nw", tags="img")
        self.draw_grid(ox, oy, s)
        self.redraw_overlay()

    def draw_grid(self, ox, oy, s):
        c = self.canvas
        vis = self.grid_vis.get()
        if vis != "none" and s >= 3:
            color = self.grid_color
            if vis == "low":
                rgb = hex_to_rgba(color)
                lum = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
                f = 0.7 if lum > 128 else 1.5
                color = rgba_hex(tuple(int(min(255, max(0, v * f))) for v in rgb[:3]) + (255,))
            for i in range(self.W + 1):
                c.create_line(ox + i * s, oy, ox + i * s, oy + self.H * s, fill=color, tags="grid")
            for i in range(self.H + 1):
                c.create_line(ox, oy + i * s, ox + self.W * s, oy + i * s, fill=color, tags="grid")
            if self.dark_grid.get() and self.dark_every.get() > 0:
                n = self.dark_every.get()
                for i in range(0, self.W + 1, n):
                    c.create_line(ox + i * s, oy, ox + i * s, oy + self.H * s, fill=self.dark_color, width=2, tags="grid")
                for i in range(0, self.H + 1, n):
                    c.create_line(ox, oy + i * s, ox + self.W * s, oy + i * s, fill=self.dark_color, width=2, tags="grid")
        if self.tilemap.get():
            ts = self.tile_size.get()
            for i in range(0, self.W + 1, ts):
                c.create_line(ox + i * s, oy, ox + i * s, oy + self.H * s, fill="#FF9800", width=3, dash=(4, 4))
            for i in range(0, self.H + 1, ts):
                c.create_line(ox, oy + i * s, ox + self.W * s, oy + i * s, fill="#FF9800", width=3, dash=(4, 4))
        if self.persp.get():
            for i in range(-self.H, self.W + 1, 8):
                c.create_line(ox + i * s, oy, ox + (i + self.H) * s, oy + self.H * s, fill="#FF9800", dash=(4, 4))
            for i in range(0, self.W + self.H + 1, 8):
                c.create_line(ox + i * s, oy, ox + (i - self.H) * s, oy + self.H * s, fill="#FF9800", dash=(4, 4))
        if self.guides.get():
            for g in self.v_guides:
                c.create_line(ox + g * s, oy, ox + g * s, oy + self.H * s, fill="#2196F3", width=2, dash=(8, 4))
            for g in self.h_guides:
                c.create_line(ox, oy + g * s, ox + self.W * s, oy + g * s, fill="#2196F3", width=2, dash=(8, 4))
        c.create_rectangle(ox, oy, ox + self.W * s, oy + self.H * s, outline=self.grid_color)

    def redraw_overlay(self):
        c = self.canvas
        c.delete("overlay")
        s = self.scale()
        ox, oy = self.origin()

        def cell(x, y, **kw):
            c.create_rectangle(ox + x * s, oy + y * s, ox + (x + 1) * s, oy + (y + 1) * s, tags="overlay", **kw)

        sel = self.selection
        if sel:
            x1, x2 = sorted((sel["x1"], sel["x2"]))
            y1, y2 = sorted((sel["y1"], sel["y2"]))
            if sel.get("data") is not None:
                img = sel["data"].resize((max(1, int(sel["data"].width * s)), max(1, int(sel["data"].height * s))),
                                         Image.Resampling.NEAREST)
                self.photos["sel"] = ImageTk.PhotoImage(img)
                c.create_image(ox + x1 * s, oy + y1 * s, image=self.photos["sel"], anchor="nw", tags="overlay")
            if sel.get("pixels") is not None and sel.get("data") is None:
                for (x, y) in sel["pixels"]:
                    if any((x + dx, y + dy) not in sel["pixels"] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                        cell(x, y, outline="#000", dash=(3, 3), width=2)
            else:
                c.create_rectangle(ox + x1 * s, oy + y1 * s, ox + (x2 + 1) * s, oy + (y2 + 1) * s,
                                   outline="#000", dash=(6, 6), width=3, tags="overlay")
        elif self.lasso:
            pts = [v for x, y in self.lasso for v in (ox + (x + 0.5) * s, oy + (y + 0.5) * s)]
            if len(pts) >= 4:
                c.create_line(*pts, fill="#000", dash=(5, 5), width=2, tags="overlay")
        if self.circle_center and getattr(self, "_circle_end", None) and self.drawing:
            cx, cy = self.circle_center
            ex, ey = self._circle_end
            r = math.sqrt((ex - cx) ** 2 + (ey - cy) ** 2) / 2 * s
            px, py = ox + (cx + 0.5) * s, oy + (cy + 0.5) * s
            c.create_oval(px - r, py - r, px + r, py + r, outline="#000", dash=(5, 5), width=2, tags="overlay")
        if self.line_start:
            cell(*self.line_start, fill="#ff8080", stipple="gray50")
        for p in self.shape_points:
            cell(*p, fill="#80ff80", stipple="gray50")
        if len(self.shape_points) > 1:
            pts = [v for x, y in self.shape_points for v in (ox + (x + 0.5) * s, oy + (y + 0.5) * s)]
            c.create_line(*pts, fill="#00ff00", width=2, tags="overlay")
        for p in self.curve_points:
            cell(*p, fill="#8080ff", stipple="gray50")
        if self.shape_start:
            cell(*self.shape_start, fill="#ffa500", stipple="gray50")
        for x, y, col in self.mesh_points:
            cell(x, y, fill=col, outline="#9c27b0", width=2)
        for x, y in self.bezier_points:
            cell(x, y, fill="#9c27b0", stipple="gray50")
