FROM ubuntu:bionic

ENV PATH=/usr/lib/go-1.9/bin:$PATH

RUN apt-get update
RUN apt-get install -y software-properties-common
RUN add-apt-repository -y ppa:ethereum/ethereum
RUN apt-get update
RUN apt-get install -y ethereum
RUN apt-get install -y python3 python3-dev python3-pip

ADD requirements.txt /

RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt
RUN apt-get install -y curl
RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -
RUN apt-get update && apt-get install -y apt-transport-https
RUN echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list
RUN apt-get update
RUN curl -sL https://deb.nodesource.com/setup_8.x | bash -
RUN apt-get install -y yarn nodejs

COPY web/ /
RUN rm -rf node_modules
RUN yarn install

ADD pr_metrics.py /
ADD run.sh /
ADD genesis.json /
ADD master-wallet /

VOLUME ["/pr-blockchain", "/data"]

EXPOSE 9999 8081 30303 8545

ENTRYPOINT ["sh", "run.sh"]
