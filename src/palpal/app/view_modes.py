"""PalPalPal main window: preview modes, dark mode, 3D and Saved Colors."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..ui.theme import Theme


class AppViewModesMixin:
    """PalPalPal main window: preview modes, dark mode, 3D and Saved Colors."""

    def update_compact_palette_editor(self):
        self.compact.build(self.active_colors_frame, big=self.view_var.get() == "No Preview")
        self.master.after_idle(self.align_saved_colors_sash)

    # ----- view modes -----
    def toggle_view_mode(self):
        order = PREVIEW_MODES
        self.view_var.set(order[(order.index(self.view_var.get()) + 1) % len(order)])
        self.choose_view_mode()

    def choose_view_mode(self):
        """A mode the user picked themselves always wins over the automatic No Preview."""
        self._auto_no_preview = None
        self.apply_view_mode()

    def apply_view_mode(self):
        # With palettes but no image there is nothing to preview, so the image-less layout takes over
        if self.stack and not self.image_layers() and self.view_var.get() != "No Preview":
            self._auto_no_preview = self.view_var.get()
            self.view_var.set("No Preview")
        elif self.image_layers() and self._auto_no_preview:
            self.view_var.set(self._auto_no_preview)
            self._auto_no_preview = None
        mode = self.view_var.get()
        if self._auto_no_preview is None:
            self.store.set("preview_mode", mode)
        # Nothing to zoom without a preview
        if mode == "No Preview":
            self.zoom_group.pack_forget()
        elif not self.zoom_group.winfo_ismapped():
            self.zoom_group.pack(side="left", before=self.zoom_group.master.winfo_children()[1])
        panes = [str(p) for p in self.paned.panes()]
        if mode == "Big Preview":
            self.compact_bar.pack_forget()
            self.scroll_frame.pack(fill="both", expand=True)
            if str(self.saved_box) in panes:
                self.paned.forget(self.saved_box)
            if self.compact.picking:
                self.compact.toggle_pick()
        else:
            self.compact_bar.pack_forget()
            if mode == "No Preview":
                self.scroll_frame.pack_forget()
                self.compact_bar.pack(side="top", fill="both", expand=True)
                self.compact_row.pack_forget()
                self.resize_handle.pack_forget()
                self.active_colors_frame.pack_propagate(True)
            else:
                self.scroll_frame.pack(fill="both", expand=True)
                self.compact_bar.pack(side="bottom", fill="x", pady=(5, 0))
                self.compact_row.pack(side="top", fill="x", padx=5, pady=(5, 2), before=self.compact_holder)
                self.resize_handle.pack(side="top", fill="x", before=self.active_colors_frame)
                self.active_colors_frame.configure(height=self.active_colors_height)
                self.active_colors_frame.pack_propagate(False)
            if str(self.saved_box) not in panes:
                self.paned.add(self.saved_box, minsize=120, stretch="never")
        self.update_compact_palette_editor()
        self.update_bottom_bar()
        if self.switcher and self.switcher.win.winfo_exists():
            self.switcher.build()
        self.request_redraw()

    def toggle_saved_colors(self):
        if str(self.saved_box) in [str(p) for p in self.paned.panes()]:
            self.paned.forget(self.saved_box)
        else:
            self.paned.add(self.saved_box, minsize=120, stretch="never")
            self.master.after_idle(self.align_saved_colors_sash)

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.store.set("dark_mode", self.dark_mode)
        Theme.apply(self)
        if self.switcher and self.switcher.win.winfo_exists():
            Theme.apply(self, self.switcher.win)
            self.switcher.refresh_swatches()
        self.saved_colors_changed()
        self.update_compact_palette_editor()
        self.update_bottom_bar()
        self.request_redraw()

    def toggle_3d(self):
        self.store.set("view_3d", self.view_3d_var.get())
        if self.view_3d_var.get() and self.preview_var.get() != "single":
            self.preview_var.set("single")
        self.request_redraw()

    def reset_3d(self):
        """Straighten the view and put layers moved in 3D back in place."""
        self.view.yaw, self.view.pitch = -30.0, 20.0
        for il in self.image_layers():
            il.offset3d = (0, 0, 0)
        self.request_redraw()

    # ----- shared state changes -----
    def saved_colors_changed(self):
        self.saved_panels = [p for p in self.saved_panels if p.frame.winfo_exists()]
        for panel in self.saved_panels:
            panel.refresh()
        self.master.after_idle(self.align_saved_colors_sash)
        self.store.set("saved_colors", [list(c) if c else None for c in self.saved_colors])
