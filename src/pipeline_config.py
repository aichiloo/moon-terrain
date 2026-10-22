from pathlib import Path
import os

REPO = Path(__file__).resolve().parents[1]
BASE = REPO
OUTPUT = Path(os.environ.get('MOON_TERRAIN_OUTPUT', REPO / 'build' / 'regions')).resolve()
BASE_LIBRARY = Path(os.environ.get('MOON_TERRAIN_BASE_LIBRARY', REPO / 'inputs' / 'base_library')).resolve()
APPROVED_PILOT = Path(os.environ.get('MOON_TERRAIN_APPROVED_PILOT', REPO / 'build' / 'pilot')).resolve()
REFERENCE_ROOT = Path(os.environ.get('MOON_TERRAIN_REFERENCE_ROOT', REPO / 'inputs')).resolve()
