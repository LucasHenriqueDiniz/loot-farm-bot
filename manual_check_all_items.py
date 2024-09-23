import asyncio
import logging

from DBManager import DBManager
from global_state import SharedState
from utils.config_logger import configure_logging
from utils.load_config import load_config

config = load_config("config.json")


async def main():
    logger = logging.getLogger(__name__)

    # mongo uri
    MANGO_URI = config["mongo_uri"]
    # mango database name
    DATABASE_NAME = config["database_name"]
    # mango collection name
    COLLECTION_NAME = config["collection_name"]

    # ignored items will not be checked for profit
    IGNORED_ITEMS = config["ignored_items"]

    # backpack.tf token
    BPTF_TOKEN = config["bptf_token"]
    # bprf api key
    BPTF_API_KEY = config["bptf_api_key"]

    # print events in console | 0 - Critical | 1 - Error | 2 - Warning | 3 - Info | 4 - Debug
    PRINT_EVENTS = config["print_events"]

    # profit threshold in usd (0.01 = 1 cent) the bot will use to determine if an item is profitable (lootfarm + threshold < bptf sum)
    PROFIT_THRESHOLD = config["profit_threshold"]

    # Configure logging
    configure_logging(PRINT_EVENTS)

    # Initialize db manager
    dbm = DBManager(
        mongo_uri=MANGO_URI,
        database_name=DATABASE_NAME,
        collection_name=COLLECTION_NAME,
        bptf_token=BPTF_TOKEN,
        bptf_api_key=BPTF_API_KEY,
        profit_threshold=PROFIT_THRESHOLD,
        ignored_items=IGNORED_ITEMS,
    )
    await dbm.create_tables()  # Create database tables
    await dbm.fetch_and_store_loot_farm_api(game="TF2")
    await dbm.comprate_prices_from_all_lootfarm_items()

    logger.warning("Ended main coroutine")


if __name__ == "__main__":
    asyncio.run(main())
