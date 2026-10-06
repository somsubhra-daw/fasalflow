import logging
import sys


def setup_logging() -> None:
    """Configure structured console logging for the application.
    Avoid logging sensitive data like passwords or tokens.
    """
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )


logger = logging.getLogger("fasalflow")
