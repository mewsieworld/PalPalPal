"""Settings, BG Options, Document Settings, New Project and the other small dialogs."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .color_picker import app_askcolor
from ..core.storage import UserStore, export_dir
from ..core.colors import to_hex
from ..core.palettes import write_palette
from .theme import Theme, Tooltip, center_on


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


CREDITS_TEXT = ("For the Glowing Kitties in the Atomic Priesthood.\n\n"
                "Don't Change Color, Kitty. Not for anyone.")


class SettingsDialog(Dialog):
    """The gear menu: custom frame settings and frame numbers (the rest is in Document Settings)."""

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


class BGOptionsDialog(Dialog):
    """BG Color (preview background) and Palette BG Color (the key / void color), in one place."""

    def __init__(self, app):
        Dialog.__init__(self, app, "BG Options")
        self.bg = app.bg_color
        self.key = app.key_color
        grid = tk.Frame(self.body)
        grid.pack()
        tk.Label(grid, text="BG Color:").grid(row=0, column=0, sticky="w", pady=3)
        self.bg_btn = tk.Button(grid, width=12, command=self.pick_bg)
        self.bg_btn._cp_keep = True
        self.bg_btn.grid(row=0, column=1, sticky="w", padx=(10, 0))
        clear_bg = tk.Button(grid, text="✖", width=2, command=self.clear_bg)
        clear_bg.grid(row=0, column=2, padx=(4, 0))
        Tooltip(clear_bg, "No BG color (transparent)", app)
        tk.Label(grid, text="Palette BG Color:").grid(row=1, column=0, sticky="w", pady=3)
        self.key_btn = tk.Button(grid, width=12, command=self.pick_key)
        self.key_btn._cp_keep = True
        self.key_btn.grid(row=1, column=1, sticky="w", padx=(10, 0))
        clear = tk.Button(grid, text="✖", width=2, command=self.clear_key)
        clear.grid(row=1, column=2, padx=(4, 0))
        Tooltip(clear, "No palette BG color", app)
        tk.Label(self.body, text="Palette slots with the Palette BG Color show as see-through.",
                 fg="gray", font=("Arial", 8)).pack(pady=(6, 0))
        self.hide = tk.BooleanVar(value=bool(app.store.get("bg_options_in_menu")))
        tk.Checkbutton(self.body, text="Hide this menu on the Options Menu", variable=self.hide).pack(anchor="w",
                                                                                                    pady=(8, 0))
        buttons = tk.Frame(self.body)
        buttons.pack(pady=(10, 0))
        tk.Button(buttons, text="Ok", width=8, command=self.ok).pack(side="left", padx=4)
        tk.Button(buttons, text="Cancel", width=8, command=lambda: self.close(None)).pack(side="left", padx=4)
        self.finish()
        self.refresh()

    def _show(self, btn, color):
        if color is None:
            c = Theme.colors(self.app)
            btn.configure(text="none", bg=c["button"], fg=c["fg"], activebackground=c["hover"])
        else:
            btn.configure(text=to_hex(color, False), bg=to_hex(color), activebackground=to_hex(color),
                          fg="black" if sum(color) > 380 else "white")

    def refresh(self):
        self._show(self.bg_btn, self.bg)
        self._show(self.key_btn, self.key)

    def clear_bg(self):
        self.bg = None
        self.refresh()

    def pick_bg(self):
        result = app_askcolor(self.app, color=to_hex(self.bg) if self.bg else None, title="BG Color", parent=self.win)
        if result and result[0]:
            self.bg = tuple(int(v) for v in result[0])
            self.refresh()

    def pick_key(self):
        result = app_askcolor(self.app, color=to_hex(self.key) if self.key else None, title="Palette BG Color",
                                       parent=self.win)
        if result and result[0]:
            self.key = tuple(int(v) for v in result[0])
            self.refresh()

    def clear_key(self):
        self.key = None
        self.refresh()

    def ok(self):
        self.app.store.set("bg_options_in_menu", self.hide.get())
        self.app.bg_color = self.bg
        self.close(True)
        self.app.set_key_color(self.key)
        self.app.update_bottom_bar()
        self.app.mark_dirty()
        self.app.request_redraw()


def color_count_picker(parent, count, count_text, on_change, question="How many colors in your color palette?"):
    """The New Project palette-size slider with its number box (shared with Document Settings)."""
    tk.Label(parent, text=question, font=("Arial", 11, "bold")).pack(anchor="w")
    scale = tk.Scale(parent, from_=NewProjectDialog.MIN_COLORS, to=PALETTE_SIZE, orient="horizontal", variable=count,
                     showvalue=False, length=460, sliderrelief="flat", sliderlength=16, width=12, bd=0,
                     highlightthickness=0, command=lambda *_: on_change())
    scale.pack(fill="x", pady=(6, 2))
    ends = tk.Frame(parent)
    ends.pack(fill="x")
    tk.Label(ends, text="as limited of\na palette as\npossible", justify="left", font=("Arial", 8)).pack(side="left")
    tk.Label(ends, text="full 256 palette/i dunno!", font=("Arial", 8)).pack(side="right", anchor="n")
    middle = tk.Frame(ends)
    middle.pack(side="left", expand=True)
    entry = tk.Entry(middle, textvariable=count_text, width=6, justify="center")
    entry.pack()

    def typed(_event=None):
        try:
            n = int(float(count_text.get()))
        except ValueError:
            n = count.get()
        count.set(max(NewProjectDialog.MIN_COLORS, min(PALETTE_SIZE, n)))
        on_change()

    entry.bind("<Return>", typed)
    entry.bind("<FocusOut>", typed)
    tk.Label(middle, text="(input a real number here, if you want)", font=("Arial", 8), fg="gray").pack()
    return typed


class NewProjectDialog(Dialog):
    """Palette size slider + number box, and the optional background (key) color question."""

    MIN_COLORS = 2

    def __init__(self, app, ask_key=True):
        Dialog.__init__(self, app, "New Project" if ask_key else "Palette size")
        self.ask_key = ask_key
        b = self.body
        self.count = tk.IntVar(value=PALETTE_SIZE)
        self.count_text = tk.StringVar(value=str(PALETTE_SIZE))
        self._typed = color_count_picker(b, self.count, self.count_text, self.slider_moved)

        self.key_box = tk.LabelFrame(b, text="What color is your palette's background color?")
        if ask_key:
            self.key_box.pack(fill="x", pady=(12, 0))
        self.key_mode = tk.StringVar(value="later")
        self.key_widgets = [
            tk.Radiobutton(self.key_box, text="Colorpick one now", variable=self.key_mode, value="now"),
            tk.Radiobutton(self.key_box, text="Colorpick one later", variable=self.key_mode, value="later"),
        ]
        for w in self.key_widgets:
            w.pack(anchor="w", padx=6)
        self.remember = tk.BooleanVar(value=False)
        remember = tk.Checkbutton(self.key_box, text="Remember my choice and fly through the prompts next time",
                                  variable=self.remember)
        remember.pack(anchor="w", padx=6, pady=(2, 4))
        self.key_widgets.append(remember)

        buttons = tk.Frame(b)
        buttons.pack(pady=(12, 0))
        tk.Button(buttons, text="Continue", width=10, command=self.ok).pack(side="left", padx=4)
        tk.Button(buttons, text="Cancel", width=8, command=lambda: self.close(None)).pack(side="left", padx=4)
        self.finish()
        self.slider_moved()

    def slider_moved(self):
        n = self.count.get()
        self.count_text.set(str(n))
        # The background question is optional for the most limited palettes, so it greys out there
        state = "disabled" if n <= self.MIN_COLORS else "normal"
        for w in self.key_widgets:
            w.configure(state=state)

    def typed(self):
        self._typed()

    def ok(self):
        self.typed()
        n = self.count.get()
        key_mode = self.key_mode.get() if n > self.MIN_COLORS else "later"
        result = {"colors": n, "key": key_mode}
        if self.ask_key and self.remember.get():
            self.app.store.set("new_project_remember", result)
        self.close(result)


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
