# log_config.py
import logging
import os
import sys

def logger_config(name, file):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s|%(name)s|%(levelname)s|%(message)s')

    fh = logging.FileHandler(file)
    fh.setFormatter(formatter)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(sh)

    return logger
