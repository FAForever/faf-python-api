#!/usr/bin/env bash
git clone https://github.com/FAForever/db.git db
pushd db
./setup_db.sh

docker exec -i faf-db mysql -uroot -pbanana faf_test < db-data.sql
popd
