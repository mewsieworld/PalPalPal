"""Frames, palette layers and image layers."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .colors import pad256


class Frame:
    """One indexed picture (a still image, or one frame of an animation)."""

    def __init__(self, image, name, source_path=""):
        self.image = image
        self.name = name
        self.source_path = source_path
        raw = image.getpalette() or []
        self.palette = pad256([tuple(raw[i:i + 3]) for i in range(0, len(raw) - len(raw) % 3, 3)])
        t = image.info.get("transparency")
        self.transparent_index = t if isinstance(t, int) else None
        self._used = None

    def used_indices(self):
        if self._used is None:
            hist = self.image.histogram()[:PALETTE_SIZE]
            self._used = [i for i, count in enumerate(hist) if count]
        return self._used


class PaletteLayer:
    """A palette. owner is the ImageLayer it belongs to, or None for a stand-alone palette layer."""

    def __init__(self, name, colors, source_path="", active=True, owner=None):
        self.name = name
        self.colors = pad256(colors)
        self.loaded_colors = list(self.colors)
        self.source_path = source_path
        self.active = active
        self.owner = owner
        self.size = PALETTE_SIZE
        self.blend = "Normal"   # how a stand-alone palette mixes with the colors under it
        self.opacity = 1.0


def clone_palette(p, owner=None, name=None):
    q = PaletteLayer(name or p.name, list(p.colors), p.source_path, p.active, owner=owner)
    q.loaded_colors = list(p.loaded_colors)
    q.size, q.blend, q.opacity = p.size, p.blend, p.opacity
    return q


class ImageLayer:
    """An image (one or more frames) in the layer stack, with its own palette."""

    def __init__(self, name, frames, source_path=""):
        self.name = name
        self.frames = frames
        self.source_path = source_path
        self.visible = True
        self.opacity = 1.0
        self.blend = "Normal"
        # One palette, or one per frame when the document separates palettes by frames
        self.palettes = [PaletteLayer("%s palette" % name, frames[0].palette, source_path, owner=self)]
        self.palette_frame = 0   # the frame whose palette the editors show (the Layers box tab)
        # Which palette paints this image: "stack" (ticked palettes above it), "own", or one PaletteLayer
        self.palette_source = "stack"
        # Combined = the image shows and edits its own palette; separated = image only, colored from the stack
        self.combined = True
        self.height_map = None   # "L" image drawn for the 3D view's "drawn" height mode
        self.offset3d = (0, 0, 0)  # beads this layer was moved in the 3D view (x, y, up)

    @property
    def palette(self):
        return self.palettes[self.palette_frame % len(self.palettes)]

    @palette.setter
    def palette(self, value):
        self.palettes = [value]

    def palette_at(self, t):
        return self.palettes[t % len(self.frames) % len(self.palettes)] if len(self.palettes) > 1 else self.palettes[0]

    def split_palettes(self, on):
        """One palette per frame (copies of the current one), or back to the current frame's palette only."""
        if on:
            base = self.palette
            self.palettes = [base] + [clone_palette(base, self) for _ in self.frames[1:]]
        else:
            self.palettes = [self.palette]
        self.palette_frame = 0

    def sync_palette_count(self):
        """Keep one palette per frame after frames were added or removed."""
        if len(self.palettes) > 1:
            while len(self.palettes) < len(self.frames):
                self.palettes.append(clone_palette(self.palettes[-1], self))
            del self.palettes[len(self.frames):]

    @property
    def size(self):
        return max(f.image.width for f in self.frames), max(f.image.height for f in self.frames)

    def frame_at(self, t):
        return self.frames[t % len(self.frames)]
