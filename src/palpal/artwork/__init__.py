"""The Artwork Tool (a port of Spooksie's Stinky Sprite Tool), split into small modules.

Open it with SpriteTool(master, width, height, on_return=callback, theme=callable).
"""

from .common import *  # noqa: F401,F403
from .model import *  # noqa: F401,F403
from .tool import SpriteTool  # noqa: F401
