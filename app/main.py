import logging
import logging.config

import redis.asyncio as rd
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination
from fastapi_pagination.utils import disable_installed_extensions_check

from .auth.router import auth_router
from .config import settings
from .log_config import LOGGING_CONFIG
from .users.router import user_router

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