.PHONY: clean tag

version := $(shell python3 setup.py --version)

clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	find . -name ".DS_Store" -delete
	rm -rf moneybot.egg-info

tag:
	git tag $(version)
