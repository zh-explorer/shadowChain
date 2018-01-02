import logging


def log_init():
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)

    file_log = logging.FileHandler("/tmp/shadow.log")
    file_log.setLevel(logging.INFO)

    fmt = logging.Formatter('[%(levelname)s] %(asctime)s  %(filename)s : %(message)s')
    console.setFormatter(fmt)
    fmt = logging.Formatter('[%(levelname)s] %(asctime)s  %(filename)s : %(message)s')
    file_log.setFormatter(fmt)

    logger = logging.getLogger("shadow")
    logger.addHandler(console)
    logger.addHandler(file_log)
    logger.setLevel(logging.DEBUG)
    return logger


logger = log_init()


def get_logger():
    return logger
