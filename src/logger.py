import logging
import sys


def logger_config():
    """Configura o logger raiz da aplicação."""
    log_level = logging.INFO
    log_format = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(log_format)
    root_logger.addHandler(stream_handler)
