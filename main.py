import asyncio
import logging
import sys
import os

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from application.orchestration.AsyncTradingOrchestrator import AsyncTradingOrchestrator

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """
    Main entrypoint for the trading system.
    Initializes and runs the orchestrator.
    """
    logger.info("Initializing trading system...")
    orchestrator = AsyncTradingOrchestrator()

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
    asyncio.run(main())
