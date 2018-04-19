# WalletConnect
A full introduction is described in our docs.

* [Overview](https://github.com/WalletConnect/WalletConnect/blob/master/docs/home.adoc)
* [Wallet Addresses Flow](https://github.com/WalletConnect/WalletConnect/blob/master/docs/wallet_addresses.adoc) 
* [Transactions Flow](https://github.com/WalletConnect/WalletConnect/blob/master/docs/transactions.adoc)

## Getting Started
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

From the project directory, run these commands to install the wallet-connect package in a virtualenv called "wallet-connect"
~~~~
$ mkvirtualenv wallet-connect
$ pip install -r requirements.txt
$ python setup.py develop
~~~~

In another terminal, start local Redis instance
~~~~
$ redis-server
~~~~

Run the project locally
~~~~
$ wallet-connect --redis-local --push-local --api-local
~~~~

Use a tool like Postman to create requests to interact with the server.
