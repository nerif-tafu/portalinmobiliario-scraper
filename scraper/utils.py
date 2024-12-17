import logging
import os
from datetime import datetime

_logger = None

def setup_logger():
    """Configure logging to both file and console"""
    global _logger
    if _logger is not None:
        return _logger
        
    # Create logs directory if it doesn't exist
    logs_dir = 'logs'
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Create a logger
    _logger = logging.getLogger('scraper')
    _logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    _logger.handlers = []

    # Create formatters
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_formatter = logging.Formatter('%(message)s')

    # File handler - logs/scraper_YYYYMMDD_HHMMSS.log
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_handler = logging.FileHandler(f'logs/scraper_{timestamp}.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Add handlers to logger
    _logger.addHandler(file_handler)
    _logger.addHandler(console_handler)

    return _logger

def log_and_print(message, level='info', color=None):
    """Helper function to both log and print messages"""
    logger = setup_logger()
    
    if level == 'info':
        logger.info(message)
    elif level == 'warning':
        logger.warning(message)
    elif level == 'error':
        logger.error(message)
    elif level == 'debug':
        logger.debug(message) 