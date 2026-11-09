"""Img2img Palette Swap: the console log (pop out, save)."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.storage import export_dir
from ..ui.theme import Theme


class ConsoleLog:
    """Activity console: lives in the adjuster, can pop out into its own window, saves to .txt."""

    def __init__(self, app, parent):
        self.app = app
        self.lines = []
        self.frame = tk.Frame(parent)
        bar = tk.Frame(self.frame)
        bar.pack(fill="x")
        tk.Label(bar, text="Console", font=("Arial", 9, "bold")).pack(side="left")
        tk.Button(bar, text="Save .txt", font=("Arial", 8), command=self.save).pack(side="right")
        tk.Button(bar, text="Pop out", font=("Arial", 8), command=self.pop_out).pack(side="right", padx=(0, 4))
        self.text = tk.Text(self.frame, height=6, font=("Consolas", 8), wrap="word")
        self.text.pack(fill="both", expand=True)
        self.popped = None

    def log(self, message):
        line = "[%s] %s" % (time.strftime("%H:%M:%S"), message)
        self.lines.append(line)
        for widget in (self.text, getattr(self.popped, "text_widget", None)):
            if widget is not None and widget.winfo_exists():
                widget.insert("end", line + "\n")
                widget.see("end")

    def pop_out(self):
        if self.popped is not None and self.popped.winfo_exists():
            self.popped.lift()
            return
        self.popped = tk.Toplevel(self.frame)
        self.popped.title("Adjuster Console")
        self.popped.geometry("560x320")
        self.popped.text_widget = tk.Text(self.popped, font=("Consolas", 9), wrap="word")
        self.popped.text_widget.pack(fill="both", expand=True)
        self.popped.text_widget.insert("end", "\n".join(self.lines) + ("\n" if self.lines else ""))
        tk.Button(self.popped, text="Save .txt", command=self.save).pack(anchor="e", padx=6, pady=4)
        Theme.apply(self.app, self.popped)

    def save(self):
        path = filedialog.asksaveasfilename(title="Save Console", defaultextension=".txt",
                                            filetypes=[("Text", "*.txt")], initialdir=export_dir("reports"),
                                            initialfile="adjuster console %s" % time.strftime("%Y-%m-%d %H%M%S"))
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.lines) + "\n")
