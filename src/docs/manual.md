# PalPalPal Manual

PalPalPal is an image and palette editor for indexed (256-color) pixel art. You load images, recolor them
through their palettes, stack layers, animate frames, and export the results.

**Editing this manual:** it is the plain text file `src/docs/manual.md` (next to the exe: `docs/manual.md`).
Change it in any text editor and save; it shows the new text the next time you open Help > Manual.
Formatting: `# Heading`, `## Heading`, `- bullet`, `**bold**`, and `---` for a line.

---` for a line.

---

## Getting started

- **New Project** (File > New, Ctrl+N): asks how many colors your palette has and what the background (key)
  color is. Answer once and tick "Remember my choice" to skip the questions next time.
- **Open Project** (Ctrl+O) opens a `.palpal` project. **Save** (Ctrl+S) / **Save As** keep everything:
  layers, palettes, frames, settings and 3D heights.
- **Import an image:** Layers > New > Image Layer, or File > Import Image as Layer. Images that aren't indexed
  yet are converted (you choose the number of colors). Colors the conversion drops can be saved as a file.
- **Import a palette:** right-click the Layers box > Import > Palette, or File > Import Palette.

## The main window

- **Zoom** (top left) and the **preview mode** dropdown: Big Preview, Small Preview, No Preview.
  No Preview hides the picture and gives the palette editor the whole window.
- **Align** (between Zoom and the preview dropdown): where the picture sits on the canvas.
- **Frame Type:** Single (one frame), All (every frame in a grid), Custom (a range, set in ⚙ Settings).
- **🌙** switches dark mode. **⚙** opens the custom frame settings.
- The divider between the canvas and the right-hand column can be dragged.

## Layers

Layers stack bottom to top like a paint program.

- **▲ Combined layer:** an image with its own palette (what an import gives you).
- **● Image layer:** an image without its own palette; the palettes above it color it.
- **■ Palette layer:** a palette that recolors the image below it.
- Click a row to select it, **drag** a row to move it, **double-click** to rename, click the **eye** to hide it.
- The **effects** button on each row sets the blend mode and opacity.
- The **🎨** button on an image row picks which palette colors it: the stack above it, its own, or any palette.
- **New ▾:** Image Layer, Palette Layer (a new palette over the selected row), Draw Pixel Layer (Artwork Tool).

**Right-click menu:**

- **Layer:** Import Img as Layer, Draw Layer, New Palette Layer, Rename, Show/Hide, Remove
- **Show:** ▲ All layers, ■ Palette layers, ● Img layers
- **Palette:** Import Palette, New Palette Layer, Edit, Separate Img (or Combine with Img)
- **Palette Inheritance:** Stack, Own, or a chosen palette layer

## Timeline

- ⏮ ◀ ⏵ Play ▶ ⏭ step and play the frames; **Hide Layer / Show Layer** toggles the selected layer.
- **Speed** sets the playback speed; the slider scrubs through the frames.
- **Copy / Paste / Delete** a frame. **+ Frames** adds several blank frames, **- Frames** removes several at once
  (the selected ones, or numbers you type like 2-4, 7), and **Import Img as Frames** adds an image as new frames.
- **Add Blank / Clone** add a frame, **Set Loop** marks the frames the playback loops over.

## Editing colors

- **Active Colors** (under the preview) lists the colors the image uses. Click a color to select it, tick
  **Multi** to select several. The **Hue / Sat / Val** sliders shift the selection, **Reset** undoes that.
- The picker row: type an **Index** and press Go, type a **Hex** color, **🎨 Pick** takes a color from the
  picture, and the rainbow button opens the gradient menu.
- **Sort** orders the swatches by index, hue, saturation or value (click again to flip the order).
- **Saved Colors** keeps colors you like: load and save them as files (Documents/PalPalPal/Excess-colors).

## Super Swatch Switcher

Edit > Super Swatch Switcher (or press **P**). Three looks, chosen in Document Settings:

- **Simple:** the full 16 × 16 palette grid.
- **Advanced:** only the image's colors, with a live preview and Select All / Clear / Sort / Save / Reset.
- **NuAge:** the old icon editor layout.

## Mass Frame Editor (img2palette)

Edit > Mass Frame Editor. Edits every frame of an animation at once through their shared indexes, with a
frame strip, an eyedropper and color mappings. **Export** saves the frames as PNG, BMP 256 color, BMP 24-bit,
GIF, PCX, TGA, TIFF or WebP.

## Img2img Palette Swap

Edit > Img2img Palette Swap. Recolors a source picture with a reference picture's colors.

- Click a thumbnail to choose a picture; **double-click** shows it; **triple-click** shows both side by side.
- **Flip** and **Rotate** turn the view (with both shown, tick **per image** to turn only the one you clicked).
- 🖌 opens the **Palette to Palette Mapper**: pick a target color, then click the source color to map it.
  Each palette has **Reset Palette**; there are Undo / Redo, a Color Picker and Reset Both Palettes.
- ✖ resets everything, ▶ makes the result (add it as a layer or save it).

## Artwork Tool (pixel art)

Edit > Artwork Tool, Layers > New > Draw Pixel Layer, or right-click > Layer > Draw Layer.

- Tools are colored buttons grouped as Brush, Color, Canvas, Shape, Global, Transform and Batch.
  Hover one for its name and keyboard shortcut (Shortcuts menu lists them all).
- Layers (with masks, effects, blend modes), frames, onion skin, timeline and animation preview.
- **Options:** Size, Display (grid, background, dark mode) and Other (guides, tilemap, onion skin,
  autosave, the Color Palette and Histogram panels).
- **File > Save and Return** puts your drawing back into PalPalPal as one layer, below the selected one.

## 3D view

Options > 3D Layer View shows the picture as perler beads: every pixel is a cube and layers stack on top of
each other. Drag to turn it; Options > Reset 3D View straightens it.

- The floating button at the top right of the canvas switches between **⟳ Turn view** and **✥ Move layer**.
  In Move layer mode, dragging moves the selected image layer around the model; **Shift+drag** lifts or lowers it.
  Reset 3D View also puts moved layers back.

**3D height settings** (Options > Document Settings):

- **Flat:** one bead per pixel.
- **Per color (heightmap):** lighter colors stand taller.
- **Per color (sliders):** "Set heights per color" gives every color its own height.
- **Manually drawn:** "Draw heightmap" opens the Artwork Tool; black is 1 bead, white is the tallest.
- **Tallest** sets the maximum height in beads.

## Document Settings

Options > Document Settings.

- **Palette colors:** how many colors the palettes have (images with more are reduced).
- **Separate Palettes by Frames:** every frame gets its own palette; the Layers box gets < > frame tabs.
- **3D height settings** (above).
- **Preferences:** Palette Format (PAL, PNG grid or both), Super Swatch Switcher UI, Excess Colors prompts,
  open palettes in the Mass Frame Editor by default, and asking the New Project questions.
- **Reset to default settings** puts the preferences back (the palette size is left alone).

## BG Options

The BG Options button (bottom right): the preview **BG Color** (✖ makes it transparent) and the
**Palette BG Color**, the key color that shows as see-through.

## Exports

- Export > Export Frame, Export Background, Export Palette, Export All Frames.
- Exports go to Documents/PalPalPal/exports.
- Palette files PalPalPal reads: PAL (VGA, JASC, RIFF), GPL, ACT, ACO, ASE, KPL, SketchPalette,
  KDE .colors, HEX, Paint.NET TXT, JSON, and the palette of any image.

## About

Help > About shows your version and build.

## Keyboard shortcuts

- **Ctrl+N** new, **Ctrl+O** open, **Ctrl+S** save
- **Left / Right** previous / next frame
- **P** Super Swatch Switcher
- **F** reverse the color order of the selected layer's palette on this frame
- **Alt+click** / **drag a box** (All or Custom view) select several frames
