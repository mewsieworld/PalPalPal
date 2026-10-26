"""Help > Manual and Help > Changelog: show the Markdown files in src/docs/ inside the app.

The files are plain Markdown, so they can be edited in any text editor:
  # Big heading   ## Heading   ### Small heading   - bullet   **bold**   `code`   --- (a line)
The release exe carries a copy (PyInstaller --add-data src/docs). A docs/ folder next to the exe, if there
is one, wins over the bundled copy, so the manual can be updated without rebuilding.
"""

import re

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.storage import app_dir
from .theme import Theme, center_on

DOC_FILES = {"manual": ("manual.md", "PalPalPal Manual"), "changelog": ("changelog.md", "PalPalPal Changelog")}


def docs_dirs():
    """Where the docs are looked for, first match wins: next to the program, then inside the exe."""
    dirs = [os.path.join(app_dir(), "docs")]
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        dirs.append(os.path.join(bundled, "docs"))
    return dirs


def doc_path(kind):
    name = DOC_FILES[kind][0]
    for folder in docs_dirs():
        path = os.path.join(folder, name)
        if os.path.exists(path):
            return path
    return None


def read_doc(kind):
    path = doc_path(kind)
    if path is None:
        return "# %s\n\nThe file %s wasn't found in:\n\n%s" % (
            DOC_FILES[kind][1], DOC_FILES[kind][0], "\n".join("- `%s`" % d for d in docs_dirs()))
    with open(path, encoding="utf-8") as f:
        return f.read()


INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`)")


def headings(source):
    """(level, text) for every # and ## heading after the document's title."""
    out = []
    for line in source.splitlines():
        s = line.strip()
        if s.startswith("## "):
            out.append((2, s[3:]))
        elif s.startswith("# "):
            out.append((1, s[2:]))
    return out[1:]


def insert_contents(t, entries):
    """A clickable table of contents; each entry jumps to the mark of its heading."""
    t.insert("end", "Contents\n", "h2")
    nested = any(level == 1 for level, _text in entries)   # indent ## entries only under # entries
    for n, (level, text) in enumerate(entries):
        link = "toc_link_%d" % n
        t.insert("end", ("      " if level == 2 and nested else "  ") + "›  ", "bullet")
        t.insert("end", text + "\n", ("toc", link))
        t.tag_bind(link, "<Button-1>", lambda e, m="toc_%d" % n: t.yview(m))
    t.insert("end", "─" * 60 + "\n", "rule")


def render_markdown(text_widget, source):
    """A small Markdown subset into a Text widget: headings, bullets, numbered lines, bold, code and rules,
    with a table of contents under the title."""
    t = text_widget
    toc = headings(source)
    seen_title = False
    heading_no = 0
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("### "):
            t.insert("end", stripped[4:] + "\n", "h3")
            continue
        if stripped.startswith("## ") or stripped.startswith("# "):
            level = 2 if stripped.startswith("## ") else 1
            if level == 1 and not seen_title:
                seen_title = True
                t.insert("end", stripped[2:] + "\n", "h1")
                if toc:
                    insert_contents(t, toc)
                continue
            t.mark_set("toc_%d" % heading_no, "end-1c")
            t.mark_gravity("toc_%d" % heading_no, "left")
            heading_no += 1
            t.insert("end", stripped[level + 1:] + "\n", "h%d" % level)
            continue
        if stripped in ("---", "***"):
            t.insert("end", "─" * 60 + "\n", "rule")
            continue
        base = ()
        if re.match(r"^[-*] ", stripped):
            indent = "    " * (len(line) - len(line.lstrip(" ")) // 2)
            t.insert("end", indent + "  •  ", "bullet")
            stripped = stripped[2:]
            base = ("item",)
        elif re.match(r"^\d+\. ", stripped):
            num, stripped = stripped.split(" ", 1)
            t.insert("end", "  " + num + "  ", "bullet")
            base = ("item",)
        for part in INLINE.split(stripped):
            if part.startswith("**") and part.endswith("**") and len(part) > 4:
                t.insert("end", part[2:-2], base + ("bold",))
            elif part.startswith("`") and part.endswith("`") and len(part) > 2:
                t.insert("end", part[1:-1], base + ("code",))
            elif part:
                t.insert("end", part, base)
        t.insert("end", "\n")


class DocViewer:
    """A read-only window for the manual or the changelog."""

    def __init__(self, app, kind):
        self.app, self.kind = app, kind
        self.win = tk.Toplevel(app.master)
        self.win.title(DOC_FILES[kind][1])
        self.win.geometry("760x640")
        c = Theme.colors(app)
        # Close sits at the bottom right; packed first so it never gets squeezed out
        bottom = tk.Frame(self.win)
        bottom.pack(side="bottom", fill="x", padx=8, pady=(0, 8))
        tk.Button(bottom, text="Close", width=10, command=self.win.destroy).pack(side="right")
        body = tk.Frame(self.win)
        body.pack(fill="both", expand=True, padx=8, pady=8)
        sb = ttk.Scrollbar(body, orient="vertical")
        sb.pack(side="right", fill="y")
        self.text = tk.Text(body, wrap="word", yscrollcommand=sb.set, padx=14, pady=10, relief="flat",
                            font=("Segoe UI", 10), cursor="arrow")
        self.text.pack(side="left", fill="both", expand=True)
        sb.configure(command=self.text.yview)
        accent = c["accent"]
        self.text.tag_configure("h1", font=("Segoe UI", 18, "bold"), foreground=accent, spacing1=8, spacing3=6)
        self.text.tag_configure("h2", font=("Segoe UI", 14, "bold"), spacing1=10, spacing3=4)
        self.text.tag_configure("h3", font=("Segoe UI", 11, "bold"), spacing1=6, spacing3=2)
        self.text.tag_configure("bold", font=("Segoe UI", 10, "bold"))
        self.text.tag_configure("code", font=("Consolas", 10), background=c["select"])
        self.text.tag_configure("bullet", foreground=accent)
        self.text.tag_configure("item", lmargin2=36)
        self.text.tag_configure("rule", foreground="#888888")
        self.text.tag_configure("toc", foreground=accent, underline=True)
        self.text.tag_bind("toc", "<Enter>", lambda e: self.text.configure(cursor="hand2"))
        self.text.tag_bind("toc", "<Leave>", lambda e: self.text.configure(cursor="arrow"))
        self.text.bind("<MouseWheel>", lambda e: self.text.yview_scroll(int(-e.delta / 120), "units"))
        Theme.apply(app, self.win)
        self.load()
        center_on(self.win, app.master)

    def load(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        render_markdown(self.text, read_doc(self.kind))
        self.text.configure(state="disabled")


def open_doc(app, kind):
    DocViewer(app, kind)
