"""PalPalPal main window: editor windows, exports, help and updates."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.storage import HOME_DIR, app_dir, cache_dir, export_dir
from ..core.colors import flat_palette, to_hex
from ..core.updates import download_file, fetch_latest_release, parse_version, update_token, write_swap_script
from ..core.palettes import palette_grid_image, read_palette, write_palette
from ..core.images import Frame, ImageLayer, convert_image, requantize_layer, unify_frame_palettes
from ..ui.theme import Theme, center_on
from ..ui.dialogs import BGOptionsDialog, SettingsDialog
from ..ui.document_settings import DocumentSettingsDialog
from ..switcher.window import SwatchSwitcher
from ..mass_editor.window import FrameMassEditor
from ..adjuster.window import ImageToImageAdjuster


class AppToolsMixin:
    """The editor windows, exports, Help menu items and updates."""

    # ----- colors -----
    def open_document_settings(self):
        if not self.image_layers() and not self.stack:
            messagebox.showinfo("Document Settings", "Start a project or add an image first.")
            return
        DocumentSettingsDialog(self).show()

    def set_palette_color_count(self, n):
        """Requantize every image that uses more than n colors, and size every palette to n."""
        changed = 0
        for il in self.image_layers():
            used = set()
            for f in il.frames:
                used.update(f.used_indices())
            if len(used) > n:
                requantize_layer(il, n, self.key_color)
                changed += 1
        for palette in self.all_palettes():
            palette.size = n
        self.compact.clear_state()
        self.structure_changed()
        self.request_redraw()
        return changed

    def all_palettes(self):
        out = []
        for e in self.stack:
            out.extend(e.palettes if isinstance(e, ImageLayer) else [e])
        return out

    def open_bg_options(self):
        BGOptionsDialog(self)

    def set_key_color(self, color):
        self.key_color = color
        self.structure_changed()

    # ----- editors -----
    def open_adjuster(self):
        if self.adjuster and self.adjuster.win.winfo_exists():
            self.adjuster.win.lift()
            return
        self.adjuster = ImageToImageAdjuster(self)

    def open_sprite_tool(self):
        """The Artwork Tool; Save and Return adds the drawing below the selected layer."""
        if self.sprite_tool and self.sprite_tool.win.winfo_exists():
            self.sprite_tool.win.lift()
            return
        from ..artwork import SpriteTool
        entry = self.entry_of(self.selected_palette())
        il = entry if isinstance(entry, ImageLayer) else self.target_image_layer()
        w, h = il.size if il is not None else (32, 32)
        self.sprite_tool = SpriteTool(self.master, w, h, on_return=self.add_drawn_layer,
                                      theme=lambda widget: Theme.apply(self, widget), colors=Theme.colors(self),
                                      store_dir=cache_dir(), read_palette=read_palette, palette_types=PALETTE_TYPES,
                                      dark_mode=(lambda: self.dark_mode, self._sprite_tool_dark))

    def _sprite_tool_dark(self):
        self.toggle_dark_mode()
        return Theme.colors(self)

    def add_drawn_layer(self, images):
        """Index the returned frames on one shared palette and put them in as a single layer."""
        w, h = images[0].size
        strip = Image.new("RGBA", (w * len(images), h), (0, 0, 0, 0))
        for n, img in enumerate(images):
            strip.paste(img, (n * w, 0))
        indexed, key = convert_image(strip, PALETTE_SIZE, self.key_color)
        if key is not None and self.key_color is None:
            self.key_color = key
        name = "Drawn sprite"
        frames = [Frame(indexed.crop((n * w, 0, (n + 1) * w, h)), name if len(images) == 1 else "%s #%d" % (name, n + 1))
                  for n in range(len(images))]
        il = ImageLayer(name, unify_frame_palettes(frames))
        entry = self.entry_of(self.selected_palette())
        pos = self.stack.index(entry) if entry in self.stack else 0
        self.stack.insert(pos, il)
        self.selected_layer = self.layers.index(il.palette)
        self.compact.clear_state()
        self.structure_changed()

    def open_mass_editor(self):
        if self.mass_editor and self.mass_editor.win.winfo_exists():
            self.mass_editor.win.lift()
            return
        if not self.images_colored_by(self.selected_palette()):
            messagebox.showinfo("Mass Frame Editor", "Select an image layer (or a palette over one) first.")
            return
        self.mass_editor = FrameMassEditor(self)

    def open_switcher(self, force=False):
        if not force and self.store.get("mass_editor_default") and self.images_colored_by(self.selected_palette()):
            self.open_mass_editor()
            return
        if self.switcher and self.switcher.win.winfo_exists():
            self.switcher.lift()
            return
        if not self.layers:
            messagebox.showinfo(SWITCHER_NAME, "There is no palette to edit yet. Start a project or import "
                                               "an image or a palette first.")
            return
        if self.selected_layer < 0:
            self.selected_layer = 0
        self.switcher = SwatchSwitcher(self)

    def save_layer_palette(self, layer, parent=None, colors=None):
        """Save a palette using the Palette Format setting: PAL, a PNG swatch grid, or both."""
        fmt = self.store.get("palette_format")
        colors = colors if colors is not None else layer.colors
        grid_type = [("PNG Grid", "*.png")]
        types = grid_type + PALETTE_TYPES[1:-1] if fmt == "png" else PALETTE_TYPES[1:-1] + grid_type
        ext = ".png" if fmt == "png" else ".pal"
        path = filedialog.asksaveasfilename(title="Save Palette", parent=parent or self.master,
                                            defaultextension=ext, initialdir=export_dir("palettes"),
                                            initialfile=layer.name + ext, filetypes=types)
        if not path:
            return False
        written = []
        try:
            if path.lower().endswith(".png"):
                palette_grid_image(colors).save(path)
            else:
                write_palette(path, colors, self.store.get("pal_style"))
                if fmt == "both":
                    grid_path = os.path.splitext(path)[0] + ".png"
                    palette_grid_image(colors).save(grid_path)
                    written.append(grid_path)
        except OSError as exc:
            messagebox.showerror("Save Palette", "Could not save:\n%s" % exc, parent=parent)
            return False
        written.insert(0, path)
        self.stats.add("palettes_saved")
        messagebox.showinfo("Saved", "Saved %s\n\n%s" % (layer.name, "\n".join(written)), parent=parent or self.master)
        return True

    # ----- export -----
    def project_name(self):
        if self.project_path:
            return os.path.splitext(os.path.basename(self.project_path))[0]
        layers = self.image_layers()
        return layers[-1].name if layers else "frame"

    def _ask_image_path(self, title, initial):
        last = self.store.get("last_frame_ext") or ".png"
        types = sorted(IMAGE_SAVE_TYPES, key=lambda t: t[1] != "*" + last)
        return filedialog.asksaveasfilename(title=title, defaultextension=last, filetypes=types,
                                            initialdir=export_dir("images"), initialfile=initial)

    def save_frame_image(self, t, path, background=False):
        ext = os.path.splitext(path)[1].lower()
        if ext in (".png", ".webp", ".tga", ".tif", ".tiff") and not background:
            self.render(t, 1.0, background=False).save(path)
            return
        if ext in (".bmp", ".gif", ".pcx") and not background:
            layers = self.visible_image_layers()
            if len(layers) == 1:
                # One layer: keep it truly indexed with its own palette
                il = layers[0]
                frame = il.frame_at(t)
                palette = self.palette_coloring(il).colors
                img = frame.image.copy()
                img.putpalette(flat_palette(palette))
                img = self.transform(img)
                keys = self.key_indices(frame, palette)
                if ext == ".gif" and keys:
                    img.save(path, transparency=min(keys))
                else:
                    img.save(path)
                return
            img = self.render(t, 1.0, background=True).convert("RGB").quantize(PALETTE_SIZE)
            img.save(path)
            return
        self.render(t, 1.0, background=True).convert("RGB").save(path)

    def export_frame(self):
        if not self.frame_count():
            messagebox.showinfo("Export Frame", "No image loaded.")
            return
        path = self._ask_image_path("Export Frame", "%s_%03d" % (self.project_name(), self.current_frame + 1))
        if not path:
            return
        try:
            self.save_frame_image(self.current_frame, path)
            self.stats.add("frames_exported")
            self.store.set("last_frame_ext", os.path.splitext(path)[1].lower() or ".png")
        except Exception as exc:
            messagebox.showerror("Export Frame", "Could not export:\n%s" % exc)

    def export_background(self):
        if not self.frame_count():
            messagebox.showinfo("Export Background", "No image loaded.")
            return
        path = self._ask_image_path("Export Background", "%s_bg" % self.project_name())
        if not path:
            return
        try:
            self.save_frame_image(self.current_frame, path, background=True)
        except Exception as exc:
            messagebox.showerror("Export Background", "Could not export:\n%s" % exc)

    def export_all_frames(self):
        frames = self.visible_frame_indices()
        if not frames:
            messagebox.showinfo("Export All Frames", "No image loaded.")
            return
        folder = filedialog.askdirectory(title="Export All Frames to...", initialdir=export_dir("images"))
        if not folder:
            return
        ext = self.store.get("last_frame_ext") or ".png"
        name = "".join(ch if ch.isalnum() or ch in "-_ " else "_" for ch in self.project_name())
        done = 0
        for n, t in enumerate(frames):
            try:
                self.save_frame_image(t, os.path.join(folder, "%s_%03d%s" % (name, n + 1, ext)))
                done += 1
                self.stats.add("frames_exported")
            except Exception as exc:
                messagebox.showerror("Export All Frames", "Stopped at frame %d:\n%s" % (t + 1, exc))
                break
        messagebox.showinfo("Export All Frames", "Exported %d frame(s) as %s to\n%s" % (done, ext, folder))

    def export_palette(self):
        ly = self.selected_palette()
        if ly is None:
            messagebox.showinfo("Export Palette", "There is no palette to export yet.")
            return
        self.save_layer_palette(ly)

    # ----- reset / info -----
    def reset_frames(self):
        if not self.frame_count():
            messagebox.showinfo("Reset Frames", "No image loaded.")
            return
        self.save_visibility_state()
        self.hidden_frames = set()
        self.flip, self.rotation = False, 0
        self.selected_frames = set()
        self.current_frame = self.custom_pos = 0
        self.visibility_changed()
        messagebox.showinfo("Reset Frames", "All frame visibility settings and preview position have been reset.")

    def open_settings(self):
        SettingsDialog(self)

    def show_statistics(self):
        messagebox.showinfo("Statistics", "Your local statistics (kept only on this PC):\n\n"
                            + "\n".join(self.stats.lines()))

    def reset_pals(self):
        if not self.layers:
            messagebox.showinfo("Reset Pals", "There are no palettes to reset.")
            return
        if not messagebox.askyesno("Reset Pals", "Put every palette back to the colors it had when it was loaded?"):
            return
        for ly in self.layers:
            ly.colors[:] = ly.loaded_colors
        self.compact.snapshot()
        self.mark_dirty()
        self.update_compact_palette_editor()
        if self.switcher and self.switcher.win.winfo_exists():
            self.switcher.dirty.clear()
            self.switcher.build()
        self.refresh_layers_box()
        self.request_redraw()

    def show_current_display_info(self):
        lines = ["View: %s, preview: %s, zoom: %s%s" % (self.view_var.get(), self.preview_var.get(),
                                                       self.zoom_var.get(), ", 3D" if self.view_3d else ""),
                 "Flip: %s, rotation: %d°" % (self.flip, self.rotation * 90),
                 "Palette BG (key) color: %s" % (to_hex(self.key_color) if self.key_color else "none"),
                 "BG color: %s" % (to_hex(self.bg_color) if self.bg_color is not None else "none (transparent)"), ""]
        if self.frame_count():
            w, h = self.canvas_size()
            lines.append("Frame %d of %d, canvas %d x %d" % (self.current_frame + 1, self.frame_count(), w, h))
        else:
            lines.append("No image loaded")
        lines.append("")
        lines.append("Layers, top first:")
        selected = self.entry_of(self.selected_palette())
        for entry in reversed(self.stack):
            if isinstance(entry, ImageLayer):
                f = entry.frame_at(self.current_frame)
                lines.append("%s %s  [image, %d frame(s), %d indexes used]%s" % (
                    "[x]" if entry.visible else "[ ]", entry.name, len(entry.frames), len(f.used_indices()),
                    "  (editing)" if entry is selected else ""))
            else:
                lines.append("%s %s  [palette]%s" % ("[x]" if entry.active else "[ ]", entry.name,
                                                    "  (editing)" if entry is selected else ""))
        messagebox.showinfo("Current Display Info", "\n".join(lines))

    def debug_info(self):
        lines = [APP_NAME, "Python %s" % sys.version.split()[0],
                 "Program folder: %s" % app_dir(), "User file: %s" % self.store.path,
                 "Home folder: %s" % HOME_DIR,
                 "Project: %s" % (self.project_path or "not saved yet"),
                 "Images: %d, palettes: %d, frames: %d" % (len(self.image_layers()), len(self.layers),
                                                          self.frame_count()),
                 "%s open: %s" % (SWITCHER_NAME, bool(self.switcher and self.switcher.win.winfo_exists()))]
        messagebox.showinfo("Debug Info", "\n".join(lines))

    def run_in_background(self, work, done, tick=None):
        """work() runs on a thread; done(result, error) and the optional tick() run on the Tk loop."""
        import threading
        state = {}

        def run():
            try:
                state["result"] = work()
            except Exception as exc:
                state["error"] = exc

        def wait():
            if thread.is_alive():
                if tick:
                    tick()
                self.master.after(150, wait)
            else:
                done(state.get("result"), state.get("error"))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        self.master.after(150, wait)

    # ----- updates -----
    def show_about(self):
        messagebox.showinfo("About %s" % APP_NAME, "%s %s (%s%s)\n\nUpdates come from github.com/%s (%s branch), "
                            "file %s." % (APP_NAME, APP_VERSION, BUILD_ARCH, ", " + BUILD_LABEL if BUILD_LABEL else "",
                                          UPDATE_REPO, UPDATE_BRANCH, UPDATE_ASSET))

    def check_for_updates(self, quiet=False):
        """Ask GitHub for the newest release in the background so the window never freezes."""
        self.run_in_background(fetch_latest_release, lambda rel, error: self._update_checked(rel, error, quiet))

    def _update_checked(self, rel, error, quiet):
        if error is not None:
            if not quiet:
                messagebox.showerror("Check for Updates", "Couldn't check for updates:\n%s" % error)
            return
        if rel is None or parse_version(rel.get("tag_name", "0")) <= parse_version(APP_VERSION):
            if not quiet:
                messagebox.showinfo("Check for Updates", "You're up to date (%s %s)." % (APP_NAME, APP_VERSION))
            return
        notes = (rel.get("body") or "").strip()
        if len(notes) > 600:
            notes = notes[:600] + "..."
        version = rel.get("tag_name", "").lstrip("vV")
        asset = next((a for a in rel.get("assets", []) if a.get("name") == UPDATE_ASSET), None)
        if not getattr(sys, "frozen", False) or asset is None:
            # Running from the .py source (or no exe attached): send them to the release page instead
            if messagebox.askyesno("Update available", "%s %s is out (you have %s).\n\n%s\n\nOpen the download page?"
                                   % (APP_NAME, version, APP_VERSION, notes)):
                import webbrowser
                webbrowser.open(rel.get("html_url", "https://github.com/%s/releases" % UPDATE_REPO))
            return
        if not messagebox.askyesno("Update available", "%s %s is out (you have %s).\n\n%s\n\nDownload and install it "
                                   "now? %s will restart." % (APP_NAME, version, APP_VERSION, notes, APP_NAME)):
            return
        self.install_update(asset["url"] if update_token() else asset["browser_download_url"], version)

    def install_update(self, url, version):
        if not self.confirm_discard():
            return
        old_exe = os.path.abspath(sys.executable)
        new_exe = old_exe + ".new"
        dlg = tk.Toplevel(self.master)
        dlg.title("Updating")
        dlg.transient(self.master)
        lbl = tk.Label(dlg, text="Downloading %s %s..." % (APP_NAME, version), padx=20, pady=15)
        lbl.pack()
        Theme.apply(self, dlg)
        center_on(dlg, self.master)
        state = {}

        def progress(done, total):
            state["pct"] = int(done * 100 / total) if total else None

        def tick():
            if state.get("pct") is not None:
                lbl.configure(text="Downloading %s %s... %d%%" % (APP_NAME, version, state["pct"]))

        def finished(_result, error):
            dlg.destroy()
            if error is not None:
                messagebox.showerror("Update", "The download failed, nothing was changed:\n%s" % error)
                return
            import subprocess
            script = write_swap_script(old_exe, new_exe, os.getpid())
            subprocess.Popen(["cmd", "/c", script], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                             close_fds=True)
            self.stats.save()
            self.master.destroy()

        self.run_in_background(lambda: download_file(url, new_exe, progress), finished, tick)

    def on_quit(self):
        if not self.confirm_discard():
            return
        self.stats.save()
        self.master.destroy()
