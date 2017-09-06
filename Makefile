.PHONY: clean tag image live

version := $(shell python3 setup.py --version)

clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	find . -name ".DS_Store" -delete
	rm -rf moneybot.egg-info

tag:
	git tag $(version)

image:
	docker build -t moneybot:latest -t moneybot:$(version) .

live:
	docker run -d \
	--name moneybot \
	--net moneybot \
	moneybot:latest \
	-s buffed-coin -l DEBUG
