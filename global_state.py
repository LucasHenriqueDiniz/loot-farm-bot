from datetime import datetime
import sys
from time import time
import traceback

from discord_utils.send_webhook_message import send_styled_webhook_message
from utils.load_config import load_config


class SharedState:
    _instance = None

    # Singleton class to store global state variables
    def __init__(self):
        if SharedState._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            SharedState._instance = self

        config = load_config("config.json")
        # Initialize stats variables
        self.ESTIMATED_PROFIT = 0.00
        self.NEW_ITEMS = 0
        self.START_TIME = datetime.now()
        self.PROFITABLE_ITEMS = 0
        self.ERRORS = 0
        self.REMAINING_MONEY = 0.00
        self.IGNORED_ITEMS = 0
        self.MAX_ITEM_PRICE = config["max_item_price"]

        # Initialize currency values
        self.REFINED_TO_USD_SELL_LOOTFARM = config["loot_farm_refined_sell_value"]
        self.KEY_TO_USD_SELL_LOOTFARM = config["loot_farm_key_sell_value"]
        # date of the last refined to usd sell value update
        self.DEFAULT_REFINED_TO_USD_SELL_LOOTFARM_DATE = datetime.strptime(
            config["loot_farm_refined_value_date"], "%d/%m/%Y"
        )
        # date of the last key to usd sell value update
        self.DEFAULT_KEY_TO_USD_SELL_LOOTFARM_DATE = datetime.strptime(
            config["loot_farm_key_value_date"], "%d/%m/%Y"
        )

        self.REFINED_TO_USD_BUY_LOOTFARM = 0
        self.KEY_TO_USD_BUY_LOOTFARM = 0

        self.KEY_TO_REFINED_SELL_BPTF = 0
        self.KEY_TO_REFINED_BUY_BPTF = 0
        self.REFINED_TO_USD_SELL_BPTF = 0
        self.REFINED_TO_USD_BUY_BPTF = 0

        self.KEY_TO_REFINED_SELL_AUTOBOT = 0
        self.KEY_TO_REFINED_BUY_AUTOBOT = 0

        self.last_snapshot_request_time = None
        self.snapshot_count = 0

    @staticmethod
    def get_instance():
        if SharedState._instance is None:
            SharedState()
        return SharedState._instance

    def debug_error(self, error, other_vars):
        self.ERRORS += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = "\n\n --------------------------------------------------------- \n\n"

        exc_type, exc_value, exc_traceback = sys.exc_info()
        file_name = exc_traceback.tb_frame.f_code.co_filename
        line_number = exc_traceback.tb_lineno
        function_name = exc_traceback.tb_frame.f_code.co_name

        header = f"Error at [{timestamp}] in [{file_name}] at line [{line_number}] in function [{function_name}]\n"

        outras_variaveis_str = ""
        for key, value in other_vars.items():
            # Truncate long values to avoid overwhelming the log
            if isinstance(value, str) and len(value) > 100:
                value = value[:100] + "..."
            outras_variaveis_str += f"{key}: {value}\n"

        # Include the traceback for more detailed error information
        traceback_str = traceback.format_exc()

        error_message = (
            header
            + line
            + str(error)
            + line
            + outras_variaveis_str
            + line
            + traceback_str
        )

        # Saving the log to a file
        with open(f"logs/errors_{self.START_TIME.strftime('%Y-%m-%d')}.log", "a") as f:
            f.write(error_message + "\n")

    def check_key_price_date(self):
        """Check if the default key price is outdated and send a message if it is."""

        if (datetime.now() - self.DEFAULT_KEY_TO_USD_SELL_LOOTFARM_DATE).days >= 7:
            last_update_date = self.DEFAULT_KEY_TO_USD_SELL_LOOTFARM_DATE.strftime(
                "%Y-%m-%d %H:%M"
            )

            send_styled_webhook_message(
                message=f"Config option used to calculate the profit is outdated ```loot_farm_key_sell_value: {self.KEY_TO_USD_SELL_LOOTFARM}```\n**Last update was:**```{last_update_date}```\nThe bot will continue to work using the value set in the config file, but it is recommended to keep this value updated to avoid losses.",
                color="red",
                title="Outdated Key Price!",
                mention=True,
            )

    def check_refined_price_date(self):
        """Check if the default refined price is outdated and send a message if it is."""

        if (datetime.now() - self.DEFAULT_REFINED_TO_USD_SELL_LOOTFARM_DATE).days >= 7:
            last_update_date = self.DEFAULT_REFINED_TO_USD_SELL_LOOTFARM_DATE.strftime(
                "%Y-%m-%d %H:%M"
            )
            send_styled_webhook_message(
                message=f"Config option used to calculate the profit is outdated ```loot_farm_refined_sell_value: {self.REFINED_TO_USD_SELL_LOOTFARM}```\n**Last update was:**```{last_update_date}```\nThe bot will continue to work using the value set in the config file, but it is recommended to keep this value updated to avoid losses.",
                color="red",
                title=f"Outdated Refined Metal Price!",
                mention=True,
            )

    def update_refined_to_usd_sell_lootfarm(self, new_value):
        self.REFINED_TO_USD_SELL_LOOTFARM = new_value
        self.DEFAULT_REFINED_TO_USD_SELL_LOOTFARM_DATE = datetime.now()

    def update_key_to_usd_sell_lootfarm(self, new_value):
        self.KEY_TO_USD_SELL_LOOTFARM = new_value
        self.DEFAULT_KEY_TO_USD_SELL_LOOTFARM_DATE = datetime.now()

    def update_balance(self, new_balance):
        # transform the balance to float
        f_new_balance = float(new_balance)
        if f_new_balance < 5.0:
            send_styled_webhook_message(
                message=f"Current balance is below $5.00, is recommended to stop the bot and add more funds.\n```Current balance: ${new_balance}```",
                color="red",
                title="Low Balance!",
                mention=True,
            )
        self.REMAINING_MONEY = f_new_balance

    def should_make_snapshot_request(self):
        current_time = time()

        if (
            self.last_snapshot_request_time is None
            or current_time - self.last_snapshot_request_time >= 60
        ):
            self.last_snapshot_request_time = current_time
            self.snapshot_count = 0
        self.snapshot_count += 1

        if self.snapshot_count > 60:
            return False

        return True
