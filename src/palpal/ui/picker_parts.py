"""The color picker's pieces: sizes, color helpers, the drawn area / tracks and the Slider."""

import colorsys
import tkinter as tk

from PIL import Image, ImageChops, ImageDraw, ImageTk


AREA_W, AREA_H = 300, 180      # the saturation / brightness area
SLIDER_W, TRACK_H = 214, 12    # H / S / V sliders
THUMB = 9                      # slider thumb radius
SCALE = 3                      # supersampling for smooth round edges


def _hex(rgb):
    return "#%02X%02X%02X" % tuple(int(round(v)) for v in rgb[:3])


def _parse(text):
    text = str(text or "").strip().lstrip("#")
    if len(text) == 3:
        text = "".join(c * 2 for c in text)
    try:
        return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4)) if len(text) == 6 else None
    except ValueError:
        return None


def _hsv_rgb(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return int(round(r * 255)), int(round(g * 255)), int(round(b * 255))


def _round_mask(size, radius):
    w, h = size
    big = Image.new("L", (w * SCALE, h * SCALE), 0)
    ImageDraw.Draw(big).rounded_rectangle((0, 0, w * SCALE - 1, h * SCALE - 1), radius=radius * SCALE, fill=255)
    return big.resize((w, h), Image.Resampling.LANCZOS)


def sv_area(hue):
    """White -> pure hue across, darkened to black downward, with rounded corners."""
    r, g, b = _hsv_rgb(hue, 1, 1)
    row = Image.new("RGB", (AREA_W, 1))
    for x in range(AREA_W):
        t = x / float(AREA_W - 1)
        row.putpixel((x, 0), (int(255 + (r - 255) * t), int(255 + (g - 255) * t), int(255 + (b - 255) * t)))
    shade = Image.new("L", (1, AREA_H))
    for y in range(AREA_H):
        shade.putpixel((0, y), int(255 * (1 - y / float(AREA_H - 1))))
    shade = shade.resize((AREA_W, AREA_H))
    img = ImageChops.multiply(row.resize((AREA_W, AREA_H)), Image.merge("RGB", (shade, shade, shade))).convert("RGBA")
    img.putalpha(_round_mask((AREA_W, AREA_H), 12))
    return img


def gradient_track(colors):
    """A pill-shaped slider track running through the given colors."""
    row = Image.new("RGB", (SLIDER_W, 1))
    n = len(colors) - 1
    for x in range(SLIDER_W):
        t = x / float(SLIDER_W - 1) * n
        i = min(n - 1, int(t))
        f = t - i
        a, b = colors[i], colors[i + 1]
        row.putpixel((x, 0), tuple(int(a[k] + (b[k] - a[k]) * f) for k in range(3)))
    img = row.resize((SLIDER_W, TRACK_H)).convert("RGBA")
    img.putalpha(_round_mask((SLIDER_W, TRACK_H), TRACK_H // 2))
    return img


def _ring(radius, fill, ring="white", edge="#00000055"):
    """A round thumb: the current color inside a white ring with a faint dark edge (readable on anything)."""
    d = radius * 2 + 4
    big = Image.new("RGBA", (d * SCALE, d * SCALE), (0, 0, 0, 0))
    g = ImageDraw.Draw(big)
    g.ellipse((0, 0, d * SCALE - 1, d * SCALE - 1), fill=(0, 0, 0, 70))
    g.ellipse((SCALE, SCALE, (d - 1) * SCALE - 1, (d - 1) * SCALE - 1), fill="white")
    inner = 3 * SCALE
    g.ellipse((inner + SCALE, inner + SCALE, (d - 1) * SCALE - inner - 1, (d - 1) * SCALE - inner - 1), fill=fill)
    return big.resize((d, d), Image.Resampling.LANCZOS)


class Slider:
    """A gradient track with a round thumb; value 0..1; calls on_change(value) while dragging."""

    def __init__(self, parent, bg, on_change):
        self.on_change = on_change
        self.value = 0.0
        self.c = tk.Canvas(parent, width=SLIDER_W + 2 * THUMB, height=2 * THUMB + 6, bg=bg, highlightthickness=0,
                           cursor="hand2")
        self.c._cp_keep = True
        self.track = None
        self.thumb_color = "#ffffff"
        self.c.bind("<Button-1>", self._click)
        self.c.bind("<B1-Motion>", self._click)

    def set_track(self, colors):
        self._track_photo = ImageTk.PhotoImage(gradient_track(colors), master=self.c)
        self.c.delete("track")
        self.c.create_image(THUMB, THUMB + 3, image=self._track_photo, anchor="w", tags="track")
        self.c.tag_lower("track")

    def set(self, value, color):
        self.value = min(1.0, max(0.0, value))
        self._thumb_photo = ImageTk.PhotoImage(_ring(THUMB - 1, color), master=self.c)
        self.c.delete("thumb")
        self.c.create_image(THUMB + self.value * SLIDER_W, THUMB + 3, image=self._thumb_photo, tags="thumb")

    def _click(self, event):
        self.on_change(min(1.0, max(0.0, (event.x - THUMB) / float(SLIDER_W))))
