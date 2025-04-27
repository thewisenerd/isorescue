import logging
import typing

logger = logging.getLogger('isorescue:tracing_io')

BLUE = "\033[0;34m"
GREEN = "\033[0;32m"
RESET = "\033[0m"

READ_COLOR = GREEN
SEEK_COLOR = BLUE

class TracingIO(typing.BinaryIO):
    def __enter__(self):
        logger.debug("__enter__")
        return self.fp.__enter__()

    def __next__(self):
        logger.debug("__next__")
        return self.fp.__next__()

    def __iter__(self):
        logger.debug("__iter__")
        return self.fp.__iter__()

    def __exit__(self, typ, value, traceback, /):
        logger.debug("__exit__")
        return self.fp.__exit__(typ, value, traceback)

    def __init__(self, fp: typing.BinaryIO):
        logger.debug("fn:__init__")
        self.fp = fp

    def close(self):
        logger.debug("fn:close")
        return self.close()

    def fileno(self):
        logger.debug("fn:fileno")
        return self.fp.fileno()

    def flush(self):
        logger.debug("fn:flush")
        return self.fp.flush()

    def isatty(self):
        logger.debug("fn:isatty")
        return self.fp.isatty()

    def read(self, n=-1, /):
        logger.debug("%sfn:read%s n=%d, hex_n=%02x, sector=%.02f", READ_COLOR, RESET, n, n, n/2048.0)
        return self.fp.read(n)

    def readable(self):
        logger.debug("fn:readable")
        return self.fp.readable()

    def readline(self, limit=-1, /):
        logger.debug("fn:readline, limit=%d", limit)
        return self.fp.readline()

    def readlines(self, hint=-1, /):
        logger.debug("fn:readlines hint=%d", hint)
        return self.fp.readlines(hint)

    def seek(self, offset, whence=0, /):
        logger.debug("%sfn:seek%s offset=%d, hex_offset=%02x, sector=%.02f, whence=%d", SEEK_COLOR, RESET, offset, offset, offset/2048.0, whence)
        return self.fp.seek(offset, whence)

    def seekable(self):
        logger.debug("fn:seekable")
        return self.fp.seekable()

    def tell(self):
        logger.debug("fn:tell")
        return self.fp.tell()

    def truncate(self, size=None, /):
        logger.debug("fn:truncate, size=%d", size)
        return self.fp.truncate(size)

    def writable(self):
        logger.debug("fn:writeable")
        return self.fp.writable()

    def write(self, s, /):
        logger.debug("fn:write")
        return self.fp.write(s)

    def writelines(self, lines, /):
        logger.debug("fn:writelines")
        return self.writelines(lines)

    @property
    def mode(self):
        logger.debug("prop:mode")
        return self.fp.mode