"""PalPalPal main window: Export > 3D Model and Export > Heightmap."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.storage import export_dir
from ..preview.beads import build_cells
from ..preview.export3d import MODEL_TYPES, WRITERS
from ..preview.heights import HeightSettings, height_image


class AppExport3DMixin:
    def export_3d_model(self):
        """The bead model as you see it in the 3D view (heights and 3D moves included), current frame."""
        layers = self.visible_image_layers()
        if not layers:
            messagebox.showinfo("Export 3D Model", "There's no image to build a model from yet.")
            return
        last = self.store.get("last_model_ext") or ".obj"
        types = sorted(MODEL_TYPES, key=lambda t: t[1] != "*" + last)
        path = filedialog.asksaveasfilename(title="Export 3D Model", defaultextension=last, filetypes=types,
                                            initialdir=export_dir("images"),
                                            initialfile="%s_3d" % self.project_name())
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        if ext not in WRITERS:
            path, ext = path + ".obj", ".obj"
        self.store.set("last_model_ext", ext)
        cells = build_cells(self, self.current_frame, layers)
        try:
            a, b = WRITERS[ext](path, cells)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Export 3D Model", str(exc))
            return
        what = {".obj": "%d vertices, %d faces (colors in the .mtl next to it)", ".ply": "%d vertices, %d faces",
                ".vox": "%d voxels, %d colors",
                ".schematic": "%d blocks, %d kinds of wool / concrete / terracotta"}[ext] % (a, b)
        messagebox.showinfo("Export 3D Model", "Saved %s\n\n%s" % (path, what))

    def export_heightmap(self):
        """The selected image layer's heights as a greyscale PNG: black = 1 bead, white = the tallest.
        The same file can be drawn on and used again (Document & 3D Settings > 3D heights > Manually drawn)."""
        il = self.target_image_layer()
        if il is None:
            messagebox.showinfo("Export Heightmap", "Select an image layer first.")
            return
        settings = self.heights
        if settings.mode == "flat":
            # No heights set up yet: use the picture's brightness (the "heightmap" mode)
            settings = HeightSettings.from_dict(dict(self.heights.to_dict(), mode="luma"))
            settings.max = max(2, settings.max)
        path = filedialog.asksaveasfilename(title="Export Heightmap", defaultextension=".png",
                                            filetypes=[("PNG (greyscale)", "*.png"), ("BMP", "*.bmp")],
                                            initialdir=export_dir("images"), initialfile="%s_heightmap" % il.name)
        if not path:
            return
        size = il.frame_at(self.current_frame).image.size
        heights = height_image(self, il, self.current_frame, size, transform=False, settings=settings)
        top = max(1, settings.max - 1)
        grey = heights.point([int(round((max(1, v) - 1) * 255.0 / top)) if v else 0 for v in range(256)])
        # see-through pixels come out black (no beads there)
        alpha = self.render_layer(il, self.current_frame).getchannel("A").point(lambda a: 255 if a >= 128 else 0)
        grey = Image.composite(grey, Image.new("L", size, 0), alpha)
        try:
            grey.save(path)
        except OSError as exc:
            messagebox.showerror("Export Heightmap", str(exc))
            return
        messagebox.showinfo("Export Heightmap", "Saved %s\n\nBlack = 1 bead, white = %d beads%s." % (
            path, settings.max, "" if self.heights.mode != "flat" else " (from brightness, since 3D heights are off)"))
