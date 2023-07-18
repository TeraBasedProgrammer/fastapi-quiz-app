import logging
import logging.config
from .log_config import LOGGING_CONFIG
from typing import List

import uvicorn
import redis.asyncio as rd
from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from .users.routers import user_router
from .config import settings



# Set up logging configuration 
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("main_logger")

redis = rd.from_url(settings.redis_url, decode_responses=True, encoding="utf-8", db=0)


app = FastAPI()

# Enable pagination in the app
# add_pagination(app)

# App routers
app.include_router(user_router)

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


# @app.get("/test-postgres")
# async def postgres_connect(session: AsyncSession = Depends(get_async_session)):
#     try:
#         logger.info("Logger info message")
#         logger.error("Logger error message")
#         logger.debug("Logger debug message")
#         logger.warning("Logger warning message")
#         await session.execute(text("SELECT 1"))
#         return {"message": "Database connection successful"}
#     except SQLAlchemyError as e:
#         return {"message": "Database connection failed", "exception": f"{e.args[0]}"}
    

# @app.get("/test-redis")
# async def redis_connect():
#     await redis.set("Ryan Gosling", "Literally me")
#     value = await redis.get("Ryan Gosling")
#     if value:
#         return {"message": f"Redis works! Ryan gosling is {value}"}
#     return {"error": "You are not Ryan Gosling, redis doesn't work"} 



if __name__ == '__main__':
    uvicorn.run('app.main:app', port=settings.port, reload=True)