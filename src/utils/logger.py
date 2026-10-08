import logging
import sys

def setup_logger(name: str = "GoogleTrendsScraper", level: int = logging.INFO) -> logging.Logger:
    """Thiết lập logger chuẩn với mã hóa UTF-8 an toàn trên Windows"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

