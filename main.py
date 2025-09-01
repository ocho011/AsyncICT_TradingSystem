import asyncio
import logging
import logging.config
import logging.handlers
import sys
import os
import configparser

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from application.orchestration.AsyncTradingOrchestrator import AsyncTradingOrchestrator

def setup_logging(config_path='config.ini'):
    """Sets up logging based on the configuration file."""
    config = configparser.ConfigParser()
    config.read(config_path)

    log_level = config.get('logging', 'level', fallback='INFO')
    log_dir = config.get('logging', 'directory', fallback='logs')
    log_filename = config.get('logging', 'filename', fallback='trading_system.log')
    max_bytes = config.getint('logging', 'max_bytes', fallback=5*1024*1024)
    backup_count = config.getint('logging', 'backup_count', fallback=5)

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file_path = os.path.join(log_dir, log_filename)

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Remove existing handlers to avoid duplication
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create console handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # Create rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        log_file_path, maxBytes=max_bytes, backupCount=backup_count
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Get the logger for the current module
    module_logger = logging.getLogger(__name__)
    module_logger.info("Logging configured from %s", config_path)
    return module_logger

async def main(logger):
    """
    Main entrypoint for the trading system.
    Initializes and runs the orchestrator.
    """
    logger.info("Initializing trading system...")
    # Pass the config file path to the orchestrator
    orchestrator = AsyncTradingOrchestrator(config_path='config.ini')

    try:
        await orchestrator.start_trading_system()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down...")
    except Exception as e:
        logger.error(f"An unexpected error occurred in main: {e}", exc_info=True)
    finally:
        await orchestrator.shutdown()
        logger.info("System has been shut down.")

if __name__ == "__main__":
    # To run the system, execute this file from the project root:
    # python main.py
    
    # Setup logging and get a logger for this module
    logger = setup_logging(config_path='config.ini')
    
    try:
        asyncio.run(main(logger))
    except Exception as e:
        logger.critical(f"Failed to run the application: {e}", exc_info=True)
        sys.exit(1)
