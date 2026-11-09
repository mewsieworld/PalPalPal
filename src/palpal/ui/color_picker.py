"""PalPalPal's color picker, laid out like a modern web picker, all in one window:

    ┌──────────────────────────┐
    │  saturation / brightness │   rounded area, ring thumb
    └──────────────────────────┘
    (●new ○old)  H ━━━━━━●━━━  [ 210 ]
                 S ━━━●━━━━━━  [  64 ]
                 V ━━━━━━━●━━  [  80 ]
    HEX [#3D7ACC]  R [ 61] G [122] B [204]
    ■ ■ ■ ■ ■ ■ ■ ■   (recent / saved colors)
                         [Cancel] [OK]

ask_color() returns "#RRGGBB" or None; askcolor() mimics tkinter.colorchooser.askcolor.
"""

import colorsys
import tkinter as tk

from PIL import Image, ImageDraw, ImageTk

from .rounded import round_button
from .picker_parts import AREA_H, AREA_W, Slider, _hex, _hsv_rgb, _parse, _ring, sv_area

class ColorPicker:
    def __init__(self, parent, color="#000000", title="Pick a color", theme=None, colors=None, recent=()):
        self.result = None
        self.old = _parse(color) or (0, 0, 0)
        self.h, self.s, self.v = colorsys.rgb_to_hsv(*(c / 255.0 for c in self.old))
        self._busy = False
        c = colors or {"bg": "#F0F0F0", "fg": "#000000", "input": "white", "canvas": "white", "select": "white"}
        bg, fg, field = c["bg"], c["fg"], c.get("input", "white")
        muted = "#9a9a9a"
        self.win = tk.Toplevel(parent)
        self.win.title(title)
        self.win.resizable(False, False)
        self.win.transient(parent.winfo_toplevel())
        self.win.withdraw()
        self.win.configure(bg=bg)
        card = tk.Frame(self.win, bg=bg)
        card.pack(padx=16, pady=16)

        # the saturation / brightness area
        self.area = tk.Canvas(card, width=AREA_W, height=AREA_H, bg=bg, highlightthickness=0, cursor="crosshair")
        self.area._cp_keep = True
        self.area.pack()
        self.area.bind("<Button-1>", self.on_area)
        self.area.bind("<B1-Motion>", self.on_area)

        # preview dots + H / S / V sliders with number boxes
        mid = tk.Frame(card, bg=bg)
        mid.pack(fill="x", pady=(14, 0))
        self.preview = tk.Canvas(mid, width=52, height=72, bg=bg, highlightthickness=0)
        self.preview._cp_keep = True
        self.preview.pack(side="left", padx=(0, 10))
        self.preview.bind("<Button-1>", lambda e: self.set_rgb(self.old) if e.y > 44 else None)
        rows = tk.Frame(mid, bg=bg)
        rows.pack(side="left")
        self.sliders, self.boxes = {}, {}
        for key, top in (("H", 360), ("S", 100), ("V", 100)):
            row = tk.Frame(rows, bg=bg)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=key, bg=bg, fg=muted, font=("Segoe UI", 9, "bold"), width=2).pack(side="left")
            sl = Slider(row, bg, lambda v, k=key: self.on_slider(k, v))
            sl.c.pack(side="left")
            self.sliders[key] = sl
            self.boxes[key] = self._box(row, 4, bg, fg, field, lambda k=key, t=top: self.on_number(k, t))
            self.boxes[key].pack(side="left", padx=(6, 0))

        # hex + RGB
        nums = tk.Frame(card, bg=bg)
        nums.pack(fill="x", pady=(12, 0))
        tk.Label(nums, text="HEX", bg=bg, fg=muted, font=("Segoe UI", 8, "bold")).pack(side="left")
        self.hex_box = self._box(nums, 8, bg, fg, field, self.from_hex)
        self.hex_box.pack(side="left", padx=(4, 12))
        for key in "RGB":
            tk.Label(nums, text=key, bg=bg, fg=muted, font=("Segoe UI", 8, "bold")).pack(side="left", padx=(6, 2))
            self.boxes[key] = self._box(nums, 4, bg, fg, field, self.from_rgb)
            self.boxes[key].pack(side="left")

        # swatches (recent / saved colors)
        recent = [r for r in recent if _parse(r)][:12]
        if recent:
            sw = tk.Frame(card, bg=bg)
            sw.pack(fill="x", pady=(12, 0))
            self._swatch_imgs = []
            for col in recent:
                img = Image.new("RGBA", (22, 22), (0, 0, 0, 0))
                ImageDraw.Draw(img).rounded_rectangle((1, 1, 20, 20), radius=6, fill=col, outline=(0, 0, 0, 60))
                photo = ImageTk.PhotoImage(img, master=sw)
                self._swatch_imgs.append(photo)
                lbl = tk.Label(sw, image=photo, bg=bg, cursor="hand2", bd=0)
                lbl._cp_keep = True
                lbl.pack(side="left", padx=2)
                lbl.bind("<Button-1>", lambda e, col=col: self.set_rgb(_parse(col)))

        buttons = tk.Frame(card, bg=bg)
        buttons.pack(fill="x", pady=(16, 0))
        ok = tk.Button(buttons, text="OK", width=8, font=("Segoe UI", 9, "bold"), command=self.ok)
        ok.pack(side="right")
        cancel = tk.Button(buttons, text="Cancel", width=8, font=("Segoe UI", 9), command=self.cancel)
        cancel.pack(side="right", padx=(0, 8))
        self.win.bind("<Return>", lambda e: self.ok())
        self.win.bind("<Escape>", lambda e: self.cancel())
        self.win.protocol("WM_DELETE_WINDOW", self.cancel)

        if theme:
            theme(self.win)
        self.win.configure(bg=bg)
        round_button(ok, "#42a5f5")
        round_button(cancel, "#9e9e9e")
        self.redraw_area()
        self.refresh()
        self._center(parent)
        self.win.deiconify()
        self.win.grab_set()
        self.win.focus_force()

    def _box(self, parent, width, bg, fg, field, command):
        e = tk.Entry(parent, width=width, justify="center", relief="flat", bg=field, fg=fg, insertbackground=fg,
                     highlightthickness=1, highlightbackground="#8a8a8a", highlightcolor="#42a5f5",
                     font=("Segoe UI", 9))
        e._cp_keep = True
        e.bind("<Return>", lambda ev: command())
        e.bind("<FocusOut>", lambda ev: command())
        return e

    def _center(self, parent):
        self.win.update_idletasks()
        top = parent.winfo_toplevel()
        w, h = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        x = top.winfo_rootx() + (top.winfo_width() - w) // 2
        y = top.winfo_rooty() + (top.winfo_height() - h) // 2
        self.win.geometry("+%d+%d" % (max(0, x), max(0, y)))

    # ----- state -----
    def rgb(self):
        return _hsv_rgb(self.h, self.s, self.v)

    def set_rgb(self, rgb):
        if rgb is None:
            return
        h, s, v = colorsys.rgb_to_hsv(*(c / 255.0 for c in rgb))
        if s > 0 and v > 0:   # greys and black keep the hue you had
            self.h = h
        self.s, self.v = s, v
        self.redraw_area()
        self.refresh()

    def redraw_area(self):
        self._area_photo = ImageTk.PhotoImage(sv_area(self.h), master=self.area)
        self.area.delete("all")
        self.area.create_image(0, 0, image=self._area_photo, anchor="nw")

    def refresh(self):
        """Thumbs, tracks, preview and boxes, all from h / s / v."""
        self._busy = True
        rgb = self.rgb()
        col = _hex(rgb)
        # area thumb
        self._area_thumb = ImageTk.PhotoImage(_ring(9, col), master=self.area)
        self.area.delete("thumb")
        self.area.create_image(self.s * (AREA_W - 1), (1 - self.v) * (AREA_H - 1), image=self._area_thumb,
                               tags="thumb")
        # slider tracks follow the color: hue is the rainbow, S runs grey -> color, V black -> color
        self.sliders["H"].set_track([_hsv_rgb(i / 6.0, 1, 1) for i in range(7)])
        self.sliders["S"].set_track([_hsv_rgb(self.h, 0, self.v), _hsv_rgb(self.h, 1, self.v)])
        self.sliders["V"].set_track([(0, 0, 0), _hsv_rgb(self.h, self.s, 1)])
        self.sliders["H"].set(self.h, _hex(_hsv_rgb(self.h, 1, 1)))
        self.sliders["S"].set(self.s, col)
        self.sliders["V"].set(self.v, col)
        # preview: new on top, old underneath (click it to go back)
        p = self.preview
        p.delete("all")
        p.create_oval(4, 2, 48, 46, fill=col, outline="#8a8a8a", width=1)
        p.create_oval(14, 48, 38, 72, fill=_hex(self.old), outline="#8a8a8a", width=1)
        for key, val in (("H", int(round(self.h * 360)) % 360), ("S", int(round(self.s * 100))),
                         ("V", int(round(self.v * 100))), ("R", rgb[0]), ("G", rgb[1]), ("B", rgb[2])):
            self._put(self.boxes[key], str(val))
        self._put(self.hex_box, col)
        self._busy = False

    @staticmethod
    def _put(entry, text):
        entry.delete(0, "end")
        entry.insert(0, text)

    # ----- input -----
    def on_area(self, event):
        self.s = min(1.0, max(0.0, event.x / float(AREA_W - 1)))
        self.v = min(1.0, max(0.0, 1 - event.y / float(AREA_H - 1)))
        self.refresh()

    def on_slider(self, key, value):
        if key == "H":
            self.h = min(0.999, value)
            self.redraw_area()
        elif key == "S":
            self.s = value
        else:
            self.v = value
        self.refresh()

    def _num(self, entry, top):
        try:
            return max(0, min(top, int(float(entry.get()))))
        except ValueError:
            return None

    def on_number(self, key, top):
        if self._busy:
            return
        val = self._num(self.boxes[key], top)
        if val is None:
            return
        if key == "H":
            self.h = (val % 360) / 360.0
            self.redraw_area()
        elif key == "S":
            self.s = val / 100.0
        else:
            self.v = val / 100.0
        self.refresh()

    def from_rgb(self):
        if self._busy:
            return
        vals = [self._num(self.boxes[k], 255) for k in "RGB"]
        if None not in vals:
            self.set_rgb(tuple(vals))

    def from_hex(self):
        if not self._busy:
            self.set_rgb(_parse(self.hex_box.get()))

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
