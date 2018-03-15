# Balance Bridge

## Mobile Client Connection Details Sharing
1. when user wants to connect, web client generates unique public/private key pair for this connection
2. web client generates a unique token
3. web client sends request to server with a unique token
4. server submits entry to DB with unique token, sends back "success" if added
5. on success, web client displays unique token and public key in QR code to mobile client
6. after scanning in QR code, mobile client generates its own public/private key pair for this connection, encrypts public addresses and its own public key with web client's public key
7. mobile client uploads its device UUID, encrypted public addresses and its encrypted public key, and unique token to server
8. server updates DB with these details, sends back "success" to mobile client if added
9. web client long polls with unique token to request details
10. server returns details if found and removes the entry from DB (otherwise just keeps returning false)
11. web client decrypts public addresses and mobile public key and stores them for future use during that session

## Send Transaction
1. web client generates transaction details
2. web client encrypts transaction details with mobile client public key
3. web client submits transaction details to server with a unique transaction UUID
4. server stores transaction details on DB
5. server sends push notification to mobile client with transaction UUID and relevant details
6. mobile client requests full transaction details from server using unique transaction UUID
7. server returns and removes transaction details from DB if found
8. mobile client decrypts transaction payload with mobile client private key
9. mobile client displays full transaction details and requests TouchID approval
10. mobile client signs transaction and executes

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

From the project directory, run these commands to install the balance\_bridge package in a virtualenv called "balance\_bridge"
~~~~
$ mkvirtualenv balance-bridge
$ pip install -r requirements.txt
$ python setup.py develop
~~~~

In another terminal, start local Redis instance
~~~~
$ redis-server
~~~~

Run the project
~~~~
$ balance-bridge
~~~~

Use a tool like Postman to create requests to interact with the server.
