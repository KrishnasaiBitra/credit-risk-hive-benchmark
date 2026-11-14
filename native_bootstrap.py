"""Load an OpenMP runtime before importing native model dependencies."""
import ctypes
from pathlib import Path
import os
import platform

_openmp_handle = None


def initialize_openmp():
    global _openmp_handle
    if platform.system() != 'Linux':
        return
    if not os.environ.get('CREDIT_RISK_FORCE_BUNDLED_OPENMP'):
        try:
            _openmp_handle = ctypes.CDLL('libgomp.so.1', mode=ctypes.RTLD_GLOBAL)
            return
        except OSError:
            pass
    if platform.machine() not in {'x86_64', 'AMD64'}:
        raise RuntimeError('Install the platform OpenMP runtime before loading LightGBM.')
    library = Path(__file__).resolve().parent / 'native/libgomp.so.1'
    _openmp_handle = ctypes.CDLL(str(library), mode=ctypes.RTLD_GLOBAL)
