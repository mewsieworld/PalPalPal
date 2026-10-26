"""Shared by every PalPalPal module: stdlib / Tk / Pillow imports and the app constants.

PalPalPal - an image and palette editor (formerly Corneas Plus, formerly the Fashion Previewer).

The old previewer (fashionpreviewer.py and the code/ package) is left untouched as a backup;
its features were ported into this package one at a time. See PORTING-CHECKLIST.md in the project folder.

Layers work like a paint program: images stack bottom to top, each image has its own palette,
and a stand-alone palette layer recolors the image right below it. The palette editor window is
the Super Swatch Switcher (Simple, Advanced and NuAge skins).

The program writes nothing next to itself except its __pycache__ user file, and falls back to
the user's local app data when that folder is read-only, so it runs the same from a portable
folder or from Program Files.
"""

import base64
import colorsys
import io
import json
import math
import os
import struct
import sys
import time

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, simpledialog

try:
    from PIL import GifImagePlugin, Image, ImageChops, ImageDraw, ImageSequence, ImageTk
except ImportError as exc:  # most often a Python build that has no Pillow installed for it
    sys.exit('PalPalPal could not load Pillow in this Python:\n  %s\n(%s)\n\n'
             'Run it with "python palpalpal.py" (or quickstart_windows.bat), or install Pillow for this Python.'
             % (sys.executable, exc))
APP_NAME = "PalPalPal"


# Bump APP_VERSION and push to UPDATE_BRANCH: the GitHub workflow builds PalPalPal.exe and publishes it as
# release v<APP_VERSION> in UPDATE_REPO, which Help > Check for Updates reads. The repo is private, so the
# workflow bakes a read-only token into the exe build (_update_token.py, never committed) to read releases.
APP_VERSION = "1.0.0"
UPDATE_REPO = "mewsieworld/PalPalPal"
UPDATE_BRANCH = "main"
# Release builds: PalPalPal.exe is the 32-bit (x86) build, PalPalPal-x64.exe the 64-bit one. Each copy updates
# itself with the file that matches how it was built.
BUILD_ARCH = "x64" if struct.calcsize("P") == 8 else "x86"
UPDATE_ASSETS = {"x86": "PalPalPal.exe", "x64": "PalPalPal-x64.exe"}
UPDATE_ASSET = UPDATE_ASSETS[BUILD_ARCH]
BUILD_LABEL = ""   # shown in the title bar and About box (the x64 backup copy says "x64-backup")
SWITCHER_NAME = "Super Swatch Switcher"
PALETTE_SIZE = 256
DEFAULT_SAVED_SLOTS = 20
ZOOM_LEVELS = ["100%", "200%", "300%", "400%", "500%", "Fit"]
PREVIEW_MODES = ["Big Preview", "Small Preview", "No Preview"]
ANIMATION_FPS = 8  # timeline playback at 1x speed
PROJECT_EXT = ".palpal"
PROJECT_TYPES = [("PalPalPal project", "*.palpal"), ("All files", "*.*")]
SKINS = ["Simple", "Advanced", "NuAge"]
IMAGE_EXTS = "*.bmp *.pcx *.tga *.pgm *.ppm *.pbm *.xpm *.xbm *.gif *.ico *.webp *.png *.tif *.tiff"
IMAGE_OPEN_TYPES = [
    ("All compatible images", IMAGE_EXTS),
    ("PNG", "*.png"), ("BMP", "*.bmp"), ("GIF", "*.gif"), ("PCX", "*.pcx"),
    ("TGA", "*.tga"), ("PGM / PPM / PBM", "*.pgm *.ppm *.pbm"), ("XPM / XBM", "*.xpm *.xbm"),
    ("ICO", "*.ico"), ("WebP", "*.webp"), ("TIFF", "*.tif *.tiff"), ("All files", "*.*"),
]
IMAGE_SAVE_TYPES = [
    ("PNG (transparent)", "*.png"), ("BMP (256 color)", "*.bmp"), ("GIF", "*.gif"),
    ("TGA", "*.tga"), ("TIFF", "*.tiff"), ("WebP", "*.webp"), ("PCX", "*.pcx"),
]
PALETTE_TYPES = [
    ("All palettes", "*.pal *.gpl *.act *.aco *.ase *.kpl *.sketchpalette *.colors *.hex *.txt *.json "
                     "*.png *.bmp *.gif *.pcx *.tga"),
    ("PAL (VGA / JASC / RIFF)", "*.pal"), ("GIMP GPL", "*.gpl"), ("Adobe ACT", "*.act"),
    ("Adobe Color Swatch", "*.aco"), ("Adobe Swatch Exchange", "*.ase"), ("Krita KPL", "*.kpl"),
    ("Sketch palette", "*.sketchpalette"), ("KDE colors", "*.colors"),
    ("HEX", "*.hex"), ("Text / Paint.NET", "*.txt"), ("JSON", "*.json"),
    ("Palette from image", "*.png *.bmp *.gif *.pcx *.tga"), ("All files", "*.*"),
]
IMAGE_PALETTE_EXTS = (".png", ".bmp", ".gif", ".pcx", ".tga", ".tif", ".tiff", ".webp")


# JSON stays first so it is the default; the other formats sit in the dropdown.
SAVED_COLOR_TYPES = [
    ("JSON", "*.json"), ("PAL", "*.pal"), ("GIMP GPL", "*.gpl"), ("Adobe ACT", "*.act"),
    ("HEX", "*.hex"), ("Text", "*.txt"),
]


# Keep GIF frames as palette images unless a frame really brings its own palette
GifImagePlugin.LOADING_STRATEGY = GifImagePlugin.LoadingStrategy.RGB_AFTER_DIFFERENT_PALETTE_ONLY

