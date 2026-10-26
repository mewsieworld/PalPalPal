"""Artwork Tool: brush strokes, fills and shapes."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .model import color_match, hex_to_rgba, hsl_to_rgb, rgb_to_hsl, rgba_hex


class DrawingMixin:
    """Brush strokes, fills and shapes."""

    # ----- drawing -----
    def in_selection(self, x, y):
        sel = self.selection
        if not sel:
            return False
        if sel.get("pixels") is not None:
            return (x, y) in sel["pixels"]
        x1, x2 = sorted((sel["x1"], sel["x2"]))
        y1, y2 = sorted((sel["y1"], sel["y2"]))
        return x1 <= x <= x2 and y1 <= y <= y2

    def allowed(self, x, y):
        return not self.selection or self.moving_sel or self.in_selection(x, y)

    def put(self, x, y, rgba):
        """savePixelToLayer: the layer, or the mask while editing a mask."""
        if not self.in_bounds(x, y):
            return
        layer = self.layer()
        if self.mask_mode and layer.mask is not None:
            layer.mask.putpixel((x, y), int(round((rgba[0] + rgba[1] + rgba[2]) / 3)))
        else:
            layer.img.putpixel((x, y), tuple(int(v) for v in rgba))

    def draw_core(self, gx, gy, color, erase=False, tool="pencil"):
        size = 1 if tool == "refined" else self.brush_size
        shape_on = tool in ("pencil", "eraser") and self.brush_shape != "square" and tool != "pencilsquare"
        cells = self.brush_offsets(size, shape_on)
        if tool == "jumble":
            pts = [(gx + dx, gy + dy) for dx, dy in self.brush_offsets(size, self.brush_shape != "square")
                   if self.in_bounds(gx + dx, gy + dy) and self.allowed(gx + dx, gy + dy)]
            vals = [self.get_px(x, y) for x, y in pts]
            random.shuffle(vals)
            for (x, y), v in zip(pts, vals):
                self.put(x, y, v)
            return
        if tool == "spray":
            for _ in range(int(math.ceil(size * 2))):
                ang = random.random() * math.pi * 2
                dist = math.sqrt(random.random()) * size
                x, y = gx + round(math.cos(ang) * dist), gy + round(math.sin(ang) * dist)
                if self.in_bounds(x, y) and self.allowed(x, y):
                    self.put(x, y, hex_to_rgba(color))
            return
        rgba = (0, 0, 0, 0) if erase else hex_to_rgba(color)
        for dx, dy in cells:
            x, y = gx + dx, gy + dy
            if not self.in_bounds(x, y) or not self.allowed(x, y):
                continue
            final = rgba
            if tool == "clone":
                if self.clone_src == (-1, -1):
                    continue
                sx, sy = x - self.clone_off[0], y - self.clone_off[1]
                if not self.in_bounds(sx, sy):
                    continue
                p = self.get_px(sx, sy)
                if p[3] == 0:
                    continue
                final = p
            elif tool == "blend":
                around = self.neighbour_colors(x, y, True)
                if not around:
                    continue
                o = self.get_px(x, y)
                final = tuple(round(o[k] * BLEND_FACTOR + sum(q[k] for q in around) / len(around) * (1 - BLEND_FACTOR))
                              for k in range(4))
            elif tool in ("depth", "highlight"):
                p = self.get_px(x, y)
                if p[3] == 0:
                    continue
                if tool == "depth":
                    final = (max(0, int(p[0] * DEPTH_DARKEN)), max(0, int(p[1] * DEPTH_DARKEN)), max(0, int(p[2] * DEPTH_DARKEN)), 255)
                else:
                    final = (min(255, int(p[0] * HIGHLIGHT_BRIGHTEN)), min(255, int(p[1] * HIGHLIGHT_BRIGHTEN)),
                             min(255, int(p[2] * HIGHLIGHT_BRIGHTEN)), 255)
            elif tool == "sharpen":
                p = self.get_px(x, y)
                if p[3] == 0:
                    continue
                around = self.neighbour_colors(x, y, False)
                if not around:
                    continue
                final = tuple(min(255, max(0, round(p[k] + (p[k] - sum(q[k] for q in around) / len(around)) * SHARPEN_FACTOR)))
                              for k in range(3)) + (255,)
            elif tool == "dither":
                bayer = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
                threshold = bayer[y % 4][x % 4] / 16 * 255
                c1 = hex_to_rgba(color)
                if (c1[0] + c1[1] + c1[2]) / 3 > threshold:
                    final = c1
                elif self.color2 and self.color2 != color:
                    final = hex_to_rgba(self.color2)
                else:
                    continue
            elif tool == "liquify":
                if self.last == (-1, -1):
                    continue
                ddx, ddy = gx - self.last[0], gy - self.last[1]
                if ddx == 0 and ddy == 0:
                    continue
                dist = math.sqrt((x - gx) ** 2 + (y - gy) ** 2)
                radius = size / 2
                if radius == 0 or dist > radius:
                    continue
                strength = 1 - dist / radius
                sx, sy = x - round(ddx * strength), y - round(ddy * strength)
                if not self.in_bounds(sx, sy):
                    continue
                p = self.get_px(sx, sy)
                if p[3] == 0:
                    continue
                final = p
            elif tool == "rainbow":
                if (x, y) in self.stroke_pixels:
                    continue
                p = self.get_px(x, y)
                if p[3] == 0:
                    continue
                h, s, l = rgb_to_hsl(p[0], p[1], p[2])
                final = hsl_to_rgb((h + HUE_SHIFT) % 1, s, l) + (255,)
                self.stroke_pixels.add((x, y))
            self.put(x, y, final)

    def draw_pixel(self, gx, gy, color, erase=False, tool="pencil"):
        if self.last == (-1, -1):
            self.save_state()
        draw_tool = "pencil" if tool == "symmetrical" or self.mask_mode else tool
        self.draw_core(gx, gy, color, erase, draw_tool)
        if tool == "symmetrical":
            mx, my = self.W - 1 - gx, self.H - 1 - gy
            mode = self.symmetry
            if mode == "horizontal" and mx != gx:
                self.draw_core(mx, gy, color, erase, "pencil")
            elif mode == "vertical" and my != gy:
                self.draw_core(gx, my, color, erase, "pencil")
            elif mode == "quad":
                if mx != gx:
                    self.draw_core(mx, gy, color, erase, "pencil")
                if my != gy:
                    self.draw_core(gx, my, color, erase, "pencil")
                if mx != gx and my != gy:
                    self.draw_core(mx, my, color, erase, "pencil")
            elif mode in ("radial8", "radial16"):
                n = 8 if mode == "radial8" else 16
                cx, cy = self.W / 2, self.H / 2
                rx, ry = gx - cx, gy - cy
                ang, dist = math.atan2(ry, rx), math.sqrt(rx * rx + ry * ry)
                for i in range(1, n):
                    na = ang + i * 2 * math.pi / n
                    nx, ny = round(cx + dist * math.cos(na)), round(cy + dist * math.sin(na))
                    if self.in_bounds(nx, ny):
                        self.draw_core(nx, ny, color, erase, "pencil")

    def gradient_color(self, ratio):
        a, b = hex_to_rgba(self.color), hex_to_rgba(self.color2)
        c = tuple(round(a[k] + (b[k] - a[k]) * ratio) for k in range(4))
        return rgba_hex(c)

    # ----- fills and shapes -----
    def flood(self, sx, sy, color_for, tol, skip_if_same=None, ignore_selection=False):
        px = self.layer().img.load()
        target = px[sx, sy]
        if skip_if_same is not None and color_match(target, skip_if_same):
            return
        limit = self.selection and not self.moving_sel and not ignore_selection
        for x, y in self.connected(sx, sy, lambda x, y: (not limit or self.in_selection(x, y))
                                   and color_match(px[x, y], target, tol)):
            px[x, y] = tuple(color_for(x, y))

    def pattern_color(self, x, y):
        p, s = hex_to_rgba(self.color), hex_to_rgba(self.color2)
        pt = self.pattern
        if pt == "dots":
            return p if x % 2 == 0 and y % 2 == 0 else s
        if pt == "checker":
            return p if (x + y) % 2 == 0 else s
        if pt == "stripes-h":
            return p if y % 2 == 0 else s
        if pt == "stripes-v":
            return p if x % 2 == 0 else s
        if pt == "diagonal":
            return p if (x - y) % 4 == 0 else s
        if pt == "crosshatch":
            return p if x % 3 == 0 or y % 3 == 0 else s
        if pt == "bricks":
            off = (y // 2 % 2) * 2
            return p if (x + off) % 4 < 2 else s
        if pt == "hexagon":
            return p if (x % 3 == 0 and y % 2 == 0) or ((x + 1) % 3 == 0 and y % 2 == 1) else s
        return p

    def plot(self, x, y, rgba):
        if self.in_bounds(x, y) and self.allowed(x, y):
            self.put(x, y, rgba)

    def draw_line(self, x0, y0, x1, y1, color):
        rgba = hex_to_rgba(color)
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx - dy
        while True:
            self.plot(x0, y0, rgba)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def fill_polygon(self, pts, color):
        if len(pts) < 3:
            return
        rgba = hex_to_rgba(color)
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            for i in range(len(pts)):
                (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % len(pts)]
                if (y1 <= y < y2) or (y2 <= y < y1):
                    xs.append(round(x1 + (y - y1) * (x2 - x1) / (y2 - y1)))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                for x in range(xs[i], xs[i + 1] + 1):
                    self.plot(x, y, rgba)

    def draw_quad(self, x0, y0, x2, y2, x1, y1, color):
        rgba = hex_to_rgba(color)
        steps = max(abs(x2 - x0), abs(y2 - y0)) * 2
        for i in range(steps + 1):
            t = i / steps if steps else 0
            u = 1 - t
            self.plot(round(u * u * x0 + 2 * u * t * x1 + t * t * x2), round(u * u * y0 + 2 * u * t * y1 + t * t * y2), rgba)

    def shape_gradient(self, ratio):
        a, b = hex_to_rgba(self.color), hex_to_rgba(self.color2)
        return tuple(round(a[k] + (b[k] - a[k]) * ratio) for k in range(3)) + (255,)

    def draw_rect(self, x1, y1, x2, y2, color, filled):
        rgba = hex_to_rgba(color)
        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))
        if filled:
            w, h = x2 - x1 + 1, y2 - y1 + 1
            for y in range(y1, y2 + 1):
                for x in range(x1, x2 + 1):
                    c = rgba
                    if self.grad_shape.get():
                        xr, yr = (x - x1) / max(1, w - 1), (y - y1) / max(1, h - 1)
                        c = self.shape_gradient(math.sqrt(xr * xr + yr * yr) / math.sqrt(2))
                    self.plot(x, y, c)
        else:
            for x in range(x1, x2 + 1):
                self.plot(x, y1, rgba)
                self.plot(x, y2, rgba)
            for y in range(y1, y2 + 1):
                self.plot(x1, y, rgba)
                self.plot(x2, y, rgba)

    def draw_circle(self, cx, cy, r, color, filled):
        rgba = hex_to_rgba(color)
        if filled:
            for y in range(int(math.floor(cy - r)), int(math.ceil(cy + r)) + 1):
                for x in range(int(math.floor(cx - r)), int(math.ceil(cx + r)) + 1):
                    d2 = (x - cx) ** 2 + (y - cy) ** 2
                    if d2 <= r * r:
                        c = self.shape_gradient(min(1, math.sqrt(d2) / r)) if self.grad_shape.get() and r else rgba
                        self.plot(x, y, c)
        else:
            x, y, err = round(r), 0, 0
            while x >= y:
                for px, py in ((x, y), (y, x), (-y, x), (-x, y), (-x, -y), (-y, -x), (y, -x), (x, -y)):
                    self.plot(round(cx + px), round(cy + py), rgba)
                if err <= 0:
                    y += 1
                    err += 2 * y + 1
                if err > 0:
                    x -= 1
                    err -= 2 * x + 1

    def draw_bezier(self, pts, color):
        (p0, p1, p2, p3) = pts
        lx, ly = p0
        for i in range(51):
            t = i / 50
            mt = 1 - t
            x = round(mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t ** 3 * p3[0])
            y = round(mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t ** 3 * p3[1])
            self.draw_line(lx, ly, x, y, color)
            lx, ly = x, y

    def fill_mesh(self):
        if len(self.mesh_points) < 3:
            messagebox.showinfo("Gradient Mesh", "Need at least 3 points for gradient mesh!", parent=self.win)
            return
        top = self.popup()
        top.title("Gradient Mesh Editor")
        tk.Label(top, text="%d control points - click a color to change it" % len(self.mesh_points)).pack(padx=10, pady=6)
        rows = tk.Frame(top)
        rows.pack(padx=10)

        def rebuild():
            for w in rows.winfo_children():
                w.destroy()
            for i, (x, y, c) in enumerate(self.mesh_points):
                r = tk.Frame(rows)
                r.pack(fill="x", pady=1)
                tk.Label(r, text="Point %d: (%d, %d)" % (i, x, y), width=18, anchor="w").pack(side="left")
                b = tk.Button(r, bg=c, width=3)
                b.configure(command=lambda i=i, b=b: change(i, b))
                b.pack(side="left")
                tk.Button(r, text="✖", fg="white", bg="#dc3545", command=lambda i=i: remove(i)).pack(side="left", padx=4)

        def change(i, b):
            res = self.askcolor(color=self.mesh_points[i][2], parent=top)
            if res and res[1]:
                x, y, _c = self.mesh_points[i]
                self.mesh_points[i] = (x, y, res[1])
                b.configure(bg=res[1])

        def remove(i):
            del self.mesh_points[i]
            if len(self.mesh_points) < 3:
                messagebox.showinfo("Gradient Mesh", "Need at least 3 points!", parent=top)
                top.destroy()
                return
            rebuild()

        def apply():
            top.destroy()
            self.save_state()
            xs = [p[0] for p in self.mesh_points]
            ys = [p[1] for p in self.mesh_points]
            for y in range(min(ys), max(ys) + 1):
                for x in range(min(xs), max(xs) + 1):
                    tot, acc = 0, [0, 0, 0]
                    for px, py, c in self.mesh_points:
                        w = 1 / (math.sqrt((x - px) ** 2 + (y - py) ** 2) + 0.1)
                        rgb = hex_to_rgba(c)
                        acc = [acc[k] + rgb[k] * w for k in range(3)]
                        tot += w
                    if self.in_bounds(x, y):
                        self.layer().img.putpixel((x, y), tuple(round(a / tot) for a in acc) + (255,))
            self.mesh_points = []
            self.set_status("Gradient mesh filled!")
            self.changed()

        rebuild()
        b = tk.Frame(top)
        b.pack(pady=8)
        tk.Button(b, text="Apply Mesh", bg="#28a745", fg="white", command=apply).pack(side="left", padx=4)
        tk.Button(b, text="Cancel", bg="#dc3545", fg="white", command=top.destroy).pack(side="left", padx=4)
        self.theme(top)
