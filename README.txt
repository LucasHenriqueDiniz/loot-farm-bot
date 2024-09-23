# Install Instructions

1. Install the latest version of Python from the official website: https://www.python.org/downloads/

2. Install the required packages by running the following command in the terminal:
   `pip install -r requirements.txt`
3. Run the program by running the following command in the terminal:
   `py main.py`
   or
   Execute the batch file named "run.bat" by double-clicking on it.


# Configuration Options

The `config.json` file contains various settings to customize the bot's behavior. Here's a breakdown of each option:

* `mongo_uri`: The connection string for your MongoDB database. Replace the placeholder with your actual MongoDB URI. (dont change)
* `database_name`: The name of the MongoDB database to use. (dont change)
* `collection_name`: The name of the collection within the database to store listings. (dont change)

* `bptf_api_key`: Your Backpack.tf API key. Obtain one from your Backpack.tf account settings. (your backpack.tf api_key you can use my for now)
* `bptf_token`: Your Backpack.tf user token. Also available in your Backpack.tf account settings. (you can use mine for now too)

* `ignored_items`: An array of item names that the bot will ignore when checking for profit.

* `steam_password`: Your Steam account password. (Currently not implemented, leave blank)
* `steam_username`: Your Steam account username. (Currently not implemented, leave blank)
* `steam_trade_url`: Your Steam trade URL. This is where the bot will send trade offers. (Currently not implemented, leave blank)

* `refresh_interval`: How often (in seconds) the bot will refresh its inventory and check for new items.
* `risk_threshold`: A value between 0 and 1 representing the bot's risk tolerance. Higher values mean the bot is more likely to take risks on potentially profitable items.
* `profit_threshold`: The minimum profit (in USD) the bot requires before considering an item profitable.

* `loot_farm_key_sell_value`: The current sell value of a Mann Co. Supply Crate Key on Loot.farm.
* `loot_farm_key_value_date`: The date when the `loot_farm_key_sell_value` was last updated.
* `loot_farm_refined_sell_value`: The current sell value of one Refined Metal on Loot.farm.
* `loot_farm_refined_value_date`: The date when the `loot_farm_refined_sell_value` was last updated.

* `print_events`: Controls the level of detail printed to the console. 0 is the least detailed (only critical errors), 4 is the most detailed (includes debug information). (the best is 3)
* `dont_withdrawn`:  (Boolean) If `true`, the bot will not actually withdraw items, only simulate the process. (if you want to check what type of items the bot consider profitable)

* `complete_value_with_what_items`: An array of item names that the bot can use to complete the value of a trade if the buyer doesn't have enough of the primary currency. (Currently not implemented, leave blank)
* `max_item_price`: The maximum price (in USD) the bot will consider for any item. Leave 0 for no limit (will only use the avaible money as a limit)

* `discord_webhook_url`: The URL of your Discord webhook. Used to send notifications and status updates. (you can ask me how to create a webhook if you want)
* `discord_webhook_avatar_url`: The URL of the avatar image to use for the Discord webhook messages.
* `discord_webhook_username`: The username to display for the Discord webhook messages.
* `discord_alert_mention_user_ids`: An array of Discord user IDs to mention in alert messages.

* `bot_version`: The current version of the bot. (dont change)