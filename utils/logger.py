"""Logging setup for Compresso (compresso).

Provides a factory function that returns a :class:`logging.Logger` configured
with a coloured console handler and a rotating file handler.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_LOG_DIR = Path(__file__).resolve().parent.parent / "output"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_LOG_FILE = _LOG_DIR / "compresso.log"

# ---------------------------------------------------------------------------
# ANSI colour helpers (no-op when output is not a TTY)
# ---------------------------------------------------------------------------

_ANSI_RESET = "\033[0m"
_LEVEL_COLOURS: dict[int, str] = {
    logging.DEBUG: "\033[36m",       # cyan
    logging.INFO: "\033[32m",        # green
    logging.WARNING: "\033[33m",     # yellow
    logging.ERROR: "\033[31m",       # red
    logging.CRITICAL: "\033[1;31m",  # bold red
}


def _colourise(message: str, levelno: int) -> str:
    """Wrap *message* in ANSI escape codes when stdout is a TTY."""
    if not sys.stdout.isatty():
        return message
    colour = _LEVEL_COLOURS.get(levelno, _ANSI_RESET)
    return f"{colour}{message}{_ANSI_RESET}"


# ---------------------------------------------------------------------------
# Custom formatter
# ---------------------------------------------------------------------------


class _ColourFormatter(logging.Formatter):
    """Formatter that colourises the level name in console output."""

    def format(self, record: logging.LogRecord) -> str:
        record.levelname = _colourise(record.levelname, record.levelno)
        return super().format(record)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_loggers: dict[str, logging.Logger] = {}


def setup_logger(
    name: str,
    level: int = logging.INFO,
) -> logging.Logger:
    """Return a logger configured for console + file output.

    The logger is cached so that repeated calls with the same *name* return
    the same instance without re-adding handlers.

    Parameters
    ----------
    name:
        Logger name (typically ``__name__`` of the calling module).
    level:
        Minimum log level.  Defaults to :data:`logging.INFO`.

    Returns
    -------
    logging.Logger
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent propagation to the root logger to avoid duplicate messages.
    logger.propagate = False

    # ---- Console handler (colourised) ----
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_fmt = _ColourFormatter(
        fmt="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    # ---- File handler (plain text, append mode) ----
    file_handler = logging.FileHandler(_LOG_FILE, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # always write everything to file
    file_fmt = logging.Formatter(
        fmt="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    _loggers[name] = logger
    return logger