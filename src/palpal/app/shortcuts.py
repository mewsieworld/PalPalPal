"""PalPalPal main window: keyboard shortcuts, the View menu that lists them, and the Reverse Palette buttons.

    F Flip            R Rotate            B BG Options           V Reverse Palette
    S Super Swatch Switcher   C Artwork Tool   E Mass Frame Editor   W Img2img Palette Swap
    A next alignment  P next preview mode (Big / Small / No)    T next frame type (Single / All / Custom)
    Space play / pause (three quick presses: canvas back to the top-left at 100%)
    M Manual          H Changelog         Ctrl+S save   Ctrl+Shift+S save as   Ctrl+N new   Ctrl+O open
"""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..preview.canvas import ALIGNMENTS
from ..ui.docs_viewer import open_doc
from ..ui.theme import Tooltip

FRAME_TYPES = ["single", "all", "custom"]
TRIPLE_SPACE = 0.6   # seconds for three Space presses to count as one "reset the canvas"


class AppShortcutsMixin:
    def shortcut_actions(self):
        """key -> (menu label, action). Single letters are typed without Shift."""
        return {
            "f": ("Flip", self.toggle_flip),
            "r": ("Rotate", self.rotate_preview),
            "b": ("BG Options...", self.open_bg_options),
            "v": ("Reverse Palette", self.flip_selected_frame),
            "s": (SWITCHER_NAME, lambda: self.open_switcher(force=True)),
            "c": ("Artwork Tool", self.open_sprite_tool),
            "e": ("Mass Frame Editor (img2palette)", self.open_mass_editor),
            "w": ("Img2img Palette Swap", self.open_adjuster),
            "a": ("Next Alignment", self.cycle_alignment),
            "p": ("Next Preview Mode", self.cycle_preview_mode),
            "t": ("Next Frame Type", self.cycle_frame_type),
            "m": ("Manual", lambda: open_doc(self, "manual")),
            "h": ("Changelog", lambda: open_doc(self, "changelog")),
        }

    def bind_shortcuts(self):
        m = self.master
        for key, (_label, action) in self.shortcut_actions().items():
            m.bind(key, lambda e, a=action: self._shortcut(a))
        m.bind("d", lambda e: self._shortcut(self.debug_info) if self.store.get("show_debug_menu") else None)
        m.bind("<space>", lambda e: self._shortcut(self.space_pressed))
        m.bind("<Control-s>", lambda e: self.save_project())
        m.bind("<Control-S>", lambda e: self.save_project_as())          # Ctrl+Shift+S
        m.bind("<Control-Shift-S>", lambda e: self.save_project_as())
        m.bind("<Control-n>", lambda e: self.new_project())
        m.bind("<Control-o>", lambda e: self.open_project())
        m.bind_all("<Left>", lambda e: self._arrow(-1))
        m.bind_all("<Right>", lambda e: self._arrow(1))

    def build_view_menu(self, menubar):
        """View: everything that has a shortcut but no other menu home."""
        menu = tk.Menu(menubar, tearoff=0)
        acts = self.shortcut_actions()
        for key in ("f", "r", "v"):
            menu.add_command(label=acts[key][0], accelerator=key.upper(), command=acts[key][1])
        menu.add_separator()
        for key in ("a", "p", "t"):
            menu.add_command(label=acts[key][0], accelerator=key.upper(), command=acts[key][1])
        menu.add_separator()
        menu.add_command(label="Play / Pause", accelerator="Space", command=self.toggle_playback)
        menu.add_command(label="Reset Canvas (top-left, 100%)", accelerator="Space x3", command=self.reset_canvas)
        menubar.add_cascade(label="View", menu=menu)
        return menu

    # ----- the actions -----
    def cycle_alignment(self):
        anchors = [a for _label, a in ALIGNMENTS]
        current = self.current_alignment()
        self.set_alignment(anchors[(anchors.index(current) + 1) % len(anchors)] if current in anchors else anchors[0])

    def cycle_preview_mode(self):
        modes = list(PREVIEW_MODES)
        current = self.view_var.get()
        self.view_var.set(modes[(modes.index(current) + 1) % len(modes)] if current in modes else modes[0])
        self.choose_view_mode()

    def cycle_frame_type(self):
        current = self.preview_var.get()
        self.preview_var.set(FRAME_TYPES[(FRAME_TYPES.index(current) + 1) % 3] if current in FRAME_TYPES else "single")
        self.on_preview_mode_change()

    def space_pressed(self):
        """Space plays / pauses; three quick presses put the canvas back at the top-left at 100% instead."""
        now = time.time()
        presses = [t for t in getattr(self, "_space_times", []) if now - t < TRIPLE_SPACE] + [now]
        if len(presses) == 1:
            self._space_playing = self.playing   # what playback was before this burst
        self._space_times = presses
        if len(presses) >= 3:
            self._space_times = []
            if self.playing != getattr(self, "_space_playing", self.playing):
                self.toggle_playback()   # undo the two play / pause toggles of the burst
            self.reset_canvas()
            return
        self.toggle_playback()

    def reset_canvas(self):
        self.zoom_var.set("100%")
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)
        self.request_redraw()
        self.master.after(60, lambda: (self.canvas.xview_moveto(0), self.canvas.yview_moveto(0)))

    # ----- Reverse Palette buttons, next to Rotate (bottom strip and the Small / No Preview bar) -----
    def reverse_button(self, parent):
        btn = tk.Button(parent, text="Reverse Palette", command=self.flip_selected_frame)
        Tooltip(btn, "Reverse the color order of the selected layer's palette on this frame (V)", self)
        return btn
