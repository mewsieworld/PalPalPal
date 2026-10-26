"""PalPalPal main window: the timeline."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.colors import flat_palette
from ..core.images import Frame, frame_fits_palette, merge_frames_into_palette
from ..ui.dialogs import ChoiceDialog


class AppFramesMixin:
    """The timeline: playback, loop points and frame editing."""

    # ----- timeline -----
    def update_timeline(self):
        count = self.frame_count()
        self._scrub_lock = True
        self.scrub.configure(to=max(1, count))
        self.scrub_var.set(self.current_frame + 1 if count else 1)
        self._scrub_lock = False
        loop = ""
        if self.loop_range:
            loop = "  ⟲%d-%s" % (self.loop_range[0] + 1, "?" if self.loop_range[1] is None else self.loop_range[1] + 1)
        self.timeline_lbl.configure(text=("%d / %d" % (self.current_frame + 1, count) if count else "0 / 0") + loop)
        self.loop_btn.configure(relief="sunken" if self.loop_range else "raised")

    def on_scrub(self):
        if getattr(self, "_scrub_lock", False) or not self.frame_count():
            return
        t = int(self.scrub_var.get()) - 1  # whole numbers only, so the slider snaps frame to frame
        if t != self.current_frame:
            self.current_frame = self.custom_pos = t
            self.request_redraw()

    def jump_frame(self, where):
        frames = self.visible_frame_indices()
        if frames:
            self.current_frame = self.custom_pos = frames[where]
            self.request_redraw()

    def playback_frames(self):
        frames = self.visible_frame_indices()
        if self.loop_range and self.loop_range[1] is not None:
            a, b = self.loop_range
            looped = [t for t in frames if a <= t <= b]
            return looped or frames
        return frames

    def toggle_playback(self):
        if self.playing:
            self.stop_playback()
        elif self.frame_count() > 1:
            self.playing = True
            self.play_btn.configure(text="⏸ Pause")
            self._tick()

    def stop_playback(self):
        self.playing = False
        if self._play_job:
            self.master.after_cancel(self._play_job)
            self._play_job = None
        if hasattr(self, "play_btn"):
            self.play_btn.configure(text="⏵ Play")

    def _tick(self):
        if not self.playing:
            return
        frames = self.playback_frames()
        if not frames:
            self.stop_playback()
            return
        pos = frames.index(self.current_frame) if self.current_frame in frames else -1
        self.current_frame = self.custom_pos = frames[(pos + 1) % len(frames)]
        self.update_image_display()
        speed = float(self.speed_var.get().rstrip("x") or 1)
        self._play_job = self.master.after(max(15, int(1000 / (ANIMATION_FPS * speed))), self._tick)

    def set_loop_point(self):
        """First press marks where the loop starts, the second where it ends, the third clears it."""
        if self.loop_range is None:
            self.loop_range = (self.current_frame, None)
        elif self.loop_range[1] is None:
            a, b = sorted((self.loop_range[0], self.current_frame))
            self.loop_range = (a, b)
        else:
            self.loop_range = None
        self.mark_dirty()
        self.update_timeline()

    # ----- frame tools (work on the selected image layer) -----
    def target_image_layer(self):
        """The image layer frame tools work on: the selected one, or the image a selected palette colors."""
        palette = self.selected_palette()
        if palette is None:
            return None
        images = self.images_colored_by(palette)
        if images:
            return images[0]
        layers = self.image_layers()
        return layers[-1] if layers else None

    def frames_changed(self):
        self.hidden_frames = {t for t in self.hidden_frames if t < self.frame_count()}
        self.selected_frames = set()
        self.loop_range = None
        self.structure_changed()

    def _frame_index(self, il):
        return self.current_frame % len(il.frames)

    def clone_frame(self):
        il = self.target_image_layer()
        if il is None:
            return
        i = self._frame_index(il)
        src = il.frames[i]
        il.frames.insert(i + 1, Frame(src.image.copy(), src.name + " copy", src.source_path))
        self.current_frame = i + 1
        self.frames_changed()

    def blank_frame_for(self, il):
        w, h = il.size
        used = set()
        for f in il.frames:
            used.update(f.used_indices())
        clear = next((f.transparent_index for f in il.frames if f.transparent_index is not None), None)
        if clear is None and self.key_color is not None:
            clear = next((i for i, c in enumerate(il.palette.colors) if self.is_key(c)), None)
        if clear is None:
            clear = next((i for i in range(PALETTE_SIZE) if i not in used), 0)
        img = Image.new("P", (w, h), clear)
        img.putpalette(flat_palette(il.palette.colors))
        img.info["transparency"] = clear
        return Frame(img, "blank", "")

    def add_blank_frame(self):
        il = self.target_image_layer()
        if il is None:
            return
        i = self._frame_index(il)
        il.frames.insert(i + 1, self.blank_frame_for(il))
        self.current_frame = i + 1
        self.frames_changed()

    def delete_frame(self):
        il = self.target_image_layer()
        if il is None:
            return
        if len(il.frames) < 2:
            messagebox.showinfo("Delete", "A layer needs at least one frame. Remove the layer instead.")
            return
        del il.frames[self._frame_index(il)]
        self.current_frame = max(0, min(self.current_frame, self.frame_count() - 1))
        self.frames_changed()

    def add_frames(self):
        """+ Frames: several blank frames after the current one."""
        il = self.target_image_layer()
        if il is None:
            return
        n = simpledialog.askinteger("+ Frames", "How many blank frames to add after frame %d?"
                                    % (self._frame_index(il) + 1), initialvalue=1, minvalue=1, maxvalue=500,
                                    parent=self.master)
        if not n:
            return
        i = self._frame_index(il)
        for _ in range(n):
            il.frames.insert(i + 1, self.blank_frame_for(il))
        il.sync_palette_count()
        self.current_frame = i + 1
        self.frames_changed()

    def remove_frames(self):
        """- Frames: remove the frames selected in the All / Custom grid, or the ones typed in (e.g. 2-4, 7)."""
        il = self.target_image_layer()
        if il is None:
            return
        count = len(il.frames)
        if self.selected_frames:
            picked = {t % count for t in self.selected_frames}
        else:
            text = simpledialog.askstring("- Frames", "Remove which frames of %s? (1 to %d, e.g. 2-4, 7)"
                                          % (il.name, count), initialvalue=str(self._frame_index(il) + 1),
                                          parent=self.master)
            if not text:
                return
            picked = set()
            try:
                for part in text.replace(" ", "").split(","):
                    if not part:
                        continue
                    lo, _sep, hi = part.partition("-")
                    for n in range(int(lo), int(hi or lo) + 1):
                        if 1 <= n <= count:
                            picked.add(n - 1)
            except ValueError:
                messagebox.showinfo("- Frames", "Type frame numbers like 2-4, 7.")
                return
        if not picked:
            return
        if len(picked) >= count:
            messagebox.showinfo("- Frames", "A layer needs at least one frame. Remove the layer instead.")
            return
        if not messagebox.askyesno("- Frames", "Remove %d frame%s from %s?" % (len(picked), "s" if len(picked) > 1
                                                                               else "", il.name)):
            return
        il.frames = [f for k, f in enumerate(il.frames) if k not in picked]
        il.sync_palette_count()
        self.current_frame = max(0, min(self.current_frame, self.frame_count() - 1))
        self.frames_changed()

    def copy_frame(self):
        il = self.target_image_layer()
        if il is not None:
            src = il.frames[self._frame_index(il)]
            self.frame_clipboard = (src.image.copy(), src.name)

    def paste_frame(self):
        il = self.target_image_layer()
        if il is None or self.frame_clipboard is None:
            return
        img, name = self.frame_clipboard
        i = self._frame_index(il)
        il.frames[i] = Frame(img.copy(), name, il.frames[i].source_path)
        self.frames_changed()

    def import_frames(self):
        """Add whole images as new frames after the selected layer's frames (they share its palette indexes)."""
        target = self.target_image_layer()
        if target is None:
            self.open_images()
            return
        paths = filedialog.askopenfilenames(title="Import Image as Frames", filetypes=IMAGE_OPEN_TYPES)
        added = []
        for path in paths:
            il = self.import_image_file(path)
            if il is not None:
                added.extend(il.frames)
        if not added:
            return
        if any(not frame_fits_palette(f, target) for f in added):
            choice = ChoiceDialog(
                self, "New frames",
                "These frames use different colors from '%s'.\n\n"
                "Share indexes: the frames keep their pixel indexes and take the layer's palette "
                "(best for editing many frames at once).\nKeep their colors: their colors are added to "
                "the layer's palette so they look the same as the file." % target.name,
                [("Share indexes", "share"), ("Keep their colors", "keep"), ("Cancel", None)], wrap=420).show()
            if choice is None:
                return
            if choice == "keep":
                added = merge_frames_into_palette(target, added)
        first = len(target.frames)
        target.frames.extend(added)
        self.stats.add("images_opened", len(paths))
        self.current_frame = first
        self.frames_changed()
