"""Artwork Tool: brush strokes, flood fills and patterns."""

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
