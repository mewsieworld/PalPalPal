"""Artwork Tool: lines, polygons, rectangles, circles, curves and mesh fills."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .model import hex_to_rgba


class ShapesMixin:
    """Lines, polygons, rectangles, circles, bezier curves and mesh fills."""

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
