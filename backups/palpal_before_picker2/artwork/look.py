"""Artwork Tool: colourful buttons, and pop-up windows centred on the tool."""

import tkinter as tk

from PIL import Image, ImageDraw, ImageTk

# Tool buttons are coloured by their group; every other button by what it does
TOOL_GROUP_COLORS = {"Brush": "#ef9a9a", "Color": "#ffcc80", "Canvas": "#90caf9", "Shape": "#a5d6a7",
                     "Global": "#ce93d8", "Transform": "#80cbc4", "Batch": "#f48fb1"}
ACTION_COLORS = [  # (words in the button text, colour), first match wins
    (("delete", "clear", "cancel", "remove", "✖", "close"), "#ef5350"),
    (("undo", "redo", "↶", "↷", "reset", "−", "+"), "#ffca28"),
    (("export", "save"), "#ab47bc"),
    (("add", "new", "import", "load", "create", "apply", "clone", "paste", "copy", "blank", "generate",
      "refresh", "update"), "#66bb6a"),
]
DEFAULT_COLOR = "#42a5f5"


def _shade(color, f):
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(v * f))) for v in (r, g, b))


def _text_color(color):
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return "#1a1a1a" if 0.299 * r + 0.587 * g + 0.114 * b > 150 else "white"


def button_color(button):
    color = getattr(button, "_paint", None)
    if color:
        return color
    text = str(button.cget("text")).lower()
    for words, c in ACTION_COLORS:
        if any(w in text for w in words):
            return c
    return DEFAULT_COLOR


def _rounded(size, color, outline=None, radius=7, scale=4):
    """A rounded rectangle with transparent corners, drawn big and shrunk for smooth edges."""
    w, h = size
    big = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    d.rounded_rectangle((0, 0, w * scale - 1, h * scale - 1), radius=radius * scale, fill=color,
                        outline=outline, width=2 * scale if outline else 0)
    return big.resize((w, h), Image.Resampling.LANCZOS)


def round_button(btn, color, selected=False):
    """Turn a Tk button into a rounded, colored one (normal / hover / pressed images on a flat button)."""
    if not getattr(btn, "_round_size", None):
        btn._round_size = (btn.winfo_reqwidth() + 4, btn.winfo_reqheight())
    w, h = btn._round_size
    try:
        back = btn.master.cget("bg")
    except tk.TclError:
        back = "#F0F0F0"
    radius = max(3, min(8, h // 3))
    ring = _shade(color, 0.5) if selected else None
    imgs = {state: ImageTk.PhotoImage(_rounded((w, h), _shade(color, f), ring, radius), master=btn)
            for state, f in (("normal", 1.0), ("hover", 0.9), ("pressed", 0.78))}
    btn._round_imgs = imgs
    btn._round_color = color
    fg = _text_color(color)
    btn.configure(image=imgs["normal"], compound="center", width=w, height=h, relief="flat", bd=0,
                  highlightthickness=0, padx=0, pady=0, bg=back, activebackground=back, fg=fg,
                  activeforeground=fg, cursor="hand2")
    if not getattr(btn, "_round_bound", False):
        btn._round_bound = True

        def show(state):
            imgs_now = getattr(btn, "_round_imgs", None)
            if imgs_now and str(btn.cget("state")) != "disabled":
                btn.configure(image=imgs_now[state])

        btn.bind("<Enter>", lambda e: show("hover"), add="+")
        btn.bind("<Leave>", lambda e: show("normal"), add="+")
        btn.bind("<ButtonPress-1>", lambda e: show("pressed"), add="+")
        btn.bind("<ButtonRelease-1>", lambda e: show("hover"), add="+")

        def resized(event):
            # Buttons stretched by their layout (fill / sticky) get an image that fills the new size
            if (event.width, event.height) != btn._round_size and event.width > 1 and event.height > 1:
                btn._round_size = (event.width, event.height)
                round_button(btn, btn._round_color, getattr(btn, "_selected", False))

        btn.bind("<Configure>", resized, add="+")


def paint_buttons(widget):
    """Give every button under widget its colour, as a rounded button (buttons that chose their own look,
    _cp_keep, and empty swatch buttons are left alone)."""
    stack = [widget]
    while stack:
        w = stack.pop()
        stack.extend(w.winfo_children())
        if isinstance(w, tk.Button) and not getattr(w, "_cp_keep", False) and str(w.cget("text")).strip():
            round_button(w, button_color(w), getattr(w, "_selected", False))


def center_over(top, parent):
    """Put a window in the middle of parent (it starts hidden so it never flashes in the corner)."""
    top.update_idletasks()
    w, h = top.winfo_reqwidth(), top.winfo_reqheight()
    size = top.wm_geometry().split("+")[0]   # a size set with geometry() wins over the requested one
    if "x" in size and int(size.split("x")[0]) > 1:
        w, h = (int(v) for v in size.split("x"))
    px, py = parent.winfo_rootx(), parent.winfo_rooty()
    pw, ph = parent.winfo_width(), parent.winfo_height()
    if pw <= 1:  # parent not shown yet
        pw, ph = top.winfo_screenwidth(), top.winfo_screenheight()
        px = py = 0
    # Centred on the parent, but kept on the screen (with room for the taskbar)
    x = max(0, min(px + (pw - w) // 2, top.winfo_screenwidth() - w))
    y = max(0, min(py + (ph - h) // 2, top.winfo_screenheight() - h - 60))
    top.geometry("+%d+%d" % (x, y))
