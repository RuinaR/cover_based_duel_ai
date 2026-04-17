import atexit
import logging
from logging import Logger
from pathlib import Path


_LOGGER_NAME = "cover_based_duel_ai"
_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_LOG_DIR = Path("logs")
_LOG_FILE = _LOG_DIR / "game.log"
_BUFFER_HANDLER: logging.Handler | None = None
_BUFFERED_LINES: list[str] = []
_LOGGING_INITIALIZED = False
_LOGGING_SHUTDOWN = False


class _BufferedLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
        except Exception:
            self.handleError(record)
            return

        _BUFFERED_LINES.append(message)


def get_logger(name: str = _LOGGER_NAME) -> Logger:
    _initialize_logging()

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.addHandler(_BUFFER_HANDLER)
    return logger


def shutdown_logging() -> None:
    global _LOGGING_SHUTDOWN

    if not _LOGGING_INITIALIZED or _LOGGING_SHUTDOWN:
        return

    _LOGGING_SHUTDOWN = True
    if not _BUFFERED_LINES:
        return

    with _LOG_FILE.open("a", encoding="utf-8") as logStream:
        logStream.write("\n".join(_BUFFERED_LINES))
        logStream.write("\n")

    _BUFFERED_LINES.clear()


def _initialize_logging() -> None:
    global _BUFFER_HANDLER, _LOGGING_INITIALIZED

    if _LOGGING_INITIALIZED:
        return

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    _LOG_FILE.touch(exist_ok=True)

    _BUFFER_HANDLER = _BufferedLogHandler()
    _BUFFER_HANDLER.setLevel(logging.INFO)
    _BUFFER_HANDLER.setFormatter(logging.Formatter(_LOG_FORMAT))
    _LOGGING_INITIALIZED = True


atexit.register(shutdown_logging)
