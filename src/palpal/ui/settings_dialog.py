"""Settings (gear menu) and the Credits box."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.storage import UserStore
from .theme import Theme, center_on
from .dialogs import Dialog


CREDITS_TEXT = ("For the Glowing Kitties in the Atomic Priesthood.\n\n"
                "Don't Change Color, Kitty. Not for anyone.")


class SettingsDialog(Dialog):
    """The gear menu: custom frame settings and frame numbers (the rest is in Document & 3D Settings)."""

    def __init__(self, app):
        Dialog.__init__(self, app, "Frame Settings")
        s = app.store
        main = self.body
        tk.Label(main, text="Custom Frame Settings", font=("Arial", 12, "bold")).pack(pady=(0, 8))
        nums = tk.Frame(main)
        nums.pack(fill="x")
        last = max(1, app.frame_count())
        self.count = tk.StringVar(value=str(s.get("custom_count")))
        self.start = tk.StringVar(value=str(s.get("custom_start")))
        self.end = tk.StringVar(value=str(s.get("custom_end") or last))
        for row, (label, var) in enumerate((("Number of Frames:", self.count), ("Start Frame:", self.start),
                                            ("End Frame:", self.end))):
            tk.Label(nums, text=label).grid(row=row, column=0, sticky="w", pady=1)
            tk.Entry(nums, textvariable=var, width=6).grid(row=row, column=1, sticky="w", padx=(6, 0))
        tk.Label(nums, text="(of %d)" % last, fg="gray").grid(row=2, column=2, sticky="w", padx=(4, 0))
        self.labels = tk.BooleanVar(value=bool(s.get("show_frame_labels")))
        tk.Checkbutton(main, text="Show Frame Numbers", variable=self.labels).pack(anchor="w", pady=(6, 0))

        self.error = tk.Label(main, text="", fg="red", wraplength=260)
        self.error.pack()

        buttons = tk.Frame(main)
        buttons.pack(pady=(6, 0))
        tk.Button(buttons, text="Credits ♥", command=self.show_credits).pack(side="left", padx=(0, 10))
        tk.Button(buttons, text="OK", width=12, command=self.ok).pack(side="left")
        tk.Button(buttons, text="Cancel", width=8, command=lambda: self.close(None)).pack(side="left", padx=(6, 0))
        tk.Button(main, text="Reset to default settings", relief="flat", fg="gray", font=("Arial", 8, "underline"),
                  command=self.defaults).pack(pady=(8, 0))
        self.finish()

    def defaults(self):
        d = UserStore.DEFAULTS
        self.count.set(str(d["custom_count"]))
        self.start.set(str(d["custom_start"]))
        self.end.set(str(max(1, self.app.frame_count())))
        self.labels.set(d["show_frame_labels"])

    def ok(self):
        try:
            count, start, end = int(self.count.get()), int(self.start.get()), int(self.end.get())
        except ValueError:
            self.error.configure(text="Frame numbers must be whole numbers.")
            return
        last = max(1, self.app.frame_count())
        if count < 1 or start < 1 or end < start or (self.app.frame_count() and end > last):
            self.error.configure(text="Use at least 1 frame, and a start frame no later than the end frame "
                                      "(1 to %d)." % last)
            return
        s = self.app.store
        s.data.update(custom_count=count, custom_start=start, custom_end=0 if end == last else end,
                      show_frame_labels=self.labels.get())
        s.save()
        self.close(True)
        self.app.request_redraw()

    def show_credits(self):
        show_credits(self.app, self.win)


def show_credits(app, parent):
    win = tk.Toplevel(parent)
    win.title("Credits")
    win.resizable(False, False)
    tk.Label(win, text=CREDITS_TEXT, font=("Arial", 11), justify="center", padx=30, pady=20).pack()
    tk.Button(win, text="Close", command=win.destroy).pack(pady=(0, 12))
    Theme.apply(app, win)
    center_on(win, parent)
