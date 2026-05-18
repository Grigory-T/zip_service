import shutil
import time

from .state import input_zip, output_zip


def run_task_process(task_id: str, task_type: str) -> None:
    # Placeholder for real task implementations. Both task types are dummy for now.
    time.sleep(1)
    shutil.copyfile(input_zip(task_id), output_zip(task_id))
