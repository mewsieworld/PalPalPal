"""Artwork Tool: the color curves window."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .model import map_rgb


class CurvesMixin:
    """Color > Curves: drag points to remap each channel."""

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
