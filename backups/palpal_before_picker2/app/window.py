"""PalPalPal main window: the class that ties the mixins together, and main()."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..preview.heights import HeightSettings
from ..core.storage import UserStore
from ..core.colors import parse_color_any
from ..core.images import ImageLayer, PaletteLayer
from ..ui.theme import Theme
from ..ui.dialogs import Statistics
from ..ui.compact import CompactEditor
from .build import AppUiMixin
from .view import AppViewMixin
from .layers import AppLayersMixin
from .frames import AppFramesMixin
from .frame_select import AppFrameSelectMixin
from .help_menu import AppHelpMixin
from .files import AppFilesMixin
from .tools import AppToolsMixin


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class PalPalPal(AppUiMixin, AppViewMixin, AppLayersMixin, AppFramesMixin, AppFrameSelectMixin, AppFilesMixin,
                AppToolsMixin, AppHelpMixin):
    START_MESSAGE = "START A NEW PROJECT, OPEN A PROJECT, OR READ THE MANUAL TO GET STARTED!"

    def __init__(self, master):
        self.master = master
        self.store = UserStore()
        self.dark_mode = bool(self.store.get("dark_mode"))
        self.use_right_click = bool(self.store.get("use_right_click"))
        saved = [parse_color_any(c) for c in (self.store.get("saved_colors") or [])][:PALETTE_SIZE]
        self.saved_colors = saved + [None] * max(0, DEFAULT_SAVED_SLOTS - len(saved))
        self.saved_panels = []

        self.stack = []            # bottom -> top: ImageLayer and stand-alone PaletteLayer entries
        self.current_frame = 0
        self.hidden_frames = set()
        self.selected_layer = -1   # index into self.layers (every palette in the project)
        self.sprite_tool = None
        self.split_palettes = False   # Document Settings: a palette per frame, shown as Layers box tabs
        self.palette_tab = 0
        self.layer_filter = "all"     # Layers box: all, images or palettes
        self.heights = HeightSettings()  # Document Settings > 3D height settings
        self.key_color = None
        self.bg_color = (255, 255, 255)
        self.flip = False
        self.rotation = 0
        self.project_path = None
        self.dirty = False
        self.switcher = None
        self.mass_editor = None
        self.adjuster = None
        self._redraw_job = None
        self._zoom_acc = 0
        self._auto_no_preview = None
        self.selected_frames = set()
        self.visibility_history = []
        self.custom_pos = 0
        self.loop_range = None        # (first, last) timeline frames for playback, or None for all
        self.playing = False
        self._play_job = None
        self.frame_clipboard = None
        self.stats = Statistics(self.store)
        self.compact = CompactEditor(self)

        self.zoom_var = tk.StringVar(value="Fit")
        self.preview_var = tk.StringVar(value="single")
        mode = self.store.get("preview_mode")
        self.view_var = tk.StringVar(value=mode if mode in PREVIEW_MODES else PREVIEW_MODES[0])
        self.view_3d_var = tk.BooleanVar(value=bool(self.store.get("view_3d")))

        self.create_ui()
        Theme.apply(self)
        self.apply_view_mode()
        self.update_title()
        self.master.protocol("WM_DELETE_WINDOW", self.on_quit)

    # ----- project model -----
    @property
    def layers(self):
        """Every palette in the project, bottom to top (image palettes and stand-alone ones)."""
        return [e.palette if isinstance(e, ImageLayer) else e for e in self.stack]

    @property
    def view_3d(self):
        return self.view_3d_var.get() and self.preview_var.get() == "single"

    def image_layers(self):
        return [e for e in self.stack if isinstance(e, ImageLayer)]

    def visible_image_layers(self):
        return [il for il in self.image_layers() if il.visible]

    def frame_count(self):
        return max([len(il.frames) for il in self.image_layers()] or [0])

    def canvas_size(self):
        layers = self.image_layers()
        if not layers:
            return 1, 1
        return max(il.size[0] for il in layers), max(il.size[1] for il in layers)

    def selected_palette(self):
        layers = self.layers
        return layers[self.selected_layer] if 0 <= self.selected_layer < len(layers) else None

    def entry_of(self, palette):
        return palette.owner if palette is not None and palette.owner is not None else palette

    def images_colored_by(self, palette):
        """Image layers a palette colors: its own image, or the nearest image below a stand-alone palette."""
        if palette is None:
            return []
        if palette.owner is not None:
            return [palette.owner]
        out = [il for il in self.image_layers() if il.palette_source is palette]
        pos = self.stack.index(palette)
        for entry in reversed(self.stack[:pos]):
            if isinstance(entry, ImageLayer):
                if entry.palette_source == "stack" and entry not in out:
                    out.append(entry)
                break
        return out

    def stacked_palettes(self, il):
        """The stand-alone palettes laid over an image layer, bottom to top, per its palette source."""
        src = il.palette_source
        if src == "own" or il not in self.stack:
            return []
        if isinstance(src, PaletteLayer):
            if src in self.stack:
                return [src]
            il.palette_source = "stack"  # the chosen palette was removed
        out = []
        for entry in self.stack[self.stack.index(il) + 1:]:
            if isinstance(entry, ImageLayer):
                break
            if entry.active:
                out.append(entry)
        return out

    def palette_coloring(self, il):
        """The palette actually painting an image layer: the top one laid over it, else its own."""
        if not il.combined and il.palette_source == "own":
            il.palette_source = "stack"  # an image-only layer has no palette of its own to show
        over = self.stacked_palettes(il)
        return over[-1] if over else il.palette

    def is_key(self, color):
        return self.key_color is not None and tuple(color[:3]) == tuple(self.key_color)

    def key_indices(self, frame, palette):
        keys = set()
        if frame.transparent_index is not None:
            keys.add(frame.transparent_index)
        if self.key_color is not None:
            keys.update(i for i, c in enumerate(palette) if self.is_key(c))
        return keys

    def editable_indices(self, palette=None):
        palette = palette if palette is not None else self.selected_palette()
        images = self.images_colored_by(palette)
        if not images:
            return list(range(palette.size if palette is not None else PALETTE_SIZE))
        used = set()
        for il in images:
            for f in il.frames:
                used.update(f.used_indices())
        if self.key_color is not None:
            used = {i for i in used if not self.is_key(palette.colors[i])}
        return sorted(used)


def main():
    root = tk.Tk()
    PalPalPal(root)
    root.mainloop()
