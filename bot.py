import asyncio
import json
import random
import requests
from colorama import init, Fore, Style
import os
import time
from urllib.parse import parse_qs
from datetime import datetime as dt

# Initialize colorama for colorful logging in terminal
init(autoreset=True)

class MoonBix:
    def __init__(self):
        self.base_headers = {
            "scheme": "https",
            "accept": "application/json, text/plain, */*",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "content-type": "application/json",
            "origin": "https://www.binance.com/",
            "x-requested-with": "org.telegram.messenger",
        }
        self.session = requests.Session()
        self.load_config()

    def load_config(self):
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
            self.auto_play_game = config.get("auto_play_game", True)
            self.min_win = config["game_point"].get("low", 10)
            self.max_win = config["game_point"].get("high", 50)
            if self.min_win > self.max_win:
                print(f"{Fore.YELLOW}High game point must be greater than low point!")
                sys.exit()
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"{Fore.RED}Error: config.json is missing or corrupt!")
            sys.exit()

    def read_data_file(self, data_file="data.txt"):
        if not os.path.exists(data_file):
            print(f"{Fore.RED}Data file not found: {data_file}")
            sys.exit()
        with open(data_file, "r") as f:
            query_ids = f.readlines()
        return [query_id.strip() for query_id in query_ids if query_id.strip()]

    def renew_access_token(self, query_id):
        url = "https://www.binance.com/bapi/growth/v1/friendly/growth-paas/third-party/access/accessToken"
        data = {"query": query_id}
        res = self.http_request(url, data=data)
        if res and res.json().get("token"):
            return res.json()["token"]
        else:
            print(f"{Fore.RED}Failed to renew access token for query ID: {query_id}")
            return None

    def http_request(self, url, headers=None, data=None, method="GET"):
        try:
            headers = headers or self.base_headers
            if method == "GET":
                response = self.session.get(url, headers=headers, params=data)
            elif method == "POST":
                response = self.session.post(url, headers=headers, json=data)
            if response.status_code == 200:
                return response
            else:
                print(f"{Fore.RED}HTTP request failed with status {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"{Fore.RED}HTTP request error: {str(e)}")
            return None

    def solve_task(self, access_token):
        url_tasks = "https://www.binance.com/bapi/growth/v1/friendly/growth-paas/mini-app-activity/third-party/task/list"
        headers = self.base_headers.copy()
        headers["Authorization"] = f"Bearer {access_token}"

        res = self.http_request(url_tasks, headers=headers)
        if not res or not res.json():
            print(f"{Fore.YELLOW}Failed to fetch tasks!")
            return

        tasks_data = res.json()
        for task_group in tasks_data:
            task_list = task_group.get("tasks", [])
            for task in task_list:
                self.process_task(task, access_token)

    def process_task(self, task, access_token):
        task_id = task.get("id")
        task_status = task.get("status")
        headers = self.base_headers.copy()
        headers["Authorization"] = f"Bearer {access_token}"

        if task_status == "READY_FOR_CLAIM":
            claim_task_url = f"https://www.binance.com/bapi/growth/v1/friendly/growth-paas/mini-app-activity/third-party/task/list/{task_id}"
            self.http_request(claim_task_url, headers=headers, method="POST")
            print(f"{Fore.GREEN}Claimed task {task_id} successfully!")
        elif task_status == "STARTED":
            start_task_url = f"https://www.binance.com/bapi/growth/v1/friendly/growth-paas/mini-app-activity/third-party/task/list/{task_id}"
            self.http_request(start_task_url, headers=headers, method="POST")
            print(f"{Fore.CYAN}Started task {task_id}")

    def play_game(self, access_token):
        url_game = "https://www.binance.com/bapi/growth/v1/friendly/growth-paas/mini-app-activity/third-party/game/start"
        headers = self.base_headers.copy()
        headers["Authorization"] = f"Bearer {access_token}"

        res = self.http_request(url_game, headers=headers)
        if res and "gameId" in res.json():
            game_id = res.json()["gameId"]
            print(f"{Fore.GREEN}Started game with ID: {game_id}")
        else:
            print(f"{Fore.RED}Failed to start the game.")

    async def main(self):
        self.display_banner()  # Display the banner when starting the script
        query_ids = self.read_data_file()
        for query_id in query_ids:
            access_token = self.renew_access_token(query_id)
            if access_token:
                self.solve_task(access_token)
                self.play_game(access_token)

    def display_banner(self):
        banner = f"""{Fore.GREEN}
   ___                   _      __  __      _                 _ 
  / _ \ _ _ _ _ _ _  ___| |__  |  \/  |__ _| |_  _ __ _  _ __| |
 | (_) | '_| '_| ' \/ _ \ '_ \ | |\/| / _` | ' \| '  \ || / _` |
  \___/|_| |_| |_||_\___/_.__/ |_|  |_\__,_|_||_|_|_|_\_,_\__,_|
                                                                
    Auto Claim Bot For Blum - Orrnob's Drop Automation
    Author  : Orrnob Mahmud
    Github  : https://github.com/OrrnobMahmud
    Telegram: https://t.me/verifiedcryptoairdops
        {Style.RESET_ALL}"""
        print(banner)

# Run the script
if __name__ == "__main__":
    try:
        moonbix = MoonBix()
        asyncio.run(moonbix.main())
    except KeyboardInterrupt:
        print("Exiting...")
