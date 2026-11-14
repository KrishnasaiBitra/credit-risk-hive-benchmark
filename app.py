"""Vercel FastAPI entrypoint; research artifacts remain read-only."""
from native_bootstrap import initialize_openmp

initialize_openmp()

from interface.app import app
