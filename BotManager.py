import logging
import sys
import time
from datetime import datetime

from httpx import TimeoutException
from selenium import webdriver
from selenium.common.exceptions import (NoSuchElementException,
                                        NoSuchWindowException)
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from discord_utils.send_webhook_message import (send_status_webhook_message,
                                                send_styled_webhook_message)
from global_state import SharedState


class BotManager:
    def __init__(
        self,
        bptf_token: str,
        ignored_items: list,
        steam_username: str,
        steam_password: str,
        request_login: bool,
        start_window_position: tuple = (0, 0),
    ):
        self.bptf_token = bptf_token
        self.ignored_items = ignored_items

        self.steam_username = steam_username #TODO: encrypt username
        self.steam_password = steam_password #TODO: encrypt password

        self.shared_state = SharedState.get_instance()
        self.start_window_position = start_window_position

        service = Service(executable_path='./chromedriver-win64/chromedriver.exe')
        options = webdriver.ChromeOptions()

        options.add_argument("--disable-application-cache")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disk-cache-size=128")

        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_window_position(self.start_window_position[0], self.start_window_position[1])

        self.wait = WebDriverWait(self.driver, 30)
        self.low_wait = WebDriverWait(self.driver, 3)
        self.action = ActionChains(self.driver)
        self.logger = logging.getLogger(__name__)
        self.first_item = None
        self.REQUEST_LOGIN = request_login

    async def wait_until_main_page_load(self):
        self.wait.until(
            EC.visibility_of_element_located((By.XPATH, "//*[@id='bots_inv']"))
        )
        self.logger.debug("Main page loaded")

    def refresh_inventory(self):
        self.logger.debug("Refreshing inventory")
        # use script to refresh inventory
        self.driver.execute_script("document.getElementById('UpdateBotInv').click()")

    def change_sorting_via_script(self, sort_number):
        self.driver.execute_script(
            f"document.querySelector('#sortULbot').children[{sort_number}].click()"
        )
        self.logger.info(f"Ordenação alterada para {sort_number}")

    def scroll_to_element(self, element):
        self.driver.execute_script("arguments[0].scrollIntoView();", element)
        time.sleep(0.3)

    async def load_more_items(self, num_loads=3, scroll_delay=1):
        # Esperar ter pelo menos 1 item visível
        self.wait.until(
            EC.visibility_of_element_located((By.XPATH, "//*[@class='itemwrap']"))
        )

        self.logger.debug("loading more items")

        bot_inv = self.driver.find_element(By.ID, "bots_inv")
        last_height = bot_inv.get_property("scrollHeight")
        # data_scroll é um atributo do bot_inv que indica quantos itens já foram carregados (0, 50, 100, 150, ...)
        data_scroll = bot_inv.get_attribute("data-scroll") or 0

        while int(data_scroll) < num_loads * 50:
            # Scroll down until no new content is loaded
            self.driver.execute_script(
                "arguments[0].scrollTo(0, arguments[0].scrollHeight);", bot_inv
            )
            time.sleep(scroll_delay)
            new_height = bot_inv.get_property("scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

            data_scroll = bot_inv.get_attribute("data-scroll")
            self.logger.info(f"Loaded {data_scroll} items")
            # Allow time for new items to appear after scrolling
            time.sleep(scroll_delay)

    async def check_if_first_item_exists(self):
        self.logger.debug("Checking if first item exists")

        try:
            bot_inv = self.driver.find_element(By.ID, "bots_inv")
            first_item = self.first_item
            first_item_element = bot_inv.find_element(
                By.XPATH, f"//*[@id='bots_inv']//*[@id='{first_item}']"
            )
            if first_item_element:
                self.logger.info(f"First item {first_item_element.get_attribute("data-name")} exists")
                return True
            else:
                self.logger.info("First item does not exist")
                return False

        except Exception as e:
            self.logger.error(f"Erro ao tentar pegar o primeiro item: {e}")
            return False

    async def store_get_first_item(self):
        try:
            self.logger.info("Storing first item")
            first_item = self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//*[@id='bots_inv']//*[@class='itemwrap']//*[@class='itemblock']")
                )
            ).get_attribute("id")
            self.first_item = first_item
            self.logger.info(f"First item stored, id:{first_item}")
            return first_item
        except Exception as e:
            self.logger.error(f"Erro ao tentar pegar o primeiro item: {e}")
            return None

    async def scan_items_after_first(self):
        new_items = []
        repeated_items = []
        new_items_existing_names = set()
        haveNewItems = False

        if not self.first_item:
            self.logger.error("First item not stored")
            self.store_get_first_item()
            return False

        try:
            self.low_wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//*[@id='bots_inv']//*[@class='itemwrap']//*[@class='itemblock']")
                )
            )
        except Exception:
            self.logger.warn("Erro ao esperar items carregar, recarregando a página")
            # Refresh page
            self.driver.refresh()
            # Wait for page to load
            await self.wait_until_main_page_load()
            await self.change_sorting_via_script(3)
            return False
        
        try:     
            current_inventory_items_elements = self.driver.find_elements(By.XPATH, "//*[@id='bots_inv']/div[@class='itemwrap']/div[@class='itemblock']")
            first_element_id = current_inventory_items_elements[0].get_attribute("id")

            first_item_is_present = any(item.get_attribute("id") == self.first_item for item in current_inventory_items_elements)
            first_item_is_the_first = self.first_item == first_element_id
            haveNewItems = (not first_item_is_present) or (first_item_is_present and not first_item_is_the_first)

            if haveNewItems:
                for item in current_inventory_items_elements:
                    self.logger.info(f"Scanning item {item.get_attribute('data-name')}")
                    item_name = item.get_attribute("data-name")
                    
                    item_price = (
                        item.find_element(By.CLASS_NAME, "it_price")
                        .text
                        .strip()
                        .split(" x")[0]
                        .removeprefix("$")
                    )

                    if item_name in self.ignored_items:
                        self.logger.info(f"Item {item_name} skipped")
                        self.shared_state.IGNORED_ITEMS += 1
                        #store refined and key prices
                        if item_name == "Refined Metal":
                            self.shared_state.REFINED_TO_USD_BUY_LOOTFARM = item_price
                        elif item_name == "Mann Co. Supply Crate Key":
                            self.shared_state.KEY_TO_USD_BUY_LOOTFARM = item_price
                        continue   

                    item_id = item.get_attribute("id")
                    
                    if item_id == self.first_item:
                        self.logger.info(f"First item found: {item_name}")
                        break

                    item_attachments = []
                    
                    try:
                        attachment_imgs = item.find_elements(By.XPATH, ".//div[contains(@class, 'it_s')]//img")
                        for img in attachment_imgs:
                            item_attachments.append(img.get_attribute("alt"))
                    except Exception:
                        self.logger.debug(f"No attachments found for {item_name}")
                        pass

                    self.logger.info(f"Item {item_name} scanned")

                    # Filtra itens existentes e ignorados
                    if item_name in new_items_existing_names:                           
                        repeated_items.append({
                            "item_id": item_id,
                            "item_name": item_name,
                            "item_price": item_price,
                            "item_attachments": item_attachments,
                        })
                        continue    
                    new_items_existing_names.add(item_name)
                    new_items.append(
                        {
                            "item_id": item_id,
                            "item_name": item_name,
                            "item_price": item_price,
                            "item_attachments": item_attachments,
                        }
                    )   
                self.logger.info(f""" New items found: {len(new_items)}""")
            else:
                self.logger.info("No new items found")
                return False
            self.first_item = first_element_id
        except NoSuchWindowException:
            self.logger.error("Window closed")
            raise Exception("Window closed")
        
        except Exception as e:                
            self.logger.error(f"Erro ao tentar pegar os itens: {e}")
            return False
        
        self.logger.info(f"Scanned {len(new_items)} new items")
        return {
            "new_items": new_items,
            "repeated_items": repeated_items,
        }

    async def get_bot_inventory_items(self):
        bot_inv = self.driver.find_element(By.ID, "bots_inv")
        existing_names = set()
        item_data = []

        self.logger.info(f"Storing bot inventory")

        for item in bot_inv.find_elements(By.XPATH, "//*[@class='itemblock']"):
            try:
                item_name = item.get_attribute("data-name")

                if item_name in existing_names or item_name in self.ignored_items:
                    self.logger.debug(f"Item {item_name} skipped")
                    continue

                existing_names.add(item_name)
                item_id = item.get_attribute("id")
                item_price = (
                    item.find_element(By.CLASS_NAME, "it_price")
                    .text
                    .strip()
                    .split(" x")[0]
                    .removeprefix("$")
                )

                item_attachments = []

                try:
                    attachment_imgs = item.find_elements(By.XPATH, ".//div[contains(@class, 'it_s')]//img")
                    for img in attachment_imgs:
                        item_attachments.append(img.get_attribute("alt"))
                        
                except NoSuchElementException:
                    self.logger.debug(f"No attachments found for {item_name}")
                    pass

                except Exception as e:
                    self.logger.error(f"Erro ao tentar pegar os anexos do item: {e}")

                item_data.append(
                    {
                        "item_id": item_id,
                        "item_name": item_name,
                        "item_price": item_price,
                        "item_attachments": item_attachments,
                    }
                )
                self.logger.info(f"Item {item_name} stored")

            except Exception as e:
                self.logger.error(f"Erro ao tentar pegar os dados do item: {e}")
                self.shared_state.debug_error(
                    error=e,
                    other_vars={
                        "item_id": item_id,
                        "item_name": item_name,
                        "item_price": item_price,
                        "item_attachments": item_attachments,
                    },
                  )
        self.logger.info(f"Bot inventory scanned: {len(item_data)} items")
        return item_data

    async def withdraw_items(self, items):
        self.logger.info(f"Withdrawing {len(items)} items")
        removed_items = []
        # Calculate total cost and update shared state *before* attempting withdrawals
        total_cost = 0.00
        profit_value = 0.00

        for item in items:
            self.shared_state.PROFITABLE_ITEMS += 1
            total_cost += float(item["loot_farm_price"]) 

        # Ensure sufficient funds before proceeding with withdrawals
        if total_cost > self.shared_state.REMAINING_MONEY:
            self.logger.info("Insufficient funds for withdrawal. Removing items...")
            while total_cost > self.shared_state.REMAINING_MONEY:
                removed_item = items.pop()
                removed_items.append(removed_item)
                total_cost -= removed_item["loot_farm_price"]
                self.logger.debug(f"Removed item: {removed_item['name']}")
            
            self.logger.info(f"Items removed. New total cost: {total_cost}")

        # Proceed with withdrawals only if there are items left after potential removal
        if items: 
            for item in items:
                try:
                    self.driver.execute_script(
                        f"document.getElementById('{item['item_id']}').querySelector('img').click()"
                    )
                except Exception as e:
                    self.logger.error(f"Error withdrawing item: {e}")

            self.logger.info("Selected items for withdrawal")

            tradeBtn = self.driver.find_element(By.ID, "tradeButton")
            if tradeBtn.text == "ERROR :(":
                self.logger.error("ERROR :( message found in trade button, too many items selected @TODO")
                time.sleep(5)
            else:
                tradeBtn.click()
                self.logger.info("Trade button clicked")

            # Open trade window 
            discord_message = f"Bought items: {datetime.now().strftime('%H:%M')} Profit: {profit_value} USD\n\n"

            # document.querySelector(".AcceptButton") - esperar ate 5 minutos
            WebDriverWait(self.driver, 300).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "AcceptButton"))
            )

            time.sleep(1)

            # vai para a página de trade
            self.driver.switch_to.window(self.driver.window_handles[1])
            self.logger.info("Trade window opened")
            # esperar trade_box_contents class
            self.wait.until(
                EC.visibility_of_element_located((By.CLASS_NAME, "trade_box_contents"))
            )

            self.logger.info("Trade page loaded")
            self.logger.warning(f"NEED TO CHECK WHAT HAPPEN WHEN THE BOT REACHES THIS POINT")

            for item in items:
                profit_price = item["average_price"] - item["loot_farm_price"] 
                self.shared_state.ESTIMATED_PROFIT += profit_price
                profit_value += profit_price
                discord_message += f"**{item['name']}** - Profit: ```{profit_price} USD```\n"

            if len(removed_items) > 0:
                discord_message += "\n\nProfitable items were removed due to insufficient funds:\n"
                for item in removed_items:
                    discord_message += f"**{item['name']}** - Price: ```{item['loot_farm_price']} USD```\n"

            send_styled_webhook_message(message=discord_message , title=f"Bot bought {len(items)} items")
        else:
            self.logger.warning("No items left to withdraw after ensuring sufficient funds.")
        
        self.logger.info(f"Finished withdrawing {len(items)} items, profit: {profit_value} USD, remaining money: {self.shared_state.REMAINING_MONEY} USD")
        time.wait(15)

    async def get_available_money(self):
        self.logger.info("Getting available money")
        try:
            #wait until the money is visible
            money = self.wait.until(
                EC.visibility_of_element_located((By.ID, "myBalance"))
            ).text.removeprefix("$")

            money = self.driver.find_element(By.ID, "myBalance").text.removeprefix("$")
            self.logger.info(f"Available money: {money}")

            self.shared_state.update_balance(money)

        except Exception as e:
            self.logger.error(f"Erro ao tentar pegar o dinheiro disponível: {e}")
            return False

    async def get_refined_and_key_lootfarm_sell_prices(self):
        self.logger.info("Getting refined and key prices from LootFarm")
        
        #execute script to change search to refined metal document.getElementById('searchBot').value='banana'
        self.driver.execute_script("document.getElementById('searchUser').value='Refined Metal'")
        self.driver.execute_script("document.getElementById('searchUser').dispatchEvent(new Event('input'))")
        
        # wait until the at least 1 item is loaded in the user inventory
        try:
            # esperar um item aparecer que nao tenha o id user_topup
            self.low_wait.until(
                EC.presence_of_element_located((By.XPATH, "//*[@id='user_inv']//*[@class='itemwrap']//*[@data-name='Refined Metal']"))
            )

            refined_metal = self.driver.find_element(By.XPATH, "//*[@id='user_inv']//*[@class='itemwrap']//*[@data-name='Refined Metal']")
            refined_metal_price = refined_metal.find_element(By.CLASS_NAME, "it_price").text.removeprefix("$").strip().split(" x")[0]

            if refined_metal_price == "0.00" or refined_metal_price == "0":
                raise Exception("Refined metal price is 0.00")
            
            self.shared_state.update_refined_to_usd_sell_lootfarm(new_value=refined_metal_price)
            self.logger.info(f"Refined metal updated to price: {refined_metal_price}")

        except Exception as e:
            self.logger.error(f"User has no refined metal, using default value {self.shared_state.REFINED_TO_USD_SELL_LOOTFARM}")
            self.shared_state.check_refined_price_date()

        #execute script to change search to key document.getElementById('searchBot').value='banana'
        self.driver.execute_script("document.getElementById('searchUser').value='Mann Co. Supply Crate Key'")
        self.driver.execute_script("document.getElementById('searchUser').dispatchEvent(new Event('input'))")

        # wait until the at least 1 item is loaded in the user inventory
        try:
            self.low_wait.until(
                EC.presence_of_element_located((By.XPATH, "//*[@id='user_inv']//*[@class='itemwrap']//*[@data-name='Mann Co. Supply Crate Key']"))
            )

            key = self.driver.find_element(By.XPATH, "//*[@id='user_inv']//*[@class='itemwrap']//*[@data-name='Mann Co. Supply Crate Key']")
            key_price = key.find_element(By.CLASS_NAME, "it_price").text.removeprefix("$").strip().split(" x")[0]

            if key_price == "0.00" or key_price == "0":
                raise Exception("Key price is 0.00")
        
            self.shared_state.update_key_to_usd_sell_lootfarm(new_value=key_price)
            self.logger.info(f"Key price: {key_price}")

        except Exception as e:
            self.logger.error(f"User has no keys, using default value {self.shared_state.KEY_TO_USD_SELL_LOOTFARM}")
            self.shared_state.check_key_price_date()

        # clean search
        self.driver.execute_script("document.getElementById('searchUser').value=''")
        self.driver.execute_script("document.getElementById('searchUser').dispatchEvent(new Event('input'))")
        
    async def login_in_steam(self, manual=True):
        self.logger.info("Logging in Steam")
        try:
            if manual or self.steam_username == "" or self.steam_password == "":
                self.logger.info("Manual login required")
                
                self.driver.execute_script("document.querySelector('#userNoLogin').firstElementChild.click()")
                self.logger.info("Clicked on login button")
                time.sleep(1)

                self.logger.info("Waiting for login")
                #esperar encontrar o inventario do bot para confirmar que o login foi feito
                WebDriverWait(self.driver, 120).until(
                    EC.visibility_of_element_located((By.ID, "bots_inv"))
                )
                self.logger.info("Logged in Steam")
                
            else:
                # try to login automatically @TODO: implement
                self.logger.info("Trying to login automatically, not implemented yet")
                raise Exception("Not implemented yet")
            return True            
        except TimeoutException as e:
            self.logger.error(f"Timeout ao tentar logar no Steam: {e}, tentando novamente")
            await self.login_in_steam(manual=manual)
            
        except Exception as e:
            self.logger.error(f"Erro ao tentar logar no Steam: {e}")
            return False
        finally:
            self.logger.info("Login finished")
            # store cookies after login #TODO: maybe store cookies in a file, but is it necessary? not really safe
            # cookies_after_login = self.driver.get_cookies()
            # store_cookies = open("cookies.txt", "w")
            # store_cookies.write(str(cookies_after_login))

    async def start(self):
        # open lootfarm
        self.driver.get("https://loot.farm/")
        # Cookies concent
        self.driver.add_cookie({"name": "receive-cookie-deprecation", "value": "1"})
        self.driver.add_cookie({"name": "noCancelScam", "value": "1"})
        self.driver.add_cookie({"name": "cookie_consent_user_accepted", "value": "true"})
        self.driver.add_cookie({"name": "cookie_consent_user_consent_token", "value": "FQAGp2I4wEAX"})
        self.driver.add_cookie({"name": "cookie_consent_level", "value": "%7B%22strictly-necessary%22%3Atrue%2C%22functionality%22%3Afalse%2C%22tracking%22%3Afalse%2C%22targeting%22%3Afalse%7D"})        

        # set game to TF2
        self.driver.execute_script("localStorage.setItem('bInvGame', '440')")
        self.driver.execute_script("localStorage.setItem('uInvGame', '440')")

        # wait until main page load
        await self.wait_until_main_page_load()
        
        # login in steam
        if self.REQUEST_LOGIN:
            login_status = await self.login_in_steam(manual=True)
            if not login_status:
                self.logger.error("Failed to login in Steam")
                raise Exception("Failed to login in Steam")
            
            # get refined and key prices from lootfarm
            await self.get_refined_and_key_lootfarm_sell_prices()
            # get available money
            await self.get_available_money()

        else:
            #Refresh page to make the cookies works
            self.logger.warning("REQUEST_LOGIN is False, the bot will not login in Steam and will use the default values for refined and key prices")
            self.driver.refresh()
        

        # change sorting to price
        self.change_sorting_via_script(3)
        # store first item
        result = None
        while result is None:
            result = await self.store_get_first_item()

        send_styled_webhook_message(
            title="Bot started",
            message=f"Bot started at {datetime.now().strftime('%H:%M')} \n Available money: {self.shared_state.REMAINING_MONEY} USD",
        )

        return True
