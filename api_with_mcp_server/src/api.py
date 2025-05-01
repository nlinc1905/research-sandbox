from fastapi import FastAPI


app = FastAPI()


@app.get("/health")
def health_check() -> dict:
    """Health check endpoint"""
    return {"status": 200, "message": "ok"}


@app.get("/add")
def add(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b
