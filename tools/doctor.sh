#!/usr/bin/env sh

# Read-only diagnostics must continue after individual failures to print a summary.
pass_count=0
warn_count=0
fail_count=0

report() {
  status=$1
  name=$2
  detail=$3
  printf '%-4s %s: %s\n' "$status" "$name" "$detail"
  case "$status" in
    PASS) pass_count=$((pass_count + 1)) ;;
    WARN) warn_count=$((warn_count + 1)) ;;
    FAIL) fail_count=$((fail_count + 1)) ;;
  esac
}

if { [ -r /proc/sys/kernel/osrelease ] && grep -qi microsoft /proc/sys/kernel/osrelease; } || [ -n "${WSL_DISTRO_NAME:-}" ]; then
  report PASS WSL2 detected
else
  report WARN WSL2 "not detected; run authoritative local commands inside WSL2"
fi

expected_python=$(tr -d '[:space:]' < .python-version)
if command -v python3 >/dev/null 2>&1; then
  actual_python=$(python3 -c 'import platform; print(platform.python_version())' 2>/dev/null)
  if [ "$actual_python" = "$expected_python" ]; then
    report PASS Python "$actual_python"
  else
    report FAIL Python "expected $expected_python, found ${actual_python:-unknown}; activate .python-version"
  fi
else
  report FAIL Python "missing; install and activate $expected_python"
fi

expected_make=$(awk '$1 == "make" {print $2}' .tool-versions)
if command -v make >/dev/null 2>&1; then
  actual_make=$(make --version 2>/dev/null | awk 'NR == 1 {print $3}')
  if [ "$actual_make" = "$expected_make" ]; then
    report PASS "GNU Make" "$actual_make"
  else
    report FAIL "GNU Make" "expected $expected_make, found ${actual_make:-unknown}"
  fi
else
  report FAIL "GNU Make" "missing; install $expected_make"
fi

if command -v git >/dev/null 2>&1; then
  report PASS Git "$(git --version | awk '{print $3}')"
else
  report FAIL Git "missing; install Git inside WSL2"
fi

if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    report PASS Docker "$(docker version --format '{{.Client.Version}}' 2>/dev/null)"
  else
    report FAIL Docker "client found but daemon unavailable; start Docker Desktop WSL2 integration"
  fi
else
  report FAIL Docker "missing; install Docker Desktop with the WSL2 backend"
fi

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  report PASS "Docker Compose" "$(docker compose version --short 2>/dev/null)"
else
  report FAIL "Docker Compose" "missing; enable the Docker Compose plugin"
fi

printf 'SUMMARY: PASS=%s WARN=%s FAIL=%s\n' "$pass_count" "$warn_count" "$fail_count"
[ "$fail_count" -eq 0 ]
