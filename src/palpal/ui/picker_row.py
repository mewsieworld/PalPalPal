"""The color picker row (eyedropper + hex box) and its pick mode."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .theme import Tooltip


def picker_row(parent, owner):
    """Index: [ ] [Go] Hex #: [ ] [🎨 Pick] [Apply, only while picking] ........ [🌈]

    owner needs idx_var, hex_var, goto_index(), apply_hex_entry(), toggle_pick(), open_gradient().
    """
    row = tk.Frame(parent)
    tk.Label(row, text="Index:").pack(side="left")
    idx = tk.Entry(row, textvariable=owner.idx_var, width=4)
    idx.pack(side="left", padx=(2, 2))
    idx.bind("<Return>", lambda e: owner.goto_index())
    tk.Button(row, text="Go", command=owner.goto_index).pack(side="left", padx=(0, 8))
    tk.Label(row, text="Hex #:").pack(side="left")
    hx = tk.Entry(row, textvariable=owner.hex_var, width=8)
    hx.pack(side="left", padx=(2, 4))
    hx.bind("<Return>", lambda e: owner.apply_hex_entry())
    owner.pick_btn = tk.Button(row, text="🎨 Exit" if owner.picking else "🎨 Pick", command=owner.toggle_pick)
    owner.pick_btn.pack(side="left")
    owner.apply_btn = tk.Button(row, text="Apply", command=owner.apply_hex_entry)
    if owner.picking:
        owner.apply_btn.pack(side="left", padx=(4, 0))
    grad = tk.Button(row, text="🌈", command=owner.open_gradient, bg="#FF4081", fg="white",
                     activebackground="#E91E63", font=("Arial", 9, "bold"), width=4)
    grad._cp_keep = True
    grad.pack(side="right")
    Tooltip(grad, "Gradient", owner.app)
    return row


def set_pick_mode(owner, on):
    """Shared Pick/Exit behaviour: Apply only shows while Pick says Exit."""
    owner.picking = on
    try:
        owner.pick_btn.configure(text="🎨 Exit" if on else "🎨 Pick")
        if on:
            owner.apply_btn.pack(side="left", padx=(4, 0), after=owner.pick_btn)
        else:
            owner.apply_btn.pack_forget()
    except (tk.TclError, AttributeError):
        pass
