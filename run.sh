#!/usr/bin/env bash
python3 ./pr_metrics.py --token github_access_token --org PicnicSupermarket --password picnic --address 0xbca7692B5d80548f7579EE14A6F7189E4f54013e &
test "$(ls /pr-blockchain 2>/dev/null)" || mkdir /pr-blockchain/keystore && cp master-wallet /pr-blockchain/keystore && geth --identity "PrEthNode" --nodiscover --networkid 1999 --datadir /pr-blockchain init genesis.json && cp master-wallet /pr-blockchain/keystore
geth --identity "PrEthNode" --ipcpath "$HOME/geth.ipc" --datadir pr-blockchain --nodiscover --nousb --syncmode "full" --mine --minerthreads 1 --networkid 1999 --rpc --rpcport "8545" --rpcaddr "0.0.0.0" --rpccorsdomain "*" --rpcapi="db,eth,net,web3,personal,web3" --etherbase '0xbca7692B5d80548f7579EE14A6F7189E4f54013e' console
yarn dev
