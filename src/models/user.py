from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal


Role = Literal["admin", "client"]


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1)
    role: Role = "client"
    password_plain: str = Field(..., min_length=8)
    # para client: restringe acesso a estes codes de projeto
    project_codes: Optional[List[str]] = Field(default_factory=list)


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[Role] = None
    password_plain: Optional[str] = Field(default=None, min_length=8)
    project_codes: Optional[List[str]] = None


class UserOut(BaseModel):
    id: str = Field(..., alias="_id")
    email: EmailStr
    name: str
    role: Role
    project_codes: List[str] = []

    class Config:
        validate_by_name = True

class UserListResponse(BaseModel):
    items: List["UserOut"]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)

    class Config:
        validate_by_name = True
