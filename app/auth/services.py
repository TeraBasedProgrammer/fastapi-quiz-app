import logging

from fastapi import HTTPException

from app.users.services import UserRepository
from app.users.services import error_handler


logger = logging.getLogger("main_logger")


async def confirm_current_user(crud: UserRepository, current_user_email: str, user_id: int) -> None:
    current_user = await crud.get_user_by_email(current_user_email)
    if current_user.id != user_id:
        logger.warning(f"User {user_id} is not a current user, abort")
        raise HTTPException(403, detail=error_handler("Forbidden"))