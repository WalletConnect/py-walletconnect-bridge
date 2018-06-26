#!/bin/bash
set -e

#starting local instance of redis server and starting wallet connect bridge connected to local redis
redis-server &
echo "started redis server"
sleep 5
walletconnect-bridge --redis-local --port 8080 --host 0.0.0.0 &
echo "started wallet connect server"
 service nginx start
echo "started nginx service"
#now sleeping infinitely
tail -f /dev/null
