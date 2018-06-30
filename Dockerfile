FROM ubuntu:16.04
RUN apt update
RUN apt install -y python3-pip git redis-server nginx
RUN git clone https://github.com/WalletConnect/py-walletconnect-bridge
WORKDIR /py-walletconnect-bridge
RUN pip3 install -r requirements.txt
RUN python3 setup.py install
COPY docker-entrypoint.sh /bin/
RUN chmod +x /bin/docker-entrypoint.sh
ENTRYPOINT ["/bin/docker-entrypoint.sh"]
EXPOSE 80
