# Bot Project

This project is a bot designed to interact with Backpack.tf, Loot.farm, and Steam, performing automated tasks such as managing inventory, identifying profitable items, and more. Below are the installation instructions, configuration options, and details on how to get started.

## Install Instructions

1. Install the latest version of Python from the official website: https://www.python.org/downloads/

2. Install the required packages by running the following command in the terminal:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the bot by executing the following command in the terminal:
   ```bash
   python main.py
   ```
   > Note: The bot will not run until you have configured the settings in the `config.json` file.

## Configuration

The bot requires a configuration file to be present in the root directory named `config.json`. Below is an example of the configuration file with all available options:

```json
{
  "mongo_uri": "",
  "database_name": "backpack-database",
  "collection_name": "listings",

  "bptf_api_key": "",
  "bptf_token": "",

  "ignored_items": ["Mann Co. Supply Crate Key", "Refined Metal", "Reclaimed Metal", "Scrap Metal"],

  "steam_password": "",
  "steam_username": "",
  "steam_trade_url": "",

  "refresh_interval": 300,
  "risk_threshold": 0.1,
  "profit_threshold": 0.1,

  "loot_farm_key_sell_value": 2.56,
  "loot_farm_key_value_date": "18/08/2024",
  "loot_farm_refined_sell_value": 0.04,
  "loot_farm_refined_value_date": "18/08/2024",
  "print_events": 3,

  "dont_withdrawn": false,
  "request_login": true,

  "complete_value_with_what_items": ["Mann Co. Supply Crate Key", "Refined Metal", "Reclaimed Metal", "Scrap Metal"],
  "max_item_price": 0,

  "start_window_position": [2000, 0],

  "discord_webhook_url": "",
  "discord_webhook_avatar_url": "",
  "discord_webhook_username": "",
  "discord_alert_mention_user_ids": [""],
  "bot_version": "0.1.0"
}
```

- `mongo_uri`: The URI for the MongoDB database.
- `database_name`: The name of the database to use.
- `collection_name`: The name of the collection to use.
- `bptf_api_key`: The API key for Backpack.tf.
- `bptf_token`: The token for Backpack.tf.
- `ignored_items`: A list of items to ignore when processing.
- `steam_password`: The password for the Steam account. (not implemented | manual login required)
- `steam_username`: The username for the Steam account. (not implemented | manual login required)
- `steam_trade_url`: The trade URL for the Steam account.
- `refresh_interval`: The interval in seconds to refresh the listings.
- `risk_threshold`: The risk threshold for identifying profitable items.
- `profit_threshold`: The profit threshold for identifying profitable items.
- `loot_farm_key_sell_value`: The sell value for keys on Loot.farm.
- `loot_farm_key_value_date`: The date for the key value on Loot.farm.
- `loot_farm_refined_sell_value`: The sell value for refined metal on Loot.farm.
- `loot_farm_refined_value_date`: The date for the refined metal value on Loot.farm.
- `print_events`: The number of events to print.
- `dont_withdrawn`: Whether to withdraw items from the Steam account.
- `request_login`: Whether to request a login from the Steam account.
- `complete_value_with_what_items`: A list of items to complete the value with. (not implemented)
- `max_item_price`: The maximum price for an item.
- `start_window_position`: The position of the bot window.
- `discord_webhook_url`: The URL for the Discord webhook.
- `discord_webhook_avatar_url`: The avatar URL for the Discord webhook. (optional)
- `discord_webhook_username`: The username for the Discord webhook. (optional)
- `discord_alert_mention_user_ids`: A list of user IDs to mention in Discord alerts.
- `bot_version`: The version of the bot.
