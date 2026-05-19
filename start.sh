#!/bin/sh
set -eu

python -m app.manager &
manager_pid=$!

uvicorn_args="--host 0.0.0.0 --port 8000"
if [ -n "${TLS_CERT_FILE:-}" ] || [ -n "${TLS_KEY_FILE:-}" ]; then
  if [ -z "${TLS_CERT_FILE:-}" ] || [ -z "${TLS_KEY_FILE:-}" ]; then
    echo "TLS_CERT_FILE and TLS_KEY_FILE must be set together"
    exit 1
  fi
  uvicorn_args="$uvicorn_args --ssl-certfile $TLS_CERT_FILE --ssl-keyfile $TLS_KEY_FILE"
fi
if [ -n "${TLS_CLIENT_CA_FILE:-}" ]; then
  uvicorn_args="$uvicorn_args --ssl-ca-certs $TLS_CLIENT_CA_FILE --ssl-cert-reqs 2"
fi

uvicorn app.main:app $uvicorn_args &
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
