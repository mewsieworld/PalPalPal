"""Shared widgets: swatches, swatch grids and HSV rows."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.colors import to_hex


# ---------------------------------------------------------------------------
# Small shared widgets
# ---------------------------------------------------------------------------

def make_swatch(parent, size, **kw):
    canvas = tk.Canvas(parent, width=size, height=size, highlightthickness=0, bd=0, **kw)
    canvas._cp_keep = True
    canvas._cp_size = size
    return canvas


def draw_swatch(app, canvas, color, selected=False):
    size = canvas._cp_size
    dark = app.dark_mode
    canvas.configure(bg="#1E1E1E" if dark else "#F0F0F0")
    canvas.delete("all")
    if color is None:
        fill, outline = ("#1E1E1E", "#444444") if dark else ("white", "#888888")
    else:
        fill, outline = to_hex(color), ("#888888" if dark else "black")
    canvas.create_rectangle(1, 1, size - 1, size - 1, fill=fill, outline=outline)
    if selected:
        canvas.create_rectangle(1, 1, size - 1, size - 1, outline="red", width=2)


def swatch_grid(parent, indices, size, cols, on_left, on_right=None, height=None):
    """A vertically scrolling grid of palette swatches. Returns {palette_index: swatch canvas}."""
    sb = ttk.Scrollbar(parent, orient="vertical")
    sb.pack(side="right", fill="y")
    canvas = tk.Canvas(parent, highlightthickness=0, yscrollcommand=sb.set, **({"height": height} if height else {}))
    canvas.pack(side="left", fill="both", expand=True)
    sb.configure(command=canvas.yview)
    inner = tk.Frame(canvas)
    canvas.create_window((0, 0), window=inner, anchor="nw")
    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    def wheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    canvas.bind("<MouseWheel>", wheel)
    swatches = {}
    for pos, idx in enumerate(indices):
        sw = make_swatch(inner, size)
        sw.grid(row=pos // cols, column=pos % cols, padx=2, pady=2)
        sw.bind("<Button-1>", lambda e, i=idx: on_left(i, e))
        if on_right:
            sw.bind("<Button-3>", lambda e, i=idx: on_right(i, e))
        sw.bind("<MouseWheel>", wheel)
        swatches[idx] = sw
    return swatches


def relay_swatches(holder, indices, size, cols, on_click):
    """Rebuild just a swatch grid inside its holder (so an open Sort list survives); None if it's gone."""
    if holder is None or not holder.winfo_exists():
        return None
    for w in holder.winfo_children():
        w.destroy()
    return swatch_grid(holder, indices, size, cols, on_click)


def hsv_row(parent, row, label, var, lo, hi, on_change, label_width=4):
    """Label [value] [slider] in one row, the order the spec asks for."""
    tk.Label(parent, text=label, width=label_width, anchor="w", font=("Arial", 8)).grid(row=row, column=0, sticky="w")
    entry = tk.Entry(parent, textvariable=var, width=5, font=("Arial", 8), justify="right")
    entry.grid(row=row, column=1, sticky="w", padx=(2, 4))
    scale = tk.Scale(parent, from_=lo, to=hi, orient="horizontal", variable=var, showvalue=False,
                     sliderrelief="flat", sliderlength=14, width=9, bd=0, highlightthickness=0,
                     command=lambda *_: on_change())
    scale.grid(row=row, column=2, sticky="we", pady=1)
    parent.grid_columnconfigure(2, weight=1)

    def commit(_event=None):
        try:
            value = int(float(var.get()))
        except (tk.TclError, ValueError):
            value = 0
        var.set(max(lo, min(hi, value)))
        on_change()

    entry.bind("<Return>", commit)
    entry.bind("<FocusOut>", commit)
    return scale
