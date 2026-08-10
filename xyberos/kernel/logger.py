"""Logging adapter used by the core components."""

import logging
from typing import Any


class Logger:
    """A thin stable interface over Python's standard logging system."""

    def __init__(self, name: str = "xyberos", level: int | str = logging.INFO) -> None:
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
            self._logger.addHandler(handler)
        self._logger.propagate = False

    def debug(self, msg: str, *args: object, **kwargs: Any) -> None:
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args: object, **kwargs: Any) -> None:
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args: object, **kwargs: Any) -> None:
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args: object, **kwargs: Any) -> None:
        self._logger.error(msg, *args, **kwargs)

    def exception(self, msg: str, *args: object, **kwargs: Any) -> None:
        self._logger.exception(msg, *args, **kwargs)
