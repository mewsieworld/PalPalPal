"""Artwork Tool: selections."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .model import color_match


class SelectionMixin:
    """Rectangle, circle, lasso, colour and edge selections, and moving them."""

    # ----- selections -----
    def make_pixel_selection(self, pixels, kind):
        pixels = set(pixels)
        xs = [p[0] for p in pixels]
        ys = [p[1] for p in pixels]
        self.selection = {"x1": min(xs), "y1": min(ys), "x2": max(xs), "y2": max(ys), "kind": kind,
                          "pixels": pixels, "layer": self.cur_layer}
        self.update_selection_info()
        self.update_tool_display()
        self.redraw_overlay()

    def select_by_color(self, cx, cy):
        target = self.get_px(cx, cy)
        px = self.layer().img.load()
        found = self.connected(cx, cy, lambda x, y: color_match(px[x, y], target))
        if found:
            self.make_pixel_selection(found, "Color")

    def select_by_edges(self, cx, cy):
        th = simpledialog.askinteger("🔍 Edge Detection", "Edge detection threshold (0-255):\n\n50 = Sensitive\n"
                                                       "100 = Moderate\n150 = Less sensitive",
                                     initialvalue=100, minvalue=0, maxvalue=255, parent=self.win)
        if th is None:
            return
        comp = self.composite_frame(self.cur_frame).load()
        edge = set()
        for y in range(1, self.H - 1):
            for x in range(1, self.W - 1):
                gx = gy = 0
                for ky in (-1, 0, 1):
                    for kx in (-1, 0, 1):
                        p = comp[x + kx, y + ky]
                        inten = (p[0] + p[1] + p[2]) / 3
                        if kx == -1:
                            gx -= inten * (2 if ky == 0 else 1)
                        if kx == 1:
                            gx += inten * (2 if ky == 0 else 1)
                        if ky == -1:
                            gy -= inten * (2 if kx == 0 else 1)
                        if ky == 1:
                            gy += inten * (2 if kx == 0 else 1)
                if math.sqrt(gx * gx + gy * gy) > th:
                    edge.add((x, y))
        found = self.connected(cx, cy, lambda x, y: (x, y) not in edge)
        if found:
            self.make_pixel_selection(found, "Edge Detect")
        else:
            messagebox.showinfo("Edge Detect", "No region found!\nTry adjusting the threshold.", parent=self.win)

    def lasso_pixels(self, path):
        if len(path) < 3:
            return set()
        poly = [(x + 0.5, y + 0.5) for x, y in path]

        def inside(px, py):
            res, j = False, len(poly) - 1
            for i in range(len(poly)):
                xi, yi = poly[i]
                xj, yj = poly[j]
                if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi) + xi:
                    res = not res
                j = i
            return res

        xs = [p[0] for p in path]
        ys = [p[1] for p in path]
        out = set()
        for y in range(min(ys), max(ys) + 1):
            for x in range(min(xs), max(xs) + 1):
                if inside(x + 0.5, y + 0.5):
                    out.add((x, y))
                    continue
                hits = sum(inside(x + (sx + 0.5) / 5, y + (sy + 0.5) / 5) for sy in range(5) for sx in range(5))
                if hits / 25 >= LASSO_THRESHOLD:
                    out.add((x, y))
        return {p for p in out if self.in_bounds(*p)}

    def capture_selection(self):
        sel = self.selection
        layer = self.layers()[sel.get("layer", self.cur_layer)]
        x1, x2 = sorted((sel["x1"], sel["x2"]))
        y1, y2 = sorted((sel["y1"], sel["y2"]))
        data = Image.new("RGBA", (x2 - x1 + 1, y2 - y1 + 1), (0, 0, 0, 0))
        sel["original"] = []
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                if self.in_bounds(x, y) and (sel.get("pixels") is None or (x, y) in sel["pixels"]):
                    p = layer.img.getpixel((x, y))
                    sel["original"].append((x, y, p))
                    data.putpixel((x - x1, y - y1), p)
                    layer.img.putpixel((x, y), (0, 0, 0, 0))
        sel["data"] = data
        self.redraw()

    def paste_selection(self, tx, ty):
        sel = self.selection
        layer = self.layers()[sel.get("layer", self.cur_layer)]
        data = sel["data"]
        for y in range(data.height):
            for x in range(data.width):
                p = data.getpixel((x, y))
                if p[3] > 0 and self.in_bounds(tx + x, ty + y):
                    layer.img.putpixel((tx + x, ty + y), p)
        self.changed()

    def cancel_selection(self):
        sel = self.selection
        if sel and sel.get("original"):
            layer = self.layers()[sel.get("layer", self.cur_layer)]
            for x, y, p in sel["original"]:
                layer.img.putpixel((x, y), p)
        self.selection = None
        self.moving_sel = False
        self.lasso = []
        self.circle_center = None
        self.update_selection_info()
        self.update_tool_display()
        self.redraw()

    def clear_selection(self):
        if self.moving_sel and self.selection and self.selection.get("original"):
            self.cancel_selection()
        self.selection = None
        self.moving_sel = False
        self.lasso = []
        self.circle_center = None
        self.update_selection_info()
        self.update_tool_display()
        self.redraw_overlay()

    def update_selection_info(self):
        sel = self.selection
        if not sel:
            self.sel_lbl.configure(text="")
            return
        if sel.get("pixels") is not None:
            n = len(sel["pixels"])
        else:
            n = (abs(sel["x2"] - sel["x1"]) + 1) * (abs(sel["y2"] - sel["y1"]) + 1)
        self.sel_lbl.configure(text="Selection: %d pixels" % n)
