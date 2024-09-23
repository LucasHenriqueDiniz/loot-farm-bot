import json
import logging
import time
import urllib.parse
from asyncio import sleep

from httpx import AsyncClient

with open("./static/stn_schema.json", "r") as f:
    stn_schema = json.load(f)


class apis:
    # Documentation for the backpack.tf API https://backpack.tf/api/index.html#/
    def __init__(
        self,
        bptf_token: str,
        bptf_api_key: str,
    ):
        self.api_key = bptf_api_key
        self.token = bptf_token
        self.standard_params = {
            "appid": "440",
            "key": self.api_key,
            "token": self.api_key,
        }
        self.http_client = AsyncClient()
        self.default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        self.logger = logging.getLogger(__name__)
        self.last_snapshot_time = -1

    #
    # Backpack.tf APIs
    #

    async def backpacktf_get_currencies(self):
        currencies = await self.http_client.get(
            "https://backpack.tf/api/IGetCurrencies/v1?key=" + self.api_key
        )

        jsondata = json.loads(currencies.text)

        if jsondata["response"]["success"] == 1:
            return jsondata["response"]["currencies"]
        else:
            raise Exception("Your API key is invalid")

    async def backpacktf_item_price(self, **kwargs):
        kwargs.update(self.standard_params)
        encoded = urllib.parse.urlencode(kwargs)
        r = await self.http_client.get(
            "https://backpack.tf/api/IGetPriceHistory/v1?" + encoded
        )
        jsondata = json.loads(r.text)

        if jsondata["response"]["success"] == 1:
            return jsondata
        else:
            raise Exception("Your API key is invalid")

    async def backpacktf_get_item_snapshot(self, item_name: str) -> dict:
        """
        Fetches item snapshot from Backpack.tf API.

        Args:
            item_name (str): The name of the item.

        Returns:
            dict: Fetched snapshot data or None if an error occurred.
        """

        try:
            # Build the request URL
            snap_request = await self.http_client.get(
                "https://backpack.tf/api/classifieds/listings/snapshot",
                params={"token": self.token, "sku": item_name, "appid": "440"},
                headers=self.default_headers,
            )
            self.logger.debug(
                f"URL: {snap_request.url}, Status Code: {snap_request.status_code}"
            )

            # write the request in a file to debug
            with open("logs/snapshot_request.txt", "a") as f:
                f.write(
                    f"Status Code: {snap_request.status_code} | item_name: {item_name}, URL: {snap_request.url}\n"
                )

            if snap_request.status_code != 200:
                self.logger.info(
                    f"Failed to fetch snapshot for {item_name}, response: {snap_request.status_code}"
                )
                if snap_request.status_code == 429:
                    self.logger.info(
                        f"Rate limited to get snapshot for {item_name} url: {snap_request.url}"
                    )
                    await sleep(5)
                return None

            snapshot = snap_request.json()
            self.logger.info(f"Snapshot for {item_name} fetched successfully")

            if not snapshot:
                self.logger.error(f"Failed to fetch snapshot for {item_name}")
                return None

            return snapshot
        except Exception as e:
            self.logger.error(f"Failed to fetch snapshot for {item_name}: {e}")
            return None

    #
    # Autobot.tf APIs
    #

    async def autobot_transform_item_name_to_sku(self, item: str) -> str:
        """
        Transforms an item name to its corresponding SKU using stn_schema.json or Autobot.tf API.

        Args:
            item (str): The name of the item.

        Returns:
            str or None: The SKU of the item, or None if not found.
        """

        sku = next((sku for sku, name in stn_schema.items() if name == item), None)

        if sku:
            return sku

        self.logger.debug(
            f"Item name '{item}' not found in stn_schema, using Autobot.tf API"
        )

        item_sku_request = await self.http_client.get(
            f"https://schema.autobot.tf/getSku/fromName/{item}",
            headers=self.default_headers,
        )

        item_sku = item_sku_request.json()

        if item_sku["success"] == False:
            return None

        # Add the item to the stn_schema
        stn_schema[item_sku["sku"]] = item

        return item_sku["sku"]

    async def autobot_transform_sku_to_item_name(self, sku: str) -> str:
        """
        Transforms an SKU to its corresponding item name using stn_schema.json or Autobot.tf API.

        Args:
            sku (str): The SKU of the item.

        Returns:
            str or None: The name of the item, or None if not found.
        """
        # Check if the SKU exists in stn_schema
        name = stn_schema.get(sku)

        if name:
            return name

        item_name_request = await self.http_client.get(
            f"https://schema.autobot.tf/getName/fromSku/{sku}",
            headers=self.default_headers,
        )

        item_name = item_name_request.json()

        if item_name["success"] == False:
            return None

        # Add the item to the stn_schema
        stn_schema[sku] = item_name["name"]

        return item_name["name"]

    async def autobot_get_item_price_sku(self, item_sku):
        item_price_request = await self.http_client.get(
            f"https://autobot.tf/json/items/{item_sku}",
            headers=self.default_headers,
        )

        item_price = item_price_request.json()

        if item_price["success"] == False:
            return None

        # Update stn_schema with the new mapping
        stn_schema[item_sku] = item_price["name"]

        return item_price

    async def autobot_get_item_price_itemname(self, item: str):
        item_sku = await self.autobot_transform_item_name_to_sku(item)

        if item_sku is None:
            return None

        item_price_request = await self.http_client.get(
            f"https://autobot.tf/json/items/{item_sku}",
            headers=self.default_headers,
        )

        item_price = item_price_request.json()

        if item_price["success"] == False:
            return None

        return item_price

    #
    # LootFarm APIs
    #

    async def lootfarm_getitems(self, game: str):
        LOOTFARM_ALL_TF2_ITEMS_URL = "https://loot.farm/fullpriceTF2.json"
        LOOTFARM_ALL_CSGO_ITEMS_URL = "https://loot.farm/fullprice.json"
        LOOTFARM_ALL_DOTA_ITEMS_URL = "https://loot.farm/fullpriceDota.json"
        LOOTFARM_ALL_RUST_ITEMS_URL = "https://loot.farm/fullpriceRust.json"

        self.logger.debug("Fetching loot farm API for " + game)
        switcher = {
            "TF2": LOOTFARM_ALL_TF2_ITEMS_URL,
            "CSGO": LOOTFARM_ALL_CSGO_ITEMS_URL,
            "Dota 2": LOOTFARM_ALL_DOTA_ITEMS_URL,
            "Rust": LOOTFARM_ALL_RUST_ITEMS_URL,
        }

        url = switcher.get(game, "TF2")
        response = await self.http_client.get(url)
        self.logger.debug("Loot farm API fetched for " + game)

        if response.status_code != 200:
            self.logger.error(
                f"Failed to fetch items from loot farm, response: {response.status_code}"
            )
            return None

        return response.json()

    #
    # SQUEMA APIs
    #

    async def schema_get_items_defindexes(self):
        """Fetches all items from the schema using dafindex API from Autobot.tf"""
        response = await self.http_client.get(
            "https://schema.autobot.tf/properties/defindexes"
        )

        if response.status_code != 200:
            self.logger.error(
                f"Failed to fetch items from schema, response: {response.status_code}"
            )
            return None

        return response.json()

    async def schema_get_items_qualities(self):
        """Fetches all items from the schema using qualities API from Autobot.tf"""
        response = await self.http_client.get(
            "https://schema.autobot.tf/properties/qualities"
        )

        if response.status_code != 200:
            self.logger.error(
                f"Failed to fetch items from schema, response: {response.status_code}"
            )
            return None

        return response.json()

    async def schema_get_items_killstreaks(self):
        """Fetches all items from the schema using killstreaks API from Autobot.tf"""
        response = await self.http_client.get(
            "https://schema.autobot.tf/properties/killstreaks"
        )

        if response.status_code != 200:
            self.logger.error(
                f"Failed to fetch items from schema, response: {response.status_code}"
            )
            return None

        return response.json()

    async def schema_get_items_effects(self):
        """Fetches all items from the schema using effects API from Autobot.tf"""
        response = await self.http_client.get(
            "https://schema.autobot.tf/properties/effects"
        )

        if response.status_code != 200:
            self.logger.error(
                f"Failed to fetch items from schema, response: {response.status_code}"
            )
            return None

        return response.json()

    async def schema_get_items_paintkits(self):
        """Fetches all items from the schema using paintkits API from Autobot.tf"""
        response = await self.http_client.get(
            "https://schema.autobot.tf/properties/paintkits"
        )

        if response.status_code != 200:
            self.logger.error(
                f"Failed to fetch items from schema, response: {response.status_code}"
            )
            return None

        return response.json()

    async def schema_get_items_wears(self):
        """Fetches all items from the schema using wears API from Autobot.tf"""
        response = await self.http_client.get(
            "https://schema.autobot.tf/properties/wears"
        )

        if response.status_code != 200:
            self.logger.error(
                f"Failed to fetch items from schema, response: {response.status_code}"
            )
            return None

        return response.json()

    async def schema_get_items_createseries(self):
        """Fetches all items from the schema using createseries API from Autobot.tf"""
        response = await self.http_client.get(
            "https://schema.autobot.tf/properties/crateseries"
        )

        if response.status_code != 200:
            self.logger.error(
                f"Failed to fetch items from schema, response: {response.status_code}"
            )
            return None

        return response.json()

    async def schema_get_items_paints(self):
        """Fetches all items from the schema using paints API from Autobot.tf"""
        response = await self.http_client.get(
            "https://schema.autobot.tf/properties/paints"
        )

        if response.status_code != 200:
            self.logger.error(
                f"Failed to fetch items from schema, response: {response.status_code}"
            )
            return None

        return response.json()

    async def schema_get_items_strangeParts(self):
        """Fetches all items from the schema using strangeParts API from Autobot.tf"""
        response = await self.http_client.get(
            "https://schema.autobot.tf/properties/strangeParts"
        )

        if response.status_code != 200:
            self.logger.error(
                f"Failed to fetch items from schema, response: {response.status_code}"
            )
            return None

        return response.json()

    async def schema_get_items_uncraftables(self):
        """Fetches all items from the schema using uncraftables API from Autobot.tf"""
        response = await self.http_client.get(
            "https://schema.autobot.tf/properties/uncraftWeapons"
        )

        if response.status_code != 200:
            self.logger.error(
                f"Failed to fetch items from schema, response: {response.status_code}"
            )
            return None

        return response.json()
