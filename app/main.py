from fastapi import FastAPI
from .config import settings


app = FastAPI()


@app.get("/")
async def root():
    return {"status_code": 200, "detail": "ok", "result": "working"}