"""Statistics and the dialog base classes (Dialog, ChoiceDialog, AllModeWarning)."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .theme import Theme, center_on


# ---------------------------------------------------------------------------
# Statistics, settings and small dialogs
# ---------------------------------------------------------------------------

class Statistics:
    """Local-only usage counters, kept in the __pycache__ user file."""

    FIELDS = [
        ("seconds_open", "Time in %s" % APP_NAME),
        ("sessions", "Times opened"),
        ("images_opened", "Images opened"),
        ("palettes_opened", "Palettes opened"),
        ("indexes_changed", "Index edits"),
        ("gradients_applied", "Gradients applied"),
        ("palettes_saved", "Palettes saved"),
        ("frames_exported", "Frames exported"),
        ("colors_saved", "Colors put in Saved Colors"),
        ("projects_saved", "Projects saved"),
    ]

    def __init__(self, store):
        self.store = store
        self.data = {key: 0 for key, _ in self.FIELDS}
        self.data.update(store.get("stats") or {})
        self.started = time.time()
        self.add("sessions")

    def add(self, key, amount=1):
        self.data[key] = self.data.get(key, 0) + amount

    def save(self):
        now = time.time()
        self.add("seconds_open", int(now - self.started))
        self.started = now
        self.store.set("stats", self.data)

    def lines(self):
        self.save()
        out = []
        for key, label in self.FIELDS:
            value = self.data.get(key, 0)
            if key == "seconds_open":
                value = "%dh %02dm" % (value // 3600, value % 3600 // 60)
            out.append("%s: %s" % (label, value))
        return out


class Dialog:
    """Small modal dialog base: themed, centred, returns self.result from show()."""

    def __init__(self, app, title, parent=None):
        self.app, self.result = app, None
        self.parent = parent or app.master
        self.win = tk.Toplevel(self.parent)
        self.win.title(title)
        self.win.resizable(False, False)
        self.win.transient(self.parent)
        self.win.protocol("WM_DELETE_WINDOW", lambda: self.close(None))
        self.body = tk.Frame(self.win)
        self.body.pack(padx=18, pady=14)

    def finish(self):
        Theme.apply(self.app, self.win)
        center_on(self.win, self.parent)
        self.win.grab_set()
        self.win.focus_set()

    def close(self, result):
        self.result = result
        self.win.destroy()

    def show(self):
        self.app.master.wait_window(self.win)
        return self.result


class ChoiceDialog(Dialog):
    """A message with a row of buttons; show() returns the chosen value (None if closed)."""

    def __init__(self, app, title, message, choices, parent=None, wrap=380):
        Dialog.__init__(self, app, title, parent)
        tk.Label(self.body, text=message, justify="center", wraplength=wrap).pack(pady=(0, 12))
        row = tk.Frame(self.body)
        row.pack()
        for label, value in choices:
            tk.Button(row, text=label, command=lambda v=value: self.close(v)).pack(side="left", padx=5)
        self.finish()


class AllModeWarning(Dialog):
    """The old 'All' preview warning for very long animations."""

    def __init__(self, app):
        Dialog.__init__(self, app, "Whoa there")
        tk.Label(self.body, text="This project has %d frames. Showing them all at once can be slow.\n"
                                 "Show them anyway?" % app.frame_count(), justify="center").pack(pady=(0, 10))
        buttons = tk.Frame(self.body)
        buttons.pack()
        tk.Button(buttons, text="Yeah I'm ballsy", command=lambda: self.done(True)).pack(side="left", padx=5)
        tk.Button(buttons, text="Nah I'm good", command=lambda: self.done(False)).pack(side="left", padx=5)
        self.dont_show = tk.BooleanVar(value=False)
        tk.Checkbutton(self.body, text="Don't show again", variable=self.dont_show).pack(pady=(10, 0))
        self.finish()

    def done(self, result):
        if self.dont_show.get():
            self.app.store.set("all_mode_warning", False)
        self.close(result)
