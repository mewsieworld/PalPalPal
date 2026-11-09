# PalPalPal Manual

PalPalPal is an image and palette editor for indexed (256-color) pixel art. You load images, recolor them
through their palettes, stack layers, animate frames, and export the results. You can also make 3D renders
out of your 2D models.

---

## Getting started

**New Project** (*File > New* or *Ctrl+N*): 
- Asks how many colors your palette has and what the background (key) color is. 
- Answer once and tick "Remember my choice" to skip the questions next time.
**Open Project** (*Ctrl+O*): opens a `.palpal` project.
**Save** (*Ctrl+S*) or **Save As** (*Ctrl+Shift+S*): keep everything: 
- Layers, palettes, frames, settings and 3D heights in a singular project file
**Import an image**: *Layers > New > Image Layer*, or *File > Import Image as Layer*
- Images that aren't indexed yet are converted (you choose the number of colors)
- Colors the conversion drops can be saved as a file
**Import a palette**: right-click the *Layers* box > *Import > Palette*, or *File > Import Palette*

### Keyboard shortcuts

These are also listed next to their items in the menus (the View menu holds the ones without another home).

- **F** Flip, **R** Rotate, **V** Reverse Palette (also the button under the Layers box), **B** BG Options
- **S** Super Swatch Switcher, **C** Artwork Tool, **E** Mass Frame Editor, **W** Img2img Palette Swap
- **A** next alignment, **P** next preview mode (Big / Small / No), **T** next frame type (Single / All / Custom)
- **Space** play / pause; **Space three times quickly** puts the canvas back at the top-left at 100% zoom
- **M** Manual, **H** Changelog
- **Ctrl+N** new, **Ctrl+O** open, **Ctrl+S** save, **Ctrl+Shift+S** save as
- **Left / Right** previous / next frame
- **Alt+click** / **drag a box** (All or Custom view) select several frames

## Main UI

**Main Canvas**
- The main canvas supports 2D and 3D Modes (togglable in Options)
- You can click and drag to pan or alt+click to move elements in 3D mode
- 2D mode allows clicking the canvas image to select the index (may also work in 3D mode!)
- The divider between the canvas and the right-hand column can be dragged.
**Zoom**: Change canvas zoom between 100-500% or "Fit"
**Align**: where the picture sits on the canvas

### Preview Modes

**Preview modes**: *Big Preview*, *Small Preview*, *No Preview*
- *Big Preview* is good for testing your display and mainly 2D images
- *Small Preview* is good for editing palettes on the same screen as a 3D image
- *No Preview* hides the picture and gives the palette editor the whole window for standalone palette editing
**Frame Type**: *Single* (one frame), *All* (every frame in a grid), *Custom* (a range, set in ⚙ Settings)
**🌙** switches dark mode
**⚙** opens the custom frame settings

### Timeline

⏮ ◀ ⏵ Play ▶ ⏭ step and play the frames
- You can also use the *space bar* to play/pause
**Hide Layer / Show Layer** toggles the selected layer.
**Speed** sets the playback speed
- The slider scrubs through the frames.
**Copy / Paste / Delete** a frame
**+ Frames** adds several blank frames
**- Frames** removes several at once (the selected ones, or numbers you type like 2-4, 7)
**Import Img as Frames** adds an image as new frames.
**Add Blank / Clone** add a frame
**Set Loop** marks the frames the playback loops over

### Layers

Layers stack bottom to top like a paint program.
- *Click* a row to select it
- *Drag* a row to move it
- *Double-click* to rename
- *Click the eye* to hide it.
**▲ Combined layer:** an image with its own palette (what an import gives you).
**● Image layer:** an image without its own palette; the palettes above it color it.
**■ Palette layer:** a palette that recolors the image below it.

**Effects** button on each row sets the blend mode and opacity.
- The **🎨** button on an image row picks which palette colors it: the stack above it, its own, or any palette.
- **New ▾:** Image Layer, Palette Layer (a new palette over the selected row), Draw Pixel Layer (Artwork Tool).

### **Right-click menu:**

- **Layer:** Import Img as Layer, Draw Layer, New Palette Layer, Rename, Show/Hide, Remove
- **Show:** ▲ All layers, ■ Palette layers, ● Img layers
- **Palette:** Import Palette, New Palette Layer, Edit, Separate Img (or Combine with Img)
- **Palette Inheritance:** Stack, Own, or a chosen palette layer

### BG Options

The BG Options button is on the bottom right. It changes its color with your desired background color.
- For the preview **BG Color**, clicking ✖ makes it transparent
- For **Palette BG Color**, the key color that shows as see-through.
- The 💧 eyedropper next to it keys out a color straight from the picture: click it, then click that color
  in the preview. Esc cancels. It works in the 2D view.

## Other UI's

### General Color Editor Panels

- **Active Colors** (under the preview) lists the colors the image uses. Click a color to select it, tick
  **Multi** to select several. The **Hue / Sat / Val** sliders shift the selection, **Reset** undoes that.
- The picker row: type an **Index** and press Go, type a **Hex** color, **🎨 Pick** takes a color from the
  picture, and the rainbow button opens the gradient menu.
- **Sort** orders the swatches by index, hue, saturation or value (click again to flip the order).
- **Saved Colors** keeps colors you like: load and save them as files (Documents/PalPalPal/Excess-colors).

### Super Swatch Switcher

Edit > Super Swatch Switcher (or press **S**). Three looks, chosen in Document & 3D Settings:

- **Simple:** the full 16 × 16 palette grid.
- **Advanced:** only the image's colors, with a live preview and Select All / Clear / Sort / Save / Reset.
- **NuAge:** the old icon editor layout.

### Mass Frame Editor (img2palette)

Edit > Mass Frame Editor. Edits every frame of an animation at once through their shared indexes, with a
frame strip, an eyedropper and color mappings. **Export** saves the frames as PNG, BMP 256 color, BMP 24-bit,
GIF, PCX, TGA, TIFF or WebP.

### Img2img Palette Swap

Edit > Img2img Palette Swap. Recolors a source picture with a reference picture's colors.

- Click a thumbnail to choose a picture; **double-click** shows it; **triple-click** shows both side by side.
- **Flip** and **Rotate** turn the view (with both shown, tick **per image** to turn only the one you clicked).
- 🖌 opens the **Palette to Palette Mapper**: pick a target color, then click the source color to map it.
  Each palette has **Reset Palette**; there are Undo / Redo, a Color Picker and Reset Both Palettes.
- ✖ resets everything, ▶ makes the result (add it as a layer or save it).

### Artwork Tool (pixel art)

Edit > Artwork Tool, Layers > New > Draw Pixel Layer, or right-click > Layer > Draw Layer.

- Tools are colored buttons grouped as Brush, Color, Canvas, Shape, Global, Transform and Batch.
  Hover one for its name and keyboard shortcut (Shortcuts menu lists them all).
- Layers (with masks, effects, blend modes), frames, onion skin, timeline and animation preview.
- **Options:** Size, Display (grid, background, dark mode) and Other (guides, tilemap, onion skin,
  autosave, the Color Palette and Histogram panels).
- **File > Save and Return** puts your drawing back into PalPalPal as one layer, below the selected one.

### 3D view

Options > 3D Layer View shows the picture as perler beads: every pixel is a cube and layers stack on top of
each other. Drag to turn it; Options > Reset 3D View straightens it.

- The floating button at the top right of the canvas switches between **⟳ Turn view** and **✥ Move layer**.
  In Move layer mode, dragging moves the selected image layer around the model; **Shift+drag** lifts or lowers it.
  Reset 3D View also puts moved layers back.

**3D height settings** (Options > Document & 3D Settings):

- **Flat:** one bead per pixel.
- **Per color (heightmap):** lighter colors stand taller.
- **Per color (sliders):** "Set heights per color" gives every color its own height.
- **Manually drawn:** "Draw heightmap" opens the Artwork Tool; black is 1 bead, white is the tallest.
- **Tallest** sets the maximum height in beads.
- **Back:** **Wall** keeps the back flat. **Mirror** puts the same heights on the back too, so turning the view
  round shows the relief reversed. Mirror also carries over into Export > 3D Model.

## Options, Exports, and Misc.

### Document & 3D Settings

Options > Document & 3D Settings.

- **Palette colors:** how many colors the palettes have (images with more are reduced).
- **Separate Palettes by Frames:** every frame gets its own palette; the Layers box gets < > frame tabs.
- **3D height settings** (above).
- **Preferences:** Palette Format (PAL, PNG grid or both), Super Swatch Switcher UI, Excess Colors prompts,
  open palettes in the Mass Frame Editor by default, and asking the New Project questions.
- **Show helpful hints:** untick it to hide the grey how-to lines across the program, like the 3D view's
  "drag to turn" line. Windows that are already open pick it up when you reopen them.
- **Reset to default settings** puts the preferences back (the palette size is left alone).

### Exports

- Export > Frame, Background, Palette, All Frames.
- Export > **3D Model** saves the 3D bead view (heights and 3D moves included) as **OBJ** (with an .mtl of
  colors, for Blender / Unity / Godot), **MagicaVoxel VOX** (up to 256 beads each way) or **PLY**,
  or a **Minecraft .schematic** (MCEdit format, for WorldEdit / Schematica). Each bead becomes the closest wool,
  concrete or terracotta block, and the picture stands upright facing south.
- Export > **Heightmap** saves the selected layer's heights as a greyscale PNG (black = 1 bead, white = tallest).
  Draw on it and load it back through Document & 3D Settings > 3D height settings > Manually drawn.
- Exports go to Documents/PalPalPal/exports.
- Palette files PalPalPal reads: PAL (VGA, JASC, RIFF), GPL, ACT, ACO, ASE, KPL, SketchPalette,
  KDE .colors, HEX, Paint.NET TXT, JSON, and the palette of any image.

### About

Help > About shows your version and build.

This program was made originally by Baylee C. of the former company Mewsie World LLC with assistance from Claude Workspace.

