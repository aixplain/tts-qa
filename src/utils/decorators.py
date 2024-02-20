import time
from functools import wraps

from src.logger import root_logger


log = root_logger.getChild("timing")


def log_timing(func):
    # we use a decorator to log the time it takes to execute a function
    # this saves boilerplate code in each function
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        log.info(f"{func.__name__} took {duration} seconds ({duration / 60:.2f} minutes)")
        return result

    return wrapper
