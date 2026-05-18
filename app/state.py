import json
import os
import shutil
import time
from pathlib import Path
from typing import Any


DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
JOBS_DIR = DATA_DIR / "jobs"
TERMINAL_STATUSES = {"done", "error"}


def now() -> float:
    return time.time()


def ensure_dirs() -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)


def job_dir(task_id: str) -> Path:
    return JOBS_DIR / task_id


def input_zip(task_id: str) -> Path:
    return job_dir(task_id) / "input.zip"


def output_zip(task_id: str) -> Path:
    return job_dir(task_id) / "output.zip"


def state_path(task_id: str) -> Path:
    return job_dir(task_id) / "state.json"


def read_state(task_id: str) -> dict[str, Any] | None:
    path = state_path(task_id)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_state(task_id: str, state: dict[str, Any]) -> None:
    ensure_dirs()
    directory = job_dir(task_id)
    directory.mkdir(parents=True, exist_ok=True)
    path = state_path(task_id)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, sort_keys=True)
    tmp.replace(path)


def update_state(task_id: str, **changes: Any) -> dict[str, Any]:
    state = read_state(task_id) or {"task_id": task_id, "job_id": task_id, "created_at": now()}
    state.update(changes)
    write_state(task_id, state)
    return state


def iter_states() -> list[dict[str, Any]]:
    ensure_dirs()
    states: list[dict[str, Any]] = []
    for path in JOBS_DIR.glob("*/state.json"):
        try:
            with path.open("r", encoding="utf-8") as f:
                states.append(json.load(f))
        except (OSError, json.JSONDecodeError):
            continue
    return states


def next_queued_task() -> str | None:
    queued = [s for s in iter_states() if s.get("status") == "queued"]
    if not queued:
        return None
    queued.sort(key=lambda s: s.get("created_at", 0))
    task_id = queued[0].get("task_id") or queued[0].get("job_id")
    return str(task_id) if task_id else None


def recover_processing_tasks(error: str) -> int:
    recovered = 0
    for state in iter_states():
        if state.get("status") != "processing":
            continue
        task_id = state.get("task_id") or state.get("job_id")
        if not task_id:
            continue
        update_state(str(task_id), status="error", error=error, finished_at=now())
        recovered += 1
    return recovered


def cleanup_old_tasks(retention_seconds: int) -> int:
    ensure_dirs()
    cutoff = now() - retention_seconds
    removed = 0
    for directory in JOBS_DIR.iterdir():
        if not directory.is_dir():
            continue
        state_file = directory / "state.json"
        if not state_file.exists():
            continue
        try:
            with state_file.open("r", encoding="utf-8") as f:
                state = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        status = state.get("status")
        finished_at = state.get("finished_at")
        if status in TERMINAL_STATUSES and isinstance(finished_at, (int, float)) and finished_at < cutoff:
            shutil.rmtree(directory, ignore_errors=True)
            removed += 1
    return removed
