"""Rounded buttons with depth, for any Tk button: a soft shadow under the button, a thin light edge along the
top and a darker one along the bottom (like light falling from above), and the button sinks 1px when pressed.
No gradient fill: the face stays one flat color.

    round_button(button, "#42a5f5")            # normal look
    round_button(button, "#42a5f5", True)      # with a ring (the selected tool)
"""

import tkinter as tk

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageTk

SCALE = 4   # drawn 4x bigger and shrunk, for smooth corners


def shade(color, f):
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(v * f))) for v in (r, g, b))


def lighten(color, amount):
    """Mix toward white by amount (0-1)."""
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(int(v + (255 - v) * amount) for v in (r, g, b))


def text_color(color):
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return "#1a1a1a" if 0.299 * r + 0.587 * g + 0.114 * b > 150 else "white"


def _rgba(color, alpha):
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return (r, g, b, alpha)


def button_face(size, color, state="normal", ring=None, radius=7):
    """The button picture: shadow, face, top light edge, bottom dark edge (and a ring when selected)."""
    w, h = size
    s = SCALE
    W, H = w * s, h * s
    r = radius * s
    pressed = state == "pressed"
    face = shade(color, {"normal": 1.0, "hover": 0.94, "pressed": 0.86}[state])
    sink = s if pressed else 0                      # the face drops 1px when pressed
    body = (s, sink, W - s - 1, H - 3 * s - 1 + sink)

    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # soft shadow: smaller and fainter while pressed (the button is "closer" to the surface)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    off = s if pressed else 2 * s
    ImageDraw.Draw(shadow).rounded_rectangle((body[0], body[1] + off, body[2], body[3] + off), radius=r,
                                             fill=(0, 0, 0, 55 if pressed else 85))
    out = Image.alpha_composite(out, shadow.filter(ImageFilter.GaussianBlur(1.6 * s)))
    # flat face
    d = ImageDraw.Draw(out)
    d.rounded_rectangle(body, radius=r, fill=_rgba(face, 255))
    # edges: a light line on the top half of the rim, a dark line on the bottom half
    rim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(rim).rounded_rectangle(body, radius=r, outline=_rgba(lighten(face, 0.45), 200), width=s)
    # the rim fades from light (top) to dark (bottom) over the button's middle, so there's no seam
    top_mask = Image.new("L", (1, H), 0)
    mid0, mid1 = body[1] + (body[3] - body[1]) * 0.3, body[1] + (body[3] - body[1]) * 0.7
    for y in range(H):
        top_mask.putpixel((0, y), int(255 * min(1.0, max(0.0, (mid1 - y) / float(mid1 - mid0)))))
    top_mask = top_mask.resize((W, H))
    rim.putalpha(ImageChops.multiply(rim.getchannel("A"), top_mask))
    out = Image.alpha_composite(out, rim)
    low = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(low).rounded_rectangle(body, radius=r, outline=_rgba(shade(face, 0.72), 220), width=s)
    low.putalpha(ImageChops.multiply(low.getchannel("A"), ImageChops.invert(top_mask)))
    out = Image.alpha_composite(out, low)
    if ring:
        ImageDraw.Draw(out).rounded_rectangle(body, radius=r, outline=_rgba(ring, 255), width=2 * s)
    return out.resize((w, h), Image.Resampling.LANCZOS)


def round_button(btn, color, selected=False):
    """Turn a Tk button into a rounded, colored one with depth (normal / hover / pressed pictures)."""
    if not getattr(btn, "_round_size", None):
        btn._round_size = (btn.winfo_reqwidth() + 4, btn.winfo_reqheight() + 3)
    w, h = btn._round_size
    try:
        back = btn.master.cget("bg")
    except tk.TclError:
        back = "#F0F0F0"
    radius = max(3, min(8, (h - 3) // 3))
    ring = shade(color, 0.45) if selected else None
    btn._round_imgs = {state: ImageTk.PhotoImage(button_face((w, h), color, state, ring, radius), master=btn)
                       for state in ("normal", "hover", "pressed")}
    btn._round_color = color
    fg = text_color(color)
    btn.configure(image=btn._round_imgs["normal"], compound="center", width=w, height=h, relief="flat", bd=0,
                  highlightthickness=0, padx=0, pady=0, bg=back, activebackground=back, fg=fg,
                  activeforeground=fg, cursor="hand2")
    if not getattr(btn, "_round_bound", False):
        btn._round_bound = True

        def show(state):
            imgs = getattr(btn, "_round_imgs", None)
            if imgs and str(btn.cget("state")) != "disabled":
                btn.configure(image=imgs[state])

        def resized(event):
            # Buttons stretched by their layout (fill / sticky) get a picture that fills the new size
            if (event.width, event.height) != btn._round_size and event.width > 1 and event.height > 1:
                btn._round_size = (event.width, event.height)
                round_button(btn, btn._round_color, getattr(btn, "_selected", False))

        btn.bind("<Enter>", lambda e: show("hover"), add="+")
        btn.bind("<Leave>", lambda e: show("normal"), add="+")
        btn.bind("<ButtonPress-1>", lambda e: show("pressed"), add="+")
        btn.bind("<ButtonRelease-1>", lambda e: show("hover"), add="+")
        btn.bind("<Configure>", resized, add="+")
