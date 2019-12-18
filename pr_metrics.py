import asyncio
import configparser
import logging
import math
import pickle
import sys

import requests

import aiohttp_cors
from aiohttp import web
from faker import Faker
from github import BadCredentialsException, Github, RateLimitExceededException
from retry import retry
from web3 import IPCProvider, Web3

LOGGER = logging.getLogger(__name__)


class Auth(web.View):
    async def get(self):
        code = self.request.rel_url.query.get("code")
        response = requests.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": self.request.app["github_client_id"],
                "client_secret": self.request.app["github_client_secret"],
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        access_token = response.json()["access_token"]
        r = web.HTTPFound(self.request.app["github_return_url"])
        r.set_cookie("X-Access-Token", access_token)
        return r


class Health(web.View):
    async def get(self):
        return web.Response(text="OK!")


class Metrics(web.View):
    async def get(self):
        token = self.request.headers.get("X-Access-Token")
        w3 = Web3(IPCProvider(ipc_path=self.request.app["ipc"]))
        github_name = ""
        if token:
            try:
                github = Github(token)
                user = github.get_user()
                github_name = user.name or user.login
            except BadCredentialsException:
                return web.Response(status=401, text="401 Bad GitHub credentials")

        table_history = []
        for name in sorted(
            self.request.app["scores"], key=self.request.app["scores"].get, reverse=True
        ):
            is_owner = False
            final_name = name
            try:
                address = self.request.app["accounts"][name]
            except KeyError:
                LOGGER.warning("No account found for name %s", name)
                address = None
            amount = 0.0
            if address:
                amount = w3.fromWei(w3.eth.getBalance(address), "ether")
            if (self.request.app["scores"].get(name) < 1.0) and github_name != name:
                final_name = self.request.app["fake"].name()
            elif github_name == name:
                final_name = name
                is_owner = True

            table_history.append(
                {
                    "name": final_name,
                    "ratio": f"{self.request.app['scores'].get(name):0.2f}",
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


def update_accounts(app, accounts):
    with open(app["accounts_data_path"], "wb+") as f:
        pickle.dump(accounts, f)


def update_scores(app, scores):
    with open(app["score_data_path"], "wb+") as f:
        pickle.dump(scores, f)


class App:
    ROUTES = [
        web.get(r"/api/health", Health),
        web.get(r"/api/authenticate", Auth),
        web.get(r"/api/metrics", Metrics),
    ]

    def __init__(self, config):
        self.config = config

    def get_app(self) -> web.Application:
        app = web.Application()
        app.add_routes(self.ROUTES)

        app.cleanup_ctx.extend(
            [
                self._init,
                self._init_config_ctx,
                self._init_github_ctx,
                self._init_scores_and_accounts_ctx,
            ]
        )

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

    async def _init(self, app):
        # Connection to Geth
        app["ipc"] = "/root/geth.ipc"
        # Region for anonymous names
        app["fake"] = Faker("en_GB")
        yield

    async def _init_config_ctx(self, app):
        LOGGER.info("Initialisation of config")
        # Configuration parsing
        config = configparser.ConfigParser()
        app["cfg"] = config.read("./config.ini")

        github = config["Github"]
        oauth = config["OAuth"]
        ethereum = config["Ethereum"]

        app["organisation"] = github["Organisation"]
        app["token"] = github["AccessToken"]

        app["main"] = ethereum["PaymentWalletAddress"]
        app["default_wallet_password"] = ethereum["PaymentWalletPassword"]

        app["github_return_url"] = oauth["ReturnUrl"]
        app["github_client_secret"] = oauth["Secret"]
        app["github_client_id"] = oauth["ClientId"]

        yield
        config.clear()
        LOGGER.info("Cleanup of config")

    async def _init_github_ctx(self, app):
        LOGGER.info("Initialisation of GitHub connection")
        # Github API
        github = Github(app["token"])
        app["org"] = github.get_organization(app["organisation"])
        yield

    async def _init_scores_and_accounts_ctx(self, app):
        LOGGER.info("Initialisation of scores and accounts")
        app["accounts_data_path"] = "data/accounts.data"
        app["scores_data_path"] = "data/scores.data"
        app["accounts"] = load_data(app["accounts_data_path"])
        app["scores"] = load_data(app["scores_data_path"])

        yield
        update_scores(app, app["scores"])
        update_accounts(app, app["accounts"])
        LOGGER.info("Flushing of data")


def main():
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logging.getLogger(__name__).setLevel(logging.DEBUG)

    app = App(configparser.ConfigParser()).get_app()
    app.on_startup.extend([pay_out_loop, score_calculation_loop])
    web.run_app(app, port=9999)


async def pay_out_loop(app):
    loop = asyncio.get_running_loop()
    while True:
        await loop.run_in_executor(None, pay_out, app)
        await asyncio.sleep(600)


async def score_calculation_loop(app):
    loop = asyncio.get_running_loop()
    while True:
        await loop.run_in_executor(None, calculate_scores, app)


def pay_out(app):
    w3 = Web3(IPCProvider(ipc_path=app["ipc"]))
    LOGGER.info("Paying out...")
    accounts = {}
    for user in app["scores"]:
        address = app["accounts"].get(user)
        if address is None:
            address = w3.geth.personal.newAccount(app["default_wallet_password"])
            accounts[user] = address
        ratio = app["scores"].get(user)
        if ratio >= 1.0:
            amount = w3.toHex(int(math.pow(ratio, 15)))
            w3.geth.personal.unlockAccount(main, app["password"])
            w3.eth.sendTransaction(
                transaction={"from": main, "to": address, "value": amount}
            )
    app["accounts"] = accounts
    update_accounts(app, accounts)


def calculate_scores(app):
    members = app["org"].get_members()
    LOGGER.info(f"Pulling stats for {members.totalCount} developers...")
    scores = app["scores"]
    for member in members:
        username = str(member.login)
        score = get_score(app, username)
        if score > 0:
            name = member.name if member.name is not None else username
            scores[name] = score
            app["scores"] = scores
            update_scores(app, scores)


@retry(RateLimitExceededException, delay=10)
def get_score(app, username):
    github = app["github"]
    organisation = app["organisation"]
    authored = github.search_issues(
        f"org:{organisation} author:{username} is:closed"
    ).totalCount
    if authored > 0:
        reviewed = github.search_issues(
            f"org:{organisation} reviewed-by:{username} is:closed"
        ).totalCount
        authored_and_reviewed = github.search_issues(
            f"org:{organisation}"
            f" reviewed-by:{username} "
            f"author:{username} is:closed"
        ).totalCount
        review_ratio = float((reviewed - authored_and_reviewed)) / authored
        return review_ratio
    return 0


if __name__ == "__main__":
    main()
