def log(self, msg):
    now = datetime.now().isoformat().split("T")[1].split(".")[0]
    print(
        f"{black}[{now}]{white}-{blue}[{white}acc {self.p + 1}{blue}]{white} {msg}{reset}"
    )

async def ipinfo(self):
    url = "https://ipinfo.io/json"
    try:
        res = await self.http(
            url,
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0"
            },
        )
        ip = res.json().get("ip")
        country = res.json().get("country")
        self.log(f"{green}ip : {white}{ip} {green}country : {white}{country}")
    except Exception as e:
        self.log(f"{green}ip : {white}None {green}country : {white}None")

def get_random_proxy(self, isself, israndom=False):
    if israndom:
        return random.choice(self.proxies)
    return self.proxies[isself % len(self.proxies)]

async def http(self, url, headers, data=None):
    while True:
        try:
            if not await aiofiles.ospath.exists(log_file):
                async with aiofiles.open(log_file, "w") as w:
                    await w.write("")
            logsize = await aiofiles.ospath.getsize(log_file)
            if logsize / 1024 / 1024 > 1:
                async with aiofiles.open(log_file, "w") as w:
                    await w.write("")
            if data is None:
                res = await self.ses.get(url, headers=headers, timeout=30)
            elif data == "":
                res = await self.ses.post(url, headers=headers, timeout=30)
            else:
                res = await self.ses.post(
                    url, headers=headers, timeout=30, data=data
                )
            async with aiofiles.open(log_file, "a", encoding="utf-8") as hw:
                await hw.write(f"{res.status_code} {res.text}\n")
            if "<title>" in res.text:
                self.log(f"{yellow}failed get json response !")
                await countdown(3)
                continue

            return res
        except httpx.ProxyError:
            proxy = self.get_random_proxy(0, israndom=True)
            transport = AsyncProxyTransport.from_url(proxy)
            self.ses = httpx.AsyncClient(transport=transport)
            self.log(f"{yellow}proxy error,selecting random proxy !")
            await asyncio.sleep(3)
            continue
        except httpx.NetworkError:
            self.log(f"{yellow}network error !")
            await asyncio.sleep(3)
            continue
        except httpx.TimeoutException:
            self.log(f"{yellow}connection timeout !")
            await asyncio.sleep(3)
            continue
        except httpx.RemoteProtocolError:
            self.log(f"{yellow}connection close without response !")
            await asyncio.sleep(3)
            continue

def is_expired(self, token):
    if token is None or isinstance(token, bool):
        return True
    header, payload, sign = token.split(".")
    payload = b64decode(payload + "==").decode()
    jload = json.loads(payload)
    now = round(datetime.now().timestamp()) + 300
    exp = jload["exp"]
    if now > exp:
        return True

    return False

async def login(self):
    auth_url = "https://user-domain.blum.codes/api/v1/auth/provider/PROVIDER_TELEGRAM_MINI_APP"
    data = {
        "query": self.query,
    }
    res = await self.http(auth_url, self.headers, json.dumps(data))
    token = res.json().get("token")
    if not token:
        self.log(f"{red}failed get access token, check log file http.log !")
        return 3600
    token = token.get("access")
    uid = self.user.get("id")
    await update_token(uid, token)
    self.log(f"{green}success get access token !")
    self.headers["authorization"] = f"Bearer {token}"

async def start(self, sem):
    if not self.valid:
        return int(datetime.now().timestamp()) + (3600 * 8)
    async with sem:
        balance_url = "https://game-domain.blum.codes/api/v1/user/balance"
        friend_balance_url = "https://user-domain.blum.codes/api/v1/friends/balance"
        farming_claim_url = "https://game-domain.blum.codes/api/v1/farming/claim"
        farming_start_url = "https://game-domain.blum.codes/api/v1/farming/start"
        checkin_url = (
            "https://game-domain.blum.codes/api/v1/daily-reward?offset=-420"
        )
        if len(self.proxies) > 0:
            await self.ipinfo()
        uid = self.user.get("id")
        first_name = self.user.get("first_name")
        self.log(f"{green}login as {white}{first_name}")
        avail = await get_by_id(uid)
        if not avail:
            await insert(uid, first_name)
        token = await get_token(uid)
        expired = self.is_expired(token=token)
        if expired:
            await self.login()
        else:
            self.headers["authorization"] = f"Bearer {token}"
        res = await self.http(checkin_url, self.headers)
        if res.status_code == 404:
            self.log(f"{yellow}already check in today !")
        else:
            res = await self.http(checkin_url, self.headers, "")
            self.log(f"{green}success check in today !")

        while True:
            res = await self.http(balance_url, self.headers)
            timestamp = res.json().get("timestamp")
            if timestamp == 0:
                timestamp = int(datetime.now().timestamp() * 1000)
            if not timestamp:
                continue
            timestamp = timestamp / 1000
            break
        balance = res.json().get("availableBalance", 0)
        await update_balance(uid, balance)
        farming = res.json().get("farming")
        end_iso = datetime.now().isoformat(" ")
        end_farming = int(datetime.now().timestamp() * 1000) + random.randint(
            3600000, 7200000
        )
        self.log(f"{green}balance : {white}{balance}")
        refres = await self.http(friend_balance_url, self.headers)
        amount_claim = refres.json().get("amountForClaim")
        can_claim = refres.json().get("canClaim", False)
        self.log(f"{green}referral balance : {white}{amount_claim}")
        if can_claim:
            friend_claim_url = "https://user-domain.blum.codes/api/v1/friends/claim"
            clres = await self.http(friend_claim_url, self.headers, "")
            if clres.json().get("claimBalance") is not None:
                self.log(f"{green}success claim referral reward !")
            else:
                self.log(f"{red}failed claim referral reward !")
        if self.cfg.auto_claim:
            while True:
                if farming is None:
                    _res = await self.http(farming_start_url, self.headers, "")
                    if _res.status_code != 200:
                        self.log(f"{red}failed start farming !")
                    else:
                        self.log(f"{green}success start farming !")
                        farming = _res.json()
                end_farming = farming.get("endTime")
                if timestamp > (end_farming / 1000):
                    res_ = await self.http(farming_claim_url, self.headers, "")
                    if res_.status_code != 200:
                        self.log(f"{red}failed claim farming !")
                    else:
                        self.log(f"{green}success claim farming !")
                        farming = None
                        continue
                else:
                    self.log(f"{yellow}not time to claim farming !")
                end_iso = (
                    datetime.fromtimestamp(end_farming / 1000)
                    .isoformat(" ")
                    .split(".")[0]
                )
                break
            self.log(f"{green}end farming : {white}{end_iso}")
        if self.cfg.auto_task:
            task_url = "https://earn-domain.blum.codes/api/v1/tasks"
            res = await self.http(task_url, self.headers)
            for tasks in res.json():
                if isinstance(tasks, str):
                    self.log(f"{yellow}failed get task list !")
                    break
                for k in list(tasks.keys()):
                    if k != "tasks" and k != "subSections":
                        continue
                    for t in tasks.get(k):
                        if isinstance(t, dict):
                            subtasks = t.get("subTasks")
                            if subtasks is not None:
                                for task in subtasks:
                                    await self.solve(task)
                                await self.solve(t)
                                continue
                        _tasks = t.get("tasks")
                        if not _tasks:
                            continue
                        for task in _tasks:
                            await self.solve(task)
        if self.cfg.auto_game:
            play_url = "https://game-domain.blum.codes/api/v1/game/play"
            claim_url = "https://game-domain.blum.codes/api/v1/game/claim"
            while True:
                res = await self.http(balance_url, self.headers)
                play = res.json().get("playPasses")
                if play is None:
                    self.log(f"{yellow}failed get game ticket !")
                    break
                self.log(f"{green}you have {white}{play}{green} game ticket")
                if play <= 0:
                    break
                for i in range(play):
                    if self.is_expired(
                        self.headers.get("authorization").split(" ")[1]
                    ):
                        await self.login()
                        continue
                    res = await self.http(play_url, self.headers, "")
                    game_id = res.json().get("gameId")
                    if game_id is None:
                        message = res.json().get("message", "")
                        if message == "cannot start game":
                            self.log(f"{yellow}{message}")
                            break
                        self.log(f"{yellow}{message}")
                        continue
                    while True:
                        await countdown(30)
                        point = random.randint(self.cfg.low, self.cfg.high)
                        data = json.dumps({"gameId": game_id, "points": point})
                        res = await self.http(claim_url, self.headers, data)
                        if "OK" in res.text:
                            self.log(
                                f"{green}success earn {white}{point}{green} from game !"
                            )
                            break

                        message = res.json().get("message", "")
                        if message == "game session not finished":
                            continue

                        self.log(
                            f"{red}failed earn {white}{point}{red} from game !"
                        )
                        break
        res = await self.http(balance_url, self.headers)
        balance = res.json().get("availableBalance", 0)
        self.log(f"{green}balance :{white}{balance}")
        await update_balance(uid, balance)
        return round(end_farming / 1000)

async def solve(self, task: dict):
    task_id = task.get("id")
    task_title = task.get("title")
    task_status = task.get("status")
    task_type = task.get("type")
    validation_type = task.get("validationType")
    start_task_url = f"https://earn-domain.blum.codes/api/v1/tasks/{task_id}/start"
    claim_task_url = f"https://earn-domain.blum.codes/api/v1/tasks/{task_id}/claim"
    while True:
        if task_status == "FINISHED":
            self.log(f"{yellow}already complete task id {white}{task_id} !")
            return
        if task_status == "READY_FOR_CLAIM" or task_status == "STARTED":
            _res = await self.http(claim_task_url, self.headers, "")
            message = _res.json().get("message")
            if message:
                return
            _status = _res.json().get("status")
            if _status == "FINISHED":
                self.log(f"{green}success complete task id {white}{task_id} !")
                return
        if task_status == "NOT_STARTED" and task_type == "PROGRESS_TARGET":
            return
        if task_status == "NOT_STARTED":
            _res = await self.http(start_task_url, self.headers, "")
            await countdown(3)
            message = _res.json().get("message")
            if message:
                return
            task_status = _res.json().get("status")
            continue
        if validation_type == "KEYWORD" or task_status == "READY_FOR_VERIFY":
            verify_url = (
                f"https://earn-domain.blum.codes/api/v1/tasks/{task_id}/validate"
            )
            answer_url = "https://akasakaid.github.io/blum/answer.json"
            res_ = await self.http(answer_url, {"User-Agent": "Marin Kitagawa"})
            answers = res_.json()
            answer = answers.get(task_id)
            if not answer:
                self.log(f"{yellow}answers to quiz tasks are not yet available.")
                return
            data = {"keyword": answer}
            res = await self.http(verify_url, self.headers, json.dumps(data))
            message = res.json().get("message")
            if message:
                return
            task_status = res.json().get("status")
            continue
