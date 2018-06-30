#!/bin/bash
set -e

#starting local instance of redis server and starting wallet connect bridge connected to local redis
redis-server &
echo "started redis server"
sleep 5
walletconnect-bridge --redis-local --port 8080 --host 0.0.0.0 &
echo "started wallet connect server"
echo "generating keys"
mkdir /keys
openssl req -x509 -newkey rsa:4096 -keyout /keys/key.pem -out /keys/cert.pem -days 365 -nodes -subj "/C=US/ST=Oregon/L=Portland/O=Company Name/OU=Org/CN=bridge.mydomain.com"
echo "generated keys"
service nginx start
echo "started nginx service"
#now sleeping infinitely
tail -f /dev/null
