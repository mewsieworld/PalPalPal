"""New Project: palette size and key color questions, and the color count picker."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .dialogs import Dialog
from .theme import hint


def color_count_picker(parent, count, count_text, on_change, question="How many colors in your color palette?"):
    """The New Project palette-size slider with its number box (shared with Document & 3D Settings)."""
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
    hint(tk.Label(middle, text="(input a real number here, if you want)", font=("Arial", 8), fg="gray"))
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
