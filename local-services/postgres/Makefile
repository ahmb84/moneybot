.PHONY: image server

image:
	docker pull postgres:9.6-alpine

server:
	docker run -d \
	--env "POSTGRES_PASSWORD=secretpass" \
	--name postgres \
	--net moneybot \
	--publish 5432:5432 \
	postgres:9.6-alpine
