"""Shared by every Artwork Tool module: imports and constants.

Artwork Tool (a port of Spooksie's Stinky Sprite Tool), part of PalPalPal.

A Python port of the web pixel art tool (spooksies-stinky-sprite-tool/code/spooksies_sprite_tool.js),
with Mew's layout changes: tool dropdowns are icon grids, the brush preview sits under the tool name,
size / display / other options live behind the File > Options Menu, and the colour palette, histogram
and channel tools are tucked under Other Options. "Save and Return" hands the finished sprite back to
PalPalPal as one layer.

Open it with SpriteTool(master, width, height, on_return=callback, theme=callable).
"""

import base64
import io
import json
import math
import os
import random
import time

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser

from PIL import Image, ImageChops, ImageTk


CANVAS_DIM = 480


MAX_ZOOM = 16


MAX_UNDO = 50


THUMB = 56


PREVIEW = 128


BLEND_FACTOR = 0.5


DEPTH_DARKEN = 0.95


HIGHLIGHT_BRIGHTEN = 1.05


SHARPEN_FACTOR = 0.15


HUE_SHIFT = 0.05


LASSO_THRESHOLD = 0.35


MAX_RECENT = 16


AUTO_SAVE_MS = 60000


AUTOSAVE_FILE = "sprite_autosave.json"


WORKSPACE_FILE = "sprite_workspace.json"


BLEND_MODES = [("normal", "Normal"), ("multiply", "Multiply"), ("screen", "Screen"), ("overlay", "Overlay"),
               ("add", "Add"), ("subtract", "Subtract"), ("darken", "Darken"), ("lighten", "Lighten"),
               ("difference", "Difference"), ("exclusion", "Exclusion"), ("hue", "Hue"),
               ("saturation", "Saturation"), ("colordodge", "Color Dodge"), ("colorburn", "Color Burn"),
               ("vividlight", "Vivid Light"), ("linearlight", "Linear Light"), ("softlight", "Soft Light"),
               ("hardlight", "Hard Light"), ("pinlight", "Pin Light"), ("hardmix", "Hard Mix")]


BLEND_LABEL = dict(BLEND_MODES)


BLEND_KEY = {label: key for key, label in BLEND_MODES}


PATTERNS = [("dots", "Dots"), ("checker", "Checkerboard"), ("stripes-h", "Horizontal Stripes"),
            ("stripes-v", "Vertical Stripes"), ("diagonal", "Diagonal Lines"), ("crosshatch", "Crosshatch"),
            ("bricks", "Bricks"), ("hexagon", "Hexagons")]


SYMMETRY = [("horizontal", "Horizontal (2-way)"), ("vertical", "Vertical (2-way)"), ("quad", "Quad (4-way)"),
            ("radial8", "Radial (8-way)"), ("radial16", "Radial (16-way)")]


BRUSH_SHAPES = [("circle", "Circle"), ("square", "Square"), ("plus", "Plus (+)"), ("x", "X Shape"),
                ("diamond", "Diamond"), ("star", "Star"), ("custom", "Custom...")]


PRESETS = [("Icon (30×30)", 30, 30), ("Portrait (105×105)", 105, 105), ("Full Character View (150×150)", 150, 150),
           ("Tiny (8×8)", 8, 8), ("Small (16×16)", 16, 16), ("Medium (32×32)", 32, 32), ("Large (48×48)", 48, 48),
           ("XLarge (64×64)", 64, 64)]


# Tool icon grids (the web tool's dropdown categories). (tool id or action, icon, name, shortcut)
TOOL_GROUPS = [
    ("Brush", [("pencil", "✏️", "Pencil (Circle)", "P"), ("pencilsquare", "▪", "Pencil (Square)", "Q"),
               ("refined", "·", "1px", "1"), ("fill", "🪣", "Fill", "F"), ("pattern", "▦", "Pattern Fill", ""),
               ("dither", "░", "Dither", ""), ("jumble", "🎲", "Jumble", "J"), ("spray", "💨", "Spray", "Y"),
               ("clone", "📋", "Clone Stamp", ""), ("erasecolor", "🧽", "Erase Color", "T"),
               ("magiceraser", "✨", "Magic Eraser", ""), ("eraser", "⌫", "Eraser", "E")]),
    ("Color", [("blend", "💧", "Blend", "B"), ("sharpen", "🔪", "Sharpen", "X"), ("depth", "🌑", "Shadow", "D"),
               ("highlight", "☀️", "Highlight", "H"), ("rainbow", "🌈", "Rainbow", "R"),
               ("gradient", "🌅", "Gradient", "G"), ("liquify", "🌊", "Liquify", ""),
               ("@curves", "📈", "Color Curves", "")]),
    ("Canvas", [("rectselect", "⬚", "Rectangle Select", "S"), ("circleselect", "◌", "Circle Select", "I"),
                ("colorselect", "🎯", "Color Select", "K"), ("edgeselect", "🔍", "Edge Detect", ""),
                ("lasso", "➰", "Lasso", "L"), ("symmetrical", "🦋", "Symmetry", "M"), ("pan", "✋", "Pan", "A"),
                ("@clearsel", "❎", "Cancel Selection", "Shift+A")]),
    ("Shape", [("line", "╱", "Line", "N"), ("curve", "◠", "Curve", "U"), ("contour", "〰", "Contour", "C"),
               ("polygon", "⬡", "Polygon", "O"), ("rectangle", "▭", "Rectangle", "V"), ("circle", "◯", "Circle", "W"),
               ("gradientmesh", "🕸", "Gradient Mesh", ""), ("beziercurve", "∿", "Bezier Brush", "")]),
    ("Global", [("@clearframe", "🗑", "Clear Current Frame", ""), ("@swap", "🔁", "Color Swap (Global)", ""),
                ("@remap", "🎨", "Color Remap (Multi)", "")]),
    ("Transform", [("@rot90", "↻", "Rotate 90° ↻", ""), ("@rot-90", "↺", "Rotate 90° ↺", ""),
                   ("@fliph", "↔", "Flip Horizontal", ""), ("@flipv", "↕", "Flip Vertical", ""),
                   ("@persp", "📐", "Perspective", ""), ("@undoxform", "⎌", "Undo Recent Transform", "")]),
    ("Batch", [("@brot", "⟳", "Rotate All Frames 90°", ""), ("@bfliph", "⇔", "Flip All Horizontal", ""),
               ("@bflipv", "⇕", "Flip All Vertical", ""), ("@bbright", "🔆", "Adjust All Brightness", ""),
               ("@bmagenta", "🟪", "Create Magenta Background", "")]),
]


TOOL_NAMES = {t: n for _g, tools in TOOL_GROUPS for t, _i, n, _k in tools}


TOOL_NAMES.update({"swap": "Color Swap", "rectselect": "Rectangle", "circleselect": "Circle", "colorselect": "Color"})


TOOL_MESSAGES = {
    "rectselect": "🔲 Rectangle Select: Hold left click and drag to make a selection, right click to cancel",
    "circleselect": "⭕ Circle Select: Hold left click and drag from center, right click to cancel",
    "lasso": "✏️ Lasso: Hold left click and drag to draw selection path, release to close, right click to cancel",
    "colorselect": "🎨 Color Select: Left click a color to select all matching pixels, right click to cancel",
    "edgeselect": "📐 Edge Detect: Left click to auto-detect edges and create selection, right click to cancel",
    "pan": "✋ Pan: Hold left click and drag to move canvas view, right click to reset position",
    "symmetrical": "🔄 Symmetry: Draw normally, strokes will mirror based on selected symmetry mode",
    "clone": "📋 Clone Stamp: Alt+Click to set source point, then left click to clone from that point",
    "line": "📏 Line: Click start point, then click end point to draw line",
    "curve": "〰️ Curve: Click start, end, then a control point",
    "contour": "🗺️ Contour: Click to add contour points, double-click to close",
    "polygon": "⬡ Polygon: Click to add polygon vertices, double-click to close shape",
    "rectangle": "▭ Rectangle: Click one corner, then the opposite corner",
    "circle": "⭕ Circle: Click one edge point, then the opposite edge point",
    "beziercurve": "〰️ Bezier Brush: Click 4 control points for a smooth curve",
    "gradientmesh": "🎨 Gradient Mesh: Click to place mesh points with colors, Enter to fill, Esc to cancel",
    "gradient": "🌈 Gradient: Click start point, then drag to apply the gradient",
    "fill": "🪣 Fill: Left click a pixel to fill connected area with current color",
    "magiceraser": "✨ Magic Eraser: Left click to erase connected pixels of similar color",
    "liquify": "💧 Liquify: Click and drag to push/warp pixels in the direction of movement",
}


SHORTCUT_TOOLS = {"s": "rectselect", "l": "lasso", "p": "pencil", "q": "pencilsquare", "a": "pan", "m": "symmetrical",
                  "r": "rainbow", "1": "refined", "g": "gradient", "b": "blend", "x": "sharpen", "d": "depth",
                  "e": "eraser", "f": "fill", "h": "highlight", "j": "jumble", "n": "line", "c": "contour",
                  "o": "polygon", "u": "curve", "k": "colorselect", "i": "circleselect", "t": "erasecolor",
                  "v": "rectangle", "w": "circle", "y": "spray"}


IMAGE_TYPES = [("Images", "*.png *.bmp *.gif *.jpg *.jpeg *.webp *.tga *.tif *.tiff"), ("All files", "*.*")]


NEIGHBOURS_4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


NEIGHBOURS_8 = tuple((dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy)
