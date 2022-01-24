import logging
from logging.handlers import RotatingFileHandler
from .cfgvars import cfgvars
import sys
import os


def get_logger(name):
    log_level = int(os.environ.get("LOG_LEVEL", 1))
    log_levels = [logging.NOTSET, logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]
    logger = logging.getLogger(name)
    logger.setLevel(logging.NOTSET)
    if not logger.handlers:
        formatter = logging.Formatter(
            '[ %(asctime)s ] | [ %(levelname)6s ] :  [  %(module)10s -> %(funcName)20s  ] -->  %(message)s ')
        logger.propagate = 0

        con_handler = logging.StreamHandler(sys.stderr)
        con_handler.setLevel(log_levels[log_level])
        con_handler.setFormatter(formatter)
        logger.addHandler(con_handler)
        file_handler = RotatingFileHandler(cfgvars.config["logfile"], mode="a", encoding="utf-8", maxBytes=10*1024*1024)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.setLevel(log_levels[log_level])

    return logger
