"""Compatibility shim for legacy entrypoint.

Use `abliterador_studio.py` as the primary launcher.
"""

import sys

from abliterador_studio import main


if __name__ == "__main__":
    sys.exit(main())
