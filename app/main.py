import uvicorn

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from .db.database import get_db
from .config import settings


app = FastAPI()


origins = [
    "http://localhost:8000",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status_code": 200, "detail": "ok", "result": "working"}

@app.get("/test-postgres")
async def test_postgres(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"message": "Database connection successful"}
    except SQLAlchemyError as e:
        return {"message": "Database connection failed", "exception": f"{e.args[0]}"}
    


if __name__ == '__main__':
    uvicorn.run('app.main:app', port=settings.port, reload=True)