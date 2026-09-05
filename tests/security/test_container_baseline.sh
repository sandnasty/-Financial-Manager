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
healthy=0
for i in $(seq 1 30); do
  status=$(docker inspect --format='{{.State.Health.Status}}' "$(docker compose ps -q "$SERVICE")" 2>/dev/null || true)
  if [ "$status" = "healthy" ]; then
    healthy=1
    break
  fi
  sleep 1
done

[ "$healthy" = "1" ] || {
  echo "FAIL: service did not become healthy"
  docker compose logs "$SERVICE" || true
  exit 1
}

uid=$(docker compose exec -T "$SERVICE" python -c 'import os; print(os.geteuid())' | tr -d '\r')
[ "$uid" != "0" ] || {
  echo "FAIL: service is running as root"
  exit 1
}

if docker compose exec -T "$SERVICE" python -c 'open("/prohibited-write-test", "w").close()' >/dev/null 2>&1; then
  echo "FAIL: root filesystem is writable"
  exit 1
fi

cap_eff=$(docker compose exec -T "$SERVICE" python -c 'print(next(line.split()[1] for line in open("/proc/self/status", encoding="utf-8") if line.startswith("CapEff:")))' | tr -d '\r')
[ "$cap_eff" = "0000000000000000" ] || {
  echo "FAIL: effective Linux capabilities are not fully dropped: $cap_eff"
  exit 1
}

if docker compose exec -T "$SERVICE" python -c 'import os,sys; sys.exit(0 if any(os.path.exists(p) for p in ("/var/run/docker.sock", "/run/docker.sock")) else 1)'; then
  echo "FAIL: host container runtime socket is exposed"
  exit 1
fi

if docker compose exec -T "$SERVICE" python -c 'import os,sys; sys.exit(0 if any(os.path.exists(p) for p in ("/dev/kvm", "/dev/mem")) else 1)'; then
  echo "FAIL: prohibited host devices are exposed"
  exit 1
fi

if docker compose exec -T "$SERVICE" python -c 'from pathlib import Path; p=Path("/tmp/allowed-write-test"); p.touch(); p.unlink()'; then
  :
else
  echo "FAIL: explicitly scoped /tmp writable area is not usable"
  exit 1
fi

version=$(docker compose exec -T "$SERVICE" python -c 'import platform; print(platform.python_version())' | tr -d '\r')
[ "$version" = "3.14.7" ] || {
  echo "FAIL: container Python runtime is $version; expected 3.14.7"
  exit 1
}

echo "PASS: MS-59 hardened container negative tests succeeded"
