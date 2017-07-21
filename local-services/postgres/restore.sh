#!/usr/bin/env sh

DB_RELEASE=2017-07-14
DB_HOST=192.168.99.100
DB_USER=postgres

echo "Downloading latest release"
wget https://github.com/elsehow/moneybot/releases/download/${DB_RELEASE}/${DB_RELEASE}.sql

echo "Restoring database to dockerized"
psql -h ${DB_HOST} -U ${DB_USER} -f ${DB_RELEASE}.sql

echo "Cleaning up artifacts"
rm -r ./${DB_RELEASE}.sql
