# make targets for WalletConnect/py-walletconnect-bridge

default:
	echo "Available tasks: build, clean, renew, run, run_skip_certbot"

build:
	docker build . -t py-walletconnect-bridge

clean:
	sudo rm -rfv ssl/certbot/*

renew:
	make clean && make run

run:
	docker run -it -v $(shell pwd)/:/source/ -p 443:443 -p 80:80 py-walletconnect-bridge --name py-walletconnect-bridge

run_skip_certbot:
	docker run -it -v $(shell pwd)/:/source/ -p 443:443 -p 80:80 py-walletconnect-bridge --name py-walletconnect-bridge --skip-certbot

update:
	docker stop py-walletconnect-bridge && docker rm py-walletconnect-bridge && docker rmi py-walletconnect-bridge:latest && make build && make run_skip_certbot
