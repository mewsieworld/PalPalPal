"""PalPalPal main window: imports and projects."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..preview.heights import HeightSettings
from ..core.storage import export_dir
from ..core.palettes import read_palette
from ..core.images import (Frame, ImageLayer, PaletteLayer, convert_image, dropped_colors, exact_indexed, is_indexed,
    read_image_frames, to_indexed, unify_frame_palettes)
from ..core.project import load_project_file, save_project_file
from ..ui.dialogs import ChoiceDialog, NewProjectDialog, ask_excess_colors


class AppFilesMixin:
    """Importing images and palettes, and new / open / save project."""

    # ----- importing -----
    def import_image_file(self, path, colors=None):
        """Read an image, offer conversion when it isn't indexed, and return a ready ImageLayer (or None).

        This runs right after the file picker closes, before anything reaches the main view.
        """
        try:
            raw = read_image_frames(path)
        except Exception as exc:
            messagebox.showerror("Open Image", "Could not read %s:\n%s" % (os.path.basename(path), exc))
            return None
        name = os.path.splitext(os.path.basename(path))[0]
        if path.lower().endswith(".gif"):
            # GIF is indexed by nature; Pillow hands later frames over as RGB when their palette changes
            raw = [img if is_indexed(img) else (exact_indexed(img) or img) for img in raw]
        if not all(is_indexed(img) for img in raw):
            choice = ChoiceDialog(self, "Convert image?",
                                  "Warning, this image is not in a readable format! It will not work with "
                                  "this program without conversion. Convert?",
                                  [("Yes", "yes"), ("Yes and Save Copy", "copy"), ("No", "no")]).show()
            if choice not in ("yes", "copy"):
                return None
            copy_path = self.ask_converted_copy_path(name) if choice == "copy" else None
            if colors is None:
                answer = NewProjectDialog(self, ask_key=False).show()
                if answer is None:
                    return None
                colors = answer["colors"]
            originals = raw
            converted, key = [], None
            for img in raw:
                indexed, key = convert_image(img, colors, self.key_color)
                converted.append(indexed)
            raw = converted
            if key is not None and self.key_color is None:
                self.key_color = key  # transparent areas became this color, so it is the key
            if copy_path:
                self.save_converted_copy(raw, copy_path)
            ask_excess_colors(self, dropped_colors(originals, raw), name)
        frames = unify_frame_palettes([Frame(to_indexed(img), name if len(raw) == 1 else "%s #%d" % (name, n + 1),
                                             path) for n, img in enumerate(raw)])
        layer = ImageLayer(name, frames, path)
        self.apply_local_name(layer)
        return layer

    def ask_converted_copy_path(self, name):
        return filedialog.asksaveasfilename(title="Save Converted Copy", defaultextension=".bmp",
                                            filetypes=[("BMP (256 color)", "*.bmp"), ("PNG", "*.png"),
                                                       ("GIF", "*.gif"), ("PCX", "*.pcx"), ("TGA", "*.tga"),
                                                       ("TIFF", "*.tiff")],
                                            initialdir=export_dir("images"), initialfile=name + "_indexed")

    def save_converted_copy(self, images, path):
        if not path:
            return
        try:
            if len(images) > 1 and path.lower().endswith(".gif"):
                images[0].save(path, save_all=True, append_images=images[1:], loop=0)
            elif len(images) > 1:
                base, ext = os.path.splitext(path)
                for n, img in enumerate(images):
                    img.save("%s_%03d%s" % (base, n + 1, ext))
            else:
                images[0].save(path)
        except Exception as exc:
            messagebox.showerror("Save Converted Copy", "Could not save:\n%s" % exc)

    def add_image_layer(self, il):
        """New images go on top of the selected row (or the top of the stack) and get selected."""
        entry = self.entry_of(self.selected_palette())
        pos = self.stack.index(entry) + 1 if entry in self.stack else len(self.stack)
        self.stack.insert(pos, il)
        self.selected_layer = self.layers.index(il.palette)
        self.compact.clear_state()

    def open_images(self):
        paths = filedialog.askopenfilenames(title="Import Image", filetypes=IMAGE_OPEN_TYPES)
        added = 0
        for path in paths:
            il = self.import_image_file(path)
            if il is not None:
                self.add_image_layer(il)
                added += 1
        if added:
            self.stats.add("images_opened", added)
            self.current_frame = 0
            self.structure_changed()

    def open_palette(self):
        path = filedialog.askopenfilename(title="Import Palette", filetypes=PALETTE_TYPES)
        if not path:
            return
        try:
            colors = read_palette(path)
        except Exception as exc:
            messagebox.showerror("Import Palette", "Could not read that palette:\n%s" % exc)
            return
        if len(colors) > PALETTE_SIZE:
            messagebox.showwarning("Import Palette", "That palette has %d colors; only the first 256 are used."
                                   % len(colors))
        layer = PaletteLayer(os.path.splitext(os.path.basename(path))[0], colors, path)
        layer.size = max(1, min(PALETTE_SIZE, len(colors)))
        self.apply_local_name(layer)
        # A stand-alone palette sits right above the selected row and recolors the image below it
        entry = self.entry_of(self.selected_palette())
        pos = self.stack.index(entry) + 1 if entry in self.stack else len(self.stack)
        # Ask about excess colors before the palette goes in, so the picture doesn't change behind the prompt
        self.stack.insert(pos, layer)
        excess = self.excess_colors(layer)
        self.stack.remove(layer)
        ask_excess_colors(self, excess, layer.name)
        self.stack.insert(pos, layer)
        self.selected_layer = self.layers.index(layer)
        self.compact.clear_state()
        self.stats.add("palettes_opened")
        self.structure_changed()

    def excess_colors(self, layer):
        """Distinct colors in a palette that sit on indexes its image never uses."""
        images = self.images_colored_by(layer)
        if not images:
            return []
        used = set()
        for il in images:
            for f in il.frames:
                used.update(f.used_indices())
        in_use = {layer.colors[i] for i in used}
        out = []
        for i, color in enumerate(layer.colors):
            if i in used or color in in_use or color in out or color == (0, 0, 0) or self.is_key(color):
                continue
            out.append(color)
        return out

    # ----- projects -----
    def confirm_discard(self):
        """Before New / Open / Quit: offer to save a project with unsaved changes. False means stop."""
        if self.switcher and self.switcher.win.winfo_exists():
            self.switcher.close()
            if self.switcher:
                return False
        if not self.stack or not self.dirty:
            return True
        answer = messagebox.askyesnocancel(APP_NAME, "Save your current project first?")
        if answer is None:
            return False
        if answer:
            return self.save_project()
        return True

    def clear_project(self):
        self.stack = []
        self.hidden_frames = set()
        self.selected_frames = set()
        self.visibility_history = []
        self.selected_layer = -1
        self.current_frame = self.custom_pos = 0
        self.key_color = None
        self.flip, self.rotation = False, 0
        self.project_path = None
        self.loop_range = None
        self.heights = HeightSettings()
        self.stop_playback()
        self.compact.clear_state()

    def new_project(self):
        if not self.confirm_discard():
            return
        answers = self.store.get("new_project_remember") or NewProjectDialog(self).show()
        if answers is None:
            return
        self.clear_project()
        colors = int(answers.get("colors", PALETTE_SIZE))
        if answers.get("key") == "now":
            result = colorchooser.askcolor(title="Your palette's background color")
            if result and result[0]:
                self.key_color = tuple(int(v) for v in result[0])
        choice = ChoiceDialog(self, "Texture", "Do you have a texture you want to import?",
                              [("Upload", "upload"), ("No", "no")]).show()
        layer = None
        if choice == "upload":
            path = filedialog.askopenfilename(title="Upload Texture", filetypes=IMAGE_OPEN_TYPES)
            # Checked the moment the file manager closes, before the main view shows anything
            if path:
                layer = self.import_image_file(path, colors)
        if layer is not None:
            self.add_image_layer(layer)
            self.stats.add("images_opened")
        else:
            ramp = [(round(255 * i / max(1, colors - 1)),) * 3 for i in range(colors)]
            palette = PaletteLayer("Palette", ramp)
            palette.size = colors
            self.stack.append(palette)
            self.selected_layer = 0
        self.structure_changed()
        self.dirty = False
        self.update_title()

    def open_project(self):
        if not self.confirm_discard():
            return
        path = filedialog.askopenfilename(title="Open Project", filetypes=PROJECT_TYPES,
                                          initialdir=export_dir("projects"))
        if not path:
            return
        try:
            state = load_project_file(path)
        except Exception as exc:
            messagebox.showerror("Open Project", "Could not open that project:\n%s" % exc)
            return
        self.clear_project()
        self.stack = state["stack"]
        self.key_color = state["key_color"]
        self.bg_color = None if state.get("bg_transparent") else (state["bg_color"] or self.bg_color)
        self.split_palettes = state.get("split_palettes", False)
        self.heights = HeightSettings.from_dict(state.get("heights"))
        self.palette_tab = 0
        self.hidden_frames = state["hidden_frames"]
        self.flip, self.rotation = state["flip"], state["rotation"]
        self.loop_range = state.get("loop_range")
        self.selected_layer = min(state["selected_layer"], len(self.layers) - 1)
        self.project_path = path
        self.structure_changed()
        self.dirty = False
        self.update_title()
        self.update_bottom_bar()

    def save_project(self):
        if not self.project_path:
            return self.save_project_as()
        return self._write_project(self.project_path)

    def save_project_as(self):
        if not self.stack:
            messagebox.showinfo("Save As", "There is nothing in this project to save yet.")
            return False
        name = os.path.splitext(os.path.basename(self.project_path))[0] if self.project_path else "Untitled"
        path = filedialog.asksaveasfilename(title="Save Project As", defaultextension=PROJECT_EXT,
                                            filetypes=PROJECT_TYPES, initialdir=export_dir("projects"),
                                            initialfile=name)
        if not path:
            return False
        return self._write_project(path)

    def _write_project(self, path):
        try:
            save_project_file(path, self)
        except Exception as exc:
            messagebox.showerror("Save Project", "Could not save the project:\n%s" % exc)
            return False
        self.project_path = path
        self.dirty = False
        self.stats.add("projects_saved")
        self.update_title()
        return True
