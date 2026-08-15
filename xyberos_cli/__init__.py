"""xyberos-cli — the Xyberos plugin developer command line.

External, additive tooling layered on the stable Xyberos public API. Provides
``xyberos plugin create | validate | repair``.
"""

from . import create, main, repair, validate
from .main import main as cli_main

__all__ = ["cli_main", "create", "main", "repair", "validate"]

__version__ = "0.1.0"
