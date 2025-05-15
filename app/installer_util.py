import sys
from pathlib import Path


def get_asset(path: str):
    if getattr(sys, 'frozen', False):
        folder = Path(sys._MEIPASS)
    else:
        folder = Path('.')

    return folder / path
