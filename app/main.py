import logging
import logging.config

from fastapi_pagination import add_pagination
from fastapi_pagination.utils import disable_installed_extensions_check
from typing import List

import uvicorn
import redis.asyncio as rd
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from fastapi.middleware.cors import CORSMiddleware

from .users.router import user_router
from .auth.router import auth_router
from .database import get_async_session
from .config import settings
from .log_config import LOGGING_CONFIG



# Set up logging configuration 
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("main_logger")

redis = rd.from_url(settings.redis_url, decode_responses=True, encoding="utf-8", db=0)


app = FastAPI()

# Enable pagination in the app
add_pagination(app)
disable_installed_extensions_check()

# App routers
app.include_router(user_router)
app.include_router(auth_router)

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


if __name__ == '__main__':
    uvicorn.run('app.main:app', port=settings.port, reload=True)