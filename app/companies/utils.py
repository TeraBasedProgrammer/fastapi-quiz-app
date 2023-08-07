import logging

from app.companies.models import Company
from .models import Company

logger = logging.getLogger("main_logger")


async def filter_companies_response(response: list[Company]) -> list[Company]:
    return(list(filter(lambda x: x.is_hidden == False, response)))
