"""Minimal chat with Xyberos using the default (echo) model.

Run:  python examples/minimal_chat.py
"""

from xyberos import create_app


def main() -> None:
    app = create_app()
    print(app.chat("Hello, Xyberos!"))


if __name__ == "__main__":
    main()
