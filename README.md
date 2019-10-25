# PR Game

![Dashboard](https://miro.medium.com/max/2680/1*aT1einIrArKy8U4P7FHw1A.png)


## Setup
### Deploy Service

```bash
# Build
docker build . -t pr-game:latest

# Run
docker run -d -p 8081:8081 -p 9999:9999 -p 8545:8545 pr-game:latest
```

### Run wallet

Download [Mist Wallet](https://github.com/ethereum/mist/releases)

```bash
brew install mist

# and run 

mist --rpc http://node-ip:8545
```