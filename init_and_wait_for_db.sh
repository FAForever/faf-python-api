#!/usr/bin/env bash
pushd db
./setup_db.sh

docker exec -i faf-db mysql -uroot -pbanana faf_test < db-data.sql
popd
