import asyncio
from datetime import datetime
import json
import logging
import sqlite3
from httpx import AsyncClient
import requests
import motor.motor_asyncio
from pymongo.server_api import ServerApi
from static.defindexes import strange_part_defindexes, strange_parts, spells
from discord_utils.send_webhook_message import send_styled_webhook_message
from apis import apis
from global_state import SharedState


class DBManager:
    def __init__(
        self,
        mongo_uri: str,
        database_name: str,
        collection_name: str,
        bptf_token: str,
        bptf_api_key: str,
        profit_threshold: float,
        ignored_items: list[str],
    ):
        # Conexão com o MongoDB
        self.client = motor.motor_asyncio.AsyncIOMotorClient(
            mongo_uri, server_api=ServerApi("1")
        )
        self.database = self.client[database_name]
        self.collection = self.database[collection_name]
        self.http_client = AsyncClient()

        # API key do Backpack.TF
        self.bptf_token = bptf_token
        # Token key do Backpack.TF
        self.bptf_api_key = bptf_api_key
        # Instância do logger
        self.logger = logging.getLogger(__name__)
        self.profit_threshold = profit_threshold
        self.shared_state = SharedState.get_instance()
        self.ignored_items = ignored_items

        # Conexão com o SQLite
        self.conn = sqlite3.connect("main.db")
        self.cursor = self.conn.cursor()

        # Instância da classe de APIs
        self.APImanager = apis(bptf_token=bptf_token, bptf_api_key=bptf_api_key)

    async def create_tables(self):
        self.logger.info("Creating database tables")

        # Criação do banco de dados de preços de moedas
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS currencies_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                price REAL,
                intent TEXT,
                diff REAL,
                currency TEXT,
                fetchedAt TEXT,
                origin TEXT
            )
            """
        )

        # Cria um banco de dados para armazenar as chamadas da API para evitar chamadas excessivas
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS api_call_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT UNIQUE,
                fetchedAt TEXT
            )
            """
        )

        # Criação do banco de dados de inventário do bot da loot.farm
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS loot_farm_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                price REAL,
                have INTEGER,
                max INTEGER,
                rate REAL
            )
            """
        )
        # Criação de índice para o nome do item
        self.cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS loot_farm_inventory_name_index ON loot_farm_inventory (name)
            """
        )

        # Criação do banco de dados de resultados de snapshots
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshot_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                steam_appid INTEGER,
                listings TEXT,
                fetched_at TEXT
            )
            """
        )

        # Index para as snapshots
        self.cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS snapshot_results_name_index ON snapshot_results (name)
            """
        )

        # defindexes
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tf2_items_defindex (
                item_name TEXT UNIQUE,
                value INTEGER UNIQUE
            )
            """
        )

        # qualities
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tf2_items_qualities (
                item_name TEXT UNIQUE,
                value INTEGER UNIQUE
            )
            """
        )

        # killstreaks

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tf2_items_killstreaks (
                item_name TEXT UNIQUE,
                value INTEGER UNIQUE
            )
            """
        )

        # effects
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tf2_items_effects (
                item_name TEXT UNIQUE,
                value INTEGER UNIQUE
            )
            """
        )

        # paintkits
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tf2_items_paintkits (
                item_name TEXT UNIQUE,
                value INTEGER UNIQUE
            )
            """
        )

        # wear
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tf2_items_wears (
                item_name TEXT UNIQUE,
                value INTEGER UNIQUE
            )
            """
        )

        # createseries
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tf2_items_createseries (
                item_name TEXT UNIQUE,
                value INTEGER UNIQUE
            )
            """
        )

        # paints
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tf2_items_paints (
                item_name TEXT UNIQUE,
                value INTEGER UNIQUE
            )
            """
        )

        # strange parts
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tf2_items_strange_parts (
                item_name TEXT UNIQUE,
                value TEXT UNIQUE
            )
            """
        )

        # uncraftable weapons
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tf2_items_uncraft_weapons (
                item_value text UNIQUE
            )
            """
        )

        self.conn.commit()

    def insert_currency_price(
        self,
        price,
        intent,
        diff,
        origin,
        name,
        fetched_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        currency="usd",
    ):
        self.cursor.execute(
            "INSERT INTO currencies_prices (price, intent, diff, currency, fetchedAt, origin, name) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (price, intent, diff, currency, fetched_at, origin, name),
        )
        self.conn.commit()

    async def insert_item(self, name, price, have, max_qty, rate) -> None:
        self.cursor.execute(
            "INSERT INTO loot_farm_inventory (name, price, have, max, rate) VALUES (?, ?, ?, ?, ?)",
            (name, price, have, max_qty, rate),
        )
        self.conn.commit()

    async def store_loot_farm_api(self, items):
        self.cursor.execute("DELETE FROM loot_farm_inventory")
        self.conn.commit()
        self.logger.info("Deleted old loot_farm_inventory table")

        for item in items:
            itemPrice = item["price"] * 0.01
            item_name = item["name"]
            item_have = item["have"]
            item_max = item["max"]

            if item_name in self.ignored_items:
                continue

            if item_have == 0 or item_max == 0 or item_have == item_max:
                continue

            await self.insert_item(
                name=item_name,
                price=itemPrice,
                have=item_have,
                rate=item["rate"],
                max_qty=item_max,
            )

    async def fetch_and_store_loot_farm_api(self, game) -> None:
        try:
            if not self.should_make_api_call(
                f"loot-farm-{game}", cache_duration_hours=1
            ):
                raise Exception("Not making API call, cache is still valid")

            response = await self.APImanager.lootfarm_getitems(game=game)
            if response:
                self.log_api_call(f"loot-farm-{game}")
                await self.store_loot_farm_api(response)
                self.logger.info("Fetched and stored items from loot farm API")
            else:
                raise Exception("Failed to fetch loot farm API")
        except Exception as e:
            self.logger.error(str(e))

    async def comprate_prices_from_all_lootfarm_items(self):
        # pegar todos os items que tiver o have > 0
        # self.cursor.execute("SELECT name, price FROM loot_farm_inventory")
        self.cursor.execute(
            "SELECT name, price, have, max, rate FROM loot_farm_inventory WHERE have > 0 AND max != have"
        )
        items = self.cursor.fetchall()
        total_items_processed = 0

        for item in items:
            item_name = item[0]
            item_price = item[1]
            item_have = item[2]
            item_max = item[3]
            item_rate = item[4]

            # Adapt item-names for the snapshot API if necessary
            if item_name.startswith("Unusual"):
                # this function ignores unusual effects because the api does not say the effect
                continue
            elif (
                item_name.startswith(
                    ("Professional Killstreak", "Killstreak", "Specialized Killstreak")
                )
                and item_name.endswith("Kit")
            ) or item_name.endswith("Unusualifier"):
                item_name = f"Non-Craftable {item_name}"
                self.logger.warning(f"New item name: {item_name}")
            elif " Series" in item_name:
                item_name = item_name.replace(" Series", "")
                self.logger.warning(f"New item name: {item_name}")
            # convert # to %23
            elif "#" in item_name:
                item_name = item_name.replace("#", "%23")
                self.logger.warning(f"New item name: {item_name}")

            try:
                snapshot_listings = await self.fetch_item_snapshot_with_cache(item_name)
                if not snapshot_listings:
                    raise ValueError(
                        f"Item '{item_name}' not found in Backpack.TF or no listings found"
                    )

                # sort listings by price
                snapshot_listings.sort(key=lambda x: x["price"])
                top_listings = snapshot_listings[:3]

                # Calculate the average price from the top listings using usd_estimated
                average_price = sum(
                    [listing["usd_estimated"] for listing in top_listings]
                ) / len(top_listings)

                # Check for profitability
                if item_price + self.profit_threshold < average_price:
                    # write profieble item in a file
                    file = open("logs/profitable_items.txt", "a")
                    file.write(
                        f"item: {item_name} \n Loot.Farm: {item_price}\n Backpack.TF (Avg of top 3): {average_price} \n item_Rate: {item_rate} \n ------------------------------------ \n"
                    )
                    self.logger.info(f"Profitable item found: {item_name}")

            except (ValueError, KeyError, requests.exceptions.RequestException) as e:
                self.logger.error(f"Error processing item '{item_name}': {e}")
                self.shared_state.debug_error(
                    error=e,
                    other_vars={
                        "item_name": item_name,
                        "item_price": item_price,
                        "snapshot_listings": snapshot_listings,
                    },
                )
            finally:
                time_left = len(items) - total_items_processed
                self.logger.info(
                    f"Processed {total_items_processed}/{len(items)} items | time left: {round(time_left / 60)} minutes and {round(time_left % 60)} seconds"
                )
                total_items_processed += 1
                await asyncio.sleep(1)

    def currencies_get_newest_value(
        self,
        origin="Backpack.TF",
        name="Mann Co. Supply Crate Key",
        currency="metal",
        intent="buy",
    ) -> float:
        """
        Get the value of the newest item from the currencies_prices table
        default values are for the Mann Co. Supply Crate Key from Backpack.TF in metal
        """
        try:
            # pegar o com o fetchAt mais recente contendo o nome, a origem e a moeda
            self.cursor.execute(
                "SELECT price FROM currencies_prices WHERE name = ? AND origin = ? AND currency = ? AND intent = ? ORDER BY fetchedAt DESC LIMIT 1",
                (name, origin, currency, intent),
            )
            key_value = self.cursor.fetchone()

            if not key_value:
                self.logger.error(
                    "Failed to fetch the newest item value from currencies_prices"
                )
                return None

            return key_value[0]

        except Exception as e:
            self.logger.error(
                "Failed to fetch the newest item value from currencies_prices" + str(e),
                exc_info=True,
            )
            return None

    async def currencies_get_backpacktf(self):
        self.logger.info("Fetching backpack.tf currency prices")

        if not self.should_make_api_call("backpack-currencies", cache_duration_hours=1):
            return None

        try:
            response = await self.APImanager.backpacktf_get_currencies()
            origin = "Backpack.TF"

            if not response:
                raise Exception("Failed to fetch key price")

            # Inserir preço de venda da chave
            self.insert_currency_price(
                name="Mann Co. Supply Crate Key",  # name
                price=response["keys"]["price"]["value"],  # sellPrice
                intent="sell",  # intent
                diff=response["keys"]["price"]["difference"],  # diff
                currency=response["keys"]["price"]["currency"],  # currency
                origin=origin,  # origin
            )
            self.insert_currency_price(
                name="Mann Co. Supply Crate Key",  # name
                price=response["keys"]["price"]["value_high"],  # buyPrice
                intent="buy",  # intent
                diff=response["keys"]["price"]["difference"],  # diff
                currency=response["keys"]["price"]["currency"],  # currency
                origin=origin,  # origin
            )

            # Inserir preço de venda do metal
            self.insert_currency_price(
                name="Refined Metal",  # name
                price=response["metal"]["price"]["value"],  # sellPrice
                intent="sell",  # intent
                diff=response["metal"]["price"]["difference"],  # diff
                currency=response["metal"]["price"]["currency"],  # currency
                origin=origin,  # origin
            )
            # Inserir preço de compra do metal
            self.insert_currency_price(
                name="Refined Metal",  # name
                price=response["metal"]["price"]["value"],  # buyPrice
                intent="buy",  # intent
                diff=response["metal"]["price"]["difference"],  # diff
                currency=response["metal"]["price"]["currency"],  # currency
                origin=origin,  # origin
            )

            self.log_api_call("backpack-currencies")

            return {
                "sell": {
                    "metal": response["metal"]["price"]["value"],
                    "key": response["keys"]["price"]["value"],
                },
                "buy": {
                    "metal": response["metal"]["price"]["value"],
                    "key": response["keys"]["price"]["value"],
                },
            }

        except Exception as e:
            self.logger.error(
                "Failed to fetch and store key price" + str(e), exc_info=True
            )

    async def currencies_get_autobot(self):
        # "5002;6",  # Refined Metal
        # "5021;6",  # Mann Co. Supply Crate Key
        origin = "Autobot.TF"
        self.logger.info("Fetching autobot.tf currency prices")
        if self.should_make_api_call("autobot-currencies", cache_duration_hours=1):
            try:
                key_response = await self.APImanager.autobot_get_item_price_sku(
                    item_sku="5021;6"
                )
                try:
                    last_key_autobot_sell_price = self.currencies_get_newest_value(
                        origin=origin,
                        name="Mann Co. Supply Crate Key",
                        currency="metal",
                        intent="sell",
                    )
                    last_key_autobot_buy_price = self.currencies_get_newest_value(
                        origin=origin,
                        name="Mann Co. Supply Crate Key",
                        currency="metal",
                        intent="buy",
                    )
                    sell_diff = float(key_response["sell"]["metal"]) - float(
                        last_key_autobot_sell_price
                    )
                    buy_diff = float(key_response["buy"]["metal"]) - float(
                        last_key_autobot_buy_price
                    )
                except Exception:
                    sell_diff = 0
                    buy_diff = 0

                if not key_response:
                    raise Exception("Failed to fetch key price")
                self.insert_currency_price(
                    name="Mann Co. Supply Crate Key",  # name
                    price=key_response["sell"]["metal"],  # sellPrice
                    intent="sell",  # intent
                    diff=sell_diff,  # diff
                    currency="metal",  # currency
                    origin=origin,  # origin
                )
                self.insert_currency_price(
                    name="Mann Co. Supply Crate Key",  # name
                    price=key_response["buy"]["metal"],  # buyPrice
                    intent="buy",  # intent
                    diff=buy_diff,  # diff
                    currency="metal",  # currency
                    origin=origin,  # origin
                )

                self.log_api_call("autobot-currencies")

                return {
                    "sell": {
                        "key": key_response["sell"]["metal"],
                    },
                    "buy": {
                        "key": key_response["buy"]["metal"],
                    },
                }
            except Exception as e:
                self.logger.error(
                    "Failed to fetch and store key price" + str(e), exc_info=True
                )
                return None
        else:
            return None

    async def reformat_snapshot(self, payload: dict) -> dict:
        """
        Reformat the Backpack.tf API snapshot response.
        obs: remove listings that are not buy listings and have blacklisted keywords

        Args:
            payload (dict): The Backpack.tf API response payload.

        Returns:
            dict: The reformatted snapshot data.
        """

        if not payload:
            return dict()

        listings = payload.get("listings", [])
        formatted_listings = []

        for listing in listings:
            # Check if the listing is reasonable

            intent = listing.get("intent", "sell")
            only_buyout = listing.get("buyout", True)

            if intent == "sell":
                continue

            # remove listings that are not buyout | Most of the time, the buyout listings are the best ones (bots) while the others are not
            if only_buyout == 0:
                continue

            # remove listings that contains spell attributes
            has_spell_or_strange_part = False
            if "item" in listing and "attributes" in listing["item"]:
                for attribute in listing["item"]["attributes"]:

                    defindex = int(attribute.get("defindex", -1))
                    float_value = float(attribute.get("float_value", -1))
                    # Verifica se é spell
                    if defindex in spells:
                        has_spell_or_strange_part = True
                        break  # Sai do loop se encontrar um spell

                    # Verifica se é strange part
                    if (
                        defindex in strange_part_defindexes
                        and float_value in strange_parts
                    ):
                        has_spell_or_strange_part = True
                        break  # Sai do loop se encontrar uma strange part

            if has_spell_or_strange_part:
                continue

            steamid = listing.get("steamid", 0)
            currencies = listing.get("currencies", {})
            listed_at = listing.get(
                "timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            bumped_at = listing.get("bump", listed_at)
            trade_offers_preferred = listing.get("offers")
            only_buyout = listing.get("buyout", True)
            item = listing.get("item", {})
            price = listing.get("price", None)

            refined_metal_lootfarm_sell_price = (
                self.shared_state.REFINED_TO_USD_SELL_LOOTFARM
            )

            if price is not None and price > 0:
                try:
                    usd_estimated = float(price) * float(
                        refined_metal_lootfarm_sell_price
                    )
                except Exception as e:
                    self.logger.error(f"Failed to calculate USD estimated: {e}")
                    usd_estimated = self.currencies_to_usd(currencies)
            else:
                usd_estimated = self.currencies_to_usd(currencies)

            formatted_listing = {
                "steamid": steamid,
                "currencies": currencies,
                "usd_estimated": usd_estimated,
                "trade_offers_preferred": trade_offers_preferred,
                "bumped_at": bumped_at,
                "intent": intent,
                "only_buyout": only_buyout,
                "price": price,
                "listed_at": listed_at,
                "item": item,
            }
            formatted_listings.append(formatted_listing)

        if len(formatted_listings) == 0:
            return None

        return formatted_listings

    async def fetch_item_snapshot_with_cache(
        self, item_name: str, cache_duration_hours: int = 1
    ) -> list[dict]:
        """
        Fetches item snapshot from Backpack.tf API, caching esults locally for a specified duration.

        Args:
            item_name (str): The name of the item.
            cache_duration_hours (int, optional): Duration in hours to cache results. Defaults to 1.

        Returns:
            dict: Fetched snapshot data or None if an error occurred.
        """
        try:
            # Check last fetch time from the database
            self.cursor.execute(
                "SELECT fetched_at FROM snapshot_results WHERE name = ?", (item_name,)
            )
            result = self.cursor.fetchone()

            if result:
                last_fetched_at = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
                time_difference = datetime.now() - last_fetched_at

                if time_difference.total_seconds() < cache_duration_hours * 3600:
                    self.logger.info(f"Using cached snapshot for {item_name}")
                    # Fetch the listings from the database
                    self.cursor.execute(
                        "SELECT listings FROM snapshot_results WHERE name = ?",
                        (item_name,),
                    )
                    listings_json = self.cursor.fetchone()
                    return json.loads(listings_json[0])  # Return the cached listings
                else:
                    self.logger.info(
                        f"Cache expired for {item_name}, time dif: {time_difference.total_seconds()}"
                    )
            else:
                self.logger.info(
                    f"No cached data found for {item_name}, result: {str(result)}"
                )
        except Exception as e:
            self.logger.info(
                f"Failed to fetch item snapshot in database for {item_name}, time dif: {time_difference.total_seconds()}"
            )
            # write file with error
            file = open("fetch_item_snapshot_with_cache_error.txt", "a")
            file.write(
                f"Failed to fetch item snapshot in database for {item_name}, time dif: {time_difference.total_seconds()}\nresult: {str(result)} \n {str(e)} \n ------------------------------------ \n"
            )

        if not self.shared_state.should_make_snapshot_request():
            self.logger.warning(
                "Exceeded the maximum number of snapshot requests for this minute (60) and the cache is expired, skipping."
            )
            return None

        # If no cached data or cache expired, fetch from API
        snapshot = await self.APImanager.backpacktf_get_item_snapshot(
            item_name=item_name
        )

        if not snapshot:
            self.logger.error(f"Failed to fetch snapshot for {item_name}")
            return None

        formatted_snapshot = await self.reformat_snapshot(snapshot)

        if formatted_snapshot:
            listings_json = json.dumps(formatted_snapshot)
            self.logger.info(f"Storing snapshot for {item_name} in the database")
            fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            steam_appid = 440
            self.cursor.execute(
                """
                INSERT OR REPLACE INTO snapshot_results (name, steam_appid, listings, fetched_at) 
                VALUES (?, ?, ?, ?)
                """,
                (
                    item_name,
                    steam_appid,
                    listings_json,
                    fetched_at,
                ),
            )
            self.conn.commit()
        else:
            self.logger.warning(
                f"Empty snapshot for {item_name}. Not storing in the database."
            )

        return formatted_snapshot

    def currencies_to_usd(self, currencies: dict) -> float:
        """
        Converts a dictionary of currencies (metal, keys) to USD value.

        Args:
            currencies (dict): A dictionary containing 'metal' and/or 'keys' amounts.

        Returns:
            float: The total USD value of the currencies.
        """

        key_value_in_usd = self.shared_state.KEY_TO_USD_SELL_LOOTFARM
        refined_sell_value_in_usd = self.shared_state.REFINED_TO_USD_SELL_LOOTFARM

        key_value = float(currencies.get("keys", 0.0))
        refined_value = float(currencies.get("metal", 0.0))

        if key_value_in_usd <= 0 or refined_sell_value_in_usd <= 0:
            self.logger.error("Failed to fetch currency values")
            return

        total_usd = (
            key_value * key_value_in_usd + refined_value * refined_sell_value_in_usd
        )

        return total_usd

    async def compare_items_prices(
        self,
        items: list,
        repeated_names_items: list,
        listing_quantity: int = 3,
        delay_between_requests: int = 0,
    ) -> list:
        """
        Compares the prices of items recieved with the average prices from Backpack.tf snapshots.

        Args:
            items (list): A list of items to compare.
            repeated_names_items (list): A list of items that have repeated names.
            listing_quantity (int, optional): The number of listings to consider. Defaults

        Returns:
            list: A list of profitable items.
        """
        profitable_items = []
        self.logger.info("Comparing item prices")
        for item in items:
            self.logger.info(f"Checking item '{item['item_name']}' for profitability")
            item_name = item["item_name"]
            item_id = item["item_id"]
            item_loot_farm_price = float(item["item_price"])
            item_attachments = item["item_attachments"]

            if (
                item_loot_farm_price > self.shared_state.MAX_ITEM_PRICE
                and self.shared_state.MAX_ITEM_PRICE > 0
            ) or item_loot_farm_price > self.shared_state.REMAINING_MONEY:
                self.logger.warning(f"Item '{item_name}' is too expensive, skipping")
                continue

            unusual_effect_id = await self.get_dafindex_from_tf2_item_table(
                item_attachments, "tf2_items_effects"
            )

            # Adapt item-names for the snapshot API if necessary
            if (
                item_name.startswith(
                    ("Professional Killstreak", "Killstreak", "Specialized Killstreak")
                )
                and item_name.endswith("Kit")
            ) or item_name.endswith("Unusualifier"):
                item_name = f"Non-Craftable {item_name}"
                self.logger.warning(f"New item name: {item_name}")
            elif " Series" in item_name:
                item_name = item_name.replace(" Series", "")
                self.logger.warning(f"New item name: {item_name}")
            elif unusual_effect_id:
                self.logger.warning(
                    f"unusual_effect_id for item '{item_name}' with unusual effect"
                )
                item_name = item_name.replace("Unusual", unusual_effect_id["name"])
                self.logger.warning(f"New item name: {item_name}")
            # convert # to %23
            elif "#" in item_name:
                item_name = item_name.replace("#", "%23")
                self.logger.warning(f"New item name: {item_name}")

            try:
                snapshot_listings = await self.fetch_item_snapshot_with_cache(item_name)

                if not snapshot_listings:
                    raise ValueError(
                        f"Item '{item_name}' not found in Backpack.TF or no listings found"
                    )

                # sort listings by price
                snapshot_listings.sort(key=lambda x: x["price"])

                top_listings = snapshot_listings[:listing_quantity]

                # Calculate the average price from the top listings using usd_estimated
                average_price = sum(
                    [listing["usd_estimated"] for listing in top_listings]
                ) / len(top_listings)

                # Check for profitability
                if item_loot_farm_price + self.profit_threshold < average_price:
                    send_styled_webhook_message(
                        message=f"item: {item_name} \n Loot.Farm: {item_loot_farm_price}\n Backpack.TF (Avg of top 3): {average_price}",
                        title="🎉 Profitable item found 🎉",
                    )

                    if item_name in repeated_names_items:
                        profitable_items.append(
                            {
                                "item_id": item_id,
                                "name": item_name,
                                "loot_farm_price": item_loot_farm_price,
                                "average_price": average_price,
                            }
                        )

                    profitable_items.append(
                        {
                            "item_id": item_id,
                            "name": item_name,
                            "loot_farm_price": item_loot_farm_price,
                            "average_price": average_price,
                        }
                    )

                    self.logger.info(
                        f"Item '{item_name}' is profitable: Loot.Farm: {item_loot_farm_price}, "
                        f"Backpack.tf (Avg of top 3): {average_price}"
                    )

            except (ValueError, KeyError, requests.exceptions.RequestException) as e:
                self.logger.error(f"Error processing item '{item_name}': {e}")
                self.shared_state.debug_error(
                    error=e,
                    other_vars={
                        "item_name": item_name,
                        "unusual_effect_id": unusual_effect_id,
                        "item_attachments": item_attachments,
                        "item": item,
                        "loot_farm_price": item_loot_farm_price,
                        "snapshot_listings": snapshot_listings,
                    },
                )
            finally:
                await asyncio.sleep(delay_between_requests)

        self.logger.info(f"Found {len(profitable_items)} profitable items")
        return profitable_items

    def should_make_api_call(self, endpoint, cache_duration_hours=24):
        """
        Verifica se é necessário fazer uma chamada de API com base no histórico de chamadas.

        Args:
            endpoint (str): O endpoint da API a ser verificado.
            cache_duration_hours (int, optional): A duração do cache em horas. Padrão é 24 horas.

        Returns:
            bool: True se a chamada deve ser feita, False caso contrário.
        """

        # Verifica a última chamada para esse tipo de API
        self.cursor.execute(
            "SELECT fetchedAt FROM api_call_log WHERE endpoint = ? ORDER BY fetchedAt DESC LIMIT 1",
            (endpoint,),
        )
        try:
            result = self.cursor.fetchone()
        except Exception as e:
            self.logger.error(
                f"Failed to fetch last API call timestamp for {endpoint}: {e}"
            )
            return True

        if result:
            last_call_timestamp = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
            time_difference = datetime.now() - last_call_timestamp
            if time_difference.total_seconds() < cache_duration_hours * 3600:
                self.logger.info(f"Using cached data for {endpoint}")
                return False

        return True

    def log_api_call(self, endpoint):
        """
        Registra uma chamada de API no banco de dados.

        Args:
            endpoint (str): O endpoint da API chamado.
        """

        fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(
            "INSERT OR REPLACE INTO api_call_log (endpoint, fetchedAt) VALUES (?, ?)",
            (endpoint, fetched_at),
        )
        self.conn.commit()

    async def fetch_tf2_schema(self):
        """
        Fetches various TF2 schema data from the Backpack.tf API and stores it in the database.
        """

        api_calls = {
            "defindex": self.APImanager.schema_get_items_defindexes,
            "qualities": self.APImanager.schema_get_items_qualities,
            "killstreaks": self.APImanager.schema_get_items_killstreaks,
            "effects": self.APImanager.schema_get_items_effects,
            "paintkits": self.APImanager.schema_get_items_paintkits,
            "wears": self.APImanager.schema_get_items_wears,
            "crateseries": self.APImanager.schema_get_items_createseries,
            "paints": self.APImanager.schema_get_items_paints,
            "strange_parts": self.APImanager.schema_get_items_strangeParts,
            "uncraft_weapons": self.APImanager.schema_get_items_uncraftables,
        }

        for endpoint, api_call in api_calls.items():
            if self.should_make_api_call(
                endpoint=endpoint,
                cache_duration_hours=24 * 7,  # 1 semana
            ):  # Verifica se a chamada é necessária
                try:
                    response = await api_call()
                    if response:
                        # Adapta o armazenamento dos dados de acordo com o tipo de resposta
                        if endpoint in [
                            "defindex",
                            "qualities",
                            "effects",
                            "paintkits",
                            "paints",
                        ]:
                            # Para dicionários simples: chave -> valor
                            for key, value in response.items():
                                self.store_schema_data(endpoint, key, value)
                        elif endpoint == "killstreaks" or endpoint == "wears":
                            # Para dicionários com valores e nomes
                            for key, value in response.items():
                                if isinstance(
                                    value, dict
                                ):  # Lidar com o caso do "wears"
                                    for name, num_value in value.items():
                                        self.store_schema_data(
                                            endpoint, name, num_value
                                        )
                                else:
                                    self.store_schema_data(endpoint, key, value)
                        elif endpoint == "strange_parts":
                            # Para dicionários com descrições e valores
                            for description, value in response.items():
                                self.store_schema_data(endpoint, description, value)
                        elif endpoint == "uncraft_weapons":
                            # Para listas de valores
                            for value in response:
                                self.store_schema_data(
                                    endpoint, value, None
                                )  # Valor nulo para o segundo campo

                        self.log_api_call(endpoint)  # Registra a chamada
                        self.logger.info(f"Fetched TF2 {endpoint} data")
                    else:
                        self.logger.error(f"Failed to fetch TF2 {endpoint} data")
                except Exception as e:
                    self.logger.error(f"Failed to fetch TF2 {endpoint} data: {e}")

    def store_schema_data(self, endpoint, key, value):
        """
        Armazena os dados do esquema TF2 no banco de dados SQLite.

        Args:
            endpoint (str): O tipo de dados do esquema (por exemplo, 'defindexes', 'qualities').
            key (str ou int): A chave ou nome do item.
            value (int ou str ou None): O valor ou descrição correspondente à chave.
        """
        table_name = f"tf2_items_{endpoint}"

        # Adapta a consulta SQL de acordo com o tipo de dados
        if value is None:
            self.cursor.execute(
                f"INSERT OR IGNORE INTO {table_name} (item_value) VALUES (?)", (key,)
            )
        else:
            self.cursor.execute(
                f"INSERT OR IGNORE INTO {table_name} (item_name, value) VALUES (?, ?)",
                (key, value),
            )

        self.conn.commit()

    async def get_dafindex_from_tf2_item_table(self, search_values, table_name):
        """
        Fetches the defindex of a TF2 item from the specified table.

        Args:
            search_values (array): The item attributes to search in the table.
            table_name (str): The name of the table to search.

        Returns:
            int: The defindex of the item or None if not found.

            OBS: retorna o primeiro valor encontrado
        """

        if not search_values:
            return None

        for search_value in search_values:
            self.cursor.execute(
                f"SELECT value FROM {table_name} WHERE item_name = ?", (search_value,)
            )
            result = self.cursor.fetchone()

            if result:
                return {"name": search_value, "value": result[0]}  # Return the defindex

        return None
