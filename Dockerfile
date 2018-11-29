FROM ubuntu:16.04
ARG branch=master
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y \
  python3-pip \
  git \
  redis-server \
  nginx \
  software-properties-common
RUN add-apt-repository ppa:certbot/certbot
RUN apt-get update
RUN apt-get install -y python-certbot-nginx
ARG revision
RUN git clone https://github.com/WalletConnect/py-walletconnect-bridge
WORKDIR /py-walletconnect-bridge
RUN git checkout ${branch}
RUN pip3 install -r requirements.txt
RUN python3 setup.py install
COPY docker-entrypoint.sh /bin/
RUN chmod +x /bin/docker-entrypoint.sh
ENTRYPOINT ["/bin/docker-entrypoint.sh"]
EXPOSE 80
