from unittest.mock import Mock

from xyberos.kernel.logger import Logger


def test_logger_delegates_each_log_level_to_standard_logger():
    logger = Logger(name="xyberos.tests.logger")
    backend = Mock()
    logger._logger = backend

    logger.debug("debug %s", "message")
    logger.info("info")
    logger.warning("warning")
    logger.error("error")
    logger.exception("exception")

    backend.debug.assert_called_once_with("debug %s", "message")
    backend.info.assert_called_once_with("info")
    backend.warning.assert_called_once_with("warning")
    backend.error.assert_called_once_with("error")
    backend.exception.assert_called_once_with("exception")
