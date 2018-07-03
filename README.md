# py-walletconnect-bridge
A full introduction is described in our docs.

* [Overview](https://github.com/WalletConnect/WalletConnect/blob/master/docs/home.adoc)
* [Wallet Addresses Flow](https://github.com/WalletConnect/WalletConnect/blob/master/docs/wallet_addresses.adoc)
* [Transactions Flow](https://github.com/WalletConnect/WalletConnect/blob/master/docs/transactions.adoc)

Telegram: [t.me/walletconnect](http://t.me/walletconnect)

## Docker setup
Add all the subdomains you want to serve as nginx configuration files in the nginx folder, and do a volume mapping to the dockers nginx configuration folder like this sample:
~~~~
$ docker build . -t py-walletconnect-bridge
$ docker run -v $(pwd)/nginx/:/etc/nginx/sites-enabled/ -p 443:443 -p 80:80 py-walletconnect-bridge
~~~~
For this sample configuration file, the bridge will be available at http://bridge.mydomain.com/ . After specifying bridge.mydomain.com to 0.0.0.0 in /etc/hosts,You can test it at http://bridge.mydomain.com/hello


## Manual setup

If you'd like to keep a separate Python environment for this project's installs, set up virtualenv
~~~~
$ pip install virtualenv virtualenvwrapper
~~~~

Add the following to your ~/.bashrc
~~~
export WORKON_HOME=$HOME/.virtualenvs~
export PROJECT_HOME=$HOME/Devel
export VIRTUALENVWRAPPER_PYTHON=/usr/local/bin/python3
source /usr/local/bin/virtualenvwrapper.sh
~~~~

From the project directory, run these commands to install the walletconnect-bridge package in a virtualenv called "walletconnect-bridge"
~~~~
$ mkvirtualenv walletconnect-bridge
$ pip install -r requirements.txt
$ python setup.py develop
~~~~

In another terminal, start local Redis instance
~~~~
$ redis-server
~~~~

Run the project locally
~~~~
$ walletconnect-bridge --redis-local
~~~~

Use a tool like Postman to create requests to interact with the server.
