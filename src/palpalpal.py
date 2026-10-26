#!/usr/bin/env python
"""PalPalPal - an image and palette editor. Start it with `python palpalpal.py`.

The program lives in the palpal/ package next to this file, split into small modules (see
palpal/__init__.py for the map). This file only starts it, and re-exports the package so scripts
that `import palpalpal` keep working.
"""

from palpal import *  # noqa: F401,F403
from palpal.app import main

if __name__ == "__main__":
    main()
