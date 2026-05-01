import logging


def _setup_logger():
    logger = logging.getLogger("UiTestAuto")
    logger.setLevel(logging.DEBUG)
    
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
    return logger

logger = _setup_logger()
