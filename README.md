# WalletConnect Bridge Python Implementation 

![travis](https://travis-ci.org/WalletConnect/py-walletconnect-bridge.svg?branch=master)

A full introduction is described in our docs: https://docs.walletconnect.org/technical-specification

## Pre-requirements

1. Python
2. Docker (for Docker setup)
3. Make (for Make commands)

## Docker setup

**Step 0.** Point DNS record to your box (required for SSL)

```bash
  <YOUR_BRIDGE_URL>	   A	   192.168.1.1
```

**Step 1.** Setup the bridge URL to match your DNS record

```bash
$ make setup URL=<YOUR_BRIDGE_URL>

# OR

$ sed -i -e 's/bridge.mydomain.com/<YOUR_BRIDGE_URL>/g' nginx/defaultConf && rm -rf nginx/defaultConf-e
```

**Step 2.** Run the following command to build the Docker image

```bash
$ make build

# OR

$ docker build . -t py-walletconnect-bridge
```

**Step 3.** Finally run the following command to run the Docker container

```bash
$ make run

# OR

$ docker run -it -v $(pwd)/:/source/ -p 443:443 -p 80:80 py-walletconnect-bridge
```

You can test it at https://<YOUR_BRIDGE_URL>/hello

### Choose Branch

This setup defaults to the active branch in your current directory in order to build a Docker image from another branch, run the following command:

```bash
$ make build BRANCH=v0.7.x

# OR

$ docker build . -t py-walletconnect-bridge --build-arg branch=v0.7.x
```

For this sample configuration file, the bridge will be available at https://<YOUR_BRIDGE_URL>/ . After specifying <YOUR_BRIDGE_URL> to 0.0.0.0 in /etc/hosts,

### Update Bridge

To update the bridge, just run the following and it will maintain the existing state of the existing bridge sessions and quickly swap containers to the new version

```bash
$ make update

# Optional (choose branch)

$ make update BRANCH=develop
```

### Skip Cerbot

This approach uses [Certbot](https://certbot.eff.org/) to generate real SSL certificates for your configured nginx hosts. If you would prefer to use the self signed certificates, you can pass the `--skip-certbot` flag to `docker run` as follows:

```bash
$ make run_no_certbot

# OR

$ docker run -it -v $(pwd)/:/source/ -p 443:443 -p 80:80 py-walletconnect-bridge --skip-certbot
```

Certbot certificates expire after 90 days. To renew, shut down the docker process and run `make renew`. You should back up your old certs before doing this, as they will be deleted.

## Manual setup

If you'd like to keep a separate Python environment for this project's installs, set up virtualenv

```bash
$ pip install virtualenv virtualenvwrapper
```

Add the following to your ~/.bashrc

```bash
export WORKON_HOME=$HOME/.virtualenvs~
export PROJECT_HOME=$HOME/Devel
export VIRTUALENVWRAPPER_PYTHON=/usr/local/bin/python3
source /usr/local/bin/virtualenvwrapper.sh
```

From the project directory, run these commands to install the walletconnect-bridge package in a virtualenv called "walletconnect-bridge"

```bash
$ mkvirtualenv walletconnect-bridge
$ pip install -r requirements.txt
$ python setup.py develop
```

In another terminal, start local Redis instance

```bash
$ redis-server
```

Run the project locally

```bash
$ walletconnect-bridge --redis-local
```

Test your Bridge is working

```bash
$ curl https://<YOUR_BRIDGE_URL>/hello
```
