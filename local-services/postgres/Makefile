.PHONY: image server

image:
	docker pull postgres:9.6

server:
	docker run -d \
	-e "POSTGRES_PASSWORD=secretpass" \
	-p 5432:5432 \
	--name postgres \
	postgres:9.6
