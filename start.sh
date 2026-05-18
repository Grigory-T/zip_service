#!/bin/sh
set -eu

python -m app.manager &
manager_pid=$!

uvicorn app.main:app --host 0.0.0.0 --port 8000 &
uvicorn_pid=$!

stop_children() {
  kill -TERM "$manager_pid" "$uvicorn_pid" 2>/dev/null || true
  wait "$manager_pid" 2>/dev/null || true
  wait "$uvicorn_pid" 2>/dev/null || true
}

trap 'stop_children; exit 0' INT TERM

while true; do
  if ! kill -0 "$manager_pid" 2>/dev/null; then
    echo "manager process exited"
    kill -TERM "$uvicorn_pid" 2>/dev/null || true
    wait "$uvicorn_pid" 2>/dev/null || true
    exit 1
  fi

  if ! kill -0 "$uvicorn_pid" 2>/dev/null; then
    echo "uvicorn process exited"
    kill -TERM "$manager_pid" 2>/dev/null || true
    wait "$manager_pid" 2>/dev/null || true
    exit 1
  fi

  sleep 1
done
