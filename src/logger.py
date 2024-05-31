import logging
import os

logger = logging.getLogger()
log_level = logging.CRITICAL if os.getenv("TEST") else logging.INFO
logger.setLevel(log_level)
