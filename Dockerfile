FROM ubuntu:disco

ENV PATH=/usr/lib/go-1.9/bin:$PATH

# Install requirements for setting up apt repositories
RUN set -eu pipefail \
  && apt-get update \
  && apt-get install -y curl software-properties-common \
    apt-transport-https

# Install all required apt repositories
RUN set -eu pipefail \
  && add-apt-repository -y ppa:ethereum/ethereum \
  && curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - \
  && echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list \
  && curl -sL https://deb.nodesource.com/setup_8.x | bash -

# Install dependencies
RUN set -eu pipefail \
  && apt-get update \
  && apt-get install -y \
    ethereum \
    python3 \
    python3-dev \
    python3-pip \
    nodejs \
    yarn

# Install Python dependencies
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ADD Pipfile.lock Pipfile config.ini ./
RUN set -eu pipefail \
  && python3 -m pip install --upgrade pip \
  && python3 -m pip install pipenv \
  && python3 -m pipenv install --deploy

# Install Javascript dependencies
ADD web/dist/ ./

# Add the rest of the source
ADD pr_metrics.py run.sh genesis.json master-wallet ./

VOLUME ["/pr-blockchain", "/data"]
EXPOSE 9999 8081 30303 8545
ENTRYPOINT ["sh", "run.sh"]
