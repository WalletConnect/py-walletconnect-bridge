#!/bin/bash
set -e

#linking
rm -rf /etc/nginx/sites-enabled
ln -s /source/nginx /etc/nginx/sites-enabled
ln -s /source/ssl /keys

#starting local instance of redis server and starting walletconnect bridge connected to local redis
redis-server &
echo "started redis server"
sleep 5
walletconnect-bridge --port 8080 --host 0.0.0.0 &
echo "started walletconnect server"

#key generation
FILE="/keys/key.pem"
if [ ! -f $FILE ]; then
  echo "generating self signed keys"
  #make the self signed key so the initial nginx load works
  openssl req -x509 \
    -newkey rsa:4096 \
    -keyout $FILE \
    -out /keys/cert.pem \
    -days 365 \
    -nodes \
    -subj "/C=US/ST=Oregon/L=Portland/O=Company Name/OU=Org/CN=bridge.mydomain.com"
fi

if [ `ls /source/ssl/certbot` ]; then
  #copy keys from local
  echo "copying previously generated keys"
  mkdir -p /etc/letsencrypt/live
  cp -rf /source/ssl/certbot/* /etc/letsencrypt/live/
else
  if [ "$1" != "--skip-certbot" ]; then
    echo "generating certbot keys"
    #create certificate with certbot
    certbot --nginx
    #copy keys to local for rehydrating
    cp -rfL /etc/letsencrypt/live/* /source/ssl/certbot/
  else
    echo "skipping certbot"
  fi
fi
echo "generated keys"

#finish up
service nginx start
echo "started nginx service"
#now sleeping infinitely
tail -f /dev/null
