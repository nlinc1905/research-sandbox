from fastapi import FastAPI
from src.tasks import long_running_task

app = FastAPI()


@app.post("/start-task")
def start_task():
    task = long_running_task.delay()
    return {"task_id": task.id}


@app.get("/task-status/{task_id}")
def get_task_status(task_id: str):
    result = long_running_task.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None
    }
