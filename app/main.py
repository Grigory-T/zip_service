import logging
import os

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse

from .state import (
    ensure_dirs,
    input_zip,
    job_dir,
    now,
    output_zip,
    read_state,
    update_state,
    write_state,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("sandbox-python-server")
API_BEARER_TOKEN = os.environ.get("API_BEARER_TOKEN", "")

app = FastAPI(title="Sandbox Python Server", docs_url=None, redoc_url=None, openapi_url=None)


@app.on_event("startup")
def startup() -> None:
    ensure_dirs()
    if not API_BEARER_TOKEN:
        raise RuntimeError("API_BEARER_TOKEN is required")
    logger.info("python HTTP server started")


def require_bearer_token(authorization: str | None = Header(default=None)) -> None:
    if authorization != f"Bearer {API_BEARER_TOKEN}":
        raise HTTPException(status_code=401, detail="invalid bearer token")


@app.post("/jobs")
async def create_job(
    task_id: str = Form(...),
    task_type: str = Form(...),
    file: UploadFile = File(...),
    _auth: None = Depends(require_bearer_token),
) -> dict[str, str]:
    if task_type not in {"1", "2"}:
        raise HTTPException(status_code=400, detail="task_type must be 1 or 2")

    directory = job_dir(task_id)
    if directory.exists():
        raise HTTPException(status_code=409, detail="task_id already exists")
    directory.mkdir(parents=True, exist_ok=False)

    destination = input_zip(task_id)
    total = 0
    with destination.open("wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            f.write(chunk)

    state = {
        "task_id": task_id,
        "job_id": task_id,
        "task_type": task_type,
        "status": "queued",
        "filename": file.filename or "upload.zip",
        "size": total,
        "created_at": now(),
    }
    write_state(task_id, state)
    logger.info("accepted task_id=%s task_type=%s filename=%s size=%s", task_id, task_type, state["filename"], total)
    return {"task_id": task_id, "job_id": task_id, "task_type": task_type, "status": "queued"}


@app.get("/jobs/{task_id}", response_model=None)
def get_job(task_id: str, _auth: None = Depends(require_bearer_token)) -> dict[str, object] | FileResponse:
    state = read_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="task not found")
    if state.get("status") != "done":
        return state

    path = output_zip(task_id)
    if not path.exists():
        update_state(task_id, status="error", error="output.zip is missing", finished_at=now())
        raise HTTPException(status_code=404, detail="output not found")

    logger.info("return output task_id=%s", task_id)
    return FileResponse(
        path,
        media_type="application/zip",
        filename=f"processed-{task_id}.zip",
        headers={
            "X-Task-Status": "done",
            "X-Task-Id": task_id,
            "X-Task-Type": str(state.get("task_type", "")),
        },
    )
