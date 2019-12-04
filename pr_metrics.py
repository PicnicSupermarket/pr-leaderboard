from github import Github, BadCredentialsException, RateLimitExceededException
from faker import Faker
from web3 import Web3, IPCProvider
from aiohttp import web
from retry import retry

import threading
import pickle
import aiohttp_cors
import requests
import schedule
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
        github_name = ""
        if token:
            try:
                github = Github(token)
                user = github.get_user()
                github_name = user.name or user.login
            except BadCredentialsException:
                return web.Response(status=401, text="401 Bad GitHub credentials")
        try:
            with open(App.historical_data, "rb") as f:
                historic = pickle.load(f)
            with open(App.accounts_data, "rb") as f:
                accounts = pickle.load(f)
        except FileNotFoundError:
            return web.Response(status=404)

        table_history = []
        for name in sorted(historic, key=historic.get, reverse=True):
            is_owner = False
            final_name = name
            try:
                address = accounts[name]
            except KeyError:
                print("No account exists for {}".format(name))
            amount = 0.0
            if address:
                w3 = Web3(IPCProvider(ipc_path=App.ipc))
                amount = w3.fromWei(w3.eth.getBalance(address), "ether")
            if (historic.get(name) < 1.0) and github_name != name:
                final_name = App.fake.name()
            elif github_name == name:
                final_name = name
                is_owner = True

            table_history.append(
                {
                    "name": final_name,
                    "ratio": "{:0.2f}".format(historic.get(name)),
                    "address": address or "n/a",
                    "coin": "{:0.6f}".format(amount),
                    "is_owner": is_owner,
                }
            )

        return web.json_response(table_history)


class App:

    ROUTES = [
        web.get(r"/api/health", Health),
        web.get(r"/api/authenticate", Auth),
        web.get(r"/api/metrics", Metrics),
    ]

    default_wallet_password = "password"

    accounts_data = "data/accounts.data"
    historical_data = "data/historical.data"

    ipc = "/root/geth.ipc"
    fake = Faker("en_GB")

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

    github = Github(token)
    org = github.get_organization(organisation)

    def __init__(self, config):
        self.config = config

    def get_app(self) -> web.Application:
        app = web.Application()
        app.add_routes(App.ROUTES)

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
    runThread = threading.Thread(target=run)
    runThread.start()
    web.run_app(app, port=9999)


def exhaust_pages(paginated):
    pages = []
    i = 0
    while True:
        page = paginated.get_page(i)
        i += 1
        pages.extend(page)
        if len(page) < 30:  # Last page
            break
    return pages


def historical():
    while True:
        members = exhaust_pages(App.org.get_members())
        ratios = {}
        print(f"Pulling stats for {len(members)} developers")
        for member in members:
            username = str(member.login)
            ratio = get_ratio(username)
            name = member.name if member.name is not None else username
            ratios[name] = ratio
        with open(App.historical_data, "wb+") as f:
            pickle.dump(ratios, f)


@retry(RateLimitExceededException, delay=10)
def get_ratio(username):
    authored = App.github.search_issues(
        f"org:{App.organisation} author:{username} is:closed"
    ).totalCount
    if authored > 0:
        reviewed = App.github.search_issues(
            "org:{} reviewed-by:{} is:closed".format(App.organisation, username)
        ).totalCount
        authored_and_reviewed = App.github.search_issues(
            "org:{} reviewed-by:{} author:{} is:closed".format(
                App.organisation, username, username
            )
        ).totalCount
        ratio = float((reviewed - authored_and_reviewed)) / authored
        return ratio


def pay_out():
    print("Paying out")
    try:
        with open(App.historical_data, "rb") as f:
            historic = pickle.load(f)
    except FileNotFoundError:
        return
    try:
        with open(App.accounts_data, "rb") as f:
            accounts = pickle.load(f)
    except FileNotFoundError:
        print("Accounts not found")
        accounts = {}

    w3 = Web3(IPCProvider(ipc_path=App.ipc))

    for user in historic:
        address = accounts.get(user)
        if address is None:
            address = w3.geth.personal.newAccount(App.default_wallet_password)
            accounts[user] = address

        ratio = historic.get(user)
        if ratio >= 1.0:
            amount = w3.toHex(int(math.pow(ratio, 15)))
            w3.geth.personal.unlockAccount(main, App.password)
            w3.eth.sendTransaction(
                transaction={"from": main, "to": address, "value": amount}
            )

    with open(App.accounts_data, "wb") as f:
        pickle.dump(accounts, f)


def pay():
    pay_out()
    schedule.every(10).minutes.do(pay_out)
    while True:
        schedule.run_pending()


def run():
    pay_thread = threading.Thread(target=pay)
    pay_thread.start()

    thread2 = threading.Thread(target=historical)
    thread2.setDaemon(True)
    thread2.start()
    thread2.join()


if __name__ == "__main__":
    main()
