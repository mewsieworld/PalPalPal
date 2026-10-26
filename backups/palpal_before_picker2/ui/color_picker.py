"""A modern color picker: a saturation / brightness square, a hue strip, old vs new preview, hex, RGB and HSV
boxes, and recent colors. ask_color() returns "#RRGGBB" or None.

    ask_color(parent, "#ff8800", title="Primary color", theme=callable, colors=theme_dict, recent=[...])
"""

import colorsys
import tkinter as tk

from PIL import Image, ImageChops, ImageTk

SQUARE = 240   # the saturation / brightness square, in pixels
STRIP = 22     # the hue strip's width


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


def _hue_strip():
    img = Image.new("RGB", (1, SQUARE))
    for y in range(SQUARE):
        r, g, b = colorsys.hsv_to_rgb(y / float(SQUARE), 1, 1)
        img.putpixel((0, y), (int(r * 255), int(g * 255), int(b * 255)))
    return img.resize((STRIP, SQUARE))


def _sv_square(hue):
    """White -> the pure hue left to right, then darkened to black top to bottom."""
    r, g, b = colorsys.hsv_to_rgb(hue, 1, 1)
    row = Image.new("RGB", (SQUARE, 1))
    for x in range(SQUARE):
        t = x / float(SQUARE - 1)
        row.putpixel((x, 0), (int(255 + (r * 255 - 255) * t), int(255 + (g * 255 - 255) * t),
                              int(255 + (b * 255 - 255) * t)))
    shade = Image.new("L", (1, SQUARE))
    for y in range(SQUARE):
        shade.putpixel((0, y), int(255 * (1 - y / float(SQUARE - 1))))
    shade = shade.resize((SQUARE, SQUARE))
    return ImageChops.multiply(row.resize((SQUARE, SQUARE)), Image.merge("RGB", (shade, shade, shade)))


class ColorPicker:
    def __init__(self, parent, color="#000000", title="Pick a color", theme=None, colors=None, recent=()):
        self.result = None
        self.old = _parse(color) or (0, 0, 0)
        h, s, v = colorsys.rgb_to_hsv(*(c / 255.0 for c in self.old))
        self.h, self.s, self.v = h, s, v
        self._busy = False
        c = colors or {"bg": "#F0F0F0", "fg": "#000000", "input": "white", "canvas": "white"}
        self.win = tk.Toplevel(parent)
        self.win.title(title)
        self.win.resizable(False, False)
        self.win.transient(parent.winfo_toplevel())
        self.win.withdraw()
        body = tk.Frame(self.win)
        body.pack(padx=12, pady=12)

        # left: the square and the hue strip
        self.sq = tk.Canvas(body, width=SQUARE, height=SQUARE, highlightthickness=1, highlightbackground="#777",
                            cursor="crosshair")
        self.sq.grid(row=0, column=0, rowspan=2)
        self.sq._cp_keep = True
        self.hue = tk.Canvas(body, width=STRIP, height=SQUARE, highlightthickness=1, highlightbackground="#777",
                             cursor="sb_v_double_arrow")
        self.hue.grid(row=0, column=1, rowspan=2, padx=(8, 12))
        self.hue._cp_keep = True
        self._hue_photo = ImageTk.PhotoImage(_hue_strip())
        self.hue.create_image(0, 0, image=self._hue_photo, anchor="nw")
        for widget, handler in ((self.sq, self.on_square), (self.hue, self.on_hue)):
            widget.bind("<Button-1>", handler)
            widget.bind("<B1-Motion>", handler)

        # right: preview, numbers, recent colors
        side = tk.Frame(body)
        side.grid(row=0, column=2, sticky="n")
        prev = tk.Frame(side)
        prev.pack(fill="x")
        tk.Label(prev, text="New", font=("Arial", 8)).grid(row=0, column=0)
        tk.Label(prev, text="Old", font=("Arial", 8)).grid(row=0, column=1)
        self.new_sw = tk.Label(prev, width=9, height=2, relief="solid", bd=1)
        self.new_sw._cp_keep = True
        self.new_sw.grid(row=1, column=0)
        self.old_sw = tk.Label(prev, width=9, height=2, relief="solid", bd=1, bg=_hex(self.old), cursor="hand2")
        self.old_sw._cp_keep = True
        self.old_sw.grid(row=1, column=1)
        self.old_sw.bind("<Button-1>", lambda e: self.set_rgb(self.old))

        grid = tk.Frame(side)
        grid.pack(fill="x", pady=(10, 0))
        self.hex_var = tk.StringVar()
        tk.Label(grid, text="Hex #").grid(row=0, column=0, sticky="e")
        hx = tk.Entry(grid, textvariable=self.hex_var, width=9)
        hx.grid(row=0, column=1, columnspan=3, sticky="w", pady=(0, 6))
        hx.bind("<Return>", lambda e: self.from_hex())
        hx.bind("<FocusOut>", lambda e: self.from_hex())
        self.vars = {}
        for row, (key, top) in enumerate((("R", 255), ("G", 255), ("B", 255)), start=1):
            self._spin(grid, row, 0, key, top, self.from_rgb)
        for row, (key, top) in enumerate((("H", 359), ("S", 100), ("V", 100)), start=1):
            self._spin(grid, row, 2, key, top, self.from_hsv)

        recent = [r for r in recent if _parse(r)][:16]
        if recent:
            tk.Label(side, text="Recent", font=("Arial", 8)).pack(anchor="w", pady=(10, 2))
            box = tk.Frame(side)
            box.pack(anchor="w")
            for n, col in enumerate(recent):
                sw = tk.Label(box, bg=col, width=2, relief="solid", bd=1, cursor="hand2")
                sw._cp_keep = True
                sw.grid(row=n // 8, column=n % 8, padx=1, pady=1)
                sw.bind("<Button-1>", lambda e, col=col: self.set_rgb(_parse(col)))

        buttons = tk.Frame(body)
        buttons.grid(row=1, column=2, sticky="se")
        tk.Button(buttons, text="Cancel", width=8, command=self.cancel).pack(side="right")
        tk.Button(buttons, text="OK", width=8, command=self.ok).pack(side="right", padx=(0, 6))
        self.win.bind("<Return>", lambda e: self.ok())
        self.win.bind("<Escape>", lambda e: self.cancel())
        self.win.protocol("WM_DELETE_WINDOW", self.cancel)
        if theme:
            theme(self.win)
        self.redraw_square()
        self.refresh()
        self._center(parent)
        self.win.deiconify()
        self.win.grab_set()
        self.win.focus_force()

    def _spin(self, grid, row, col, key, top, command):
        tk.Label(grid, text=key).grid(row=row, column=col, sticky="e", padx=(6 if col else 0, 2))
        var = tk.StringVar()
        sp = tk.Spinbox(grid, from_=0, to=top, textvariable=var, width=5, command=command)
        sp.grid(row=row, column=col + 1, sticky="w", pady=1)
        sp.bind("<Return>", lambda e: command())
        sp.bind("<FocusOut>", lambda e: command())
        self.vars[key] = var

    def _center(self, parent):
        self.win.update_idletasks()
        top = parent.winfo_toplevel()
        w, h = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        x = top.winfo_rootx() + (top.winfo_width() - w) // 2
        y = top.winfo_rooty() + (top.winfo_height() - h) // 2
        self.win.geometry("+%d+%d" % (max(0, x), max(0, y)))

    # ----- state -----
    def rgb(self):
        r, g, b = colorsys.hsv_to_rgb(self.h, self.s, self.v)
        return int(round(r * 255)), int(round(g * 255)), int(round(b * 255))

    def set_rgb(self, rgb):
        if rgb is None:
            return
        h, s, v = colorsys.rgb_to_hsv(*(c / 255.0 for c in rgb))
        if s > 0 and v > 0:   # keep the hue when the color is grey / black
            self.h = h
        self.s, self.v = s, v
        self.redraw_square()
        self.refresh()

    def redraw_square(self):
        self._sq_photo = ImageTk.PhotoImage(_sv_square(self.h))
        self.sq.delete("all")
        self.sq.create_image(0, 0, image=self._sq_photo, anchor="nw")

    def refresh(self):
        """Markers, preview and the number boxes, from h / s / v."""
        self._busy = True
        rgb = self.rgb()
        self.sq.delete("marker")
        x, y = self.s * (SQUARE - 1), (1 - self.v) * (SQUARE - 1)
        ring = "white" if self.v < 0.6 or self.s > 0.5 else "black"
        self.sq.create_oval(x - 6, y - 6, x + 6, y + 6, outline=ring, width=2, tags="marker")
        self.hue.delete("marker")
        hy = self.h * SQUARE
        self.hue.create_rectangle(0, hy - 2, STRIP + 1, hy + 2, outline="white", width=2, tags="marker")
        self.new_sw.configure(bg=_hex(rgb))
        self.hex_var.set(_hex(rgb)[1:])
        for key, val in zip("RGB", rgb):
            self.vars[key].set(str(val))
        for key, val in (("H", int(round(self.h * 360)) % 360), ("S", int(round(self.s * 100))),
                         ("V", int(round(self.v * 100)))):
            self.vars[key].set(str(val))
        self._busy = False

    # ----- input -----
    def on_square(self, event):
        self.s = min(1.0, max(0.0, event.x / float(SQUARE - 1)))
        self.v = min(1.0, max(0.0, 1 - event.y / float(SQUARE - 1)))
        self.refresh()

    def on_hue(self, event):
        self.h = min(0.999, max(0.0, event.y / float(SQUARE)))
        self.redraw_square()
        self.refresh()

    def _num(self, key, top):
        try:
            return max(0, min(top, int(float(self.vars[key].get()))))
        except ValueError:
            return None

    def from_rgb(self):
        if self._busy:
            return
        vals = [self._num(k, 255) for k in "RGB"]
        if None not in vals:
            self.set_rgb(tuple(vals))

    def from_hsv(self):
        if self._busy:
            return
        h, s, v = self._num("H", 359), self._num("S", 100), self._num("V", 100)
        if None in (h, s, v):
            return
        self.h, self.s, self.v = h / 360.0, s / 100.0, v / 100.0
        self.redraw_square()
        self.refresh()

    def from_hex(self):
        if not self._busy:
            self.set_rgb(_parse(self.hex_var.get()))

    def ok(self):
        self.result = _hex(self.rgb())
        self.win.destroy()

    def cancel(self):
        self.result = None
        self.win.destroy()


def ask_color(parent, color="#000000", title="Pick a color", theme=None, colors=None, recent=()):
    previous = parent.grab_current()   # a modal dialog that opened the picker gets its grab back after
    picker = ColorPicker(parent, color, title, theme, colors, recent)
    parent.wait_window(picker.win)
    if previous is not None:
        try:
            previous.grab_set()
        except tk.TclError:
            pass
    return picker.result


def askcolor(color=None, parent=None, title="Pick a color", theme=None, colors=None, recent=()):
    """Drop-in for tkinter.colorchooser.askcolor: ((r, g, b), "#rrggbb") or (None, None)."""
    if isinstance(color, (tuple, list)):
        color = _hex(color)
    result = ask_color(parent, color or "#000000", title, theme, colors, recent)
    return (_parse(result), result) if result else (None, None)


def app_askcolor(app, color=None, parent=None, title="Pick a color"):
    """The picker for PalPalPal's own windows: themed like the app, with Saved Colors as the quick swatches."""
    from .theme import Theme
    saved = [_hex(c) for c in (getattr(app, "saved_colors", None) or []) if c]
    return askcolor(color, parent or app.master, title, theme=lambda w: Theme.apply(app, w),
                    colors=Theme.colors(app), recent=saved)
