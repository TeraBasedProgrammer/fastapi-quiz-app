# from typing import List, Optional
# from datetime import datetime

# from pydantic import BaseModel

# from .companies.schemas import CompanyBase
# from .users.schemas import UserBase

# class UserSchema(UserBase):
#     id: int
#     registered_at: datetime
#     auth0_registered: Optional[bool]
#     # is_owner: Optional[bool]
#     # companies: List[CompanyBase]

#     class Config:
#         from_attributes = True
#         # populate_by_name = True


# class CompanySchema(CompanyBase):
#     users: List[UserBase]

