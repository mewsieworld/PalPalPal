"""The Image to Image Palette Adjuster."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.storage import export_dir
from ..core.colors import to_hex
from ..core.images import convert_image, sample_unique_colors
from ..core.layers import Frame, ImageLayer
from ..ui.theme import Theme, center_on
from ..ui.dialogs import ChoiceDialog
from .mapper import MapperMixin
from .layout import AdjusterLayoutMixin
from .view import AdjusterViewMixin
from .mapping import AdjusterMappingMixin


class ImageToImageAdjuster(MapperMixin, AdjusterLayoutMixin, AdjusterViewMixin, AdjusterMappingMixin):
    """Recolor a source picture with a reference picture's colors, by mapping source colors onto reference
    colors. Layout follows Mew's spec: thumbnails at the top, the result canvas in the middle, Filters &
    Options below it, Advanced Options and the console tucked behind a checkbox."""

    def __init__(self, app):
        self.app = app
        self.source = None          # RGBA images
        self.reference = None
        self.source_palette = []    # source colors by index (from the source picture)
        self.target_palette = []    # target colors by index (from the reference picture)
        self.color_map = {}         # source index -> rgb
        self.selected_source = None
        self.selected_target = None
        self.modified_target = None
        self.tolerance = 0
        self.filters = {"hue": 0, "saturation": 100, "brightness": 100, "contrast": 100}
        self.eyedropper = False
        self.mapper = None
        self.result = None
        self._job = None
        self._map_cache = {}
        self.view_mode = "source"     # what the canvas shows: source (live result), reference, or both
        self.view_xform = {"source": [False, 0], "reference": [False, 0]}   # [flip, quarter turns]
        self.active_view = "source"
        self.regions = []
        self._thumb_job = None
        self.mapper_undo, self.mapper_redo = [], []

        self.win = tk.Toplevel(app.master)
        self.win.title("Image to Image Palette Adjuster")
        self.win.geometry("900x820")
        self.win.minsize(760, 640)
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.build()
        Theme.apply(app, self.win)
        center_on(self.win, app.master)
        self.show_prompt()

    def _load(self, title):
        path = filedialog.askopenfilename(title=title, filetypes=IMAGE_OPEN_TYPES, parent=self.win)
        if not path:
            return None
        try:
            img = Image.open(path)
            img.load()
            return img.convert("RGBA")
        except Exception as exc:
            messagebox.showerror(title, "Could not read that image:\n%s" % exc, parent=self.win)
            return None

    def use_current_frame(self):
        if not self.app.frame_count():
            messagebox.showinfo("Source", "There is no image in the project yet.", parent=self.win)
            return
        self.source = self.app.composite(self.app.current_frame, background=False)
        self.log("Source: current project frame %d (%dx%d)" % (self.app.current_frame + 1, *self.source.size))
        self.after_load()

    def choose_source(self):
        img = self._load("Choose a Source Image")
        if img is not None:
            self.source = img
            self.log("Source image loaded (%dx%d)" % img.size)
            self.after_load()

    def choose_reference(self):
        img = self._load("Choose a color reference file")
        if img is not None:
            self.reference = img
            self.log("Color reference loaded (%dx%d)" % img.size)
            self.after_load()

    def after_load(self):
        for label, img in ((self.thumb_src, self.source), (self.thumb_ref, self.reference)):
            if img is not None:
                thumb = img.copy()
                thumb.thumbnail((96, 72), Image.Resampling.NEAREST)
                label.photo = ImageTk.PhotoImage(thumb)
                label.configure(image=label.photo, width=96, height=72, text="")
        if self.source is None or self.reference is None:
            self.show_prompt()
            return
        self.analyze()

    def analyze(self):
        self.source_palette = sample_unique_colors(self.source)
        self.target_palette = sample_unique_colors(self.reference)
        self.color_map = {i: c for i, c in enumerate(self.source_palette)}
        self._map_cache = {}
        self.selected_source = self.selected_target = self.modified_target = None
        self.log("Palettes extracted. Source size: %d, Target size: %d." % (len(self.source_palette),
                                                                            len(self.target_palette)))
        self.refresh_mapper()
        self.schedule()

    def generate_result(self):
        if self.source is None or self.reference is None:
            messagebox.showinfo("Result", "Choose a source image and a color reference first.", parent=self.win)
            return
        self.result = self.recolor()
        changed = ["#%d -> %s" % (i, to_hex(c)) for i, c in self.color_map.items()
                   if i < len(self.source_palette) and tuple(c) != tuple(self.source_palette[i])]
        self.log("--- FINAL RESULT --- %d source indexes changed: %s" % (len(changed), "; ".join(changed[:40])))
        self.draw_image(self.result, "Result")
        choice = ChoiceDialog(self.app, "Result", "What do you want to do with the result?",
                              [("Add as Layer", "layer"), ("Save Image...", "save"), ("Keep Editing", None)],
                              parent=self.win).show()
        if choice == "save":
            path = filedialog.asksaveasfilename(title="Save Result", defaultextension=".png",
                                                filetypes=IMAGE_SAVE_TYPES, initialdir=export_dir("images"),
                                                parent=self.win)
            if path:
                img = self.result if path.lower().endswith((".png", ".webp", ".tga", ".tif", ".tiff")) else \
                    convert_image(self.result, PALETTE_SIZE, self.app.key_color)[0]
                img.save(path)
                self.log("Result saved to %s" % path)
        elif choice == "layer":
            indexed, key = convert_image(self.result, PALETTE_SIZE, self.app.key_color)
            if key is not None and self.app.key_color is None:
                self.app.key_color = key
            layer = ImageLayer("Recolored", [Frame(indexed, "Recolored")])
            self.app.add_image_layer(layer)
            self.app.structure_changed()
            self.log("Result added to the project as a layer.")

    def close(self):
        self.win.destroy()
        self.app.adjuster = None
