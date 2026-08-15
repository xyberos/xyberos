"""Example: load the texttools plugin and run its tools.

Run from the plugin directory:

    python examples/example.py

(If the plugin is installed, e.g. ``pip install -e .``, it can be run from
anywhere.)
"""

import sys
from pathlib import Path

# Allow running straight from the source tree without installing the plugin.
PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from xyberos import create_app

from texttools import plugin


def main() -> None:
    app = create_app()
    app.load_plugin(plugin)
    print("loaded plugins:", app.plugins.names)

    registry = app.resolve("tools")
    print("registered tools:", registry.names)
    print(registry.execute("slugify", None, text="Hello, World! 42"))
    print(
        registry.execute(
            "count_words",
            None,
            text="The quick brown fox jumps over the lazy dog",
        )
    )
    print(registry.execute("echo", None, text="ping"))

    app.unload_plugin(plugin.name)


if __name__ == "__main__":
    main()
