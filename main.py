import asyncio
import logging

from BotManager import BotManager
from DBManager import DBManager
from discord_utils.send_webhook_message import (send_status_webhook_message,
                                                send_styled_webhook_message)
from global_state import SharedState
from utils.config_logger import configure_logging
from utils.load_config import load_config

config = load_config("config.json")


async def fetch_and_process_items(bm, dbm, shared_state):
    """Coroutine para buscar e processar itens"""
    while True:
        try:
            result = await bm.scan_items_after_first()
            if result:
                new_items = result.get("new_items", None)
                if new_items and len(new_items) > 0:
                    # add item name to the message
                    message = f"New items found \n"
                    for item in new_items:
                        item_name = item.get("item_name")
                        item_price = item.get("item_price")
                        message += f"{item_name} - ${item_price} \n"

                    send_styled_webhook_message(
                        mention=False,
                        title="New items found! 🎉",
                        color="green",
                        message=message,
                    )

                    repeated_items = result.get("repeated_names_items", [])

                    shared_state.NEW_ITEMS += len(new_items) + len(repeated_items)
                    profitable_items = await dbm.compare_items_prices(
                        items=new_items,
                        repeated_names_items=repeated_items,
                        listing_quantity=2,
                    )
                    
                    print(f"request_login {config["request_login"]} dont_withdrawn: {config["dont_withdrawn"]}")

                    if (
                        config["dont_withdrawn"] == False
                        and config["request_login"] == True
                    ):
                        await bm.withdraw_items(profitable_items)

                    for item in profitable_items:
                        for item in profitable_items:
                            item_name = item.get("item_name")
                            loot_farm_price = item.get("loot_farm_price")
                            average_price = item.get("average_price")

                            file = open("logs/profitable_items.txt", "a")
                            file.write(
                                f"item: {item_name} \n Loot.Farm: {loot_farm_price}\n Backpack.TF (Avg of top 3): {average_price} \n ------------------------------------ \n"
                            )

            bm.refresh_inventory()
        except Exception as e:
            shared_state.debug_error(e, locals())
            send_styled_webhook_message(
                mention=False,
                title="An error occurred!",
                color="red",
                message=f"An error occurred: {e}",
            )


async def fetch_bptf_currency_prices(
    dbm,
    shared_state,
):
    """Coroutine para buscar preços do Backpack.tf a cada 1 hora"""
    while True:
        response = await dbm.currencies_get_backpacktf()
        if response:
            shared_state.KEY_TO_REFINED_SELL_BPTF = response.get("sell").get("key")
            shared_state.KEY_TO_REFINED_BUY_BPTF = response.get("buy").get("key")
            shared_state.REFINED_TO_USD_SELL_BPTF = response.get("sell").get("metal")
            shared_state.REFINED_TO_USD_BUY_BPTF = response.get("buy").get("metal")
        else:
            try:
                sell_key = dbm.currencies_get_newest_value(
                    origin="Backpack.TF",
                    intent="sell",
                )
                buy_key = dbm.currencies_get_newest_value(
                    origin="Backpack.TF",
                    intent="buy",
                )
                refined_to_usd_sell = dbm.currencies_get_newest_value(
                    origin="Backpack.TF",
                    intent="sell",
                    name="Refined Metal",
                    currency="usd",
                )
                refined_to_usd_buy = dbm.currencies_get_newest_value(
                    origin="Backpack.TF",
                    intent="buy",
                    name="Refined Metal",
                    currency="usd",
                )
                shared_state.KEY_TO_REFINED_SELL_BPTF = sell_key
                shared_state.KEY_TO_REFINED_BUY_BPTF = buy_key
                shared_state.REFINED_TO_USD_SELL_BPTF = refined_to_usd_sell
                shared_state.REFINED_TO_USD_BUY_BPTF = refined_to_usd_buy
            except Exception as e:
                print(e)
        await asyncio.sleep(3600)


async def fetch_autobot_currency_prices(dbm, shared_state):
    """Coroutine para buscar preços do Autobot.tf a cada 1 hora"""
    while True:
        response = await dbm.currencies_get_autobot()
        if response:
            shared_state.KEY_TO_REFINED_SELL_AUTOBOT = response.get("sell").get("key")
            shared_state.KEY_TO_REFINED_BUY_AUTOBOT = response.get("buy").get("key")
        else:
            try:
                sell_key = dbm.currencies_get_newest_value(
                    origin="Autobot.TF",
                    intent="sell",
                )
                buy_key = dbm.currencies_get_newest_value(
                    origin="Autobot.TF",
                    intent="buy",
                )
                shared_state.KEY_TO_REFINED_SELL_AUTOBOT = sell_key
                shared_state.KEY_TO_REFINED_BUY_AUTOBOT = buy_key
            except Exception as e:
                print(e)
        await asyncio.sleep(3600)


async def bot_send_status_via_discord(shared_state):
    """Coroutine para enviar mensagem de status a cada 1 hora"""
    while True:
        if not config["discord_webhook_url"] or config["discord_webhook_url"] == "":
            print("No webhook url provided, skipping status message")
            break
        # 5 minutos para dar tempo de carregar os dados
        await asyncio.sleep(600)
        send_status_webhook_message(shared_state)
        # await asyncio.sleep(3600)


async def fetch_and_store_tf2_schema(dbm):
    """buscar e armazenar o schema do TF2"""
    await dbm.fetch_tf2_schema()


async def main():
    logger = logging.getLogger(__name__)
    shared_state = SharedState().get_instance()

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

    # steam login and password to login - Not implemented yet do not use! leave empty
    STEAM_LOGIN = ""  # config["steam_login"]
    STEAM_PASSWORD = ""  # config["steam_password"]

    REQUEST_LOGIN = config["request_login"]

    # Configure logging
    configure_logging(PRINT_EVENTS)

    # Initialize bot manager
    bm = BotManager(
        bptf_token=BPTF_TOKEN,
        ignored_items=IGNORED_ITEMS,
        steam_username=STEAM_LOGIN,
        steam_password=STEAM_PASSWORD,
        request_login=REQUEST_LOGIN,
    )

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

    # Start the bot
    await dbm.create_tables()  # Create database tables
    start_status = await bm.start()  # Start the bot

    if not start_status:
        logger.error("Failed to start the bot")
        return

    await fetch_and_store_tf2_schema(dbm),  # Fetch and store the TF2 schema

    # Start coroutines
    await asyncio.gather(
        # Fetch Backpack.tf currency prices
        fetch_bptf_currency_prices(dbm, shared_state),
        # Fetch Autobot.tf currency prices
        fetch_autobot_currency_prices(dbm, shared_state),
        # Send status via Discord
        bot_send_status_via_discord(shared_state),
        # Fetch and process items
        fetch_and_process_items(bm, dbm, shared_state),
    )

    logger.warning("Shutting down bot...")


if __name__ == "__main__":
    asyncio.run(main())
