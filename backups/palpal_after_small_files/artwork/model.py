"""Artwork Tool document model: colour maths, blend modes, layers, effects and compositing."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)


def walk(a, b):
    """Grid points from a to b, one per step of the longer axis (how strokes fill in fast mouse moves)."""
    (lx, ly), (gx, gy) = a, b
    steps = max(abs(gx - lx), abs(gy - ly))
    for i in range(steps + 1):
        t = i / steps if steps else 1
        yield round(lx + (gx - lx) * t), round(ly + (gy - ly) * t), t


def flip_op(direction):
    return Image.Transpose.FLIP_LEFT_RIGHT if direction == "h" else Image.Transpose.FLIP_TOP_BOTTOM


def map_rgb(img, lut):
    r, g, b, a = img.split()
    return Image.merge("RGBA", (r.point(lut), g.point(lut), b.point(lut), a))


# ---------------------------------------------------------------------------
# Colour helpers (same maths as the web tool)
# ---------------------------------------------------------------------------

def hex_to_rgba(text):
    text = (text or "").strip().lstrip("#")
    if len(text) == 3:
        text = "".join(c * 2 for c in text)
    try:
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16), 255)
    except (ValueError, IndexError):
        return None


def rgba_hex(c):
    return "#%02X%02X%02X" % (c[0], c[1], c[2])


def rgb_to_hsl(r, g, b):
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2
    if mx == mn:
        return 0.0, 0.0, l
    d = mx - mn
    s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
    if mx == r:
        h = ((g - b) / d + (6 if g < b else 0)) / 6
    elif mx == g:
        h = ((b - r) / d + 2) / 6
    else:
        h = ((r - g) / d + 4) / 6
    return h, s, l


def hsl_to_rgb(h, s, l):
    if s == 0:
        v = round(l * 255)
        return v, v, v

    def hue2rgb(p, q, t):
        if t < 0:
            t += 1
        if t > 1:
            t -= 1
        if t < 1 / 6:
            return p + (q - p) * 6 * t
        if t < 1 / 2:
            return q
        if t < 2 / 3:
            return p + (q - p) * (2 / 3 - t) * 6
        return p

    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q
    return (round(hue2rgb(p, q, h + 1 / 3) * 255), round(hue2rgb(p, q, h) * 255),
            round(hue2rgb(p, q, h - 1 / 3) * 255))


def color_match(a, b, tol=0):
    return all(abs(a[k] - b[k]) <= tol for k in range(4))


def blend_pixel(base, layer, mode, opacity):
    """applyBlendMode from the web tool, pixel by pixel."""
    br, bg, bb, ba = base
    lr, lg, lb, la = layer
    if la == 0:
        return base
    if ba == 0:
        mode = "normal"
    rr, rg, rb = lr, lg, lb

    def each(f):
        return f(br, lr), f(bg, lg), f(bb, lb)

    if mode == "multiply":
        rr, rg, rb = each(lambda b, l: b * l / 255)
    elif mode == "screen":
        rr, rg, rb = each(lambda b, l: 255 - (255 - b) * (255 - l) / 255)
    elif mode == "overlay":
        rr, rg, rb = each(lambda b, l: 2 * b * l / 255 if b < 128 else 255 - 2 * (255 - b) * (255 - l) / 255)
    elif mode == "add":
        rr, rg, rb = each(lambda b, l: min(255, b + l))
    elif mode == "subtract":
        rr, rg, rb = each(lambda b, l: max(0, b - l))
    elif mode == "darken":
        rr, rg, rb = each(min)
    elif mode == "lighten":
        rr, rg, rb = each(max)
    elif mode == "difference":
        rr, rg, rb = each(lambda b, l: abs(b - l))
    elif mode == "exclusion":
        rr, rg, rb = each(lambda b, l: b + l - 2 * b * l / 255)
    elif mode == "hue":
        _bh, bs, bl = rgb_to_hsl(br, bg, bb)
        lh, _ls, _ll = rgb_to_hsl(lr, lg, lb)
        rr, rg, rb = hsl_to_rgb(lh, bs, bl)
    elif mode == "saturation":
        bh, _bs, bl = rgb_to_hsl(br, bg, bb)
        _lh, ls, _ll = rgb_to_hsl(lr, lg, lb)
        rr, rg, rb = hsl_to_rgb(bh, ls, bl)
    elif mode == "colordodge":
        rr, rg, rb = each(lambda b, l: 255 if b == 255 else min(255, l * 255 / (255 - b)))
    elif mode == "colorburn":
        rr, rg, rb = each(lambda b, l: 0 if l == 0 else max(0, 255 - (255 - b) * 255 / l))
    elif mode == "vividlight":
        rr, rg, rb = each(lambda b, l: (0 if l == 0 else max(0, 255 - (255 - b) * 255 / (2 * l))) if l < 128
                          else (255 if l == 255 else min(255, b * 255 / (2 * (255 - l)))))
    elif mode == "linearlight":
        rr, rg, rb = each(lambda b, l: max(0, min(255, b + 2 * l - 255)))
    elif mode == "softlight":
        rr, rg, rb = each(lambda b, l: b - (255 - b) * (128 - l) / 128 if l < 128 else b + b * (l - 128) / 128)
    elif mode == "hardlight":
        rr, rg, rb = each(lambda b, l: 2 * b * l / 255 if l < 128 else 255 - 2 * (255 - b) * (255 - l) / 255)
    elif mode == "pinlight":
        rr, rg, rb = each(lambda b, l: min(b, 2 * l) if l < 128 else max(b, 2 * (l - 128)))
    elif mode == "hardmix":
        rr, rg, rb = each(lambda b, l: 0 if b + l < 255 else 255)
    ea = (la / 255) * opacity
    return (int(round(br * (1 - ea) + rr * ea)), int(round(bg * (1 - ea) + rg * ea)),
            int(round(bb * (1 - ea) + rb * ea)), int(min(255, ba + la * opacity)))


# ---------------------------------------------------------------------------
# Document model
# ---------------------------------------------------------------------------

def default_effects():
    return {"dropShadow": False, "glow": False, "stroke": False}


class Layer:
    def __init__(self, name, width, height, img=None):
        self.name = name
        self.img = img if img is not None else Image.new("RGBA", (width, height), (0, 0, 0, 0))
        self.visible = True
        self.opacity = 1.0
        self.blend = "normal"
        self.mask = None          # "L" image: white shows, black hides
        self.mask_enabled = False
        self.effects = default_effects()

    def clone(self):
        c = Layer(self.name, 0, 0, self.img.copy())
        c.visible, c.opacity, c.blend = self.visible, self.opacity, self.blend
        c.mask = self.mask.copy() if self.mask is not None else None
        c.mask_enabled = self.mask_enabled
        c.effects = dict(self.effects)
        return c


def apply_effects(img, effects):
    """Drop shadow, outer glow and stroke, exactly as the web tool (1px, on empty pixels only)."""
    if not (effects.get("dropShadow") or effects.get("glow") or effects.get("stroke")):
        return img
    w, h = img.size
    img = img.copy()
    if effects.get("dropShadow"):
        src = img.copy().load()
        px = img.load()
        for y in range(h - 1):
            for x in range(w - 1):
                if src[x, y][3] > 0 and px[x + 1, y + 1][3] == 0:
                    px[x + 1, y + 1] = (0, 0, 0, round(src[x, y][3] * 0.5))
    for kind in ("glow", "stroke"):
        if not effects.get(kind):
            continue
        src = img.copy().load()
        px = img.load()
        for y in range(h):
            for x in range(w):
                if px[x, y][3] != 0:
                    continue
                best = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if (dx or dy) and 0 <= x + dx < w and 0 <= y + dy < h:
                            best = max(best, src[x + dx, y + dy][3])
                if best:
                    px[x, y] = (255, 255, 255, round(best * 0.6)) if kind == "glow" else (0, 0, 0, 255)
    return img


def composite_layers(layers, size):
    """All visible layers bottom to top, with masks, effects, blend modes and opacity."""
    w, h = size
    result = Image.new("RGBA", size, (0, 0, 0, 0))
    for layer in layers:
        if not layer.visible:
            continue
        img = layer.img
        if img.size != size:
            canvas = Image.new("RGBA", size, (0, 0, 0, 0))
            canvas.paste(img, (0, 0))
            img = canvas
        if layer.mask_enabled and layer.mask is not None:
            img = img.copy()
            img.putalpha(ImageChops.multiply(img.getchannel("A"), layer.mask))
        img = apply_effects(img, layer.effects)
        if layer.blend == "normal":
            top = img
            if layer.opacity < 1:
                top = img.copy()
                top.putalpha(top.getchannel("A").point(lambda a: int(a * layer.opacity)))
            # The web tool's normal blend: colour lerps by the top alpha, alphas add up (done with Pillow, not per pixel)
            top_a = top.getchannel("A")
            alpha = ImageChops.add(result.getchannel("A"), top_a)
            result = Image.composite(top, result, top_a)
            result.putalpha(alpha)
        else:
            base_px = result.load()
            top_px = img.load()
            for y in range(h):
                for x in range(w):
                    t = top_px[x, y]
                    if t[3]:
                        base_px[x, y] = blend_pixel(base_px[x, y], t, layer.blend, layer.opacity)
    return result
