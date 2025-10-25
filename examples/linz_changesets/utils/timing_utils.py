import time
import datetime
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

def timing_decorator(func):
    """
    A helper wrapper function to time other functions.
    """
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        formatted = str(datetime.timedelta(seconds=elapsed_time))
        msg = f"Function '{func.__name__}' elapsed time: {formatted}."

        if logger.hasHandlers():
            logger.info(msg)
        return result
        
    return wrapper

@contextmanager
def timer():
    """
    A context manager to time a block of code.
    """
    start_time = time.time()
    yield
    end_time = time.time()
    elapsed_time = end_time - start_time
    formatted = str(datetime.timedelta(seconds=elapsed_time))
    msg = f"Block of code elapsed time: {formatted}."

    # Use the logger if logging is configured
    if logger.hasHandlers():
        logger.info(msg)