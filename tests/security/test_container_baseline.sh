#!/usr/bin/env sh
set -eu

SERVICE="baseline"

cleanup() {
  docker compose down --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker compose build --pull=false "$SERVICE"
docker compose up -d "$SERVICE"

printf 'Waiting for health check...\n'
for i in $(seq 1 30); do
  status=$(docker inspect --format='{{.State.Health.Status}}' "$(docker compose ps -q "$SERVICE")" 2>/dev/null || true)
  [ "$status" = "healthy" ] && break
  sleep 1
done

[ "$(docker compose exec -T "$SERVICE" id -u)" != "0" ] || {
  echo "FAIL: service is running as root"
  exit 1
}

if docker compose exec -T "$SERVICE" sh -c 'touch /prohibited-write-test' >/dev/null 2>&1; then
  echo "FAIL: root filesystem is writable"
  exit 1
fi

if docker compose exec -T "$SERVICE" sh -c 'grep -q "CapEff:\s*0000000000000000" /proc/self/status'; then
  :
else
  echo "FAIL: effective Linux capabilities are not fully dropped"
  exit 1
fi

if docker compose exec -T "$SERVICE" sh -c 'test -S /var/run/docker.sock || test -S /run/docker.sock'; then
  echo "FAIL: host container runtime socket is exposed"
  exit 1
fi

if docker compose exec -T "$SERVICE" sh -c 'test -e /dev/kvm || test -e /dev/mem'; then
  echo "FAIL: prohibited host devices are exposed"
  exit 1
fi

if docker compose exec -T "$SERVICE" sh -c 'touch /tmp/allowed-write-test && rm /tmp/allowed-write-test'; then
  :
else
  echo "FAIL: explicitly scoped /tmp writable area is not usable"
  exit 1
fi

echo "PASS: MS-59 hardened container negative tests succeeded"
