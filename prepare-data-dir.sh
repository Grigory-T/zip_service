#!/bin/sh
set -eu

DATA_DIR="${DATA_DIR:-./data}"

mkdir -p "$DATA_DIR/jobs"

if command -v sudo >/dev/null 2>&1; then
    sudo chown -R 1000:1000 "$DATA_DIR"
else
    chown -R 1000:1000 "$DATA_DIR"
fi

chmod 775 "$DATA_DIR" "$DATA_DIR/jobs"

echo "prepared $DATA_DIR for container uid 1000"
