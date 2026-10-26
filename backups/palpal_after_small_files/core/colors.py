"""Color math and conversions."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

def to_hex(color, hash_sign=True):
    text = "%02x%02x%02x" % tuple(int(v) for v in color[:3])
    return "#" + text if hash_sign else text


def parse_hex(text):
    text = str(text).strip().lstrip("#")
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) == 8:  # AARRGGBB (paint.net style)
        text = text[2:]
    if len(text) != 6:
        return None
    try:
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
    except ValueError:
        return None


def parse_color_any(value):
    if value is None:
        return None
    if isinstance(value, str):
        return parse_hex(value)
    if isinstance(value, dict):
        for keys in (("r", "g", "b"), ("red", "green", "blue"), ("R", "G", "B")):
            if all(k in value for k in keys):
                vals = [float(value[k]) for k in keys]
                if all(v <= 1.0 for v in vals) and any(isinstance(value[k], float) for k in keys):
                    return tuple(int(round(v * 255)) for v in vals)
                return tuple(max(0, min(255, int(v))) for v in vals)
        for key in ("hex", "color", "value", "rgb"):
            if key in value:
                return parse_color_any(value[key])
        return None
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return tuple(max(0, min(255, int(v))) for v in value[:3])
    return None


def pad256(colors):
    out = []
    for c in list(colors)[:PALETTE_SIZE]:
        c = parse_color_any(c)
        out.append(c if c else (0, 0, 0))
    return out + [(0, 0, 0)] * (PALETTE_SIZE - len(out))


def flat_palette(colors):
    flat = []
    for r, g, b in pad256(colors):
        flat += [r, g, b]
    return flat


def rgb_to_hsv_int(color):
    h, s, v = colorsys.rgb_to_hsv(color[0] / 255.0, color[1] / 255.0, color[2] / 255.0)
    return int(round(h * 360)), int(round(s * 100)), int(round(v * 100))


def hsv_int_to_rgb(h, s, v):
    r, g, b = colorsys.hsv_to_rgb((h % 360) / 360.0, max(0, min(100, s)) / 100.0, max(0, min(100, v)) / 100.0)
    return int(round(r * 255)), int(round(g * 255)), int(round(b * 255))


def avoid_key(color, key):
    """Nudge a color off the project's key (void) color so edits never key out by accident."""
    color = tuple(int(v) for v in color[:3])
    if key is None or color != tuple(key):
        return color
    r, g, b = color
    return (r - 1 if r > 0 else r + 1, g, b)


# ---------------------------------------------------------------------------
# Palette files
# ---------------------------------------------------------------------------

def _unit(v):
    """A 0-1 float (or a 0-255 number) as a 0-255 channel."""
    v = float(v)
    return max(0, min(255, int(round(v * 255 if v <= 1.0 else v))))


def cmyk_to_rgb(c, m, y, k):
    return tuple(int(round(255 * (1 - c) * (1 - k))) for c in (c, m, y))


def lab_to_rgb(l, a, b):
    """CIE L*a*b* (D50, as Photoshop/ASE store it) to sRGB."""
    fy = (l + 16) / 116.0
    fx, fz = fy + a / 500.0, fy - b / 200.0

    def finv(t):
        return t ** 3 if t ** 3 > 0.008856 else (t - 16 / 116.0) / 7.787

    x, y, z = 0.9642 * finv(fx), 1.0 * finv(fy), 0.8249 * finv(fz)
    # Bradford-adapted D50 XYZ -> linear sRGB
    rl = 3.1338561 * x - 1.6168667 * y - 0.4906146 * z
    gl = -0.9787684 * x + 1.9161415 * y + 0.0334540 * z
    bl = 0.0719453 * x - 0.2289914 * y + 1.4052427 * z

    def gamma(c):
        c = max(0.0, min(1.0, c))
        return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055

    return tuple(int(round(gamma(c) * 255)) for c in (rl, gl, bl))


def bg_fill(color):
    """The RGBA a background is filled with: the BG color, or fully transparent when it is unset."""
    return tuple(color) + (255,) if color is not None else (0, 0, 0, 0)


def rgb_to_hsl(color):
    h, l, s = colorsys.rgb_to_hls(color[0] / 255.0, color[1] / 255.0, color[2] / 255.0)
    return h * 360.0, s * 100.0, l * 100.0


def hsl_to_rgb(h, s, l):
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0, max(0.0, min(100.0, l)) / 100.0, max(0.0, min(100.0, s)) / 100.0)
    return int(round(r * 255)), int(round(g * 255)), int(round(b * 255))


# ---------------------------------------------------------------------------
# Image to Image Palette Adjuster (from recolortool2.html)
# ---------------------------------------------------------------------------

def luminosity(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def color_dist(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)
