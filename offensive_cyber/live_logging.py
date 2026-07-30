"""Console logging setup.

agent.py logs every step, tool call, and observation directly via the
logger returned here as it runs, so students see the whole run live instead
of only a summary line at the end.
"""

import logging


def configure_logging(level: str = "INFO") -> logging.Logger:
    """Configure console logging once and return this project's logger."""
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("offensive_cyber")
