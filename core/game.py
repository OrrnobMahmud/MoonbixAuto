import requests
import time

from orrnob_drops_automation import base
from core.headers import headers
from core.info import get_info
from core.combination import get_game_data


def start_game(token, proxies=None):
    url = "https://www.binance.com/bapi/growth/v1/friendly/growth-paas/mini-app-activity/third-party/game/start"
    payload = {"resourceId": 2056}

    try:
        response = requests.post(
            url=url,
            headers=headers(token=token),
            json=payload,
            proxies=proxies,
            timeout=20,
        )
        data = response.json()
        return data
    except:
        return None


def complete_game(token, payload, point, proxies=None):
    url = "https://www.binance.com/bapi/growth/v1/friendly/growth-paas/mini-app-activity/third-party/game/complete"
    payload = {
        "resourceId": 2056,
        "payload": payload,
        "log": point,
    }

    try:
        response = requests.post(
            url=url,
            headers=headers(token=token),
            json=payload,
            proxies=proxies,
            timeout=20,
        )
        data = response.json()
        status = data["success"]
        return status
    except:
        return None


def loading_animation(seconds):
    animation = "|/-\\"
    for i in range(seconds):
        print(f"\r{base.yellow}Playing... {animation[i % len(animation)]}", end="")
        time.sleep(1)
    print()  # Move to the next line after loading


# Use the working version of the play_game logic
def play_game(start_game_data):
    # No 'proxies' argument passed here, following the working version you provided
    payload, point = get_game_data(game_response=start_game_data)
    return payload, point


def process_play_game(token, proxies=None):
    while True:
        start_game_data = start_game(token=token, proxies=proxies)
        start_game_code = start_game_data["code"]

        if start_game_code == "000000":
            payload, point = play_game(start_game_data=start_game_data)
            if payload:
                base.log(f"{base.yellow}Playing for 45 seconds...")
                loading_thread = threading.Thread(target=loading_animation, args=(45,))
                loading_thread.start()

                # Wait for the game to be played
                time.sleep(45)
                loading_thread.join()  # Wait for loading animation to finish

                complete_game_status = complete_game(
                    token=token, payload=payload, point=point, proxies=proxies
                )
                if complete_game_status:
                    base.log(
                        f"{base.white}Auto Play Game: {base.green}Success | {base.blue}Collected {point} points"
                    )
                    get_info(token=token, proxies=proxies)
                    time.sleep(1)
                else:
                    base.log(f"{base.white}Auto Play Game: {base.red}Fail")
                    break
            else:
                base.log(f"{base.white}Auto Play Game: {base.red}Fail")
                break
        elif start_game_code == "116002":
            base.log(f"{base.white}Auto Play Game: {base.red}No ticket left to play")
            break
        else:
            error_message = start_game_data["messageDetail"]
            base.log(f"{base.white}Auto Play Game: {base.red}Error - {error_message}")
            break
