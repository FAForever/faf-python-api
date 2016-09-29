#!/usr/bin/env bash
pushd db
./setup_db.sh

docker build -t faf-db .
docker exec -i faf-db mysql -h127.0.0.1 -uroot -pbanana faf_test < db-data.sql
popd
