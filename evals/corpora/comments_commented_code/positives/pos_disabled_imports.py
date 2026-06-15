"""Disabled import statements left in modules during refactors."""

from __future__ import annotations

import json
import os

# import logging
# from datetime import datetime
# from pathlib import Path as _Path
# import numpy as np
# from .legacy import OldService
# from typing import Optional, List


def load_config(path: str) -> dict:
    """Return parsed JSON config from path."""
    return json.loads(open(path).read())


# import yaml
# import tomllib


PATH_SEP = os.sep
