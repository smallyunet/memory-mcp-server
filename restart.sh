set -e
set -x

docker compose build
docker compose down
docker compose up -d
