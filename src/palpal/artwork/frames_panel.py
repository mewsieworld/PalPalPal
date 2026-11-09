"""Artwork Tool: animation frames, the timeline and the animation preview."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .look import round_button
from .model import Layer


class FramesMixin:
    """Animation frames, timeline thumbnails and the animation preview."""

    # ----- frames -----
    def load_frame(self, index):
        index = max(0, min(len(self.frames) - 1, index))
        self.cur_frame = index
        self.cur_layer = 0
        self.refresh_all()

    def add_frame(self, kind="clone"):
        self.save_state()
        new = [l.clone() for l in self.layers()] if kind == "clone" else [Layer("Layer 1", self.W, self.H)]
        pos = self.cur_frame + 1
        self.frames.insert(pos, new)
        self.tags.insert(pos, "")
        self.durations.insert(pos, None)
        self.load_frame(pos)

    def delete_frame(self):
        if len(self.frames) <= 1:
            messagebox.showinfo("Delete", "Cannot delete the only frame.", parent=self.win)
            return
        self.save_state()
        del self.frames[self.cur_frame]
        del self.tags[self.cur_frame]
        del self.durations[self.cur_frame]
        self.load_frame(min(self.cur_frame, len(self.frames) - 1))

    def copy_frame(self):
        self.frame_clip = [l.clone() for l in self.layers()]
        messagebox.showinfo("Copy", "Frame %d copied to clipboard!\n(%d layers)" % (self.cur_frame + 1, len(self.frame_clip)),
                            parent=self.win)

    def paste_frame(self):
        if not self.frame_clip:
            messagebox.showinfo("Paste", "No frame in clipboard!\nUse 'Copy' first.", parent=self.win)
            return
        self.save_state()
        self.frames[self.cur_frame] = [l.clone() for l in self.frame_clip]
        self.cur_layer = 0
        self.changed()

    def move_frame(self, a, b):
        if a == b or not (0 <= a < len(self.frames)) or not (0 <= b < len(self.frames)):
            return
        self.save_state()
        for seq in (self.frames, self.tags, self.durations):
            seq.insert(b, seq.pop(a))
        if a == self.cur_frame:
            self.cur_frame = b
        self.load_frame(self.cur_frame)

    def move_frame_left(self):
        self.move_frame(self.cur_frame, self.cur_frame - 1 if self.cur_frame > 0 else len(self.frames) - 1)

    def move_frame_right(self):
        self.move_frame(self.cur_frame, self.cur_frame + 1 if self.cur_frame < len(self.frames) - 1 else 0)

    def set_loop(self):
        choice = simpledialog.askstring("🔄 Loop Settings", "Current: Start=%d, End=%s\n\n1 = Set CURRENT frame as loop START (%d)\n"
                                                         "2 = Set CURRENT frame as loop END (%d)\n3 = Reset to full animation"
                                        % (self.loop_start, "Last Frame" if self.loop_end == -1 else self.loop_end,
                                           self.cur_frame, self.cur_frame), parent=self.win)
        if choice == "1":
            self.loop_start = self.cur_frame
        elif choice == "2":
            self.loop_end = self.cur_frame
        elif choice == "3":
            self.loop_start, self.loop_end = 0, -1
        self.loop_lbl.configure(text="Loop: %d-%s" % (self.loop_start + 1, "end" if self.loop_end == -1 else self.loop_end + 1))

    def clear_frame(self):
        self.save_state()
        for layer in self.layers():
            layer.img = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        self.changed()

    def render_thumbs(self):
        c = self.thumb_canvas
        c.delete("all")
        x = 4
        default = self.speed_var.get()
        for i in range(len(self.frames)):
            img = self.composite_frame(i)
            img.thumbnail((THUMB, THUMB), Image.Resampling.NEAREST)
            photo = ImageTk.PhotoImage(img)
            self.photos["thumb%d" % i] = photo
            c.create_rectangle(x - 2, 2, x + THUMB + 2, THUMB + 6, outline="#2196f3" if i == self.cur_frame else "#888",
                               width=2 if i == self.cur_frame else 1)
            c.create_image(x + THUMB // 2, THUMB // 2 + 4, image=photo)
            c.create_text(x + THUMB, THUMB + 4, text=str(i + 1), anchor="se", fill="#888", font=("Arial", 7))
            if self.tags[i]:
                c.create_text(x, 4, text=self.tags[i], anchor="nw", fill="#ff9800", font=("Arial", 7, "bold"))
            if self.durations[i] and self.durations[i] != default:
                c.create_text(x + THUMB, 4, text="%dms" % self.durations[i], anchor="ne", fill="#2196f3", font=("Arial", 7))
            x += THUMB + 8
        c.configure(scrollregion=(0, 0, x, THUMB + 16))
        self.update_timeline()

    def thumb_at(self, event):
        i = int((self.thumb_canvas.canvasx(event.x) - 2) // (THUMB + 8))
        return i if 0 <= i < len(self.frames) else None

    def on_thumb_click(self, event):
        i = self.thumb_at(event)
        if i is not None:
            self._thumb_drag = i
            self.load_frame(i)

    def on_thumb_release(self, event):
        """Dropping a dragged thumbnail on another one moves the frame there."""
        src = getattr(self, "_thumb_drag", None)
        self._thumb_drag = None
        dst = self.thumb_at(event)
        if src is not None and dst is not None and src != dst:
            self.move_frame(src, dst)

    def on_thumb_right(self, event):
        i = self.thumb_at(event)
        if i is None:
            return
        tag = simpledialog.askstring("🏷️ Tag Frame", 'Tag frame %d:\n\nExamples: "idle", "walk-1", "attack"\n\n'
                                                   "Leave empty to remove tag." % (i + 1), initialvalue=self.tags[i],
                                     parent=self.win)
        if tag is not None:
            self.tags[i] = tag.strip()
            self.render_thumbs()

    def on_thumb_double(self, event):
        i = self.thumb_at(event)
        if i is None:
            return
        default = self.speed_var.get()
        v = simpledialog.askinteger("⏱️ Frame Duration", "Frame %d duration (milliseconds):\n\nDefault: %dms\n"
                                                       "0 = use default" % (i + 1, default),
                                    initialvalue=self.durations[i] or default, minvalue=0, parent=self.win)
        if v is not None:
            self.durations[i] = v or None
            self.render_thumbs()

    def toggle_timeline(self):
        if self.timeline_var.get():
            self.timeline_row.pack(fill="x", before=self.thumb_canvas.master)
        else:
            self.timeline_row.pack_forget()
        self.update_timeline()

    def update_timeline(self):
        self.scrub.configure(to=max(0, len(self.frames) - 1))
        self.scrub_var.set(self.cur_frame)
        self.timeline_lbl.configure(text="%d/%d" % (self.cur_frame + 1, len(self.frames)))

    # ----- animation preview -----
    def toggle_preview(self):
        self.playing = not self.playing
        self.play_btn.configure(text="Pause Preview" if self.playing else "Play Preview")
        self.play_btn._paint = "#dc3545" if self.playing else "#28a745"
        round_button(self.play_btn, self.play_btn._paint)
        if self.playing:
            self.preview_tick()

    def preview_tick(self):
        if not self.win.winfo_exists():
            return
        if not self.frames:
            return
        self.anim_frame = min(self.anim_frame, len(self.frames) - 1)
        img = self.composite_frame(self.anim_frame).resize((PREVIEW, PREVIEW), Image.Resampling.NEAREST)
        self.photos["preview"] = ImageTk.PhotoImage(img)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(0, 0, image=self.photos["preview"], anchor="nw")
        self.preview_lbl.configure(text="Frame %d / %d" % (self.anim_frame + 1, len(self.frames)))
        mult = float(self.mult_var.get().rstrip("x"))
        duration = (self.durations[self.anim_frame] or self.speed_var.get()) / mult
        self.fps_lbl.configure(text="FPS ~%.1f" % (1000 / duration))
        end = len(self.frames) - 1 if self.loop_end == -1 else min(self.loop_end, len(self.frames) - 1)
        self.anim_frame += 1
        if self.anim_frame > end:
            self.anim_frame = self.loop_start
        if self.playing:
            self.win.after(max(16, int(duration)), self.preview_tick)
