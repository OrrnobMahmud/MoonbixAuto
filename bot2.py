import os
import json
import logging
import requests
import time
import random
import asyncio
from datetime import datetime
from pathlib import Path
from colorama import init, Fore, Style
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Initialize colorama
init(autoreset=True)

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', filename='bot.log', filemode='w')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

class Config:
    def __init__(self, auto_task, auto_game, min_points, max_points, interval_minutes):
        self.auto_task = auto_task
        self.auto_game = auto_game
        self.min_points = min_points
        self.max_points = max_points
        self.interval_minutes = interval_minutes

class Binance:
    def __init__(self, account_index, query_string, config: Config, proxy=None):
        self.account_index = account_index
        self.query_string = query_string
        self.proxy = proxy
        self.proxy_ip = "Unknown" if proxy else "Direct"
        self.headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5",
            "Content-Type": "application/json",
            "Origin": "https://www.binance.com",
            "Referer": "https://www.binance.com/vi/game/tg/moon-bix",
            "Sec-Ch-Ua": '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
            "Sec-Ch-Ua-Mobile": "?1",
            "Sec-Ch-Ua-Platform": '"Android"',
            "User-Agent": self.get_random_android_user_agent()
        }
        self.game_response = None
        self.game = None
        self.config = config
        self.trap_items = []
        logging.debug(f'Initialized Binance client for account index {account_index}')

    @staticmethod
    def get_random_android_user_agent():
        android_user_agents = [
            "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 11; Pixel 4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.62 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 11; OnePlus 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 10; Redmi Note 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Mobile Safari/537.36"
        ]
        return random.choice(android_user_agents)

    def log(self, msg, type='info'):
        timestamp = datetime.now().strftime('%H:%M:%S')
        account_prefix = f"[Pemulung {self.account_index + 1}]"
        ip_prefix = f"[{self.proxy_ip}]"
        log_message = {
            'success': f"{account_prefix}{ip_prefix} {Fore.GREEN}{msg}",
            'error': f"{account_prefix}{ip_prefix} {Fore.RED}{msg}",
            'warning': f"{account_prefix}{ip_prefix} {Fore.YELLOW}{msg}",
            'custom': f"{account_prefix}{ip_prefix} {Fore.MAGENTA}{msg}"
        }.get(type, f"{account_prefix}{ip_prefix} {msg}")
        
        print(f"[{timestamp}] {log_message}")
        logging.debug(f"{account_prefix}{ip_prefix} {msg}")  # Log to file

    def create_requests_session(self):
        session = requests.Session()
        if self.proxy:
            proxy = {"http": self.proxy, "https": self.proxy}
            session.proxies.update(proxy)
            logging.debug(f'Using proxy {self.proxy}')
        else:
            logging.debug('No proxy used')
        retry = Retry(connect=3, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.headers.update(self.headers)
        return session

    def check_proxy_ip(self):
        try:
            session = self.create_requests_session()
            response = session.get('https://api.ipify.org?format=json')
            if response.status_code == 200:
                self.proxy_ip = response.json().get('ip')
            else:
                raise ValueError(f"Cannot check proxy IP. Status code: {response.status_code}")
        except Exception as e:
            raise ValueError(f"Error checking proxy IP: {str(e)}")
        logging.debug(f'Proxy IP is {self.proxy_ip}')

    async def call_binance_api(self, query_string):
        access_token_url = "https://www.binance.com/bapi/growth/v1/friendly/growth-paas/third-party/access/accessToken"
        user_info_url = "https://www.binance.com/bapi/growth/v1/friendly/growth-paas/mini-app-activity/third-party/user/user-info"
        
        session = self.create_requests_session()
        
        try:
            response = await asyncio.to_thread(
                session.post, access_token_url, json={"queryString": query_string, "socialType": "telegram"}
            )
            access_token_response = response.json()
            if access_token_response.get('code') != "000000" or not access_token_response.get('success'):
                raise ValueError(f"Failed to get access token: {access_token_response.get('message')}")
            
            access_token = access_token_response.get('data', {}).get('accessToken')
            session.headers.update({"X-Growth-Token": access_token})
            
            response = await asyncio.to_thread(
                session.post, user_info_url, json={"resourceId": 2056}
            )
            user_info_response = response.json()
            if user_info_response.get('code') != "000000" or not user_info_response.get('success'):
                raise ValueError(f"Failed to get user info: {user_info_response.get('message')}")
            
            return {"userInfo": user_info_response.get('data'), "accessToken": access_token}
        except Exception as e:
            self.log(f"API call failed: {str(e)}", 'error')
            return None

    def identify_trap_items(self, game_config):
        for item in game_config.get('itemSettingList', []):
            if item['type'] == 'TRAP':
                self.trap_items.append(item)
        self.log(f"Identified {len(self.trap_items)} traps to avoid.", 'info')

    async def start_game(self, access_token):
        try:
            response = await asyncio.to_thread(
                self.create_requests_session().post,
                'https://www.binance.com/bapi/growth/v1/friendly/growth-paas/mini-app-activity/third-party/game/start',
                json={"resourceId": 2056},
                headers={"X-Growth-Token": access_token}
            )
            self.game_response = response.json()
            if self.game_response.get('code') == '000000':
                self.log("Started Game", 'success')
                self.identify_trap_items(self.game_response.get('cryptoMinerConfig', {}))
                return True
            else:
                self.handle_game_start_failure()
                return False
        except Exception as e:
            self.log(f"Cannot start game: {str(e)}", 'error')
            return False
    
    async def complete_game(self, access_token):
        try:
            response = await asyncio.to_thread(
                self.create_requests_session().post,
                'https://www.binance.com/bapi/growth/v1/friendly/growth-paas/mini-app-activity/third-party/game/complete',
                json={
                    "resourceId": 2056,
                    "payload": self.game.get('payload'),
                    "log": self.game.get('log')
                },
                headers={"X-Growth-Token": access_token}
            )

            if response.json().get('code') == '000000' and response.json().get('success'):
                self.log(f"Completed game | Received {self.game.get('log')} points", 'custom')
                return True

            self.log(f"Cannot complete game: {response.json().get('message')}", 'error')
            return False
        except Exception as e:
            self.log(f"Error completing game: {str(e)}", 'error')
            return False

    async def auto_play_game(self, access_token, available_tickets):
        while available_tickets > 0:
            self.log(f"Starting game with {available_tickets} tickets available", 'info')
            if await self.start_game(access_token):
                if await self.game_data():
                    points = random.randint(self.config.min_points, self.config.max_points)
                    self.log(f"Playing game with {points} points!")
                    if await self.complete_game(access_token):
                        available_tickets -= 1
                        self.log(f"Tickets remaining: {available_tickets}", 'info')
                    await asyncio.sleep(random.uniform(1, 3))  # Random pauses
                else:
                    self.break_game_play("Cannot receive game data")
                    break
            else:
                self.break_game_play("Cannot start game")
                break

    def break_game_play(self, reason):
        self.log(reason, 'error')

async def run_worker(account_index, query_string, proxy, config):
    client = Binance(account_index, query_string, config, proxy)
    await client.play_game_if_tickets_available()

async def main():
    # Clear the console
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Displaying the banner
    banner = f"""
{Fore.GREEN}
   ___                   _      __  __      _                 _ 
  / _ \ _ _ _ _ _ _  ___| |__  |  \/  |__ _| |_  _ __ _  _ __| |
 | (_) | '_| '_| ' \/ _ \ '_ \ | |\/| / _` | ' \| '  \ || / _` |
  \___/|_| |_| |_||_\___/_.__/ |_|  |_\__,_|_||_|_|_|_\_,_\__,_|
                                                                
    Automated Binance Game Bot with Proxy and Task Management
    {Style.RESET_ALL}
"""
    print(banner)
    
    data_file = Path(__file__).parent / 'data.txt'
    proxy_file = Path(__file__).parent / 'proxy.txt'
    config_file = Path(__file__).parent / 'config.json'

    # Ensure config file exists
    if not config_file.exists():
        with open(config_file, 'w') as f:
            json.dump({
                "auto_task": True,
                "auto_game": True,
                "min_points": 100,
                "max_points": 300,
                "interval_minutes": 60
            }, f, indent=4)

    # Ensure proxy file exists (create if not)
    if not proxy_file.exists():
        with open(proxy_file, 'w') as f:
            pass  # Creating an empty proxy file

    with open(data_file, 'r') as file:
        data = file.read().replace('\r', '').split('\n')
        logging.debug(f'Read {len(data)} accounts from {data_file}')

    with open(proxy_file, 'r') as file:
        proxies = file.read().split('\n')
        logging.debug(f'Read {len(proxies)} proxies from {proxy_file}')

    with open(config_file, 'r') as file:
        config_data = json.load(file)
        config = Config(
            auto_task=config_data.get("auto_task", True),
            auto_game=config_data.get("auto_game", True),
            min_points=config_data.get("min_points", 100),
            max_points=config_data.get("max_points", 300),
            interval_minutes=config_data.get("interval_minutes", 60)
        )
        logging.debug(f'Configuration: {config_data}')

    data = [line for line in data if line.strip()]
    proxies = [line for line in proxies if line.strip()]

    max_threads = 10
    wait_time = config.interval_minutes * 60  # Convert minutes to seconds

    while True:
        tasks = []
        for i in range(0, len(data)):
            account_index = i
            query_string = data[account_index]
            proxy = proxies[account_index % len(proxies)] if proxies else None
            tasks.append(run_worker(account_index, query_string, proxy, config))

            if len(tasks) >= max_threads or i == len(data) - 1:
                await asyncio.gather(*tasks)
                tasks = []
                await asyncio.sleep(3)

        logging.debug(f"All accounts processed. Waiting for {wait_time // 60} minutes before restarting...")
        print(f"All accounts processed. Waiting for {wait_time // 60} minutes before restarting...")
        await asyncio.sleep(wait_time)


if __name__ == '__main__':
    asyncio.run(main())
