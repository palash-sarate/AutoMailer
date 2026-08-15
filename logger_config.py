import logging
import os
import sys

# Detect if running as packaged PyInstaller executable or in local development
IS_FROZEN = getattr(sys, "frozen", False)
LOG_FILE_PATH = os.path.join(os.getcwd(), "automailer.log")


def get_logger(name: str = "AutoMailer") -> logging.Logger:
    """Configures and returns a structured logger with standardized level formats.
    
    Logs are written to 'automailer.log' and standard console output only in local dev mode.
    When running as a frozen executable, logging is minimal and does not spam unnecessary disk writes.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.DEBUG if not IS_FROZEN else logging.WARNING)

        # Standard structured format recognized by colorized log viewers
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # 1. Console Output Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.DEBUG if not IS_FROZEN else logging.WARNING)
        logger.addHandler(console_handler)

        # 2. File Output Handler (Only enabled in local development mode)
        if not IS_FROZEN:
            try:
                file_handler = logging.FileHandler(LOG_FILE_PATH, mode="a", encoding="utf-8")
                file_handler.setFormatter(formatter)
                file_handler.setLevel(logging.DEBUG)
                logger.addHandler(file_handler)
                logger.debug("--- AutoMailer Development Session Started ---")
            except Exception as e:
                print(f"[Warning] Failed to initialize file logger at {LOG_FILE_PATH}: {e}")

    return logger
