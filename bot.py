import sys
import time

sys.dont_write_bytecode = True

from orrnob_drops_automation import base
from core.token import get_token
from core.info import get_info
from core.game import process_play_game


class Moonbix:
    def __init__(self):
        # Get file directory
        self.data_file = base.file_path(file_name="data.txt")
        self.config_file = base.file_path(file_name="config.json")
        self.proxy_file = base.file_path(file_name="data.proxy.txt")  # Add proxy file path

        # Initialize line
        self.line = base.create_line(length=50)

        # Initialize banner
        self.banner = base.create_banner(game_name="Moonbix")

    def display_proxy(self):
        # Display active proxy details if found
        try:
            with open(self.proxy_file, "r") as file:
                proxy_data = file.read().strip()
                if proxy_data:
                    base.log(f"{base.green}Active Proxy: {base.white}{proxy_data}")
                else:
                    base.log(f"{base.red}No active proxy found.")
        except FileNotFoundError:
            base.log(f"{base.red}Proxy file not found.")

    def main(self):
        while True:
            base.clear_terminal()
            print(self.banner)

            # Display proxy details
            self.display_proxy()

            data = open(self.data_file, "r").read().splitlines()
            num_acc = len(data)
            base.log(self.line)
            base.log(f"{base.green}Number of accounts: {base.white}{num_acc}")

            for no, data in enumerate(data):
                base.log(self.line)
                base.log(f"{base.green}Account number: {base.white}{no+1}/{num_acc}")

                try:
                    token = get_token(data=data)

                    if token:
                        get_info(token=token)
                        process_play_game(token=token)
                        get_info(token=token)
                    else:
                        base.log(f"{base.red}Token Expired! Please get new query id")
                except Exception as e:
                    base.log(f"{base.red}Error: {base.white}{e}")

            print()
            wait_time = 30 * 60
            base.log(f"{base.yellow}Wait for {int(wait_time / 60)} minutes!")
            time.sleep(wait_time)


if __name__ == "__main__":
    try:
        moonbix = Moonbix()
        moonbix.main()
    except KeyboardInterrupt:
        sys.exit()
