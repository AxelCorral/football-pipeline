"""
Logger standard du pipeline football.

Format de sortie : YYYY-MM-DD HH:MM:SS | LEVEL    | module | message

Usage :
    from src.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Pipeline démarré")
"""

import logging
import sys


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Retourne un logger configuré avec le format standard du pipeline.

    Le guard sur `handlers` empêche l'ajout de handlers dupliqués
    si la fonction est appelée plusieurs fois avec le même nom.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger
