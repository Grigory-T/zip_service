import logging
import multiprocessing
import os
import time

from .processor import run_task_process
from .state import (
    cleanup_old_tasks,
    ensure_dirs,
    next_queued_task,
    now,
    output_zip,
    recover_processing_tasks,
    read_state,
    update_state,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("sandbox-python-manager")

RETENTION_SECONDS = int(os.environ.get("RETENTION_SECONDS", "3600"))
TASK_TIMEOUT_SECONDS = int(os.environ.get("TASK_TIMEOUT_SECONDS", "60"))


def process_task(task_id: str) -> None:
    state = read_state(task_id)
    if state is None:
        logger.error("task_id=%s disappeared before processing", task_id)
        return

    task_type = str(state.get("task_type", ""))
    update_state(task_id, status="processing", started_at=now())
    logger.info("task start task_id=%s task_type=%s", task_id, task_type)

    proc = multiprocessing.Process(target=run_task_process, args=(task_id, task_type), daemon=False)
    proc.start()
    proc.join(TASK_TIMEOUT_SECONDS)

    if proc.is_alive():
        proc.kill()
        proc.join(5)
        update_state(
            task_id,
            status="error",
            error=f"task timed out after {TASK_TIMEOUT_SECONDS}s",
            finished_at=now(),
        )
        logger.error("task timeout task_id=%s task_type=%s", task_id, task_type)
        return

    if proc.exitcode == 0 and output_zip(task_id).exists():
        update_state(task_id, status="done", finished_at=now(), output_name="processed.zip")
        logger.info("task done task_id=%s task_type=%s", task_id, task_type)
        return

    update_state(
        task_id,
        status="error",
        error=f"task process exited with code {proc.exitcode}",
        finished_at=now(),
    )
    logger.error("task error task_id=%s task_type=%s exitcode=%s", task_id, task_type, proc.exitcode)


def manager_loop() -> None:
    ensure_dirs()
    recovered = recover_processing_tasks("interrupted by manager restart")
    if recovered:
        logger.warning("marked %s interrupted task(s) as error", recovered)

    logger.info("manager loop started timeout=%ss retention=%ss", TASK_TIMEOUT_SECONDS, RETENTION_SECONDS)
    while True:
        try:
            removed = cleanup_old_tasks(RETENTION_SECONDS)
            if removed:
                logger.info("cleanup removed %s old task(s)", removed)

            task_id = next_queued_task()
            if task_id:
                process_task(task_id)
            else:
                time.sleep(1)
        except Exception:
            logger.exception("manager loop failure")
            time.sleep(1)


if __name__ == "__main__":
    manager_loop()
