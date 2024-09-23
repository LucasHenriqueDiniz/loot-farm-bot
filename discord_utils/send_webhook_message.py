from datetime import datetime

import requests

from utils.load_config import load_config

config = load_config("config.json")

# colors dictionary
colors = {
    "green": 0x2ECC71,
    "red": 0xE74C3C,
    "blue": 0x3498DB,
    "yellow": 0xF1C40F,
    "orange": 0xE67E22,
    "purple": 0x9B59B6,
    "pink": 0xE91E63,
    "cyan": 0x1ABC9C,
    "teal": 0x1ABC9C,
    "brown": 0x795548,
    "grey": 0x95A5A6,
    "black": 0x000000,
    "white": 0xFFFFFF,
}


def send_status_webhook_message(shared_state):
    url = config["discord_webhook_url"]
    if not url or url == "":
        print("ERROR: No webhook url provided in config.json, ignoring message")
        return

    avatar_url = config.get(
        "discord_webhook_avatar_url",
        "https://t3.ftcdn.net/jpg/05/66/26/98/360_F_566269813_8VisUzV5qqdN7nQ7De4FcVEVxnRuKh2E.jpg",
    )
    webhook_username = config.get("discord_webhook_username", "LootBot")
    bot_version = config.get("bot_version", "Unknown")
    running_time = datetime.now() - shared_state.START_TIME
    total_running_str = (
        f"{running_time.days} days, {running_time.seconds // 3600} hours, {(running_time.seconds // 60) % 60} minutes"
        if running_time.days > 0
        else f"{running_time.seconds // 3600} hours, {(running_time.seconds // 60) % 60} minutes"
    )
    embed_color = colors.get("blue", 0x3498DB)

    formatted_profit = format(shared_state.ESTIMATED_PROFIT, ".2f")
    formatted_remaining_money = format(shared_state.REMAINING_MONEY, ".2f")

    data = {
        "username": webhook_username,
        "avatar_url": avatar_url,
        "embeds": [
            {
                "title": "📊 Statistics 📊",
                "description": f"A summary of the bot's current status from the past {total_running_str}.",
                "color": embed_color,
                "fields": [
                    {
                        "name": "__Type__",
                        "value": f"""
                        **• Estimated profit:** 
                        **• New items found:** 
                        **• Profitable items found:** 
                        **• Errors encountered:**
                        **• Remaining money:**
                        """,
                        "inline": True,
                    },
                    {
                        "name": "__Value__",
                        "value": f"""
                        ${formatted_profit}
                        {shared_state.NEW_ITEMS} items 
                        {shared_state.PROFITABLE_ITEMS} items 
                        {shared_state.ERRORS} errors
                        ${formatted_remaining_money}
                        """,
                        "inline": True,
                    },
                    {
                        "name": "__Status__",
                        "value": f"""
                        **• Running time:**  {total_running_str} 
                        **• Bot version:** {bot_version} 
                        """,
                    },
                ],
            },
            {
                "title": "🏷️ Prices 🏷️",
                "description": "A summary of the current prices used by the bot.",
                "color": embed_color,
                "footer": {
                    "text": f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} • v{bot_version}",
                    "avatar_url": avatar_url,
                    "icon_url": avatar_url,
                },
                "fields": [
                    {
                        "name": "__Type__",
                        "value": f"""
                        **• Refined to USD (Loot.Farm):** 
                        **• Key to USD (Loot.Farm):** 
                        **• Refined to USD (BPTF):** 
                        **• Key to Refined (BPTF):** 
                        **• Refined to USD (Autobot):** 
                        **• Key to Refined (Autobot):** 
                        """,
                        "inline": True,
                    },
                    {
                        "name": "__Sell__",
                        "value": f"""
                        {shared_state.REFINED_TO_USD_SELL_LOOTFARM} USD 
                        {shared_state.KEY_TO_USD_SELL_LOOTFARM} USD 
                        {shared_state.REFINED_TO_USD_SELL_BPTF} USD 
                        {shared_state.KEY_TO_REFINED_SELL_BPTF} Refined 
                        N/A 
                        {shared_state.KEY_TO_REFINED_SELL_AUTOBOT} Refined 
                        """,
                        "inline": True,
                    },
                    {
                        "name": "__Buy__",
                        "value": f"""
                        {shared_state.REFINED_TO_USD_BUY_LOOTFARM} USD 
                        {shared_state.KEY_TO_USD_BUY_LOOTFARM} USD 
                        {shared_state.REFINED_TO_USD_BUY_BPTF} USD 
                        {shared_state.KEY_TO_REFINED_BUY_BPTF} Refined 
                        N/A
                        {shared_state.KEY_TO_REFINED_BUY_AUTOBOT} Refined 
                        """,
                        "inline": True,
                    },
                ],
            },
        ],
    }

    response = requests.post(url, json=data)

    if response.status_code != 204:
        print("Error sending message:")
        print(response.status_code)
        print(response.text)  # Include the error response for debugging


def send_styled_webhook_message(
    message, is_crash_alert=False, title=None, color="green", mention=False
):
    url = config["discord_webhook_url"]
    if not url or url == "":
        print("ERROR: No webhook url provided in config.json, ignoring message")
        return
    embed_color = colors.get(color, 0x2ECC71)
    avatar_url = config.get(
        "discord_webhook_avatar_url",
        "https://yt3.googleusercontent.com/ytc/AIdro_mFWZoH7C9E4n2R7uyaXTuj_oWK1sw84-9sXnJxj60Mng=s160-c-k-c0x00ffffff-no-rj",
    )
    webhook_username = config.get("discord_webhook_username", "Your Beloved Bot")
    version = config.get("bot_version", "Unknown")
    user_ids = config.get("discord_alert_mention_user_ids", [])

    # Basic embed structure
    data = {
        "username": webhook_username,
        "avatar_url": avatar_url,
        "embeds": [
            {
                "description": message,
                "color": embed_color,
                "title": title,
                "footer": {
                    "text": f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} • v{version}",
                    "avatar_url": avatar_url,
                    "icon_url": avatar_url,
                },
            }
        ],
    }

    if mention and not is_crash_alert:
        mention_str = " ".join([f"<@{user_id}>" for user_id in user_ids])
        data["embeds"][0]["description"] += "\n\n" + mention_str

    # Enhance the embed if it's a crash alert
    if is_crash_alert:
        data["embeds"][0]["title"] = "Bot crashed!"
        data["embeds"][0]["color"] = colors.get("red", 0xE74C3C)
        data["embeds"][0]["description"] = f"**{title}**\n\n```{message}```\n\n"
        mention_str = " ".join([f"<@{user_id}>" for user_id in user_ids])
        data["embeds"][0]["description"] += "\n\n" + mention_str

    response = requests.post(url, json=data)

    if response.status_code != 204:
        print("Error sending message:")
        print(response.status_code)
        print(response.text)  # Include the error response for debugging
