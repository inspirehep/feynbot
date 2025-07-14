import inspect
import logging
import time
from contextlib import contextmanager


@contextmanager
def timer(name):
    frame = inspect.currentframe().f_back.f_back
    module_name = frame.f_globals["__name__"]
    logger = logging.getLogger(module_name)

    start = time.time()
    yield
    logger.warning(f"{name} time: %.2fs", time.time() - start)
