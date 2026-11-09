"""Yes / no prompts about colors: too many colors in an image, saving a sorted palette."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.storage import export_dir
from ..core.palettes import write_palette
from .dialogs import Dialog


def ask_excess_colors(app, excess, name="palette"):
    """Offer to keep palette colors the image never uses: save them to a named file and into Saved Colors."""
    if not excess or not app.store.get("show_excess_prompt"):
        return
    dlg = Dialog(app, "Excess colors")
    tk.Label(dlg.body, text="This palette has %d colors your image doesn't use, save them to a file?"
                            % len(excess), wraplength=360,
             justify="center").pack(pady=(0, 10))
    dont = tk.BooleanVar(value=False)
    row = tk.Frame(dlg.body)
    row.pack()
    tk.Button(row, text="Yes, save them", command=lambda: dlg.close(True)).pack(side="left", padx=5)
    tk.Button(row, text="No thanks", command=lambda: dlg.close(False)).pack(side="left", padx=5)
    tk.Checkbutton(dlg.body, text="Don't show again", variable=dont).pack(pady=(8, 0))
    dlg.finish()
    keep = dlg.show()
    if dont.get():
        app.store.set("show_excess_prompt", False)
    if not keep:
        return
    path = filedialog.asksaveasfilename(title="Save Excess Colors", defaultextension=".json",
                                        filetypes=SAVED_COLOR_TYPES, initialdir=export_dir("colors"),
                                        initialfile="%s excess colors" % name)
    if path:
        try:
            if path.lower().endswith(".json"):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump([list(c) for c in excess], f)
            else:
                write_palette(path, excess, app.store.get("pal_style"))
        except OSError as exc:
            messagebox.showerror("Save Excess Colors", "Could not save:\n%s" % exc)
    slots = app.saved_colors
    for color in excess:
        free = [i for i, c in enumerate(slots) if c is None]
        if not free:
            if len(slots) >= PALETTE_SIZE:
                break
            slots.extend([None] * min(10, PALETTE_SIZE - len(slots)))
            free = [i for i, c in enumerate(slots) if c is None]
        slots[free[0]] = color
    app.saved_colors_changed()


def ask_save_sorted(app, parent):
    """'Save with custom sorting?' Yes / No, with Don't ask again. Returns True, False, or None if closed."""
    dlg = Dialog(app, "Save", parent)
    tk.Label(dlg.body, text="Save with custom sorting?", font=("Arial", 10, "bold")).pack(pady=(0, 6))
    dont = tk.BooleanVar(value=False)
    tk.Checkbutton(dlg.body, text="Don't ask again", variable=dont).pack(anchor="w")
    row = tk.Frame(dlg.body)
    row.pack(pady=(10, 0))
    tk.Button(row, text="Yes", width=8, command=lambda: dlg.close(True)).pack(side="left", padx=4)
    tk.Button(row, text="No", width=8, command=lambda: dlg.close(False)).pack(side="left", padx=4)
    dlg.finish()
    answer = dlg.show()
    if dont.get() and answer is not None:
        app.store.set("save_sorted_choice", answer)
    return answer
