import logging
import os
from functools import cache
from logging import Logger

from botocore.exceptions import ClientError
from rich.console import Console
from rich.logging import RichHandler

console = Console(
    color_system="256",
    width=150,
    style="blue"
)

DEBUG: int = int(os.getenv("DEBUG", "0"))


@cache
def get_logger(module_name: str) -> Logger:
    """Get logger for module :module_name."""
    logger = logging.getLogger(module_name)
    handler = RichHandler(
        rich_tracebacks=True,
        console=console,
        tracebacks_show_locals=True,
    )
    handler.setFormatter(
        logging.Formatter(
            "[%(name)s @%(threadName)s:%(funcName)s:%(lineno)d] %(message)s"
        )
    )
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
    return logger


def get_exc_msg(
    msg: str | None = None,
    exc: Exception | None = None
):
    if not (msg or exc):
        raise ValueError('Either :msg: or :exc: needs to be provided.')

    exc_msg = ""
    if msg:
        exc_msg = msg
    if exc:
        exc_msg += '\nException:\n{}'.format(getattr(exc, 'message', str(exc)))

    return exc_msg


class LoggerValueError(ValueError):
    def __init__(
        self,
        logger: Logger,
        msg: str | None = None,
        exc: Exception | None = None,
        *args
    ):
        self.msg = get_exc_msg(msg, exc)
        logger.error(self.msg)
        super().__init__(self.msg, *args)


class LoggerOSError(OSError):
    def __init__(
        self,
        logger: Logger,
        msg: str | None = None,
        exc: Exception | None = None,
        *args
    ):
        self.msg = get_exc_msg(msg, exc)
        logger.error(self.msg)
        super().__init__(self.msg, *args)


class LoggerIndexError(IndexError):
    def __init__(
        self,
        logger: Logger,
        msg: str | None = None,
        exc: Exception | None = None,
        *args
    ):
        self.msg = get_exc_msg(msg, exc)
        logger.error(self.msg)
        super().__init__(self.msg, *args)


class LoggerClientError(ClientError):
    def __init__(
        self,
        logger: Logger,
        msg: str | None = None,
        exc: Exception | None = None,
        *args
    ):
        self.msg = get_exc_msg(msg, exc)
        logger.error(self.msg)
        super().__init__(self.msg, *args)
