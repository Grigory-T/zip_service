# Sandbox Python Server

Small FastAPI zip-processing server for the LAN sandbox.

## What It Does

- Accepts a zip upload with `task_id` and `task_type`.
- Stores task files under `/data/jobs/<task_id>/`.
- Runs one manager process that processes queued tasks sequentially.
- Runs each task once in a separate child process.
- Returns final status as `done` or `error`.

Task types `1` and `2` are dummy implementations for now: both sleep for 1 second and copy `input.zip` to `output.zip`.

## Run

```bash
docker compose up --build
```

The service listens on:

```text
http://0.0.0.0:18081
```

Runtime task data is stored in:

```text
./data/jobs/
```

`data/` is intentionally ignored by git.
