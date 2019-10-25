from github import Github, BadCredentialsException
from faker import Faker
from web3 import Web3, IPCProvider
from aiohttp import web

import threading
import time
import pickle
import json
import aiohttp_cors
import requests
import schedule
import math
import configparser

default_wallet_password = 'password'

accounts_data = 'data/accounts.data'
historical_data = 'data/historical.data'

ipc = "/root/geth.ipc"
fake = Faker('en_GB')
routes = web.RouteTableDef()

config = configparser.ConfigParser()
cfg = config.read('config.ini')

github = config['Github']
oauth = config['OAuth']
ethereum = config['Ethereum']

organisation = github['Organisation']
token = github['AccessToken']

main = ethereum['PaymentWalletAddress']
password = ethereum['PaymentWalletPassword']

github_return_url = oauth['ReturnUrl']
github_client_secret = oauth['Secret']
github_client_id = oauth['ClientId']

g = Github(token)
org = g.get_organization(organisation)


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
    members = exhaust_pages(org.get_members())

    ratios = {}
    for member in members:
        username = str(member.login)
        authored = g.search_issues("org:{} author:{} is:closed".format(organisation, username)).totalCount
        if authored > 0:
            reviewed = g.search_issues("org:{} reviewed-by:{} is:closed".format(organisation, username)).totalCount
            authored_and_reviewed = g.search_issues(
                "org:{} reviewed-by:{} author:{} is:closed".format(organisation, username, username)).totalCount
            ratio = (float((reviewed - authored_and_reviewed)) / authored)
            name = member.name if member.name is not None else username
            ratios[name] = ratio
        time.sleep(10)

    with open(historical_data, 'wb') as f:
        pickle.dump(ratios, f)


def pay_out():
    w3 = Web3(IPCProvider(ipc_path=ipc))
    try:
        with open(historical_data, 'rb') as f:
            historic = pickle.load(f)
    except FileNotFoundError:
        return
    accounts = {}
    try:
        with open(accounts_data, 'rb') as f:
            accounts = pickle.load(f)
    except FileNotFoundError:
        print("Accounts not found")

    for user in historic:
        address = accounts.get(user)
        if address is None:
            address = w3.personal.newAccount(default_wallet_password)
            accounts[user] = address

        ratio = historic.get(user)
        if historic.get(user) >= 1.0:
            amount = w3.toHex(int(math.pow(ratio, 15)))
            w3.personal.unlockAccount(main, password)
            w3.eth.sendTransaction(
                transaction={'from': main, 'to': address, 'value': amount})

    with open(accounts_data, 'wb') as f:
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


@routes.get("/api/authenticate")
async def auth(request):
    code = request.rel_url.query.get("code")
    response = requests.post("https://github.com/login/oauth/access_token",
                             data={"client_id": github_client_id,
                                   "client_secret": github_client_secret,
                                   "code": code},
                             headers={'Accept': "application/json"})
    access_token = response.json()['access_token']
    r = web.HTTPFound(github_return_url)
    r.set_cookie('X-Access-Token', access_token)
    return r


@routes.get('/api/health')
async def health(request):
    return web.Response(text="OK!")


@routes.get('/api/metrics')
async def metrics(request):
    token = request.headers.get('X-Access-Token')
    github_name = ""
    if token:
        try:
            github = Github(token)
            user = github.get_user()
            github_name = user.name if user.name is not None else user.login
        except BadCredentialsException:
            return web.Response(status=401, text="401 Bad GitHub credentials")
    try:
        with open(historical_data, 'rb') as f:
            historic = pickle.load(f)
        with open(accounts_data, 'rb') as f:
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
        if address is None:
            address = "n/a"
        else:
            w3 = Web3(IPCProvider(ipc_path=ipc))
            amount = w3.fromWei(w3.eth.getBalance(address), "ether")
        if (historic.get(name) < 1.0) and github_name != name:
            final_name = fake.name()
        elif github_name == name:
            final_name = "{}".format(name)
            is_owner = True
        final = {'name': final_name, 'ratio': "{:0.2f}".format(historic.get(name)), 'address': address,
                 'coin': "{:0.6f}".format(amount), 'is_owner': is_owner}
        table_history.append(final)

    return web.Response(text=json.dumps(table_history))


def run_web():
    app = web.Application()
    app.add_routes(routes)
    configure_cors(app)
    web.run_app(app, port=9999)


def configure_cors(app):
    # Configure default CORS settings.
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })
    # Configure CORS on all routes.
    for route in list(app.router.routes()):
        cors.add(route)


if __name__ == '__main__':
    runThread = threading.Thread(target=run)
    runThread.start()
    run_web()
