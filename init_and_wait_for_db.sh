pushd db
docker build -t faf-db .
DB_CONTAINER=`docker run -d --name faf-db -e MYSQL_ROOT_PASSWORD=banana faf-db`
./wait_for_db.sh
docker logs faf-db
docker exec -i faf-db mysql -h127.0.0.1 -uroot -pbanana < db-structure.sql
docker exec -i faf-db mysql -h127.0.0.1 -uroot -pbanana < db-data.sql
popd
until nc -z $(sudo docker inspect --format='{{.NetworkSettings.IPAddress}}' $DB_CONTAINER) 3306
do
  echo "waiting for postgres container..."
  sleep 0.5
done
