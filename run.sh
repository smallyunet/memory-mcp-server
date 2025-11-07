set -euo pipefail

# Simple helper to manage the Dockerized app.
# Usage:
#   ./run.sh start          # start with Supabase (no local PostgreSQL)
#   ./run.sh start-local    # start with local PostgreSQL
#   ./run.sh stop           # stop containers
#   ./run.sh stop-local     # stop containers including local PostgreSQL
#   ./run.sh restart        # restart containers
#   ./run.sh logs           # follow logs
#   ./run.sh build          # rebuild image
#   ./run.sh down           # stop and remove containers
#   ./run.sh down-local     # stop and remove including local PostgreSQL volume
#   ./run.sh ps             # list containers
#   ./run.sh sh             # open a shell inside the running container
#
# Environment variables:
#   USE_LOCAL_DB=1 ./run.sh start   # alternative way to use local PostgreSQL

COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.yml}
SERVICE_NAME=${SERVICE_NAME:-memory-mcp}
USE_LOCAL_DB=${USE_LOCAL_DB:-0}

require_compose() {
  if ! command -v docker &>/dev/null; then
    echo "Docker is required but not installed." >&2
    exit 1
  fi
  if ! docker compose version &>/dev/null; then
    echo "Docker Compose v2 is required (docker compose)." >&2
    exit 1
  fi
}

get_profile_args() {
  if [ "$USE_LOCAL_DB" = "1" ]; then
    echo "--profile local-db"
  else
    echo ""
  fi
}

start() {
  require_compose
  local profile_args=$(get_profile_args)
  if [ -n "$profile_args" ]; then
    echo "🏠 Starting with local PostgreSQL..."
    docker compose -f "$COMPOSE_FILE" $profile_args up -d --build
    echo "✅ App started with local database. View logs with: ./run.sh logs"
  else
    echo "☁️  Starting with Supabase (no local PostgreSQL)..."
    docker compose -f "$COMPOSE_FILE" up -d --build
    echo "✅ App started. View logs with: ./run.sh logs"
  fi
}

start_local() {
  USE_LOCAL_DB=1 start
}

stop() {
  require_compose
  local profile_args=$(get_profile_args)
  docker compose -f "$COMPOSE_FILE" $profile_args stop
}

stop_local() {
  USE_LOCAL_DB=1 stop
}

restart() {
  require_compose
  docker compose -f "$COMPOSE_FILE" restart
}

logs() {
  require_compose
  docker compose -f "$COMPOSE_FILE" logs -f "$SERVICE_NAME"
}

build() {
  require_compose
  docker compose -f "$COMPOSE_FILE" build --no-cache
}

down() {
  require_compose
  local profile_args=$(get_profile_args)
  docker compose -f "$COMPOSE_FILE" $profile_args down
}

down_local() {
  require_compose
  echo "⚠️  Warning: This will remove the local PostgreSQL volume (data will be lost)"
  read -p "Continue? (y/N) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker compose -f "$COMPOSE_FILE" --profile local-db down -v
    echo "✅ Local database removed"
  else
    echo "Cancelled"
  fi
}

ps() {
  require_compose
  docker compose -f "$COMPOSE_FILE" ps
}

sh() {
  require_compose
  docker compose -f "$COMPOSE_FILE" exec "$SERVICE_NAME" sh
}

usage() {
  grep '^#' "$0" | sed -e 's/^# \{0,1\}//'
}

cmd=${1:-help}
case "$cmd" in
  start) start ;;
  start-local) start_local ;;
  stop) stop ;;
  stop-local) stop_local ;;
  restart) restart ;;
  logs) logs ;;
  build) build ;;
  down) down ;;
  down-local) down_local ;;
  ps) ps ;;
  sh) sh ;;
  help|*) usage ;;
 esac
