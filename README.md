# PalPalPal
A Perfect Palette-n-Pixel Editor. Now supporting 3D features.

## Installing & Running

### If you download the Code/ZIP

1. Download Python
2. Follow the Tutorial in `AAA Tutorials` > `pythonpathwind.png`
![Python](AAA Tutorials/pythonpathwind.png)
3. OPTIONAL: Download Visual Studio to build the EXE Yourself
4. Extract the folder after restarting your computer
5. Run `firststart_windows.bat` OR in the `PalPalPal` folder in File Explorer, click the Directory name (Where it shows `C:\Your\Path\To\PalPalPal\`) and type `powershell` then press `Enter`. (If you ran `firststart_windows.bat, skip to Step 9)
6. Type `pip install pillow` and wait.
7. Type `cd src`
8. Type `python palpalpal.py` or `py palpalpal.py`
9. You've run it! Great job!
10. If you want a quick launch next time since you've downloaded the dependency already (`pillow`), click on `quickstart_windows.bat` instead of `firststart_windows.bat` :)

### If you download the `.exe`

1. Click on the `PalPalPal.exe` you have selected. If you are on Windows up to Windows 10, either should be fine, but Windows 11 onwards may require `x64`.
2. You're done!

# More About

PalPalPal supports:
- Palette editing for 2D and 3D Images as well as palette files themselves.
- 2D and 3D views, editing, and exporting
![3d1](pics/3dview1.png)
![3d2](pics/3dview2.png)
- 3D Rotation, mirroring, and Heightmap Control
![3dmirror](pics/3dview_mirror.png)
- Palette indexing up to 256 indexes, swapping, and exporting
- Heightmap display, editing, and exporting
- 3 Main Display Modes ->
	- Big Preview:
		- Timeline, Frame Controls, and Palette/Image layer preview along with actual Image preview
![Main_view_lightmode](pics/main_view_light_mode.png)
	- Small Preview:
		- Timeline, Palette/Image layer preview, smaller Image Preview window than Big, Saved
			colors boxes, index displays, HSV Adjustments, image and frame controls
![SmallPV](pics/small_preview_mode.png)
	- No Preview:
		- Basically everything in Small Preview but with the Indexes and HSV sliders bigger with
			no image preview or changes. However, Timeline and Layers are still visible, as
			one may want to change them.
![NoPV](pics/no_preview_mode_with_multiselect_and_hsv_change.png)
- A mini Editor with 3 UI's:
	- Simple:
		- Grid showing all indexes, Saved Colors, HSV Adjustment sliders, Multi-select, Gradient
			button, Palette Export and selection.
![Simple](pics/swatch_simple.png)
	- Advanced:
		- Image Preview, Filtered indexes, Colorpicker, Gradient button, Click-to-select-index, 
			Index sorting, multi-select, color sliders (Hue/Saturation/Value), palette export 
			and selection, frame preview, saved colors, and zoom
![Advanced](pics/swatch_advanced_preview.png)
![Advanced2](pics/swatch_advanced_smaller_preview.png)
	- NuAge:
		- Image Preview (based on your main UI's Preview Mode), Filtered Indexes, Gradient Button, 
			colorpicker, HSV Sliders, Saved Colors, Click-to-select-index, palette export and
			selection, frame selection, and zoom.
![NuageNP](pics/nuage_nopreview.png)
![NuageP](pics/nuage_preview.png)
- Timeline, Frame, and Animation Control
- Custom Frame Preview Options (Number of Frames, Start and End Frame)
- Ability to switch between using either a palette, image, or both from any layer
- Right Click Context Menu for Image Preview and Layers Box
	- Image Preview:
		- Set As Current Frame
		- Switch to Single Preview (Switches to `Frame Type: Single`)
		- Select Frame
		- Reverse this frame's palette
		- Hide this frame
		- Hide selected frames
	- Layers Box:
		- Layer >
			- Import Img as Layer
			- Draw [a] Layer
			- New Palette Layer
		- Show > 
			- All Layers
			- Palette Layers
			- Img Layers
		- Palette > 
			- Import Palette...
			- New Palette Layer
- Stack Palettes and change Layer Opacity and Blend Modes
- A mini Manual
- Changelog, including the base program's it was made from that I had created and formerly released
- Frame, Background, and Palette Export
- Awesome Gradient button and Dark Mode

![Gradient](pics/gradient_menu.png)
![MainView](pics/main_view_darkmode.png)
- A sprite editor that supports multiple tools, layers, animations, shortcuts, histograms (Options > Other Options),
	and so much more.
![Sprite](pics/sprite_tool.png)
- An image-to-image palette swapper
- A palette to palette swapper for many frames
![MassFrame](pics/mass_frame_editor.png)
- Local Statistics (For fun :3c )


# Credits

Proprietary software ownership of Mewsie and usage of other Open Source materials along with help from Claude Workspace.

Inspiration originally from having limitations of the software known as [PalEdit](https://www.baker76.com/paledit/).
