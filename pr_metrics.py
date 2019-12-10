from github import Github, BadCredentialsException, RateLimitExceededException
from faker import Faker
from web3 import Web3, IPCProvider
from aiohttp import web
from retry import retry

import concurrent.futures
import asyncio
import time
import pickle
import aiohttp_cors
import requests
import math
import configparser


class Auth(web.View):
    async def get(self):
        code = self.request.rel_url.query.get("code")
        response = requests.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": App.github_client_id,
                "client_secret": App.github_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        access_token = response.json()["access_token"]
        r = web.HTTPFound(App.github_return_url)
        r.set_cookie("X-Access-Token", access_token)
        return r


class Health(web.View):
    async def get(self):
        return web.Response(text="OK!")


class Metrics(web.View):
    async def get(self):
        token = self.request.headers.get("X-Access-Token")
        w3 = Web3(IPCProvider(ipc_path=App.ipc))
        github_name = ""
        if token:
            try:
                github = Github(token)
                user = github.get_user()
                github_name = user.name or user.login
            except BadCredentialsException:
                return web.Response(status=401, text="401 Bad GitHub credentials")

        table_history = []
        for name in sorted(App.scores, key=App.scores.get, reverse=True):
            is_owner = False
            final_name = name
            try:
                address = App.accounts[name]
            except KeyError:
                print(f"No account exists for {name}")
                address = None
            amount = 0.0
            if address:
                amount = w3.fromWei(w3.eth.getBalance(address), "ether")
            if (App.scores.get(name) < 1.0) and github_name != name:
                final_name = App.fake.name()
            elif github_name == name:
                final_name = name
                is_owner = True

            table_history.append(
                {
                    "name": final_name,
                    "ratio": f"{App.scores.get(name):0.2f}",
                    "address": address or "n/a",
                    "coin": f"{amount:0.6f}",
                    "is_owner": is_owner,
                }
            )

        return web.json_response(table_history)


def load_data(file):
    try:
        with open(file, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        return {}


def update_accounts():
    with open(App.accounts_data_path, "wb+") as f:
        pickle.dump(App.accounts, f)


def update_scores():
    with open(App.score_data_path, "wb+") as f:
        pickle.dump(App.scores, f)


class App:
    ROUTES = [
        web.get(r"/api/health", Health),
        web.get(r"/api/authenticate", Auth),
        web.get(r"/api/metrics", Metrics),
    ]

    default_wallet_password = "password"

    accounts_data_path = "data/accounts.data"
    score_data_path = "data/scores.data"

    accounts = load_data(accounts_data_path)
    scores = load_data(score_data_path)

    # Connection to Geth
    ipc = "/root/geth.ipc"
    fake = Faker("en_GB")

    # Configuration parsing
    config = configparser.ConfigParser()
    cfg = config.read("./config.ini")

    github = config["Github"]
    oauth = config["OAuth"]
    ethereum = config["Ethereum"]

    organisation = github["Organisation"]
    token = github["AccessToken"]

    main = ethereum["PaymentWalletAddress"]
    password = ethereum["PaymentWalletPassword"]

    github_return_url = oauth["ReturnUrl"]
    github_client_secret = oauth["Secret"]
    github_client_id = oauth["ClientId"]

    # Github API
    github = Github(token)
    org = github.get_organization(organisation)

    def __init__(self, config):
        self.config = config

    def get_app(self) -> web.Application:
        app = web.Application()
        app.add_routes(self.ROUTES)

        # Configure default CORS settings.
        cors = aiohttp_cors.setup(
            app,
            defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True, expose_headers="*", allow_headers="*",
                )
            },
        )
        # Configure CORS on all routes.
        for route in list(app.router.routes()):
            cors.add(route)

        return app


def main():
    app = App(configparser.ConfigParser()).get_app()
    app.on_startup.append(schedule)
    web.run_app(app, port=9999)


async def schedule(app):
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
    loop = asyncio.get_running_loop()
    loop.run_in_executor(executor, calculate_scores)
    loop.run_in_executor(executor, pay_out)


def pay_out():
    w3 = Web3(IPCProvider(ipc_path=App.ipc))
    while True:
        print("Paying out...")
        for user in App.scores:
            address = App.accounts.get(user)
            if address is None:
                address = w3.geth.personal.newAccount(App.default_wallet_password)
                App.accounts[user] = address

            ratio = App.scores.get(user)
            if ratio >= 1.0:
                amount = w3.toHex(int(math.pow(ratio, 15)))
                w3.geth.personal.unlockAccount(main, App.password)
                w3.eth.sendTransaction(
                    transaction={"from": main, "to": address, "value": amount}
                )
        update_accounts()
        time.sleep(600)


def calculate_scores():
    while True:
        members = App.org.get_members()
        print(f"Pulling stats for {members.totalCount} developers...")
        for member in members:
            username = str(member.login)
            score = get_score(username)
            if score > 0:
                name = member.name if member.name is not None else username
                App.scores[name] = score
                update_scores()


@retry(RateLimitExceededException, delay=10)
def get_score(username):
    authored = App.github.search_issues(
        f"org:{App.organisation} author:{username} is:closed"
    ).totalCount
    if authored > 0:
        reviewed = App.github.search_issues(
            f"org:{App.organisation} reviewed-by:{username} is:closed"
        ).totalCount
        authored_and_reviewed = App.github.search_issues(
            f"org:{App.organisation} reviewed-by:{username} author:{username} is:closed"
        ).totalCount
        review_ratio = float((reviewed - authored_and_reviewed)) / authored
        return review_ratio
    return 0


if __name__ == "__main__":
    main()
