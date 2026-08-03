"""Plugin loading and lifecycle errors."""


class PluginError(Exception):
    """Base error for plugin discovery and lifecycle operations."""


class PluginAlreadyLoadedError(PluginError, KeyError):
    """Raised when loading a plugin whose name is already active."""


class PluginNotFoundError(PluginError, KeyError):
    """Raised when unloading or retrieving an unknown plugin."""


class PluginLoadError(PluginError):
    """Raised when a module does not expose a valid plugin."""
