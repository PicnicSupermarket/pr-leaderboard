# PR Game
A leaderboard to rank developers based on their contributions to code reviewing, coupled with an Ethereum based 
cryptocurrency reward scheme.

![Dashboard](https://miro.medium.com/max/2680/1*aT1einIrArKy8U4P7FHw1A.png)

## About
The PR Game is a gamification of the code review process. We all love writing code, and some of us love reviewing code. 
But for a large number of us, code reviewing isn't how we necessarily want to spend our time but a necessity it is!
The PR Game adds an extra incentive to code reviewing in the form of a cryptocurrency where developers mine coins based 
on their contributions to code reviews. 

The default score is simply the ratio of between the number of PRs that a developer has reviewed versus the number of PRs 
that they have authored. This score can easily be adopted in the `pr_metrics.py` to take into account other PR related 
metrics such as number or length of comments in the PR, or decaying PR lead time for example. The possibilities are 
numerous, whatever KPI it is you are looking to optimise. 

Checkout the original [blog post](https://blog.picnic.nl/crypto-incentives-for-code-reviews-71a0be53d130).

## Setup

### Configuration
To setup the PR Game for your organisation there are a few properties that need to be configured in the `config.ini` 
file.

#### GitHub
To scrape pull request information from your organisations GitHub you need to 
[create a Github app](https://developer.github.com/apps/building-github-apps/creating-a-github-app/) organisation app 
then you need to configure the `AccessToken` and `Organisation` name in the `config.ini` file accordingly.

The dashboard is open to all users and authentication is up to you as the owner. Users who have a score below 1 aren't 
listed and their names are randomised. To allow for users in your organisation to sign into the dashboard to reveal
their position then you need to setup and
[configure your GitHub app](https://developer.github.com/apps/building-github-apps/creating-a-github-app/) provide an 
OAuth flow. Once this has been done you can configure the `Secret`, `ReturnUrl` and `ClientId` accordingly in the 
`config.ini`.

#### Ethereum
The default `PaymentWalletAddress` in the `config.ini` is configured to be the same as which the Ethereum node is initialised. 
This account is gifted a large quantity of ETH and is responsible for paying out the developers periodically. The default
developer account password is configured in `PaymentWalletPassword` and can be changed and updated by them via their wallet app.

### Deploy Service

```bash
# Install JS dependencies
yarn --cwd web install

# Build JS
yarn --cwd web build

# Build Docker image
docker build . -t pr-game:latest

# Run Docker container
docker run -d -p 8081:8081 -p 9999:9999 -p 8545:8545 pr-game:latest
```

### Run wallet

Download and install [Mist Wallet](https://github.com/ethereum/mist/releases). Then run:

```bash
mist --rpc http://node-ip:8545
```
