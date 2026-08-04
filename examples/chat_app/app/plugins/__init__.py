"""Pluggable auto-discovered plugins for the chat app.

Nothing imports these modules by name. ``main.py`` runs
``xyberos.load_plugins_from("app.plugins")``, which walks this package and loads
every concrete ``Plugin`` subclass it finds, registering their services with the
Xyberos kernel.
"""
