# WalletConnect Bridge Python Implementation

A full introduction is described in our docs: https://docs.walletconnect.org/technical-specification

## Pre-requirements

1. Python
2. Docker (for Docker setup)
3. Make (for Make commands)

## Docker setup

**Step 0.** Point DNS record to your box (required for SSL)

```bash
  bridge.mydomain.com	   A	   192.168.1.1
```

**Step 1.** Change the domain name on the `nginx/defaultConf` file

```bash
L4    server_name bridge.mydomain.com;

L10   server_name bridge.mydomain.com;

L28   proxy_redirect             http://0.0.0.0:8080 http://bridge.mydomain.com;
```

**Step 2.** Run the following command to build the Docker image

```bash
$ docker build . -t py-walletconnect-bridge

# OR

$ make build
```

**Step 3.** Finally run the following command to run the Docker container

```bash
$ docker run -it -v $(pwd)/:/source/ -p 443:443 -p 80:80 py-walletconnect-bridge

# OR

$ make run
```

You can test it at http://bridge.mydomain.com/hello

### Choose Branch

This setup defaults to `master` branch in order to build a Docker image from another branch, run the following command:

```bash
$ docker build . -t py-walletconnect-bridge --build-arg branch=develop

# OR

$ make build BRANCH=develop
```

For this sample configuration file, the bridge will be available at http://bridge.mydomain.com/ . After specifying bridge.mydomain.com to 0.0.0.0 in /etc/hosts,

### Update Bridge

To update the bridge, just run the following and it will maintain the existing state of the existing bridge sessions and quickly swap containers to the new version

```bash
$ make update

# Optional (choose branch)

$ make update BRANCH=develop
```

### Skip Certbot

This approach uses [Certbot](https://certbot.eff.org/) to generate real SSL certificates for your configured nginx hosts. If you would prefer to use the self signed certificates, you can pass the `--skip-certbot` flag to `docker run` as follows:

```bash
$ docker run -it -v $(pwd)/:/source/ -p 443:443 -p 80:80 py-walletconnect-bridge --skip-certbot

# OR

$ make run_no_certbot
```

Certbot certificates expire after 90 days. To renew, shut down the docker process and run `make renew`. You should back up your old certs before doing this, as they will be deleted.

## Manual setup

If you'd like to keep a separate Python environment for this project's installs, set up virtualenv

```bash
$ pip install virtualenv virtualenvwrapper
```

Add the following to your ~/.bashrc

```
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
$ curl http://bridge.mydomain.com/hello
```
