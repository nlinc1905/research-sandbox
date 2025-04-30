# Long Running Task with Celery and Redis

This folder has a hello-world FastAPI application with a long running task. The task is executed on a celery worker 
and uses Redis as a message broker. Task runs are monitored with Flower.

## How to Run

```commandline
docker compose up --build
```

Then go to [http://localhost:8000/start-task](http://localhost:8000/start-task) to start the long-running task. 
You can check the status by going to [http://localhost:8000/task-status/{task_id}](http://localhost:8000/task-status/{task_id}).
You can access the Flower monitoring tool at [http://localhost:5555](http://localhost:5555).

## How to Stop

```commandline
docker compose down
```
