"""Artwork Tool: colourful buttons, and pop-up windows centred on the tool."""

import tkinter as tk

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


def paint_buttons(widget):
    """Give every button under widget its colour (buttons that already chose one, _cp_keep, are left alone)."""
    stack = [widget]
    while stack:
        w = stack.pop()
        stack.extend(w.winfo_children())
        if isinstance(w, tk.Button) and not getattr(w, "_cp_keep", False) and str(w.cget("text")).strip():
            c = button_color(w)
            w.configure(bg=c, activebackground=_shade(c, 0.85), fg=_text_color(c), activeforeground=_text_color(c))


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
